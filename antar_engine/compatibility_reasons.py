"""
antar_engine/compatibility_reasons.py

Compatibility V2 — the 7-reason taxonomy, role config, per-reason layer weights,
per-role score modifiers, and the layer→source map. Single source of truth for
the gating; the layer mapper (compatibility_layers.compose_compat_v2) reads this.

Direction is encoded in the reason (never an exposed switch):
  employee        -> user is SENIOR (the employer/manager)   direction="user_senior"
  boss-or-manager -> user is JUNIOR (the report)              direction="user_junior"
"""

# ── reason directory ─────────────────────────────────────────────────────────
REASON_DEFINITIONS = {
    "romantic":        {"label": "Romantic partner",        "needs_role": False, "direction": None},
    "business":        {"label": "Business partner",        "needs_role": False, "direction": None},
    "cofounder":       {"label": "Cofounder",               "needs_role": False, "direction": None},
    "friend":          {"label": "Friend",                  "needs_role": False, "direction": None},
    "family":          {"label": "Family member",           "needs_role": False, "direction": None},
    "employee":        {"label": "Someone reporting to me", "needs_role": True,  "direction": "user_senior"},
    "boss-or-manager": {"label": "Someone I report to",     "needs_role": True,  "direction": "user_junior"},
}

VALID_REASONS = tuple(REASON_DEFINITIONS.keys())
ROLE_REQUIRED_REASONS = tuple(k for k, v in REASON_DEFINITIONS.items() if v["needs_role"])
VALID_ROLES = ["sales", "marketing", "finance", "managerial"]

LAYER_ORDER = ["soul", "chemistry", "public", "lifepath", "communication", "friction"]
LAYER_LABELS = {
    "soul":          "Soul Alignment",
    "chemistry":     "Chemistry & Attraction",
    "public":        "Public & Worldly Fit",
    "lifepath":      "Lifepath & Timing",
    "communication": "Communication & Trust",
    "friction":      "Friction & Growth",
}

# ── per-reason layer weights (sum to 100 within each reason) ──────────────────
REASON_WEIGHTS = {
    "romantic":        {"soul": 25, "chemistry": 25, "public": 5,  "lifepath": 15, "communication": 15, "friction": 15},
    "cofounder":       {"soul": 20, "chemistry": 5,  "public": 25, "lifepath": 25, "communication": 15, "friction": 10},
    "business":        {"soul": 10, "chemistry": 5,  "public": 30, "lifepath": 25, "communication": 20, "friction": 10},
    "friend":          {"soul": 25, "chemistry": 5,  "public": 10, "lifepath": 15, "communication": 25, "friction": 20},
    "family":          {"soul": 30, "chemistry": 0,  "public": 5,  "lifepath": 25, "communication": 20, "friction": 20},
    "employee":        {"soul": 10, "chemistry": 0,  "public": 30, "lifepath": 15, "communication": 25, "friction": 20},
    "boss-or-manager": {"soul": 10, "chemistry": 0,  "public": 25, "lifepath": 20, "communication": 25, "friction": 20},
}

# ── per-role modifiers (employee + boss-or-manager only) ──────────────────────
# Applied to the layer SCORES (not weights), then capped to 0-100.
ROLE_MODIFIERS = {
    "sales":      {"public": +5,  "communication": +5,  "friction": -5},
    "marketing":  {"communication": +10, "public": +5,  "soul": -5},
    "finance":    {"friction": +10, "lifepath": +5, "chemistry": -5},
    "managerial": {"public": +10, "lifepath": +10, "friction": -10},
}

# ── layer -> (source, intra-weight) map ───────────────────────────────────────
# Source keys resolve via compatibility_layers.resolve_source(...). These match
# the V2 contract table exactly. NOTE: friction is the 3-source classical set
# (mutual 6/8 + Nadi + growth areas); cross-chart graha drishti is Phase-2/out of
# scope here, so it is intentionally excluded.
V2_LAYER_SOURCES = {
    "soul":          [("d9_overall", 0.50), ("graha_maitri", 0.35), ("varna", 0.15)],
    "chemistry":     [("yoni", 0.40), ("venus_compatibility", 0.35), ("mars_compatibility", 0.25)],
    "public":        [("house_7", 0.40), ("house_10", 0.40), ("house_11", 0.20)],
    "lifepath":      [("dasha_timing", 0.70), ("bhakoot", 0.30)],
    "communication": [("mercury_compatibility", 0.40), ("graha_maitri", 0.30), ("gana", 0.30)],
    "friction":      [("mutual_6_8", 0.45), ("nadi_dosha", 0.35), ("growth_areas_count", 0.20)],
}

# ── DIRECTIONAL EXTENSION (employee / boss-or-manager) ────────────────────
# Asymmetric house-exchange spec per the reason-routing brief. The dominant
# 'their planets in your role-houses' term lives under the `public` layer for
# these two reasons only; the other five reasons are untouched.
DIRECTIONAL_HOUSES = {
    "employee": {
        # User is SENIOR. Read = "does THEIR chart deliver into MY 6/10/3?"
        "your_houses":  [6, 10, 3],
        "their_houses": [10, 6, 3],
        "house_weights": [1.0, 1.0, 0.6],
        "karakas":      ["Mercury", "Saturn"],
        "divisional":   "D10",
        "frame":        "execution_fit",
    },
    "boss-or-manager": {
        # User is JUNIOR. Read = "does THEIR authority advance MY 10/6?"
        "your_houses":  [10, 6],
        "their_houses": [6, 10],
        "house_weights": [1.0, 0.8],
        "karakas":      ["Sun", "Saturn"],
        "divisional":   "D10",
        "frame":        "advancement_vs_friction",
    },
}

# Per-reason override of V2_LAYER_SOURCES. Only the `public` layer changes —
# the directional term takes 0.50; the remaining 0.50 keeps the existing
# 7/10/11 sources at their original ratio (0.40/0.40/0.20 -> halved).
V2_LAYER_SOURCES_BY_REASON = {
    "employee": {
        **V2_LAYER_SOURCES,
        "public": [
            ("house_exchange_their_to_your", 0.50),
            ("house_7",  0.20),
            ("house_10", 0.20),
            ("house_11", 0.10),
        ],
    },
    "boss-or-manager": {
        **V2_LAYER_SOURCES,
        "public": [
            ("house_exchange_their_to_your", 0.50),
            ("house_10", 0.30),
            ("house_7",  0.10),
            ("house_11", 0.10),
        ],
    },
}

# Per-reason layer label overrides. Modern framing — never 'do not hire',
# never 'avoid'. Only the listed layers are renamed; unspecified layers
# fall back to LAYER_LABELS.
REASON_LAYER_LABELS = {
    "employee": {
        "public":   "Execution Fit",
        "lifepath": "Operating Rhythm",
        "friction": "Support Direction",
    },
    "boss-or-manager": {
        "public":   "Advancement",
        "lifepath": "Operating Rhythm",
        "friction": "Autonomy",
    },
}

LAYER_PASS_THRESHOLD = 65


def badge(score: int) -> str:
    if score >= 75:
        return "FLOW"
    if score >= 50:
        return "MIXED"
    return "STRAIN"


def tier(score: int) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 50:
        return "MID"
    return "LOW"


def normalize_reason(compat_type=None, mode=None, default="romantic") -> str:
    """Resolve the effective reason from compat_type (preferred) or legacy mode."""
    raw = (compat_type or mode or default or "").strip().lower()
    # tolerant aliases
    aliases = {
        "boss": "boss-or-manager", "manager": "boss-or-manager",
        "boss_or_manager": "boss-or-manager", "boss-manager": "boss-or-manager",
        "relationship": "romantic", "partner": "romantic", "marriage": "romantic",
        "co-founder": "cofounder", "co_founder": "cofounder",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in REASON_DEFINITIONS else default


def reasons_directory() -> dict:
    """Static directory for GET /api/v1/compatibility/reasons."""
    questions = {
        "romantic":        ("How are we as a couple?",                "Partnership, marriage, dating"),
        "cofounder":       ("Should we build this company together?", "Equity-tied venture partnership"),
        "business":        ("Will this partnership work?",            "Generic business or contractual"),
        "friend":          ("What is our friendship made of?",        "Non-romantic, platonic"),
        "family":          ("What does this relationship ask of me?", "Parents, siblings, in-laws, children"),
        "employee":        ("Will this person work well on my team?", "You are the employer / manager"),
        "boss-or-manager": ("Will I thrive under this person?",       "You are the report"),
    }
    role_dir = [
        {"key": "sales",      "label": "Sales / BD",    "sublabel": "Revenue, deals, pipeline"},
        {"key": "marketing",  "label": "Marketing",     "sublabel": "Brand, creative, content"},
        {"key": "finance",    "label": "Finance / Ops", "sublabel": "Accounting, controllership"},
        {"key": "managerial", "label": "Leadership",    "sublabel": "P&L, team management"},
    ]
    # Stable display order (employer/report last, per the picker design).
    order = ["romantic", "cofounder", "business", "friend", "family", "employee", "boss-or-manager"]
    out = []
    for key in order:
        d = REASON_DEFINITIONS[key]
        q, sub = questions[key]
        entry = {
            "key": key, "label": d["label"], "question": q, "sublabel": sub,
            "needs_role": d["needs_role"], "direction": d["direction"],
        }
        if d["needs_role"]:
            entry["roles"] = role_dir
        out.append(entry)
    return {"reasons": out}
