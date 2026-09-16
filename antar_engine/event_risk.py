"""
antar_engine/event_risk.py

Event-risk / windfall APTITUDE engine — DESCRIPTIVE propensity reads for the
"sudden" money-event cluster, NOT magnitude or a guaranteed outcome (that class
was falsified; see BUSINESS_TIMING_STUDY.md):
  - sudden gains vs sudden losses  ← 8th house (sudden events, upheaval, OPM,
                                     inheritance/windfall) + Rahu/Ketu volatility
  - bankruptcy / financial ruin    ← weak reserves (2nd) + income (11th) against
                                     heavy debt (6th) + loss (12th) + 8th affliction

Ordinal propensity only (elevated / moderate / low) + which way it leans, with a
protective note. The LLM narrates; timing (WHEN) is left to the convergence /
loss-dasha engines the caller already has.
"""
from __future__ import annotations

from antar_engine.d10_career import SIGN_LORD, _EXALT, _OWN, _DEBIL, _sign_n_from
from antar_engine.money_flow import _house_strength, analyze_money_flow

_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_HARD_MALEFIC = {"Mars", "Saturn", "Sun"}


def _occupants(h, d1):
    return [p for p, v in d1.items()
            if isinstance(v, dict) and v.get("house") == h and p != "Lagna"]


def sudden_events(chart_data: dict) -> dict:
    """8th-house read: propensity + lean for SUDDEN money events (windfall vs
    blow-up). Descriptive. Returns {available, volatility, lean, reasons[]}."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lag = (cd.get("lagna") or {}).get("sign")
        if not d1 or not lag:
            return {"available": False}

        occ8 = _occupants(8, d1)
        s8 = _house_strength(8, d1, lag)   # includes lord dignity + occupants
        reasons = []
        gain, loss = 0.0, 0.0

        # Rahu/Ketu in the 8th = high volatility (sudden ups AND downs)
        volatility = "low"
        if "Rahu" in occ8 or "Ketu" in occ8:
            volatility = "high"
            reasons.append("a node in your house of sudden events — big swings, up and down")
        # benefics in 8th / strong 8th lord → sudden GAINS lean (OPM, windfall, inheritance)
        for p in occ8:
            if p in _BENEFIC:
                gain += 1.0
                reasons.append("support for sudden gains — inheritance, backing, or windfall")
            elif p in _HARD_MALEFIC:
                loss += 1.0
                reasons.append("exposure to sudden costs or losses")
        if s8 >= 1.5:
            gain += 0.8
        elif s8 <= -1.0:
            loss += 0.8
        if volatility == "low" and (gain or loss):
            volatility = "moderate"

        if gain - loss >= 1.0:
            lean = "gains"
        elif loss - gain >= 1.0:
            lean = "losses"
        else:
            lean = "mixed"
        return {"available": True, "volatility": volatility, "lean": lean,
                "reasons": reasons or ["your house of sudden events is quiet — "
                                       "few abrupt money shocks either way"]}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def bankruptcy_risk(chart_data: dict) -> dict:
    """Financial-ruin PROPENSITY (not a prediction it will happen): weak reserves
    (2nd) + income (11th) against heavy debt (6th) + loss (12th) + 8th affliction.
    Returns {available, risk: elevated|moderate|low, reasons[], protective[]}."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lag = (cd.get("lagna") or {}).get("sign")
        if not d1 or not lag:
            return {"available": False}

        h2 = _house_strength(2, d1, lag)     # reserves / savings
        h11 = _house_strength(11, d1, lag)   # income / gains
        h6 = _house_strength(6, d1, lag)     # debt / loans
        h12 = _house_strength(12, d1, lag)   # loss / spending
        mf = analyze_money_flow(cd)

        risk_score = 0.0
        reasons, protective = [], []
        if h2 <= 0.0:
            risk_score += 1.0; reasons.append("thin reserves — little cushion saved")
        else:
            protective.append("a real savings cushion")
        if h11 <= 0.0:
            risk_score += 1.0; reasons.append("income/gains under strain")
        else:
            protective.append("supported income")
        if h6 >= 1.5:
            risk_score += 1.0; reasons.append("a heavy debt/loan load")
        if h12 >= 1.5:
            risk_score += 0.8; reasons.append("large or leaking expenditure")
        if mf.get("available") and mf.get("net_lean") == "outflow_heavy":
            risk_score += 1.0; reasons.append("outflow running ahead of inflow")
        # a strong 2nd or 11th genuinely protects
        if h2 >= 1.5 or h11 >= 1.5:
            risk_score -= 1.0

        risk = ("elevated" if risk_score >= 3.0 else
                "moderate" if risk_score >= 1.5 else "low")
        return {"available": True, "risk": risk,
                "reasons": reasons or ["no strong ruin markers — the money base holds"],
                "protective": protective}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
