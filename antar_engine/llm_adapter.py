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
        return (r.content[0].text if r.content else "") or ""
    r = await _openai(prov).chat.completions.create(
        model=mdl, max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "system", "content": _flatten_system(system)}, *messages])
    return (r.choices[0].message.content or "") if r.choices else ""
