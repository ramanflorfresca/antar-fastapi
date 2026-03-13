"""
api_smoke_test.py
=================
Layer 2 — API endpoint smoke test.
Requires the server to be running: uvicorn main:app --host 0.0.0.0 --port 8000

Creates a real Sam K chart, then exercises every downstream endpoint.
Prints a full pass/fail table. Exits 1 if any test fails.

Run:
    cd antarai
    pip install httpx python-dotenv
    python api_smoke_test.py [--base-url http://localhost:8000]
"""

import sys
import json
import time
import argparse
import os

try:
    import httpx
except ImportError:
    print("pip install httpx")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="http://localhost:8000")
parser.add_argument("--auth-token", default=os.getenv("ANTAR_TEST_TOKEN", ""))
args = parser.parse_args()

BASE = args.base_url.rstrip("/")
TOKEN = args.auth_token
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# Sam K birth data
BIRTH_PAYLOAD = {
    "birth_date":    "1970-11-02",
    "birth_time":    "14:30",
    "birth_city":    "Mumbai",
    "birth_country": "IN",
    "name":          "Sam K (test)",
    "language":      "en",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"
results = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    icon = PASS if condition else FAIL
    print(f"{icon}  {label}  {('← ' + str(detail)) if detail and not condition else ''}")
    results.append((status, label))
    return condition


def section(title):
    print(f"\n{'─'*64}")
    print(f"  {title}")
    print(f"{'─'*64}")


def post(path, payload, headers=None, timeout=30):
    try:
        r = httpx.post(f"{BASE}{path}", json=payload,
                       headers={**HEADERS, **(headers or {})}, timeout=timeout)
        return r
    except Exception as e:
        print(f"  REQUEST ERROR {path}: {e}")
        return None


def get(path, params=None, headers=None, timeout=20):
    try:
        r = httpx.get(f"{BASE}{path}", params=params or {},
                      headers={**HEADERS, **(headers or {})}, timeout=20)
        return r
    except Exception as e:
        print(f"  REQUEST ERROR {path}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 0 — Health check
# ─────────────────────────────────────────────────────────────────────────────
section("0 · Health check")

r = get("/health")
if not check("GET /health → 200", r and r.status_code == 200,
             r.status_code if r else "no response"):
    print(f"\n  Server not reachable at {BASE}. Start with:")
    print(f"    uvicorn main:app --host 0.0.0.0 --port 8000\n")
    sys.exit(1)

data = r.json()
check("Response has 'status'", "status" in data)
check("status = ok",           data.get("status") == "ok")


# ─────────────────────────────────────────────────────────────────────────────
# 1 — Create chart
# ─────────────────────────────────────────────────────────────────────────────
section("1 · POST /api/v1/chart/create")

r = post("/api/v1/chart/create", BIRTH_PAYLOAD)
check("Request succeeded",    r is not None)
check("Status 200",           r and r.status_code == 200, r.status_code if r else "—")

chart_id = None
if r and r.status_code == 200:
    data = r.json()
    chart_id = data.get("chart_id")
    check("chart_id present",       bool(chart_id))
    check("lagna = Libra",          data.get("lagna") == "Libra", data.get("lagna"))
    check("moon_sign present",      bool(data.get("moon_sign")))
    check("dasha_count > 0",        (data.get("dasha_count") or 0) > 0)
    check("atmakaraka present",     bool(data.get("atmakaraka")))
    print(f"  chart_id: {chart_id}")
    print(f"  lagna: {data.get('lagna')}  |  moon: {data.get('moon_sign')}")
    print(f"  dasha_count: {data.get('dasha_count')}")

if not chart_id:
    print(f"\n  Cannot continue without chart_id. Aborting.")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# 2 — Get chart
# ─────────────────────────────────────────────────────────────────────────────
section("2 · GET /api/v1/chart/{chart_id}")

r = get(f"/api/v1/chart/{chart_id}")
check("Status 200",              r and r.status_code == 200)
if r and r.status_code == 200:
    data = r.json()
    check("id matches",          data.get("id") == chart_id)
    check("chart_data.lagna",    "lagna" in data)
    check("chart_data.planets",  "planets" in data)
    check("lal_kitab key present", "lal_kitab" in data)

    lk = data.get("lal_kitab") or {}
    check("lk age = 55",         lk.get("age") == 55,       f"got {lk.get('age')}")
    check("lk table_age = 56",   lk.get("table_age") == 56, f"got {lk.get('table_age')}")
    check("lk placements present", bool(lk.get("placements")))

    if lk.get("placements"):
        p = lk["placements"]
        print(f"  LK placements: Sun→H{p.get('Sun')}  Moon→H{p.get('Moon')}  "
              f"Saturn→H{p.get('Saturn')}  Rahu→H{p.get('Rahu')}")


# ─────────────────────────────────────────────────────────────────────────────
# 3 — POST /predict
# ─────────────────────────────────────────────────────────────────────────────
section("3 · POST /api/v1/predict")

predict_payload = {
    "chart_id": chart_id,
    "question": "What career opportunities should I focus on this year?",
    "language": "en",
}

print(f"  Calling /predict (may take 5-15s for DeepSeek)...")
r = post("/api/v1/predict", predict_payload, timeout=60)
check("Status 200",               r and r.status_code == 200, r.status_code if r else "—")
if r and r.status_code == 200:
    data = r.json()
    check("prediction text present", bool(data.get("prediction")))
    check("confidence > 0",          (data.get("confidence") or 0) > 0)
    check("factors list present",    isinstance(data.get("factors"), list))
    check("remedies present",        isinstance(data.get("remedies"), list))
    check("rarity_signals present",  isinstance(data.get("rarity_signals"), list))

    pred = data.get("prediction", "")
    print(f"\n  Prediction (first 300 chars):")
    print(f"  {pred[:300]}")
    print(f"\n  Confidence: {data.get('confidence')}")
    print(f"  Remedies: {len(data.get('remedies', []))} returned")
    print(f"  Concern detected: {[f for f in data.get('factors', []) if 'Concern' in f]}")


# ─────────────────────────────────────────────────────────────────────────────
# 4 — Lal Kitab endpoints
# ─────────────────────────────────────────────────────────────────────────────
section("4 · GET /api/v1/chart/{id}/remedies")

r = get(f"/api/v1/chart/{chart_id}/remedies", {"concern": "career"})
check("Status 200",               r and r.status_code == 200)
if r and r.status_code == 200:
    data = r.json()
    check("cards key present",    "cards" in data)
    check("age = 55",             data.get("age") == 55, f"got {data.get('age')}")
    cards = data.get("cards", [])
    check("At least 1 card",      len(cards) >= 1, f"got {len(cards)}")
    if cards:
        print(f"  First remedy card: {cards[0].get('planet')} — {cards[0].get('practice', '')[:60]}")


section("4b · POST /api/v1/lal-kitab/varshphal/generate")

if TOKEN:
    r = post(f"/api/v1/lal-kitab/varshphal/generate?chart_id={chart_id}",
             {}, headers=HEADERS)
    check("Status 200",           r and r.status_code == 200, r.status_code if r else "—")
    if r and r.status_code == 200:
        data = r.json()
        check("age = 55",         data.get("age") == 55, f"got {data.get('age')}")
        check("placements present", bool(data.get("placements")))
else:
    print(f"  SKIP  (no auth token — set ANTAR_TEST_TOKEN env var)")


# ─────────────────────────────────────────────────────────────────────────────
# 5 — Career endpoint
# ─────────────────────────────────────────────────────────────────────────────
section("5 · POST /api/v1/career")

r = post("/api/v1/career", {"chart_id": chart_id, "language": "en"}, timeout=60)
check("Status 200",              r and r.status_code == 200)
if r and r.status_code == 200:
    data = r.json()
    check("reading text present", bool(data.get("reading")))
    check("primary_fields list",  isinstance(data.get("primary_fields"), list))
    check("current_phase present", bool(data.get("current_phase")))
    print(f"  Fields: {data.get('primary_fields', [])[:3]}")


# ─────────────────────────────────────────────────────────────────────────────
# 6 — Monthly briefing
# ─────────────────────────────────────────────────────────────────────────────
section("6 · POST /api/v1/predict/monthly-briefing")

r = post("/api/v1/predict/monthly-briefing",
         {"chart_id": chart_id, "concern": "career", "language": "en"}, timeout=60)
check("Status 200",              r and r.status_code == 200)
if r and r.status_code == 200:
    data = r.json()
    check("briefing text present", bool(data.get("briefing")))
    check("month_year present",    bool(data.get("month_year")))
    print(f"  Month: {data.get('month_year')}")


# ─────────────────────────────────────────────────────────────────────────────
# 7 — Daily practice
# ─────────────────────────────────────────────────────────────────────────────
section("7 · POST /api/v1/predict/daily-practice")

r = post("/api/v1/predict/daily-practice",
         {"chart_id": chart_id, "language": "en"}, timeout=30)
check("Status 200",             r and r.status_code == 200)
if r and r.status_code == 200:
    data = r.json()
    check("practice text present", bool(data.get("practice")))


# ─────────────────────────────────────────────────────────────────────────────
# 8 — Chakra endpoint
# ─────────────────────────────────────────────────────────────────────────────
section("8 · POST /api/v1/chakra")

r = post("/api/v1/chakra", {"chart_id": chart_id, "language": "en"})
check("Status 200",             r and r.status_code == 200)
if r and r.status_code == 200:
    data = r.json()
    check("stressed_chakras key", "stressed_chakras" in data)
    check("summary present",      bool(data.get("summary")))


# ─────────────────────────────────────────────────────────────────────────────
# 9 — Proof points
# ─────────────────────────────────────────────────────────────────────────────
section("9 · POST /api/v1/proof-points")

r = post("/api/v1/proof-points", {"chart_id": chart_id})
check("Status 200",             r and r.status_code == 200)
if r and r.status_code == 200:
    data = r.json()
    check("proof_points list",  isinstance(data.get("proof_points"), list))
    check("At least 1 point",   len(data.get("proof_points", [])) >= 1)


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'═'*64}")
passed  = sum(1 for r in results if r[0] == "PASS")
failed  = sum(1 for r in results if r[0] == "FAIL")
total   = len(results)
print(f"  RESULTS: {passed}/{total} passed  |  {failed} failed")
if failed:
    print(f"\n  Failed:")
    for status, label in results:
        if status == "FAIL":
            print(f"    ✗ {label}")
print(f"{'═'*64}\n")
sys.exit(0 if failed == 0 else 1)
