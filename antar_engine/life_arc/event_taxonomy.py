"""
antar_engine/life_arc/event_taxonomy.py
=======================================
Shared event taxonomy for past + forward cycle engines.

Each entry maps the canonical event_type (from dasha_event_mapper) to:
  category : UI bucket — WORK | RELATIONSHIP | FAMILY | RELOCATION | HEALTH
  houses   : D1 houses the event "lives in" — used by D_gate linkage check
  karaka   : primary classical karaka — used by the amplifier's karaka_match term
  title    : planet-free, jargon-free user-facing title (no Sanskrit, no house numbers)

This module is INTERNAL — planet / karaka strings here are gating signals only;
they never leave the forward engine. UI receives `title`, `category`, `window_label`,
`conviction` only.

Tier 1 (D1 only). Tier 2 will add varga-specific overrides; this module's shape
stays identical — only Varga_mult downstream changes.
"""
from __future__ import annotations

EVENT_TAXONOMY = {
    "serious_partnership_began": {
        "category": "RELATIONSHIP",
        "houses":   [7, 2, 11],
        "karaka":   "Venus",
        "title":    "A partnership window opens",
    },
    "serious_partnership_ended": {
        "category": "RELATIONSHIP",
        "houses":   [7, 8, 12],
        "karaka":   "Saturn",
        "title":    "A partnership reshapes",
    },
    "family_expansion_first": {
        "category": "FAMILY",
        "houses":   [5, 9],
        "karaka":   "Jupiter",
        "title":    "Family grows",
    },
    "family_expansion_second": {
        "category": "FAMILY",
        "houses":   [5, 9],
        "karaka":   "Jupiter",
        "title":    "Family grows again",
    },
    "major_relocation": {
        "category": "RELOCATION",
        "houses":   [4, 12, 9],
        "karaka":   "Rahu",
        "title":    "A meaningful move",
    },
    "major_acquisition": {
        "category": "WORK",
        "houses":   [4, 2, 11],
        "karaka":   "Venus",
        "title":    "A major acquisition lands",
    },
    "career_pivot": {
        "category": "WORK",
        "houses":   [10, 6, 11],
        "karaka":   "Sun",
        "title":    "Your work direction shifts",
    },
    "professional_setback": {
        "category": "WORK",
        "houses":   [10, 6, 8],
        "karaka":   "Saturn",
        "title":    "A work pressure tests you",
    },
    "financial_disruption": {
        "category": "WORK",
        "houses":   [2, 6, 8],
        "karaka":   "Saturn",
        "title":    "A money pressure builds",
    },
    "legal_entanglement": {
        "category": "WORK",
        "houses":   [6, 8, 12],
        "karaka":   "Mars",
        "title":    "A dispute or formal matter",
    },
    "loss_of_mother": {
        "category": "HEALTH",
        "houses":   [4, 8],
        "karaka":   "Moon",
        "title":    "A loss in the home",
    },
    "loss_of_father": {
        "category": "HEALTH",
        "houses":   [9, 8],
        "karaka":   "Sun",
        "title":    "A loss in the elder line",
    },
}

# Karaka-of-event mapping — used by amplifier.karaka_match.
# AmK = work/status, DK = relationship, GK = friction/health/dispute, AK = self/direction.
KARAKA_DOMAIN_MAP = {
    "AmK": ("WORK",),
    "DK":  ("RELATIONSHIP",),
    "GK":  ("HEALTH",),
    "AK":  ("WORK",),  # AK touches self-direction — often surfaces as career pivot
    "PK":  ("FAMILY",),
    "MK":  ("HEALTH",),  # Matrukaraka — health/mother
    "BK":  ("RELATIONSHIP",),  # Bhratrukaraka — siblings/peers
}


def event_target_houses(event_type: str) -> list:
    entry = EVENT_TAXONOMY.get(event_type) or {}
    return list(entry.get("houses") or [])


def event_category(event_type: str) -> str:
    entry = EVENT_TAXONOMY.get(event_type) or {}
    return entry.get("category") or "WORK"


def event_karaka_planet(event_type: str) -> str:
    entry = EVENT_TAXONOMY.get(event_type) or {}
    return entry.get("karaka") or ""


def event_title(event_type: str) -> str:
    entry = EVENT_TAXONOMY.get(event_type) or {}
    return entry.get("title") or "A meaningful moment"
