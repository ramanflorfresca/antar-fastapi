"""
antar_engine/today_signal.py

ONE committed day-signal per chart per local date.

The Today engine (today_highlight.select_today_highlight) makes the day's
committed selection: lead domain(s), direction, strength, the headline/
highlight the user actually SAW (post-narration), the hora windows, and the
BODY state line (chandra-bala model). This module persists that selection so
every other surface — the Deep Read first — reads the SAME snapshot instead
of re-deriving its own. That is the cross-surface no-drift invariant.

Storage: today_narration_cache with a language-sentinel row. The table
already exists (Today v2 Part 6) and is keyed (chart_id, narration_date,
language), so no schema migration is needed. Fail-open everywhere: a missing
table or row simply means the Deep Read proceeds without the committed block.
"""
from __future__ import annotations

import json
from typing import Optional

# NOTE: today_narration_cache.language is VARCHAR(5) — the sentinel must fit
# ("engine" was 6 chars and made every commit upsert fail silently).
_SENTINEL_LANG = "sig"

# Today SELECTABLE domains -> Deep Read theme keys
DOMAIN_TO_THEME = {
    "money": "money",
    "work": "work",
    "relationships": "relationships",
    "body": "body",
    "mind": "inner",
}


def body_state_from_chandra(chandra: str) -> str:
    s = (chandra or "").strip().lower()
    if s in ("weak", "low", "poor"):
        return "low"
    if s in ("strong", "high", "excellent"):
        return "high"
    return "even"


def commit_today_signal(supabase, chart_id: str, date_str: str, *,
                        engine: dict, displayed_headline: str,
                        displayed_highlight: str, chandra_bala: str) -> None:
    """Upsert the committed selection. `engine` is select_today_highlight's
    output; displayed_* are the FINAL texts after the narration layer (what
    the user actually saw on the Today card)."""
    try:
        from antar_engine.highlight_templates import body_from_chandra
        body_text = body_from_chandra(chandra_bala)
    except Exception:
        body_text = ""
    payload = {
        "kind": "today_signal_v1",
        "highlight_domains": list(engine.get("highlight_domains") or []),
        "direction": engine.get("direction"),
        "strength": engine.get("strength"),
        "headline": displayed_headline or engine.get("headline") or "",
        "highlight": displayed_highlight or engine.get("highlight") or "",
        "hora": engine.get("todays_move") or engine.get("hora") or {},
        "body_text": body_text,
        "body_state": body_state_from_chandra(chandra_bala),
    }
    try:
        supabase.table("today_narration_cache").upsert({
            "chart_id": chart_id,
            "narration_date": date_str,
            "language": _SENTINEL_LANG,
            "payload": payload,
        }, on_conflict="chart_id,narration_date,language").execute()
    except Exception as e:
        print(f"[today-signal] commit skipped (table missing?): {e}")


def read_today_signal(supabase, chart_id: str, date_str: str) -> Optional[dict]:
    """The committed selection for (chart, local date), or None."""
    try:
        res = supabase.table("today_narration_cache").select("payload") \
            .eq("chart_id", chart_id).eq("narration_date", date_str) \
            .eq("language", _SENTINEL_LANG).limit(1).execute()
        if not res.data:
            return None
        p = res.data[0].get("payload")
        if isinstance(p, str):
            try:
                p = json.loads(p)
            except Exception:
                return None
        if isinstance(p, dict) and p.get("kind") == "today_signal_v1":
            return p
        return None
    except Exception as e:
        print(f"[today-signal] read skipped: {e}")
        return None
