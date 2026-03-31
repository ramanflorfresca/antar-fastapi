"""
test_c3_c4.py
Sprint C3 + C4 — Combined Verification

Tests Pattern Memory (C3) and Common Sense Layer (C4) together.

Run after deploying:
    python test_c3_c4.py

Tests:
  1. /patterns endpoint — prediction history + themes + unresolved
  2. Memory continuity — second question references first
  3. Diagnostic mode — same domain after window passed
  4. C4 age reframing — age-inappropriate question gets reframed
  5. C4 contradiction detection — opposing signals acknowledged
  6. Rating endpoint — user marks prediction accurate/inaccurate
  7. Accuracy shows in /patterns after rating
"""

import asyncio
import time
import httpx

BASE_URL      = "https://antar-fastapi-production.up.railway.app"
TEST_CHART_ID = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"


async def predict(client, question, concern, label=""):
    t0   = time.time()
    resp = await client.post(f"{BASE_URL}/api/v1/predict", json={
        "chart_id": TEST_CHART_ID,
        "question": question,
        "concern":  concern,
    })
    elapsed = round(time.time() - t0, 1)
    if resp.status_code != 200:
        print(f"  ❌ {label} — {resp.status_code}: {resp.text[:100]}")
        return None
    data = resp.json()
    print(f"  ✅ {label} ({elapsed}s)")
    print(f"     signal: {data.get('signal_line', '')}")
    print(f"     summary: {(data.get('plain_summary') or '')[:100]}...")
    return data


async def run():
    print("\n" + "="*60)
    print("SPRINT C3 + C4 — COMBINED VERIFICATION")
    print("="*60)

    async with httpx.AsyncClient(timeout=90.0) as client:

        # ── Test 1: /patterns baseline ────────────────────────────
        print("\n[1/7] GET /api/v1/patterns — baseline state...")
        resp = await client.get(f"{BASE_URL}/api/v1/patterns/{TEST_CHART_ID}")
        if resp.status_code != 200:
            print(f"  ❌ {resp.status_code}: {resp.text[:150]}")
        else:
            d = resp.json()
            print(f"  ✅ Total predictions: {d.get('total_predictions', 0)}")
            print(f"  Recurring themes:    {d.get('recurring_themes', [])}")
            print(f"  Unresolved cases:    {len(d.get('unresolved_cases', []))}")
            print(f"  Accuracy summary:    {d.get('accuracy_summary') or 'none yet'}")

            # Store a prediction id for rating test
            preds = d.get("predictions", [])
            first_pred_id = preds[0]["id"] if preds else None

        # ── Test 2: Memory continuity ──────────────────────────────
        print("\n[2/7] Ask career question #1 — seeds memory...")
        d1 = await predict(
            client,
            "What is the energy around my career right now?",
            "career",
            "Career Q1"
        )
        await asyncio.sleep(2)

        print("\n  Ask career question #2 — should reference Q1...")
        d2 = await predict(
            client,
            "Any update on my career situation from before?",
            "career",
            "Career Q2 (memory test)"
        )

        if d2:
            ps2 = (d2.get("plain_summary") or "").lower()
            continuity = any(w in ps2 for w in [
                "previously", "earlier", "last time", "as i mentioned",
                "before", "still", "continue", "remains", "update"
            ])
            print(f"\n  {'✅ Continuity detected' if continuity else '⚠️  No continuity language — check Railway logs for C3 memory loaded'}")
            print(f"  → Railway log should show: [predict] C3 memory loaded")

        # ── Test 3: Diagnostic mode ────────────────────────────────
        print("\n[3/7] Ask funding question — then ask again (diagnostic mode test)...")
        d3 = await predict(
            client,
            "I've been trying to raise funding for my startup. What does my chart say?",
            "funding",
            "Funding Q1"
        )
        await asyncio.sleep(2)

        print("\n  Ask funding again — should trigger diagnostic if window passed...")
        d4 = await predict(
            client,
            "I asked about funding before and it hasn't happened yet. What's blocking it?",
            "funding",
            "Funding Q2 (diagnostic test)"
        )

        if d4:
            ps4 = (d4.get("plain_summary") or "").lower()
            diagnostic_words = [
                "block", "delay", "hasn't", "did not", "didn't", "why",
                "obstacle", "extended", "closed", "new window", "different"
            ]
            found = [w for w in diagnostic_words if w in ps4]
            print(f"\n  {'✅ Diagnostic language detected: ' + str(found[:3]) if found else '⚠️  No diagnostic language — may need more past predictions with passed windows'}")
            print(f"  → Railway log should show: [predict] C3 DIAGNOSTIC MODE (if window has passed)")

        # ── Test 4: C4 age reframing ──────────────────────────────
        print("\n[4/7] C4 age reframing — ask children question (user is 51)...")
        d5 = await predict(
            client,
            "What does my chart say about having children?",
            "children",
            "Children Q (C4 reframe test)"
        )

        if d5:
            ps5 = (d5.get("plain_summary") or "").lower()
            reframe_words = [
                "legacy", "mentor", "creativity", "creative", "wisdom",
                "grandchildren", "adult children", "knowledge"
            ]
            found5 = [w for w in reframe_words if w in ps5]
            if found5:
                print(f"\n  ✅ C4 age reframe applied — found: {found5[:3]}")
            else:
                print(f"\n  ⚠️  No reframe words found — check Railway logs for:")
                print(f"     [predict] C4 common sense — XXX chars")
                print(f"     (C4 may be working but LLM may not have used the reframe)")

        # ── Test 5: C4 contradiction detection ────────────────────
        print("\n[5/7] C4 contradiction — ask to invest after 'hold' signal...")
        d6 = await predict(
            client,
            "Should I make a major investment right now?",
            "wealth",
            "Wealth invest Q (contradiction test)"
        )

        if d6:
            print(f"  → Check if signal acknowledges any tension with previous wealth advice")
            print(f"  → Railway log should show: [predict] C4 common sense — XXX chars")

        # ── Test 6: Rating endpoint ───────────────────────────────
        print("\n[6/7] POST /api/v1/predictions/{id}/rate...")
        if not first_pred_id:
            # Try getting one now
            r = await client.get(f"{BASE_URL}/api/v1/patterns/{TEST_CHART_ID}")
            if r.status_code == 200:
                preds = r.json().get("predictions", [])
                first_pred_id = preds[0]["id"] if preds else None

        if not first_pred_id:
            print("  ⚠️  No prediction id found — skipping rating test")
        else:
            resp_rate = await client.post(
                f"{BASE_URL}/api/v1/predictions/{first_pred_id}/rate",
                json={"rating": 1}
            )
            if resp_rate.status_code != 200:
                print(f"  ❌ {resp_rate.status_code}: {resp_rate.text[:150]}")
            else:
                print(f"  ✅ Rated prediction {str(first_pred_id)[:8]}... as accurate (1)")

            # Also rate one as inaccurate
            r2 = await client.get(f"{BASE_URL}/api/v1/patterns/{TEST_CHART_ID}")
            if r2.status_code == 200:
                preds2 = r2.json().get("predictions", [])
                if len(preds2) > 1:
                    second_id = preds2[1]["id"]
                    resp_rate2 = await client.post(
                        f"{BASE_URL}/api/v1/predictions/{second_id}/rate",
                        json={"rating": 0}
                    )
                    if resp_rate2.status_code == 200:
                        print(f"  ✅ Rated prediction {str(second_id)[:8]}... as inaccurate (0)")

        # ── Test 7: Accuracy in /patterns ─────────────────────────
        print("\n[7/7] Check accuracy summary in /patterns...")
        resp7 = await client.get(f"{BASE_URL}/api/v1/patterns/{TEST_CHART_ID}")
        if resp7.status_code != 200:
            print(f"  ❌ {resp7.status_code}")
        else:
            d7    = resp7.json()
            preds7 = d7.get("predictions", [])
            rated  = [p for p in preds7 if p.get("accuracy_rating") is not None]
            acc7   = d7.get("accuracy_summary", "")
            themes7 = d7.get("recurring_themes", [])
            unres7  = d7.get("unresolved_cases", [])

            print(f"  ✅ Total predictions: {len(preds7)}")
            print(f"  Rated: {len(rated)}")
            print(f"  Accuracy: {acc7 or 'need 2+ ratings'}")
            print(f"  Recurring themes: {themes7}")
            print(f"  Unresolved cases: {len(unres7)}")

            if unres7:
                for u in unres7[:2]:
                    print(f"    ⚠ {u.get('concern')}: {u.get('signal_line', '')[:60]}")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("C3 + C4 VERIFICATION COMPLETE")
    print("="*60)
    print("\nRailway logs to verify:")
    print("  [predict] C3 memory loaded — N past predictions")
    print("  [predict] C3 DIAGNOSTIC MODE — (same domain repeated)")
    print("  [predict] C4 common sense — XXX chars")
    print("\nFull C3+C4 working when:")
    print("  ✅ /patterns returns history, themes, unresolved cases")
    print("  ✅ Second question on same domain shows continuity language")
    print("  ✅ Children question for 51yo gets legacy/creativity framing")
    print("  ✅ Rating endpoint saves to DB")
    print("  ✅ Accuracy summary appears after 2+ ratings\n")


if __name__ == "__main__":
    asyncio.run(run())
