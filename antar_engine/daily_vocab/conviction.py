"""
antar_engine/daily_vocab/conviction.py — the confidence model + tier gates for
the Concrete Daily Vocabulary Layer.

DOCTRINE
  * Conviction is a SIDE CHANNEL. It decides whether a field is surfaced; the
    score itself is NEVER shown to the user.
  * Conviction must VARY. The known antipattern in this codebase is confidence
    saturating at 0.92 (see predictions.py). We avoid it structurally:
      - confidence is built additively from NAMED, day-dependent factors,
      - the hard ceiling is CONF_CEIL = 0.85 (never 0.9+),
      - a field with no real factors stays near its small base and falls
        below floor -> omitted. A quiet day legitimately surfaces fewer fields.
  * Two risk tiers:
      TIER A (soft/specific): per-field floor. Below floor -> omit (None),
        rather than emit a weak generic line.
      TIER B (event/probabilistic): HARD gate. Needs >= MIN_TIER_B_FACTORS
        independent converging factors AND confidence >= TIER_B_CONF. Phrased
        as a soft "an unhurried day for X", never an assertion. Usually None.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# Never let confidence saturate. Hard ceiling well below the 0.92 antipattern.
CONF_CEIL: float = 0.85

# Per-field surface floors (Tier A). Tuned so a busy day yields 4-6 fields and a
# quiet day yields 2-3. food/mood are "core" (low floor); color/direction/
# romance/body are signal-gated (higher floor -> drop out when unreinforced).
TIER_A_FLOORS: Dict[str, float] = {
    # food/mood/color/direction are benign day-lord/Moon facts the brief lists
    # under "surface freely, every day" — floors at/below their base so they
    # show daily (content rotates; confidence still varies for ordering/debug).
    "food_lean": 0.45,
    "mood_tone": 0.45,
    "favourable_direction": 0.35,
    "lucky_color": 0.30,
    # body/romance are conditional — they should drop out when no real signal.
    "body_focus": 0.46,  # [perchart] surface chart-specific body read on milder contacts
    "romance_read": 0.46,  # [perchart] benefic-in-5/7 surfaces on its own
}

# Tier B hard gate.
MIN_TIER_B_FACTORS: int = 2
TIER_B_CONF: float = 0.62  # [perchart] event_watch slightly less rare (still time-bound + 2 factors)


def confidence(base: float, factors: List[Tuple[str, float]]) -> float:
    """Additive confidence from named factors, capped at CONF_CEIL.

    `factors` is a list of (reason, weight). Returns a float in [0, CONF_CEIL].
    Keeping reasons attached lets the debug side-channel explain WHY a field
    surfaced without ever leaking into user-facing text.
    """
    score = float(base) + sum(float(w) for _, w in factors)
    if score < 0.0:
        score = 0.0
    return round(min(CONF_CEIL, score), 3)


def passes_tier_a(field: str, conf: float) -> bool:
    """True if a Tier A field clears its surface floor."""
    floor = TIER_A_FLOORS.get(field, 0.50)
    return conf >= floor


def passes_tier_b(factor_count: int, conf: float) -> bool:
    """Hard gate for the Tier B event_watch field."""
    return factor_count >= MIN_TIER_B_FACTORS and conf >= TIER_B_CONF


__all__ = [
    "CONF_CEIL", "TIER_A_FLOORS", "MIN_TIER_B_FACTORS", "TIER_B_CONF",
    "confidence", "passes_tier_a", "passes_tier_b",
]
