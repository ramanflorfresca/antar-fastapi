

def test_pratyantar_derived_when_rows_have_only_md_ad(monkeypatch):
    """People sub-charts store MD+AD rows only; the inner sub-period is derived from the chart, never left off."""
    import antar_engine.event_evidence as ev
    from antar_engine.chart_identity import build_chart_identity
    monkeypatch.setattr(ev, "_vim_tree_live", lambda cd, jd, now: ({"pd": {"lord": "Venus"}}, None))
    from datetime import date
    rows = [{"level": "mahadasha", "lord_or_sign": "Saturn", "start_date": "2019-01-01", "end_date": "2038-01-01"},
            {"level": "antardasha", "lord_or_sign": "Mercury", "start_date": "2026-01-01", "end_date": "2028-01-01"}]
    cd = {"lagna": {"sign": "Leo", "degree": 10}, "planets": {"Sun": {"sign": "Leo", "house": 1}}, "birth_jd": 2450000.5}
    out = build_chart_identity(cd, rows, today=date(2026, 10, 11))
    assert out["current_period"].get("pratyantar")
