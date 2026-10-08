"""topic-read `shared_with`: people in the asker's ACTIVE Circle pairs whose own window for the same
topic overlaps - intersection dates + first name only, owner-only, capped, fail-open, additive."""
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_circle import A, B, X, TODAY  # noqa: E402
from test_circle_routes import AUTH, d, env as _env, make_pair  # noqa: E402,F401

env = _env
URL = f"/api/v1/chart/{A}/topic-read?topic=money&scale=month"


def _read():
    return {"chart_id": A, "topic": "money", "scale": "month", "tone": "open",
            "best_window": {"start": d(3).isoformat(), "end": d(10).isoformat(), "label": "x"},
            "watch_window": {"start": d(15).isoformat(), "end": d(20).isoformat(), "label": "y"}}


@pytest.fixture
def ctx(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_topic_read_compute", lambda *a: _read())
    return c, db, main


def get(c, headers=AUTH["uA"]):
    r = c.get(URL, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_overlap_is_intersection_only_per_window(ctx):
    c, db, main = ctx
    make_pair(c, db)
    out = get(c)
    # A asks, B open d5-d12 -> best d3-d10 overlap d5-d10; B has no care run -> no watch field
    assert out["best_window"]["shared_with"] == [
        {"chart_id": B, "first_name": "Aarav", "start": d(5).isoformat(), "end": d(10).isoformat()}]
    assert "shared_with" not in out["watch_window"]
    assert out["best_window"]["label"] == "x"                      # additive: nothing else changed


def test_none_when_no_overlap(ctx, monkeypatch):
    c, db, main = ctx
    make_pair(c, db)
    main_w = {"open": [{"start": d(40), "end": d(45), "confidence": "high"}], "care": []}
    monkeypatch.setattr(main, "_circle_windows_for", lambda cid, sc, t: ({"money": main_w}, d(29)))
    out = get(c)
    assert "shared_with" not in out["best_window"]


def test_not_shared_without_an_accepted_pair_or_ownership(ctx):
    c, db, main = ctx
    c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Aarav"},
           headers=AUTH["uA"])                                       # pending invite only
    assert "shared_with" not in get(c)["best_window"]


def test_anonymous_and_foreign_callers_never_get_names(ctx):
    c, db, main = ctx
    make_pair(c, db)
    assert "shared_with" not in get(c, headers={})["best_window"]
    assert "shared_with" not in get(c, headers=AUTH["uB"])["best_window"]     # B does not own chart A


def test_left_pair_is_excluded(ctx):
    c, db, main = ctx
    make_pair(c, db)
    assert "shared_with" in get(c)["best_window"]
    c.post(f"/api/v1/circle/{A}/pair/{B}/leave", headers=AUTH["uA"])
    assert "shared_with" not in get(c)["best_window"]


def test_ended_windows_ignored(ctx, monkeypatch):
    c, db, main = ctx
    make_pair(c, db)
    past = {"open": [{"start": d(-9), "end": d(-2), "confidence": "high"}], "care": []}
    monkeypatch.setattr(main, "_circle_windows_for", lambda cid, sc, t: ({"money": past}, d(29)))
    monkeypatch.setattr(main, "_topic_read_compute", lambda *a: dict(
        _read(), best_window={"start": d(-9).isoformat(), "end": d(-2).isoformat(), "label": "x"}))
    assert "shared_with" not in get(c)["best_window"]


def test_cap_of_five_earliest_first_and_pair_limit(ctx, monkeypatch):
    c, db, main = ctx
    make_pair(c, db)
    ids = [f"{i:08d}-0000-0000-0000-000000000009" for i in range(8)]
    for i, cid in enumerate(ids):
        db.t["charts"].append({"id": cid, "user_id": None, "name": f"P{i}", "first_name": f"P{i}",
                               "language": "en", "deleted_at": None})
        db.t["circle_pairs"].append({"id": f"pp{i}", "chart_a": A, "chart_b": cid, "created_at": f"2026-10-0{i+1}",
                                     "relation_a_to_b": "friend", "relation_b_to_a": "friend"})
    start = {cid: d(3 + i % 3) for i, cid in enumerate(ids)}

    def fw(cid, sc, t):
        s = start.get(cid, d(5))
        return ({"money": {"open": [{"start": s, "end": d(12), "confidence": "high"}], "care": []}}, d(29))
    monkeypatch.setattr(main, "_circle_windows_for", fw)
    sw = get(c)["best_window"]["shared_with"]
    assert len(sw) == 5
    assert [x["start"] for x in sw] == sorted(x["start"] for x in sw)
    assert set(sw[0]) == {"chart_id", "first_name", "start", "end"}
    monkeypatch.setattr(main, "_TOPIC_SHARED_PAIRS_MAX", 2)
    assert len(get(c)["best_window"]["shared_with"]) == 2


def test_fail_open_on_any_error(ctx, monkeypatch):
    c, db, main = ctx
    make_pair(c, db)

    def boom(*a):
        raise RuntimeError("x")
    monkeypatch.setattr(main, "_circle_windows_for", boom)
    out = get(c)
    assert "shared_with" not in out["best_window"] and out["tone"] == "open"
    monkeypatch.setattr(main, "_circle_windows_for", lambda *a: None)
    assert "shared_with" not in get(c)["best_window"]


def test_demo_chart_gets_none(ctx, monkeypatch):
    c, db, main = ctx
    make_pair(c, db)
    monkeypatch.setattr(main._circle, "is_demo", lambda sb, cid: True)
    assert "shared_with" not in get(c)["best_window"]


def test_cached_body_is_not_mutated(ctx):
    c, db, main = ctx
    make_pair(c, db)
    shared = _read()
    main._topic_read_compute = lambda *a: shared
    get(c)
    assert "shared_with" not in shared["best_window"]
