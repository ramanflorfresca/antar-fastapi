"""
Deterministic Parashari event engine on the Vimshottari dasha (BPHS principles as taught in
the owner's library: Raman, P.V.R. Narasimha Rao, Boney's composite method). No LLM.

For each Vimshottari antardasha (MD lord + AD lord) and event we ask:
  1. Are the period lords SIGNIFICATORS of the event? (house lords, occupants, aspectors of the
     event house, natural karakas; nodes act for their sign lord and conjunct planets.)
  2. Does the D-10 back the career/money reading? (period lord is lord/occupant of D-10 10th)
  3. Do Jupiter AND Saturn both touch the event house/lord by transit (from lagna or Moon)?
Strength: both lords primary = "strong"; primary + support = "supported"; one primary = "partial";
a transit confirmation lifts the tier by one layer. Caution = AD lord rules 6/8/12 and is not
also a primary significator. Events: marriage, career, money, study. Rule ids tagged.
"""
from datetime import datetime
from typing import Dict, List, Optional

from antar_engine.jaimini_engine import Planet, SIGN_NAMES, SIGN_LORDS
from antar_engine.d10_layer import d10_chart
from antar_engine.composite_events import _slow_signs, _touch, _JUP, _SAT

GRAHA_ASPECT = {"Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10)}
LORD = SIGN_LORDS  # Parashari: Mars owns Scorpio, Saturn Aquarius
NODES = ("Rahu", "Ketu")


class PChart:
    def __init__(self, lagna_sign: int, lagna_lon: float, planets: Dict[str, Planet]):
        self.lagna, self.planets = lagna_sign, planets
        self.moon = planets["Moon"].sign
        self.d10 = d10_chart(lagna_lon, planets)

    def sign(self, h): return (self.lagna + h - 1) % 12
    def lord(self, h): return LORD[self.sign(h)]
    def occupants(self, h): return [n for n, p in self.planets.items() if p.sign == self.sign(h)]

    def aspectors(self, h):
        tgt, out = self.sign(h), []
        for n, p in self.planets.items():
            if n in NODES: continue
            houses = GRAHA_ASPECT.get(n, (7,))
            if any((p.sign + k - 1) % 12 == tgt for k in houses) and p.sign != tgt:
                out.append(n)
        return out

    def node_acts_as(self, node) -> set:
        """A node gives the results of its sign lord and of planets joined to it."""
        p = self.planets[node]
        joined = {n for n, q in self.planets.items() if q.sign == p.sign and n != node and n not in NODES}
        return {LORD[p.sign]} | joined

    def expand(self, plist) -> set:
        s = set(plist)
        for nd in NODES:
            if nd in s: s |= self.node_acts_as(nd)
        return s


def significators(c: PChart, event: str):
    """(primary, support) planet sets for the event."""
    L, O, A = c.lord, c.occupants, c.aspectors
    if event == "marriage":
        primary = {L(7), "Venus"} | set(O(7)) | set(A(7))
        support = {L(2), L(11)}
    elif event == "career":
        d10 = c.d10
        d10_10_sign = d10["house_sign"](10)
        primary = {L(10)} | set(O(10)) | set(A(10)) | {d10["lord"](10)} | set(d10["occ"].get(d10_10_sign, []))
        support = {"Sun", "Saturn", L(6), L(11)}
    elif event == "money":
        d10 = c.d10
        primary = {L(2), L(11), "Jupiter"} | set(O(2)) | set(O(11)) | {d10["lord"](2), d10["lord"](11)}
        support = {L(5), L(9), L(1)}
    elif event == "study":
        primary = {L(5), L(4), "Jupiter", "Mercury"} | set(O(5))
        support = {L(9), L(1)}
    else:
        raise ValueError(event)
    primary = c.expand(primary) - {None}
    support = c.expand(support) - primary
    return primary, support


def _transit_targets(c: PChart, event: str) -> List[int]:
    sp = lambda p: c.planets[p].sign
    return {"marriage": [c.sign(1), c.sign(7), sp(c.lord(7))],
            "career": [c.sign(10), sp(c.lord(10))],
            "money": [c.sign(2), c.sign(11), sp(c.lord(2)), sp(c.lord(11))],
            "study": [c.sign(5), sp(c.lord(5))]}[event]


def _double_transit(c: PChart, event: str, when: datetime) -> Optional[dict]:
    sl = _slow_signs(when)
    if not sl: return None
    for base, ref in (("lagna", c.lagna), ("Moon", c.moon)):
        shift = (ref - c.lagna) % 12   # re-base the targets from Moon: same houses counted from Moon
        for t in _transit_targets(c, event):
            t2 = (t + shift) % 12
            if _touch(sl["Jupiter"], _JUP, t2) and _touch(sl["Saturn"], _SAT, t2):
                return {"base": base, "target": SIGN_NAMES[t2], "jupiter": SIGN_NAMES[sl["Jupiter"]],
                        "saturn": SIGN_NAMES[sl["Saturn"]]}
    return None


def _grade(md: str, ad: str, prim: set, sup: set) -> Optional[str]:
    mp, ap = md in prim, ad in prim
    if mp and ap: return "strong"
    if (mp and ad in sup) or (ap and md in sup): return "supported"
    if ap or mp: return "partial"
    return None


def parashari_windows(lagna_sign: int, lagna_lon: float, planets: Dict[str, Planet],
                      vim_rows: list, start: datetime, end: datetime) -> List[dict]:
    """vim_rows: dicts with planet, level ('mahadasha'/'antardasha'), start_date, end_date (datetime)."""
    c = PChart(lagna_sign, lagna_lon, planets)
    mds = [r for r in vim_rows if str(r["level"]).lower() in ("1", "mahadasha")]
    ads = [r for r in vim_rows if str(r["level"]).lower() in ("2", "antardasha", "bhukti")]
    sig = {e: significators(c, e) for e in ("marriage", "career", "money", "study")}
    dusthana = {c.lord(6), c.lord(8), c.lord(12)}
    out = []
    for a in sorted(ads, key=lambda r: r["start_date"]):
        if a["end_date"] < start or a["start_date"] > end: continue
        mid = a["start_date"] + (a["end_date"] - a["start_date"]) / 2
        md = next((m["planet"] for m in mds if m["start_date"] <= mid < m["end_date"]), None)
        if not md: continue
        events = []
        for ev, (prim, sup) in sig.items():
            g = _grade(md, a["planet"], prim, sup)
            if not g: continue
            dt = _double_transit(c, ev, mid)
            events.append({"event": ev, "grade": g, "double_transit": dt,
                           "rules": [f"PAR.{ev}.md_{md}", f"PAR.{ev}.ad_{a['planet']}", f"PAR.{ev}.{g}"]
                                    + (["PAR.double_transit"] if dt else [])})
        caution = a["planet"] in dusthana and not any(e["grade"] == "strong" for e in events)
        out.append({"start": a["start_date"], "end": a["end_date"], "md": md, "ad": a["planet"],
                    "events": events, "caution": ["PAR.ad_lord_rules_6_8_12"] if caution else []})
    return out
