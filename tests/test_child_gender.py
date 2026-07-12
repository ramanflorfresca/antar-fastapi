"""Unit tests for the classical progeny-gender leaning (child_gender)."""
from antar_engine.child_gender import child_gender_signal


def _chart(fifth_sign, fifth_lord, planets, d7_lagna, d7_planets):
    return {
        "house_lords": {"5": {"sign": fifth_sign, "lord": fifth_lord}},
        "planets": planets,
        "divisional_charts": {"d7": {"lagna": d7_lagna, "planets": d7_planets}},
    }


def test_all_male_indicators_lean_boy():
    # Odd signs (Aries/Leo/Sagittarius) + male planets everywhere.
    chart = _chart(
        "Aries", "Mars",
        {"Mars": {"sign": "Leo", "sign_index": 4, "house": 1},
         "Jupiter": {"sign": "Sagittarius", "sign_index": 8, "house": 5}},
        "Aries",
        {"Sun": {"sign": "Leo", "sign_index": 4, "house": 5}},
    )
    sig = child_gender_signal(chart)
    assert sig["leaning"] == "boy"
    assert sig["male"] > sig["female"]
    assert sig["female"] == 0


def test_all_female_indicators_lean_girl():
    # Even signs (Taurus/Cancer) + female planets.
    chart = _chart(
        "Taurus", "Venus",
        {"Venus": {"sign": "Taurus", "sign_index": 1, "house": 2},
         "Jupiter": {"sign": "Cancer", "sign_index": 3, "house": 4}},
        "Taurus",
        {"Moon": {"sign": "Cancer", "sign_index": 3, "house": 5}},
    )
    sig = child_gender_signal(chart)
    assert sig["leaning"] == "girl"
    assert sig["female"] > sig["male"]
    assert sig["male"] == 0


def test_neuter_lord_casts_no_nature_vote():
    # Saturn is neuter: it must NOT contribute a planet-nature vote, only its
    # (odd/even) sign counts.
    chart = _chart(
        "Aquarius", "Saturn",   # Aquarius odd -> male sign vote (w2)
        {"Saturn": {"sign": "Capricorn", "sign_index": 9, "house": 3}},  # even sign -> female
        "Sagittarius",
        {},
    )
    sig = child_gender_signal(chart)
    natures = [f for f in sig["factors"] if f["source"] == "5th-lord's nature"]
    assert natures == []                      # Saturn abstained on nature
    # sign votes still present (5th house Aquarius male, Saturn-in-Capricorn female)
    srcs = {f["source"] for f in sig["factors"]}
    assert "5th house sign" in srcs and "5th-lord's sign" in srcs


def test_d7_outweighs_d1():
    # D1 points female (Taurus 5th, Venus lord in Taurus, Jupiter in Taurus) but
    # the D7 progeny chart points male — the heavier D7 weighting must win.
    chart = _chart(
        "Taurus", "Venus",
        {"Venus": {"sign": "Taurus", "sign_index": 1, "house": 2},
         "Jupiter": {"sign": "Taurus", "sign_index": 1, "house": 2}},
        "Aries",  # D7 5th = Leo (male), lord Sun in Leo (male), Sun occupies it
        {"Sun": {"sign": "Leo", "sign_index": 4, "house": 5}},
    )
    sig = child_gender_signal(chart)
    assert sig["leaning"] == "boy"        # D7 dominance flips the D1 female lean


def test_lopsided_tally_is_clear():
    chart = _chart(
        "Aries", "Mars",
        {"Mars": {"sign": "Leo", "sign_index": 4, "house": 1},
         "Jupiter": {"sign": "Sagittarius", "sign_index": 8, "house": 5}},
        "Aries",
        {"Sun": {"sign": "Leo", "sign_index": 4, "house": 5}},
    )
    sig = child_gender_signal(chart)
    assert sig["leaning"] == "boy" and sig["strength"] == "clear"


def test_missing_data_returns_empty():
    assert child_gender_signal({}) == {}
    assert child_gender_signal({"planets": {}}) == {}
    assert child_gender_signal(None) == {}
