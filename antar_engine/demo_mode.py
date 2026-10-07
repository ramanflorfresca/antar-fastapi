"""antar_engine/demo_mode.py — the public, read-only DEMO chart.

[demo-mode 2026-10-05] Apple review, testers and contractors need a way into the
product that is not a shared email+password. The demo is one dedicated chart
(`app_config.demo_chart_id`) that anyone can open with no session. This module is
the SAFETY half: what a request that touches the demo chart is allowed to do.

The backend has no per-user auth on `chart_id` (a chart id is a secret link), so a
public chart is only safe if the BACKEND refuses to let it be changed. Design:

  * a request that mentions the demo chart id (path, query or JSON body) is
    checked; any other request passes through untouched — real users are never
    affected, and nothing happens at all while no demo chart is configured;
  * GET is always allowed; PUT / PATCH / DELETE never are;
  * POST is DEFAULT-DENY with an allow-list of compute/read routes (Ask, the
    predict family, Prashna, places/astrocartography compute …). A new mutating
    route is therefore blocked for the demo automatically;
  * Ask-class routes are rate-limited per client IP per day (LLM cost / abuse);
  * a nightly job wipes what the demo created (history, outcomes, practice logs…)
    and restores the seeded life-facts.

Fail-open on config problems (no chart id → no guard), fail-closed on the
decision itself (unknown POST on the demo chart → 403).
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import date, timedelta
from typing import Any, Dict, Optional, Tuple

DEMO_KEY = "demo_chart_id"
BASELINE_KEY = "demo_chart_baseline"
ASK_PER_IP_PER_DAY_KEY = "demo_ask_per_ip_day"
DEFAULT_ASK_PER_IP_PER_DAY = 15

# POST routes that only compute / read for the chart they are given.
_ALLOW_EXACT = frozenset({
    "/api/v1/ask", "/api/v1/ask/evidence",
    "/api/v1/predict", "/api/v1/predict/daily", "/api/v1/predict/daily-week",
    "/api/v1/predict/monthly", "/api/v1/predict/yearly", "/api/v1/predict/dasha-cycle",
    "/api/v1/predict/monthly-briefing", "/api/v1/predict/year-attention",
    "/api/v1/predict/day-deep", "/api/v1/predict/daily-practice",
    "/api/v1/daily-signal", "/api/v1/prashna", "/api/v1/prashna/followup",
    "/api/v1/chakra", "/api/v1/chapter-arc", "/api/v1/proof-points",
    "/api/v1/timing/windows", "/api/v1/panchanga", "/api/v1/muhurta/best-times",
    "/api/v1/varshphal/annual", "/api/v1/transit-alerts", "/api/v1/career",
    "/api/v1/places/concern", "/api/v1/places/overall", "/api/v1/places/potential",
    "/api/v1/places/prescribe", "/api/v1/places/city", "/api/v1/places/compare",
    "/api/v1/astrocartography/best-cities", "/api/v1/astrocartography/city-reading",
    "/api/v1/astrocartography/recommend", "/api/v1/astrocartography/city",
    "/api/v1/daily-wisdom/chat", "/api/v1/support", "/api/v1/client-error",
    "/api/v1/auth/signout",
})

# Allowed POSTs that spend LLM money → rate-limited.
_ASK_CLASS = frozenset({
    "/api/v1/ask", "/api/v1/ask/evidence", "/api/v1/prashna", "/api/v1/prashna/followup",
    "/api/v1/daily-wisdom/chat",
})

_ALWAYS_OK_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

_CACHE: Dict[str, Any] = {"id": None, "at": 0.0}
_TTL = 30.0
_HITS: Dict[Tuple[str, str], int] = {}     # (ip, yyyy-mm-dd) → Asks (per worker)


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def demo_chart_id(supabase, *, force: bool = False) -> Optional[str]:
    """The configured demo chart id, or None. Cached ~30s; a read failure → None
    (no guard) rather than a broken request."""
    now = time.time()
    if not force and now - _CACHE["at"] < _TTL:
        return _CACHE["id"]
    val = None
    try:
        r = supabase.table("app_config").select("value").eq("key", DEMO_KEY).limit(1).execute()
        if r.data and r.data[0].get("value"):
            val = str(r.data[0]["value"]).strip().strip('"') or None
    except Exception:
        val = _CACHE["id"]          # keep the last known value on a read error
    _CACHE.update(id=val, at=now)
    return val


def is_demo_chart(chart_id) -> bool:
    """True if chart_id is the configured demo chart. Reads the cache only (no I/O): the
    guard middleware refreshes it on every request that mentions the demo chart, so by the
    time a handler asks, the value is current."""
    cid = _CACHE.get("id")
    return bool(cid) and str(chart_id or "").strip().lower() == str(cid).strip().lower()


def route_allowed(method: str, path: str) -> bool:
    m = (method or "").upper()
    if m in _ALWAYS_OK_METHODS:
        return True
    if m != "POST":
        return False                 # PUT / PATCH / DELETE never touch the demo chart
    return (path or "").rstrip("/") in _ALLOW_EXACT


def is_ask_class(path: str) -> bool:
    return (path or "").rstrip("/") in _ASK_CLASS


def rate_ok(ip: str, limit: int = DEFAULT_ASK_PER_IP_PER_DAY) -> bool:
    """Count one Ask-class call for this IP today; False once over the limit."""
    key = (ip or "unknown", _today())
    n = _HITS.get(key, 0)
    if n >= limit:
        return False
    if len(_HITS) > 5000:            # day rollover / long uptime: drop old days
        t = _today()
        for k in [k for k in _HITS if k[1] != t]:
            _HITS.pop(k, None)
    _HITS[key] = n + 1
    return True


def decide(method: str, path: str, mentions_demo: bool, ip: str,
           limit: int = DEFAULT_ASK_PER_IP_PER_DAY) -> Optional[Tuple[int, dict]]:
    """None → let the request through; else (status, json body)."""
    if not mentions_demo:
        return None
    if not route_allowed(method, path):
        return 403, {"demo": True, "code": "DEMO_READ_ONLY",
                     "detail": "The demo is read-only. Create your own chart to save this."}
    if (method or "").upper() == "POST" and is_ask_class(path) and not rate_ok(ip, limit):
        return 429, {"demo": True, "code": "DEMO_RATE_LIMIT",
                     "detail": "You've reached today's demo limit. Create your own chart to keep asking."}
    return None


class DemoGuardMiddleware:
    """Pure ASGI (so the request body can be inspected and replayed)."""

    def __init__(self, app, get_supabase, max_body: int = 1_000_000):
        self.app = app
        self._sb = get_supabase
        self._max = max_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        demo_id = None
        if path.startswith("/api/"):
            try:
                if time.time() - _CACHE["at"] < _TTL:
                    demo_id = _CACHE["id"]                    # fresh: no I/O at all
                else:       # a sync supabase call in an async def freezes the loop → thread
                    demo_id = await asyncio.to_thread(demo_chart_id, self._sb())
            except Exception:
                demo_id = _CACHE["id"]
        if not demo_id:
            return await self.app(scope, receive, send)

        needle = demo_id.encode()
        mentions = needle in path.encode() or needle in (scope.get("query_string") or b"")
        body = b""
        replay = receive
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            chunks, more, size = [], True, 0
            while more:
                msg = await receive()
                if msg["type"] != "http.request":
                    chunks.append(msg); break
                part = msg.get("body", b"") or b""
                size += len(part)
                chunks.append(msg)
                more = msg.get("more_body", False)
                if size > self._max:     # too big to be a normal call: stop reading, pass on
                    break
            body = b"".join(c.get("body", b"") for c in chunks if c["type"] == "http.request")
            if needle in body:
                mentions = True
            queue = list(chunks)

            async def replay():          # hand the buffered body to the app, then the rest
                if queue:
                    return queue.pop(0)
                return await receive()

        ip = ""
        for k, v in scope.get("headers", []):
            if k == b"x-forwarded-for":
                ip = v.decode("latin-1").split(",")[0].strip()
                break
        if not ip and scope.get("client"):
            ip = scope["client"][0]

        try:
            limit = DEFAULT_ASK_PER_IP_PER_DAY
            verdict = decide(method, path, mentions, ip, limit)
        except Exception:
            verdict = None
        if verdict is None:
            return await self.app(scope, replay, send)

        status, payload = verdict
        raw = json.dumps(payload).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(raw)).encode())]})
        await send({"type": "http.response.body", "body": raw})


# ── nightly reset ────────────────────────────────────────────────────────────
# What the demo (or Ask on the demo chart) creates. NOT the natal data, dasha
# periods or the warm caches — those are the product being demoed.
RESET_TABLES = (
    "conversations", "chat_messages", "prediction_claims", "saved_decisions", "ventures",
    "practice_log", "practice_completions", "daily_feedback", "life_arc_feedback",
    "user_correlations", "prediction_accuracy_marks", "verification_ratings",
    "reward_ledger", "prashna_log", "prashna_readings", "signature_question_log",
    "intent_classify_log", "nlu_log", "places_saved_cities", "user_alerts", "alert_log",
    "messaging_links", "device_tokens", "user_predictions",
)

# charts columns the Ask harvest / onboarding can change; restored from baseline
BASELINE_COLS = ("life_work", "life_relationship", "life_kids", "marital_status",
                 "children_status", "career_stage", "health_status", "financial_status",
                 "language", "language_preference", "current_city", "current_country")


# ── Seeded decisions for the demo ────────────────────────────────────────────
# [demo-decisions 2026-10-07] saved_decisions is in RESET_TABLES, so the nightly
# reset wipes whatever the demo created — correct, but it also means the
# Decisions tab would be empty for every reviewer who opens the demo. An empty
# tab is worse than a hidden one: it is the app's one non-horoscope feature
# showing nothing.
#
# Windows are computed RELATIVE TO TODAY at seed time, never hardcoded, so the
# list always shows one of each status (open / upcoming / closed) no matter when
# it is opened. A hardcoded month would quietly turn the whole list "closed".
DEMO_DECISIONS = (
    # (question, verdict, months_from_now_start, months_from_now_end)
    ("Is this the right time to change jobs?", "YES", 0, 2),
    ("Should I start the business this year?", "NOT_YET", 4, 7),
    ("Is this a good month to move cities?", "LIKELY", -3, -1),
)


def _month_window(offset_start: int, offset_end: int, today: Optional[date] = None):
    """First day of the start month → last day of the end month, offset in months."""
    t = today or date.today()

    def _shift(n: int) -> date:
        m = t.month - 1 + n
        return date(t.year + m // 12, m % 12 + 1, 1)

    start = _shift(offset_start)
    nxt = _shift(offset_end + 1)
    return start, nxt - timedelta(days=1)


def _label(start: date, end: date) -> str:
    a, b = start.strftime("%b %Y"), end.strftime("%b %Y")
    return a if a == b else f"{a} – {b}"


def seed_decisions(supabase, chart_id: str, today: Optional[date] = None) -> int:
    """Insert the demo's saved decisions. Returns how many landed. Never raises."""
    if not chart_id:
        return 0
    rows = []
    for q, verdict, o1, o2 in DEMO_DECISIONS:
        start, end = _month_window(o1, o2, today)
        rows.append({
            "chart_id": chart_id, "question": q, "verdict": verdict,
            "timing_label": _label(start, end),
            "window_start": start.isoformat(), "window_end": end.isoformat(),
            "language": "en",
            # no open_reminder_due_at: the demo must never queue a notification
            "open_reminder_due_at": None,
        })
    try:
        supabase.table("saved_decisions").insert(rows).execute()
        return len(rows)
    except Exception as e:
        print(f"[demo] seed_decisions failed (non-fatal): {str(e)[:120]}")
        return 0


def snapshot_baseline(supabase, chart_id: str) -> dict:
    row = supabase.table("charts").select(",".join(BASELINE_COLS)).eq("id", chart_id).limit(1).execute().data
    base = (row or [{}])[0]
    supabase.table("app_config").upsert(
        {"key": BASELINE_KEY, "value": json.dumps(base), "updated_by": "demo-seed"},
        on_conflict="key").execute()
    return base


def reset_demo(supabase) -> dict:
    """Wipe what the demo created and restore the seeded profile. Never raises."""
    out = {"chart_id": None, "cleared": {}, "restored": False, "errors": []}
    cid = demo_chart_id(supabase, force=True)
    if not cid:
        return out
    out["chart_id"] = cid
    for t in RESET_TABLES:
        try:
            supabase.table(t).delete().eq("chart_id", cid).execute()
            out["cleared"][t] = "ok"
        except Exception as e:           # a table without chart_id etc. — skip, don't stop
            out["errors"].append(f"{t}: {str(e)[:80]}")
    try:
        r = supabase.table("app_config").select("value").eq("key", BASELINE_KEY).limit(1).execute()
        if r.data and r.data[0].get("value"):
            base = json.loads(r.data[0]["value"])
            if isinstance(base, dict) and base:
                supabase.table("charts").update(base).eq("id", cid).execute()
                out["restored"] = True
    except Exception as e:
        out["errors"].append(f"baseline: {str(e)[:80]}")
    # saved_decisions was just wiped above; put the demo's own back, with windows
    # recomputed for today so the tab always shows open / upcoming / closed.
    try:
        out["decisions_seeded"] = seed_decisions(supabase, cid)
    except Exception as e:
        out["errors"].append(f"decisions: {str(e)[:80]}")
    return out
