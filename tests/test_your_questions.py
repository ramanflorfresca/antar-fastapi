"""Your questions: every dated Ask answer shows up without a 'save' tap."""
from datetime import date

import pytest
from fastapi import HTTPException

from antar_engine import saved_decisions as sd

TODAY = date(2026, 10, 7)


def claim(i, q, ws, we, **kw):
    base = dict(id=f"c{i}", chart_id="ch1", created_at=f"2026-10-0{i}T10:00:00Z", source="ask_explore",
                question=q, verdict="YES_WITH_TIMING", window_start=ws, window_end=we,
                channel="app", language="en")
    base.update(kw)
    return base


def test_dated_claims_become_rows_with_status_and_source():
    rows = sd.claims_to_decisions([
        claim(1, "Is this the right time to change jobs?", "2026-10-01", "2026-12-31", channel="whatsapp"),
        claim(2, "Should I start the business?", "2027-02-01", "2027-05-31"),
        claim(3, "Move cities?", "2026-07-01", "2026-09-30"),
    ], [], today=TODAY)
    by = {r["question"]: r for r in rows}
    assert by["Is this the right time to change jobs?"]["status"] == "open"
    assert by["Should I start the business?"]["status"] == "upcoming"
    assert by["Move cities?"]["status"] == "closed"
    assert by["Is this the right time to change jobs?"]["source"] == "From WhatsApp"
    assert by["Should I start the business?"]["source"] == "From the app"
    assert all(r["id"].startswith("claim:") and r["auto"] for r in rows)


def test_timing_label_has_year_when_not_this_year():
    assert sd.claim_timing_label(date(2026, 10, 14), date(2026, 10, 20), "en", TODAY) == "Oct 14 – Oct 20"
    assert sd.claim_timing_label(date(2026, 11, 1), date(2027, 1, 31), "en", TODAY) == "Nov 2026 – Jan 2027"
    assert sd.claim_timing_label(None, None, "en", TODAY) is None


def test_other_sources_and_undated_claims_are_excluded():
    rows = sd.claims_to_decisions([
        claim(1, "q topic", "2026-10-01", "2026-10-30", source="topic_read"),
        claim(2, "q decoy", "2026-10-01", "2026-10-30", source="decoy"),
        claim(3, "q no window", None, None),
        claim(4, "", "2026-10-01", "2026-10-30"),
        claim(5, "q yesno", "2026-10-01", "2026-10-30", source="ask_yesno"),
    ], [], today=TODAY)
    assert [r["question"] for r in rows] == ["q yesno"]


def test_saved_archived_and_duplicate_questions_do_not_come_back():
    claims = [claim(1, "A?", "2026-10-01", "2026-10-30"), claim(2, "B?", "2026-10-01", "2026-10-30"),
              claim(3, "C?", "2026-10-01", "2026-10-30"), claim(4, "c?", "2026-10-01", "2026-10-30")]
    saved = [{"claim_id": "c1", "question": "A?", "archived_at": None},          # saved via claim
             {"claim_id": "c2", "question": "B?", "archived_at": "2026-10-05"}]  # archived/deleted
    rows = sd.claims_to_decisions(claims, saved, today=TODAY)
    assert [r["question"] for r in rows] == ["c?"]      # newest of C/c, one row per question


def test_live_saved_question_hides_same_question_claim():
    rows = sd.claims_to_decisions([claim(1, "Same?", "2026-10-01", "2026-10-30")],
                                  [{"claim_id": None, "question": "same?", "archived_at": None}], today=TODAY)
    assert rows == []


def test_languages_es_pt_and_fallback():
    r = sd.claims_to_decisions([claim(1, "¿Cambio?", "2026-10-01", "2026-10-30", channel="whatsapp", language="es")], [], today=TODAY)[0]
    assert r["source"] == "Desde WhatsApp" and r["timing_label"] == "1 oct – 30 oct"
    r = sd.claims_to_decisions([claim(1, "Muda?", "2026-10-01", "2026-10-30", language="pt")], [], today=TODAY)[0]
    assert r["source"] == "Pelo app"
    r = sd.claims_to_decisions([claim(1, "Q?", "2026-10-01", "2026-10-30", language="hinglish")], [], today=TODAY)[0]
    assert r["source"] == "From the app"


def test_reversed_window_is_put_in_order():
    r = sd.claims_to_decisions([claim(1, "Close a deal?", "2027-01-15", "2026-11-30")], [], today=TODAY)[0]
    assert r["window_start"] == "2026-11-30" and r["window_end"] == "2027-01-15"
    assert r["timing_label"] == "Nov 2026 – Jan 2027" and r["status"] == "upcoming"


def test_claim_id_roundtrip():
    assert sd.parse_claim_decision_id(sd.claim_decision_id("abc")) == "abc"
    assert sd.parse_claim_decision_id("abc") is None and sd.parse_claim_decision_id("claim:") is None


# ── endpoints ──────────────────────────────────────────────────────

class _Res:
    def __init__(self, data): self.data = data


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.f, self.op, self.payload = db, name, [], "select", None
    def select(self, *a, **k): return self
    def insert(self, p): self.op, self.payload = "insert", p; return self
    def update(self, p): self.op, self.payload = "update", p; return self
    def eq(self, k, v): self.f.append(lambda r, k=k, v=v: r.get(k) == v); return self
    def in_(self, k, vs): self.f.append(lambda r, k=k, vs=vs: r.get(k) in vs); return self
    def is_(self, k, v): self.f.append(lambda r, k=k: r.get(k) is None); return self
    def order(self, *a, **k): return self
    def limit(self, n): return self
    def execute(self):
        rows = self.db[self.name]
        if self.op == "insert":
            row = dict(self.payload); row.setdefault("id", f"s{len(rows)+1}"); rows.append(row)
            return _Res([row])
        hit = [r for r in rows if all(f(r) for f in self.f)]
        if self.op == "update":
            for r in hit: r.update(self.payload)
        return _Res([dict(r) for r in hit])


class _DB:
    def __init__(self, claims, saved=None):
        self.t = {"prediction_claims": claims, "saved_decisions": saved or [], "charts": [{"id": "ch1", "user_id": "u1"}]}
    def table(self, n): return _Q(self.t, n)


@pytest.fixture
def api(monkeypatch):
    import main
    def setup(claims, saved=None):
        db = _DB(claims, saved)
        monkeypatch.setattr(main, "supabase", db)
        monkeypatch.setattr(main, "verify_token", lambda a: "u1")
        monkeypatch.setattr(main, "_oc_owned_chart", lambda u, c: u == "u1" and c == "ch1")
        monkeypatch.setattr(main, "_decisions_is_demo", lambda c: False)
        return main, db
    return setup


def test_list_includes_auto_questions(api):
    main, _ = api([claim(1, "Q one?", "2026-10-01", "2026-12-31", channel="whatsapp")])
    out = main.decisions_list("ch1", authorization="Bearer x")
    assert out["count"] == 1 and out["decisions"][0]["id"] == "claim:c1"
    assert out["decisions"][0]["source"] == "From WhatsApp"


def test_list_fails_open_when_claims_table_errors(api, monkeypatch):
    main, db = api([claim(1, "Q?", "2026-10-01", "2026-12-31")], saved=[
        {"id": "s1", "chart_id": "ch1", "question": "Saved?", "window_start": "2026-10-01",
         "window_end": "2026-12-31", "archived_at": None, "created_at": "2026-10-06T00:00:00Z"}])
    orig = db.table
    def boom(n):
        if n == "prediction_claims": raise RuntimeError("table missing")
        return orig(n)
    monkeypatch.setattr(db, "table", boom)
    out = main.decisions_list("ch1", authorization="Bearer x")
    assert [d["question"] for d in out["decisions"]] == ["Saved?"]


def test_delete_auto_row_hides_it_and_keeps_the_claim(api):
    main, db = api([claim(1, "Hide me?", "2026-10-01", "2026-12-31")])
    out = main.decisions_delete("claim:c1", authorization="Bearer x")
    assert out["deleted"] is True
    assert len(db.t["prediction_claims"]) == 1                    # accuracy record untouched
    saved = db.t["saved_decisions"][0]
    assert saved["claim_id"] == "c1" and saved["archived_at"] and saved["open_reminder_due_at"] is None
    assert main.decisions_list("ch1", authorization="Bearer x")["count"] == 0   # stays hidden


def test_patch_note_on_auto_row_makes_it_a_saved_row_without_a_reminder(api):
    main, db = api([claim(1, "Note me?", "2026-10-01", "2026-12-31")])
    main.decisions_update("claim:c1", main._DecisionPatch(note="  watch this  "), authorization="Bearer x")
    saved = db.t["saved_decisions"][0]
    assert saved["note"] == "watch this" and saved.get("archived_at") is None and saved["open_reminder_due_at"] is None
    out = main.decisions_list("ch1", authorization="Bearer x")
    assert out["count"] == 1 and out["decisions"][0]["note"] == "watch this" and not out["decisions"][0].get("auto")


def test_auto_row_actions_need_ownership_and_a_real_claim(api, monkeypatch):
    main, db = api([claim(1, "Q?", "2026-10-01", "2026-12-31")])
    with pytest.raises(HTTPException) as e:
        main.decisions_delete("claim:nope", authorization="Bearer x")
    assert e.value.status_code == 404
    monkeypatch.setattr(main, "_oc_owned_chart", lambda u, c: False)
    with pytest.raises(HTTPException) as e:
        main.decisions_delete("claim:c1", authorization="Bearer x")
    assert e.value.status_code == 404 and db.t["saved_decisions"] == []


# ── topic on every row (additive; drives the FE icon) ──────────────

def _saved(i, q, **kw):
    base = dict(id=f"s{i}", chart_id="ch1", question=q, window_start="2026-10-01", window_end="2026-12-31",
                archived_at=None, created_at=f"2026-10-0{i}T00:00:00Z", claim_id=None)
    base.update(kw)
    return base


def test_ask_claims_map_their_stored_concern_to_a_topic():
    rows = sd.claims_to_decisions([
        claim(1, "Raise?", "2026-10-01", "2026-12-31", topic="finance"),
        claim(2, "Marry?", "2026-10-01", "2026-12-31", topic="marriage"),
        claim(3, "Promotion?", "2026-10-01", "2026-12-31", topic="career"),
        claim(4, "Surgery?", "2026-10-01", "2026-12-31", topic="health"),
        claim(5, "Gamble?", "2026-10-01", "2026-12-31", topic="speculation"),
        claim(6, "Other?", "2026-10-01", "2026-12-31", topic="general"),
        claim(7, "No topic?", "2026-10-01", "2026-12-31"),
    ], [], today=TODAY)
    by = {r["question"]: r["topic"] for r in rows}
    assert by == {"Raise?": "money", "Marry?": "love", "Promotion?": "career", "Surgery?": "health",
                  "Gamble?": None, "Other?": None, "No topic?": None}


def test_topic_read_claim_topic_is_used_directly_by_a_saved_row():
    rows = [_saved(1, "whatever", claim_id="t1")]
    sd.attach_topics(rows, [{"id": "t1", "source": "topic_read", "topic": "business"}])
    assert rows[0]["topic"] == "business"


@pytest.mark.parametrize("q,topic", [
    ("Should I ask for a promotion at my job?", "career"),
    ("¿Me va bien con el matrimonio este año?", "love"),
    ("Como vai ficar minha renda este ano?", "money"),
    ("Meri shaadi kab hogi?", "love"),
    ("¿Cómo estará mi salud?", "health"),
    ("Cuándo abrir mi negocio?", "business"),
])
def test_manual_row_question_text_is_classified_across_languages(q, topic):
    rows = [_saved(1, q)]
    sd.attach_topics(rows, [])
    assert rows[0]["topic"] == topic


def test_unknown_question_is_null():
    rows = [_saved(1, "hello there")]
    sd.attach_topics(rows, [])
    assert rows[0]["topic"] is None


def test_linked_claim_wins_even_when_its_topic_is_unmappable():
    rows = [_saved(1, "Should I ask for a promotion at my job?", claim_id="c1")]
    sd.attach_topics(rows, [{"id": "c1", "topic": "general"}])
    assert rows[0]["topic"] is None


def test_list_rows_all_carry_topic_and_materialized_row_keeps_it(api):
    main, db = api([claim(1, "Raise?", "2026-10-01", "2026-12-31", topic="finance"),
                    claim(2, "Plain?", "2026-10-01", "2026-12-31", topic="general")],
                   saved=[_saved(3, "x", claim_id="t9")])
    db.t["prediction_claims"].append({"id": "t9", "chart_id": "ch1", "source": "topic_read", "topic": "peace"})
    out = main.decisions_list("ch1", authorization="Bearer x")
    by = {d["id"]: d["topic"] for d in out["decisions"]}
    assert by == {"claim:c1": "money", "claim:c2": None, "s3": "peace"}
    main.decisions_update("claim:c1", main._DecisionPatch(note="n"), authorization="Bearer x")
    out = main.decisions_list("ch1", authorization="Bearer x")
    by = {d["id"]: d["topic"] for d in out["decisions"]}
    assert out["count"] == 3 and by["claim:c2"] is None
    mat = [d for d in out["decisions"] if d.get("claim_id") == "c1"]
    assert len(mat) == 1 and mat[0]["topic"] == "money"
