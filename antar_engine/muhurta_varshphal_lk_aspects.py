"""
Three backend additions:
1. Muhurta API endpoint wiring
2. Full Tajika Varshphal
3. Lal Kitab aspects (unique system)

Run from antarai directory to patch main.py
"""

# ── 1. MUHURTA ENDPOINT ─────────────────────────────────────────
MUHURTA_ENDPOINT = '''

@app.post("/api/v1/muhurta/best-times")
async def get_muhurta(request: dict):
    """
    Find auspicious timing for specific events.
    Uses dasha confluence + transit analysis + planetary war check.
    Events: marriage, business_start, property_purchase, travel,
            surgery, job_start, investment, naming_ceremony
    """
    from antar_engine.timing_engine import timing_insights, upcoming_transit_windows

    chart_id  = request.get("chart_id")
    event     = request.get("event", "general")
    days_ahead= request.get("days_ahead", 90)

    if not chart_id:
        raise HTTPException(400, "chart_id required")

    res = supabase.table("charts").select("chart_data").eq("id", chart_id).execute()
    if not res.data:
        raise HTTPException(404, "Chart not found")

    chart_data = res.data[0]["chart_data"]
    dashas     = get_dashas_for_chart(chart_id)

    # Get timing insights
    try:
        insights = timing_insights(chart_data, dashas, supabase=supabase)
    except Exception as e:
        insights = {"error": str(e)}

    # Transit windows
    try:
        transit_windows = upcoming_transit_windows(chart_data, look_ahead_years=1)
    except Exception as e:
        transit_windows = []

    # Muhurta rules per event type
    MUHURTA_RULES = {
        "marriage": {
            "favorable_lords": ["Venus", "Jupiter", "Moon"],
            "favorable_nakshatras": ["Rohini","Mrigashira","Magha","Uttara Phalguni",
                                     "Hasta","Swati","Anuradha","Uttara Ashadha","Uttara Bhadrapada"],
            "avoid_during": ["Saturn AD", "Rahu AD", "Mars AD"],
            "best_day": "Wednesday (Mercury) or Thursday (Jupiter) or Friday (Venus)",
            "avoid_months": "Adhika Masa, Bhadra Masa",
        },
        "business_start": {
            "favorable_lords": ["Mercury", "Jupiter", "Sun"],
            "avoid_during": ["Saturn MD starting", "Ketu AD"],
            "best_day": "Wednesday (Mercury) or Thursday (Jupiter)",
            "note": "Start during waxing moon (Shukla Paksha)",
        },
        "property_purchase": {
            "favorable_lords": ["Mars", "Venus", "Jupiter", "Saturn"],
            "avoid_during": ["Mars AD in 8/12", "Rahu AD"],
            "best_day": "Tuesday (Mars) or Saturday (Saturn for long-term)",
            "note": "4th house lord dasha is ideal for property",
        },
        "travel": {
            "favorable_lords": ["Mercury", "Moon", "Jupiter"],
            "avoid_during": ["Ketu AD", "Saturn AD"],
            "best_day": "Wednesday or Thursday",
            "note": "Avoid travel when Moon is in Ashlesha, Jyeshtha, or Mula",
        },
        "surgery": {
            "favorable_lords": ["Mars", "Sun"],
            "avoid_during": ["Ketu AD", "Saturn AD in 8th from natal Moon"],
            "best_day": "Tuesday (Mars) for scheduled surgery",
            "note": "Avoid surgery during Moon in the sign of the body part being operated",
        },
        "investment": {
            "favorable_lords": ["Jupiter", "Venus", "Mercury"],
            "avoid_during": ["Saturn AD", "Ketu AD"],
            "best_day": "Thursday (Jupiter) or Friday (Venus)",
            "note": "Invest during Jupiter transit over 2nd or 11th house",
        },
    }

    rules = MUHURTA_RULES.get(event, MUHURTA_RULES.get("business_start"))

    # Current dasha quality for this event
    current_dasha = _current_dasha_str(dashas)
    dasha_quality = "favorable"
    if rules:
        avoid = rules.get("avoid_during", [])
        for a in avoid:
            if any(word in current_dasha for word in a.split()):
                dasha_quality = "caution"
                break

    return {
        "chart_id":       chart_id,
        "event":          event,
        "current_dasha":  current_dasha,
        "dasha_quality":  dasha_quality,
        "muhurta_rules":  rules,
        "timing_insights": insights if isinstance(insights, dict) else {},
        "transit_windows": transit_windows[:5] if isinstance(transit_windows, list) else [],
        "general_advice": (
            f"Current dasha ({current_dasha}) is {'favorable' if dasha_quality=='favorable' else 'requires caution'} for {event}. "
            f"Best days: {rules.get('best_day', 'consult Panchanga')}. "
            f"Note: {rules.get('note', 'Follow Vedic Muhurta principles.')}"
        ),
    }

'''

# ── 2. FULL TAJIKA VARSHPHAL ────────────────────────────────────
VARSHPHAL_ENGINE = '''

class VarshphalRequest(BaseModel):
    chart_id: str
    year:     Optional[int] = None  # defaults to current year

@app.post("/api/v1/varshphal/annual")
async def get_varshphal(request: VarshphalRequest):
    """
    Full Tajika Varshphal — annual solar return chart.
    Most accurate annual prediction system in Jyotish.
    """
    from datetime import date, timedelta
    import swisseph as swe

    chart_id = request.chart_id
    res = supabase.table("charts").select(
        "chart_data,birth_date,birth_time,latitude,longitude,timezone"
    ).eq("id", chart_id).execute()

    if not res.data:
        raise HTTPException(404, "Chart not found")

    row        = res.data[0]
    chart_data = row["chart_data"]
    birth_date = row.get("birth_date", "")
    birth_jd   = chart_data.get("birth_jd", 0)

    # Target year
    today     = date.today()
    year      = request.year or today.year

    try:
        from datetime import datetime
        born = date.fromisoformat(birth_date[:10])
        age  = year - born.year

        # Find solar return JD (when Sun returns to natal longitude)
        natal_sun_long = chart_data.get("planets", {}).get("Sun", {}).get("longitude", 0)

        # Approximate: birth_jd + age * 365.25
        approx_return = birth_jd + age * 365.25

        # Narrow down using Swiss Ephemeris
        try:
            swe.set_sid_mode(swe.SIDM_LAHIRI)
            # Search within 2 days
            for offset in [d * 0.01 for d in range(-200, 200)]:
                test_jd = approx_return + offset
                sun_pos, _ = swe.calc_ut(test_jd, swe.SUN)
                tropical_long = sun_pos[0]
                ayanamsa = swe.get_ayanamsa(test_jd)
                sidereal_long = (tropical_long - ayanamsa) % 360
                if abs(sidereal_long - natal_sun_long) < 0.05:
                    solar_return_jd = test_jd
                    break
            else:
                solar_return_jd = approx_return
        except Exception:
            solar_return_jd = approx_return

        # Year lord (Varsha Pati) — planet that rules the solar return moment
        # Simplified: based on day of week of solar return
        from datetime import datetime as dt
        # JD to date
        y, m, d_day, h = swe.revjul(solar_return_jd) if solar_return_jd > 0 else (year, born.month, born.day, 0)
        return_date = date(int(y), int(m), int(d_day))
        day_lords   = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
        year_lord   = day_lords[return_date.weekday()]

        # Year lord house in natal chart
        year_lord_house = chart_data.get("planets", {}).get(year_lord, {}).get("house", 0)

        # Annual themes based on year lord
        YEAR_LORD_THEMES = {
            "Sun":     {"theme":"authority and career", "favorable":["career","recognition","father"],
                        "challenge":"ego conflicts, health of father"},
            "Moon":    {"theme":"emotions and public life", "favorable":["family","public","mother"],
                        "challenge":"emotional instability, mother health"},
            "Mars":    {"theme":"action and property", "favorable":["property","courage","energy"],
                        "challenge":"accidents, disputes, anger"},
            "Mercury": {"theme":"communication and business", "favorable":["business","education","trade"],
                        "challenge":"nervous system, overthinking"},
            "Jupiter": {"theme":"expansion and wisdom", "favorable":["wealth","children","wisdom"],
                        "challenge":"overexpansion, liver health"},
            "Venus":   {"theme":"relationships and luxury", "favorable":["marriage","beauty","vehicles"],
                        "challenge":"indulgence, relationship issues"},
            "Saturn":  {"theme":"discipline and karma", "favorable":["career_longevity","service"],
                        "challenge":"delays, depression, bones"},
        }

        year_theme = YEAR_LORD_THEMES.get(year_lord, {})

        # Tajika aspects in Varshphal (different from Parashari)
        # Sextile (60°), Square (90°), Trine (120°), Opposition (180°) used
        tajika_aspects = []
        planets = chart_data.get("planets", {})
        year_lord_long = planets.get(year_lord, {}).get("longitude", 0)

        for planet, data in planets.items():
            if planet == year_lord:
                continue
            p_long = data.get("longitude", 0)
            diff   = abs(year_lord_long - p_long) % 360
            if diff > 180: diff = 360 - diff

            if diff < 10:
                tajika_aspects.append({"type": "conjunction", "planet": planet, "quality": "intense"})
            elif abs(diff - 60) < 8:
                tajika_aspects.append({"type": "sextile", "planet": planet, "quality": "friendly"})
            elif abs(diff - 90) < 8:
                tajika_aspects.append({"type": "square", "planet": planet, "quality": "challenging"})
            elif abs(diff - 120) < 8:
                tajika_aspects.append({"type": "trine", "planet": planet, "quality": "favorable"})
            elif abs(diff - 180) < 10:
                tajika_aspects.append({"type": "opposition", "planet": planet, "quality": "tension"})

        # Muntha (annual lagna) — moves 1 sign per year
        natal_lagna_idx = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                           "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"].index(
                            chart_data.get("lagna",{}).get("sign","Aries") if isinstance(chart_data.get("lagna"),dict) else "Aries")
        muntha_idx  = (natal_lagna_idx + age - 1) % 12
        muntha_sign = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                       "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"][muntha_idx]

        # Overall year quality
        favorable_aspects = sum(1 for a in tajika_aspects if a["quality"] in ["favorable","friendly"])
        challenging_aspects = sum(1 for a in tajika_aspects if a["quality"] in ["challenging","tension"])
        year_quality = ("excellent" if favorable_aspects >= 3 else
                       "good" if favorable_aspects >= 2 else
                       "mixed" if challenging_aspects <= favorable_aspects else
                       "challenging")

        return {
            "chart_id":        chart_id,
            "year":            year,
            "age_this_year":   age,
            "solar_return_date": str(return_date),
            "year_lord":       year_lord,
            "year_lord_house": year_lord_house,
            "year_theme":      year_theme,
            "muntha":          muntha_sign,
            "muntha_house":    ((muntha_idx - natal_lagna_idx) % 12) + 1,
            "tajika_aspects":  tajika_aspects[:6],
            "year_quality":    year_quality,
            "favorable_areas": year_theme.get("favorable", []),
            "challenge_areas": year_theme.get("challenge", ""),
            "summary": (
                f"Year {year} is ruled by {year_lord} in house {year_lord_house}. "
                f"Theme: {year_theme.get('theme','')}. "
                f"Muntha in {muntha_sign} (house {((muntha_idx - natal_lagna_idx) % 12) + 1}). "
                f"Overall quality: {year_quality.upper()}."
            ),
        }
    except Exception as e:
        raise HTTPException(500, f"Varshphal calculation error: {e}")

'''

# ── 3. LK ASPECTS ENGINE ────────────────────────────────────────
LK_ASPECTS_CODE = '''
def calculate_lk_aspects(planets: dict, lagna_sign: str) -> dict:
    """
    Lal Kitab Aspect System — completely different from Parashari.

    LK Aspect Rules:
    1. Every planet aspects the 7th house from itself (universal)
    2. Jupiter aspects 5th and 9th from itself (additional)
    3. Mars aspects 4th and 8th from itself (additional)
    4. Saturn aspects 3rd and 10th from itself (additional)
    5. Rahu/Ketu aspect 5th, 7th, 9th from themselves

    Aspect RESULTS in LK (very different from Parashari):
    - Planet aspecting its OWN house = powerful protection
    - Benefic aspecting a house = planet sleeps less, gives results
    - Malefic aspecting a house = planet in that house becomes disturbed
    - Mutual aspect of enemies = very bad for both houses
    - Planet aspecting 2nd from itself = activates income/speech
    """
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    BENEFICS = ["Jupiter", "Venus", "Moon", "Mercury"]
    MALEFICS  = ["Saturn", "Mars", "Sun", "Rahu", "Ketu"]

    lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

    # Build house occupation
    house_planets = {h: [] for h in range(1, 13)}
    for planet, data in planets.items():
        h = data.get("house", 0)
        if h:
            house_planets[h].append(planet)

    # Calculate all aspects
    all_aspects = []
    aspect_on_house = {h: [] for h in range(1, 13)}

    for planet, data in planets.items():
        p_house = data.get("house", 0)
        if not p_house:
            continue

        # Universal 7th aspect
        seventh = ((p_house - 1 + 6) % 12) + 1
        all_aspects.append({
            "from_planet": planet,
            "from_house":  p_house,
            "to_house":    seventh,
            "aspect_type": "7th",
            "quality":     "benefic" if planet in BENEFICS else "malefic",
        })
        aspect_on_house[seventh].append({"planet": planet, "type": "7th"})

        # Special aspects
        if planet == "Jupiter":
            for offset in [4, 8]:
                to_h = ((p_house - 1 + offset) % 12) + 1
                all_aspects.append({
                    "from_planet": planet, "from_house": p_house,
                    "to_house": to_h, "aspect_type": f"{offset+1}th",
                    "quality": "benefic",
                })
                aspect_on_house[to_h].append({"planet": planet, "type": f"{offset+1}th"})

        elif planet == "Mars":
            for offset in [3, 7]:
                to_h = ((p_house - 1 + offset) % 12) + 1
                all_aspects.append({
                    "from_planet": planet, "from_house": p_house,
                    "to_house": to_h, "aspect_type": f"{offset+1}th",
                    "quality": "malefic",
                })
                aspect_on_house[to_h].append({"planet": planet, "type": f"{offset+1}th"})

        elif planet == "Saturn":
            for offset in [2, 9]:
                to_h = ((p_house - 1 + offset) % 12) + 1
                all_aspects.append({
                    "from_planet": planet, "from_house": p_house,
                    "to_house": to_h, "aspect_type": f"{offset+1}th",
                    "quality": "malefic",
                })
                aspect_on_house[to_h].append({"planet": planet, "type": f"{offset+1}th"})

        elif planet in ["Rahu", "Ketu"]:
            for offset in [4, 6, 8]:
                to_h = ((p_house - 1 + offset) % 12) + 1
                all_aspects.append({
                    "from_planet": planet, "from_house": p_house,
                    "to_house": to_h, "aspect_type": f"{offset+1}th",
                    "quality": "malefic",
                })
                aspect_on_house[to_h].append({"planet": planet, "type": f"{offset+1}th"})

    # Key insights from LK aspects
    key_insights = []

    for house, aspects in aspect_on_house.items():
        if not aspects:
            continue
        benefic_aspects  = [a for a in aspects if a["planet"] in BENEFICS]
        malefic_aspects  = [a for a in aspects if a["planet"] in MALEFICS]
        house_occupants  = house_planets.get(house, [])

        if len(malefic_aspects) >= 2 and not benefic_aspects:
            key_insights.append({
                "house":   house,
                "message": f"House {house} has {len(malefic_aspects)} malefic LK aspects ({', '.join(a['planet'] for a in malefic_aspects)}) — this house's significations face obstacles",
                "type":    "warning",
            })

        if benefic_aspects and not malefic_aspects:
            if house in [1,2,4,5,7,9,10,11]:
                key_insights.append({
                    "house":   house,
                    "message": f"House {house} receives benefic LK aspects only ({', '.join(a['planet'] for a in benefic_aspects)}) — protected and supported",
                    "type":    "positive",
                })

        # Jupiter aspecting 2nd/5th/9th/11th = wealth/children protection
        if any(a["planet"] == "Jupiter" for a in aspects) and house in [2, 5, 9, 11]:
            key_insights.append({
                "house":   house,
                "message": f"Jupiter LK aspect on house {house} — divine protection for this house's significations",
                "type":    "blessing",
            })

    return {
        "all_aspects":    all_aspects,
        "aspect_on_house": aspect_on_house,
        "key_insights":   key_insights[:6],
        "lk_aspect_rule": "LK aspects are action-oriented — benefic aspects wake sleeping planets, malefic aspects disturb house significations",
    }
'''

# ── 4. TRANSIT DB SAVE ──────────────────────────────────────────
TRANSIT_SAVE_CODE = '''
    # Save transits to DB on chart create
    try:
        from antar_engine.transits_engine import calculate_current_transits
        _transit_data = calculate_current_transits(chart_data)
        if _transit_data and not _transit_data.get("error"):
            supabase.table("chart_transits").insert({
                "chart_id":        chart_id,
                "jupiter_house":   _transit_data.get("jupiter_house"),
                "saturn_house":    _transit_data.get("saturn_house"),
                "transit_data":    _transit_data.get("current_transits", []),
                "timing_insights": _transit_data.get("timing_insights", []),
            }).execute()
    except Exception as _te:
        print(f"[transit_save] non-fatal: {_te}")
'''

print("All code blocks ready")
print(f"Muhurta endpoint: {len(MUHURTA_ENDPOINT)} chars")
print(f"Varshphal engine: {len(VARSHPHAL_ENGINE)} chars")
print(f"LK aspects code : {len(LK_ASPECTS_CODE)} chars")
print(f"Transit save    : {len(TRANSIT_SAVE_CODE)} chars")
