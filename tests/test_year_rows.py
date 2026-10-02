"""This Year rows (2026-10-02 walkthrough): rows had no `key` (FE printed the
index 0-4 as the area name), repeated the hook three times, said "the month's
shape" on a yearly row, and "Relationships stays"."""
from antar_engine.layered_phrasing import ALT_MONTH, ALT_YEAR, build_fallback_domains


def _rows(altitude, specs):
    ins = [{"domain": d, "polarity": p, "conviction": c, "altitude": altitude, "seed": s,
            "late_year": True, "window": None, "sourced": []} for d, p, c, s in specs]
    return build_fallback_domains(ins, "en")


def test_rows_carry_a_key():
    for r in _rows(ALT_YEAR, [("money", "steady", 0, ""), ("career", "positive", 3, "Strong.")]):
        assert r["key"] == r["domain"]


def test_no_repeated_beats_on_a_quiet_year_row():
    (r,) = _rows(ALT_YEAR, [("money", "steady", 0, "")])
    assert r["substance"] == ""
    assert r["hook"] not in r["depth"]


def test_year_rows_never_say_month_and_grammar():
    rows = _rows(ALT_YEAR, [("relationships", "steady", 0, ""), ("family", "caution", 0, "Under pressure.")])
    assert rows[0]["hook"].startswith("Relationships stay steady")
    assert all("month" not in (r["depth"] + r["substance"]).lower() for r in rows)


def test_month_rows_keep_month_tail():
    (r,) = _rows(ALT_MONTH, [("money", "positive", 2, "Good for a raise.")])
    assert "month's shape" in r["depth"]
