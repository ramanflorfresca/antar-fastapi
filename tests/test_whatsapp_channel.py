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


@pytest.fixture(autouse=True)
def _policy_already_accepted(monkeypatch):
    """[wa-policy] These tests are about the conversation, not the data-policy gate (tested in
    test_wa_policy_acceptance.py). Without this, policy_state reads the REAL wa_policy_acceptances table
    whenever a local .env is present and every unknown test number is asked to accept first."""
    from antar_engine import messaging as _m
    monkeypatch.setattr(_m, "policy_state", lambda *a, **k: "ok")



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

    async def fake_handle(number, body, ts, num_media=0, sink=None, sid="", choice="", lat_lon=None, media=None):
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
                 delay=0.0, policy="ok"):
        self.sent, self.asked, self.saved = [], [], []
        self.link = link
        self.answer = answer if answer is not None else {
            "read": "Hold until spring. The stronger move opens in March.",
            "timing": "March – June 2027", "next": "Update your portfolio this month.",
            "suggested_questions": ["Which role fits me?", "How will money be?", "Should I start my own?"]}
        monkeypatch.setattr(msg, "get_whatsapp_link", lambda sb, n: self.link)
        # [wa-policy] The data-processing gate added in #198 answers EVERY inbound
        # message with the policy prompt until the number has accepted the current
        # wording. These conversations are not about that gate, and the fixture
        # stubs every other messaging dependency, so stub this one too. Pass
        # policy="needed" to exercise the gate itself.
        monkeypatch.setattr(msg, "policy_state", lambda sb, n, l: policy)
        monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: self.sent.append(t) or True)
        monkeypatch.setattr(msg, "save_link_context",
                            lambda sb, l, c: self.saved.append(c) or (l.__setitem__("context", c) if l else None) or True)
        monkeypatch.setattr(msg, "set_link_chart",
                            lambda sb, l, cid: l.__setitem__("chart_id", cid) or True)
        monkeypatch.setattr(msg, "list_user_charts", lambda sb, uid, p: charts or [])
        self.typing = []
        monkeypatch.setattr(msg, "whatsapp_typing", lambda sid: self.typing.append(sid) or True)
        self.lists = []
        self.list_ok = False          # default: lists unavailable → numbered text
        monkeypatch.setattr(msg, "whatsapp_send_list",
                            lambda n, b, btn, items, ts: (self.lists.append((b, btn, items)) or True)
                            if self.list_ok else False)
        monkeypatch.setattr(m, "_resolve_primary_chart_id", lambda uid: primary)
        monkeypatch.setattr(m, "_wa_chart_alive", lambda cid: True)
        monkeypatch.setattr(m, "_wa_saved_lang", lambda cid: None)
        monkeypatch.setattr(m, "_wa_resolve_tz", lambda cid, n, ctx=None: (m._wa_tz(n), "number", ""))
        monkeypatch.setattr(m, "_wa_number_tz", lambda cid, n: (m._wa_tz(n), ""))
        monkeypatch.setattr(m, "_wa_prashna_lock", lambda cid, q="": None)
        monkeypatch.setattr(m, "_wa_chart_name", lambda cid: {"self-1": "Raman Singh", "mom-1": "Mom"}.get(cid, "X"))

        async def fake_ask(req):
            self.asked.append(req)
            if delay:
                await asyncio.sleep(delay)
            return self.answer
        monkeypatch.setattr(m, "ask_endpoint", fake_ask)
        self.m = m

    def run(self, body, num_media=0, lat_lon=None, choice_id="", media=None):
        asyncio.run(self.m._wa_handle("+919812345678", body, time.time(), num_media,
                                      None, "", choice_id, lat_lon, media))


def _link(chart="self-1", consented=True):
    """A linked WhatsApp number.

    [wa-consent] carries consent_version by default: the data-processing-policy
    gate added in #198 answers EVERY inbound message with the policy prompt
    until the link has accepted the current wording, so without this each of
    these tests would assert against the prompt instead of the behaviour it is
    actually about. The gate keeps its own dedicated tests below; pass
    consented=False to exercise it here.
    """
    link = {"id": 1, "chart_id": chart, "user_id": "u1", "context": {}}
    if consented:
        link["consent_version"] = msg.WA_CONSENT_VERSION
    return link


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
    assert out.rstrip().endswith("3  Should I start my own?\n_…or just type your own question._")
    assert "Reading your chart" not in " ".join(cv.sent)        # fast answer: no ack
    assert cv.saved[-1]["options"]["items"][0] == "Which role fits me?"


def test_digit_asks_the_numbered_followup(m, monkeypatch):
    link = _link()
    link["context"] = msg.remember_options({}, "ask", ["Which role fits me?", "How will money be?"])
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("2")
    assert cv.asked[0].question == "How will money be?"
    assert cv.sent[-1].startswith("*→ How will money be?*")


def test_slow_answer_sends_only_the_complete_answer(m, monkeypatch):
    monkeypatch.setattr(m, "_WA_READING_AFTER_S", 0.05)
    cv = _Conv(m, monkeypatch, link=_link(), delay=0.2)
    cv.run("When will I change jobs?")
    assert len(cv.sent) == 1 and "Hold until spring" in cv.sent[0]   # no holding message


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
    cv.run("Where should I move next year?")
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
    monkeypatch.setattr(msg, "bind_link_whatsapp", lambda sb, code, n, consent=None: "self-1")
    cv.link = None
    def after_bind(sb, n):
        return _link()
    monkeypatch.setattr(msg, "get_whatsapp_link", lambda sb, n: cv.link)
    import antar_engine.ask_suggestions as sugg
    monkeypatch.setattr(sugg, "build_suggested_prompts",
                        lambda cid, sb, language="en": [{"text": "Q1"}, {"text": "Q2"}, {"text": "Q3"}, {"text": "Q4"}])
    orig_bind = msg.bind_link_whatsapp
    def bind(sb, code, n, consent=None):
        cv.link = _link()
        return "self-1"
    monkeypatch.setattr(msg, "bind_link_whatsapp", bind)
    monkeypatch.setattr(msg, "peek_pending_code", lambda sb, code: {"id": 1, "consent_at": "2026-10-06"})
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


# ─── consent (opt-in + Terms/Privacy) ──────────────────────────────

def test_link_start_no_longer_needs_app_consent_but_records_it_when_given(m, monkeypatch):
    """[wa-qr-consent] the QR comes first; consent is accepted in WhatsApp after the scan."""
    from fastapi.testclient import TestClient
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    monkeypatch.setattr(m, "_resolve_primary_chart_id", lambda uid: "chart-1")
    rows = []
    monkeypatch.setattr(msg, "create_pending_link",
                        lambda sb, cid, uid, ch, extra=None: rows.append(extra) or
                        {"available": True, "code": "abc12345", "channel": ch})
    c = TestClient(m.app)
    h = {"Authorization": "Bearer x"}
    r = c.post("/api/v1/messaging/link/start", json={"channel": "whatsapp"}, headers=h)
    assert r.status_code == 200 and not (rows[-1] or {}).get("consent_at")
    r = c.post("/api/v1/messaging/link/start", headers=h, json={
        "channel": "whatsapp", "consent_accepted": True, "consent_version": "old"})
    assert r.status_code == 200 and not (rows[-1] or {}).get("consent_at")
    r = c.post("/api/v1/messaging/link/start", headers=h, json={
        "channel": "whatsapp", "consent_accepted": True,
        "consent_version": msg.WA_CONSENT_VERSION})
    assert r.status_code == 200
    assert rows[-1]["consent_version"] == msg.WA_CONSENT_VERSION and rows[-1]["consent_source"] == "app"


# ─── QR first, consent in chat ─────────────────────────────────────

def test_qr_scan_without_consent_holds_the_code_and_asks_terms_and_privacy(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=None, policy="needed")
    held, bound = [], []
    monkeypatch.setattr(msg, "peek_pending_code", lambda sb, code: {"id": 1, "chart_id": "self-1"})
    monkeypatch.setattr(msg, "hold_code_for_number", lambda sb, code, n: held.append(code) or True)
    monkeypatch.setattr(msg, "bind_link_whatsapp", lambda *a, **k: bound.append(a) or "self-1")
    cv.run("LINK abc12345")
    assert held == ["abc12345"] and bound == [], "never linked before ACCEPT"
    assert "terms" in cv.sent[-1].lower() and "privacy policy" in cv.sent[-1].lower()


def test_accept_after_the_scan_links_with_in_chat_consent_and_offers_optional_alerts(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=None, policy="needed")
    got = {}
    monkeypatch.setattr(msg, "record_policy", lambda *a, **k: True)
    monkeypatch.setattr(msg, "held_code_for", lambda sb, n: "abc12345")

    def bind(sb, code, n, consent=None):
        got["code"], got["consent"] = code, consent
        cv.link = _link()
        return "self-1"
    monkeypatch.setattr(msg, "bind_link_whatsapp", bind)
    cv.run("ACCEPT")
    assert got["code"] == "abc12345" and got["consent"]["consent_source"] == "whatsapp"
    assert got["consent"]["consent_version"] == msg.WA_CONSENT_VERSION
    assert any("alert" in t.lower() and "optional" in t.lower() for t in cv.sent)


def test_optin_reply_parsing():
    assert msg.parse_optin_reply("Sí") == "yes" and msg.parse_optin_reply("no gracias") == "no"
    assert msg.parse_optin_reply("x", "opt:offers:yes") == "yes"
    assert msg.parse_optin_reply("When will I marry?") is None


class _FakeQ:
    def __init__(self, store):
        self.store, self.upd = store, None
    def select(self, *a): return self
    def eq(self, *a): return self
    def neq(self, *a): return self
    def limit(self, *a): return self
    def update(self, d): self.upd = d; return self
    def execute(self):
        if self.upd is not None:
            self.store["updates"].append(self.upd)
            return type("R", (), {"data": []})()
        return type("R", (), {"data": self.store["rows"]})()


class _FakeSB:
    def __init__(self, rows): self.store = {"rows": rows, "updates": []}
    def table(self, name): return _FakeQ(self.store)


def test_bind_refuses_code_without_consent():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    sb = _FakeSB([{"id": 1, "chart_id": "c1", "user_id": "u1", "created_at": now}])
    assert msg.bind_link_whatsapp(sb, "abc12345", "+919812345678") is None
    assert not any(u.get("status") == "linked" for u in sb.store["updates"])
    sb2 = _FakeSB([{"id": 1, "chart_id": "c1", "user_id": "u1", "created_at": now,
                    "consent_at": now, "consent_version": msg.WA_CONSENT_VERSION}])
    assert msg.bind_link_whatsapp(sb2, "abc12345", "+919812345678") == "c1"
    assert any(u.get("status") == "linked" for u in sb2.store["updates"])


def test_direct_link_requires_consent():
    assert msg.link_whatsapp_direct(_FakeSB([]), "c1", "u1", "+919812345678") is False


def test_alerts_opt_in_is_separate_and_off_by_default(m, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    monkeypatch.setattr(m, "_resolve_primary_chart_id", lambda uid: "chart-1")
    rows = []
    monkeypatch.setattr(msg, "create_pending_link",
                        lambda sb, cid, uid, ch, extra=None: rows.append(extra) or
                        {"available": True, "code": "abc12345", "channel": ch})
    c = TestClient(m.app)
    body = {"channel": "whatsapp", "consent_accepted": True,
            "consent_version": msg.WA_CONSENT_VERSION}
    c.post("/api/v1/messaging/link/start", json=body, headers={"Authorization": "Bearer x"})
    c.post("/api/v1/messaging/link/start", json=dict(body, alerts_opt_in=True),
           headers={"Authorization": "Bearer x"})
    assert rows[0]["alerts_opt_in"] is False and rows[1]["alerts_opt_in"] is True


def test_help_is_answered_inline_with_twiml(m, monkeypatch):
    from fastapi.testclient import TestClient
    handled = []

    async def fake_handle(*a, **k):
        handled.append(a)
    monkeypatch.setattr(m, "_wa_handle", fake_handle)
    raw, sig = _signed({"MessageSid": "SM9", "From": "whatsapp:+919812345678",
                        "Body": "ayuda", "NumMedia": "0"})
    r = TestClient(m.app).post("/api/v1/messaging/whatsapp/webhook", content=raw, headers={
        "Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig})
    assert r.status_code == 200 and r.text.startswith("<Response><Message>")
    assert "Hazme cualquier pregunta" in r.text and handled == []



# ─── inline (TwiML) replies ────────────────────────────────────────

def _post(m, params):
    from fastapi.testclient import TestClient
    raw, sig = _signed(params)
    return TestClient(m.app).post("/api/v1/messaging/whatsapp/webhook", content=raw, headers={
        "Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig})


def test_fast_answer_returns_inline_twiml(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    r = _post(m, {"MessageSid": "SMf1", "From": "whatsapp:+919812345678",
                  "Body": "When will I change jobs?", "NumMedia": "0"})
    assert r.status_code == 200
    assert r.text.count("<Message>") == 1 and "Hold until spring" in r.text
    assert cv.sent == []                       # nothing went through REST


def test_slow_answer_reading_inline_then_rest(m, monkeypatch):
    monkeypatch.setattr(m, "_WA_INLINE_DEADLINE_S", 2.0)
    from fastapi.testclient import TestClient
    link = _link()
    link["context"] = {"rest_ok_at": int(time.time())}       # REST known to work here
    cv = _Conv(m, monkeypatch, link=link, delay=2.5)
    raw, sig = _signed({"MessageSid": "SMs1", "From": "whatsapp:+919812345678",
                        "Body": "When will I change jobs?", "NumMedia": "0"})
    with TestClient(m.app) as c:       # keep the loop alive, as uvicorn does
        r = c.post("/api/v1/messaging/whatsapp/webhook", content=raw, headers={
            "Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig})
        assert r.text == "<Response></Response>"          # nothing partial goes out
        deadline = time.time() + 5
        while not cv.sent and time.time() < deadline:
            time.sleep(0.1)
    assert cv.sent and "Hold until spring" in cv.sent[-1]   # answer followed via REST


def test_inline_can_be_switched_off(m, monkeypatch):
    monkeypatch.setenv("WHATSAPP_INLINE_REPLIES", "off")
    cv = _Conv(m, monkeypatch, link=_link())
    r = _post(m, {"MessageSid": "SMo1", "From": "whatsapp:+919812345678",
                  "Body": "When will I change jobs?", "NumMedia": "0"})
    assert r.text == "<Response></Response>"


# ─── undelivered answers handed over on the next message ───────────

def test_failed_send_is_kept_and_delivered_on_next_message(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)
    monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: False)     # REST blocked
    cv.run("When will I change jobs?")
    ctx = link["context"]
    assert "Hold until spring" in ctx["pending"]["items"][-1] and ctx.get("rest_blocked_at")
    asked_before = len(cv.asked)
    monkeypatch.setattr(msg, "whatsapp_send", lambda n, t, ts: cv.sent.append(t) or True)
    cv.run("ok")
    assert any("Hold until spring" in t for t in cv.sent)
    assert len(cv.asked) == asked_before                  # "ok" didn't trigger a new Ask
    assert "pending" not in link["context"] and "rest_blocked_at" not in link["context"]


def test_pending_then_new_question_answers_both(m, monkeypatch):
    link = _link()
    link["context"] = {"pending": {"items": ["*Old answer.*"], "at": int(time.time())}}
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("And what about money?")
    assert cv.sent[0] == "*Old answer.*" and "Hold until spring" in cv.sent[-1]
    assert cv.asked[-1].question == "And what about money?"


def test_reading_message_asks_for_ok_while_rest_blocked(m, monkeypatch):
    monkeypatch.setattr(m, "_WA_INLINE_DEADLINE_S", 2.0)
    link = _link()
    link["context"] = {"rest_blocked_at": int(time.time())}
    cv = _Conv(m, monkeypatch, link=link, delay=2.5)
    r = _post(m, {"MessageSid": "SMp1", "From": "whatsapp:+919812345678",
                  "Body": "When will I change jobs?", "NumMedia": "0"})
    assert "Reply *ok* in about 20 seconds" in r.text


def test_slow_answer_asks_for_ok_even_without_a_recent_block(m, monkeypatch):
    # live 2026-10-03 (Andres): last block >24h ago → no note → he waited for nothing
    monkeypatch.setattr(m, "_WA_INLINE_DEADLINE_S", 2.0)
    link = _link()
    link["context"] = {}
    cv = _Conv(m, monkeypatch, link=link, delay=2.5)
    r = _post(m, {"MessageSid": "SMp2", "From": "whatsapp:+919812345678",
                  "Body": "When will I change jobs?", "NumMedia": "0"})
    assert "Reply *ok* in about 20 seconds" in r.text



# ─── no partial messages: typing indicator + nudges ────────────────

def test_typing_indicator_fires_for_a_question(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link(), delay=0.1)
    asyncio.run(m._wa_handle("+919812345678", "When will I change jobs?", time.time(),
                             0, None, "SMabc"))
    assert cv.typing and cv.typing[0] == "SMabc"
    assert len(cv.sent) == 1 and "Hold until spring" in cv.sent[0]


def test_nudge_while_answer_in_flight_sends_nothing(m, monkeypatch):
    link = _link()
    link["context"] = {"in_flight_at": int(time.time())}
    cv = _Conv(m, monkeypatch, link=link)
    for t in ("Waiting", "hello?", "still there", "ok"):
        asyncio.run(m._wa_handle("+919812345678", t, time.time(), 0, None, "SMn"))
    assert cv.sent == [] and cv.asked == [] and cv.typing


def test_greeting_gets_menu_not_an_ask(m, monkeypatch):
    import antar_engine.ask_suggestions as sugg
    monkeypatch.setattr(sugg, "build_suggested_prompts",
                        lambda cid, sb, language="en": [{"text": "Q1"}, {"text": "Q2"}, {"text": "Q3"}])
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("Hello")
    assert cv.asked == []
    assert cv.sent[0].startswith("Hi \U0001f64f What would you like to know?") and "3  Q3" in cv.sent[0]
    cv.run("2")
    assert cv.asked[-1].question == "Q2"


def test_in_flight_flag_cleared_after_answer(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("When will I change jobs?")
    assert "in_flight_at" not in link["context"]

def test_format_bolds_the_answer_not_the_warm_opener_and_drops_offer():
    t, fus = msg.format_ask_whatsapp_v2({
        "read": "Raman, the wait is real. The trigger is a key client noticing your work. "
                "Want me to look at early 2027?",
        "practice_cta": {"available": True, "label": "A grounding minute", "step": "Six slow breaths."},
        "suggested_questions": ["Q1", "Q2"]})
    assert t.startswith("Raman, the wait is real.\n\n*The trigger is a key client noticing your work.*")
    assert "Want me to look" not in t
    assert "\U0001f9d8 A grounding minute\nSix slow breaths." in t
    # without numbered follow-ups the offer stays (it's the only next step)
    t2, _ = msg.format_ask_whatsapp_v2({"read": "It opens in March. Want me to look at money?"})
    assert "Want me to look at money?" in t2



# ─── interactive lists ─────────────────────────────────────────────

def test_answer_followups_become_a_list_when_rest_is_used(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())                 # direct run = REST path
    cv.list_ok = True
    cv.run("When will I change jobs?")
    assert cv.sent == [] and len(cv.lists) == 1
    body, btn, items = cv.lists[0]
    assert body.startswith("*Hold until spring.*") and "1  " not in body
    # [followup-flows] title = kind of step (never the truncated question twice); last row = free text
    assert btn == "Ask next" and items[0] == ("💬 Ask this", "q:Which role fits me?", "Which role fits me?")
    assert items[-1][1] == "own"


def test_list_failure_falls_back_to_numbered_text(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("When will I change jobs?")
    assert cv.lists == [] and cv.sent and "1  Which role fits me?" in cv.sent[-1]


def test_inline_mode_keeps_numbered_text(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.list_ok = True
    r = _post(m, {"MessageSid": "SMl1", "From": "whatsapp:+919812345678",
                  "Body": "When will I change jobs?", "NumMedia": "0"})
    assert "1  Which role fits me?" in r.text and cv.lists == []


def test_interactive_switch_off(m, monkeypatch):
    monkeypatch.setenv("WHATSAPP_INTERACTIVE", "off")
    cv = _Conv(m, monkeypatch, link=_link())
    cv.list_ok = True
    cv.run("When will I change jobs?")
    assert cv.lists == [] and "1  Which role fits me?" in cv.sent[-1]


def test_list_tap_asks_the_full_question(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    asyncio.run(m._wa_handle("+919812345678", "Which day this week is\u2026", time.time(),
                             0, None, "SMt", "q:Which day this week is best for me?"))
    assert cv.asked[-1].question == "Which day this week is best for me?"


def test_chart_tap_switches(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link,
               charts=[("self-1", "Raman Singh", True), ("mom-1", "Mom", False)])
    asyncio.run(m._wa_handle("+919812345678", "Mom", time.time(), 0, None, "SMc", "chart:mom-1"))
    assert link["chart_id"] == "mom-1" and cv.asked == [] and "Mom" in cv.sent[-1]


def test_short_title():
    assert msg.short_title("Which day this week is best for me?") == "Which day this week is\u2026"
    assert len(msg.short_title("x" * 40)) == 24 and msg.short_title("Short") == "Short"


# ─── compact answers, "more", practice once a day ──────────────────

_LONG = {"read": ("Speculation is moderately favorable today — the gains side has real support "
                  "right now, and hidden gains are possible if you keep positions small. Your "
                  "savings are still under pressure, so don't pull from them to fund any move. "
                  "Best window: morning. Act before midday — after that, the window tightens fast. "
                  "Debt is live, so only put in what you can walk away from completely."),
         "next": "Cap any speculative position at an amount that leaves your savings untouched.",
         "practice_cta": {"available": True, "label": "A grounding minute before you act",
                          "step": "Pause and set a hard limit before you decide."},
         "suggested_questions": ["Which day this week is best for me?", "What is my safest way to play this?"]}


def test_compact_keeps_timing_and_fits_one_screen():
    full, _ = msg.format_ask_whatsapp_v2(_LONG, "en")
    c, _ = msg.format_ask_whatsapp_v2(_LONG, "en", compact=True, include_practice=False)
    assert len(c) < len(full) and "Best window: morning." in c and "Debt is live" not in c
    assert c.startswith("*Speculation is moderately favorable today")
    assert "→ Cap any speculative position" in c and "1  Which day" in c


def test_long_answer_offers_more_and_more_sends_full(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link, answer=dict(_LONG))
    cv.run("How is speculation today")
    assert "Reply *more* for the full read" in cv.sent[-1]
    assert "Debt is live" not in cv.sent[-1] and "Debt is live" in link["context"]["last_full"]
    n_asked = len(cv.asked)
    cv.run("more")
    assert "Debt is live" in cv.sent[-1] and len(cv.asked) == n_asked   # no new Ask


def test_practice_line_shows_once_a_day(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link, answer=dict(_LONG, read="Short answer today. Keep it small."))
    cv.run("How is speculation today")
    assert "A grounding minute" in cv.sent[-1]
    cv.run("And what about money this month in general")
    assert "A grounding minute" not in cv.sent[-1]


def test_compact_budget_covers_the_whole_message():
    # live 2026-10-02: ~650 chars incl. follow-ups still folded behind "Read more"
    p = {"read": ("Not yet — right now (Oct 2026) is for laying groundwork; the strong business "
                  "window is Nov 2026 – Jan 2027. The potential is real — your business sits in a "
                  "genuine growth chapter in the months ahead. Right now the pieces aren't fully "
                  "aligned yet; the trigger forms in the coming weeks into November."),
         "next": ("Pick one thing that's stopping you — money, whether people want your product, "
                  "or getting customers. Figure out which one matters most. Then spend this week "
                  "doing one real thing to fix it."),
         "suggested_questions": ["When is the best time to raise funding?",
                                 "Where will my first real customers come from?",
                                 "Should I build alone or bring in a partner?"]}
    c, fus = msg.format_ask_whatsapp_v2(p, "en", asked="When does my startup take off",
                                        compact=True, include_practice=False)
    assert len(c) <= msg.WA_COMPACT_BUDGET
    assert "into November" in c and "The potential is real" not in c     # specific timing wins
    assert c.startswith("*Not yet — right now (Oct 2026)") and "→ Pick one thing" in c
    assert len(fus) >= 2 and fus == [q for q in p["suggested_questions"] if q in c]



def test_where_question_keeps_the_substance_not_the_timing_line():
    # live 2026-10-02: kept "that short list" and dropped "Your network is your fastest path"
    p = {"read": ("Not yet — right now (Oct 2026) is for laying groundwork. Your network is your "
                  "fastest path — the people who already know your work are most likely to say yes "
                  "first. Right now, caution is holding back bold outreach, so warm introductions "
                  "beat cold pitches. The coming weeks are for building that short list."),
         "next": "Write those 10 names today and send the first message before the week ends.",
         "suggested_questions": ["When is the best time to raise funding?"]}
    c, _ = msg.format_ask_whatsapp_v2(p, "en", asked="Where will my first real customers come from?",
                                      compact=True, include_practice=False)
    assert "Your network is your fastest path" in c


def test_source_question_skips_the_dated_verdict():
    from dotenv import load_dotenv
    load_dotenv()
    import main
    for q in ("Where will my first real customers come from?", "Who will fund my startup?",
              "¿De dónde vendrán mis primeros clientes?", "Kahan se customers aayenge?"):
        assert main._is_source_q(q), q
    for q in ("When will I get funding?", "Where will I be next year?", "Should I raise now?",
              "Which month is best to launch?"):
        assert not main._is_source_q(q), q



# ─── Yes/No routing + timezone ─────────────────────────────────────

_YN_ANSWER = {"mode": "yesno", "verdict": "NO", "lean": "conditional",
              "why": "The door isn't open yet, but it can be if you clear one hurdle first.",
              "timing": "Oct 3, 2026 – Jan 31, 2027", "verify_after": "2027-01-31"}


def test_yesno_asks_for_the_kp_number_then_answers(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link, answer=dict(_YN_ANSWER, method="kp_number", horary_number=74))
    cv.run("prashna: Will I raise funding by March?")
    assert cv.asked == [] and "number from 1 to 249" in cv.sent[-1]
    assert link["context"]["kp_pending"]["q"] == "Will I raise funding by March?"
    cv.run("74")
    req = cv.asked[-1]
    assert req.mode == "yesno" and req.horary_number == 74
    assert req.question == "Will I raise funding by March?"
    out = cv.sent[-1]
    assert out.startswith("*→ Will I raise funding by March?*\n_Yes/No reading · #74_")
    assert "*Possible — on one condition.*" in out
    assert "check back after Jan 31" in out and "kp_pending" not in link["context"]


def test_kp_skip_reads_the_moment_and_range_is_checked(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link, answer=dict(_YN_ANSWER))
    cv.run("prashna: Will I get the job?")
    cv.run("300")
    assert "1 to 249" in cv.sent[-1] and cv.asked == []
    cv.run("prashna: Will I get the job?")
    cv.run("skip")
    assert cv.asked[-1].mode == "yesno" and cv.asked[-1].horary_number is None


def test_number_in_the_question_skips_the_ritual(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link(), answer=dict(_YN_ANSWER))
    cv.run("prashna: Will I get the job? number 74")
    assert cv.asked and cv.asked[-1].mode == "yesno"


def test_prashna_command_forces_kp(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link(), answer=dict(_YN_ANSWER))
    cv.run("prashna: tell me about the job offer")
    assert "number from 1 to 249" in cv.sent[-1]
    cv.run("12")
    assert cv.asked[-1].mode == "yesno" and cv.asked[-1].question == "tell me about the job offer"


def test_new_question_while_waiting_moves_on(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("prashna: Will I get the job?")
    cv.run("How is my career looking this year overall")
    assert cv.asked[-1].mode == "explore" and "kp_pending" not in link["context"]


def test_choice_question_is_not_yesno(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("Should I build alone or bring in a partner?")
    assert cv.asked[-1].mode == "explore"


def test_ritual_can_be_switched_off(m, monkeypatch):
    monkeypatch.setenv("WHATSAPP_KP_NUMBER_RITUAL", "off")
    cv = _Conv(m, monkeypatch, link=_link(), answer=dict(_YN_ANSWER))
    cv.run("prashna: Will I raise funding by March?")
    assert cv.asked[-1].mode == "yesno" and cv.asked[-1].horary_number is None


def test_yesno_question_first_asks_which_answer(m, monkeypatch):
    # owner 2026-10-03: "do you want yes or no, or detailed?" → only then the number
    link = _link()
    cv = _Conv(m, monkeypatch, link=link, answer=dict(_YN_ANSWER, method="kp_number", horary_number=7))
    q = "Will I make good money doing defence deals with the government?"
    cv.run(q)
    assert cv.asked == [] and "1  *Yes or no*" in cv.sent[-1] and "2  *Detailed reading*" in cv.sent[-1]
    assert "Prashna" not in cv.sent[-1]
    cv.run("1")
    assert cv.asked == [] and "number from 1 to 249" in cv.sent[-1]
    cv.run("7")
    assert cv.asked[-1].mode == "yesno" and cv.asked[-1].question == q


@pytest.mark.parametrize("reply", ["2", "detailed", "Detailed reading", "lectura detallada"])
def test_choosing_detailed_gives_the_regular_read(m, monkeypatch, reply):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("Will I get the job?")
    cv.run(reply)
    assert cv.asked[-1].mode == "explore" and cv.asked[-1].question == "Will I get the job?"
    assert "Reply *yes or no*" not in cv.sent[-1]


def test_choosing_yes_or_no_by_words_and_list_tap(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link(), answer=dict(_YN_ANSWER))
    cv.run("¿Voy a conseguir el trabajo?")
    assert "1  *Sí o no*" in cv.sent[-1]
    cv.run("sí o no")
    assert "1 al 249" in cv.sent[-1]                      # stays Spanish on a short reply
    cv.run("7")
    assert cv.asked[-1].mode == "yesno" and cv.asked[-1].language == "es"
    cv.run("Will I get the job?")
    cv.run("Detailed reading", choice_id="yn:read")             # list tap
    assert cv.asked[-1].mode == "explore" and cv.asked[-1].question == "Will I get the job?"


def test_a_new_question_instead_of_choosing_moves_on(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("Will I get the job?")
    cv.run("How is my career looking this year overall")
    assert cv.asked[-1].question == "How is my career looking this year overall"
    assert "choice_pending" not in link["context"]


def test_open_question_gets_no_prashna_offer(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("How is my career looking this year overall")
    assert cv.asked[-1].mode == "explore" and "yes or no" not in cv.sent[-1].lower()


@pytest.mark.parametrize("q,yn", [
    ("Will I raise funding by March?", True), ("Is this a good time to sign?", True),
    ("Should I build alone or bring in a partner?", False), ("When will I marry?", False),
    ("Will you tell me when I marry?", False), ("¿Voy a conseguir el trabajo?", True),
    ("¿Debo emprender solo o con un socio?", False), ("Vou conseguir o emprego?", True),
    ("kya meri shaadi is saal hogi?", True), ("Naukri milegi?", True),
    ("How about tomorrow", False)])
def test_is_yesno_question(q, yn):
    assert msg.is_yesno_question(q) is yn


def test_timezone_follows_the_whatsapp_number(m, monkeypatch):
    """WhatsApp sends no clock; the number is the live signal. Live bug: the chart
    said Bogotá while the person was messaging from US Eastern."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    def off(z):
        return int(datetime.now(ZoneInfo(z)).utcoffset().total_seconds() // 60)

    class Q:
        def __init__(self, row): self.row = row
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self): return type("R", (), {"data": [self.row]})()
    monkeypatch.setattr(m.supabase, "table",
                        lambda name: Q({"current_timezone": "America/Bogota", "current_country": "US"}))
    assert m._wa_user_tz_minutes("c1", "+14077825752") == off("America/New_York")   # 407 Orlando
    assert m._wa_user_tz_minutes("c1", "+13105551234") == off("America/Los_Angeles")
    assert m._wa_user_tz_minutes("c1", "+5592987654321") == off("America/Manaus")
    assert m._wa_user_tz_minutes(None, "+919812345678") == 330



# ─── travel ────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("I'm in London", ("city", "London")), ("im in new york now", ("city", "new york")),
    ("Estoy en Madrid", ("city", "Madrid")), ("main Delhi mein hoon", ("city", "Delhi")),
    ("I'm home", ("home", None)), ("back home", ("home", None)),
    ("I am in love", (None, None)), ("I'm in trouble", (None, None)),
    ("I'm in a meeting", (None, None)), ("I'm in a tough spot?", (None, None))])
def test_parse_travel(text, expected):
    assert msg.parse_travel(text) == expected


def test_resolve_tz_prefers_override_then_device_then_number(m, monkeypatch):
    monkeypatch.setattr(m, "_wa_number_tz", lambda cid, n: (-240, "America/New_York"))
    now = time.time()
    ov = {"tz_override": {"tz": "Asia/Kolkata", "label": "Delhi", "until": now + 3600}}
    assert m._wa_resolve_tz("c", "+14077825752", ov)[:2] == (330, "override")
    dev = {"device_tz": {"minutes": 60, "at": now - 3600}}
    assert m._wa_resolve_tz("c", "+14077825752", dev) == (60, "device", "UTC+1")
    stale = {"device_tz": {"minutes": 60, "at": now - 3 * 86400},
             "tz_override": {"tz": "Asia/Kolkata", "until": now - 1}}
    assert m._wa_resolve_tz("c", "+14077825752", stale)[:2] == (-240, "number")


def test_shared_location_sets_override(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)
    cv.run("", lat_lon=(28.61, 77.21))
    assert link["context"]["tz_override"]["tz"] == "Asia/Kolkata"
    assert "Kolkata time for the next 2 weeks" in cv.sent[-1] and cv.asked == []


def test_im_in_city_and_im_home(m, monkeypatch):
    link = _link()
    cv = _Conv(m, monkeypatch, link=link)

    async def geo(city, country):
        return (51.5, -0.12, "Europe/London", "test")
    monkeypatch.setattr(m, "_geocode_city", geo)
    cv.run("I'm in London")
    assert link["context"]["tz_override"]["tz"] == "Europe/London" and "London time" in cv.sent[-1]
    cv.run("I'm home")
    assert "tz_override" not in link["context"] and "home time again" in cv.sent[-1]
    assert cv.asked == []


def test_travel_note_when_device_clock_differs(m, monkeypatch):
    link = _link()
    link["context"] = {"device_tz": {"minutes": 60, "at": time.time()}}
    cv = _Conv(m, monkeypatch, link=link)
    monkeypatch.setattr(m, "_wa_resolve_tz", lambda cid, n, ctx=None: (60, "device", "UTC+1"))
    monkeypatch.setattr(m, "_wa_number_tz", lambda cid, n: (330, "Asia/Kolkata"))
    cv.run("How is my day today?")
    assert cv.asked[-1].tz_offset == 60
    assert "looks like you're travelling" in cv.sent[-1]
    cv.run("And tomorrow at work then later")
    assert "travelling" not in cv.sent[-1]            # once a week at most



def test_same_question_replays_the_original_prashna(m, monkeypatch):
    # one Prashna per DISTINCT question a day: re-asking replays the original cast
    from datetime import datetime, timezone
    cv = _Conv(m, monkeypatch, link=_link(), answer=dict(_YN_ANSWER, locked=True))
    from datetime import timedelta
    # tomorrow at noon in the sender's zone (+91 → UTC+5:30), whatever time it is now
    local_now = datetime.now(timezone.utc) + timedelta(minutes=330)
    unlock = (datetime.combine(local_now.date() + timedelta(days=1), datetime.min.time())
              + timedelta(hours=12) - timedelta(minutes=330)).replace(tzinfo=timezone.utc)
    monkeypatch.setattr(m, "_wa_prashna_lock", lambda cid, q="": unlock)
    cv.run("prashna: Will I raise funding by March?")
    assert cv.asked and cv.asked[-1].mode == "yesno" and cv.asked[-1].horary_number is None
    assert "number from 1 to 249" not in " ".join(cv.sent)
    out = cv.sent[-1]
    assert out.startswith("*→ Will I raise funding by March?*\n_Yes/No reading_\n\n_You asked this earlier — a yes-or-no reading is cast once per question a day")
    assert "tomorrow._" in out and "check back" not in out      # day always named; no new promise


def test_read_command_forces_a_regular_answer(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("read: will I raise funding by March?")
    assert cv.asked[-1].mode == "explore" and "Prashna ·" not in cv.sent[-1]


def test_prashna_same_question_matching(m):
    same = m._prashna_same_question
    assert same("Will I raise funding by March?", "will i raise funding by march")
    assert same("Will I raise funding by March?", "Will I raise the funding by March")
    assert not same("Will I raise funding by March?", "Will I get the job?")
    assert not same("Will I raise funding by March?", "Will I raise funding by December?")



def test_unlock_label_always_names_the_day(m):
    from datetime import datetime
    now = datetime(2026, 10, 2, 22, 34)
    assert m._wa_when_label(datetime(2026, 10, 3, 21, 25), now, "en") == "9:25 PM tomorrow"
    assert m._wa_when_label(datetime(2026, 10, 2, 23, 0), now, "en") == "11:00 PM"
    assert m._wa_when_label(datetime(2026, 10, 5, 9, 0), now, "en") == "Mon Oct 5, 9:00 AM"
    assert m._wa_when_label(datetime(2026, 10, 3, 21, 25), now, "pt") == "das 21:25 de amanhã"



def test_yesno_shows_the_specific_condition():
    p = {"mode": "yesno", "lean": "conditional", "why": "Funding can come, through the right route.",
         "timing": "Oct 3, 2026 – Jan 23, 2027", "verify_after": "2027-01-23",
         "condition": "It can come through people who already know your work, but only if you "
                      "steer clear of money with heavy strings attached.",
         "condition_label": "What it hinges on"}
    out, _ = msg.format_ask_whatsapp_v2(p, "en", compact=True)
    assert out.startswith("*Possible — on one condition.*")
    assert "*What it hinges on:* It can come through people who already know your work" in out


def test_saved_language_is_the_fallback_but_clear_text_wins(m, monkeypatch):
    # owner 2026-10-03: follow the chart's saved language; a message clearly in
    # another language is answered in that language.
    cv = _Conv(m, monkeypatch, link=_link())
    monkeypatch.setattr(m, "_wa_saved_lang", lambda cid: "es")
    cv.run("ok 2026")                                   # nothing to detect → saved
    assert cv.asked[-1].language == "es"
    cv.run("How will my money look doing defence deals with the government this year?")
    assert cv.asked[-1].language == "en"                # clearly English → English
    cv.run("meri shaadi kab hogi?")
    assert cv.asked[-1].language == "hinglish"


@pytest.mark.parametrize("pref,lang,want", [
    ("es", None, "es"), ("es-CO", None, "es"), ("pt_BR", None, "pt"), (None, "en", "en"),
    ("hinglish", None, "hinglish"), ("fr", None, None), (None, None, None)])
def test_saved_lang_normalizes(m, monkeypatch, pref, lang, want):
    class Q:
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self):
            return type("R", (), {"data": [{"language_preference": pref, "language": lang}]})()
    monkeypatch.setattr(m.supabase, "table", lambda name: Q())
    assert m._wa_saved_lang("c1") == want


@pytest.mark.parametrize("t", ["yes or no", "Yes/No", "sí o no", "Si o no.", "sim ou não",
                               "prashna", "*haan ya na*"])
def test_bare_yesno_reply_words(t):
    assert msg.is_bare_prashna(t)


@pytest.mark.parametrize("t", ["yes", "no", "sí", "Will I get the job yes or no?"])
def test_bare_yesno_reply_is_not_a_plain_yes(t):
    assert not msg.is_bare_prashna(t)


@pytest.mark.parametrize("t,q", [
    ("yes or no: will I get the job?", "will I get the job?"),
    ("Yes/No, will I raise funding by March?", "will I raise funding by March?"),
    ("sí o no: ¿voy a conseguir el trabajo?", "¿voy a conseguir el trabajo?"),
    ("Si o no voy a mudarme este año", "voy a mudarme este año"),
    ("sim ou não: vou conseguir o emprego?", "vou conseguir o emprego?"),
    ("haan ya na: naukri milegi?", "naukri milegi?"),
    ("prashna: will I move?", "will I move?")])
def test_yesno_prefix_commands(t, q):
    assert msg.parse_prashna_command(t) == q


@pytest.mark.parametrize("t", ["yes, I think so", "Is it yes or no for the job?", "no",
                               "sí, claro", "yes or no"])
def test_yesno_prefix_does_not_catch_ordinary_text(t):
    assert msg.parse_prashna_command(t) is None


def test_yesno_prefix_goes_straight_to_the_ritual(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link(), answer=dict(_YN_ANSWER))
    cv.run("yes or no: will I get the job?")
    assert cv.asked == [] and "number from 1 to 249" in cv.sent[-1]
    cv.run("12")
    assert cv.asked[-1].mode == "yesno" and cv.asked[-1].question == "will I get the job?"


def test_help_lists_the_yesno_prefix(m):
    assert "*yes or no:*" in m._wa_text("help", "en")
    assert "*sí o no:*" in m._wa_text("help", "es")
    assert "*sim ou não:*" in m._wa_text("help", "pt")


def test_speculation_never_gets_the_yesno_choice(m, monkeypatch):
    # live 2026-10-03: "Will I win in speculation?" → picked 1, then 13 → silently a
    # regular read (Ask diverts betting to explore). Now: straight to the full read.
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("Will I win in speculation?")
    assert cv.asked and cv.asked[-1].mode == "explore"
    assert "1  *Yes or no*" not in " ".join(cv.sent) and "1 to 249" not in " ".join(cv.sent)


def test_asking_yesno_on_betting_says_why(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("yes or no: will I win at the casino tonight?")
    assert cv.asked[-1].mode == "explore" and "1 to 249" not in " ".join(cv.sent)
    assert "aren't given for betting or speculation" in cv.sent[-1]


def test_unplaceable_question_gets_no_yesno_choice(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("Will it happen?")
    assert cv.asked and cv.asked[-1].mode == "explore" and "1  *Yes or no*" not in " ".join(cv.sent)


def test_forcing_yesno_on_an_unplaceable_question_says_why(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("yes or no: will it happen?")
    assert cv.asked[-1].mode == "explore" and "needs a clear area of life" in cv.sent[-1]



# ─── voice notes (owner 2026-10-03) ──────────────────────────────

def test_voice_note_is_transcribed_echoed_and_answered(m, monkeypatch):
    monkeypatch.setattr(msg, "voice_enabled", lambda: True)
    monkeypatch.setattr(msg, "transcribe_voice", lambda url, ct: ("How is my career looking this year", "en"))
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("", num_media=1, media=("https://api.twilio.com/x/Media/ME1", "audio/ogg; codecs=opus"))
    assert any("I heard:" in t and "career looking this year" in t for t in cv.sent)
    assert cv.asked and cv.asked[-1].question == "How is my career looking this year"


def test_spanish_voice_note_answers_in_spanish(m, monkeypatch):
    monkeypatch.setattr(msg, "voice_enabled", lambda: True)
    monkeypatch.setattr(msg, "transcribe_voice", lambda url, ct: ("¿Cómo va mi carrera este año?", "es"))
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("", num_media=1, media=("https://x/ME2", "audio/ogg"))
    assert any("Entendí:" in t for t in cv.sent) and cv.asked[-1].language == "es"


def test_unclear_voice_note_asks_again(m, monkeypatch):
    monkeypatch.setattr(msg, "voice_enabled", lambda: True)
    monkeypatch.setattr(msg, "transcribe_voice", lambda url, ct: ("", None))
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("", num_media=1, media=("https://x/ME3", "audio/ogg"))
    assert cv.asked == [] and "couldn't make out that voice note" in cv.sent[-1]


def test_voice_without_key_or_an_image_keeps_the_text_only_reply(m, monkeypatch):
    monkeypatch.setattr(msg, "voice_enabled", lambda: False)
    cv = _Conv(m, monkeypatch, link=_link())
    cv.run("", num_media=1, media=("https://x/ME4", "audio/ogg"))
    assert cv.asked == [] and "only read text" in cv.sent[-1]
    monkeypatch.setattr(msg, "voice_enabled", lambda: True)
    cv.run("", num_media=1, media=("https://x/ME5", "image/jpeg"))
    assert "only read text" in cv.sent[-1]


def test_voice_enabled_needs_the_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert not msg.voice_enabled()
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    monkeypatch.setenv("WHATSAPP_VOICE", "off")
    assert not msg.voice_enabled()


# ── [wa-consistent 2026-10-04] a fast (inline) answer looks like a slow one ───────
def test_inline_answer_goes_out_as_the_tappable_list_when_rest_is_known_good():
    import main
    items = [("Q1?", "q:Q1?", "Q1?")]
    s = main._WaSink("+10000000000", time.time(), inline=True)
    s.send_choices("body", "Ask next", items, "body\n\n1  Q1?", prefer_rest=True)
    assert s.buf == [] and s.outbox and s.outbox[0][0] == "list"
    s2 = main._WaSink("+10000000000", time.time(), inline=True)
    s2.send_choices("body", "Ask next", items, "body\n\n1  Q1?", prefer_rest=False)
    assert s2.buf == ["body\n\n1  Q1?"] and not s2.outbox


def test_failed_rest_list_rides_the_inline_reply(monkeypatch):
    import main
    from antar_engine import messaging as m
    monkeypatch.setattr(m, "whatsapp_send_list", lambda *a, **k: False)
    monkeypatch.setattr(m, "whatsapp_send", lambda *a, **k: False)
    s = main._WaSink("+10000000000", time.time(), inline=True)
    s.send_choices("body", "Ask next", [("Q?", "q:Q?", "Q?")], "numbered text", prefer_rest=True)
    failed, ok = s.flush()
    assert failed == [] and ok is False and s.buf == ["numbered text"]


# ── [wa-ui 2026-10-04] consistent look across every answer ───────────────────────
def test_hinglish_followups_are_hinglish_and_choice_bucket_exists():
    import main
    hi = main._ask_followups("business", "Mera business kaisa chalega?", "hinglish")
    assert hi and all(not q.startswith(("When ", "Where ", "Should ")) for q in hi)
    ch = main._ask_followups("choice", "Gold or defence?", "en")
    assert ch and not any("speculation" in q.lower() for q in ch)
    for lg in ("es", "pt", "hinglish"):
        assert main._ask_followups("choice", "x", lg)


def test_every_language_has_no_more_text_and_area_questions():
    import main
    for lg in ("en", "es", "pt", "hinglish"):
        assert main._wa_text("no_more", lg)
        assert len(main._WA_AREA_Q[lg]) == 3


# [wa-disclaimer 2026-10-05] the /ask payload's domain disclaimer must reach WhatsApp —
# the formatter ignored the field, so health/money/legal/fertility answers (incl. named
# Ayurvedic herbs) went out with no qualifier while the app card showed one.
_DZ = "An analysis of your planetary positions and timing — not a diagnosis, and not a guarantee. See a doctor about symptoms."


def _dz_payloads():
    explore = {"mode": "explore", "read": "Not yet — next health window Dec 2026 – Feb 2027. The timing shows a building phase. Recovery gets traction later.",
               "next": "Book a checkup this week. Traditionally, Ayurveda associates this period with brahmi — supportive practice, not treatment.",
               "timing": "Dec 2026 – Feb 2027", "disclaimer": _DZ,
               "practice_cta": {"available": True, "label": "A grounding minute", "step": "Breathe for a minute."},
               "suggested_questions": ["What should I watch for?", "When is the best week to start?"]}
    yesno = {"mode": "yesno", "verdict": "NO", "lean": "conditional", "locked": False,
             "why": "The route is your own body's strength, but the final yes isn't locked in.",
             "condition": "a clear commitment", "condition_label": "What it hinges on",
             "timing": "Oct 5 – Oct 6, 2026", "disclaimer": _DZ}
    return explore, yesno


@pytest.mark.parametrize("compact", [False, True])
def test_wa_v2_carries_the_disclaimer_in_every_mode(compact):
    from antar_engine import messaging as m
    for p in _dz_payloads():
        text, _ = m.format_ask_whatsapp_v2(p, "en", compact=compact)
        assert "not a diagnosis" in text and "See a doctor" in text
        assert text.count("not a diagnosis") == 1
        # italic, on its own line, and before the numbered follow-ups block
        assert f"_{_DZ}_" in text
        if "1  " in text:
            assert text.index("not a diagnosis") < text.index("\n1  ")


def test_wa_v2_without_a_disclaimer_is_unchanged():
    from antar_engine import messaging as m
    for p in _dz_payloads():
        q = dict(p); q.pop("disclaimer")
        text, _ = m.format_ask_whatsapp_v2(q, "en")
        assert "not a diagnosis" not in text and "planetary positions" not in text


def test_wa_legacy_formatter_carries_it_once():
    from antar_engine import messaging as m
    for p in _dz_payloads():
        assert m.format_ask_for_whatsapp(p, "en").count("not a diagnosis") == 1


def test_wa_disclaimer_survives_the_compact_budget():
    from antar_engine import messaging as m
    p = _dz_payloads()[0]
    p["read"] = " ".join(["The timing shows a long careful sentence about recovery and rest."] * 12)
    text, _ = m.format_ask_whatsapp_v2(p, "en", compact=True)
    assert "not a diagnosis" in text


# ── the data-processing gate, through a real conversation ──────────────────
# [wa-policy] _Conv stubs policy_state to "ok" so the other 150+ tests exercise
# what they are about. These pin the gate itself, so stubbing it elsewhere does
# not leave it uncovered.
def test_policy_prompt_comes_before_the_answer_and_nothing_is_asked(m, monkeypatch):
    cv = _Conv(m, monkeypatch, link=_link(), policy="needed")
    cv.run("When will I change jobs?")
    assert cv.asked == [], "no question may reach /ask before the policy is accepted"
    assert "privacy policy" in cv.sent[0].lower() and "terms" in cv.sent[0].lower()


def test_policy_prompt_comes_before_the_connect_message_for_an_unlinked_number(m, monkeypatch):
    monkeypatch.delenv("WHATSAPP_CONNECT_URL", raising=False)
    cv = _Conv(m, monkeypatch, link=None, policy="needed")
    cv.run("Will I get married?")
    assert cv.asked == []
    assert "privacy policy" in cv.sent[0].lower() and "terms" in cv.sent[0].lower()
    assert "Connect WhatsApp" not in cv.sent[0]


def test_declining_the_policy_ends_it_without_asking(m, monkeypatch):
    recorded = []
    monkeypatch.setattr(msg, "record_policy",
                        lambda sb, n, d, lang="en", link=None: recorded.append(d) or True)
    cv = _Conv(m, monkeypatch, link=_link(), policy="needed")
    cv.run("NO")
    assert recorded == ["no"]
    assert cv.asked == []


def test_accepting_the_policy_is_recorded(m, monkeypatch):
    recorded = []
    monkeypatch.setattr(msg, "record_policy",
                        lambda sb, n, d, lang="en", link=None: recorded.append(d) or True)
    cv = _Conv(m, monkeypatch, link=_link(), policy="needed")
    cv.run("ACCEPT")
    assert recorded == ["yes"]


def test_storage_not_set_up_fails_open_rather_than_locking_everyone_out(m, monkeypatch):
    """policy_state returns 'unknown' when wa_policy_acceptances is missing —
    the channel must keep working rather than refuse every message."""
    cv = _Conv(m, monkeypatch, link=_link(), policy="unknown")
    cv.run("When will I change jobs?")
    assert len(cv.asked) == 1


# [tg-disclaimer 2026-10-05] Telegram's renderer dropped the payload disclaimer too.
def test_telegram_carries_the_disclaimer_once_before_suggestions():
    from antar_engine import messaging as m
    for p in _dz_payloads():
        p = dict(p, suggested_questions=["What should I watch for?"])
        text = m.format_ask_for_telegram(p, "en")
        assert text.count("not a diagnosis") == 1
        assert "_An analysis" not in text          # plain text — no WhatsApp italics
        assert text.index("not a diagnosis") < text.index("You could also ask")


def test_telegram_without_a_disclaimer_is_unchanged():
    from antar_engine import messaging as m
    p = dict(_dz_payloads()[0]); p.pop("disclaimer")
    assert "planetary positions" not in m.format_ask_for_telegram(p, "en")


# ─── [wa-connect-by-country 2026-10-06] the connect link opens the right Antar number ───────

def test_link_start_picks_the_number_by_the_users_country(m, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("WA_SENDERS", '[{"number": "+19782131475", "label": "in-1", "countries": ["IN"]},'
                                     ' {"number": "+17322035001", "label": "us-1", "countries": ["US", "CA", "*"]}]')
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    monkeypatch.setattr(m, "_resolve_primary_chart_id", lambda uid: "chart-1")
    monkeypatch.setattr(msg, "create_pending_link",
                        lambda sb, cid, uid, ch, extra=None: {"available": True, "code": "abc12345", "channel": ch})
    c = TestClient(m.app)
    h = {"Authorization": "Bearer x"}
    r = c.post("/api/v1/messaging/link/start", json={"channel": "whatsapp", "country": "IN"}, headers=h).json()
    assert r["antar_number"] == "+19782131475" and r["deep_link"] == "https://wa.me/19782131475?text=LINK%20abc12345"
    assert r["qr_text"] == r["deep_link"]
    r = c.post("/api/v1/messaging/link/start", json={"channel": "whatsapp", "country": "CO"}, headers=h).json()
    assert r["antar_number"] == "+17322035001"


def test_country_falls_back_to_the_chart(m, monkeypatch):
    monkeypatch.setattr(m, "_wa_request_country", lambda req, hint=None: "")

    class _Q:
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self): return type("R", (), {"data": [{"current_country": "India", "birth_country": ""}]})()

    monkeypatch.setattr(m, "supabase", type("S", (), {"table": lambda self, t: _Q()})())
    assert m._wa_user_country(None, None, "chart-1") == "IN"
    assert m._wa_iso("Colombia") == "CO" and m._wa_iso("us") == "US" and m._wa_iso("Atlantis") == ""
