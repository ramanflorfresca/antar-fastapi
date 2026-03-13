"""
antar_engine/astrocartography.py

Astrocartography Engine — Dasha + Patra Integrated
──────────────────────────────────────────────────────────────────────
Standard astrocartography maps planetary lines across the world.
This engine adds two layers no other app has:

  1. DASHA TIMING: A Jupiter AC line means more when you're IN
     a Jupiter dasha. A Venus line means more during Venus dasha.
     Lines that match your active dasha are amplified and time-windowed.

  2. PATRA FILTER: The same Jupiter line means different things
     for a 25-year-old student vs a 45-year-old entrepreneur.
     Recommendations are filtered through life circumstances.

The 4 Planetary Lines:
  AC (Ascendant):  Planet rising — its energy expresses through YOU
                   Best for: personal growth, identity, presence
  MC (Midheaven):  Planet at career peak — its energy is PUBLIC
                   Best for: career, reputation, recognition
  DC (Descendant): Planet setting — its energy comes THROUGH others
                   Best for: relationships, partnerships, marriage
  IC (Nadir):      Planet at root — its energy is PRIVATE/HOME
                   Best for: home, family, inner life, roots

The meaning of each planet × line × life concern × dasha:
  These are all pre-computed in the lookup tables below.
  The LLM gets the top 3-5 city recommendations with full context.

Usage:
    from antar_engine.astrocartography import (
        get_best_cities_for_concern,
        get_current_location_reading,
        build_astrocartography_prompt,
    )
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ── What each planet × line means ────────────────────────────────────────────

PLANET_LINE_MEANINGS = {
    "Sun": {
        "AC": {
            "theme":        "Identity, authority, and personal power",
            "best_for":     ["career", "leadership", "recognition", "confidence"],
            "energy":       "You shine here. Others see your authority naturally. "
                            "Leadership positions come more easily.",
            "caution":      "Ego pressure. The need to perform can be exhausting.",
            "life_areas":   ["career", "identity", "growth"],
        },
        "MC": {
            "theme":        "Peak career recognition and public achievement",
            "best_for":     ["career", "fame", "professional legacy"],
            "energy":       "Your career peaks here. This is where reputation is built. "
                            "Public recognition comes naturally.",
            "caution":      "Workaholic tendencies. Life can become all about career.",
            "life_areas":   ["career", "recognition"],
        },
        "DC": {
            "theme":        "Relationships with authority figures",
            "best_for":     ["partnerships with powerful people", "mentors"],
            "energy":       "Partners here tend to be strong, authoritative, solar types. "
                            "Good for finding powerful collaborators.",
            "caution":      "Power imbalances in relationships.",
            "life_areas":   ["relationships", "partnerships"],
        },
        "IC": {
            "theme":        "Deep personal roots and family pride",
            "best_for":     ["family legacy", "home ownership", "roots"],
            "energy":       "Strong sense of identity through home and family here.",
            "caution":      "Father issues or family pressure can surface.",
            "life_areas":   ["home", "family"],
        },
    },

    "Moon": {
        "AC": {
            "theme":        "Emotional depth, intuition, and connection with locals",
            "best_for":     ["emotional healing", "intuition", "belonging", "family"],
            "energy":       "You feel at home here quickly. Locals feel like family. "
                            "Your intuition and emotional intelligence are heightened.",
            "caution":      "Emotional volatility. Mood swings amplified.",
            "life_areas":   ["happiness", "home", "emotional wellbeing", "family"],
        },
        "MC": {
            "theme":        "Career in nurturing, public service, or emotional work",
            "best_for":     ["counselling", "healthcare", "food", "real estate", "public work"],
            "energy":       "Career involving the public and nurturing. "
                            "Public emotional connection is your strength here.",
            "caution":      "Career can feel emotionally draining.",
            "life_areas":   ["career", "public life"],
        },
        "DC": {
            "theme":        "Deeply nurturing, emotional partnerships",
            "best_for":     ["love", "marriage", "emotional partnerships"],
            "energy":       "Relationships here are deeply emotional and nurturing. "
                            "Very good for finding a life partner.",
            "caution":      "Codependency patterns can emerge.",
            "life_areas":   ["love", "relationships", "marriage"],
        },
        "IC": {
            "theme":        "The perfect home — roots, comfort, belonging",
            "best_for":     ["settling down", "family home", "domestic happiness"],
            "energy":       "This is where home feels like home. "
                            "The best place in the world to put down roots.",
            "caution":      "Can be hard to leave. Attachment to place.",
            "life_areas":   ["home", "family", "happiness", "roots"],
        },
    },

    "Mars": {
        "AC": {
            "theme":        "Energy, courage, drive, and physical vitality",
            "best_for":     ["entrepreneurship", "athletics", "action", "independence"],
            "energy":       "You become bold and driven here. Energy is high. "
                            "This is where you take action and build.",
            "caution":      "Aggression, conflict, and accidents risk higher.",
            "life_areas":   ["career", "entrepreneurship", "health", "growth"],
        },
        "MC": {
            "theme":        "Career in action, competition, and leadership",
            "best_for":     ["military", "sports", "surgery", "engineering", "startups"],
            "energy":       "Competitive career energy peaks here. "
                            "You fight for recognition and win.",
            "caution":      "Workaholism and burnout risk.",
            "life_areas":   ["career", "achievement"],
        },
        "DC": {
            "theme":        "Passionate, dynamic relationships",
            "best_for":     ["passionate romance", "competitive partnerships"],
            "energy":       "Relationships here are intense, passionate, and dynamic. "
                            "Strong sexual and creative chemistry.",
            "caution":      "Conflict and power struggles in relationships.",
            "life_areas":   ["love", "relationships"],
        },
        "IC": {
            "theme":        "Active home environment",
            "best_for":     ["construction", "property development", "active lifestyle"],
            "energy":       "Home is a place of activity and building. "
                            "Good for property investment.",
            "caution":      "Conflict in the home environment.",
            "life_areas":   ["home", "property"],
        },
    },

    "Mercury": {
        "AC": {
            "theme":        "Communication, intellect, and networking",
            "best_for":     ["writing", "media", "business", "education", "technology"],
            "energy":       "Your mind shines here. Communication flows. "
                            "Business and intellectual work come naturally.",
            "caution":      "Overthinking. Nervous energy.",
            "life_areas":   ["career", "business", "education", "growth"],
        },
        "MC": {
            "theme":        "Career in communication, media, and commerce",
            "best_for":     ["journalism", "publishing", "tech", "trading", "consulting"],
            "energy":       "Mercury careers peak here. Writing, speaking, trading. "
                            "Your words carry authority.",
            "caution":      "Scattered focus. Too many projects.",
            "life_areas":   ["career", "money"],
        },
        "DC": {
            "theme":        "Intellectual partnerships and communication-based relationships",
            "best_for":     ["intellectual partnerships", "business partnerships"],
            "energy":       "Relationships here are stimulating and communicative. "
                            "Good for finding a witty, intelligent partner.",
            "caution":      "Relationships can stay too intellectual, lack depth.",
            "life_areas":   ["relationships", "business partnerships"],
        },
        "IC": {
            "theme":        "Stimulating home and neighborhood environment",
            "best_for":     ["studying at home", "writing retreats", "lively neighborhood"],
            "energy":       "Home is intellectually alive. Good neighborhood connections.",
            "caution":      "Restlessness. Difficulty settling.",
            "life_areas":   ["education", "home"],
        },
    },

    "Jupiter": {
        "AC": {
            "theme":        "Expansion, luck, wisdom, and abundance",
            "best_for":     ["all life areas", "growth", "opportunity", "wisdom"],
            "energy":       "The luckiest line. Everything expands here. "
                            "Opportunity finds you. People want to help you. "
                            "Your natural optimism and wisdom shine.",
            "caution":      "Over-expansion. Taking on too much. Weight gain.",
            "life_areas":   ["growth", "happiness", "money", "career", "love"],
        },
        "MC": {
            "theme":        "Career in education, law, spirituality, or leadership",
            "best_for":     ["academia", "law", "consulting", "spiritual teaching", "international work"],
            "energy":       "Career recognition and respect come abundantly here. "
                            "You're seen as wise and authoritative.",
            "caution":      "Overconfidence in professional matters.",
            "life_areas":   ["career", "education", "recognition"],
        },
        "DC": {
            "theme":        "Expansive, growth-oriented partnerships",
            "best_for":     ["marriage", "business partnerships", "beneficial alliances"],
            "energy":       "Partners here are generous, wise, and growth-oriented. "
                            "Marriage here is expansive and blessed.",
            "caution":      "Partner may be over-promising or extravagant.",
            "life_areas":   ["love", "marriage", "business partnerships"],
        },
        "IC": {
            "theme":        "Abundant, spacious, philosophical home life",
            "best_for":     ["large home", "family abundance", "spiritual home"],
            "energy":       "Home feels expansive and blessed here. "
                            "Family life is abundant and generous.",
            "caution":      "Excess at home. Difficulty with limits.",
            "life_areas":   ["home", "family", "happiness"],
        },
    },

    "Venus": {
        "AC": {
            "theme":        "Beauty, charm, art, and social magnetism",
            "best_for":     ["love", "art", "beauty industry", "social life", "luxury"],
            "energy":       "You're magnetic here. People are drawn to you. "
                            "Beauty and pleasure surround you. "
                            "Art and aesthetic work flourish.",
            "caution":      "Laziness. Overindulgence. Vanity.",
            "life_areas":   ["love", "happiness", "career (creative)", "money"],
        },
        "MC": {
            "theme":        "Career in arts, beauty, luxury, or diplomacy",
            "best_for":     ["fashion", "art", "music", "hospitality", "diplomacy"],
            "energy":       "Creative and aesthetic career thrives here. "
                            "Your beauty and charm are your professional currency.",
            "caution":      "Career can become about appearances, not substance.",
            "life_areas":   ["career", "creative work", "money"],
        },
        "DC": {
            "theme":        "Beautiful, harmonious, loving relationships",
            "best_for":     ["love", "marriage", "romantic partnerships"],
            "energy":       "The best line for love and marriage. "
                            "Partners here are beautiful, refined, and loving. "
                            "Romance flows naturally.",
            "caution":      "Relationships can be too focused on aesthetics.",
            "life_areas":   ["love", "marriage", "relationships"],
        },
        "IC": {
            "theme":        "Beautiful, harmonious, pleasurable home",
            "best_for":     ["beautiful home", "art-filled space", "domestic harmony"],
            "energy":       "Home is a sanctuary of beauty and pleasure. "
                            "Domestic life is harmonious.",
            "caution":      "Spending too much on home aesthetics.",
            "life_areas":   ["home", "happiness", "family harmony"],
        },
    },

    "Saturn": {
        "AC": {
            "theme":        "Discipline, mastery, and long-term building",
            "best_for":     ["serious career building", "long-term projects", "mastery"],
            "energy":       "This is where you do your life's most serious work. "
                            "Results come slowly but they last. "
                            "Real mastery is possible here.",
            "caution":      "Heavy, slow, isolating. Loneliness possible. Depression risk.",
            "life_areas":   ["career", "mastery", "long-term growth"],
        },
        "MC": {
            "theme":        "Career legacy and serious professional authority",
            "best_for":     ["government", "law", "finance", "long-term businesses"],
            "energy":       "Saturn MC creates lasting career legacy. "
                            "Slow but permanent professional recognition.",
            "caution":      "Career feels like burden. Burnout without boundaries.",
            "life_areas":   ["career", "legacy"],
        },
        "DC": {
            "theme":        "Serious, committed, karmic relationships",
            "best_for":     ["serious long-term partnership", "karmic relationships"],
            "energy":       "Relationships here are serious and committed. "
                            "Often karmic — teachers and lessons through partners.",
            "caution":      "Heavy or cold relationships. Relationships feel like work.",
            "life_areas":   ["relationships", "marriage (serious)"],
        },
        "IC": {
            "theme":        "Karmic home and ancestral roots",
            "best_for":     ["ancestral homeland", "serious contemplation", "retreat"],
            "energy":       "Feels connected to deep roots and ancestors. "
                            "Good for retreat and serious inner work.",
            "caution":      "Home can feel cold, heavy, or isolating.",
            "life_areas":   ["roots", "spiritual work", "solitude"],
        },
    },

    "Rahu": {
        "AC": {
            "theme":        "Ambition, transformation, and foreign destiny",
            "best_for":     ["ambition", "fame", "transformation", "foreign culture"],
            "energy":       "Intensely destined and karmic. This is where you become. "
                            "Rapid growth, fame, transformation — but turbulent.",
            "caution":      "Obsession. Identity confusion. Too much too fast.",
            "life_areas":   ["growth", "career (ambitious)", "transformation"],
        },
        "MC": {
            "theme":        "Ambitious, unconventional career peak",
            "best_for":     ["disruptive business", "media", "fame", "tech", "foreign work"],
            "energy":       "Career here is unconventional and rapidly rising. "
                            "Fame is possible. Foreign elements amplify career.",
            "caution":      "Career rises fast and can fall fast.",
            "life_areas":   ["career", "fame", "money"],
        },
        "DC": {
            "theme":        "Karmic, transformative, unusual relationships",
            "best_for":     ["cross-cultural relationships", "transformative partnerships"],
            "energy":       "Relationships here are intensely karmic. "
                            "Often cross-cultural or unusual. Very transformative.",
            "caution":      "Obsessive attachments. Unstable relationships.",
            "life_areas":   ["love (intense)", "relationships"],
        },
        "IC": {
            "theme":        "Foreign roots and transformative home life",
            "best_for":     ["expat life", "foreign ancestry exploration"],
            "energy":       "Home in a foreign land feels destined and karmic.",
            "caution":      "Feeling rootless or unsettled at home.",
            "life_areas":   ["expat life", "transformation"],
        },
    },

    "Ketu": {
        "AC": {
            "theme":        "Spiritual depth, detachment, and past-life resonance",
            "best_for":     ["spiritual practice", "meditation", "solitude", "liberation"],
            "energy":       "Deep spiritual resonance. Past-life connections strong. "
                            "Meditation and spiritual practice are amplified. "
                            "Worldly desires naturally reduce.",
            "caution":      "Isolation. Withdrawal from life. Depression possible.",
            "life_areas":   ["spirituality", "education (spiritual)", "liberation"],
        },
        "MC": {
            "theme":        "Spiritual or service-based career",
            "best_for":     ["spiritual teaching", "healing", "research", "service"],
            "energy":       "Career here is selfless and spiritual. "
                            "Recognition through service and wisdom.",
            "caution":      "Career feels meaningless or detached.",
            "life_areas":   ["career (spiritual)", "service"],
        },
        "DC": {
            "theme":        "Spiritual and releasing relationships",
            "best_for":     ["spiritual partnerships", "past-life connections"],
            "energy":       "Relationships feel karmic and past-life connected. "
                            "Deep soul recognition with partners.",
            "caution":      "Relationships dissolve. Partners disappear or withdraw.",
            "life_areas":   ["spiritual relationships"],
        },
        "IC": {
            "theme":        "Spiritual home and ancestral karma",
            "best_for":     ["ashram life", "ancestral homeland", "spiritual retreat"],
            "energy":       "Deep spiritual roots here. Ancestral connections strong.",
            "caution":      "Home feels like karma, not comfort.",
            "life_areas":   ["spirituality", "roots", "solitude"],
        },
    },
}


# ── Concern → best planet/line combinations ──────────────────────────────────

CONCERN_TO_LINES = {
    "love": [
        ("Venus", "DC"), ("Moon", "DC"), ("Jupiter", "DC"),
        ("Venus", "AC"), ("Moon", "AC"), ("Jupiter", "AC"),
    ],
    "marriage": [
        ("Venus", "DC"), ("Jupiter", "DC"), ("Moon", "DC"),
        ("Jupiter", "IC"), ("Moon", "IC"),
    ],
    "career": [
        ("Jupiter", "MC"), ("Sun", "MC"), ("Mercury", "MC"),
        ("Mars", "MC"), ("Saturn", "MC"), ("Jupiter", "AC"),
        ("Sun", "AC"), ("Rahu", "MC"),
    ],
    "money": [
        ("Jupiter", "AC"), ("Jupiter", "MC"), ("Venus", "AC"),
        ("Venus", "MC"), ("Mercury", "MC"), ("Rahu", "MC"),
    ],
    "growth": [
        ("Jupiter", "AC"), ("Jupiter", "MC"), ("Sun", "AC"),
        ("Mars", "AC"), ("Rahu", "AC"),
    ],
    "health": [
        ("Moon", "AC"), ("Moon", "IC"), ("Jupiter", "AC"),
        ("Venus", "IC"), ("Sun", "AC"),
    ],
    "happiness": [
        ("Jupiter", "AC"), ("Venus", "AC"), ("Moon", "AC"),
        ("Moon", "IC"), ("Jupiter", "IC"), ("Venus", "IC"),
    ],
    "education": [
        ("Jupiter", "AC"), ("Jupiter", "MC"), ("Mercury", "AC"),
        ("Mercury", "IC"), ("Ketu", "AC"),
    ],
    "spirituality": [
        ("Ketu", "AC"), ("Ketu", "IC"), ("Jupiter", "AC"),
        ("Moon", "IC"), ("Saturn", "IC"),
    ],
    "home": [
        ("Moon", "IC"), ("Jupiter", "IC"), ("Venus", "IC"),
        ("Moon", "AC"),
    ],
}


# ── City database — planet line proximities ──────────────────────────────────
# In production: calculate these from Swiss Ephemeris using the user's birth chart.
# These are approximate line regions — replace with real calculations.
# Format: city → { planet: { line_type: strength (0-1) } }

# This is a representative sample. Real system calculates all cities
# from the planetary positions at birth.

CITY_LINE_DATA = {
    # ── Jupiter AC line cities (sample) ──
    "Berlin, Germany":        {"Jupiter": {"AC": 0.9}, "Saturn": {"IC": 0.7}},
    "Oslo, Norway":           {"Jupiter": {"AC": 0.85}, "Mercury": {"MC": 0.6}},
    "Vienna, Austria":        {"Jupiter": {"AC": 0.8}, "Venus": {"DC": 0.75}},
    "Zurich, Switzerland":    {"Jupiter": {"MC": 0.85}, "Mercury": {"MC": 0.7}},

    # ── Venus DC / AC line cities (sample) ──
    "Paris, France":          {"Venus": {"AC": 0.9, "DC": 0.85}, "Jupiter": {"MC": 0.6}},
    "Florence, Italy":        {"Venus": {"AC": 0.85}, "Moon": {"IC": 0.7}},
    "Barcelona, Spain":       {"Venus": {"DC": 0.8}, "Mars": {"AC": 0.6}},
    "Buenos Aires, Argentina":{"Venus": {"AC": 0.75}, "Moon": {"AC": 0.8}},

    # ── Moon AC / IC line cities (sample) ──
    "Amsterdam, Netherlands": {"Moon": {"AC": 0.85}, "Mercury": {"DC": 0.7}},
    "Vancouver, Canada":      {"Moon": {"AC": 0.9}, "Jupiter": {"DC": 0.65}},
    "Auckland, New Zealand":  {"Moon": {"IC": 0.85}, "Venus": {"DC": 0.7}},
    "Edinburgh, Scotland":    {"Moon": {"AC": 0.8}, "Saturn": {"IC": 0.7}},

    # ── Mars AC line cities (sample) ──
    "Tel Aviv, Israel":       {"Mars": {"AC": 0.85}, "Rahu": {"MC": 0.6}},
    "São Paulo, Brazil":      {"Mars": {"AC": 0.8}, "Jupiter": {"MC": 0.7}},
    "Melbourne, Australia":   {"Mars": {"MC": 0.75}, "Saturn": {"DC": 0.6}},

    # ── Mercury MC line cities (sample) ──
    "Singapore":              {"Mercury": {"MC": 0.9}, "Jupiter": {"AC": 0.7}},
    "San Francisco, USA":     {"Mercury": {"MC": 0.85}, "Rahu": {"AC": 0.7}},
    "London, UK":             {"Mercury": {"MC": 0.8}, "Saturn": {"AC": 0.65}},
    "Toronto, Canada":        {"Mercury": {"AC": 0.75}, "Moon": {"DC": 0.7}},

    # ── Rahu AC / MC line cities (sample) ──
    "Dubai, UAE":             {"Rahu": {"MC": 0.9}, "Jupiter": {"DC": 0.65}},
    "New York, USA":          {"Rahu": {"AC": 0.85}, "Mercury": {"MC": 0.8}},
    "Shanghai, China":        {"Rahu": {"AC": 0.8}, "Saturn": {"MC": 0.6}},
    "Mumbai, India":          {"Rahu": {"MC": 0.75}, "Venus": {"DC": 0.6}},

    # ── Saturn AC / MC line cities (sample) ──
    "Tokyo, Japan":           {"Saturn": {"MC": 0.85}, "Mercury": {"AC": 0.7}},
    "Seoul, South Korea":     {"Saturn": {"AC": 0.8}, "Rahu": {"MC": 0.65}},

    # ── Sun AC / MC line cities (sample) ──
    "Los Angeles, USA":       {"Sun": {"AC": 0.85}, "Venus": {"DC": 0.7}},
    "Rome, Italy":            {"Sun": {"MC": 0.8}, "Venus": {"AC": 0.75}},
    "Cairo, Egypt":           {"Sun": {"AC": 0.75}, "Mars": {"IC": 0.6}},

    # ── Moon IC (home/roots) cities (sample) ──
    "Lisbon, Portugal":       {"Moon": {"IC": 0.9}, "Venus": {"AC": 0.75}},
    "Chiang Mai, Thailand":   {"Moon": {"IC": 0.85}, "Jupiter": {"AC": 0.7}},
    "Medellin, Colombia":     {"Moon": {"IC": 0.8}, "Venus": {"DC": 0.65}},
    "Porto, Portugal":        {"Moon": {"IC": 0.85}, "Venus": {"IC": 0.7}},

    # ── Ketu AC (spiritual) cities (sample) ──
    "Rishikesh, India":       {"Ketu": {"AC": 0.9}, "Jupiter": {"IC": 0.75}},
    "Kyoto, Japan":           {"Ketu": {"AC": 0.8}, "Saturn": {"IC": 0.7}},
    "Ubud, Bali":             {"Ketu": {"AC": 0.85}, "Moon": {"IC": 0.8}},
    "Varanasi, India":        {"Ketu": {"IC": 0.9}, "Saturn": {"AC": 0.7}},

    # ── Jupiter IC (home abundance) cities (sample) ──
    "Sydney, Australia":      {"Jupiter": {"IC": 0.85}, "Moon": {"AC": 0.7}},
    "Cape Town, South Africa":{"Jupiter": {"IC": 0.8}, "Venus": {"DC": 0.7}},
    "Montreal, Canada":       {"Jupiter": {"IC": 0.75}, "Mercury": {"AC": 0.7}},
}


# ── Dasha amplification ───────────────────────────────────────────────────────

def get_dasha_amplification(planet: str, dashas: dict) -> dict:
    """
    Returns how much the current dasha amplifies this planet's lines.

    If you're in a Jupiter dasha and looking at Jupiter lines:
    → Those lines are HOT right now with a time window.

    Returns:
    {
        "amplified": bool,
        "multiplier": float,   # 1.0 = normal, 1.5 = strong, 2.0 = very strong
        "reason": str,
        "window": str,         # "until July 2027"
        "urgency": str,        # "NOW" | "SOON" | "BUILDING"
    }
    """
    vim_dasha = dashas.get("vimsottari", [{}])[0]
    vim_antardasha = dashas.get("vimsottari", [{}, {}])[1] if len(dashas.get("vimsottari", [])) > 1 else {}
    jai_dasha = dashas.get("jaimini", [{}])[0]

    vim_lord = vim_dasha.get("lord_or_sign", "")
    vim_ad   = vim_antardasha.get("lord_or_sign", "")
    vim_end  = vim_dasha.get("end", "")

    # Perfect match: planet = mahadasha
    if vim_lord == planet:
        return {
            "amplified":  True,
            "multiplier": 2.0,
            "reason":     f"You are IN your {planet} Mahadasha right now",
            "window":     f"until {vim_end[:7] if vim_end else 'your period ends'}",
            "urgency":    "NOW",
        }

    # Strong match: planet = antardasha
    if vim_ad == planet:
        ad_end = vim_antardasha.get("end", "")
        return {
            "amplified":  True,
            "multiplier": 1.5,
            "reason":     f"{planet} is your active sub-period right now",
            "window":     f"until {ad_end[:7] if ad_end else 'sub-period ends'}",
            "urgency":    "NOW",
        }

    # Next dasha: planet coming soon
    upcoming = dashas.get("vimsottari", [])[1:4]
    for i, period in enumerate(upcoming):
        if period.get("lord_or_sign") == planet:
            start = period.get("start", "")
            return {
                "amplified":  True,
                "multiplier": 1.2,
                "reason":     f"Your {planet} period is approaching",
                "window":     f"starting {start[:7] if start else 'soon'}",
                "urgency":    "SOON" if i == 0 else "BUILDING",
            }

    # Natural affinity: Jaimini aligns
    if jai_dasha.get("lord_or_sign") == planet:
        return {
            "amplified":  True,
            "multiplier": 1.3,
            "reason":     f"Jaimini Chara Dasha also activates {planet} energy",
            "window":     "current Jaimini period",
            "urgency":    "NOW",
        }

    return {
        "amplified":  False,
        "multiplier": 1.0,
        "reason":     "",
        "window":     "",
        "urgency":    "NEUTRAL",
    }


# ── Patra filter ──────────────────────────────────────────────────────────────

def filter_by_patra(recommendations: list, patra) -> list:
    """
    Filter and re-rank city recommendations based on life circumstances.

    A 22-year-old student gets education-forward cities.
    A 45-year-old entrepreneur gets business-forward cities.
    A newly married person gets home/family cities for settling.
    """
    if not patra:
        return recommendations

    # Boost scoring based on patra
    for rec in recommendations:
        boost = 0.0

        # Career-stage based boosts
        if patra.career_stage in ["entrepreneur", "mid_career", "senior_career"]:
            if "career" in rec.get("life_areas", []) or "money" in rec.get("life_areas", []):
                boost += 0.2

        if patra.career_stage == "student":
            if "education" in rec.get("life_areas", []):
                boost += 0.3

        if patra.career_stage == "retired":
            if "happiness" in rec.get("life_areas", []) or "home" in rec.get("life_areas", []):
                boost += 0.3

        # Marital-status based boosts
        if patra.marital_status in ["single", "divorced"]:
            if "love" in rec.get("life_areas", []):
                boost += 0.25

        if patra.marital_status in ["married", "in_relationship"]:
            if "home" in rec.get("life_areas", []) or "family" in rec.get("life_areas", []):
                boost += 0.2

        # Life stage boosts
        if patra.life_stage_key == "brahmacharya":          # young, forming
            if "education" in rec.get("life_areas", []) or "growth" in rec.get("life_areas", []):
                boost += 0.2

        if patra.life_stage_key in ["consolidation", "vanaprastha"]:
            if "spirituality" in rec.get("life_areas", []):
                boost += 0.3

        # Health boosts
        if patra.health_status in ["chronic", "recovery", "mental_health"]:
            if "health" in rec.get("life_areas", []) or "happiness" in rec.get("life_areas", []):
                boost += 0.2

        rec["patra_adjusted_score"] = rec.get("base_score", 0.7) + boost

    # Re-rank by adjusted score
    recommendations.sort(key=lambda x: x.get("patra_adjusted_score", 0), reverse=True)
    return recommendations


# ── Current location reading ──────────────────────────────────────────────────

def get_current_location_reading(
    city: str,
    planet_lines: dict,        # { planet: { line_type: strength } }
    dashas: dict,
    patra=None,
    language: str = "en",
) -> dict:
    """
    Generate a reading for the user's CURRENT city.
    Shows which planetary lines are active there and what they mean.

    Args:
        city: current city name
        planet_lines: pre-calculated planetary lines for this city
        dashas: user's current dasha periods
        patra: user's life circumstances

    Returns:
        {
            "city": str,
            "active_lines": [...],
            "dominant_theme": str,
            "summary": str,
            "dasha_alignment": str,
            "recommendations": str,
        }
    """
    if not planet_lines:
        return {
            "city": city,
            "active_lines": [],
            "dominant_theme": "No strong planetary lines detected here",
            "summary": (
                "This location doesn't sit on a strong planetary line for your chart. "
                "That's neutral — it means no particular planetary energy is amplified. "
                "Your results here depend more on your own effort than on location energy."
            ),
            "dasha_alignment": "",
            "recommendations": "Focus on inner work rather than relying on location energy.",
        }

    # Find active lines (strength > 0.6)
    active_lines = []
    for planet, lines in planet_lines.items():
        for line_type, strength in lines.items():
            if strength >= 0.6:
                meaning = PLANET_LINE_MEANINGS.get(planet, {}).get(line_type, {})
                dasha_amp = get_dasha_amplification(planet, dashas)
                active_lines.append({
                    "planet":      planet,
                    "line_type":   line_type,
                    "strength":    strength,
                    "theme":       meaning.get("theme", ""),
                    "energy":      meaning.get("energy", ""),
                    "caution":     meaning.get("caution", ""),
                    "life_areas":  meaning.get("life_areas", []),
                    "dasha_amp":   dasha_amp,
                    "final_score": strength * dasha_amp["multiplier"],
                })

    # Sort by final score
    active_lines.sort(key=lambda x: x["final_score"], reverse=True)

    # Dominant line
    dominant = active_lines[0] if active_lines else None
    dominant_theme = dominant["theme"] if dominant else "Neutral location"

    # Dasha alignment summary
    dasha_notes = []
    for line in active_lines[:3]:
        if line["dasha_amp"]["amplified"]:
            dasha_notes.append(
                f"{line['planet']} {line['line_type']} line is active here "
                f"AND {line['dasha_amp']['reason']} — "
                f"this amplification lasts {line['dasha_amp']['window']}"
            )

    return {
        "city":            city,
        "active_lines":    active_lines,
        "dominant_theme":  dominant_theme,
        "dasha_alignment": " | ".join(dasha_notes) if dasha_notes else "No strong dasha alignment here currently",
        "summary":         _build_location_summary(city, active_lines, dominant),
        "recommendations": _build_location_recommendations(active_lines, patra),
    }


# ── Best cities for concern ───────────────────────────────────────────────────

def get_best_cities_for_concern(
    concern: str,
    city_line_data: dict,     # pre-calculated for user's chart
    dashas: dict,
    patra=None,
    current_country: str = None,
    limit: int = 5,
) -> list[dict]:
    """
    Returns top cities for a specific life concern.
    Filtered by dasha timing + patra circumstances.

    Args:
        concern: "love" | "career" | "money" | "growth" | "health" |
                 "happiness" | "education" | "spirituality" | "home"
        city_line_data: calculated planetary lines per city
        dashas: user's current dasha periods
        patra: user's life circumstances
        current_country: bias toward nearby cities if provided
        limit: max cities to return

    Returns list of city recommendation dicts.
    """
    target_lines = CONCERN_TO_LINES.get(concern, CONCERN_TO_LINES["growth"])
    recommendations = []

    for city, planet_lines in city_line_data.items():
        city_score = 0.0
        matched_lines = []
        life_areas = []

        for planet, line_type in target_lines:
            strength = planet_lines.get(planet, {}).get(line_type, 0.0)
            if strength >= 0.5:
                dasha_amp  = get_dasha_amplification(planet, dashas)
                final_score = strength * dasha_amp["multiplier"]
                city_score  = max(city_score, final_score)
                meaning     = PLANET_LINE_MEANINGS.get(planet, {}).get(line_type, {})
                life_areas.extend(meaning.get("life_areas", []))

                matched_lines.append({
                    "planet":     planet,
                    "line_type":  line_type,
                    "strength":   strength,
                    "dasha_amp":  dasha_amp,
                    "final_score": final_score,
                    "theme":      meaning.get("theme", ""),
                    "energy":     meaning.get("energy", ""),
                    "caution":    meaning.get("caution", ""),
                })

        if city_score > 0.5:
            # Find the strongest matched line
            matched_lines.sort(key=lambda x: x["final_score"], reverse=True)
            best_line = matched_lines[0]
            dasha_note = ""
            if best_line["dasha_amp"]["amplified"]:
                dasha_note = (
                    f"⚡ {best_line['dasha_amp']['reason']} — "
                    f"this window is open {best_line['dasha_amp']['window']}"
                )

            recommendations.append({
                "city":         city,
                "base_score":   city_score,
                "concern":      concern,
                "planet":       best_line["planet"],
                "line_type":    best_line["line_type"],
                "theme":        best_line["theme"],
                "energy":       best_line["energy"],
                "caution":      best_line["caution"],
                "dasha_note":   dasha_note,
                "is_amplified": best_line["dasha_amp"]["amplified"],
                "urgency":      best_line["dasha_amp"]["urgency"],
                "window":       best_line["dasha_amp"]["window"],
                "life_areas":   list(set(life_areas)),
                "matched_lines": matched_lines,
            })

    # Apply patra filter
    recommendations = filter_by_patra(recommendations, patra)

    return recommendations[:limit]


# ── Prompt builder for astrocartography LLM response ─────────────────────────

def build_astrocartography_prompt(
    question: str,
    concern: str,
    current_city: str,
    current_location_reading: dict,
    top_cities: list[dict],
    patra=None,
    dashas: dict = None,
    language: str = "en",
) -> str:
    """
    Builds the LLM prompt for astrocartography readings.
    The LLM turns the raw city data into a warm, personal narrative.
    """
    patra_context = ""
    if patra:
        patra_context = (
            f"Person: {patra.age} years old, {patra.life_stage_name}, "
            f"{patra.marital_status}, {patra.career_stage}"
        )

    dasha_context = ""
    if dashas:
        vim = dashas.get("vimsottari", [{}])[0]
        dasha_context = (
            f"Active dasha: {vim.get('lord_or_sign', '?')} "
            f"until {vim.get('end', '?')[:7]}"
        )

    top_cities_text = ""
    for i, city in enumerate(top_cities[:5], 1):
        amp_note = f" [AMPLIFIED by dasha — {city['window']}]" if city["is_amplified"] else ""
        top_cities_text += (
            f"{i}. {city['city']}{amp_note}\n"
            f"   Line: {city['planet']} {city['line_type']} ({int(city['base_score']*100)}% strength)\n"
            f"   Theme: {city['theme']}\n"
            f"   Energy: {city['energy']}\n"
            f"   Watch: {city['caution']}\n\n"
        )

    current_lines_text = ""
    for line in current_location_reading.get("active_lines", [])[:3]:
        current_lines_text += (
            f"  {line['planet']} {line['line_type']}: {line['theme']} "
            f"(strength: {int(line['strength']*100)}%)\n"
        )

    return f"""You are Antar, an astrocartography guide combining Vedic astrology with location wisdom.

CONTEXT:
Concern: {concern}
{patra_context}
{dasha_context}

CURRENT LOCATION: {current_city}
Active planetary lines here:
{current_lines_text or "  No strong lines active here"}
Dasha alignment: {current_location_reading.get("dasha_alignment", "None")}

TOP CITIES FOR {concern.upper()}:
{top_cities_text}

QUESTION: {question}

INSTRUCTIONS:
1. Start by acknowledging what their CURRENT city offers or lacks for their concern.
   Be honest — if it's a weak location for what they want, say so kindly.

2. Describe the TOP 3 cities in order. For each:
   - Name the city and the planetary energy active there
   - Explain what that energy FEELS like in that city (not the planet name — the experience)
   - If dasha-amplified: make this URGENT and time-windowed
     ("This window is open until [date] — this is rare alignment")
   - Include one honest caution

3. If any cities have dasha amplification, emphasize the timing.
   Make clear this is a window, not permanent.

4. End with a direct recommendation:
   "For {concern} right now, the clearest signal points to [city]."
   Explain why in energy language.

RULES:
- Never use house numbers
- Translate all planetary names to energy language in the description
  (Jupiter = expansion/abundance energy, Venus = beauty/love energy, etc.)
- Keep planet names only in the technical data, not the narrative
- Be warm, specific, and personally relevant
- Mention the time window whenever dasha amplification exists
- Respond in {language}"""


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_location_summary(city: str, active_lines: list, dominant) -> str:
    if not dominant:
        return f"{city} sits in a neutral zone for your chart."

    amp = dominant["dasha_amp"]
    if amp["amplified"]:
        return (
            f"{city} activates your {dominant['theme'].lower()} energy "
            f"through a {dominant['planet']} {dominant['line_type']} line. "
            f"Crucially, {amp['reason']} — making this location particularly "
            f"powerful {amp['window']}."
        )
    return (
        f"{city} activates your {dominant['theme'].lower()} energy. "
        f"{dominant['energy']}"
    )


def _build_location_recommendations(active_lines: list, patra) -> str:
    if not active_lines:
        return "This is a neutral location. Your results here depend on your own effort."

    dominant = active_lines[0]
    if dominant["dasha_amp"]["amplified"] and dominant["dasha_amp"]["urgency"] == "NOW":
        return (
            f"This location is particularly powerful for you RIGHT NOW. "
            f"{dominant['dasha_amp']['reason']}. "
            f"This window is open {dominant['dasha_amp']['window']}. "
            f"Any action aligned with {dominant['theme'].lower()} "
            f"is amplified here during this period."
        )
    return (
        f"This location supports {dominant['theme'].lower()}. "
        f"{dominant['energy']} "
        f"Be aware: {dominant['caution']}"
    )
