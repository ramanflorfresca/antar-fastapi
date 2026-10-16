"""[audit-dates 2026-10-15] A stretch in another year, or months away, carries its year so it is never read as this year's."""
from datetime import date

from antar_engine import shortcuts as sc, coming as cm

TODAY = date(2026, 10, 15)


def test_near_dates_stay_short_and_far_ones_get_a_year():
    assert sc._md(date(2026, 10, 31), "en", TODAY) == "Oct 31"
    assert sc._md(date(2027, 8, 1), "en", TODAY) == "Aug 1, 2027"
    assert sc._md(date(2027, 1, 10), "en", TODAY) == "Jan 10, 2027"
    assert sc._md(date(2027, 8, 1), "es", TODAY) == "1 ago 2027"


def test_shortcut_care_line_for_next_year_names_the_year():
    feed = {"tracks": [{"topic": "career", "windows": [{"kind": "care", "start": "2027-08-01", "end": "2027-10-31"}]}]}
    out = sc._dot_and_stat("career", feed, "en", TODAY)
    assert "Take care Aug 1, 2027 – Oct 31, 2027." in out["stat"]


def test_coming_sentence_names_the_year_for_another_year():
    w = {"topic": "career", "kind": "care", "start": date(2027, 8, 1), "end": date(2027, 10, 31)}
    assert "2027" in cm._sentence(w, "en")
