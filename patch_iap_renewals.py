#!/usr/bin/env python3
"""
patch_iap_renewals.py — store renewal / lifecycle webhooks.

Adds:
  POST /api/v1/payments/apple/notifications   App Store Server Notifications V2
  POST /api/v1/payments/google/rtdn           Play Real-Time Developer Notifications
  _iap_find_chart / _iap_deactivate / _iap_revoke_consumable / _iap_bust

Closes the gap where purchase-time verification only ever saw period 1:
without these, a renewing subscriber silently lost access at the end of the
first period and a refunded user kept theirs forever.

Inserts before the canonical Stripe webhook handler (unique landmark).
Idempotent; creates main.py.bak_iap_renewals; ast.parse-verifies before writing.
"""
import ast
import shutil
import sys

TARGET = "main.py"
BAK = "main.py.bak_iap_renewals"
LANDMARK = '@app.post("/api/v1/payments/stripe/webhook")'
SENTINEL = "async def apple_store_notifications("

NEW_BLOCK = '''# ── Store renewal / lifecycle notifications [iap-renewals 2026-09-22] ──
# Purchase-time verification (verify-receipt / verify-purchase) only ever sees
# period 1. Renewals, refunds, cancellations, billing retry, grace periods and
# account holds all arrive asynchronously, here. Both routes converge on the
# SAME entitlement path the Stripe webhook and the purchase-time routes use.

def _iap_bust(chart_id: str):
    try:
        from antar_engine.entitlements import bust_entitlement_cache
        bust_entitlement_cache(chart_id)
    except Exception:
        pass


def _iap_find_chart(provider: str, *candidate_ids) -> str:
    """chart_id behind a store subscription, by whichever id we stored."""
    for cid in candidate_ids:
        if not cid:
            continue
        try:
            r = (supabase.table("subscriptions").select("chart_id")
                 .eq("payment_provider", provider)
                 .eq("provider_sub_id", str(cid)).limit(1).execute())
            if r.data:
                return r.data[0].get("chart_id") or ""
        except Exception as _e:
            print(f"[iap-renewals] lookup failed {provider}:{cid}: {_e}")
    return ""


def _iap_deactivate(chart_id: str, reason: str, hard: bool = False) -> dict:
    """Drop a store subscriber to free.

    `hard` (refund / revoke / void) also closes the paid period immediately.
    A natural expiry leaves current_period_end alone as the historical record —
    get_subscription() already reads a past period_end as expired."""
    patch = {"plan": "free",
             "status": "cancelled" if hard else "expired",
             "is_paid": False}
    if hard:
        patch["current_period_end"] = datetime.now(timezone.utc).isoformat()
    try:
        supabase.table("subscriptions").update(patch).eq("chart_id", chart_id).execute()
    except Exception as _e:
        raise HTTPException(500, f"deactivate failed: {_e}")
    _iap_bust(chart_id)
    print(f"[iap-renewals] {chart_id} -> free ({reason})")
    return {"received": True, "action": "deactivate", "reason": reason}


def _iap_revoke_consumable(provider: str, *ids) -> dict:
    """Refunded one-time purchase -> take the compatibility slot back.
    Keys match what _apply_iap_result wrote: f"{provider}:{transaction_id}"."""
    for raw in ids:
        if not raw:
            continue
        key = f"{provider}:{raw}"
        try:
            r = (supabase.table("compat_slot_purchases").select("chart_id")
                 .eq("stripe_session_id", key).limit(1).execute())
            if not r.data:
                continue
            _cid = r.data[0].get("chart_id") or ""
            supabase.table("compat_slot_purchases").update(
                {"status": "refunded"}).eq("stripe_session_id", key).execute()
            if _cid:
                _iap_bust(_cid)
            print(f"[iap-renewals] compat slot revoked ({key})")
            return {"received": True, "action": "revoke_consumable", "key": key}
        except Exception as _e:
            print(f"[iap-renewals] consumable revoke failed {key}: {_e}")
    return {"received": True, "action": "noop", "reason": "consumable not found"}


@app.post("/api/v1/payments/apple/notifications")
async def apple_store_notifications(request: Request):
    """
    App Store Server Notifications V2.  Body: {"signedPayload": "<JWS>"}

    The JWS is self-authenticating and IS the authority here, so it is fully
    verified before anything is written: ES256 signature, x5c chain validated
    up to Apple Root CA G3, and bundle-id pinning — all inside
    parse_apple_notification(). A verification failure is a hard 400: Apple
    retries, and dropping a real notification beats trusting a forged one.

    Configure in App Store Connect -> App Information -> App Store Server
    Notifications (V2), production + sandbox URLs.
    """
    from antar_engine.iap_renewals import parse_apple_notification, apple_action
    from antar_engine.iap_engine import PRODUCTS
    from antar_engine.subscription_engine import activate_subscription

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "body must be JSON")
    signed = (body or {}).get("signedPayload") or ""
    if not signed:
        raise HTTPException(400, "signedPayload required")

    try:
        notif = parse_apple_notification(signed)
    except ValueError as _ve:
        print(f"[iap-renewals apple] REJECTED: {_ve}")
        raise HTTPException(400, f"notification not verified: {_ve}")

    ntype   = notif["notification_type"]
    subtype = notif["subtype"] or "-"
    otx     = notif["original_transaction_id"]
    txid    = notif["transaction_id"]
    pid     = notif["product_id"]

    if ntype == "TEST":
        print("[iap-renewals apple] TEST notification verified OK")
        return {"received": True, "action": "test"}

    action = apple_action(notif)
    print(f"[iap-renewals apple] {ntype}/{subtype} product={pid} otx={otx} -> {action}")

    # Consumables (compat_chart) never touch the subscriptions table.
    spec = PRODUCTS.get(pid) or {}
    if spec.get("kind") == "consumable":
        if action == "deactivate":
            return _iap_revoke_consumable("apple", txid, otx)
        return {"received": True, "action": "ignore", "type": ntype}

    if action == "ignore":
        return {"received": True, "action": "ignore", "type": ntype}

    chart_id = _iap_find_chart("apple", otx, txid)
    if not chart_id:
        # Most often a race: the notification beat the client's verify-receipt
        # call. 404 keeps Apple retrying (it gives up after ~3 days) rather
        # than acking a renewal we failed to apply.
        print(f"[iap-renewals apple] no chart for otx={otx} txid={txid}")
        raise HTTPException(404, "no subscription for this transaction")

    if action == "deactivate":
        return _iap_deactivate(chart_id, f"apple:{ntype}",
                               hard=(ntype in ("REFUND", "REVOKE") or notif["revoked"]))

    period_end = notif["expires_iso"]
    if not period_end:
        raise HTTPException(400, f"{ntype} carries no expiry")

    # Out-of-order delivery guard: never walk a paid period backwards.
    try:
        _cur = (supabase.table("subscriptions").select("current_period_end")
                .eq("chart_id", chart_id).limit(1).execute())
        _have = (_cur.data or [{}])[0].get("current_period_end") or ""
        if _have and (datetime.fromisoformat(_have.replace("Z", "+00:00"))
                      >= datetime.fromisoformat(period_end.replace("Z", "+00:00"))):
            print(f"[iap-renewals apple] stale, kept {_have} (notification said {period_end})")
            return {"received": True, "action": "stale", "period_end": _have}
    except Exception:
        pass

    activate_subscription(
        chart_id=chart_id, plan=spec.get("plan") or "ask", provider="apple",
        # Canonicalise onto the ORIGINAL transaction id — it is the only Apple
        # identifier stable across renewals.
        provider_sub_id=str(otx or txid),
        period_end_iso=period_end, sb=supabase,
    )
    _iap_bust(chart_id)
    print(f"[iap-renewals apple] {chart_id} active through {period_end}")
    return {"received": True, "action": "activate", "period_end": period_end}


@app.post("/api/v1/payments/google/rtdn")
async def google_rtdn(request: Request):
    """
    Google Play Real-Time Developer Notifications (Pub/Sub push).

    Unlike Apple's, an RTDN payload is NOT signed and proves nothing on its
    own, so it is treated purely as a TRIGGER: authoritative state is always
    re-read from the Play Developer API via verify_google(). Endpoint
    authenticity is a shared secret on the push URL, which is how Google
    documents securing a plain HTTPS push endpoint:

        https://<host>/api/v1/payments/google/rtdn?token=<GOOGLE_RTDN_TOKEN>
    """
    import hmac as _hmac
    from antar_engine.iap_renewals import parse_google_rtdn, GOOGLE_HARD_STOP
    from antar_engine.iap_engine import verify_google, PRODUCTS
    from antar_engine.subscription_engine import activate_subscription

    want = os.getenv("GOOGLE_RTDN_TOKEN", "")
    if not want:
        # Fail closed, as the Stripe webhook does. Pub/Sub retries, so nothing
        # is lost while the secret is being configured.
        raise HTTPException(503, "GOOGLE_RTDN_TOKEN not configured")
    if not _hmac.compare_digest(request.query_params.get("token", ""), want):
        raise HTTPException(403, "bad rtdn token")

    try:
        envelope = await request.json()
    except Exception:
        raise HTTPException(400, "body must be JSON")
    try:
        note = parse_google_rtdn(envelope)
    except ValueError as _ve:
        raise HTTPException(400, str(_ve))

    kind  = note["kind"]
    tname = note["type_name"]
    token = note["purchase_token"]
    pid   = note["product_id"]
    print(f"[iap-renewals google] {kind}/{tname} product={pid} token={token[:12]}...")

    if kind == "test":
        return {"received": True, "action": "test"}

    if kind == "voided":
        _cid = _iap_find_chart("google", token)
        if _cid:
            return _iap_deactivate(_cid, "google:VOIDED", hard=True)
        return _iap_revoke_consumable("google", token)

    if kind == "one_time":
        if tname == "CANCELED":
            return _iap_revoke_consumable("google", token)
        return {"received": True, "action": "ignore", "type": tname}

    if kind != "subscription":
        return {"received": True, "action": "ignore", "type": tname}

    chart_id = _iap_find_chart("google", token)
    if not chart_id:
        print(f"[iap-renewals google] no chart for token={token[:12]}...")
        raise HTTPException(404, "no subscription for this purchase token")

    # REVOKED / EXPIRED / ON_HOLD / PAUSED end access without needing to ask.
    if tname in GOOGLE_HARD_STOP:
        return _iap_deactivate(chart_id, f"google:{tname}", hard=(tname == "REVOKED"))

    # Everything else (RENEWED, RECOVERED, CANCELED, IN_GRACE_PERIOD, DEFERRED,
    # RESTARTED, PRICE_CHANGE_CONFIRMED, PAUSE_SCHEDULE_CHANGED): ask Play what
    # is actually true now and mirror it. Note CANCELED means auto-renew was
    # turned off, NOT that access ends — the user keeps it until expiry, which
    # is exactly what the API will tell us.
    res = verify_google(pid, token, kind="subscription")
    if not res.get("valid"):
        return _iap_deactivate(chart_id, f"google:{tname}:{res.get('error')}")

    _spec = PRODUCTS.get(pid) or {}
    activate_subscription(
        chart_id=chart_id, plan=res.get("plan") or _spec.get("plan") or "ask",
        provider="google", provider_sub_id=token,
        period_end_iso=res.get("period_end_iso") or "", sb=supabase,
    )
    _iap_bust(chart_id)
    print(f"[iap-renewals google] {chart_id} active through {res.get('period_end_iso')}")
    return {"received": True, "action": "activate",
            "period_end": res.get("period_end_iso")}


'''


def main():
    src = open(TARGET, encoding="utf-8").read()

    if SENTINEL in src:
        print("already patched (sentinel present) — nothing to do")
        return 0

    idx = src.find(LANDMARK)
    if idx == -1:
        print(f"ERROR: landmark not found: {LANDMARK}")
        return 1
    if src.count(LANDMARK) != 1:
        print(f"ERROR: landmark appears {src.count(LANDMARK)}x — expected exactly 1")
        return 1

    out = src[:idx] + NEW_BLOCK + src[idx:]

    try:
        ast.parse(out)
    except SyntaxError as e:
        print(f"ERROR: patched source does not parse: {e}")
        return 1

    shutil.copyfile(TARGET, BAK)
    open(TARGET, "w", encoding="utf-8").write(out)
    print(f"patched {TARGET} (backup: {BAK})")
    print("  + POST /api/v1/payments/apple/notifications")
    print("  + POST /api/v1/payments/google/rtdn")
    return 0


if __name__ == "__main__":
    sys.exit(main())
