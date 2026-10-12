"""[phase-view 2026-10-12] Current phase: dates, progress, combination wording, areas, turning points."""
from datetime import date

from antar_engine import phase_view as PV


def _rows():
    return {"vimsottari": [
        {"level": "mahadasha", "planet_or_sign": "Rahu", "start_date": "2011-04-01", "end_date": "2029-04-01"},
        {"level": "mahadasha", "planet_or_sign": "Jupiter", "start_date": "2029-04-01", "end_date": "2045-04-01"},
        {"level": "antardasha", "planet_or_sign": "Rahu", "parent_lord": "Rahu", "start_date": "2024-01-01", "end_date": "2026-06-01"},
        {"level": "antardasha", "planet_or_sign": "Jupiter", "parent_lord": "Rahu", "start_date": "2026-06-01", "end_date": "2028-10-01"},
        {"level": "antardasha", "planet_or_sign": "Saturn", "parent_lord": "Rahu", "start_date": "2028-10-01", "end_date": "2029-04-01"},
        {"level": "antardasha", "planet_or_sign": "Jupiter", "parent_lord": "Jupiter", "start_date": "2029-04-01", "end_date": "2031-01-01"},
    ]}


T = date(2026, 10, 12)


def test_chapter_shift_dates_and_progress():
    out = PV.build(_rows(), None, "en", T)
    assert out["available"] is True
    c, s = out["chapter"], out["shift"]
    assert c["planet"] == "Rahu" and c["start"] == "2011-04-01" and c["end"] == "2029-04-01"
    assert 0 < c["progress_pct"] < 100 and c["months_left"] == 30
    assert s["planet"] == "Jupiter" and s["start"] == "2026-06-01" and s["end"] == "2028-10-01"
    assert c["watch"] and c["helps"] and c["line"]


def test_upcoming_shifts_stay_inside_the_chapter():
    out = PV.build(_rows(), None, "en", T)
    assert [u["planet"] for u in out["upcoming_shifts"]] == ["Saturn"]   # not the next chapter's Jupiter


def test_turning_points_in_order():
    tp = PV.build(_rows(), None, "en", T)["turning_points"]
    assert [x["date"] for x in tp] == ["2028-10-01", "2029-04-01"]
    assert tp[0]["in_months"] == 24 and "Jupiter" in tp[0]["label"] and "Saturn" in tp[0]["label"]
    assert tp[1]["in_months"] == 30


def test_same_planet_wording_and_flag():
    rows = _rows()
    out = PV.build(rows, None, "en", date(2025, 1, 1))
    assert out["shift"]["planet"] == "Rahu" and out["shift"].get("same_as_chapter") is True
    assert "same energy again" in out["how_they_combine"].lower()


def test_life_areas_come_from_the_windows_feed():
    feed = {"now": [{"topic": "money", "kind": "open", "start": "2026-10-01", "end": "2027-01-01"},
                    {"topic": "health", "kind": "care", "start": "2026-10-01", "end": "2027-01-01"}]}
    areas = {a["topic"]: a["state"] for a in PV.build(_rows(), feed, "en", T)["life_areas"]}
    assert areas == {"career": "neutral", "money": "supporting", "love": "neutral", "health": "testing"}
    assert [a["area"] for a in PV.build(_rows(), feed, "es", T)["life_areas"]] == ["Trabajo", "Dinero", "Amor", "Salud"]


def test_no_vimshottari_is_unavailable_not_an_error():
    assert PV.build({}, None, "en", T) == {"available": False}
    assert PV.build({"vimsottari": []}, None, "en", T) == {"available": False}


def test_other_dasha_systems_are_ignored():
    d = _rows()
    d["jaimini"] = [{"level": "mahadasha", "planet_or_sign": "Aries", "start_date": "2020-01-01", "end_date": "2030-01-01"}]
    assert PV.build(d, None, "en", T)["chapter"]["planet"] == "Rahu"


def test_es_wording():
    out = PV.build(_rows(), None, "es", T)
    assert out["language"] == "es" and out["how_they_combine"]
    assert "same energy" not in out["how_they_combine"].lower()


def test_no_jargon_in_copy():
    import re
    out = PV.build(_rows(), {"now": []}, "en", T)
    blob = " ".join([out["how_they_combine"]] + [a["line"] for a in out["life_areas"]]
                    + [t["label"] for t in out["turning_points"]]).lower()
    assert not re.search(r"dasha|antardasha|mahadasha|vimshottari|nakshatra|house", blob)


def test_route_registered():
    import main
    assert any(r.path == "/api/v1/phase/{chart_id}" for r in main.app.routes)


def test_shift_start_matches_the_running_row_not_an_older_row_of_the_same_planet():
    d = _rows()
    d["vimsottari"].insert(0, {"level": "antardasha", "planet_or_sign": "Jupiter", "parent_lord": "Rahu",
                               "start_date": "1990-01-01", "end_date": "2030-01-01"})   # a stray older row
    s = PV.build(d, None, "en", T)["shift"]
    assert s["start"] == "2026-06-01" and s["end"] == "2028-10-01"
