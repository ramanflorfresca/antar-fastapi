"""[focus-why 2026-10-17] WHY a window is strong (or hard) for an area, in plain words, for the sheet a tap on a "next 3 months" block opens.

Composed only from what the focus detail already holds: the chapters running over the window (their theme, what each is about, what to
watch and what helps, and whether it works through the same part of life as the area) and the window's own peak. No method, planet or
house names; the theme names are the plain ones (Ambition, Growth, Intellect ...). Wording is here, in en / es."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}
TX = {
    "en": {"now": "You are in {a} {theme} chapter until {end}. It is about {covers}.",
           "up": "It works through the same part of your life as {area}, which is why this stretch lifts it.",
           "down": "It works against {area}, so progress here asks for patience.",
           "next": "From {start}, {a} {theme} chapter takes over: {covers}.",
           "next_up": "It keeps lifting {area}.", "next_down": "It eases the pressure on {area}.",
           "watch": "In this chapter, watch for {watch}. What helps: {helps}.",
           "peak": "The strongest stretch is {a} to {b}."},
    "es": {"now": "Estás en un capítulo de {theme} hasta el {end}. Trata de {covers}.",
           "up": "Actúa sobre la misma parte de tu vida que {area}, por eso este tramo la impulsa.",
           "down": "Actúa en contra de {area}, así que el avance aquí pide paciencia.",
           "next": "Desde el {start}, toma el relevo un capítulo de {theme}: {covers}.",
           "next_up": "Sigue impulsando {area}.", "next_down": "Alivia la presión sobre {area}.",
           "watch": "En este capítulo, cuida {watch}. Lo que ayuda: {helps}.",
           "peak": "El tramo más fuerte va del {a} al {b}."},
}


def _d(x) -> Optional[date]:
    try:
        return date.fromisoformat(str(x)[:10])
    except Exception:
        return None


def _a(word: str, lg: str) -> str:
    return "an" if lg == "en" and (word or "")[:1].lower() in "aeiou" else "a"


def _fmt(d: date, lg: str, today: date) -> str:
    base = f"{d.day} {MON[lg][d.month - 1]}" if lg == "es" else f"{MON[lg][d.month - 1]} {d.day}"
    if d.year != today.year or (d - today).days > 183:
        return f"{base} {d.year}" if lg == "es" else f"{base}, {d.year}"
    return base


def build(label: str, bring: List[dict], chapters: List[dict], windows: Optional[dict], lang: str, today: date) -> Optional[dict]:
    """{headline, because: [sentences], peak} or None when there is nothing real to say."""
    lg = "es" if str(lang or "en").lower().startswith("es") else "en"
    t = TX[lg]
    area = (label or "").lower()
    chs = [c for c in chapters or [] if c.get("theme") and _d(c.get("end")) and _d(c["end"]) >= today]
    chs.sort(key=lambda c: c["start"])
    headline = ((bring or [{}])[0] or {}).get("text")
    because = []
    if chs:
        c = chs[0]
        if c.get("covers"):
            because.append(t["now"].format(a=_a(c["theme"], lg), theme=c["theme"], end=_fmt(_d(c["end"]), lg, today), covers=c["covers"]))
            because.append(t["up"].format(area=area) if c.get("supports") else t["down"].format(area=area))
        if len(chs) > 1 and chs[1].get("covers"):
            n = chs[1]
            because.append(t["next"].format(a=_a(n["theme"], lg), start=_fmt(_d(n["start"]), lg, today), theme=n["theme"], covers=n["covers"]) + " "
                           + (t["next_up"] if n.get("supports") else t["next_down"]).format(area=area))
        if c.get("watch") and c.get("helps"):
            because.append(t["watch"].format(watch=c["watch"], helps=c["helps"]))
    peak = None
    pk = ((windows or {}).get("best") or {}).get("peaks") or []
    if pk and _d(pk[0].get("start")) and _d(pk[0].get("end")):
        peak = t["peak"].format(a=_fmt(_d(pk[0]["start"]), lg, today), b=_fmt(_d(pk[0]["end"]), lg, today))
    if not (because or peak):
        return None
    return {"headline": headline, "because": because, "peak": peak}
