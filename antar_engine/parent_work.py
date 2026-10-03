"""
antar_engine/parent_work.py — what the reading says about working WITH a parent
(family business, joining a father's or mother's work), in plain words.

[parent-work 2026-10-03] Owner: add the father relationship reading. Live: "Is my
work better with partners or with my father?" answered only about deals — the
chart's father signals (the 9th house and the Sun; the mother's are the 4th house
and the Moon) were never read. domain_engines_tier1 already computes them
(engine_father / engine_mother) but Ask never called it.

This module turns those signals into a narrator block in plain language:
  * support → the parent's backing, name or network tends to open doors;
  * friction → authority / distance / differing views are part of the bond.
Hard rules for the narrator: never the parent's health, illness, lifespan or
death (the engine's longevity note is dropped); never a winner against
partners; for work together, the practical move is clear roles, decision
rights and the money split agreed up front.
"""
from __future__ import annotations

import json
import re
from typing import Optional

_FATHER = re.compile(r"(?i)\b(father|dad|daddy|papa|pap[aá]|padre|pai|pitaji|pita ji|abba|baba|"
                     r"apa|my old man)\b")
_MOTHER = re.compile(r"(?i)\b(mother|mom|mum|mummy|mama|mam[aá]|madre|m[aã]e|maa|mataji|ammi|amma)\b")


def who(question: str, u: Optional[dict] = None) -> Optional[str]:
    """'father' | 'mother' | None — only when the message names the parent."""
    q = question or ""
    if _FATHER.search(q):
        return "father"
    if _MOTHER.search(q):
        return "mother"
    return None


_PLAIN = {
    "father": {
        "support": "their father's backing, name or network tends to open doors for them, and "
                   "some of their good fortune comes through him",
        "friction": "authority clashes, distance or differing views are part of this bond — "
                    "who decides needs to be clear",
        "label": "father",
    },
    "mother": {
        "support": "their mother's care and steadiness tends to give them a secure base to work from",
        "friction": "emotional expectations and old family patterns can blur business lines — "
                    "roles need to be clear",
        "label": "mother",
    },
}


def _engine(chart_data: dict, birth_date: str, rel: str) -> Optional[dict]:
    try:
        from antar_engine.domain_engines_tier1 import engine_father, engine_mother
        cd = chart_data if isinstance(chart_data, dict) else json.loads(chart_data or "{}")
        planets = cd.get("planets", {}) or {}
        hl = cd.get("house_lords", {}) or {}
        divs = cd.get("divisional_charts", {}) or {}
        if not planets:
            return None
        if rel == "father":
            return engine_father(planets, hl, divs, birth_date or "")
        return engine_mother(planets, hl, divs)
    except Exception:
        return None


def block(chart_data, birth_date: str, rel: Optional[str]) -> str:
    """Narrator block for a question about working with / relating to a parent."""
    if rel not in _PLAIN:
        return ""
    r = _engine(chart_data, birth_date, rel)
    if not r:
        return ""
    p = _PLAIN[rel]
    sup, fri = len(r.get("blessings") or []), len(r.get("challenges") or [])
    if sup and not fri:
        tone = f"mostly supportive: {p['support']}"
    elif fri and not sup:
        tone = f"carries real weight: {p['friction']}"
    elif sup and fri:
        tone = f"mixed: {p['support']}; and {p['friction']}"
    else:
        tone = "neutral — neither a strong push nor a strong drag"
    return (f"\n\nWORKING WITH THEIR {p['label'].upper()} — what the reading shows about this "
            f"relationship ({sup} supportive signal(s), {fri} friction signal(s)): it is {tone}.\n"
            f"- Say this in plain words (no house, planet or sign names).\n"
            f"- NEVER mention the {p['label']}'s health, illness, lifespan or death.\n"
            f"- If they're weighing it against partners or another option, don't name a winner: "
            f"say how working with their {p['label']} tends to go for them, and what makes it work.\n"
            f"- The practical move for working together: agree roles, who decides what, and how "
            f"the money is split, up front and in writing.")
