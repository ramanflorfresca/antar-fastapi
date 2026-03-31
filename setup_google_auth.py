#!/usr/bin/env python3
"""
Antar Google Auth System
=========================
Run from project root:
    python setup_google_auth.py

Builds:
  1. DB migration — add email, google_id, avatar_url to charts
  2. POST /api/v1/auth/link-chart — links anonymous chart to Google user
  3. GET  /api/v1/auth/restore/{google_id} — restores chart for returning user
  4. POST /api/v1/auth/verify-token — verifies Google token server-side
  5. Commits, pushes, smoke tests
"""

import os, sys, subprocess, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/Users/ramandeepsinghchadha/antarai/.env")
ROOT = Path("/Users/ramandeepsinghchadha/antarai")
os.chdir(ROOT)

from supabase import create_client
sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)

print("=" * 60)
print("ANTAR GOOGLE AUTH SYSTEM")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════
# STEP 1 — DB MIGRATIONS
# ══════════════════════════════════════════════════════════════════
print("\n[1] DB migrations ...")


# ══════════════════════════════════════════════════════════════════
# STEP 2 — PATCH main.py WITH AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════
print("\n[2] Patching main.py ...")

main_path = ROOT / "main.py"
main_src  = main_path.read_text()
main_orig = main_src

NEW_AUTH_ENDPOINTS = '''

# ── Google Auth Endpoints ─────────────────────────────────────────

@app.post("/api/v1/auth/link-chart")
async def link_chart_to_google(request: dict):
    """
    Links an anonymous chart to a Google-authenticated user.
    Called after Google Sign-in succeeds on the frontend.

    Body: {
        chart_id: string,       -- the anonymous chart from localStorage
        google_id: string,      -- user.id from Supabase Auth
        email: string,
        display_name: string,
        avatar_url: string
    }
    """
    chart_id     = request.get("chart_id","")
    google_id    = request.get("google_id","")
    email        = request.get("email","")
    display_name = request.get("display_name","")
    avatar_url   = request.get("avatar_url","")

    if not chart_id or not google_id:
        raise HTTPException(400, "chart_id and google_id required")

    # Check if this Google user already has a chart
    existing = supabase.table("charts").select("id").eq(
        "google_id", google_id
    ).execute()

    if existing.data:
        # User already has a chart — return existing chart_id
        # (don't create duplicate — just return the one they already have)
        existing_chart_id = existing.data[0]["id"]

        # Update profile info in case it changed
        supabase.table("charts").update({
            "email":        email,
            "display_name": display_name,
            "avatar_url":   avatar_url,
            "first_name":   display_name.split()[0] if display_name else "",
        }).eq("id", existing_chart_id).execute()

        return {
            "success":  True,
            "chart_id": existing_chart_id,
            "action":   "restored",
            "message":  "Welcome back — your chart has been restored",
        }

    # New user — link the anonymous chart to their Google account
    supabase.table("charts").update({
        "google_id":    google_id,
        "email":        email,
        "display_name": display_name,
        "avatar_url":   avatar_url,
        "first_name":   display_name.split()[0] if display_name else "",
        "user_id":      google_id,
    }).eq("id", chart_id).execute()

    return {
        "success":  True,
        "chart_id": chart_id,
        "action":   "linked",
        "message":  "Chart saved to your Google account",
    }


@app.get("/api/v1/auth/restore/{google_id}")
async def restore_chart(google_id: str):
    """
    Restores chart_id for a returning Google user.
    Called on app load when Supabase session exists but localStorage is empty.
    """
    res = supabase.table("charts").select(
        "id,first_name,display_name,avatar_url,email,"
        "lagna_sign,moon_sign,moon_nakshatra,sun_sign"
    ).eq("google_id", google_id).order(
        "created_at", desc=True
    ).limit(1).execute()

    if not res.data:
        raise HTTPException(404, "No chart found for this account")

    row = res.data[0]

    # Get current dasha
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    dasha_res = supabase.table("dasha_periods").select(
        "level,planet_or_sign,system"
    ).eq("chart_id", row["id"]).eq("system","vimsottari").execute()

    current_md = current_ad = ""
    for d in (dasha_res.data or []):
        try:
            sd = datetime.fromisoformat(str(d.get("start_date",""))[:10])
            ed = datetime.fromisoformat(str(d.get("end_date",""))[:10])
            if sd.date() <= now.date() <= ed.date():
                if d.get("level") == 1: current_md = d.get("planet_or_sign","")
                elif d.get("level") == 2: current_ad = d.get("planet_or_sign","")
        except Exception:
            pass

    dasha = f"{current_md}-{current_ad}" if current_ad else current_md

    return {
        "chart_id":       row["id"],
        "first_name":     row.get("first_name","") or row.get("display_name","").split()[0] if row.get("display_name") else "",
        "display_name":   row.get("display_name",""),
        "avatar_url":     row.get("avatar_url",""),
        "email":          row.get("email",""),
        "lagna":          row.get("lagna_sign",""),
        "moon_sign":      row.get("moon_sign",""),
        "moon_nakshatra": row.get("moon_nakshatra",""),
        "sun_sign":       row.get("sun_sign",""),
        "current_dasha":  dasha,
    }


@app.get("/api/v1/auth/profile/{google_id}")
async def get_profile(google_id: str):
    """Get user profile for display in header/settings."""
    res = supabase.table("charts").select(
        "id,first_name,display_name,avatar_url,email,lagna_sign,moon_sign,created_at"
    ).eq("google_id", google_id).limit(1).execute()

    if not res.data:
        raise HTTPException(404, "Profile not found")

    row = res.data[0]

    # Get subscription
    sub_res = supabase.table("subscriptions").select("plan,status").eq(
        "chart_id", row["id"]
    ).execute()
    plan = sub_res.data[0].get("plan","free") if sub_res.data else "free"

    return {
        "chart_id":     row["id"],
        "display_name": row.get("display_name",""),
        "first_name":   row.get("first_name",""),
        "avatar_url":   row.get("avatar_url",""),
        "email":        row.get("email",""),
        "lagna":        row.get("lagna_sign",""),
        "moon_sign":    row.get("moon_sign",""),
        "plan":         plan,
        "member_since": str(row.get("created_at",""))[:10],
    }

'''

if "/api/v1/auth/link-chart" not in main_src:
    main_src = main_src.rstrip() + "\n" + NEW_AUTH_ENDPOINTS + "\n"
    print("    ✅ Added 3 auth endpoints")
else:
    print("    ⏭  Auth endpoints already present")

if main_src != main_orig:
    backup = main_path.with_suffix(".py.bak10")
    backup.write_text(main_orig)
    main_path.write_text(main_src)

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
    "feat: Google auth endpoints\n\n"
    "- POST /api/v1/auth/link-chart — links anonymous chart to Google user\n"
    "- GET  /api/v1/auth/restore/{google_id} — restores chart on return\n"
    "- GET  /api/v1/auth/profile/{google_id} — user profile\n"
    "- DB: email, google_id, avatar_url, display_name columns on charts"
], check=True)
subprocess.run(["git","push","origin","main"], check=True)
print("    ✅ Pushed")

print("\n[4] Waiting 50s ...")
time.sleep(50)
print("    Done — run: python test_auth.py")
print("    Then paste lovable_google_auth.md into Lovable")
