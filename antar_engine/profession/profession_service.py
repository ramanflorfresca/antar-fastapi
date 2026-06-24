"""
antar_engine/profession/profession_service.py  —  ORCHESTRATOR + SURFACE

Single entry point for "what career suits me". Backend only. NOT wired into any
endpoint yet — it surfaces nothing until the conviction gate passes and Raman
approves (require_gate=True returns eligible:False while the gate is closed).

OUTPUT CONTRACT
  surface (jargon-free, frontend-safe):
    archetype : {name, tagline, description, strength, blind_spot}
    arenas    : [{label, why}]                # 3-4 modern arenas
    conviction: "strong" | "supported" | "exploratory"
    headline  : one plain-English line
  evidence (internal only, include_evidence=True):
    full signature: D10 / Amatyakaraka-house / Karakamsa, dignities, sources,
    and the driving_factor behind each arena (traceability for validation).

JARGON RULE (project rule 12): the surface NEVER contains planet names, house
numbers, sign names, or Sanskrit. _scrub() enforces it as a backstop.
"""

from __future__ import annotations

import re

from .profession_signature import compute_profession_signature
from .profession_archetype import build_archetype_and_arenas
from .profession_gate import is_gate_open

_JARGON = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    "Amatyakaraka", "Atmakaraka", "Karakamsa", "Dasamsa", "Dashamsha",
    "Navamsa", "lagna", "nakshatra", "D10", "D9", "D1", "house", "cusp",
]
_JARGON_RE = re.compile("|".join(rf"\b{re.escape(w)}\b" for w in _JARGON),
                        re.IGNORECASE)


def _has_jargon(text: str) -> bool:
    return bool(_JARGON_RE.search(text or ""))


def _arena_why(arena: dict) -> str:
    """Plain-English 'why' for an arena — no jargon, energy-voice."""
    factor = arena.get("driving_factor", "")
    # driving_factor strings are already written jargon-free in the archetype map
    return factor or "a recurring strength in how you work"


CONVICTION_HEADLINE = {
    "strong": "Your chart points clearly at one kind of work — and backs it with real strength.",
    "supported": "There is a clear shape to the work that fits you, with solid support behind it.",
    "exploratory": "There is a recognizable direction here, though the chart asks you to test it rather than commit blind.",
}


def get_profession_read(chart_data: dict, include_evidence: bool = False,
                        require_gate: bool = True) -> dict:
    """
    Build the vocational read. While the gate is closed and require_gate=True,
    returns {"eligible": False, ...} and surfaces nothing.
    """
    if require_gate and not is_gate_open():
        return {
            "eligible": False,
            "mode": "off",
            "reason": "profession gate closed — quarantined until validated + approved",
        }

    sig = compute_profession_signature(chart_data)
    built = build_archetype_and_arenas(sig)

    conviction = sig.get("conviction", "exploratory")
    if not sig.get("strength_gate_passed", False):
        # No dignity anywhere for the driving planet -> never stronger than exploratory.
        conviction = "exploratory"

    arenas_surface = [{"label": a["label"], "why": _arena_why(a)}
                      for a in built["arenas"]]

    surface = {
        "eligible": True,
        "archetype": built["archetype"],
        "arenas": arenas_surface,
        "conviction": conviction,
        "converged": sig.get("converged", False),
        "headline": CONVICTION_HEADLINE.get(conviction, CONVICTION_HEADLINE["exploratory"]),
    }

    # Jargon backstop on every user-facing string.
    leaks = []
    for a in surface["archetype"].values():
        if isinstance(a, str) and _has_jargon(a):
            leaks.append(a)
    for a in arenas_surface:
        if _has_jargon(a["label"]) or _has_jargon(a["why"]):
            leaks.append(a["label"])
    if _has_jargon(surface["headline"]):
        leaks.append(surface["headline"])
    surface["_jargon_clean"] = not leaks

    if include_evidence:
        surface["evidence"] = {
            "dominant_planet": sig["dominant_planet"],
            "strength_gate_passed": sig["strength_gate_passed"],
            "dignity_points": sig["dignity_points"],
            "dignity_where": sig["dignity_where"],
            "convergence_count": sig["convergence_count"],
            "dominant_sources": sig["dominant_sources"],
            "d10": sig["d10"],
            "amk": sig["amk"],
            "karakamsa": sig["karakamsa"],
            "career_weights": sig["career_weights"],
            "arena_factors": [
                {"label": a["label"], "source": a["source"],
                 "driving_factor": a["driving_factor"]}
                for a in built["arenas"]
            ],
        }

    return surface
