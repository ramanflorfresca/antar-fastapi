"""One-line birth entry: '15 Oct 1990, 2:30 pm, Hyderabad' -> date, time, place to confirm. Never guesses silently."""
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from antar_engine import birth_parse as BP  # noqa: E402


@pytest.mark.parametrize("text,date,time,prec,city", [
    ("15 Oct 1990, 2:30 pm, Hyderabad", "1990-10-15", "14:30", "exact", "Hyderabad"),
    ("born oct 15th 1990 at 14:30 in New Delhi", "1990-10-15", "14:30", "exact", "New Delhi"),
    ("15 de octubre de 1990, 9:15 pm, Medellín, Colombia", "1990-10-15", "21:15", "exact", "Medellin Colombia"),
    ("1990-10-15 noon London", "1990-10-15", "12:00", "exact", "London"),
    ("October 15, 1990 12:05 am Pune", "1990-10-15", "00:05", "exact", "Pune"),
    ("15/10/1990 evening Pune", "1990-10-15", "18:30", "approximate", "Pune"),
    ("3 mar 1988, not sure of the time, Austin Texas", "1988-03-03", "12:00", "unknown", "Austin Texas"),
    ("15/10/90 7.45 am Lima", "1990-10-15", "07:45", "exact", "Lima"),
    ("15 outubro 1990 às 6h30 pm Lisboa", "1990-10-15", "18:30", "exact", "Lisboa"),
])
def test_parses_date_time_and_place(text, date, time, prec, city):
    r = BP.parse(text)
    assert (r["birth_date"], r["birth_time"], r["time_precision"], r["city_text"]) == (date, time, prec, city), r
    assert r["date_ambiguous"] is None and r["time_ambiguous"] is None and r["missing"] == []


def test_an_ambiguous_day_month_is_returned_as_a_question_not_a_guess():
    r = BP.parse("04/05/1990 8am Bogota")
    assert r["birth_date"] is None and r["date_ambiguous"] == ["1990-05-04", "1990-04-05"] and "date" not in r["missing"]
    assert BP.parse("04/05/1990 8am Bogota", "dmy")["birth_date"] == "1990-05-04"
    assert BP.parse("04/05/1990 8am Bogota", "mdy")["birth_date"] == "1990-04-05"
    assert BP.parse("10/10/1990")["birth_date"] == "1990-10-10"                           # same day and month: not ambiguous
    assert BP.parse("25/12/1990")["birth_date"] == "1990-12-25" and BP.parse("12/25/1990")["birth_date"] == "1990-12-25"


def test_a_clock_time_without_am_pm_is_returned_as_two_candidates():
    r = BP.parse("15/10/1990 2:30 Mumbai")
    assert r["birth_time"] is None and r["time_ambiguous"] == ["02:30", "14:30"] and r["city_text"] == "Mumbai"
    assert BP.parse("15/10/1990 14:30 Mumbai")["birth_time"] == "14:30"                    # 24h is unambiguous
    assert BP.parse("15/10/1990 00:15 Mumbai")["birth_time"] == "00:15"


def test_missing_parts_are_named_and_garbage_is_safe():
    r = BP.parse("10/15/90 midnight")
    assert r["birth_date"] == "1990-10-15" and r["birth_time"] == "00:00" and r["missing"] == ["place"]
    assert BP.parse("")["missing"] == ["date", "time", "place"]
    assert BP.parse("hello there")["birth_date"] is None
    assert BP.parse("32/13/1990")["birth_date"] is None and BP.parse("31/02/1990")["birth_date"] is None
    assert BP.parse("15 oct 1850")["birth_date"] is None                                    # out of range
    assert BP.parse("15 oct 2999")["birth_date"] is None


# ── HTTP ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def client(monkeypatch):
    import main
    monkeypatch.setattr(main, "_st_identity", lambda a: ("u1" if a == "Bearer ok" else None, None))

    async def geo(city, country):
        if city.lower().startswith("nowhere"):
            raise RuntimeError("no match")
        return (17.38, 78.48, "Asia/Kolkata", "test")
    monkeypatch.setattr(main, "_geocode_city", geo)
    return TestClient(main.app), main


def test_parse_birth_endpoint(client):
    c, _ = client
    assert c.post("/api/v1/people/parse-birth", json={"text": "15 Oct 1990"}).status_code == 401
    assert c.post("/api/v1/people/parse-birth", json={"text": "  "}, headers={"Authorization": "Bearer ok"}).status_code == 422
    r = c.post("/api/v1/people/parse-birth", json={"text": "15 Oct 1990, 2:30 pm, Hyderabad"}, headers={"Authorization": "Bearer ok"}).json()
    assert r["birth_date"] == "1990-10-15" and r["birth_time"] == "14:30" and r["missing"] == []
    assert r["place"] == {"city": "Hyderabad", "latitude": 17.38, "longitude": 78.48, "timezone": "Asia/Kolkata"}
    miss = c.post("/api/v1/people/parse-birth", json={"text": "15 Oct 1990, 2:30 pm, Nowhereville"}, headers={"Authorization": "Bearer ok"}).json()
    assert miss["place"] is None and "place" in miss["missing"] and miss["birth_date"] == "1990-10-15"
    amb = c.post("/api/v1/people/parse-birth", json={"text": "04/05/1990 8am Lima", "date_order": "mdy"}, headers={"Authorization": "Bearer ok"}).json()
    assert amb["birth_date"] == "1990-04-05"


# ── where they live NOW (same screen as the birth place) ─────────────────────
def test_current_location_columns_for_the_added_person(client):
    import asyncio
    c, main = client
    mk = lambda **kw: main.CompatibilityStartRequest(chart_id_a="a", **kw)
    assert asyncio.run(main._compat_current_columns(mk())) == {}
    cols = asyncio.run(main._compat_current_columns(mk(current_city_b="Austin", current_country_b="US")))
    assert cols == {"current_city": "Austin", "current_country": "US", "current_latitude": 17.38, "current_longitude": 78.48,
                    "current_timezone": "Asia/Kolkata"}
    given = asyncio.run(main._compat_current_columns(mk(current_city_b="Lima", current_latitude_b=-12.0, current_longitude_b=-77.0,
                                                        current_timezone_b="America/Lima")))
    assert given["current_latitude"] == -12.0 and given["current_timezone"] == "America/Lima"
    miss = asyncio.run(main._compat_current_columns(mk(current_city_b="Nowhereville", current_country_b="XX")))
    assert miss == {"current_city": "Nowhereville", "current_country": "XX"}                # geocode failed: still stored as typed
