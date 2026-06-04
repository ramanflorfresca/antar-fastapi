"""
antar_engine/entitlements.py

Backend entitlement layer — the single source of truth for what a user
can access per subscription tier.  Frontend gating is UX only; every
gated endpoint calls into this module so the API itself is not bypassable.

Tiers:   free | seeker | navigator
Access:  full | headline | teaser | preview | sample | limited | locked

Tier is derived from the live subscription row (antar_engine.
subscription_engine.get_subscription) which already downgrades
expired periods to free — so lapsed/cancelled subscriptions re-lock
paid surfaces automatically (graceful expiry).
"""

import time
from typing import Optional

from antar_engine.subscription_engine import get_subscription

# ── Constants ─────────────────────────────────────────────────────

TIER_RANK = {"free": 0, "seeker": 1, "navigator": 2}
UPGRADE_URL = "https://antar.world/upgrade"

# 30-day Ask trial (replaced the lifetime-3 cap on 2026-06-05).
# Existing users' clocks start at launch; new users at signup.
ASK_TRIAL_DAYS = 30
ASK_TRIAL_DAILY_LIMIT = 20
ASK_TRIAL_LAUNCH_ISO = "2026-06-05T00:00:00+00:00"

# Feature matrix — source of truth: ANTAR subscription tiers spec.
# Values are access levels the frontend can render directly.
FEATURE_MATRIX = {
    "today":         {"free": "full",     "seeker": "full",    "navigator": "full"},
    "month":         {"free": "headline", "seeker": "full",    "navigator": "full"},
    "year":          {"free": "teaser",   "seeker": "full",    "navigator": "full"},
    "cycle":         {"free": "preview",  "seeker": "full",    "navigator": "full"},
    "ask":           {"free": "limited",  "seeker": "full",    "navigator": "full"},
    "compatibility": {"free": "preview",  "seeker": "preview", "navigator": "full"},
    "places":        {"free": "preview",  "seeker": "preview", "navigator": "full"},
    "practice":      {"free": "sample",   "seeker": "full",    "navigator": "full"},
    "history":       {"free": "locked",   "seeker": "full",    "navigator": "full"},
}

# Lowest tier at which the feature is "full".
FEATURE_REQUIRED_TIER = {
    "today":         "free",
    "month":         "seeker",
    "year":          "seeker",
    "cycle":         "seeker",
    "ask":           "seeker",
    "compatibility": "navigator",
    "places":        "navigator",
    "practice":      "seeker",
    "history":       "seeker",
}

# ── Entitlement resolution (60s in-process TTL cache) ─────────────

_ENT_CACHE: dict = {}
_ENT_TTL = 60.0


def bust_entitlement_cache(chart_id: str) -> None:
    _ENT_CACHE.pop(chart_id, None)


def get_entitlement(chart_id: str, sb) -> str:
    """
    Resolve the live tier for a chart: 'free' | 'seeker' | 'navigator'.
    Respects subscription status — anything not active/trialing => free.
    get_subscription() already maps an expired current_period_end to
    plan=free, so lapsed subscriptions downgrade cleanly.
    """
    if not chart_id:
        return "free"
    hit = _ENT_CACHE.get(chart_id)
    if hit and hit[0] > time.time():
        return hit[1]
    tier = "free"
    try:
        sub = get_subscription(chart_id, sb) or {}
        plan = str(sub.get("plan") or "free").lower()
        status = str(sub.get("status") or "").lower()
        if plan in ("seeker", "navigator") and status in ("active", "trialing"):
            tier = plan
    except Exception:
        tier = "free"
    _ENT_CACHE[chart_id] = (time.time() + _ENT_TTL, tier)
    return tier


def feature_access(tier: str, feature: str) -> str:
    """Access level for (tier, feature): full/headline/teaser/preview/sample/limited/locked."""
    return FEATURE_MATRIX.get(feature, {}).get(tier, "full")


def upgrade_block(feature: str, current_tier: str, locked_fields: Optional[list] = None, **extra) -> dict:
    """
    Consistent upgrade signal the frontend can act on.  Embedded in
    partial (preview) payloads and used as the body of 402 denials.
    """
    block = {
        "error": "upgrade_required",
        "feature": feature,
        "required_tier": FEATURE_REQUIRED_TIER.get(feature, "seeker"),
        "current_tier": current_tier,
        "upgrade_url": UPGRADE_URL,
    }
    if locked_fields:
        block["locked_fields"] = locked_fields
    block.update(extra)
    return block


# ── Ask 30-day trial ──────────────────────────────────────────────
# Stored in the ask_usage table (chart_id PK, user_id backfilled from
# profiles).  Usage is user-scoped: when a user_id is known, today's
# count is summed across all of that user's chart rows so a free user
# can't reset the cap by casting a new chart.  The lifetime ask_count
# column remains as analytics; it no longer gates anything.
# Daily window reckons on UTC dates (a tz-local reset is a frontend
# nicety, not a fairness issue at 20/day).

_ASK_USAGE_COLS = "chart_id,user_id,ask_count,ask_count_today,ask_count_date,ask_trial_start"


def _resolve_user_id(chart_id: str, sb) -> Optional[str]:
    try:
        r = sb.table("profiles").select("user_id").eq(
            "chart_id", chart_id
        ).limit(1).execute()
        if r.data:
            return r.data[0].get("user_id")
    except Exception:
        pass
    return None


def _parse_ts(v):
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _user_ask_rows(chart_id: str, sb) -> list:
    """This chart's ask_usage row + the user's sibling rows."""
    rows = []
    try:
        r = sb.table("ask_usage").select(_ASK_USAGE_COLS).eq(
            "chart_id", chart_id
        ).execute()
        rows = list(r.data or [])
        uid = (rows[0].get("user_id") if rows else None) or _resolve_user_id(chart_id, sb)
        if uid:
            r2 = sb.table("ask_usage").select(_ASK_USAGE_COLS).eq(
                "user_id", uid
            ).execute()
            seen = {x.get("chart_id") for x in rows}
            rows += [x for x in (r2.data or []) if x.get("chart_id") not in seen]
    except Exception as e:
        print(f"[entitlements] ask_usage read failed (fail-open): {e}")
    return rows


def _trial_anchor(chart_id: str, sb, rows: list):
    """Earliest ask_trial_start across the user's rows; else the chart's
    signup date clamped to launch — existing users start 2026-06-05, new
    users at signup, including users with no ask_usage row yet."""
    starts = [_parse_ts(r.get("ask_trial_start")) for r in (rows or [])]
    starts = [s for s in starts if s]
    if starts:
        return min(starts)
    launch = _parse_ts(ASK_TRIAL_LAUNCH_ISO)
    try:
        r = sb.table("charts").select("created_at").eq(
            "id", chart_id
        ).single().execute()
        created = _parse_ts((r.data or {}).get("created_at"))
        if created:
            return max(created, launch)
    except Exception:
        pass
    return launch


def ask_trial_state(chart_id: str, sb) -> dict:
    """Trial window + today's usage for the free tier."""
    from datetime import datetime, timedelta, timezone
    rows = _user_ask_rows(chart_id, sb)
    start = _trial_anchor(chart_id, sb, rows)
    now = datetime.now(timezone.utc)
    ends = start + timedelta(days=ASK_TRIAL_DAYS)
    today = now.date().isoformat()
    used_today = 0
    for r in rows:
        if str(r.get("ask_count_date") or "")[:10] == today:
            used_today += int(r.get("ask_count_today") or 0)
    return {
        "trial_active": now < ends,
        "trial_start": start.isoformat(),
        "trial_ends_at": ends.isoformat(),
        "days_left": max(0, (ends - now).days),
        "used_today": used_today,
        "daily_limit": ASK_TRIAL_DAILY_LIMIT,
    }


def increment_ask_usage(chart_id: str, sb) -> None:
    """Count one consultation answer. Maintains the trial's per-day counter
    (ask_count_today/ask_count_date) and backfills ask_trial_start; the
    lifetime ask_count keeps counting as analytics. Non-blocking — never
    breaks the answer path."""
    from datetime import datetime, timezone
    try:
        uid = _resolve_user_id(chart_id, sb)
        now_dt = datetime.now(timezone.utc)
        today = now_dt.date().isoformat()
        existing = sb.table("ask_usage").select(
            "ask_count,ask_count_today,ask_count_date,ask_trial_start"
        ).eq("chart_id", chart_id).execute()
        if existing.data:
            row = existing.data[0]
            cur = int(row.get("ask_count") or 0)
            same_day = str(row.get("ask_count_date") or "")[:10] == today
            today_n = (int(row.get("ask_count_today") or 0) + 1) if same_day else 1
            upd = {"ask_count": cur + 1, "ask_count_today": today_n,
                   "ask_count_date": today, "user_id": uid,
                   "updated_at": now_dt.isoformat()}
            if not row.get("ask_trial_start"):
                upd["ask_trial_start"] = _trial_anchor(chart_id, sb, []).isoformat()
            sb.table("ask_usage").update(upd).eq("chart_id", chart_id).execute()
        else:
            sb.table("ask_usage").insert({
                "chart_id": chart_id, "user_id": uid, "ask_count": 1,
                "ask_count_today": 1, "ask_count_date": today,
                "ask_trial_start": _trial_anchor(chart_id, sb, []).isoformat(),
            }).execute()
    except Exception as e:
        print(f"[entitlements] ask_usage increment failed (non-blocking): {e}")


def ask_quota(chart_id: str, sb, tier: Optional[str] = None) -> dict:
    """{used, limit, remaining, trial} — paid tiers are unlimited. Free tier
    reports TODAY's usage against the trial's daily cap; the lifetime-3
    cap is retired."""
    tier = tier or get_entitlement(chart_id, sb)
    if tier in ("seeker", "navigator"):
        return {"used": None, "limit": None, "remaining": None, "trial": None}
    st = ask_trial_state(chart_id, sb)
    remaining = (max(0, st["daily_limit"] - st["used_today"])
                 if st["trial_active"] else 0)
    return {
        "used": st["used_today"],
        "limit": st["daily_limit"],
        "remaining": remaining,
        "trial": {
            "active": st["trial_active"],
            "start": st["trial_start"],
            "ends_at": st["trial_ends_at"],
            "days_left": st["days_left"],
        },
    }


# ── Frontend-facing summary ───────────────────────────────────────


def entitlement_summary(chart_id: str, sb) -> dict:
    """
    Shape served to the frontend (in /me/billing and
    /api/v1/entitlements/{chart_id}) so it knows what to lock/preview
    without trial-and-error.
    """
    tier = get_entitlement(chart_id, sb)
    quota = ask_quota(chart_id, sb, tier)
    return {
        "tier": tier,
        "ask_used": quota["used"],
        "ask_limit": quota["limit"],
        "ask_remaining": quota["remaining"],
        "ask_trial": quota.get("trial"),
        "features": {f: FEATURE_MATRIX[f][tier] for f in FEATURE_MATRIX},
    }
