"""Sidereal (Lahiri) sign of each transiting planet on a date, for activation clauses. Rahu is the mean node; Ketu is opposite."""
from datetime import date
from functools import lru_cache
from typing import Dict

_IDS = {"Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4, "Jupiter": 5, "Saturn": 6}


@lru_cache(maxsize=4096)
def transit_signs(d: date) -> Dict[str, int]:
    import swisseph as swe
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(d.year, d.month, d.day, 12.0)
    flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
    out = {p: int(swe.calc_ut(jd, i, flags)[0][0] // 30) % 12 for p, i in _IDS.items()}
    rahu = int(swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0] // 30) % 12
    out["Rahu"], out["Ketu"] = rahu, (rahu + 6) % 12
    return out
