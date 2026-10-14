from datetime import date, timedelta

import pytest

from antar_engine import practice_composer as PC

_REAL = PC.moon_ruling_today

YEAR = {"planet": "Venus", "scope": "varshphal_year", "severity": 0.8}
CYCLE = {"planet": "Saturn", "scope": "dasha_period", "severity": 0.5}
NATAL = {"planet": "Mars", "scope": "natal_weakness", "severity": 0.6}
TODAY_HIT = {"planet": "Mercury", "scope": "daily_transit", "severity": 0.4}
D = date(2026, 10, 12)


def ruling(star=None, sub=None, sign=None, day=None, nak="Swati"):
    return {"nakshatra": nak, "star_lord": star, "sub_lord": sub, "sign_lord": sign, "day_lord": day}


@pytest.fixture(autouse=True)
def _none(monkeypatch):
    monkeypatch.setattr(PC, "moon_ruling_today", lambda d: None)


def lead(actives, r=None, monkeypatch=None):
    if r is not None:
        PC.moon_ruling_today = lambda d: r            # autouse fixture restores it
    s = PC.select_practice_set(actives, today_date=D)
    return s["lead"], s


def test_no_ruling_data_keeps_the_year_lead():
    l, _ = lead([YEAR, CYCLE, NATAL])
    assert l["planet"] == "Venus" and "day_basis" not in l


def test_star_lord_leads_and_year_focus_stays_visible():
    l, s = lead([YEAR, CYCLE, NATAL], ruling(star="Saturn", sub="Rahu", sign="Venus", day="Moon"))
    assert l["planet"] == "Saturn" or l["planet"] == "Venus"       # Saturn=3 vs Venus=1 -> Saturn
    assert l["planet"] == "Saturn" and l["day_basis"] == "ruling_planets" and "star" in l["_roles"]
    assert l["_moon_star"] == "Swati" and l["year_focus_planet"] == "Venus"
    assert "Venus" in [x["planet"] for x in s["secondary"]]


def test_planet_with_several_roles_beats_a_single_star_role():
    # Venus holds sub (2) + sign (1) = 3 ties Mars star (3) -> severity decides (Venus .8 > Mars .6)
    l, _ = lead([YEAR, NATAL], ruling(star="Mars", sub="Venus", sign="Venus", day="Moon"))
    assert l["planet"] == "Venus" and set(l["_roles"]) == {"sub", "sign"}
    # but a star lord with sub as well outranks
    l2, _ = lead([YEAR, NATAL], ruling(star="Mars", sub="Mars", sign="Venus", day="Moon"))
    assert l2["planet"] == "Mars"


def test_weekday_lord_alone_can_lead():
    l, _ = lead([YEAR, CYCLE, NATAL], ruling(star="Ketu", sub="Rahu", sign="Moon", day="Saturn"))
    assert l["planet"] == "Saturn" and l["_roles"] == ["day"] and "_moon_star" not in l


def test_no_ruling_planet_is_a_candidate_falls_back_to_year():
    l, _ = lead([YEAR, CYCLE, NATAL], ruling(star="Ketu", sub="Rahu", sign="Moon", day="Sun"))
    assert l["planet"] == "Venus" and "day_basis" not in l


def test_acute_transit_beats_the_ruling_planets():
    l, _ = lead([YEAR, NATAL, TODAY_HIT], ruling(star="Mars", sub="Mars", sign="Mars", day="Mars"))
    assert l["planet"] == "Mercury" and l["day_basis"] == "today_pressure"


def test_switch_off_restores_the_router(monkeypatch):
    monkeypatch.setenv("PRACTICE_DAY_LEAD", "off")
    l, _ = lead([YEAR, CYCLE, NATAL], ruling(star="Saturn", sub="Saturn", sign="Saturn", day="Saturn"))
    assert l["planet"] == "Venus" and "day_basis" not in l


def test_no_date_or_no_actives_is_harmless():
    assert PC.select_practice_set([], today_date=D)["lead"] is None
    assert PC.select_practice_set([YEAR], today_date=None)["lead"]["planet"] == "Venus"


def test_why_now_text():
    star = dict(YEAR, day_basis="ruling_planets", _moon_star="Swati", _roles=["star"])
    assert "Moon is in Swati" in PC._why_now(star, "en") and "annual chart" not in PC._why_now(star, "en")
    other = dict(YEAR, day_basis="ruling_planets", _roles=["sub"])
    assert "influences point to" in PC._why_now(other, "en")
    assert "Luna" in PC._why_now(star, "es")


def test_real_kp_chain_for_a_known_day():
    r = _REAL(D)                                                   # verified against Parashara's Light / prod: Swati
    assert r["nakshatra"] == "Swati" and r["star_lord"] == "Rahu" and r["day_lord"] == "Moon"
    assert r["sub_lord"] == "Venus" and r["sign_lord"] == "Venus"
    nine = {"Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"}
    days = [_REAL(D + timedelta(days=i)) for i in range(28)]
    assert all(x["star_lord"] in nine and x["sub_lord"] in nine for x in days)
    assert len({x["nakshatra"] for x in days}) >= 20             # the Moon really changes star ~daily
