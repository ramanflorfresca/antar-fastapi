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
    assert d and "not a diagnosis" in d


@pytest.mark.parametrize("concern,text", [
    ("money", "The timing doesn't support speculation."),
    ("speculation", "The window for unearned gains is open now."),
    (None, "The timing supports going after outside funding this month."),
])
def test_money_answers_get_a_financial_disclaimer(concern, text):
    d = disclaimer_for(concern, text, language="en")
    assert d and "not financial advice" in d


def test_legal_answer_disclaims_outcome_prediction():
    d = disclaimer_for("legal", "The timing leans in your favour on this matter.",
                       language="en")
    assert d and "not legal advice" in d and "not a guarantee of any result" in d


def test_fertility_answer_gets_a_medical_disclaimer():
    d = disclaimer_for(None, "Yes - family window is open now; conceiving is supported.",
                       language="en")
    assert d and "not a diagnosis" in d


@pytest.mark.parametrize("lang,needle", [
    ("en", "not a diagnosis"),
    ("es", "no es un diagnóstico"),
    ("pt", "não é diagnóstico"),
    ("hi", "diagnosis nahi"),
    ("hinglish", "diagnosis nahi"),
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


@pytest.mark.parametrize("concern,text", [
    ("health", "Not yet — next health window Dec 2026."),
    ("legal",  "The timing leans in your favour on this matter."),
    ("money",  "The timing doesn't support speculation."),
    (None,     "Yes - family window is open now; conceiving is supported."),
])
def test_disclaimer_never_denies_a_shipped_feature(concern, text):
    """[disclaimer-honest-register] The first cut said "Antar reads timing, not
    your body" and "not a prediction of any outcome" — both false. Antar DOES
    read health from the chart and DOES return a dated yes/no on a legal
    question, so a disclaimer written in the denial register contradicts the
    answer printed directly above it. Bound the authority, never the feature."""
    d = disclaimer_for(concern, text, language="en")
    assert d
    low = d.lower()
    for banned in ("reads timing, not", "not a prediction", "does not predict",
                   "not fertility", "timing only", "reading"):
        assert banned not in low, f"denial-register phrase back in: {banned!r}"
    assert "planetary positions" in low, "name the method, not only what it isn't"
    assert "not a guarantee" in low or "not a diagnosis" in low


# [yesno-disclaimer 2026-10-05] Yes/No answers are a short timing line with no herb
# or court words, and a generic concern — production returned disclaimer=None for
# "Will my health improve this year?". The QUESTION decides the domain.
@pytest.mark.parametrize("q,needle", [
    ("Will my health improve this year?", "not a diagnosis"),
    ("Am I going to recover from this surgery soon?", "not a diagnosis"),
    ("Will I win my court case?", "not legal advice"),
    ("Should I put my savings into crypto this week?", "not financial advice"),
    ("Will I get pregnant this year?", "clinical answer about conceiving"),
])
def test_yesno_domain_comes_from_the_question(q, needle):
    d = disclaimer_for("general", "The timing is not aligned yet.", "NO", language="en", question=q)
    assert d and needle in d


@pytest.mark.parametrize("q", [
    "Should I take this job offer?",
    "Is the operations manager role right for me?",
    "Will I hear back about the interview?",
    "Should I start my free trial?",
    "Can I share my story with my family?",
])
def test_ordinary_questions_get_no_disclaimer(q):
    assert disclaimer_for("general", "The timing is not aligned yet.", language="en", question=q) is None


def test_question_cannot_override_a_set_concern_and_es_still_works():
    assert "not financial advice" in disclaimer_for("money", "x", language="en", question="Will my health improve?")
    assert disclaimer_for("general", "x", language="es", question="¿Mejorará mi salud?").startswith("Un análisis")


# [disclaimer-false-positive 2026-10-06] The text sniff ran on answers full of everyday words:
# production showed "not legal advice … Your lawyer runs the case" under a RAISE answer that said
# "make your case with clear facts". These pin the false positives shut and the true positives open.
@pytest.mark.parametrize("text", [
    "Make your case with clear facts, not just a feeling you deserve more.",
    "The timing favours a structured, prepared ask — build the case with three specific wins.",
    "You may be hearing back from them next week; keep a calm tone.",
    "Your business concept is clear — test it with one customer.",
    "Invest time in one skill; share your results with your manager.",
    "Update your portfolio of work and ask the loan officer at your bank nothing yet.",
    "The verdict is a YES for the career window; counsel your team early.",
    "A settlement between two priorities is needed this month.",
])
def test_everyday_words_in_a_career_answer_do_not_trigger_a_disclaimer(text):
    assert disclaimer_for("general", text, "YES", language="en") is None
    assert disclaimer_for(None, text, language="en", question="Should I ask for a raise this quarter?") is None


@pytest.mark.parametrize("text,needle", [
    ("Traditionally, Ayurveda associates this period with brahmi or neem.", "not a diagnosis"),
    ("The timing doesn't support speculation this month.", "not financial advice"),
    ("Skip the casino and the lottery; crypto is not supported now.", "not financial advice"),
    ("The timing supports going after outside funding this month.", "not financial advice"),
    ("Your lawyer should file before the court date; the lawsuit timing is mixed.", "not legal advice"),
    ("Yes - family window is open now; conceiving is supported.", "not a diagnosis"),
    ("Pregnancy planning is supported in this window.", "not a diagnosis"),
])
def test_genuinely_sensitive_answers_still_get_the_right_disclaimer(text, needle):
    d = disclaimer_for(None, text, language="en")
    assert d and needle in d, text
