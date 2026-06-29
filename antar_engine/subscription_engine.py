"""
antar_engine/subscription_engine.py

Subscription and usage tracking engine.
Persists rate limits to Supabase — survives Railway redeploys.
"""

from datetime import datetime, timezone
from typing import Optional


# ── Plan definitions ──────────────────────────────────────────────

PLANS = {
    "free": {
        "name":          "Free",
        # [model-c 2026-06-29] Everything free forever. Readings unlimited;
        # the only metered lever is Ask volume (20/day for 30 days from
        # created_at, then 1/day — enforced live in entitlements.py, NOT
        # this static int). ask_limit here is the nominal trial cap for
        # display; /subscription reports the live value.
        "pred_limit":    None,   # unlimited life readings
        "ask_limit":     20,     # nominal; live value via entitlements
        "compat_limit":  1,
        "alerts":        ["high"],   # only high urgency alerts
        "features": [
            "Everything free — readings, briefings, astrocartography, practices",
            "Daily signal (unlimited)",
            "Ask Antar — 20/day for 30 days, then 1/day",
            "1 compatibility check free",
            "Extra compatibility charts — $0.99 each",
            "High-urgency transit alerts",
        ],
    },
    # [model-c 2026-06-29] DEPRECATED tiers — retained so historical
    # subscriptions and in-flight webhooks resolve (never deleted). New
    # checkouts use the single "ask_unlimited" plan; these are unreachable
    # from the current pricing UI.
    "seeker": {
        "name":          "Seeker",
        "pred_limit":    999,
        "ask_limit":     999,
        "compat_limit":  999,
        "alerts":        ["high", "medium", "opportunity"],
        "price_usd":     4.99,
        "price_inr":     399,
        "price_usd_annual": 39,
        "price_inr_annual": 2999,
        "features": [
            "Unlimited life readings",
            "Unlimited Ask Antar",
            "Unlimited compatibility checks",
            "All transit alerts",
            "Monthly life briefing",
            "Full prediction history",
            "PDF report (1/month)",
        ],
    },
    "navigator": {
        "name":          "Navigator",
        "pred_limit":    999,
        "ask_limit":     999,
        "compat_limit":  999,
        "alerts":        ["high", "medium", "opportunity"],
        "price_usd":     19.99,
        "price_inr":     1499,
        "features": [
            "Everything in Seeker",
            "Remedies: gemstone, daan, yantra, food",
            "Chakra balancing",
            "Priority responses",
            "Astrocartography",
            "Annual chart reading",
            "Unlimited PDF reports",
        ],
    },
}


def get_current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_subscription(chart_id: str, sb) -> dict:
    """Get subscription status for a chart."""
    try:
        res = sb.table("subscriptions").select("*").eq(
            "chart_id", chart_id
        ).execute()
        if res.data:
            sub = res.data[0]
            # Check if subscription is still active
            if sub.get("current_period_end"):
                end = datetime.fromisoformat(
                    sub["current_period_end"].replace("Z", "+00:00")
                )
                if end < datetime.now(timezone.utc):
                    sub["status"] = "expired"
                    sub["plan"]   = "free"
            return sub
    except Exception:
        pass
    return {"plan": "free", "status": "active"}


def get_usage(chart_id: str, sb) -> dict:
    """Get this month\'s usage for a chart."""
    month = get_current_month()
    try:
        res = sb.table("usage_tracking").select("*").eq(
            "chart_id", chart_id
        ).eq("usage_month", month).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return {"pred_count": 0, "ask_count": 0, "compat_count": 0}


def increment_usage(chart_id: str, usage_type: str, sb) -> dict:
    """Increment usage counter. Returns updated usage."""
    month  = get_current_month()
    col    = f"{usage_type}_count"
    try:
        # Upsert — create if not exists, increment if exists
        existing = sb.table("usage_tracking").select("*").eq(
            "chart_id", chart_id
        ).eq("usage_month", month).execute()

        if existing.data:
            current = existing.data[0].get(col, 0)
            res = sb.table("usage_tracking").update({
                col:         current + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("chart_id", chart_id).eq("usage_month", month).execute()
        else:
            res = sb.table("usage_tracking").insert({
                "chart_id":    chart_id,
                "usage_month": month,
                col:           1,
            }).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        return {}


def check_limit(chart_id: str, usage_type: str, sb) -> dict:
    """
    Check if user is within limits.
    Returns: { allowed, used, limit, plan, is_free }
    """
    sub   = get_subscription(chart_id, sb)
    plan  = sub.get("plan", "free")

    # Active paid plan — always allowed
    if plan != "free" and sub.get("status") == "active":
        return {
            "allowed": True, "plan": plan,
            "used": 0, "limit": 999, "is_free": False,
        }

    usage     = get_usage(chart_id, sb)
    col       = f"{usage_type}_count"
    used      = usage.get(col, 0)
    limit     = PLANS["free"].get(f"{usage_type}_limit", 3)
    allowed   = used < limit

    return {
        "allowed":  allowed,
        "plan":     "free",
        "used":     used,
        "limit":    limit,
        "is_free":  True,
        "remaining": max(0, limit - used),
    }


def get_what_youre_missing(chart_id: str, sb) -> dict:
    """
    The key upgrade hook — returns personalized content showing
    what the user will miss if they don\'t upgrade.
    Pulls from their actual chart data for maximum relevance.
    """
    # Get their transit alerts
    try:
        alerts_res = sb.table("user_alerts").select(
            "headline,urgency,alert_type"
        ).eq("chart_id", chart_id).eq(
            "urgency", "opportunity"
        ).is_("dismissed_at", "null").limit(3).execute()
        opportunity_alerts = alerts_res.data or []
    except Exception:
        opportunity_alerts = []

    # Get pending predictions
    try:
        usage = get_usage(chart_id, sb)
        pred_used = usage.get("pred_count", 0)
    except Exception:
        pred_used = 0

    # Get their accuracy score
    try:
        acc_res = sb.table("prediction_accuracy").select("*").eq(
            "chart_id", chart_id
        ).execute()
        accuracy = acc_res.data[0] if acc_res.data else {}
    except Exception:
        accuracy = {}

    # Build personalized hook message
    hook_lines = []

    if opportunity_alerts:
        a = opportunity_alerts[0]
        hook_lines.append("✨ " + a.get("headline","") + " — full reading locked")

    hook_lines += [
        "📊 Unlimited life readings — no monthly cap",
        "🔔 All 6 transit alert types (you\'re missing medium + opportunity alerts)",
        "📅 Monthly life briefing — deep dive every first Sunday",
        "📄 PDF life report — your complete chart as a document",
    ]

    accuracy_pct = accuracy.get("accuracy_pct")
    if accuracy_pct and accuracy_pct >= 70:
        hook_lines.insert(0,
            f"Antar has been {accuracy_pct}% accurate for you — "
            f"don\'t lose access to more readings"
        )

    return {
        "hook_lines":         hook_lines[:4],
        "opportunity_alerts": opportunity_alerts,
        "pred_used":          pred_used,
        "pred_limit":         3,
        "accuracy_pct":       accuracy_pct,
        "plans":              {k: v for k, v in PLANS.items() if k != "free"},
    }


def activate_subscription(
    chart_id: str,
    plan: str,
    provider: str,
    provider_sub_id: str,
    period_end_iso: str,
    sb,
) -> dict:
    """Activate or upgrade a subscription after payment verified."""
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "chart_id":            chart_id,
        "plan":                plan,
        "status":              "active",
        "payment_provider":    provider,
        "provider_sub_id":     provider_sub_id,
        "current_period_end":  period_end_iso,
        "updated_at":          now,
    }
    try:
        existing = sb.table("subscriptions").select("id").eq(
            "chart_id", chart_id
        ).execute()
        if existing.data:
            res = sb.table("subscriptions").update(data).eq(
                "chart_id", chart_id
            ).execute()
        else:
            res = sb.table("subscriptions").insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        return {"error": str(e)}
