"""The relationship page must say 'Raman + Saransh', never 'Person A + saransh'."""
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from circle_fakedb import DB  # noqa: E402


def test_display_name_prefers_a_real_name_then_the_chart_then_you():
    import main
    f = main._compat_display_name
    assert f("Raman", {"first_name": "X"}) == "Raman"
    for ph in (None, "", "  ", "Person A", "person a", "Partner", "Person B"):
        assert f(ph, {"first_name": "Raman", "name": "Raman Singh"}) == "Raman"
        assert f(ph, {"first_name": "", "name": "Raman Singh"}) == "Raman"
        assert f(ph, {"first_name": "Person A", "name": ""}) == "You"
        assert f(ph, {}) == "You" and f(ph, None) == "You"


def test_start_request_no_longer_defaults_to_the_placeholder():
    import main
    r = main.CompatibilityStartRequest(chart_id_a="a")
    assert r.name_a is None                      # the old default "Person A" was truthy and beat the chart's own name
    assert main.CompatibilityStartRequest(chart_id_a="a", name_a="Raman").name_a == "Raman"


def test_a_session_saved_with_person_a_reads_with_the_charts_first_name(monkeypatch):
    import main
    db = DB()
    db.t["charts"] = [{"id": "A", "first_name": "Raman", "name": "", "deleted_at": None}]
    db.t["compatibility_sessions"] = [{"id": "s1", "chart_id_a": "A", "chart_id_b": "B", "name_a": "Person A", "name_b": "saransh",
                                       "compat_type": "cofounder", "layer1_analysis": "Person A and saransh have a fit.", "score": 55,
                                       "current_layer": 1}]
    monkeypatch.setattr(main, "supabase", db)
    r = TestClient(main.app).get("/api/v1/compatibility/session/s1")
    assert r.status_code == 200 and r.json()["name_a"] == "Raman" and r.json()["name_b"] == "saransh"
    # an already-real name is left alone
    db.t["compatibility_sessions"][0]["name_a"] = "Rae"
    assert TestClient(main.app).get("/api/v1/compatibility/session/s1").json()["name_a"] == "Rae"
    # no name anywhere: 'You', never the placeholder
    db.t["compatibility_sessions"][0]["name_a"] = "Person A"
    db.t["charts"][0].update(first_name="", name="")
    assert TestClient(main.app).get("/api/v1/compatibility/session/s1").json()["name_a"] == "You"
