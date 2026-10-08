"""WhatsApp users who hide their phone number reach us as a user ID ("CO.113…"), not "+57…". Both must connect and chat."""
import sys

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_whatsapp_channel import _signed, m  # noqa: E402,F401  (the module's own webhook fixtures)
from circle_fakedb import DB  # noqa: E402

from antar_engine import messaging as msg
from antar_engine import wa_log, wa_numbers

BSUID = "CO.1130884559869035369"
HDR = lambda sig: {"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig}


def test_wa_number_keeps_both_kinds_of_identity():
    assert msg.wa_number("whatsapp:+919812345678") == "+919812345678"
    assert msg.wa_number("whatsapp:" + BSUID) == BSUID
    assert msg.wa_number("whatsapp:co.1130884559869035369") == BSUID           # prefix upper-cased, id untouched
    assert msg.wa_number("US.ABCdef1234567890") == "US.ABCdef1234567890"
    for bad in ("", None, "whatsapp:", "whatsapp:12", "hello", "C.123456", "COL.123456", "CO.12"):
        assert msg.wa_number(bad) == "", bad
    assert msg.is_bsuid(BSUID) and not msg.is_bsuid("+573112578335") and not msg.is_bsuid(None)


def test_country_and_log_identity_for_a_user_id():
    assert wa_numbers.country_of(BSUID) == "CO" and wa_numbers.country_of("IN.99999999999") == "IN"
    assert wa_numbers.country_of("+573112578335") == "CO" and wa_numbers.country_of("+14155550123") == "US"
    assert wa_log._digits_number("whatsapp:" + BSUID) == BSUID
    assert wa_log._digits_number("whatsapp:+57 311 257 8335") == "+573112578335"
    assert wa_numbers.sender_for(BSUID, {}, "") == wa_numbers.sender_for(BSUID, {}, "")      # stable routing, no crash


def test_the_webhook_hands_a_user_id_message_to_the_handler(m, monkeypatch):
    from fastapi.testclient import TestClient
    handled = []

    async def fake_handle(number, body, ts, num_media=0, sink=None, sid="", choice="", lat_lon=None, media=None):
        handled.append((number, body))
    monkeypatch.setattr(m, "_wa_handle", fake_handle)
    raw, sig = _signed({"MessageSid": "SMb1", "From": "whatsapp:" + BSUID, "Body": "Hi Antar! Connect my account: BDVGJZ", "NumMedia": "0"})
    r = TestClient(m.app).post("/api/v1/messaging/whatsapp/webhook", content=raw, headers=HDR(sig))
    assert r.status_code == 200 and handled == [(BSUID, "Hi Antar! Connect my account: BDVGJZ")]


def test_help_is_answered_to_a_user_id_too(m, monkeypatch):
    from fastapi.testclient import TestClient
    raw, sig = _signed({"MessageSid": "SMb2", "From": "whatsapp:" + BSUID, "Body": "help", "NumMedia": "0"})
    r = TestClient(m.app).post("/api/v1/messaging/whatsapp/webhook", content=raw, headers=HDR(sig))
    assert r.status_code == 200 and r.text.startswith("<Response><Message>")


def test_an_unattributable_message_is_logged_not_silently_dropped(m, capsys):
    from fastapi.testclient import TestClient
    raw, sig = _signed({"MessageSid": "SMb3", "From": "whatsapp:??", "Body": "hello", "NumMedia": "0"})
    r = TestClient(m.app).post("/api/v1/messaging/whatsapp/webhook", content=raw, headers=HDR(sig))
    assert r.status_code == 200 and r.text == "<Response></Response>"
    assert "dropped a message with an unusable From" in capsys.readouterr().out
    raw2, sig2 = _signed({"MessageSid": "SMb4", "From": "whatsapp:+919812345678", "Body": "", "NumMedia": "0"})   # a true status ping
    TestClient(m.app).post("/api/v1/messaging/whatsapp/webhook", content=raw2, headers=HDR(sig2))
    assert "dropped a message" not in capsys.readouterr().out


def test_a_pending_code_binds_to_a_user_id_and_to_a_phone_number():
    for ident in (BSUID, "+573112578335"):
        db = DB()
        db.t["messaging_links"] = [{"id": "L1", "chart_id": "chart-1", "user_id": "u1", "channel": "whatsapp", "status": "pending",
                                    "link_code": "BDVGJZ", "channel_user_id": None, "consent_at": "2026-10-08T00:00:00+00:00",
                                    "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}]
        assert msg.bind_link_whatsapp(db, "BDVGJZ", msg.wa_number("whatsapp:" + ident)) == "chart-1"
        row = db.rows("messaging_links")[0]
        assert row["status"] == "linked" and row["channel_user_id"] == ident and row["link_code"] is None
