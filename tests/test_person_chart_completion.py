"""[person-chart 2026-10-11] a person added to the network gets a complete chart, so the two-chart reading starts from two full charts."""
import re

import main


def test_the_add_flow_uses_the_canonical_dasha_normaliser():
    """Regression: a local copy iterated {mahadashas, antardashas} (its two KEY strings) and returned [] — people added after the dasha
    modules changed format had NO dasha rows (saransh, Rishi)."""
    src = open(main.__file__, encoding="utf-8").read()
    body = src[src.index("            def _normalise_dashas_b(raw):"):src.index("            try:\n                _vim_b = _normalise_dashas_b(")]
    assert "return _normalise_dashas(raw)" in body and "for p in raw" not in body


def test_canonical_normaliser_flattens_the_dict_format_into_md_and_ad_rows():
    raw = {"mahadashas": [{"lord": "Saturn", "start_date": "2020-01-01", "end_date": "2039-01-01", "duration_years": 19}],
           "antardashas": [{"lord": "Rahu", "parent_lord": "Saturn", "start_date": "2026-01-01", "end_date": "2028-01-01", "duration_years": 2}]}
    rows = main._normalise_dashas(raw)
    assert [(r["lord_or_sign"], r["level"]) for r in rows] == [("Saturn", "mahadasha"), ("Rahu", "antardasha")]
    assert main._normalise_dashas({}) == [] and main._normalise_dashas(None) == []


class _Q:
    def __init__(self, rows):
        self.data = rows

    def __getattr__(self, name):
        return lambda *a, **k: self

    def execute(self):
        return self


class _SB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Q(self.tables.get(name, []))


def test_complete_person_chart_rebuilds_from_the_stored_chart(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "supabase", _SB({"charts": [{"id": "c1", "chart_data": {"planets": {"Sun": {"sign": "Leo"}}}, "birth_date": "1980-02-03T00:00:00"}]}))
    monkeypatch.setattr(main, "_rederive_after_birth_edit", lambda cid, cd, bd: calls.append((cid, cd, bd)) or {"dashas": "ok", "jaimini": "ok"})
    out = main._complete_person_chart_sync("c1")
    assert out == {"dashas": "ok", "jaimini": "ok"} and calls == [("c1", {"planets": {"Sun": {"sign": "Leo"}}}, "1980-02-03")]


def test_complete_person_chart_refuses_a_chart_with_nothing_to_rebuild_from(monkeypatch):
    monkeypatch.setattr(main, "supabase", _SB({"charts": []}))
    assert main._complete_person_chart_sync("x") == {"error": "chart not found"}
    monkeypatch.setattr(main, "supabase", _SB({"charts": [{"id": "c1", "chart_data": {}, "birth_date": ""}]}))
    assert "error" in main._complete_person_chart_sync("c1")


def test_gap_check_names_what_a_light_chart_is_missing(monkeypatch):
    monkeypatch.setattr(main, "supabase", _SB({"charts": [{"jaimini_data": None, "lal_kitab_data": None}], "dasha_periods": []}))
    assert main._person_chart_gaps("c1") == ["jaimini_data", "lal_kitab_data", "vimsottari", "jaimini", "ashtottari"]
    full = {"charts": [{"jaimini_data": {"karakas": []}, "lal_kitab_data": {"age": 40}}],
            "dasha_periods": [{"system": "vimsottari"}, {"system": "jaimini"}, {"system": "ashtottari"}]}
    monkeypatch.setattr(main, "supabase", _SB(full))
    assert main._person_chart_gaps("c1") == []
