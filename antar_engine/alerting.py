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

Set ALERT_WEBHOOK_URL on Railway to route alerts to Slack/Discord/ops.
"""
from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger("antar.alert")

_last_sent: dict[str, float] = {}
_lock = threading.Lock()
_MIN_INTERVAL_S = 300.0  # per-key external-send throttle (5 min)

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
