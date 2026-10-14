from datetime import date
from antar_engine import reading_library as rl, book_rules


def test_line_split_by_jaimini_entities():
    assert rl.line_of({"requires": [{"planet": "AK", "in_houses": [1]}]}) == "jaimini"
    assert rl.line_of({"requires": [{"planet": "Jupiter", "in_houses": [1]}]}) == "vimshottari"


def test_build_windows_dedupe_and_hide_actionless(monkeypatch):
    from tests.test_rule_registry import ctx
    c = ctx()
    rules = [{"id": "G1", "requires": [{"planet": "AK", "in_houses": [1]}], "activation": [], "tone": "good",
              "topics": ["money"], "effect": "a", "book": "kn_rao_x"},
             {"id": "G2", "requires": [{"planet": "AK", "in_houses": [1]}, {"house": 7, "empty": True}], "activation": [],
              "tone": "good", "topics": ["money"], "effect": "b", "book": "kn_rao_x"},
             {"id": "B1", "requires": [], "activation": [], "tone": "bad", "topics": ["other"], "effect": "c", "book": "kn_rao_x"}]
    ev = []
    for r in rules:
        from antar_engine.rule_registry import _book_evidence
        ev.append(_book_evidence(r))
    monkeypatch.setattr(rl.rr, "timed_book_evidence", lambda ctx_, d: ev)
    monkeypatch.setattr(book_rules, "load_rules", lambda: rules)
    out = rl.build(c, 2, "en", date(2026, 1, 1))
    ids = [i["rule_id"] for i in out["jaimini"]["lean_in"]]
    assert ids == ["BK.G2"] and out["jaimini"]["lean_in"][0]["more"] == 1
    assert out["vimshottari"]["watch"] == [] and out["jaimini"]["watch"] == []     # 'other' caution has no step: hidden
    w = out["jaimini"]["lean_in"][0]
    assert w["start"] == "2026-01-01" and w["end"] >= "2026-03-01"
