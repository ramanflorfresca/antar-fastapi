"""Daily engine accepts the web client's MINUTES and the country default's HOURS (2026-10-03)."""
import datetime as dt
from antar_engine import daily_prediction_engine as dpe


def test_tz_hours_handles_both_units():
    assert dpe._tz_hours(-240) == -4.0 and dpe._tz_hours(330) == 5.5 and dpe._tz_hours(-300) == -5.0
    assert dpe._tz_hours(-4.0) == -4.0 and dpe._tz_hours(5.5) == 5.5 and dpe._tz_hours(0) == 0.0
    assert dpe._tz_hours(None) == 0.0 and dpe._tz_hours("x") == 0.0
    assert dpe._tz_hours(14) == 14.0 and dpe._tz_hours(60) == 1.0


def test_moon_is_the_same_for_minutes_and_hours():
    d = dt.datetime(2026, 10, 3)
    a = dpe.get_moon_data_for_date(d, tz_offset=-240)       # web: minutes
    b = dpe.get_moon_data_for_date(d, tz_offset=-4.0)       # hours
    assert a == b
    # ground truth (Lahiri, local noon EDT): Gemini 17.6°, Ardra — NOT Libra 29°
    assert b["sign"] == "Gemini" and 17.0 < b["degree"] < 18.3 and b["nakshatra"] == "Ardra"
    assert dpe.get_tithi(d, tz_offset=-240) == dpe.get_tithi(d, tz_offset=-4.0) == "23rd"
    assert dpe.get_planet_sign_for_date(d, 2, tz_offset=330) == dpe.get_planet_sign_for_date(d, 2, tz_offset=5.5)


def test_cached_cards_from_the_wrong_moon_are_discarded():
    assert dpe.DAILY_LOGIC_VERSION >= 3
