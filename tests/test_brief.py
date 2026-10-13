from datetime import date

from antar_engine import brief as B

SIG = {"day_energy": {"key": "steady"}, "direction": "positive", "confidence": {"level": "high"},
       "windows": [{"kind": "best", "start": "12:17 PM", "end": "1:05 PM"},
                   {"kind": "avoid", "start": "4:54 PM", "end": "6:19 PM"}]}


def test_verdict_rules():
    assert B.derive_verdict(SIG) == "go"
    assert B.derive_verdict({**SIG, "confidence": {"level": "low"}}) == "steady"
    assert B.derive_verdict({**SIG, "day_energy": {"key": "friction"}}) == "wait"
    assert B.derive_verdict({**SIG, "direction": "adverse"}) == "wait"
    assert B.derive_verdict({}) == "steady"


def test_strip_fractions_and_order():
    s = B.build_strip(SIG)
    assert [x["kind"] for x in s] == ["best", "avoid"]
    assert 0 < s[0]["from"] < s[0]["to"] < s[1]["from"] < s[1]["to"] < 1


def test_closing_soon():
    s = B.build_strip(SIG)
    assert B.closing_soon(s, 12.5)["open_now"] is True
    assert B.closing_soon(s, 8.0) is None          # ends > 4h away
    assert B.closing_soon(s, 14.0) is None         # already over


def test_line_is_deterministic_and_localised():
    d = date(2026, 10, 12)
    assert B.pick_line("c", d, "go") == B.pick_line("c", d, "go")
    assert B.pick_line("c", d, "go", "es") in B._LINES["es"]["go"]


def test_build_fails_open_on_empty():
    out = B.build("c", {}, None, None, "en", date(2026, 10, 12), 9.0)
    assert out["verdict"] == "steady" and out["beyond"] == [] and out["closing_soon"] is None
    assert out["verdict_word"] == "Steady"


def test_beyond_items():
    feed = {"next": [{"kind": "open", "topic": "money", "opens_in_days": 90, "label_range": "a"}],
            "care": [{"topic": "health", "opens_in_days": 240, "label_range": "b"}]}
    phase = {"available": True, "how_they_combine": "x", "chapter": {"start": "2026-08-13", "end": "2044-08-13"}}
    assert [i["zoom"] for i in B.beyond(feed, phase)] == ["year", "month", "chapter"]
