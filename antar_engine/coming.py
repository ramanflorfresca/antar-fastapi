"""[coming 2026-10-13] The "What is coming" screen: the next 12 months as twelve readable tiles, one plain sentence, and
the dated moments, for one topic at a time; plus the running chapter as steps.

Replaces the Gantt-style timeline. Everything here is RE-SHAPED from engines that already compute it (the Windows feed for
areas; the career-change and residence convergence engines for life moves; the phase view for the chapter). No new
astrology and no invented meanings: sentences are assembled from real dates and the engines' own words.
Pure functions; the endpoint in main.py supplies the data. Never raises on missing data (empty -> quiet)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

AREAS = ("money", "career", "love", "health", "business", "peace", "family")
ORDER = ("all", "money", "career", "love", "health", "business", "peace", "family")
# Life moves are NOT month tiles: their engines (career_change_timing, residence_timing) return whole-year windows and flag
# almost every year as forced, which would paint twelve alarming tiles. They are offered as Ask prompts instead, where the
# promise gate and the validate-first wording live.
ASK_MOVES = {
    "en": [{"key": "job_change", "label": "Job change", "question": "When is the best time for me to change jobs?"},
           {"key": "move_home", "label": "Moving home", "question": "When is the best time for me to move home?"}],
    "es": [{"key": "job_change", "label": "Cambio de trabajo", "question": "\u00bfCu\u00e1ndo es el mejor momento para cambiar de trabajo?"},
           {"key": "move_home", "label": "Mudanza", "question": "\u00bfCu\u00e1ndo es el mejor momento para mudarme?"}],
}

LABEL = {
    "en": {"all": "All", "money": "Money", "career": "Career", "love": "Love", "health": "Health", "business": "Business",
           "peace": "Peace", "family": "Family"},
    "es": {"all": "Todo", "money": "Dinero", "career": "Carrera", "love": "Amor", "health": "Salud", "business": "Negocio",
           "peace": "Calma", "family": "Familia"},
}
MON = {"en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
       "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")}


def _lang(language) -> str:
    return "es" if str(language or "en").lower().startswith("es") else "en"


def _d(s) -> Optional[date]:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _md(d: date, lg: str) -> str:
    return f"{d.day} {MON[lg][d.month - 1]}" if lg == "es" else f"{MON[lg][d.month - 1]} {d.day}"


def _my(d: date, lg: str) -> str:
    return f"{MON[lg][d.month - 1]} {d.year}"


def _ord(n: int, lg: str) -> str:
    if lg == "es":
        return f"el {n}"
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def month_list(today: date, n: int = 12) -> List[Tuple[int, int]]:
    out, y, m = [], today.year, today.month
    for _ in range(n):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def _month_range(y: int, m: int) -> Tuple[date, date]:
    first = date(y, m, 1)
    nxt = date(y + (m == 12), 1 if m == 12 else m + 1, 1)
    return first, date.fromordinal(nxt.toordinal() - 1)


def topic_label(key: str, lg: str) -> str:
    return LABEL[lg].get(key, key.replace("_", " ").title())


def chips(lang: str = "en") -> List[Dict[str, str]]:
    lg = _lang(lang)
    return [{"key": k, "label": topic_label(k, lg)} for k in ORDER]


def windows_from_feed(feed: Optional[dict], topic: str) -> List[Dict[str, Any]]:
    """Flatten the Windows feed tracks into [{topic, kind, start, end, why}] for one topic or all area topics."""
    out = []
    for t in (feed or {}).get("tracks") or []:
        key = t.get("topic")
        if key not in AREAS or (topic != "all" and key != topic):
            continue
        for w in t.get("windows") or []:
            s, e = _d(w.get("start")), _d(w.get("end"))
            if s and e and w.get("kind") in ("open", "care"):
                out.append({"topic": key, "kind": w["kind"], "start": s, "end": e})
    # attach the feed's own explanation line where the same window appears in now/next/care
    why = {}
    for bucket in ("now", "next", "care"):
        for w in (feed or {}).get(bucket) or []:
            why[(w.get("topic"), w.get("kind"), str(w.get("start")))] = ((w.get("why") or {}).get("line") or "")
    for w in out:
        w["why"] = why.get((w["topic"], w["kind"], w["start"].isoformat()), "")
    return out


def _overlaps(w, a: date, b: date) -> bool:
    return w["start"] <= b and w["end"] >= a


def _cell_text(ws: List[Dict[str, Any]], a: date, b: date, topic: str, lg: str) -> Tuple[str, str, bool]:
    """(kind, text, care_flag) for one month from the windows overlapping it."""
    opens = [w for w in ws if w["kind"] == "open"]
    cares = [w for w in ws if w["kind"] == "care"]
    if not opens and not cares:
        return "quiet", ("Quiet" if lg == "en" else "Tranquilo"), False
    es = lg == "es"
    if topic != "all":
        w = (opens or cares)[0]
        starts, ends = a <= w["start"] <= b, a <= w["end"] <= b
        if w["kind"] == "open":
            t = (f"Opens {_ord(w['start'].day, lg)}" if not es else f"Se abre {_ord(w['start'].day, lg)}") if starts else \
                (f"Closes {_ord(w['end'].day, lg)}" if not es else f"Cierra {_ord(w['end'].day, lg)}") if ends else \
                ("Open" if not es else "Abierta")
        else:
            t = (f"Care from {_ord(w['start'].day, lg)}" if not es else f"Cuidado desde {_ord(w['start'].day, lg)}") if starts else \
                (f"Care ends {_ord(w['end'].day, lg)}" if not es else f"Cuidado hasta {_ord(w['end'].day, lg)}") if ends else \
                ("Take care" if not es else "Cuidado")
        return ("open" if opens else "care"), t, bool(opens and cares)

    def names(items):
        seen = []
        for w in items:
            nm = topic_label(w["topic"], lg).lower()
            if nm not in seen:
                seen.append(nm)
        return seen
    if opens:
        n = names(opens)
        shown = ", ".join(n[:2]) + (f" +{len(n) - 2}" if len(n) > 2 else "")
        shown = shown[:1].upper() + shown[1:]
        return "open", (f"{shown} open" if not es else f"{shown} abierto"), bool(cares)
    n = names(cares)
    shown = ", ".join(n[:2]) + (f" +{len(n) - 2}" if len(n) > 2 else "")
    return "care", (f"Care: {shown}" if not es else f"Cuidado: {shown}"), False


def _sentence(w: Dict[str, Any], lg: str) -> str:
    nm = topic_label(w["topic"], lg).lower()
    a, b = _md(w["start"], lg), _md(w["end"], lg)
    if lg == "es":
        return (f"Tu ventana de {nm} va del {a} al {b}." if w["kind"] == "open"
                else f"Un tramo de cuidado para {nm} va del {a} al {b}.")
    return (f"Your {nm} window runs {a} to {b}." if w["kind"] == "open" else f"A care stretch for {nm} runs {a} to {b}.")


def build_months(ws: List[Dict[str, Any]], today: date, topic: str, lang: str = "en") -> List[Dict[str, Any]]:
    lg = _lang(lang)
    out = []
    for y, m in month_list(today):
        a, b = _month_range(y, m)
        hit = [w for w in ws if _overlaps(w, a, b)]
        kind, text, care = _cell_text(hit, a, b, topic, lg)
        out.append({"key": f"{y}-{m:02d}", "month": MON[lg][m - 1], "year": y, "this_month": (y, m) == (today.year, today.month),
                    "kind": kind, "text": text, "care_too": care,
                    "lines": [_sentence(w, lg) for w in hit][:4],
                    "why": next((w["why"] for w in hit if w.get("why")), "")})
    return out


def _runs_len(w) -> int:
    return (w["end"] - w["start"]).days


def headline(ws: List[Dict[str, Any]], topic: str, lang: str = "en") -> Dict[str, str]:
    """{head, sub}: one plain sentence about the next 12 months."""
    lg = _lang(lang)
    es = lg == "es"
    sub = ("Cada cuadro es un mes. Toca uno para ver qué pasa." if es else "Each square is a month. Tap one to see what is happening.")
    if not ws:
        return {"head": ("Nada grande se abre ni se cierra en los próximos 12 meses." if es
                         else "Nothing big opens or closes in the next 12 months."), "sub": sub}
    opens = [w for w in ws if w["kind"] == "open"]
    cares = [w for w in ws if w["kind"] == "care"]
    parts = []
    nm = topic_label(topic, lg).lower()
    if opens:
        w = max(opens, key=lambda x: (_runs_len(x), -x["start"].toordinal()))
        who = (f"para {nm}" if es else f"for {nm}") if topic != "all" else (f"para {topic_label(w['topic'], lg).lower()}" if es
                                                                              else f"for {topic_label(w['topic'], lg).lower()}")
        parts.append((f"Tu mejor tramo {who} va de {_md(w['start'], lg)} a {_md(w['end'], lg)}." if es
                      else f"Your best stretch {who} runs {_md(w['start'], lg)} to {_md(w['end'], lg)}."))
    if cares:
        w = max(cares, key=lambda x: (_runs_len(x), -x["start"].toordinal()))
        who = (f"con {topic_label(w['topic'], lg).lower()}" if es else f"with {topic_label(w['topic'], lg).lower()}") if topic == "all" else ""
        parts.append((f"Cuidado {who} de {_md(w['start'], lg)} a {_md(w['end'], lg)}.".replace("  ", " ") if es
                      else f"Take care {who} from {_md(w['start'], lg)} to {_md(w['end'], lg)}.".replace("  ", " ")))
    return {"head": " ".join(parts), "sub": sub}


def build_moments(ws: List[Dict[str, Any]], today: date, lang: str = "en", limit: int = 6) -> List[Dict[str, Any]]:
    lg = _lang(lang)
    months = month_list(today)
    keys = {f"{y}-{m:02d}": i for i, (y, m) in enumerate(months)}
    out = []
    for w in sorted(ws, key=lambda x: (x["start"], x["end"])):
        if w["end"] <= today:                      # today-only windows already live on Home
            continue
        nm = topic_label(w["topic"], lg)
        title = (f"Ventana de {nm.lower()}" if w["kind"] == "open" else f"Cuidado con {nm.lower()}") if lg == "es" else \
                (f"{nm} window" if w["kind"] == "open" else f"Care with {nm.lower()}")
        first = max(w["start"], today)
        out.append({"title": title, "kind": w["kind"], "topic": w["topic"],
                    "range": f"{_md(w['start'], lg)} – {_md(w['end'], lg)}",
                    "start": w["start"].isoformat(), "end": w["end"].isoformat(),
                    "month_index": keys.get(f"{first.year}-{first.month:02d}", 0)})
    return out[:limit]


def build_year(feed: Optional[dict], topic: str, today: date, lang: str = "en") -> Dict[str, Any]:
    lg = _lang(lang)
    topic = topic if topic in ORDER else "all"
    ws = windows_from_feed(feed, topic)
    last = _month_range(*month_list(today)[-1])[1]
    ws = [w for w in ws if w["end"] >= today and w["start"] <= last]          # only what falls inside the 12 tiles
    h = headline(ws, topic, lg)
    return {"version": "coming-1", "view": "year", "topic": topic, "topics": chips(lg), "ask_moves": ASK_MOVES[lg],
            "today": today.isoformat(),
            "head": h["head"], "sub": h["sub"], "months": build_months(ws, today, topic, lg),
            "moments": build_moments(ws, today, lg), "quiet": not ws}


def build_chapter(phase: Optional[dict], today: date, lang: str = "en") -> Dict[str, Any]:
    """The chapter and its shifts as steps, in the engines' own words (phase_view): name, years, the energy line, what helps."""
    lg = _lang(lang)
    base = {"version": "coming-1", "view": "chapter", "today": today.isoformat(), "topics": [], "steps": [], "quiet": True}
    if not phase or not phase.get("available"):
        return {**base, "head": ("Aún no hay un capítulo para mostrar." if lg == "es" else "No chapter to show yet."), "sub": ""}
    ch, sh = phase.get("chapter") or {}, phase.get("shift") or {}
    end = str(ch.get("end") or "")[:4]
    nm = ch.get("plain_name") or ""
    head = ((f"Estás en un capítulo largo de {nm}, hasta {end}." if lg == "es" else f"You are in a long chapter of {nm}, running to {end}.")
            if nm and end else ("Tu capítulo actual" if lg == "es" else "Your current chapter"))
    sub = ch.get("line") or ""
    steps = []

    def step(x, now):
        s, e = str(x.get("start") or "")[:4], str(x.get("end") or "")[:4]
        yrs = (f"{'Ahora' if lg == 'es' else 'Now'} – {e}" if now else f"{s} – {e}")
        return {"years": yrs, "title": (x.get("plain_name") or "") + (" (etapa)" if lg == "es" else " shift"), "now": now,
                "meaning": x.get("line") or "", "helps": x.get("helps") or "", "watch": x.get("watch") or ""}
    if sh.get("plain_name"):
        steps.append(step(sh, True))
    for u in (phase.get("upcoming_shifts") or [])[:4]:
        if u.get("plain_name"):
            steps.append(step(u, False))
    return {**base, "head": head, "sub": sub, "steps": steps, "quiet": not steps}
