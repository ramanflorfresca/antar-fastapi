"""
antar_engine/subject_promise.py
Is THIS subject promised in THIS chart?  (2026-07-21)

The gap this closes: "promise" was being answered with one fixed set of wealth
yogas (2/9/11) regardless of what was asked. So a FUNDING question — which lives
in the 8th (other people's money) — never looked at the 8th at all, and a career
question never looked at the 10th. The promise was generic; only the question
changed.

A reader does the opposite: take the houses the question actually belongs to,
look at THEIR lords — dignity, placement, whether they talk to each other, what
afflicts them — and say whether that specific thing is supported. Then check
whether the running or upcoming dasha belongs to one of those lords, because a
promise nobody's period activates is a promise that stays on paper.

Everything here is derived from D-1 plus the lords involved; nothing is invented.
When the chart cannot be read the functions return a "no_data" verdict rather
than a confident guess.
"""

from typing import Dict, List, Optional

from antar_engine.d_charts_calculator import (
    SIGNS, SIGN_LORDS, OWN_SIGNS, EXALTATION, DEBILITATION,
    get_house_lord as _dc_house_lord,
)

# Houses that consume rather than deliver — a subject lord parked here is
# working uphill (6 = debt/conflict, 8 = disruption/OPM, 12 = loss/expense).
_DUSTHANA = {6, 8, 12}
_KENDRA = {1, 4, 7, 10}
_TRIKONA = {1, 5, 9}

# What each house actually promises, in the user's terms — used verbatim in the
# evidence lines so the reasoning is legible instead of "the 11th lord".
HOUSE_MEANING = {
    1:  "you yourself, vitality, how you show up",
    2:  "your own money, savings, what you accumulate",
    3:  "your own effort, outreach, communication",
    4:  "home, property, inner base",
    5:  "creativity, speculation, children",
    6:  "debt, competition, staff and daily service",
    7:  "clients, partners, the market, the other party",
    8:  "other people's money — investors, loans, inheritance",
    9:  "fortune, mentors, belief, the long arc",
    10: "the enterprise, standing, public work",
    11: "gains realised, income, network, customers",
    12: "expense, foreign, letting go",
}

# Subject -> the houses that actually carry it. This is the piece that was
# missing: the promise is read from THESE, not from a fixed wealth set.
SUBJECT_HOUSES: Dict[str, List[int]] = {
    "funding":   [8, 11, 2],      # OPM first, then gains, then own base
    "loan":      [6, 8, 2],       # debt-taking, OPM, capacity to service
    "investor":  [8, 11, 7],      # OPM, gains, the counterparty
    "business":  [7, 10, 11],     # market, enterprise, gains
    "startup":   [7, 10, 11],
    "sales":     [7, 11, 3],      # market, gains, own outreach
    "career":    [10, 6, 2],      # standing, service, income from it
    "job":       [10, 6, 2],
    "wealth":    [2, 11, 9],
    "property":  [4, 2, 11],
    "marriage":  [7, 2, 11],
    "health":    [1, 6, 8],
    "education": [4, 5, 9],
    "legal":     [6, 7, 8],
    "children":  [5, 9, 2],
    "travel":    [9, 12, 4],
}


def _sign_of(planet: str, planets: dict) -> str:
    p = planets.get(planet) or {}
    return p.get("sign", "") if isinstance(p, dict) else ""


def _house_of(planet: str, planets: dict) -> Optional[int]:
    p = planets.get(planet) or {}
    h = p.get("house") if isinstance(p, dict) else None
    try:
        return int(h)
    except (TypeError, ValueError):
        return None


def house_lord(lagna_sign: str, house: int) -> str:
    """Whole-sign: the lord of the Nth sign from lagna."""
    try:
        return _dc_house_lord(lagna_sign, house)
    except Exception:
        pass
    try:
        idx = (SIGNS.index(lagna_sign) + house - 1) % 12
        return SIGN_LORDS[SIGNS[idx]]
    except Exception:
        return ""


def _dignity(planet: str, planets: dict) -> str:
    s = _sign_of(planet, planets)
    if not s:
        return "unknown"
    if s == EXALTATION.get(planet):
        return "exalted"
    if s in (OWN_SIGNS.get(planet) or []):
        return "own"
    if s == DEBILITATION.get(planet):
        return "debilitated"
    return "neutral"



def neecha_bhanga(planet: str, planets: dict) -> dict:
    """Is a debilitation cancelled? (Neecha Bhanga Raja Yoga)

    Scoring a debilitation as a flat negative is how this module first read a
    live, revenue-generating business as "weak": the 10th lord was debilitated
    but CANCELLED, which classically inverts it into strength rather than
    weakness. Two standard conditions, either sufficient:
      1. the dispositor (lord of the debilitation sign) sits in a kendra
      2. the planet that exalts in that sign sits in a kendra
    """
    sign = _sign_of(planet, planets)
    if not sign or sign != DEBILITATION.get(planet):
        return {"cancelled": False, "reasons": []}
    reasons = []
    disp = SIGN_LORDS.get(sign)
    if disp and _house_of(disp, planets) in _KENDRA:
        reasons.append(f"its dispositor {disp} sits in a kendra")
    for p, ex in EXALTATION.items():
        if ex == sign and _house_of(p, planets) in _KENDRA:
            reasons.append(f"{p}, which exalts in {sign}, sits in a kendra")
            break
    return {"cancelled": bool(reasons), "reasons": reasons}


def assess_subject_promise(chart_data: dict, subject: str,
                           houses: Optional[List[int]] = None) -> dict:
    """Is this specific subject supported by this specific chart?

    Reads the lords of the subject's own houses: dignity, where they sit,
    whether they connect to each other. Returns a graded verdict plus the
    evidence in plain language, so the reading can show its work.
    """
    try:
        planets = chart_data["planets"]
        lagna = chart_data["lagna"]["sign"]
    except Exception:
        return {"verdict": "no_data", "score": 0, "evidence": [], "houses": []}

    hs = houses or SUBJECT_HOUSES.get((subject or "").lower()) or [10, 11]
    evidence: List[str] = []
    score = 0
    lords: Dict[int, str] = {}

    for h in hs:
        lord = house_lord(lagna, h)
        if not lord:
            continue
        lords[h] = lord
        dig = _dignity(lord, planets)
        pos = _house_of(lord, planets)
        meaning = HOUSE_MEANING.get(h, f"house {h}")

        if dig in ("exalted", "own"):
            score += 2
            evidence.append(f"{lord} rules {meaning} and is {dig} — that source is strong.")
        elif dig == "debilitated":
            nb = neecha_bhanga(lord, planets)
            if nb["cancelled"]:
                score += 2
                evidence.append(
                    f"{lord} rules {meaning} — debilitated but CANCELLED "
                    f"({nb['reasons'][0]}), which turns the weakness into strength."
                )
            else:
                score -= 2
                evidence.append(f"{lord} rules {meaning} but is debilitated — that source needs deliberate support.")
        else:
            evidence.append(f"{lord} rules {meaning}, in neutral dignity.")

        _cancelled = dig == "debilitated" and neecha_bhanga(lord, planets)["cancelled"]
        if pos in _DUSTHANA and not _cancelled:
            score -= 1
            evidence.append(f"  …and sits in the {pos}th ({HOUSE_MEANING.get(pos, '')}) — it pays a cost to deliver.")
        elif pos in _KENDRA or pos in _TRIKONA:
            score += 1
            evidence.append(f"  …and sits in the {pos}th, a strong angle — it has a platform to work from.")

    # Do the subject's own lords talk to each other? A connected pair is the
    # difference between "the ingredients exist" and "they combine".
    ls = list(dict.fromkeys(lords.values()))
    for i in range(len(ls)):
        for j in range(i + 1, len(ls)):
            a, b = ls[i], ls[j]
            ha, hb = _house_of(a, planets), _house_of(b, planets)
            if ha and hb and ha == hb:
                score += 2
                evidence.append(f"{a} and {b} sit together in the {ha}th — the parts of this combine.")
            elif (_sign_of(a, planets) in (OWN_SIGNS.get(b) or [])
                  and _sign_of(b, planets) in (OWN_SIGNS.get(a) or [])):
                score += 3
                evidence.append(f"{a} and {b} are in exchange — a strong, self-reinforcing link.")

    verdict = ("strong" if score >= 5 else "supported" if score >= 2
               else "mixed" if score >= 0 else "weak")
    return {
        "verdict": verdict,
        "score": score,
        "houses": hs,
        "lords": lords,
        "evidence": evidence,
        "subject": subject,
    }


def dasha_relevance(subject_result: dict, md_lord: str = "",
                    ad_lord: str = "") -> dict:
    """Does the running period belong to the subject, or to something else?

    This is the step that decides whether a promise is live now or merely on
    paper. A strong promise whose lords never get a dasha stays theoretical;
    a modest promise running its own lord's period delivers.
    """
    lords = set((subject_result or {}).get("lords", {}).values())
    md, ad = (md_lord or "").strip(), (ad_lord or "").strip()
    md_hit, ad_hit = md in lords, ad in lords

    if md_hit and ad_hit:
        state, note = "fully_active", (
            f"Both the running mahadasha ({md}) and antardasha ({ad}) belong to "
            f"this subject — the period is pointed straight at it."
        )
    elif md_hit:
        state, note = "active", (
            f"The running mahadasha ({md}) owns part of this subject — the long "
            f"arc supports it."
        )
    elif ad_hit:
        state, note = "window", (
            f"The antardasha ({ad}) owns part of this subject — a window inside "
            f"a larger period that is about something else."
        )
    else:
        state, note = "dormant", (
            f"Neither the mahadasha ({md or '?'}) nor the antardasha ({ad or '?'}) "
            f"belongs to this subject — the promise is real but not the theme of "
            f"this period. Build, do not force."
        )
    return {"state": state, "note": note, "md": md, "ad": ad,
            "subject_lords": sorted(lords)}
