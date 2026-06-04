"""
antar_engine/llm_log.py

Lightweight LLM call logging for the admin dashboard (llm_call_log table).
wrap_claude_client() monkey-wraps client.messages.create so EVERY call made
through that client is recorded: endpoint (calling module:function, derived
from the stack), model, token usage, success/failure, duration. Fail-open:
a missing table or any insert error never touches the answer path.
"""
from __future__ import annotations

import inspect
import os
import time


def _sb(sb_getter):
    try:
        if sb_getter is not None:
            return sb_getter()
        import main as _m  # resolved at call time; main is loaded in prod
        return getattr(_m, "supabase", None)
    except Exception:
        return None


def log_llm_call(sb, *, endpoint, model="", success=True, error=None,
                 input_tokens=0, output_tokens=0, cache_read_tokens=0,
                 duration_ms=0, chart_id=None, language=None):
    if sb is None:
        return
    try:
        sb.table("llm_call_log").insert({
            "endpoint": (endpoint or "unknown")[:120],
            "model": (model or "")[:80],
            "success": bool(success),
            "error": (str(error)[:300] if error else None),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "cache_read_tokens": int(cache_read_tokens or 0),
            "duration_ms": int(duration_ms or 0),
            "chart_id": chart_id,
            "language": (language or None),
        }).execute()
    except Exception as e:
        print(f"[llm-log] insert skipped (table missing?): {e}")


def wrap_claude_client(client, sb_getter=None):
    """Wrap client.messages.create with logging. Idempotent; fail-open."""
    if client is None:
        return client
    try:
        if getattr(client, "_antar_llm_log_wrapped", False):
            return client
        orig = client.messages.create
    except Exception:
        return client

    async def _create_logged(*args, **kwargs):
        t0 = time.monotonic()
        endpoint = "unknown"
        try:
            for fr in inspect.stack()[1:8]:
                fn = fr.filename or ""
                base = os.path.basename(fn)
                if base == "llm_log.py" or "anthropic" in fn:
                    continue
                endpoint = f"{base.rsplit('.', 1)[0]}:{fr.function}"
                break
        except Exception:
            pass
        model = str(kwargs.get("model") or "")
        try:
            resp = await orig(*args, **kwargs)
        except Exception as e:
            log_llm_call(_sb(sb_getter), endpoint=endpoint, model=model,
                         success=False, error=e,
                         duration_ms=int((time.monotonic() - t0) * 1000))
            raise
        try:
            u = getattr(resp, "usage", None)
            log_llm_call(
                _sb(sb_getter), endpoint=endpoint, model=model, success=True,
                input_tokens=getattr(u, "input_tokens", 0) or 0,
                output_tokens=getattr(u, "output_tokens", 0) or 0,
                cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception:
            pass
        return resp

    try:
        client.messages.create = _create_logged
        client._antar_llm_log_wrapped = True
    except Exception as e:
        print(f"[llm-log] wrap failed (client stays unlogged): {e}")
    return client
