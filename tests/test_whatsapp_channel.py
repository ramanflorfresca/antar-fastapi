"""
WhatsApp (Twilio) Ask channel — 2026-10-02.

Pure helpers in antar_engine/messaging.py plus the webhook contract in main.py:
signature verification, the 24h send guard, message splitting, commands, the
Path-B connect token, and that the webhook ACKs fast and answers in the background.
"""
import asyncio
import time
import urllib.parse

import pytest

from antar_engine import messaging as msg


# ─── signature ─────────────────────────────────────────────────────

# Twilio's documented example (verified against twilio.request_validator).
_URL = "https://mycompany.com/myapp.php?foo=1&bar=2"
_PARAMS = {"CallSid": "CA1234567890ABCDE", "Caller": "+12349013030", "Digits": "1234",
           "From": "+12349013030", "To": "+18005551212"}


def test_signature_matches_twilio_reference():
    assert msg.twilio_signature_ok("12345", _URL, _PARAMS, "0/KCTR6DLpKmkAf8muzZqo1nDgQ=")


def test_signature_rejects_tampering():
    bad = dict(_PARAMS, Digits="9999")
    assert not msg.twilio_signature_ok("12345", _URL, bad, "0/KCTR6DLpKmkAf8muzZqo1nDgQ=")
    assert not msg.twilio_signature_ok("12345", _URL, _PARAMS, "")
    assert not msg.twilio_signature_ok("", _URL, _PARAMS, "0/KCTR6DLpKmkAf8muzZqo1nDgQ=")


# ─── numbers, window, splitting ────────────────────────────────────

def test_wa_number_normalises():
    assert msg.wa_number("whatsapp:+919812345678") == "+919812345678"
    assert msg.wa_number("+1 (415) 523-8886") == "+14155238886"
    assert msg.wa_number("whatsapp:") == ""
    assert msg.wa_number("abc") == ""


def test_24h_window_guard():
    now = time.time()
    assert msg.wa_window_open(now - 60, now)
    assert not msg.wa_window_open(now - 24 * 3600 - 1, now)
    assert not msg.wa_window_open(None, now)


def test_send_refuses_outside_window(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC1")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "t")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    called = []
    monkeypatch.setattr(msg.urllib.request, "urlopen", lambda *a, **k: called.append(a))
    assert not msg.whatsapp_send("+919812345678", "hi", time.time() - 25 * 3600)
    assert called == []
    assert msg.whatsapp_send("+919812345678", "hi", time.time())
    body = urllib.parse.parse_qs(called[0][0].data.decode())
    assert body["To"] == ["whatsapp:+919812345678"]
    assert body["From"] == ["whatsapp:+14155238886"]


def test_split_respects_limit_and_order():
    paras = [("para %d " % i) * 60 for i in range(6)]
    parts = msg.wa_split("\n\n".join(paras))
    assert len(parts) > 1
    assert all(len(p) <= msg.WA_MAX_CHARS for p in parts)
    assert parts[0].startswith("para 0")
    one_long = "x" * 4000
    assert all(len(p) <= msg.WA_MAX_CHARS for p in msg.wa_split(one_long))
    assert msg.wa_split("short") == ["short"]


# ─── commands ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("LINK aB3_x-9Q", ("link", "aB3_x-9Q")),
    ("link K7P2Q", ("link", "K7P2Q")),
    ("STOP", ("unlink", "")),
    ("stop.", ("unlink", "")),
    ("help", ("help", "")),
    ("ayuda", ("help", "")),
    ("should I stop my job this year?", ("", "")),     # a question, not a command
    ("kya meri shaadi is saal hogi?", ("", "")),
])
def test_commands(text, expected):
    assert msg.parse_wa_command(text) == expected


# ─── Path B token ──────────────────────────────────────────────────

def test_connect_token_roundtrip_and_tamper():
    tok = msg.make_connect_token("s3cret", "whatsapp:+919812345678")
    assert msg.read_connect_token("s3cret", tok) == "+919812345678"
    assert msg.read_connect_token("other", tok) is None
    body, sig = tok.rsplit(".", 1)
    assert msg.read_connect_token("s3cret", body + "." + ("0" * len(sig))) is None
    expired = msg.make_connect_token("s3cret", "+919812345678", ttl_s=-1)
    assert msg.read_connect_token("s3cret", expired) is None


# ─── formatting ────────────────────────────────────────────────────

def test_format_uses_whatsapp_bold():
    out = msg.format_ask_for_whatsapp(
        {"read": "**Yes** — the window is open.", "timing": "Nov 2026 – Feb 2027",
         "next": "Send the proposal this month."}, "en")
    assert "*Yes*" in out and "**" not in out
    assert "Nov 2026" in out and "Send the proposal" in out


# ─── webhook contract (main.py) ────────────────────────────────────

@pytest.fixture()
def m(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setenv("TWILIO_WEBHOOK_URL", "https://api.example.com/api/v1/messaging/whatsapp/webhook")
    monkeypatch.setenv("WHATSAPP_ENABLED", "true")
    main._WA_SEEN.clear()
    return main


def _signed(params):
    import base64, hashlib, hmac
    url = "https://api.example.com/api/v1/messaging/whatsapp/webhook"
    data = url + "".join(k + params[k] for k in sorted(params))
    sig = base64.b64encode(hmac.new(b"tok", data.encode(), hashlib.sha1).digest()).decode()
    return urllib.parse.urlencode(params), sig


def test_webhook_rejects_unsigned(m):
    from fastapi.testclient import TestClient
    c = TestClient(m.app)
    r = c.post("/api/v1/messaging/whatsapp/webhook", content="From=whatsapp%3A%2B911&Body=hi",
               headers={"Content-Type": "application/x-www-form-urlencoded",
                        "X-Twilio-Signature": "nope"})
    assert r.status_code == 403


def test_webhook_acks_fast_and_answers_in_background(m, monkeypatch):
    from fastapi.testclient import TestClient
    handled = []

    async def fake_handle(number, body, ts, num_media=0):
        handled.append((number, body, num_media))
    monkeypatch.setattr(m, "_wa_handle", fake_handle)
    params = {"MessageSid": "SM1", "From": "whatsapp:+919812345678",
              "Body": "When will I change jobs?", "NumMedia": "0"}
    raw, sig = _signed(params)
    c = TestClient(m.app)
    hdr = {"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig}
    r = c.post("/api/v1/messaging/whatsapp/webhook", content=raw, headers=hdr)
    assert r.status_code == 200 and r.text == "<Response></Response>"
    # a Twilio retry of the same MessageSid is not answered twice
    c.post("/api/v1/messaging/whatsapp/webhook", content=raw, headers=hdr)
    assert handled == [("+919812345678", "When will I change jobs?", 0)]
    # a media-only message still reaches the handler (it replies "text only")
    raw2, sig2 = _signed({"MessageSid": "SM2", "From": "whatsapp:+919812345678",
                          "Body": "", "NumMedia": "1"})
    c.post("/api/v1/messaging/whatsapp/webhook", content=raw2,
           headers={"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig2})
    assert handled[-1] == ("+919812345678", "", 1)


# ─── conversation handler ──────────────────────────────────────────

class _Conv:
    """Wires _wa_handle to an in-memory link row + captured sends."""
    def __init__(self, m, monkeypatch, link=None, charts=None, primary="self-1", answer=None,
                 delay=0.0):
        self.sent, self.asked, self.saved = [], [], []
        self.link = link
        self.answer = answer if answer is not None else {
            "read": "Hold until spring. The stronger move opens in March.",
            "timing": "March – June 2027", "next": "Update your portfolio this month.",
            "suggested_questions": ["Which role fits me?", "How will money be?", "Should I start my own?"]}
        monkeypatch.setattr(msg, "get_whatsapp_link", lambda sb, n: self.link)
        monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: self.sent.append(t) or True)
        monkeypatch.setattr(msg, "save_link_context",
                            lambda sb, l, c: self.saved.append(c) or (l.__setitem__("context", c) if l else None) or True)
        monkeypatch.setattr(msg, "set_link_chart",
                            lambda sb, l, cid: l.__setitem__("chart_id", cid) or True)
        monkeypatch.setattr(msg, "list_user_charts", lambda sb, uid, p: charts or [])
        monkeypatch.setattr(m, "_resolve_primary_chart_id", lambda uid: primary)
        monkeypatch.setattr(m, "_wa_chart_alive", lambda cid: True)
        monkeypatch.setattr(m, "_wa_chart_name", lambda cid: {"self-1": "Raman Singh", "mom-1": "Mom"}.get(cid, "X"))

        async def fake_ask(req):
            self.asked.append(req)
            if delay:
                await asyncio.sleep(delay)
            return self.answer
        monkeypatch.setattr(m, "ask_endpoint", fake_ask)
        self.m = m

    def run(self, body, num_media=0):
        asyncio.run(self.m._wa_handle("+919812345678", body, time.time(), num_media))


def _link(chart="self-1"):
    return {"id": 1, "chart_id": chart, "user_id": "u1", "context": {}}


def test_unlinked_number_never_reaches_ask(m, monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONNECT_URL", raising=False)
    cv = _Conv(m, monkeypatch, link=None)
    cv.run("Will I get married?")
    assert cv.asked == []
    assert len(cv.sent) == 1 and "Connect WhatsApp" in cv.sent[0]


def test_answer_layout_and_followups_remembered(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("When will I change jobs?")
    assert cv.asked[0].chart_id == "self-1" and cv.asked[0].tz_offset == 330
    out = cv.sent[-1]
    assert out.startswith("*Hold until spring.*")              # bold first sentence
    assert "🗓 _Window: March" in out and "→ Update your portfolio" in out
    assert out.rstrip().endswith("3  Should I start my own?")
    assert "Reading your chart" not in " ".join(cv.sent)        # fast answer: no ack
    assert cv.saved[-1]["options"]["items"][0] == "Which role fits me?"


def test_digit_asks_the_numbered_followup(m, monkeypatch):
    link = _link()
    link["context"] = msg.remember_options({}, "ask", ["Which role fits me?", "How will money be?"])
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("2")
    assert cv.asked[0].question == "How will money be?"
    assert cv.sent[-1].startswith("*→ How will money be?*")


def test_slow_answer_sends_reading_first(m, monkeypatch):
    monkeypatch.setattr(m, "_WA_READING_AFTER_S", 0.05)
    cv = _Conv(m, monkeypatch, link=_link(), delay=0.2)
    cv.run("When will I change jobs?")
    assert cv.sent[0] == "Reading your chart…" and "Hold until spring" in cv.sent[1]


def test_thanks_uses_no_question(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    for t in ("thanks!", "gracias", "🙏", "shukriya"):
        cv.run(t)
    assert cv.asked == [] and len(cv.sent) == 4


def test_media_only_gets_text_only_reply(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("", num_media=1)
    assert cv.asked == [] and "only read text" in cv.sent[0]


def test_switch_list_pick_and_header(m, monkeypatch):
    charts = [("self-1", "Raman Singh", True), ("mom-1", "Mom", False)]
    link = _link()
    cv = _Conv(m, monkeypatch, link=link, charts=charts)
    cv.run("switch")
    assert "1  Raman Singh (you) ✓" in cv.sent[-1] and "2  Mom" in cv.sent[-1]
    cv.run("2")
    assert link["chart_id"] == "mom-1" and "Mom" in cv.sent[-1] and cv.asked == []
    cv.run("How is her health this year?")
    assert cv.asked[-1].chart_id == "mom-1"
    assert cv.sent[-1].startswith("_Antar · Mom_")


def test_switch_by_name_and_single_chart(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link, charts=[("self-1", "Raman Singh", True), ("mom-1", "Mom", False)])
    cv.run("ask about mom")
    assert link["chart_id"] == "mom-1"
    cv2 = _Conv(m, monkeypatch, link=_link(), charts=[("self-1", "Raman Singh", True)])
    cv2.run("switch")
    assert "only your own chart" in cv2.sent[-1]


def test_soft_cap_once_a_day(m, monkeypatch):
    from fastapi.responses import JSONResponse
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)

    async def capped(req):
        return JSONResponse(status_code=200, content={
            "read": "You've used today's 1 Ask question.", "error": "daily_cap", "soft_capped": True})
    monkeypatch.setattr(m, "ask_endpoint", capped)
    cv.run("Should I move?")
    assert "antar.world/upgrade" in cv.sent[-1]
    cv.run("And next month?")
    assert "upgrade" not in cv.sent[-1] and "resets tomorrow" in cv.sent[-1]


def test_hinglish_short_messages(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=None)
    monkeypatch.delenv("WHATSAPP_CONNECT_URL", raising=False)
    cv.run("kya meri shaadi is saal hogi?")
    assert cv.sent[0].startswith("Namaste")


def test_link_sends_welcome_with_starters(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=None, charts=[("self-1", "Raman Singh", True), ("mom-1", "Mom", False)])
    monkeypatch.setattr(msg, "bind_link_whatsapp", lambda sb, code, n: "self-1")
    cv.link = None
    def after_bind(sb, n):
        return _link()
    monkeypatch.setattr(msg, "get_whatsapp_link", lambda sb, n: cv.link)
    import antar_engine.ask_suggestions as sugg
    monkeypatch.setattr(sugg, "build_suggested_prompts",
                        lambda cid, sb, language="en": [{"text": "Q1"}, {"text": "Q2"}, {"text": "Q3"}, {"text": "Q4"}])
    orig_bind = msg.bind_link_whatsapp
    def bind(sb, code, n):
        cv.link = _link()
        return "self-1"
    monkeypatch.setattr(msg, "bind_link_whatsapp", bind)
    cv.run("LINK abc12345")
    w = cv.sent[-1]
    assert "Raman Singh" in w and "1  Q1" in w and "3  Q3" in w and "Q4" not in w
    assert "Mom" in w and "switch" in w
    assert cv.saved[-1]["options"]["items"] == ["Q1", "Q2", "Q3"]


def test_helpers():
    assert msg.parse_pick("2") == 2 and msg.parse_pick("2.") == 2 and msg.parse_pick("12") is None
    assert msg.parse_switch("switch") == "" and msg.parse_switch("switch to Mom") == "Mom"
    assert msg.parse_switch("cambiar a Ana") == "Ana" and msg.parse_switch("ask about Ana") == "Ana"
    assert msg.parse_switch("should I switch jobs?") is None
    assert msg.is_thanks("ok thanks") and msg.is_thanks("theek hai")
    assert not msg.is_thanks("thanks, but when will it happen?")
    assert msg.match_chart([("a", "Ana Lopez", False), ("b", "Mom", False)], "ana")[0] == "a"
    ctx = msg.remember_options({}, "ask", ["x"], now=0)
    assert msg.pick_option(ctx, 1, now=10) == ("ask", "x")
    assert msg.pick_option(ctx, 1, now=25 * 3600) == (None, None)


# ─── status / unlink endpoints ─────────────────────────────────────

def test_status_and_unlink_endpoints(m, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    monkeypatch.setattr(msg, "whatsapp_status", lambda sb, uid: {
        "linked": True, "number_last4": "5678", "chart_id": "c1", "linked_at": "2026-10-02"})
    monkeypatch.setattr(m, "_wa_chart_name", lambda cid: "Raman Singh")
    revoked = []
    monkeypatch.setattr(msg, "_revoke_whatsapp", lambda sb, **kw: revoked.append(kw) or True)
    c = TestClient(m.app)
    r = c.get("/api/v1/messaging/whatsapp/status", headers={"Authorization": "Bearer x"}).json()
    assert r["linked"] and r["number_last4"] == "5678" and r["chart_name"] == "Raman Singh"
    assert r["available"] is True and r["antar_number"] == "+14155238886"
    r = c.post("/api/v1/messaging/whatsapp/unlink", headers={"Authorization": "Bearer x"}).json()
    assert r == {"linked": False} and revoked == [{"user_id": "user-1"}]
