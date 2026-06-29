"""
antar_engine/window_sizing.py
=============================
Shared, surface-agnostic date-window sizer  (Fix #1/#2, 2026-06-29).

A predicted "when" must never be voiced more precisely than the COARSEST
contributing technique can actually support:

    dasha / Mahadasha / Varshphal annual  -> year         (whole year)
    Antardasha / bhukti                    -> quarter      (~3 months)
    slow transit (Saturn/Jupiter/nodes)    -> multimonth   (~3 months)
    Masik / monthly condition              -> month        (one month)
    fast transit / daily / score_day       -> day          (NO widening — exempt)

A bare point-date ("June 22") emitted by LLM free-text on a dasha/transit
surface is over-precise by construction — the technique resolves to a month
or a year, never a single day. This module is the enforcement helper.

It is the same philosophy as antar_engine.timing_fidelity.scrub_freelance_dates
(which already guards /ask): Python is the last gate before text reaches the
frontend, never the model. This generalizes it from "scrub month/year tokens
not in the allowed window" to "widen ANY date to its technique's resolution".

Public API
----------
    size_window(date_or_range, technique) -> dict
        {start, end, label, technique, resolution, widened}

    size_dates_in_text(text, technique, mode="shadow") -> (text_out, log)
        Scans free narration for point-dates / month-year / ranges and, per
        `mode`, either rewrites them to the technique-sized label ("on") or
        leaves the text untouched and only reports what it WOULD do ("shadow").

    has_bare_point_date(text) -> bool
        Fail-closed check: True if a month+day point-date survives.

No LLM. No network. Pure text + datetime. Never raises into the request path.
"""

from __future__ import annotations

import contextvars
import os
import re
from datetime import date, datetime, timedelta

# ── Technique → resolution band ──────────────────────────────────────────────
_RESOLUTION = {
    # coarsest
    "dasha": "year", "md": "year", "mahadasha": "year", "maha": "year",
    "varshphal": "year", "varsha": "year", "annual": "year", "year": "year",
    # antardasha / bhukti
    "antardasha": "quarter", "ad": "quarter", "bhukti": "quarter",
    "pratyantar": "quarter", "quarter": "quarter",
    # slow transits resolve to a multi-month band
    "slow_transit": "multimonth", "transit": "multimonth",
    "saturn": "multimonth", "jupiter": "multimonth", "node": "multimonth",
    "rahu": "multimonth", "ketu": "multimonth", "multimonth": "multimonth",
    # masik / monthly condition
    "masik": "month", "monthly": "month", "month": "month",
    # fast / daily — EXEMPT (day precision allowed, no widening)
    "fast_transit": "day", "fast": "day", "daily": "day",
    "score_day": "day", "panchanga": "day", "hora": "day",
    "tara": "day", "day": "day",
}

# half-width (in days) the band expands around the anchor date
_BAND_DAYS = {"quarter": 45, "multimonth": 45}

_MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]
_MONTH_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_ALT = "|".join(sorted(_MONTHS.keys(), key=len, reverse=True))

# "June 22", "June 22nd", "June 22, 2027", "22 June", "22nd of June 2027"
_POINT_DATE_RE = re.compile(
    rf"\b(?:({_MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?"
    rf"|(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_ALT})\.?(?:,?\s+(20\d\d))?)\b",
    re.IGNORECASE,
)
# "June 8-14" / "June 8–14"  (intra-month day range)
_DAY_RANGE_RE = re.compile(
    rf"\b({_MONTH_ALT})\.?\s+(\d{{1,2}})\s*[–—-]\s*(\d{{1,2}})\b", re.IGNORECASE
)


def _resolution_for(technique) -> str:
    return _RESOLUTION.get(str(technique or "").strip().lower(), "month")


def _coerce_date(value):
    """Best-effort parse of a date-ish value to a datetime.date. None on failure."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    s = value.strip()
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    m = _POINT_DATE_RE.search(s)
    if m:
        if m.group(1):  # "Month DD"
            mon = _MONTHS[m.group(1).lower()]; day = int(m.group(2)); yr = m.group(3)
        else:           # "DD Month"
            mon = _MONTHS[m.group(5).lower()]; day = int(m.group(4)); yr = m.group(6)
        yr = int(yr) if yr else date.today().year
        day = min(max(day, 1), 28)
        try:
            return date(yr, mon, day)
        except ValueError:
            return None
    return None


def _label_year(d: date) -> str:
    return str(d.year)


def _label_month(d: date) -> str:
    return f"{_MONTH_NAMES[d.month]} {d.year}"


def _label_band(start: date, end: date) -> str:
    if start.year == end.year:
        return f"{_MONTH_ABBR[start.month]}–{_MONTH_ABBR[end.month]} {start.year}"
    return f"{_MONTH_ABBR[start.month]} {start.year} – {_MONTH_ABBR[end.month]} {end.year}"


def size_window(date_or_range, technique) -> dict:
    """Widen a date (or 'start–end' range) to its technique's resolution.

    Returns {start, end, label, technique, resolution, widened}. `start`/`end`
    are ISO date strings (or None if unparseable). `label` is the jargon-free
    user-facing phrase. `widened` is False when nothing changed (day band).
    """
    resolution = _resolution_for(technique)
    out = {"start": None, "end": None, "label": None,
           "technique": str(technique), "resolution": resolution, "widened": False}

    anchor = _coerce_date(date_or_range)
    if anchor is None:
        # cannot parse — return original string as label, nothing widened
        out["label"] = str(date_or_range)
        return out

    if resolution == "day":
        out["start"] = out["end"] = anchor.isoformat()
        out["label"] = f"{_MONTH_NAMES[anchor.month]} {anchor.day}"
        out["widened"] = False
        return out

    if resolution == "year":
        start, end = date(anchor.year, 1, 1), date(anchor.year, 12, 31)
        out["label"] = _label_year(anchor)
    elif resolution == "month":
        start = date(anchor.year, anchor.month, 1)
        nm = date(anchor.year + (anchor.month // 12), (anchor.month % 12) + 1, 1)
        end = nm - timedelta(days=1)
        out["label"] = _label_month(anchor)
    else:  # quarter / multimonth → symmetric band
        half = _BAND_DAYS.get(resolution, 45)
        start = anchor - timedelta(days=half)
        end = anchor + timedelta(days=half)
        out["label"] = _label_band(start, end)

    out["start"], out["end"] = start.isoformat(), end.isoformat()
    out["widened"] = True
    return out


def size_dates_in_text(text, technique, mode="shadow"):
    """Find day-precise dates in free narration and size them to `technique`.

    mode="shadow": text returned UNCHANGED; `log` reports what would widen.
    mode="on":     each over-precise date rewritten to its sized label.
    Returns (text_out, log) where log = [{original, sized, resolution}, ...].
    Never raises.
    """
    log = []
    if not text or not isinstance(text, str):
        return text, log
    resolution = _resolution_for(technique)
    # day-resolution techniques are EXEMPT — day precision is legitimate.
    if resolution == "day":
        return text, log
    try:
        def _repl_point(m):
            original = m.group(0)
            sized = size_window(original, technique)
            label = sized.get("label") or original
            if not sized.get("widened"):
                return original
            # preserve a leading connector word's grammar ("by June 22" -> "by 2027"
            # reads wrong; prefer "around <label>")
            log.append({"original": original.strip(), "sized": label,
                        "resolution": resolution})
            return label

        def _repl_dayrange(m):
            mon = _MONTHS[m.group(1).lower()]
            yr = date.today().year
            anchor = date(yr, mon, min(int(m.group(2)), 28))
            sized = size_window(anchor, technique)
            label = sized.get("label") or m.group(0)
            log.append({"original": m.group(0).strip(), "sized": label,
                        "resolution": resolution})
            return label

        out = _DAY_RANGE_RE.sub(_repl_dayrange, text)
        out = _POINT_DATE_RE.sub(_repl_point, out)

        if mode == "on" and log:
            out = re.sub(r"\bby\s+(?=\d{4}\b)", "around ", out)
            out = re.sub(r"\s{2,}", " ", out).strip()
            return out, log
        # shadow (or nothing matched): return original text, keep the log
        return text, log
    except Exception:
        return text, log


def has_bare_point_date(text) -> bool:
    """Fail-closed probe: True if a month+day point-date survives in `text`."""
    if not text or not isinstance(text, str):
        return False
    return bool(_POINT_DATE_RE.search(text) or _DAY_RANGE_RE.search(text))


# ── Chokepoint integration (kill switch + shadow capture) ────────────────────
# WINDOW_SIZING = off | shadow | on   (default shadow)
#   off    : do nothing
#   shadow : log what each date WOULD widen to, change nothing
#   on     : rewrite over-precise dates to their technique-sized label
_SHADOW_LOG = contextvars.ContextVar("window_sizing_shadow_log", default=None)


def current_mode() -> str:
    return (os.getenv("WINDOW_SIZING", "shadow") or "shadow").strip().lower()


def begin_capture():
    """Start a fresh shadow-log buffer for the current request/task."""
    _SHADOW_LOG.set([])


def drain_capture(field=None):
    """Return and clear the captured shadow entries (list of dicts)."""
    buf = _SHADOW_LOG.get() or []
    _SHADOW_LOG.set([])
    return buf


def enforce(text, technique, field_name=None):
    """Chokepoint entry. Sizes dates per the WINDOW_SIZING env mode.

    Returns text rewritten ONLY in 'on'; in 'shadow' returns text unchanged
    and records would-widen entries into the active capture buffer. Never
    raises — enforcement must not break the request path.
    """
    mode = current_mode()
    if mode == "off" or not technique or not isinstance(text, str) or not text:
        return text
    try:
        out, log = size_dates_in_text(text, technique, "on" if mode == "on" else "shadow")
        if log:
            buf = _SHADOW_LOG.get()
            if buf is not None:
                for e in log:
                    e2 = dict(e)
                    if field_name:
                        e2["field"] = field_name
                    e2["technique"] = str(technique)
                    buf.append(e2)
        return out
    except Exception:
        return text
