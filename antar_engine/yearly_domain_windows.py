"""
antar_engine/yearly_domain_windows.py — [yearly-windows 2026-09-09]

The yearly reading gave per-domain TIERS (move now / hold steady / go slow) + a
single global best-months list, but no per-domain DATED windows — so it read
generic next to competitors who say, per life-area, the exact months of ups and
downs ("Finance: gain then loss Jun–Jul 2026; weak Oct–Nov 2026; strong Jul–Aug").

This closes that gap using the SAME convergence sweep the monthly uses, run across
the 12 months of the solar-return year. For each life-domain it collects a
month-by-month polarity series, merges consecutive same-tone months into windows,
ranks domains by real activation, and writes a plain dated line per domain.

Deterministic (swisseph transits + daśā), no LLM. Falls back to [] on any error.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from antar_engine.house_activation import DOMAIN_SWEEP, score_domains

try:
    from antar_engine.transit_events import compute_transit_events_in_range as _tev
    _HAS_TEV = True
except Exception:
    _HAS_TEV = False

_MONTH = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Year-appropriate friendly labels (a shade more formal than the daily map).
YEAR_LABEL: Dict[str, str] = {
    "work":         "Work",
    "authority":    "Standing & official matters",
    "money":        "Finance",
    "speculation":  "Ventures & risk",
    "home":         "Home & property",
    "travel":       "Travel & the far-off",
    "relationship": "Love & partnership",
    "family":       "Family",
    "health":       "Health",
    "spiritual":    "Inner life",
}


def _solar_year(birth_date: str, today: date) -> tuple:
    """(start_date, end_date) of the current solar-return year — birthday to the
    day before the next birthday, matching the yearly period the app shows."""
    try:
        y, m, d = [int(x) for x in str(birth_date)[:10].split("-")]
    except Exception:
        m, d = 1, 1
    # most recent birthday on/before today
    try:
        anchor = date(today.year, m, min(d, 28))
    except Exception:
        anchor = date(today.year, 1, 1)
    if anchor > today:
        anchor = date(today.year - 1, m, min(d, 28))
    end = date(anchor.year + 1, anchor.month, anchor.day) - timedelta(days=1)
    return anchor, end


def _month_starts(start: date, end: date) -> List[date]:
    """One anchor date per month across [start, end] (mid-month, capped 12)."""
    out, cur = [], date(start.year, start.month, 15)
    for _ in range(13):
        if cur > end:
            break
        if cur >= date(start.year, start.month, 1):
            out.append(cur)
        # advance a month
        ny, nm = (cur.year + (cur.month // 12), (cur.month % 12) + 1)
        cur = date(ny, nm, 15)
    return out[:12]


def _tones_relative(rows: List[dict]) -> List[str]:
    """Given a domain's month series [{score, polarity}], return a per-month tone
    ['up'|'down'|''] using the domain's OWN baseline — so we surface the months
    that genuinely STAND OUT (transit-driven peaks/dips), not every above-zero
    month. A flat-but-high domain yields no windows (it's steady, not a window).
    A risk-polarity month is always 'down' regardless of score."""
    n = len(rows)
    scores = [float(r.get("score") or 0.0) for r in rows]
    pols = [(r.get("polarity") or "neutral").lower() for r in rows]
    if not scores:
        return [""] * n
    rng = max(scores) - min(scores)

    # 'up' = the few PEAK months (top-K opportunity months by score) — keeps the
    # window to a standout stretch, not "most of the year". 'down' = every risk
    # month, plus (if no risk) the weakest 1-2 non-opportunity months. A flat
    # domain (rng < 1.5) yields nothing — steady, not window-worthy.
    K_UP = 3
    order = sorted(range(n), key=lambda i: scores[i], reverse=True)
    up_idx = set()
    if rng >= 1.5:
        for i in order:
            if pols[i] == "opportunity":
                up_idx.add(i)
            if len(up_idx) >= K_UP:
                break

    down_idx = {i for i in range(n) if pols[i] == "risk"}
    if not down_idx and rng >= 1.5:
        weak = sorted((i for i in range(n) if pols[i] != "opportunity"),
                      key=lambda i: scores[i])[:2]
        down_idx.update(weak)

    out = []
    for i in range(n):
        if i in up_idx and i not in down_idx:
            out.append("up")
        elif i in down_idx:
            out.append("down")
        else:
            out.append("")
    return out


def _fmt_window(a: date, b: date) -> str:
    """'Jul–Aug 2026' / 'Dec 2025' from a month-window."""
    if a.year == b.year and a.month == b.month:
        return f"{_MONTH[a.month]} {a.year}"
    if a.year == b.year:
        return f"{_MONTH[a.month]}–{_MONTH[b.month]} {a.year}"
    return f"{_MONTH[a.month]} {a.year} – {_MONTH[b.month]} {b.year}"


def _runs(series: List[tuple], want: str) -> List[str]:
    """Merge consecutive months of the same tone into window strings.
    series = [(date, tone), …] in month order."""
    out, run_start, prev = [], None, None
    for dt, tone in series + [(None, None)]:
        if tone == want:
            if run_start is None:
                run_start = dt
            prev = dt
        else:
            if run_start is not None:
                out.append(_fmt_window(run_start, prev))
                run_start = None
    return out


def _runs_dated(series: List[tuple], want: str) -> List[tuple]:
    """Like _runs but keeps the month anchors: (label, first_anchor, last_anchor)
    so the caller can flag each window past/current/upcoming."""
    out, run_start, prev = [], None, None
    for dt, tone in series + [(None, None)]:
        if tone == want:
            if run_start is None:
                run_start = dt
            prev = dt
        else:
            if run_start is not None:
                out.append((_fmt_window(run_start, prev), run_start, prev))
                run_start = None
    return out


def _win_status(first_anchor: date, last_anchor: date, today: date) -> str:
    """past | current | upcoming for a window spanning [first_anchor month ..
    last_anchor month] relative to today. Lets This Year show the varshphal
    retrospective (past marked as past) while highlighting the runway ahead."""
    start_first = date(first_anchor.year, first_anchor.month, 1)
    y, m = last_anchor.year, last_anchor.month
    ny, nm = (y + (m // 12), (m % 12) + 1)
    last_end = date(ny, nm, 1) - timedelta(days=1)
    if last_end < today:
        return "past"
    if start_first > today:
        return "upcoming"
    return "current"


def build_yearly_domain_windows(chart_data: dict, dashas: dict,
                                birth_date: str, today: Optional[date] = None,
                                max_domains: int = 4, year_offset: int = 0) -> List[dict]:
    """Per-domain dated up/down windows across the solar year.

    Returns [{key, label, line, up_windows[], down_windows[], score}], ranked by
    real activation, most-active first. Empty list if transits unavailable.

    year_offset shifts the solar-return window forward by N years so the SAME
    engine (dasha + FUTURE gochar, computed per-month via ephemeris) can project
    the NEXT varshphal year (birthday+N → birthday+N+1)."""
    if not _HAS_TEV or not isinstance(chart_data, dict) or not chart_data:
        return []
    today = today or date.today()
    start, end = _solar_year(birth_date, today)
    if year_offset:
        def _shift(d: date, n: int) -> date:
            try:
                return d.replace(year=d.year + n)
            except ValueError:      # Feb 29 → Feb 28
                return d.replace(year=d.year + n, day=28)
        start, end = _shift(start, year_offset), _shift(end, year_offset)
    months = _month_starts(start, end)
    if not months:
        return []

    # rows[domain_key] = [{date, score, polarity}, …] in month order
    rows: Dict[str, List[dict]] = {d["key"]: [] for d in DOMAIN_SWEEP}

    for m in months:
        m_start = date(m.year, m.month, 1)
        # end of this month
        ny, nm = (m.year + (m.month // 12), (m.month % 12) + 1)
        m_end = date(ny, nm, 1) - timedelta(days=1)
        try:
            evs = _tev(chart_data, m_start, m_end, include_fast=True) or []
        except Exception:
            evs = []
        try:
            scored = score_domains(chart_data, dashas, evs, m) or []
        except Exception:
            scored = []
        by_key = {s.get("key"): s for s in scored}
        for key in rows:
            dom = by_key.get(key) or {}
            rows[key].append({"date": m,
                              "score": float(dom.get("score") or 0.0),
                              "polarity": dom.get("polarity") or "neutral"})

    say = {d["key"]: (d.get("say") or d["key"]) for d in DOMAIN_SWEEP}
    out = []
    for key in rows:
        tones = _tones_relative(rows[key])
        series = list(zip([r["date"] for r in rows[key]], tones))
        ups = _runs(series, "up")
        downs = _runs(series, "down")
        # year-activation = total score across standout months (ranks domains)
        activation_score = sum(r["score"] for r, t in zip(rows[key], tones)
                               if t in ("up", "down"))
        if not ups and not downs:
            continue
        label = YEAR_LABEL.get(key, key.title())
        parts = []
        if ups:
            parts.append("strongest around " + ", ".join(ups))
        if downs:
            parts.append("under pressure around " + ", ".join(downs))
        line = f"{say[key].capitalize()} is active this year — " + "; ".join(parts) + "."
        # [past/upcoming 2026-09-10] structured windows carrying past|current|
        # upcoming so the frontend can grey elapsed windows and highlight the
        # runway. up_windows/down_windows (strings) kept for backward compat.
        windows = []
        for _lbl, _a, _b in _runs_dated(series, "up"):
            windows.append({"window": _lbl, "direction": "up",
                            "status": _win_status(_a, _b, today)})
        for _lbl, _a, _b in _runs_dated(series, "down"):
            windows.append({"window": _lbl, "direction": "down",
                            "status": _win_status(_a, _b, today)})
        out.append({
            "key": key, "label": label, "line": line,
            "up_windows": ups, "down_windows": downs,
            "windows": windows,
            "score": round(activation_score, 1),
        })

    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:max_domains]
