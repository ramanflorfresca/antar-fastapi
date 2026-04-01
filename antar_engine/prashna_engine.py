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
    "wealth":       [2, 11],
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

def compute_prashna_verdict(
    chart: dict,
    question: str,
    jaimini_data: Optional[dict] = None,
    natal_dasha: Optional[str] = None,
) -> dict:
    """
    Master scoring function. Combines all 4 steps + edge cases + bonuses.

    Args:
        chart: Output of cast_prashna_chart()
        question: The user's question
        jaimini_data: Stored jaimini_data JSONB from charts table (for triple-lock)
        natal_dasha: Current dasha string e.g. "Mars-Moon"

    Returns:
        Complete verdict dict ready for Claude to explain.
    """
    # Detect domain
    domain, houses = detect_domain(question)

    # Determine significators
    lagna_sign = chart["lagna_sign"]
    lord_1_id = get_sign_lord(lagna_sign)

    # Primary house of interest (use first in list)
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

    # ─── Step D+: Void of Course Moon ───
    voc = check_void_of_course(chart)

    # ─── Navamsa Genuineness Check ───
    genuineness = check_navamsa_genuineness(chart)

    # ─── Edge Cases (only if Ithasala is neutral or negative) ───
    edge_yoga = None
    if step_c["type"] != "ithasala":
        edge_yoga = check_edge_yogas(chart, lord_1_id, lord_x_id)

    # ─── Mutual Reception Bonus ───
    mutual_rec = check_mutual_reception(chart, lord_1_id, lord_x_id)

    # ─── Compute Base Score ───
    base_score = step_a["score"] + step_b["score"] + step_c["score"] + step_d["score"]

    # Add mutual reception bonus
    if mutual_rec["found"]:
        base_score += mutual_rec["score"]

    # Edge yoga handling
    if edge_yoga:
        if edge_yoga.get("override"):
            # Muthashila overrides everything
            base_score = edge_yoga["score"]
        else:
            # Nakta/Yamaya add to base (but only if base isn't already highly positive)
            if base_score < 70:
                base_score += edge_yoga["score"]

    # ─── Jaimini Triple-Lock Bonus ───
    jaimini_locks = {"vimsottari": False, "chara_dasha": False, "arudha": False}
    jaimini_bonus = 0

    if jaimini_data:
        try:
            jaimini_locks = _check_jaimini_triple_lock(jaimini_data, domain, houses)
            lock_count = sum(1 for v in jaimini_locks.values() if v)
            jaimini_bonus = lock_count * 5  # +5% per lock
            base_score += jaimini_bonus
        except Exception as e:
            logger.warning(f"Jaimini triple-lock check failed: {e}")

    # ─── Void of Course Moon Penalty ───
    # If Moon is VoC, a YES verdict will stall. Apply hard penalty.
    if voc["void_of_course"]:
        base_score += voc["penalty"]  # -15

    # ─── Navamsa Genuineness Penalty ───
    # If the question is flagged as potentially fruitless, reduce score.
    if genuineness["penalty"] < 0:
        base_score += genuineness["penalty"]  # -5 or -10

    # ─── Clamp Score ───
    final_score = max(0, min(100, base_score))

    # ─── Determine Verdict ───
    if final_score >= 85:
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

    # ─── Weakest Planet for Remedy ───
    weakest = find_weakest_planet(chart)

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
            "void_of_course": voc,
            "navamsa_genuineness": genuineness,
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
    """
    Build the system prompt for Claude to explain the pre-calculated verdict
    in plain English. Claude does NOT compute — it only explains.
    """
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

═══ PRASHNA CHART (cast at the moment of the question) ═══
Lagna (Ascendant): {pc['lagna_sign']} at {pc['lagna_degree']:.1f}°
Moon Nakshatra: {pc['moon_nakshatra']}
Moon House: {pc['moon_house']}th
Significator 1 (You): {pc['significator_1']['planet']} in {pc['significator_1']['sign']} ({pc['significator_1']['house']}th house)
Significator 2 (Goal): {pc['significator_x']['planet']} in {pc['significator_x']['sign']} ({pc['significator_x']['house']}th house)

═══ SCORING BREAKDOWN ═══
Step A — Environment: {bd['lagna_strength']['score']}% — {bd['lagna_strength']['reason']}
Step B — Connection: {bd['lord_connection']['score']}% — {bd['lord_connection']['reason']}
Step C — Momentum: {bd['ithasala']['score']}% ({bd['ithasala']['type']}) — {bd['ithasala']['reason']}
Step D — Intuition: {bd['moon_validation']['score']}% — {bd['moon_validation']['reason']}
"""

    # Void of Course Moon
    voc = bd.get("void_of_course", {})
    if voc.get("void_of_course"):
        prompt += f"⚠ VOID OF COURSE MOON: {voc['reason']} (penalty: {voc['penalty']}%)\n"
    elif voc.get("next_aspect"):
        prompt += f"Moon Momentum: {voc['reason']}\n"

    # Navamsa Genuineness
    genuineness = bd.get("navamsa_genuineness", {})
    if genuineness.get("penalty", 0) < 0:
        prompt += f"⚠ GENUINENESS FLAG: {genuineness['reason']} (penalty: {genuineness['penalty']}%)\n"
    elif genuineness.get("genuine"):
        prompt += f"Question Validity: {genuineness['reason']}\n"

    if bd.get("edge_yoga"):
        ey = bd["edge_yoga"]
        prompt += f"Edge Case: {ey['yoga'].title()} — {ey['reason']}\n"

    if bd.get("mutual_reception", {}).get("found"):
        prompt += f"Bonus: Mutual Reception — {bd['mutual_reception']['reason']}\n"

    locks = bd.get("jaimini_locks", {})
    lock_count = sum(1 for v_l in locks.values() if v_l)
    if lock_count > 0:
        prompt += f"Jaimini Triple-Lock: {lock_count}/3 passed (+{v['breakdown']['jaimini_bonus']}% bonus)\n"

    # Natal context
    nc = v.get("natal_context", {})
    prompt += f"\n═══ NATAL CONTEXT ═══\nCurrent Life Chapter: {nc.get('dasha', 'unknown')}\n"

    # Remedy
    wp = v.get("weakest_planet", {})
    prompt += f"\n═══ REMEDY TARGET ═══\nWeakest planet in this chart: {wp.get('planet', 'unknown')}\nWeakness: {', '.join(wp.get('reasons', []))}\n"

    # Instructions
    is_india = locale.lower() in ["in", "india"]

    prompt += f"""
═══ YOUR INSTRUCTIONS ═══
1. Start with the verdict as a single decisive sentence.
2. Explain WHY in 2-3 sentences using the breakdown above. Reference the momentum (Ithasala) result specifically.
3. Give the timing window.
4. End with ONE specific action the user should take this week.
5. Keep it under 150 words total.
6. ZERO astrological jargon — no Sanskrit terms, no house numbers, no planet names.
7. Write as a confident executive advisor, not an astrologer.
"""

    if is_india:
        prompt += "8. For the remedy, suggest a specific ritual practice (e.g., 'Donate mustard oil on Saturday').\n"
    else:
        prompt += "8. For the remedy, suggest a specific energy practice (e.g., 'Express gratitude to a mentor this week').\n"

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
        return f"Your next Oracle question opens in {hours}h {minutes}m. Each question captures a unique moment — let this one settle first."
    elif minutes > 0:
        return f"Your next Oracle question opens in {minutes} minutes."
    else:
        return "Your Oracle is almost ready."


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
    user_name: str = "User",
    locale: str = "global",
) -> dict:
    """
    Full Prashna pipeline:
    1. Cast Moment Chart
    2. Detect domain
    3. Run 4-step scoring + edge cases
    4. Build Claude prompt
    5. Return everything

    This is what main.py calls. Claude call happens in main.py after this returns.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Step 0: Cast the chart
    chart = cast_prashna_chart(lat, lng, timestamp)

    # Steps A-D + edge cases + score
    verdict_data = compute_prashna_verdict(
        chart=chart,
        question=question,
        jaimini_data=jaimini_data,
        natal_dasha=natal_dasha,
    )

    # Build prompt for Claude
    claude_prompt = build_prashna_prompt(
        verdict_data=verdict_data,
        question=question,
        user_name=user_name,
        locale=locale,
    )

    # Cooldown timestamp for response
    cooldown_until = (timestamp + timedelta(hours=PRASHNA_COOLDOWN_HOURS)).isoformat()

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
        "full_chart": chart,  # For logging / debug
    }
