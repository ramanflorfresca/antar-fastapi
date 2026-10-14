"""Sidereal (Lahiri) sign of each transiting planet on a date, for activation clauses. Rahu is the mean node; Ketu is opposite."""
from datetime import date
from functools import lru_cache
from typing import Dict

_IDS = {"Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4, "Jupiter": 5, "Saturn": 6}


@lru_cache(maxsize=4096)
def transit_longitudes(d: date) -> Dict[str, float]:
    """Sidereal (Lahiri) longitude 0-360 of each transiting planet at noon UT on a date; Rahu mean node, Ketu opposite."""
    import swisseph as swe
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(d.year, d.month, d.day, 12.0)
    flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
    out = {p: swe.calc_ut(jd, i, flags)[0][0] % 360.0 for p, i in _IDS.items()}
    rahu = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0] % 360.0
    out["Rahu"], out["Ketu"] = rahu, (rahu + 180.0) % 360.0
    return out


@lru_cache(maxsize=4096)
def transit_longitudes_tropical(d: date) -> Dict[str, float]:
    """Tropical (Sayana) longitude 0-360, for sources that use the tropical zodiac (e.g. Butaney)."""
    import swisseph as swe
    jd = swe.julday(d.year, d.month, d.day, 12.0)
    flags = swe.FLG_SWIEPH
    out = {p: swe.calc_ut(jd, i, flags)[0][0] % 360.0 for p, i in _IDS.items()}
    rahu = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0] % 360.0
    out["Rahu"], out["Ketu"] = rahu, (rahu + 180.0) % 360.0
    return out


@lru_cache(maxsize=4096)
def transit_signs(d: date) -> Dict[str, int]:
    return {p: int(lon // 30) % 12 for p, lon in transit_longitudes(d).items()}
