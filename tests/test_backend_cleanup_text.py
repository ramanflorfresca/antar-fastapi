from datetime import date

import pytest

from antar_engine import outcomes as oc
from antar_engine.output_strips import apply_user_facing_strips as A, tidy_energy_phrases as T


def test_planet_by_role_compounds_and_house_of_phrases_do_not_reach_the_user():
    t = ("his career energy is concentrated (Sun, the mind-planet and the wisdom-planet all stacked in his "
         "house of work): he spreads across too many things.")
    out = A(t, language="en", field_type="plain", source="llm").lower()
    assert "-planet" not in out and "house of" not in out
    assert "work life" in out and "another strong influence" in out


@pytest.mark.parametrize("house,plain", [("house of money", "money life"), ("house of marriage", "close relationships"),
                                         ("house of health", "health"), ("house of home", "home life")])
def test_house_of_phrases_become_plain_life_areas(house, plain):
    assert plain in A(f"it sits in the {house} now", language="en", field_type="plain", source="llm")


def test_article_adjective_before_a_swapped_planet_is_repaired():
    assert T("The classical your love and partnership energy glyph engraved on silver — the carrier.") == \
        "The classical glyph for your love and partnership energy engraved on silver — the carrier."


def test_possessive_on_a_swapped_planet_is_repaired():
    assert T("Keep it with something floral to honour your love and partnership energy's quality.") == \
        "Keep it with something floral to honour the quality of your love and partnership energy."
    assert T("The Guadalupana carries your love and partnership energy's tender, beautiful, devotional feminine grace, loved across Latin America.") == \
        "The Guadalupana carries the tender, beautiful, devotional feminine grace of your love and partnership energy, loved across Latin America."


@pytest.mark.parametrize("ok", ["Giving feeds your love and partnership energy.", "Nothing to change here.", "", None, 5])
def test_tidy_leaves_good_text_and_odd_input_alone(ok):
    assert T(ok) == ok


def test_a_yesno_window_never_runs_backwards():
    p = {"verdict": "CONDITIONAL", "lean": "CONDITIONAL", "verify_after": "2026-11-03", "timing": "Jan 20"}
    c = oc.build_claim("c1", "Will I close a new deal this month?", p, mode="yesno", topic="general",
                       language="en", today=date(2026, 10, 3))
    assert c["window_start"] <= c["window_end"] and c["window_end"] == "2026-11-03"
    assert c["window_start"] == "2026-10-03"


def test_a_normal_yesno_window_is_unchanged():
    p = {"verdict": "YES", "lean": "YES", "verify_after": "2026-12-01", "timing": "Nov 10"}
    c = oc.build_claim("c1", "Will it close?", p, mode="yesno", topic="general", language="en", today=date(2026, 10, 3))
    assert c["window_start"] == "2026-11-10" and c["window_end"] == "2026-12-01"
