from antar_engine.answer_polish import polish_answer

READ = ("Your income and cash flow are solid this month. Bringing a new partner into this adds momentum without adding risk. "
        "One note: your earnings aren't keeping pace with the effort you and your partner are putting in right now. "
        "It holds if you build it through your network.")


def _run(q):
    return polish_answer({"read": READ, "next": "Commit only what you can afford to a new partner in writing."}, "en", typed_question=q)


def test_unasked_partner_sentences_dropped():
    out = _run("How does this month look for my money?")
    assert "partner" not in out["read"].lower()
    assert "income and cash flow" in out["read"]
    assert "partner" not in (out.get("next") or "").lower()


def test_kept_when_asked_about_partner():
    out = _run("Should I bring in a partner?")
    assert "new partner" in out["read"]
