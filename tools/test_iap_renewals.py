#!/usr/bin/env python3
"""
tools/test_iap_renewals.py — end-to-end test of the store renewal webhooks.

Drives the real FastAPI routes through TestClient with a fake Supabase, so it
exercises the actual handlers (lookup, guards, entitlement writes), not just
the parsing module. No network, no database.

Run:  IAP_TEST_MODE=1 ./venv311/bin/python tools/test_iap_renewals.py
"""
import json
import os
import sys

os.environ["IAP_TEST_MODE"] = "1"
os.environ["GOOGLE_RTDN_TOKEN"] = "rtdn-secret"
os.environ.setdefault("APPLE_BUNDLE_ID", "world.antar.app")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base64
from datetime import datetime, timedelta, timezone

import main
from fastapi.testclient import TestClient
import antar_engine.iap_engine as iap_engine
import antar_engine.subscription_engine as sub_engine

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)
PAST   = datetime.now(timezone.utc) - timedelta(days=2)

CALLS = {"activate": [], "updates": []}


# ── fake supabase ────────────────────────────────────────────────
class _Q:
    def __init__(self, tbl, rows, op="select", payload=None):
        self.tbl, self.rows, self.op, self.payload = tbl, rows, op, payload
        self.filters = {}

    def eq(self, k, v):
        self.filters[k] = v
        return self

    def limit(self, _n):
        return self

    def execute(self):
        if self.op == "update":
            CALLS["updates"].append((self.tbl, dict(self.filters), self.payload))
            return type("R", (), {"data": [self.payload]})()
        out = [r for r in self.rows
               if all(str(r.get(k)) == str(v) for k, v in self.filters.items())]
        return type("R", (), {"data": out})()


class FakeSupabase:
    def __init__(self):
        self.data = {"subscriptions": [], "compat_slot_purchases": []}

    def table(self, name):
        self._t = name
        return self

    def select(self, *_a, **_k):
        return _Q(self._t, self.data[self._t])

    def update(self, payload):
        return _Q(self._t, self.data[self._t], op="update", payload=payload)


def fake_activate(chart_id, plan, provider, provider_sub_id, period_end_iso, sb):
    CALLS["activate"].append(dict(chart_id=chart_id, plan=plan, provider=provider,
                                  provider_sub_id=provider_sub_id,
                                  period_end_iso=period_end_iso))
    return {"chart_id": chart_id, "plan": plan}


def reset(subs=None, slots=None):
    CALLS["activate"].clear()
    CALLS["updates"].clear()
    fake = FakeSupabase()
    fake.data["subscriptions"] = subs or []
    fake.data["compat_slot_purchases"] = slots or []
    main.supabase = fake
    return fake


sub_engine.activate_subscription = fake_activate
client = TestClient(main.app)

SUB_ROW = {"chart_id": "chart-1", "payment_provider": "apple",
           "provider_sub_id": "otx-1", "current_period_end": PAST.isoformat()}
GSUB_ROW = {"chart_id": "chart-2", "payment_provider": "google",
            "provider_sub_id": "tok-1", "current_period_end": PAST.isoformat()}


def apple_payload(ntype, product="ask_unlimited_monthly", expires=None,
                  otx="otx-1", txid="tx-9", subtype="", revoked=False):
    tx = {"productId": product, "transactionId": txid,
          "originalTransactionId": otx,
          "expiresDate": int((expires or FUTURE).timestamp() * 1000)}
    if revoked:
        tx["revocationDate"] = int(PAST.timestamp() * 1000)
    return {"signedPayload": json.dumps({
        "notificationType": ntype, "subtype": subtype, "signedDate": 1,
        "data": {"bundleId": "world.antar.app", "environment": "Sandbox",
                 "signedTransactionInfo": json.dumps(tx)}})}


def rtdn(ntype_num, token="tok-1", product="ask_unlimited_monthly", body=None):
    note = body or {"packageName": "world.antar.app",
                    "subscriptionNotification": {"notificationType": ntype_num,
                                                 "purchaseToken": token,
                                                 "subscriptionId": product}}
    return {"message": {"data": base64.b64encode(json.dumps(note).encode()).decode(),
                        "messageId": "m1"}}


PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


print("\nAPPLE")
reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications", json=apple_payload("DID_RENEW"))
check("DID_RENEW -> 200 activate", r.status_code == 200 and r.json()["action"] == "activate",
      f"{r.status_code} {r.text[:120]}")
check("DID_RENEW extends period", CALLS["activate"] and CALLS["activate"][0]["period_end_iso"][:4] == str(FUTURE.year))
check("canonicalises to originalTransactionId",
      CALLS["activate"] and CALLS["activate"][0]["provider_sub_id"] == "otx-1",
      str(CALLS["activate"]))

reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications", json=apple_payload("EXPIRED"))
check("EXPIRED -> deactivate", r.status_code == 200 and r.json()["action"] == "deactivate")
check("EXPIRED writes plan=free/status=expired",
      CALLS["updates"] and CALLS["updates"][0][2]["plan"] == "free"
      and CALLS["updates"][0][2]["status"] == "expired", str(CALLS["updates"]))

reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications", json=apple_payload("REFUND"))
check("REFUND -> hard deactivate (period closed now)",
      r.status_code == 200 and CALLS["updates"]
      and CALLS["updates"][0][2]["status"] == "cancelled"
      and "current_period_end" in CALLS["updates"][0][2], str(CALLS["updates"]))

reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications",
                json=apple_payload("DID_CHANGE_RENEWAL_STATUS"))
check("auto-renew off -> ignore, access untouched",
      r.json()["action"] == "ignore" and not CALLS["updates"] and not CALLS["activate"])

reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications", json=apple_payload("DID_FAIL_TO_RENEW"))
check("billing retry -> ignore, access untouched",
      r.json()["action"] == "ignore" and not CALLS["updates"])

# out-of-order: stored period already later than the notification's
reset([dict(SUB_ROW, current_period_end=(FUTURE + timedelta(days=30)).isoformat())])
r = client.post("/api/v1/payments/apple/notifications", json=apple_payload("DID_RENEW"))
check("stale renewal does not shorten the period",
      r.json()["action"] == "stale" and not CALLS["activate"], r.text[:120])

reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications",
                json=apple_payload("DID_RENEW", expires=PAST))
check("renewal with past expiry -> deactivate, not resurrect",
      r.json()["action"] == "deactivate", r.text[:120])

reset([])   # no matching subscription row
r = client.post("/api/v1/payments/apple/notifications", json=apple_payload("DID_RENEW"))
check("unknown transaction -> 404 so Apple retries", r.status_code == 404, str(r.status_code))

reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications", json={"signedPayload": "aaa.bbb.ccc"})
check("forged/unsigned JWS -> 400, nothing written",
      r.status_code == 400 and not CALLS["activate"] and not CALLS["updates"],
      f"{r.status_code} {r.text[:120]}")

reset([SUB_ROW])
r = client.post("/api/v1/payments/apple/notifications", json={})
check("missing signedPayload -> 400", r.status_code == 400)

reset([], [{"chart_id": "chart-3", "stripe_session_id": "apple:tx-9", "status": "paid"}])
r = client.post("/api/v1/payments/apple/notifications",
                json=apple_payload("REFUND", product="compat_chart"))
check("refunded consumable -> compat slot revoked",
      r.json()["action"] == "revoke_consumable"
      and CALLS["updates"] and CALLS["updates"][0][2]["status"] == "refunded",
      str(CALLS["updates"]))

print("\nGOOGLE")
reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn", json=rtdn(2))
check("missing ?token -> 403, nothing written",
      r.status_code == 403 and not CALLS["activate"], str(r.status_code))

reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=wrong", json=rtdn(2))
check("wrong token -> 403", r.status_code == 403)

iap_engine.verify_google = lambda pid, tok, kind="": {
    "valid": True, "kind": "subscription", "plan": "ask",
    "period_end_iso": FUTURE.isoformat(), "transaction_id": tok}
reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret", json=rtdn(2))
check("RENEWED -> re-reads Play API and activates",
      r.status_code == 200 and r.json()["action"] == "activate", r.text[:140])
check("google keyed on the stable purchase token",
      CALLS["activate"] and CALLS["activate"][0]["provider_sub_id"] == "tok-1",
      str(CALLS["activate"]))

reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret", json=rtdn(3))
check("CANCELED (auto-renew off) keeps access while Play says active",
      r.json()["action"] == "activate", r.text[:140])

reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret", json=rtdn(13))
check("EXPIRED -> deactivate without calling Play",
      r.json()["action"] == "deactivate" and not CALLS["activate"])

reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret", json=rtdn(5))
check("ON_HOLD -> deactivate", r.json()["action"] == "deactivate")

iap_engine.verify_google = lambda pid, tok, kind="": {"valid": False, "error": "not active"}
reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret", json=rtdn(1))
check("Play says not active -> deactivate", r.json()["action"] == "deactivate")

reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret",
                json=rtdn(0, body={"voidedPurchaseNotification":
                                   {"purchaseToken": "tok-1", "orderId": "GPA.1"}}))
check("voided purchase -> hard deactivate",
      r.json()["action"] == "deactivate"
      and CALLS["updates"] and CALLS["updates"][0][2]["status"] == "cancelled",
      str(CALLS["updates"]))

reset([])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret", json=rtdn(2))
check("unknown purchase token -> 404 so Pub/Sub retries", r.status_code == 404)

reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret",
                json=rtdn(0, body={"testNotification": {"version": "1.0"}}))
check("Play test notification -> 200 test", r.json()["action"] == "test")

os.environ["GOOGLE_RTDN_TOKEN"] = ""
reset([GSUB_ROW])
r = client.post("/api/v1/payments/google/rtdn?token=rtdn-secret", json=rtdn(2))
check("no secret configured -> 503 fail closed", r.status_code == 503)
os.environ["GOOGLE_RTDN_TOKEN"] = "rtdn-secret"

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
