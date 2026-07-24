"""
antar_engine/transit_translation.py
═══════════════════════════════════════════════════════════════════════════════
LAYER 3 — translate_transit_weight (V2.1 doctrine, per-trigger)

Mirrors Layer 1's modern-translation pass, applied to transit triggers BEFORE
aggregation. A malefic on an upachaya / output / gains house — for an archetype
built to work through that house — is CONSTRUCTIVE, not friction.

Doctrine reference: Antar.world V2.1 Layer 3.
    "Translate at trigger time, not in synthesis. Deferring translation lets
    raw -15 weights shape best_windows before the archetype lens runs, which
    tells a Saturn-friendly chart its best month is 'friction.'"

V2.2 doctrine gap closed:
    project_unified_prediction_engine_v22.md flagged
    "translate_transit_weight not yet per-trigger" as one of three remaining
    V2.2 gaps. This module closes it.

Public surface (consumed by precision_windows.py and domain_engines.py):

    resolve_wealth_archetype(chart_data) -> str
        Returns one of DISRUPTOR / SYSTEMATIC / MASS_SERVER / CHARISMA /
        INSTITUTIONAL / NEUTRAL.  Wraps classify_wealth_archetype with a
        defensive fallback so callers never crash on a partial chart.

    translate_transit_weight(trigger, archetype) -> dict
        Per-trigger translator. Accepts a trigger dict shaped
        {"date","planet","type","weight", optional "transit_house"} and
        returns the trigger with type/weight/note overwritten when the
        archetype lens flips its sign. Date-aware: transit_house is resolved
        FROM the trigger's date (caller pre-computes), not "now."

    translate_dasha_window_weight(lord, lord_house, archetype, base_score)
        Cousin function for natal-dasha-window scoring in domain_engines.py.
        Same lens: flat malefic-in-dushthana penalties get translated
        through Viparita Raja Yoga + archetype fit.

    archetype_aware_transit_bonus(planet, transit_house, archetype)
        Pure-helper used inside precision_windows._score_date to ADD a
        constructive bonus when a malefic sits on an archetype-aligned
        output house. Returns (delta_score, reason) or (0.0, "").

Translation rules — exhaustive (audit-tracable):

  ┌───────────┬──────────────────────────┬─────────────────────────────────────┐
  │ Planet    │ Houses                   │ Archetype                           │
  ├───────────┼──────────────────────────┼─────────────────────────────────────┤
  │ Saturn    │ 3, 6, 10, 11             │ MASS_SERVER, INSTITUTIONAL,         │
  │           │ (upachaya + karma)       │ SYSTEMATIC                          │
  │           │                          │ -> CONSTRUCTIVE (+15 / +0.5)        │
  │           │                          │    "Saturn on output house,         │
  │           │                          │     archetype-aligned"              │
  ├───────────┼──────────────────────────┼─────────────────────────────────────┤
  │ Rahu      │ 3, 6, 10, 11             │ DISRUPTOR                           │
  │           │ (gains + initiative)     │ -> CONSTRUCTIVE (+20 / +0.6)        │
  │           │                          │    "Rahu on gains/initiative,       │
  │           │                          │     disruptor-aligned"              │
  ├───────────┼──────────────────────────┼─────────────────────────────────────┤
  │ Mars      │ 3, 6, 10                 │ DISRUPTOR, SYSTEMATIC               │
  │           │ (action + competition)   │ -> CONSTRUCTIVE (+10 / +0.4)        │
  │           │                          │    "Mars on action house,           │
  │           │                          │     archetype-aligned"              │
  └───────────┴──────────────────────────┴─────────────────────────────────────┘

Genuine afflicting transits (e.g. Saturn on Moon, Rahu on lagna without
archetype fit) are left at their raw weight — translation only flips signs
when the archetype lens has positive evidence.

KV-cache + memory cross-refs:
  [[project_unified_prediction_engine_v22]] — doctrine source
  [[project_kill_generic_read_sprint]]      — has_domain_anchor consumer
  [[feedback_ast_parse_before_push]]        — patch script must ast.parse
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Constants — keep in lock-step with archetype_classifier.WEALTH_ARCHETYPES
# ─────────────────────────────────────────────────────────────────────────────

ARCHETYPES = ("DISRUPTOR", "SYSTEMATIC", "MASS_SERVER", "CHARISMA", "INSTITUTIONAL")

# Houses where a malefic, for the named archetype, becomes CONSTRUCTIVE.
# Tracable to V2.1 doctrine + archetype_classifier reasoning.
_CONSTRUCTIVE_MAP: Dict[Tuple[str, str], Tuple[float, float, str]] = {
    # (planet, archetype): (precision_delta, dasha_delta, reason)
    ("Saturn", "MASS_SERVER"):    (+0.5, +0.30, "Saturn on output/service house — MASS_SERVER aligned"),
    ("Saturn", "INSTITUTIONAL"):  (+0.5, +0.30, "Saturn on output/karma house — INSTITUTIONAL aligned"),
    ("Saturn", "SYSTEMATIC"):     (+0.4, +0.25, "Saturn on output/karma house — SYSTEMATIC aligned"),
    ("Rahu",   "DISRUPTOR"):      (+0.6, +0.35, "Rahu on gains/initiative — DISRUPTOR aligned"),
    ("Mars",   "DISRUPTOR"):      (+0.4, +0.20, "Mars on action house — DISRUPTOR aligned"),
    ("Mars",   "SYSTEMATIC"):     (+0.3, +0.15, "Mars on action house — SYSTEMATIC aligned"),
}

_CONSTRUCTIVE_HOUSES: Dict[str, set] = {
    "Saturn": {3, 6, 10, 11},  # upachaya + karma
    "Rahu":   {3, 6, 10, 11},  # gains + initiative + competition
    "Mars":   {3, 6, 10},      # action + competition + karma
}


# ─────────────────────────────────────────────────────────────────────────────
# Archetype resolver — graceful fallback
# ─────────────────────────────────────────────────────────────────────────────

def resolve_wealth_archetype(chart_data: Optional[Dict[str, Any]]) -> str:
    """
    Returns one of DISRUPTOR / SYSTEMATIC / MASS_SERVER / CHARISMA /
    INSTITUTIONAL, or NEUTRAL on any failure.

    Why graceful fallback: /predict must never 500 because the archetype
    classifier choked on a partial chart. NEUTRAL means "no archetype lens
    applies" — translation rules silently no-op for that branch.
    """
    if not chart_data:
        return "NEUTRAL"
    try:
        from antar_engine.life_arc.archetype_classifier import classify_wealth_archetype
        result = classify_wealth_archetype(chart_data)
        primary = (result or {}).get("primary_archetype") or "NEUTRAL"
        return primary if primary in ARCHETYPES else "NEUTRAL"
    except Exception:
        return "NEUTRAL"


# ─────────────────────────────────────────────────────────────────────────────
# Per-trigger translator — V2.1 Layer 3 doctrine
# ─────────────────────────────────────────────────────────────────────────────

def translate_transit_weight(
    trigger: Dict[str, Any],
    archetype: str,
) -> Dict[str, Any]:
    """
    Per-trigger translation, applied BEFORE aggregate_triggers_by_date.

    Mutates and returns `trigger`.  Caller must have pre-resolved
    `trigger["transit_house"]` AT THE TRIGGER DATE — translating against
    "now" silently breaks for any non-immediate window (Cowork V2.1 review).

    A malefic on an archetype-aligned output house flips from FRICTION to
    CONSTRUCTIVE.  Anything else passes through untouched.
    """
    planet = trigger.get("planet", "")
    house  = trigger.get("transit_house")
    if not planet or house is None or archetype == "NEUTRAL":
        return trigger

    if house not in _CONSTRUCTIVE_HOUSES.get(planet, set()):
        return trigger

    key = (planet, archetype)
    rule = _CONSTRUCTIVE_MAP.get(key)
    if not rule:
        return trigger

    precision_delta, _dasha_delta, reason = rule
    # V2.1 mapping: precision_windows weight scale ~0-10, transit-event scale
    # uses -15 .. +20.  Use the dasha-scale weight only for trigger structs
    # that carry an explicit numeric "weight" in the -15..+20 band; otherwise
    # keep the precision-scale delta.
    raw_weight = trigger.get("weight")
    if isinstance(raw_weight, (int, float)) and abs(raw_weight) >= 5:
        # transit-event scale: -15 friction -> +15..+20 constructive
        translated = +15 if planet == "Saturn" else +20 if planet == "Rahu" else +10
        trigger["weight"] = translated
    else:
        # precision-window scale: bonus added on top of raw
        trigger["weight"] = (raw_weight or 0.0) + precision_delta

    trigger["type"] = "CONSTRUCTIVE"
    trigger["note"] = reason
    trigger["translated"] = True
    return trigger


# ─────────────────────────────────────────────────────────────────────────────
# Pure helper for precision_windows._score_date
# ─────────────────────────────────────────────────────────────────────────────

def archetype_aware_transit_bonus(
    planet: str,
    transit_house: Optional[int],
    archetype: str,
) -> Tuple[float, str]:
    """
    Used inline by precision_windows._score_date.  Returns
    (delta_score, reason) — both zero/empty when no archetype rule applies.

    This is the CONSTRUCTIVE-bonus pass: the doctrine fix is not removing
    flat penalties (precision_windows has few of those) but ADDING the
    archetype-aligned bonus that the original engine misses entirely.
    """
    if not planet or transit_house is None or archetype == "NEUTRAL":
        return 0.0, ""
    if transit_house not in _CONSTRUCTIVE_HOUSES.get(planet, set()):
        return 0.0, ""
    rule = _CONSTRUCTIVE_MAP.get((planet, archetype))
    if not rule:
        return 0.0, ""
    precision_delta, _dasha_delta, reason = rule
    return precision_delta, reason


# ─────────────────────────────────────────────────────────────────────────────
# Dasha-window weight translator — domain_engines.run_timing_engine
# ─────────────────────────────────────────────────────────────────────────────

def translate_dasha_window_weight(
    lord: str,
    lord_house: Optional[int],
    archetype: str,
    base_score: float,
) -> Tuple[float, str]:
    """
    Closes the V2.1 Layer 1/3 hybrid case in domain_engines.run_timing_engine
    where a malefic dasha lord in [6,8,12] gets a flat 0.30 ("bad window")
    regardless of archetype fit.

    Translation:
      - Viparita Raja Yoga: a dushthana lord in dushthana for a chart with
        DISRUPTOR or MASS_SERVER lens recovers most of the penalty.
      - Saturn-in-6 for MASS_SERVER/INSTITUTIONAL/SYSTEMATIC is constructive
        (service-at-scale engine), not "bad window."
      - Rahu-in-11 for DISRUPTOR is the unicorn marker (boosted, not penalized).
      - Genuine 8/12 malefic placements outside archetype fit keep the raw
        penalty.

    Returns (translated_score, reason).  Reason is "" when no translation
    applies — caller uses base_score as-is in that case.
    """
    if not lord or lord_house is None or archetype == "NEUTRAL":
        return base_score, ""

    is_dushthana = lord_house in (6, 8, 12)
    if not is_dushthana:
        return base_score, ""

    # Rahu in 11 — already handled higher up the score ladder in
    # domain_engines (0.85 boost).  Translation here applies only when the
    # flat 0.30 penalty would otherwise overwrite that boost.
    if lord == "Rahu" and lord_house in (6, 11) and archetype == "DISRUPTOR":
        return max(base_score, 0.80), "Rahu in 6/11 — DISRUPTOR unicorn marker, classical penalty cancelled"

    # Saturn in 6 — MASS_SERVER service-at-scale engine
    if lord == "Saturn" and lord_house == 6 and archetype in ("MASS_SERVER", "INSTITUTIONAL", "SYSTEMATIC"):
        return max(base_score, 0.75), "Saturn in 6 — service-at-scale engine, archetype-aligned"

    # Mars in 6 — DISRUPTOR/SYSTEMATIC competitive edge
    if lord == "Mars" and lord_house == 6 and archetype in ("DISRUPTOR", "SYSTEMATIC"):
        return max(base_score, 0.70), "Mars in 6 — competitive edge, archetype-aligned"

    # Viparita catch-all: malefic in 6/8/12 for DISRUPTOR/MASS_SERVER
    # archetypes recovers to a neutral baseline (0.55) rather than 0.30.
    # Not a glowing endorsement, but not "bad window" either.
    if archetype in ("DISRUPTOR", "MASS_SERVER"):
        return max(base_score, 0.55), f"{lord} in dushthana — viparita potential, archetype-tolerated"

    return base_score, ""


__all__ = [
    "ARCHETYPES",
    "resolve_wealth_archetype",
    "translate_transit_weight",
    "archetype_aware_transit_bonus",
    "translate_dasha_window_weight",
]
