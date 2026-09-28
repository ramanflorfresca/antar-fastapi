"""
antar_engine/dasha_cache.py
───────────────────────────
Process-local cache for dasha_periods rows.

[loop-unblock 2026-09-28] `supabase-py` is a SYNCHRONOUS client, so every query
made from inside an `async def` handler blocks the whole event loop — not just
that request. dasha_periods was the worst offender on the daily surfaces: ~900
rows per chart, ~190ms per fetch, and the same rows were being fetched TEN times
in a single /daily-signal request (once per day of the week, plus the day-frame
and highlight passes).

The cheapest fix is not to make the request. This module is the one home for
that cache so main.py and the engine modules share a single copy — previously
the cache lived in main.py, which engine code cannot import without a cycle.

Safe to cache: dasha_periods is effectively immutable. Rows are written once at
chart creation and otherwise only by an explicit backfill/recompute. In-process
writers call invalidate(); the TTL bounds staleness for anything else (the
standalone backfill script runs out of process and cannot invalidate).

We hand back the RAW ROWS. Callers that assemble them into their own structure
must not mutate the list or the row dicts in place — see rows_for_chart.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Optional

_CACHE: dict = {}
_LOCK = threading.Lock()
TTL_SECONDS = float(os.getenv("DASHA_CACHE_TTL", "300"))

_PAGE = 1000
_MAX_PAGES = 20


def invalidate(chart_id: Optional[str] = None) -> None:
    """Drop cached rows. Call after ANY write to dasha_periods.
    With no chart_id, clears everything (used by bulk backfills)."""
    with _LOCK:
        if chart_id is None:
            _CACHE.clear()
        else:
            _CACHE.pop(str(chart_id), None)


def rows_for_chart(supabase_client, chart_id: str) -> list:
    """All dasha_periods rows for a chart, cached for TTL_SECONDS.

    Returns the cached list itself — treat it as READ-ONLY. Callers that need a
    mutable structure must build their own from it (main.get_dashas_for_chart
    rebuilds its dict per call for exactly this reason).
    """
    key = str(chart_id)
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and hit[0] > now:
            return hit[1]

    # [dasha-truncation 2026-07-21] Page rather than .limit(). Charts carry ~903
    # rows and `sequence` is NOT chronological, so a cap punched arbitrary HOLES
    # in the timeline rather than trimming its tail — one chart had a 59-day gap
    # sitting exactly over today.
    rows: list = []
    page = 0
    while True:
        res = (supabase_client.table("dasha_periods").select("*")
               .eq("chart_id", chart_id).order("sequence")
               .range(page * _PAGE, page * _PAGE + _PAGE - 1).execute())
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < _PAGE or page >= _MAX_PAGES:
            break
        page += 1

    # Never cache an empty result: a chart mid-creation (rows not inserted yet)
    # or a transient PostgREST failure would otherwise pin "this chart has no
    # dashas" for the whole TTL, which reads downstream as a chart with no
    # timeline at all.
    if rows:
        with _LOCK:
            _CACHE[key] = (now + TTL_SECONDS, rows)
    return rows


def active_vimsottari(supabase_client, chart_id: str, now_iso: str) -> list:
    """Currently-running vimsottari periods, innermost level last.

    Served from the cached rows — replaces a second round trip that asked
    PostgREST for the same thing with
        .eq("system","vimsottari").lte("start_date",now).gte("end_date",now)
        .order("level")
    Dates are ISO-8601 (YYYY-MM-DD...), so lexicographic comparison on the
    10-char prefix is exactly the ordering the database applies.
    """
    day = str(now_iso)[:10]
    out = []
    for r in rows_for_chart(supabase_client, chart_id):
        if (r.get("system") or "vimsottari") != "vimsottari":
            continue
        start = str(r.get("start_date") or "")[:10]
        end = str(r.get("end_date") or "")[:10]
        if start and end and start <= day <= end:
            out.append(r)
    out.sort(key=lambda r: (r.get("level") or 0))
    return out
