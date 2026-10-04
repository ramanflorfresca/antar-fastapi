"""'How is my day today' gets day chips, not career chips (owner screenshot 2026-10-03)."""
from dotenv import load_dotenv
load_dotenv()
import main


def test_day_overview_questions():
    for q in ["How is my day today?", "how is my day today", "How is tomorrow?", "How is my week?",
              "How's today looking?", "¿Cómo está mi día hoy?", "¿Cómo se ve mañana?",
              "Como está meu dia hoje?", "Como vai ser minha semana?", "Aaj ka din kaisa rahega?"]:
        assert main._ask_is_day_overview(q), q


def test_domain_or_other_questions_are_not_day_overview():
    for q in ["How is my money today?", "How is speculation for me today?", "How is my career looking this year?",
              "Which day this week is best for me?", "When will my day come?", "How is my health looking this week?"]:
        assert not main._ask_is_day_overview(q), q


def test_day_chips_replace_career_chips_even_with_inherited_concern():
    chips = main._ask_followups("career", "How is my day today?", "en")
    assert chips == ["How is tomorrow looking?", "What is the best time of day for me today?",
                     "How is my week ahead?"]
    assert "Which profession fits me best?" not in chips
    assert "career" in " ".join(main._ask_followups("career", "How is my career this year?", "en")).lower()
    assert main._ask_followups("general", "¿Cómo está mi día hoy?", "es")[0] == "¿Cómo se ve mañana?"
    # never repeats the question just asked
    assert "How is tomorrow looking?" not in main._ask_followups("career", "How is tomorrow looking?", "en")


def test_day_overview_never_inherits_the_previous_topic(monkeypatch):
    import asyncio
    async def nop(*a, **k): return None
    monkeypatch.setattr(main, "_ask_persist", nop)
    monkeypatch.setattr(main, "_nlu_shadow", nop)
    monkeypatch.setattr(main, "_ask_harvest_stated", lambda *a, **k: None)
    monkeypatch.setattr(main, "_ask_recent_thread", lambda cid, limit=4, within_minutes=240: [
        {"q": "How is speculation for me today", "a": "x", "domain": "speculation", "m": ""}])
    r = asyncio.run(main.ask_endpoint(main.AskRequest(
        question="How is my day today?", chart_id="a4c9d57b-fb9c-4890-8fe7-4a9904f515ed",
        mode="explore", language="en", tz_offset=-240)))
    txt = f"{r.get('read')} {r.get('next')}".lower()
    assert "speculat" not in txt and "unearned" not in txt


def test_day_chip_never_repeats_the_day_just_asked():
    t = main._ask_followups("general", "How is tomorrow?", "en")
    assert all("tomorrow" not in c.lower() for c in t) and len(t) >= 2
    w = main._ask_followups("general", "How is my week?", "en")
    assert all("week" not in c.lower() for c in w) and len(w) >= 2
