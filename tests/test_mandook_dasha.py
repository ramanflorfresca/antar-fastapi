"""Mandook dasha against K.N. Rao's printed Table I and dated charts (ledger fixtures F1-F5)."""
from datetime import datetime

import pytest

from antar_engine import mandook_dasha as md

ARI, TAU, GEM, CAN, LEO, VIR, LIB, SCO, SAG, CAP, AQU, PIS = range(12)
ABBR = {"Ar": ARI, "Ta": TAU, "Ge": GEM, "Ca": CAN, "Le": LEO, "Vi": VIR, "Li": LIB, "Sc": SCO, "Sg": SAG,
        "Cp": CAP, "Aq": AQU, "Pi": PIS}


def S(text):
    return [ABBR[x.strip()] for x in text.split(",")]


def test_table_i_examples_from_the_book():
    assert md.mandook_sign_order(ARI) == S("Ar, Ca, Li, Cp, Ta, Le, Sc, Aq, Ge, Vi, Sg, Pi")
    assert md.mandook_sign_order(TAU) == S("Sc, Le, Ta, Aq, Li, Ca, Ar, Cp, Vi, Ge, Pi, Sg")
    assert md.mandook_sign_order(CAP) == S("Ca, Ar, Cp, Li, Ge, Pi, Sg, Vi, Ta, Aq, Sc, Le")


@pytest.mark.parametrize("lagna", range(12))
def test_order_is_a_permutation_and_direction_by_lagna_parity(lagna):
    o = md.mandook_sign_order(lagna)
    assert sorted(o) == list(range(12))
    assert o[0] == (lagna if lagna in md.ODD_SIGNS else (lagna + 6) % 12)
    step = 3 if lagna in md.ODD_SIGNS else -3
    assert o[1] == (o[0] + step) % 12


def _signs(**kw):
    return {k: ABBR[v] for k, v in kw.items()}


# F2 Charan Singh: Sagittarius lagna, b. 23 Dec 1902
F2 = _signs(Sun="Sg", Moon="Vi", Mars="Vi", Mercury="Sg", Jupiter="Cp", Venus="Sg", Saturn="Cp")
# F3 Rajiv Gandhi: Leo lagna, b. 20 Aug 1944
F3 = _signs(Sun="Le", Moon="Le", Mars="Vi", Mercury="Le", Jupiter="Le", Venus="Le", Saturn="Ge")
# F4 K.N. Rao: Libra lagna, b. 12 Oct 1931
F4 = _signs(Sun="Vi", Moon="Li", Mars="Li", Mercury="Vi", Jupiter="Ca", Venus="Li", Saturn="Sg")
# F1 Aries lagna, b. 6 Feb 1962
F1 = _signs(Sun="Cp", Moon="Aq", Mars="Cp", Mercury="Cp", Jupiter="Cp", Venus="Cp", Saturn="Cp")


def _list(lagna, signs, birth, n=12):
    ps = md.compute_mandook_dasha(lagna, signs, birth, num_cycles=1)
    return [(p.sign, p.years) for p in ps][:n]


def test_f2_charan_singh_periods_and_subs():
    assert _list(SAG, F2, datetime(1902, 12, 23)) == [
        (SAG, 2), (PIS, 3), (GEM, 10), (VIR, 10), (CAP, 12), (ARI, 6), (CAN, 11), (LIB, 3),
        (AQU, 12), (TAU, 6), (LEO, 5), (SCO, 3)]
    ps = md.compute_mandook_dasha(SAG, F2, datetime(1902, 12, 23), 2)
    assert sum(p.years for p in ps[:12]) == 83
    virgo = next(p for p in ps if p.sign == VIR)
    assert virgo.start.year == 1917 and virgo.end.year == 1927
    # marriage 25 Jun 1925 falls in the Virgo-period sub #10 (Aquarius), which starts 23 Jun 1925
    assert [s.sign for s in virgo.subs][9] == AQU
    assert virgo.subs[9].start.date() == datetime(1925, 6, 23).date()
    assert virgo.subs[9].start <= datetime(1925, 6, 25) < virgo.subs[9].end
    # second cycle repeats the same periods, second Sagittarius starts Dec 1985
    sag2 = [p for p in ps if p.sign == SAG][1]
    assert sag2.start.year == 1985 and sag2.start.month == 12 and sag2.years == 2


def test_f3_rajiv_gandhi_periods_and_death_sub():
    assert _list(LEO, F3, datetime(1944, 8, 20)) == [
        (LEO, 12), (SCO, 3), (AQU, 5), (TAU, 10), (VIR, 2), (SAG, 9), (PIS, 8), (GEM, 3), (LIB, 11), (CAP, 8),
        (ARI, 6), (CAN, 12)]
    ps = md.compute_mandook_dasha(LEO, F3, datetime(1944, 8, 20), 1)
    pisces = next(p for p in ps if p.sign == PIS)
    assert pisces.start.year == 1985 and pisces.end.year == 1993
    taurus_sub = next(s for s in pisces.subs if s.sign == TAU)
    assert taurus_sub.start <= datetime(1991, 5, 21) < taurus_sub.end        # killed 21 May 1991


def test_f4_rao_periods_and_subs():
    assert _list(LIB, F4, datetime(1931, 10, 12)) == [
        (LIB, 12), (CAP, 2), (ARI, 10), (CAN, 10), (SCO, 2), (AQU, 11), (TAU, 8), (LEO, 2), (SAG, 8),
        (PIS, 9), (GEM, 4), (VIR, 12)]
    ps = md.compute_mandook_dasha(LIB, F4, datetime(1931, 10, 12), 1)
    cancer = next(p for p in ps if p.sign == CAN)
    aq_sub = next(s for s in cancer.subs if s.sign == AQU)                    # father's death sub, Oct 1960 - Aug 1961
    assert aq_sub.start.year == 1960 and aq_sub.start.month == 10


def test_f1_aries_lagna_and_f5_gemini_durations():
    assert _list(ARI, F1, datetime(1962, 2, 6), 4) == [(ARI, 10), (CAN, 6), (LIB, 4), (CAP, 12)]
    libra = next(p for p in md.compute_mandook_dasha(ARI, F1, datetime(1962, 2, 6), 1) if p.sign == LIB)
    assert [s.sign for s in libra.subs][:6] == [LIB, CAP, ARI, CAN, SCO, AQU]  # sub order from the major sign
    f5 = _signs(Mercury="Sc", Jupiter="Pi", Venus="Sc", Sun="Sc", Moon="Sc", Mars="Sc", Saturn="Sc")
    assert md.mandook_duration(GEM, f5) == 6                                  # Mercury in the 6th, count 6


def test_duration_rules():
    # count 7 -> 10, count 1 -> 12, never 1 or 7; Scorpio uses Mars only, Aquarius Saturn only
    base = {n: ARI for n in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")}
    base["Saturn"] = CAP
    assert md.mandook_duration(ARI, {**base, "Mars": ARI}) == 12
    assert md.mandook_duration(ARI, {**base, "Mars": LIB}) == 10              # lord in the 7th
    assert md.mandook_duration(SCO, {**base, "Mars": ARI, "Ketu": SCO}) == 8   # Ketu ignored; Mars in Aries: count 8 backward
    assert md.mandook_duration(AQU, {**base, "Saturn": AQU, "Rahu": TAU}) == 12
    for sign in range(12):
        for lord_sign in range(12):
            ps = {**base, "Mars": lord_sign, "Venus": lord_sign, "Mercury": lord_sign, "Moon": lord_sign,
                  "Sun": lord_sign, "Jupiter": lord_sign, "Saturn": lord_sign}
            assert md.mandook_duration(sign, ps) in (2, 3, 4, 5, 6, 8, 9, 10, 11, 12)


def test_gate():
    kend = {n: ARI for n in ("Sun", "Moon", "Mars", "Mercury")}
    assert md.mandook_applicable(ARI, {**kend, "Jupiter": TAU, "Venus": TAU, "Saturn": TAU})
    assert not md.mandook_applicable(ARI, {"Sun": ARI, "Moon": ARI, "Mars": ARI, "Mercury": TAU,
                                          "Jupiter": TAU, "Venus": TAU, "Saturn": TAU})
    assert md.compute_mandook_dasha(ARI, {"Sun": TAU, "Moon": TAU, "Mars": TAU, "Mercury": TAU,
                                          "Jupiter": TAU, "Venus": TAU, "Saturn": TAU}, datetime(1990, 1, 1)) is None
