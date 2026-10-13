"""
Chara Dasha ORDER (sequence direction) against K.N. Rao's "Predicting through
Jaimini's Chara Dasha" (ch.3 "Chara Dasha Order", ch.4 "Order of Sub Periods").

Regression for the 2026-10-13 fix: the engine used the sign-counting group
(Aries, Taurus, Gemini, Libra, Scorpio, Sagittarius = forward) to pick the
direction of the dasha SEQUENCE from the lagna. Rao's rule is the 9th-house rule:
  forward lagnas  : Aries, Leo, Virgo, Libra, Aquarius, Pisces
  backward lagnas : Taurus, Gemini, Cancer, Scorpio, Sagittarius, Capricorn
The two groupings agree only for Aries, Libra, Cancer and Capricorn, so the bug
was invisible on a Capricorn-lagna verification chart.

Sub-periods (ch.4): same rule applied to the MAJOR-PERIOD sign, each sign takes its
own sub-period LAST (Aries: Taurus ... Pisces, Aries).

The published examples used below are Rao's Rajiv Gandhi horoscope (Leo lagna,
20 Aug 1944): major periods Leo 12y, Virgo 1y, Libra 10y, Scorpio 2y, Sagittarius 8y,
Capricorn 7y, Aquarius 8y, and the sub-periods he states: Libra-Cancer 20 Apr 1964
to 20 Feb 1965 (Nehru died 27 May 1964) and Aquarius-Capricorn 20 Apr to 20 Dec 1991
(Rajiv killed 21 May 1991); the Queen (Capricorn lagna, backward order); and a
Taurus-lagna chart (backward: Taurus, Aries, Pisces, Aquarius, Capricorn).
"""
from datetime import date, datetime

import pytest

from antar_engine import jaimini
from antar_engine import jaimini_engine as je

ARI, TAU, GEM, CAN, LEO, VIR, LIB, SCO, SAG, CAP, AQU, PIS = range(12)

# Rao: ninth from the lagna in {Aries, Taurus, Gemini, Libra, Scorpio, Sagittarius} => forward
_NINTH_FORWARD = {ARI, TAU, GEM, LIB, SCO, SAG}


def _rao_forward(lagna):
    return ((lagna + 8) % 12) in _NINTH_FORWARD


def _seq(lagna, forward):
    return [(lagna + i) % 12 if forward else (lagna - i) % 12 for i in range(12)]


@pytest.mark.parametrize("lagna", range(12))
def test_md_sequence_follows_the_ninth_house_rule(lagna):
    expected = _seq(lagna, _rao_forward(lagna))
    assert je.compute_md_sequence(lagna) == expected
    assert jaimini.get_dasha_sequence(lagna) == expected


def test_direct_and_indirect_lagna_groups_are_raos():
    direct = {s for s in range(12) if _rao_forward(s)}
    assert direct == {ARI, LEO, VIR, LIB, AQU, PIS}
    assert je.DIRECT_LAGNA_SIGNS == direct
    assert jaimini.DIRECT_LAGNA_SIGNS == direct


def test_published_sequences():
    # Leo lagna (Nixon, Rajiv Gandhi): Leo, Virgo, Libra, Scorpio, Sagittarius, Capricorn, Aquarius ...
    assert je.compute_md_sequence(LEO)[:7] == [LEO, VIR, LIB, SCO, SAG, CAP, AQU]
    # Queen Elizabeth (Capricorn lagna, backward): Cap, Sag, Sco, Lib, Vir, Leo, Can, Gem, Tau, Ari, Pis, Aqu
    assert je.compute_md_sequence(CAP) == [CAP, SAG, SCO, LIB, VIR, LEO, CAN, GEM, TAU, ARI, PIS, AQU]
    # Taurus lagna (backward): Taurus, Aries, Pisces, Aquarius, Capricorn ...
    assert je.compute_md_sequence(TAU)[:5] == [TAU, ARI, PIS, AQU, CAP]


@pytest.mark.parametrize("md_sign", range(12))
def test_antardasha_own_sign_last_and_direction_by_md_sign(md_sign):
    seq = je.compute_ad_sequence(md_sign)
    assert len(seq) == 12 and len(set(seq)) == 12
    assert seq[-1] == md_sign                       # own sub-period is LAST
    step = 1 if _rao_forward(md_sign) else -1
    assert seq[0] == (md_sign + step) % 12          # starts with the neighbour in the direction


def test_published_antardasha_orders():
    # Aries (forward): Taurus ... Pisces, Aries.
    assert je.compute_ad_sequence(ARI) == [TAU, GEM, CAN, LEO, VIR, LIB, SCO, SAG, CAP, AQU, PIS, ARI]
    # Taurus (backward): Aries, Pisces ... Gemini, Taurus.
    assert je.compute_ad_sequence(TAU) == [ARI, PIS, AQU, CAP, SAG, SCO, LIB, VIR, LEO, CAN, GEM, TAU]


# Synthetic planet signs that reproduce Rao's Rajiv Gandhi major-period lengths
# (Leo 12, Virgo 1, Libra 10, Scorpio 2, Sagittarius 8, Capricorn 7, Aquarius 8).
_PLANET_SIGN = {"Sun": LEO, "Moon": ARI, "Mars": CAP, "Mercury": LEO, "Jupiter": LEO,
                "Venus": LEO, "Saturn": GEM, "Rahu": GEM, "Ketu": CAP}
_BIRTH = date(1944, 8, 20)


def test_engine_major_periods_match_rajiv_gandhi_table():
    planets = {n: je.Planet(name=n, sign=s, degree=s * 30 + 10.0, degree_in_sign=10.0)
               for n, s in _PLANET_SIGN.items()}
    mds = je.compute_chara_dasha(LEO, planets, datetime(1944, 8, 20), num_cycles=1)
    assert [(m.sign, m.duration_years) for m in mds[:7]] == [
        (LEO, 12), (VIR, 1), (LIB, 10), (SCO, 2), (SAG, 8), (CAP, 7), (AQU, 8)]


def _md_at(mds, when):
    return next(m for m in mds if m.start_date <= when < m.end_date)


def _ad_at(md, when):
    return next(a for a in md.sub_periods if a.start_date <= when < a.end_date)


def test_engine_antardashas_match_rao_dates():
    planets = {n: je.Planet(name=n, sign=s, degree=s * 30 + 10.0, degree_in_sign=10.0)
               for n, s in _PLANET_SIGN.items()}
    mds = je.compute_chara_dasha(LEO, planets, datetime(1944, 8, 20), num_cycles=1)

    # Nehru died 27 May 1964: Rao puts it in Libra-Cancer (20 Apr 1964 - 20 Feb 1965)
    when = datetime(1964, 5, 27)
    md = _md_at(mds, when)
    assert md.sign == LIB
    ad = _ad_at(md, when)
    assert ad.sign == CAN
    assert abs((ad.start_date - datetime(1964, 4, 20)).days) <= 8
    assert abs((ad.end_date - datetime(1965, 2, 20)).days) <= 8

    # Rajiv killed 21 May 1991: Aquarius-Capricorn (20 Apr - 20 Dec 1991)
    when = datetime(1991, 5, 21)
    md = _md_at(mds, when)
    assert md.sign == AQU
    ad = _ad_at(md, when)
    assert ad.sign == CAP
    assert abs((ad.start_date - datetime(1991, 4, 20)).days) <= 8
    assert abs((ad.end_date - datetime(1991, 12, 20)).days) <= 8


def test_simple_module_major_periods_match_rajiv_gandhi_table():
    mds = jaimini.compute_jaimini_dashas(LEO, _PLANET_SIGN, _BIRTH)
    assert [(m["sign"], m["duration_years"]) for m in mds[:7]] == [
        ("Leo", 12), ("Virgo", 1), ("Libra", 10), ("Scorpio", 2),
        ("Sagittarius", 8), ("Capricorn", 7), ("Aquarius", 8)]
    assert mds[2]["start_date"] == date(1957, 8, 20)
    assert mds[6]["start_date"] == date(1984, 8, 20)


def test_capricorn_lagna_unchanged():
    # the module owner's own chart (verified against Parasara Light): backward from Capricorn
    assert je.compute_md_sequence(CAP)[:3] == [CAP, SAG, SCO]
    assert jaimini.get_dasha_sequence(CAP)[:3] == [CAP, SAG, SCO]
