"""
kp_service.py  —  A5: the single entry point main.py calls.

kp_answer(chart_record, question, language, ...) -> dict

Everything KP-specific lives here so the main.py patch is a tiny landmark insert.
Hard rules enforced here:
  * Gate: returns eligible=False unless kp_backtest.is_gate_open() is True.
  * KP_MODE env: 'off' | 'shadow' (default) | 'primary'. Off => nothing.
    Shadow => computed + returned under a shadow key, never user-facing.
  * Birth-time confidence: if the chart is flagged needs_reconfirm, KP is
    suppressed (KP is birth-time-critical and was validated only on a verified,
    rectified chart — see kp_gate_status.json caveats).
  * Never raises into the caller: any failure -> eligible=False with a reason.
"""

import os
from datetime import datetime

from .kp_backtest import is_gate_open


def kp_mode():
    """'off' | 'shadow' | 'primary'. Forced 'off' until the gate is open."""
    if not is_gate_open():
        return "off"
    m = (os.environ.get("KP_MODE") or "shadow").strip().lower()
    return m if m in ("off", "shadow", "primary") else "shadow"


# question keywords -> (verdict_type, timing_type)
#   verdict_type: a kp_significators.QUESTION_TYPES key, or 'loss7', or None
#   timing_type : a kp_timing.NATAL_EVENTS key, or None
_KEYWORDS = [
    (("marry", "marriage", "wedding", "engaged", "casar", "boda", "matrimonio"),
     "marriage", "marriage"),
    (("divorce", "separat", "break up", "breakup", "divorc", "separac", "ruptura"),
     "loss7", "separation"),
    (("promot", "raise", "ascens"), "promotion", "job_change"),
    (("job", "offer", "hire", "employ", "trabajo", "empleo", "puesto"),
     "job_new", "job_change"),
    (("house", "home", "property", "apartment", "flat", "casa", "propiedad",
      "piso"), "property", "property"),
    (("child", "baby", "pregnan", "conceiv", "hijo", "embaraz", "beb"),
     None, "childbirth"),
    (("business", "startup", "venture", "negocio", "empresa", "emprend"),
     None, "business_start"),
    (("move", "relocat", "shift abroad", "mudar", "reubic", "mudanza"),
     None, "relocation"),
    (("money", "gain", "profit", "deal", "close the", "dinero", "ganan", "trato"),
     "gain", None),
    (("win", "lawsuit", "litig", "court", "pleito", "demanda"),
     "litigation_win", None),
    (("recover", "heal", "health", "salud", "recuper"), "recovery", None),
]


def _classify(question):
    q = (question or "").lower()
    for keys, vt, tt in _KEYWORDS:
        if any(k in q for k in keys):
            return vt, tt
    return None, None


def _build_chart(chart_record, kp_birth_time=None):
    from .kp_chart import compute_kp_chart
    bt = kp_birth_time or chart_record.get("birth_time")
    bd = str(chart_record.get("birth_date") or "")[:10]
    lat = chart_record.get("latitude")
    lon = chart_record.get("longitude")
    tz = chart_record.get("tz_offset")
    if not (bd and bt and lat is not None and lon is not None and tz is not None):
        return None
    return compute_kp_chart(bd, str(bt)[:8], float(lat), float(lon),
                            tz_offset=float(tz))


def kp_answer(chart_record, question, language="en", now=None,
              kp_birth_time=None):
    """
    Returns:
      {eligible: bool, mode: str, ...narration..., debug: {...}}  on success, or
      {eligible: False, mode, reason}                              otherwise.
    Caller decides placement (shadow field vs primary verdict) from `mode`.
    """
    mode = kp_mode()
    if mode == "off":
        return {"eligible": False, "mode": "off", "reason": "gate closed / KP off"}

    # birth-time confidence guard
    if chart_record.get("needs_reconfirm") is True:
        return {"eligible": False, "mode": mode,
                "reason": "birth time unverified (needs_reconfirm) — KP suppressed"}

    verdict_type, timing_type = _classify(question)
    if verdict_type is None and timing_type is None:
        return {"eligible": False, "mode": mode,
                "reason": "question not KP-mappable"}

    try:
        chart = _build_chart(chart_record, kp_birth_time)
        if chart is None:
            return {"eligible": False, "mode": mode,
                    "reason": "missing birth data for KP chart"}

        from .kp_significators import verdict as kp_verdict, QUESTION_TYPES
        from .kp_timing import next_window, csl_gate
        from .kp_narration import narrate

        # verdict
        if verdict_type == "loss7":
            v = kp_verdict(chart, "loss", loss_house=7)
        elif verdict_type in QUESTION_TYPES:
            v = kp_verdict(chart, verdict_type)
        else:
            # timing-only matter (childbirth/business/relocation): derive from
            # the cuspal-sub-lord gate of the natal event type
            gate_ok, _csl = csl_gate(chart, timing_type)
            v = {"verdict": "yes" if gate_ok else "no",
                 "confidence": 2 if gate_ok else 0,
                 "drivers": [], "debug": {"csl_gate": gate_ok}}

        # forward window (timing)
        win = None
        if timing_type is not None:
            now = now or datetime.utcnow()
            import swisseph as swe
            from_jd = swe.julday(now.year, now.month, now.day, 12.0)
            s, e = next_window(chart, timing_type, from_jd)
            if s is not None:
                win = {"start_jd": s, "end_jd": e}
                v["confidence"] = min(3, int(v.get("confidence", 0)) + 1)

        narration = narrate({**v, "window": win}, language=language)
        return {
            "eligible": True,
            "mode": mode,
            **narration,
            "debug": {
                "verdict_type": verdict_type,
                "timing_type": timing_type,
                "raw_verdict": v.get("verdict"),
                "kp_debug": v.get("debug"),
            },
        }
    except Exception as e:  # never break the caller
        return {"eligible": False, "mode": mode, "reason": f"kp error: {e}"}
