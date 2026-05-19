"""
antar_engine/welcome_signal.py
Sprint W — Welcome Signal: 3 WOW Moments

Generated immediately after chart creation.
This is the first thing a new user sees — the entire product audition.

Three signals:
  Signal 1 — The Mirror: identity/character insight (no events, no dates)
  Signal 2 — The Chapter: names the life chapter + specific future timing
  Signal 3 — The Signal: one thing to watch for in 60-90 days + domain + action

Rules:
  - Zero Sanskrit, zero jargon
  - All dates must be in the future
  - Age-appropriate: never reference themes below floor_age
  - Cached in welcome_signals table — never regenerated
  - Generated async in background after chart save
"""

import json
import logging
import os
import re
from datetime import datetime, date, timezone
from typing import Optional

from antar_engine.age_utils import (
    calculate_current_age,
    get_floor_age,
    filter_umra_activations,
    filter_future_dasha_transitions,
    format_timing_pill,
)

# [output-strips] migrate welcome_signal v1
from antar_engine.output_strips import apply_user_facing_strips

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# System prompt — the 3-signal WOW structure
# ─────────────────────────────────────────────────────────────────────────────

WELCOME_SYSTEM_PROMPT = """You are Antar — a precise, empathetic life navigation advisor.

A new user has just submitted their birth details. Generate three signals.
This is their FIRST impression of Antar. It must be unforgettable.

SIGNAL 1 — THE MIRROR
One precise character insight based on their rising sign + moon sign + nakshatra.
This is about IDENTITY — who they are, how they process the world.
Personal. Slightly uncomfortable in its accuracy. NOT an event — a truth.
2-3 sentences. No dates. No predictions. No events.

SIGNAL 2 — THE PROOF
Your context contains PROOF EVENTS — past convergence points where two independent
timing systems activated the same life area simultaneously. Use them.

For each proof event (up to 3):
- ASK the user if it happened (question format — "Between X and Y, did...?")
- Then CONNECT it to the arc — one sentence explaining WHY it happened in their life story
- Use the chapter name provided (e.g. "The break", "The reckoning")

After all proof events, add THE THREAD: connect all events to the present moment.
The user should feel that every chapter led directly to what they are doing right now.
2 sentences maximum for the thread.

If no proof events are in the context, fall back to naming their current life chapter
with a specific future timing.

SIGNAL 3 — THE PAYOFF
This is chapter 4 of the story you just told in Signal 2.
The proof events showed what happened. Signal 3 shows what it was all leading to.

One specific thing to watch for in the next 60-90 days.
Based on current planetary period + slow planet transits.
Name the domain. Name the date range. End with one action or thing to watch for.

CRITICAL: Connect this to the thread from Signal 2. Reference the arc.
NOT: "A financial door opens in April."
YES: "Everything those chapters cost you starts paying back now. Between April and June, a financial door opens through your network — act on it within the week."

2-3 sentences. The user should feel this is the destination, not random advice.

ABSOLUTE RULES:
1. This user is {{current_age}} years old. NEVER reference events or themes from before age {{floor_age}}.
2. Zero Sanskrit terms. Zero jargon. Plain English only.
3. Each signal is 2-4 sentences. No padding. No hedging. No filler.
4. Do NOT say "your chart shows" or "astrologically speaking." State facts directly.
5. Signal 2 dates are PAST events (proof). Signal 3 dates must be in the FUTURE. The proof is about what already happened — the signal is about what is coming.
6. Signal 2 proof events must use the exact periods provided in the context — do not invent dates.
7. Signal 3 domain must be one of: career / relationship / financial / health / travel / legal
8. Signal 3 watch_for must be one concrete sentence — what to watch for or do.
9. If the user's name is provided, start Signal 1 headline with their name.
10. Career signals for 55+ = authority, legacy, succession — NOT starting out.
11. Relationship signals for 60+ = depth, companionship — NOT first relationship.
12. Never reference childhood, teenage years, or early adulthood for users over 40.

Return EXACTLY this JSON and nothing else:
{
  "signal_1": {
    "type": "mirror",
    "headline": "<user's name if provided>, <insight in under 12 words>",
    "body": "2-3 sentences. Character/identity only. No events. No dates."
  },
  "signal_2": {
    "type": "proof",
    "events": [
      {
        "chapter": "The break",
        "period": "2006–2009",
        "age": "32–35",
        "question": "Between 2006 and 2009, did something you had built or depended on end — suddenly, and not on your terms?",
        "meaning": "This was not bad luck. It was a scheduled demolition — clearing ground for what comes next."
      }
    ],
    "thread": "Each of those chapters cleared the ground for what you are creating right now. The pattern is not random — and neither is this moment."
  },
  "signal_3": {
    "type": "signal",
    "headline": "<one sentence under 12 words>",
    "body": "2-3 sentences. Specific domain + date range + what to do.",
    "domain": "career",
    "watch_for": "One sentence — the specific thing to watch for or act on."
  }
}"""


WELCOME_SYSTEM_PROMPT_ES = """Eres Antar — un guía de navegación de vida preciso y empático.

Un usuario nuevo acaba de registrar sus datos de nacimiento. Genera tres señales.
Esta es su PRIMERA impresión de Antar. Debe ser inolvidable.

SEÑAL 1 — EL ESPEJO
Una observación precisa sobre su carácter, basada en el signo ascendente,
el signo lunar y el nakshatra. Esto trata de la IDENTIDAD — quién es la
persona, cómo procesa el mundo. Personal. Ligeramente incómodo por la
precisión. NO es un evento — es una verdad.
2-3 frases. Sin fechas. Sin predicciones. Sin eventos.

SEÑAL 2 — LA PRUEBA
Tu contexto contiene EVENTOS DE PRUEBA — momentos de convergencia en el pasado
donde dos sistemas independientes de temporalidad activaron la misma área de
vida al mismo tiempo. Úsalos.

Para cada evento de prueba (hasta 3):
- PREGUNTA al usuario si ocurrió (formato pregunta — "Entre X e Y, ¿...?")
- Luego CONECTA con el arco — una frase explicando POR QUÉ ocurrió en su historia
- Usa el nombre del capítulo proporcionado (ej. "La ruptura", "El ajuste")

Después de todos los eventos, añade EL HILO: conecta todos los eventos con el
momento presente. El usuario debe sentir que cada capítulo condujo directamente
a lo que está haciendo ahora mismo.  Máximo 2 frases para el hilo.

Si no hay eventos de prueba en el contexto, nombra el capítulo actual de su vida
con una fecha futura específica.

SEÑAL 3 — LA RECOMPENSA
Este es el capítulo 4 de la historia que acabas de contar en la Señal 2.
Los eventos de prueba mostraron lo que pasó. La Señal 3 muestra a qué conducía todo.

Una cosa específica que vigilar en los próximos 60-90 días.
Basada en el período planetario actual + tránsitos de planetas lentos.
Nombra el dominio. Nombra el rango de fechas. Termina con una acción o algo
que vigilar.

CRÍTICO: Conecta esto con el hilo de la Señal 2. Referencia el arco.
NO: "Una puerta financiera se abre en abril."
SÍ: "Todo lo que esos capítulos te costaron empieza a devolverse ahora. Entre
abril y junio, se abre una puerta financiera a través de tu red — actúa dentro
de la primera semana."

2-3 frases. El usuario debe sentir que este es el destino, no un consejo aleatorio.

REGLAS ABSOLUTAS:
1. Esta persona tiene {{current_age}} años. NUNCA hagas referencia a eventos o
   temas de antes de los {{floor_age}} años.
2. Cero términos en sánscrito. Cero jerga. Solo español claro.
3. Cada señal tiene 2-4 frases. Sin relleno. Sin titubeo. Sin paja.
4. NO digas "tu carta muestra" ni "astrológicamente hablando". Declara los
   hechos directamente.
5. Las fechas de la Señal 2 son eventos PASADOS (prueba). Las fechas de la
   Señal 3 deben estar en el FUTURO.
6. Los eventos de prueba de la Señal 2 deben usar los períodos exactos
   proporcionados en el contexto — no inventes fechas.
7. El dominio de la Señal 3 debe ser uno de: career / relationship / financial /
   health / travel / legal  (mantén el valor del campo `domain` en inglés para
   el enrutamiento — el resto del texto debe estar en español).
8. El `watch_for` de la Señal 3 debe ser una frase concreta — qué vigilar o hacer.
9. Si se proporciona el nombre del usuario, empieza el `headline` de la Señal 1
   con su nombre.
10. Señales de carrera para 55+ = autoridad, legado, sucesión — NO "empezando".
11. Señales de relación para 60+ = profundidad, compañía — NO "primera relación".
12. Nunca referencies infancia, adolescencia o juventud temprana para usuarios
    mayores de 40.

Devuelve EXACTAMENTE este JSON y nada más.  Todo el texto narrativo
(`headline`, `body`, `thread`, `chapter`, `question`, `meaning`, `watch_for`)
debe estar en español.  Los valores del campo `domain` y `type` permanecen en
inglés (son identificadores internos).

{
  "signal_1": {
    "type": "mirror",
    "headline": "<nombre del usuario si se proporciona>, <observación en menos de 12 palabras>",
    "body": "2-3 frases. Solo carácter/identidad. Sin eventos. Sin fechas."
  },
  "signal_2": {
    "type": "proof",
    "events": [
      {
        "chapter": "La ruptura",
        "period": "2006–2009",
        "age": "32–35",
        "question": "Entre 2006 y 2009, ¿algo que habías construido o de lo que dependías terminó — de repente y no en tus términos?",
        "meaning": "Esto no fue mala suerte. Fue una demolición programada — despejar el terreno para lo que viene."
      }
    ],
    "thread": "Cada uno de esos capítulos despejó el terreno para lo que estás creando ahora mismo. El patrón no es aleatorio — y este momento tampoco."
  },
  "signal_3": {
    "type": "signal",
    "headline": "<una frase de menos de 12 palabras>",
    "body": "2-3 frases. Dominio específico + rango de fechas + qué hacer.",
    "domain": "career",
    "watch_for": "Una frase — lo concreto que vigilar o hacer."
  }
}"""


def _select_system_prompt(language: Optional[str]) -> str:
    """Return the system prompt for the user's language.  English fallback."""
    code = (language or "en").lower()[:2]
    if code == "es":
        return WELCOME_SYSTEM_PROMPT_ES
    return WELCOME_SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point — same signature as before so main.py needs zero changes
# ─────────────────────────────────────────────────────────────────────────────

async def generate_welcome_signal(
    chart_id:      str,
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    supabase,
    claude_client,
    birth_date:    Optional[str] = None,
    language:      Optional[str] = "en",
) -> dict:
    """
    Generate and save the 3-signal welcome for a new chart.
    Called async after chart creation — non-blocking.
    Returns the welcome signal dict with signal_1, signal_2, signal_3.
    """
    # ── Check if already generated ────────────────────────────────
    try:
        existing = supabase.table("welcome_signals") \
            .select("*") \
            .eq("chart_id", chart_id) \
            .execute()
        if existing.data:
            row = existing.data[0]
            # If it has signal_1_type, it's the new 3-signal format — return as structured
            if row.get("signal_1_type"):
                return _row_to_response(row)
            # Old format — delete and regenerate
            try:
                supabase.table("welcome_signals") \
                    .delete() \
                    .eq("chart_id", chart_id) \
                    .execute()
                logger.info(f"[welcome] Deleted old-format signal for {chart_id[:8]}, regenerating")
            except Exception:
                pass
    except Exception:
        pass

    # ── Build context ─────────────────────────────────────────────
    try:
        context = _build_welcome_context(
            chart_data, dashas, first_name, lagna,
            moon_sign, current_dasha, age, country_code,
            birth_date=birth_date,
            chart_id=chart_id,
            supabase=supabase,
            language=language,
        )
    except Exception as _ctx_err:
        logger.error(f"[welcome] Context build failed: {_ctx_err}")
        context = None

    # ── Call Claude ───────────────────────────────────────────────
    result = await _call_claude(context, claude_client, language=language)
    if result is None:
        result = _fallback_signal(language=language)

    # ── Inject first_name into Signal 1 headline if missing ──────
    if first_name and result:
        s1 = result.get("signal_1", {})
        headline = s1.get("headline", "")
        if headline and not headline.lower().startswith(first_name.lower()):
            s1["headline"] = f"{first_name}, {headline[0].lower()}{headline[1:]}"
            result["signal_1"] = s1

    # ── Save to DB (flattened for Supabase) ──────────────────────
    if result is None:
        result = _fallback_signal(language=language)
    try:
        s1 = result.get("signal_1", {})
        s2 = result.get("signal_2", {})
        s3 = result.get("signal_3", {})

        row = {
            "chart_id":          chart_id,
            # Signal 1 — Mirror
            "signal_1_type":     s1.get("type", "mirror"),
            "signal_1_headline": s1.get("headline", ""),
            "signal_1_body":     s1.get("body", ""),
            # Signal 2 — Proof
            "signal_2_type":     s2.get("type", "proof"),
            "signal_2_headline": s2.get("thread", ""),
            "signal_2_body":     json.dumps(s2.get("events", [])),
            "signal_2_timing":   "",
            # Signal 3 — Signal
            "signal_3_type":     s3.get("type", "signal"),
            "signal_3_headline": s3.get("headline", ""),
            "signal_3_body":     s3.get("body", ""),
            "signal_3_domain":   s3.get("domain", ""),
            "signal_3_watch_for": s3.get("watch_for", ""),
            # Legacy fields (for backward compat if Lovable still reads old shape)
            "headline":          s1.get("headline", ""),
            "summary":           s2.get("body", ""),
            "action":            s3.get("watch_for", ""),
            "signal_type":       s3.get("domain", "opportunity"),
            "chapter_name":      s2.get("headline", ""),
            "created_at":        datetime.now(timezone.utc).isoformat(),
        }

        # [loc-1] Seed content_by_language so the per-language cache works for
        # charts created via the background pre-warm path too. Without this the
        # first /welcome GET would always MISS and regenerate synchronously.
        _v1_lang = (language or "en").split("-")[0].lower()
        if _v1_lang not in ("en", "es", "pt"):
            _v1_lang = "en"
        row["content_by_language"] = {
            _v1_lang: {
                _k: _v for _k, _v in row.items()
                if _k not in ("chart_id", "created_at", "content_by_language")
            }
        }
        supabase.table("welcome_signals").insert(row).execute()
        logger.info(f"[welcome] 3-signal saved for chart {chart_id[:8]} lang={_v1_lang}")
        return _row_to_response(row)

    except Exception as e:
        logger.error(f"[welcome] DB save failed: {e}")
        # Return structured response even if DB save fails
        return result


def _row_to_response(row: dict) -> dict:
    """Convert a flattened DB row back to the structured 3-signal response."""
    return {
        "chart_id": row.get("chart_id", ""),
        "signal_1": {
            "type":     row.get("signal_1_type", "mirror"),
            "headline": row.get("signal_1_headline", ""),
            "body":     row.get("signal_1_body", ""),
        },
        "signal_2": _reconstruct_signal_2(row),
        "signal_3": {
            "type":     row.get("signal_3_type", "signal"),
            "headline": row.get("signal_3_headline", ""),
            "body":     row.get("signal_3_body", ""),
            "domain":   row.get("signal_3_domain", ""),
            "watch_for": row.get("signal_3_watch_for", ""),
        },
        # Legacy fields for backward compat
        "headline":     row.get("headline", ""),
        "summary":      row.get("summary", ""),
        "action":       row.get("action", ""),
        "signal_type":  row.get("signal_type", "opportunity"),
        "chapter_name": row.get("chapter_name", ""),
    }



# ─────────────────────────────────────────────────────────────────────────────
# Convergence proof engine — finds past events where 2+ dasha systems agree
# ─────────────────────────────────────────────────────────────────────────────

# House themes for plain English output
HOUSE_THEMES = {
    1: ("identity", "Self, health, personality — who you are at your core"),
    2: ("finances", "Wealth, family, speech — what you possess and value"),
    3: ("courage", "Courage, siblings, communication — how you assert yourself"),
    4: ("home", "Home, mother, property — your foundation and inner peace"),
    5: ("creation", "Children, creativity, intelligence — what you bring into the world"),
    6: ("conflict", "Enemies, debts, health challenges — what tests you"),
    7: ("partnership", "Marriage, partnerships, contracts — your closest alliances"),
    8: ("transformation", "Transformation, crisis, hidden matters — what breaks and rebuilds you"),
    9: ("fortune", "Fortune, father, higher learning — your dharma and beliefs"),
    10: ("career", "Career, authority, public life — how the world sees you"),
    11: ("gains", "Gains, networks, aspirations — what you receive and who helps you"),
    12: ("surrender", "Spirituality, foreign lands, loss — what you release"),
}

# Chapter names for each house convergence
CHAPTER_NAMES = {
    1: "The identity shift",
    2: "The financial reckoning",
    3: "The assertion",
    4: "The foundation crack",
    5: "The creative rupture",
    6: "The fight",
    7: "The reckoning",
    8: "The break",
    9: "The belief shift",
    10: "The authority test",
    11: "The network shift",
    12: "The surrender",
}

# Question templates for each house (B+C format)
HOUSE_QUESTIONS = {
    1: "Did something force you to fundamentally redefine who you are — a health crisis, an identity shift, or a moment where the version of yourself you had been living as stopped working?",
    2: "Did your financial foundation shift — a major gain, a loss, or a change in how your family or income was structured?",
    3: "Did you have to assert yourself in a way you had been avoiding — a confrontation, a bold move, or a break from a sibling or close peer?",
    4: "Did something shift in your home, your relationship with your mother, or a property matter — a move, a loss, or a decision about where you truly belong?",
    5: "Did something change in your creative life, your relationship with children, or a speculative venture — something you brought into the world that demanded a new version of you?",
    6: "Did you face a legal, financial, or health battle that exhausted you — but left you knowing exactly what you are willing to fight for?",
    7: "Did a partnership — marriage, business, or deep alliance — reach a point where you had to decide who you actually are versus who you had been performing as?",
    8: "Did something you had built or depended on end — suddenly, and not on your terms?",
    9: "Did your beliefs, your relationship with your father, or your sense of purpose go through a fundamental shift — where what you thought was true stopped being true?",
    10: "Did your career or public standing face a test — a demotion, a role change, or a moment where your authority was challenged?",
    11: "Did your network, your income sources, or a long-held aspiration shift dramatically — old alliances ending, new ones forming?",
    12: "Did you experience a period of isolation, a foreign connection, or a loss that forced you to let go of something you thought you needed?",
}

# Meaning connectors — why it happened in the arc
HOUSE_MEANING = {
    1: "This was not a breakdown — it was an identity upgrade. Who you were before could not carry what comes next.",
    2: "This was the financial ground being cleared. What you lost or gained here set the terms for everything that followed.",
    3: "This was you finding your voice. The courage that emerged here is what you now use daily.",
    4: "This was your foundation being tested. What survived is what you actually stand on now.",
    5: "This was creative destruction. What you released made room for what you are building now.",
    6: "This was not punishment — it was purification. The fight stripped away everything except what actually matters to you.",
    7: "The relationship was the vehicle, but the real event was identity. What you chose here shaped everything after.",
    8: "This was not bad luck. It was a scheduled demolition — clearing ground for what comes next.",
    9: "This was your worldview being rebuilt. The beliefs you carry now were forged in this window.",
    10: "This was your authority being tested so it could be earned, not inherited. What you proved here is what you stand on now.",
    11: "This was your network being pruned. The connections that survived are the ones that matter.",
    12: "This was a necessary surrender. What you released created the space you now occupy.",
}



def _reconstruct_signal_2(row: dict) -> dict:
    """Reconstruct Signal 2 from DB row — handles both proof and legacy chapter format."""
    s2_type = row.get("signal_2_type", "chapter")
    if s2_type == "proof":
        events = []
        try:
            events = json.loads(row.get("signal_2_body", "[]"))
        except (json.JSONDecodeError, TypeError):
            events = []
        return {
            "type": "proof",
            "events": events,
            "thread": row.get("signal_2_headline", ""),
        }
    else:
        return {
            "type": "chapter",
            "headline": row.get("signal_2_headline", ""),
            "body": row.get("signal_2_body", ""),
            "timing": row.get("signal_2_timing", ""),
        }


def _build_convergence_proof(
    chart_id: str,
    chart_data: dict,
    birth_date: str,
    supabase,
    current_age: int = None,
    birth_country: str = "",
    current_country: str = "",
) -> str:
    """
    Queries dasha_periods for all past Vimsottari + Jaimini periods.
    Finds convergence points where both systems activate the same house.
    Returns a context block for Claude with 3 past-event proof cards.
    """
    from datetime import date

    if not birth_date or not chart_id:
        return ""

    today = date.today()
    house_lords = chart_data.get("house_lords", {})

    # ── Build planet-to-houses mapping ────────────────────────────
    # Which houses does each planet rule?
    planet_to_houses = {}
    for house_num, lord_info in house_lords.items():
        lord_name = lord_info.get("lord", "") if isinstance(lord_info, dict) else str(lord_info)
        if lord_name:
            if lord_name not in planet_to_houses:
                planet_to_houses[lord_name] = []
            try:
                planet_to_houses[lord_name].append(int(house_num))
            except (ValueError, TypeError):
                pass

    # ── Build sign-to-house mapping (for Jaimini) ────────────────
    SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna_info = chart_data.get("lagna", {})
    lagna_sign = lagna_info.get("sign", "Aries") if isinstance(lagna_info, dict) else "Aries"
    lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0
    sign_to_house = {}
    for i, sign in enumerate(SIGNS):
        house = ((SIGNS.index(sign) - lagna_idx) % 12) + 1
        sign_to_house[sign] = house

    # ── Query all dasha periods ──────────────────────────────────
    try:
        vim_res = supabase.table("dasha_periods")             .select("planet_or_sign, start_date, end_date")             .eq("chart_id", chart_id)             .eq("system", "vimsottari")             .eq("level", 1)             .order("start_date")             .execute()
        vim_periods = vim_res.data if vim_res.data else []

        jai_res = supabase.table("dasha_periods")             .select("planet_or_sign, start_date, end_date")             .eq("chart_id", chart_id)             .eq("system", "jaimini")             .eq("level", 1)             .order("start_date")             .execute()
        jai_periods = jai_res.data if jai_res.data else []
    except Exception as e:
        print(f"[welcome] Convergence query failed: {e}")
        return ""

    if not vim_periods or not jai_periods:
        return ""

    # ── Find convergences — overlapping periods activating same house ─
    bd = date.fromisoformat(birth_date[:10])
    convergences = []

    for vim in vim_periods:
        vim_start = date.fromisoformat(str(vim["start_date"])[:10])
        vim_end = date.fromisoformat(str(vim["end_date"])[:10])
        vim_planet = vim["planet_or_sign"]

        # Skip current and future periods — we want PAST events only
        if vim_end > today:
            # Include partially past periods (started in past, ends in future)
            # but only if it started at least 2 years ago
            if vim_start > date(today.year - 2, today.month, today.day):
                continue

        vim_houses = planet_to_houses.get(vim_planet, [])
        if not vim_houses:
            continue

        for jai in jai_periods:
            jai_start = date.fromisoformat(str(jai["start_date"])[:10])
            jai_end = date.fromisoformat(str(jai["end_date"])[:10])
            jai_sign = jai["planet_or_sign"]
            jai_house = sign_to_house.get(jai_sign)

            if not jai_house:
                continue

            # Check overlap
            overlap_start = max(vim_start, jai_start)
            overlap_end = min(vim_end, jai_end)

            if overlap_start >= overlap_end:
                continue

            # Skip overlaps entirely in the future
            if overlap_start > today:
                continue

            # Check if the Jaimini house matches any Vimsottari house
            if jai_house in vim_houses:
                # Calculate age during this period
                age_start = overlap_start.year - bd.year
                age_end = overlap_end.year - bd.year

                # Age-adaptive floor:
                # 40+ users: skip events before age 25 (focus on peak life)
                # 25-40 users: skip events before age 18 (include career/migration)
                # 18-24 users: skip events before age 16
                if current_age and current_age >= 40:
                    _min_event_age = 25
                elif current_age and current_age >= 25:
                    _min_event_age = 18
                else:
                    _min_event_age = 16
                if age_end < _min_event_age:
                    continue

                overlap_years = (overlap_end - overlap_start).days / 365.25

                convergences.append({
                    "house": jai_house,
                    "vim_planet": vim_planet,
                    "jai_sign": jai_sign,
                    "start_year": max(overlap_start.year, bd.year + 16),
                    "end_year": min(overlap_end.year, today.year),
                    "age_start": max(age_start, 16),
                    "age_end": min(age_end, today.year - bd.year),
                    "overlap_years": overlap_years,
                    "theme": HOUSE_THEMES.get(jai_house, ("unknown", ""))[0],
                    "chapter": CHAPTER_NAMES.get(jai_house, "A turning point"),
                    "question": HOUSE_QUESTIONS.get(jai_house, "Did something significant happen in this period?"),
                    "meaning": HOUSE_MEANING.get(jai_house, "This was part of the pattern leading to now."),
                })

    # ── Migration detection ─────────────────────────────────────
    # If birth_country != current_country, find the 12th/9th/Rahu period
    # that most likely corresponds to when they left home
    _is_migrant = (
        birth_country and current_country
        and birth_country.strip().upper() != current_country.strip().upper()
    )
    if _is_migrant:
        # Look for 12th house, 9th house, or Rahu-linked periods in age 16-30
        migration_houses = {12, 9}
        migration_candidates = []
        for c in convergences:
            if c["house"] in migration_houses and c["age_start"] >= 16 and c["age_start"] <= 35:
                migration_candidates.append(c)
        
        # Also check for Rahu periods (even without house convergence)
        for vim in vim_periods:
            vim_planet = vim["planet_or_sign"]
            if vim_planet == "Rahu":
                vim_start = date.fromisoformat(str(vim["start_date"])[:10])
                vim_end = date.fromisoformat(str(vim["end_date"])[:10])
                rahu_age_start = vim_start.year - bd.year
                rahu_age_end = vim_end.year - bd.year
                if rahu_age_start <= 35 and rahu_age_end >= 16 and vim_end <= today:
                    # Check if already in convergences
                    already_found = any(
                        c["vim_planet"] == "Rahu" and abs(c["start_year"] - vim_start.year) < 3
                        for c in convergences
                    )
                    if not already_found:
                        _mig_start = max(vim_start.year, bd.year + 16)
                        _mig_end = min(vim_end.year, today.year)
                        _mig_age_s = max(rahu_age_start, 16)
                        _mig_age_e = min(rahu_age_end, today.year - bd.year)
                        migration_candidates.append({
                            "house": 12,
                            "vim_planet": "Rahu",
                            "jai_sign": "migration",
                            "start_year": _mig_start,
                            "end_year": _mig_end,
                            "age_start": _mig_age_s,
                            "age_end": _mig_age_e,
                            "overlap_years": (_mig_end - _mig_start),
                            "theme": "migration",
                            "chapter": "The crossing",
                            "question": f"Around {_mig_start}–{_mig_end}, did you leave your home country — a move that felt like starting from zero in a completely new world?",
                            "meaning": "This was not exile. It was the chart redirecting your entire trajectory — everything you have built since was only possible because you left.",
                        })
        
        if migration_candidates:
            # Add best migration candidate if not already in convergences
            migration_candidates.sort(key=lambda c: c["start_year"])
            best_mig = migration_candidates[0]
            already_has = any(
                c["house"] == best_mig["house"]
                and abs(c["start_year"] - best_mig["start_year"]) < 3
                for c in convergences
            )
            if not already_has:
                convergences.append(best_mig)

    if not convergences:
        return ""

    # ── Sort by recency and significance, take top 3 ─────────────
    # Prefer: recent, longer overlap, transformation houses (7,8,10,12 for migration)
    priority_houses = {8: 3, 7: 2, 10: 2, 12: 2, 6: 1, 1: 1}
    convergences.sort(
        key=lambda c: (
            -priority_houses.get(c["house"], 0),  # priority houses first
            -c["overlap_years"],                    # longer overlap = more significant
            -c["start_year"],                       # more recent first
        )
    )

    # Deduplicate by house (don't show two events for the same house)
    seen_houses = set()
    unique = []
    for c in convergences:
        if c["house"] not in seen_houses:
            seen_houses.add(c["house"])
            unique.append(c)
    
    top_3 = unique[:3]
    # Sort chronologically for presentation
    top_3.sort(key=lambda c: c["start_year"])

    # ── Build context block ──────────────────────────────────────
    lines = ["── PAST EVENT PROOF (for Signal 2 — The Proof) ──"]
    lines.append("These are convergence points where TWO independent dasha systems")
    lines.append("activated the SAME house at the SAME time. Use these as proof events.")
    lines.append("For each event: ASK the user if it happened (question format),")
    lines.append("then CONNECT it to the arc — explain WHY it happened in their life story.")
    lines.append("The final event should connect all threads to the PRESENT moment.")
    lines.append("")

    for i, c in enumerate(top_3):
        event_num = i + 1
        lines.append(f"PROOF EVENT {event_num}:")
        lines.append(f"  Period: {c['start_year']}–{c['end_year']} (age {c['age_start']}–{c['age_end']})")
        lines.append(f"  Chapter name: {c['chapter']}")
        lines.append(f"  House: {c['house']} ({HOUSE_THEMES[c['house']][1]})")
        lines.append(f"  Vimsottari: {c['vim_planet']} MD (rules house {c['house']})")
        lines.append(f"  Jaimini: {c['jai_sign']} (= house {c['house']} from lagna)")
        lines.append(f"  Convergence: BOTH systems activated house {c['house']} simultaneously")
        lines.append(f"  Question to ask: {c['question']}")
        lines.append(f"  Why it happened: {c['meaning']}")
        lines.append("")

    # Add age-specific strategy note
    if current_age and current_age < 25:
        lines.append("AGE NOTE: This user is under 25. If proof events are thin or absent,")
        lines.append("Signal 2 should INSTEAD name what they are struggling with RIGHT NOW")
        lines.append("with uncomfortable specificity — the tension between family expectations")
        lines.append("and personal desire, the career decision they are avoiding, the relationship")
        lines.append("question they already know the answer to. Make it feel private and precise.")
        lines.append("Format: still use the proof JSON structure but with 1 event that describes")
        lines.append("the CURRENT tension, not a past event. Thread connects to Signal 3.")
        lines.append("")
    
    lines.append("FINAL THREAD (after the proof events):")
    lines.append("Connect all events to the present. The user should feel that")
    lines.append("every chapter — the break, the reckoning, the fight — led directly")
    lines.append("to what they are doing right now. The present is not accidental.")
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Context builder — temporal grounding + chart facts
# ─────────────────────────────────────────────────────────────────────────────

def _build_welcome_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    birth_date:    Optional[str] = None,
    chart_id:      Optional[str] = None,
    supabase=None,
    language:      Optional[str] = "en",
) -> str:
    # ── Age intelligence (Sprint W) ───────────────────────────────
    if birth_date:
        current_age = calculate_current_age(birth_date[:10])
    elif age:
        current_age = age
    else:
        current_age = None

    floor_age = get_floor_age(current_age) if current_age else None

    # ── Umra — filtered to upcoming only ─────────────────────────
    umra_block = ""
    if current_age:
        umra_items = filter_umra_activations(current_age, max_upcoming=2)
        if umra_items:
            umra_lines = []
            for u in umra_items:
                years_away = u['activation_age'] - current_age
                if years_away <= 0:
                    distance = "currently active"
                elif years_away == 1:
                    distance = "activates next year"
                else:
                    distance = f"activates in {years_away} years"
                umra_lines.append(
                    f"  House {u['house']} (age {u['activation_age']}, {distance}): {u['theme']}. "
                    f"Tell the user what this house unlocks and what to start building toward now."
                )
            umra_block = "Upcoming age activations:\n" + "\n".join(umra_lines)

    # ── Convergence proof (past events) ────────────────────────
    proof_block = ""
    if chart_id and supabase and birth_date and current_age and current_age >= 18:
        try:
            proof_block = _build_convergence_proof(
                chart_id, chart_data, birth_date, supabase,
                current_age=current_age,
                birth_country=country_code or "",
                current_country=country_code or "",
            )
        except Exception as e:
            print(f"[welcome] Convergence proof failed (non-fatal): {e}")
            proof_block = ""

    # ── Dasha — future transitions only ──────────────────────────
    dasha_text = current_dasha or ""
    future_transition = ""
    if not dasha_text and dashas:
        vim = dashas.get("vimsottari", [])
        if vim:
            first = vim[0]
            dasha_text = first.get("lord_or_sign") or first.get("planet_or_sign", "")

    raw_ts = []
    for d in dashas.get("vimsottari", []) if dashas else []:
        if d.get("end_date"):
            raw_ts.append({
                "planet": d.get("lord_or_sign") or d.get("planet_or_sign", ""),
                "end_date": d["end_date"],
            })
    future_ts = filter_future_dasha_transitions(raw_ts)
    if future_ts:
        future_transition = f"Current period ends: {format_timing_pill(future_ts[0]['end_date'])} ({future_ts[0]['end_date']})"

    # ── Chart facts ──────────────────────────────────────────────
    planets    = chart_data.get("planets", {})
    moon_nak   = planets.get("Moon", {}).get("nakshatra", "")
    sun_sign   = planets.get("Sun", {}).get("sign", "")
    mars_sign  = planets.get("Mars", {}).get("sign", "")
    jupiter_sign = planets.get("Jupiter", {}).get("sign", "")
    saturn_sign  = planets.get("Saturn", {}).get("sign", "")
    yogas      = chart_data.get("yogas", [])
    top_yoga   = yogas[0].get("name", "") if yogas else ""
    house_lords = chart_data.get("house_lords", {})

    # ── Assemble context — temporal grounding first ──────────────
    lines = []

    # Temporal grounding — must be the first thing Claude sees
    if current_age and floor_age:
        lines.append(f"TEMPORAL GROUNDING — READ THIS FIRST:")
        if birth_date:
            _bday_month = datetime.strptime(birth_date[:10], "%Y-%m-%d").strftime("%B")
            _turning = current_age + 1
            lines.append(f"This user is {current_age} years old (turning {_turning} in {_bday_month}).")
        else:
            lines.append(f"This user is {current_age} years old.")
        lines.append(f"Temporal floor: NEVER reference themes or events from before age {floor_age}.")
        lines.append(f"Today: {datetime.now().strftime('%B %d, %Y')}")
        lines.append("")

    # Identity facts for Signal 1 (Mirror)
    lines.append("── IDENTITY (for Signal 1 — Mirror) ──")
    if first_name:
        lines.append(f"User's name: {first_name}")
    lines.append(f"Rising sign (Lagna): {lagna or 'unknown'}")
    lines.append(f"Moon sign: {moon_sign or 'unknown'}")
    if moon_nak:
        lines.append(f"Moon nakshatra: {moon_nak}")
    lines.append(f"Sun sign: {sun_sign}")
    if top_yoga:
        lines.append(f"Strongest yoga: {top_yoga}")
    lines.append("")

    # Timing facts for Signal 2 (Chapter)
    lines.append("── TIMING (for Signal 2 — Chapter) ──")
    lines.append(f"Current planetary period: {dasha_text}")
    if future_transition:
        lines.append(future_transition)
    if house_lords:
        # Show what houses the current dasha lord rules
        dasha_lord = dasha_text.split("-")[0].strip() if dasha_text else ""
        ruled_houses = [
            h for h, lord in house_lords.items()
            if str(lord).strip().lower() == dasha_lord.lower()
        ]
        if ruled_houses:
            lines.append(f"{dasha_lord} rules houses: {', '.join(str(h) for h in ruled_houses)}")
    if umra_block:
        lines.append(umra_block)
    lines.append("")

    # Transit facts for Signal 3 (Signal)
    lines.append("── TRANSITS (for Signal 3 — Signal) ──")
    if jupiter_sign:
        lines.append(f"Jupiter currently in: {jupiter_sign}")
    if saturn_sign:
        lines.append(f"Saturn currently in: {saturn_sign}")
    if mars_sign:
        lines.append(f"Mars currently in: {mars_sign}")
    if country_code:
        lines.append(f"Country: {country_code}")
    lines.append("")

    # Proof block (past events convergence)
    if proof_block:
        lines.append(proof_block)
        lines.append("")

    # Final instruction
    age_note = f"someone who is currently {current_age} years old" if current_age else "an adult"
    lines.append(
        f"Generate three WOW signals for {age_note}. "
        f"Signal 1 must be about identity/character ONLY — no events. "
        f"Signal 2 must use the PROOF EVENTS from context — ask if each happened, then connect to the arc. "
        f"Signal 3 must name a domain and a 60-90 day watch window. "
        f"All content must be age-appropriate. All dates must be in the future."
    )

    # [i18n] When the user's language is Spanish, pin the output language here.
    # The system prompt is already localized, but this reinforces it inside the
    # user-turn context so nothing English slips through the JSON.
    _lang_code = (language or "en").lower()[:2]
    if _lang_code == "es":
        lines.append("")
        lines.append("IMPORTANTE: Responde en ESPAÑOL. Todo el contenido narrativo "
                     "(headline, body, thread, chapter, question, meaning, watch_for) "
                     "debe estar en español natural — no traducción literal. "
                     "Mantén los valores de `domain` y `type` en inglés (son IDs internos).")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Claude call — parse 3-signal JSON
# ─────────────────────────────────────────────────────────────────────────────

async def _call_claude(context: str, claude_client, language: Optional[str] = "en") -> dict:
    """Call Claude Sonnet and parse the 3-signal welcome JSON."""
    try:
        # [i18n] pick system prompt based on user language (en/es)
        _system_prompt = _select_system_prompt(language)
        response = await claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            system=_system_prompt,
            messages=[{"role": "user", "content": context}],
        )
        text = response.content[0].text.strip()

        # Strip markdown fences
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        result = json.loads(text.strip())

        # Validate structure — must have all 3 signals
        if "signal_1" not in result or "signal_2" not in result or "signal_3" not in result:
            logger.warning("[welcome] Claude returned incomplete 3-signal structure, using fallback")
            return _fallback_signal(language=language)

        # Validate Signal 2 timing is future
        timing = result.get("signal_2", {}).get("timing", "")
        if timing:
            try:
                timing_date = datetime.strptime(timing, "%B %Y")
                if timing_date.replace(day=1) < datetime.now().replace(day=1):
                    logger.warning(f"[welcome] Signal 2 timing is past ({timing}), will regenerate")
                    # Don't fail — let it through, the prompt should prevent this
            except ValueError:
                pass  # Non-standard format, let it through

        # Validate Signal 3 domain
        valid_domains = {"career", "relationship", "financial", "health", "travel", "legal"}
        s3_domain = result.get("signal_3", {}).get("domain", "")
        if s3_domain and s3_domain.lower() not in valid_domains:
            result["signal_3"]["domain"] = "career"  # Safe default

        # [output-strips] strip welcome v1 plain fields
        # Route every user-facing narrative field through the centralized
        # output-strip layer.  Threaded from generate_welcome_signal → here.
        _lang = (language or "en").lower()[:2]

        # signal_1 + signal_3: headline/body/watch_for
        for _key in ('signal_1', 'signal_3'):
            _sig = result.get(_key)
            if isinstance(_sig, dict):
                for _f in ('headline', 'body', 'watch_for'):
                    _v = _sig.get(_f)
                    if isinstance(_v, str) and _v:
                        _sig[_f] = apply_user_facing_strips(
                            _v, language=_lang, field_type='plain'
                        )

        # signal_2: thread + each events[].{chapter, question, meaning}
        # (events[].period and events[].age are date strings — skip)
        _s2 = result.get('signal_2')
        if isinstance(_s2, dict):
            _thread = _s2.get('thread')
            if isinstance(_thread, str) and _thread:
                _s2['thread'] = apply_user_facing_strips(
                    _thread, language=_lang, field_type='plain'
                )
            _events = _s2.get('events')
            if isinstance(_events, list):
                for _ev in _events:
                    if isinstance(_ev, dict):
                        for _f in ('chapter', 'question', 'meaning'):
                            _v = _ev.get(_f)
                            if isinstance(_v, str) and _v:
                                _ev[_f] = apply_user_facing_strips(
                                    _v, language=_lang, field_type='plain'
                                )

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[welcome] JSON parse failed: {e}")
        return _fallback_signal(language=language)
    except Exception as e:
        import traceback
        print(f"[welcome] Claude call FAILED: {type(e).__name__}: {e}")
        print(f"[welcome] Traceback: {traceback.format_exc()}")
        logger.error(f"[welcome] Claude call failed: {e}")
        return _fallback_signal(language=language)


def _fallback_signal(language: Optional[str] = "en") -> dict:
    """Fallback if Claude fails — returns valid 3-signal structure.

    Localized for en/es so Spanish users don't see English text if Claude
    fails before generating output.
    """
    code = (language or "en").lower()[:2]
    if code == "es":
        return {
            "signal_1": {
                "type": "mirror",
                "headline": "Tu carta está calculada — esto es lo que muestra ahora mismo.",
                "body": "Tu carta natal revela un patrón específico en cómo procesas decisiones y relaciones. Hazle a Antar cualquier pregunta para explorar lo que tu carta dice sobre tu vida en este momento.",
            },
            "signal_2": {
                "type": "proof",
                "events": [],
                "thread": "Tu carta tiene un patrón claro a lo largo de las últimas dos décadas. Hazle una pregunta a Antar para ver cómo se conecta con lo que viene.",
            },
            "signal_3": {
                "type": "signal",
                "headline": "Haz tu primera pregunta para activar tu señal.",
                "body": "Tu carta tiene señales específicas para los próximos 90 días. Pregúntale a Antar sobre carrera, relaciones, finanzas o cualquier área de tu vida para ver qué está llegando y cuándo.",
                "domain": "career",
                "watch_for": "Haz tu primera pregunta para obtener una señal específica con tiempos.",
            },
        }
    # default: English
    return {
        "signal_1": {
            "type": "mirror",
            "headline": "Your chart is calculated — here is what stands out.",
            "body": "Your birth chart reveals a specific pattern in how you process decisions and relationships. Ask Antar any question to explore what your chart says about your life right now.",
        },
        "signal_2": {
            "type": "proof",
            "events": [],
            "thread": "Your chart has a clear pattern across the last two decades. Ask Antar a question to see how it connects to what is coming next.",
        },
        "signal_3": {
            "type": "signal",
            "headline": "Ask your first question to activate your signal.",
            "body": "Your chart has specific signals for the next 90 days. Ask Antar about career, relationships, finances, or any life area to see what is arriving and when.",
            "domain": "career",
            "watch_for": "Ask your first question to get a specific signal with timing.",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sync reader — for GET /api/v1/welcome/{chart_id}
# ─────────────────────────────────────────────────────────────────────────────

def _safe_jsonb_welcome(v):
    """Parse a Supabase JSONB column that may arrive as a JSON string.

    welcome_signals.content_by_language is JSONB, but the client occasionally
    hands it back as a raw JSON string — always parse defensively.
    """
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def get_welcome_signal(chart_id: str, supabase, language: str = "en") -> Optional[dict]:
    """Read the cached welcome signal for a specific language.

    [loc-1] Looks up content_by_language[language]. Returns None (cache MISS)
    when that language has not been generated yet, so the endpoint regenerates
    fresh in the requested language. The legacy top-level flat columns are NOT
    used for the language match — they only ever held one language of content.
    """
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"
    try:
        result = supabase.table("welcome_signals") \
            .select("*") \
            .eq("chart_id", chart_id) \
            .execute()
        if not result.data:
            return None
        row = result.data[0]
        cbl = _safe_jsonb_welcome(row.get("content_by_language"))
        lang_content = cbl.get(language) if isinstance(cbl, dict) else None
        if isinstance(lang_content, dict) and lang_content.get("signal_1_type"):
            # Cache HIT for this specific language
            return _row_to_response({**lang_content, "chart_id": chart_id})
        # Cache MISS for this language — endpoint will regenerate
        return None
    except Exception as e:
        logger.warning(f"[welcome] Read failed: {e}")
        return None
