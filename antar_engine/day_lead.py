"""[day-lead 2026-10-16] What the day is ABOUT, from the Moon's star lord and sub lord (KP), read against THIS chart.

The Moon keeps one sign for about two and a half days, so a day lead built from the Moon's house repeats for two or three days.
The star (nakshatra) changes about daily and the sub lord within the day, so they are what makes one day differ from the next:
the star lord decides what the day is about, the sub lord whether it goes through. A lord signifies the houses it OWNS and the
house it SITS in (a node: where it sits and where its sign lord sits). Each area of life has houses that are for it and against
it (data/day_lead.json, owner-editable); the day's highlight is the area the two lords support most, the watch-point the area they
press on most. Pure and deterministic; whole-sign houses from the lagna (an approximation of KP's cusps). No planet or house names
in the text."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

_PATH = os.path.join(os.path.dirname(__file__), "data", "day_lead.json")
_CACHE: dict = {}
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
RULER = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus",
         "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}


def _houses(spec: dict) -> tuple:
    """(favourable, unfavourable) houses for an area: the KP rule table's own sets for its question type (the book rules)."""
    try:
        from antar_engine.kp.kp_significators import QUESTION_TYPES
        qt = QUESTION_TYPES.get(spec.get("kp_type")) or {}
        return list(qt.get("favour") or []), list(qt.get("against") or [])
    except Exception:
        return [], []


def _data() -> dict:
    if not _CACHE:
        try:
            with open(_PATH, encoding="utf-8") as fh:
                _CACHE.update(json.load(fh))
        except Exception as e:
            print(f"[day-lead] data unavailable: {e}")
            _CACHE["_empty"] = True
    return _CACHE


def _house_of_sign(lagna: str, sign: str) -> Optional[int]:
    try:
        return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1
    except ValueError:
        return None


def significators(planet: str, chart_data: dict) -> List[int]:
    """The houses this planet signifies in this chart: those it owns and the one it sits in (a node: its own house and its sign lord's)."""
    cd = chart_data if isinstance(chart_data, dict) else {}
    lagna = (cd.get("lagna") or {}).get("sign")
    pl = cd.get("planets") or {}
    if not lagna or planet not in pl:
        return []
    out = []
    for h in range(1, 13):
        sign = SIGNS[(SIGNS.index(lagna) + h - 1) % 12]
        if RULER.get(sign) == planet and planet not in ("Rahu", "Ketu"):
            out.append(h)
    seat = (pl.get(planet) or {}).get("house") or _house_of_sign(lagna, (pl.get(planet) or {}).get("sign"))
    if seat:
        out.append(int(seat))
    if planet in ("Rahu", "Ketu"):
        disp = RULER.get((pl.get(planet) or {}).get("sign"))
        if disp and disp != planet and disp in pl:
            out += significators(disp, cd)
    return sorted(set(out))


def lead(chart_data: dict, star_lord: str, sub_lord: Optional[str], lang: str = "en") -> Optional[dict]:
    """{highlight, caution, scores, star_lord, sub_lord, houses}: the day's highlight and watch-point, or None with no usable lord."""
    d = _data()
    if d.get("_empty") or not star_lord:
        return None
    sw, bw = float(d.get("star_weight", 2)), float(d.get("sub_weight", 1))
    hs = {"star": significators(star_lord, chart_data), "sub": significators(sub_lord, chart_data) if sub_lord else []}
    if not hs["star"] and not hs["sub"]:
        return None
    scores: Dict[str, float] = {}
    for key, spec in d["domains"].items():
        good, bad = _houses(spec)
        if not good and not bad:
            continue
        sc = 0.0
        for role, w in (("star", sw), ("sub", bw)):
            # share of the area's own for / against houses the lord touches, so an area with many houses (work) does not win by size
            for h in hs[role]:
                sc += w * ((1 / len(good) if h in good else 0) - (1 / len(bad) if h in bad else 0))
        scores[key] = sc
    if not scores:
        return None
    top = max(scores, key=lambda k: (scores[k], k))
    low = min(scores, key=lambda k: (scores[k], k))
    out = {"star_lord": star_lord, "sub_lord": sub_lord, "houses": hs, "scores": scores, "highlight": None, "caution": None}
    if scores[top] > 0:
        s = d["domains"][top]
        out["highlight"] = {"area": top, "label": s["label"], "event": s["up"], "text": d["highlight"].format(label=s["label"], event=s["up"])}
    if scores[low] < 0:
        s = d["domains"][low]
        out["caution"] = {"area": low, "label": s["label"], "event": s["down"], "text": d["caution"].format(label=s["label"], event=s["down"])}
    out["text"] = " ".join(x["text"] for x in (out["highlight"], out["caution"]) if x) or d["quiet"]
    return out
