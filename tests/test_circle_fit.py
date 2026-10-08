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


def test_season_theme_from_the_houses_a_lord_rules():
    chart = {"lagna": {"sign_index": 0}, "planets": {}}            # Aries rising: Mars rules 1+8, Venus 2+7, Mercury 3+6, Moon 4, Sun 5, Jupiter 9+12, Saturn 10+11
    assert F.lord_theme(chart, "Moon") == "consolidation"          # 4th only
    assert F.lord_theme(chart, "Sun") == "expansion"               # 5th only
    assert F.lord_theme(chart, "Saturn") == "action"               # 10th + 11th, both supportive: the first of equals wins
    assert F.lord_theme(chart, "Mars") == "transformation"
    assert F.lord_theme(chart, "zzz") is None


def test_mercury_example_is_friction_when_net_is_negative():
    chart = {"lagna": {"sign_index": 0}, "planets": {}}
    assert F.lord_theme(chart, "Mercury") == "friction"


def test_seasons_and_the_first_clear_stretch():
    chart = {"lagna": {"sign_index": 0}, "planets": {}}
    rows = [{"level": "antardasha", "lord_or_sign": "Mars", "start_date": "2026-01-01", "end_date": "2027-03-01"},     # heavy (transformation)
            {"level": "antardasha", "lord_or_sign": "Sun", "start_date": "2027-03-01", "end_date": "2028-03-01"}]     # expansion
    se = F.season_at(chart, rows, TODAY)
    assert se["theme"] == "transformation" and se["heavy"] and se["ends"] == date(2027, 3, 1)
    clear_rows = [{"level": "antardasha", "lord_or_sign": "Sun", "start_date": "2026-01-01", "end_date": "2030-01-01"}]
    d = F.better_from((chart, rows), (chart, clear_rows), TODAY)
    assert date(2027, 3, 1) <= d <= date(2027, 3, 20)               # first step after the heavy season ends
    assert F.better_from((chart, clear_rows), (chart, clear_rows), TODAY) == TODAY
    forever = [{"level": "antardasha", "lord_or_sign": "Mars", "start_date": "2026-01-01", "end_date": "2040-01-01"}]
    assert F.better_from((chart, forever), (chart, clear_rows), TODAY) is None


def test_phase_lines():
    chart = {"lagna": {"sign_index": 0}, "planets": {}}
    heavy = [{"level": "antardasha", "lord_or_sign": "Mars", "start_date": "2026-01-01", "end_date": "2027-03-01"},
             {"level": "antardasha", "lord_or_sign": "Sun", "start_date": "2027-03-01", "end_date": "2031-03-01"}]
    ok = [{"level": "antardasha", "lord_or_sign": "Sun", "start_date": "2026-01-01", "end_date": "2031-03-01"}]
    sh, so = F.season_at(chart, heavy, TODAY), F.season_at(chart, ok, TODAY)
    one = F.phase(sh, so, "Raman", "Andres", (chart, heavy), (chart, ok), "en", TODAY)
    assert one["status"] == "one_heavy" and "Raman is in a season of transformation until Mar 1, 2027" in one["line"]
    assert one["better"]["on"].startswith("2027-03") and "What doesn't work now can work later" in one["better"]["line"]
    both = F.phase(sh, sh, "A", "B", (chart, heavy), (chart, heavy), "es", TODAY)
    assert both["status"] == "both_heavy" and "no es el momento" in both["line"]
    clear = F.phase(so, so, "A", "B", (chart, ok), (chart, ok), "en", TODAY)
    assert clear["status"] == "clear" and clear["better"] is None


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
        assert se is None or se["theme"] in F.THEMES


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
