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
ASK_POST_TRIAL_DAILY_LIMIT = 1  # [ask-launch] free-forever soft cap
ASK_TRIAL_LAUNCH_ISO = "2026-06-05T00:00:00+00:00"

# Feature matrix — source of truth: ANTAR subscription tiers spec.
# Values are access levels the frontend can render directly.
# [final-launch 2026-06-04] EVERYTHING is free, forever. The only paid
# levers are Ask volume (soft-capped below) and ADDITIONAL compatibility
# charts (per-chart one-time purchase — see compat_slots). No content
# feature is ever gated.
FEATURE_MATRIX = {
    "today":         {"free": "full",     "seeker": "full",    "navigator": "full"},
    "month":         {"free": "full",     "seeker": "full",    "navigator": "full"},
    "year":          {"free": "full",     "seeker": "full",    "navigator": "full"},
    "cycle":         {"free": "full",     "seeker": "full",    "navigator": "full"},
    "ask":           {"free": "limited",  "seeker": "full",    "navigator": "full"},
    "compatibility": {"free": "full",     "seeker": "full",    "navigator": "full"},
    "places":        {"free": "full",     "seeker": "full",    "navigator": "full"},
    "practice":      {"free": "full",     "seeker": "full",    "navigator": "full"},
    "history":       {"free": "full",     "seeker": "full",    "navigator": "full"},
    "remedies":      {"free": "full",     "seeker": "full",    "navigator": "full"},
}

# Lowest tier at which the feature is "full".
FEATURE_REQUIRED_TIER = {
    "today":         "free",
    "month":         "free",
    "year":          "free",
    "cycle":         "free",
    "ask":           "seeker",    # unlimited Ask = any active Ask subscription
    "compatibility": "free",      # [final-launch] feature open; extra charts per-chart
    "places":        "free",      # [final-launch]
    "practice":      "free",
    "remedies":      "free",      # [final-launch] remedies free for everyone
    "history":       "free",      # [final-launch]
}

# ── Compatibility chart slots [compat-slots] ──────────────────────
# Navigator includes N charts; additional charts are one-time purchases
# (compat_slot_purchases). A purchase binds permanently to one partner
# chart on first full compatibility run. Fail-open on DB errors so a
# missing table never breaks compatibility.

# [final-launch] every user gets 1 compatibility chart free; navigator
# keeps the 2 it was sold with (grandfathered until the SKU collapse).
COMPAT_INCLUDED_SLOTS = {"free": 1, "seeker": 1, "navigator": 2}
COMPAT_SLOT_PRICE = {"usd_cents": 99, "label": "$0.99"}


def _compat_partners(chart_id: str, sb) -> list:
    """Distinct partner chart ids for this owner, oldest connection first."""
    try:
        rows = sb.table("chart_connections").select("chart_id_b,created_at")             .eq("chart_id_a", chart_id).order("created_at").execute().data or []
    except Exception:
        try:
            rows = sb.table("chart_connections").select("chart_id_b")                 .eq("chart_id_a", chart_id).execute().data or []
        except Exception:
            return []
    seen, out = set(), []
    for r in rows:
        b = r.get("chart_id_b")
        if b and b not in seen:
            seen.add(b)
            out.append(b)
    return out


def compat_slots(chart_id: str, sb, tier: Optional[str] = None) -> dict:
    """{included, purchased, bound, partners_used} for the frontend."""
    tier = tier or get_entitlement(chart_id, sb)
    included = COMPAT_INCLUDED_SLOTS.get(tier, 0)
    purchased = bound = 0
    try:
        rows = sb.table("compat_slot_purchases").select("connection_chart_id,status")             .eq("chart_id", chart_id).eq("status", "paid").execute().data or []
        purchased = len(rows)
        bound = sum(1 for r in rows if r.get("connection_chart_id"))
    except Exception:
        pass
    return {
        "included": included,
        "purchased": purchased,
        "bound": bound,
        "partners_used": len(_compat_partners(chart_id, sb)),
        "price": COMPAT_SLOT_PRICE["label"],
    }


def compat_slot_allows(chart_id_a: str, chart_id_b: Optional[str], tier: str,
                       sb, consume: bool = True) -> bool:
    """True when full compatibility with chart_id_b is covered by an included
    (navigator) slot, an already-bound purchase, or an unused purchase (which
    is then consumed/bound permanently when consume=True)."""
    if not chart_id_a or not chart_id_b:
        return False
    try:
        rows = sb.table("compat_slot_purchases")             .select("id,connection_chart_id,status")             .eq("chart_id", chart_id_a).eq("status", "paid").execute().data or []
    except Exception:
        rows = []
    # 1. already bound to this exact partner
    for r in rows:
        if r.get("connection_chart_id") == chart_id_b:
            return True
    # 2. included slots (navigator): existing partner, or room for a new one
    included = COMPAT_INCLUDED_SLOTS.get(tier, 0)
    if included:
        partners = _compat_partners(chart_id_a, sb)
        if chart_id_b in partners[:included]:
            return True
        if chart_id_b not in partners and len(partners) < included:
            return True
    # 3. consume an unused purchase — permanent binding
    for r in rows:
        if not r.get("connection_chart_id"):
            if consume:
                try:
                    from datetime import datetime, timezone
                    sb.table("compat_slot_purchases").update({
                        "connection_chart_id": chart_id_b,
                        "used_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", r["id"]).execute()
                except Exception:
                    return False
            return True
    # 4. [gamification] an earned compatibility credit — the monthly free read
    #    and streak-milestone rewards. Checked last so a real purchase or an
    #    included slot is always used before something the user earned.
    try:
        from antar_engine import gamification as _gam
        if _gam.balance(sb, chart_id_a, "compat") > 0:
            if not consume:
                return True
            if _gam.spend(sb, chart_id_a, "compat", 1,
                          f"compat_read:{chart_id_b}"):
                return True
    except Exception as e:
        print(f"[gamification] compat credit check skipped (non-blocking): {e}")
    return False


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


def has_unlimited_ask(chart_id: str, sb) -> bool:
    """[final-launch] ANY active/trialing PAID subscription => unlimited Ask.
    Keyed on subscription status, not the plan name, so it survives the plan
    collapse to a single "unlimited Ask" SKU (get_subscription returns
    plan=free/status=active when there is no row, hence the plan check)."""
    if not chart_id:
        return False
    try:
        sub = get_subscription(chart_id, sb) or {}
        plan = str(sub.get("plan") or "free").lower()
        status = str(sub.get("status") or "").lower()
        return plan not in ("", "free") and status in ("active", "trialing")
    except Exception:
        return False


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


def ask_trial_state(chart_id: str, sb, tz_offset: int = 0) -> dict:
    """Trial window + today's usage for the free tier."""
    from datetime import datetime, timedelta, timezone
    rows = _user_ask_rows(chart_id, sb)
    start = _trial_anchor(chart_id, sb, rows)
    now = datetime.now(timezone.utc)
    ends = start + timedelta(days=ASK_TRIAL_DAYS)
    # [model-c] reset at the user's LOCAL midnight, not UTC. tz_offset is
    # minutes east of UTC (client-supplied; same convention as the daily
    # surfaces' _prac_local_date). Absent => UTC, unchanged behaviour.
    today = (now + timedelta(minutes=int(tz_offset or 0))).date().isoformat()
    used_today = 0
    for r in rows:
        if str(r.get("ask_count_date") or "")[:10] == today:
            used_today += int(r.get("ask_count_today") or 0)
    active = now < ends
    return {
        "trial_active": active,
        "trial_start": start.isoformat(),
        "trial_ends_at": ends.isoformat(),
        "days_left": max(0, (ends - now).days),
        "used_today": used_today,
        "daily_limit": ASK_TRIAL_DAILY_LIMIT if active else ASK_POST_TRIAL_DAILY_LIMIT,
    }


def increment_ask_usage(chart_id: str, sb, tz_offset: int = 0) -> None:
    """Count one consultation answer. Maintains the trial's per-day counter
    (ask_count_today/ask_count_date) and backfills ask_trial_start; the
    lifetime ask_count keeps counting as analytics. Non-blocking — never
    breaks the answer path."""
    from datetime import datetime, timedelta, timezone
    try:
        uid = _resolve_user_id(chart_id, sb)
        now_dt = datetime.now(timezone.utc)
        # [model-c] local-midnight day key; tz_offset = minutes east of UTC.
        today = (now_dt + timedelta(minutes=int(tz_offset or 0))).date().isoformat()
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
    """[ask-launch] {used, limit, remaining, trial} — seeker AND navigator are
    unlimited. Free reports TODAY's usage against 20/day in the 30-day trial,
    then 1/day forever (soft cap, never expires)."""
    tier = tier or get_entitlement(chart_id, sb)
    if tier in ("seeker", "navigator") or has_unlimited_ask(chart_id, sb):
        return {"used": None, "limit": None, "remaining": None, "trial": None}
    st = ask_trial_state(chart_id, sb)
    remaining = max(0, st["daily_limit"] - st["used_today"])
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
    # [gamification] Earned credits are additive to the free daily allowance.
    # ask_remaining stays the FREE remainder so existing callers keep their
    # meaning; ask_total_available is what the user can actually ask right now.
    try:
        from antar_engine import gamification as _gam
        _earned_ask = _gam.balance(sb, chart_id, "ask")
        _earned_compat = _gam.balance(sb, chart_id, "compat")
    except Exception:
        _earned_ask = _earned_compat = 0
    _free_rem = quota["remaining"]
    return {
        "tier": tier,
        "ask_used": quota["used"],
        "ask_limit": quota["limit"],
        "ask_remaining": _free_rem,
        "ask_trial": quota.get("trial"),
        "ask_credits": _earned_ask,
        "ask_total_available": (None if _free_rem is None else _free_rem + _earned_ask),
        "compat_credits": _earned_compat,
        "features": {f: FEATURE_MATRIX[f][tier] for f in FEATURE_MATRIX},
        "compat_slots": compat_slots(chart_id, sb, tier),
    }
