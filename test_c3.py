"""
test_c3.py
Sprint C3 — Pattern Memory Verification

Run after deploying:
    python test_c3.py

Tests:
  1. /patterns endpoint returns prediction history
  2. Memory block appears in predictions (Railway log check)
  3. Diagnostic mode triggers when same domain asked twice
  4. Rating endpoint works (POST /predictions/{id}/rate)
  5. Rated prediction shows in pattern summary
"""

import asyncio
import time
import httpx

BASE_URL      = "https://antar-fastapi-production.up.railway.app"
TEST_CHART_ID = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"


async def run():
    print("\n" + "="*60)
    print("SPRINT C3 — PATTERN MEMORY VERIFICATION")
    print("="*60)

    async with httpx.AsyncClient(timeout=60.0) as client:

        # ── Test 1: /patterns endpoint ────────────────────────────
        print("\n[1/5] GET /api/v1/patterns/{chart_id}...")
        resp = await client.get(f"{BASE_URL}/api/v1/patterns/{TEST_CHART_ID}")

        if resp.status_code != 200:
            print(f"  ❌ FAIL — returned {resp.status_code}: {resp.text[:200]}")
        else:
            data  = resp.json()
            total = data.get("total_predictions", 0)
            themes = data.get("recurring_themes", [])
            unresolved = data.get("unresolved_cases", [])
            acc = data.get("accuracy_summary", "")

            print(f"  ✅ Returned 200")
            print(f"  Total predictions in memory: {total}")
            print(f"  Recurring themes: {themes or 'none yet (need 2+ same domain)'}")
            print(f"  Unresolved cases: {len(unresolved)}")
            print(f"  Accuracy summary: {acc or 'none yet (need user ratings)'}")

            if total == 0:
                print("  ⚠️  No predictions yet — ask a few questions first")

            # Store a prediction id for rating test
            prediction_id = None
            preds = data.get("predictions", [])
            if preds:
                prediction_id = preds[0].get("id")
                print(f"  Using prediction: {str(prediction_id)[:8]}... for rating test")

        # ── Test 2: Memory appears in predict ─────────────────────
        print("\n[2/5] Ask career question — check memory is loaded...")
        t0   = time.time()
        resp2 = await client.post(f"{BASE_URL}/api/v1/predict", json={
            "chart_id": TEST_CHART_ID,
            "question": "What should I focus on for my career this month?",
            "concern":  "career"
        })
        elapsed = round(time.time() - t0, 1)

        if resp2.status_code != 200:
            print(f"  ❌ FAIL — {resp2.status_code}: {resp2.text[:150]}")
        else:
            data2 = resp2.json()
            ps    = data2.get("plain_summary", "") or ""
            sl    = data2.get("signal_line", "") or ""
            print(f"  ✅ /predict returned 200 in {elapsed}s")
            print(f"  signal_line:   {sl}")
            print(f"  plain_summary: {ps[:100]}...")
            print(f"  → Check Railway logs for: [predict] C3 memory loaded")

        # ── Test 3: Diagnostic mode trigger ───────────────────────
        print("\n[3/5] Ask same domain AGAIN — should trigger diagnostic mode...")
        await asyncio.sleep(1)

        t0   = time.time()
        resp3 = await client.post(f"{BASE_URL}/api/v1/predict", json={
            "chart_id": TEST_CHART_ID,
            "question": "I asked about career before — any update on the timing?",
            "concern":  "career"
        })
        elapsed = round(time.time() - t0, 1)

        if resp3.status_code != 200:
            print(f"  ❌ FAIL — {resp3.status_code}")
        else:
            data3 = resp3.json()
            ps3   = (data3.get("plain_summary") or "").lower()
            sl3   = data3.get("signal_line") or ""

            # Look for continuity signals — does Antar reference the previous prediction?
            continuity_words = [
                "previously", "last time", "before", "earlier", "as i mentioned",
                "still", "update", "since", "continue", "remains", "now"
            ]
            found = [w for w in continuity_words if w in ps3]

            print(f"  ✅ /predict returned 200 in {elapsed}s")
            print(f"  signal_line: {sl3}")
            if found:
                print(f"  ✅ Continuity language detected: {found[:3]}")
            else:
                print(f"  ⚠️  No continuity language found — check Railway logs for")
                print(f"     '[predict] C3 memory loaded' or '[predict] C3 DIAGNOSTIC MODE'")

        # ── Test 4: Rating endpoint ───────────────────────────────
        print("\n[4/5] POST /api/v1/predictions/{id}/rate ...")
        if not prediction_id:
            print("  ⚠️  No prediction_id from Test 1 — skipping")
        else:
            resp4 = await client.post(
                f"{BASE_URL}/api/v1/predictions/{prediction_id}/rate",
                json={"rating": 1}
            )
            if resp4.status_code != 200:
                print(f"  ❌ FAIL — {resp4.status_code}: {resp4.text[:150]}")
            else:
                data4 = resp4.json()
                print(f"  ✅ Rating saved: {data4}")

        # ── Test 5: Rating shows in pattern summary ───────────────
        print("\n[5/5] Check rating appears in /patterns...")
        resp5 = await client.get(f"{BASE_URL}/api/v1/patterns/{TEST_CHART_ID}")
        if resp5.status_code != 200:
            print(f"  ❌ FAIL — {resp5.status_code}")
        else:
            data5  = resp5.json()
            preds5 = data5.get("predictions", [])
            rated  = [p for p in preds5 if p.get("accuracy_rating") is not None]
            acc5   = data5.get("accuracy_summary", "")

            print(f"  ✅ Total predictions: {len(preds5)}")
            print(f"  Rated predictions: {len(rated)}")
            print(f"  Accuracy summary: {acc5 or 'need 2+ ratings to show'}")

            if rated:
                r = rated[0]
                print(f"  ✅ Rated prediction: {r.get('concern')} — "
                      f"rating={r.get('accuracy_rating')} "
                      f"status={r.get('fulfillment_status')}")

    print("\n" + "="*60)
    print("C3 VERIFICATION COMPLETE")
    print("="*60)
    print("\nRailway logs to verify:")
    print("  [predict] C3 memory loaded — N past predictions")
    print("  [predict] C3 DIAGNOSTIC MODE — (only when same domain repeats)")
    print("\nFull C3 is working when:")
    print("  ✅ /patterns returns prediction history")
    print("  ✅ Railway shows 'C3 memory loaded' on every predict")
    print("  ✅ Railway shows 'C3 DIAGNOSTIC MODE' when same domain asked twice")
    print("  ✅ /rate endpoint saves accuracy_rating to DB")
    print("  ✅ Rated predictions show in /patterns accuracy_summary\n")


if __name__ == "__main__":
    asyncio.run(run())
