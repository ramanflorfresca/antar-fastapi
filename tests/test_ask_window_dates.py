"""[window-dates 2026-10-07] Parsed window bounds on the Ask payload.

The answer card can only LABEL the window ("Oct 2026 – Nov 2026"); to DRAW it
the client needs the two dates. It must never parse that label itself — the
label is localized to es/pt before it reaches the client, and a frontend that
parses "oct 2026 – nov 2026" in Spanish is a bug waiting for a Spanish user.
"""
from datetime import date

import pytest

from antar_engine.outcomes import parse_window

TODAY = date(2026, 10, 7)


@pytest.mark.parametrize("label,start,end", [
    ("Oct 2026 – Nov 2026", date(2026, 10, 1), date(2026, 11, 30)),
    ("Nov 2026 – Jan 2027",  date(2026, 11, 1), date(2027, 1, 31)),
    ("Oct 2026",             date(2026, 10, 1), date(2026, 10, 31)),
    ("Feb 2027 – May 2027",  date(2027, 2, 1),  date(2027, 5, 31)),
])
def test_the_chip_label_yields_the_bounds_the_card_will_draw(label, start, end):
    s, e = parse_window(label, TODAY)
    assert (s, e) == (start, end), label


def test_the_end_is_the_last_day_of_the_month_not_the_first():
    """The band has to cover the whole final month. If this returned the 1st,
    every drawn window would stop a month short."""
    _s, e = parse_window("Oct 2026 – Dec 2026", TODAY)
    assert e == date(2026, 12, 31)


def test_a_year_boundary_does_not_roll_backwards():
    s, e = parse_window("Dec 2026 – Feb 2027", TODAY)
    assert s == date(2026, 12, 1) and e == date(2027, 2, 28)
    assert e > s


@pytest.mark.parametrize("junk", ["", None, "soon", "later this year", "sometime"])
def test_an_unparseable_chip_yields_no_bounds(junk):
    """No dates means the client renders the label as text and draws nothing —
    which is correct. Inventing bounds would draw a bar that is a lie."""
    s, e = parse_window(junk or "", TODAY)
    assert not (s and e)


def test_bounds_are_ordered_whenever_both_are_present():
    for label in ("Oct 2026 – Nov 2026", "Oct 2026", "Nov 2026 – Jan 2027"):
        s, e = parse_window(label, TODAY)
        if s and e:
            assert s <= e, label
