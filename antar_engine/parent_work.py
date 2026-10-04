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


_WORK_Q = re.compile(
    r"(?i)\b(work|working|business|partner|partners|partnership|company|firm|deal|deals|money|income|"
    r"career|job|venture|startup|trabaj\w*|negocio|socio\w*|empresa|neg[oó]cio|s[oó]cio\w*|kaam|vyapar|"
    r"dhandha|naukri)\b")
_HEALTH_AREAS = frozenset({"health_self", "health_other", "children_wellbeing"})


def applies(question: str, u: Optional[dict] = None) -> bool:
    """[audit r7] The father-backing / money-split reading belongs to questions about working with
    or relating to a parent — never to the parent's HEALTH (live: "How is my father's health
    looking?" got 'his name opens doors for you')."""
    return (u or {}).get("area") not in _HEALTH_AREAS


def health_block(rel: Optional[str]) -> str:
    """A question about a parent's HEALTH: the reading is about the asker, so say so, and never
    predict the parent's conditions (live r7: 'kidneys, skin, a health-sensitive window')."""
    if rel not in _PLAIN:
        return ""
    lab = _PLAIN[rel]["label"]
    return (f"\n\nTHEIR {lab.upper()}'S HEALTH — the reading is THEIR chart; it cannot diagnose or "
            f"forecast another person's body.\n"
            f"- Do NOT name any condition, body part, illness, lifespan or risk window for their {lab}.\n"
            f"- Acknowledge it is weighing on them; say what this period is like FOR THEM (energy, "
            f"worry, how much they can carry); keep the practical step to a check-up with a qualified "
            f"doctor, being present, sharing the load. No herbs or remedies.")


def is_work_question(question: str, u: Optional[dict] = None) -> bool:
    return bool(_WORK_Q.search(question or "")) or (u or {}).get("area") in (
        "business_partnership", "business_venture", "career_job", "income_money")


_PLAIN = {
    "father": {
        "support": "their father's backing tends to be a real source of support for them",
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


def block(chart_data, birth_date: str, rel: Optional[str], work: bool = True) -> str:
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
    if not work:
        # a question about the relationship itself, not about working together
        return (f"\n\nTHEIR {p['label'].upper()} — what the reading shows about this relationship "
                f"({sup} supportive signal(s), {fri} friction signal(s)): it is {tone}.\n"
                f"- Say this in plain words (no house, planet or sign names); a tendency, never a past fact.\n"
                f"- NEVER mention the {p['label']}'s health, illness, lifespan or death.\n"
                f"- This is NOT a business question: do NOT bring up business, doors opening, money, gains or "
                f"agreements; stay on how the bond tends to go and one human step (a conversation, a visit).\n"
                f"- If they ask whether the {p['label']} will be successful, say the reading is about THEIR "
                f"chart and cannot judge the {p['label']}'s own success; speak to the bond instead.")
    return (f"\n\nWORKING WITH THEIR {p['label'].upper()} — what the reading shows about this "
            f"relationship ({sup} supportive signal(s), {fri} friction signal(s)): it is {tone}.\n"
            f"- Say this in plain words (no house, planet or sign names).\n"
            f"- NEVER mention the {p['label']}'s health, illness, lifespan or death.\n"
            f"- Say what the reading shows as a TENDENCY ('tends to open doors'), never as past fact "
            f"('some of your gains have come through him').\n"
            f"- If they're weighing it against partners or another option, don't name a winner: "
            f"say how working with their {p['label']} tends to go for them, and what makes it work.\n"
            f"- The practical move for working together: agree roles, who decides what, and how "
            f"the money is split, up front and in writing.")
