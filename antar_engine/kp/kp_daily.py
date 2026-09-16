"""
antar_engine/kp/kp_daily.py

KP daily SHADOW signal — computed + logged, NEVER user-facing.

KP's validation gate is closed (see kp_gate_status.json — quarantined,
birth-time-critical). So KP does not feed the user-facing daily convergence
confidence. This module computes a real, honest KP daily fingerprint and hands
it back for SHADOW logging only, so that — over time, against real outcomes — KP
can be validated for daily use and earn its gate. Nothing here reaches a user.

The signal: KP timing turns on the running DASHA LORD being a significator of the
relevant houses. For a day-quality shadow we read which houses the running lord
signifies (via build_significators) and net them into a direction:
  + gain/effort/career/income houses (2, 10, 11)   -> positive lean
  - loss/expense/upheaval houses      (8, 12)       -> negative lean
Then we record whether that KP lean AGREES with the day's committed direction.

Never raises — any failure returns {available: False, reason}.
"""
from __future__ import annotations

from datetime import datetime

_POS_HOUSES = {2, 10, 11}   # wealth, career, gains/income
_NEG_HOUSES = {8, 12}       # upheaval/others' money, loss/expense
# 6 (debts/competition) is deliberately excluded — it is dual (Harsha for the
# fighter, drag for the earner) and would add noise to a shadow signal.


def kp_daily_shadow(chart_record: dict, dasha_lord: str,
                    committed_direction: str, now: datetime = None) -> dict:
    """Compute the KP daily shadow fingerprint. Returns (never raises):
      {available, birth_time_ok, dasha_lord, signifies[list of houses],
       kp_lean: 'positive'|'adverse'|'neutral', agrees_with_committed: bool|None,
       note}
    `agrees_with_committed` is None when either side has no direction.
    """
    try:
        from .kp_service import _build_chart
        from .kp_significators import build_significators

        lord = (dasha_lord or "").strip().title()
        if not lord:
            return {"available": False, "reason": "no running dasha lord"}

        chart = _build_chart(chart_record)
        if chart is None:
            return {"available": False, "reason": "missing birth data for KP chart"}

        # birth-time confidence is recorded (not enforced — this is shadow only)
        birth_time_ok = chart_record.get("needs_reconfirm") is not True

        _, planet_sig = build_significators(chart)
        houses = sorted(planet_sig.get(lord, []) or [])
        if not houses:
            return {"available": True, "birth_time_ok": birth_time_ok,
                    "dasha_lord": lord, "signifies": [], "kp_lean": "neutral",
                    "agrees_with_committed": None,
                    "note": "running lord signifies no scored house today"}

        pos = len(_POS_HOUSES.intersection(houses))
        neg = len(_NEG_HOUSES.intersection(houses))
        kp_lean = ("positive" if pos > neg else
                   "adverse" if neg > pos else "neutral")

        agrees = None
        if committed_direction in ("positive", "adverse") and kp_lean != "neutral":
            agrees = (kp_lean == committed_direction)

        return {
            "available": True,
            "birth_time_ok": birth_time_ok,
            "dasha_lord": lord,
            "signifies": houses,
            "kp_lean": kp_lean,
            "agrees_with_committed": agrees,
            "note": f"lord signifies gain-houses={pos}, loss-houses={neg}",
        }
    except Exception as e:
        return {"available": False, "reason": f"kp daily shadow error: {e}"[:180]}
