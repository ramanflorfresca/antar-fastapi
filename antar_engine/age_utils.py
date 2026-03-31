"""
age_utils.py — Shared age intelligence utilities for all Antar signal generators.
Sprint W · antar.world · March 31, 2026

Import this wherever you build a signal context:
    from age_utils import calculate_current_age, get_floor_age, filter_umra_activations, get_future_dasha_transitions
"""

from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# W-01 — Current age calculation
# ---------------------------------------------------------------------------

def calculate_current_age(birth_date: str) -> int:
    """
    Returns the user's current age in whole years.
    Handles the birthday-not-yet-this-year edge case correctly.

    Args:
        birth_date: ISO string 'YYYY-MM-DD'

    Returns:
        Integer age (e.g. 51 for Nov 26 1974 as of March 2026)
    """
    today = date.today()
    bd = date.fromisoformat(birth_date)
    age = today.year - bd.year
    # Subtract 1 if birthday hasn't occurred yet this calendar year
    if (today.month, today.day) < (bd.month, bd.day):
        age -= 1
    return age


def get_floor_age(current_age: int) -> int:
    """
    Returns the minimum age threshold for signal content.
    Signals must never reference events or themes below this age.

    Rule: max(current_age - 5, 16)
    A 20-year-old gets floor 16. A 51-year-old gets floor 46.
    """
    return max(current_age - 5, 16)


# ---------------------------------------------------------------------------
# W-03 — Umra activation filter
# ---------------------------------------------------------------------------

# Full Umra age activation table (LK tradition)
UMRA_ACTIVATIONS = [
    {"house": 1,  "activation_age": 1,  "theme": "Self, personality, health"},
    {"house": 2,  "activation_age": 2,  "theme": "Wealth, family, speech"},
    {"house": 3,  "activation_age": 3,  "theme": "Courage, siblings, communication"},
    {"house": 4,  "activation_age": 4,  "theme": "Home, mother, property"},
    {"house": 5,  "activation_age": 5,  "theme": "Children, intelligence, speculation"},
    {"house": 6,  "activation_age": 6,  "theme": "Enemies, debts, disease"},
    {"house": 7,  "activation_age": 7,  "theme": "Marriage, partnerships (early)"},
    {"house": 7,  "activation_age": 34, "theme": "Marriage, partnerships (key activation)"},
    {"house": 8,  "activation_age": 8,  "theme": "Accidents, inheritance (early)"},
    {"house": 8,  "activation_age": 36, "theme": "Transformation, inheritance (key)"},
    {"house": 9,  "activation_age": 9,  "theme": "Fortune, father (early)"},
    {"house": 9,  "activation_age": 30, "theme": "Fortune, dharma (peak)"},
    {"house": 10, "activation_age": 10, "theme": "Career (early)"},
    {"house": 10, "activation_age": 22, "theme": "Career (launch window)"},
    {"house": 10, "activation_age": 48, "theme": "Career (authority peak)"},
    {"house": 11, "activation_age": 11, "theme": "Gains, siblings (early)"},
    {"house": 11, "activation_age": 54, "theme": "Income, elder networks (peak)"},
    {"house": 12, "activation_age": 12, "theme": "Spirituality, foreign (early)"},
    {"house": 12, "activation_age": 60, "theme": "Liberation, completion (peak)"},
]


def filter_umra_activations(current_age: int, max_upcoming: int = 2) -> list[dict]:
    """
    Returns only upcoming Umra age activations relevant to the user's current age.

    Rule: activation_age >= current_age - 2 (allows showing activations
    just passed so the LLM can say "you just entered this window").

    Returns at most `max_upcoming` activations, sorted ascending.
    """
    threshold = current_age - 2
    upcoming = [
        a for a in UMRA_ACTIVATIONS
        if a["activation_age"] >= threshold
    ]
    upcoming.sort(key=lambda x: x["activation_age"])
    return upcoming[:max_upcoming]


# ---------------------------------------------------------------------------
# W-04 — Future dasha transition guard
# ---------------------------------------------------------------------------

def filter_future_dasha_transitions(transitions: list[dict]) -> list[dict]:
    """
    Filters out dasha sub-period transitions that have already passed.
    Returns only transitions with end_date in the future.

    Each transition dict should have at minimum:
        { "planet": str, "end_date": "YYYY-MM-DD", ... }

    The first item in the returned list is the next upcoming transition.
    """
    today = date.today()
    future = [
        t for t in transitions
        if date.fromisoformat(t["end_date"]) > today
    ]
    future.sort(key=lambda x: x["end_date"])
    return future


def days_until(date_str: str) -> int:
    """Returns days from today to a future date string 'YYYY-MM-DD'. Negative = past."""
    return (date.fromisoformat(date_str) - date.today()).days


def format_timing_pill(date_str: str) -> str:
    """
    Converts 'YYYY-MM-DD' to a human-readable timing pill.
    E.g. '2026-10-15' → 'October 2026'
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%B %Y")
