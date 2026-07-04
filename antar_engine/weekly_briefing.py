"""
antar_engine/weekly_briefing.py
Sprint E — Weekly Briefing

Every Monday, Antar proactively delivers a 5-domain briefing for the week ahead.
No user action required. Pulled from /api/v1/weekly-briefing/{chart_id}.

The briefing covers:
  Career / Wealth / Relationships / Health / Spirit
  One overall focus recommendation for the week
  Key timing window (best day this week for important actions)

Uses: Masik Phal overlay + current transits + dasha + DKP context
Cached per chart per week — regenerated on Monday.
"""

import logging
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

# [output-strips] migrate weekly_briefing
from antar_engine.output_strips import apply_user_facing_strips

logger = logging.getLogger(__name__)

BRIEFING_TABLE = "weekly_briefings"

WEEKLY_SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation advisor.

Generate a weekly briefing for the upcoming week. This is proactive coaching — 
the user did not ask a question. Antar is watching their chart and flagging what matters.

RULES:
- ALWAYS start weekly_focus with the user's first name if provided e.g. "Ramandeep, this week..."
- Each domain signal: 2 sentences maximum. Plain English. Zero jargon.
- The weekly focus: one paragraph, the single most important theme this week
- Best day: name a specific day of the week for important actions
- ALWAYS address the user by first name in weekly_focus e.g. 'Ramandeep, this week...'
- Be specific to the chart data provided — not generic weekly horoscope language
- Warm but precise. Like a trusted advisor's Monday morning message.

Return ONLY this JSON:
{
  "week_of": "March 31, 2026",
  "weekly_focus": "One paragraph — the dominant theme for this week and what it means practically.",
  "best_day": "Wednesday — [reason in 5 words]",
  "domains": {
    "career":       "2 sentences. What career/work energy is active this week.",
    "wealth":       "2 sentences. What financial energy is active this week.",
    "relationships":"2 sentences. What relationship energy is active this week.",
    "health":       "2 sentences. What health/body energy is active this week.",
    "spirit":       "2 sentences. What spiritual/inner energy is active this week."
  },
  "one_action": "The single most important action to take before Sunday. Verb-first."
}"""


WEEKLY_SYSTEM_PROMPT_ES = """Eres Antar — un guía de navegación de vida preciso y cálido.

Genera un informe semanal para la semana que viene. Esto es orientación proactiva —
el usuario no hizo ninguna pregunta. Antar observa su carta y señala lo que importa.

REGLAS:
- SIEMPRE comienza weekly_focus con el nombre del usuario si está disponible, p. ej. "Ramandeep, esta semana..."
- Cada señal de dominio: 2 frases como máximo. Español claro. Cero jerga.
- El enfoque semanal: un párrafo, el único tema más importante de esta semana
- Best day: nombra un día concreto de la semana para las acciones importantes
- SIEMPRE dirígete al usuario por su nombre en weekly_focus, p. ej. 'Ramandeep, esta semana...'
- Sé específico con los datos de la carta proporcionados — nada de lenguaje genérico de horóscopo
- Cálido pero preciso. Como el mensaje de un lunes por la mañana de un asesor de confianza.

Todo el texto narrativo va en ESPAÑOL. Las claves JSON se mantienen en inglés.

Devuelve SOLO este JSON:
{
  "week_of": "March 31, 2026",
  "weekly_focus": "Un párrafo — el tema dominante de esta semana y lo que significa en la práctica.",
  "best_day": "Miércoles — [razón en 5 palabras]",
  "domains": {
    "career":       "2 frases. Qué energía laboral/profesional está activa esta semana.",
    "wealth":       "2 frases. Qué energía financiera está activa esta semana.",
    "relationships":"2 frases. Qué energía de relaciones está activa esta semana.",
    "health":       "2 frases. Qué energía de salud/cuerpo está activa esta semana.",
    "spirit":       "2 frases. Qué energía espiritual/interior está activa esta semana."
  },
  "one_action": "La única acción más importante a realizar antes del domingo. Empieza con un verbo."
}"""


WEEKLY_SYSTEM_PROMPT_PT = """Você é Antar — um guia de navegação de vida preciso e acolhedor.

Gere um resumo semanal para a semana que vem. Isto é orientação proativa —
o usuário não fez nenhuma pergunta. Antar observa o mapa dele e sinaliza o que importa.

REGRAS:
- SEMPRE comece weekly_focus com o primeiro nome do usuário, se disponível, ex.: "Ramandeep, esta semana..."
- Cada sinal de domínio: no máximo 2 frases. Português claro. Zero jargão.
- O foco semanal: um parágrafo, o tema mais importante desta semana
- Best day: indique um dia específico da semana para as ações importantes
- SEMPRE trate o usuário pelo primeiro nome em weekly_focus, ex.: 'Ramandeep, esta semana...'
- Seja específico com os dados do mapa fornecidos — nada de linguagem genérica de horóscopo
- Acolhedor, mas preciso. Como a mensagem de uma segunda de manhã de um conselheiro de confiança.

Todo o texto narrativo vai em PORTUGUÊS. As chaves JSON permanecem em inglês.

Retorne APENAS este JSON:
{
  "week_of": "March 31, 2026",
  "weekly_focus": "Um parágrafo — o tema dominante desta semana e o que ele significa na prática.",
  "best_day": "Quarta-feira — [motivo em 5 palavras]",
  "domains": {
    "career":       "2 frases. Que energia profissional/de trabalho está ativa esta semana.",
    "wealth":       "2 frases. Que energia financeira está ativa esta semana.",
    "relationships":"2 frases. Que energia de relacionamentos está ativa esta semana.",
    "health":       "2 frases. Que energia de saúde/corpo está ativa esta semana.",
    "spirit":       "2 frases. Que energia espiritual/interior está ativa esta semana."
  },
  "one_action": "A única ação mais importante a realizar antes de domingo. Comece com um verbo."
}"""


def _select_weekly_prompt(language: str) -> str:
    """[loc-2] Pick the weekly-briefing system prompt for the user's language.
    [loc-3 2026-07-04] Non-EN prompts carry the hard LANGUAGE INSTRUCTION
    block as reinforcement (EN fragments were leaking into PT output);
    FR composes natively on the EN base + FR block."""
    lang = (language or "en").lower()[:2]
    base = {
        "es": WEEKLY_SYSTEM_PROMPT_ES,
        "pt": WEEKLY_SYSTEM_PROMPT_PT,
    }.get(lang, WEEKLY_SYSTEM_PROMPT)
    if lang in ("es", "pt", "fr"):
        try:
            from language_utils import build_language_instruction
            return build_language_instruction(lang) + base
        except Exception:
            pass
    return base


def _safe_jsonb_weekly(v):
    """[loc-2] Parse a JSONB column that may arrive as a JSON string."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _is_legacy_weekly_blob(blob) -> bool:
    """[loc-2] True if `blob` is a pre-loc-2 single-language briefing payload."""
    return isinstance(blob, dict) and ("weekly_focus" in blob or "domains" in blob)


async def generate_weekly_briefing(
    chart_id:      str,
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    dkp_context:   Optional[str],
    supabase,
    claude_client,
    force_refresh: bool = False,
    language: str = "en",
) -> dict:
    """
    Generate or return cached weekly briefing for a chart.
    Regenerates on Mondays or if force_refresh=True.
    """
    # [loc-2] normalize locale (es-CO -> es); en/es/pt only
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"
    now       = datetime.now(timezone.utc)
    week_start = _get_week_start(now)

    # Check cache
    if not force_refresh:
        cached = _read_cache(chart_id, week_start, supabase, language)
        if cached:
            return cached

    # Build context
    context = _build_briefing_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, age, country_code,
        dkp_context, now
    )

    # Call Claude
    result = await _call_claude(context, claude_client, language)
    result["chart_id"]   = chart_id
    result["week_start"] = week_start.isoformat()
    result["week_of"]    = week_start.strftime("%B %d, %Y")

    # Inject first_name into weekly_focus
    if first_name and result.get("weekly_focus"):
        wf = result["weekly_focus"]
        if not wf.startswith(first_name):
            result["weekly_focus"] = f"{first_name}, {wf[0].lower()}{wf[1:]}"
    if first_name and result.get("one_action"):
        oa = result["one_action"]
        if not oa.startswith(first_name):
            result["one_action"] = oa  # action stays verb-first

    # [output-strips] strip weekly_briefing
    # Route every user-facing narrative field through the central
    # output-strip layer BEFORE the cache upsert, so cached rows are
    # clean.  Language is hard-coded to 'en' because weekly_briefing
    # is currently English-only; wire chart language through when
    # /weekly-briefing goes multilingual.
    _lang = language  # [loc-2] was hard-coded 'en'
    # weekly_focus + one_action: full plain strip
    for _f in ('weekly_focus', 'one_action'):
        _v = result.get(_f)
        if isinstance(_v, str) and _v:
            result[_f] = apply_user_facing_strips(_v, language=_lang, field_type='plain')
    # best_day: 'timing' — keeps the weekday (prompt requires it), strips the rest
    _bd = result.get('best_day')
    if isinstance(_bd, str) and _bd:
        result['best_day'] = apply_user_facing_strips(_bd, language=_lang, field_type='timing')
    # domains.* — each 2-sentence domain body is a plain field
    _domains = result.get('domains')
    if isinstance(_domains, dict):
        for _dk, _dv in list(_domains.items()):
            if isinstance(_dv, str) and _dv:
                _domains[_dk] = apply_user_facing_strips(
                    _dv, language=_lang, field_type='plain'
                )

    # Save to cache — [loc-2] language-keyed. The `briefing` JSONB column holds
    # {"en": {...}, "es": {...}, "pt": {...}} so a single-language write keeps
    # the others. Mirrors daily_wow_cache. Legacy single-blob rows are discarded
    # (the read path already treated them as a MISS).
    try:
        _blob = {}
        try:
            _ex = supabase.table(BRIEFING_TABLE) \
                .select("briefing") \
                .eq("chart_id", chart_id) \
                .eq("week_start", week_start.isoformat()) \
                .execute()
            if _ex.data:
                _eb = _safe_jsonb_weekly(_ex.data[0].get("briefing"))
                if isinstance(_eb, dict) and not _is_legacy_weekly_blob(_eb):
                    _blob = _eb
        except Exception as _pre:
            logger.warning(f"[weekly] Cache pre-read failed (will overwrite): {_pre}")
        _blob[_lang] = result
        supabase.table(BRIEFING_TABLE).upsert({
            "chart_id":   chart_id,
            "week_start": week_start.isoformat(),
            "briefing":   _blob,
            "created_at": now.isoformat(),
        }, on_conflict="chart_id,week_start").execute()
        logger.info(f"[weekly] Briefing saved for chart {chart_id[:8]} lang={_lang} (langs={list(_blob.keys())})")
    except Exception as e:
        logger.warning(f"[weekly] Cache save failed: {e}")

    return result


def _get_week_start(dt: datetime) -> datetime:
    """Return Monday of the current week."""
    days_since_monday = dt.weekday()
    return (dt - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _read_cache(chart_id: str, week_start: datetime, supabase, language: str = "en") -> Optional[dict]:
    # [loc-2] language-keyed read. `briefing` is {"en": {...}, "es": {...}, ...}.
    # A legacy single-blob row is treated as a MISS so the next write migrates it.
    try:
        result = supabase.table(BRIEFING_TABLE) \
            .select("briefing") \
            .eq("chart_id", chart_id) \
            .eq("week_start", week_start.isoformat()) \
            .execute()
        if result.data:
            blob = _safe_jsonb_weekly(result.data[0].get("briefing"))
            if isinstance(blob, dict) and not _is_legacy_weekly_blob(blob):
                entry = blob.get(language)
                if isinstance(entry, dict) and entry:
                    return entry
    except Exception as e:
        logger.warning(f"[weekly] Cache read failed: {e}")
    return None


def _build_briefing_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    dkp_context:   Optional[str],
    now:           datetime,
) -> str:
    week_str  = now.strftime("Week of %B %d, %Y")
    name_str  = f"Name: {first_name}" if first_name else ""
    age_str   = f"Age: {age}" if age else ""

    planets   = chart_data.get("planets", {})
    moon_nak  = planets.get("Moon", {}).get("nakshatra", "")
    sun_sign  = planets.get("Sun",  {}).get("sign", "")

    # Get transits if available
    transits  = chart_data.get("current_transits", {})
    saturn_transit = transits.get("Saturn", {}).get("sign", "")
    jupiter_transit = transits.get("Jupiter", {}).get("sign", "")

    lines = [
        f"WEEKLY BRIEFING REQUEST — {week_str}",
        name_str,
        f"Rising sign: {lagna or 'unknown'}",
        f"Moon sign: {moon_sign or 'unknown'}, Moon nakshatra: {moon_nak}",
        f"Sun sign: {sun_sign}",
        f"Current planetary period: {current_dasha or 'unknown'}",
    ]

    if age_str:          lines.append(age_str)
    if country_code:     lines.append(f"Country: {country_code}")
    if saturn_transit:   lines.append(f"Saturn currently in: {saturn_transit}")
    if jupiter_transit:  lines.append(f"Jupiter currently in: {jupiter_transit}")

    if dkp_context:
        # Add first 2 lines of DKP only
        dkp_lines = [l for l in dkp_context.split("\n") if l.strip()][:2]
        lines.append("Economic context: " + " ".join(dkp_lines))

    lines.append(
        f"\nGenerate a weekly briefing for the week ahead ({week_str}). "
        "Cover all 5 life domains. Be specific to this chart's current period."
    )

    return "\n".join(l for l in lines if l)


async def _call_claude(context: str, claude_client, language: str = "en") -> dict:
    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=_select_weekly_prompt(language),
            messages=[{"role": "user", "content": context}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"[weekly] Claude call failed: {e}")
        return _fallback_briefing()


def _fallback_briefing() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "week_of":       now.strftime("%B %d, %Y"),
        "weekly_focus":  "Your chart is active this week. Ask Antar a specific question to get a precise reading.",
        "best_day":      "Wednesday — mid-week clarity",
        "domains": {
            "career":        "Focus on completing existing projects before starting new ones.",
            "wealth":        "Review your financial commitments this week.",
            "relationships": "Invest time in your most important relationship.",
            "health":        "Prioritise sleep and reduce stimulants.",
            "spirit":        "A quiet 10 minutes in the morning will anchor your week."
        },
        "one_action": "Identify your single most important task and do it first thing Monday.",
    }
