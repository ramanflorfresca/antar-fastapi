import json
from antar_engine import focus_view as fv, when_engine


def _lib():
    mk = lambda subj, text, rid, start="2026-10-14": {"rule_id": rid, "text": text, "subject": subj, "start": start, "end": "2027-01-01", "tendency": False}
    return {"horizon": ["2026-10-14", "2028-10-12"], "agree": [],
            "vimshottari": {"lean_in": [mk("money", "Income opens up.", "BK.A"), mk("marriage", "Partnership takes shape.", "BK.B")],
                            "watch": [{**mk("money", "Big commitments can backfire.", "BK.C"), "do": "Check the numbers twice."}]},
            "jaimini": {"lean_in": [mk("career", "Clients come in.", "BK.D")], "watch": []}}


def _run(monkeypatch, life=None, recent=None, pinned=None):
    from tests.test_rule_registry import ctx
    monkeypatch.setattr(fv.rr, "applicable", lambda c: [])
    monkeypatch.setattr(fv.rr, "_windows", lambda c, s, l: [{"action": "Line up your asks.", "start": "2026-10-14", "end": "2027-02-01",
                                                               "both_systems": True}] if s == "money" else [])
    monkeypatch.setattr(when_engine, "_lk_year", lambda c, s: None)
    return fv.build(ctx(), _lib(), life, recent, "en", pinned)


def test_recent_questions_lead(monkeypatch):
    out = _run(monkeypatch, life={"partnered": False, "marital": "single"}, recent=["funding", "funding", "business client"])
    assert [c["area"] for c in out["focus"]][:1] == ["money"]
    assert out["labels"]["pattern"] == "Your pattern" and out["labels"]["season"] == "Your season"


def test_married_person_is_not_led_into_marriage_timing(monkeypatch):
    out = _run(monkeypatch, life={"partnered": True, "marital": "married", "employed": False}, recent=None)
    focus = [c["area"] for c in out["focus"]]
    assert "partnership" not in focus and any(a["area"] == "partnership" for a in out["also"])


def test_one_card_merges_season_move_watch_and_has_no_method_names(monkeypatch):
    out = _run(monkeypatch, recent=["money"])
    c = out["focus"][0]
    assert c["season"]["text"] == "Income opens up." and c["move"] == "Line up your asks." and c["watch"]["do"] == "Check the numbers twice."
    b = json.dumps(out)
    for w in ("Jaimini", "Vimshottari", "KP", "Lal Kitab", "Rao", "rule_id", "BK."):
        assert w not in b


def test_pinned_focus_wins_and_at_most_two(monkeypatch):
    out = _run(monkeypatch, recent=["money"], pinned=["partnership"])
    assert out["focus"][0]["area"] == "partnership" and len(out["focus"]) <= 2


def test_card_carries_a_support_remedy_and_top_level_care_line(monkeypatch):
    from tests.test_rule_registry import ctx
    monkeypatch.setattr(fv.rr, "remedy_calendar", lambda c, l, s=None: {"this_month": [], "six_months": [
        {"steps": ["Offer water to the sun at dawn for 43 days."], "duration": "43 days", "purpose": "To ease it", "rule_id": "RM.A.1"}]})
    lib = _lib()
    lib["wellness"] = {"themes": [{"rule_id": "BK.CHM.5", "text": "Your digestion may need care.", "remedy": "Eat lighter now and then."}]}
    monkeypatch.setattr(fv.rr, "applicable", lambda c: [])
    monkeypatch.setattr(fv.rr, "_windows", lambda c, s, l: [])
    monkeypatch.setattr(when_engine, "_lk_year", lambda c, s: None)
    out = fv.build(ctx(), lib, None, ["money"], "en")
    c = out["focus"][0]
    assert c["support"]["text"].startswith("Offer water") and c["support"]["ref"]
    assert out["care"]["text"] == "Eat lighter now and then." and out["horizon_months"] == 6
    assert out["labels"]["support"] == "Do this to support it"


def test_area_param_returns_that_areas_full_card_even_when_not_in_focus(monkeypatch):
    out = _run(monkeypatch, recent=["money"])
    assert out["card"] is None                                      # no area asked for
    from tests.test_rule_registry import ctx
    monkeypatch.setattr(fv.rr, "applicable", lambda c: [])
    monkeypatch.setattr(fv.rr, "_windows", lambda c, s, l: [])
    monkeypatch.setattr(fv.rr, "remedy_calendar", lambda c, l, s=None: {})
    monkeypatch.setattr(when_engine, "_lk_year", lambda c, s: None)
    out = fv.build(ctx(), _lib(), None, ["money"], "en", None, None, 6, "partnership")
    assert out["card"]["area"] == "partnership" and out["card"]["season"]["text"] == "Partnership takes shape."
    assert fv.build(ctx(), _lib(), None, ["money"], "en", None, None, 6, "inner")["card"] is None
