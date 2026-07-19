"""
Capability layer — "can this person actually do the job?"

Every other layer in compatibility_layers.py is *relational*: it scores the pair
(soul, chemistry, public, lifepath, communication, friction). None of them looks
at one person on their own, so a hiring question ("will they perform in a sales
role?") was being answered with a get-along score.

This module scores ONE chart's aptitude for a function, from that person's own
placements only. Nothing here touches the other party.

Astrological basis
------------------
D-10 (Dashamsa) is the classical divisional chart for profession and career
conduct — the right varga for "how do they operate at work", where D-1 shows the
vocation and D-9 shows the soul. We read three things:

  1. Function karakas in D-10  — the significators for that specific kind of
     work, by dignity and house.
  2. D-10 Lagna lord           — professional constitution overall.
  3. D-1 10th house            — karma-sthana; vocation in the birth chart.

Each karaka is scored by dignity (exalted/own/neutral/debilitated) and adjusted
by its D-10 house: kendras and trikonas support, upachayas reward effort over
time, dusthanas undercut.

The `drivers` returned alongside the score name the actual placement, so the
copy layer can say "Mercury is exalted in their D-10 tenth" instead of "a
workable fit with clear structure".
"""

from __future__ import annotations

from antar_engine.d_charts_calculator import (
    get_d_chart, SIGNS, SIGN_INDEX, SIGN_LORDS,
    EXALTATION, DEBILITATION, OWN_SIGNS,
)

# ── Function significators ──────────────────────────────────────────────────
# Weights sum to 1.0 within each role.
ROLE_KARAKAS = {
    # Persuasion + drive to close + the charm that makes people say yes.
    "sales":       [("Mercury", 0.40), ("Mars", 0.35), ("Venus", 0.25)],
    # Aesthetic judgement + message-craft + a read on public mood.
    "marketing":   [("Venus", 0.40), ("Mercury", 0.35), ("Moon", 0.25)],
    # Mass mood + wit + taste + Rahu, the classical significator of
    # amplification, novelty and sudden reach — the planet of going viral.
    "social":      [("Moon", 0.30), ("Mercury", 0.30), ("Rahu", 0.25), ("Venus", 0.15)],
    # Systems and process (Saturn) + coordination (Mercury) + execution (Mars).
    "operations":  [("Saturn", 0.40), ("Mercury", 0.35), ("Mars", 0.25)],
    # Dhana-karaka judgement + calculation + the discipline to be exact.
    "finance":     [("Jupiter", 0.40), ("Mercury", 0.35), ("Saturn", 0.25)],
    # Custodian of capital: judgement and controls outrank speed.
    "cfo":         [("Jupiter", 0.35), ("Saturn", 0.35), ("Mercury", 0.30)],
    # Vision and command, expansion judgement, decisiveness, endurance.
    "ceo":         [("Sun", 0.35), ("Jupiter", 0.25), ("Mars", 0.20), ("Saturn", 0.20)],
    # Logic + structure + the appetite to build and debug + inventiveness.
    "engineering": [("Mercury", 0.35), ("Saturn", 0.30), ("Mars", 0.20), ("Rahu", 0.15)],
    # Reading people, keeping harmony, giving counsel.
    "people":      [("Moon", 0.35), ("Venus", 0.35), ("Jupiter", 0.30)],
    # Dharma and argument and precision.
    "legal":       [("Jupiter", 0.40), ("Mercury", 0.35), ("Saturn", 0.25)],
    # Authority + responsibility + decisiveness under load.
    "managerial":  [("Sun", 0.40), ("Saturn", 0.35), ("Mars", 0.25)],
}

# Used for cofounder/business, where no single function is named: general
# capacity to build and carry a venture.
FOUNDER_KARAKAS = [("Sun", 0.30), ("Mars", 0.30), ("Saturn", 0.20), ("Mercury", 0.20)]

# What each karaka *means* for that role — used to build specific copy.
KARAKA_MEANING = {
    ("sales", "Mercury"):      "persuasion and negotiation",
    ("sales", "Mars"):         "drive to push and close",
    ("sales", "Venus"):        "rapport and likeability",
    ("marketing", "Venus"):    "aesthetic judgement and appeal",
    ("marketing", "Mercury"):  "message-craft and positioning",
    ("marketing", "Moon"):     "instinct for public mood",
    ("finance", "Jupiter"):    "judgement about money and risk",
    ("finance", "Mercury"):    "analysis and accuracy with numbers",
    ("finance", "Saturn"):     "discipline and audit rigour",
    ("managerial", "Sun"):     "authority and command",
    ("managerial", "Saturn"):  "responsibility and follow-through",
    ("managerial", "Mars"):    "decisiveness under pressure",
    ("social", "Moon"):        "instinct for what the crowd feels",
    ("social", "Mercury"):     "wit and quick output",
    ("social", "Rahu"):        "appetite for reach and novelty",
    ("social", "Venus"):       "taste and visual sense",
    ("operations", "Saturn"):  "process discipline",
    ("operations", "Mercury"): "coordination across moving parts",
    ("operations", "Mars"):    "getting things actually finished",
    ("cfo", "Jupiter"):        "judgement over capital",
    ("cfo", "Saturn"):         "controls and restraint",
    ("cfo", "Mercury"):        "command of the numbers",
    ("ceo", "Sun"):            "authority people follow",
    ("ceo", "Jupiter"):        "judgement about where to expand",
    ("ceo", "Mars"):           "decisiveness when it costs something",
    ("ceo", "Saturn"):         "endurance through the bad years",
    ("engineering", "Mercury"): "structured reasoning",
    ("engineering", "Saturn"):  "rigour and maintainable work",
    ("engineering", "Mars"):    "drive to build and debug",
    ("engineering", "Rahu"):    "inventiveness with new tools",
    ("people", "Moon"):        "reading how people actually feel",
    ("people", "Venus"):       "keeping harmony without avoiding truth",
    ("people", "Jupiter"):     "counsel people trust",
    ("legal", "Jupiter"):      "grasp of principle and dharma",
    ("legal", "Mercury"):      "argument and drafting",
    ("legal", "Saturn"):       "precision and patience",
    ("founder", "Sun"):        "vision and the will to lead",
    ("founder", "Mars"):       "execution and appetite for risk",
    ("founder", "Saturn"):     "staying power through the long middle",
    ("founder", "Mercury"):    "adaptability and commercial thinking",
}

_DIGNITY_SCORE = {"exalted": 95, "own": 82, "neutral": 55, "debilitated": 25}

# D-10 house adjustment. Kendra/trikona support professional expression;
# upachaya rewards accumulated effort; dusthana drains it.
_KENDRA   = (1, 4, 7, 10)
_TRIKONA  = (5, 9)
_UPACHAYA = (3, 11)
_DUSTHANA = (6, 8, 12)


def _dignity(planet: str, sign: str) -> str:
    if EXALTATION.get(planet) == sign:
        return "exalted"
    if sign in OWN_SIGNS.get(planet, []):
        return "own"
    if DEBILITATION.get(planet) == sign:
        return "debilitated"
    return "neutral"


def _house_adjust(house: int | None) -> tuple[int, str]:
    """Return (delta, plain-language note) for a D-10 house placement."""
    if not house:
        return 0, ""
    if house in _KENDRA:
        return +12, "well-placed in a kendra"
    if house in _TRIKONA:
        return +8, "supported in a trikona"
    if house in _UPACHAYA:
        return +5, "in a growth house — strengthens with experience"
    if house in _DUSTHANA:
        return -15, "in a difficult house"
    return 0, ""


def _d10_of(chart: dict) -> dict:
    """Prefer the stored d10; fall back to computing it. Normalised shape."""
    stored = (chart.get("divisional_charts") or {}).get("d10")
    if isinstance(stored, dict) and stored:
        out = {}
        for body, v in stored.items():
            if not isinstance(v, dict) or not v.get("sign"):
                continue
            out[body] = {"sign": v["sign"], "house": v.get("house")}
        if out:
            return out
    try:
        raw = get_d_chart(chart, 10)
    except Exception:
        return {}
    lagna_idx = (raw.get("Lagna") or {}).get("sign_index")
    out = {}
    for body, v in raw.items():
        si = v.get("sign_index")
        house = None
        if lagna_idx is not None and si is not None:
            house = ((si - lagna_idx) % 12) + 1
        out[body] = {"sign": v.get("sign"), "house": house}
    return out


def _karaka_score(planet: str, d10: dict) -> tuple[float, dict | None]:
    """Score one significator in D-10. Returns (0-100, driver-dict|None)."""
    node = d10.get(planet)
    if not node or not node.get("sign"):
        return 55.0, None  # unknown -> neutral, and no claim is made
    sign = node["sign"]
    house = node.get("house")
    dig = _dignity(planet, sign)
    delta, note = _house_adjust(house)
    score = max(0.0, min(100.0, _DIGNITY_SCORE[dig] + delta))
    return score, {
        "planet": planet, "sign": sign, "house": house,
        "dignity": dig, "house_note": note, "score": int(round(score)),
    }


def _d10_lagna_lord_score(chart: dict, d10: dict) -> tuple[float, dict | None]:
    """Dignity of the D-10 ascendant lord — overall professional constitution."""
    lag = d10.get("Lagna") or {}
    lag_sign = lag.get("sign")
    if not lag_sign:
        stored = (chart.get("divisional_charts") or {}).get("d10") or {}
        lag_sign = (stored.get("Lagna") or stored.get("lagna") or {}).get("sign") \
            if isinstance(stored.get("Lagna") or stored.get("lagna"), dict) else None
    if not lag_sign or lag_sign not in SIGN_LORDS:
        return 55.0, None
    lord = SIGN_LORDS[lag_sign]
    return _karaka_score(lord, d10)


def _d1_tenth_score(chart: dict) -> tuple[float, dict | None]:
    """Karma-sthana in the birth chart: occupants + lord dignity."""
    planets = chart.get("planets") or {}
    lagna_sign = (chart.get("lagna") or {}).get("sign")
    if not lagna_sign or lagna_sign not in SIGN_INDEX:
        return 55.0, None
    tenth_sign = SIGNS[(SIGN_INDEX[lagna_sign] + 9) % 12]
    lord = SIGN_LORDS[tenth_sign]
    lord_node = planets.get(lord) or {}
    lord_sign = lord_node.get("sign")
    if not lord_sign:
        return 55.0, None
    dig = _dignity(lord, lord_sign)
    score = float(_DIGNITY_SCORE[dig])
    # Occupants of the 10th nudge it either way.
    benefics, malefics = {"Jupiter", "Venus", "Mercury", "Moon"}, {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}
    occupants = [p for p, v in planets.items() if v.get("house") == 10]
    score += 6 * len([p for p in occupants if p in benefics])
    score -= 4 * len([p for p in occupants if p in malefics])
    score = max(0.0, min(100.0, score))
    return score, {
        "planet": lord, "sign": lord_sign, "house": None, "dignity": dig,
        "house_note": "lord of the 10th", "score": int(round(score)),
        "occupants": occupants,
    }


def karakas_for(reason: str, role: str | None) -> tuple[list, str]:
    """Return (karaka list, meaning-key) for a reason/role combination."""
    if reason in ("employee", "boss-or-manager") and role in ROLE_KARAKAS:
        return ROLE_KARAKAS[role], role
    return FOUNDER_KARAKAS, "founder"


def capability(chart: dict, reason: str, role: str | None) -> dict:
    """
    Score one person's aptitude for the function implied by reason/role.

    Returns {score, karakas[], drivers[], strongest, weakest, basis}.
    Never raises — a chart missing D-10 degrades to a neutral 55 with no
    drivers, so the copy layer stays quiet rather than inventing a claim.
    """
    d10 = _d10_of(chart)
    karakas, meaning_key = karakas_for(reason, role)

    drivers, total, wsum = [], 0.0, 0.0
    for planet, weight in karakas:
        sc, drv = _karaka_score(planet, d10)
        total += sc * weight
        wsum += weight
        if drv:
            drv["means"] = KARAKA_MEANING.get((meaning_key, planet), "")
            drv["weight"] = weight
            drivers.append(drv)
    karaka_avg = total / (wsum or 1.0)

    lag_sc, lag_drv = _d10_lagna_lord_score(chart, d10)
    tenth_sc, tenth_drv = _d1_tenth_score(chart)

    score = 0.65 * karaka_avg + 0.20 * lag_sc + 0.15 * tenth_sc
    score = int(round(max(0, min(100, score))))

    ranked = sorted(drivers, key=lambda d: d["score"], reverse=True)
    return {
        "score": score,
        "karakas": [p for p, _ in karakas],
        "drivers": ranked,
        "strongest": ranked[0] if ranked else None,
        "weakest": ranked[-1] if len(ranked) > 1 else None,
        "basis": {
            "karaka_avg": int(round(karaka_avg)),
            "d10_lagna_lord": int(round(lag_sc)),
            "d1_tenth": int(round(tenth_sc)),
            "d10_available": bool(d10),
        },
        "_lagna_driver": lag_drv,
        "_tenth_driver": tenth_drv,
    }


# ── Copy ────────────────────────────────────────────────────────────────────
# Lines are composed from the drivers, not selected from a static template
# bank, so the sentence names the placement that produced the score. If there
# are no drivers (chart missing D-10), we say nothing specific rather than
# reaching for a generic reassurance.

_DIGNITY_PHRASE = {
    "exalted":     "is exalted",
    "own":         "sits in its own sign",
    "neutral":     "sits neutral",
    "debilitated": "is debilitated",
}


def _clause(d: dict) -> str:
    """'Mercury is exalted in their D-10 tenth' — one factual clause."""
    bit = f"{d['planet']} {_DIGNITY_PHRASE.get(d['dignity'], 'sits')}"
    if d.get("house"):
        bit += f" in the {_ordinal(d['house'])} of their D-10"
    else:
        bit += " in their D-10"
    return bit


def _upper1(s: str) -> str:
    """Capitalise the first letter only — str.capitalize() would lowercase the
    rest and turn 'the CFO seat' into 'The cfo seat'."""
    return (s[:1].upper() + s[1:]) if s else s


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd", 21: "21st", 22: "22nd", 23: "23rd"}.get(
        n, f"{n}th")


def capability_line(cap: dict, b_name: str, role: str | None) -> str:
    """One sentence naming the real driver behind the capability score."""
    drivers = cap.get("drivers") or []
    if not drivers:
        return (f"{b_name}'s professional chart isn't detailed enough to read "
                f"capability — birth time would sharpen this.")

    top, low = drivers[0], drivers[-1]
    score = cap["score"]
    # "native rather than learned" is a claim about innate aptitude. Only a
    # dignified significator earns it — a neutral planet that scored well on
    # house placement alone does not, and saying so would be an overclaim.
    innate = top["dignity"] in ("exalted", "own")
    # NB: never .lower() a clause — it starts with a planet name and contains
    # "D-10". Sentences are built so the clause can sit capitalised.

    if score >= 75:
        if innate:
            s = f"{_clause(top)}, so {top['means']} is native rather than learned."
        else:
            s = (f"{b_name}'s strength here is placement rather than dignity: "
                 f"{_clause(top)}, which supports {top['means']}.")
        if low["score"] < 55 and low is not top:
            s += f" Watch {low['means']}: {_clause(low)}."
        return s

    if score >= 60:
        verb = "brings real" if innate else "has workable"
        s = f"{b_name} {verb} {top['means']} — {_clause(top)}."
        if low["score"] < 55 and low is not top:
            s += f" The gap is {low['means']}: {_clause(low)}."
        return s

    # Below 60 — be straight about it, and say what would compensate.
    s = f"{b_name}'s {low['means']} is the weak point here — {_clause(low)}."
    if top["score"] >= 65:
        s += f" What carries them is {top['means']}: {_clause(top)}."
    else:
        s += " Structure and a tight scope matter more than usual for this fit."
    return s


def capability_headline(cap: dict, b_name: str, role: str | None,
                        reason: str) -> str:
    """Short verdict used above the layer line."""
    score = cap["score"]
    what = {
        "sales":       "a sales seat",
        "marketing":   "a marketing seat",
        "social":      "running your social presence",
        "operations":  "an operations seat",
        "finance":     "a finance seat",
        "cfo":         "the CFO seat",
        "ceo":         "running the business",
        "engineering": "an engineering seat",
        "people":      "a people seat",
        "legal":       "a legal seat",
        "managerial":  "a management seat",
    }.get(role or "", "this kind of work")
    if reason in ("cofounder", "business"):
        what = "building something with you"
    # Phrasings must stay grammatical for both noun seats ("a sales seat") and
    # gerund seats ("running the business"), so no verb takes `what` as object.
    if score >= 78:
        return f"{b_name} is genuinely well-built for {what}."
    if score >= 65:
        return f"{b_name} is a solid fit for {what}, with known edges."
    if score >= 52:
        return f"{_upper1(what)} is within reach for {b_name}, with structure around them."
    return f"{_upper1(what)} runs against {b_name}'s natural grain."
