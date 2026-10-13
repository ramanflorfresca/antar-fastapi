from datetime import date

import pytest

from antar_engine.kp import kp_hourly as H


def test_net_and_lean_use_level_weights():
    st = {2: 1.0, 10: 0.5, 8: 0.25}                      # gain 1.5 - loss 0.25 = +1.25
    assert H.net_score(st) == 1.25 and H.lean_for(1.25) == "positive"
    assert H.lean_for(-0.5) == "adverse" and H.lean_for(0.25) == "neutral" and H.lean_for(0.0) == "neutral"
    assert H.net_score({}) == 0.0 and H.net_score({6: 1.0}) == 0.0   # house 6 is deliberately unscored


def test_planet_house_strength_takes_the_strongest_level():
    hs = {2: {"L1": [], "L2": ["Mars"], "L3": ["Mars"], "L4": []}, 10: {"L1": ["Mars"]}}
    assert H.planet_house_strength(hs)["Mars"] == {2: 0.75, 10: 1.0}


def test_timeline_covers_the_whole_day_and_merges():
    tl = H.moon_sub_timeline(date(2026, 10, 12), -4.0)
    assert tl[0]["start_min"] == 0 and tl[-1]["end_min"] == 1440
    assert all(a["end_min"] == b["start_min"] for a, b in zip(tl, tl[1:]))
    assert all((a["star_lord"], a["sub_lord"]) != (b["star_lord"], b["sub_lord"]) for a, b in zip(tl, tl[1:]))
    assert 5 <= len(tl) <= 14                                      # the Moon's sub changes a handful of times a day


def test_timeline_follows_the_timezone():
    a = H.moon_sub_timeline(date(2026, 10, 12), -4.0)
    b = H.moon_sub_timeline(date(2026, 10, 12), 5.5)
    assert [(s["sub_lord"], s["start_min"]) for s in a] != [(s["sub_lord"], s["start_min"]) for s in b]


def test_clock_and_span_parsing():
    assert H._clock_to_min("12:17 PM") == 12 * 60 + 17 and H._clock_to_min("12:05 AM") == 5
    assert H._span("4:54 PM – 6:19 PM") == (16 * 60 + 54, 18 * 60 + 19)
    assert H._span("") is None and H._span("nonsense") is None


def test_relative_leans_rank_the_day_and_tolerate_flat_days():
    segs = [{"start_min": 360 + i * 120, "end_min": 480 + i * 120, "net": n} for i, n in enumerate([-1, 0, 0.25, 1.5, 0.5, 0.0, -0.5])]
    H.relative_leans(segs)
    assert segs[3]["rel"] == "positive" and segs[0]["rel"] == "adverse"
    flat = [{"start_min": 360 + i * 120, "end_min": 480 + i * 120, "net": 0.5} for i in range(5)]
    H.relative_leans(flat)
    assert {x["rel"] for x in flat} == {"neutral"}


def test_build_fails_open_without_birth_data():
    out = H.build({"chart_data": {}}, date(2026, 10, 12), -4.0)
    assert out["available"] is False and "missing birth data" in out["reason"]


def test_record_is_a_noop_when_the_table_is_missing_and_never_retries():
    class Boom:
        calls = 0

        def table(self, *_):
            Boom.calls += 1
            raise RuntimeError("relation kp_hourly_shadow does not exist")
    H._DONE.clear()
    p = {"available": True, "date": "2026-10-12"}
    assert H.record(Boom(), "c1", p) is False and H.record(Boom(), "c1", p) is False
    assert Boom.calls == 1                                         # second call is skipped


def test_record_upserts_once_per_chart_day():
    class Fake:
        rows = []

        def table(self, name):
            assert name == "kp_hourly_shadow"
            return self

        def upsert(self, row, on_conflict=None):
            Fake.rows.append((row, on_conflict))
            return self

        def execute(self):
            return None
    H._DONE.clear()
    p = {"available": True, "date": "2026-10-12", "segments": []}
    assert H.record(Fake(), "c1", p) is True and H.record(Fake(), "c1", p) is False
    assert len(Fake.rows) == 1 and Fake.rows[0][1] == "chart_id,local_date"
    assert H.record(Fake(), "c2", {"available": False}) is False


def test_switch(monkeypatch):
    monkeypatch.setenv("KP_HOURLY_SHADOW", "off")
    assert H.enabled() is False
    monkeypatch.delenv("KP_HOURLY_SHADOW")
    assert H.enabled() is True


def _seg(a, b, net):
    return {"start_min": a, "end_min": b, "net": net}


def test_tight_window_is_one_stretch_clipped_to_two_and_a_half_hours():
    segs = [_seg(0, 360, 0.2), _seg(360, 780, 1.0), _seg(780, 1000, 0.5), _seg(1000, 1440, -1.0)]
    b = H.tight_window(segs, True)
    assert b == {"start_min": 360, "end_min": 360 + 150}                    # a 7h run is clipped to 150 min
    a = H.tight_window(segs, False)
    assert a["start_min"] == 1000 and a["end_min"] <= 1000 + 150 and a["end_min"] <= H.WAKING[1]


def test_tight_window_short_stretch_stays_as_is_and_flat_days_give_none():
    segs = [_seg(360, 480, 0.0), _seg(480, 570, 1.5), _seg(570, 1320, 0.25)]
    assert H.tight_window(segs, True) == {"start_min": 480, "end_min": 570}  # 90 min, kept whole
    assert H.tight_window([_seg(360, 700, 0.5), _seg(700, 1300, 0.5)], True) is None
    assert H.tight_window([_seg(360, 1300, 1.0)], True) is None
    assert 60 <= (H.MAX_WINDOW_MIN) <= 180
