"""A birth edit must rebuild dashas / jaimini / lal kitab / yogas from the NEW chart
and purge stale caches — not leave them describing the old birth."""
import os
os.environ.setdefault("SUPABASE_URL", "http://localhost:1")
os.environ.setdefault("SUPABASE_KEY", "k")

import main
from antar_engine import chart as chart_mod


class _Rec:
    def __init__(self):
        self.ops = []

    def table(self, name):
        rec = self
        class Q:
            def __init__(s): s.n, s.op, s.payload = name, None, None
            def delete(s): s.op = "delete"; return s
            def insert(s, p): s.op, s.payload = "insert", p; return s
            def update(s, p): s.op, s.payload = "update", p; return s
            def eq(s, *a): return s
            def execute(s): rec.ops.append((s.n, s.op, s.payload)); return type("R", (), {"data": []})()
        return Q()


def test_rederive_rebuilds_every_layer(monkeypatch):
    rec = _Rec()
    monkeypatch.setattr(main, "supabase", rec)
    cd = chart_mod.calculate_chart(birth_date="1990-05-17", birth_time="06:30",
                                   lat=28.61, lng=77.21, tz_offset=5.5, ayanamsa="lahiri")
    st = main._rederive_after_birth_edit("c" * 8 + "-0000-0000-0000-000000000000", cd, "1990-05-17")
    assert st["dashas"] == "ok" and st["jaimini"] == "ok" and st["lal_kitab"] == "ok", st
    purged = {n for n, op, _ in rec.ops if op == "delete"}
    assert {"dasha_periods", "daily_surface_cache", "chart_yogas"} <= purged
    # user content must survive a birth edit
    assert not purged & {"predictions", "user_predictions", "chat_messages", "conversations"}
    inserted = [p for n, op, p in rec.ops if n == "dasha_periods" and op == "insert"]
    systems = {r["system"] for batch in inserted for r in batch}
    assert {"vimsottari", "jaimini", "ashtottari"} <= systems
    # ordering: purge happens before the re-insert (else we'd delete the new rows)
    first_ins = next(i for i, o in enumerate(rec.ops) if o[:2] == ("dasha_periods", "insert"))
    last_del = max(i for i, o in enumerate(rec.ops) if o[:2] == ("dasha_periods", "delete"))
    assert last_del < first_ins
    lk = [p for n, op, p in rec.ops if n == "charts" and op == "update" and p and "lal_kitab_data" in p][0]
    assert lk["lal_kitab_data"]["birth_date"] == "1990-05-17"
    assert lk["lal_kitab_data"]["lagna_sign"] == cd["lagna"]["sign"]
