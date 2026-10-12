"""Trap-line watch-outs from natal rulership (2026-10-12)."""
from antar_engine.places_concern import houses_ruled, lord_trap_watch


def _chart(lagna_sign):
    return {"lagna_sign": lagna_sign}


def _line(planet, angle, lat=10.0, lon=10.0):
    return {"planet": planet, "angle": angle, "polyline": [[lat, lon]]}


def test_houses_ruled_aries():
    assert houses_ruled(_chart("Aries"), "Saturn") == [10, 11]
    assert houses_ruled(_chart("Aries"), "Mars") == [1, 8]
    assert houses_ruled({}, "Mars") == []


def test_sixth_lord_on_ascendant_is_a_drain_for_love():
    # Aries lagna: Mercury rules 3 & 6. For love (neg 6/8/12, support 7/5/11)
    # Mercury on the AC line is a drain; the city sits on the line.
    w = lord_trap_watch(_chart("Aries"), "love", [_line("Mercury", "AC")], 10.0, 10.0)
    assert [x["kind"] for x in w] == ["lord_drain"] and w[0]["planet"] == "Mercury"


def test_planet_with_supportive_rulership_is_not_a_drain():
    # Mars rules 1st + 8th for Aries; 1st is supportive for career -> no flag.
    assert lord_trap_watch(_chart("Aries"), "career", [_line("Mars", "MC")], 10.0, 10.0) == []


def test_malefic_tenth_lord_on_mc_is_never_flagged_for_career():
    # Saturn rules the 10th for Aries: strength for career, not a trap.
    assert lord_trap_watch(_chart("Aries"), "career", [_line("Saturn", "MC")], 10.0, 10.0) == []


def test_malefic_seventh_lord_on_dc_is_strain_for_love():
    # Cancer lagna: 7th is Capricorn -> Saturn, a malefic.
    w = lord_trap_watch(_chart("Cancer"), "love", [_line("Saturn", "DC")], 10.0, 10.0)
    assert [x["kind"] for x in w] == ["lord_strain"]
    # Aries lagna: 7th is Libra -> Venus, a benefic -> no flag.
    assert lord_trap_watch(_chart("Aries"), "love", [_line("Venus", "DC")], 10.0, 10.0) == []


def test_far_line_and_wrong_angle_ignored():
    assert lord_trap_watch(_chart("Cancer"), "love", [_line("Saturn", "DC", 10.0, 40.0)], 10.0, 10.0) == []
    assert lord_trap_watch(_chart("Cancer"), "love", [_line("Saturn", "MC")], 10.0, 10.0) == []
