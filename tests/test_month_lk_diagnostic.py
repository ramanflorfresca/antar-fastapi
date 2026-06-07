"""
tests/test_month_lk_diagnostic.py — Month LK condition engine + masa lord.

compute_lk_month_diagnostic aggregates the 7 weekday-lord LK conditions +
natal sleeping planets into a month-scale signal with a votes trail. Pure
computation (no Claude, no network). Run via the swisseph-stubbed runner.
"""

from datetime import datetime


def _chart():
    # Capricorn lagna; houses set so a couple of planets sit in sleeping houses
    P = {
        "Sun": ("Scorpio", 11), "Moon": ("Pisces", 3), "Mars": ("Libra", 10),
        "Mercury": ("Libra", 10), "Jupiter": ("Aquarius", 2),
        "Venus": ("Scorpio", 11), "Saturn": ("Gemini", 6),
        "Rahu": ("Scorpio", 11), "Ketu": ("Taurus", 5),
    }
    return {"lagna": {"sign": "Capricorn", "sign_index": 9},
            "planets": {p: {"sign": s, "house": h} for p, (s, h) in P.items()}}


def test_month_lk_diagnostic_shape_and_votes():
    from antar_engine.lal_kitab_advanced import compute_lk_month_diagnostic
    out = compute_lk_month_diagnostic({}, _chart(), datetime(2026, 6, 1))
    assert set(out) >= {"available", "domains_amplified", "domains_caution",
                        "sleeping_planets", "day_lord_conditions", "votes"}
    assert isinstance(out["votes"], list)
    # at most 7 distinct day-lord conditions (one per weekday lord)
    assert len(out["day_lord_conditions"]) <= 7
    # votes are jargon-free tags consumed only internally as an evidence trail
    for v in out["votes"]:
        assert v.startswith(("lk_amplify:", "lk_caution:", "lk_sleeping:"))


def test_month_lk_handles_empty_chart_gracefully():
    from antar_engine.lal_kitab_advanced import compute_lk_month_diagnostic
    out = compute_lk_month_diagnostic({}, {}, datetime(2026, 6, 1))
    assert out["available"] in (False, True)   # never raises
    assert isinstance(out["sleeping_planets"], list)


def test_masa_lord_and_theme_present():
    import sys, types
    if "swisseph" not in sys.modules:
        m = types.ModuleType("swisseph")
        for n in ("SUN", "MOON"):
            setattr(m, n, 0)
        m.set_ephe_path = lambda *a, **k: None
        m.set_sid_mode = lambda *a, **k: None
        sys.modules["swisseph"] = m
    from antar_engine import daily_panchanga as dp
    # every sign-lord maps to a plain theme; no Sanskrit in the themes
    for lord, theme in dp.MASA_LORD_THEME.items():
        assert theme and lord not in theme
    assert len(dp.MASA_BY_SUN_SIGN) == 12


def test_today_panchanga_texture_jargon_free():
    from antar_engine.today_narration import build_narration_system, _JARGON_RX
    s = build_narration_system(
        engine={"highlight_domains": ["money"], "direction": "positive",
                "strength": "high", "todays_move": {}},
        nudge=None, date_str="2026-06-07", drivers=[],
        panchanga={"karana_quality": "inauspicious — avoid important work",
                   "masa": "Ashadha", "masa_lord": "Mercury",
                   "masa_theme": "communication, deals, and learning"},
    )
    assert '"second_half_quality": "caution"' in s
    assert "communication, deals, and learning" in s
    # the Sanskrit masa name + planet must NOT be in the payload
    assert "Ashadha" not in s
    assert '"masa_lord"' not in s
