"""[checkin-visible 2026-10-05] The Ask payload must carry checkin_due_at so the
answer card can say when Antar will come back and ask whether it happened.

The store listing's subtitle is "Dated answers, then it checks" — the card showed
the date and said nothing about the check. These pin the two rules that keep the
promise honest: it is present for claims the check-in job really sends, and
absent for claims it never asks about.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from antar_engine import outcomes as oc


def _explore_payload():
    return {"verdict": "YES", "timing": "Oct 2026",
            "read": "Yes — career window is open now, through October 2026.",
            "confidence": "medium"}


def test_build_claim_sets_checkin_due_three_days_after_the_window_ends():
    c = oc.build_claim("chart-1", "Is this the right time to change jobs?",
                       _explore_payload(), mode="explore", topic="career",
                       language="en", today=date(2026, 10, 5))
    assert c, "a dated verdict must produce a claim"
    assert c["source"] == "ask_explore"
    due = datetime.fromisoformat(c["checkin_due_at"])
    end = date.fromisoformat(c["window_end"])
    assert due.date() == end + timedelta(days=oc.CHECKIN_DELAY_DAYS)
    assert due.tzinfo is not None, "stored as an aware UTC timestamp"


def test_explore_claims_are_the_ones_the_job_actually_asks_about():
    """The payload field is gated on this set — if ask_explore ever leaves it,
    the answer card would promise a check-back nobody sends."""
    assert "ask_explore" in oc.CHECKIN_SOURCES


def test_yesno_claims_are_never_checked_in_so_must_not_promise_one():
    """A Yes/No claim is recorded but never asked about. Surfacing
    checkin_due_at there would be a promise the product does not keep."""
    assert "ask_yesno" not in oc.CHECKIN_SOURCES


def test_an_undated_answer_makes_no_claim_and_so_no_promise():
    for p in ({"verdict": "YES", "read": "Things are opening up."},
              {"read": "Here is some reflection.", "timing": None}):
        assert oc.build_claim("chart-1", "q", p, mode="explore", topic="career",
                              language="en", today=date(2026, 10, 5)) is None


def test_a_replayed_locked_answer_is_not_a_new_claim():
    p = _explore_payload(); p["locked"] = True
    assert oc.build_claim("chart-1", "q", p, mode="explore", topic="career",
                          language="en", today=date(2026, 10, 5)) is None
