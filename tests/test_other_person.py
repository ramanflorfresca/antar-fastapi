"""[other-person 2026-10-12] Questions about another person's feelings, or a forecast of illness,
are rewritten into the asker's decision. The matching must catch them in every language and
must never catch a question about a boss, a client, a deal or the asker's general health."""
import pytest

from antar_engine.other_person import classify, reframe, _REFRAME

CAUGHT = [
    ("Will my ex come back?", "reunion"),
    ("my ex wants me back", "reunion"),
    ("Does my ex still love me?", "reunion"),
    ("Will my ex text me?", "reunion"),
    ("Are we going to get back together?", "reunion"),
    ("¿Volverá mi ex conmigo?", "reunion"),
    ("¿Mi ex va a volver?", "reunion"),
    ("Meu ex vai voltar comigo?", "reunion"),
    ("Kya mera ex wapas ayega?", "reunion"),
    ("Does he love me?", "feelings"),
    ("Does she like me?", "feelings"),
    ("Will he ever propose?", "feelings"),
    ("is my boyfriend cheating", "feelings"),
    ("kya woh mujhse pyaar karta hai", "feelings"),
    ("Will I have a health scare this year?", "health_event"),
    ("will I get sick", "health_event"),
    ("Will I get cancer?", "health_event"),
    ("When will I die?", "health_event"),
    ("How long will I live?", "health_event"),
    ("¿Tendré cáncer?", "health_event"),
    ("Quando vou morrer?", "health_event"),
    ("kab marunga", "health_event"),
    ("¿Voy a enfermarme este año?", "health_event"),
    ("Vou adoecer este ano?", "health_event"),
    ("Will I fall ill this winter?", "health_event"),
]

LEFT_ALONE = [
    "Should I take the job?",
    "Will my boss approve my raise?",
    "Will my business come back strong?",
    "Will the deal close this month?",
    "Will my partnership break?",
    "How is my health this year?",
    "When is my energy highest?",
    "How should I handle my ex in the custody case?",
    "Should I invite my ex to my wedding?",
    "Can I leave my job?",
    "Will I get the loan?",
    "¿Debo invitar a mi ex?",
    "Which day is best for a hard conversation with my partner?",
]


@pytest.mark.parametrize("q,kind", CAUGHT)
def test_caught(q, kind):
    assert classify(q) == kind


@pytest.mark.parametrize("q", LEFT_ALONE)
def test_left_alone(q):
    assert classify(q) is None


def test_every_kind_has_every_language():
    for kind, table in _REFRAME.items():
        for lang in ("en", "es", "pt", "hi", "hinglish"):
            assert table.get(lang), (kind, lang)


def test_reframed_question_is_not_caught_again():
    # the rewritten question must pass straight through the normal Ask path
    for kind, table in _REFRAME.items():
        for lang, text in table.items():
            assert classify(text) is None, (kind, lang, text)


def test_unknown_language_falls_back_to_english():
    assert reframe("feelings", "xx") == _REFRAME["feelings"]["en"]
    assert reframe("nope", "en") == ""


# ── health softening: no verdict chip, no lead phrase, no dated window for an illness forecast ──
def test_health_soften_applies_to_health_answers_and_illness_forecasts_only():
    import main
    assert main._health_soften_applies("health", None) is True
    assert main._health_soften_applies("career", {"kind": "health_event", "original": "x"}) is True
    assert main._health_soften_applies("career", None) is False
    assert main._health_soften_applies("career", {"kind": "feelings"}) is False
    assert main._health_soften_applies("", None) is False


def test_health_soften_kill_switch(monkeypatch):
    import main
    monkeypatch.setenv("ASK_HEALTH_SOFTEN", "off")
    assert main._health_soften_applies("health", None) is False
