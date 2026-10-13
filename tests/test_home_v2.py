from datetime import date

from antar_engine import horizon as H
from antar_engine import seasons as SE
from antar_engine import shortcuts as SC

T = date(2026, 10, 13)


def test_houses_ruled_for_a_capricorn_rising_chart():
    assert SE.houses_ruled("Jupiter", "Capricorn") == [3, 12]
    assert SE.houses_ruled("Saturn", "Capricorn") == [1, 2]
    assert SE.houses_ruled("Mars", "Capricorn") == [4, 11]
    assert SE.houses_ruled("Sun", "Nowhere") == []


def test_chart_read_tone_combines_the_generic_nature_with_the_rising_sign():
    r = SE.chart_read("Jupiter", "Capricorn", None, "supportive", "en")            # generic: supportive; for Capricorn rising: a strain
    assert r["tone"] == "mixed" and r["houses"] == [3, 12] and "rules your 3rd and 12th houses" in r["note"] and "come with a cost" in r["note"]
    assert SE.chart_read("Jupiter", "Aries", None, "supportive", "en")["tone"] == "supportive"
    assert SE.chart_read("Saturn", "Aries", None, "testing", "en")["tone"] == "testing"


def test_nodes_act_through_the_sign_lord_where_they_sit():
    cd = {"planets": {"Rahu": {"sign": "Aries"}}}
    r = SE.chart_read("Rahu", "Capricorn", cd, "testing", "en")
    assert r["houses"] == [4, 11] and "no house of its own" in r["note"]
    assert SE.chart_read("Rahu", "Capricorn", {}, "testing", "en")["houses"] == []


def test_seasons_cut_the_next_36_months_at_real_boundaries():
    phase = {"available": True, "chapter": {"plain_name": "Ambition", "end": "2044-08-13", "line": "x"},
             "shift": {"planet": "Rahu", "plain_name": "Ambition", "start": "2026-08-13", "end": "2029-04-25", "nature": "testing", "line": "a", "helps": "b", "watch": "c"},
             "upcoming_shifts": [{"planet": "Jupiter", "plain_name": "Growth", "start": "2029-04-25", "end": "2031-09-19", "nature": "supportive"},
                                 {"planet": "Saturn", "plain_name": "Discipline", "start": "2031-09-19", "end": "2034-09-01", "nature": "testing"}]}
    r = SE.build(phase, {"lagna": {"sign": "Capricorn"}, "planets": {"Rahu": {"sign": "Aries"}}}, "en", T)
    assert r["available"] and [x["title"] for x in r["seasons"]] == ["Ambition season", "Growth season"]       # Discipline starts after the horizon
    assert r["seasons"][0]["years"] == "Now – 2029" and r["seasons"][1]["years"] == "2029 – 2031" and r["seasons"][1]["tone"] == "mixed"
    assert SE.build(None, None)["available"] is False and SE.build({"available": False}, {})["seasons"] == []


FEED = {"tracks": [{"topic": "money", "windows": [{"kind": "open", "start": "2026-10-10", "end": "2026-10-20"}, {"kind": "open", "start": "2027-01-10", "end": "2027-05-09"},
                                                    {"kind": "care", "start": "2027-06-09", "end": "2027-09-06"}]},
                   {"topic": "health", "windows": [{"kind": "care", "start": "2026-11-01", "end": "2026-11-20"}]}]}


def test_shortcuts_dots_and_status_from_the_one_windows_feed():
    r = SC.build(FEED, "en", T)
    k = {x["key"]: x for x in r["topics"]}
    assert r["default"] == ["money", "love", "legal", "career", "health"] and r["max"] == 6
    assert k["money"]["dot"] == "g" and k["money"]["stat"].startswith("A window is open until Oct 20.") and "Your next stretch runs Jan 10 – May 9." in k["money"]["stat"]
    assert k["health"]["dot"] == "c" and k["health"]["stat"] == "Take care Nov 1 – Nov 20."          # starts within 45 days
    assert k["love"]["dot"] == "" and k["love"]["stat"] == "Nothing big marked in the next 12 months."
    assert "not legal advice" in k["legal"]["stat"] and "not a calendar window" in k["job"]["stat"] and k["legal"]["glyph"] == "§"
    assert k["money"]["questions"][1] == "When does my strongest money window open?" and k["career"]["opener"] == "What is on your mind at work?"


def test_shortcuts_spanish_and_no_feed():
    es = {x["key"]: x for x in SC.build(FEED, "es", T)["topics"]}
    assert es["money"]["label"] == "Dinero" and es["money"]["stat"].startswith("Hay una ventana abierta hasta el 20 oct.")
    assert {x["dot"] for x in SC.build(None, "en", T)["topics"]} == {""}


def test_horizon_today_carries_the_read_block():
    sig = {"headline": "A steady day for money and income.", "verdict_subline": "Partnerships are live — work the room, not the desk.",
           "wow": "Watch for a client to signal interest. Reply directly.", "signal": "A partner or client signals readiness today.",
           "windows": [{"kind": "best", "start": "12:17 PM", "end": "1:05 PM", "text": "Best."}], "do_today": ["Do a thing"]}
    c = H.build_today(sig, None, "en", "Steady", "Tue")
    assert c["read"] == {"headline": "Partnerships are live — work the room, not the desk.", "body": "Watch for a client to signal interest. Reply directly.",
                         "move": "A partner or client signals readiness today.", "window": "12:17 PM – 1:05 PM"}


def test_greeting_is_made_for_this_person_and_this_hour():
    from datetime import datetime
    g = H.greeting("Raman Singh", datetime(2026, 10, 13, 8, 30), "en", {"start": "2026-08-13", "title": "Ambition season"})
    assert g["text"] == "Good morning, Raman" and g["date"] == "Tuesday, October 13" and g["part"] == "morning" and g["name"] == "Raman"
    assert g["context"] == "Month 3 of your ambition season"
    assert H.greeting("Raman", datetime(2026, 10, 13, 13, 0))["text"] == "Good afternoon, Raman"
    assert H.greeting("Raman", datetime(2026, 10, 13, 23, 59))["part"] == "evening" and H.greeting("Raman", datetime(2026, 10, 13, 3, 0))["part"] == "evening"
    assert H.greeting(None, datetime(2026, 10, 13, 8, 0))["text"] == "Good morning" and H.greeting("  ", datetime(2026, 10, 13, 8, 0))["name"] is None
    es = H.greeting("Raman", datetime(2026, 10, 13, 20, 0), "es", {"start": "2026-08-13", "title": "temporada de ambici\u00f3n"})
    assert es["text"] == "Buenas noches, Raman" and es["date"] == "martes, 13 de octubre" and es["context"] == "Mes 3 de tu temporada de ambici\u00f3n"
    assert H.greeting("Raman", datetime(2026, 10, 13, 8, 0), "en", {"start": "2027-01-01", "title": "x"})["context"] == ""     # future season: no claim
