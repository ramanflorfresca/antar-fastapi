"""[wa-numbers] sender pool: deterministic per-country dedication, stickiness, safe defaults."""
import json
import time

import pytest

from antar_engine import wa_numbers as wn, messaging as msg

POOL = [
    {"number": "+14155550101", "label": "in-1", "countries": ["IN"], "langs": ["hinglish", "en"]},
    {"number": "+14155550102", "label": "in-2", "countries": ["IN"]},
    {"number": "+14155550103", "label": "co-1", "countries": ["CO", "AR"], "langs": ["es"]},
    {"number": "+14155550104", "label": "us-1", "countries": ["US", "CA"]},
    {"number": "+14155550105", "label": "us-2", "countries": ["US"]},
    {"number": "+14155550199", "label": "world", "countries": ["*"]},
]


@pytest.fixture()
def pool(monkeypatch):
    monkeypatch.setenv("WA_SENDERS", json.dumps(POOL))
    monkeypatch.delenv("TWILIO_WHATSAPP_FROM", raising=False)


@pytest.mark.parametrize("number,iso", [
    ("+919812345678", "IN"), ("whatsapp:+573001234567", "CO"), ("+5491155551234", "AR"),
    ("+14155550123", "US"), ("+16135550123", "CA"), ("+525512345678", "MX"), ("+5511999999999", "BR"),
    ("+442071234567", "GB"), ("", "")])
def test_country_from_number(number, iso):
    assert wn.country_of(number) == iso


def test_each_country_only_ever_gets_its_own_numbers(pool):
    for i in range(200):
        assert wn.assign(f"+9198{i:08d}") in ("+14155550101", "+14155550102")
        assert wn.assign(f"+5730{i:08d}") == "+14155550103"
        assert wn.assign(f"+141655{i:05d}") in ("+14155550105", "+14155550104")


def test_assignment_is_deterministic_and_spread(pool):
    nums = [f"+9198{i:08d}" for i in range(400)]
    first = [wn.assign(n) for n in nums]
    assert first == [wn.assign(n) for n in nums]
    assert 120 < first.count("+14155550101") < 280               # both Indian numbers carry real load


def test_country_without_numbers_falls_to_language_neighbour_then_world(pool):
    assert wn.assign("+56912345678") == "+14155550103"           # Chile → Spanish-serving number
    assert wn.assign("+819012345678") == "+14155550199"          # Japan → world


def test_language_only_narrows_never_blocks(pool):
    assert wn.assign("+919800000001", lang="hinglish") == "+14155550101"
    assert wn.assign("+919800000001", lang="pt") in ("+14155550101", "+14155550102")


def test_paused_sender_gets_no_new_users_but_keeps_existing(pool, monkeypatch):
    p = [dict(x) for x in POOL]
    p[0]["paused"] = True
    monkeypatch.setenv("WA_SENDERS", json.dumps(p))
    assert all(wn.assign(f"+9198{i:08d}") == "+14155550102" for i in range(50))
    assert wn.sender_for("+919800000001", {"sender": "+14155550101"}) == "+14155550101"


def test_the_number_they_wrote_to_wins_unless_it_left_the_pool(pool):
    n = "+919800000001"
    assert wn.sender_for(n, {"sender": "+14155550102"}) == "+14155550102"
    assert wn.sender_for(n, {"sender": "+19999999999"}) == wn.assign(n)


def test_no_pool_means_todays_single_sender(monkeypatch):
    monkeypatch.delenv("WA_SENDERS", raising=False)
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    assert wn.assign("+919800000001") == "+14155238886"
    assert wn.effective_sender() == "+14155238886"
    monkeypatch.setenv("WA_SENDERS", "not json")
    assert wn.assign("+919800000001") == "+14155238886"


def test_send_uses_the_context_sender(pool, monkeypatch):
    import urllib.parse
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC1")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "t")
    seen = []
    monkeypatch.setattr(msg.urllib.request, "urlopen", lambda r, **k: seen.append(r))
    wn.use("whatsapp:+14155550103")
    assert msg.whatsapp_send("+573001234567", "hola", time.time())
    assert urllib.parse.parse_qs(seen[0].data.decode())["From"] == ["whatsapp:+14155550103"]
    wn.use("+19999999999")                                        # not ours → never used
    assert wn.effective_sender() != "+19999999999"
    wn.use("")


def test_connect_token_carries_the_sender():
    tok = msg.make_connect_token("s", "+919812345678", sender="whatsapp:+14155550101")
    assert msg.read_connect_token_full("s", tok) == {"number": "+919812345678", "sender": "+14155550101"}
    assert msg.read_connect_token("s", tok) == "+919812345678"
    old = msg.make_connect_token("s", "+919812345678")
    assert msg.read_connect_token_full("s", old)["sender"] == ""


def test_deep_link_number_spreads_by_account_and_follows_country(pool):
    got = {wn.deep_link_number("IN", key=f"user-{i}") for i in range(60)}
    assert got == {"+14155550101", "+14155550102"}
    assert wn.deep_link_number("CO", key="u") == "+14155550103"
