"""
antar_engine/hora_engine.py
Kala Hora — Planetary Hour Timing Engine

Computes current + upcoming planetary hours for a location.
Maps each hora ruler to FIELD×MODE action guidance.

Chaldean sequence (correct order):
  Saturn → Jupiter → Mars → Sun → Venus → Mercury → Moon → (repeat)

Day lord starts first hora:
  Sunday=Sun, Monday=Moon, Tuesday=Mars, Wednesday=Mercury,
  Thursday=Jupiter, Friday=Venus, Saturday=Saturn

Hora span:
  Day horas  = (sunset - sunrise) / 12
  Night horas = (next_sunrise - sunset) / 12

Usage:
    from antar_engine.hora_engine import get_hora_schedule
    result = get_hora_schedule(lat, lng, tz_offset=−5, n_horas=8)
"""

from datetime import datetime, timedelta, timezone as tz
from typing import List, Dict, Optional
import math
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# CHALDEAN SEQUENCE (correct — Saturn first)
# ═══════════════════════════════════════════════════════════════════

CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

# First hora of the day by weekday
# Python weekday(): 0=Monday … 6=Sunday
DAY_LORD = {
    6: "Sun",      # Sunday
    0: "Moon",     # Monday
    1: "Mars",     # Tuesday
    2: "Mercury",  # Wednesday
    3: "Jupiter",  # Thursday
    4: "Venus",    # Friday
    5: "Saturn",   # Saturday
}

# ═══════════════════════════════════════════════════════════════════
# HORA → FIELD × ACTION WINDOW
# ═══════════════════════════════════════════════════════════════════

HORA_GUIDANCE = {
    "Sun": {
        "window":      "AUTHORITY WINDOW",
        "field":       "COMMAND",
        "mode":        "DRIVE",
        "action":      "High-status meetings, leadership decisions, visibility moves",
        "go_dark":     False,
        "emoji":       "☀️",
        "color":       "#F59E0B",  # amber
    },
    "Venus": {
        "window":      "MAGNETISM WINDOW",
        "field":       "ALLIANCE",
        "mode":        "BALANCE",
        "action":      "Relationship building, design, negotiation, creative work",
        "go_dark":     False,
        "emoji":       "✦",
        "color":       "#EC4899",  # pink
    },
    "Mercury": {
        "window":      "CONNECT WINDOW",
        "field":       "ALLIANCE",
        "mode":        "CONNECT",
        "action":      "Emails, pitches, calls, rapid communication, coding",
        "go_dark":     False,
        "emoji":       "⚡",
        "color":       "#00BFA5",  # teal
    },
    "Moon": {
        "window":      "REFLECT WINDOW",
        "field":       "NURTURE",
        "mode":        "BALANCE",
        "action":      "Intuition, planning, emotional check-ins, research",
        "go_dark":     False,
        "emoji":       "◐",
        "color":       "#8B5CF6",  # purple
    },
    "Saturn": {
        "window":      "STRUCTURE WINDOW",
        "field":       "DEPTH",
        "mode":        "PENETRATE",
        "action":      "Deep work, auditing, admin, long-form writing, systems",
        "go_dark":     False,
        "emoji":       "⬡",
        "color":       "#64748B",  # slate
    },
    "Jupiter": {
        "window":      "EXPANSION WINDOW",
        "field":       "EXPANSION",
        "mode":        "EXPAND",
        "action":      "Strategy, big-picture planning, mentorship, learning",
        "go_dark":     False,
        "emoji":       "⬆",
        "color":       "#3B82F6",  # blue
    },
    "Mars": {
        "window":      "DRIVE WINDOW",
        "field":       "COMMAND",
        "mode":        "DRIVE",
        "action":      "High-intensity execution, gym, confrontations, cold calls",
        "go_dark":     False,
        "emoji":       "▲",
        "color":       "#EF4444",  # red
    },
}

# ═══════════════════════════════════════════════════════════════════
# WOW CONVERGENCE — when daily mode matches hora field
# ═══════════════════════════════════════════════════════════════════

# Maps daily FIELD → best matching hora planet(s)
FIELD_HORA_MATCH = {
    "COMMAND":   ["Sun", "Mars"],
    "ALLIANCE":  ["Mercury", "Venus"],
    "SPARK":     ["Mars", "Sun"],
    "DEPTH":     ["Saturn", "Moon"],
    "NURTURE":   ["Moon", "Venus"],
    "EXPANSION": ["Jupiter"],
}

# ═══════════════════════════════════════════════════════════════════
# SUNRISE / SUNSET via Swiss Ephemeris
# ═══════════════════════════════════════════════════════════════════

def _get_sunrise_sunset(lat: float, lng: float, date: datetime) -> tuple:
    """
    Returns (sunrise_utc, sunset_utc) as datetime objects for the given date and location.
    Uses Swiss Ephemeris for precision.
    """
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        jd_noon = swe.julday(date.year, date.month, date.day, 12.0)

        # Rise/set flags
        RISE_FLAG  = swe.CALC_RISE
        SET_FLAG   = swe.CALC_SET
        GEO_FLAG   = swe.BIT_DISC_CENTER

        # Sunrise
        rise_result = swe.rise_trans(
            jd_noon - 0.5,
            swe.SUN,
            RISE_FLAG | GEO_FLAG,
            [lng, lat, 0],
            0.0, 0.0,
            swe.FLG_SWIEPH,
        )
        # Sunset
        set_result = swe.rise_trans(
            jd_noon - 0.5,
            swe.SUN,
            SET_FLAG | GEO_FLAG,
            [lng, lat, 0],
            0.0, 0.0,
            swe.FLG_SWIEPH,
        )

        def jd_to_utc(jd):
            y, m, d, h = swe.revjul(jd)
            hour = int(h)
            minute = int((h - hour) * 60)
            second = int(((h - hour) * 60 - minute) * 60)
            return datetime(y, m, d, hour, minute, second, tzinfo=tz.utc)

        sunrise = jd_to_utc(rise_result[1][0])
        sunset  = jd_to_utc(set_result[1][0])
        return sunrise, sunset

    except Exception as e:
        logger.warning(f"[hora] Sunrise calc failed: {e} — using defaults")
        # Fallback: approximate 6am/6pm
        base = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz.utc)
        return base + timedelta(hours=6), base + timedelta(hours=18)


def _get_next_sunrise(lat: float, lng: float, date: datetime) -> datetime:
    """Get sunrise for the next day."""
    next_day = date + timedelta(days=1)
    sunrise, _ = _get_sunrise_sunset(lat, lng, next_day)
    return sunrise


# ═══════════════════════════════════════════════════════════════════
# HORA INDEX COMPUTATION
# ═══════════════════════════════════════════════════════════════════

def _get_hora_start_index(weekday_lord: str) -> int:
    """Get starting index in CHALDEAN sequence for given day lord."""
    return CHALDEAN.index(weekday_lord)


def _build_hora_grid(
    sunrise: datetime,
    sunset: datetime,
    next_sunrise: datetime,
    start_index: int,
) -> List[Dict]:
    """
    Build full 24-hora grid for one day.
    Returns list of hora dicts with start_time, end_time, ruler, guidance.
    """
    day_span   = (sunset - sunrise).total_seconds()
    night_span = (next_sunrise - sunset).total_seconds()

    day_hora_secs   = day_span / 12
    night_hora_secs = night_span / 12

    horas = []
    idx = start_index

    # 12 day horas
    for i in range(12):
        start = sunrise + timedelta(seconds=i * day_hora_secs)
        end   = sunrise + timedelta(seconds=(i + 1) * day_hora_secs)
        ruler = CHALDEAN[idx % 7]
        horas.append(_make_hora(start, end, ruler, is_day=True))
        idx += 1

    # 12 night horas
    for i in range(12):
        start = sunset + timedelta(seconds=i * night_hora_secs)
        end   = sunset + timedelta(seconds=(i + 1) * night_hora_secs)
        ruler = CHALDEAN[idx % 7]
        horas.append(_make_hora(start, end, ruler, is_day=False))
        idx += 1

    return horas


def _make_hora(start: datetime, end: datetime, ruler: str, is_day: bool) -> Dict:
    """Build a single hora dict."""
    guidance = HORA_GUIDANCE.get(ruler, {})
    duration_mins = int((end - start).total_seconds() / 60)
    return {
        "ruler":          ruler,
        "start_utc":      start.isoformat(),
        "end_utc":        end.isoformat(),
        "duration_mins":  duration_mins,
        "is_day":         is_day,
        "window":         guidance.get("window", f"{ruler.upper()} WINDOW"),
        "field":          guidance.get("field", ""),
        "mode":           guidance.get("mode", ""),
        "action":         guidance.get("action", ""),
        "go_dark":        guidance.get("go_dark", False),
        "emoji":          guidance.get("emoji", ""),
        "color":          guidance.get("color", "#64748B"),
    }


# ═══════════════════════════════════════════════════════════════════
# WOW CONVERGENCE CHECK
# ═══════════════════════════════════════════════════════════════════

def _check_wow_convergence(
    hora_ruler: str,
    daily_field: str,
    is_friction_day: bool,
) -> Dict:
    """
    Check if current hora amplifies or conflicts with daily FIELD.
    Returns convergence dict.
    """
    matching_horas = FIELD_HORA_MATCH.get(daily_field, [])
    is_peak = hora_ruler in matching_horas

    if is_friction_day and is_peak:
        return {
            "type":    "AMPLIFIED_FRICTION",
            "label":   "⚠ DOUBLE FRICTION",
            "message": f"Your {daily_field} field meets {hora_ruler} hora on a friction day. High risk of conflict. Go dark until next hora.",
        }
    elif is_peak and not is_friction_day:
        return {
            "type":    "PEAK_SIGNAL",
            "label":   "◆ PEAK WINDOW",
            "message": f"Your {daily_field} field is amplified by {hora_ruler} hora. Act now — this window closes in {{duration}} minutes.",
        }
    elif is_friction_day:
        return {
            "type":    "FRICTION",
            "label":   "↓ FRICTION ACTIVE",
            "message": f"Friction day. Low-stakes tasks only. Wait for {matching_horas[0] if matching_horas else 'Jupiter'} hora.",
        }
    else:
        return {
            "type":    "NORMAL",
            "label":   "",
            "message": "",
        }


# ═══════════════════════════════════════════════════════════════════
# MAIN PUBLIC FUNCTION
# ═══════════════════════════════════════════════════════════════════

def get_hora_schedule(
    lat: float,
    lng: float,
    tz_offset: int = 0,
    n_horas: int = 8,
    daily_field: Optional[str] = None,
    is_friction_day: bool = False,
    target_dt: Optional[datetime] = None,
) -> Dict:
    """
    Compute current and upcoming horas for a location.

    Args:
        lat, lng:        Geographic coordinates
        tz_offset:       UTC offset in hours (e.g. -5 for Colombia)
        n_horas:         Number of upcoming horas to return (default 8)
        daily_field:     User's dominant FIELD from character_archetype (for WOW check)
        is_friction_day: From daily signal engine
        target_dt:       Override current time (for testing)

    Returns:
        {
            "current_hora": {...},
            "upcoming_horas": [...],
            "wow_convergence": {...},
            "sunrise_local": "06:14",
            "sunset_local": "18:22",
        }
    """
    now_utc = target_dt or datetime.now(tz.utc)
    local_dt = now_utc + timedelta(hours=tz_offset)
    today = local_dt.date()

    # Get sunrise/sunset for today
    today_dt = datetime(today.year, today.month, today.day, 12, 0, tzinfo=tz.utc)
    sunrise, sunset = _get_sunrise_sunset(lat, lng, today_dt)
    next_sunrise = _get_next_sunrise(lat, lng, today_dt)

    # Determine weekday lord (use local date)
    weekday = local_dt.weekday()  # 0=Monday
    day_lord = DAY_LORD[weekday]
    start_idx = _get_hora_start_index(day_lord)

    # Build full 24-hora grid
    horas = _build_hora_grid(sunrise, sunset, next_sunrise, start_idx)

    # Find current hora
    current_hora = None
    current_idx = 0
    for i, h in enumerate(horas):
        h_start = datetime.fromisoformat(h["start_utc"])
        h_end   = datetime.fromisoformat(h["end_utc"])
        if h_start <= now_utc < h_end:
            current_hora = h
            current_idx = i
            # Add time remaining
            mins_remaining = int((h_end - now_utc).total_seconds() / 60)
            current_hora = {**h, "mins_remaining": mins_remaining}
            break

    # Upcoming horas (after current)
    upcoming = []
    if current_idx is not None:
        for h in horas[current_idx + 1:current_idx + 1 + n_horas]:
            upcoming.append(h)

    # If we need more (wrap to next day), add from tomorrow
    if len(upcoming) < n_horas:
        tomorrow_dt = today_dt + timedelta(days=1)
        t_sunrise, t_sunset = _get_sunrise_sunset(lat, lng, tomorrow_dt)
        t_next_sunrise = _get_next_sunrise(lat, lng, tomorrow_dt)
        t_weekday = (weekday + 1) % 7
        t_lord = DAY_LORD[t_weekday]
        t_start_idx = _get_hora_start_index(t_lord)
        tomorrow_horas = _build_hora_grid(t_sunrise, t_sunset, t_next_sunrise, t_start_idx)
        needed = n_horas - len(upcoming)
        upcoming.extend(tomorrow_horas[:needed])

    # WOW convergence
    wow = {}
    if current_hora and daily_field:
        wow = _check_wow_convergence(
            current_hora["ruler"],
            daily_field,
            is_friction_day,
        )
        if wow.get("message") and current_hora.get("mins_remaining"):
            wow["message"] = wow["message"].replace(
                "{duration}", str(current_hora["mins_remaining"])
            )

    # Format local times for display
    def utc_to_local_str(iso_str):
        dt = datetime.fromisoformat(iso_str)
        local = dt + timedelta(hours=tz_offset)
        return local.strftime("%I:%M %p").lstrip("0")

    sunrise_local = (sunrise + timedelta(hours=tz_offset)).strftime("%I:%M %p").lstrip("0")
    sunset_local  = (sunset  + timedelta(hours=tz_offset)).strftime("%I:%M %p").lstrip("0")

    # Add local time display to each hora
    if current_hora:
        current_hora["start_local"] = utc_to_local_str(current_hora["start_utc"])
        current_hora["end_local"]   = utc_to_local_str(current_hora["end_utc"])

    for h in upcoming:
        h["start_local"] = utc_to_local_str(h["start_utc"])
        h["end_local"]   = utc_to_local_str(h["end_utc"])

    return {
        "current_hora":   current_hora,
        "upcoming_horas": upcoming,
        "wow_convergence": wow,
        "day_lord":       day_lord,
        "sunrise_local":  sunrise_local,
        "sunset_local":   sunset_local,
        "tz_offset":      tz_offset,
        "computed_at":    now_utc.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
# FRICTION WARNING BUILDER
# ═══════════════════════════════════════════════════════════════════

def get_next_power_hora(
    upcoming_horas: List[Dict],
    daily_field: str,
) -> Optional[Dict]:
    """
    From upcoming horas, find the next one that matches the user's daily FIELD.
    Used for friction day warning: "Wait until Jupiter hora at 2:00 PM."
    """
    matching = FIELD_HORA_MATCH.get(daily_field, [])
    for h in upcoming_horas:
        if h["ruler"] in matching:
            return h
    return None
