"""
antar_engine/d10_career.py

D-10 (Dashamsha) career-TYPE engine — KN Rao synthesis.

Answers "which profession / what career suits me" DETERMINISTICALLY: it reads
the real chart (D-1 + D-10 + Amatyakaraka) and ranks career FIELDS. The LLM only
narrates this ranked list — it never invents the astrology.

Method (KN Rao's multi-significator approach; a career significator that recurs
across independent factors and sits strong is the real one):
  1. D-1 10th house — its lord, planets in it, planets conjunct the 10th lord.
  2. D-10 10th house — its lord, planets in it (D-10 = the career close-up, so
     it carries the most weight).
  3. Amatyakaraka — the Jaimini career karaka.
  4. Dignity in D-10 — exalted / own-sign planets there are strengthened.
Each significator planet is voted; its votes flow to its career significations;
fields are ranked by total weight.

v1 uses standard planetary career significations (PLANET_CAREERS) — a starting
point to refine against real charts, not a final word.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}
_EXALT = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
          "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
          "Saturn": "Libra"}
_OWN = {"Sun": {"Leo"}, "Moon": {"Cancer"}, "Mars": {"Aries", "Scorpio"},
        "Mercury": {"Gemini", "Virgo"}, "Jupiter": {"Sagittarius", "Pisces"},
        "Venus": {"Taurus", "Libra"}, "Saturn": {"Capricorn", "Aquarius"}}

# Standard planetary career significations (v1). Ordered most→least prominent.
PLANET_CAREERS = {
    "Sun":     ["government / public sector", "leadership & administration",
                "medicine", "politics", "authority roles"],
    "Moon":    ["public-facing & hospitality", "food & beverage",
                "care / nursing / psychology", "travel & real estate",
                "roles serving the public"],
    "Mars":    ["engineering & technical", "real estate & construction",
                "surgery / defense / police", "sports & fitness",
                "manufacturing / metals"],
    "Mercury": ["commerce & trade", "IT / software", "writing & communication",
                "accounting & analytics", "teaching / consulting"],
    "Jupiter": ["finance & banking", "law", "advisory / consulting",
                "teaching & academia", "publishing / philosophy"],
    "Venus":   ["arts & entertainment", "luxury / fashion / beauty",
                "design & creative", "hospitality", "diplomacy & relationships"],
    "Saturn":  ["operations & service industries", "construction / heavy industry",
                "law & governance", "long-term / structured roles", "agriculture"],
    "Rahu":    ["technology & innovation", "foreign / international business",
                "media & digital", "research & the unconventional",
                "startups & speculation"],
    "Ketu":    ["research & investigation", "IT / coding", "healing / medicine",
                "niche / specialist expertise", "behind-the-scenes technical"],
}

_CHARA_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]


def _sign_n_from(lagna_sign: str, n: int) -> Optional[str]:
    if lagna_sign not in SIGNS:
        return None
    return SIGNS[(SIGNS.index(lagna_sign) + n - 1) % 12]


def _dignity(planet: str, sign: str) -> Optional[str]:
    if _EXALT.get(planet) == sign:
        return "exalted"
    if sign in _OWN.get(planet, set()):
        return "own sign"
    return None


def _amatyakaraka(planets: dict) -> Optional[str]:
    """2nd-highest degree-within-sign among the 8 chara karakas (Rahu counted at
    30 - its degree). Highest = Atmakaraka, second = Amatyakaraka (career)."""
    ranked = []
    for p in _CHARA_ORDER:
        v = planets.get(p) or {}
        deg = v.get("degree")
        if deg is None:
            continue
        d = float(deg) % 30
        if p == "Rahu":
            d = 30 - d
        ranked.append((d, p))
    ranked.sort(reverse=True)
    return ranked[1][1] if len(ranked) >= 2 else None


def analyze_career(chart_data: dict) -> dict:
    """Return {available, careers[], drivers[], factors{}, summary}.
    careers = ranked list of {field, weight, from[]}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        d1_lagna = ((cd.get("lagna") or {}).get("sign"))
        d10 = ((cd.get("divisional_charts") or {}).get("d10") or {})
        d10_pl = d10.get("planets") or {}
        d10_lagna = d10.get("lagna")
        if not d1 or not d1_lagna or not d10_pl or not d10_lagna:
            return {"available": False}

        votes: dict = defaultdict(float)
        reasons: dict = defaultdict(list)

        def vote(planet, w, why):
            if planet and planet in PLANET_CAREERS:
                votes[planet] += w
                reasons[planet].append(why)

        factors = {}

        # 1) D-1 10th house
        d1_10sign = _sign_n_from(d1_lagna, 10)
        d1_10lord = SIGN_LORD.get(d1_10sign)
        factors["d1_10th_sign"] = d1_10sign
        factors["d1_10th_lord"] = d1_10lord
        vote(d1_10lord, 2.0, "rules your 10th house of career")
        in_d1_10 = [p for p, v in d1.items()
                    if isinstance(v, dict) and v.get("house") == 10]
        factors["planets_in_d1_10th"] = in_d1_10
        for p in in_d1_10:
            vote(p, 1.5, "sits in your 10th house of career")
        # conjunctions with the 10th lord (same house as the lord)
        lord_house = (d1.get(d1_10lord) or {}).get("house")
        if lord_house:
            for p, v in d1.items():
                if p != d1_10lord and isinstance(v, dict) and v.get("house") == lord_house:
                    vote(p, 1.0, "sits with your career lord")

        # 2) D-10 10th house (career close-up → highest weight)
        d10_10sign = _sign_n_from(d10_lagna, 10)
        d10_10lord = SIGN_LORD.get(d10_10sign)
        factors["d10_10th_sign"] = d10_10sign
        factors["d10_10th_lord"] = d10_10lord
        vote(d10_10lord, 2.0, "rules the 10th of your career chart (D-10)")
        in_d10_10 = [p for p, v in d10_pl.items()
                     if isinstance(v, dict) and v.get("house") == 10]
        factors["planets_in_d10_10th"] = in_d10_10
        for p in in_d10_10:
            vote(p, 2.5, "sits in the 10th of your career chart (D-10)")

        # 3) Amatyakaraka (career karaka)
        amk = _amatyakaraka(d1)
        factors["amatyakaraka"] = amk
        vote(amk, 1.5, "is your career karaka (Amatyakaraka)")

        # 4) Dignity in D-10 — exalted / own-sign there is strengthened
        for p, v in d10_pl.items():
            if isinstance(v, dict):
                dig = _dignity(p, v.get("sign"))
                if dig:
                    vote(p, 1.0, f"is {dig} in your career chart")

        if not votes:
            return {"available": False}

        # career fields: each voting planet contributes its significations,
        # weighted by that planet's votes and the signification's rank.
        field_w: dict = defaultdict(float)
        field_from: dict = defaultdict(set)
        for planet, w in votes.items():
            careers = PLANET_CAREERS.get(planet, [])
            for i, field in enumerate(careers[:3]):   # top 3 per planet
                field_w[field] += w * (1.0 - i * 0.2)
                field_from[field].add(planet)

        careers_ranked = sorted(
            ({"field": f, "weight": round(w, 2),
              "from": sorted(field_from[f])} for f, w in field_w.items()),
            key=lambda x: x["weight"], reverse=True)

        drivers = sorted(
            ({"planet": p, "weight": round(w, 2), "why": reasons[p]}
             for p, w in votes.items()),
            key=lambda x: x["weight"], reverse=True)

        top = drivers[0]["planet"] if drivers else None
        summary = ("Your strongest career significators are "
                   + ", ".join(d["planet"] for d in drivers[:3])
                   + f" — pointing to {', '.join(c['field'] for c in careers_ranked[:3])}."
                   ) if drivers else ""

        return {"available": True, "careers": careers_ranked[:6],
                "drivers": drivers[:5], "factors": factors, "summary": summary,
                "top_significator": top}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
