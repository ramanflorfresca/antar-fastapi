import json

from antar_engine import dasha_heal as dh


def _chart():
    from antar_engine import chart as chart_module
    return chart_module.calculate_chart(birth_date="1990-10-24", birth_time="15:00", lat=23.03, lng=72.58,
                                        tz_offset=5.5, ayanamsa="lahiri")


class _Q:
    def __init__(self, db, table): self.db, self.t, self.f, self.rows = db, table, {}, None
    def select(self, *_): return self
    def eq(self, k, v): self.f[k] = v; return self
    def limit(self, *_): return self
    def order(self, *_): return self
    def insert(self, rows): self.rows = rows; return self
    def execute(self):
        if self.rows is not None:
            self.db.inserted.extend(self.rows); return type("R", (), {"data": self.rows})
        if self.t == "dasha_periods":
            return type("R", (), {"data": ([{"id": 1}] if (self.db.has or self.db.inserted) else [])})
        return type("R", (), {"data": self.db.charts})


class _DB:
    def __init__(self, has=False):
        self.has, self.inserted = has, []
        cd = _chart()
        self.charts = [{"chart_data": json.dumps(cd), "birth_date": "1990-10-24"}]
    def table(self, t): return _Q(self, t)


def test_build_rows_matches_creation_shape():
    systems = dh.compute(_chart(), "1990-10-24")
    rows = dh.build_rows("cid", systems)
    vim = [r for r in rows if r["system"] == "vimsottari"]
    assert {r["level"] for r in vim} == {1, 2, 3} and {r["type"] for r in vim} == {"mahadasha", "antardasha", "pratyantardasha"}
    assert [len([r for r in vim if r["level"] == k]) for k in (1, 2, 3)] == [9, 81, 729]
    assert all(r["chart_id"] == "cid" and r["start_date"] and r["end_date"] and r["planet_or_sign"] for r in vim)
    assert {r["system"] for r in rows} == {"vimsottari", "jaimini", "ashtottari"}


def test_heal_inserts_only_when_chart_has_no_rows():
    db = _DB(has=False)
    n = dh.heal(db, "cid")
    assert n == len(db.inserted) > 90
    assert dh.heal(_DB(has=True), "cid") == 0          # existing rows: never touched
    d2 = _DB(has=False)
    assert dh.heal(d2, "cid", dry_run=True) > 0 and d2.inserted == []


def test_heal_skips_a_chart_it_cannot_compute():
    db = _DB()
    db.charts = [{"chart_data": {"planets": {}}, "birth_date": "1990-10-24"}]
    assert dh.heal(db, "cid") == 0 and db.inserted == []


def test_schedule_is_once_per_chart_with_backoff(monkeypatch):
    calls = []
    monkeypatch.setattr(dh, "heal", lambda sb, cid: calls.append(cid) or 0)
    dh._INFLIGHT.clear(); dh._NEXT_TRY.clear()
    import time
    assert dh.schedule(object(), "c1") is True
    assert dh.schedule(object(), "c1") is False          # inside the backoff
    assert dh.schedule(object(), "") is False
    for _ in range(50):
        if calls: break
        time.sleep(0.02)
    assert calls == ["c1"]


def test_pratyantars_for_gives_729_contiguous_levels_per_chart():
    vim = dh.compute(_chart(), "1990-10-24")["vimsottari"]
    assert len([p for p in vim if p["level"] == "pratyantardasha"]) == 729
    ads = [p for p in vim if p["level"] == "antardasha"]
    pds = [p for p in vim if p["level"] == "pratyantardasha"]
    for k, ad in enumerate(ads):
        kids = pds[k * 9:(k + 1) * 9]
        assert kids[0]["planet_or_sign"] == ad["planet_or_sign"] and kids[0]["parent_lord"] == ad["planet_or_sign"]
        assert kids[0]["start_date"] == ad["start_date"] and kids[-1]["end_date"] == ad["end_date"]
        assert all(a["end_date"] == b["start_date"] for a, b in zip(kids, kids[1:]))
    assert dh.pratyantars_for(vim) == []                      # already has them: never doubled


def test_person_chart_builder_now_returns_rows_including_pratyantars():
    from antar_engine import people_links
    rows = people_links.build_dasha_rows("cid", _chart())
    assert len(rows) > 800 and {r["level"] for r in rows if r["system"] == "vimsottari"} == {1, 2, 3}


class _BF:
    def __init__(self, ads, has3=False):
        self.ads, self.has3, self.inserted = ads, has3, []
    def table(self, _): return _BQ(self)


class _BQ:
    def __init__(self, db): self.db, self.f, self.rows = db, {}, None
    def select(self, *_): return self
    def eq(self, k, v): self.f[k] = v; return self
    def order(self, *_): return self
    def limit(self, *_): return self
    def range(self, *_): return self
    def insert(self, rows): self.rows = rows; return self
    def execute(self):
        if self.rows is not None:
            self.db.inserted.extend(self.rows); return type("R", (), {"data": self.rows})
        if self.f.get("level") == 3:
            return type("R", (), {"data": [{"id": 1}] if self.db.has3 or self.db.inserted else []})
        return type("R", (), {"data": self.db.ads})


def test_backfill_builds_from_the_charts_own_antardashas_and_is_insert_only():
    vim = dh.compute(_chart(), "1990-10-24")["vimsottari"]
    ads = [{"planet_or_sign": p["planet_or_sign"], "start_date": p["start_date"], "end_date": p["end_date"]} for p in vim if p["level"] == "antardasha"]
    db = _BF(ads)
    assert dh.backfill_pratyantars(db, "cid", dry_run=True) == 729 and db.inserted == []
    assert dh.backfill_pratyantars(db, "cid") == 729 and len(db.inserted) == 729
    assert dh.backfill_pratyantars(db, "cid") == 0                 # now has level 3: untouched
    assert dh.backfill_pratyantars(_BF(ads, has3=True), "cid") == 0


class _CV:
    """dasha_periods stub with per-level rows for one chart; charts table returns a real computed chart."""
    def __init__(self, mds=None, ads=None):
        self.levels = {1: list(mds or []), 2: list(ads or []), 3: []}
        self.inserted = []
        cd = _chart()
        self.chart = [{"chart_data": json.dumps(cd), "birth_date": "1990-10-24"}]
    def table(self, t): return _CVQ(self, t)


class _CVQ:
    def __init__(self, db, t): self.db, self.t, self.f, self.rows = db, t, {}, None
    def select(self, *_): return self
    def eq(self, k, v): self.f[k] = v; return self
    def order(self, *_): return self
    def limit(self, *_): return self
    def insert(self, rows): self.rows = rows; return self
    def execute(self):
        if self.rows is not None:
            for r in self.rows:
                self.db.levels.setdefault(r["level"], []).append(r) if r["system"] == "vimsottari" else None
            self.db.inserted.extend(self.rows)
            return type("R", (), {"data": self.rows})
        if self.t == "charts":
            return type("R", (), {"data": self.db.chart})
        return type("R", (), {"data": self.db.levels.get(self.f.get("level"), [])})


def test_complete_vimsottari_adds_missing_levels_and_keeps_existing_rows():
    vim = dh.compute(_chart(), "1990-10-24")["vimsottari"]
    mds = [{"planet_or_sign": p["planet_or_sign"], "start_date": p["start_date"], "end_date": p["end_date"]} for p in vim if p["level"] == "mahadasha"]
    db = _CV(mds=mds)                                              # mahadasha only, like the early charts
    assert dh.complete_vimsottari(db, "cid", dry_run=True) == 81 + 729 and db.inserted == []
    assert dh.complete_vimsottari(db, "cid") == 810
    assert {r["level"] for r in db.inserted} == {2, 3}             # the 9 mahadasha rows are never re-inserted
    assert dh.complete_vimsottari(db, "cid") == 0                  # has antardashas now: untouched


def test_complete_vimsottari_refuses_when_stored_mahadashas_disagree():
    db = _CV(mds=[{"planet_or_sign": "Sun", "start_date": "1900-01-01", "end_date": "1906-01-01"}])
    assert dh.complete_vimsottari(db, "cid") == 0 and db.inserted == []


def test_complete_vimsottari_from_nothing_inserts_all_three_levels():
    db = _CV()
    assert dh.complete_vimsottari(db, "cid") == 9 + 81 + 729


def test_alert_failure_raises_a_keyed_alert_and_never_raises(monkeypatch):
    seen = []
    from antar_engine import alerting
    monkeypatch.setattr(alerting, "alert", lambda key, message, level="warn", detail=None: seen.append((key, level, message, detail)))
    dh.alert_failure("create:insert:sync", "abcdef12-0000", RuntimeError("boom"))
    assert seen == [("dasha_write_failed:create:insert:sync", "error", "dasha create:insert:sync failed for chart abcdef12: boom",
                     "chart_id=abcdef12-0000")]
    monkeypatch.setattr(alerting, "alert", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("webhook down")))
    dh.alert_failure("x", "c", "e")                                  # a broken alert channel must not raise


def test_heal_thread_failure_alerts_as_a_warning(monkeypatch):
    import time
    seen = []
    monkeypatch.setattr(dh, "alert_failure", lambda stage, cid, err, level="error": seen.append((stage, level)))
    monkeypatch.setattr(dh, "heal", lambda sb, cid: (_ for _ in ()).throw(RuntimeError("db down")))
    dh._INFLIGHT.clear(); dh._NEXT_TRY.clear()
    assert dh.schedule(object(), "c9") is True
    for _ in range(100):
        if seen:
            break
        time.sleep(0.02)
    assert seen == [("heal", "warn")]


def test_creation_and_edit_paths_alert_on_their_silent_failures():
    import re
    src = open("main.py").read()
    for stage in ("create:compute:vimsottari", "create:insert:", "edit-birth", "create:no-vimsottari-rows"):
        assert re.search(r"_daf\(f?\"" + re.escape(stage), src), stage
