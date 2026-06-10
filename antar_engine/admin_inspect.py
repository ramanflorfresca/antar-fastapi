"""
antar_engine/admin_inspect.py — read-only Prediction Inspector backend.

One entry point:

    await inspect_surface(chart_id, surface, language="en") -> dict

surface in {"today", "month", "year", "cycle"}.

Architecture: every surface already follows "Python computes, Claude
narrates". This module re-runs the SAME compute + narrate functions the
live surfaces call and captures (a) the deterministic raw bundle,
(b) the narrated user-facing output, (c) the exact system prompt sent to
the model, (d) model + latency. It never writes to production tables:

  * INSPECT_CTX is a request-scoped contextvar. main.py's LLM wrappers
    append every call (system_prompt/model/latency) to it, and main.py's
    cache-write sites skip writes while it is set ("strict no-write").
  * month runs through generate_monthly_deepdive() with a read-only
    Supabase proxy (writes become no-ops) and a recording Claude client,
    so antar_engine/monthly_deepdive.py needs no changes.

NOTE: plain_english.py is /predict-only — none of these four surfaces run
it, so "plain_english" is always None here (output_strips is the real
post-processor on these paths and is already applied inside them).

Surface → live pipeline inspected:
  today  -> get_daily_signal_endpoint (what POST /api/v1/predict/daily serves)
  month  -> generate_monthly_deepdive (what POST /api/v1/predict/monthly serves)
  year   -> predict_year_attention    (POST /api/v1/predict/year-attention)
  cycle  -> _life_arc_compute         (what GET /api/v1/life-arc serves)
"""

import contextvars
import time
from datetime import datetime, timezone

# Set ONLY by inspect_surface(). None == live traffic, all hooks no-op.
INSPECT_CTX: contextvars.ContextVar = contextvars.ContextVar(
    "antar_inspect_ctx", default=None
)

VALID_SURFACES = {"today", "month", "year", "cycle"}

# Per-surface marker that identifies the PRIMARY narration call when a
# surface makes more than one LLM call (e.g. cycle = phase summary +
# diagnostic; year may also capture upaay modernization).
_PRIMARY_HINT = {
    "today": "## LIVE DATA",
    "year": "## LIVE DATA",
    "cycle": "life phase analyst",
    "month": None,  # single call
}


# ── Read-only Supabase proxy (month path) ────────────────────────────────────

class _NoopResult:
    data = []


class _NoopQuery:
    """Absorbs any chained builder call after a blocked write."""

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return _NoopResult()


class _ReadOnlyTable:
    _BLOCKED = ("insert", "upsert", "update", "delete")

    def __init__(self, real_table, table_name, ctx):
        self._t = real_table
        self._name = table_name
        self._ctx = ctx

    def __getattr__(self, name):
        if name in self._BLOCKED:
            def _blocked(*_a, **_k):
                self._ctx["notes"].append(
                    f"blocked write: {self._name}.{name} (read-only proxy)"
                )
                return _NoopQuery()
            return _blocked
        return getattr(self._t, name)


class ReadOnlySupabase:
    """Pass-through Supabase client whose write verbs are no-ops."""

    def __init__(self, real, ctx):
        self._r = real
        self._ctx = ctx

    def table(self, name):
        return _ReadOnlyTable(self._r.table(name), name, self._ctx)

    def __getattr__(self, name):
        return getattr(self._r, name)


# ── Recording Claude client (month path) ─────────────────────────────────────

class _RecordingMessages:
    def __init__(self, real_messages, ctx):
        self._m = real_messages
        self._ctx = ctx

    async def create(self, **kwargs):
        t0 = time.monotonic()
        resp = await self._m.create(**kwargs)
        sys_ = kwargs.get("system", "")
        if isinstance(sys_, list):  # KV-cache system blocks
            sys_ = "".join(
                b.get("text", "") for b in sys_ if isinstance(b, dict)
            )
        user_prompt = ""
        for m in reversed(kwargs.get("messages") or []):
            if isinstance(m, dict) and m.get("role") == "user":
                c = m.get("content")
                user_prompt = c if isinstance(c, str) else str(c)
                break
        self._ctx["llm_calls"].append({
            "system_prompt": sys_ or "",
            "model": kwargs.get("model", ""),
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "user_prompt": user_prompt,
        })
        return resp


class RecordingClaude:
    def __init__(self, real, ctx):
        self._r = real
        self._ctx = ctx

    @property
    def messages(self):
        return _RecordingMessages(self._r.messages, self._ctx)

    def __getattr__(self, name):
        return getattr(self._r, name)


# ── Surface runners ──────────────────────────────────────────────────────────

async def _run_today(_m, chart_id, language, ctx):
    # Same coroutine POST /api/v1/predict/daily delegates to. Narration
    # cache read/write, today-signal commit and deep-read prewarm are all
    # skipped in main.py while INSPECT_CTX is set.
    narrated = await _m.get_daily_signal_endpoint(
        chart_id=chart_id, request={}, language=language, date=None,
    )
    ctx["notes"].append(
        "today: narration cache bypassed (forced fresh); today-signal "
        "commit + deep-read prewarm skipped"
    )
    ctx["notes"].append(
        "today: daily_signals_cache rows may refresh same-value (write "
        "lives inside daily_prediction_engine, untouched by design)"
    )
    return narrated


async def _run_year(_m, chart_id, language, ctx):
    narrated = await _m.predict_year_attention(
        {"chart_id": chart_id, "language": language}
    )
    ctx["notes"].append(
        "year: year_narration_cache read+write and upaay_cache write "
        "skipped (forced fresh narration)"
    )
    return narrated


async def _run_month(_m, chart_id, language, ctx):
    # Mirrors GET /api/v1/monthly-deepdive's input assembly (same
    # functions), then calls the SAME generator with a read-only Supabase
    # proxy + recording Claude client so nothing is cached.
    from antar_engine.monthly_deepdive import generate_monthly_deepdive

    chart_res = (
        _m.supabase.table("charts").select("*").eq("id", chart_id).execute()
    )
    if not chart_res.data:
        raise _m.HTTPException(status_code=404, detail="Chart not found")
    chart_record = chart_res.data[0]
    chart_data = chart_record.get("chart_data", {})

    lk_ctx = ""
    try:
        from antar_engine.lal_kitab_db import format_lk_context_from_stored
        lk_ctx = format_lk_context_from_stored(chart_record) or ""
    except Exception:
        pass

    _current_dasha = ""
    try:
        from datetime import date as _date
        _dr = (
            _m.supabase.table("dasha_periods")
            .select("planet_or_sign")
            .eq("chart_id", chart_id)
            .eq("system", "vimsottari")
            .eq("level", 1)
            .lte("start_date", str(_date.today()))
            .gte("end_date", str(_date.today()))
            .limit(1)
            .execute()
        )
        if _dr.data:
            _current_dasha = _dr.data[0].get("planet_or_sign", "")
    except Exception:
        pass

    _cc = _m.claude_client
    result = await generate_monthly_deepdive(
        chart_id=chart_id,
        chart_data=chart_data,
        dashas={},
        first_name=chart_record.get("first_name", ""),
        lagna=chart_record.get("lagna_sign", "")
        or chart_data.get("lagna", {}).get("sign", ""),
        moon_sign=chart_record.get("moon_sign", "")
        or chart_data.get("planets", {}).get("Moon", {}).get("sign", ""),
        current_dasha=_current_dasha,
        age=None,
        country_code=chart_record.get("current_country")
        or chart_record.get("country_code", ""),
        lk_context=lk_ctx,
        supabase=ReadOnlySupabase(_m.supabase, ctx),
        claude_client=RecordingClaude(_cc, ctx) if _cc else _cc,
        force_refresh=True,
        language=language,
        birth_date=chart_record.get("birth_date", ""),
        lk_data=_m._safe_jsonb(chart_record.get("lal_kitab_data")),
    )
    # The deterministic month bundle IS the deepdive context block —
    # captured verbatim as the user message of the recorded call.
    if ctx["llm_calls"]:
        ctx["raw"]["deepdive_context"] = ctx["llm_calls"][0].get(
            "user_prompt", ""
        )
    ctx["notes"].append(
        "month: monthly_deepdives cache bypassed via read-only proxy "
        "(forced fresh recompute)"
    )
    ctx["notes"].append(
        "month: deterministic bundle is the prose context block "
        "(_build_deepdive_context) — see raw.deepdive_context"
    )
    ctx["notes"].append(
        "month: Layer-2 highlights (deterministic, added by the live "
        "handler after the deepdive) are not re-run here"
    )
    return result


async def _run_cycle(_m, chart_id, language, ctx):
    # Mirrors get_life_arc's foreground prefetch, then calls the same
    # compute coroutine synchronously (no generating/poll dance). The
    # life_arc_cache upsert inside _life_arc_compute is skipped while
    # INSPECT_CTX is set.
    from antar_engine.life_arc.signatures import get_library_version

    chart_res = (
        _m.supabase.table("charts").select("*").eq("id", chart_id).execute()
    )
    if not chart_res.data:
        raise _m.HTTPException(status_code=404, detail="Chart not found")
    chart_record = chart_res.data[0]
    chart_data = _m._safe_jsonb(chart_record.get("chart_data"))
    if not chart_data:
        raise _m.HTTPException(status_code=400, detail="Chart has no chart_data")

    narrated = await _m._life_arc_compute(
        chart_id, 12, language, chart_record, chart_data,
        get_library_version(),
    )
    ctx["notes"].append(
        "cycle: life_arc_cache write skipped; computed synchronously "
        "(forced fresh recompute)"
    )
    ctx["notes"].append(
        "cycle: two narration calls (phase summary + diagnostic) — both "
        "in llm_calls; system_prompt holds the phase-summary call"
    )
    return narrated


_RUNNERS = {
    "today": _run_today,
    "month": _run_month,
    "year": _run_year,
    "cycle": _run_cycle,
}


def _pick_primary(surface, calls):
    hint = _PRIMARY_HINT.get(surface)
    if hint:
        for c in calls:
            if hint in (c.get("system_prompt") or ""):
                return c
    return calls[0] if calls else None


# ── Entry point ──────────────────────────────────────────────────────────────

async def inspect_surface(chart_id: str, surface: str, language: str = "en") -> dict:
    """
    Re-run compute + narrate for one surface and return raw bundle,
    narrated output, exact system prompt, model, latency. Pure
    read/compute — never mutates DB state (see module docstring).
    """
    if surface not in VALID_SURFACES:
        raise ValueError(
            "surface must be one of: today, month, year, cycle"
        )

    import main as _m  # deferred — main is fully imported by request time

    t0 = time.monotonic()
    ctx = {
        "no_write": True,
        "llm_calls": [],
        "raw": {},
        "notes": ["forced fresh recompute", "strict no-write: production caches untouched"],
    }
    token = INSPECT_CTX.set(ctx)
    try:
        narrated = await _RUNNERS[surface](_m, chart_id, language, ctx)
    finally:
        INSPECT_CTX.reset(token)

    primary = _pick_primary(surface, ctx["llm_calls"])
    if not ctx["llm_calls"]:
        ctx["notes"].append(
            "no LLM call captured — surface served template/fallback text "
            "(e.g. quiet day) or narration was skipped; raw vs narrated "
            "still valid"
        )

    return {
        "surface": surface,
        "chart_id": chart_id,
        "language": language,
        "raw": ctx["raw"],
        "narrated": narrated,
        "plain_english": None,  # /predict-only post-processor; not on these 4 surfaces
        "system_prompt": (primary or {}).get("system_prompt", ""),
        "model": (primary or {}).get("model", ""),
        "latency_ms": int((time.monotonic() - t0) * 1000),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_calls": ctx["llm_calls"],
        "notes": ctx["notes"],
    }
