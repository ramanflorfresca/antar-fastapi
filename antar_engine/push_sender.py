"""
push_sender.py — direct APNs (Apple Push Notification service) sender.

The iOS app registers via @capacitor/push-notifications, which yields raw APNs
device tokens (no FCM in the loop). We send to them directly over HTTP/2 using a
`.p8` token-auth key — no third-party push provider.

Configuration (env vars — set on Railway):
  APNS_KEY_P8       the .p8 private key contents (PEM). Railway strips newlines,
                    so a literal "\\n"-joined value is accepted and un-escaped.
  APNS_KEY_P8_BASE64  (alternative) base64 of the .p8 file — safest for env vars.
  APNS_KEY_ID       the Key ID of the .p8 (Apple Developer → Keys)
  APNS_TEAM_ID      your Apple Developer Team ID
  APNS_BUNDLE_ID    app bundle id (default "world.antar.app")
  APNS_USE_SANDBOX  "1" (default) → api.sandbox.push.apple.com, matches the
                    `development` aps-environment entitlement / TestFlight-dev builds.
                    Set "0" for App Store production tokens.

Everything is fail-open: if unconfigured, is_configured() is False and callers
skip silently. Dead tokens (Unregistered / BadDeviceToken) are pruned from
device_tokens so the table stays clean.
"""
from __future__ import annotations

import os
import base64
import time
import asyncio
from typing import Optional

import httpx

try:
    import jwt as _pyjwt  # PyJWT
except Exception:  # pragma: no cover
    _pyjwt = None

_BUNDLE_ID = os.getenv("APNS_BUNDLE_ID", "world.antar.app")
_KEY_ID = os.getenv("APNS_KEY_ID")
_TEAM_ID = os.getenv("APNS_TEAM_ID")
_USE_SANDBOX = os.getenv("APNS_USE_SANDBOX", "1") not in ("0", "false", "False", "")

_HOST = "api.sandbox.push.apple.com" if _USE_SANDBOX else "api.push.apple.com"

# Reasons that mean the token is permanently dead → prune it.
_DEAD_REASONS = {"Unregistered", "BadDeviceToken", "DeviceTokenNotForTopic"}

# JWT is cached and refreshed well within APNs' 60-minute limit.
_jwt_cache: dict = {"token": None, "iat": 0.0}


def _load_p8() -> Optional[str]:
    b64 = os.getenv("APNS_KEY_P8_BASE64")
    if b64:
        try:
            return base64.b64decode(b64).decode("utf-8")
        except Exception:
            return None
    raw = os.getenv("APNS_KEY_P8")
    if raw:
        # Railway/env stores multiline secrets as a single line with literal \n.
        return raw.replace("\\n", "\n")
    return None


def is_configured() -> bool:
    return bool(_pyjwt and _KEY_ID and _TEAM_ID and _load_p8())


def _provider_jwt() -> Optional[str]:
    """ES256 provider token, cached and refreshed every ~50 min."""
    now = time.time()
    if _jwt_cache["token"] and (now - _jwt_cache["iat"]) < 3000:
        return _jwt_cache["token"]
    p8 = _load_p8()
    if not (_pyjwt and p8 and _KEY_ID and _TEAM_ID):
        return None
    try:
        token = _pyjwt.encode(
            {"iss": _TEAM_ID, "iat": int(now)},
            p8,
            algorithm="ES256",
            headers={"kid": _KEY_ID},
        )
        _jwt_cache["token"] = token
        _jwt_cache["iat"] = now
        return token
    except Exception as e:
        print(f"[push] JWT sign failed: {e}")
        return None


async def _send_one(client: httpx.AsyncClient, jwt_token: str, device_token: str,
                    title: str, body: str, data: Optional[dict]) -> tuple[bool, int, str]:
    aps = {"alert": {"title": title, "body": body}, "sound": "default"}
    payload = {"aps": aps}
    if data:
        payload.update(data)
    headers = {
        "authorization": f"bearer {jwt_token}",
        "apns-topic": _BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    try:
        r = await client.post(f"https://{_HOST}/3/device/{device_token}",
                              json=payload, headers=headers)
        if r.status_code == 200:
            return True, 200, "ok"
        reason = ""
        try:
            reason = (r.json() or {}).get("reason", "")
        except Exception:
            reason = r.text[:120]
        return False, r.status_code, reason
    except Exception as e:
        return False, 0, f"exc:{type(e).__name__}"


async def send_to_tokens(sb, rows: list[dict], title: str, body: str,
                         data: Optional[dict] = None) -> dict:
    """rows: [{token, id?}]. Sends concurrently, prunes dead tokens. Returns a
    small summary dict. Fail-open — never raises."""
    if not rows or not is_configured():
        return {"sent": 0, "failed": 0, "pruned": 0, "configured": is_configured()}
    jwt_token = _provider_jwt()
    if not jwt_token:
        return {"sent": 0, "failed": 0, "pruned": 0, "configured": False}

    sent = failed = pruned = 0
    dead_tokens: list[str] = []
    # http2=True is REQUIRED — APNs only speaks HTTP/2.
    async with httpx.AsyncClient(http2=True, timeout=10.0) as client:
        results = await asyncio.gather(*[
            _send_one(client, jwt_token, row["token"], title, body, data)
            for row in rows if row.get("token")
        ], return_exceptions=True)

    for row, res in zip([r for r in rows if r.get("token")], results):
        if isinstance(res, Exception):
            failed += 1
            continue
        ok, status, reason = res
        if ok:
            sent += 1
        else:
            failed += 1
            if status == 410 or reason in _DEAD_REASONS:
                dead_tokens.append(row["token"])

    if dead_tokens:
        try:
            sb.table("device_tokens").delete().in_("token", dead_tokens).execute()
            pruned = len(dead_tokens)
        except Exception as e:
            print(f"[push] prune failed: {e}")

    return {"sent": sent, "failed": failed, "pruned": pruned, "configured": True}


async def send_to_chart(sb, chart_id: str, title: str, body: str,
                        data: Optional[dict] = None) -> dict:
    """Look up all device tokens for a chart and push to them."""
    if not is_configured():
        return {"sent": 0, "failed": 0, "pruned": 0, "configured": False}
    try:
        res = sb.table("device_tokens").select("token").eq("chart_id", chart_id).execute()
        rows = res.data or []
    except Exception as e:
        print(f"[push] token lookup failed for {chart_id}: {e}")
        rows = []
    return await send_to_tokens(sb, rows, title, body, data)
