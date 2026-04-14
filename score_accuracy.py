#!/usr/bin/env python3
"""
score_accuracy.py
==================
Reads accuracy_test_results.json after you've manually scored each prediction.
Outputs accuracy by category and overall.

USAGE:
  python score_accuracy.py
"""

import json
from collections import defaultdict

def main():
    try:
        with open("accuracy_test_results.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Run run_accuracy_test.py first")
        return

    results = data["results"]
    scored  = [r for r in results if r.get("score") is not None and r["score"] != 0]
    pending = [r for r in results if r.get("score") == 0 or r.get("score") is None]

    if not scored:
        print("No scored results yet. Fill in 'score' fields in accuracy_test_results.json")
        return

    print(f"\n{'='*60}")
    print(f"ANTAR ACCURACY REPORT")
    print(f"Scored: {len(scored)} | Pending: {len(pending)}")
    print(f"{'='*60}\n")

    # Overall accuracy (score 3 = full credit, 2 = half credit, 1 = no credit)
    total_possible = len(scored) * 3
    total_earned   = sum(r["score"] for r in scored if isinstance(r["score"], (int, float)))
    overall_pct    = (total_earned / total_possible * 100) if total_possible > 0 else 0

    # Confirmed rate (score >= 2 = "correct enough")
    confirmed = [r for r in scored if isinstance(r["score"], (int, float)) and r["score"] >= 2]
    confirmed_pct = len(confirmed) / len(scored) * 100

    print(f"OVERALL ACCURACY:  {overall_pct:.1f}%  (weighted: 3=full, 2=half, 1=none)")
    print(f"CONFIRMATION RATE: {confirmed_pct:.1f}%  (score >= 2 counts as correct)")
    print(f"TARGET:            70-75%")
    gap = 70 - confirmed_pct
    if gap > 0:
        print(f"GAP TO TARGET:     {gap:.1f} percentage points")
    else:
        print(f"✅ AT OR ABOVE TARGET")

    # By verifiable category
    print(f"\n--- BY CATEGORY ---")
    by_category = defaultdict(list)
    for r in scored:
        by_category[r.get("verifiable", "unknown")].append(r["score"])

    for cat, scores in sorted(by_category.items()):
        valid = [s for s in scores if isinstance(s, (int, float))]
        if not valid:
            continue
        cat_pct = sum(1 for s in valid if s >= 2) / len(valid) * 100
        avg = sum(valid) / len(valid)
        print(f"  {cat:20s}: {cat_pct:.0f}% confirmed  (avg score {avg:.1f})  n={len(valid)}")

    # By concern/domain
    print(f"\n--- BY DOMAIN ---")
    by_domain = defaultdict(list)
    for r in scored:
        by_domain[r.get("concern", "general")].append(r["score"])

    for domain, scores in sorted(by_domain.items()):
        valid = [s for s in scores if isinstance(s, (int, float))]
        if not valid:
            continue
        dom_pct = sum(1 for s in valid if s >= 2) / len(valid) * 100
        print(f"  {domain:20s}: {dom_pct:.0f}% confirmed  n={len(valid)}")

    # Context path comparison
    print(f"\n--- JSON PATH vs PROSE PATH ---")
    by_path = defaultdict(list)
    for r in scored:
        path = r.get("context_path", "prose")
        by_path[path].append(r["score"])

    for path, scores in by_path.items():
        valid = [s for s in scores if isinstance(s, (int, float))]
        if not valid:
            continue
        path_pct = sum(1 for s in valid if s >= 2) / len(valid) * 100
        print(f"  {path:20s}: {path_pct:.0f}% confirmed  n={len(valid)}")

    # Low scoring predictions (to diagnose)
    print(f"\n--- LOWEST SCORING (to improve) ---")
    low = sorted([r for r in scored if isinstance(r.get("score"), (int,float)) and r["score"] <= 1],
                 key=lambda x: x["score"])
    for r in low[:5]:
        print(f"  [{r['id']}] score={r['score']} | {r['question'][:50]}")
        print(f"       Prediction: {r['plain_summary'][:80]}")
        print(f"       Notes: {r.get('score_notes','')}")
        print()

    # Specificity check
    print(f"--- SPECIFICITY CHECK ---")
    for r in scored:
        has_date  = any(
            w in (r.get("timing_window") or "").lower()
            for w in ["2026", "2025", "january","february","march","april",
                      "may","june","july","august","september","october",
                      "enero","febrero","marzo","abril","mayo","junio"]
        )
        has_range = "-" in (r.get("timing_window") or "")
        print(f"  {r['id']}: timing='{r.get('timing_window','')}' | specific={'✅' if has_date else '❌'}")

    print(f"\n{'='*60}")
    print("To improve accuracy:")
    print("  1. Low past/natal scores → chart data quality issue (D9, dashas)")
    print("  2. Low current scores  → context/DKP not being applied")
    print("  3. Low specificity     → falsifiable predictions sprint needed")
    print("  4. JSON < prose score  → system prompt needs tuning")


if __name__ == "__main__":
    main()
