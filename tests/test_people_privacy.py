"""People/connection privacy guards (compat partner ownership, merge-redirect
cross-user, remove-person purge, account-delete sub-chart purge)."""
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def m():
    import main
    return main


class _Q:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.op, self.filters, self.payload = "select", [], None

    def select(self, *a, **k): return self
    def limit(self, *a): return self
    def eq(self, c, v): self.filters.append(("eq", c, v)); return self
    def in_(self, c, v): self.filters.append(("in", c, list(v))); return self
    def update(self, p): self.op, self.payload = "update", p; return self
    def delete(self): self.op = "delete"; return self

    def _match(self, row):
        for kind, c, v in self.filters:
            if kind == "eq" and row.get(c) != v: return False
            if kind == "in" and row.get(c) not in v: return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        hit = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hit: r.update(self.payload)
            self.db.log.append(("update", self.name, self.payload))
        elif self.op == "delete":
            self.db.tables[self.name] = [r for r in rows if r not in hit]
            self.db.log.append(("delete", self.name, list(self.filters)))
        return type("R", (), {"data": [dict(r) for r in hit]})()


class FakeDB:
    def __init__(self, tables):
        self.tables, self.log = tables, []

    def table(self, name): return _Q(self, name)


CHARTS = [
    {"id": "A", "user_id": "u1", "parent_chart_id": None, "guest_session_id": None, "chart_type": None},
    {"id": "A2", "user_id": "u1", "parent_chart_id": None, "guest_session_id": None, "chart_type": None},
    {"id": "S", "user_id": None, "parent_chart_id": "A", "guest_session_id": None, "chart_type": "compatibility"},
    {"id": "X", "user_id": "u2", "parent_chart_id": None, "guest_session_id": None, "chart_type": None},
    {"id": "XS", "user_id": None, "parent_chart_id": "X", "guest_session_id": None, "chart_type": "compatibility"},
]


def _db(extra=None):
    t = {"charts": [dict(r) for r in CHARTS]}
    t.update(extra or {})
    return FakeDB(t)


def test_compat_partner_ownership(m, monkeypatch):
    monkeypatch.setattr(m, "supabase", _db())
    assert m._compat_partner_allowed("A", "S")        # own People sub-chart
    assert m._compat_partner_allowed("A", "A2")       # same user's other chart
    assert not m._compat_partner_allowed("A", "X")    # stranger's chart
    assert not m._compat_partner_allowed("A", "XS")   # stranger's sub-chart
    assert not m._compat_partner_allowed("A", "nope")


def test_merge_redirect_never_crosses_users(m):
    assert m._redirect_crosses_users({"user_id": "u1"}, {"user_id": "u2"})
    assert m._redirect_crosses_users({"user_id": None, "chart_type": "compatibility"}, {"user_id": "u1"})
    assert not m._redirect_crosses_users({"user_id": "u1"}, {"user_id": "u1"})
    assert not m._redirect_crosses_users({"user_id": None}, {"user_id": "u1"})


def test_remove_person_purges_orphan_subchart(m, monkeypatch):
    db = _db({
        "compatibility_sessions": [{"id": 1, "chart_id_a": "A", "chart_id_b": "S"}],
        "chart_connections": [{"id": 9, "chart_id_a": "A", "chart_id_b": "S"}],
    })
    monkeypatch.setattr(m, "supabase", db)
    monkeypatch.setattr(m, "_purge_prashna_followups", lambda c: None)
    monkeypatch.setattr(m, "_purge_proxy_cache", lambda c: 0)
    monkeypatch.setattr(m, "_delete_rows_by", lambda t, c, v: None)
    out = m.remove_network_person("A", "S")
    assert out["subchart_purged"] is True
    assert db.tables["chart_connections"] == []
    s = [r for r in db.tables["charts"] if r["id"] == "S"][0]
    assert s["deleted_at"] and s["birth_date"] is None and s["name"] is None


def test_remove_person_keeps_subchart_still_referenced(m, monkeypatch):
    db = _db({
        "compatibility_sessions": [{"id": 1, "chart_id_a": "A", "chart_id_b": "S"}],
        "chart_connections": [{"id": 9, "chart_id_a": "A2", "chart_id_b": "S"}],
    })
    monkeypatch.setattr(m, "supabase", db)
    monkeypatch.setattr(m, "_delete_rows_by", lambda t, c, v: None)
    out = m.remove_network_person("A", "S")
    assert out["subchart_purged"] is False
    assert not [r for r in db.tables["charts"] if r["id"] == "S"][0].get("deleted_at")


def test_remove_person_never_purges_a_real_chart(m, monkeypatch):
    db = _db({"compatibility_sessions": [], "chart_connections": []})
    monkeypatch.setattr(m, "supabase", db)
    out = m.remove_network_person("A", "A2")
    assert out["subchart_purged"] is False
    assert not [r for r in db.tables["charts"] if r["id"] == "A2"][0].get("deleted_at")


def test_dedupe_script_excludes_people_subcharts():
    src = open("scripts/dedupe_charts.py").read()
    assert 'chart_type") == "compatibility"' in src
    assert "never merge across different users" in src
    assert "APPLY = " in src and '"--apply" in sys.argv' in src
