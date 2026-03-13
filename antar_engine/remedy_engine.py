"""
antar_engine/remedy_engine.py

Remedy Selection Engine
──────────────────────────────────────────────────────────────────────
WHAT THIS FILE DOES:
  Given a domain (legal/wealth/health/marriage...) and the planets
  involved, selects the most appropriate remedies.

THE LOGIC:
  1. Find the weakest planet causing the problem
     (debilitated lord, afflicted karaka, wrong dasha lord)
  2. Find the strongest planet that can help
     (strong yoga lord, active dasha planet)
  3. Select remedies that:
     a. Strengthen the helping planet
     b. Pacify the hurting planet
     c. Are appropriate for the user's life stage (Patra)
     d. Are practical (not just "donate gold every day")

REMEDY TYPES:
  Mantra        → specific planet mantra + count + timing
  Gemstone      → which stone, which finger, which metal
  Fasting       → which day, what to avoid
  Charity       → what to donate, to whom, which day
  Ritual        → specific ritual aligned to the problem
  Color therapy → what colors to wear/use
  Food          → dietary adjustments
  Direction     → which direction to face for prayer/work

PATRA FILTER:
  Young student → simple mantras, no expensive gemstones
  Entrepreneur  → actionable, time-efficient remedies
  Senior person → devotional, gentler practices
  Health issue  → no fasting, gentle practices only
"""

from __future__ import annotations
from antar_engine.d_charts_calculator import (
    SIGN_LORDS, OWN_SIGNS, EXALTATION, DEBILITATION,
    get_house_lord, NATURAL_BENEFICS, NATURAL_MALEFICS,
)


# ── Planet remedy database ────────────────────────────────────────────────────

PLANET_REMEDIES = {
    "Sun": {
        "mantra":       "Om Hraam Hreem Hraum Sah Suryaya Namaha",
        "simple_mantra": "Om Suryaya Namaha",
        "count":        108,
        "best_time":    "Sunrise, facing East",
        "best_day":     "Sunday",
        "fasting_day":  "Sunday (skip oily food)",
        "gemstone":     "Ruby",
        "metal":        "Gold",
        "finger":       "Ring finger",
        "charity":      "Donate wheat, jaggery, or copper items on Sunday",
        "color":        "Saffron, orange, gold",
        "direction":    "East",
        "food":         "Wheat, saffron, red lentils",
        "ritual":       "Light a lamp with ghee at sunrise, recite the mantra 108 times",
        "strengthens":  ["authority", "vitality", "confidence", "leadership", "father relationship"],
        "pacifies":     ["ego", "arrogance", "career blockages", "father issues", "government trouble"],
    },
    "Moon": {
        "mantra":       "Om Shraam Shreem Shraum Sah Chandraya Namaha",
        "simple_mantra": "Om Chandraya Namaha",
        "count":        108,
        "best_time":    "Moonrise or evening",
        "best_day":     "Monday",
        "fasting_day":  "Monday (white food only)",
        "gemstone":     "Pearl or Moonstone",
        "metal":        "Silver",
        "finger":       "Little finger",
        "charity":      "Donate milk, white rice, or white cloth on Monday",
        "color":        "White, silver, cream",
        "direction":    "Northwest",
        "food":         "Milk, white rice, coconut, white sesame",
        "ritual":       "Offer milk to Shiva on Mondays. Keep a silver bowl of water at the bedside.",
        "strengthens":  ["emotional balance", "intuition", "public connection", "mind", "mother relationship"],
        "pacifies":     ["anxiety", "emotional instability", "insomnia", "relationship issues", "mother issues"],
    },
    "Mars": {
        "mantra":       "Om Kraam Kreem Kraum Sah Bhaumaya Namaha",
        "simple_mantra": "Om Angarakaya Namaha",
        "count":        108,
        "best_time":    "Sunrise or early morning",
        "best_day":     "Tuesday",
        "fasting_day":  "Tuesday (no meat, no alcohol)",
        "gemstone":     "Red Coral",
        "metal":        "Copper",
        "finger":       "Ring finger",
        "charity":      "Donate red lentils, red cloth, or copper items on Tuesday",
        "color":        "Red, orange, copper",
        "direction":    "South",
        "food":         "Red lentils, beets, pomegranate",
        "ritual":       "Offer red flowers to Hanuman or Kartikeya on Tuesday",
        "strengthens":  ["courage", "energy", "action", "entrepreneurship", "legal fighting spirit"],
        "pacifies":     ["aggression", "accidents", "legal problems", "blood disorders", "property disputes"],
    },
    "Mercury": {
        "mantra":       "Om Braam Breem Braum Sah Budhaya Namaha",
        "simple_mantra": "Om Budhaya Namaha",
        "count":        108,
        "best_time":    "Early morning",
        "best_day":     "Wednesday",
        "fasting_day":  "Wednesday (green vegetables only)",
        "gemstone":     "Emerald or Green Tourmaline",
        "metal":        "Gold or Silver",
        "finger":       "Little finger",
        "charity":      "Donate green vegetables, green cloth, or books on Wednesday",
        "color":        "Green, lime, teal",
        "direction":    "North",
        "food":         "Green vegetables, moong dal, spinach",
        "ritual":       "Read or write something meaningful every Wednesday morning",
        "strengthens":  ["intellect", "communication", "business", "education", "learning"],
        "pacifies":     ["nervous system issues", "communication blocks", "business problems", "education delays"],
    },
    "Jupiter": {
        "mantra":       "Om Graam Greem Graum Sah Gurave Namaha",
        "simple_mantra": "Om Gurave Namaha",
        "count":        108,
        "best_time":    "Sunrise or early morning",
        "best_day":     "Thursday",
        "fasting_day":  "Thursday (yellow food, no salt)",
        "gemstone":     "Yellow Sapphire or Citrine",
        "metal":        "Gold",
        "finger":       "Index finger",
        "charity":      "Donate yellow items, turmeric, or feed a Brahmin on Thursday",
        "color":        "Yellow, gold, saffron",
        "direction":    "Northeast",
        "food":         "Chickpeas, turmeric, yellow lentils, banana",
        "ritual":       "Light a ghee lamp at sunrise. Recite mantra. Give thanks before eating.",
        "strengthens":  ["wisdom", "wealth", "children", "health", "legal protection", "marriage"],
        "pacifies":     ["financial problems", "legal issues", "relationship problems", "health issues", "lack of children"],
    },
    "Venus": {
        "mantra":       "Om Draam Dreem Draum Sah Shukraya Namaha",
        "simple_mantra": "Om Shukraya Namaha",
        "count":        108,
        "best_time":    "Evening, at sunset",
        "best_day":     "Friday",
        "fasting_day":  "Friday (light food, no meat)",
        "gemstone":     "Diamond or White Sapphire or Zircon",
        "metal":        "Silver or Platinum",
        "finger":       "Middle finger",
        "charity":      "Donate white sweets, white cloth, or perfume on Friday",
        "color":        "White, pink, cream, pastels",
        "direction":    "Southeast",
        "food":         "White rice, milk sweets, white beans",
        "ritual":       "Offer white flowers to a goddess on Friday. Wear clean white or pink.",
        "strengthens":  ["love", "beauty", "wealth", "relationships", "creativity", "marriage"],
        "pacifies":     ["relationship problems", "marriage delays", "financial issues", "creative blocks"],
    },
    "Saturn": {
        "mantra":       "Om Praam Preem Praum Sah Shanaischaraya Namaha",
        "simple_mantra": "Om Shanaischaraya Namaha",
        "count":        108,
        "best_time":    "Sunset or evening",
        "best_day":     "Saturday",
        "fasting_day":  "Saturday (black sesame, no oil)",
        "gemstone":     "Blue Sapphire (only with expert consultation)",
        "metal":        "Iron or Lead",
        "finger":       "Middle finger",
        "charity":      "Donate black sesame, black cloth, or iron items on Saturday. Feed the poor.",
        "color":        "Black, dark blue, grey",
        "direction":    "West",
        "food":         "Black sesame, black lentils, dark leafy greens",
        "ritual":       "Light sesame oil lamp on Saturday evening. Serve the elderly or needy.",
        "strengthens":  ["discipline", "patience", "career foundation", "karma resolution"],
        "pacifies":     ["delays", "obstacles", "chronic health", "legal problems", "career blocks", "Saturn transit effects"],
    },
    "Rahu": {
        "mantra":       "Om Bhraam Bhreem Bhraum Sah Rahave Namaha",
        "simple_mantra": "Om Rahave Namaha",
        "count":        108,
        "best_time":    "Dusk",
        "best_day":     "Saturday (some traditions: Wednesday)",
        "fasting_day":  "Saturday",
        "gemstone":     "Hessonite Garnet (Gomed)",
        "metal":        "Silver or Mixed metals",
        "finger":       "Middle finger",
        "charity":      "Donate coal, mustard, or black sesame on Saturday",
        "color":        "Smoky grey, dark blue, indigo",
        "direction":    "Southwest",
        "food":         "Mustard, sesame, radish",
        "ritual":       "Offer coconut and flowers at Durga temple on Saturday. Chant Durga Chalisa.",
        "strengthens":  ["ambition", "foreign connections", "unconventional success", "disruption"],
        "pacifies":     ["sudden reversal", "obsession", "illusion", "foreign obstacles", "Rahu dasha effects"],
    },
    "Ketu": {
        "mantra":       "Om Sraam Sreem Sraum Sah Ketave Namaha",
        "simple_mantra": "Om Ketave Namaha",
        "count":        108,
        "best_time":    "Dawn",
        "best_day":     "Tuesday (some traditions: Saturday)",
        "fasting_day":  "Tuesday",
        "gemstone":     "Cat's Eye (Vaidurya)",
        "metal":        "Silver",
        "finger":       "Ring finger",
        "charity":      "Donate sesame, blankets, or feed dogs on Tuesday",
        "color":        "Smoky grey, brown, maroon",
        "direction":    "Northwest",
        "food":         "Sesame, multi-grain",
        "ritual":       "Offer grey flowers to Ganesha or Bhairava. Practice silence for one hour.",
        "strengthens":  ["spiritual depth", "detachment", "past-life expertise", "liberation"],
        "pacifies":     ["confusion", "sudden loss", "detachment from life", "Ketu dasha isolation"],
    },
}


# ── Domain → which planets to remedy ─────────────────────────────────────────

DOMAIN_REMEDY_FOCUS = {
    "wealth": {
        "strengthen":   ["Jupiter", "Venus"],
        "pacify":       ["Saturn"],
        "primary_note": "Strengthen the wealth planets, pacify delay planets",
    },
    "billionaire": {
        "strengthen":   ["Jupiter", "Sun", "Rahu"],
        "pacify":       ["Saturn"],
        "primary_note": "Amplify the power and wealth planets",
    },
    "funding": {
        "strengthen":   ["Jupiter", "Rahu", "Mercury"],
        "pacify":       ["Saturn"],
        "primary_note": "Build trust energy (Jupiter) and opportunity energy (Rahu)",
    },
    "legal": {
        "strengthen":   ["Jupiter", "Mars"],
        "pacify":       ["Saturn", "Rahu"],
        "primary_note": "Justice (Jupiter) and fighting spirit (Mars) need amplification",
    },
    "health": {
        "strengthen":   ["Jupiter", "Moon", "Sun"],
        "pacify":       ["Saturn", "Rahu"],
        "primary_note": "Strengthen the healing planets, reduce the chronic/delay planets",
    },
    "marriage": {
        "strengthen":   ["Venus", "Jupiter"],
        "pacify":       ["Saturn", "Rahu"],
        "primary_note": "Love and expansion energy (Venus + Jupiter) must be strengthened",
    },
    "children": {
        "strengthen":   ["Jupiter", "Moon"],
        "pacify":       ["Saturn", "Rahu"],
        "primary_note": "Jupiter is the putrakaraka — strengthen it first",
    },
    "property": {
        "strengthen":   ["Mars", "Jupiter"],
        "pacify":       ["Rahu"],
        "primary_note": "Mars activates property, Jupiter brings good deals",
    },
    "foreign": {
        "strengthen":   ["Rahu", "Jupiter"],
        "pacify":       ["Moon", "Ketu"],
        "primary_note": "Open the foreign doors (Rahu + Jupiter)",
    },
    "education": {
        "strengthen":   ["Mercury", "Jupiter"],
        "pacify":       ["Saturn", "Rahu"],
        "primary_note": "Intellect (Mercury) and wisdom (Jupiter) must be at peak",
    },
    "career": {
        "strengthen":   ["Sun", "Saturn", "Mercury"],
        "pacify":       ["Rahu"],
        "primary_note": "Authority (Sun), discipline (Saturn), communication (Mercury)",
    },
}


# ── Remedy builder ────────────────────────────────────────────────────────────

def select_remedies(
    domain: str,
    chart_data: dict,
    dashas: dict,
    patra=None,
    weak_planets: list[str] = None,
    limit: int = 3,
) -> list[dict]:
    """
    Select the most appropriate remedies for a given domain.

    Logic:
    1. Get the planets to strengthen/pacify for this domain
    2. Add the active dasha lord if it's weak
    3. Add the house lord of the relevant house if it's weak
    4. Filter by patra (what's practical for this person's life)
    5. Return the top 3 remedies

    Args:
        domain:         "wealth" | "legal" | "health" | "marriage" etc.
        chart_data:     from DB
        dashas:         from DB
        patra:          life circumstances (optional)
        weak_planets:   override — specific planets detected as weak
        limit:          max remedies to return

    Returns:
        List of remedy dicts ready for the frontend and LLM
    """
    planets    = chart_data["planets"]
    lagna_sign = chart_data["lagna"]["sign"]
    config     = DOMAIN_REMEDY_FOCUS.get(domain, DOMAIN_REMEDY_FOCUS["career"])

    # Build planet priority list
    to_strengthen = list(config.get("strengthen", []))
    to_pacify     = list(config.get("pacify", []))

    # Add the active dasha lord
    current_dasha = dashas.get("vimsottari", [{}])[0].get("lord_or_sign", "")
    if current_dasha and current_dasha not in to_strengthen:
        planet_sign = planets.get(current_dasha, {}).get("sign", "")
        if planet_sign == DEBILITATION.get(current_dasha, ""):
            to_pacify.insert(0, current_dasha)   # weak dasha lord → pacify first

    # Add specific weak planets detected by yoga engine
    if weak_planets:
        for p in weak_planets:
            if p not in to_strengthen and p not in to_pacify:
                to_pacify.append(p)

    # Build remedy list
    remedies = []

    # Primary: strengthen planets
    for planet in to_strengthen[:2]:
        remedy = _build_remedy(
            planet=planet,
            remedy_type="strengthen",
            domain=domain,
            patra=patra,
        )
        if remedy:
            remedies.append(remedy)

    # Secondary: pacify planets
    for planet in to_pacify[:1]:
        remedy = _build_remedy(
            planet=planet,
            remedy_type="pacify",
            domain=domain,
            patra=patra,
        )
        if remedy:
            remedies.append(remedy)

    return remedies[:limit]


def _build_remedy(
    planet: str,
    remedy_type: str,   # "strengthen" | "pacify"
    domain: str,
    patra=None,
) -> dict | None:
    """Build a single remedy dict."""
    data = PLANET_REMEDIES.get(planet)
    if not data:
        return None

    # Patra filter
    is_student   = getattr(patra, "career_stage", "") == "student"
    is_elderly   = getattr(patra, "age", 30) > 65
    has_health   = getattr(patra, "health_status", "") in ("chronic", "recovery")
    is_busy_exec = getattr(patra, "career_stage", "") in ("senior_career", "entrepreneur")

    # Gemstone advice
    gemstone = data["gemstone"]
    if is_student:
        gemstone = f"{gemstone} (alternative: {data.get('simple_mantra','')} — affordable option)"
    if planet == "Saturn" and "Blue Sapphire" in gemstone:
        gemstone = "Blue Sapphire — ONLY after consultation with an expert astrologer. Can backfire."

    # Fasting adjustment
    fasting = data["fasting_day"]
    if has_health:
        fasting = f"Skip fasting (health condition). Do mantra instead."

    # Choose mantra based on proficiency
    mantra = data["simple_mantra"] if is_student or is_elderly else data["mantra"]

    return {
        "planet":       planet,
        "type":         remedy_type,
        "domain":       domain,
        "mantra":       mantra,
        "full_mantra":  data["mantra"],
        "count":        data["count"],
        "best_time":    data["best_time"],
        "best_day":     data["best_day"],
        "fasting":      fasting,
        "gemstone":     gemstone,
        "metal":        data["metal"],
        "finger":       data["finger"],
        "charity":      data["charity"],
        "color":        data["color"],
        "direction":    data["direction"],
        "food":         data["food"],
        "ritual":       data["ritual"],
        "purpose":      (
            f"Strengthens {', '.join(data['strengthens'][:3])}"
            if remedy_type == "strengthen" else
            f"Pacifies {', '.join(data['pacifies'][:3])}"
        ),
        "energy_language": _get_energy_language(planet, remedy_type, domain),
    }


def _get_energy_language(planet: str, remedy_type: str, domain: str) -> str:
    """Human-friendly description of what this remedy does."""
    energy_descriptions = {
        "Jupiter": {
            "strengthen": "Opens the channels of wisdom, trust, and abundance. Jupiter's expansion energy supports growth in all areas.",
            "pacify":     "Calms over-expansion and brings measured wisdom rather than excess.",
        },
        "Venus": {
            "strengthen": "Activates love, beauty, and graceful prosperity. Venus brings harmony and magnetic attraction.",
            "pacify":     "Calms excessive desire and brings contentment and balance in relationships.",
        },
        "Mars": {
            "strengthen": "Builds courage, action energy, and fighting spirit. Mars gives you the will to push through obstacles.",
            "pacify":     "Reduces aggression and accident-prone energy. Channels the warrior energy productively.",
        },
        "Mercury": {
            "strengthen": "Sharpens the mind, improves communication, and opens business channels.",
            "pacify":     "Calms nervous energy and scattered thinking. Brings focused clarity.",
        },
        "Moon": {
            "strengthen": "Nourishes emotional wellbeing, intuition, and public connection.",
            "pacify":     "Calms emotional turbulence and restores inner peace.",
        },
        "Sun": {
            "strengthen": "Builds confidence, authority, and vitality. The inner light grows brighter.",
            "pacify":     "Calms ego and reduces pride. Brings humble authority.",
        },
        "Saturn": {
            "strengthen": "Builds patience, discipline, and the ability to sustain long-term effort.",
            "pacify":     "Eases delays, reduces obstacles, and softens Saturn's hard lessons.",
        },
        "Rahu": {
            "strengthen": "Amplifies ambition, foreign connections, and unconventional opportunities.",
            "pacify":     "Reduces obsessive patterns and brings grounded clarity to Rahu's illusions.",
        },
        "Ketu": {
            "strengthen": "Deepens spiritual insight and activates past-life expertise.",
            "pacify":     "Reduces detachment and confusion. Grounds the spiritual energy.",
        },
    }
    planet_desc = energy_descriptions.get(planet, {})
    return planet_desc.get(remedy_type, f"Works with {planet} energy for {domain}.")


def remedies_to_context_block(remedies: list[dict]) -> str:
    """Format remedies for the LLM prompt."""
    if not remedies:
        return "REMEDIES: No specific remedies identified for this query."

    lines = ["═══ REMEDIES ═══"]
    for i, r in enumerate(remedies, 1):
        lines += [
            f"{i}. {r['planet']} — {r['energy_language']}",
            f"   Mantra: {r['mantra']} (×{r['count']}, {r['best_time']})",
            f"   Day: {r['best_day']} | Charity: {r['charity']}",
            f"   Color: {r['color']} | Direction: {r['direction']}",
            f"   Ritual: {r['ritual']}",
            "",
        ]
    lines.append("INSTRUCTION: Present remedies warmly as 'working with energy consciously.'")
    lines.append("Never say 'you must do this.' Frame as invitation, not obligation.")
    lines.append("Translate all planetary names to energy language in the response.")
    return "\n".join(lines)
