from datetime import datetime

from antar_engine import vim_levels as vl

ROWS = vl.parse_rows([
    {"planet_or_sign": "Rahu", "level": "mahadasha", "start_date": "2026-08-13", "end_date": "2044-08-13"},
    {"planet_or_sign": "Rahu", "level": "antardasha", "start_date": "2026-08-13", "end_date": "2029-04-25"},
    {"planet_or_sign": "Jupiter", "level": "antardasha", "start_date": "2029-04-25", "end_date": "2031-09-18"},
])


def test_subdivision_is_proportional_and_complete():
    parts = vl.subdivide("Rahu", datetime(2026, 8, 13), datetime(2029, 4, 25))
    assert [p["lord"] for p in parts] == ["Rahu", "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun", "Moon", "Mars"]
    assert parts[0]["start"] == datetime(2026, 8, 13) and parts[-1]["end"] == datetime(2029, 4, 25)
    total = (datetime(2029, 4, 25) - datetime(2026, 8, 13)).total_seconds()
    assert abs((parts[0]["end"] - parts[0]["start"]).total_seconds() - total * 18 / 120) < 1


def test_running_lords_nest_correctly():
    r = vl.running_lords(ROWS, datetime(2026, 10, 13))
    assert r["md"] == "Rahu" and r["ad"] == "Rahu" and r["pd"] == "Rahu" and r["sd"]
    later = vl.running_lords(ROWS, datetime(2029, 6, 1))
    assert later["ad"] == "Jupiter" and later["pd"] == "Jupiter"
    assert vl.running_lords(ROWS, datetime(2000, 1, 1)) == {"md": None, "ad": None, "pd": None, "sd": None}


def test_window_collects_every_lord_that_runs():
    w = vl.lords_in_window(ROWS, datetime(2026, 10, 13), datetime(2027, 4, 13), levels=("pd",), step_days=2)
    assert "Rahu" in w
    month = vl.lords_in_window(ROWS, datetime(2026, 10, 13), datetime(2026, 11, 13), levels=("pd", "sd"), step_days=1)
    assert len(month) >= 2                                                    # sookshma lords change within weeks


def test_levels_are_always_computable_from_the_moon():
    rows = vl.rows_from_moon(24.4, datetime(1974, 11, 26, 12))             # Moon at 24d24m Aries: Bharani, Venus period
    assert rows[0]["level"] == "md" and rows[0]["lord"] == "Venus"
    assert sum(1 for r in rows if r["level"] == "md") == 11
    r = vl.running_lords(rows, datetime(2026, 10, 13))
    assert all(r[k] for k in ("md", "ad", "pd", "sd"))
    # balance of the first period: the Moon is 0.6*(13d20m) into Bharani, so about 40% of Venus's 20 years remains
    first = rows[0]
    assert abs(((first["end"] - datetime(1974, 11, 26, 12)).days / 365.25) - 20 * (1 - (24.4 % (360 / 27)) / (360 / 27))) < 0.01
