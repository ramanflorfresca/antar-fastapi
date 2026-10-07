"""[wa-one-card] status → one card state, and the Open chat link."""
from antar_engine import messaging as msg


def test_card_state():
    assert msg.card_state({"available": False, "linked": True}) == "unavailable"
    assert msg.card_state({"available": True, "linked": False}) == "not_connected"
    assert msg.card_state({"available": True, "linked": True}) == "connected"
    assert msg.card_state({}) == "unavailable"


def test_open_chat_link():
    assert msg.open_chat_link("+17322035001") == "https://wa.me/17322035001"
    assert msg.open_chat_link("+1 (978) 213-1475") == "https://wa.me/19782131475"
    assert msg.open_chat_link("") is None and msg.open_chat_link(None) is None


def test_status_endpoint_returns_state_and_link(monkeypatch):
    import main
    monkeypatch.setattr(main, "verify_token", lambda a: "u1")
    monkeypatch.setattr(main, "_wa_on", lambda: True)
    monkeypatch.setattr(main, "_wa_chart_name", lambda cid: "Raman")
    monkeypatch.setattr(msg, "whatsapp_status", lambda sb, uid: {"linked": True, "number_last4": "4821",
                                                                  "chart_id": "c1"})
    monkeypatch.setattr(msg, "prompt_state", lambda sb, uid: {"tracked": True, "shown_at": "x"})
    monkeypatch.setattr(main, "_wa_request_country", lambda r, c: "US")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "+17322035001")

    class _Q:
        def __getattr__(self, n):
            return lambda *a, **k: self
        def execute(self):
            return type("R", (), {"data": []})()
    monkeypatch.setattr(main, "supabase", type("S", (), {"table": lambda s, n: _Q()})())
    out = main.messaging_whatsapp_status(object(), "US", "Bearer x")
    assert out["state"] == "connected" and out["chart_name"] == "Raman"
    assert out["open_chat_link"].startswith("https://wa.me/") and out["antar_number"].startswith("+")
