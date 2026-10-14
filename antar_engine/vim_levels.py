"""
Vimshottari to the fourth level: major (MD), sub (AD), pratyantara (PD) and sookshma (SD) lords on a date.
MD and AD come from the stored rows; PD and SD are the standard proportional subdivisions:
a period of length L ruled by lord X is split among the nine lords in Vimshottari order starting with X, each taking
L * years(lord) / 120. Used for week-level and day-level timing and to decide when a remedy is live.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from antar_engine import constants

SEQ = constants.VIMSOTTARI_SEQUENCE
YEARS = constants.VIMSOTTARI_YEARS


def _dt(v) -> Optional[datetime]:
    try:
        d = v if isinstance(v, datetime) else datetime.fromisoformat(str(v)[:19].replace("Z", ""))
        return d.replace(tzinfo=None)
    except Exception:
        return None


def parse_rows(rows) -> List[dict]:
    out = []
    for r in rows or []:
        s, e = _dt(r.get("start_date") or r.get("start")), _dt(r.get("end_date") or r.get("end"))
        lord = r.get("planet_or_sign") or r.get("lord_or_sign") or r.get("planet")
        lvl = str(r.get("level") or r.get("type") or "").lower()
        level = "md" if lvl in ("1", "mahadasha") else "ad" if lvl in ("2", "antardasha", "bhukti") else None
        if s and e and lord and level:
            out.append({"level": level, "lord": lord, "start": s, "end": e})
    return out


def subdivide(lord: str, start: datetime, end: datetime) -> List[dict]:
    total = (end - start).total_seconds()
    i0 = SEQ.index(lord)
    out, t = [], start
    for k in range(9):
        p = SEQ[(i0 + k) % 9]
        t2 = t + timedelta(seconds=total * YEARS[p] / 120.0)
        out.append({"lord": p, "start": t, "end": t2})
        t = t2
    return out


def running_lords(rows: List[dict], when: datetime) -> Dict[str, Optional[str]]:
    """{'md','ad','pd','sd'} lords on `when` (rows already parsed by parse_rows)."""
    md = next((r for r in rows if r["level"] == "md" and r["start"] <= when < r["end"]), None)
    ad = next((r for r in rows if r["level"] == "ad" and r["start"] <= when < r["end"]), None)
    out = {"md": md["lord"] if md else None, "ad": ad["lord"] if ad else None, "pd": None, "sd": None}
    if ad:
        for pd in subdivide(ad["lord"], ad["start"], ad["end"]):
            if pd["start"] <= when < pd["end"]:
                out["pd"] = pd["lord"]
                for sd in subdivide(pd["lord"], pd["start"], pd["end"]):
                    if sd["start"] <= when < sd["end"]:
                        out["sd"] = sd["lord"]
                        break
                break
    return out


def lords_in_window(rows: List[dict], start: datetime, end: datetime, levels=("md", "ad", "pd"),
                    step_days: int = 3) -> Set[str]:
    """Planets whose period at any of `levels` runs at some moment inside [start, end]."""
    seen: Set[str] = set()
    t = start
    while t <= end:
        r = running_lords(rows, t)
        seen |= {r[l] for l in levels if r.get(l)}
        t += timedelta(days=step_days)
    return seen


def rows_from_moon(moon_longitude: float, birth: datetime, mds: int = 11) -> List[dict]:
    """Full Vimshottari MD and AD rows computed from the Moon's sidereal longitude and the birth moment, so the four
    levels are always available even when no rows are stored. (Same arithmetic as vimsottari.py: the balance of the
    first major period is what remains of the Moon's nakshatra; years of 365.25 days.)"""
    seg = 360.0 / 27
    nk = int((moon_longitude % 360) // seg)
    frac = ((moon_longitude % 360) % seg) / seg
    lords = constants.NAKSHATRA_LORDS
    i0 = SEQ.index(lords[nk])
    first = YEARS[SEQ[i0]]
    start = birth - timedelta(days=first * frac * 365.25)          # the major period began before birth
    rows, t = [], start
    for i in range(mds):
        lord = SEQ[(i0 + i) % 9]
        end = t + timedelta(days=YEARS[lord] * 365.25)
        rows.append({"level": "md", "lord": lord, "start": t, "end": end})
        for sub in subdivide(lord, t, end):
            rows.append({"level": "ad", "lord": sub["lord"], "start": sub["start"], "end": sub["end"]})
        t = end
    return rows
