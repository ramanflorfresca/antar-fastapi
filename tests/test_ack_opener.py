from antar_engine.answer_polish import polish_answer, strip_ack_opener

ACK = [
    "Raman, I hear how much weight this question carries.",
    "Raman, this weight is real — and you deserve a clear answer.",
    "Raman, this is a real question and I take it seriously.",
    "Raman, sitting with this uncertainty takes real steadiness — and you have it.",
    "Raman, the uncertainty you're carrying here is real — and it deserves a clear answer.",
    "Raman, carrying doubt about trust is exhausting — and you deserve a clear-eyed look at this.",
    "Raman, this is a hard place to be — and the uncertainty you're feeling is real.",
    "Raman, I hear that question.",
    "Raman, this one clearly matters to you.",
    "I understand why that matters.",
    "Raman, the wait is real — and it makes sense to want to understand it.",
    "Raman, carrying this doubt quietly is exhausting — and you deserve clarity.",
    "Raman, carrying this is real — and you're not stuck forever.",
    "Shashi, carrying this is heavy — and the fact that you're asking means you're ready to move.",
    "You're carrying something heavy right now — and the timing sees it clearly.",
    "Shashi, this is weighing on you — and that matters.",
    "Raman, this is a real weight to carry.",
    "Andres, this uncertainty is genuinely hard to carry — and you deserve a clear answer.",
    "Entiendo lo que pesa esta pregunta.",
    "Entendo por que isso importa.",
]
BODY = "The timing leans toward a temporary fight, not a final break. What steadies it is your own follow-through."


def test_acknowledging_first_sentence_is_dropped():
    for a in ACK:
        out, changed = strip_ack_opener(a + " " + BODY)
        assert changed and out == BODY, a


def test_real_answer_after_a_colon_is_kept():
    t = "Raman, that question deserves a straight answer: nothing in your timing points to an affair. What does show up is restlessness."
    out, changed = strip_ack_opener(t)
    assert changed and out.startswith("Nothing in your timing points to an affair.") and "restlessness" in out and "deserves" not in out


def test_answers_that_start_with_the_answer_are_untouched():
    for t in ("The timing leans toward a temporary fight. It is a hard stretch.",
              "Likely — partnership window Nov 2026 – Jan 2027. You are in a quiet phase.",
              "This season is a hard one for money, and the window opens in March.",       # "hard" + content, not an acknowledgment
              "Your marriage question is about the bond with your former spouse. Here is the timing.",
              "I'd put the window in March 2027. Before then, build the ground."):
        out, changed = strip_ack_opener(t)
        assert not changed and out == t, t


def test_never_empties_a_one_sentence_answer():
    for a in ACK[:3]:
        out, changed = strip_ack_opener(a)
        assert not changed and out == a


def test_only_the_first_sentence_is_touched():
    t = BODY + " I hear how much weight this carries. Make one direct move."
    out, changed = strip_ack_opener(t)
    assert not changed and out == t


def test_polish_answer_applies_it_and_keeps_the_rest():
    pay = {"read": "Raman, I hear how much weight this question carries. " + BODY, "next": "Say what you need once, plainly."}
    polish_answer(pay, language="en", typed_question="Is this a temporary fight or a final break?", concern="love")
    assert pay["read"].startswith("The timing leans toward a temporary fight")
    assert "weight" not in pay["read"]


def test_real_answer_after_the_dash_is_kept():
    t = ("Harleen, you're carrying a lot right now — and the timing shows a real opening for a close partnership through late 2027. "
         "The person who fits reads as mature and dependable.")
    out, changed = strip_ack_opener(t)
    assert changed and out.startswith("The timing shows a real opening for a close partnership through late 2027.") and "carrying" not in out
    assert out.endswith("mature and dependable.")


def test_ordinary_first_sentences_with_similar_words_are_untouched():
    for t in ("Shashi, you're already married — so the real question is what the bond looks like from here. The timing is quiet.",
              "Your current life chapter strongly supports deepening the bond you already have — you're married, so the real question is how to strengthen it. Start now.",
              "The wait is long: the supportive window opens in March 2028. Until then it is groundwork.",
              "This is a hard stretch for money, and the window opens in March. Build the ground first."):
        out, changed = strip_ack_opener(t)
        assert not changed and out == t, t


def test_that_fear_is_real_keeps_the_answer_after_the_dash():
    t = "Andres, that fear is real — and the timing gives you a steady answer: yes, this marriage has the bones to last. The stretch is testing."
    out, changed = strip_ack_opener(t)
    assert changed and out.startswith("The timing gives you a steady answer") and "fear is real" not in out and "testing" in out
