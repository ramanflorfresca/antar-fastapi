import asyncio, time, httpx

BASE_URL      = "https://antar-fastapi-production.up.railway.app"
TEST_CHART_ID = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"

DOMAIN_TESTS = [
    ("career",       "What does my career chart say about my next move?",        ["career","authority","window"]),
    ("finance",      "What is my wealth picture right now?",                     ["wealth","income","surge"]),
    ("health",       "What should I watch for with my health?",                  ["health","attention","practice"]),
    ("legal",        "I have a legal dispute — what does my chart say?",         ["legal","case","victory"]),
    ("foreign",      "What does my chart say about moving abroad?",              ["foreign","window"]),
    ("funding",      "Can I raise funding for my startup this year?",            ["funding","investor","window"]),
    ("marriage",     "What does my chart say about marriage?",                   ["marriage","partner","timing"]),
    ("children",     "What does my chart say about having children?",            ["child","window"]),
    ("mental_health","I am feeling anxious and stressed — what does my chart show?", ["stress","anxiety","relief"]),
]

async def run():
    print("\n" + "="*60)
    print("SPRINT D — DOMAIN INTELLIGENCE VERIFICATION")
    print("="*60)
    passed = 0
    async with httpx.AsyncClient(timeout=90.0) as client:
        for concern, question, required in DOMAIN_TESTS:
            t0   = time.time()
            resp = await client.post(f"{BASE_URL}/api/v1/predict", json={
                "chart_id": TEST_CHART_ID,
                "question": question,
                "concern":  concern,
            })
            elapsed = round(time.time() - t0, 1)
            if resp.status_code != 200:
                print(f"\n  ❌ [{concern}] HTTP {resp.status_code}")
                continue
            data  = resp.json()
            full  = " ".join([
                (data.get("plain_summary") or ""),
                (data.get("signal_line")   or ""),
                (data.get("action_item")   or ""),
            ]).lower()
            found   = [w for w in required if w in full]
            ok      = len(found) >= 2
            passed += int(ok)
            status  = "✅" if ok else "⚠️ "
            print(f"\n  {status} [{concern}] {elapsed}s — found: {found}")
            print(f"     signal: {data.get('signal_line','')[:80]}")

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{len(DOMAIN_TESTS)} domains passing")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(run())
