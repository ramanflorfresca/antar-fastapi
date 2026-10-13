"""[instrument-brief 2026-10-12] The one-glance Today for the timing-instrument redesign.

    verdict   Go / Steady / Wait  (one word, derived from fields the daily engine already computed)
    window    the best window today (dated, with the avoid window beside it)
    strip     the day as bands across 06:00-24:00, as 0-1 fractions, so the client draws one component
    closing   a window that ends soon (hours left to local midnight / to the window end)
    beyond    one-liners for the month, the year and the chapter, each opening the timeline at that zoom
    line      one warm human-written line, picked by (chart, date, verdict) from a CURATED library

Integrity: engines compute, copy only phrases. No LLM, no new astrology. The warm-line library is hand-written
(en + es), copy-reviewed; the pick is deterministic so a day never flickers.
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

# Warm lines: copy-reviewed 2026-10-12 (see Antar.world/WARM_LINE_LIBRARY_for_copy_review.md). Short, plain, conditions never
# outcomes, never fear. Change text only through copy review; the pick below depends on pool sizes only.
_LINES = {
    "en": {
        "go": [
            "A good day to say the thing you have been rehearsing.",
            "The door looks open. Walk through it while the day holds.",
            "Conditions are with you. Make the call that matters.",
            "If you have been waiting for a sign, today is a fair day to move.",
            "Send it. Today favours clear asks.",
            "You have more room today than usual. Use it on one thing.",
            "A day to decide, not to keep weighing.",
            "Good footing today. Take the step you have been circling.",
            "One thing is worth a yes today. Give it.",
            "Ask plainly today. The day favours a clear question.",
            "Momentum is available. Spend it on what matters most.",
            "Start the conversation. Today gives it a better chance.",
        ],
        "steady": [
            "Nothing is forcing your hand today. Keep going at your own pace.",
            "A quiet day does real work. Finish what is already in motion.",
            "No big moves needed. Small, honest progress counts.",
            "An ordinary day, and a useful one. Tidy the loose ends.",
            "Not a day to bet big. A good day to keep your word.",
            "Keep it simple. Do the next right thing.",
            "Today rewards the patient task. Do it well and move on.",
            "Mixed signals today, so keep your plans small and flexible.",
            "Good for follow-ups. Grand announcements can wait.",
            "Stay with what you started. Starting something new can wait.",
            "A level day. Use it to catch up, not to leap.",
            "Light touch today. Notice, don't force.",
            "A steady day. Steady is enough.",
            "Do the ordinary thing well. That is the work today.",
            "No rush today. The task in front of you is the right one.",
            "Keep your promises, especially the small ones.",
            "A day for maintenance, not for milestones.",
            "Nothing needs to be decided today. Let it rest.",
        ],
        "wait": [
            "Today is for preparing, not committing. Draft it, sleep on it.",
            "Hold the big decision. The window you want is not today.",
            "Go gently. What you protect today is worth more than what you push.",
            "If it can wait a day, let it wait.",
            "Not a day to force a yes. Gather, don't sign.",
            "Slow is the right speed today.",
            "Write the hard message, but do not send it yet.",
            "Keep today small. There is no need to force it.",
            "Listen more than you decide today.",
            "Give the details one more look. Commit when you are ready.",
            "Let the argument wait. It will keep.",
            "Pause is a decision too. Take it without guilt.",
        ],
    },
    "es": {
        "go": [
            "Buen día para decir eso que has estado ensayando.",
            "La puerta parece abierta. Cruza mientras el día aguante.",
            "Las condiciones te acompañan. Haz la llamada que importa.",
            "Si esperabas una señal, hoy es un día razonable para moverte.",
            "Envíalo. Hoy favorece las peticiones claras.",
            "Hoy tienes más margen que de costumbre. Úsalo en una sola cosa.",
            "Un día para decidir, no para seguir dándole vueltas.",
            "Buen terreno hoy. Da el paso que llevas tiempo rodeando.",
            "Di que sí a lo único que merece un sí.",
            "Pide con claridad hoy. El día favorece una pregunta clara.",
            "Hay impulso disponible. Gástalo en lo que más importa.",
            "Empieza esa conversación. Hoy le da mejor oportunidad.",
        ],
        "steady": [
            "Nada te obliga hoy. Sigue a tu ritmo.",
            "Un día tranquilo también trabaja. Termina lo que ya está en marcha.",
            "No hacen falta grandes movimientos. El progreso pequeño cuenta.",
            "Un día normal, y útil. Cierra los cabos sueltos.",
            "No es día para apuestas grandes. Sí para cumplir tu palabra.",
            "Hazlo simple. Haz lo siguiente que toca.",
            "Hoy premia la tarea paciente. Hazla bien y sigue.",
            "Señales mezcladas hoy: mantén los planes pequeños y flexibles.",
            "Bueno para dar seguimiento. Los grandes anuncios pueden esperar.",
            "Quédate con lo que empezaste. Lo nuevo puede esperar.",
            "Un día parejo. Úsalo para ponerte al día, no para dar saltos.",
            "Toque suave hoy. Observa, no fuerces.",
            "Un día estable. Lo estable es suficiente.",
            "Haz bien lo ordinario. Ese es el trabajo de hoy.",
            "Sin prisa hoy. La tarea que tienes delante es la correcta.",
            "Cumple tu palabra, sobre todo en lo pequeño.",
            "Un día de mantenimiento, no de hitos.",
            "Hoy no hay que decidir nada. Déjalo descansar.",
        ],
        "wait": [
            "Hoy es para preparar, no para comprometerse. Escríbelo y déjalo reposar.",
            "Retén la decisión grande. La ventana que buscas no es hoy.",
            "Ve con suavidad. Lo que cuidas hoy vale más que lo que empujas.",
            "Si puede esperar un día, que espere.",
            "No es día para forzar un sí. Reúne información, no firmes.",
            "Ir despacio es la velocidad correcta hoy.",
            "Escribe el mensaje difícil, pero no lo envíes todavía.",
            "Que hoy sea pequeño. No hace falta forzarlo.",
            "Hoy escucha más de lo que decides.",
            "Dale otra mirada a los detalles. Comprométete cuando estés listo.",
            "Deja la discusión para mañana. Va a seguir ahí.",
            "Pausar también es decidir. Hazlo sin culpa.",
        ],
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
    """Deterministic, stateless, and never the same line twice within len(pool)-1 days for one person+verdict:
    a per-person offset plus the day ordinal walks the pool, so two days of the same verdict land on different
    lines unless they are an exact multiple of the pool size apart."""
    pool = _LINES[_lang(language)][verdict if verdict in VERDICTS else "steady"]
    off = int(hashlib.sha256(f"{chart_id}|{verdict}".encode()).hexdigest(), 16)
    return pool[(off + day.toordinal()) % len(pool)]


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
