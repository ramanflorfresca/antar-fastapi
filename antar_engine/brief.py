"""[instrument-brief 2026-10-12] The one-glance Today for the timing-instrument redesign.

    verdict   Go / Steady / Wait  (one word, derived from fields the daily engine already computed)
    window    the best window today (dated, with the avoid window beside it)
    strip     the day as bands across 06:00-24:00, as 0-1 fractions, so the client draws one component
    closing   a window that ends soon (hours left to local midnight / to the window end)
    beyond    one-liners for the month, the year and the chapter, each opening the timeline at that zoom
    line      one warm human-written line, picked by (chart, date, verdict) from a CURATED library

Integrity: engines compute, copy only phrases. No LLM, no new astrology. The warm-line library is hand-written
(en + es) and is a DRAFT until the owner/marketing copy review; the pick is deterministic so a day never flickers.
Pure functions here; the endpoint in main.py supplies the already-computed payloads and fails open."""
from __future__ import annotations

import hashlib
from datetime import date as _date
from typing import Any, Dict, List, Optional

VERDICTS = ("go", "steady", "wait")
DAY_START_H, DAY_END_H = 6.0, 24.0

_WORD = {
    "en": {"go": "Go", "steady": "Steady", "wait": "Wait"},
    "es": {"go": "Avanza", "steady": "Con calma", "wait": "Espera"},
}

# DRAFT warm lines (copy review pending). Short, plain, never predictive of an event, never fear.
_LINES = {
    "en": {
        "go": ["A good day to say the thing you have been rehearsing.",
               "The door is open. Walk through it before the afternoon turns.",
               "Conditions are with you. Make the call that matters."],
        "steady": ["Nothing is forcing your hand today. Keep going at your own pace.",
                   "A quiet day does real work. Finish what is already in motion.",
                   "No big moves needed. Small, honest progress counts."],
        "wait": ["Today is for preparing, not committing. Draft it, sleep on it.",
                 "Hold the big decision. The window you want is not today.",
                 "Go gently. What you protect today is worth more than what you push."],
    },
    "es": {
        "go": ["Buen día para decir eso que has estado ensayando.",
               "La puerta está abierta. Cruza antes de que cambie la tarde.",
               "Las condiciones te acompañan. Haz la llamada que importa."],
        "steady": ["Nada te obliga hoy. Sigue a tu ritmo.",
                   "Un día tranquilo también trabaja. Termina lo que ya está en marcha.",
                   "No hacen falta grandes movimientos. El progreso pequeño cuenta."],
        "wait": ["Hoy es para preparar, no para comprometerse. Escríbelo y déjalo reposar.",
                 "Retén la decisión grande. La ventana que buscas no es hoy.",
                 "Ve con suavidad. Lo que cuidas hoy vale más que lo que empujas."],
    },
}


def _lang(language) -> str:
    return "es" if str(language or "en").lower().startswith("es") else "en"


def derive_verdict(signal: Dict[str, Any]) -> str:
    """Wait if the day is friction or adverse; Go only if positive + steady + confidence not low; else Steady."""
    sig = signal or {}
    key = str((sig.get("day_energy") or {}).get("key") or "").lower()
    direction = str(sig.get("direction") or "").lower()
    conf = str((sig.get("confidence") or {}).get("level") or "").lower()
    if key == "friction" or direction == "adverse" or sig.get("is_friction_day"):
        return "wait"
    if direction == "positive" and key == "steady" and conf not in ("low", ""):
        return "go"
    return "steady"


def pick_line(chart_id: str, day: _date, verdict: str, language: str = "en") -> str:
    pool = _LINES[_lang(language)][verdict if verdict in VERDICTS else "steady"]
    h = int(hashlib.sha256(f"{chart_id}|{day.isoformat()}|{verdict}".encode()).hexdigest(), 16)
    return pool[h % len(pool)]


def _hm(s) -> Optional[float]:
    """'12:17' or '12:17 PM' -> 12.28 hours."""
    if not s:
        return None
    t = str(s).strip().upper()
    pm, am = t.endswith("PM"), t.endswith("AM")
    t = t.replace("PM", "").replace("AM", "").strip()
    try:
        h, m = t.split(":")[:2]
        v = int(h) % 24 + int(m[:2]) / 60.0
    except (ValueError, IndexError):
        return None
    if pm and int(h) < 12:
        v += 12
    if am and int(h) == 12:
        v -= 12
    return v


def _frac(h: float) -> float:
    return round(max(0.0, min(1.0, (h - DAY_START_H) / (DAY_END_H - DAY_START_H))), 4)


def build_strip(signal: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for w in (signal or {}).get("windows") or []:
        kind = w.get("kind")
        if kind not in ("best", "avoid"):
            continue
        a, b = _hm(w.get("start")), _hm(w.get("end"))
        if a is None or b is None or b <= a:
            continue
        out.append({"kind": kind, "start": w.get("start"), "end": w.get("end"),
                    "from": _frac(a), "to": _frac(b)})
    out.sort(key=lambda x: x["from"])
    return out


def closing_soon(strip: List[Dict[str, Any]], now_h: float, within_h: float = 4.0) -> Optional[Dict[str, Any]]:
    """The best window if it is open now or opens soon and ends within `within_h`; hours_left rounded to 0.5."""
    for s in strip:
        if s["kind"] != "best":
            continue
        a, b = _hm(s["start"]), _hm(s["end"])
        if a is not None and b is not None and now_h < b and (b - now_h) <= within_h:
            return {"start": s["start"], "end": s["end"], "open_now": a <= now_h,
                    "hours_left": round((b - now_h) * 2) / 2}
    return None


def _zoom_for(days) -> str:
    """The timeline zoom whose range actually contains a window `days` away (month = 30 days, year = 365)."""
    try:
        return "month" if int(days) <= 30 else "year"
    except (TypeError, ValueError):
        return "year"


def beyond(feed: Optional[Dict[str, Any]], phase: Optional[Dict[str, Any]], language: str = "en") -> List[Dict[str, Any]]:
    """Month / year / chapter one-liners from the windows feed and the phase view. Omits what is missing."""
    es = _lang(language) == "es"
    items: List[Dict[str, Any]] = []
    nxt = [w for w in ((feed or {}).get("next") or []) if w.get("kind") == "open"]
    if nxt:
        w = nxt[0]
        items.append({"zoom": _zoom_for(w.get("opens_in_days")), "topic": w.get("topic"),
                      "text": (f"Se abre una ventana de {w.get('topic')} en {w.get('opens_in_days')} días."
                               if es else f"A {w.get('topic')} window opens in {w.get('opens_in_days')} days."),
                      "range": w.get("label_range")})
    care = ((feed or {}).get("care") or [])
    if care:
        w = care[0]
        items.append({"zoom": _zoom_for(w.get("opens_in_days")), "topic": w.get("topic"),
                      "text": (f"Etapa de cuidado en {w.get('topic')} en {w.get('opens_in_days')} días."
                               if es else f"A care stretch for {w.get('topic')} starts in {w.get('opens_in_days')} days."),
                      "range": w.get("label_range")})
    if phase and phase.get("available") and phase.get("how_they_combine"):
        ch = phase.get("chapter") or {}
        items.append({"zoom": "chapter", "topic": None, "text": phase.get("how_they_combine"),
                      "range": f"{ch.get('start')} \u2192 {ch.get('end')}" if ch.get("start") else None})
    return items


def build(chart_id: str, signal: Dict[str, Any], feed: Optional[Dict[str, Any]], phase: Optional[Dict[str, Any]],
          language: str, today: _date, now_h: float) -> Dict[str, Any]:
    lang = _lang(language)
    verdict = derive_verdict(signal)
    strip = build_strip(signal)
    best = next((s for s in strip if s["kind"] == "best"), None)
    avoid = next((s for s in strip if s["kind"] == "avoid"), None)
    return {
        "version": "brief-1", "date": today.isoformat(), "language": lang,
        "verdict": verdict, "verdict_word": _WORD[lang][verdict],
        "line": pick_line(chart_id, today, verdict, lang),
        "window": {"best": best, "avoid": avoid},
        "strip": {"day_start": "06:00", "day_end": "24:00", "bands": strip, "now": _frac(now_h)},
        "closing_soon": closing_soon(strip, now_h),
        "beyond": beyond(feed, phase, lang),
        "source": {"engine": "daily-signal", "confidence": (signal or {}).get("confidence", {}).get("level")},
    }
