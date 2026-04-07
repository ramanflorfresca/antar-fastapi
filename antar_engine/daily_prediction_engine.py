"""
daily_prediction_engine.py — 7-Day Daily Signal Generator
Antar Intelligence Platform

Generates per-day Moon + Mercury signals for a 7-day window.
Personalized via user's natal Moon sign.

Data used (ONLY):
  - Moon nakshatra, sign, degree for each target date
  - Mercury sign for each target date
  - User natal Moon sign (from chart)
  - Weekday + tithi

Data NOT used:
  - House positions
  - Dasha periods
  - Divisional charts
  - Aspects / conjunctions

Called by: GET /api/v1/daily-week/{chart_id}
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constants
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

# Moon-sign friction map: certain transit signs create friction with certain natal signs
# Key = natal moon sign, Value = transit signs that create friction
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

# Weekday energy overlays
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
# Core Ephemeris Functions
# ──────────────────────────────────────────────

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
    """
    Returns Moon nakshatra, sign, and degree for a given date.
    Computed at noon UTC for that date.
    """
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
# Signal Builder
# ──────────────────────────────────────────────

def _score_day(moon_sign: str, natal_moon_sign: str, nakshatra: str, weekday: str) -> tuple:
    """
    Returns (score: int, is_friction: bool)
    score 0–10, higher = more aligned
    """
    score = 5  # neutral baseline

    # Nakshatra alignment: high-energy nakshatras boost score
    high_energy = {"Rohini", "Pushya", "Uttara Phalguni", "Uttara Ashadha",
                   "Chitra", "Dhanishta", "Magha", "Punarvasu"}
    friction_nakshatras = {"Ardra", "Ashlesha", "Jyeshtha", "Mula",
                           "Purva Bhadrapada", "Bharani"}
    if nakshatra in high_energy:
        score += 2
    elif nakshatra in friction_nakshatras:
        score -= 2

    # Moon transit vs natal moon friction
    friction_signs = MOON_FRICTION_MAP.get(natal_moon_sign, [])
    if moon_sign in friction_signs:
        score -= 2
    elif moon_sign == natal_moon_sign:
        score += 1  # Moon returns to natal sign — emotional clarity

    # Weekday boosts
    power_days = {"Thursday", "Sunday"}
    if weekday in power_days:
        score += 1

    score = max(0, min(10, score))
    is_friction = score < 4

    return score, is_friction


def _build_signal_text(
    nakshatra: str,
    moon_sign: str,
    mercury_sign: str,
    natal_moon_sign: str,
    weekday: str,
    score: int,
    is_friction: bool
) -> dict:
    """Build the signal, aligned_for, friction_for, move, and wow fields."""

    profile = NAKSHATRA_PROFILES.get(nakshatra, {
        "energy": "variable", "aligned": ["flexible work"], "friction": ["rigid planning"]
    })
    day_overlay = WEEKDAY_OVERLAY.get(weekday, {})
    friction_signs = MOON_FRICTION_MAP.get(natal_moon_sign, [])

    aligned = profile.get("aligned", [])[:3]
    friction = profile.get("friction", [])[:2]

    # Mercury modifier: if Mercury is in a communication-friendly sign, boost that
    mercury_comm_signs = {"Gemini", "Virgo", "Aquarius", "Libra"}
    mercury_note = None
    if mercury_sign in mercury_comm_signs:
        mercury_note = "Communication and negotiation carry extra weight today."

    # Build 2-sentence signal
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

    # WOW: special alignment notes
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
# Main 7-Day Generator
# ──────────────────────────────────────────────

def generate_weekly_signals(natal_moon_sign: str, start_date: Optional[datetime] = None) -> list:
    """
    Generate 7-day daily signal array.

    Args:
        natal_moon_sign: User's natal Moon sign (e.g., "Scorpio")
        start_date: First day of the 7-day window (defaults to today UTC)

    Returns:
        List of 7 daily signal dicts
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    results = []

    try:
        import swisseph as swe
        MERCURY = swe.MERCURY
    except ImportError:
        logger.error("swisseph not available")
        MERCURY = 2  # fallback constant

    for i in range(7):
        target_date = start_date + timedelta(days=i)
        weekday = target_date.strftime("%A")
        date_str = target_date.strftime("%Y-%m-%d")

        # Compute Moon data
        moon_data = get_moon_data_for_date(target_date)
        nakshatra = moon_data["nakshatra"]
        moon_sign = moon_data["sign"]

        # Compute Mercury sign
        mercury_sign = get_planet_sign_for_date(target_date, 2)  # swe.MERCURY = 2

        # Compute tithi
        tithi = get_tithi(target_date)

        # Score the day
        score, is_friction = _score_day(moon_sign, natal_moon_sign, nakshatra, weekday)

        # Build signal
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
        }

        results.append(day_result)
        logger.info(f"[daily-week] {date_str} {weekday}: {nakshatra} in {moon_sign} | score={score}")

    return results


# ──────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import json
    signals = generate_weekly_signals(natal_moon_sign="Scorpio")
    print(json.dumps(signals, indent=2))
