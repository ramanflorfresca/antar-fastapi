"""
test_sprint_d.py
Sprint D — Domain Intelligence Engine Verification

Tests that each domain gets its correct system prompt, 
domain-specific DKP context, and required elements in output.

Run after deploying:
    python test_sprint_d.py
"""

import asyncio
import time
import httpx

BASE_URL      = "https://antar-fastapi-production.up.railway.app"
TEST_CHART_ID = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"

# Domain test cases — question, concern, required words in output
DOMAIN_TESTS = [
    (
        "career",
        "What does my career chart say about my next move?",
        ["career", "authority", "window", "action"],
        "D10 Dashamsa or career chart language"
    ),
    (
        "finance",
        "What is my wealth picture right now?",
        ["wealth", "jupiter", "window", "investment"],
        "Wealth score or Jupiter language"
    ),
    (
        "health",
        "What should I watch for with my health?",
        ["health", "attention", "practice", "body"],
        "Health watch areas or dosha"
    ),
    (
        "legal",
        "I have a legal dispute — what does my chart say?",
        ["case", "saturn", "timing", "remedy"],
        "Legal verdict or Saturn language"
    ),
    (
        "foreign",
        "What does my chart say about moving abroad?",
        ["foreign", "rahu", "window", "destination"],
        "Foreign score or direction"
    ),
    (
        "funding",
        "Can I raise funding for my startup this year?",
        ["funding", "investor", "window", "action"],
        "11th house or funding type"
    ),
    (
        "marriage",
        "What does my chart say about marriage?",
        ["marriage", "partner", "timing", "remedy"],
        "7th house or partner nature"
    ),
    (
        "children",
        "What does my chart say about having children?",
        ["child", "legacy", "window", "remedy"],
        "5th house or Jupiter children reading"
    ),
    (
        "mental_health",
        "I am feeling anxious and stressed — what does my chart show?",
        ["moon", "pattern", "practice", "support"],
        "Moon condition or emotional theme"
    ),
]


async def predict(client, question, concern):
    t0 = time.time()
    resp = await client.post(f"{BASE_URL}/api/v1/predict", json={
        "chart_id": TEST_CHART_ID,
        "question": question,
        "concern":  concern,
    })
    elapsed = round(time.time() - t0, 1)
    return resp, elapsed


async def run():
    print("\n" + "="*60)
    print("SPRINT D — DOMAIN INTELLIGENCE ENGINE VERIFICATION")
    print("="*60)

    passed = 0
    failed = 0
    results = []

    async with httpx.AsyncClient(timeout=90.0) as client:

        for concern, question, required_words, description in DOMAIN_TESTS:
            print(f"\n[{concern.upper()}] {description}")
            resp, elapsed = await predict(client, question, concern)

            if resp.status_code != 200:
                print(f"  ❌ HTTP {resp.status_code}: {resp.text[:100]}")
                failed += 1
                results.append((concern, False, "HTTP error"))
                continue

            data = resp.json()
            ps   = (data.get("plain_summary") or "").lower()
            sl   = (data.get("signal_line")   or "").lower()
            ai   = (data.get("action_item")   or "").lower()
            full = ps + " " + sl + " " + ai

            found   = [w for w in required_words if w in full]
            missing = [w for w in required_words if w not in full]
            ok      = len(found) >= 2  # pass if at least 2 required words present

            if ok:
                passed += 1
                results.append((concern, True, found))
                print(f"  ✅ {elapsed}s — domain keywords found: {found}")
            else:
                failed += 1
                results.append((concern, False, missing))
                print(f"  ⚠️  {elapsed}s — missing keywords: {missing}")

            print(f"  signal: {data.get('signal_line', '')[:80]}")
            print(f"  summary: {(data.get('plain_summary') or '')[:100]}...")

        # ── Summary ───────────────────────────────────────────────
        print("\n" + "="*60)
        print(f"RESULTS: {passed}/{len(DOMAIN_TESTS)} domains passing")
        print("="*60)

        for concern, ok, detail in results:
            status = "✅" if ok else "⚠️ "
            print(f"  {status} {concern}: {detail}")

        print("\nRailway logs to verify:")
        print("  [predict] C3 memory loaded")
        print("  [predict] C4 common sense — XXX chars")
        print("  No 'build_concern_system_prompt' errors")
        print("\nDomain system prompts are working when:")
        print("  ✅ Career answer references D10 / authority / specific timing")
        print("  ✅ Health answer references body system / dosha / practices")
        print("  ✅ Legal answer gives direct verdict / timing / two remedies")
        print("  ✅ Children answer reframes as legacy/mentoring for 51yo chart\n")


if __name__ == "__main__":
    asyncio.run(run())
