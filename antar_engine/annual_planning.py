"""
antar_engine/annual_planning.py
Sprint E — Annual Planning Session

Generated on user's birthday and January 1st.
The most comprehensive proactive output Antar produces:
  - Year lord analysis (what this year is fundamentally about)
  - Peak windows per domain (when to act in each area of life)
  - What to build, protect, and release this year
  - Remedies for the year specific to this chart
  - One-paragraph summary for sharing

Cached per chart per year. Available via GET /api/v1/annual-plan/{chart_id}
"""

import logging
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

# [cp-day4b] transit events import
from antar_engine.transit_events import compute_transit_events_in_range

# [output-strips] migrate annual_planning
from antar_engine.output_strips import apply_user_facing_strips

logger = logging.getLogger(__name__)

# [cp-day4b] annual transit helpers
# [cp-day5] annual remedy helpers
# [cp-day7] year_quality helper
_DASHA_TO_YEAR_QUALITY = {
    'Jupiter':  'expansion',
    'Saturn':   'consolidation',
    'Mars':     'building',
    'Sun':      'building',
    'Rahu':     'transformation',
    'Ketu':     'transformation',
    'Venus':    'harvest',
    'Moon':     'harvest',
    'Mercury':  'harvest',
}

def _pick_year_quality(current_dasha: str | None) -> str:
    """
    Map current dasha lord to one of the canonical year_quality enum
    values.  Returns 'building' as a neutral default when unknown.
    """
    if not isinstance(current_dasha, str) or not current_dasha.strip():
        return 'building'
    lord = current_dasha.strip().split()[0].split('/')[0].strip().capitalize()
    return _DASHA_TO_YEAR_QUALITY.get(lord, 'building')

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

def _pick_yearly_remedy_planets(current_dasha: str | None) -> list[str]:
    """
    Canonical classical pattern: current dasha lord + Saturn + Jupiter.
    De-dup if dasha lord is already Saturn/Jupiter; substitute Mars to
    keep the list at 3.
    """
    # Accept dasha strings like 'Mars', 'Mars MD', 'Mars / Mercury'.
    lord = ''
    if isinstance(current_dasha, str) and current_dasha.strip():
        lord = current_dasha.strip().split()[0].split('/')[0].strip()
    picks = []
    if lord and lord not in picks:
        picks.append(lord)
    for p in ('Saturn', 'Jupiter', 'Mars'):
        if len(picks) >= 3:
            break
        if p not in picks:
            picks.append(p)
    return picks[:3]

_HOUSE_TO_DOMAIN_ANNUAL = {
    1:  'health',        2:  'wealth',          3:  'career',
    4:  'home',          5:  'learning',        6:  'health',
    7:  'relationships', 8:  'health',          9:  'spiritual',
    10: 'career',        11: 'wealth',          12: 'foreign',
}
# Annual plan's canonical domains (schema-aligned)
_ANNUAL_DOMAINS = (
    'career', 'wealth', 'relationships', 'health', 'foreign', 'spiritual',
)
_EVENT_WEIGHT_ANNUAL = {
    'aspect':          3,
    'ingress':         2,
    'retro_start':     2,
    'retro_end':       2,
    'nakshatra_shift': 1,
}
_MONTH_NAMES = (
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
)

def _format_month_run(months_sorted: list) -> str:
    """
    Compress a sorted list of month indices (1-12) into a human range.
      [3,4,5,6,7]    → 'March–July'
      [3,7]          → 'March, July'
      [3,4,7,8]      → 'March–April, July–August'
      [3]            → 'March'
      []             → 'Throughout the year (steady focus)'
    """
    # [cp-day5] empty months fallback — give Claude a literal string to
    # copy rather than '' which it treats as a license to invent.
    if not months_sorted:
        return 'Throughout the year (steady focus)'
    runs = []
    start = months_sorted[0]
    prev  = start
    for m in months_sorted[1:]:
        if m == prev + 1:
            prev = m
            continue
        runs.append((start, prev))
        start = m; prev = m
    runs.append((start, prev))
    parts = []
    for s, e in runs:
        if s == e:
            parts.append(_MONTH_NAMES[s-1])
        else:
            parts.append(f'{_MONTH_NAMES[s-1]}–{_MONTH_NAMES[e-1]}')
    return ', '.join(parts)

def _aggregate_year_peak_windows(events: list) -> dict:
    """
    Returns {domain: {'months': 'March–July', 'active_months': [...],
                       'score': N, 'event_count': N}} for every
    canonical annual domain.  Domains with zero events still appear
    with months='' so downstream JSON keys are always present.
    """
    tally: dict = {d: {'months_score': {}, 'score': 0, 'event_count': 0}
                   for d in _ANNUAL_DOMAINS}
    for ev in (events or []):
        house = ev.get('natal_house')
        etype = ev.get('event_type')
        if not isinstance(house, int) or not 1 <= house <= 12:
            continue
        domain = _HOUSE_TO_DOMAIN_ANNUAL.get(house)
        if domain not in tally:
            continue
        try:
            mo = int(ev['date'].split('-')[1])
        except Exception:
            continue
        weight = _EVENT_WEIGHT_ANNUAL.get(etype, 1)
        slot = tally[domain]
        slot['months_score'][mo] = slot['months_score'].get(mo, 0) + weight
        slot['score']       += weight
        slot['event_count'] += 1
    out = {}
    for domain, slot in tally.items():
        active = sorted(slot['months_score'].keys())
        out[domain] = {
            'months':        _format_month_run(active),
            'active_months': active,
            'score':         slot['score'],
            'event_count':   slot['event_count'],
        }
    return out

def _compute_critical_dates(events: list, top_n: int = 4) -> list:
    """
    Pick the top N most-significant events of the year for the
    critical_dates field.  Scoring:
      ingress       : 3  (slow planet changes sign → major arc shift)
      retro_start   : 3
      retro_end     : 2
      aspect        : 4 - orb  (tighter orb = higher)
      nakshatra_shift: 0.5
    Returns a list of dicts ready for JSON: {date: 'April 2026',
    event_summary: str, raw_date: ISO, planet, type}.
    """
    scored = []
    for ev in (events or []):
        etype = ev.get('event_type')
        if etype == 'ingress':
            s = 3.0
        elif etype == 'retro_start':
            s = 3.0
        elif etype == 'retro_end':
            s = 2.0
        elif etype == 'aspect':
            orb = ev.get('orb') or 2.0
            s = max(0.5, 4.0 - float(orb))
        elif etype == 'nakshatra_shift':
            s = 0.5
        else:
            s = 0.0
        # De-prioritize inner-planet Moon events
        if ev.get('planet') == 'Moon':
            s *= 0.3
        scored.append((s, ev))
    scored.sort(key=lambda x: (-x[0], x[1].get('date','')))
    top = [ev for s, ev in scored[:top_n]]
    # Resort chronologically for user-facing output
    top.sort(key=lambda e: e.get('date',''))
    out = []
    for ev in top:
        iso = ev.get('date','')
        try:
            yr, mo = int(iso[:4]), int(iso[5:7])
            pretty = f'{_MONTH_NAMES[mo-1]} {yr}'
        except Exception:
            pretty = iso
        out.append({
            'date':          pretty,
            'event_summary': ev.get('detail',''),
            'raw_date':      iso,
            'planet':        ev.get('planet'),
            'event_type':    ev.get('event_type'),
        })
    return out

ANNUAL_TABLE = "annual_plans"

ANNUAL_SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation advisor.

Generate a full annual planning session. This is the most important reading Antar produces.
It covers the full year ahead — what it's about, when to act in each domain, what remedies to follow.

RULES:
- ALWAYS start year_summary with the user's first name if provided e.g. "Ramandeep, this year..."
- year_summary SHAPE (Narration Contract): the FIRST sentence must be a
  verdict — "[Name], this year is [favorable / under pressure / mixed /
  consolidating / expansive] for [the year's strong axis] — [terse
  imperative]." Examples of the SHAPE (do not copy the words):
    * "Ramandeep, this year is favorable for your career and your savings
      — ship the visible work, then protect the gains."
    * "Ramandeep, this year is under pressure around your daily routine
      and your partnerships — protect health first, postpone big bets."
    * "Ramandeep, this year is mixed — your career is the strong axis,
      your home and family ask for care."
  FORBIDDEN year_summary openings (these are abstract frames, not
  answers — the contract bans them):
    * "this year is about [X]" / "is about refining" / "is about
      protecting" — a frame, not a verdict.
    * Any sentence whose first concrete noun is an abstraction
      (vitality, systems, foundations, infrastructure, energy, momentum,
      alignment, growth, consolidation as a bare word).
- year_summary BODY (sentences 2-4): name 2-3 CONCRETE life-nouns
  drawn from the peak_windows the engine just chose. Use plain life
  terms — "your career", "your savings", "a property or vehicle
  decision", "your father or a mentor", "a long-distance move", "your
  daily routine", "your partner", "your work standing". NEVER write the bare
  category alone ("focus on health", "relationships matter").
- year_summary WINDOW: end the summary with a concrete multi-month
  window using the peak months — e.g. "Ship through May–June,
  consolidate Q4", "Move on the property question in late summer",
  "Hold off on big partnership moves until November".
- year_theme: ONE plain, everyday sentence, under 12 words — the year's core
  tension or opportunity, said the way a person would say it. NEVER use the word
  "energy". NEVER string two descriptive phrases together with a hyphen (e.g.
  "your discipline and structure energy-your ambition and breakthrough energy").
  NEVER lead with an abstraction. Good: "A year to build the foundation before
  you expand." / "Steady progress if you protect your health first." Bad: any
  sentence containing "energy" or a phrase-hyphen-phrase construction.
- Plain English throughout. Zero jargon.
- Specific timing windows: name months, not vague periods
- [cp-day4b] peak_windows + critical_dates rule — if the user context
  below contains COMPUTED JSON VALUES with 'peak_windows_months' and
  'critical_dates_dates', the following JSON fields MUST be filled
  verbatim from those computed values:
    * peak_windows.<domain>.months  copies peak_windows_months[<domain>]
    * critical_dates[i].date        copies critical_dates_dates[i]
  Do not invent months outside the computed ranges.  Do not invent
  critical dates not in the provided list.  The narrative fields
  (peak_windows.<domain>.signal, critical_dates[i].event) can be
  your own phrasing but must be grounded in the transit events
  listed in the YEAR TRANSIT SUMMARY block.
- [cp-day5] yearly_remedies rule — if the context contains a
  'yearly_remedies_list' in COMPUTED JSON VALUES, the yearly_remedies
  array in your response MUST be a character-for-character copy of
  that list — same length, same planets in the same order, same
  practice text verbatim.  Do not substitute planets.  Do not rewrite
  practice text.  These values are canonical classical mantras —
  paraphrasing them loses meaning.
- [cp-day7] year_quality rule — if the context contains a
  'year_quality MUST be:' computed enum value, the year_quality
  field in your response MUST equal that string verbatim.
- Peak windows per domain: at least 4 domains covered
- Be specific to the chart data — actual planetary periods and positions
- ALWAYS address the user by first name in year_summary e.g. 'Ramandeep, this year...'
- The year summary should feel like a wise advisor's view of the year ahead
- Remedies: practical, tied to specific chart placements, maintainable year-round

Return ONLY this JSON:
{
  "year":          2026,
  "year_theme":    "One PLAIN everyday sentence, under 12 words. No 'energy', no phrase-hyphen-phrase. See the year_theme rule above.",
  "year_quality":  "expansion OR consolidation OR transformation OR harvest OR building",
  "year_summary":  "3-4 sentences. The arc of the year. What will grow, what will shift, what will resolve.",
  "peak_windows": {
    "career":       {"months": "March–August", "signal": "One sentence what career energy does this period."},
    "wealth":       {"months": "August–December", "signal": "One sentence."},
    "relationships":{"months": "April–June", "signal": "One sentence."},
    "health":       {"months": "January–March", "signal": "One sentence about health focus."},
    "foreign":      {"months": "September–November", "signal": "One sentence."},
    "spiritual":    {"months": "November–January", "signal": "One sentence."}
  },
  "build_this_year":    ["thing1", "thing2", "thing3"],
  "protect_this_year":  ["thing1", "thing2"],
  "release_this_year":  ["thing1", "thing2"],
  "yearly_remedies": [
    {"planet": "Saturn", "practice": "Year-long remedy. Specific and practical."},
    {"planet": "Jupiter", "practice": "Year-long remedy. Specific and practical."},
    {"planet": "current_dasha_lord", "practice": "Remedy for the current planetary period lord."}
  ],
  "year_mantra":   "One plain English affirmation for the year. Under 10 words.",
  "critical_dates": [
    {"date": "August 2026", "event": "What happens astrologically and what it means."},
    {"date": "November 2026", "event": "What changes and how to navigate it."}
  ]
}"""


ANNUAL_SYSTEM_PROMPT_ES = """Eres Antar — un guía de navegación de vida preciso y cálido.

Genera una sesión de planificación anual completa. Esta es la lectura más importante que produce Antar.
Cubre todo el año que viene — de qué trata, cuándo actuar en cada dominio, qué remedios seguir.

REGLAS:
- SIEMPRE comienza year_summary con el nombre del usuario si está disponible, p. ej. "Ramandeep, este año..."
- Español claro en todo momento. Cero jerga.
- Ventanas de tiempo concretas: nombra meses, no periodos vagos
- [cp-day4b] regla peak_windows + critical_dates — si el contexto del usuario
  contiene COMPUTED JSON VALUES con 'peak_windows_months' y
  'critical_dates_dates', los siguientes campos JSON DEBEN rellenarse
  de forma literal a partir de esos valores calculados:
    * peak_windows.<domain>.months  copia peak_windows_months[<domain>]
    * critical_dates[i].date        copia critical_dates_dates[i]
  No inventes meses fuera de los rangos calculados.  No inventes fechas
  críticas que no estén en la lista proporcionada.  Los campos narrativos
  (peak_windows.<domain>.signal, critical_dates[i].event) pueden ser tu
  propia redacción pero deben fundamentarse en los eventos de tránsito
  listados en el bloque YEAR TRANSIT SUMMARY.
- [cp-day5] regla yearly_remedies — si el contexto contiene una
  'yearly_remedies_list' en COMPUTED JSON VALUES, el array yearly_remedies
  de tu respuesta DEBE ser una copia carácter por carácter de esa lista —
  misma longitud, mismos planetas en el mismo orden, mismo texto de practice
  literal.  No sustituyas planetas.  No reescribas el texto de practice.
  Estos valores son mantras clásicos canónicos — parafrasearlos pierde su
  significado.
- [cp-day7] regla year_quality — si el contexto contiene un valor enum
  calculado 'year_quality MUST be:', el campo year_quality de tu respuesta
  DEBE ser igual a esa cadena de forma literal.
- Ventanas pico por dominio: al menos 4 dominios cubiertos
- Sé específico con los datos de la carta — periodos y posiciones planetarias reales
- SIEMPRE dirígete al usuario por su nombre en year_summary, p. ej. 'Ramandeep, este año...'
- El resumen del año debe sentirse como la visión de un asesor sabio sobre el año que viene
- Remedios: prácticos, ligados a posiciones concretas de la carta, mantenibles todo el año

Todo el texto narrativo va en ESPAÑOL. Las claves JSON, los valores enum
(year_quality), los identificadores de dominio en peak_windows, los nombres de
planetas y los valores months/date copiados de COMPUTED JSON VALUES se mantienen
en inglés.

Devuelve SOLO este JSON:
{
  "year":          2026,
  "year_theme":    "Una frase — de qué trata fundamentalmente este año. Menos de 12 palabras.",
  "year_quality":  "expansion OR consolidation OR transformation OR harvest OR building",
  "year_summary":  "3-4 frases. El arco del año. Qué crecerá, qué cambiará, qué se resolverá.",
  "peak_windows": {
    "career":       {"months": "March–August", "signal": "Una frase sobre qué hace la energía profesional en este periodo."},
    "wealth":       {"months": "August–December", "signal": "Una frase."},
    "relationships":{"months": "April–June", "signal": "Una frase."},
    "health":       {"months": "January–March", "signal": "Una frase sobre el enfoque de salud."},
    "foreign":      {"months": "September–November", "signal": "Una frase."},
    "spiritual":    {"months": "November–January", "signal": "Una frase."}
  },
  "build_this_year":    ["cosa1", "cosa2", "cosa3"],
  "protect_this_year":  ["cosa1", "cosa2"],
  "release_this_year":  ["cosa1", "cosa2"],
  "yearly_remedies": [
    {"planet": "Saturn", "practice": "Remedio para todo el año. Concreto y práctico."},
    {"planet": "Jupiter", "practice": "Remedio para todo el año. Concreto y práctico."},
    {"planet": "current_dasha_lord", "practice": "Remedio para el regente del periodo planetario actual."}
  ],
  "year_mantra":   "Una afirmación en español claro para el año. Menos de 10 palabras.",
  "critical_dates": [
    {"date": "August 2026", "event": "Qué ocurre astrológicamente y qué significa."},
    {"date": "November 2026", "event": "Qué cambia y cómo navegarlo."}
  ]
}"""


ANNUAL_SYSTEM_PROMPT_PT = """Você é Antar — um guia de navegação de vida preciso e acolhedor.

Gere uma sessão completa de planejamento anual. Esta é a leitura mais importante que Antar produz.
Ela cobre todo o ano que vem — do que se trata, quando agir em cada domínio, quais remédios seguir.

REGRAS:
- SEMPRE comece year_summary com o primeiro nome do usuário, se disponível, ex.: "Ramandeep, este ano..."
- Português claro o tempo todo. Zero jargão.
- Janelas de tempo concretas: indique meses, não períodos vagos
- [cp-day4b] regra peak_windows + critical_dates — se o contexto do usuário
  contiver COMPUTED JSON VALUES com 'peak_windows_months' e
  'critical_dates_dates', os seguintes campos JSON DEVEM ser preenchidos
  de forma literal a partir desses valores calculados:
    * peak_windows.<domain>.months  copia peak_windows_months[<domain>]
    * critical_dates[i].date        copia critical_dates_dates[i]
  Não invente meses fora dos intervalos calculados.  Não invente datas
  críticas que não estejam na lista fornecida.  Os campos narrativos
  (peak_windows.<domain>.signal, critical_dates[i].event) podem ser sua
  própria redação, mas devem se fundamentar nos eventos de trânsito
  listados no bloco YEAR TRANSIT SUMMARY.
- [cp-day5] regra yearly_remedies — se o contexto contiver uma
  'yearly_remedies_list' em COMPUTED JSON VALUES, o array yearly_remedies
  da sua resposta DEVE ser uma cópia caractere por caractere dessa lista —
  mesmo comprimento, mesmos planetas na mesma ordem, mesmo texto de practice
  literal.  Não substitua planetas.  Não reescreva o texto de practice.
  Esses valores são mantras clássicos canônicos — parafraseá-los perde o
  significado.
- [cp-day7] regra year_quality — se o contexto contiver um valor enum
  calculado 'year_quality MUST be:', o campo year_quality da sua resposta
  DEVE ser igual a essa string de forma literal.
- Janelas de pico por domínio: ao menos 4 domínios cobertos
- Seja específico com os dados do mapa — períodos e posições planetárias reais
- SEMPRE trate o usuário pelo primeiro nome em year_summary, ex.: 'Ramandeep, este ano...'
- O resumo do ano deve soar como a visão de um conselheiro sábio sobre o ano que vem
- Remédios: práticos, ligados a posições concretas do mapa, sustentáveis o ano todo

Todo o texto narrativo vai em PORTUGUÊS. As chaves JSON, os valores enum
(year_quality), os identificadores de domínio em peak_windows, os nomes de
planetas e os valores months/date copiados de COMPUTED JSON VALUES permanecem
em inglês.

Retorne APENAS este JSON:
{
  "year":          2026,
  "year_theme":    "Uma frase — do que este ano se trata fundamentalmente. Menos de 12 palavras.",
  "year_quality":  "expansion OR consolidation OR transformation OR harvest OR building",
  "year_summary":  "3-4 frases. O arco do ano. O que vai crescer, o que vai mudar, o que vai se resolver.",
  "peak_windows": {
    "career":       {"months": "March–August", "signal": "Uma frase sobre o que a energia profissional faz neste período."},
    "wealth":       {"months": "August–December", "signal": "Uma frase."},
    "relationships":{"months": "April–June", "signal": "Uma frase."},
    "health":       {"months": "January–March", "signal": "Uma frase sobre o foco de saúde."},
    "foreign":      {"months": "September–November", "signal": "Uma frase."},
    "spiritual":    {"months": "November–January", "signal": "Uma frase."}
  },
  "build_this_year":    ["coisa1", "coisa2", "coisa3"],
  "protect_this_year":  ["coisa1", "coisa2"],
  "release_this_year":  ["coisa1", "coisa2"],
  "yearly_remedies": [
    {"planet": "Saturn", "practice": "Remédio para o ano todo. Concreto e prático."},
    {"planet": "Jupiter", "practice": "Remédio para o ano todo. Concreto e prático."},
    {"planet": "current_dasha_lord", "practice": "Remédio para o regente do período planetário atual."}
  ],
  "year_mantra":   "Uma afirmação em português claro para o ano. Menos de 10 palavras.",
  "critical_dates": [
    {"date": "August 2026", "event": "O que acontece astrologicamente e o que significa."},
    {"date": "November 2026", "event": "O que muda e como navegar isso."}
  ]
}"""


def _select_annual_prompt(language: str) -> str:
    """[loc-2] Pick the annual-plan system prompt for the user's language.
    [loc-3 2026-07-04] Non-EN prompts carry the hard LANGUAGE INSTRUCTION
    block as reinforcement (EN fragments were leaking into PT output);
    FR composes natively on the EN base + FR block."""
    lang = (language or "en").lower()[:2]
    base = {
        "es": ANNUAL_SYSTEM_PROMPT_ES,
        "pt": ANNUAL_SYSTEM_PROMPT_PT,
    }.get(lang, ANNUAL_SYSTEM_PROMPT)
    if lang in ("es", "pt", "fr"):
        try:
            from language_utils import build_language_instruction
            return build_language_instruction(lang) + base
        except Exception:
            pass
    return base


def _safe_jsonb_annual(v):
    """[loc-2] Parse a JSONB column that may arrive as a JSON string."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _is_legacy_annual_blob(blob) -> bool:
    """[loc-2] True if `blob` is a pre-loc-2 single-language annual-plan payload."""
    return isinstance(blob, dict) and ("year_summary" in blob or "peak_windows" in blob)


def _life_constraint_block(life: Optional[dict]) -> str:
    """A prompt block that forbids claims the reader's KNOWN circumstances
    contradict — the intelligence layer's core promise: never tell a business
    owner about 'your boss', never tell someone with no children about 'your
    child', never tell a single person about 'your spouse'. Empty when nothing
    is known (unknown must steer wording, never fabricate a fact)."""
    if not life:
        return ""
    lines = []
    emp = life.get("employed")
    if emp is False:
        lines.append('- The reader is SELF-EMPLOYED / a business owner — NEVER write '
                     '"your boss", "jefe", "your manager", or "your employer". Use '
                     '"your reputation", "your work standing", "an authority figure", '
                     'or "your business" for career/10th-house themes.')
    elif emp is None:
        lines.append('- The reader is NOT known to be an employee — do NOT assume a '
                     'boss/employer. Use "your reputation" / "your work standing" / '
                     '"an authority figure" for career and authority themes.')
    if life.get("has_children") is False:
        lines.append('- The reader has NO children — NEVER reference "your child", '
                     '"your children", or any child-related event as a present fact.')
    if life.get("partnered") is False:
        lines.append('- The reader is NOT currently partnered — NEVER reference "your '
                     'spouse", "your partner", or "your marriage" as a present '
                     'relationship (5th/7th-house themes: use "a partnership", '
                     '"a close collaborator", or a future-framed possibility).')
    if not lines:
        return ""
    return ("\n\nKNOWN LIFE FACTS — confirmed about this reader; NEVER write anything "
            "that contradicts them (this is what makes the reading feel truly known):\n"
            + "\n".join(lines))


async def generate_annual_plan(
    chart_id:       str,
    chart_data:     dict,
    dashas:         dict,
    first_name:     Optional[str],
    lagna:          Optional[str],
    moon_sign:      Optional[str],
    current_dasha:  Optional[str],
    birth_date:     Optional[str],
    age:            Optional[int],
    country_code:   Optional[str],
    dkp_context:    Optional[str],
    lk_context:     Optional[str],
    supabase,
    claude_client,
    force_refresh:  bool = False,
    language:       str = "en",
    dasha_levels:   Optional[dict] = None,
) -> dict:
    """
    Generate or return cached annual plan.
    Regenerates on birthday, January 1st, or if force_refresh=True.
    """
    # [loc-2] normalize locale (es-CO -> es); en/es/pt only
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"
    now      = datetime.now(timezone.utc)
    year_key = str(now.year)

    # Check cache
    if not force_refresh:
        cached = _read_cache(chart_id, year_key, supabase, language)
        if cached:
            return cached

    # Build context
    context = _build_annual_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, birth_date,
        age, country_code, dkp_context, lk_context, now,
        dasha_levels=dasha_levels,
    )

    # [life-gate] Fetch the reader's KNOWN facts and forbid contradicting them
    # (no "your boss" for a business owner, no "your child" for the childless).
    # Fail-open: any read problem just means no extra constraint, never a crash.
    try:
        from antar_engine.life_context import resolve_life_facts as _rlf
        _lrow = (supabase.table("charts").select(
            "career_stage,profession,life_work,marital_status,children_status")
            .eq("id", chart_id).single().execute().data or {})
        _lblock = _life_constraint_block(_rlf(_lrow))
        if _lblock:
            context = context + _lblock
    except Exception as _lge:
        logger.debug("[annual] life-gate skipped (non-fatal): %s", _lge)

    # [kal] era grounding — modern-day framing when the chart supports it. Kept
    # to the annual surface first so the tone can be reviewed before it reaches
    # the high-frequency daily card.
    try:
        from antar_engine.desh_kal_patra import ERA_CONTEXT_NOTE
        context = context + ERA_CONTEXT_NOTE
    except Exception:
        pass

    # Call Claude — wrapped so a hard failure falls back to the previous
    # cached row (if any) rather than shipping an empty critical_dates.
    try:
        result = await _call_claude(context, claude_client, language)
    except Exception as _claude_err:
        logger.error(f"[annual] generation raised; trying cached: {_claude_err}")
        cached_any = _read_cache(chart_id, year_key, supabase, language)
        if cached_any and (cached_any.get("critical_dates") or []):
            logger.info("[annual] serving previous cached year — generation failed.")
            return cached_any
        raise
    # [lk-real-fix1 2026-06-08] Removed the post-narration cache
    # backfill. If the real generator produces 0 events, the response
    # ships 0 events — never silently restored from a prior cache.
    # (The exception-path cache fallback above stays: a RAISED
    # generation still falls back to last-good rather than 500-ing.)
    result["chart_id"] = chart_id
    result["year_key"] = year_key

    # [theme-guard] never ship a clumsy year_theme. The theme must be plain —
    # if the model leaked "energy" (its jargon tell) or a phrase-hyphen-phrase
    # join, replace it with a clean quality-based line. Runs BEFORE name
    # injection so the first name still attaches to the clean theme.
    _yt = result.get("year_theme") or ""
    if _yt and ("energy" in _yt.lower() or re.search(r"\w-\w+\s+\w+\s+\w", _yt)):
        _QUALITY_THEME = {
            "consolidation": "A year to consolidate and strengthen what you've built.",
            "expansion":     "A year of expansion — grow, but choose where.",
            "transformation":"A year of deep change — let the old restructure before the new.",
            "harvest":       "A harvest year — reap what you've built, then rest into it.",
            "building":      "A building year — lay the foundation before you expand.",
        }
        _q = str(result.get("year_quality") or "building").lower()
        result["year_theme"] = _QUALITY_THEME.get(
            _q, "A year to build steadily and choose your moves with care.")

    # Inject the FIRST name only (never the full name), and skip injection when
    # the text already opens with it — case-insensitively — so we never produce
    # "Gerardo Murillo, gerardo, this year…" (double name) when first_name holds
    # a full name or the model already led with the first name.
    _fn = ((first_name or "").strip().split() or [""])[0]
    if _fn and result.get("year_summary"):
        ys = result["year_summary"]
        if not ys.lower().lstrip().startswith(_fn.lower()):
            result["year_summary"] = f"{_fn}, {ys[0].lower()}{ys[1:]}"
    if _fn and result.get("year_theme"):
        yt = result["year_theme"]
        if not yt.lower().lstrip().startswith(_fn.lower()):
            result["year_theme"] = f"{_fn}: {yt}"

    # [output-strips] strip annual_plan
    # Route every user-facing narrative field through the central
    # output-strip layer BEFORE cache upsert so cached rows stay
    # clean.  Hard-coded 'en' — matches current prompt behavior.
    #
    # Plain fields (full strip):
    #   year_theme, year_summary, year_mantra,
    #   peak_windows[<domain>].signal,
    #   build_this_year[], protect_this_year[], release_this_year[],
    #   yearly_remedies[].practice,
    #   critical_dates[].event
    # Skipped (ints / enums / dates / proper nouns / metadata):
    #   year, year_quality,
    #   peak_windows[<domain>].months,
    #   yearly_remedies[].planet,
    #   critical_dates[].date,
    #   chart_id, year_key
    _lang = language  # [loc-2] was hard-coded 'en'

    # Scalar plain fields
    for _f in ('year_theme', 'year_summary', 'year_mantra'):
        _v = result.get(_f)
        if isinstance(_v, str) and _v:
            _v = apply_user_facing_strips(_v, language=_lang, field_type='plain')
            # [energy-strip] "your growth and wisdom energy('s)" is clumsy jargon-
            # tell — drop the trailing "energy" so it reads "your growth and
            # wisdom". Targets only the "your <words> energy" construction.
            _v = re.sub(r"(\byour [\w' ]+?)\s+energy('s)?\b", r"\1", _v, flags=re.I)
            _v = re.sub(r"\s{2,}", " ", _v).strip()
            result[_f] = _v

    # [energy-strip] "your/natal X energy" -> "your/natal X" across every annual
    # prose field (critical_dates especially read "your action and drive energy
    # opposes your natal growth and wisdom energy" — clumsy).
    def _de_energy(v):
        if not isinstance(v, str) or not v:
            return v
        v = re.sub(r"(\byour [\w' ]+?)\s+energy('s)?\b", r"\1", v, flags=re.I)
        v = re.sub(r"(\bnatal )([\w' ]+?)\s+energy\b", r"\1\2", v, flags=re.I)
        v = re.sub(r"\benergy\b", "", v)  # any stragglers
        return re.sub(r"\s{2,}", " ", v).strip()

    # peak_windows[<domain>].signal — plain per domain
    _pw = result.get('peak_windows')
    if isinstance(_pw, dict):
        for _domain, _win in list(_pw.items()):
            if isinstance(_win, dict):
                _sig = _win.get('signal')
                if isinstance(_sig, str) and _sig:
                    _win['signal'] = _de_energy(apply_user_facing_strips(
                        _sig, language=_lang, field_type='plain'))

    # build / protect / release string arrays — each item is plain
    for _arr_key in ('build_this_year', 'protect_this_year', 'release_this_year'):
        _arr = result.get(_arr_key)
        if isinstance(_arr, list):
            result[_arr_key] = [
                _de_energy(apply_user_facing_strips(_x, language=_lang, field_type='plain'))
                if isinstance(_x, str) and _x else _x
                for _x in _arr
            ]

    # yearly_remedies[].practice — planet field left untouched
    _rems = result.get('yearly_remedies')
    if isinstance(_rems, list):
        for _r in _rems:
            if isinstance(_r, dict):
                _pr = _r.get('practice')
                if isinstance(_pr, str) and _pr:
                    _r['practice'] = apply_user_facing_strips(
                        _pr, language=_lang, field_type='timing'
                    )

    # critical_dates[].event — date field left untouched
    _crit = result.get('critical_dates')
    if isinstance(_crit, list):
        for _c in _crit:
            if isinstance(_c, dict):
                _ev = _c.get('event')
                if isinstance(_ev, str) and _ev:
                    _c['event'] = _de_energy(apply_user_facing_strips(
                        _ev, language=_lang, field_type='plain'
                    ))

    # Save to cache — [loc-2] language-keyed. The `plan` JSONB column holds
    # {"en": {...}, "es": {...}, "pt": {...}} so a single-language write keeps
    # the others. Mirrors daily_wow_cache. Legacy single-blob rows are discarded
    # (the read path already treated them as a MISS).
    try:
        _blob = {}
        try:
            _ex = supabase.table(ANNUAL_TABLE) \
                .select("plan") \
                .eq("chart_id", chart_id) \
                .eq("year_key", year_key) \
                .execute()
            if _ex.data:
                _eb = _safe_jsonb_annual(_ex.data[0].get("plan"))
                if isinstance(_eb, dict) and not _is_legacy_annual_blob(_eb):
                    _blob = _eb
        except Exception as _pre:
            logger.warning(f"[annual] Cache pre-read failed (will overwrite): {_pre}")
        _blob[_lang] = result
        supabase.table(ANNUAL_TABLE).upsert({
            "chart_id":  chart_id,
            "year_key":  year_key,
            "plan":      _blob,
            "created_at": now.isoformat(),
        }, on_conflict="chart_id,year_key").execute()
        logger.info(f"[annual] Plan saved for {chart_id[:8]} {year_key} lang={_lang} (langs={list(_blob.keys())})")
    except Exception as e:
        logger.warning(f"[annual] Cache save failed: {e}")

    return result


def _read_cache(chart_id: str, year_key: str, supabase, language: str = "en") -> Optional[dict]:
    # [loc-2] language-keyed read. `plan` is {"en": {...}, "es": {...}, ...}.
    # A legacy single-blob row is treated as a MISS so the next write migrates it.
    try:
        result = supabase.table(ANNUAL_TABLE) \
            .select("plan") \
            .eq("chart_id", chart_id) \
            .eq("year_key", year_key) \
            .execute()
        if result.data:
            blob = _safe_jsonb_annual(result.data[0].get("plan"))
            if isinstance(blob, dict) and not _is_legacy_annual_blob(blob):
                entry = blob.get(language)
                if isinstance(entry, dict) and entry:
                    return entry
    except Exception as e:
        logger.warning(f"[annual] Cache read failed: {e}")
    return None


def _build_annual_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    birth_date:    Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    dkp_context:   Optional[str],
    lk_context:    Optional[str],
    now:           datetime,
    dasha_levels:  Optional[dict] = None,
) -> str:
    year = now.year
    planets = chart_data.get("planets", {})

    # Get upcoming dasha transitions
    # [upcoming-fix 2026-07-22] This took vim[:4] — the FIRST four periods in
    # the list, not the next four. A chart born in 1974 was telling the model
    # "Mercury period ends: 1976-08-13" under a heading that says UPCOMING, and
    # every annual plan has been written against transitions that happened
    # decades ago. Filter to periods that end in the FUTURE, nearest first.
    dasha_transitions = []
    _today_iso = now.strftime("%Y-%m-%d")
    vim = dashas.get("vimsottari", []) or []
    _future = []
    for p in vim:
        lord = p.get("lord_or_sign") or p.get("planet_or_sign", "")
        end  = str(p.get("end_date") or p.get("end", ""))[:10]
        if lord and end and end >= _today_iso:
            _future.append((end, lord))
    for end, lord in sorted(_future)[:4]:
        dasha_transitions.append(f"{lord} period ends: {end}")
    if not dasha_transitions:
        dasha_transitions.append("(no upcoming transition on record)")

    # Key planet positions
    saturn_sign  = planets.get("Saturn",  {}).get("sign", "")
    jupiter_sign = planets.get("Jupiter", {}).get("sign", "")
    rahu_sign    = planets.get("Rahu",    {}).get("sign", "")

    # [yearly-levels 2026-07-22] The running sub-periods. The mahadasha says
    # what the decade is about; the ANTARDASHA and PRATYANTARDASHA say what
    # happens inside THIS year, and the chara dasha sign says which area of
    # life the year is being lived from. None of this reached the prompt
    # before — the whole annual reading was written from the mahadasha NAME.
    lvl = dasha_levels or {}
    def _lp(key):
        d = lvl.get(key) or {}
        p = d.get("planet_or_sign")
        e = str(d.get("end_date") or "")[:10]
        return f"{p} (until {e})" if p and e else (p or None)

    period_lines = []
    for key, label in (("vimsottari_1", "Mahadasha"),
                       ("vimsottari_2", "Antardasha"),
                       ("vimsottari_3", "Pratyantardasha"),
                       ("jaimini_1", "Chara dasha sign"),
                       ("jaimini_2", "Chara antardasha")):
        v = _lp(key)
        if v:
            period_lines.append(f"{label}: {v}")

    lines = [
        f"ANNUAL PLAN REQUEST — Year {year}",
        f"Name: {first_name or 'not provided'}",
        f"Rising sign: {lagna or 'unknown'}",
        f"Moon sign: {moon_sign or 'unknown'}",
        f"Current planetary period: {current_dasha or 'unknown'}",
        f"Age this year: {age or 'unknown'}",
        f"Birth date: {birth_date or 'unknown'}",
        f"Country: {country_code or 'unknown'}",
        "",
        "KEY PLANETARY POSITIONS:",
        f"Saturn in: {saturn_sign or 'unknown'}",
        f"Jupiter in: {jupiter_sign or 'unknown'}",
        f"Rahu in: {rahu_sign or 'unknown'}",
        "",
        "RUNNING PERIODS — the year is lived inside these:",
    ] + (period_lines or ["(sub-periods unavailable)"]) + [
        "",
        "UPCOMING DASHA TRANSITIONS:",
    ] + dasha_transitions

    if dkp_context:
        dkp_lines = [l for l in dkp_context.split("\n") if l.strip()][:3]
        lines.append("\nECONOMIC CONTEXT:")
        lines.extend(dkp_lines)

    if lk_context:
        lk_lines = lk_context.split("\n")[:3]
        lines.append("\nLAL KITAB ANNUAL CONTEXT:")
        lines.extend(lk_lines)

    # [cp-day4b] annual transit context injection
    # Compute 12 months of slow-planet transit events, aggregate by
    # natal-house-based domain → months, and surface top critical dates.
    try:
        from datetime import date as _date
        _y_start = _date(year, 1, 1)
        _y_end   = _date(year, 12, 31)
        _year_events = compute_transit_events_in_range(
            chart_data, _y_start, _y_end, include_fast=False,
        )
        _peak   = _aggregate_year_peak_windows(_year_events)
        _crit   = _compute_critical_dates(_year_events, top_n=4)
        # Server log — use print so Railway's log-level filter won't hide it
        _log_peaks = {d: _peak[d]["months"] for d in _peak}
        _log_crits = [c["date"] for c in _crit]
        print(
            f'[annual-day4b] events={len(_year_events)} '
            f'peak_months={_log_peaks} '
            f'critical_dates={_log_crits}'
        )

        lines.append('')
        lines.append('YEAR TRANSIT SUMMARY — per-domain activity (from Swiss Ephemeris):')
        for _d in _ANNUAL_DOMAINS:
            _entry = _peak.get(_d, {})
            _months = _entry.get('months', '')
            _score  = _entry.get('score', 0)
            _count  = _entry.get('event_count', 0)
            if _months:
                lines.append(
                    f'  {_d}: {_months} — {_count} events, score {_score}'
                )
            else:
                lines.append(f'  {_d}: (no concentrated transit activity this year)')

        lines.append('')
        lines.append('TOP CRITICAL DATES THIS YEAR (slow-planet ingresses + tight aspects):')
        for _c in _crit:
            lines.append(
                f'  {_c["date"]} — {_c.get("event_summary","")} '
                f'(raw: {_c.get("raw_date")})'
            )

        # Machine-readable block Claude must copy verbatim
        import json as _json_ann
        _pw_map = {d: _peak[d]['months'] for d in _ANNUAL_DOMAINS}
        _cd_list = [c['date'] for c in _crit]
        lines.append('')
        lines.append('COMPUTED JSON VALUES — peak_windows and critical_dates MUST use these:')
        lines.append(f'  peak_windows_months:   {_json_ann.dumps(_pw_map)}')
        lines.append(f'  critical_dates_dates:  {_json_ann.dumps(_cd_list)}')
        lines.append(
            '(Each peak_windows.<domain>.months MUST equal peak_windows_months[<domain>] '
            'verbatim. Each critical_dates[i].date MUST equal critical_dates_dates[i] '
            'verbatim. Narrative signal/event fields can be your own phrasing.)'
        )

        # [cp-day5] annual yearly_remedies injection
        _remedy_planets = _pick_yearly_remedy_planets(current_dasha)
        _remedy_list = [
            {'planet': _p, 'practice': _canonical_practice(_p)}
            for _p in _remedy_planets
        ]
        print(f'[annual-day5] yearly_remedies={_remedy_planets}')
        lines.append('')
        lines.append('CANONICAL YEARLY REMEDIES — from classical planetary mantras:')
        for _r in _remedy_list:
            lines.append(f'  {_r["planet"]}: {_r["practice"]}')
        lines.append('')
        lines.append('COMPUTED JSON VALUES — yearly_remedies array MUST be exactly this list:')
        lines.append(f'  yearly_remedies_list: {_json_ann.dumps(_remedy_list)}')
        lines.append('(Each entry {planet, practice} must be a character-for-character copy.)')

        # [cp-day7] year_quality injection — deterministic from dasha lord
        _year_quality = _pick_year_quality(current_dasha)
        print(f'[annual-day7] year_quality={_year_quality!r} (from dasha={current_dasha!r})')
        lines.append('')
        lines.append(f'COMPUTED JSON VALUES — year_quality MUST be: {_json_ann.dumps(_year_quality)}')
        lines.append('(Copy this enum value into the year_quality field verbatim.)')
    except Exception as _ann_err:
        # Never block the annual plan on transit computation failure
        logger.warning(f'[annual-day4b] transit context skipped: {_ann_err}')

    lines.append(
        f"\nGenerate a complete annual plan for {year}. "
        "Identify the year's dominant theme from the current dasha and transits. "
        "[cp-day4b] peak_windows.<domain>.months MUST match peak_windows_months "
        "from COMPUTED JSON VALUES above, verbatim.  critical_dates[i].date MUST "
        "match critical_dates_dates[i] verbatim in the same order.  Do not invent "
        "months or dates outside these lists.  Narrative fields (signal, event, "
        "remedies) can be your own phrasing but must cite the YEAR TRANSIT SUMMARY. "
        "Give year-long remedies that are practical and maintainable."
    )

    return "\n".join(str(l) for l in lines)


async def _call_claude(context: str, claude_client, language: str = "en",
                       _attempt: int = 1) -> dict:
    """[yv2-canonical 2026-06-08] Retry once on failure; raise on
    second failure instead of silently returning _fallback_annual()
    (which carries critical_dates=[]). The endpoint now sees a real
    exception and the caller can keep the previous cache rather than
    shipping an empty year."""
    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            system=_select_annual_prompt(language),
            messages=[{"role": "user", "content": context}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)
        parsed = json.loads(text.strip())
        # Fallback-shape sentinel: if the model returned the safety
        # filler shape (empty critical_dates + year_quality 'building'
        # + the canned theme phrase) treat as a soft failure and retry.
        if (_attempt == 1
                and isinstance(parsed, dict)
                and not parsed.get("critical_dates")
                and isinstance(parsed.get("year_theme"), str)
                and parsed["year_theme"].startswith(
                    "A year of building towards your next major life chapter")):
            logger.warning("[annual] Claude returned the fallback shape — retrying once.")
            import asyncio as _ann_asyncio
            await _ann_asyncio.sleep(0.6)
            return await _call_claude(context, claude_client, language, _attempt=2)
        return parsed
    except Exception as e:
        if _attempt == 1:
            logger.warning(f"[annual] Claude call failed (will retry once): {e}")
            import asyncio as _ann_asyncio
            await _ann_asyncio.sleep(0.6)
            return await _call_claude(context, claude_client, language, _attempt=2)
        logger.error(f"[annual] Claude call failed twice; raising: {e}")
        # Raise so generate_annual_plan can decide what to do — never
        # silently substitute the empty fallback for a real year.
        raise


def _fallback_annual() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "year":         now.year,
        "year_theme":   "A year of building towards your next major life chapter.",
        "year_quality": "building",
        "year_summary": "This year asks you to lay foundations for what comes next. "
                        "Focus on the areas where consistent effort compounds over time. "
                        "Ask Antar specific questions to get precise timing for each domain.",
        "peak_windows": {
            "career":       {"months": "Q2-Q3", "signal": "Career momentum builds mid-year."},
            "wealth":       {"months": "Q3-Q4", "signal": "Financial consolidation in second half."},
            "relationships":{"months": "Q1-Q2", "signal": "Relationship clarity early in the year."},
            "health":       {"months": "All year", "signal": "Consistent practices matter most."},
        },
        "build_this_year":   ["Professional expertise", "Financial reserves", "Key relationships"],
        "protect_this_year": ["Health and energy", "Core relationships"],
        "release_this_year": ["Outdated commitments", "Draining situations"],
        "yearly_remedies": [
            {"planet": "general", "practice": "Morning sunlight and grounding practice daily."},
        ],
        "year_mantra":   "Build what lasts, release what doesn't.",
        "critical_dates": [],
    }
