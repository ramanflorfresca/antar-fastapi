#!/usr/bin/env python3
"""
test_life_events_accuracy.py
=============================
Tests Antar's prediction accuracy against 6 known life events.

KNOWN EVENTS (ground truth):
  Raman:
    - Civil marriage:    Jan 12, 1998
    - Indian wedding:    Dec 25, 1998
    - Came to America:   May 17, 1992
    - First son born:    Nov 8, 2001
    - Second son born:   Oct 13, 2003
    - Divorce:           Sep 14, 2014

  Andres:
    - Daughter born:     Apr 10, 2023

SCORING:
  We ask the system to predict WHEN each event happened (without telling it).
  Then we score how close the prediction is to the actual date.
  3-6 month window = good enough per Raman's spec.
"""

import os, json, asyncio, httpx
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://antar-fastapi-production.up.railway.app"
RAMAN_ID  = "de02bb52-d43a-4b09-be25-b45a07bfbf8a"
ANDRES_ID = "6ec6311c-d46e-4e97-a46c-859882071971"

# Ground truth
ACTUAL_EVENTS = {
    "R01": {"date": date(1998,  1, 12), "label": "Raman civil marriage"},
    "R02": {"date": date(1998, 12, 25), "label": "Raman Indian wedding"},
    "R03": {"date": date(1992,  5, 17), "label": "Raman moved to America"},
    "R04": {"date": date(2001, 11,  8), "label": "Raman first son born"},
    "R05": {"date": date(2003, 10, 13), "label": "Raman second son born"},
    "R06": {"date": date(2014,  9, 14), "label": "Raman divorce"},
    "A01": {"date": date(2023,  4, 10), "label": "Andres daughter born"},
}

# Questions — phrased to elicit timing without giving away the answer
TEST_QUESTIONS = [
    {
        "id": "R01",
        "chart_id": RAMAN_ID,
        "question": "When did I get married? What period in my chart shows marriage activation?",
        "language": "en",
        "concern": "relationships",
    },
    {
        "id": "R02",
        "chart_id": RAMAN_ID,
        "question": "What year and period does my chart show for marriage or major relationship commitment?",
        "language": "en",
        "concern": "relationships",
    },
    {
        "id": "R03",
        "chart_id": RAMAN_ID,
        "question": "When does my chart show a major relocation or move to a foreign country?",
        "language": "en",
        "concern": "general",
    },
    {
        "id": "R04",
        "chart_id": RAMAN_ID,
        "question": "When did I have my first child? What period in my chart shows childbirth?",
        "language": "en",
        "concern": "general",
    },
    {
        "id": "R05",
        "chart_id": RAMAN_ID,
        "question": "When did I have children? What years does my chart show for birth of children?",
        "language": "en",
        "concern": "general",
    },
    {
        "id": "R06",
        "chart_id": RAMAN_ID,
        "question": "When does my chart show a major relationship ending or divorce?",
        "language": "en",
        "concern": "relationships",
    },
    {
        "id": "A01",
        "chart_id": ANDRES_ID,
        "question": "When did I have a child or when does my chart show childbirth?",
        "language": "es",
        "concern": "general",
    },
]


def extract_years_mentioned(text: str) -> list:
    """Extract all years mentioned in a prediction text."""
    import re
    years = re.findall(r'\b(19[0-9]{2}|20[0-2][0-9])\b', text)
    return sorted(set(int(y) for y in years))


def score_prediction(pred_text: str, timing_window: str, actual_date: date) -> dict:
    """
    Score a prediction against the actual event date.
    Returns score (3/2/1/0) and explanation.
    """
    actual_year  = actual_date.year
    actual_month = actual_date.month

    # Extract years from prediction
    all_text = (pred_text or "") + " " + (timing_window or "")
    years_mentioned = extract_years_mentioned(all_text)

    # Check for exact year match
    exact_year = actual_year in years_mentioned

    # Check for adjacent year (±1)
    adjacent_year = any(abs(y - actual_year) == 1 for y in years_mentioned)

    # Check for within-2-year range
    near_year = any(abs(y - actual_year) <= 2 for y in years_mentioned)

    # Score
    if exact_year:
        score = 3
        label = "✅ EXACT year predicted"
    elif adjacent_year:
        score = 2
        label = "🟡 Within 1 year (good)"
    elif near_year:
        score = 1
        label = "🟠 Within 2 years (partial)"
    elif years_mentioned:
        closest = min(years_mentioned, key=lambda y: abs(y - actual_year))
        gap = abs(closest - actual_year)
        score = 0
        label = f"❌ Off by {gap} years (closest: {closest})"
    else:
        score = 0
        label = "❌ No year predicted"

    return {
        "score":           score,
        "label":           label,
        "actual_year":     actual_year,
        "actual_month":    actual_month,
        "years_in_pred":   years_mentioned,
        "exact_year_hit":  exact_year,
    }


async def run_question(client: httpx.AsyncClient, test: dict) -> dict:
    """Run one question."""
    try:
        resp = await client.post(
            f"{BASE_URL}/api/v1/predict",
            json={
                "chart_id":        test["chart_id"],
                "question":        test["question"],
                "language":        test["language"],
                "use_json_context": True,
            },
            timeout=45.0,
        )
        data = resp.json()
        return {
            **test,
            "plain_summary":  data.get("plain_summary", ""),
            "timing_window":  data.get("timing_window", ""),
            "why_this":       data.get("why_this", ""),
            "signal_line":    data.get("signal_line", ""),
            "context_path":   data.get("context_path", "prose"),
            "error": None,
        }
    except Exception as e:
        return {**test, "plain_summary": "", "timing_window": "", "error": str(e)}


async def main():
    print("=" * 65)
    print("ANTAR LIFE EVENTS ACCURACY TEST")
    print("=" * 65)
    print(f"Testing {len(TEST_QUESTIONS)} questions against {len(ACTUAL_EVENTS)} known events")
    print()

    results = []
    async with httpx.AsyncClient() as client:
        for test in TEST_QUESTIONS:
            event   = ACTUAL_EVENTS[test["id"]]
            person  = "Raman" if test["chart_id"] == RAMAN_ID else "Andres"
            print(f"[{test['id']}] {person} — {event['label']}")
            print(f"     Q: {test['question']}")

            result = await run_question(client, test)

            if result.get("error"):
                print(f"     ❌ ERROR: {result['error']}")
                results.append({**result, "scoring": {"score": 0, "label": "ERROR"}})
                continue

            # Score it
            scoring = score_prediction(
                result["plain_summary"],
                result["timing_window"],
                event["date"],
            )

            print(f"     PATH: {result['context_path']}")
            print(f"     PREDICTION: {result['plain_summary'][:120]}...")
            print(f"     TIMING: {result['timing_window']}")
            print(f"     ACTUAL: {event['date'].strftime('%B %d, %Y')}")
            print(f"     SCORE: {scoring['label']}")
            print(f"     YEARS IN PRED: {scoring['years_in_pred']}")
            print()

            results.append({
                **result,
                "actual_date":  event["date"].isoformat(),
                "actual_label": event["label"],
                "scoring":      scoring,
            })

    # Summary
    print("=" * 65)
    print("ACCURACY SUMMARY")
    print("=" * 65)

    scored = [r for r in results if not r.get("error")]
    total  = len(scored)
    scores = [r["scoring"]["score"] for r in scored]

    exact   = sum(1 for s in scores if s == 3)
    good    = sum(1 for s in scores if s >= 2)
    partial = sum(1 for s in scores if s >= 1)
    wrong   = sum(1 for s in scores if s == 0)

    print(f"\nTotal predictions scored: {total}")
    print(f"Exact year (score 3):     {exact}/{total}  = {exact/total*100:.0f}%")
    print(f"Within 1 yr (score 2+):   {good}/{total}  = {good/total*100:.0f}%")
    print(f"Within 2 yrs (score 1+):  {partial}/{total} = {partial/total*100:.0f}%")
    print(f"Wrong/no year (score 0):  {wrong}/{total}  = {wrong/total*100:.0f}%")
    print()
    print(f"{'PASS ✅' if good/total >= 0.6 else 'NEEDS WORK ❌'}  "
          f"(target: 70% within 1 year = {int(total*0.7)} of {total} correct)")

    print("\n--- DETAIL ---")
    for r in results:
        if r.get("error"):
            continue
        s = r["scoring"]
        print(f"  {r['id']} {r['actual_label']:35s} actual={r['actual_date'][:7]}  "
              f"pred_years={s['years_in_pred']}  {s['label']}")

    # What dasha was active at each actual event
    print("\n--- DASHA CONTEXT AT EACH EVENT ---")
    print("  (For manual verification — what dasha should have been active)")
    dasha_context = {
        "R01": "Venus MD (1983-2003) — Venus rules 5H (romance) and 10H (authority) for Capricorn lagna",
        "R02": "Venus MD — same period, Indian wedding 11 months after civil",
        "R03": "Venus MD (1983-2003) / Ketu AD or Venus AD — foreign travel",
        "R04": "Sun MD (2003-2009) started Aug 2003 / Venus MD ended Aug 2003 — Sun rules 8H",
        "R05": "Sun MD (2003-2009) — Oct 2003 is right at Venus→Sun MD transition",
        "R06": "Moon MD (2009-2019) — Moon rules 7H (marriage/partnerships) for Capricorn lagna",
        "A01": "Check Andres dasha for Apr 2023 — should show 5H activation",
    }
    for event_id, context in dasha_context.items():
        print(f"  {event_id}: {context}")

    # Save
    output = {
        "ran_at":  datetime.now().isoformat(),
        "summary": {
            "total":           total,
            "exact_year_pct":  round(exact/total*100, 1) if total else 0,
            "within_1yr_pct":  round(good/total*100, 1) if total else 0,
            "within_2yr_pct":  round(partial/total*100, 1) if total else 0,
        },
        "results": results,
    }
    with open("life_events_accuracy.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n✅ Full results saved to life_events_accuracy.json")


if __name__ == "__main__":
    asyncio.run(main())
