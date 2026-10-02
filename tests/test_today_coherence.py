"""Today card coherence (2026-10-02 UX walkthrough).

The card stitches /daily-week's today entry with /daily-signal. Live it read
"LIGHTER-TOUCH DAY" over "A friction day — …", showed two different "best"
times, an avoid-line arguing from a friction day, "Work & standing" twice, and
the same canned "Your Move" on consecutive days.
"""
from antar_engine.daily_life_areas import dedupe_day_map
from antar_engine.today_nudge import derive_todays_nudge
from antar_engine.today_signal import reconcile_week_today, snap_day_type


def _auth(band="light"):
    return {
        "headline": "Today lights up a venture — take it, but keep a stop.",
        "card": {
            "language": "en",
            "day_energy": {"key": band, "label": "LIGHTER-TOUCH DAY", "score": 3},
            "score": 3,
            "windows": [
                {"kind": "avoid", "start": "10:14 AM", "end": "11:20 AM"},
                {"kind": "best", "start": "11:20 AM", "end": "12:09 PM", "text": "best"},
            ],
            "move": "Take the money move today…",
            "day_turn": "Your clearest window today is around 11:20 AM.",
        },
    }


def _week_today():
    return {
        "date": "2026-10-02",
        "day_energy": {"key": "friction"},
        "is_friction_day": True,
        "verdict_subline": "A friction day — steady effort beats bold moves.",
        "windows": [
            {"type": "peak", "start": "12:21 PM", "end": "2:52 PM"},
            {"type": "reflection", "start": "4:25 PM", "end": "5:47 PM"},
            {"type": "connection", "start": "11:30 AM", "end": "12:00 PM"},
        ],
        "evita_hoy": [
            "Don't launch a new deal today — the day's friction runs deep.",
            "Skip the luxury purchase.",
        ],
    }


def test_band_and_headline_follow_daily_signal():
    d = reconcile_week_today(_week_today(), _auth(), "en")
    assert d["day_energy"]["key"] == "light"
    assert d["is_friction_day"] is False
    assert d["verdict_subline"].startswith("Today lights up a venture")


def test_single_best_window_and_no_overlap():
    d = reconcile_week_today(_week_today(), _auth(), "en")
    peaks = [w for w in d["windows"] if w.get("type") == "peak"]
    assert [(w["start"], w["end"]) for w in peaks] == [("11:20 AM", "12:09 PM")]
    # the weekly 11:30 connection window collides with the authority's best → dropped
    assert all(w["start"] != "11:30 AM" for w in d["windows"])
    assert any(w.get("type") == "reflection" for w in d["windows"])


def test_friction_justified_avoid_lines_dropped_off_friction():
    d = reconcile_week_today(_week_today(), _auth(), "en")
    assert d["evita_hoy"] == ["Skip the luxury purchase."]


def test_friction_band_keeps_avoid_lines():
    d = reconcile_week_today(_week_today(), _auth("friction"), "en")
    assert len(d["evita_hoy"]) == 2


def test_other_language_does_not_inject_english_prose():
    d = reconcile_week_today(_week_today(), _auth(), "es")
    assert d["day_energy"]["key"] == "light"
    assert d["verdict_subline"].startswith("A friction day")  # untouched prose
    assert d["windows"][0]["start"] == "12:21 PM"


def test_fail_open_without_authority():
    w = _week_today()
    assert reconcile_week_today(w, None, "en") is w
    assert reconcile_week_today(w, {"headline": "x"}, "en")["day_energy"]["key"] == "friction"


def test_snap_day_type():
    assert snap_day_type("A heavy day — hold.", "light") == "A lighter-touch day — hold."
    assert snap_day_type("A steady day for review.", "steady") == "A steady day for review."
    assert snap_day_type("No day word here.", "friction") == "No day word here."


def test_work_and_authority_render_once():
    rows = [{"key": "work", "label": "Work"}, {"key": "money"},
            {"key": "authority", "label": "Work & standing"}]
    assert [r["key"] for r in dedupe_day_map(rows)] == ["work", "money"]


def test_your_move_varies_day_to_day_but_is_stable_within_a_day():
    days = ["2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03"]
    lines = [derive_todays_nudge("caution", ["money"], "IN", date_str=d) for d in days]
    assert all(a != b for a, b in zip(lines, lines[1:]))
    assert derive_todays_nudge("caution", ["money"], "IN", date_str="2026-10-02") == lines[2]
