"""[instrument-timeline 2026-10-12] Data for the ONE zoomable Timeline component (day / month / year / chapter).

Every zoom returns the same shape so the client draws a single component:
    {zoom, start, end, now, tracks:[{key,label,bands:[{kind,start,end,from,to,label?}]}]}
`from`/`to` are 0-1 fractions of [start,end] (clipped), `now` likewise. kind is open | care | best | avoid | chapter | shift.
Deterministic; built only from payloads the engines already computed (daily signal strip, Windows feed tracks, phase view)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from antar_engine import brief as _brief

ZOOMS = ("day", "month", "year", "chapter")


def _d(s) -> Optional[date]:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _fr(d: date, a: date, b: date) -> float:
    span = max(1, (b - a).days)
    return round(max(0.0, min(1.0, (d - a).days / span)), 4)


def _clip(runs, a: date, b: date, kind_key="kind") -> List[Dict[str, Any]]:
    out = []
    for r in runs or []:
        s, e = _d(r.get("start")), _d(r.get("end"))
        if not s or not e or e < a or s > b:
            continue
        s2, e2 = max(s, a), min(e, b)
        out.append({"kind": r.get(kind_key), "start": s2.isoformat(), "end": e2.isoformat(),
                    "from": _fr(s2, a, b), "to": _fr(e2 + timedelta(days=1), a, b), **({"label": r["label"]} if r.get("label") else {})})
    return out


def day(signal, now_h: float, today: date) -> Dict[str, Any]:
    bands = _brief.build_strip(signal)
    return {"zoom": "day", "start": today.isoformat(), "end": today.isoformat(), "now": _brief._frac(now_h),
            "tracks": [{"key": "day", "label": "Today", "bands": bands}] if bands else []}


def windows_zoom(zoom: str, feed, today: date) -> Dict[str, Any]:
    a = today
    b = today + timedelta(days=30 if zoom == "month" else 365)
    tracks = []
    for t in (feed or {}).get("tracks") or []:
        bands = _clip(t.get("windows"), a, b)
        if bands:
            tracks.append({"key": t.get("topic"), "label": t.get("label"), "bands": bands})
    return {"zoom": zoom, "start": a.isoformat(), "end": b.isoformat(), "now": 0.0, "tracks": tracks}


def chapter(phase, today: date) -> Dict[str, Any]:
    if not phase or not phase.get("available"):
        return {"zoom": "chapter", "start": None, "end": None, "now": 0.0, "tracks": []}
    ch = phase.get("chapter") or {}
    a, b = _d(ch.get("start")), _d(ch.get("end"))
    if not a or not b or b <= a:
        return {"zoom": "chapter", "start": None, "end": None, "now": 0.0, "tracks": []}
    runs = [{"kind": "chapter", "start": ch.get("start"), "end": ch.get("end"), "label": ch.get("plain_name")}]
    shifts = []
    sh = phase.get("shift")
    if sh and sh.get("start"):
        shifts.append({"kind": "shift", "start": sh.get("start"), "end": sh.get("end"), "label": sh.get("plain_name")})
    for u in phase.get("upcoming_shifts") or []:
        shifts.append({"kind": "shift", "start": u.get("start"), "end": u.get("end"), "label": u.get("plain_name")})
    tracks = [{"key": "chapter", "label": "Chapter", "bands": _clip(runs, a, b)}]
    if shifts:
        tracks.append({"key": "shift", "label": "Shift", "bands": _clip(shifts, a, b)})
    return {"zoom": "chapter", "start": a.isoformat(), "end": b.isoformat(), "now": _fr(today, a, b), "tracks": tracks}


def build(zoom: str, signal, feed, phase, today: date, now_h: float) -> Dict[str, Any]:
    z = zoom if zoom in ZOOMS else "day"
    if z == "day":
        out = day(signal, now_h, today)
    elif z == "chapter":
        out = chapter(phase, today)
    else:
        out = windows_zoom(z, feed, today)
    out["version"] = "timeline-1"
    return out
