import os
os.environ.setdefault("DEEPSEEK_API_KEY", "x")
import main


def test_action_questions_about_this_period_are_not_dasha_questions():
    for q in ("How do I make the most of this period for my venture?",
              "How do I make the most of this period for my money?",
              "Should I wait out this period?",
              "What does my health period look like this year?"):
        assert not main._is_dasha_q(q), q


def test_asking_what_the_period_is_still_works():
    for q in ("What is my dasha?", "Which mahadasha am I in?", "What is my current period?",
              "Tell me about this period", "what's the outcome of this dasha?"):
        assert main._is_dasha_q(q), q
