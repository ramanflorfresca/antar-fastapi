"""
antar_engine/astrocartography_recommender.py
=============================================
Astrocartography city recommendation engine — v4 (Apr 14 2026)

Scoring architecture (applied in order):
  1. Line scoring    — planet × line_type × strength × intent_weight
  2. Dasha alignment — ×1.2 current MD, ×1.5 next MD (choosing for 18 years)
  3. Yoga amplification — ×1.3 if Dhana Yoga planets both present
  4. Paran detection — ×1.5 for major wealth parans

Stay-vs-move rule:
  current_city_score > 70th percentile of all cities → "stay"
  else → "move to top city"

DeepSeek writes the narrative from the Python ranking.
Python never writes prose. DeepSeek never calculates scores.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Intent weights: planet → line_type → weight
# ---------------------------------------------------------------------------
INTENT_WEIGHTS: Dict[str, Dict[str, Dict[str, float]]] = {
    "startup": {
        "Jupiter": {"DC": 1.0, "MC": 0.9, "ASC": 0.8, "IC": 0.6},
        "Mercury": {"ASC": 1.0, "MC": 0.9, "DC": 0.8, "IC": 0.5},
        "Rahu":    {"ASC": 1.0, "MC": 0.95, "DC": 0.7, "IC": 0.6},
        "Sun":     {"MC": 0.9, "ASC": 0.7, "IC": 0.6, "DC": 0.6},
        "Mars":    {"ASC": 0.8, "MC": 0.7, "IC": 0.5, "DC": 0.5},
        "Venus":   {"DC": 0.8, "IC": 0.7, "ASC": 0.6, "MC": 0.5},
        "Saturn":  {"MC": 0.6, "ASC": 0.5, "IC": 0.5, "DC": 0.4},
        "Moon":    {"DC": 0.6, "IC": 0.5, "ASC": 0.5, "MC": 0.4},
        "Ketu":    {"MC": 0.5, "ASC": 0.4, "IC": 0.4, "DC": 0.3},
    },
    "billionaire": {
        "Rahu":    {"MC": 1.0, "ASC": 0.95, "DC": 0.7, "IC": 0.65},
        "Jupiter": {"MC": 1.0, "ASC": 0.9, "DC": 0.8, "IC": 0.7},
        "Sun":     {"MC": 0.9, "ASC": 0.7, "DC": 0.6, "IC": 0.5},
        "Saturn":  {"MC": 0.8, "ASC": 0.6, "DC": 0.5, "IC": 0.5},
        "Venus":   {"MC": 0.7, "DC": 0.7, "IC": 0.8, "ASC": 0.6},
        "Mercury": {"MC": 0.7, "ASC": 0.6, "DC": 0.6, "IC": 0.4},
        "Mars":    {"MC": 0.6, "ASC": 0.6, "DC": 0.4, "IC": 0.4},
        "Moon":    {"MC": 0.5, "DC": 0.5, "ASC": 0.4, "IC": 0.4},
        "Ketu":    {"MC": 0.4, "ASC": 0.4, "IC": 0.3, "DC": 0.3},
    },
    "wealth": {
        "Jupiter": {"IC": 1.0, "DC": 0.9, "MC": 0.9, "ASC": 0.7},
        "Venus":   {"IC": 1.0, "DC": 0.9, "ASC": 0.7, "MC": 0.6},
        "Rahu":    {"IC": 0.85, "MC": 0.9, "ASC": 0.8, "DC": 0.7},
        "Saturn":  {"MC": 0.8, "IC": 0.7, "ASC": 0.5, "DC": 0.5},
        "Sun":     {"MC": 0.7, "IC": 0.7, "ASC": 0.6, "DC": 0.5},
        "Mercury": {"DC": 0.7, "MC": 0.6, "ASC": 0.6, "IC": 0.5},
        "Mars":    {"IC": 0.6, "MC": 0.5, "ASC": 0.5, "DC": 0.4},
        "Moon":    {"IC": 0.6, "DC": 0.6, "ASC": 0.4, "MC": 0.4},
        "Ketu":    {"IC": 0.5, "MC": 0.4, "ASC": 0.3, "DC": 0.3},
    },
    "career": {
        "Sun":     {"MC": 1.0, "ASC": 0.8, "DC": 0.6, "IC": 0.5},
        "Saturn":  {"MC": 0.95, "ASC": 0.7, "DC": 0.5, "IC": 0.5},
        "Jupiter": {"MC": 0.9, "DC": 0.8, "ASC": 0.7, "IC": 0.6},
        "Mercury": {"MC": 0.85, "ASC": 0.8, "DC": 0.7, "IC": 0.4},
        "Mars":    {"MC": 0.8, "ASC": 0.7, "DC": 0.5, "IC": 0.4},
        "Rahu":    {"MC": 0.75, "ASC": 0.7, "DC": 0.5, "IC": 0.4},
        "Venus":   {"MC": 0.6, "DC": 0.6, "ASC": 0.5, "IC": 0.4},
        "Moon":    {"MC": 0.5, "ASC": 0.5, "DC": 0.5, "IC": 0.4},
        "Ketu":    {"MC": 0.5, "ASC": 0.4, "IC": 0.4, "DC": 0.3},
    },
    "relationships": {
        "Venus":   {"DC": 1.0, "ASC": 0.9, "IC": 0.7, "MC": 0.5},
        "Moon":    {"DC": 1.0, "IC": 0.8, "ASC": 0.7, "MC": 0.4},
        "Jupiter": {"DC": 0.9, "ASC": 0.7, "IC": 0.6, "MC": 0.5},
        "Sun":     {"DC": 0.7, "ASC": 0.6, "MC": 0.5, "IC": 0.4},
        "Mercury": {"DC": 0.7, "ASC": 0.7, "MC": 0.5, "IC": 0.4},
        "Mars":    {"DC": 0.6, "ASC": 0.6, "MC": 0.4, "IC": 0.4},
        "Saturn":  {"DC": 0.5, "IC": 0.5, "ASC": 0.4, "MC": 0.4},
        "Rahu":    {"DC": 0.6, "ASC": 0.5, "IC": 0.4, "MC": 0.4},
        "Ketu":    {"DC": 0.4, "IC": 0.4, "ASC": 0.3, "MC": 0.3},
    },
    "general": {
        "Jupiter": {"MC": 0.9, "DC": 0.9, "ASC": 0.8, "IC": 0.75},
        "Venus":   {"DC": 0.85, "ASC": 0.8, "IC": 0.8, "MC": 0.7},
        "Mercury": {"ASC": 0.8, "MC": 0.75, "DC": 0.75, "IC": 0.5},
        "Sun":     {"MC": 0.8, "ASC": 0.7, "DC": 0.6, "IC": 0.5},
        "Rahu":    {"ASC": 0.75, "MC": 0.75, "DC": 0.6, "IC": 0.6},
        "Saturn":  {"MC": 0.7, "ASC": 0.6, "DC": 0.5, "IC": 0.5},
        "Mars":    {"ASC": 0.65, "MC": 0.65, "DC": 0.5, "IC": 0.5},
        "Moon":    {"DC": 0.6, "IC": 0.6, "ASC": 0.55, "MC": 0.5},
        "Ketu":    {"MC": 0.5, "ASC": 0.45, "IC": 0.45, "DC": 0.4},
    },
}

# Paran combinations with multipliers
PARAN_RULES = [
    ({"Jupiter", "Venus"},   "MC",  "DC",  1.5, "Jupiter_MC_x_Venus_DC: major wealth paran"),
    ({"Jupiter", "Venus"},   "DC",  "IC",  1.4, "Jupiter_DC_x_Venus_IC: Dhana Yoga at peak"),
    ({"Jupiter", "Venus"},   "ASC", "IC",  1.35,"Jupiter_ASC_x_Venus_IC: wisdom meets private wealth"),
    ({"Rahu",    "Jupiter"}, "MC",  "MC",  1.5, "Rahu_MC_x_Jupiter_MC: billionaire convergence"),
    ({"Rahu",    "Jupiter"}, "ASC", "DC",  1.4, "Rahu_ASC_x_Jupiter_DC: disruption meets investors"),
    ({"Rahu",    "Venus"},   "MC",  "IC",  1.35,"Rahu_MC_x_Venus_IC: unconventional private wealth"),
    ({"Mercury", "Mars"},    "ASC", "ASC", 1.3, "Mercury_ASC_x_Mars_ASC: execution paran"),
    ({"Sun",     "Jupiter"}, "MC",  "MC",  1.4, "Sun_MC_x_Jupiter_MC: authority-wealth convergence"),
    ({"Mercury", "Jupiter"}, "ASC", "DC",  1.3, "Mercury_ASC_x_Jupiter_DC: deals + investors"),
]

REGION_FILTERS: Dict[str, List[str]] = {
    "latam":         ["Mexico","Colombia","Brazil","Argentina","Chile","Peru","Uruguay","Paraguay","Bolivia","Ecuador","Venezuela","Guatemala","Costa Rica","Panama","Monterrey","Guadalajara","Mexico City","Buenos Aires","Montevideo","Asuncion","Bogota","Lima","Santiago","Medellin","Cali"],
    "europe":        ["UK","Germany","France","Spain","Italy","Netherlands","Portugal","Switzerland","Austria","Belgium","Sweden","Norway","Denmark","Finland","Poland","Czech","Hungary","Romania","Bulgaria","Croatia","Serbia","Greece","Ireland","Scotland","London","Paris","Berlin","Madrid","Rome","Amsterdam","Vienna","Zurich","Geneva","Barcelona","Milan","Oslo","Brussels","Dublin","Warsaw","Budapest","Lisbon","Tallinn","Riga","Vilnius","Ljubljana","Zagreb","Belgrade","Sofia","Bucharest","Edinburgh"],
    "asia":          ["India","Japan","China","Singapore","South Korea","Taiwan","Thailand","Vietnam","Indonesia","Malaysia","Philippines","Bangladesh","Nepal","Sri Lanka","Pakistan","Kazakhstan","Tokyo","Shanghai","Seoul","Taipei","Bangkok","Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Kolkata","Jaipur","Varanasi","Rishikesh","Goa","Karachi","Lahore","Dhaka","Colombo","Kathmandu","Almaty","Busan"],
    "middleeast":    ["UAE","Saudi Arabia","Qatar","Israel","Jordan","Lebanon","Iran","Kuwait","Doha","Dubai","Riyadh","Jeddah","Jerusalem","Beirut","Amman","Tehran","Kuwait City"],
    "africa":        ["Nigeria","Kenya","South Africa","Ghana","Ethiopia","Tanzania","Uganda","Senegal","Morocco","Tunisia","Ivory Coast","Lagos","Nairobi","Cape Town","Johannesburg","Accra","Addis Ababa","Dar es Salaam","Kampala","Dakar","Casablanca","Marrakech","Tunis","Abidjan"],
    "north_america": ["USA","Canada","Mexico","Houston","Austin","Denver","Phoenix","Las Vegas","Los Angeles","Monterrey","Guadalajara","Mexico City","Calgary"],
    "global":        [],
}


# ---------------------------------------------------------------------------
# Core scorer — matches the spec exactly
# ---------------------------------------------------------------------------

def score_city(
    city_data: Dict[str, Any],
    dashas: Dict[str, Any],
    intent: str,
    natal_yogas: Optional[List[Dict]] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Score a city using the 4-step framework from the spec.

    Returns (score, details_dict)
    """
    weights = INTENT_WEIGHTS.get(intent, INTENT_WEIGHTS["general"])

    # Dasha planets
    vim        = dashas.get("vimsottari", {})
    current_md = (vim.get("current_md") or {}).get("planet", "")
    current_ad = (vim.get("current_ad") or {}).get("planet", "")
    upcoming   = vim.get("upcoming_md") or []
    next_md    = (upcoming[0] if upcoming else {}).get("planet", "")

    # Step 1: Base line scoring
    score = 0.0
    line_details = []

    for planet, planet_lines in city_data.items():
        if not isinstance(planet_lines, dict):
            continue
        pw = weights.get(planet, {})
        for line_type, strength in planet_lines.items():
            if not isinstance(strength, (int, float)):
                continue
            w = pw.get(line_type, 0.0)
            if w == 0.0:
                continue
            contribution = float(strength) * w
            score += contribution
            line_details.append({
                "planet":       planet,
                "line":         line_type,
                "strength":     round(float(strength), 3),
                "contribution": round(contribution, 3),
            })

    line_details.sort(key=lambda x: x["contribution"], reverse=True)

    # Step 2: Dasha alignment multipliers
    dasha_notes = []
    city_planets = set(city_data.keys())

    if current_md and current_md in city_planets:
        score *= 1.2
        dasha_notes.append(f"×1.2 current MD ({current_md})")
    if current_ad and current_ad in city_planets and current_ad != current_md:
        score *= 1.15
        dasha_notes.append(f"×1.15 current AD ({current_ad})")
    if next_md and next_md in city_planets:
        score *= 1.5
        dasha_notes.append(f"×1.5 next MD ({next_md}) — 18yr window")

    # Step 3: Yoga amplification
    yoga_notes = []
    # Dhana Yoga: Jupiter + Venus both present
    if "Jupiter" in city_planets and "Venus" in city_planets:
        score *= 1.3
        yoga_notes.append("×1.3 Dhana Yoga (Jupiter + Venus)")

    # Additional yogas from natal data
    for yoga in (natal_yogas or []):
        yp = set(yoga.get("planets", []))
        if len(yp) >= 2 and yp.issubset(city_planets) and not (
            "Jupiter" in yp and "Venus" in yp  # already counted
        ):
            score *= 1.2
            yoga_notes.append(f"×1.2 {yoga.get('name','yoga')}")

    # Step 4: Paran detection
    paran_notes = []
    city_line_map: Dict[str, str] = {}  # planet -> strongest line type
    for planet, planet_lines in city_data.items():
        if isinstance(planet_lines, dict) and planet_lines:
            best_line = max(
                planet_lines.items(),
                key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0
            )
            city_line_map[planet] = best_line[0]

    for planets_set, l1, l2, multiplier, paran_name in PARAN_RULES:
        p_list = list(planets_set)
        if len(p_list) == 2:
            p1, p2 = p_list[0], p_list[1]
            # Check if both planets have the specified line types
            has_paran = (
                (city_line_map.get(p1) == l1 and city_line_map.get(p2) == l2) or
                (city_line_map.get(p1) == l2 and city_line_map.get(p2) == l1)
            )
            if has_paran:
                score *= multiplier
                paran_notes.append(f"×{multiplier} {paran_name}")

    return round(score, 3), {
        "line_details":  line_details[:5],
        "dasha_notes":   dasha_notes,
        "yoga_notes":    yoga_notes,
        "paran_notes":   paran_notes,
    }


# ---------------------------------------------------------------------------
# Flatten nested astro data
# ---------------------------------------------------------------------------

def _flatten(astro_data: Any) -> Dict[str, Any]:
    PLANETS = {"Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"}

    def is_city(d: Any) -> bool:
        return isinstance(d, dict) and bool(d) and any(k in PLANETS for k in d)

    flat: Dict[str, Any] = {}
    if not isinstance(astro_data, dict):
        return flat
    for key, val in astro_data.items():
        if not isinstance(val, dict):
            continue
        if is_city(val):
            flat[key] = val
        else:
            for city, cd in val.items():
                if is_city(cd):
                    flat[city] = cd
    return flat


# ---------------------------------------------------------------------------
# Stay-vs-move rule
# ---------------------------------------------------------------------------

def _stay_or_move(
    current_city: str,
    current_country: str,
    scored_cities: List[Dict],
) -> str:
    """
    Returns "stay" or "move".
    Stay if current location score is above 70th percentile of all cities.
    """
    if not scored_cities:
        return "move"

    all_scores = [c["score"] for c in scored_cities]
    if not all_scores:
        return "move"

    threshold = sorted(all_scores)[int(len(all_scores) * 0.7)]

    # Find current city score
    current_score = 0.0
    for c in scored_cities:
        city_name = c["city"].lower()
        if (current_city and current_city.lower() in city_name) or \
           (current_country and not current_city and (
               current_country.lower() in city_name or
               {"US": "usa", "CO": "colombia", "IN": "india", "GB": "uk"}.get(
                   current_country, current_country.lower()
               ) in city_name
           )):
            current_score = c["score"]
            break

    return "stay" if current_score >= threshold else "move"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def recommend_cities(
    chart_record: Dict[str, Any],
    dashas: Dict[str, Any],
    natal_yogas: Optional[List[Dict]] = None,
    intent: str = "general",
    region: str = "global",
    language: str = "en",
    top_n: int = 5,
) -> Dict[str, Any]:
    """
    Score and rank cities. Returns deterministic ranking for DeepSeek to narrate.
    """
    astro_data      = chart_record.get("astrocartography_data") or {}
    current_city    = chart_record.get("current_city") or ""
    current_country = chart_record.get("current_country") or chart_record.get("country_code", "")

    flat = _flatten(astro_data)
    if not flat:
        return {"error": "No astrocartography data for this chart"}

    # Dasha summary for DeepSeek prompt
    vim        = dashas.get("vimsottari", {})
    current_md = (vim.get("current_md") or {}).get("planet", "")
    current_md_end = (vim.get("current_md") or {}).get("end", "")
    current_ad = (vim.get("current_ad") or {}).get("planet", "")
    upcoming   = vim.get("upcoming_md") or []
    next_md    = (upcoming[0] if upcoming else {}).get("planet", "")
    next_md_start = (upcoming[0] if upcoming else {}).get("start", "")

    # Score all cities
    all_scored = []
    for city, city_data in flat.items():
        if not isinstance(city_data, dict) or not city_data:
            continue
        s, details = score_city(city_data, dashas, intent, natal_yogas)
        if s <= 0:
            continue
        is_current = bool(
            current_city and current_city.lower() in city.lower()
        ) or bool(
            not current_city and current_country and any(
                frag in city.lower()
                for frag in [current_country.lower(),
                             {"US":"usa","CO":"colombia","IN":"india","GB":"uk"}.get(
                                 current_country, current_country.lower())]
            )
        )
        all_scored.append({
            "city":               city,
            "score":              s,
            "is_current_location": is_current,
            **details,
        })

    all_scored.sort(key=lambda x: x["score"], reverse=True)

    # Region filter — applied after global ranking
    region_frags = REGION_FILTERS.get(region.lower(), [])
    if region_frags:
        region_scored = [
            c for c in all_scored
            if any(f.lower() in c["city"].lower() for f in region_frags)
        ]
        if len(region_scored) < 3:
            in_set = {c["city"] for c in region_scored}
            region_scored += [c for c in all_scored if c["city"] not in in_set][:3 - len(region_scored)]
    else:
        region_scored = all_scored

    top_cities = region_scored[:top_n]

    # Stay-vs-move
    stay_move = _stay_or_move(current_city, current_country, all_scored)

    # Missing lines report
    missing_lines = []
    present_lines = []
    for planet in ["Rahu", "Jupiter", "Sun"]:
        for lt in ["MC", "ASC"]:
            found = [c for c in all_scored if any(
                lt in (d.get(planet) or {})
                for d in [flat.get(c["city"], {})]
            )]
            key = f"{planet} {lt}"
            if found:
                present_lines.append(f"{key}: {found[0]['city']}")
            else:
                missing_lines.append(key)

    return {
        "intent":          intent,
        "region":          region,
        "current_city":    current_city or current_country,
        "stay_vs_move":    stay_move,
        "dasha_context": {
            "current_md":      current_md,
            "current_md_end":  current_md_end,
            "current_ad":      current_ad,
            "next_md":         next_md,
            "next_md_start":   next_md_start[:10] if next_md_start else "",
        },
        "top_cities":      top_cities,
        "missing_lines":   missing_lines,
        "present_lines":   present_lines,
        "cities_scored":   len(all_scored),
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def _smoke_test():
    print("Running astrocartography_recommender v4 smoke test...\n")

    fake_record = {
        "astrocartography_data": {
            "Monterrey, Mexico": {"Sun": {"IC": 0.977}, "Jupiter": {"DC": 0.533}},
            "Houston, USA":      {"Venus": {"IC": 0.987}, "Rahu": {"IC": 0.69}, "Jupiter": {"DC": 0.906}},
            "London, UK":        {"Mars": {"ASC": 0.925}, "Mercury": {"ASC": 0.976}, "Jupiter": {"IC": 0.739}},
            "Bogota, Colombia":  {"Jupiter": {"DC": 0.60}},
        },
        "current_city":    "Bogota",
        "current_country": "CO",
    }
    fake_dashas = {
        "vimsottari": {
            "current_md": {"planet": "Mars",  "end": "2026-08-13"},
            "current_ad": {"planet": "Moon",  "end": "2026-08-13"},
            "upcoming_md": [{"planet": "Rahu", "start": "2026-08-13"}],
        }
    }
    fake_yogas = [{"name": "Dhana Yoga", "planets": ["Jupiter", "Venus"]}]

    # Test 1: score_city directly
    s, d = score_city(
        fake_record["astrocartography_data"]["Houston, USA"],
        fake_dashas, "wealth", fake_yogas
    )
    assert s > 0, "FAIL: Houston score zero"
    assert any("Dhana" in n for n in d["yoga_notes"]), "FAIL: Dhana Yoga not detected"
    assert any("Rahu" in n for n in d["dasha_notes"]), "FAIL: Rahu next MD not detected"
    print(f"✅ Test 1: Houston wealth score={s}, yoga={d['yoga_notes']}, dasha={d['dasha_notes']}")

    # Test 2: stay-vs-move — Bogota has low score, should move
    r = recommend_cities(fake_record, fake_dashas, fake_yogas, intent="startup", region="global")
    print(f"✅ Test 2: stay_vs_move={r['stay_vs_move']} (Bogota score low → expect 'move')")

    # Test 3: London ranks for startup (Mars ASC + Mercury ASC)
    cities = [c["city"] for c in r["top_cities"][:3]]
    assert "London, UK" in cities, f"FAIL: London not in top 3. Got: {cities}"
    print(f"✅ Test 3: London in top 3 startup: {cities}")

    # Test 4: missing lines reported
    assert len(r["missing_lines"]) > 0
    print(f"✅ Test 4: Missing lines reported: {r['missing_lines'][:3]}")

    print("\n✅ All v4 smoke tests passed.")


if __name__ == "__main__":
    _smoke_test()
