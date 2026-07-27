"""
antar_engine/patra_catalog.py
──────────────────────────────────────────────────────────────────────
Localized + dejargoned catalog for the Patra onboarding questions.

Two goals in one file:
  1. Localization — every user-facing string has `{en, es}` entries, so
     Spanish users see Spanish questions + tap labels, not English.
  2. Dejargon (project rule #12) — zero Sanskrit / planet names / raw
     astrological terms in any user-facing string.  The EN source has
     been rewritten to use energy-layer phrasing ("your chart is carrying
     strong relationship energy", "expansion — family, wisdom, generativity",
     etc.) in place of "Venus dasha" / "Jupiter is your active planet" / etc.

What is NOT localized (by design):
  - `value`  — stable enum keys used in analytics + DB (e.g. "married",
    "entrepreneur").  NEVER change or you break downstream pipelines.
  - `patra`  — Supabase patra field keys (e.g. "marital_status").
  - `extracts` — list of patra fields this question fills.
  - `reason` — internal-only debugging string, never user-facing.

Adding a question
-----------------
  1. Add an entry to PATRA_QUESTIONS under a stable snake_case id.
  2. Provide en + es for every user-facing string.
  3. Run: pytest tests/test_patra_catalog.py  (all entries round-trip test)

Consumers
---------
  antar_engine/patra_conversation.py::get_smart_patra_questions
  — renders the appropriate question_id via render_question(id, language).
"""

from __future__ import annotations

from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# Question catalog
#
# Each entry:
#   question:    {en, es}           — the question bubble text
#   reason:      str                 — internal-only, not user-facing
#   options:     list[dict]          — tap options
#                   label:   {en, es}
#                   value:   str     — STABLE enum key, don't touch
#                   patra:   dict    — STABLE field → value mapping
#   extracts:    list[str]           — patra fields this question populates
# ═══════════════════════════════════════════════════════════════════════════

PATRA_QUESTIONS: dict = {

    # ── RELATIONSHIP ────────────────────────────────────────────────────

    "relationship_venus_dasha": {
        "question": {
            "en": ("Your chart is carrying strong relationship energy right now. "
                   "Are you navigating that inside a partnership, or is the pull "
                   "still looking for somewhere to land?"),
            "es": ("Tu carta está cargando una energía fuerte de vínculos ahora mismo. "
                   "¿Estás navegando esa energía dentro de una relación, o esa "
                   "atracción todavía está buscando dónde aterrizar?"),
        },
        "reason": "Venus dasha or exalted Venus active",
        "options": [
            {"label": {"en": "In a relationship",       "es": "En una relación"},            "value": "in_relationship", "patra": {"marital_status": "in_relationship"}},
            {"label": {"en": "Married",                  "es": "Casado/a"},                   "value": "married",         "patra": {"marital_status": "married"}},
            {"label": {"en": "Single — ready",           "es": "Soltero/a — listo/a"},        "value": "single",          "patra": {"marital_status": "single"}},
            {"label": {"en": "It's complicated",         "es": "Es complicado"},              "value": "separated",       "patra": {"marital_status": "separated"}},
            {"label": {"en": "Recently out of one",      "es": "Recién salí de una"},         "value": "divorced",        "patra": {"marital_status": "divorced"}},
        ],
        "extracts": ["marital_status"],
    },

    "relationship_moon_dasha": {
        "question": {
            "en": ("Your chart is running deep emotional currents right now. "
                   "Is that depth being channelled through a close partnership, "
                   "or are you processing it on your own?"),
            "es": ("Tu carta está atravesando corrientes emocionales profundas ahora mismo. "
                   "¿Esa profundidad se está canalizando a través de una pareja cercana, "
                   "o la estás procesando en solitario?"),
        },
        "reason": "Emotional moon sign or Moon dasha",
        "options": [
            {"label": {"en": "Yes — in a relationship",  "es": "Sí — en una relación"},      "value": "in_relationship", "patra": {"marital_status": "in_relationship"}},
            {"label": {"en": "Yes — married",             "es": "Sí — casado/a"},             "value": "married",         "patra": {"marital_status": "married"}},
            {"label": {"en": "No — processing solo",      "es": "No — procesándolo sola/o"},  "value": "single",          "patra": {"marital_status": "single"}},
            {"label": {"en": "Going through a split",     "es": "Pasando por una separación"},"value": "separated",       "patra": {"marital_status": "separated"}},
        ],
        "extracts": ["marital_status"],
    },

    "relationship_general": {
        "question": {
            "en": ("To give you the most relevant reading — are you navigating life "
                   "as a solo person right now, or inside a partnership?"),
            "es": ("Para darte la lectura más relevante — ¿estás navegando la vida "
                   "en solitario ahora mismo, o dentro de una pareja?"),
        },
        "reason": "General relationship status needed",
        "options": [
            {"label": {"en": "Solo",                 "es": "En solitario"},                    "value": "single",          "patra": {"marital_status": "single"}},
            {"label": {"en": "In a relationship",    "es": "En una relación"},                 "value": "in_relationship", "patra": {"marital_status": "in_relationship"}},
            {"label": {"en": "Married",              "es": "Casado/a"},                        "value": "married",         "patra": {"marital_status": "married"}},
            {"label": {"en": "Separated / Divorced", "es": "Separado/a / Divorciado/a"},       "value": "divorced",        "patra": {"marital_status": "divorced"}},
            {"label": {"en": "Widowed",              "es": "Viudo/a"},                         "value": "widowed",         "patra": {"marital_status": "widowed"}},
        ],
        "extracts": ["marital_status"],
    },

    # ── CHILDREN ────────────────────────────────────────────────────────

    "children_jupiter_dasha": {
        "question": {
            "en": ("Your chart is pointed toward expansion right now — family, wisdom, "
                   "generativity. Is that expansion already showing up through children "
                   "in your life, or is the energy still building?"),
            "es": ("Tu carta está apuntando hacia la expansión ahora mismo — familia, "
                   "sabiduría, generatividad. ¿Esa expansión ya se está manifestando "
                   "a través de los hijos en tu vida, o la energía todavía se está "
                   "construyendo?"),
        },
        "reason": "Jupiter dasha active — 5th house themes prominent",
        "options": [
            {"label": {"en": "I have young children",     "es": "Tengo hijos pequeños"},       "value": "young_children",        "patra": {"children_status": "young_children"}},
            {"label": {"en": "My children are older",     "es": "Mis hijos ya son mayores"},   "value": "older_children",        "patra": {"children_status": "older_children"}},
            {"label": {"en": "Expecting a child",         "es": "Esperando un hijo"},          "value": "expecting",             "patra": {"children_status": "expecting"}},
            {"label": {"en": "Hoping for children",       "es": "Esperando tener hijos"},      "value": "no_children_wants",     "patra": {"children_status": "no_children_wants"}},
            {"label": {"en": "Not the path I'm on",       "es": "No es mi camino"},            "value": "no_children_by_choice", "patra": {"children_status": "no_children_by_choice"}},
        ],
        "extracts": ["children_status"],
    },

    "children_strong_jupiter": {
        "question": {
            "en": ("Your chart carries a strong signature around family and legacy. "
                   "Has that energy already manifested for you through children, "
                   "or is it still ahead?"),
            "es": ("Tu carta tiene una firma fuerte alrededor de la familia y el legado. "
                   "¿Esa energía ya se ha manifestado para ti a través de los hijos, "
                   "o todavía está por venir?"),
        },
        "reason": "Strong Jupiter placement",
        "options": [
            {"label": {"en": "Yes — I have children",     "es": "Sí — tengo hijos"},           "value": "young_children",        "patra": {"children_status": "young_children"}},
            {"label": {"en": "Children are grown",        "es": "Mis hijos ya son adultos"},   "value": "adult_children",        "patra": {"children_status": "adult_children"}},
            {"label": {"en": "Expecting soon",            "es": "Esperando pronto"},           "value": "expecting",             "patra": {"children_status": "expecting"}},
            {"label": {"en": "Still ahead for me",        "es": "Todavía está por venir"},     "value": "no_children_wants",     "patra": {"children_status": "no_children_wants"}},
            {"label": {"en": "Probably not my path",      "es": "Probablemente no es mi camino"}, "value": "no_children_by_choice", "patra": {"children_status": "no_children_by_choice"}},
        ],
        "extracts": ["children_status"],
    },

    # ── CAREER ──────────────────────────────────────────────────────────

    "career_saturn_dasha": {
        "question": {
            "en": ("Your chart right now is asking you to build something real and lasting. "
                   "Is that pressure landing on an established career, or is it helping "
                   "you figure out what to build in the first place?"),
            "es": ("Tu carta ahora mismo te pide construir algo real y duradero. "
                   "¿Esa presión está cayendo sobre una carrera establecida, o te está "
                   "ayudando a descubrir qué construir para empezar?"),
        },
        "reason": "Saturn dasha — career restructuring themes",
        "options": [
            {"label": {"en": "I'm established — refining",    "es": "Ya estoy establecido/a — refinando"}, "value": "senior_career", "patra": {"career_stage": "senior_career"}},
            {"label": {"en": "Mid-career — pushing forward",  "es": "A mitad de carrera — empujando"},     "value": "mid_career",    "patra": {"career_stage": "mid_career"}},
            {"label": {"en": "Building my own thing",         "es": "Construyendo lo mío"},                "value": "entrepreneur",  "patra": {"career_stage": "entrepreneur"}},
            {"label": {"en": "In transition — figuring it out","es": "En transición — descubriendo"},     "value": "transition",    "patra": {"career_stage": "transition"}},
            {"label": {"en": "Early in my path",              "es": "Al inicio de mi camino"},             "value": "early_career",  "patra": {"career_stage": "early_career"}},
            {"label": {"en": "Retired",                        "es": "Jubilado/a"},                        "value": "retired",       "patra": {"career_stage": "retired"}},
        ],
        "extracts": ["career_stage"],
    },

    "career_rahu_dasha": {
        "question": {
            "en": ("Your chart is running hungry, ambitious energy right now — the kind "
                   "that reaches beyond what's familiar. Is that ambition pointed at your "
                   "own venture, climbing inside an organization, or something you're "
                   "still discovering?"),
            "es": ("Tu carta está corriendo una energía hambrienta y ambiciosa ahora mismo "
                   "— del tipo que alcanza más allá de lo familiar. ¿Esa ambición apunta "
                   "a tu propio proyecto, a escalar dentro de una organización, o a algo "
                   "que todavía estás descubriendo?"),
        },
        "reason": "Rahu dasha — ambition and foreign themes",
        "options": [
            {"label": {"en": "My own business / startup",   "es": "Mi propio negocio / emprendimiento"}, "value": "entrepreneur",  "patra": {"career_stage": "entrepreneur"}},
            {"label": {"en": "Corporate — climbing",        "es": "Corporativo — escalando"},            "value": "mid_career",    "patra": {"career_stage": "mid_career"}},
            {"label": {"en": "Senior leadership",           "es": "Liderazgo senior"},                   "value": "senior_career", "patra": {"career_stage": "senior_career"}},
            {"label": {"en": "Creative / independent",      "es": "Creativo/a / independiente"},         "value": "creative",      "patra": {"career_stage": "creative"}},
            {"label": {"en": "Still discovering",           "es": "Todavía descubriendo"},               "value": "transition",    "patra": {"career_stage": "transition"}},
            {"label": {"en": "Studying / preparing",        "es": "Estudiando / preparándome"},          "value": "student",       "patra": {"career_stage": "student"}},
        ],
        "extracts": ["career_stage"],
    },

    "career_sun_mercury": {
        "question": {
            "en": ("Your chart is pointing strongly toward your professional world. "
                   "Where would you say you are in your work life right now?"),
            "es": ("Tu carta está apuntando fuertemente hacia tu mundo profesional. "
                   "¿Dónde dirías que estás en tu vida laboral ahora mismo?"),
        },
        "reason": "Sun or Mercury dasha — professional themes",
        "options": [
            {"label": {"en": "Just starting out",       "es": "Recién empezando"},               "value": "early_career",  "patra": {"career_stage": "early_career"}},
            {"label": {"en": "Established professional","es": "Profesional establecido/a"},     "value": "mid_career",    "patra": {"career_stage": "mid_career"}},
            {"label": {"en": "Running my own business", "es": "Dirigiendo mi propio negocio"}, "value": "entrepreneur",  "patra": {"career_stage": "entrepreneur"}},
            {"label": {"en": "Senior / leadership",     "es": "Senior / liderazgo"},            "value": "senior_career", "patra": {"career_stage": "senior_career"}},
            {"label": {"en": "Creative path",           "es": "Camino creativo"},                "value": "creative",      "patra": {"career_stage": "creative"}},
            {"label": {"en": "In transition",           "es": "En transición"},                  "value": "transition",    "patra": {"career_stage": "transition"}},
        ],
        "extracts": ["career_stage"],
    },

    # ── FINANCIAL ───────────────────────────────────────────────────────

    "financial_abundance_dasha": {
        "question": {
            "en": ("This is typically an expansive period financially. Is the expansion "
                   "you're sensing building on an already stable foundation, or are you "
                   "working to establish that foundation first?"),
            "es": ("Este suele ser un período expansivo en lo financiero. ¿La expansión "
                   "que estás sintiendo se construye sobre una base ya estable, o todavía "
                   "estás trabajando para establecer esa base primero?"),
        },
        "reason": "Venus or Jupiter dasha — financial expansion themes",
        "options": [
            {"label": {"en": "Already stable — growing",   "es": "Ya estable — creciendo"},            "value": "growing",    "patra": {"financial_status": "growing"}},
            {"label": {"en": "Stable — protecting it",     "es": "Estable — protegiéndolo"},           "value": "stable",     "patra": {"financial_status": "stable"}},
            {"label": {"en": "Building toward stability",  "es": "Construyendo hacia la estabilidad"}, "value": "debt",       "patra": {"financial_status": "debt"}},
            {"label": {"en": "Established — legacy focus", "es": "Establecido/a — enfoque en legado"}, "value": "wealthy",    "patra": {"financial_status": "wealthy"}},
            {"label": {"en": "In a financial transition",  "es": "En una transición financiera"},     "value": "transition", "patra": {"financial_status": "transition"}},
        ],
        "extracts": ["financial_status"],
    },

    "financial_saturn_pressure": {
        "question": {
            "en": ("This period often brings sharp financial lessons — the kind that test "
                   "what you've built. Is the lesson right now about building wealth, "
                   "protecting it, or recovering after a contraction?"),
            "es": ("Este período suele traer lecciones financieras agudas — del tipo que "
                   "ponen a prueba lo que has construido. ¿La lección ahora mismo es sobre "
                   "construir riqueza, protegerla, o recuperarte después de una contracción?"),
        },
        "reason": "Saturn dasha — financial discipline themes",
        "options": [
            {"label": {"en": "Building — working hard",    "es": "Construyendo — trabajando duro"},     "value": "stable",     "patra": {"financial_status": "stable"}},
            {"label": {"en": "Recovering — rebuilding",    "es": "Recuperándome — reconstruyendo"},      "value": "debt",       "patra": {"financial_status": "debt"}},
            {"label": {"en": "Protecting what I have",     "es": "Protegiendo lo que tengo"},            "value": "growing",    "patra": {"financial_status": "growing"}},
            {"label": {"en": "In transition financially",  "es": "En transición financiera"},           "value": "transition", "patra": {"financial_status": "transition"}},
        ],
        "extracts": ["financial_status"],
    },

    # ── HEALTH ──────────────────────────────────────────────────────────

    "health_saturn_ketu": {
        "question": {
            "en": ("Your chart is asking you to pay attention to the body right now "
                   "— a period that makes health signals louder than usual. Is your "
                   "physical energy something you're working with or working around?"),
            "es": ("Tu carta te pide prestar atención al cuerpo ahora mismo — un período "
                   "que hace que las señales de salud suenen más fuertes de lo habitual. "
                   "¿Tu energía física es algo con lo que estás trabajando o alrededor "
                   "de lo cual navegas?"),
        },
        "reason": "Saturn/Ketu dasha or Mars affliction — health awareness",
        "options": [
            {"label": {"en": "Strong — no concerns",          "es": "Fuerte — sin preocupaciones"},    "value": "excellent",     "patra": {"health_status": "excellent"}},
            {"label": {"en": "Managing something minor",      "es": "Manejando algo menor"},           "value": "minor_issues",  "patra": {"health_status": "minor_issues"}},
            {"label": {"en": "Living with a chronic thing",   "es": "Viviendo con algo crónico"},      "value": "chronic",       "patra": {"health_status": "chronic"}},
            {"label": {"en": "Recovering — rebuilding",       "es": "Recuperándome — reconstruyendo"}, "value": "recovery",      "patra": {"health_status": "recovery"}},
            {"label": {"en": "Emotional / mental health",     "es": "Salud emocional / mental"},       "value": "mental_health", "patra": {"health_status": "mental_health"}},
        ],
        "extracts": ["health_status"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Renderer
# ═══════════════════════════════════════════════════════════════════════════

# Supported language codes — everything else falls back to English.
_SUPPORTED = ("en", "es")


def _normalize_lang(language: Optional[str]) -> str:
    code = (language or "en").lower()[:2]
    return code if code in _SUPPORTED else "en"


def render_question(question_id: str, language: Optional[str] = "en") -> Optional[dict]:
    """Return the localized question + options for a given question_id.

    Shape preserves the existing consumer contract in patra_conversation.py:
      {
        "id": str,
        "question": str,          # localized
        "reason": str,            # internal only, not user-facing
        "options": [
          {"label": str, "value": str, "patra": dict},   # label localized
          ...
        ],
        "extracts": [str],
      }

    Returns None if question_id is unknown.
    """
    q = PATRA_QUESTIONS.get(question_id)
    if not q:
        return None
    code = _normalize_lang(language)

    # String-or-dict safe accessors — tolerate malformed entries in case of
    # a typo during editing (fall back to English, never crash).
    def _localized(block):
        if isinstance(block, dict):
            return block.get(code) or block.get("en") or ""
        return str(block or "")

    return {
        "id":       question_id,
        "question": _localized(q.get("question", "")),
        "reason":   q.get("reason", ""),
        "options": [
            {
                "label": _localized(opt.get("label", "")),
                "value": opt.get("value", ""),
                "patra": opt.get("patra", {}),
            }
            for opt in q.get("options", [])
        ],
        "extracts": list(q.get("extracts", [])),
    }


def list_question_ids() -> list[str]:
    """Return every question_id in the catalog (stable order by insertion)."""
    return list(PATRA_QUESTIONS.keys())


# ═══════════════════════════════════════════════════════════════════════════
# Admin editor — dropdown options per patra field
#
# The admin chart editor renders these fields as dropdowns matching the choices
# the user sees in the frontend. VALUES come straight from this catalog (the
# same stable enum keys the onboarding writes), so the dropdowns can never drift
# from production. LABELS below are curated for standalone display (the catalog's
# own labels are question-specific, e.g. "Recently out of one", which read oddly
# out of context). Order is curated; any catalog value missing a label here is
# still surfaced (derived label) so nothing becomes unselectable.
# ═══════════════════════════════════════════════════════════════════════════

_ADMIN_LABELS: dict = {
    "marital_status": [
        ("single", "Single"), ("in_relationship", "In a relationship"),
        ("married", "Married"), ("separated", "Separated / complicated"),
        ("divorced", "Divorced"), ("widowed", "Widowed"),
    ],
    "children_status": [
        ("young_children", "Young children"), ("older_children", "Older children"),
        ("adult_children", "Adult children"), ("expecting", "Expecting"),
        ("no_children_wants", "No children — hoping to"),
        ("no_children_by_choice", "No children — by choice"),
    ],
    "career_stage": [
        ("student", "Student"), ("early_career", "Early career"),
        ("mid_career", "Mid-career"), ("senior_career", "Senior / leadership"),
        ("entrepreneur", "Entrepreneur / own business"),
        ("creative", "Creative / independent"), ("transition", "In transition"),
        ("retired", "Retired"),
    ],
    "financial_status": [
        ("growing", "Growing"), ("stable", "Stable"),
        ("debt", "Building / debt"), ("wealthy", "Wealthy / legacy"),
        ("transition", "In transition"),
    ],
    "health_status": [
        ("excellent", "Excellent"), ("minor_issues", "Minor issues"),
        ("chronic", "Chronic condition"), ("recovery", "Recovering"),
        ("mental_health", "Emotional / mental health"),
    ],
}

# fields the admin edits that are NOT in the patra catalog (static choice sets)
_EXTRA_OPTIONS: dict = {
    "gender": [
        ("male", "Male"), ("female", "Female"),
        ("non_binary", "Non-binary"), ("prefer_not_to_say", "Prefer not to say"),
    ],
}


def _catalog_values() -> dict:
    """{patra_field: set(valid values)} derived live from PATRA_QUESTIONS."""
    vals: dict = {}
    for q in PATRA_QUESTIONS.values():
        for opt in q.get("options", []):
            for field, fv in (opt.get("patra") or {}).items():
                if fv:
                    vals.setdefault(field, set()).add(fv)
    return vals


def admin_field_options() -> dict:
    """{field: [{value, label}]} for the admin chart editor. Patra fields are
    validated against the live catalog so a stale label here can never inject an
    invalid code; extra fields (gender) are static."""
    catalog = _catalog_values()
    out: dict = {}
    for field, pairs in _ADMIN_LABELS.items():
        valid = catalog.get(field, set())
        seen = set()
        lst = []
        for value, label in pairs:
            if value in valid:
                lst.append({"value": value, "label": label})
                seen.add(value)
        for value in sorted(valid - seen):  # catalog gained a value we didn't label
            lst.append({"value": value, "label": value.replace("_", " ").title()})
        out[field] = lst
    for field, pairs in _EXTRA_OPTIONS.items():
        out[field] = [{"value": v, "label": l} for v, l in pairs]
    return out


__all__ = [
    "PATRA_QUESTIONS",
    "render_question",
    "list_question_ids",
    "admin_field_options",
]
