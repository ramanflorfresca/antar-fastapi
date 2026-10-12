"""
antar_engine/daily_double_transit.py — Double Transit as a DAILY confidence input.

Reuses the KN Rao double_transit engine (Saturn+Jupiter both on a point, Moon
frame primary, lagna confirm) at day resolution.

DESIGN (confidence, never magnitude)
  * Targets = houses the running antardasha / pratyantar lords RULE or OCCUPY,
    intersected with today's LIT house (Moon from lagna). Anything else is
    "not read" — a slow, near-constant signal must not vote every day.
  * Because the target is the Moon's own house today, its valence is NOT
    independent of the Moon axis. It therefore does not add a layer: the caller
    folds it into the single Moon axis (same fix as nakshatra + moon_house).
  * Valence is the house's nature (6/8/12 pressure, else opportunity). Only
    `fires` / `likely` count; weak / none is not a vote.

Pure, deterministic, never raises. Ephemeris positions are cached per date
and can be injected for tests.
"""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from typing import Any, Dict, Iterable, Optional

from antar_engine.double_transit import (
    SIGNS, SIGN_INDEX, SIGN_LORDS, dt_state_for_event, sidereal_sign_indices,
)

_DUSTHANA = {6, 8, 12}
_NEEDED = ("Saturn", "Jupiter", "Mars", "Moon")


@lru_cache(maxsize=512)
def _positions_cached(day_iso: str) -> tuple:
    d = date.fromisoformat(day_iso)
    return tuple(sorted(sidereal_sign_indices(d, _NEEDED).items()))


def _lagna_idx(chart_data: dict) -> Optional[int]:
    lag = (chart_data or {}).get("lagna") or {}
    si = lag.get("sign_index")
    if isinstance(si, int):
        return si % 12
    return SIGN_INDEX.get(lag.get("sign"))


def lord_houses(chart_data: dict, planet: str) -> set:
    """Houses (1-12) `planet` rules or occupies in the natal chart."""
    li = _lagna_idx(chart_data)
    if li is None or not planet:
        return set()
    planet = str(planet).strip().title()
    houses = set()
    for i, sign in enumerate(SIGNS):
        if SIGN_LORDS.get(sign) == planet:
            houses.add((i - li) % 12 + 1)
    pd_ = ((chart_data or {}).get("planets") or {}).get(planet) or {}
    si = pd_.get("sign_index")
    si = si % 12 if isinstance(si, int) else SIGN_INDEX.get(pd_.get("sign"))
    if si is not None:
        houses.add((si - li) % 12 + 1)
    return houses


def daily_double_transit(chart_data: dict, lords: Iterable[str],
                         lit_house: Optional[int],
                         target_date: "date | datetime",
                         positions: Optional[dict] = None) -> Dict[str, Any]:
    """Return {available, house, verdict, polarity}. `available` is False when
    the lit house is not one of the running lords' houses, or on any failure."""
    try:
        if not lit_house or not chart_data:
            return {"available": False}
        targets = set()
        for lord in lords:
            targets |= lord_houses(chart_data, lord)
        if lit_house not in targets:
            return {"available": False}
        if positions is None:
            d = target_date.date() if isinstance(target_date, datetime) else target_date
            positions = dict(_positions_cached(d.isoformat()))
        st = dt_state_for_event(chart_data, [lit_house], target_date,
                                positions=positions)
        verdict = st.get("classical_verdict", "none")
        if verdict not in ("fires", "likely"):
            return {"available": False, "house": lit_house, "verdict": verdict}
        return {"available": True, "house": lit_house, "verdict": verdict,
                "polarity": -1 if lit_house in _DUSTHANA else 1}
    except Exception as e:  # fail-open: layer simply not read
        return {"available": False, "error": str(e)[:120]}


def attach_to_precision(precision: dict, chart_data: dict, lords: Iterable[str],
                        target_date, positions: Optional[dict] = None) -> dict:
    """Write dt_direction / dt_verdict onto a precision dict (in place) for
    build_day_signals. No-op when the layer is not read."""
    if not precision:
        return precision
    r = daily_double_transit(chart_data, lords,
                             precision.get("moon_house_from_lagna"),
                             target_date, positions=positions)
    if r.get("available"):
        precision["dt_direction"] = "supportive" if r["polarity"] > 0 else "friction"
        precision["dt_verdict"] = r["verdict"]
    return precision
