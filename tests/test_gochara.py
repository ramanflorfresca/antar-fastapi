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
    assert set(out) == {"start", "days", "vimshottari", "jaimini", "lal_kitab"}
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
