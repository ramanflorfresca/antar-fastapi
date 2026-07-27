"""
antar_engine/app_config.py

[runtime-config 2026-07-27] Backend configuration the admin panel can change at
RUNTIME — no redeploy. Key/value, stored in the `app_config` table (see
Antar.world/APP_CONFIG.sql), read through a short in-process cache so a change in
the panel takes effect within seconds across all workers.

Fail-safe by contract: if the table is missing or a read fails, every getter
returns its hard default. Config can tune behaviour; it can never break the app
by being absent. Only keys in ALLOWED_KEYS are settable from the panel, each
validated, so a typo can't wedge production.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict

# key -> (default, kind, choices|None, help)
ALLOWED_KEYS: Dict[str, dict] = {
    "claude_model": {
        "default": "claude-sonnet-4-6", "kind": "str",
        "choices": ["claude-sonnet-4-6", "claude-opus-4-8",
                    "claude-haiku-4-5-20251001"],
        "help": "Model for the central call_llm_claude path (Ask/predict prose).",
    },
    "llm_provider": {
        "default": "anthropic", "kind": "str",
        "choices": ["anthropic", "deepseek", "kimi"],
        "help": "Provider for the call_llm path (Ask fallback + DKP). NOTE: the "
                "daily/predict engines still call Claude directly — see the "
                "LLM-adapter migration before this switches everything.",
    },
    "daily_db_cache": {
        "default": "on", "kind": "bool", "choices": ["on", "off"],
        "help": "Shared daily-surface DB cache (L2). Kill switch.",
    },
    "narration_audit_strict": {
        "default": "off", "kind": "bool", "choices": ["on", "off"],
        "help": "If on, a jargon/broken/incoherent daily card is regenerated "
                "harder before shipping (future hook).",
    },
}

_CACHE: Dict[str, Any] = {}
_CACHE_AT = 0.0
_TTL = 20.0  # seconds — a panel change lands within this window
_SB = None


def _sb(supabase):
    """Use the passed client, else a lazily-created one from env — so engine code
    with no supabase handle (e.g. the daily generator) can still read config."""
    global _SB
    if supabase is not None:
        return supabase
    if _SB is None:
        from supabase import create_client
        _SB = create_client(
            os.environ["SUPABASE_URL"],
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
    return _SB


def _load(supabase) -> Dict[str, str]:
    global _CACHE, _CACHE_AT
    now = time.monotonic()
    if _CACHE and (now - _CACHE_AT) < _TTL:
        return _CACHE
    out: Dict[str, str] = {}
    try:
        rows = _sb(supabase).table("app_config").select("key,value").execute().data or []
        out = {r["key"]: r["value"] for r in rows if r.get("key")}
    except Exception:
        out = {}  # table missing / read failed -> defaults only
    _CACHE, _CACHE_AT = out, now
    return out


def get(supabase, key: str, default: Any = None) -> Any:
    """Config value for `key`: DB override if present, else the registered
    default, else the passed default. Never raises."""
    spec = ALLOWED_KEYS.get(key, {})
    fallback = spec.get("default", default)
    try:
        v = _load(supabase).get(key)
        return v if v is not None else fallback
    except Exception:
        return fallback


def get_bool(supabase, key: str, default: bool = False) -> bool:
    v = str(get(supabase, key, "on" if default else "off")).strip().lower()
    return v in ("on", "true", "1", "yes")


def all_config(supabase) -> Dict[str, dict]:
    """Merged view for the panel: each key with its effective value, whether it
    is overridden, and its spec (choices/help)."""
    overrides = _load(supabase)
    out = {}
    for key, spec in ALLOWED_KEYS.items():
        out[key] = {
            "value": overrides.get(key, spec["default"]),
            "default": spec["default"],
            "overridden": key in overrides,
            "kind": spec["kind"],
            "choices": spec.get("choices"),
            "help": spec.get("help", ""),
        }
    return out


def set_value(supabase, key: str, value: str, by: str = "") -> dict:
    """Validate + persist one config key. Returns {ok, error?}. Busts the cache
    so the change is live within the next read."""
    global _CACHE_AT
    spec = ALLOWED_KEYS.get(key)
    if not spec:
        return {"ok": False, "error": f"unknown key '{key}'"}
    value = str(value).strip()
    choices = spec.get("choices")
    if choices and value not in choices:
        return {"ok": False, "error": f"'{value}' not in {choices}"}
    if spec["kind"] == "bool" and value not in ("on", "off"):
        return {"ok": False, "error": "bool keys must be 'on' or 'off'"}
    try:
        from datetime import datetime, timezone
        supabase.table("app_config").upsert({
            "key": key, "value": value, "updated_by": by,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="key").execute()
    except Exception as e:
        return {"ok": False, "error": f"write failed: {str(e)[:120]}"}
    _CACHE_AT = 0.0  # force reload on next get
    return {"ok": True, "key": key, "value": value}
