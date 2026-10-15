from antar_engine import today_decision as td


def _payload(best="12:23 PM – 1:11 PM", rahu="12:48 PM – 2:13 PM"):
    return {"evidence": {"chosen": ["money"], "lead_dir": "positive"}, "hora": {"best_window": best},
            "rahu_kalam": rahu, "moon_sign": "Leo", "dont_today": ["Don't stake what you can't afford to lose"],
            "do_today": ["Send the proposal"], "domains": [], "confidence": {"level": "high"}}


def test_best_window_never_overlaps_avoid():
    # best 12:23-1:11 vs avoid 12:48-2:13: only 12:23-12:48 is clear (25 min)
    assert td.clear_of("12:23 PM – 1:11 PM", "12:48 PM – 2:13 PM") == "12:23 PM – 12:48 PM"


def test_no_clear_time_left_drops_the_window():
    assert td.clear_of("1:00 PM – 1:30 PM", "12:48 PM – 2:13 PM") is None


def test_disjoint_windows_untouched():
    assert td.clear_of("9:00 AM – 10:00 AM", "12:48 PM – 2:13 PM") == "9:00 AM – 10:00 AM"


def test_unreadable_window_is_kept_not_guessed():
    assert td.clear_of("morning", "12:48 PM – 2:13 PM") == "morning"


def test_compose_holds_and_breaks_do_not_overlap():
    d = td.compose(_payload())
    assert d["window"]["best"] == "12:23 PM – 12:48 PM"
    assert "12:23 PM and 12:48 PM" in d["holds"]


def test_past_day_has_no_instructions_and_past_tense():
    d = td.compose(_payload(), "en", "past")
    assert d["relation"] == "past"
    assert d["prediction"].startswith("That day favoured")
    assert not any(k in d for k in ("holds", "breaks", "move"))


def test_future_day_keeps_the_plan_but_not_the_word_today():
    d = td.compose(_payload(), "en", "future")
    assert d["prediction"].startswith("That day favours")
    assert d["holds"] and d["breaks"] and d["relation"] == "future"


def test_today_unchanged():
    d = td.compose(_payload())
    assert d["prediction"].startswith("Today favours") and d["relation"] == "today"
