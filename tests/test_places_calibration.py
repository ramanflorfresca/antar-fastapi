"""Calibration guards for the places score subscores (2026-07-12).

The old normalisers demanded all three karakas + both angles to converge, so a
single strong line could never lift a city out of STRAIN and FLOW was
unreachable for every chart. These lock in the fix: one strong line scores high.
"""
from antar_engine.places_concern import (
    _karaka_score_from_norms, _angle_score_from_prox,
)

KARAKAS = ["Sun", "Saturn", "Mercury"]  # e.g. career


def test_single_strong_primary_karaka_reaches_high():
    # One perfect (condition-max) primary-karaka line — used to cap ~0.44.
    assert _karaka_score_from_norms({"Sun": 1.0}, KARAKAS) >= 0.95


def test_single_strong_secondary_karaka_still_strong():
    s = _karaka_score_from_norms({"Saturn": 1.0}, KARAKAS)
    assert 0.85 <= s <= 0.95          # rank-tapered, but not crushed


def test_more_karakas_score_at_least_as_high():
    one = _karaka_score_from_norms({"Sun": 0.8}, KARAKAS)
    three = _karaka_score_from_norms({"Sun": 0.8, "Saturn": 0.6, "Mercury": 0.5}, KARAKAS)
    assert three >= one               # convergence adds, never subtracts
    assert three <= 1.0


def test_weak_condition_stays_low():
    # On the line but poorly conditioned karaka -> still a low score (honest).
    assert _karaka_score_from_norms({"Saturn": 0.25}, KARAKAS) < 0.30


def test_no_karaka_line_is_zero():
    assert _karaka_score_from_norms({}, KARAKAS) == 0.0


def test_single_strong_angle_not_halved():
    # One strong angle line, the other angle empty — must not be averaged down.
    assert _angle_score_from_prox({"MC": 0.9, "AC": 0.0}) >= 0.9


def test_two_angles_beat_one():
    one = _angle_score_from_prox({"MC": 0.8, "AC": 0.0})
    two = _angle_score_from_prox({"MC": 0.8, "AC": 0.6})
    assert two > one and two <= 1.0


def test_empty_angles_zero():
    assert _angle_score_from_prox({}) == 0.0
