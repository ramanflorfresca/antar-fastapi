"""The chakra reason sentence must end on the same verdict the map shows (3-state status)."""
import re

import pytest

from antar_engine import practice_chakras as PC

_ALL_CONDS = ["exalted", "own_sign", "friend", "neutral", "enemy", "debilitated", "combust", "sleeping"]


@pytest.mark.parametrize("status,state,conds,key", [
    ("strong", "FLOWING", [("Venus", "friend")], "strong"),
    ("steady", "NEEDS_BALANCE", [("Venus", "friend"), ("Mars", "neutral")], "steady"),
    ("steady", "NEEDS_BALANCE", [("Venus", "combust"), ("Mars", "friend")], "mixed"),
    ("needs_attention", "FRICTION", [("Venus", "friend")], "weak"),
    ("needs_attention", "DEPLETED", [("Venus", "debilitated")], "weak"),
])
def test_reason_key_follows_the_three_state_status(status, state, conds, key):
    assert PC._reason_key(status, state, conds) == key


def test_steady_with_an_overshadowed_ruler_never_says_balanced():
    key = PC._reason_key("steady", "NEEDS_BALANCE", [("Venus", "combust"), ("Sun", "friend")])
    text = PC._reason([("Venus", "combust"), ("Sun", "friend")], key, "en")
    assert "overshadowed" in text and "balanced" not in text.lower() and "mixed" in text


@pytest.mark.parametrize("lang", ["en", "es"])
@pytest.mark.parametrize("key", ["strong", "steady", "mixed", "weak", "blocked"])
def test_every_verdict_renders_in_both_languages(lang, key):
    assert PC._reason([("Venus", "friend")], key, lang).strip()


def test_needs_attention_never_ends_balanced_or_steady():
    for lang in ("en", "es"):
        for state in ("FRICTION", "DEPLETED"):
            k = PC._reason_key("needs_attention", state, [("Venus", "friend")])
            t = PC._reason([("Venus", "friend")], k, lang).lower()
            assert "balanced" not in t and "equilibrado" not in t and "steady" not in t and "estable" not in t


def test_computed_reasons_agree_with_their_status():
    chart = {"lagna": {"sign": "Aries", "sign_index": 0}, "planets": {}}
    conds = {p: {"condition": c} for p, c in zip(
        ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"),
        ["combust", "friend", "enemy", "neutral", "exalted", "debilitated", "own_sign", "sleeping", "neutral"])}
    out = PC.compute_chakra_states(chart, conditions=conds, language="en")
    for key, c in out.items():
        r = (c.get("reason") or "").lower()
        if not r:
            continue
        if c["status"] == "needs_attention":
            assert "needs attention" in r and "blocked" not in r, (key, r)
        if c["status"] == "steady":
            assert "steady" in r or "mixed" in r, (key, r)
        if c["status"] == "strong":
            assert "well supported" in r, (key, r)
        assert not re.search(r"balanced", r), (key, r)
