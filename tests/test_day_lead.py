from datetime import date

from antar_engine import practice_composer as PC

YEAR = {"planet": "Venus", "scope": "varshphal_year", "severity": 0.8}
CYCLE = {"planet": "Saturn", "scope": "dasha_period", "severity": 0.5}
NATAL = {"planet": "Mars", "scope": "natal_weakness", "severity": 0.6}
TODAY_HIT = {"planet": "Mercury", "scope": "daily_transit", "severity": 0.4}

FRI, SAT, TUE, WED = date(2026, 10, 9), date(2026, 10, 10), date(2026, 10, 13), date(2026, 10, 14)


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
