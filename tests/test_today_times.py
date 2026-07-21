"""
tests/test_today_times.py
The day card must have ONE authority on WHEN.   2026-07-21

A live card for the product owner carried four different answers to "when":
    computed best window        11:49 AM - 12:37 PM
    computed steer-clear         3:50 PM -  5:38 PM
    LLM move            "...before 10:50 PM - the late-night window..."
    LLM friction_for    "Between 7:39 PM and 8:51 PM is a caution window"
windows[] is computed from panchanga and is correct. The prose was inventing
its own times beside it. Prose says WHAT, windows say WHEN.

Run: ./venv311/bin/python -m pytest tests/test_today_times.py -q
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine.today_windows import (          # noqa: E402
    strip_invented_times, strip_invented_times_list,
    _first_purpose, _strip_avoid_prefix,
)

LIVE_MOVE = ("In career: make one deliberate, well-prepared move before 10:50 PM "
             "— the late-night window is your sharpest slot for anything that "
             "needs to land cleanly.")
LIVE_FRICTION = ("Between 7:39 PM and 8:51 PM is a caution window — do not sign, "
                 "commit, or initiate anything major.")


def test_strips_the_exact_live_contradiction():
    out = strip_invented_times(LIVE_MOVE)
    assert "10:50" not in out and "late-night" not in out
    assert "deliberate" in out and out.endswith(".")


def test_keeps_the_instruction_when_the_clause_was_only_timing():
    out = strip_invented_times(LIVE_FRICTION)
    assert "7:39" not in out and "8:51" not in out
    assert out.startswith("Do not sign")      # capitalised after clause drop


def test_leaves_prose_with_no_time_claim_untouched():
    src = ("Avoid forcing bold initiatives or competitive moves today — steady "
           "effort outperforms dramatic pushes.")
    assert strip_invented_times(src) == src


def test_spanish_is_handled_too():
    out = strip_invented_times(
        "Entre las 3:50 PM y las 5:38 PM es una franja de cautela — no firmes nada.")
    assert "3:50" not in out and out.startswith("No firmes")


def test_list_drops_entries_left_with_nothing():
    assert strip_invented_times_list(["Between 1:00 PM and 2:00 PM is a window.",
                                      "Rest today."]) == ["Rest today."]
    assert strip_invented_times_list(None) == []


def test_bare_day_quality_nouns_are_rejected_as_purposes():
    """"use it for art" / "Avoid ugliness" were the rendered results."""
    assert _first_purpose(["art", "design", "beautification"], "FB") == "FB"
    # "avoid ugliness" is two words but renders as the bare noun once the
    # avoid- prefix is stripped, so it must lose to a real phrase.
    assert _strip_avoid_prefix(
        _first_purpose(["avoid ugliness", "harsh environments"], "FB")
    ) == "harsh environments"


def test_activity_phrase_wins_over_noun():
    assert _first_purpose(
        ["the one thing that actually matters today", "art"], "FB"
    ).startswith("the one thing")
