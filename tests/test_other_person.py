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
    # [relationship set 2026-10-12] "he or she" is how people type it when unsure
    ("Will he or she come back?", "reunion"),
    ("Is he or she cheating on me?", "feelings"),
    ("Is my husband or wife having an affair?", "trust"),
    ("Is there a third person in my relationship?", "trust"),
    ("Me engaña mi esposo?", "trust"),
    ("Am I having an affair?", "affair"),
    ("Will my affair be exposed?", "affair"),
    ("Will I have a secret relationship?", "affair"),
    ("When will he or she contact me?", "contact"),
    ("Will we meet this month?", "contact"),
    ("Will my ex marry someone else?", "ex_future"),
    ("What will my spouse look like?", "partner_looks"),
    ("Will my spouse be from a different caste or religion?", "partner_looks"),
]

LEFT_ALONE = [
    "Will I ever get married?",
    "Will my marriage last?",
    "Is my partner compatible with me?",
    "Will I marry before 30?",
    "Will my spouse be supportive of my business?",
    "Should I propose?",
    "Should I meet the investors this month?",
    "Will we meet our revenue target this month?",
    "Will my contact at the bank call back about the loan?",
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
