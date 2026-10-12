"""
antar_engine/relationship_foundation.py

LAYER 2 of the relationship reading — "what is the bond actually made of?".

relationships.py reads the promise (7th, karaka, D-9 confirm) and the timing; this layer reads
whether the bond can SURVIVE and what the partner-significator looks like inside the native's field:

  • Sustenance — the 2nd from the Upapada Lagna (UL). Occupants, the lord's dignity and its
    placement FROM the UL (6/8/12 = the sustaining house works against the bond), aspects on it.
    A benefic here = the marriage absorbs stress; an afflicted lord/malefic = it breaks under the
    pressure another chart would absorb. Timing never repairs a broken sustenance house.
  • Spouse indicator — the Darakaraka (DK): in a dusthana / with the nodes / combust = the partner
    is detached, burdened or karmically leaving *in the native's field*; kendra/trikona with benefics
    = invested. This is the partner's ROLE in the native's karma — NOT his or her inner state.
  • D-9 as the lifetime verdict — navamsa lagna lord, the 7th from navamsa lagna (occupants + lord),
    Venus and the Atmakaraka in the navamsa. D-9 is the foundation; varshphal/dasha are the weather.

`foundation.band` ∈ sound | mixed | fragile. When it is fragile the narrator is told NOT to hold
out a reunion/commitment window and to say so kindly — stringing a window over a broken foundation
is the failure mode this layer exists to stop.

Pure + fail-open. Reuses relationships.py helpers (same dignity/UL/DK definitions). Status: v1,
classical defaults, UNVALIDATED against dated outcomes (see outcome loop) — a principled first pass.
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD
from antar_engine.relationships import (
    _BENEFICS, _MALEFICS, _combust, _darakaraka, _dig, _house_of, _upapada_sign, _sign_aspects)

_NODES = {"Rahu", "Ketu"}
_HARD = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}
_STRONG_HOUSES = {1, 4, 5, 7, 9, 10}       # kendra + trikona


def _from(a: str, b: str) -> int:
    """House number of sign b counted from sign a (1..12)."""
    return (SIGNS.index(b) - SIGNS.index(a)) % 12 + 1


def _in_sign(planets: dict, sign: str) -> list:
    return [p for p, v in planets.items() if isinstance(v, dict) and v.get("sign") == sign]


def _aspecting(planets: dict, sign: str) -> list:
    return [p for p, v in planets.items()
            if isinstance(v, dict) and v.get("sign") in SIGNS and v.get("sign") != sign
            and _sign_aspects(v["sign"], sign, p)]


def _sustenance(d1: dict, ul: str) -> dict:
    s2 = SIGNS[(SIGNS.index(ul) + 1) % 12]
    lord = SIGN_LORD.get(s2)
    lord_sign = (d1.get(lord) or {}).get("sign")
    score, flags, relief = 0.0, [], []
    lord_dig = _dig(lord, lord_sign)[0] if lord_sign in SIGNS else 0.0
    # the lord sitting in its OWN house is judged by its dignity below, not as an intruder
    occ = [p for p in _in_sign(d1, s2) if p in _BENEFICS | _MALEFICS and not (p == lord and lord_dig > 0)]
    for p in occ:
        if p in ("Jupiter", "Venus"):
            score += 1.0; relief.append(f"{p} in the sustaining house")
        elif p in _BENEFICS:
            score += 0.5; relief.append(f"{p} in the sustaining house")
        elif p == "Sun":
            score -= 0.6; flags.append("the Sun sits in the sustaining house")
        elif p in _HARD:
            score -= 1.2; flags.append(f"{p} sits in the sustaining house")
    asp = [p for p in _aspecting(d1, s2) if p not in occ]
    if "Jupiter" in asp:
        score += 0.8; relief.append("Jupiter looks on the sustaining house")
    hard_asp = [p for p in asp if p in ("Saturn", "Mars")]
    if hard_asp:
        score -= 0.5 * len(hard_asp); flags.append(f"{'/'.join(hard_asp)} presses on the sustaining house")
    if lord_sign in SIGNS:
        dig, lab = _dig(lord, lord_sign)
        hfu = _from(ul, lord_sign)
        if dig > 0:
            score += 0.8; relief.append(f"the sustaining lord is {lab}")
        elif dig < 0:
            score -= 1.5; flags.append("the sustaining lord is debilitated")
        if hfu in (6, 8, 12):
            score -= 1.2; flags.append("the sustaining lord sits in a house of loss from the marriage point")
        elif hfu in (1, 4, 5, 7, 9, 10, 11):
            score += 0.4
        with_hard = [p for p in _in_sign(d1, lord_sign) if p != lord and p in _HARD]
        if with_hard:
            score -= 0.6; flags.append(f"the sustaining lord sits with {'/'.join(with_hard)}")
    level = "sustains" if score >= 1.2 else "holds with care" if score > -0.8 else "fragile"
    return {"level": level, "score": round(score, 2), "flags": flags, "relief": relief,
            "second_from_ul": s2, "ul_sign": ul}


def _spouse_indicator(d1: dict) -> dict:
    dk = _darakaraka(d1)
    if not dk:
        return {"state": "unknown", "planet": None, "score": 0.0, "flags": [], "relief": []}
    v = d1.get(dk) or {}
    h, sign = v.get("house"), v.get("sign")
    score, flags, relief = 0.0, [], []
    dig, lab = _dig(dk, sign)
    if dig > 0:
        score += 1.0; relief.append(f"the partner-significator is {lab}")
    elif dig < 0:
        score -= 1.5; flags.append("the partner-significator is debilitated")
    if h in (6, 8, 12):
        score -= 1.5; flags.append("the partner-significator sits in a house of loss/distance")
    elif h in _STRONG_HOUSES:
        score += 0.8; relief.append("the partner-significator is well placed")
    mates = [p for p, pv in d1.items() if isinstance(pv, dict) and p != dk and pv.get("house") == h]
    nodes = [p for p in mates if p in _NODES]
    if nodes:
        score -= 1.2; flags.append(f"{'/'.join(nodes)} sits with the partner-significator")
    ben = [p for p in mates if p in ("Jupiter", "Venus")]
    if ben:
        score += 0.8; relief.append(f"{'/'.join(ben)} supports the partner-significator")
    if _combust(dk, d1):
        score -= 0.8; flags.append("the partner-significator is combust")
    detached = (h in (6, 8, 12) or bool(nodes)) and score <= -1.0
    state = ("invested" if score >= 1.2 else "mixed" if score > -1.0 else
             "detached" if detached else "burdened")
    return {"state": state, "planet": dk, "house": h, "score": round(score, 2), "flags": flags, "relief": relief}


def _d9_verdict(cd: dict) -> dict:
    d9 = ((cd.get("divisional_charts") or {}).get("d9") or {})
    pl, lg = d9.get("planets") or {}, d9.get("lagna")
    if not pl or lg not in SIGNS:
        return {"level": "unknown", "score": 0.0, "flags": [], "relief": []}
    score, flags, relief = 0.0, [], []

    def dg(p):
        return _dig(p, (pl.get(p) or {}).get("sign"))
    ll = SIGN_LORD.get(lg)
    d, lab = dg(ll)
    if d > 0: score += 0.8; relief.append(f"the marriage chart's own lord is {lab}")
    elif d < 0: score -= 1.2; flags.append("the marriage chart's own lord is debilitated")
    seventh = SIGNS[(SIGNS.index(lg) + 6) % 12]
    occ = _in_sign(pl, seventh)
    ben = [p for p in occ if p in ("Jupiter", "Venus", "Mercury", "Moon")]
    mal = [p for p in occ if p in _HARD]
    if ben: score += 0.8; relief.append("a benefic sits in the 7th of the marriage chart")
    if mal: score -= 1.0 * len(mal); flags.append("a hard planet sits in the 7th of the marriage chart")
    l7 = SIGN_LORD.get(seventh)
    d7, lab7 = dg(l7)
    if d7 > 0: score += 0.8; relief.append(f"the marriage chart's 7th lord is {lab7}")
    elif d7 < 0: score -= 1.2; flags.append("the marriage chart's 7th lord is debilitated")
    dv, labv = dg("Venus")
    if dv > 0: score += 0.6; relief.append(f"Venus is {labv} in the marriage chart")
    elif dv < 0: score -= 1.0; flags.append("Venus is debilitated in the marriage chart")
    ak = cd.get("atmakaraka")
    ak = ak.get("planet") if isinstance(ak, dict) else ak
    if ak in pl and ak not in _NODES:
        da, laba = dg(ak)
        if da < 0: score -= 0.6; flags.append("the soul-significator is weak in the marriage chart")
        elif da > 0: score += 0.4
    level = "supports" if score >= 1.5 else "partial" if score > -0.8 else "weak"
    return {"level": level, "score": round(score, 2), "flags": flags, "relief": relief}


def analyze_foundation(chart_data: dict, partnered: bool = False) -> dict:
    """{available, sustenance{}, spouse_indicator{}, d9{}, foundation{band, score, unsound}, facts[]}.
    Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign")
        if not d1 or lagna not in SIGNS:
            return {"available": False}
        ul = _upapada_sign(lagna, d1)
        if not ul:
            return {"available": False}
        sus, dki, d9 = _sustenance(d1, ul), _spouse_indicator(d1), _d9_verdict(cd)
        total = sus["score"] * 1.3 + dki["score"] + d9["score"]
        # the marriage-sustaining house and the lifetime chart carry the verdict; the DK colours it
        unsound = (sus["level"] == "fragile" and d9["level"] == "weak") or \
                  (sus["level"] == "fragile" and dki["state"] in ("detached", "burdened"))
        band = "fragile" if unsound or total <= -3.0 else "sound" if total >= 2.0 and sus["level"] != "fragile" else "mixed"
        return {"available": True, "sustenance": sus, "spouse_indicator": dki, "d9": d9,
                "foundation": {"band": band, "score": round(total, 2), "unsound": unsound},
                "facts": foundation_facts(band, sus, dki, d9, unsound, partnered)}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def foundation_facts(band, sus, dki, d9, unsound, partnered: bool = False) -> list:
    """Plain-language narrator lines (no planet/house/Upapada/Darakaraka/navamsa names).

    partnered=True (the reader is MARRIED / in the relationship being asked about): the same signals are worded as tendencies to tend -
    where the bond is most easily strained and what protects it - never as 'thin', 'pulling away', 'no window' or 'ending'. The band is a
    v1 heuristic, unvalidated against outcomes: it must not tell someone their own marriage is weak."""
    if partnered:
        return _foundation_facts_partnered(band, dki)
    L = [f"WHAT THE BOND IS MADE OF: foundation is {band}. "
         f"The part that lets a partnership survive pressure {sus['level']}; "
         f"the marriage chart as a whole {d9['level']} it."]
    ind = dki["state"]
    if ind != "unknown":
        L.append({
            "invested": "From the reader's side, the partner's role in their life reads as invested and engaged.",
            "mixed": "From the reader's side, the partner's role in their life reads as mixed — engaged in some ways, distant in others.",
            "detached": "From the reader's side, the partner's role in their life reads as distant or pulling away.",
            "burdened": "From the reader's side, the partner's role in their life reads as weighed down — carrying a load that crowds out closeness.",
        }[ind])
    L.append("EPISTEMICS — HARD RULE: this describes the partner's ROLE in the reader's life and how the "
             "bond feels FROM THE READER'S SIDE. It is NOT the partner's inner state or intentions: never say "
             "what he or she feels, wants, will do or is doing. Say 'in your life this person reads as…', "
             "never 'he/she loves/doesn't love you'.")
    if unsound or band == "fragile":
        L.append("FRAGILE FOUNDATION: do NOT hold out a reunion, repair or commitment window as likely, and do "
                 "not stack soft maybes. Say kindly and plainly that the lasting support under this bond looks thin, "
                 "then turn to what is in the reader's hands (closure, boundaries, or a clearly bounded attempt).")
    elif band == "sound":
        L.append("SOUND FOUNDATION: the bond has what it takes to survive stress — a repair or commitment "
                 "window is worth acting on; still never promise the other person's response.")
    else:
        L.append("MIXED FOUNDATION: the bond can hold but only with deliberate care — frame any window as "
                 "conditional on the reader's own steadiness, not as an outcome.")
    return L


_PARTNERED_SIDE = {
    "fragile": "This bond is one that asks for more deliberate care than most: it has points that strain easily under pressure.",
    "mixed": "This bond holds well when both people stay deliberate; it is tested most when pressure and distance pile up.",
    "sound": "This bond has what it takes to hold under pressure.",
}
_PARTNERED_ROLE = {
    "invested": "In the reader's life, the partner's role reads as engaged and invested.",
    "mixed": "In the reader's life, the partner's role reads as engaged in some ways and in need of attention in others.",
    "detached": "In the reader's life, the partner's role reads as stretched — closeness is likely to need deliberate attention.",
    "burdened": "In the reader's life, the partner's role reads as carrying a load that can crowd out closeness — worth easing together.",
}


def _foundation_facts_partnered(band, dki) -> list:
    L = ["WHAT THE BOND IS MADE OF (the reader is IN this relationship): " + _PARTNERED_SIDE.get(band, _PARTNERED_SIDE["mixed"])]
    if dki.get("state") in _PARTNERED_ROLE:
        L.append(_PARTNERED_ROLE[dki["state"]])
    L.append("EPISTEMICS — HARD RULE: this describes the partner's ROLE in the reader's life and how the bond feels FROM THE READER'S SIDE. "
             "It is NOT the partner's inner state or intentions: never say what he or she feels, wants or will do.")
    L.append("THIS READER IS PARTNERED - SPEAK TO PROTECTING THE BOND, NEVER JUDGE IT: do not call the marriage weak, thin, fragile, failing or "
             "ending, and do not mention a reunion, a closure or 'stop waiting'. These are tendencies from a heuristic that is not yet "
             "validated against real outcomes. Name where the bond is most easily strained (pace, communication, closeness under "
             "pressure) and give ONE concrete thing that protects it, then say the reader and their partner can act on it together.")
    return L
