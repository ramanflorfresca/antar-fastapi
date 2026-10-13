"""
D-10 (Dasamsa) layer for career, funding and money timing, deterministic.

Per Boney (Predicting Major Life Events 2.2-2.3, career chapter): read the Chara period
sign as a house counted from the D-10 lagna; a planet in a D-10 house colours its period;
the D-10 2nd/10th/11th are gain houses, 3rd/6th/8th mark breaks or job instability, the
12th loss; when the running Chara MD sign IS the D-10 lagna sign, the D-10 chart is the
"lagna chart" for the whole period. Vimshottari agreement = period lord is a D-10
2nd/10th/11th lord or sits in the D-10 10th. Rule ids tagged; no accuracy gate.
Funding (other people's money) is read from the D-10 8th plus the 2nd/11th lords.
"""
from datetime import datetime
from typing import Dict, List, Optional

from antar_engine.jaimini_engine import (Planet, SIGN_NAMES, SIGN_LORDS, compute_chara_dasha,
                                         get_rashi_drishti)

GAIN = {2, 10, 11}
BREAK = {3, 6, 8}
LOSS = {12}
BOUNDARY_WARN_DEG = 1.0  # lagna within this many degrees of a D-10 division edge


def d10_sign(lon: float) -> int:
    s = int(lon // 30) % 12
    k = int((lon % 30) // 3)
    return (s + k) % 12 if s % 2 == 0 else (s + 8 + k) % 12


def lagna_sensitivity(lagna_lon: float) -> dict:
    """How far (degrees / approx minutes of birth time) the D-10 lagna is from flipping."""
    off = (lagna_lon % 30) % 3
    edge = min(off, 3 - off)
    return {"degrees_to_edge": round(edge, 2), "approx_minutes_of_birth_time": round(edge * 4, 1),
            "fragile": edge < BOUNDARY_WARN_DEG}


def d10_chart(lagna_lon: float, planets: Dict[str, Planet]) -> dict:
    lg = d10_sign(lagna_lon)
    pos = {n: d10_sign(p.degree) for n, p in planets.items()}
    occ: Dict[int, List[str]] = {}
    for n, s in pos.items():
        occ.setdefault(s, []).append(n)
    house_sign = lambda h: (lg + h - 1) % 12
    lord = lambda h: SIGN_LORDS[house_sign(h)]
    return {"lagna": lg, "pos": pos, "occ": occ, "house_sign": house_sign, "lord": lord,
            "sensitivity": lagna_sensitivity(lagna_lon)}


def _rules(ch: dict, sign: int, md_sign: int) -> List[str]:
    lg = ch["lagna"]
    h = (sign - lg) % 12 + 1
    out = [f"D10.period_sign_is_house_{h}"]
    if h in GAIN:
        out.append("D10.gain_house_period")
    if h in BREAK:
        out.append("D10.break_or_instability_house_period")
    if h in LOSS:
        out.append("D10.loss_house_period")
    for pl in ch["occ"].get(sign, []):
        out.append(f"D10.occupant_{pl}")
    for gh in (2, 10, 11):
        if ch["pos"].get(ch["lord"](gh)) == sign:
            out.append(f"D10.lord_of_{gh}_in_period_sign")
        gs = ch["house_sign"](gh)
        if gs != sign and gs in get_rashi_drishti(sign):
            out.append(f"D10.period_sign_aspects_house_{gh}")
    if h == 8 or ch["pos"].get(ch["lord"](8)) == sign:
        out.append("D10.other_peoples_money_8th")
    if md_sign == lg:
        out.append("D10.major_period_is_d10_lagna")
    return out


def d10_windows(lagna_sign: int, lagna_lon: float, planets: Dict[str, Planet],
                birth_date: datetime, start: datetime, end: datetime,
                vim_rows: Optional[list] = None) -> dict:
    ch = d10_chart(lagna_lon, planets)
    sig_planets = {ch["lord"](h) for h in (2, 10, 11)} | set(ch["occ"].get(ch["house_sign"](10), []))
    funding_planets = sig_planets | {ch["lord"](8)}
    mds = compute_chara_dasha(lagna_sign, planets, birth_date, num_cycles=3)
    wins = []
    for md in mds:
        for ad in md.sub_periods:
            if ad.end_date < start or ad.start_date > end:
                continue
            rules = _rules(ch, ad.sign, md.sign)
            mid = ad.start_date + (ad.end_date - ad.start_date) / 2
            vim = None
            for r in vim_rows or []:
                who = r.get("planet")
                if r["start_date"] <= mid < r["end_date"] and who in sig_planets:
                    vim = who
            h = (ad.sign - ch["lagna"]) % 12 + 1
            wins.append({"start": ad.start_date, "end": ad.end_date, "major": SIGN_NAMES[md.sign],
                         "sub": SIGN_NAMES[ad.sign], "d10_house": h, "rules": rules,
                         "vimshottari_agrees": vim,
                         "gain_score": sum(r.startswith(("D10.gain", "D10.lord_of", "D10.period_sign_aspects"))
                                           for r in rules) + (1 if vim else 0),
                         "funding_signal": any(r in ("D10.other_peoples_money_8th",) or
                                               r.startswith("D10.lord_of_11") for r in rules)})
    return {"d10_lagna": SIGN_NAMES[ch["lagna"]], "sensitivity": ch["sensitivity"],
            "planets_in_d10": {n: SIGN_NAMES[s] for n, s in ch["pos"].items()},
            "gain_lords": sorted(sig_planets), "funding_planets": sorted(funding_planets),
            "windows": wins}
