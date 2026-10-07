"""[wa-scan-login] code issue/approve/poll rules + the WhatsApp handler and endpoints (hermetic)."""
import asyncio
import time
from datetime import datetime, timedelta, timezone

from antar_engine import wa_login as wl


class _Res:
    def __init__(self, data):
        self.data = data


class _SB:
    """Tiny in-memory wa_login_codes with eq-filtered select/update/insert."""
    def __init__(self, missing=False):
        self.rows, self.missing = [], missing

    def table(self, name):
        return _Q(self)


class _Q:
    def __init__(self, db):
        self.db, self.op, self.f, self.payload = db, "select", {}, None

    def select(self, *_):
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, row):
        self.op, self.payload = "update", row
        return self

    def eq(self, k, v):
        self.f[k] = v
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self.db.missing:
            raise RuntimeError("Could not find the table 'public.wa_login_codes' in the schema cache")
        hit = [r for r in self.db.rows if all(r.get(k) == v for k, v in self.f.items())]
        if self.op == "insert":
            self.db.rows.append(dict(self.payload))
            return _Res([self.payload])
        if self.op == "update":
            for r in hit:
                r.update(self.payload)
            return _Res(hit)
        return _Res(hit)


def test_parse_login():
    assert wl.parse_login("Hi Antar! Sign me in: k7q2mx") == "K7Q2MX"
    assert wl.parse_login("login K7Q2MX") == "K7Q2MX"
    assert wl.parse_login("Hola Antar! iniciar sesión: K7Q2MX") == "K7Q2MX"
    assert wl.parse_login("will I login to my job soon?") is None
    assert wl.parse_login("Hi Antar! Connect my account: K7Q2MX") is None


def test_happy_path_and_one_use():
    sb = _SB()
    out = wl.issue(sb)
    assert wl.poll(sb, out["code"], out["browser_token"]) == {"status": "pending"}
    assert wl.approve(sb, out["code"], "+15551234567", "user-1")
    r = wl.poll(sb, out["code"], out["browser_token"])
    assert r == {"status": "approved", "user_id": "user-1"}
    assert wl.poll(sb, out["code"], out["browser_token"]) == {"status": "expired"}   # consumed


def test_wrong_browser_token_cannot_redeem():
    sb = _SB()
    out = wl.issue(sb)
    wl.approve(sb, out["code"], "+1555", "user-1")
    assert wl.poll(sb, out["code"], "someone-elses-token") == {"status": "expired"}
    assert wl.poll(sb, out["code"], out["browser_token"])["status"] == "approved"   # still redeemable by owner


def test_expired_code_cannot_be_approved_or_polled():
    sb = _SB()
    out = wl.issue(sb)
    sb.rows[0]["created_at"] = (datetime.now(timezone.utc) - timedelta(seconds=wl.TTL_S + 5)).isoformat()
    assert wl.approve(sb, out["code"], "+1555", "user-1") is False
    assert wl.poll(sb, out["code"], out["browser_token"]) == {"status": "expired"}


def test_cannot_approve_twice():
    sb = _SB()
    out = wl.issue(sb)
    assert wl.approve(sb, out["code"], "+1555", "user-1")
    assert wl.approve(sb, out["code"], "+1999", "attacker") is False
    assert sb.rows[0]["user_id"] == "user-1"


def test_missing_table_is_unavailable_not_a_crash():
    sb = _SB(missing=True)
    assert wl.issue(sb) is None
    assert wl.approve(sb, "ABCDEF", "+1", "u") is False
    assert wl.poll(sb, "ABCDEF", "t") == {"status": "expired"}


def test_every_text_has_all_languages():
    for k, v in wl.T.items():
        assert set(v) == {"en", "es", "pt", "hinglish"}, k


# ── through the real handler / endpoints ──────────────────────────────────────

def _handler(monkeypatch, link, sb):
    import main
    from tests.test_whatsapp_channel import _Conv
    conv = _Conv(main, monkeypatch, link=link)
    monkeypatch.setattr(main, "supabase", sb)
    return main, conv


def test_linked_number_tapping_send_approves_the_browser(monkeypatch):
    sb = _SB()
    out = wl.issue(sb)
    main, conv = _handler(monkeypatch, {"id": "L1", "chart_id": "c1", "user_id": "user-1", "context": {}}, sb)
    conv.run(wl.sign_in_text(out["code"]))
    assert "Signed in" in conv.sent[-1] and not conv.asked        # never answered as an Ask question
    assert sb.rows[0]["status"] == "approved" and sb.rows[0]["user_id"] == "user-1"


def test_unknown_number_gets_no_account_and_code_stays_pending(monkeypatch):
    sb = _SB()
    out = wl.issue(sb)
    main, conv = _handler(monkeypatch, None, sb)
    conv.run(wl.sign_in_text(out["code"]))
    assert "don't have an account" in conv.sent[-1]
    assert sb.rows[0]["status"] == "pending"


def test_stale_code_in_chat_says_so(monkeypatch):
    sb = _SB()
    main, conv = _handler(monkeypatch, {"id": "L1", "chart_id": "c1", "user_id": "user-1", "context": {}}, sb)
    conv.run("Hi Antar! Sign me in: ZZZZZZ")
    assert "isn't valid" in conv.sent[-1]


def test_endpoints_start_then_poll_mints_a_session(monkeypatch):
    import main
    sb = _SB()
    monkeypatch.setattr(main, "supabase", sb)
    monkeypatch.setenv("WHATSAPP_ENABLED", "true")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "+17322035001")
    main._WA_LOGIN_RATE.clear()

    class _Req:
        headers = {"x-forwarded-for": "1.2.3.4"}
        client = None
    start = main.auth_whatsapp_start(_Req(), "US")
    assert start["deep_link"].startswith("https://wa.me/") and start["code"] in start["prefilled_text"]
    assert main.auth_whatsapp_poll(main._WaLoginPoll(code=start["code"], browser_token=start["browser_token"])) \
        == {"status": "pending"}
    wl.approve(sb, start["code"], "+15551234567", "user-1")

    class _Admin:
        def get_user_by_id(self, uid):
            return type("U", (), {"user": type("X", (), {"email": "wa1555@wa.antar.world"})()})()

        def generate_link(self, p):
            assert p["type"] == "magiclink" and p["email"] == "wa1555@wa.antar.world"
            return type("L", (), {"properties": type("P", (), {"hashed_token": "HASH123"})()})()
    sb.auth = type("A", (), {"admin": _Admin()})()
    got = main.auth_whatsapp_poll(main._WaLoginPoll(code=start["code"], browser_token=start["browser_token"]))
    assert got == {"status": "approved", "token_hash": "HASH123", "type": "magiclink"}
    again = main.auth_whatsapp_poll(main._WaLoginPoll(code=start["code"], browser_token=start["browser_token"]))
    assert again == {"status": "expired"}


def test_start_is_rate_limited_and_off_when_disabled(monkeypatch):
    import main
    from fastapi import HTTPException
    sb = _SB()
    monkeypatch.setattr(main, "supabase", sb)
    main._WA_LOGIN_RATE.clear()

    class _Req:
        headers = {"x-forwarded-for": "9.9.9.9"}
        client = None
    monkeypatch.delenv("WHATSAPP_ENABLED", raising=False)
    try:
        main.auth_whatsapp_start(_Req(), None)
        assert False
    except HTTPException as e:
        assert e.status_code == 503
    monkeypatch.setenv("WHATSAPP_ENABLED", "true")
    for _ in range(10):
        main.auth_whatsapp_start(_Req(), None)
    try:
        main.auth_whatsapp_start(_Req(), None)
        assert False
    except HTTPException as e:
        assert e.status_code == 429
