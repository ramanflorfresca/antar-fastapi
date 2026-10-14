"""
KP phase 2: sub-sub lords, cuspal links, significator levels, sign type, house ownership.

Everything is derived from the KP chart (kp_chart.compute_kp_chart[_from_jd]) with pure arithmetic; no new ephemeris.
  sub_sub_lord(lon)      the 9-fold Vimshottari subdivision of the sub arc, starting with the sub lord itself
  enrich(chart)          adds `sub_sub_lord` to every cusp and planet
  links(chart, planet)   cusps whose sign/star/sub/sub-sub lord is the planet (a node also stands for its dispositor)
  sig_levels(chart)      {planet: {house: level 1..4}} (1 = planet in the star of an occupant, strongest ... 4 = owner)
"""
from typing import Dict, Iterable, List, Set

from .kp_chart import (VIM_ORDER, VIM_YEARS, VIM_TOTAL, _SUB_SEGMENTS, resolve_sublord)
from .kp_significators import build_house_significators

MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
FIXED = {"Taurus", "Leo", "Scorpio", "Aquarius"}
DUAL = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
NODES = ("Rahu", "Ketu")


def sub_sub_lord(longitude: float) -> str:
    lon = float(longitude) % 360.0
    seg = next((s for s in _SUB_SEGMENTS if s["start"] <= lon < s["end"]), _SUB_SEGMENTS[-1])
    width = seg["end"] - seg["start"]
    start_idx = VIM_ORDER.index(seg["sub_lord"])
    edge = seg["start"]
    for k in range(9):
        lord = VIM_ORDER[(start_idx + k) % 9]
        edge += VIM_YEARS[lord] / VIM_TOTAL * width
        if lon < edge - 1e-12:
            return lord
    return VIM_ORDER[(start_idx + 8) % 9]


def enrich(chart: dict) -> dict:
    """Idempotent: add sub_sub_lord to cusps and planets."""
    for part in ("cusps", "planets"):
        for v in chart[part].values():
            if "sub_sub_lord" not in v:
                v["sub_sub_lord"] = sub_sub_lord(v["longitude"])
    return chart


def sign_type(sign: str) -> str:
    return "movable" if sign in MOVABLE else "fixed" if sign in FIXED else "dual"


def stands_for(chart: dict, planet: str) -> Set[str]:
    """A node acts for itself and for the planet that rules its sign."""
    out = {planet}
    if planet in NODES:
        out.add(chart["planets"][planet]["sign_lord"])
    return out


def links(chart: dict, planet: str, via: Iterable[str] = ("sign", "star", "sub", "sub_sub")) -> List[int]:
    """Cusps (1-12) in which the planet (or what it stands for) is the sign / star / sub / sub-sub lord."""
    enrich(chart)
    who = stands_for(chart, planet)
    key = {"sign": "sign_lord", "star": "star_lord", "sub": "sub_lord", "sub_sub": "sub_sub_lord"}
    out = []
    for h in range(1, 13):
        c = chart["cusps"][h]
        if any(c[key[v]] in who for v in via):
            out.append(h)
    return out


def sig_levels(chart: dict) -> Dict[str, Dict[int, int]]:
    """For each planet the strongest level at which it signifies each house (1 strongest, 4 weakest)."""
    hs = build_house_significators(chart)
    out: Dict[str, Dict[int, int]] = {}
    for h, d in hs.items():
        for lvl, key in ((1, "L1"), (2, "L2"), (3, "L3"), (4, "L4")):
            for p in d[key]:
                out.setdefault(p, {})
                out[p][h] = min(out[p].get(h, 9), lvl)
    return out


def owned_houses(chart: dict, planet: str) -> List[int]:
    return [h for h in range(1, 13) if chart["cusps"][h]["sign_lord"] == planet]
