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

    async def fake_handle(number, body, ts):
        handled.append((number, body))
    monkeypatch.setattr(m, "_wa_handle", fake_handle)
    params = {"MessageSid": "SM1", "From": "whatsapp:+919812345678",
              "Body": "When will I change jobs?"}
    raw, sig = _signed(params)
    c = TestClient(m.app)
    hdr = {"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig}
    r = c.post("/api/v1/messaging/whatsapp/webhook", content=raw, headers=hdr)
    assert r.status_code == 200 and r.text == "<Response></Response>"
    # a Twilio retry of the same MessageSid is not answered twice
    c.post("/api/v1/messaging/whatsapp/webhook", content=raw, headers=hdr)
    assert handled == [("+919812345678", "When will I change jobs?")]


def test_unlinked_number_never_reaches_ask(m, monkeypatch):
    sent, asked = [], []
    monkeypatch.setattr(msg, "resolve_chart", lambda *a, **k: None)
    monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: sent.append(t) or True)

    async def fake_ask(req):
        asked.append(req)
        return {}
    monkeypatch.setattr(m, "ask_endpoint", fake_ask)
    monkeypatch.delenv("WHATSAPP_CONNECT_URL", raising=False)
    asyncio.run(m._wa_handle("+919812345678", "Will I get married?", time.time()))
    assert asked == []
    assert len(sent) == 1 and "Connect WhatsApp" in sent[0]


def test_linked_number_gets_ack_then_answer(m, monkeypatch):
    sent = []
    monkeypatch.setattr(msg, "resolve_chart", lambda *a, **k: "chart-1")
    monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: sent.append(t) or True)

    async def fake_ask(req):
        assert req.chart_id == "chart-1" and req.tz_offset == 330
        return {"read": "The window opens in March.", "next": "Prepare now."}
    monkeypatch.setattr(m, "ask_endpoint", fake_ask)
    asyncio.run(m._wa_handle("+919812345678", "When will I change jobs?", time.time()))
    assert sent[0] == "Reading your chart…"
    assert "March" in sent[1]


def test_soft_cap_jsonresponse_is_unwrapped(m, monkeypatch):
    from fastapi.responses import JSONResponse
    sent = []
    monkeypatch.setattr(msg, "resolve_chart", lambda *a, **k: "chart-1")
    monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: sent.append(t) or True)

    async def fake_ask(req):
        return JSONResponse(status_code=200, content={
            "read": "You've used today's 1 Ask question.", "error": "daily_cap"})
    monkeypatch.setattr(m, "ask_endpoint", fake_ask)
    asyncio.run(m._wa_handle("+15551234567", "Should I move?", time.time()))
    assert "used today's" in sent[-1]
