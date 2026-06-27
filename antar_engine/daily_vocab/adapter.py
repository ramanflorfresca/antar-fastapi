"""
antar_engine/daily_vocab/adapter.py — the ONE place that turns a chart + a date
into a `concrete` block using the live transit engine.

This is the bridge between the pure vocab layer (compose.py, no ephemeris) and
the Swiss-Ephemeris world. It reuses transit_events' Lahiri helpers so positions
match the rest of the pipeline exactly. Both the prod wiring (home_composer) and
the review harness (antar_research/daily_vocab_samples) call THIS function, so
what Raman reviews is byte-for-byte what prod emits.

Transit sign/nakshatra/house and natal aspects are GEOCENTRIC — they need only
the date, not a location. Intraday timing windows (which DO need a location) are
reused from upstream and passed in as best_window / steer_clear_window.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from antar_engine.daily_vocab.compose import compute_concrete_block


def _tithi_quality(moon_lon: float, sun_lon: float) -> Optional[str]:
    try:
        from antar_engine.daily_panchanga import TITHI_QUALITY, TITHI_NAMES
        idx = int(((moon_lon - sun_lon) % 360.0) / 12.0) % 30
        return TITHI_QUALITY.get(TITHI_NAMES[idx])
    except Exception:
        return None


def build_day_inputs(chart_data: dict, on_date: date) -> Dict[str, Any]:
    """Compute the engine-agnostic kwargs compute_concrete_block expects, for
    one date, from a natal chart. Touches Swiss Ephemeris via transit_events."""
    from antar_engine.transit_events import (
        _calc, _sign_of, _nakshatra_of, _natal_house_for,
        _extract_natal_positions, _extract_lagna_sign_idx,
        SIGNS, NAKSHATRAS, _ALL_PLANETS, _ASPECT_ANGLES, _ASPECT_ORB,
    )
    from antar_engine.daily_precision import compute_daily_precision

    natal = _extract_natal_positions(chart_data)
    lagna_idx = _extract_lagna_sign_idx(chart_data)

    moon_lon, _ = _calc("Moon", on_date)
    sun_lon, _ = _calc("Sun", on_date)

    contacts: List[dict] = []
    for p in _ALL_PLANETS:
        try:
            lon, _ = _calc(p, on_date)
        except Exception:
            continue
        house = _natal_house_for(lon, lagna_idx)
        best = None  # (orb, kind, natal_planet)
        orb_allow = _ASPECT_ORB.get(p, 1.5)
        for npl, nlon in natal.items():
            sep = abs((lon - nlon) % 360.0)
            sep = min(sep, 360.0 - sep)
            for kind, angle in _ASPECT_ANGLES.items():
                o = abs(sep - angle)
                if o <= orb_allow and (best is None or o < best[0]):
                    best = (o, kind, npl)
        c: Dict[str, Any] = {"planet": p, "house": house}
        if best:
            o, kind, npl = best
            c["aspect_to_natal"] = kind
            c["orb"] = round(o, 2)
            c["target_house"] = _natal_house_for(natal[npl], lagna_idx)
        contacts.append(c)

    today_moon_sign = SIGNS[_sign_of(moon_lon)]
    today_moon_nak = NAKSHATRAS[_nakshatra_of(moon_lon)]
    nm = natal.get("Moon")
    natal_moon_sign = SIGNS[_sign_of(nm)] if nm is not None else None
    natal_moon_nak = NAKSHATRAS[_nakshatra_of(nm)] if nm is not None else None
    natal_lagna_sign = SIGNS[lagna_idx]

    precision = compute_daily_precision(
        natal_moon_nak or "", natal_lagna_sign, today_moon_nak, today_moon_sign)

    return dict(
        today_moon_sign=today_moon_sign,
        today_moon_nak=today_moon_nak,
        natal_moon_sign=natal_moon_sign,
        natal_moon_nak=natal_moon_nak,
        natal_lagna_sign=natal_lagna_sign,
        weekday=on_date.strftime("%A"),
        tithi_quality=_tithi_quality(moon_lon, sun_lon),
        transit_contacts=contacts,
        precision=precision,
    )


def build_concrete_for_chart(
    chart_data: dict,
    *,
    on_date: Optional[date] = None,
    best_window: Optional[str] = None,
    steer_clear_window: Optional[str] = None,
    language: str = "en",
    personal_lord: Optional[str] = None,  # [perchart-lord]
) -> Dict[str, Any]:
    """Full `concrete` block (incl. internal `_debug`) for a chart on a date.
    Callers strip `_debug` via public_view() before sending to a user."""
    on_date = on_date or date.today()
    inputs = build_day_inputs(chart_data, on_date)
    return compute_concrete_block(
        best_window=best_window,
        steer_clear_window=steer_clear_window,
        language=language,
        personal_lord=personal_lord,  # [perchart-lord]
        **inputs,
    )


__all__ = ["build_day_inputs", "build_concrete_for_chart"]
