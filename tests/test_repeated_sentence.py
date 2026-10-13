from antar_engine.answer_polish import drop_repeated_sentences

READ = ("The timing supports gains from speculation, and the window is open now. "
        "Open means possible, not safe: your gains tend to arrive in bursts and give some of it back. "
        "Keep it capped: only an amount you can afford to lose. "
        "Your gains tend to come in bursts and give some of it back, so take what you set out to take and stop. "
        "The risk is position size growing past what you can afford to lose.")


def test_repeated_idea_is_dropped_once():
    out, changed = drop_repeated_sentences(READ)
    assert changed
    assert out.lower().count("give some of it back") == 1
    assert "Keep it capped" in out and "The risk is position size" in out


def test_distinct_sentences_untouched():
    t = "Your income is supported this month. The drag is on savings. It holds if you grow income through your network."
    assert drop_repeated_sentences(t) == (t, False)


def test_never_below_two_sentences():
    t = "Keep every position small and capped always. Keep every position small and capped always."
    assert drop_repeated_sentences(t) == (t, False)


def test_polish_dedupes_after_conditions_block(monkeypatch):
    from antar_engine import answer_polish as ap
    import antar_engine.ask_basis as ab
    monkeypatch.setattr(ab, "conditions", lambda *a, **k: "Keep it capped: only an amount you can afford to lose. Your gains tend to come in bursts and give some of it back, so take what you set out to take and stop.")
    payload = {"read": "The timing supports gains from speculation, and the window is open now. Open means possible, not safe: your gains tend to arrive in bursts and give some of it back.",
               "next": "Set the most you can afford to lose and stop at that number."}
    out = ap.polish_answer(payload, "en", typed_question="Is this a good time to speculate?", concern="speculation")
    assert out["read"].lower().count("give some of it back") == 1
