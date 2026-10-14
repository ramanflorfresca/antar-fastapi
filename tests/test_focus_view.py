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


def test_season_gets_a_plain_sentence_when_no_timed_statement_exists(monkeypatch):
    from tests.test_rule_registry import ctx
    monkeypatch.setattr(fv.rr, "applicable", lambda c: [])
    monkeypatch.setattr(fv.rr, "remedy_calendar", lambda c, l, s=None: {})
    monkeypatch.setattr(fv.rr, "_windows", lambda c, s, l: [{"start": "2026-10-14", "end": "2027-04-14", "both_systems": True}] if s == "money" else [])
    monkeypatch.setattr(when_engine, "_lk_year", lambda c, s: (__import__("datetime").date(2026, 10, 14), __import__("datetime").date(2026, 11, 26)))
    lib = {"horizon": ["a", "b"], "vimshottari": {"lean_in": [], "watch": []}, "jaimini": {"lean_in": [], "watch": []}}
    out = fv.build(ctx(), lib, None, ["money"], "en")
    t = out["focus"][0]["season"]["text"]
    assert t.startswith("Strong support through Apr 2027.") and "Strongest from Oct 2026 to Nov 2026." in t
    es = fv.build(ctx(), lib, None, ["money"], "es")["focus"][0]["season"]["text"]
    assert es.startswith("Mucho apoyo hasta abr 2027.")


def test_folded_areas_get_a_hint_only_when_it_is_a_dated_season_line_not_seen_elsewhere():
    focus = [{"season": {"text": "Strong support through Apr 2027."}, "pattern": {"text": "Profits grow."}}]
    assert fv._also_hint({"area": "health", "season": {"text": "x"}}, focus) is None            # body-care line covers health
    assert fv._also_hint({"area": "partnership", "season": None, "pattern": {"text": "Flattering trait."}}, focus) is None
    assert fv._also_hint({"area": "partnership", "season": {"text": "Strong support through Apr 2027."}}, focus) is None   # already shown
    assert fv._also_hint({"area": "partnership", "season": {"text": "Oct 2026 to Jun 2027 favours partnership."}}, focus) == "Oct 2026 to Jun 2027 favours partnership."


def test_every_card_and_folded_row_carries_a_window_status(monkeypatch):
    out = _run(monkeypatch, recent=["money"])
    c = out["focus"][0]
    assert c["window"]["kind"] == "window" and c["window"]["start"] and c["window"]["end"]
    assert out["labels"]["window"] == "Window" and out["labels"]["take_care"] == "Take care"
    assert all("window" in a for a in out["also"])
    assert fv._window(None, {"text": "x"}) == {"kind": "care", "start": None, "end": None}
    assert fv._window({"start": "2026-10-14", "end": "2027-01-01", "strength": "possible"}, {"text": "x"})["kind"] == "care"
    assert fv._window(None, None) is None


def test_window_prefers_the_strongest_stretch_and_keeps_the_end_of_support():
    w = fv._window({"start": "2026-10-14", "end": "2027-04-14", "strength": "strong",
                    "peaks": [{"start": "2026-10-14", "end": "2026-11-26"}]}, None)
    assert w == {"kind": "window", "start": "2026-10-14", "end": "2026-11-26", "through": "2027-04-14"}
    w2 = fv._window({"start": "2026-10-14", "end": "2027-04-14", "strength": "good", "peaks": []}, None)
    assert w2["start"] == "2026-10-14" and w2["end"] == "2027-04-14" and w2["through"] == "2027-04-14"


def test_no_present_tense_spouse_or_children_claims_unless_known():
    assert fv._gate_ok("Your spouse comes from a high-standing family.", {"partnered": False}) is False
    assert fv._gate_ok("Your spouse comes from a high-standing family.", {"partnered": None}) is False
    assert fv._gate_ok("Your spouse comes from a high-standing family.", {"partnered": True}) is True
    assert fv._gate_ok("You are attached to your children.", {"has_children": False}) is False
    assert fv._gate_ok("You are attached to your children.", {"has_children": True}) is True
    assert fv._gate_ok("Partnership takes shape.", {}) is True and fv._gate_ok(None, {}) is True


def test_focus_pattern_skips_spouse_lines_for_someone_who_is_not_partnered(monkeypatch):
    from tests.test_rule_registry import ctx
    ev = [rr_ev("Your spouse comes from a high-standing family.", "A"), rr_ev("You value steady partnership.", "B")]
    monkeypatch.setattr(fv.rr, "applicable", lambda c: ev)
    monkeypatch.setattr(fv.rr, "for_subject", lambda evs, s: evs)
    p = fv._pattern(ctx(), ("love",), "en", {"partnered": False, "marital": "divorced"})
    assert p["text"] == "You value steady partnership."
    assert fv._pattern(ctx(), ("love",), "en", {"partnered": True})["text"] in ("Your spouse comes from a high-standing family.", "You value steady partnership.")


def rr_ev(text, rid):
    return fv.rr.Evidence(rid, "x", ["love"], "good", "specific", {"en": text}, {"en": ""})


def test_pattern_never_uses_a_year_level_statement(monkeypatch):
    from tests.test_rule_registry import ctx
    ev = [rr_ev("This is a favourable year for a wedding.", "A"), rr_ev("You value steady partnership.", "B")]
    monkeypatch.setattr(fv.rr, "applicable", lambda c: ev)
    monkeypatch.setattr(fv.rr, "for_subject", lambda evs, s: evs)
    assert fv._pattern(ctx(), ("love",), "en", {"partnered": False})["text"] == "You value steady partnership."


def _lib2():
    mk = lambda subj, text, rid, start="2026-10-14", end="2027-01-01": {"rule_id": rid, "text": text, "subject": subj, "start": start, "end": end, "tendency": False}
    return {"horizon": ["a", "b"], "agree": [],
            "vimshottari": {"lean_in": [mk("money", "Income opens up.", "BK.A"), mk("marriage", "Partnership takes shape.", "BK.B"),
                                        mk("career", "Clients come in.", "BK.D")],
                            "watch": [{**mk("money", "Big commitments can backfire.", "BK.C", "2027-02-01", "2027-03-01"), "do": "Check the numbers twice."},
                                      {**mk("marriage", "Rush into promises.", "BK.E"), "do": "Slow down."}]},
            "jaimini": {"lean_in": [], "watch": []}}


def _run2(monkeypatch, life, area=None):
    from tests.test_rule_registry import ctx
    monkeypatch.setattr(fv.rr, "applicable", lambda c: [])
    monkeypatch.setattr(fv.rr, "remedy_calendar", lambda c, l, s=None: {"six_months": [
        {"steps": ["Bury barley under heavy weights."], "duration": "43 days", "problem": "p", "rule_id": "RM.1"}]} if s == "money" else {})
    monkeypatch.setattr(fv.rr, "_windows", lambda c, s, l: [{"action": "Line up your asks.", "start": "2026-10-14", "end": "2027-02-01", "both_systems": True}]
                        if s in ("money", "career") else [])
    monkeypatch.setattr(when_engine, "_lk_year", lambda c, s: None)
    return fv.build(ctx(), _lib2(), life, ["money", "business"], "en", None, None, 6, area)


def test_a_founder_gets_one_business_and_money_card_others_keep_money_and_work_apart(monkeypatch):
    out = _run2(monkeypatch, {"employed": False})
    keys = [c["area"] for c in out["focus"]] + [a["area"] for a in out["also"]]
    assert "business" in keys and "money" not in keys and "work" not in keys
    emp = _run2(monkeypatch, {"employed": True})
    keys2 = [c["area"] for c in emp["focus"]] + [a["area"] for a in emp["also"]]
    assert "money" in keys2 and "work" in keys2 and "business" not in keys2


def test_detail_has_only_this_topics_statements_and_everything_in_one_place(monkeypatch):
    out = _run2(monkeypatch, {"employed": False}, area="money")          # circle says Money; a founder's card is business
    d = out["detail"]
    assert d["area"] == "business" and d["goal"].startswith("Grow the business")
    texts = [b["text"] for b in d["bring"]] + [a["text"] for a in d["avoid"]]
    assert "Income opens up." in texts and "Clients come in." in texts and "Partnership takes shape." not in texts and "Rush into promises." not in texts
    assert d["do"] == ["Line up your asks."] and d["avoid"][0]["instead"] == "Check the numbers twice."
    assert d["remedies"][0]["text"].startswith("Bury barley") and d["mantra"]["text"] == "Om Budhaya Namaha"
    assert d["windows"]["avoid"] == [{"start": "2027-02-01", "end": "2027-03-01"}] and d["windows"]["best"]["start"] == "2026-10-14"
    assert out["labels"]["focus_title"].startswith("for the next 3 to 6 months") and out["labels"]["do"] == "Do"
