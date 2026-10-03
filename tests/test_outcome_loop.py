"""Outcome loop, week 1 (2026-10-02): checkable claims are recorded with the
window the verdict names, and only an explicit answer is an outcome."""
from datetime import date

import pytest

from antar_engine import outcomes as oc

T = date(2026, 10, 2)


def test_parse_window_forms():
    assert oc.parse_window("Nov 2026 – Jan 2027", T) == (date(2026, 11, 1), date(2027, 1, 31))
    assert oc.parse_window("Oct 2026", T) == (date(2026, 10, 1), date(2026, 10, 31))
    assert oc.parse_window("24 Nov – 12 Dec", T) == (date(2026, 11, 24), date(2026, 12, 12))
    assert oc.parse_window("soon", T) == (None, None)


def test_claim_uses_the_window_the_verdict_names_not_the_chip():
    # live: chip "Oct 2026" (groundwork) vs the claim "Jun 2027 – Oct 2027"
    p = {"verdict": "NOT_YET", "timing": "Oct 2026",
         "read": "Not yet — right now (Oct 2026) is for laying groundwork; the strong funding "
                 "window is Jun 2027 – Oct 2027. The potential is real."}
    c = oc.build_claim("c1", "When is the best time to raise funding?", p, mode="explore",
                       topic="funding", language="en", today=T)
    assert (c["window_start"], c["window_end"]) == ("2027-06-01", "2027-10-31")
    assert c["checkin_due_at"].startswith("2027-11-03")
    assert c["dedupe_key"] == "c1|funding|window|2027-06-01|2027-10-31"


def test_advice_and_mood_are_not_claims():
    assert oc.build_claim("c1", "q", {"verdict": None, "read": "A day to protect what you have."},
                          mode="explore", topic="money", language="en", today=T) is None
    assert oc.build_claim("c1", "q", {"verdict": "LIKELY", "read": "Yes, soon."},
                          mode="explore", topic="money", language="en", today=T) is None


def test_yesno_claim():
    c = oc.build_claim("c1", "Will I get the offer?",
                       {"lean": "LEAN_YES", "verify_after": "2026-12-15", "timing": "24 Nov – 12 Dec",
                        "why": "The signs support it."},
                       mode="yesno", topic="career", language="en", today=T,
                       engines={"kp": {"lean": "LEAN_YES"}})
    assert c["claim_type"] == "yesno" and c["window_end"] == "2026-12-15"
    assert c["engines"]["kp"]["lean"] == "LEAN_YES"


def test_checkin_text_and_sensitive_topics():
    c = {"language": "en", "topic": "business", "claim_type": "window", "source": "ask_explore",
         "text_shown": "The strong business window is Nov 2026 – Jan 2027."}
    t = oc.checkin_text(c)
    assert "We said:" in t and "Did things move for your business in that time?" in t
    h = oc.checkin_text({"language": "en", "topic": "health", "claim_type": "window",
                         "text_shown": "Your health improves in March."})
    assert h == "Did it happen?"                      # no detail for sensitive topics
    assert "¿Se movió algo en tu negocio" in oc.checkin_text(dict(c, language="es"))


def test_outcome_values_are_validated():
    with pytest.raises(ValueError):
        oc.record_outcome(None, "x", "maybe")


@pytest.fixture()
def m():
    from dotenv import load_dotenv
    load_dotenv()
    import main
    return main


def test_due_endpoint_requires_ownership(m, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    monkeypatch.setattr(m, "_oc_owned_chart", lambda u, c: c == "mine")
    monkeypatch.setattr(oc, "due_claims", lambda sb, cid: [
        {"id": "k1", "language": "en", "topic": "business", "claim_type": "window",
         "text_shown": "The strong business window is Nov 2026 – Jan 2027.", "window_end": "2027-01-31"}])
    c = TestClient(m.app)
    assert c.get("/api/v1/outcomes/due/theirs", headers={"Authorization": "Bearer x"}).status_code == 403
    r = c.get("/api/v1/outcomes/due/mine", headers={"Authorization": "Bearer x"}).json()
    assert r["due"][0]["claim_id"] == "k1"
    assert [o["value"] for o in r["due"][0]["options"]] == ["yes", "partly", "no", "not_sure"]


def test_answer_endpoint_rejects_bad_outcome(m, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    r = TestClient(m.app).post("/api/v1/outcomes/k1", json={"outcome": "maybe"},
                               headers={"Authorization": "Bearer x"})
    assert r.status_code == 400


def test_life_arc_text_is_never_quoted():
    t = oc.checkin_text({"language": "en", "topic": "current_chapter", "claim_type": "window",
                         "source": "life_arc",
                         "text_shown": "You are in a clarifying pressure — Saturn is asking what is true."})
    assert "Saturn" not in t and t == "Did it happen?"
    assert "life_arc" not in oc.CHECKABLE_SOURCES



def test_replayed_answer_is_not_a_claim_and_yesno_keys_by_question():
    base = {"lean": "conditional", "verify_after": "2027-01-31", "timing": "Oct 3 – Jan 31",
            "why": "The door isn't open yet."}
    assert oc.build_claim("c1", "Will I?", dict(base, locked=True), mode="yesno",
                          topic="general", language="en", today=T) is None
    a = oc.build_claim("c1", "Will I raise funding by March?", base, mode="yesno",
                       topic="general", language="en", today=T)
    b = oc.build_claim("c1", "Will I get the job?", base, mode="yesno",
                       topic="general", language="en", today=T)
    assert a["dedupe_key"] != b["dedupe_key"]


# ─── week 2: sending check-ins ───

def _due(i, chart, due="2026-10-01", src="ask_explore", sent=None):
    return {"id": f"k{i}", "chart_id": chart, "source": src, "checkin_due_at": due,
            "checkin_sent_at": sent, "language": "en", "topic": "business",
            "claim_type": "window", "text_shown": "The strong business window is Nov 2026 – Jan 2027."}


def test_pick_due_one_per_chart_cap_and_sources():
    claims = [_due(1, "a", "2026-10-02"), _due(2, "a", "2026-10-01"), _due(3, "b"),
              _due(4, "c"), _due(5, "d", src="ask_yesno"), _due(6, "e", src="life_arc")]
    picked = oc.pick_due(claims, sent_last_week={"c": 2}, answered={"k3"})
    assert [p["id"] for p in picked] == ["k2"]          # oldest for a; b answered; c capped; yesno/life_arc not here


def test_push_and_whatsapp_checkin_text():
    title, body = oc.push_message(dict(_due(1, "a"), source="ask_explore"))
    assert title == "Did it happen?" and "Did things move for your business" in body
    text, opts = oc.whatsapp_checkin(dict(_due(1, "a"), source="ask_explore"))
    assert "1  Yes" in text and "4  Not sure yet" in text
    assert opts == [["k1", "yes"], ["k1", "partly"], ["k1", "no"], ["k1", "not_sure"]]


def test_whatsapp_digit_answers_the_checkin(monkeypatch):
    import asyncio
    import time
    from dotenv import load_dotenv
    load_dotenv()
    import main
    from antar_engine import messaging as msg
    link = {"id": 1, "chart_id": "c1", "user_id": "u1",
            "context": msg.remember_options({}, "outcome", [["k9", "yes"], ["k9", "partly"],
                                                          ["k9", "no"], ["k9", "not_sure"]])}
    sent, recorded = [], []
    monkeypatch.setattr(msg, "get_whatsapp_link", lambda sb, n: link)
    monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: sent.append(t) or True)
    monkeypatch.setattr(msg, "save_link_context", lambda sb, l, c: l.__setitem__("context", c) or True)
    monkeypatch.setattr(main, "_resolve_primary_chart_id", lambda uid: "c1")
    monkeypatch.setattr(oc, "record_outcome", lambda sb, cid, o, note, via: recorded.append((cid, o, via)) or True)

    async def no_ask(req):
        raise AssertionError("a check-in answer must not start an Ask")
    monkeypatch.setattr(main, "ask_endpoint", no_ask)
    asyncio.run(main._wa_handle("+919812345678", "2", time.time()))
    assert recorded == [("k9", "partly", "whatsapp")]
    assert sent[-1].startswith("Thanks — noted.")
    assert link["context"].get("last_in")
