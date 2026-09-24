"""
antar_engine/daily_convergence.py

Daily convergence-CONFIDENCE layer — the classical principle behind how a
careful astrologer predicts a day: an event/day-quality is only as strong as the
AGREEMENT among independent timing layers. One good tara, or one good transit, is
not a strong day on its own; conviction comes when several independent readings
point the same way.

This module does NOT decide the day's direction — the validated vote engine
(today_highlight) + house-activation sweep + dasha-season cap already commit
that. It only reports HOW MUCH the independent, already-shipped/validated layers
agree with that committed read, as an honest confidence signal.

Layers polled (each independent, each already live):
  1. Tara Bala      — the day's nakshatra vs the birth star   (daily_precision)
  2. Moon placement — the Moon's house transit (gochara)       (daily_precision)
  3. Running dasha  — the antardasha lord's natural tilt        (daily_precision)
  4. Lal Kitab      — a sleeping planet dragging today          (daily_precision)
  5. Dasha season   — the multi-year mahadasha register (slow gate, business_timing)

'transit' from build_day_signals is intentionally skipped — it is the Moon's
placement re-expressed, already counted at #2 (double-counting would inflate
agreement).

KP is deliberately NOT a layer here: its validation gate is closed (quarantined,
birth-time-critical). It rides in SHADOW only (see kp_daily_shadow), never in
this user-facing confidence, until it earns its gate.

Everything is jargon-free on the way out. Never raises.
"""
from __future__ import annotations

# signal `direction` (from daily_precision.build_day_signals) -> polarity sign
_POL = {
    "strong": 1, "supportive": 1,
    "neutral": 0,
    "friction": -1, "adverse": -1,
    # "unknown" -> excluded (a layer we could not read is not a neutral vote)
}

# dasha-season register -> polarity sign
_SEASON_POL = {"supported": 1, "steady": 0, "hard": -1}

# jargon-free names for each layer, for the plain "why" line
_LAYER_NAME = {
    "nakshatra": "the day's star",
    "moon_house": "the day's mood",   # [de-jargon] was "where the Moon is today" — planet name leaked to the user
    "dasha": "your current chapter",
    "lal_kitab": "your chart's own pattern",
    "season": "your longer season",
}


def _join(names):
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def daily_convergence(day_signals: list, season_register: str,
                      committed_direction: str) -> dict:
    """How strongly the independent validated layers AGREE with the day's
    committed direction.

    Args:
      day_signals: rows from daily_precision.build_day_signals (each with
                   key/direction/available).
      season_register: 'hard' | 'steady' | 'supported' | None (business_timing).
      committed_direction: the card's committed 'positive' | 'adverse' | 'quiet'.

    Returns (never raises):
      {available, level, score, aligned[], tension[], layers_read, line}
      level  : 'high' | 'moderate' | 'low'   (low == split / quiet)
      score  : 0.0-1.0 agreement ratio among the layers that took a side
      aligned: plain names of layers agreeing with the committed direction
      tension: plain names of layers pulling the other way
      line   : one jargon-free sentence for the card
    """
    try:
        target = (1 if committed_direction == "positive"
                  else -1 if committed_direction == "adverse" else 0)

        layers = []  # (key, polarity)
        for row in (day_signals or []):
            if not isinstance(row, dict):
                continue
            if row.get("key") == "transit":       # counted once at moon_house
                continue
            if not row.get("available"):
                continue
            pol = _POL.get(row.get("direction"))
            if pol is None:
                continue
            layers.append((row.get("key"), pol))

        sp = _SEASON_POL.get(season_register)
        if sp is not None:
            layers.append(("season", sp))

        if not layers:
            return {"available": False}

        sided = [(k, p) for k, p in layers if p != 0]      # layers that took a side
        pos = [k for k, p in sided if p > 0]
        neg = [k for k, p in sided if p < 0]

        # Quiet day: nothing committed to a direction — confidence is about the
        # ABSENCE of convergence, not agreement with a non-direction.
        if target == 0:
            if not sided:
                line = "Nothing is converging strongly today — a genuinely quiet day to keep simple."
            else:
                lean = "toward opportunity" if len(pos) >= len(neg) else "toward caution"
                line = ("A quiet day overall — the independent readings only lightly lean "
                        f"{lean}, nothing strong enough to force a move.")
            return {"available": True, "level": "low", "score": 0.0,
                    "aligned": [], "tension": [],
                    "layers_read": len(layers), "line": line}

        agree_keys = pos if target > 0 else neg
        oppose_keys = neg if target > 0 else pos
        n_agree, n_oppose = len(agree_keys), len(oppose_keys)
        denom = n_agree + n_oppose
        score = (n_agree / denom) if denom else 0.0

        aligned = [_LAYER_NAME.get(k, k) for k in agree_keys]
        tension = [_LAYER_NAME.get(k, k) for k in oppose_keys]

        # Levels: HIGH needs a real stack agreeing with no opposition; LOW is a
        # genuine split (or a lone voice); MODERATE is the majority-with-a-caveat
        # middle. Deliberately conservative — a confident label must be earned.
        if n_agree >= 3 and n_oppose == 0:
            level = "high"
        elif n_agree >= 2 and n_agree > n_oppose:
            level = "moderate"
        else:
            level = "low"

        _side_word = "toward opportunity" if target > 0 else "toward caution"
        if level == "high":
            line = (f"Several independent readings agree today — {_join(aligned)} "
                    f"all point {_side_word}, so this reads with real conviction.")
        elif level == "moderate":
            if tension:
                _pull = "pull" if len(tension) > 1 else "pulls"
                line = (f"Most of the day lines up {_side_word} ({_join(aligned)}), "
                        f"though {_join(tension)} {_pull} the other way — a fairly "
                        f"confident read, not a certainty.")
            else:
                line = (f"The day leans {_side_word} ({_join(aligned)}) — a fairly "
                        f"confident read.")
        else:  # low / split
            if tension and aligned:
                line = (f"The forces are split today — some readings lean {_side_word} "
                        f"({_join(aligned)}), others the opposite ({_join(tension)}). "
                        f"Hold this as a mixed read, not a sure thing.")
            else:
                line = ("Only one reading is really speaking today — take it as a "
                        "light lean, not a strong signal.")

        return {"available": True, "level": level, "score": round(score, 2),
                "aligned": aligned, "tension": tension,
                "layers_read": len(layers), "line": line}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
