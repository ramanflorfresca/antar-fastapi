"""[wa-offers-news 2026-10-05] The messages behind the "Offers & news" switch.

Hard rules pinned here: MARKETING stays MARKETING (never dressed as UTILITY), the opt-out is IN the
body, Meta's variable placement rules hold in all four languages, no price/discount/buy wording can
reach WhatsApp (owner rule), and nothing sends to someone who has not opted in."""
import re

import pytest

from antar_engine import messaging as m
from antar_engine import wa_templates as w

NAMES = ("antar_news_v1", "antar_offer_v1")
LANGS = w.LANGS


@pytest.mark.parametrize("name", NAMES)
def test_marketing_templates_are_marketing_with_all_four_languages(name):
    t = w.TEMPLATES[name]
    assert t["category"] == "MARKETING"
    for lang in LANGS:
        assert t["body"][lang].strip(), (name, lang)
        assert 1 <= len(t["buttons"][lang]) <= 3
        for title, bid in t["buttons"][lang]:
            assert len(title) <= 20, (name, lang, title)            # Meta quick-reply limit
        ids = [b for _, b in t["buttons"][lang]]
        assert ids == ["own", "mkt_stop"], ids                      # Ask Antar + Stop offers


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("lang", LANGS)
def test_meta_variable_rules_and_opt_out_in_every_body(name, lang):
    body = w.TEMPLATES[name]["body"][lang]
    assert not re.match(r"\s*\{\{", body) and not re.search(r"\}\}\s*[.!?]?\s*$", body)   # not first/last
    assert not re.search(r"\}\}\s*\{\{", body)                                              # not adjacent
    assert sorted(re.findall(r"\{\{(\d)\}\}", body)) == sorted(w.TEMPLATES[name]["variables"])
    assert re.search(r"(?i)STOP OFFERS|PARAR OFERTAS", body), "the opt-out must be in the message"
    assert not re.search(r"[\U0001F300-\U0001FAFF]", body), "no emoji in a marketing template"


def test_every_news_item_is_complete_and_passes_the_no_prices_rule():
    assert set(w.NEWS_ITEMS) >= {"decisions", "daily_wisdom", "people_timing", "places"}
    for key, entry in w.NEWS_ITEMS.items():
        for lang in LANGS:
            head, line = entry[lang]
            assert head and line and w.marketing_text_ok(head) and w.marketing_text_ok(line), (key, lang)
            built = w.build_marketing("news", "Harleen Kaur", lang, item=key)
            assert built and built[0] == "antar_news_v1" and built[1]["1"] == "Harleen"
            assert "\n" not in built[1]["2"] + built[1]["3"]


@pytest.mark.parametrize("bad", [
    "20% off for a month", "only $9 this week", "₹499 for the year", "a discount on your plan",
    "buy more questions", "upgrade today", "limited time only", "descuento del 20", "preço especial",
    "premium access", "use code SAVE10 at checkout",
])
def test_price_and_pressure_wording_never_reaches_whatsapp(bad):
    assert not w.marketing_text_ok(bad)
    assert w.build_marketing("offer", "Harleen", "en", offer=bad, until="Oct 31") is None


@pytest.mark.parametrize("good", [
    "an extra week of daily alerts", "early access to the new Places view",
    "a real answer on your own timing", "una semana extra de alertas diarias",
])
def test_plain_non_monetary_offers_pass(good):
    out = w.build_marketing("offer", "Harleen", "en", offer=good + ".", until="Oct 31")
    assert out == ("antar_offer_v1", {"1": "Harleen", "2": good, "3": "Oct 31"})


def test_build_refuses_incomplete_or_unknown_input():
    assert w.build_marketing("offer", "H", "en", offer="", until="Oct 31") is None
    assert w.build_marketing("offer", "H", "en", offer="an extra week", until="") is None
    assert w.build_marketing("news", "H", "en", item="not-shipped-yet") is None
    assert w.build_marketing("blast", "H", "en") is None


def test_nothing_sends_without_an_offers_opt_in(monkeypatch):
    calls = []
    monkeypatch.setattr(w, "template_sid", lambda *a, **k: "HXtest")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACx")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "+10000000000")
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: calls.append(a))

    base = {"status": "linked", "display_name": "Harleen"}
    no_optin = dict(base, marketing_opt_in=False)
    old_wording = dict(base, marketing_opt_in=True, marketing_consent_version="wa-mkt-OLD")
    assert not m.can_send_marketing(no_optin) and not m.can_send_marketing(old_wording)
    for link in (None, {}, no_optin, old_wording):
        assert w.send_marketing(link, "+15551234567", "news", "en", item="decisions") is False
    assert calls == []                                              # no HTTP call was even attempted


def test_opted_in_link_passes_the_gate(monkeypatch):
    ok = {"status": "linked", "display_name": "Harleen", "marketing_opt_in": True,
          "marketing_consent_version": m.WA_MARKETING_CONSENT_VERSION}
    assert m.can_send_marketing(ok)
    sent = {}
    monkeypatch.setattr(w, "send", lambda to, name, lang, vars_, link=None: sent.update(
        to=to, name=name, vars=vars_) or True)
    assert w.send_marketing(ok, "+15551234567", "news", "es", item="places") is True
    assert sent["name"] == "antar_news_v1" and sent["vars"]["1"] == "Harleen"


def test_stop_offers_button_is_handled_like_the_typed_command():
    src = open("main.py", encoding="utf-8").read()
    assert 'cmd == "marketing_off" or choice_id == "mkt_stop"' in src
    assert m.parse_wa_command("stop offers")[0] == "marketing_off"
    assert m.parse_wa_command("parar ofertas")[0] == "marketing_off"
