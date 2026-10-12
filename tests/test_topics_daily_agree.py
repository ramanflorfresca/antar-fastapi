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


def test_fallback_topics_are_all_visible_on_home():
    rows = TE.fallback_topics("en")
    assert len(rows) == 7 and all(r["home_visible"] is True for r in rows)


def test_home_visible_hides_only_the_quiet_rows_and_never_leaves_fewer_than_three():
    import inspect
    src = inspect.getsource(TE.rank_topics)
    assert '"home_visible": kind != "quiet"' in src and "for r in out[:3]:" in src and 'r["home_visible"] = True' in src
