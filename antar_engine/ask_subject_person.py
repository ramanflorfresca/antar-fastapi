"""
antar_engine/ask_subject_person.py

Person-path helpers for Ask when the question is about someone ELSE (resolved by
ask_subject.resolve_subject). Pure: main.py does the I/O; everything the reading
says about WHO and WHAT is decided here so it is unit-testable without a database.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from antar_engine.ask_subject import _fold

_REL_LABEL = {
    "en": {"child": "child", "partner": "partner", "parent": "parent", "sibling": "sibling",
           "friend": "friend", "boss": "boss", "employee": "colleague",
           "cofounder": "co-founder", "advisor": "advisor", "family": "relative"},
    "es": {"child": "hijo/a", "partner": "pareja", "parent": "padre/madre", "sibling": "hermano/a",
           "friend": "amigo/a", "boss": "jefe/a", "employee": "colega",
           "cofounder": "cofundador/a", "advisor": "mentor/a", "family": "familiar"},
    "pt": {"child": "filho/a", "partner": "parceiro/a", "parent": "pai/mãe", "sibling": "irmão/ã",
           "friend": "amigo/a", "boss": "chefe", "employee": "colega",
           "cofounder": "cofundador/a", "advisor": "mentor/a", "family": "familiar"},
    "hinglish": {"child": "bachcha", "partner": "partner", "parent": "mata-pita", "sibling": "bhai/behen",
                 "friend": "dost", "boss": "boss", "employee": "colleague",
                 "cofounder": "co-founder", "advisor": "mentor", "family": "rishtedaar"},
}
_LANG_NAME = {"en": "English", "es": "Spanish", "pt": "Portuguese",
              "hinglish": "Hinglish (Romanized Hindi mixed with English, Latin script)"}


def _lang(language: str) -> str:
    l = (language or "en").split("-")[0].lower()
    return "hinglish" if l == "hi" else (l if l in _REL_LABEL else "en")


def relation_label(relation: Optional[str], language: str = "en") -> str:
    return _REL_LABEL[_lang(language)].get(relation or "", "") or (relation or "")


_AMBIG_TXT = {
    "en": ("Just so I read the right chart — which {who} do you mean?",
           "Tap the one you mean and I'll read their chart."),
    "es": ("Para leer la carta correcta, ¿a cuál {who} te refieres?",
           "Elige a quién te refieres y leeré su carta."),
    "pt": ("Para ler o mapa certo, a qual {who} você se refere?",
           "Escolha de quem fala e eu leio o mapa dessa pessoa."),
    "hinglish": ("Sahi chart padhne ke liye batao — kaun sa {who}?",
                 "Jiske baare mein pooch rahe ho use chuno, main unka chart padhunga."),
}
_MISSING_TXT = {
    "en": ("I don't have your {rel}'s chart yet, so I can't read theirs — and I won't answer "
           "about them from your own chart. Add them in People (name, birth date, time and place) "
           "and ask me again.",
           "Add them in People, then ask again."),
    "es": ("Todavía no tengo la carta de tu {rel}, así que no puedo leer la suya — y no voy a "
           "responder sobre esa persona con tu propia carta. Agrégala en Personas (nombre, fecha, "
           "hora y lugar de nacimiento) y pregúntame de nuevo.",
           "Agrégala en Personas y vuelve a preguntar."),
    "pt": ("Ainda não tenho o mapa do seu {rel}, então não consigo ler o dele — e não vou "
           "responder sobre essa pessoa com o seu próprio mapa. Adicione em Pessoas (nome, data, "
           "hora e local de nascimento) e pergunte de novo.",
           "Adicione em Pessoas e pergunte de novo."),
    "hinglish": ("Mere paas abhi aapke {rel} ka chart nahi hai, isliye main unka read nahi kar "
                 "sakta — aur unke baare mein aapke apne chart se jawab nahi dunga. People mein "
                 "unhe add karo (naam, janam tithi, samay aur jagah) aur phir poocho.",
                 "People mein add karo, phir poocho."),
}
_UNREADABLE_TXT = {
    "en": "I have {name} saved, but their chart isn't readable right now, so I won't guess from yours. "
          "Open them in People to re-check their birth details, then ask again.",
    "es": "Tengo guardado a {name}, pero su carta no se puede leer ahora, así que no voy a adivinar con la tuya. "
          "Ábrelo en Personas para revisar sus datos de nacimiento y vuelve a preguntar.",
    "pt": "Tenho {name} salvo(a), mas o mapa não pode ser lido agora, então não vou adivinhar com o seu. "
          "Abra em Pessoas para rever os dados de nascimento e pergunte de novo.",
    "hinglish": "{name} saved hain, par unka chart abhi padha nahi ja sakta, isliye aapke chart se andaza nahi lagaunga. "
                "People mein unki birth details check karo aur phir poocho.",
}


def ambiguous_payload(res: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
    lg = _lang(language)
    who = relation_label(res.get("relation"), lg) or ("persona" if lg in ("es", "pt") else "person")
    read, nxt = _AMBIG_TXT[lg]
    chips = [c["name"] for c in (res.get("candidates") or [])][:6]
    return {"mode": "explore", "read": read.format(who=who), "next": nxt, "locked": False,
            "needs_clarification": True, "clarification_chips": chips,
            "clarification_fact": "subject"}


def is_ambiguity_prompt(prev_answer: str) -> bool:
    """Was the previous assistant turn our which-one clarify (any language)?"""
    a = (prev_answer or "").strip()
    return bool(a) and any(a.startswith(t[0].split("{who}")[0]) for t in _AMBIG_TXT.values())


def missing_payload(res: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
    lg = _lang(language)
    read, nxt = _MISSING_TXT[lg]
    return {"mode": "explore",
            "read": read.format(rel=relation_label(res.get("relation"), lg) or "person"),
            "next": nxt, "locked": False,
            "subject": {"relation": res.get("relation"), "chart_available": False}}


def unreadable_payload(name: str, language: str = "en") -> Dict[str, Any]:
    lg = _lang(language)
    return {"mode": "explore", "read": _UNREADABLE_TXT[lg].format(name=name),
            "next": _MISSING_TXT[lg][1], "locked": False,
            "subject": {"name": name, "chart_available": False}}


# ── relation lens ─────────────────────────────────────────────────────────────
# the asker-side house that describes the asker's bond with this kind of person
_ASKER_LENS = {"child": (5, "children"), "partner": (7, "partnership"),
               "sibling": (3, "siblings"), "parent": (4, "mother/home"),
               "boss": (10, "career/authority"), "friend": (11, "friends"),
               "cofounder": (7, "partnerships"), "employee": (6, "service/colleagues"),
               "advisor": (9, "mentors"), "family": (4, "family")}


def person_concern(concern: str, question: str = "") -> Optional[str]:
    """Map the router's concern word to a concern_engines key; None => descriptive digest."""
    c = (concern or "").lower()
    q = _fold(question)
    if c in ("health", "illness", "disease") or re.search(
            r"\b(health|sick|ill|surgery|salud|saude|sehat|bimar)\b", q):
        return "health"
    if c in ("divorce", "separation"):
        return "separation"
    if c in ("marriage", "love", "relationship") or re.search(
            r"\b(married|marry|marriage|wedding|casar\w*|shaadi|shadi|pregnan\w*|conceive)\b", q):
        return "relationship_entry"
    if c in ("finance", "wealth", "money", "income") or re.search(
            r"\b(money|income|salary|wealth|dinero|dinheiro|paisa)\b", q):
        return "income"
    return None


def _house_line(cd: dict, lagna: str, h: int, label: str) -> str:
    from antar_engine.d10_career import SIGN_LORD, _sign_n_from
    sign = _sign_n_from(lagna, h)
    lord = SIGN_LORD.get(sign)
    planets = (cd or {}).get("planets") or {}
    occ = [p for p, v in planets.items() if isinstance(v, dict) and v.get("house") == h]
    lv = planets.get(lord) or {}
    return (f"{label}: lord {lord} sits in house {lv.get('house', '?')} ({lv.get('sign', '?')})"
            + (f"; occupied by {', '.join(occ)}" if occ else "; unoccupied"))


def _running(dashas: dict) -> str:
    from datetime import date
    today = date.today().isoformat()
    md = ad = ""
    for sysname in ("vimsottari", "vimshottari"):
        for p in (dashas or {}).get(sysname) or []:
            if not isinstance(p, dict):
                continue
            s = str(p.get("start_date") or p.get("start") or "")[:10]
            e = str(p.get("end_date") or p.get("end") or "")[:10]
            if not (s and e and s <= today <= e):
                continue
            lord = str(p.get("lord_or_sign") or p.get("planet_or_sign") or "").title()
            lvl = str(p.get("level") or p.get("type") or "").lower()
            if lvl.startswith("maha"):
                md = lord
            elif lvl.startswith("antar"):
                ad = lord
    return (f"{md} major period" + (f", {ad} sub-period" if ad else "")) if md else ""


def build_person_facts(name: str, relation: Optional[str], question: str, concern: str,
                       person_chart: dict, person_dashas: dict,
                       asker_chart: Optional[dict] = None, intent: str = "state") -> Dict[str, Any]:
    """Facts about THE PERSON's chart (the asker's chart only as labelled bond
    context). {available, facts, concern_key}. Never raises."""
    try:
        cd = person_chart if isinstance(person_chart, dict) else {}
        lagna = (cd.get("lagna") or {}).get("sign")
        planets = cd.get("planets") or {}
        if not lagna or not planets:
            return {"available": False}
        key = person_concern(concern, question)
        lines = [f"SUBJECT: {name}" + (f" ({relation} of the reader)" if relation else "")]
        lines.append(f"{name}'s rising sign: {lagna}")
        moon = planets.get("Moon") or {}
        if moon:
            lines.append(f"{name}'s Moon: {moon.get('sign', '?')}, house {moon.get('house', '?')}")
        run = _running(person_dashas)
        if run:
            lines.append(f"{name}'s running period: {run}")
        if key:
            from antar_engine.concern_engines import analyze_concern
            r = analyze_concern(key, cd, person_dashas, intent)
            if r.get("available"):
                lines.append(f"READING OF {name}'s CHART for {r.get('subject')} "
                             f"(verdict: {r.get('verdict')}); 'you/your' below means {name}:\n"
                             f"{r.get('narration_facts')}")
        else:
            for h, lab in ((1, "body/self"), (6, "daily strain"), (10, "work/standing"),
                           (7, "partnership")):
                lines.append(_house_line(cd, lagna, h, f"{name}'s {lab}"))
        if relation == "child" and key == "health":
            lines.append(_house_line(cd, lagna, 8, f"{name}'s chronic/long-run house"))
        al = _ASKER_LENS.get(relation or "")
        acd = asker_chart if isinstance(asker_chart, dict) else None
        if al and acd and (acd.get("lagna") or {}).get("sign"):
            lines.append("BOND CONTEXT (the reader's side, background only — never describe it as "
                         f"{name}'s): " + _house_line(acd, acd["lagna"]["sign"], al[0],
                                                       f"reader's house of {al[1]}"))
        return {"available": True, "facts": "\n".join(lines), "concern_key": key}
    except Exception as e:
        return {"available": False, "error": str(e)[:120]}


def narrator_block(name: str, relation: Optional[str], language: str = "en") -> str:
    """Prompt block for subject=person. Applies to every language."""
    lg = _lang(language)
    rel = relation_label(relation, "en") or "person"
    return (
        f"SUBJECT OF THIS QUESTION — This question is about {name} ({rel}). "
        f"Use ONLY the supplied reading of {name}'s chart. Do not describe the reader's own "
        f"health, marriage, career or money as {name}'s, and do not use the reader's chart as "
        f"theirs. Do not invent facts about {name}: no ages, diagnoses, jobs, spouses or events "
        f"that are not in the reading. Speak ABOUT {name} in the third person (use the name), "
        f"and where the reading says 'you/your' it means {name}. You may add one line on what "
        f"the reader can do to support {name}. Plain everyday words — no planet, house or Sanskrit "
        f"terms. Answer in {_LANG_NAME[lg]}. Give a real answer first; hedge honestly, never "
        f"promise or predict a death, a diagnosis or a certain outcome. 3-5 sentences.")


_OWN_CLAIM = re.compile(
    r"\b(your own|your) (health|marriage|chart|career|body|finances|money)\b", re.I)


def guard_read(text: str, name: str) -> str:
    """Deterministic sentence guard: drop sentences about the reader's OWN
    health/marriage/chart that slipped in, and make sure the person is named.
    Returns '' when nothing safe is left (caller falls back)."""
    try:
        parts = re.split(r"(?<=[.!?¿¡])\s+", (text or "").strip())
        out = " ".join(s for s in parts if not _OWN_CLAIM.search(s)).strip()
        if not out:
            return ""
        first = (name or "").split(" ")[0]
        if first and _fold(first) not in _fold(out):
            out = f"{first}: " + out
        return out
    except Exception:
        return text or ""
