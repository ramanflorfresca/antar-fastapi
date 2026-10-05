"""[wa-marketing 2026-10-05] Offers / news on WhatsApp: a separate, optional, default-off opt-in."""
from antar_engine import messaging as msg
from antar_engine import wa_templates as wt


class _Q:
    def __init__(self, db):
        self.db, self.op, self.row = db, None, None

    def insert(self, row):
        self.op, self.row = "insert", row
        return self

    def execute(self):
        if self.db.get("reject") and any(k in self.row for k in msg.OPTIONAL_LINK_COLS):
            raise RuntimeError("column \"marketing_opt_in\" does not exist")
        self.db.setdefault("rows", []).append(dict(self.row))
        return type("R", (), {"data": [self.row]})()


class FakeSB:
    def __init__(self, reject=False):
        self.db = {"reject": reject}

    def table(self, _name):
        return _Q(self.db)


def test_marketing_is_off_unless_ticked_and_records_the_wording():
    off = msg.marketing_row(False)
    assert off == {"marketing_opt_in": False, "marketing_opt_in_at": None, "marketing_consent_version": None}
    on = msg.marketing_row(True)
    assert on["marketing_opt_in"] is True and on["marketing_opt_in_at"]
    assert on["marketing_consent_version"] == msg.WA_MARKETING_CONSENT_VERSION


def test_can_send_marketing_needs_link_opt_in_and_current_wording():
    base = {"status": "linked", "marketing_opt_in": True,
            "marketing_consent_version": msg.WA_MARKETING_CONSENT_VERSION}
    assert msg.can_send_marketing(base)
    assert not msg.can_send_marketing(dict(base, marketing_opt_in=False))
    assert not msg.can_send_marketing(dict(base, marketing_consent_version="old"))
    assert not msg.can_send_marketing(dict(base, status="revoked"))
    assert not msg.can_send_marketing(None)


def test_linking_never_fails_when_the_optional_columns_are_missing():
    sb = FakeSB(reject=True)
    extra = msg.consent_row("app")
    extra.update(msg.marketing_row(True))
    out = msg.create_pending_link(sb, "chart-1", "user-1", "whatsapp", extra)
    assert out["available"] is True
    row = sb.db["rows"][0]
    assert "marketing_opt_in" not in row and row["consent_version"] == msg.WA_CONSENT_VERSION


def test_stop_offers_command_in_four_languages():
    for t in ("stop offers", "STOP PROMOS", "parar ofertas", "sem ofertas", "offers band"):
        assert msg.parse_wa_command(t) == ("marketing_off", "")
    assert msg.parse_wa_command("STOP") == ("unlink", "")
    assert msg.parse_wa_command("stop alerts") == ("alerts_off", "")


def test_marketing_template_is_blocked_without_opt_in(monkeypatch):
    monkeypatch.setitem(wt.TEMPLATES, "promo_test", {"category": "MARKETING", "variables": {}, "body": {},
                                                     "buttons": {}})
    assert wt.send("+15550000000", "promo_test", "en", {}, link={"status": "linked"}) is False
    assert wt.send("+15550000000", "promo_test", "en", {}, link=None) is False
