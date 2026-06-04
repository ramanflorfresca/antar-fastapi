"""
Antar Prashna (Horary) Engine
=============================
Cast a Moment Chart for the exact second a question is asked,
then compute a probabilistic YES/NO verdict using:
  Step A — Lagna Strength (+25%)
  Step B — Lord Connection (+25%)
  Step C — Ithasala / Ishrafa Verdict (+35% / -35%)
  Step D — Moon Validation (+15%)
  Edge Cases — Muthashila (override 95%), Nakta (+25%), Yamaya (+20%)
  Bonus — Mutual Reception (+15%), Jaimini Triple-Lock (+5% each)

Author: Antar Engine Team
Date: April 2026
"""

import math
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List, Tuple

try:
    import swisseph as swe
except ImportError:
    swe = None  # Will be available on Railway

logger = logging.getLogger("antar.prashna")

# --- Language Utils (Sprint L) ---
try:
    from language_utils import build_language_instruction
except ImportError:
    def build_language_instruction(lang="en"): return ""  # fallback


# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANETS = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn"
}

# Swiss Ephemeris planet IDs
SWE_PLANETS = {
    "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3,
    "Mars": 4, "Jupiter": 5, "Saturn": 6
}

# Nakshatras (27)
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# Sign lords (Vedic — traditional rulerships)
SIGN_LORDS = {
    0: 4,   # Aries → Mars
    1: 3,   # Taurus → Venus
    2: 2,   # Gemini → Mercury
    3: 1,   # Cancer → Moon
    4: 0,   # Leo → Sun
    5: 2,   # Virgo → Mercury
    6: 3,   # Libra → Venus
    7: 4,   # Scorpio → Mars
    8: 5,   # Sagittarius → Jupiter
    9: 6,   # Capricorn → Saturn
    10: 6,  # Aquarius → Saturn
    11: 5,  # Pisces → Jupiter
}

# Natural benefics
BENEFIC_IDS = {3, 5, 2}  # Venus, Jupiter, Mercury

# Tajika orbs (degrees)
TAJIKA_ORBS = {
    "Sun": 15, "Moon": 12, "Mars": 8, "Mercury": 7,
    "Jupiter": 9, "Venus": 7, "Saturn": 9
}

# Tajika aspect angles
TAJIKA_ASPECTS = [0, 60, 90, 120, 180]

# Rashi Drishti — Jaimini sign aspects
# Movable signs aspect Fixed (except adjacent), Fixed aspect Movable (except adjacent),
# Dual aspects Dual
RASHI_DRISHTI = {
    0: [4, 7, 10],    # Aries → Leo, Scorpio, Aquarius
    1: [3, 8, 11],    # Taurus → Cancer, Sagittarius, Pisces (actually: 3,8,11 from mapping)
    2: [5, 6, 9],     # Gemini → Virgo, Libra, Capricorn (actually: 5,8,11 — let me fix)
    3: [1, 6, 9],     # Cancer
    4: [0, 7, 10],    # Leo
    5: [2, 8, 11],    # Virgo
    6: [0, 3, 10],    # Libra
    7: [1, 4, 11],    # Scorpio (actually: 1,4,11)
    8: [2, 5, 10],    # Sagittarius (actually: needs dual→dual check)
    9: [3, 6, 11],    # Capricorn (actually: 3,6 — let me use standard)
    10: [0, 4, 7],    # Aquarius
    11: [1, 5, 8],    # Pisces
}
# NOTE: Using standard Jaimini Rashi Drishti as implemented in jaimini_engine.py.
# Movable(0,3,6,9) aspects Fixed(1,4,7,10) except adjacent.
# Fixed aspects Movable except adjacent.
# Dual(2,5,8,11) aspects other Duals.

def get_rashi_drishti(sign_idx: int) -> List[int]:
    """Return list of sign indices that this sign aspects via Rashi Drishti."""
    sign_type = sign_idx % 3  # 0=movable, 1=fixed, 2=dual
    if sign_type == 0:  # Movable — aspects all Fixed except adjacent
        fixed = [1, 4, 7, 10]
        adjacent = (sign_idx + 1) % 12
        return [s for s in fixed if s != adjacent]
    elif sign_type == 1:  # Fixed — aspects all Movable except adjacent
        movable = [0, 3, 6, 9]
        adjacent = (sign_idx - 1) % 12
        return [s for s in movable if s != adjacent]
    else:  # Dual — aspects other Duals
        dual = [2, 5, 8, 11]
        return [s for s in dual if s != sign_idx]


# Domain → House of Interest mapping
DOMAIN_HOUSE_MAP = {
    "career":       [10],
    "job":          [10],
    "promotion":    [10],
    "promoted":     [10],
    "raise":        [10],
    "business":     [7, 10],
    "finance":      [2, 11],
    "money":        [2, 11],
    "investment":   [2, 11],
    "funding":      [8, 11],
    "fund":         [8, 11],
    "loan":         [8, 11],
    "equity":       [8, 11],
    "investor":     [8, 11],
    "series":       [8, 11],
    "raise":        [8, 11],
    "wealth":       [2, 11],
    "purpose":      [9, 10],
    "direction":    [9, 10],
    "relationship": [7],
    "marriage":     [7],
    "love":         [7],
    "partner":      [7],
    "health":       [6],
    "surgery":      [6, 8],
    "illness":      [6],
    "education":    [4, 5],
    "exam":         [5],
    "study":        [4, 5],
    "travel":       [9, 12],
    "abroad":       [9, 12],
    "visa":         [9, 12],
    "move":         [4, 9],
    "legal":        [6, 7],
    "court":        [6, 7],
    "lawsuit":      [6, 7],
    "children":     [5],
    "baby":         [5],
    "pregnancy":    [5],
    "property":     [4],
    "house":        [4],
    "real estate":  [4],
    "land":         [4],
}

# YES/NO intent patterns
PRASHNA_PATTERNS = [
    re.compile(r"\b(will|shall)\s+(i|my|we|this|it|he|she|they)\b", re.I),
    re.compile(r"\bshould\s+(i|we)\b", re.I),
    re.compile(r"\b(is|are|was)\s+(it|this|that|there|he|she)\b", re.I),
    re.compile(r"\b(can|am)\s+i\b", re.I),
    re.compile(r"\b(yes[\s/\-]?no|good\s+time|right\s+decision|right\s+move)\b", re.I),
    re.compile(r"\b(do\s+i|does\s+this|would\s+it)\b", re.I),
    re.compile(r"\bgive\s+me\s+a\s+yes\b", re.I),
]

# Cooldown: once per day (24 hours). Configurable.
PRASHNA_COOLDOWN_HOURS = 24

# ═══ PRASHNA V2: DOMAIN INTELLIGENCE PATCH ═══
# Added: Domain Audit, Proof Bars, Intent-Birth Sync

# Exaltation signs (sign index where planet is exalted)
EXALTATION_SIGNS = {
    0: 0,   # Sun → Aries
    1: 1,   # Moon → Taurus
    2: 5,   # Mercury → Virgo
    3: 11,  # Venus → Pisces
    4: 9,   # Mars → Capricorn
    5: 3,   # Jupiter → Cancer
    6: 6,   # Saturn → Libra
}

DEBILITATION_SIGNS = {k: (v + 6) % 12 for k, v in EXALTATION_SIGNS.items()}

COMBUSTION_ORB = 8.0
ANGLE_HOUSES = [1, 4, 7, 10]

# Domain → Audit Configuration (4 core domains from spec)
DOMAIN_AUDIT_CONFIG = {
    "finance": {
        "primary_house": 8, "secondary_house": 11,
        "label": "CAPITAL AUDIT",
        "house_label": "Other People\'s Money · Liquid Gains",
        "rules": [
            {"check": "retrograde_lord", "house": 8, "penalty": -20,
             "message": "Terms will be renegotiated at the 11th hour. Watch the fine print."},
            {"check": "combust_lord", "house": 8, "penalty": -30,
             "message": "Funding source is burnt out or lacks the actual liquidity they claim."},
            {"check": "exalted_lord", "house": 8, "bonus": 15,
             "message": "Capital is high-quality — investor brings more than just cash."},
        ],
    },
    "investment": {
        "primary_house": 8, "secondary_house": 11,
        "label": "CAPITAL AUDIT",
        "house_label": "Other People\'s Money · Liquid Gains",
        "rules": [
            {"check": "retrograde_lord", "house": 8, "penalty": -20,
             "message": "Terms will be renegotiated. Watch the fine print."},
            {"check": "combust_lord", "house": 8, "penalty": -30,
             "message": "Funding source lacks actual liquidity."},
            {"check": "exalted_lord", "house": 8, "bonus": 15,
             "message": "Capital is high-quality — investor brings more than cash."},
        ],
    },
    "money": {
        "primary_house": 2, "secondary_house": 11,
        "label": "CAPITAL AUDIT",
        "house_label": "Personal Wealth · Liquid Gains",
        "rules": [
            {"check": "retrograde_lord", "house": 2, "penalty": -20,
             "message": "Income flow is delayed or terms will shift."},
            {"check": "exalted_lord", "house": 2, "bonus": 15,
             "message": "Strong earning potential — money comes with authority."},
        ],
    },
    "wealth": {
        "primary_house": 2, "secondary_house": 11,
        "label": "CAPITAL AUDIT",
        "house_label": "Personal Wealth · Liquid Gains",
        "rules": [
            {"check": "retrograde_lord", "house": 2, "penalty": -20,
             "message": "Income flow delayed."},
            {"check": "exalted_lord", "house": 2, "bonus": 15,
             "message": "Strong earning energy."},
        ],
    },
    "career": {
        "primary_house": 10, "secondary_house": 6,
        "label": "POWER AUDIT",
        "house_label": "Status & Rank · Competition",
        "rules": [
            {"check": "lagna_connection", "house": 10, "bonus": 25,
             "message": "You are the natural choice. The role is seeking you."},
            {"check": "sixth_pressure", "house": 10, "penalty": -15,
             "message": "Competition is too high. Even with a yes, expect internal politics."},
            {"check": "saturn_aspect", "house": 10, "delay_days": 30,
             "message": "A yes, but the administrative paperwork will crawl. Don\'t resign yet."},
        ],
    },
    "job": {
        "primary_house": 10, "secondary_house": 6,
        "label": "POWER AUDIT",
        "house_label": "Status & Rank · Competition",
        "rules": [
            {"check": "lagna_connection", "house": 10, "bonus": 25,
             "message": "You are the natural choice. The job is seeking you."},
            {"check": "sixth_pressure", "house": 10, "penalty": -15,
             "message": "Competition is high. Expect internal resistance."},
            {"check": "saturn_aspect", "house": 10, "delay_days": 30,
             "message": "Administrative paperwork will crawl. Don\'t resign yet."},
        ],
    },
    "promotion": {
        "primary_house": 10, "secondary_house": 6,
        "label": "POWER AUDIT",
        "house_label": "Status & Rank · Competition",
        "rules": [
            {"check": "lagna_connection", "house": 10, "bonus": 25,
             "message": "You are the natural choice for this elevation."},
            {"check": "sixth_pressure", "house": 10, "penalty": -15,
             "message": "Someone else is also being considered. Brace for competition."},
        ],
    },
    "relationship": {
        "primary_house": 7, "secondary_house": 12,
        "label": "SYNC AUDIT",
        "house_label": "The Partner · Distance & Exit",
        "rules": [
            {"check": "twelfth_house_leak", "house": 7, "penalty": -40,
             "message": "The partner is emotionally or physically checked out. They are looking for the exit."},
            {"check": "stationary_lord", "house": 7, "verdict_override": "UNCERTAIN",
             "message": "The partner is paralyzed. They cannot make a decision right now. Re-calculate in 72 hours."},
            {"check": "venus_angle", "bonus": 20,
             "message": "There is still surface harmony to work with. A yes is sustainable."},
        ],
    },
    "marriage": {
        "primary_house": 7, "secondary_house": 12,
        "label": "SYNC AUDIT",
        "house_label": "The Partner · Distance & Exit",
        "rules": [
            {"check": "twelfth_house_leak", "house": 7, "penalty": -40,
             "message": "The other person is emotionally checked out."},
            {"check": "stationary_lord", "house": 7, "verdict_override": "UNCERTAIN",
             "message": "They cannot commit right now. Revisit in 72 hours."},
            {"check": "venus_angle", "bonus": 20,
             "message": "Surface harmony exists. The connection can be rebuilt."},
        ],
    },
    "love": {
        "primary_house": 7, "secondary_house": 12,
        "label": "SYNC AUDIT",
        "house_label": "The Partner · Distance & Exit",
        "rules": [
            {"check": "twelfth_house_leak", "house": 7, "penalty": -40,
             "message": "The other person is emotionally distant."},
            {"check": "venus_angle", "bonus": 20,
             "message": "Attraction is still active. The connection has life."},
        ],
    },
    "legal": {
        "primary_house": 6, "secondary_house": 7,
        "label": "CONFLICT AUDIT",
        "house_label": "The Opponent · The Court",
        "rules": [
            {"check": "retrograde_opponent", "house": 6, "bonus": 25,
             "message": "The opponent is losing their nerve or their evidence is faulty. They will settle."},
            {"check": "mars_aspect_sixth", "severity": "aggression",
             "message": "This will not be a quiet settlement. Expect a scorched-earth battle."},
            {"check": "seventh_lord_strength", "house": 7,
             "message_strong": "The system will work as intended. No backdoor deals.",
             "message_weak": "The arbitrator or judge may be compromised or distracted."},
        ],
    },
    "lawsuit": {
        "primary_house": 6, "secondary_house": 7,
        "label": "CONFLICT AUDIT",
        "house_label": "The Opponent · The Court",
        "rules": [
            {"check": "retrograde_opponent", "house": 6, "bonus": 25,
             "message": "The opponent\'s case has weaknesses. They will settle."},
            {"check": "mars_aspect_sixth", "severity": "aggression",
             "message": "This will escalate. Prepare for a prolonged fight."},
        ],
    },
    "court": {
        "primary_house": 6, "secondary_house": 7,
        "label": "CONFLICT AUDIT",
        "house_label": "The Opponent · The Court",
        "rules": [
            {"check": "retrograde_opponent", "house": 6, "bonus": 25,
             "message": "The other side\'s position is weakening."},
            {"check": "seventh_lord_strength", "house": 7,
             "message_strong": "Fair outcome expected.",
             "message_weak": "Process may be biased or slow."},
        ],
    },
}

DEFAULT_AUDIT_CONFIG = {
    "primary_house": 10, "secondary_house": 1,
    "label": "GENERAL AUDIT", "house_label": "Status · Self",
    "rules": [],
}


# ═══ E1: EMOTIONAL INTELLIGENCE LAYER ═══
# Detects emotional state from question text and adapts Claude's tone.
# Does NOT change the verdict or score — only the delivery.

EMOTIONAL_KEYWORDS = {
    "desperate": [
        "ever find", "never find", "always alone", "no one", "give up", "hopeless",
        "scared", "afraid", "terrified", "panic", "anxiety", "depressed",
        "crying", "broken", "lost everything", "stuck forever", "worth it",
        "will i ever", "am i doomed", "no hope", "cant take", "falling apart",
        "will things ever", "is there any hope", "feel so alone",
    ],
    "hopeful": [
        "finally", "dream come true", "hoping", "praying", "please tell me",
        "is there a chance", "possible", "one day", "meant to be", "destiny",
        "will my luck", "turning point", "light at the end", "things looking up",
    ],
    "angry": [
        "unfair", "betrayed", "cheated", "lied to", "robbed", "screwed",
        "revenge", "justice", "punish", "how dare", "sick of", "fed up",
        "they ruined", "backstabbed", "stolen from me",
    ],
}

# Business phrases that contain emotional words but aren't emotional
EMOTION_EXCLUSIONS = [
    "dying to close", "killing it", "crushing it", "scared money",
    "afraid of missing", "lost opportunity", "broken deal",
]


def detect_emotional_tone(question: str) -> str:
    """
    Detect emotional state from question text.
    Returns: "desperate" | "hopeful" | "angry" | "neutral"

    Checks exclusions first to avoid false positives on business jargon.
    """
    q = question.lower()

    # Check exclusions — business phrases that look emotional but aren't
    for exclusion in EMOTION_EXCLUSIONS:
        if exclusion in q:
            return "neutral"

    # Check emotional keywords
    for tone, keywords in EMOTIONAL_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return tone

    return "neutral"


def get_time_modifier(hour_utc: int) -> str:
    """
    Detect late-night queries (0-5 AM UTC).
    Returns: "late_night" | "normal"

    Late-night questions get warmer tone — someone reaching out at 2am
    is probably anxious or can't sleep.
    """
    if 0 <= hour_utc < 6:
        return "late_night"
    return "normal"


def build_emotional_prompt_block(tone: str, time_mod: str) -> str:
    """
    Build the prompt injection block for Claude based on detected emotion.
    Returns empty string for neutral tone (no injection needed).
    """
    blocks = []

    if tone == "desperate":
        blocks.append(
            "EMOTIONAL CONTEXT: The user is in emotional distress. "
            "Lead with acknowledgment — one sentence that shows you hear them. "
            "Use softer language: 'the energy suggests' instead of 'the verdict is'. "
            "If the answer is difficult, frame it as 'not yet' rather than 'no'. "
            "End with grounding: a concrete small step they can take TODAY. "
            "Never dismiss their feelings. Never use platitudes. "
            "The verdict doesn't change — only the delivery."
        )
    elif tone == "hopeful":
        blocks.append(
            "EMOTIONAL CONTEXT: The user is carrying hope. Honor it. "
            "Don't inflate expectations but don't crush them either. "
            "If the verdict is negative, frame it as timing — 'the window isn't open yet' "
            "rather than a flat no. End with what they CAN do now to prepare. "
            "Match their energy without overpromising."
        )
    elif tone == "angry":
        blocks.append(
            "EMOTIONAL CONTEXT: The user is angry. Don't match the energy. "
            "Don't dismiss it either. Validate the feeling in ONE sentence, "
            "then pivot to what the data actually shows. "
            "Frame THE MOVE as reclaiming power and clarity, not seeking revenge. "
            "Be direct, not clinical."
        )

    if time_mod == "late_night":
        blocks.append(
            "TIME CONTEXT: The user is reaching out late at night. "
            "This suggests urgency or insomnia. Be warm but grounding. "
            "Keep it concise — they need clarity, not a lecture. "
            "Don't add more to worry about."
        )

    if blocks:
        return "\n\n" + "\n".join(blocks) + "\n"
    return ""


BIRTH_POWER_HOUSES = {
    "career": 10, "job": 10, "promotion": 10, "business": 10,
    "finance": 2, "money": 2, "investment": 8, "wealth": 2,
    "relationship": 7, "marriage": 7, "love": 5, "partner": 7,
    "health": 6, "surgery": 8, "illness": 6,
    "education": 5, "exam": 5, "study": 4,
    "travel": 9, "abroad": 9, "visa": 9,
    "legal": 6, "court": 7, "lawsuit": 6,
    "children": 5, "baby": 5, "pregnancy": 5,
    "property": 4, "house": 4, "land": 4,
    "general": 10,
}



# ═══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def sign_name(idx: int) -> str:
    return SIGNS[idx % 12]

def planet_name_from_id(pid: int) -> str:
    return PLANETS.get(pid, f"Planet_{pid}")

def get_nakshatra(longitude: float) -> dict:
    """Get nakshatra from sidereal longitude."""
    nak_idx = int(longitude / (360 / 27))
    pada = int((longitude % (360 / 27)) / (360 / 108)) + 1
    return {
        "index": nak_idx,
        "name": NAKSHATRAS[nak_idx % 27],
        "pada": min(pada, 4),
        "degree": longitude % (360 / 27)
    }

def get_sign_lord(sign_idx: int) -> int:
    """Return the SWE planet ID that rules this sign."""
    return SIGN_LORDS[sign_idx % 12]

def normalize_angle(angle: float) -> float:
    """Normalize angle to 0-360."""
    return angle % 360

def angular_distance(a: float, b: float) -> float:
    """Shortest angular distance between two longitudes."""
    diff = abs(normalize_angle(a) - normalize_angle(b))
    return min(diff, 360 - diff)

def assign_planet_to_house(planet_long: float, cusps: list) -> int:
    """Assign planet to house based on cusp positions (1-indexed).
    cusps[0] = 1st house cusp, cusps[1] = 2nd, etc.
    """
    planet_long = normalize_angle(planet_long)
    for i in range(12):
        cusp_start = normalize_angle(cusps[i])
        cusp_end = normalize_angle(cusps[(i + 1) % 12])
        if cusp_start < cusp_end:
            if cusp_start <= planet_long < cusp_end:
                return i + 1
        else:  # Wraps around 360
            if planet_long >= cusp_start or planet_long < cusp_end:
                return i + 1
    return 1  # Fallback


# ═══════════════════════════════════════════════════════════════════
# NAVAMSA (D9) LAGNA — Genuineness Check
# ═══════════════════════════════════════════════════════════════════

def calculate_navamsa_sign(longitude: float) -> int:
    """
    Calculate the Navamsa (D9) sign for a given sidereal longitude.
    Each sign is divided into 9 equal parts of 3°20' (3.3333°).
    Navamsa counting starts from the sign itself for Movable signs,
    from the 9th sign for Fixed signs, and from the 5th sign for Dual signs.

    Returns: sign index 0-11
    """
    sign_idx = int(longitude / 30) % 12
    degree_in_sign = longitude % 30
    navamsa_pada = int(degree_in_sign / (30 / 9))  # 0-8 within the sign

    # Starting point depends on sign type (Movable/Fixed/Dual)
    sign_type = sign_idx % 3
    if sign_type == 0:    # Movable (Aries, Cancer, Libra, Capricorn) — start from itself
        start = sign_idx
    elif sign_type == 1:  # Fixed (Taurus, Leo, Scorpio, Aquarius) — start from 9th
        start = (sign_idx + 8) % 12
    else:                 # Dual (Gemini, Virgo, Sagittarius, Pisces) — start from 5th
        start = (sign_idx + 4) % 12

    navamsa_sign = (start + navamsa_pada) % 12
    return navamsa_sign


def check_navamsa_genuineness(chart: dict) -> dict:
    """
    Check if the Prashna question is "Genuine" or "Fruitless" using the Navamsa Lagna.

    Rules (Tajika school):
    1. If the D1 Lagna lord and the D9 Lagna lord are the same or friendly → Genuine.
    2. If the D9 Lagna falls in a Dusthana (6, 8, 12) from the D1 Lagna → Fruitless suspicion.
    3. If Moon's Navamsa is in a Kendra (1, 4, 7, 10) from the Navamsa Lagna → Genuine.

    Returns:
        {"genuine": bool, "navamsa_lagna_sign": int, "reason": str, "penalty": int}
    """
    lagna_lon = chart.get("lagna", 0)
    lagna_sign = chart.get("lagna_sign", 0)

    # Calculate Navamsa Lagna
    nav_lagna_sign = calculate_navamsa_sign(lagna_lon)

    # Calculate Moon's Navamsa
    moon = chart["planets"].get(1)
    moon_nav_sign = calculate_navamsa_sign(moon["longitude"]) if moon else None

    # Check 1: D9 Lagna lord vs D1 Lagna lord relationship
    d1_lord = get_sign_lord(lagna_sign)
    d9_lord = get_sign_lord(nav_lagna_sign)

    # Natural friendships (simplified Vedic friendship table)
    FRIENDSHIPS = {
        0: {1, 4, 5},       # Sun friends: Moon, Mars, Jupiter
        1: {0, 2},           # Moon friends: Sun, Mercury
        2: {0, 3},           # Mercury friends: Sun, Venus
        3: {2, 6},           # Venus friends: Mercury, Saturn
        4: {0, 1, 5},        # Mars friends: Sun, Moon, Jupiter
        5: {0, 1, 4},        # Jupiter friends: Sun, Moon, Mars
        6: {2, 3},           # Saturn friends: Mercury, Venus
    }

    same_or_friendly = (d1_lord == d9_lord) or (d9_lord in FRIENDSHIPS.get(d1_lord, set()))

    # Check 2: D9 Lagna distance from D1 Lagna
    dist_d9_from_d1 = (nav_lagna_sign - lagna_sign) % 12
    dusthana_from_d1 = dist_d9_from_d1 in [5, 7, 11]  # 6th(idx5), 8th(idx7), 12th(idx11)

    # Check 3: Moon's Navamsa in Kendra from Navamsa Lagna
    moon_nav_kendra = False
    if moon_nav_sign is not None:
        moon_dist = (moon_nav_sign - nav_lagna_sign) % 12
        moon_nav_kendra = moon_dist in [0, 3, 6, 9]  # 1st, 4th, 7th, 10th

    # Determine genuineness
    genuine = True
    penalty = 0
    reasons = []

    if dusthana_from_d1 and not same_or_friendly:
        genuine = False
        penalty = -10
        reasons.append("Navamsa Lagna falls in a difficult position from the Ascendant — question may lack focus")
    elif same_or_friendly:
        reasons.append("Ascendant lords aligned — the question is well-timed")
    else:
        reasons.append("Navamsa Lagna neutral — question is valid")

    if moon_nav_kendra:
        genuine = True  # Moon in Kendra overrides dusthana concern
        reasons.append("Moon's deeper position confirms sincerity")
        if penalty < 0:
            penalty = -5  # Reduce penalty but don't eliminate

    return {
        "genuine": genuine,
        "navamsa_lagna_sign": nav_lagna_sign,
        "navamsa_lagna_name": sign_name(nav_lagna_sign),
        "moon_navamsa_sign": moon_nav_sign,
        "moon_navamsa_name": sign_name(moon_nav_sign) if moon_nav_sign is not None else None,
        "d1_lord": planet_name_from_id(d1_lord),
        "d9_lord": planet_name_from_id(d9_lord),
        "lords_aligned": same_or_friendly,
        "moon_nav_kendra": moon_nav_kendra,
        "reason": ". ".join(reasons),
        "penalty": penalty,
    }


# ═══════════════════════════════════════════════════════════════════
# VOID OF COURSE MOON
# ═══════════════════════════════════════════════════════════════════

def check_void_of_course(chart: dict) -> dict:
    """
    Check if the Moon is Void of Course — i.e., the Moon will NOT complete
    any major Tajika aspect (conjunction, sextile, square, trine, opposition)
    with any planet before it leaves its current sign.

    A Void Moon means the question's energy won't connect to any outcome.
    Events stall, decisions fizzle. This is a hard penalty on YES verdicts.

    Logic:
    1. Get Moon's current longitude and sign.
    2. Calculate how many degrees remain before Moon enters the next sign.
    3. For each other planet, check if the Moon will form any Tajika aspect
       (within orb) before leaving the sign.
    4. If NO aspects are found → Moon is Void of Course.

    Returns:
        {"void_of_course": bool, "penalty": int, "reason": str,
         "degrees_remaining": float, "next_aspect": dict or None}
    """
    moon = chart["planets"].get(1)
    if not moon:
        return {"void_of_course": False, "penalty": 0, "reason": "Moon data unavailable"}

    moon_lon = moon["longitude"]
    moon_sign = moon["sign"]
    moon_speed = moon["daily_speed"]
    degree_in_sign = moon_lon % 30
    degrees_to_sign_end = 30 - degree_in_sign

    # If Moon is retrograde (very rare but possible), skip VoC check
    if moon_speed <= 0:
        return {
            "void_of_course": False,
            "penalty": 0,
            "reason": "Moon is retrograde — Void of Course check not applicable",
            "degrees_remaining": degrees_to_sign_end,
            "next_aspect": None,
        }

    # Check every planet for upcoming aspects
    moon_orb = TAJIKA_ORBS["Moon"]
    closest_aspect = None
    closest_distance = 999

    for pid, pdata in chart["planets"].items():
        if pid == 1:  # Skip Moon itself
            continue

        planet_lon = pdata["longitude"]
        planet_name = pdata["name"]
        planet_orb = TAJIKA_ORBS.get(planet_name, 9)
        combined_orb = (moon_orb + planet_orb) / 2

        for aspect_angle in TAJIKA_ASPECTS:
            # Where the Moon needs to be for this aspect
            target_1 = normalize_angle(planet_lon + aspect_angle)
            target_2 = normalize_angle(planet_lon - aspect_angle)

            for target in [target_1, target_2]:
                # Only count if target is in the Moon's current sign
                target_sign = int(target / 30) % 12
                if target_sign != moon_sign:
                    continue

                # How far must the Moon travel (forward) to reach this target?
                forward_to_target = (target - moon_lon) % 360

                # Must be reachable before sign boundary AND within orb approach
                if 0 < forward_to_target <= degrees_to_sign_end:
                    if forward_to_target < closest_distance:
                        closest_distance = forward_to_target
                        closest_aspect = {
                            "planet": planet_name,
                            "aspect": aspect_angle,
                            "degrees_away": round(forward_to_target, 2),
                        }

    if closest_aspect is None:
        # Moon makes NO aspects before leaving its sign → Void of Course
        return {
            "void_of_course": True,
            "penalty": -15,
            "reason": f"Moon makes no further connections before leaving {sign_name(moon_sign)} — energy dissipates, outcomes stall",
            "degrees_remaining": round(degrees_to_sign_end, 2),
            "next_aspect": None,
        }
    else:
        return {
            "void_of_course": False,
            "penalty": 0,
            "reason": f"Moon will connect with {closest_aspect['planet']} ({closest_aspect['aspect']}° aspect) in {closest_aspect['degrees_away']:.1f}° — question has momentum",
            "degrees_remaining": round(degrees_to_sign_end, 2),
            "next_aspect": closest_aspect,
        }


# ═══════════════════════════════════════════════════════════════════
# STEP 0: CAST THE MOMENT CHART
# ═══════════════════════════════════════════════════════════════════

def cast_prashna_chart(lat: float, lng: float, timestamp: datetime) -> dict:
    """
    Cast a full Prashna (Horary) chart for the exact moment of inquiry.

    Args:
        lat: User's current latitude
        lng: User's current longitude
        timestamp: Exact moment of the question (UTC)

    Returns:
        dict with lagna, cusps, planets (positions + speeds + houses)
    """
    if swe is None:
        raise ImportError("swisseph not installed — cannot cast chart")

    # Set sidereal mode (Lahiri ayanamsha)
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # Convert to Julian Day
    hour_decimal = timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0
    jd = swe.julday(timestamp.year, timestamp.month, timestamp.day, hour_decimal)

    # Calculate house cusps (Placidus)
    cusps_tuple, asc_mc = swe.houses_ex(jd, lat, lng, b'P', swe.FLG_SIDEREAL)
    cusps = list(cusps_tuple)  # 12 cusps
    prashna_lagna = asc_mc[0]  # Ascendant degree (sidereal)
    lagna_sign = int(prashna_lagna / 30)
    lagna_degree = prashna_lagna % 30

    # Calculate planetary positions
    SWE_IDS = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN]
    planets = {}

    for p_id in SWE_IDS:
        result = swe.calc_ut(jd, p_id, swe.FLG_SIDEREAL | swe.FLG_SPEED)
        # result is a tuple: ((longitude, latitude, distance, speed_long, ...), return_flag)
        lon = result[0]
        longitude = lon[0]
        daily_speed = lon[3]
        sign_idx = int(longitude / 30)
        degree_in_sign = longitude % 30
        house = assign_planet_to_house(longitude, cusps)
        nak = get_nakshatra(longitude)

        planets[p_id] = {
            "id": p_id,
            "name": planet_name_from_id(p_id),
            "longitude": round(longitude, 4),
            "sign": sign_idx,
            "sign_name": sign_name(sign_idx),
            "degree_in_sign": round(degree_in_sign, 4),
            "daily_speed": round(daily_speed, 6),
            "retrograde": daily_speed < 0,
            "house": house,
            "nakshatra": nak["name"],
            "nakshatra_pada": nak["pada"],
        }

    # Also compute Rahu/Ketu (mean node)
    rahu_result = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SIDEREAL | swe.FLG_SPEED)
    rahu_lon = rahu_result[0][0]
    ketu_lon = normalize_angle(rahu_lon + 180)

    moon_data = planets[swe.MOON]
    moon_nak = get_nakshatra(moon_data["longitude"])

    # Navamsa (D9) Lagna for genuineness check
    nav_lagna_sign = calculate_navamsa_sign(prashna_lagna)

    return {
        "timestamp": timestamp.isoformat(),
        "lat": lat,
        "lng": lng,
        "jd": round(jd, 6),
        "lagna": round(prashna_lagna, 4),
        "lagna_sign": lagna_sign,
        "lagna_sign_name": sign_name(lagna_sign),
        "lagna_degree": round(lagna_degree, 4),
        "lagna_nakshatra": get_nakshatra(prashna_lagna)["name"],
        "navamsa_lagna_sign": nav_lagna_sign,
        "navamsa_lagna_name": sign_name(nav_lagna_sign),
        "cusps": [round(c, 4) for c in cusps],
        "planets": planets,
        "rahu_longitude": round(rahu_lon, 4),
        "ketu_longitude": round(ketu_lon, 4),
        "moon_nakshatra": moon_nak["name"],
        "moon_house": moon_data["house"],
    }


# ═══════════════════════════════════════════════════════════════════
# DOMAIN DETECTION & ROUTING
# ═══════════════════════════════════════════════════════════════════

def detect_prashna_intent(question: str) -> bool:
    """Check if the question has Yes/No intent."""
    for pattern in PRASHNA_PATTERNS:
        if pattern.search(question):
            return True
    return False

def detect_domain(question: str) -> Tuple[str, List[int]]:
    """
    Detect the life domain from the question and return the house(s) of interest.
    Returns: (domain_name, [house_numbers])
    """
    q_lower = question.lower()

    # Check each domain keyword
    for keyword, houses in DOMAIN_HOUSE_MAP.items():
        if keyword in q_lower:
            return keyword, houses

    # Broader pattern matching
    if any(w in q_lower for w in ["raise", "boss", "resign", "hired", "fired", "interview"]):
        return "career", [10]
    if any(w in q_lower for w in ["marry", "divorce", "engaged", "dating", "girlfriend", "boyfriend", "wife", "husband"]):
        return "relationship", [7]
    if any(w in q_lower for w in ["buy", "sell", "stock", "crypto", "deal", "profit", "loss"]):
        return "finance", [2, 11]
    if any(w in q_lower for w in ["sick", "doctor", "hospital", "medicine", "recover"]):
        return "health", [6]
    if any(w in q_lower for w in ["pregnant", "conceive", "child", "kid", "son", "daughter"]):
        return "children", [5]
    if any(w in q_lower for w in ["passport", "migrate", "immigration", "relocate", "foreign"]):
        return "travel", [9, 12]
    if any(w in q_lower for w in ["degree", "admission", "university", "school", "test"]):
        return "education", [4, 5]

    # Default: 10th house (general success)
    return "general", [10]


# ═══════════════════════════════════════════════════════════════════
# STEP A: LAGNA STRENGTH (+25%)
# ═══════════════════════════════════════════════════════════════════

def check_lagna_strength(chart: dict) -> dict:
    """
    Check if a natural benefic (Jupiter, Venus, Mercury) is in the 1st house
    or aspects the Lagna sign via Rashi Drishti.
    Returns: {"score": 0 or 25, "reason": str}
    """
    lagna_sign = chart["lagna_sign"]
    planets = chart["planets"]

    for pid, pdata in planets.items():
        p_name = pdata["name"]
        if pid not in BENEFIC_IDS:
            continue

        # Check if in 1st house
        if pdata["house"] == 1:
            return {
                "score": 25,
                "reason": f"{p_name} is in the 1st house — strong environment for success"
            }

        # Check Rashi Drishti to lagna sign
        aspected_signs = get_rashi_drishti(pdata["sign"])
        if lagna_sign in aspected_signs:
            return {
                "score": 25,
                "reason": f"{p_name} aspects the Lagna from {pdata['sign_name']} — supportive energy"
            }

    # Also check waxing Moon (benefic when waxing)
    moon = planets.get(1)  # swe.MOON = 1
    sun = planets.get(0)   # swe.SUN = 0
    if moon and sun:
        moon_sun_dist = (moon["longitude"] - sun["longitude"]) % 360
        if moon_sun_dist < 180:  # Waxing
            if moon["house"] == 1:
                return {
                    "score": 25,
                    "reason": "Waxing Moon in the 1st house — favorable mental environment"
                }

    return {"score": 0, "reason": "No benefic influence on the Lagna"}


# ═══════════════════════════════════════════════════════════════════
# STEP B: LORD CONNECTION (+25%)
# ═══════════════════════════════════════════════════════════════════

def check_lord_connection(chart: dict, houses_of_interest: List[int]) -> dict:
    """
    Check if Lord of 1st house and Lord of the house of interest are
    in mutual aspect or Trikona (1-5-9) relationship.
    """
    lagna_sign = chart["lagna_sign"]
    lord_1_id = get_sign_lord(lagna_sign)
    planets = chart["planets"]

    if lord_1_id not in planets:
        return {"score": 0, "reason": "Cannot determine Lord of 1st house"}

    lord_1_data = planets[lord_1_id]
    lord_1_sign = lord_1_data["sign"]

    best_result = {"score": 0, "reason": "No connection between querent and goal"}

    for house_num in houses_of_interest:
        # Get the sign on the cusp of the house of interest
        cusp_long = chart["cusps"][house_num - 1]
        house_sign = int(cusp_long / 30) % 12
        lord_x_id = get_sign_lord(house_sign)

        if lord_x_id not in planets:
            continue

        lord_x_data = planets[lord_x_id]
        lord_x_sign = lord_x_data["sign"]

        # Same sign (conjunction)
        if lord_1_sign == lord_x_sign:
            return {
                "score": 25,
                "reason": f"Lords of 1st and {house_num}th house are conjunct in {sign_name(lord_1_sign)} — strong connection",
                "house": house_num,
                "lord_1": lord_1_data["name"],
                "lord_x": lord_x_data["name"],
            }

        # Trikona (1-5-9 relationship)
        dist = (lord_x_sign - lord_1_sign) % 12
        if dist in [0, 4, 8] or (12 - dist) in [4, 8]:
            return {
                "score": 25,
                "reason": f"Lords are in Trikona — harmonious flow between querent and goal",
                "house": house_num,
                "lord_1": lord_1_data["name"],
                "lord_x": lord_x_data["name"],
            }

        # Mutual aspect (7th from each other)
        if dist == 6:
            return {
                "score": 25,
                "reason": f"Lords in mutual 7th aspect — direct confrontation leading to resolution",
                "house": house_num,
                "lord_1": lord_1_data["name"],
                "lord_x": lord_x_data["name"],
            }

        # Rashi Drishti
        if lord_x_sign in get_rashi_drishti(lord_1_sign):
            best_result = {
                "score": 25,
                "reason": f"Lords connected via Rashi Drishti — indirect but present connection",
                "house": house_num,
                "lord_1": lord_1_data["name"],
                "lord_x": lord_x_data["name"],
            }

    return best_result


# ═══════════════════════════════════════════════════════════════════
# STEP C: ITHASALA YOGA — THE VERDICT ENGINE (+35% / -35%)
# ═══════════════════════════════════════════════════════════════════

def check_ithasala(chart: dict, planet_a_id: int, planet_b_id: int) -> dict:
    """
    Check Ithasala (Applying) or Ishrafa (Separating) between two planets.
    The faster planet must be behind the slower one and moving toward it.

    Returns:
        {"type": "ithasala"|"ishrafa"|"neutral",
         "score": +35 or -35 or 0,
         "aspect": angle or None,
         "reason": str}
    """
    planets = chart["planets"]

    if planet_a_id not in planets or planet_b_id not in planets:
        return {"type": "neutral", "score": 0, "aspect": None, "reason": "Planet not found"}

    pa = planets[planet_a_id]
    pb = planets[planet_b_id]

    # Determine faster planet by actual daily speed
    if abs(pa["daily_speed"]) > abs(pb["daily_speed"]):
        faster, slower = pa, pb
    else:
        faster, slower = pb, pa

    # Retrograde check — if faster planet is retrograde, Ithasala breaks
    if faster["retrograde"]:
        return {
            "type": "ishrafa",
            "score": -35,
            "aspect": None,
            "reason": f"{faster['name']} is retrograde — moving away from completion",
            "faster": faster["name"],
            "slower": slower["name"],
        }

    faster_name = faster["name"]
    slower_name = slower["name"]
    faster_orb = TAJIKA_ORBS.get(faster_name, 9)
    slower_orb = TAJIKA_ORBS.get(slower_name, 9)
    combined_orb = (faster_orb + slower_orb) / 2

    faster_lon = faster["longitude"]
    slower_lon = slower["longitude"]

    # Check each Tajika aspect angle
    for aspect_angle in TAJIKA_ASPECTS:
        # Where the faster planet needs to be for this aspect
        target_lon = normalize_angle(slower_lon - aspect_angle)
        alt_target = normalize_angle(slower_lon + aspect_angle)

        for target in [target_lon, alt_target]:
            dist = angular_distance(faster_lon, target)
            if dist <= combined_orb:
                # Within orb — is it applying or separating?
                # Applying: faster planet's longitude < target (it hasn't reached the aspect yet)
                # We check if the faster planet will reach the target by moving forward
                forward_dist = (target - faster_lon) % 360
                if forward_dist <= combined_orb and faster["daily_speed"] > 0:
                    # Applying aspect
                    return {
                        "type": "ithasala",
                        "score": 35,
                        "aspect": aspect_angle,
                        "reason": f"{faster_name} is applying toward {slower_name} ({aspect_angle}° aspect) — event is moving toward completion",
                        "faster": faster_name,
                        "slower": slower_name,
                        "orb": round(dist, 2),
                    }
                else:
                    # Separating aspect
                    return {
                        "type": "ishrafa",
                        "score": -35,
                        "aspect": aspect_angle,
                        "reason": f"{faster_name} is separating from {slower_name} — the opportunity window has passed",
                        "faster": faster_name,
                        "slower": slower_name,
                        "orb": round(dist, 2),
                    }

    return {
        "type": "neutral",
        "score": 0,
        "aspect": None,
        "reason": f"No Tajika aspect between {faster_name} and {slower_name} within orb",
        "faster": faster_name,
        "slower": slower_name,
    }


def check_ithasala_for_houses(chart: dict, houses_of_interest: List[int]) -> dict:
    """Run Ithasala check between Lord of 1st and Lord of house(s) of interest."""
    lagna_sign = chart["lagna_sign"]
    lord_1_id = get_sign_lord(lagna_sign)

    best_result = {"type": "neutral", "score": 0, "aspect": None, "reason": "No connection"}

    for house_num in houses_of_interest:
        cusp_long = chart["cusps"][house_num - 1]
        house_sign = int(cusp_long / 30) % 12
        lord_x_id = get_sign_lord(house_sign)

        if lord_1_id == lord_x_id:
            # Same lord rules both houses — inherent connection
            return {
                "type": "ithasala",
                "score": 35,
                "aspect": 0,
                "reason": "Same planet rules both the querent and the goal — inherent alignment",
                "lord_1": planet_name_from_id(lord_1_id),
                "lord_x": planet_name_from_id(lord_x_id),
                "house": house_num,
            }

        result = check_ithasala(chart, lord_1_id, lord_x_id)
        result["house"] = house_num
        result["lord_1"] = planet_name_from_id(lord_1_id)
        result["lord_x"] = planet_name_from_id(lord_x_id)

        # Priority: ithasala > ishrafa > neutral
        # An ithasala always wins. An ishrafa beats neutral (it's a definitive answer).
        if result["type"] == "ithasala":
            return result  # Best possible — return immediately
        if result["type"] == "ishrafa" and best_result["type"] == "neutral":
            best_result = result  # Ishrafa is definitive — better than "no data"
        elif result["score"] > best_result.get("score", -999):
            best_result = result

    return best_result


# ═══════════════════════════════════════════════════════════════════
# STEP D: MOON VALIDATION (+15%)
# ═══════════════════════════════════════════════════════════════════

def check_moon_validation(chart: dict) -> dict:
    """
    Moon in Upachaya houses (3, 6, 10, 11) = growth/success energy (+15%).
    Also checks waxing/waning and void-of-course.
    """
    moon = chart["planets"].get(1)  # swe.MOON = 1
    if not moon:
        return {"score": 0, "reason": "Moon data not available"}

    moon_house = moon["house"]
    UPACHAYA = [3, 6, 10, 11]

    result = {
        "moon_house": moon_house,
        "moon_sign": moon["sign_name"],
        "moon_nakshatra": moon["nakshatra"],
    }

    if moon_house in UPACHAYA:
        result["score"] = 15
        result["reason"] = f"Moon in {moon_house}th house (Upachaya) — growth energy supports the question"
    else:
        result["score"] = 0
        house_quality = "angular" if moon_house in [1, 4, 7, 10] else "succedent" if moon_house in [2, 5, 8, 11] else "cadent"
        result["reason"] = f"Moon in {moon_house}th house ({house_quality}) — neutral for this inquiry"

    # Waxing/Waning check
    sun = chart["planets"].get(0)
    if sun and moon:
        moon_sun_dist = (moon["longitude"] - sun["longitude"]) % 360
        result["waxing"] = moon_sun_dist < 180
        if result["waxing"]:
            result["reason"] += ". Waxing Moon adds optimism."

    return result


# ═══════════════════════════════════════════════════════════════════
# EDGE CASES: MUTHASHILA, NAKTA, YAMAYA
# ═══════════════════════════════════════════════════════════════════

def check_muthashila(chart: dict, lord_1_id: int, lord_x_id: int) -> Optional[dict]:
    """
    Muthashila: Significators within 1° of exact aspect.
    Event is imminent. Overrides to 95%+.
    """
    planets = chart["planets"]
    if lord_1_id not in planets or lord_x_id not in planets:
        return None

    p1 = planets[lord_1_id]
    px = planets[lord_x_id]
    diff = angular_distance(p1["longitude"], px["longitude"])

    for angle in TAJIKA_ASPECTS:
        dist_to_exact = abs(diff - angle)
        if dist_to_exact < 1.0:
            return {
                "yoga": "muthashila",
                "score": 95,
                "reason": f"{p1['name']} and {px['name']} are within {dist_to_exact:.2f}° of exact {angle}° aspect — event is imminent",
                "override": True,
            }
    return None


def check_nakta(chart: dict, lord_1_id: int, lord_x_id: int) -> Optional[dict]:
    """
    Nakta: No direct Ithasala, but Moon bridges both significators.
    YES through a third party / mediator.
    """
    moon_id = 1  # swe.MOON

    if lord_1_id == moon_id or lord_x_id == moon_id:
        return None  # Moon is already a significator

    bridge_to_1 = check_ithasala(chart, moon_id, lord_1_id)
    bridge_to_x = check_ithasala(chart, moon_id, lord_x_id)

    if bridge_to_1["type"] == "ithasala" and bridge_to_x["type"] == "ithasala":
        return {
            "yoga": "nakta",
            "score": 25,
            "reason": "Moon bridges both significators — success through a third party or mediator",
        }
    return None


def check_yamaya(chart: dict, lord_1_id: int, lord_x_id: int) -> Optional[dict]:
    """
    Yamaya: A slower planet (Jupiter/Saturn) receives aspect from both significators.
    YES through authority or institutional support.
    """
    SLOW_PLANETS = [5, 6]  # Jupiter, Saturn

    for slow_id in SLOW_PLANETS:
        if slow_id == lord_1_id or slow_id == lord_x_id:
            continue

        recv_1 = check_ithasala(chart, lord_1_id, slow_id)
        recv_x = check_ithasala(chart, lord_x_id, slow_id)

        if recv_1["type"] == "ithasala" and recv_x["type"] == "ithasala":
            slow_name = planet_name_from_id(slow_id)
            return {
                "yoga": "yamaya",
                "score": 20,
                "reason": f"{slow_name} receives energy from both significators — success through authority or institutional support",
            }
    return None


def check_edge_yogas(chart: dict, lord_1_id: int, lord_x_id: int) -> Optional[dict]:
    """Run all three edge-case yoga checks. Returns the first match or None."""
    # Priority: Muthashila > Nakta > Yamaya
    result = check_muthashila(chart, lord_1_id, lord_x_id)
    if result:
        return result

    result = check_nakta(chart, lord_1_id, lord_x_id)
    if result:
        return result

    result = check_yamaya(chart, lord_1_id, lord_x_id)
    if result:
        return result

    return None


# ═══════════════════════════════════════════════════════════════════
# BONUS: MUTUAL RECEPTION (+15%)
# ═══════════════════════════════════════════════════════════════════

def check_mutual_reception(chart: dict, lord_1_id: int, lord_x_id: int) -> dict:
    """
    Mutual Reception: Two planets in each other's signs.
    Example: Mars in Sagittarius + Jupiter in Aries.
    """
    planets = chart["planets"]
    if lord_1_id not in planets or lord_x_id not in planets:
        return {"score": 0, "found": False}

    p1 = planets[lord_1_id]
    px = planets[lord_x_id]

    # Lord of p1's sign is lord_x, and lord of px's sign is lord_1
    lord_of_p1_sign = get_sign_lord(p1["sign"])
    lord_of_px_sign = get_sign_lord(px["sign"])

    if lord_of_p1_sign == lord_x_id and lord_of_px_sign == lord_1_id:
        return {
            "score": 15,
            "found": True,
            "reason": f"{p1['name']} and {px['name']} are in mutual reception — they exchange energy and support each other",
        }

    return {"score": 0, "found": False}


# ═══════════════════════════════════════════════════════════════════
# REMEDY: WEAKEST PLANET
# ═══════════════════════════════════════════════════════════════════

def find_weakest_planet(chart: dict) -> dict:
    """
    Find the weakest planet in the Prashna chart for remedy suggestion.
    Weakness = retrograde, in enemy sign, in 6/8/12 houses, lowest speed.
    """
    planets = chart["planets"]
    weakness_scores = {}

    for pid, pdata in planets.items():
        score = 0
        reasons = []

        # Retrograde
        if pdata["retrograde"]:
            score += 3
            reasons.append("retrograde")

        # In dusthana houses (6, 8, 12)
        if pdata["house"] in [6, 8, 12]:
            score += 2
            reasons.append(f"in {pdata['house']}th house")

        # Low daily speed (relative to its normal speed)
        if abs(pdata["daily_speed"]) < 0.1:
            score += 1
            reasons.append("slow-moving")

        weakness_scores[pid] = {"score": score, "reasons": reasons, "name": pdata["name"]}

    # Find the weakest
    weakest_id = max(weakness_scores, key=lambda k: weakness_scores[k]["score"])
    weakest = weakness_scores[weakest_id]

    return {
        "planet_id": weakest_id,
        "planet": weakest["name"],
        "weakness_score": weakest["score"],
        "reasons": weakest["reasons"],
    }


# ═══════════════════════════════════════════════════════════════════
# MASTER SCORE: COMBINE ALL STEPS
# ═══════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════
# DOMAIN AUDIT — Planet Condition Helpers
# ═══════════════════════════════════════════════════════════════════

def _is_combust(chart: dict, planet_id: int) -> bool:
    if planet_id == 0:
        return False
    planets = chart["planets"]
    if planet_id not in planets or 0 not in planets:
        return False
    return angular_distance(planets[0]["longitude"], planets[planet_id]["longitude"]) <= COMBUSTION_ORB


def _is_exalted(chart: dict, planet_id: int) -> bool:
    planets = chart["planets"]
    if planet_id not in planets:
        return False
    return planets[planet_id]["sign"] == EXALTATION_SIGNS.get(planet_id, -1)


def _is_debilitated(chart: dict, planet_id: int) -> bool:
    planets = chart["planets"]
    if planet_id not in planets:
        return False
    return planets[planet_id]["sign"] == DEBILITATION_SIGNS.get(planet_id, -1)


def _is_retrograde_check(chart: dict, planet_id: int) -> bool:
    if planet_id in [0, 1]:
        return False
    planets = chart["planets"]
    if planet_id not in planets:
        return False
    return planets[planet_id]["retrograde"]


def _is_stationary(chart: dict, planet_id: int) -> bool:
    if planet_id in [0, 1]:
        return False
    planets = chart["planets"]
    if planet_id not in planets:
        return False
    speed = abs(planets[planet_id]["daily_speed"])
    threshold = 0.1 if planet_id in [2, 3] else 0.05
    return speed < threshold


def _get_house_lord_id(chart: dict, house_num: int) -> int:
    cusp_long = chart["cusps"][house_num - 1]
    house_sign = int(cusp_long / 30) % 12
    return get_sign_lord(house_sign)


def _planet_aspects_house(chart: dict, planet_id: int, target_house: int) -> bool:
    planets = chart["planets"]
    if planet_id not in planets:
        return False
    p_lon = planets[planet_id]["longitude"]
    cusp_lon = chart["cusps"][target_house - 1]
    dist = angular_distance(p_lon, cusp_lon)
    for angle in TAJIKA_ASPECTS:
        if abs(dist - angle) < 10:
            return True
    return False


def _planet_strength_score(chart: dict, planet_id: int) -> int:
    planets = chart["planets"]
    if planet_id not in planets:
        return 0
    p = planets[planet_id]
    score = 50
    if _is_exalted(chart, planet_id):
        score += 30
    if _is_debilitated(chart, planet_id):
        score -= 30
    if p["retrograde"]:
        score -= 15
    if _is_combust(chart, planet_id):
        score -= 20
    if p["house"] in ANGLE_HOUSES:
        score += 10
    if p["house"] in [6, 8, 12]:
        score -= 10
    return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════════
# DOMAIN AUDIT ENGINE
# ═══════════════════════════════════════════════════════════════════

def run_domain_audit(chart: dict, domain: str, houses: list) -> dict:
    config = DOMAIN_AUDIT_CONFIG.get(domain, DEFAULT_AUDIT_CONFIG)
    primary_house = config["primary_house"]
    secondary_house = config["secondary_house"]

    flags = []
    audit_bonuses = []
    net_adjustment = 0
    hard_truth = None
    delay_days = None
    verdict_override = None

    planets = chart["planets"]
    sixth_lord_id = _get_house_lord_id(chart, 6)
    seventh_lord_id = _get_house_lord_id(chart, 7)
    tenth_lord_id = _get_house_lord_id(chart, 10)

    for rule in config.get("rules", []):
        check = rule["check"]

        if check == "retrograde_lord":
            h = rule.get("house", primary_house)
            lord_id = _get_house_lord_id(chart, h)
            if _is_retrograde_check(chart, lord_id):
                pen = rule.get("penalty", -20)
                flags.append({"type": "RETROGRADE_LORD", "severity": "warning", "penalty": pen,
                              "message": rule["message"], "planet": planet_name_from_id(lord_id), "house": h})
                net_adjustment += pen
                if not hard_truth:
                    hard_truth = rule["message"]

        elif check == "combust_lord":
            h = rule.get("house", primary_house)
            lord_id = _get_house_lord_id(chart, h)
            if _is_combust(chart, lord_id):
                pen = rule.get("penalty", -30)
                flags.append({"type": "COMBUST_LORD", "severity": "danger", "penalty": pen,
                              "message": rule["message"], "planet": planet_name_from_id(lord_id), "house": h})
                net_adjustment += pen
                if not hard_truth:
                    hard_truth = rule["message"]

        elif check == "exalted_lord":
            h = rule.get("house", primary_house)
            lord_id = _get_house_lord_id(chart, h)
            if _is_exalted(chart, lord_id):
                bon = rule.get("bonus", 15)
                audit_bonuses.append({"type": "EXALTED_LORD", "bonus": bon,
                                      "message": rule["message"], "planet": planet_name_from_id(lord_id), "house": h})
                net_adjustment += bon

        elif check == "lagna_connection":
            if tenth_lord_id in planets and planets[tenth_lord_id]["house"] == 1:
                bon = rule.get("bonus", 25)
                audit_bonuses.append({"type": "LAGNA_CONNECTION", "bonus": bon,
                                      "message": rule["message"], "planet": planet_name_from_id(tenth_lord_id)})
                net_adjustment += bon

        elif check == "sixth_pressure":
            if _planet_strength_score(chart, sixth_lord_id) > _planet_strength_score(chart, tenth_lord_id):
                pen = rule.get("penalty", -15)
                flags.append({"type": "SIXTH_PRESSURE", "severity": "warning", "penalty": pen,
                              "message": rule["message"]})
                net_adjustment += pen
                if not hard_truth:
                    hard_truth = rule["message"]

        elif check == "saturn_aspect":
            saturn_id = 6
            if saturn_id in planets and tenth_lord_id in planets:
                dist = angular_distance(planets[saturn_id]["longitude"], planets[tenth_lord_id]["longitude"])
                for angle in TAJIKA_ASPECTS:
                    if abs(dist - angle) < TAJIKA_ORBS.get("Saturn", 9):
                        d = rule.get("delay_days", 30)
                        flags.append({"type": "SATURN_DELAY", "severity": "caution", "penalty": 0,
                                      "message": rule["message"], "delay_days": d})
                        delay_days = d
                        break

        elif check == "twelfth_house_leak":
            if seventh_lord_id in planets and planets[seventh_lord_id]["house"] == 12:
                pen = rule.get("penalty", -40)
                flags.append({"type": "12TH_HOUSE_LEAK", "severity": "danger", "penalty": pen,
                              "message": rule["message"]})
                net_adjustment += pen
                hard_truth = rule["message"]

        elif check == "stationary_lord":
            h = rule.get("house", 7)
            lord_id = _get_house_lord_id(chart, h)
            if _is_stationary(chart, lord_id):
                verdict_override = rule.get("verdict_override", "UNCERTAIN")
                flags.append({"type": "STATIONARY_LORD", "severity": "warning", "penalty": 0,
                              "message": rule["message"]})
                hard_truth = rule["message"]

        elif check == "venus_angle":
            venus_id = 3
            if venus_id in planets and planets[venus_id]["house"] in ANGLE_HOUSES:
                bon = rule.get("bonus", 20)
                audit_bonuses.append({"type": "VENUS_ANGLE", "bonus": bon, "message": rule["message"]})
                net_adjustment += bon

        elif check == "retrograde_opponent":
            if _is_retrograde_check(chart, sixth_lord_id):
                bon = rule.get("bonus", 25)
                audit_bonuses.append({"type": "RETROGRADE_OPPONENT", "bonus": bon, "message": rule["message"]})
                net_adjustment += bon

        elif check == "mars_aspect_sixth":
            mars_id = 4
            if _planet_aspects_house(chart, mars_id, 6):
                flags.append({"type": "MARS_AGGRESSION", "severity": "aggression", "penalty": 0,
                              "message": rule["message"]})

        elif check == "seventh_lord_strength":
            strength = _planet_strength_score(chart, seventh_lord_id)
            if strength >= 50:
                audit_bonuses.append({"type": "FAIR_JUDGE", "bonus": 0,
                                      "message": rule.get("message_strong", "Fair process expected.")})
            else:
                flags.append({"type": "WEAK_JUDGE", "severity": "warning", "penalty": 0,
                              "message": rule.get("message_weak", "Process may be compromised.")})

    return {
        "domain_type": domain, "primary_house": primary_house, "secondary_house": secondary_house,
        "label": config["label"], "house_label": config["house_label"],
        "flags": flags, "bonuses": audit_bonuses, "net_adjustment": net_adjustment,
        "hard_truth": hard_truth, "delay_days": delay_days, "verdict_override": verdict_override,
    }


# ═══════════════════════════════════════════════════════════════════
# PROOF BARS
# ═══════════════════════════════════════════════════════════════════

def build_proof_bars(step_a, step_c, edge_yoga, jaimini_locks, jaimini_bonus):
    if step_a["score"] >= 25:
        command = {"value": 88, "label": "HIGH", "detail": "You are driving the narrative"}
    else:
        command = {"value": 35, "label": "LOW", "detail": "Environment is not fully aligned"}

    if step_c.get("type") == "ithasala":
        orb = step_c.get("orb", 5)
        if orb < 2:
            handshake = {"value": 92, "label": "LOCKED", "detail": "Converging — near completion"}
        elif orb < 5:
            handshake = {"value": 72, "label": "APPLYING", "detail": "Converging — not yet locked"}
        else:
            handshake = {"value": 55, "label": "APPROACHING", "detail": "Momentum building — wide orb"}
    elif step_c.get("type") == "ishrafa":
        handshake = {"value": 15, "label": "SEPARATING", "detail": "Window is closing — momentum lost"}
    else:
        handshake = {"value": 30, "label": "PENDING", "detail": "No active convergence detected"}

    if edge_yoga:
        yoga = edge_yoga.get("yoga", "")
        if yoga == "muthashila":
            broker = {"value": 95, "label": "OVERRIDE", "detail": "Imminent completion — barriers cleared"}
        elif yoga == "nakta":
            broker = {"value": 65, "label": "ACTIVE", "detail": "Third party bridging the gap"}
        elif yoga == "yamaya":
            broker = {"value": 55, "label": "ACTIVE", "detail": "Authority or institution providing support"}
        else:
            broker = {"value": 0, "label": "NONE", "detail": "No intermediary override detected"}
    else:
        broker = {"value": 0, "label": "NONE", "detail": "No intermediary override detected"}

    lock_count = sum(1 for v in jaimini_locks.values() if v)
    if lock_count == 3:
        alignment = {"value": 95, "label": "LOCKED", "detail": "All 3 confirmation engines agree"}
    elif lock_count == 2:
        alignment = {"value": 72, "label": "PARTIAL", "detail": "2 of 3 confirmation engines agree"}
    elif lock_count == 1:
        alignment = {"value": 40, "label": "WEAK", "detail": "Only 1 confirmation engine agrees"}
    else:
        alignment = {"value": 15, "label": "NONE", "detail": "No confirmation from backup engines"}

    return {"command": command, "handshake": handshake, "broker": broker, "alignment": alignment}


# ═══════════════════════════════════════════════════════════════════
# INTENT-BIRTH SYNC
# ═══════════════════════════════════════════════════════════════════

def check_intent_birth_sync(chart, domain, natal_chart_data=None):
    prashna_lagna_sign = chart["lagna_sign"]
    prashna_lagna_name = chart["lagna_sign_name"]
    power_house_num = BIRTH_POWER_HOUSES.get(domain, 10)

    result = {
        "prashna_lagna": prashna_lagna_name,
        "birth_power_house": f"{power_house_num}H",
        "sync_detected": False,
        "intensity_multiplier": 1.0,
        "message": "",
    }

    if natal_chart_data:
        try:
            natal_cusps = natal_chart_data.get("cusps", [])
            if natal_cusps and len(natal_cusps) >= power_house_num:
                natal_house_sign = int(natal_cusps[power_house_num - 1] / 30) % 12
                if prashna_lagna_sign == natal_house_sign:
                    result["sync_detected"] = True
                    result["intensity_multiplier"] = 1.4
                    result["message"] = (
                        f"Your moment chart\'s ascendant ({prashna_lagna_name}) matches your birth chart\'s "
                        f"{power_house_num}th house sign — strong confluence. This question hits at the core."
                    )
                elif natal_house_sign in get_rashi_drishti(prashna_lagna_sign):
                    result["sync_detected"] = True
                    result["intensity_multiplier"] = 1.2
                    result["message"] = (
                        f"Your moment chart aspects your birth chart\'s {power_house_num}th house — "
                        f"the question connects to your deeper pattern."
                    )
        except Exception as e:
            logger.warning(f"Intent-birth sync error: {e}")
    else:
        natural_sign = (power_house_num - 1) % 12
        if prashna_lagna_sign == natural_sign:
            result["sync_detected"] = True
            result["intensity_multiplier"] = 1.3
            result["message"] = (
                f"Your moment chart\'s ascendant ({prashna_lagna_name}) naturally governs the "
                f"{power_house_num}th house domain — this question carries extra weight."
            )
        elif natural_sign in get_rashi_drishti(prashna_lagna_sign):
            result["sync_detected"] = True
            result["intensity_multiplier"] = 1.15
            result["message"] = (
                f"Your moment chart\'s ascendant ({prashna_lagna_name}) aspects the "
                f"{power_house_num}th house domain — supporting connection detected."
            )

    return result



def compute_prashna_verdict(
    chart: dict,
    question: str,
    jaimini_data: Optional[dict] = None,
    natal_dasha: Optional[str] = None,
    natal_chart_data: Optional[dict] = None,
    domain_override: Optional[str] = None,
) -> dict:
    """
    Master scoring function v2.
    Same Steps A-D + edge cases + bonuses as before.
    NEW: domain_audit, proof_bars, confluence added after base scoring.
    NEW param: natal_chart_data for intent-birth sync.
    """
    # Detect domain (classifier override wins when valid; houses always
    # come from the canonical DOMAIN_HOUSE_MAP — single source of truth)
    if domain_override and domain_override in DOMAIN_HOUSE_MAP:
        domain = domain_override
        _h = DOMAIN_HOUSE_MAP[domain_override]
        houses = list(_h) if isinstance(_h, list) else [_h]
    else:
        domain, houses = detect_domain(question)

    # Determine significators
    lagna_sign = chart["lagna_sign"]
    lord_1_id = get_sign_lord(lagna_sign)
    primary_house = houses[0]
    cusp_long = chart["cusps"][primary_house - 1]
    house_sign = int(cusp_long / 30) % 12
    lord_x_id = get_sign_lord(house_sign)

    # ─── Step A: Lagna Strength ───
    step_a = check_lagna_strength(chart)

    # ─── Step B: Lord Connection ───
    step_b = check_lord_connection(chart, houses)

    # ─── Step C: Ithasala ───
    step_c = check_ithasala_for_houses(chart, houses)

    # ─── Step D: Moon Validation ───
    step_d = check_moon_validation(chart)

    # ─── Edge Cases (only if Ithasala is neutral or negative) ───
    edge_yoga = None
    if step_c["type"] != "ithasala":
        edge_yoga = check_edge_yogas(chart, lord_1_id, lord_x_id)

    # ─── Mutual Reception Bonus ───
    mutual_rec = check_mutual_reception(chart, lord_1_id, lord_x_id)

    # ─── Compute Base Score ───
    base_score = step_a["score"] + step_b["score"] + step_c["score"] + step_d["score"]

    if mutual_rec["found"]:
        base_score += mutual_rec["score"]

    if edge_yoga:
        if edge_yoga.get("override"):
            base_score = edge_yoga["score"]
        else:
            if base_score < 70:
                base_score += edge_yoga["score"]

    # ─── Jaimini Triple-Lock Bonus ───
    jaimini_locks = {"vimsottari": False, "chara_dasha": False, "arudha": False}
    jaimini_bonus = 0

    if jaimini_data:
        try:
            jaimini_locks = _check_jaimini_triple_lock(jaimini_data, domain, houses)
            lock_count = sum(1 for v in jaimini_locks.values() if v)
            jaimini_bonus = lock_count * 5
            base_score += jaimini_bonus
        except Exception as e:
            logger.warning(f"Jaimini triple-lock check failed: {e}")

    # ═══ NEW: Domain Audit ═══
    domain_audit = run_domain_audit(chart, domain, houses)
    base_score += domain_audit["net_adjustment"]

    # ═══ NEW: Intent-Birth Sync ═══
    confluence = check_intent_birth_sync(chart, domain, natal_chart_data)
    if confluence["sync_detected"] and base_score > 0:
        base_score = min(int(base_score * confluence["intensity_multiplier"]), 100)

    # ─── Clamp Score ───
    final_score = max(0, min(100, base_score))

    # ─── Determine Verdict ───
    if domain_audit.get("verdict_override"):
        verdict = domain_audit["verdict_override"]
        label = "Decision Paralysis"
        final_score = max(final_score, 30)
    elif final_score >= 85:
        verdict = "STRONG YES"
        label = "High Confidence"
    elif final_score >= 65:
        verdict = "YES"
        label = "Favorable"
    elif final_score >= 40:
        verdict = "CAUTIOUS YES"
        label = "Moderate"
    elif final_score >= 15:
        verdict = "UNLIKELY"
        label = "Low Confidence"
    elif final_score > 0:
        verdict = "NO"
        label = "Not Supported"
    else:
        verdict = "STRONG NO"
        label = "Opportunity Passed"

    # ─── Timing Estimate ───
    timing = _estimate_timing(chart, step_c, edge_yoga)
    if domain_audit.get("delay_days"):
        timing += f" (expect +{domain_audit['delay_days']} day administrative delay)"

    # ─── Weakest Planet for Remedy ───
    weakest = find_weakest_planet(chart)

    # ═══ NEW: Proof Bars ═══
    proof_bars = build_proof_bars(step_a, step_c, edge_yoga, jaimini_locks, jaimini_bonus)

    return {
        "verdict": verdict,
        "score": final_score,
        "label": label,
        "domain": domain,
        "house_of_interest": primary_house,
        "breakdown": {
            "lagna_strength": step_a,
            "lord_connection": step_b,
            "ithasala": step_c,
            "moon_validation": step_d,
            "mutual_reception": mutual_rec,
            "edge_yoga": edge_yoga,
            "jaimini_locks": jaimini_locks,
            "jaimini_bonus": jaimini_bonus,
        },
        "timing": timing,
        "prashna_chart": {
            "lagna_sign": chart["lagna_sign_name"],
            "lagna_degree": chart["lagna_degree"],
            "moon_nakshatra": chart["moon_nakshatra"],
            "moon_house": chart["moon_house"],
            "significator_1": {
                "planet": planet_name_from_id(lord_1_id),
                "house": chart["planets"][lord_1_id]["house"] if lord_1_id in chart["planets"] else None,
                "sign": chart["planets"][lord_1_id]["sign_name"] if lord_1_id in chart["planets"] else None,
            },
            "significator_x": {
                "planet": planet_name_from_id(lord_x_id),
                "house": chart["planets"][lord_x_id]["house"] if lord_x_id in chart["planets"] else None,
                "sign": chart["planets"][lord_x_id]["sign_name"] if lord_x_id in chart["planets"] else None,
            },
        },
        "weakest_planet": weakest,
        "natal_context": {
            "dasha": natal_dasha or "unknown",
            "domain_supported": bool(jaimini_bonus > 0),
        },
        "proof_bars": proof_bars,
        "domain_audit": domain_audit,
        "confluence": confluence,
    }



# ═══════════════════════════════════════════════════════════════════
# JAIMINI TRIPLE-LOCK (Wire 4)
# ═══════════════════════════════════════════════════════════════════

def _check_jaimini_triple_lock(jaimini_data: dict, domain: str, houses: List[int]) -> dict:
    """
    Check the 3 Jaimini locks using stored jaimini_data from the charts table.

    Lock 1 — Vimsottari: Is current dasha lord supportive?
    Lock 2 — Chara Dasha: Does current sign-dasha aspect relevant karaka?
    Lock 3 — Arudha: Is current sign-dasha favorable from AL?
    """
    locks = {"vimsottari": False, "chara_dasha": False, "arudha": False}

    # Parse jaimini_data (might be string or dict)
    if isinstance(jaimini_data, str):
        try:
            jaimini_data = json.loads(jaimini_data)
        except:
            return locks

    # Lock 1: Vimsottari — check if current dasha lord is a natural significator for the domain
    current_md = jaimini_data.get("current_mahadasha", {})
    if current_md:
        md_lord = current_md.get("lord", "").lower()
        # Map domain to planets that naturally support it
        domain_supportive_planets = {
            "career": ["sun", "saturn", "mars", "jupiter"],
            "job": ["sun", "saturn", "mars", "jupiter"],
            "promotion": ["sun", "jupiter", "mars"],
            "promoted": ["sun", "jupiter", "mars"],
            "finance": ["jupiter", "venus", "mercury"],
            "money": ["jupiter", "venus", "mercury"],
            "investment": ["jupiter", "mercury", "saturn"],
            "wealth": ["jupiter", "venus"],
            "relationship": ["venus", "moon", "jupiter"],
            "marriage": ["venus", "jupiter"],
            "love": ["venus", "moon"],
            "health": ["sun", "mars"],
            "education": ["jupiter", "mercury"],
            "travel": ["moon", "jupiter", "rahu"],
            "children": ["jupiter"],
            "property": ["mars", "saturn", "venus"],
            "legal": ["jupiter", "saturn"],
        }
        supportive = domain_supportive_planets.get(domain, ["jupiter", "sun"])
        locks["vimsottari"] = md_lord in supportive

    # Lock 2: Chara Dasha — does current sign aspect the relevant karaka?
    current_chara = jaimini_data.get("current_chara_dasha", {})
    karakas = jaimini_data.get("karakas", {})
    if current_chara and karakas:
        dasha_sign_idx = current_chara.get("sign_index")
        # Map domain to karaka
        domain_karaka_map = {
            "career": "AmK", "job": "AmK", "promotion": "AmK",
            "relationship": "DK", "marriage": "DK", "love": "DK",
            "children": "PK", "baby": "PK",
            "health": "GK", "illness": "GK",
        }
        target_karaka = domain_karaka_map.get(domain, "AmK")
        karaka_sign = karakas.get(target_karaka, {}).get("sign_index")

        if dasha_sign_idx is not None and karaka_sign is not None:
            drishti = get_rashi_drishti(dasha_sign_idx)
            if karaka_sign in drishti or karaka_sign == dasha_sign_idx:
                locks["chara_dasha"] = True

    # Lock 3: Arudha — is dasha sign favorable from AL?
    al = jaimini_data.get("arudha_lagna", {})
    if al and current_chara:
        al_sign = al.get("sign_index")
        dasha_sign_idx = current_chara.get("sign_index")
        if al_sign is not None and dasha_sign_idx is not None:
            dist_from_al = (dasha_sign_idx - al_sign) % 12
            favorable = [0, 1, 3, 4, 6, 8, 9, 10]  # 1,2,4,5,7,9,10,11 (0-indexed distances)
            locks["arudha"] = dist_from_al in favorable

    return locks


# ═══════════════════════════════════════════════════════════════════
# TIMING ESTIMATE
# ═══════════════════════════════════════════════════════════════════

def _estimate_timing(chart: dict, ithasala_result: dict, edge_yoga: Optional[dict]) -> str:
    """
    Estimate when the event will manifest based on Ithasala orb distance.
    Closer orb = sooner. Wider orb = longer.
    """
    if edge_yoga and edge_yoga.get("yoga") == "muthashila":
        return "Within days — this is imminent"

    if ithasala_result.get("type") == "ithasala":
        orb = ithasala_result.get("orb", 5)
        if orb < 2:
            return "Within the next week"
        elif orb < 5:
            return "Within the next 2-3 weeks"
        elif orb < 8:
            return "Within the next 1-2 months"
        else:
            return "Within the next 3-6 months"

    if ithasala_result.get("type") == "ishrafa":
        return "The window may have passed — review within 2 weeks"

    return "Timing unclear — reassess when conditions shift"


# ═══════════════════════════════════════════════════════════════════
# PROMPT BUILDER FOR CLAUDE
# ═══════════════════════════════════════════════════════════════════


def build_prashna_prompt(verdict_data: dict, question: str, user_name: str = "User",
                          locale: str = "global") -> str:
    """Build Claude prompt with domain audit, proof bars, and confluence data."""
    v = verdict_data
    bd = v["breakdown"]
    pc = v["prashna_chart"]

    prompt = f"""You are Antar, an executive life advisor. The user asked a Yes/No question and the Prashna (Horary) engine has ALREADY calculated the verdict. Your job is to EXPLAIN the result in plain English. Do NOT compute anything. Use ONLY the facts below.

USER: {user_name}
QUESTION: {question}

═══ PRE-CALCULATED VERDICT ═══
VERDICT: {v['verdict']}
SCORE: {v['score']}%
LABEL: {v['label']}
DOMAIN: {v['domain']}
TIMING: {v['timing']}

═══ PROOF BARS ═══"""

    pb = v.get("proof_bars", {})
    for bar_name in ["command", "handshake", "broker", "alignment"]:
        bar = pb.get(bar_name, {})
        prompt += f"\n[{bar_name.upper()}]: {bar.get('label', 'N/A')} — {bar.get('detail', '')}"

    prompt += f"""

═══ PRASHNA CHART ═══
Lagna: {pc['lagna_sign']} at {pc['lagna_degree']:.1f}°
Moon Nakshatra: {pc['moon_nakshatra']}
Moon House: {pc['moon_house']}th
Significator 1 (You): {pc['significator_1']['planet']} in {pc['significator_1']['sign']} ({pc['significator_1']['house']}th house)
Significator 2 (Goal): {pc['significator_x']['planet']} in {pc['significator_x']['sign']} ({pc['significator_x']['house']}th house)

═══ SCORING BREAKDOWN ═══
Environment: {bd['lagna_strength']['score']}% — {bd['lagna_strength']['reason']}
Connection: {bd['lord_connection']['score']}% — {bd['lord_connection']['reason']}
Momentum: {bd['ithasala']['score']}% ({bd['ithasala']['type']}) — {bd['ithasala']['reason']}
Intuition: {bd['moon_validation']['score']}% — {bd['moon_validation']['reason']}"""

    if bd.get("edge_yoga"):
        ey = bd["edge_yoga"]
        prompt += f"\nEdge Case: {ey['yoga'].title()} — {ey['reason']}"

    if bd.get("mutual_reception", {}).get("found"):
        prompt += f"\nBonus: Mutual Reception — {bd['mutual_reception']['reason']}"

    locks = bd.get("jaimini_locks", {})
    lock_count = sum(1 for v_l in locks.values() if v_l)
    if lock_count > 0:
        prompt += f"\nJaimini Triple-Lock: {lock_count}/3 passed (+{bd.get('jaimini_bonus', 0)}% bonus)"

    da = v.get("domain_audit", {})
    if da.get("flags") or da.get("bonuses") or da.get("hard_truth"):
        prompt += f"\n\n═══ DOMAIN AUDIT: {da.get('label', 'GENERAL')} ═══"
        for flag in da.get("flags", []):
            prompt += f"\n⚠ {flag['type']}: {flag['message']}"
            if flag.get("penalty"):
                prompt += f" (penalty: {flag['penalty']}%)"
        for bonus in da.get("bonuses", []):
            prompt += f"\n✓ {bonus['type']}: {bonus['message']}"
            if bonus.get("bonus"):
                prompt += f" (bonus: +{bonus['bonus']}%)"
        if da.get("hard_truth"):
            prompt += f"\nTHE HARD TRUTH: {da['hard_truth']}"
        if da.get("delay_days"):
            prompt += f"\nEXPECTED DELAY: +{da['delay_days']} days"
        prompt += f"\nNet domain adjustment: {da.get('net_adjustment', 0)}%"

    conf = v.get("confluence", {})
    if conf.get("sync_detected"):
        prompt += f"\n\n═══ CONFLUENCE ═══\n{conf['message']}\nIntensity: {conf['intensity_multiplier']}x"

    nc = v.get("natal_context", {})
    prompt += f"\n\n═══ NATAL CONTEXT ═══\nCurrent Life Chapter: {nc.get('dasha', 'unknown')}"

    wp = v.get("weakest_planet", {})
    prompt += f"\n\n═══ REMEDY TARGET ═══\nWeakest planet: {wp.get('planet', 'unknown')}\nWeakness: {', '.join(wp.get('reasons', []))}"

    is_india = locale.lower() in ["in", "india"]

    prompt += f"""

═══ YOUR INSTRUCTIONS ═══
1. Start with the verdict as a single decisive sentence.
2. Explain WHY in 2-3 sentences using the breakdown above. Reference the momentum result and domain audit findings.
3. If there is a HARD TRUTH from the domain audit, state it directly. No softening.
4. Give the timing window.
5. End with ONE specific action — THE MOVE — the user should take this week.
6. Keep it under 150 words total.
7. ZERO astrological jargon — no Sanskrit terms, no house numbers, no planet names.

9. If an EMOTIONAL CONTEXT block appears above, follow its tone instructions.
   The verdict and data are unchanged — only adjust how you deliver them.
10. If a TIME CONTEXT block appears above, adjust warmth accordingly.
8. Write as a confident executive advisor, not an astrologer.
"""

    if is_india:
        prompt += "9. For the remedy, suggest a specific ritual practice.\n"
    else:
        prompt += "9. For the remedy, suggest a specific energy practice.\n"

    return prompt



# ═══════════════════════════════════════════════════════════════════
# COOLDOWN CHECK
# ═══════════════════════════════════════════════════════════════════

def check_cooldown(last_prashna_time: Optional[str], cooldown_hours: int = PRASHNA_COOLDOWN_HOURS) -> dict:
    """
    Check if the user is still in cooldown from their last Prashna question.

    Args:
        last_prashna_time: ISO 8601 timestamp of last question, or None
        cooldown_hours: Hours between allowed questions (default 24)

    Returns:
        {"allowed": bool, "remaining_seconds": int, "cooldown_until": str or None}
    """
    if not last_prashna_time:
        return {"allowed": True, "remaining_seconds": 0, "cooldown_until": None}

    try:
        if isinstance(last_prashna_time, str):
            last_time = datetime.fromisoformat(last_prashna_time.replace("Z", "+00:00"))
        else:
            last_time = last_prashna_time

        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        cooldown_end = last_time + timedelta(hours=cooldown_hours)
        remaining = (cooldown_end - now).total_seconds()

        if remaining > 0:
            return {
                "allowed": False,
                "remaining_seconds": int(remaining),
                "cooldown_until": cooldown_end.isoformat(),
                "message": _format_cooldown_message(int(remaining)),
            }
        else:
            return {"allowed": True, "remaining_seconds": 0, "cooldown_until": None}

    except Exception as e:
        logger.warning(f"Cooldown check error: {e}")
        return {"allowed": True, "remaining_seconds": 0, "cooldown_until": None}


def _format_cooldown_message(seconds: int) -> str:
    """Format remaining cooldown into a human-readable message."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"The Oracle reads your subconscious frequency at the exact moment you ask. That signal needs {hours}h {minutes}m to fully settle before the next reading can be accurate. The universe calculates once — let it complete."
    elif minutes > 0:
        return f"Your signal is almost calibrated. {minutes} minutes until the Oracle can read a fresh frequency."
    else:
        return "Your Oracle is recalibrating — almost ready to read your next frequency."


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT (for /prashna endpoint in main.py)
# ═══════════════════════════════════════════════════════════════════


def run_prashna_engine(
    question: str,
    lat: float,
    lng: float,
    timestamp: Optional[datetime] = None,
    jaimini_data: Optional[dict] = None,
    natal_dasha: Optional[str] = None,
    natal_chart_data: Optional[dict] = None,
    user_name: str = "User",
    locale: str = "global",
    domain_override: Optional[str] = None,
) -> dict:
    """
    Full Prashna pipeline v2.
    Same as before + natal_chart_data param + proof_bars/domain_audit/confluence in output.
    Cooldown: 4 hours (was 24).
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    chart = cast_prashna_chart(lat, lng, timestamp)

    verdict_data = compute_prashna_verdict(
        chart=chart,
        question=question,
        jaimini_data=jaimini_data,
        natal_dasha=natal_dasha,
        natal_chart_data=natal_chart_data,
        domain_override=domain_override,
    )

    claude_prompt = build_prashna_prompt(
        verdict_data=verdict_data,
        question=question,
        user_name=user_name,
        locale=locale,
    )

    cooldown_until = (timestamp + timedelta(hours=4)).isoformat()

    return {
        "verdict": verdict_data["verdict"],
        "score": verdict_data["score"],
        "label": verdict_data["label"],
        "domain": verdict_data["domain"],
        "timing": verdict_data["timing"],
        "breakdown": verdict_data["breakdown"],
        "prashna_chart": verdict_data["prashna_chart"],
        "weakest_planet": verdict_data["weakest_planet"],
        "natal_context": verdict_data["natal_context"],
        "cooldown_until": cooldown_until,
        "claude_prompt": claude_prompt,
        "full_chart": chart,
        "proof_bars": verdict_data["proof_bars"],
        "domain_audit": verdict_data["domain_audit"],
        "confluence": verdict_data["confluence"],
    }

