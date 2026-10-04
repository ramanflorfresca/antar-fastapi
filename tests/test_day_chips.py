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
