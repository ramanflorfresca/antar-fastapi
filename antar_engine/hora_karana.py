"""
antar_engine/hora_karana.py
─────────────────────────────
WS4 of the "kill the generic read" sprint.

PURPOSE:
  For tactical / "today" / "right now" questions, produce a real intraday
  clock boundary so /predict's `precision_windows` payload is non-empty
  for the answer to anchor on.

WHY THIS EXISTS:
  Live diagnostic showed `precision_windows = []` on both the speculation
  and property questions because find_precision_windows only resolves
  date-level windows over the coming year — it cannot say "the current
  window tightens at 11:40 and clears after". For a tactical question
  the answer needs a clock boundary, not a date range.

WHAT IT DOES:
  1. Decides whether the question is tactical (today / now / today's /
     this evening / right now ...). Cheap keyword router; conservative.
  2. Resolves the user's CURRENT location (capital of current_country,
     not birth coords — sunrise is location-dependent).
  3. Calls hora_engine.get_hora_schedule() to find the current Hora
     window's end (real local-sunrise-anchored boundary).
  4. Computes the current Karana (half-tithi) boundary from real Moon
     and Sun longitudes via swisseph with Lahiri sidereal mode VERIFIED.
  5. Returns a list shaped like find_precision_windows output so the
     existing `precision_windows_to_context_block` can render it
     without changes.

CRITICAL CONSTRAINTS:
  - Lahiri sidereal mode (SIDM_LAHIRI) must be active before trusting
    swisseph longitudes.
  - Sunrise uses CURRENT location, not birth location.
  - Never crash /predict — every failure returns an empty list.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone as _tz
from typing import Any, Dict, List, Optional


# Cheap router — these tactical markers indicate the answer must carry
# a clock boundary, not a date range.
_TACTICAL_MARKERS = [
    "today", "right now", "this morning", "this afternoon",
    "this evening", "tonight", "this week",
    "now ", " now?", " now.", " now,",
    "in the next hour", "in the next few hours",
    "this hour", "before tonight", "before tomorrow",
    # Spanish
    "hoy", "ahora", "esta tarde", "esta noche", "esta mañana",
    "en la próxima hora", "en la proxima hora",
]


def is_tactical_question(question: str) -> bool:
    """True if the question wants a clock-boundary answer, not a date range."""
    if not question:
        return False
    q = str(question).lower()
    return any(m in q for m in _TACTICAL_MARKERS)


# ─────────────────────────────────────────────────────────────────────
# Karana (half-tithi) — computed live from swisseph
# ─────────────────────────────────────────────────────────────────────

# A karana = 6° of Moon−Sun separation. There are 11 named karanas in
# a repeating sequence across the 60 karanas of a lunar month.
_KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila",
    "Garaja", "Vanija", "Vishti",
]

# Mapping to plain English mode-of-window so we can label the boundary
# without leaking Sanskrit into the user-facing field.
_KARANA_MOOD = {
    "Bava":    "smooth",
    "Balava":  "supportive",
    "Kaulava": "supportive",
    "Taitila": "negotiable",
    "Garaja":  "grounded",
    "Vanija":  "transactional",
    "Vishti":  "friction",
}


def _ensure_lahiri() -> bool:
    """Set SIDM_LAHIRI on swisseph and verify. Returns True on success.
    Per project rule we must not trust output otherwise."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        # Defensive verification — if the call above silently no-ops we
        # would generate tropical longitudes and lie about the karana.
        # swisseph doesn't expose a "get sid mode" cleanly, so we assert
        # by computing a Lahiri ayanamsa and checking it is in range.
        from datetime import datetime as _dt
        jd_now = swe.julday(_dt.utcnow().year, _dt.utcnow().month, _dt.utcnow().day, 0)
        ayan = swe.get_ayanamsa(jd_now)
        # 2026 Lahiri ayanamsa is ~24.2°. Sanity-bound rather than
        # exact-match so this works across years.
        return 22.0 < float(ayan) < 27.0
    except Exception:
        return False


def _moon_sun_diff(now_utc: datetime) -> Optional[float]:
    """Sidereal Moon−Sun longitude in [0, 360). None on failure."""
    try:
        import swisseph as swe
        jd_ut = swe.julday(
            now_utc.year, now_utc.month, now_utc.day,
            now_utc.hour + now_utc.minute / 60.0 + now_utc.second / 3600.0,
        )
        flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
        sun_lon = swe.calc_ut(jd_ut, swe.SUN, flag)[0][0]
        moon_lon = swe.calc_ut(jd_ut, swe.MOON, flag)[0][0]
        diff = (float(moon_lon) - float(sun_lon)) % 360.0
        return diff
    except Exception:
        return None


def _current_karana(now_utc: datetime) -> Optional[Dict[str, Any]]:
    """Return current karana + minutes-to-boundary at the boundary
    where Moon−Sun crosses the next 6° mark."""
    if not _ensure_lahiri():
        return None
    diff = _moon_sun_diff(now_utc)
    if diff is None:
        return None

    # Karana index in [0, 59]; each spans 6°.
    karana_idx = int(diff / 6.0) % 60
    # Name is the simple 7-of-11 cycle for the "movable" karanas.
    # First and last karanas of the lunar month are "fixed" — Kimstughna,
    # Shakuni, Naga, Chatushpada — we collapse those into adjacent
    # mood labels for narration purposes (treat all fixed as "subtle").
    if karana_idx == 0 or karana_idx >= 57:
        name = "Subtle"
        mood = "subtle"
    else:
        name = _KARANA_NAMES[(karana_idx - 1) % 7]
        mood = _KARANA_MOOD.get(name, "neutral")

    # Boundary: how long until diff hits the next 6° mark.
    deg_into = diff % 6.0
    deg_to_next = 6.0 - deg_into
    # Moon moves ~13.18°/day vs Sun ~0.985°/day → relative ~12.19°/day.
    rel_speed_per_min = 12.19 / (24.0 * 60.0)
    if rel_speed_per_min <= 0:
        return None
    mins_to_boundary = int(deg_to_next / rel_speed_per_min)
    boundary_dt = now_utc + timedelta(minutes=mins_to_boundary)

    return {
        "mood": mood,
        "mins_to_boundary": mins_to_boundary,
        "boundary_utc": boundary_dt.isoformat(),
        "_karana_name_for_debug": name,
    }


# ─────────────────────────────────────────────────────────────────────
# Public entry — main.py wires this in
# ─────────────────────────────────────────────────────────────────────

def build_intraday_window(
    lat: float,
    lng: float,
    tz_offset_hours: float = 0,
    concern: str = "general",
    language: str = "en",
    target_dt: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Return precision-window-shaped list with ONE entry: the current
    intraday boundary (hora end + karana boundary, whichever comes
    first). Empty list on any failure — never crashes the caller."""
    try:
        from antar_engine.hora_engine import get_hora_schedule
        now_utc = target_dt or datetime.now(_tz.utc)

        sched = get_hora_schedule(
            lat=lat, lng=lng, tz_offset=int(round(tz_offset_hours)),
            n_horas=2, target_dt=now_utc,
        ) or {}
        current = sched.get("current_hora") or {}
        if not current:
            return []

        hora_window = current.get("window", "current window")
        mins_left = int(current.get("mins_remaining", 0) or 0)
        if mins_left <= 0:
            return []
        hora_end_utc = datetime.fromisoformat(current["end_utc"])
        hora_end_local = hora_end_utc + timedelta(hours=tz_offset_hours)
        # [window-state] stale-end guard
        # Defensive: if the hora_end_local has already passed at
        # narration time (rounding, race condition, cache hit
        # boundary), the window is no longer live. Drop it.
        _now_local_dt = now_utc + timedelta(hours=tz_offset_hours)
        if hora_end_local <= _now_local_dt:
            return []

        # Karana is optional — render with it when available.
        karana = _current_karana(now_utc)
        karana_boundary_str = ""
        karana_mood = ""
        if karana:
            k_end_utc = datetime.fromisoformat(karana["boundary_utc"])
            k_end_local = k_end_utc + timedelta(hours=tz_offset_hours)
            karana_boundary_str = k_end_local.strftime("%H:%M")
            karana_mood = karana.get("mood", "")

        hora_boundary_str = hora_end_local.strftime("%H:%M")

        is_es = (language or "en").lower().startswith("es")
        if is_es:
            label = "Ventana intradía"
            reasons = [
                f"{hora_window.lower()} cierra a las {hora_boundary_str} hora local",
            ]
            if karana_boundary_str:
                reasons.append(
                    f"transición sutil ({karana_mood}) a las {karana_boundary_str}"
                )
            what_to_do = (
                f"Antes de las {hora_boundary_str}, mueve la pieza que requiere "
                "tracción; después, baja a tareas internas hasta la próxima ventana."
            )
            avoid = (
                "Evita decisiones de alta apuesta en el cambio de ventana — "
                "espera el siguiente segmento."
            )
            intensity_desc = "Ventana corta — actúa dentro del horizonte de minutos, no de días."
        else:
            label = "Intraday window"
            reasons = [
                f"{hora_window.lower()} closes at {hora_boundary_str} local",
            ]
            if karana_boundary_str:
                reasons.append(
                    f"karana mood shift ({karana_mood}) at {karana_boundary_str}"
                )
            what_to_do = (
                f"Before {hora_boundary_str}, move the piece that needs "
                "traction; after that, drop to internal tasks until the next window."
            )
            avoid = (
                "Avoid high-stakes commitments right at the window changeover — "
                "let the next segment open first."
            )
            intensity_desc = (
                "Short window — act on the minutes horizon, not the days horizon."
            )

        # Pick the EARLIER boundary as the window's end so the caller
        # gets the real "this tightens at X" signal.
        if karana and karana.get("mins_to_boundary", 99999) < mins_left:
            end_for_label = karana_boundary_str
            duration_label = f"~{karana['mins_to_boundary']} min"
        else:
            end_for_label = hora_boundary_str
            duration_label = f"~{mins_left} min"

        return [{
            "rank": 1,
            "window_label": label,
            "date_range": f"now → {end_for_label} local",
            "score": 7.0,
            "avg_score": 7.0,
            "duration_days": 0,
            "duration_label": duration_label,
            "intensity": "intraday",
            "intensity_desc": intensity_desc,
            "reasons": reasons,
            "what_to_do": what_to_do,
            "what_to_avoid": avoid,
            "is_intraday": True,
        }]
    except Exception as e:
        try:
            import logging
            logging.getLogger(__name__).warning(
                f"[hora_karana] build_intraday_window failed: {e}"
            )
        except Exception:
            pass
        return []
