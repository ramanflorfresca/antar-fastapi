"""
antar_engine/career_mode.py
Job, business, or venture — as a GATE, not a ranking.        2026-07-22

The first version of this scored three modes and took the highest. It failed in
one consistent direction: it over-called enterprise. Two salaried technologists
out of three came back BUSINESS, and one of them showed exactly why.

Rishipal — Sagittarius lagna, Mars + Mercury + Venus in the 10th, 10th lord
Mercury at +2.0 — is a Big-5 consultant. A career that strong read as "works
for himself". It does not follow. THE 10TH IS STANDING, NOT OWNERSHIP. A
salaried consultant with three planets in the 10th has a superb career as an
employee. Weighting the 10th into all three modes simply inflated whichever
mode had the most other houses bolted on, which was always business.

So the 10th no longer discriminates. It says how prominent the career is, in
every mode equally. What discriminates is:

    6th   service — working under another
    7th   vyapara — trade, the market, the counterparty
    8th   other people's money, and the sudden turn
    3rd   self-initiated effort

And the structure is a gate rather than a contest. Independent enterprise needs
specific strength; employment is what happens WITHOUT it. Most working adults
carry moderate 7th/10th/11th points, so under a ranking "business" wins by
accumulation. Under a gate they simply fail to clear the bar, which is the
correct answer for most people.

The rules below are the classical ones, named individually so a reading can be
argued with. The two load-bearing ones are in every text:

    10th lord in the 6th, or 6th lord in the 10th   -> service
    10th lord in the 7th, or 7th lord in the 10th   -> business

Written BEFORE seeing any further outcome data, deliberately. The dasha finding
in this codebase held up because its mapping was fixed before the dates were
known; this keeps the same discipline.
"""

from typing import Dict, List, Optional

SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

MODE_JOB = "job"
MODE_BUSINESS = "business"
MODE_VENTURE = "venture"

# A chart must reach this to be read as independent at all. Below it, service.
ENTERPRISE_GATE = 2.5


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


def ownership_axis(chart: dict) -> Dict:
    """Owned or employed — a SEPARATE question from what kind of work it is.

    Collapsing this into the nature axis is what made every earlier version
    trade one bias for the other. JS reads service-natured because his 10th lord
    is in the 6th, and that is CORRECT — B2B SaaS with live clients is service
    work. He simply owns it. Rishipal reads trade-natured, also correct —
    consulting is transactional client work — but he does it inside a firm.

    Nature and ownership are independent, and the classical markers differ:
    Saturn is the karaka of working under another, the Sun of standing in your
    own name, Mars of initiative. The lagna lord tied to the 10th fuses self and
    career, which is what ownership actually means.
    """
    own, emp = 0.0, 0.0
    why: List[str] = []

    L1, L10, L6 = _lord_of(chart, 1), _lord_of(chart, 10), _lord_of(chart, 6)
    h_L1, h_L10 = _house_of(chart, L1), _house_of(chart, L10)
    h_sat, h_sun = _house_of(chart, "Saturn"), _house_of(chart, "Sun")

    if h_L1 == 10:
        own += 1.5; why.append("own+1.5: lagna lord in the 10th — the career carries your own name")
    if h_L10 == 1:
        own += 1.5; why.append("own+1.5: 10th lord in the 1st — self and profession fused")
    if h_sun == 10 or L10 == "Sun":
        own += 1.0; why.append("own+1: Sun on the career house — standing in your own right")
    if _strength(chart, "Mars") >= 1.0 and _house_of(chart, "Mars") in (1, 3, 10, 11):
        own += 1.0; why.append("own+1: Mars strong and placed for initiative")
    if _strength(chart, L1) >= 1.5:
        own += 0.5; why.append("own+0.5: lagna lord strong — self-directed")

    if h_sat == 10 or L10 == "Saturn":
        emp += 1.5; why.append("employed+1.5: Saturn on the career house — the karaka of serving another")
    if h_L10 == 6:
        emp += 1.5; why.append("employed+1.5: 10th lord in the 6th — the career sits in the house of service")
    if _house_of(chart, L6) == 10:
        emp += 1.0; why.append("employed+1: 6th lord in the 10th — employment defines the work")
    if _house_of(chart, "Moon") == 10:
        emp += 0.5; why.append("employed+0.5: Moon on the career house — works within another's structure")

    return {"owned": round(own, 2), "employed": round(emp, 2),
            "verdict": "owned" if own > emp else "employed", "reasons": why}


def career_mode(chart: dict) -> Dict:
    """Which way this chart earns: {mode, enterprise, service, reasons, prominence}."""
    if not chart or not chart.get("planets"):
        return {"mode": MODE_JOB, "enterprise": 0.0, "service": 0.0,
                "reasons": ["no chart data"], "prominence": 0.0}

    L10 = _lord_of(chart, 10)
    L7  = _lord_of(chart, 7)
    L6  = _lord_of(chart, 6)
    L8  = _lord_of(chart, 8)
    L3  = _lord_of(chart, 3)
    L11 = _lord_of(chart, 11)

    service, business, venture = 0.0, 0.0, 0.0
    reasons: List[str] = []

    def add(bucket: str, pts: float, why: str):
        nonlocal service, business, venture
        if bucket == "service":
            service += pts
        elif bucket == "business":
            business += pts
        else:
            venture += pts
        reasons.append(f"{bucket}+{pts:g}: {why}")

    # ── SERVICE ──────────────────────────────────────────────────────────
    if _house_of(chart, L10) == 6:
        add("service", 2.0, "10th lord sits in the 6th — the career operates as service")
    if _house_of(chart, L6) == 10:
        add("service", 1.5, "6th lord sits in the 10th — service defines the profession")
    if _house_of(chart, "Saturn") in (6, 10) or L10 == "Saturn":
        add("service", 1.0, "Saturn on the career axis — the karaka of working under another")
    if _strength(chart, L6) >= 1.0:
        add("service", 0.5, "6th lord well placed — thrives inside an organisation")

    # ── BUSINESS (trade) ─────────────────────────────────────────────────
    if _house_of(chart, L10) == 7:
        add("business", 2.0, "10th lord in the 7th — the profession IS the marketplace")
    if _house_of(chart, L7) == 10:
        add("business", 2.0, "7th lord in the 10th — trade occupies the career house")
    if _house_of(chart, L10) == 7 and _house_of(chart, L7) == 10:
        add("business", 1.0, "full exchange between 7th and 10th — the classic trade yoga")
    if _strength(chart, "Mercury") >= 1.0 and _house_of(chart, "Mercury") in (7, 10, 11):
        add("business", 1.0, "Mercury strong on a trade house — dealing, margin, turnover")
    if _strength(chart, L7) >= 1.5:
        add("business", 0.5, "7th lord strong — the counterparty side holds")

    # ── VENTURE (startup) ────────────────────────────────────────────────
    # A salary is your own 2nd house; outside capital is the 8th.
    if _house_of(chart, L8) in (10, 11):
        add("venture", 1.5, "8th lord on the career/gains axis — outside money funds the work")
    if _house_of(chart, L3) in (10, 11):
        add("venture", 1.0, "3rd lord on the career/gains axis — self-launched effort")
    if _house_of(chart, "Rahu") in (10, 11):
        add("venture", 1.5, "Rahu on the career/gains axis — unconventional, scale-seeking")
    if _strength(chart, "Rahu") >= 1.0 and _strength(chart, "Mercury") >= 1.0:
        add("venture", 0.5, "Rahu and Mercury both strong — technology at scale")

    # ── PROMINENCE — how big, in ANY mode. Deliberately not a discriminator.
    prominence = _strength(chart, L10) + 0.4 * sum(
        _strength(chart, p) for p in _occupants(chart, 10))

    # NATURE: what kind of work, regardless of who owns it.
    nature = max((service, "service"), (business, "trade"), (venture, "venture"))[1]
    own = ownership_axis(chart)

    # Legacy single answer, kept for callers that want one word.
    enterprise = max(business, venture)
    if own["verdict"] == "employed" or enterprise < ENTERPRISE_GATE:
        mode = MODE_JOB
    else:
        mode = MODE_BUSINESS if business >= venture else MODE_VENTURE

    return {
        "mode": mode,
        "nature": nature,
        "ownership": own["verdict"],
        "own_pts": own["owned"],
        "emp_pts": own["employed"],
        "ownership_reasons": own["reasons"],
        "enterprise": round(enterprise, 2),
        "service": round(service, 2),
        "business": round(business, 2),
        "venture": round(venture, 2),
        "prominence": round(prominence, 2),
        "reasons": reasons,
    }
