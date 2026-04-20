"""
daily_prediction_engine.py — 7-Day Daily Signal Generator (v2 — LLM-backed)
Antar Intelligence Platform

Generates per-day signals for a 7-day window using:
  - Existing panchang/Moon/Mercury scoring (KEPT from v1)
  - Claude Sonnet LLM call per day for text generation (NEW)
  - Full chart context: archetype, dashas, D10, DKP, transits (NEW)

Called by: GET /api/v1/daily-week/{chart_id}
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import json
import os

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constants (KEPT from v1)
# ──────────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Nakshatra energy profiles — action-friendly language only
NAKSHATRA_PROFILES = {
    "Ashwini":           {"energy": "swift, initiating",      "aligned": ["starting projects", "health actions", "speed decisions"],   "friction": ["long-term planning", "slow negotiations"]},
    "Bharani":           {"energy": "intense, transformative", "aligned": ["difficult conversations", "ending cycles", "financial moves"], "friction": ["new beginnings", "light social events"]},
    "Krittika":          {"energy": "sharp, decisive",         "aligned": ["cutting losses", "clarity conversations", "editing work"],   "friction": ["diplomacy", "compromise situations"]},
    "Rohini":            {"energy": "creative, nurturing",     "aligned": ["creative work", "relationship building", "financial planning"], "friction": ["confrontation", "endings"]},
    "Mrigashira":        {"energy": "searching, curious",      "aligned": ["research", "exploration", "new contacts"],                   "friction": ["commitment decisions", "finalizing"]},
    "Ardra":             {"energy": "stormy, transformative",  "aligned": ["problem-solving", "technical work", "breakthrough thinking"], "friction": ["partnerships", "public appearances"]},
    "Punarvasu":         {"energy": "expansive, restoring",    "aligned": ["recovery", "travel", "relaunching stalled projects"],        "friction": ["intense focus", "confrontation"]},
    "Pushya":            {"energy": "nurturing, auspicious",   "aligned": ["investments", "long-term planning", "team building"],        "friction": ["risky moves", "speculation"]},
    "Ashlesha":          {"energy": "penetrating, strategic",  "aligned": ["negotiation", "research", "uncovering hidden info"],        "friction": ["trust-building", "openness"]},
    "Magha":             {"energy": "authoritative, regal",    "aligned": ["leadership actions", "presentations", "legacy work"],        "friction": ["collaboration", "blending in"]},
    "Purva Phalguni":    {"energy": "creative, pleasure-seeking", "aligned": ["client entertainment", "creative projects", "partnerships"], "friction": ["solo deep work", "financial discipline"]},
    "Uttara Phalguni":   {"energy": "steady, establishing",    "aligned": ["contracts", "long-term agreements", "institutional work"],   "friction": ["speculation", "rapid pivots"]},
    "Hasta":             {"energy": "skilled, precise",        "aligned": ["detailed work", "craftsmanship", "healing actions"],         "friction": ["big-picture strategy", "delegation"]},
    "Chitra":            {"energy": "creative, brilliant",     "aligned": ["design", "presentations", "brand work", "pitches"],         "friction": ["routine work", "slow processes"]},
    "Swati":             {"energy": "independent, adaptable",  "aligned": ["networking", "flexibility", "trading"],                     "friction": ["fixed commitments", "confrontation"]},
    "Vishakha":          {"energy": "goal-oriented, intense",  "aligned": ["goal-setting", "competitive moves", "ambition-driven work"], "friction": ["rest", "casual socializing"]},
    "Anuradha":          {"energy": "devoted, disciplined",    "aligned": ["team loyalty", "friendship", "structured work"],            "friction": ["isolation", "self-promotion"]},
    "Jyeshtha":          {"energy": "commanding, protective",  "aligned": ["authority decisions", "crisis management", "protection"],   "friction": ["partnership building", "softness"]},
    "Mula":              {"energy": "uprooting, investigative","aligned": ["root-cause analysis", "endings", "philosophy"],             "friction": ["stability", "new launches"]},
    "Purva Ashadha":     {"energy": "invincible, persuasive",  "aligned": ["pitching", "persuasion", "travel"],                        "friction": ["accepting defeat", "slowing down"]},
    "Uttara Ashadha":    {"energy": "victorious, ethical",     "aligned": ["finalizing wins", "integrity-based decisions", "launches"], "friction": ["compromise", "grey areas"]},
    "Shravana":          {"energy": "listening, connecting",   "aligned": ["mentorship", "learning", "advisory conversations"],        "friction": ["speaking over others", "impulsive action"]},
    "Dhanishta":         {"energy": "abundant, musical",       "aligned": ["wealth moves", "group leadership", "bold action"],         "friction": ["isolation", "detail work"]},
    "Shatabhisha":       {"energy": "healing, mysterious",     "aligned": ["research", "solo work", "unconventional approaches"],      "friction": ["public-facing work", "partnerships"]},
    "Purva Bhadrapada":  {"energy": "fierce, transformative",  "aligned": ["high-stakes decisions", "intense focus", "transitions"],   "friction": ["patience", "slow work"]},
    "Uttara Bhadrapada": {"energy": "stable, wise",            "aligned": ["teaching", "long-term planning", "settling matters"],      "friction": ["fast pivots", "speculation"]},
    "Revati":            {"energy": "compassionate, completing","aligned": ["closing cycles", "charitable work", "spiritual clarity"],  "friction": ["new ventures", "competitive pressure"]},
}

# Moon-sign friction map
MOON_FRICTION_MAP = {
    "Aries":       ["Cancer", "Capricorn"],
    "Taurus":      ["Leo", "Aquarius"],
    "Gemini":      ["Virgo", "Pisces"],
    "Cancer":      ["Aries", "Libra"],
    "Leo":         ["Taurus", "Scorpio"],
    "Virgo":       ["Gemini", "Sagittarius"],
    "Libra":       ["Cancer", "Capricorn"],
    "Scorpio":     ["Leo", "Aquarius"],
    "Sagittarius": ["Virgo", "Pisces"],
    "Capricorn":   ["Aries", "Libra"],
    "Aquarius":    ["Taurus", "Scorpio"],
    "Pisces":      ["Gemini", "Sagittarius"],
}

WEEKDAY_OVERLAY = {
    "Monday":    {"boost": "emotional intelligence, intuition", "caution": "logic-heavy analysis"},
    "Tuesday":   {"boost": "courage, direct action, confrontation", "caution": "diplomacy"},
    "Wednesday": {"boost": "communication, negotiation, writing", "caution": "emotional decisions"},
    "Thursday":  {"boost": "expansion, learning, authority", "caution": "details, contracts"},
    "Friday":    {"boost": "relationships, creativity, partnerships", "caution": "solo competitive work"},
    "Saturday":  {"boost": "discipline, structure, long-term planning", "caution": "spontaneity"},
    "Sunday":    {"boost": "vitality, leadership, visibility", "caution": "rest (if needed)"},
}


# ──────────────────────────────────────────────
# Core Ephemeris Functions (KEPT exactly from v1)
# ──────────────────────────────────────────────


def calculate_panchang(dt_utc, lat: float, lon: float) -> dict:
    """
    Calculate the 5 daily Panchang elements for a given datetime + location.
    """
    import swisseph as swe
    from datetime import timezone

    jd = swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
    )

    sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
    moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]

    # Tithi
    tithi_deg = (moon_lon - sun_lon) % 360
    tithi_num = int(tithi_deg / 12) + 1

    TITHI_NAMES = [
        "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
        "Shashthi","Saptami","Ashtami","Navami","Dashami",
        "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
        "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
        "Shashthi","Saptami","Ashtami","Navami","Dashami",
        "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
    ]
    TITHI_QUALITY = {
        1:"neutral", 2:"auspicious", 3:"auspicious", 4:"mixed",
        5:"auspicious", 6:"mixed", 7:"auspicious", 8:"mixed",
        9:"mixed", 10:"auspicious", 11:"auspicious", 12:"auspicious",
        13:"mixed", 14:"inauspicious", 15:"auspicious",
        16:"neutral", 17:"auspicious", 18:"auspicious", 19:"mixed",
        20:"auspicious", 21:"mixed", 22:"auspicious", 23:"mixed",
        24:"mixed", 25:"auspicious", 26:"auspicious", 27:"auspicious",
        28:"mixed", 29:"inauspicious", 30:"inauspicious"
    }

    tithi = {
        "number": tithi_num,
        "name": TITHI_NAMES[tithi_num - 1],
        "quality": TITHI_QUALITY.get(tithi_num, "neutral"),
        "paksha": "Shukla" if tithi_num <= 15 else "Krishna",
    }

    # Vara
    weekday = dt_utc.weekday()
    VARA = [
        {"lord":"Moon",    "name":"Monday",    "themes":"Emotions, home, mother, mind, water",
         "good_for":"Emotional conversations, family matters, intuitive decisions",
         "avoid":"Major business moves, confrontation"},
        {"lord":"Mars",    "name":"Tuesday",   "themes":"Action, courage, energy, competition",
         "good_for":"Bold moves, physical activity, negotiations, new initiatives",
         "avoid":"Emotional decisions, overspending"},
        {"lord":"Mercury", "name":"Wednesday", "themes":"Communication, intellect, trade, travel",
         "good_for":"Writing, contracts, learning, networking, short trips",
         "avoid":"Major financial commitments"},
        {"lord":"Jupiter", "name":"Thursday",  "themes":"Wisdom, expansion, teachers, wealth",
         "good_for":"Education, spiritual practice, seeking guidance, investments",
         "avoid":"Arguments, harsh speech"},
        {"lord":"Venus",   "name":"Friday",    "themes":"Love, beauty, pleasure, creativity, wealth",
         "good_for":"Relationships, creative work, luxury, social events",
         "avoid":"Starting confrontational matters"},
        {"lord":"Saturn",  "name":"Saturday",  "themes":"Structure, discipline, karma, endurance",
         "good_for":"Long-term planning, hard work, resolving old matters",
         "avoid":"Starting new ventures, celebrations"},
        {"lord":"Sun",     "name":"Sunday",    "themes":"Vitality, authority, father, leadership, visibility",
         "good_for":"Career moves, leadership, visibility, government matters",
         "avoid":"Starting new relationships"},
    ]
    vara = VARA[weekday]

    # Nakshatra
    nakshatra_num = int(moon_lon / (360/27))
    NAKSHATRAS_FULL = [
        {"name":"Ashwini","deity":"Ashwins","quality":"swift","good_for":"Starting new things, medical matters, travel"},
        {"name":"Bharani","deity":"Yama","quality":"fierce","good_for":"Completing difficult tasks, transformation"},
        {"name":"Krittika","deity":"Agni","quality":"mixed","good_for":"Cooking, purification, sharp actions"},
        {"name":"Rohini","deity":"Brahma","quality":"fixed","good_for":"Agriculture, building, sensual pleasures, stability"},
        {"name":"Mrigashira","deity":"Soma","quality":"soft","good_for":"Searching, exploration, gentle activities"},
        {"name":"Ardra","deity":"Rudra","quality":"sharp","good_for":"Cutting through obstacles, research, destructive work"},
        {"name":"Punarvasu","deity":"Aditi","quality":"moveable","good_for":"Return journeys, renewals, buying/selling"},
        {"name":"Pushya","deity":"Brihaspati","quality":"auspicious","good_for":"Almost everything — most auspicious nakshatra"},
        {"name":"Ashlesha","deity":"Naga","quality":"sharp","good_for":"Occult matters, research, medicine"},
        {"name":"Magha","deity":"Pitrs","quality":"fierce","good_for":"Honoring ancestors, authority matters, father-related"},
        {"name":"Purva Phalguni","deity":"Bhaga","quality":"fierce","good_for":"Creativity, pleasure, relaxation"},
        {"name":"Uttara Phalguni","deity":"Aryaman","quality":"fixed","good_for":"Friendships, contracts, getting favors"},
        {"name":"Hasta","deity":"Savitar","quality":"swift","good_for":"Crafts, healing, stealing — quick activities"},
        {"name":"Chitra","deity":"Vishwakarma","quality":"soft","good_for":"Art, architecture, wearing new clothes"},
        {"name":"Swati","deity":"Vayu","quality":"moveable","good_for":"Business, trade, learning, independence"},
        {"name":"Vishakha","deity":"Indra-Agni","quality":"mixed","good_for":"Achieving goals, political matters"},
        {"name":"Anuradha","deity":"Mitra","quality":"soft","good_for":"Friendships, devotion, group activities"},
        {"name":"Jyeshtha","deity":"Indra","quality":"sharp","good_for":"Leadership, authority, competitive situations"},
        {"name":"Mula","deity":"Nirriti","quality":"sharp","good_for":"Research, getting to root causes, medicine"},
        {"name":"Purva Ashadha","deity":"Apas","quality":"fierce","good_for":"Water activities, purification, travel"},
        {"name":"Uttara Ashadha","deity":"Vishwadevas","quality":"fixed","good_for":"Long-term projects, victory, stability"},
        {"name":"Shravana","deity":"Vishnu","quality":"moveable","good_for":"Learning, listening, travel, communication"},
        {"name":"Dhanishta","deity":"Ashta Vasus","quality":"moveable","good_for":"Music, wealth, community activities"},
        {"name":"Shatabhisha","deity":"Varuna","quality":"moveable","good_for":"Healing, occult, isolation, research"},
        {"name":"Purva Bhadrapada","deity":"Ajaikapada","quality":"fierce","good_for":"Intensity, transformation, occult"},
        {"name":"Uttara Bhadrapada","deity":"Ahirbudhnya","quality":"fixed","good_for":"Stability, depth, spiritual practice"},
        {"name":"Revati","deity":"Pushan","quality":"soft","good_for":"Completion, travel, nourishment, spiritual practice"},
    ]
    nakshatra = NAKSHATRAS_FULL[nakshatra_num]
    nakshatra["number"] = nakshatra_num + 1
    nakshatra["moon_lon"] = round(moon_lon, 2)

    # Yoga
    yoga_deg = (sun_lon + moon_lon) % 360
    yoga_num = int(yoga_deg / (360/27))
    YOGAS = [
        ("Vishkambha","mixed"),("Priti","auspicious"),("Ayushman","auspicious"),
        ("Saubhagya","auspicious"),("Shobhana","auspicious"),("Atiganda","inauspicious"),
        ("Sukarma","auspicious"),("Dhriti","auspicious"),("Shoola","inauspicious"),
        ("Ganda","inauspicious"),("Vriddhi","auspicious"),("Dhruva","auspicious"),
        ("Vyaghata","inauspicious"),("Harshana","auspicious"),("Vajra","mixed"),
        ("Siddhi","auspicious"),("Vyatipata","inauspicious"),("Variyan","mixed"),
        ("Parigha","inauspicious"),("Shiva","auspicious"),("Siddha","auspicious"),
        ("Sadhya","auspicious"),("Shubha","auspicious"),("Shukla","auspicious"),
        ("Brahma","auspicious"),("Mahendra","auspicious"),("Vaidhriti","inauspicious"),
    ]
    yoga_name, yoga_quality = YOGAS[yoga_num]
    yoga = {"number": yoga_num+1, "name": yoga_name, "quality": yoga_quality}

    # Karana
    karana_num = int(tithi_deg / 6) % 11
    KARANAS = [
        ("Bava","auspicious"),("Balava","auspicious"),("Kaulava","auspicious"),
        ("Taitila","auspicious"),("Garaja","mixed"),("Vanija","auspicious"),
        ("Vishti","inauspicious"),("Shakuni","mixed"),("Chatushpada","mixed"),
        ("Naga","mixed"),("Kimstughna","mixed"),
    ]
    karana_name, karana_quality = KARANAS[karana_num]
    karana = {"name": karana_name, "quality": karana_quality}

    # Moon sign
    moon_sign_num = int(moon_lon / 30)
    SIGNS_LOCAL = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    moon_sign = SIGNS_LOCAL[moon_sign_num]

    qualities = [tithi["quality"], yoga["quality"], karana["quality"]]
    auspicious_count = qualities.count("auspicious")
    inauspicious_count = qualities.count("inauspicious")

    if inauspicious_count >= 2:
        panchang_quality = "challenging"
    elif auspicious_count >= 2:
        panchang_quality = "favorable"
    else:
        panchang_quality = "mixed"

    return {
        "tithi": tithi,
        "vara": vara,
        "nakshatra": nakshatra,
        "yoga": yoga,
        "karana": karana,
        "moon_sign": moon_sign,
        "panchang_quality": panchang_quality,
        "summary": (
            f"{vara['name']}, {nakshatra['name']} nakshatra, "
            f"{tithi['name']} tithi ({tithi['quality']}), "
            f"{yoga_name} yoga ({yoga_quality})"
        )
    }


def get_chandra_bala(natal_moon_sign: str, current_moon_sign: str) -> dict:
    """
    Calculate Moon's strength relative to natal Moon position.
    """
    SIGNS_LOCAL = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    try:
        natal_idx = SIGNS_LOCAL.index(natal_moon_sign)
        current_idx = SIGNS_LOCAL.index(current_moon_sign)
    except ValueError:
        return {"strength": "neutral", "house_from_moon": 0}

    house_from_moon = ((current_idx - natal_idx) % 12) + 1

    STRENGTH = {
        1:"favorable", 2:"neutral", 3:"favorable", 4:"unfavorable",
        5:"neutral", 6:"favorable", 7:"favorable", 8:"unfavorable",
        9:"neutral", 10:"favorable", 11:"favorable", 12:"unfavorable"
    }

    strength = STRENGTH.get(house_from_moon, "neutral")
    is_chandrashtama = house_from_moon in [4, 8, 12]

    return {
        "strength": strength,
        "house_from_moon": house_from_moon,
        "is_chandrashtama": is_chandrashtama,
        "plain": (
            "Moon transiting unfavorably from your natal Moon — be careful with decisions today. Avoid starting new things."
            if is_chandrashtama else
            "Moon well-placed from your natal Moon — your instincts are reliable today."
            if strength == "favorable" else
            "Moon in neutral position from natal Moon."
        )
    }


def get_planet_sign_for_date(target_date: datetime, planet_id: int) -> str:
    """Compute sidereal sign of a planet for a given date."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)
        pos, _ = swe.calc_ut(jd, planet_id)
        ayanamsa = swe.get_ayanamsa(jd)
        sidereal = (pos[0] - ayanamsa) % 360
        return SIGNS[int(sidereal / 30)]
    except Exception as e:
        logger.warning(f"get_planet_sign_for_date failed for planet {planet_id}: {e}")
        return "Unknown"


def get_moon_data_for_date(target_date: datetime) -> dict:
    """Returns Moon nakshatra, sign, and degree for a given date."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)
        pos, _ = swe.calc_ut(jd, swe.MOON)
        ayanamsa = swe.get_ayanamsa(jd)
        sidereal = (pos[0] - ayanamsa) % 360
        nak_idx = int(sidereal / (360 / 27))
        nak_name = NAKSHATRAS[nak_idx % 27]
        moon_sign = SIGNS[int(sidereal / 30)]
        degree = round(sidereal % 30, 2)
        return {
            "nakshatra": nak_name,
            "sign": moon_sign,
            "degree": degree,
            "sidereal_longitude": round(sidereal, 4)
        }
    except Exception as e:
        logger.error(f"get_moon_data_for_date failed for {target_date}: {e}")
        return {"nakshatra": "Unknown", "sign": "Unknown", "degree": 0.0, "sidereal_longitude": 0.0}


def get_tithi(target_date: datetime) -> str:
    """Compute approximate tithi (lunar day 1-30) for a date."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)
        moon_pos, _ = swe.calc_ut(jd, swe.MOON)
        sun_pos, _ = swe.calc_ut(jd, swe.SUN)
        diff = (moon_pos[0] - sun_pos[0]) % 360
        tithi_num = int(diff / 12) + 1
        TITHIS = [
            "New Moon", "2nd", "3rd", "4th", "5th", "6th", "7th",
            "8th (Half Moon)", "9th", "10th", "11th (Ekadashi)", "12th",
            "13th", "14th", "Full Moon",
            "16th", "17th", "18th", "19th", "20th", "21st",
            "22nd (Half Moon)", "23rd", "24th", "25th (Ekadashi)", "26th",
            "27th", "28th", "29th", "30th"
        ]
        return TITHIS[(tithi_num - 1) % 30]
    except Exception as e:
        logger.warning(f"get_tithi failed: {e}")
        return "Unknown"


# ──────────────────────────────────────────────
# Scoring (KEPT from v1)
# ──────────────────────────────────────────────

def _score_day(moon_sign: str, natal_moon_sign: str, nakshatra: str, weekday: str) -> tuple:
    """
    Returns (score: int, is_friction: bool)
    score 0–10, higher = more aligned
    """
    score = 5  # neutral baseline

    high_energy = {"Rohini", "Pushya", "Uttara Phalguni", "Uttara Ashadha",
                   "Chitra", "Dhanishta", "Magha", "Punarvasu"}
    friction_nakshatras = {"Ardra", "Ashlesha", "Jyeshtha", "Mula",
                           "Purva Bhadrapada", "Bharani"}
    if nakshatra in high_energy:
        score += 2
    elif nakshatra in friction_nakshatras:
        score -= 2

    friction_signs = MOON_FRICTION_MAP.get(natal_moon_sign, [])
    if moon_sign in friction_signs:
        score -= 2
    elif moon_sign == natal_moon_sign:
        score += 1

    power_days = {"Thursday", "Sunday"}
    if weekday in power_days:
        score += 1

    score = max(0, min(10, score))
    is_friction = score < 4
    return score, is_friction


# ──────────────────────────────────────────────
# v1 template fallback (used when chart_id is None or LLM fails)
# ──────────────────────────────────────────────

def _build_signal_text(
    nakshatra: str, moon_sign: str, mercury_sign: str,
    natal_moon_sign: str, weekday: str, score: int, is_friction: bool
) -> dict:
    """Template-based fallback signal builder (v1 legacy)."""
    profile = NAKSHATRA_PROFILES.get(nakshatra, {
        "energy": "variable", "aligned": ["flexible work"], "friction": ["rigid planning"]
    })
    day_overlay = WEEKDAY_OVERLAY.get(weekday, {})

    aligned = profile.get("aligned", [])[:3]
    friction = profile.get("friction", [])[:2]

    mercury_comm_signs = {"Gemini", "Virgo", "Aquarius", "Libra"}
    mercury_note = None
    if mercury_sign in mercury_comm_signs:
        mercury_note = "Communication and negotiation carry extra weight today."

    if is_friction:
        signal = (
            f"The energy today creates internal friction — best used for inner work, "
            f"review, and preparation rather than launching or confronting. "
            f"{weekday}'s overlay favors {day_overlay.get('boost', 'steady progress')} "
            f"but the Moon's position slows outer momentum."
        )
        move = (
            f"Use today to audit, review, or strengthen one thing already in motion. "
            f"Hold new launches until energy lifts."
        )
    else:
        signal = (
            f"The energy today is {profile['energy']} — lean into it. "
            f"{weekday} amplifies {day_overlay.get('boost', 'focused effort')}, "
            f"making this a good window for {aligned[0] if aligned else 'action'}."
        )
        move = (
            f"Take one concrete step today in: {', '.join(aligned[:2])}. "
            f"Avoid: {', '.join(friction[:1])}."
        )

    wow = None
    if moon_sign == natal_moon_sign:
        wow = "Moon returns to your natal sign today — emotional clarity peaks. Trust your instincts."
    elif nakshatra in {"Pushya", "Rohini", "Uttara Phalguni"}:
        wow = f"{nakshatra} is one of the most auspicious nakshatras. Major decisions made today carry positive momentum."
    elif nakshatra == "Mula":
        wow = "Mula energy cuts to the root. Any investigation or deep audit today will reveal what's been hidden."
    elif mercury_note:
        wow = mercury_note

    return {
        "energy": profile["energy"],
        "aligned_for": aligned,
        "friction_for": friction,
        "signal": signal,
        "move": move,
        "wow": wow,
        "score": score,
    }


# ──────────────────────────────────────────────
# NEW: Chart context builder for LLM prompts
# ──────────────────────────────────────────────

def _safe_json(v):
    """Parse JSONB that might be stored as a string."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _get_life_stage(birth_date_str: str) -> str:
    """Compute life stage from birth date string."""
    try:
        if not birth_date_str:
            return "unknown"
        bd = datetime.strptime(str(birth_date_str)[:10], "%Y-%m-%d")
        age = (datetime.now() - bd).days / 365.25
        if age < 25:
            return "early career (under 25)"
        elif age < 35:
            return "establishment phase (25-35)"
        elif age < 50:
            return "peak execution (35-50)"
        elif age < 65:
            return "consolidation/legacy (50-65)"
        else:
            return "wisdom/legacy (65+)"
    except Exception:
        return "unknown"


def _extract_current_dashas(dashas_dict: dict) -> dict:
    """Extract current MD/AD/PD from dashas_dict."""
    result = {"md": "unknown", "ad": "unknown", "pd": "unknown"}
    today = datetime.now().strftime("%Y-%m-%d")

    vimsottari = dashas_dict.get("vimsottari", [])
    if not vimsottari:
        return result

    for d in vimsottari:
        start = d.get("start_date") or d.get("start", "")
        end = d.get("end_date") or d.get("end", "")
        level = d.get("level", "")
        planet = d.get("planet_or_sign") or d.get("lord_or_sign", "")

        if start <= today <= end:
            if level in ("mahadasha", 1, "1"):
                result["md"] = planet
            elif level in ("antardasha", 2, "2"):
                result["ad"] = planet
            elif level in ("pratyantardasha", 3, "3"):
                result["pd"] = planet

    return result


def _extract_chara_dasha(dashas_dict: dict) -> str:
    """Extract current Jaimini Chara Dasha sign."""
    today = datetime.now().strftime("%Y-%m-%d")
    chara = dashas_dict.get("chara_dasha", dashas_dict.get("jaimini_chara", []))
    if not chara:
        return "not available"

    for d in chara:
        start = d.get("start_date") or d.get("start", "")
        end = d.get("end_date") or d.get("end", "")
        if start <= today <= end:
            return d.get("planet_or_sign") or d.get("lord_or_sign", "unknown")

    return "not available"


def _extract_natal_moon_info(chart_data: dict) -> dict:
    """Extract natal Moon sign, nakshatra, and house."""
    planets = chart_data.get("planets") or chart_data.get("planet_positions", [])
    result = {"sign": "unknown", "nakshatra": "unknown", "house": 0}

    if isinstance(planets, list):
        for p in planets:
            if isinstance(p, dict):
                name = (p.get("name") or p.get("planet") or "").lower()
                if name == "moon":
                    result["sign"] = p.get("sign") or p.get("rashi") or "unknown"
                    result["nakshatra"] = p.get("nakshatra") or "unknown"
                    result["house"] = p.get("house") or 0
                    break
    elif isinstance(planets, dict):
        moon = planets.get("Moon") or planets.get("moon", {})
        if moon:
            result["sign"] = moon.get("sign") or moon.get("rashi") or "unknown"
            result["nakshatra"] = moon.get("nakshatra") or "unknown"
            result["house"] = moon.get("house") or 0

    return result


def _extract_lagna(chart_data: dict) -> str:
    """Extract lagna/rising sign."""
    lagna = chart_data.get("lagna") or chart_data.get("ascendant", {})
    if isinstance(lagna, dict):
        return lagna.get("sign") or lagna.get("rashi") or "unknown"
    if isinstance(lagna, str):
        return lagna
    return "unknown"


def _extract_d10_lagna(chart_data: dict) -> str:
    """Extract D10 lagna from divisional charts."""
    divs = chart_data.get("divisional_charts") or {}
    d10 = divs.get("D10") or divs.get("d10", {})
    if isinstance(d10, dict):
        lagna = d10.get("lagna") or d10.get("ascendant", {})
        if isinstance(lagna, dict):
            return lagna.get("sign") or "unknown"
        if isinstance(lagna, str):
            return lagna
    return "not available"


def _extract_sleeping_planets(lk_data: dict) -> str:
    """Extract sleeping planets from Lal Kitab advanced data."""
    adv = lk_data.get("advanced", {})
    sleeping = adv.get("sleeping_planets", [])
    if not sleeping:
        return "none detected"
    if isinstance(sleeping, list):
        names = []
        for s in sleeping:
            if isinstance(s, dict):
                names.append(s.get("planet", str(s)))
            else:
                names.append(str(s))
        return ", ".join(names) if names else "none detected"
    return str(sleeping)


async def build_daily_context(chart_id: str, supabase_client) -> dict:
    """
    Fetch full chart context from Supabase for daily signal generation.
    Returns a dict ready for prompt injection.
    """
    try:
        res = supabase_client.table("charts").select(
            "chart_data, jaimini_data, lal_kitab_data, character_archetype, "
            "current_country, birth_country, birth_date, name"
        ).eq("id", chart_id).single().execute()

        if not res.data:
            return None

        row = res.data
        chart_data = _safe_json(row.get("chart_data") or {})
        jaimini_data = _safe_json(row.get("jaimini_data") or {})
        lk_data = _safe_json(row.get("lal_kitab_data") or {})
        archetype = row.get("character_archetype") or {}
        if isinstance(archetype, str):
            archetype = _safe_json(archetype)

        # Get dashas — LIVE computation via phase_analyzer (includes PD + SD)
        # (dasha_periods table does not store PD/SD, so we compute live.)
        current_dashas = {"md": "unknown", "ad": "unknown", "pd": "unknown", "sd": "unknown",
                          "md_end_date": None, "pd_end_date": None, "sd_end_date": None}
        try:
            from antar_engine.life_arc.phase_analyzer import get_current_vimsottari
            birth_jd = chart_data.get("birth_jd")
            if birth_jd is not None:
                vim = get_current_vimsottari(chart_data, birth_jd)
                if not vim.get("error"):
                    current_dashas["md"] = vim.get("md") or "unknown"
                    current_dashas["ad"] = vim.get("ad") or "unknown"
                    current_dashas["pd"] = vim.get("pd") or "unknown"
                    current_dashas["sd"] = vim.get("sd") or "unknown"
                    current_dashas["md_end_date"] = vim.get("md_end_date")
                    current_dashas["pd_end_date"] = vim.get("pd_end_date")
                    current_dashas["sd_end_date"] = vim.get("sd_end_date")
            else:
                logger.warning("[daily-context] chart_data has no birth_jd; cannot compute live vimsottari")
        except Exception as de:
            logger.warning(f"[daily-context] live dasha computation failed: {de}")

        # Jaimini Chara — still reads from dasha_periods table
        dashas_dict = {}
        try:
            dasha_res = supabase_client.table("dasha_periods").select("*").eq(
                "chart_id", chart_id
            ).order("sequence").limit(500).execute()
            for d_row in (dasha_res.data or []):
                system = d_row.get("system", "vimsottari")
                if system not in dashas_dict:
                    dashas_dict[system] = []
                dashas_dict[system].append({
                    "planet_or_sign": d_row.get("planet_or_sign", ""),
                    "start_date": d_row.get("start_date", ""),
                    "end_date": d_row.get("end_date", ""),
                    "level": d_row.get("type") or d_row.get("level", "mahadasha"),
                })
        except Exception as de:
            logger.warning(f"[daily-context] chara dasha fetch failed: {de}")

        chara_md = _extract_chara_dasha(dashas_dict)
        natal_moon = _extract_natal_moon_info(chart_data)
        lagna_sign = _extract_lagna(chart_data)
        d10_lagna = _extract_d10_lagna(chart_data)
        sleeping_planets = _extract_sleeping_planets(lk_data)
        life_stage = _get_life_stage(row.get("birth_date"))
        current_country = row.get("current_country") or row.get("birth_country") or ""

        # Get transit report
        formatted_transits = "No transit data available."
        try:
            from antar_engine.transit_engine import get_full_transit_report
            transit_rpt = get_full_transit_report(chart_data)
            major = transit_rpt.get("major_transits", [])
            if major:
                lines = []
                for t in major[:6]:
                    desc = t.get("description") or t.get("type", "")
                    planet = t.get("planet", "")
                    lines.append(f"- {planet}: {desc}")
                formatted_transits = "\n".join(lines)
        except Exception as te:
            logger.warning(f"[daily-context] transit computation failed: {te}")

        return {
            "archetype_name": archetype.get("name", "unknown"),
            "archetype_voice": archetype.get("voice", archetype.get("description", "")),
            "md": current_dashas["md"],
            "ad": current_dashas["ad"],
            "pd": current_dashas["pd"],
            "sd": current_dashas.get("sd", "unknown"),
            "md_end_date": current_dashas.get("md_end_date"),
            "pd_end_date": current_dashas.get("pd_end_date"),
            "sd_end_date": current_dashas.get("sd_end_date"),
            "chara_md": chara_md,
            "natal_moon_sign": natal_moon["sign"],
            "moon_nakshatra": natal_moon["nakshatra"],
            "moon_house": natal_moon["house"],
            "lagna_sign": lagna_sign,
            "d10_lagna": d10_lagna,
            "current_country": current_country,
            "life_stage": life_stage,
            "sleeping_planets": sleeping_planets,
            "formatted_transits": formatted_transits,
            "chart_data": chart_data,  # raw natal data for transit analyzer
        }

    except Exception as e:
        logger.error(f"[daily-context] build_daily_context failed for {chart_id}: {e}")
        return None



# ──────────────────────────────────────────────
# FIX 14b+14c: Post-generation validators
# ──────────────────────────────────────────────

import re as _re_val

_BANNED_TEMPORAL_ES = _re_val.compile(
    r'\b(lunes|martes|mi[eé]rcoles|miercoles|jueves|viernes|s[aá]bado|sabado|domingo|ayer|ma[nñ]ana|manana)\b',
    _re_val.IGNORECASE
)
_BANNED_TEMPORAL_EN = _re_val.compile(
    r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|tomorrow)\b',
    _re_val.IGNORECASE
)

_ENGLISH_LEAK_WORDS = {
    'nurturing', 'auspicious', 'recovery', 'travel', 'investments',
    'moves', 'communication', 'negotiation', 'writing', 'expansive',
    'restoring', 'alignment', 'speeches', 'collective', 'aura',
    'harmonious', 'steady', 'pausing', 'focus', 'spiritual',
    'growth', 'energy', 'flow', 'caution', 'opportunity',
    'reflection', 'connection', 'peak',
}

# FIX E: Instrument names that must never appear in non-English output
_INSTRUMENT_NAMES_EN = {
    'intuition compass', 'emotional radar', 'authority engine',
    'authority signal', 'processing speed', 'fortune vector',
    'relationship channel', 'magnetism field', 'impulse',
    'expansion field', 'structure field', 'vitality',
    'love signal', 'wealth signal', 'career signal',
    'power windows', 'signal detected', 'action drive',
    'ambition engine', 'structural load', 'growth amplifier',
    'revenue pipeline', 'alliance sync', 'capital runway',
    'hungry becoming', 'creative pulse', 'velocity engine',
    'foundation shield', 'wisdom lens', 'health matrix',
    'resource grid', 'system vitals', 'capital reserves',
    'action capacity', 'creation engine', 'conflict shield',
    'global vector', 'real estate radar',
}

_VALIDATED_FIELDS = ['senal_de_hoy', 'observa_hoy_text', 'el_movimiento', 'verdict_subline']


def _validate_no_day_names(signal_json: dict, language: str) -> list:
    """FIX 14b: Check for forbidden day-of-week names in regulated fields."""
    banned = _BANNED_TEMPORAL_ES if language == 'es' else _BANNED_TEMPORAL_EN
    violations = []
    for f in _VALIDATED_FIELDS:
        val = signal_json.get(f, '')
        if isinstance(val, str) and banned.search(val):
            violations.append(f)
    return violations


def _detect_english_leak(signal_json: dict, language: str) -> list:
    """FIX 14c+E: Detect English words AND instrument names leaking into non-English output."""
    if language == 'en':
        return []
    all_text = ' '.join([
        str(signal_json.get(f, '')) for f in _VALIDATED_FIELDS
    ]).lower()
    # Also check haz_hoy and evita_hoy (lists)
    for list_field in ['haz_hoy', 'evita_hoy']:
        items = signal_json.get(list_field, [])
        if isinstance(items, list):
            all_text += ' ' + ' '.join(str(x) for x in items).lower()
    # Also check windows text
    for w in signal_json.get('windows', []):
        if isinstance(w, dict):
            all_text += ' ' + str(w.get('text', '')).lower()
    words_in_text = set(_re_val.findall(r'\b[a-záéíóúñüàèìòù]+\b', all_text))
    leaks = list(_ENGLISH_LEAK_WORDS & words_in_text)
    # FIX E: Also detect instrument name phrases (multi-word)
    for inst in _INSTRUMENT_NAMES_EN:
        if inst in all_text:
            leaks.append(inst)
    return leaks


def _strip_day_names_from_signal(signal_json: dict, language: str) -> dict:
    """Last-resort: regex-strip day names from regulated fields."""
    banned = _BANNED_TEMPORAL_ES if language == 'es' else _BANNED_TEMPORAL_EN
    for f in _VALIDATED_FIELDS:
        val = signal_json.get(f, '')
        if isinstance(val, str) and banned.search(val):
            cleaned = banned.sub('', val)
            cleaned = _re_val.sub(r'\s{2,}', ' ', cleaned).strip()
            cleaned = _re_val.sub(r'^[,\s—–-]+', '', cleaned).strip()
            signal_json[f] = cleaned or val
    return signal_json

# ──────────────────────────────────────────────
# NEW: LLM call for daily signal text
# ──────────────────────────────────────────────

async def _call_claude_daily_signal_retry(
    context: dict,
    day_data: dict,
    language: str,
    violations: dict,
    failed_signal: dict,
) -> Optional[dict]:
    """
    FIX D: Corrective retry — feeds specific violations back to LLM.
    Instead of re-rolling the same prompt, tells Claude exactly what it
    did wrong and demands correction.
    """
    try:
        import anthropic

        from antar_engine.daily_system_prompt import (
            DAILY_SYSTEM_PROMPT_V1,
            DAILY_USER_PROMPT_TEMPLATE,
        )

        prompt_vars = {**context, **day_data, "language": language}
        user_prompt = DAILY_USER_PROMPT_TEMPLATE.format(**prompt_vars)

        # Extract the actual offending words from the failed output
        caught_day_words = []
        banned = _BANNED_TEMPORAL_ES if language == 'es' else _BANNED_TEMPORAL_EN
        for f in violations.get('day_names', []):
            val = failed_signal.get(f, '')
            if isinstance(val, str):
                found = banned.findall(val)
                caught_day_words.extend(found)
        caught_day_words = list(set(caught_day_words))

        caught_eng_words = violations.get('eng_leaks', [])

        # Build corrective block
        corrective_parts = []
        corrective_parts.append("YOUR PREVIOUS OUTPUT WAS REJECTED. You violated hard restrictions.")
        corrective_parts.append("")
        corrective_parts.append("Specific violations:")

        if caught_day_words:
            corrective_parts.append(f"- You used day-of-week words: {caught_day_words}")
            corrective_parts.append(f"- In fields: {violations['day_names']}")
        if caught_eng_words:
            corrective_parts.append(f"- English words leaked into {language} output: {caught_eng_words}")

        corrective_parts.append("")
        corrective_parts.append(f"REGENERATE the entire signal_json for {day_data.get('iso_date', '')}. This time:")
        corrective_parts.append("")

        if caught_day_words:
            corrective_parts.append(f"1. The words {caught_day_words} must NOT appear anywhere in your output.")
            corrective_parts.append("2. Do NOT open any sentence with a day-of-week name in any language.")
            corrective_parts.append("3. Do NOT reference any day of the week. The only temporal word allowed is \"hoy\"/\"today\".")
            corrective_parts.append("4. If you need to reference timing, use hours only (\"antes de las 11 AM\", \"por la tarde\", \"al atardecer\").")

        if caught_eng_words:
            corrective_parts.append(f"5. The English words {caught_eng_words} must NOT appear. Write ONLY in {language}.")
            corrective_parts.append(f"6. Every single word must be in {language}. Zero English.")

        corrective_parts.append("")
        corrective_parts.append("This is a strict correction. Zero tolerance. Produce valid JSON with the same schema.")

        corrective_block = "\n".join(corrective_parts)
        retry_prompt = user_prompt + "\n\n" + corrective_block

        client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        # Use full system prompt (no cache split for retry — it's rare)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            temperature=0.2,  # Lower temp for correction
            system=DAILY_SYSTEM_PROMPT_V1,
            messages=[{"role": "user", "content": retry_prompt}],
        )

        raw_text = response.content[0].text.strip()
        logger.info(f"[daily-llm-retry] output_tokens={response.usage.output_tokens}")

        # Parse JSON
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```", 2)[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        parsed = json.loads(raw_text)
        return parsed

    except json.JSONDecodeError as je:
        logger.error(f"[daily-llm-retry] JSON parse failed: {je}")
        return None
    except Exception as e:
        logger.error(f"[daily-llm-retry] Retry call failed: {e}")
        return None


async def _call_claude_daily_signal(
    context: dict,
    day_data: dict,
    language: str = "en",
) -> Optional[dict]:
    """
    Call Claude Sonnet to generate one day's signal text.
    Returns parsed JSON dict or None on failure.
    """
    try:
        import anthropic

        from antar_engine.daily_system_prompt import (
            DAILY_SYSTEM_PROMPT_V1,
            DAILY_USER_PROMPT_TEMPLATE,
        )

        # Merge context + day data for prompt
        prompt_vars = {**context, **day_data, "language": language}
        user_prompt = DAILY_USER_PROMPT_TEMPLATE.format(**prompt_vars)

        client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        # Split system prompt at ## LIVE DATA for KV caching
        _SPLIT = "## LIVE DATA"
        if _SPLIT in DAILY_SYSTEM_PROMPT_V1:
            static_part, dynamic_part = DAILY_SYSTEM_PROMPT_V1.split(_SPLIT, 1)
            dynamic_part = _SPLIT + dynamic_part
        else:
            static_part = DAILY_SYSTEM_PROMPT_V1
            dynamic_part = ""

        system_blocks = [
            {
                "type": "text",
                "text": static_part,
                "cache_control": {"type": "ephemeral"}
            }
        ]
        if dynamic_part:
            system_blocks.append({"type": "text", "text": dynamic_part})

        # FIX 13: Bumped from 800 → 1500 to prevent JSON truncation
        # (daily signal JSON has 10+ fields including arrays — 800 tokens caused
        # "Unterminated string" parse errors in production logs)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            temperature=0.3,
            system=system_blocks,
            messages=[{"role": "user", "content": user_prompt}],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )

        raw_text = response.content[0].text.strip()
        _cache_r = getattr(response.usage, 'cache_read_input_tokens', 0) or 0
        _cache_w = getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
        logger.info(f"[daily-llm] cache_hit={_cache_r} cache_write={_cache_w} output={response.usage.output_tokens}")

        # Parse JSON — handle markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```", 2)[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        parsed = json.loads(raw_text)
        return parsed

    except json.JSONDecodeError as je:
        logger.error(f"[daily-llm] JSON parse failed: {je}")
        return None
    except Exception as e:
        logger.error(f"[daily-llm] Claude call failed: {e}")
        return None


# ──────────────────────────────────────────────
# NEW: Cache helpers
# ──────────────────────────────────────────────

async def _get_cached_signal(chart_id: str, date_str: str, language: str, supabase_client) -> Optional[dict]:
    """Check Supabase daily_signals cache."""
    try:
        res = supabase_client.table("daily_signals_cache").select("signal_json").eq(
            "chart_id", chart_id
        ).eq("signal_date", date_str).eq("language", language).execute()
        if res.data:
            cached = res.data[0].get("signal_json")
            if cached:
                return _safe_json(cached) if isinstance(cached, str) else cached
    except Exception as e:
        logger.warning(f"[daily-cache] read failed (non-fatal): {e}")
    return None


async def _save_cached_signal(chart_id: str, date_str: str, language: str, signal_json: dict, supabase_client):
    """Save to Supabase daily_signals_cache (upsert)."""
    try:
        supabase_client.table("daily_signals_cache").upsert({
            "chart_id": chart_id,
            "signal_date": date_str,
            "language": language,
            "signal_json": signal_json,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }, on_conflict="chart_id,signal_date,language").execute()
    except Exception as e:
        logger.warning(f"[daily-cache] save failed (non-fatal): {e}")


# ──────────────────────────────────────────────
# Main 7-Day Generator (v2 — LLM-backed)
# ──────────────────────────────────────────────

async def generate_weekly_signals(
    natal_moon_sign: str,
    start_date: Optional[datetime] = None,
    chart_id: Optional[str] = None,
    supabase_client=None,
    language: str = "en",
    tz_offset: int = 0,
    force_refresh: bool = False,
) -> list:
    """
    Generate 7-day daily signal array.

    v2: If chart_id + supabase_client provided, uses Claude LLM for text
    generation with full chart context. Falls back to v1 templates if
    chart_id is None or LLM call fails.

    Args:
        natal_moon_sign: User's natal Moon sign (e.g., "Scorpio")
        start_date: First day of the 7-day window (defaults to today UTC)
        chart_id: Chart UUID for full context (NEW)
        supabase_client: Supabase client instance (NEW)
        language: "en" or "es" (NEW)
        tz_offset: Timezone offset in hours (NEW)

    Returns:
        List of 7 daily signal dicts
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # Build chart context if we have chart_id
    daily_context = None
    use_llm = chart_id is not None and supabase_client is not None
    if use_llm:
        try:
            daily_context = await build_daily_context(chart_id, supabase_client)
            if not daily_context:
                logger.warning(f"[daily-week] Could not build context for {chart_id}, falling back to templates")
                use_llm = False
        except Exception as ce:
            logger.error(f"[daily-week] Context build failed: {ce}")
            use_llm = False

    results = []

    try:
        import swisseph as swe
        MERCURY = swe.MERCURY
    except ImportError:
        logger.error("swisseph not available")
        MERCURY = 2

    for i in range(7):
        target_date = start_date + timedelta(days=i)
        weekday = target_date.strftime("%A")
        date_str = target_date.strftime("%Y-%m-%d")

        # Compute Moon data (KEPT)
        moon_data = get_moon_data_for_date(target_date)
        nakshatra = moon_data["nakshatra"]
        moon_sign = moon_data["sign"]

        # Compute Mercury sign (KEPT)
        mercury_sign = get_planet_sign_for_date(target_date, 2)

        # Compute tithi (KEPT)
        tithi = get_tithi(target_date)

        # Compute chandra bala
        chandra_bala = get_chandra_bala(natal_moon_sign, moon_sign)

        # Score the day (KEPT)
        score, is_friction = _score_day(moon_sign, natal_moon_sign, nakshatra, weekday)

        # Compute panchang quality for this day
        try:
            panchang = calculate_panchang(target_date, 0.0, 0.0)
            panchang_quality = panchang.get("panchang_quality", "mixed")
        except Exception:
            panchang_quality = "mixed"

        # ── LLM path ──
        llm_signal = None
        if use_llm:
            # FIX 14: force_refresh — delete stale cache + skip read
            if force_refresh and supabase_client:
                try:
                    supabase_client.table("daily_signals_cache").delete().eq(
                        "chart_id", chart_id
                    ).eq("signal_date", date_str).eq("language", language).execute()
                    logger.info(f"[daily-week] force_refresh: deleted cache for {chart_id}/{date_str}/{language}")
                except Exception as _fr_e:
                    logger.warning(f"[daily-week] force_refresh delete failed (non-fatal): {_fr_e}")

            # Check cache first (skipped when force_refresh)
            if supabase_client and not force_refresh:
                llm_signal = await _get_cached_signal(chart_id, date_str, language, supabase_client)
                if llm_signal:
                    logger.info(f"[daily-week] Cache HIT for {chart_id}/{date_str}/{language}")

            if not llm_signal:
                # Build day-specific data for prompt
                day_prompt_data = {
                    "iso_date": date_str,
                    "weekday": weekday,
                    "today_moon_sign": moon_sign,
                    "today_moon_nakshatra": nakshatra,
                    "tithi": tithi,
                    "chandra_bala": chandra_bala["strength"],
                    "panchang_quality": panchang_quality,
                    "score": score,
                    "is_friction": is_friction,
                }

                # ── Phase 1+2: Full transit analysis (slow + fast + ashtakavarga + tara + aspects) ──
                try:
                    from antar_engine.daily_transit_analyzer import analyze_day_transits
                    chart_data_raw = daily_context.get("chart_data", {})
                    md_lord = daily_context.get("md", "")
                    user_country = daily_context.get("current_country", "")
                    transit_result = await analyze_day_transits(
                        chart_data=chart_data_raw,
                        target_date=target_date,
                        current_md_lord=md_lord,
                        current_country=user_country,
                    )
                    # Phase 1 blocks (kept)
                    day_prompt_data["transit_analysis_block"] = transit_result["transit_analysis_block"]
                    day_prompt_data["dasha_spotlight_block"] = transit_result["dasha_spotlight_block"]
                    day_prompt_data["synthesis_hints_block"] = transit_result["synthesis_hints_block"]
                    # Phase 2 blocks
                    day_prompt_data["ashtakavarga_block"] = transit_result.get("ashtakavarga_block", "")
                    day_prompt_data["tara_bala_block"] = transit_result.get("tara_bala_block", "")
                    day_prompt_data["aspects_block"] = transit_result.get("aspects_block", "")
                    day_prompt_data["enhanced_synthesis_block"] = transit_result.get("enhanced_synthesis_block", "")
                    # Phase 3 blocks
                    day_prompt_data["day_chart_block"] = transit_result.get("day_chart_block", "")
                    day_prompt_data["day_yogas_block"] = transit_result.get("day_yogas_block", "")
                    day_prompt_data["muhurtas_block"] = transit_result.get("muhurtas_block", "")
                    day_prompt_data["vedha_block"] = transit_result.get("vedha_block", "")
                except Exception as ta_err:
                    logger.warning(f"[daily-week] Transit analysis failed for {date_str}: {ta_err}")
                    day_prompt_data["transit_analysis_block"] = "Transit data unavailable."
                    day_prompt_data["dasha_spotlight_block"] = "No dasha spotlight available."
                    day_prompt_data["synthesis_hints_block"] = "No synthesis hints available."
                    day_prompt_data["ashtakavarga_block"] = ""
                    day_prompt_data["tara_bala_block"] = ""
                    day_prompt_data["aspects_block"] = ""
                    day_prompt_data["enhanced_synthesis_block"] = ""
                    day_prompt_data["day_chart_block"] = ""
                    day_prompt_data["day_yogas_block"] = ""
                    day_prompt_data["muhurtas_block"] = ""
                    day_prompt_data["vedha_block"] = ""

                llm_signal = await _call_claude_daily_signal(
                    context=daily_context,
                    day_data=day_prompt_data,
                    language=language,
                )

                # ── FIX D: Validate + corrective retry ──
                if llm_signal:
                    day_violations = _validate_no_day_names(llm_signal, language)
                    eng_leaks = _detect_english_leak(llm_signal, language)

                    if day_violations or eng_leaks:
                        logger.warning(f"[daily-week] Validation failed for {date_str}: day_names={day_violations} eng_leaks={eng_leaks}")

                        # Build corrective retry prompt with specific violations
                        retry_signal = await _call_claude_daily_signal_retry(
                            context=daily_context,
                            day_data=day_prompt_data,
                            language=language,
                            violations={'day_names': day_violations, 'eng_leaks': eng_leaks},
                            failed_signal=llm_signal,
                        )
                        if retry_signal:
                            retry_day = _validate_no_day_names(retry_signal, language)
                            retry_eng = _detect_english_leak(retry_signal, language)
                            if not retry_day and not retry_eng:
                                llm_signal = retry_signal
                                logger.info(f"[daily-week] Retry succeeded for {date_str}")
                            else:
                                # Strip what we can, accept with warnings
                                retry_signal = _strip_day_names_from_signal(retry_signal, language)
                                retry_signal['_validation_warnings'] = {
                                    'day_names': retry_day, 'english_leaks': retry_eng
                                }
                                llm_signal = retry_signal
                                logger.warning(f"[daily-week] Retry still has issues for {date_str}, accepting with warnings")
                        else:
                            # Retry failed entirely — strip first attempt
                            llm_signal = _strip_day_names_from_signal(llm_signal, language)
                            llm_signal['_validation_warnings'] = {
                                'day_names': day_violations, 'english_leaks': eng_leaks
                            }
                    else:
                        # First pass clean — still strip as safety net
                        llm_signal = _strip_day_names_from_signal(llm_signal, language)


                # Cache if successful
                if llm_signal and supabase_client:
                    await _save_cached_signal(chart_id, date_str, language, llm_signal, supabase_client)
                    logger.info(f"[daily-week] Cached LLM signal for {chart_id}/{date_str}/{language}")

        # ── Build result ──
        if llm_signal:
            # LLM-generated signal — merge with computed data
            day_result = {
                "date": date_str,
                "day": weekday,
                "moon_nakshatra": nakshatra,
                "moon_sign": moon_sign,
                "moon_degree": moon_data["degree"],
                "mercury_sign": mercury_sign,
                "tithi": tithi,
                "score": score,
                "is_friction_day": is_friction,
                # LLM-generated fields
                "verdict_emoji": llm_signal.get("verdict_emoji", "●"),
                "verdict_label": llm_signal.get("verdict_label", ""),
                "verdict_subline": llm_signal.get("verdict_subline", ""),
                "haz_hoy": llm_signal.get("haz_hoy", []),
                "evita_hoy": llm_signal.get("evita_hoy", []),
                "el_movimiento": llm_signal.get("el_movimiento", ""),
                "observa_hoy_domain": llm_signal.get("observa_hoy_domain", "general"),
                "observa_hoy_text": llm_signal.get("observa_hoy_text", ""),
                "senal_de_hoy": llm_signal.get("senal_de_hoy", ""),
                "windows": llm_signal.get("windows", []),
                # Backward compat — map to old fields
                "energy": llm_signal.get("senal_de_hoy", ""),
                "aligned_for": llm_signal.get("haz_hoy", []),
                "friction_for": llm_signal.get("evita_hoy", []),
                "signal": llm_signal.get("senal_de_hoy", ""),
                "move": llm_signal.get("el_movimiento", ""),
                "wow": llm_signal.get("observa_hoy_text"),
                "llm_generated": True,
                "fallback": False,
            }
        else:
            # Fallback to v1 template
            signal_data = _build_signal_text(
                nakshatra=nakshatra,
                moon_sign=moon_sign,
                mercury_sign=mercury_sign,
                natal_moon_sign=natal_moon_sign,
                weekday=weekday,
                score=score,
                is_friction=is_friction
            )

            day_result = {
                "date": date_str,
                "day": weekday,
                "moon_nakshatra": nakshatra,
                "moon_sign": moon_sign,
                "moon_degree": moon_data["degree"],
                "mercury_sign": mercury_sign,
                "tithi": tithi,
                "energy": signal_data["energy"],
                "aligned_for": signal_data["aligned_for"],
                "friction_for": signal_data["friction_for"],
                "signal": signal_data["signal"],
                "move": signal_data["move"],
                "wow": signal_data["wow"],
                "score": score,
                "is_friction_day": is_friction,
                "llm_generated": False,
                "fallback": True,
            }

        results.append(day_result)
        logger.info(f"[daily-week] {date_str} {weekday}: {nakshatra} in {moon_sign} | score={score} | llm={'yes' if llm_signal else 'no'}")

    return results


# ──────────────────────────────────────────────
# Sync wrapper for non-async callers (hora endpoints, feedback)
# ──────────────────────────────────────────────

def generate_weekly_signals_sync(
    natal_moon_sign: str,
    start_date: Optional[datetime] = None,
) -> list:
    """
    Synchronous template-only version for callers that only need
    score/friction (hora endpoints, feedback). No LLM call.
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    results = []

    for i in range(7):
        target_date = start_date + timedelta(days=i)
        weekday = target_date.strftime("%A")
        date_str = target_date.strftime("%Y-%m-%d")

        moon_data = get_moon_data_for_date(target_date)
        nakshatra = moon_data["nakshatra"]
        moon_sign = moon_data["sign"]
        mercury_sign = get_planet_sign_for_date(target_date, 2)
        tithi = get_tithi(target_date)
        score, is_friction = _score_day(moon_sign, natal_moon_sign, nakshatra, weekday)

        signal_data = _build_signal_text(
            nakshatra=nakshatra, moon_sign=moon_sign, mercury_sign=mercury_sign,
            natal_moon_sign=natal_moon_sign, weekday=weekday,
            score=score, is_friction=is_friction
        )

        results.append({
            "date": date_str,
            "day": weekday,
            "moon_nakshatra": nakshatra,
            "moon_sign": moon_sign,
            "moon_degree": moon_data["degree"],
            "mercury_sign": mercury_sign,
            "tithi": tithi,
            "energy": signal_data["energy"],
            "aligned_for": signal_data["aligned_for"],
            "friction_for": signal_data["friction_for"],
            "signal": signal_data["signal"],
            "move": signal_data["move"],
            "wow": signal_data["wow"],
            "score": score,
            "is_friction_day": is_friction,
            "llm_generated": False,
            "fallback": True,
        })

    return results


# ──────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    signals = asyncio.run(generate_weekly_signals(natal_moon_sign="Scorpio"))
    print(json.dumps(signals, indent=2))
