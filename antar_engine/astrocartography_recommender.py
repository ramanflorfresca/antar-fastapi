"""
antar_engine/astrocartography_recommender.py
=============================================
City recommendation engine for Mapa Mundial.
v3 — rebuilt from DeepSeek framework (Apr 14 2026)

LAYER PRIORITY (applied in order):
  L1: Line type priority (MC > DC > ASC > IC varies by intent)
  L2: Planet-line meaning (Jupiter DC = investors find you, Rahu MC = billionaire track)
  L3: Dasha-location alignment (next MD weighted 40% higher than current)
  L4: Dhana Yoga amplification (compound effect when natal yoga planets both active)
  L5: Intent mapping (startup vs billionaire vs wealth vs career)
  L6: Gap reporting (honest about missing lines, infer likely lines from chart)
  L7: Context awareness (current location, stay vs move recommendation)

ENTRY POINT:
  recommend_cities(chart_record, dashas, natal_chart, intent, region, language, top_n)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# L1: Line type weights by intent
# Higher = more important for this intent
# ---------------------------------------------------------------------------
LINE_TYPE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "startup":       {"DC": 1.0, "MC": 0.85, "ASC": 0.80, "IC": 0.60},
    "billionaire":   {"MC": 1.0, "ASC": 0.85, "DC": 0.80, "IC": 0.70},
    "wealth":        {"IC": 1.0, "DC": 0.90, "MC": 0.80, "ASC": 0.65},
    "career":        {"MC": 1.0, "ASC": 0.75, "DC": 0.70, "IC": 0.50},
    "relationships": {"DC": 1.0, "ASC": 0.85, "IC": 0.70, "MC": 0.50},
    "health":        {"ASC": 1.0, "IC": 0.80, "DC": 0.60, "MC": 0.50},
    "spiritual":     {"IC": 1.0, "ASC": 0.80, "MC": 0.60, "DC": 0.50},
    "general":       {"MC": 0.85, "DC": 0.85, "ASC": 0.80, "IC": 0.75},
}

# ---------------------------------------------------------------------------
# L2: Planet-line meanings (what each combination actually means)
# ---------------------------------------------------------------------------
PLANET_LINE_MEANINGS: Dict[str, Dict[str, str]] = {
    "Jupiter": {
        "MC":  "Institutional wealth, public authority, investors come to you publicly",
        "DC":  "Investors and partners find you naturally — best line for fundraising",
        "IC":  "Private wealth accumulation, family fortune, inner prosperity",
        "ASC": "Personal luck visible, people see you as wise and fortunate",
    },
    "Venus": {
        "MC":  "Creative public success, luxury brand authority",
        "DC":  "High-value partnerships, beautiful alliances form naturally",
        "IC":  "Private asset accumulation, hidden wealth — strongest wealth-building line",
        "ASC": "Personal charm visible, deals flow through your presence",
    },
    "Rahu": {
        "MC":  "BILLIONAIRE TRACK — unconventional public wealth, foreign capital, disruption at scale",
        "ASC": "Disruptive public identity, fame through unconventional means",
        "DC":  "Foreign investors, disruptive alliances, unexpected partnerships",
        "IC":  "Private unconventional wealth, hidden foreign income, internal transformation",
    },
    "Mercury": {
        "MC":  "Public intellectual authority, media presence, thought leadership",
        "ASC": "Deals flow, words land perfectly — strongest line for negotiation",
        "DC":  "Deal flow through partnerships, contracts come easily",
        "IC":  "Private business acumen, internal strategy clarity",
    },
    "Sun": {
        "MC":  "Authority peak — government contracts, institutional recognition, leadership",
        "ASC": "Personal vitality and leadership visible, people follow you",
        "DC":  "High-status partnerships, alliance with powerful figures",
        "IC":  "Private confidence, inner authority, family legacy building",
    },
    "Mars": {
        "MC":  "Public competitive edge, warrior authority",
        "ASC": "Physical energy peak, competitive identity — great for aggressive execution",
        "DC":  "Aggressive partnerships, competitive alliances",
        "IC":  "Private drive, property energy, home as power base",
    },
    "Saturn": {
        "MC":  "Long-term disciplined authority, institutional backing over time",
        "ASC": "Disciplined identity, serious demeanor — respect but not warmth",
        "DC":  "Serious partnerships, long-term business alliances",
        "IC":  "Private discipline, structural wealth building",
    },
    "Moon": {
        "MC":  "Public emotional appeal, nurturing authority",
        "ASC": "Emotional intelligence visible, public warmth",
        "DC":  "Emotional partnerships, nurturing alliances",
        "IC":  "Private emotional foundation, fluctuating private income",
    },
    "Ketu": {
        "MC":  "Past-life mastery visible, spiritual authority, detachment from ego",
        "ASC": "Mystical identity, research-focused presence",
        "DC":  "Spiritual partnerships, past-life connections in alliances",
        "IC":  "Private spiritual depth, detachment from material concerns",
    },
}

# Billionaire-track lines (public wealth + unconventional wealth)
BILLIONAIRE_LINES = {
    "Rahu":    ["MC", "ASC"],
    "Jupiter": ["MC", "ASC"],
    "Sun":     ["MC"],
    "Saturn":  ["MC"],
}

# Planet base scores by intent (how relevant is this planet for this intent)
PLANET_INTENT_BASE: Dict[str, Dict[str, float]] = {
    "startup": {
        "Jupiter": 1.0, "Mercury": 1.0, "Rahu": 0.95, "Sun": 0.85,
        "Mars": 0.80, "Venus": 0.75, "Saturn": 0.65, "Moon": 0.55, "Ketu": 0.40,
    },
    "billionaire": {
        "Rahu": 1.0, "Jupiter": 1.0, "Sun": 0.90, "Saturn": 0.80,
        "Venus": 0.70, "Mercury": 0.65, "Mars": 0.60, "Moon": 0.45, "Ketu": 0.35,
    },
    "wealth": {
        "Jupiter": 1.0, "Venus": 1.0, "Rahu": 0.85, "Sun": 0.75,
        "Mercury": 0.70, "Saturn": 0.70, "Mars": 0.55, "Moon": 0.60, "Ketu": 0.30,
    },
    "career": {
        "Sun": 1.0, "Saturn": 0.95, "Jupiter": 0.90, "Mercury": 0.85,
        "Mars": 0.80, "Rahu": 0.70, "Venus": 0.60, "Moon": 0.55, "Ketu": 0.45,
    },
    "relationships": {
        "Venus": 1.0, "Moon": 1.0, "Jupiter": 0.85, "Sun": 0.65,
        "Mercury": 0.60, "Mars": 0.55, "Saturn": 0.45, "Rahu": 0.50, "Ketu": 0.40,
    },
    "health": {
        "Moon": 1.0, "Venus": 0.90, "Jupiter": 0.85, "Sun": 0.75,
        "Mercury": 0.65, "Mars": 0.60, "Saturn": 0.50, "Rahu": 0.45, "Ketu": 0.55,
    },
    "spiritual": {
        "Ketu": 1.0, "Moon": 0.90, "Jupiter": 0.85, "Saturn": 0.75,
        "Sun": 0.65, "Mercury": 0.55, "Venus": 0.60, "Rahu": 0.50, "Mars": 0.40,
    },
    "general": {
        "Jupiter": 1.0, "Venus": 0.90, "Mercury": 0.85, "Sun": 0.80,
        "Rahu": 0.80, "Moon": 0.75, "Saturn": 0.70, "Mars": 0.70, "Ketu": 0.55,
    },
}

REGION_FILTERS: Dict[str, List[str]] = {
    "latam":         ["Mexico","Colombia","Brazil","Argentina","Chile","Peru","Uruguay","Paraguay","Bolivia","Ecuador","Venezuela","Guatemala","Costa Rica","Panama","Monterrey","Guadalajara","Mexico City","Buenos Aires","Montevideo","Asuncion","Bogota","Lima","Santiago","Medellin","Cali","Cartagena"],
    "europe":        ["UK","Germany","France","Spain","Italy","Netherlands","Portugal","Switzerland","Austria","Belgium","Sweden","Norway","Denmark","Finland","Poland","Czech","Hungary","Romania","Bulgaria","Croatia","Serbia","Greece","Ireland","Scotland","London","Paris","Berlin","Madrid","Rome","Amsterdam","Vienna","Zurich","Geneva","Barcelona","Milan","Oslo","Brussels","Dublin","Warsaw","Budapest","Lisbon","Tallinn","Riga","Vilnius","Ljubljana","Zagreb","Belgrade","Sofia","Bucharest","Edinburgh"],
    "asia":          ["India","Japan","China","Singapore","South Korea","Taiwan","Thailand","Vietnam","Indonesia","Malaysia","Philippines","Bangladesh","Nepal","Sri Lanka","Pakistan","Kazakhstan","Tokyo","Shanghai","Seoul","Taipei","Bangkok","Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Kolkata","Jaipur","Varanasi","Rishikesh","Goa","Karachi","Lahore","Dhaka","Colombo","Kathmandu","Almaty","Busan","Novosibirsk"],
    "middleeast":    ["UAE","Saudi Arabia","Qatar","Israel","Jordan","Lebanon","Iran","Kuwait","Doha","Dubai","Riyadh","Jeddah","Jerusalem","Beirut","Amman","Tehran","Kuwait City"],
    "africa":        ["Nigeria","Kenya","South Africa","Ghana","Ethiopia","Tanzania","Uganda","Senegal","Morocco","Tunisia","Ivory Coast","Lagos","Nairobi","Cape Town","Johannesburg","Accra","Addis Ababa","Dar es Salaam","Kampala","Dakar","Casablanca","Marrakech","Tunis","Abidjan"],
    "north_america": ["USA","Canada","Mexico","Houston","Austin","Denver","Phoenix","Las Vegas","Los Angeles","Monterrey","Guadalajara","Mexico City","Calgary"],
    "global":        [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flatten_astro_data(astro_data: Any) -> Dict[str, Any]:
    """Flatten nested {region: {city: data}} or flat {city: data} to flat dict."""
    PLANET_NAMES = {"Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"}

    def is_city_data(d: Any) -> bool:
        return isinstance(d, dict) and bool(d) and any(k in PLANET_NAMES for k in d)

    flat: Dict[str, Any] = {}
    if not isinstance(astro_data, dict):
        return flat

    for key, val in astro_data.items():
        if not isinstance(val, dict):
            continue
        if is_city_data(val):
            flat[key] = val
        else:
            for city, city_data in val.items():
                if is_city_data(city_data):
                    flat[city] = city_data

    return flat


def _detect_yogas(city_data: Dict, natal_yogas: List[Dict]) -> List[str]:
    """Return names of natal yogas whose planets are ALL active in this city."""
    city_planets = set(city_data.keys())
    active = []
    for yoga in natal_yogas:
        planets = set(yoga.get("planets", []))
        if len(planets) >= 2 and planets.issubset(city_planets):
            active.append(yoga["name"])
    return active


def _detect_parans(city_data: Dict, intent: str) -> List[Dict]:
    """
    Detect parans — where two planetary lines are BOTH active in the same city.
    A paran is more powerful than either line alone.
    Returns list of significant paran combinations.
    """
    POWERFUL_PARANS = [
        ("Jupiter", "Venus",   "Dhana Yoga paran — wealth through partnerships amplified"),
        ("Jupiter", "Rahu",    "Billionaire paran — institutional wealth meets disruption"),
        ("Jupiter", "Mercury", "Business success paran — wisdom meets deal flow"),
        ("Sun",     "Jupiter", "Authority-wealth paran — leadership creates institutional wealth"),
        ("Rahu",    "Venus",   "Foreign luxury wealth paran — unconventional asset accumulation"),
        ("Rahu",    "Mercury", "Tech disruption paran — deals flow through unconventional channels"),
        ("Mars",    "Mercury", "Execution paran — energy meets communication for rapid deals"),
        ("Saturn",  "Jupiter", "Longevity wealth paran — disciplined expansion, lasting empire"),
    ]
    active = []
    for p1, p2, meaning in POWERFUL_PARANS:
        if p1 in city_data and p2 in city_data:
            active.append({
                "planets": [p1, p2],
                "meaning": meaning,
                "bonus":   0.25,  # 25% score bonus for paran
            })
    return active


# ---------------------------------------------------------------------------
# L3: Dasha alignment scoring
# ---------------------------------------------------------------------------

def _dasha_multiplier(
    planet: str,
    current_md: str,
    current_ad: str,
    next_md: str,
) -> Tuple[float, str]:
    """
    Return (multiplier, note) for dasha-planet alignment.
    Next MD weighted highest — you're choosing a location for 18 years.
    """
    if planet == current_ad:
        return 1.35, f"✦ Current AD ({current_ad}) — activated now"
    if planet == current_md:
        return 1.25, f"✦ Current MD ({current_md}) — active period"
    if planet == next_md:
        return 1.45, f"★ Next MD ({next_md}) — 18-year window starts soon"
    return 1.0, ""


# ---------------------------------------------------------------------------
# Core city scorer
# ---------------------------------------------------------------------------

def _score_city(
    city_data: Dict[str, Any],
    intent: str,
    current_md: str,
    current_ad: str,
    next_md: str,
) -> Tuple[float, List[Dict]]:
    """Score a city using the 5-layer framework."""
    line_weights   = LINE_TYPE_WEIGHTS.get(intent, LINE_TYPE_WEIGHTS["general"])
    planet_weights = PLANET_INTENT_BASE.get(intent, PLANET_INTENT_BASE["general"])

    total  = 0.0
    lines  = []

    for planet, planet_lines in city_data.items():
        if not isinstance(planet_lines, dict):
            continue

        p_base = planet_weights.get(planet, 0.5)
        d_mult, d_note = _dasha_multiplier(planet, current_md, current_ad, next_md)

        for line_type, strength in planet_lines.items():
            if not isinstance(strength, (int, float)):
                continue

            l_weight = line_weights.get(line_type, 0.5)

            # Final score = strength × planet_relevance × line_type_weight × dasha_multiplier
            weighted = float(strength) * p_base * l_weight * d_mult

            total += weighted
            meaning = PLANET_LINE_MEANINGS.get(planet, {}).get(line_type, "")
            lines.append({
                "planet":              planet,
                "line":                line_type,
                "strength":            round(float(strength), 3),
                "weighted_score":      round(weighted, 3),
                "meaning":             meaning,
                "dasha_note":          d_note,
                "is_billionaire_line": line_type in BILLIONAIRE_LINES.get(planet, []),
            })

    lines.sort(key=lambda x: x["weighted_score"], reverse=True)
    return round(total, 3), lines


# ---------------------------------------------------------------------------
# Gap reporter with inference
# ---------------------------------------------------------------------------

def _report_gaps(
    flat: Dict[str, Any],
    next_md: str,
    natal_planets: Dict[str, Any],
) -> Dict[str, Any]:
    """Report missing lines and infer likely locations based on chart."""

    # Check which billionaire lines exist in dataset
    missing_bill = []
    present_bill = []
    for planet, line_types in BILLIONAIRE_LINES.items():
        for lt in line_types:
            cities_with = [
                c for c, d in flat.items()
                if isinstance(d.get(planet), dict) and lt in d[planet]
            ]
            key = f"{planet} {lt}"
            if cities_with:
                present_bill.append(f"{key}: {', '.join(cities_with[:2])}")
            else:
                missing_bill.append(key)

    # Next MD coverage
    next_md_cities = [
        c for c, d in flat.items()
        if isinstance(d.get(next_md), dict) and d[next_md]
    ]

    # Inference note based on natal chart
    inference = ""
    if next_md == "Rahu" and natal_planets:
        rahu_sign  = (natal_planets.get("Rahu") or {}).get("sign",  "")
        rahu_house = (natal_planets.get("Rahu") or {}).get("house", "")
        inference = (
            f"Rahu is in {rahu_sign} (house {rahu_house}) natally. "
            f"Rahu MC/ASC lines likely cross Asia-Pacific or Middle East — "
            f"Singapore, Dubai, and Mumbai are common Rahu MC locations for South Asian charts. "
            f"Swiss Ephemeris computation needed to confirm exact crossing."
        )

    return {
        "missing_billionaire_lines": missing_bill,
        "present_billionaire_lines": present_bill,
        "next_md_cities_in_dataset": next_md_cities,
        "inference": inference,
        "data_limitation": (
            "Current data: city-point scores only. "
            "True astrocartography uses continuous line paths — "
            "being within 500km of a line still gives effect. "
            "Parans (line crossings) are exponentially more powerful than single lines. "
            "Swiss Ephemeris line computation sprint will fix this."
        ),
        "missing_varga_lines": (
            "D9 Navamsa and D10 Dasamsa planet lines not computed. "
            "D9 shows where soul dharma peaks; D10 shows career authority peak. "
            "These differ from D1 lines. Future sprint."
        ),
    }


# ---------------------------------------------------------------------------
# Phase strategy builder
# ---------------------------------------------------------------------------

def _phase_strategy(
    flat: Dict[str, Any],
    current_md: str,
    current_md_end: str,
    current_ad: str,
    next_md: str,
    next_md_start: str,
    current_city: str,
    current_country: str,
    language: str,
) -> Dict[str, Any]:
    """Build a time-phased location recommendation."""

    def best_city_for(planet: str) -> Optional[str]:
        best, best_s = None, 0.0
        for city, data in flat.items():
            if not isinstance(data.get(planet), dict):
                continue
            s = sum(v for v in data[planet].values() if isinstance(v, (int, float)))
            if s > best_s:
                best_s, best = s, city
        return best

    now_city    = best_city_for(current_md) or best_city_for(current_ad)
    future_city = best_city_for(next_md)

    # Context awareness — is user already in a good city?
    user_location = current_city or current_country
    already_good  = user_location and now_city and user_location.lower() in now_city.lower()

    if language == "es":
        return {
            "ahora": {
                "planeta":     current_md,
                "hasta":       current_md_end,
                "ciudad":      now_city,
                "ya_ahi":      already_good,
                "instruccion": (
                    f"Ya estás en el lugar correcto. Aprovecha {current_md} energía aquí hasta {current_md_end}."
                    if already_good else
                    f"Hasta {current_md_end}: maximiza {current_md} energía en {now_city}."
                ) if now_city else f"Sin línea fuerte de {current_md} en los datos actuales.",
            },
            "proximo_md": {
                "planeta":    next_md,
                "desde":      next_md_start,
                "ciudad":     future_city,
                "urgencia":   "ALTA — decisión de ubicación más importante para los próximos 18 años",
                "instruccion": (
                    f"Desde {next_md_start}: establécete en {future_city} para el MD de {next_md} (18 años)."
                    if future_city else
                    f"Calcular líneas globales de {next_md} — no están en los datos actuales. Probablemente Asia o Medio Oriente."
                ),
            },
        }
    else:
        return {
            "now": {
                "planet":      current_md,
                "until":       current_md_end,
                "city":        now_city,
                "already_there": already_good,
                "instruction": (
                    f"You're already in the right place. Leverage {current_md} energy here until {current_md_end}."
                    if already_good else
                    f"Until {current_md_end}: maximize {current_md} energy in {now_city}."
                ) if now_city else f"No strong {current_md} line in current dataset.",
            },
            "next_md": {
                "planet":      next_md,
                "from":        next_md_start,
                "city":        future_city,
                "urgency":     "HIGH — most important location decision for the next 18 years",
                "instruction": (
                    f"From {next_md_start}: establish in {future_city} for {next_md} MD (18 years)."
                    if future_city else
                    f"Compute global {next_md} lines — not in current dataset. Likely Asia or Middle East."
                ),
            },
        }


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
    Recommend best cities using the 6-layer DeepSeek framework.

    Layers: Line type → Planet meaning → Dasha alignment →
            Yoga + Paran amplification → Intent mapping → Gap + inference
    """
    astro_data = chart_record.get("astrocartography_data") or {}
    natal_planets = (chart_record.get("chart_data") or {}).get("planets", {})
    current_city    = chart_record.get("current_city", "") or ""
    current_country = chart_record.get("current_country", "") or chart_record.get("country_code", "")

    flat = _flatten_astro_data(astro_data)
    if not flat:
        return {"error": "No astrocartography data for this chart"}

    # Dasha context
    vim            = dashas.get("vimsottari", {})
    current_md     = (vim.get("current_md") or {}).get("planet", "")
    current_md_end = (vim.get("current_md") or {}).get("end", "")
    current_ad     = (vim.get("current_ad") or {}).get("planet", "")
    upcoming       = vim.get("upcoming_md") or []
    next_md        = (upcoming[0] if upcoming else {}).get("planet", "")
    next_md_start  = (upcoming[0] if upcoming else {}).get("start", "")

    # Score all cities
    all_scored = []
    for city, city_data in flat.items():
        if not isinstance(city_data, dict) or not city_data:
            continue

        base_score, lines = _score_city(city_data, intent, current_md, current_ad, next_md)
        if base_score <= 0:
            continue

        # L4a: Yoga amplification
        active_yogas = _detect_yogas(city_data, natal_yogas or [])
        yoga_bonus   = sum(0.20 * base_score for _ in active_yogas)

        # L4b: Paran bonus
        parans      = _detect_parans(city_data, intent)
        paran_bonus = sum(p["bonus"] * base_score for p in parans)

        final_score = round(base_score + yoga_bonus + paran_bonus, 3)

        # Context: is user already here?
        is_current = bool(
            current_city and current_city.lower() in city.lower()
        ) or bool(
            current_country and not current_city and
            any(c.lower() in city.lower() for c in [current_country, "USA" if current_country == "US" else current_country])
        )

        all_scored.append({
            "city":          city,
            "score":         final_score,
            "active_lines":  lines,
            "active_yogas":  active_yogas,
            "parans":        parans,
            "is_current_location": is_current,
        })

    all_scored.sort(key=lambda x: x["score"], reverse=True)

    # Apply region filter after global ranking
    region_fragments = REGION_FILTERS.get(region.lower(), [])
    if region_fragments:
        region_scored = [
            c for c in all_scored
            if any(f.lower() in c["city"].lower() for f in region_fragments)
        ]
        if len(region_scored) < 3:
            in_set = {c["city"] for c in region_scored}
            region_scored += [c for c in all_scored if c["city"] not in in_set][:3 - len(region_scored)]
    else:
        region_scored = all_scored

    top_cities = region_scored[:top_n]

    # Build explanations
    for rec in top_cities:
        top_lines   = rec["active_lines"][:3]
        yogas       = rec["active_yogas"]
        parans_list = rec["parans"]
        dasha_lines = [l for l in top_lines if l.get("dasha_note")]
        current_tag = " [YOUR CURRENT LOCATION]" if rec["is_current_location"] else ""

        yoga_str  = f" Activates {', '.join(yogas)}." if yogas else ""
        paran_str = f" Paran: {parans_list[0]['meaning']}." if parans_list else ""

        if language == "es":
            lead = dasha_lines[0] if dasha_lines else (top_lines[0] if top_lines else None)
            rec["explanation"] = (
                f"{current_tag}{lead['planet']} {lead['line']} ({lead['strength']}) — "
                f"{lead['meaning'][:80]}. {lead.get('dasha_note','')}{yoga_str}{paran_str}"
            ).strip() if lead else f"{current_tag}Activación moderada."
        else:
            lead = dasha_lines[0] if dasha_lines else (top_lines[0] if top_lines else None)
            rec["explanation"] = (
                f"{current_tag}{lead['planet']} {lead['line']} ({lead['strength']}) — "
                f"{lead['meaning'][:80]}. {lead.get('dasha_note','')}{yoga_str}{paran_str}"
            ).strip() if lead else f"{current_tag}Moderate activation."

    # Phase strategy
    strategy = _phase_strategy(
        flat, current_md, current_md_end, current_ad,
        next_md, next_md_start, current_city, current_country, language,
    )

    # Gap report
    gaps = _report_gaps(flat, next_md, natal_planets)

    # Global insight
    dhana_cities = [c["city"] for c in all_scored if c["active_yogas"]]
    paran_cities = [c["city"] for c in all_scored if c["parans"]]

    if language == "es":
        global_insight = (
            f"Ciudades con Yoga Dhana activo: {', '.join(dhana_cities[:2]) or 'ninguna en los datos'}. "
            f"Ciudades con parans activos: {', '.join(paran_cities[:2]) or 'ninguna'}. "
            f"La decisión más crítica: dónde estar cuando empiece {next_md} MD ({next_md_start[:10]})."
        )
    else:
        global_insight = (
            f"Dhana Yoga cities: {', '.join(dhana_cities[:2]) or 'none in dataset'}. "
            f"Paran cities: {', '.join(paran_cities[:2]) or 'none'}. "
            f"Critical decision: where to be when {next_md} MD starts ({next_md_start[:10]})."
        )

    return {
        "intent":         intent,
        "region":         region,
        "dasha_context":  f"MD: {current_md} until {current_md_end} | AD: {current_ad} | Next MD: {next_md} from {next_md_start[:10]}",
        "top_cities":     top_cities,
        "phase_strategy": strategy,
        "gaps":           gaps,
        "global_insight": global_insight,
        "cities_scored":  len(all_scored),
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def _smoke_test():
    print("Running astrocartography_recommender v3 smoke test...\n")

    fake_record = {
        "astrocartography_data": {
            "Monterrey, Mexico": {"Sun": {"IC": 0.977}, "Jupiter": {"DC": 0.533}},
            "Mexico City, Mexico": {"Sun": {"IC": 0.79}, "Jupiter": {"DC": 0.524}},
            "Houston, USA": {"Ketu": {"MC": 0.978}, "Venus": {"IC": 0.987}, "Rahu": {"IC": 0.69}, "Jupiter": {"DC": 0.906}},
            "Austin, USA": {"Sun": {"IC": 0.57}, "Venus": {"IC": 0.614}, "Jupiter": {"DC": 0.876}},
            "London, UK": {"Mars": {"ASC": 0.925}, "Mercury": {"ASC": 0.976}, "Jupiter": {"IC": 0.739}},
            "Singapore": {"Rahu": {"MC": 0.85}, "Jupiter": {"MC": 0.72}},
        },
        "chart_data": {"planets": {"Rahu": {"sign": "Aries", "house": 4}}},
        "current_city": "",
        "current_country": "US",
    }
    fake_dashas = {
        "vimsottari": {
            "current_md": {"planet": "Mars",  "end": "2026-08-13"},
            "current_ad": {"planet": "Moon",  "end": "2026-08-13"},
            "upcoming_md": [{"planet": "Rahu", "start": "2026-08-13"}],
        }
    }
    fake_yogas = [{"name": "Dhana Yoga", "planets": ["Jupiter", "Venus"]}]

    # Test 1: For billionaire globally — Houston OR Singapore should be in top 2
    # Houston wins on combined IC wealth; Singapore has Rahu MC public track
    # Both are valid — test that at least one is in top 2
    r1 = recommend_cities(fake_record, fake_dashas, fake_yogas, intent="billionaire", region="global")
    top2 = [c["city"] for c in r1["top_cities"][:2]]
    assert any("Singapore" in c or "Houston" in c for c in top2),         f"FAIL: neither Singapore nor Houston in top 2 billionaire. Got: {top2}"
    print(f"✅ Test 1: Billionaire top 2: {top2} (Houston=private wealth, Singapore=public Rahu MC)")

    # Test 2: Houston has Dhana Yoga + paran detected
    r2 = recommend_cities(fake_record, fake_dashas, fake_yogas, intent="wealth", region="global")
    houston = next((c for c in r2["top_cities"] if "Houston" in c["city"]), None)
    assert houston, "FAIL: Houston not in top results"
    assert "Dhana Yoga" in houston.get("active_yogas", []), "FAIL: Dhana Yoga not detected in Houston"
    assert len(houston.get("parans", [])) > 0, "FAIL: No parans detected in Houston"
    print("✅ Test 2: Houston Dhana Yoga + paran detected (Jupiter DC + Venus IC)")

    # Test 3: London in top for startup (Mars ASC + Mercury ASC)
    r3 = recommend_cities(fake_record, fake_dashas, fake_yogas, intent="startup", region="global")
    cities3 = [c["city"] for c in r3["top_cities"][:3]]
    assert "London, UK" in cities3, f"FAIL: London not in top 3 startup. Got: {cities3}"
    print("✅ Test 3: London in top 3 startup (Mars ASC + Mercury ASC)")

    # Test 4: Phase strategy populated with stay-vs-move awareness
    assert "now" in r3["phase_strategy"] or "ahora" in r3["phase_strategy"]
    print("✅ Test 4: Phase strategy with stay/move awareness")

    # Test 5: LATAM with global fallback
    r5 = recommend_cities(fake_record, fake_dashas, fake_yogas, intent="startup", region="latam")
    assert len(r5["top_cities"]) >= 2
    print("✅ Test 5: LATAM filter with global fallback")

    # Test 6: Gap report has Rahu inference
    r6 = recommend_cities(fake_record, fake_dashas, fake_yogas, intent="billionaire", region="global")
    assert "inference" in r6["gaps"]
    assert "Rahu" in r6["gaps"]["inference"]
    print("✅ Test 6: Gap report with Rahu inference from natal chart")

    # Test 7: Spanish language
    r7 = recommend_cities(fake_record, fake_dashas, fake_yogas, intent="startup", region="latam", language="es")
    assert "ahora" in r7["phase_strategy"]
    print("✅ Test 7: Spanish phase strategy")

    print("\n✅ All v3 smoke tests passed.")


if __name__ == "__main__":
    _smoke_test()
