"""
antar_engine/health.py

Deterministic HEALTH engine. Answers, from the real chart:
  • CONSTITUTION — baseline vitality (lagna + lagna lord + Sun/Moon).
  • CHRONIC vs ACUTE — a chronic/constitutional tendency shows in BOTH the D-1 and
    the D-9 (the navamsa confirms it is structural, not passing); an affliction
    that appears only in the D-1 / by transit is acute and passes. (Owner's rule.)
  • NATURE / body area — what kind of issue, from the afflicted planet (its ailment
    signification) and its sign (the body part, Kālapuruṣa).
  • VULNERABLE WINDOWS — when health needs care, via the shared convergence timer
    with the Lal-Kitab varshphal weighted HEAVILY (most accurate yearly) + Sade Sati.

Houses: 1 (body/vitality), 6 (acute disease), 8 (chronic/surgery/longevity),
12 (hospitalisation/bed). Karakas: Sun (vitality/heart/bones), Moon (mind/fluids),
Saturn (chronic/bones/nerves), Mars (blood/accident/surgery), Rahu/Ketu (mystery).
LLM narrates only. v1 — calibrate against real health events.
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.relationships import (
    _dig, _house_of, _in_house, _malefics_on, _combust, _conj_malefics)
from antar_engine.domain_timing import domain_convergence

# Body area by sign (Kālapuruṣa) — the "where" of an ailment.
_SIGN_BODY = {
    "Aries": "head, brain, or eyes", "Taurus": "face, throat, or neck",
    "Gemini": "shoulders, arms, lungs, or nervous system",
    "Cancer": "chest, stomach, or emotional/digestive system",
    "Leo": "heart, spine, or upper back", "Virgo": "intestines or digestion",
    "Libra": "kidneys, lower back, or skin",
    "Scorpio": "reproductive/urinary system or colon",
    "Sagittarius": "hips, thighs, or liver",
    "Capricorn": "knees, joints, bones, or skin",
    "Aquarius": "calves, ankles, or circulation",
    "Pisces": "feet, lymph, or immunity",
}
# Nature of ailment by planet.
_PLANET_AILMENT = {
    "Sun": "vitality, heart, bones, eyes, or blood pressure",
    "Moon": "mind/mood, fluids, chest, or hormonal balance",
    "Mars": "blood, inflammation, injuries/accidents, surgery, or fevers",
    "Mercury": "the nervous system, skin, or anxiety",
    "Jupiter": "the liver, weight, or sugar/diabetes",
    "Venus": "the reproductive/urinary system, kidneys, or hormones",
    "Saturn": "chronic/degenerative issues, bones/joints, nerves, or teeth",
    "Rahu": "mysterious/undiagnosed conditions, toxins, or the skin",
    "Ketu": "neurological, immune, viral, or mysterious/latent conditions",
}

HEALTH_SPEC = {
    "noun": "health",
    "houses": [1, 6, 8, 12],
    "activator_houses": [6, 8, 12],
    "karakas": ["Saturn", "Mars", "Rahu", "Ketu", "Sun"],
    "varsh_houses": [1, 6, 8],
    "transit_grahas": ["Saturn", "Mars", "Rahu", "Ketu"],
    "transit_houses": [1, 6, 8],
    "malefic_varsh": True,
    "varsh_weight": 1.8,       # LK varshphal weighted heavily (owner: most accurate yearly)
    "sade_sati": True,
    "sade_sati_weight": 1.0,
    "min_score": 2.0,
}


def _weak(planet, sign):
    return _dig(planet, sign)[0] < 0


_MALEFIC_SET = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}


def _house_from(lagna_sign, sign):
    if lagna_sign not in SIGNS or sign not in SIGNS:
        return None
    return (SIGNS.index(sign) - SIGNS.index(lagna_sign)) % 12 + 1


def _health_afflictions(pmap, lagna_sign, lagna_lord, house_of, allow_combust=True):
    """Tally GENUINE health damage (not the crude 'lord in a dusthana'). A malefic
    in the 6th is Harṣa/Vipaṛīta — protective — so it is NOT counted. Returns
    (score, afflicted_planets, flags)."""
    score, afflicted, flags = 0.0, set(), []

    def add(s, p, why):
        nonlocal score
        score += s
        if p:
            afflicted.add(p)
        flags.append(why)

    ll = pmap.get(lagna_lord) or {}
    ll_sign = ll.get("sign")
    if ll_sign and _weak(lagna_lord, ll_sign):
        add(1.0, lagna_lord, "the constitution's ruler is debilitated")
    if allow_combust and _combust(lagna_lord, pmap):
        add(0.8, lagna_lord, "the constitution's ruler is combust")
    _cm = _conj_malefics(lagna_lord, pmap)
    if _cm and lagna_lord not in _MALEFIC_SET:
        add(0.6, lagna_lord, f"the constitution's ruler is afflicted by {', '.join(_cm)}")
    # malefics sitting ON the body (1st house) — Ketu/Rahu heavier (congenital/neuro)
    on_lagna = [p for p in _MALEFIC_SET if house_of(p) == 1]
    for m in on_lagna:
        add(0.8 if m in ("Ketu", "Rahu") else 0.6, m, f"{m} sits on the body/self")
    if len(on_lagna) >= 2:
        add(0.6, None, "several hard influences press the body at once")
    # the mind / nervous system (Moon + Mercury) — neurological / cognitive
    for mind in ("Moon", "Mercury"):
        v = pmap.get(mind) or {}
        s = v.get("sign")
        if s and (_weak(mind, s) or (allow_combust and _combust(mind, pmap))
                  or _conj_malefics(mind, pmap) or house_of(mind) in (6, 8, 12)):
            add(0.5, mind, f"the mind/nervous significator ({mind}) is under strain")
    # lord in the 8th/12th (crisis/undoing) — but NOT the protective 6th
    if house_of(lagna_lord) in (8, 12):
        add(0.4, None, "the constitution's ruler sits in a house of crisis/undoing")
    # the DISEASE houses — a node in the 6th/8th is the classic chronic / autoimmune
    # / mysterious-illness signature (autism, Type-1 diabetes both live here); Saturn
    # in the 8th is chronic/degenerative. (Nodes/Saturn in the 6th are NOT counted —
    # a malefic there is Harṣa/protective.)
    for node in ("Rahu", "Ketu"):
        nh = house_of(node)
        if nh == 6:
            add(1.0, node, f"{node} sits in the house of chronic/mysterious illness")
        elif nh == 8:
            add(0.8, node, f"{node} sits in the house of chronic crises")
        elif nh == 12:
            add(0.5, node, f"{node} sits in the house of hospitalisation/undoing")
    if house_of("Saturn") == 8:
        add(0.6, "Saturn", "Saturn sits in the house of chronic/degenerative conditions")
    return round(score, 2), afflicted, flags


def analyze_health(chart_data: dict) -> dict:
    """{available, constitution{}, chronic{}, nature[], factors{}, summary}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        d9 = ((cd.get("divisional_charts") or {}).get("d9") or {})
        d9_pl = d9.get("planets") or {}
        d9_lagna = d9.get("lagna")
        if not d1 or not lagna:
            return {"available": False}

        lagna_lord = SIGN_LORD.get(lagna)

        # ── genuine affliction tally in D-1 and (confirming) D-9 ─────────────
        d1_house = lambda p: (d1.get(p) or {}).get("house")
        d1_score, d1_affl, d1_flags = _health_afflictions(d1, lagna, lagna_lord, d1_house, True)
        # D-9: houses reckoned from the navamsa lagna; combustion is a D-1 notion.
        d9_house = lambda p: _house_from(d9_lagna, (d9_pl.get(p) or {}).get("sign"))
        d9_ll = SIGN_LORD.get(d9_lagna) if d9_lagna else lagna_lord
        d9_score, d9_affl, _d9f = _health_afflictions(d9_pl, d9_lagna or lagna, d9_ll, d9_house, False) if d9_pl else (0.0, set(), [])

        # ── CONSTITUTION / vitality ──────────────────────────────────────────
        constitution = {
            "score": d1_score,
            "level": ("robust" if d1_score < 1.0 else "moderate" if d1_score < 2.5 else "delicate"),
            "flags": d1_flags,
        }

        # ── CHRONIC vs ACUTE — a genuine D-1 stack CONFIRMED in the D-9 ──────
        # A malefic in the 6th is NOT counted (protective). Chronic requires real,
        # stacked damage (>=2.0) echoed in the navamsa (>=1.2). D-1-only = acute.
        is_chronic = bool(d1_score >= 2.0 and d9_score >= 1.2)
        chronic = {
            "is_chronic": is_chronic,
            "kind": ("a chronic / constitutional tendency (it shows in both the birth "
                     "chart and the deeper navamsa — manage it long-term)" if is_chronic
                     else "acute / passing tendencies (they come and go rather than being "
                          "structural)"),
            "d1_score": d1_score, "d9_score": d9_score,
        }

        # ── NATURE / body area — from the actually-afflicted significators ────
        nature, seen = [], set()
        for p in list(d1_affl) + _in_house(d1, 6) + _in_house(d1, 8):
            if not p or p in seen or p not in _PLANET_AILMENT:
                continue
            seen.add(p)
            body = _SIGN_BODY.get((d1.get(p) or {}).get("sign"))
            nature.append(_PLANET_AILMENT[p] + (f" — {body}" if body else ""))
        sixth = _sign_n_from(lagna, 6)
        if not nature and sixth in _SIGN_BODY:
            nature.append("the seat of illness points to " + _SIGN_BODY[sixth])
        nature = nature[:3]

        factors = {"lagna_lord": lagna_lord, "malefics_on_1st": _malefics_on(d1, 1),
                   "sixth_sign": sixth, "planets_in_6": _in_house(d1, 6),
                   "d1_afflicted": sorted(d1_affl), "d9_afflicted": sorted(d9_affl)}

        summary = (f"Constitution is {constitution['level']}; tendencies read as "
                   + ("chronic/constitutional" if is_chronic else "acute/passing")
                   + (f", tending to involve {nature[0]}." if nature else "."))

        return {"available": True, "constitution": constitution, "chronic": chronic,
                "nature": nature, "factors": factors, "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def _health_nature_for(chart_data, lords):
    """Body/ailment nature from the activating lords of a window."""
    d1 = (chart_data.get("planets") or {})
    out, seen = [], set()
    for lord in lords:
        if lord in _PLANET_AILMENT and lord not in seen:
            seen.add(lord)
            body = _SIGN_BODY.get((d1.get(lord) or {}).get("sign"))
            out.append(_PLANET_AILMENT[lord] + (f" — {body}" if body else ""))
    return out[:2]


def health_timing(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                  today: Optional[str] = None) -> dict:
    """Vulnerable-health windows via multi-system convergence (varshphal-heavy +
    Sade Sati). Returns {available, windows[], best, summary}."""
    res = domain_convergence(chart_data, dashas, HEALTH_SPEC, birth_date=birth_date, today=today)
    if not res.get("available"):
        return res
    for w in res.get("windows", []):
        parts = [x.strip() for x in w["label"].replace("–", "-").split("-")]
        w["nature"] = _health_nature_for(chart_data, parts)
    best = res.get("best")
    if best:
        nat = best.get("nature") or []
        res["summary"] = (f"The most health-sensitive window is around {best['start'][:7]} "
                          f"— {len(best['systems'])} systems flag it"
                          + (f", tending to involve {nat[0]}." if nat else "."))
    else:
        res["summary"] = "No sharply-converging health-risk window ahead — no structural flare flagged."
    return res
