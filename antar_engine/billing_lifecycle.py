"""
antar_engine/billing_lifecycle.py — what a payment event DOES to a subscriber.

[billing-lifecycle 2026-10-04] Owner: have Stripe and Razorpay fully wired so that the day
the accounts are approved we only TEST checkout, and know exactly how a subscriber is marked
paid / unpaid / renewed / cancelled. Prices live in the providers' catalogs (Stripe Prices,
Razorpay Plans), not here.

One place, pure of HTTP, driven by an injected Supabase client, so the whole lifecycle is
covered by tests with no network:

    handle_stripe_event(event, sb)      checkout / subscription / invoice / refund / dispute
    handle_razorpay_event(event, sb)    subscription.* / payment.failed / refund
    cancel_subscription / resume_subscription     user-initiated, at period end by default
    subscription_view(chart_id, sb)     the one status shape the app reads

State machine (subscriptions.status):
    active     paid and inside the period            -> paid tier
    past_due   a renewal payment failed; the provider is retrying. Access KEEPS going until
               current_period_end (pushed out a few days of grace) — never cut on the first fail
    cancelled  ended (period over / deleted / refunded) -> free
    expired    provider gave up (unpaid / incomplete_expired) -> free
`cancel_at_period_end` = the user cancelled but is still paid until `current_period_end`.

The plan name stored is ALWAYS "paid" (entitlements.PAID_TIERS). Before this module the webhook
stored "ask" (plan_key.split("_")[0]), which is not a paid tier — a paying subscriber would have
read as free for every tier-gated feature.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

PAID_PLAN = "paid"
PAST_DUE_GRACE_DAYS = 5          # extra access after a failed renewal while the provider retries
_OPTIONAL_COLS = ("cancel_at_period_end", "canceled_at", "provider_customer_id",
                  "last_payment_status", "last_event_at")


# ── small helpers ───────────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _from_ts(ts) -> Optional[str]:
    try:
        return _iso(datetime.fromtimestamp(int(ts), tz=timezone.utc))
    except Exception:
        return None


def plan_from_key(plan_key: str) -> str:
    """Every purchasable plan is the single paid tier. Legacy keys stay legacy (historical rows)."""
    k = (plan_key or "").lower()
    if k.startswith("ask_unlimited") or k in ("", "ask", "paid", "unlimited", "operator"):
        return PAID_PLAN
    return k.split("_")[0] or PAID_PLAN


def _interval_days(plan_key: str = "", interval: str = "") -> int:
    i = (interval or "").lower()
    if i in ("year", "yearly", "annual") or "annual" in (plan_key or "") or "yearly" in (plan_key or ""):
        return 366
    return 32


def _bust(chart_id: str) -> None:
    try:
        from antar_engine.entitlements import bust_entitlement_cache, bust_grandfather_cache
        bust_entitlement_cache(chart_id)
        bust_grandfather_cache(chart_id)
    except Exception:
        pass


def _write(sb, chart_id: str, data: dict) -> bool:
    """Update the subscription row; if the optional lifecycle columns have not been added yet
    (sql_subscription_lifecycle.sql), retry without them — an unknown column fails the whole call."""
    if not chart_id:
        return False
    data = dict(data, updated_at=_iso(_now()))
    for attempt in (0, 1):
        try:
            rows = sb.table("subscriptions").select("id").eq("chart_id", chart_id).execute().data or []
            if rows:
                sb.table("subscriptions").update(data).eq("chart_id", chart_id).execute()
            else:
                sb.table("subscriptions").insert(dict(data, chart_id=chart_id)).execute()
            _bust(chart_id)
            return True
        except Exception as e:
            if attempt == 0 and any(c in data for c in _OPTIONAL_COLS):
                data = {k: v for k, v in data.items() if k not in _OPTIONAL_COLS}
                continue
            print(f"[billing] write failed for {chart_id}: {e}")
            return False
    return False


def _row(sb, chart_id: str = "", provider_sub_id: str = "") -> dict:
    try:
        q = sb.table("subscriptions").select("*")
        q = q.eq("chart_id", chart_id) if chart_id else q.eq("provider_sub_id", provider_sub_id)
        rows = q.execute().data or []
        return rows[0] if rows else {}
    except Exception:
        return {}


def _chart_for(sb, chart_id: str = "", provider_sub_id: str = "") -> str:
    if chart_id:
        return chart_id
    return (_row(sb, provider_sub_id=provider_sub_id).get("chart_id") or "") if provider_sub_id else ""


def _activate(sb, chart_id: str, plan_key: str, provider: str, provider_sub_id: str,
              period_end_iso: str, customer_id: str = "", cancel_at_period_end: bool = False) -> dict:
    ok = _write(sb, chart_id, {
        "plan": plan_from_key(plan_key), "status": "active", "is_paid": True,
        "payment_provider": provider, "provider_sub_id": str(provider_sub_id or ""),
        "current_period_end": period_end_iso, "period_end": period_end_iso,
        "cancel_at_period_end": bool(cancel_at_period_end), "last_payment_status": "paid",
        **({"provider_customer_id": customer_id} if customer_id else {}),
    })
    return {"action": "activated" if ok else "write_failed", "chart_id": chart_id,
            "period_end": period_end_iso}


def _past_due(sb, chart_id: str) -> dict:
    row = _row(sb, chart_id)
    try:
        cur = datetime.fromisoformat(str(row.get("current_period_end")).replace("Z", "+00:00"))
    except Exception:
        cur = _now()
    keep = _iso(max(cur, _now()) + timedelta(days=PAST_DUE_GRACE_DAYS))
    ok = _write(sb, chart_id, {"status": "past_due", "is_paid": False, "current_period_end": keep,
                               "period_end": keep, "last_payment_status": "failed"})
    return {"action": "past_due" if ok else "write_failed", "chart_id": chart_id, "access_until": keep}


def _end(sb, chart_id: str, status: str, why: str) -> dict:
    ok = _write(sb, chart_id, {"plan": "free", "status": status, "is_paid": False,
                               "current_period_end": None, "period_end": None,
                               "cancel_at_period_end": False, "canceled_at": _iso(_now()),
                               "last_payment_status": why})
    return {"action": status if ok else "write_failed", "chart_id": chart_id, "why": why}


# ── Stripe ──────────────────────────────────────────────────────────────────────
def _stripe_period_end(sub_obj: dict) -> Optional[str]:
    """current_period_end moved onto the items in newer Stripe API versions — accept both."""
    v = sub_obj.get("current_period_end")
    if not v:
        for it in ((sub_obj.get("items") or {}).get("data") or []):
            if it.get("current_period_end"):
                v = it["current_period_end"]
                break
    return _from_ts(v) if v else None


def _stripe_interval(sub_obj: dict) -> str:
    for it in ((sub_obj.get("items") or {}).get("data") or []):
        iv = ((it.get("price") or {}).get("recurring") or {}).get("interval")
        if iv:
            return iv
    return ""


def _stripe_invoice_period_end(inv: dict) -> Optional[str]:
    """A subscription invoice's NEW period is on its line item; invoice.period_end is the
    previous billing period's end (≈ now), which would expire a freshly renewed subscriber."""
    ends = [((ln.get("period") or {}).get("end")) for ln in ((inv.get("lines") or {}).get("data") or [])]
    ends = [e for e in ends if e]
    return _from_ts(max(ends)) if ends else None


def handle_stripe_event(event: dict, sb, fetch_subscription: Optional[Callable[[str], dict]] = None) -> dict:
    """Apply one verified Stripe event. Returns {"action": ..., ...} (also useful in tests)."""
    et = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    meta = obj.get("metadata") or {}

    def _sub(sub_id: str) -> dict:
        try:
            return (fetch_subscription(sub_id) if fetch_subscription else {}) or {}
        except Exception:
            return {}

    # one-time compat-slot purchase is handled by the route (not a subscription)
    if et == "checkout.session.completed" and meta.get("type") == "compat_slot":
        return {"action": "compat_slot"}

    if et in ("checkout.session.completed", "customer.subscription.created"):
        if et == "checkout.session.completed" and obj.get("mode") == "payment":
            return {"action": "ignored_one_time"}
        chart_id = obj.get("client_reference_id") or meta.get("chart_id") or ""
        sub_id = obj.get("subscription") or (obj.get("id") if et.startswith("customer.") else "") or ""
        plan_key = meta.get("plan") or "ask_unlimited_monthly"
        if not chart_id:
            return {"action": "no_chart"}
        sub_obj = obj if et.startswith("customer.") else _sub(str(sub_id))
        period_end = _stripe_period_end(sub_obj) or _iso(
            _now() + timedelta(days=_interval_days(plan_key, _stripe_interval(sub_obj))))
        if sub_obj.get("status") in ("incomplete", "incomplete_expired"):
            return {"action": "incomplete", "chart_id": chart_id}
        return _activate(sb, chart_id, plan_key, "stripe", str(sub_id), period_end,
                         customer_id=obj.get("customer") or "",
                         cancel_at_period_end=bool(sub_obj.get("cancel_at_period_end")))

    if et == "customer.subscription.updated":
        sub_id = obj.get("id", "")
        chart_id = _chart_for(sb, meta.get("chart_id", ""), sub_id)
        if not chart_id:
            return {"action": "no_chart"}
        status = obj.get("status", "")
        cape = bool(obj.get("cancel_at_period_end"))
        plan_key = meta.get("plan") or _row(sb, chart_id).get("plan") or "ask_unlimited_monthly"
        if status in ("active", "trialing"):
            pe = _stripe_period_end(obj) or _iso(_now() + timedelta(days=_interval_days(plan_key, _stripe_interval(obj))))
            return _activate(sb, chart_id, plan_key, "stripe", sub_id, pe,
                             customer_id=obj.get("customer") or "", cancel_at_period_end=cape)
        if status == "past_due":
            return _past_due(sb, chart_id)
        if status in ("unpaid", "canceled", "incomplete_expired"):
            return _end(sb, chart_id, "expired" if status != "canceled" else "cancelled", f"stripe_{status}")
        return {"action": "ignored", "status": status}

    if et == "customer.subscription.deleted":
        chart_id = _chart_for(sb, meta.get("chart_id", ""), obj.get("id", ""))
        return _end(sb, chart_id, "cancelled", "subscription_deleted") if chart_id else {"action": "no_chart"}

    if et in ("invoice.payment_succeeded", "invoice.paid"):
        sub_id = obj.get("subscription") or ((obj.get("parent") or {}).get("subscription_details") or {}).get("subscription") or ""
        chart_id = (((obj.get("subscription_details") or {}).get("metadata") or {}).get("chart_id")
                    or next((ln.get("metadata", {}).get("chart_id") for ln in ((obj.get("lines") or {}).get("data") or [])
                             if (ln.get("metadata") or {}).get("chart_id")), "")
                    or _chart_for(sb, "", str(sub_id)))
        if not chart_id or not sub_id:
            return {"action": "no_chart"}
        if (obj.get("amount_paid") or 0) == 0 and obj.get("billing_reason") == "subscription_create" and not obj.get("lines"):
            return {"action": "ignored_zero"}
        pe = _stripe_invoice_period_end(obj) or _stripe_period_end(_sub(str(sub_id))) or _iso(_now() + timedelta(days=32))
        row = _row(sb, chart_id)
        return _activate(sb, chart_id, row.get("plan") or "ask_unlimited_monthly", "stripe", str(sub_id), pe,
                         customer_id=obj.get("customer") or "", cancel_at_period_end=bool(row.get("cancel_at_period_end")))

    if et == "invoice.payment_failed":
        sub_id = obj.get("subscription") or ""
        chart_id = (((obj.get("subscription_details") or {}).get("metadata") or {}).get("chart_id")
                    or _chart_for(sb, "", str(sub_id)))
        if not chart_id:
            return {"action": "no_chart"}
        return _past_due(sb, chart_id)

    if et in ("charge.refunded", "charge.dispute.created"):
        # a FULL refund or any dispute ends access; a partial refund does not
        if et == "charge.refunded" and not obj.get("refunded"):
            return {"action": "partial_refund_ignored"}
        inv = obj.get("invoice") or ""
        sub_id = ((_sub_from_invoice(inv) or {}).get("subscription") or "") if inv else ""
        chart_id = _chart_for(sb, "", str(sub_id)) or _chart_for_customer(sb, obj.get("customer") or "")
        return _end(sb, chart_id, "cancelled", "refunded" if et == "charge.refunded" else "disputed") if chart_id else {"action": "no_chart"}

    return {"action": "ignored", "type": et}


def _sub_from_invoice(invoice_id: str) -> dict:
    try:
        import stripe
        inv = stripe.Invoice.retrieve(invoice_id)
        return {"subscription": inv.get("subscription")}
    except Exception:
        return {}


def _chart_for_customer(sb, customer_id: str) -> str:
    if not customer_id:
        return ""
    try:
        rows = sb.table("subscriptions").select("chart_id").eq("provider_customer_id", customer_id).execute().data or []
        return rows[0]["chart_id"] if rows else ""
    except Exception:
        return ""


# ── Razorpay ────────────────────────────────────────────────────────────────────
def razorpay_plan_id(plan_key: str) -> str:
    """The Razorpay Plan id for a plan key — set in Railway once the plans exist in the dashboard
    (the price lives in the Razorpay plan, not in code)."""
    annual = "annual" in (plan_key or "") or "yearly" in (plan_key or "")
    return os.getenv("RAZORPAY_PLAN_ID_ANNUAL" if annual else "RAZORPAY_PLAN_ID_MONTHLY", "").strip()


def handle_razorpay_event(event: dict, sb) -> dict:
    """Apply one verified Razorpay subscription event. One-time packs/orders are handled by the route."""
    et = event.get("event", "")
    payload = event.get("payload") or {}
    sub = (payload.get("subscription") or {}).get("entity") or {}
    pay = (payload.get("payment") or {}).get("entity") or {}
    notes = {**(pay.get("notes") or {}), **(sub.get("notes") or {})}
    sub_id = sub.get("id") or pay.get("subscription_id") or ""
    if not sub_id and et.startswith("subscription."):
        return {"action": "no_subscription"}
    if not sub_id:
        return {"action": "not_a_subscription_event"}
    chart_id = _chart_for(sb, notes.get("chart_id", ""), sub_id)
    plan_key = notes.get("plan") or _row(sb, chart_id).get("plan") or "ask_unlimited_monthly"

    def _end_iso() -> str:
        return (_from_ts(sub.get("current_end") or sub.get("charge_at"))
                or _iso(_now() + timedelta(days=_interval_days(plan_key))))

    if not chart_id:
        return {"action": "no_chart"}
    if et in ("subscription.activated", "subscription.charged", "subscription.resumed"):
        return _activate(sb, chart_id, plan_key, "razorpay", sub_id, _end_iso())
    if et in ("subscription.pending", "subscription.halted", "payment.failed"):
        return _past_due(sb, chart_id) if et != "subscription.halted" else _end(sb, chart_id, "expired", "razorpay_halted")
    if et == "subscription.cancelled":
        # cancelled at cycle end keeps access until current_end; immediate cancel ends it
        end = _from_ts(sub.get("current_end"))
        if end and datetime.fromisoformat(end) > _now():
            _write(sb, chart_id, {"cancel_at_period_end": True, "canceled_at": _iso(_now()),
                                  "current_period_end": end, "period_end": end})
            return {"action": "cancel_scheduled", "chart_id": chart_id, "access_until": end}
        return _end(sb, chart_id, "cancelled", "razorpay_cancelled")
    if et == "subscription.completed":
        return _end(sb, chart_id, "cancelled", "razorpay_completed")
    if et in ("refund.processed", "refund.created"):
        return _end(sb, chart_id, "cancelled", "refunded")
    return {"action": "ignored", "type": et}


# ── user-initiated cancel / resume ──────────────────────────────────────────────
def cancel_subscription(sb, chart_id: str, immediate: bool = False, stripe_mod: Any = None,
                        razorpay_client: Any = None) -> dict:
    """Cancel at period end by default (the user keeps what they paid for). Apple/Google
    subscriptions are managed in the store — we say so instead of pretending."""
    row = _row(sb, chart_id)
    prov, sid = (row.get("payment_provider") or ""), (row.get("provider_sub_id") or "")
    if not row or row.get("plan") in (None, "", "free"):
        return {"ok": False, "error": "no_active_subscription"}
    try:
        if prov == "stripe":
            stripe = stripe_mod or __import__("stripe")
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            if immediate:
                stripe.Subscription.delete(sid)
                return dict(_end(sb, chart_id, "cancelled", "user_cancelled_now"), ok=True)
            stripe.Subscription.modify(sid, cancel_at_period_end=True)
        elif prov == "razorpay":
            if razorpay_client is None:
                import razorpay
                razorpay_client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID", ""),
                                                        os.getenv("RAZORPAY_KEY_SECRET", "")))
            razorpay_client.subscription.cancel(sid, {"cancel_at_cycle_end": 0 if immediate else 1})
            if immediate:
                return dict(_end(sb, chart_id, "cancelled", "user_cancelled_now"), ok=True)
        elif prov in ("apple", "google"):
            return {"ok": False, "error": "manage_in_store", "provider": prov}
        else:
            return {"ok": False, "error": "unknown_provider", "provider": prov}
    except Exception as e:
        return {"ok": False, "error": "provider_error", "detail": str(e)[:200]}
    _write(sb, chart_id, {"cancel_at_period_end": True, "canceled_at": _iso(_now())})
    return {"ok": True, "action": "cancel_scheduled", "access_until": row.get("current_period_end")}


def resume_subscription(sb, chart_id: str, stripe_mod: Any = None) -> dict:
    """Undo a scheduled cancellation (Stripe). Razorpay needs a new subscription."""
    row = _row(sb, chart_id)
    if (row.get("payment_provider") or "") != "stripe":
        return {"ok": False, "error": "resume_not_supported", "provider": row.get("payment_provider")}
    try:
        stripe = stripe_mod or __import__("stripe")
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        stripe.Subscription.modify(row.get("provider_sub_id"), cancel_at_period_end=False)
    except Exception as e:
        return {"ok": False, "error": "provider_error", "detail": str(e)[:200]}
    _write(sb, chart_id, {"cancel_at_period_end": False, "canceled_at": None})
    return {"ok": True, "action": "resumed"}


# ── the one status shape ─────────────────────────────────────────────────────────
def subscription_view(sb, chart_id: str) -> dict:
    """What the app shows: paid or not, until when, renewing or ending, who bills it."""
    from antar_engine.subscription_engine import get_subscription
    sub = get_subscription(chart_id, sb) or {}
    status = str(sub.get("status") or "").lower()
    plan = str(sub.get("plan") or "free").lower()
    paid_access = plan != "free" and status in ("active", "trialing", "past_due")
    cape = bool(sub.get("cancel_at_period_end"))
    end = sub.get("current_period_end")
    if not paid_access:
        state = "free"
    elif status == "past_due":
        state = "payment_failed"
    elif cape:
        state = "cancelling"
    else:
        state = "active"
    return {
        "state": state,                       # free | active | cancelling | payment_failed
        "is_paid": paid_access,
        "plan": plan, "status": status or "none",
        "provider": sub.get("payment_provider") or None,
        "renews_on": end if state == "active" else None,
        "ends_on": end if state in ("cancelling", "payment_failed") else None,
        "cancel_at_period_end": cape,
        "can_cancel": state == "active" and (sub.get("payment_provider") in ("stripe", "razorpay")),
        "can_resume": state == "cancelling" and sub.get("payment_provider") == "stripe",
        "manage_in_store": sub.get("payment_provider") in ("apple", "google"),
    }
