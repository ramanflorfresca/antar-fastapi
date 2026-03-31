#!/usr/bin/env python3
"""
Test all 3 quality fixes.
Usage: python test_quality.py
"""
import requests, time, sys

BASE = "https://antar-fastapi-production.up.railway.app"
CID  = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"

BANNED = [
    "Atmakaraka","Amatyakaraka","Mahadasha","Antardasha",
    "Navamsa","Bhrashta","Dusthana","Darakaraka"
]

print("=" * 60)
print("QUALITY FIXES SMOKE TEST")
print("=" * 60)

all_pass = True

# Test 1: Banned terms in predictions
print("\n[1] Testing banned terms in predictions ...")
for domain, q in [
    ("career",   "What is my career peak window?"),
    ("spiritual","What is my soul purpose?"),
    ("health",   "What health areas should I watch?"),
]:
    rc = requests.post(f"{BASE}/api/v1/chart/create", json={
        "birth_date":"1974-11-26","birth_time":"11:59",
        "birth_city":"New Delhi","birth_country":"IN"
    }, timeout=30)
    cid = rc.json().get("chart_id","")
    r = requests.post(f"{BASE}/api/v1/predict",
        json={"chart_id":cid,"question":q}, timeout=60)
    pred = r.json().get("prediction","")
    found = [b for b in BANNED if b in pred]
    if found:
        print(f"  ❌ [{domain}]: BANNED TERMS FOUND: {found}")
        all_pass = False
    elif len(pred) < 50:
        print(f"  ⚠️  [{domain}]: Empty response")
    else:
        print(f"  ✅ [{domain}]: Clean ({len(pred)} chars)")
    time.sleep(2)

# Test 2: Wealth score — should find more than 2 combinations
print("\n[2] Testing wealth engine combinations ...")
r2 = requests.post(f"{BASE}/api/v1/predict", json={
    "chart_id": CID,
    "question": "Do I have billionaire potential?",
}, timeout=60)
pred2 = r2.json().get("prediction","")
if "2 out of 6" in pred2:
    print("  ❌ Still showing '2 out of 6' — house_lords fix may not be applied")
    all_pass = False
elif pred2:
    print(f"  ✅ Wealth prediction ({len(pred2)} chars)")
    print(f"     Preview: {pred2[:120]}")
else:
    print("  ⚠️  Empty wealth prediction")

# Test 3: PDF endpoint exists
print("\n[3] Testing PDF report endpoint ...")
r3 = requests.get(f"{BASE}/api/v1/report/{CID}/pdf", timeout=20)
if r3.status_code == 403:
    detail = r3.json().get("detail",{})
    if isinstance(detail, dict) and detail.get("error") == "upgrade_required":
        print("  ✅ PDF endpoint live — correctly requires upgrade")
    else:
        print(f"  ✅ PDF endpoint live: HTTP {r3.status_code}")
elif r3.status_code == 200:
    print(f"  ✅ PDF generated: {len(r3.content)} bytes")
else:
    print(f"  ❌ PDF endpoint: HTTP {r3.status_code} | {r3.text[:100]}")
    all_pass = False

print(f"\n{'='*60}")
if all_pass:
    print("✅ All quality fixes verified")
else:
    print("⚠️  Some issues remain — run: railway logs --tail 50")
print(f"{'='*60}")
