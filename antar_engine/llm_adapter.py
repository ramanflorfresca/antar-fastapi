"""
antar_engine/llm_adapter.py

[llm-adapter 2026-07-27] One call path for every provider, selected from
app_config at runtime. This is what makes the admin panel's `llm_provider`
actually govern the brain, not just the fallback path.

Providers:
  anthropic  — Claude, PRESERVING the KV-cache system-block split + prompt-
               caching header the engines rely on. Behaviour-identical to the
               direct calls it replaces, so with the default provider nothing
               changes in production.
  deepseek   — OpenAI-compatible (api.deepseek.com).
  kimi       — Moonshot, OpenAI-compatible (api.moonshot.ai/v1).

Design guarantees:
  * anthropic is the default; a config/read problem falls back to anthropic.
  * a str `system` is split at `## LIVE DATA` for KV caching exactly as before;
    a pre-built block list is passed through untouched.
  * for the OpenAI-shape providers the system blocks are flattened to one string
    and prepended as the system message (they have no block/cache concept).
  * returns plain text; the caller is unchanged regardless of provider.
"""
from __future__ import annotations

import os
from typing import Any, List, Optional

_clients: dict = {}

# [forced-provider 2026-07-27] A context override so the admin compare view can
# force a provider for a WHOLE surface generation (monthly/life-arc make many
# call_llm_claude calls; threading a param through all of them is impractical).
# resolve() honors this first. Always cleared in a finally by the caller.
import contextvars as _cv
_FORCED = _cv.ContextVar("antar_forced_provider", default=None)


def set_forced_provider(provider):
    """Force a provider for everything generated in this context; returns a token
    to reset. Pass None to clear."""
    return _FORCED.set((provider or "").lower() or None)


# [usage-meter 2026-07-27] Token accounting for the admin Compare cost view.
# Metering is OFF unless reset_usage() has been called in this async context —
# then every LLM response (adapter here + the two direct-Anthropic sites in
# main.py) accrues into a task-local counter. Cost is computed from _PRICING.
_USAGE = _cv.ContextVar("antar_llm_usage", default=None)

# USD per 1,000,000 tokens (input, output). ESTIMATES — update as prices move.
_PRICING = {
    "anthropic": (3.00, 15.00),   # Claude Sonnet class
    "deepseek":  (0.27, 1.10),    # deepseek-chat
    "kimi":      (0.60, 2.50),    # moonshot / kimi (approx)
}


def reset_usage():
    """Start metering for this context (call before a metered generation)."""
    _USAGE.set({"input": 0, "output": 0, "cached": 0, "calls": 0})


def get_usage() -> dict:
    return dict(_USAGE.get() or {"input": 0, "output": 0, "cached": 0, "calls": 0})


def accrue_usage(input_tokens=0, output_tokens=0, cached_tokens=0):
    """Add one call's tokens to the active meter (no-op if metering is off)."""
    u = _USAGE.get()
    if u is None:
        return
    try:
        u["input"] += int(input_tokens or 0)
        u["output"] += int(output_tokens or 0)
        u["cached"] += int(cached_tokens or 0)
        u["calls"] += 1
    except Exception:
        pass


def usage_cost(provider: str, usage: dict) -> float:
    """USD cost for a usage dict under a provider's pricing. Cached-read input
    is billed at ~10% (Anthropic prompt-cache) to keep the estimate honest."""
    ppm_in, ppm_out = _PRICING.get((provider or "").lower(), _PRICING["anthropic"])
    billable_in = max(0, int(usage.get("input", 0)) - int(usage.get("cached", 0)))
    cost = (billable_in / 1e6) * ppm_in
    cost += (int(usage.get("cached", 0)) / 1e6) * ppm_in * 0.1
    cost += (int(usage.get("output", 0)) / 1e6) * ppm_out
    return round(cost, 6)


def reset_forced_provider(token):
    try:
        _FORCED.reset(token)
    except Exception:
        pass

_PROVIDER_DEFAULT_MODEL = {
    "anthropic": "claude-sonnet-4-6",
    "deepseek":  "deepseek-chat",
    "kimi":      "moonshot-v1-32k",
}
_KV_SPLIT = "## LIVE DATA"


def _anthropic():
    if "anthropic" not in _clients:
        from anthropic import AsyncAnthropic
        _clients["anthropic"] = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _clients["anthropic"]


def _openai(kind: str):
    if kind not in _clients:
        from openai import AsyncOpenAI
        if kind == "deepseek":
            _clients[kind] = AsyncOpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        else:  # kimi / moonshot
            _clients[kind] = AsyncOpenAI(
                api_key=os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY"),
                base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1"))
    return _clients[kind]


def _flatten_system(system) -> str:
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        out = []
        for b in system:
            if isinstance(b, dict):
                out.append(b.get("text", ""))
            elif isinstance(b, str):
                out.append(b)
        return "\n\n".join(p for p in out if p)
    return ""


def _anthropic_system_blocks(system, cache: bool):
    """Reproduce the engines' KV-cache split exactly."""
    if isinstance(system, list):
        return system                      # already blocks — passthrough
    if not isinstance(system, str) or not system:
        return system or ""
    if not cache:
        return system
    if _KV_SPLIT in system:
        static, dyn = system.split(_KV_SPLIT, 1)
        return [
            {"type": "text", "text": static, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": _KV_SPLIT + dyn},
        ]
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def resolve(supabase=None, provider: Optional[str] = None, model: Optional[str] = None):
    """(provider, model) from explicit args → app_config → anthropic defaults."""
    prov = (provider or "").lower()
    if not prov:
        forced = _FORCED.get()
        if forced:
            prov = forced
    if not prov and supabase is not None:
        try:
            from antar_engine import app_config
            prov = (app_config.get(supabase, "llm_provider", "anthropic") or "anthropic").lower()
        except Exception:
            prov = "anthropic"
    prov = prov if prov in _PROVIDER_DEFAULT_MODEL else "anthropic"
    if not model and supabase is not None:
        try:
            from antar_engine import app_config
            if prov == "anthropic":
                model = app_config.get(supabase, "claude_model", None)
            else:
                model = app_config.get(supabase, f"{prov}_model", None)
        except Exception:
            model = None
    model = model or _PROVIDER_DEFAULT_MODEL[prov]
    return prov, model


async def complete(*, system, messages, max_tokens: int = 1200,
                   temperature: float = 0.3, cache: bool = True,
                   supabase=None, provider: Optional[str] = None,
                   model: Optional[str] = None) -> str:
    """Provider-agnostic completion. Returns text. Anthropic path is
    behaviour-identical to the direct calls; OpenAI-shape providers flatten the
    system + call chat.completions."""
    prov, mdl = resolve(supabase, provider, model)
    if prov == "anthropic":
        r = await _anthropic().messages.create(
            model=mdl, max_tokens=max_tokens, temperature=temperature,
            system=_anthropic_system_blocks(system, cache), messages=messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"})
        try:
            _u = getattr(r, "usage", None)
            if _u is not None:
                accrue_usage(getattr(_u, "input_tokens", 0),
                             getattr(_u, "output_tokens", 0),
                             getattr(_u, "cache_read_input_tokens", 0) or 0)
        except Exception:
            pass
        return (r.content[0].text if r.content else "") or ""
    r = await _openai(prov).chat.completions.create(
        model=mdl, max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "system", "content": _flatten_system(system)}, *messages])
    try:
        _u = getattr(r, "usage", None)
        if _u is not None:
            accrue_usage(getattr(_u, "prompt_tokens", 0),
                         getattr(_u, "completion_tokens", 0), 0)
    except Exception:
        pass
    return (r.choices[0].message.content or "") if r.choices else ""
