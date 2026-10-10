"""chart_summary: the plain-language 'your chart in 60 seconds' block."""
import re
from datetime import date

import pytest

from antar_engine import chart_identity as CI

_JARGON = re.compile(r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu|dasha|yoga|house|"
                     r"Sol|Luna|Marte|Mercurio|Júpiter|Saturno|Lua|Vênus|Mercúrio)\b")


def _chart(**over):
    cd = {
        "lagna": {"sign": "Aquarius", "degree": 27.4},
        "planets": {
            "Sun": {"sign": "Aquarius", "house": 1, "nakshatra": "x"},
            "Moon": {"sign": "Aquarius", "house": 1, "nakshatra": "y"},
            "Mars": {"sign": "Leo", "house": 6},
            "Saturn": {"sign": "Aries", "house": 3},
        },
        "atmakaraka": {"planet": "Sun"},
        "yogas": [{"name": "Dhana Yoga", "strength": "strong", "effect": "e"}],
    }
    cd.update(over)
    return cd


TODAY = date(2026, 10, 10)
VIM = [
    {"level": "mahadasha", "lord_or_sign": "Jupiter", "start_date": "2011-12-04", "end_date": "2027-12-04"},
    {"level": "mahadasha", "lord_or_sign": "Saturn", "start_date": "2027-12-04", "end_date": "2046-12-04"},
    {"level": "antardasha", "lord_or_sign": "Rahu", "start_date": "2025-06-01", "end_date": "2027-12-04"},
    {"level": "antardasha", "lord_or_sign": "Saturn", "start_date": "2027-12-04", "end_date": "2030-06-01"},
]


def _summary(cd=None, lang="en", vim=VIM):
    out = CI.build_chart_identity(cd or _chart(), vim, today=TODAY, language=lang)
    return out["chart_summary"]


def test_summary_shape_and_three_strengths():
    s = _summary()
    assert s is not None
    assert len(s["strengths"]) == 3 and len(set(s["strengths"])) == 3
    assert s["growth_edge"]
    assert set(s) == {"strengths", "growth_edge", "phase", "phase_ends"}


def test_summary_omitted_when_fewer_than_three_strengths():
    cd = _chart(yogas=[], atmakaraka=None)
    assert CI.build_chart_identity(cd, VIM, today=TODAY)["chart_summary"] is None


def test_atma_and_lagna_lord_same_planet_counted_once():
    # Saturn rules Aquarius; make Saturn the soul planet too.
    cd = _chart(atmakaraka={"planet": "Saturn"}, yogas=[])
    assert CI.build_chart_identity(cd, VIM, today=TODAY)["chart_summary"] is None  # only 1 distinct strength


@pytest.mark.parametrize("lang", ["en", "es", "pt"])
def test_no_planet_or_chart_jargon(lang):
    s = _summary(lang=lang)
    blob = " ".join(s["strengths"] + [s["growth_edge"] or "", s["phase"] or ""])
    assert not _JARGON.search(blob), blob


def test_growth_edge_prefers_debilitated_then_running_planet():
    # Saturn is debilitated in Aries; Mars only sits in a hard house.
    s = _summary()
    assert "discipline and time" in s["growth_edge"]  # debilitated Saturn beats Mars in a hard house


def test_growth_edge_none_when_no_weak_planet():
    cd = _chart(planets={"Sun": {"sign": "Leo", "house": 1}, "Moon": {"sign": "Cancer", "house": 2}})
    assert _summary(cd)["growth_edge"] is None


def test_phase_uses_nearer_handover_and_localizes():
    s = _summary()
    assert "Dec 2027" in s["phase"] and "season" not in s["phase"].lower()
    assert s["phase_ends"] == "2027-12-04"
    assert _summary(lang="es")["phase"].startswith("Estás")
    assert _summary(lang="pt")["phase"].startswith("Você")


def test_reading_same_sign_sun_moon_not_different_wells():
    out = CI.build_chart_identity(_chart(), VIM, today=TODAY)["reading"]
    assert "different wells" not in out and "share Aquarius" in out
    cd = _chart()
    cd["planets"]["Moon"] = {"sign": "Taurus", "house": 3}
    assert "different wells" in CI.build_chart_identity(cd, VIM, today=TODAY)["reading"]
    es = CI.build_chart_identity(_chart(), VIM, today=TODAY, language="es")["reading"]
    assert "fuentes distintas" not in es and "comparten Acuario" in es
    pt = CI.build_chart_identity(_chart(), VIM, today=TODAY, language="pt")["reading"]
    assert "fontes diferentes" not in pt and "compartilham Aquário" in pt


def test_growth_edge_tie_goes_to_running_chapter_planet():
    # Both debilitated (Mars in Cancer, Saturn in Aries); Saturn runs the chapter.
    cd = _chart()
    cd["planets"]["Mars"] = {"sign": "Cancer", "house": 6}
    vim = [{"level": "mahadasha", "lord_or_sign": "Saturn",
            "start_date": "2020-01-01", "end_date": "2039-01-01"}]
    s = CI.build_chart_identity(cd, vim, today=TODAY)["chart_summary"]
    assert "discipline and time" in s["growth_edge"]
