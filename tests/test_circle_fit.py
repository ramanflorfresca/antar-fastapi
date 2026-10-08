"""The plain-language partnership-fit verdict: lean, seasons, structure. Descriptive and deterministic."""
import json
import re
import sys
from datetime import date

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from antar_engine import circle_fit as F  # noqa: E402

LANGS = ("en", "es", "pt", "hinglish")
TODAY = date(2026, 10, 8)
_JARGON = re.compile(
    r"\b(dasha|dasa|jaimini|vimsottari|parashar\w*|lords?|malefic\w*|benefic\w*|transits?|karakas?|lagna|"
    r"nakshatras?|navamsa|kendra|ascendant|houses?|\d+(st|nd|rd|th)|d-?\d{1,2}|sun|moon|mars|mercury|jupiter|venus|"
    r"saturn|rahu|ketu|yoga|price|premium|subscribe\w*)\b", re.I)
_PREDICT = re.compile(r"\b(will (succeed|win|raise|fail|work)|guarantee\w*|destined|doomed)\b", re.I)


def test_temperament_covers_all_27_and_reads_from_the_moon():
    assert len(F.TEMPERAMENT_EN) == 27 and len(set(F.TEMPERAMENT_EN)) == 27
    t = F.temperament({"planets": {"Moon": {"nakshatra": "Revati", "nakshatra_index": 26}}})
    assert t["nakshatra"] == "Revati" and t["trait"].startswith("Caring, imaginative")
    assert F.temperament({"planets": {"Moon": {"nakshatra": "Chitra"}}})["trait"].startswith("Creative")      # by name when no index
    assert F.temperament({}) is None and F.temperament({"planets": {"Moon": {}}}) is None


def test_no_chart_term_or_prediction_in_any_user_string():
    def strings(x):
        if isinstance(x, str): yield x
        elif isinstance(x, dict):
            for v in x.values(): yield from strings(v)
        elif isinstance(x, (list, tuple)):
            for v in x: yield from strings(v)
    for s in list(strings(F.TEMPERAMENT_EN)) + list(strings(F.COPY_TABLES)):
        assert not _JARGON.search(s), s
        assert not _PREDICT.search(s), s
    for t in F.COPY_TABLES:
        for entry in t.values():
            if isinstance(entry, dict) and "en" in entry:
                assert set(entry) >= set(LANGS), entry


ROWS_RAMAN = [{"level": "mahadasha", "lord_or_sign": "Rahu", "start_date": "2026-08-13", "end_date": "2044-08-13"},
              {"level": "antardasha", "lord_or_sign": "Rahu", "start_date": "2026-08-13", "end_date": "2029-04-25"},
              {"level": "antardasha", "lord_or_sign": "Jupiter", "start_date": "2029-04-25", "end_date": "2032-01-01"}]
ROWS_ANDRES = [{"level": "mahadasha", "lord_or_sign": "Jupiter", "start_date": "2011-06-05", "end_date": "2027-06-05"},
               {"level": "antardasha", "lord_or_sign": "Rahu", "start_date": "2025-01-10", "end_date": "2027-06-05"},
               {"level": "antardasha", "lord_or_sign": "Saturn", "start_date": "2027-06-05", "end_date": "2030-01-01"},
               {"level": "mahadasha", "lord_or_sign": "Saturn", "start_date": "2027-06-05", "end_date": "2046-06-05"}]


def test_the_running_chapter_and_stretch_in_plain_words():
    se = F.season_at({}, ROWS_ANDRES, TODAY)
    assert (se["md"], se["ad"], se["tone"], se["heavy"], se["pos"]) == ("Jupiter", "Rahu", "clouded", True, "last")
    assert se["ends"] == date(2027, 6, 5) and se["md_end"] == date(2027, 6, 5) and se["next_md"] == "Saturn"
    d = F.describe(se, "en")
    # the big chapter with its end date, where he is inside it (the LAST stretch), when it closes, and what comes next
    assert d["label"] == ("A long chapter of growth and wisdom (to Jun 5, 2027), now in its last stretch: illusion and chasing the unfamiliar, "
                          "until Jun 5, 2027, when this chapter closes. Next comes a long chapter of discipline and delay.")
    assert "Illusion is strong here" in d["effect"] and "real opportunities get missed unless there is discipline" in d["effect"]
    assert d["position"] == "last" and d["chapter_ends"] == "2027-06-05" and d["ends_label"] == "Jun 5, 2027" and d["heavy"] is True


def test_a_chapter_that_just_began_says_so():
    sr = F.season_at({}, ROWS_RAMAN, TODAY)
    assert (sr["md"], sr["ad"], sr["pos"]) == ("Rahu", "Rahu", "first") and sr["md_end"] == date(2044, 8, 13) and sr["ends"] == date(2029, 4, 25)
    d = F.describe(sr, "en")
    assert d["label"] == ("A long chapter of ambition and chasing the unfamiliar (to Aug 13, 2044), now in its first stretch: "
                          "illusion and chasing the unfamiliar, until Apr 25, 2029.")
    assert "next comes" not in d["label"].lower() and d["position"] == "first"
    mid = [{"level": "mahadasha", "lord_or_sign": "Saturn", "start_date": "2020-01-01", "end_date": "2039-01-01"},
           {"level": "antardasha", "lord_or_sign": "Venus", "start_date": "2025-01-01", "end_date": "2028-01-01"}]
    dm = F.describe(F.season_at({}, mid, TODAY), "en")
    assert dm["position"] == "mid" and "now in a stretch of comfort and harmony, until Jan 1, 2028." in dm["label"]
    es = F.describe(F.season_at({}, ROWS_ANDRES, TODAY), "es")
    assert es["label"].startswith("Una larga etapa de crecimiento y sabiduría (hasta el 5 jun 2027), ahora en su último tramo:") and "Sigue una larga etapa de disciplina y demora." in es["label"]
    assert F.season_at({}, [], TODAY) is None and F.season_at({}, [{"level": "antardasha", "lord_or_sign": "Zzz", "start_date": "2026-01-01", "end_date": "2030-01-01"}], TODAY) is None


def test_a_chart_with_only_the_big_chapter_still_reads():
    only_md = [{"level": "mahadasha", "lord_or_sign": "Rahu", "start_date": "2027-01-01", "end_date": "2045-01-01"}]
    only_md[0]["start_date"] = "2020-01-01"
    se = F.season_at({}, only_md, TODAY)
    assert se["ad"] is None and se["tone"] == "clouded"
    d = F.describe(se, "en")
    assert d["label"] == "A long chapter of ambition and chasing the unfamiliar (to Jan 1, 2045)." and d["position"] is None and d["effect"]
    assert F.better_from(({}, only_md), ({}, only_md), TODAY) is None          # clouded for the whole horizon
    assert F.phase(se, se, "A", "B", ({}, only_md), ({}, only_md), "en", TODAY)["call"] == "not_now"


def test_tone_rules():
    assert F._tone("Jupiter", "Rahu") == "clouded" and F._tone("Venus", "Ketu") == "clouded"
    assert F._tone("Jupiter", "Saturn") == "testing" and F._tone("Venus", "Mars") == "testing"
    assert F._tone("Jupiter", "Venus") == "favorable" and F._tone("Venus", "Moon") == "steady"
    assert F._tone("Rahu", "Jupiter") == "testing"                                     # good stretch inside a clouded chapter
    assert F._tone("Rahu", "Rahu") == "clouded"


def test_the_first_clear_stretch():
    d = F.better_from(({}, ROWS_RAMAN), ({}, ROWS_ANDRES), TODAY)
    assert d is not None and d > date(2029, 4, 24)                                      # Raman clouded until Apr 2029
    clear = [{"level": "antardasha", "lord_or_sign": "Venus", "start_date": "2026-01-01", "end_date": "2031-01-01"}]
    assert F.better_from(({}, clear), ({}, clear), TODAY) == TODAY
    forever = [{"level": "antardasha", "lord_or_sign": "Rahu", "start_date": "2026-01-01", "end_date": "2040-01-01"}]
    assert F.better_from(({}, forever), ({}, clear), TODAY) is None


def test_phase_is_a_direct_call():
    sr, sa = F.season_at({}, ROWS_RAMAN, TODAY), F.season_at({}, ROWS_ANDRES, TODAY)
    both = F.phase(sr, sa, "Raman", "Andres", ({}, ROWS_RAMAN), ({}, ROWS_ANDRES), "en", TODAY)
    assert both["status"] == "both_heavy" and both["call"] == "not_now" and both["call_title"] == "Not now"
    assert both["line"].startswith("Not now. You are both in clouded stretches") and both["better"]["on"] > "2029-04"
    assert "What doesn't work now can work later" in both["better"]["line"]
    ok = [{"level": "antardasha", "lord_or_sign": "Venus", "start_date": "2026-01-01", "end_date": "2031-01-01"}]
    so = F.season_at({}, ok, TODAY)
    one = F.phase(sa, so, "Andres", "Sam", ({}, ROWS_ANDRES), ({}, ok), "en", TODAY)
    assert one["status"] == "one_heavy" and one["call"] == "not_now"
    assert "Not now. Andres is in a clouded stretch until Jun 5, 2027." in one["line"]
    assert "Illusion is strong here" in one["line"] and one["better"]["on"].startswith("2027-06")
    clear = F.phase(so, so, "A", "B", ({}, ok), ({}, ok), "en", TODAY)
    assert clear["status"] == "clear" and clear["call"] == "good_now" and clear["better"] is None
    sat = [{"level": "antardasha", "lord_or_sign": "Saturn", "start_date": "2026-01-01", "end_date": "2031-01-01"}]
    t = F.phase(F.season_at({}, sat, TODAY), so, "A", "B", ({}, sat), ({}, ok), "es", TODAY)
    assert t["status"] == "testing" and t["call"] == "with_structure" and "estructura" in t["line"]


def test_every_planet_has_every_phrase_in_every_language():
    for lang in LANGS:
        for table in (F.MD_PHRASE, F.AD_PHRASE, F.EFFECT):
            assert set(table[lang]) == set(F.PLANETS)
    assert set(F.TONE.values()) == {"clouded", "testing", "steady", "favorable"}


def test_verdict_picks_the_structure():
    a = lambda n, l: {"first_name": n, "lean": l}
    assert F.verdict(a("R", "partner"), a("A", "partner"), True)["key"] == "full_partners"
    assert F.verdict(a("R", "partner"), a("A", "partner"), False)["key"] == "partners_with_lanes"
    assert F.verdict(a("R", "either"), a("A", "partner"), True)["key"] == "partners_with_lanes"
    v = F.verdict(a("Raman", "partner"), a("Andres", "solo"), True)
    assert v["key"] == "founder_plus_advisor" and v["lead"] == "Andres" and v["other"] == "Raman"
    assert "Andres is better built to lead this alone" in v["line"] and "task or vesting basis, not as a co-founder" in v["line"]
    assert F.verdict(a("R", "solo"), a("A", "either"), False)["lead"] == "R"
    assert F.verdict(a("R", "solo"), a("A", "solo"), True)["key"] == "solo_contract"
    for lang in LANGS:
        assert F.verdict(a("R", "solo"), a("A", "partner"), True, lang)["line"].count("{") == 0


def test_a_lean_needs_a_clear_margin():
    assert (F.PARTNER_MIN, F.SOLO_MAX) == (1.5, -1.5)


def test_real_charts_lean_is_deterministic_and_reasons_are_plain_and_neutral(two=None):
    from test_topic_engine import _real_ctx
    for c in (_real_ctx("1985-03-15", "08:30"), _real_ctx("1990-10-15", "14:10")):
        p1, p2 = F.partnership_lean(c.chart_data), F.partnership_lean(c.chart_data)
        assert p1 == p2 and p1["lean"] in ("partner", "either", "solo")
        for k in p1["reasons"]:
            for lang in LANGS:
                line = F.REASON[k][lang]
                assert not _JARGON.search(line)
                assert not re.search(r"\b(you|your|tú|tu|você|aap)\b", line, re.I) or lang == "hinglish"
        se = F.season_at(c.chart_data, c.dashas["vimsottari"], TODAY)
        assert se is None or (se["ad"] in F.TONE and se["tone"] in ("clouded", "testing", "steady", "favorable"))


def test_brief_carries_verdict_phase_and_per_person_fit_without_chart_terms():
    from test_topic_engine import _real_ctx
    from antar_engine import circle_brief as CB
    a, b = _real_ctx("1985-03-15", "08:30"), _real_ctx("1990-10-15", "14:10")
    pa, pb = CB.profile(a.chart_data, a.dashas, "Raman", "en", TODAY), CB.profile(b.chart_data, b.dashas, "Andres", "en", TODAY)
    for p in (pa, pb):
        assert set(p["temperament"]) == {"trait"} and p["temperament"]["trait"] and p["partnership"]["label"] and set(p["partnership"]) == {"lean", "label", "reasons"}
    br = CB.build(pa, pb, "cofounder", [], {"badge": "MIXED"}, [], "en", TODAY, phase={"status": "clear", "line": "x", "better": None})
    assert br["verdict"]["key"] in ("full_partners", "partners_with_lanes", "founder_plus_advisor", "solo_contract")
    assert br["phase"]["status"] == "clear"
    blob = json.dumps({k: v for k, v in br.items() if k != "note"}, ensure_ascii=False)
    assert not _JARGON.search(blob), _JARGON.search(blob).group(0)
