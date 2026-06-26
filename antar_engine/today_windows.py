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

# [today-windows-v2] Sanity-gate bounds. A real, surfaceable window must
# begin no earlier than _WAKE_START, end no later than _WAKE_END, span no
# more than _MAX_SPAN, and not cross midnight (cross-midnight ends are
# normalized > 1440 by _parse_range and thus rejected here).
_WAKE_START = 5 * 60      # 05:00
_WAKE_END = 23 * 60       # 23:00
_MAX_SPAN = 6 * 60        # 6h — longer is a bug


def _sane(s0: int, s1: int) -> bool:
    """True iff [s0, s1] is a real daytime window (no overnight, no >6h,
    no midnight-cross). s1 is already normalized by _parse_range."""
    if s1 <= s0:
        return False
    if s1 - s0 > _MAX_SPAN:
        return False
    if s0 < _WAKE_START or s1 > _WAKE_END:
        return False
    return True


def _first_purpose(src: Any, fallback: str) -> str:
    """First non-empty string purpose token from a str or list, else fallback."""
    if isinstance(src, str) and src.strip():
        return src.strip()
    if isinstance(src, (list, tuple)):
        for item in src:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return fallback


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


# [today-windows-v2] leading avoidance verb to drop from a dont_today token so
# it can be re-framed cleanly as "Avoid <x>" without doubling.
_AVOID_PREFIX = re.compile(r"^\s*(?:avoid(?:ing)?|don'?t|do not|evita(?:r)?|no)\b[\s:,-]*", re.I)


def _strip_avoid_prefix(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return s
    cleaned = _AVOID_PREFIX.sub("", s).strip()
    return cleaned or s


def build_today_windows(
    abhijit: str,
    rahu_kalam: str,
    llm_windows: Optional[List[Dict[str, Any]]] = None,
    language: str = "en",
    best_for: Any = None,
    avoid_for: Any = None,
) -> List[Dict[str, Any]]:
    """[today-windows-v2] Return at most TWO distinct windows: ONE best +
    ONE steer-clear, each carrying a `best_for` purpose token.

    A best window that overlaps the steer-clear window is salvaged to the
    clean slice AFTER rahu kalam (dropped if none remains) — never emitted
    overlapping the avoid window. Every window is sanity-gated to waking
    hours and a sane span, so overnight / midnight-spanning / >6h ranges
    are rejected. Supporting LLM windows are no longer surfaced (they were
    the overnight-noise source). Fail-open: the fallback returns the
    sanity-gated, de-duplicated LLM windows so the card is never garbage.
    """
    is_es = (language or "en").lower().startswith("es")

    best_token = _first_purpose(
        best_for, "lo que más importa hoy" if is_es else "what matters most today")
    avoid_token = _first_purpose(
        avoid_for, "decisiones grandes o firmar algo" if is_es else "big decisions or signing")
    # [today-windows-v2] dont_today tokens are often already phrased as an
    # avoidance ("avoid compromising on goals", "don't overcommit"). Strip the
    # leading avoid/don't so the rendered text doesn't double it up
    # ("Avoid avoid compromising…").
    avoid_token = _strip_avoid_prefix(avoid_token)

    out: List[Dict[str, Any]] = []

    best = _parse_range(abhijit)
    avoid = _parse_range(rahu_kalam)
    avoid_span = (avoid[0], avoid[1]) if avoid else None

    # ── BEST (abhijit), salvaged clear of the steer-clear window ──────
    if best:
        b0, b1, _bs, _be = best
        if avoid_span:
            r0, r1 = avoid_span
            if _overlaps(b0, b1, r0, r1):
                b0 = max(b0, r1)   # keep only the slice AFTER rahu ends
        if b1 - b0 >= _MIN_BEST_SPAN and _sane(b0, b1):
            out.append({
                "kind": "best",
                "type": "peak",
                "label": "Ventana ideal" if is_es else "Best window",
                "start": _fmt(b0),
                "end": _fmt(b1),
                "best_for": best_token,
                "text": (
                    f"La ventana más auspiciosa del día — úsala para {best_token}."
                    if is_es else
                    f"The day's most auspicious window — use it for {best_token}."
                ),
            })

    # ── STEER-CLEAR (rahu kalam) ─────────────────────────────────────
    if avoid and _sane(avoid[0], avoid[1]):
        _r0, _r1, rs, re_ = avoid
        out.append({
            "kind": "avoid",
            "type": "caution",
            "label": "Evitar" if is_es else "Steer clear",
            "start": rs,
            "end": re_,
            "best_for": (f"evitar {avoid_token}" if is_es else f"avoiding {avoid_token}"),
            "text": (
                f"Evita {avoid_token} en esta franja — deja que pase."
                if is_es else
                f"Avoid {avoid_token} in this window — let it pass."
            ),
        })

    # ── Fallback — never return an empty/garbage card ────────────────
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
        # [today-windows-v2] never surface overnight / insane ranges
        if rng and not _sane(rng[0], rng[1]):
            continue
        k = _key(rng[0], rng[1]) if rng else (w.get("start"), w.get("end"))
        if k in seen:
            continue
        seen.add(k)
        out.append(w)
    return out
