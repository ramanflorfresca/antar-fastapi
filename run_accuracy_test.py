#!/usr/bin/env python3
"""
run_accuracy_test.py
=====================
Runs 10 specific test questions against Raman's chart using the JSON path,
saves all predictions to accuracy_test_results.json for manual scoring.

You (Raman) score each prediction:
  3 = Confirmed — happened exactly as predicted
  2 = Partial   — directionally right, timing or details off
  1 = Wrong     — didn't happen or opposite happened
  0 = Too early — window hasn't passed yet, can't score

USAGE:
  cd ~/antarai && source venv311/bin/activate
  python run_accuracy_test.py
  # Review accuracy_test_results.json
  # Score each prediction manually
  # Run: python score_accuracy.py to see results

These questions are designed to be verifiable against your actual life:
  - Past events (2019-2025): you know what happened
  - Current state (now): you can observe
  - Near future (2026): you'll know soon
"""

import os, json, asyncio, httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://antar-fastapi-production.up.railway.app"
RAMAN_CHART_ID = "de02bb52-d43a-4b09-be25-b45a07bfbf8a"
ANDRES_CHART_ID = "6ec6311c-d46e-4e97-a46c-859882071971"

# 15 test questions — mix of past, present, near-future
# Designed to be verifiable by the person who lived them
TEST_QUESTIONS = [
    # PAST — Mars MD started Aug 2019. You can verify these.
    {
        "id": "T01",
        "chart_id": RAMAN_CHART_ID,
        "question": "What happened to my career and income between 2019 and 2021?",
        "language": "en",
        "concern": "career",
        "scoring_guide": "Did career have friction/pressure 2019-2021? Was income blocked?",
        "verifiable": "past",
    },
    {
        "id": "T02",
        "chart_id": RAMAN_CHART_ID,
        "question": "Was 2022-2023 a period of financial pressure or opportunity for me?",
        "language": "en",
        "concern": "finance",
        "scoring_guide": "Score against your actual 2022-2023 financial experience",
        "verifiable": "past",
    },
    {
        "id": "T03",
        "chart_id": RAMAN_CHART_ID,
        "question": "What does my chart say about my ability to close deals and build partnerships?",
        "language": "en",
        "concern": "career",
        "scoring_guide": "Does description match your actual deal-making strengths/weaknesses?",
        "verifiable": "natal",
    },
    {
        "id": "T04",
        "chart_id": RAMAN_CHART_ID,
        "question": "What is the core challenge in my financial life and what causes it?",
        "language": "en",
        "concern": "finance",
        "scoring_guide": "Does the diagnosis match what you know about your actual financial patterns?",
        "verifiable": "natal",
    },
    # CURRENT STATE — Mars MD Moon AD (Jan-Aug 2026)
    {
        "id": "T05",
        "chart_id": RAMAN_CHART_ID,
        "question": "How is my cash flow right now and what should I do about it?",
        "language": "en",
        "concern": "finance",
        "scoring_guide": "Is cash flow actually under pressure right now? Does advice match reality?",
        "verifiable": "current",
    },
    {
        "id": "T06",
        "chart_id": RAMAN_CHART_ID,
        "question": "What is the state of my key business partnerships right now?",
        "language": "en",
        "concern": "career",
        "scoring_guide": "Does description of partnership state match what you're experiencing?",
        "verifiable": "current",
    },
    {
        "id": "T07",
        "chart_id": RAMAN_CHART_ID,
        "question": "Is this a good time for me to negotiate deals?",
        "language": "en",
        "concern": "career",
        "scoring_guide": "Moon AD in 3H (communication/negotiation) — does it feel like a negotiation window?",
        "verifiable": "current",
    },
    # NEAR FUTURE — windows that will be verifiable by end of 2026
    {
        "id": "T08",
        "chart_id": RAMAN_CHART_ID,
        "question": "When exactly does my financial pressure ease and what triggers it?",
        "language": "en",
        "concern": "finance",
        "scoring_guide": "Note the exact date predicted. Score in Aug-Sep 2026.",
        "verifiable": "near_future",
    },
    {
        "id": "T09",
        "chart_id": RAMAN_CHART_ID,
        "question": "What changes in my income sources after August 2026?",
        "language": "en",
        "concern": "finance",
        "scoring_guide": "Score in Sep 2026 — did income sources actually shift?",
        "verifiable": "near_future",
    },
    {
        "id": "T10",
        "chart_id": RAMAN_CHART_ID,
        "question": "Will I close a significant deal before the end of 2026?",
        "language": "en",
        "concern": "career",
        "scoring_guide": "Score in Dec 2026 — did a significant deal close?",
        "verifiable": "near_future",
    },
    # ANDRES — cross-chart accuracy check
    {
        "id": "T11",
        "chart_id": ANDRES_CHART_ID,
        "question": "What is the state of my career right now and what's the next major shift?",
        "language": "es",
        "concern": "career",
        "scoring_guide": "Andres scores: does current career description match reality?",
        "verifiable": "current",
    },
    {
        "id": "T12",
        "chart_id": ANDRES_CHART_ID,
        "question": "What is my core strength as a professional and where does it show most?",
        "language": "es",
        "concern": "career",
        "scoring_guide": "Andres scores: does description of professional strength match self-knowledge?",
        "verifiable": "natal",
    },
    # SPECIFICITY TEST — these test whether predictions are specific enough to be falsifiable
    {
        "id": "T13",
        "chart_id": RAMAN_CHART_ID,
        "question": "Give me a specific prediction with an exact date for when my next major income breakthrough happens",
        "language": "en",
        "concern": "finance",
        "scoring_guide": "Does it give a specific date? Or just vague 'soon'? Specificity test.",
        "verifiable": "specificity_test",
    },
    {
        "id": "T14",
        "chart_id": RAMAN_CHART_ID,
        "question": "What was the most difficult period in my life between 2015 and 2020, and why?",
        "language": "en",
        "concern": "general",
        "scoring_guide": "Does it correctly identify the hardest period? You know the answer.",
        "verifiable": "past",
    },
    {
        "id": "T15",
        "chart_id": RAMAN_CHART_ID,
        "question": "What is my relationship with money — do I earn it easily or with struggle?",
        "language": "en",
        "concern": "finance",
        "scoring_guide": "Does the description match your actual lived experience with money?",
        "verifiable": "natal",
    },
]


async def run_question(client: httpx.AsyncClient, test: dict) -> dict:
    """Run one question against the predict endpoint."""
    try:
        resp = await client.post(
            f"{BASE_URL}/api/v1/predict",
            json={
                "chart_id": test["chart_id"],
                "question": test["question"],
                "language": test["language"],
                "use_json_context": True,
            },
            timeout=45.0,
        )
        data = resp.json()
        return {
            **test,
            "plain_summary":  data.get("plain_summary", ""),
            "signal_line":    data.get("signal_line", ""),
            "timing_window":  data.get("timing_window", ""),
            "confidence":     data.get("confidence", 0),
            "why_this":       data.get("why_this", ""),
            "action_item":    data.get("action_item", ""),
            "context_path":   data.get("context_path", "prose"),
            "ran_at":         datetime.now().isoformat(),
            "score":          None,  # to be filled manually
            "score_notes":    "",    # your notes
            "error":          None,
        }
    except Exception as e:
        return {
            **test,
            "plain_summary": "",
            "error": str(e),
            "ran_at": datetime.now().isoformat(),
            "score": None,
        }


async def main():
    print(f"Running {len(TEST_QUESTIONS)} accuracy test questions...")
    print(f"Chart: Raman ({RAMAN_CHART_ID[:8]}...) + Andres ({ANDRES_CHART_ID[:8]}...)")
    print()

    results = []
    async with httpx.AsyncClient() as client:
        for i, test in enumerate(TEST_QUESTIONS, 1):
            chart_name = "Raman" if test["chart_id"] == RAMAN_CHART_ID else "Andres"
            print(f"[{i:2d}/{len(TEST_QUESTIONS)}] {test['id']} ({chart_name}) — {test['question'][:50]}...")
            result = await run_question(client, test)
            results.append(result)

            if result.get("error"):
                print(f"         ❌ ERROR: {result['error']}")
            else:
                print(f"         ✅ {result['context_path']} | timing: {result['timing_window']} | conf: {result['confidence']}")
                print(f"         → {result['plain_summary'][:100]}...")
            print()

    # Save to file
    output = {
        "ran_at": datetime.now().isoformat(),
        "total_questions": len(results),
        "scoring_instructions": {
            "3": "Confirmed — happened exactly as predicted",
            "2": "Partial — directionally right, timing or details off",
            "1": "Wrong — didn't happen or opposite happened",
            "0": "Too early — window hasn't passed yet",
            "notes": "Fill in 'score' and 'score_notes' for each result. Then run: python score_accuracy.py"
        },
        "results": results,
    }

    with open("accuracy_test_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"✅ Results saved to accuracy_test_results.json")
    print()
    print("NEXT STEPS:")
    print("  1. Open accuracy_test_results.json")
    print("  2. For each result, fill in:")
    print('     "score": 3|2|1|0')
    print('     "score_notes": "your notes on why"')
    print("  3. Run: python score_accuracy.py")
    print()
    print("SCORING GUIDE:")
    print("  3 = Confirmed exactly")
    print("  2 = Partial / directionally right")
    print("  1 = Wrong")
    print("  0 = Too early to score (window not passed)")


if __name__ == "__main__":
    asyncio.run(main())
