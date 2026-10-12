from antar_engine import topic_engine as TE


def _row(key, kind, ends_today):
    return {"key": key, "label": key.title(), "status": "active", "tag": "Open now, until Oct 11" if kind == "open_now" else "x", "tag_kind": kind, "tone": "open",
            "ends_today": ends_today, "verdict": "Good time", "headline": "Money matters have better backing than usual.", "rank": 1}


def test_today_only_good_time_yields_to_the_daily_caution():
    rows = [_row("money", "open_now", True), _row("career", "open_now", True), _row("love", "open_now", True)]
    daily = [{"key": "money", "state": "caution"}, {"key": "work", "state": "steady"}, {"key": "people", "state": "caution"}]
    out = TE.reconcile_with_daily(rows, daily, "en")
    m, c, l = out
    assert m["tag_kind"] == "care_now" and m["verdict"] == "Be careful" and m["tone"] == "care" and "better backing" not in m["headline"]
    assert c["tag_kind"] == "open_now" and c["verdict"] == "Good time"        # the daily vote is steady for work: untouched
    assert l["tag_kind"] == "open_now"                                         # love has no daily mapping: untouched


def test_longer_windows_and_missing_daily_are_left_alone():
    longer = _row("money", "open_now", False)
    assert TE.reconcile_with_daily([longer], [{"key": "money", "state": "caution"}], "en")[0]["tag_kind"] == "open_now"
    today = _row("money", "open_now", True)
    assert TE.reconcile_with_daily([today], None, "en")[0]["tag_kind"] == "open_now"
    assert TE.reconcile_with_daily([today], "garbage", "en")[0]["tag_kind"] == "open_now"      # never raises


def _read(topic="money", tone="open", scale="today"):
    return {"topic": topic, "scale": scale, "tone": tone, "claim": "Today, good for income and pricing, but careful with money swings.",
            "best_window": {"start": "2026-10-12", "end": "2026-10-12", "label": "Oct 12"}, "your_move": "x"}


def test_a_today_read_that_is_open_yields_to_a_daily_caution_and_nothing_else_changes():
    caution = [{"key": "money", "state": "caution"}, {"key": "work", "state": "steady"}]
    r = TE.agree_read_with_daily(_read(), caution, "en")
    assert r["tone"] == "care" and r["best_window"] is None and "income and pricing" not in r["claim"] and r["your_move"] == "x"
    assert TE.agree_read_with_daily(_read(), [{"key": "money", "state": "volatile"}], "en")["tone"] == "open"      # volatile ('careful with swings') already agrees
    assert TE.agree_read_with_daily(_read("career"), caution, "en")["tone"] == "open"                              # work is steady
    assert TE.agree_read_with_daily(_read(scale="month"), caution, "en")["tone"] == "open"                         # only the 'today' scale
    assert TE.agree_read_with_daily(_read(tone="care"), caution, "en")["tone"] == "care"
    assert TE.agree_read_with_daily(_read(), None, "en")["tone"] == "open" and TE.agree_read_with_daily(None, caution, "en") is None
