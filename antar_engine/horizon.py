"""[horizon 2026-10-13] The Home card at three distances: today, this month, this year.

Every distance answers the same questions in the same order, so there is nothing to learn twice:
    do · don't · coming up (dated) · watch out + how to avoid it · how to make it work · why · what is further ahead
plus a short conversational card (an opener and three questions that open Ask).

Nothing new is computed. Each block is re-shaped from what the product already returns: the daily signal (today), the
monthly deep-dive (month) and the annual plan (year), each with its `decision` object (prediction / why / holds / breaks /
move), and the Windows feed for "further ahead". Sentences are the engines' own; the only text written here is a few
fixed labels and question templates (en/es). Pure functions, never raise on missing data."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

SCOPES = ("today", "month", "year")

_T = {
    "en": {
        "today": "Today", "month": "This month", "year": "This year",
        "best_window": "Best window", "steer_clear": "Steer clear", "strongest_week": "Strongest week", "caution_week": "Caution week",
        "avoid_window": "Stay out of {w} for big decisions and tense conversations.",
        "next": "Next: {t}", "ahead": "Further ahead: {t}", "care": "care",
        "q_focus": {"today": "What is the one thing I should focus on today?", "month": "What is the one thing I should focus on this month?",
                    "year": "What is the one thing I should focus on this year?"},
        "opener": {"today": "Want to talk today through? Ask me anything about it.",
                   "month": "Want to talk this month through? Ask me anything about it.",
                   "year": "Want to talk this year through? Ask me anything about it."},
        "to": "To {d}", "focus": "Focus on: ", "letgo": "Let go of: ",
    },
    "es": {
        "today": "Hoy", "month": "Este mes", "year": "Este año",
        "best_window": "Mejor ventana", "steer_clear": "Evita", "strongest_week": "Semana más fuerte", "caution_week": "Semana de cuidado",
        "avoid_window": "Evita {w} para decisiones importantes y conversaciones tensas.",
        "next": "Siguiente: {t}", "ahead": "Más adelante: {t}", "care": "cuidado",
        "q_best": "¿Cómo aprovecho mejor {t}?", "q_care": "¿Cómo paso {t}?",
        "q_focus": {"today": "¿En qué debo enfocarme hoy?", "month": "¿En qué debo enfocarme este mes?",
                    "year": "¿En qué debo enfocarme este año?"},
        "opener": {"today": "¿Quieres hablar de hoy? Pregúntame lo que quieras.",
                   "month": "¿Quieres hablar de este mes? Pregúntame lo que quieras.",
                   "year": "¿Quieres hablar de este año? Pregúntame lo que quieras."},
        "to": "Hasta {d}", "focus": "Enf\u00f3cate en: ", "letgo": "Suelta: ",
    },
}
_MON = {"en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")}
_CARE_WORDS = re.compile(r"(?i)pressure|risk|protect|postpone|caution|careful|strain|presión|riesgo|prote|pospon|cuidado|tensi")
_AVOID_START = re.compile(r"(?i)^(delay|avoid|don'?t|do not|hold off|skip|postpone|pause|retrasa|evita|no |pospon|espera)")


def _lang(language) -> str:
    return "es" if str(language or "en").lower().startswith("es") else "en"


def _s(x) -> str:
    return re.sub(r"\s+", " ", x).strip() if isinstance(x, str) else ""


def _cap(x: str) -> str:
    return x[:1].upper() + x[1:] if x else x


def _uniq(items, n: int = 2) -> List[str]:
    seen, out = set(), []
    for x in items:
        t = _s(x)
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(_cap(t))
    return out[:n]


def _dt(s) -> Optional[date]:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _fmt(d: Optional[date], lg: str) -> str:
    if not d:
        return ""
    return f"{d.day} {_MON[lg][d.month - 1]}" if lg == "es" else f"{_MON[lg][d.month - 1]} {d.day}"


def _far(feed: Optional[dict], lg: str, scope: str) -> str:
    """One line about what lies beyond this distance, from the Windows feed's next open / care windows."""
    t = _T[lg]
    nxt = next((w for w in (feed or {}).get("next") or [] if w.get("kind") == "open"), None)
    care = next((w for w in (feed or {}).get("care") or []), None)
    bits = []
    for w, is_care in ((nxt, False), (care, True)):
        if not w:
            continue
        s, e = _dt(w.get("start")), _dt(w.get("end"))
        if not s or not e:
            continue
        lab = (_s(w.get("label")) or _cap(_s(w.get("topic")))).lower()
        rng = f"{_fmt(s, lg)} \u2013 {_fmt(e, lg)}, {s.year}"
        if lg == "es":
            bits.append(f"{'cuidado con' if is_care else 'ventana de'} {lab}: {rng}")
        else:
            bits.append(f"care with {lab}: {rng}" if is_care else f"{lab} window: {rng}")
    if not bits:
        return ""
    return (t["ahead"] if scope == "year" else t["next"]).format(t="; ".join(bits[:2]))


def _is_clock(w: str) -> bool:
    return bool(re.search(r"\d:\d\d", w or ""))


def _chip(kind: str, c: Dict[str, Any], lg: str) -> str:
    title, when = _s(c.get("title")), _s(c.get("when"))
    yearlike = bool(re.search(r"\d{4}", title))
    if lg == "es":
        if kind == "good":
            return (f"\u00bfC\u00f3mo aprovecho {when}?" if _is_clock(when) else f"\u00bfQu\u00e9 debo hacer en {title}?" if yearlike
                    else f"\u00bfC\u00f3mo uso la {title.lower()}, {when}?")
        return (f"\u00bfQu\u00e9 debo evitar entre {when}?" if _is_clock(when) else f"\u00bfQu\u00e9 hago con {title}?" if yearlike
                else f"\u00bfQu\u00e9 debo evitar en la {title.lower()}, {when}?")
    if kind == "good":
        return (f"What is the best use of {when}?" if _is_clock(when) else f"What should I do in {title}?" if yearlike
                else f"How should I use the {title.lower()}, {when}?")
    return (f"What should I avoid between {when}?" if _is_clock(when) else f"What should I do about {title}?" if yearlike
            else f"What should I avoid in the {title.lower()}, {when}?")


def _converse(scope: str, coming: List[Dict[str, Any]], lg: str) -> Dict[str, Any]:
    t = _T[lg]
    good = next((c for c in coming if c["kind"] == "good"), None)
    care = next((c for c in coming if c["kind"] == "care"), None)
    chips = []
    if good:
        chips.append(_chip("good", good, lg))
    if care:
        chips.append(_chip("care", care, lg))
    chips.append(t["q_focus"][scope])
    return {"opener": t["opener"][scope], "chips": chips[:3]}


_GREET = {"en": {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening"},
          "es": {"morning": "Buenos d\u00edas", "afternoon": "Buenas tardes", "evening": "Buenas noches"}}
_WEEKDAY = {"en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
            "es": ("lunes", "martes", "mi\u00e9rcoles", "jueves", "viernes", "s\u00e1bado", "domingo")}
_MONTH = {"en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
          "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")}


def greeting(first_name: Optional[str], local_now: datetime, language: str = "en", season: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Every Home screen opens with a greeting made for THIS person: their first name, the right part of their day, the date, and
    where they are in their running season ("Month 3 of your Ambition season"). Deterministic; no model call. The name is used
    exactly as stored (never guessed); with no name the greeting simply drops it."""
    lg = _lang(language)
    h = local_now.hour
    part = "morning" if 5 <= h < 12 else "afternoon" if 12 <= h < 17 else "evening"
    name = _s(first_name).split(" ")[0] if _s(first_name) else ""
    text = f"{_GREET[lg][part]}, {name}" if name else _GREET[lg][part]
    d = local_now.date()
    date_txt = (f"{_WEEKDAY[lg][d.weekday()]}, {d.day} de {_MONTH[lg][d.month - 1]}" if lg == "es"
                else f"{_WEEKDAY[lg][d.weekday()]}, {_MONTH[lg][d.month - 1]} {d.day}")
    out: Dict[str, Any] = {"text": text + ("." if False else ""), "date": date_txt, "part": part, "name": name or None, "context": ""}
    try:
        if season and season.get("start") and season.get("title"):
            s = _dt(season["start"])
            if s and s <= d:
                months = (d.year - s.year) * 12 + (d.month - s.month) + 1
                out["context"] = (f"Mes {months} de tu {season['title'].lower()}" if lg == "es"
                                  else f"Month {months} of your {season['title'].lower()}")
    except Exception:
        pass
    return out


def _empty(scope: str, lg: str) -> Dict[str, Any]:
    return {"version": "horizon-1", "scope": scope, "available": False, "label": _T[lg][scope]}


def _finish(scope: str, lg: str, **kw) -> Dict[str, Any]:
    out = {"version": "horizon-1", "scope": scope, "available": True, "label": _T[lg][scope], **kw}
    out["converse"] = _converse(scope, out.get("coming") or [], lg)
    return out


def build_today(signal: Optional[dict], feed: Optional[dict], language: str = "en", tone_word: str = "",
                when: str = "", show_windows: bool = True) -> Dict[str, Any]:
    lg = _lang(language)
    sig = signal or {}
    dec = sig.get("decision") or {}
    if not dec and not sig.get("do_today") and not sig.get("headline"):
        return _empty("today", lg)
    t = _T[lg]
    coming = []
    for w in sig.get("windows") or []:
        if w.get("kind") in ("best", "avoid") and w.get("start") and w.get("end"):
            coming.append({"kind": "good" if w["kind"] == "best" else "care",
                           "title": t["best_window"] if w["kind"] == "best" else t["steer_clear"],
                           "when": f"{w['start']} – {w['end']}", "text": _s(w.get("text"))})
    coming.sort(key=lambda c: c["kind"] != "good")
    if not show_windows:                 # the generic Abhijit / Rahu Kalam pair is not personal; Home hides it unless switched on
        coming = []
    aw = next((c["when"] for c in coming if c["kind"] == "care"), "")
    # A quiet day has no decision object (the engine will not invent one). Fall back to the daily signal's own lines.
    hora = sig.get("hora") if isinstance(sig.get("hora"), dict) else {}
    short = _s(dec.get("prediction")) or _s(sig.get("headline"))
    watch = _s(dec.get("breaks")) or (("Avoid " + _s(hora.get("avoid_what")) + ".") if _s(hora.get("avoid_what")) else "")
    work = _s(dec.get("holds")) or ((_cap(_s(hora.get("best_for"))) + ".") if _s(hora.get("best_for")) else "")
    why = _s(dec.get("why")) or (f"The Moon is in {_s(sig.get('moon_sign'))}, in {_s(sig.get('moon_nakshatra'))}."
                                  if sig.get("moon_sign") and sig.get("moon_nakshatra") and lg == "en" else "")
    # The "read": the day's own lead line, body and move, for the Home read (no model call; the daily engine's own sentences).
    lead = _s(sig.get("verdict_subline")) or _s(sig.get("headline")) or short
    read = {"headline": lead, "body": _s(sig.get("wow")) or short, "move": _s(sig.get("signal")) or (_s(dec.get("move"))),
            "window": next((c["when"] for c in coming if c["kind"] == "good"), "")}
    from antar_engine import brief as _brief
    return _finish("today", lg, read=read, areas=_brief.build_areas(sig), when=when, tone=tone_word, short=short,
                   do=_uniq([*(sig.get("do_today") or []), dec.get("move"), *(sig.get("aligned_for") or [])]),
                   dont=_uniq([*(sig.get("dont_today") or []), *(sig.get("friction_for") or [])]),
                   coming=coming, watch=watch,
                   avoid=(t["avoid_window"].format(w=aw) if aw else ""),
                   work=work, why=why, far=_far(feed, lg, "today"))


def _split_week(txt: str) -> Dict[str, str]:
    """'Week of October 26 — your communication ...' -> when / text."""
    a, _, b = _s(txt).partition(" — ")
    return {"when": _cap(a), "text": _cap(b)} if b else {"when": "", "text": _cap(a)}


def build_month(month: Optional[dict], feed: Optional[dict], language: str = "en") -> Dict[str, Any]:
    lg = _lang(language)
    m = month or {}
    dec = m.get("decision") or {}
    if not dec:
        return _empty("month", lg)
    t = _T[lg]
    acts = [a for a in (m.get("priority_actions") or []) if isinstance(a, dict) and _s(a.get("action"))]
    coming = []
    for key, kind, title in (("best_week", "good", t["strongest_week"]), ("caution_week", "care", t["caution_week"])):
        w = _split_week(m.get(key)) if m.get(key) else None
        if w:
            coming.append({"kind": kind, "title": title, **w})
    start, end = _dt(m.get("period_start")), _dt(m.get("period_end"))
    when = f"{_fmt(start, lg)} – {_fmt(end, lg)}" if start and end else _s(m.get("month"))
    avoid = next((a["action"] for a in acts if _AVOID_START.match(_s(a["action"]))), "")
    return _finish("month", lg, when=when, tone=_cap(_s(m.get("energy_level"))), short=_s(dec.get("prediction")),
                   do=_uniq([a["action"] for a in acts if not _AVOID_START.match(_s(a["action"]))] + [dec.get("move")]),
                   dont=(_uniq([a["action"] for a in acts if _AVOID_START.match(_s(a["action"]))])
                         or _uniq([dec.get("breaks")])),
                   coming=coming, watch=_s(dec.get("breaks")), avoid=_s(avoid),
                   work=_s(dec.get("holds")), why=_s(dec.get("why")), far=_far(feed, lg, "month"))


def build_year(year: Optional[dict], feed: Optional[dict], language: str = "en") -> Dict[str, Any]:
    lg = _lang(language)
    y = year or {}
    dec = y.get("decision") or {}
    if not dec:
        return _empty("year", lg)
    t = _T[lg]
    dates = [c for c in (y.get("critical_dates") or []) if isinstance(c, dict) and _s(c.get("event"))]
    good = [c for c in dates if not _CARE_WORDS.search(c["event"])]
    care = [c for c in dates if _CARE_WORDS.search(c["event"])]
    coming = []
    for c in good[:1]:
        coming.append({"kind": "good", "title": _s(c.get("date")), "when": "", "text": _s(c["event"])})
    for c in care[:2]:
        coming.append({"kind": "care", "title": _s(c.get("date")), "when": "", "text": _s(c["event"])})
    end = _dt(y.get("period_end"))
    prot = [x for x in (y.get("protect_this_year") or []) if _s(x)]
    rel = [x for x in (y.get("release_this_year") or []) if _s(x)]
    return _finish("year", lg, when=(t["to"].format(d=_fmt(end, lg)) if end else ""),
                   tone=_cap(_s(y.get("quality") or y.get("year_quality"))), short=_s(dec.get("prediction")),
                   do=[f"{t['focus']}{x[:1].lower() + x[1:]}" for x in _uniq(y.get("build_this_year") or [])],
                   dont=[f"{t['letgo']}{x[:1].lower() + x[1:]}" for x in _uniq(rel)],
                   coming=coming, watch=_s(dec.get("breaks")), avoid=_s(prot[0] if prot else (rel[0] if rel else "")),
                   work=_s(dec.get("holds")), why=_s(dec.get("why")), far=_far(feed, lg, "year"))
