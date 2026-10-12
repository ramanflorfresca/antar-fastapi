from antar_engine import ask_subject_person as asp

CHART = {"lagna": {"sign": "Aries"}, "planets": {
    "Sun": {"sign": "Aries", "house": 1, "degree": 10.0}, "Moon": {"sign": "Cancer", "house": 4, "degree": 5.0},
    "Mars": {"sign": "Aries", "house": 1, "degree": 20.0}, "Mercury": {"sign": "Pisces", "house": 12, "degree": 3.0},
    "Jupiter": {"sign": "Sagittarius", "house": 9, "degree": 12.0}, "Venus": {"sign": "Taurus", "house": 2, "degree": 8.0},
    "Saturn": {"sign": "Capricorn", "house": 10, "degree": 25.0}, "Rahu": {"sign": "Gemini", "house": 3, "degree": 9.0},
    "Ketu": {"sign": "Sagittarius", "house": 9, "degree": 9.0}}}


def test_trait_kind():
    for q, k in (("Will my spouse be rich?", "money"), ("Is my wife good with money?", "money"), ("¿Será rico mi esposo?", "money"),
                 ("What will my spouse's profession be?", "work"), ("What is my wife's career going to be?", "work"),
                 ("Will my spouse be dominating?", "temperament"), ("What is my husband like?", "temperament"),
                 ("Is my wife calm?", "temperament")):
        assert asp.trait_kind(q) == k, q
    for q in ("When will my son get married?", "How is Amik doing?", "Will my wife get the visa?", "Is my husband healthy?"):
        assert asp.trait_kind(q) is None, q


def test_money_word_wins_over_the_marriage_word():
    assert asp.person_concern("marriage", "Will my spouse be rich?") == "income"
    assert asp.person_concern("love", "Is my wife good with money?") == "income"
    assert asp.person_concern("marriage", "When will my son get married?") == "relationship_entry"     # unchanged
    assert asp.person_concern("health", "How is my wife's health?") == "health"                            # unchanged


def test_money_question_gets_the_income_reader_not_the_entry_window():
    f = asp.build_person_facts("Sudha", "partner", "Will my spouse be rich?", "marriage", CHART, {}, None, "state")
    assert f["available"] and f["trait"] == "money" and f["concern_key"] == "income"
    assert "your income and cash flow" in f["facts"] and "significant person entering" not in f["facts"]


def test_temperament_sheet_is_a_tendency_with_reasons():
    f = asp.build_person_facts("Sudha", "partner", "Will my spouse be dominating?", "marriage", CHART, {}, None, "state")
    assert f["trait"] == "temperament" and f["concern_key"] is None
    t = f["facts"]
    assert "rising sign (Aries)" in t and "emotional nature (Moon in Cancer)" in t
    assert "TENDENCY of assertiveness: firm and strong-willed" in t                    # Sun + Mars on the self-house, firm rising sign
    assert "significant person entering" not in t


def test_gentle_chart_reads_gentle():
    soft = {"lagna": {"sign": "Pisces"}, "planets": {
        "Moon": {"sign": "Taurus", "house": 3, "degree": 5.0}, "Venus": {"sign": "Pisces", "house": 1, "degree": 8.0},
        "Jupiter": {"sign": "Pisces", "house": 1, "degree": 12.0}, "Sun": {"sign": "Virgo", "house": 8, "degree": 3.0},
        "Mars": {"sign": "Libra", "house": 9, "degree": 3.0}, "Saturn": {"sign": "Taurus", "house": 3, "degree": 3.0},
        "Mercury": {"sign": "Virgo", "house": 8, "degree": 3.0}, "Rahu": {"sign": "Cancer", "house": 5, "degree": 3.0},
        "Ketu": {"sign": "Capricorn", "house": 11, "degree": 3.0}}}
    f = asp.build_person_facts("Dana", "partner", "Is my wife calm?", "general", soft, {}, None, "state")
    assert "gentle and accommodating" in f["facts"]


def test_work_sheet_names_a_tendency_not_a_verdict():
    cd = dict(CHART, divisional_charts={"d10": {"lagna": "Scorpio", "planets": {
        "Sun": {"sign": "Scorpio", "house": 1}, "Moon": {"sign": "Scorpio", "house": 1}, "Mars": {"sign": "Aries", "house": 6},
        "Mercury": {"sign": "Virgo", "house": 9}, "Jupiter": {"sign": "Cancer", "house": 10}, "Venus": {"sign": "Libra", "house": 12},
        "Saturn": {"sign": "Capricorn", "house": 3}, "Rahu": {"sign": "Gemini", "house": 8}, "Ketu": {"sign": "Sagittarius", "house": 2}}}})
    f = asp.build_person_facts("Sudha", "partner", "What will my spouse's profession be?", "marriage", cd, {}, None, "state")
    assert f["trait"] == "work" and f["concern_key"] is None and "tendency" in f["facts"].lower()
    assert "not a verdict on fit or success" in f["facts"]


def test_narrator_block_carries_the_trait_rule():
    for trait, must in (("money", "NEVER state a wealth level"), ("work", "never name one job as fact"),
                        ("temperament", "what this means for the reader")):
        assert must in asp.narrator_block("Sudha", "partner", "en", trait=trait), trait
    assert "NEVER state a wealth level" not in asp.narrator_block("Sudha", "partner", "en")
    assert asp.narrator_block("Sudha", "partner", "es", trait="money").count("Spanish") == 1


def test_non_trait_questions_are_unchanged():
    f = asp.build_person_facts("Amik", "child", "When will my son get married?", "marriage", CHART, {}, None, "timing")
    assert f["trait"] is None and f["concern_key"] == "relationship_entry"


def test_person_read_drops_jargon_sentences_but_keeps_two_clean_ones():
    t = ("Sudha tends to be firm and structured. Capricorn rising brings a natural authority. Venus sits in its own sign in the career zone. "
         "She tends to hold her ground on things that matter to her security.")
    out = asp.guard_read(t, "Sudha")
    assert "Capricorn" not in out and "Venus" not in out
    assert "firm and structured" in out and "hold her ground" in out


def test_jargon_is_kept_rather_than_leaving_an_empty_or_one_line_answer():
    t = "Venus sits in its own sign. Sudha tends to be steady."
    out = asp.guard_read(t, "Sudha")
    assert "Venus sits in its own sign" in out and "steady" in out         # only one clean sentence left: no drop


def test_possessive_relation_word_reaches_the_person():
    from antar_engine import ask_subject as AS
    people = [{"name_b": "Sudha", "chart_id_b": "c1", "compat_type": "spouse", "relation_detail": "wife"}]
    r = AS.resolve_subject("What will my spouse's profession be?", "me", people)
    assert r["subject"] == "person" and r["person"]["name"] == "Sudha"
    r = AS.resolve_subject("What is my wife's income?", "me", people)
    assert r["subject"] == "person"


def test_internal_verdict_label_and_orphaned_pronoun():
    t = ("The chart reading for Sudha comes back as \"supported, conditionally\" — which is an honest middle ground. "
         "Her earning pattern is steady and built through work. She tends to save more than she spends.")
    out = asp.guard_read(t, "Sudha")
    assert "supported, conditionally" not in out and "reading for" not in out
    assert out.startswith("Sudha's earning pattern is steady")


def test_possessive_spouse_narrows_to_the_romantic_person_not_the_business_partner():
    from antar_engine import ask_subject as AS
    people = [{"name_b": "Sudha", "chart_id_b": "c1", "compat_type": "spouse", "relation_detail": "wife"},
              {"name_b": "Rakesh", "chart_id_b": "c2", "compat_type": "business"}]
    r = AS.resolve_subject("What will my spouse's profession be?", "me", people)
    assert r["subject"] == "person" and r["person"]["name"] == "Sudha"
