"""
antar_engine/wealth_magnitude.py — [wealth-engine 2026-09-23]

Native-level WEALTH read that survives falsification, unlike "which vertical wins"
(that idea was tested and killed — see the business-timing study). Two things the
chart CAN grade about the PERSON:

  MAGNITUDE  — how big can this person's wealth engine go? (dhana/raja/mahapurusha
               yogas + the strength of the wealth houses 2/10/11)
  STABILITY  — does it HOLD, or arrive-and-dissolve? (a node in a money house
               2/8/11) → the SIZING DISCIPLINE that fits the chart.

It NEVER names a vertical or predicts a specific company. It grades capacity and
tells the founder how to spread money across ventures — then execution + market decide which vehicle
catches the money. Deterministic, zero-LLM, plain-language summary.

Design: reuse yogas.detect_all_yogas (the yoga source of truth) for magnitude, and
mirror the node-in-money-house logic already in concern_engines for stability, but
turn it into actionable sizing advice.
"""
from __future__ import annotations
import re
from typing import Optional, List, Dict, Any

from antar_engine.yogas import (
    detect_all_yogas, _get_house, _house_lord,
    _is_exalted, _is_debilitated, _is_own_sign,
)

_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
_STRENGTH_W = {"strong": 3.0, "moderate": 2.0, "weak": 1.0}
_WEALTH_CATS = {"wealth", "raj_yoga", "mahapurusha"}
_MONEY_HOUSES = (2, 8, 11)   # 2 own capital, 8 other-people's-money, 11 gains


def _cur_lords(dashas: Optional[dict]) -> set:
    """Set of planets whose Vimśottarī period (MD/AD) is running today."""
    if not isinstance(dashas, dict):
        return set()
    try:
        # [precision 2026-09-24] Vimśottarī-ONLY (matches the docstring). The mixed
        # _current_dasha_lords folds in Yoginī/chara, which would falsely mark a
        # secondary-system lord's period as "running" for the wealth read.
        from antar_engine.concern_engines import _vim_active_lords
        return _vim_active_lords(dashas) or set()
    except Exception:
        return set()


def _dignity_pts(planet: str, planets: dict) -> float:
    if _is_exalted(planet, planets) or _is_own_sign(planet, planets):
        return 1.0
    if _is_debilitated(planet, planets):
        return -1.0
    return 0.0


def _magnitude(planets: dict, lagna_sign: str,
               dashas: Optional[dict]) -> Dict[str, Any]:
    yogas = detect_all_yogas(planets, lagna_sign) or []
    drivers: List[str] = []
    yoga_score = 0.0
    wealth_planets: set = set()
    for y in yogas:
        if y.get("category") in _WEALTH_CATS:
            w = _STRENGTH_W.get(str(y.get("strength", "")).lower(), 1.0)
            yoga_score += w
            for p in (y.get("planets") or []):
                wealth_planets.add(p)
            drivers.append(f"{y.get('name')} ({y.get('strength')})")

    # strength of the wealth houses: lords' dignity + benefic occupants
    lord_score = 0.0
    for h in (2, 10, 11):
        lord = _house_lord(h, lagna_sign)
        if lord:
            pts = _dignity_pts(lord, planets)
            lord_score += pts
            if lord in _WEALTH_CATS:
                pass
            if pts:
                drivers.append(f"the {h}th-house ruler is "
                               f"{'strong' if pts > 0 else 'weak'}")
            wealth_planets.add(lord)
    occ_bonus = 0.0
    for p, v in planets.items():
        if not isinstance(v, dict):
            continue
        if v.get("house") in (2, 10, 11) and p in _BENEFICS:
            occ_bonus += 1.0 if _is_exalted(p, planets) else 0.5

    # [node-amplifier] Rahu in a wealth house is a big-GAINS magnitude driver (its
    # instability is handled separately in _stability). Crucially, add Rahu/Ketu
    # to wealth_planets when they sit in a money house so a running NODE dasha
    # (e.g. Rahu Mahadasha lighting an 11th-house Rahu) correctly reads as
    # "switched on now" — that is often the single biggest wealth activation.
    rahu_h, ketu_h = _get_house("Rahu", planets), _get_house("Ketu", planets)
    node_bonus = 0.0
    if rahu_h == 11:
        node_bonus += 2.0
        drivers.append("an amplifier sits in your gains area — big-gains potential")
    elif rahu_h in (2, 8):
        node_bonus += 1.0
    if rahu_h in _MONEY_HOUSES:
        wealth_planets.add("Rahu")
    if ketu_h in _MONEY_HOUSES:
        wealth_planets.add("Ketu")  # its dasha lights the theme (as instability)

    score = round(yoga_score + lord_score + occ_bonus + node_bonus, 2)
    if score >= 10:
        label = "exceptional"
    elif score >= 6.5:
        label = "high"
    elif score >= 3.5:
        label = "solid"
    else:
        label = "modest"

    # is the wealth engine "switched on" — does a running period (MD/AD) lord also
    # drive the wealth engine (a wealth-yoga planet, a 2/10/11 lord, or a node in
    # a money house)?
    cur = _cur_lords(dashas)
    lit = sorted(wealth_planets & cur)
    activated_now = bool(lit)

    return {"score": score, "label": label, "activated_now": activated_now,
            "lit_lords": lit, "drivers": drivers[:6]}


def _stability(planets: dict, lagna_sign: str) -> Dict[str, Any]:
    rahu_h = _get_house("Rahu", planets)
    ketu_h = _get_house("Ketu", planets)
    drivers: List[str] = []

    if ketu_h in _MONEY_HOUSES:
        return {
            "grade": "fragile", "node": f"Ketu-{ketu_h}", "lean": "spread",
            "sizing_advice": ("Gains here arrive but tend to DISSOLVE — putting "
                "everything into one venture is the trap. Cap how much you commit to "
                "any single venture, take profits out as they come, and never let "
                "one thing hold everything you've built."),
            "drivers": [f"the node of loss sits in a money area ({ketu_h}th) — "
                        "gains don't hold on their own"],
        }
    if rahu_h == 11:
        return {
            "grade": "volatile", "node": "Rahu-11", "lean": "spread",
            "sizing_advice": ("A large but SWINGY engine — big upside with a pull "
                "to over-reach. Spread across several ventures and cap how much "
                "rides on each; running more than one is the chart-fit move, not a "
                "distraction. Bank gains rather than rolling them all forward."),
            "drivers": ["the node of amplification sits in the gains area (11th) — "
                        "large but volatile"],
        }
    if rahu_h in (2, 8):
        return {
            "grade": "volatile", "node": f"Rahu-{rahu_h}", "lean": "spread",
            "sizing_advice": ("Money here can inflate then reverse and invites "
                "over-leverage. Keep debt modest, size positions so a reversal "
                "can't sink you, and don't mistake a fast run-up for a floor."),
            "drivers": [f"the node of amplification sits in a money area ({rahu_h}th) "
                        "— prone to leverage and swings"],
        }

    # No node in a money house — check for malefic drag on 2/11.
    afflicted = False
    for h in (2, 11):
        for p, v in planets.items():
            if isinstance(v, dict) and v.get("house") == h and p in ("Saturn", "Mars"):
                afflicted = True
    if afflicted:
        return {
            "grade": "moderate", "node": None, "lean": "concentrate",
            "sizing_advice": ("Steady rather than explosive, with some drag — grow "
                "by compounding what works and avoid forcing the pace. Reinvest "
                "deliberately; don't chase."),
            "drivers": ["a hard planet weighs on a money area — steady, some friction"],
        }
    return {
        "grade": "stable", "node": None, "lean": "concentrate",
        "sizing_advice": ("Gains tend to HOLD — you can concentrate on what's "
            "working and let it compound rather than spreading thin."),
        "drivers": ["no destabiliser on the money areas — gains tend to hold"],
    }


# [one-lean 2026-10-04] the stability grade IS the answer to "concentrate or
# diversify?" — said once, in sentence one, and the move carries it out. Live
# (Raman, Rahu-11): "reputation grows when you run more than one venture" + move
# "close the nearest deal before spreading attention" = a mixed signal.
LEAN_DIRECTIVE = {
    "spread": ("THE ANSWER IS: SPREAD — run more than one venture, with a hard cap on how much "
               "money and time any single one can take, and bank gains as they land. Say this "
               "plainly in sentence one. `next` MUST carry it out (e.g. set the cap per venture "
               "this week, or move gains out of the biggest one). Do NOT tell them to focus on "
               "one deal first, and never recommend concentrating."),
    "concentrate": ("THE ANSWER IS: CONCENTRATE — put the main effort and money into what is "
                    "already working and let it compound; don't spread thin. Say this plainly in "
                    "sentence one. `next` MUST carry it out (e.g. name the one venture to back "
                    "and what to pause). Never recommend diversifying."),
}

_CONC_RX = re.compile(r"(?i)concentr|\bfocus|enfoc|\bfoc[ao]r|all[- ]in|put everything|"
                      r"all my eggs|ek jagah|one place|un solo|um s[oó]")
_DIV_RX = re.compile(r"(?i)diversif|\bspread|repartir|distribu|alag alag|several|varios|v[aá]rios")


def is_concentrate_vs_diversify(question: str) -> bool:
    q = question or ""
    return bool(_CONC_RX.search(q) and _DIV_RX.search(q))


# [allin-keeps-lean 2026-10-04] "I am 100% all in on Tezops AI and Antar" (a reply to
# the concentrate-or-diversify answer) skipped the wealth layer, so the SAME chart got
# "the reading supports it" one run and "pick one, the reading favours focus" the next.
# A statement of how their money/time is placed gets the same lean, applied to it.
_ALLOC_RX = re.compile(
    r"(?i)\b(i'?m|i am|went|go|going|gone|been|be)\s+(100\s?%\s+)?all[- ]in\b|\ball[- ]in\s+(on|with|for)\b|"
    r"\b100\s?%|\bhundred percent\b|\beverything (is |i have )?(in|into|on)\b|"
    r"\ball (of )?my (money|savings|time|capital|energy)\b|\bput (it )?all\b|"
    r"\btodo (mi dinero |mi tiempo )?(en|a)\b|\bvoy con todo\b|\btudo (em|no|na)\b|"
    r"\bsab kuch\b|\bpoora (paisa|time)\b")


def is_allocation_statement(question: str) -> bool:
    return bool(_ALLOC_RX.search(question or ""))


ALLOCATION_DIRECTIVE = {
    "spread": ("THEY JUST TOLD YOU HOW THEIR MONEY/TIME IS PLACED. Apply the SAME answer — SPREAD "
               "WITH CAPS — to exactly what they said; do not re-decide. If they run two or more "
               "ventures, say plainly that this already fits (it IS spreading); the risk is the "
               "all-in part — nothing capped and nothing set aside. Never tell them to pick one "
               "venture or that the reading favours focus. `next` = set the most each venture can "
               "draw from them and what share of any gain goes straight to savings."),
    "concentrate": ("THEY JUST TOLD YOU HOW THEIR MONEY/TIME IS PLACED. Apply the SAME answer — "
                    "CONCENTRATE — to exactly what they said; do not re-decide. All in on ONE thing "
                    "that is working fits; split across several means back the strongest and pause "
                    "the rest. `next` = the concrete step that does that."),
}


def wealth_profile(chart_data: dict, dashas: Optional[dict] = None,
                   chart_record: Optional[dict] = None) -> dict:
    """Native wealth read: {magnitude, stability, headline, summary, guard}.
    Never raises; returns {available: False} when the chart is unreadable."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        planets = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign") or (chart_record or {}).get("lagna_sign")
        if not planets or not lagna:
            return {"available": False}

        mag = _magnitude(planets, lagna, dashas)
        sta = _stability(planets, lagna)

        _mag_word = {"exceptional": "an exceptional wealth engine",
                     "high": "a large wealth engine",
                     "solid": "a solid wealth engine",
                     "modest": "a modest, work-it wealth engine"}[mag["label"]]
        _sta_tail = {
            "fragile": "but a fragile one, so cap what you put into any one venture — gains dissolve if you concentrate",
            "volatile": "but a volatile one, so spread across several ventures and cap the downside",
            "moderate": "steady with some drag, so compound what works and don't force it",
            "stable": "and a stable one, so you can concentrate on what works and let it compound",
        }[sta["grade"]]
        headline = f"{_mag_word.capitalize()}, {_sta_tail}."

        _when = (" And it's switched on now — your current life-period is one of "
                 "its own drivers, so this is a build-and-raise window, not a wait."
                 if mag["activated_now"] else
                 " It's more latent than lit right now — it turns on when the right "
                 "life-period runs; build the groundwork for then.")
        summary = (
            f"Your chart carries {_mag_word} — this is about how BIG your money "
            f"capacity can go, not which business it comes through.{_when} "
            f"The important part is HOW it behaves: {sta['sizing_advice']} "
            "The chart can grade your capacity and how to spread your money across "
            "ventures — it cannot tell you which venture becomes the big one; that's "
            "execution and market, and it's yours to decide."
        )

        return {
            "available": True,
            "magnitude": mag,
            "stability": sta,
            "headline": headline,
            "summary": summary,
            "guard": ("Grades wealth CAPACITY + how to spread money across ventures "
                      "— never picks a vertical or predicts a specific company."),
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
