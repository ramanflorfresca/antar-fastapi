"""[ritual-why 2026-10-15] Every Rituals card carries a plain reason, free of chart jargon; chants only offer Play when audio exists."""
from antar_engine import ritual_why as rw, ritual_today as rt


def _clean(o):
    return rt.jargon_leaks(o) == []


def test_food_why_balance_uses_the_days_character():
    w = rw.food_why({"mode": "balance", "planet": "Saturn", "why_eat": "x"})
    assert w and w["state_plain"] and w["helps_plain"] and w["adds_plain"] and w["variation_plain"]
    assert _clean(w)


def test_food_why_strengthen_has_adds_line():
    w = rw.food_why({"mode": "strengthen", "planet": "Mars", "why_eat": "These foods feed your drive and stamina — that is what today is running on"})
    assert w["adds_plain"] and w["state_plain"].endswith(".")


def test_food_card_avoid_line_no_longer_contradicts_eat():
    card = rt.food_card({"food": {"eat": ["Triphala"], "avoid": ["Sweets"], "mode": "balance", "planet": "Saturn",
                                  "why_avoid": "these push the day further in the direction it is already leaning"}}, set())
    assert "direction it is already leaning" not in card["details"]["why_avoid_plain"]
    assert card["why_this"]["state_plain"]


def test_verse_why_has_cause_theme_and_variation():
    w = rw.verse_why({"season": "expansive", "season_cause": {"kind": "moon", "house": 3},
                      "verse": {"themes": ["courage", "action"]}})
    assert "favours moving forward" in w["cause_plain"]
    assert "courage and action" in w["about_plain"]
    assert "rotates" in w["variation_plain"] and _clean(w)


def test_verse_why_none_without_season():
    assert rw.verse_why({}) is None


def test_mantra_why_names_the_area_not_the_planet():
    w = rw.mantra_why("Mercury")
    assert "thinking, speaking and deals" in w["supports_plain"] and _clean(w)


def test_gayatri_chant_has_text_and_audio_only_when_listed(monkeypatch):
    c = rw.chant_for("Recite the Gayatri mantra regularly.")
    assert c["name"] == "Gayatri" and c["sanskrit"] and c["audio_url"].endswith("/gayatri-en.mp3") and c["audio_credit_plain"]
    monkeypatch.setitem(rw._data(), "audio_available", [])
    assert "audio_url" not in rw.chant_for("Recite the Gayatri mantra regularly.")


def test_chalisa_and_sahasranama_are_text_only():
    for t in ("Hanuman Chalisa daily", "Chant Vishnu Sahasranama"):
        c = rw.chant_for(t)
        assert c and "audio_url" not in c and c["how_plain"]


def test_remedy_card_how_row_matches_the_chant():
    card = rt.remedy_card(rt._date(2026, 10, 15), {"remedies": ["Recite the Hanuman Chalisa daily."], "verdict": "mixed"}, set())
    assert "forty verses" in card["details"]["how_plain"] and card["chant"]["name"] == "Hanuman Chalisa"
