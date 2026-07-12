"""Guards for the live-audit fixes (2026-07-12): P2 timing, P5 axis, P6 casing."""
from antar_engine.plain_english import _repair_contradictory_window
from antar_engine.narration_polish import fix_capitalization
from antar_engine.places_templates import AXIS


# ── P2: contradictory timing_window repair ──────────────────────────────────
def test_far_date_with_short_horizon_is_repaired():
    # "next six months (strongest through February 2028)" — Feb 2028 is far out.
    out = _repair_contradictory_window("next six months (strongest through February 2028)")
    assert "next six months" not in out.lower()
    assert "February 2028" in out


def test_pure_relative_window_untouched():
    assert _repair_contradictory_window("Next 3 weeks") == "Next 3 weeks"


def test_pure_absolute_window_untouched():
    assert _repair_contradictory_window("April–September 2026") == "April–September 2026"


def test_near_date_within_horizon_untouched():
    # A date inside the stated horizon is not a contradiction; leave it.
    assert _repair_contradictory_window("next month") == "next month"


# ── P5: axis reframes carry no jargon ("axis"/"eje") ────────────────────────
def test_axis_map_has_no_jargon_word():
    for lang, m in AXIS.items():
        for angle, phrase in m.items():
            assert "axis" not in phrase.lower(), f"{lang}/{angle}: {phrase}"
            assert "eje" not in phrase.lower(), f"{lang}/{angle}: {phrase}"


# ── P6: em-dash is not a sentence boundary ──────────────────────────────────
def test_no_capital_after_em_dash():
    s = "you're in a favorable window — whether a raise or a loan. funders look hard."
    out = fix_capitalization(s)
    assert "— whether" in out            # stays lowercase after the dash
    assert out.startswith("You're")       # string start still capitalised
    assert ". Funders" in out             # real sentence boundary still capitalised


def test_en_dash_range_not_capitalised():
    assert fix_capitalization("open april–september window") == "Open april–september window"
