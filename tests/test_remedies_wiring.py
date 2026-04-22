"""
Unit tests for cp-day5/day6 remedy wiring helpers.

Run:  pytest tests/test_remedies_wiring.py -v
"""

import pytest

from antar_engine.annual_planning import (
    _canonical_practice as _canonical_annual,
    _pick_yearly_remedy_planets,
)
from antar_engine.monthly_deepdive import (
    _canonical_practice as _canonical_monthly,
    _pick_monthly_remedy_planets,
)


# ─── canonical practice builder ──────────────────────────────────
def test_canonical_practice_saturn_has_mantra_and_purpose():
    out = _canonical_annual("Saturn")
    assert "Om Shanaye Namaha" in out
    assert "discipline" in out.lower()
    assert "saturday" in out.lower()
    assert "108" in out


def test_canonical_practice_unknown_planet_returns_empty():
    assert _canonical_annual("NotAPlanet") == ""
    assert _canonical_annual(None) == ""   # type: ignore[arg-type]


def test_canonical_practice_monthly_and_annual_match():
    """Both files import the same source — outputs must agree."""
    for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
              "Saturn", "Rahu", "Ketu"):
        assert _canonical_annual(p) == _canonical_monthly(p)


# ─── yearly remedy planet picker ─────────────────────────────────
def test_yearly_picks_use_dasha_lord_plus_classical_pair():
    picks = _pick_yearly_remedy_planets("Mars")
    assert picks == ["Mars", "Saturn", "Jupiter"]


def test_yearly_picks_handle_dasha_already_saturn():
    picks = _pick_yearly_remedy_planets("Saturn")
    assert len(picks) == 3
    assert picks[0] == "Saturn"
    assert "Jupiter" in picks
    assert "Mars" in picks


def test_yearly_picks_handle_empty_dasha():
    picks = _pick_yearly_remedy_planets(None)
    # Falls to Saturn, Jupiter, Mars in order
    assert picks == ["Saturn", "Jupiter", "Mars"]


def test_yearly_picks_handle_composite_dasha_string():
    """'Mars MD + Mercury AD' should extract 'Mars'."""
    picks = _pick_yearly_remedy_planets("Mars MD")
    assert picks[0] == "Mars"
    picks = _pick_yearly_remedy_planets("Mars / Mercury")
    assert picks[0] == "Mars"


# ─── monthly remedy planet picker ────────────────────────────────
def test_monthly_picks_prefer_masik_weak_first():
    masik_weak = [
        {"planet": "Sun"},
        {"planet": "Rahu"},
        {"planet": "Venus"},
    ]
    picks = _pick_monthly_remedy_planets(masik_weak, "Mars")
    assert picks == ["Sun", "Rahu", "Venus"]


def test_monthly_picks_pad_with_dasha_when_short():
    masik_weak = [{"planet": "Sun"}]
    picks = _pick_monthly_remedy_planets(masik_weak, "Mars")
    assert picks[0] == "Sun"
    assert "Mars" in picks
    assert len(picks) == 3


def test_monthly_picks_pad_with_saturn_when_dasha_present_in_weak():
    masik_weak = [{"planet": "Mars"}]
    picks = _pick_monthly_remedy_planets(masik_weak, "Mars")
    assert "Mars" in picks
    assert "Saturn" in picks
    assert len(picks) <= 3
