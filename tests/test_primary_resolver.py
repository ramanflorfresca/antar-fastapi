"""_resolve_primary_chart_id: profile by user_id, else the OLDEST live chart
(live 2026-10-03: it looked profiles up by id, never matched, and linked
WhatsApp to the newest — a nameless duplicate — chart)."""
from dotenv import load_dotenv
load_dotenv()
import main


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.f, self.order_desc = db, name, [], None
    def select(self, *a): return self
    def eq(self, k, v): self.f.append((k, v)); return self
    def is_(self, k, v): self.f.append((k, None)); return self
    def order(self, k, desc=False): self.order_desc = desc; return self
    def limit(self, n): return self
    def execute(self):
        rows = [r for r in self.db[self.name] if all(r.get(k) == v for k, v in self.f)]
        if self.order_desc is not None:
            rows.sort(key=lambda r: r["created_at"], reverse=self.order_desc)
        return type("R", (), {"data": rows[:1]})()


def _db(primary):
    return {"profiles": [{"id": "p-1", "user_id": "u1", "primary_chart_id": primary}],
            "charts": [{"id": "leena", "user_id": "u1", "created_at": "2026-04-08", "deleted_at": None},
                       {"id": "dup", "user_id": "u1", "created_at": "2026-09-17", "deleted_at": None}]}


def test_uses_the_profile_primary_looked_up_by_user_id(monkeypatch):
    db = _db("leena")
    monkeypatch.setattr(main.supabase, "table", lambda n: _Q(db, n))
    assert main._resolve_primary_chart_id("u1") == "leena"


def test_falls_back_to_the_oldest_chart_not_the_newest(monkeypatch):
    db = _db(None)
    monkeypatch.setattr(main.supabase, "table", lambda n: _Q(db, n))
    assert main._resolve_primary_chart_id("u1") == "leena"


def test_a_deleted_primary_is_not_returned(monkeypatch):
    db = _db("gone")
    monkeypatch.setattr(main.supabase, "table", lambda n: _Q(db, n))
    assert main._resolve_primary_chart_id("u1") == "leena"
