"""[ritual-today 2026-10-14] the plain-language Ritual payload: gated colour of the day, hidden-not-generic cards,
no jargon, no internal fields."""
from datetime import date

from antar_engine import ritual_today as RT

LK_YEAR = {
    "verdict": "mixed",
    "remedies": ["Keep a fast on Sundays.", "Recite the Gayatri mantra regularly.", "Keep a fast on Wednesdays.",
                 "Never take free electrical goods, blue clothing or steel."],
    "what_to_avoid": ["Don't force big moves in your work, money and communication this year."],
    "gemstones": {"timed": [{"stone": "emerald", "metal": "gold", "finger": "little finger",
                             "why": "the part of you that governs your work is under strain this year"}],
                  "lifelong": {"stone": "Diamond", "metal": "silver/platinum", "finger": "little finger",
                               "why": "Strengthens the engine of your strong years."}},
}
WD = {"Moon": ["White", "Silver"], "Mars": ["Red"], "Mercury": ["Green"], "Jupiter": ["Yellow", "Gold"],
      "Venus": ["White", "Pink", "Sky Blue"], "Saturn": ["Black", "Dark Blue"], "Sun": ["Orange", "Gold"],
      "Rahu": [], "Ketu": []}
FAVOUR_ONLY = {"white", "pink", "sky blue"}     # this chart: only the Venus colours work; blue is refused by the year read


def _assess(nm):
    k = nm.lower()
    if k in FAVOUR_ONLY:
        return "favor"
    if k in ("black", "dark blue", "blue"):
        return "avoid"
    return "neutral"


def _compose(d, **kw):
    base = dict(
        today=d, language="en", chart={"id": "c1"}, lk=None, schedule={"lal_kitab": {"year": LK_YEAR}},
        wisdom={"season": "expansive", "why_now": "You're in a push-forward phase.",
                "verse": {"source": "Bhagavad Gita 3.8", "sanskrit": "x", "translation": "Do the work that is yours."},
                "mantra": {"name": "Om Gam Ganapataye Namaha", "use": "Chant 11 times before you begin."}},
        daily={"food": {"eat": ["Black sesame"], "avoid": ["Cold foods"], "texture": "warm, grounding",
                        "why_eat": "These foods feed your endurance."}, "decision": {"prediction": "Steady day."}},
        vastu={"available": True, "directions": {
            "sleep_head": {"zone": "S", "label": "South", "status": "steady", "why": "the traditional default stands"},
            "work_facing": {"zone": "N", "label": "North", "why": "the traditional default stands"},
            "eat_facing": {"zone": "N", "label": "North", "why": "the traditional default stands"}}},
        natal_mat={"favorable": [{"color": "White/Pink/Sky Blue", "gem": "Diamond", "metal": "Silver", "why": "x"}],
                   "avoid": []},
        year_mat={"favor": [], "avoid": []}, nak_lord="Saturn", completed_ids=set(), streak=0, longest=0,
        assess=_assess, weekday_colours=WD, caution="Check with a qualified jeweller-astrologer.")
    base.update(kw)
    return RT.compose(**base)


def test_colour_of_the_day_is_never_an_avoid_colour_over_a_year():
    for i in range(365):
        d = date.fromordinal(date(2026, 1, 1).toordinal() + i)
        c = _compose(d)["colour_of_the_day"]
        assert c is None or _assess(c["name"]) != "avoid"
        assert c is None or c["name"].lower() not in ("blue", "sky blue", "dark blue", "black")


def test_year_read_refusal_beats_a_favourable_natal_colour():
    wear = _compose(date(2026, 10, 14))["cards"]["wear"]
    names = [c["name"].lower() for c in wear["for_life"]["colors"]]
    assert "sky blue" not in names and "pink" in names     # "never ... blue clothing" removes sky blue too


def test_skip_today_lists_the_weekday_colour_that_failed_the_gate():
    wear = _compose(date(2026, 10, 17))["cards"]["wear"]    # Saturday: the weekday colours are black / dark blue
    assert {s["name"].lower() for s in wear["today"]["skip_today"]} >= {"black", "dark blue"}


def test_colour_moves_with_the_weekday_when_the_weekday_colour_suits_the_chart():
    allowed = FAVOUR_ONLY | {"green"}
    def a(nm):
        return "favor" if nm.lower() in allowed else _assess(nm)
    wed = _compose(date(2026, 10, 14), assess=a)["colour_of_the_day"]
    fri = _compose(date(2026, 10, 16), assess=a)["colour_of_the_day"]
    assert wed["name"] == "Green" and fri["name"] != "Green"       # Wednesday ruler's colour, Friday's own


def test_no_eligible_colour_gives_none_not_a_generic_one():
    c = _compose(date(2026, 10, 14), assess=lambda nm: "avoid", natal_mat={})["cards"]["wear"]
    assert _compose(date(2026, 10, 14), assess=lambda nm: "avoid", natal_mat={})["colour_of_the_day"] is None
    assert c["status"] in ("ready", "hidden")


def test_remedy_is_an_action_for_today_never_a_refusal_rule():
    for i in range(14):
        d = date.fromordinal(date(2026, 10, 12).toordinal() + i)
        r = _compose(d)["cards"]["remedy"]
        assert r["status"] == "ready" and not r["title"].lower().startswith(("never", "don't", "avoid"))
    assert "Wednesday" in _compose(date(2026, 10, 14))["cards"]["remedy"]["title"]
    assert _compose(date(2026, 10, 14))["cards"]["remedy"]["cadence_label"] == "Every Wednesday"


def test_cards_without_a_real_source_are_hidden_and_progress_counts_only_ready_cards():
    p = _compose(date(2026, 10, 14), vastu={"available": False}, wisdom={}, daily={})
    assert p["cards"]["space"]["status"] == p["cards"]["mantra"]["status"] == p["cards"]["verse"]["status"] == "hidden"
    assert p["cards"]["food"]["status"] == "hidden"
    assert p["progress"]["total"] == sum(1 for c in p["cards"].values() if c["status"] == "ready")


def test_jargon_strings_are_dropped_not_shown():
    assert RT.clean("Saturn is strong in your 8th house") is None
    assert RT.clean("Your Lal Kitab year says") is None
    assert RT.clean("Keep a fast on Sundays.") == "Keep a fast on Sundays."
    p = _compose(date(2026, 10, 14), daily={"food": {"eat": ["Sesame", "Saturn foods"], "avoid": [], "texture": "warm"}})
    assert p["cards"]["food"]["eat"] == ["Sesame"]


def test_the_stripped_payload_has_no_internal_fields_and_no_jargon():
    s = RT.strip_internal(_compose(date(2026, 10, 14)))
    assert "why_chart" not in str(s) and "_colour_of_the_day" not in str(s)
    assert RT.jargon_leaks(s) == []


def test_done_cards_count_toward_progress():
    p = _compose(date(2026, 10, 14), completed_ids={"wear_today", "food_today"})
    assert p["progress"]["done"] == 2


def test_same_planet_weekday_and_moon_star_is_one_signal():
    # Saturday ruler == Saturn == the Moon-star ruler: the colour basis names it once, never twice
    c = RT.pick_colour_of_the_day(date(2026, 10, 17), "Saturn", [], lambda n: "favor", set(), WD)["colour"]
    assert c["basis"] == "weekday_ruler:saturn"
