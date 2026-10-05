from antar_engine.answer_polish import scrub_register


def test_reading_becomes_timing_everywhere():
    p = {"read": "The reading leans your way. Your reading doesn't support speculation. This reading is steady.",
         "next": "Wait — the reading says hold.", "actions": ["Trust the reading."]}
    scrub_register(p, "en")
    blob = " ".join([p["read"], p["next"], *p["actions"]]).lower()
    assert "reading" not in blob
    assert "The timing leans your way." in p["read"] and "Your timing doesn't" in p["read"]


def test_body_strength_reassurance_dropped_clause_kept():
    p = {"read": "Not yet — next health window Dec 2026. The reading shows your constitution is robust, but a recurring pattern of passing illness is active. These bouts come and go."}
    scrub_register(p, "en")
    assert "robust" not in p["read"] and "reading" not in p["read"]
    assert "A recurring pattern of passing illness is active." in p["read"]
    assert "Dec 2026" in p["read"]


def test_whole_reassurance_sentence_dropped():
    p = {"read": "A window opens in March. Your constitution tends toward passing flare-ups rather than deep structural problems, which is genuinely good news. Rest more."}
    scrub_register(p, "en")
    assert "structural" not in p["read"] and "good news" not in p["read"]
    assert "March" in p["read"] and "Rest more." in p["read"]


def test_other_languages_untouched_and_never_empties():
    p = {"read": "La lectura dice algo."}
    assert scrub_register(dict(p), "es") == p
    q = {"read": "Your body is strong."}
    scrub_register(q, "en")
    assert q["read"].strip()
