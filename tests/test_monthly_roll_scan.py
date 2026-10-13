"""The monthly event scan must cover the period of the (rolled) reference date, not the one that just closed."""
import inspect
from datetime import date

from antar_engine import monthly_deepdive
from antar_engine.jyotish_periods import month_period


def test_rolled_reference_date_selects_next_period():
    # birth day 8, today Oct 3 (inside the 7-day roll window): reference rolls to Oct 8
    ps, _ = month_period("1990-03-08", date(2026, 10, 3), roll_ahead_days=7)
    assert ps == "2026-10-08"
    # resolving with the rolled date must give the same period start, not Sep 8
    assert month_period("1990-03-08", date(2026, 10, 8))[0] == "2026-10-08"
    assert month_period("1990-03-08", date(2026, 10, 3))[0] == "2026-09-08"  # the old wall-clock bug


def test_scan_uses_reference_date():
    src = inspect.getsource(monthly_deepdive)
    assert "_p1_mp(birth_date, now.date())" in src
    assert "_p1_mp(birth_date) if" not in src
