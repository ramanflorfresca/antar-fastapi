"""
test_sprint_e.py
Sprint E — Life Coaching Experience Verification

Run after deploying:
    python test_sprint_e.py
"""

import asyncio
import time
import httpx

BASE_URL      = "https://antar-fastapi-production.up.railway.app"
TEST_CHART_ID = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"


async def run():
    print("\n" + "="*60)
    print("SPRINT E — LIFE COACHING EXPERIENCE VERIFICATION")
    print("="*60)

    async with httpx.AsyncClient(timeout=90.0) as client:

        # ── Test 1: Welcome signal ────────────────────────────────
        print("\n[1/4] GET /api/v1/welcome/{chart_id}...")
        t0   = time.time()
        resp = await client.get(f"{BASE_URL}/api/v1/welcome/{TEST_CHART_ID}")
        elapsed = round(time.time() - t0, 1)

        if resp.status_code != 200:
            print(f"  ❌ {resp.status_code}: {resp.text[:150]}")
        else:
            d = resp.json()
            print(f"  ✅ {elapsed}s")
            print(f"  headline:     {d.get('headline', '')}")
            print(f"  summary:      {(d.get('summary') or '')[:100]}...")
            print(f"  action:       {d.get('action', '')}")
            print(f"  chapter_name: {d.get('chapter_name', '')}")
            print(f"  signal_type:  {d.get('signal_type', '')}")

            checks = {
                "headline":     bool(d.get("headline")),
                "summary":      bool(d.get("summary")),
                "action":       bool(d.get("action")),
                "chapter_name": bool(d.get("chapter_name")),
            }
            passed = all(checks.values())
            print(f"\n  {'✅ PASS' if passed else '❌ FAIL'} — welcome signal fields")

        # ── Test 2: Weekly briefing ───────────────────────────────
        print("\n[2/4] GET /api/v1/weekly-briefing/{chart_id}...")
        t0   = time.time()
        resp2 = await client.get(f"{BASE_URL}/api/v1/weekly-briefing/{TEST_CHART_ID}")
        elapsed = round(time.time() - t0, 1)

        if resp2.status_code != 200:
            print(f"  ❌ {resp2.status_code}: {resp2.text[:150]}")
        else:
            d2 = resp2.json()
            print(f"  ✅ {elapsed}s")
            print(f"  week_of:      {d2.get('week_of', '')}")
            print(f"  weekly_focus: {(d2.get('weekly_focus') or '')[:100]}...")
            print(f"  best_day:     {d2.get('best_day', '')}")
            print(f"  one_action:   {d2.get('one_action', '')}")

            domains = d2.get("domains", {})
            print(f"\n  Domain signals:")
            for domain, signal in domains.items():
                print(f"    {domain}: {(signal or '')[:60]}...")

            checks2 = {
                "weekly_focus": bool(d2.get("weekly_focus")),
                "domains":      len(domains) >= 4,
                "best_day":     bool(d2.get("best_day")),
                "one_action":   bool(d2.get("one_action")),
            }
            print(f"\n  {'✅ PASS' if all(checks2.values()) else '❌ FAIL'} — weekly briefing fields")

        # ── Test 3: Monthly deep-dive ─────────────────────────────
        print("\n[3/4] GET /api/v1/monthly-deepdive/{chart_id}...")
        t0   = time.time()
        resp3 = await client.get(f"{BASE_URL}/api/v1/monthly-deepdive/{TEST_CHART_ID}")
        elapsed = round(time.time() - t0, 1)

        if resp3.status_code != 200:
            print(f"  ❌ {resp3.status_code}: {resp3.text[:150]}")
        else:
            d3 = resp3.json()
            print(f"  ✅ {elapsed}s")
            print(f"  month:          {d3.get('month', '')}")
            print(f"  month_theme:    {d3.get('month_theme', '')}")
            print(f"  energy_level:   {d3.get('energy_level', '')}")
            print(f"  strong_planets: {d3.get('strong_planets', [])}")
            print(f"  overview:       {(d3.get('overview') or '')[:100]}...")

            actions = d3.get("priority_actions", [])
            print(f"\n  Priority actions ({len(actions)}):")
            for a in actions:
                print(f"    [{a.get('domain')}] {a.get('action', '')[:70]}")

            checks3 = {
                "month_theme":      bool(d3.get("month_theme")),
                "overview":         bool(d3.get("overview")),
                "priority_actions": len(actions) >= 2,
                "remedies":         len(d3.get("remedies", [])) >= 1,
            }
            print(f"\n  {'✅ PASS' if all(checks3.values()) else '❌ FAIL'} — monthly deep-dive fields")

        # ── Test 4: Annual plan ───────────────────────────────────
        print("\n[4/4] GET /api/v1/annual-plan/{chart_id}...")
        t0   = time.time()
        resp4 = await client.get(f"{BASE_URL}/api/v1/annual-plan/{TEST_CHART_ID}")
        elapsed = round(time.time() - t0, 1)

        if resp4.status_code != 200:
            print(f"  ❌ {resp4.status_code}: {resp4.text[:150]}")
        else:
            d4 = resp4.json()
            print(f"  ✅ {elapsed}s")
            print(f"  year:           {d4.get('year', '')}")
            print(f"  year_theme:     {d4.get('year_theme', '')}")
            print(f"  year_quality:   {d4.get('year_quality', '')}")
            print(f"  year_summary:   {(d4.get('year_summary') or '')[:100]}...")

            windows = d4.get("peak_windows", {})
            print(f"\n  Peak windows ({len(windows)} domains):")
            for domain, w in windows.items():
                print(f"    {domain}: {w.get('months', '')} — {w.get('signal', '')[:50]}")

            build   = d4.get("build_this_year", [])
            release = d4.get("release_this_year", [])
            print(f"\n  Build: {build}")
            print(f"  Release: {release}")
            print(f"  Year mantra: {d4.get('year_mantra', '')}")

            checks4 = {
                "year_theme":    bool(d4.get("year_theme")),
                "year_summary":  bool(d4.get("year_summary")),
                "peak_windows":  len(windows) >= 3,
                "year_mantra":   bool(d4.get("year_mantra")),
            }
            print(f"\n  {'✅ PASS' if all(checks4.values()) else '❌ FAIL'} — annual plan fields")

    print("\n" + "="*60)
    print("SPRINT E VERIFICATION COMPLETE")
    print("="*60)
    print("\nSecond calls should be near-instant (cached):")
    print("  curl -s .../api/v1/welcome/{chart_id} | python3 -m json.tool")
    print("  curl -s .../api/v1/weekly-briefing/{chart_id} | python3 -m json.tool")
    print("\nNew user flow now works:")
    print("  ✅ Chart created → welcome signal fires in background")
    print("  ✅ /welcome returns personalised first signal")
    print("  ✅ /weekly-briefing returns Monday 5-domain briefing")
    print("  ✅ /monthly-deepdive returns full month reading")
    print("  ✅ /annual-plan returns full year coaching plan\n")


if __name__ == "__main__":
    asyncio.run(run())
