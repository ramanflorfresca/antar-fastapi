from datetime import date

from antar_engine.event_forecast import build_forecast

CD = {"lagna": {"sign_index": 4, "degree": 10.0},
      "planets": {n: {"sign_index": s, "degree": d, "longitude": s * 30 + d}
                  for n, s, d in [("Sun", 4, 25), ("Moon", 0, 20), ("Mars", 9, 15), ("Mercury", 4, 12),
                                  ("Jupiter", 4, 8), ("Venus", 4, 5), ("Saturn", 2, 3),
                                  ("Rahu", 2, 9), ("Ketu", 9, 9)]}}


def test_forecast_shape_and_determinism():
    vim = [{"planet_or_sign": "Venus", "start_date": "2020-01-01", "end_date": "2040-01-01", "level": "mahadasha"}]
    a = build_forecast(CD, "1981-03-02", vim, today=date(2026, 10, 13))
    assert a == build_forecast(CD, "1981-03-02", vim, today=date(2026, 10, 13))
    assert a["available"] and a["window"] == ["2026-10-13", "2028-10-13"]
    assert len(a["lal_kitab"]["annual"]) == 2
    assert all(e["rules"] for e in a["events"])


def test_incomplete_chart_is_unavailable():
    assert build_forecast({}, "1981-03-02", [], today=date(2026, 10, 13))["available"] is False
