"""
antar_engine/life_area_map.py
─────────────────────────────
WS1 of the "kill the generic read" sprint.

EXTENDS the legacy DOMAIN_HOUSE_MAP (which only carries primary house numbers)
with secondary houses + karaka planets per life area. Used by the
`has_domain_anchor` gate (domain_anchor.py) to decide whether the engine has
a domain-matched signal for the asked area, or whether the narrator must
take an honest-flat / cross-domain-redirect path.

Concern strings mirror what `antar_engine.astrological_rules.detect_concern`
returns. Anything missing falls back to "general".

This is ADDITIVE. The legacy DOMAIN_HOUSE_MAP in prashna_engine stays the
single source of truth for the prashna/yes-no engine. This map is a
superset used by /predict's anchor gate.
"""

from __future__ import annotations
from typing import Dict, List


# Keys must match the concerns returned by
# antar_engine.astrological_rules.detect_concern.
LIFE_AREA_MAP: Dict[str, Dict[str, object]] = {
    # Money flow that is luck-driven / event-driven (5 = pure speculation,
    # 11 = gains realised, 2 = liquid wealth, 8 = sudden/leveraged money,
    # 9 = luck karaka). Mercury rules speculative intellect, Jupiter
    # blesses gains, Rahu amplifies risk-taking.
    "speculation":   {"primary": 5,  "secondary": [11, 2, 8, 9], "karaka": ["Mercury", "Jupiter", "Rahu"]},

    # Land, home, real estate (4 = home, 12 = expenditure on assets,
    # 11 = gains from property).
    "property":      {"primary": 4,  "secondary": [12, 11, 2],   "karaka": ["Moon", "Mars", "Venus"]},

    # Reputation, role, public mandate.
    "career":        {"primary": 10, "secondary": [6, 11, 1, 2], "karaka": ["Sun", "Mercury", "Saturn"]},

    # General money flow.
    "finance":       {"primary": 2,  "secondary": [11, 8, 9, 6], "karaka": ["Jupiter", "Venus", "Mercury"]},

    # Long-term accumulation.
    "wealth":        {"primary": 2,  "secondary": [11, 5, 9],    "karaka": ["Jupiter", "Venus"]},

    # Money loss / drain.
    "loss":          {"primary": 12, "secondary": [6, 8, 2, 11], "karaka": ["Saturn", "Ketu", "Rahu", "Mars"]},

    # Existing marriage.
    "marriage":      {"primary": 7,  "secondary": [2, 11, 12, 8],"karaka": ["Venus", "Jupiter", "Moon"]},

    # Finding / dating love.
    "love":          {"primary": 5,  "secondary": [7, 11, 9],    "karaka": ["Venus", "Moon", "Jupiter"]},

    # Re-binding after split.
    "reconciliation":{"primary": 7,  "secondary": [5, 11, 4],    "karaka": ["Venus", "Mercury", "Moon"]},

    # Ending a partnership.
    "divorce":       {"primary": 7,  "secondary": [8, 12, 6],    "karaka": ["Saturn", "Mars", "Ketu"]},

    # Body / vitality.
    "health":        {"primary": 6,  "secondary": [1, 8, 12],    "karaka": ["Sun", "Moon", "Mars", "Saturn"]},

    # Moving country / long-distance.
    "foreign":       {"primary": 12, "secondary": [9, 3, 11, 4], "karaka": ["Rahu", "Moon", "Jupiter"]},

    # Dharma / meaning / inner work.
    "spiritual":     {"primary": 9,  "secondary": [12, 5, 4, 8], "karaka": ["Jupiter", "Ketu", "Saturn"]},

    # Children / family.
    "family":        {"primary": 4,  "secondary": [2, 7, 9, 5],  "karaka": ["Moon", "Venus", "Jupiter"]},
    "children":      {"primary": 5,  "secondary": [9, 2, 11],    "karaka": ["Jupiter", "Moon", "Mercury"]},

    # Catch-all — keep wide so general questions still resolve.
    "general":       {"primary": 1,  "secondary": [10, 4, 7, 11, 2], "karaka": ["Sun", "Moon", "Jupiter"]},
}


def get_life_area(concern: str) -> Dict[str, object]:
    """Return the LIFE_AREA_MAP row for a concern, falling back to general."""
    if not concern:
        return LIFE_AREA_MAP["general"]
    return LIFE_AREA_MAP.get(str(concern).strip().lower(), LIFE_AREA_MAP["general"])


def area_houses(concern: str) -> List[int]:
    """All houses (primary + secondary) bound to the asked area."""
    cfg = get_life_area(concern)
    out: List[int] = []
    p = cfg.get("primary")
    if isinstance(p, int):
        out.append(p)
    for s in cfg.get("secondary", []) or []:
        if isinstance(s, int) and s not in out:
            out.append(s)
    return out


def area_karakas(concern: str) -> List[str]:
    """Karaka planet names (canonical capitalised) for the asked area."""
    cfg = get_life_area(concern)
    return [str(k) for k in (cfg.get("karaka") or [])]
