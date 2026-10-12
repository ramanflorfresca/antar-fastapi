"""Phase A birth-time rectification (antar_engine/rectify_window.py) — internal only.

Pins the guards from the platform spec: refuse tight claims on thin evidence,
report conflicts instead of averaging, never claim finer than the band floor,
and keep dasha arithmetic identical to production's vimsottari.py.
"""
from datetime import datetime, timezone

import pytest

from antar_engine import rectify_window as rw
from antar_engine.antar_ephemeris import julian_day

BIRTH = dict(date="1974-11-26", time="11:59", lat=28.6139, lng=77.209,
             tz_offset=5.5, source="family_memory")


def _ev(i, typ, date, tier="hard"):
    return {"id": i, "type": typ, "date": date, "tier": tier}


HARD3 = [_ev("m", "marriage", "1998-01"), _ev("c1", "childbirth", "2001-11-08"),
         _ev("c2", "childbirth", "2003-10-13")]


def test_fewer_than_three_hard_anchors_is_coarse_only():
    res = rw.phase_a(BIRTH, HARD3[:2])
    assert res["status"] == "coarse_only"
    assert "no narrowing" in res["reason"]
    assert "claimable_band_min" not in res


def test_soft_and_weak_events_never_count_as_hard():
    evs = HARD3[:2] + [_ev("p", "property", "2001-05", "soft"), _ev("w", "marriage", "1998-01", "weak")]
    assert rw.phase_a(BIRTH, evs)["hard_anchor_count"] == 2


def test_year_only_hard_anchor_is_demoted():
    n = rw.normalise_events([_ev("y", "marriage", "1998")])
    assert not n["hard"] and n["soft"][0]["demoted"]


def test_unsupported_event_type_is_reported_not_guessed():
    n = rw.normalise_events([_ev("d", "divorce", "2014-09-14")])
    assert n["ignored"] and not n["hard"]


def test_conflict_is_reported_never_averaged():
    res = rw.phase_a(BIRTH, HARD3, half_window_min=60)  # strict mode: c1 unexplainable here
    assert res["status"] == "conflict"
    assert res["window"] is None
    assert "c1" in res["unexplainable_alone"]


def test_band_never_below_floor():
    res = rw.phase_a(BIRTH, HARD3, half_window_min=60, connection="connected")
    assert res["status"] == "window"
    assert res["claimable_band_min"] >= rw.BAND_FLOOR_MIN[3]
    assert "Confirm against the next two" in res["validation_clause"]


def test_floor_by_anchor_count():
    assert rw._band_floor(1) == 30 and rw._band_floor(2) == 20
    assert rw._band_floor(3) == 13 and rw._band_floor(5) == 5


def test_vimshottari_matches_production():
    """After the birth-balance mahadasha, MD/AD must equal vimsottari.py's."""
    from antar_engine.vimsottari import calculate_vimsottari_from_chart
    jd = julian_day(1974, 11, 26, 11 + 59 / 60 - 5.5)
    moon = rw._moon_sid(jd)
    prod = calculate_vimsottari_from_chart({"planets": {"Moon": {"longitude": moon}}}, jd)
    for ymd in [(1998, 1, 15), (2001, 11, 8), (2003, 10, 13), (2026, 10, 12)]:
        when = datetime(*ymd, 12, tzinfo=timezone.utc)
        md = next(m for m in prod["mahadashas"] if m["start_datetime"] <= when < m["end_datetime"])
        ad = next(a for a in prod["antardashas"] if a["start_datetime"] <= when < a["end_datetime"])
        assert rw._vimshottari_at(moon, jd, julian_day(*ymd, 12.0)) == (md["lord"], ad["lord"]), ymd


def test_connected_mode_is_superset_of_strict():
    rule = rw.EVENT_RULES["childbirth"]
    karakas = dict(zip(rw._KARAKA_ORDER, rw._KARAKA_PLANETS))
    sign_of = {p: i for i, p in enumerate(rw._KARAKA_PLANETS + ["Rahu", "Ketu"])}
    strict = rw._significators(rule, 9, karakas)
    conn = rw._significators(rule, 9, karakas, sign_of, rw.CONNECTION_CONNECTED)
    assert strict <= conn
