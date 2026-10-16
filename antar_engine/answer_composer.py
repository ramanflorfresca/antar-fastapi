"""[answer-composer 2026-10-16] ONE way to answer a question about one area of the reader's life, the way an astrologer would:
  verdict (what the chart says about the thing asked) -> because (the plain cause) -> when (dates from the SAME windows and day
  scores the screens show) -> do / avoid (one concrete step).
No disclaimer step: the care is the advice, drawn from the chart (a health read says to make health the focus and get regular checkups;
a legal read says paperwork and partnership matters are showing and to be careful what is signed). Crisis is the one exception and is
never routed here.

Pure functions. The topic adapters take the numbers the existing engines already return (health.py, legal.py, speculation_policy.py,
the period reads and the day areas) and shape them into one `facts` dict; `compose` turns facts into the Ask-shaped answer. Nothing is
invented: a topic with no real read returns None and the question stays with the full Ask.

facts = {topic, verdict_plain, because_plain, windows: [{kind: open|care, start, end}], do_plain, avoid_plain, scope}
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Dict, List, Optional

# the understanding layer's area -> the composer's topic
TOPIC_OF = {
    "health_self": "health", "legal_case": "legal",
    "speculation_betting": "speculation",
    "income_money": "money", "business_venture": "money", "clients_sales": "money", "funding_investment": "money",
    "debt_owed_money": "money",
    "career_job": "career", "promotion": "career",
    "new_romance": "love", "existing_relationship": "love", "family": "love",
    "purpose_spiritual": "mind",
}
PERIOD_DOMAIN = {"money": "money", "career": "career", "love": "love", "mind": "mind", "health": "health"}
ROUTED_INTENTS = ("how", "when", "what_to_do", "open", "which")

MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}
TX = {
    "en": {"scope": {"day": "today", "week": "this week", "month": "this month", "year": "this year"},
           "until": "This stretch runs until {d}.", "next_open": "The next open stretch starts {d}.",
           "next_care": "The stretch to be most careful in is {d}.", "year_care": "The most sensitive stretch is around {y}.",
           "health_focus": "Your chart asks you to put your health first {scope}.",
           "health_steady": "Your health looks steady {scope}; keep the basics going.",
           "health_because": "It points to {nature}{body}, and it reads as {kind}.",
           "body_with": ", with {body} most exposed",
           "kind_chronic": "a long-term tendency to manage", "kind_acute": "something passing, not structural",
           "health_do": "{care}, and keep regular medical checkups.",
           "legal_showing": "Legal and paperwork matters are showing {scope}{about}.",
           "legal_quiet": "No strong legal pressure shows {scope}.",
           "legal_about": ", tied to {cause}",
           "legal_lean": "If one comes up, the chart leans {lean}; preparation turns a lean into a result.",
           "lean": {"favourable": "your way", "contested": "both ways", "unfavourable": "against you"},
           "legal_do": "Be careful what you sign, and keep every step correct and documented.",
           "legal_avoid": "Don't rush into a contract or let paperwork slide.",
           "moves": "Your move: {x}"},
    "es": {"scope": {"day": "hoy", "week": "esta semana", "month": "este mes", "year": "este año"},
           "until": "Este tramo dura hasta el {d}.", "next_open": "El próximo tramo abierto empieza el {d}.",
           "next_care": "El tramo en que más cuidado tener es {d}.", "year_care": "El tramo más sensible es alrededor de {y}.",
           "health_focus": "Tu carta te pide poner tu salud primero {scope}.",
           "health_steady": "Tu salud se ve estable {scope}; sigue con lo básico.",
           "health_because": "Apunta a {nature}{body}, y se lee como {kind}.",
           "body_with": ", con {body} como lo más expuesto",
           "kind_chronic": "una tendencia de largo plazo que conviene manejar", "kind_acute": "algo pasajero, no estructural",
           "health_do": "{care}, y mantén chequeos médicos regulares.",
           "legal_showing": "Asuntos legales y de papeleo se asoman {scope}{about}.",
           "legal_quiet": "No se ve una presión legal fuerte {scope}.",
           "legal_about": ", ligados a {cause}",
           "legal_lean": "Si surge uno, la carta se inclina {lean}; la preparación convierte una inclinación en un resultado.",
           "lean": {"favourable": "a tu favor", "contested": "en ambos sentidos", "unfavourable": "en tu contra"},
           "legal_do": "Ten cuidado con lo que firmas y mantén cada paso correcto y documentado.",
           "legal_avoid": "No te apresures con un contrato ni dejes el papeleo para después.",
           "moves": "Tu paso: {x}"},
}


def _lang(l) -> str:
    return "es" if str(l or "en").lower().startswith("es") else "en"


def scope_for(horizon_days) -> str:
    """The reading that answers the question's own horizon."""
    try:
        h = int(horizon_days)
    except (TypeError, ValueError):
        return "month"
    return "day" if h <= 1 else "week" if h <= 7 else "month" if h <= 45 else "year"


def plan(u: Optional[dict]) -> Optional[dict]:
    """{topic, scope} for a confidently-read question about the reader's own life, or None (the full Ask answers)."""
    if not isinstance(u, dict) or u.get("crisis"):
        return None
    if u.get("intent") not in ROUTED_INTENTS or float(u.get("confidence") or 0) < 0.5:
        return None
    if u.get("subject") not in (None, "self"):
        return None
    topic = TOPIC_OF.get(u.get("area"))
    if not topic:
        return None
    return {"topic": topic, "scope": scope_for(u.get("horizon_days")), "gambling": bool(u.get("gambling"))}


def _d(x) -> Optional[date]:
    try:
        return date.fromisoformat(str(x)[:10])
    except Exception:
        return None


def _fmt(d: date, lg: str, today: date) -> str:
    base = f"{d.day} {MON[lg][d.month - 1]}" if lg == "es" else f"{MON[lg][d.month - 1]} {d.day}"
    if d.year != today.year or (d - today).days > 183:
        return f"{base} {d.year}" if lg == "es" else f"{base}, {d.year}"
    return base


def when_sentence(windows: List[dict], today: date, lang: str, prefer: str = "care") -> Optional[str]:
    """Where the reader stands today and what comes next, from dated windows (open / care)."""
    lg = _lang(lang)
    t = TX[lg]
    ws = []
    for w in windows or []:
        s, e = _d(w.get("start")), _d(w.get("end"))
        if s and e and e >= today and w.get("kind") in ("open", "care"):
            ws.append((s, e, w["kind"]))
    ws.sort()
    if not ws:
        return None
    on = next((w for w in ws if w[0] <= today <= w[1]), None)
    if on:
        return t["until"].format(d=_fmt(on[1], lg, today))
    nxt = next((w for w in ws if w[2] == prefer), ws[0])
    key = "next_open" if nxt[2] == "open" else "next_care"
    # a year-wide window reads as "around 2027", not "Jan 1, 2027"
    if (nxt[1] - nxt[0]).days >= 330:
        return t["year_care"].format(y=nxt[0].year)
    return t[key].format(d=_fmt(nxt[0], lg, today) + (f" – {_fmt(nxt[1], lg, today)}" if nxt[1] != nxt[0] else ""))


# ── topic adapters: the existing engines' numbers -> one facts dict ──────────────────────────────────────────────
_AYUR = re.compile(r"\s*[;,]?\s*in Ayurveda.*$", re.I)


def _plain_care(s: str) -> str:
    """The first clause of the engine's care line, without the herb/method tail ("; in Ayurveda, ...")."""
    s = _AYUR.sub("", s or "").strip().rstrip(".")
    return s[:1].upper() + s[1:] if s else ""


def health_facts(health: dict, timing: dict, scope: str, today: date, lang: str = "en") -> Optional[dict]:
    """health = health.analyze_health(); timing = health.health_timing()."""
    lg = _lang(lang)
    t = TX[lg]
    if not isinstance(health, dict) or not health.get("available"):
        return None
    wins = [{"kind": "care", "start": w.get("start"), "end": w.get("end"), "year": w.get("year")}
            for w in (timing or {}).get("windows") or []]
    near = [w for w in wins if (_d(w["end"]) or date.min) >= today and (_d(w["start"]) or date.max) <= today + timedelta(days=548)]
    level = (health.get("constitution") or {}).get("level")
    nature = (health.get("nature") or [None])[0]
    care = _plain_care((health.get("care") or [""])[0])
    sc = t["scope"][scope]
    if level == "robust" and not near:
        return {"topic": "health", "scope": scope, "verdict_plain": t["health_steady"].format(scope=sc), "because_plain": None,
                "windows": wins, "do_plain": care or None, "avoid_plain": None}
    chronic = (health.get("chronic") or {}).get("is_chronic")
    ailment, _, body = (nature or "").partition(" — ")
    because = (t["health_because"].format(nature=ailment.strip(), body=(t["body_with"].format(body=body.strip()) if body.strip() else ""),
                                          kind=t["kind_chronic"] if chronic else t["kind_acute"])
               if nature else None)
    return {"topic": "health", "scope": scope, "verdict_plain": t["health_focus"].format(scope=sc), "because_plain": because,
            "windows": wins, "do_plain": t["health_do"].format(care=care) if care else None, "avoid_plain": None}


def legal_facts(legal: dict, timing: dict, scope: str, today: date, lang: str = "en") -> Optional[dict]:
    lg = _lang(lang)
    t = TX[lg]
    if not isinstance(legal, dict) or not legal.get("available"):
        return None
    wins = [{"kind": "care", "start": w.get("start"), "end": w.get("end")} for w in (timing or {}).get("windows") or []]
    near = [w for w in wins if (_d(w["end"]) or date.min) >= today and (_d(w["start"]) or date.max) <= today + timedelta(days=548)]
    level = (legal.get("propensity") or {}).get("level")
    showing = bool(near) or level in ("high", "elevated")
    cause = (legal.get("likely_causes") or [None])[0]
    sc = t["scope"][scope]
    if not showing:
        return {"topic": "legal", "scope": scope, "verdict_plain": t["legal_quiet"].format(scope=sc), "because_plain": None,
                "windows": wins, "do_plain": t["legal_do"], "avoid_plain": None}
    lean = (legal.get("outcome") or {}).get("lean")
    return {"topic": "legal", "scope": scope,
            "verdict_plain": t["legal_showing"].format(scope=sc, about=(t["legal_about"].format(cause=cause) if cause else "")),
            "because_plain": t["legal_lean"].format(lean=t["lean"].get(lean, t["lean"]["contested"])) if lean else None,
            "windows": wins, "do_plain": t["legal_do"], "avoid_plain": None}


def period_facts(domain: Optional[dict], best: Optional[dict], avoid: Optional[dict], topic: str, scope: str) -> Optional[dict]:
    """A period read's own area paragraph (verdict, support, catch, step, window all in one) is already the whole answer."""
    if not isinstance(domain, dict) or not domain.get("paragraph"):
        return None
    return {"topic": topic, "scope": scope, "preset_read": domain["paragraph"], "windows": [], "do_plain": None, "avoid_plain": None}


def compose(facts: Optional[dict], today: date, lang: str = "en") -> Optional[dict]:
    """The Ask-shaped answer, or None when there is nothing real to say."""
    if not facts:
        return None
    lg = _lang(lang)
    t = TX[lg]
    if facts.get("preset_read"):
        read = facts["preset_read"]
    else:
        parts = [facts.get("verdict_plain"), facts.get("because_plain"),
                 when_sentence(facts.get("windows") or [], today, lg), facts.get("avoid_plain")]
        read = " ".join(p for p in parts if p)
    if not read:
        return None
    return {"mode": "explore", "locked": False, "source": "composer", "route": facts["scope"], "area": facts["topic"],
            "read": read, "next": facts.get("do_plain") or ""}
