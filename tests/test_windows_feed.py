"""Windows feed: a cross-topic list of dated windows built from the topic engine's own scans.

Deterministic: fixed `today`, real swisseph charts, no network."""
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_circle import A, B, TODAY as CIRCLE_TODAY  # noqa: E402
from test_circle_routes import AUTH, d, env as _env, make_pair  # noqa: E402,F401
from test_topic_engine import (  # noqa: E402
    LANGS, TODAY, _JARGON, _real_ctx, _season_ctx, _strings, _synth, _ev, C, T)

from antar_engine import windows_feed as W  # noqa: E402

env = _env
KEYS = list(T.TOPIC_KEYS)


@pytest.fixture(scope="module")
def ctx():
    return _real_ctx("1990-10-15", "14:10")


@pytest.fixture(scope="module")
def raw(ctx):
    return W.raw_windows(ctx, TODAY)


def feed(ctx, raw, lang="en", hm=30):
    return W.assemble(ctx, raw, TODAY, lang, hm)


def D(s):
    return date.fromisoformat(s)


# ── ordering, caps, shape ────────────────────────────────────────────────────
def test_now_next_care_ordering_and_caps(ctx, raw):
    f = feed(ctx, raw)
    assert set(f) == {"chart_id", "as_of", "language", "horizon_end", "now", "next", "care",
                      "tracks", "big_picture", "quiet_topics"}
    assert f["as_of"] == TODAY.isoformat() and f["language"] == "en"
    assert f["now"] and f["next"] and f["care"]          # this fixture has all three
    for w in f["now"]:
        assert D(w["start"]) <= TODAY <= D(w["end"]) and w["days_left"] == (D(w["end"]) - TODAY).days
        assert w["kind"] in ("open", "care") and w["headline"].endswith(".") and w["move"]
        assert set(w) == {"topic", "label", "kind", "start", "end", "days_left", "headline", "move",
                          "why", "confidence"}
    assert [w["end"] for w in f["now"]] == sorted(w["end"] for w in f["now"])      # soonest-ending first
    assert len(f["next"]) <= 12 and len(f["care"]) <= 6
    assert [w["start"] for w in f["next"]] == sorted(w["start"] for w in f["next"])
    for lst in (f["next"], f["care"]):
        for w in lst:
            assert D(w["start"]) > TODAY and w["opens_in_days"] == (D(w["start"]) - TODAY).days
            assert w["window_phase"] == T.window_phase(D(w["start"]), D(w["end"]), TODAY)
            assert w["label_range"] and w["headline"] and w["move"]
    assert all(w["kind"] == "care" for w in f["care"])
    for key in KEYS:
        assert sum(w["topic"] == key for w in f["next"]) <= 2


def test_per_topic_cap_picks_the_two_earliest():
    r = {k: {"open": [], "care": []} for k in KEYS}
    r["money"]["open"] = [(TODAY + timedelta(days=30 * i), TODAY + timedelta(days=30 * i + 10)) for i in (1, 3, 5)]
    r["money"]["care"] = [(TODAY + timedelta(days=60), TODAY + timedelta(days=70))]
    f = W.assemble(_synth(), r, TODAY, "en", 30)
    assert [(w["kind"], w["start"]) for w in f["next"]] == [
        ("open", (TODAY + timedelta(days=30)).isoformat()), ("care", (TODAY + timedelta(days=60)).isoformat())]
    assert len(f["care"]) == 1 and len(f["tracks"][0]["windows"]) == 4        # the track keeps all


def test_overlapping_runs_of_one_topic_and_kind_merge():
    s = TODAY
    assert W._merge([(s + timedelta(days=5), s + timedelta(days=9)), (s, s + timedelta(days=6)),
                     (s + timedelta(days=10), s + timedelta(days=12)),
                     (s + timedelta(days=20), s + timedelta(days=25))]) == [
        (s, s + timedelta(days=12)), (s + timedelta(days=20), s + timedelta(days=25))]


def test_no_window_is_dated_before_today(ctx, raw):
    for tr in feed(ctx, raw)["tracks"]:
        for w in tr["windows"]:
            assert D(w["start"]) >= TODAY and D(w["end"]) >= D(w["start"])


# ── horizon ──────────────────────────────────────────────────────────────────
def test_horizon_cut_and_clamp(ctx, raw):
    full, short = feed(ctx, raw, hm=30), feed(ctx, raw, hm=3)
    he = D(short["horizon_end"])
    assert he == W._month_end(C.add_months(TODAY, 3))          # snapped to a calendar boundary so the last window's end does not slide daily
    for lst in (short["now"], short["next"], short["care"]):
        for w in lst:
            assert D(w["start"]) <= he and D(w["end"]) <= he
    for tr in short["tracks"]:
        assert all(D(w["start"]) <= he and D(w["end"]) <= he for w in tr["windows"])
    assert sum(len(t["windows"]) for t in short["tracks"]) < sum(len(t["windows"]) for t in full["tracks"])
    assert W.clamp_horizon(99) == 36 and W.clamp_horizon(0) == 1 and W.clamp_horizon("x") == 30
    assert W.clamp_horizon(None) == 30 and W.clamp_horizon(12) == 12
    assert feed(ctx, raw, hm=99)["horizon_end"] == W._month_end(C.add_months(TODAY, 36)).isoformat()


def test_quiet_topics_have_no_window_in_the_horizon(ctx, raw):
    f = feed(ctx, raw)
    tracked = {t["topic"] for t in f["tracks"]}
    assert set(f["quiet_topics"]).isdisjoint(tracked) and set(f["quiet_topics"]) | tracked == set(KEYS)
    assert f["quiet_topics"] == [k for k in KEYS if k in f["quiet_topics"]]
    tiny = W.assemble(ctx, raw, TODAY, "en", 1)
    assert len(tiny["quiet_topics"]) >= len(f["quiet_topics"])
    nothing = W.assemble(_synth(), {k: {"open": [], "care": []} for k in KEYS}, TODAY, "en", 30)
    assert nothing["quiet_topics"] == KEYS and nothing["tracks"] == [] and nothing["now"] == []


# ── agreement with the topic reads and the tiles ─────────────────────────────
def test_tracks_cover_the_windows_topic_read_shows(ctx, raw):
    f = feed(ctx, raw, hm=36)
    tracks = {t["topic"]: t["windows"] for t in f["tracks"]}
    checked = 0
    for key in KEYS:
        for scale in ("month", "season", "year"):
            r = T.read_topic(ctx, key, scale, TODAY, "en", with_best_fit=False)
            for field, kind in (("best_window", "open"), ("watch_window", "care")):
                w = r[field]
                if not w:
                    continue
                s, e = D(w["start"]), D(w["end"])
                hit = [x for x in tracks.get(key, []) if x["kind"] == kind and D(x["start"]) <= s and e <= D(x["end"])]
                assert hit, (key, scale, field, w["start"], w["end"])
                checked += 1
    assert checked > 0


def test_every_window_running_today_in_a_read_is_in_now(ctx, raw):
    now = {(w["topic"], w["kind"]) for w in feed(ctx, raw)["now"]}
    for key in KEYS:
        for scale in ("month", "season", "year"):
            r = T.read_topic(ctx, key, scale, TODAY, "en", with_best_fit=False)
            if r["window_phase"] == "now":
                assert (key, "open" if r["tone"] == "open" else "care") in now


def test_every_active_tile_is_in_now(ctx, raw):
    tiles = T.rank_topics(ctx, TODAY, "en")
    now_topics = {w["topic"] for w in feed(ctx, raw)["now"]}
    assert any(t["status"] == "active" for t in tiles)
    for t in tiles:
        if t["status"] == "active":
            assert t["key"] in now_topics


def test_phase_matches_the_engine_for_ahead_windows(ctx, raw):
    for w in feed(ctx, raw)["next"]:
        assert w["window_phase"] in ("soon", "later")
        assert " from " in w["headline"] or " starts " in w["headline"]      # names the day it opens


# ── big picture ──────────────────────────────────────────────────────────────
def test_big_picture_stretch_and_chapter():
    bp = W.assemble(_season_ctx("2029-04-25"), {k: {"open": [], "care": []} for k in KEYS}, TODAY, "en", 30)["big_picture"]
    assert bp["stretch"]["label"] == "The next 2½ years" and bp["stretch"]["end"] == "2029-04-25"
    assert bp["stretch"]["span"] == {"months": 31, "bucket": "2.5y"}
    assert (bp["stretch"]["chip"], bp["stretch"]["rung"]) == ("Life chapter", "stretch")
    assert bp["chapter"] == {"label": "Your current chapter · to Jan 2040", "start": "2020-01-01", "end": "2040-01-01", "rung": "chapter"}
    es = W.assemble(_season_ctx("2029-04-25"), {k: {"open": [], "care": []} for k in KEYS}, TODAY, "es", 30)["big_picture"]
    assert es["stretch"]["label"] == "Los próximos 2½ años" and es["chapter"]["label"].startswith("Tu capítulo actual")
    none = W.assemble(_synth(), {k: {"open": [], "care": []} for k in KEYS}, TODAY, "en", 30)["big_picture"]
    assert none["chapter"] is None and none["stretch"]["span"]["bucket"] == "months"      # 6-month fallback


# ── language + jargon ────────────────────────────────────────────────────────
def test_language_variants_and_no_jargon(ctx, raw):
    en = feed(ctx, raw, "en")
    seen = 0
    for lang in LANGS + ("hi",):
        f = feed(ctx, raw, lang)
        assert f["language"] == C.serve_language(lang)
        for s in _strings({k: v for k, v in f.items() if k != "chart_id"}):
            assert not _JARGON.search(s), (lang, s)
            seen += 1
        assert [w["start"] for w in f["next"]] == [w["start"] for w in en["next"]]     # dates never change
        if lang in ("es", "pt", "hinglish"):
            assert f["next"][0]["headline"] != en["next"][0]["headline"]
            assert f["tracks"][0]["label"] == C.LABEL[lang][f["tracks"][0]["topic"]]
    assert seen > 100
    assert feed(ctx, raw, "hi")["next"][0]["headline"] == en["next"][0]["headline"]    # Hindi falls back like the rest


def test_synth_chart_with_dated_signals_is_jargon_free():
    c = _synth("Saturn", [_ev("2026-10-20", "Jupiter", 10), _ev("2026-11-02", "Saturn", 2)])
    for lang in LANGS:
        for s in _strings(W.assemble(c, W.raw_windows(c, TODAY), TODAY, lang, 36)):
            assert not _JARGON.search(s), (lang, s)


# ── fail open ────────────────────────────────────────────────────────────────
def test_one_failing_topic_is_skipped_never_called_quiet(ctx, monkeypatch):
    real = T.windows_for

    def flaky(c, key, scale, today):
        if key == "money":
            raise RuntimeError("boom")
        return real(c, key, scale, today)
    monkeypatch.setattr(T, "windows_for", flaky)
    r = W.raw_windows(ctx, TODAY)
    assert r["money"] is None and r["love"] is not None
    f = W.assemble(ctx, r, TODAY, "en", 30)
    assert "money" not in f["quiet_topics"] and all(t["topic"] != "money" for t in f["tracks"])


def test_engine_scan_error_degrades_to_empty_lists(ctx, monkeypatch):
    monkeypatch.setattr(T, "_scan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    f = W.assemble(ctx, W.raw_windows(ctx, TODAY), TODAY, "en", 30)
    assert f["now"] == f["next"] == f["care"] == [] and f["tracks"] == []


# ── the route: caching, auth, demo, 404 ──────────────────────────────────────
def _patch_ctx(main, monkeypatch, c):
    monkeypatch.setattr(main, "_topic_ctx_load", lambda cid: (c, {"language": "en"}))
    T.cache_clear()


def test_second_call_does_not_recompute(env, ctx, monkeypatch):
    cl, db, main = env
    _patch_ctx(main, monkeypatch, ctx)
    calls = []
    real = T.windows_for
    monkeypatch.setattr(T, "windows_for", lambda *a: calls.append(a) or real(*a))
    url = f"/api/v1/chart/{A}/windows"
    r1 = cl.get(url + "?language=en")
    assert r1.status_code == 200 and r1.json()["next"]
    n = len(calls)
    assert n == len(KEYS) * 3
    assert cl.get(url + "?language=en").json() == r1.json() and len(calls) == n
    es = cl.get(url + "?language=es").json()                   # new language: words only, same dates
    assert es["language"] == "es" and len(calls) == n
    assert cl.get(url + "?language=en&horizon_months=6").status_code == 200 and len(calls) == n
    assert cl.get(url + "?horizon_months=99").json()["horizon_end"] == W._month_end(C.add_months(CIRCLE_TODAY, 36)).isoformat()


def test_route_fails_open_and_404(env, ctx, monkeypatch):
    cl, db, main = env
    monkeypatch.setattr(main, "_topic_ctx_load", lambda cid: (None, None))
    assert cl.get(f"/api/v1/chart/{A}/windows").status_code == 404
    monkeypatch.setattr(main, "_topic_ctx_load", lambda cid: (_ for _ in ()).throw(RuntimeError("db down")))
    r = cl.get(f"/api/v1/chart/{A}/windows?language=pt")
    assert r.status_code == 200 and r.json()["now"] == [] and r.json()["language"] == "pt"


def _fixed_feed():
    return {"chart_id": A, "as_of": TODAY.isoformat(), "language": "en", "horizon_end": d(900).isoformat(),
            "now": [], "next": [], "care": [], "big_picture": {"stretch": None, "chapter": None}, "quiet_topics": [],
            "tracks": [{"topic": "money", "label": "Money",
                        "windows": [{"kind": "open", "start": d(3).isoformat(), "end": d(10).isoformat()}]}]}


def test_shared_with_only_for_the_owner(env, monkeypatch):
    cl, db, main = env
    monkeypatch.setattr(main, "_windows_compute", lambda *a: _fixed_feed())
    make_pair(cl, db)
    url = f"/api/v1/chart/{A}/windows"
    mine = cl.get(url, headers=AUTH["uA"]).json()["tracks"][0]
    assert mine["shared_with"] == {"open": [
        {"chart_id": B, "first_name": "Aarav", "start": d(5).isoformat(), "end": d(10).isoformat()}]}
    assert mine["windows"] and mine["topic"] == "money"
    for headers in ({}, AUTH["uB"]):                      # anonymous and someone else's chart
        r = cl.get(url, headers=headers)
        assert r.status_code == 200 and "shared_with" not in r.json()["tracks"][0]


def test_demo_chart_reads_without_shared_with(env, ctx, monkeypatch):
    cl, db, main = env
    _patch_ctx(main, monkeypatch, ctx)
    make_pair(cl, db)
    monkeypatch.setattr(main._circle, "is_demo", lambda sb, cid: True)
    r = cl.get(f"/api/v1/chart/{A}/windows", headers=AUTH["uA"])
    assert r.status_code == 200 and r.json()["tracks"]
    assert all("shared_with" not in t for t in r.json()["tracks"])


# ── [why-line] every window says what carried it ──────────────────────────
def test_every_entry_carries_a_why_and_confidence(ctx, raw):
    f = feed(ctx, raw)
    ents = f["now"] + f["next"] + f["care"]
    assert ents
    for w in ents:
        assert set(w["why"]) == {"line", "bullets"} and isinstance(w["why"]["bullets"], list)
        assert w["confidence"] is None or w["confidence"]["level"] in ("high", "medium", "low")
        if w["why"]["line"]:
            assert w["why"]["line"].endswith(".")
            assert not any(t in w["why"]["line"].lower() for t in ("saturn", "jupiter", "dasha", "house", "transit"))
        # the contradiction a window card must never carry
        assert "not a dated window" not in " ".join(w["why"]["bullets"])


def test_why_is_chart_specific_and_follows_the_driver():
    drv_core = {"dasha_kind": "core", "chara_confirm": True, "n_signals": 2,
                "first_date": "2026-11-02", "last_date": "2026-12-20", "mode": "open", "score": 5.0,
                "confidence": "high"}
    drv_alone = dict(drv_core, n_signals=0, first_date="", last_date="", confidence="low")
    drv_theme = dict(drv_core, dasha_kind="theme", confidence="medium")
    a, ca = W._why("money", "open", D("2026-11-01"), D("2026-12-30"), TODAY, "en", drv_core, "exact")
    b, cb = W._why("money", "open", D("2026-11-01"), D("2026-12-30"), TODAY, "en", drv_alone, "exact")
    c, _ = W._why("money", "open", D("2026-11-01"), D("2026-12-30"), TODAY, "en", drv_theme, "exact")
    assert "tied directly" in a["line"] and "support" in a["line"].lower()        # chapter + dated clause
    assert "tied directly" in b["line"] and "support" not in b["line"].lower()    # chapter alone: no dated clause
    assert "touches the themes" in c["line"]
    assert ca["level"] == "high" and cb["level"] == "low"
    assert len({a["line"], b["line"], c["line"]}) == 3


def test_why_care_window_says_press_and_unknown_birth_time_caps_confidence():
    drv = {"dasha_kind": "core", "chara_confirm": False, "n_signals": 1, "first_date": "2026-11-02",
           "last_date": "2026-11-20", "mode": "care", "score": 4.0, "confidence": "high"}
    w, conf = W._why("career", "care", D("2026-11-01"), D("2026-11-30"), TODAY, "en", drv, "unknown")
    assert "press" in w["line"].lower() and conf["level"] == "low"
    assert any("birth time" in b.lower() for b in w["bullets"])


def test_why_missing_driver_is_empty_not_an_error():
    assert W._why("money", "open", D("2026-11-01"), D("2026-11-30"), TODAY, "en", None, "exact") == (
        {"line": "", "bullets": []}, None)


@pytest.mark.parametrize("lang", LANGS)
def test_why_lines_exist_in_every_language(ctx, raw, lang):
    ents = feed(ctx, raw, lang)["now"] + feed(ctx, raw, lang)["next"]
    assert any(w["why"]["line"] for w in ents)


def test_driver_survives_merge_and_the_json_round_trip(ctx, raw):
    back = W.raw_from_json(W.raw_to_json(raw))
    for key, v in raw.items():
        if v is None:
            continue
        assert back[key]["open"] == v["open"] and back[key]["care"] == v["care"]
        assert back[key]["drivers"] == v["drivers"]
    # every window has a driver keyed by its start
    for key, v in raw.items():
        for kd in ("open", "care"):
            for s, e in (v or {}).get(kd, []):
                assert s.isoformat() in v["drivers"][kd]


def test_merge_driver_keeps_the_stronger_link_and_widest_dates():
    a = {"dasha_kind": "theme", "chara_confirm": False, "n_signals": 1, "first_date": "2026-11-05",
         "last_date": "2026-11-10", "score": 2.0, "mode": "open", "confidence": "low"}
    b = {"dasha_kind": "core", "chara_confirm": True, "n_signals": 3, "first_date": "2026-11-01",
         "last_date": "2026-11-30", "score": 5.0, "mode": "open", "confidence": "high"}
    m = W._merge_driver(a, b)
    assert m["dasha_kind"] == "core" and m["confidence"] == "high"
    assert m["first_date"] == "2026-11-01" and m["last_date"] == "2026-11-30" and m["n_signals"] == 3


def test_a_window_not_yet_open_never_says_right_now():
    drv = {"dasha_kind": "core", "chara_confirm": False, "n_signals": 1, "first_date": "2027-02-02",
           "last_date": "2027-03-01", "mode": "open", "score": 4.0, "confidence": "medium"}
    for lang in LANGS:
        ahead, _ = W._why("money", "open", TODAY + timedelta(days=90), TODAY + timedelta(days=120), TODAY, lang, drv, "exact")
        now, _ = W._why("money", "open", TODAY, TODAY + timedelta(days=30), TODAY, lang, drv, "exact")
        assert ahead["line"] and now["line"] and ahead["line"] != now["line"], lang
    en, _ = W._why("money", "open", TODAY + timedelta(days=90), TODAY + timedelta(days=120), TODAY, "en", drv, "exact")
    assert "right now" not in en["line"] and "then" in en["line"]


def test_horizon_end_is_the_same_all_month_so_the_last_window_does_not_slide():
    from datetime import date as _d
    assert W._month_end(_d(2026, 10, 7)) == _d(2026, 10, 31) and W._month_end(_d(2026, 12, 31)) == _d(2026, 12, 31)
    assert W._month_end(_d(2028, 2, 3)) == _d(2028, 2, 29)
    ends = {W._month_end(C.add_months(_d(2026, 10, d), 12)) for d in range(1, 29)}
    assert ends == {_d(2027, 10, 31)}
