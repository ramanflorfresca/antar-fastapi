"""
antar_engine/proof_points.py  — COMPLETE REWRITE
LLM-powered proof points using full astrological analysis.
No templates. Real Jyotish analysis sent to LLM.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
import os

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

PLANET_DOMAIN = {
    "Sun":     "career, authority, father, ego",
    "Moon":    "mind, mother, home, emotions, public",
    "Mars":    "property, siblings, energy, disputes, courage",
    "Mercury": "communication, business, intellect, friends",
    "Jupiter": "wealth, children, wisdom, teacher, expansion",
    "Venus":   "marriage, relationships, luxury, beauty, vehicles",
    "Saturn":  "career restructuring, delays, discipline, servants, longevity",
    "Rahu":    "sudden changes, foreign matters, technology, obsession, transformation",
    "Ketu":    "spirituality, moksha, past life, detachment, sudden losses",
}

KEY_HOUSE_MEANINGS = {
    1:  "self, body, personality, overall life direction",
    2:  "wealth, family, speech, accumulated assets",
    4:  "home, mother, property, happiness, land",
    5:  "children, intelligence, past karma, speculation, creative projects",
    6:  "enemies, disease, debt, service, competition",
    7:  "marriage, partnerships, legal contracts, business partnerships",
    8:  "transformation, longevity, hidden matters, inheritance, occult",
    9:  "dharma, father, fortune, higher education, spirituality",
    10: "career, profession, public life, government, social standing",
    11: "gains, income, elder siblings, aspirations, social networks",
    12: "losses, spirituality, foreign lands, moksha, expenditure",
}


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except Exception:
        return datetime.utcnow()


def _format_date_range(start_dt: datetime, end_dt: datetime) -> str:
    def season(dt):
        m = dt.month
        if m <= 3:   return f"early {dt.year}"
        elif m <= 6: return f"mid-{dt.year}"
        else:        return f"late {dt.year}"
    if start_dt.year == end_dt.year:
        return f"During {start_dt.year}"
    elif end_dt.year - start_dt.year <= 2:
        return f"Between {start_dt.year} and {end_dt.year}"
    return f"Between {season(start_dt)} and {season(end_dt)}"


def _build_chart_brief(
    chart_data: dict,
    dashas: dict,
    birth_date: str,
    age: int,
    gender: str,
    first_name: str,
    yogas: list,
    divisional_charts: dict,
) -> str:
    """Build comprehensive astrological brief for LLM."""

    lagna = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign", "") if isinstance(lagna, dict) else str(lagna)
    planets = chart_data.get("planets", {})

    lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

    # ── D1 Planet positions ─────────────────────────────────────
    planet_lines = []
    for planet, data in planets.items():
        sign = data.get("sign", "")
        house = data.get("house", "")
        nak = data.get("nakshatra", "")
        retro = "R" if data.get("retrograde") else ""
        domain = PLANET_DOMAIN.get(planet, "")
        house_meaning = KEY_HOUSE_MEANINGS.get(int(house) if str(house).isdigit() else 0, "")
        planet_lines.append(
            f"  {planet}{retro}: {sign}, house {house} ({house_meaning}) — rules: {domain}"
        )

    # ── House lords ─────────────────────────────────────────────
    house_lord_lines = []
    for h in [1,2,4,5,7,8,9,10,11,12]:
        sign_idx = (lagna_idx + h - 1) % 12
        sign = SIGNS[sign_idx]
        lord = SIGN_LORDS.get(sign, "")
        lord_house = planets.get(lord, {}).get("house", "?")
        house_lord_lines.append(
            f"  {h}th house lord: {lord} in house {lord_house}"
        )

    # ── Conjunctions and aspects ────────────────────────────────
    conj_lines = []
    planet_list = list(planets.keys())
    for i, p1 in enumerate(planet_list):
        for p2 in planet_list[i+1:]:
            h1 = planets[p1].get("house", 0)
            h2 = planets[p2].get("house", 0)
            if h1 and h2 and h1 == h2:
                conj_lines.append(f"  {p1} conjunct {p2} in house {h1} ({KEY_HOUSE_MEANINGS.get(h1,'')})")

    # ── Past dashas ──────────────────────────────────────────────
    now = datetime.utcnow()
    vim = dashas.get("vimsottari", [])

    past_md_lines = []
    current_md = None
    current_ad = None

    for row in vim:
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign", "")
        level = row.get("level") or row.get("type", "")
        sd    = _parse_dt(row.get("start_date") or row.get("start", ""))
        ed    = _parse_dt(row.get("end_date")   or row.get("end", ""))
        dr    = _format_date_range(sd, ed)

        if level == "mahadasha":
            if ed < now:
                past_md_lines.append(
                    f"  {lord} Mahadasha {dr} — "
                    f"domain: {PLANET_DOMAIN.get(lord,'')}"
                )
            elif sd <= now <= ed:
                current_md = (lord, dr)
        elif level == "antardasha":
            if sd <= now <= ed:
                current_ad = (lord, dr)

    # ── Yogas ────────────────────────────────────────────────────
    strong_yogas   = [y for y in yogas if y.get("strength") == "strong"]
    moderate_yogas = [y for y in yogas if y.get("strength") == "moderate"]

    # ── D9 and D10 summaries ─────────────────────────────────────
    d9  = divisional_charts.get("d9", {})
    d10 = divisional_charts.get("d10", {})

    d9_lagna = d9.get("lagna", "unknown")
    d9_venus = d9.get("planets", {}).get("Venus", {})
    d9_moon  = d9.get("planets", {}).get("Moon", {})

    d10_lagna = d10.get("lagna", "unknown")
    d10_sun   = d10.get("planets", {}).get("Sun", {})
    d10_sat   = d10.get("planets", {}).get("Saturn", {})
    d10_jup   = d10.get("planets", {}).get("Jupiter", {})

    # ── Life stage ───────────────────────────────────────────────
    if age < 28:   life_stage = "Brahmacharya (student/formation, pre-Saturn return)"
    elif age < 50: life_stage = "Grihastha (householder/building, prime life)"
    elif age < 72: life_stage = "Vanaprastha (wisdom/legacy, post-peak)"
    else:          life_stage = "Sannyasa (liberation/completion)"

    name_str = first_name if first_name else "the person"
    gender_note = ""
    if gender and gender.lower() in ("female","woman","f"):
        gender_note = f"Gender: Female — predictions should emphasize relational, emotional, and family domains where relevant."
    elif gender and gender.lower() in ("male","man","m"):
        gender_note = f"Gender: Male — predictions should emphasize career, authority, and action domains where relevant."

    # ── Lal Kitab house rules ────────────────────────────────────
    lk_lines = []
    for planet, data in planets.items():
        house = data.get("house", 0)
        if not house:
            continue
        lk_lines.append(f"  {planet} in house {house}: {_lal_kitab_rule(planet, int(house))}")

    brief = f"""
=== COMPLETE ASTROLOGICAL BRIEF FOR PROOF POINTS ===

PERSON: {name_str}, Age {age}, DOB {birth_date}
Life Stage: {life_stage}
{gender_note}

=== D1 NATAL CHART ===
Lagna (Rising Sign): {lagna_sign}
Lagna Lord: {SIGN_LORDS.get(lagna_sign,'')} in house {planets.get(SIGN_LORDS.get(lagna_sign,''),{{}}).get('house','?')}

PLANETARY POSITIONS:
{chr(10).join(planet_lines)}

HOUSE LORDS:
{chr(10).join(house_lord_lines[:8])}

CONJUNCTIONS:
{chr(10).join(conj_lines) if conj_lines else "  No major conjunctions"}

=== STRONG YOGAS ===
{chr(10).join(f"  • {y['name']}: {y['effect']}" for y in strong_yogas) if strong_yogas else "  None"}

MODERATE YOGAS:
{chr(10).join(f"  • {y['name']}: {y['effect']}" for y in moderate_yogas[:4]) if moderate_yogas else "  None"}

=== D9 NAVAMSA (Soul and Marriage) ===
D9 Lagna: {d9_lagna}
Venus in D9: {d9_venus.get('sign','?')} house {d9_venus.get('house','?')} (marriage/relationship quality)
Moon in D9: {d9_moon.get('sign','?')} house {d9_moon.get('house','?')} (emotional fulfillment)

=== D10 DASHAMSA (Career) ===
D10 Lagna: {d10_lagna}
Sun in D10: house {d10_sun.get('house','?')} (leadership/authority in career)
Saturn in D10: house {d10_sat.get('house','?')} (discipline/longevity in career)
Jupiter in D10: house {d10_jup.get('house','?')} (expansion/wisdom in career)

=== VIMSOTTARI DASHA HISTORY ===
PAST COMPLETED CHAPTERS (use these for proof points):
{chr(10).join(past_md_lines) if past_md_lines else "  No completed mahadashas"}

CURRENT CHAPTER: {f"{current_md[0]} Mahadasha ({current_md[1]})" if current_md else "unknown"}
Current Sub-period: {f"{current_ad[0]} Antardasha" if current_ad else "unknown"}

=== LAL KITAB HOUSE ANALYSIS ===
{chr(10).join(lk_lines[:6])}

=== END OF ASTROLOGICAL BRIEF ===
"""
    return brief


def _lal_kitab_rule(planet: str, house: int) -> str:
    """Basic Lal Kitab interpretation for planet in house."""
    LK_RULES = {
        ("Sun",1):    "Strong personality, father's influence dominant, leadership from early life",
        ("Sun",10):   "Career success, authority in profession, father's legacy in work",
        ("Sun",12):   "Career struggles, father issues, spiritual path, foreign connections",
        ("Moon",1):   "Emotional personality, mother's strong influence, public life prominent",
        ("Moon",4):   "Happy home life, mother's blessings, property gains",
        ("Moon",12):  "Emotional isolation, spiritual depth, foreign lands, mother separation",
        ("Mars",1):   "Aggressive, energetic, initiator, early life full of action",
        ("Mars",7):   "Conflict in partnerships, strong-willed spouse, business through force",
        ("Mars",8):   "Sudden events, accidents possible, interest in hidden matters",
        ("Mercury",1):"Intelligent, communicative, business-minded from youth",
        ("Mercury",10):"Business success, communication career, multiple income streams",
        ("Jupiter",1): "Blessed life, wisdom, teacher's energy, generally protected",
        ("Jupiter",9): "Religious, dharmic, fortunate father, higher education",
        ("Jupiter",10):"Career in teaching/law/religion/finance, respected professionally",
        ("Venus",1):  "Beautiful appearance, artistic nature, love life prominent",
        ("Venus",7):  "Loving marriage, beautiful spouse, success through partnerships",
        ("Venus",12): "Expenditure on luxury, secret relationships, foreign pleasures",
        ("Saturn",1): "Slow start, disciplined life, hardship builds character",
        ("Saturn",8): "Long life, interest in occult, hidden enemies, inheritance themes",
        ("Saturn",10):"Career through hard work, delayed success, respected in old age",
        ("Saturn",12):"Spiritual liberation, foreign settlement, detachment",
        ("Rahu",1):   "Unusual personality, foreign influence, unconventional life path",
        ("Rahu",7):   "Unusual marriage, foreign spouse possible, unconventional partnerships",
        ("Ketu",1):   "Spiritual nature, detached personality, past life abilities",
        ("Ketu",12):  "Moksha indicator, spiritual liberation, loss of material attachment",
    }
    return LK_RULES.get((planet, house),
           f"{planet} in {house}th house — active {PLANET_DOMAIN.get(planet,'')} themes through this life area")


def _build_proof_points_prompt(
    chart_brief: str,
    birth_date: str,
    age: int,
    first_name: str,
) -> str:
    """Build the LLM prompt for proof point generation."""

    name_str = first_name if first_name else "this person"

    return f"""You are a master Vedic astrologer with 30 years of experience.
You are given a complete astrological brief for {name_str}, age {age}.

{chart_brief}

TASK: Generate exactly 3 proof points — past life events that this chart 
predicts happened. These will be shown to the person as "We'll tell you 
3 things that already happened in your life."

STRICT RULES:
1. Base each proof point on SPECIFIC completed dasha periods from the chart
2. Reference SPECIFIC planets, houses, and their significations
3. Make statements specific enough to feel personal but accurate enough to land
4. NEVER use astrology jargon (no "mahadasha", "dasha", "Rahu", planet names)
5. Write in past tense — these already happened
6. Account for age: {name_str} is {age} years old
   - If 60+: NO love/romance predictions. Focus on: career legacy, family,
     health patterns, spiritual development, financial situations, property
   - If 40-60: career shifts, relationship depth, children themes, wealth
   - If 25-40: identity formation, career building, love/marriage
   - If under 25: education, early career, family separation, identity
7. Each statement should have a specific date range tied to a real dasha period
8. The confidence score reflects how strong the astrological indicators are

DOMAIN GUIDANCE based on age {age}:
{"Focus on: career legacy, health patterns, family/children situations, spiritual development, financial/property matters. Do NOT generate love/romance predictions." if age >= 60 else "All domains relevant: career, relationships, home, identity, finances." if age >= 35 else "Focus on: identity formation, career beginnings, education, family dynamics, early relationships."}

OUTPUT FORMAT (return valid JSON only, no other text):
{{
  "proof_points": [
    {{
      "statement": "Between [year] and [year], [specific past-tense statement about what happened in their life]",
      "date_range": "Between [year] and [year]",
      "domain": "career|home|identity|finances|family|health|relationships",
      "domain_label": "[human readable label]",
      "confidence": 0.75,
      "astrological_basis": "[brief internal note on which planets/houses drove this — NOT shown to user]",
      "follow_up": "[if user says 'not quite', this clarifies what else it could mean]"
    }}
  ]
}}

EXAMPLE of quality output for a 68-year-old:
{{
  "statement": "Between 2013 and 2023, you went through a decade-long period of deepening — professionally you moved from building to sustaining, and something significant in your family structure or living situation changed, possibly more than once. This was a period of processing what your life had meant rather than pushing toward new goals.",
  "date_range": "Between 2013 and 2023",
  "domain": "identity",
  "domain_label": "Life Direction & Legacy",
  "confidence": 0.82,
  "astrological_basis": "Moon Mahadasha 2013-2023, Moon in 12th house conjunct Saturn — emotional withdrawal, isolation, processing of the past",
  "follow_up": "This may have shown up as a health pattern requiring more attention, or as a shift in your relationship with your own parents or children."
}}

Now generate 3 specific proof points for {name_str} (age {age}) based on 
their actual chart. Make each one feel like you know their life.
"""


async def generate_proof_points_llm(
    birth_date: str,
    chart_data: dict,
    dashas: dict,
    first_name: str = "",
    gender: str = "",
    yogas: list = None,
    divisional_charts: dict = None,
) -> list:
    """
    Generate proof points using LLM with full astrological context.
    This replaces the template-based approach entirely.
    """
    import json
    from datetime import date

    if yogas is None:
        yogas = []
    if divisional_charts is None:
        divisional_charts = {}

    # Calculate age
    try:
        born = date.fromisoformat(birth_date[:10])
        age = (date.today() - born).days // 365
    except Exception:
        age = 35

    # Build comprehensive chart brief
    chart_brief = _build_chart_brief(
        chart_data=chart_data,
        dashas=dashas,
        birth_date=birth_date,
        age=age,
        gender=gender,
        first_name=first_name,
        yogas=yogas,
        divisional_charts=divisional_charts,
    )

    # Build LLM prompt
    prompt = _build_proof_points_prompt(chart_brief, birth_date, age, first_name)

    # Call LLM
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        )
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a master Vedic astrologer. Return only valid JSON."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
            timeout=45,
        )
        raw = response.choices[0].message.content.strip()

        # Clean JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        points = data.get("proof_points", [])

        # Ensure domain_icon
        DOMAIN_ICONS = {
            "career":"💼","home":"🏠","identity":"🔄","finances":"💰",
            "family":"👨‍👩‍👧","health":"⚡","relationships":"💫"
        }
        for p in points:
            p["domain_icon"] = DOMAIN_ICONS.get(p.get("domain",""), "✦")

        return points[:3]

    except Exception as e:
        print(f"[proof_points] LLM error: {e}")
        return _fallback_proof_points(chart_data, dashas, birth_date, age)


def _fallback_proof_points(
    chart_data: dict, dashas: dict,
    birth_date: str, age: int
) -> list:
    """
    Fallback to improved template system if LLM fails.
    Still uses actual dasha dates and chart data.
    """
    now = datetime.utcnow()
    vim = dashas.get("vimsottari", [])

    past_periods = []
    for row in vim:
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign","")
        level = row.get("level") or row.get("type","")
        sd    = _parse_dt(row.get("start_date") or row.get("start",""))
        ed    = _parse_dt(row.get("end_date")   or row.get("end",""))
        if ed < now and level == "mahadasha" and lord not in ("Mercury",):
            past_periods.append((lord, sd, ed))

    past_periods.sort(key=lambda x: x[2], reverse=True)

    HIGH_IMPACT_TEMPLATES = {
        "Rahu":   "A major transformation reshaped your life direction — old structures fell away and something new and unfamiliar began forming.",
        "Saturn": "A period of sustained pressure and restructuring demanded discipline and patience. What was built during this time was built to last.",
        "Ketu":   "Something significant came to an end — a chapter closed, a relationship or role was released, and a quieter, more inward phase began.",
        "Mars":   "A high-energy, high-stakes period — action was required, conflicts came to a head, and decisive moves were made.",
        "Jupiter":"An expansion phase opened doors — growth, opportunity, and optimism made this period qualitatively different from what came before.",
        "Venus":  "Your relationships or creative life went through significant change — something in how you loved or what you valued shifted.",
        "Moon":   "Your home life, family situation, or emotional foundations went through meaningful change.",
        "Sun":    "Your career identity or relationship with authority underwent a significant shift.",
    }

    DOMAIN_ICONS = {
        "career":"💼","home":"🏠","identity":"🔄","finances":"💰",
        "family":"👨‍👩‍👧","health":"⚡","relationships":"💫"
    }

    points = []
    used_domains = set()
    DOMAINS = {"Rahu":"identity","Saturn":"career","Ketu":"identity",
               "Mars":"career","Jupiter":"finances","Venus":"relationships",
               "Moon":"home","Sun":"career"}

    for lord, sd, ed in past_periods[:6]:
        if len(points) >= 3:
            break
        template = HIGH_IMPACT_TEMPLATES.get(lord)
        if not template:
            continue
        domain = DOMAINS.get(lord, "identity")
        if domain in used_domains:
            domain = "identity" if domain != "identity" else "finances"
        if domain in used_domains:
            continue

        dr = _format_date_range(sd, ed)
        points.append({
            "statement":    f"{dr}, {template}",
            "date_range":   dr,
            "domain":       domain,
            "domain_label": domain.replace("_"," ").title(),
            "domain_icon":  DOMAIN_ICONS.get(domain,"✦"),
            "confidence":   0.72,
            "follow_up":    "This may have shown up more subtly — as a shift in values or priorities rather than a dramatic external event.",
            "planet":       lord,
        })
        used_domains.add(domain)

    return points


# ── Keep synchronous wrapper for backward compatibility ───────────────────────
def generate_proof_points(
    birth_date: str,
    chart_data: dict,
    dashas: dict,
    first_name: str = "",
    gender: str = "",
    lagna_sign: str = "",
    yogas: list = None,
    divisional_charts: dict = None,
) -> list:
    """
    Synchronous wrapper — falls back to template system.
    The async LLM version is called directly from main.py.
    """
    from datetime import date
    try:
        born = date.fromisoformat(birth_date[:10])
        age  = (date.today() - born).days // 365
    except Exception:
        age = 35

    return _fallback_proof_points(chart_data, dashas, birth_date, age)


# ── Score evaluation ─────────────────────────────────────────────────────────
def evaluate_proof_score(responses: list) -> dict:
    correct = sum(1 for r in responses if r in ("yes","correct"))
    partial = sum(1 for r in responses if r in ("partial","not_quite","partially"))
    total   = len(responses) or 3
    pct     = round((correct + partial * 0.5) / total * 100)

    if pct >= 80:
        return {"score":correct,"accuracy_pct":pct,"verdict":"strong",
                "headline":"Your chart is unusually clear.",
                "sub_headline":"That level of match is not coincidence. This pattern runs deep.",
                "cta_text":"See What's Coming →","offer_free_month":False}
    elif pct >= 50:
        return {"score":correct,"accuracy_pct":pct,"verdict":"good",
                "headline":f"{pct}% match. That is significant.",
                "sub_headline":"The one that didn't land may still be true — some periods are processed years later.",
                "cta_text":"See What's Coming →","offer_free_month":False}
    else:
        return {"score":correct,"accuracy_pct":pct,"verdict":"free_month",
                "headline":"Your first month is on us.",
                "sub_headline":"We want to earn your trust. Use your free month.",
                "cta_text":"Start Free →","offer_free_month":True}
