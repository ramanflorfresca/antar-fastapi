"""
antar_engine/speculation_days.py — which day this week suits a (small, capped)
speculative move, picked from the SAME per-day data the Today screen shows.

[spec-days-from-today 2026-10-03] Owner: day and crypto traders plan by day. Live
inconsistency found while comparing with a rival app: the speculation answer said
"Friday 9 Oct is your clearest day" while Today's own data for 9 Oct read
"Neutral — lighter-touch day, skip the big moves", and Today's money line for 3 Oct
said "hold off on speculative money moves". Two calculations, two answers.
Now day-level speculation answers come from daily-week only.

Rule (deterministic, no model):
  score = tier (High 3 · Good 2 · Neutral 1 · Caution 0)
          − 1 if the day's money line says hold off / timing isn't with you
          + 0.5 if it says tailwind / chase payments
  best  = highest score, earliest on ties (needs score >= 2, else "no standout day")
  avoid = lowest score if it is Caution or a hold-off day and differs from best
The caller adds the unearned-gains window as context. Gambling never reaches here.
"""
from __future__ import annotations

import re
from typing import Optional

_TIER = {"high": 3, "good": 2, "neutral": 1, "caution": 0,
         # localized labels the daily-week endpoint may return
         "alto": 3, "alta": 3, "bueno": 2, "buena": 2, "bom": 2, "boa": 2, "neutro": 1, "neutra": 1,
         "precaución": 0, "precaucao": 0, "precaução": 0, "cautela": 0}
_NEG = re.compile(r"(?i)hold off|isn'?t with you|not with you|avoid|espera|evita|n[aã]o [eé] o momento|"
                  r"el momento no|aguarde|evite")
_POS = re.compile(r"(?i)tailwind|chase payments|favou?r|viento a favor|vento a favor")

_MONTH = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
          "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]}


def _l(language: str) -> str:
    l = (language or "en").lower()[:2]
    return l if l in ("es", "pt") else "en"


def tier(day: dict) -> int:
    return _TIER.get(str(day.get("verdict_label") or "").strip().lower(), 1)


def money_line(day: dict) -> str:
    for h in day.get("highlights") or []:
        if h.get("domain") == "money":
            return str(h.get("text") or "")
    return ""


def score(day: dict) -> float:
    s = float(tier(day))
    m = money_line(day)
    if m and _NEG.search(m):
        s -= 1
    elif m and _POS.search(m):
        s += 0.5
    return s


def peak(day: dict) -> str:
    for w in day.get("windows") or []:
        if w.get("type") == "peak" or w.get("kind") == "best":
            a, b = w.get("start"), w.get("end")
            if a and b:
                return f"{a}–{b}"
    return ""


_WEEKDAY = {"en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
            "pt": ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]}


def label(day: dict, language: str = "en") -> str:
    """'Sunday 4 Oct' from the date. FULL weekday names, from our own table: the
    abbreviation 'Sun' is a banned planet word and the output scrub rewrote it to
    'your identity and authority energy 4 Oct' (live dry run)."""
    d = str(day.get("date") or "")
    try:
        import datetime as _dt
        y, m, dd = (int(x) for x in d.split("-"))
        lg = _l(language)
        return f"{_WEEKDAY[lg][_dt.date(y, m, dd).weekday()]} {dd} {_MONTH[lg][m - 1]}"
    except Exception:
        return d


def pick(days: list) -> dict:
    """{'best': day|None, 'avoid': day|None}"""
    days = [d for d in (days or []) if isinstance(d, dict) and d.get("date")]
    if not days:
        return {"best": None, "avoid": None}
    ranked = sorted(days, key=lambda d: (-score(d), d["date"]))
    best = ranked[0] if score(ranked[0]) >= 2 else None
    worst = sorted(days, key=lambda d: (score(d), d["date"]))[0]
    avoid = worst if (score(worst) <= 0 and worst is not best) else None
    return {"best": best, "avoid": avoid}


_T = {
    "en": {
        "best": "Best day this week for a small, capped speculative move: {d}{w}.",
        "best_w": " — strongest window {w}",
        "avoid": " Most strained: {d} — sit that one out.",
        "none": "No standout day this week for speculation — every day is low-conviction, so keep any move very small.",
        "day_good": "{d} reads as a supportive day{w} — small, capped positions only.",
        "day_flat": "{d} is a lighter-touch day — if you trade at all, keep it small.",
        "day_bad": "{d} is a strained day for money moves — sit it out.",
        "next": "Pick one day, write your loss limit first, and stop when you reach it.",
    },
    "es": {
        "best": "Mejor día de esta semana para un movimiento especulativo pequeño y con tope: {d}{w}.",
        "best_w": " — mejor ventana {w}",
        "avoid": " El más tenso: {d} — mejor no operar.",
        "none": "Esta semana no hay un día destacado para especular — todos son de baja convicción, así que mantén cualquier movimiento muy pequeño.",
        "day_good": "{d} se lee como un día favorable{w} — solo posiciones pequeñas y con tope.",
        "day_flat": "{d} es un día de toque ligero — si operas, que sea pequeño.",
        "day_bad": "{d} es un día tenso para movimientos de dinero — mejor no operar.",
        "next": "Elige un día, escribe primero tu límite de pérdida y detente al llegar a él.",
    },
    "pt": {
        "best": "Melhor dia desta semana para um movimento especulativo pequeno e com teto: {d}{w}.",
        "best_w": " — melhor janela {w}",
        "avoid": " O mais tenso: {d} — melhor ficar de fora.",
        "none": "Esta semana não há um dia de destaque para especular — todos são de baixa convicção, então mantenha qualquer movimento bem pequeno.",
        "day_good": "{d} aparece como um dia favorável{w} — só posições pequenas e com teto.",
        "day_flat": "{d} é um dia de toque leve — se for operar, que seja pequeno.",
        "day_bad": "{d} é um dia tenso para movimentos de dinheiro — melhor ficar de fora.",
        "next": "Escolha um dia, anote primeiro seu limite de perda e pare ao atingi-lo.",
    },
}


def week_answer(days: list, language: str = "en") -> Optional[dict]:
    """{'read','next','timing'} for 'which day this week…', or None without data."""
    p = pick(days)
    if not any(isinstance(d, dict) and d.get("date") for d in (days or [])):
        return None
    T = _T[_l(language)]
    if p["best"]:
        pk = peak(p["best"])
        read = T["best"].format(d=label(p["best"], language),
                                w=T["best_w"].format(w=pk) if pk else "")
        if p["avoid"]:
            read += T["avoid"].format(d=label(p["avoid"], language))
        return {"read": read, "next": T["next"], "timing": label(p["best"], language)}
    return {"read": T["none"], "next": T["next"], "timing": ""}


def specific_day(days: list, which: str, language: str = "en") -> Optional[dict]:
    """'today' | 'tomorrow' → that day's speculation read from the same data."""
    ds = [d for d in (days or []) if isinstance(d, dict) and d.get("date")]
    idx = {"today": 0, "tomorrow": 1}.get(which)
    if idx is None or len(ds) <= idx:
        return None
    d, T = ds[idx], _T[_l(language)]
    s = score(d)
    pk = peak(d)
    w = f" ({pk})" if pk else ""
    if s <= 0:
        key = "day_bad"
    elif s >= 2:
        key = "day_good"
    else:
        key = "day_flat"
    return {"read": T[key].format(d=label(d, language), w=w), "next": T["next"], "timing": label(d, language)}


_TOMORROW = re.compile(r"(?i)\b(tomorrow|ma[nñ]ana|amanh[aã]|kal)\b")
_TODAY = re.compile(r"(?i)\b(today|tonight|hoy|esta noche|hoje|esta noite|aaj)\b")


def which_day(question: str) -> Optional[str]:
    """'tomorrow' | 'today' | None (→ the week)."""
    q = question or ""
    if _TOMORROW.search(q):
        return "tomorrow"
    if _TODAY.search(q):
        return "today"
    return None
