from datetime import date
from antar_engine import gochara as g


def test_house_from_moon():
    assert g.house_from(5, 5) == 1 and g.house_from(5, 4) == 12 and g.house_from(0, 11) == 12


def test_vedha_blocks_favourable(monkeypatch):
    # Jupiter in 11th from Moon is favourable; another planet in the 8th from Moon obstructs it
    signs = {"Sun": 3, "Moon": 0, "Mercury": 3, "Venus": 3, "Mars": 3, "Jupiter": 10, "Saturn": 3, "Rahu": 3, "Ketu": 9}
    monkeypatch.setattr(g, "transit_signs", lambda d: signs)
    signs2 = dict(signs, Venus=7)  # 8th house from Moon in sign 0 is sign 7
    st = g.state_on(0, date(2026, 1, 1))
    assert st["Jupiter"]["house"] == 11 and st["Jupiter"]["state"] == "good"
    monkeypatch.setattr(g, "transit_signs", lambda d: signs2)
    assert g.state_on(0, date(2026, 1, 1))["Jupiter"]["state"] == "blocked"


def test_nodes_always_unfavourable_and_exempt_pairs(monkeypatch):
    signs = {"Sun": 2, "Moon": 0, "Mercury": 0, "Venus": 5, "Mars": 5, "Jupiter": 1, "Saturn": 8, "Rahu": 1, "Ketu": 7}
    monkeypatch.setattr(g, "transit_signs", lambda d: signs)
    st = g.state_on(0, date(2026, 1, 1))
    assert st["Rahu"]["state"] == "bad" and st["Ketu"]["state"] == "bad"
    # Moon in 1st (vedha 5) is not obstructed by Mercury... nothing in 5th; Moon stays good
    assert st["Moon"]["state"] == "good"


def test_outlook_shape_and_languages():
    o = g.outlook(5, date(2026, 10, 13), 7, "es")
    assert [l["planet_key"] for l in o["background"]] == ["Jupiter", "Saturn"]
    assert len(o["moon_days"]) == 7
    assert all(not any(n in l["text"] for n in ("Jupiter", "Saturn", "Mars")) for l in o["background"] + o["this_month"])


def test_weekly_layer_three_labelled_lines():
    from tests.test_rule_registry import ctx
    from antar_engine import weekly_layer
    c = ctx()
    out = weekly_layer.week(c, "en", 7)
    assert set(out) == {"start", "days", "vimshottari", "jaimini", "lal_kitab", "lean_in", "watch", "watch_more", "wellness"}
    assert out["vimshottari"]["gochara"]["background"]
    assert isinstance(out["jaimini"], list) and "year_lord" in out["lal_kitab"]


def test_week_shows_one_rule_per_topic_and_tone(monkeypatch):
    from antar_engine import weekly_layer, book_rules
    monkeypatch.setattr(book_rules, "load_rules", lambda: [
        {"id": "A", "requires": [1], "activation": []}, {"id": "B", "requires": [1, 2], "activation": [1]}])
    rows = [{"rule_id": "A", "book": "x", "tone": "good", "subjects": ["love"], "text": "a", "days": []},
            {"rule_id": "B", "book": "x", "tone": "good", "subjects": ["love"], "text": "b", "days": []}]
    out = weekly_layer._one_per_topic(rows)
    assert [r["rule_id"] for r in out] == ["B"] and out[0]["more"][0]["rule_id"] == "A"


def test_character_labels_and_vague_spans_removed():
    import json, re
    from scripts.build_rc_rules import LABEL_RE
    for f in ("book_rules", "lk_roop_chand_rules"):
        for r in json.load(open(f"antar_engine/data/{f}.json"))["rules"]:
            assert not LABEL_RE.search(r.get("effect") or ""), r["id"]
    assert not any(re.search("pin down", r["effect"]) for r in json.load(open("antar_engine/data/book_rules.json"))["rules"])


def test_watch_block_has_action_or_is_hidden():
    from antar_engine import weekly_layer as wl
    out = {"jaimini": [
        {"rule_id": "BK.X", "book": "K.N. Rao", "tone": "bad", "subjects": ["money"], "text": "t", "days": ["d"]},
        {"rule_id": "BK.Y", "book": "K.N. Rao", "tone": "bad", "subjects": ["other"], "text": "u", "days": ["d"]},
        {"rule_id": "BK.Z", "book": "K.N. Rao", "tone": "good", "subjects": ["money"], "text": "g", "days": ["d"]}],
        "lal_kitab": {"rules": []}, "vimshottari": {"gochara": None}}
    b = wl._blocks(out, "en")
    assert [w["rule_id"] for w in b["watch"]] == ["BK.X"] and b["watch"][0]["do"]
    assert [l["rule_id"] for l in b["lean_in"]] == ["BK.Z"]


def test_every_topic_step_is_plain_and_bilingual():
    from antar_engine import weekly_layer as wl
    from scripts.build_rc_rules import PLANET_RE, JARGON_RE, LABEL_RE
    for en, es in wl.STEPS.values():
        assert en and es and not (PLANET_RE.search(en) or JARGON_RE.search(en) or LABEL_RE.search(en))


def test_wellness_never_repeats_the_same_habit_on_two_shown_themes(monkeypatch):
    from tests.test_rule_registry import ctx
    from antar_engine import reading_library as rl, book_rules
    habit = "Favour fruit and buttermilk."
    rules = [{"id": f"H{i}", "requires": [], "activation": [{"dasha": {"level": "md", "lords": ["Moon", "Mars", "Sun", "Venus", "Saturn", "Mercury", "Jupiter", "Rahu", "Ketu"]}}],
              "tone": "info", "topics": ["health"], "effect": f"Area {i} may need care.", "remedy": (habit if i < 3 else "Use neem."), "book": "chatterjee_medical"}
             for i in range(4)]
    ev = [rl.rr._book_evidence(r) for r in rules]
    monkeypatch.setattr(rl.rr, "timed_book_evidence", lambda c, d: ev)
    monkeypatch.setattr(rl.rr, "_book_family", lambda c: [])
    monkeypatch.setattr(book_rules, "load_rules", lambda: rules)
    w = rl.wellness(ctx(), language="en")
    remedies = [t["remedy"] for t in w["themes"] if t["remedy"]]
    assert len(remedies) == len(set(remedies)) and "Use neem." in remedies and len(w["themes"]) == 3
