"""
test_c1.py
Sprint C1 — Verification Tests

Run after deploying to Railway:
    python test_c1.py

Requires:
    pip install httpx --break-system-packages
    
Set your test chart_id at the top before running.
"""

import asyncio
import httpx
import json

BASE_URL = "https://antar-fastapi-production.up.railway.app"
TEST_CHART_ID = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"  # ← replace with real chart_id

BANNED_TERMS = [
    "mahadasha", "antardasha", "atmakaraka", "amatyakaraka",
    "navamsa", "lagna", "nakshatra", "rashi", "bhava", "graha"
]

FIVE_QUESTIONS = [
    ("career",  "Should I change jobs this year?"),
    ("wealth",  "Is this a good time to invest?"),
    ("love",    "What is the energy around my relationship right now?"),
    ("health",  "What should I watch for with my health this month?"),
    ("foreign", "Are there opportunities abroad for me?"),
]


async def run():
    async with httpx.AsyncClient(timeout=60.0) as client:

        print("\n" + "="*60)
        print("SPRINT C1 VERIFICATION")
        print("="*60)

        # ── Test 1: /predict returns plain English fields ─────────
        print("\n[1/4] Testing /predict returns plain English fields...")
        resp = await client.post(f"{BASE_URL}/api/v1/predict", json={
            "chart_id": TEST_CHART_ID,
            "question": "Should I change jobs this year?",
            "concern":  "career"
        })

        if resp.status_code != 200:
            print(f"  ❌ FAIL — /predict returned {resp.status_code}")
            print(f"     {resp.text[:200]}")
        else:
            data = resp.json()
            checks = {
                "plain_summary":  bool(data.get("plain_summary")),
                "action_item":    bool(data.get("action_item")),
                "signal_line":    bool(data.get("signal_line")),
                "timing_window":  bool(data.get("timing_window")),
                "signal_confidence": data.get("signal_confidence") in ("high", "medium", "low"),
                "all_domains":    isinstance(data.get("all_domains"), list),
            }
            all_pass = all(checks.values())
            for k, v in checks.items():
                print(f"  {'✅' if v else '❌'} {k}: {str(data.get(k, 'MISSING'))[:80]}")
            print(f"\n  {'✅ PASS' if all_pass else '❌ FAIL'} — /predict plain English fields")

        # ── Test 2: Zero jargon in plain_summary ──────────────────
        print("\n[2/4] Checking for banned jargon in plain_summary...")
        if resp.status_code == 200:
            data = resp.json()
            ps = (data.get("plain_summary") or "").lower()
            ai = (data.get("action_item") or "").lower()
            found_jargon = []
            for term in BANNED_TERMS:
                if term in ps or term in ai:
                    found_jargon.append(term)
            if found_jargon:
                print(f"  ❌ FAIL — banned terms found: {found_jargon}")
            else:
                print(f"  ✅ PASS — zero jargon in plain_summary + action_item")

        # ── Test 3: /predictions endpoint ─────────────────────────
        print("\n[3/4] Testing GET /api/v1/predictions/{chart_id}...")
        resp2 = await client.get(f"{BASE_URL}/api/v1/predictions/{TEST_CHART_ID}?limit=5")
        if resp2.status_code != 200:
            print(f"  ❌ FAIL — returned {resp2.status_code}: {resp2.text[:200]}")
        else:
            data2 = resp2.json()
            preds = data2.get("predictions", [])
            print(f"  ✅ Returned {len(preds)} predictions")
            if preds:
                first = preds[0]
                has_summary = bool(first.get("plain_summary"))
                print(f"  {'✅' if has_summary else '⚠️ '} First prediction has plain_summary: {has_summary}")

        # ── Test 4: domain-signals after 5 questions ──────────────
        print("\n[4/4] Seeding 5 domain questions then checking domain-signals...")
        for domain, question in FIVE_QUESTIONS:
            r = await client.post(f"{BASE_URL}/api/v1/predict", json={
                "chart_id": TEST_CHART_ID,
                "question": question,
                "concern":  domain
            })
            print(f"  {'✅' if r.status_code == 200 else '❌'} {domain}: {r.status_code}")

        resp3 = await client.get(f"{BASE_URL}/api/v1/domain-signals/{TEST_CHART_ID}")
        if resp3.status_code != 200:
            print(f"  ❌ FAIL — domain-signals returned {resp3.status_code}")
        else:
            data3 = resp3.json()
            signals = data3.get("signals", {})
            found = [d for d in ["career", "wealth", "love", "health", "foreign"] if signals.get(d)]
            print(f"\n  ✅ Domain signals populated: {found}")
            for d in found:
                sl = signals[d].get("signal_line", "")[:60]
                print(f"     {d}: {sl}")

        print("\n" + "="*60)
        print("C1 VERIFICATION COMPLETE")
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(run())
