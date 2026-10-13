"""Regression for 2026-10-13: rasi drishti gave fixed signs four aspects; arudha/upapada 7th-house
exception went to the wrong sign. Checked against Jaimini Sutras and two commentaries."""
import pytest

from antar_engine import jaimini_engine as je
from antar_engine import jaimini_rao_events as ev
from antar_engine.jaimini_engine import Planet

ARI, TAU, GEM, CAN, LEO, VIR, LIB, SCO, SAG, CAP, AQU, PIS = range(12)
MOVABLE = {ARI, CAN, LIB, CAP}; FIXED = {TAU, LEO, SCO, AQU}; DUAL = {GEM, VIR, SAG, PIS}


@pytest.mark.parametrize("sign", range(12))
def test_rasi_drishti_is_three_signs_and_never_adjacent(sign):
    got = set(je.get_rashi_drishti(sign))
    assert len(got) == 3 and sign not in got
    if sign in MOVABLE:
        assert got == FIXED - {(sign + 1) % 12}
    elif sign in FIXED:
        assert got == MOVABLE - {(sign - 1) % 12}
    else:
        assert got == DUAL - {sign}


def test_rasi_drishti_published_examples():
    assert set(je.get_rashi_drishti(TAU)) == {CAN, LIB, CAP}      # not Aries
    assert set(je.get_rashi_drishti(LEO)) == {ARI, LIB, CAP}      # not Cancer
    assert set(je.get_rashi_drishti(ARI)) == {LEO, SCO, AQU}      # not Taurus
    # aspect is symmetric between a movable and a fixed sign that are not neighbours
    for m in MOVABLE:
        for f in je.get_rashi_drishti(m):
            assert m in je.get_rashi_drishti(f)


def _planets(lord_sign_by_house):
    base = {n: Planet(name=n, sign=0, degree=10.0, degree_in_sign=10.0) for n in
            ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")}
    for n, s in lord_sign_by_house.items():
        base[n] = Planet(name=n, sign=s, degree=s * 30 + 10.0, degree_in_sign=10.0)
    return base


def test_arudha_same_house_goes_to_tenth_and_seventh_goes_to_fourth():
    # Aries lagna, Mars (lord) in Aries: lord in the house itself -> projection lands on Aries -> 10th from Aries = Capricorn
    assert ev.arudha(ARI, _planets({"Mars": ARI})) == CAP
    # Aries lagna, Mars in Cancer (4th): projects to Libra, which is the 7th from Aries -> 4th from Aries = Cancer
    assert ev.arudha(ARI, _planets({"Mars": CAN})) == CAN
    # ordinary case: Mars in Taurus (2nd) -> Gemini (3rd)... lord 1 step from house: lands 2 steps from the house
    assert ev.arudha(ARI, _planets({"Mars": TAU})) == GEM


@pytest.mark.parametrize("lagna", range(12))
def test_upapada_matches_generic_arudha_of_the_twelfth(lagna):
    P = _planets({n: (lagna + i) % 12 for i, n in enumerate(("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"))})
    h12 = (lagna + 11) % 12
    assert je.compute_upapada_lagna(lagna, P).sign == ev.arudha(h12, P)
