"""Unit tests for the scoring harness' arithmetic (not for any astrology)."""
from datetime import date, timedelta

from scripts import score_notable_charts as sc


def test_parse_pos_and_event_interval():
    assert abs(sc.parse_pos("Scorpio 19d54m") - (7 * 30 + 19 + 54 / 60)) < 1e-9
    assert sc.event_interval({"date": "1964"}) == (date(1964, 1, 1), date(1964, 12, 31))
    assert sc.event_interval({"date": "1964-12"}) == (date(1964, 12, 1), date(1964, 12, 31))
    assert sc.event_interval({"date": "1964-02-29"}) == (date(1964, 2, 29), date(1964, 2, 29))
    assert sc.event_interval({"date": "garbage"}) is None


def test_poisson_binomial_exact():
    assert abs(sc.poisson_binomial_tail([0.5, 0.5], 1) - 0.75) < 1e-12
    assert abs(sc.poisson_binomial_tail([0.5, 0.5], 2) - 0.25) < 1e-12
    assert sc.poisson_binomial_tail([0.5], 0) == 1.0
    assert sc.poisson_binomial_tail([0.3, 0.3, 0.3], 4) == 0.0


def test_bh_adjust_is_monotone_and_bounded():
    adj = sc.bh_adjust([0.01, 0.04, 0.03, 0.5])
    assert all(0 <= a <= 1 for a in adj)
    assert adj[0] <= adj[2] <= adj[1] <= adj[3] or adj[0] <= adj[2]
    assert abs(adj[0] - 0.04) < 1e-12 and adj[3] == 0.5


def test_hit_and_baseline_on_a_weekly_grid():
    a0 = date(2000, 1, 3)
    n = 100
    series = [False] * n
    for k in range(10, 20):
        series[k] = True                                    # firing weeks 10..19
    iv = (a0 + timedelta(weeks=12), a0 + timedelta(weeks=12))
    hit, p = sc.hit_and_baseline(series, a0, iv)
    assert hit is True and abs(p - 10 / 100) < 1e-9          # a one-week event overlaps with probability 10/100
    iv2 = (a0 + timedelta(weeks=50), a0 + timedelta(weeks=50))
    assert sc.hit_and_baseline(series, a0, iv2)[0] is False
    # a wider event overlaps more often (width 5: starts 6..19 overlap = 14 of 96 starts)
    wide = (a0 + timedelta(weeks=30), a0 + timedelta(weeks=34))
    assert abs(sc.hit_and_baseline(series, a0, wide)[1] - 14 / 96) < 1e-9
    assert sc.hit_and_baseline(series, a0, (a0 - timedelta(days=10), a0)) is None   # outside the grid
