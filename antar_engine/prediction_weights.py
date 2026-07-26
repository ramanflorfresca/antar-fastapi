"""
antar_engine/prediction_weights.py

[multi-system-confidence 2026-07-26] The weighting layer for prediction.

A prediction is rarely made from one technique. Vimśottarī says one thing,
Yoginī another, the gochara (transit) a third, the divisionals a fourth. The
founder's rule: when several of these AGREE, confidence is high; when a single
weak signal speaks alone, it is tentative; when strong signals CONFLICT, the
reading must say "mixed" rather than fake certainty. This module turns that into
arithmetic.

Each signal votes with three numbers:
  weight    — how much this TECHNIQUE counts (config below; the founder tunes it)
  direction — +1 supportive / -1 friction / 0 neutral, for the theme in question
  strength  — 0..1, how strong the signal is IN THIS CHART (lord dignity, exact
              transit vs applying, yoga present-and-unafflicted, etc.)

score = Σ (weight × direction × strength). Confidence is NOT just the score — it
also counts how many INDEPENDENT high-weight techniques agree, because three
clocks striking together is the real signal (K.N. Rao's double-transit + daśā
convergence), not one loud voice.

Weights live here as a plain dict so they can be tuned in one place and later
graduate to a DB table without changing the caller. Defaults reflect mainstream
practice — Vimśottarī primary, gochara the timing trigger, Yoginī/Jaimini as
confirmation, divisionals as verification — but they are the founder's to set.
"""
from __future__ import annotations

from typing import List, Dict, Any

# ── The tunable table ────────────────────────────────────────────────────────
# Higher = counts more. Change these and every prediction re-weights.
DEFAULT_WEIGHTS: Dict[str, float] = {
    # Daśās — Vimśottarī is the primary clock; its sub-period is nearly as strong.
    "vimshottari_maha":  1.00,
    "vimshottari_antar": 0.90,
    # Yoginī — the short, repeatable confirmation overlay.
    "yogini_maha":       0.70,
    "yogini_antar":      0.60,
    # Jaimini Chara — rāśi-based second opinion.
    "jaimini_chara":     0.70,
    # Gochara (transit) — the timing TRIGGER. The Rao double-transit is strong;
    # a single slow-planet transit is a softer nudge.
    "transit_double":    0.85,
    "transit_saturn":    0.50,
    "transit_jupiter":   0.50,
    # Natal promise — a yoga sets the ceiling; without it, no daśā "delivers".
    "natal_yoga":        0.80,
    # Divisional verification — does the varga confirm the rāśi promise?
    "d10_confirm":       0.60,   # career / status (Daśāṃśa)
    "d9_confirm":        0.60,   # relationships / dharma (Navāṃśa)
}

# A technique is "major" (counts toward convergence) at or above this weight.
MAJOR_WEIGHT = 0.70


def weight_of(signal_type: str, weights: Dict[str, float] = None) -> float:
    return (weights or DEFAULT_WEIGHTS).get(signal_type, 0.0)


def score_signals(signals: List[Dict[str, Any]],
                  weights: Dict[str, float] = None) -> Dict[str, Any]:
    """Combine independent technique-signals into one weighted verdict.

    Each signal: {"type": <key in weights>, "direction": -1|0|1,
                  "strength": 0..1 (default 1.0), "note": str}

    Returns:
      net          — Σ weight×direction×strength (sign = overall lean)
      confidence   — "high" | "moderate" | "tentative" | "mixed" | "none"
      agree        — how many MAJOR techniques share the net's direction
      conflict     — how many MAJOR techniques oppose it
      supporting   — the signals that drove the verdict, strongest first
    """
    w = weights or DEFAULT_WEIGHTS
    net = 0.0
    contribs = []
    for s in signals or []:
        d = int(s.get("direction", 0))
        if d == 0:
            continue
        strength = float(s.get("strength", 1.0))
        wt = weight_of(s.get("type", ""), w)
        c = wt * d * strength
        net += c
        contribs.append({**s, "weight": wt, "contribution": c})

    lean = 1 if net > 0 else (-1 if net < 0 else 0)
    majors = [c for c in contribs if c["weight"] >= MAJOR_WEIGHT]
    agree = sum(1 for c in majors if (1 if c["contribution"] > 0 else -1) == lean)
    conflict = sum(1 for c in majors if (1 if c["contribution"] > 0 else -1) == -lean)

    if lean == 0:
        confidence = "none"
    elif conflict >= 1 and agree - conflict <= 1:
        # strong voices pulling opposite ways, and no clear majority
        confidence = "mixed"
    elif agree >= 3:
        confidence = "high"
    elif agree == 2:
        confidence = "moderate"
    else:
        confidence = "tentative"

    contribs.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return {
        "net": round(net, 3),
        "lean": lean,                       # +1 supportive / -1 friction / 0
        "confidence": confidence,
        "agree": agree,
        "conflict": conflict,
        "supporting": contribs,
    }
