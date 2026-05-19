"""
antar_engine/monthly_deepdive.py
Sprint E — Monthly Deep-Dive

On the 1st of each month, Antar generates a full monthly reading:
  - Which planets are strong/weak this month (Masik Phal)
  - 3 priority actions for the month
  - Remedies specific to this chart this month
  - Key timing windows — best and worst weeks

Cached per chart per month. Generated on the 1st via cron.
Also available on-demand via GET /api/v1/monthly-deepdive/{chart_id}
"""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Optional

# [output-strips] migrate monthly_deepdive
from antar_engine.output_strips import apply_user_facing_strips

# [cp-day1] masik phal import
from antar_engine.lal_kitab_masik import build_masik_context_block, calculate_masik_phal

# [cp-day3] transit events import
from antar_engine.transit_events import compute_transit_events_in_range, bucket_events_by_week

logger = logging.getLogger(__name__)

# [cp-day4a] hot-domain aggregation helper
# [cp-day6] monthly remedy helpers
# [cp-day7] monthly energy + week-tone helpers

def _compute_energy_level(strong_count: int, weak_count: int) -> str:
    """
    Deterministic enum from masik strong / weak planet counts.
      strong ≥ 2 and weak ≥ 2              → 'mixed'
      strong ≥ weak + 2                    → 'high'
      weak   ≥ strong + 2                  → 'low'
      otherwise                            → 'moderate'
    """
    s = max(0, int(strong_count or 0))
    w = max(0, int(weak_count   or 0))
    if s >= 2 and w >= 2:
        return 'mixed'
    if s >= w + 2:
        return 'high'
    if w >= s + 2:
        return 'low'
    return 'moderate'

# Which planets are 'benefic' vs 'malefic' for tone scoring
_BENEFIC = frozenset(('Jupiter', 'Venus', 'Mercury', 'Moon'))
_MALEFIC = frozenset(('Saturn', 'Mars', 'Rahu', 'Ketu', 'Sun'))

def _score_event_tone(ev: dict) -> float:
    """
    Return signed tone score for a single transit event.
    Benefic trine/sextile/conjunction → positive.
    Malefic square/opposition         → negative.
    Retro start (any planet)          → mild negative.
    Ingress / nakshatra_shift         → near zero.
    Magnitude grows with tightness of orb for aspects.
    """
    etype  = ev.get('event_type')
    planet = ev.get('planet', '')
    if etype == 'aspect':
        kind = ev.get('aspect_kind', '')
        orb  = float(ev.get('orb') or 2.0)
        magnitude = max(0.2, 3.0 - orb)
        if kind in ('trine', 'sextile', 'conjunction'):
            # Benefic planet making a soft aspect → clearly positive.
            # Malefic planet making a soft aspect → mild positive.
            return magnitude if planet in _BENEFIC else magnitude * 0.4
        if kind in ('square', 'opposition'):
            # Malefic hard aspect → clearly negative.
            # Benefic hard aspect → mild negative.
            return -magnitude if planet in _MALEFIC else -magnitude * 0.4
        return 0.0
    if etype == 'retro_start':
        return -0.5 if planet in _MALEFIC else -0.2
    if etype == 'retro_end':
        return 0.3
    if etype == 'ingress':
        # Benefic moving forward = slightly positive, malefic = neutral
        return 0.4 if planet in _BENEFIC else 0.0
    return 0.0

def _pick_best_and_caution_weeks(weeks: list) -> tuple[str, str]:
    """
    Given a list of week buckets (from bucket_events_by_week), score
    each week by summed event tone and return:
        (best_week_start_iso, caution_week_start_iso)
    If fewer than 2 weeks, best and caution may both be the same week.
    Empty input returns ('', '').
    """
    if not weeks:
        return ('', '')
    scored = []
    for wk in weeks:
        total = sum(_score_event_tone(e) for e in (wk.get('events') or []))
        scored.append((wk.get('week_start', ''), total))
    # Best = highest tone score, caution = lowest.
    best    = max(scored, key=lambda t: t[1])[0]
    caution = min(scored, key=lambda t: t[1])[0]
    # Edge case: if both end up the same, pick second-lowest for caution
    if best == caution and len(scored) > 1:
        others = sorted([s for s in scored if s[0] != best], key=lambda t: t[1])
        caution = others[0][0]
    return (best, caution)

# [cp-day5] canonical remedy practice builder
def _canonical_practice(planet: str) -> str:
    """
    Build a chart-agnostic canonical practice string from
    remedies.PLANET_MANTRAS.  Returns '' for unknown planets.
    """
    try:
        from antar_engine.remedies import PLANET_MANTRAS
    except Exception:
        return ''
    m = PLANET_MANTRAS.get(planet) if isinstance(planet, str) else None
    if not m:
        return ''
    mantra  = m.get('simple', '')
    purpose = (m.get('purpose') or '').strip().rstrip('.').lower()
    count   = m.get('count', 108)
    day     = m.get('recommended_day', 'any day')
    return f"{mantra} — for {purpose}. Chant {count} times on {day}."

def _pick_monthly_remedy_planets(masik_weak: list, current_dasha: str | None,
                                  top_n: int = 3) -> list[str]:
    """
    Prefer the month's weak planets (from Masik Phal) first.  Pad with
    current_dasha lord then Saturn if short.
    ``masik_weak`` is the 'weak_planets' list from calculate_masik_phal,
    where each entry is a dict {planet: 'Sun', house: 6, ...}.
    """
    picks: list[str] = []
    for entry in (masik_weak or []):
        if len(picks) >= top_n:
            break
        name = entry.get('planet') if isinstance(entry, dict) else entry
        if isinstance(name, str) and name and name not in picks:
            picks.append(name)
    # Pad with dasha lord if missing
    if len(picks) < top_n and isinstance(current_dasha, str) and current_dasha.strip():
        lord = current_dasha.strip().split()[0].split('/')[0].strip()
        if lord and lord not in picks:
            picks.append(lord)
    # Final pad with Saturn (classical universal discipline remedy)
    if len(picks) < top_n and 'Saturn' not in picks:
        picks.append('Saturn')
    return picks[:top_n]

# Map each natal house to a user-facing domain the priority_actions
# schema expects.  H3 (effort/initiative) folds into career so users
# see actionable advice instead of abstract 'communication'.  H8
# (transformation/hidden stress) folds into health.
_HOUSE_TO_DOMAIN = {
    1:  'health',        2:  'wealth',          3:  'career',
    4:  'home',          5:  'learning',        6:  'health',
    7:  'relationships', 8:  'health',          9:  'spiritual',
    10: 'career',        11: 'wealth',          12: 'spiritual',
}
_EVENT_WEIGHT = {
    'aspect':          3,
    'ingress':         2,
    'retro_start':     2,
    'retro_end':       2,
    'nakshatra_shift': 1,
}
# Safe fallback ordering — if aggregation yields < 3 distinct
# domains, pad with these in priority.
_FALLBACK_DOMAINS = ('career', 'wealth', 'health', 'relationships')

def _aggregate_hot_domains(events: list, top_n: int = 3) -> tuple[list, dict]:
    """
    Return (domain_list, score_map).  domain_list is the top_n domains
    by weighted event score, padded from _FALLBACK_DOMAINS if fewer
    than top_n have nonzero score.  score_map is {domain: {score, event_count}}
    for every domain that had at least one event.
    """
    tally: dict[str, dict] = {}
    for ev in (events or []):
        house = ev.get('natal_house')
        etype = ev.get('event_type')
        if not isinstance(house, int) or house < 1 or house > 12:
            continue
        domain = _HOUSE_TO_DOMAIN.get(house)
        if not domain:
            continue
        weight = _EVENT_WEIGHT.get(etype, 1)
        slot = tally.setdefault(domain, {'score': 0, 'event_count': 0})
        slot['score']       += weight
        slot['event_count'] += 1
    ranked = sorted(tally.items(), key=lambda kv: (-kv[1]['score'], kv[0]))
    ordered = [d for d, _ in ranked]
    # Pad with fallback domains if we don't have enough
    for d in _FALLBACK_DOMAINS:
        if len(ordered) >= top_n:
            break
        if d not in ordered:
            ordered.append(d)
    return ordered[:top_n], tally

DEEPDIVE_TABLE = "monthly_deepdives"

MONTHLY_SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation advisor.

Generate a full monthly deep-dive reading. This is proactive coaching for the month ahead.
The user did not ask a specific question — Antar is providing a complete monthly overview.

RULES:
- ALWAYS start overview with the user's first name if provided e.g. "Ramandeep, this month..."
- Plain English throughout. Zero jargon.
- Be specific to the chart data provided — actual planets, actual timing
- 3 priority actions: specific, actionable, different domains
- Remedies: practical and tied to specific chart placements
- Timing windows: name specific weeks, not vague periods
- [cp-day1b] COMPUTED JSON VALUES rule — at the end of the user context below
  you will find a block labeled 'COMPUTED JSON VALUES — COPY THESE ARRAYS INTO
  YOUR RESPONSE'.  The strong_planets and weak_planets arrays in your JSON
  response MUST be character-for-character copies of the arrays in that block.
  Do not add planets.  Do not remove planets.  Do not reorder.  Do not re-derive
  the assessment.  These values are computed deterministically from the chart;
  your job is to narrate the priority_actions, overview, and monthly_mantra
  that flow from them.  If the COMPUTED JSON VALUES block is absent, fall back
  to your own judgment — but when present, it overrides.
- [cp-day3] WEEKLY TRANSIT SCHEDULE rule — if the user context contains a
  'WEEKLY TRANSIT SCHEDULE' block followed by 'available_weeks' in COMPUTED
  JSON VALUES, the best_week and caution_week JSON fields MUST begin with
  'Week of <Month> <D>' where the date is one of the week_start entries
  listed in available_weeks.  Do not invent weeks outside this list.  Pick
  best_week based on supportive aspects / benefic ingresses in the schedule;
  pick caution_week based on challenging aspects / retrograde stations /
  malefic ingresses.  The reason clause after the em-dash can be your own
  phrasing but must cite events from that week's schedule.
- [cp-day4a] HOT DOMAINS rule — if the user context contains a
  'priority_action_domains' array in COMPUTED JSON VALUES, the
  priority_actions JSON array in your response MUST contain exactly
  len(priority_action_domains) entries, and the 'domain' field of each
  entry MUST equal priority_action_domains[i] in that exact order.
  Do not substitute other domains.  Do not add or remove entries.
  Write one specific, verb-first action per domain that references
  the concrete transit events listed in the WEEKLY TRANSIT SCHEDULE
  for that domain's houses.
- [cp-day6] monthly remedies rule — if the context contains a
  'monthly_remedies_list' in COMPUTED JSON VALUES, the remedies
  array in your response MUST be a character-for-character copy of
  that list — same length, same planets in the same order, same
  practice text verbatim.  Do not substitute planets.  Do not
  rewrite practice text.  These are canonical classical mantras.
- [cp-day7] energy_level + best/caution week rule —
  (a) energy_level MUST equal the computed value shown under
      'COMPUTED JSON VALUES — energy_level MUST be:' verbatim.
  (b) If best_week_start / caution_week_start are provided,
      the best_week and caution_week JSON fields MUST begin with
      'Week of <Month> <D>' where the date equals the computed
      start date.  Reason clause after the em-dash is your own
      phrasing but must cite events from that specific week's
      schedule.

Return ONLY this JSON:
{
  "month":          "April 2026",
  "month_theme":    "One sentence — what this month is fundamentally about for this person.",
  "energy_level":   "high OR moderate OR low OR mixed",
  "strong_planets": ["planet1", "planet2"],
  "weak_planets":   ["planet1"],
  "overview":       "2-3 sentences. Overall energy of the month. What is the dominant theme.",
  "priority_actions": [
    {"domain": "career",  "action": "Specific action for this month. Verb-first."},
    {"domain": "wealth",  "action": "Specific action for this month. Verb-first."},
    {"domain": "health",  "action": "Specific action for this month. Verb-first."}
  ],
  "best_week":  "Week of [date] — [reason in 6 words]",
  "caution_week": "Week of [date] — [what to avoid in 5 words]",
  "remedies": [
    {"planet": "Saturn", "practice": "Specific remedy. One sentence."},
    {"planet": "Moon",   "practice": "Specific remedy. One sentence."}
  ],
  "monthly_mantra": "One plain English affirmation for this month. Under 10 words."
}"""


MONTHLY_SYSTEM_PROMPT_ES = """Eres Antar — un guía de navegación de vida preciso y cálido.

Genera un análisis mensual completo. Esto es orientación proactiva para el mes que viene.
El usuario no hizo ninguna pregunta concreta — Antar ofrece un panorama mensual completo.

REGLAS:
- SIEMPRE comienza overview con el nombre del usuario si está disponible, p. ej. "Ramandeep, este mes..."
- Español claro en todo momento. Cero jerga.
- Sé específico con los datos de la carta proporcionados — planetas reales, tiempos reales
- 3 acciones prioritarias: concretas, accionables, de dominios distintos
- Remedios: prácticos y ligados a posiciones concretas de la carta
- Ventanas de tiempo: nombra semanas concretas, no periodos vagos
- [cp-day1b] regla COMPUTED JSON VALUES — al final del contexto del usuario
  encontrarás un bloque etiquetado 'COMPUTED JSON VALUES — COPY THESE ARRAYS INTO
  YOUR RESPONSE'.  Los arrays strong_planets y weak_planets de tu respuesta JSON
  DEBEN ser copias carácter por carácter de los arrays de ese bloque.
  No añadas planetas.  No quites planetas.  No los reordenes.  No vuelvas a derivar
  la evaluación.  Estos valores se calculan de forma determinista a partir de la carta;
  tu tarea es narrar priority_actions, overview y monthly_mantra que se desprenden
  de ellos.  Si el bloque COMPUTED JSON VALUES no está presente, usa tu propio
  criterio — pero cuando está presente, prevalece.
- [cp-day3] regla WEEKLY TRANSIT SCHEDULE — si el contexto del usuario contiene un
  bloque 'WEEKLY TRANSIT SCHEDULE' seguido de 'available_weeks' en COMPUTED
  JSON VALUES, los campos JSON best_week y caution_week DEBEN empezar con
  'Week of <Month> <D>' donde la fecha es una de las entradas week_start
  listadas en available_weeks.  No inventes semanas fuera de esta lista.  Elige
  best_week según aspectos favorables / ingresos de benéficos en el calendario;
  elige caution_week según aspectos desafiantes / estaciones retrógradas /
  ingresos de maléficos.  La cláusula de razón tras el guión largo puede ser tu
  propia redacción pero debe citar eventos del calendario de esa semana.
  ('Week of' y la fecha se mantienen en inglés porque coinciden con available_weeks.)
- [cp-day4a] regla HOT DOMAINS — si el contexto del usuario contiene un
  array 'priority_action_domains' en COMPUTED JSON VALUES, el array
  priority_actions de tu respuesta DEBE contener exactamente
  len(priority_action_domains) entradas, y el campo 'domain' de cada
  entrada DEBE ser igual a priority_action_domains[i] en ese orden exacto.
  No sustituyas otros dominios.  No añadas ni quites entradas.  Escribe una
  acción concreta que empiece con verbo por dominio y que haga referencia a
  los eventos de tránsito listados en el WEEKLY TRANSIT SCHEDULE para las
  casas de ese dominio.
- [cp-day6] regla de remedios mensuales — si el contexto contiene una
  'monthly_remedies_list' en COMPUTED JSON VALUES, el array remedies
  de tu respuesta DEBE ser una copia carácter por carácter de esa lista —
  misma longitud, mismos planetas en el mismo orden, mismo texto de practice
  literal.  No sustituyas planetas.  No reescribas el texto de practice.
  Son mantras clásicos canónicos.
- [cp-day7] regla energy_level + best/caution week —
  (a) energy_level DEBE ser igual al valor calculado que se muestra bajo
      'COMPUTED JSON VALUES — energy_level MUST be:' de forma literal.
  (b) Si se proporcionan best_week_start / caution_week_start, los campos
      JSON best_week y caution_week DEBEN empezar con 'Week of <Month> <D>'
      donde la fecha sea igual a la fecha de inicio calculada.  La cláusula
      de razón tras el guión largo es tu propia redacción pero debe citar
      eventos del calendario de esa semana concreta.

Todo el texto narrativo va en ESPAÑOL. Las claves JSON, los valores enum
(energy_level), los nombres de planetas copiados de COMPUTED JSON VALUES y los
prefijos 'Week of' con sus fechas se mantienen en inglés.

Devuelve SOLO este JSON:
{
  "month":          "April 2026",
  "month_theme":    "Una frase — de qué trata fundamentalmente este mes para esta persona.",
  "energy_level":   "high OR moderate OR low OR mixed",
  "strong_planets": ["planet1", "planet2"],
  "weak_planets":   ["planet1"],
  "overview":       "2-3 frases. Energía general del mes. Cuál es el tema dominante.",
  "priority_actions": [
    {"domain": "career",  "action": "Acción concreta para este mes. Empieza con verbo."},
    {"domain": "wealth",  "action": "Acción concreta para este mes. Empieza con verbo."},
    {"domain": "health",  "action": "Acción concreta para este mes. Empieza con verbo."}
  ],
  "best_week":  "Week of [date] — [razón en 6 palabras]",
  "caution_week": "Week of [date] — [qué evitar en 5 palabras]",
  "remedies": [
    {"planet": "Saturn", "practice": "Remedio concreto. Una frase."},
    {"planet": "Moon",   "practice": "Remedio concreto. Una frase."}
  ],
  "monthly_mantra": "Una afirmación en español claro para este mes. Menos de 10 palabras."
}"""


MONTHLY_SYSTEM_PROMPT_PT = """Você é Antar — um guia de navegação de vida preciso e acolhedor.

Gere um aprofundamento mensal completo. Isto é orientação proativa para o mês que vem.
O usuário não fez nenhuma pergunta específica — Antar oferece um panorama mensal completo.

REGRAS:
- SEMPRE comece overview com o primeiro nome do usuário, se disponível, ex.: "Ramandeep, este mês..."
- Português claro o tempo todo. Zero jargão.
- Seja específico com os dados do mapa fornecidos — planetas reais, tempos reais
- 3 ações prioritárias: concretas, acionáveis, de domínios distintos
- Remédios: práticos e ligados a posições concretas do mapa
- Janelas de tempo: indique semanas concretas, não períodos vagos
- [cp-day1b] regra COMPUTED JSON VALUES — ao final do contexto do usuário
  você encontrará um bloco rotulado 'COMPUTED JSON VALUES — COPY THESE ARRAYS INTO
  YOUR RESPONSE'.  Os arrays strong_planets e weak_planets da sua resposta JSON
  DEVEM ser cópias caractere por caractere dos arrays desse bloco.
  Não adicione planetas.  Não remova planetas.  Não reordene.  Não re-derive
  a avaliação.  Esses valores são calculados de forma determinística a partir do
  mapa; sua tarefa é narrar priority_actions, overview e monthly_mantra que
  decorrem deles.  Se o bloco COMPUTED JSON VALUES estiver ausente, use seu
  próprio critério — mas quando presente, ele prevalece.
- [cp-day3] regra WEEKLY TRANSIT SCHEDULE — se o contexto do usuário contiver um
  bloco 'WEEKLY TRANSIT SCHEDULE' seguido de 'available_weeks' em COMPUTED
  JSON VALUES, os campos JSON best_week e caution_week DEVEM começar com
  'Week of <Month> <D>' onde a data é uma das entradas week_start listadas em
  available_weeks.  Não invente semanas fora desta lista.  Escolha best_week
  com base em aspectos favoráveis / ingressos de benéficos no calendário;
  escolha caution_week com base em aspectos desafiadores / estações retrógradas
  / ingressos de maléficos.  A cláusula de motivo após o travessão pode ser sua
  própria redação, mas deve citar eventos do calendário daquela semana.
  ('Week of' e a data permanecem em inglês porque coincidem com available_weeks.)
- [cp-day4a] regra HOT DOMAINS — se o contexto do usuário contiver um
  array 'priority_action_domains' em COMPUTED JSON VALUES, o array
  priority_actions da sua resposta DEVE conter exatamente
  len(priority_action_domains) entradas, e o campo 'domain' de cada
  entrada DEVE ser igual a priority_action_domains[i] nessa ordem exata.
  Não substitua outros domínios.  Não adicione nem remova entradas.  Escreva
  uma ação concreta começando com verbo por domínio que faça referência aos
  eventos de trânsito listados no WEEKLY TRANSIT SCHEDULE para as casas
  daquele domínio.
- [cp-day6] regra de remédios mensais — se o contexto contiver uma
  'monthly_remedies_list' em COMPUTED JSON VALUES, o array remedies
  da sua resposta DEVE ser uma cópia caractere por caractere dessa lista —
  mesmo comprimento, mesmos planetas na mesma ordem, mesmo texto de practice
  literal.  Não substitua planetas.  Não reescreva o texto de practice.
  São mantras clássicos canônicos.
- [cp-day7] regra energy_level + best/caution week —
  (a) energy_level DEVE ser igual ao valor calculado mostrado sob
      'COMPUTED JSON VALUES — energy_level MUST be:' de forma literal.
  (b) Se best_week_start / caution_week_start forem fornecidos, os campos
      JSON best_week e caution_week DEVEM começar com 'Week of <Month> <D>'
      onde a data seja igual à data de início calculada.  A cláusula de
      motivo após o travessão é sua própria redação, mas deve citar eventos
      do calendário daquela semana específica.

Todo o texto narrativo vai em PORTUGUÊS. As chaves JSON, os valores enum
(energy_level), os nomes de planetas copiados de COMPUTED JSON VALUES e os
prefixos 'Week of' com suas datas permanecem em inglês.

Retorne APENAS este JSON:
{
  "month":          "April 2026",
  "month_theme":    "Uma frase — do que este mês se trata fundamentalmente para esta pessoa.",
  "energy_level":   "high OR moderate OR low OR mixed",
  "strong_planets": ["planet1", "planet2"],
  "weak_planets":   ["planet1"],
  "overview":       "2-3 frases. Energia geral do mês. Qual é o tema dominante.",
  "priority_actions": [
    {"domain": "career",  "action": "Ação concreta para este mês. Comece com verbo."},
    {"domain": "wealth",  "action": "Ação concreta para este mês. Comece com verbo."},
    {"domain": "health",  "action": "Ação concreta para este mês. Comece com verbo."}
  ],
  "best_week":  "Week of [date] — [motivo em 6 palavras]",
  "caution_week": "Week of [date] — [o que evitar em 5 palavras]",
  "remedies": [
    {"planet": "Saturn", "practice": "Remédio concreto. Uma frase."},
    {"planet": "Moon",   "practice": "Remédio concreto. Uma frase."}
  ],
  "monthly_mantra": "Uma afirmação em português claro para este mês. Menos de 10 palavras."
}"""


def _select_monthly_prompt(language: str) -> str:
    """[loc-2] Pick the monthly-deepdive system prompt for the user's language."""
    return {
        "es": MONTHLY_SYSTEM_PROMPT_ES,
        "pt": MONTHLY_SYSTEM_PROMPT_PT,
    }.get((language or "en").lower(), MONTHLY_SYSTEM_PROMPT)


def _safe_jsonb_monthly(v):
    """[loc-2] Parse a JSONB column that may arrive as a JSON string."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _is_legacy_monthly_blob(blob) -> bool:
    """[loc-2] True if `blob` is a pre-loc-2 single-language deepdive payload."""
    return isinstance(blob, dict) and ("overview" in blob or "month_theme" in blob)


async def generate_monthly_deepdive(
    chart_id:      str,
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    lk_context:    Optional[str],
    supabase,
    claude_client,
    force_refresh: bool = False,
    birth_date:    Optional[str] = None,   # [cp-day1] birth_date kwarg
    language:      str = "en",
) -> dict:
    """
    Generate or return cached monthly deep-dive.
    Regenerates on the 1st of each month or if force_refresh=True.
    """
    # [loc-2] normalize locale (es-CO -> es); en/es/pt only
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"
    now        = datetime.now(timezone.utc)
    month_key  = now.strftime("%Y-%m")

    # Check cache
    if not force_refresh:
        cached = _read_cache(chart_id, month_key, supabase, language)
        if cached:
            return cached

    # Build context
    # [cp-day1] pass birth_date to context builder
    _bd = birth_date or chart_data.get('birth_date') or ''
    context = _build_deepdive_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, age, country_code,
        lk_context, now, _bd,
    )

    # Call Claude
    result = await _call_claude(context, claude_client, language)
    result["chart_id"]  = chart_id
    result["month_key"] = month_key

    # Inject first_name into overview
    if first_name and result.get("overview"):
        ov = result["overview"]
        if not ov.startswith(first_name):
            result["overview"] = f"{first_name}, {ov[0].lower()}{ov[1:]}"
    if first_name and result.get("month_theme"):
        mt = result["month_theme"]
        if not mt.startswith(first_name):
            result["month_theme"] = f"{first_name}: {mt}"  

    # [output-strips] strip monthly_deepdive
    # Route every user-facing narrative field through the central
    # output-strip layer BEFORE the cache upsert so cached rows stay
    # clean.  Hard-coded 'en' — match current prompt behavior.
    #
    # Plain fields (full strip):
    #   month_theme, overview, best_week, caution_week, monthly_mantra,
    #   priority_actions[].action, remedies[].practice
    # Skipped (enums / dates / proper-noun arrays):
    #   month, energy_level, priority_actions[].domain,
    #   strong_planets[], weak_planets[], remedies[].planet,
    #   chart_id, month_key
    _lang = language  # [loc-2] was hard-coded 'en'
    for _f in ('month_theme', 'overview', 'best_week', 'caution_week', 'monthly_mantra'):
        _v = result.get(_f)
        if isinstance(_v, str) and _v:
            result[_f] = apply_user_facing_strips(
                _v, language=_lang, field_type='plain'
            )
    _pas = result.get('priority_actions')
    if isinstance(_pas, list):
        for _pa in _pas:
            if isinstance(_pa, dict):
                _action = _pa.get('action')
                if isinstance(_action, str) and _action:
                    _pa['action'] = apply_user_facing_strips(
                        _action, language=_lang, field_type='plain'
                    )
    _rems = result.get('remedies')
    if isinstance(_rems, list):
        for _r in _rems:
            if isinstance(_r, dict):
                _pr = _r.get('practice')
                if isinstance(_pr, str) and _pr:
                    _r['practice'] = apply_user_facing_strips(
                        _pr, language=_lang, field_type='plain'
                    )

    # Save to cache — [loc-2] language-keyed. The `deepdive` JSONB column holds
    # {"en": {...}, "es": {...}, "pt": {...}} so a single-language write keeps
    # the others. Mirrors daily_wow_cache. Legacy single-blob rows are discarded
    # (the read path already treated them as a MISS).
    try:
        _blob = {}
        try:
            _ex = supabase.table(DEEPDIVE_TABLE) \
                .select("deepdive") \
                .eq("chart_id", chart_id) \
                .eq("month_key", month_key) \
                .execute()
            if _ex.data:
                _eb = _safe_jsonb_monthly(_ex.data[0].get("deepdive"))
                if isinstance(_eb, dict) and not _is_legacy_monthly_blob(_eb):
                    _blob = _eb
        except Exception as _pre:
            logger.warning(f"[monthly] Cache pre-read failed (will overwrite): {_pre}")
        _blob[_lang] = result
        supabase.table(DEEPDIVE_TABLE).upsert({
            "chart_id":  chart_id,
            "month_key": month_key,
            "deepdive":  _blob,
            "created_at": now.isoformat(),
        }, on_conflict="chart_id,month_key").execute()
        logger.info(f"[monthly] Deep-dive saved for {chart_id[:8]} {month_key} lang={_lang} (langs={list(_blob.keys())})")
    except Exception as e:
        logger.warning(f"[monthly] Cache save failed: {e}")

    return result


def _read_cache(chart_id: str, month_key: str, supabase, language: str = "en") -> Optional[dict]:
    # [loc-2] language-keyed read. `deepdive` is {"en": {...}, "es": {...}, ...}.
    # A legacy single-blob row is treated as a MISS so the next write migrates it.
    try:
        result = supabase.table(DEEPDIVE_TABLE) \
            .select("deepdive") \
            .eq("chart_id", chart_id) \
            .eq("month_key", month_key) \
            .execute()
        if result.data:
            blob = _safe_jsonb_monthly(result.data[0].get("deepdive"))
            if isinstance(blob, dict) and not _is_legacy_monthly_blob(blob):
                entry = blob.get(language)
                if isinstance(entry, dict) and entry:
                    return entry
    except Exception as e:
        logger.warning(f"[monthly] Cache read failed: {e}")
    return None


def _build_deepdive_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    lk_context:    Optional[str],
    now:           datetime,
    birth_date:    str = '',   # [cp-day1] accept birth_date
) -> str:
    month_str = now.strftime("%B %Y")
    planets   = chart_data.get("planets", {})

    # Planet positions
    planet_positions = []
    for planet, data in planets.items():
        if isinstance(data, dict):
            sign = data.get("sign", "")
            house = data.get("house", "")
            if sign:
                planet_positions.append(f"{planet} in {sign}" + (f" (house {house})" if house else ""))

    # Lal Kitab monthly context
    lk_note = ""
    if lk_context:
        lk_lines = lk_context.split("\n")[:3]
        lk_note = "Lal Kitab context: " + " ".join(lk_lines)

    lines = [
        f"MONTHLY DEEP-DIVE REQUEST — {month_str}",
        f"Name: {first_name or 'not provided'}",
        f"Rising sign: {lagna or 'unknown'}",
        f"Moon sign: {moon_sign or 'unknown'}",
        f"Current planetary period: {current_dasha or 'unknown'}",
        f"Age: {age or 'unknown'}",
        f"Country: {country_code or 'unknown'}",
        "",
        "PLANET POSITIONS:",
    ] + planet_positions[:9]

    if lk_note:
        lines.append(lk_note)

    # [cp-day1b] explicit COMPUTED JSON VALUES injection
    # Day 1 proved the masik block reaches Claude but the narrative format
    # gave Claude too much room to cherry-pick.  Now we ALSO append a
    # ready-made arrays block that mirrors the JSON schema exactly.
    if birth_date:
        try:
            _masik_block = build_masik_context_block(birth_date, planets)
            _masik_data  = calculate_masik_phal(birth_date, planets)
            _strong_names = [p['planet'] for p in _masik_data.get('strong_planets', [])]
            _weak_names   = [p['planet'] for p in _masik_data.get('weak_planets',   [])]
            # Server log — shows up in Railway; confirms compute and prompt wiring
            logger.info(
                f'[monthly-day1] masik computed: strong={_strong_names} '
                f'weak={_weak_names} month={_masik_data.get("month_name")}'
            )
            if _masik_block:
                lines.append('')
                lines.append('STRUCTURAL FACTS — chart-computed monthly assessment:')
                lines.append(_masik_block)
            # Machine-readable block Claude must copy verbatim
            import json as _json_inner
            lines.append('')
            lines.append('COMPUTED JSON VALUES — COPY THESE ARRAYS INTO YOUR RESPONSE:')
            lines.append(f'  strong_planets: {_json_inner.dumps(_strong_names)}')
            lines.append(f'  weak_planets:   {_json_inner.dumps(_weak_names)}')
            lines.append('(Do not substitute. Do not reorder. Do not add or remove planets.)')

            # [cp-day6] monthly remedies injection
            _mon_remedy_planets = _pick_monthly_remedy_planets(
                _masik_data.get('weak_planets', []),
                current_dasha,
                top_n=3,
            )
            _mon_remedy_list = [
                {'planet': _p, 'practice': _canonical_practice(_p)}
                for _p in _mon_remedy_planets
            ]
            print(f'[monthly-day6] remedies={_mon_remedy_planets}')
            lines.append('')
            lines.append('CANONICAL MONTHLY REMEDIES — from classical planetary mantras:')
            for _r in _mon_remedy_list:
                lines.append(f'  {_r["planet"]}: {_r["practice"]}')
            lines.append('')
            lines.append('COMPUTED JSON VALUES — remedies array MUST be exactly this list:')
            lines.append(f'  monthly_remedies_list: {_json_inner.dumps(_mon_remedy_list)}')
            lines.append('(Each entry {planet, practice} must be a character-for-character copy.)')
        except Exception as _mp_err:
            # Never block the deep-dive on masik phal failure
            logger.warning(f'[monthly] masik phal block skipped: {_mp_err}')
    else:
        logger.info('[monthly-day1] no birth_date — masik block skipped')

    # [cp-day3] WEEKLY TRANSIT SCHEDULE block — Day 2 event engine output
    # bucketed into Monday-start weeks.  Best/caution weeks must be picked
    # from this list rather than invented by Claude.
    try:
        # Target the calendar month the prompt is about
        from datetime import date as _date, timedelta as _td
        _m_start = now.replace(day=1).date()
        if now.month == 12:
            _next_first = now.replace(year=now.year + 1, month=1, day=1)
        else:
            _next_first = now.replace(month=now.month + 1, day=1)
        _m_end = (_next_first - _td(days=1)).date()

        _events = compute_transit_events_in_range(chart_data, _m_start, _m_end)
        _weeks  = bucket_events_by_week(_events, _m_start)
        logger.info(
            f'[monthly-day3] weekly schedule: {len(_weeks)} weeks, '
            f'{len(_events)} events total, range {_m_start}..{_m_end}'
        )

        if _weeks:
            import json as _json_sch
            lines.append('')
            lines.append('WEEKLY TRANSIT SCHEDULE — pick best_week and caution_week from here:')
            _available_week_starts = []
            for _wk in _weeks:
                _wstart = _wk['week_start']
                _wend   = _wk['week_end']
                _wlabel = _wk['week_label']
                _wevs   = _wk['events']
                _available_week_starts.append(_wstart)
                lines.append('')
                lines.append(f'  {_wlabel} ({_wstart} → {_wend}): {len(_wevs)} events')
                # Show up to 6 highest-signal events per week
                _shown = 0
                for _ev in _wevs:
                    if _shown >= 6: break
                    _det = _ev.get('detail', '')
                    _edate = _ev.get('date', '')
                    _etype = _ev.get('event_type', '')
                    lines.append(f'    • {_edate}  [{_etype}]  {_det}')
                    _shown += 1
                if len(_wevs) > 6:
                    lines.append(f'    … and {len(_wevs) - 6} more events this week')
            lines.append('')
            lines.append('COMPUTED JSON VALUES — best_week and caution_week must reference one of these:')
            lines.append(f'  available_weeks: {_json_sch.dumps(_available_week_starts)}')
            lines.append('(Format as "Week of <Month> <D> — <reason>" using one of the above dates.)')

            # [cp-day4a] HOT DOMAINS injection
            _hot_domains, _tally = _aggregate_hot_domains(_events, top_n=3)
            logger.info(
                f'[monthly-day4a] hot domains: {_hot_domains} '
                f'(scores={_tally})'
            )
            lines.append('')
            lines.append('HOT DOMAINS THIS MONTH (by transit-to-natal-house activation score):')
            _rank = 1
            for _d in _hot_domains:
                _slot = _tally.get(_d, {'score': 0, 'event_count': 0})
                lines.append(
                    f'  {_rank}. {_d} — score {_slot["score"]} '
                    f'across {_slot["event_count"]} events'
                )
                _rank += 1
            lines.append('')
            lines.append('COMPUTED JSON VALUES — priority_actions MUST cover exactly these domains in this order:')
            lines.append(f'  priority_action_domains: {_json_sch.dumps(_hot_domains)}')
            lines.append('(Write one verb-first action per domain, citing the transit events above.)')

            # [cp-day7] monthly energy + week picks injection
            # energy_level from masik strong/weak counts (pinned to fix regression)
            _energy = _compute_energy_level(
                len(_strong_names or []), len(_weak_names or []),
            )
            # best_week / caution_week picked deterministically from
            # aspect-tone scoring of the weekly schedule.
            _best_ws, _caution_ws = _pick_best_and_caution_weeks(_weeks)
            print(
                f'[monthly-day7] energy={_energy!r} '
                f'best_week_start={_best_ws!r} '
                f'caution_week_start={_caution_ws!r}'
            )
            lines.append('')
            lines.append(f'COMPUTED JSON VALUES — energy_level MUST be: {_json_sch.dumps(_energy)}')
            lines.append('(Copy this enum value into the energy_level field verbatim.)')
            if _best_ws or _caution_ws:
                lines.append('')
                lines.append('COMPUTED JSON VALUES — best_week and caution_week week_start dates MUST be:')
                lines.append(f'  best_week_start:    {_json_sch.dumps(_best_ws)}')
                lines.append(f'  caution_week_start: {_json_sch.dumps(_caution_ws)}')
                lines.append('(best_week begins with "Week of <Month> <D>" from best_week_start; '
                              'caution_week begins with "Week of <Month> <D>" from caution_week_start. '
                              'Reason clause after the em-dash is your own phrasing.)')
    except Exception as _te_err:
        # Never block monthly generation on transit-event failure
        logger.warning(f'[monthly-day3] weekly schedule skipped: {_te_err}')

    lines.append(
        f"\nGenerate a complete monthly deep-dive for {month_str}. "
        "[cp-day1b] final instruction — if a COMPUTED JSON VALUES block is "
        "present above, the strong_planets and weak_planets fields MUST be "
        "exact copies of the arrays shown there.  Do not re-derive.  Do not "
        "substitute other planets.  [cp-day3] best_week and caution_week MUST "
        "reference a week_start date from the available_weeks list above — "
        "do not invent weeks that are not in the WEEKLY TRANSIT SCHEDULE. "
        "[cp-day4a] final instruction domains — priority_actions MUST contain "
        "exactly 3 entries whose domain fields equal priority_action_domains "
        "in that exact order.  Write one verb-first, chart-specific action "
        "per domain citing the transit events in that domain's houses."
    )

    return "\n".join(lines)


async def _call_claude(context: str, claude_client, language: str = "en") -> dict:
    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=_select_monthly_prompt(language),
            messages=[{"role": "user", "content": context}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"[monthly] Claude call failed: {e}")
        return _fallback_deepdive()


def _fallback_deepdive() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "month":       now.strftime("%B %Y"),
        "month_theme": "A month of consolidation and forward movement.",
        "energy_level":"moderate",
        "strong_planets": [],
        "weak_planets":   [],
        "overview":    "This month calls for focused action on your most important priorities. "
                       "Ask Antar a specific question for a precise reading.",
        "priority_actions": [
            {"domain": "career",  "action": "Identify your top professional priority and work on it daily."},
            {"domain": "wealth",  "action": "Review and reduce one unnecessary expense."},
            {"domain": "health",  "action": "Establish one consistent daily health practice."},
        ],
        "best_week":    "First week of the month — fresh energy",
        "caution_week": "Last week — avoid major decisions",
        "remedies": [
            {"planet": "general", "practice": "Morning sunlight for 10 minutes daily."},
        ],
        "monthly_mantra": "Steady progress beats urgent rushing.",
    }
