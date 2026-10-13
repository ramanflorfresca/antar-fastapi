from datetime import datetime

from antar_engine import d10_layer as d
from antar_engine.jaimini_engine import Planet

TAU, CAP = 1, 9


def test_d10_sign_known_values():
    # Raman: lagna 24d41' Capricorn -> D-10 Taurus
    assert d.d10_sign(9 * 30 + 24.69) == TAU
    assert d.d10_sign(0.5) == 0            # odd sign starts at itself
    assert d.d10_sign(30.5) == 9           # Taurus (even) starts from 9th = Capricorn


def test_lagna_sensitivity_flags_edge():
    s = d.lagna_sensitivity(9 * 30 + 24.69)
    assert s["fragile"] and s["approx_minutes_of_birth_time"] < 4
    assert not d.lagna_sensitivity(9 * 30 + 25.5)["fragile"]


def test_windows_deterministic_and_houses_consistent():
    P = {n: Planet(name=n, sign=s, degree=s * 30 + 10.0, degree_in_sign=10.0)
         for n, s in [("Sun", 7), ("Moon", 11), ("Mars", 6), ("Mercury", 6), ("Jupiter", 10),
                      ("Venus", 7), ("Saturn", 2), ("Rahu", 7), ("Ketu", 1)]}
    a = d.d10_windows(CAP, 9 * 30 + 24.69, P, datetime(1974, 11, 26), datetime(2026, 1, 1), datetime(2029, 1, 1))
    assert a == d.d10_windows(CAP, 9 * 30 + 24.69, P, datetime(1974, 11, 26), datetime(2026, 1, 1), datetime(2029, 1, 1))
    assert a["d10_lagna"] == "Taurus" and a["windows"]
    for w in a["windows"]:
        assert 1 <= w["d10_house"] <= 12 and w["rules"][0] == f"D10.period_sign_is_house_{w['d10_house']}"
