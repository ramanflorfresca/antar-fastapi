"""
antar_engine/compat_convergence.py

Compatibility convergence-CONFIDENCE layer — the Partner-domain analog of
`daily_convergence`. A relationship read is only as strong as the AGREEMENT
among its independent synastry layers: one strong layer (great chemistry) does
not make a strong pairing if the others pull the other way. Conviction comes
when several independent layers point the same way as the committed badge.

This module does NOT change the score or the badge — `compose_compat_v2` already
commits those. It only reports HOW MUCH the six (or seven) independent, already-
scored layers agree with that committed badge, as an honest confidence signal.

Layers polled: whatever `compose_compat_v2` produced — soul / chemistry / public
/ lifepath / communication / friction (+ capability for hiring-type reasons).
Each carries a 0-100 `score`, a user-facing `layer_label`, and its
`weight_in_this_reason` (the per-reason importance). Agreement is WEIGHTED by
that importance — a barely-weighted layer disagreeing counts less than the
lead layer disagreeing (a precision gain over naive layer-counting).

Everything is jargon-free on the way out. Never raises.
"""
from __future__ import annotations

# overall badge -> target polarity
_BADGE_POL = {"FLOW": 1, "MIXED": 0, "STRAIN": -1}

# a layer's own lean, from its 0-100 score. >=65 = the engine's own `passed`
# threshold (a real strength); <50 = a real strain; the 50-64 middle is a
# genuine "neither", excluded (a layer we can't call is not a vote).
def _layer_pol(score) -> int:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0
    if s >= 65:
        return 1
    if s < 50:
        return -1
    return 0


def _join(names):
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def compat_convergence(layers: list, overall_badge: str) -> dict:
    """How strongly the independent synastry layers AGREE with the committed
    compatibility badge.

    Args:
      layers: the list from compose_compat_v2 (each with score, layer_label,
              weight_in_this_reason).
      overall_badge: 'FLOW' | 'MIXED' | 'STRAIN' (the committed badge).

    Returns (never raises):
      {available, level, score, aligned[], tension[], layers_read, line}
      level  : 'high' | 'moderate' | 'low'
      score  : 0.0-1.0 WEIGHTED agreement among the layers that took a side
      aligned: plain labels of layers agreeing with the badge
      tension: plain labels of layers pulling the other way
      line   : one jargon-free sentence about how sure the read is
    """
    try:
        target = _BADGE_POL.get((overall_badge or "").upper())
        if target is None:
            return {"available": False}

        sided = []  # (label, pol, weight)
        for l in (layers or []):
            if not isinstance(l, dict):
                continue
            pol = _layer_pol(l.get("score"))
            if pol == 0:
                continue
            label = l.get("layer_label") or l.get("layer_key") or ""
            try:
                w = float(l.get("weight_in_this_reason") or 0.0)
            except (TypeError, ValueError):
                w = 0.0
            if w <= 0:
                w = 1.0 / max(1, len(layers))   # equal fallback when unweighted
            sided.append((label, pol, w))

        if not sided:
            return {"available": False}

        n_layers = len([l for l in layers if isinstance(l, dict)])
        strong = [(lab, w) for lab, p, w in sided if p > 0]   # real strengths
        weak = [(lab, w) for lab, p, w in sided if p < 0]     # real strains

        # A MIXED badge is, by definition, a split verdict — so confidence is
        # about acknowledging the genuine two-sidedness, never manufacturing
        # certainty.
        if target == 0:
            sw = sum(w for _, w in strong)
            ww = sum(w for _, w in weak)
            lopsided = abs(sw - ww) >= 0.5 * (sw + ww) if (sw + ww) else False
            line = ("This reads as a genuine mix — real strengths ("
                    f"{_join([l for l, _ in strong])}) alongside real friction ("
                    f"{_join([l for l, _ in weak])}). Neither cancels the other; "
                    "it works if you tend the hard parts.") if (strong and weak) else (
                    "A middling read overall — nothing lines up strongly either "
                    "way, so treat it as workable-with-effort, not settled.")
            return {"available": True, "level": ("moderate" if lopsided else "low"),
                    "score": 0.0, "aligned": [l for l, _ in strong],
                    "tension": [l for l, _ in weak], "layers_read": n_layers,
                    "line": line}

        aligned = strong if target > 0 else weak     # layers agreeing with the badge
        opposed = weak if target > 0 else strong
        aw = sum(w for _, w in aligned)
        ow = sum(w for _, w in opposed)
        denom = aw + ow
        ratio = (aw / denom) if denom else 0.0
        n_aligned, n_opposed = len(aligned), len(opposed)

        aligned_lbls = [l for l, _ in aligned]
        opposed_lbls = [l for l, _ in opposed]

        # HIGH needs a real, heavily-weighted stack agreeing with little pulling
        # back; LOW is a genuine split; MODERATE is the majority-with-a-caveat
        # middle. Conservative on purpose — a confident label is earned.
        if ratio >= 0.80 and n_aligned >= 3:
            level = "high"
        elif ratio >= 0.60 and n_aligned > n_opposed:
            level = "moderate"
        else:
            level = "low"

        if target > 0:   # FLOW badge
            if level == "high":
                line = (f"Several parts of this pairing point the same way — "
                        f"{_join(aligned_lbls)} all align — so a strong match "
                        f"reads with real conviction.")
            elif level == "moderate":
                line = (f"Most of what matters here lines up ({_join(aligned_lbls)})"
                        + (f", though {_join(opposed_lbls)} pulls against it" if opposed_lbls else "")
                        + " — a fairly confident match, not a certainty.")
            else:
                line = (f"The read is split — you align on {_join(aligned_lbls)} but "
                        f"strain on {_join(opposed_lbls)}. Real on both sides; hold it "
                        f"as promising-but-mixed, not settled.")
        else:            # STRAIN badge
            if level == "high":
                line = (f"The friction runs through several parts — "
                        f"{_join(aligned_lbls)} all pull against this — so the "
                        f"mismatch reads clearly, not as a fluke.")
            elif level == "moderate":
                line = (f"Mostly strained ({_join(aligned_lbls)})"
                        + (f", though {_join(opposed_lbls)} genuinely works" if opposed_lbls else "")
                        + " — a real challenge with a bright spot, not hopeless.")
            else:
                line = (f"A hard-to-call read — it strains on {_join(aligned_lbls)} yet "
                        f"holds on {_join(opposed_lbls)}. Take the caution seriously, but "
                        f"it isn't one-sided.")

        return {"available": True, "level": level, "score": round(ratio, 2),
                "aligned": aligned_lbls, "tension": opposed_lbls,
                "layers_read": n_layers, "line": line}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
