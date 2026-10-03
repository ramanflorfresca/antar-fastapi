"""The decision gate must fire in every language Antar answers in.

is_decision_question() is what lets build_convergence_timing() and
run_event_engine() run at all — a False here means no verdict, no dated
window, no actions and no practices. The list has twice shipped missing a
language (pt in Sep 2026, Hinglish in Oct 2026); both were silent, because
a reflective answer still reads fine. These cases lock each language in.
"""
import pytest
from antar_engine.ask_consultation import is_decision_question


@pytest.mark.parametrize("q", [
    # English
    "When should I change jobs?", "Should I quit my job this year?",
    # Spanish
    "¿Cuándo debo cambiar de trabajo?", "¿Debo cambiar de trabajo?",
    # Portuguese
    "Quando devo mudar de emprego?", "Devo mudar de emprego?",
    # Hinglish — the romanised-Hindi gap
    "Job change kab karun?", "Shaadi kab hogi?", "Paisa kab aayega?",
    "Mujhe job kab change karni chahiye?",
    "Kya mujhe business start karna chahiye?",
    "Ghar kab milega?",
])
def test_timing_questions_reach_the_dated_path(q):
    assert is_decision_question(q), f"{q!r} lost its verdict/window/practices"


@pytest.mark.parametrize("q", [
    "Mera business kyun nahi chal raha?",   # why — reflective
    "Aaj ka din kaisa hai?",                # how is today
    "Meri strength kya hai?",               # what am I like
    "What is my strength?",
])
def test_reflective_questions_stay_reflective(q):
    assert not is_decision_question(q), f"{q!r} wrongly pulled into the dated path"
