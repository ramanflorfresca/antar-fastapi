"""
antar_engine/output_strips.py
Central output strip module.

All user-facing LLM output flows through ``apply_user_facing_strips()``.
This is the single enforcement point for four bug classes that every
LLM endpoint has historically leaked:

  1. English instrument codenames (Magnetism Field, Ambition Engine, …)
  2. Sanskrit / Vedic jargon (Gajakesari, tara, nakshatra, MD/AD, …)
  3. Raw "X/56" ashtakavarga score fractions
  4. Day-of-week name leaks (martes, sunday, …)

Rules
-----
 * DO NOT add new strip logic to individual endpoints.  Add it here.
 * DO NOT bypass this function on user-facing text.
 * ``field_type`` controls which layers run — pick the right one:

    field_type='plain'     — full strip. For senal_de_hoy, haz_hoy[],
                             evita_hoy[], observa_hoy_text,
                             verdict_subline, plain_summary,
                             action_item, signal_line.
    field_type='headline'  — same layers as 'plain'; caller typically
                             also truncates for notifications / cards.
    field_type='evidence'  — minimal: instruments + day names only.
                             Keeps Vedic depth + raw scores.  For
                             el_movimiento, why_this, strategic context.
    field_type='window'    — instruments + day names stripped; Sanskrit
                             Panchang terms (Abhijit Muhurta, Rahu Kalam)
                             allowed because the UI glosses them.

 * ``depth`` controls Vedic aggressiveness:

    depth='user'        — strip all Vedic terms (default, consumer flow)
    depth='power_user'  — keep classical Sanskrit terms (future feature
                          for Navigator users who opt in to depth)

Architectural note
------------------
The private ``_strip_*`` helpers here are the canonical implementations.
The legacy functions in ``plain_english._strip_jargon`` and
``daily_prediction_engine._strip_day_names_from_signal`` are kept in
place during Phase 1 migration to avoid breakage — they will be
converted to deprecated wrappers in Phase 5.
"""

from __future__ import annotations

import re
from typing import Any


# ════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════

# Canonical label map (exact, case-insensitive match) — mirrors
# main.py::_INSTRUMENT_TRANSLATIONS so that Phase 3 can drop that
# duplicate.  Used by _translate_instrument_name() for section labels.
_INSTRUMENT_TRANSLATIONS: dict[str, dict[str, str]] = {
    'es': {
        'SYSTEM VITALS':        'SEÑALES VITALES',
        'CAPITAL RESERVES':     'RESERVAS DE CAPITAL',
        'ACTION CAPACITY':      'CAPACIDAD DE ACCIÓN',
        'REAL ESTATE RADAR':    'RADAR INMOBILIARIO',
        'CREATION ENGINE':      'MOTOR CREATIVO',
        'CONFLICT SHIELD':      'ESCUDO DE CONFLICTOS',
        'ALLIANCE SYNC':        'SINCRONIZACIÓN DE ALIANZAS',
        'CAPITAL RUNWAY':       'PISTA DE CAPITAL',
        'FORTUNE VECTOR':       'VECTOR DE FORTUNA',
        'AUTHORITY ENGINE':     'MOTOR DE AUTORIDAD',
        'REVENUE PIPELINE':     'FLUJO DE INGRESOS',
        'GLOBAL VECTOR':        'VECTOR GLOBAL',
        'INTUITION COMPASS':    'BRÚJULA DE INTUICIÓN',
        'EMOTIONAL RADAR':      'RADAR EMOCIONAL',
        'PROCESSING SPEED':     'VELOCIDAD DE PROCESAMIENTO',
        'MAGNETISM FIELD':      'CAMPO MAGNÉTICO',
        'ACTION DRIVE':         'IMPULSO DE ACCIÓN',
        'AMBITION ENGINE':      'MOTOR DE AMBICIÓN',
        'STRUCTURAL LOAD':      'CARGA ESTRUCTURAL',
        'GROWTH AMPLIFIER':     'AMPLIFICADOR DE CRECIMIENTO',
        'AUTHORITY SIGNAL':     'SEÑAL DE AUTORIDAD',
        'RELATIONSHIP CHANNEL': 'CANAL DE RELACIONES',
        'VITALITY':             'VITALIDAD',
    },
    'en': {},   # no-op: codenames already in English
    # Backlog: 'pt', 'hi', 'fr' — fill in later sprints.
}

# Inline prose translation list — case-insensitive, applied anywhere
# the English codename appears inside sentences.  Ordered longer-first
# to avoid partial shadowing (e.g. "Authority Signal" before "Vitality").
_INSTRUMENT_SUBS_ES: list[tuple[str, str]] = [
    (r'\bReal Estate Radar\b',   'radar inmobiliario'),
    (r'\bCapital Reserves\b',    'reservas de capital'),
    (r'\bCapital Runway\b',      'pista de capital'),
    (r'\bAction Capacity\b',     'capacidad de acción'),
    (r'\bAction Drive\b',        'impulso de acción'),
    (r'\bAlliance Sync\b',       'sincronización de alianzas'),
    (r'\bAmbition Engine\b',     'motor de ambición'),
    (r'\bAuthority Engine\b',    'motor de autoridad'),
    (r'\bAuthority Signal\b',    'señal de autoridad'),
    (r'\bConflict Shield\b',     'escudo de conflictos'),
    (r'\bCreation Engine\b',     'motor creativo'),
    (r'\bCreative Pulse\b',      'pulso creativo'),
    (r'\bEmotional Radar\b',     'radar emocional'),
    (r'\bExpansion Field\b',     'campo de expansión'),
    (r'\bFoundation Shield\b',   'escudo de fundamentos'),
    (r'\bFortune Vector\b',      'vector de fortuna'),
    (r'\bGlobal Vector\b',       'vector global'),
    (r'\bGrowth Amplifier\b',    'amplificador de crecimiento'),
    (r'\bHealth Matrix\b',       'matriz de salud'),
    (r'\bHungry Becoming\b',     'impulso de búsqueda'),
    (r'\bIntuition Compass\b',   'brújula de intuición'),
    (r'\bMagnetism Field\b',     'campo magnético'),
    (r'\bPower Windows\b',       'ventanas de poder'),
    (r'\bProcessing Speed\b',    'velocidad de procesamiento'),
    (r'\bRelationship Channel\b','canal de relaciones'),
    (r'\bResource Grid\b',       'red de recursos'),
    (r'\bRevenue Pipeline\b',    'flujo de ingresos'),
    (r'\bSignal Detected\b',     'señal detectada'),
    (r'\bStructural Load\b',     'carga estructural'),
    (r'\bStructure Field\b',     'campo de estructura'),
    (r'\bSystem Vitals\b',       'señales vitales'),
    (r'\bVelocity Engine\b',     'motor de velocidad'),
    (r'\bWisdom Lens\b',         'lente de sabiduría'),
    (r'\bCareer Signal\b',       'señal de carrera'),
    (r'\bLove Signal\b',         'señal de relaciones'),
    (r'\bWealth Signal\b',       'señal de abundancia'),
    (r'\bVitality\b',            'vitalidad'),
]
_INSTRUMENT_SUBS_EN: list[tuple[str, str]] = []   # no-op in English

# Vedic / Sanskrit softeners — order matters (specific before generic)
_VEDIC_SUBS_ES: list[tuple[str, str]] = [
    # Named yogas
    (r'\byoga Gajakesari\b',      'alineación Luna–Júpiter favorable'),
    (r'\byoga Shubha Kartari\b',  'alineación favorable de benéficos'),
    (r'\byoga Ubhayachari\b',     'alineación bilateral favorable'),
    (r'\bGajakesari\b',           'alineación Luna–Júpiter favorable'),
    (r'\bShubha Kartari\b',       'alineación favorable de benéficos'),
    (r'\bUbhayachari\b',          'alineación bilateral favorable'),
    (r'\bLakshmi yoga\b',         'alineación de prosperidad'),
    (r'\bChandra-Mangala\b',      'alineación Luna–Marte'),
    (r'\bDhana yoga\b',           'alineación de abundancia'),
    (r'\bHamsa yoga\b',           'alineación de sabiduría'),
    (r'\bRuchaka yoga\b',         'alineación de autoridad'),
    # Named taras
    (r'\btara Ati-Mitra\b',       'energía lunar muy favorable'),
    (r'\btara Ati Mitra\b',       'energía lunar muy favorable'),
    (r'\btara Mitra\b',           'energía lunar favorable'),
    (r'\btara Sadhana\b',         'energía lunar de realización'),
    (r'\btara Sampat\b',          'energía lunar de abundancia'),
    (r'\btara Janma\b',           'energía lunar de introspección'),
    (r'\btara Vipat\b',           'energía lunar cautelosa'),
    (r'\btara Kshema\b',          'energía lunar protectora'),
    (r'\btara Pratyari\b',        'energía lunar de resistencia'),
    (r'\btara Vadha\b',           'energía lunar de obstáculo'),
    # Generic "la tara …"
    (r'\bla tara favorable\b',    'la energía lunar favorable'),
    (r'\bla tara desfavorable\b', 'la energía lunar desfavorable'),
    (r'\bla tara activa\b',       'la energía lunar activa'),
    (r'\btara\b',                 'energía lunar'),         # fallback last
    # Named Panchang periods (plain fields only; windows keep these via field_type='window')
    (r'\bAbhijit Muhurta\b',      'ventana favorable del mediodía'),
    (r'\bRahu Kalam\b',           'ventana de precaución'),
    (r'\bGulika Kala\b',          'zona de interferencia'),
    (r'\bYamagandam\b',           'zona desfavorable'),
    (r'\bMuhurta\b',              'ventana'),
    (r'\bKalam\b',                'período'),
    # Dasha jargon
    (r'\bMahadasha\b',            'período mayor'),
    (r'\bAntardasha\b',           'subperíodo'),
    (r'\bPratyantardasha\b',      'sub-subperíodo'),
    (r'\bSookshma dasha\b',       'ciclo menor'),
    (r'\b(\w+) MD \+ (\w+) AD\b', r'\1 en período mayor con \2 en subperíodo'),
    (r'\b(\w+) MD\b',             r'\1, tu planeta del período mayor'),
    (r'\b(\w+) AD\b',             r'\1 en subperíodo'),
    (r'\b(\w+) PD\b',             r'\1 en sub-subperíodo'),
    (r'\b(\w+) SD\b',             r'\1 en ciclo menor'),
    # Sanskrit nouns
    (r'\bnakshatra lunar\b',      'la energía lunar del día'),
    (r'\bnakshatra\b',            'la energía lunar'),
    (r'\bashtakavarga\b',         'puntaje planetario'),
    (r'\bupagraha\b',             'influencia sutil'),
    # Generic yogas
    (r'\bdos yogas muy auspiciosos\b',  'dos alineaciones muy favorables'),
    (r'\btres yogas muy auspiciosos\b', 'tres alineaciones muy favorables'),
    (r'\byogas muy auspiciosos\b',      'alineaciones muy favorables'),
    (r'\byogas auspiciosos\b',          'alineaciones favorables'),
    (r'\byogas activos\b',              'alineaciones activas'),
    (r'\byogas\b',                      'alineaciones'),
]

_VEDIC_SUBS_EN: list[tuple[str, str]] = [
    (r'\byoga Gajakesari\b',      'favorable Moon–Jupiter alignment'),
    (r'\byoga Shubha Kartari\b',  'benefic protective alignment'),
    (r'\byoga Ubhayachari\b',     'bilateral benefic alignment'),
    (r'\bGajakesari\b',           'favorable Moon–Jupiter alignment'),
    (r'\bShubha Kartari\b',       'benefic protective alignment'),
    (r'\bUbhayachari\b',          'bilateral benefic alignment'),
    (r'\bLakshmi yoga\b',         'prosperity alignment'),
    (r'\bChandra-Mangala\b',      'Moon–Mars alignment'),
    (r'\bDhana yoga\b',           'abundance alignment'),
    (r'\bHamsa yoga\b',           'wisdom alignment'),
    (r'\bRuchaka yoga\b',         'authority alignment'),
    (r'\btara Ati-Mitra\b',       'very favorable lunar energy'),
    (r'\btara Ati Mitra\b',       'very favorable lunar energy'),
    (r'\btara Mitra\b',           'favorable lunar energy'),
    (r'\btara Sadhana\b',         'lunar energy for completion'),
    (r'\btara Sampat\b',          'abundant lunar energy'),
    (r'\btara Janma\b',           'inward lunar energy'),
    (r'\btara Vipat\b',           'cautious lunar energy'),
    (r'\btara Kshema\b',          'protective lunar energy'),
    (r'\btara Pratyari\b',        'resistant lunar energy'),
    (r'\btara Vadha\b',           'obstructed lunar energy'),
    (r'\bfavorable tara\b',       'favorable lunar energy'),
    (r'\bunfavorable tara\b',     'unfavorable lunar energy'),
    (r'\btara\b',                 'lunar energy'),
    (r'\bAbhijit Muhurta\b',      'favorable midday window'),
    (r'\bRahu Kalam\b',           'caution window'),
    (r'\bGulika Kala\b',          'interference zone'),
    (r'\bYamagandam\b',           'unfavorable zone'),
    (r'\bMuhurta\b',              'window'),
    (r'\bKalam\b',                'period'),
    (r'\bMahadasha\b',            'major period'),
    (r'\bAntardasha\b',           'sub-period'),
    (r'\bPratyantardasha\b',      'sub-sub-period'),
    (r'\bSookshma dasha\b',       'minor cycle'),
    (r'\b(\w+) MD \+ (\w+) AD\b', r'\1 major period with \2 sub-period'),
    (r'\b(\w+) MD\b',             r'\1, your major-period planet'),
    (r'\b(\w+) AD\b',             r'\1 sub-period'),
    (r'\b(\w+) PD\b',             r'\1 sub-sub-period'),
    (r'\b(\w+) SD\b',             r'\1 minor cycle'),
    (r'\bnakshatra lunar\b',      "the day's lunar energy"),
    (r'\bnakshatra\b',            'lunar energy'),
    (r'\bashtakavarga\b',         'planetary strength score'),
    (r'\bupagraha\b',             'subtle influence'),
    (r'\btwo highly auspicious yogas\b',   'two strongly favorable alignments'),
    (r'\bthree highly auspicious yogas\b', 'three strongly favorable alignments'),
    (r'\bhighly auspicious yogas\b',       'strongly favorable alignments'),
    (r'\bauspicious yogas\b',              'favorable alignments'),
    (r'\bactive yogas\b',                  'active alignments'),
    (r'\byogas\b',                         'alignments'),
]

# Planet-name → energy-phrase map — canonical copy of
# plain_english.ENERGY_MAP.  Used by _strip_planet_names().
_PLANET_ENERGY_MAP_EN: dict[str, str] = {
    "rahu":    "your ambition and breakthrough energy",
    "ketu":    "your intuition and release energy",
    "saturn":  "your discipline and structure energy",
    "jupiter": "your growth and wisdom energy",
    "mars":    "your action and drive energy",
    "venus":   "your love and partnership energy",
    "mercury": "your communication and intellect energy",
    "sun":     "your identity and authority energy",
    "moon":    "your emotional and nurturing energy",
}
_PLANET_ENERGY_MAP_ES: dict[str, str] = {
    "rahu":    "tu energía de ambición y ruptura",
    "ketu":    "tu energía de intuición y desapego",
    "saturno": "tu energía de disciplina y estructura",
    "jupiter": "tu energía de crecimiento y sabiduría",
    "júpiter": "tu energía de crecimiento y sabiduría",
    "marte":   "tu energía de acción y empuje",
    "venus":   "tu energía de amor y asociación",
    "mercurio":"tu energía de comunicación e intelecto",
    "sol":     "tu energía de identidad y autoridad",
    "luna":    "tu energía emocional y nutrición",
}

# Dasha period combos — canonical copy of plain_english.PERIOD_MAP
_PERIOD_MAP_EN: dict[str, str] = {
    "rahu period":    "Ambition cycle",
    "rahu-saturn":    "Ambition-meets-Structure phase",
    "rahu-jupiter":   "Ambition-meets-Growth phase",
    "rahu-mercury":   "Ambition-meets-Communication phase",
    "rahu-venus":     "Ambition-meets-Magnetism phase",
    "rahu-mars":      "Ambition-meets-Execution phase",
    "rahu-moon":      "Ambition-meets-Emotional phase",
    "rahu-sun":       "Ambition-meets-Authority phase",
    "rahu-ketu":      "Ambition-meets-Extraction phase",
    "saturn period":  "Structure cycle",
    "jupiter period": "Growth cycle",
    "mars period":    "Execution cycle",
    "venus period":   "Magnetism cycle",
    "mercury period": "Communication cycle",
    "sun period":     "Authority cycle",
    "moon period":    "Emotional cycle",
    "ketu period":    "Extraction cycle",
    "mars-moon":      "Execution-meets-Emotional phase",
    "mars-saturn":    "Execution-meets-Structure phase",
    "mars-jupiter":   "Execution-meets-Growth phase",
    "mars-venus":     "Execution-meets-Magnetism phase",
    "mars-mercury":   "Execution-meets-Communication phase",
    "mars-rahu":      "Execution-meets-Ambition phase",
    "mars-sun":       "Execution-meets-Authority phase",
    "mars-ketu":      "Execution-meets-Extraction phase",
}

# Residual Sanskrit terms dropped entirely (not translated)
_BANNED_SANSKRIT_TERMS: tuple[str, ...] = (
    "atmakaraka", "amatyakaraka", "navamsa", "darakaraka", "putrakaraka",
    "bhava", "graha", "rashi", "vimsottari", "ashtottari", "jaimini",
    "lagna", "yogakaraka", "vargottama", "panchanga", "tithi", "karana",
    "vara", "hora", "ayanamsa", "ephemeris", "varshphal", "masik",
    "teva", "umra",
)

_DAY_NAMES_ES: tuple[str, ...] = (
    "lunes", "martes", "miércoles", "miercoles", "jueves", "viernes",
    "sábado", "sabado", "domingo", "ayer", "mañana", "manana",
)
_DAY_NAMES_EN: tuple[str, ...] = (
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "yesterday", "tomorrow",
)

_SCORE_PATTERN = re.compile(r'\s*\((\d{1,2})/56\)\s*')
_HOUSE_PATTERN_A = re.compile(r'\b\d{1,2}(?:st|nd|rd|th)\s+house\s*(?:lord)?', re.IGNORECASE)
_HOUSE_PATTERN_B = re.compile(r'\bhouse\s+\d{1,2}\b', re.IGNORECASE)


# ════════════════════════════════════════════════════════════════
# Private strippers
# ════════════════════════════════════════════════════════════════

def _strip_instrument_names(text: str, language: str = 'es') -> str:
    """
    Translate English instrument codenames (Magnetism Field, Ambition
    Engine, …) into plain-language equivalents.  No-op for English.
    """
    if not isinstance(text, str) or not text:
        return text
    if language == 'en':
        return text
    subs = _INSTRUMENT_SUBS_ES if language == 'es' else _INSTRUMENT_SUBS_EN
    result = text
    for pattern, replacement in subs:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    # Fix stranded possessives ("your campo magnético" → "tu campo magnético")
    result = re.sub(
        r'\byour\s+(campo|motor|vector|señal|radar|pulso|flujo|red|ventanas|'
        r'pista|impulso|brújula|velocidad|matriz|escudo|canal|sincronización|'
        r'amplificador|lente|carga|reservas|capacidad|vitalidad)\b',
        r'tu \1', result, flags=re.IGNORECASE
    )
    return _tidy(result)


def _strip_vedic_jargon(text: str, language: str = 'es') -> str:
    """Replace Sanskrit / Vedic technical terms with plain-language equivalents."""
    if not isinstance(text, str) or not text:
        return text
    subs = _VEDIC_SUBS_ES if language == 'es' else _VEDIC_SUBS_EN
    result = text
    for pattern, replacement in subs:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return _tidy(result)


def _strip_raw_scores(text: str) -> str:
    """Remove raw ``(X/56)`` score fractions from user-facing prose."""
    if not isinstance(text, str) or not text:
        return text
    cleaned = _SCORE_PATTERN.sub(' ', text)
    return _tidy(cleaned)


def _strip_day_names(text: str, language: str = 'es') -> str:
    """Remove day-of-week name leaks from sentences."""
    if not isinstance(text, str) or not text:
        return text
    days = _DAY_NAMES_ES if language == 'es' else _DAY_NAMES_EN
    filler = 'hoy' if language == 'es' else 'today'
    result = text
    for day in days:
        # Qualified forms collapse to "hoy/today"
        result = re.sub(
            rf'\b(este|esta|un|una|the|this|a)\s+{re.escape(day)}\b',
            filler, result, flags=re.IGNORECASE
        )
        # Bare day names drop
        result = re.sub(rf'\b{re.escape(day)}\b', '', result, flags=re.IGNORECASE)
    return _tidy(result)


def _strip_planet_names(text: str, language: str = 'es') -> str:
    """
    Replace planet names with energy-frequency phrases and drop stray
    Sanskrit / house references.  Canonical copy of the original
    plain_english._strip_jargon() logic, parameterized by language.
    """
    if not isinstance(text, str) or not text:
        return text
    result = text

    # 1. Dasha/period combinations (longest match first so sub-strings don't win)
    period_map = _PERIOD_MAP_EN  # (ES periods map not yet built — see backlog)
    for period_term in sorted(period_map.keys(), key=len, reverse=True):
        result = re.sub(
            rf'\b{re.escape(period_term)}\b',
            period_map[period_term], result, flags=re.IGNORECASE
        )

    # 2. Planet names → energy phrases (per-language)
    planet_map = _PLANET_ENERGY_MAP_ES if language == 'es' else _PLANET_ENERGY_MAP_EN
    for planet, energy in planet_map.items():
        result = re.sub(rf'\b{re.escape(planet)}\b', energy, result, flags=re.IGNORECASE)

    # 3. Residual banned Sanskrit terms → drop
    for term in _BANNED_SANSKRIT_TERMS:
        result = re.sub(rf'\b{re.escape(term)}\b', '', result, flags=re.IGNORECASE)

    # 4. House-number references → drop (e.g. "10th house", "house 8")
    result = _HOUSE_PATTERN_A.sub('', result)
    result = _HOUSE_PATTERN_B.sub('', result)

    return _tidy(result)


def _translate_instrument_name(name: str, language: str = 'es') -> str:
    """
    Exact-match label translator for whole instrument labels
    (e.g. section headings in the SYSTEM VITALS card).  Returns the
    original string if no translation is known.
    """
    if not name or language == 'en':
        return name
    table = _INSTRUMENT_TRANSLATIONS.get(language, {})
    direct = table.get(name.upper())
    if direct:
        return direct
    for en, loc in table.items():
        if en.lower() == name.lower():
            return loc
    return name


# ════════════════════════════════════════════════════════════════
# Internal utilities
# ════════════════════════════════════════════════════════════════

def _tidy(text: str) -> str:
    """Collapse double spaces and orphaned punctuation after substitutions."""
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\s+([,.;:])', r'\1', text)
    return text.strip()


# ════════════════════════════════════════════════════════════════
# Public entry point
# ════════════════════════════════════════════════════════════════

_VALID_FIELD_TYPES = ('plain', 'headline', 'evidence', 'window', 'timing')
_VALID_DEPTHS = ('user', 'power_user')


def apply_user_facing_strips(
    content: Any,
    language: str = 'es',
    field_type: str = 'plain',
    depth: str = 'user',
) -> Any:
    """
    Single enforcement point for all user-facing LLM output.

    See module docstring for the contract — in particular which layers
    run per ``field_type`` and how ``depth`` gates Vedic stripping.

    Returns the same type that was passed in (str, list, dict, or any
    non-string scalar which is passed through unchanged).
    """
    if field_type not in _VALID_FIELD_TYPES:
        raise ValueError(
            f"field_type={field_type!r} invalid; expected one of {_VALID_FIELD_TYPES}"
        )
    if depth not in _VALID_DEPTHS:
        raise ValueError(
            f"depth={depth!r} invalid; expected one of {_VALID_DEPTHS}"
        )

    if content is None:
        return None
    if isinstance(content, list):
        return [
            apply_user_facing_strips(item, language, field_type, depth)
            for item in content
        ]
    if isinstance(content, dict):
        return {
            k: apply_user_facing_strips(v, language, field_type, depth)
            for k, v in content.items()
        }
    if not isinstance(content, str):
        return content  # int, float, bool, etc. pass through
    if not content:
        return content

    result = content

    # Layer ordering is critical — compound Vedic terms (Abhijit Muhurta,
    # Rahu Kalam) must be translated BEFORE _strip_planet_names fires, or
    # the banned-Sanskrit sweep would break them into fragments.
    if field_type in ('plain', 'headline'):
        result = _strip_instrument_names(result, language)
        if depth == 'user':
            result = _strip_vedic_jargon(result, language)
        result = _strip_day_names(result, language)
        result = _strip_planet_names(result, language)
        result = _strip_raw_scores(result)

    elif field_type == 'evidence':
        # Keep Vedic depth + raw scores for "the why" expandables.
        result = _strip_instrument_names(result, language)
        result = _strip_day_names(result, language)
        # (no vedic / no score strip)

    elif field_type == 'window':
        # Panchang terms (Abhijit Muhurta, Rahu Kalam) stay — UI glosses them.
        result = _strip_instrument_names(result, language)
        result = _strip_day_names(result, language)
        # (no vedic / no score / no planet strip)

    elif field_type == 'timing':
        # Same as 'plain' EXCEPT day-of-week names are preserved.
        # Used for fields where the weekday IS the answer, e.g. the
        # weekly_briefing.best_day field ("Wednesday — mid-week clarity").
        result = _strip_instrument_names(result, language)
        if depth == 'user':
            result = _strip_vedic_jargon(result, language)
        result = _strip_planet_names(result, language)
        result = _strip_raw_scores(result)
        # (no day-name strip — that's the whole point of this field type)

    return result


__all__ = [
    "apply_user_facing_strips",
    "_translate_instrument_name",
    # Private but re-exported for the Phase 5 legacy wrappers:
    "_strip_instrument_names",
    "_strip_vedic_jargon",
    "_strip_raw_scores",
    "_strip_day_names",
    "_strip_planet_names",
]
