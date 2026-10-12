"""Unit tests for antar_engine.capital_wiring (mechanics only, not validity)."""
from antar_engine.capital_wiring import SIGNS, analyze_capital_wiring


def chart(lagna, placements):
    """placements: {planet: sign_name}; longitude 15 deg into the sign."""
    return {"lagna": {"sign": lagna, "sign_index": SIGNS.index(lagna)},
            "planets": {p: {"longitude": SIGNS.index(s) * 30 + 15.0,
                            "sign_index": SIGNS.index(s)}
                        for p, s in placements.items()}}


# Spec section 9: Leo lagna. (The spec calls Sun "own sign" in the 10th; Taurus
# is Venus's sign, so Sun is neutral there. Placement is kept as written.)
LEO = chart("Leo", {"Sun": "Taurus", "Moon": "Cancer", "Mars": "Aries",
                    "Mercury": "Gemini", "Jupiter": "Sagittarius",
                    "Venus": "Aries", "Saturn": "Libra", "Rahu": "Pisces",
                    "Ketu": "Virgo"})


def test_never_raises_and_flags_unvalidated():
    for bad in (None, {}, {"planets": {}}, {"lagna": {"sign": "Leo"}}):
        r = analyze_capital_wiring(bad)
        assert r["available"] is False and r["validated"] is False


def test_leo_one_fact_is_not_counted_twice():
    r = analyze_capital_wiring(LEO)
    assert r["available"] and r["validated"] is False
    w = {w["houses"]: w for w in r["wires"]}
    # Jupiter (5th AND 8th lord) in the 5th and Mercury (11th lord) in the 11th
    # look at each other: that single fact lights BOTH 8-11 and 5-11.
    assert w[(8, 11)]["lords"] == w[(5, 11)]["lords"] == ("Jupiter", "Mercury")
    assert w[(8, 11)]["kinds"] == ["mutual_aspect"] and w[(8, 11)]["strict"]
    # ...but it is one independent connection. Distinct facts here:
    # Jupiter-Mercury, Jupiter-Venus (8-10), Mars-Jupiter (9-8).
    assert len(r["wires"]) == 4 and r["independent_count"] == 3
    assert "custodian" not in r["archetypes"]


def test_hard_drain_gains_lord_in_dusthana():
    # Leo lagna: Mercury rules 11th; put it in Pisces (8th house).
    c = chart("Leo", {"Sun": "Leo", "Moon": "Cancer", "Mars": "Aries",
                      "Mercury": "Pisces", "Jupiter": "Sagittarius",
                      "Venus": "Libra", "Saturn": "Capricorn",
                      "Rahu": "Taurus", "Ketu": "Scorpio"})
    r = analyze_capital_wiring(c)
    assert r["has_hard_drain"]
    assert any(f["id"] == "gains_in_dusthana" for f in r["drains"])


def test_rahu_8th_with_debilitated_saturn_is_flagged():
    # Leo lagna, Rahu in Pisces (8th), Saturn debilitated in Aries.
    c = chart("Leo", {"Sun": "Leo", "Moon": "Cancer", "Mars": "Leo",
                      "Mercury": "Gemini", "Jupiter": "Sagittarius",
                      "Venus": "Libra", "Saturn": "Aries",
                      "Rahu": "Pisces", "Ketu": "Virgo"})
    ids = {a["id"] for a in analyze_capital_wiring(c)["audit"]}
    assert "rahu8_weak_saturn" in ids


def test_saturn_dusthana_is_not_weak():
    # Saturn own sign in the 6th (Leo lagna: Capricorn) must not read as weak.
    c = chart("Leo", {"Sun": "Leo", "Moon": "Cancer", "Mars": "Leo",
                      "Mercury": "Gemini", "Jupiter": "Sagittarius",
                      "Venus": "Libra", "Saturn": "Capricorn",
                      "Rahu": "Pisces", "Ketu": "Virgo"})
    ids = {a["id"] for a in analyze_capital_wiring(c)["audit"]}
    assert "rahu8_weak_saturn" not in ids and "rahu8_saturn_ok" in ids


def test_no_verdict_or_timing_keys():
    r = analyze_capital_wiring(LEO)
    for k in ("verdict", "score", "tier", "windows", "dates"):
        assert k not in r
