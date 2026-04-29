"""
antar_engine/muhurta_engine.py
===============================
Phase 3 — Compute classical muhurta timing windows for a day.

Includes:
  - Abhijit muhurta (universally auspicious ~noon window)
  - Rahu Kalam (inauspicious, weekday-dependent)
  - Gulika Kala (inauspicious, weekday-dependent)
  - Yamagandam (inauspicious, weekday-dependent)
  - Varjyam (inauspicious ~48min window per nakshatra)
  - Moon nakshatra transitions (when Moon shifts nakshatra)
  - Kala Hora sequence (planetary hour rulers)

All times returned as ISO strings (UTC) plus local approximations.
Sunrise/sunset via Swiss Ephemeris.

Called by: daily_transit_analyzer.py (Phase 3 integration)
"""
import logging
import math
from datetime import datetime, timedelta, timezone as tz
from typing import Dict, List, Optional, Tuple

import swisseph as swe

logger = logging.getLogger("antar_engine.muhurta_engine")

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Nakshatra span in degrees
NAKSHATRA_SPAN = 360.0 / 27.0  # 13°20' = 13.3333...°

SWE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

# ── Rahu Kalam segment by weekday (Python: 0=Mon, 6=Sun) ──
# The day (sunrise to sunset) is divided into 8 equal parts.
# Segment numbering: 1 = first after sunrise ... 8 = last before sunset.
RAHU_KALAM_SEGMENT = {
    0: 2,  # Monday
    1: 7,  # Tuesday
    2: 5,  # Wednesday
    3: 6,  # Thursday
    4: 4,  # Friday
    5: 3,  # Saturday
    6: 8,  # Sunday
}

# ── Gulika Kala segment by weekday ──
GULIKA_SEGMENT = {
    0: 6,  # Monday
    1: 5,  # Tuesday
    2: 4,  # Wednesday
    3: 3,  # Thursday
    4: 2,  # Friday
    5: 1,  # Saturday
    6: 7,  # Sunday
}

# ── Yamagandam segment by weekday ──
YAMAGANDAM_SEGMENT = {
    0: 4,  # Monday
    1: 3,  # Tuesday
    2: 2,  # Wednesday
    3: 1,  # Thursday
    4: 7,  # Friday
    5: 6,  # Saturday
    6: 5,  # Sunday
}

# ── Varjyam: nakshatra portion that is "rejected" ──
# Classical tables specify which of the 4 padas (quarters) contains
# the varjyam. Expressed as fraction of nakshatra duration from start.
# Each entry: (start_fraction, end_fraction) of the nakshatra span.
# Typically ~6 ghatikas (2h24m) into each nakshatra for ~1.5 ghatikas (36min).
# Simplified: the 50th-58th navamsa (60 ghatikas per nakshatra),
# which is roughly the last quarter of the nakshatra for most.
# Classical varjyam ghatikas (from start of nakshatra, 60 ghatikas = full):
VARJYAM_GHATIKAS = {
    "Ashwini":           (50, 54),
    "Bharani":           (14, 18),
    "Krittika":          (30, 34),
    "Rohini":            (22, 26),
    "Mrigashira":        (14, 18),
    "Ardra":             (26, 30),
    "Punarvasu":         (30, 34),
    "Pushya":            (14, 18),
    "Ashlesha":          (26, 30),
    "Magha":             (30, 34),
    "Purva Phalguni":    (14, 18),
    "Uttara Phalguni":   (26, 30),
    "Hasta":             (22, 26),
    "Chitra":            (14, 18),
    "Swati":             (26, 30),
    "Vishakha":          (14, 18),
    "Anuradha":          (26, 30),
    "Jyeshtha":          (22, 26),
    "Mula":              (14, 18),
    "Purva Ashadha":     (26, 30),
    "Uttara Ashadha":    (22, 26),
    "Shravana":          (14, 18),
    "Dhanishta":         (26, 30),
    "Shatabhisha":       (22, 26),
    "Purva Bhadrapada":  (14, 18),
    "Uttara Bhadrapada": (26, 30),
    "Revati":            (30, 34),
}

# Chaldean hora sequence
CHALDEAN_SEQUENCE = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

# Day lord by Python weekday (0=Mon, 6=Sun)
DAY_LORD = {
    0: "Moon",
    1: "Mars",
    2: "Mercury",
    3: "Jupiter",
    4: "Venus",
    5: "Saturn",
    6: "Sun",
}


# ─────────────────────────────────────────────────────────────────
# SUNRISE / SUNSET
# ─────────────────────────────────────────────────────────────────

def _compute_sunrise_sunset(target_date: datetime, lat: float, lon: float) -> Tuple[datetime, datetime]:
    """
    Compute sunrise and sunset (UTC) via Swiss Ephemeris.
    Falls back to 6am/6pm if calculation fails.
    """
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd_noon = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)

        RISE_FLAG = swe.CALC_RISE
        SET_FLAG = swe.CALC_SET
        GEO_FLAG = swe.BIT_DISC_CENTER

        rise_result = swe.rise_trans(
            jd_noon - 0.5, swe.SUN,
            RISE_FLAG | GEO_FLAG,
            [lon, lat, 0], 0.0, 0.0, swe.FLG_SWIEPH,
        )
        set_result = swe.rise_trans(
            jd_noon - 0.5, swe.SUN,
            SET_FLAG | GEO_FLAG,
            [lon, lat, 0], 0.0, 0.0, swe.FLG_SWIEPH,
        )

        def jd_to_utc(jd):
            y, m, d, h = swe.revjul(jd)
            hour = int(h)
            minute = int((h - hour) * 60)
            second = int(((h - hour) * 60 - minute) * 60)
            return datetime(y, m, d, hour, minute, second, tzinfo=tz.utc)

        return jd_to_utc(rise_result[1][0]), jd_to_utc(set_result[1][0])

    except Exception as e:
        logger.warning(f"[muhurta] Sunrise/sunset calc failed: {e} — using defaults")
        base = datetime(target_date.year, target_date.month, target_date.day, tzinfo=tz.utc)
        return base + timedelta(hours=6), base + timedelta(hours=18)


# ─────────────────────────────────────────────────────────────────
# SEGMENT WINDOW COMPUTATION
# ─────────────────────────────────────────────────────────────────

def _segment_window(sunrise: datetime, sunset: datetime, segment: int) -> Tuple[datetime, datetime]:
    """
    Given 8 equal segments of daylight, return (start, end) for the given segment (1-based).
    """
    total = (sunset - sunrise).total_seconds()
    seg_duration = total / 8.0
    start = sunrise + timedelta(seconds=(segment - 1) * seg_duration)
    end = sunrise + timedelta(seconds=segment * seg_duration)
    return start, end


# ─────────────────────────────────────────────────────────────────
# ABHIJIT MUHURTA
# ─────────────────────────────────────────────────────────────────

def _compute_abhijit(sunrise: datetime, sunset: datetime) -> dict:
    """
    Abhijit muhurta = 24 minutes before to 24 minutes after local solar noon.
    Solar noon = midpoint of sunrise and sunset.
    """
    total_secs = (sunset - sunrise).total_seconds()
    solar_noon = sunrise + timedelta(seconds=total_secs / 2)
    start = solar_noon - timedelta(minutes=24)
    end = solar_noon + timedelta(minutes=24)

    return {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "type": "very_auspicious",
        "note": "The one universally auspicious window of the day. Use for any important action if possible.",
    }


# ─────────────────────────────────────────────────────────────────
# RAHU KALAM / GULIKA / YAMAGANDAM
# ─────────────────────────────────────────────────────────────────

def _compute_rahu_kalam(sunrise: datetime, sunset: datetime, weekday: int) -> dict:
    seg = RAHU_KALAM_SEGMENT.get(weekday, 2)
    start, end = _segment_window(sunrise, sunset, seg)
    return {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "type": "inauspicious",
        "note": "Do not initiate, sign, commit, or travel. Wait.",
    }


def _compute_gulika_kala(sunrise: datetime, sunset: datetime, weekday: int) -> dict:
    seg = GULIKA_SEGMENT.get(weekday, 6)
    start, end = _segment_window(sunrise, sunset, seg)
    return {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "type": "inauspicious",
        "note": "Secondary inauspicious window — avoid starting new ventures.",
    }


def _compute_yamagandam(sunrise: datetime, sunset: datetime, weekday: int) -> dict:
    seg = YAMAGANDAM_SEGMENT.get(weekday, 4)
    start, end = _segment_window(sunrise, sunset, seg)
    return {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "type": "inauspicious",
        "note": "Window of hidden danger — avoid risky decisions and travel.",
    }


# ─────────────────────────────────────────────────────────────────
# VARJYAM
# ─────────────────────────────────────────────────────────────────

def _get_moon_longitude_sidereal(jd: float) -> float:
    """Get Moon's sidereal longitude at a given JD."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    result = swe.calc_ut(jd, swe.MOON, SWE_FLAGS)
    return result[0][0]


def _compute_varjyam(target_date: datetime, lat: float, lon: float,
                     sunrise: datetime, sunset: datetime) -> Optional[dict]:
    """
    Compute varjyam window for the day based on Moon's current nakshatra.
    Varjyam is a ~48 minute inauspicious window within the nakshatra.
    """
    try:
        # Get Moon position at sunrise
        jd_sunrise = swe.julday(
            sunrise.year, sunrise.month, sunrise.day,
            sunrise.hour + sunrise.minute / 60.0 + sunrise.second / 3600.0
        )
        moon_lon = _get_moon_longitude_sidereal(jd_sunrise)
        nak_idx = int(moon_lon / NAKSHATRA_SPAN)
        nak_name = NAKSHATRAS[nak_idx % 27]

        varjyam_range = VARJYAM_GHATIKAS.get(nak_name)
        if not varjyam_range:
            return None

        # Compute Moon's entry into current nakshatra
        nak_start_lon = nak_idx * NAKSHATRA_SPAN
        nak_end_lon = nak_start_lon + NAKSHATRA_SPAN

        # Moon speed at sunrise (degrees per day)
        result = swe.calc_ut(jd_sunrise, swe.MOON, SWE_FLAGS)
        moon_speed = result[0][3]  # deg/day

        if moon_speed <= 0:
            return None

        # Time for Moon to traverse the full nakshatra from its start
        # Ghatikas: 60 ghatikas = full nakshatra duration
        nak_duration_days = NAKSHATRA_SPAN / moon_speed
        ghatika_duration_days = nak_duration_days / 60.0

        # Moon's position within nakshatra (in ghatikas from start)
        degree_into_nak = moon_lon - nak_start_lon
        ghatikas_elapsed = (degree_into_nak / NAKSHATRA_SPAN) * 60.0

        # Varjyam start/end in ghatikas from nakshatra start
        varjyam_start_ghatika, varjyam_end_ghatika = varjyam_range

        # Convert to time offset from nakshatra entry
        # Nakshatra entry time = sunrise - (ghatikas_elapsed * ghatika_duration)
        nak_entry_time = sunrise - timedelta(days=ghatikas_elapsed * ghatika_duration_days)

        varjyam_start = nak_entry_time + timedelta(days=varjyam_start_ghatika * ghatika_duration_days)
        varjyam_end = nak_entry_time + timedelta(days=varjyam_end_ghatika * ghatika_duration_days)

        # Only return if varjyam falls within today's waking hours
        # Extend window: sunrise - 1h to sunset + 2h
        day_start = sunrise - timedelta(hours=1)
        day_end = sunset + timedelta(hours=2)

        if varjyam_end < day_start or varjyam_start > day_end:
            return None

        return {
            "start_utc": varjyam_start.isoformat(),
            "end_utc": varjyam_end.isoformat(),
            "type": "inauspicious",
            "nakshatra": nak_name,
            "note": f"Varjyam within {nak_name} nakshatra — 'rejected' time period, avoid important actions.",
        }

    except Exception as e:
        logger.warning(f"[muhurta] Varjyam computation failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# MOON NAKSHATRA TRANSITIONS
# ─────────────────────────────────────────────────────────────────

def _find_moon_nakshatra_transitions(
    target_date: datetime,
    sunrise: datetime,
    sunset: datetime,
) -> List[dict]:
    """
    Find times when Moon crosses nakshatra boundaries during the day.
    Uses binary search between sunrise and next day's sunrise.
    """
    transitions = []
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        # Search window: sunrise today to sunrise + 24h
        search_start = sunrise
        search_end = sunrise + timedelta(hours=24)

        jd_start = swe.julday(
            search_start.year, search_start.month, search_start.day,
            search_start.hour + search_start.minute / 60.0
        )
        jd_end = swe.julday(
            search_end.year, search_end.month, search_end.day,
            search_end.hour + search_end.minute / 60.0
        )

        # Get Moon nakshatra at start
        start_lon = _get_moon_longitude_sidereal(jd_start)
        start_nak = int(start_lon / NAKSHATRA_SPAN)

        # Step through in ~2 hour increments, check for nakshatra change
        step_days = 2.0 / 24.0  # 2 hours in days
        jd_current = jd_start

        while jd_current < jd_end:
            jd_next = min(jd_current + step_days, jd_end)
            lon_current = _get_moon_longitude_sidereal(jd_current)
            lon_next = _get_moon_longitude_sidereal(jd_next)
            nak_current = int(lon_current / NAKSHATRA_SPAN) % 27
            nak_next = int(lon_next / NAKSHATRA_SPAN) % 27

            if nak_current != nak_next:
                # Binary search for exact transition
                lo, hi = jd_current, jd_next
                for _ in range(20):  # ~20 iterations → sub-second precision
                    mid = (lo + hi) / 2
                    mid_lon = _get_moon_longitude_sidereal(mid)
                    mid_nak = int(mid_lon / NAKSHATRA_SPAN) % 27
                    if mid_nak == nak_current:
                        lo = mid
                    else:
                        hi = mid

                transition_jd = (lo + hi) / 2
                y, m, d, h = swe.revjul(transition_jd)
                hour = int(h)
                minute = int((h - hour) * 60)
                second = int(((h - hour) * 60 - minute) * 60)
                transition_time = datetime(y, m, d, hour, minute, second, tzinfo=tz.utc)

                from_nak = NAKSHATRAS[nak_current]
                to_nak = NAKSHATRAS[nak_next]

                transitions.append({
                    "time_utc": transition_time.isoformat(),
                    "from_nakshatra": from_nak,
                    "to_nakshatra": to_nak,
                    "note": f"Moon shifts from {from_nak} to {to_nak} — energy flavor changes.",
                })

            jd_current = jd_next

    except Exception as e:
        logger.warning(f"[muhurta] Moon transition computation failed: {e}")

    return transitions


# ─────────────────────────────────────────────────────────────────
# KALA HORA SEQUENCE
# ─────────────────────────────────────────────────────────────────

def _compute_hora_sequence(
    sunrise: datetime,
    sunset: datetime,
    weekday: int,
) -> List[dict]:
    """
    Compute the 24-hora (planetary hour) sequence for the day.
    First hora after sunrise = weekday's lord.
    Chaldean sequence cycles.
    """
    day_lord = DAY_LORD.get(weekday, "Sun")
    start_idx = CHALDEAN_SEQUENCE.index(day_lord)

    day_duration = (sunset - sunrise).total_seconds()
    # Night duration: assume ~12 hours for simplicity (next sunrise not computed here)
    night_duration = 86400 - day_duration  # remainder of 24h

    day_hora_secs = day_duration / 12.0
    night_hora_secs = night_duration / 12.0

    horas = []
    idx = start_idx

    # 12 day horas
    for i in range(12):
        start = sunrise + timedelta(seconds=i * day_hora_secs)
        end = sunrise + timedelta(seconds=(i + 1) * day_hora_secs)
        ruler = CHALDEAN_SEQUENCE[idx % 7]
        horas.append({
            "hour_start_utc": start.isoformat(),
            "hour_end_utc": end.isoformat(),
            "ruler": ruler,
            "is_day": True,
        })
        idx += 1

    # 12 night horas
    for i in range(12):
        start = sunset + timedelta(seconds=i * night_hora_secs)
        end = sunset + timedelta(seconds=(i + 1) * night_hora_secs)
        ruler = CHALDEAN_SEQUENCE[idx % 7]
        horas.append({
            "hour_start_utc": start.isoformat(),
            "hour_end_utc": end.isoformat(),
            "ruler": ruler,
            "is_day": False,
        })
        idx += 1

    return horas


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def compute_muhurtas(
    target_date: datetime,
    latitude: float,
    longitude: float,
    tz_offset: float = None,
) -> dict:
    """
    Compute today's classical muhurta windows.

    Args:
        target_date: date/datetime for the day
        latitude: geographic latitude
        longitude: geographic longitude

    Returns:
        Dict with all muhurta windows, transitions, and hora sequence.
    """
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        # Sunrise/sunset
        sunrise, sunset = _compute_sunrise_sunset(target_date, latitude, longitude)
        weekday = target_date.weekday() if hasattr(target_date, 'weekday') else 0

        # Use explicit tz_offset if provided; fall back to longitude approximation
        if tz_offset is not None:
            utc_offset = tz_offset
        else:
            utc_offset = round(longitude / 15.0)

        def utc_to_local_str(dt: datetime) -> str:
            local = dt + timedelta(hours=utc_offset)
            return local.strftime("%I:%M %p").lstrip("0")

        # Core windows
        abhijit = _compute_abhijit(sunrise, sunset)
        rahu_kalam = _compute_rahu_kalam(sunrise, sunset, weekday)
        gulika_kala = _compute_gulika_kala(sunrise, sunset, weekday)
        yamagandam = _compute_yamagandam(sunrise, sunset, weekday)

        # Varjyam
        varjyam = _compute_varjyam(target_date, latitude, longitude, sunrise, sunset)

        # Moon nakshatra transitions
        moon_transitions = _find_moon_nakshatra_transitions(target_date, sunrise, sunset)

        # Hora sequence (compact — only include day horas for prompt)
        hora_sequence = _compute_hora_sequence(sunrise, sunset, weekday)

        # Add local time strings to all windows
        def add_local_times(window: dict) -> dict:
            if not window:
                return window
            w = dict(window)
            if "start_utc" in w:
                try:
                    start_dt = datetime.fromisoformat(w["start_utc"])
                    end_dt = datetime.fromisoformat(w["end_utc"])
                    w["start_local"] = utc_to_local_str(start_dt)
                    w["end_local"] = utc_to_local_str(end_dt)
                except Exception:
                    pass
            return w

        abhijit = add_local_times(abhijit)
        rahu_kalam = add_local_times(rahu_kalam)
        gulika_kala = add_local_times(gulika_kala)
        yamagandam = add_local_times(yamagandam)
        if varjyam:
            varjyam = add_local_times(varjyam)

        for t in moon_transitions:
            if "time_utc" in t:
                try:
                    t_dt = datetime.fromisoformat(t["time_utc"])
                    t["time_local"] = utc_to_local_str(t_dt)
                except Exception:
                    pass

        return {
            "sunrise_utc": sunrise.isoformat(),
            "sunset_utc": sunset.isoformat(),
            "sunrise_local": utc_to_local_str(sunrise),
            "sunset_local": utc_to_local_str(sunset),
            "utc_offset_approx": utc_offset,

            "abhijit_muhurta": abhijit,
            "rahu_kalam": rahu_kalam,
            "gulika_kala": gulika_kala,
            "yamagandam": yamagandam,
            "varjyam": varjyam,

            "moon_nakshatra_transitions": moon_transitions,
            "hora_sequence": hora_sequence,
        }

    except Exception as e:
        logger.error(f"[muhurta] compute_muhurtas failed: {e}", exc_info=True)
        return {}


# ─────────────────────────────────────────────────────────────────
# PROMPT FORMATTER
# ─────────────────────────────────────────────────────────────────

def format_muhurtas_for_prompt(muhurtas: dict) -> str:
    """
    Format muhurta windows into a text block for LLM prompt injection.
    Uses local times when available.
    """
    if not muhurtas:
        return ""

    lines = ["MUHURTA WINDOWS (timing data):"]
    lines.append(f"  Sunrise: {muhurtas.get('sunrise_local', '?')}")
    lines.append(f"  Sunset: {muhurtas.get('sunset_local', '?')}")

    # Abhijit
    ab = muhurtas.get("abhijit_muhurta", {})
    if ab:
        lines.append(f"  Abhijit Muhurta (AUSPICIOUS): {ab.get('start_local', '?')} – {ab.get('end_local', '?')}")
        lines.append(f"    {ab.get('note', '')}")

    # Rahu Kalam
    rk = muhurtas.get("rahu_kalam", {})
    if rk:
        lines.append(f"  Rahu Kalam (AVOID): {rk.get('start_local', '?')} – {rk.get('end_local', '?')}")
        lines.append(f"    {rk.get('note', '')}")

    # Gulika Kala
    gk = muhurtas.get("gulika_kala", {})
    if gk:
        lines.append(f"  Gulika Kala (AVOID): {gk.get('start_local', '?')} – {gk.get('end_local', '?')}")
        lines.append(f"    {gk.get('note', '')}")

    # Yamagandam
    yg = muhurtas.get("yamagandam", {})
    if yg:
        lines.append(f"  Yamagandam (AVOID): {yg.get('start_local', '?')} – {yg.get('end_local', '?')}")
        lines.append(f"    {yg.get('note', '')}")

    # Varjyam
    vj = muhurtas.get("varjyam")
    if vj:
        lines.append(f"  Varjyam (AVOID): {vj.get('start_local', '?')} – {vj.get('end_local', '?')}")
        lines.append(f"    {vj.get('note', '')}")

    # Moon transitions
    transitions = muhurtas.get("moon_nakshatra_transitions", [])
    if transitions:
        for t in transitions:
            lines.append(f"  Moon nakshatra shift at {t.get('time_local', '?')}: "
                         f"{t.get('from_nakshatra', '?')} → {t.get('to_nakshatra', '?')}")
            lines.append(f"    {t.get('note', '')}")
    else:
        lines.append("  Moon nakshatra: No transition during waking hours today.")

    return "\n".join(lines)
