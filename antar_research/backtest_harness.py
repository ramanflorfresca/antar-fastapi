#!/usr/bin/env python3
"""
backtest_harness.py — Public-chart backtest harness for Antar's deterministic
past-events engine (engine: convergence_v1).

Read-only against the production API. Creates test charts via the public
create endpoint, retrodicts categorical/dated life events, and scores them
against a roster of documented public-figure life events.

Usage:
    python backtest_harness.py                       # uses ./backtest_roster.json
    python backtest_harness.py --roster path.json    # custom roster
    python backtest_harness.py --only "Elon Musk"    # single chart (seed verify)
    python backtest_harness.py --base-url <url>       # override base URL

Writes:
    out/backtest_results.csv   — one row per scored event
    out/backtest_results.json  — full structured results + aggregate scorecard

Nothing in this file edits production. It does not import any engine module.
"""

import argparse
import csv
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date

BASE_URL_DEFAULT = "https://antar-fastapi-production.up.railway.app"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")

# ---------------------------------------------------------------------------
# Event-type vocabulary observed in production (convergence_v1)
# ---------------------------------------------------------------------------
KNOWN_EVENT_TYPES = {
    "major_relocation", "career_pivot", "professional_setback",
    "serious_partnership_began", "serious_partnership_ended",
    "family_expansion_first", "family_expansion_second", "business_start",
    "financial_disruption", "major_acquisition", "legal_entanglement",
    "loss_of_father", "loss_of_mother",
}

# Opposite-polarity pairs for POLARITY_ERROR detection.
# If a positive event of type A has no in-window prediction of type A, but the
# engine fired one of these "opposite" types near the actual date, that's a
# polarity error (the engine saw *something* but flipped the valence).
POLARITY_OPPOSITES = {
    "serious_partnership_began": ["serious_partnership_ended"],
    "serious_partnership_ended": ["serious_partnership_began"],
    "business_start": ["professional_setback", "financial_disruption"],
    "professional_setback": ["business_start", "major_acquisition", "career_pivot"],
    "major_acquisition": ["financial_disruption", "professional_setback"],
    "financial_disruption": ["business_start", "major_acquisition"],
    "career_pivot": ["professional_setback"],
}

# Time-of-day-sensitive event types (depend on lagna / house cusps).
# Excluded from scoring on noon-default (rodden_rating == "X") charts.
TIME_SENSITIVE_TYPES = {
    "major_relocation", "career_pivot", "professional_setback",
}

# ---------------------------------------------------------------------------
# Date helpers — everything works in "months since epoch" integers so window
# math is precise and timezone-free.
# ---------------------------------------------------------------------------

def ym_to_months(y, m):
    return y * 12 + (m - 1)


def parse_month(s):
    """'YYYY-MM' or 'YYYY-MM-DD' -> integer month index. None -> None."""
    if not s:
        return None
    parts = str(s).split("-")
    return ym_to_months(int(parts[0]), int(parts[1]))


def months_label(month_idx):
    y, m = divmod(month_idx, 12)
    return f"{y:04d}-{m + 1:02d}"


def window_months(window):
    """Return (start_idx, end_idx, mid_idx) in month units for a window dict."""
    s = parse_month(window.get("start"))
    e = parse_month(window.get("end"))
    if s is None or e is None:
        return None, None, None
    mid = (s + e) // 2
    return s, e, mid


def months_off_from_window(actual_idx, start_idx, end_idx):
    """
    Signed distance in months from the actual date to the nearer window edge.
    Inside the window -> 0. Before start -> negative. After end -> positive.
    """
    if actual_idx is None or start_idx is None:
        return None
    if start_idx <= actual_idx <= end_idx:
        return 0
    if actual_idx < start_idx:
        return actual_idx - start_idx  # negative
    return actual_idx - end_idx        # positive


# ---------------------------------------------------------------------------
# HTTP — stdlib only, with retry + timeout discipline (§3)
# ---------------------------------------------------------------------------

def _http(method, url, payload=None, timeout=60):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def http_call(method, url, payload=None, timeout=60, retries=1):
    """One retry on timeout/5xx, then raise."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            status, body = _http(method, url, payload, timeout)
            if status >= 500:
                last_err = RuntimeError(f"HTTP {status}")
                time.sleep(2)
                continue
            return status, body
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < retries:
                last_err = e
                time.sleep(2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(2)
                continue
            raise
    if last_err:
        raise last_err


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

def create_chart(base_url, chart):
    payload = {
        "birth_date": chart["birth_date"],
        "birth_time": chart["birth_time"],
        "latitude": chart["latitude"],
        "longitude": chart["longitude"],
        "timezone_offset": chart["timezone_offset"],
        "timezone_name": chart["timezone_name"],
        "birth_place": chart.get("birth_place", ""),
        "name": "BACKTEST " + chart["name"],
    }
    status, body = http_call("POST", base_url + "/api/v1/chart/create", payload)
    return body


def backfill_jaimini(base_url, chart_id):
    try:
        http_call("GET", base_url + f"/api/v1/backfill-jaimini/{chart_id}")
    except Exception:
        pass  # idempotent; body ignored per brief


def fetch_past_events(base_url, chart_id):
    status, body = http_call(
        "GET",
        base_url + f"/api/v1/chart/{chart_id}/past-events"
        "?min_confidence=3&max_predictions=20",
    )
    return body


def build_prediction_map(past_events):
    """event_type -> {window, confidence}. Keep highest-confidence on collision."""
    pred_map = {}
    collisions = []
    for p in past_events.get("predictions", []):
        et = p.get("event_type")
        conf = p.get("confidence", 0)
        entry = {
            "window": p.get("window", {}),
            "confidence": conf,
            "confidence_label": p.get("confidence_label"),
            "dasha": p.get("dasha"),
        }
        if et in pred_map:
            collisions.append(et)
            if conf > pred_map[et]["confidence"]:
                pred_map[et] = entry
        else:
            pred_map[et] = entry
    return pred_map, collisions


# ---------------------------------------------------------------------------
# Scoring rubric (§4)
# ---------------------------------------------------------------------------

def score_event(roster_event, pred_map, tolerance_months):
    """Return a dict describing the outcome for one roster event."""
    et = roster_event["event_type"]
    kind = roster_event["kind"]
    actual = roster_event.get("actual_date")
    actual_idx = parse_month(actual)

    result = {
        "event_type": et,
        "kind": kind,
        "actual_date": actual,
        "predicted_window": "",
        "confidence": "",
        "outcome": None,
        "months_off": "",
        "polarity_fired": "",
        "source": roster_event.get("source", ""),
        "notes": roster_event.get("notes", ""),
    }

    pred = pred_map.get(et)

    # --- negative_alive: any matching-type prediction is a false positive ---
    if kind == "negative_alive":
        if pred is not None:
            w = pred["window"]
            result["outcome"] = "FALSE_POSITIVE"
            result["predicted_window"] = f"{w.get('start')}..{w.get('end')}"
            result["confidence"] = pred["confidence"]
        else:
            result["outcome"] = "TRUE_NEGATIVE"
        return result

    # --- positive events ---
    if pred is not None:
        w = pred["window"]
        s_idx, e_idx, mid_idx = window_months(w)
        result["predicted_window"] = f"{w.get('start')}..{w.get('end')}"
        result["confidence"] = pred["confidence"]

        # HIT: inside window, or within tolerance of window midpoint.
        edge_off = months_off_from_window(actual_idx, s_idx, e_idx)
        in_window = edge_off == 0
        within_tol = (
            actual_idx is not None and mid_idx is not None
            and abs(actual_idx - mid_idx) <= tolerance_months
        )
        result["months_off"] = edge_off if edge_off is not None else ""
        if in_window or within_tol:
            result["outcome"] = "HIT"
        else:
            result["outcome"] = "NEAR"
        return result

    # --- no matching-type prediction: check for a polarity error ---
    opp_types = POLARITY_OPPOSITES.get(et, [])
    best_opp = None
    best_dist = None
    for ot in opp_types:
        opred = pred_map.get(ot)
        if not opred:
            continue
        s_idx, e_idx, mid_idx = window_months(opred["window"])
        dist = months_off_from_window(actual_idx, s_idx, e_idx)
        if dist is None:
            continue
        adist = abs(dist)
        # Only counts as a polarity error if it landed near the actual date.
        if adist <= tolerance_months and (best_dist is None or adist < best_dist):
            best_dist = adist
            best_opp = (ot, opred, dist)

    if best_opp is not None:
        ot, opred, dist = best_opp
        w = opred["window"]
        result["outcome"] = "POLARITY_ERROR"
        result["polarity_fired"] = ot
        result["predicted_window"] = f"{w.get('start')}..{w.get('end')}"
        result["confidence"] = opred["confidence"]
        result["months_off"] = dist
        return result

    # --- nothing fired at all ---
    result["outcome"] = "MISS"
    return result


# ---------------------------------------------------------------------------
# Per-chart processing
# ---------------------------------------------------------------------------

def process_chart(base_url, chart, tolerance_months, verbose=True):
    name = chart["name"]
    rodden = chart.get("rodden_rating", "?")
    record = {
        "name": name,
        "expected_lagna": chart.get("expected_lagna"),
        "rodden_rating": rodden,
        "lagna": None,
        "chart_id": None,
        "status": None,
        "scored_events": [],
        "collisions": [],
        "all_predictions": [],
        "note": "",
    }

    # 1. Create
    try:
        created = create_chart(base_url, chart)
    except Exception as e:
        record["status"] = "ERROR"
        record["note"] = f"create failed: {e}"
        if verbose:
            print(f"  [{name}] ERROR creating chart: {e}")
        return record

    record["chart_id"] = created.get("chart_id")
    record["lagna"] = created.get("lagna")

    # 2. Integrity gate
    expected = chart.get("expected_lagna")
    got = created.get("lagna")
    if expected and got and got.strip().lower() != expected.strip().lower():
        record["status"] = "NEEDS_VERIFICATION"
        record["note"] = f"lagna mismatch (expected {expected}, got {got})"
        if verbose:
            print(f"  [{name}] NEEDS_VERIFICATION — expected {expected}, got {got}; skipping scoring")
        return record

    # 3. Backfill (idempotent)
    backfill_jaimini(base_url, record["chart_id"])

    # 4. Retrodict
    try:
        past = fetch_past_events(base_url, record["chart_id"])
    except Exception as e:
        record["status"] = "ERROR"
        record["note"] = f"past-events failed: {e}"
        if verbose:
            print(f"  [{name}] ERROR fetching past-events: {e}")
        return record

    # 5. Prediction map
    pred_map, collisions = build_prediction_map(past)
    record["collisions"] = collisions
    record["all_predictions"] = [
        {
            "event_type": p.get("event_type"),
            "confidence": p.get("confidence"),
            "window": p.get("window", {}),
        }
        for p in past.get("predictions", [])
    ]

    # 6. Score each roster event
    is_noon_default = str(rodden).upper() == "X"
    for ev in chart.get("events", []):
        if is_noon_default and ev["event_type"] in TIME_SENSITIVE_TYPES:
            # reduced scoring scope for noon-default charts
            continue
        scored = score_event(ev, pred_map, tolerance_months)
        record["scored_events"].append(scored)

    record["status"] = "SCORED"
    if verbose:
        n = len(record["scored_events"])
        print(f"  [{name}] SCORED — lagna {got}, {len(record['all_predictions'])} predictions, {n} events scored")
    return record


# ---------------------------------------------------------------------------
# Aggregate scorecard (§5)
# ---------------------------------------------------------------------------

def build_scorecard(records):
    scored_records = [r for r in records if r["status"] == "SCORED"]

    # Flatten scored events from gated-in charts only.
    pos_events = []   # positive events
    neg_events = []   # negative_alive events
    for r in scored_records:
        for ev in r["scored_events"]:
            if ev["kind"] == "negative_alive":
                neg_events.append(ev)
            else:
                pos_events.append(ev)

    def count(outcomes, events):
        return sum(1 for e in events if e["outcome"] in outcomes)

    n_hit = count({"HIT"}, pos_events)
    n_near = count({"NEAR"}, pos_events)
    n_pol = count({"POLARITY_ERROR"}, pos_events)
    n_miss = count({"MISS"}, pos_events)
    n_pos = len(pos_events)

    hit_rate = (n_hit / n_pos) if n_pos else None
    near_present_rate = ((n_hit + n_near + n_pol) / n_pos) if n_pos else None

    offs = [abs(e["months_off"]) for e in pos_events
            if e["outcome"] in {"HIT", "NEAR"} and isinstance(e["months_off"], int)]
    median_off = statistics.median(offs) if offs else None

    n_fp = count({"FALSE_POSITIVE"}, neg_events)
    n_tn = count({"TRUE_NEGATIVE"}, neg_events)
    n_neg = len(neg_events)
    fp_rate = (n_fp / n_neg) if n_neg else None

    # Per-event-type accuracy
    per_type = {}
    for e in pos_events + neg_events:
        et = e["event_type"]
        d = per_type.setdefault(et, {"n": 0, "hit": 0, "near": 0, "miss": 0,
                                     "fp": 0, "tn": 0, "polarity": 0})
        d["n"] += 1
        o = e["outcome"]
        if o == "HIT":
            d["hit"] += 1
        elif o == "NEAR":
            d["near"] += 1
        elif o == "MISS":
            d["miss"] += 1
        elif o == "FALSE_POSITIVE":
            d["fp"] += 1
        elif o == "TRUE_NEGATIVE":
            d["tn"] += 1
        elif o == "POLARITY_ERROR":
            d["polarity"] += 1

    # Confidence calibration — bucket EVERY emitted prediction.
    # A prediction is "correct" if it corresponds to a HIT (positive event in
    # window/tolerance) and "wrong" if it is a FALSE_POSITIVE. Predictions that
    # don't map to any roster event are "unscored" (no ground truth).
    buckets = {"4-5": [], "6-7": [], "8": [], "9": []}

    def bucket_for(conf):
        if conf is None:
            return None
        if conf >= 9:
            return "9"
        if conf == 8:
            return "8"
        if conf >= 6:
            return "6-7"
        if conf >= 4:
            return "4-5"
        return None

    # Map each scored event that had a prediction to a correctness flag.
    for r in scored_records:
        for ev in r["scored_events"]:
            conf = ev.get("confidence")
            if conf == "" or conf is None:
                continue
            b = bucket_for(conf)
            if b is None:
                continue
            if ev["outcome"] == "HIT":
                buckets[b].append(1)
            elif ev["outcome"] in {"FALSE_POSITIVE", "MISS"}:
                # MISS can't have a confidence (no pred) so effectively FP/NEAR here
                buckets[b].append(0)
            elif ev["outcome"] in {"NEAR", "POLARITY_ERROR"}:
                buckets[b].append(0)  # saw it but wrong window/polarity = not a clean hit

    calibration = {}
    for b, vals in buckets.items():
        if vals:
            calibration[b] = {"n": len(vals), "hit_rate": sum(vals) / len(vals)}
        else:
            calibration[b] = {"n": 0, "hit_rate": None}

    roster_status = [
        {"name": r["name"], "lagna": r["lagna"],
         "expected": r["expected_lagna"], "rodden": r["rodden_rating"],
         "status": r["status"], "note": r["note"]}
        for r in records
    ]

    return {
        "totals": {
            "charts_total": len(records),
            "charts_scored": len(scored_records),
            "charts_needs_verification": sum(1 for r in records if r["status"] == "NEEDS_VERIFICATION"),
            "charts_error": sum(1 for r in records if r["status"] == "ERROR"),
            "positive_events": n_pos,
            "negative_alive_events": n_neg,
        },
        "hit_rate": hit_rate,
        "near_but_present_rate": near_present_rate,
        "median_abs_months_off": median_off,
        "false_positive_rate": fp_rate,
        "counts": {
            "HIT": n_hit, "NEAR": n_near, "POLARITY_ERROR": n_pol,
            "MISS": n_miss, "FALSE_POSITIVE": n_fp, "TRUE_NEGATIVE": n_tn,
        },
        "per_event_type": per_type,
        "confidence_calibration": calibration,
        "roster_status": roster_status,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_csv(records, path):
    cols = ["chart", "event_type", "kind", "actual_date", "predicted_window",
            "confidence", "outcome", "months_off", "polarity_fired", "source"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in records:
            if r["status"] != "SCORED":
                continue
            for ev in r["scored_events"]:
                w.writerow([
                    r["name"], ev["event_type"], ev["kind"], ev["actual_date"],
                    ev["predicted_window"], ev["confidence"], ev["outcome"],
                    ev["months_off"], ev.get("polarity_fired", ""), ev["source"],
                ])


def pct(x):
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "n/a"


def print_scorecard(sc):
    t = sc["totals"]
    print("\n" + "=" * 70)
    print("ANTAR PAST-EVENTS BACKTEST — SCORECARD")
    print("=" * 70)
    print(f"Charts: {t['charts_total']} total | {t['charts_scored']} scored | "
          f"{t['charts_needs_verification']} needs-verification | {t['charts_error']} error")
    print(f"Events scored: {t['positive_events']} positive | {t['negative_alive_events']} negative-alive")
    print()
    print(f"  Hit rate              : {pct(sc['hit_rate'])}   "
          f"(HIT / all positive events)")
    print(f"  Near-but-present rate : {pct(sc['near_but_present_rate'])}   "
          f"(engine saw the event at all, timing aside)")
    mo = sc["median_abs_months_off"]
    print(f"  Median |months_off|   : {mo if mo is not None else 'n/a'}   (HIT+NEAR timing precision)")
    print(f"  False-positive rate   : {pct(sc['false_positive_rate'])}   "
          f"(fired on a non-event)")
    c = sc["counts"]
    print(f"  Outcome tally         : HIT={c['HIT']} NEAR={c['NEAR']} "
          f"POLARITY={c['POLARITY_ERROR']} MISS={c['MISS']} "
          f"FP={c['FALSE_POSITIVE']} TN={c['TRUE_NEGATIVE']}")

    print("\nPER-EVENT-TYPE ACCURACY")
    print(f"  {'event_type':28s} {'n':>3} {'hit':>4} {'near':>5} {'miss':>5} {'fp':>3} {'tn':>3} {'pol':>4}")
    for et in sorted(sc["per_event_type"].keys()):
        d = sc["per_event_type"][et]
        print(f"  {et:28s} {d['n']:>3} {d['hit']:>4} {d['near']:>5} {d['miss']:>5} "
              f"{d['fp']:>3} {d['tn']:>3} {d['polarity']:>4}")

    print("\nCONFIDENCE CALIBRATION  (does a higher confidence number earn its keep?)")
    print(f"  {'bucket':>8} {'n':>4} {'hit_rate':>10}")
    for b in ["4-5", "6-7", "8", "9"]:
        d = sc["confidence_calibration"][b]
        print(f"  {b:>8} {d['n']:>4} {pct(d['hit_rate']):>10}")

    print("\nROSTER STATUS")
    print(f"  {'name':22s} {'lagna':10s} {'expected':10s} {'rod':>3} {'status':18s} note")
    for r in sc["roster_status"]:
        print(f"  {str(r['name'])[:22]:22s} {str(r['lagna']):10s} "
              f"{str(r['expected']):10s} {str(r['rodden']):>3} {str(r['status']):18s} {r['note']}")
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

RECORD_DIR = os.path.join(OUT_DIR, "_records")


def finalize(base_url, tolerance_months):
    """Read all checkpointed per-chart records, build scorecard + CSV + JSON."""
    import glob
    paths = sorted(glob.glob(os.path.join(RECORD_DIR, "*.json")),
                   key=lambda p: int(os.path.basename(p).split("_")[0]))
    records = [json.load(open(p)) for p in paths]
    scorecard = build_scorecard(records)
    print_scorecard(scorecard)
    csv_path = os.path.join(OUT_DIR, "backtest_results.csv")
    json_path = os.path.join(OUT_DIR, "backtest_results.json")
    write_csv(records, csv_path)
    with open(json_path, "w") as f:
        json.dump({
            "base_url": base_url,
            "tolerance_months": tolerance_months,
            "run_date": str(date.today()),
            "scorecard": scorecard,
            "records": records,
        }, f, indent=2)
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


def main():
    ap = argparse.ArgumentParser(description="Antar past-events backtest harness")
    ap.add_argument("--roster", default=os.path.join(HERE, "backtest_roster.json"))
    ap.add_argument("--base-url", default=BASE_URL_DEFAULT)
    ap.add_argument("--only", default=None, help="Run only the chart with this exact name")
    ap.add_argument("--slice", default=None, help="Process roster indices start:end (checkpointed)")
    ap.add_argument("--finalize", action="store_true", help="Aggregate checkpointed records into scorecard")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds between charts")
    args = ap.parse_args()

    with open(args.roster) as f:
        roster = json.load(f)
    tolerance_months = roster.get("tolerance_months", 6)
    all_charts = roster["charts"]

    # Aggregation-only mode (reads checkpointed records, hits no API).
    if args.finalize:
        finalize(args.base_url, tolerance_months)
        return

    # Checkpointed slice mode — process a subset, write per-chart records.
    if args.slice:
        os.makedirs(RECORD_DIR, exist_ok=True)
        start, end = (int(x) for x in args.slice.split(":"))
        indexed = list(enumerate(all_charts))[start:end]
        print(f"Base URL: {args.base_url} | slice {start}:{end} ({len(indexed)} charts)\n")
        for idx, chart in indexed:
            print(f"[{idx}] {chart['name']}")
            rec = process_chart(args.base_url, chart, tolerance_months)
            safe = chart["name"].replace(" ", "_")
            with open(os.path.join(RECORD_DIR, f"{idx:02d}_{safe}.json"), "w") as f:
                json.dump(rec, f, indent=2)
            time.sleep(args.sleep)
        print("slice complete (records checkpointed)")
        return

    # Full in-process run (single call) — used for small rosters / --only.
    charts = all_charts
    if args.only:
        charts = [c for c in charts if c["name"] == args.only]
        if not charts:
            print(f"No chart named {args.only!r} in roster.")
            sys.exit(1)

    print(f"Base URL: {args.base_url}")
    print(f"Tolerance: +/-{tolerance_months} months | Charts: {len(charts)}\n")

    records = []
    for i, chart in enumerate(charts):
        print(f"[{i + 1}/{len(charts)}] {chart['name']}")
        rec = process_chart(args.base_url, chart, tolerance_months)
        records.append(rec)
        if i < len(charts) - 1:
            time.sleep(args.sleep)

    scorecard = build_scorecard(records)
    print_scorecard(scorecard)

    os.makedirs(OUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUT_DIR, "backtest_results.csv")
    json_path = os.path.join(OUT_DIR, "backtest_results.json")
    write_csv(records, csv_path)
    with open(json_path, "w") as f:
        json.dump({
            "base_url": args.base_url,
            "tolerance_months": tolerance_months,
            "run_date": str(date.today()),
            "scorecard": scorecard,
            "records": records,
        }, f, indent=2)

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
