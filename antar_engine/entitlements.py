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

# Lifetime (not monthly) Ask quota for free users.
ASK_FREE_LIFETIME_LIMIT = 3

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


# ── Ask lifetime quota ────────────────────────────────────────────
# Stored in the ask_usage table (chart_id PK, user_id backfilled from
# profiles.primary_chart_id).  When a user_id is known, usage is summed
# across all of that user's chart rows so a free user can't reset the
# quota by casting a new chart.  NOTE: the post-launch Ask history
# table can reuse/replace this — counter reads should then move to
# count(*) over that table.


def _resolve_user_id(chart_id: str, sb) -> Optional[str]:
    try:
        r = sb.table("profiles").select("user_id").eq(
            "primary_chart_id", chart_id
        ).limit(1).execute()
        if r.data:
            return r.data[0].get("user_id")
    except Exception:
        pass
    return None


def get_ask_used(chart_id: str, sb) -> int:
    """Lifetime Ask answers consumed (summed across the user's charts when linkable)."""
    try:
        r = sb.table("ask_usage").select("user_id,ask_count").eq(
            "chart_id", chart_id
        ).execute()
        row = r.data[0] if r.data else None
        uid = (row or {}).get("user_id") or _resolve_user_id(chart_id, sb)
        if uid:
            r2 = sb.table("ask_usage").select("ask_count").eq(
                "user_id", uid
            ).execute()
            if r2.data:
                return sum(int(x.get("ask_count") or 0) for x in r2.data)
        return int((row or {}).get("ask_count") or 0)
    except Exception as e:
        print(f"[entitlements] ask_usage read failed (fail-open): {e}")
        return 0


def increment_ask_usage(chart_id: str, sb) -> None:
    """Count one consultation answer. Non-blocking — never breaks the answer path."""
    from datetime import datetime, timezone
    try:
        uid = _resolve_user_id(chart_id, sb)
        existing = sb.table("ask_usage").select("ask_count").eq(
            "chart_id", chart_id
        ).execute()
        now = datetime.now(timezone.utc).isoformat()
        if existing.data:
            cur = int(existing.data[0].get("ask_count") or 0)
            sb.table("ask_usage").update(
                {"ask_count": cur + 1, "user_id": uid, "updated_at": now}
            ).eq("chart_id", chart_id).execute()
        else:
            sb.table("ask_usage").insert(
                {"chart_id": chart_id, "user_id": uid, "ask_count": 1}
            ).execute()
    except Exception as e:
        print(f"[entitlements] ask_usage increment failed (non-blocking): {e}")


def ask_quota(chart_id: str, sb, tier: Optional[str] = None) -> dict:
    """{used, limit, remaining} — limit/remaining are None for paid tiers (unlimited)."""
    tier = tier or get_entitlement(chart_id, sb)
    if tier in ("seeker", "navigator"):
        return {"used": None, "limit": None, "remaining": None}
    used = get_ask_used(chart_id, sb)
    return {
        "used": used,
        "limit": ASK_FREE_LIFETIME_LIMIT,
        "remaining": max(0, ASK_FREE_LIFETIME_LIMIT - used),
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
        "features": {f: FEATURE_MATRIX[f][tier] for f in FEATURE_MATRIX},
    }
