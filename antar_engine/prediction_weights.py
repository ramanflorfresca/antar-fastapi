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
#
# Rationale for the ranking (founder-set 2026-07-26):
#   * Vimśottarī is the universally-accepted primary daśā (BPHS precedence).
#   * Jaimini Chara sits just under it and ABOVE Yoginī on purpose — it is
#     rāśi-based, a genuinely INDEPENDENT axis from the nakshatra daśās, so its
#     agreement is stronger evidence than a second nakshatra-based clock.
#   * Yoginī is bumped from 0.70 -> 0.75: Goel and others rate it highly for
#     timing, but it shares Vimśottarī's Moon-nakshatra basis, so it is partly
#     correlated — strong confirmer, not an independent one.
#   * Transit double is the TRIGGER; kept just below the primary daśā so a
#     transit refines timing WITHIN a daśā theme rather than overriding it.
#   * Natal yoga is the CEILING — see NOTE below; here it is a same-plane baseline.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "vimshottari_maha":   1.00,
    "vimshottari_antar":  0.85,
    "jaimini_chara_maha": 0.90,   # independent (sign-based) — ranks above Yoginī
    "jaimini_chara_antar":0.70,
    "yogini_maha":        0.75,
    "yogini_antar":       0.65,
    "transit_double":     0.85,   # the event trigger (Rao double-transit)
    "transit_saturn":     0.45,
    "transit_jupiter":    0.45,
    "natal_yoga":         0.80,   # promise / ceiling
    "d10_confirm":        0.60,   # career / status (Daśāṃśa)
    "d9_confirm":         0.60,   # relationships / dharma (Navāṃśa)
}

# NOTE (future refinement, not yet wired): natal_yoga and the divisionals are
# really CEILING/VETO multipliers, not same-plane timing votes — a promise absent
# in the birth chart no daśā can deliver, and a rāśi promise broken in the varga
# fades. v1 keeps them as flat votes for simplicity; graduating them to
# multipliers is the next accuracy step.

# [independence 2026-07-26] Convergence must count INDEPENDENT bases, not
# signals — three clocks only "strike together" when they are genuinely separate
# measurements. Vimśottarī + Yoginī agreeing is largely ONE basis (both keyed to
# the Moon's nakshatra); Vimśottarī + Chara + transit agreeing is THREE. Each
# signal maps to its basis; confidence is driven by how many distinct bases agree.
SIGNAL_BASIS: Dict[str, str] = {
    "vimshottari_maha":   "nakshatra_dasha",
    "vimshottari_antar":  "nakshatra_dasha",
    "yogini_maha":        "nakshatra_dasha",
    "yogini_antar":       "nakshatra_dasha",
    "jaimini_chara_maha": "sign_dasha",
    "jaimini_chara_antar":"sign_dasha",
    "transit_double":     "transit",
    "transit_saturn":     "transit",
    "transit_jupiter":    "transit",
    "natal_yoga":         "natal",
    "d10_confirm":        "divisional",
    "d9_confirm":         "divisional",
}

# A signal must clear this weight to let its basis count toward convergence.
MAJOR_WEIGHT = 0.70


def weight_of(signal_type: str, weights: Dict[str, float] = None) -> float:
    return (weights or DEFAULT_WEIGHTS).get(signal_type, 0.0)


def score_signals(signals: List[Dict[str, Any]],
                  weights: Dict[str, float] = None) -> Dict[str, Any]:
    """Combine technique-signals into one weighted verdict, counting INDEPENDENT
    bases for convergence.

    Each signal: {"type": <key in weights>, "direction": -1|0|1,
                  "strength": 0..1 (default 1.0), "note": str}

    Returns:
      net          — Σ weight×direction×strength (sign = overall lean)
      confidence   — "high" | "moderate" | "tentative" | "mixed" | "none"
      bases_agree  — count of DISTINCT independent bases backing the lean
      bases_conflict — count of distinct bases opposing it
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
        contribs.append({**s, "weight": wt, "contribution": c,
                         "basis": SIGNAL_BASIS.get(s.get("type", ""), "other")})

    lean = 1 if net > 0 else (-1 if net < 0 else 0)
    # A basis counts once, in the direction of its strongest MAJOR signal.
    basis_dir: Dict[str, float] = {}
    for c in contribs:
        if c["weight"] < MAJOR_WEIGHT:
            continue
        b = c["basis"]
        if b not in basis_dir or abs(c["contribution"]) > abs(basis_dir[b]):
            basis_dir[b] = c["contribution"]
    bases_agree = sum(1 for v in basis_dir.values() if (1 if v > 0 else -1) == lean)
    bases_conflict = sum(1 for v in basis_dir.values() if (1 if v > 0 else -1) == -lean)

    if lean == 0:
        confidence = "none"
    elif bases_conflict >= 1 and bases_agree - bases_conflict <= 1:
        confidence = "mixed"
    elif bases_agree >= 3:
        confidence = "high"
    elif bases_agree == 2:
        confidence = "moderate"
    else:
        confidence = "tentative"

    contribs.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return {
        "net": round(net, 3),
        "lean": lean,
        "confidence": confidence,
        "bases_agree": bases_agree,
        "bases_conflict": bases_conflict,
        "supporting": contribs,
    }
