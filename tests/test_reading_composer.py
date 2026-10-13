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


def test_exact_birth_time_lifts_the_gate_unless_margin_is_under_a_minute():
    from antar_engine.reading_composer import compose as c2
    base = json.loads(json.dumps(FC))
    base["d10"]["sensitivity"] = {"fragile": True, "gate": True, "approx_minutes_of_birth_time": 2.8, "accuracy": None}
    assert c2(base, "en", TODAY)["notes"]                                  # gated, asks to confirm
    base["d10"]["sensitivity"].update(gate=False, accuracy="exact")        # confirmed exact, margin 2.8 min
    r = c2(base, "en", TODAY)
    assert not r["notes"] and any(w["strength"] == "strong" for a in r["areas"] for w in a["windows"] if a["area"] == "money")
    base["d10"]["sensitivity"].update(gate=True, accuracy="exact", approx_minutes_of_birth_time=0.5)
    assert "edge" in c2(base, "en", TODAY)["notes"][0]


def test_focus_push_picks_strongest_active_area_and_is_antar_driven():
    r = compose(FC, "en", TODAY)
    f = r["focus"]
    assert f["mode"] == "push" and f["primary"]["area"] == "money"        # strong money window active now
    assert f["primary"]["timing"] == "Active now" and f["primary"]["first_step"]
    assert f["horizon"][0] == "2026-10-13" and f["horizon"][1] > "2027-03-01"
    assert all(a["area"] != "money" for a in f["also"])


def test_focus_protect_when_pressure_dominates_and_nothing_strong_is_active():
    fc = json.loads(json.dumps(FC)); fc["caution_spans"] = [{"start": "2026-10-13", "end": "2027-06-01", "rules": ["x"]}]
    fc["parashari"]["spans"] = []; fc["d10"]["spans"] = []          # leaves only possible/good career windows
    fc["event_spans"] = [{"event": "career", "tier": "double", "start": "2026-10-13", "end": "2027-09-08"}]
    fc["event_spans"][0]["peak"] = ["2026-10-13", "2027-01-08"]
    r = compose(fc, "en", TODAY)
    top = r["focus"]
    assert top["mode"] in ("protect", "push")
    fc["event_spans"] = []
    assert compose(fc, "en", TODAY)["focus"]["mode"] == "protect"
    assert compose(fc, "en", TODAY)["focus"]["primary"]["headline"] == "Protect your energy and cash"


def test_focus_pressure_does_not_override_a_strong_active_window():
    fc = json.loads(json.dumps(FC)); fc["caution_spans"] = [{"start": "2026-10-13", "end": "2027-06-01", "rules": ["x"]}]
    f = compose(fc, "en", TODAY)["focus"]
    assert f["mode"] == "push" and f["primary"]["area"] == "money" and f["avoid"]


def test_focus_build_when_nothing_is_active_and_both_locales_plain():
    fc = {"available": True, "d10": {"sensitivity": {}, "spans": []}, "event_spans": [], "caution_spans": [],
          "parashari": {"spans": [], "caution_spans": []}}
    f = compose(fc, "en", TODAY)["focus"]
    assert f["mode"] == "build" and f["primary"]["area"] is None
    for loc in ("en", "es"):
        text = json.dumps(compose(FC, loc, TODAY)["focus"], ensure_ascii=False).lower()
        assert not [j for j in JARGON if j in text], loc
    assert compose(FC, "es", TODAY)["focus"]["title"].startswith("Tu enfoque")
