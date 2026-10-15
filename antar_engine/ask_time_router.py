"""
Time-aware answers for ANY topic: "how is money tomorrow?", "is Friday good for a launch?", "how are the next 4 days for my health?",
"which day this month is best for a pitch?".

The message is read by the shared understanding layer (understand.py: area, intent, horizon, start offset, crisis and gambling flags);
this module only decides WHICH engine answers and shapes the answer. The authority for a day is the daily engine for that date: each
day's result already carries a read for every area of life, so a day's answer here can never disagree with the Today view for that
date. A "best day" question scans the days with the same engine. Nothing here predicts anything itself.

Rules:
  * crisis is never routed; yes/no questions stay with the yes/no engine; anything this cannot place returns None and the full Ask runs
  * a gambling / speculation question always carries the guardrail: timing guidance, not a promise; risk only what can be lost
  * one best and one care day, never an hour-by-hour strip
Pure functions; fail-open (None) on any missing field.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Dict, List, Optional

# a cheap pre-filter so the (model-backed) reading is only paid for when a time word is present (EN / ES / PT)
TIME_HINT = re.compile(
    r"(?i)\b(today|tonight|tomorrow|day after tomorrow|this (week|weekend|month)|next (\d+|few|two|three|four|five|six|seven) days?|"
    r"coming days|best day|which day|what day|good day|bad day|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"hoy|esta noche|mañana|pasado mañana|esta semana|este mes|próximos? (\d+|dos|tres|cuatro|cinco|seis|siete) días|mejor día|qué día|"
    r"hoje|amanhã|esta semana|este mês|próximos? (\d+) dias|melhor dia|que dia)\b")

# the understanding layer's area -> the daily engine's own area key. Areas with their own safeguards (an ex, a separation, a
# marriage, a child's conception, a lost item, retirement) are NOT here: they stay with the full Ask.
AREA_DOMAIN = {
    "career_job": "work", "promotion": "work",
    "business_venture": "money", "clients_sales": "money", "funding_investment": "money", "income_money": "money", "debt_owed_money": "money",
    "speculation_betting": "speculation",
    "property": "home", "residence_move": "home",
    "foreign_travel_visa": "travel",
    "new_romance": "relationship", "existing_relationship": "relationship",
    "children_wellbeing": "family", "family": "family",
    "health_self": "health", "purpose_spiritual": "spiritual", "legal_case": "authority",
}
ROUTED_INTENTS = ("how", "when", "what_to_do", "open", "which")
MAX_BEST_DAYS = 31

TX = {
    "en": {"today": "Today", "tomorrow": "Tomorrow",
           "good": "supportive", "steady": "quiet", "mixed": "mixed", "tough": "take care",
           "g": "{d} supports {say}.", "s": "{d} is quiet for {say}: nothing pushes either way.",
           "t": "{d} is a day to take care with {say}.",
           "best_w": "Your best window is {w}.", "avoid_w": "Keep clear of {w} for anything that matters.",
           "step_g": "Use it for the move you have been putting off.", "step_s": "Keep to routine steps; nothing needs forcing.",
           "step_t": "Keep commitments light and double-check before you agree to anything.",
           "range": "{lines}", "range_best": "Best: {b}.", "range_care": "Take care: {c}.",
           "best_day": "The best day for {say} is {d}.", "care_day": "Take care on {d}.",
           "no_best": "No day stands out for {say}; the steadiest is {d}.",
           "range_step": "Keep the moves that matter for {d}.",
           "guard": "This is timing guidance, not a promise: risk only what you can afford to lose."},
    "es": {"today": "Hoy", "tomorrow": "Mañana",
           "good": "favorable", "steady": "tranquilo", "mixed": "mixto", "tough": "con cuidado",
           "g": "{d} favorece {say}.", "s": "{d} es tranquilo para {say}: nada empuja en ningún sentido.",
           "t": "{d} es un día para tener cuidado con {say}.",
           "best_w": "Tu mejor ventana es {w}.", "avoid_w": "Evita {w} para lo que importa.",
           "step_g": "Úsalo para el paso que has estado posponiendo.", "step_s": "Quédate con lo rutinario; nada necesita forzarse.",
           "step_t": "Mantén los compromisos ligeros y revisa dos veces antes de aceptar algo.",
           "range": "{lines}", "range_best": "Mejor: {b}.", "range_care": "Con cuidado: {c}.",
           "best_day": "El mejor día para {say} es {d}.", "care_day": "Con cuidado el {d}.",
           "no_best": "Ningún día destaca para {say}; el más estable es {d}.",
           "range_step": "Deja lo importante para {d}.",
           "guard": "Esto es una guía de tiempos, no una promesa: arriesga solo lo que puedas perder."},
}
WD = {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]}
MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}


def _lang(l) -> str:
    return "es" if str(l or "en").lower().startswith("es") else "en"


def day_label(d: date, today: date, lang: str) -> str:
    t = TX[lang]
    if d == today:
        return t["today"]
    if d == today + timedelta(days=1):
        return t["tomorrow"]
    return f"{WD[lang][d.weekday()]} {MON[lang][d.month - 1]} {d.day}" if lang == "en" else f"{WD[lang][d.weekday()]} {d.day} {MON[lang][d.month - 1]}"


def plan(u: Optional[dict], question: str, today: date) -> Optional[dict]:
    """What to answer and for which dates, or None to leave the question to the full Ask."""
    # `needs_clarification` is not a blocker here: a short question like "how is money tomorrow" is flagged by the reader even though
    # its area and day are clear; what matters is that an area, an intent and a horizon were read.
    if not isinstance(u, dict) or u.get("crisis"):
        return None
    if u.get("intent") not in ROUTED_INTENTS or float(u.get("confidence") or 0) < 0.5:
        return None
    domain = AREA_DOMAIN.get(u.get("area"))
    if not domain or u.get("subject") not in (None, "self"):
        return None
    hz, off = u.get("horizon_days"), u.get("start_offset_days") or 0
    if hz is None or hz > MAX_BEST_DAYS or off > MAX_BEST_DAYS:
        return None
    gamble = bool(u.get("gambling")) or domain == "speculation"
    if u.get("intent") in ("when", "which"):
        span = max(hz, 7)
        return {"mode": "best", "domain": domain, "gamble": gamble,
                "dates": [today + timedelta(days=off + i) for i in range(min(span, MAX_BEST_DAYS))]}
    if hz <= 1:
        return {"mode": "day", "domain": domain, "gamble": gamble, "dates": [today + timedelta(days=off)]}
    return {"mode": "range", "domain": domain, "gamble": gamble, "dates": [today + timedelta(days=off + i) for i in range(min(hz, 7))]}


# the five areas the Today detail shows (daily payload `domains`: work, body, mind, money, people)
STRIP = {"work": "work", "money": "money", "health": "body", "relationship": "people", "family": "people"}
_STATE_TONE = {"favorable": "good", "rising": "good", "steady": "steady", "volatile": "mixed", "caution": "tough"}
_MAP_TONE = {"opportunity": "good", "risk": "tough"}
_RANK = {"good": 3, "steady": 2, "mixed": 1, "tough": 0}


def area_view(daily: dict, domain: str, prefer_map: bool = False) -> Optional[dict]:
    """The day's own read of an area: {line, tone, label}. For the five areas the Today detail shows, that detail's own line and state
    (so the answer agrees with it); for the others (speculation, travel, home, ...), the day's area line from `day_map`."""
    if not isinstance(daily, dict):
        return None
    key = STRIP.get(domain)
    if key and not prefer_map:
        for e in daily.get("domains") or []:
            if isinstance(e, dict) and e.get("key") == key and e.get("line"):
                return {"line": e["line"], "tone": _STATE_TONE.get(str(e.get("state")), "steady"), "label": e.get("label")}
    for e in daily.get("day_map") or []:
        if isinstance(e, dict) and e.get("key") == domain and e.get("line"):
            return {"line": e["line"], "tone": _MAP_TONE.get(str(e.get("tone")), "steady"), "label": e.get("label")}
    return None


def retime(line: str, d: date, today: date, lang: str) -> str:
    """The daily engine writes every day's lines in the present ("... today"). For another date the word is changed to that date's own
    ("tomorrow", "that day") so the answer does not say "today" about Friday."""
    if not isinstance(line, str) or d == today:
        return line
    tomorrow = d == today + timedelta(days=1)
    if lang == "es":
        word = "mañana" if tomorrow else "ese día"
        return re.sub(r"(?i)\bhoy\b", word, line)
    word = "tomorrow" if tomorrow else "that day"
    out = re.sub(r"(?i)\btoday's\b", word + "'s" if tomorrow else "that day's", line)
    return re.sub(r"(?i)\btoday\b", word, out)


def _say(domain: str, lang: str) -> str:
    return {"en": {"money": "money and income", "work": "your work", "speculation": "a venture or a risk",
                   "home": "home and property", "travel": "travel", "relationship": "a close relationship", "family": "family",
                   "health": "your health", "spiritual": "your inner life", "authority": "legal and official matters"},
            "es": {"money": "el dinero", "work": "tu trabajo", "speculation": "una apuesta o riesgo", "home": "el hogar",
                   "travel": "viajes", "relationship": "una relación cercana", "family": "la familia", "health": "tu salud",
                   "spiritual": "tu vida interior", "authority": "lo legal y oficial"}}[lang].get(domain, "this")


def _window(daily: dict) -> Dict[str, str]:
    w = ((daily or {}).get("decision") or {}).get("window") or {}
    return {k: v for k, v in (("best", w.get("best")), ("avoid", w.get("avoid"))) if isinstance(v, str) and v.strip()}


def compose(pl: dict, per_day: Dict[date, dict], today: date, language: str = "en") -> Optional[dict]:
    """The Ask-shaped answer for a plan, from the per-date daily results. None when no usable day came back."""
    lang = _lang(language)
    t = TX[lang]
    rows = []
    for d in pl["dates"]:
        daily = per_day.get(d)
        if isinstance(daily, dict) and not daily.get("pending"):
            v = area_view(daily, pl["domain"], prefer_map=pl["gamble"] and pl["domain"] == "speculation")
            if v:
                v = {**v, "line": retime(v["line"], d, today, lang)}
                rows.append({"date": d, "daily": daily, "v": v, "tone": v["tone"], "rank": (_RANK[v["tone"]], float(daily.get("score") or 0))})
    if not rows:
        return None
    say = _say(pl["domain"], lang)
    guard = t["guard"] if pl["gamble"] else ""
    name = lambda r: day_label(r["date"], today, lang)
    # inside a sentence "today" / "tomorrow" read lower-case; a weekday date keeps its capital
    mid = lambda r: (lambda x: x.lower() if r["date"] in (today, today + timedelta(days=1)) else x)(name(r))
    if pl["mode"] == "day":
        r = rows[0]
        read = r["v"]["line"]
        w = _window(r["daily"])
        if w.get("best") and r["tone"] in ("good", "steady"):
            read += " " + t["best_w"].format(w=w["best"])
        if w.get("avoid"):
            read += " " + t["avoid_w"].format(w=w["avoid"])
        nxt = t[{"good": "step_g", "steady": "step_s", "mixed": "step_t", "tough": "step_t"}[r["tone"]]]
    elif pl["mode"] == "range":
        lines = " ".join(f"{name(r)}: {t[r['tone']]}." for r in rows)
        goods = [r for r in rows if r["tone"] == "good"]
        toughs = [r for r in rows if r["tone"] == "tough"]
        best = max(goods, key=lambda r: r["rank"]) if goods else None
        care = min(toughs, key=lambda r: r["rank"]) if toughs else None
        read = lines + (" " + t["range_best"].format(b=mid(best)) if best else "") + (" " + t["range_care"].format(c=mid(care)) if care else "")
        nxt = t["range_step"].format(d=mid(best)) if best else t["step_s"]
    else:   # best day among the scanned days
        goods = [r for r in rows if r["tone"] == "good"]
        toughs = [r for r in rows if r["tone"] == "tough"]
        care = min(toughs, key=lambda r: r["rank"]) if toughs else None
        if goods:
            b = max(goods, key=lambda r: r["rank"])
            read = t["best_day"].format(say=say, d=mid(b)) + " " + b["v"]["line"]
            nxt = t["range_step"].format(d=mid(b))
        else:
            b = max(rows, key=lambda r: (r["rank"], -r["date"].toordinal()))
            read = t["no_best"].format(say=say, d=mid(b))
            nxt = t["step_s"]
        if care:
            read += " " + t["care_day"].format(d=mid(care))
    if guard:
        read += " " + guard
        if pl["mode"] != "day" or rows[0]["tone"] != "good":
            nxt = guard
    return {"mode": "explore", "locked": False, "source": "daily_days", "route": pl["mode"], "area": pl["domain"],
            "read": read, "next": nxt}
