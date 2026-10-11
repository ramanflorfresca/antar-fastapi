"""[connection-card 2026-10-11] The plain-language CARD for a saved connection — strong points, friction, who leads what, do / don't.

The engines already decide everything (the six fit layers, the catalysts / watch-points / moves, and for a cofounder or business partner the
deterministic `roles` read: leads, shared, contested, gaps, the can-they-partner gate). What they produce is correct but reads like a ledger.
This turns those FACTS into a short, human card:

    headline    one sentence — how the two of you work together
    strengths   3 x {title, text}     what works between you
    frictions   3 x {issue, do}       what doesn't, each with the move that handles it
    leads       lane -> you | other | shared | open     (only with roles; each line is checked against the engine's own answer)
    style       {you, other}          how each of you works best (only with roles)
    dos / donts 3 each
    now         one line on timing, when the engines have one

THE LLM ONLY PHRASES. It is given facts and may not add astrology, change a lead, assign a lane the engines left open, or use a chart term.
Every output is validated; anything that fails (bad JSON, jargon, a lead that contradicts the engine) is discarded and a DETERMINISTIC card
built from the same facts is shown instead, so the page never waits on or trusts a bad generation. Good generations are stored per
(session, language) with a hash of the facts: they are reused until the facts change (a period turns, a chart is re-saved).
Pure functions + an injected `llm` callable; storage is isolated in fail-open helpers."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

CARD_VERSION = "connection-card-1"
LANGS = ("en", "es")

LANE_NAME = {
    "en": {"tech": "technology & product", "ops": "operations & execution", "sales": "sales & clients", "vision": "vision & leadership",
           "finance": "finance", "creative": "creative & brand"},
    "es": {"tech": "tecnología / producto", "ops": "operaciones / ejecución", "sales": "ventas / clientes", "vision": "visión / liderazgo",
           "finance": "finanzas", "creative": "creatividad / marca"},
}

# a gendered pronoun for the other person is a guess from a name — never allowed (no gender is given to the model)
# (Spanish: only the ACCENTED pronoun "él" and "ella" — the unaccented "el" is the definite article and must pass)
_PRONOUN = re.compile(r"(?i:\b(?:he|him|his|himself|she|her|hers|herself|ella|suyo|suya)\b)|\b[\u00c9\u00e9]l\b")

# a chart term in a plain-language card is a failed generation
_JARGON = re.compile(
    r"(?i)\b(?:\d+(?:st|nd|rd|th) house|houses?|d-?\d+|navamsa|dasha|mahadasha|antardasha|karakas?|atmakaraka|amatyakaraka|darakaraka|"
    r"parashari|jaimini|vimshottari|vimsottari|chara|nakshatra|lagna|ascendant|rahu|ketu|saturn|mars|mercury|jupiter|venus|"
    r"planets?|transits?|retrograde|exalted|debilitated|horoscope|astrolog\w*|zodiac|casa \d|saturno|marte|mercurio|j[uú]piter|"
    r"planeta|tr[aá]nsito|astrolog[ií]a)\b")


# ── facts ────────────────────────────────────────────────────────────────────
def build_facts(out: dict, language: str = "en") -> dict:
    """The engines' own answers about this pair, reduced to what the card may say. Never raises."""
    try:
        lang = language if language in LANGS else "en"
        roles = out.get("roles") if isinstance(out.get("roles"), dict) else None
        layers = [{"key": l.get("layer_key"), "label": l.get("layer_label"), "score": l.get("score"),
                   "headline": l.get("headline"), "detail": l.get("detail")}
                  for l in (out.get("layers") or []) if isinstance(l, dict)]
        facts = {
            "language": lang, "you": "you", "other": (out.get("name_b") or "").strip() or ("la otra persona" if lang == "es" else "the other person"),
            "relationship": out.get("compat_type_label") or out.get("compat_type") or "",
            "compat_type": out.get("compat_type") or "", "badge": out.get("badge"), "score": out.get("score"),
            "headline": out.get("headline"), "summary": out.get("summary"),
            "strong_points": [x for x in (out.get("catalysts") or []) if x][:6],
            "friction_points": [x for x in (out.get("watch_points") or []) if x][:6],
            "moves": [m.get("text") if isinstance(m, dict) else m for m in (out.get("moves") or []) if m][:6],
            "layers": layers,
            "timing_line": (out.get("timing") or {}).get("line") if isinstance(out.get("timing"), dict) else None,
            "confidence_line": (out.get("confidence") or {}).get("line") if isinstance(out.get("confidence"), dict) else None,
            "career_fit_note": out.get("career_fit_note"),
        }
        if roles and roles.get("kind") == "hierarchy":
            # a reporting line / advisory connection: authority and fit, no lane split — `leads` stays absent
            o = roles.get("other") or {}
            facts["authority"] = {"type": roles.get("type"), "role": roles.get("role"), "fit_for_role": roles.get("fit"),
                                  "takes_direction": roles.get("direction"),
                                  "their_strongest": [LANE_NAME[lang][l] for l in o.get("strengths", [])],
                                  "their_thin": [LANE_NAME[lang][l] for l in o.get("thin", [])],
                                  "their_authority_style": o.get("style"),
                                  "you_add": [LANE_NAME[lang][l] for l in (roles.get("you") or {}).get("add", [])],
                                  "systems_agree_on_their_top_lane": not roles.get("contested_top")}
        elif roles:
            facts["roles"] = {
                "you_lead": roles["you"].get("leads", []), "other_lead": roles["other"].get("leads", []),
                "shared": roles.get("shared", []), "open_contested": roles.get("contested", []), "open_gaps": roles.get("gaps", []),
                "you_can_partner": (roles.get("capacity") or {}).get("you", {}).get("level"),
                "other_can_partner": (roles.get("capacity") or {}).get("other", {}).get("level"),
                "pair_has_a_solo_builder": bool((roles.get("capacity") or {}).get("solo")),
                "systems_agree": not roles.get("contested"),
            }
        return facts
    except Exception:
        return {"language": language, "you": "you", "other": "", "layers": []}


def facts_hash(facts: dict) -> str:
    return hashlib.sha1(json.dumps(facts, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


# ── deterministic card (always available; also the fallback) ───────────────────────────────────
def fallback_card(facts: dict) -> dict:
    """A card built only from the engines' own sentences — plain, correct, a little stiff. Never raises."""
    try:
        lang = facts.get("language") if facts.get("language") in LANGS else "en"
        nm = LANE_NAME[lang]
        strengths = [{"title": "", "text": t} for t in (facts.get("strong_points") or [])[:3]]
        if len(strengths) < 3:
            for l in sorted((facts.get("layers") or []), key=lambda x: -(x.get("score") or 0)):
                if (l.get("score") or 0) >= 60 and l.get("detail") and len(strengths) < 3 and all(l["detail"] != s["text"] for s in strengths):
                    strengths.append({"title": l.get("label") or "", "text": l["detail"]})
        moves = facts.get("moves") or []
        frictions = [{"issue": w, "do": moves[i] if i < len(moves) else ""} for i, w in enumerate((facts.get("friction_points") or [])[:3])]
        card = {"headline": facts.get("headline") or facts.get("summary") or "", "strengths": strengths, "frictions": frictions,
                "dos": [m for m in moves[:3]], "donts": []}
        r = facts.get("roles")
        if r:
            leads = []
            for lane in r["you_lead"]:
                leads.append({"lane": lane, "who": "you", "line": nm[lane]})
            for lane in r["other_lead"]:
                leads.append({"lane": lane, "who": "other", "line": nm[lane]})
            for lane in r["shared"]:
                leads.append({"lane": lane, "who": "shared", "line": nm[lane]})
            for lane in list(r["open_contested"]) + list(r["open_gaps"]):
                leads.append({"lane": lane, "who": "open", "line": nm[lane]})
            card["leads"] = leads
        if facts.get("timing_line"):
            card["now"] = facts["timing_line"]
        return card
    except Exception:
        return {"headline": "", "strengths": [], "frictions": [], "dos": [], "donts": []}


# ── prompt ──────────────────────────────────────────────────────────────────
_SYSTEM = {
    "en": ("You write a short, warm, plain-language read of how two people work together, addressed to the first person (\"you\"). "
           "Use ONLY the facts you are given. Output ONE JSON object and nothing else. "
           "RULES: no astrology or chart words of any kind (no planets, houses, periods, charts, signs). Short sentences, everyday words. "
           "Talk about working style, never about someone's character or feelings; never say a person is 'built to' do or not do something — "
           "say how they do their best work. Never change who leads a lane: copy it from the facts. A lane marked open is NOT assigned. "
           "If the facts say someone works best owning a lane outright, say it as a working style and suggest narrow, written terms. "
           "Every friction must come with one concrete thing to do. "
           "PRONOUNS: you are not told anyone's gender. Call the other person by name or say 'they' — never he, him, his, she or her. "
           "LEADS: each `line` only restates the lane and who owns it, in one short sentence — do not invent duties, tasks or powers the facts do not state."),
    "es": ("Escribes una lectura breve, cálida y en lenguaje sencillo de cómo trabajan juntas dos personas, dirigida a la primera (\"tú\"). "
           "Usa SOLO los datos que recibes. Responde con UN objeto JSON y nada más. "
           "REGLAS: nada de astrología ni palabras de la carta (ni planetas, casas, periodos, cartas, signos). Frases cortas, palabras de todos los días. "
           "Habla de estilo de trabajo, nunca del carácter ni de los sentimientos de alguien; nunca digas que una persona 'está hecha para' algo — "
           "di cómo rinde mejor. Nunca cambies quién lidera un área: cópialo de los datos. Un área marcada como abierta NO está asignada. "
           "Si los datos dicen que alguien rinde mejor dueño de un área, dilo como estilo de trabajo y sugiere términos acotados y por escrito. "
           "Cada fricción debe ir con una cosa concreta que hacer. "
           "PRONOMBRES: no se te dice el género de nadie. Llama a la otra persona por su nombre; nunca uses él ni ella, y evita adjetivos con género sobre ella. "
           "ÁREAS: cada `line` solo repite el área y quién la lleva, en una frase corta; no inventes tareas ni poderes que los datos no digan."),
}

_SCHEMA_HINT = {
    "headline": "one sentence, <= 140 characters",
    "strengths": [{"title": "2-4 words", "text": "one sentence"}, "... exactly 3"],
    "frictions": [{"issue": "one sentence", "do": "one concrete action"}, "... exactly 3"],
    "leads": [{"lane": "tech|ops|sales|vision|finance|creative", "who": "you|other|shared|open", "line": "one short sentence"},
              "... ONLY when facts.roles exists: one per lane in facts.roles, copying who exactly"],
    "style": {"you": "how you work best, one sentence", "other": "how they work best, one sentence"},
    "dos": ["exactly 3 short imperatives"], "donts": ["exactly 3 short imperatives"],
    "now": "one sentence on timing, ONLY if facts.timing_line exists, else omit",
}


def build_prompt(facts: dict) -> Tuple[str, str]:
    lang = facts.get("language") if facts.get("language") in LANGS else "en"
    lane_note = ""
    if facts.get("roles"):
        lane_note = "\nLANE NAMES you may use in sentences: " + json.dumps(LANE_NAME[lang], ensure_ascii=False)
    auth_note = ""
    if facts.get("authority"):
        auth_note = ("\nThis is a REPORTING / ADVISORY line (facts.authority), not a partnership: describe how to manage, work with or use them in "
                     "`style.other`, `strengths`, `frictions`, `dos` and `donts`; say who is strong where in plain words; OMIT `leads`.")
    user = ("FACTS (the only source you may use):\n" + json.dumps(facts, ensure_ascii=False, indent=1, default=str)
            + lane_note + auth_note + "\n\nReturn this JSON shape (omit `leads` and `style` when facts.roles is absent):\n"
            + json.dumps(_SCHEMA_HINT, ensure_ascii=False, indent=1))
    return _SYSTEM[lang], user


# ── validation ────────────────────────────────────────────────────────────────────────────────
def parse_json(text: str) -> Optional[dict]:
    try:
        t = (text or "").strip()
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
        i, j = t.find("{"), t.rfind("}")
        return json.loads(t[i:j + 1]) if i >= 0 and j > i else None
    except Exception:
        return None


def _strings(card: dict) -> List[str]:
    out: List[str] = []
    for k in ("headline", "now"):
        if isinstance(card.get(k), str):
            out.append(card[k])
    for s in card.get("strengths") or []:
        out += [str(s.get("title") or ""), str(s.get("text") or "")] if isinstance(s, dict) else []
    for f in card.get("frictions") or []:
        out += [str(f.get("issue") or ""), str(f.get("do") or "")] if isinstance(f, dict) else []
    for l in card.get("leads") or []:
        out.append(str(l.get("line") or "")) if isinstance(l, dict) else None
    st = card.get("style") or {}
    out += [str(st.get("you") or ""), str(st.get("other") or "")] if isinstance(st, dict) else []
    out += [str(x) for x in (card.get("dos") or []) + (card.get("donts") or [])]
    return out


def validate(card, facts: dict) -> Tuple[bool, List[str]]:
    """(ok, reasons). A card that fails is never shown."""
    why: List[str] = []
    if not isinstance(card, dict):
        return False, ["not an object"]
    if not (isinstance(card.get("headline"), str) and 0 < len(card["headline"]) <= 220):
        why.append("headline")
    st, fr = card.get("strengths"), card.get("frictions")
    if not (isinstance(st, list) and len(st) == 3 and all(isinstance(x, dict) and x.get("text") for x in st)):
        why.append("strengths")
    if not (isinstance(fr, list) and len(fr) == 3 and all(isinstance(x, dict) and x.get("issue") and x.get("do") for x in fr)):
        why.append("frictions")
    for k in ("dos", "donts"):
        v = card.get(k)
        if not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, str) and x.strip() for x in v)):
            why.append(k)
    for s in _strings(card):
        m = _JARGON.search(s)
        if m:
            why.append(f"jargon:{m.group(0).lower()}")
            break
    for s in _strings(card):
        m = _PRONOUN.search(s)
        if m:
            why.append(f"pronoun:{m.group(0).lower()}")
            break
    roles = facts.get("roles")
    leads = card.get("leads")
    if roles:
        expect = {}
        for lane in roles["you_lead"]:
            expect[lane] = "you"
        for lane in roles["other_lead"]:
            expect[lane] = "other"
        for lane in roles["shared"]:
            expect[lane] = "shared"
        for lane in list(roles["open_contested"]) + list(roles["open_gaps"]):
            expect[lane] = "open"
        if not isinstance(leads, list):
            why.append("leads missing")
        else:
            for l in leads:
                if not isinstance(l, dict) or l.get("lane") not in expect or l.get("who") != expect[l["lane"]]:
                    why.append(f"lead mismatch:{(l or {}).get('lane') if isinstance(l, dict) else l}")
                    break
            if {l.get("lane") for l in leads if isinstance(l, dict)} != set(expect):
                why.append("leads incomplete")
    elif leads:
        why.append("leads without roles")
    return (not why), why


# ── generation ────────────────────────────────────────────────────────────────────────────────
async def generate(facts: dict, llm: Callable[[str, str], Awaitable[str]]) -> Tuple[Optional[dict], List[str]]:
    """(card | None, reasons). One attempt plus one corrective retry; the caller falls back to `fallback_card` on None."""
    system, user = build_prompt(facts)
    last: List[str] = []
    for attempt in range(2):
        try:
            text = await llm(user if attempt == 0 else user + "\n\nYour previous answer was rejected for: " + ", ".join(last)
                             + ". Fix exactly that and return only the JSON.", system)
        except Exception as e:
            return None, [f"llm error: {type(e).__name__}"]
        card = parse_json(text)
        ok, last = validate(card, facts)
        if ok:
            card["source"] = "llm"
            card["version"] = CARD_VERSION
            return card, []
    return None, last


# ── storage (fail-open; the table is created by sql_connection_reads.sql) ─────────────────────
_MEM: Dict[tuple, dict] = {}


def cached(sb, session_id: str, language: str, fhash: str) -> Optional[dict]:
    hit = _MEM.get((session_id, language, fhash))
    if hit:
        return hit
    try:
        r = (sb.table("connection_reads").select("card,facts_hash").eq("session_id", session_id).eq("language", language)
             .limit(1).execute().data or [])
        if r and r[0].get("facts_hash") == fhash and isinstance(r[0].get("card"), dict):
            _MEM[(session_id, language, fhash)] = r[0]["card"]
            return r[0]["card"]
    except Exception as e:
        print(f"[connection-card] read skipped (table missing?): {type(e).__name__}")
    return None


def store(sb, session_id: str, language: str, fhash: str, card: dict, model: str = "") -> None:
    _MEM[(session_id, language, fhash)] = card
    try:
        sb.table("connection_reads").upsert({"session_id": session_id, "language": language, "facts_hash": fhash, "card": card,
                                             "model": model, "source": card.get("source", "llm")},
                                            on_conflict="session_id,language").execute()
    except Exception as e:
        print(f"[connection-card] store skipped (table missing?): {type(e).__name__}")
