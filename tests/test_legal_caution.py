"""Proactive caution: the running chain (MD→AD→PD→SD) must LINK to natal pressure."""
import re
from pathlib import Path

from antar_engine import arishta_gate as ag, legal, debt as dbt, immigration as imm
from tests.test_immigration_debt import _chart
from tests.test_arishta_gate import HEAVY_DEBT

# Aries lagna: 6th lord Mercury, 8th lord Mars, 12th lord Jupiter.
QUIET_NATAL = _chart("Aries", {"Mercury": ("Virgo", 6), "Mars": ("Capricorn", 10), "Rahu": ("Sagittarius", 9),
                               "Saturn": ("Leo", 5), "Ketu": ("Gemini", 3), "Sun": ("Aries", 1),
                               "Moon": ("Cancer", 4), "Jupiter": ("Taurus", 2), "Venus": ("Libra", 7)})


def _dashas(md, ad, pd=None, sd=None):
    rows = [{"level": "mahadasha", "lord_or_sign": md, "start_date": "2020-01-01", "end_date": "2040-01-01"},
            {"level": "antardasha", "lord_or_sign": ad, "start_date": "2026-01-01", "end_date": "2028-01-01"}]
    if pd:
        rows.append({"level": "pratyantardasha", "lord_or_sign": pd, "start_date": "2026-09-01", "end_date": "2026-12-01"})
    if sd:
        rows.append({"level": "sookshma", "lord_or_sign": sd, "start_date": "2026-10-05", "end_date": "2026-10-20"})
    return {"vimsottari": rows}


TODAY = "2026-10-12"


def test_current_chain_reads_all_four_levels():
    c = ag.current_chain(_dashas("Mercury", "Mars", "Venus", "Moon"), TODAY)
    assert [c[k]["lord"] for k in ("md", "ad", "pd", "sd")] == ["Mercury", "Mars", "Venus", "Moon"]
    assert ag.current_chain(_dashas("Mercury", "Mars"), TODAY)["pd"] is None
    assert ag.current_chain({}, TODAY)["md"] is None


def test_natal_pressure_is_found():
    nat = ag.natal_pressure(HEAVY_DEBT)
    assert 12 in nat and 8 in nat                      # Mars in the 12th; Ketu in the 8th
    assert ag.natal_pressure(QUIET_NATAL) == {}
    assert ag.natal_pressure({}) == {}


def test_stack_with_natal_meet_is_high_and_imminence_uses_transit():
    d = _dashas("Mercury", "Mars", "Venus", "Moon")
    here = ag.legal_caution(HEAVY_DEBT, d, TODAY, transit_house_fn=lambda p: 8)
    assert here["tier"] == "high" and here["imminent"] is True and here["trigger"] is True
    assert here["linked_houses"] and here["window"]["start"] == "2026-09-01"
    calm = ag.legal_caution(HEAVY_DEBT, d, TODAY, transit_house_fn=lambda p: 3)
    assert calm["tier"] == "high" and calm["imminent"] is False


def test_natal_pressure_with_quiet_chain_is_no_caution():
    # heavy natal chart, but the running chain (Sun–Saturn) touches none of 6/8/12
    r = ag.legal_caution(HEAVY_DEBT, _dashas("Sun", "Saturn"), TODAY, transit_house_fn=lambda p: 8)
    assert r["tier"] == "none" and ag.caution_note(r, "en") == ""


def test_chain_link_without_natal_pressure_is_only_a_watch():
    r = ag.legal_caution(QUIET_NATAL, _dashas("Mercury", "Mars"), TODAY, transit_house_fn=lambda p: 8)
    assert r["tier"] == "watch" and r["linked_houses"] == [] and ag.caution_note(r, "en") == ""


def test_caution_note_is_a_caution_not_a_forecast():
    for lang in ("en", "es", "pt"):
        for imminent in (False, True):
            t = ag.caution_note({"tier": "high", "imminent": imminent}, lang)
            assert t and "counsel" in t.lower() or lang != "en"
            assert not re.search(r"jail|prison|arrest|detain|detention|deport|c[aá]rcel|prisi[oó]n|arrest|deporta|pris[aã]o|cadeia",
                                 t, re.I), t
            assert not re.search(r"\byou will\b|\bvas a\b|\bvoc[eê] vai\b", t, re.I)
    assert ag.caution_note({"tier": "caution", "imminent": True}, "en").count("next few weeks") == 1
    assert "next few weeks" not in ag.caution_note({"tier": "caution", "imminent": False}, "en")
    assert ag.caution_note({"tier": "watch"}, "en") == "" and ag.caution_note(None, "en") == ""


def test_verdicts_append_the_caution():
    note = ag.caution_note({"tier": "caution", "imminent": False}, "en")
    assert note in legal.legal_verdict("contested", False, 2028, "en", caution=note)["line"]
    assert note in dbt.debt_verdict("contested", 2028, None, "en", caution=note)["line"]
    assert note in imm.immigration_verdict("some", "mixed", False, 2028, "en", caution=note)["line"]
    assert note not in legal.legal_verdict("contested", False, 2028, "en")["line"]


def test_never_raises_on_bad_input():
    assert ag.legal_caution({}, {}, TODAY)["tier"] == "none"
    assert ag.legal_caution(HEAVY_DEBT, {"vimsottari": [{"level": "x"}]}, TODAY)["tier"] == "none"


def test_wired_into_main():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    assert src.count("caution=_caution_text(") >= 4          # immigration, legal, debt, loan
    assert src.count("PROACTIVE CAUTION (give it as a calm heads-up") == 3
