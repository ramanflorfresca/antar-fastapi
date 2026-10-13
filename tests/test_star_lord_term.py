import pytest

from antar_engine import daily_precision as DP
from antar_engine import daily_prediction_engine as DE


def test_nature_is_functional_for_the_lagna():
    t = DP.star_lord_term("Saturn", "Libra")            # Saturn is a yogakaraka-type benefic for Libra
    assert t["nature"] == 1 and t["delta"] == 1 and t["activated"] is None
    t = DP.star_lord_term("Saturn", "Cancer")           # malefic for Cancer lagna
    assert t["nature"] == -1 and t["delta"] == -1


def test_dasha_lord_amplifies_in_the_same_direction_never_a_free_bonus():
    assert DP.star_lord_term("Saturn", "Libra", md="Saturn")["delta"] == 2          # benefic + MD -> +2
    assert DP.star_lord_term("Saturn", "Cancer", ad="Saturn")["delta"] == -2        # malefic + AD -> -2 (harder, not luckier)
    assert DP.star_lord_term("Sun", "Cancer", md="Sun")["delta"] == 0             # neutral planet: dasha adds nothing


def test_nodes_are_neutral_to_avoid_double_counting_the_friction_list():
    assert DP.star_lord_term("Rahu", "Libra", md="Rahu")["delta"] == 0
    assert DP.star_lord_term("Ketu", "Libra")["delta"] == 0


def test_bad_input_is_harmless():
    assert DP.star_lord_term("", "Libra")["delta"] == 0
    assert DP.star_lord_term("Saturn", "")["delta"] == 0


def test_lord_by_index_matches_ephemeris_table():
    from antar_engine.antar_ephemeris import NAKSHATRA_LORDS
    assert all(DP.nakshatra_lord_by_index(i) == NAKSHATRA_LORDS[i] for i in range(27))


def _prec(**kw):
    return DP.compute_daily_precision("Magha", "Libra", "Swati", "Libra", "Leo", today_star_lord=kw.get("sl", "Saturn"),
                                      dasha_md=kw.get("md", ""), dasha_ad=kw.get("ad", ""), weekday_index=0)


def test_off_by_default_term_is_shadow_only(monkeypatch):
    monkeypatch.delenv("DAILY_STAR_LORD", raising=False)
    p = _prec(md="Saturn")
    assert p["star_lord_delta"] == 2 and p["star_lord_in_score"] is False
    base = DP.apply_precision_to_score(5, dict(p, star_lord_in_score=False))[0]
    assert DP.apply_precision_to_score(5, p)[0] == base
    assert "star_lord_reason" not in DP.precision_fields(p)


def test_on_blends_and_exposes_a_reason(monkeypatch):
    monkeypatch.setenv("DAILY_STAR_LORD", "on")
    p = _prec(md="Saturn")
    off = DP.apply_precision_to_score(5, dict(p, star_lord_in_score=False))[0]
    assert DP.apply_precision_to_score(5, p)[0] == min(10, off + 2)
    f = DP.precision_fields(p)
    assert f["star_lord_delta"] == 2 and "supports your chart" in f["star_lord_reason"]["en"]
    assert "cuenta doble" in f["star_lord_reason"]["es"]


def test_score_is_clamped(monkeypatch):
    monkeypatch.setenv("DAILY_STAR_LORD", "on")
    p = _prec(sl="Saturn", md="Saturn")
    assert 0 <= DP.apply_precision_to_score(9, p)[0] <= 10 and DP.apply_precision_to_score(10, p)[0] == 10


def test_generic_star_list_weight_halves_when_asked():
    # Pushya is on the high-energy list; Rohini too. Same day, only the star weight differs.
    a = DE._score_day("Cancer", "Leo", "Pushya", "Monday")[0]
    b = DE._score_day("Cancer", "Leo", "Pushya", "Monday", star_weight=1)[0]
    assert a - b == 1
    assert DE._score_day("Cancer", "Leo", "Ardra", "Monday")[0] + 1 == DE._score_day("Cancer", "Leo", "Ardra", "Monday", star_weight=1)[0]
