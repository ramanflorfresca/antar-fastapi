from datetime import datetime

from antar_engine import jaimini_engine as je
from antar_engine import jaimini_rao_events as ev

LEO, ARI, CAP, GEM = 4, 0, 9, 2
SIGNS = {"Sun": 4, "Moon": 0, "Mars": 9, "Mercury": 4, "Jupiter": 4,
         "Venus": 4, "Saturn": 2, "Rahu": 2, "Ketu": 9}
DEG = {"Sun": 25, "Moon": 20, "Mars": 15, "Mercury": 12, "Jupiter": 8, "Venus": 5, "Saturn": 3, "Rahu": 9, "Ketu": 9}


def _planets():
    return {n: je.Planet(name=n, sign=s, degree=s * 30 + DEG[n], degree_in_sign=DEG[n])
            for n, s in SIGNS.items()}


def test_arudha_never_in_house_or_its_seventh():
    P = _planets()
    for house in range(12):
        a = ev.arudha(house, P)
        assert a not in (house, (house + 6) % 12)


def test_navamsa_sign():
    assert ev.navamsa_sign(0.0) == 0 and ev.navamsa_sign(3.4) == 1 and ev.navamsa_sign(359.9) == 11


def test_marriage_rule_seventh_from_lagna_fires():
    c = ev.Chart(LEO, 130.0, _planets())
    assert "MAR.7th_from_lagna" in ev.rules_for_sign(c, 10)["marriage"]  # Aquarius is 7th from Leo


def test_windows_are_deterministic_and_carry_rule_ids():
    P = _planets()
    a = ev.predict_windows(LEO, 130.0, P, datetime(1944, 8, 20), datetime(2026, 1, 1),
                           datetime(2030, 1, 1), with_transits=False, min_rules=1)
    b = ev.predict_windows(LEO, 130.0, P, datetime(1944, 8, 20), datetime(2026, 1, 1),
                           datetime(2030, 1, 1), with_transits=False, min_rules=1)
    assert a == b and a
    assert all(e["rules"] for w in a for e in w["events"])


def test_composite_tiers_and_determinism():
    from antar_engine import composite_events as ce
    P = _planets()
    vim = [{"planet": "Venus", "start_date": datetime(2026, 1, 1), "end_date": datetime(2032, 1, 1)}]
    a = ce.composite_windows(LEO, 130.0, P, datetime(1944, 8, 20), datetime(2026, 1, 1),
                             datetime(2032, 1, 1), vim_rows=vim, min_rules=1)
    assert a == ce.composite_windows(LEO, 130.0, P, datetime(1944, 8, 20), datetime(2026, 1, 1),
                                     datetime(2032, 1, 1), vim_rows=vim, min_rules=1)
    tiers = {e["tier"] for w in a for e in w["events"]}
    assert tiers <= {"single", "double", "triple"} and tiers
    assert any("vimshottari" in e["layers"] for w in a for e in w["events"] if e["event"] == "marriage")
