"""
KP-frame book rules (Placidus cusps, KP-Old ayanamsa, sub lords, significators).

INTERNAL / SHADOW ONLY until the owner approves KP output: nothing here is called from a user-facing path.
A rule applies only if every `requires` clause holds on the KP chart; a timed rule also needs every `activation`
clause to hold at the date. Unknown clause shapes never hold (silence, not a guess).
Chart comes from antar_engine.kp.kp_service._build_chart; significators from kp_significators.build_significators.
"""
import json
import os
from typing import Dict, List, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "book_rules_kp.json")
_cache: Optional[List[dict]] = None


def load_rules(path: str = DATA_PATH) -> List[dict]:
    global _cache
    if path == DATA_PATH and _cache is not None:
        return _cache
    try:
        rules = json.load(open(path)).get("rules", [])
    except Exception:
        rules = []
    if path == DATA_PATH:
        _cache = rules
    return rules


def kp_state(chart: dict, gender: Optional[str] = None) -> dict:
    """Pre-compute what the clauses ask about. chart = compute_kp_chart(_from_jd) output."""
    from antar_engine.kp.kp_significators import build_significators
    _hs, planet_sig = build_significators(chart)
    return {"chart": chart, "sig": planet_sig, "gender": gender, "periods": None}


def _mode_ok(have: set, want, mode: str) -> bool:
    want = set(want or [])
    if not want:
        return False
    if mode == "all":
        return want <= have
    if mode == "none":
        return not (want & have)
    return bool(want & have)


def _star_of(st, planet):
    return st["chart"]["planets"].get(planet, {}).get("star_lord")


def holds(c: dict, st: dict) -> bool:
    if "unparsed" in c:
        return False
    ch = st["chart"]
    if "chart" in c and len(c) == 1:
        return st.get("gender") == c["chart"]
    if c.get("frame") != "kp":
        return False
    mode = c.get("mode", "any")
    if "cusp" in c:
        cu = ch["cusps"].get(c["cusp"])
        if not cu:
            return False
        if "sub_lord_signifies" in c:
            return _mode_ok(set(st["sig"].get(cu["sub_lord"], [])), c["sub_lord_signifies"], mode)
        if "sub_lord_star_lord_signifies" in c:
            sl = ch["planets"].get(cu["sub_lord"], {}).get("star_lord")
            return _mode_ok(set(st["sig"].get(sl, [])), c["sub_lord_star_lord_signifies"], mode)
        if "sub_lord_in_house" in c:
            h = ch["planets"].get(cu["sub_lord"], {}).get("house")
            return h in c["sub_lord_in_house"]
        for key in ("sub_lord", "star_lord", "sign_lord"):
            if key in c:
                return cu.get(key) == c[key]
        return False
    p = c.get("planet")
    if p and p in ch["planets"]:
        pl = ch["planets"][p]
        if "signifies" in c:
            return _mode_ok(set(st["sig"].get(p, [])), c["signifies"], mode)
        if "star_lord_signifies" in c:
            return _mode_ok(set(st["sig"].get(pl["star_lord"], [])), c["star_lord_signifies"], mode)
        if "in_house" in c:
            return pl.get("house") in c["in_house"]
        for key in ("star_lord", "sub_lord", "sign_lord"):
            if key in c:
                return pl.get(key) == c[key]
    return False


def lords_at(st: dict, jd: float) -> Dict[str, Optional[str]]:
    from antar_engine.kp.kp_timing import build_timeline, lords_at as _la
    if st.get("periods") is None:
        st["periods"] = build_timeline(st["chart"], jd + 3650)
    md, ad, pd = _la(st["periods"], jd)
    return {"md": md, "ad": ad, "pd": pd}


def act_holds(a: dict, st: dict, jd: Optional[float]) -> bool:
    if jd is None:
        return False
    if "dasha_signifies" in a:
        d = a["dasha_signifies"]
        lord = lords_at(st, jd).get(d.get("level"))
        return bool(lord) and _mode_ok(set(st["sig"].get(lord, [])), d.get("houses"), d.get("mode", "any"))
    if "dasha" in a:
        d = a["dasha"]
        return lords_at(st, jd).get(d.get("level")) in (d.get("lords") or [])
    return False


def applying(st: dict, jd: Optional[float] = None, rules: Optional[List[dict]] = None) -> List[dict]:
    """Standing rules when jd is None; with a jd, timed rules whose activation also holds."""
    out = []
    for r in (load_rules() if rules is None else rules):
        if not all(holds(c, st) for c in r.get("requires", [])):
            continue
        acts = r.get("activation", [])
        if acts and (jd is None or not all(act_holds(a, st, jd) for a in acts)):
            continue
        if not acts and jd is not None:
            continue
        out.append(r)
    return out
