"""[thread-home 2026-10-12, P1] The conversation Home: opening, router, cards, rollout flag. Deterministic, en + es."""
import re

import pytest

from antar_engine import thread_home as T

DECISION = {"prediction": "Today favours home and property, then work and reputation. A lighter-touch day.",
            "move": "Between 12:17 PM and 1:05 PM, do the analytical work that needs no one else.",
            "holds": "It holds if the decision that matters goes between 12:17 PM and 1:05 PM.",
            "breaks": "It breaks if you force a hard conversation between 4:54 PM and 6:19 PM.",
            "window": {"best": "12:17 PM – 1:05 PM", "avoid": "4:54 PM – 6:19 PM", "best_start": "12:17", "best_end": "13:05"}}
FEED_CLOSING = {"now": [{"topic": "money", "label": "Money", "kind": "open", "start": "2026-10-12", "end": "2026-10-12", "days_left": 0,
                         "headline": "Money matters have better backing than usual.", "move": "Pick the one money decision you have been putting off and act on it within the window."}],
                "next": [], "care": []}
FEED_OPEN2 = {"now": [{"topic": "career", "kind": "open", "end": "2026-10-14", "days_left": 2, "move": "Make your ask at work within the window."}], "next": [], "care": []}
FEED_CARE = {"now": [{"topic": "health", "kind": "care", "start": "2026-10-10", "end": "2026-10-24", "days_left": 12}], "next": [], "care": []}
READ = {"topic": "money", "label": "Money", "scale": "month", "period": {"label": "Next 30 days"}, "tone": "steady",
        "claim": "Over the next 30 days, it is steady overall for money.", "best_window": None, "watch_window": None,
        "your_move": "Hold new spending.", "confidence_note": "Lower confidence.", "why": "The chapter you are in is tied to money."}
PHASE = {"available": True, "chapter": {"planet": "Rahu"}, "shift": {"planet": "Rahu"}, "how_they_combine": "The same energy again.",
         "life_areas": [], "upcoming_shifts": [], "turning_points": []}


def texts(r):
    return " ".join(m["text"] for m in r["messages"])


def test_opening_leads_with_a_window_that_closes_today():
    r = T.opening({"name": "Raman Singh", "hour": 8, "decision": DECISION, "windows": FEED_CLOSING, "heads_up": None}, "en")
    t = texts(r)
    assert t.startswith("Good morning, Raman.") and "money window closes tonight" in t
    assert FEED_CLOSING["now"][0]["headline"] not in t          # facts come from fields, nothing is quoted loosely
    assert "Want me to walk you through it?" in t
    assert [q["send"] for q in r["quick_replies"]][0] == "Yes, walk me through it"
    assert r["starters"]["primary"]["send"] == "Just tell me my day" and len(r["starters"]["items"]) == 4


def test_opening_with_two_facts_and_a_heads_up():
    r = T.opening({"name": "Raman", "hour": 15, "decision": DECISION, "windows": FEED_CLOSING, "heads_up": {"name": "Andres"}}, "en")
    t = texts(r)
    assert "Good afternoon, Raman." in t and "Two things matter today." in t and "Andres has a tender day today." in t


def test_opening_falls_back_to_the_days_read_then_a_plain_offer():
    r = T.opening({"name": "Raman", "hour": 21, "decision": DECISION, "windows": {"now": []}, "heads_up": None}, "en")
    assert DECISION["prediction"] in texts(r) and "Good evening, Raman." in texts(r)
    r2 = T.opening({"name": "", "hour": None, "decision": None, "windows": None, "heads_up": None}, "en")
    assert "Good to see you, there." in texts(r2) and "Want the one thing for today?" in texts(r2)


def test_opening_open_window_reuses_the_engine_move_verbatim():
    t = texts(T.opening({"name": "R", "hour": 9, "windows": FEED_OPEN2}, "en"))
    assert "open for 2 more days" in t and "Make your ask at work within the window." in t


def test_opening_care_stretch():
    t = texts(T.opening({"name": "R", "hour": 9, "windows": FEED_CARE}, "en"))
    assert "careful stretch for health" in t.lower()


def test_spanish_opening():
    t = texts(T.opening({"name": "Raman", "hour": 8, "windows": FEED_CLOSING, "decision": DECISION}, "es"))
    assert t.startswith("Buenos días, Raman.") and "se cierra esta noche" in t and "paso a paso" in t


@pytest.mark.parametrize("text,intent,arg", [
    ("Just tell me my day", "today", None), ("What's my move today?", "today", None), ("Yes, walk me through it", "today", None),
    ("Show me my year", "year", None), ("How's this month?", "month", None), ("What chapter am I in?", "chapter", None),
    ("How's my money?", "topic", "money"), ("how's my health", "topic", "health"), ("Someone in my life", "people", None),
    ("Not sure what to ask?", "starters", None), ("Something else", "starters", None), ("I just feel stuck", "stuck", None),
    ("I'm deciding something", "deciding", None), ("A worry", "worry", None), ("Just timing", "timing", None),
    ("What's coming for me?", "coming", None), ("Where am I today?", "loop", None),
    ("Should I raise my prices next month?", "ask", None), ("Will my ex come back?", "ask", None),
    ("When is a good time to make a move at work?", "ask", None), ("Qué debería hacer con mi negocio?", "ask", None),
])
def test_classify(text, intent, arg):
    assert T.classify(text) == (intent, arg)


def test_reply_today_card_and_source():
    r = T.reply("today", None, {"decision": DECISION}, "en")
    assert r["cards"][0]["type"] == "move" and r["cards"][0]["data"]["window"]["best_start"] == "12:17"
    assert r["cards"][0]["source"] and r["messages"][0]["text"] == DECISION["prediction"]
    assert r["cards"][0]["link"] == {"route": "/full/day"}


def test_reply_topic_uses_the_engine_claim_verbatim():
    r = T.reply("topic", "money", {"topic_read": READ}, "en")
    assert r["messages"][0]["text"] == READ["claim"] and r["cards"][0]["type"] == "topic" and r["cards"][0]["link"]["route"] == "/ask/topic/money"


def test_reply_year_month_chapter_loop_people():
    y = T.reply("year", None, {"reads": [READ, dict(READ, topic="career", label="Career")]}, "en")
    assert y["cards"][0]["type"] == "year" and len(y["cards"][0]["data"]["topics"]) == 2 and y["cards"][0]["link"]["route"] == "/timeline?view=year"
    assert T.reply("month", None, {"reads": [READ]}, "en")["cards"][0]["type"] == "month"
    assert T.reply("chapter", None, {"phase": PHASE}, "en")["cards"][0]["type"] == "phase"
    assert [c["type"] for c in T.reply("coming", None, {"reads": [READ], "phase": PHASE}, "en")["cards"]] == ["year", "phase"]
    lp = T.reply("loop", None, {"loop": {"steps": {"read": True}, "streak": {"streak": 7}}}, "en")
    assert lp["cards"][0]["type"] == "loop" and lp["cards"][0]["data"]["streak"]["streak"] == 7
    pe = T.reply("people", None, {"heads_up": {"name": "Andres", "connection_chart_id": "x"}}, "en")
    assert pe["cards"][0]["type"] == "heads_up" and "Andres has a tender day today." in pe["cards"][0]["data"]["text"]
    assert "Star up to three people" in T.reply("people", None, {"heads_up": None, "heads_set": False}, "en")["messages"][0]["text"]
    assert "Nobody you follow" in T.reply("people", None, {"heads_up": None, "heads_set": True}, "en")["messages"][0]["text"]


def test_reply_ask_wraps_the_ask_response_and_notes_a_reframe():
    ask = {"mode": "explore", "read": {"answer": "x"}, "reframed": {"kind": "reunion", "original": "Will my ex come back?"}}
    r = T.reply("ask", None, {"ask": ask}, "en")
    assert r["cards"][0]["type"] == "ask_answer" and r["cards"][0]["data"] is ask
    assert "I can't tell you what another person feels or will do" in r["messages"][0]["text"]
    plain = T.reply("ask", None, {"ask": {"mode": "explore", "read": {}}}, "en")
    assert plain["messages"] == [] and plain["cards"]


def test_missing_engine_data_never_breaks_a_reply():
    for intent in ("today", "year", "month", "chapter", "coming", "loop", "topic", "ask"):
        r = T.reply(intent, "money" if intent == "topic" else None, {}, "en")
        assert r["messages"] and not r["cards"] and r["quick_replies"]


def test_guided_replies_offer_taps_not_a_blank_box():
    for intent in ("deciding", "worry", "timing", "stuck"):
        r = T.reply(intent, None, {}, "en")
        assert r["quick_replies"] and r["messages"]
    assert T.reply("stuck", None, {}, "en")["quick_replies"][0]["send"] == "A decision"
    assert T.reply("starters", None, {}, "en")["starters"]["items"]


def test_es_parity_with_en():
    assert set(T._T["en"]) == set(T._T["es"])
    for k in T._T["en"]:
        assert T._T["es"][k].count("{") == T._T["en"][k].count("{"), k


def test_no_jargon_in_templates():
    for lg in ("en", "es"):
        blob = " ".join(T._T[lg].values()).lower()
        assert not re.search(r"dasha|mahadasha|antardasha|vimshottari|nakshatra|ephemeris", blob)


def test_rollout_flag_is_stable_and_respects_the_allow_list():
    assert T.enabled("C1", 0, "") is False
    assert T.enabled("C1", 100, "") is True
    assert T.enabled("c1", 0, "C1, c2") is True
    assert T.enabled("zzz", "abc", "") is False
    ids = [f"chart-{i}" for i in range(400)]
    on = sum(T.enabled(i, 25, "") for i in ids)
    assert 60 < on < 140                                   # about a quarter
    assert all(T.enabled(i, 25, "") == T.enabled(i, 25, "") for i in ids[:50])      # stable


def test_routes_and_config_keys():
    import main
    paths = {(r.path, tuple(sorted(getattr(r, "methods", []) or []))) for r in main.app.routes}
    assert ("/api/v1/conversation/{chart_id}/open", ("GET",)) in paths
    assert ("/api/v1/conversation/{chart_id}/message", ("POST",)) in paths
    assert ("/api/v1/conversation/{chart_id}/enabled", ("GET",)) in paths
    from antar_engine import app_config
    assert app_config.ALLOWED_KEYS["home_thread_pct"]["default"] == "0"      # dark until you turn it on
    assert "home_thread_allow" in app_config.ALLOWED_KEYS
