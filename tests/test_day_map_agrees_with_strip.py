"""[one-day-story 2026-10-16] The day map can never call an area a clean opportunity when the five-area strip reads it as volatile/cautious."""
from antar_engine import daily_life_areas as dla

MONEY_ACTIVE = [{"key": "money", "polarity": "opportunity", "tone": 0.9, "caution": False}]


def _line(strip):
    return dla.build_day_map(MONEY_ACTIVE, [], strip=strip)[0]["line"]


def test_volatile_strip_downgrades_a_clean_rise_to_the_two_sided_line():
    rise = _line(None)
    assert rise.startswith("Money moves your way today")
    for state in ("volatile", "caution"):
        line = _line([{"key": "money", "state": state}])
        assert line.startswith("Money is active today") and "spending rises right alongside it" in line
        assert "Money moves your way" not in line


def test_favourable_or_steady_strip_keeps_the_rise():
    for state in ("favorable", "rising", "steady"):
        assert _line([{"key": "money", "state": state}]).startswith("Money moves your way today")


def test_other_areas_and_missing_strip_are_untouched():
    assert dla.build_day_map(MONEY_ACTIVE, [], strip=[{"key": "work", "state": "caution"}])[0]["line"].startswith("Money moves your way")
    assert dla.strip_states(None) == {} and dla.strip_states([{"key": "work", "state": "caution"}]) == {"work": "caution"}


def test_risk_band_stays_risk():
    act = [{"key": "money", "polarity": "risk", "tone": -0.8}]
    assert dla.build_day_map(act, [], strip=[{"key": "money", "state": "volatile"}])[0]["tone"] == "risk"
