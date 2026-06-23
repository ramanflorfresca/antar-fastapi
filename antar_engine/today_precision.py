"""
today_precision.py — "Today Precision v2": the five-layer collapse.

Turns the signals that already exist in the codebase into ONE specific, timed,
named line — the "wow" daily:

    "Today leans toward money & voice — strongest window 2:10–4:30 PM;
     ease off after the evening dip. Make the ask in that window."

LAYERS (each answers a different question, by how fast it moves):
  1. Life chapter   — current mahadasha lord (years)            -> theme
  2. Pressure       — Lal Kitab day quality (today)             -> tone
  3. Day quality    — Tara Bala vs natal Moon (today, personal) -> for-you verdict
  4. Domain         — today's Moon house-from-lagna (today)     -> which area
  5. Hours          — planetary hora for that domain (intraday) -> WHEN today

Reuses antar_engine.daily_precision (Tara + Moon-house) and
antar_engine.hora_engine (hour windows). Pure + fallback-safe: any missing
input degrades, never raises. Jargon-free output (no nakshatra / tara / house /
planet words leak); output_strips runs as a backstop. Behind DAILY_PRECISION_V2.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone as _tz
from typing import Any, Dict, Optional

from antar_engine.daily_precision import compute_daily_precision

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# chart.py nakshatra spelling (what chart_data stores)
CHART_NAK = [
    "Ashvini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]
# tara_bala.py spelling (what compute_tara_bala expects)
TARA_NAK = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]


def _norm_key(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "").replace("-", "").replace("w", "v")


# normalized -> tara_bala canonical name (handles Ashvini/Ashwini + spacing)
_TO_TARA = {_norm_key(n): n for n in TARA_NAK}


def _to_tara_nak(name: str) -> Optional[str]:
    return _TO_TARA.get(_norm_key(name))


# lit domain house -> hora FIELD (which hour-window suits the day's area)
_HOUSE_FIELD = {
    1: "COMMAND", 2: "EXPANSION", 3: "ALLIANCE", 4: "NURTURE",
    5: "ALLIANCE", 6: "COMMAND", 7: "ALLIANCE", 8: "DEPTH",
    9: "EXPANSION", 10: "COMMAND", 11: "EXPANSION", 12: "DEPTH",
}


def _today_moon(now_utc: datetime):
    """(sign, nakshatra in chart spelling) of the Moon now, Lahiri sidereal."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd = swe.julday(now_utc.year, now_utc.month, now_utc.day,
                        now_utc.hour + now_utc.minute / 60.0)
        vals, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        lon = vals[0] % 360.0
        return SIGNS[int(lon // 30)], CHART_NAK[int(lon // (360.0 / 27.0))]
    except Exception:
        return None, None


def _natal_moon_lagna(chart_data: Dict[str, Any]):
    planets = (chart_data or {}).get("planets") or {}
    moon = planets.get("Moon") or {}
    nak = moon.get("nakshatra")
    lagna = ((chart_data or {}).get("lagna") or {}).get("sign")
    return nak, lagna


def _strip(text, language):
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        return apply_user_facing_strips(text, language=language, field_type="plain")
    except Exception:
        return text


def _parse_clock(s: str):
    try:
        t = datetime.strptime((s or "").strip(), "%I:%M %p")
        return t.hour * 60 + t.minute
    except Exception:
        return None


def _fmt_clock(mins: int) -> str:
    mins %= 1440
    h, m = divmod(mins, 60)
    ap = "AM" if h < 12 else "PM"
    return f"{(h % 12) or 12}:{m:02d} {ap}"


def _window_from_hora(h: Dict[str, Any]):
    """Rebuild a sane 'start–end' window from start_local + duration (never
    reversed). Returns (window_str, is_day) or (None, None) if unusable."""
    if not h:
        return None, None
    st = _parse_clock(h.get("start_local") or "")
    dur = h.get("duration_mins")
    # Real planetary horas are ~40-90 min. Anything outside that means the
    # sunrise/sunset calc produced a bad span -> reject (don't surface garbage).
    if st is None or not isinstance(dur, (int, float)) or not (35 <= dur <= 95):
        return None, None
    return f"{_fmt_clock(st)}–{_fmt_clock(st + int(dur))}", bool(h.get("is_day"))


def is_enabled() -> bool:
    return (os.environ.get("DAILY_PRECISION_V2", "shadow") or "shadow").lower() \
        in ("shadow", "on", "primary")


def compute_today_precision(chart_data: Dict[str, Any],
                            transit_polarity: Optional[str],
                            lat: float, lng: float,
                            tz_offset_hours: float = 0.0,
                            now_utc: Optional[datetime] = None,
                            day_quality: Optional[str] = None,
                            fallback_window: Optional[str] = None,
                            fallback_avoid: Optional[str] = None,
                            language: str = "en") -> Dict[str, Any]:
    """
    Return the collapsed precise-today bundle (always a dict; eligible=False when
    inputs are insufficient).

      {eligible, line, domain, verdict, best_window, avoid_window, action,
       confidence, confidence_meter, debug}

    transit_polarity: "positive"/"negative" from the existing today signal.
    day_quality:      Lal Kitab day quality ("favorable"/"caution"/...) if known.
    """
    now_utc = now_utc or datetime.now(_tz.utc)
    natal_nak, natal_lagna = _natal_moon_lagna(chart_data)
    t_sign, t_nak = _today_moon(now_utc)

    if not (natal_nak and natal_lagna and t_sign and t_nak):
        return {"eligible": False, "reason": "missing Moon/lagna inputs"}

    precision = compute_daily_precision(
        _to_tara_nak(natal_nak) or natal_nak, natal_lagna,
        _to_tara_nak(t_nak) or t_nak, t_sign,
    )
    domain = precision.get("lit_domain")
    house = precision.get("moon_house_from_lagna")
    if not domain:
        return {"eligible": False, "reason": "no lit domain"}

    # ── verdict blend: transit polarity + tara + house deltas ──
    base = 1 if (transit_polarity == "positive") else (-1 if transit_polarity == "negative" else 0)
    tara_d = int(precision.get("tara_score_delta", 0))
    house_d = int(precision.get("house_score_delta", 0))
    score = base + tara_d + house_d

    if score >= 2:
        verdict, lead = "favorable", f"Today genuinely favors {domain}"
    elif score == 1:
        verdict, lead = "leaning", f"Today leans toward {domain}"
    elif score == 0:
        verdict, lead = "mixed", f"A mixed day for {domain}"
    else:
        verdict, lead = "caution", f"Hold big moves on {domain} today"

    is_friction = (verdict == "caution") or (day_quality in ("caution", "unfavorable"))

    # ── hours: best window for this domain's field ──
    best_window = None
    avoid_window = None
    best_is_day = False
    field = _HOUSE_FIELD.get(house or 0)
    prefer_day = field in ("COMMAND", "ALLIANCE", "EXPANSION", "SPARK")
    try:
        from antar_engine.hora_engine import get_hora_schedule, get_next_power_hora
        sched = get_hora_schedule(float(lat), float(lng),
                                  tz_offset=int(round(tz_offset_hours)),
                                  n_horas=24, daily_field=field,
                                  is_friction_day=is_friction, target_dt=now_utc)
        cur = sched.get("current_hora") or {}
        candidates = [cur] + (sched.get("upcoming_horas") or [])
        # Action domains need WAKING hours — a career/money window at 11pm is
        # useless. Pass 1: daytime field-match with a sane window. Pass 2: any
        # field-match with a sane window. Windows are rebuilt start+duration so a
        # buggy reversed end_local can never surface.
        if field:
            for require_day in ((True, False) if prefer_day else (False,)):
                for h in candidates:
                    if not h or h.get("field") != field:
                        continue
                    if require_day and not h.get("is_day"):
                        continue
                    w, isday = _window_from_hora(h)
                    if w:
                        best_window, best_is_day = w, isday
                        break
                if best_window:
                    break
        # avoid: the next go-dark (Mars) hora with a sane window
        for h in candidates:
            if h and h.get("ruler") == "Mars":
                w, _ = _window_from_hora(h)
                if w:
                    avoid_window = w
                    break
    except Exception:
        avoid_window = None

    # Trusted fallback: when hora gives no sane daytime window, use the muhurta
    # window the home composer already computes (daytime, classical, correct).
    if not best_window and fallback_window:
        best_window, best_is_day = fallback_window, True
    if not avoid_window and fallback_avoid:
        avoid_window = fallback_avoid

    # ── action (jargon-free) ──
    advice = precision.get("tara_advice") or ""
    late = bool(best_window) and prefer_day and not best_is_day
    if verdict in ("favorable", "leaning"):
        if late:
            action = (f"Today's clear window comes late — line up the {domain} "
                      "move for daytime.")
        elif best_window:
            action = f"Make your real move on {domain} inside that window."
        else:
            action = f"Lean into {domain} today."
    elif verdict == "mixed":
        action = f"Test the water on {domain}; don't commit hard today."
    else:
        action = "Use today to review and tidy up — not to launch."

    # ── confidence 0-3: how many layers agree with the verdict direction ──
    agree = 0
    favourable_dir = score > 0
    if (base > 0) == favourable_dir and base != 0:
        agree += 1
    if (tara_d > 0) == favourable_dir and tara_d != 0:
        agree += 1
    if (house_d > 0) == favourable_dir and house_d != 0:
        agree += 1
    confidence = max(0, min(3, agree))

    # ── collapse into one line ──
    parts = [lead]
    if best_window:
        parts.append(f"next clear window {best_window} (late)" if late
                     else f"strongest window {best_window}")
    if is_friction and avoid_window:
        parts.append(f"ease off around {avoid_window}")
    line = " — ".join([parts[0]] + ([", ".join(parts[1:])] if len(parts) > 1 else []))
    line = f"{line}. {action}"

    return {
        "eligible": True,
        "line": _strip(line, language),
        "domain": domain,
        "verdict": verdict,
        "best_window": best_window,
        "avoid_window": avoid_window if is_friction else None,
        "action": _strip(action, language),
        "confidence": confidence,
        "confidence_meter": "●" * confidence + "○" * (3 - confidence),
        "debug": {
            "transit_polarity": transit_polarity, "score": score,
            "tara_delta": tara_d, "house_delta": house_d,
            "house": house, "field": field,
            "today_moon": {"sign": t_sign, "nak": t_nak},
            "day_quality": day_quality,
        },
    }
