#!/usr/bin/env python3
"""Seed (or re-check) the public DEMO chart. Idempotent. Dry-run unless --apply.

  set -a; source .env; set +a
  venv311/bin/python scripts/seed_demo_chart.py            # show the plan
  venv311/bin/python scripts/seed_demo_chart.py --apply    # do it

What --apply does, in order:
  1. reuse app_config.demo_chart_id if that chart still exists, else create a GUEST
     chart through the normal /api/v1/chart/create path (no user, no email);
  2. give it a complete, believable profile so answers read as personal;
  3. record it in app_config.demo_chart_id (this switches the backend guard ON);
  4. snapshot the profile as app_config.demo_chart_baseline (the nightly reset
     restores it);
  5. warm Today / week / month / year so a reviewer never sees an empty card.

Deploy the guard (antar_engine/demo_mode.py) BEFORE running this with --apply.
Never run it against a chart that belongs to a real user.
"""
import argparse
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = os.getenv("ANTAR_API", "https://antar-fastapi-production.up.railway.app")

BIRTH = {  # same fictional "Alex" persona as the App Review account
    "birth_date": "1990-03-15", "birth_time": "12:00", "birth_lat": 40.71427, "birth_lng": -74.00597,
    "timezone_name": "America/New_York", "full_name": "Alex Demo", "birth_city": "New York",
    "birth_country": "US", "country_code": "US", "gender": "female", "language_preference": "en",
    "current_city": "San Francisco", "current_country": "US",
    "marital_status": "married", "children_status": "has_children", "career_stage": "mid_career",
    "health_status": "excellent", "financial_status": "stable",
}
PROFILE = {"life_work": "job", "life_relationship": "married", "life_kids": "yes",
           "marital_status": "married", "children_status": "has_children",
           "career_stage": "mid_career", "health_status": "excellent", "financial_status": "stable",
           "current_city": "San Francisco", "current_country": "US", "language": "en"}


def post(path, body, timeout=180):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    from supabase import create_client
    from antar_engine import demo_mode as dm
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    cid = dm.demo_chart_id(sb, force=True)
    exists = bool(cid and sb.table("charts").select("id").eq("id", cid).is_("deleted_at", "null")
                  .limit(1).execute().data)
    owner = None
    if exists:
        owner = sb.table("charts").select("user_id,auth_user_id,email").eq("id", cid).limit(1).execute().data[0]
        if owner.get("user_id") or owner.get("auth_user_id") or owner.get("email"):
            sys.exit(f"REFUSING: chart {cid} belongs to a user/email — the demo chart must be a guest chart")
    print(f"configured demo chart: {cid or 'none'} | exists: {exists}")
    if not a.apply:
        print("DRY RUN — would " + ("reuse it" if exists else "create a guest chart via /api/v1/chart/create")
              + ", set the profile, store demo_chart_id + baseline, warm the caches. Re-run with --apply.")
        return
    if not exists:
        res = post("/api/v1/chart/create", BIRTH)
        cid = res.get("chart_id") or res.get("id") or (res.get("chart") or {}).get("id")
        if not cid:
            sys.exit(f"chart create returned no id: {str(res)[:300]}")
        print("created guest chart", cid)
    sb.table("charts").update(PROFILE).eq("id", cid).execute()
    sb.table("app_config").upsert({"key": dm.DEMO_KEY, "value": cid, "updated_by": "demo-seed"},
                                  on_conflict="key").execute()
    base = dm.snapshot_baseline(sb, cid)
    print("demo_chart_id set; baseline columns:", sorted(k for k, v in base.items() if v is not None))
    for path, body in (("/api/v1/predict/daily-week", {"chart_id": cid}),
                       ("/api/v1/predict/monthly", {"chart_id": cid}),
                       ("/api/v1/predict/yearly", {"chart_id": cid}),
                       ("/api/v1/predict/daily", {"chart_id": cid})):
        try:
            post(path, body)
            print("warmed", path)
        except Exception as e:
            print("warm FAILED", path, str(e)[:120])
    print("done. Demo chart:", cid)


if __name__ == "__main__":
    main()
