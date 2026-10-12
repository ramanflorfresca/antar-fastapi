"""Personal house-lord karakas for the places scorer (2026-10-12)."""
from antar_engine.places_concern import (
    CONCERN_MAP, chart_lords_for_concern, effective_karakas,
)

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def _chart(lagna_sign):
    return {"lagna_sign": lagna_sign}


def test_career_lord_is_tenth_lord():
    # Aries lagna -> 10th is Capricorn -> Saturn
    assert chart_lords_for_concern(_chart("Aries"), "career") == ["Saturn"]
    # Libra lagna -> 10th is Cancer -> Moon
    assert chart_lords_for_concern(_chart("Libra"), "career") == ["Moon"]


def test_money_two_lords():
    # Taurus lagna: 2nd Gemini (Mercury), 11th Pisces (Jupiter)
    assert chart_lords_for_concern(_chart("Taurus"), "money") == ["Mercury", "Jupiter"]
    # Gemini lagna: 2nd Cancer (Moon), 11th Aries (Mars)
    assert chart_lords_for_concern(_chart("Gemini"), "money") == ["Moon", "Mars"]


def test_same_lord_for_two_houses_is_deduped():
    # Aquarius lagna: 7th Leo (Sun), 11th Sagittarius (Jupiter) -> distinct;
    # Capricorn lagna: 7th Cancer (Moon), 11th Scorpio (Mars) -> distinct.
    # Libra lagna: 2nd Scorpio (Mars), 11th Leo (Sun) -> distinct.
    # Dedup is exercised by the effective list below.
    for sign in SIGNS:
        ks = effective_karakas(_chart(sign), "money")
        assert len(ks) == len(set(ks))


def test_lords_lead_and_generic_follow():
    ks = effective_karakas(_chart("Aries"), "career")
    assert ks[0] == "Saturn"
    assert set(CONCERN_MAP["career"]["karakas"]) <= set(ks)


def test_nodes_never_a_lord():
    for sign in SIGNS:
        for c in CONCERN_MAP:
            assert not {"Rahu", "Ketu"} & set(chart_lords_for_concern(_chart(sign), c))


def test_unknown_lagna_falls_back_to_generic():
    assert effective_karakas({}, "career") == CONCERN_MAP["career"]["karakas"]
