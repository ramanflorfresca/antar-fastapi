"""[appstore-disclaimer 2026-10-05] Sensitive-domain answers must carry a
disclaimer at the point of delivery, in the answer's own language.

Live production on 2026-10-05 returned named Ayurvedic substances to
"I keep getting sick, when will my health improve?" with nothing attached —
the disclaimer copy existed only in Terms, the WhatsApp legal block and the
marketing site. These pin the gap closed.
"""
import pytest

from antar_engine.answer_disclaimer import disclaimer_for


@pytest.mark.parametrize("concern,text", [
    ("health", "Not yet — next health window Dec 2026 - Feb 2027."),
    ("health_self", "Your recovery builds through the winter."),
    # the real failure: concern resolved elsewhere, herbs still landed
    ("career", "Traditionally, Ayurveda associates this period with brahmi or gotu kola."),
    (None, "warm sesame-oil self-massage (abhyanga) supports you now"),
])
def test_health_answers_get_a_medical_disclaimer(concern, text):
    d = disclaimer_for(concern, text, language="en")
    assert d and "Not medical advice" in d


@pytest.mark.parametrize("concern,text", [
    ("money", "The timing doesn't support speculation."),
    ("speculation", "The window for unearned gains is open now."),
    (None, "The timing supports going after outside funding this month."),
])
def test_money_answers_get_a_financial_disclaimer(concern, text):
    d = disclaimer_for(concern, text, language="en")
    assert d and "Not financial advice" in d


def test_legal_answer_disclaims_outcome_prediction():
    d = disclaimer_for("legal", "The timing leans in your favour on this matter.",
                       language="en")
    assert d and "Not legal advice" in d and "not a prediction" in d


def test_fertility_answer_gets_a_medical_disclaimer():
    d = disclaimer_for(None, "Yes - family window is open now; conceiving is supported.",
                       language="en")
    assert d and "Not medical advice" in d


@pytest.mark.parametrize("lang,needle", [
    ("en", "Not medical advice"),
    ("es", "No es consejo médico"),
    ("pt", "Não é orientação médica"),
    ("hi", "medical advice nahi hai"),
    ("hinglish", "medical advice nahi hai"),
])
def test_disclaimer_speaks_the_answers_language(lang, needle):
    """English-only keyword logic is a silent bug — es/pt/Hinglish users would
    otherwise get an English disclaimer on a non-English answer."""
    d = disclaimer_for("health", "health window Dec 2026", language=lang)
    assert d and needle in d


@pytest.mark.parametrize("text", [
    "This week, write down one clear sentence about what you offer.",
    "Talk openly with your partner this week about what ready looks like.",
])
def test_neutral_answers_get_no_disclaimer(text):
    """Don't paper every answer with legalese — only the four real domains."""
    assert disclaimer_for("career", text, language="en") is None


def test_never_raises_on_junk_input():
    assert disclaimer_for(None, None, language=None) is None
    assert disclaimer_for("", "", language="zz") is None
