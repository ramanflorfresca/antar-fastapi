"""[daily-loop 2026-10-12] The 3-step loop: step rules, once-only streak count, question pick, fail-open."""
import uuid
from datetime import date, timedelta

import pytest

from antar_engine import daily_loop as DL


class _Res:
    def __init__(self, data, count=None):
        self.data, self.count = data, count


class _Q:
    def __init__(self, sb, name):
        self.sb, self.name, self.f, self.op, self.payload, self.cnt = sb, name, [], "select", None, False

    def select(self, *a, **k):
        self.cnt = k.get("count") == "exact"
        return self

    def eq(self, c, v): self.f.append(("eq", c, v)); return self
    def gte(self, c, v): self.f.append(("gte", c, v)); return self
    def lt(self, c, v): self.f.append(("lt", c, v)); return self
    def order(self, *a, **k): return self
    def limit(self, n): return self

    @property
    def not_(self): return self
    def is_(self, c, v): return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, row):
        self.op, self.payload = "update", row
        return self

    def _match(self, r):
        for kind, c, v in self.f:
            x = r.get(c)
            if kind == "eq" and str(x) != str(v): return False
            if kind == "gte" and not (x is not None and str(x) >= str(v)): return False
            if kind == "lt" and not (x is not None and str(x) < str(v)): return False
        return True

    def execute(self):
        if self.sb.broken:
            raise RuntimeError("relation does not exist")
        rows = self.sb.tables.setdefault(self.name, [])
        if self.op == "insert":
            r = {"id": str(uuid.uuid4()), **self.payload}
            rows.append(r)
            return _Res([r])
        if self.op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                r.update(self.payload)
            return _Res(hit)
        hit = [dict(r) for r in rows if self._match(r)]
        return _Res(hit, count=len(hit) if self.cnt else None)


class FakeSB:
    def __init__(self, broken=False):
        self.tables, self.broken = {}, broken

    def table(self, name):
        return _Q(self, name)


@pytest.fixture
def touches(monkeypatch):
    calls = []
    from antar_engine import gamification as G
    monkeypatch.setattr(G, "touch", lambda sb, cid, tz=0, uid=None: (calls.append(cid) or
                        {"ok": True, "streak": 7, "changed": True, "awards": [{"kind": "ask", "amount": 3}]}))
    return calls


def test_practice_needs_eleven_repeats():
    sb = FakeSB()
    r = DL.record_step(sb, "c1", "practice", 0, mantra_count=10)
    assert r["steps"]["practice"] is False and r["mantra_count"] == 10
    r = DL.record_step(sb, "c1", "practice", 0, mantra_count=11)
    assert r["steps"]["practice"] is True
    # the count never goes down
    r = DL.record_step(sb, "c1", "practice", 0, mantra_count=3)
    assert r["mantra_count"] == 11


def test_other_practice_counts_on_completion():
    r = DL.record_step(FakeSB(), "c1", "practice", 0, other_practice=True)
    assert r["steps"]["practice"] is True


def test_runaway_count_is_capped():
    r = DL.record_step(FakeSB(), "c1", "practice", 0, mantra_count=10 ** 9)
    assert r["mantra_count"] == DL.MANTRA_MAX


def test_streak_counted_once_when_all_three_done(touches):
    sb = FakeSB()
    assert DL.record_step(sb, "c1", "read", 0)["just_completed"] is False
    assert DL.record_step(sb, "c1", "ask", 0)["just_completed"] is False
    assert touches == []
    r = DL.record_step(sb, "c1", "practice", 0, mantra_count=11)
    assert r["complete"] and r["just_completed"] and touches == ["c1"]
    assert r["awards"] and r["awards"][0]["kind"] == "ask"
    # repeating any step never counts the day twice
    again = DL.record_step(sb, "c1", "practice", 0, mantra_count=108)
    assert again["just_completed"] is False and touches == ["c1"]
    assert DL.record_step(sb, "c1", "read", 0)["just_completed"] is False


def test_steps_are_idempotent_and_bad_step_rejected():
    sb = FakeSB()
    DL.record_step(sb, "c1", "read", 0)
    DL.record_step(sb, "c1", "read", 0)
    assert len(sb.tables[DL.TABLE]) == 1
    assert DL.record_step(sb, "c1", "dance", 0)["ok"] is False


def test_local_day_follows_tz_offset():
    from datetime import datetime, timezone, timedelta
    far = DL.local_date(14 * 60)
    near = DL.local_date(-12 * 60)
    assert (far - near).days in (0, 1)
    assert DL.local_date(0) == datetime.now(timezone.utc).date()


def test_fails_open_when_table_missing(touches):
    sb = FakeSB(broken=True)
    r = DL.record_step(sb, "c1", "practice", 0, mantra_count=50)
    assert r["ok"] is False and r["just_completed"] is False and touches == []
    assert DL.totals(sb, "c1") == {"mantra_repeats": 0, "practice_days": 0, "questions_asked": 0}
    assert DL.get_row(sb, "c1", date.today()) is None


CANDS = [
    {"id": "q1", "topic": "money", "text": "Is now the time to raise my prices?", "reason": "Your money window is open."},
    {"id": "q2", "topic": "career", "text": "Is November good for my ask at work?", "reason": "A work window opens."},
    {"id": "q3", "topic": "love", "text": "Is the spring good for a talk?", "reason": "Care window."},
]


def test_pick_is_deterministic_and_offers_next_topic():
    a = DL.pick_question(CANDS, [], date(2026, 10, 12))
    b = DL.pick_question(CANDS, [], date(2026, 10, 12))
    assert a == b and a["id"] == "q1" and a["next_topic"] == "career"


def test_pick_skips_recent_text_and_yesterdays_theme():
    t = date(2026, 10, 12)
    recent = [{"local_date": (t - timedelta(days=1)).isoformat(), "question_text": CANDS[0]["text"],
               "question_theme": "money"}]
    q = DL.pick_question(CANDS, recent, t)
    assert q["id"] == "q2"
    # everything used recently: still returns something, never nothing
    allused = [{"local_date": (t - timedelta(days=i + 2)).isoformat(), "question_text": c["text"],
                "question_theme": c["topic"]} for i, c in enumerate(CANDS)]
    assert DL.pick_question(CANDS, allused, t) is not None
    assert DL.pick_question([], [], t) is None


def test_question_is_stable_all_day():
    sb = FakeSB()
    t = DL.local_date(0)
    first = DL.ensure_question(sb, "c1", t, CANDS)
    # the ranking changes later in the day; the stored question does not
    second = DL.ensure_question(sb, "c1", t, list(reversed(CANDS)))
    assert first["text"] == second["text"]
    assert second["reason"] is None or isinstance(second["reason"], str)


def test_totals_count_loop_and_practice_days():
    sb = FakeSB()
    DL.record_step(sb, "c1", "practice", 0, mantra_count=40)
    sb.tables.setdefault("practice_log", []).append({"chart_id": "c1", "completed_at": "2026-01-02T10:00:00"})
    t = DL.totals(sb, "c1")
    assert t["mantra_repeats"] == 40 and t["practice_days"] == 2


def test_routes_and_flag_are_wired():
    import main
    paths = {(r.path, tuple(sorted(getattr(r, "methods", []) or []))) for r in main.app.routes}
    assert ("/api/v1/daily-loop/{chart_id}", ("GET",)) in paths
    assert ("/api/v1/daily-loop/{chart_id}/step", ("POST",)) in paths
    from antar_engine import app_config
    assert "loop_streak" in app_config.ALLOWED_KEYS
    assert app_config.ALLOWED_KEYS["loop_streak"]["default"] == "off"   # dark until the app ships the loop


def test_unlock_ladder():
    assert DL.unlock_for(7)["id"] == "hidden_strength"
    assert DL.unlock_for(8) is None
    lst = DL.unlock_list(21)
    assert [u["unlocked"] for u in lst] == [True, True, False, False]


def test_carry_over_once_for_a_fresh_login_streak(monkeypatch):
    from antar_engine import gamification as G
    sb = FakeSB()
    t = DL.local_date(0)
    sb.tables["user_streaks"] = [{"user_id": "u1", "current_streak": 12,
                                  "last_active_date": (t - timedelta(days=2)).isoformat()}]
    monkeypatch.setattr(G, "_uid", lambda sb_, cid: "u1")
    assert DL.carry_over(sb, "c1", t) is True
    assert sb.tables["user_streaks"][0]["last_active_date"] == (t - timedelta(days=1)).isoformat()
    # once only: after a completed loop exists, never again
    sb.tables[DL.TABLE] = [{"chart_id": "c1", "local_date": (t - timedelta(days=1)).isoformat(),
                            "completed_at": "2026-10-11T10:00:00"}]
    sb.tables["user_streaks"][0]["last_active_date"] = (t - timedelta(days=3)).isoformat()
    assert DL.carry_over(sb, "c1", t) is False


def test_carry_over_skips_stale_or_empty_streaks(monkeypatch):
    from antar_engine import gamification as G
    monkeypatch.setattr(G, "_uid", lambda sb_, cid: "u1")
    t = DL.local_date(0)
    sb = FakeSB()
    sb.tables["user_streaks"] = [{"user_id": "u1", "current_streak": 12,
                                  "last_active_date": (t - timedelta(days=10)).isoformat()}]
    assert DL.carry_over(sb, "c1", t) is False          # too old: it already lapsed
    sb2 = FakeSB()
    sb2.tables["user_streaks"] = [{"user_id": "u1", "current_streak": 0, "last_active_date": t.isoformat()}]
    assert DL.carry_over(sb2, "c1", t) is False


def test_rituals_completions_feed_the_loop_practice_step(monkeypatch):
    import main
    seen = []
    monkeypatch.setattr(DL, "record_step", lambda sb, cid, step, tz=0, **kw: seen.append((cid, step, tz, kw)) or {})
    main._loop_mark_practice("c1", 330, other_practice=True)
    main._loop_mark_practice("c1", None, mantra_count=108)
    assert seen[0] == ("c1", "practice", 330, {"mantra_count": None, "other_practice": True})
    assert seen[1][3] == {"mantra_count": 108, "other_practice": False} and seen[1][2] == 0


def test_loop_hook_never_raises(monkeypatch):
    import main
    monkeypatch.setattr(DL, "record_step", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    main._loop_mark_practice("c1", 0, other_practice=True)      # must not raise


def test_next_milestone_carries_days_and_credits_for_the_app():
    from antar_engine import gamification as G
    nm = G.next_milestone(6)
    assert nm["at"] == 7 and nm["in_days"] == 1 and nm["ask"] == 3


def test_stored_question_keeps_a_why_line_after_the_ranking_moves():
    sb = FakeSB()
    t = DL.local_date(0)
    DL.ensure_question(sb, "c1", t, CANDS)
    # later in the day the original question is no longer ranked; another money candidate still explains the topic
    later = [{"id": "z", "topic": "money", "text": "Something else about money?", "reason": "Timing is worth checking for money."}]
    q = DL.ensure_question(sb, "c1", t, later)
    assert q["text"] == CANDS[0]["text"] and q["reason"] == "Timing is worth checking for money."
    assert DL.ensure_question(sb, "c1", t, [])["reason"] is None       # nothing to say: none, never invented
