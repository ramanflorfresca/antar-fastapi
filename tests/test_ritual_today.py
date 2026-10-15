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
    assert p["progress"]["total"] == sum(1 for c in p["cards"].values() if c["status"] == "ready" and c["kind"] == "action")


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


def test_only_action_cards_count_toward_progress_and_info_cards_have_no_tick():
    p = _compose(date(2026, 10, 14), completed_ids={"wear_today", "food_today"})
    kinds = {k: c["kind"] for k, c in p["cards"].items()}
    assert kinds["wear"] == kinds["verse"] == kinds["space"] == kinds["food"] == "info"
    assert kinds["mantra"] == "action" and kinds["remedy"] == "action"       # Wednesday: the fast is due
    assert p["progress"]["done"] == 0 and p["progress"]["total"] == 2
    q = _compose(date(2026, 10, 14), completed_ids={p["cards"]["mantra"]["practice_id"], p["cards"]["remedy"]["practice_id"]})
    assert q["progress"] == {"done": 2, "total": 2}


def test_a_remedy_that_is_next_on_another_day_is_information_not_a_task():
    assert RT.card_kind("remedy", {"status": "ready", "cadence_label": "Next on Wednesday"}, date(2026, 10, 15)) == "info"
    assert RT.card_kind("remedy", {"status": "ready", "cadence_label": "Every Wednesday"}, date(2026, 10, 14)) == "action"
    assert RT.card_kind("remedy", {"status": "ready", "cadence_label": "Keep it up through the year"}, date(2026, 10, 15)) == "action"


def test_why_plan_lines_are_plain_and_not_repeated():
    p = _compose(date(2026, 10, 14))
    lines = p["why_plan"]["lines"]
    assert lines and len(lines) == len(set(lines))
    assert RT.jargon_leaks(p["why_plan"]) == []


def test_mantra_prefers_the_focus_mantra_with_its_audio():
    practice = {"today_priority": {"mantra": {"advanced": {"transliteration": "OM SHAM SHANAISHCHARAYA NAMAHA"}, "count": 108,
                                              "when": "Before sunset", "why": "It steadies the mind.", "tone_hz": 295,
                                              "audio_url": "https://x/saturn-en.mp3"}}}
    c = RT.mantra_card({}, set(), practice)
    assert c["status"] == "ready" and c["audio_url"].endswith("saturn-en.mp3") and c["tone_hz"] == 295
    assert c["repeats"] == 11 and c["full_count"] == 108 and c["best_time_plain"] == "Before sunset"
    # no audio on the practice mantra: fall back to the season mantra
    assert RT.mantra_card({"mantra": {"name": "Om Gam Ganapataye Namaha", "use": "Chant 11 times."}}, set(), {"today_priority": {"mantra": {"name": "x"}}})["text_roman"] == "Om Gam Ganapataye Namaha"


def test_space_card_has_an_about_line_and_no_lowercase_default_sentence():
    p = _compose(date(2026, 10, 14))
    sp = p["cards"]["space"]
    assert sp["about_plain"].startswith("Vastu is")
    for d in sp["directions"]:
        assert not (d["why_plain"] or "A").startswith("your chart")
        assert "traditional default" not in (d["why_plain"] or "")


def test_same_planet_weekday_and_moon_star_is_one_signal():
    # Saturday ruler == Saturn == the Moon-star ruler: the colour basis names it once, never twice
    c = RT.pick_colour_of_the_day(date(2026, 10, 17), "Saturn", [], lambda n: "favor", set(), WD)["colour"]
    assert c["basis"] == "weekday_ruler:saturn"


# ── colour hierarchy: year decides what is allowed, month and day pick inside it ─────────────────────────────────
def _pick(**kw):
    wd = {"Mercury": ["Green"], "Saturn": ["Black"], "Venus": ["Pink", "White"], "Rahu": ["Smoky Grey"], "Moon": ["White"]}
    base = dict(today=date(2026, 10, 14), nak_lord="Saturn", favor_shades=["Pink"], refused=set(), weekday_colours=wd,
                assess=lambda nm: {"pink": "favor"}.get(nm.lower(), "neutral"))
    base.update(kw)
    return RT.pick_colour_of_the_day(**base)


def test_a_neutral_day_colour_beats_the_years_favourable_shade():
    c = _pick()["colour"]
    assert c["name"] == "Green" and c["scope"] == "day"      # Wednesday's ruler, not the year's pink every day


def test_year_avoid_wins_over_every_day_candidate():
    c = _pick(year_avoid=["Green", "Black"])["colour"]
    assert c["name"] != "Green" and c["name"] != "Black"


def test_moon_sub_ruler_is_a_day_candidate_and_one_planet_counts_once():
    wd = {"Mercury": [], "Saturn": [], "Rahu": ["Smoky Grey"], "Venus": ["Pink"]}
    c = _pick(weekday_colours=wd, sub_lord="Rahu")["colour"]
    assert c["name"] == "Smoky Grey" and c["basis"] == "moon_sub_ruler:rahu" and c["scope"] == "day"
    assert _pick(weekday_colours=wd, sub_lord="Saturn", nak_lord="Saturn")["colour"]["scope"] != "day"


def test_month_colour_is_used_when_no_day_colour_is_eligible_and_year_is_last():
    wd = {"Mercury": [], "Saturn": [], "Venus": ["Pink"], "Rahu": ["Smoky Grey"]}
    c = _pick(weekday_colours=wd, month_lord="Rahu")["colour"]
    assert c["scope"] == "month" and c["name"] == "Smoky Grey"
    c = _pick(weekday_colours=wd)["colour"]
    assert c["scope"] == "year" and c["name"] == "Pink"


def test_nothing_eligible_gives_no_colour_not_a_repeat_of_something_refused():
    r = _pick(favor_shades=[], assess=lambda nm: "avoid")
    assert r["colour"] is None and r["skip"]


def test_the_colour_of_the_day_says_which_period_it_comes_from_and_never_overclaims():
    p = _compose(date(2026, 10, 14))
    cod = p["colour_of_the_day"]
    assert cod["scope"] in ("day", "month", "year")
    if cod["scope"] == "year":
        assert "this year" in cod["reason_plain"] and "today" in cod["reason_plain"]


def test_month_colours_pass_the_year_avoid_list():
    wd = {"Rahu": ["Smoky Grey", "Dark Blue"]}
    out = RT.month_colours("Rahu", wd, lambda nm: "neutral", set(), ["Dark Blue"])
    assert [c["name"] for c in out] == ["Smoky Grey"]
