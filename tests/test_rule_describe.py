import json
from antar_engine.rule_describe import describe


def test_describe_common_shapes():
    assert describe([]) == "(always, for any chart)"
    d = describe([{"planet": "L1", "in_houses": [1, 4]}, {"planet": "AK", "dignity": ["own"]}])
    assert "lord of house 1" in d and "1st / 4th" in d and "Atmakaraka" in d and " AND " in d
    assert "never applies" in describe([{"unparsed": "x"}])
    assert "Saturn transits Scorpio 26-30" in describe([{"transit_deg": {"planet": "Saturn", "sign": "Scorpio", "from_deg": 26, "to_deg": 30}}])
    assert "[KP chart]" in describe([{"frame": "kp", "cusp": 7, "sub_lord_signifies": [2, 7], "mode": "any"}])


def test_every_shipped_clause_has_a_readable_description():
    from antar_engine import book_rules
    for r in book_rules.load_rules()[:600]:
        for c in r.get("requires", []) + r.get("activation", []):
            from antar_engine.rule_describe import clause
            assert not clause(c).startswith("{"), c


def test_overrides_apply_in_build(tmp_path, monkeypatch):
    import importlib, scripts.build_book_rules as b
    rule = {"id": "T.1", "book": "x", "requires": [{"house": 7, "empty": True}], "activation": [], "tone": "good", "topics": ["money"],
            "effect": "Old line.", "effect_es": None, "remedy": None, "remedy_es": None, "timing_note": None, "clarity": "clear", "line": 1}
    (tmp_path / "RULES_book_x_2026-10-13.json").write_text(json.dumps({"rules": [{**{k: v for k, v in rule.items() if k not in ("effect", "remedy", "remedy_es")},
                                                                                 "effect_en": "Old line.", "drop": False}]}))
    ov_file = b.os.path.join(b.os.path.dirname(b.os.path.dirname(b.os.path.abspath(b.__file__))), "antar_engine", "data", "rule_overrides.json")
    orig = open(ov_file).read()
    try:
        open(ov_file, "w").write(json.dumps({"overrides": {"T.1": {"effect": "New line.", "tone": "bad"}}}))
        out, st = b.build(str(tmp_path))
        assert out["main"][0]["effect"] == "New line." and out["main"][0]["tone"] == "bad" and st["overrides_edited"] == 1
        open(ov_file, "w").write(json.dumps({"overrides": {"T.1": {"drop": True}}}))
        out, st = b.build(str(tmp_path))
        assert out["main"] == [] and st["overrides_dropped"] == 1
    finally:
        open(ov_file, "w").write(orig)
