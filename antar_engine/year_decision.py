"""[year-decision 2026-10-10] One coherent, decision-shaped read of THIS YEAR, composed from the annual-plan payload.

Same shape as Today / This Month / Ask: prediction → why → holds → breaks → move. The annual payload's prose
fields contradict each other (live, 2026-10-10: theme "a year of expansion — opportunities open" next to year_theme
"guard your speculative bets"; quality "Expansion" next to year_quality "transformation"; year_summary "your money
is the strong axis" next to an event "Money comes under pressure — protect savings"). The STRUCTURED fields are
consistent, so this composes only from them: arcs (trend + when), events (polarity, month), the build / protect /
release lists, the running period, the year's end date. A solar-return year runs birthday to birthday, so by Oct 10
only weeks remain — the block says how many, and offers no move whose month is over. Deterministic; English only;
additive."""
from __future__ import annotations

from datetime import date, datetime
import re

from antar_engine import decision_i18n as I18

_MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

_TX = {
    "en": {
        "pred": "This year{left}: {bits}.", "rising": "{name} is rising", "pressure": "{name} comes under pressure",
        "wk": " ({n} week{s} left, to {end})", "ends": " (ends {end})", "peak": ", {when}",
        "holds": "It holds if you build on {x}.", "holds_none": "It holds if you put your effort where the year is rising.",
        "build_and": " and ", "brk": "It breaks if you take on {x}", "brk_none": "It breaks if you overreach where the year is under pressure",
        "lands": " \u2014 {when} is where the pressure lands.", "dot": ".",
        "conv": "Two timing systems agree on {x}{w}.", "conv_w": " ({w})",
        "move_before": "Before {end}: protect {x}.",
    },
    "es": {
        "pred": "Este a\u00f1o{left}: {bits}.", "rising": "{name} va en ascenso", "pressure": "{name} est\u00e1 bajo presi\u00f3n",
        "wk": " (quedan {n} semana{s}, hasta el {end})", "ends": " (termina el {end})", "peak": ", {when}",
        "holds": "Se sostiene si construyes sobre {x}.", "holds_none": "Se sostiene si pones tu esfuerzo donde el a\u00f1o va en ascenso.",
        "build_and": " y ", "brk": "Se rompe si cedes a {x}", "brk_none": "Se rompe si te excedes donde el a\u00f1o est\u00e1 bajo presi\u00f3n",
        "lands": " \u2014 {when} es donde cae la presi\u00f3n.", "dot": ".",
        "conv": "Dos sistemas de tiempos coinciden en {x}{w}.", "conv_w": " ({w})",
        "move_before": "Antes del {end}: protege {x}.",
    },
}


def _lower_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s else s


def _head(s: str) -> str:
    """The noun phrase before the first ' \u2014 ' of a build/protect/release line."""
    return (s or "").split(" \u2014 ")[0].strip().rstrip(".")


def _month_of(label: str, today: date):
    """'Oct 2026' / 'oct 2026' -> (date(2026,10,1), date(2026,10,31)); None if unparseable."""
    try:
        m, y = (label or "").replace(",", " ").split()[:2]
        key = m[:3].lower()
        mi = _MON.get(key) or I18.MONTH_NUM_ES.get(m.lower().rstrip(".")) or I18.MONTH_NUM_ES.get(key)
        yi = int(y)
        start = date(yi, mi, 1)
        end = date(yi + (mi == 12), (mi % 12) + 1, 1)
        return start, date.fromordinal(end.toordinal() - 1)
    except Exception:
        return None


def _end_date(p: dict):
    try:
        return date.fromisoformat(str(p.get("period_end"))[:10])
    except Exception:
        return None


def _when(a: dict, L: str):
    """The arc's 'when' phrase: English as shipped; Spanish only when it is the known 'peaks Mon YYYY' form."""
    w = a.get("when") or ""
    if L == "en":
        return w
    m = re.match(r"(?i)peaks\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", w)
    if m and m.group(1).title() in I18.MON_EN_ES:
        return f"con el pico en {I18.MON_EN_ES[m.group(1).title()]} {m.group(2)}"
    return ""


def _date_range_es(w: str):
    try:
        a, b = [date.fromisoformat(x.strip()[:10]) for x in w.split("\u2013")]
        if (a.year, a.month) == (b.year, b.month):
            return f"del {a.day} al {b.day} de {I18.MONTH_LONG['es'][b.month - 1]}"
        return f"del {I18.date_short(a, 'es')} al {I18.date_short(b, 'es')}"
    except Exception:
        return ""


def compose(p: dict, language: str = "en", today: date | None = None, period_line: str = ""):
    try:
        if language not in _TX or not isinstance(p, dict):
            return None
        L, tx = language, _TX[language]
        today = today or datetime.utcnow().date()
        arcs = [a for a in (p.get("arcs") or []) if a.get("trend") in ("rising", "pressure", "falling")]
        rising = [a for a in arcs if a["trend"] == "rising"]
        pressed = [a for a in arcs if a["trend"] in ("pressure", "falling")]
        if not arcs:
            return None

        def aname(a):
            return a["name"].lower() if L == "en" else I18.ARC[L].get(a.get("key"))
        if L != "en" and any(aname(a) is None for a in (rising[:2] + pressed[:2])):
            return None
        end = _end_date(p)
        left = ""
        if end and end >= today:
            wk = (end - today).days // 7
            e_txt = I18.date_short(end, L)
            left = (tx["wk"].format(n=wk, s=("s" if wk != 1 else ""), end=e_txt) if wk >= 1 else tx["ends"].format(end=e_txt))
        bits = []
        for a in rising[:2]:
            w = _when(a, L)
            bits.append(tx["rising"].format(name=aname(a)) + (tx["peak"].format(when=w) if w else ""))
        for a in pressed[:2]:
            w = _when(a, L)
            bits.append(tx["pressure"].format(name=aname(a)) + (tx["peak"].format(when=w) if w else ""))
        pred = tx["pred"].format(left=left, bits="; ".join(bits))

        why_bits = []
        if period_line:
            why_bits.append(period_line + ".")
        for d in (p.get("active_domains") or []):
            if d.get("convergence"):
                w = d.get("window") or ""
                if L == "en":
                    try:
                        a, b = [date.fromisoformat(x.strip()[:10]) for x in w.split("\u2013")]
                        w = f"{a.strftime('%b %-d')} to {b.strftime('%b %-d')}"
                    except Exception:
                        w = ""
                    label = (d.get("label") or "").lower()
                else:
                    w = _date_range_es(w)
                    label = I18.DOMAIN[L].get(d.get("key"))
                if label:
                    why_bits.append(tx["conv"].format(x=label, w=(tx["conv_w"].format(w=w) if w else "")))
                break
        if L == "en" and p.get("active"):
            why_bits.append(str(p["active"]).rstrip(".") + ".")      # the English prose line; no Spanish source for it
        why = " ".join(why_bits)

        def _ok(x):
            return bool(x) and (L == "en" or not _is_english(x))      # a missed translation is dropped, never shown
        build = [_head(x) for x in (p.get("build_this_year") or []) if _ok(x)][:2]
        protect = [_head(x) for x in (p.get("protect_this_year") or []) if _ok(x)][:1]
        release = [_head(x) for x in (p.get("release_this_year") or []) if _ok(x)][:1]
        holds = (tx["holds"].format(x=tx["build_and"].join(_lower_first(b) for b in build)) if build else tx["holds_none"])
        neg_when = next((e.get("date_label") for e in (p.get("events") or [])
                         if (e.get("polarity") or 0) < 0 and (_month_of(e.get("date_label"), today) or (None, date.min))[1] >= today), "")
        if L == "es" and neg_when:
            mo = _month_of(neg_when, today)
            neg_when = I18.month_year(mo[0], L) if mo else ""
        brk_target = release[0] if release else (protect[0] if protect else "")
        brk = (tx["brk"].format(x=_lower_first(brk_target)) if brk_target else tx["brk_none"])
        brk += tx["lands"].format(when=neg_when) if neg_when else tx["dot"]

        move = ""
        live_pos = []
        for e in (p.get("events") or []):
            mo = _month_of(e.get("date_label"), today)
            if mo and mo[1] >= today and (e.get("polarity") or 0) > 0:
                live_pos.append((mo[0], e))
        live_pos.sort(key=lambda x: x[0])
        if live_pos:
            e = live_pos[0][1]
            txt = e["text"]
            if not (L != "en" and _is_english(txt)):
                lab = e["date_label"]
                if L == "es":
                    mo = _month_of(lab, today)
                    lab = I18.month_year(mo[0], L) if mo else lab
                move = f"{lab}: {_lower_first(txt)}"
                move = move[:move.index(": ") + 2] + move[move.index(": ") + 2:].rstrip(".") + "."
        if not move and protect:
            move = tx["move_before"].format(end=I18.date_short(end, L) if end else "", x=_lower_first(protect[0]))
            if not end and L == "en":
                move = f"Before the year closes: protect {_lower_first(protect[0])}."
        out = {"prediction": pred, "why": why, "holds": holds, "breaks": brk, "move": move,
               "window": {"ends": end.isoformat() if end else None, "pressure_month": neg_when or None},
               "version": "year-decision-1"}
        return out if (pred and holds and brk) else None
    except Exception:
        return None


def _is_english(s: str) -> bool:
    from antar_engine.today_decision import _looks_english
    return _looks_english(s)


def merge_structure(es_payload: dict, en_payload: dict) -> dict:
    """The Spanish annual plan is generated separately and can carry no dated events / rising or pressured arcs
    (live, 2026-10-10: events [], every arc "steady"). The arcs, events, converging windows and year end are
    language-agnostic ENGINE output, so take them from the canonical (English) plan; keep the Spanish prose lists
    (build / protect / release). Returns a new dict; the payload actually sent is never modified."""
    out = dict(es_payload or {})
    for k in ("arcs", "events", "active_domains", "period_start", "period_end"):
        if (en_payload or {}).get(k):
            out[k] = en_payload[k]
    return out
