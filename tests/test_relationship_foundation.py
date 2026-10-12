from antar_engine.relationship_foundation import analyze_foundation


def _chart(extra: dict):
    """Aries lagna; Jupiter (12th lord) in Taurus puts the Upapada in Cancer, so the sustaining
    house (2nd from UL) is Leo, ruled by the Sun."""
    base = {
        "Jupiter": {"sign": "Taurus", "house": 2, "degree": 20.0},
        "Sun": {"sign": "Leo", "house": 5, "degree": 15.0},
        "Moon": {"sign": "Virgo", "house": 6, "degree": 25.0},
        "Mars": {"sign": "Aries", "house": 1, "degree": 22.0},
        "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0},
        "Venus": {"sign": "Libra", "house": 7, "degree": 12.0},
        "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0},
        "Rahu": {"sign": "Pisces", "house": 12, "degree": 5.0},
        "Ketu": {"sign": "Virgo", "house": 6, "degree": 5.0},
    }
    base.update(extra)
    return {"planets": base, "lagna": {"sign": "Aries"}}


def test_fragile_sustenance_blocks_reunion_window():
    # Saturn + Rahu sit in the sustaining house; its lord (Sun) is 8 houses from the marriage point
    a = analyze_foundation(_chart({
        "Saturn": {"sign": "Leo", "house": 5, "degree": 27.0},
        "Rahu": {"sign": "Leo", "house": 5, "degree": 5.0},
        "Sun": {"sign": "Aquarius", "house": 11, "degree": 15.0},
        "Venus": {"sign": "Virgo", "house": 6, "degree": 12.0}}))      # partner-significator debilitated, in a dusthana
    assert a["available"] and a["sustenance"]["ul_sign"] == "Cancer" and a["sustenance"]["second_from_ul"] == "Leo"
    assert a["sustenance"]["level"] == "fragile" and a["foundation"]["band"] == "fragile"
    txt = " ".join(a["facts"])
    assert "do NOT hold out a reunion" in txt


def test_sound_sustenance_and_hedge_always_present():
    a = analyze_foundation(_chart({
        "Venus": {"sign": "Leo", "house": 5, "degree": 12.0},
        "Mercury": {"sign": "Leo", "house": 5, "degree": 18.0},
        "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0}}))
    assert a["sustenance"]["level"] == "sustains"
    assert a["foundation"]["band"] != "fragile"
    assert "never say what he or she feels" in " ".join(a["facts"])   # epistemic hedge on every band


def test_spouse_indicator_states():
    # lowest-degree planet is the Darakaraka: Mars at 1° with Ketu in the 8th -> detached
    a = analyze_foundation(_chart({"Mars": {"sign": "Scorpio", "house": 8, "degree": 1.0},
                                   "Ketu": {"sign": "Scorpio", "house": 8, "degree": 5.0}}))
    assert a["spouse_indicator"]["planet"] == "Mars" and a["spouse_indicator"]["state"] == "detached"
    b = analyze_foundation(_chart({"Jupiter": {"sign": "Taurus", "house": 2, "degree": 0.5},
                                   "Venus": {"sign": "Libra", "house": 7, "degree": 12.0}}))
    assert b["spouse_indicator"]["planet"] == "Jupiter"


def test_facts_use_no_jargon():
    a = analyze_foundation(_chart({}))
    txt = " ".join(a["facts"]).lower()
    for bad in ("upapada", "darakaraka", "navamsa", "d-9", "saturn", "rahu", "ketu", "house of"):
        assert bad not in txt


def test_fail_open():
    assert analyze_foundation({}) == {"available": False}
    assert analyze_foundation(None) == {"available": False}


def test_fragile_band_without_unsound_flag_still_blocks_window():
    from antar_engine.relationship_foundation import foundation_facts
    sus = {"level": "fragile"}; dki = {"state": "mixed"}; d9 = {"level": "partial"}
    assert "do NOT hold out a reunion" in " ".join(foundation_facts("fragile", sus, dki, d9, False))
    assert "do NOT hold out a reunion" not in " ".join(foundation_facts("mixed", sus, dki, d9, False))
