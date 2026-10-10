from datetime import date

import pytest

from antar_engine import remedy_schedule as RS

SAT = date(2026, 10, 10)          # a Saturday


def _resp(**tp):
    return {"today_priority": tp, "active": [{"cadence": "daily_tunein"}, {"cadence": "varshphal_scale"}]}


def test_food_gets_a_verb_title_weekly_frequency_and_the_next_friday():
    r = RS.annotate_practice_response(_resp(food={
        "one_line": "your love and partnership energy wants sweet, fragrant, dairy-rich foods — eat to feed beauty.",
        "best_day": "Friday", "why_for_this_user": "this year highlights love."}), SAT)
    f = r["today_priority"]["food"]
    assert f["title"] == "Eat sweet, fragrant, dairy-rich foods on Fridays"
    assert (f["frequency"], f["frequency_label"], f["optional"], f["weekday"]) == ("weekly", "Every Friday", False, 5)
    assert f["next_date"] == "2026-10-16"
    assert f["one_line"].startswith("Your love and partnership")        # leading lowercase fixed
    assert f["why_for_this_user"].startswith("This year")


def test_today_counts_when_the_weekday_matches():
    r = RS.annotate_practice_response(_resp(food={"one_line": "x wants y.", "best_day": "Saturday"}), SAT)
    assert r["today_priority"]["food"]["next_date"] == "2026-10-10"


def test_gemstone_is_once_optional_with_no_date():
    r = RS.annotate_practice_response(_resp(gemstone={"name": "Diamond", "why": "w"}), SAT)
    g = r["today_priority"]["gemstone"]
    assert (g["title"], g["frequency"], g["frequency_label"], g["optional"]) == ("Wear your diamond", "once", "Set up once", True)
    assert g["weekday"] is None and g["next_date"] is None


def test_giving_and_fast_are_weekly_and_fast_is_optional():
    r = RS.annotate_practice_response(_resp(
        giving={"one_line": "Give sweet, white things to women and artists — on Friday.", "day": "Friday"},
        fast={"one_line": "Voluntary restraint on Friday — one white meal.", "day": "Friday"}), SAT)
    g, f = r["today_priority"]["giving"], r["today_priority"]["fast"]
    assert g["title"] == "Give sweet, white things to women and artists" and g["optional"] is False
    assert f["title"] == "Fast gently on Fridays" and f["optional"] is True
    assert g["next_date"] == f["next_date"] == "2026-10-16"


def test_yantra_is_a_one_time_setup():
    r = RS.annotate_practice_response(_resp(energy_diagram={"name": "Shukra Yantra"}), SAT)
    y = r["today_priority"]["energy_diagram"]
    assert y["title"] == "Set up your Shukra Yantra" and y["frequency"] == "once" and y["optional"] is True


@pytest.mark.parametrize("day,wd", [("Friday", 5), ("viernes", 5), ("Viernes", 5), ("sexta-feira", 5), ("sexta", 5),
                                    ("miércoles", 3), ("miercoles", 3), ("domingo", 7), ("Someday", None), (None, None)])
def test_weekday_names_parse_across_languages(day, wd):
    assert RS.weekday_number(day) == wd


def test_translated_day_still_schedules():
    r = RS.annotate_practice_response(_resp(food={"one_line": "tu energía quiere dulces.", "best_day": "Viernes"}), SAT, "es")
    f = r["today_priority"]["food"]
    assert f["next_date"] == "2026-10-16" and f["frequency_label"] == "Cada viernes"


def test_active_items_get_a_frequency():
    r = RS.annotate_practice_response(_resp(), SAT)
    assert [a["frequency"] for a in r["active"]] == ["daily", "period"]


def test_never_raises_on_odd_input():
    for bad in (None, {}, {"today_priority": None}, {"today_priority": {"food": "x"}}, {"today_priority": {"food": {"best_day": 5}}}):
        RS.annotate_practice_response(bad, SAT)


def test_a_remedy_with_no_weekday_is_not_scheduled():
    r = RS.annotate_practice_response(_resp(food={"one_line": "wants y."}), SAT)
    f = r["today_priority"]["food"]
    assert f["frequency"] == "once" and f["next_date"] is None
