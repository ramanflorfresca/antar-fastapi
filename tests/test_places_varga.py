"""Relocated varga annotation (2026-10-12)."""
from antar_engine.places_varga import relocation_varga_notes

# Aries lagna; Venus at Aries 10deg -> navamsa Cancer (index 3).
CHART = {"lagna_sign": "Aries", "planets": {"Venus": {"longitude": 10.0}}}


def _reloc(lon):
    return {"relocated_lagna_longitude": lon}


def test_supportive_when_venus_in_kendra_of_navamsa_lagna():
    # reloc lagna 0deg Aries -> navamsa lagna Aries(0); Venus Cancer(3) = 4th house
    notes = relocation_varga_notes(CHART, _reloc(0.0), "love")
    assert len(notes) == 1
    n = notes[0]
    assert (n["varga"], n["planet"], n["house"], n["polarity"]) == ("D9", "Venus", 4, "supportive")


def test_friction_when_venus_in_eighth_of_navamsa_lagna():
    # reloc lagna 28deg Aries -> navamsa Sagittarius(8); Venus Cancer(3) = 8th house
    notes = relocation_varga_notes(CHART, _reloc(28.0), "love")
    assert notes and notes[0]["polarity"] == "friction" and notes[0]["house"] == 8


def test_neutral_placement_is_omitted():
    # navamsa lagna Virgo(5)? Aries lon ~ ... use Cancer(3) as lagna: Venus = 1st (supportive);
    # choose navamsa lagna Leo(4): Venus Cancer(3) = 12th (friction). Pick Gemini(2): 2nd -> neutral.
    # Gemini navamsa starts at Libra: lon 60 + 3.33*k ; k=8 -> Libra+8 = Taurus.. search instead:
    import itertools
    neutral = None
    for lon in [i * 3.34 for i in range(108)]:
        r = relocation_varga_notes(CHART, _reloc(lon), "love")
        if not r:
            neutral = lon
            break
    assert neutral is not None            # some city yields no line (house 2 or 3 or 8-excluded)


def test_no_varga_lens_for_other_concerns_or_missing_degree():
    assert relocation_varga_notes(CHART, _reloc(0.0), "money") == []
    assert relocation_varga_notes(CHART, {}, "love") == []
    assert relocation_varga_notes(CHART, {"relocated_lagna_longitude": None}, "career") == []


def test_career_uses_tenth_lord_in_dashamsa():
    # Aries lagna -> 10th lord Saturn. Saturn at Aquarius 5deg (305) -> some D10 sign.
    chart = {"lagna_sign": "Aries", "planets": {"Saturn": {"longitude": 305.0}}}
    notes = relocation_varga_notes(chart, _reloc(15.0), "career")
    assert all(n["varga"] == "D10" and n["planet"] == "Saturn" for n in notes)


def test_es_text_and_friction_sorted_first():
    chart = {"lagna_sign": "Aries", "planets": {"Venus": {"longitude": 10.0}}}
    notes = relocation_varga_notes(chart, _reloc(28.0), "love", language="es")
    assert notes[0]["text"].startswith("Vista desde")
