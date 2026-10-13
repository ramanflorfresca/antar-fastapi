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
    phase = {"available": True, "chapter": {"plain_name": "Ambition", "start": "2026-08-13", "end": "2044-08-13"},
             "shift": {"plain_name": "Growth", "end": "2029-02-01"}}
    assert [i["zoom"] for i in B.beyond(feed, phase)] == ["year", "year", "chapter"]
    feed["care"][0]["opens_in_days"] = 12
    assert B.beyond(feed, None)[1]["zoom"] == "month"


def test_no_repeat_within_pool_window_and_pools_sizes():
    from datetime import timedelta
    for lang in ("en", "es"):
        for v in B.VERDICTS:
            n = len(B._LINES[lang][v])
            assert n >= 12
            d0 = date(2026, 10, 12)
            seen = [B.pick_line("c", d0 + timedelta(days=i), v, lang) for i in range(n)]
            assert len(set(seen)) == n          # a full cycle shows every line once, no repeat
    assert len(B._LINES["en"]["steady"]) == len(B._LINES["es"]["steady"]) == 18


def test_lines_obey_voice_rules():
    banned = ("!", "energy", "universe", "cosmic", "vibe", "will happen", "you must")
    for lang in B._LINES.values():
        for pool in lang.values():
            for line in pool:
                assert not any(b in line.lower() for b in banned), line
                assert len(line.split()) <= 18, line


def test_chapter_line_is_short_plain_and_dated():
    phase = {"available": True, "chapter": {"plain_name": "Ambition", "start": "2026-08-13", "end": "2044-08-13"},
             "shift": {"plain_name": "Growth", "end": "2029-02-01"}}
    it = B.beyond(None, phase)[0]
    assert it["text"] == "Chapter: Ambition, to 2044. Current shift: Growth, to 2029."
    assert it["range"] == "2026 \u2192 2044" and "Rahu" not in it["text"]
    assert B.beyond(None, {"available": True, "chapter": {"plain_name": "Ambition", "end": "2044-08-13"}})[0]["text"] == "Chapter: Ambition, to 2044."
    assert B.beyond(None, phase, "es")[0]["text"].startswith("Cap\u00edtulo: Ambition, hasta 2044.")


def test_areas_map_states_order_and_use_engine_lines():
    sig = {"domains": [
        {"key": "work", "label": "Career", "state": "steady", "line": "Work is steady.", "notable": False},
        {"key": "money", "label": "Money", "state": "volatile", "line": "Money moves both ways.", "notable": True},
        {"key": "body", "label": "Health", "state": "caution", "line": "Go easy.", "notable": False},
        {"key": "mind", "label": "Mind", "state": "favorable", "line": "Head is clear.", "notable": True},
        {"key": "x", "label": "X", "state": "weird", "line": "", "notable": False}]}
    a = B.build_areas(sig)
    assert [x["key"] for x in a] == ["body", "money", "mind", "work"]            # care, mixed, good, steady; empty line dropped
    assert [x["state"] for x in a] == ["care", "mixed", "good", "steady"]
    assert a[1]["line"] == "Money moves both ways." and B.build_areas({}) == []


def test_do_dont_fall_back_dedupe_and_cap():
    sig = {"do_today": ["Finish X"], "aligned_for": ["Finish X", "Review Y", "Plan Z"], "dont_today": [], "friction_for": ["Avoid A"]}
    d = B.build_do_dont(sig)
    assert d["do"] == ["Finish X", "Review Y"] and d["dont"] == ["Avoid A"]
    assert B.build_do_dont({}) == {"do": [], "dont": []}


def test_build_carries_areas_and_dos():
    out = B.build("c", {"domains": [{"key": "money", "label": "Money", "state": "caution", "line": "Hold.", "notable": True}],
                        "do_today": ["a"], "dont_today": ["b"]}, None, None, "en", date(2026, 10, 12), 9.0)
    assert out["areas"][0]["state"] == "care" and out["do"] == ["a"] and out["dont"] == ["b"]
