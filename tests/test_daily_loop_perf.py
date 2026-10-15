import time
from datetime import date

import pytest

import main
from antar_engine import daily_loop as dl


@pytest.fixture()
def stubs(monkeypatch):
    state = {"row": {}, "sq_delay": 0.0, "sq_calls": 0, "saved": []}

    def _sq(chart_id, language, tz, limit):
        state["sq_calls"] += 1
        time.sleep(state["sq_delay"])
        return {"questions": [{"id": "q1", "topic": "money", "text": "Should I raise my prices?", "reason": "Money is active."}]}

    monkeypatch.setattr(main, "_suggested_questions_compute", _sq)
    monkeypatch.setattr(dl, "get_row", lambda sb, c, d: dict(state["row"]) if state["row"] else None)
    monkeypatch.setattr(dl, "recent_rows", lambda sb, c, d, days=14: [])
    monkeypatch.setattr(dl, "_save_row", lambda sb, c, d, f: state["saved"].append(f) or {**state["row"], **f})
    monkeypatch.setattr(dl, "totals", lambda sb, c: {"mantra_repeats": 0, "practice_days": 0, "questions_asked": 0})
    monkeypatch.setattr(main, "get_daily_wisdom", lambda c, l: {"mantra": {"name": "Om", "transliteration": "Om", "use": "x", "why": "y"}})
    monkeypatch.setattr(main._gam if hasattr(main, "_gam") else __import__("antar_engine.gamification", fromlist=["x"]), "state",
                        lambda sb, c, tz: {"current_streak": 3, "longest_streak": 8, "next_milestone": None}, raising=False)
    monkeypatch.setattr(main, "_ac_loop_on", lambda: True)
    return state


def test_a_stored_question_is_not_held_up_by_a_slow_ranking(stubs):
    stubs["row"] = {"question_text": "Should I raise my prices?", "question_theme": "money", "question_id": "q1", "mantra_count": 4}
    stubs["sq_delay"] = 3.0                          # a cold ranking
    t = time.perf_counter()
    out = main.get_daily_loop("cid", None, 0)
    assert time.perf_counter() - t < 2.0             # waited at most ~1 s for it, not 3
    assert out["question"]["text"] == "Should I raise my prices?" and out["question"]["why"] is None
    assert out["practice"]["count"] == 4 and out["streak"]["longest_streak"] == 8


def test_a_stored_question_keeps_its_why_when_the_ranking_is_warm(stubs):
    stubs["row"] = {"question_text": "Should I raise my prices?", "question_theme": "money", "question_id": "q1"}
    out = main.get_daily_loop("cid", None, 0)
    assert out["question"]["why"] == "Money is active."


def test_the_first_call_of_the_day_waits_for_the_ranking_and_stores_the_pick(stubs):
    stubs["row"] = {}
    stubs["sq_delay"] = 1.3                          # longer than the 1 s allowance: must still wait, there is nothing to show yet
    out = main.get_daily_loop("cid", None, 0)
    assert out["question"]["text"] == "Should I raise my prices?"
    assert stubs["saved"] and stubs["saved"][0]["question_text"] == "Should I raise my prices?"


def test_an_unknown_chart_is_still_a_404(stubs, monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(main, "_suggested_questions_compute", lambda *a, **k: None)
    with pytest.raises(HTTPException) as e:
        main.get_daily_loop("nope", None, 0)
    assert e.value.status_code == 404


def test_the_response_shape_is_unchanged(stubs):
    stubs["row"] = {"question_text": "Q?", "question_theme": "money", "read_at": "t", "practice_at": None, "ask_at": None}
    out = main.get_daily_loop("cid", None, 0)
    assert set(out) == {"local_date", "steps", "complete", "practice", "question", "streak", "loop_streak"}
    assert out["steps"] == {"read": True, "practice": False, "ask": False} and out["complete"] is False
    assert set(out["practice"]) >= {"name", "target", "full_round", "count"}
