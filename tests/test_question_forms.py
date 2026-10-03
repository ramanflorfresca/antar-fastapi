"""Question forms × every phase of life × EN/ES/PT/Hinglish (owner 2026-10-03)."""
import pytest
from antar_engine import question_forms as qf
from antar_engine import messaging as msg

# one plain noun per phase of life, per language
PHASES = {
    "studies":    {"en": "exam results", "es": "examen", "pt": "prova", "hi": "exam"},
    "first_job":  {"en": "first job", "es": "primer trabajo", "pt": "primeiro emprego", "hi": "pehli naukri"},
    "career":     {"en": "career", "es": "carrera", "pt": "carreira", "hi": "career"},
    "business":   {"en": "business", "es": "negocio", "pt": "negócio", "hi": "business"},
    "money":      {"en": "income", "es": "dinero", "pt": "dinheiro", "hi": "paisa"},
    "debt":       {"en": "loan", "es": "deuda", "pt": "dívida", "hi": "karz"},
    "love":       {"en": "love life", "es": "vida amorosa", "pt": "vida amorosa", "hi": "pyaar"},
    "marriage":   {"en": "marriage", "es": "matrimonio", "pt": "casamento", "hi": "shaadi"},
    "separation": {"en": "separation", "es": "separación", "pt": "separação", "hi": "talaq"},
    "children":   {"en": "pregnancy", "es": "embarazo", "pt": "gravidez", "hi": "bachcha"},
    "parents":    {"en": "father's health", "es": "relación con mi padre", "pt": "relação com meu pai", "hi": "papa"},
    "home":       {"en": "new house", "es": "casa nueva", "pt": "casa nova", "hi": "naya ghar"},
    "relocation": {"en": "move abroad", "es": "mudanza al extranjero", "pt": "mudança para o exterior", "hi": "videsh"},
    "health":     {"en": "health", "es": "salud", "pt": "saúde", "hi": "sehat"},
    "legal":      {"en": "court case", "es": "juicio", "pt": "processo", "hi": "case"},
    "purpose":    {"en": "life purpose", "es": "propósito", "pt": "propósito", "hi": "jeevan ka maqsad"},
    "retirement": {"en": "retirement", "es": "jubilación", "pt": "aposentadoria", "hi": "retirement"},
    "later_life": {"en": "later years", "es": "vejez", "pt": "velhice", "hi": "budhapa"},
}

TEMPLATES = {
    "en": {"when": "When will my {n} improve?", "how": "How is my {n} looking?",
           "what": "What should I do about my {n}?", "will": "Will my {n} work out?",
           "should": "Should I focus on my {n} now?", "could": "Could my {n} get better this year?",
           "would": "Would it be wise to change my {n}?", "why": "Why is my {n} so hard?",
           "which": "Which path is best for my {n}?", "where": "Where will my {n} take me?"},
    "es": {"when": "¿Cuándo mejorará mi {n}?", "how": "¿Cómo va mi {n}?",
           "what": "¿Qué debo hacer con mi {n}?", "will": "¿Voy a tener éxito con mi {n}?",
           "should": "¿Me conviene cambiar mi {n}?", "could": "¿Podría mejorar mi {n} este año?",
           "would": "¿Sería buena idea cambiar mi {n}?", "why": "¿Por qué me cuesta tanto mi {n}?",
           "which": "¿Cuál es el mejor camino para mi {n}?", "where": "¿Dónde me llevará mi {n}?"},
    "pt": {"when": "Quando vai melhorar meu {n}?", "how": "Como está meu {n}?",
           "what": "O que devo fazer com meu {n}?", "will": "Vou ter sucesso com meu {n}?",
           "should": "Vale a pena mudar meu {n}?", "could": "É possível melhorar meu {n} este ano?",
           "would": "Seria bom mudar meu {n}?", "why": "Por que meu {n} está tão difícil?",
           "which": "Qual é o melhor caminho para meu {n}?", "where": "Onde meu {n} vai me levar?"},
    "hi": {"when": "Mera {n} kab theek hoga?", "how": "Mera {n} kaisa rahega?",
           "what": "Mere {n} ke liye kya karun?", "will": "Kya mera {n} safal hoga?",
           "should": "Mujhe apna {n} badalna chahiye?", "could": "Kya mera {n} is saal behtar ho sakta hai?",
           "would": "Agar main {n} badlun to kya hota?", "why": "Mera {n} itna mushkil kyun hai?",
           "which": "Mere {n} ke liye kaunsa raasta sahi hai?", "where": "Mera {n} mujhe kahan le jayega?"},
}
# "Cuál es…" / "Qual é…" open with a which-word but read as "what is" — both fine
OK_ALIASES = {("es", "which"): {"which", "what"}, ("pt", "which"): {"which", "what"}}

CASES = [(lang, form, phase, TEMPLATES[lang][form].format(n=nouns[lang]))
         for phase, nouns in PHASES.items() for lang in TEMPLATES for form in TEMPLATES[lang]]


@pytest.mark.parametrize("lang,form,phase,q", CASES)
def test_every_form_in_every_phase_and_language(lang, form, phase, q):
    got = qf.primary(q)
    assert got in OK_ALIASES.get((lang, form), {form}), (q, qf.detect(q))
    assert qf.is_question(q), q


@pytest.mark.parametrize("lang,form,phase,q", [c for c in CASES if c[1] in ("will", "should", "could", "would")])
def test_yes_no_forms_are_offered_the_yes_no_reading(lang, form, phase, q):
    assert msg.is_yesno_question(q), q


@pytest.mark.parametrize("lang,form,phase,q", [c for c in CASES if c[1] in ("when", "how", "why", "where")])
def test_open_forms_are_not_yes_no(lang, form, phase, q):
    assert not msg.is_yesno_question(q), q


@pytest.mark.parametrize("s", ["Estoy separado de mi esposa que vive lejos.", "Trabalho como gerente.",
                               "I was laid off in June.", "Main abhi kaam nahi kar raha.",
                               "Me casé el año pasado.", "Eu sou casado."])
def test_statements_are_not_questions(s):
    assert not qf.is_question(s), (s, qf.detect(s))


def test_fallback_intents():
    assert qf.intent("What should I do about my career?") == "what_to_do"
    assert qf.intent("¿Cuándo me caso?") == "when"
    assert qf.intent("Should I build alone or bring in a partner?") == "which"
    assert qf.intent("Mera vivah kab hoga?") == "when"
    assert qf.intent("Kya meri naukri lagegi?") == "yes_no"
    assert qf.intent("Hello there") is None
