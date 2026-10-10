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

_LABEL = {
    "work": "work and reputation", "network": "income and your network", "money": "money",
    "father": "fortune, mentors and the long view", "body": "health and energy",
    "relationship": "close relationships", "family": "family", "travel": "travel", "home": "home and property",
}


def _lower_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].lower() + s[1:] if s else s


def _between(w: str) -> str:
    return "between " + w.replace(" \u2013 ", " and ").replace(" - ", " and ") if w else ""


def _clean(s: str) -> str:
    return (s or "").strip().rstrip(".!? ")


def compose(p: dict, language: str = "en"):
    """The decision block, or None when the payload can't support a truthful one."""
    try:
        if language != "en" or not isinstance(p, dict):
            return None
        ev = p.get("evidence") or {}
        chosen = [k for k in (ev.get("chosen") or []) if k in _LABEL]
        if not chosen:
            return None
        negative = (ev.get("lead_dir") or p.get("direction") or "positive") == "negative"
        light = ((p.get("confidence") or {}).get("level") == "low") or ((p.get("day_energy") or {}).get("key") == "light")
        care = [str((d.get("name") or {}).get("en") or d.get("key")).lower()
                for d in (p.get("domains") or []) if d.get("state") in ("caution", "risk")][:2]

        lead = _LABEL[chosen[0]] + (f", then {_LABEL[chosen[1]]}" if len(chosen) > 1 else "")
        if negative:
            pred = f"Today is a hold day for {lead} — protect what you have rather than push."
        else:
            pred = f"Today favours {lead}."
        overreach = [c for c in care if c in ("career", "work")]
        other = [c for c in care if c not in ("career", "work")]
        if other:
            pred += f" {' and '.join(other).capitalize()} need{'s' if len(other) == 1 else ''} care."
        if overreach and any(k in ("work", "network") for k in chosen):
            pred += " Watch for taking on too much at work."
        if light:
            pred += " It's a lighter-touch day: steady progress, not big bets."

        shift = ((p.get("moon_shift") or {}).get("split") or {})
        at = (p.get("moon_shift") or {}).get("changes_at") or shift.get("at")
        improves = shift.get("material") and shift.get("direction") == "improves"
        worsens = shift.get("material") and shift.get("direction") == "worsens"

        bits = []
        if p.get("moon_sign"):
            frm = (p.get("moon_shift") or {}).get("from_nakshatra") or (p.get("panchanga") or {}).get("nakshatra")
            q_before = ((shift.get("before") or {}).get("quality_label") or "").lower()
            q_after = ((shift.get("after") or {}).get("quality_label") or "").lower()
            if (improves or worsens) and at and frm:
                bits.append(f"The Moon is in {p['moon_sign']}, in {frm} ({q_before}) until {at}, then "
                            f"{(p.get('moon_shift') or {}).get('to_nakshatra')} ({q_after}).")
            elif frm:
                bits.append(f"The Moon is in {p['moon_sign']}, in {frm}.")
        if p.get("moon_house_from_lagna") and p.get("lit_domain"):
            bits.append(f"It lights your {p['moon_house_from_lagna']}th house ({p['lit_domain']}).")
        for sg in (p.get("signals") or []):
            if sg.get("key") == "dasha" and sg.get("value"):
                bits.append(f"You're running {sg['value'].replace(' → ', '–')}"
                            + (f" ({sg['direction']})" if sg.get("direction") in ("friction", "adverse", "supportive") else "") + ".")
        why = " ".join(bits)

        best = (p.get("hora") or {}).get("best_window") or (p.get("panchanga") or {}).get("best_time") or p.get("abhijit")
        avoid = p.get("rahu_kalam") or (p.get("hora") or {}).get("avoid_window")
        if improves and at:
            holds = (f"It holds if you prepare before {at} and commit after it, when the Moon's star turns in your favour"
                     + (f"; the sharpest single hour for an ask or a pitch is {best}" if best else "") + ".")
            when = f"After {at}"
        elif worsens and at:
            holds = f"It holds if you commit before {at}, while the Moon's star still favours you, and keep the afternoon light."
            when = f"Before {at}"
        elif best:
            holds = f"It holds if the decision that matters goes {_between(best)}."
            when = _between(best)[:1].upper() + _between(best)[1:]
        else:
            holds, when = "It holds if you keep to steady, ordinary work.", "Today"

        brk = "It breaks if you force a decision or a hard conversation" + (f" {_between(avoid)}" if avoid else "")
        dont = _clean((p.get("dont_today") or [""])[0])
        if dont.lower().startswith("don't "):
            brk += f", or {_lower_first(dont[6:])}"
        brk += "."

        item = _clean(next((x for x in ((p.get("haz_hoy") or []) + (p.get("aligned_for") or [])) if x), "")
                      or (p.get("do_today") or [""])[0])
        move = f"{when}, {_lower_first(item)}." if item else ""
        out = {"prediction": pred, "why": why, "holds": holds, "breaks": brk, "move": move,
               "window": {"best": best, "avoid": avoid, "shift_at": at if (improves or worsens) else None},
               "version": "today-decision-1"}
        return out if (pred and holds and brk) else None
    except Exception:
        return None
