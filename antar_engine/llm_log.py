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


def record_fallback(sb, *, endpoint, from_model="", to_provider="", reason=""):
    """[P0 observability 2026-09-05] Record a silent LLM fallback (e.g.
    Claude->DeepSeek) so it is VISIBLE in llm_call_log AND fires an alert.
    Without this a fallback shows only as a *drop* in Claude volume — never as
    an error — which is exactly how the temperature outage stayed invisible."""
    try:
        log_llm_call(sb, endpoint=f"FALLBACK:{endpoint}", model=from_model,
                     success=False, error=f"fell back to {to_provider}: {reason}")
    except Exception:
        pass
    try:
        from antar_engine.alerting import alert
        alert(f"llm_fallback:{to_provider}",
              f"LLM fell back to {to_provider} at {endpoint} (from {from_model or 'claude'})",
              level="error", detail=reason)
    except Exception:
        pass


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
        # [sdk-compat 2026-09-04] The pinned anthropic SDK is unpinned
        # (>=0.40.0), so a redeploy can pull a version that rejects a kwarg
        # the code passes (observed globally: "AsyncMessages.create() got an
        # unexpected keyword argument 'temperature'"), which silently sent
        # EVERY Claude call to the DeepSeek fallback. Retry once without the
        # rejected kwarg so Claude keeps working until the SDK is pinned.
        async def _call():
            return await orig(*args, **kwargs)
        try:
            resp = await _call()
        except TypeError as _te:
            _m = str(_te)
            import re as _re_kw
            _mm = _re_kw.search(r"unexpected keyword argument '([^']+)'", _m)
            if _mm and _mm.group(1) in kwargs:
                _dropped = _mm.group(1)
                kwargs.pop(_dropped, None)
                try:
                    print(f"[llm-log] SDK rejected '{_dropped}' — retrying without it (model={model})")
                except Exception:
                    pass
                # The retry below succeeds and would otherwise log as success,
                # masking the exact failure mode that caused the outage. Alert
                # so an SDK/kwarg regression is never silent again.
                try:
                    from antar_engine.alerting import alert
                    alert("llm_sdk_kwarg_rejected",
                          f"Anthropic SDK rejected '{_dropped}' (model={model}) — retried without it. "
                          f"Likely an unpinned/upgraded SDK; verify requirements pin.",
                          level="error")
                except Exception:
                    pass
                try:
                    resp = await orig(*args, **kwargs)
                except Exception as e:
                    log_llm_call(_sb(sb_getter), endpoint=endpoint, model=model,
                                 success=False, error=e,
                                 duration_ms=int((time.monotonic() - t0) * 1000))
                    raise
            else:
                log_llm_call(_sb(sb_getter), endpoint=endpoint, model=model,
                             success=False, error=_te,
                             duration_ms=int((time.monotonic() - t0) * 1000))
                raise
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
