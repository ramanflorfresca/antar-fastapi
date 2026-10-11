"""[horizon-rule 2026-10-11] owner rule: true within the next 12 months -> say so; further out -> 'not yet, slow until X'. One answer per concern."""
from datetime import date

from antar_engine import event_narrator as EN
from antar_engine import speculation_policy as SP
from antar_engine.ask_consultation import is_decision_question


def test_state_open_requires_the_window_to_be_active_now():
    natal = {"score": 90, "gain_indicators": ["a"], "risk_indicators": []}
    assert SP.state(natal, "LIKELY", "", 0) == "open" and SP.state(natal, "LIKELY", "", None) == "open"
    assert SP.state(natal, "LIKELY", "", 8) == "later"          # promised, starts in 8 months: supported, opens X — NOT "open now"
    assert SP.state(natal, "YES", "", -2) == "open" and SP.state(natal, "NOT_YET", "", 8) == "later"


def test_combine_kp_lift_respects_the_horizon():
    assert SP.combine("no", {"verdict": "yes"}, "LIKELY", 8) == "later" and SP.combine("no", {"verdict": "yes"}, "LIKELY", 0) == "open"
    assert SP.combine("no", {"verdict": "yes"}, "LIKELY") == "open"
    assert SP.combine("losses", {"against": [8], "favour": []}, "LIKELY", 0) == "losses"


def test_gold_silver_bullion_questions_are_speculation_but_gold_mine_deals_are_not():
    for q in ("Should I buy gold?", "Is it a good time to invest in gold?", "Should I sell my gold?", "What will gold prices do?", "Should I buy silver coins?"):
        assert SP.SPECULATION_Q.search(q), q
    for q in ("Should I do the gold mine deal?", "Will my gold mining company succeed?", "I wear a gold ring"):
        assert not SP.SPECULATION_Q.search(q), q


def test_gold_answers_say_it_is_the_readers_timing_not_a_price_call():
    assert "does not forecast the price of gold" in SP.asset_note("Should I buy gold?", "en")
    assert "no pronostica el precio del oro" in SP.asset_note("¿Debo comprar oro?", "es")
    assert SP.asset_note("Should I buy stocks?", "en") == ""


def test_good_year_questions_are_decision_questions_like_good_time_ones():
    assert is_decision_question("Is this a good year to buy a house?") == is_decision_question("Is it a good time to invest in real estate?") is True


def test_future_money_events_take_the_window_path_pattern_questions_do_not():
    import main
    for q in ("Will my income increase this year?", "Will I make more money next year than this year?", "Will my savings grow this year?"):
        assert main._ask_money_intent(q) is None, q
    assert main._ask_money_intent("Why is my income unstable?") == "income-flow"
    assert main._ask_money_intent("Where does my money go?") == "expenditure-loss"


def _engine_result(monkeypatch, verdict, start, end, today):
    class V(dict):
        pass
    monkeypatch.setattr("antar_engine.event_evidence.build_whole_board", lambda *a, **k: {})
    monkeypatch.setattr(EN, "compute_event_verdict", lambda board, dt_mode="weighter": {"verdict": verdict, "window": {"start": start, "end": end, "label": "L"}})
    monkeypatch.setattr(EN, "build_reading_sequence_prompt", lambda b, v: "p")
    return EN.run_event_engine({}, {}, {}, "1980-01-01", "money", current_date=today)


def test_promised_event_within_12_months_is_likely_not_not_yet(monkeypatch):
    r = _engine_result(monkeypatch, "promised_building", "2027-06-01", "2027-10-31", date(2026, 10, 11))
    assert r["client_verdict"] == "LIKELY" and r["client_verdict_raw"] == "NOT_YET" and r["horizon_months"] == 8


def test_promised_event_further_out_stays_not_yet(monkeypatch):
    r = _engine_result(monkeypatch, "promised_building", "2029-03-01", "2029-08-31", date(2026, 10, 11))
    assert r["client_verdict"] == "NOT_YET" and r["horizon_months"] == 29


def test_boundary_is_exactly_twelve_months(monkeypatch):
    assert _engine_result(monkeypatch, "promised_building", "2027-10-01", "2028-01-31", date(2026, 10, 11))["client_verdict"] == "LIKELY"
    assert _engine_result(monkeypatch, "promised_building", "2027-11-01", "2028-02-28", date(2026, 10, 11))["client_verdict"] == "NOT_YET"


def test_supported_and_denied_verdicts_are_not_touched(monkeypatch):
    assert _engine_result(monkeypatch, "supported", "2026-08-01", "2027-01-31", date(2026, 10, 11))["client_verdict"] == "YES"
    assert _engine_result(monkeypatch, "not_supported", "2027-06-01", "2027-10-31", date(2026, 10, 11))["client_verdict"] == "NO"
