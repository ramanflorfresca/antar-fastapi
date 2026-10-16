from datetime import date

from antar_engine import timing_reconcile as TR

TODAY = date(2026, 10, 13)
W = [{"kind": "open", "start": date(2027, 1, 10), "end": date(2027, 5, 9)},
     {"kind": "care", "start": date(2027, 6, 9), "end": date(2027, 9, 6)}]


def test_parse_label_variants():
    assert TR.parse_label("Jun 2027 – Oct 2027") == (date(2027, 6, 1), date(2027, 10, 31))
    assert TR.parse_label("Jan 2027") == (date(2027, 1, 1), date(2027, 1, 31))
    assert TR.parse_label("Nov 2026-Jan 2027") == (date(2026, 11, 1), date(2027, 1, 31))
    assert TR.parse_label("ene 2027 – may 2027") == (date(2027, 1, 1), date(2027, 5, 31))
    assert TR.parse_label("later this year") is None and TR.parse_label(None) is None


def test_the_live_conflict_is_trimmed_to_the_usable_part_with_an_astrologers_note():
    rc = TR.reconcile("Jun 2027 – Oct 2027", W, "money", "en", TODAY)
    assert rc["status"] == "trimmed" and rc["label"] == "Sep 2027 – Oct 2027"
    assert "Jun 9 – Sep 6 is a care stretch for money" in rc["note"] and "Sep 7 – Oct 31" in rc["note"] and "slow start" in rc["note"]


def test_window_inside_an_open_stretch_is_confirmed():
    rc = TR.reconcile("Feb 2027 – Apr 2027", W, "money", "en", TODAY)
    assert rc["status"] == "confirmed" and "open stretch for money (Jan 10 – May 9)" in rc["note"] and rc["label"] == "Feb 2027 – Apr 2027"


def test_window_mostly_in_care_is_flagged_not_moved():
    rc = TR.reconcile("Jun 2027 – Aug 2027", W, "money", "en", TODAY)
    assert rc["status"] == "pressured" and rc["label"] == "Jun 2027 – Aug 2027" and "build slowly" in rc["note"]


def test_unknown_to_the_feed_or_in_the_past_is_left_alone():
    assert TR.reconcile("Nov 2027 – Dec 2027", W, "money", "en", TODAY) is None
    assert TR.reconcile("Jan 2026", W, "money", "en", TODAY) is None
    assert TR.reconcile("Jun 2027 – Oct 2027", [], "money", "en", TODAY) is None
    assert TR.reconcile("no dates here", W, "money", "en", TODAY) is None


def test_apply_rewrites_label_note_and_timing():
    res = {"mode": "explore", "timing": "Jun 2027 – Oct 2027",
           "read": "Likely within the year — the money window is Jun 2027 – Oct 2027; until then it is groundwork. It holds if you test one client. It breaks if you rush."}
    rc = TR.reconcile(res["timing"], W, "money", "en", TODAY)
    out = TR.apply_to_answer(res, rc, "Jun 2027 – Oct 2027")
    assert out["timing"] == "Sep 2027 – Oct 2027" and "the money window is Sep 2027 – Oct 2027" in out["read"]
    assert out["read"].index("care stretch") < out["read"].index("It holds if") and out["timing_note"]["status"] == "trimmed"


def test_windows_for_topic_and_concern_map():
    feed = {"tracks": [{"topic": "money", "windows": [{"kind": "open", "start": "2027-01-10", "end": "2027-05-09"}, {"kind": "x", "start": "2027-01-01", "end": "2027-01-02"}]},
                       {"topic": "career", "windows": [{"kind": "care", "start": "2027-08-08", "end": "2027-10-06"}]}]}
    assert len(TR.windows_for_topic(feed, "money")) == 1 and TR.windows_for_topic(feed, "love") == []
    assert TR.topic_for_concern("speculation") == "money" and TR.topic_for_concern("property") is None


def test_spanish_note():
    rc = TR.reconcile("Jun 2027 – Oct 2027", W, "money", "es", TODAY)
    assert rc["status"] == "trimmed" and "tramo de cuidado para el dinero" in rc["note"]


# ── standing note: an answer with no window of its own still agrees with the Windows feed ─────────────────────────
from datetime import date as _d2
from antar_engine import timing_reconcile as _tr_s

_T = _d2(2026, 10, 15)


def _w(kind, a, b):
    return {"kind": kind, "start": _d2(*a), "end": _d2(*b)}


def test_standing_note_in_a_care_stretch_names_the_end_and_the_next_open_window():
    n = _tr_s.standing_note([_w("care", (2026, 8, 1), (2026, 10, 31)), _w("open", (2027, 1, 10), (2027, 5, 9))], "career", "en", _T)
    assert n["status"] == "care_now" and "your job and career is in a care stretch until Oct 31" in n["text"] and "starts Jan 10" in n["text"]


def test_standing_note_open_now_and_open_next():
    assert _tr_s.standing_note([_w("open", (2026, 10, 1), (2026, 12, 20))], "money", "en", _T)["status"] == "open_now"
    n = _tr_s.standing_note([_w("open", (2027, 2, 1), (2027, 3, 1))], "money", "en", _T)
    assert n["status"] == "open_next" and "starts Feb 1" in n["text"]


def test_standing_note_none_without_a_future_window_and_spanish():
    assert _tr_s.standing_note([_w("care", (2025, 1, 1), (2025, 2, 1))], "career", "en", _T) is None
    assert "tramo de cuidado hasta el 31 oct" in _tr_s.standing_note([_w("care", (2026, 8, 1), (2026, 10, 31))], "career", "es", _T)["text"]


def test_apply_standing_adds_the_sentence_once_before_it_holds_if():
    res = {"read": "The timing supports a move. It holds if you keep it steady.", "mode": "explore"}
    note = _tr_s.standing_note([_w("care", (2026, 8, 1), (2026, 10, 31))], "career", "en", _T)
    _tr_s.apply_standing(res, note)
    assert res["read"].index("care stretch") < res["read"].index("It holds if") and res["timing_note"]["status"] == "care_now"
    before = res["read"]
    _tr_s.apply_standing(res, note)
    assert res["read"] == before
