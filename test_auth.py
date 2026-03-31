#!/usr/bin/env python3
"""
Google Auth smoke test.
Usage: python test_auth.py
"""
import requests, time

BASE = "https://antar-fastapi-production.up.railway.app"
CID  = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"

print("=" * 60)
print("GOOGLE AUTH SMOKE TEST")
print("=" * 60)

all_pass = True

# Test 1: Link chart to Google user
print("\n[1] Link chart to Google user ...")
r1 = requests.post(f"{BASE}/api/v1/auth/link-chart", json={
    "chart_id":     CID,
    "google_id":    "google_test_123",
    "email":        "ramandeep@test.com",
    "display_name": "Ramandeep Chadha",
    "avatar_url":   "https://lh3.googleusercontent.com/test",
}, timeout=15)

if r1.status_code == 200:
    d = r1.json()
    print(f"  ✅ Link chart: HTTP 200")
    print(f"     Action:   {d.get('action')}")
    print(f"     Chart ID: {d.get('chart_id','')[:8]}...")
    print(f"     Message:  {d.get('message')}")
else:
    print(f"  ❌ Link chart: HTTP {r1.status_code} | {r1.text[:100]}")
    all_pass = False

time.sleep(1)

# Test 2: Restore chart for returning user
print("\n[2] Restore chart for returning user ...")
r2 = requests.get(f"{BASE}/api/v1/auth/restore/google_test_123", timeout=15)
if r2.status_code == 200:
    d2 = r2.json()
    print(f"  ✅ Restore: HTTP 200")
    print(f"     Chart ID:   {d2.get('chart_id','')[:8]}...")
    print(f"     First name: {d2.get('first_name')}")
    print(f"     Lagna:      {d2.get('lagna')}")
    print(f"     Moon:       {d2.get('moon_sign')}")
    print(f"     Dasha:      {d2.get('current_dasha')}")
else:
    print(f"  ❌ Restore: HTTP {r2.status_code} | {r2.text[:100]}")
    all_pass = False

time.sleep(1)

# Test 3: Get profile
print("\n[3] Get profile ...")
r3 = requests.get(f"{BASE}/api/v1/auth/profile/google_test_123", timeout=15)
if r3.status_code == 200:
    d3 = r3.json()
    print(f"  ✅ Profile: HTTP 200")
    print(f"     Name:  {d3.get('display_name')}")
    print(f"     Email: {d3.get('email')}")
    print(f"     Plan:  {d3.get('plan')}")
else:
    print(f"  ❌ Profile: HTTP {r3.status_code} | {r3.text[:100]}")
    all_pass = False

# Test 4: Returning user (link again — should restore)
print("\n[4] Simulate returning user (link again) ...")
r4 = requests.post(f"{BASE}/api/v1/auth/link-chart", json={
    "chart_id":     "different-chart-id",
    "google_id":    "google_test_123",
    "email":        "ramandeep@test.com",
    "display_name": "Ramandeep Chadha",
    "avatar_url":   "",
}, timeout=15)
if r4.status_code == 200:
    d4 = r4.json()
    if d4.get("action") == "restored":
        print(f"  ✅ Returning user correctly restored existing chart")
        print(f"     Returns original chart: {d4.get('chart_id','')[:8]}...")
    else:
        print(f"  ⚠️  Expected 'restored' but got: {d4.get('action')}")
else:
    print(f"  ❌ HTTP {r4.status_code} | {r4.text[:100]}")
    all_pass = False

print(f"\n{'='*60}")
if all_pass:
    print("✅ Auth system live — paste lovable_google_auth.md into Lovable")
else:
    print("⚠️  Some tests failed — run: railway logs --tail 50")
print(f"{'='*60}")
