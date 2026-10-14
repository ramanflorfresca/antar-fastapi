from antar_engine import kp_speculation as ks, app_config


def test_flag_values(monkeypatch):
    for val, want in (("off", False), ("", False), ("all", True), ("a1,B2", True)):
        monkeypatch.setattr(app_config, "get", lambda sb, k, d=None, v=val: v)
        assert ks.enabled_for(None, "b2") == want or val != "a1,B2"
    monkeypatch.setattr(app_config, "get", lambda sb, k, d=None: "a1,b2")
    assert ks.enabled_for(None, "B2") and not ks.enabled_for(None, "c3")


def test_default_is_off_and_registered():
    assert app_config.ALLOWED_KEYS["kp_speculation"]["default"] == "off"


def test_build_on_a_real_chart():
    import swisseph as swe
    from datetime import date
    jd = swe.julday(1985, 3, 14, 5.0)
    out = ks.build({"chart_data": {"birth_jd": jd}, "latitude": 28.6, "longitude": 77.2}, "en", date(2026, 10, 14))
    assert out["experimental"] and out["confidence"] == "low" and out["verdict"] in ("yes", "conditional", "no")
    assert all(w["start"] <= w["end"] for w in out["windows"]) and len(out["windows"]) <= 6
    es = ks.build({"chart_data": {"birth_jd": jd}, "latitude": 28.6, "longitude": 77.2}, "es", date(2026, 10, 14))
    assert es["note"] != out["note"]
