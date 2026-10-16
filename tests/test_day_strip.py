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


def _wk(scores, start=date(2026, 10, 15)):
    return [{"date": (start + timedelta(days=i)).isoformat(), "score": s} for i, s in enumerate(scores)]


def test_week_line_names_best_and_slower_day_with_reasons():
    scores = [5, 4, 2, 8, 5, 6, 5]          # Oct 15 .. 21: day 2 (Oct 17) tough, day 3 (Oct 18) best
    out = DS.build_strip(_wk(scores), date(2026, 10, 15), "en")
    wl = out["week_line"]
    assert wl["best"]["label"] == "Sun Oct 18" and "strongest day" in wl["best"]["reason_plain"]
    assert wl["care"]["label"] == "Sat Oct 17" and "avoid signing" in wl["care"]["reason_plain"]
    assert wl["text"] == "Best day Sun Oct 18. Slower day Sat Oct 17."
    tags = {x["date"]: x.get("tag") for x in out["days"]}
    assert tags["2026-10-18"] == "best" and tags["2026-10-17"] == "slower"
    assert [l["key"] for l in out["legend"]] == ["steady", "light", "friction"]


def test_no_slower_day_named_when_none_is_tough():
    out = DS.build_strip(_wk([5, 5, 6, 8, 5, 6, 5]), date(2026, 10, 15), "en")
    assert out["week_line"]["care"] is None and "Slower" not in out["week_line"]["text"]


def test_no_best_day_named_when_nothing_stands_out():
    out = DS.build_strip(_wk([5, 5, 5, 5, 5, 5, 5]), date(2026, 10, 15), "en")
    assert out["week_line"]["best"] is None and out["week_line"]["text"] is None


def test_week_line_spanish():
    out = DS.build_strip(_wk([5, 4, 2, 8, 5, 6, 5]), date(2026, 10, 15), "es")
    assert out["week_line"]["text"].startswith("Mejor día dom oct 18")
