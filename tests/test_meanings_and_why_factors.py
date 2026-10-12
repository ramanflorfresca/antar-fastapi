"""[why-factors 2026-10-12] The approved meanings table and the labelled reasons built from it."""
import re
from datetime import date, timedelta

import pytest

from antar_engine import meanings as M
from antar_engine import why_factors as W

# words the approved copy must not use (owner: hard parts stay in, but never doom, never a forecast)
_DOOM = re.compile(r"\b(malefic|benefic|doomed|cursed|you will (die|get sick|fall ill)|bad luck|evil)\b", re.I)
_FORECAST = re.compile(r"\b(lifespan|how long you (will )?live|will die|death)\b", re.I)


def test_table_is_complete_in_both_languages():
    assert set(M.PLANETS) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    assert set(M.HOUSES) == set(range(1, 13))
    for name, p in M.PLANETS.items():
        assert p["nature"] in M.NATURE
        for lg in M.LANGS:
            assert all(p[lg][k].strip() for k in ("name", "verb", "covers", "watch", "helps")), (name, lg)
    for n, h in M.HOUSES.items():
        for lg in M.LANGS:
            assert all(h[lg][k].strip() for k in ("name", "q", "covers", "watch", "helps")), (n, lg)


def test_four_aims_cover_each_house_once():
    seen = sorted(h for a in M.AIMS.values() for h in a["houses"])
    assert seen == list(range(1, 13))
    assert M.house(4)["aim"] == "moksha" and M.house(10)["aim"] == "artha"


def test_nature_is_the_approved_split():
    assert {n for n, p in M.PLANETS.items() if p["nature"] == "testing"} == {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    assert M.planet("Rahu", "en")["nature_label"] == "testing" and M.planet("Rahu", "es")["nature_label"] == "exigente"


def test_copy_never_dooms_and_never_forecasts_a_lifespan():
    texts = []
    for p in M.PLANETS.values():
        texts += [v for lg in M.LANGS for v in p[lg].values()]
    for h in M.HOUSES.values():
        texts += [v for lg in M.LANGS for v in h[lg].values()]
    texts += [t["plain_en"] for t in M.TERMS.values()] + [t["plain_es"] for t in M.TERMS.values()]
    for t in texts:
        assert not _DOOM.search(t) and not _FORECAST.search(t), t


def test_hard_parts_are_present_and_come_with_what_helps():
    en = M.planet("Mars")
    assert "surgery" in en["watch"] and en["helps"]
    assert "grief" in M.planet("Saturn")["watch"] and "loneliness" in M.planet("Saturn")["watch"]
    assert "rivals" in M.house(6)["covers"] and "endurance" in M.house(8)["covers"]
    assert "not only of loss" in M.house(12)["covers"]


def test_terms_map_the_exact_notes_the_chart_facts_line_uses():
    for note, term in (("vargottama (strong in the navamsa)", "Vargottama"), ("combust (weakened by the Sun)", "Combust"),
                       ("exalted", "Exalted"), ("debilitated", "Debilitated"), ("in its own sign", "In its own sign")):
        assert M.term_for_note(note)["term"] == term
    assert M.term_for_note("something else") is None


# ── the factors ──
TODAY = date(2026, 10, 12)


def _dashas():
    def row(level, planet, s, e):
        return {"level": level, "planet_or_sign": planet, "start_date": s.isoformat(), "end_date": e.isoformat()}
    return {"vimsottari": [row("mahadasha", "Rahu", date(2020, 1, 1), date(2038, 1, 1)),
                           row("antardasha", "Rahu", date(2026, 1, 1), date(2029, 4, 25)),
                           row("antardasha", "Jupiter", date(2029, 4, 25), date(2031, 1, 1))]}


def _chart():
    # Cancer lagna: 10th house = Aries, lord Mars; karakas for career include Sun, Saturn
    def p(sign, house, lon):
        return {"sign": sign, "house": house, "longitude": lon}
    return {"lagna": {"sign": "Cancer"},
            "planets": {"Sun": p("Scorpio", 5, 220.0), "Moon": p("Taurus", 11, 40.0), "Mars": p("Scorpio", 5, 215.0),
                        "Mercury": p("Libra", 4, 195.0), "Jupiter": p("Cancer", 1, 100.0), "Venus": p("Libra", 4, 190.0),
                        "Saturn": p("Gemini", 12, 70.0), "Rahu": p("Aquarius", 8, 310.0), "Ketu": p("Leo", 2, 130.0)}}


def test_career_factors_in_order_with_plain_names_and_what_helps():
    fs = W.build("career", _chart(), _dashas(), "en", TODAY)
    assert [f["kind"] for f in fs][:3] == ["chapter", "shift", "house"]
    chapter, shift, house = fs[0], fs[1], fs[2]
    assert chapter["label"] == "Ambition (Rahu)" and chapter["nature"] == "testing" and chapter["until"] == "until Jan 2038"
    assert shift["until"] == "until Apr 2029" and shift["same_as_chapter"] is True      # Rahu-Rahu: said once
    assert shift["line"] == "The same energy again, in a shorter stretch." and shift["watch"] == "" and shift["helps"] == ""
    assert house["label"] == "Career · 10th house" and house["question"] == "What do I achieve?" and house["aim"] == "artha"
    lord = next(f for f in fs if f["kind"] == "lord")
    assert lord["label"] == "Drive (Mars)" and lord["sits_in"] == {"number": 5, "name": "Creativity"}
    assert "5th house (Creativity)" in lord["line"] and lord["watch"] and lord["helps"]


def test_a_different_shift_keeps_its_own_watch_and_helps():
    d = _dashas()
    d["vimsottari"][1]["planet_or_sign"] = "Jupiter"
    shift = W.build("career", _chart(), d, "en", TODAY)[1]
    assert shift["label"] == "Growth (Jupiter)" and shift["nature"] == "supportive" and shift["watch"] and shift["helps"]
    assert not shift.get("same_as_chapter")


def test_strength_terms_come_with_a_plain_explanation():
    chart = _chart()
    chart["planets"]["Mars"]["sign"] = "Cancer"       # Mars debilitated in Cancer
    lord = next(f for f in W.build("career", chart, _dashas(), "en", TODAY) if f["kind"] == "lord")
    assert any(t["term"] == "Debilitated" and "extra care" in t["plain"] for t in lord["terms"])


def test_spanish_uses_spanish_names_labels_and_months():
    fs = W.build("career", _chart(), _dashas(), "es", TODAY)
    assert fs[0]["label"] == "Ambición (Rahu)" and fs[0]["until"] == "hasta ene 2038"
    assert fs[0]["nature_label"] == "exigente"
    lord = next(f for f in fs if f["kind"] == "lord")
    assert lord["label"].startswith("Impulso (") and "casa 5" in lord["line"]


def test_ordinals_are_right_for_the_first_three_houses():
    for h, label in ((1, "1st"), (2, "2nd"), (3, "3rd")):
        assert W._ordinal_en(h) == label
    fs = W.build("wealth", _chart(), _dashas(), "en", TODAY)        # wealth leads with the 2nd house
    house = next(f for f in fs if f["kind"] == "house")
    assert house["label"] == "Money and family · 2nd house"
    assert not any("thth" in f.get("line", "") or "2th" in f["label"] for f in fs)


def test_other_languages_and_bad_input_give_nothing_and_never_raise():
    assert W.build("career", _chart(), _dashas(), "hi", TODAY) == []
    assert W.build("career", None, None, "en", TODAY) == []
    assert W.build("nonsense", _chart(), _dashas(), "en", TODAY)[:2] != []      # chapter + shift still stand
    assert W.build("career", {"lagna": {"sign": "Nowhere"}, "planets": {"Sun": {}}}, _dashas(), "en", TODAY)[0]["kind"] == "chapter"


def test_every_factor_is_jargon_safe_and_never_forecasts():
    for lg in ("en", "es"):
        for f in W.build("career", _chart(), _dashas(), lg, TODAY):
            for v in (f.get("line", ""), f.get("watch", ""), f.get("helps", "")):
                assert not _DOOM.search(v) and not _FORECAST.search(v), v
