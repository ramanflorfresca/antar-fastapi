"""[right-now 2026-10-05] "How is my love life looking right now?" is a CURRENT-status question, not a
question about today. 22 of our own suggestion chips were read as day questions, which added
per-day instructions and switched the timing path off — and, once that flag was fixed, would have
put an invented clock ("before 14:02 today") into status answers via hora_karana. One shared rule."""
from antar_engine import ask_followups as af
from antar_engine.ask_timeframe import detect_horizon, now_means_today
from antar_engine.hora_karana import is_tactical_question

STATUS = ["How is my money looking right now?", "How is my love life looking right now?",
          "Why does work feel stuck right now?", "What is draining my energy right now?",
          "How do I handle the tension at home right now?", "Which practice fits me best right now?",
          "¿Cómo está mi dinero ahora mismo?", "¿Cómo se ve mi vida amorosa ahora?",
          "Como está meu dinheiro agora?", "How am I doing right now?"]
ACT_NOW = ["Should I sign this contract right now?", "What should I do right now?",
           "Is it a good time to call him right now?", "How is my day right now?",
           "¿Debo firmar esto ahora?", "¿Puedo llamarlo ahora?", "Devo assinar isso agora?"]


def _is_day(q):
    return (detect_horizon(q) or {}).get("kind") == "days"


def test_status_questions_are_not_day_or_tactical():
    for q in STATUS:
        assert not _is_day(q), f"day-scope: {q}"
        assert not is_tactical_question(q), f"tactical: {q}"
        assert not now_means_today(q), q


def test_act_now_questions_still_are():
    for q in ACT_NOW:
        assert _is_day(q), f"day-scope lost: {q}"
        assert is_tactical_question(q), f"tactical lost: {q}"


def test_bare_now_action_is_still_tactical():
    # a bare "now" never made a DAY scope (unchanged) but is still a clock question when acting
    assert is_tactical_question("Should I send it now?")
    assert not is_tactical_question("Why is everything so heavy now?")


def test_explicit_today_tomorrow_unchanged():
    for q in ("How is tomorrow looking?", "What is the best time of day for me today?",
              "Which day this week is best for me?", "¿Cómo se ve mañana?", "O que devo evitar hoje?"):
        assert _is_day(q) or is_tactical_question(q), q


def test_no_non_day_chip_is_read_as_a_day_question():
    bad = [(lang, q) for lang, t in af._Q.items() for b, lanes in t.items() if b != "day"
           for q in lanes.values() if _is_day(q)]
    assert not bad, bad
