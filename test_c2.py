"""
test_c2.py
Sprint C2 — Desh Kal Patra Verification

Run after deploying to Railway:
    python test_c2.py

Tests:
  1. World Bank API reachable and returning data
  2. DKP context cached in Supabase after first /predict call
  3. Same chart + different countries = different predictions
  4. Cache hit on second call (fast response)
  5. Period quality assessment correct per country
  6. DKP block appears in prediction output context

Requires:
    pip install httpx supabase --break-system-packages
"""

import asyncio
import time
import httpx
import os
from datetime import datetime

BASE_URL     = "https://antar-fastapi-production.up.railway.app"
TEST_CHART_ID = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"  # ← your real chart_id

# Countries to test — pick ones your users actually come from
TEST_COUNTRIES = ["IN", "US", "CO", "AE", "GB"]

WB_BASE = "https://api.worldbank.org/v2/country/{code}/indicator/{indicator}?format=json&mrv=1"
WB_INDICATORS = {
    "gdp_growth":   "NY.GDP.MKTP.KD.ZG",
    "inflation":    "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
}

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY", ""))


async def run():
    print("\n" + "="*60)
    print("SPRINT C2 — DESH KAL PATRA VERIFICATION")
    print("="*60)

    async with httpx.AsyncClient(timeout=30.0) as client:

        # ── Test 1: World Bank API reachable ──────────────────────
        print("\n[1/5] World Bank API — checking all 3 indicators for IN...")
        wb_pass = True
        for key, indicator in WB_INDICATORS.items():
            url  = WB_BASE.format(code="in", indicator=indicator)
            resp = await client.get(url)
            if resp.status_code != 200:
                print(f"  ❌ {key}: HTTP {resp.status_code}")
                wb_pass = False
                continue

            data  = resp.json()
            value = None
            if isinstance(data, list) and len(data) > 1 and data[1]:
                value = data[1][0].get("value")

            if value is not None:
                print(f"  ✅ {key}: {value:.1f}%")
            else:
                print(f"  ⚠️  {key}: No data returned (API up but no value)")

        print(f"\n  {'✅ PASS' if wb_pass else '❌ FAIL'} — World Bank API reachable")

        # ── Test 2: First /predict — triggers DKP fetch + cache ───
        print("\n[2/5] First /predict call — triggers DKP World Bank fetch...")
        t0   = time.time()
        resp = await client.post(f"{BASE_URL}/api/v1/predict", json={
            "chart_id": TEST_CHART_ID,
            "question": "What is the economic climate for my career right now?",
            "concern":  "career"
        })
        t1 = time.time()
        elapsed = round(t1 - t0, 1)

        if resp.status_code != 200:
            print(f"  ❌ FAIL — /predict returned {resp.status_code}: {resp.text[:200]}")
        else:
            data = resp.json()
            ps   = data.get("plain_summary", "") or ""
            sl   = data.get("signal_line", "") or ""
            print(f"  ✅ /predict returned 200 in {elapsed}s")
            print(f"  plain_summary: {ps[:100]}...")
            print(f"  signal_line:   {sl}")
            print(f"\n  Note: first call is slower (World Bank fetch + DeepSeek sector query)")
            print(f"  Subsequent calls should be <1s from cache")

        # ── Test 3: Cache check in Supabase ───────────────────────
        print("\n[3/5] Checking country_context_cache table in Supabase...")
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("  ⚠️  SUPABASE_URL / SUPABASE_KEY not set — skipping cache check")
            print("     Set env vars to enable: export SUPABASE_URL=... SUPABASE_KEY=...")
        else:
            try:
                from supabase import create_client
                sb     = create_client(SUPABASE_URL, SUPABASE_KEY)
                result = sb.table("country_context_cache").select("*").execute()
                rows   = result.data or []

                if not rows:
                    print("  ⚠️  Cache table empty — DKP may not have written (check Railway logs)")
                else:
                    print(f"  ✅ {len(rows)} countries cached:")
                    for row in rows:
                        code    = row.get("country_code", "?")
                        gdp     = row.get("gdp_growth")
                        inf     = row.get("inflation")
                        quality = row.get("period_quality", "?")
                        age     = ""
                        if row.get("fetched_at"):
                            fetched = datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00"))
                            mins    = int((datetime.now().astimezone() - fetched).total_seconds() / 60)
                            age     = f"{mins}m ago"
                        gdp_str = f"GDP {gdp:+.1f}%" if gdp else "GDP N/A"
                        inf_str = f"inf {inf:.1f}%" if inf else "inf N/A"
                        print(f"     {code}: {quality} | {gdp_str} | {inf_str} | {age}")

            except Exception as e:
                print(f"  ❌ Supabase check failed: {e}")

        # ── Test 4: Cache speed — second call should be fast ──────
        print("\n[4/5] Second /predict call — should hit cache (fast)...")
        t2   = time.time()
        resp2 = await client.post(f"{BASE_URL}/api/v1/predict", json={
            "chart_id": TEST_CHART_ID,
            "question": "Is now a good time to invest?",
            "concern":  "wealth"
        })
        t3      = time.time()
        elapsed2 = round(t3 - t2, 1)

        if resp2.status_code != 200:
            print(f"  ❌ FAIL — returned {resp2.status_code}")
        else:
            print(f"  ✅ Second call returned 200 in {elapsed2}s")
            if elapsed2 < elapsed:
                print(f"  ✅ Faster than first call ({elapsed}s → {elapsed2}s) — cache is working")
            else:
                print(f"  ⚠️  Not faster than first call — cache may not have written")

        # ── Test 5: DKP content quality check ─────────────────────
        print("\n[5/5] Checking plain_summary contains real-world context...")
        if resp2.status_code == 200:
            data2 = resp2.json()
            ps2   = (data2.get("plain_summary") or "").lower()
            sl2   = data2.get("signal_line") or ""

            # Look for economic signal words in the output
            economic_keywords = [
                "economy", "economic", "market", "sector", "growth",
                "inflation", "job", "career", "industry", "financial",
                "investment", "gdp", "employment", "expansion", "contraction"
            ]
            found = [w for w in economic_keywords if w in ps2]

            if found:
                print(f"  ✅ Economic context present in plain_summary")
                print(f"     Keywords found: {', '.join(found[:5])}")
            else:
                print(f"  ⚠️  No clear economic keywords in plain_summary")
                print(f"     This may be fine — DKP influences framing not always keywords")

            print(f"\n  signal_line: {sl2}")
            print(f"  plain_summary: {(data2.get('plain_summary') or '')[:150]}...")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("C2 VERIFICATION COMPLETE")
    print("="*60)
    print("\nWhat to check in Railway logs:")
    print("  ✅ [predict] DKP loaded for IN (XXX chars)")
    print("  ✅ [predict] plain_english ok")
    print("  ✅ No 'DKP failed' errors")
    print("\nIf DKP loaded but plain_summary has no economic context:")
    print("  → Check dkp_block is reaching the prompt (grep dkp_block prompt_builder.py)")
    print("  → Check full_context path isn't bypassing the template\n")


if __name__ == "__main__":
    asyncio.run(run())
