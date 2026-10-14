from datetime import date
from antar_engine import when_engine as we, kp_when


class _Ctx:
    today = date(2026, 1, 1)
    birth_date = "1980-06-15"


def _run(monkeypatch, base, kp=None, lk=None):
    monkeypatch.setattr(we.rr, "_windows", lambda ctx, subj, lang: base)
    monkeypatch.setattr(we, "_lk_year", lambda ctx, subj: lk)
    return we.build(_Ctx(), "money", "en", kp=kp)


def test_single_signal_is_not_a_headline(monkeypatch):
    out = _run(monkeypatch, [{"start": "2026-03-01", "end": "2026-06-01", "both_systems": False}])
    assert out["agree"] == [] and len(out["also"]) == 1


def test_two_independent_lines_agree_and_peak_is_reported(monkeypatch):
    base = [{"start": "2026-03-01", "end": "2026-09-01", "both_systems": False}]
    kp = {"windows": [{"start": "2026-05-01", "end": "2026-05-20"}], "promise": "weak"}
    out = _run(monkeypatch, base, kp)
    a = out["agree"]
    assert len(a) == 1 and a[0]["start"] == "2026-05-01" and a[0]["end"] == "2026-05-20" and a[0]["signals"] == 2
    assert out["kp_promise"] == "weak" and "kp" in a[0]["lines"] and "timing_methods" in a[0]["lines"]


def test_both_systems_counts_as_two_and_lk_year_raises_it(monkeypatch):
    base = [{"start": "2026-03-01", "end": "2026-09-01", "both_systems": True}]
    out = _run(monkeypatch, base, None, lk=(date(2026, 2, 1), date(2026, 5, 1)))
    a = out["agree"]
    assert a[0]["signals"] == 3 and a[0]["strength"] == "strong" and a[0]["peaks"]
    assert a[0]["start"] == "2026-03-01" and a[0]["end"] == "2026-09-01"


def test_kp_flag_values(monkeypatch):
    from antar_engine import app_config
    for val, cid, want in (("off", "x", False), ("all", "x", True), ("a1,B2", "b2", True), ("a1", "c3", False)):
        monkeypatch.setattr(app_config, "get", lambda sb, k, d=None, v=val: v)
        assert kp_when.enabled_for(None, cid) == want
    assert app_config.ALLOWED_KEYS["kp_when"]["default"] == "off"


def test_kp_windows_shape_on_a_real_chart():
    from antar_engine.kp.kp_chart import compute_kp_chart
    ch = compute_kp_chart("1985-03-14", "10:30", 40.7, -74.0, tz_offset=-5)
    out = kp_when.windows(ch, "marriage", date(2026, 10, 14))
    assert out["promise"] in ("strong", "partial", "weak") and all(w["start"] <= w["end"] for w in out["windows"])
    assert kp_when.windows(ch, "nonsense", date(2026, 10, 14)) is None


def test_short_peak_does_not_lift_the_whole_range(monkeypatch):
    base = [{"start": "2026-03-01", "end": "2026-12-01", "both_systems": True}]
    kp = {"windows": [{"start": "2026-05-01", "end": "2026-05-04"}], "promise": "partial"}
    out = _run(monkeypatch, base, kp)
    a = out["agree"][0]
    assert a["strength"] == "good" and a["signals"] == 2 and a["peaks"]
