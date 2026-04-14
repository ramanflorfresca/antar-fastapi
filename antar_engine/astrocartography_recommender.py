#!/usr/bin/env python3
"""
antar_engine/astrocartography_recommender.py
=============================================
City recommendation engine for Mapa Mundial.

Takes the user's astrocartography data + current dashas + intent
and returns ranked cities with astrological reasoning.

ENTRY POINT:
  recommend_cities(chart_record, dashas, intent, region, language, top_n=5)

INTENTS:
  startup      — Jupiter DC + Mercury ASC + Rahu ASC/MC + Sun MC
  wealth       — Jupiter MC/ASC + Rahu ASC/MC + Venus IC + Sun IC
  billionaire  — Jupiter MC + Rahu ASC/MC + Sun MC (public wealth)
  career       — Sun MC + Saturn MC + Jupiter MC + Mercury MC
  relationships — Venus DC + Moon DC + Jupiter DC
  health       — Moon ASC + Venus ASC + Jupiter ASC
  spiritual    — Ketu ASC/IC + Moon IC + Jupiter IC
  general      — all planets, all lines

REGIONS:
  latam   — Mexico, Colombia, Brazil, Argentina, Chile, Peru, Uruguay, Paraguay, etc.
  europe  — UK, Germany, France, Spain, Italy, Netherlands, etc.
  asia    — India, Japan, Singapore, China, South Korea, etc.
  middleeast — UAE, Saudi Arabia, Qatar, Israel, Jordan, etc.
  africa  — Nigeria, Kenya, South Africa, Ghana, etc.
  north_america — USA, Canada, Mexico
  global  — all cities

Place at: ~/antarai/antar_engine/astrocartography_recommender.py
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

# Which planets and line types matter for each intent
# Format: {planet: {line_type: weight}}
INTENT_WEIGHTS: Dict[str, Dict[str, Dict[str, float]]] = {
    "startup": {
        "Jupiter": {"DC": 1.0, "MC": 0.9, "ASC": 0.7},
        "Mercury": {"ASC": 1.0, "MC": 0.9, "DC": 0.8},
        "Rahu":    {"ASC": 1.0, "MC": 0.9, "IC": 0.6},
        "Sun":     {"MC": 0.9, "IC": 0.7},
        "Mars":    {"MC": 0.7, "ASC": 0.6},
        "Venus":   {"DC": 0.7, "IC": 0.5},
    },
    "wealth": {
        "Jupiter": {"MC": 1.0, "ASC": 0.9, "IC": 0.8, "DC": 0.7},
        "Venus":   {"IC": 1.0, "DC": 0.9, "ASC": 0.7},
        "Rahu":    {"MC": 1.0, "ASC": 0.9, "IC": 0.7},
        "Sun":     {"MC": 0.8, "IC": 0.7},
        "Mercury": {"MC": 0.7, "DC": 0.6},
    },
    "billionaire": {
        "Jupiter": {"MC": 1.0, "ASC": 0.9},
        "Rahu":    {"MC": 1.0, "ASC": 0.9},
        "Sun":     {"MC": 0.9},
        "Saturn":  {"MC": 0.7},  # billionaires often have Saturn MC (discipline at top)
        "Venus":   {"MC": 0.6},
    },
    "career": {
        "Sun":     {"MC": 1.0, "IC": 0.6},
        "Saturn":  {"MC": 0.9, "ASC": 0.7},
        "Jupiter": {"MC": 0.9, "DC": 0.7},
        "Mercury": {"MC": 0.8, "ASC": 0.7},
        "Mars":    {"MC": 0.8, "ASC": 0.6},
    },
    "relationships": {
        "Venus":   {"DC": 1.0, "ASC": 0.9, "IC": 0.7},
        "Moon":    {"DC": 1.0, "IC": 0.8},
        "Jupiter": {"DC": 0.9, "ASC": 0.7},
        "Sun":     {"DC": 0.6},
    },
    "health": {
        "Moon":    {"ASC": 1.0, "IC": 0.8},
        "Venus":   {"ASC": 0.9, "IC": 0.7},
        "Jupiter": {"ASC": 0.9, "IC": 0.7},
        "Sun":     {"ASC": 0.7},
        "Saturn":  {"ASC": -0.5},  # Saturn ASC = health challenges
        "Mars":    {"ASC": -0.3},  # Mars ASC = injury risk
    },
    "spiritual": {
        "Ketu":    {"ASC": 1.0, "IC": 1.0, "MC": 0.8},
        "Moon":    {"IC": 0.9, "ASC": 0.7},
        "Jupiter": {"IC": 0.9, "ASC": 0.7},
        "Saturn":  {"IC": 0.7},
        "Neptune": {"ASC": 0.8, "IC": 0.8},
    },
    "general": {
        "Jupiter": {"MC": 0.9, "ASC": 0.8, "DC": 0.8, "IC": 0.7},
        "Venus":   {"ASC": 0.8, "DC": 0.8, "IC": 0.7},
        "Mercury": {"ASC": 0.7, "MC": 0.7, "DC": 0.6},
        "Sun":     {"MC": 0.7, "ASC": 0.6},
        "Moon":    {"IC": 0.6, "DC": 0.6},
        "Rahu":    {"ASC": 0.6, "MC": 0.6},
        "Saturn":  {"MC": 0.5},
        "Mars":    {"MC": 0.5, "ASC": 0.5},
    },
}

# Region filters — city name fragments
REGION_FILTERS: Dict[str, List[str]] = {
    "latam": [
        "Mexico", "Colombia", "Brazil", "Argentina", "Chile", "Peru",
        "Uruguay", "Paraguay", "Bolivia", "Ecuador", "Venezuela",
        "Guatemala", "Costa Rica", "Panama", "Honduras", "Nicaragua",
        "Monterrey", "Guadalajara", "Mexico City", "Buenos Aires",
        "Montevideo", "Asuncion", "Bogota", "Lima", "Santiago",
        "Medellin", "Cali", "Cartagena",
    ],
    "europe": [
        "UK", "Germany", "France", "Spain", "Italy", "Netherlands",
        "Portugal", "Switzerland", "Austria", "Belgium", "Sweden",
        "Norway", "Denmark", "Finland", "Poland", "Czech", "Hungary",
        "Romania", "Bulgaria", "Croatia", "Serbia", "Greece", "Ireland",
        "Scotland", "London", "Paris", "Berlin", "Madrid", "Rome",
        "Amsterdam", "Vienna", "Zurich", "Geneva", "Barcelona",
        "Milan", "Munich", "Prague", "Warsaw", "Budapest", "Lisbon",
        "Oslo", "Stockholm", "Helsinki", "Brussels", "Dublin",
        "Tallinn", "Riga", "Vilnius", "Ljubljana", "Zagreb",
        "Belgrade", "Sofia", "Bucharest", "Edinburgh",
    ],
    "asia": [
        "India", "Japan", "China", "Singapore", "South Korea", "Taiwan",
        "Thailand", "Vietnam", "Indonesia", "Malaysia", "Philippines",
        "Bangladesh", "Nepal", "Sri Lanka", "Pakistan", "Kazakhstan",
        "Tokyo", "Shanghai", "Seoul", "Taipei", "Bangkok", "Mumbai",
        "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
        "Jaipur", "Varanasi", "Rishikesh", "Goa", "Karachi", "Lahore",
        "Dhaka", "Colombo", "Kathmandu", "Almaty", "Novosibirsk",
        "Busan",
    ],
    "middleeast": [
        "UAE", "Saudi Arabia", "Qatar", "Israel", "Jordan", "Lebanon",
        "Iran", "Kuwait", "Oman", "Bahrain", "Turkey", "Egypt",
        "Doha", "Dubai", "Riyadh", "Jeddah", "Jerusalem", "Beirut",
        "Amman", "Tehran", "Kuwait City",
    ],
    "africa": [
        "Nigeria", "Kenya", "South Africa", "Ghana", "Ethiopia",
        "Tanzania", "Uganda", "Senegal", "Morocco", "Tunisia",
        "Ivory Coast", "Lagos", "Nairobi", "Cape Town", "Johannesburg",
        "Accra", "Addis Ababa", "Dar es Salaam", "Kampala", "Dakar",
        "Casablanca", "Marrakech", "Tunis", "Abidjan",
    ],
    "north_america": [
        "USA", "Canada", "Mexico",
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
        "San Francisco", "Seattle", "Austin", "Denver", "Las Vegas",
        "Toronto", "Vancouver", "Montreal", "Calgary",
        "Monterrey", "Mexico City", "Guadalajara",
    ],
    "global": [],  # empty = no filter, include all
}

# Line type human descriptions
LINE_DESCRIPTIONS: Dict[str, str] = {
    "MC":  "public authority and career recognition",
    "IC":  "private foundation and inner wealth",
    "ASC": "personal energy, identity, and vitality",
    "DC":  "partnerships, investors, and alliances",
}

# Planet meanings for natural language
PLANET_MEANINGS: Dict[str, str] = {
    "Jupiter": "expansion, opportunity, wisdom, investors, luck",
    "Venus":   "partnerships, creativity, luxury, harmony",
    "Mercury": "communication, contracts, networks, technology",
    "Sun":     "authority, recognition, government, leadership",
    "Mars":    "energy, initiative, competition, speed",
    "Saturn":  "discipline, structure, longevity, institutional backing",
    "Moon":    "public appeal, emotional resonance, fluctuating opportunity",
    "Rahu":    "disruption, foreign capital, unconventional growth, technology",
    "Ketu":    "past-life skills, research, spiritual insight, detachment",
}


# ---------------------------------------------------------------------------
# 2. Core scoring function
# ---------------------------------------------------------------------------

def _score_city(
    city_data: Dict[str, Any],
    intent: str,
    current_dasha_planet: str = "",
    current_ad_planet: str = "",
) -> Tuple[float, List[Dict]]:
    """
    Score a city for a given intent.
    Returns (total_score, active_lines_list).
    """
    weights = INTENT_WEIGHTS.get(intent, INTENT_WEIGHTS["general"])
    total_score = 0.0
    active_lines = []

    for planet, lines in city_data.items():
        planet_weights = weights.get(planet, {})
        for line_type, strength in lines.items():
            if not isinstance(strength, (int, float)):
                continue
            line_weight = planet_weights.get(line_type, 0.0)
            if line_weight == 0.0:
                continue  # not relevant for this intent

            weighted = float(strength) * line_weight

            # Dasha alignment bonus — current dasha planet's line = +30%
            dasha_bonus = 0.0
            dasha_note = ""
            if planet == current_ad_planet:
                dasha_bonus = weighted * 0.3
                dasha_note = f"ACTIVE: current AD ({current_ad_planet})"
            elif planet == current_dasha_planet:
                dasha_bonus = weighted * 0.2
                dasha_note = f"ACTIVE: current MD ({current_dasha_planet})"

            total_score += weighted + dasha_bonus

            active_lines.append({
                "planet": planet,
                "line": line_type,
                "strength": round(float(strength), 3),
                "weighted_score": round(weighted + dasha_bonus, 3),
                "line_description": LINE_DESCRIPTIONS.get(line_type, ""),
                "planet_meaning": PLANET_MEANINGS.get(planet, ""),
                "dasha_note": dasha_note,
            })

    # Sort by weighted score descending
    active_lines.sort(key=lambda x: x["weighted_score"], reverse=True)
    return round(total_score, 3), active_lines


# ---------------------------------------------------------------------------
# 3. City filter
# ---------------------------------------------------------------------------

def _filter_cities_by_region(
    astro_data: Dict[str, Any],
    region: str,
) -> Dict[str, Any]:
    """Filter astrocartography cities by region."""
    if region == "global" or not region:
        return astro_data

    fragments = REGION_FILTERS.get(region.lower(), [])
    if not fragments:
        return astro_data

    return {
        city: data
        for city, data in astro_data.items()
        if any(f.lower() in city.lower() for f in fragments)
    }


# ---------------------------------------------------------------------------
# 4. Natural language builder
# ---------------------------------------------------------------------------

def _build_city_explanation(
    city: str,
    score: float,
    active_lines: List[Dict],
    intent: str,
    language: str = "en",
) -> str:
    """Build a 1-2 sentence natural language explanation for a city ranking."""
    if not active_lines:
        return f"{city} has minimal planetary activation for {intent}."

    top = active_lines[0]
    second = active_lines[1] if len(active_lines) > 1 else None

    dasha_active = [l for l in active_lines if l.get("dasha_note")]

    if language == "es":
        if dasha_active:
            d = dasha_active[0]
            return (
                f"{city} activa {d['planet']} {d['line']} ({d['strength']}) — "
                f"tu período actual de {d['planet']} amplifica esto directamente. "
                f"{top['planet_meaning'].split(',')[0].capitalize()}."
            )
        return (
            f"{city} activa {top['planet']} {top['line']} ({top['strength']}) — "
            f"{top['planet_meaning'].split(',')[0]}. "
            + (f"También {second['planet']} {second['line']} para {second['planet_meaning'].split(',')[0]}." if second else "")
        )
    else:
        if dasha_active:
            d = dasha_active[0]
            return (
                f"{city} activates your {d['planet']} {d['line']} line ({d['strength']}) — "
                f"your current {d['planet']} period amplifies this directly. "
                f"{top['planet_meaning'].split(',')[0].capitalize()} energy is strong here."
            )
        return (
            f"{city} activates {top['planet']} {top['line']} ({top['strength']}) — "
            f"{top['planet_meaning'].split(',')[0]}. "
            + (f"Also {second['planet']} {second['line']} for {second['planet_meaning'].split(',')[0]}." if second else "")
        )


# ---------------------------------------------------------------------------
# 5. Main entry point
# ---------------------------------------------------------------------------

def recommend_cities(
    chart_record: Dict[str, Any],
    dashas: Dict[str, Any],
    intent: str = "general",
    region: str = "global",
    language: str = "en",
    top_n: int = 5,
) -> Dict[str, Any]:
    """
    Recommend best cities for a given intent based on astrocartography + dasha alignment.

    Args:
        chart_record: full charts row from Supabase
        dashas:       output of _fetch_dashas() — {vimsottari: {current_md, current_ad, ...}}
        intent:       startup | wealth | billionaire | career | relationships | health | spiritual | general
        region:       latam | europe | asia | middleeast | africa | north_america | global
        language:     en | es
        top_n:        number of cities to return

    Returns:
        {
          "intent": "startup",
          "region": "latam",
          "top_cities": [...],
          "dasha_context": "Current Mars MD ends Aug 2026, Rahu MD starts. Rahu lines = highest priority.",
          "global_insight": "...",
          "no_data_note": "..." (if no cities found for region)
        }
    """
    astro_data = chart_record.get("astrocartography_data") or {}
    if not isinstance(astro_data, dict) or not astro_data:
        return {"error": "No astrocartography data available for this chart"}

    # Get current dasha planets
    vim = dashas.get("vimsottari", {})
    current_md = (vim.get("current_md") or {}).get("planet", "")
    current_ad = (vim.get("current_ad") or {}).get("planet", "")
    next_md = (vim.get("next_md") or {}).get("planet", "")
    next_md_start = ((vim.get("upcoming_md") or [{}])[0]).get("start", "") if vim.get("upcoming_md") else ""

    # Filter by region
    filtered = _filter_cities_by_region(astro_data, region)
    if not filtered:
        return {
            "intent": intent,
            "region": region,
            "top_cities": [],
            "no_data_note": f"No cities found in {region} in your astrocartography data. Try 'global' for worldwide results.",
        }

    # Score all cities
    scored = []
    for city, city_data in filtered.items():
        score, active_lines = _score_city(city_data, intent, current_md, current_ad)
        if score > 0:
            scored.append({
                "city": city,
                "score": score,
                "active_lines": active_lines,
                "explanation": _build_city_explanation(city, score, active_lines, intent, language),
            })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_cities = scored[:top_n]

    # Build dasha context
    dasha_context_parts = []
    if current_md:
        dasha_context_parts.append(f"Current MD: {current_md}")
    if current_ad:
        dasha_context_parts.append(f"Current AD: {current_ad}")
    if next_md and next_md_start:
        dasha_context_parts.append(f"Next MD: {next_md} from {next_md_start[:10]}")

    # Check if next MD has stronger city presence
    next_md_cities = []
    if next_md:
        for city, city_data in filtered.items():
            if next_md in city_data:
                lines = city_data[next_md]
                best_line = max(lines.items(), key=lambda x: x[1])
                next_md_cities.append(f"{city} ({next_md} {best_line[0]} {best_line[1]:.2f})")
        next_md_cities.sort()

    # Global insight
    if language == "es":
        global_insight = f"Las ciudades con líneas de {current_ad or current_md} activas son las más poderosas ahora mismo."
        if next_md and next_md_cities:
            global_insight += f" Cuando empiece {next_md} MD ({next_md_start[:10]}), prioriza: {', '.join(next_md_cities[:2])}."
    else:
        global_insight = f"Cities with active {current_ad or current_md} lines are most powerful right now."
        if next_md and next_md_cities:
            global_insight += f" When {next_md} MD starts ({next_md_start[:10]}), prioritize: {', '.join(next_md_cities[:2])}."

    return {
        "intent": intent,
        "region": region,
        "dasha_context": " | ".join(dasha_context_parts),
        "top_cities": top_cities,
        "global_insight": global_insight,
        "cities_scored": len(scored),
        "cities_total_in_region": len(filtered),
    }


# ---------------------------------------------------------------------------
# 6. Smoke test
# ---------------------------------------------------------------------------

def _smoke_test():
    print("Running astrocartography_recommender smoke test...\n")

    # Fake chart_record with Raman's confirmed real data
    fake_record = {
        "astrocartography_data": {
            "Monterrey, Mexico": {"Sun": {"IC": 0.977}, "Jupiter": {"DC": 0.533}},
            "Mexico City, Mexico": {"Sun": {"IC": 0.79}, "Jupiter": {"DC": 0.524}},
            "Guadalajara, Mexico": {"Sun": {"IC": 0.54}},
            "Houston, USA": {"Ketu": {"MC": 0.978}, "Rahu": {"IC": 0.69}, "Venus": {"IC": 0.987}, "Jupiter": {"DC": 0.906}},
            "Austin, USA": {"Sun": {"IC": 0.57}, "Ketu": {"MC": 0.627}, "Venus": {"IC": 0.614}, "Jupiter": {"DC": 0.876}},
            "London, UK": {"Mars": {"ASC": 0.925}, "Jupiter": {"IC": 0.739}, "Mercury": {"ASC": 0.976}},
            "Buenos Aires, Argentina": {},
            "Bogota, Colombia": {},
        }
    }
    fake_dashas = {
        "vimsottari": {
            "current_md": {"planet": "Mars", "end": "2026-08-13"},
            "current_ad": {"planet": "Moon", "end": "2026-08-13"},
            "upcoming_md": [{"planet": "Rahu", "start": "2026-08-13"}],
        }
    }

    # Test 1: LATAM startup
    result = recommend_cities(fake_record, fake_dashas, intent="startup", region="latam", language="en")
    assert result["cities_scored"] > 0, "FAIL: no cities scored"
    assert result["top_cities"][0]["city"] == "Monterrey, Mexico", f"FAIL: expected Monterrey first, got {result['top_cities'][0]['city']}"
    print("✅ Test 1: LATAM startup — Monterrey ranked first")

    # Test 2: Global wealth
    result2 = recommend_cities(fake_record, fake_dashas, intent="wealth", region="global", language="en")
    top_city = result2["top_cities"][0]["city"]
    assert "Houston" in top_city, f"FAIL: expected Houston first for wealth, got {top_city}"
    print("✅ Test 2: Global wealth — Houston ranked first")

    # Test 3: Spanish output
    result3 = recommend_cities(fake_record, fake_dashas, intent="startup", region="latam", language="es")
    assert "activa" in result3["top_cities"][0]["explanation"]
    print("✅ Test 3: Spanish explanations working")

    # Test 4: No data region
    result4 = recommend_cities(fake_record, fake_dashas, intent="startup", region="africa", language="en")
    assert "no_data_note" in result4 or result4["cities_scored"] == 0
    print("✅ Test 4: Empty region handled gracefully")

    print("\n✅ All smoke tests passed.")


if __name__ == "__main__":
    _smoke_test()
