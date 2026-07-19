"""
push_sender.py — push notification sender for both platforms.

  • iOS  → direct APNs over HTTP/2 with a `.p8` token-auth key (no third party).
  • Android → Firebase Cloud Messaging (FCM) HTTP v1 with a service account.

Tokens live in `device_tokens` with a `platform` column ("ios" | "android");
send_to_tokens() routes each token to the right transport. Everything is
fail-open — if a transport is unconfigured its tokens are skipped silently.
Dead tokens (Unregistered / BadDeviceToken on APNs, UNREGISTERED / NOT_FOUND on
FCM) are pruned from device_tokens.

Env vars (Railway):
  # APNs (iOS)
  APNS_KEY_P8 | APNS_KEY_P8_BASE64   the .p8 private key (PEM; \\n-escaped ok)
  APNS_KEY_ID, APNS_TEAM_ID
  APNS_BUNDLE_ID    (default "world.antar.app")
  APNS_USE_SANDBOX  "1" (default) sandbox host; "0" production
  # FCM (Android)
  FCM_SERVICE_ACCOUNT_JSON | FCM_SERVICE_ACCOUNT_JSON_BASE64
                    the Firebase service-account JSON (Project settings →
                    Service accounts → Generate new private key). project_id,
                    client_email and private_key are read from it.
"""
from __future__ import annotations

import os
import json
import base64
import time
import asyncio
from typing import Optional

import httpx

try:
    import jwt as _pyjwt  # PyJWT (ES256 for APNs, RS256 for the FCM SA JWT)
except Exception:  # pragma: no cover
    _pyjwt = None

# ── APNs config ──────────────────────────────────────────────────────────────
_BUNDLE_ID = os.getenv("APNS_BUNDLE_ID", "world.antar.app")
_KEY_ID = os.getenv("APNS_KEY_ID")
_TEAM_ID = os.getenv("APNS_TEAM_ID")
_USE_SANDBOX = os.getenv("APNS_USE_SANDBOX", "1") not in ("0", "false", "False", "")
_APNS_HOST = "api.sandbox.push.apple.com" if _USE_SANDBOX else "api.push.apple.com"
_APNS_DEAD = {"Unregistered", "BadDeviceToken", "DeviceTokenNotForTopic"}

# ── FCM config ───────────────────────────────────────────────────────────────
_FCM_DEAD = {"UNREGISTERED", "NOT_FOUND", "INVALID_ARGUMENT"}
_OAUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"
_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


def _load_apns_p8() -> Optional[str]:
    b64 = os.getenv("APNS_KEY_P8_BASE64")
    if b64:
        try:
            return base64.b64decode(b64).decode("utf-8")
        except Exception:
            return None
    raw = os.getenv("APNS_KEY_P8")
    return raw.replace("\\n", "\n") if raw else None


def _load_fcm_sa() -> Optional[dict]:
    raw = os.getenv("FCM_SERVICE_ACCOUNT_JSON")
    b64 = os.getenv("FCM_SERVICE_ACCOUNT_JSON_BASE64")
    try:
        if b64:
            raw = base64.b64decode(b64).decode("utf-8")
        if not raw:
            return None
        sa = json.loads(raw)
        if sa.get("client_email") and sa.get("private_key") and sa.get("project_id"):
            return sa
    except Exception:
        pass
    return None


def apns_configured() -> bool:
    return bool(_pyjwt and _KEY_ID and _TEAM_ID and _load_apns_p8())


def fcm_configured() -> bool:
    return bool(_pyjwt and _load_fcm_sa())


def is_configured() -> bool:
    return apns_configured() or fcm_configured()


# ── APNs ─────────────────────────────────────────────────────────────────────
_apns_jwt_cache: dict = {"token": None, "iat": 0.0}


def _apns_provider_jwt() -> Optional[str]:
    now = time.time()
    if _apns_jwt_cache["token"] and (now - _apns_jwt_cache["iat"]) < 3000:
        return _apns_jwt_cache["token"]
    p8 = _load_apns_p8()
    if not (_pyjwt and p8 and _KEY_ID and _TEAM_ID):
        return None
    try:
        token = _pyjwt.encode({"iss": _TEAM_ID, "iat": int(now)}, p8,
                              algorithm="ES256", headers={"kid": _KEY_ID})
        _apns_jwt_cache.update(token=token, iat=now)
        return token
    except Exception as e:
        print(f"[push] APNs JWT sign failed: {e}")
        return None


async def _send_apns_one(client, jwt_token, device_token, title, body, data):
    payload = {"aps": {"alert": {"title": title, "body": body}, "sound": "default"}}
    if data:
        payload.update(data)
    headers = {"authorization": f"bearer {jwt_token}", "apns-topic": _BUNDLE_ID,
               "apns-push-type": "alert", "apns-priority": "10"}
    try:
        r = await client.post(f"https://{_APNS_HOST}/3/device/{device_token}",
                              json=payload, headers=headers)
        if r.status_code == 200:
            return True, 200, "ok"
        try:
            reason = (r.json() or {}).get("reason", "")
        except Exception:
            reason = r.text[:120]
        return False, r.status_code, reason
    except Exception as e:
        return False, 0, f"exc:{type(e).__name__}"


async def _send_apns(sb, rows, title, body, data):
    """rows: [{token}]. Returns (sent, failed, dead_tokens)."""
    jwt_token = _apns_provider_jwt()
    if not jwt_token:
        return 0, len(rows), []
    sent = failed = 0
    dead: list[str] = []
    async with httpx.AsyncClient(http2=True, timeout=10.0) as client:  # APNs needs HTTP/2
        results = await asyncio.gather(*[
            _send_apns_one(client, jwt_token, r["token"], title, body, data) for r in rows
        ], return_exceptions=True)
    for r, res in zip(rows, results):
        if isinstance(res, Exception):
            failed += 1
            continue
        ok, status, reason = res
        if ok:
            sent += 1
        else:
            failed += 1
            if status == 410 or reason in _APNS_DEAD:
                dead.append(r["token"])
    return sent, failed, dead


# ── FCM ──────────────────────────────────────────────────────────────────────
_fcm_tok_cache: dict = {"token": None, "exp": 0.0}


async def _fcm_access_token() -> Optional[str]:
    now = time.time()
    if _fcm_tok_cache["token"] and now < _fcm_tok_cache["exp"] - 300:
        return _fcm_tok_cache["token"]
    sa = _load_fcm_sa()
    if not (_pyjwt and sa):
        return None
    try:
        assertion = _pyjwt.encode(
            {"iss": sa["client_email"], "scope": _FCM_SCOPE, "aud": _OAUTH_TOKEN_URI,
             "iat": int(now), "exp": int(now) + 3600},
            sa["private_key"], algorithm="RS256")
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(_OAUTH_TOKEN_URI, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion})
        if r.status_code != 200:
            print(f"[push] FCM token exchange failed: {r.status_code} {r.text[:120]}")
            return None
        j = r.json()
        _fcm_tok_cache.update(token=j["access_token"], exp=now + j.get("expires_in", 3600))
        return _fcm_tok_cache["token"]
    except Exception as e:
        print(f"[push] FCM token exchange error: {e}")
        return None


async def _send_fcm_one(client, access_token, project_id, token, title, body, data):
    msg = {"message": {"token": token,
                       "notification": {"title": title, "body": body},
                       "android": {"priority": "high"}}}
    if data:
        # FCM data values must be strings.
        msg["message"]["data"] = {str(k): str(v) for k, v in data.items()}
    try:
        r = await client.post(
            f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
            json=msg, headers={"Authorization": f"Bearer {access_token}"})
        if r.status_code == 200:
            return True, 200, "ok"
        reason = ""
        try:
            reason = ((r.json() or {}).get("error", {}) or {}).get("status", "")
        except Exception:
            reason = r.text[:120]
        return False, r.status_code, reason
    except Exception as e:
        return False, 0, f"exc:{type(e).__name__}"


async def _send_fcm(sb, rows, title, body, data):
    """rows: [{token}]. Returns (sent, failed, dead_tokens)."""
    access = await _fcm_access_token()
    sa = _load_fcm_sa()
    if not (access and sa):
        return 0, len(rows), []
    project_id = sa["project_id"]
    sent = failed = 0
    dead: list[str] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await asyncio.gather(*[
            _send_fcm_one(client, access, project_id, r["token"], title, body, data)
            for r in rows
        ], return_exceptions=True)
    for r, res in zip(rows, results):
        if isinstance(res, Exception):
            failed += 1
            continue
        ok, status, reason = res
        if ok:
            sent += 1
        else:
            failed += 1
            if status in (404, 400) or reason in _FCM_DEAD:
                dead.append(r["token"])
    return sent, failed, dead


# ── Public API ───────────────────────────────────────────────────────────────
async def send_to_tokens(sb, rows: list[dict], title: str, body: str,
                         data: Optional[dict] = None) -> dict:
    """rows: [{token, platform}]. Routes ios→APNs, android→FCM, prunes dead
    tokens. Fail-open — never raises."""
    rows = [r for r in (rows or []) if r.get("token")]
    if not rows:
        return {"sent": 0, "failed": 0, "pruned": 0, "configured": is_configured()}

    ios = [r for r in rows if (r.get("platform") or "ios").lower() != "android"]
    android = [r for r in rows if (r.get("platform") or "").lower() == "android"]

    sent = failed = 0
    dead: list[str] = []
    if ios and apns_configured():
        s, f, d = await _send_apns(sb, ios, title, body, data)
        sent += s; failed += f; dead += d
    elif ios:
        failed += len(ios)
    if android and fcm_configured():
        s, f, d = await _send_fcm(sb, android, title, body, data)
        sent += s; failed += f; dead += d
    elif android:
        failed += len(android)

    pruned = 0
    if dead:
        try:
            sb.table("device_tokens").delete().in_("token", dead).execute()
            pruned = len(dead)
        except Exception as e:
            print(f"[push] prune failed: {e}")

    return {"sent": sent, "failed": failed, "pruned": pruned, "configured": is_configured()}


async def send_to_chart(sb, chart_id: str, title: str, body: str,
                        data: Optional[dict] = None) -> dict:
    """Look up all device tokens (both platforms) for a chart and push to them."""
    if not is_configured():
        return {"sent": 0, "failed": 0, "pruned": 0, "configured": False}
    try:
        res = sb.table("device_tokens").select("token, platform") \
            .eq("chart_id", chart_id).execute()
        rows = res.data or []
    except Exception as e:
        print(f"[push] token lookup failed for {chart_id}: {e}")
        rows = []
    return await send_to_tokens(sb, rows, title, body, data)
