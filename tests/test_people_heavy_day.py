"""[people-heavy-day 2026-10-12] Star limit, window, pick, message, setting default, wiring."""
from datetime import datetime, timezone

from antar_engine import people_heavy_day as P


def test_star_limit_is_three_and_unstar_is_free():
    assert P.can_star(2, False) is True
    assert P.can_star(3, False) is False
    assert P.can_star(3, True) is True          # re-starring an already-starred person is idempotent


def test_window_follows_the_local_morning():
    # 14:00 UTC is 8:00 in UTC-6 and 19:30 in UTC+5.5
    now = datetime(2026, 10, 12, 14, 0, tzinfo=timezone.utc)
    assert P.in_window(now, -6) is True
    assert P.in_window(now, 5.5) is False
    assert P.in_window(datetime(2026, 10, 12, 17, 0, tzinfo=timezone.utc), -6) is False   # 11:00 local


def test_pick_takes_the_oldest_starred_friction_person():
    c = [{"connection_chart_id": "b", "band": "friction", "starred_at": "2026-10-02"},
         {"connection_chart_id": "a", "band": "friction", "starred_at": "2026-10-01"},
         {"connection_chart_id": "c", "band": "steady", "starred_at": "2026-09-01"}]
    assert P.pick(c)["connection_chart_id"] == "a"
    assert P.pick([{"band": "steady"}, {"band": "light"}]) is None
    assert P.pick([]) is None


def test_message_is_plain_decision_framed_and_localised():
    t, b = P.build_message("Andres", "en")
    assert t == "Antar" and "Andres" in b and "ask tomorrow" in b.lower()
    assert "Andres" in P.build_message("Andres", "es")[1] and "mañana" in P.build_message("Andres", "es")[1]
    assert P.build_message("", "pt")[1]                    # a missing name still reads fine
    assert P.build_message("X", "fr")[1] == P.build_message("X", "en")[1]
    low = b.lower()
    assert "feel" not in low and "dasha" not in low and "bad" not in low


def test_setting_defaults_on_and_respects_off():
    assert P.pref_on(None) is True
    assert P.pref_on({"preferences": {"daily_reading": True}}) is True
    assert P.pref_on({"preferences": {"people_heavy_day": False}}) is False
    assert P.pref_on({"preferences": {"people_heavy_day": True}}) is True


def test_wiring():
    import main
    paths = {(r.path, tuple(sorted(getattr(r, "methods", []) or []))) for r in main.app.routes}
    assert ("/api/v1/network/{chart_id}/person/{connection_chart_id}/star", ("PUT",)) in paths
    assert main.scheduler.get_job("people_heavy_day") is not None
    shape = main._st_notif_shape({"channels": {}, "preferences": {}})
    prefs = {p["key"]: p["enabled"] for p in shape["preferences"]}
    assert prefs["people_heavy_day"] is True and prefs["weekly_outlook"] is False   # only the new key defaults on
    assert main._SETTINGS_DEFAULT_NOTIFS["preferences"]["people_heavy_day"] is True
