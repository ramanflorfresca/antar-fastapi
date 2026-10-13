from datetime import date, datetime, timedelta

from antar_engine import personal_window as pw

D = date(2026, 10, 13)           # Tuesday
DASHAS = {"vimsottari": [{"level": "antardasha", "planet_or_sign": "Rahu", "start_date": "2026-01-01", "end_date": "2028-12-31"}]}


def test_subdivide_covers_parent_exactly_and_starts_with_parent():
    s, e = datetime(2026, 1, 1), datetime(2028, 12, 31)
    first = pw.subdivide("Rahu", s, e, s)
    assert first[0] == "Rahu" and first[1] == s
    last = pw.subdivide("Rahu", s, e, e - timedelta(seconds=1))
    assert last[2] == e
    # proportional: the first child is Rahu's 18/120 of the parent
    assert abs((first[2] - first[1]).total_seconds() / (e - s).total_seconds() - 18 / 120) < 1e-9


def test_running_stack_has_three_levels():
    s, e = datetime(2026, 1, 1), datetime(2028, 12, 31)
    st = pw.running_stack("Rahu", s, e, datetime(2026, 10, 13, 6))
    assert st["ad"] == "Rahu" and st["pd"] in pw.VIM_SEQ and st["sd"] in pw.VIM_SEQ


def test_hora_grid_starts_with_weekday_lord_and_is_chaldean():
    g = pw.hora_grid(D, 6 * 60 + 30, 18 * 60)
    assert len(g) == 24 and g[0]["ruler"] == "Mars"            # Tuesday
    assert [h["ruler"] for h in g[:3]] == ["Mars", "Sun", "Venus"]
    assert g[0]["start_min"] == 390 and abs(g[11]["end_min"] - 1080) < 1e-6


def test_build_yields_one_best_and_one_avoid_that_never_overlap_and_respect_rules():
    p = pw.build("Capricorn", DASHAS, D, -4.0, 6 * 60 + 30, 18 * 60 + 10,
                 abhijit="11:50 AM - 12:38 PM", rahu_kalam="3:00 PM - 4:30 PM")
    assert p["available"] and p["version"] == pw.VERSION
    b, a = p["best"], p["avoid"]
    for w in (b, a):
        if w:
            assert w["end_min"] - w["start_min"] <= pw.MAX_WINDOW_MIN
            assert pw.WAKING[0] <= w["start_min"] and w["end_min"] <= pw.WAKING[1]
    if b and a:
        assert min(b["end_min"], a["end_min"]) <= max(b["start_min"], a["start_min"])
    if b:                                                       # never inside a kala
        assert not (b["start_min"] < 16 * 60 + 30 and b["end_min"] > 15 * 60)
    assert len(p["horas"]) == 24


def test_deterministic_and_never_raises():
    a = pw.build("Capricorn", DASHAS, D, -4.0, 390, 1090, "", "", "", "")
    assert a == pw.build("Capricorn", DASHAS, D, -4.0, 390, 1090, "", "", "", "")
    assert pw.build("", {}, D, 0, 390, 1090)["available"] is False
    assert pw.build("Capricorn", {}, D, 0, 390, 1090)["available"] is True     # no dashas: chart + panchang only


def test_period_lord_hour_amplifies_by_function():
    g = {"ruler": "Venus", "start_min": 600, "end_min": 660, "is_day": True}
    plain = pw.score_hora(g, "Capricorn", {"ad": None, "pd": None, "sd": None}, [None, None, None], None)
    run = pw.score_hora(g, "Capricorn", {"ad": None, "pd": None, "sd": "Venus"}, [None, None, None], None)
    assert plain["parts"]["chart"] == 1.0 and run["score"] == plain["score"] + pw.W_SD   # Venus benefic for Capricorn


class _Tbl:
    def __init__(self, fail): self.fail, self.rows = fail, []
    def table(self, _): return self
    def upsert(self, row, on_conflict=None): self.row = row; return self
    def execute(self):
        if self.fail:
            raise RuntimeError("table missing")
        self.rows.append(self.row)


def test_record_retries_after_failure_and_stops_after_success(monkeypatch):
    pw._DONE.clear(); pw._RETRY_AFTER.clear()
    p = {"available": True, "date": "2026-10-13"}
    db = _Tbl(fail=True)
    assert pw.record(db, "c1", p) is False and "c1" not in {k[0] for k in pw._DONE}
    assert pw.record(db, "c1", p) is False                     # inside the backoff: no second hit
    pw._RETRY_AFTER.clear()                                    # backoff elapsed
    db.fail = False
    assert pw.record(db, "c1", p) is True and len(db.rows) == 1
    assert pw.record(db, "c1", p) is False and len(db.rows) == 1   # done: never written twice


def test_current_pratyantar_derived_from_antardasha_when_no_pd_rows():
    d = {"vimsottari": [{"level": "antardasha", "planet_or_sign": "Rahu", "start_date": "2026-01-01", "end_date": "2028-12-31"}]}
    pd = pw.current_pratyantar(d, date(2026, 10, 13))
    assert pd["planet_or_sign"] == "Jupiter" == pw.running_stack("Rahu", datetime(2026, 1, 1), datetime(2029, 1, 1), datetime(2026, 10, 13, 12))["pd"]
    assert pd["start_date"] <= "2026-10-13" <= pd["end_date"]
    assert pw.current_pratyantar({}, date(2026, 10, 13)) == {}
    assert pw.current_pratyantar({"vimsottari": [{"level": "mahadasha", "planet_or_sign": "Rahu", "start_date": "2020-01-01", "end_date": "2038-01-01"}]}) == {}
