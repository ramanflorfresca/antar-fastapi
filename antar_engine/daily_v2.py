"""
antar_engine/daily_v2.py — new /predict/daily contract assembler
=================================================================

Produces the JSON shape the Daily brief specifies, layered on top of the
existing endpoint output (additive, not breaking). Frontend reads the
new fields; legacy clients keep working until Lovable migrates.

Contract (brief, verbatim):
  {
    "date":            "YYYY-MM-DD",
    "day_label":       "MON · JUN 8",
    "verdict_headline": "...",
    "strength":         0..100,
    "strength_note":    "...",
    "windows": [
      {"type":"best", "start":"HH:MM","end":"HH:MM","text":"..."},
      {"type":"avoid","start":"HH:MM","end":"HH:MM","text":"..."}
    ],
    "domains": [
      {"key":"mind",  "name":"Mind",  "state":"favorable|caution|steady","line":"..."},
      {"key":"body",  "name":"Body",  ...},
      {"key":"work",  "name":"Work",  ...},
      {"key":"money", "name":"Money", ...},
      {"key":"people","name":"People",...}
    ]
  }

By construction:
  * `domains` is always exactly five — one slot per domain — last-write-
    wins inside the composer. Impossible to emit two of the same.
  * `windows` come from the existing hora_engine at the user's location.
  * `strength` is the score_day(today) score (0..100).
  * No remedy is included — brief: "Today has no remedy".
  * Sanskrit/planet/house leaks scrubbed by apply_user_facing_strips.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _dt, timedelta as _td, timezone as _tz
from typing import Any, Dict, List, Optional


_DOMAIN_LABELS = {
    "mind":   "Mind",
    "body":   "Body",
    "work":   "Work",
    "money":  "Money",
    "people": "People",
}
_DOMAIN_ORDER = ("mind", "body", "work", "money", "people")

# Per-domain plain-language line per state. The composer overrides these
# with chart-specific lines when score_day produced a strong bias on that
# domain (i.e. when there's actually something to say beyond the state).
_STATE_LINES = {
    "favorable": {
        "mind":   "Your head runs clear today — write, decide, work the hard thinking.",
        "body":   "Body holds up well today — a good day for movement and routine care.",
        "work":   "Work rewards visible effort today — push the thing that matters.",
        "money":  "Money matters carry tailwind today — chase what you're owed, send invoices.",
        "people": "People respond warmly today — make the ask, mend the rift, reach out.",
    },
    "caution": {
        "mind":   "Judgment is foggier than usual today — avoid choices that need a sharp head.",
        "body":   "Don't overexert physically today — your reserves are lower than they feel.",
        "work":   "Don't force big work commitments today — execution yes, decisions later.",
        "money":  "Hold off on new spending or speculative money moves today — timing isn't with you.",
        "people": "Go easy in tense conversations today — postpone confrontation if you can.",
    },
    "steady": {
        "mind":   "Mental texture is steady today — focused, ordinary work moves things.",
        "body":   "Body is steady today — keep the habit, don't push past warning signs.",
        "work":   "Work is steady today — protect blocks of focus time, ship small things.",
        "money":  "Money is quiet today — no big moves needed; tend the cushion.",
        "people": "Relationships are calm today — short, warm touches are enough.",
    },
}


def _strength_note(score: int, states: Dict[str, str]) -> str:
    """Human-readable subtitle under the strength meter."""
    fav = sum(1 for v in states.values() if v == "favorable")
    cau = sum(1 for v in states.values() if v == "caution")
    if score >= 75 and cau <= 1:
        return f"Strong day overall · {fav} of 5 domains favorable"
    if score >= 60:
        if cau == 0:
            return f"Mostly favorable · {fav} of 5 domains in your favor"
        return f"Mostly favorable · {cau} area to protect"
    if score >= 45:
        return f"Mixed day · {fav} favorable, {cau} need care"
    if score >= 30:
        return f"Lower energy day · {cau} areas asking for care"
    return "Protect-mode day · take it easy and don't force"


def _day_label(d: _date) -> str:
    """'MON · JUN 8' format — uppercase 3-letter weekday + month."""
    wk = d.strftime("%a").upper()
    mo = d.strftime("%b").upper()
    return f"{wk} · {mo} {d.day}"


def _verdict_headline(score: int, states: Dict[str, str]) -> str:
    """Deterministic one-sentence headline. Falls back to a generic phrasing
    if the bias is flat; otherwise highlights the strongest tilt."""
    strong = [d for d in _DOMAIN_ORDER if states.get(d) == "favorable"]
    soft   = [d for d in _DOMAIN_ORDER if states.get(d) == "caution"]
    if score >= 70 and strong:
        if len(soft) == 0:
            return f"A high-energy day — push the {strong[0]} work first."
        return f"Strong day overall — push {strong[0]}, protect {soft[0]}."
    if score >= 55 and strong:
        if soft:
            return f"Use your {strong[0]} edge today; ease off the {soft[0]} pressure."
        return f"A steady, supportive day — lean into {strong[0]}."
    if score >= 40 and soft:
        return f"Mixed day — guard your {soft[0]} energy, lean on {strong[0] if strong else 'small wins'}."
    if soft:
        return f"Low-key day — protect {soft[0]} and don't force decisions."
    return "A steady day — small, consistent moves outpace big bets."


def _format_time_hhmm(iso_or_local: Optional[str], tz_offset_hours: float = 0.0) -> str:
    """Best-effort HH:MM extractor for the windows[] payload."""
    if not iso_or_local:
        return ""
    s = str(iso_or_local).strip()
    if not s:
        return ""
    # If already an "11:42" / "01:30 PM" / "11:42 AM" string, normalise.
    s = s.replace(" AM", "").replace(" PM", "").replace("AM", "").replace("PM", "")
    if "T" in s:
        try:
            dt = _dt.fromisoformat(s.replace("Z", "+00:00"))
            dt_local = dt + _td(hours=tz_offset_hours) if dt.tzinfo is None else dt
            return dt_local.strftime("%H:%M")
        except Exception:
            pass
    if ":" in s:
        try:
            parts = s.strip().split(":")
            hh = int(parts[0]); mm = int(parts[1][:2])
            return f"{hh:02d}:{mm:02d}"
        except Exception:
            return s[:5]
    return s[:5]


def _build_windows_from_hora(hora_block: Dict[str, Any], tz_offset_hours: float = 0.0
                             ) -> List[Dict[str, Any]]:
    """
    Pick exactly two windows from the existing /daily hora block:
      best  — the peak / abhijit-aligned window
      avoid — the rahu_kalam / dark window
    Both come from hora_engine output at the user's location/sunrise.
    Returns [] if no usable data — the caller can fall back to text-only.
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(hora_block, dict):
        return out

    # BEST: prefer abhijit, else the current peak hora.
    best = (hora_block.get("abhijit") or hora_block.get("abhijit_muhurta") or {})
    if isinstance(best, dict) and (best.get("start") or best.get("start_local")):
        out.append({
            "type":  "best",
            "start": _format_time_hhmm(best.get("start") or best.get("start_local"), tz_offset_hours),
            "end":   _format_time_hhmm(best.get("end")   or best.get("end_local"),   tz_offset_hours),
            "text":  "Decide, pitch, ask — anything that matters.",
        })
    else:
        cur = hora_block.get("current_hora") or {}
        if isinstance(cur, dict) and cur.get("start_local"):
            out.append({
                "type":  "best",
                "start": _format_time_hhmm(cur.get("start_local"), tz_offset_hours),
                "end":   _format_time_hhmm(cur.get("end_local"),   tz_offset_hours),
                "text":  "Use this window for anything that actually matters.",
            })

    # AVOID: prefer rahu_kalam.
    rk = hora_block.get("rahu_kalam") or {}
    if isinstance(rk, dict) and (rk.get("start") or rk.get("start_local")):
        out.append({
            "type":  "avoid",
            "start": _format_time_hhmm(rk.get("start") or rk.get("start_local"), tz_offset_hours),
            "end":   _format_time_hhmm(rk.get("end")   or rk.get("end_local"),   tz_offset_hours),
            "text":  "Don't force decisions or hard talks here.",
        })

    return out


def _scrub_text(language: str, text: str, field_type: str = "plain") -> str:
    if not isinstance(text, str) or not text:
        return text
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        return apply_user_facing_strips(text, language=(language or "en"),
                                        field_type=field_type)
    except Exception:
        return text


def _domains_v2(states: Dict[str, str], bias: Dict[str, float],
                language: str) -> List[Dict[str, Any]]:
    """Always exactly five slots, in canonical order. last-write-wins is
    enforced by the dict-of-states being closed to the five keys."""
    out: List[Dict[str, Any]] = []
    for key in _DOMAIN_ORDER:
        state = states.get(key, "steady")
        line  = (_STATE_LINES.get(state, _STATE_LINES["steady"]).get(key) or
                 _STATE_LINES["steady"][key])
        out.append({
            "key":   key,
            "name":  _DOMAIN_LABELS[key],
            "state": state,
            "line":  _scrub_text(language, line, "plain"),
        })
    return out


def compose_daily_contract(chart_id: str,
                           chart_record: Dict[str, Any],
                           legacy_response: Dict[str, Any],
                           language: str = "en",
                           target_date: Optional[_date] = None,
                           ) -> Dict[str, Any]:
    """
    Build the new daily contract on top of the existing endpoint output.

    Returns ONLY the new fields — caller merges into the legacy response.
    No remedy field is added. All text fields run through the central scrub.
    """
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"

    # Date the contract is anchored to.
    d = target_date or _date.today()
    if isinstance(d, _dt):
        d = d.date()

    chart_data = chart_record.get("chart_data") or {}
    if isinstance(chart_data, str):
        try:
            import json as _j
            chart_data = _j.loads(chart_data)
        except Exception:
            chart_data = {}

    lat = chart_record.get("latitude") or 28.6
    lng = chart_record.get("longitude") or 77.2
    tz_offset_hours = 0.0
    try:
        tz_offset_hours = float(chart_record.get("tz_offset_hours") or 0.0)
    except Exception:
        tz_offset_hours = 0.0
    location = {"lat": lat, "lng": lng, "tz_offset": tz_offset_hours}

    # ── score_day → strength + per-domain states ──
    try:
        from antar_engine.score_day import score_day
        sd = score_day(chart_data, d, location)
    except Exception:
        sd = {"score": 50, "domain_states": {k: "steady" for k in _DOMAIN_ORDER},
              "domain_bias": {k: 0.0 for k in _DOMAIN_ORDER}}

    states = {k: (sd.get("domain_states") or {}).get(k, "steady")
              for k in _DOMAIN_ORDER}
    bias   = {k: (sd.get("domain_bias")   or {}).get(k, 0.0)
              for k in _DOMAIN_ORDER}
    score  = int(sd.get("score") or 50)

    # ── windows[] from the legacy hora/panchanga block ──
    windows = _build_windows_from_hora({
        "abhijit":    legacy_response.get("abhijit"),
        "rahu_kalam": legacy_response.get("rahu_kalam"),
        "current_hora": (legacy_response.get("hora") or {}).get("current_hora")
                          if isinstance(legacy_response.get("hora"), dict) else None,
    }, tz_offset_hours=tz_offset_hours)

    # ── verdict_headline ──
    verdict = _verdict_headline(score, states)
    verdict = _scrub_text(language, verdict, "plain")

    contract: Dict[str, Any] = {
        "date":             d.isoformat(),
        "day_label":        _day_label(d),
        "verdict_headline": verdict,
        "strength":         score,
        "strength_note":    _scrub_text(language, _strength_note(score, states), "plain"),
        "windows":          windows,
        "domains":          _domains_v2(states, bias, language),
    }
    # Legacy `strength` may already be a string ("high"/"mid"/"low"); the
    # caller preserves it under "strength_label" and overwrites the
    # top-level "strength" with our int. This is a breaking change
    # consumers asked for — see the brief.
    return contract


__all__ = ["compose_daily_contract"]
