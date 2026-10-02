"""Conversation layer (2026-10-02): follow-ups become standalone questions, and
the narrator sees the moves it already gave. Seeded with live WhatsApp turns."""
import asyncio
import json

from antar_engine import conversation as cv

THREAD = [{"q": "How is speculation today", "a": "Speculation is moderately favorable today…",
           "domain": "speculation", "m": "Cap your speculative position at an amount you can walk away from."}]


def test_followup_gate():
    for t in ("How about tomorrow", "and money?", "y mañana?", "e amanhã?", "aur kal?",
              "why?", "what about next week"):
        assert cv.looks_like_followup(t, THREAD), t
    for t in ("Which profession fits me best given my background in engineering and sales?",
              "When will I get married to the person I am seeing now and will it last"):
        assert not cv.looks_like_followup(t, THREAD), t
    assert not cv.looks_like_followup("How about tomorrow", [])       # nothing to follow


def test_parse_rewrite_accepts_a_faithful_followup():
    raw = json.dumps({"type": "follow_up", "standalone": "How is speculation for me tomorrow?"})
    assert cv.parse_rewrite(raw, "How about tomorrow") == "How is speculation for me tomorrow?"


def test_parse_rewrite_rejects_new_topic_or_drift():
    assert cv.parse_rewrite(json.dumps({"type": "new", "standalone": "x"}), "When will I marry?") is None
    # drops the person's own words → rejected
    assert cv.parse_rewrite(json.dumps({"type": "follow_up",
                                        "standalone": "How is my career this year?"}),
                            "And what about money tomorrow") is None
    assert cv.parse_rewrite("not json", "How about tomorrow") is None
    assert cv.parse_rewrite(json.dumps({"type": "follow_up", "standalone": "x" * 300}), "why?") is None


def test_rewrite_request_carries_recent_turns():
    req = json.loads(cv.rewrite_request("How about tomorrow", THREAD, "en"))
    assert req["recent_conversation"][0]["user_asked"] == "How is speculation today"
    assert req["new_message"] == "How about tomorrow"


def test_moves_block_lists_prior_advice_once():
    block = cv.moves_block(THREAD + [dict(THREAD[0])])
    assert block.count("Cap your speculative position") == 1
    assert "Do NOT repeat" in block
    assert cv.moves_block([{"q": "x", "a": "y", "m": ""}]) == ""


def test_history_records_what_was_typed(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    saved = []

    async def fake_save(sb, chart_id, question, payload, language, **kw):
        saved.append(question)
    monkeypatch.setattr(main, "save_chat_message", fake_save)

    async def run():
        main._ASK_TYPED_Q.set("How about tomorrow")
        await main._ask_persist(None, "chart-1", "How is speculation for me tomorrow?",
                                {}, "en", "explore")
    asyncio.run(run())
    assert saved == ["How about tomorrow"]
