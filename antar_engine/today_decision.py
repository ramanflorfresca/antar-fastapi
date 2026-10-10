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
        "house": "It lights your {h}th house ({lit}).",
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
    },
}

_EN_WORDS = frozenset("the your you and with that this is are of to has have been one for it in on will can not "
                      "audit check lead reach send call hold avoid keep take make any bet brings risk savings money work "
                      "guard made from at by but if or they their we our my an be do up out over than then when what who "
                      "how all more year years week step visible venture speculative investment considering odds favour "
                      "favor build protect release".split())


def _looks_english(s: str) -> bool:
    """True when a payload string that should be Spanish is actually English (a missed translation)."""
    toks = [t.strip(".,;:!?\u2014-()'\"").lower() for t in (s or "").split()]
    return sum(1 for t in toks if t in _EN_WORDS) >= 2


def _lower_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s else s


def _clean(s: str) -> str:
    return (s or "").strip().rstrip(".!? ")


def _between(w: str, tx: dict) -> str:
    if not w:
        return ""
    parts = [x.strip() for x in w.replace(" \u2013 ", "|").replace(" - ", "|").split("|")]
    if len(parts) == 2:
        return tx["between"].format(a=parts[0], b=parts[1])
    return "between " + w if tx is _TX["en"] else "en " + w


def compose(p: dict, language: str = "en"):
    """The decision block, or None when the payload can't support a truthful one."""
    try:
        if language not in _TX or not isinstance(p, dict):
            return None
        L, tx = language, _TX[language]
        ev = p.get("evidence") or {}
        chosen = [k for k in (ev.get("chosen") or []) if k in _LABEL]
        if not chosen:
            return None
        lead_name = (lambda k: _LABEL[k]) if L == "en" else (lambda k: I18.LEAD[L].get(k))
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
        if overreach and any(k in ("work", "network") for k in chosen):
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
            bits.append(tx["house"].format(h=h, lit=lit))
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
        if improves and at:
            holds = tx["holds_up"].format(at=at, best=(tx["holds_up_best"].format(best=best) if best else ""))
            when = tx["w_after"].format(at=at)
        elif worsens and at:
            holds = tx["holds_dn"].format(at=at)
            when = tx["w_before"].format(at=at)
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
        move = tx["move"].format(when=when, item=_lower_first(item)) if item else ""
        out = {"prediction": pred, "why": why, "holds": holds, "breaks": brk, "move": move,
               "window": {"best": best, "avoid": avoid, "shift_at": at if (improves or worsens) else None},
               "version": "today-decision-1"}
        return out if (pred and holds and brk) else None
    except Exception:
        return None
