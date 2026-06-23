"""
kp_rectify.py — honest birth-time rectification with held-out validation.
RUN ON THE MAC VENV:

    cd ~/antarai && source venv311/bin/activate
    python -m antar_engine.kp.kp_rectify

Rectifying a birth time to the events you then test on is circular. This does
it the honest way: repeated random splits — rectify (pick the best time) on a
TRAIN subset, then measure hit-rate + lift on the HELD-OUT TEST subset. If the
out-of-sample test performance clears the bar, rectification generalizes and the
gate can open on it. If only the in-sample fit looks good, it's overfitting and
we say so.

Strictness = ad_pd (the honest discriminator). Search window = recorded time
+- WINDOW_MIN at STEP_MIN resolution. Takes a couple of minutes.
"""

import os
import json
import random
import statistics
from datetime import datetime, timedelta

from .kp_timing import compute_kp_chart, score_event, base_rate, _date_to_jd

_HERE = os.path.dirname(os.path.abspath(__file__))
ROSTER = os.path.join(_HERE, "validation", "kp_natal_events.json")
OUT = os.path.join(_HERE, "validation", "out", "kp_rectify_results.json")

WINDOW_MIN = 15      # search recorded +- 15 min
STEP_MIN = 1
STRICT = "ad_pd"
N_SPLITS = 300
TRAIN_FRAC = 0.6
HIT_BAR = 0.70
LIFT_BAR = 0.20
SEED = 7


def _tol(ev, default):
    t = ev.get("tolerance_months")
    if t is None:
        t = 6 if ev.get("precision") == "year" else default
    return t


def _candidate_times(base_date, base_time):
    base_dt = datetime.strptime(
        f"{base_date} {base_time}",
        "%Y-%m-%d %H:%M" if len(base_time) <= 5 else "%Y-%m-%d %H:%M:%S")
    times = []
    for off in range(-WINDOW_MIN, WINDOW_MIN + 1, STEP_MIN):
        times.append(((base_dt + timedelta(minutes=off)).strftime("%H:%M"), off))
    return times


def _build_matrices(roster):
    """H[t][e] = hit bool (ad_pd), B[t][e] = base rate, for each candidate time."""
    b = roster["birth"]
    default_tol = roster.get("tolerance_months", 3)
    events = roster["events"]
    times = _candidate_times(b["birth_date"], b["birth_time"])

    H, B = {}, {}
    for hhmm, off in times:
        chart = compute_kp_chart(b["birth_date"], hhmm, b["lat"], b["lon"],
                                 tz_offset=b.get("tz_offset"),
                                 timezone=b.get("timezone"))
        hits, bases = [], []
        for ev in events:
            tol = _tol(ev, default_tol)
            sc = score_event(chart, ev["event_type"], ev["actual_date"],
                             loss_house=ev.get("loss_house"), tolerance_months=tol,
                             strong=True, require_csl=True, require_transit=True)
            through = _date_to_jd(ev["actual_date"]) + 400.0
            br = base_rate(chart, ev["event_type"], through,
                           loss_house=ev.get("loss_house"), strictness=STRICT,
                           strong=True, require_transit=True)
            hits.append(1.0 if sc["hits"][STRICT] else 0.0)
            bases.append(br if br is not None else 0.0)
        H[off] = hits
        B[off] = bases
    return times, H, B, events


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def main():
    with open(ROSTER) as f:
        roster = json.load(f)
    random.seed(SEED)

    times, H, B, events = _build_matrices(roster)
    offsets = [off for _, off in times]
    n = len(events)
    idx = list(range(n))

    # in-sample reference at recorded time (off=0)
    rec_hit = _mean(H[0])
    rec_lift = _mean([H[0][e] - B[0][e] for e in idx])

    # full-fit best time (IN-SAMPLE — for reference only, NOT a validation)
    def hit_on(off, subset):
        return _mean([H[off][e] for e in subset])
    full_best = max(offsets, key=lambda o: (hit_on(o, idx), -abs(o)))

    # repeated hold-out: rectify on train, validate on test
    test_hits, test_lifts, chosen = [], [], []
    passes = 0
    n_train = max(1, round(TRAIN_FRAC * n))
    for _ in range(N_SPLITS):
        random.shuffle(idx)
        train, test = idx[:n_train], idx[n_train:]
        if not test:
            continue
        best = max(offsets, key=lambda o: (hit_on(o, train), -abs(o)))
        th = _mean([H[best][e] for e in test])
        tl = _mean([H[best][e] - B[best][e] for e in test])
        test_hits.append(th)
        test_lifts.append(tl)
        chosen.append(best)
        if th >= HIT_BAR and tl >= LIFT_BAR:
            passes += 1

    from collections import Counter
    modal_off, modal_ct = Counter(chosen).most_common(1)[0]
    base_dt = datetime.strptime(f"{roster['birth']['birth_date']} "
                                f"{roster['birth']['birth_time']}",
                                "%Y-%m-%d %H:%M")
    modal_time = (base_dt + timedelta(minutes=modal_off)).strftime("%H:%M")
    full_best_time = (base_dt + timedelta(minutes=full_best)).strftime("%H:%M")

    result = {
        "strictness": STRICT,
        "n_events": n,
        "search_window_min": WINDOW_MIN,
        "recorded_time": {"hit": round(rec_hit, 3), "lift": round(rec_lift, 3)},
        "full_fit_in_sample": {"best_time": full_best_time,
                               "hit": round(hit_on(full_best, idx), 3),
                               "NOTE": "in-sample, NOT a validation"},
        "held_out_validation": {
            "splits": len(test_hits),
            "mean_test_hit": round(_mean(test_hits), 3),
            "mean_test_lift": round(_mean(test_lifts), 3),
            "stdev_test_lift": round(statistics.pstdev(test_lifts), 3)
                if len(test_lifts) > 1 else 0.0,
            "fraction_splits_pass": round(passes / len(test_hits), 3)
                if test_hits else 0.0,
            "modal_rectified_time": modal_time,
            "modal_time_chosen_in": f"{modal_ct}/{len(chosen)} splits",
        },
        "verdict": None,
    }
    mh = result["held_out_validation"]["mean_test_hit"]
    ml = result["held_out_validation"]["mean_test_lift"]
    if mh >= HIT_BAR and ml >= LIFT_BAR:
        result["verdict"] = (f"Rectification GENERALIZES (out-of-sample mean "
                             f"hit {mh}, lift {ml}). Modal time "
                             f"{modal_time}. Gate can open on a rectified time.")
    else:
        result["verdict"] = (f"Does NOT generalize out-of-sample (mean test "
                             f"hit {mh}, lift {ml}). The 1.0 in-sample fit is "
                             "overfitting. KP stays quarantined.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
