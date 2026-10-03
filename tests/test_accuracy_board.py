"""Accuracy board (outcome loop week 3): honest statuses, engine rule, holdout."""
from antar_engine import accuracy_board as ab


def _claim(i, topic="business", src="ask_explore", start="2026-11-01", end="2027-01-31",
           engines=None, sent=True):
    return {"id": f"k{i}", "chart_id": f"chart-{i}", "source": src, "topic": topic,
            "claim_type": "window", "window_start": start, "window_end": end,
            "engines": engines or {}, "checkin_due_at": "2026-01-01",
            "checkin_sent_at": "2026-02-01" if sent else None, "checkin_channel": "push"}


def _outs(n_yes, n_no, offset=0, ids=None):
    ids = ids or [f"k{i}" for i in range(offset, offset + n_yes + n_no)]
    return ([{"claim_id": ids[i], "outcome": "yes", "answered_at": "2027-02-03"} for i in range(n_yes)]
            + [{"claim_id": ids[n_yes + i], "outcome": "no", "answered_at": "2027-02-03"} for i in range(n_no)])


def test_too_few_answers_and_no_baseline():
    claims = [_claim(i) for i in range(40)]
    b = ab.build(claims, _outs(8, 2))
    row = b["final_answers"][0]
    assert row["answered"] == 10 and row["status"] == "Too few answers"
    b = ab.build(claims, _outs(30, 10))
    row = b["final_answers"][0]
    assert row["answered"] == 40 and row["hit_rate"] == 0.75
    assert row["status"] == "No baseline yet" and row["lift"] is None


def test_beats_chance_needs_a_decoy_baseline_and_both_halves():
    real = [_claim(i) for i in range(80)]
    decoys = [_claim(100 + i, src="decoy") for i in range(40)]
    outs = _outs(72, 8, ids=[f"k{i}" for i in range(80)])                 # 90% hit
    outs += _outs(12, 28, ids=[f"k{100 + i}" for i in range(40)])         # 30% base rate
    b = ab.build(real + decoys, outs)
    row = b["final_answers"][0]
    assert b["baselines"] == {"business": 0.3}
    assert row["lift"] == 0.6 and row["status"] == "Beats chance"


def test_no_better_than_chance():
    real = [_claim(i) for i in range(60)]
    decoys = [_claim(100 + i, src="decoy") for i in range(40)]
    outs = _outs(30, 30, ids=[f"k{i}" for i in range(60)])                # 50% hit
    outs += _outs(20, 20, ids=[f"k{100 + i}" for i in range(40)])         # 50% base rate
    assert ab.build(real + decoys, outs)["final_answers"][0]["status"] == "No better than chance"


def test_unreliable_when_few_people_answer():
    claims = [_claim(i) for i in range(200)]                              # 200 sent
    row = ab.build(claims, _outs(30, 10))["final_answers"][0]             # 40 answered = 20%
    assert row["status"] == "Unreliable"


def test_engine_rule_positive_needs_overlapping_window():
    c = _claim(1, engines={
        "event_engine": {"client": "NOT_YET", "window": "Nov 2026 – Jan 2027"},   # overlaps → positive
        "convergence": {"verdict": "LIKELY", "window": "Oct 2026"},               # no overlap → negative
        "kp": {"lean": "conditional"}})
    calls = ab.engine_calls(c)
    assert calls == {"event_engine": "positive", "convergence": "negative", "kp": "conditional"}


def test_engine_hits_follow_the_rule():
    c = _claim(1, engines={"event_engine": {"client": "NOT_YET", "window": "Nov 2026 – Jan 2027"},
                           "convergence": {"verdict": "LIKELY", "window": "Oct 2026"}})
    b = ab.build([c], [{"claim_id": "k1", "outcome": "yes", "answered_at": "2027-02-03"}])
    by = {r["engine"]: r for r in b["engines"]}
    assert by["event_engine"]["hit_rate"] == 1.0 and by["convergence"]["hit_rate"] == 0.0


def test_not_sure_is_counted_but_not_scored_and_windows_are_counted():
    claims = [_claim(1), _claim(2), _claim(3, start="2027-06-01", end="2027-10-31")]
    outs = [{"claim_id": "k1", "outcome": "not_sure", "answered_at": "2027-02-03"},
            {"claim_id": "k2", "outcome": "partly", "answered_at": "2027-02-03"},
            {"claim_id": "k3", "outcome": "yes", "answered_at": "2027-11-03"}]
    row = ab.build(claims, outs)["final_answers"][0]
    assert row["not_sure"] == 1 and row["answered"] == 2 and row["hit_rate"] == 0.75
    assert row["distinct_windows"] == 2


def test_holdout_halves_are_deterministic_and_wilson_sane():
    assert ab.half_of("chart-1") == ab.half_of("chart-1")
    assert {ab.half_of(f"chart-{i}") for i in range(20)} == {"A", "B"}
    lo, hi = ab.wilson(45, 50)
    assert 0.78 < lo < 0.9 < hi <= 1.0 and ab.wilson(0, 0) == (None, None)


def test_endpoint_is_admin_gated_and_page_is_served():
    from dotenv import load_dotenv
    load_dotenv()
    import main
    from fastapi.testclient import TestClient
    c = TestClient(main.app)
    assert c.get("/api/v1/admin/accuracy-board").status_code == 401
    page = c.get("/admin/accuracy")
    assert page.status_code == 200 and "Accuracy board" in page.text
