"""
antar_engine/singleflight.py

[singleflight 2026-07-25] Cross-worker single-flight for daily-signal / daily-week
generation, so a burst of concurrent requests for the SAME (chart, date, language)
produces exactly ONE LLM generation instead of one per request.

Why: the client fires a storm of daily-signal/daily-week calls on login (Railway
logs: ~8 daily-signal for one chart, one load). On the first open of the day they
all miss the cache at once and each starts its own generation — a stampede that
burns Sonnet cost, triggers the validation-retry pile-up, and strands the user on
a spinner. The nightly prewarm makes this rare; this makes it impossible.

Coordination is two-layer:
  * in-process: a module set, so concurrent async tasks in ONE worker coalesce
    with no DB round-trip;
  * cross-worker: a marker row in the EXISTING daily_surface_cache table (PK
    (chart_id, surface, language, local_date, variant)), so the 4 uvicorn workers
    coalesce too. No new table — DDL here goes through Lovable Cloud, so reusing
    an existing table keeps this a pure code change.

Fail-open by contract: if the lock store misbehaves, callers proceed to generate.
A stampede is a cost/latency problem; a blocked daily card is a broken product.
The winner is not tracked as "the one true generator" — losers simply wait for
the cache and fall back to generating themselves if the wait times out.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Set, Tuple

_LOCK_SURFACE = "__genlock__"
_INFLIGHT: Set[Tuple[str, str, str, str]] = set()


def _k(chart_id, date_str, language, variant):
    return (chart_id, date_str, language, variant)


def try_acquire(sb, chart_id, date_str, language, variant="signal", ttl=180) -> bool:
    """True if THIS caller should generate; False if a peer already is.

    A False return is the signal to wait on the cache (see the engine's
    _sf_wait_for_signal) rather than generate.
    """
    if not (sb and chart_id and date_str and language):
        return True  # can't coordinate -> just generate
    key = _k(chart_id, date_str, language, variant)
    if key in _INFLIGHT:
        return False  # another task in THIS worker owns it
    try:
        # Reclaim a lock abandoned by a crashed generator before trying to claim.
        stale = (datetime.now(timezone.utc) - timedelta(seconds=ttl)).isoformat()
        sb.table("daily_surface_cache").delete() \
            .eq("chart_id", chart_id).eq("surface", _LOCK_SURFACE) \
            .eq("language", language).eq("local_date", date_str) \
            .eq("variant", variant).lt("created_at", stale).execute()
        # Claim: the PK makes this the atomic mutex — a second inserter gets 23505.
        sb.table("daily_surface_cache").insert({
            "chart_id": chart_id, "surface": _LOCK_SURFACE, "language": language,
            "local_date": date_str, "variant": variant, "payload": {},
        }).execute()
        _INFLIGHT.add(key)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "23505" in msg or "duplicate" in msg or "conflict" in msg:
            return False  # a peer holds the lock
        # Lock store is broken — fail OPEN so the card still generates.
        _INFLIGHT.add(key)
        return True


def release(sb, chart_id, date_str, language, variant="signal") -> None:
    """Release a lock acquired by try_acquire. Never raises."""
    _INFLIGHT.discard(_k(chart_id, date_str, language, variant))
    try:
        sb.table("daily_surface_cache").delete() \
            .eq("chart_id", chart_id).eq("surface", _LOCK_SURFACE) \
            .eq("language", language).eq("local_date", date_str) \
            .eq("variant", variant).execute()
    except Exception:
        pass
