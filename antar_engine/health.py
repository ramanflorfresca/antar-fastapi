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
    "Ketu": "mysterious, immune, viral, or latent conditions",
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
        ll_sign = (d1.get(lagna_lord) or {}).get("sign")

        # ── CONSTITUTION / vitality ──────────────────────────────────────────
        vit, vflags = 0.0, []
        mal1 = _malefics_on(d1, 1)
        if len(mal1) >= 2:
            vit -= 1.0; vflags.append("the body (1st house) is under malefic pressure")
        if _weak(lagna_lord, ll_sign):
            vit -= 1.0; vflags.append("the constitution's ruler is weakened")
        if _house_of(lagna_lord, d1) in (6, 8, 12):
            vit -= 0.8; vflags.append("the constitution's ruler sits in a house of illness/loss")
        sun_s = (d1.get("Sun") or {}).get("sign")
        moon_s = (d1.get("Moon") or {}).get("sign")
        if _weak("Sun", sun_s):
            vit -= 0.5; vflags.append("core vitality (Sun) is weak")
        if _weak("Moon", moon_s) or _conj_malefics("Moon", d1):
            vit -= 0.5; vflags.append("the mind/emotional vitality (Moon) is under strain")
        constitution = {
            "score": round(vit, 2),
            "level": ("robust" if vit >= -0.4 else "moderate" if vit >= -1.6 else "delicate"),
            "flags": vflags,
        }

        # ── CHRONIC vs ACUTE — must confirm in D-1 AND D-9 ───────────────────
        # D-1 constitutional weakness AND the same weakness echoing in the navamsa
        # = a chronic/structural tendency. D-1 only = acute/transient.
        d1_weak = (len(mal1) >= 2 or _weak(lagna_lord, ll_sign)
                   or _house_of(lagna_lord, d1) in (6, 8, 12))
        # D-9 confirmation: lagna lord weak in D-9, or the D-9 lagna lord weak, or
        # the Moon weak in D-9, or malefics on the D-9 lagna.
        d9_ll_sign = (d9_pl.get(lagna_lord) or {}).get("sign")
        d9_lagna_lord = SIGN_LORD.get(d9_lagna) if d9_lagna else None
        d9_ll2_sign = (d9_pl.get(d9_lagna_lord) or {}).get("sign") if d9_lagna_lord else None
        d9_weak = (_weak(lagna_lord, d9_ll_sign)
                   or (d9_lagna_lord and _weak(d9_lagna_lord, d9_ll2_sign))
                   or _weak("Moon", (d9_pl.get("Moon") or {}).get("sign")))
        is_chronic = bool(d1_weak and d9_weak)
        chronic = {
            "is_chronic": is_chronic,
            "kind": ("a chronic / constitutional tendency (it shows in both the birth "
                     "chart and the deeper navamsa — manage it long-term)" if is_chronic
                     else "acute / passing tendencies (they come and go rather than being "
                          "structural)"),
            "d1_weak": bool(d1_weak), "d9_weak": bool(d9_weak),
        }

        # ── NATURE / body area — the afflicted health significators ───────────
        nature = []
        seen = set()
        # afflicted planets among the health significators
        candidates = ["Sun", "Moon", lagna_lord, "Saturn", "Mars"] + _in_house(d1, 6) + _in_house(d1, 8)
        for p in candidates:
            if not p or p in seen:
                continue
            v = d1.get(p) or {}
            sgn = v.get("sign")
            afflicted = (_weak(p, sgn) or _combust(p, d1) or bool(_conj_malefics(p, d1))
                         or v.get("house") in (6, 8, 12))
            if afflicted and p in _PLANET_AILMENT:
                seen.add(p)
                body = _SIGN_BODY.get(sgn)
                nature.append(_PLANET_AILMENT[p] + (f" — {body}" if body else ""))
        # the 6th-house sign itself → the seat of disease
        sixth = _sign_n_from(lagna, 6)
        if sixth in _SIGN_BODY:
            nature.append("the seat of illness points to " + _SIGN_BODY[sixth])
        nature = nature[:3]

        factors = {"lagna_lord": lagna_lord, "malefics_on_1st": mal1,
                   "sixth_sign": sixth, "planets_in_6": _in_house(d1, 6)}

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
