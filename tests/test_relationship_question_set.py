"""Static integrity of the relationship question set (the live run is scripts/relationship_question_audit.py)."""
from tests.data.relationship_questions import GROUPS, LANES, QUESTIONS


def test_set_is_complete_and_unique():
    assert [x["id"] for x in QUESTIONS] == list(range(1, 56))
    assert len({x["q"] for x in QUESTIONS}) == 55


def test_every_row_is_tagged():
    for x in QUESTIONS:
        assert x["lane"] in LANES and x["group"] in GROUPS and x["q"].endswith("?") and x["key"]


def test_every_lane_is_exercised():
    assert {x["lane"] for x in QUESTIONS} == set(LANES)



def test_lane_checks_catch_third_party_claims():
    from tests.data.relationship_lane_checks import lane_checks
    item = {"id": 22, "lane": "reframe", "q": "Will he or she come back?"}
    assert "THIRD_PARTY_PREDICTION" in lane_checks(item, {"read": "She will come back in March. Try waiting.", "concern": "reconciliation"})
    assert "ACCUSATION" in lane_checks({"id": 24, "lane": "decline", "q": "x?"}, {"read": "He is cheating on you. You should ask.", "concern": "reconciliation"})
    assert lane_checks(item, {"read": "This season favours closure; you could decide by June.", "next": "Write down what you need.", "concern": "reconciliation"}) == []
    assert "ROUTE_OFF:career" in lane_checks(item, {"read": "You could decide.", "next": "x", "concern": "career"})
    assert "NO_WINDOW" in lane_checks({"id": 2, "lane": "serve", "q": "When will I get married?"}, {"read": "Soon.", "concern": "reconciliation"})
    assert "THIRD_PARTY_CHARACTER" in lane_checks({"id": 24, "lane": "decline", "q": "x?"}, {"read": "The person you're asking about reads as emotionally genuine. The friction is more about distance than deception.", "next": "x", "concern": "love"})
    assert "REUNION_OUTCOME" in lane_checks(item, {"read": "The timing actually does support a reconciliation right now.", "next": "x", "concern": "reconciliation"})
    assert "ACK_OPENER" in lane_checks(item, {"read": "Raman, this question matters - I understand that.", "next": "x", "concern": "reconciliation"})
    d = {"id": 24, "lane": "decline", "q": "x?"}
    assert "DECLINE_GIVES_VERDICT" in lane_checks(d, {"read": "Likely — opening Nov 2026.", "next": "x", "concern": "love"})
    assert "THIRD_PARTY_REFERENCE" in lane_checks(d, {"read": "Mixed signals are likely his way of processing.", "next": "x", "concern": "love"})
    assert "ASSUMES_AFFAIR" in lane_checks({"id": 31, "lane": "decline", "q": "x?"}, {"read": "The affair sits in a volatile stretch.", "next": "x", "concern": "divorce"})
    assert "CLARIFY_ASKED" in lane_checks(d, {"read": "Just so I read the right chart — which partner do you mean?", "concern": None})
    assert "OVER_PRECISE_TIMING" in lane_checks({"id": 23, "lane": "decline", "q": "When will he or she contact me?"}, {"read": "Expect contact within a few weeks.", "next": "x", "concern": "love"})


def test_template_reuse_flags_canned_branch():
    from tests.data.relationship_lane_checks import template_reuse
    rows = [{"id": i, "read": "You're divorced, so there are two separate questions here, and the timing answers them differently."} for i in (25, 27, 28)]
    assert template_reuse(rows) and not template_reuse(rows[:2])


def test_assumes_affair_only_when_the_asker_did_not_say_it():
    from tests.data.relationship_lane_checks import lane_checks
    row = {"read": "The affair puts you at a fork.", "next": "x", "concern": "love", "reframed": {"kind": "affair"}}
    assert "ASSUMES_AFFAIR" in lane_checks({"id": 31, "lane": "decline", "q": "Am I having an affair?"}, row)
    assert "ASSUMES_AFFAIR" not in lane_checks({"id": 32, "lane": "decline", "q": "Will my affair be exposed?"}, row)


def test_reframed_decline_answers_are_credited_and_unreframed_flagged():
    from tests.data.relationship_lane_checks import lane_checks
    q = {"id": 28, "lane": "decline", "q": "Is there a third person in my relationship?"}
    assert "REFRAME_MISSING" in lane_checks(q, {"read": "Fine.", "next": "x", "concern": "love"})
    assert "REFRAME_MISSING" not in lane_checks(q, {"read": "Fine.", "next": "x", "concern": "love", "reframed": {"kind": "trust"}})


def test_explicit_no_window_answers_a_timing_question():
    from tests.data.relationship_lane_checks import lane_checks
    q = {"id": 16, "lane": "serve", "q": "What month will I get engaged?"}
    base = {"next": "x", "concern": "marriage"}
    assert "NO_WINDOW" not in lane_checks(q, {**base, "read": "No strong partnership window in the next 24 months."})
    assert "NO_WINDOW" in lane_checks(q, {**base, "read": "Things look supportive in general."})
    assert "NO_WINDOW" not in lane_checks(q, {**base, "read": "Likely.", "timing": "Nov 2026 – Jan 2027"})


def test_dateless_sentence_is_flagged_and_dropped():
    from tests.data.relationship_lane_checks import lane_checks
    from antar_engine.answer_polish import polish_answer
    bad = "The next chapter, starting around, brings more natural warmth and expansion."
    assert "SENTENCE_BROKEN" in lane_checks({"id": 15, "lane": "serve", "q": "x?"}, {"read": bad, "next": "x", "concern": "marriage"})
    pay = {"read": "You are in a quiet stretch. " + bad + " It holds if you make the first move.", "next": "Reach out once."}
    polish_answer(pay, language="en", typed_question="Will I marry in this dasha or the next?", concern="marriage")
    assert "starting around," not in pay["read"] and "quiet stretch" in pay["read"] and "first move" in pay["read"]
    ok = {"read": "A window opens around March 2027. Then it eases.", "next": "x"}
    polish_answer(ok, language="en", typed_question="when?", concern="marriage")
    assert "around March 2027" in ok["read"]


def test_window_stated_in_prose_counts():
    from tests.data.relationship_lane_checks import lane_checks
    q = {"id": 15, "lane": "serve", "q": "Will I marry in this dasha or the next?"}
    assert "NO_WINDOW" not in lane_checks(q, {"read": "The strongest window runs right now through late 2027.", "next": "x", "concern": "marriage"})
    assert "NO_WINDOW" in lane_checks(q, {"read": "Partnership is possible but slow.", "next": "x", "concern": "marriage"})


def test_legitimate_about_comma_is_never_dropped_or_flagged():
    from tests.data.relationship_lane_checks import lane_checks
    from antar_engine.answer_polish import polish_answer
    ok = "Name the specific thing you want to talk about, not just catching up."
    assert "SENTENCE_BROKEN" not in lane_checks({"id": 22, "lane": "reframe", "q": "x?"}, {"read": ok, "next": ok, "concern": "love"})
    pay = {"read": "First sentence here. " + ok + " Third sentence here.", "next": "Reach out once."}
    polish_answer(pay, language="en", typed_question="x", concern="love")
    assert "talk about, not just" in pay["read"]


def test_decision_rule_and_own_move_wording_are_not_flagged():
    from tests.data.relationship_lane_checks import lane_checks
    q = {"id": 30, "lane": "reframe", "q": "Should I wait for him or her, or move on?"}
    ok = {"read": "Here is what the timing supports for each.\nRebuilding with your former spouse: the window opens Mar 2028.",
          "next": "Decide what you want and write it down this week.", "concern": "love"}
    assert lane_checks(q, ok) == []
    bad = {"read": "The timing actually does support a reunion right now.", "next": "x", "concern": "love"}
    assert "REUNION_OUTCOME" in lane_checks(q, bad)
    q2 = {"id": 23, "lane": "decline", "q": "When will he or she contact me?"}
    assert "OVER_PRECISE_TIMING" in lane_checks(q2, {"read": "Expect contact within a few weeks.", "next": "x", "concern": "love"})


def test_shared_lead_verdicts_are_not_template_reuse():
    from tests.data.relationship_lane_checks import template_reuse
    lead = "Likely within the year — the partnership window is Apr 2027 – Jun 2027. "
    rows = [{"id": i, "read": lead + body} for i, body in ((1, "You are in a quiet stretch for love."), (2, "A mentor introduces someone."), (3, "Work on trust first."))]
    assert not template_reuse(rows)
    canned = [{"id": i, "read": lead + "The same canned paragraph repeated word for word here."} for i in (1, 2, 3)]
    assert template_reuse(canned)
