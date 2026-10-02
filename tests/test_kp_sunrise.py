"""KP day lord follows the SUNRISE-to-sunrise day, not midnight (2026-10-02).

A question at 3 AM on a Friday belongs to Thursday in KP, so its day lord —
one of the Ruling Planets that confirm a horary verdict and its timing — is
Jupiter, not Venus. Checked at the Ask seat (Edgewater, NJ).
"""
from datetime import datetime, timedelta, timezone

import pytest

swe = pytest.importorskip("swisseph")

from antar_engine.kp.kp_horary import (  # noqa: E402
    WEEKDAY_LORDS, cast_horary, last_sunrise_jd, ruling_planets, vedic_weekday,
)
from antar_engine.kp.kp_prashna import ASTROLOGER_SEAT, kp_prashna  # noqa: E402

LAT, LON = ASTROLOGER_SEAT["lat"], ASTROLOGER_SEAT["lon"]
EDT = timezone(timedelta(hours=-4))


def _jd(dt):
    u = dt.astimezone(timezone.utc)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + u.second / 3600)


def _local(jd):
    y, m, d, h = swe.revjul(jd)
    return (datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)).astimezone(EDT)


def test_sunrise_at_the_seat_is_morning_local():
    s = _local(last_sunrise_jd(_jd(datetime(2026, 10, 2, 12, tzinfo=EDT)), LAT, LON))
    assert (s.date().isoformat(), s.hour) == ("2026-10-02", 6)


@pytest.mark.parametrize("dt,lord", [
    (datetime(2026, 10, 1, 23, 30, tzinfo=EDT), "Jupiter"),   # Thu night
    (datetime(2026, 10, 2, 0, 30, tzinfo=EDT), "Jupiter"),    # Fri, after midnight
    (datetime(2026, 10, 2, 3, 0, tzinfo=EDT), "Jupiter"),     # Fri, before sunrise
    (datetime(2026, 10, 2, 6, 50, tzinfo=EDT), "Jupiter"),    # minutes before sunrise
    (datetime(2026, 10, 2, 7, 5, tzinfo=EDT), "Venus"),       # just after sunrise
    (datetime(2026, 10, 2, 22, 0, tzinfo=EDT), "Venus"),      # Fri evening
    (datetime(2026, 10, 4, 5, 0, tzinfo=EDT), "Saturn"),      # Sun pre-dawn → Saturday
    (datetime(2026, 10, 5, 4, 0, tzinfo=EDT), "Sun"),         # Mon pre-dawn → Sunday
])
def test_day_lord_changes_at_sunrise(dt, lord):
    wd, basis = vedic_weekday(_jd(dt), LAT, LON, dt.weekday())
    assert (WEEKDAY_LORDS[wd], basis) == (lord, "sunrise")
    rp = ruling_planets(_jd(dt), LAT, LON, dt.weekday())
    assert rp["day_lord"] == lord and rp["day_basis"] == "sunrise"
    assert lord in rp["set"]


def test_polar_night_falls_back_to_civil_weekday():
    dt = datetime(2026, 12, 21, 12, tzinfo=timezone.utc)      # Svalbard, no sunrise
    assert vedic_weekday(_jd(dt), 78.2, 15.6, dt.weekday()) == (dt.weekday(), "civil")


def test_number_horary_uses_the_kp_day():
    ch = cast_horary(74, datetime(2026, 10, 2, 3, 0), LAT, LON, -4.0)
    assert ch["ruling_planets"]["day_lord"] == "Jupiter"


def test_ask_engine_pre_dawn_question_gets_thursdays_lord():
    q = "Will I get this job?"
    pre = kp_prashna(None, q, number=74, now_utc=datetime(2026, 10, 2, 7, 0, tzinfo=timezone.utc))
    post = kp_prashna(None, q, number=74, now_utc=datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc))
    assert pre["available"] and post["available"]
    assert pre["debug"]["rp"][0] == "Jupiter"      # 03:00 EDT Friday → Thursday
    assert post["debug"]["rp"][0] == "Venus"       # 10:00 EDT Friday
