import json
from datetime import date

from antar_engine.reading_composer import compose

TODAY = date(2026, 10, 13)
FC = {
    "available": True,
    "d10": {"sensitivity": {"fragile": False},
            "spans": [{"start": "2027-05-27", "end": "2027-11-26", "peak": ["2027-05-27", "2027-11-26"], "gain_score": 3}]},
    "event_spans": [{"event": "career", "tier": "double", "start": "2026-10-13", "end": "2027-09-08", "peak": ["2026-10-13", "2027-01-08"]},
                    {"event": "education", "tier": "double", "start": "2027-01-01", "end": "2027-06-01", "peak": ["2027-01-01", "2027-06-01"]}],
    "caution_spans": [{"start": "2027-11-26", "end": "2028-05-26", "rules": ["x"]}],
    "parashari": {"spans": [{"event": "money", "start": "2026-10-13", "end": "2029-04-25", "grade": "strong"},
                            {"event": "career", "start": "2027-06-01", "end": "2027-12-01", "grade": "supported"}],
                  "caution_spans": []},
}
JARGON = ["dasha", "rahu", "ketu", "jupiter", "saturn", "venus", "mars", "mercury", "d-10", "d10", "house", "lagna",
          "karaka", "chara", "vimshottari", "parashari", "jaimini", "aries", "taurus", "gemini", "capricorn"]


def test_two_systems_make_a_strong_money_window_with_peak():
    r = compose(FC, "en", TODAY)
    money = next(a for a in r["areas"] if a["area"] == "money")
    w = money["windows"][0]
    assert w["strength"] == "strong" and w["both_systems"] and w["peak"] == ["2027-05-27", "2027-11-26"]
    assert "Two independent" in w["why"]


def test_study_needs_triple_and_single_system_is_not_strong():
    r = compose(FC, "en", TODAY)
    assert next(a for a in r["areas"] if a["area"] == "learning")["windows"] == []
    career = next(a for a in r["areas"] if a["area"] == "career")["windows"]
    assert career and all(w["strength"] in ("good", "strong") for w in career)


def test_no_jargon_and_both_locales_and_deterministic():
    for loc in ("en", "es"):
        r = compose(FC, loc, TODAY)
        text = json.dumps(r, ensure_ascii=False).lower()
        assert not [j for j in JARGON if j in text], loc
        assert r == compose(FC, loc, TODAY)
    assert compose(FC, "es", TODAY)["areas"][0]["title"] == "Dinero"


def test_fragile_birth_time_drops_d10_money_and_caps_strength():
    fc = json.loads(json.dumps(FC)); fc["d10"]["sensitivity"]["fragile"] = True
    r = compose(fc, "en", TODAY)
    money = next(a for a in r["areas"] if a["area"] == "money")["windows"][0]
    assert money["strength"] != "strong" and r["notes"]


def test_cautions_and_dates_are_clipped_to_today():
    r = compose(FC, "en", TODAY)
    assert r["cautions"][0]["start"] == "2027-11-26"
    assert all(w["start"] >= "2026-10-13" for a in r["areas"] for w in a["windows"])


LK = {"annual": [{"annual_houses": {"Jupiter": 11, "Saturn": 2, "Moon": 4, "Rahu": 10}, "special_cycle": None,
                  "good_placements": [{"planet": "Jupiter", "house": 11}, {"planet": "Moon", "house": 4}, {"planet": "Rahu", "house": 10}],
                  "bad_placements": [{"planet": "Saturn", "house": 2}],
                  "dormant_areas": [{"area": "children", "house": 5}],
                  "remedies": {"Saturn": [{"name": "Saturn in 2nd", "do": "Serve the poor on Saturdays and donate oil.", "timing": "Saturday", "duration": "43 days"},
                                          {"name": "x", "do": "Wear Jupiter gem daily", "timing": "", "duration": ""}]}}]}


def test_year_block_good_bad_and_remedies_plain():
    fc = {**FC, "lal_kitab": LK}
    for loc in ("en", "es"):
        y = compose(fc, loc, TODAY)["year"]
        assert y["good"] and y["watch"] and y["tone"] in ("favourable", "mixed", "testing")
        assert len(y["remedies"]) == 1          # the remedy naming a planet is dropped
        assert "Jupiter" not in json.dumps(y) and "Saturn" not in json.dumps(y)
    assert "income and gains" in compose(fc, "en", TODAY)["year"]["good"]
    assert compose(FC, "en", TODAY)["year"] is None


def test_weak_single_system_window_does_not_say_strongly():
    r = compose(FC, "en", TODAY)
    for a in r["areas"]:
        for w in a["windows"]:
            if w["strength"] == "possible":
                assert "strongly" not in w["why"]
