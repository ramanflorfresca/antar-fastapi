"""D-10 delivery + career affliction inputs to assess_promise [d10-delivery]."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine import ask_promise as AP
from antar_engine import antar_ephemeris as AE

SIGNS = AP.SIGNS


def _d10(lagna, placements):
    out = {"Lagna": {"sign": lagna}}
    for pl, sg in placements.items():
        out[pl] = {"sign": sg}
    return out


def _run(monkeypatch, d1, d10, lagna_sign="Aries"):
    monkeypatch.setattr(AE, "divisional_chart", lambda cd, n: d10)
    return AP._d10_delivery({}, d1, SIGNS.index(lagna_sign))


def test_vargottama_and_kendra_lord_score_positive(monkeypatch):
    # Aries lagna: 10th lord = Saturn (Capricorn). Saturn in Capricorn in both charts.
    d1 = {"Saturn": {"sign": "Capricorn", "house": 10}, "Sun": {"sign": "Leo"}}
    d10 = _d10("Aries", {"Saturn": "Capricorn", "Sun": "Leo", "Mars": "Aries"})
    r = _run(monkeypatch, d1, d10)
    assert any("Saturn vargottama" in x for x in r["details"])
    assert r["points"] > 1.5 and not r["afflictions"]


def test_tenth_lord_in_8_12_both_charts_is_penalised(monkeypatch):
    d1 = {"Saturn": {"sign": "Scorpio", "house": 8}}
    # D10 lagna Aries; Saturn in Scorpio = 8th from it
    d10 = _d10("Aries", {"Saturn": "Scorpio", "Mars": "Aries"})
    r = _run(monkeypatch, d1, d10)
    assert any("D1" in a and "D10" in a for a in r["afflictions"])
    assert r["points"] < 0


def test_combust_tenth_lord(monkeypatch):
    d1 = {"Saturn": {"sign": "Capricorn", "house": 10, "is_combust": True}}
    d10 = _d10("Aries", {"Saturn": "Libra", "Mars": "Aries"})
    r = _run(monkeypatch, d1, d10)
    assert "Saturn combust" in r["afflictions"]


def test_sun_is_never_combust(monkeypatch):
    # Leo lagna: 10th lord = Venus; Sun flagged combust must be ignored
    d1 = {"Sun": {"sign": "Leo", "is_combust": True}, "Venus": {"sign": "Taurus", "house": 10}}
    d10 = _d10("Leo", {"Venus": "Taurus", "Sun": "Leo", "Saturn": "Aquarius"})
    r = _run(monkeypatch, d1, d10, "Leo")
    assert not any("Sun combust" in a for a in r["afflictions"])


def test_only_career_concerns_get_the_factor():
    chart = {"lagna": {"sign": "Aries", "sign_index": 0, "degree": 5.0},
             "planets": {p: {"sign": "Aries", "house": 1, "longitude": 10.0 + i, "degree": 10.0 + i}
                         for i, p in enumerate(["Sun", "Moon", "Mars", "Mercury", "Jupiter",
                                                "Venus", "Saturn", "Rahu", "Ketu"])}}
    c = AP.assess_promise(chart, [10], ["Saturn"], concern="career")
    m = AP.assess_promise(chart, [7], ["Venus"], concern="marriage")
    assert any(f["factor"] == "D10 delivery" for f in c["factors"])
    assert not any(f["factor"].startswith("D10 ") and "delivery" in f["factor"] for f in m["factors"])
