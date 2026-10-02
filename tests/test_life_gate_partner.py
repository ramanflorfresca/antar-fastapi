"""Partner wording follows the reader's known facts (2026-10-02 audit).

A live audit of ~20 reading surfaces for founder / divorced / separated /
single readers found three contradictions, all partner-related:
  - daily-signal beats.life_area: "your partner and the deals you make"
    (the house-7 THEME; the noun gate never covered it)
  - practice schedule, Lal Kitab year: "Don't force big moves in your wife"
    (a PERSON label used as an AREA — wrong grammar and wrong for a divorcé)
  - practice schedule, partnership rin card: "Write an honest letter to your
    partner"
"""
import re

import pytest

from antar_engine import lk_varshphal_year as lk
from antar_engine.life_context import (
    reset_active_life, resolve_life_facts, set_active_life,
)
from antar_engine import practice_engine as pe
from antar_engine.today_narration import _apply_life_context

PERSON = re.compile(r"\byour (wife|husband|spouse|partner)\b", re.I)


def _with(row, fn):
    tok = set_active_life(resolve_life_facts(row) if row is not None else None)
    try:
        return fn()
    finally:
        reset_active_life(tok)


@pytest.mark.parametrize("row,label", [
    ({"marital_status": "divorced"}, "your love life and partnerships"),
    ({"marital_status": "separated"}, "your love life and partnerships"),
    ({"life_relationship": "single"}, "your love life and partnerships"),
    (None, "your love life and partnerships"),                       # unknown
    ({"marital_status": "married"}, "your marriage"),
    ({"marital_status": "in_relationship"}, "your relationship"),
])
def test_spouse_planet_labels_an_area_from_known_facts(row, label):
    for gender in ("male", "female"):
        spouse = lk.R.spouse_karaka(gender)
        got = _with(row, lambda: lk._domain_label(spouse, 7, gender, True))
        assert got == label
        # the template that produced "big moves in your wife" now reads as an area
        assert not PERSON.search(f"Don't force big moves in {got} this year.")


def test_partnership_rin_practice_never_assumes_a_current_partner():
    texts = [v for k, v in pe.__dict__.items() if isinstance(v, dict) and "spouse_debt" in v]
    assert texts, "spouse_debt practice table not found"
    card = texts[0]["spouse_debt"]
    for key in ("IN", "GLOBAL"):
        assert not PERSON.search(card[key]), card[key]


@pytest.mark.parametrize("status,reworded", [
    ("single", True), ("divorced", True), ("separated", True), ("", True),
    ("married", False),
])
def test_today_partner_theme_reworded_unless_partnered(status, reworded):
    _, theme = _apply_life_context(
        "partner", ["a business partner"], "your partner and the deals you make",
        {"marital_status": status})
    if reworded:
        assert theme == "your partnerships and the deals you make"
    else:
        assert theme == "your partner and the deals you make"


def test_daily_beats_gate_covers_partner_next_to_boss():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    i = src.index("def _degate_boss_theme(_t):")
    block = src[i:i + 2500]
    assert '_ptn_beats is not True' in block and "your partnerships" in block
