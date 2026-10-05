"""[saved-decisions 2026-10-05] The user's own saved decision + the window-OPEN
reminder.

prediction_claims is what ANTAR said, logged silently so the engine can score
itself. This is what the USER chose to keep. The distinction is the point: it
changes what the app takes in, not only what it puts out.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from antar_engine import saved_decisions as sd

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


# ── status ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("start,end,today,expected", [
    (date(2026, 11, 1), date(2027, 1, 31), date(2026, 10, 5), "upcoming"),
    (date(2026, 9, 1),  date(2026, 12, 31), date(2026, 10, 5), "open"),
    (date(2026, 1, 1),  date(2026, 9, 30),  date(2026, 10, 5), "closed"),
    (None,              date(2026, 12, 31), date(2026, 10, 5), "open"),
    (date(2026, 11, 1), None,               date(2026, 10, 5), "upcoming"),
    (None,              None,               date(2026, 10, 5), "open"),
])
def test_status_for(start, end, today, expected):
    assert sd.status_for(start, end, today) == expected


def test_status_is_open_on_both_boundary_days():
    """A window that starts today is open today, and one that ends today is
    still open today — an off-by-one here silently drops a whole day."""
    assert sd.status_for(date(2026, 10, 5), date(2026, 12, 1), date(2026, 10, 5)) == "open"
    assert sd.status_for(date(2026, 9, 1), date(2026, 10, 5), date(2026, 10, 5)) == "open"


# ── when the reminder fires ───────────────────────────────────────────────
def test_future_window_reminds_at_local_8am_on_the_start_day():
    due = sd.open_reminder_due(date(2026, 11, 1), tz_offset_hours=0, now=NOW)
    assert due == datetime(2026, 11, 1, sd.LOCAL_HOUR, tzinfo=timezone.utc)


def test_tz_offset_shifts_the_utc_instant_so_everyone_gets_their_own_morning():
    ist = sd.open_reminder_due(date(2026, 11, 1), tz_offset_hours=5.5, now=NOW)
    assert ist == datetime(2026, 11, 1, sd.LOCAL_HOUR, tzinfo=timezone.utc) - timedelta(hours=5.5)
    est = sd.open_reminder_due(date(2026, 11, 1), tz_offset_hours=-5, now=NOW)
    assert est == datetime(2026, 11, 1, sd.LOCAL_HOUR, tzinfo=timezone.utc) + timedelta(hours=5)


def test_an_already_open_window_reminds_next_morning_not_instantly_and_not_never():
    """The common case: people save the answer they just read, and its window is
    already live. Firing immediately is noise; dropping it loses the feature."""
    due = sd.open_reminder_due(date(2026, 9, 1), tz_offset_hours=0, now=NOW)
    assert due is not None and due > NOW
    assert due == datetime(2026, 10, 6, sd.LOCAL_HOUR, tzinfo=timezone.utc)


def test_no_start_date_means_nothing_to_announce():
    assert sd.open_reminder_due(None, 0, NOW) is None


# ── the row ───────────────────────────────────────────────────────────────
def test_build_row_keeps_the_timing_label_the_person_actually_read():
    r = sd.build_row("c1", "Is this the right time to change jobs?",
                     {"verdict": "not_yet", "timing": "Nov 2026 – Jan 2027",
                      "window_start": "2026-11-01", "window_end": "2027-01-31"},
                     language="en", now=NOW)
    assert r["verdict"] == "NOT_YET"
    assert r["timing_label"] == "Nov 2026 – Jan 2027"   # verbatim, already localized
    assert r["window_start"] == "2026-11-01" and r["window_end"] == "2027-01-31"
    assert r["open_reminder_due_at"].startswith("2026-11-01T08:00")


def test_build_row_survives_an_answer_with_no_dates():
    r = sd.build_row("c1", "What should I focus on?", {"read": "..."}, now=NOW)
    assert r["window_start"] is None and r["open_reminder_due_at"] is None
    assert r["question"] == "What should I focus on?"


def test_question_and_note_are_bounded():
    r = sd.build_row("c1", "q" * 900, {}, note="n" * 2000, now=NOW)
    assert len(r["question"]) <= 500 and len(r["note"]) <= 1000


# ── copy ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("lang,needle", [
    ("en", "Your window is open"),
    ("es", "Tu ventana está abierta"),
    ("pt", "Sua janela está aberta"),
    ("hi", "Aapki window khul gayi"),
    ("hinglish", "Aapki window khul gayi"),
])
def test_the_reminder_speaks_the_language_the_decision_was_saved_in(lang, needle):
    """English-only copy here would be the same silent-i18n bug as everywhere
    else — es/pt/Hinglish users getting an English push."""
    title, body = sd.push_message({"question": "Should I take the offer?", "language": lang})
    assert title == needle and body


def test_a_long_question_is_shortened_not_dumped_into_the_push():
    title, body = sd.push_message(
        {"question": "Is this genuinely the right moment for me to leave my job and "
                     "start the consulting business I have been planning for years?",
         "language": "en"})
    assert "…" in body and len(body) < 220


def test_whatsapp_line_carries_the_window_label_when_there_is_one():
    row = {"question": "Should I take the offer?", "language": "en",
           "timing_label": "Nov 2026 – Jan 2027"}
    assert "(Nov 2026 – Jan 2027)" in sd.whatsapp_message(row)
    assert "(" not in sd.whatsapp_message({"question": "q", "language": "en"})


def test_copy_never_raises_on_an_empty_row():
    assert sd.push_message({})[0]
    assert sd.whatsapp_message({})
