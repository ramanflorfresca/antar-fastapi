from datetime import datetime

from antar_engine import parashari_events as pe
from antar_engine.jaimini_engine import Planet

SIGNS = {"Sun": 7, "Moon": 11, "Mars": 6, "Mercury": 6, "Jupiter": 10, "Venus": 7, "Saturn": 2, "Rahu": 7, "Ketu": 1}


def _chart():
    P = {n: Planet(name=n, sign=s, degree=s * 30 + 10.0, degree_in_sign=10.0) for n, s in SIGNS.items()}
    return pe.PChart(9, 9 * 30 + 24.69, P), P


def test_significators_include_house_lords_and_karakas():
    c, _ = _chart()
    prim, sup = pe.significators(c, "marriage")
    assert c.lord(7) in prim and "Venus" in prim
    assert pe.significators(c, "career")[0] >= {c.lord(10)}


def test_node_acts_for_sign_lord_and_conjuncts():
    c, _ = _chart()
    acts = c.node_acts_as("Rahu")      # Rahu in Scorpio with Sun and Venus
    assert "Mars" in acts and {"Sun", "Venus"} <= acts


def test_grade_and_windows_deterministic():
    c, P = _chart()
    rows = [{"planet": "Venus", "level": "mahadasha", "start_date": datetime(2020, 1, 1), "end_date": datetime(2040, 1, 1)},
            {"planet": "Venus", "level": "antardasha", "start_date": datetime(2026, 1, 1), "end_date": datetime(2028, 1, 1)},
            {"planet": "Sun", "level": "antardasha", "start_date": datetime(2028, 1, 1), "end_date": datetime(2029, 1, 1)}]
    a = pe.parashari_windows(9, 9 * 30 + 24.69, P, rows, datetime(2026, 1, 1), datetime(2029, 1, 1))
    assert a == pe.parashari_windows(9, 9 * 30 + 24.69, P, rows, datetime(2026, 1, 1), datetime(2029, 1, 1))
    assert a and any(e["grade"] == "strong" for w in a for e in w["events"])
    assert pe._grade("Venus", "Venus", {"Venus"}, set()) == "strong"
    assert pe._grade("Mars", "Sun", set(), set()) is None
