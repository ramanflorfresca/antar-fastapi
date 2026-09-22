"""
antar_engine/iap_renewals.py  —  store renewal / lifecycle notifications.

The purchase-time endpoints (payments/apple/verify-receipt,
payments/google/verify-purchase) only ever see period 1. Everything after
that — renewals, cancellations, refunds, billing retry, grace periods,
account holds — arrives asynchronously from the stores:

  Apple   App Store Server Notifications V2  (JWS-signed, self-authenticating)
  Google  Real-Time Developer Notifications  (Pub/Sub push, NOT signed)

This module is PURE: it verifies and normalises those payloads and says what
should happen. It touches no database. main.py owns the entitlement writes,
exactly as it does for the purchase-time path.

Security model
  Apple  — the notification IS the authority, so its signature must be fully
           verified: ES256 over the JWS, plus the x5c certificate chain
           validated up to Apple Root CA G3, plus bundle-id pinning.
           Fails closed if the root certificate is not configured.
  Google — the RTDN payload is NOT signed and carries no proof of anything.
           It is only a TRIGGER. Authoritative state is always re-fetched
           from the Play Developer API via iap_engine.verify_google().
           Endpoint authenticity is a shared secret on the push URL.

Env vars
  APPLE_ROOT_CA_PEM     Apple Root CA G3, PEM text (takes precedence)
  APPLE_ROOT_CA_PATH    ...or a path to it. Default: certs/AppleRootCA-G3.pem
  APPLE_BUNDLE_ID       expected bundle id, e.g. world.antar.app
  IAP_TEST_MODE         "1" accepts synthetic payloads (see _maybe_test)
"""

import base64
import json
import os
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

DEFAULT_ROOT_PATH = "certs/AppleRootCA-G3.pem"


# ══════════════════════════════ helpers ══════════════════════════════
def _b64url(seg: str) -> bytes:
    """Decode a base64url JWS segment (padding is optional in JWS)."""
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def _ms_to_iso(ms) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


def _cert_window(cert):
    """not_before, not_after as aware datetimes across cryptography versions."""
    nb = getattr(cert, "not_valid_before_utc", None)
    na = getattr(cert, "not_valid_after_utc", None)
    if nb is None:
        nb = cert.not_valid_before.replace(tzinfo=timezone.utc)
    if na is None:
        na = cert.not_valid_after.replace(tzinfo=timezone.utc)
    return nb, na


def _load_apple_root() -> bytes:
    """Apple Root CA G3 as PEM bytes. Raises if not configured (fail closed)."""
    pem = os.getenv("APPLE_ROOT_CA_PEM", "").strip()
    if pem:
        return pem.encode()
    path = os.getenv("APPLE_ROOT_CA_PATH", "") or DEFAULT_ROOT_PATH
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except Exception as e:
        raise ValueError(
            f"Apple root CA not configured ({e}). Set APPLE_ROOT_CA_PEM, or "
            f"place the certificate at {path}. See tools/fetch_apple_root_ca.sh"
        )


# ══════════════════════════════ APPLE ══════════════════════════════
def verify_apple_jws(signed_payload: str) -> dict:
    """
    Verify an Apple JWS (a notification, or a signedTransactionInfo /
    signedRenewalInfo nested inside one) and return its decoded payload.

    Verification is the whole point of this function — an unverified payload
    is an attacker-controlled renewal. Raises ValueError on any failure.
    """
    if not signed_payload or signed_payload.count(".") != 2:
        raise ValueError("malformed JWS")
    header_b64, payload_b64, sig_b64 = signed_payload.split(".")

    try:
        header = json.loads(_b64url(header_b64))
    except Exception as e:
        raise ValueError(f"bad JWS header: {e}")
    if header.get("alg") != "ES256":
        raise ValueError(f"unexpected alg {header.get('alg')!r} (want ES256)")

    x5c = header.get("x5c") or []
    if len(x5c) < 2:
        raise ValueError("JWS header carries no certificate chain")

    try:
        chain = [x509.load_der_x509_certificate(base64.b64decode(c)) for c in x5c]
    except Exception as e:
        raise ValueError(f"unparseable x5c chain: {e}")

    # 1. The root presented in the chain must BE Apple's root, byte for byte.
    trusted = x509.load_pem_x509_certificate(_load_apple_root())
    if chain[-1].fingerprint(hashes.SHA256()) != trusted.fingerprint(hashes.SHA256()):
        raise ValueError("chain does not terminate at the trusted Apple root")

    # 2. Every certificate must currently be valid.
    now = datetime.now(timezone.utc)
    for cert in chain:
        nb, na = _cert_window(cert)
        if not (nb <= now <= na):
            raise ValueError("certificate in chain is expired or not yet valid")

    # 3. Each certificate must actually be signed by the next one up.
    for lower, upper in zip(chain, chain[1:]):
        if lower.issuer != upper.subject:
            raise ValueError("broken issuer/subject linkage in chain")
        try:
            upper.public_key().verify(
                lower.signature,
                lower.tbs_certificate_bytes,
                ec.ECDSA(lower.signature_hash_algorithm),
            )
        except Exception as e:
            raise ValueError(f"chain signature invalid: {e}")

    # 4. Finally the payload signature itself. JWS ES256 is raw r||s; the
    #    cryptography API wants DER.
    sig = _b64url(sig_b64)
    if len(sig) != 64:
        raise ValueError("ES256 signature must be 64 bytes")
    der = encode_dss_signature(
        int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
    )
    try:
        chain[0].public_key().verify(
            der, f"{header_b64}.{payload_b64}".encode(), ec.ECDSA(hashes.SHA256())
        )
    except Exception as e:
        raise ValueError(f"payload signature invalid: {e}")

    return json.loads(_b64url(payload_b64))


def _maybe_test_apple(signed_payload: str):
    """IAP_TEST_MODE=1 — accept a plain JSON notification, unsigned.

    Lets the endpoint be exercised before the Apple root cert and real
    notifications exist. Never fires unless the env var is explicitly set.
    """
    if os.getenv("IAP_TEST_MODE", "") != "1":
        return None
    try:
        obj = json.loads(signed_payload)
    except Exception:
        return None
    # Any JSON object stands in for a verified JWS here — top-level
    # notification or nested transaction/renewal info alike. A genuine JWS is
    # not valid JSON, so real payloads always fall through to verification.
    return obj if isinstance(obj, dict) else None


def parse_apple_notification(signed_payload: str) -> dict:
    """
    Verify an App Store Server Notification V2 and flatten it to one dict.

    Returns: notification_type, subtype, bundle_id, environment, product_id,
             original_transaction_id, transaction_id, expires_iso,
             revoked (bool), auto_renew (bool|None), signed_ms (int)
    """
    body = _maybe_test_apple(signed_payload)
    verified = body is not None
    if body is None:
        body = verify_apple_jws(signed_payload)
        verified = True

    data = body.get("data") or {}
    bundle_id = data.get("bundleId") or ""

    want_bundle = os.getenv("APPLE_BUNDLE_ID", "")
    if want_bundle and bundle_id and want_bundle != bundle_id:
        raise ValueError(f"bundle mismatch {bundle_id!r}")

    tx = {}
    signed_tx = data.get("signedTransactionInfo") or ""
    if signed_tx:
        tx = _maybe_test_apple(signed_tx) or verify_apple_jws(signed_tx)

    renewal = {}
    signed_renewal = data.get("signedRenewalInfo") or ""
    if signed_renewal:
        try:
            renewal = _maybe_test_apple(signed_renewal) or verify_apple_jws(signed_renewal)
        except Exception:
            renewal = {}   # renewal info is advisory; never fail the notification on it

    auto_renew = renewal.get("autoRenewStatus")
    return {
        "verified":                verified,
        "notification_type":       body.get("notificationType") or "",
        "subtype":                 body.get("subtype") or "",
        "bundle_id":               bundle_id,
        "environment":             data.get("environment") or tx.get("environment") or "",
        "product_id":              tx.get("productId") or "",
        "original_transaction_id": tx.get("originalTransactionId") or "",
        "transaction_id":          tx.get("transactionId") or "",
        "expires_iso":             _ms_to_iso(tx.get("expiresDate")),
        "revoked":                 bool(tx.get("revocationDate")),
        "auto_renew":              None if auto_renew is None else bool(auto_renew),
        "signed_ms":               int(body.get("signedDate") or 0),
    }


# What each notification type means for entitlement.
#   activate   — user should have access; extend to the transaction's expiry
#   deactivate — access ends now
#   ignore     — informational; access state does not change
_APPLE_ACTIVATE = {
    "SUBSCRIBED",           # initial buy or resubscribe
    "DID_RENEW",            # the renewal we exist for
    "DID_RECOVER",          # recovered from a billing failure
    "OFFER_REDEEMED",
    "RENEWAL_EXTENDED",     # Apple granted extra time
    "REFUND_REVERSED",      # refund was reversed; access comes back
    "ONE_TIME_CHARGE",
}
_APPLE_DEACTIVATE = {
    "EXPIRED",              # ran out and did not renew
    "GRACE_PERIOD_EXPIRED", # grace ran out too
    "REFUND",               # money returned; entitlement goes with it
    "REVOKE",               # family sharing revoked
}
# Deliberately IGNORED:
#   DID_CHANGE_RENEWAL_STATUS — auto-renew toggled off. The user keeps access
#     until expiresDate; EXPIRED will arrive when it actually ends. Treating
#     this as a cancellation is the classic IAP bug: it cuts off a user who
#     has already paid for the rest of the period.
#   DID_FAIL_TO_RENEW — billing retry / grace. Access continues; EXPIRED or
#     GRACE_PERIOD_EXPIRED closes it out.
#   DID_CHANGE_RENEWAL_PREF — plan switch takes effect next period.
#   CONSUMPTION_REQUEST, REFUND_DECLINED, PRICE_INCREASE, TEST — no change.


def apple_action(notif: dict) -> str:
    ntype = notif.get("notification_type") or ""
    if notif.get("revoked"):
        return "deactivate"
    if ntype in _APPLE_DEACTIVATE:
        return "deactivate"
    if ntype in _APPLE_ACTIVATE:
        # An activation with an expiry already in the past is a no-op at best
        # and a resurrection at worst.
        exp = notif.get("expires_iso") or ""
        if exp:
            try:
                if datetime.fromisoformat(exp) <= datetime.now(timezone.utc):
                    return "deactivate"
            except Exception:
                pass
        return "activate"
    return "ignore"


# ══════════════════════════════ GOOGLE ══════════════════════════════
# purchases.subscriptions notificationType values.
GOOGLE_SUB_TYPES = {
    1:  "RECOVERED",       2:  "RENEWED",          3:  "CANCELED",
    4:  "PURCHASED",       5:  "ON_HOLD",          6:  "IN_GRACE_PERIOD",
    7:  "RESTARTED",       8:  "PRICE_CHANGE_CONFIRMED",
    9:  "DEFERRED",        10: "PAUSED",           11: "PAUSE_SCHEDULE_CHANGED",
    12: "REVOKED",         13: "EXPIRED",
}
# These end access immediately, without needing to ask the Play API.
GOOGLE_HARD_STOP = {"REVOKED", "EXPIRED", "ON_HOLD", "PAUSED"}


def parse_google_rtdn(envelope: dict) -> dict:
    """
    Unwrap a Pub/Sub push envelope into the DeveloperNotification inside it.

    Returns: kind ("subscription"|"one_time"|"voided"|"test"|"unknown"),
             type_name, purchase_token, product_id, package_name, message_id
    """
    msg = (envelope or {}).get("message") or {}
    raw = msg.get("data") or ""
    if not raw:
        raise ValueError("pub/sub envelope carries no message.data")
    try:
        note = json.loads(base64.b64decode(raw))
    except Exception as e:
        raise ValueError(f"undecodable RTDN payload: {e}")

    out = {
        "kind": "unknown", "type_name": "", "purchase_token": "",
        "product_id": "", "package_name": note.get("packageName") or "",
        "message_id": msg.get("messageId") or "",
    }

    if "subscriptionNotification" in note:
        sn = note["subscriptionNotification"]
        out.update(
            kind="subscription",
            type_name=GOOGLE_SUB_TYPES.get(sn.get("notificationType"), "UNKNOWN"),
            purchase_token=sn.get("purchaseToken") or "",
            product_id=sn.get("subscriptionId") or "",
        )
    elif "oneTimeProductNotification" in note:
        on = note["oneTimeProductNotification"]
        out.update(
            kind="one_time",
            type_name="PURCHASED" if on.get("notificationType") == 1 else "CANCELED",
            purchase_token=on.get("purchaseToken") or "",
            product_id=on.get("sku") or "",
        )
    elif "voidedPurchaseNotification" in note:
        vn = note["voidedPurchaseNotification"]
        out.update(
            kind="voided",
            type_name="VOIDED",
            purchase_token=vn.get("purchaseToken") or "",
            product_id=vn.get("productType") or "",
        )
    elif "testNotification" in note:
        out.update(kind="test", type_name="TEST")

    return out


# ── self-test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    os.environ["IAP_TEST_MODE"] = "1"

    # Apple: unsigned test payloads, action mapping.
    future = int((datetime.now(timezone.utc).timestamp() + 86400) * 1000)
    past   = int((datetime.now(timezone.utc).timestamp() - 86400) * 1000)
    tx_f = json.dumps({"productId": "ask_unlimited_monthly", "transactionId": "t2",
                       "originalTransactionId": "t1", "expiresDate": future})
    tx_p = json.dumps({"productId": "ask_unlimited_monthly", "transactionId": "t9",
                       "originalTransactionId": "t1", "expiresDate": past})

    def note(ntype, tx):
        return json.dumps({"notificationType": ntype, "subtype": "",
                           "signedDate": 1, "data": {"bundleId": "world.antar.app",
                           "environment": "Sandbox", "signedTransactionInfo": tx}})

    n = parse_apple_notification(note("DID_RENEW", tx_f))
    assert apple_action(n) == "activate", n
    assert n["original_transaction_id"] == "t1"
    assert apple_action(parse_apple_notification(note("EXPIRED", tx_f))) == "deactivate"
    assert apple_action(parse_apple_notification(note("REFUND", tx_f))) == "deactivate"
    # auto-renew switched off must NOT cut access short
    assert apple_action(parse_apple_notification(note("DID_CHANGE_RENEWAL_STATUS", tx_f))) == "ignore"
    assert apple_action(parse_apple_notification(note("DID_FAIL_TO_RENEW", tx_f))) == "ignore"
    # a renewal whose expiry is already past must not resurrect access
    assert apple_action(parse_apple_notification(note("DID_RENEW", tx_p))) == "deactivate"

    # a real (unsigned) JWS-shaped string must be rejected outright
    try:
        verify_apple_jws("aaa.bbb.ccc")
        raise AssertionError("unsigned JWS was accepted")
    except ValueError:
        pass

    # Google: envelope unwrapping.
    dev = {"packageName": "world.antar.app",
           "subscriptionNotification": {"notificationType": 2,
                                        "purchaseToken": "tok123",
                                        "subscriptionId": "ask_unlimited_monthly"}}
    env = {"message": {"data": base64.b64encode(json.dumps(dev).encode()).decode(),
                       "messageId": "m1"}}
    g = parse_google_rtdn(env)
    assert g["kind"] == "subscription" and g["type_name"] == "RENEWED"
    assert g["purchase_token"] == "tok123"

    voided = {"voidedPurchaseNotification": {"purchaseToken": "tok9", "orderId": "GPA.1"}}
    ev = {"message": {"data": base64.b64encode(json.dumps(voided).encode()).decode()}}
    assert parse_google_rtdn(ev)["kind"] == "voided"

    print("iap_renewals self-test OK")
