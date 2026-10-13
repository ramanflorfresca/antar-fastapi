from antar_engine.conversation import bare_affirmative, previous_question


def test_bare_agreements_in_four_languages():
    for t in ("Yes", "yes.", "Yeah!", "ok", "Sí", "claro", "Sim", "Haan", "haan ji", "Theek hai", "aur batao"):
        assert bare_affirmative(t), t


def test_real_questions_are_not_bare_agreements():
    for t in ("Yes, but when does the window open?", "Is it ok to wait?", "Haan lekin kab?", "How is my money?", ""):
        assert not bare_affirmative(t), t


def test_previous_question_skips_the_agreement_itself():
    thread = [{"q": "How is speculation this week?"}, {"q": "Yes"}]
    assert previous_question(thread) == "How is speculation this week?"
