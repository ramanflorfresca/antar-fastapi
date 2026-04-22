"""
Unit tests for cp-day7 mop-up helpers.

Run:  pytest tests/test_day7_mop_up.py -v
"""

import pytest

from antar_engine.annual_planning import _pick_year_quality
from antar_engine.monthly_deepdive import (
    _compute_energy_level,
    _score_event_tone,
    _pick_best_and_caution_weeks,
)


# ─── _pick_year_quality ─────────────────────────────────────────
def test_year_quality_maps_known_planets():
    assert _pick_year_quality("Jupiter") == "expansion"
    assert _pick_year_quality("Saturn")  == "consolidation"
    assert _pick_year_quality("Mars")    == "building"
    assert _pick_year_quality("Rahu")    == "transformation"
    assert _pick_year_quality("Venus")   == "harvest"


def test_year_quality_handles_composite_dasha():
    assert _pick_year_quality("Mars MD") == "building"
    assert _pick_year_quality("Mars / Mercury") == "building"


def test_year_quality_default_on_missing():
    assert _pick_year_quality(None) == "building"
    assert _pick_year_quality("") == "building"
    assert _pick_year_quality("UnknownPlanet") == "building"


# ─── _compute_energy_level ──────────────────────────────────────
def test_energy_level_mixed_when_both_sides_present():
    assert _compute_energy_level(3, 3) == "mixed"
    assert _compute_energy_level(2, 2) == "mixed"


def test_energy_level_high_on_lopsided_strong():
    assert _compute_energy_level(4, 1) == "high"
    assert _compute_energy_level(3, 0) == "high"


def test_energy_level_low_on_lopsided_weak():
    assert _compute_energy_level(1, 4) == "low"
    assert _compute_energy_level(0, 3) == "low"


def test_energy_level_moderate_on_near_balance():
    assert _compute_energy_level(0, 0) == "moderate"
    assert _compute_energy_level(1, 1) == "moderate"
    assert _compute_energy_level(2, 1) == "moderate"


# ─── _score_event_tone ──────────────────────────────────────────
def test_tone_benefic_trine_positive():
    ev = {"event_type": "aspect", "aspect_kind": "trine",
          "planet": "Jupiter", "orb": 1.0}
    assert _score_event_tone(ev) > 0


def test_tone_malefic_square_negative():
    ev = {"event_type": "aspect", "aspect_kind": "square",
          "planet": "Saturn", "orb": 1.0}
    assert _score_event_tone(ev) < 0


def test_tone_tight_orb_larger_magnitude():
    tight = _score_event_tone({"event_type": "aspect", "aspect_kind": "trine",
                                "planet": "Jupiter", "orb": 0.3})
    loose = _score_event_tone({"event_type": "aspect", "aspect_kind": "trine",
                                "planet": "Jupiter", "orb": 2.5})
    assert tight > loose


def test_tone_retro_is_mild_negative():
    assert _score_event_tone({"event_type": "retro_start",
                               "planet": "Saturn"}) < 0


def test_tone_ingress_is_nonnegative():
    assert _score_event_tone({"event_type": "ingress",
                               "planet": "Jupiter"}) >= 0


# ─── _pick_best_and_caution_weeks ───────────────────────────────
def test_pick_best_caution_simple():
    weeks = [
        {"week_start": "2026-04-06", "events": [
            {"event_type": "aspect", "aspect_kind": "trine",
             "planet": "Jupiter", "orb": 0.5},
        ]},
        {"week_start": "2026-04-13", "events": [
            {"event_type": "aspect", "aspect_kind": "square",
             "planet": "Saturn", "orb": 0.5},
        ]},
    ]
    best, caution = _pick_best_and_caution_weeks(weeks)
    assert best == "2026-04-06"
    assert caution == "2026-04-13"


def test_pick_empty_returns_empty_strings():
    assert _pick_best_and_caution_weeks([]) == ("", "")


def test_pick_single_week_returns_same_for_both():
    weeks = [{"week_start": "2026-04-06", "events": []}]
    best, caution = _pick_best_and_caution_weeks(weeks)
    assert best == caution == "2026-04-06"
