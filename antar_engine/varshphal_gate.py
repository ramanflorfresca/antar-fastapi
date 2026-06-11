"""
antar_engine/varshphal_gate.py
==============================
Varshphal (Tajika solar-return) year-gate — Stage-3 candidate for the event
convergence engine (founder ruling 2026-06-11: "Varshphal GATES the year,
wired then measured on the harness before it counts as a lock").

STATUS: SHADOW VOTE. Nothing here affects lock counts until the harness
shows separation at true event dates vs background (the double-transit and
Muntha-only formulations both measured AT background and are parked).

v1 vote elements (declared simplifications — founder refines):
  - solar return moment: transiting sidereal Sun returns to its natal
    sidereal longitude nearest the birthday of the given year (bisection).
  - varsha lagna: ascendant at that moment, birth coordinates.
  - muntha: natal lagna + completed years (sign-level arithmetic).
  - year vote for an event: ANY of
      (a) varsha lagna falls in an event house counted from the NATAL lagna,
      (b) the varsha-lagna lord is a Stage-1 significator of the event,
      (c) the muntha lord is a Stage-1 significator of the event.

Needs swisseph (ephemeris + houses). Where unavailable the gate returns
None and the resolver records "varshphal: unavailable" — never guesses.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

SIGN_RULER_IDX = {0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun",
                  5: "Mercury", 6: "Venus", 7: "Mars", 8: "Jupiter",
                  9: "Saturn", 10: "Saturn", 11: "Jupiter"}
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
              "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

_SR_CACHE: Dict = {}


def _swe():
    import swisseph as swe
    try:
        from antar_engine.lahiri_gate import ensure_lahiri_sid_mode
        ensure_lahiri_sid_mode()
    except Exception:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe


def _sun_lon(swe, jd: float) -> float:
    return swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)[0][0]


def solar_return_jd(natal_sun_lon: float, birth_jd: float,
                    year_index: int) -> Optional[float]:
    """JD of the solar return `year_index` years after birth (bisection on
    sidereal Sun longitude; handles the 0/360 wrap)."""
    key = (round(natal_sun_lon, 4), round(birth_jd, 4), year_index)
    if key in _SR_CACHE:
        return _SR_CACHE[key]
    try:
        swe = _swe()
    except Exception:
        return None
    approx = birth_jd + year_index * 365.2422
    lo, hi = approx - 3.0, approx + 3.0

    def diff(jd):
        d = (_sun_lon(swe, jd) - natal_sun_lon + 180.0) % 360.0 - 180.0
        return d

    try:
        dlo = diff(lo)
        # widen if the root is outside the bracket
        for _ in range(4):
            if dlo <= 0 <= diff(hi):
                break
            lo -= 2.0
            hi += 2.0
            dlo = diff(lo)
        for _ in range(40):
            mid = (lo + hi) / 2.0
            if diff(mid) < 0:
                lo = mid
            else:
                hi = mid
        _SR_CACHE[key] = (lo + hi) / 2.0
        return _SR_CACHE[key]
    except Exception:
        return None


def varsha_snapshot(chart_data: dict, chart_record: dict,
                    year_index: int) -> Optional[dict]:
    """Varsha lagna + muntha for the year starting at the year_index-th
    solar return. None when ephemeris/coords are unavailable."""
    try:
        swe = _swe()
    except Exception:
        return None
    cd = chart_data or {}
    natal_sun = (cd.get("planets") or {}).get("Sun") or {}
    sun_lon = natal_sun.get("longitude")
    birth_jd = cd.get("birth_jd")
    lat = (chart_record or {}).get("latitude")
    lng = (chart_record or {}).get("longitude")
    lagna = cd.get("lagna") or {}
    lagna_idx = lagna.get("sign_index")
    if sun_lon is None or not birth_jd or lat is None or lng is None \
            or lagna_idx is None:
        return None
    sr_jd = solar_return_jd(float(sun_lon), float(birth_jd), year_index)
    if not sr_jd:
        return None
    try:
        # sidereal ascendant at the solar-return moment, birth coords
        ayan = swe.get_ayanamsa_ut(sr_jd)
        houses = swe.houses(sr_jd, float(lat), float(lng), b"W")
        asc_tropical = houses[1][0]
        asc_sid = (asc_tropical - ayan) % 360.0
        vl_idx = int(asc_sid / 30) % 12
    except Exception:
        return None
    muntha_sign = (int(lagna_idx) + year_index) % 12
    return {
        "year_index": year_index,
        "sr_jd": sr_jd,
        "varsha_lagna_idx": vl_idx,
        "varsha_lagna": SIGN_NAMES[vl_idx],
        "varsha_lagna_lord": SIGN_RULER_IDX[vl_idx],
        "muntha_sign": SIGN_NAMES[muntha_sign],
        "muntha_lord": SIGN_RULER_IDX[muntha_sign],
        "natal_lagna_idx": int(lagna_idx),
    }


def year_vote(event_houses: List[int], significators: Set[str],
              snap: Optional[dict]) -> Optional[dict]:
    """v1 Varshphal vote for one event in one varsha year. None = no data."""
    if not snap:
        return None
    hs = set(int(h) for h in event_houses or [])
    vl_house = ((snap["varsha_lagna_idx"] - snap["natal_lagna_idx"]) % 12) + 1
    conds = []
    if vl_house in hs:
        conds.append(f"varsha lagna in event house {vl_house}")
    if snap["varsha_lagna_lord"] in (significators or set()):
        conds.append(f"varsha-lagna lord {snap['varsha_lagna_lord']} "
                     "is an event significator")
    if snap["muntha_lord"] in (significators or set()):
        conds.append(f"muntha lord {snap['muntha_lord']} "
                     "is an event significator")
    return {"vote": bool(conds), "conditions": conds,
            "varsha_lagna": snap["varsha_lagna"],
            "varsha_lagna_house": vl_house,
            "muntha": snap["muntha_sign"],
            "year_index": snap["year_index"]}


def vote_for_window(chart_data: dict, chart_record: dict,
                    birth_date: datetime, window_start: str,
                    event_houses: List[int],
                    significators: Set[str]) -> Optional[dict]:
    """Vote for the varsha year containing window_start. None = unavailable."""
    try:
        ws = datetime.strptime(str(window_start)[:10], "%Y-%m-%d")
        year_index = int((ws - birth_date).days // 365.2422)
    except (ValueError, TypeError):
        return None
    snap = varsha_snapshot(chart_data, chart_record, year_index)
    return year_vote(event_houses, significators, snap)
