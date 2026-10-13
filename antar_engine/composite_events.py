"""
Composite event engine after Marc Boney, "Predicting Major Life Events" (Rao school).

Boney's order: static promise -> dasha confluence (Vimshottari AND Chara) -> transits
last (Jupiter AND Saturn both on the event's house/lord, from lagna or Moon). This
module layers Vimshottari and the double transit onto the Chara windows from
jaimini_rao_events and grades each by how many independent layers agree:
  chara (>=min Rao rules) + vimshottari (period lord is an event significator)
  + double transit (Jupiter and Saturn both touch a target sign).
Tier = number of layers, reported as "triple" / "double" / "single". A count, not a
probability. Boney predicts only positive events; negative cautions stay in Rao's engine.
Deterministic, rule-id tagged. Not gated on accuracy by owner decision.
"""
from datetime import datetime
from typing import Dict, List, Optional

from antar_engine.jaimini_engine import Planet, SIGN_NAMES
from antar_engine.jaimini_rao_events import predict_windows, Chart

# Graha drishti (houses aspected counted from own sign, incl. 7th)
_JUP = (5, 7, 9)
_SAT = (3, 7, 10)


def _grahadrishti(sign: int, houses) -> set:
    return {(sign + h - 1) % 12 for h in houses}


def _touch(planet_sign: int, houses, target: int) -> bool:
    return planet_sign == target or target in _grahadrishti(planet_sign, houses)


def _slow_signs(when: datetime) -> Optional[Dict[str, int]]:
    try:
        import swisseph as swe
    except ImportError:
        return None
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(when.year, when.month, when.day, 12.0)
    f = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
    return {n: int(swe.calc_ut(jd, i, f)[0][0] // 30) % 12
            for n, i in (("Jupiter", swe.JUPITER), ("Saturn", swe.SATURN))}


def _targets(event: str, lagna: int, lord_sign: Dict[str, int]) -> List[int]:
    h = lambda n: (lagna + n - 1) % 12
    return {
        "marriage": [h(1), h(7), lord_sign["7L"]],
        "children": [h(5), h(9), lord_sign["5L"]],
        "education": [h(5), lord_sign["5L"]],
        "career": [h(10), lord_sign["10L"]],
    }[event]


def double_transit(event: str, c: Chart, moon_sign: int, when: datetime) -> Optional[dict]:
    sl = _slow_signs(when)
    if not sl:
        return None
    lord_sign = {"7L": c.planets[c.lord7].sign, "5L": c.planets[c.lord5].sign,
                 "10L": c.planets[c.lord10].sign}
    for base, lg in (("lagna", c.lagna), ("Moon", moon_sign)):
        # targets counted from lagna for lagna-base; from Moon for Moon-base
        tg = _targets(event, lg, lord_sign)
        for t in tg:
            if _touch(sl["Jupiter"], _JUP, t) and _touch(sl["Saturn"], _SAT, t):
                return {"base": base, "target": SIGN_NAMES[t],
                        "jupiter": SIGN_NAMES[sl["Jupiter"]], "saturn": SIGN_NAMES[sl["Saturn"]]}
    return None


def composite_windows(lagna_sign: int, lagna_longitude: float, planets: Dict[str, Planet],
                      birth_date: datetime, start: datetime, end: datetime,
                      vim_rows: Optional[list] = None, min_rules: int = 2) -> List[dict]:
    c = Chart(lagna_sign, lagna_longitude, planets)
    moon = planets["Moon"].sign
    out = []
    for w in predict_windows(lagna_sign, lagna_longitude, planets, birth_date, start, end,
                             vim_rows=vim_rows, with_transits=False, min_rules=min_rules):
        mid = w["start"] + (w["end"] - w["start"]) / 2
        evs = []
        for e in w["events"]:
            dt = double_transit(e["event"], c, moon, mid)
            layers = ["chara"] + (["vimshottari"] if e["vimshottari_agrees"] else []) \
                + (["double_transit"] if dt else [])
            evs.append({**e, "double_transit": dt, "layers": layers,
                        "tier": {3: "triple", 2: "double", 1: "single"}[len(layers)]})
        evs.sort(key=lambda e: (-len(e["layers"]), -e["score"]))
        out.append({**w, "events": evs})
    return out
