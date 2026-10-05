"""[pct-narrow 2026-10-05] narration_polish must strip internal metric
phrasing (confidence / probability / score) but never an ordinary
instruction that happens to contain a percentage."""
import pytest

from antar_engine.narration_polish import polish, strip_internal_metrics


ADVICE = [
    "Move 10% of every payment into a separate account this week — treat it as untouchable.",
    "Call one client — ask for 20% upfront.",
    "Offer a 15% discount to your first three clients.",
    "Raise your rate by 10% for new clients — keep old clients where they are.",
    "Save 10% (about one week of pay) this month.",
    "Call one client — ask for 20% upfront.".replace("—", "–"),
]


@pytest.mark.parametrize("text", ADVICE)
def test_percentage_advice_is_untouched(text):
    assert strip_internal_metrics(text) == text
    assert polish({"action_item": text})["action_item"] == text


def test_reported_examples_via_polish():
    d = polish({"action_item": "Move 10% of every payment into a separate account "
                               "this week — treat it as untouchable."})
    assert d["action_item"].startswith("Move 10% of every payment")
    assert d["action_item"].endswith("treat it as untouchable.")
    d = polish({"action_item": "Call one client — ask for 20% upfront."})
    assert d["action_item"] == "Call one client — ask for 20% upfront."


def test_text_without_percentage_unchanged():
    t = "Call one client — ask for payment upfront."
    assert polish({"action_item": t})["action_item"] == t


@pytest.mark.parametrize("text,expected", [
    ("Push the pitch this week — 72% confidence on a yes.", "Push the pitch this week."),
    ("Ask for the raise (72% confidence).", "Ask for the raise."),
    ("Pitch on Tuesday, with 70% confidence.", "Pitch on Tuesday."),
    ("Career signal sits at 51%. Ask for the raise.", "Ask for the raise."),
    ("The probability is 64% — go ahead.", "Go ahead."),
    ("There is a 70% chance of success; act on Tuesday.", "Act on Tuesday."),
    ("Lead the meeting — score 0.8 today.", "Lead the meeting."),
])
def test_internal_metrics_still_stripped(text, expected):
    out = strip_internal_metrics(text)
    assert out == expected
    assert "%" not in out and "0.8" not in out


def test_metric_stripped_but_advice_pct_kept_in_same_text():
    t = "Ask for 20% upfront (72% confidence)."
    assert strip_internal_metrics(t) == "Ask for 20% upfront."


def test_idempotent():
    for t in ADVICE + ["Push the pitch this week — 72% confidence on a yes."]:
        once = strip_internal_metrics(t)
        assert strip_internal_metrics(once) == once
