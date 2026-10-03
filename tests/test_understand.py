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
