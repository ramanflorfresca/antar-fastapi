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


def _ev(rule):
    from antar_engine.rule_registry import _book_evidence
    return _book_evidence(rule)


def test_opposite_tones_under_same_timing_are_dropped_unless_one_is_clearly_more_specific(monkeypatch):
    from tests.test_rule_registry import ctx
    act = [{"dasha": {"level": "md", "lords": ["Mars"]}}]
    rules = [{"id": "A", "requires": [], "activation": act, "tone": "good", "topics": ["money"], "effect": "a", "book": "x"},
             {"id": "B", "requires": [], "activation": act, "tone": "bad", "topics": ["money"], "effect": "b", "book": "x"},
             {"id": "C", "requires": [{"planet": "AK", "in_houses": [1]}], "activation": act, "tone": "good",
              "topics": ["career"], "effect": "c", "book": "x"},
             {"id": "D", "requires": [], "activation": act, "tone": "bad", "topics": ["career"], "effect": "d", "book": "x"}]
    ev = [_ev(r) for r in rules]
    monkeypatch.setattr(rl.rr, "timed_book_evidence", lambda c, d: ev)
    monkeypatch.setattr(book_rules, "load_rules", lambda: rules)
    out = rl.build(ctx(), 2, "en", date(2026, 1, 1))
    ids = [i["rule_id"] for line in ("vimshottari", "jaimini") for blk in out[line].values() for i in blk]
    assert "BK.A" not in ids and "BK.B" not in ids          # tie: dropped
    assert "BK.C" in ids and "BK.D" not in ids               # clearly more specific good wins


def test_agreement_needs_two_independent_signals(monkeypatch):
    from tests.test_rule_registry import ctx
    d = [{"dasha": {"level": "md", "lords": ["Mars"]}}]
    t = [{"transit": {"planet": "Jupiter", "from": "Moon", "houses": [5]}}]
    rules = [{"id": "A", "requires": [], "activation": d, "tone": "good", "topics": ["money"], "effect": "a", "book": "x"},
             {"id": "B", "requires": [{"house": 3, "empty": True}], "activation": d, "tone": "good", "topics": ["money"], "effect": "b", "book": "x"},
             {"id": "T", "requires": [], "activation": t, "tone": "good", "topics": ["career"], "effect": "t", "book": "x"}]
    ev = [_ev(r) for r in rules]
    monkeypatch.setattr(rl.rr, "timed_book_evidence", lambda c, dd: ev)
    monkeypatch.setattr(book_rules, "load_rules", lambda: rules)
    out = rl.build(ctx(), 2, "en", date(2026, 1, 1))
    assert out["agree"] == []                                # two rules, one signal (dasha); one rule on another topic
    rules.append({"id": "T2", "requires": [], "activation": t, "tone": "good", "topics": ["money"], "effect": "t2", "book": "x"})
    ev.append(_ev(rules[-1]))
    out = rl.build(ctx(), 2, "en", date(2026, 1, 1))
    assert [a["subject"] for a in out["agree"]] == ["money"] and out["agree"][0]["signals"] == ["dasha", "transit"]
