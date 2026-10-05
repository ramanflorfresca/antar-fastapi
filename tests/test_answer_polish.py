"""[audit 2026-10-04] answer_polish — built from the conversation audit's classes."""
from antar_engine import answer_polish as ap


def test_jargon_to_plain_words():
    t = ap.plain_words("Your wealth engine is large but swings hard, and gains tend to dissolve. "
                       "Your grain runs strongest with research.", "en")
    assert "wealth engine" not in t and "earning power" in t and "grain" not in t
    assert "rises and falls sharply" in t and "slip away" in t and "you do best in research" in t.lower()
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


def test_b3_openers_acknowledge_and_wider_pick_one():
    from antar_engine import wealth_magnitude as wm
    r = wm.apply_alloc_opener("Raman, cap it. Keep a reserve. Add a line later.", "spread_single", "en", "Raman")
    assert r.startswith("Raman, the reading says spread your risk")
    p = {"read": "a. b. One clear mandate beats three half-built ventures.", "next": "Pick the one active work stream and double down there."}
    ap.polish_answer(p, "en", "Which profession fits me best?", "career", "spread")
    assert "half-built" not in p["read"] and "double down" not in p["next"]
    m = {"read": "a. b. c.", "next": None}
    ap.polish_answer(m, "en", "I am all in", "finance", "spread")
    assert "10%" in m["next"]
    h = ap.plain_words("Gains dissolve ho jaate hain. Tera wealth engine strong hai.", "hinglish")
    assert "dissolve" in h and "wealth engine" not in h


def test_scrub_payload_timing_only_leaves_next_alone():
    import main
    p = {"read": "x.", "next": "Move 10% of every payment into a separate account this week — treat it as untouchable.",
         "timing": None}
    main._ask_scrub_payload(p, ["timing"], language="en")
    assert p["next"].startswith("Move 10% of every payment")
    m = {"read": "a. b. c.", "next": None}
    ap.polish_answer(m, "en", "I am 100% all in on Antar", "general", "spread")
    assert "10%" in m["next"]


def test_b4_receivables_backing_and_wider_pick_one():
    p = {"read": "Income is supported. The reading shows pressure on savings. Collect what you're already owed first.",
         "next": "Name the single oldest unpaid amount owed to you and chase it this week."}
    ap.polish_answer(p, "en", "How is my money looking right now?", "finance", "")
    assert "owed" not in p["read"] and "owed" not in p["next"]
    assert "10%" in p["next"] or "outflows" in p["next"]   # a money move: the answer says savings are pressured → outflow cut
    q = {"read": "a. b. You're owed money from March.", "next": "Chase what you're owed."}
    ap.polish_answer(q, "en", "A client owes me money from March — what's owed to me?", "finance", "")
    assert "owed" in q["next"]
    r = {"read": "a. b. Money through backing or outside money looks good.", "next": "Track your costs this week carefully."}
    ap.polish_answer(r, "en", "How is my money?", "finance", "")
    assert "backing" not in r["read"]
    for t in ("Pick the one client-facing or investigative project in your business and put your best effort there.",
              "Elige el campo más cercano a lo que ya haces y lleva esa pieza al frente.",
              "Channel it into one clear leadership role."):
        s = {"read": "a. b. c.", "next": t}
        ap.polish_answer(s, "en", "Which profession fits me best?", "career", "spread")
        assert s["next"] != t, t


def test_b4_definitions():
    from antar_engine import wealth_magnitude as wm
    assert "OUTSIDE your ventures" in wm.LEAN_DIRECTIVE["spread"] and "start more ventures" in wm.LEAN_DIRECTIVE["spread"]
    assert "capped or paused" in wm.LEAN_DIRECTIVE["concentrate"]
    from antar_engine.narration_contract import concern_to_noun_palette as pal
    assert not set(pal("finance", k=15, partnered=True)) & {"other people's money", "inheritance", "windfall", "debt"}
