"""Training export: consent gate, no retroactive data, scrubbing, pseudonymity."""
import importlib.util
import os

from antar_engine import messaging as msg
from antar_engine.wa_scrub import scrub

_spec = importlib.util.spec_from_file_location(
    "export_wa_training", os.path.join(os.path.dirname(__file__), "..", "scripts", "export_wa_training.py"))
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

OK = {"status": "linked", "chart_id": "chart-uuid-1234", "training_opt_in": True,
      "training_opt_in_at": "2026-10-06T10:00:00+00:00",
      "training_consent_version": msg.WA_TRAINING_CONSENT_VERSION}


def row(t, body="hello", d="in", kind="text", **k):
    return {"created_at": f"2026-10-06T{t}+00:00", "direction": d, "body": body, "kind": kind, "country": "IN", **k}


def test_consent_gate():
    assert msg.can_train(OK)
    for bad in ({"training_opt_in": False}, {"training_consent_version": "old"}, {"status": "revoked"}):
        assert not msg.can_train({**OK, **bad})
    assert not msg.can_train(None)
    assert msg.training_row(False)["training_consent_version"] is None


def test_not_retroactive_and_kinds():
    assert not ex.eligible(row("09:59:00"), OK)          # before consent
    assert ex.eligible(row("10:00:00"), OK)
    assert not ex.eligible(row("11:00:00", kind="template"), OK)
    assert not ex.eligible(row("11:00:00", kind="media"), OK)
    assert not ex.eligible(row("11:00:00"), {**OK, "training_opt_in": False})


def test_scrub():
    t = scrub("Mail me at a.b@x.com or +91 98123 45678, born 14/03/1987, see https://x.io. Priya asks", ["Priya"])
    for leak in ("a.b@x.com", "98123", "1987", "https://", "Priya"):
        assert leak not in t
    assert "[EMAIL]" in t and "[PHONE]" in t and "[DATE]" in t and "[NAME]" in t
    assert scrub("Your money window opens on 14 Oct 2026") == "Your money window opens on 14 Oct 2026"


def test_conversations_split_and_pseudonym():
    rows = [row("10:05:00", "hi"), row("10:06:00", "answer", d="out"), row("20:00:00", "later")]
    cs = ex.conversations(rows, OK, [], "k")
    assert [len(c["messages"]) for c in cs] == [2, 1]
    assert cs[0]["messages"][1]["role"] == "assistant"
    assert "chart-uuid" not in str(cs) and cs[0]["person"] == ex.pseudonym("chart-uuid-1234", "k")


def test_stop_training_is_its_own_command_not_unlink():
    for t in ("STOP TRAINING", "stop training.", "Parar entrenamiento", "parar treinamento"):
        assert msg.parse_wa_command(t) == ("training_off", "")
    assert msg.parse_wa_command("stop") == ("unlink", "")           # plain STOP still disconnects
    assert msg.parse_wa_command("how is training for a marathon") == ("", "")


def test_training_texts_exist_in_every_language():
    import re
    src = open(os.path.join(os.path.dirname(__file__), "..", "main.py")).read()
    for key in ("optin_training", "training_on", "training_off"):
        block = src[src.index(f'"{key}": {{') if f'"{key}": {{' in src else src.index(f'"{key}":'):][:2500]
        for lang in ("en", "es", "pt", "hinglish"):
            assert f'"{lang}":' in block, (key, lang)
