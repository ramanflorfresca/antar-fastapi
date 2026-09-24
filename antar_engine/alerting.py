"""
antar_engine/alerting.py  — [P0 observability 2026-09-05]

Lightweight, dependency-free alerting so a silent model degradation (the kind
that ran the whole app on DeepSeek for an unknown period) turns into a signal
instead of nothing. Fire-and-forget, rate-limited per key, fail-open — an alert
failure NEVER touches the answer path.

Behaviour:
  - ALWAYS logs the alert line (so it shows in Railway logs even with no webhook).
  - If ALERT_WEBHOOK_URL is set (a Slack-compatible incoming webhook, or any
    endpoint accepting {"text": ...}), POSTs there too, at most once per key per
    5 minutes so a storm of failures can't spam the channel.
  - If ALERT_EMAIL_TO is set (and RESEND_API_KEY is configured), ALSO emails via
    Resend — for teams with no Slack. Email is throttled harder (30 min per key)
    and only sent at ALERT_EMAIL_MIN_LEVEL or above (default "error"), because an
    inbox is more intrusive than a channel.

Set ALERT_WEBHOOK_URL and/or ALERT_EMAIL_TO on Railway. Either, both, or neither
works — with neither, alerts still land in the Railway logs.
"""
from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger("antar.alert")

_last_sent: dict[str, float] = {}
_lock = threading.Lock()
_MIN_INTERVAL_S = 300.0  # per-key webhook throttle (5 min)
_MIN_EMAIL_INTERVAL_S = 1800.0  # per-key email throttle (30 min)
_last_email: dict[str, float] = {}

# Only these levels reach email; webhook gets everything.
_LEVEL_RANK = {"info": 0, "warn": 1, "error": 2, "critical": 3}

_EMOJI = {"info": "ℹ️", "warn": "⚠️", "error": "🚨", "critical": "🔥"}


def alert(key: str, message: str, level: str = "warn", detail: str | None = None) -> None:
    """Record an operational alert. `key` groups/throttles related alerts."""
    line = f"[ALERT:{level}] {key}: {message}" + (f" | {detail}" if detail else "")
    try:
        (logger.error if level in ("error", "critical") else logger.warning)(line)
    except Exception:
        pass

    # Throttle the EXTERNAL send only; the log line above always fires.
    now = time.monotonic()
    try:
        with _lock:
            if now - _last_sent.get(key, 0.0) < _MIN_INTERVAL_S:
                return
            _last_sent[key] = now
    except Exception:
        return

    _send_webhook(key, message, level, detail)
    _send_email(key, message, level, detail, now)


def _send_webhook(key: str, message: str, level: str, detail: str | None) -> None:
    """POST {"text": ...} to a Slack/Discord-compatible incoming webhook."""
    url = os.environ.get("ALERT_WEBHOOK_URL")
    if not url:
        return
    try:
        import httpx
        emoji = _EMOJI.get(level, "⚠️")
        text = f"{emoji} *Antar {level.upper()}* — {key}\n{message}"
        if detail:
            text += f"\n```{str(detail)[:600]}```"
        httpx.post(url, json={"text": text}, timeout=2.5)
    except Exception as e:  # never raise from an alert
        try:
            logger.warning(f"[alert] webhook post failed: {e}")
        except Exception:
            pass


def _send_email(key: str, message: str, level: str, detail: str | None,
                now: float) -> None:
    """Email the alert via Resend, for setups with no chat webhook.

    Deliberately stricter than the webhook path: a mailbox is more intrusive
    than a channel, so this is gated on level and throttled to 30 min per key.
    Shares main.py's Resend config (RESEND_API_KEY / RESEND_FROM_EMAIL) but does
    NOT import from main.py — that would be a circular import, and this module
    must stay importable from anywhere in the engine.
    """
    to = (os.environ.get("ALERT_EMAIL_TO") or "").strip()
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    if not to or not api_key:
        return

    min_level = (os.environ.get("ALERT_EMAIL_MIN_LEVEL") or "error").lower()
    if _LEVEL_RANK.get(level, 1) < _LEVEL_RANK.get(min_level, 2):
        return

    try:
        with _lock:
            if now - _last_email.get(key, 0.0) < _MIN_EMAIL_INTERVAL_S:
                return
            _last_email[key] = now
    except Exception:
        return

    try:
        import html as _html
        import httpx
        sender = os.environ.get("RESEND_FROM_EMAIL", "antar@antar.world")
        emoji = _EMOJI.get(level, "⚠️")
        body = (
            f"<p><strong>{emoji} Antar {_html.escape(level.upper())}</strong> "
            f"&mdash; {_html.escape(key)}</p>"
            f"<p>{_html.escape(message)}</p>"
        )
        if detail:
            body += (
                "<pre style=\"background:#f4f4f5;padding:12px;border-radius:6px;"
                "white-space:pre-wrap;font-size:13px\">"
                f"{_html.escape(str(detail)[:2000])}</pre>"
            )
        body += (
            "<p style=\"color:#71717a;font-size:12px\">"
            "Sent by antar_engine/alerting.py. Set ALERT_EMAIL_MIN_LEVEL to change "
            "which levels email (info / warn / error / critical), or unset "
            "ALERT_EMAIL_TO to stop these.</p>"
        )
        httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"from": sender, "to": [to],
                  "subject": f"{emoji} Antar {level.upper()}: {key}",
                  "html": body},
            timeout=5.0,
        )
    except Exception as e:  # never raise from an alert
        try:
            logger.warning(f"[alert] email send failed: {e}")
        except Exception:
            pass
