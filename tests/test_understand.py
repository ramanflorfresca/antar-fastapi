"""Understanding layer (antar_engine/understand.py): strict parsing, menus, safety OR."""
import json
from antar_engine import understand as u


def _raw(**kw):
    base = {"language": "en", "standalone": "Will my partnership break?", "intent": "yes_no",
            "area": "partnership_ending", "subject": "business_partner", "polarity": "feared",
            "horizon_days": None, "yes_no_fit": True, "crisis": False, "gambling": False,
            "needs_clarification": False, "clarify": "", "confidence": 0.93}
    base.update(kw)
    return "here you go " + json.dumps(base)


def test_parse_valid_and_maps_to_kp_and_concern():
    r = u.parse(_raw(), "Will my partnership break")
    assert r["area"] == "partnership_ending" and r["polarity"] == "feared"
    assert u.kp_type(r) == "loss" and u.concern(r) == "business"


def test_unknown_area_rejected_and_bad_enums_defaulted():
    assert u.parse(_raw(area="astrology_stuff")) is None
    r = u.parse(_raw(intent="banana", language="klingon", subject="cat", horizon_days="soon"))
    assert r["intent"] == "open" and r["language"] == "other" and r["subject"] == "self"
    assert r["horizon_days"] is None


def test_garbage_is_none():
    assert u.parse("no json here") is None and u.parse("") is None


def test_every_area_says_how_kp_and_ask_read_it():
    from antar_engine.kp.kp_significators import QUESTION_TYPES
    for area, (qt, concern) in u.AREAS.items():
        assert concern, area
        assert qt is None or qt == "loss" or qt in QUESTION_TYPES, (area, qt)


def test_safety_is_an_or_never_weaker():
    assert u.safety({"crisis": False, "gambling": False}, True, False) == {"crisis": True, "gambling": False}
    assert u.safety({"crisis": True, "gambling": True}, False, False) == {"crisis": True, "gambling": True}
    assert u.safety(None, False, True)["gambling"] is True


def test_compare_flags_disagreements():
    r = u.parse(_raw())
    d = u.compare(r, {"language": "hinglish", "kp_type": None, "concern": "business",
                      "yes_no": True, "gambling": False, "crisis": False})
    assert not d["language"]["agree"] and not d["kp_type"]["agree"] and d["concern"]["agree"]


def test_request_carries_thread_and_saved_language():
    txt = u.request("and tomorrow?", [{"question": "How is speculation today?", "answer": "Cautious."}], "es")
    assert "Earlier question: How is speculation today?" in txt and "es" in txt
    assert txt.strip().endswith("Message: and tomorrow?")


def test_memo_and_worth_reading():
    k = u.memo_key("Will I pass?", [], "")
    u.memo_put(k, {"area": "education_exam"})
    assert u.memo_get(k) == {"area": "education_exam"}
    assert not u.worth_reading("13") and not u.worth_reading("ok") and u.worth_reading("Will I pass?")


def test_golden_set_is_valid():
    import os
    p = os.path.join(os.path.dirname(__file__), "fixtures", "nlu_golden.jsonl")
    for line in open(p):
        r = json.loads(line)
        for a in (r.get("area") or []):
            assert a in u.AREAS, a
        assert r.get("language") in (None,) + u.LANGS


def test_shadow_never_touches_the_answer(monkeypatch):
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    import main
    async def fake_call(**kw):
        return (_raw(), None)
    monkeypatch.setattr(main, "call_llm_claude", fake_call)
    monkeypatch.setattr(main, "_ask_recent_thread", lambda *a, **k: [])
    logged = []
    class T:
        def insert(self, row): logged.append(row); return self
        def execute(self): return None
    monkeypatch.setattr(main.supabase, "table", lambda name: T())
    asyncio.run(main._nlu_shadow("Will my partnership break", "c1", "en", "whatsapp", "explore"))
    assert logged and logged[0]["understanding"]["area"] == "partnership_ending"
    assert isinstance(logged[0]["disagree"], list) and logged[0]["channel"] == "whatsapp"


def test_feared_partnership_event_is_its_ending():
    r = u.parse(_raw(area="business_partnership", polarity="feared"))
    assert r["area"] == "partnership_ending" and u.kp_type(r) == "loss"
    r = u.parse(_raw(area="existing_relationship", polarity="feared"))
    assert r["area"] == "separation"
    r = u.parse(_raw(area="business_partnership", polarity="wanted"))
    assert r["area"] == "business_partnership"


# ── stated life facts (live 2026-10-03: unemployed reader told about a promotion) ──
def test_stated_facts_parsed_and_menu_checked():
    r = u.parse(_raw(stated_facts={"work": "unemployed", "relationship": "astronaut",
                                   "children": "maybe", "other": ["has debt", "", "x" * 200, "a", "b"]}))
    f = r["stated_facts"]
    assert f["work"] == "unemployed" and f["relationship"] is None and f["children"] is None
    assert f["other"][0] == "has debt" and len(f["other"]) == 3 and len(f["other"][1]) <= 80


def test_unemployed_block_forbids_promotion_and_boss():
    r = u.parse(_raw(stated_facts={"work": "unemployed", "other": ["unfocused for months"]}))
    b = u.stated_block(r)
    assert "UNEMPLOYED" in b and "promotion" in b and "boss" in b
    assert "They told you: unfocused for months." in b
    assert u.life_overrides(r) == {"employed": False}


def test_no_stated_facts_no_block():
    r = u.parse(_raw())
    assert u.stated_block(r) == "" and u.life_overrides(r) == {}


def test_relationship_and_children_overrides():
    r = u.parse(_raw(stated_facts={"relationship": "divorced", "children": "no"}))
    assert u.life_overrides(r) == {"partnered": False, "has_children": False}
    assert "DIVORCED" in u.stated_block(r) and "NO children" in u.stated_block(r)


def test_harvest_writes_only_empty_fields(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    import antar_engine.profile_harvest as ph
    wrote = []
    monkeypatch.setattr(ph, "apply_harvest", lambda sb, cid, facts: wrote.append(facts) or {"written": list(facts)})
    r = u.parse(_raw(stated_facts={"work": "unemployed", "relationship": "single"}))
    row = {"career_stage": "", "marital_status": "married"}
    main._ask_harvest_stated("c1", row, r)
    assert wrote == [{"career_stage": {"value": "seeking", "evidence": "stated (nlu)"}}]
    assert row["career_stage"] == "seeking" and row["marital_status"] == "married"



# ── warm opening ──
def test_struggling_feeling_adds_a_warm_opening_rule():
    r = u.parse(_raw(feeling="stuck"))
    b = u.tone_block(r)
    assert "they sound stuck" in b and "Never open with blame" in b


def test_neutral_or_unknown_feeling_adds_nothing():
    assert u.tone_block(u.parse(_raw(feeling="curious"))) == ""
    assert u.parse(_raw(feeling="ecstatic-ish"))["feeling"] == "neutral"
    assert u.tone_block(u.parse(_raw())) == ""


# ── comparisons, how they earn, wealth promises (live 2026-10-03, Andres) ──
def test_options_and_earning_parsed():
    r = u.parse(_raw(intent="which", options=["gold mine deals", "defence contracts", "real estate", ""],
                     stated_facts={"work": "self_employed", "earning": ["advisory", "commission", "equity", "magic"]}))
    assert r["options"] == ["gold mine deals", "defence contracts", "real estate"]
    assert r["stated_facts"]["earning"] == ["advisory", "commission", "equity"]
    assert u.is_comparison(r)


def test_comparison_block_forbids_a_winner_and_uses_how_they_earn():
    r = u.parse(_raw(intent="which", options=["gold", "defence"],
                     stated_facts={"earning": ["advisory", "commission", "equity"]}))
    b = u.comparison_block(r)
    assert "Do NOT name a winner" in b and "stronger bet" in b
    assert "advisory fees + commission + equity / sweat equity" in b
    assert "NEVER assume how a deal is structured" in b
    assert u.comparison_block(u.parse(_raw())) == ""


def test_stored_earning_roundtrip():
    stored = u.EARNS_PREFIX + u.earning_text(["advisory", "commission"])
    assert u.stored_earning(stored) == "advisory fees + commission"
    assert "advisory fees + commission" in u.earning_line(stored)
    assert u.earning_line("Engineer") == "" and u.stored_earning("") == ""


def test_wealth_promise_gets_the_honesty_rule():
    r = u.parse(_raw(outcome_claim=True))
    assert "can't honestly promise an amount" in u.outcome_block(r)
    assert u.outcome_block(u.parse(_raw())) == ""


def test_earning_saved_into_empty_profession_only(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    import antar_engine.profile_harvest as ph
    wrote = []
    monkeypatch.setattr(ph, "apply_harvest", lambda sb, cid, facts: wrote.append(facts) or {})
    r = u.parse(_raw(stated_facts={"earning": ["advisory", "commission", "equity"]}))
    main._ask_harvest_stated("c1", {"profession": None, "career_stage": "x"}, r)
    assert wrote[-1]["profession"]["value"] == "Earns via advisory fees + commission + equity / sweat equity"
    wrote.clear()
    main._ask_harvest_stated("c1", {"profession": "Lawyer", "career_stage": "x"}, r)
    assert not wrote
