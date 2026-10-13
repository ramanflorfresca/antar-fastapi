from datetime import date

from antar_engine import timeline as T

TODAY = date(2026, 10, 12)


def test_day_uses_strip():
    sig = {"windows": [{"kind": "best", "start": "12:17 PM", "end": "1:05 PM"}]}
    out = T.build("day", sig, None, None, TODAY, 9.0)
    assert out["tracks"][0]["bands"][0]["kind"] == "best" and 0 < out["now"] < 1


def test_year_clips_and_drops_out_of_range():
    feed = {"tracks": [{"topic": "money", "label": "Money", "windows": [
        {"kind": "open", "start": "2026-10-12", "end": "2026-10-12"},
        {"kind": "open", "start": "2027-01-10", "end": "2027-05-09"},
        {"kind": "care", "start": "2028-01-01", "end": "2028-02-01"}]}]}
    out = T.build("year", None, feed, None, TODAY, 0)
    bands = out["tracks"][0]["bands"]
    assert len(bands) == 2 and all(0 <= b["from"] <= b["to"] <= 1 for b in bands)


def test_month_window():
    feed = {"tracks": [{"topic": "money", "label": "Money", "windows": [
        {"kind": "care", "start": "2026-10-20", "end": "2026-12-30"}]}]}
    b = T.build("month", None, feed, None, TODAY, 0)["tracks"][0]["bands"][0]
    assert b["end"] == "2026-11-11" and b["to"] == 1.0


def test_chapter_and_empty():
    ph = {"available": True, "chapter": {"start": "2026-08-13", "end": "2044-08-13", "plain_name": "Ambition"},
          "shift": {"start": "2026-08-13", "end": "2029-02-01", "plain_name": "Ambition"}, "upcoming_shifts": []}
    out = T.build("chapter", None, None, ph, TODAY, 0)
    assert [t["key"] for t in out["tracks"]] == ["chapter", "shift"] and 0 < out["now"] < 0.1
    assert T.build("chapter", None, None, None, TODAY, 0)["tracks"] == []
    assert T.build("bogus", None, None, None, TODAY, 0)["zoom"] == "day"
