"""
Onboarding Welcome Prediction — the first-impression Prashna hook.

When a first-time user answers "What brought you to Antar?" we cast a
horary chart for that exact moment and generate a short, striking,
specific welcome prediction tied to the live Moon and their stated
concern. This module owns:

  * the concern-chip → domain mapping (deterministic, no keyword guessing
    for chips; free text only steers the "just curious" path)
  * the synthetic prashna question per chip (crafted so
    prashna_engine.detect_domain resolves to the intended houses)
  * the welcome-prediction LLM prompt (coach voice, zero jargon,
    localized EN/ES)
  * localized static fallbacks if the engine or LLM fails

The endpoint wiring lives in main.py (POST /api/v1/onboarding/welcome-prediction).
IMPORTANT: the onboarding prashna must NEVER write to prashna_log —
that would consume the user's 24h oracle cooldown on their first login.
"""

from typing import Optional, Tuple

# ───────────────────────── concern chips ──────────────────────────────
# Keys are canonical slugs. `aliases` cover the literal chip labels the
# frontend may send. `question` is crafted so detect_domain() hits the
# intended houses ("purpose" requires the DOMAIN_HOUSE_MAP entry added
# by patch_onboarding_welcome.py).

CONCERN_MAP = {
    "career_money": {
        "aliases": ["career & money", "career and money", "career", "money", "career_money"],
        "label_en": "career and money",
        "label_es": "carrera y dinero",
        "question": "Will my career grow in the year ahead?",
        "domain_label": "career",
        "houses": [10],
    },
    "love_relationships": {
        "aliases": ["love & relationships", "love and relationships", "love", "relationships", "love_relationships"],
        "label_en": "love and relationships",
        "label_es": "amor y relaciones",
        "question": "Will my relationship life deepen and flourish?",
        "domain_label": "relationship",
        "houses": [7],
    },
    "health_energy": {
        "aliases": ["health & energy", "health and energy", "health", "energy", "health_energy"],
        "label_en": "health and energy",
        "label_es": "salud y energía",
        "question": "Will my health and vitality improve?",
        "domain_label": "health",
        "houses": [6],
    },
    "life_purpose": {
        "aliases": ["life purpose", "purpose", "life_purpose", "direction"],
        "label_en": "life purpose",
        "label_es": "propósito de vida",
        "question": "Will I find my purpose and true direction?",
        "domain_label": "purpose",
        "houses": [9, 10],
    },
    "just_curious": {
        "aliases": ["just curious", "curious", "just_curious", "exploring"],
        "label_en": "what this moment holds",
        "label_es": "lo que este momento guarda",
        "question": "What does this moment hold for me?",
        "domain_label": "general",
        "houses": [10],
    },
}


def normalize_concern(raw: Optional[str]) -> str:
    """Map whatever the frontend sends (slug or chip label) to a canonical slug."""
    if not raw:
        return "just_curious"
    r = raw.strip().lower()
    for slug, cfg in CONCERN_MAP.items():
        if r == slug or r in cfg["aliases"]:
            return slug
    # Loose containment fallback (e.g. "Career &amp; Money")
    for slug, cfg in CONCERN_MAP.items():
        if any(a in r for a in cfg["aliases"]):
            return slug
    return "just_curious"


def build_welcome_question(slug: str, free_text: Optional[str]) -> Tuple[str, str]:
    """
    Returns (prashna_question, domain_label).
    Chips are deterministic. Free text only drives domain detection on the
    "just curious" path, where the user typed their real reason.
    """
    cfg = CONCERN_MAP.get(slug, CONCERN_MAP["just_curious"])
    ft = (free_text or "").strip()
    if slug == "just_curious" and len(ft) >= 8:
        return ft, "general"
    return cfg["question"], cfg["domain_label"]


def concern_label(slug: str, language: str = "en") -> str:
    cfg = CONCERN_MAP.get(slug, CONCERN_MAP["just_curious"])
    return cfg["label_es"] if (language or "en").lower().startswith("es") else cfg["label_en"]


# ───────────────────────── prompt ──────────────────────────────────────

def build_welcome_prompt(
    engine_result: dict,
    first_name: str,
    slug: str,
    free_text: Optional[str],
    language: str = "en",
) -> str:
    """
    Welcome-prediction system prompt. Deliberately NOT the standard prashna
    explain prompt: this is a first-impression reveal, not a yes/no verdict
    card. Short, second person, specific, zero astrological vocabulary.
    """
    lang = (language or "en").lower()[:2]
    label = concern_label(slug, lang)
    bd = engine_result.get("breakdown", {})
    pc = engine_result.get("prashna_chart", {})
    moon_v = bd.get("moon_validation", {})
    confluence = engine_result.get("confluence", {})

    facts = f"""COMPUTED FACTS (translate everything — never quote these terms):
- Their stated reason for coming: {label}
- What they typed (optional): {free_text or '(nothing)'}
- Verdict for this area right now: {engine_result.get('verdict')} ({engine_result.get('score')}%)
- Timing signal: {engine_result.get('timing')}
- The Moon at this exact moment: house {moon_v.get('moon_house')}, {'waxing (building)' if moon_v.get('waxing') else 'waning (releasing)'}
- Moon read: {moon_v.get('reason', '')}
- Environment read: {bd.get('lagna_strength', {}).get('reason', '')}
- Connection read: {bd.get('lord_connection', {}).get('reason', '')}
- Momentum read: {bd.get('ithasala', {}).get('reason', '')}
- Intent-birth sync: {'YES — the moment they chose to arrive echoes a pattern in their own birth chart' if confluence.get('sync_detected') else 'not detected'}"""

    lang_rule = (
        "Write ENTIRELY in natural, warm Latin American Spanish (tú form)."
        if lang == "es"
        else "Write in natural, warm English."
    )

    return f"""You are Antar, welcoming {first_name or 'a new user'} the moment they arrive. They just told you what brought them here. A precise calculation was run on the sky at the EXACT moment they answered — your job is to turn it into one short, striking welcome reading that makes them feel seen.

{facts}

RULES — non-negotiable:
- 70 to 110 words. One flowing paragraph, or two short ones. No headings, no lists.
- {lang_rule}
- ZERO astrological vocabulary. Never say Moon, planet names, houses, signs, nakshatra, chart, horary, or any Sanskrit. Translate everything into plain, concrete language about timing and real life ("the moment you chose to ask", "a window opening", "the next few weeks"). Never use the word "energy", "vibration", or any abstract noun-phrase.
- Structure: (1) name the exact moment they arrived carrying this question about {label} — make it feel deliberate, not random; (2) ONE specific observation drawn from the strongest computed fact above — concrete, not horoscope-generic; (3) end with a forward hook tied to the timing signal — what to watch for, without promising outcomes.
- If intent-birth sync is YES, weave in one line that the timing of their arrival mirrors something already written in them — this is the wow, use it.
- Confident, warm, precise coach voice. READABILITY (NON-NEGOTIABLE): one idea per
  sentence; sentences under 18 words; everyday words; first sentence lands the point;
  end with one concrete thing to watch or do. No hedging ("maybe", "perhaps"), no flattery, no emojis, no greeting clichés ("Welcome to Antar!").
- Do NOT mention the verdict percentage or the words yes/no. This is a reading, not a scorecard."""


# ───────────────────────── fallbacks ───────────────────────────────────

_FALLBACK = {
    "en": {
        "career_money": "You arrived carrying a question about your work and what it builds. That timing matters more than you think — the current around effort and reward is shifting right now, and the next few weeks will show you exactly where to push. Watch for one conversation that opens a door you'd assumed was closed.",
        "love_relationships": "You came here holding a question about connection. The moment you chose to ask sits inside a current that favors honesty over performance — what's real strengthens, what's performed thins out. In the coming weeks, notice who moves toward you without being asked. That's your signal.",
        "health_energy": "You arrived asking about your body and your energy — and the timing of that question is itself the first answer. A cycle of depletion is ending its grip. Small, repeated acts of repair will compound faster than usual now. Watch how mornings feel two weeks from today.",
        "life_purpose": "You came with the biggest question there is — direction. The moment you chose to ask it carries a building current, the kind that rewards commitment over searching. Something you already do effortlessly is the thread. In the coming weeks, notice what people keep asking of you. That's not coincidence.",
        "just_curious": "Even curiosity has timing — and yours brought you here at a moment that favors beginnings. There's a building current around you right now: questions asked in it tend to organize themselves into answers faster than usual. Sit with what you'd really want to know. It will sharpen within days.",
    },
    "es": {
        "career_money": "Llegaste con una pregunta sobre tu trabajo y lo que construye. Ese momento importa más de lo que crees — la corriente entre esfuerzo y recompensa está cambiando ahora mismo, y las próximas semanas te mostrarán exactamente dónde empujar. Atento a una conversación que abre una puerta que creías cerrada.",
        "love_relationships": "Viniste con una pregunta sobre conexión. El momento que elegiste para preguntar está dentro de una corriente que favorece la honestidad sobre la apariencia — lo real se fortalece, lo actuado se desvanece. En las próximas semanas, fíjate en quién se acerca a ti sin que lo pidas. Esa es tu señal.",
        "health_energy": "Llegaste preguntando por tu cuerpo y tu energía — y el momento de esa pregunta es en sí la primera respuesta. Un ciclo de desgaste está soltando su agarre. Los actos pequeños y repetidos de reparación se acumularán más rápido de lo habitual. Observa cómo se sienten tus mañanas en dos semanas.",
        "life_purpose": "Viniste con la pregunta más grande que existe — la dirección. El momento que elegiste lleva una corriente en ascenso, de las que premian el compromiso sobre la búsqueda. Algo que ya haces sin esfuerzo es el hilo. En las próximas semanas, nota qué te pide la gente una y otra vez. No es coincidencia.",
        "just_curious": "Hasta la curiosidad tiene su momento — y la tuya te trajo aquí en uno que favorece los comienzos. Hay una corriente en ascenso a tu alrededor: las preguntas hechas dentro de ella tienden a ordenarse en respuestas más rápido de lo habitual. Quédate con lo que de verdad querrías saber. Se aclarará en días.",
    },
}


def fallback_prediction(slug: str, language: str = "en") -> str:
    lang = "es" if (language or "en").lower().startswith("es") else "en"
    return _FALLBACK[lang].get(slug, _FALLBACK[lang]["just_curious"])
