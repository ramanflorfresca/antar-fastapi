"""[month-decision 2026-10-10] One coherent, decision-shaped read of THIS MONTH, composed from the monthly payload.

Same shape as Today / Ask: prediction → why → holds → breaks → move. The monthly payload's own fields can
disagree (theme "a steady month — small moves outpace big bets" next to month_theme "one needs a bold push";
domains "Money is quiet" next to a "lock in a payout Oct 14–23" action) and can offer advice whose date has already
passed (live: "cap your exposure … before October 8" shown on October 10). This keeps ONLY what is still
actionable today and composes one answer from structured fields (active_domains, best/caution week,
priority_actions, planet strength, running period). Deterministic; English only; additive."""
from __future__ import annotations

import re
from datetime import date, datetime

from antar_engine import decision_i18n as I18

_NOUN = {"money": "savings or payout decision", "work": "visible work", "travel": "trip planning",
         "speculation": "bet sizing", "relationship": "important conversation", "family": "family matters",
         "health": "health routine", "home": "home and property decisions", "authority": "authority or legal matters"}
_RISK = {"travel": "long trips", "speculation": "speculative bets", "work": "overcommitting at work",
         "money": "big purchases", "relationship": "a hard conversation"}
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], 1)}


def _d(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _win(w: str):
    parts = [x.strip() for x in re.split(r"\s+[–\-]\s+", w or "") if x.strip()]
    s = _d(parts[0]) if parts else None
    e = _d(parts[-1]) if parts else None
    return s, e


_TX = {
    "en": {
        "pred": "This month ({rng}) favours {names}.", "caution": "{x} call{s} for caution.",
        "best": "The strongest stretch is {bw}.",
        "strong": "{x} are strong this month", "weak": "{x} are under strain",
        "conv": "Two timing systems agree on {x}.",
        "holds": "It holds if you time {parts}", "for": " for {w}", "and": " and ",
        "holds_bw": "; the strongest week overall is {bw}.", "holds_end": ".",
        "brk": "It breaks if you commit to {risky}", "brk_none": "big commitments", "or": " or ",
        "during": " during {cw}", "spend": ", or let spending run ahead of income", "brk_end": ".",
        "spend_rx": r"(?i)overspend|spending",
        "restrain_rx": r"(?i)\s*(delay|hold|avoid|cap|skip|postpone|don't|do not|wait|pause|pull back)",
    },
    "es": {
        "pred": "Este mes ({rng}) favorece {names}.", "caution": "Ten cautela con {x}.",
        "best": "El tramo m\u00e1s fuerte es {bw}.",
        "strong": "{x} est\u00e1n fuertes este mes", "weak": "{x} est\u00e1n bajo tensi\u00f3n",
        "conv": "Dos sistemas de tiempos coinciden en {x}.",
        "holds": "Se sostiene si programas {parts}", "for": " {w}", "and": " y ",
        "holds_bw": "; la mejor semana en conjunto es {bw}.", "holds_end": ".",
        "brk": "Se rompe si te comprometes con {risky}", "brk_none": "compromisos grandes", "or": " o ",
        "during": " durante {cw}", "spend": ", o dejas que el gasto se adelante a los ingresos", "brk_end": ".",
        "spend_rx": r"(?i)gast|sobregast|derroch",
        "restrain_rx": r"(?i)\s*(retrasa|posterga|pospon|posp\u00f3n|aplaza|evita|limita|frena|espera|pausa|salta|det\u00e9n|no\s|"
                       r"mant[e\u00e9]n (?:bajo|limit)|reduce)",
    },
}


def _fmt(s, e, L="en") -> str:
    if not s:
        return ""
    if not e or e == s:
        return I18.date_short(s, L)
    return f"{I18.date_short(s, L)} \u2013 {I18.date_short(e, L)}"


def _fmt_for(s, e, L) -> str:
    """window text inside 'for …': en 'Oct 14 \u2013 Oct 23'; es 'del 14 oct al 23 oct'."""
    if L == "es" and s and e and e != s:
        if (s.year, s.month) == (e.year, e.month):
            return f"del {s.day} al {e.day} de {I18.MONTH_LONG['es'][e.month - 1]}"
        return f"del {I18.date_short(s, L)} al {I18.date_short(e, L)}"
    if L == "es" and s:
        return f"el {I18.date_short(s, L)}"
    return _fmt(s, e, L)


def _text_dates(text: str, today: date):
    out = []
    t = (text or "").lower()
    for m in re.finditer(r"\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2})\b", t):
        try:
            out.append(date(today.year, _MONTHS[m.group(1)], int(m.group(2))))
        except ValueError:
            pass
    for m in re.finditer(r"\b(\d{1,2})\s+(?:de\s+)?(" + "|".join(sorted(I18.MONTH_NUM_ES, key=len, reverse=True)) + r")\b", t):
        try:
            out.append(date(today.year, I18.MONTH_NUM_ES[m.group(2)], int(m.group(1))))
        except ValueError:
            pass
    return out


def _week_of_es(head: str) -> str:
    """'week of October 26' / 'Week of Oct 26' (English legacy sentence head) -> 'la semana del 26 de octubre'."""
    m = re.match(r"(?i)week of ([a-z]+)\.? (\d{1,2})", head or "")
    if not m:
        return head
    key = m.group(1).lower()[:3]
    mi = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}.get(key)
    return f"la semana del {int(m.group(2))} de {I18.MONTH_LONG['es'][mi - 1]}" if mi else head


def _wk(x, L="en") -> dict:
    """best_week / caution_week arrive as {"label": ...} from the v2 overlay but as a legacy sentence
    ("Week of October 26 \u2014 your communication\u2026" / "Semana del 26 de octubre \u2014 \u2026") from GET
    /monthly-deepdive: normalise to {"label": ...}."""
    if isinstance(x, dict):
        lab = x.get("label")
        if L == "es" and lab:
            lab = I18.es_label(lab)
            lab = ("la semana del " + lab) if not lab.lower().startswith("semana") else _lower_first("la " + lab)
        return {"label": lab} if lab else {}
    if isinstance(x, str) and x.strip():
        head = _lower_first(x.split(" \u2014 ")[0].strip())
        if L == "es":
            head = "la " + head if head.startswith("semana") else _week_of_es(head)
            if re.search(r"(?i)\bweek\b", head):          # unknown English phrasing: omit rather than leak
                return {}
        return {"label": head}
    return {}


def _range(p: dict, L="en") -> str:
    if p.get("range") and L == "en":
        return str(p["range"]).title()
    a, b = _d(p.get("period_start")), _d(p.get("period_end"))
    return f"{I18.date_short(a, L)} \u2013 {I18.date_short(b, L)}" if a and b else (str(p.get("range") or "").title() if L == "en" else "")


def _lower_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s else s


def compose(p: dict, language: str = "en", today: date | None = None, period_line: str = ""):
    try:
        if language not in _TX or not isinstance(p, dict):
            return None
        L, tx = language, _TX[language]
        today = today or datetime.utcnow().date()
        live = []
        for d in (p.get("active_domains") or []):
            s, e = _win(d.get("window") or "")
            if e and e < today:
                continue                       # that window is over — not advice any more
            live.append((d, s, e))
        # a domain whose own action is a restraint ("Delay any long trip\u2026", "Cap your exposure\u2026") is a CAUTION,
        # not something the month "favours" — whatever its transit polarity says
        restrain = {a.get("domain") for a in (p.get("priority_actions") or [])
                    if re.match(tx["restrain_rx"], a.get("action") or "")}
        lead = sorted([x for x in live if x[0].get("polarity") != "risk" and x[0].get("label") not in restrain],
                      key=lambda x: -float(x[0].get("score") or 0))[:2]
        if not lead:
            return None

        def dname(d):
            return (d.get("label") or d.get("key") or "").lower() if L == "en" else I18.DOMAIN[L].get(d.get("key"))
        names = [dname(x[0]) for x in lead]
        if not all(names):
            return None
        rng = _range(p, L)
        pred = tx["pred"].format(rng=rng or p.get("month"), names=I18.join_list(names, L) if L != "en" else " and ".join(names))
        lead_keys = [l[0] for l in lead]
        cautions = [x[0] for x in live if x[0] not in lead_keys
                    and (x[0].get("label") in restrain or x[0].get("caution"))][:2]
        if cautions:
            if L == "en":
                pred += f" {' and '.join((c.get('label') or '').lower() for c in cautions).capitalize()} call{'s' if len(cautions) == 1 else ''} for caution."
            else:
                cn = [I18.DOMAIN[L].get(c.get("key")) for c in cautions]
                if all(cn):
                    pred += " " + tx["caution"].format(x=I18.join_list(cn, L))
        bw = _wk(p.get("best_week"), L)
        if bw.get("label"):
            pred += " " + tx["best"].format(bw=bw["label"])

        bits = []
        sp, wp = p.get("strong_planets") or [], p.get("weak_planets") or []
        pn = (lambda n: n) if L == "en" else (lambda n: I18.planet(n, L))
        if sp or wp:
            if L == "en":
                bits.append((f"{' and '.join(sp)} are strong this month" if sp else "")
                            + ("; " if sp and wp else "") + (f"{', '.join(wp[:-1]) + ' and ' + wp[-1] if len(wp) > 1 else wp[0]} are under strain" if wp else "") + ".")
            else:
                bits.append((tx["strong"].format(x=I18.join_list([pn(x) for x in sp], L)) if sp else "")
                            + ("; " if sp and wp else "") + (tx["weak"].format(x=I18.join_list([pn(x) for x in wp], L)) if wp else "") + ".")
        conv = [dname(x[0]) for x in lead if x[0].get("convergence")]
        if conv:
            bits.append(tx["conv"].format(x=I18.join_list(conv, L) if L != "en" else " and ".join(conv)))
        if period_line:
            bits.append(period_line + ".")
        why = " ".join(b[:1].upper() + b[1:] for b in bits)

        parts = []
        for d, s, e in lead:
            w = _fmt_for(s, e, L)
            noun = (_NOUN.get(d.get("key"), (d.get("label") or "").lower()) if L == "en"
                    else I18.DOMAIN_NOUN[L].get(d.get("key"), dname(d)))
            parts.append((f"the {noun}" if L == "en" else noun) + (tx["for"].format(w=w) if w else ""))
        holds = tx["holds"].format(parts=tx["and"].join(parts))
        holds += (tx["holds_bw"].format(bw=bw["label"]) if bw.get("label") else tx["holds_end"])

        cw = _wk(p.get("caution_week"), L)
        risky = [(_RISK if L == "en" else I18.DOMAIN_RISK[L]).get(x[0].get("key"),
                  (x[0].get("label") or "").lower() if L == "en" else None) for x in live
                 if x[0] not in lead_keys and (x[0].get("label") in restrain or x[0].get("caution"))]
        risky = [r for r in risky if r]
        brk = tx["brk"].format(risky=tx["or"].join(risky[:2]) or tx["brk_none"])
        brk += tx["during"].format(cw=cw["label"]) if cw.get("label") else ""
        if re.search(tx["spend_rx"], p.get("overview") or ""):
            brk += tx["spend"]
        brk += tx["brk_end"]

        move = ""
        lead_labels = [x[0].get("label") for x in lead]
        acts = [a for a in (p.get("priority_actions") or []) if a.get("action")]
        acts.sort(key=lambda a: (a.get("domain") not in lead_labels,))
        for a in acts:
            ds = _text_dates(a["action"], today)
            if ds and max(ds) < today:
                continue
            move = a["action"].strip()
            break
        out = {"prediction": pred, "why": why, "holds": holds, "breaks": brk, "move": move,
               "window": {"best_week": bw.get("label"), "caution_week": cw.get("label")},
               "version": "month-decision-1"}
        return out if (holds and brk) else None
    except Exception:
        return None
