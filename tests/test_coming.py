import json
from datetime import date

from antar_engine import coming as C

T = date(2026, 10, 12)


def W(topic, kind, s, e):
    return {"topic": topic, "kind": kind, "start": date.fromisoformat(s), "end": date.fromisoformat(e), "why": ""}


FEED = {"tracks": [
    {"topic": "money", "label": "Money", "windows": [
        {"kind": "open", "start": "2026-10-12", "end": "2026-10-12"}, {"kind": "open", "start": "2027-01-10", "end": "2027-05-09"},
        {"kind": "care", "start": "2027-06-09", "end": "2027-09-06"}, {"kind": "care", "start": "2027-10-07", "end": "2027-10-12"}]},
    {"topic": "business", "label": "Business", "windows": [{"kind": "care", "start": "2027-02-09", "end": "2027-03-10"}]},
    {"topic": "weird", "label": "x", "windows": [{"kind": "open", "start": "2027-01-01", "end": "2027-02-01"}]}],
    "next": [{"topic": "money", "kind": "open", "start": "2027-01-10", "why": {"line": "Tied to income."}}], "now": [], "care": []}


def test_month_list_is_twelve_starting_this_month_and_wraps_the_year():
    ml = C.month_list(T)
    assert len(ml) == 12 and ml[0] == (2026, 10) and ml[3] == (2027, 1) and ml[-1] == (2027, 9)


def test_year_all_has_tiles_sentence_and_only_in_range_moments():
    r = C.build_year(FEED, "all", T, "en")
    k = {m["month"]: m for m in r["months"]}
    assert k["Jan"]["kind"] == "open" and k["Jan"]["text"] == "Money open"
    assert k["Feb"]["kind"] == "open" and k["Feb"]["care_too"] is True           # money open + business care
    assert k["Jun"]["kind"] == "care" and k["Jun"]["text"].startswith("Care: money")
    assert k["Nov"]["kind"] == "quiet"
    assert r["head"] == (f"Your best stretch for money runs {C._mdy(date(2027, 1, 10), 'en')} to {C._mdy(date(2027, 5, 9), 'en')}. "
                         f"Take care with money from {C._mdy(date(2027, 6, 9), 'en')} to {C._mdy(date(2027, 9, 6), 'en')}.")
    assert all(x["start"] <= "2027-09-30" for x in r["moments"])                 # the Oct-2027 window is outside the 12 tiles
    assert [x["title"] for x in r["moments"]][0] == "Money window" and r["moments"][0]["range"] == "Jan 10 – May 9"
    assert [c["key"] for c in r["topics"]][0] == "all" and "love" in [c["key"] for c in r["topics"]]
    assert all(m["month"] != "weird" for m in r["months"]) and r["quiet"] is False


def test_single_topic_tile_words_and_why_line():
    r = C.build_year(FEED, "money", T, "en")
    k = {m["month"]: m for m in r["months"]}
    assert k["Jan"]["text"] == "Opens 10th" and k["Feb"]["text"] == "Open" and k["May"]["text"] == "Closes 9th"
    assert k["Jun"]["text"] == "Care from 9th" and k["Sep"]["text"] == "Care ends 6th"
    assert k["Jan"]["lines"] == [f"Your money window runs {C._mdy(date(2027, 1, 10), 'en')} to {C._mdy(date(2027, 5, 9), 'en')}."] and k["Jan"]["why"] == "Tied to income."
    assert r["head"].endswith(f"Take care from {C._mdy(date(2027, 6, 9), 'en')} to {C._mdy(date(2027, 9, 6), 'en')}.")


def test_quiet_topic_is_honest_not_empty():
    r = C.build_year(FEED, "career", T, "en")
    assert r["quiet"] is True and r["head"] == "Nothing big opens or closes in the next 12 months."
    assert {m["kind"] for m in r["months"]} == {"quiet"} and r["moments"] == []


def test_life_moves_are_ask_prompts_not_tiles():
    r = C.build_year(FEED, "all", T, "en")
    assert [x["key"] for x in r["ask_moves"]] == ["job_change", "move_home"]
    assert r["ask_moves"][0]["question"] == "When is the best time for me to change jobs?"
    assert "job_change" not in [c["key"] for c in r["topics"]]
    assert C.build_year(FEED, "job_change", T, "en")["topic"] == "all"           # not a tile topic any more
    assert C.build_year(FEED, "all", T, "es")["ask_moves"][1]["label"] == "Mudanza"


def test_spanish_and_bad_topic():
    r = C.build_year(FEED, "all", T, "es")
    assert r["head"].startswith(f"Tu mejor tramo para dinero va de {C._mdy(date(2027, 1, 10), 'es')} a {C._mdy(date(2027, 5, 9), 'es')}.")
    assert {m["month"]: m for m in r["months"]}["ene"]["text"] == "Dinero abierto"
    assert C.build_year(FEED, "nonsense", T, "en")["topic"] == "all"


def test_chapter_steps_use_engine_words():
    ph = {"available": True, "chapter": {"plain_name": "Ambition", "end": "2044-08-13", "line": "hunger, novelty"},
          "shift": {"plain_name": "Ambition", "start": "2026-08-13", "end": "2029-02-01", "line": "same energy", "helps": "facts"},
          "upcoming_shifts": [{"plain_name": "Growth", "start": "2029-04-25", "end": "2031-09-19", "line": "wisdom", "helps": "a mentor"}]}
    r = C.build_chapter(ph, T, "en")
    assert r["head"] == "You are in a long chapter of Ambition, running to 2044." and r["sub"] == "hunger, novelty"
    assert r["steps"][0] == {"years": "Now – 2029", "title": "Ambition shift", "now": True, "meaning": "same energy", "helps": "facts", "watch": ""}
    assert r["steps"][1]["years"] == "2029 – 2031" and r["steps"][1]["now"] is False
    assert C.build_chapter(None, T, "en")["quiet"] is True and C.build_chapter({"available": False}, T)["steps"] == []
