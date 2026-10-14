from antar_engine import rc_rules as rc

NATAL = {"Sun": 5, "Moon": 12, "Mars": 7, "Mercury": 7, "Jupiter": 11, "Venus": 8, "Saturn": 3, "Rahu": 8, "Ketu": 2}
ANNUAL = {"Sun": 5, "Moon": 4, "Mars": 1, "Mercury": 11, "Jupiter": 11, "Venus": 8, "Saturn": 2, "Rahu": 2, "Ketu": 1}
ST = {"natal": NATAL, "annual": ANNUAL, "gender": "male"}


def test_clauses():
    h = rc.holds
    assert h({"planet": "Mars", "in": [1, 7]}, ST) and not h({"planet": "Mars", "in": [1, 8]}, ST)
    assert h({"planet": "Mars", "not_in": [2, 10]}, ST)
    assert h({"planet": "Mars", "with": "Mercury"}, ST) and not h({"planet": "Mars", "with": "Venus"}, ST)
    assert h({"house": 4, "empty": True}, ST) and h({"house": 7, "empty": False}, ST)
    assert h({"houses": [2, 5, 9, 12], "holds_any": ["Sun", "Jupiter"]}, ST)
    assert h({"houses": [2, 5], "holds_none_of": ["Saturn", "Rahu"]}, ST)                 # neither is in 2 or 5
    assert h({"houses": [2, 5], "holds_none_of": ["Sun"]}, ST) is False                   # Sun sits in 5
    assert h({"chart": "male"}, ST) and not h({"chart": "female"}, ST)
    assert not h({"unparsed": "well placed"}, ST)                                         # never applies
    assert h({"planet": "Mars", "in": [1], "chart": "annual"}, ST)                        # annual chart read
    assert not h({"planet": "Mars", "in": [1], "chart": "annual"}, {"natal": NATAL, "annual": None})


def test_natal_and_annual_rules_apply_only_when_conditions_hold():
    natal_rule = {"kind": "natal", "planet": "Mars", "houses": [7], "requires": [{"planet": "Mercury", "with": "Mars"}],
                  "tone": "good", "effect": "x", "topics": ["marriage"]}
    assert rc.rule_applies(natal_rule, ST)
    assert not rc.rule_applies({**natal_rule, "requires": [{"planet": "Venus", "with": "Mars"}]}, ST)
    assert not rc.rule_applies({**natal_rule, "houses": [8]}, ST)
    assert not rc.rule_applies({**natal_rule, "sensitive": True}, ST)
    assert not rc.rule_applies({**natal_rule, "requires": [{"unparsed": "afflicted"}]}, ST)
    ann = {"kind": "annual", "planet": "Mars", "annual_houses": [1], "requires": [], "tone": "good", "effect": "y"}
    assert rc.rule_applies(ann, ST) and not rc.rule_applies(ann, {"natal": NATAL, "annual": None})
    assert not rc.rule_applies({**ann, "annual_houses": [8]}, ST)
    house_rule = {"kind": "natal", "planet": None, "houses": None, "requires": [{"house": 4, "empty": True}], "effect": "z"}
    assert rc.rule_applies(house_rule, ST)                                                # chart-level rule


def test_subjects_and_merge(tmp_path):
    assert rc.subjects_of({"topics": ["career", "fame", "money"]}) == ["career", "job", "business", "money"]
    import json
    a = {"rules": [{"kind": "natal", "planet": "Sun", "houses": [1], "requires": [], "tone": "good", "effect": "ok"},
                   {"kind": "natal", "planet": "Sun", "houses": [1], "requires": [], "tone": "good", "effect": "ok"},
                   {"kind": "natal", "planet": "Sun", "houses": [2], "requires": [], "tone": "bad", "effect": "(omitted)", "sensitive": True},
                   {"kind": "natal", "planet": "Sun", "houses": [3], "requires": [], "tone": "bad", "effect": "fine", "sensitive": True}]}
    p = tmp_path / "a.json"
    p.write_text(json.dumps(a))
    assert len(rc.merge_files([str(p)])) == 1
