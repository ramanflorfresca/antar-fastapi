"""[today-decision 2026-10-10] One coherent, decision-shaped read of TODAY, composed from the daily payload itself.

The Today payload carries dozens of fields written by different layers (headline / verdict_label / highlight /
signal / wow …) and they can disagree on the same day — "Good" next to "Mixed day", a travel headline over a
work evidence lead. This composes ONE answer in the shape the product now uses everywhere:

    prediction  → what today favours, and what needs care
    why         → the named facts behind it (Moon's star + when it turns, the house it lights, the running period)
    holds       → what makes the day work (usually: WHEN to commit)
    breaks      → what spoils it
    move        → one action, with its time

Deterministic: no LLM, no new astrology — every clause is read from fields the engine already computed
(evidence.chosen, moon_shift, signals, hora/rahu_kalam windows, haz_hoy, dont_today). English only; other
languages keep the existing fields and get no `decision` (wrong-language text is worse than none)."""
from __future__ import annotations

from antar_engine import decision_i18n as I18

_LABEL = {
    "work": "work and reputation", "network": "income and your network", "money": "money",
    "father": "fortune, mentors and the long view", "body": "health and energy",
    "relationship": "close relationships", "family": "family", "travel": "travel", "home": "home and property",
}

_TX = {
    "en": {
        "pos": "Today favours {lead}.",
        "neg": "Today is a hold day for {lead} \u2014 protect what you have rather than push.",
        "then": ", then ", "and": " and ",
        "care1": "{x} needs care.", "careN": "{x} need care.",
        "overreach": "Watch for taking on too much at work.",
        "light": "It's a lighter-touch day: steady progress, not big bets.",
        "moon_shift": "The Moon is in {sign}, in {nak} ({qb}) until {at}, then {to} ({qa}).",
        "moon": "The Moon is in {sign}, in {nak}.",
        "house": "It lights your {h} house ({lit}).",
        "dasha": "You're running {v}{d}.",
        "holds_up": "It holds if you prepare before {at} and commit after it, when the Moon's star turns in your favour{best}.",
        "holds_up_best": "; the sharpest single hour for an ask or a pitch is {best}",
        "holds_dn": "It holds if you commit before {at}, while the Moon's star still favours you, and keep the afternoon light.",
        "holds_best": "It holds if the decision that matters goes {between}.",
        "holds_none": "It holds if you keep to steady, ordinary work.",
        "brk": "It breaks if you force a decision or a hard conversation{avoid}",
        "brk_dont": ", or {dont}", "brk_end": ".",
        "w_after": "After {at}", "w_before": "Before {at}", "w_today": "Today",
        "between": "between {a} and {b}", "move": "{when}, {item}.",
        "wk_work": "visibility and reputation", "wk_prep": "{when}, draft the ask or pitch you will send on Monday \u2014 prepare today, don't send it.",
        "wk_holds": "It holds if you do the thinking and drafting {between}, and send nothing until Monday.",
    },
    "es": {
        "pos": "Hoy favorece {lead}.",
        "neg": "Hoy es un d\u00eda de pausa para {lead}: protege lo que tienes en lugar de forzar.",
        "then": ", y luego ", "and": " y ",
        "care1": "{x} necesita cuidado.", "careN": "{x} necesitan cuidado.",
        "overreach": "Cuida no asumir demasiado en el trabajo.",
        "light": "Es un d\u00eda de toque ligero: avance constante, sin grandes apuestas.",
        "moon_shift": "La Luna est\u00e1 en {sign}, en {nak} ({qb}) hasta las {at}, y luego en {to} ({qa}).",
        "moon": "La Luna est\u00e1 en {sign}, en {nak}.",
        "house": "Ilumina tu casa {h} ({lit}).",
        "dasha": "Est\u00e1s en el periodo {v}{d}.",
        "holds_up": "Se sostiene si preparas antes de las {at} y te comprometes despu\u00e9s, cuando la estrella de la Luna cambia a tu favor{best}.",
        "holds_up_best": "; la mejor hora para pedir o proponer algo es {best}",
        "holds_dn": "Se sostiene si te comprometes antes de las {at}, mientras la estrella de la Luna a\u00fan te favorece, y mantienes la tarde ligera.",
        "holds_best": "Se sostiene si la decisi\u00f3n importante va {between}.",
        "holds_none": "Se sostiene si te mantienes en un trabajo constante y ordinario.",
        "brk": "Se rompe si fuerzas una decisi\u00f3n o una conversaci\u00f3n dif\u00edcil{avoid}",
        "brk_dont": ". Y recuerda: {dont}", "brk_end": ".",
        "w_after": "A partir de las {at}", "w_before": "Antes de las {at}", "w_today": "Hoy",
        "between": "entre {a} y {b}", "move": "{when}, {item}.",
        "wk_work": "la visibilidad y la reputaci\u00f3n", "wk_prep": "{when}, redacta la petici\u00f3n o propuesta que enviar\u00e1s el lunes: prep\u00e1rala hoy, no la env\u00edes.",
        "wk_holds": "Se sostiene si piensas y redactas {between}, y no env\u00edas nada hasta el lunes.",
    },
}

import re as _re
from datetime import date as _date

# a move line that already names a time ("before noon", "after 2 PM") must not get a window stuck in front of it
_HAS_TIME = _re.compile(r"(?i)\b\d{1,2}(:\d{2})?\s?(am|pm|h)\b|\b(noon|midday|midnight|mediod[i\u00ed]a|medianoche)\b")
# a move that is about contacting someone at work/senior — not something to do on a weekend
_CONTACT = _re.compile(r"(?i)decision-?maker|client|senior|boss|manager|reach out|pitch|ask\b|negotiat|"
                       r"tomador de decisiones|cliente|jefe|contacta|contacto|llama|escribe|escr[i\u00ed]ba|habla con|pide|solicita|propuesta|negoci")


def _is_weekend(p: dict) -> bool:
    try:
        return _date.fromisoformat(str(p.get("date"))[:10]).weekday() >= 5
    except Exception:
        return str(p.get("day") or "").strip().lower() in ("saturday", "sunday", "s\u00e1bado", "sabado", "domingo")

_EN_WORDS = frozenset("the your you and with that this is are of to has have been one for it in on will can not "
                      "audit check lead reach send call hold avoid keep take make any bet brings risk savings money work "
                      "guard made from at by but if or they their we our my an be do up out over than then when what who "
                      "how all more year years week step visible venture speculative investment considering odds favour "
                      "favor build protect release".split())


def _looks_english(s: str) -> bool:
    """True when a payload string that should be Spanish is actually English (a missed translation)."""
    toks = [t.strip(".,;:!?\u2014-()'\"").lower() for t in (s or "").split()]
    return sum(1 for t in toks if t in _EN_WORDS) >= 2


def _ordinal_en(n) -> str:
    """1 -> 1st, 2 -> 2nd, 11 -> 11th (the template used a bare "{h}th", which gave "1th house")."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _lower_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s else s


def _clean(s: str) -> str:
    return (s or "").strip().rstrip(".!? ")


_CLOCK = _re.compile(r"(\d{1,2}):(\d{2})\s*([AaPp])?\.?[Mm]?\.?\s*(?:\u2013|\u2014|-|to)\s*(\d{1,2}):(\d{2})\s*([AaPp])?\.?[Mm]?\.?")


def clock_range(window):
    """("12:18", "13:06") from "12:18 PM \u2013 1:06 PM", else None. 24-hour, same local day as the
    window. A start with no AM/PM takes the end's, and flips to the other half if that would make it
    later than the end ("11:30 \u2013 12:15 PM"). Never guesses: an unreadable window gives None."""
    try:
        m = _CLOCK.search(str(window or ""))
        if not m:
            return None
        h1, m1, a1, h2, m2, a2 = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5)), m.group(6)
        if not (0 <= m1 < 60 and 0 <= m2 < 60):
            return None

        def h24(h, ap):
            if ap is None:
                return h
            if not 1 <= h <= 12:
                return None
            return (0 if h == 12 else h) + (12 if ap.lower() == "p" else 0)

        end = h24(h2, a2)
        start = h24(h1, a1 if a1 else a2)
        if start is None or end is None or not (0 <= start < 24 and 0 <= end < 24):
            return None
        if not a1 and a2 and start * 60 + m1 >= end * 60 + m2:
            start = h24(h1, "a" if a2.lower() == "p" else "p")
        if start is None or start * 60 + m1 >= end * 60 + m2:
            return None
        return f"{start:02d}:{m1:02d}", f"{end:02d}:{m2:02d}"
    except Exception:
        return None


def _fmt12(hm: str) -> str:
    h, m = int(hm[:2]), int(hm[3:5])
    return f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def clear_of(best, avoid, min_minutes: int = 20):
    """The best window with any overlap with the avoid window cut away, as "12:23 PM \u2013 1:11 PM"
    text. The two come from different generic sources (best hour, Rahu Kalam) and can overlap, which
    told the user to commit and not to commit in the same minutes. Keeps the longer clear side; None
    when less than `min_minutes` is left, or when either window cannot be read (then the caller keeps
    what it had: never a guess)."""
    b, a = clock_range(best), clock_range(avoid)
    if not b or not a:
        return best
    mm = lambda hm: int(hm[:2]) * 60 + int(hm[3:5])
    bs, be, as_, ae = mm(b[0]), mm(b[1]), mm(a[0]), mm(a[1])
    if be <= as_ or bs >= ae:
        return best
    left, right = (bs, min(be, as_)), (max(bs, ae), be)
    seg = max((x for x in (left, right) if x[1] - x[0] >= min_minutes), key=lambda x: x[1] - x[0], default=None)
    if not seg:
        return None
    f = lambda v: _fmt12(f"{v // 60:02d}:{v % 60:02d}")
    return f"{f(seg[0])} \u2013 {f(seg[1])}"


def _between(w: str, tx: dict) -> str:
    if not w:
        return ""
    parts = [x.strip() for x in w.replace(" \u2013 ", "|").replace(" - ", "|").split("|")]
    if len(parts) == 2:
        return tx["between"].format(a=parts[0], b=parts[1])
    return "between " + w if tx is _TX["en"] else "en " + w


_REL = {
    "past": {
        "en": {"pos": "That day favoured {lead}.", "neg": "That day was a hold day for {lead}.",
               "light": "It was a lighter-touch day.", "overreach": "", "care1": "{x} needed care.", "careN": "{x} needed care.",
               "w_today": "That day"},
        "es": {"pos": "Ese d\u00eda favoreci\u00f3 {lead}.", "neg": "Ese d\u00eda fue de pausa para {lead}.",
               "light": "Fue un d\u00eda de toque ligero.", "overreach": "", "care1": "{x} necesit\u00f3 cuidado.", "careN": "{x} necesitaron cuidado.",
               "w_today": "Ese d\u00eda"},
    },
    "future": {
        "en": {"pos": "That day favours {lead}.", "neg": "That day is a hold day for {lead} \u2014 protect what you have rather than push.",
               "w_today": "That day"},
        "es": {"pos": "Ese d\u00eda favorece {lead}.", "neg": "Ese d\u00eda es de pausa para {lead}: protege lo que tienes en lugar de forzar.",
               "w_today": "Ese d\u00eda"},
    },
}


def compose(p: dict, language: str = "en", relation: str = "today"):
    """The decision block, or None when the payload can't support a truthful one."""
    try:
        if language not in _TX or not isinstance(p, dict):
            return None
        L, tx = language, dict(_TX[language])
        if relation in ("past", "future"):
            tx.update((_REL[relation].get(L) or {}))
        ev = p.get("evidence") or {}
        chosen = [k for k in (ev.get("chosen") or []) if k in _LABEL]
        if not chosen:
            return None
        weekend = _is_weekend(p)
        _base = (lambda k: _LABEL[k]) if L == "en" else (lambda k: I18.LEAD[L].get(k))
        # Saturday / Sunday: the Moon can light the 10th house, but nobody is at the desk \u2014 say visibility, not workload
        lead_name = (lambda k: tx["wk_work"] if (weekend and k == "work") else _base(k))
        if L != "en" and any(lead_name(k) is None for k in chosen[:2]):
            return None
        negative = (ev.get("lead_dir") or p.get("direction") or "positive") == "negative"
        light = ((p.get("confidence") or {}).get("level") == "low") or ((p.get("day_energy") or {}).get("key") == "light")
        care_keys = [d.get("key") for d in (p.get("domains") or []) if d.get("state") in ("caution", "risk")][:2]
        if L == "en":
            care = [str((d.get("name") or {}).get("en") or d.get("key")).lower()
                    for d in (p.get("domains") or []) if d.get("state") in ("caution", "risk")][:2]
        else:
            care = [I18.CARE[L].get(k) for k in care_keys]
            care = [c for c in care if c]

        lead = lead_name(chosen[0]) + (f"{tx['then']}{lead_name(chosen[1])}" if len(chosen) > 1 else "")
        pred = (tx["neg"] if negative else tx["pos"]).format(lead=lead)
        overreach = [c for c in care_keys if c in ("career", "work")] if L != "en" else \
            [c for c in care if c in ("career", "work")]
        other = [c for c in care if (c not in ("career", "work") and c != I18.CARE.get(L, {}).get("career")
                                      and c != I18.CARE.get(L, {}).get("work"))] if L != "en" else \
            [c for c in care if c not in ("career", "work")]
        if other:
            joined = tx["and"].join(other)
            pred += " " + (tx["care1"] if len(other) == 1 else tx["careN"]).format(x=joined.capitalize() if L == "en" else joined)
        if overreach and tx["overreach"] and any(k in ("work", "network") for k in chosen) and not weekend:
            pred += " " + tx["overreach"]
        if light:
            pred += " " + tx["light"]

        shift = ((p.get("moon_shift") or {}).get("split") or {})
        at = (p.get("moon_shift") or {}).get("changes_at") or shift.get("at")
        improves = shift.get("material") and shift.get("direction") == "improves"
        worsens = shift.get("material") and shift.get("direction") == "worsens"

        bits = []
        msign = p.get("moon_sign")
        if msign:
            msign = msign if L == "en" else I18.sign(msign, L)
            frm = (p.get("moon_shift") or {}).get("from_nakshatra") or (p.get("panchanga") or {}).get("nakshatra")
            qb_raw = ((shift.get("before") or {}).get("quality_label") or "")
            qa_raw = ((shift.get("after") or {}).get("quality_label") or "")
            qb = qb_raw.lower() if L == "en" else I18.quality(qb_raw, L)
            qa = qa_raw.lower() if L == "en" else I18.quality(qa_raw, L)
            to_nak = (p.get("moon_shift") or {}).get("to_nakshatra")
            if (improves or worsens) and at and frm and qb and qa:
                bits.append(tx["moon_shift"].format(sign=msign, nak=frm, qb=qb, at=at, to=to_nak, qa=qa))
            elif frm:
                bits.append(tx["moon"].format(sign=msign, nak=frm))
        h = p.get("moon_house_from_lagna")
        lit = p.get("lit_domain") if L == "en" else I18.HOUSE_LIT[L].get(h)
        if h and lit:
            bits.append(tx["house"].format(h=_ordinal_en(h) if L == "en" else h, lit=lit))
        for sg in (p.get("signals") or []):
            if sg.get("key") == "dasha" and sg.get("value"):
                v = sg["value"].replace(" \u2192 ", "\u2013")
                d = ""
                if sg.get("direction") in ("friction", "adverse", "supportive"):
                    d = f" ({sg['direction'] if L == 'en' else I18.SIGNAL_DIR[L][sg['direction']]})"
                if L != "en":
                    v = "\u2013".join(I18.planet(x, L) for x in v.split("\u2013"))
                bits.append(tx["dasha"].format(v=v, d=d))
        why = " ".join(bits)

        best = (p.get("hora") or {}).get("best_window") or (p.get("panchanga") or {}).get("best_time") or p.get("abhijit")
        avoid = p.get("rahu_kalam") or (p.get("hora") or {}).get("avoid_window")
        if best and avoid:
            best = clear_of(best, avoid)
        if improves and at:
            holds = tx["holds_up"].format(at=at, best=(tx["holds_up_best"].format(best=best) if best else ""))
            when = tx["w_after"].format(at=at)
        elif worsens and at:
            holds = tx["holds_dn"].format(at=at)
            when = tx["w_before"].format(at=at)
        elif best and weekend and any(k in ("work", "network") for k in chosen):
            holds = tx["wk_holds"].format(between=_between(best, tx))
            b = _between(best, tx)
            when = b[:1].upper() + b[1:]
        elif best:
            holds = tx["holds_best"].format(between=_between(best, tx))
            b = _between(best, tx)
            when = b[:1].upper() + b[1:]
        else:
            holds, when = tx["holds_none"], tx["w_today"]

        brk = tx["brk"].format(avoid=(" " + _between(avoid, tx)) if avoid else "")
        dont = _clean((p.get("dont_today") or [""])[0])
        if L == "en":
            if dont.lower().startswith("don't "):
                brk += tx["brk_dont"].format(dont=_lower_first(dont[6:]))
            brk += tx["brk_end"]
        else:
            brk += tx["brk_end"]
            if dont and not _looks_english(dont):
                brk += " " + tx["brk_dont"].split(". ")[1].format(dont=_lower_first(dont)) + "."

        item = _clean(next((x for x in ((p.get("haz_hoy") or []) + (p.get("aligned_for") or [])) if x), "")
                      or (p.get("do_today") or [""])[0])
        if L != "en" and _looks_english(item):
            item = ""
        if item and weekend and _CONTACT.search(item) and any(k in ("work", "network") for k in chosen):
            move = tx["wk_prep"].format(when=when)
        elif item and _HAS_TIME.search(item):
            move = item[:1].upper() + item[1:] + "."          # it already says when
        else:
            move = tx["move"].format(when=when, item=_lower_first(item)) if item else ""
        if p.get("pending"):
            # fast-phase payload: its do/aligned item is a deterministic placeholder that the full (LLM) pass
            # replaces within seconds, so the card showed one "Your move" then swapped it (2026-10-11 UI audit).
            # Publish no move until the full phase so the client never shows a sentence that is then replaced.
            move = ""
        if relation == "past":
            # nothing to act on in a day that is over: what it favoured, and why
            return {"prediction": pred, "why": why, "relation": "past", "version": "today-decision-1"} if pred else None
        out = {"prediction": pred, "why": why, "holds": holds, "breaks": brk, "move": move, "relation": relation,
               "window": {"best": best, "avoid": avoid, "shift_at": at if (improves or worsens) else None,
                          # structured, so the app can offer "add to calendar" without parsing prose
                          **({"best_start": _cr[0], "best_end": _cr[1]} if (_cr := clock_range(best)) else {})},
               "version": "today-decision-1"}
        return out if (pred and holds and brk) else None
    except Exception:
        return None
