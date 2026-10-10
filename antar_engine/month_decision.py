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


def _fmt(s, e) -> str:
    if not s:
        return ""
    if not e or e == s:
        return s.strftime("%b %-d")
    return f"{s.strftime('%b %-d')} – {e.strftime('%b %-d')}"


def _text_dates(text: str, today: date):
    out = []
    for m in re.finditer(r"\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2})\b", (text or "").lower()):
        try:
            out.append(date(today.year, _MONTHS[m.group(1)], int(m.group(2))))
        except ValueError:
            pass
    return out


def _wk(x) -> dict:
    """best_week / caution_week arrive as {"label": ...} from the v2 overlay but as a legacy sentence
    ("Week of October 26 — your communication…") from GET /monthly-deepdive: normalise to {"label": ...}."""
    if isinstance(x, dict):
        return x
    if isinstance(x, str) and x.strip():
        return {"label": _lower_first(x.split(" \u2014 ")[0].strip())}
    return {}


def _range(p: dict) -> str:
    if p.get("range"):
        return str(p["range"]).title()
    a, b = _d(p.get("period_start")), _d(p.get("period_end"))
    return f"{a.strftime('%b %-d')} \u2013 {b.strftime('%b %-d')}" if a and b else ""


def _lower_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s else s


def compose(p: dict, language: str = "en", today: date | None = None, period_line: str = ""):
    try:
        if language != "en" or not isinstance(p, dict):
            return None
        today = today or datetime.utcnow().date()
        live = []
        for d in (p.get("active_domains") or []):
            s, e = _win(d.get("window") or "")
            if e and e < today:
                continue                       # that window is over — not advice any more
            live.append((d, s, e))
        # a domain whose own action is a restraint ("Delay any long trip…", "Cap your exposure…") is a CAUTION,
        # not something the month "favours" — whatever its transit polarity says
        restrain = {a.get("domain") for a in (p.get("priority_actions") or [])
                    if re.match(r"(?i)\s*(delay|hold|avoid|cap|skip|postpone|don't|do not|wait|pause|pull back)", a.get("action") or "")}
        lead = sorted([x for x in live if x[0].get("polarity") != "risk" and x[0].get("label") not in restrain],
                      key=lambda x: -float(x[0].get("score") or 0))[:2]
        if not lead:
            return None
        names = [x[0].get("label") or x[0].get("key") for x in lead]
        rng = _range(p)
        pred = f"This month ({rng or p.get('month')}) favours {' and '.join(n.lower() for n in names)}."
        lead_keys = [l[0] for l in lead]
        cautions = [x[0].get("label") for x in live if x[0] not in lead_keys
                    and (x[0].get("label") in restrain or x[0].get("caution"))][:2]
        if cautions:
            pred += f" {' and '.join(c.lower() for c in cautions).capitalize()} call{'s' if len(cautions) == 1 else ''} for caution."
        bw = _wk(p.get("best_week"))
        if bw.get("label"):
            pred += f" The strongest stretch is {bw['label']}."

        bits = []
        sp, wp = p.get("strong_planets") or [], p.get("weak_planets") or []
        if sp or wp:
            bits.append((f"{' and '.join(sp)} are strong this month" if sp else "")
                        + ("; " if sp and wp else "") + (f"{', '.join(wp[:-1]) + ' and ' + wp[-1] if len(wp) > 1 else wp[0]} are under strain" if wp else "") + ".")
        conv = [x[0].get("label") for x in lead if x[0].get("convergence")]
        if conv:
            bits.append(f"Two timing systems agree on {' and '.join(c.lower() for c in conv)}.")
        if period_line:
            bits.append(period_line + ".")
        why = " ".join(b[:1].upper() + b[1:] for b in bits)

        parts = []
        for d, s, e in lead:
            w = _fmt(s, e)
            parts.append(f"the {_NOUN.get(d.get('key'), d.get('label', '').lower())}" + (f" for {w}" if w else ""))
        holds = f"It holds if you time {' and '.join(parts)}"
        holds += (f"; the strongest week overall is {bw['label']}." if bw.get("label") else ".")

        cw = _wk(p.get("caution_week"))
        risky = [_RISK.get(x[0].get("key"), x[0].get("label", "").lower()) for x in live
                 if x[0] not in lead_keys and (x[0].get("label") in restrain or x[0].get("caution"))]
        brk = "It breaks if you commit to " + (" or ".join(risky[:2]) or "big commitments")
        brk += f" during {cw['label']}" if cw.get("label") else ""
        if re.search(r"(?i)overspend|spending", p.get("overview") or ""):
            brk += ", or let spending run ahead of income"
        brk += "."

        move = ""
        lead_labels = [n for n in names]
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
