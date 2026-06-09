"""
antar_engine/dasha_activation.py
─────────────────────────────────
V2.2 Layer 2 helper used by has_domain_anchor to gate the window-path
and promise-path on REAL dasha activation for the asked life area.

Per V2.2 doctrine:
    has_anchor_via_window = bool(windows) AND dasha in ("ACTIVE", "SUPPORTIVE")
    has_anchor_via_promise = natal == "STRUCTURALLY_SUPPORTED" AND dasha == "ACTIVE"

This module gives you the `dasha` state for the area.

WHAT "DASHA ACTIVE FOR DOMAIN" MEANS:
  ACTIVE     — current MD lord OR current AD lord rules a primary or
               secondary house of the life area (sign-lordship reckoned
               from natal lagna). MD-driven activation is strongest.
  SUPPORTIVE — current MD or AD lord is itself a karaka of the area.
  INACTIVE   — neither.

CANONICAL SOURCE:
  antar_engine.life_arc.phase_analyzer.get_current_vimsottari is the
  V2.2 canonical Vimsottari read. We import it inside the function so
  this module can be loaded in environments where phase_analyzer's
  swisseph dependency isn't available (sandbox tests, etc.).

NEVER RAISES. Returns {"state": "INACTIVE", "reason": "..."} on any
failure so /predict callers can degrade gracefully.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional


# Sign lordship — sidereal. Index matches SIGNS list (0=Aries).
_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Each sign → ruling planet. Used to compute "which houses does this
# planet rule from the natal lagna."
_SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}


def _sidx(name: str) -> Optional[int]:
    try:
        return _SIGNS.index(name)
    except (ValueError, TypeError):
        return None


def _houses_ruled_by(planet: str, lagna_sign: str) -> list:
    """Return the houses (from lagna) whose cusp sign is ruled by `planet`.
    A planet usually rules 1 or 2 houses."""
    if not planet or not lagna_sign:
        return []
    lagna_idx = _sidx(lagna_sign)
    if lagna_idx is None:
        return []
    houses = []
    for offset in range(12):
        sign = _SIGNS[(lagna_idx + offset) % 12]
        if _SIGN_LORDS.get(sign) == planet:
            houses.append(offset + 1)
    return houses


def compute_dasha_state_for_area(
    chart_data: Dict[str, Any],
    birth_jd: Optional[float],
    life_area_config: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Returns {"state": "ACTIVE" | "SUPPORTIVE" | "INACTIVE",
                "md": str|None, "ad": str|None,
                "ruled_houses": {"md":[...], "ad":[...]},
                "matched_houses": [...], "reason": str}.

    Pure function. Never raises. Inputs that can't produce a verdict
    return INACTIVE with a reason string."""
    if not chart_data or not isinstance(chart_data, dict):
        return {"state": "INACTIVE", "reason": "no chart_data"}
    if birth_jd is None:
        return {"state": "INACTIVE", "reason": "no birth_jd"}

    lagna = chart_data.get("lagna") or {}
    lagna_sign = lagna.get("sign") if isinstance(lagna, dict) else ""
    if not lagna_sign:
        return {"state": "INACTIVE", "reason": "no lagna sign"}

    primary = life_area_config.get("primary")
    secondary = life_area_config.get("secondary") or []
    karakas = life_area_config.get("karaka") or []
    area_houses = set(([primary] if isinstance(primary, int) else []) + list(secondary))
    karaka_set = {str(k).strip() for k in karakas}

    # Read current Vimsottari. Import deferred so this module loads in
    # environments without swisseph.
    try:
        from antar_engine.life_arc.phase_analyzer import get_current_vimsottari
        vim = get_current_vimsottari(chart_data, float(birth_jd), now=now)
    except Exception as e:
        return {"state": "INACTIVE", "reason": f"vimsottari read failed: {e}"}

    if not isinstance(vim, dict) or vim.get("error"):
        return {"state": "INACTIVE", "reason": vim.get("error") if isinstance(vim, dict) else "no vim"}

    md = vim.get("md")
    ad = vim.get("ad")

    md_houses = _houses_ruled_by(md, lagna_sign) if md else []
    ad_houses = _houses_ruled_by(ad, lagna_sign) if ad else []

    md_match = sorted(set(md_houses) & area_houses)
    ad_match = sorted(set(ad_houses) & area_houses)

    # MD-driven activation is the strongest signal.
    if md_match:
        return {
            "state": "ACTIVE",
            "md": md, "ad": ad,
            "ruled_houses": {"md": md_houses, "ad": ad_houses},
            "matched_houses": md_match,
            "reason": f"MD lord {md} rules house(s) {md_match} of life area",
        }

    # AD lord rules an area house → ACTIVE (V2.2 narrow ACTIVE band).
    if ad_match:
        return {
            "state": "ACTIVE",
            "md": md, "ad": ad,
            "ruled_houses": {"md": md_houses, "ad": ad_houses},
            "matched_houses": ad_match,
            "reason": f"AD lord {ad} rules house(s) {ad_match} of life area",
        }

    # Karaka-touch — MD or AD lord is itself a karaka → SUPPORTIVE.
    if md in karaka_set or ad in karaka_set:
        which = md if md in karaka_set else ad
        return {
            "state": "SUPPORTIVE",
            "md": md, "ad": ad,
            "ruled_houses": {"md": md_houses, "ad": ad_houses},
            "matched_houses": [],
            "reason": f"dasha lord {which} is a karaka of the life area",
        }

    return {
        "state": "INACTIVE",
        "md": md, "ad": ad,
        "ruled_houses": {"md": md_houses, "ad": ad_houses},
        "matched_houses": [],
        "reason": f"MD={md} (rules {md_houses}), AD={ad} (rules {ad_houses}) — neither touches area",
    }
