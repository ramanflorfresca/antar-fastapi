"""
antar_engine/planet_significations.py — Ask port Slice 1b: era- and
context-aware planet significations + functional strength.

The promise engine (Slice 1) scored planets by SIGN DIGNITY alone. That reads
the nodes (Rahu/Ketu) as "neutral" and misses the four things that actually make
a placement powerful — so a Rahu Mahadasha in the 11th with Sun+Venus (a
textbook modern tech/fame/gains chapter) scored as nothing. This module adds:

  1. Era-aware significations — each planet carries a CLASSICAL set and a MODERN
     set (Rahu-modern = technology / AI / media / fame / foreign / disruption).
  2. House-context strength — the nodes are functional benefits in the upachaya
     houses (3/6/11, 11th best for Rahu); polarity is house/theme dependent, not
     a flat minus.
  3. Conjunction color — a node takes on the significations & strength of the
     planets it sits with (Sun -> fame, Venus -> wealth/business).
  4. Dispositor channel — a node acts THROUGH its dispositor's house (Rahu in
     Scorpio -> Mars in the 10th -> the gains route into career).

Pure + fail-open. Feeds assess_promise (Stage 1) and, later, the dasha tone.
"""
from __future__ import annotations
from typing import List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

NODES = {"Rahu", "Ketu"}
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
DIGNITY_PTS = {"exalted": 2, "own": 2, "friendly": 1, "neutral": 0,
               "debilitated": -2}

UPACHAYA = {3, 6, 11}
KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
DUSTHANA = {8, 12}          # 6 is dusthana but ALSO upachaya — growth wins here

# ── era-aware significations (plain-English; classical + present-day) ────────
ERA_SIGNIFICATIONS = {
    "Sun":     {"classical": ["father", "authority", "soul", "health", "government"],
                "modern":    ["leadership", "fame", "public profile", "founder", "brand"]},
    "Moon":    {"classical": ["mother", "mind", "emotions", "public", "fluids"],
                "modern":    ["audience", "the public", "wellbeing", "consumer reach"]},
    "Mars":    {"classical": ["courage", "energy", "land", "siblings", "conflict"],
                "modern":    ["engineering", "surgery", "sports", "real estate", "drive"]},
    "Mercury": {"classical": ["intellect", "speech", "trade", "writing", "skill"],
                "modern":    ["software", "communication", "commerce", "data", "product"]},
    "Jupiter": {"classical": ["wisdom", "wealth", "children", "guru", "dharma"],
                "modern":    ["finance", "advising", "education", "expansion", "law"]},
    "Venus":   {"classical": ["wealth", "spouse", "luxury", "arts", "vehicles"],
                "modern":    ["business", "brand", "design", "media", "relationships"]},
    "Saturn":  {"classical": ["discipline", "labour", "longevity", "servants", "delay"],
                "modern":    ["systems", "operations", "infrastructure", "the long game"]},
    "Rahu":    {"classical": ["obsession", "foreign", "illusion", "outsider", "sudden"],
                "modern":    ["technology", "artificial intelligence", "media", "fame",
                              "virality", "foreign / global", "disruption",
                              "unconventional wealth"]},
    "Ketu":    {"classical": ["detachment", "moksha", "past life", "occult", "loss"],
                "modern":    ["research", "deep specialisation", "spirituality", "letting go"]},
}

# concern -> the plain themes that a planet's modern significations can match
_CONCERN_THEMES = {
    "career": {"leadership", "fame", "founder", "software", "business", "systems",
               "engineering", "product", "brand", "technology", "artificial intelligence"},
    "business": {"business", "commerce", "trade", "brand", "product", "technology",
                 "artificial intelligence", "media", "unconventional wealth"},
    "wealth": {"finance", "wealth", "business", "unconventional wealth"},
    "funding": {"finance", "wealth", "foreign / global", "unconventional wealth",
                "technology", "disruption"},
    "foreign": {"foreign / global", "foreign"},
    "speculation": {"virality", "disruption", "unconventional wealth", "technology"},
    "education": {"education", "data", "research", "deep specialisation"},
    "spiritual": {"spirituality", "moksha", "letting go", "research"},
    "marriage": {"relationships", "spouse"},
    "love": {"relationships"},
    "children": {"children"},
    "health": {"health", "wellbeing"},
    "property": {"real estate", "land", "vehicles"},
}


def _sig(planet: str, era: str = "modern") -> List[str]:
    return (ERA_SIGNIFICATIONS.get(planet) or {}).get(era, [])


def _lagna_idx(chart_data: dict) -> Optional[int]:
    lg = (chart_data or {}).get("lagna") or {}
    s = lg.get("sign") if isinstance(lg, dict) else None
    return SIGNS.index(s) if s in SIGNS else None


def _house_context_pts(planet: str, house) -> float:
    """Functional strength contribution from the bhava the planet sits in."""
    if not isinstance(house, int):
        return 0.0
    if planet == "Rahu":
        if house == 11:
            return 2.0                     # Rahu's strongest house — gains/fame
        if house in (3, 6):
            return 1.5                     # upachaya — ambition grows
        if house in KENDRA | TRIKONA:
            return 0.7
        if house in (8, 12):
            return -0.5                    # ambitious but turbulent, not a flat veto
        return 0.3
    if planet == "Ketu":
        if house in (3, 6, 11, 12):
            return 1.0                     # upachaya + moksha house
        if house in (1, 7):
            return -0.8
        return 0.0
    # non-nodes: standard bhava dignity
    if house in TRIKONA:
        return 1.0
    if house == 11:
        return 0.8
    if house in KENDRA:
        return 0.7
    if house == 2:
        return 0.4
    if house in DUSTHANA or house == 6:
        return -1.0
    return 0.0


def contextual_strength(planet: str, chart_data: dict) -> dict:
    """Functional strength of `planet` FOR PREDICTION — node/house/conjunction/
    dispositor aware. Returns {points ~[-2,2], factors[], summary, significations}.
    Fail-open: returns points=0 if unassessable."""
    out = {"points": 0.0, "factors": [], "summary": "", "significations": _sig(planet)}
    try:
        from antar_engine.antar_ephemeris import _planet_strength
    except Exception:
        _planet_strength = lambda p, s: "neutral"
    try:
        planets = (chart_data or {}).get("planets") or {}
        pd = planets.get(planet) or {}
        sign = pd.get("sign")
        house = pd.get("house")
        pts = 0.0
        facs = []

        hp = _house_context_pts(planet, house)
        pts += hp
        if house:
            facs.append(f"house {house} ({'+' if hp >= 0 else ''}{round(hp, 1)})")

        if planet in NODES:
            # conjunction color — planets sharing the node's house
            co = [p for p, d in planets.items()
                  if p != planet and isinstance(d, dict) and d.get("house") == house]
            if co:
                cvals = []
                for p in co:
                    ps = planets.get(p, {}).get("sign")
                    base = DIGNITY_PTS.get(_planet_strength(p, ps), 0) if ps in SIGNS else 0
                    cvals.append(base + (0.5 if p in BENEFICS else -0.2))
                cadd = 0.5 * (sum(cvals) / len(cvals))
                pts += cadd
                facs.append(f"conjunct {', '.join(co)} ({'+' if cadd >= 0 else ''}{round(cadd, 1)})")
            # dispositor channel — the node acts through its sign-lord's house
            disp = SIGN_LORDS.get(sign)
            if disp and disp in planets:
                dh = planets[disp].get("house")
                dadd = 0.4 * _house_context_pts(disp, dh)
                pts += dadd
                facs.append(f"via {disp} in house {dh} ({'+' if dadd >= 0 else ''}{round(dadd, 1)})")
        else:
            if sign in SIGNS:
                d = _planet_strength(planet, sign)
                dadd = 0.7 * DIGNITY_PTS.get(d, 0)
                pts += dadd
                facs.append(f"{d} in {sign} ({'+' if dadd >= 0 else ''}{round(dadd, 1)})")

        pts = max(-2.0, min(2.0, pts))
        out.update({"points": round(pts, 2), "factors": facs,
                    "summary": "; ".join(facs)})
    except Exception as e:
        out["error"] = str(e)
    return out


def dasha_relevance(planet: str, concern: str, concern_houses: List[int],
                    chart_data: dict) -> float:
    """How much the running chapter lord bears on `concern`: 1.0 if it occupies
    or rules a concern house, 0.6 if its MODERN significations match the concern
    theme, else 0.3 (the chapter always colours the period a little)."""
    try:
        planets = (chart_data or {}).get("planets") or {}
        ch = set(concern_houses or [])
        ph = (planets.get(planet) or {}).get("house")
        if ph in ch:
            return 1.0
        li = _lagna_idx(chart_data)
        if li is not None:
            ruled = {h for h in range(1, 13)
                     if SIGN_LORDS[SIGNS[(li + h - 1) % 12]] == planet}
            if ruled & ch:
                return 1.0
        themes = _CONCERN_THEMES.get(concern, set())
        if themes & set(_sig(planet, "modern")):
            return 0.6
    except Exception:
        pass
    return 0.3


def modern_significations(planet: str) -> List[str]:
    return _sig(planet, "modern")
