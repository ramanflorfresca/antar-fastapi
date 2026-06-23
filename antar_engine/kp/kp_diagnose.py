"""
kp_diagnose.py — timing diagnostics. RUN ON THE MAC VENV:

    cd ~/antarai && source venv311/bin/activate
    python -m antar_engine.kp.kp_diagnose

Three views over kp_natal_events.json:
  1. Per-event table at the stated birth time (CSL, gate pass, MD/AD/PD sigs, hit)
  2. any2 hit-rate WITH vs WITHOUT the cuspal-sub-lord gate
     (isolates whether the time-sensitive gate is the bottleneck)
  3. Birth-time sweep +-40 min (step 4 min): any2 hit-rate + lift at each time
     (a clear nearby peak => birth-time rectification signal)

Read-only. Touches nothing.
"""

import os
import json
from datetime import datetime, timedelta

from .kp_timing import (
    compute_kp_chart, score_event, base_rate, _date_to_jd,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
ROSTER = os.path.join(_HERE, "validation", "kp_natal_events.json")


def _load():
    with open(ROSTER) as f:
        return json.load(f)


def _tol(ev, default):
    t = ev.get("tolerance_months")
    if t is None:
        t = 6 if ev.get("precision") == "year" else default
    return t


def _evaluate(roster, hhmm, require_csl=True, strictness="any2",
              require_transit=True):
    b = roster["birth"]
    chart = compute_kp_chart(b["birth_date"], hhmm, b["lat"], b["lon"],
                             tz_offset=b.get("tz_offset"), timezone=b.get("timezone"))
    default_tol = roster.get("tolerance_months", 3)
    hits, lifts, rows = 0, [], []
    for ev in roster["events"]:
        tol = _tol(ev, default_tol)
        sc = score_event(chart, ev["event_type"], ev["actual_date"],
                         loss_house=ev.get("loss_house"), tolerance_months=tol,
                         strong=True, require_csl=require_csl,
                         require_transit=require_transit)
        through = _date_to_jd(ev["actual_date"]) + 400.0
        br = base_rate(chart, ev["event_type"], through,
                       loss_house=ev.get("loss_house"), strictness=strictness,
                       strong=True, require_transit=require_transit)
        hit = sc["hits"][strictness]
        hits += 1 if hit else 0
        if br is not None:
            lifts.append((1.0 if hit else 0.0) - br)
        rows.append((ev["id"], sc, hit))
    n = len(roster["events"])
    return hits / n, (sum(lifts) / len(lifts) if lifts else None), rows


def main():
    roster = _load()
    b = roster["birth"]
    base_time = b["birth_time"]

    print(f"Birth: {b['birth_date']} {base_time} {b.get('place','')}\n")

    # 1) per-event table at stated time
    hr, lift, rows = _evaluate(roster, base_time, require_csl=True)
    print(f"{'event':<18}{'cusp':>4} {'CSL':<8}{'gate':<5} "
          f"{'MD':<8}{'AD':<8}{'PD':<8}{'any2'}")
    for eid, sc, hit in rows:
        a = sc["at_date"]
        def mark(p): return (p or "-") + ("*" if p in sc["significators"] else "")
        print(f"{eid:<18}{sc['primary_cusp']:>4} {str(sc['cuspal_sub_lord']):<8}"
              f"{'Y' if sc['csl_gate_pass'] else 'n':<5} "
              f"{mark(a['MD']):<8}{mark(a['AD']):<8}{mark(a['PD']):<8}"
              f"{'HIT' if hit else 'miss'}")
    print(f"\n  any2 hit-rate (CSL gate ON):  {hr:.3f}  mean-lift {lift:+.3f}"
          "   (* = significator)")

    # 2) ablations: CSL gate off, transit off
    hr_nocsl, lift_nocsl, _ = _evaluate(roster, base_time, require_csl=False)
    hr_notr, lift_notr, _ = _evaluate(roster, base_time, require_transit=False)
    print(f"  any2 hit-rate (CSL gate OFF): {hr_nocsl:.3f}  mean-lift {lift_nocsl:+.3f}")
    print(f"  any2 hit-rate (transit OFF): {hr_notr:.3f}  mean-lift {lift_notr:+.3f}")
    if hr_nocsl - hr >= 0.25:
        print("  -> the CSL gate is the bottleneck (time-sensitive -> suspect "
              "birth time or cusp house-group).")

    # 3) birth-time sweep
    print("\nBirth-time sweep (any2, CSL gate ON):")
    base_dt = datetime.strptime(f"{b['birth_date']} {base_time}",
                                "%Y-%m-%d %H:%M" if len(base_time) <= 5
                                else "%Y-%m-%d %H:%M:%S")
    best = (hr, base_time)
    for off in range(-40, 44, 4):
        t = (base_dt + timedelta(minutes=off)).strftime("%H:%M")
        h, lf, _ = _evaluate(roster, t, require_csl=True)
        flag = "  <= stated" if off == 0 else ("  <= peak" if h > best[0] else "")
        if h > best[0]:
            best = (h, t)
        print(f"  {t}  ({off:+3d}m)  hit {h:.3f}  lift {lf:+.3f}{flag}")
    print(f"\nBest in window: {best[1]} hit {best[0]:.3f}")


if __name__ == "__main__":
    main()
