"""
antar_engine/remedy_selector.py

Thin wrapper that bridges main.py's call signature to remedy_engine.
Also the home of the cross-system priority logic that unifies:
  - Lal Kitab annual (Varshphal) remedies
  - Dasha-based remedies (remedy_engine)
  - D-9 vargottama strength signal

HOW THIS FILE FITS:
  main.py /predict calls:
    remedy_selector.select_remedies(supabase, chart_data, dashas,
                                     transits, user_age, question)

  This module:
    1. Maps the question → concern domain
    2. Reads lal_kitab_data from chart_data if present
    3. Runs the 4-priority selection:
       Priority 1 — all 3 systems agree planet is challenged → convergence
       Priority 2 — dasha lord is weak (debilitated/combust/retrograde)
       Priority 3 — LK annual placement is challenging for this concern
       Priority 4 — amplify the strongest supported planet
    4. Returns list[dict] in the same format as remedy_engine._build_remedy()
    5. Never exposes system names to the LLM or frontend
       (the source is recorded internally for tracking, not shown)
"""

from __future__ import annotations
from typing import Optional
import re

from antar_engine.remedy_engine import (
    select_remedies as _engine_select,
    PLANET_REMEDIES,
    _build_remedy,
    _get_energy_language,
    DOMAIN_REMEDY_FOCUS,
)
from antar_engine.d_charts_calculator import DEBILITATION, NATURAL_BENEFICS

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN DETECTION
# Maps free-text question → concern domain used everywhere else
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "career":    ["career", "job", "work", "profession", "business", "promotion",
                  "office", "boss", "salary", "professional"],
    "wealth":    ["money", "wealth", "finance", "income", "invest", "savings",
                  "financial", "rich", "poor", "debt", "loan"],
    "marriage":  ["marriage", "wedding", "spouse", "husband", "wife", "married",
                  "divorce", "partner", "relationship", "love marriage"],
    "love":      ["love", "romance", "crush", "boyfriend", "girlfriend", "dating",
                  "heart", "feeling", "attraction"],
    "health":    ["health", "illness", "sick", "disease", "body", "pain",
                  "hospital", "doctor", "medicine", "recover"],
    "children":  ["child", "children", "baby", "pregnancy", "pregnant",
                  "son", "daughter", "fertility", "conceive"],
    "spiritual": ["spiritual", "meditation", "god", "temple", "dharma", "karma",
                  "soul", "moksha", "purpose", "meaning"],
    "property":  ["property", "house", "home", "land", "flat", "apartment",
                  "real estate", "buy", "rent"],
    "education": ["study", "exam", "education", "college", "degree",
                  "university", "learn", "school"],
}

LK_DOMAIN_PLANETS = {
    "career":    ["Sun", "Saturn", "Mercury"],
    "wealth":    ["Jupiter", "Venus", "Moon"],
    "marriage":  ["Venus", "Jupiter", "Moon"],
    "love":      ["Venus", "Moon"],
    "health":    ["Saturn", "Mars", "Sun"],
    "children":  ["Jupiter", "Moon"],
    "spiritual": ["Ketu", "Saturn", "Jupiter"],
    "property":  ["Mars", "Saturn", "Moon"],
    "education": ["Mercury", "Jupiter"],
    "general":   ["Jupiter", "Moon", "Mercury"],
}

BENEFIC_ANNUAL_HOUSES     = {1, 2, 4, 5, 7, 9, 10, 11}
CHALLENGING_ANNUAL_HOUSES = {6, 8, 12}


def _detect_domain(question: str) -> str:
    q = question.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return domain
    return "general"


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-SYSTEM PRIORITY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _lk_placements(chart_data: dict) -> dict:
    """Extract LK annual placements from chart_data.lal_kitab_data if present."""
    lk = chart_data.get("lal_kitab_data") or {}
    return lk.get("placements") or {}


def _planet_is_weak_dasha(planet: str, chart_data: dict) -> bool:
    """True if the planet is combust or in deep debilitation in natal chart."""
    pdata = chart_data.get("planets", {}).get(planet, {})
    if pdata.get("is_combust"):
        return True
    if pdata.get("sign") == DEBILITATION.get(planet, ""):
        return True
    # retrograde_state mandatara = near station = intensified weakness
    if pdata.get("retrograde_state") in ("mandatara", "anuvakra"):
        return True
    return False


def _planet_is_vargottama(planet: str, chart_data: dict) -> bool:
    """True if planet has same D-1 and D-9 sign (1.5× strength)."""
    return chart_data.get("planets", {}).get(planet, {}).get("is_vargottama", False)


def _convergence_score(planet: str, domain: str,
                        chart_data: dict, dashas: dict,
                        lk_placements: dict) -> int:
    """
    Score 0–3 counting how many systems flag this planet as challenged:
      1 point — LK annual placement in challenging house (6/8/12)
      1 point — natal planet is combust / debilitated / near station
      1 point — this planet IS the active Mahadasha lord AND it's weak
    """
    score = 0
    house = lk_placements.get(planet)
    if house and house in CHALLENGING_ANNUAL_HOUSES:
        score += 1
    if _planet_is_weak_dasha(planet, chart_data):
        score += 1
    # Active mahadasha lord
    current_lord = (dashas.get("vimsottari") or [{}])[0].get("lord_or_sign", "")
    if planet == current_lord and _planet_is_weak_dasha(planet, chart_data):
        score += 1
    return score


def _select_by_priority(domain: str, chart_data: dict,
                         dashas: dict, patra=None) -> list[dict]:
    """
    4-priority selection. Returns up to 3 remedy dicts.
    Each dict has 'source' key ('convergence'/'dasha'/'lal_kitab'/'amplify')
    for internal tracking — never shown to the user.
    """
    lk_pl   = _lk_placements(chart_data)
    planets = LK_DOMAIN_PLANETS.get(domain, LK_DOMAIN_PLANETS["general"])
    results = []

    # ── PRIORITY 1: all 3 systems agree (convergence score == 3) ──────────
    p1_planets = [p for p in planets
                  if _convergence_score(p, domain, chart_data, dashas, lk_pl) >= 3]
    for p in p1_planets[:1]:
        r = _build_remedy(planet=p, remedy_type="pacify", domain=domain, patra=patra)
        if r:
            r["source"] = "convergence"
            r["priority_label"] = "All timing systems point here"
            results.append(r)

    if len(results) >= 3:
        return results[:3]

    # ── PRIORITY 2: active dasha lord is weak ─────────────────────────────
    current_lord = (dashas.get("vimsottari") or [{}])[0].get("lord_or_sign", "")
    if current_lord and current_lord not in [r["planet"] for r in results]:
        if _planet_is_weak_dasha(current_lord, chart_data):
            r = _build_remedy(planet=current_lord, remedy_type="pacify",
                               domain=domain, patra=patra)
            if r:
                r["source"] = "dasha"
                r["priority_label"] = "Your current chapter needs support"
                results.append(r)

    if len(results) >= 3:
        return results[:3]

    # ── PRIORITY 3: LK annual planet in challenging house ─────────────────
    p3_planets = [
        p for p in planets
        if lk_pl.get(p) in CHALLENGING_ANNUAL_HOUSES
        and p not in [r["planet"] for r in results]
    ]
    for p in p3_planets[:1]:
        r = _build_remedy(planet=p, remedy_type="pacify", domain=domain, patra=patra)
        if r:
            r["source"] = "lal_kitab"
            r["priority_label"] = "This year's clearing practice"
            results.append(r)

    if len(results) >= 3:
        return results[:3]

    # ── PRIORITY 4: amplify strongest planet (vargottama + benefic LK house)
    p4_planets = [
        p for p in planets
        if lk_pl.get(p) in BENEFIC_ANNUAL_HOUSES
        and _planet_is_vargottama(p, chart_data)
        and p not in [r["planet"] for r in results]
    ]
    if not p4_planets:
        # fallback: any planet in benefic annual house
        p4_planets = [
            p for p in planets
            if lk_pl.get(p) in BENEFIC_ANNUAL_HOUSES
            and p not in [r["planet"] for r in results]
        ]
    for p in p4_planets[:1]:
        r = _build_remedy(planet=p, remedy_type="strengthen", domain=domain, patra=patra)
        if r:
            r["source"] = "amplify"
            r["priority_label"] = "Amplify what's already working"
            results.append(r)

    if results:
        return results[:3]

    # ── FALLBACK: delegate to remedy_engine with domain + weak dasha lord ──
    return _engine_select(
        domain=domain,
        chart_data=chart_data,
        dashas=dashas,
        patra=patra,
        limit=3,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — called by main.py
# ─────────────────────────────────────────────────────────────────────────────

def select_remedies(
    supabase,          # passed by main.py, not used here (future: store selections)
    chart_data: dict,
    dashas: dict,
    transits: dict,    # passed by main.py, reserved for future transit-based logic
    user_age: int,
    question: str,
    patra=None,
    limit: int = 3,
) -> list[dict]:
    """
    Entry point called by main.py /predict.
    Runs 4-priority cross-system selection and returns remedy list.

    The 'source' field on each remedy is for internal tracking only.
    The LLM and frontend never see it — they see 'priority_label' and
    'energy_language' only.
    """
    domain = _detect_domain(question)
    remedies = _select_by_priority(domain, chart_data, dashas, patra)
    return remedies[:limit]
