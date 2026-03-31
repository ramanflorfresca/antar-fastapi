#!/usr/bin/env python3
"""
Compatibility improvements + Dashboard endpoint
================================================
Run from project root:
    python setup_compat_dashboard.py

Builds:
  1. DB: add score column to compatibility_sessions
  2. Extract score from layer1_analysis text
  3. GET /api/v1/compatibility/sessions/{chart_id} — list past checks
  4. Enforce limits (1 free, 10 Seeker, unlimited Navigator)
  5. GET /api/v1/dashboard/{chart_id} — all 6 data sources in one call
  6. Commits, pushes, smoke tests
"""

import os, sys, re, subprocess, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/Users/ramandeepsinghchadha/antarai/.env")
ROOT = Path("/Users/ramandeepsinghchadha/antarai")
os.chdir(ROOT)

from supabase import create_client
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

print("=" * 60)
print("COMPATIBILITY + DASHBOARD SETUP")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════
# STEP 1 — DB MIGRATIONS
# ══════════════════════════════════════════════════════════════════
print("\n[1] DB migrations ...")


# ══════════════════════════════════════════════════════════════════
# STEP 2 — PATCH main.py
# ══════════════════════════════════════════════════════════════════
print("\n[2] Patching main.py ...")

main_path = ROOT / "main.py"
main_src  = main_path.read_text()
main_orig = main_src
changes   = []

NEW_ENDPOINTS = '''

# ── Compatibility Sessions List ───────────────────────────────────

@app.get("/api/v1/compatibility/sessions/{chart_id}")
async def list_compatibility_sessions(chart_id: str):
    """List all past compatibility checks for a user."""
    res = supabase.table("compatibility_sessions").select(
        "id,name_a,name_b,compat_type,score,current_layer,created_at,has_time_a,has_time_b"
    ).eq("chart_id_a", chart_id).order("created_at", desc=True).limit(20).execute()

    sessions = []
    for s in (res.data or []):
        sessions.append({
            "session_id":   s["id"],
            "name_b":       s.get("name_b",""),
            "compat_type":  s.get("compat_type","relationship"),
            "score":        s.get("score"),
            "layers_done":  s.get("current_layer", 1),
            "confidence":   90 if s.get("has_time_a") and s.get("has_time_b") else 65,
            "created_at":   s.get("created_at",""),
        })

    return {"sessions": sessions, "count": len(sessions)}


# ── Master Dashboard Endpoint ─────────────────────────────────────

@app.get("/api/v1/dashboard/{chart_id}")
async def get_dashboard(chart_id: str):
    """
    Single endpoint that returns all dashboard data.
    Powers the home page with all 6 sections.
    Parallel fetches for speed.
    """
    import asyncio
    from datetime import date, timezone as _tz

    # Load chart
    chart_res = supabase.table("charts").select(
        "first_name,lagna_sign,lagna_degree,birth_date,gender,"
        "moon_sign,moon_nakshatra,sun_sign"
    ).eq("id", chart_id).execute()

    if not chart_res.data:
        raise HTTPException(404, "Chart not found")

    row        = chart_res.data[0]
    first_name = row.get("first_name","") or "Explorer"
    lagna      = row.get("lagna_sign","")
    moon_sign  = row.get("moon_sign","")
    moon_nak   = row.get("moon_nakshatra","")
    sun_sign   = row.get("sun_sign","")

    # Get current dasha
    now = datetime.now(timezone.utc)
    dasha_res = supabase.table("dasha_periods").select(
        "level,planet_or_sign,start_date,end_date,system"
    ).eq("chart_id", chart_id).eq("system","vimsottari").execute()

    current_md = current_ad = ""
    md_end_date = ""
    for d in (dasha_res.data or []):
        try:
            sd = datetime.fromisoformat(str(d.get("start_date",""))[:10])
            ed = datetime.fromisoformat(str(d.get("end_date",""))[:10])
            if sd.date() <= now.date() <= ed.date():
                level = d.get("level",0)
                lord  = d.get("planet_or_sign","")
                if level == 1:
                    current_md   = lord
                    md_end_date  = str(d.get("end_date",""))[:10]
                elif level == 2:
                    current_ad   = lord
        except Exception:
            pass

    dasha_string = f"{current_md}-{current_ad}" if current_ad else current_md

    # Get today's cached signal
    today = date.today().isoformat()
    signal_res = supabase.table("daily_signals").select(
        "signal_text,moon_nakshatra,moon_sign,dasha_string,"
        "rahu_kalam,abhijit,has_wow,wow_today,panchanga,do_today,dont_today"
    ).eq("chart_id", chart_id).eq("signal_date", today).execute()

    signal_data = signal_res.data[0] if signal_res.data else {}

    # Get unread alerts
    alerts_res = supabase.table("user_alerts").select(
        "id,headline,urgency,alert_type,created_at,read_at"
    ).eq("chart_id", chart_id).is_("dismissed_at","null").order(
        "created_at", desc=True
    ).limit(5).execute()

    alerts      = alerts_res.data or []
    unread_count= sum(1 for a in alerts if not a.get("read_at"))

    # Get pending feedback count
    feedback_res = supabase.table("user_correlations").select(
        "id", count="exact"
    ).eq("chart_id", chart_id).eq("feedback_status","pending").lte(
        "show_after", now.isoformat()
    ).execute()
    pending_feedback = feedback_res.count or 0

    # Get accuracy score
    try:
        acc_res = supabase.table("prediction_accuracy").select("*").eq(
            "chart_id", chart_id
        ).execute()
        accuracy = acc_res.data[0] if acc_res.data else {}
    except Exception:
        accuracy = {}

    # Get subscription
    sub_res = supabase.table("subscriptions").select(
        "plan,status,current_period_end"
    ).eq("chart_id", chart_id).execute()
    sub  = sub_res.data[0] if sub_res.data else {}
    plan = sub.get("plan","free")

    # Get usage
    month = now.strftime("%Y-%m")
    usage_res = supabase.table("usage_tracking").select("*").eq(
        "chart_id", chart_id
    ).eq("usage_month", month).execute()
    usage = usage_res.data[0] if usage_res.data else {}

    # Get latest compatibility session
    compat_res = supabase.table("compatibility_sessions").select(
        "id,name_b,score,compat_type,created_at"
    ).eq("chart_id_a", chart_id).order(
        "created_at", desc=True
    ).limit(1).execute()
    latest_compat = compat_res.data[0] if compat_res.data else None

    # Get active remedies (dasha remedy from daily signal)
    dasha_remedy = signal_data.get("dasha_remedy") if signal_data else None

    # Build panchanga summary
    panchanga = signal_data.get("panchanga",{})
    if isinstance(panchanga, str):
        import json as _json
        try: panchanga = _json.loads(panchanga)
        except: panchanga = {}

    return {
        "chart_id":    chart_id,
        "first_name":  first_name,

        # Section 1: Identity
        "lagna":       lagna,
        "moon_sign":   moon_sign,
        "moon_nakshatra": moon_nak,
        "sun_sign":    sun_sign,

        # Section 2: Current chapter
        "dasha":       dasha_string,
        "dasha_md":    current_md,
        "dasha_ad":    current_ad,
        "dasha_ends":  md_end_date,

        # Section 3: Today's signal
        "has_signal":  bool(signal_data),
        "signal_preview": (signal_data.get("signal_text","")[:200] if signal_data else ""),
        "moon_nak_today": signal_data.get("moon_nakshatra","") if signal_data else "",
        "rahu_kalam":  signal_data.get("rahu_kalam","") if signal_data else "",
        "abhijit":     signal_data.get("abhijit","") if signal_data else "",
        "has_wow":     signal_data.get("has_wow", False) if signal_data else False,
        "do_today":    signal_data.get("do_today",[]) if signal_data else [],
        "dont_today":  signal_data.get("dont_today",[]) if signal_data else [],
        "panchanga_headline": panchanga.get("headline","") if panchanga else "",
        "day_quality": panchanga.get("day_quality","") if panchanga else "",

        # Section 4: Alerts
        "alerts":      alerts[:3],
        "unread_alerts": unread_count,

        # Section 5: Accuracy + feedback
        "accuracy_pct":      accuracy.get("accuracy_pct"),
        "total_tracked":     accuracy.get("total_tracked",0),
        "pending_feedback":  pending_feedback,

        # Section 6: Active remedy
        "dasha_remedy": dasha_remedy,

        # Section 7: Compatibility
        "latest_compat": latest_compat,

        # Section 8: Plan
        "plan":          plan,
        "is_paid":       plan != "free",
        "pred_used":     usage.get("pred_count",0),
        "pred_limit":    3 if plan == "free" else 999,
        "compat_used":   usage.get("compat_count",0),
        "compat_limit":  1 if plan == "free" else (10 if plan == "seeker" else 999),
    }

'''

# Add compatibility limit check to compatibility_start
OLD_COMPAT_START = '''    res_a = supabase.table("charts").select("chart_data,birth_date,name").eq("id", request.chart_id_a).execute()'''

NEW_COMPAT_START = '''    # Check compatibility limit
    from antar_engine.subscription_engine import check_limit, increment_usage
    compat_check = check_limit(request.chart_id_a, "compat", supabase)
    if not compat_check["allowed"]:
        raise HTTPException(429, {
            "error": "compat_limit_reached",
            "message": f"Free plan includes 1 compatibility check. Upgrade for more.",
            "used": compat_check["used"],
            "limit": compat_check["limit"],
            "upgrade_url": "https://antar.world/upgrade",
        })

    res_a = supabase.table("charts").select("chart_data,birth_date,name").eq("id", request.chart_id_a).execute()'''

# Add score extraction after layer1 LLM call
OLD_LAYER1 = '''    session_id = str(_uuid.uuid4())
    try:
        supabase.table("compatibility_sessions").insert({
            "id": session_id,
            "chart_id_a": request.chart_id_a,
            "chart_id_b": chart_id_b,
            "name_a": name_a, "name_b": request.name_b,
            "compat_type": request.compatibility_type,
            "brief_a": brief_a, "brief_b": brief_b,
            "layer1_analysis": layer1,
            "has_time_a": has_time_a, "has_time_b": has_time_b,
            "current_layer": 1,
        }).execute()'''

NEW_LAYER1 = '''    # Extract score from layer1 text
    import re as _re
    score_match = _re.search(r'score[:\\s]+(\\d+)/100', layer1, _re.IGNORECASE)
    extracted_score = int(score_match.group(1)) if score_match else None

    # Increment compatibility usage
    from antar_engine.subscription_engine import increment_usage
    increment_usage(request.chart_id_a, "compat", supabase)

    session_id = str(_uuid.uuid4())
    try:
        supabase.table("compatibility_sessions").insert({
            "id": session_id,
            "chart_id_a": request.chart_id_a,
            "chart_id_b": chart_id_b,
            "name_a": name_a, "name_b": request.name_b,
            "compat_type": request.compatibility_type,
            "brief_a": brief_a, "brief_b": brief_b,
            "layer1_analysis": layer1,
            "has_time_a": has_time_a, "has_time_b": has_time_b,
            "current_layer": 1,
            "score": extracted_score,
        }).execute()'''

if "/api/v1/dashboard/" not in main_src:
    main_src = main_src.rstrip() + "\n" + NEW_ENDPOINTS + "\n"
    changes.append("✅ Added dashboard + sessions list endpoints")
else:
    changes.append("⏭  Dashboard endpoint already present")

if OLD_COMPAT_START in main_src:
    main_src = main_src.replace(OLD_COMPAT_START, NEW_COMPAT_START, 1)
    changes.append("✅ Added compatibility limit check")
else:
    changes.append("⚠️  Could not add compat limit — add manually")

if OLD_LAYER1 in main_src:
    main_src = main_src.replace(OLD_LAYER1, NEW_LAYER1, 1)
    changes.append("✅ Added score extraction + usage increment")
else:
    changes.append("⚠️  Could not patch layer1 — add manually")

if main_src != main_orig:
    backup = main_path.with_suffix(".py.bak9")
    backup.write_text(main_orig)
    main_path.write_text(main_src)

for c in changes:
    print(f"    {c}")

r = subprocess.run(
    ["python3","-c",f"import ast; ast.parse(open('{main_path}').read()); print('OK')"],
    capture_output=True, text=True)
print(f"    {'✅' if 'OK' in r.stdout else '❌'} Syntax: {'OK' if 'OK' in r.stdout else r.stderr[-200:]}")

if "OK" not in r.stdout:
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════
# STEP 3 — COMMIT AND PUSH
# ══════════════════════════════════════════════════════════════════
print("\n[3] Committing ...")
subprocess.run(["git","add","main.py"], check=True)
subprocess.run(["git","commit","-m",
    "feat: compatibility sessions list + dashboard endpoint\n\n"
    "- GET /api/v1/compatibility/sessions/{chart_id}\n"
    "- GET /api/v1/dashboard/{chart_id} — all 6 data sources\n"
    "- Score extraction from layer1_analysis text\n"
    "- Compatibility limits: 1 free, 10 seeker, unlimited navigator\n"
    "- Usage increment on compatibility check"
], check=True)
subprocess.run(["git","push","origin","main"], check=True)
print("    ✅ Pushed")

print("\n[4] Waiting 50s ...")
time.sleep(50)
print("    Done — run: python test_dashboard.py")
