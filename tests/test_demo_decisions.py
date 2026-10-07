"""[demo-decisions 2026-10-07] The Decisions tab in the public demo.

GET /decisions required an Authorization header, the demo has no session, so it
422'd and the tab was hidden — which hid the one feature that distinguishes this
product from a horoscope app, from exactly the people it needs to convince.

Two rules keep that safe:
  1. Only the configured demo chart is readable without a token.
  2. The demo's seeded decisions are recomputed from TODAY, so the tab always
     shows one open, one upcoming and one closed, whenever it is opened.
"""
from datetime import date

import pytest

from antar_engine import demo_mode as dm
from antar_engine import saved_decisions as sd


# ── the seeded windows ────────────────────────────────────────────────────
@pytest.mark.parametrize("today", [
    date(2026, 1, 1), date(2026, 6, 15), date(2026, 10, 7),
    date(2026, 12, 31), date(2027, 2, 28),
])
def test_the_demo_always_shows_one_of_each_status(today):
    """A hardcoded month would quietly turn the whole list 'closed' a few months
    after it was written. These are offsets from today, so they never age."""
    seen = set()
    for _q, _v, o1, o2 in dm.DEMO_DECISIONS:
        start, end = dm._month_window(o1, o2, today)
        seen.add(sd.status_for(start, end, today))
    assert seen == {"open", "upcoming", "closed"}, f"got {seen} on {today}"


def test_windows_are_whole_months_and_ordered():
    for _q, _v, o1, o2 in dm.DEMO_DECISIONS:
        start, end = dm._month_window(o1, o2, date(2026, 10, 7))
        assert start.day == 1
        assert end >= start
        assert (end + __import__("datetime").timedelta(days=1)).day == 1, "end is a month-end"


def test_december_rollover_does_not_break_the_year():
    start, end = dm._month_window(0, 2, date(2026, 12, 15))
    assert start == date(2026, 12, 1) and end == date(2027, 2, 28)


@pytest.mark.parametrize("o1,o2,expected", [
    (0, 0, "Oct 2026"),
    (0, 2, "Oct 2026 – Dec 2026"),
])
def test_label_collapses_a_single_month(o1, o2, expected):
    start, end = dm._month_window(o1, o2, date(2026, 10, 7))
    assert dm._label(start, end) == expected


def test_every_seeded_verdict_is_one_the_card_can_render():
    from antar_engine.outcomes import _VERDICTS_TRACKED
    for _q, verdict, _a, _b in dm.DEMO_DECISIONS:
        assert verdict in _VERDICTS_TRACKED, verdict


def test_the_demo_never_queues_a_notification():
    """The seed must not set open_reminder_due_at: a demo visitor has no device
    and no consent, and the window-open job would otherwise pick these up."""
    sent = {}

    class _T:
        def insert(self, rows):
            sent["rows"] = rows
            return self

        def execute(self):
            class R:
                data = sent["rows"]
            return R()

    class _SB:
        def table(self, _n):
            return _T()

    n = dm.seed_decisions(_SB(), "demo-chart", today=date(2026, 10, 7))
    assert n == len(dm.DEMO_DECISIONS)
    assert all(r["open_reminder_due_at"] is None for r in sent["rows"])
    assert all(r["chart_id"] == "demo-chart" for r in sent["rows"])


def test_seeding_is_never_fatal():
    class _Boom:
        def table(self, _n):
            raise RuntimeError("no table")
    assert dm.seed_decisions(_Boom(), "c") == 0
    assert dm.seed_decisions(None, "") == 0


def test_saved_decisions_is_still_wiped_before_reseeding():
    """If it ever left RESET_TABLES the demo would accumulate every visitor's
    saved decisions, which is a privacy problem, not just clutter."""
    assert "saved_decisions" in dm.RESET_TABLES
