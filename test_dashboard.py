#!/usr/bin/env python3
"""
Dashboard + compatibility smoke test.
Usage: python test_dashboard.py
"""
import requests, time

BASE = "https://antar-fastapi-production.up.railway.app"
CID  = "6849e41a-a70c-4dd8-a6a9-b1d83b9691c8"  # real chart

print("=" * 60)
print("DASHBOARD + COMPATIBILITY SMOKE TEST")
print("=" * 60)

all_pass = True

# Test 1: Dashboard
print("\n[1] Dashboard endpoint ...")
r = requests.get(f"{BASE}/api/v1/dashboard/{CID}", timeout=20)
if r.status_code == 200:
    d = r.json()
    print(f"  ✅ GET /dashboard: HTTP 200")
    print(f"     Name:          {d.get('first_name')}")
    print(f"     Lagna:         {d.get('lagna')}")
    print(f"     Moon:          {d.get('moon_sign')} / {d.get('moon_nakshatra')}")
    print(f"     Dasha:         {d.get('dasha')}")
    print(f"     Has signal:    {d.get('has_signal')}")
    print(f"     Day quality:   {d.get('day_quality')}")
    print(f"     Unread alerts: {d.get('unread_alerts')}")
    print(f"     Accuracy:      {d.get('accuracy_pct')}%")
    print(f"     Plan:          {d.get('plan')}")
    print(f"     Pred used:     {d.get('pred_used')}/{d.get('pred_limit')}")
    print(f"     Compat used:   {d.get('compat_used')}/{d.get('compat_limit')}")
else:
    print(f"  ❌ Dashboard: HTTP {r.status_code} | {r.text[:100]}")
    all_pass = False

time.sleep(1)

# Test 2: Compatibility sessions list
print("\n[2] Compatibility sessions list ...")
r2 = requests.get(f"{BASE}/api/v1/compatibility/sessions/{CID}", timeout=15)
if r2.status_code == 200:
    d2 = r2.json()
    print(f"  ✅ GET /compatibility/sessions: HTTP 200")
    print(f"     Session count: {d2.get('count')}")
    for s in d2.get("sessions",[])[:3]:
        print(f"     - {s.get('name_b')} ({s.get('compat_type')}) "
              f"score={s.get('score')} layers={s.get('layers_done')}")
else:
    print(f"  ❌ Sessions list: HTTP {r2.status_code} | {r2.text[:100]}")
    all_pass = False

time.sleep(1)

# Test 3: Compatibility still works
print("\n[3] Compatibility start ...")
r3 = requests.post(f"{BASE}/api/v1/compatibility/start", json={
    "chart_id_a":       CID,
    "name_a":           "Ramandeep",
    "name_b":           "Test",
    "birth_date_b":     "1990-05-15",
    "birth_time_b":     "10:00",
    "birth_city_b":     "Mumbai",
    "birth_country_b":  "IN",
    "compatibility_type": "relationship",
}, timeout=45)
if r3.status_code == 200:
    d3 = r3.json()
    print(f"  ✅ Compatibility start: HTTP 200")
    print(f"     Session: {d3.get('session_id','')[:8]}...")
    print(f"     Score:   {d3.get('score') or 'extracted from text'}")
elif r3.status_code == 429:
    print(f"  ✅ Limit enforced: {r3.json().get('detail',{}).get('message','')}")
else:
    print(f"  ❌ Compatibility: HTTP {r3.status_code} | {r3.text[:100]}")
    all_pass = False

print(f"\n{'='*60}")
if all_pass:
    print("✅ All passing — paste lovable_dashboard.md into Lovable")
else:
    print("⚠️  Some failed — run: railway logs --tail 50")
print(f"{'='*60}")
