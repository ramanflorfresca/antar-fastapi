"""[day-lead 2026-10-16] The day's highlight and watch-point from the star lord and sub lord, read against the chart."""
from antar_engine import day_lead as dl, ritual_today as rt

# Aries lagna: Mars owns 1 and 8, Venus 2 and 7, Mercury 3 and 6, Moon 4, Sun 5, Jupiter 9 and 12, Saturn 10 and 11
CD = {"lagna": {"sign": "Aries"}, "planets": {
    "Sun": {"sign": "Leo", "house": 5}, "Moon": {"sign": "Cancer", "house": 4}, "Mars": {"sign": "Aries", "house": 1},
    "Mercury": {"sign": "Gemini", "house": 3}, "Jupiter": {"sign": "Sagittarius", "house": 9}, "Venus": {"sign": "Taurus", "house": 2},
    "Saturn": {"sign": "Aquarius", "house": 11}, "Rahu": {"sign": "Gemini", "house": 3}, "Ketu": {"sign": "Sagittarius", "house": 9}}}


def test_significators_are_owned_houses_plus_the_seat():
    assert dl.significators("Venus", CD) == [2, 7]                # owns 2 and 7, sits in 2
    assert dl.significators("Saturn", CD) == [10, 11]             # owns 10 and 11, sits in 11
    assert dl.significators("Rahu", CD) == [3, 6]                 # a node: its seat (3) and its sign lord Mercury's houses (3, 6)
    assert dl.significators("Nobody", CD) == []


def test_different_star_lords_give_different_leads_on_the_same_chart():
    a = dl.lead(CD, "Saturn", "Venus")        # Saturn 10, 11 for money/work; Venus 2, 7
    b = dl.lead(CD, "Mars", "Mercury")        # Mars 1, 8: against; Mercury 3, 6
    assert a["highlight"]["area"] in ("money", "work") and a["caution"] is None or a["caution"]["area"] != a["highlight"]["area"]
    assert a["text"] != b["text"] and b["caution"] is not None


def test_text_is_plain_and_names_the_event():
    r = dl.lead(CD, "Saturn", "Venus")
    assert r["highlight"]["text"].startswith("Today's highlight: ") and ", with " in r["highlight"]["text"]
    assert rt.jargon_leaks({"t": r["text"]}) == []


def test_no_usable_lord_is_none_and_a_flat_day_says_so():
    assert dl.lead(CD, "", None) is None and dl.lead({}, "Venus", None) is None
    r = dl.lead(CD, "Moon", None)     # Moon owns only 4 and sits in 4: home is for it
    assert r["highlight"]["area"] == "home"
