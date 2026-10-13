import os
os.environ.setdefault("DEEPSEEK_API_KEY", "x")
import asyncio
import main


def test_week_span_questions_are_recognised():
    for q in ("How is my week ahead?", "What are the best days this week?", "¿Cómo se ve esta semana?",
              "Como está a próxima semana?", "Is hafte kaisa rahega?", "How are the coming days?"):
        assert main._ASK_WEEKSPAN_Q.search(q), q
    for q in ("How is my money this month?", "Should I quit my job?"):
        assert not main._ASK_WEEKSPAN_Q.search(q), q


def _run(payload, keep):
    return asyncio.run(main._ask_localize(dict(payload), "en", ["read", "next"], None, keep_days=keep))


def test_localize_keeps_the_weekday_for_a_week_span_question():
    payload = {"read": "Monday 13 Oct is your clearest day; use it.", "next": "Call one contact on Monday."}
    assert "Monday" not in _run(payload, False)["read"]          # the bug this guards: the plain strip deleted it
    out = _run(payload, bool(main._ASK_WEEKSPAN_Q.search("How is my week ahead?")))
    assert "Monday" in out["read"] and "Monday" in out["next"]
