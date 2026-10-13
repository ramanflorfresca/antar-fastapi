from datetime import datetime, timezone

from antar_engine import dasha_audit as da


class FakeSB:
    """charts + dasha_periods stub. rows: {chart_id: set of (system, level)}; repairs add what they would add."""
    def __init__(self, rows, created=None):
        self.rows = {k: set(v) for k, v in rows.items()}
        self.created = created or {}
    def table(self, t): return _Q(self, t)


class _Q:
    def __init__(self, db, t): self.db, self.t, self.f, self.since = db, t, {}, None
    def select(self, *_): return self
    def is_(self, *_): return self
    def gte(self, k, v): self.since = v; return self
    def eq(self, k, v): self.f[k] = v; return self
    def order(self, *_): return self
    def range(self, *_): return self
    def limit(self, *_): return self
    def execute(self):
        if self.t == "charts":
            ids = [c for c in self.db.rows if self.since is None or self.db.created.get(c, "9999") >= self.since]
            return type("R", (), {"data": [{"id": c} for c in ids]})
        have = self.db.rows.get(self.f["chart_id"], set())
        if "system" in self.f:
            ok = (self.f["system"], self.f["level"]) in have
        else:
            ok = bool(have)
        return type("R", (), {"data": [{"id": 1}] if ok else []})


FULL = {("vimsottari", 1), ("vimsottari", 2), ("vimsottari", 3)}
NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)


def test_classify_each_gap_class():
    db = FakeSB({"ok": FULL, "none": set(), "noad": {("vimsottari", 1), ("jaimini", 1)}, "nopd": {("vimsottari", 1), ("vimsottari", 2)}})
    assert [da.classify(db, c) for c in ("ok", "none", "noad", "nopd")] == [None, "no_rows", "no_ad", "no_pd"]


def test_audit_repairs_with_the_right_function_and_alerts_as_a_warning(monkeypatch):
    from antar_engine import dasha_heal, alerting
    db = FakeSB({"ok": FULL, "none": set(), "nopd": {("vimsottari", 1), ("vimsottari", 2)}})
    calls = []
    monkeypatch.setattr(dasha_heal, "heal", lambda sb, c: calls.append(("heal", c)) or sb.rows[c].update(FULL) or 1)
    monkeypatch.setattr(dasha_heal, "backfill_pratyantars", lambda sb, c: calls.append(("pd", c)) or sb.rows[c].add(("vimsottari", 3)) or 729)
    seen = []
    monkeypatch.setattr(alerting, "alert", lambda key, msg, level="warn", detail=None: seen.append((key, level)))
    res = da.audit(db, full=True, now=NOW)
    assert sorted(calls) == [("heal", "none"), ("pd", "nopd")]
    assert res["gaps"] == {"no_rows": 1, "no_ad": 0, "no_pd": 1} and res["fixed"] == 2 and res["still_broken"] == 0
    assert seen == [("dasha_audit:repaired", "warn")]


def test_audit_alerts_as_an_error_when_a_gap_survives_the_repair(monkeypatch):
    from antar_engine import dasha_heal, alerting
    db = FakeSB({"bad": set()})
    monkeypatch.setattr(dasha_heal, "heal", lambda sb, c: 0)               # repair does nothing
    seen = []
    monkeypatch.setattr(alerting, "alert", lambda key, msg, level="warn", detail=None: seen.append((key, level, detail)))
    res = da.audit(db, full=True, now=NOW)
    assert res["still_broken"] == 1 and seen == [("dasha_audit:unrepaired", "error", "bad")]


def test_repair_off_only_alerts_and_writes_nothing(monkeypatch):
    from antar_engine import dasha_heal, alerting
    db = FakeSB({"bad": set()})
    monkeypatch.setattr(dasha_heal, "heal", lambda sb, c: (_ for _ in ()).throw(AssertionError("must not write")))
    monkeypatch.setattr(alerting, "alert", lambda *a, **k: None)
    assert da.audit(db, full=True, repair=False, now=NOW)["still_broken"] == 1


def test_nightly_pass_only_looks_at_recent_charts_and_clean_db_is_silent(monkeypatch):
    from antar_engine import alerting
    db = FakeSB({"old": set(), "new": FULL}, created={"old": "2026-01-01T00:00:00+00:00", "new": "2026-10-13T00:00:00+00:00"})
    seen = []
    monkeypatch.setattr(alerting, "alert", lambda *a, **k: seen.append(a))
    res = da.audit(db, full=False, repair=False, now=NOW)
    assert res["checked"] == 1 and res["gaps"] == {"no_rows": 0, "no_ad": 0, "no_pd": 0} and seen == []
    assert da.audit(db, full=True, repair=False, now=NOW)["gaps"]["no_rows"] == 1      # Sunday: everything


def test_chart_list_failure_is_reported_not_raised():
    class Boom:
        def table(self, *_): raise RuntimeError("down")
    assert da.audit(Boom(), now=NOW)["ok"] is False
