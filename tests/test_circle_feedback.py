"""One-tap 'does this fit?': call | me | reading, yes / partly / no, through the existing outcome loop."""
import json
import re
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from circle_fakedb import DB  # noqa: E402
from test_circle_routes import AUTH, env, make_pair  # noqa: E402,F401
from test_circle import A, B, X  # noqa: E402,F401

from antar_engine import accuracy_board as ab
from antar_engine import circle_feedback as FB
from antar_engine import topic_checkback as tcb

TODAY = date(2026, 10, 8)
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
LANGS = ("en", "es", "pt", "hinglish")
READING = {"score": 58, "headline": "Two builders who pull in different directions.", "brief": {
    "lens": "cofounder", "family": "work_partner", "verdict": {"key": "partners_with_lanes"}, "fit": {"badge": "MIXED"},
    "phase": {"status": "both_heavy", "call": "not_now", "call_title": "Not now", "line": "Not now. You are both in clouded stretches."},
    "people": [{"first_name": "Raman", "role": "driver", "temperament": {"trait": "Caring and protective."},
                "season": {"label": "A long chapter of ambition.", "tone": "clouded", "position": "first"},
                "partnership": {"lean": "either"}, "bond": None}, {"first_name": "Andres"}]}}
NO_BRIEF = {"score": 50, "headline": "h"}


def test_items_depend_on_what_the_reading_has():
    assert FB.available_items(READING) == ("call", "me", "reading")
    assert FB.available_items(NO_BRIEF) == ("reading",)
    assert FB.available_items(None) == ("reading",)


def test_snapshot_and_shown_text_carry_no_names_or_birth_data():
    snap = FB.snapshot("me", READING)
    assert snap == {"item": "me", "lens": "cofounder", "family": "work_partner", "verdict": "partners_with_lanes", "call": "not_now",
                    "phase": "both_heavy", "fit_badge": "MIXED", "score": 58, "me_tone": "clouded", "me_position": "first",
                    "me_bond": "either", "me_role": "driver"}
    blob = json.dumps(snap)
    assert "Raman" not in blob and "Andres" not in blob
    assert FB.shown_text("call", READING).startswith("Not now. Not now. You are both")
    assert "Caring and protective." in FB.shown_text("me", READING) and FB.shown_text("reading", READING).startswith("Two builders")


def test_prompt_copy_is_four_languages_and_plain():
    for lang in LANGS:
        for item in FB.ITEMS:
            p = FB.prompt(item, READING, lang)
            assert p["question"] and [o["value"] for o in p["options"]] == ["yes", "partly", "no"] and all(o["label"] for o in p["options"])
            assert not re.search(r"\b(dasha|lagna|rahu|saturn|house|lord|nakshatra)\b", json.dumps(p), re.I)
        assert FB.thanks(lang)
    assert FB.prompt("me", READING, "hi")["question"] == "Does the card about you fit?"            # Hindi falls back to English
    assert FB.prompt("call", READING, "es")["question"].startswith("¿La conclusión")


def test_the_next_item_walks_call_me_reading_then_stops():
    db = DB()
    seen = []
    for ans in ("yes", "partly", "no"):
        item = FB.next_item(db, A, "P1", READING, TODAY)
        seen.append(item)
        assert FB.record(db, A, "P1", item, ans, READING, "en", TODAY, NOW)["saved"] is True
    assert seen == ["call", "me", "reading"] and FB.next_item(db, A, "P1", READING, TODAY) is None
    assert FB.next_item(db, B, "P1", READING, TODAY) == "call"                                       # the other person is asked separately
    assert FB.next_item(db, A, "P2", READING, TODAY) == "call"                                       # another pair is separate


def test_claim_rows_use_the_outcome_loop_and_a_repeat_keeps_the_first_answer():
    db = DB()
    assert FB.record(db, A, "P1", "me", "no", READING, "es", TODAY, NOW) == {"saved": True, "already_answered": False, "outcome": "no"}
    again = FB.record(db, A, "P1", "me", "yes", READING, "es", TODAY, NOW)
    assert again == {"saved": False, "already_answered": True, "outcome": "no"}                     # first answer stands
    claim = db.rows("prediction_claims")[0]
    assert (claim["source"], claim["topic"], claim["claim_type"], claim["chart_id"], claim["language"]) == ("circle_fit", "cofounder", "fit", A, "es")
    assert claim["engines"]["circle_fit"]["item"] == "me" and claim["dedupe_key"].startswith(f"{A}|P1|circle_fit:me|")
    assert len(db.rows("prediction_claims")) == 1 and [o["outcome"] for o in db.rows("prediction_outcomes")] == ["no"]


def test_a_new_period_asks_again_and_bad_input_is_refused():
    db = DB()
    FB.record(db, A, "P1", "call", "yes", READING, "en", TODAY, NOW)
    later = date.fromordinal(TODAY.toordinal() + FB.BUCKET_DAYS + 1)
    assert FB.next_item(db, A, "P1", READING, later) == "call"
    assert FB.record(db, A, "P1", "call", "no", READING, "en", later, NOW)["saved"] is True
    for item, ans, code in (("zzz", "yes", "bad_item"), ("call", "maybe", "bad_answer"), ("call", "not_sure", "bad_answer")):
        with pytest.raises(FB.FeedbackError) as e:
            FB.record(db, A, "P1", item, ans, READING, "en", TODAY, NOW)
        assert e.value.code == code and e.value.status == 422


def test_fails_open_without_the_tables():
    db = DB(missing=True)
    assert FB.next_item(db, A, "P1", READING, TODAY) is None
    with pytest.raises(FB.FeedbackError) as e:
        FB.record(db, A, "P1", "call", "yes", READING, "en", TODAY, NOW)
    assert e.value.status == 503


def test_the_board_scores_each_item_per_lens_and_suppresses_small_n():
    def claim(i, item, lens="cofounder"):
        return {"id": f"f{i}", "chart_id": f"c{i}", "source": "circle_fit", "topic": lens, "window_end": "2026-10-08",
                "engines": {"circle_fit": {"item": item, "lens": lens}}}
    claims = [claim(1, "call"), claim(2, "call"), claim(3, "me"), claim(4, "reading", "friend")]
    outs = [{"claim_id": "f1", "outcome": "yes", "answered_at": "2026-10-08"}, {"claim_id": "f2", "outcome": "no", "answered_at": "2026-10-08"},
            {"claim_id": "f3", "outcome": "partly", "answered_at": "2026-10-08"}]
    b = ab.build(claims, outs)
    rows = {(r["engine"], r["topic"]): r for r in b["engines"]}
    assert set(rows) == {("circle_fit:call", "cofounder"), ("circle_fit:me", "cofounder"), ("circle_fit:reading", "friend")}
    assert rows[("circle_fit:call", "cofounder")]["answered"] == 2 and rows[("circle_fit:call", "cofounder")]["small_n"] is True
    assert rows[("circle_fit:call", "cofounder")]["hit_rate"] is None and rows[("circle_fit:reading", "friend")]["claims"] == 1
    assert any(r["source"] == "circle_fit" for r in b["final_answers"])


def test_feedback_is_never_asked_as_a_window_checkback():
    db = DB()
    FB.record(db, A, "P1", "call", "yes", READING, "en", TODAY, NOW)
    assert tcb.due_items(db, A, "en", now=datetime(2027, 1, 1, tzinfo=timezone.utc), limit=3) == []
    cid = db.rows("prediction_claims")[0]["id"]
    with pytest.raises(tcb.UnknownCheckback):
        tcb.record_answer(db, A, cid, "no", datetime(2027, 1, 1, tzinfo=timezone.utc))


# ── HTTP ─────────────────────────────────────────────────────────────────────
STUB = {"score": 58, "badge": "MIXED", "headline": "Two builders.", "summary": "s", "watch_points": [], "catalysts": [], "confidence": None,
        "timing": None, "layers": [{"key": "communication", "label": "C", "score": 23, "status": "friction", "status_label": "Friction",
                                    "headline": "h", "detail": "d"}]}


def wire(c, db, main, monkeypatch, relation="cofounder", on=True):
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(STUB))
    monkeypatch.setattr(main, "_circle_brief_compute", lambda *a: json.loads(json.dumps(READING["brief"])))
    make_pair(c, db, relation=relation)
    if on:
        for me, other, who in ((A, B, "uA"), (B, A, "uB")):
            c.put(f"/api/v1/circle/{me}/sharing/{other}", json={"share_reading": True}, headers=AUTH[who])


def fb(c, me, other, who, method="get", **kw):
    return getattr(c, method)(f"/api/v1/circle/{me}/pair/{other}/feedback", headers=AUTH[who], **kw)


def test_http_one_question_at_a_time_then_done(env, monkeypatch):
    c, db, main = env
    wire(c, db, main, monkeypatch)
    q = fb(c, A, B, "uA").json()
    assert q["item"] == "call" and q["question"] and [o["value"] for o in q["options"]] == ["yes", "partly", "no"] and q["context"].startswith("Not now")
    r = fb(c, A, B, "uA", "post", json={"item": "call", "answer": "yes"}).json()
    assert r["saved"] is True and r["outcome"] == "yes" and r["thanks"] and r["next"]["item"] == "me"
    assert fb(c, A, B, "uA", "post", json={"item": "call", "answer": "no"}).json() == dict(
        saved=False, already_answered=True, outcome="yes", thanks=r["thanks"], next={**r["next"]})
    fb(c, A, B, "uA", "post", json={"item": "me", "answer": "partly"})
    last = fb(c, A, B, "uA", "post", json={"item": "reading", "answer": "no"}).json()
    assert last["saved"] is True and last["next"] is None and fb(c, A, B, "uA").json() == {"item": None}
    assert fb(c, B, A, "uB").json()["item"] == "call"                              # Andres' own questions are untouched
    assert {x["source"] for x in db.rows("prediction_claims")} == {"circle_fit"} and len(db.rows("prediction_outcomes")) == 3


def test_http_nothing_is_asked_unless_the_reading_is_on(env, monkeypatch):
    c, db, main = env
    wire(c, db, main, monkeypatch, on=False)
    assert fb(c, A, B, "uA").json() == {"item": None}
    r = fb(c, A, B, "uA", "post", json={"item": "call", "answer": "yes"})
    assert r.status_code == 409 and r.json()["detail"]["error"] == "not_on"
    c.put(f"/api/v1/circle/{A}/sharing/{B}", json={"share_reading": True}, headers=AUTH["uA"])          # only one side on: still nothing
    assert fb(c, A, B, "uA").json() == {"item": None} and db.rows("prediction_claims") == []


def test_http_auth_validation_and_non_venture_lenses(env, monkeypatch):
    c, db, main = env
    wire(c, db, main, monkeypatch, relation="friend")
    assert c.get(f"/api/v1/circle/{A}/pair/{B}/feedback").status_code == 401
    assert fb(c, A, B, "uB").status_code == 403
    assert fb(c, A, B, "uA", "post", json={"item": "zzz", "answer": "yes"}).status_code == 422
    assert fb(c, A, B, "uA", "post", json={"item": "call", "answer": "maybe"}).status_code == 422
    assert fb(c, A, B, "uA").json()["item"] == "call"
    assert c.get(f"/api/v1/circle/{A}/pair/{X}/feedback", headers=AUTH["uA"]).status_code == 404       # no pair


def test_http_a_reading_without_a_brief_still_asks_the_overall_question(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(STUB))
    monkeypatch.setattr(main, "_circle_brief_compute", lambda *a: None)
    make_pair(c, db, relation="friend")
    for me, other, who in ((A, B, "uA"), (B, A, "uB")):
        c.put(f"/api/v1/circle/{me}/sharing/{other}", json={"share_reading": True}, headers=AUTH[who])
    assert fb(c, A, B, "uA").json()["item"] == "reading"


def test_http_fails_open_when_the_claim_tables_are_missing(env, monkeypatch):
    c, db, main = env
    wire(c, db, main, monkeypatch)
    db.missing = {"prediction_claims", "prediction_outcomes"}
    assert fb(c, A, B, "uA").json() == {"item": None}
    assert fb(c, A, B, "uA", "post", json={"item": "call", "answer": "yes"}).status_code == 503
