"""
kp_backtest.py  —  Agent 4: validation / backtest harness (THE GATE)
====================================================================

KP is QUARANTINED behind this gate. No KP output reaches a user until the gate
passes AND Raman approves — same discipline as the past-events engine.

This harness consumes a binary-outcome validation set (past questions with KNOWN
yes/no + rough timing), scores verdict hit-rate and timing error, and writes a
persisted gate-status flag that the integration layer (A5) MUST check.

----------------------------------------------------------------------------
GATE RULE
----------------------------------------------------------------------------
  PASS_THRESHOLD = 0.70 binary hit-rate on the validation set.
  'conditional' verdicts count as MISSES for the strict binary score (reported
  separately so they can be inspected). The gate opens only when:
      hit_rate >= PASS_THRESHOLD  AND  n_cases >= MIN_CASES.

----------------------------------------------------------------------------
VALIDATION SET FORMAT  (validation/kp_binary_validation.json)
----------------------------------------------------------------------------
{
  "tolerance_months": 3,
  "cases": [
    {
      "id": "deal-2025-03",
      "mode": "horary",              # "horary" | "natal"
      "question_type": "gain",       # key in kp_significators.QUESTION_TYPES, or "loss"
      "loss_house": null,            # required only if question_type == "loss"
      "number": 74,                  # 1..249, horary mode only
      "asked_at": "2025-03-04 14:30",# local time of the question (horary)
      "lat": 28.6139, "lon": 77.2090, "tz_offset": 5.5,
      "known_outcome": "yes",        # "yes" | "no"
      "actual_date": "2025-05",      # rough YYYY-MM, optional (timing scoring)
      "notes": "client signed"
    },
    {
      "id": "marriage-natal",
      "mode": "natal",
      "question_type": "marriage",
      "birth_date": "1988-07-12", "birth_time": "09:20",
      "lat": 19.0760, "lon": 72.8777, "tz_offset": 5.5,
      "known_outcome": "yes", "actual_date": "2016-12"
    }
  ]
}

A starter template + this schema live in validation/. Until a real set is
provided the gate stays RED (run_backtest returns passed=False, n=0).
"""

import os
import json
import csv
import sys
from datetime import datetime

PASS_THRESHOLD = 0.70
MIN_CASES = 8  # don't open the gate on a trivially small sample

_HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATION_DIR = os.path.join(_HERE, "validation")
DEFAULT_ROSTER = os.path.join(VALIDATION_DIR, "kp_binary_validation.json")
OUT_DIR = os.path.join(VALIDATION_DIR, "out")
GATE_STATUS_PATH = os.path.join(VALIDATION_DIR, "kp_gate_status.json")


def _months_between(ym_a, ym_b):
    """Rough month distance between 'YYYY-MM' (or 'YYYY-MM-DD') strings."""
    def parse(s):
        parts = str(s).split("-")
        return int(parts[0]) * 12 + int(parts[1])
    try:
        return abs(parse(ym_a) - parse(ym_b))
    except Exception:
        return None


def _predict_case(case):
    """Run the appropriate KP engine for one case; return its verdict bundle."""
    mode = case.get("mode", "horary")
    qtype = case["question_type"]
    loss_house = case.get("loss_house")
    if mode == "horary":
        from .kp_horary import answer_horary
        dt = datetime.strptime(case["asked_at"].strip(),
                               "%Y-%m-%d %H:%M" if len(case["asked_at"].strip()) <= 16
                               else "%Y-%m-%d %H:%M:%S")
        return answer_horary(
            case["number"], qtype, dt,
            case["lat"], case["lon"], case["tz_offset"],
            loss_house=loss_house,
        )
    elif mode == "natal":
        from .kp_chart import compute_kp_chart
        from .kp_significators import verdict
        chart = compute_kp_chart(
            case["birth_date"], case["birth_time"],
            case["lat"], case["lon"],
            tz_offset=case.get("tz_offset"), timezone=case.get("timezone"),
        )
        v = verdict(chart, qtype, loss_house=loss_house)
        return {"verdict": v["verdict"], "confidence": v["confidence"],
                "drivers": v["drivers"], "window": None, "debug": v["debug"]}
    raise ValueError(f"unknown mode {mode!r} (expected 'horary' or 'natal')")


def run_backtest(roster_path=DEFAULT_ROSTER, write=True):
    """
    Score the validation set. Returns a scorecard dict and (if write) persists
    results + the gate-status flag.
    """
    if not os.path.exists(roster_path):
        scorecard = {
            "passed": False, "reason": "no validation set provided",
            "roster_path": roster_path, "n_cases": 0, "hit_rate": None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if write:
            _write_gate_status(scorecard)
        return scorecard

    with open(roster_path) as f:
        roster = json.load(f)
    cases = roster.get("cases", [])
    tol = roster.get("tolerance_months", 3)

    rows = []
    hits = conditionals = timing_scored = timing_within = 0
    for case in cases:
        try:
            pred = _predict_case(case)
        except Exception as e:  # a broken case must not silently pass the gate
            rows.append({"id": case.get("id"), "error": str(e),
                         "predicted": None, "known": case.get("known_outcome"),
                         "hit": False})
            continue
        predicted = pred["verdict"]
        known = case.get("known_outcome")
        hit = (predicted == known)
        if predicted == "conditional":
            conditionals += 1
            hit = False  # strict: conditional != a clean binary hit
        if hit:
            hits += 1

        timing_err = None
        win = pred.get("window") or {}
        if case.get("actual_date") and win.get("end"):
            timing_err = _months_between(win["end"], case["actual_date"])
            if timing_err is not None:
                timing_scored += 1
                if timing_err <= tol:
                    timing_within += 1

        rows.append({
            "id": case.get("id"), "mode": case.get("mode"),
            "question_type": case.get("question_type"),
            "predicted": predicted, "known": known, "hit": hit,
            "confidence": pred.get("confidence"),
            "timing_error_months": timing_err,
        })

    n = len(cases)
    hit_rate = (hits / n) if n else None
    passed = bool(n >= MIN_CASES and hit_rate is not None
                  and hit_rate >= PASS_THRESHOLD)

    scorecard = {
        "passed": passed,
        "reason": ("gate open" if passed else
                   f"hit_rate {hit_rate} < {PASS_THRESHOLD} or n {n} < {MIN_CASES}"),
        "roster_path": roster_path,
        "n_cases": n,
        "hits": hits,
        "conditionals": conditionals,
        "hit_rate": hit_rate,
        "threshold": PASS_THRESHOLD,
        "min_cases": MIN_CASES,
        "timing_scored": timing_scored,
        "timing_within_tolerance": timing_within,
        "tolerance_months": tol,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(os.path.join(OUT_DIR, "kp_backtest_results.json"), "w") as f:
            json.dump({"scorecard": scorecard, "rows": rows}, f, indent=2)
        if rows:
            keys = sorted({k for r in rows for k in r})
            with open(os.path.join(OUT_DIR, "kp_backtest_results.csv"), "w",
                      newline="") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                w.writerows(rows)
        _write_gate_status(scorecard)

    return scorecard


def _write_gate_status(scorecard):
    os.makedirs(VALIDATION_DIR, exist_ok=True)
    flag = {k: scorecard.get(k) for k in
            ("passed", "reason", "n_cases", "hit_rate", "threshold", "timestamp")}
    with open(GATE_STATUS_PATH, "w") as f:
        json.dump(flag, f, indent=2)


def is_gate_open():
    """
    The single source of truth A5 MUST consult before surfacing KP anywhere.
    Returns False unless a backtest has run and recorded passed=True.
    """
    try:
        with open(GATE_STATUS_PATH) as f:
            return bool(json.load(f).get("passed") is True)
    except Exception:
        return False


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROSTER
    sc = run_backtest(path)
    print(json.dumps(sc, indent=2))
    print("\nGATE OPEN" if sc["passed"] else "\nGATE CLOSED (KP quarantined)")
