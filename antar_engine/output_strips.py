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
# [why-block-leak-fix] English codenames are DEPRECATED FIELD×MODE names —
# they must never reach the user in ANY language. Translate to the same
# energy phrases the rest of the product uses. Ordered longer-first.
_INSTRUMENT_SUBS_EN: list[tuple[str, str]] = [
    (r'\bReal Estate Radar\b',    'your property area'),
    (r'\bCapital Reserves\b',     'your financial reserves'),
    (r'\bCapital Runway\b',       'your financial runway'),
    (r'\bAction Capacity\b',      'your capacity to act'),
    (r'\bAction Drive\b',         'your action and drive energy'),
    (r'\bAlliance Sync\b',        'your partnership area'),
    (r'\bAmbition Engine\b',      'your ambition and breakthrough energy'),
    (r'\bAuthority Engine\b',     'your identity and authority energy'),
    (r'\bAuthority Signal\b',     'your identity and authority energy'),
    (r'\bConflict Shield\b',      'your resilience under pressure'),
    (r'\bCreation Engine\b',      'your creativity area'),
    (r'\bCreative Pulse\b',       'your creativity area'),
    (r'\bEmotional Radar\b',      'your emotional and nurturing energy'),
    (r'\bExpansion Field\b',      'your growth area'),
    (r'\bFoundation Shield\b',    'your home and stability area'),
    (r'\bFortune Vector\b',       'your luck area'),
    (r'\bGlobal Vector\b',        'your foreign-connections area'),
    (r'\bGrowth Amplifier\b',     'your growth and wisdom energy'),
    (r'\bHealth Matrix\b',        'your health area'),
    (r'\bHungry Becoming\b',      'your drive to grow'),
    (r'\bIntuition Compass\b',    'your intuition and release energy'),
    (r'\bMagnetism Field\b',      'your love and partnership energy'),
    (r'\bPower Windows\b',        'your strongest time windows'),
    (r'\bProcessing Speed\b',     'your communication and intellect energy'),
    (r'\bRelationship Channel\b', 'your relationships area'),
    (r'\bResource Grid\b',        'your resource base'),
    (r'\bRevenue Pipeline\b',     'your income flow'),
    (r'\bStructural Load\b',      'your discipline and structure energy'),
    (r'\bStructure Field\b',      'your discipline and structure area'),
    (r'\bSystem Vitals\b',        'your health and vitality'),
    (r'\bVelocity Engine\b',      'your momentum'),
    (r'\bWisdom Lens\b',          'your wisdom and learning area'),
    (r'\bCareer Signal\b',        'your career area'),
    (r'\bLove Signal\b',          'your relationships area'),
    (r'\bWealth Signal\b',        'your wealth area'),
]

# Vedic / Sanskrit softeners — order matters (specific before generic)
_VEDIC_SUBS_ES: list[tuple[str, str]] = [
    # [ask-narration 2026-06-08] paridad ES con _VEDIC_SUBS_EN.
    (r'\blas?\s+combinaciones?\s+planetarias?\s+que\s+gobiernan\s+[a-záéíóúñ\s]+?\s+no\s+est[áa]n?\s+alineadas(?:\s+a\s+tu\s+favor)?(?:\s+ahora)?', 'el momento no está a tu favor'),
    (r'\blas?\s+combinaciones?\s+planetarias?\s+que\s+gobiernan\s+[a-záéíóúñ\s]+?\s+est[áa]n?\s+alineadas(?:\s+a\s+tu\s+favor)?(?:\s+ahora)?',     'el momento está a tu favor'),
    (r'\bcombinaciones?\s+planetarias?\s+(?:est[áa]n?|son)\s+no\s+alineadas?\b', 'el momento no está a tu favor'),
    (r'\bcombinaciones?\s+planetarias?\s+(?:est[áa]n?|son)\s+alineadas?\b',     'el momento está a tu favor'),
    (r'\bcombinaci[óo]n(?:es)?\s+planetarias?\b', 'la ventana actual'),
    (r'\balineaci[óo]n(?:es)?\s+planetarias?\b',  'la ventana actual'),
    (r'\bper[íi]odo\s+planetario\s+actual\b',    'la ventana actual'),
    # [bija-confine] — see EN list.
    (r'\bcant(?:a|e|ando|ar)\s+(?:om\s+)?(?:lam|vam|ram|yam|ham|aim|ksham)\b', 'canta el sonido semilla'),
    (r'(?-i:\b(?:LAM|VAM|RAM|YAM|HAM|KSHAM)\b)', ''),
    # [practice-leaks] Ayurveda / remedy vocabulary — compounds before generics.
    (r'\b(?:la\s+)?hora\s+de(?:l)?\s+(?:sol|luna|marte|mercurio|j[u\u00fa]piter|venus|saturno|rahu|ketu)\b', 'su hora de poder'),
    (r'\b(?:the\s+)?(?:sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\s+hora\b', 'su hora de poder'),
    (r'\b(?:sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\s+yantra\b', 'yantra de pr\u00e1ctica'),
    (r'\bpittas?\b',            'el elemento fuego'),
    (r'\bkaphas?\b',            'el elemento tierra-agua'),
    (r'\bvatas?\b',             'el elemento aire'),
    (r'\bdoshas?\b',            'constituci\u00f3n'),
    (r'\bs[a\u00e1]ttvic[oa]?s?\b', 'ligero y clarificante'),
    (r'\braj[a\u00e1]sic[oa]?s?\b', 'estimulante'),
    (r'\btam[a\u00e1]sic[oa]?s?\b', 'pesado y embotador'),
    (r'\banna\s*da{1,2}nam\b',  'ofrenda de alimentos'),
    (r'\bpanchadhatu\b',        'aleaci\u00f3n de cinco metales'),
    (r'\bpukhraj\b',            'zafiro amarillo'),
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
    # [tara-leak-fix] formas invertidas y simples en cualquier orden, antes del
    # reemplazo genérico \btara\b de más abajo.
    (r'\b(?:tara\s+)?Ati[-\s]?Mitra(?:\s+tara)?\b', 'energía lunar muy favorable'),
    (r'\b(?:tara\s+)?Sadhana(?:\s+tara)?\b',  'energía lunar de realización'),
    (r'\b(?:tara\s+)?Sampat(?:\s+tara)?\b',   'energía lunar de abundancia'),
    (r'\b(?:tara\s+)?Janma(?:\s+tara)?\b',    'energía lunar de introspección'),
    (r'\b(?:tara\s+)?Vipat(?:\s+tara)?\b',    'energía lunar cautelosa'),
    (r'\b(?:tara\s+)?Kshema(?:\s+tara)?\b',   'energía lunar protectora'),
    (r'\b(?:tara\s+)?Pratyari(?:\s+tara)?\b', 'energía lunar de resistencia'),
    (r'\b(?:tara\s+)?Vadha(?:\s+tara)?\b',    'energía lunar de obstáculo'),
    (r'\b(?:tara\s+)?Naidhana(?:\s+tara)?\b', 'energía lunar de transformación'),
    (r'\b(?:tara\s+)?Mitra(?:\s+tara)?\b',    'energía lunar favorable'),
    # Generic "la tara …"
    (r'\bla tara favorable\b',    'la energía lunar favorable'),
    (r'\bla tara desfavorable\b', 'la energía lunar desfavorable'),
    (r'\bla tara activa\b',       'la energía lunar activa'),
    (r'\btara\b',                 'energía lunar'),         # fallback last
    # [why-block-leak-fix] LK / chart-frame jargon (paridad ES)
    (r'\bdeuda intelectual\b',  'un atraso pendiente'),
    (r'\bsigno ascendente\b',   'identidad central'),
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
    # [polish] named nakshatras — added via patch_polish_content_tables.py
    (r'\bPurva\s+Phalguni\b', 'la energía lunar'),
    (r'\bUttara\s+Phalguni\b', 'la energía lunar'),
    (r'\bPurva\s+Ashadha\b', 'la energía lunar'),
    (r'\bUttara\s+Ashadha\b', 'la energía lunar'),
    (r'\bPurva\s+Bhadrapada\b', 'la energía lunar'),
    (r'\bUttara\s+Bhadrapada\b', 'la energía lunar'),
    (r'\bAshwini\b', 'la energía lunar'),
    (r'\bBharani\b', 'la energía lunar'),
    (r'\bKrittika\b', 'la energía lunar'),
    (r'\bRohini\b', 'la energía lunar'),
    (r'\bMrigashira\b', 'la energía lunar'),
    (r'\bArdra\b', 'la energía lunar'),
    (r'\bPunarvasu\b', 'la energía lunar'),
    (r'\bPushya\b', 'la energía lunar'),
    (r'\bAshlesha\b', 'la energía lunar'),
    (r'\bMagha\b', 'la energía lunar'),
    (r'\bHasta\b', 'la energía lunar'),
    (r'\bChitra\b', 'la energía lunar'),
    (r'\bSwati\b', 'la energía lunar'),
    (r'\bVishakha\b', 'la energía lunar'),
    (r'\bAnuradha\b', 'la energía lunar'),
    (r'\bJyeshtha\b', 'la energía lunar'),
    (r'\bMula\b', 'la energía lunar'),
    (r'\bShravana\b', 'la energía lunar'),
    (r'\bDhanishta\b', 'la energía lunar'),
    (r'\bShatabhisha\b', 'la energía lunar'),
    (r'\bRevati\b', 'la energía lunar'),
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
    # [ask-narration 2026-06-08] /ask yesno Claude calque-strip.
    # The yesno 'why' prompt already forbids astrology vocab; these
    # catch the leaks Claude emits anyway ('planetary combinations
    # governing X are not aligned...'). Verdict-direction-preserving.
    (r'\bthe\s+planetary\s+combinations?\s+governing\s+[a-z\s]+?\s+(?:are|is)\s+not\s+aligned(?:\s+in\s+your\s+favor)?(?:\s+right\s+now)?', 'the timing is not on your side'),
    (r'\bthe\s+planetary\s+combinations?\s+governing\s+[a-z\s]+?\s+(?:are|is)\s+aligned(?:\s+in\s+your\s+favor)?(?:\s+right\s+now)?', 'the timing is on your side'),
    (r'\bplanetary\s+combinations?\s+(?:are|is)\s+not\s+aligned\b', 'the timing is not on your side'),
    (r'\bplanetary\s+combinations?\s+(?:are|is)\s+aligned\b',       'the timing is on your side'),
    (r'\bplanetary\s+combinations?\b',  'the current window'),
    (r'\bplanetary\s+alignments?\b',    'the current window'),
    (r'\bcurrent\s+planetary\s+period\b', 'the current window'),
    # [bija-confine] seed syllables belong ONLY to mantra fields (which the
    # strip walks skip). Chant-context rewrite + uppercase-only standalone
    # drop — (?-i:) scopes out the loop's IGNORECASE so English ram/yam/ham
    # are untouched (Py>=3.11).
    (r'\bchant(?:ing|ed)?\s+(?:om\s+)?(?:lam|vam|ram|yam|ham|aim|ksham)\b', 'chanting the seed sound'),
    (r'(?-i:\b(?:LAM|VAM|RAM|YAM|HAM|KSHAM)\b)', ''),
    # [practice-leaks] Ayurveda / remedy vocabulary — compounds before generics.
    (r'\b(?:the\s+)?(?:sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\s+hora\b', 'its power hour'),
    (r'\b(?:sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\s+yantra\b', 'practice yantra'),
    (r'\bpittas?\b',            'the fire element'),
    (r'\bkaphas?\b',            'the earth-water element'),
    (r'\bvatas?\b',             'the air element'),
    (r'\bdoshas?\b',            'constitution'),
    (r'\bs[a\u00e1]ttvic[oa]?s?\b', 'light, clarifying'),
    (r'\braj[a\u00e1]sic[oa]?s?\b', 'stimulating'),
    (r'\btam[a\u00e1]sic[oa]?s?\b', 'heavy, dulling'),
    (r'\banna\s*da{1,2}nam\b',  'food offering'),
    (r'\bpanchadhatu\b',        'five-metal alloy'),
    (r'\bpukhraj\b',            'yellow sapphire'),
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
    # [tara-leak-fix] reversed ('Sadhana tara') and bare ('Sadhana') forms in any
    # word order, caught BEFORE the generic \btara\b fallback further down.
    (r'\b(?:tara\s+)?Ati[-\s]?Mitra(?:\s+tara)?\b', 'very favorable lunar energy'),
    (r'\b(?:tara\s+)?Sadhana(?:\s+tara)?\b',  'lunar energy for completion'),
    (r'\b(?:tara\s+)?Sampat(?:\s+tara)?\b',   'abundant lunar energy'),
    (r'\b(?:tara\s+)?Janma(?:\s+tara)?\b',    'inward lunar energy'),
    (r'\b(?:tara\s+)?Vipat(?:\s+tara)?\b',    'cautious lunar energy'),
    (r'\b(?:tara\s+)?Kshema(?:\s+tara)?\b',   'protective lunar energy'),
    (r'\b(?:tara\s+)?Pratyari(?:\s+tara)?\b', 'resistant lunar energy'),
    (r'\b(?:tara\s+)?Vadha(?:\s+tara)?\b',    'obstructed lunar energy'),
    (r'\b(?:tara\s+)?Naidhana(?:\s+tara)?\b', 'transformative lunar energy'),
    (r'\b(?:tara\s+)?Mitra(?:\s+tara)?\b',    'favorable lunar energy'),
    (r'\bfavorable tara\b',       'favorable lunar energy'),
    (r'\bunfavorable tara\b',     'unfavorable lunar energy'),
    (r'\btara\b',                 'lunar energy'),
    # [why-block-leak-fix] LK / chart-frame jargon
    (r'\bcarrying intellectual debt\b', 'working through an old backlog'),
    (r'\bintellectual debt\b',  'an old backlog'),
    (r'\bkarmic debt\b',        'an old pattern to resolve'),
    (r'\bfrom your rising sign\b', ''),
    (r'\brising sign\b',        'core identity'),
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
    # [polish] named nakshatras — added via patch_polish_content_tables.py
    (r'\bPurva\s+Phalguni\b', 'lunar energy'),
    (r'\bUttara\s+Phalguni\b', 'lunar energy'),
    (r'\bPurva\s+Ashadha\b', 'lunar energy'),
    (r'\bUttara\s+Ashadha\b', 'lunar energy'),
    (r'\bPurva\s+Bhadrapada\b', 'lunar energy'),
    (r'\bUttara\s+Bhadrapada\b', 'lunar energy'),
    (r'\bAshwini\b', 'lunar energy'),
    (r'\bBharani\b', 'lunar energy'),
    (r'\bKrittika\b', 'lunar energy'),
    (r'\bRohini\b', 'lunar energy'),
    (r'\bMrigashira\b', 'lunar energy'),
    (r'\bArdra\b', 'lunar energy'),
    (r'\bPunarvasu\b', 'lunar energy'),
    (r'\bPushya\b', 'lunar energy'),
    (r'\bAshlesha\b', 'lunar energy'),
    (r'\bMagha\b', 'lunar energy'),
    (r'\bHasta\b', 'lunar energy'),
    (r'\bChitra\b', 'lunar energy'),
    (r'\bSwati\b', 'lunar energy'),
    (r'\bVishakha\b', 'lunar energy'),
    (r'\bAnuradha\b', 'lunar energy'),
    (r'\bJyeshtha\b', 'lunar energy'),
    (r'\bMula\b', 'lunar energy'),
    (r'\bShravana\b', 'lunar energy'),
    (r'\bDhanishta\b', 'lunar energy'),
    (r'\bShatabhisha\b', 'lunar energy'),
    (r'\bRevati\b', 'lunar energy'),
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
    # [cycle-andres-fix 2026-06-09] Cycle invented-vocab drops
    "sub-chapter", "micro-chapter", "chapter-nesting", "major/sub/micro",
)

_DAY_NAMES_ES: tuple[str, ...] = (
    "lunes", "martes", "miércoles", "miercoles", "jueves", "viernes",
    "sábado", "sabado", "domingo", "ayer", "mañana", "manana",
)
_DAY_NAMES_EN: tuple[str, ...] = (
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "yesterday", "tomorrow",
)

# [non-canonical-scores] two-pass strip — parens first, bare second.
# Pass 1: any parenthetical whose interior contains 'X/56'.
# Pass 2: bare 'X/56' at word boundaries.
_SCORE_PATTERN_PARENS = re.compile(r'\s*\([^()]*?\d{1,2}/56[^()]*?\)\s*')
_SCORE_PATTERN_BARE   = re.compile(r'\b\d{1,2}/56\b')
# Back-compat alias for any external caller still referencing _SCORE_PATTERN.
_SCORE_PATTERN = _SCORE_PATTERN_PARENS
# [why-block-leak-fix] ordinal house references TRANSLATE to area labels
# (the voice rule: "your creativity area", never "5th house"). Dropping them
# garbles the sentence; translating preserves it. Consumes optional "lord"
# and "from your rising sign/lagna/ascendant" so no orphan fragments remain.
_HOUSE_AREA_EN: dict[int, str] = {
    1: 'identity area',       2: 'wealth area',     3: 'courage area',
    4: 'home area',           5: 'creativity area', 6: 'work area',
    7: 'partnership area',    8: 'transformation area',
    9: 'luck area',          10: 'career area',    11: 'gains area',
    12: 'foreign area',
}
_HOUSE_ORDINAL_EN = re.compile(
    r'\b(\d{1,2})(?:st|nd|rd|th)\s+house(?:\s+lord)?'
    r'(?:\s+from\s+(?:your\s+)?(?:rising\s+sign|lagna|ascendant))?',
    re.IGNORECASE)
_HOUSE_PATTERN_A = re.compile(r'\b\d{1,2}(?:st|nd|rd|th)\s+house\s*(?:lord)?', re.IGNORECASE)
_HOUSE_PATTERN_B = re.compile(r'\bhouse\s+\d{1,2}\b', re.IGNORECASE)
# [es-house-parity 2026-06-08] Spanish/Portuguese house-number leak.
# Mirrors _HOUSE_PATTERN_A/B for ES + PT ('casa N', 'casas N y M',
# 'en la casa N', 'casa 9 de fortuna'). DROP, matching EN backstop —
# _tidy collapses residual whitespace and orphan punctuation.
_HOUSE_PATTERN_ES = re.compile(
    r'\b(?:en\s+(?:la\s+|las\s+)?)?casas?\s+\d{1,2}'
    r'(?:\s+(?:y|e|,)\s+\d{1,2})*'
    r'(?:\s+de\s+[a-záéíóúñ]+)?',
    re.IGNORECASE,
)
_HOUSE_PATTERN_PT = re.compile(
    r'\b(?:(?:em|n[ao])\s+(?:a\s+|as\s+)?)?casas?\s+\d{1,2}'
    r'(?:\s+(?:e|,)\s+\d{1,2})*'
    r'(?:\s+d[ao]\s+[a-záéíóúãâêôç]+)?',
    re.IGNORECASE,
)



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
    # [why-block-leak-fix] EN is no longer a no-op: deprecated codenames
    # (Structural Load, Processing Speed, …) must be translated in English too.
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
    """Two-pass strip of ashtakavarga-style scores.

    Handles:
      (48/56)         — canonical
      (48/56 peak)    — extra text inside parens
      48/56           — bare, no parens
      48/56-peak      — hyphen-joined to a reason word

    Order: parens sweep first, then bare-form sweep.  Otherwise
    the bare sweep would kill the digits inside a parenthetical
    and leave orphan parens behind.
    """
    if not isinstance(text, str) or not text:
        return text
    cleaned = _SCORE_PATTERN_PARENS.sub(' ', text)
    cleaned = _SCORE_PATTERN_BARE.sub(' ', cleaned)
    return _tidy(cleaned)


def _strip_day_names(text: str, language: str = 'es') -> str:
    """Remove day-of-week name leaks from sentences.

    Matches both singular and plural forms (Saturday / Saturdays /
    sábado / sábados) via an optional trailing 's'.

    Phase 3.10b — cross-language sweep.  LLM output in non-English
    languages frequently embeds English day names ('Las Saturdays
    son fuertes').  When language != 'en' we run BOTH the requested
    language's list AND the English list, catching the cross-language
    leak without regressing the same-language case.
    """
    if not isinstance(text, str) or not text:
        return text
    # [3.10b] cross-language day-name sweep
    primary = _DAY_NAMES_ES if language == 'es' else _DAY_NAMES_EN
    filler  = 'hoy' if language == 'es' else 'today'
    # Non-English languages also sweep English day names (LLM bias).
    # English stays single-pass because Spanish day names in EN prose
    # are extremely rare and risk false positives on proper nouns.
    all_days = tuple(primary) + (_DAY_NAMES_EN if language != 'en' else ())
    # De-dup while preserving order (English-in-EN path would otherwise
    # sweep each day twice).
    seen = set()
    dedup_days = tuple(d for d in all_days if not (d in seen or seen.add(d)))
    result = text
    for day in dedup_days:
        # Qualified forms collapse to 'hoy/today' — supports plural too
        result = re.sub(
            rf'\b(este|esta|un|una|the|this|a|los|las)\s+{re.escape(day)}s?\b',
            filler, result, flags=re.IGNORECASE
        )
        # Bare day names (singular or plural) drop
        result = re.sub(rf'\b{re.escape(day)}s?\b', '', result, flags=re.IGNORECASE)
    return _tidy(result)


def _strip_planet_names(text: str, language: str = 'es', keep_planet_actors: bool = False) -> str:
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
    #    Skipped when keep_planet_actors (source='curated_static'): curated
    #    canonical statics are editorially reviewed and may name planets as actors.
    if not keep_planet_actors:
        planet_map = _PLANET_ENERGY_MAP_ES if language == 'es' else _PLANET_ENERGY_MAP_EN
        for planet, energy in planet_map.items():
            result = re.sub(rf'\b{re.escape(planet)}\b', energy, result, flags=re.IGNORECASE)

    # 3. Residual banned Sanskrit terms → drop
    for term in _BANNED_SANSKRIT_TERMS:
        result = re.sub(rf'\b{re.escape(term)}\b', '', result, flags=re.IGNORECASE)

    # 4. House-number references — EN translates to area labels first
    #    ("5th house" → "creativity area"); drop patterns remain as the
    #    residual fallback (e.g. "house 8", Spanish prose).
    if language != 'es':
        result = _HOUSE_ORDINAL_EN.sub(
            lambda m: _HOUSE_AREA_EN.get(int(m.group(1)), 'life area'), result)
    result = _HOUSE_PATTERN_A.sub('', result)
    result = _HOUSE_PATTERN_B.sub('', result)
    # [es-house-parity 2026-06-08 strip-call] symmetric ES/PT drop.
    if language == 'es':
        result = _HOUSE_PATTERN_ES.sub('', result)
    elif language == 'pt':
        result = _HOUSE_PATTERN_PT.sub('', result)

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
    """Collapse double spaces, orphaned punctuation, and chain-translation
    artifacts after substitutions.

    Chain-translation artifacts happen when the Vedic sub translates a
    compound (e.g. 'Rahu Kalam' → 'ventana de precaución') and the
    surrounding sentence already carries a similar word.  Examples:
      'tu Sol'     → 'tu tu energía de identidad'   (ES possessive dup)
      'Saturn energy' → '…energy energy'            (EN noun dup)
      'la ventana de Rahu Kalam' → 'la ventana de ventana de precaución'
    Dedup rules are surgical — they only collapse the exact
    stuttered phrase, not any legitimate repetition.
    """
    # [polish] dedup chain-translation artifacts
    # Possessive stutter (Spanish)
    text = re.sub(r'\btu\s+tu\b', 'tu', text, flags=re.IGNORECASE)
    text = re.sub(r'\btus\s+tus\b', 'tus', text, flags=re.IGNORECASE)
    # Noun stutter (English) — 'energy energy', 'cycle cycle', etc.
    text = re.sub(r'\b(energy)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(cycle|phase|window|alignment)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    # Panchang-of-panchang stutter (Spanish)
    text = re.sub(r'\bventana\s+de\s+ventana\b', 'ventana', text, flags=re.IGNORECASE)
    text = re.sub(r'\bla\s+la\b', 'la', text, flags=re.IGNORECASE)
    text = re.sub(r'\bel\s+el\b', 'el', text, flags=re.IGNORECASE)
    # [planet-sub-garble-fix] _strip_planet_names inserts a possessive phrase
    # ('your ... energy') where a bare noun stood, stranding a determiner:
    #   'the dual Moon aspects' -> 'the dual your ... energy aspects'.
    # Collapse determiner+possessive collisions (loop for stacks like 'the dual your').
    _prev = None
    while _prev != text:
        _prev = text
        text = re.sub(
            r'\b(?:the|a|an|this|that|these|those|its|his|her|their|dual)\s+your\b',
            'your', text, flags=re.IGNORECASE,
        )
    text = re.sub(r'\byour\s+your\b', 'your', text, flags=re.IGNORECASE)
    # [p1-natal-doubling 2026-06-08] template merge leak from
    # 'Saturn aligns with your natal Saturn' templates where the
    # planet -> energy strip rewrites both slots and 'natal'
    # sits between two 'your X energy' rewrites.
    text = re.sub(r'\byour\s+natal\s+your\b', 'your natal',
                  text, flags=re.IGNORECASE)
    # ES analogue: tu natal tu
    text = re.sub(r'\btu\s+natal\s+tu\b', 'tu natal',
                  text, flags=re.IGNORECASE)
    # [score-strip-garble-fix] orphaned opener left when an 'X/56' score was removed
    # mid-sentence ('sits at 21/56,' -> 'sits at,').
    text = re.sub(r'\bsits?\s+at\s*,\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*,\s*and\s*,\s*', ' and ', text)
    text = re.sub(r'\s+,\s+,\s+', ' ', text)
    # [es-house-parity 2026-06-08 tidy] residual orphans from dropped 'casa N'.
    # Pattern 'X en  y Y'  -> 'X y Y'   (dropped 'en casa 12 y' -> orphan ' y')
    text = re.sub(r'\s+en\s+(?=[,.;:])', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+en\s+y\s+', ' y ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+en\s+e\s+', ' e ', text, flags=re.IGNORECASE)
    # Same for Portuguese 'na'/'no'
    text = re.sub(r'\s+n[ao]\s+(?=[,.;:])', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+n[ao]\s+e\s+', ' e ', text, flags=re.IGNORECASE)
    # Standard whitespace / punctuation normalization
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
    source: str = 'llm',
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
    if source not in ('llm', 'curated_static'):
        raise ValueError(
            f"source={source!r} invalid; expected 'llm' or 'curated_static'"
        )
    keep_planet_actors = (source == 'curated_static')

    if content is None:
        return None
    if isinstance(content, list):
        return [
            apply_user_facing_strips(item, language, field_type, depth, source)
            for item in content
        ]
    if isinstance(content, dict):
        return {
            k: apply_user_facing_strips(v, language, field_type, depth, source)
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
        result = _strip_planet_names(result, language, keep_planet_actors=keep_planet_actors)
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
        result = _strip_planet_names(result, language, keep_planet_actors=keep_planet_actors)
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


# ── [P0b] Prediction-surface astro-voice scrub ────────────────────────────────
# Doctrine: energy/astro-voice belongs to Practice only; prediction surfaces
# carry concrete life-nouns. apply_user_facing_strips handles TOKENS; this
# handles PROSE phrases the LLM sometimes emits despite the no-jargon prompt.
# Conservative word/phrase SWAPS (not clause deletion) so sentences stay valid.
_ASTRO_VOICE_SWAPS_EN = [
    (re.compile(r"\bthe energy today is\b", re.I), "today is"),
    (re.compile(r"\btoday's energy is\b", re.I), "today is"),
    (re.compile(r"\benergy today\b", re.I), "the day"),
    (re.compile(r"\bnatural ruling energy\b", re.I), "tone"),
    (re.compile(r"\bruling energy\b", re.I), "tone"),
    # [3a 2026-06-24] constructions that leaked live (plain 'low energy' stays)
    (re.compile(r"\bthe day['’]s energy is\b", re.I), "the day is"),
    (re.compile(r"\b(?:today['’]s\s+)?lunar energy\b", re.I), "the day's mood"),
    (re.compile(r"\s+energy(['’]s)\b", re.I), r"\1"),
    (re.compile(r"\bthe conflict zone of your chart\b", re.I), "this area"),
    (re.compile(r"\bconflict zone of your chart\b", re.I), "this area"),
    (re.compile(r"\bconflict zone\b", re.I), "area of tension"),
    (re.compile(r"\bafflicted\b", re.I), "strained"),
    (re.compile(r"\bwell[- ]?dignified\b", re.I), "well supported"),
    (re.compile(r"\bdignified\b", re.I), "supported"),
    (re.compile(r"\bexalted\b", re.I), "strong"),
    (re.compile(r"\bdebilitated\b", re.I), "weak"),
    (re.compile(r"\bcombust\b", re.I), "strained"),
    (re.compile(r"\bretrograde\b", re.I), "in review"),
    # weekday-as-planet narration ("Tuesday amplifies courage")
    (re.compile(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I), "today"),
]


def strip_prediction_astro_voice(text, language="en"):
    """Swap astro-voice phrases for plain language on prediction surfaces.
    EN-only (the source language); a no-op for already-translated text."""
    if not isinstance(text, str) or not text.strip():
        return text
    if (language or "en") != "en":
        return text
    out = text
    for _rx, _repl in _ASTRO_VOICE_SWAPS_EN:
        out = _rx.sub(_repl, out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    return out.strip()
