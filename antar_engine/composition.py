"""
Antar prediction engine — composition helpers.
Reads from lk_conditions.py. Produces the headline + modifiers + override
state for a given chart on a given date.

Founder-locked policy (see LOCK_NOTE.md):
- Path B: planet names allowed as actors in curated statics
- Crisis floor: no interaction gate
- Yoga collision: negative wins headline
- Tiebreak (b): negative polarity wins ties
- Heavy split: friction-heavy vs growth-leaning awakenings tracked separately
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime


def _as_date(d):
    """Tolerate date, datetime, or ISO string (Postgres/JSONB returns strings)."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.fromisoformat(d[:10]).date()
    return d


# =====================================================================
# HEAVY CLASSIFICATION (item #3 — split)
# =====================================================================
# Only HEAVY_FRICTION_CONDITIONS count toward the circuit breaker.
# HEAVY_GROWTH_CONDITIONS fire correctly on cards but do not accrue.
HEAVY_FRICTION_CONDITIONS = {
    # Friction-heavy sleeping awakenings
    "sun_transit_with_sun_sleeping",
    "mars_transit_natal_6_with_mars_sleeping",  # NB: sample-row id, not the {planet}_transit_with_{planet}_sleeping convention
    "saturn_transit_with_saturn_sleeping",
    "rahu_transit_with_rahu_sleeping",
    "ketu_transit_with_ketu_sleeping",
    # Named friction yogas
    "vish_yoga_active",
    "guru_chandala_active",
    "kemadruma_active",
    # Slow-mover dushthana transits
    "saturn_transit_natal_8",
    "rahu_transit_natal_12",
    "ketu_transit_natal_6",
    # Extend with other slow-mover-over-dushthana rows as authored
}

HEAVY_GROWTH_CONDITIONS = {
    # Growth-leaning sleeping awakenings — felt as friction but pointing toward expansion
    "moon_transit_with_moon_sleeping",
    "mercury_transit_with_mercury_sleeping",
    "jupiter_transit_with_jupiter_sleeping",
    "venus_transit_with_venus_sleeping",
}

# =====================================================================
# PRECEDENCE LADDER (Rule 1)
# =====================================================================
PRECEDENCE_RANKS = {
    "named_yoga":          1,  # Vish, Guru-Chandala, Kemadruma, Shri
    "sleeping_awakening":  2,  # sleeping planet + own transit
    "dasha_confluence":    3,  # transit during own MD
    "slow_friction":       4,  # Saturn/Rahu/Ketu over dushthana
    "slow_supportive":     5,  # Jupiter/Saturn over kendra/trikona
    "fast_transit":        6,  # Sun/Mercury/Venus/Mars routine transits
    "flat":                7,  # no condition fired
}

# Planet slowness (lower number = slower)
PLANET_SLOWNESS = {
    "Saturn": 1, "Rahu": 2, "Ketu": 2, "Jupiter": 3,
    "Mars": 4, "Sun": 5, "Venus": 6, "Mercury": 7, "Moon": 8,
}


def _condition_rank_category(cond: dict) -> str:
    """Classify a fired condition into a precedence rank category."""
    if cond["precedence"].get("yoga_named"):
        return "named_yoga"
    trig = cond["trigger"]
    if trig.get("natal_state_required") == "sleeping":
        return "sleeping_awakening"
    if trig.get("type") == "transit_with_dasha":
        return "dasha_confluence"
    activator = trig.get("planet")
    is_slow = activator in ("Saturn", "Rahu", "Ketu", "Jupiter")
    if cond["precedence"]["polarity"] == "negative" and is_slow:
        return "slow_friction"
    if cond["precedence"]["polarity"] == "positive" and is_slow:
        return "slow_supportive"
    return "fast_transit"


def _sort_key(cond: dict, current_md: str) -> tuple:
    """Sort key for ranking fired conditions. Lower = higher priority."""
    rank = PRECEDENCE_RANKS[_condition_rank_category(cond)]
    md_match = 0 if cond["trigger"].get("planet") == current_md else 1
    polarity_match = 0 if cond["precedence"]["polarity"] == "negative" else 1
    slowness = PLANET_SLOWNESS.get(cond["trigger"].get("planet"), 99)
    return (rank, md_match, polarity_match, slowness)


# =====================================================================
# YOGA COLLISION (Rule 5 — item #6)
# =====================================================================
def resolve_yoga_collision(active_yogas: List[dict]) -> Tuple[Optional[dict], List[dict]]:
    """
    When multiple yogas fire on the same day:
    Negative yoga takes the headline; positive yogas become modifiers.
    Among same-polarity yogas, slower activator wins.
    """
    if not active_yogas:
        return None, []
    negative = [y for y in active_yogas if y["precedence"]["polarity"] == "negative"]
    positive = [y for y in active_yogas if y["precedence"]["polarity"] == "positive"]
    if negative:
        headline = sorted(negative, key=lambda y: PLANET_SLOWNESS.get(
            y["trigger"].get("planet", y["trigger"].get("activation_planet", "")), 99
        ))[0]
        # Positive yogas become modifiers; other negative yogas are suppressed below the cap
        return headline, positive
    else:
        headline = sorted(positive, key=lambda y: PLANET_SLOWNESS.get(
            y["trigger"].get("planet", y["trigger"].get("activation_planet", "")), 99
        ))[0]
        return headline, []


# =====================================================================
# HEADLINE + MODIFIER PICKER (Rule 2 — surfacing limit)
# =====================================================================
def pick_headline_and_modifiers(
    fired_conditions: List[dict],
    current_md: str,
) -> Tuple[Optional[dict], List[dict]]:
    """
    Apply the precedence ladder and surfacing limit.
    Returns (headline_condition, up_to_2_modifier_conditions).
    The rest are logged but not surfaced.
    """
    if not fired_conditions:
        return None, []
    # Special-case yoga collisions first
    yogas = [c for c in fired_conditions if c["precedence"].get("yoga_named")]
    non_yogas = [c for c in fired_conditions if not c["precedence"].get("yoga_named")]
    if yogas:
        yoga_headline, yoga_modifiers = resolve_yoga_collision(yogas)
        # Pick top 2 non-yoga conditions as additional modifiers
        non_yogas_sorted = sorted(non_yogas, key=lambda c: _sort_key(c, current_md))
        modifiers = (yoga_modifiers + non_yogas_sorted)[:2]
        return yoga_headline, modifiers
    # No yogas — straight precedence sort
    sorted_conditions = sorted(fired_conditions, key=lambda c: _sort_key(c, current_md))
    return sorted_conditions[0], sorted_conditions[1:3]


# =====================================================================
# CIRCUIT BREAKER (Rule 2 — accumulation)
# =====================================================================
def check_circuit_breaker(recent_headlines: List[dict], today_date) -> dict:
    """
    Track last 7 days of headline conditions per chart.
    If 4+ HEAVY_FRICTION_CONDITIONS in 7 days, gentling override activates.
    """
    td = _as_date(today_date)
    last_7 = [h for h in recent_headlines if (td - _as_date(h["date"])).days <= 7]
    heavy_count = sum(1 for h in last_7 if h["condition_id"] in HEAVY_FRICTION_CONDITIONS)
    return {
        "gentling_active": heavy_count >= 4,
        "heavy_count": heavy_count,
    }


def compose_gentling_prefix(
    today_condition: Optional[dict],
    breaker_state: dict,
) -> Optional[str]:
    """
    Two branches (item #4 fix):
    - If today's headline is also heavy: "Nth heavy day in a stretch" prefix
    - If today's headline is light/positive: "After a heavy stretch" relief prefix
    Either way, the `do` field gentles toward rest.
    """
    if not breaker_state["gentling_active"]:
        return None
    today_is_heavy = (
        today_condition is not None
        and today_condition.get("id") in HEAVY_FRICTION_CONDITIONS
    )
    if today_is_heavy:
        # Accumulation continues today
        n = breaker_state["heavy_count"] + 1
        ordinal = {2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
                   7: "seventh", 8: "eighth"}.get(n, f"{n}th")
        return (
            f"This is the {ordinal} heavy day in a stretch. "
            f"The pattern is real, and so is the wear of meeting it. Today's read:"
        )
    else:
        # Relief day after accumulation
        return (
            "After a heavy stretch, an easier day. "
            "Take it slowly even though the chart has opened — "
            "the body and mind take longer to uncoil than the day takes to lighten."
        )


def gentle_the_do(do_text: str) -> str:
    """
    When breaker is active, soften the `do` toward rest.
    Prepends a rest-acknowledging clause; the prescribed do still runs.
    """
    rest = "Before anything else today: eat, drink water, walk outside if you can."
    if not do_text:
        return rest
    return rest + " Then, if you have capacity: " + do_text[0].lower() + do_text[1:]


# =====================================================================
# CRISIS FLOOR (Rule 2 — wellbeing) — item #5 fix
# =====================================================================
CRISIS_FOOTER_TEXT = (
    "You've been carrying a heavy stretch. The chart isn't lying, but the "
    "weight is real — and if you're struggling, please talk to someone you "
    "trust. We're not a replacement for a friend, a therapist, or a crisis line."
)


def check_crisis_floor(recent_headlines: List[dict], today_date) -> dict:
    """
    NO daily-interaction gate (item #5 fix).
    Withdrawal is a depression symptom; gating on interaction would suppress
    the footer for users most likely to need it.
    Triggers on heavy-friction count alone over a 14-day window.
    """
    td = _as_date(today_date)
    last_14 = [h for h in recent_headlines if (td - _as_date(h["date"])).days <= 14]
    heavy_count = sum(1 for h in last_14 if h["condition_id"] in HEAVY_FRICTION_CONDITIONS)
    return {
        "crisis_floor_active": heavy_count >= 6,
        "heavy_count_14d": heavy_count,
        "footer_text": CRISIS_FOOTER_TEXT if heavy_count >= 6 else None,
    }


# =====================================================================
# CONVENIENCE: full daily composition
# =====================================================================
def compose_daily_card(
    fired_conditions: List[dict],
    current_md: str,
    recent_headlines: List[dict],
    today_date,
) -> dict:
    """
    Single entry point: takes fired conditions + dasha + history, returns
    the composed daily card payload.
    """
    headline, modifiers = pick_headline_and_modifiers(fired_conditions, current_md)
    breaker = check_circuit_breaker(recent_headlines, today_date)
    crisis = check_crisis_floor(recent_headlines, today_date)
    if headline is None:
        # Flat day — pick one of the 4 flat-day variants
        return {
            "polarity": "flat",
            "condition_id": "flat_day",
            "headline": "A quiet day. Neither pushed nor blocked. Useful for ordinary work.",
            "modifiers": [],
            "gentling_prefix": None,
            "crisis_footer": crisis["footer_text"],
        }
    polarity = headline["precedence"]["polarity"]
    headline_text = (
        headline.get("headline_negative") if polarity == "negative"
        else headline.get("headline_positive")
    )
    do_text = headline.get("do", "")
    if breaker["gentling_active"]:
        do_text = gentle_the_do(do_text)
    return {
        "polarity": polarity,
        "condition_id": headline.get("id"),
        "headline": headline_text,
        "gist": headline.get("gist", ""),
        "cause": headline.get("cause") if polarity == "negative" else None,
        "use": headline.get("use") if polarity == "positive" else None,
        "do": do_text,
        "dont": headline.get("dont", ""),
        "areas_affected": headline.get("areas_affected", []),
        "remedy_planet": headline.get("remedy_planet"),
        "remedy_variant": headline.get("remedy_variant"),
        "modifiers": [
            {"condition_id": m.get("id"), "note": m.get("modifier_note", m.get("gist", "")[:120])}
            for m in modifiers
        ],
        "gentling_prefix": compose_gentling_prefix(headline, breaker),
        "crisis_footer": crisis["footer_text"],
    }
