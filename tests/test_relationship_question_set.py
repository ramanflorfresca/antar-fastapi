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
