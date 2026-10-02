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
                        displayed_highlight: str, chandra_bala: str,
                        card: Optional[dict] = None) -> None:
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
    # [today-authority 2026-10-02] The card-level facts the Today screen shows
    # (band, windows, move, …) so /daily-week can reconcile its today entry to
    # them — see reconcile_week_today.
    if isinstance(card, dict):
        payload["card"] = {k: v for k, v in card.items() if v not in (None, "", [], {})}
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


# ── [today-authority 2026-10-02] /daily-week ↔ /daily-signal reconcile ───────
# The Today card is stitched from BOTH payloads: the band, move, day_turn and
# area list come from /daily-signal, while the headline (verdict_subline), the
# time dial (windows) and the do/avoid lists come from /daily-week's today
# entry. The two engines score the day independently, so live the card read
# "LIGHTER-TOUCH DAY" over "A friction day — …", "clearest window ~11:20 AM"
# beside a BEST 12:21–2:52 PM dial, and "Take the money move" beside "don't
# sign anything — the day's friction runs deep". /daily-signal is the
# authority for today (it runs the coherence passes), so the weekly entry is
# snapped to its committed card. Fail-open: no committed card → untouched.

import re as _re

_DAYTYPE_RE = _re.compile(
    r"\b(?:friction|heavy|lighter[- ]touch|lighter|light|steady|strong|quiet)\s+day\b", _re.I)
_BAND_PHRASE = {"friction": "friction day", "light": "lighter-touch day",
                "steady": "steady day"}
# avoid-lines that justify themselves with a friction/heavy-day claim
_FRICTION_CLAIM_RE = _re.compile(
    r"\bfriction\b|\bheavy day\b|\bday'?s? (?:pressure|resistance)\b", _re.I)


def snap_day_type(text: str, band: Optional[str]) -> str:
    """Make a headline's day-TYPE phrase agree with the band (EN only)."""
    want = _BAND_PHRASE.get((band or "").lower())
    if not text or not want:
        return text
    m = _DAYTYPE_RE.search(text)
    if not m or m.group(0).lower() == want:
        return text
    return text[:m.start()] + want + text[m.end():]


def _to_week_window(w: dict) -> Optional[dict]:
    if not isinstance(w, dict) or not w.get("start"):
        return None
    kind = (w.get("kind") or "").lower()
    out = {"start": w.get("start"), "end": w.get("end") or "",
           "text": w.get("text") or w.get("label") or ""}
    if kind == "avoid":
        out["kind"] = "avoid"
    elif kind == "best":
        out["type"] = "peak"
    else:
        return None
    return out


def _mins(t: str) -> Optional[int]:
    from datetime import datetime as _dt
    try:
        x = _dt.strptime(str(t).strip(), "%I:%M %p")
        return x.hour * 60 + x.minute
    except Exception:
        return None


def _overlaps(a: dict, b: dict) -> bool:
    a0, a1, b0, b1 = (_mins(a.get("start")), _mins(a.get("end")),
                      _mins(b.get("start")), _mins(b.get("end")))
    if None in (a0, a1, b0, b1):
        return False
    return a0 < b1 and b0 < a1


def reconcile_week_today(day: dict, committed: Optional[dict], language: str = "en") -> dict:
    """Snap /daily-week's TODAY entry to the committed /daily-signal card."""
    if not isinstance(day, dict) or not isinstance(committed, dict):
        return day
    card = committed.get("card") or {}
    if not card:
        return day
    same_lang = (card.get("language") or "en")[:2] == (language or "en")[:2]

    energy = card.get("day_energy")
    band = (energy or {}).get("key") if isinstance(energy, dict) else None
    if isinstance(energy, dict) and band:
        day["day_energy"] = energy
        day["is_friction_day"] = band == "friction"
        if isinstance(card.get("score"), (int, float)):
            day["score"] = card["score"]

    if band and band != "friction":
        # The weekly prose was written for ITS band; drop lines that argue
        # from a friction day the authority says this isn't.
        for k in ("evita_hoy", "haz_hoy"):
            if isinstance(day.get(k), list):
                kept = [x for x in day[k] if not (isinstance(x, str) and _FRICTION_CLAIM_RE.search(x))]
                if kept or k == "evita_hoy":
                    day[k] = kept

    if same_lang:
        hl = (committed.get("headline") or "").strip()
        sub = day.get("verdict_subline") or ""
        if hl and (not sub or (band and _DAYTYPE_RE.search(sub)
                               and snap_day_type(sub, band) != sub)):
            # Weekly headline contradicts the band → use the card's own headline.
            day["verdict_subline"] = hl
        if card.get("move"):
            day["move"] = card["move"]
        if card.get("day_turn"):
            day["day_turn"] = card["day_turn"]
        auth = [w for w in (_to_week_window(x) for x in (card.get("windows") or [])) if w]
        if auth:
            # ONE "best" on the dial: the authority's best/avoid, plus the weekly
            # connect/think windows that don't collide with them.
            rest = [w for w in (day.get("windows") or [])
                    if isinstance(w, dict)
                    and (w.get("type") or "").lower() not in ("peak", "")
                    and (w.get("kind") or "").lower() != "avoid"
                    and not any(_overlaps(w, a) for a in auth)]
            day["windows"] = sorted(auth + rest, key=lambda w: _mins(w.get("start")) or 0)
    return day
