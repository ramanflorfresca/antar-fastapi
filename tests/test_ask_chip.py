from antar_engine import ask_chip as AC

DAILY = {"verdict_subline": "A strong window for deals and direct conversation.",
         "observa_hoy_text": "Watch for a signal about money owed to you.",
         "signal": "A counterpart reaches out about a deal today — respond before midday to lock it in.",
         "decision": {"prediction": "Today favours income.", "why": "The Moon is in Scorpio. It lights your 11th house.",
                      "holds": "It holds if the decision goes between 12:16 PM and 12:41 PM.",
                      "breaks": "It breaks if you force a decision between 12:41 PM and 2:04 PM.", "move": "x"}}

PERIOD = {"summary": "Partnership and business and money lead. Business and money need care.",
          "do": [{"area": "Love", "text": "Put time into the relationship."}],
          "avoid": [{"area": "Money", "text": "Loss of wealth is possible.", "instead": "Hold off on big spending."}],
          "best_week": {"title": "Best week", "label": "Oct 15 to Oct 21", "text": "Take the important asks here."}}


def test_only_the_home_focus_chips_are_matched_whatever_the_spacing_and_case():
    assert AC.chip_scope("What is the one thing I should focus on today?") == "today"
    assert AC.chip_scope("  what is the ONE thing I should focus on   this month? ") == "month"
    assert AC.chip_scope("What is the one thing I should focus on this year?") == "year"
    assert AC.chip_scope("¿En qué debo enfocarme hoy?") == "today"
    assert AC.chip_scope("What should I focus on today and tomorrow?") is None
    assert AC.chip_scope("Will I get the deal?") is None and AC.chip_scope("") is None and AC.chip_scope(None) is None


def test_the_today_answer_is_homes_own_text_word_for_word():
    a = AC.answer_today(DAILY)
    assert a["next"] == DAILY["signal"]                                            # the same "Your move" Home shows
    assert a["read"] == DAILY["verdict_subline"] + " " + DAILY["observa_hoy_text"]  # the same "Today's read"
    assert a["mode"] == "explore" and a["source"] == "daily" and a["locked"] is False


def test_the_today_decision_block_carries_what_holds_and_breaks_but_never_the_why():
    d = AC.answer_today(DAILY)["decision"]
    assert d["holds"] == DAILY["decision"]["holds"] and d["breaks"] == DAILY["decision"]["breaks"] and d["move"] == DAILY["signal"]
    assert "why" not in d and "house" not in str(d).lower()


def test_a_missing_field_or_a_pending_payload_falls_back_to_the_full_ask():
    assert AC.answer_today({}) is None and AC.answer_today(None) is None
    assert AC.answer_today({**DAILY, "pending": True}) is None
    assert AC.answer_today({**DAILY, "signal": ""}) is None and AC.answer_today({**DAILY, "verdict_subline": ""}) is None


def test_the_month_and_year_answers_come_from_the_period_composer():
    a = AC.answer_period(PERIOD, "month")
    assert a["source"] == "period" and a["chip"] == "focus_month" and a["next"] == "Put time into the relationship."
    assert a["read"].endswith("Best week: Oct 15 to Oct 21.") and a["read"].startswith(PERIOD["summary"])
    assert a["decision"]["breaks"] == "Loss of wealth is possible. Hold off on big spending."
    assert AC.answer_period({**PERIOD, "do": []}, "year") is None and AC.answer_period({}, "year") is None
