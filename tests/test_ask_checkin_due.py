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


# ── the check-back SENTENCE, not just the timestamp ───────────────────────
@pytest.mark.parametrize("lang,expected", [
    ("en",       "Antar will check back in February."),
    ("es",       "Antar volverá a preguntarte en febrero."),
    ("pt",       "O Antar vai voltar a perguntar em fevereiro."),
    ("hinglish", "Antar aapse February mein dobara poochhega."),
    ("hi",       "Antar फ़रवरी में आपसे फिर पूछेगा।"),     # Devanagari — never the Roman copy
])
def test_checkin_note_speaks_the_language_the_answer_was_written_in(lang, expected):
    """The FE built this line itself in en/es/pt only, so a Hinglish answer
    carried an English check-back line underneath it. Language belongs to the
    side that knows what language the answer is in."""
    assert oc.checkin_note("2027-02-03T00:00:00+00:00", lang) == expected


def test_hinglish_keeps_the_english_month_name():
    """Romanised Hindi says 'February', not the Devanagari month."""
    assert "February" in oc.checkin_note("2027-02-03T00:00:00+00:00", "hinglish")


def test_an_unknown_language_falls_back_to_english_rather_than_breaking():
    assert oc.checkin_note("2027-02-03T00:00:00+00:00", "fr").startswith("Antar will check back")


@pytest.mark.parametrize("bad", [None, "", "not-a-date", "2027-13-99", 12345])
def test_no_timestamp_means_no_promise(bad):
    """The card must never claim a check-back that is not scheduled."""
    assert oc.checkin_note(bad, "en") is None
