"""Dasha acts as a multiplier on the static place score (2026-10-12)."""
from antar_engine import places_concern as pc


def test_multiplier_range_and_neutral():
    assert pc._dasha_multiplier(0.0) == 0.5
    assert pc._dasha_multiplier(0.5) == 1.0
    assert pc._dasha_multiplier(1.0) == 1.5
    assert pc._dasha_multiplier(-3) == 0.5 and pc._dasha_multiplier(9) == 1.5


def test_default_mode_is_multiplier_and_env_rolls_back(monkeypatch):
    monkeypatch.delenv("PLACES_DASHA_MODE", raising=False)
    assert pc._dasha_mode() == "multiplier"
    monkeypatch.setenv("PLACES_DASHA_MODE", "blend")
    assert pc._dasha_mode() == "blend"
    monkeypatch.setenv("PLACES_DASHA_MODE", "garbage")
    assert pc._dasha_mode() == "multiplier"


def test_bad_dasha_fit_halves_good_fit_lifts():
    base = 0.60
    assert round(base * pc._dasha_multiplier(0.0), 2) == 0.30
    assert round(base * pc._dasha_multiplier(1.0), 2) == 0.90
    # a high static score cannot outrun a terrible dasha fit
    assert 0.9 * pc._dasha_multiplier(0.0) < 0.6 * pc._dasha_multiplier(1.0)
