"""Neecha Bhanga, vargottama and relocated dig bala (2026-10-12)."""
from antar_engine.places_conditions import (
    compute_all_conditions, is_vargottama, neecha_bhanga,
)
from antar_engine.places_concern import dig_bala_factor, relocation_veto_watch


def _p(sign_index, lon=None):
    return {"sign_index": sign_index, "longitude": lon if lon is not None else sign_index * 30 + 15.0}


def _chart(**planets):
    return {"lagna_sign": "Aries", "planets": planets}


def test_sun_debilitated_in_libra_rescued_by_venus_in_kendra():
    # Aries lagna: Venus (lord of Libra) in Capricorn = 10th = kendra
    ch = _chart(Sun=_p(6), Moon=_p(2), Venus=_p(9), Mars=_p(4), Saturn=_p(4))
    assert neecha_bhanga("Sun", ch) is True


def test_not_rescued_when_no_cancelling_planet_in_kendra():
    ch = _chart(Sun=_p(6), Moon=_p(2), Venus=_p(1), Mars=_p(4), Saturn=_p(4))
    assert neecha_bhanga("Sun", ch) is False


def test_not_debilitated_is_never_a_rescue():
    ch = _chart(Sun=_p(0), Moon=_p(2), Venus=_p(9))
    assert neecha_bhanga("Sun", ch) is False


def test_conditions_weight_rises_when_cancelled_but_name_stays():
    rescued = _chart(Sun=_p(6, 195.0), Moon=_p(2), Venus=_p(9), Mars=_p(4), Saturn=_p(4))
    alone = _chart(Sun=_p(6, 195.0), Moon=_p(2), Venus=_p(1), Mars=_p(4), Saturn=_p(4))
    a, b = compute_all_conditions(rescued)["Sun"], compute_all_conditions(alone)["Sun"]
    assert a["condition"] == b["condition"] == "debilitated"
    assert a["cancelled"] and not b["cancelled"]
    assert a["weight"] > b["weight"] and a["polarity"] == "mixed" and b["polarity"] == "friction"


def test_vargottama_same_sign_in_navamsa():
    assert is_vargottama("Mars", _chart(Mars=_p(0, 1.0))) is True      # Aries 1deg -> D9 Aries
    assert is_vargottama("Mars", _chart(Mars=_p(0, 10.0))) is False    # Aries 10deg -> D9 Cancer


def test_vargottama_adds_weight_capped():
    v = compute_all_conditions(_chart(Mars=_p(0, 1.0)))["Mars"]   # own sign 1.3 + 0.2
    assert v["vargottama"] and v["weight"] == 1.5
    plain = compute_all_conditions(_chart(Mars=_p(0, 10.0)))["Mars"]
    assert not plain["vargottama"] and plain["weight"] == 1.3


def test_dig_bala_by_relocated_house():
    assert dig_bala_factor("Jupiter", 1) == 1.15 and dig_bala_factor("Jupiter", 7) == 0.90
    assert dig_bala_factor("Sun", 10) == 1.15 and dig_bala_factor("Sun", 4) == 0.90
    assert dig_bala_factor("Saturn", 7) == 1.15 and dig_bala_factor("Saturn", 1) == 0.90
    assert dig_bala_factor("Moon", 4) == 1.15 and dig_bala_factor("Venus", 10) == 0.90
    assert dig_bala_factor("Mercury", 5) == 1.0 and dig_bala_factor("Rahu", 1) == 1.0


def test_cancelled_debility_is_not_a_broken_karaka_veto():
    # career lead karaka = Sun; debilitated in Libra and in a relocated dusthana
    ch = _chart(Sun=_p(6), Saturn=_p(10))
    reloc = {"relocated_lagna_index": 11}                     # Sun (6) -> house 8
    broken = {"Sun": {"condition": "debilitated", "cancelled": False}}
    rescued = {"Sun": {"condition": "debilitated", "cancelled": True}}
    assert "karaka_broken" in [x["kind"] for x in relocation_veto_watch(ch, "career", reloc, broken, [], 0, 0)]
    assert "karaka_broken" not in [x["kind"] for x in relocation_veto_watch(ch, "career", reloc, rescued, [], 0, 0)]
