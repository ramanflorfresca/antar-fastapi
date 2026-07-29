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

# Career TYPE comes from the SIGN a significator occupies (its element + ruler),
# NOT the planet in the abstract — Jupiter in Virgo (a Mercury sign) means
# commerce/analysis, not law. This is the primary field source; the sign's
# dispositor (PLANET_CAREERS below) adds a secondary flavor. Ordered by prominence.
SIGN_CAREERS = {
    "Aries":       ["engineering & machinery", "sports & competition",
                    "defense / police / military", "pioneering / entrepreneurship", "surgery"],
    "Taurus":      ["finance & banking", "food & agriculture",
                    "luxury goods & art", "real estate", "stable material trades"],
    "Gemini":      ["communication & media", "commerce & trade",
                    "writing & content", "IT / software", "sales & networking"],
    "Cancer":      ["public-facing & hospitality", "food & beverage",
                    "real estate & property", "care / nursing", "consumer goods"],
    "Leo":         ["leadership & management", "government & authority",
                    "entertainment & performance", "politics", "executive roles"],
    "Virgo":       ["analysis & accounting", "health & medicine",
                    "IT / data / detail work", "editing & service", "research & quality"],
    "Libra":       ["arts & design", "law & diplomacy", "fashion & beauty",
                    "luxury & hospitality", "advisory / relationship-based"],
    "Scorpio":     ["research & investigation", "surgery & medicine",
                    "other-people's-money / insurance / finance", "occult / depth work",
                    "defense & security"],
    "Sagittarius": ["teaching & academia", "law", "finance & advisory",
                    "publishing & philosophy", "foreign / travel"],
    "Capricorn":   ["business & management", "government & administration",
                    "construction / mining / heavy industry", "executive / structured roles",
                    "operations"],
    "Aquarius":    ["technology & innovation", "science & research",
                    "networks / community / humanitarian", "unconventional / new-age",
                    "engineering & systems"],
    "Pisces":      ["arts / film / imagination", "healing / spirituality / medicine",
                    "foreign & maritime", "charity & service", "creative / behind-the-scenes"],
}

# Dispositor flavor only (secondary). Ordered most→least prominent.
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

# [kal / era-weighting] In the present age, Rahu (technology, foreign, disruption)
# and Mercury (commerce, data, communication) are more operative than Jupiter
# (traditional dharma/advisory) and Ketu (renunciation). This deterministically
# nudges significator scores so a chart's modern-era fields surface — e.g. a
# tech founder's Rahu ranks above their Jupiter-finance. TUNABLE: adjust these,
# or set all to 1.0 to disable era weighting entirely.
# [de-overfit 2026-07-28] Cut WAY down after the blind test: the old 1.35/0.85
# manufactured "tech" and buried a hospitality CEO's real (Venus/Taurus) 10th.
# Now a light TIEBREAKER only — it nudges, it never overrides the chart.
ERA_WEIGHT = {
    "Rahu": 1.08, "Mercury": 1.05,
    "Jupiter": 0.96, "Ketu": 0.96,
    # Sun, Moon, Mars, Venus, Saturn = 1.0 (neutral)
}


def era_weight(planet: str) -> float:
    return ERA_WEIGHT.get(planet, 1.0)


# [kal / era-weighting — FIELD level] The sign gives the field; this nudges the
# RESULT toward present-age fields so a modern chart surfaces tech/commerce over
# purely traditional callings, when both are indicated. TUNABLE.
_FIELD_ERA = (
    (("technology", "innovation", "IT", "software", "science", "media", "commerce",
      "trade", "networks", "data", "engineering & systems", "startup"), 1.30),
    (("law", "teaching & academia", "publishing", "philosophy", "charity",
      "priesthood", "clergy"), 0.85),
)


# [nodal-axis venture rule] Rahu's HOUSE = the venture channel that amplifies;
# Ketu's = the one that dissolves. Keyed to the house's venture THEMES (5th =
# speculation/hospitality/creative — that's the restaurant), not the node's sign.
# MODEST multipliers — ONE factor, the significator synthesis still leads. TUNABLE.
NODE_BOOST, NODE_PENALTY = 1.18, 0.78
HOUSE_VENTURE = {
    1:  ("personal brand", "independent", "self-"),
    2:  ("finance", "banking", "food & agriculture", "savings"),
    3:  ("communication", "media", "writing", "sales", "transport"),
    4:  ("real estate", "property", "agriculture", "consumer goods", "vehicles"),
    5:  ("entertainment", "arts", "hospitality", "food & beverage", "sports",
         "creative", "speculation", "performance", "children"),
    6:  ("service", "health", "law", "operations", "labor"),
    7:  ("business", "trade", "diplomacy", "partnership", "client"),
    8:  ("research", "investigation", "surgery", "insurance",
         "other-people's-money", "occult", "security"),
    9:  ("teaching", "law", "publishing", "philosophy", "foreign", "advisory"),
    10: ("management", "government", "authority", "executive", "leadership"),
    11: ("technology", "commerce", "trade", "networks", "media", "innovation",
         "engineering & systems", "science", "software", "it / data", "it / software"),
    12: ("foreign", "healing", "spirituality", "charity", "behind-the-scenes"),
}


def _field_era(field: str) -> float:
    fl = field.lower()
    for keys, mult in _FIELD_ERA:
        if any(k in fl for k in keys):
            return mult
    return 1.0


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

        # [era-weighting] nudge each significator by the present-age weight so
        # modern-era fields (tech/commerce) rank above traditional ones when the
        # chart supports them.
        for p in list(votes.keys()):
            votes[p] *= era_weight(p)

        # Career FIELD = the two 10th-house SIGNS (D-1 birth + D-10 career chart),
        # each a STRONG BASE, plus each significator's fields from BOTH its D-1 and
        # D-10 sign. [de-overfit] balancing D-1↔D-10 keeps the real domain in the
        # BIRTH 10th (Joe's Taurus/Venus = hospitality) from being buried by the
        # D-10. Era nudge is applied ONCE (to votes above), not doubled on fields.
        field_w: dict = defaultdict(float)
        field_from: dict = defaultdict(set)

        def _add_sign(sign, weight, tag):
            for i, field in enumerate(SIGN_CAREERS.get(sign, [])[:3]):
                if field:
                    field_w[field] += weight * (1.0 - i * 0.15)
                    field_from[field].add(tag)

        _add_sign(d1_10sign, 2.6, f"10th-house sign · {d1_10sign} (birth chart)")
        _add_sign(d10_10sign, 2.6, f"10th sign · {d10_10sign} (career chart)")
        for planet, w in votes.items():
            d1s = (d1.get(planet) or {}).get("sign")
            d10s = (d10_pl.get(planet) or {}).get("sign")
            if d1s:
                _add_sign(d1s, w * 0.55, f"{planet} in {d1s} (birth)")
            if d10s:
                _add_sign(d10s, w * 0.55, f"{planet} in {d10s} (career chart)")
                disp = SIGN_LORD.get(d10s)
                for i, field in enumerate(PLANET_CAREERS.get(disp, [])[:2]):
                    field_w[field] += w * 0.25 * (1.0 - i * 0.2)
                    field_from[field].add(f"{d10s} ruled by {disp}")

        # [leadership level] Leo lagna / strong Sun / strong 10th-lord / raja-yoga
        # = an EXECUTIVE signature independent of domain (Rishipal=Director,
        # Joe=CEO are both leaders). Add leadership fields weighted by that signal.
        _lead = 0.0
        _sun = d1.get("Sun") or {}
        if d1_lagna == "Leo":
            _lead += 2.0
        if _sun.get("house") in (1, 10, 11):
            _lead += 1.0
        if _dignity("Sun", _sun.get("sign")):
            _lead += 1.0
        if _dignity(d1_10lord, (d1.get(d1_10lord) or {}).get("sign")):
            _lead += 1.0
        if any("raj" in str(y).lower() for y in (cd.get("yogas") or [])):
            _lead += 1.5
        leadership_level = "executive / leader" if _lead >= 2.5 else "individual / specialist"
        if _lead >= 2.5:
            for field in ("leadership & management", "executive roles"):
                field_w[field] += _lead * 0.8
                field_from[field].add("leadership signature (Sun/lagna/raja-yoga)")

        # [nodal-axis venture rule] ONE factor: Rahu's house-theme fields get a
        # modest boost (success channel), Ketu's a modest penalty (dissolution).
        # This is what drops Raman's restaurant (Ketu in 5th = speculation/
        # hospitality) while keeping tech (Rahu in 11th = technology/networks).
        _rahu_h = (d1.get("Rahu") or {}).get("house")
        _ketu_h = (d1.get("Ketu") or {}).get("house")
        _rahu_kw = HOUSE_VENTURE.get(_rahu_h, ())
        _ketu_kw = HOUSE_VENTURE.get(_ketu_h, ())
        nodal = {"rahu_house": _rahu_h, "ketu_house": _ketu_h}
        for f in list(field_w.keys()):
            fl = f.lower()
            if any(k in fl for k in _rahu_kw):
                field_w[f] *= NODE_BOOST
                field_from[f].add(f"Rahu(h{_rahu_h}) amplifies")
            if any(k in fl for k in _ketu_kw):
                field_w[f] *= NODE_PENALTY
                field_from[f].add(f"Ketu(h{_ketu_h}) dissolves")

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
                "nodal_axis": nodal, "leadership_level": leadership_level,
                "top_significator": top}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
