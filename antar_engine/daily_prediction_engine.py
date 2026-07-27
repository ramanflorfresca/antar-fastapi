import re
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

# [output-strips] migrate daily_prediction_engine (Phase 3.7)
# Legacy import retained commented-out for one deploy cycle in case
# we need to roll back.  Once 3.7 is verified, this can be deleted.
# from antar_engine.plain_english import (
#     _strip_jargon, _strip_vedic_jargon, _strip_raw_scores,
#     _strip_instrument_names,
# )
from antar_engine.output_strips import apply_user_facing_strips

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


def get_planet_sign_for_date(target_date: datetime, planet_id: int, tz_offset: float = 0) -> str:
    """Compute sidereal sign of a planet for a given date at user's local noon."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        utc_hour_for_local_noon = 12.0 - tz_offset
        jd = swe.julday(target_date.year, target_date.month, target_date.day, utc_hour_for_local_noon)
        pos, _ = swe.calc_ut(jd, planet_id)
        ayanamsa = swe.get_ayanamsa(jd)
        sidereal = (pos[0] - ayanamsa) % 360
        return SIGNS[int(sidereal / 30)]
    except Exception as e:
        logger.warning(f"get_planet_sign_for_date failed for planet {planet_id}: {e}")
        return "Unknown"


def get_moon_data_for_date(target_date: datetime, tz_offset: float = 0) -> dict:
    """Returns Moon nakshatra, sign, and degree for a given date at user's LOCAL noon.

    Args:
        target_date: The calendar date (user's local date)
        tz_offset: UTC offset in hours (e.g., -5 for Colombia, 5.5 for India).
                   Moon is computed at user's local noon = UTC (12 - tz_offset).
    """
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        # Compute Moon at user's LOCAL noon:
        # Local noon = 12:00 local = (12 - tz_offset) UTC
        utc_hour_for_local_noon = 12.0 - tz_offset
        jd = swe.julday(target_date.year, target_date.month, target_date.day, utc_hour_for_local_noon)
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


def get_tithi(target_date: datetime, tz_offset: float = 0) -> str:
    """Compute approximate tithi (lunar day 1-30) for a date at user's local noon."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        utc_hour_for_local_noon = 12.0 - tz_offset
        jd = swe.julday(target_date.year, target_date.month, target_date.day, utc_hour_for_local_noon)
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
    # [chara-key 2026-07-22] The dict handed to this engine keys the Jaimini
    # periods as "jaimini". This looked only for "chara_dasha" / "jaimini_chara",
    # found nothing, and returned "not available" on EVERY chart — so Chara
    # dasha, one of the systems the product is meant to read from, has never
    # reached a single reading despite being computed and stored.
    chara = (dashas_dict.get("jaimini")
             or dashas_dict.get("chara_dasha")
             or dashas_dict.get("jaimini_chara")
             or [])
    if not chara:
        return "not available"

    for d in chara:
        if not isinstance(d, dict):
            continue
        # Stored as full ISO ("1974-11-26T00:00:00+00:00"); compare on the date
        # part alone so a period starting today is not excluded by the "T".
        start = str(d.get("start_date") or d.get("start", ""))[:10]
        end = str(d.get("end_date") or d.get("end", ""))[:10]
        if start and end and start <= today <= end:
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


# House meanings in PLAIN words. The writer is told what a house governs in
# ordinary language so it does not have to translate jargon itself — when it
# has to, it reaches for vague abstractions instead.
_HOUSE_PLAIN = {
    1:  "you yourself, your health and how you come across",
    2:  "money in hand, savings, family, what you say",
    3:  "your own effort, siblings, short trips, courage",
    4:  "home, mother, property, peace of mind",
    5:  "children, creativity, learning, speculation",
    6:  "work, service, competitors, debts, health routine",
    7:  "partner, clients, deals, the other side of a table",
    8:  "sudden change, other people's money, deep research",
    9:  "luck, father, teachers, long journeys, belief",
    10: "career, reputation, public standing, the boss",
    11: "income, gains, friends, networks, what you get paid",
    12: "expense, foreign places, rest, letting go",
}

# What a transiting planet DOES, in the plainest terms available.
_PLANET_PLAIN = {
    "Sun": "attention and authority", "Moon": "mood and the public",
    "Mars": "push, conflict and machinery", "Mercury": "talk, paperwork and trade",
    "Jupiter": "growth, advice and opening doors", "Venus": "money, comfort and people liking you",
    "Saturn": "slow grind, discipline and delay", "Rahu": "sudden scale and hunger",
    "Ketu": "cutting away and detachment",
}


def _format_transits_for_writer(rpt: dict) -> str:
    """Turn a transit report into concrete lines the daily writer can use.

    Prefers `major_transits` when present, but falls back to the material that
    is almost always there — which houses are being lit up, and the tightest
    aspects. A node RETURN (transit Rahu on natal Rahu) is called out
    explicitly: it happens roughly every 18.6 years and is one of the few
    genuinely rare things a daily card can honestly report.
    """
    if not isinstance(rpt, dict):
        return ""
    lines = []

    for t in (rpt.get("major_transits") or [])[:6]:
        desc = t.get("description") or t.get("type", "")
        lines.append(f"- {t.get('planet','')}: {desc}")

    for area in (rpt.get("activated_areas") or [])[:6]:
        h = area.get("house")
        pls = ", ".join(area.get("planets") or [])
        if not (h and pls):
            continue
        lines.append(f"- {pls} now crossing house {h} — {_HOUSE_PLAIN.get(h, area.get('area',''))}")

    for a in (rpt.get("top_aspects") or [])[:5]:
        tp, np_ = a.get("transit_planet"), a.get("natal_planet")
        if not (tp and np_):
            continue
        orb = a.get("orb")
        orb_s = f", {orb:.1f}deg off exact" if isinstance(orb, (int, float)) else ""
        if tp == np_ and a.get("aspect") == "conjunction" and tp in ("Rahu", "Ketu"):
            lines.append(
                f"- {tp} RETURN: transiting {tp} is back on his natal {tp}{orb_s}. "
                f"This comes round about every 18-19 years — treat it as rare and say so."
            )
            continue
        lines.append(
            f"- transiting {tp} ({_PLANET_PLAIN.get(tp,'')}) {a.get('aspect')} natal "
            f"{np_} in house {a.get('natal_house','?')}"
            f" ({_HOUSE_PLAIN.get(a.get('natal_house'), '')}){orb_s}"
        )
    return "\n".join(lines)


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

        # Get transit report.
        #
        # This used to read ONLY `major_transits` and, finding it empty, told the
        # writer "No transit data available." — while `top_aspects`,
        # `house_activation` and `activated_areas` in the same report were full.
        # A user with Sun and Jupiter crossing his 10th, a Rahu return at 0.62
        # orb and Venus sextile natal Mercury was handed a blank page, so the
        # card fell back to abstractions ("your intelligence is high") because
        # abstraction is all that is left when nothing concrete is supplied.
        formatted_transits = "No transit data available."
        try:
            from antar_engine.transit_engine import get_full_transit_report
            transit_rpt = get_full_transit_report(chart_data)
            formatted_transits = _format_transits_for_writer(transit_rpt) or formatted_transits
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
            # Needed by _validate_no_invented_specifics: the only place names
            # the reading is permitted to use are the ones the chart actually
            # contains.
            "chart_row": {k: row.get(k) for k in
                          ("birth_city", "birth_country", "current_city",
                           "current_country", "first_name", "name")},
            "chart_data": chart_data,  # raw natal data for transit analyzer
            "lk_data": lk_data,  # raw LK data for daily diagnostic
            "tz_offset": 0,  # placeholder — actual tz_offset passed separately at call site
        }

    except Exception as e:
        logger.error(f"[daily-context] build_daily_context failed for {chart_id}: {e}")
        return None



# ──────────────────────────────────────────────
# FIX 14b+14c: Post-generation validators
# ──────────────────────────────────────────────

import re as _re_val

_BANNED_TEMPORAL_ES = _re_val.compile(
    # Weekday names + 'ayer' (yesterday) are always banned.
    r'\b(?:lunes|martes|mi[eé]rcoles|miercoles|jueves|viernes|s[aá]bado|sabado|domingo|ayer)\b'
    # 'mañana' is banned ONLY in its 'tomorrow' sense. Exempt the
    # unambiguous MORNING forms (la/esta/una/de mañana) so legitimate
    # time-of-day references don't false-fire the daily validator.
    r'|(?<!la )(?<!ta )(?<!na )(?<!de )\bma[nñ]ana\b',
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

_VALIDATED_FIELDS = ['senal_de_hoy', 'observa_hoy_text', 'verdict_subline', 'el_movimiento']
# [why-block-leak-fix] el_movimiento is rendered VERBATIM by the frontend as
# the italic "why" block under the verdict — it is user-facing display, not an
# internal evidence layer. It gets the same validation + strips as every other
# plain field.


# The headline is the ONLY line many users read. It kept opening on a faculty —
# "Strong intellectual current today", "Your intelligence is high" — which names
# a quality of mind rather than anything the reader can act on or recognise. Two
# separate users said they did not understand what it meant.
#
# A prompt rule alone did not hold, so this detects the pattern and forces the
# corrective retry that already exists for day-name violations.
_ABSTRACT_SUBJECTS = (
    "intellectual", "intelligence", "mental", "cognitive", "emotional weight",
    "energy", "vibration", "alignment", "manifestation", "potential",
    "capacity", "clarity", "awareness", "consciousness", "aura", "frequency",
    "vitality", "intuition", "current", "strength of mind", "inner state",
)

# Things a person can actually observe happening. A headline may talk about
# qualities as much as it likes, PROVIDED it also names one of these — that is
# what lets the reader check tonight whether the day went as described.
_CONCRETE_ANCHORS = (
    "someone", "somebody", "anyone", "person", "people", "they",
    "call", "message", "text", "email", "conversation", "talk", "reply",
    "meeting", "deal", "contract", "offer", "negotiation", "proposal",
    "money", "payment", "invoice", "bill", "debt", "price", "number",
    "client", "customer", "boss", "partner", "colleague", "family", "friend",
    "sign", "send", "ask", "answer", "say", "speak", "write", "decide",
    "sleep", "food", "eat", "travel", "trip", "document", "paperwork",
    "buy", "sell", "pay", "meet",
    # NOT finish / close / start / wait: those verbs apply just as happily to
    # an abstraction ("use the clarity for finishing") and so are no evidence
    # that anything observable was named.
)
# Word-bounded, like every other matcher in this engine has had to become.
# The first cut used bare substrings and "he " matched inside "t-he ", so a
# headline about "the clarity" counted as naming a person and passed. That is
# the fifth substring trap found in this codebase; bare `in` on human sentences
# does not work.
_ANCHOR_RE = re.compile(
    "|".join(r"\b" + re.escape(w) + r"\w*" for w in _CONCRETE_ANCHORS), re.I)
_ABSTRACT_RE = re.compile(
    "|".join(r"\b" + re.escape(w) for w in _ABSTRACT_SUBJECTS), re.I)
_HEADLINE_FIELDS = ("senal_de_hoy", "signal", "verdict_subline")


# Words that may legitimately be capitalised in a reading. Everything else that
# looks like a proper noun is treated as INVENTED, because the chart cannot know
# it. A real card shipped:
#
#   "Someone from your past — perhaps a familiar face from Delhi or an old
#    Colorado connection — steps back into your world today."
#
# Colorado appears nowhere in that user's data. Fabricated specificity is worse
# than vagueness: vague is forgettable, but a named place the reader knows to be
# wrong tells them the whole thing is guesswork. Rule 11b told the model not to
# invent a person, company or amount; it named a US state instead.
_PROPER_NOUN_OK = set("""
Sun Moon Mars Mercury Jupiter Venus Saturn Rahu Ketu
Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces
Ashwini Bharani Krittika Rohini Mrigashira Ardra Punarvasu Pushya Ashlesha Magha
Purva Uttara Phalguni Hasta Chitra Swati Vishakha Anuradha Jyeshtha Mula Ashadha
Shravana Dhanishta Shatabhisha Bhadrapada Revati Abhijit
Monday Tuesday Wednesday Thursday Friday Saturday Sunday
January February March April May June July August September October November December
Antar AM PM I You Your Today Tomorrow Tonight The A An It If And But So When What Where Who Why How
This That These Those There Here One Two Three Four Five Six Seven Eight Nine Ten
Rahu-Kalam Abhijit Kalam Lal Kitab Vedic
""".split())


def _validate_no_invented_specifics(signal_json: dict, chart_row: dict = None) -> list:
    """Fields naming a place or proper noun the chart has no basis for.

    The user's own birth and current city are allowed — those are known facts.
    Anything else capitalised mid-sentence is a fabrication.
    """
    allowed = set(_PROPER_NOUN_OK)
    for k in ("birth_city", "current_city", "birth_country", "current_country",
              "first_name", "name"):
        v = (chart_row or {}).get(k)
        if isinstance(v, str):
            allowed.update(re.findall(r"[A-Z][a-zA-Z]+", v))
    bad = []
    for f in _VALIDATED_FIELDS:
        v = signal_json.get(f)
        if not isinstance(v, str) or not v.strip():
            continue
        # mid-sentence capitals only: skip a word that starts a sentence
        for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-zA-Z]{2,})\b", v):
            w = m.group(1)
            if w not in allowed:
                bad.append((f, w))
                break
    return bad


# A claim needs something to HAPPEN or something to DO. Atmospheric headlines
# ("a favorable day for trade and direct conversation") clear the concrete-anchor
# bar — "conversation" is a real noun — while still predicting nothing. So the
# headline must also carry an event verb or an instruction.
_EVENT_VERBS = (
    "reach", "reaches", "arrive", "arrives", "call", "calls", "message",
    "messages", "notice", "notices", "offer", "offers", "ask", "asks",
    "pay", "pays", "move", "moves", "come", "comes", "return", "returns",
    "land", "lands", "open", "opens", "reply", "replies", "respond",
    "responds", "show", "shows", "surface", "surfaces", "resurface",
    "resurfaces", "appear", "appears", "happen", "happens", "close",
    "closes", "arrive", "sign", "signs", "want", "wants", "bring", "brings",
    "llega", "llegan", "aparece", "responde", "ofrece", "paga",
)
_IMPERATIVES = (
    "send", "call", "ask", "say", "write", "finish", "close", "chase",
    "make", "have", "take", "check", "confirm", "follow up", "reply",
    "hold", "wait", "start", "book", "pay", "collect", "push",
    "envia", "envía", "llama", "pregunta", "termina", "cobra",
)
_CLAIM_RE = re.compile(
    "|".join(r"\b" + re.escape(w) + r"\b" for w in set(_EVENT_VERBS + _IMPERATIVES)),
    re.I,
)


def _validate_headline_concrete(signal_json: dict, language: str) -> list:
    """Fields whose headline opens on an abstraction instead of a situation."""
    bad = []
    for f in _HEADLINE_FIELDS:
        v = signal_json.get(f)
        if not (isinstance(v, str) and v.strip()):
            continue
        # Flag only when the line leans on an abstraction AND offers nothing
        # observable anywhere in it. Requiring the abstraction to be the first
        # word was too narrow — "Today carries real intellectual strength
        # wrapped inside emotional weight" sailed through and was exactly the
        # sentence a user said he could not understand.
        # Reject when it leans on an abstraction with nothing observable, OR
        # when it is purely atmospheric — no event, no instruction.
        if _ABSTRACT_RE.search(v) and not _ANCHOR_RE.search(v):
            bad.append(f)
        elif f == "senal_de_hoy" and not _CLAIM_RE.search(v):
            bad.append(f)
    return bad


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


_DANGLING_FIXES = (
    # A stripped weekday leaves its possessive behind: "Tuesday's stronger
    # window" -> "'s stronger window". Seen live on a real card.
    (re.compile(r"(?:^|(?<=\s))['’]s\b\s*", re.I), ""),
    # ...or leaves a preposition pointing at nothing: "priorities for." /
    # "prepare for ." / "good for  ."
    (re.compile(r"\b(for|on|by|until|before|after|through)\s*(?=[.,;!?]|$)", re.I), ""),
    # Two weekdays in one phrase both become the same relative phrase:
    # "Monday or Wednesday" -> "later this week or later this week".
    (re.compile(r"\b(later this week|the next)\b(?:\s*(?:,|or|and)\s*\1\b)+", re.I), r"\1"),
    (re.compile(r"\b(en los pr\u00f3ximos d\u00edas)\b(?:\s*(?:,|o|y)\s*\1\b)+", re.I), r"\1"),
    # "act on later this week" reads wrong; the phrase is already adverbial.
    (re.compile(r"\bon\s+(later this week)\b", re.I), r"\1"),
    (re.compile(r"\s{2,}"), " "),
    (re.compile(r"\s+([.,;!?])"), r"\1"),
    (re.compile(r"([.,;!?])\1+"), r"\1"),
)


def _clean_temporal_fragments(text):
    """Repair the wreckage a day-name strip leaves in a sentence.

    Removing "Tuesday" from "Tuesday's stronger action window" satisfies the
    no-day-names rule and produces "'s stronger action window", which is worse
    than the violation. Same for "prepare for ." Cosmetic, but it is the first
    thing a user notices and it makes the whole card look unfinished.
    """
    if not isinstance(text, str) or not text.strip():
        return text
    out = text
    for rx, rep in _DANGLING_FIXES:
        out = rx.sub(rep, out)
    return out.strip()


def _hhmm(clock):
    """"10:44 AM" -> minutes since midnight, or None."""
    if not isinstance(clock, str):
        return None
    m = re.match(r"\s*(\d{1,2}):(\d{2})\s*([AaPp])[Mm]", clock.strip())
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    if ap == "a" and h == 12:
        h = 0
    if ap == "p" and h != 12:
        h += 12
    return h * 60 + mi


def _resolve_window_overlaps(windows):
    """A peak window must not sit inside a caution window.

    A real card offered a "sharpest window" of 10:20-11:08 AM while the caution
    window ran 10:44-11:56 AM, then explained the collision in prose: "avoid the
    overlap with the caution period that begins at 10:44." That asks the user to
    do arithmetic to find out when they are actually allowed to act.

    The good window is trimmed to end where the caution begins. If nothing
    usable is left (under 10 minutes), the window is dropped rather than shown
    as a slot too short to use.
    """
    if not isinstance(windows, list):
        return windows
    CAUTION = {"caution", "avoid", "friction", "rahu", "rahu_kalam"}
    GOOD = {"peak", "best", "auspicious", "abhijit", "connection", "reflection"}
    bad = []
    for w in windows:
        if not isinstance(w, dict):
            continue
        if str(w.get("type", "")).lower() in CAUTION:
            a, b = _hhmm(w.get("start")), _hhmm(w.get("end"))
            if a is not None and b is not None:
                bad.append((a, b))
    if not bad:
        return windows
    out = []
    for w in windows:
        if not isinstance(w, dict) or str(w.get("type", "")).lower() not in GOOD:
            out.append(w)
            continue
        a, b = _hhmm(w.get("start")), _hhmm(w.get("end"))
        if a is None or b is None:
            out.append(w)
            continue
        # Keep the LARGEST clear stretch rather than trimming repeatedly. The
        # sequential version collapsed a window to nothing when two cautions
        # straddled it, and a real card lost all three of its good windows —
        # leaving only the caution. That is strictly worse than the overlap it
        # was written to fix: the user is told when NOT to act and never when
        # to act.
        segments, cursor = [], a
        for ca, cb in sorted(bad):
            if cb <= cursor or ca >= b:
                continue
            if ca > cursor:
                segments.append((cursor, min(ca, b)))
            cursor = max(cursor, cb)
            if cursor >= b:
                break
        if cursor < b:
            segments.append((cursor, b))
        segments = [(x, y) for x, y in segments if y - x >= 10]
        if not segments:
            # Fully buried. Keep the window rather than deleting it — a good
            # window that shares time with a caution is still information, and
            # the caution is shown alongside it.
            out.append(w)
            continue
        a, b = max(segments, key=lambda seg: seg[1] - seg[0])
        def _fmt(mins):
            h, mi = divmod(mins, 60)
            ap = "AM" if h < 12 else "PM"
            hh = h % 12 or 12
            return f"{hh}:{mi:02d} {ap}"
        w = dict(w)
        w["start"], w["end"] = _fmt(a), _fmt(b)
        out.append(w)
    return out


def _tidy_signal(signal_json: dict, language: str = "en") -> dict:
    """Final pass over everything the user actually reads.

    _VALIDATED_FIELDS is a short list; day names also reach haz_hoy, evita_hoy
    and the window texts, which is where the broken sentences were seen.
    """
    if not isinstance(signal_json, dict):
        return signal_json
    _fix = lambda t: _clean_temporal_fragments(_substitute_day_names(t, language))
    for k, v in list(signal_json.items()):
        if isinstance(v, str):
            signal_json[k] = _fix(v)
        elif isinstance(v, list):
            signal_json[k] = [_fix(x) if isinstance(x, str) else x for x in v]
    for w in signal_json.get("windows") or []:
        if isinstance(w, dict) and isinstance(w.get("text"), str):
            w["text"] = _fix(w["text"])
    # signals[] is built deterministically, not written by the model, so it
    # never passed through the jargon strip — and shipped "Swati · Naidhana"
    # onto a real user's card. Naidhana is on the banned list precisely because
    # it means nothing to a reader and, translated, means "death star". The
    # replacement rules already existed; they were simply never applied here.
    # Replacing jargon with an abstraction is not an improvement. The generic
    # strip turns "Swati · Naidhana" into "lunar energy · transformative lunar
    # energy", which is longer, vaguer and still tells the reader nothing. The
    # tara is a nine-step scale of how the day treats you; say THAT.
    _TARA_PLAIN = {
        "janma":     "mixed for you",
        "sampat":    "things come to you",
        "vipat":     "avoid risk today",
        "kshema":    "safe and steady",
        "pratyari":  "expect resistance",
        "sadhana":   "effort pays off",
        "naidhana":  "protect what you have",
        "mitra":     "people are on your side",
        "ati-mitra": "strongly in your favour",
        "atimitra":  "strongly in your favour",
    }
    for sig in signal_json.get("signals") or []:
        if not isinstance(sig, dict) or not isinstance(sig.get("value"), str):
            continue
        parts = [p.strip() for p in re.split(r"[·|]", sig["value"])]
        rebuilt = [_TARA_PLAIN.get(p.lower(), p) for p in parts if p]
        if rebuilt:
            sig["value"] = " · ".join(rebuilt)
    # NOT the generic strip. Run over this row it produced
    #     "Moon's star"          -> "your emotional and nurturing energy's star"
    #     "Mars -> Moon -> Venus" -> "your action and drive energy -> your
    #                                emotional and nurturing energy -> ..."
    # Planet names are the most CREDIBLE thing on the card: concrete, checkable,
    # and what any astrologer would say out loud. Replacing them with feelings
    # vocabulary is what makes the read sound like a horoscope. The strip exists
    # to remove untranslated technical terms from PROSE, not to launder every
    # proper noun out of a labelled data row.
    signal_json["windows"] = _resolve_window_overlaps(signal_json.get("windows"))
    # "wow" was rendering byte-identical to observa_hoy_text, so the same
    # paragraph appeared twice on one card.
    if (signal_json.get("wow") or "").strip() and \
       (signal_json.get("wow") or "").strip() == (signal_json.get("observa_hoy_text") or "").strip():
        signal_json["wow"] = None
    return signal_json


# Replacing a weekday beats deleting it. Deletion satisfies the no-day-names
# rule and wrecks the sentence: "opens Thursday" -> "opens.", "Tuesday's
# stronger window" -> "'s stronger window", "priorities for Friday" ->
# "priorities for." All three shipped to real cards. A relative phrase keeps
# the meaning AND the grammar, and stays true whichever day the card is read.
_DAY_POSSESSIVE = re.compile(
    r"\b(?:mon|tues|wednes|thurs|fri|satur|sun)day['\u2019]s\b", re.I)
_DAY_POSSESSIVE_ES = re.compile(
    r"\bdel? (?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b", re.I)


def _substitute_day_names(text: str, language: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text
    if language == 'es':
        out = _DAY_POSSESSIVE_ES.sub("de los pr\u00f3ximos d\u00edas", text)
        return (_BANNED_TEMPORAL_ES.sub("en los pr\u00f3ximos d\u00edas", out)
                if _BANNED_TEMPORAL_ES.search(out) else out)
    out = _DAY_POSSESSIVE.sub("the next", text)
    return (_BANNED_TEMPORAL_EN.sub("later this week", out)
            if _BANNED_TEMPORAL_EN.search(out) else out)


def _strip_day_names_from_signal(signal_json: dict, language: str) -> dict:
    """Replace day names in regulated fields, then repair any wreckage."""
    banned = _BANNED_TEMPORAL_ES if language == 'es' else _BANNED_TEMPORAL_EN
    for f in _VALIDATED_FIELDS:
        val = signal_json.get(f, '')
        if isinstance(val, str) and banned.search(val):
            cleaned = _substitute_day_names(val, language)
            cleaned = _re_val.sub(r'\s{2,}', ' ', cleaned).strip()
            cleaned = _re_val.sub(r'^[,\s—–-]+', '', cleaned).strip()
            signal_json[f] = cleaned or val
    return signal_json


import re as _re_faith
# [faith-neutral P3 2026-07-12] The daily nudge kept naming a specific place of
# worship ("donation at the church...") — a real miss for users of another faith
# (e.g. a Sikh). The system-prompt rule alone didn't hold (LLMs default to
# "church"), so neutralize deterministically here. Replaces "<article> <house of
# worship>" with "a place of worship", keeping the surrounding sentence intact.
_FAITH_HOUSE_RE = _re_faith.compile(
    r'\b(?:the|a|an|your|his|her|their|el|la|un|una|tu|su)\s+'
    r'(?:local\s+)?(?:church|temple|mosque|gurdwara|gurudwara|synagogue|'
    r'mandir|masjid|iglesia|templo|mezquita|sinagoga)\b', _re_faith.I)
_FAITH_BARE_RE = _re_faith.compile(
    r'\b(?:church|mosque|gurdwara|gurudwara|synagogue|mandir|masjid|'
    r'iglesia|mezquita|sinagoga)\b', _re_faith.I)


def _faith_neutralize(text):
    """Swap a named house of worship for a faith-neutral phrase. Best-effort."""
    if not text or not isinstance(text, str):
        return text
    es = any(w in text.lower() for w in ("iglesia", "templo", "mezquita", "sinagoga"))
    neutral = "un lugar de culto" if es else "a place of worship"
    out = _FAITH_HOUSE_RE.sub(neutral, text)
    out = _FAITH_BARE_RE.sub(neutral, out)
    return out


# [cosmic-leak 2026-07-27] The plain scrub (apply_user_facing_strips) removes
# planet/sign names but NOT astronomy synonyms, cycle-rarity claims, or the
# day-frame's own "completing/starting" language — a live card opened with "A
# rare nodal return is active — something that happens once every 18-19 years.
# Today asks you to notice what is completing, not what is starting." Drop any
# SENTENCE carrying that class of leak, rather than word-stripping it into
# fragments. Cheap safety net behind the day_frame silent-rule fix.
_COSMIC_LEAK_RX = re.compile(
    r"(?i)\b("
    r"nodal|nodes?|eclipse|sidereal|ephemeris|jyotish|vedic|zodiac|retrograde|"
    r"lunar\s+return|solar\s+return|saturn\s+return|"
    r"once\s+(?:in|every)\s+[\w\s-]{0,12}?\d+\s*(?:[-–]\s*\d+\s*)?years?|"
    r"every\s+\d+\s*(?:[-–]\s*\d+\s*)?years?|"
    # [gate-widen 2026-07-27] compare view proved these slip through:
    r"\d+\s*[-–\s]\s*year\s+cycle|\d+\s*[-–]\s*\d+\s*year|"   # "18-year cycle" (single #) + ranges
    r"karmic(?:\s+(?:reset|axis|cycle|gateway|gate|window|node|lesson|theme|reckoning))?|"  # karmic + bare
    r"(?:cosmic|celestial|astral)\s+\w+|"                    # "cosmic reset", "celestial shift"
    r"what\s+is\s+completing|not\s+what\s+is\s+starting|coming\s+full\s+circle|"
    r"a\s+new\s+cycle"
    r")\b"
)


# [mechanics-jargon 2026-07-27] Step 2 of the narration pass: the SOFT jargon
# class the planet/sign strip misses — astrological MECHANICS verbalized into
# prose. A live card read "the strong planetary strength in the income zone is
# real — but the favorable your growth and wisdom energy transit is blocked" and
# "a hard aspect from a fast-moving planet." These are the engine's own workings
# leaking as explanation. High-precision astro-context phrases only — bare
# "energy"/"aspect" are left alone because the product voice uses "the day's
# energy" and "every aspect of life" legitimately.
_MECHANICS_JARGON_RX = re.compile(
    r"(?i)("
    r"\b(?:hard|soft|challenging|favou?rable|tight|close|exact)\s+aspect\b|"
    r"\baspect(?:ed|ing|s)?\s+(?:from|by|to)\b|"
    r"\benergy\s+transit\b|\btransit(?:s|ing|ed)?\s+(?:is|are|of|through|blocked|active|strong)\b|"
    r"\bplanetary\s+(?:strength|position|energy|influence)\b|"
    r"\bstrength\s+in\s+the\s+\w+\s+zone\b|"
    r"\b(?:income|gains?|money|wealth|career|love|marriage|health|home)\s+zone\b|"
    r"\bfast[-\s]moving\s+planet\b|\bslow[-\s]moving\s+planet\b|"
    r"\bretrograde\b|\bconjunction\b|\bnakshatra\b|\bhouse\s+lord\b|"
    r"\b(?:lunar|solar)\s+energy\b"
    r")"
)


def _mechanics_fields(signal_json: dict) -> list:
    """User-facing fields verbalizing astrological mechanics."""
    bad = []
    for f in ("verdict_subline", "senal_de_hoy", "observa_hoy_text", "el_movimiento"):
        v = signal_json.get(f)
        if isinstance(v, str) and _MECHANICS_JARGON_RX.search(v):
            bad.append(f)
    for f in ("haz_hoy", "evita_hoy"):
        arr = signal_json.get(f)
        if isinstance(arr, list) and any(
                isinstance(x, str) and _MECHANICS_JARGON_RX.search(x) for x in arr):
            bad.append(f)
    return bad


def _scrub_cosmic_leak(text):
    """Drop whole sentences that name astronomy / cycle-rarity / the day frame /
    astrological mechanics. Removing the sentence (not the word) avoids mangled
    fragments; empty is better than a jargon leak (the frame/prompt fixes + the
    retry are the primary defences — this is the last-resort net)."""
    if not isinstance(text, str) or not text.strip():
        return text
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept = [p for p in parts
            if not _COSMIC_LEAK_RX.search(p) and not _MECHANICS_JARGON_RX.search(p)]
    out = " ".join(kept).strip()
    return out if out else ""


# [completeness 2026-07-27] Catch TRUNCATED / grammatically-broken user-facing
# sentences before they ship — "offer it in the — your steadiness lands well
# today" and "the favorable your growth and wisdom energy transit is blocked"
# both reached a live card. High-precision patterns only: each marks an
# unrecoverable structural break (a dropped word), so a hit triggers a
# regeneration rather than a repair — we can't know what word was lost.
# `(?<!-)` on each dangling-word pattern: a function word that is the TAIL of a
# hyphenated compound ("check-in,", "follow-on.", "run-on;") is not dangling —
# the hyphen creates a false word boundary that these patterns would otherwise
# read as a standalone preposition/article. Same false-positive family as the
# em-dash compound guard above.
_BROKEN_PATTERNS = (
    # a function word left dangling before a DASH break or clause end. The dash
    # must be an em/en dash, or a SPACE-BOUNDED hyphen — a word-internal hyphen
    # ("behind-the-scenes", "state-of-the-art") is a compound, not a break.
    re.compile(r"\b(?<!-)(in|on|at|to|of|the|a|an|for|with|and|or|but|your|his|her|"
               r"their|before|after|by|into|onto|from)\b(?:\s*[—–]\s*|\s+-\s+)"
               r"(?=[a-z]|$)", re.I),
    re.compile(r"\b(?<!-)(in|on|at|to|of|the|a|an|for|with|and|or|but|your|his|her|"
               r"their|before|after|by|into|onto|from)\s*[.,;!?]", re.I),
    re.compile(r"\b(?<!-)(in|on|at|to|of|the|a|an|for|with|and|or|but|your)\s*$", re.I),
    # determiner + word + possessive/determiner with no noun between
    # ("the favorable your", "a strong the")
    re.compile(r"\b(the|a|an)\s+\w+\s+(your|his|her|their|the|a|an)\s+\w+", re.I),
)
# The determiner-gap pattern above is too broad alone ("the best of the day" is
# fine); only flag it when the middle word is an ADJECTIVE-shaped token that
# clearly wants a noun. Kept simple: flagged only via _looks_broken's guard.
_ADJ_HINT = re.compile(r"\w+(ly|ful|ous|ive|able|ible|al|ic|ant|ent)$", re.I)


def _looks_broken(text) -> bool:
    """True if a user-facing sentence has an unrecoverable structural break."""
    if not isinstance(text, str) or len(text.strip()) < 8:
        return False
    t = text.strip()
    # dangling function word before dash / punctuation / end
    for rx in _BROKEN_PATTERNS[:3]:
        if rx.search(t):
            return True
    # determiner + adjective + determiner (no noun): "the favorable your ..."
    for m in _BROKEN_PATTERNS[3].finditer(t):
        mid = m.group(0).split()[1]
        if _ADJ_HINT.search(mid):
            return True
    # an EM-dash with no real content after it (< 2 words to the next stop).
    # Split on em-dash ONLY, never en-dash: en-dash is a RANGE connector
    # ("February–March", "Jul 2026 – Oct 2026") whose short tail is a label, not
    # a dangling sentence — flagging it was a false positive.
    for seg in re.split(r"—", t)[1:]:
        tail = seg.strip()
        if tail and len(re.findall(r"\w+", tail.split(".")[0])) < 2:
            return True
    return False


def _broken_fields(signal_json: dict) -> list:
    """User-facing fields carrying a truncated/broken sentence."""
    bad = []
    for f in ("verdict_subline", "senal_de_hoy", "observa_hoy_text", "el_movimiento"):
        if _looks_broken(signal_json.get(f)):
            bad.append(f)
    for f in ("haz_hoy", "evita_hoy"):
        arr = signal_json.get(f)
        if isinstance(arr, list) and any(_looks_broken(x) for x in arr):
            bad.append(f)
    return bad


def _strip_all_jargon_from_signal(signal_json: dict, language: str) -> dict:
    """
    Apply centralized output strips to user-facing fields before cache write.

    Delegates to antar_engine.output_strips.apply_user_facing_strips, which
    handles Spanish planet names, non-canonical X/56 scores, plural day
    names, compound Vedic terms, and instrument codenames — all in one
    place, shared with every other migrated endpoint.

    Field → field_type mapping:
      'plain'   senal_de_hoy, observa_hoy_text, verdict_subline,
                haz_hoy[], evita_hoy[]
      'window'  windows[].text   (keeps Panchang terms like Abhijit
                                  Muhurta, Rahu Kalam)
      'plain'   el_movimiento — [why-block-leak-fix] the frontend renders
                this verbatim as the italic "why" block; it must be coach
                voice like everything else
      (untouched) verdict_emoji, verdict_label, domain, dates, etc.
    """
    if not signal_json or not isinstance(signal_json, dict):
        return signal_json

    # Scalar plain fields
    for _f in ('senal_de_hoy', 'observa_hoy_text', 'verdict_subline', 'el_movimiento'):
        _v = signal_json.get(_f)
        if isinstance(_v, str) and _v:
            signal_json[_f] = _scrub_cosmic_leak(_faith_neutralize(apply_user_facing_strips(
                _v, language=language, field_type='plain'
            )))

    # List plain fields — MUST also pass the cosmic gate. Previously only the
    # scalar fields were scrubbed, so "nodal return / karmic axis / 18-year
    # cycle" leaked through haz_hoy/evita_hoy (this is why Shashi's avoid item
    # kept carrying "the nodal return amplifies temptation" after the gate fix).
    for _f in ('haz_hoy', 'evita_hoy'):
        _arr = signal_json.get(_f)
        if isinstance(_arr, list):
            _scrubbed = [
                _scrub_cosmic_leak(_fix_reversed_range(
                    _faith_neutralize(apply_user_facing_strips(_x, language=language, field_type='plain'))))
                if isinstance(_x, str) and _x else _x
                for _x in _arr
            ]
            # a scrub can empty an item whose whole sentence was the leak — drop
            # those so the card never shows a blank bullet.
            signal_json[_f] = [_x for _x in _scrubbed
                               if not (isinstance(_x, str) and not _x.strip())]

    # [why-block-leak-fix] el_movimiento now stripped above — it renders
    # directly on the Today card and must never carry raw jargon.

    # [3.7c] windows[].text uses 'plain' — UI does not gloss Panchang
    # terms, so translate Rahu Kalam / Abhijit Muhurta / Gulika Kala
    # to their plain-Spanish equivalents just like every other field.
    windows = signal_json.get('windows') or []
    if isinstance(windows, list):
        # [window-coherence 2026-07-20] The LLM writes start/end/text together
        # and sometimes contradicts itself: a 10 PM window described as "morning
        # hours". The clock is deterministic; the prose is not — so when they
        # disagree, trust the clock and drop the misleading time-of-day claim
        # from the text rather than shipping a self-contradiction.
        for w in windows:
            if isinstance(w, dict):
                # [window-bounds 2026-07-20] The LLM also emits the structured
                # start/end backwards ("09:33 AM" -> "08:21 AM"). _fix_reversed_range
                # only mends prose; these fields drive the full-day view, so swap
                # a same-half-day pair whose end precedes its start. A genuine
                # overnight window (PM -> AM) is left alone.
                _s, _e = _hour24(w.get('start')), _hour24(w.get('end'))
                if (_s is not None and _e is not None and _e < _s
                        and (_s < 12) == (_e < 12)):
                    w['start'], w['end'] = w.get('end'), w.get('start')
                w['text'] = _reconcile_window_text(
                    w.get('text'), w.get('start'), w.get('end'))
                t = w.get('text')
                if isinstance(t, str) and t:
                    w['text'] = apply_user_facing_strips(
                        t, language=language, field_type='plain'
                    )

    return signal_json


# [window-coherence 2026-07-20] ----------------------------------------------
_TOD_WORDS = {
    "morning":   (5, 12),
    "afternoon": (12, 17),
    "evening":   (17, 21),
    "night":     (21, 29),      # 29 == 5 next day; night wraps midnight
    "midday":    (11, 14),
    "noon":      (11, 14),
    "midnight":  (23, 25),
    "dawn":      (4, 7),
    "dusk":      (17, 20),
}


def _hour24(clock: str):
    """'10:00 PM' -> 22.0, tolerant. None if unparseable."""
    if not isinstance(clock, str) or not clock.strip():
        return None
    import re as _r
    m = _r.match(r'\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp][Mm])?', clock.strip())
    if not m:
        return None
    h = int(m.group(1)); mm = int(m.group(2) or 0)
    ap = (m.group(3) or "").lower()
    if ap == "pm" and h != 12:
        h += 12
    elif ap == "am" and h == 12:
        h = 0
    return h + mm / 60.0


def _fix_reversed_range(text):
    """Swap a 'between H1 and H2' range whose end is BEFORE its start.

    The model sometimes emits a caution window backwards -- "Between 2:18 PM and
    1:07 PM" -- which reads as broken. When the two clock times are within the
    same ~12h span and the second is earlier, they are reversed, not a genuine
    overnight window, so swap them. A real overnight range (e.g. 10 PM to 2 AM)
    has the second time in AM and the first in PM and is left alone.
    """
    if not isinstance(text, str) or not text.strip():
        return text
    import re as _r
    m = _r.search(
        r'\b(?:between|from)\s+'
        r'(?:approximately|approx\.?|around|about|roughly|~)?\s*'
        r'(\d{1,2}(?::\d{2})?\s*[AaPp][Mm])\s+'
        r'(?:and|to|[-\u2013\u2014])\s+'
        r'(?:approximately|approx\.?|around|about|roughly|~)?\s*'
        r'(\d{1,2}(?::\d{2})?\s*[AaPp][Mm])',
        text, _r.IGNORECASE)
    if not m:
        return text
    a, b = _hour24(m.group(1)), _hour24(m.group(2))
    if a is None or b is None or b >= a:
        return text
    # b < a. Genuine overnight (PM -> AM) is legitimate; only swap when both
    # sit in the same half-day (both AM or both PM), which cannot be overnight.
    both_same_half = (a < 12) == (b < 12)
    if not both_same_half:
        return text
    return text[:m.start(1)] + m.group(2) + text[m.end(1):m.start(2)] + m.group(1) + text[m.end(2):]


def _reconcile_window_text(text, start, end):
    """Drop a time-of-day phrase from a window's text when it contradicts the
    window's actual clock times. Deterministic: the clock wins.

    Also strips a leading 'After ... around H:MM' clause whose stated hour does
    not match `start` — the LLM sometimes narrates a different pivot time than
    the window it labelled.
    """
    if not isinstance(text, str) or not text.strip():
        return text
    import re as _r
    sh = _hour24(start)
    if sh is None:
        return text

    low = text.lower()
    for word, (lo, hi) in _TOD_WORDS.items():
        if word not in low:
            continue
        # does `start` fall in this phrase's band? (night wraps past midnight)
        in_band = (lo <= sh < hi) or (hi > 24 and (sh >= lo or sh < hi - 24))
        if in_band:
            continue
        # contradiction — excise the "<word> hours"/"the <word>" phrase cleanly
        # subject position: "Morning hours carry/bring/offer ..." -> "This window
        # carries ...". Fix the verb agreement in the same pass.
        text = _r.sub(
            rf'^\s*(?:the\s+|early\s+|late\s+)?{word}\s+hours?\s+'
            rf'(carry|bring|offer|hold|favor|favour|suit|support)\b',
            lambda m: 'This window ' + {
                'carry':'carries','bring':'brings','offer':'offers','hold':'holds',
                'favor':'favors','favour':'favours','suit':'suits','support':'supports',
            }[m.group(1).lower()],
            text, flags=_r.IGNORECASE)
        text = _r.sub(rf'\b(?:the\s+|early\s+|late\s+)?{word}\s+hours?\b',
                      'this window', text, flags=_r.IGNORECASE)
        text = _r.sub(rf'\b(?:in|during)\s+the\s+{word}\b',
                      'in this window', text, flags=_r.IGNORECASE)
        text = _r.sub(rf'\bthe\s+{word}\b', 'this window', text, flags=_r.IGNORECASE)
        low = text.lower()

    # leading "After ... around 9:19 AM," pivot that disagrees with start
    m = _r.match(r'^\s*After[^,]*?\baround\s+(\d{1,2}(?::\d{2})?\s*[AaPp][Mm])\b[^,]*,\s*',
                 text)
    if m:
        pivot = _hour24(m.group(1))
        if pivot is not None and abs(pivot - sh) > 0.75:
            rest = text[m.end():]
            text = rest[:1].upper() + rest[1:] if rest else text
    text = _r.sub(r'\s{2,}', ' ', text).strip()
    return text
# ----------------------------------------------------------------------------

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

        for _f, _w in violations.get('invented_specifics', []) or []:
            corrective_parts.append(
                f"- You invented a proper noun in '{_f}': \"{_w}\". The chart "
                f"contains no such fact. Naming a place, person or organisation "
                f"the data does not contain is worse than being vague — the "
                f"reader recognises it as wrong and stops believing the rest. "
                f"Describe the KIND of person or situation "
                f"(\"someone you worked with years ago\"), never a named place."
            )

        for _f in violations.get('abstract_headline', []) or []:
            corrective_parts.append(
                f"- The headline field '{_f}' opened on an ABSTRACTION: "
                f"\"{str(failed_signal.get(_f, ''))[:110]}\""
            )
            corrective_parts.append(
                "  It must be THE CLAIM for the day: one sentence naming what is "
                "likely to happen and what to do about it, drawn from the "
                "strongest signal you were given. Two real users read a headline "
                "like this and said they did not "
                "understand what it meant. Do not name a quality of mind "
                "(intellect, intelligence, energy, clarity, potential, current). "
                "Open on something the reader could confirm happened by tonight: "
                "a conversation, a message, a decision, someone's reaction, money "
                "moving. "
                "BAD:  'Strong intellectual current today - communicate and wrap up.' "
                "GOOD: 'Words land well today. Have the conversation you have been "
                "putting off, before evening.' "
                "GOOD: 'Someone senior notices your work today. Say the one sentence "
                "that moves the deal.'"
            )

        for _f in violations.get('broken_sentences', []) or []:
            _bv = failed_signal.get(_f, '')
            if isinstance(_bv, list):
                _bv = next((x for x in _bv if isinstance(x, str)), '')
            corrective_parts.append(
                f"- The field '{_f}' was a BROKEN, incomplete sentence: "
                f"\"{str(_bv)[:110]}\". A word or clause is missing (e.g. 'offer "
                "it in the —' or 'the favorable your ...'). Every sentence must be "
                "complete and grammatical, with no dropped words, no dangling "
                "'the/in/for' before a dash, and no missing noun after an adjective."
            )

        for _f in violations.get('mechanics_jargon', []) or []:
            _mv = failed_signal.get(_f, '')
            if isinstance(_mv, list):
                _mv = next((x for x in _mv if isinstance(x, str)), '')
            corrective_parts.append(
                f"- The field '{_f}' explained the ASTROLOGY MECHANICS instead of "
                f"the reader's life: \"{str(_mv)[:110]}\". Never write 'transit', "
                "'aspect', 'planetary strength', 'energy transit', 'the income/gains/"
                "career zone', 'retrograde', or 'fast-moving planet'. Say only WHAT "
                "happens in their life and WHAT to do — never why in sky-terms. "
                "BAD:  'the strong planetary strength in the income zone is real but "
                "your growth-and-wisdom transit is blocked'. "
                "GOOD: 'money you're already owed can move today, but don't count on "
                "a windfall out of nowhere — chase what's pending.'"
            )

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
        try:
            from antar_engine.llm_log import wrap_claude_client as _wcc
            client = _wcc(client)
        except Exception:
            pass

        # Use full system prompt (no cache split for retry — it's rare)
        # --- Sprint EN-GLOSS-1: English Sanskrit-gloss block ---
        _daily_system_retry = DAILY_SYSTEM_PROMPT_V1
        if language == "en":
            from antar_engine.english_glossary import build_english_glossary_block
            _daily_system_retry = _daily_system_retry + "\n\n" + build_english_glossary_block("coach")
        # --- end Sprint EN-GLOSS-1 ---
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            temperature=0.2,  # Lower temp for correction
            system=_daily_system_retry,
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
    day_frame: Optional[dict] = None,
    provider_override: Optional[str] = None,
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
        try:
            from antar_engine.llm_log import wrap_claude_client as _wcc
            client = _wcc(client)
        except Exception:
            pass

        # Split system prompt at ## LIVE DATA for KV caching
        # --- Sprint EN-GLOSS-1: English Sanskrit-gloss block ---
        _daily_system = DAILY_SYSTEM_PROMPT_V1
        if language == "en":
            from antar_engine.english_glossary import build_english_glossary_block
            _daily_system = _daily_system + "\n\n" + build_english_glossary_block("coach")
            logger.info("[daily-llm] EN-GLOSS-1: English glossary block injected (voice=coach)")
        # --- end Sprint EN-GLOSS-1 ---
        _SPLIT = "## LIVE DATA"
        if _SPLIT in _daily_system:
            static_part, dynamic_part = _daily_system.split(_SPLIT, 1)
            dynamic_part = _SPLIT + dynamic_part
        else:
            static_part = _daily_system
            dynamic_part = ""

        system_blocks = [
            {
                "type": "text",
                "text": static_part,
                "cache_control": {"type": "ephemeral"}
            }
        ]
        # [frame-contract 2026-07-24] The day's binding orientation, identical to
        # the one today_narration receives — see antar_engine/day_frame.py. This
        # goes in the DYNAMIC block on purpose: it is per-chart and per-day, so
        # putting it above the ## LIVE DATA split would poison the KV cache that
        # every other chart shares. An open day contributes nothing.
        try:
            from antar_engine.day_frame import frame_constraint_block
            _fb = frame_constraint_block(day_frame)
            if _fb:
                dynamic_part = (dynamic_part + "\n\n" + _fb) if dynamic_part else _fb
        except Exception as _fe:
            logger.warning(f"[daily-llm] day frame not applied (non-fatal): {_fe}")

        if dynamic_part:
            system_blocks.append({"type": "text", "text": dynamic_part})

        # FIX 13: Bumped from 800 → 1500 to prevent JSON truncation
        # (daily signal JSON has 10+ fields including arrays — 800 tokens caused
        # "Unterminated string" parse errors in production logs)
        # [llm-adapter 2026-07-27] Non-Anthropic providers (panel-selected) route
        # through the adapter; the Anthropic branch below is unchanged, so the
        # default provider generates exactly as before.
        _raw_via_adapter = None
        try:
            from antar_engine import llm_adapter as _lad
            # [compare] an explicit override forces that provider (incl.
            # anthropic, via the adapter's KV-cache-preserving path).
            _prov, _mdl = _lad.resolve(None, provider=provider_override) if provider_override \
                else _lad.resolve(None)
            if provider_override or _prov != "anthropic":
                _raw_via_adapter = (await _lad.complete(
                    system=system_blocks,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=1500, temperature=0.3, provider=_prov, model=_mdl) or "").strip()
                logger.info(f"[daily-llm] generated via {_prov}/{_mdl}")
        except Exception as _lae:
            logger.warning(f"[daily-llm] adapter route failed, using Claude: {_lae}")
            _raw_via_adapter = None

        if _raw_via_adapter is not None:
            raw_text = _raw_via_adapter
        else:
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
            try:
                from antar_engine import llm_adapter as _ladu
                _ladu.accrue_usage(getattr(response.usage, 'input_tokens', 0),
                                   getattr(response.usage, 'output_tokens', 0), _cache_r)
            except Exception:
                pass

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


# [daily-cache-scrub 2026-06-09] Apply same strippers the live response
# path uses, so stale cache rows can't keep leaking '27 out of 56' /
# 'Budhaditya' / dropped-noun garble after a rule deploy.
def _dpc_scrub_signal(obj):
    try:
        from antar_engine.narration_polish import (
            strip_internal_metrics as _spim,
            strip_planet_traits as _sppt,
            ban_relative_time as _sbrt,
            has_clock_token as _shct,
        )
    except Exception:
        return obj

    def _walk(o):
        if isinstance(o, dict):
            return {k: _walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_walk(v) for v in o]
        if isinstance(o, str) and o:
            v = _spim(o)
            v = _sppt(v)
            v = _sbrt(v, has_hard_clock=_shct(v))
            return v
        return o
    try:
        return _walk(obj)
    except Exception:
        return obj


# [logic-version 2026-07-22] Bump when the generation logic changes in a way
# that should invalidate previously written cards: the prompt contract, the
# validators, or the strip pipeline.
#
# Without this, a fix ships and users keep reading pre-fix cards for a week. It
# happened exactly that way today: the claim-headline rule, the invented-place
# rejection and the plain-language tara mapping all shipped, and the cards for
# 23-27 July had been written on 20 July and were served unchanged. The user saw
# "Heavy structural pressure today" — a headline the new validator rejects —
# because nothing told the cache the rules had moved.
#
# v2: claim-first headline + event-verb requirement, invented proper-noun
#     rejection, day-name substitution, window overlap trimming, plain tara,
#     planet names preserved in the signals row.
DAILY_LOGIC_VERSION = 2


async def _get_cached_signal(chart_id: str, date_str: str, language: str, supabase_client) -> Optional[dict]:
    """Check Supabase daily_signals cache."""
    try:
        res = supabase_client.table("daily_signals_cache").select("signal_json").eq(
            "chart_id", chart_id
        ).eq("signal_date", date_str).eq("language", language).execute()
        if res.data:
            cached = res.data[0].get("signal_json")
            if cached:
                _payload = _safe_json(cached) if isinstance(cached, str) else cached
                # Written under older generation rules: discard rather than serve
                # a card the current validators would have rejected.
                if isinstance(_payload, dict):
                    _v = _payload.get("_logic_version")
                    if _v != DAILY_LOGIC_VERSION:
                        logger.info(
                            f"[daily-cache] {chart_id} {date_str}: stale logic "
                            f"v{_v} != v{DAILY_LOGIC_VERSION}, regenerating")
                        return None
                # [daily-cache-scrub 2026-06-09] scrub stale rows on hit
                return _dpc_scrub_signal(_payload)
    except Exception as e:
        logger.warning(f"[daily-cache] read failed (non-fatal): {e}")
    return None


async def _sf_wait_for_signal(chart_id, date_str, language, supabase_client,
                              timeout=75.0, interval=1.5):
    """Wait for a PEER's generation of this day to land in the cache, then return
    it — used when singleflight.try_acquire said someone else is already
    generating. Returns the cached signal dict, or None if it never arrives in
    `timeout`s (caller then generates itself — fail open).

    Timeout is deliberately GENEROUS. A cold single-day generation runs 30-50s
    (LLM + the validation-retry loop), so a short wait would time out and the
    loser would generate anyway — the worst outcome, since it waited AND paid.
    75s comfortably covers a worst-case winner; only a crashed winner makes a
    waiter hit the ceiling, and the lock's own TTL bounds that. When the winner
    succeeds the waiter returns the instant the cache appears, not at the ceiling."""
    import asyncio as _aio
    import time as _time
    deadline = _time.monotonic() + timeout
    while True:
        # Check first — the winner may already have written the cache.
        try:
            sig = await _get_cached_signal(chart_id, date_str, language, supabase_client)
        except Exception:
            sig = None
        if sig:
            return sig
        if _time.monotonic() >= deadline:
            return None
        await _aio.sleep(interval)


async def _save_cached_signal(chart_id: str, date_str: str, language: str, signal_json: dict, supabase_client):
    """Save to Supabase daily_signals_cache (upsert)."""
    try:
        # [daily-cache-scrub 2026-06-09] scrub before persisting
        signal_json = _dpc_scrub_signal(signal_json)
        if isinstance(signal_json, dict):
            signal_json["_logic_version"] = DAILY_LOGIC_VERSION
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

# [eph-memo 2026-06-16] Per-date global ephemeris memo. moon/mercury/tithi/
# panchang for a (date, tz) are identical across all charts, so computing
# them 7x per request per user is wasted CPU that blocks the async event
# loop and serializes concurrent requests. Cache per date so the work is
# reused. Cached values are READ-ONLY downstream, so sharing refs is safe.
# Process-local + deterministic (no cross-worker issue). Kill: DAILY_EPH_MEMO=off.
_EPH_DATE_CACHE = {}
_EPH_CACHE_MAX = 4000

def _eph_memo(kind, target_date, tz_offset, producer):
    if os.getenv("DAILY_EPH_MEMO", "on").strip().lower() in ("off", "0", "false", "no"):
        return producer()
    try:
        date_iso = target_date.strftime("%Y-%m-%d")
    except Exception:
        return producer()
    tz_key = round(float(tz_offset or 0.0), 2)
    k = (kind, date_iso, tz_key)
    if k in _EPH_DATE_CACHE:
        return _EPH_DATE_CACHE[k]
    v = producer()
    if len(_EPH_DATE_CACHE) > _EPH_CACHE_MAX:
        _EPH_DATE_CACHE.clear()
    _EPH_DATE_CACHE[k] = v
    return v


async def generate_weekly_signals(
    natal_moon_sign: str,
    start_date: Optional[datetime] = None,
    chart_id: Optional[str] = None,
    supabase_client=None,
    language: str = "en",
    tz_offset: float = 0,
    force_refresh: bool = False,
    fast_mode: bool = False,
    days_to_generate: int = 7,
    day_frame: Optional[dict] = None,
    provider_override: Optional[str] = None,
    persist: bool = True,
) -> list:
    """
    Generate 7-day daily signal array.

    [compare 2026-07-27] provider_override forces a specific LLM (anthropic/
    deepseek/kimi) for this run, ignoring config — used by the admin compare
    view. persist=False skips ALL cache read/write so a comparison never
    pollutes the real per-user cache.

    v2: If chart_id + supabase_client provided, uses Claude LLM for text
    generation with full chart context. Falls back to v1 templates if
    chart_id is None or LLM call fails.

    Args:
        natal_moon_sign: User's natal Moon sign (e.g., "Scorpio")
        start_date: First day of the 7-day window (defaults to today UTC)
        chart_id: Chart UUID for full context (NEW)
        supabase_client: Supabase client instance (NEW)
        language: "en" or "es" (NEW)
        tz_offset: Timezone offset in hours, supports half-hours e.g. 5.5 for India (NEW)

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

    # [es-latency] caller may request fewer than 7 days (daily-signal needs
    # only TODAY; the remaining days are warmed off the request path).
    for i in range(max(1, min(7, days_to_generate))):
        target_date = start_date + timedelta(days=i)
        weekday = target_date.strftime("%A")
        date_str = target_date.strftime("%Y-%m-%d")

        # Compute Moon data (KEPT)
        moon_data = _eph_memo("moon", target_date, tz_offset, lambda: get_moon_data_for_date(target_date, tz_offset=tz_offset))
        nakshatra = moon_data["nakshatra"]
        moon_sign = moon_data["sign"]

        # Compute Mercury sign (KEPT)
        mercury_sign = _eph_memo("merc", target_date, tz_offset, lambda: get_planet_sign_for_date(target_date, 2, tz_offset=tz_offset))

        # Compute tithi (KEPT)
        tithi = _eph_memo("tithi", target_date, tz_offset, lambda: get_tithi(target_date, tz_offset=tz_offset))

        # Compute chandra bala
        chandra_bala = get_chandra_bala(natal_moon_sign, moon_sign)

        # Score the day (KEPT)
        score, is_friction = _score_day(moon_sign, natal_moon_sign, nakshatra, weekday)

        # [daily-precision c1] chart-relative layer (tara + moon-house),
        # computed from daily_context (natal moon nakshatra + lagna). None
        # when there's no chart context. Score is NOT changed in c1.
        _precision = None
        try:
            if daily_context:
                from antar_engine.daily_precision import compute_daily_precision
                _precision = compute_daily_precision(
                    natal_moon_nak=daily_context.get("moon_nakshatra", ""),
                    natal_lagna_sign=daily_context.get("lagna_sign", ""),
                    today_moon_nak=nakshatra,
                    today_moon_sign=moon_sign,
                )
        except Exception as _prec_e:
            logger.warning(f"[daily-week] precision compute failed for {date_str}: {_prec_e}")
            _precision = None
        # [daily-precision] _precision ready
        # [daily-precision c2] fold tara + moon-house into the score
        # (kill switch DAILY_PRECISION_SCORE=off reverts to base score).
        if _precision and os.getenv("DAILY_PRECISION_SCORE", "on").strip().lower() \
                not in ("off", "0", "false", "no"):
            from antar_engine.daily_precision import apply_precision_to_score as _aps
            score, is_friction = _aps(score, _precision)

        # [signals 2026-07-20] Assemble the five inputs behind the verdict so the
        # card can SHOW its reasoning. The score was built from two of them
        # (tara + Moon house) and the card displayed neither — which is why the
        # read felt thinner than a competitor showing a fabricated percentage.
        # Lal Kitab and the running dasha were already in daily_context and had
        # never been consulted.
        _signals = None
        try:
            from antar_engine.daily_precision import build_day_signals as _bds
            _ctx0 = daily_context or {}
            _signals = _bds(
                _precision or {},
                dasha_md=_ctx0.get("md", ""), dasha_ad=_ctx0.get("ad", ""),
                dasha_pd=_ctx0.get("pd", ""),
                lk_sleeping=_ctx0.get("sleeping_planets", ""),
                moon_nakshatra=nakshatra,
                lit_domain=(_precision or {}).get("lit_domain", ""),
            )
        except Exception as _sig_e:
            logger.warning(f"[daily-week] signals failed for {date_str}: {_sig_e}")
            _signals = None

        # [moon-transit 2026-07-20] The Moon is sampled once at local noon, which
        # picks the WRONG governing nakshatra on ~12% of days — those where it
        # crosses in the early afternoon, leaving most remaining waking hours to
        # the incoming nakshatra. tara bala is derived from the nakshatra and can
        # invert across that boundary, so the whole reading flips. Prefer the
        # nakshatra covering most waking hours, and remember when it turns.
        _moon_shift = None
        try:
            from antar_engine.moon_transit import moon_day_profile as _mdp
            _prof = _mdp(target_date, tz_offset) or {}
            if _prof.get("nakshatra"):
                if _prof.get("differs_from_noon"):
                    logger.info(
                        f"[moon-transit] {date_str}: noon={_prof.get('noon_nakshatra')} "
                        f"-> governing={_prof['nakshatra']} (changes {_prof.get('changes_at')})")
                nakshatra = _prof["nakshatra"]
                _moon_shift = _prof
                # Before/after halves, so the card can show how the day turns
                # rather than averaging two different days into one verdict.
                # `material` is False when the character does not actually flip,
                # and the UI must render a single reading in that case.
                try:
                    from antar_engine.moon_transit import split_day as _split
                    _ctx = daily_context or {}
                    _sd = _split(_prof,
                                 _ctx.get("moon_nakshatra", ""),
                                 _ctx.get("lagna_sign", ""),
                                 target_date.weekday(),
                                 _ctx.get("chart_data"),
                                 moon_sign)
                    if _sd:
                        _moon_shift = {**_prof, "split": _sd}
                except Exception as _sd_e:
                    logger.warning(f"[daily-week] day split failed for {date_str}: {_sd_e}")
        except Exception as _mt_e:
            logger.warning(f"[daily-week] moon transit failed for {date_str}: {_mt_e}")

        # [color-therapy 2026-07-20] Which colour activates today's live energy.
        # Uses the nakshatra lord (the daily-moving signal) led by the vara lord
        # (the day's standing frame), and respects tara: on an adverse tara we
        # must NOT amplify the nakshatra lord — that pours energy into the graha
        # causing the trouble. Returns None when inputs are unusable; the caller
        # shows nothing rather than inventing a colour.
        _color = None
        _food = None
        try:
            from antar_engine.color_therapy import color_for_day as _cfd
            _color = _cfd(nakshatra,
                          target_date.weekday(),
                          (_precision or {}).get("tara_quality"),
                          chart_data=daily_context.get("chart_data") if daily_context else None,
                          # lagna makes the reason chart-specific: the same
                          # Saturn colour activates career for one user and
                          # money for another. Absent -> generic fallback.
                          lagna_sign=(daily_context or {}).get("lagna_sign"))
        except Exception as _col_e:
            logger.warning(f"[daily-week] colour compute failed for {date_str}: {_col_e}")
            _color = None
        # Food follows the SAME graha as the colour (shared resolve_day_graha),
        # so the day card reads as one instruction rather than two unrelated
        # recommendations. Adverse tara switches eat-list from strengthen to
        # balance for the same reason the colour falls back to the vara lord.
        try:
            from antar_engine.ayurveda_astrology import food_for_day as _ffd
            _food = _ffd(nakshatra,
                         target_date.weekday(),
                         (_precision or {}).get("tara_quality"),
                         # Duration scales with WHY the graha matters: a passing
                         # transit is a 40-day mandala, the running dasha lord
                         # is a commitment for the period.
                         dasha_md=(daily_context or {}).get("md"),
                         dasha_ad=(daily_context or {}).get("ad")) or None
        except Exception as _food_e:
            logger.warning(f"[daily-week] food compute failed for {date_str}: {_food_e}")
            _food = None

        # Compute panchang quality for this day
        try:
            panchang = _eph_memo("panchang", target_date, 0.0, lambda: calculate_panchang(target_date, 0.0, 0.0))
            panchang_quality = panchang.get("panchang_quality", "mixed")
        except Exception:
            panchang_quality = "mixed"

        # ── LLM path ──
        llm_signal = None
        if use_llm:
            # FIX 14: force_refresh — delete stale cache + skip read
            # [compare] persist=False never touches the cache (no delete either).
            if force_refresh and supabase_client and persist:
                try:
                    supabase_client.table("daily_signals_cache").delete().eq(
                        "chart_id", chart_id
                    ).eq("signal_date", date_str).eq("language", language).execute()
                    logger.info(f"[daily-week] force_refresh: deleted cache for {chart_id}/{date_str}/{language}")
                except Exception as _fr_e:
                    logger.warning(f"[daily-week] force_refresh delete failed (non-fatal): {_fr_e}")

            # Check cache first (skipped when force_refresh or not persisting)
            if supabase_client and not force_refresh and persist:
                llm_signal = await _get_cached_signal(chart_id, date_str, language, supabase_client)
                if llm_signal:
                    logger.info(f"[daily-week] Cache HIT for {chart_id}/{date_str}/{language}")
                    # [why-block-leak-fix] rows cached BEFORE the el_movimiento
                    # strip-exemption was removed still carry raw jargon —
                    # re-strip on read. All strippers are idempotent.
                    llm_signal = _strip_day_names_from_signal(llm_signal, language)
                    llm_signal = _tidy_signal(_strip_all_jargon_from_signal(llm_signal, language), language)

            # [async-fast] fast_mode: never call Claude inline on a cache
            # miss — fall through to the v1 template branch (differentiated
            # per day) and let the route's background full pass fill the cache.
            if not llm_signal and fast_mode:
                logger.info(f"[daily-week] fast_mode: deferring LLM generation for {date_str}")

            # [singleflight 2026-07-25] Coalesce concurrent generations of THIS
            # (chart, date, language) across all workers. On a login burst the
            # same day is requested many times at once; without this each request
            # generates it independently. If a peer already holds the lock, wait
            # for its cache write instead of generating a duplicate; only fall
            # through to our own generation if that wait times out (fail open).
            # Sets _sf_owned so the lock is released after the cache write below.
            # [compare-fix] singleflight is for deduping concurrent REAL user
            # requests; skip it when persist=False (admin compare runs every
            # provider in parallel on the same chart/date/lang and must NOT
            # coordinate — each provider generates independently).
            _sf_owned = False
            if not llm_signal and not fast_mode and chart_id and supabase_client and persist:
                try:
                    from antar_engine import singleflight as _sf
                    if _sf.try_acquire(supabase_client, chart_id, date_str, language):
                        _sf_owned = True
                    else:
                        _peer = await _sf_wait_for_signal(
                            chart_id, date_str, language, supabase_client)
                        if _peer:
                            _peer = _strip_day_names_from_signal(_peer, language)
                            llm_signal = _tidy_signal(
                                _strip_all_jargon_from_signal(_peer, language), language)
                            logger.info(f"[singleflight] {date_str} served from peer generation")
                except Exception as _sfe:
                    logger.warning(f"[singleflight] guard skipped (non-fatal): {_sfe}")

            if not llm_signal and not fast_mode:
                # Build day-specific data for prompt
                day_prompt_data = {
                    "iso_date": date_str,
                    "weekday": weekday,
                    "tz_display": f"{tz_offset:+.1f}".rstrip("0").rstrip(".") if tz_offset else "+0",
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
                        tz_offset=tz_offset,
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

                # ── LK Daily Diagnostic — personalized weekday × chart ──
                try:
                    from antar_engine.lal_kitab_advanced import compute_lk_daily_diagnostic
                    _lk_raw = daily_context.get("lk_data", {})
                    _chart_raw = daily_context.get("chart_data", {})
                    lk_daily = compute_lk_daily_diagnostic(
                        lk_data=_lk_raw,
                        chart_data=_chart_raw,
                        target_date=target_date,
                        language=language,
                    )
                    if lk_daily.get("available"):
                        _status = lk_daily.get("day_lord_status", {})
                        _lang_key = "summary_es" if language == "es" else "summary_en"
                        _hint_key = "user_facing_hint_es" if language == "es" else "user_facing_hint_en"
                        lk_block_lines = [
                            "## DAY-LORD DIAGNOSTIC (Lal Kitab)",
                            f"Day-lord planet: {lk_daily['day_lord']}",
                            f"Condition for this user: {_status.get(_lang_key, '')}",
                            f"Day quality for user: {lk_daily.get('day_quality_for_user', 'neutral')}",
                            f"Domains amplified: {', '.join(lk_daily.get('domains_amplified_today', []))}",
                            f"Domains to avoid: {', '.join(lk_daily.get('domains_to_avoid_today', []))}",
                            f"Diagnostic hint: {lk_daily.get(_hint_key, '')}",
                            f"Evidence: {lk_daily.get('evidence_for_movement', '')}",
                            "",
                            "Use this in:",
                            "- haz_hoy: prefer actions in amplified domains",
                            "- evita_hoy: caution in avoided domains",
                            "- el_movimiento: include LK evidence as one strategic reason",
                            "- senal_de_hoy: tone reflects day_quality_for_user",
                            "DO NOT use 'Lal Kitab', 'day-lord', or weekday names in user-facing fields.",
                            "el_movimiento is USER-FACING: plain energy language only — no planet names, no codenames, no Sanskrit. Refer to the day's ruler as \"today's natural ruling energy\".",
                        ]
                        day_prompt_data["lk_daily_block"] = "\n".join(lk_block_lines)
                    else:
                        day_prompt_data["lk_daily_block"] = ""
                except Exception as lk_err:
                    logger.warning(f"[daily-week] LK daily diagnostic failed for {date_str}: {lk_err}")
                    day_prompt_data["lk_daily_block"] = ""

                llm_signal = await _call_claude_daily_signal(
                    context=daily_context,
                    day_data=day_prompt_data,
                    language=language,
                    day_frame=day_frame,
                    provider_override=provider_override,
                )

                # ── FIX D: Validate + corrective retry ──
                if llm_signal:
                    day_violations = _validate_no_day_names(llm_signal, language)
                    eng_leaks = _detect_english_leak(llm_signal, language)
                    abstract = _validate_headline_concrete(llm_signal, language)
                    invented = _validate_no_invented_specifics(
                        llm_signal, (daily_context or {}).get("chart_row") or {})
                    # [completeness 2026-07-27] truncated/broken sentences are
                    # unrecoverable — regenerate rather than ship "offer it in the —".
                    broken = _broken_fields(llm_signal)
                    # [mechanics-jargon 2026-07-27] astro mechanics verbalized as
                    # prose ("energy transit is blocked", "aspect from a planet").
                    mechanics = _mechanics_fields(llm_signal)

                    # [cold-fix] eng-leak is non-load-bearing: it no longer
                    # triggers the corrective retry (a 2nd es Sonnet). The
                    # jargon strip below still cleans any leak.
                    if day_violations or abstract or invented or broken or mechanics:
                        logger.warning(f"[daily-week] Validation failed for {date_str}: "
                                       f"day_names={day_violations} eng_leaks={eng_leaks} "
                                       f"abstract_headline={abstract} broken={broken} "
                                       f"mechanics={mechanics}")

                        # Build corrective retry prompt with specific violations
                        retry_signal = await _call_claude_daily_signal_retry(
                            context=daily_context,
                            day_data=day_prompt_data,
                            language=language,
                            violations={'day_names': day_violations, 'eng_leaks': eng_leaks,
                                        'abstract_headline': abstract,
                                        'invented_specifics': invented,
                                        'broken_sentences': broken,
                                        'mechanics_jargon': mechanics},
                            failed_signal=llm_signal,
                        )
                        if retry_signal:
                            retry_day = _validate_no_day_names(retry_signal, language)
                            retry_eng = _detect_english_leak(retry_signal, language)
                            if not retry_day and not retry_eng:
                                # [3.7c] strip even on retry-success — the day-name/eng
                                # validators only check two leak classes; Vedic jargon,
                                # Spanish planet names, and X/56 scores still need scrubbing.
                                retry_signal = _strip_day_names_from_signal(retry_signal, language)
                                retry_signal = _tidy_signal(_strip_all_jargon_from_signal(retry_signal, language), language)
                                llm_signal = retry_signal
                                logger.info(f"[daily-week] Retry succeeded for {date_str}")
                            else:
                                # Strip what we can, accept with warnings
                                retry_signal = _strip_day_names_from_signal(retry_signal, language)
                                retry_signal = _tidy_signal(_strip_all_jargon_from_signal(retry_signal, language), language)
                                retry_signal['_validation_warnings'] = {
                                    'day_names': retry_day, 'english_leaks': retry_eng
                                }
                                llm_signal = retry_signal
                                logger.warning(f"[daily-week] Retry still has issues for {date_str}, accepting with warnings")
                        else:
                            # Retry failed entirely — strip first attempt
                            llm_signal = _strip_day_names_from_signal(llm_signal, language)
                            llm_signal = _tidy_signal(_strip_all_jargon_from_signal(llm_signal, language), language)
                            llm_signal['_validation_warnings'] = {
                                'day_names': day_violations, 'english_leaks': eng_leaks
                            }
                    else:
                        # First pass clean — still strip as safety net
                        llm_signal = _strip_day_names_from_signal(llm_signal, language)
                        llm_signal = _tidy_signal(_strip_all_jargon_from_signal(llm_signal, language), language)


                # Cache if successful (never when persist=False — compare runs)
                if llm_signal and supabase_client and persist:
                    await _save_cached_signal(chart_id, date_str, language, llm_signal, supabase_client)
                    logger.info(f"[daily-week] Cached LLM signal for {chart_id}/{date_str}/{language}")

            # [singleflight 2026-07-25] Release our generation lock now the cache
            # is written (or generation is done), so peers waiting on it can read
            # the result. Guarded by _sf_owned so a peer/wait path never releases
            # a lock it does not hold. Held only if we acquired above.
            if locals().get("_sf_owned"):
                try:
                    from antar_engine import singleflight as _sf
                    _sf.release(supabase_client, chart_id, date_str, language)
                except Exception:
                    pass

        # ── Build result ──
        if llm_signal:
            # LLM-generated signal — merge with computed data
            day_result = {
                "date": date_str,
                "day": weekday,
                "moon_nakshatra": nakshatra,
                "color": _color,
                "food": _food,
                "signals": _signals,
                "moon_shift": _moon_shift,
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
                "color": _color,
                "food": _food,
                "signals": _signals,
                "moon_shift": _moon_shift,
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
            # [daily-precision c2] vary the frozen fallback wow from the
            # day's strongest chart-relative signal (jargon-free).
            if _precision:
                try:
                    from antar_engine.daily_precision import strongest_signal_phrase as _ssp
                    _wow2 = _ssp(_precision)
                    if _wow2:
                        day_result["wow"] = _wow2
                except Exception:
                    pass
            # [async-fast] mark fast-path days so the route schedules a
            # background full pass and the frontend can poll for the upgrade.
            if fast_mode:
                day_result["pending"] = True

        # [daily-precision c1] surface chart-relative fields (additive).
        if _precision:
            try:
                from antar_engine.daily_precision import precision_fields
                day_result.update(precision_fields(_precision))
            except Exception:
                pass
        results.append(day_result)
        logger.info(f"[daily-week] {date_str} {weekday}: {nakshatra} in {moon_sign} | score={score} | llm={'yes' if llm_signal else 'no'}")

    return results


# ──────────────────────────────────────────────
# Sync wrapper for non-async callers (hora endpoints, feedback)
# ──────────────────────────────────────────────

def generate_weekly_signals_sync(
    natal_moon_sign: str,
    start_date: Optional[datetime] = None,
    tz_offset: float = 0,
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

        moon_data = _eph_memo("moon", target_date, tz_offset, lambda: get_moon_data_for_date(target_date, tz_offset=tz_offset))
        nakshatra = moon_data["nakshatra"]
        moon_sign = moon_data["sign"]
        mercury_sign = _eph_memo("merc", target_date, tz_offset, lambda: get_planet_sign_for_date(target_date, 2, tz_offset=tz_offset))
        tithi = _eph_memo("tithi", target_date, tz_offset, lambda: get_tithi(target_date, tz_offset=tz_offset))
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
            "color": _color,
            "food": _food,
            "signals": _signals,
            "moon_shift": _moon_shift,
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
