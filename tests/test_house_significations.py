"""
tests/test_house_significations.py — the house -> literal-noun layer + wiring.

Pure functions (no ephemeris). Covers the canonical table, the selection
guardrails (domain-filtered, direction-aware, capped), the Today driver wiring,
and the Year engine-state noun_signals.
"""

from antar_engine.house_significations import (
    select_nouns, select_phrase, nouns_for_domain, resolve_signal,
    HOUSE_SIGNIFICATIONS, DOMAIN_PRIMARY_HOUSE,
)


# ── canonical table ──────────────────────────────────────────────────────────

def test_all_twelve_houses_present_with_required_keys():
    assert set(HOUSE_SIGNIFICATIONS.keys()) == set(range(1, 13))
    for h, sig in HOUSE_SIGNIFICATIONS.items():
        assert sig["theme"] and sig["nouns"]
        assert sig["positive"] and sig["adverse"]


def test_literal_nouns_match_competitor_examples():
    # the exact nouns the feedback called out
    assert "your mother" in HOUSE_SIGNIFICATIONS[4]["nouns"]
    assert "a vehicle" in HOUSE_SIGNIFICATIONS[4]["nouns"]
    assert "your boss" in HOUSE_SIGNIFICATIONS[10]["nouns"]
    assert any("loan" in n for n in HOUSE_SIGNIFICATIONS[6]["nouns"])
    assert "your partner" in HOUSE_SIGNIFICATIONS[7]["nouns"]
    assert "your father" in HOUSE_SIGNIFICATIONS[9]["nouns"]


# ── selection guardrails ─────────────────────────────────────────────────────

def test_select_nouns_is_capped():
    assert len(select_nouns(4, limit=2)) == 2
    assert len(select_nouns(6, limit=3)) <= 3


def test_sixth_house_is_domain_filtered():
    # the headline example: 6th in money = loan/credit; in health = routine
    money = select_nouns(6, "adverse", "money", 3)
    health = select_nouns(6, "adverse", "health", 3)
    assert any("loan" in n or "credit" in n for n in money)
    assert any("routine" in n for n in health)
    assert money != health


def test_direction_aware_phrase_flips():
    pos = select_phrase(4, "positive")
    adv = select_phrase(4, "adverse")
    assert pos != adv
    assert "gain" in pos or "support" in pos
    assert "expense" in adv or "care" in adv


def test_negative_normalizes_to_adverse():
    assert select_phrase(10, "negative") == select_phrase(10, "adverse")
    assert select_phrase(10, "caution") == select_phrase(10, "adverse")


def test_nouns_for_domain_resolves_primary_house():
    out = nouns_for_domain("relationships", "positive", 3)
    assert out["house"] == DOMAIN_PRIMARY_HOUSE["relationships"] == 7
    assert any("partner" in n for n in out["nouns"])


def test_resolve_signal_prefers_actual_house_over_domain():
    # activated house 10 given -> boss/career nouns, not the money default
    sig = resolve_signal(10, "money", "positive", 3)
    assert sig["house"] == 10
    assert any("raise" in n or "career" in n for n in sig["nouns"])


def test_resolve_signal_falls_back_to_domain_when_no_house():
    sig = resolve_signal(None, "money", "adverse", 3)
    assert sig["house"] == DOMAIN_PRIMARY_HOUSE["money"]
    assert sig["nouns"]


def test_resolve_signal_empty_when_nothing():
    assert resolve_signal(None, None) == {}


# ── Today wiring: summarize_drivers attaches the activated house's nouns ──────

def test_today_drivers_carry_concrete_nouns():
    from antar_engine.today_narration import summarize_drivers
    debug = {
        "votes": ["A:moon_house10:work:+3.2", "C:lk_amplify:work:+3.5"],
        "net": {"work": 6.7},
        "chosen": ["work"],
    }
    out = summarize_drivers(debug)
    work = out[0]
    assert work["domain"] == "work"
    # house 10 (from the moon_house10 vote) -> boss/career nouns
    assert any("boss" in n for n in work["concrete_nouns"])
    assert work["life_area"]            # theme present
    assert work["this_could_touch"]     # direction-bound phrase present


def test_today_drivers_fallback_house_from_domain_when_no_house_vote():
    from antar_engine.today_narration import summarize_drivers
    # only an LK vote (no moon_house) -> domain primary house fallback
    debug = {"votes": ["C:lk_avoid:money:-3.5"], "net": {"money": -3.5},
             "chosen": ["money"]}
    out = summarize_drivers(debug)
    assert out[0]["signal"] == "caution"
    assert out[0]["concrete_nouns"]     # resolved via DOMAIN_PRIMARY_HOUSE


def test_today_driver_nouns_jargon_free():
    from antar_engine.today_narration import summarize_drivers, _JARGON_RX
    debug = {"votes": ["A:moon_house4:relationships:-2.0"],
             "net": {"relationships": -2.0}, "chosen": ["relationships"]}
    for d in summarize_drivers(debug):
        for n in d["concrete_nouns"]:
            assert not _JARGON_RX.search(n), f"jargon: {n}"
        assert not _JARGON_RX.search(d["this_could_touch"])


# ── Year wiring: engine state gains concrete_nouns ───────────────────────────

def test_year_state_builds_concrete_nouns_from_areas():
    from antar_engine.year_narration import build_year_engine_state
    year = {
        "range": "JUN 10 '25 – JUN 09 '26", "polarity": "positive",
        "areas": [
            {"name": "Career", "bars": 4, "care": False, "note": ""},
            {"name": "Wealth", "bars": 2, "care": True, "note": ""},
        ],
        "stretch": {"worst": "autumn", "best": "spring"},
    }
    state = build_year_engine_state(
        year=year, attention=None, muntha="", highlights=[],
        chart_data={"planets": {}, "lagna": {"sign": "Capricorn"}},
        lk_data={}, birth_date="1974-06-10",
        current_md_row=None, next_md_row=None,
    )
    nouns = state.get("concrete_nouns") or []
    assert nouns, "year state should carry concrete nouns"
    # career area (positive) -> boss/career; wealth (care) -> savings/income flavor
    assert any("boss" in n or "career" in n or "promotion" in n for n in nouns)
