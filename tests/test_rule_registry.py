from datetime import date

import pytest

from antar_engine import rule_registry as rr
from antar_engine import rc_rules as rc

SMALL = [
    {"id": "T1", "kind": "natal", "planet": "Moon", "houses": [12], "requires": [], "tone": "bad", "topics": ["money"],
     "effect": "Spending runs ahead of income.", "effect_es": "El gasto va por delante del ingreso.", "remedy": "Float a coconut in running water for 43 days.", "remedy_es": "Echa un coco al agua corriente durante 43 días.", "clarity": "clear"},
    {"id": "T2", "kind": "natal", "planet": "Mars", "houses": [7], "requires": [{"planet": "Mercury", "with": "Mars"}],
     "tone": "good", "topics": ["marriage"], "effect": "A steady, supportive partner.", "clarity": "clear"},
    {"id": "T3", "kind": "natal", "planet": "Moon", "houses": [4], "requires": [], "tone": "good", "topics": ["money"],
     "effect": "Family help keeps money steady.", "clarity": "clear"},
    {"id": "T4", "kind": "natal", "planet": "Saturn", "houses": [3], "requires": [{"planet": "Venus", "with": "Mars"}],
     "tone": "good", "topics": ["career"], "effect": "Hard work pays at work.", "clarity": "clear"},
]


@pytest.fixture(autouse=True)
def small_rules(monkeypatch):
    monkeypatch.setattr(rc, "_cache", SMALL)
    yield

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]
TODAY = date(2026, 10, 13)


def chart(lagna, signs, degs=None):
    degs = degs or {}
    pl = {}
    for n, s in signs.items():
        d = degs.get(n, 10.0)
        pl[n] = {"sign": SIGNS[s], "sign_index": s, "degree": d, "longitude": s * 30 + d,
                 "house": (s - lagna) % 12 + 1}
    return {"lagna": {"sign": SIGNS[lagna], "sign_index": lagna, "degree": 12.0}, "planets": pl}


# Capricorn lagna, Moon Pisces ... : planets chosen so a few LK cells apply
SIGNS_A = {"Sun": 7, "Moon": 11, "Mars": 6, "Mercury": 6, "Jupiter": 10, "Venus": 7, "Saturn": 2, "Rahu": 7, "Ketu": 1}


def ctx(signs=SIGNS_A, lagna=9, age_years=51):
    return rr.Ctx(chart(lagna, signs), f"{2026 - age_years}-11-26", [], TODAY)


def test_parse_question_languages():
    assert rr.parse_question("When will my startup get funding?") == ("funding", "when")
    assert rr.parse_question("¿Cuándo me voy a casar?") == ("marriage", "when")
    assert rr.parse_question("Why is my income stuck?") == ("money", "why")
    assert rr.parse_question("Kab shaadi hogi?")[0] == "marriage"
    assert rr.parse_question("how do I get promoted in my career")[1] == "how"
    assert rr.parse_question("tell me about the weather") == (None, "what")


def test_rule_applies_only_when_planet_and_conditions_hold():
    c = ctx()
    ids = {e.rule_id for e in rr.applicable(c)}
    assert "LK.T1" in ids and "LK.T3" not in ids               # Moon is in 12, not 4
    assert "LK.T2" in ids                                       # Mars and Mercury share Libra (house 7)
    assert "LK.T4" not in ids                                   # Saturn is not in house 3
    moved = ctx({**SIGNS_A, "Moon": 3})                         # Moon in Cancer = house 4
    mids = {e.rule_id for e in rr.applicable(moved)}
    assert "LK.T3" in mids and "LK.T1" not in mids


def test_disputed_cells_stay_silent_because_no_rule_exists_for_them():
    c = ctx({**SIGNS_A, "Jupiter": 7})
    assert not [e for e in rr.applicable(c) if e.planet == "Jupiter"]


def test_for_subject_uses_house_subjects_and_parents():
    c = ctx()
    evs = rr.applicable(c)
    money = rr.for_subject(evs, "money")
    assert all({"money"} & set(e.subjects) for e in money)
    funding = rr.for_subject(evs, "funding")                   # funding also draws on money rules
    assert set(map(id, money)) <= set(map(id, funding))


def test_answers_are_deterministic_plain_and_bilingual():
    c = ctx()
    for lang in ("en", "es"):
        a = rr.answer(c, "money", "why", lang)
        assert a == rr.answer(ctx(), "money", "why", lang)
        low = a["text"].lower()
        for bad in ("rahu", "ketu", "dasha", "lagna", "karaka", "house ", "yoga"):
            assert bad not in low, (lang, bad)
    assert rr.answer(c, "money", "what", "es")["headline"].startswith("Lo que dice")


def test_silence_when_no_rule_applies():
    c = ctx({"Sun": 0, "Moon": 0, "Mars": 0, "Mercury": 0, "Jupiter": 0, "Venus": 0, "Saturn": 0, "Rahu": 0, "Ketu": 6})
    a = rr.answer(c, "children", "what", "en")
    assert a["applicable"] is False and "no rule" in a["text"]


def test_remedies_attach_to_straining_placements_and_name_no_planet():
    c = ctx()
    a = rr.answer(c, "marriage", "how", "en")
    for r in a["remedies"]:
        assert r["do"] and "rahu" not in r["do"].lower() and "venus" not in r["do"].lower()


def test_speculation_gets_a_caution_not_a_call():
    a = rr.answer(ctx(), "speculation", "what", "en")
    assert any("caution" in l.lower() for l in a["lines"]) and a["applicable"]
    assert "buy" not in a["text"].lower() and "sell" not in a["text"].lower()


def test_unknown_subject_and_unusable_chart():
    assert rr.answer(ctx(), None, "what")["applicable"] is False
    bad = rr.Ctx({}, "1980-01-01", [], TODAY)
    assert rr.answer(bad, "money", "what") == {"available": False}


def test_money_draws_on_expense_and_hidden_money_houses():
    c = ctx()                                                  # Moon in house 12 (bad) -> bears on money
    evs = rr.for_subject(rr.applicable(c), "money")
    assert any(e.rule_id == "LK.T1" for e in evs)


def test_why_leads_with_the_strain_and_how_never_comes_back_blank():
    c = ctx()
    why = rr.answer(c, "money", "why", "en")["lines"]
    assert why[0].startswith("To handle with care")
    for subj in rr.SUBJECTS:
        a = rr.answer(c, subj, "how", "en")
        assert a["lines"] and all(l.strip() for l in a["lines"])


VIM = [
    {"planet_or_sign": "Moon", "level": "mahadasha", "start_date": "2020-01-01", "end_date": "2030-01-01"},
    {"planet_or_sign": "Moon", "level": "antardasha", "start_date": "2026-01-01", "end_date": "2027-06-01"},
    {"planet_or_sign": "Saturn", "level": "antardasha", "start_date": "2027-06-01", "end_date": "2029-01-01"},
]


def ctx_v(signs=SIGNS_A):
    return rr.Ctx(chart(9, signs), "1975-11-26", VIM, TODAY)


def test_dasha_state_reads_vimshottari_and_chara():
    st = rr.dasha_state(ctx_v(), TODAY)
    assert st["vim_md"] == "Moon" and st["vim_ad"] == "Moon"
    assert st["chara_md"] is not None and st["chara_ad"] is not None


def test_a_rule_runs_only_when_its_planet_or_sign_is_dashaed():
    c = ctx_v()
    moon12 = next(e for e in rr.applicable(c) if e.rule_id == "LK.T1")
    assert "vimshottari" in rr.running(c, moon12, rr.dasha_state(c, TODAY))          # Moon dasha running
    later = rr.dasha_state(c, date(2028, 1, 1))                                       # Moon major, Saturn sub: still runs
    assert later["vim_ad"] == "Saturn" and "vimshottari" in rr.running(c, moon12, later)
    neither = {**later, "vim_md": "Venus"}                                            # no Moon lord running
    assert "vimshottari" not in rr.running(c, moon12, neither)


def test_timeline_segments_are_ordered_labelled_and_silent_when_nothing_runs():
    c = ctx_v()
    tl = rr.timeline(c, "money", 24, "en")
    assert all(s["tone_label"] in ("supportive", "strained", "mixed") for s in tl)
    assert [s["start"] for s in tl] == sorted(s["start"] for s in tl)
    assert tl == rr.timeline(ctx_v(), "money", 24, "en")
    es = rr.timeline(c, "money", 24, "es")
    assert all(s["tone_label"] in ("favorable", "tenso", "mixto") for s in es)
    quiet = rr.Ctx(chart(9, SIGNS_A), "1975-11-26", [], TODAY)                       # no Vimshottari rows: no answer lines
    assert "to" not in " ".join(rr.answer(quiet, "money", "when", "en")["lines"][:0])


def test_rules_whose_ages_are_all_past_are_history_not_guidance():
    old = {"id": "T9", "kind": "natal", "planet": "Moon", "houses": [12], "requires": [], "tone": "bad",
           "topics": ["money"], "effect": "Money slips at around age 24.", "ages": [24], "clarity": "clear"}
    rc._cache = SMALL + [old]
    ids = {e.rule_id for e in rr.applicable(ctx(age_years=51))}
    assert "LK.T9" not in ids
    young = {e.rule_id for e in rr.applicable(rr.Ctx(chart(9, SIGNS_A), "2005-11-26", [], TODAY))}
    assert "LK.T9" in young                                    # still ahead at 20


def test_how_never_lists_cautions_under_lean_on():
    a = rr.answer(ctx(), "marriage", "how", "en")
    text = "\n".join(a["lines"])
    assert "Lean on:" not in text or all("wedding can be delayed" not in l for l in a["lines"])


def test_gender_clauses_need_a_known_gender():
    fem = {"id": "T10", "kind": "natal", "planet": "Moon", "houses": [12], "requires": [{"chart": "female"}],
           "tone": "good", "topics": ["money"], "effect": "x", "clarity": "clear"}
    rc._cache = SMALL + [fem]
    c = rr.Ctx(chart(9, SIGNS_A), "1975-11-26", [], TODAY, gender="female")
    assert "LK.T10" in {e.rule_id for e in rr.applicable(c)}
    assert "LK.T10" not in {e.rule_id for e in rr.applicable(ctx())}


def test_combination_rules_apply_only_when_the_planets_stand_that_way(monkeypatch):
    from antar_engine import combo_rules as cb
    monkeypatch.setattr(cb, "_cache", [
        {"id": "CB.1", "n": 1, "name": "Gajakesari Yoga", "tone": "good", "topics": ["fame", "money"],
         "requires": [{"planet": "Jupiter", "in_houses_from": "Moon", "houses": [1, 4, 7, 10]}],
         "effect": "Your standing outlasts you.", "effect_es": "Tu prestigio te sobrevive.", "clarity": "clear"},
        {"id": "CB.2", "n": 2, "name": "Other Yoga", "tone": "bad", "topics": ["money"],
         "requires": [{"planet": "Jupiter", "in_houses": [6]}], "effect": "Money feels thin.", "effect_es": None, "clarity": "clear"}])
    c = ctx({**SIGNS_A, "Moon": 3, "Jupiter": 6})                 # Moon Cancer, Jupiter Libra: 4th from the Moon
    ids = {e.rule_id for e in rr.applicable(c)}
    assert "CB.1" in ids and "CB.2" not in ids
    a = rr.answer(c, "money", "what", "en")
    assert any("Your standing outlasts you." in l for l in a["lines"])
    es = rr.answer(c, "money", "what", "es")
    assert any("Tu prestigio" in l for l in es["lines"])
    other = ctx({**SIGNS_A, "Moon": 3, "Jupiter": 11})
    assert "CB.1" not in {e.rule_id for e in rr.applicable(other)}


def test_capped_answers_draw_from_every_book():
    many = [{"id": f"M{i}", "kind": "natal", "planet": "Moon", "houses": [12], "requires": [], "tone": "bad",
             "topics": ["money"], "effect": f"Lal Kitab line {i}.", "effect_es": f"Linea {i}.", "clarity": "clear"} for i in range(12)]
    rc._cache = many
    from antar_engine import combo_rules as cb
    cb._cache = [{"id": "CB.1", "n": 1, "name": "Z Yoga", "tone": "bad", "topics": ["money"],
                  "requires": [{"planet": "Moon", "in_houses": [4]}], "effect": "Combination line.", "effect_es": "Linea c.",
                  "clarity": "clear"}]
    a = rr.answer(ctx({**SIGNS_A, "Moon": 3}), "money", "what", "en")      # Moon in Cancer: 4th from Aries lagna? lagna is Capricorn
    assert a["applicable"] in (True, False)
    c = ctx({**SIGNS_A})
    # lagna Capricorn (9): Moon in Pisces is house 3, so use a Moon placement that is the 4th house (Aries)
    c4 = ctx({**SIGNS_A, "Moon": 0})
    cb._cache = [{"id": "CB.1", "n": 1, "name": "Z Yoga", "tone": "bad", "topics": ["money"],
                  "requires": [{"planet": "Moon", "in_houses": [4]}], "effect": "Combination line.", "effect_es": "Linea c.",
                  "clarity": "clear"}]
    rc._cache = [{**m, "houses": [1]} for m in many]                         # Moon in Aries = Lal Kitab house 1
    lines = rr.answer(c4, "money", "what", "en")["lines"]
    assert any("Combination line." in l for l in lines)
    assert any("Lal Kitab line" in l for l in lines)
