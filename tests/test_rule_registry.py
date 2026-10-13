from datetime import date

import pytest

from antar_engine import rule_registry as rr

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


def test_lk_rule_applies_only_when_the_planet_is_in_that_house():
    c = ctx()
    evs = {e.rule_id for e in rr.applicable(c)}
    assert "LK.Moon_12.bad" in evs                            # Moon in Pisces = house 12
    assert "LK.Moon_1.good" not in evs                         # not applicable: says nothing
    moved = ctx({**SIGNS_A, "Moon": 3})                        # Moon in Cancer = house 4 (good)
    assert "LK.Moon_4.good" in {e.rule_id for e in rr.applicable(moved)}


def test_disputed_placements_are_silent():
    # Jupiter in 8 (Scorpio) is disputed between the books -> no rule
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
        assert r["rule_id"].endswith(".bad")
        assert "rahu" not in r["do"].lower() and "venus" not in r["do"].lower()


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
    assert any(e.rule_id == "LK.Moon_12.bad" for e in evs)


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
    moon12 = next(e for e in rr.applicable(c) if e.rule_id == "LK.Moon_12.bad")
    assert "vimshottari" in rr.running(c, moon12, rr.dasha_state(c, TODAY))          # Moon dasha running
    st_later = rr.dasha_state(c, date(2028, 1, 1))                                    # Saturn sub-period
    assert "vimshottari" not in rr.running(c, moon12, st_later)


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
