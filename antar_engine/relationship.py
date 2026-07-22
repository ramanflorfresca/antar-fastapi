"""
antar_engine/relationship.py
Marriage, friction, separation — the 7th house and everything that touches it.

The daily `people` domain was drawing from the 7th alone and sat STEADY on 27 of
28 measured chart-days. That is a texture reading, not a relationship reading,
and relationships are the second thing people bring to an astrologer after money.

The classical spread is wider than the 7th:

    7th   the spouse, the marriage itself, any partnership
    2nd   kutumba — the family that forms, and the 8th FROM the 7th, which is
          why it carries the marriage's own vulnerability
    4th   domestic peace, the home the marriage lives in
    5th   romance, courtship, children — love BEFORE or OUTSIDE marriage
    6th   conflict, litigation, the mechanics of separation
    8th   mangalya sthana — the longevity of the bond, and intimacy
    12th  bed pleasures, what is private, what is hidden
    Venus kalatra karaka, the significator of the spouse
    Jupiter for a woman's chart, the pati karaka

WHAT THIS MODULE WILL NOT DO
----------------------------
It will not assert that anyone is having an affair. A chart can show a pattern
— secrecy, divided attention, a 12th-house pull on the 7th — in the person
whose chart it is. It cannot know a fact about another human being's behaviour,
and telling a user their spouse is unfaithful on that basis would be indefensible
and, if wrong, destructive. The vocabulary here is deliberately about the
NATIVE'S OWN pattern and pressures, never an accusation about a partner.

Nor does it predict divorce as an event. It reports friction and its sources.
The difference matters: friction is readable, an outcome is not.
"""

from typing import Dict, List, Optional

SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

# Kuja dosha — Mars in these houses stresses the marriage axis. Counted from
# the lagna; the classical set also counts from the Moon and from Venus, which
# is why the reading below checks all three rather than the lagna alone.
_KUJA_HOUSES = (1, 2, 4, 7, 8, 12)


def _lagna_index(chart: dict) -> int:
    lg = (chart or {}).get("lagna") or {}
    i = lg.get("sign_index")
    return i if isinstance(i, int) and 0 <= i <= 11 else 0


def _lord_of(chart: dict, house: int) -> str:
    return SIGN_LORD[(_lagna_index(chart) + house - 1) % 12]


def _house_of(chart: dict, planet: str) -> Optional[int]:
    d = ((chart or {}).get("planets") or {}).get(planet) or {}
    h = d.get("house")
    return h if isinstance(h, int) else None


def _occupants(chart: dict, house: int) -> List[str]:
    return [p for p, d in ((chart or {}).get("planets") or {}).items()
            if isinstance(d, dict) and d.get("house") == house]


def _strength(chart: dict, planet: str) -> float:
    try:
        from antar_engine.planet_significations import contextual_strength
        return float((contextual_strength(planet, chart) or {}).get("points") or 0.0)
    except Exception:
        return 0.0


def _house_from(chart: dict, planet: str, target: str) -> Optional[int]:
    """House position of `target` counted FROM `planet` (1 = same house)."""
    a, b = _house_of(chart, planet), _house_of(chart, target)
    if a is None or b is None:
        return None
    return ((b - a) % 12) + 1


def relationship_reading(chart: dict, gender: Optional[str] = None) -> Dict:
    """Marriage promise, friction, and where the pressure comes from."""
    if not chart or not chart.get("planets"):
        return {"available": False}

    L7, L6, L12, L8 = (_lord_of(chart, 7), _lord_of(chart, 6),
                       _lord_of(chart, 12), _lord_of(chart, 8))
    h_L7 = _house_of(chart, L7)

    promise, friction, privacy = 0.0, 0.0, 0.0
    p_why: List[str] = []
    f_why: List[str] = []
    v_why: List[str] = []

    # ── PROMISE — does the chart support a durable partnership at all ────
    s_L7 = _strength(chart, L7)
    promise += s_L7
    p_why.append(f"7th lord {L7} at {s_L7:+.1f}")

    # Venus is the karaka of the spouse in every chart; Jupiter carries the
    # husband in a woman's. Both are read, weighted by which applies.
    s_ven = _strength(chart, "Venus")
    promise += 0.6 * s_ven
    p_why.append(f"Venus (significator of the spouse) at {s_ven:+.1f}")
    if (gender or "").lower().startswith("f"):
        s_jup = _strength(chart, "Jupiter")
        promise += 0.5 * s_jup
        p_why.append(f"Jupiter (pati karaka) at {s_jup:+.1f}")

    for occ in _occupants(chart, 7):
        if occ in _BENEFIC:
            promise += 0.5
            p_why.append(f"{occ}, a benefic, sits in the 7th")

    if h_L7 in (1, 4, 5, 7, 9, 10):
        promise += 0.7
        p_why.append(f"7th lord in house {h_L7} — a supported placement")

    # ── FRICTION — where the pressure on the bond comes from ─────────────
    if h_L7 in (6, 8, 12):
        friction += 1.5
        f_why.append(f"7th lord in the {h_L7}th — the partnership sits in a house of "
                     f"{'conflict' if h_L7 == 6 else 'crisis' if h_L7 == 8 else 'loss'}")

    for occ in _occupants(chart, 7):
        if occ == "Saturn":
            friction += 1.2
            f_why.append("Saturn in the 7th — delay, distance, duty in place of warmth")
        elif occ == "Mars":
            friction += 1.2
            f_why.append("Mars in the 7th — heat and argument on the partnership axis")
        elif occ in ("Rahu", "Ketu"):
            friction += 1.0
            f_why.append(f"{occ} in the 7th — the axis is unsettled; expectation and "
                         f"reality keep missing each other")
        elif occ == "Sun":
            friction += 0.6
            f_why.append("Sun in the 7th — ego meets the partner head-on")

    # Kuja dosha, checked from lagna, Moon and Venus as the texts require.
    kuja = []
    if _house_of(chart, "Mars") in _KUJA_HOUSES:
        kuja.append("lagna")
    if _house_from(chart, "Moon", "Mars") in _KUJA_HOUSES:
        kuja.append("Moon")
    if _house_from(chart, "Venus", "Mars") in _KUJA_HOUSES:
        kuja.append("Venus")
    if kuja:
        friction += 0.5 * len(kuja)
        f_why.append(f"Mars stresses the marriage axis from {', '.join(kuja)} "
                     f"({len(kuja)} of 3 references) — the classical Kuja dosha")

    if _house_of(chart, L6) == 7 or _house_of(chart, L7) == 6:
        friction += 1.0
        f_why.append("the 6th and 7th are linked — conflict is structurally part of "
                     "how this person partners")

    if s_ven <= -1.0:
        friction += 0.8
        f_why.append(f"Venus itself is under pressure ({s_ven:+.1f})")

    # ── PRIVACY — the 12th on the 7th. NOT an accusation. ────────────────
    # This reads as: what is private, unspoken, or kept separate in the way
    # THIS person relates. It is reported as a pattern to be aware of, never as
    # a claim about a partner's conduct.
    if _house_of(chart, L12) == 7 or _house_of(chart, L7) == 12:
        privacy += 1.0
        v_why.append("the 12th and 7th are linked — a private, interior dimension to "
                     "partnership; things go unsaid")
    if _house_of(chart, "Venus") == 12:
        privacy += 0.8
        v_why.append("Venus in the 12th — affection is expressed privately, and can be "
                     "kept apart from the rest of life")
    if _house_of(chart, "Rahu") == _house_of(chart, "Venus"):
        privacy += 0.8
        v_why.append("Rahu with Venus — appetite outruns judgement in matters of "
                     "attraction; the classical caution here is against impulse, not a "
                     "statement about anyone's conduct")
    if _house_of(chart, L7) == 5 or _house_of(chart, _lord_of(chart, 5)) == 7:
        privacy += 0.5
        v_why.append("the 5th and 7th are linked — romance and partnership blur into "
                     "each other")

    band = ("strong" if promise >= 2.0 else
            "workable" if promise >= 0.5 else
            "needs care")
    fband = ("high" if friction >= 3.0 else
             "moderate" if friction >= 1.5 else
             "low")

    return {
        "available": True,
        "promise": round(promise, 2),
        "promise_band": band,
        "promise_reasons": p_why,
        "friction": round(friction, 2),
        "friction_band": fband,
        "friction_reasons": f_why,
        "privacy": round(privacy, 2),
        "privacy_reasons": v_why,
        "seventh_lord": L7,
        "seventh_lord_house": h_L7,
        "seventh_occupants": _occupants(chart, 7),
    }
