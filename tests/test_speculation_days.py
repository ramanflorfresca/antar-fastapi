"""Day-level speculation from the Today data (owner 2026-10-03)."""
from antar_engine import speculation_days as sd

HOLD = "Hold off on new spending or speculative money moves — timing isn't with you."
THREAD = "Money is the week's recurring thread — most decisions circle back to it, so handle it deliberately."
TAIL = "Money matters carry tailwind — chase payments, send invoices, ask for what you're owed."


def _d(date, day, label, money="", peak=("11:30 AM", "12:15 PM")):
    return {"date": date, "day": day, "verdict_label": label,
            "highlights": ([{"domain": "money", "text": money}] if money else []),
            "windows": [{"start": peak[0], "end": peak[1], "type": "peak"}]}


# the owner's real week (Oct 3-9 2026)
WEEK = [_d("2026-10-03", "Saturday", "Caution", HOLD), _d("2026-10-04", "Sunday", "High", THREAD, ("11:32 AM", "12:20 PM")),
        _d("2026-10-05", "Monday", "High", THREAD), _d("2026-10-06", "Tuesday", "Good", TAIL),
        _d("2026-10-07", "Wednesday", "Caution"), _d("2026-10-08", "Thursday", "Good"),
        _d("2026-10-09", "Friday", "Neutral", peak=("12:19 PM", "2:46 PM"))]


def test_best_day_matches_today_not_a_second_calculation():
    a = sd.week_answer(WEEK)
    assert "Sunday 4 Oct" in a["read"] and "11:32 AM–12:20 PM" in a["read"]
    assert "Friday 9 Oct" not in a["read"]                      # the old answer's pick (Today: Neutral)
    assert "Most strained: Saturday 3 Oct" in a["read"] and a["timing"] == "Sunday 4 Oct"


def test_scoring_rules():
    assert sd.score(_d("2026-10-03", "Saturday", "Caution", HOLD)) == -1
    assert sd.score(_d("2026-10-06", "Tuesday", "Good", TAIL)) == 2.5
    assert sd.score(_d("2026-10-04", "Sunday", "High", THREAD)) == 3


def test_no_standout_week_is_said_plainly():
    flat = [_d(f"2026-10-0{i}", "Mon", "Neutral") for i in range(3, 8)]
    a = sd.week_answer(flat)
    assert "No standout day" in a["read"] and a["timing"] == ""


def test_today_and_tomorrow():
    t = sd.specific_day(WEEK, "today")
    assert "Saturday 3 Oct is a strained day" in t["read"] and "sit it out" in t["read"]
    tm = sd.specific_day(WEEK, "tomorrow")
    assert "Sunday 4 Oct reads as a supportive day (11:32 AM–12:20 PM)" in tm["read"]
    assert sd.which_day("Is tomorrow a good day to trade crypto?") == "tomorrow"
    assert sd.which_day("hoy es buen día para operar") == "today" and sd.which_day("Which day this week?") is None


def test_languages_and_missing_data():
    es = sd.week_answer(WEEK, "es")
    assert "Mejor día de esta semana" in es["read"] and "domingo 4 oct" in es["read"]
    pt = sd.week_answer(WEEK, "pt")
    assert "Melhor dia desta semana" in pt["read"] and "domingo 4 out" in pt["read"]
    assert sd.week_answer([]) is None and sd.specific_day([], "today") is None


def test_no_banned_planet_word_in_the_labels():
    from antar_engine.narration_validator import validate_narration
    for lang in ("en", "es", "pt"):
        a = sd.week_answer(WEEK, lang)
        assert not validate_narration(a["read"], language="en") or all(
            "planet_name" not in str(v) for v in validate_narration(a["read"], language="en")), lang
        assert "Sun " not in a["read"]
