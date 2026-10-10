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

_MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _lower_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s else s


def _head(s: str) -> str:
    """The noun phrase before the first ' — ' of a build/protect/release line."""
    return (s or "").split(" — ")[0].strip().rstrip(".")


def _month_of(label: str, today: date):
    """'Oct 2026' -> (date(2026,10,1), date(2026,10,31)); None if unparseable."""
    try:
        m, y = (label or "").replace(",", " ").split()[:2]
        mi, yi = _MON[m[:3].lower()], int(y)
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


def compose(p: dict, language: str = "en", today: date | None = None, period_line: str = ""):
    try:
        if language != "en" or not isinstance(p, dict):
            return None
        today = today or datetime.utcnow().date()
        arcs = [a for a in (p.get("arcs") or []) if a.get("trend") in ("rising", "pressure", "falling")]
        rising = [a for a in arcs if a["trend"] == "rising"]
        pressed = [a for a in arcs if a["trend"] in ("pressure", "falling")]
        if not arcs:
            return None
        end = _end_date(p)
        left = ""
        if end and end >= today:
            wk = (end - today).days // 7
            left = (f" ({wk} week{'s' if wk != 1 else ''} left, to {end.strftime('%b %-d')})" if wk >= 1
                    else f" (ends {end.strftime('%b %-d')})")
        bits = []
        for a in rising[:2]:
            bits.append(f"{a['name'].lower()} is rising" + (f", {a['when']}" if a.get("when") else ""))
        for a in pressed[:2]:
            bits.append(f"{a['name'].lower()} comes under pressure" + (f", {a['when']}" if a.get("when") else ""))
        pred = f"This year{left}: " + "; ".join(bits) + "."

        why_bits = []
        if period_line:
            why_bits.append(period_line + ".")
        conv = [d.get("label") for d in (p.get("active_domains") or []) if d.get("convergence")]
        for d in (p.get("active_domains") or []):
            if d.get("convergence"):
                w = d.get("window") or ""
                try:
                    a, b = [date.fromisoformat(x.strip()[:10]) for x in w.split("\u2013")]
                    w = f"{a.strftime('%b %-d')} to {b.strftime('%b %-d')}"
                except Exception:
                    w = ""
                why_bits.append(f"Two timing systems agree on {d['label'].lower()}" + (f" ({w})." if w else "."))
                break
        if p.get("active"):
            why_bits.append(str(p["active"]).rstrip(".") + ".")
        why = " ".join(why_bits)

        build = [_head(x) for x in (p.get("build_this_year") or []) if x][:2]
        protect = [_head(x) for x in (p.get("protect_this_year") or []) if x][:1]
        release = [_head(x) for x in (p.get("release_this_year") or []) if x][:1]
        if build:
            holds = "It holds if you build on " + " and ".join(_lower_first(b) for b in build) + "."
        else:
            holds = "It holds if you put your effort where the year is rising."
        neg_when = next((e.get("date_label") for e in (p.get("events") or [])
                         if (e.get("polarity") or 0) < 0 and (_month_of(e.get("date_label"), today) or (None, date.min))[1] >= today), "")
        brk_target = release[0] if release else (protect[0] if protect else "")
        brk = ("It breaks if you take on " + _lower_first(brk_target) if brk_target else "It breaks if you overreach where the year is under pressure")
        brk += f" — {neg_when} is where the pressure lands." if neg_when else "."

        move = ""
        live_pos = []
        for e in (p.get("events") or []):
            mo = _month_of(e.get("date_label"), today)
            if mo and mo[1] >= today and (e.get("polarity") or 0) > 0:
                live_pos.append((mo[0], e))
        live_pos.sort(key=lambda x: x[0])
        if live_pos:
            e = live_pos[0][1]
            move = f"{e['date_label']}: {_lower_first(e['text'])}"
            move = move[:move.index(": ") + 2] + move[move.index(": ") + 2:].rstrip(".") + "."
        elif protect:
            move = f"Before {end.strftime('%b %-d') if end else 'the year closes'}: protect {_lower_first(protect[0])}."
        out = {"prediction": pred, "why": why, "holds": holds, "breaks": brk, "move": move,
               "window": {"ends": end.isoformat() if end else None, "pressure_month": neg_when or None},
               "version": "year-decision-1"}
        return out if (pred and holds and brk) else None
    except Exception:
        return None
