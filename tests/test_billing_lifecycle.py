"""[billing-lifecycle 2026-10-04] Every way a subscriber becomes paid, renews, fails, cancels or is refunded —
Stripe + Razorpay — driven through the real handlers with a fake Supabase. No network.

The thing these tests exist to prove: after each event, what does the APP think of this chart?
(`get_entitlement` tier, `has_unlimited_ask`, `subscription_view`)."""
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

# main.py builds its LLM / Supabase clients at import. In CI there is no .env, so give it placeholders
# (never called — Supabase is faked). Locally a real .env exists and must NOT be shadowed by them,
# or later tests that read the live database would see the fake URL.
if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")):
    os.environ.setdefault("DEEPSEEK_API_KEY", "ci-placeholder-not-a-real-key")
    os.environ.setdefault("SUPABASE_URL", "https://ci.supabase.co")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "ci-placeholder-not-a-real-key")

from antar_engine import billing_lifecycle as bl
from antar_engine import entitlements as ent
from antar_engine import subscription_engine as se

CHART = "chart-1"
NOW = datetime.now(timezone.utc)


class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, {}, "select", None

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def upsert(self, payload, **_k):
        self.op, self.payload = "insert", payload
        return self

    def eq(self, k, v):
        self.filters[k] = v
        return self

    def limit(self, _n):
        return self

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        hit = [r for r in rows if all(str(r.get(k)) == str(v) for k, v in self.filters.items())]
        if self.op == "select":
            return _Res([dict(r) for r in hit])
        if self.op == "update":
            if self.db.get("__reject_cols__") and any(c in self.payload for c in self.db["__reject_cols__"]):
                raise RuntimeError("column does not exist")
            for r in hit:
                r.update(self.payload)
            return _Res([dict(r) for r in hit])
        if self.db.get("__reject_cols__") and any(c in self.payload for c in self.db["__reject_cols__"]):
            raise RuntimeError("column does not exist")
        rows.append(dict(self.payload, id=len(rows) + 1))
        return _Res([rows[-1]])


class FakeSB:
    def __init__(self):
        self.db = {"subscriptions": []}

    def table(self, name):
        return _Q(self.db, name)

    @property
    def sub(self):
        rows = self.db["subscriptions"]
        return rows[0] if rows else {}


@pytest.fixture(autouse=True)
def _clear():
    ent._ENT_CACHE.clear()
    yield
    ent._ENT_CACHE.clear()


def ts(days):
    return int((NOW + timedelta(days=days)).timestamp())


def tier(sb):
    return ent.get_entitlement(CHART, sb)


def stripe_checkout(days=30, plan="ask_unlimited_monthly", cape=False):
    ev = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_1", "mode": "subscription", "client_reference_id": CHART, "subscription": "sub_1",
        "customer": "cus_1", "metadata": {"chart_id": CHART, "plan": plan}}}}
    fetch = lambda sid: {"id": sid, "status": "active", "current_period_end": ts(days), "cancel_at_period_end": cape,
                         "items": {"data": [{"price": {"recurring": {"interval": "year" if "annual" in plan else "month"}}}]}}
    return ev, fetch


# ── becoming paid ───────────────────────────────────────────────────────────────
def test_stripe_checkout_marks_the_chart_paid_with_the_paid_tier():
    sb = FakeSB()
    ev, fetch = stripe_checkout()
    r = bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    assert r["action"] == "activated"
    assert sb.sub["plan"] == "paid" and sb.sub["status"] == "active" and sb.sub["is_paid"] is True
    assert sb.sub["payment_provider"] == "stripe" and sb.sub["provider_sub_id"] == "sub_1"
    assert tier(sb) == "paid" and ent.has_unlimited_ask(CHART, sb)


def test_legacy_ask_plan_rows_still_count_as_paid():
    # the old webhook stored plan "ask" — those subscribers must not read as free
    sb = FakeSB()
    sb.db["subscriptions"].append({"chart_id": CHART, "plan": "ask", "status": "active",
                                   "current_period_end": (NOW + timedelta(days=9)).isoformat()})
    assert tier(sb) == "paid"


def test_activate_subscription_normalises_the_plan():
    sb = FakeSB()
    se.activate_subscription(CHART, "ask", "razorpay", "pay_1", (NOW + timedelta(days=30)).isoformat(), sb)
    assert sb.sub["plan"] == "paid" and tier(sb) == "paid"


def test_annual_checkout_period_comes_from_stripe_not_a_guess():
    sb = FakeSB()
    ev, fetch = stripe_checkout(days=365, plan="ask_unlimited_annual")
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    end = datetime.fromisoformat(sb.sub["current_period_end"])
    assert abs((end - (NOW + timedelta(days=365))).total_seconds()) < 5


def test_checkout_without_fetch_falls_back_to_the_plan_interval():
    sb = FakeSB()
    ev, _ = stripe_checkout(plan="ask_unlimited_annual")
    bl.handle_stripe_event(ev, sb, fetch_subscription=None)
    assert (datetime.fromisoformat(sb.sub["current_period_end"]) - NOW).days >= 360


def test_one_time_payment_checkout_does_not_activate_a_subscription():
    sb = FakeSB()
    ev, _ = stripe_checkout()
    ev["data"]["object"]["mode"] = "payment"
    assert bl.handle_stripe_event(ev, sb)["action"] == "ignored_one_time" and not sb.db["subscriptions"]


def test_replaying_the_same_event_is_harmless():
    sb = FakeSB()
    ev, fetch = stripe_checkout()
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    assert len(sb.db["subscriptions"]) == 1 and tier(sb) == "paid"


# ── renewal ─────────────────────────────────────────────────────────────────────
def invoice(event="invoice.payment_succeeded", new_end_days=60, stale_period_end_days=30):
    return {"type": event, "data": {"object": {
        "subscription": "sub_1", "customer": "cus_1", "amount_paid": 799, "billing_reason": "subscription_cycle",
        "period_end": ts(stale_period_end_days),   # the PREVIOUS period's end — must not be used
        "subscription_details": {"metadata": {"chart_id": CHART}},
        "lines": {"data": [{"period": {"start": ts(30), "end": ts(new_end_days)}}]}}}}


def test_renewal_extends_to_the_new_period_from_the_line_item():
    sb = FakeSB()
    ev, fetch = stripe_checkout(days=30)
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    bl.handle_stripe_event(invoice(new_end_days=60), sb)
    end = datetime.fromisoformat(sb.sub["current_period_end"])
    assert abs((end - (NOW + timedelta(days=60))).total_seconds()) < 5          # not the stale invoice.period_end
    assert sb.sub["status"] == "active" and sb.sub["is_paid"] is True


# ── a failed renewal ────────────────────────────────────────────────────────────
def test_failed_renewal_keeps_access_while_stripe_retries():
    sb = FakeSB()
    ev, fetch = stripe_checkout(days=0)         # period ends right now
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    r = bl.handle_stripe_event({"type": "invoice.payment_failed", "data": {"object": {
        "subscription": "sub_1", "subscription_details": {"metadata": {"chart_id": CHART}}}}}, sb)
    assert r["action"] == "past_due" and sb.sub["status"] == "past_due" and sb.sub["is_paid"] is False
    assert tier(sb) == "paid" and ent.has_unlimited_ask(CHART, sb)             # grace, not an instant cut
    view = bl.subscription_view(sb, CHART)
    assert view["state"] == "payment_failed" and view["is_paid"] is True


def test_recovery_after_a_failed_renewal():
    sb = FakeSB()
    ev, fetch = stripe_checkout(days=0)
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    bl.handle_stripe_event({"type": "invoice.payment_failed", "data": {"object": {
        "subscription": "sub_1", "subscription_details": {"metadata": {"chart_id": CHART}}}}}, sb)
    bl.handle_stripe_event(invoice(new_end_days=30), sb)
    assert sb.sub["status"] == "active" and sb.sub["is_paid"] is True
    assert bl.subscription_view(sb, CHART)["state"] == "active"


def test_stripe_giving_up_ends_access():
    sb = FakeSB()
    ev, fetch = stripe_checkout()
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    bl.handle_stripe_event({"type": "customer.subscription.updated", "data": {"object": {
        "id": "sub_1", "status": "unpaid", "metadata": {"chart_id": CHART}}}}, sb)
    assert sb.sub["plan"] == "free" and sb.sub["status"] == "expired" and tier(sb) == "free"


def test_past_due_status_event_is_a_grace_not_a_cut():
    sb = FakeSB()
    ev, fetch = stripe_checkout()
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    bl.handle_stripe_event({"type": "customer.subscription.updated", "data": {"object": {
        "id": "sub_1", "status": "past_due", "metadata": {"chart_id": CHART}}}}, sb)
    assert sb.sub["status"] == "past_due" and tier(sb) == "paid"


# ── cancelling ──────────────────────────────────────────────────────────────────
def test_user_cancel_keeps_access_until_the_period_ends_then_stops():
    sb = FakeSB()
    ev, fetch = stripe_checkout(days=20)
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    calls = []

    class FakeStripe:
        api_key = ""

        class Subscription:
            @staticmethod
            def modify(sid, **kw):
                calls.append(("modify", sid, kw))

            @staticmethod
            def delete(sid):
                calls.append(("delete", sid))

    r = bl.cancel_subscription(sb, CHART, stripe_mod=FakeStripe)
    assert r["ok"] and calls == [("modify", "sub_1", {"cancel_at_period_end": True})]
    v = bl.subscription_view(sb, CHART)
    assert v["state"] == "cancelling" and v["is_paid"] and v["can_resume"] and v["ends_on"] and not v["renews_on"]
    assert tier(sb) == "paid"
    # Stripe confirms with an update, then deletes at the end of the period
    bl.handle_stripe_event({"type": "customer.subscription.updated", "data": {"object": {
        "id": "sub_1", "status": "active", "cancel_at_period_end": True, "current_period_end": ts(20),
        "metadata": {"chart_id": CHART, "plan": "ask_unlimited_monthly"}}}}, sb)
    assert bl.subscription_view(sb, CHART)["state"] == "cancelling"
    bl.handle_stripe_event({"type": "customer.subscription.deleted", "data": {"object": {
        "id": "sub_1", "metadata": {"chart_id": CHART}}}}, sb)
    assert sb.sub["plan"] == "free" and sb.sub["status"] == "cancelled" and tier(sb) == "free"
    assert bl.subscription_view(sb, CHART)["state"] == "free"


def test_resume_undoes_a_scheduled_cancel():
    sb = FakeSB()
    ev, fetch = stripe_checkout(days=20)
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)

    class FakeStripe:
        api_key = ""

        class Subscription:
            @staticmethod
            def modify(sid, **kw):
                pass

    bl.cancel_subscription(sb, CHART, stripe_mod=FakeStripe)
    assert bl.resume_subscription(sb, CHART, stripe_mod=FakeStripe)["ok"]
    assert bl.subscription_view(sb, CHART)["state"] == "active"


def test_immediate_cancel_ends_access_now():
    sb = FakeSB()
    ev, fetch = stripe_checkout()
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)

    class FakeStripe:
        api_key = ""

        class Subscription:
            @staticmethod
            def delete(sid):
                pass

    assert bl.cancel_subscription(sb, CHART, immediate=True, stripe_mod=FakeStripe)["ok"]
    assert tier(sb) == "free"


def test_cannot_cancel_when_not_subscribed_and_store_subs_point_to_the_store():
    sb = FakeSB()
    assert bl.cancel_subscription(sb, CHART)["error"] == "no_active_subscription"
    se.activate_subscription(CHART, "paid", "apple", "orig_1", (NOW + timedelta(days=9)).isoformat(), sb)
    r = bl.cancel_subscription(sb, CHART)
    assert r["error"] == "manage_in_store"
    assert bl.subscription_view(sb, CHART)["manage_in_store"] is True


# ── refunds / disputes ──────────────────────────────────────────────────────────
def test_full_refund_and_dispute_end_access_partial_refund_does_not(monkeypatch):
    sb = FakeSB()
    ev, fetch = stripe_checkout()
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    monkeypatch.setattr(bl, "_sub_from_invoice", lambda inv: {"subscription": "sub_1"})
    part = {"type": "charge.refunded", "data": {"object": {"refunded": False, "invoice": "in_1", "customer": "cus_1"}}}
    assert bl.handle_stripe_event(part, sb)["action"] == "partial_refund_ignored" and tier(sb) == "paid"
    full = {"type": "charge.refunded", "data": {"object": {"refunded": True, "invoice": "in_1", "customer": "cus_1"}}}
    bl.handle_stripe_event(full, sb)
    assert tier(sb) == "free" and sb.sub["last_payment_status"] == "refunded"
    # and a dispute
    sb2 = FakeSB()
    bl.handle_stripe_event(ev, sb2, fetch_subscription=fetch)
    bl.handle_stripe_event({"type": "charge.dispute.created", "data": {"object": {"invoice": "in_1", "customer": "cus_1"}}}, sb2)
    assert tier(sb2) == "free"


# ── robustness ──────────────────────────────────────────────────────────────────
def test_optional_columns_missing_does_not_fail_the_payment():
    sb = FakeSB()
    sb.db["__reject_cols__"] = list(bl._OPTIONAL_COLS)        # sql_subscription_lifecycle.sql not run yet
    ev, fetch = stripe_checkout()
    r = bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    assert r["action"] == "activated" and tier(sb) == "paid"


def test_events_for_unknown_charts_are_ignored_safely():
    sb = FakeSB()
    assert bl.handle_stripe_event({"type": "invoice.payment_failed", "data": {"object": {"subscription": "nope"}}}, sb)["action"] == "no_chart"
    assert bl.handle_stripe_event({"type": "something.else", "data": {"object": {}}}, sb)["action"] == "ignored"


def test_subscription_view_free_state():
    v = bl.subscription_view(FakeSB(), CHART)
    assert v["state"] == "free" and not v["is_paid"] and not v["can_cancel"]


# ── Razorpay ────────────────────────────────────────────────────────────────────
def rzp(event, status="active", end_days=30, notes=True, sub_id="sub_rzp_1"):
    return {"event": event, "payload": {"subscription": {"entity": {
        "id": sub_id, "status": status, "current_end": ts(end_days),
        "notes": {"chart_id": CHART, "plan": "ask_unlimited_monthly"} if notes else {}}},
        "payment": {"entity": {"id": "pay_1", "subscription_id": sub_id}}}}


def test_razorpay_activation_charge_and_renewal():
    sb = FakeSB()
    assert bl.handle_razorpay_event(rzp("subscription.activated"), sb)["action"] == "activated"
    assert sb.sub["plan"] == "paid" and sb.sub["payment_provider"] == "razorpay" and tier(sb) == "paid"
    bl.handle_razorpay_event(rzp("subscription.charged", end_days=60), sb)
    assert abs((datetime.fromisoformat(sb.sub["current_period_end"]) - (NOW + timedelta(days=60))).total_seconds()) < 5


def test_razorpay_events_find_the_chart_by_subscription_id_when_notes_are_missing():
    sb = FakeSB()
    bl.handle_razorpay_event(rzp("subscription.activated"), sb)
    r = bl.handle_razorpay_event(rzp("subscription.pending", notes=False), sb)
    assert r["action"] == "past_due" and tier(sb) == "paid"


def test_razorpay_halted_ends_access_and_cancel_at_cycle_end_keeps_it():
    sb = FakeSB()
    bl.handle_razorpay_event(rzp("subscription.activated"), sb)
    r = bl.handle_razorpay_event(rzp("subscription.cancelled", end_days=15), sb)
    assert r["action"] == "cancel_scheduled" and tier(sb) == "paid"
    assert bl.subscription_view(sb, CHART)["state"] == "cancelling"
    bl.handle_razorpay_event(rzp("subscription.completed"), sb)
    assert tier(sb) == "free"
    sb2 = FakeSB()
    bl.handle_razorpay_event(rzp("subscription.activated"), sb2)
    bl.handle_razorpay_event(rzp("subscription.halted"), sb2)
    assert tier(sb2) == "free" and sb2.sub["status"] == "expired"


def test_razorpay_user_cancel_calls_the_provider_at_cycle_end():
    sb = FakeSB()
    bl.handle_razorpay_event(rzp("subscription.activated"), sb)
    seen = []

    class Client:
        class subscription:
            @staticmethod
            def cancel(sid, opts):
                seen.append((sid, opts))

    r = bl.cancel_subscription(sb, CHART, razorpay_client=Client)
    assert r["ok"] and seen == [("sub_rzp_1", {"cancel_at_cycle_end": 1})]
    assert bl.subscription_view(sb, CHART)["state"] == "cancelling"
    assert bl.subscription_view(sb, CHART)["can_resume"] is False


def test_razorpay_subscription_signature_and_plan_config(monkeypatch):
    from antar_engine import payment_engine as pe
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "s3cret")
    good = hmac.new(b"s3cret", b"pay_1|sub_1", hashlib.sha256).hexdigest()
    assert pe.verify_razorpay_subscription("pay_1", "sub_1", good)["verified"] is True
    assert pe.verify_razorpay_subscription("pay_1", "sub_1", "bad")["verified"] is False
    monkeypatch.delenv("RAZORPAY_PLAN_ID_MONTHLY", raising=False)
    assert pe.create_razorpay_subscription(CHART, "ask_unlimited_monthly")["error"] == "razorpay_plan_not_configured"
    assert bl.razorpay_plan_id("ask_unlimited_annual") == ""


# ── the routes (signature gate + dispatch) ──────────────────────────────────────
def test_razorpay_webhook_route_dispatches_subscription_events(monkeypatch):
    import main
    from fastapi.testclient import TestClient
    sb = FakeSB()
    monkeypatch.setattr(main, "supabase", sb)
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "s3cret")
    body = json.dumps(rzp("subscription.activated")).encode()
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    c = TestClient(main.app)
    bad = c.post("/api/v1/payments/razorpay/webhook", content=body, headers={"x-razorpay-signature": "nope"})
    assert bad.status_code == 400 and not sb.db["subscriptions"]
    ok = c.post("/api/v1/payments/razorpay/webhook", content=body, headers={"x-razorpay-signature": sig})
    assert ok.status_code == 200 and tier(sb) == "paid"


def test_stripe_webhook_route_runs_the_lifecycle(monkeypatch):
    stripe = pytest.importorskip("stripe")
    import main
    from fastapi.testclient import TestClient
    sb = FakeSB()
    monkeypatch.setattr(main, "supabase", sb)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_x")
    ev, fetch = stripe_checkout()
    monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(lambda body, sig, secret: ev))
    monkeypatch.setattr(stripe.Subscription, "retrieve", staticmethod(lambda sid: fetch(sid)), raising=False)
    c = TestClient(main.app)
    r = c.post("/api/v1/payments/stripe/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})
    assert r.status_code == 200 and tier(sb) == "paid"
    ev2 = {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_1", "metadata": {"chart_id": CHART}}}}
    monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(lambda body, sig, secret: ev2))
    r2 = c.post("/api/v1/payments/stripe/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})
    assert r2.status_code == 200 and tier(sb) == "free"


def test_status_endpoint_carries_the_billing_view(monkeypatch):
    import main
    from fastapi.testclient import TestClient
    sb = FakeSB()
    monkeypatch.setattr(main, "supabase", sb)
    ev, fetch = stripe_checkout()
    bl.handle_stripe_event(ev, sb, fetch_subscription=fetch)
    r = TestClient(main.app).get(f"/api/v1/subscription/{CHART}")
    assert r.status_code == 200
    b = r.json()["billing"]
    assert b["state"] == "active" and b["is_paid"] and b["provider"] == "stripe" and b["can_cancel"]
