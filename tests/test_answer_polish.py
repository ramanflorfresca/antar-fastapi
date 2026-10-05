"""[audit 2026-10-04] answer_polish — built from the conversation audit's classes."""
from antar_engine import answer_polish as ap


def test_jargon_to_plain_words():
    t = ap.plain_words("Your wealth engine is large but swings hard, and gains tend to dissolve. "
                       "Your grain runs strongest with research.", "en")
    assert "wealth engine" not in t and "earning power" in t and "grain" not in t
    assert "rises and falls sharply" in t and "slip away" in t and "you do best in research" in t
    assert "esfuman" in ap.plain_words("Las ganancias se disuelven rápido.", "es")


def test_spread_chart_drops_pick_one_move():
    p = {"read": "Raman, you do best in tech. Your network matters. Pick the one venture closest to a platform model.",
         "next": "Pick the one venture where your insight is the product and double down there."}
    ap.polish_answer(p, "en", "Which profession fits me best?", "career", "spread")
    assert "Pick the one venture" not in p["read"] and "Pick the one" not in p["next"] and p["next"]
    q = {"read": "a. b. Pick one venture.", "next": "Pick one venture."}
    ap.polish_answer(q, "en", "Should I pick one venture?", "career", "spread")   # they asked → untouched
    assert q["next"] == "Pick one venture."


def test_unasked_funding_dropped_but_kept_when_asked():
    p = {"read": "Abhi income pe pressure hai. Savings tight hai. Funding ke liye abhi sahi samay hai.",
         "next": "Aaj ek overdue payment collect karo."}
    ap.polish_answer(p, "hinglish", "Abhi mera paisa kaisa dikh raha hai?", "finance", "spread")
    assert "Funding" not in p["read"]
    q = {"read": "a. b. Funding opens in Oct.", "next": "Call two investors."}
    ap.polish_answer(q, "en", "When is the best time to raise funding?", "funding", "")
    assert "Funding" in q["read"] and q["next"] == "Call two investors."


def test_never_ship_without_a_move():
    for lang, concern in (("en", "career"), ("es", "finance"), ("hinglish", "love"), ("pt", "health")):
        p = {"read": "x. y. z.", "next": None}
        ap.polish_answer(p, lang, "q", concern, "")
        assert isinstance(p["next"], str) and len(p["next"].split()) >= 6
    c = {"read": "x", "next": None, "needs_clarification": True}
    ap.polish_answer(c, "en", "q", "career", "")
    assert c["next"] is None


def test_palette_has_no_personal_nouns_on_work_questions():
    from antar_engine.narration_contract import concern_to_noun_palette as pal
    for c in ("career", "finance", "general", "business"):
        got = set(pal(c, k=12, partnered=True))
        assert not got & {"partner", "spouse", "your home", "your mother", "presence"}, (c, got)
    assert "partner" in pal("love", k=10, partnered=True)


def test_aside_between_dashes_is_not_a_cut():
    from antar_engine.daily_prediction_engine import _looks_broken as lb
    assert not lb("Move a fixed share — 10% — of every payment into a separate account this week.")
    assert lb("Book the call — today")


def test_more_plain_words():
    t = ap.plain_words("Tech is on-grain for you. Your wealth capacity is real; bank gains as they land.", "en")
    assert "grain" not in t and "wealth capacity" not in t and "bank gains" not in t


def test_fragment_move_replaced_and_phrasal_end_kept():
    for frag in ("Before you spend anything on either venture.", "untouched by either venture."):
        p = {"read": "a. b. c.", "next": frag}
        ap.polish_answer(p, "en", "q", "finance", "")
        assert p["next"] != frag and len(p["next"].split()) >= 6
    ok = {"read": "a. b. c.", "next": "When the payment lands, move 10% into savings."}
    ap.polish_answer(ok, "en", "q", "finance", "")
    assert ok["next"].startswith("When the payment lands")
    import main
    assert main._ask_repair_next("Find someone you can rely on.") == "Find someone you can rely on."
    assert main._ask_repair_next("Send the deck to.") == "Send the deck."
