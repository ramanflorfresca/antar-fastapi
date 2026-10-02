"""Evening "did today land?" nudge + weekly accuracy receipt (2026-10-02)."""
from datetime import datetime, timedelta, timezone

from antar_engine import evening_checkin as ec

IST = 5.5
# 14:30 UTC = 20:00 IST on Fri 2 Oct 2026
EVE = datetime(2026, 10, 2, 14, 30, tzinfo=timezone.utc)


def _claim(**kw):
    r = {"feedback_status": "pending", "correlation_key": "daily-2026-10-02",
         "show_after": "2026-10-02T08:00:00+00:00",
         "trackable_claim": "A steady day for careful words and quiet financial moves."}
    r.update(kw)
    return r


def test_evening_due_only_for_todays_pending_claim_at_8pm_local():
    assert ec.evening_due(_claim(), EVE, IST)
    assert not ec.evening_due(_claim(), EVE - timedelta(hours=1), IST)          # 7 PM
    assert not ec.evening_due(_claim(feedback_status="yes"), EVE, IST)           # answered
    assert not ec.evening_due(_claim(correlation_key="daily-2026-10-01"), EVE, IST)  # yesterday
    assert not ec.evening_due(_claim(show_after="2026-10-02T15:00:00+00:00"), EVE, IST)  # not yet
    assert not ec.evening_due(_claim(trackable_claim=" "), EVE, IST)


def test_local_date_uses_the_persons_timezone():
    # 23:30 UTC Oct 1 is already Oct 2 in IST
    assert ec.daily_key_for(datetime(2026, 10, 1, 23, 30, tzinfo=timezone.utc), IST) == "daily-2026-10-02"


def test_evening_message_localized_and_clipped():
    t, b = ec.build_evening_message("x " * 200, "es")
    assert t == "¿Cómo te fue hoy?" and len(b) < 220 and "…" in b
    assert ec.build_evening_message("A calm day.", "en")[0] == "Did today land?"


def _ans(status, days_ago, claim="c"):
    at = (EVE - timedelta(days=days_ago)).isoformat()
    return {"feedback_status": status, "feedback_at": at, "created_at": at, "trackable_claim": claim}


def test_weekly_receipt_counts_only_answered_in_window():
    rows = [_ans("yes", 0, "best"), _ans("yes", 2), _ans("partial", 3), _ans("no", 4),
            _ans("skipped", 1), _ans("pending", 1), _ans("yes", 9)]  # last one outside window
    r = ec.weekly_receipt(rows, EVE, IST)
    assert (r["landed"], r["partly"], r["missed"], r["answered"]) == (2, 1, 1, 4)
    assert r["accuracy_pct"] == 62.5
    assert r["best_landed"] == "best"
    assert r["tracked"] == 6 and r["days_answered"] == 4


def test_weekly_message_is_honest_about_partly():
    r = {"answered": 6, "landed": 4, "partly": 1}
    assert ec.build_weekly_message(r, "en")[1].startswith("4 landed and 1 partly, out of 6")
    assert ec.build_weekly_message({"answered": 3, "landed": 2, "partly": 0}, "pt")[1].startswith("2 de 3")


def test_weekly_gate_and_slot():
    assert not ec.weekly_should_send({"answered": 1})
    assert ec.weekly_should_send({"answered": 2})
    sun_7pm_ist = datetime(2026, 10, 4, 13, 30, tzinfo=timezone.utc)  # Sun 19:00 IST
    assert ec.is_local_weekly_slot(sun_7pm_ist, IST)
    assert not ec.is_local_weekly_slot(sun_7pm_ist + timedelta(hours=1), IST)


def test_empty_week():
    r = ec.weekly_receipt([], EVE, IST)
    assert r["answered"] == 0 and r["accuracy_pct"] is None and not ec.weekly_should_send(r)


def test_evening_message_has_no_double_stop():
    _, body = ec.build_evening_message("Today lights up a venture — take it, but keep a stop.", "en")
    assert "stop”. Did it fit?" in body and ".”." not in body
