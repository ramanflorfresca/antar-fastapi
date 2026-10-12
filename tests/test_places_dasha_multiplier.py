"""Dasha acts as a gate-style multiplier on the static place score (2026-10-12)."""
from antar_engine import places_concern as pc


def test_multiplier_range_and_neutral():
    assert pc._dasha_multiplier(0.0) == 0.5
    assert pc._dasha_multiplier(0.5) == 1.0
    assert round(pc._dasha_multiplier(1.0), 4) == 1.15
    assert pc._dasha_multiplier(-3) == 0.5 and round(pc._dasha_multiplier(9), 4) == 1.15


def test_multiplier_is_monotonic_and_asymmetric():
    xs = [i / 20 for i in range(21)]
    ms = [pc._dasha_multiplier(x) for x in xs]
    assert ms == sorted(ms)
    # the downside (gate) is far larger than the upside (nudge)
    assert (1.0 - pc._dasha_multiplier(0.0)) > 3 * (pc._dasha_multiplier(1.0) - 1.0)


def test_default_mode_is_multiplier_and_env_rolls_back(monkeypatch):
    monkeypatch.delenv("PLACES_DASHA_MODE", raising=False)
    assert pc._dasha_mode() == "multiplier"
    monkeypatch.setenv("PLACES_DASHA_MODE", "blend")
    assert pc._dasha_mode() == "blend"
    monkeypatch.setenv("PLACES_DASHA_MODE", "garbage")
    assert pc._dasha_mode() == "multiplier"


def test_bad_dasha_fit_halves_but_good_fit_cannot_run_away():
    base = 0.60
    assert round(base * pc._dasha_multiplier(0.0), 2) == 0.30
    assert round(base * pc._dasha_multiplier(1.0), 2) == 0.69
    # a high static score still cannot outrun a terrible dasha fit
    assert 0.9 * pc._dasha_multiplier(0.0) < 0.6 * pc._dasha_multiplier(1.0)
    # and a very strong static score + great dasha stays under the 100 cap
    assert 0.85 * pc._dasha_multiplier(1.0) < 1.0
