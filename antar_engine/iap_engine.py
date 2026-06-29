"""
antar_engine/iap_engine.py  —  A1: in-app-purchase receipt validation.

Validates Apple App Store receipts and Google Play purchases, then normalises
them to a single shape the /payments/*/verify endpoints feed straight into the
EXISTING entitlement path (activate_subscription / compat_slot_purchases). A
store-IAP user is therefore identical to a web-Stripe user downstream:

  ask_unlimited_monthly / ask_unlimited_annual  -> plan "ask" subscription
                                                   (single Ask Unlimited SKU;
                                                    has_unlimited_ask == True)
  compat_chart                                  -> one consumable compat slot

No heavy SDKs: Apple uses verifyReceipt (requests); Google mints an
androidpublisher access token from a service-account JWT (PyJWT RS256) and
calls the Play Developer API over REST.

Env vars
  APPLE_SHARED_SECRET            App-specific shared secret (App Store Connect)
  APPLE_BUNDLE_ID               (optional) expected bundle id, e.g. world.antar.app
  GOOGLE_PLAY_SERVICE_ACCOUNT_JSON   the service-account JSON (raw string)
  GOOGLE_PLAY_PACKAGE           Android package, e.g. world.antar.twa
  IAP_TEST_MODE                 "1" enables the synthetic test-receipt path
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests

# ── Product catalogue ─────────────────────────────────────────────
# IDs MUST match what is created in App Store Connect + Play Console.
# kind: "subscription" grants Ask Unlimited via a seeker plan row;
#       "consumable" grants one compatibility-chart slot.
PRODUCTS = {
    "ask_unlimited_monthly": {"kind": "subscription", "plan": "ask", "period_days": 32},
    "ask_unlimited_annual":  {"kind": "subscription", "plan": "ask", "period_days": 366},
    "compat_chart":          {"kind": "consumable",   "plan": None,     "period_days": 0},
}

APPLE_VERIFY_PROD    = "https://buy.itunes.apple.com/verifyReceipt"
APPLE_VERIFY_SANDBOX = "https://sandbox.itunes.apple.com/verifyReceipt"
GOOGLE_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GOOGLE_API_ROOT      = "https://androidpublisher.googleapis.com/androidpublisher/v3"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _period_end(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _result(valid=False, **kw) -> dict:
    base = {
        "valid": valid, "kind": None, "product_id": None, "plan": None,
        "period_end_iso": None, "transaction_id": None,
        "environment": None, "error": None,
    }
    base.update(kw)
    return base


# ══════════════════════════════ TEST PATH ══════════════════════════════
# Lets Raman exercise the endpoints before real store credentials exist.
# Enable with IAP_TEST_MODE=1. The magic tokens below short-circuit to a
# synthetic valid result; nothing hits Apple / Google.
_TEST_TOKENS = {
    "TEST_VALID_ASK_UNLIMITED_MONTHLY": "ask_unlimited_monthly",
    "TEST_VALID_ASK_UNLIMITED_ANNUAL":  "ask_unlimited_annual",
    "TEST_VALID_COMPAT":                "compat_chart",
}


def _maybe_test(token: str) -> dict:
    if os.getenv("IAP_TEST_MODE", "") != "1":
        return None
    pid = _TEST_TOKENS.get((token or "").strip())
    if not pid:
        return None
    spec = PRODUCTS[pid]
    return _result(
        valid=True, kind=spec["kind"], product_id=pid, plan=spec["plan"],
        period_end_iso=_period_end(spec["period_days"]) if spec["kind"] == "subscription" else None,
        transaction_id=f"test_{pid}_{int(time.time())}",
        environment="test",
    )


# ══════════════════════════════ APPLE ══════════════════════════════
def verify_apple(receipt_data: str) -> dict:
    """
    Validate a base64 App Store receipt via verifyReceipt, auto-falling back
    to the sandbox endpoint on status 21007 (so TestFlight + sandbox buyers
    validate too). Returns the normalised result shape.
    """
    test = _maybe_test(receipt_data)
    if test is not None:
        return test

    if not receipt_data:
        return _result(error="receipt_data required")
    secret = os.getenv("APPLE_SHARED_SECRET", "")
    if not secret:
        return _result(error="APPLE_SHARED_SECRET not configured")

    payload = {
        "receipt-data": receipt_data,
        "password": secret,
        "exclude-old-transactions": True,
    }

    def _post(url):
        r = requests.post(url, json=payload, timeout=15)
        return r.json()

    try:
        data = _post(APPLE_VERIFY_PROD)
        env = "production"
        if data.get("status") == 21007:           # receipt is from the sandbox
            data = _post(APPLE_VERIFY_SANDBOX)
            env = "sandbox"
    except Exception as e:
        return _result(error=f"apple verify request failed: {e}")

    status = data.get("status")
    if status != 0:
        return _result(error=f"apple status {status}", environment=env)

    # Optional bundle-id pinning.
    want_bundle = os.getenv("APPLE_BUNDLE_ID", "")
    got_bundle = (data.get("receipt") or {}).get("bundle_id", "")
    if want_bundle and got_bundle and want_bundle != got_bundle:
        return _result(error=f"bundle mismatch {got_bundle}", environment=env)

    # Newest known product wins. latest_receipt_info covers auto-renewables;
    # the receipt.in_app array covers consumables / non-renewing.
    entries = (data.get("latest_receipt_info")
               or (data.get("receipt") or {}).get("in_app")
               or [])
    chosen, chosen_expiry = None, -1.0
    for e in entries:
        pid = e.get("product_id")
        if pid not in PRODUCTS:
            continue
        exp = float(e.get("expires_date_ms") or e.get("purchase_date_ms") or 0)
        if exp >= chosen_expiry:
            chosen, chosen_expiry = e, exp
    if not chosen:
        return _result(error="no known product in receipt", environment=env)

    pid = chosen["product_id"]
    spec = PRODUCTS[pid]
    txid = chosen.get("transaction_id") or chosen.get("original_transaction_id")

    if spec["kind"] == "subscription":
        exp_ms = chosen.get("expires_date_ms")
        if exp_ms:
            period_end = datetime.fromtimestamp(int(exp_ms) / 1000, tz=timezone.utc).isoformat()
        else:
            period_end = _period_end(spec["period_days"])
        # Reject an already-lapsed subscription.
        if datetime.fromisoformat(period_end) < datetime.now(timezone.utc):
            return _result(error="subscription expired", environment=env, product_id=pid)
        return _result(valid=True, kind="subscription", product_id=pid,
                       plan=spec["plan"], period_end_iso=period_end,
                       transaction_id=txid, environment=env)

    # consumable (compat_chart)
    return _result(valid=True, kind="consumable", product_id=pid, plan=None,
                   transaction_id=txid, environment=env)


# ══════════════════════════════ GOOGLE ══════════════════════════════
def _google_access_token() -> str:
    """Mint an androidpublisher access token from the service-account JWT."""
    import jwt  # PyJWT (already a dependency)
    raw = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON not configured")
    sa = json.loads(raw)
    now = int(time.time())
    claim = {
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/androidpublisher",
        "aud": GOOGLE_TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    assertion = jwt.encode(claim, sa["private_key"], algorithm="RS256")
    r = requests.post(GOOGLE_TOKEN_URL, data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def verify_google(product_id: str, purchase_token: str, kind: str = "") -> dict:
    """
    Validate a Google Play purchase. `kind` may be passed by the client
    ("subscription" / "consumable"); otherwise it is inferred from the
    product catalogue. Subscriptions use purchases.subscriptionsv2; one-time
    products use purchases.products.
    """
    test = _maybe_test(purchase_token) or _maybe_test(product_id)
    if test is not None:
        return test

    if product_id not in PRODUCTS:
        return _result(error=f"unknown product {product_id}")
    if not purchase_token:
        return _result(error="purchase_token required")
    package = os.getenv("GOOGLE_PLAY_PACKAGE", "")
    if not package:
        return _result(error="GOOGLE_PLAY_PACKAGE not configured")

    spec = PRODUCTS[product_id]
    kind = kind or spec["kind"]

    try:
        token = _google_access_token()
    except Exception as e:
        return _result(error=f"google auth failed: {e}")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        if kind == "subscription":
            url = f"{GOOGLE_API_ROOT}/applications/{package}/purchases/subscriptionsv2/tokens/{purchase_token}"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return _result(error=f"google sub status {r.status_code}: {r.text[:200]}")
            body = r.json()
            state = body.get("subscriptionState", "")
            if state not in ("SUBSCRIPTION_STATE_ACTIVE", "SUBSCRIPTION_STATE_IN_GRACE_PERIOD"):
                return _result(error=f"subscription not active ({state})")
            line = (body.get("lineItems") or [{}])[0]
            period_end = line.get("expiryTime") or _period_end(spec["period_days"])
            return _result(valid=True, kind="subscription", product_id=product_id,
                           plan=spec["plan"], period_end_iso=period_end,
                           transaction_id=body.get("latestOrderId") or purchase_token,
                           environment="production")
        else:
            url = f"{GOOGLE_API_ROOT}/applications/{package}/purchases/products/{product_id}/tokens/{purchase_token}"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return _result(error=f"google product status {r.status_code}: {r.text[:200]}")
            body = r.json()
            # purchaseState: 0 = purchased, 1 = canceled, 2 = pending
            if body.get("purchaseState", 1) != 0:
                return _result(error=f"product not purchased (state {body.get('purchaseState')})")
            return _result(valid=True, kind="consumable", product_id=product_id, plan=None,
                           transaction_id=body.get("orderId") or purchase_token,
                           environment="production")
    except Exception as e:
        return _result(error=f"google verify failed: {e}")


# ── self-test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    os.environ["IAP_TEST_MODE"] = "1"
    assert verify_apple("TEST_VALID_ASK_UNLIMITED_MONTHLY")["valid"]
    assert verify_apple("TEST_VALID_ASK_UNLIMITED_MONTHLY")["plan"] == "ask"
    assert verify_apple("TEST_VALID_COMPAT")["kind"] == "consumable"
    assert verify_google("compat_chart", "TEST_VALID_COMPAT")["kind"] == "consumable"
    assert verify_google("ask_unlimited_annual", "TEST_VALID_ASK_UNLIMITED_ANNUAL")["plan"] == "ask"
    assert not verify_apple("garbage")["valid"]
    print("iap_engine self-test 6/6 OK")
