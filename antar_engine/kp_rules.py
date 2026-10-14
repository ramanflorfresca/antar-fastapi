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


def kp_state(chart: dict, gender: Optional[str] = None, ruling: Optional[set] = None) -> dict:
    """Pre-compute what the clauses ask about. chart = compute_kp_chart(_from_jd) output.
    ruling = the ruling planets at the moment of judgement (optional; clauses that need it never hold without it)."""
    from antar_engine.kp.kp_significators import build_significators
    from antar_engine.kp import kp_levels
    kp_levels.enrich(chart)
    _hs, planet_sig = build_significators(chart)
    return {"chart": chart, "sig": planet_sig, "gender": gender, "periods": None,
            "levels": kp_levels.sig_levels(chart), "ruling": set(ruling or [])}


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
    from antar_engine.kp import kp_levels as kl
    ch_ = st["chart"]
    if "links_to_cusps" in c:                       # a planet / cusp lord is linked (sign, star, sub or sub-sub lord) with these cusps
        if "planet" in c:
            who = c["planet"]
        elif "cusp" in c:
            cu_ = ch_["cusps"].get(c["cusp"])
            if not cu_:
                return False
            who = cu_.get(c.get("lord_level", "sub_sub_lord"))
        else:
            return False
        have = set(kl.links(ch_, who, tuple(c.get("via", ("sign", "star", "sub", "sub_sub")))))
        return _mode_ok(have, c["links_to_cusps"], mode)
    if "retrograde" in c and "planet" in c:
        pl_ = ch_["planets"].get(c["planet"])
        return bool(pl_) and bool(pl_.get("retrograde")) == bool(c["retrograde"])
    if "sign_type" in c:
        if "planet" in c:
            sg = ch_["planets"].get(c["planet"], {}).get("sign")
        elif "cusp" in c:
            sg = ch_["cusps"].get(c["cusp"], {}).get("sign")
        else:
            return False
        return sg is not None and kl.sign_type(sg) in (c["sign_type"] if isinstance(c["sign_type"], list) else [c["sign_type"]])
    if "in_sign" in c and ("planet" in c or "cusp" in c):
        sg = ch_["planets"].get(c["planet"], {}).get("sign") if "planet" in c else ch_["cusps"].get(c["cusp"], {}).get("sign")
        return sg in (c["in_sign"] if isinstance(c["in_sign"], list) else [c["in_sign"]])
    if "owns" in c and "planet" in c:
        return _mode_ok(set(kl.owned_houses(ch_, c["planet"])), c["owns"], mode)
    if "star_lord_owns" in c and "planet" in c:
        sl = ch_["planets"].get(c["planet"], {}).get("star_lord")
        return bool(sl) and _mode_ok(set(kl.owned_houses(ch_, sl)), c["star_lord_owns"], mode)
    if "signifies_level" in c and "planet" in c:    # {"houses":[2,11],"max_level":2} strong significator (star of occupant / occupant)
        d = c["signifies_level"]
        lv = (st.get("levels") or {}).get(c["planet"], {})
        return _mode_ok({h for h, v in lv.items() if v <= d.get("max_level", 2)}, d.get("houses"), mode)
    if "ruling_includes" in c:                      # the planet is among the ruling planets at the moment of judgement
        return c["ruling_includes"] in (st.get("ruling") or set())
    if "cusp" in c and any(k in c for k in ("sub_sub_lord", "sub_sub_lord_signifies")):
        cu_ = ch_["cusps"].get(c["cusp"])
        if not cu_:
            return False
        if "sub_sub_lord" in c:
            return cu_.get("sub_sub_lord") == c["sub_sub_lord"]
        return _mode_ok(set(st["sig"].get(cu_.get("sub_sub_lord"), [])), c["sub_sub_lord_signifies"], mode)
    if "planet" in c and "sub_sub_lord" in c:
        return ch_["planets"].get(c["planet"], {}).get("sub_sub_lord") == c["sub_sub_lord"]
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
        if not lord:
            return False
        if d.get("max_level"):                       # only strong significators (star of occupant / occupant ...) count
            have = {h for h, v in (st.get("levels") or {}).get(lord, {}).items() if v <= d["max_level"]}
            return _mode_ok(have, d.get("houses"), d.get("mode", "any"))
        return _mode_ok(set(st["sig"].get(lord, [])), d.get("houses"), d.get("mode", "any"))
    if "dasha_lord_ruling" in a:                     # the running period lord at that level is among the ruling planets
        lord = lords_at(st, jd).get(a["dasha_lord_ruling"].get("level"))
        return bool(lord) and lord in (st.get("ruling") or set())
    if "dasha_links_to_cusps" in a:                  # the running period lord is linked (sign/star/sub/sub-sub) with these cusps
        from antar_engine.kp import kp_levels as kl
        d = a["dasha_links_to_cusps"]
        lord = lords_at(st, jd).get(d.get("level"))
        return bool(lord) and _mode_ok(set(kl.links(st["chart"], lord, tuple(d.get("via", ("sign", "star", "sub", "sub_sub"))))), d.get("cusps"), d.get("mode", "any"))
    if "dasha" in a:
        d = a["dasha"]
        return lords_at(st, jd).get(d.get("level")) in (d.get("lords") or [])
    return False


def applying(st: dict, jd: Optional[float] = None, rules: Optional[List[dict]] = None) -> List[dict]:
    """Standing rules when jd is None; with a jd, timed rules whose activation also holds."""
    out = []
    for r in (load_rules() if rules is None else rules):
        if r.get("asked_at_judgement") and not st.get("ruling"):
            continue                                  # question-time rule: needs the ruling planets of a question moment
        if not all(holds(c, st) for c in r.get("requires", [])):
            continue
        acts = r.get("activation", [])
        if acts and (jd is None or not all(act_holds(a, st, jd) for a in acts)):
            continue
        if not acts and jd is not None:
            continue
        out.append(r)
    return out
