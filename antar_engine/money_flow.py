"""
antar_engine/money_flow.py

Money-flow APTITUDE/pattern engine — a DESCRIPTIVE read of a chart's money
dynamics (income vs expenditure, gains vs losses, earned vs unearned), NOT a
future-amount or net-loss/net-gain prediction (that outcome class was falsified;
see BUSINESS_TIMING_STUDY.md). The LLM only narrates this.

House anchors (owner-designed 2026-09-16):
  income / earned inflow  ← 2nd (self-earned, savings) + 11th (gains) + 10th (career)
  gains                    ← 11th (labha)
  expenditure / outflow    ← 12th (vyaya: spending, drains) + 6th (debts, loans)
  unearned / windfall / OPM ← 8th (other-people's money, inheritance, sudden) + 5th (speculation)
  net cash pattern         ← inflow (2/11) vs leak (12/6)

Each house's strength = lord dignity + lord placement + benefic/malefic occupants.
Output is ordinal emphasis ("you earn well but money leaks", "your money leans
unearned"), a temperament read — never a guaranteed amount.
"""
from __future__ import annotations

from antar_engine.d10_career import SIGN_LORD, _EXALT, _OWN, _DEBIL, _sign_n_from

_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC = {"Sun", "Mars", "Saturn"}   # nodes handled separately (upachaya-aware)


def _house_strength(h, d1, lag):
    """Ordinal strength of house `h`: lord dignity + lord placement + occupants."""
    sign = _sign_n_from(lag, h)
    lord = SIGN_LORD.get(sign)
    s = 0.0
    ls = (d1.get(lord) or {}).get("sign")
    if _EXALT.get(lord) == ls:
        s += 2.0
    elif ls in _OWN.get(lord, set()):
        s += 1.5
    elif _DEBIL.get(lord) == ls:
        s -= 2.0
    lh = (d1.get(lord) or {}).get("house")
    if lh in (1, 2, 4, 5, 7, 9, 10, 11):
        s += 0.5
    elif lh in (6, 8, 12):
        s -= 0.5
    for p, v in d1.items():
        if not isinstance(v, dict) or p == "Lagna":
            continue
        if v.get("house") == h:
            if p in _BENEFIC:
                s += 1.0
            elif p in _MALEFIC:
                s -= 0.3
            # [era-aware 2026-09-16] Rahu is a modern amplifier, not a plain drag:
            # in wealth/gain/trine houses it MAGNIFIES that house's money theme
            # (Rahu in the 2nd/11th = amplified wealth/gains). Ketu withdraws.
            elif p == "Rahu":
                s += 1.0 if h in (2, 5, 9, 10, 11) else (0.6 if h in (3, 6) else -0.2)
            elif p == "Ketu":
                s += 0.3 if h in (3, 6, 11) else -0.4
    return round(s, 2)


def analyze_money_flow(chart_data: dict) -> dict:
    """Descriptive money-flow pattern. Returns {available, inflow, outflow,
    earned, unearned, net_lean, earned_lean, labels{}, houses{}}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lag = (cd.get("lagna") or {}).get("sign")
        if not d1 or not lag:
            return {"available": False}

        h = {n: _house_strength(n, d1, lag) for n in (2, 5, 6, 8, 10, 11, 12)}

        inflow = round(h[2] + h[11] + 0.5 * h[10], 2)      # earned + gains + career
        outflow = round(h[12] + h[6], 2)                    # spending + debts
        earned = round(h[10] + h[2], 2)                     # career + self-earned
        unearned = round(h[8] + h[5] + 0.5 * h[11], 2)      # OPM/inheritance + speculation + network gains

        # net cash pattern (inflow vs leak)
        net = inflow - outflow
        if inflow >= 1.5 and outflow >= 1.5:
            net_lean = "earns_but_leaks"
            net_label = ("You earn well, but money tends to leak — strong inflow "
                         "paired with strong outflow. Plugging the drains matters "
                         "more than earning more.")
        elif net >= 1.5:
            net_lean = "retains"
            net_label = ("Money tends to stay with you — inflow outweighs outflow. "
                         "A natural saver's pattern.")
        elif net <= -1.5:
            net_lean = "outflow_heavy"
            net_label = ("Outflow runs ahead of inflow — spending, debts, or "
                         "obligations press on what comes in. Guarding the outflow "
                         "is the lever.")
        else:
            net_lean = "balanced"
            net_label = ("Inflow and outflow are fairly matched — money moves "
                         "through steadily rather than piling up or draining away.")

        # earned vs unearned lean
        diff = earned - unearned
        if diff >= 1.5:
            earned_lean = "earned"
            earned_label = ("Your money comes mainly through your own work and "
                            "effort — earned, not handed to you.")
        elif diff <= -1.5:
            earned_lean = "unearned"
            earned_label = ("You have a real unearned channel — money through "
                            "others, backing, windfalls, or investments — often "
                            "more than through salary alone.")
        else:
            earned_lean = "mixed"
            earned_label = ("Your money is a mix — partly earned through your work, "
                            "partly through outside sources, backing, or returns.")

        return {
            "available": True,
            "inflow": inflow, "outflow": outflow,
            "earned": earned, "unearned": unearned,
            "net_lean": net_lean, "earned_lean": earned_lean,
            "labels": {"net": net_label, "earned": earned_label},
            "houses": h,
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def wealth_power_signature(chart_data: dict) -> dict:
    """[era-aware 2026-09-16] Detect MODERN wealth/power signatures — the Rahu-led
    combinations that a 7000-year-old 'Rahu = malefic' lens misses but which, in
    the current era, mark large wealth & power potential:
      Rahu + Venus   → enormous material wealth / luxury
      Rahu + Sun     → power, status, authority
      Rahu + Mercury → tech / media / trade scale
      Rahu in 2/11   → amplified wealth / gains
      Rahu + Jupiter → unconventional, outsized (guru-chandala) growth
    DESCRIPTIVE strong-POTENTIAL read — never a guaranteed net-worth tier. Returns
    {available, signatures[], strength: high|moderate|none, in_gains(bool),
    rahu_house}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        rahu = d1.get("Rahu") or {}
        rh = rahu.get("house")
        if rh is None:
            return {"available": False}

        def same_house(p):
            return (d1.get(p) or {}).get("house") == rh

        sigs = []
        if same_house("Venus"):
            sigs.append(("wealth", "Rahu with Venus — a modern signature of large "
                                   "material wealth and luxury"))
        if same_house("Sun"):
            sigs.append(("power", "Rahu with the Sun — a signature of power, status "
                                  "and reach"))
        if same_house("Mercury"):
            sigs.append(("scale", "Rahu with Mercury — scale through tech, media, or "
                                  "trade"))
        if same_house("Jupiter"):
            sigs.append(("outsized", "Rahu with Jupiter — unconventional, outsized "
                                     "growth (guru-chandala)"))
        in_gains = rh in (2, 11)
        if in_gains:
            sigs.append(("gains", "Rahu in your house of wealth/gains — it amplifies "
                                  "what flows in"))

        strength = ("high" if (len(sigs) >= 2 or
                    (any(s[0] == "wealth" for s in sigs) and in_gains))
                    else "moderate" if sigs else "none")
        return {
            "available": True,
            "signatures": [s[1] for s in sigs],
            "kinds": [s[0] for s in sigs],
            "strength": strength,
            "in_gains": in_gains,
            "rahu_house": rh,
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
