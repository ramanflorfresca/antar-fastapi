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


def test_merge_spans_joins_back_to_back_windows():
    from antar_engine.event_forecast import merge_spans
    items = [{"event": "career", "tier": "double", "start": "2026-10-13", "end": "2027-01-08", "rules": ["a"]},
             {"event": "career", "tier": "double", "start": "2027-01-08", "end": "2027-09-08", "rules": ["b"]},
             {"event": "career", "tier": "double", "start": "2028-01-01", "end": "2028-03-01", "rules": ["a"]}]
    out = merge_spans(items, key=lambda x: x["event"], tier_key="tier")
    assert [(o["start"], o["end"], o["windows"]) for o in out] == [
        ("2026-10-13", "2027-09-08", 2), ("2028-01-01", "2028-03-01", 1)]
    assert out[0]["rules"] == ["a", "b"]


def test_gate_lifted_by_exact_time_but_not_inside_one_minute():
    from antar_engine.event_forecast import build_forecast
    cd = {**CD, "lagna": {"sign_index": 9, "degree": 24.69}}   # ~2.8 min from a D-10 edge
    off = build_forecast(cd, "1974-11-26", [], today=date(2026, 10, 13))["d10"]["sensitivity"]
    on = build_forecast(cd, "1974-11-26", [], today=date(2026, 10, 13), birth_time_accuracy="exact")["d10"]["sensitivity"]
    assert off["fragile"] and off["gate"] and on["fragile"] and not on["gate"]
    cd2 = {**CD, "lagna": {"sign_index": 9, "degree": 24.1}}   # ~0.4 min from the edge
    edge = build_forecast(cd2, "1974-11-26", [], today=date(2026, 10, 13), birth_time_accuracy="exact")["d10"]["sensitivity"]
    assert edge["gate"]
