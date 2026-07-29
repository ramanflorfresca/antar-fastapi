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
_DEBIL = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
          "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
          "Saturn": "Aries"}

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

        # [government / politics axis] The Sun is the karaka of the king / the state.
        # A government or political career needs the Sun to actually SIGNIFY the
        # career (Amatyakaraka or a 10th-lord), not merely be well placed — that
        # gate keeps this off charts with an incidental strong Sun. When the Sun
        # governs the career AND authority is prominent (Leo 10th, Sun in 1/10/11),
        # surface government & politics above generic "public-facing" (Jose = govt
        # job, wants politics: Sun AmK + Leo 10th — the read was there but it ranked
        # under hospitality because "public-facing" swallowed it). TUNABLE.
        _gov = 0.0
        if amk == "Sun":
            _gov += 1.5
        if "Sun" in (d1_10lord, d10_10lord):
            _gov += 1.5
        if _sun.get("house") in (1, 10, 11):
            _gov += 1.0
        if "Leo" in (d1_10sign, d10_10sign):
            _gov += 1.0
        if _dignity("Sun", _sun.get("sign")):
            _gov += 0.5
        factors["gov_score"] = round(_gov, 2)
        if _gov >= 2.5:
            for field in ("government & authority", "politics"):
                field_w[field] += _gov * 0.75
                field_from[field].add("Sun governs the career (government/politics signature)")

        # [marketing / branding axis] Marketing/PR/branding = Venus (image, desire,
        # persuasion) carrying the message of Mercury (communication). But it is
        # ONLY marketing when the Venus is the EXPRESSIVE/communicative face —
        # Taurus/Libra/Gemini or in the 3rd (communication) house. Venus buried in
        # Virgo is the CRITICAL/analytical Venus (Rishipal = audit: Venus+Mercury
        # both in Virgo → that's accounting, not branding), so it must not fire.
        # Mercury adds only when it too speaks (Gemini/Libra or 3rd), never the
        # Virgo-analyst Mercury. This surfaces Susanna (Venus in own-sign Taurus =
        # marketing head) while leaving Rishipal's audit intact. TUNABLE.
        _VEN_EXPR = {"Taurus", "Libra", "Gemini"}
        _MER_COMM = {"Gemini", "Libra"}
        _ven = votes.get("Venus", 0.0)
        _mer = votes.get("Mercury", 0.0)
        _ven_p = d1.get("Venus") or {}
        _mer_p = d1.get("Mercury") or {}
        _ven_expressive = _ven_p.get("sign") in _VEN_EXPR or _ven_p.get("house") == 3
        _mer_comm = _mer >= 1.0 and (_mer_p.get("sign") in _MER_COMM or _mer_p.get("house") == 3)
        factors["marketing_score"] = round(_ven if _ven_expressive else 0.0, 2)
        if _ven >= 2.0 and _ven_expressive:
            field_w["marketing & branding"] += _ven * 1.3 + (_mer * 0.8 if _mer_comm else 0.0)
            field_from["marketing & branding"].add(
                "expressive Venus (image/persuasion) = marketing/branding")

        # [construction gate — de-index Saturn] Saturn / Capricorn on their own mean
        # STRUCTURE: business, management, operations, government — NOT physical
        # construction. Construction / mining / heavy-industry needs Mars (the
        # builder's hand, machinery, labor) actually signifying the career. Without
        # a Mars significator, demote it so a corporate Capricorn (Susanna) isn't
        # miscast as a builder. TUNABLE.
        _mars_is_sig = votes.get("Mars", 0.0) >= 1.5
        if not _mars_is_sig:
            for f in list(field_w.keys()):
                fl = f.lower()
                if any(k in fl for k in ("construction", "mining", "heavy industry")):
                    field_w[f] *= 0.7

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


# ═══════════════════════════════════════════════════════════════════════════
# DASHA-TIMED CAREER TIMELINE
# ───────────────────────────────────────────────────────────────────────────
# The static ranking above answers "which field fits the chart." But a career is
# LIVED IN CHAPTERS: each Vimśottarī mahādasha (6–20 yrs) switches on a different
# planet, and THAT planet's placement — read in the D-10 (career chart) and D-9 —
# is the arena and field that actually activates. This is the astrologer's real
# method and the answer to "which profession, at what time":
#   for the dasha lord → where does it sit in the D-10 (house = arena, sign =
#   field) and D-9 → that is the chapter. (User's own read: "my Rahu in D-10 is
#   8th/Sagittarius and my Rahu dasha is starting" → a foreign/deep venture turn.)
# Deliberately SIMPLE — one clean chapter line per dasha, current one flagged.

# The life-MODE a mahadasha runs in — the nature of the period, independent of
# field. This is WHY people change careers 2–3 times: each chapter reweights
# which significator is lit.
PLANET_CHAPTER = {
    "Sun":     "authority & visibility — stepping into leadership, government, or your own name",
    "Moon":    "public & people — the public, care, home/roots, an emotional cadence",
    "Mars":    "initiative & independence — breaking out on your own, competing, building",
    "Mercury": "commerce & communication — trade, learning, deals, versatility, words",
    "Jupiter": "expansion & counsel — growth, teaching/advising, scaling up, wisdom",
    "Venus":   "relationships & craft — arts, brand, comfort, partnerships, the good life",
    "Saturn":  "the long grind — structure, service, discipline; slow but durable reward",
    "Rahu":    "ambition & disruption — ventures, foreign/new fields, sudden elevation, risk",
    "Ketu":    "dissolution & depth — letting go, spiritual/behind-scenes, research, a niche",
}

# What a house MEANS inside the D-10 (career chart) — the ARENA a chapter plays in.
D10_HOUSE_ARENA = {
    1:  "your own standing & personal brand — visible, independent",
    2:  "earnings & accumulated professional value",
    3:  "communication, skill & self-effort — media, writing, hustle",
    4:  "foundations, a home-base or workplace, real estate/comfort",
    5:  "creativity, intelligence & speculation — advisory, ideas",
    6:  "service, employment & competition — daily work, problem-solving",
    7:  "business, partnership & the market — clients, dealings",
    8:  "sudden shifts & transformation — research, deep/hidden or other-people's-money, upheaval",
    9:  "fortune, higher knowledge & the foreign — mentorship, big vision",
    10: "the peak of the profession — command, authority, government",
    11: "gains, income realization & large networks",
    12: "foreign lands, behind-the-scenes & exit — dissolution, spiritual work",
}


def _career_lord_fields(lord: str, d1: dict, d10_pl: dict) -> list:
    """Top fields a dasha lord ACTIVATES — led by its D-10 sign (the career
    close-up), then its D-1 sign, then its own significations."""
    fw: dict = defaultdict(float)
    d1s = (d1.get(lord) or {}).get("sign")
    d10s = (d10_pl.get(lord) or {}).get("sign")
    for i, f in enumerate(SIGN_CAREERS.get(d10s, [])[:3]):   # D-10 sign leads
        fw[f] += 1.0 * (1.0 - i * 0.2)
    for i, f in enumerate(SIGN_CAREERS.get(d1s, [])[:2]):
        fw[f] += 0.6 * (1.0 - i * 0.2)
    for i, f in enumerate(PLANET_CAREERS.get(lord, [])[:2]):
        fw[f] += 0.4 * (1.0 - i * 0.2)
    return [f for f, _ in sorted(fw.items(), key=lambda x: x[1], reverse=True)][:3]


def career_timeline(chart_data: dict, dashas: dict, today: Optional[str] = None) -> dict:
    """Career chapters by Vimśottarī mahadasha, each read through the dasha lord's
    D-10 (arena+field) and D-9 (inner confirmation). Returns
    {available, chapters[], current, next_chapter, summary}. Never raises."""
    try:
        from datetime import date
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        dv = cd.get("divisional_charts") or {}
        d10_pl = ((dv.get("d10") or {}).get("planets") or {})
        d9_pl = ((dv.get("d9") or {}).get("planets") or {})
        if not d1 or not lagna:
            return {"available": False}

        # Extract the Vimśottarī mahadasha sequence from the payload.
        vim = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
        raw = []
        for p in vim if isinstance(vim, list) else []:
            if not isinstance(p, dict):
                continue
            lord = (p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("lord") or "")
            lord = str(lord).title()
            s = str(p.get("start_date") or p.get("start") or "")[:10]
            e = str(p.get("end_date") or p.get("end") or "")[:10]
            lvl = str(p.get("level") or p.get("type") or "").lower()
            dur = float(p.get("duration_years") or p.get("duration") or 0) or 0.0
            if lord and s and e:
                raw.append({"lord": lord, "start": s, "end": e, "level": lvl, "dur": dur})
        # Prefer rows explicitly tagged mahadasha; else fall back to the long ones
        # (mahadashas are 6–20 yrs; antardashas are < ~3 yrs).
        mds = [r for r in raw if r["level"] in ("mahadasha", "maha", "md")]
        if not mds:
            mds = [r for r in raw if r["dur"] >= 5.0]
        if not mds:
            return {"available": False}
        mds.sort(key=lambda x: x["start"])

        today = today or date.today().isoformat()
        birth_year = int(mds[0]["start"][:4])
        cur_idx = None
        for i, m in enumerate(mds):
            if m["start"] <= today <= m["end"]:
                cur_idx = i
                break

        def _tone(lord):
            d10s = (d10_pl.get(lord) or {}).get("sign")
            d1s = (d1.get(lord) or {}).get("sign")
            for s in (d10s, d1s):
                if _EXALT.get(lord) == s or s in _OWN.get(lord, set()):
                    return "rise / favourable"
                if _DEBIL.get(lord) == s:
                    return "testing — effort before reward"
            return "steady"

        def _phase(i):
            if cur_idx is None:
                return "future" if mds[i]["start"] > today else "past"
            if i == cur_idx:
                return "current"
            if i == cur_idx + 1:
                return "next"
            return "past" if i < cur_idx else "future"

        chapters = []
        for i, m in enumerate(mds):
            end_year = int(m["end"][:4])
            start_year = int(m["start"][:4])
            # only career-relevant chapters (age ~16+), and don't run past next+1
            if end_year < birth_year + 16:
                continue
            if cur_idx is not None and i > cur_idx + 2:
                continue
            lord = m["lord"]
            d10h = (d10_pl.get(lord) or {}).get("house")
            d10s = (d10_pl.get(lord) or {}).get("sign")
            d9h = (d9_pl.get(lord) or {}).get("house")
            fields = _career_lord_fields(lord, d1, d10_pl)
            arena = D10_HOUSE_ARENA.get(d10h, "")
            chapters.append({
                "lord": lord,
                "phase": _phase(i),
                "years": f"{start_year}–{end_year}",
                "age": f"{max(0, start_year - birth_year)}–{end_year - birth_year}",
                "nature": PLANET_CHAPTER.get(lord, ""),
                "d10_house": d10h, "d10_sign": d10s, "d10_arena": arena,
                "d9_house": d9h,
                "fields": fields,
                "tone": _tone(lord),
            })

        def _line(ch):
            arena = f" in the arena of {ch['d10_arena']}" if ch["d10_arena"] else ""
            where = ""
            if ch["d10_sign"] and ch["d10_house"]:
                where = (f" In your career chart {ch['lord']} sits in {ch['d10_sign']} "
                         f"(house {ch['d10_house']}){arena}.")
            return (f"{ch['years']} (age {ch['age']}) · {ch['lord']} period — "
                    f"{ch['nature']}.{where} Activates: {', '.join(ch['fields'])}. "
                    f"Tone: {ch['tone']}.")

        for ch in chapters:
            ch["line"] = _line(ch)

        current = next((c for c in chapters if c["phase"] == "current"), None)
        nxt = next((c for c in chapters if c["phase"] == "next"), None)

        if current:
            summary = ("Right now you are in your " + current["lord"]
                       + f" period ({current['years']}) — {current['nature'].split(' — ')[0]}"
                       + f". It activates {', '.join(current['fields'])}.")
            if nxt:
                summary += (f" Next opens your {nxt['lord']} period ({nxt['years']}), "
                            f"shifting toward {', '.join(nxt['fields'][:2])}.")
        else:
            summary = ""

        return {"available": True, "chapters": chapters,
                "current": current, "next_chapter": nxt, "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
