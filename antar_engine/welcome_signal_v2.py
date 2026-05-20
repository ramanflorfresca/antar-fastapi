"""
Welcome Signal v2 — Jaimini-Powered 3-Signal WOW Engine
========================================================
Antar Platform · Sprint W + F01 · March 31, 2026

This module generates the 3-signal welcome experience:
  Signal 1 — The Mirror (Identity): Who you ARE, not what will happen.
  Signal 2 — The Chapter (Timing): The life chapter you're in RIGHT NOW.
  Signal 3 — The Signal (Action): One specific thing to watch for in 60-90 days.

Key upgrade from v1:
  - Jaimini Karakas power the Mirror (AK = soul type, AmK = career DNA)
  - Chara Dasha + Moving Lagna power the Chapter (sign-based timing)
  - Event predictions + Rashi Drishti power the Signal (outcome certainty)
  - Age intelligence: temporal floor, Umra filter, future-date guard
  - Karakamsa Career DNA table gives specificity to career signals

Integration:
  Called from main.py at GET /api/v1/welcome/{chart_id}
  Stores result in welcome_signals table (cached, fire-and-forget)

File: antar_engine/welcome_signal_v2.py
"""

import json
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List

# [output-strips] migrate welcome_signal_v2
from antar_engine.output_strips import apply_user_facing_strips

logger = logging.getLogger("antar.welcome_signal")

# =============================================================================
# BANNED TERMS — Zero Sanskrit in user-facing output
# =============================================================================

BANNED_TERMS = [
    "mahadasha", "antardasha", "atmakaraka", "amatyakaraka", "darakaraka",
    "bhratrukaraka", "matrukaraka", "putrakaraka", "gnatikaraka",
    "navamsa", "navamsha", "vimsottari", "ashtottari", "lagna",
    "nakshatra", "tithi", "rashi", "drishti", "argala", "virodhargala",
    "karakamsa", "arudha", "upapada", "chara dasha", "yoga", "dosha",
    "graha", "bhava", "rahu", "ketu", "mangal", "shani", "budh", "guru",
    "shukra", "surya", "chandra", "karaka", "dasha lord", "sign lord",
    "house lord", "planetary period", "vedic", "jyotish", "kundali",
    "horoscope", "zodiac sign",
]


def banned_terms_check(text: str) -> List[str]:
    """Check text for banned Sanskrit/jargon terms. Returns list of found terms."""
    text_lower = text.lower()
    return [term for term in BANNED_TERMS if term in text_lower]


# =============================================================================
# AGE INTELLIGENCE
# =============================================================================

def calculate_current_age(birth_date_str: str) -> int:
    """
    Calculate current age from birth date string.
    Handles birthday-not-yet-this-year edge case.
    """
    if not birth_date_str:
        return 30  # Safe fallback

    try:
        if "T" in str(birth_date_str):
            birth_date_str = str(birth_date_str).split("T")[0]
        bd = datetime.strptime(str(birth_date_str), "%Y-%m-%d").date()
        today = date.today()
        age = today.year - bd.year
        if (today.month, today.day) < (bd.month, bd.day):
            age -= 1
        return max(age, 0)
    except (ValueError, TypeError):
        return 30


def get_floor_age(current_age: int) -> int:
    """Temporal floor: never reference events below this age."""
    return max(current_age - 5, 16)


def filter_umra_for_age(current_age: int) -> List[Dict[str, Any]]:
    """
    Only include Umra activations where activation_age >= current_age - 2.
    Return next 2 upcoming activations sorted ascending.
    """
    UMRA_TABLE = [
        {"house": 1, "age": 1, "theme": "Self, personality, health"},
        {"house": 2, "age": 2, "theme": "Wealth, family, speech"},
        {"house": 3, "age": 16, "theme": "Courage, siblings, communication"},
        {"house": 4, "age": 4, "theme": "Home, mother, property"},
        {"house": 5, "age": 15, "theme": "Children, intelligence, speculation"},
        {"house": 6, "age": 6, "theme": "Enemies, debts, disease"},
        {"house": 7, "age": 34, "theme": "Marriage, partnerships"},
        {"house": 8, "age": 36, "theme": "Transformation, inheritance"},
        {"house": 9, "age": 30, "theme": "Fortune, father, dharma"},
        {"house": 10, "age": 22, "theme": "Career — first activation"},
        {"house": 10, "age": 48, "theme": "Career — peak authority"},
        {"house": 11, "age": 54, "theme": "Gains, elder siblings, income"},
        {"house": 12, "age": 60, "theme": "Spirituality, foreign, liberation"},
    ]
    floor = current_age - 2
    upcoming = [u for u in UMRA_TABLE if u["age"] >= floor]
    upcoming.sort(key=lambda x: x["age"])
    return upcoming[:2]


# =============================================================================
# JAIMINI CONTEXT BUILDER FOR WELCOME SIGNAL
# =============================================================================

def _get_karaka_by_code(karakas: List[Dict], code: str) -> Optional[Dict]:
    """Find a karaka by its code (AK, AmK, DK, etc.)"""
    for k in karakas:
        if k.get("karaka") == code:
            return k
    return None


# Karakamsa Career DNA — maps planet to professional archetype
CAREER_DNA = {
    "Sun": "leadership, public authority, and governance",
    "Moon": "intuition, psychology, creative arts, and nurturing",
    "Mars": "engineering, sports, surgery, and decisive action",
    "Mercury": "business, writing, communication, and technology",
    "Jupiter": "teaching, law, philosophy, and advisory",
    "Venus": "design, luxury, entertainment, and diplomacy",
    "Saturn": "long-term research, manufacturing, and disciplined mastery",
    "Ketu": "high-tech, mathematics, spirituality, and hidden knowledge",
    "Rahu": "foreign ventures, innovation, and unconventional paths",
}

# Lagna + Moon personality archetypes for Mirror signal
LAGNA_ARCHETYPES = {
    0: "You lead with instinct. Decision first, explanation later. People either follow you or step aside.",
    1: "You build slowly and permanently. What you commit to, you finish. Rushing feels wrong because it is — for you.",
    2: "You process the world through questions. The answer is never enough — you need to understand how the answer was reached.",
    3: "You absorb the room before speaking. Your emotional radar is precise, and you trust it more than any argument.",
    4: "You need to be seen — not for vanity, but because invisibility feels like a form of dishonesty about who you are.",
    5: "You notice what others miss. Details, patterns, inconsistencies — your mind catalogues everything, and this makes you invaluable and exhausting in equal measure.",
    6: "You weigh every side before choosing. This is not indecision — it is precision. The people closest to you know that once you decide, it is final.",
    7: "You run on intensity. Half-measures feel dishonest. You either commit fully or walk away, and there is no in-between.",
    8: "You aim further than anyone around you thinks is reasonable. The gap between where you are and where you are going is what drives you.",
    9: "You build structures — in your career, in your relationships, in your mind. What you create is meant to last longer than you.",
    10: "You think in systems. While others see events, you see the pattern connecting them. This makes you ahead of most people and lonely among them.",
    11: "You hold contradictions comfortably. You are deeply private and deeply connected. Spiritual and pragmatic. This duality is not a flaw — it is your superpower.",
}

MOON_MODIFIERS = {
    0: "Your emotional reactions are fast and fierce — you process anger before sadness.",
    1: "You find stability through beauty, comfort, and the physical world. Chaos in your environment creates chaos in your mind.",
    2: "Your mind never stops. You think in multiple tracks simultaneously, and silence makes you uneasy.",
    3: "You feel everything. The mood of a room, the unspoken tension, the thing no one will say — you feel it all before anyone speaks.",
    4: "You need recognition for what you feel, not just what you do. Being overlooked emotionally is worse than being overlooked professionally.",
    5: "You process emotions through analysis. You understand your feelings by taking them apart, and this sometimes frustrates people who just want you to feel.",
    6: "You need harmony — not as a luxury, but as a precondition for functioning. Conflict drains you physically.",
    7: "Your emotional depth is extreme. You love deeply, hurt deeply, and remember everything. Forgiveness is not your first instinct.",
    8: "You process through movement — physical or mental. Sitting with a problem does not work for you. Walking, traveling, doing — that is where your clarity comes from.",
    9: "You carry responsibility like a second skin. Other people's problems become yours, not out of kindness alone, but because you cannot stop yourself.",
    10: "You process emotion intellectually. You step back, observe your own reactions, and sometimes this makes you appear detached when you are anything but.",
    11: "You absorb the emotional frequency of everyone around you. Boundaries are a learned skill for you, not a natural one.",
}


def build_welcome_context_v2(
    chart_data: Dict[str, Any],
    birth_date_str: str,
) -> Dict[str, Any]:
    """
    Build the complete context block for the Welcome Signal Claude call.
    Returns a dict with all data needed for the system prompt interpolation.

    Sources:
      - Jaimini: karakas, AL, UL, karakamsa, current MD/AD, moving lagna, predictions
      - Vimsottari: current MD/AD from dasha_periods
      - Natal: lagna, moon sign, moon nakshatra
      - Age: current_age, floor_age, filtered Umra
      - Lal Kitab: year lord from lal_kitab_data (if available)
    """
    # ── Basic chart info ──
    lagna_sign = chart_data.get("lagna_sign", "")
    moon_sign = chart_data.get("moon_sign", "")
    moon_nakshatra = chart_data.get("moon_nakshatra", "")
    first_name = chart_data.get("first_name") or chart_data.get("name") or "this person"

    # ── Lagna index ──
    SIGN_NAMES = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    try:
        lagna_idx = SIGN_NAMES.index(lagna_sign.title())
    except (ValueError, AttributeError):
        lagna_idx = 0

    try:
        moon_idx = SIGN_NAMES.index(moon_sign.title())
    except (ValueError, AttributeError):
        moon_idx = 3  # fallback Cancer

    # ── Age intelligence ──
    current_age = calculate_current_age(birth_date_str)
    floor_age = get_floor_age(current_age)
    upcoming_umra = filter_umra_for_age(current_age)

    # ── Jaimini data (from stored JSONB) ──
    jaimini_data = chart_data.get("jaimini_data", {})
    if isinstance(jaimini_data, str):
        try:
            jaimini_data = json.loads(jaimini_data)
        except (json.JSONDecodeError, TypeError):
            jaimini_data = {}

    karakas = jaimini_data.get("karakas", [])
    al = jaimini_data.get("arudha_lagna", {})
    ul = jaimini_data.get("upapada_lagna", {})
    karakamsa = jaimini_data.get("karakamsa", {})
    jaimini_md = jaimini_data.get("current_md", {})
    jaimini_ad = jaimini_data.get("current_ad", {})
    moving_lagna = jaimini_data.get("moving_lagna", {})
    jaimini_predictions = jaimini_data.get("predictions", [])
    rashi_drishti = jaimini_data.get("rashi_drishti_ad", [])

    # ── AK and AmK for Mirror ──
    ak = _get_karaka_by_code(karakas, "AK")
    amk = _get_karaka_by_code(karakas, "AmK")
    dk = _get_karaka_by_code(karakas, "DK")

    # ── Karakamsa Career DNA ──
    career_dna = ""
    if karakamsa:
        kl_sign = karakamsa.get("sign_name", "")
        # Find planets in or aspecting karakamsa for career DNA
        # Use the AK planet itself as primary career indicator
        if ak:
            ak_planet = ak.get("planet", "")
            career_dna = CAREER_DNA.get(ak_planet, "")

    # ── Mirror building blocks ──
    lagna_archetype = LAGNA_ARCHETYPES.get(lagna_idx, "")
    moon_modifier = MOON_MODIFIERS.get(moon_idx, "")

    # ── Lal Kitab data (if available) ──
    lk_data = chart_data.get("lal_kitab_data", {})
    if isinstance(lk_data, str):
        try:
            lk_data = json.loads(lk_data)
        except (json.JSONDecodeError, TypeError):
            lk_data = {}

    year_lord = lk_data.get("year_lord", "")

    # ── Vimsottari dasha (from stored dasha text or dasha_periods) ──
    current_dasha = chart_data.get("current_dasha", "")

    # ── Build the Chapter timing ──
    chapter_sign = ""
    chapter_years = ""
    chapter_start = ""
    chapter_end = ""
    chapter_direction = ""
    if jaimini_md:
        chapter_sign = jaimini_md.get("sign_name", "")
        chapter_years = str(jaimini_md.get("years", ""))
        chapter_start = jaimini_md.get("start", "")[:10] if jaimini_md.get("start") else ""
        chapter_end = jaimini_md.get("end", "")[:10] if jaimini_md.get("end") else ""
        chapter_direction = jaimini_md.get("direction", "")

    sub_period_sign = ""
    sub_period_end = ""
    if jaimini_ad:
        sub_period_sign = jaimini_ad.get("sign_name", "")
        sub_period_end = jaimini_ad.get("end", "")[:10] if jaimini_ad.get("end") else ""

    # ── Future date guard ──
    today_str = date.today().isoformat()
    if chapter_end and chapter_end < today_str:
        chapter_end = ""  # Skip past dates — LLM should not reference them

    # ── Build the Signal from Jaimini predictions ──
    best_prediction = None
    for p in jaimini_predictions:
        if p.get("confidence") == "high":
            best_prediction = p
            break
    if not best_prediction and jaimini_predictions:
        best_prediction = jaimini_predictions[0]

    signal_event = ""
    signal_domain = "career"  # default
    signal_conditions = []
    if best_prediction:
        signal_event = best_prediction.get("description", "")
        etype = best_prediction.get("event_type", "career")
        signal_conditions = best_prediction.get("conditions", [])
        # Map event type to user-facing domain
        domain_map = {
            "career": "career", "wealth": "financial", "marriage": "relationship",
            "children": "relationship", "health": "health", "property": "financial",
        }
        signal_domain = domain_map.get(etype, "career")

    # ── Moving Lagna effects for Chapter enrichment ──
    ml_effects = []
    for key in ["ak_effect", "amk_effect", "dk_effect", "al_effect", "ul_effect"]:
        effect = moving_lagna.get(key, "")
        if effect and "Neutral" not in effect:
            ml_effects.append(effect)

    return {
        "first_name": first_name,
        "current_age": current_age,
        "floor_age": floor_age,
        "lagna_sign": lagna_sign,
        "moon_sign": moon_sign,
        "moon_nakshatra": moon_nakshatra,
        "lagna_archetype": lagna_archetype,
        "moon_modifier": moon_modifier,
        "ak_planet": ak.get("planet", "") if ak else "",
        "ak_meaning": ak.get("meaning", "") if ak else "",
        "amk_planet": amk.get("planet", "") if amk else "",
        "dk_planet": dk.get("planet", "") if dk else "",
        "career_dna": career_dna,
        "karakamsa_sign": karakamsa.get("sign_name", ""),
        "al_sign": al.get("sign_name", ""),
        "ul_sign": ul.get("sign_name", ""),
        "current_dasha": current_dasha,
        "chapter_sign": chapter_sign,
        "chapter_years": chapter_years,
        "chapter_end": chapter_end,
        "sub_period_sign": sub_period_sign,
        "sub_period_end": sub_period_end,
        "rashi_drishti": rashi_drishti,
        "ml_effects": ml_effects,
        "signal_event": signal_event,
        "signal_domain": signal_domain,
        "signal_conditions": signal_conditions,
        "upcoming_umra": upcoming_umra,
        "year_lord": year_lord,
        "jaimini_predictions": jaimini_predictions,
        "today": today_str,
    }


# =============================================================================
# SYSTEM PROMPT — The exact instruction sent to Claude Sonnet
# =============================================================================

WELCOME_SYSTEM_PROMPT = """You are Antar — a precise, empathetic life navigation advisor.

Generate three signals for {first_name}. This is their first impression of Antar. It must be unforgettable.

ABOUT THIS PERSON:
- Age: {current_age} years old
- Rising energy: {lagna_sign}
- Emotional processing: {moon_sign} ({moon_nakshatra})
- Soul significator: {ak_planet} ({ak_meaning})
- Career significator: {amk_planet}
- Career DNA: {career_dna}
- Current life chapter (sign-based timing): {chapter_sign} period ({chapter_years} years, ends {chapter_end})
- Current sub-chapter: {sub_period_sign} (ends {sub_period_end})
- Signs being influenced right now: {rashi_drishti_str}
- Public image point: {al_sign}
- Marriage point: {ul_sign}
- Active life effects: {ml_effects_str}
- Upcoming age activations: {umra_str}

CHARACTER BUILDING BLOCKS (use these to craft Signal 1):
Rising archetype: "{lagna_archetype}"
Emotional signature: "{moon_modifier}"

SIGNAL 1 — THE MIRROR
One precise character insight. Personal. Slightly uncomfortable in its accuracy. This is about who {first_name} IS — not what will happen. Use the character building blocks above as raw material but rewrite them in your own voice — do NOT copy them verbatim. 2-3 sentences. Must feel like something only someone who truly knows them would say.

SIGNAL 2 — THE CHAPTER: Name the exact life chapter {first_name} is in.
Their {chapter_sign} period governs the next phase. The sub-chapter is {sub_period_sign}.
Active effects in this period: {ml_effects_str}
{signal_event_context}
Name the chapter in 3-5 words. Include what this period is asking of them and one specific event or decision arriving before a named date. The date MUST be in the future (after {today}). 3-4 sentences.

SIGNAL 3 — THE SIGNAL
One specific thing to watch for in the next 60-90 days.
Domain: {signal_domain}
{signal_conditions_str}
Name the domain. Give a specific date range. End with one concrete thing to watch for or act on. 2-3 sentences.

ABSOLUTE RULES:
1. {first_name} is {current_age} years old. NEVER reference events or themes from before age {floor_age}.
2. Zero Sanskrit terms. Zero astrological jargon. Plain English only.
3. Each signal is 2-4 sentences. No padding. No hedging. No "your chart shows."
4. State facts directly. Do not say "astrologically speaking" or "the stars suggest."
5. All dates in Signal 2 and Signal 3 MUST be in the future (after {today}). Never reference a past date.
6. Signal 2 MUST include a timing field with the specific Month YYYY format.
7. Signal 3 MUST include domain (one of: career/relationship/financial/health/travel/legal) and watch_for.
8. Do NOT copy the character building blocks word-for-word. Use them as raw material and rewrite.

Return EXACTLY this JSON and nothing else — no markdown, no backticks, no preamble:
{{"signal_1": {{"type": "mirror", "headline": "<12 words max>", "body": "..."}}, "signal_2": {{"type": "chapter", "headline": "<chapter name 3-5 words>", "body": "...", "timing": "<Month YYYY>"}}, "signal_3": {{"type": "signal", "headline": "<12 words max>", "body": "...", "domain": "{signal_domain}", "watch_for": "..."}}}}"""


WELCOME_SYSTEM_PROMPT_ES = """Eres Antar — un guía de navegación de vida preciso y empático.

Genera tres señales para {first_name}. Esta es su primera impresión de Antar.  Debe ser inolvidable.

SOBRE ESTA PERSONA:
- Edad: {current_age} años
- Energía ascendente: {lagna_sign}
- Procesamiento emocional: {moon_sign} ({moon_nakshatra})
- Significador del alma: {ak_planet} ({ak_meaning})
- Significador de carrera: {amk_planet}
- ADN profesional: {career_dna}
- Capítulo de vida actual (tiempo por signo): período {chapter_sign} ({chapter_years} años, termina {chapter_end})
- Sub-capítulo actual: {sub_period_sign} (termina {sub_period_end})
- Signos bajo influencia ahora mismo: {rashi_drishti_str}
- Punto de imagen pública: {al_sign}
- Punto de pareja: {ul_sign}
- Efectos activos de vida: {ml_effects_str}
- Activaciones por edad próximas: {umra_str}

BLOQUES PARA CONSTRUIR EL CARÁCTER (úsalos para crear la Señal 1):
Arquetipo ascendente: "{lagna_archetype}"
Firma emocional: "{moon_modifier}"

SEÑAL 1 — EL ESPEJO
Una observación precisa sobre su carácter. Personal. Ligeramente incómoda por su precisión. Esta es sobre quién ES {first_name} — no sobre lo que ocurrirá.  Usa los bloques de arriba como materia prima pero reescríbelos con tu propia voz — NO los copies literalmente.  2-3 frases. Debe sentirse como algo que solo alguien que realmente la conoce diría.

SEÑAL 2 — EL CAPÍTULO: Nombra el capítulo de vida exacto en el que está {first_name}.
Su período {chapter_sign} gobierna la próxima fase. El sub-capítulo es {sub_period_sign}.
Efectos activos en este período: {ml_effects_str}
{signal_event_context}
Nombra el capítulo en 3-5 palabras. Incluye lo que este período le está pidiendo y un evento o decisión específica que llega antes de una fecha nombrada.  La fecha DEBE ser futura (posterior a {today}).  3-4 frases.

SEÑAL 3 — LA SEÑAL
Una cosa específica que vigilar en los próximos 60-90 días.
Dominio: {signal_domain}
{signal_conditions_str}
Nombra el dominio. Da un rango de fechas específico. Termina con una cosa concreta que vigilar o hacer.  2-3 frases.

REGLAS ABSOLUTAS:
1. {first_name} tiene {current_age} años.  NUNCA hagas referencia a eventos o temas de antes de los {floor_age} años.
2. Cero términos en sánscrito. Cero jerga astrológica. Solo español claro.
3. Cada señal tiene 2-4 frases. Sin relleno. Sin titubeo. Nada de "tu carta muestra".
4. Declara los hechos directamente. No digas "astrológicamente hablando" ni "las estrellas sugieren".
5. Todas las fechas en la Señal 2 y la Señal 3 DEBEN ser futuras (posteriores a {today}). Nunca referencies una fecha pasada.
6. La Señal 2 DEBE incluir un campo `timing` con el formato "Mes YYYY" (en inglés como "December 2026" para compatibilidad con el parser).
7. La Señal 3 DEBE incluir `domain` (uno de: career/relationship/financial/health/travel/legal) y `watch_for`.
8. NO copies los bloques de construcción de carácter palabra por palabra. Úsalos como materia prima y reescríbelos.
9. Todo el texto narrativo (headline, body, watch_for, timing chapter-name) va en ESPAÑOL.  Los valores de `domain` y `type` se mantienen en inglés (son identificadores internos). El valor de `timing` mantiene el mes en inglés para que el parser lo lea (ej. "December 2026").

Devuelve EXACTAMENTE este JSON y nada más — sin markdown, sin backticks, sin preámbulo:
{{"signal_1": {{"type": "mirror", "headline": "<máx 12 palabras>", "body": "..."}}, "signal_2": {{"type": "chapter", "headline": "<nombre del capítulo 3-5 palabras>", "body": "...", "timing": "<Month YYYY en inglés>"}}, "signal_3": {{"type": "signal", "headline": "<máx 12 palabras>", "body": "...", "domain": "{signal_domain}", "watch_for": "..."}}}}"""


WELCOME_SYSTEM_PROMPT_PT = """Você é Antar — um guia de navegação de vida preciso e empático.

Gere três sinais para {first_name}. Esta é a primeira impressão dela sobre o Antar. Precisa ser inesquecível.

SOBRE ESTA PESSOA:
- Idade: {current_age} anos
- Energia ascendente: {lagna_sign}
- Processamento emocional: {moon_sign} ({moon_nakshatra})
- Significador da alma: {ak_planet} ({ak_meaning})
- Significador de carreira: {amk_planet}
- DNA profissional: {career_dna}
- Capítulo de vida atual (tempo por signo): período {chapter_sign} ({chapter_years} anos, termina {chapter_end})
- Subcapítulo atual: {sub_period_sign} (termina {sub_period_end})
- Signos sob influência neste momento: {rashi_drishti_str}
- Ponto de imagem pública: {al_sign}
- Ponto de parceria: {ul_sign}
- Efeitos de vida ativos: {ml_effects_str}
- Ativações por idade que se aproximam: {umra_str}

BLOCOS PARA CONSTRUIR O CARÁTER (use-os para criar o Sinal 1):
Arquétipo ascendente: "{lagna_archetype}"
Assinatura emocional: "{moon_modifier}"

SINAL 1 — O ESPELHO
Uma observação precisa sobre o caráter dela. Pessoal. Levemente desconfortável pela precisão. Este é sobre quem {first_name} É — não sobre o que vai acontecer. Use os blocos acima como matéria-prima, mas reescreva-os com a sua própria voz — NÃO os copie literalmente. 2-3 frases. Deve soar como algo que só alguém que realmente a conhece diria.

SINAL 2 — O CAPÍTULO: Nomeie o capítulo de vida exato em que {first_name} está.
O período {chapter_sign} dela governa a próxima fase. O subcapítulo é {sub_period_sign}.
Efeitos ativos neste período: {ml_effects_str}
{signal_event_context}
Nomeie o capítulo em 3-5 palavras. Inclua o que este período está pedindo a ela e um evento ou decisão específica que chega antes de uma data nomeada. A data DEVE ser futura (posterior a {today}). 3-4 frases.

SINAL 3 — O SINAL
Uma coisa específica para observar nos próximos 60-90 dias.
Domínio: {signal_domain}
{signal_conditions_str}
Nomeie o domínio. Dê um intervalo de datas específico. Termine com uma coisa concreta para observar ou fazer. 2-3 frases.

REGRAS ABSOLUTAS:
1. {first_name} tem {current_age} anos. NUNCA faça referência a eventos ou temas anteriores aos {floor_age} anos.
2. Zero termos em sânscrito. Zero jargão astrológico. Apenas português claro.
3. Cada sinal tem 2-4 frases. Sem enrolação. Sem hesitação. Nada de "seu mapa mostra".
4. Declare os fatos diretamente. Não diga "astrologicamente falando" nem "os astros sugerem".
5. Todas as datas no Sinal 2 e no Sinal 3 DEVEM ser futuras (posteriores a {today}). Nunca referencie uma data passada.
6. O Sinal 2 DEVE incluir um campo `timing` no formato "Mês AAAA" (em inglês, como "December 2026", para compatibilidade com o parser).
7. O Sinal 3 DEVE incluir `domain` (um de: career/relationship/financial/health/travel/legal) e `watch_for`.
8. NÃO copie os blocos de construção de caráter palavra por palavra. Use-os como matéria-prima e reescreva-os.
9. Todo o texto narrativo (headline, body, watch_for, nome do capítulo) vai em PORTUGUÊS. Os valores de `domain` e `type` permanecem em inglês (são identificadores internos). O valor de `timing` mantém o mês em inglês para que o parser o leia (ex.: "December 2026").

Retorne EXATAMENTE este JSON e nada mais — sem markdown, sem crases, sem preâmbulo:
{{"signal_1": {{"type": "mirror", "headline": "<máx 12 palavras>", "body": "..."}}, "signal_2": {{"type": "chapter", "headline": "<nome do capítulo 3-5 palavras>", "body": "...", "timing": "<Month YYYY em inglês>"}}, "signal_3": {{"type": "signal", "headline": "<máx 12 palavras>", "body": "...", "domain": "{signal_domain}", "watch_for": "..."}}}}"""


def _select_system_prompt_v2(language: Optional[str]) -> str:
    """Pick the v2 system prompt template for the user's language. English fallback."""
    code = (language or "en").lower()[:2]
    if code == "es":
        return WELCOME_SYSTEM_PROMPT_ES
    if code == "pt":
        return WELCOME_SYSTEM_PROMPT_PT
    return WELCOME_SYSTEM_PROMPT


def build_system_prompt(ctx: Dict[str, Any]) -> str:
    """Interpolate the context into the system prompt."""
    # Format list fields
    rashi_drishti_str = ", ".join(ctx.get("rashi_drishti", [])) or "none active"
    ml_effects_str = " | ".join(ctx.get("ml_effects", [])) or "steady period"
    umra_str = "; ".join(
        f"Age {u['age']}: {u['theme']}" for u in ctx.get("upcoming_umra", [])
    ) or "none upcoming"

    signal_conditions_str = ""
    if ctx.get("signal_conditions"):
        signal_conditions_str = "Supporting evidence: " + " | ".join(ctx["signal_conditions"])

    signal_event_context = ""
    if ctx.get("signal_event"):
        signal_event_context = f"Jaimini event signal: {ctx['signal_event']}"

    # [i18n] pick English/Spanish template based on ctx['language'] (threaded from generate_welcome_signal_v2)
    _tpl = _select_system_prompt_v2(ctx.get("language"))
    return _tpl.format(
        first_name=ctx.get("first_name", "this person"),
        current_age=ctx.get("current_age", 30),
        floor_age=ctx.get("floor_age", 16),
        lagna_sign=ctx.get("lagna_sign", ""),
        moon_sign=ctx.get("moon_sign", ""),
        moon_nakshatra=ctx.get("moon_nakshatra", ""),
        ak_planet=ctx.get("ak_planet", ""),
        ak_meaning=ctx.get("ak_meaning", ""),
        amk_planet=ctx.get("amk_planet", ""),
        career_dna=ctx.get("career_dna", ""),
        chapter_sign=ctx.get("chapter_sign", ""),
        chapter_years=ctx.get("chapter_years", ""),
        chapter_end=ctx.get("chapter_end", ""),
        sub_period_sign=ctx.get("sub_period_sign", ""),
        sub_period_end=ctx.get("sub_period_end", ""),
        rashi_drishti_str=rashi_drishti_str,
        al_sign=ctx.get("al_sign", ""),
        ul_sign=ctx.get("ul_sign", ""),
        ml_effects_str=ml_effects_str,
        lagna_archetype=ctx.get("lagna_archetype", ""),
        moon_modifier=ctx.get("moon_modifier", ""),
        signal_domain=ctx.get("signal_domain", "career"),
        signal_event_context=signal_event_context,
        signal_conditions_str=signal_conditions_str,
        umra_str=umra_str,
        today=ctx.get("today", ""),
    )


# =============================================================================
# RESPONSE PARSING
# =============================================================================

def parse_welcome_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse Claude's JSON response into the 3-signal structure.
    Handles markdown fences, preamble text, and malformed JSON gracefully.
    """
    text = raw_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.replace("```json", "").replace("```", "").strip()

    # Try to find JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse welcome signal JSON: {text[:200]}")
        return None

    # Validate structure
    required = ["signal_1", "signal_2", "signal_3"]
    for key in required:
        if key not in data:
            logger.error(f"Missing {key} in welcome signal response")
            return None

    return data


def validate_welcome_signals(data: Dict[str, Any], current_age: int) -> Dict[str, Any]:
    """
    Post-validation: check for banned terms, future dates, and structure.
    Returns the validated data with any corrections applied.
    """
    issues = []

    # Check banned terms across all signal bodies
    for key in ["signal_1", "signal_2", "signal_3"]:
        signal = data.get(key, {})
        for field in ["headline", "body", "watch_for"]:
            text = signal.get(field, "")
            found = banned_terms_check(text)
            if found:
                issues.append(f"{key}.{field} contains banned terms: {found}")

    # Check Signal 2 timing is in the future
    s2 = data.get("signal_2", {})
    timing = s2.get("timing", "")
    if timing:
        try:
            # Parse "Month YYYY" format
            timing_date = datetime.strptime(timing, "%B %Y").date()
            if timing_date < date.today():
                issues.append(f"Signal 2 timing is in the past: {timing}")
        except ValueError:
            pass  # Non-standard format, let it through

    # Check Signal 3 has required fields
    s3 = data.get("signal_3", {})
    valid_domains = {"career", "relationship", "financial", "health", "travel", "legal"}
    if s3.get("domain", "").lower() not in valid_domains:
        issues.append(f"Signal 3 domain invalid: {s3.get('domain')}")
    if not s3.get("watch_for"):
        issues.append("Signal 3 missing watch_for field")

    if issues:
        logger.warning(f"Welcome signal validation issues: {issues}")
        data["_validation_issues"] = issues

    return data


# =============================================================================
# MAIN GENERATOR — Called from the /welcome endpoint
# =============================================================================

async def generate_welcome_signal_v2(
    chart_data: Dict[str, Any],
    birth_date: Optional[str] = None,
    anthropic_client=None,
    language: Optional[str] = "en",
) -> Dict[str, Any]:
    """
    Generate the 3-signal welcome experience.

    This is an async function called from main.py at:
      GET /api/v1/welcome/{chart_id}

    Args:
        chart_data: Full chart row from Supabase
        birth_date: Birth date string (YYYY-MM-DD), or extracted from chart_data
        anthropic_client: Anthropic client instance for Claude API calls

    Returns:
        {
            "signal_1": {"type": "mirror", "headline": str, "body": str},
            "signal_2": {"type": "chapter", "headline": str, "body": str, "timing": str},
            "signal_3": {"type": "signal", "headline": str, "body": str, "domain": str, "watch_for": str},
            "chart_id": str,
            "generated_at": str,
        }
    """
    chart_id = chart_data.get("id", "")

    # Resolve birth_date
    if not birth_date:
        birth_date = chart_data.get("birth_date", "")
    if not birth_date:
        logger.error(f"No birth_date for chart {chart_id}")
        return _fallback_response(chart_id, language=language)

    try:
        # Build context with Jaimini + age intelligence
        ctx = build_welcome_context_v2(chart_data, birth_date)

        # [i18n] thread user language into ctx so build_system_prompt picks the ES template
        _lang_code = (language or "en").lower()[:2]
        ctx["language"] = _lang_code

        # Build the system prompt
        system_prompt = build_system_prompt(ctx)

        # Call Claude Sonnet
        if anthropic_client is None:
            logger.error("No Anthropic client provided")
            return _fallback_response(chart_id, language=_lang_code)

        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1200,
            messages=[{"role": "user", "content": "Generate the three welcome signals now."}],
            system=system_prompt,
        )

        # Extract text from response
        raw_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw_text += block.text

        # Parse response
        parsed = parse_welcome_response(raw_text)
        if not parsed:
            logger.error(f"Failed to parse welcome signal for {chart_id}")
            return _fallback_response(chart_id, language=_lang_code)

        # Validate
        validated = validate_welcome_signals(parsed, ctx["current_age"])

        # [output-strips] strip welcome plain fields
        # Route every user-facing text field through the centralized
        # output-strip layer before returning to the /welcome endpoint.
        # Language is threaded from generate_welcome_signal_v2 → here.
        _lang = _lang_code
        for _key in ('signal_1', 'signal_2', 'signal_3'):
            _sig = validated.get(_key)
            if isinstance(_sig, dict):
                for _f in ('headline', 'body', 'watch_for'):
                    _v = _sig.get(_f)
                    if isinstance(_v, str) and _v:
                        _sig[_f] = apply_user_facing_strips(
                            _v, language=_lang, field_type='plain'
                        )

        # Add metadata
        validated["chart_id"] = chart_id
        validated["generated_at"] = datetime.now().isoformat()

        return validated

    except Exception as e:
        logger.error(f"Welcome signal generation failed for {chart_id}: {e}")
        return _fallback_response(chart_id, language=language)


def _fallback_response(chart_id: str, language: Optional[str] = "en") -> Dict[str, Any]:
    """Safe fallback if generation fails. Generic but structurally correct.

    Localized for en/es so Spanish users don't see English text if generation
    fails before Claude returns (network errors, no client, JSON parse fail).
    """
    code = (language or "en").lower()[:2]
    if code == "es":
        return {
            "signal_1": {
                "type": "mirror",
                "headline": "Tu patrón es precisión, no velocidad",
                "body": "Procesas antes de responder. Esto no es vacilación — es exactitud. Las personas que importan han aprendido a esperar tu respuesta."
            },
            "signal_2": {
                "type": "chapter",
                "headline": "La Fase de Consolidación",
                "body": "Estás en un período de afianzar lo que has construido. Los próximos 12 meses te piden fortalecer cimientos, no perseguir nuevos horizontes. Una decisión sobre tu camino actual llega pronto.",
                "timing": "December 2026"
            },
            "signal_3": {
                "type": "signal",
                "headline": "Un reconocimiento llega antes de parecer ganado",
                "body": "Una oportunidad o reconocimiento de alguien en una posición de autoridad llega en los próximos 60 días. Se sentirá prematuro. Actúa.",
                "domain": "career",
                "watch_for": "Una oferta o reconocimiento inesperado de una figura superior en los próximos 60 días."
            },
            "chart_id": chart_id,
            "generated_at": datetime.now().isoformat(),
            "_fallback": True,
        }
    # default: English
    return {
        "signal_1": {
            "type": "mirror",
            "headline": "Your pattern is precision, not speed",
            "body": "You process before you respond. This is not hesitation — it is accuracy. The people who matter have learned to wait for your answer."
        },
        "signal_2": {
            "type": "chapter",
            "headline": "The Consolidation Phase",
            "body": "You are in a period of grounding what you have built. The next 12 months ask you to strengthen foundations, not chase new horizons. A decision about your current path arrives soon.",
            "timing": "December 2026"
        },
        "signal_3": {
            "type": "signal",
            "headline": "A recognition arrives before it feels earned",
            "body": "An opportunity or acknowledgment from someone in a position of authority arrives within the next 60 days. It will feel premature. Act on it.",
            "domain": "career",
            "watch_for": "An unexpected offer or recognition from a senior figure within the next 60 days."
        },
        "chart_id": chart_id,
        "generated_at": datetime.now().isoformat(),
        "_fallback": True,
    }


# =============================================================================
# SYNC WRAPPER — For testing without async
# =============================================================================

def generate_welcome_context_preview(chart_data: Dict[str, Any], birth_date: str) -> str:
    """
    Sync function for testing: builds context + system prompt, returns the
    full prompt that would be sent to Claude. Does NOT call Claude.
    """
    ctx = build_welcome_context_v2(chart_data, birth_date)
    return build_system_prompt(ctx)


# =============================================================================
# MAIN.PY WIRING REFERENCE
# =============================================================================

"""
===========================================================================
WIRING INTO MAIN.PY — REPLACE EXISTING WELCOME ENDPOINT
===========================================================================

In main.py, find the GET /api/v1/welcome/{chart_id} endpoint.
Replace the signal generation call with:

  ┌──────────────────────────────────────────────────────────┐
  │  from antar_engine.welcome_signal_v2 import (            │
  │      generate_welcome_signal_v2                          │
  │  )                                                       │
  │                                                          │
  │  # Inside the endpoint handler:                          │
  │  # 1. Check cache first                                  │
  │  cached = await supabase.table("welcome_signals")        │
  │      .select("*")                                        │
  │      .eq("chart_id", chart_id)                           │
  │      .execute()                                          │
  │                                                          │
  │  if cached.data:                                         │
  │      return cached.data[0]["signal_data"]                │
  │                                                          │
  │  # 2. Fetch chart data                                   │
  │  chart = await supabase.table("charts")                  │
  │      .select("*")                                        │
  │      .eq("id", chart_id)                                 │
  │      .single()                                           │
  │      .execute()                                          │
  │                                                          │
  │  # 3. Generate (fire-and-forget or await)                │
  │  result = await generate_welcome_signal_v2(              │
  │      chart_data=chart.data,                              │
  │      birth_date=chart.data.get("birth_date"),            │
  │      anthropic_client=anthropic,                          │
  │  )                                                       │
  │                                                          │
  │  # 4. Cache result                                       │
  │  await supabase.table("welcome_signals").upsert({        │
  │      "chart_id": chart_id,                               │
  │      "signal_data": json.dumps(result),                  │
  │      "generated_at": result["generated_at"],             │
  │  }).execute()                                            │
  │                                                          │
  │  return result                                           │
  └──────────────────────────────────────────────────────────┘

===========================================================================
"""
