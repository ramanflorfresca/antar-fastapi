"""WhatsApp templates + user guide (owner 2026-10-03: retention first)."""
import re
import pytest
from antar_engine import wa_templates as wt, messaging as msg


@pytest.mark.parametrize("name", list(wt.TEMPLATES))
@pytest.mark.parametrize("lang", ["en", "es", "pt_BR"])
def test_templates_follow_meta_utility_rules(name, lang):
    t = wt.TEMPLATES[name]
    body = t["body"][lang]
    assert t["category"] == "UTILITY" and len(body) <= 1024
    assert not body.lstrip().startswith("{{") and not body.rstrip(" .!?").endswith("}}")
    assert not re.search(r"\}\}\s*\{\{", body)                       # no adjacent variables
    used = set(re.findall(r"\{\{(\d+)\}\}", body))
    assert used == set(t["variables"]), (name, lang)
    for title, _id in t["buttons"][lang]:
        assert len(title) <= 20, title
    for w in ("upgrade", "price", "offer", "discount", "free", "$", "₹", "gratis", "grátis"):
        assert w not in body.lower(), (name, w)                     # never promotional


def test_checkin_buttons_are_the_typed_numbers():
    for lang in ("en", "es", "pt_BR"):
        assert [b for _, b in wt.TEMPLATES["antar_checkin_v1"]["buttons"][lang]] == ["1", "2", "3", "4"]


def test_lang_mapping_and_env_key(monkeypatch):
    assert wt.wa_lang("hinglish") == "en" and wt.wa_lang("pt") == "pt_BR" and wt.wa_lang("es") == "es"
    assert wt.env_key("antar_checkin_v1", "es") == "WA_TPL_ANTAR_CHECKIN_V1_ES"
    monkeypatch.delenv("WA_TPL_ANTAR_CHECKIN_V1_EN", raising=False)
    assert wt.template_sid("antar_checkin_v1", "en") is None
    assert wt.send("+14075550123", "antar_checkin_v1", "en", {"1": "a"}) is False   # not approved → no send


def test_content_payload_shape():
    p = wt.content_payload("antar_window_alert_v1", "es")
    qr = p["types"]["twilio/quick-reply"]
    assert p["language"] == "es" and qr["actions"][1]["id"] == "alert_stop"
    assert p["types"]["twilio/text"]["body"] == qr["body"]


def test_template_vars_quote_only_safe_claims():
    from antar_engine.outcomes import template_vars
    c = {"source": "ask_explore", "topic": "career", "text_shown": "A new client signs before January.",
         "created_at": "2026-10-02T12:00:00", "language": "en"}
    assert template_vars(c, "Harleen") == {"1": "Harleen", "2": "Oct 2", "3": "A new client signs before January"}
    assert template_vars(dict(c, topic="health"), "H") is None
    assert template_vars(dict(c, text_shown=""), "H") is None


@pytest.mark.parametrize("t,cmd", [("tips", "tips"), ("Consejos", "tips"), ("dicas", "tips"),
                                   ("stop alerts", "alerts_off"), ("parar alertas", "alerts_off")])
def test_commands(t, cmd):
    assert msg.parse_wa_command(t)[0] == cmd


def test_tips_cover_the_never_send_list():
    from dotenv import load_dotenv
    load_dotenv()
    import main
    for lang in ("en", "es", "pt", "hinglish"):
        t = main._wa_text("tips", lang)
        assert "OTP" in t and "STOP" in t
    for lang in ("en", "es", "pt", "hinglish"):
        h = main._wa_text("help", lang)
        assert "*tips*" in h or "*dicas*" in h, lang
