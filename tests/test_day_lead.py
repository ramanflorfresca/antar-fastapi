from datetime import date

import pytest

from antar_engine import practice_composer as PC

_REAL_STAR = PC.moon_star_today

YEAR = {"planet": "Venus", "scope": "varshphal_year", "severity": 0.8}
CYCLE = {"planet": "Saturn", "scope": "dasha_period", "severity": 0.5}
NATAL = {"planet": "Mars", "scope": "natal_weakness", "severity": 0.6}
TODAY_HIT = {"planet": "Mercury", "scope": "daily_transit", "severity": 0.4}

FRI, SAT, TUE, WED = date(2026, 10, 9), date(2026, 10, 10), date(2026, 10, 13), date(2026, 10, 14)


@pytest.fixture(autouse=True)
def _no_star(monkeypatch):
    monkeypatch.setattr(PC, "moon_star_today", lambda d: None)     # isolate the weekday rule; star rule tested below


def lead(actives, d):
    s = PC.select_practice_set(actives, today_date=d)
    return s["lead"], s


def test_weekday_ruler_leads_when_it_is_a_candidate():
    l, s = lead([YEAR, CYCLE, NATAL], SAT)
    assert l["planet"] == "Saturn" and l["day_basis"] == "weekday_ruler"
    assert l["year_focus_planet"] == "Venus"
    assert "Venus" in [x["planet"] for x in s["secondary"]]      # the year focus is displaced, not dropped


def test_focus_moves_through_the_week():
    seen = {lead([YEAR, CYCLE, NATAL], d)[0]["planet"] for d in (FRI, SAT, TUE, WED)}
    assert seen == {"Venus", "Saturn", "Mars"}                   # Wed has no Mercury candidate -> year lead (Venus)


def test_no_candidate_for_the_weekday_keeps_the_year_lead():
    l, _ = lead([YEAR, CYCLE, NATAL], WED)
    assert l["planet"] == "Venus" and "day_basis" not in l


def test_acute_transit_today_beats_the_weekday():
    l, _ = lead([YEAR, CYCLE, NATAL, TODAY_HIT], SAT)
    assert l["planet"] == "Mercury" and l["day_basis"] == "today_pressure"


def test_switch_off_restores_the_router(monkeypatch):
    monkeypatch.setenv("PRACTICE_DAY_LEAD", "off")
    l, _ = lead([YEAR, CYCLE, NATAL], SAT)
    assert l["planet"] == "Venus" and "day_basis" not in l


def test_no_date_or_no_actives_is_harmless():
    assert PC.select_practice_set([], today_date=SAT)["lead"] is None
    assert PC.select_practice_set([YEAR], today_date=None)["lead"]["planet"] == "Venus"


def test_why_now_names_the_weekday_not_the_year():
    e = dict(YEAR, day_basis="weekday_ruler", _weekday=SAT.weekday())
    assert "Saturday" in PC._why_now(e, "en") and "annual chart" not in PC._why_now(e, "en")
    assert "sábado" in PC._why_now(e, "es")


def test_moon_star_lord_beats_the_weekday(monkeypatch):
    monkeypatch.setattr(PC, "moon_star_today", lambda d: ("Swati", "Mars"))
    l, s = lead([YEAR, CYCLE, NATAL], SAT)                        # Saturday would pick Saturn; the star says Mars
    assert l["planet"] == "Mars" and l["day_basis"] == "moon_star_lord" and l["_moon_star"] == "Swati"
    assert "Venus" in [x["planet"] for x in s["secondary"]]


def test_star_lord_not_a_candidate_falls_through_to_weekday(monkeypatch):
    monkeypatch.setattr(PC, "moon_star_today", lambda d: ("Ashwini", "Ketu"))
    assert lead([YEAR, CYCLE, NATAL], SAT)[0]["day_basis"] == "weekday_ruler"


def test_acute_transit_still_beats_the_star(monkeypatch):
    monkeypatch.setattr(PC, "moon_star_today", lambda d: ("Swati", "Mars"))
    assert lead([YEAR, NATAL, TODAY_HIT], SAT)[0]["day_basis"] == "today_pressure"


def test_why_now_names_the_star():
    e = dict(YEAR, day_basis="moon_star_lord", _moon_star="Swati")
    assert "Moon is in Swati" in PC._why_now(e, "en")


def test_moon_star_today_is_real_and_valid():
    r = _REAL_STAR(date(2026, 10, 12))
    assert r and r[1] in {"Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"}
    assert _REAL_STAR(date(2026, 10, 12)) == r
    assert len({_REAL_STAR(date(2026, 10, d))[0] for d in range(1, 29)}) >= 20   # it really moves daily
