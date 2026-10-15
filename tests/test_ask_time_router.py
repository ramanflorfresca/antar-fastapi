from datetime import date, timedelta

from antar_engine import ask_time_router as R

TODAY = date(2026, 10, 14)


def _daily(money_state="volatile", spec_tone="risk", work_state="steady", score=7, window=True):
    d = {"score": score,
         "domains": [{"key": "work", "label": "Career", "state": work_state, "line": "Work is steady today — protect blocks of focus time."},
                     {"key": "money", "label": "Money", "state": money_state, "line": "Money moves BOTH ways today — gain and loss are both live."},
                     {"key": "body", "label": "Health", "state": "steady", "line": "Body is steady today."}],
         "day_map": [{"key": "speculation", "label": "Ventures & risk", "tone": spec_tone,
                      "line": "Risk runs against you today — a creative or joint-money bet is prone to unravel."}]}
    if window:
        d["decision"] = {"window": {"best": "12:16 PM – 1:05 PM", "avoid": "12:41 PM – 2:04 PM"}}
    return d


def _u(**k):
    base = {"intent": "how", "area": "income_money", "subject": "self", "horizon_days": 1, "start_offset_days": 0, "confidence": 0.8,
            "crisis": False, "gambling": False, "needs_clarification": True}
    base.update(k)
    return base


def test_the_hint_only_fires_on_a_time_word():
    for q in ("How is money tomorrow?", "how are the next 4 days", "best day this month for a pitch", "¿cómo está mañana el dinero?"):
        assert R.TIME_HINT.search(q), q
    assert not R.TIME_HINT.search("Will I get the job?")


def test_the_plan_reads_area_intent_and_horizon_and_ignores_the_clarify_flag():
    p = R.plan(_u(), "q", TODAY)
    assert p["mode"] == "day" and p["domain"] == "money" and p["dates"] == [TODAY]
    assert R.plan(_u(start_offset_days=1), "q", TODAY)["dates"] == [TODAY + timedelta(days=1)]
    r = R.plan(_u(horizon_days=4), "q", TODAY)
    assert r["mode"] == "range" and len(r["dates"]) == 4
    b = R.plan(_u(intent="which", horizon_days=31), "q", TODAY)
    assert b["mode"] == "best" and len(b["dates"]) == 31


def test_what_must_never_be_routed():
    assert R.plan(_u(crisis=True), "q", TODAY) is None                       # crisis stays with the full Ask
    assert R.plan(_u(intent="yes_no"), "q", TODAY) is None                   # yes/no stays with the yes/no engine
    assert R.plan(_u(area="reunion_ex"), "q", TODAY) is None and R.plan(_u(area="separation"), "q", TODAY) is None
    assert R.plan(_u(area="children_conception"), "q", TODAY) is None
    assert R.plan(_u(subject="partner"), "q", TODAY) is None                 # someone else's chart
    assert R.plan(_u(horizon_days=None), "q", TODAY) is None and R.plan(_u(horizon_days=200), "q", TODAY) is None
    assert R.plan(_u(confidence=0.3), "q", TODAY) is None and R.plan(None, "q", TODAY) is None


def test_a_single_day_answer_is_the_days_own_line_for_that_area_with_one_best_and_one_avoid_window():
    p = R.plan(_u(), "q", TODAY)
    out = R.compose(p, {TODAY: _daily()}, TODAY, "en")
    assert out["read"].startswith("Money moves BOTH ways today — gain and loss are both live.")      # the Today detail's own line
    assert "12:41 PM – 2:04 PM" in out["read"] and out["source"] == "daily_days" and out["route"] == "day"


def test_another_dates_line_does_not_say_today():
    tm = TODAY + timedelta(days=1)
    out = R.compose(R.plan(_u(start_offset_days=1), "q", TODAY), {tm: _daily()}, TODAY, "en")
    assert "tomorrow" in out["read"].lower() and "today" not in out["read"].lower()
    far = TODAY + timedelta(days=3)
    out = R.compose({"mode": "day", "domain": "money", "gamble": False, "dates": [far]}, {far: _daily()}, TODAY, "en")
    assert "that day" in out["read"] and "today" not in out["read"].lower()
    assert "mañana" in R.retime("Hoy el dinero se mueve.", tm, TODAY, "es")


def test_a_speculation_answer_always_carries_the_guardrail_and_never_a_promise():
    p = R.plan(_u(area="speculation_betting", gambling=True), "q", TODAY)
    for tone in ("risk", "opportunity", "mixed"):
        out = R.compose(p, {TODAY: _daily(spec_tone=tone)}, TODAY, "en")
        assert "not a promise" in out["read"] and "afford to lose" in out["read"]
        assert "guaranteed" not in out["read"].lower() and "will win" not in out["read"].lower()
    assert "Risk runs against you" in R.compose(p, {TODAY: _daily(spec_tone="risk")}, TODAY, "en")["read"]


def test_next_days_names_one_best_and_one_care_day_and_never_a_clock_strip():
    ds = [TODAY + timedelta(days=i) for i in range(4)]
    per = {ds[0]: _daily(work_state="steady", score=7), ds[1]: _daily(work_state="caution", score=3),
           ds[2]: _daily(work_state="favorable", score=9), ds[3]: _daily(work_state="caution", score=1)}
    out = R.compose({"mode": "range", "domain": "work", "gamble": False, "dates": ds}, per, TODAY, "en")
    assert "Best: Fri Oct 16." in out["read"] and "Take care: Sat Oct 17." in out["read"]      # the care day is the weakest of the two
    assert ":" not in out["read"].replace("Today:", "").replace("Tomorrow:", "").replace("Fri Oct 16:", "").replace("Sat Oct 17:", "").replace("Best:", "").replace("Take care:", "")


def test_best_day_picks_the_strongest_day_and_names_the_day_to_take_care_on():
    ds = [TODAY + timedelta(days=i) for i in range(5)]
    per = {ds[0]: _daily(money_state="steady", score=5), ds[1]: _daily(money_state="favorable", score=9), ds[2]: _daily(money_state="caution", score=2),
           ds[3]: _daily(money_state="favorable", score=6), ds[4]: _daily(money_state="volatile", score=4)}
    out = R.compose({"mode": "best", "domain": "money", "gamble": False, "dates": ds}, per, TODAY, "en")
    assert out["read"].startswith("The best day for money and income is tomorrow.") and "Take care on Fri Oct 16." in out["read"]
    flat = {d: _daily(money_state="steady") for d in ds}
    assert "No day stands out" in R.compose({"mode": "best", "domain": "money", "gamble": False, "dates": ds}, flat, TODAY, "en")["read"]


def test_no_usable_day_falls_back_to_the_full_ask():
    assert R.compose(R.plan(_u(), "q", TODAY), {}, TODAY, "en") is None
    assert R.compose(R.plan(_u(), "q", TODAY), {TODAY: {"pending": True}}, TODAY, "en") is None
    assert R.compose(R.plan(_u(area="foreign_travel_visa"), "q", TODAY), {TODAY: _daily()}, TODAY, "en") is None      # no travel line that day


def test_spanish_answers_use_spanish_connectors():
    out = R.compose({"mode": "range", "domain": "work", "gamble": False, "dates": [TODAY]}, {TODAY: _daily(work_state="favorable")}, TODAY, "es")
    assert "Hoy: favorable." in out["read"]
