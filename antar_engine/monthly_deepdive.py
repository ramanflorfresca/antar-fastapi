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
) -> dict:
    """
    Generate or return cached monthly deep-dive.
    Regenerates on the 1st of each month or if force_refresh=True.
    """
    now        = datetime.now(timezone.utc)
    month_key  = now.strftime("%Y-%m")

    # Check cache
    if not force_refresh:
        cached = _read_cache(chart_id, month_key, supabase)
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
    result = await _call_claude(context, claude_client)
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
    _lang = 'en'
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

    # Save to cache
    try:
        supabase.table(DEEPDIVE_TABLE).upsert({
            "chart_id":  chart_id,
            "month_key": month_key,
            "deepdive":  result,
            "created_at": now.isoformat(),
        }).execute()
        logger.info(f"[monthly] Deep-dive saved for {chart_id[:8]} {month_key}")
    except Exception as e:
        logger.warning(f"[monthly] Cache save failed: {e}")

    return result


def _read_cache(chart_id: str, month_key: str, supabase) -> Optional[dict]:
    try:
        result = supabase.table(DEEPDIVE_TABLE) \
            .select("deepdive") \
            .eq("chart_id", chart_id) \
            .eq("month_key", month_key) \
            .execute()
        if result.data:
            return result.data[0]["deepdive"]
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


async def _call_claude(context: str, claude_client) -> dict:
    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=MONTHLY_SYSTEM_PROMPT,
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
