"""[one-timing-source 2026-10-13] Reconcile an Ask answer's window with the Windows feed so one chart never gets two
stories about the same stretch.

Found live: Ask said "the money window is Jun 2027 – Oct 2027" while the Windows feed (Home, J9/J10, suggested questions)
showed Jan 10 – May 9, 2027 as the open money stretch and Jun 9 – Sep 6, 2027 as a CARE stretch for money. Two engines
(the event / dasha-convergence engine behind Ask, and the topic windows) answered with different methods, and the user saw
both. A good astrologer would not hide that; they would read the two together: the long-range period points to Jun–Oct,
but transits press on money until Sep 6, so the usable part is Sep 7 onward.

This does exactly that, deterministically:
  * the Ask window is clipped to what is still ahead;
  * any part of it that falls in a care stretch of the same topic is cut out, and the largest remaining piece (>= 21 days)
    becomes the label; if nothing usable remains the window stays but is flagged as a slow, pressured start;
  * a window that sits inside an open stretch is confirmed;
  * a window the feed knows nothing about is left alone.
It only ever narrows or annotates a window the engines already produced; it invents no dates. Pure functions."""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

_MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "ene": 1, "abr": 4, "ago": 8, "dic": 12, "fev": 2, "set": 9, "out": 10, "dez": 12}
_TOKEN = re.compile(r"(?<![A-Za-z])(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|abr|ago|dic|fev|set|out|dez)[a-z]*\.?\s+(\d{4})",
                    re.I)
_TOPIC = {"finance": "money", "speculation": "money", "wealth": "money", "funding": "money", "career": "career",
          "business": "business", "love": "love", "marriage": "love", "health": "health"}
_MIN_DAYS = 21
_NAME = {"en": {"money": "money", "career": "career", "business": "business", "love": "love", "health": "health"},
         "es": {"money": "el dinero", "career": "la carrera", "business": "el negocio", "love": "el amor", "health": "la salud"}}
_MONS = {"en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
         "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")}


def topic_for_concern(concern: Optional[str]) -> Optional[str]:
    return _TOPIC.get(str(concern or "").lower())


def parse_label(label: Optional[str]) -> Optional[Tuple[date, date]]:
    """'Jun 2027 – Oct 2027' -> (2027-06-01, 2027-10-31); 'Jan 2027' -> that month. None if there is no month-year."""
    toks = _TOKEN.findall(str(label or ""))
    if not toks:
        return None
    (m1, y1), (m2, y2) = toks[0], toks[-1]
    a = date(int(y1), _MON[m1.lower()[:3]], 1)
    mm, yy = _MON[m2.lower()[:3]], int(y2)
    return a, date(yy, mm, monthrange(yy, mm)[1])


def windows_for_topic(feed: Optional[dict], topic: str) -> List[Dict[str, Any]]:
    out = []
    for t in (feed or {}).get("tracks") or []:
        if t.get("topic") != topic:
            continue
        for w in t.get("windows") or []:
            try:
                s, e = date.fromisoformat(str(w["start"])[:10]), date.fromisoformat(str(w["end"])[:10])
            except (KeyError, ValueError):
                continue
            if w.get("kind") in ("open", "care"):
                out.append({"kind": w["kind"], "start": s, "end": e})
    return out


def _overlap(a: Tuple[date, date], s: date, e: date) -> int:
    lo, hi = max(a[0], s), min(a[1], e)
    return max(0, (hi - lo).days + 1)


def _subtract(win: Tuple[date, date], cares: List[Dict[str, Any]]) -> List[Tuple[date, date]]:
    pieces = [win]
    for c in cares:
        nxt = []
        for a, b in pieces:
            if c["end"] < a or c["start"] > b:
                nxt.append((a, b))
                continue
            if c["start"] > a:
                nxt.append((a, c["start"] - timedelta(days=1)))
            if c["end"] < b:
                nxt.append((c["end"] + timedelta(days=1), b))
        pieces = nxt
    return [p for p in pieces if (p[1] - p[0]).days + 1 >= _MIN_DAYS]


def _md(d: date, lg: str) -> str:
    return f"{d.day} {_MONS[lg][d.month - 1]}" if lg == "es" else f"{_MONS[lg][d.month - 1]} {d.day}"


def _ym(d: date, lg: str) -> str:
    return f"{_MONS[lg][d.month - 1]} {d.year}"


def reconcile(label: str, windows: List[Dict[str, Any]], topic: str, language: str = "en",
              today: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """None when nothing should change. Else {status, label, note}: status = confirmed | trimmed | pressured."""
    lg = "es" if str(language or "en").lower().startswith("es") else "en"
    win = parse_label(label)
    if not win or not windows:
        return None
    today = today or date.today()
    if win[1] < today:
        return None
    win = (max(win[0], today), win[1])
    cares = [w for w in windows if w["kind"] == "care" and _overlap(win, w["start"], w["end"])]
    opens = [w for w in windows if w["kind"] == "open" and _overlap(win, w["start"], w["end"])]
    span = (win[1] - win[0]).days + 1
    name = _NAME[lg].get(topic, topic)
    if not cares:
        if opens and sum(_overlap(win, w["start"], w["end"]) for w in opens) >= span * 0.5:
            o = max(opens, key=lambda w: _overlap(win, w["start"], w["end"]))
            note = (f"This sits inside your open stretch for {name} ({_md(o['start'], lg)} – {_md(o['end'], lg)}), so it carries more weight."
                    if lg == "en" else f"Esto cae dentro de tu tramo abierto para {name} ({_md(o['start'], lg)} – {_md(o['end'], lg)}), así que pesa más.")
            return {"status": "confirmed", "label": label, "note": note}
        return None
    cspan = "; ".join(f"{_md(c['start'], lg)} – {_md(c['end'], lg)}" for c in sorted(cares, key=lambda c: c["start"]))
    pieces = _subtract(win, cares)
    if pieces:
        a, b = max(pieces, key=lambda p: (p[1] - p[0]).days)
        new = f"{_ym(a, lg)} – {_ym(b, lg)}" if (a.year, a.month) != (b.year, b.month) else _ym(a, lg)
        if lg == "en":
            note = (f"One thing to read with it: {cspan} is a care stretch for {name}, so the usable part of that window "
                    f"runs {_md(a, lg)} – {_md(b, lg)}. Expect a slow start before it.")
        else:
            note = (f"Para leerlo bien: {cspan} es un tramo de cuidado para {name}, así que la parte útil de esa ventana "
                    f"va del {_md(a, lg)} al {_md(b, lg)}. Espera un inicio lento.")
        return {"status": "trimmed", "label": new, "note": note}
    note = (f"One thing to read with it: {cspan} is a care stretch for {name} that covers most of that window, so expect it to build slowly "
            f"and do not force it." if lg == "en" else
            f"Para leerlo bien: {cspan} es un tramo de cuidado para {name} que cubre casi toda esa ventana; espera que avance despacio y no lo fuerces.")
    return {"status": "pressured", "label": label, "note": note}


def apply_to_answer(res: Dict[str, Any], rc: Dict[str, Any], original_label: str) -> Dict[str, Any]:
    """Update an /ask response in place: the label wherever it appears, the `timing` field, and one note sentence placed
    before 'It holds if' (or at the end of the read)."""
    if not rc or not isinstance(res, dict):
        return res
    new, note = rc["label"], rc["note"]
    read = res.get("read")
    if isinstance(read, str) and read:
        if new != original_label:
            read = read.replace(original_label, new)
        m = re.search(r"(?<![A-Za-z])(It holds if|Se sostiene si|Se sustenta se)\b", read)
        read = (read[:m.start()].rstrip() + " " + note + " " + read[m.start():]) if m else (read.rstrip() + " " + note)
        res["read"] = read
    if isinstance(res.get("timing"), str):
        res["timing"] = new
    res["timing_note"] = {"status": rc["status"], "text": note}
    return res
