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


def test_arudha_lagna_money_and_ledger_rules():
    P = _planets()
    c = ev.Chart(LEO, 130.0, P)
    assert c.al not in (LEO, (LEO + 6) % 12)                  # AL is never the lagna or its 7th
    assert "MON.sign_2nd_or_11th_from_AL" in ev.rules_for_sign(c, (c.al + 1) % 12)["money"]
    assert "MON.sign_2nd_or_11th_from_AL" in ev.rules_for_sign(c, (c.al + 10) % 12)["money"]
    # unsupported-by-the-books AL career rules are gone
    for sgn in range(12):
        assert not any("_AL" in r for r in ev.rules_for_sign(c, sgn)["career"])
    # Rangacharya's job set: Sun or Venus in the running sign
    assert "CAR.sign_holds_Sun_or_Venus" in ev.rules_for_sign(c, P["Sun"].sign)["career"]
    # spouse set: upapada family, darapada, 7th from AL / AK, DK's navamsa sign
    assert "MAR.sign_is_UL_or_2nd_from_UL" in ev.rules_for_sign(c, c.ul)["marriage"]
    assert "MAR.sign_is_darapada" in ev.rules_for_sign(c, c.a7)["marriage"]
    assert "MAR.7th_from_AL" in ev.rules_for_sign(c, (c.al + 6) % 12)["marriage"]
    assert "MAR.sign_is_DK_navamsa_sign" in ev.rules_for_sign(c, c.dkn)["marriage"]


def test_karakamsha_cautions_and_narrowed_sagittarius_rule():
    P = _planets()
    c = ev.Chart(LEO, 130.0, P)
    assert "KAR.running_sign_8th_from_karakamsha" in ev.rules_for_sign(c, (c.kl + 7) % 12)["caution"]
    sag = ev.rules_for_sign(c, 8)["caution"]
    assert ("CAU.sagittarius_period_with_AK_in_sagittarius_navamsa" in sag) == (c.kl == 8)
    assert not any(x == "CAU.sagittarius_period_accident_or_sudden_illness" for x in sag)


def test_money_event_flows_through_windows_and_composite():
    from antar_engine import composite_events as ce
    P = _planets()
    w = ev.predict_windows(LEO, 130.0, P, datetime(1944, 8, 20), datetime(2026, 1, 1),
                           datetime(2036, 1, 1), with_transits=False, min_rules=1)
    assert any(e["event"] == "money" for x in w for e in x["events"])
    cw = ce.composite_windows(LEO, 130.0, P, datetime(1944, 8, 20), datetime(2026, 1, 1),
                              datetime(2036, 1, 1), min_rules=1)
    assert any(e["event"] == "money" and e["tier"] in ("single", "double", "triple") for x in cw for e in x["events"])
