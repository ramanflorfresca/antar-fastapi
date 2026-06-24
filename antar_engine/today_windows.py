"""Deterministic Today timing-window builder.

Problem this solves
-------------------
The /daily-signal `windows[]` array used to be authored entirely by the
LLM (schema: type ∈ connection|peak|reflection, free start/end times).
That surface had two defects:

  1. No dedup — the model could emit two windows with the SAME time range
     (e.g. 11:00 AM–12:00 PM appearing twice).
  2. No best-vs-avoid axis — every row was a "positive" type, so the
     frontend rendered them all as a single "BEST WINDOW" label. There
     was no steer-clear window at all.

THIS MONTH does it right by being deterministic: best window comes from
abhijit muhurta, the steer-clear window from rahu kalam (see
highlight_composer._build_today). This module ports that pattern onto
Today: it builds a small set of DISTINCT, de-duplicated windows, each
tagged with an explicit `kind` ("best" | "avoid" | "supporting") and a
display `label`, so the best/steer-clear distinction is unambiguous.

The builder NEVER raises — on any parse failure it degrades to the
de-duplicated LLM windows so the card is never empty.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# en-dash, em-dash, or hyphen, with optional surrounding space
_DASH = re.compile(r"\s*[–—\-]\s*")
_TIME = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*$")

# Minimum minutes a best window must retain after overlap-trimming to be
# worth showing. Below this it is dropped (a 2-minute "best window" is noise).
_MIN_BEST_SPAN = 5


def _parse_time(s: str) -> Optional[int]:
    """'H:MM AM/PM' -> minutes since midnight, else None."""
    m = _TIME.match(s or "")
    if not m:
        return None
    h = int(m.group(1)) % 12
    if m.group(3).lower() == "pm":
        h += 12
    return h * 60 + int(m.group(2))


def _fmt(mins: int) -> str:
    """minutes since midnight -> 'H:MM AM/PM'."""
    mins %= 24 * 60
    h, m = divmod(mins, 60)
    ap = "AM" if h < 12 else "PM"
    return f"{(h % 12) or 12}:{m:02d} {ap}"


def _parse_range(s: str) -> Optional[Tuple[int, int, str, str]]:
    """'H:MM AM/PM – H:MM AM/PM' -> (start_min, end_min, start_str, end_str).

    end_min is normalized to be > start_min for windows that cross
    midnight (e.g. 11:46 PM – 12:34 AM)."""
    if not s or not isinstance(s, str):
        return None
    parts = _DASH.split(s.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    a, b = _parse_time(parts[0]), _parse_time(parts[1])
    if a is None or b is None:
        return None
    if b <= a:
        b += 24 * 60  # crosses midnight
    return (a, b, parts[0].strip(), parts[1].strip())


def _overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def _key(start_min: int, end_min: int) -> Tuple[int, int]:
    """Dedup key — round to 5 minutes so near-identical ranges collapse."""
    return (round(start_min / 5) * 5, round(end_min / 5) * 5)


def build_today_windows(
    abhijit: str,
    rahu_kalam: str,
    llm_windows: Optional[List[Dict[str, Any]]] = None,
    language: str = "en",
) -> List[Dict[str, Any]]:
    """Return a small, de-duplicated, distinctly-labeled window list.

    Order: best (abhijit) → steer-clear (rahu kalam) → up to 2 supporting
    LLM windows that don't overlap the deterministic pair or each other.
    """
    is_es = (language or "en").lower().startswith("es")
    out: List[Dict[str, Any]] = []
    seen: set = set()

    best = _parse_range(abhijit)
    avoid = _parse_range(rahu_kalam)

    avoid_span: Optional[Tuple[int, int]] = (avoid[0], avoid[1]) if avoid else None

    # ── BEST (abhijit) ───────────────────────────────────────────────
    # A best window that overlaps the steer-clear window is contradictory.
    # Keep only the part of abhijit that precedes rahu kalam; drop it if
    # nothing clean remains.
    if best:
        b0, b1, bs, be = best
        if avoid_span:
            r0, r1 = avoid_span
            if b0 < r0 < b1:            # overlaps the tail → trim to rahu start
                b1, be = r0, _fmt(r0)
            elif r0 <= b0 < r1:         # starts inside rahu → no clean best
                b0 = b1                 # force-drop below
        if b1 - b0 >= _MIN_BEST_SPAN:
            out.append({
                "kind": "best",
                "type": "peak",
                "label": "Ventana ideal" if is_es else "Best window",
                "start": bs,
                "end": be,
                "text": (
                    "La ventana más auspiciosa del día — úsala para lo que "
                    "de verdad importa."
                    if is_es else
                    "The day's most auspicious window — use it for anything "
                    "that truly matters."
                ),
            })
            seen.add(_key(b0, b1))

    # ── STEER-CLEAR (rahu kalam) ─────────────────────────────────────
    if avoid:
        r0, r1, rs, re_ = avoid
        out.append({
            "kind": "avoid",
            "type": "caution",
            "label": "Evitar" if is_es else "Steer clear",
            "start": rs,
            "end": re_,
            "text": (
                "Evita decisiones grandes o firmar algo en esta franja — "
                "deja que pase."
                if is_es else
                "Avoid big decisions or signing anything in this window — "
                "let it pass."
            ),
        })
        seen.add(_key(r0, r1))

    # ── SUPPORTING (carry distinct LLM windows, deduped) ─────────────
    # Only reflection/connection context windows — never another "peak",
    # which would compete with the abhijit best window. Skip anything
    # that overlaps an already-chosen window. Cap at 2.
    support_label = "Apoyo" if is_es else "Supporting"
    for w in (llm_windows or []):
        if len([o for o in out if o["kind"] == "supporting"]) >= 2:
            break
        if not isinstance(w, dict):
            continue
        if (w.get("type") or "").lower() not in ("reflection", "connection"):
            continue
        rng = _parse_range(f"{w.get('start', '')} - {w.get('end', '')}")
        if not rng:
            continue
        s0, s1, ss, se = rng
        k = _key(s0, s1)
        if k in seen:
            continue
        if any(_overlaps(s0, s1, *_key_to_span(o)) for o in out):
            continue
        text = (w.get("text") or "").strip()
        if not text:
            continue
        out.append({
            "kind": "supporting",
            "type": w.get("type"),
            "label": support_label,
            "start": ss,
            "end": se,
            "text": text,
        })
        seen.add(k)

    # ── Fallback — never return an empty card ────────────────────────
    if not out:
        return _dedup_passthrough(llm_windows or [])

    return out


def _key_to_span(win: Dict[str, Any]) -> Tuple[int, int]:
    rng = _parse_range(f"{win.get('start', '')} - {win.get('end', '')}")
    if not rng:
        return (0, 0)
    return (rng[0], rng[1])


def _dedup_passthrough(llm_windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Last resort: return LLM windows with exact-duplicate ranges removed."""
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for w in llm_windows:
        if not isinstance(w, dict):
            continue
        rng = _parse_range(f"{w.get('start', '')} - {w.get('end', '')}")
        k = _key(rng[0], rng[1]) if rng else (w.get("start"), w.get("end"))
        if k in seen:
            continue
        seen.add(k)
        out.append(w)
    return out
