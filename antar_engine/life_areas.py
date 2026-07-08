"""
antar_engine/life_areas.py — house-anchored life-area taxonomy (Fix B).

The daily vote engine (today_highlight.py) historically tallied only 5 coarse
domains: money / work / relationships / body / mind. That granularity can't
ground the finer beats a warm whole-life reading needs — "your father", "your
network", "an expense" — so the narrator was free to invent them.

This module defines the FINER, house-anchored buckets the sources vote on, plus
a stable collapse back to the 5 legacy coarse domains. Every existing consumer
(headline templates, deep_read theme grouping, today_signal) keeps reading the
coarse `highlight_domains`; the new warm/gated narration reads the fine
`highlight_areas`. Same vote math — signed weights -> net per life-area ->
choose top N — just finer buckets. "father strain" can only appear if a source
actually voted on the 9th.

ZERO jargon leaves this module in any user-facing string: the labels here are
plain-English; house numbers live only in the anchor field for the evidence
trail and noun resolution.
"""
from __future__ import annotations
from typing import Optional

# slug -> (anchor_house | None for Moon, coarse_domain, headline_label,
#          polarity_bias). polarity_bias: +1 benefic house, -1 dusthana (6/8/12),
# 0 neutral — a tilt on Source A only; the truth of direction still comes from
# the day's overall bias (Source C / score).
LIFE_AREAS: dict = {
    "body":     (1,   "body",          "your body",                    0),
    "money":    (2,   "money",         "money",                       +1),
    "siblings": (3,   "work",          "communication and courage",   +1),
    "home":     (4,   "relationships", "home and family",             +1),
    "children": (5,   "relationships", "children and creativity",     +1),
    "health":   (6,   "body",          "your health",                 -1),
    "partner":  (7,   "relationships", "your partner",                 0),
    "depth":    (8,   "mind",          "deeper matters",              -1),
    "father":   (9,   "relationships", "father and fortune",          +1),
    "work":     (10,  "work",          "work",                        +1),
    "network":  (11,  "money",         "network and goals",           +1),
    "expense":  (12,  "money",         "spending and rest",           -1),
    "mind":     (None, "mind",         "your head",                    0),
}

# Fast lookups derived from the table.
AREA_HOUSE:    dict = {a: v[0] for a, v in LIFE_AREAS.items()}
AREA_COARSE:   dict = {a: v[1] for a, v in LIFE_AREAS.items()}
AREA_LABEL:    dict = {a: v[2] for a, v in LIFE_AREAS.items()}
AREA_POLARITY: dict = {a: v[3] for a, v in LIFE_AREAS.items()}

# house (1-12) -> the life-area anchored there.
HOUSE_TO_AREA: dict = {v[0]: a for a, v in LIFE_AREAS.items() if v[0] is not None}

# All votable areas, in canonical (house) order — mind last.
AREAS: tuple = tuple(LIFE_AREAS.keys())

# Legacy 5 coarse domains (frontend-locked). Kept for the collapse target.
COARSE_DOMAINS: tuple = ("money", "work", "relationships", "body", "mind")

# coarse domain -> its representative life-area (for mapping a coarse-only
# source, e.g. the patra prior, onto the fine tally space).
COARSE_TO_AREA: dict = {
    "money": "money", "work": "work", "body": "body", "mind": "mind",
    "relationships": "partner",   # the most common relationship concern
    "opportunity": "work", "watch": "health",
}

# coarse domain -> its primary house (for LK micros that only resolve to coarse).
COARSE_PRIMARY_HOUSE: dict = {
    "money": 2, "work": 10, "relationships": 7, "body": 1, "mind": None,
    "opportunity": 10, "watch": 6,
}

# LK fine micro-domain -> the house it truly points to. Overrides the lossy
# coarse round-trip so LK's own "father"/"mother"/"children"/"communication"
# signals land on the right life-area. Covers the EN + ES vocabulary that
# compute_lk_daily_diagnostic() actually emits (see highlight_templates.py).
LK_MICRO_TO_HOUSE: dict = {
    # 4th — home / mother / property / comfort
    "mother": 4, "madre": 4, "home": 4, "hogar": 4, "property": 4,
    "propiedad": 4, "comfort": 4, "confort": 4,
    # 9th — father / elders / higher law & wisdom / teaching
    "father": 9, "padre": 9, "elders": 9, "mayores": 9, "law": 9, "ley": 9,
    "teaching": 9, "enseñanza": 9, "wisdom": 9, "sabiduría": 9,
    # 5th — children / creativity / self-expression / learning
    "children": 5, "hijos": 5, "creativity": 5, "creatividad": 5,
    "self-expression": 5, "autoexpresión": 5, "learning": 5, "aprendizaje": 5,
    # 3rd — communication / writing / courage / initiative / action
    "communication": 3, "comunicación": 3, "writing": 3, "escritura": 3,
    "courage": 3, "coraje": 3, "initiative": 3, "iniciativa": 3,
    "action": 3, "acción": 3,
    # 7th — partnership / diplomacy / negotiation
    "relationships": 7, "relaciones": 7, "diplomacy": 7, "diplomacia": 7,
    "negotiation": 7, "negociación": 7,
    # 2nd — wealth / trade / luxury
    "wealth-growth": 2, "trade": 2, "luxury": 2,
    "crecimiento financiero": 2, "comercio": 2, "lujo": 2,
    # 10th — authority / discipline / structure / long-term / labor
    "authority": 10, "autoridad": 10, "leadership": 10, "liderazgo": 10,
    "discipline": 10, "disciplina": 10, "structure": 10, "estructura": 10,
    "long-term": 10, "largo plazo": 10, "labor": 10, "trabajo": 10,
    # 1st — vitality / beauty
    "vitality": 1, "vitalidad": 1, "beauty": 1, "belleza": 1,
    # 6th — conflict (friction)
    "conflict": 6, "conflicto": 6,
}


def lk_micro_to_area(micro: str) -> Optional[str]:
    """Map an LK fine micro-domain to a votable life-area. Prefer the direct
    house map; fall back through the legacy coarse map so nothing is dropped."""
    m = str(micro or "").strip().lower()
    if not m:
        return None
    h = LK_MICRO_TO_HOUSE.get(m)
    if h is not None:
        return HOUSE_TO_AREA.get(h)
    # fall back: coarse domain -> its primary house -> area.
    from antar_engine.highlight_templates import lk_micro_to_domain
    coarse = lk_micro_to_domain(m)
    if coarse == "mind":
        return "mind"
    hh = COARSE_PRIMARY_HOUSE.get(coarse)
    return HOUSE_TO_AREA.get(hh) if hh is not None else None


def coarse_of(area: str) -> str:
    """Collapse a fine life-area to one of the 5 legacy coarse domains."""
    return AREA_COARSE.get(area, "work")


def collapse(areas) -> list:
    """Ordered, de-duplicated coarse collapse of a list of fine areas."""
    out: list = []
    for a in (areas or []):
        c = coarse_of(a)
        if c not in out:
            out.append(c)
    return out


def area_from_coarse(coarse: str) -> Optional[str]:
    """Map a coarse-only source (e.g. patra) onto its representative area."""
    return COARSE_TO_AREA.get(str(coarse or "").strip().lower())


# ── Source D — dasha lord (the "through-line") ───────────────────────────────
# The running Mahadasha/Antardasha lord is the chapter the person is inside for
# months or years. It votes on the life-areas it RULES (lordship from the lagna)
# and OCCUPIES (natal placement), and carries a plain-English tone tag the
# narrator can voice as the day's through-line. ZERO jargon in the tone strings
# (no planet names) so they pass the narration scrub.

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# planet -> the felt texture of its chapter (plain English; NO planet names).
PLANET_TONE = {
    "Saturn":  "earned and real — what lands today comes through patience, not luck",
    "Jupiter": "expansive and fortunate — things open wider than usual today",
    "Mars":    "forceful and direct — push, but don't force what should stay whole",
    "Sun":     "visible and steady — you're seen today; lead from the front",
    "Venus":   "warm and relational — ease, comfort, and connection carry the day",
    "Mercury": "quick and clever — talk, deals, and paperwork move today",
    "Moon":    "shifting and feeling-led — read the room before you act",
    "Rahu":    "sudden and unconventional — an unusual opening appears; verify before you leap",
    "Ketu":    "inward and clearing — release more than you reach for today",
}


def _sign_in_house(lagna_sign: str, h: int) -> Optional[str]:
    if lagna_sign not in SIGNS:
        return None
    return SIGNS[(SIGNS.index(lagna_sign) + (h - 1)) % 12]


def houses_ruled(lagna_sign: str, planet: str) -> list:
    """Whole-sign houses (1-12 from the lagna) whose sign-lord is `planet`."""
    planet = (planet or "").strip().title()
    if lagna_sign not in SIGNS or not planet:
        return []
    return [h for h in range(1, 13)
            if SIGN_LORD.get(_sign_in_house(lagna_sign, h)) == planet]


def dasha_votes(lagna_sign: str, natal_planets: dict, lord: str) -> list:
    """The life-areas the dasha `lord` touches today: houses it rules + the
    house it occupies natally. Returns [(area, house), ...] de-duplicated."""
    lord = (lord or "").strip().title()
    if not lord:
        return []
    houses = set(houses_ruled(lagna_sign, lord))
    occ = (natal_planets.get(lord) or {}).get("house") if isinstance(natal_planets, dict) else None
    if isinstance(occ, int) and 1 <= occ <= 12:
        houses.add(occ)
    out = []
    for h in sorted(houses):
        area = HOUSE_TO_AREA.get(h)
        if area:
            out.append((area, h))
    return out


def dasha_tone(lord: str) -> str:
    return PLANET_TONE.get((lord or "").strip().title(), "")
