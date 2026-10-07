"""Topic-read "did it hold?" check-backs: windows are recorded when shown, asked about
only after they END, answered into the existing outcome loop, and scored by the
accuracy board honestly (hits AND misses, small-n suppressed)."""
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from antar_engine import accuracy_board as ab
from antar_engine import topic_checkback as tcb
from antar_engine import topic_copy as C

TODAY = date(2026, 10, 7)
NOW = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)
CHART = str(uuid.uuid4())
LANGS = ("en", "es", "pt", "hinglish")

_JARGON = re.compile(
    r"\b(dasha|dasa|mahadasha|antardasha|jaimini|vimsottari|chara|malefic\w*|benefic\w*|"
    r"transits?|gochar|karakas?|lagna|nakshatra|navamsa|kendra|trikona|ascendant|houses?|"
    r"d-?\d{1,2}|sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)\b",
    re.I)


def read(scale="month", best=("2026-10-14", "2026-10-20"), watch=None, period_end="2026-11-05",
         topic="money", tone="open", **kw):
    out = {"chart_id": CHART, "topic": topic, "scale": scale, "language": "en", "tone": tone,
           "claim": "A good stretch for money.",
           "period": {"start": "2026-10-07", "end": period_end},
           "best_window": {"start": best[0], "end": best[1], "label": "x"} if best else None,
           "watch_window": {"start": watch[0], "end": watch[1], "label": "y"} if watch else None}
    out.update(kw)
    return out


# ── an in-memory stand-in for the slice of PostgREST these helpers use ──
class _Q:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.f, self._order, self._lim, self._op, self._payload, self._opts = [], None, None, "select", None, {}

    def select(self, *_):
        return self

    def eq(self, c, v):
        self.f.append(lambda r: r.get(c) == v); return self

    def gte(self, c, v):
        self.f.append(lambda r: str(r.get(c)) >= str(v)); return self

    def lte(self, c, v):
        self.f.append(lambda r: str(r.get(c)) <= str(v)); return self

    def in_(self, c, vs):
        self.f.append(lambda r: r.get(c) in vs); return self

    def order(self, c):
        self._order = c; return self

    def limit(self, n):
        self._lim = n; return self

    def upsert(self, payload, on_conflict=None, ignore_duplicates=False):
        self._op, self._payload, self._opts = "upsert", payload, (on_conflict, ignore_duplicates); return self

    def update(self, payload):
        self._op, self._payload = "update", payload; return self

    def execute(self):
        if self.db.missing:
            raise Exception("PGRST205 Could not find the table 'public.%s'" % self.name)
        rows = self.db.t.setdefault(self.name, [])
        class R: data = None
        r = R()
        if self._op == "select":
            out = [x for x in rows if all(f(x) for f in self.f)]
            if self._order:
                out.sort(key=lambda x: str(x.get(self._order)))
            r.data = [dict(x) for x in out[: self._lim]]
        elif self._op == "update":
            for x in rows:
                if all(f(x) for f in self.f):
                    x.update(self._payload)
            r.data = []
        else:
            key, ign = self._opts
            hit = next((x for x in rows if x.get(key) == self._payload.get(key)), None)
            if hit and ign:
                r.data = []
            elif hit:
                hit.update(self._payload); r.data = [hit]
            else:
                row = dict(self._payload); row.setdefault("id", str(uuid.uuid4()))
                rows.append(row); r.data = [row]
        return r


class DB:
    def __init__(self, missing=False):
        self.t, self.missing = {}, missing

    def table(self, name):
        return _Q(self, name)

    def claims(self):
        return self.t.get("prediction_claims", [])


# ── A) RECORD ────────────────────────────────────────────────────────────────
def test_records_one_claim_per_window_with_board_fields():
    db = DB()
    n = tcb.record_windows(db, read(watch=("2026-10-25", "2026-10-28"), tone="open"), CHART, TODAY)
    assert n == 2
    best = next(c for c in db.claims() if c["engines"]["topic_read"]["kind"] == "best")
    assert best["source"] == "topic_read" and best["claim_type"] == "window"
    assert (best["window_start"], best["window_end"]) == ("2026-10-14", "2026-10-20")
    assert best["engines"]["topic_read"]["scale"] == "month" and best["verdict"] == "open"
    assert best["checkin_due_at"].startswith("2026-10-21")      # the day AFTER the window ends


def test_recording_is_idempotent_and_overlap_aware():
    db = DB()
    tcb.record_windows(db, read(), CHART, TODAY)
    tcb.record_windows(db, read(), CHART, TODAY)                 # same window shown twice
    # tomorrow the engine's buckets shift: same stretch, start/end a few days off
    tcb.record_windows(db, read(best=("2026-10-15", "2026-10-22")), CHART, TODAY + timedelta(days=1))
    assert len(db.claims()) == 1
    # a genuinely later window is a new claim; so is a different kind or scale
    tcb.record_windows(db, read(best=("2026-10-29", "2026-11-02")), CHART, TODAY)
    tcb.record_windows(db, read(best=None, watch=("2026-10-14", "2026-10-20")), CHART, TODAY)
    assert len(db.claims()) == 3


def test_no_claim_for_no_window_locked_replay_today_scale_or_clipped_window():
    db = DB()
    assert tcb.record_windows(db, read(best=None, tone="steady"), CHART, TODAY) == 0
    assert tcb.record_windows(db, read(locked=True), CHART, TODAY) == 0
    assert tcb.record_windows(db, read(scale="today", best=("2026-10-07", "2026-10-07")), CHART, TODAY) == 0
    # a month window that runs into the rolling 30-day edge has no known end yet
    assert tcb.record_windows(db, read(best=("2026-10-30", "2026-11-05"), period_end="2026-11-05"),
                              CHART, TODAY) == 0
    assert db.claims() == []


def test_year_window_to_a_fixed_period_end_is_recorded():
    db = DB()
    assert tcb.record_windows(db, read(scale="year", best=("2026-11-01", "2027-02-28"),
                                       period_end="2027-02-28"), CHART, TODAY) == 1


def test_fail_open_when_table_missing(caplog):
    db = DB(missing=True)
    assert tcb.record_windows(db, read(), CHART, TODAY) == 0       # no raise
    assert tcb.due_items(db, CHART, "en", NOW) == []
    with pytest.raises(tcb.StoreUnavailable):
        tcb.record_answer(db, CHART, str(uuid.uuid4()), "yes")


def test_fail_open_on_any_store_error():
    class Boom:
        def table(self, *_):
            raise RuntimeError("db down")
    assert tcb.record_windows(Boom(), read(), CHART, TODAY) == 0
    assert tcb.due_items(Boom(), CHART, "en", NOW) == []


# ── B) CHECK-BACK DUE ────────────────────────────────────────────────────────
def test_due_only_after_the_window_has_ended():
    db = DB()
    tcb.record_windows(db, read(), CHART, TODAY)                  # ends Oct 20
    assert tcb.due_items(db, CHART, "en", datetime(2026, 10, 20, 23, 0, tzinfo=timezone.utc)) == []
    got = tcb.due_items(db, CHART, "en", datetime(2026, 10, 21, 0, 1, tzinfo=timezone.utc))
    assert len(got) == 1


def test_question_text_best_and_watch_in_plain_words():
    db = DB()
    tcb.record_windows(db, read(best=("2026-10-14", "2026-10-20"), watch=("2026-10-22", "2026-10-24")),
                       CHART, TODAY)
    items = tcb.due_items(db, CHART, "en", NOW, limit=3)
    q = {i["kind"]: i for i in items}
    assert q["best"]["question"] == "Your money window, Oct 14 – Oct 20, has passed. Did it hold?"
    assert "caution" in q["watch"]["question"] and "matter" in q["watch"]["question"]
    assert [o["value"] for o in q["best"]["options"]] == ["yes", "no", "not_sure"]
    assert q["best"]["window"] == {"start": "2026-10-14", "end": "2026-10-20", "label": "Oct 14 – Oct 20"}
    assert q["best"]["id"] and q["best"]["topic"] == "money"


def test_one_question_at_a_time_oldest_first_and_cap():
    db = DB()
    for i, (s, e) in enumerate([("2026-10-10", "2026-10-12"), ("2026-10-14", "2026-10-16"),
                                ("2026-10-17", "2026-10-19"), ("2026-10-20", "2026-10-22")]):
        tcb.record_windows(db, read(best=(s, e)) | {"topic": ["money", "career", "love", "health"][i]},
                           CHART, TODAY)
    one = tcb.due_items(db, CHART, "en", NOW)
    assert len(one) == 1 and one[0]["window"]["end"] == "2026-10-12"           # oldest first
    assert len(tcb.due_items(db, CHART, "en", NOW, limit=3)) == 3
    assert len(tcb.due_items(db, CHART, "en", NOW, limit=99)) == 3             # hard cap


def test_other_sources_and_other_charts_are_not_asked():
    db = DB()
    tcb.record_windows(db, read(), CHART, TODAY)
    db.claims().append({"id": str(uuid.uuid4()), "chart_id": CHART, "source": "ask_explore",
                        "topic": "money", "window_start": "2026-10-01", "window_end": "2026-10-02",
                        "engines": {}, "checkin_due_at": "2026-10-03T00:00:00+00:00"})
    assert len(tcb.due_items(db, CHART, "en", NOW, limit=3)) == 1
    assert tcb.due_items(db, str(uuid.uuid4()), "en", NOW) == []


def test_showing_a_checkback_stamps_it_shown_for_the_answer_rate():
    db = DB()
    tcb.record_windows(db, read(), CHART, TODAY)
    tcb.due_items(db, CHART, "en", NOW)
    assert db.claims()[0]["checkin_sent_at"] and db.claims()[0]["checkin_channel"] == "app"


# ── C) ANSWER ────────────────────────────────────────────────────────────────
def _one(db):
    tcb.record_windows(db, read(), CHART, TODAY)
    return db.claims()[0]["id"]


def test_answer_yes_no_idempotent_and_final():
    db = DB(); cid = _one(db)
    assert tcb.record_answer(db, CHART, cid, "yes", NOW)["saved"] is True
    again = tcb.record_answer(db, CHART, cid, "no", NOW)             # a final answer is never overwritten
    assert again == {"saved": False, "already_answered": True, "outcome": "yes"}
    assert [o["outcome"] for o in db.t["prediction_outcomes"]] == ["yes"]
    assert tcb.due_items(db, CHART, "en", NOW) == []                  # answered → never asked again


def test_unknown_malformed_and_other_charts_ids_rejected():
    db = DB(); cid = _one(db)
    for bad in (str(uuid.uuid4()), "nope", ""):
        with pytest.raises(tcb.UnknownCheckback):
            tcb.record_answer(db, CHART, bad, "yes")
    with pytest.raises(tcb.UnknownCheckback):                         # right id, wrong chart
        tcb.record_answer(db, str(uuid.uuid4()), cid, "yes")
    with pytest.raises(ValueError):
        tcb.record_answer(db, CHART, cid, "partly")


def test_not_sure_is_asked_once_more_after_30_days_then_never():
    db = DB(); cid = _one(db)
    tcb.record_answer(db, CHART, cid, "not_sure", NOW)
    assert tcb.due_items(db, CHART, "en", NOW + timedelta(days=29)) == []     # too soon
    assert tcb.record_answer(db, CHART, cid, "not_sure", NOW + timedelta(days=5))["saved"] is False
    later = NOW + timedelta(days=31)
    again = tcb.due_items(db, CHART, "en", later)
    assert len(again) == 1 and again[0]["reask"] is True
    assert again[0]["question"].startswith("Last time you weren't sure yet.")
    tcb.record_answer(db, CHART, cid, "not_sure", later)                      # still unsure
    assert tcb.due_items(db, CHART, "en", later + timedelta(days=365)) == []  # then stop


def test_not_sure_can_become_a_real_answer():
    db = DB(); cid = _one(db)
    tcb.record_answer(db, CHART, cid, "not_sure", NOW)
    assert tcb.record_answer(db, CHART, cid, "yes", NOW + timedelta(days=2))["outcome"] == "yes"


def test_not_sure_is_neither_a_hit_nor_a_miss_on_the_board():
    claims = [{"id": f"k{i}", "chart_id": f"c{i}", "source": "topic_read", "topic": "money",
               "claim_type": "window", "window_start": "2026-10-14", "window_end": "2026-10-20",
               "engines": {"topic_read": {"kind": "best", "scale": "month"}},
               "checkin_due_at": "2026-10-21", "checkin_sent_at": "2026-10-22", "checkin_channel": "app"}
              for i in range(5)]
    outs = [{"claim_id": "k0", "outcome": "yes", "answered_at": "2026-10-22"},
            {"claim_id": "k1", "outcome": "no", "answered_at": "2026-10-22"},
            {"claim_id": "k2", "outcome": "not_sure", "answered_at": "2026-10-22"},
            {"claim_id": "k3", "outcome": "not_sure", "answered_at": "2026-10-22"}]
    row = next(r for r in ab.build(claims, outs)["final_answers"] if r["source"] == "topic_read")
    assert row["answered"] == 2 and row["not_sure"] == 2 and row["claims"] == 5   # k4 unanswered
    assert row["n"] == 2


# ── D) BOARD ─────────────────────────────────────────────────────────────────
def _tr(i, topic="money", kind="best", chart=None):
    return {"id": f"t{i}", "chart_id": chart or f"chart-{i}", "source": "topic_read", "topic": topic,
            "claim_type": "window", "window_start": f"2026-0{1 + i % 9}-01", "window_end": f"2026-0{1 + i % 9}-20",
            "engines": {"topic_read": {"kind": kind, "scale": "month"}},
            "checkin_due_at": "2026-12-01", "checkin_sent_at": "2026-12-02", "checkin_channel": "app"}


def _o(i, v):
    return {"claim_id": f"t{i}", "outcome": v, "answered_at": "2026-12-03"}


def test_board_small_n_shows_count_never_a_rate():
    claims = [_tr(i) for i in range(10)]
    outs = [_o(i, "yes") for i in range(8)] + [_o(8, "no"), _o(9, "no")]
    b = ab.build(claims, outs)
    for row in [r for r in b["final_answers"] if r["source"] == "topic_read"] + \
               [r for r in b["engines"] if r["engine"].startswith("topic_read")]:
        assert row["n"] == 10 and row["small_n"] is True
        assert row["hit_rate"] is None and row["lift"] is None and row["ci95"] == [None, None]
        assert row["status"] == "Too few answers"


def test_board_rows_split_by_kind_and_compare_to_the_decoy_base_rate():
    claims = ([_tr(i, kind="best") for i in range(40)] + [_tr(100 + i, kind="watch") for i in range(35)]
              + [dict(_tr(200 + i), source="decoy", engines={}) for i in range(40)])
    outs = ([_o(i, "yes") for i in range(36)] + [_o(i, "no") for i in range(36, 40)]          # best 90%
            + [_o(100 + i, "yes") for i in range(10)] + [_o(100 + i, "no") for i in range(10, 35)]  # watch 29%
            + [_o(200 + i, "yes") for i in range(12)] + [_o(200 + i, "no") for i in range(12, 40)])  # decoy 30%
    b = ab.build(claims, outs)
    assert b["baselines"] == {"money": 0.3}
    rows = {r["engine"]: r for r in b["engines"] if r["engine"].startswith("topic_read")}
    assert set(rows) == {"topic_read:best", "topic_read:watch"}
    assert rows["topic_read:best"]["small_n"] is False
    assert rows["topic_read:best"]["hit_rate"] == 0.9 and rows["topic_read:best"]["lift"] == 0.6
    assert rows["topic_read:best"]["status"] == "Beats chance"
    # the misses are reported just as plainly
    assert rows["topic_read:watch"]["hit_rate"] == 0.286
    assert rows["topic_read:watch"]["status"] == "No better than chance"


def test_other_board_rows_keep_their_rates_on_small_n():
    claims = [{"id": f"k{i}", "chart_id": f"c{i}", "source": "ask_explore", "topic": "business",
               "claim_type": "window", "window_start": "2026-11-01", "window_end": "2027-01-31",
               "engines": {}, "checkin_due_at": "2026-01-01"} for i in range(4)]
    outs = [{"claim_id": f"k{i}", "outcome": "yes", "answered_at": "2027-02-03"} for i in range(4)]
    row = ab.build(claims, outs)["final_answers"][0]
    assert row["hit_rate"] == 1.0 and "small_n" not in row         # existing rows unchanged


# ── languages + jargon ───────────────────────────────────────────────────────
def test_four_languages_and_hindi_falls_back_to_english():
    db = DB(); _one(db)
    seen = set()
    for lang in LANGS:
        it = tcb.due_items(db, CHART, lang, NOW)[0]
        assert it["language"] == lang and it["topic_label"] == C.LABEL[lang]["money"]
        assert it["question"] and "{" not in it["question"] and it["question"] not in seen
        seen.add(it["question"])
        assert it["options"][0]["label"] != it["options"][2]["label"]
    for raw in ("hi", "fr", "de", None):
        assert tcb.due_items(db, CHART, raw, NOW)[0]["language"] == "en"


def test_no_jargon_in_any_checkback_string():
    db = DB()
    tcb.record_windows(db, read(watch=("2026-10-22", "2026-10-24")), CHART, TODAY)
    for lang in LANGS:
        for it in tcb.due_items(db, CHART, lang, NOW, limit=3):
            strings = [it["question"], tcb.thanks(lang)] + [o["label"] for o in it["options"]]
            for s in strings:
                assert not _JARGON.search(s), (lang, s)
                assert not re.search(r"[$€₹]|\bprice|\bplan\b|\bpremium|\bsubscri", s, re.I), s
    for table in tcb.TEXTS:
        for lang, v in table.items():
            for s in (v.values() if isinstance(v, dict) and all(isinstance(x, str) for x in v.values()) else
                      [x for d in v.values() for x in d.values()] if isinstance(v, dict) else [v]):
                assert not _JARGON.search(s), (lang, s)


# ── E) PURGE ─────────────────────────────────────────────────────────────────
def test_claims_table_is_in_both_delete_paths_and_outcomes_cascade():
    import main
    assert "prediction_claims" in main._CHART_DERIVED_TABLES
    assert "prediction_claims" in main._ACCOUNT_DELETE_TABLES
    sql = open("sql_outcome_loop.sql").read()
    assert re.search(r"claim_id\s+uuid primary key references public\.prediction_claims\(id\) on delete cascade", sql)


@pytest.mark.live_db
def test_live_schema_has_every_column_this_feature_touches():
    import main
    cols = ("id,chart_id,source,topic,claim_type,window_start,window_end,text_shown,language,"
            "channel,verdict,engines,dedupe_key,checkin_due_at,checkin_sent_at,checkin_channel")
    main.supabase.table("prediction_claims").select(cols).limit(1).execute()
    main.supabase.table("prediction_outcomes").select("claim_id,outcome,note,answered_at,answered_via") \
        .limit(1).execute()


# ── HTTP contract ────────────────────────────────────────────────────────────
@pytest.fixture
def client(monkeypatch):
    import main
    from fastapi.testclient import TestClient
    db = DB()
    monkeypatch.setattr(main, "supabase", db)
    return TestClient(main.app), db, main


def test_endpoints_end_to_end(client):
    c, db, main = client
    # the endpoint uses the real clock, so record a window that has really passed
    tcb.record_windows(db, read(best=("2026-09-14", "2026-09-20"), period_end="2026-10-01"),
                       CHART, date(2026, 9, 1))
    r = c.get(f"/api/v1/chart/{CHART}/topic-checkbacks?language=es")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1 and body["checkbacks"][0]["language"] == "es"
    cid = body["checkbacks"][0]["id"]
    assert c.post(f"/api/v1/chart/{CHART}/topic-checkbacks/{cid}/answer", json={"answer": "maybe"}).status_code == 400
    assert c.post(f"/api/v1/chart/{CHART}/topic-checkbacks/{uuid.uuid4()}/answer", json={"answer": "yes"}).status_code == 404
    ok = c.post(f"/api/v1/chart/{CHART}/topic-checkbacks/{cid}/answer?language=es", json={"answer": "yes"})
    assert ok.status_code == 200 and ok.json()["saved"] is True and ok.json()["thanks"].startswith("Gracias")
    assert c.post(f"/api/v1/chart/{CHART}/topic-checkbacks/{cid}/answer", json={"answer": "no"}).json()["outcome"] == "yes"
    assert c.get(f"/api/v1/chart/{CHART}/topic-checkbacks").json() == {"checkbacks": [], "count": 0}


def test_get_with_missing_table_is_an_empty_list_not_a_500(client, monkeypatch):
    c, db, main = client
    db.missing = True
    r = c.get(f"/api/v1/chart/{CHART}/topic-checkbacks")
    assert r.status_code == 200 and r.json() == {"checkbacks": [], "count": 0}


def test_topic_read_records_in_background_and_survives_a_broken_store(client, monkeypatch):
    c, db, main = client
    import antar_engine.topic_engine as te
    monkeypatch.setattr(main, "_topic_read_compute",
                        lambda *a, **k: read(best=("2026-10-14", "2026-10-20"), period_end="2026-11-05"))
    monkeypatch.setattr(main, "_prac_local_date", lambda tz=None: TODAY)
    main._TOPIC_RECORDED.clear()
    assert c.get(f"/api/v1/chart/{CHART}/topic-read?topic=money&scale=month").status_code == 200
    assert len(db.claims()) == 1
    db.missing, db.t = True, {}
    main._TOPIC_RECORDED.clear()
    r = c.get(f"/api/v1/chart/{CHART}/topic-read?topic=money&scale=month")
    assert r.status_code == 200 and r.json()["topic"] == "money"
