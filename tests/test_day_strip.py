"""[day-strip 2026-10-15] 7 back / today / 7 ahead, shaped only from the deterministic day score."""
from datetime import date, timedelta

from antar_engine import day_strip as DS
from antar_engine.daily_v2 import day_energy

TODAY = date(2026, 10, 14)


def _days(scores):
    # scores: {offset: score}
    return [{"date": (TODAY + timedelta(days=o)).isoformat(), "score": s} for o, s in scores.items()]


def test_fifteen_days_in_order_with_kinds():
    p = DS.build_strip(_days({o: 5 for o in range(-7, 8)}), TODAY)
    assert [d["offset"] for d in p["days"]] == list(range(-7, 8))
    kinds = [d["kind"] for d in p["days"]]
    assert kinds.count("past") == 7 and kinds.count("today") == 1 and kinds.count("future") == 7


def test_each_chip_is_the_cards_own_day_energy_so_it_cannot_contradict_it():
    for sc in range(0, 11):
        d = DS.build_strip(_days({0: sc}), TODAY)["days"][7]
        assert d["energy"]["key"] == day_energy({"score": sc})["key"]
    assert DS.build_strip(_days({0: 3}), TODAY)["days"][7]["energy"]["key"] == "friction"
    assert DS.build_strip(_days({0: 4}), TODAY)["days"][7]["energy"]["key"] == "light"
    assert DS.build_strip(_days({0: 7}), TODAY)["days"][7]["energy"]["key"] == "steady"


def test_past_days_are_labelled_recomputed_and_future_live():
    p = DS.build_strip(_days({-3: 8, 3: 8}), TODAY)
    by = {d["offset"]: d for d in p["days"]}
    assert by[-3]["source"] == "recomputed" and by[3]["source"] == "live"


def test_a_missing_day_is_no_reading_never_invented():
    p = DS.build_strip(_days({0: 5}), TODAY)
    miss = [d for d in p["days"] if d["offset"] != 0]
    assert all(d["status"] == "no_reading" and "energy" not in d for d in miss)


def test_best_and_care_ahead_point_at_real_future_days():
    p = DS.build_strip(_days({1: 9, 2: 2, 3: 5, -1: 10}), TODAY)
    assert p["best_ahead"] == (TODAY + timedelta(days=1)).isoformat()
    assert p["care_ahead"] == (TODAY + timedelta(days=2)).isoformat()


def test_garbage_input_never_raises():
    assert DS.build_strip([{"date": "nope", "score": 1}, None, {"date": "2026-10-14"}], TODAY)["days"][7]["status"] == "no_reading"
    assert DS.build_strip(None, TODAY)["best_ahead"] is None


def test_spanish_labels():
    d = DS.build_strip(_days({0: 8}), TODAY, "es")["days"][7]
    assert d["energy"]["label"] == "DÍA ESTABLE"
