"""Per-route time budgets for GET requests.

A slow upstream used to leave the browser on "LOADING..." forever: Railway's log shows the duration but the client never got an answer. A GET that exceeds
its budget now returns a clear 504 JSON error ({"error": "timeout", "retry": true, ...}) and logs [TIMEOUT]; the page can show a retry instead of spinning.
Only GETs under /api/ are bounded; POSTs (Ask, LLM generation) are never cut off. Kill switch: env ANTAR_DEADLINES=off.
"""
import asyncio
import os
import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# (regex, seconds) — first match wins
_BUDGETS = [
    (re.compile(r"^/api/v1/chart/[^/]+/upcoming-themes$"), 30.0),        # LLM-generated on first call (~13 s), cached after
    (re.compile(r"^/api/v1/chart/[^/]+/(?:identity|overview|first-read|signature|arc|aligned-path|past-events|pattern|remedies|topics)$"), 10.0),
    (re.compile(r"^/api/v1/people/[^/]+$"), 8.0),
    (re.compile(r"^/api/v1/compatibility/session/[^/]+/agreement$"), 8.0),
    (re.compile(r"^/api/v1/compatibility/session/[^/]+$"), 12.0),
]
DEFAULT_BUDGET = 45.0                                                   # unlisted GETs (cold-start dailies can be slow): still ends in a clear error, never a hang
_UNBOUNDED = ("stream", "/sse", "events", "export", "download")


def budget_for(method: str, path: str):
    """Seconds allowed, or None when the request is not bounded."""
    if method != "GET" or not path.startswith("/api/"):
        return None
    if any(w in path for w in _UNBOUNDED):
        return None
    for rx, secs in _BUDGETS:
        if rx.match(path):
            return secs
    return DEFAULT_BUDGET


class DeadlineMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if os.environ.get("ANTAR_DEADLINES", "").lower() == "off":
            return await call_next(request)
        secs = budget_for(request.method, request.url.path)
        if secs is None:
            return await call_next(request)
        t0 = time.perf_counter()
        try:
            return await asyncio.wait_for(call_next(request), timeout=secs)
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] {request.method} {request.url.path} gave up after {secs:.0f}s (budget) — returned 504 so the client can retry")
            return JSONResponse(
                {"error": "timeout", "message": "This took too long. Please try again.", "retry": True,
                 "budget_s": secs, "path": request.url.path,
                 "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
                status_code=504, headers={"Retry-After": "2"})
