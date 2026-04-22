"""
Unit tests for antar_engine/transit_events.py

Run:  pytest tests/test_transit_events.py -v

These tests exercise the transit event engine with Raman's natal
chart (Capricorn rising, well-known placements) across a 30-day
monthly range and a 1-year annual range.

If swisseph isn't installed in the test environment the whole
module skips — CI should install it.  Local venv311 already has it.
"""

from __future__ import annotations

import pytest
from datetime import date

from antar_engine.transit_events import (
    SIGNS,
    NAKSHATRAS,
    bucket_events_by_week,
    compute_transit_events_in_range,
)

try:
    import swisseph  # noqa: F401
    _HAS_SWE = True
except ImportError:
    _HAS_SWE = False

pytestmark = pytest.mark.skipif(
    not _HAS_SWE,
    reason="swisseph not installed — transit_events tests skipped",
)


# ─── Fixture chart ──────────────────────────────────────────────
@pytest.fixture
def raman_chart():
    """Raman's chart: Capricorn rising, Moon in Capricorn, per Supabase."""
    return {
        "lagna": {"sign": "Capricorn"},
        "planets": {
            "Sun":     {"sign": "Scorpio",     "house": 11, "degree_in_sign": 10.0},
            "Moon":    {"sign": "Capricorn",   "house": 1,  "degree_in_sign": 15.0},
            "Mars":    {"sign": "Libra",       "house": 10, "degree_in_sign": 20.0},
            "Mercury": {"sign": "Scorpio",     "house": 11, "degree_in_sign": 5.0},
            "Jupiter": {"sign": "Pisces",      "house": 3,  "degree_in_sign": 8.0},
            "Venus":   {"sign": "Sagittarius", "house": 12, "degree_in_sign": 22.0},
            "Saturn":  {"sign": "Gemini",      "house": 6,  "degree_in_sign": 12.0},
            "Rahu":    {"sign": "Capricorn",   "house": 1,  "degree_in_sign": 3.0},
            "Ketu":    {"sign": "Cancer",      "house": 7,  "degree_in_sign": 3.0},
        },
    }


# ─── API contract ───────────────────────────────────────────────
def test_returns_empty_for_reversed_range(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 5, 1), date(2026, 4, 1),
    )
    assert out == []


def test_returns_list_of_dicts(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30),
    )
    assert isinstance(out, list)
    if out:  # events are chart-dependent; just shape-check
        for ev in out:
            assert isinstance(ev, dict)
            assert "date" in ev
            assert "planet" in ev
            assert "event_type" in ev
            assert "detail" in ev


def test_events_sorted_by_date(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 6, 30),
    )
    if len(out) >= 2:
        dates = [ev["date"] for ev in out]
        assert dates == sorted(dates), "events must be date-sorted"


def test_event_type_is_enum(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30),
    )
    valid = {"ingress", "nakshatra_shift", "retro_start", "retro_end", "aspect"}
    for ev in out:
        assert ev["event_type"] in valid


def test_signs_are_from_canonical_list(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30),
    )
    for ev in out:
        if ev.get("sign"):
            assert ev["sign"] in SIGNS
        if ev.get("sign_prev"):
            assert ev["sign_prev"] in SIGNS


def test_nakshatras_are_from_canonical_list(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30),
    )
    for ev in out:
        if ev.get("nakshatra"):
            assert ev["nakshatra"] in NAKSHATRAS


def test_natal_house_in_range(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30),
    )
    for ev in out:
        if ev.get("natal_house") is not None:
            assert 1 <= ev["natal_house"] <= 12


# ─── Coverage expectations ──────────────────────────────────────
def test_slow_planets_have_at_least_one_event_over_a_year(raman_chart):
    """Jupiter/Saturn ALWAYS produce at least one ingress-or-aspect over 12 months."""
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2027, 3, 31),
        include_fast=False,
    )
    slow_events = [e for e in out if e["planet"] in ("Jupiter", "Saturn")]
    assert slow_events, "expected at least one Jupiter/Saturn event in 12 months"


def test_fast_planets_toggle_with_include_fast(raman_chart):
    """include_fast=False should suppress Sun/Moon/Mercury/Venus events."""
    wide = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30), include_fast=True,
    )
    slow = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30), include_fast=False,
    )
    wide_planets = {e["planet"] for e in wide}
    slow_planets = {e["planet"] for e in slow}
    # Slow output should not contain Sun/Moon (except if aspects triggered,
    # but those come from Sun as transit planet, which include_fast=False
    # suppresses entirely).
    assert not (slow_planets & {"Sun", "Moon", "Mercury", "Venus"}), (
        f"include_fast=False leaked fast planets: {slow_planets}"
    )
    # And the wide scan should have AT LEAST the slow scan's events
    assert len(wide) >= len(slow)


def test_aspect_events_include_natal_target(raman_chart):
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 6, 30),
    )
    for ev in out:
        if ev["event_type"] == "aspect":
            assert ev.get("natal_target"), "aspect event must name a natal target"
            assert ev["natal_target"] in raman_chart["planets"]
            assert ev.get("aspect_kind") in (
                "conjunction", "sextile", "square", "trine", "opposition",
            )


# ─── bucket_events_by_week ──────────────────────────────────────
def test_bucket_empty_input():
    assert bucket_events_by_week([], date(2026, 4, 1)) == []


def test_bucket_groups_by_monday():
    fake_events = [
        {"date": "2026-04-07", "planet": "Sun", "event_type": "ingress", "detail": "x"},
        {"date": "2026-04-09", "planet": "Moon", "event_type": "ingress", "detail": "y"},
        {"date": "2026-04-14", "planet": "Mars", "event_type": "ingress", "detail": "z"},
    ]
    buckets = bucket_events_by_week(fake_events, date(2026, 4, 1))
    assert len(buckets) == 2
    # First bucket: week of Apr 6 (Mon) — contains Apr 7, Apr 9
    assert buckets[0]["week_start"] == "2026-04-06"
    assert len(buckets[0]["events"]) == 2
    # Second bucket: week of Apr 13 — contains Apr 14
    assert buckets[1]["week_start"] == "2026-04-13"
    assert len(buckets[1]["events"]) == 1


def test_bucket_week_labels_are_human():
    fake_events = [
        {"date": "2026-04-07", "planet": "Sun", "event_type": "ingress", "detail": "x"},
    ]
    buckets = bucket_events_by_week(fake_events, date(2026, 4, 1))
    assert "April" in buckets[0]["week_label"]
    assert buckets[0]["week_label"].startswith("Week of")


# ─── Smoke: realistic monthly scan produces non-trivial output ──
def test_monthly_scan_nontrivial_for_raman(raman_chart):
    """
    For a realistic 30-day window on an established chart, the engine
    should produce SOME events — exact count varies by ephemeris data
    but zero events would indicate the compute path is broken.
    """
    out = compute_transit_events_in_range(
        raman_chart, date(2026, 4, 1), date(2026, 4, 30),
    )
    # Very permissive floor — the assertion is "the engine ran and
    # produced SOMETHING", not a specific count which would be brittle
    # to ephemeris updates.
    assert len(out) >= 1, "monthly scan returned no events — compute broken"
