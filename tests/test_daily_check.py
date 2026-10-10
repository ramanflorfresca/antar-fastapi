from datetime import date, datetime, timezone

import pytest

from antar_engine import accuracy_board as AB
from antar_engine import daily_check as DC

D = date(2026, 10, 10)
SIG = {"day_energy": {"key": "light", "label": "LIGHTER-TOUCH DAY", "score": 4},
       "verdict_subline": "Strong discipline window — review and lock in, don't launch.", "fallback": False}


def test_day_class_reads_the_engines_own_rating():
    assert DC.day_class(SIG) == {"class": "light", "score": 4, "label": "LIGHTER-TOUCH DAY"}


@pytest.mark.parametrize("bad", [None, {}, {"fallback": True, "day_energy": {"key": "steady"}},
                                 {"pending": True, "day_energy": {"key": "steady"}},
                                 {"day_energy": {"key": "mystery"}}, "x"])
def test_unrated_or_fallback_signals_are_never_recorded(bad):
    assert DC.day_class(bad) is None and DC.build_claim("c1", D, bad) is None


def test_build_claim_shape_and_dedupe_per_chart_per_day():
    c = DC.build_claim("c1", D, SIG, "es-MX")
    assert c["source"] == "daily_check" and c["topic"] == "day" and c["claim_type"] == "day"
    assert c["window_start"] == c["window_end"] == "2026-10-10"
    assert c["engines"]["daily"]["class"] == "light" and c["verdict"] == "LIGHT" and c["language"] == "es"
    assert c["dedupe_key"] == "c1|day|daily_check|2026-10-10|2026-10-10"
    assert DC.build_claim("c1", D, SIG)["dedupe_key"] == c["dedupe_key"]
    assert DC.build_claim("c2", D, SIG)["dedupe_key"] != c["dedupe_key"]


@pytest.mark.parametrize("hour,which", [(0, "yesterday"), (11, "yesterday"), (12, None), (16, None), (17, "today"), (23, "today")])
def test_which_day_window(hour, which):
    assert DC.which_day(datetime(2026, 10, 10, hour, 30)) == which


def test_target_date_and_local_now():
    now = datetime(2026, 10, 10, 1, 0, tzinfo=timezone.utc)
    local = DC.local_now(now, -240)                        # EDT: Oct 9, 9 PM
    assert local.date() == date(2026, 10, 9) and DC.which_day(local) == "today"
    assert DC.target_date(local, "today") == date(2026, 10, 9)
    assert DC.target_date(datetime(2026, 10, 10, 8), "yesterday") == date(2026, 10, 9)
    assert DC.local_now(now, None) == now and DC.local_now(now, "x") == now


def test_card_never_carries_the_engines_rating():
    c = DC.card("id1", D, "today", "en")
    assert c["question"] == "How did today go?" and [o["value"] for o in c["options"]] == ["good", "mixed", "hard"]
    assert "class" not in str(c) and "light" not in str(c).lower().replace("lighter", "")
    assert DC.card("id1", D, "yesterday", "es")["question"] == "¿Cómo te fue ayer?"
    assert DC.RATINGS == {"good": "yes", "mixed": "partly", "hard": "no"}


def _claim(i, cls, chart):
    return {"id": f"c{i}", "chart_id": chart, "source": "daily_check", "engines": {"daily": {"class": cls}}}


def _board(n_each, steady_mean_good, friction_mean_good, charts=40):
    claims, outs = [], []
    k = 0
    for cls, good_share in (("steady", steady_mean_good), ("friction", friction_mean_good)):
        for i in range(n_each):
            claims.append(_claim(k, cls, f"chart-{k % charts}"))
            outs.append({"claim_id": f"c{k}", "outcome": "yes" if i < n_each * good_share else "no"})
            k += 1
    return claims, outs


def test_too_few_answers_never_reports_a_difference_as_a_finding():
    cl, ou = _board(10, 0.9, 0.1)
    s = AB.build(cl, ou)["daily_check"]
    assert s["status"] == "Too few answers" and s["answered"] == 20 and s["asked"] == 20


def test_a_real_gap_with_enough_answers_is_reported_and_holds_in_both_halves():
    cl, ou = _board(120, 0.8, 0.2, charts=60)
    s = AB.build(cl, ou)["daily_check"]
    assert s["status"] == "Steady days rate higher"
    assert s["steady_minus_friction"]["diff"] > 0.5 and s["steady_minus_friction"]["ci95"][0] > 0
    assert all(v is not None and v > 0 for v in s["steady_minus_friction"]["halves"].values())


def test_no_gap_is_reported_as_no_difference_not_hidden():
    cl, ou = _board(120, 0.5, 0.5, charts=60)
    assert AB.build(cl, ou)["daily_check"]["status"] == "No difference yet"


def test_daily_check_never_enters_the_engine_by_topic_cells():
    cl, ou = _board(40, 0.8, 0.2)
    b = AB.build(cl, ou)
    assert b["final_answers"] == [] and b["engines"] == [] and b["health"]["claims"] == 0
    assert b["daily_check"]["by_class"]["steady"]["n"] == 40


def test_not_sure_is_counted_but_not_scored():
    cl = [_claim(1, "steady", "a"), _claim(2, "steady", "b")]
    ou = [{"claim_id": "c1", "outcome": "not_sure"}, {"claim_id": "c2", "outcome": "yes"}]
    s = AB.build(cl, ou)["daily_check"]
    assert s["not_sure"] == 1 and s["answered"] == 1 and s["by_class"]["steady"]["mean_rating"] == 1.0


# ── endpoints ────────────────────────────────────────────────────────────────
@pytest.fixture()
def m():
    from dotenv import load_dotenv
    load_dotenv()
    import main
    return main


H = {"Authorization": "Bearer x"}


def _client(m, monkeypatch, hour):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    monkeypatch.setattr(m, "_oc_owned_chart", lambda u, c: c == "mine")
    monkeypatch.setattr(DC, "local_now", lambda now, tz: datetime(2026, 10, 10, hour, 30))
    return TestClient(m.app)


def test_get_requires_ownership(m, monkeypatch):
    c = _client(m, monkeypatch, 18)
    assert c.get("/api/v1/daily-check/theirs", headers=H).status_code == 403


def test_get_is_unavailable_midday_and_never_computes_a_signal(m, monkeypatch):
    c = _client(m, monkeypatch, 14)
    async def boom(*a, **k):
        raise AssertionError("signal must not be fetched outside the window")
    monkeypatch.setattr(m, "_dc_signal", boom)
    assert c.get("/api/v1/daily-check/mine", headers=H).json() == {"available": False}


def test_get_records_the_claim_from_the_days_signal_and_hides_the_rating(m, monkeypatch):
    from antar_engine import outcomes as oc
    c = _client(m, monkeypatch, 18)
    recorded = {}
    async def sig(chart_id, language, d_iso):
        return dict(SIG)
    monkeypatch.setattr(m, "_dc_signal", sig)
    monkeypatch.setattr(m, "_dc_find_claim", lambda cid, d: None)
    monkeypatch.setattr(m, "_dc_is_answered", lambda i: False)
    monkeypatch.setattr(oc, "record_claim", lambda sb, row: recorded.setdefault("row", row) and "claim-1")
    r = c.get("/api/v1/daily-check/mine?language=en&tz_offset=-240", headers=H).json()
    assert r["available"] is True and r["claim_id"] == "claim-1" and r["day"] == "today" and r["date"] == "2026-10-10"
    assert r["question"] == "How did today go?" and [o["value"] for o in r["options"]] == ["good", "mixed", "hard"]
    assert "light" not in str(r).lower().replace("lighter", "") and "class" not in r
    assert recorded["row"]["source"] == "daily_check" and recorded["row"]["engines"]["daily"]["class"] == "light"


def test_get_yesterday_in_the_morning(m, monkeypatch):
    from antar_engine import outcomes as oc
    c = _client(m, monkeypatch, 9)
    seen = {}
    async def sig(chart_id, language, d_iso):
        seen["d"] = d_iso
        return dict(SIG)
    monkeypatch.setattr(m, "_dc_signal", sig)
    monkeypatch.setattr(m, "_dc_find_claim", lambda cid, d: None)
    monkeypatch.setattr(m, "_dc_is_answered", lambda i: False)
    monkeypatch.setattr(oc, "record_claim", lambda sb, row: "claim-y")
    r = c.get("/api/v1/daily-check/mine", headers=H).json()
    assert r["day"] == "yesterday" and r["date"] == "2026-10-09" and seen["d"] == "2026-10-09"


def test_get_does_nothing_when_the_signal_is_a_fallback(m, monkeypatch):
    from antar_engine import outcomes as oc
    c = _client(m, monkeypatch, 18)
    async def sig(chart_id, language, d_iso):
        return {"fallback": True, "day_energy": {"key": "steady", "score": 10}}
    monkeypatch.setattr(m, "_dc_signal", sig)
    monkeypatch.setattr(m, "_dc_find_claim", lambda cid, d: None)
    monkeypatch.setattr(oc, "record_claim", lambda sb, row: (_ for _ in ()).throw(AssertionError("must not record")))
    assert c.get("/api/v1/daily-check/mine", headers=H).json() == {"available": False}


def test_get_reports_answered_and_does_not_ask_twice(m, monkeypatch):
    c = _client(m, monkeypatch, 18)
    monkeypatch.setattr(m, "_dc_find_claim", lambda cid, d: {"id": "claim-1", "chart_id": cid, "window_end": d})
    monkeypatch.setattr(m, "_dc_is_answered", lambda i: True)
    assert c.get("/api/v1/daily-check/mine", headers=H).json() == {"available": False, "answered": True}


def test_answer_maps_to_the_outcome_enum_and_checks_the_source_and_owner(m, monkeypatch):
    from fastapi.testclient import TestClient
    from antar_engine import outcomes as oc
    monkeypatch.setattr(m, "verify_token", lambda a: "user-1")
    monkeypatch.setattr(m, "_oc_owned_chart", lambda u, c: c == "mine")
    saved = {}
    monkeypatch.setattr(oc, "record_outcome", lambda sb, cid, outcome, note=None, via="app": saved.update(cid=cid, outcome=outcome, via=via) or True)

    class _Q:
        def __init__(self, rows): self.rows = rows
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: pass
            r = R(); r.data = self.rows; return r

    rows = {"v": [{"chart_id": "mine", "source": "daily_check", "language": "es"}]}
    monkeypatch.setattr(m.supabase, "table", lambda name: _Q(rows["v"]))
    c = TestClient(m.app)
    assert c.post("/api/v1/daily-check/k1/answer", json={"answer": "great"}, headers=H).status_code == 400
    r = c.post("/api/v1/daily-check/k1/answer", json={"answer": "hard"}, headers=H)
    assert r.status_code == 200 and saved == {"cid": "k1", "outcome": "no", "via": "app"} and "Gracias" in r.json()["thanks"]
    rows["v"] = [{"chart_id": "mine", "source": "ask_explore", "language": "en"}]
    assert c.post("/api/v1/daily-check/k1/answer", json={"answer": "good"}, headers=H).status_code == 404
    rows["v"] = [{"chart_id": "theirs", "source": "daily_check", "language": "en"}]
    assert c.post("/api/v1/daily-check/k1/answer", json={"answer": "good"}, headers=H).status_code == 404
