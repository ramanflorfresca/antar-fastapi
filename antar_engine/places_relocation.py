"""
antar_engine/places_relocation.py
─────────────────────────────────────────────────────────────────────────────
PLACES — relocation chart math.  Phase 1.

Re-cast a natal chart for a new geographic location.  Birth date + time are
unchanged; only the place changes, which moves the ascendant and therefore
every whole-sign house cusp and each planet's house.

SIDEREAL (Lahiri).  WHOLE-SIGN houses (consistent with the rest of Antar).

What changes:  lagna, house cusps, which house each planet sits in.
What does NOT change:  zodiac longitudes, nakshatras, dasha schedule,
divisional placements.
"""

from __future__ import annotations

from typing import Optional

try:
    import swisseph as swe
    _SWE_AVAILABLE = True
except Exception:                                       # pragma: no cover
    swe = None
    _SWE_AVAILABLE = False

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}


def _natal_lagna_index(natal_chart: dict) -> Optional[int]:
    lagna = natal_chart.get("lagna")
    if isinstance(lagna, dict):
        si = lagna.get("sign_index")
        if si is not None:
            return int(si)
        sign = lagna.get("sign")
        if sign in SIGN_INDEX:
            return SIGN_INDEX[sign]
    sign = natal_chart.get("lagna_sign")
    if sign in SIGN_INDEX:
        return SIGN_INDEX[sign]
    if isinstance(lagna, str) and lagna in SIGN_INDEX:
        return SIGN_INDEX[lagna]
    return None


def _planet_sign_index(rec: dict) -> Optional[int]:
    si = rec.get("sign_index")
    if si is not None:
        try:
            return int(si)
        except (TypeError, ValueError):
            pass
    lon = rec.get("longitude")
    if lon is not None:
        try:
            return int((float(lon) % 360.0) // 30.0)
        except (TypeError, ValueError):
            pass
    sign = rec.get("sign")
    if sign in SIGN_INDEX:
        return SIGN_INDEX[sign]
    return None


def compute_relocated_lagna_index(birth_jd: float, lat: float, lon: float) -> Optional[int]:
    """Sidereal ascendant sign index at a new place, or None on failure."""
    if not _SWE_AVAILABLE or birth_jd is None:
        return None
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        _cusps, ascmc = swe.houses_ex(birth_jd, lat, lon, b"W", swe.FLG_SIDEREAL)
        asc_lon = ascmc[0] % 360.0
        return int(asc_lon // 30.0)
    except Exception:
        return None


def compute_relocated_chart(natal_chart: dict, lat: float, lon: float) -> dict:
    """
    Re-cast the natal chart for (lat, lon).

    Returns:
        {
          "natal_lagna":            "Capricorn",
          "relocated_lagna":        "Aries",
          "relocated_lagna_index":  0,
          "lagna_shift_houses":     3,                 # 0..11
          "relocated_house_cusps":  ["Aries", ... 12 signs],
          "relocated_planet_houses": {                # only planets that moved
              "Saturn": {"natal_house": 10, "relocated_house": 7, "delta": -3},
              ...
          },
          "_available": True
        }
    """
    birth_jd = natal_chart.get("birth_jd")
    natal_idx = _natal_lagna_index(natal_chart)
    reloc_idx = compute_relocated_lagna_index(birth_jd, lat, lon)

    natal_lagna_name = SIGNS[natal_idx] if natal_idx is not None else None

    if reloc_idx is None:
        # Ephemeris unavailable — degrade gracefully without inventing a shift.
        return {
            "natal_lagna": natal_lagna_name,
            "relocated_lagna": natal_lagna_name,
            "relocated_lagna_index": natal_idx,
            "lagna_shift_houses": 0,
            "relocated_house_cusps": (
                [SIGNS[(natal_idx + h) % 12] for h in range(12)] if natal_idx is not None else []
            ),
            "relocated_planet_houses": {},
            "_available": False,
        }

    relocated_house_cusps = [SIGNS[(reloc_idx + h) % 12] for h in range(12)]

    lagna_shift = ((reloc_idx - natal_idx) % 12) if natal_idx is not None else 0

    planet_houses: dict[str, dict] = {}
    for planet, rec in (natal_chart.get("planets", {}) or {}).items():
        psi = _planet_sign_index(rec)
        if psi is None:
            continue
        relocated_house = ((psi - reloc_idx) % 12) + 1
        natal_house = rec.get("house")
        if natal_house is None and natal_idx is not None:
            natal_house = ((psi - natal_idx) % 12) + 1
        delta = None
        if natal_house is not None:
            delta = relocated_house - int(natal_house)
        # Only report planets whose house actually changed.
        if natal_house is None or relocated_house != int(natal_house):
            planet_houses[planet] = {
                "natal_house": int(natal_house) if natal_house is not None else None,
                "relocated_house": relocated_house,
                "delta": delta,
            }

    return {
        "natal_lagna": natal_lagna_name,
        "relocated_lagna": SIGNS[reloc_idx],
        "relocated_lagna_index": reloc_idx,
        "lagna_shift_houses": lagna_shift,
        "relocated_house_cusps": relocated_house_cusps,
        "relocated_planet_houses": planet_houses,
        "_available": True,
    }
