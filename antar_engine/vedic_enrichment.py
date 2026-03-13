# antar_engine/vedic_enrichment.py
"""
Vedic Enrichment Layer
======================
Adds the high-signal features missing from antar_ephemeris.py.

ALL functions are pure Python — no DB queries, no side effects.
Input: chart_data dict (as returned by calculate_chart())
Output: enriched fields, ready to merge back into chart_data or append to LLM prompt

USAGE in calculate_chart() (antar_ephemeris.py):

    from antar_engine.vedic_enrichment import enrich_chart
    result = enrich_chart(chart_data, jd_ut)

USAGE in /predict (prompt injection):

    from antar_engine.vedic_enrichment import build_enrichment_context
    enrichment_block = build_enrichment_context(chart_data, transit_planets)
    prompt += f"\\n\\n{enrichment_block}"

What this adds to each planet:
  is_retrograde     bool   — computed from daily motion delta (was always False)
  is_combust        bool   — within combustion orb of Sun
  combust_degree    float  — arc distance from Sun (None if not combust)
  is_vargottama     bool   — same sign in D-1 and D-9
  dig_bala          bool   — in the house of directional strength
  effective_strength str   — upgrade/downgrade of sthana bala considering combust/retro

What this adds to chart_data:
  nakshatra_meta    dict   — deity, shakti, tara class, guna, gender for all 27 nakshatras
  panchanga         dict   — tithi, vara, yoga (panchanga), karana for birth moment
  gandanta_planets  list   — planets in sensitive junction degrees
  sade_sati         dict   — phase (1/2/3/none), years_remaining (for transit Saturn)
  sarvashtakavarga  dict   — total bindus per sign for transit scoring
  yoga_bhanga       list   — list of yoga names cancelled by bhanga rules
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import math

# ─────────────────────────────────────────────────────────────────────────────
# SHARED CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]
SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

NAKSHATRAS = [
    "Ashvini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. RETROGRADE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

# Rahu and Ketu are always retrograde (mean node convention)
ALWAYS_RETROGRADE = {"Rahu", "Ketu"}

def compute_retrograde(planet: str, lon_today: float, lon_tomorrow: float) -> bool:
    """
    Returns True if planet is moving backward (retrograde).
    lon_today and lon_tomorrow are sidereal degrees.
    """
    if planet in ALWAYS_RETROGRADE:
        return True
    delta = lon_tomorrow - lon_today
    # Wrap-safe: correct for 360° crossing
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360
    return delta < 0


def add_retrograde_to_chart(chart_data: Dict, jd_ut: float) -> None:
    """
    Mutates chart_data.planets in-place: sets is_retrograde correctly.
    Requires jd_ut (Julian Day for birth moment).
    Calls planet_longitude for JD+1 to compute daily motion.
    """
    try:
        from antar_engine.antar_ephemeris import planet_longitude, lahiri_ayanamsa
    except ImportError:
        # Fallback: import the module-level function directly
        from antar_ephemeris import planet_longitude, lahiri_ayanamsa

    ayanamsa_t1 = lahiri_ayanamsa(jd_ut + 1)
    for planet, data in chart_data["planets"].items():
        if planet in ALWAYS_RETROGRADE:
            data["is_retrograde"] = True
            continue
        try:
            lon_t1 = (planet_longitude(planet, jd_ut + 1) - ayanamsa_t1) % 360
            data["is_retrograde"] = compute_retrograde(planet, data["longitude"], lon_t1)
            data["daily_motion"] = round(
                (lon_t1 - data["longitude"] + 180) % 360 - 180, 4
            )
        except Exception:
            data["is_retrograde"] = False
            data["daily_motion"] = None


# ─────────────────────────────────────────────────────────────────────────────
# 1b. RETROGRADE GRADATIONS (Chesta Bala component)
# ─────────────────────────────────────────────────────────────────────────────

# Strength multiplier by motion state
RETROGRADE_STATES = {
    "direct":    1.00,   # normal direct motion
    "anuvakra":  0.70,   # slowing before/after station (|dm| < 0.3)
    "mandatara": 0.60,   # at station — nearly motionless (|dm| < 0.05)
    "vakri":     0.80,   # normal retrograde
}


def get_retrograde_state(
    planet: str,
    daily_motion: Optional[float],
    is_retrograde: bool,
) -> Tuple[str, float]:
    """
    Returns (state_name, strength_multiplier).

    States:
      direct    — normal forward motion
      anuvakra  — pre/post station (slowing or speeding up, |dm| < 0.3)
      mandatara — at station, nearly motionless (|dm| < 0.05)
      vakri     — retrograde

    Rahu/Ketu are always vakri at their mean daily motion of ~0.053°/day.
    """
    if planet in ALWAYS_RETROGRADE:
        return "vakri", RETROGRADE_STATES["vakri"]

    if daily_motion is None:
        state = "vakri" if is_retrograde else "direct"
        return state, RETROGRADE_STATES[state]

    dm = abs(daily_motion)

    if not is_retrograde:
        if dm >= 0.3:
            return "direct", RETROGRADE_STATES["direct"]
        return "anuvakra", RETROGRADE_STATES["anuvakra"]  # slowing before station

    # Retrograde
    if dm <= 0.05:
        return "mandatara", RETROGRADE_STATES["mandatara"]
    if dm <= 0.3:
        return "anuvakra", RETROGRADE_STATES["anuvakra"]
    return "vakri", RETROGRADE_STATES["vakri"]


def add_retrograde_state_to_chart(chart_data: Dict) -> None:
    """
    Mutates chart_data.planets in-place: adds retrograde_state and
    chesta_bala_multiplier based on daily_motion.
    Call AFTER add_retrograde_to_chart (which sets is_retrograde and daily_motion).
    """
    for planet, data in chart_data["planets"].items():
        state, mult = get_retrograde_state(
            planet,
            data.get("daily_motion"),
            data.get("is_retrograde", False),
        )
        data["retrograde_state"]       = state
        data["chesta_bala_multiplier"] = mult


# ─────────────────────────────────────────────────────────────────────────────
# 2. COMBUSTION (ASTAANGA)
# ─────────────────────────────────────────────────────────────────────────────

# Combustion orbs in degrees (Parashara / Sarwartha Chintamani)
COMBUSTION_ORBS: Dict[str, Dict] = {
    "Moon":    {"direct": 12.0, "retrograde": 12.0},
    "Mars":    {"direct": 17.0, "retrograde": 17.0},
    "Mercury": {"direct": 14.0, "retrograde": 12.0},
    "Jupiter": {"direct": 11.0, "retrograde": 11.0},
    "Venus":   {"direct": 10.0, "retrograde":  8.0},
    "Saturn":  {"direct": 15.0, "retrograde": 15.0},
}


def arc_distance(lon1: float, lon2: float) -> float:
    """Shortest arc between two zodiac longitudes (0–180)."""
    diff = abs(lon1 - lon2) % 360
    return diff if diff <= 180 else 360 - diff


def add_combustion_to_chart(chart_data: Dict) -> None:
    """
    Mutates chart_data.planets in-place: adds is_combust, combust_degree.
    Sun, Rahu, Ketu cannot be combust.
    """
    sun_lon = chart_data["planets"]["Sun"]["longitude"]
    for planet, data in chart_data["planets"].items():
        if planet in ("Sun", "Rahu", "Ketu"):
            data["is_combust"] = False
            data["combust_degree"] = None
            continue
        is_retro = data.get("is_retrograde", False)
        orb_key  = "retrograde" if is_retro else "direct"
        orb      = COMBUSTION_ORBS.get(planet, {}).get(orb_key, 0)
        dist     = arc_distance(data["longitude"], sun_lon)
        combust  = dist <= orb
        data["is_combust"]    = combust
        data["combust_degree"] = round(dist, 2) if combust else None


# ─────────────────────────────────────────────────────────────────────────────
# 3. VARGOTTAMA FLAG
# ─────────────────────────────────────────────────────────────────────────────

def _navamsa_sign(lon_degrees: float) -> str:
    """
    Compute D-9 (Navamsa) sign from sidereal longitude.
    Traditional Parashara method:
      Movable signs (Aries, Cancer, Libra, Capricorn): start from Aries
      Fixed signs (Taurus, Leo, Scorpio, Aquarius): start from Capricorn
      Dual signs (Gemini, Virgo, Sagittarius, Pisces): start from Cancer
    """
    NAVAMSA_STARTS = {
        "Aries": "Aries", "Taurus": "Capricorn", "Gemini": "Cancer",
        "Cancer": "Cancer", "Leo": "Aries", "Virgo": "Cancer",
        "Libra": "Libra", "Scorpio": "Capricorn", "Sagittarius": "Libra",
        "Capricorn": "Capricorn", "Aquarius": "Aries", "Pisces": "Cancer",
    }
    sign_idx   = int(lon_degrees / 30) % 12
    d1_sign    = SIGNS[sign_idx]
    degree     = lon_degrees % 30
    pada_idx   = int(degree / (30 / 9))  # 0–8
    start      = NAVAMSA_STARTS[d1_sign]
    start_idx  = SIGN_INDEX[start]
    d9_idx     = (start_idx + pada_idx) % 12
    return SIGNS[d9_idx]


def add_vargottama_to_chart(chart_data: Dict) -> None:
    """
    Mutates chart_data.planets in-place.
    Adds: is_vargottama, d9_sign, pada_lord.

    Vargottama: same sign in D-1 and D-9 (extremely strong).
    Pada lord: lord of the navamsa sign = sub-ruler of the nakshatra pada.
    """
    for planet, data in chart_data["planets"].items():
        d1_sign   = data["sign"]
        d9_sign   = _navamsa_sign(data["longitude"])
        pada_lord = SIGN_LORDS.get(d9_sign, "")
        data["is_vargottama"] = (d1_sign == d9_sign)
        data["d9_sign"]       = d9_sign
        data["pada_lord"]     = pada_lord  # sub-ruler: career/marriage significator


# ─────────────────────────────────────────────────────────────────────────────
# 4. DIG BALA (DIRECTIONAL STRENGTH)
# ─────────────────────────────────────────────────────────────────────────────

# House of maximum directional strength per planet
DIG_BALA_HOUSE: Dict[str, int] = {
    "Jupiter": 1, "Mercury": 1,
    "Sun": 10,    "Mars": 10,
    "Saturn": 7,
    "Venus": 4,   "Moon": 4,
}


def add_dig_bala_to_chart(chart_data: Dict) -> None:
    """
    Mutates chart_data.planets in-place: adds dig_bala bool.
    Rahu/Ketu not assigned dig bala in tradition.
    """
    lagna_idx = chart_data["lagna"]["sign_index"]
    for planet, data in chart_data["planets"].items():
        peak_house = DIG_BALA_HOUSE.get(planet)
        if peak_house is None:
            data["dig_bala"] = False
            continue
        planet_house = (data["sign_index"] - lagna_idx) % 12 + 1
        data["dig_bala"] = (planet_house == peak_house)


# ─────────────────────────────────────────────────────────────────────────────
# 5. EFFECTIVE STRENGTH (composite)
# ─────────────────────────────────────────────────────────────────────────────

def compute_effective_strength(data: Dict) -> str:
    """
    Upgrade or downgrade sthana bala considering combust, retrograde, vargottama.
    Returns: "exalted_strong" | "exalted" | "own" | "vargottama" | "friendly" |
             "neutral" | "combust" | "debilitated" | "debilitated_combust"
    """
    base     = data.get("strength", "neutral")
    combust  = data.get("is_combust", False)
    retro    = data.get("is_retrograde", False)
    varg     = data.get("is_vargottama", False)
    dig      = data.get("dig_bala", False)

    # Debilitated + combust = worst
    if base == "debilitated" and combust:
        return "debilitated_combust"
    if base == "debilitated":
        return "debilitated"
    # Combust overrides other strengths (except exalted by some traditions)
    if combust and base not in ("exalted", "own"):
        return "combust"
    # Vargottama elevates own/friendly
    if varg and base in ("own", "friendly", "exalted"):
        return f"{base}_vargottama"
    # Dig bala elevates neutral/friendly
    if dig and base in ("neutral", "friendly"):
        return "dig_bala_strong"
    return base


# ─────────────────────────────────────────────────────────────────────────────
# 5b. NAISARGIKA BALA (Natural Strength)
# ─────────────────────────────────────────────────────────────────────────────

# Fixed natural strength rank (Parashara): Sun=7 (strongest), Saturn=1 (weakest)
# Rahu/Ketu not assigned in this system
NAISARGIKA_BALA: Dict[str, int] = {
    "Sun": 7, "Moon": 6, "Venus": 5, "Jupiter": 4,
    "Mercury": 3, "Mars": 2, "Saturn": 1,
}


def get_naisargika_bala(planet: str) -> Optional[int]:
    """Natural strength rank 1-7. None for Rahu/Ketu."""
    return NAISARGIKA_BALA.get(planet)


def add_naisargika_bala_to_chart(chart_data: Dict) -> None:
    """Mutates chart_data.planets: adds naisargika_bala rank."""
    for planet, data in chart_data["planets"].items():
        data["naisargika_bala"] = get_naisargika_bala(planet)


# ─────────────────────────────────────────────────────────────────────────────
# 6. NAKSHATRA METADATA (deity, shakti, guna, tara class, gender)
# ─────────────────────────────────────────────────────────────────────────────

# Data per nakshatra: (deity, shakti_power, guna, gender, tara_type_from_janma)
# Tara types cycle in groups of 9: Janma, Sampat, Vipat, Kshema, Pratyari,
# Sadhaka, Vadha, Mitra, Atimitra (repeats 3x for 27 nakshatras)
TARA_CYCLE = ["Janma","Sampat","Vipat","Kshema","Pratyari","Sadhaka","Vadha","Mitra","Atimitra"]

NAKSHATRA_META: Dict[str, Dict] = {
    "Ashvini":         {"deity": "Ashvini Kumaras",  "shakti": "Power to heal",           "guna": "Rajas",  "gender": "Male"},
    "Bharani":         {"deity": "Yama",              "shakti": "Power to cleanse",         "guna": "Rajas",  "gender": "Female"},
    "Krittika":        {"deity": "Agni",              "shakti": "Power to burn",            "guna": "Rajas",  "gender": "Female"},
    "Rohini":          {"deity": "Brahma",            "shakti": "Power to grow",            "guna": "Rajas",  "gender": "Female"},
    "Mrigashira":      {"deity": "Soma (Moon)",       "shakti": "Power to give fulfillment","guna": "Tamas",  "gender": "Neutral"},
    "Ardra":           {"deity": "Rudra",             "shakti": "Power to make effort",     "guna": "Tamas",  "gender": "Female"},
    "Punarvasu":       {"deity": "Aditi",             "shakti": "Power to gain wealth",     "guna": "Rajas",  "gender": "Female"},
    "Pushya":          {"deity": "Brihaspati",        "shakti": "Power to create spiritual energy","guna": "Tamas","gender": "Male"},
    "Ashlesha":        {"deity": "Nagas (Serpents)",  "shakti": "Power to destroy by poison","guna": "Sattva","gender": "Female"},
    "Magha":           {"deity": "Pitrs (Ancestors)", "shakti": "Power to leave the body",  "guna": "Tamas",  "gender": "Female"},
    "Purva Phalguni":  {"deity": "Bhaga",             "shakti": "Power to procreate",       "guna": "Rajas",  "gender": "Female"},
    "Uttara Phalguni": {"deity": "Aryaman",           "shakti": "Power to give prosperity", "guna": "Rajas",  "gender": "Female"},
    "Hasta":           {"deity": "Savitar",           "shakti": "Power to manifest goals",  "guna": "Rajas",  "gender": "Male"},
    "Chitra":          {"deity": "Tvashtr",           "shakti": "Power to accumulate merit","guna": "Tamas",  "gender": "Female"},
    "Swati":           {"deity": "Vayu",              "shakti": "Power to scatter like wind","guna": "Tamas", "gender": "Female"},
    "Vishakha":        {"deity": "Indra & Agni",      "shakti": "Power to achieve goals",   "guna": "Rajas",  "gender": "Female"},
    "Anuradha":        {"deity": "Mitra",             "shakti": "Power of worship",         "guna": "Tamas",  "gender": "Male"},
    "Jyeshtha":        {"deity": "Indra",             "shakti": "Power to rise above",      "guna": "Sattva", "gender": "Female"},
    "Mula":            {"deity": "Nirriti (Kali)",    "shakti": "Power to ruin and destroy","guna": "Tamas",  "gender": "Neutral"},
    "Purva Ashadha":   {"deity": "Apas (Waters)",     "shakti": "Power to invigorate",      "guna": "Rajas",  "gender": "Female"},
    "Uttara Ashadha":  {"deity": "Vishvedevas",       "shakti": "Power to grant unchallengeable victory","guna":"Rajas","gender": "Female"},
    "Shravana":        {"deity": "Vishnu",            "shakti": "Power to connect",         "guna": "Rajas",  "gender": "Male"},
    "Dhanishtha":      {"deity": "Eight Vasus",       "shakti": "Power to give abundance",  "guna": "Tamas",  "gender": "Female"},
    "Shatabhisha":     {"deity": "Varuna",            "shakti": "Power to heal",            "guna": "Tamas",  "gender": "Neutral"},
    "Purva Bhadrapada":{"deity": "Aja Ekapad",        "shakti": "Power to uplift",          "guna": "Rajas",  "gender": "Male"},
    "Uttara Bhadrapada":{"deity":"Ahir Budhanya",     "shakti": "Power to bring rain",      "guna": "Tamas",  "gender": "Female"},
    "Revati":          {"deity": "Pushan",            "shakti": "Power of nourishment",     "guna": "Sattva", "gender": "Female"},
}


def get_nakshatra_meta(nakshatra_name: str) -> Dict:
    """Return full metadata dict for a nakshatra. Safe fallback if unknown."""
    return NAKSHATRA_META.get(nakshatra_name, {
        "deity": "Unknown", "shakti": "Unknown", "guna": "Unknown", "gender": "Unknown"
    })


def get_tara_class(moon_nakshatra: str, planet_nakshatra: str) -> str:
    """
    Tara Bala: relationship of planet's nakshatra to the Moon's nakshatra.
    Starts counting from the Moon's nakshatra as 'Janma'.
    """
    moon_idx   = NAKSHATRAS.index(moon_nakshatra) if moon_nakshatra in NAKSHATRAS else 0
    planet_idx = NAKSHATRAS.index(planet_nakshatra) if planet_nakshatra in NAKSHATRAS else 0
    offset     = (planet_idx - moon_idx) % 27
    tara_idx   = offset % 9
    return TARA_CYCLE[tara_idx]


TARA_QUALITY = {
    "Janma": "sensitive",   # birth star — sensitive, self-referential
    "Sampat": "wealth",     # 2nd — wealth and prosperity
    "Vipat": "danger",      # 3rd — accidents, obstacles, danger
    "Kshema": "support",    # 4th — comfort, stability, support
    "Pratyari": "obstacle", # 5th — enemy, obstacle
    "Sadhaka": "goal",      # 6th — achievement, goal fulfillment
    "Vadha": "destructive", # 7th — destruction, harm
    "Mitra": "friendly",    # 8th — friend, ally
    "Atimitra": "best",     # 9th — great friend, very auspicious
}


# ─────────────────────────────────────────────────────────────────────────────
# 7. PANCHANGA (Five Limbs of the Day)
# ─────────────────────────────────────────────────────────────────────────────

TITHI_NAMES = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami",
    "Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi",
    "Purnima",  # Full moon (15)
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami",
    "Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi",
    "Amavasya", # New moon (30)
]

PANCHANGA_YOGA_NAMES = [
    "Vishkumbha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma",
    "Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra",
    "Siddhi","Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha",
    "Shukla","Brahma","Indra","Vaidhriti",
]

KARANA_NAMES = [
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",  # repeating 7
    "Shakuni","Chatushpada","Naga","Kimstughna",  # fixed 4 (at start/end of lunar month)
]

VARA_NAMES = {1:"Sunday",2:"Monday",3:"Tuesday",4:"Wednesday",5:"Thursday",6:"Friday",0:"Saturday"}

# Yoga auspiciousness (simplified):
YOGA_AUSPICIOUS = {
    "Priti","Ayushman","Saubhagya","Shobhana","Sukarma","Dhriti","Vriddhi",
    "Dhruva","Harshana","Siddhi","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra",
}
YOGA_INAUSPICIOUS = {
    "Vishkumbha","Atiganda","Shula","Ganda","Vyaghata","Vajra","Vyatipata","Parigha","Vaidhriti",
}


def compute_panchanga(sun_lon: float, moon_lon: float, jd_ut: float) -> Dict:
    """
    Compute the five panchanga elements from birth-moment longitudes.
    sun_lon, moon_lon: sidereal degrees.
    jd_ut: Julian Day for weekday calculation.
    """
    # Tithi: each 12° of Moon-Sun separation = one tithi
    moon_sun_diff = (moon_lon - sun_lon) % 360
    tithi_num     = int(moon_sun_diff / 12)          # 0-29
    tithi_name    = TITHI_NAMES[tithi_num]
    tithi_paksha  = "Shukla" if tithi_num < 15 else "Krishna"  # waxing/waning

    # Panchanga Yoga: (Sun + Moon) / 13.333...
    yoga_num  = int(((sun_lon + moon_lon) % 360) / (360 / 27))
    yoga_name = PANCHANGA_YOGA_NAMES[yoga_num % 27]
    yoga_quality = (
        "auspicious"   if yoga_name in YOGA_AUSPICIOUS   else
        "inauspicious" if yoga_name in YOGA_INAUSPICIOUS else
        "neutral"
    )

    # Karana: half-tithi (each 6° of Moon-Sun = one karana)
    karana_num = int(moon_sun_diff / 6) % 7  # simplified: repeating group
    karana_name = KARANA_NAMES[karana_num]

    # Vara: weekday from Julian Day
    # JD 0 = Monday (Jan 1, 4713 BC was a Monday)
    # Day of week: (int(jd_ut + 1.5) % 7) maps to Sun/Mon/Tue...
    vara_idx  = int(jd_ut + 1.5) % 7
    vara_name = VARA_NAMES.get(vara_idx, "Unknown")

    return {
        "tithi":         tithi_name,
        "tithi_number":  tithi_num + 1,
        "tithi_paksha":  tithi_paksha,
        "vara":          vara_name,
        "yoga":          yoga_name,
        "yoga_quality":  yoga_quality,
        "karana":        karana_name,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. GANDANTA ZONES
# ─────────────────────────────────────────────────────────────────────────────

# Gandanta = junction of water sign end + fire sign start
# Water signs end at: 120° (Cancer), 240° (Scorpio), 360°/0° (Pisces)
# Fire signs start at: 0° (Aries), 120° (Leo), 240° (Sagittarius)
# Sensitive zone = last 3°20' (3.333°) of water signs AND first 3°20' of fire signs
GANDANTA_ORB = 3 + 20/60  # 3°20' = 3.333°

GANDANTA_BOUNDARIES = [
    (120 - GANDANTA_ORB, 120 + GANDANTA_ORB, "Cancer–Aries junction"),
    (240 - GANDANTA_ORB, 240 + GANDANTA_ORB, "Scorpio–Sagittarius junction"),
    (360 - GANDANTA_ORB, 360,                 "Pisces–Aries junction"),
    (0,                  GANDANTA_ORB,         "Pisces–Aries junction"),
]


def is_gandanta(longitude: float) -> Tuple[bool, Optional[str]]:
    """Returns (True, zone_name) if longitude is in a Gandanta zone, else (False, None)."""
    lon = longitude % 360
    for start, end, label in GANDANTA_BOUNDARIES:
        if start <= lon <= end:
            return True, label
    return False, None


def find_gandanta_planets(chart_data: Dict) -> List[Dict]:
    """Return list of planets in Gandanta zones."""
    result = []
    for planet, data in chart_data["planets"].items():
        flag, zone = is_gandanta(data["longitude"])
        if flag:
            result.append({
                "planet": planet,
                "sign":   data["sign"],
                "degree": data["degree"],
                "zone":   zone,
            })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 9. SADE SATI — THREE-PHASE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

SATURN_YEAR_PER_SIGN = 2.46  # years (29.5 / 12)


def get_sade_sati_phase(
    natal_moon_sign: str,
    transit_saturn_sign: str,
) -> Optional[Dict]:
    """
    Returns sade sati phase dict if active, None if not in sade sati.

    Phase 1 (Preparatory): Saturn in 12th from natal Moon
    Phase 2 (Peak):        Saturn over natal Moon sign
    Phase 3 (Transition):  Saturn in 2nd from natal Moon
    """
    moon_idx   = SIGN_INDEX.get(natal_moon_sign, -1)
    saturn_idx = SIGN_INDEX.get(transit_saturn_sign, -1)

    if moon_idx == -1 or saturn_idx == -1:
        return None

    # Position of Saturn relative to Moon (1-indexed, 12th = moon-1, 2nd = moon+1)
    position = (saturn_idx - moon_idx) % 12  # 0=same, 11=12th house, 1=2nd house

    if position == 11:
        return {
            "active":    True,
            "phase":     1,
            "phase_name": "Preparatory",
            "description": "Saturn is approaching your emotional world from the 12th house — expenses, inner unrest, and a calling to release what no longer serves.",
            "invitation":  "What needs to be surrendered? Begin releasing now before the peak.",
            "duration":    f"~{SATURN_YEAR_PER_SIGN:.1f} years for this phase",
        }
    elif position == 0:
        return {
            "active":    True,
            "phase":     2,
            "phase_name": "Peak",
            "description": "Saturn is moving directly through your Moon sign — the deepest clarification of what is real in your emotional life.",
            "invitation":  "This is the sculptor at work. Get radically honest. What is real will remain; what is not will surface.",
            "duration":    f"~{SATURN_YEAR_PER_SIGN:.1f} years — the most intense phase.",
        }
    elif position == 1:
        return {
            "active":    True,
            "phase":     3,
            "phase_name": "Transition",
            "description": "Saturn has moved past your Moon into the 2nd house — consolidation, rebuilding your material and family foundation.",
            "invitation":  "What you clarified in the peak phase now asks to be rebuilt. Be patient and methodical.",
            "duration":    f"~{SATURN_YEAR_PER_SIGN:.1f} years — consolidation phase.",
        }
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 10. ASHTAKAVARGA SARVASHTAKAVARGA
# ─────────────────────────────────────────────────────────────────────────────
# Simplified Sarvashtakavarga (total bindus per sign across all 7 planets).
# Based on Parashara's traditional bindu-contribution offsets.
# Each planet contributes a bindu to a sign if the sign is at certain
# offsets from the planet's natal sign.
# Output: {sign_name: total_bindus_0_to_48}
# Transit quality: ≤3 = weak, 4 = average, 5–6 = strong, 7–8 = excellent

ASHTAKAVARGA_OFFSETS: Dict[str, List[int]] = {
    # Offsets FROM each planet's natal sign (1-indexed) where it contributes a bindu
    "Sun":     [1, 2, 4, 7, 8, 9, 10, 11],    # 8 contributions
    "Moon":    [3, 6, 7, 8, 10, 11],           # 6
    "Mars":    [1, 2, 4, 7, 8, 10, 11],        # 7
    "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],   # 8
    "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],    # 8
    "Venus":   [1, 2, 3, 4, 5, 8, 9, 10, 11], # 9
    "Saturn":  [3, 5, 6, 11, 12],             # 5
    # Lagna also contributes — use lagna sign as index 1
    "Lagna":   [1, 3, 6, 10, 11],             # 5
}


def compute_sarvashtakavarga(chart_data: Dict) -> Dict[str, int]:
    """
    Compute Sarvashtakavarga: total bindus per sign (0–48).
    Returns {sign_name: bindu_count} for all 12 signs.

    How to use:
      If transit planet is moving through a sign with ≥5 bindus → transit will be felt strongly.
      If ≤3 bindus → transit passes largely without effect.
    """
    bindus = {sign: 0 for sign in SIGNS}
    lagna_sign_idx = chart_data["lagna"]["sign_index"]

    contributors = {**{p: d["sign_index"] for p, d in chart_data["planets"].items()
                       if p in ASHTAKAVARGA_OFFSETS},
                    "Lagna": lagna_sign_idx}

    for planet, base_idx in contributors.items():
        offsets = ASHTAKAVARGA_OFFSETS.get(planet, [])
        for offset in offsets:
            target_idx  = (base_idx + offset - 1) % 12  # offset 1 = same sign (0-indexed)
            target_sign = SIGNS[target_idx]
            bindus[target_sign] += 1

    return bindus


def transit_quality(sign: str, sarva: Dict[str, int]) -> str:
    """Human-readable transit quality for a planet transiting this sign."""
    count = sarva.get(sign, 0)
    if count >= 7: return "excellent"
    if count >= 5: return "strong"
    if count == 4: return "average"
    if count >= 2: return "weak"
    return "minimal"


# ─────────────────────────────────────────────────────────────────────────────
# 11. YOGA BHANGA (YOGA CANCELLATION)
# ─────────────────────────────────────────────────────────────────────────────

# Houses that contaminate a Raja Yoga when the yoga lord also rules them
DUSTHANA_HOUSES = {6, 8, 12}

# Houses the yoga lords must be lords of to form valid Raja Yoga
KENDRA_HOUSES   = {1, 4, 7, 10}
TRIKONA_HOUSES  = {1, 5, 9}


def check_yoga_bhanga(
    yoga_name: str,
    yoga_planets: List[str],
    chart_data: Dict,
) -> Optional[Dict]:
    """
    Check if a detected yoga is cancelled or weakened by bhanga rules.
    Returns a dict if bhanga found, None if yoga stands.

    Currently handles:
      - Raja Yoga contamination (yoga lord also rules 6th/8th/12th)
      - Combust yoga lord (debilitates even exalted yogas)
      - Yoga in 6/8/12 house (debilitating placement)
    """
    lagna_idx  = chart_data["lagna"]["sign_index"]
    planets    = chart_data["planets"]

    for planet in yoga_planets:
        if planet not in planets:
            continue
        data = planets[planet]

        # Planet in dusthana house weakens yoga
        planet_house = (data["sign_index"] - lagna_idx) % 12 + 1
        if planet_house in DUSTHANA_HOUSES:
            return {
                "yoga":    yoga_name,
                "reason":  f"{planet} in {planet_house}th house (dusthana)",
                "impact":  "weakened",
            }

        # Combust yoga lord
        if data.get("is_combust", False):
            return {
                "yoga":    yoga_name,
                "reason":  f"{planet} is combust (within {data.get('combust_degree', '?')}° of Sun)",
                "impact":  "significantly weakened",
            }

        # Debilitated yoga lord
        if data.get("strength") == "debilitated":
            return {
                "yoga":    yoga_name,
                "reason":  f"{planet} is debilitated in {data['sign']}",
                "impact":  "weakened",
            }

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 11b. GRAHA DRISHTI (Planetary Aspects) + BHAVA ENRICHMENT
# ─────────────────────────────────────────────────────────────────────────────

# Special aspects (Parashari): all planets aspect 7th.
# Mars additionally 4th+8th; Jupiter 5th+9th; Saturn 3rd+10th; Rahu/Ketu 5th+9th.
GRAHA_ASPECT_OFFSETS: Dict[str, List[int]] = {
    "Sun":     [7],
    "Moon":    [7],
    "Mars":    [4, 7, 8],
    "Mercury": [7],
    "Jupiter": [5, 7, 9],
    "Venus":   [7],
    "Saturn":  [3, 7, 10],
    "Rahu":    [5, 7, 9],
    "Ketu":    [5, 7, 9],
}

SANDHI_ORB = 2.0  # degrees from house cusp = bhava sandhi zone


def get_aspected_signs(planet: str, natal_sign: str) -> List[str]:
    """
    Returns list of signs aspected by a planet from its natal sign.
    Includes the sign the planet occupies (conjunction = 1st aspect).
    """
    base_idx = SIGN_INDEX.get(natal_sign, 0)
    offsets  = GRAHA_ASPECT_OFFSETS.get(planet, [7])
    return [SIGNS[(base_idx + offset - 1) % 12] for offset in offsets]


def compute_bhava_aspects(chart_data: Dict) -> Dict[int, List[str]]:
    """
    Returns {house_number: [planet_names_aspecting_this_house]}.
    house_number 1-12, relative to lagna.
    A planet aspects a house if it aspects the sign that occupies that house.
    """
    lagna_idx  = chart_data["lagna"]["sign_index"]
    # Map each house (1-12) to its sign
    house_sign = {h: SIGNS[(lagna_idx + h - 1) % 12] for h in range(1, 13)}
    # Reverse: sign → house number
    sign_house = {v: k for k, v in house_sign.items()}

    bhava_aspects: Dict[int, List[str]] = {h: [] for h in range(1, 13)}

    for planet, data in chart_data["planets"].items():
        natal_sign   = data.get("sign")
        aspected     = get_aspected_signs(planet, natal_sign)
        for sign in aspected:
            house = sign_house.get(sign)
            if house and planet not in bhava_aspects[house]:
                bhava_aspects[house].append(planet)

    return bhava_aspects


def find_sandhi_planets(chart_data: Dict) -> List[Dict]:
    """
    Returns planets within SANDHI_ORB degrees of a house cusp.
    In equal house system, cusp N is at lagna_longitude + (N-1)*30.
    A sandhi planet has uncertain house ownership — it may belong to either
    the house it's in or the adjacent house.
    """
    lagna_lon = chart_data["lagna"].get("longitude") or \
                chart_data["lagna"]["sign_index"] * 30 + chart_data["lagna"]["degree"]

    sandhi_planets = []
    for planet, data in chart_data["planets"].items():
        planet_lon = data["longitude"]
        for i in range(12):
            cusp_lon = (lagna_lon + i * 30) % 360
            diff     = abs((planet_lon - cusp_lon + 180) % 360 - 180)
            if diff <= SANDHI_ORB:
                house_entering = (i % 12) + 1
                house_leaving  = i if i > 0 else 12
                sandhi_planets.append({
                    "planet":         planet,
                    "sign":           data["sign"],
                    "degree":         data["degree"],
                    "cusp_distance":  round(diff, 2),
                    "cusp_of_house":  house_entering,
                    "note": (
                        f"Within {diff:.1f}° of house {house_entering} cusp — "
                        f"read as both house {house_leaving} and house {house_entering}"
                    ),
                })
                break  # only flag once per planet

    return sandhi_planets


def add_bhava_enrichment_to_chart(chart_data: Dict) -> None:
    """
    Mutates chart_data in-place:
      - bhava_aspects:  {house: [aspecting_planets]}
      - sandhi_planets: planets near house cusps
      - drik_bala:      per-planet net aspectual strength from bhava_aspects
    """
    bhava_asp  = compute_bhava_aspects(chart_data)
    chart_data["bhava_aspects"]  = bhava_asp
    chart_data["sandhi_planets"] = find_sandhi_planets(chart_data)

    # Drik Bala: net benefic/malefic aspect score for each planet
    # +1 per benefic planet that aspects this planet's house, -1 per malefic
    BENEFICS = {"Jupiter", "Venus", "Moon", "Mercury"}
    MALEFICS  = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}
    lagna_idx = chart_data["lagna"]["sign_index"]

    for planet, data in chart_data["planets"].items():
        planet_house = (data["sign_index"] - lagna_idx) % 12 + 1
        aspectors    = bhava_asp.get(planet_house, [])
        drik = sum(
            1 if asp in BENEFICS else -1
            for asp in aspectors
            if asp != planet  # a planet doesn't aspect itself for drik bala
        )
        data["drik_bala"] = drik  # range: typically -5 to +5


# ─────────────────────────────────────────────────────────────────────────────
# 12. MAIN ENRICHMENT FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def enrich_chart(chart_data: Dict, jd_ut: Optional[float] = None) -> Dict:
    """
    Main entry point. Enriches chart_data in-place and returns it.
    Call this at the end of calculate_chart() in antar_ephemeris.py.

    If jd_ut is None, retrograde detection is skipped
    (falls back to False for all planets except Rahu/Ketu).
    """
    # 1. Retrograde + daily motion (requires jd_ut)
    if jd_ut is not None:
        try:
            add_retrograde_to_chart(chart_data, jd_ut)
        except Exception as e:
            print(f"Retrograde enrichment error (non-fatal): {e}")
            for data in chart_data["planets"].values():
                data.setdefault("is_retrograde", False)
                data.setdefault("daily_motion", None)
    else:
        # Preserve any is_retrograde values already in chart_data (e.g. from test fixtures)
        # Only set defaults for planets that don't already have the field
        for planet, data in chart_data["planets"].items():
            if "is_retrograde" not in data:
                data["is_retrograde"] = planet in ALWAYS_RETROGRADE
            if "daily_motion" not in data:
                data["daily_motion"] = None

    # 1b. Retrograde gradations (chesta bala component)
    add_retrograde_state_to_chart(chart_data)

    # 2. Combustion
    add_combustion_to_chart(chart_data)

    # 3. Vargottama + D-9 sign
    add_vargottama_to_chart(chart_data)

    # 4. Dig Bala
    add_dig_bala_to_chart(chart_data)

    # 5. Effective strength (composite)
    for data in chart_data["planets"].values():
        data["effective_strength"] = compute_effective_strength(data)

    # 5b. Naisargika Bala (natural strength rank)
    add_naisargika_bala_to_chart(chart_data)

    # 6. Nakshatra tara classes + deity/shakti/guna (relative to Moon)
    moon_nak = chart_data.get("moon_nakshatra") or \
               chart_data["planets"]["Moon"]["nakshatra"]
    for planet, data in chart_data["planets"].items():
        nak  = data.get("nakshatra", "")
        meta = get_nakshatra_meta(nak)
        data["nakshatra_deity"]  = meta.get("deity")
        data["nakshatra_shakti"] = meta.get("shakti")
        data["nakshatra_guna"]   = meta.get("guna")
        tara = get_tara_class(moon_nak, nak)
        data["tara_class"]       = tara
        data["tara_quality"]     = TARA_QUALITY.get(tara, "neutral")

    # 7. Panchanga
    sun_lon  = chart_data["planets"]["Sun"]["longitude"]
    moon_lon = chart_data["planets"]["Moon"]["longitude"]
    jd_for_panchanga = jd_ut or 2451545.0  # J2000 fallback
    chart_data["panchanga"] = compute_panchanga(sun_lon, moon_lon, jd_for_panchanga)

    # 8. Gandanta planets
    chart_data["gandanta_planets"] = find_gandanta_planets(chart_data)

    # 9. Sarvashtakavarga
    chart_data["sarvashtakavarga"] = compute_sarvashtakavarga(chart_data)

    # 11b. Bhava aspects + sandhi planets
    try:
        add_bhava_enrichment_to_chart(chart_data)
    except Exception as e:
        print(f"Bhava enrichment error (non-fatal): {e}")
        chart_data.setdefault("bhava_aspects", {h: [] for h in range(1, 13)})
        chart_data.setdefault("sandhi_planets", [])

    return chart_data


def build_enrichment_context(
    chart_data: Dict,
    transit_planets: Optional[Dict[str, str]] = None,
    concern: str = "general",
) -> str:
    """
    Build a compact LLM context block from enriched chart fields.
    Returns a string to append to the system prompt.

    transit_planets: {planet_name: sign_name} — current transit positions.
    """
    lines = ["CHART ENRICHMENT (deep Vedic signals):"]

    # Vargottama planets
    varg = [p for p, d in chart_data["planets"].items() if d.get("is_vargottama")]
    if varg:
        lines.append(f"  Vargottama planets (1.5× strength): {', '.join(varg)}")

    # Combust planets
    combust = [p for p, d in chart_data["planets"].items() if d.get("is_combust")]
    if combust:
        lines.append(f"  Combust planets (significantly weakened): {', '.join(combust)}")

    # Retrograde planets
    retro = [p for p, d in chart_data["planets"].items()
             if d.get("is_retrograde") and p not in ("Rahu", "Ketu")]
    if retro:
        lines.append(f"  Retrograde planets (internalised energy): {', '.join(retro)}")

    # Dig bala planets
    dig = [p for p, d in chart_data["planets"].items() if d.get("dig_bala")]
    if dig:
        lines.append(f"  Directional strength (dig bala): {', '.join(dig)}")

    # Gandanta planets
    gand = chart_data.get("gandanta_planets", [])
    if gand:
        gand_str = ", ".join(f"{g['planet']} ({g['zone']})" for g in gand)
        lines.append(f"  Gandanta planets (sensitive junction degrees): {gand_str}")

    # Panchanga
    pan = chart_data.get("panchanga")
    if pan:
        lines.append(
            f"  Birth panchanga: Tithi {pan['tithi']} ({pan['tithi_paksha']}), "
            f"Vara {pan['vara']}, Yoga {pan['yoga']} ({pan['yoga_quality']})"
        )

    # Moon nakshatra context
    moon_nak = chart_data.get("moon_nakshatra", "")
    if moon_nak:
        meta = get_nakshatra_meta(moon_nak)
        lines.append(
            f"  Moon nakshatra {moon_nak}: deity {meta.get('deity','?')}, "
            f"shakti '{meta.get('shakti','?')}'"
        )

    # Transit quality via Ashtakavarga (if transit data provided)
    sarva = chart_data.get("sarvashtakavarga", {})
    if transit_planets and sarva:
        transit_lines = []
        for planet, sign in transit_planets.items():
            if sign and sign in sarva:
                q = transit_quality(sign, sarva)
                if q in ("excellent", "strong"):
                    transit_lines.append(f"{planet} transiting {sign}: {q} ({sarva[sign]} bindus)")
                elif q in ("weak", "minimal"):
                    transit_lines.append(f"{planet} transiting {sign}: {q} ({sarva[sign]} bindus) — low impact expected")
        if transit_lines:
            lines.append(f"  Ashtakavarga transit strength: {'; '.join(transit_lines)}")

    return "\n".join(lines)


def build_enrichment_context_v2(
    chart_data: Dict,
    transit_planets: Optional[Dict[str, str]] = None,
    concern: str = "general",
) -> str:
    """
    Enhanced LLM context block — includes all new enrichment signals.
    Replaces build_enrichment_context. Returns string for prompt injection.

    transit_planets: {planet_name: sign_name} — current transit positions.
    """
    BENEFICS = {"Jupiter", "Venus", "Moon", "Mercury"}
    MALEFICS  = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

    lines = ["CHART ENRICHMENT (deep Vedic signals):"]

    # Vargottama
    varg = [p for p, d in chart_data["planets"].items() if d.get("is_vargottama")]
    if varg:
        lines.append(f"  Vargottama (same D-1 + D-9 sign, 1.5x strength): {', '.join(varg)}")

    # Combust
    combust = [
        f"{p} ({d['combust_degree']}° from Sun)"
        for p, d in chart_data["planets"].items() if d.get("is_combust")
    ]
    if combust:
        lines.append(f"  Combust (effectively weakened): {', '.join(combust)}")

    # Retrograde with state
    retro_parts = [
        f"{p} [{d.get('retrograde_state', 'vakri')}]"
        for p, d in chart_data["planets"].items()
        if d.get("is_retrograde") and p not in ("Rahu", "Ketu")
    ]
    if retro_parts:
        lines.append(f"  Retrograde (internalised energy): {', '.join(retro_parts)}")

    near_station = [
        p for p, d in chart_data["planets"].items()
        if d.get("retrograde_state") in ("mandatara", "anuvakra")
        and p not in ("Rahu", "Ketu")
    ]
    if near_station:
        lines.append(f"  Near station (most intensified): {', '.join(near_station)}")

    # Dig bala
    dig = [p for p, d in chart_data["planets"].items() if d.get("dig_bala")]
    if dig:
        lines.append(f"  Dig bala (directional peak house): {', '.join(dig)}")

    # Naisargika bala — top 3 natural strengths for this chart
    nat_sorted = sorted(
        [(p, d["naisargika_bala"]) for p, d in chart_data["planets"].items()
         if d.get("naisargika_bala") is not None],
        key=lambda x: -x[1],
    )[:3]
    if nat_sorted:
        ns_str = ", ".join(f"{p}({r})" for p, r in nat_sorted)
        lines.append(f"  Natural strength rank (top 3): {ns_str}")

    # Gandanta
    gand = chart_data.get("gandanta_planets", [])
    if gand:
        lines.append(
            f"  Gandanta (junction degrees, sensitive): "
            + ", ".join(f"{g['planet']} at {g['zone']}" for g in gand)
        )

    # Sandhi planets
    sandhi = chart_data.get("sandhi_planets", [])
    if sandhi:
        lines.append(
            f"  Sandhi (within 2° of house cusp, dual-house influence): "
            + ", ".join(f"{s['planet']} near H{s['cusp_of_house']}" for s in sandhi)
        )

    # Panchanga
    pan = chart_data.get("panchanga")
    if pan:
        lines.append(
            f"  Birth panchanga: {pan['tithi']} tithi ({pan['tithi_paksha']}), "
            f"{pan['vara']}, {pan['yoga']} yoga ({pan['yoga_quality']})"
        )

    # Moon nakshatra deity + shakti
    moon_nak = chart_data.get("moon_nakshatra", "")
    if moon_nak:
        meta = get_nakshatra_meta(moon_nak)
        lines.append(
            f"  Moon nakshatra {moon_nak}: deity {meta.get('deity','?')}, "
            f"shakti '{meta.get('shakti','?')}'"
        )

    # Bhava aspects — houses with significant aspect clusters
    bhava = chart_data.get("bhava_aspects", {})
    if bhava:
        notable = []
        for house, planets_asp in bhava.items():
            b_count = sum(1 for p in planets_asp if p in BENEFICS)
            m_count = sum(1 for p in planets_asp if p in MALEFICS)
            if b_count >= 2:
                notable.append(
                    f"H{house} benefic-aspected ({', '.join(p for p in planets_asp if p in BENEFICS)})"
                )
            elif m_count >= 2:
                notable.append(
                    f"H{house} malefic-aspected ({', '.join(p for p in planets_asp if p in MALEFICS)})"
                )
        if notable:
            lines.append(f"  Multi-planet house aspects: {'; '.join(notable[:4])}")

    # Ashtakavarga transit quality
    sarva = chart_data.get("sarvashtakavarga", {})
    if transit_planets and sarva:
        transit_parts = []
        for planet, sign in transit_planets.items():
            if sign and sign in sarva:
                q = transit_quality(sign, sarva)
                if q in ("excellent", "strong"):
                    transit_parts.append(f"{planet}/{sign}: {q} ({sarva[sign]}b)")
                elif q in ("weak", "minimal"):
                    transit_parts.append(f"{planet}/{sign}: {q} ({sarva[sign]}b, low impact)")
        if transit_parts:
            lines.append(f"  Transit quality (ashtakavarga): {'; '.join(transit_parts)}")

    return "\n".join(lines)
