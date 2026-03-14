"""
antar_engine/daily_prediction_engine.py

Daily signal engine — generates a rich daily reading that includes:
1. Today's planetary hour and its effect
2. Active transits hitting natal chart today
3. Dasha sub-period activation
4. WOW moment detection (rare planetary events today)
5. Ayurveda daily tip based on Moon nakshatra
6. Lal Kitab daily remedy
7. Auspicious timing windows today
"""

from datetime import datetime, date, timedelta
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

# Planetary hours — sequence from sunrise
# Each day starts with its day lord
# Sequence: Sun, Venus, Mercury, Moon, Saturn, Jupiter, Mars (repeating)
PLANETARY_HOUR_SEQUENCE = ["Sun","Venus","Mercury","Moon","Saturn","Jupiter","Mars"]

DAY_LORD = {
    0: "Moon",    # Monday
    1: "Mars",    # Tuesday
    2: "Mercury", # Wednesday
    3: "Jupiter", # Thursday
    4: "Venus",   # Friday
    5: "Saturn",  # Saturday
    6: "Sun",     # Sunday
}

MOON_NAKSHATRA_TIPS = {
    "Ashvini":         {"energy":"high initiative", "dosha":"Vata", "tip":"Start new projects today. Avoid scattered energy.", "food":"light grains, ginger tea"},
    "Bharani":         {"energy":"intense creation", "dosha":"Pitta", "tip":"Channel intensity into creative work.", "food":"cooling foods, coconut water"},
    "Krittika":        {"energy":"sharp focus", "dosha":"Pitta", "tip":"Excellent for precision work and decisions.", "food":"avoid spicy food today"},
    "Rohini":          {"energy":"abundance", "dosha":"Kapha", "tip":"Perfect for business and relationship nurturing.", "food":"dairy, rice, sweet items"},
    "Mrigashira":      {"energy":"curious seeking", "dosha":"Vata", "tip":"Research and learning favored today.", "food":"warm herbal teas, nuts"},
    "Ardra":           {"energy":"transformative storm", "dosha":"Vata", "tip":"Expect changes. Stay grounded.", "food":"warm cooked food only"},
    "Punarvasu":       {"energy":"renewal", "dosha":"Vata", "tip":"Return to basics. Rest and restore.", "food":"light nourishing food"},
    "Pushya":          {"energy":"nourishing", "dosha":"Kapha", "tip":"Best nakshatra for starting anything sacred.", "food":"milk, ghee, traditional foods"},
    "Ashlesha":        {"energy":"penetrating", "dosha":"Kapha", "tip":"Avoid new beginnings. Good for research.", "food":"detoxifying foods"},
    "Magha":           {"energy":"royal authority", "dosha":"Kapha", "tip":"Assert your authority with grace.", "food":"nutritious, quality food"},
    "Purva Phalguni":  {"energy":"pleasure seeking", "dosha":"Pitta", "tip":"Enjoy beauty and creativity.", "food":"sweet fruits, rose water"},
    "Uttara Phalguni": {"energy":"stable foundation", "dosha":"Pitta", "tip":"Excellent for contracts and commitments.", "food":"balanced wholesome meal"},
    "Hasta":           {"energy":"craftsmanship", "dosha":"Vata", "tip":"Hands-on work produces excellent results.", "food":"light salads, fresh juice"},
    "Chitra":          {"energy":"creation", "dosha":"Pitta", "tip":"Beautify your environment and work.", "food":"colorful fresh foods"},
    "Swati":           {"energy":"independent movement", "dosha":"Vata", "tip":"Go with the flow. Avoid forcing outcomes.", "food":"vata-pacifying warm foods"},
    "Vishakha":        {"energy":"purposeful striving", "dosha":"Pitta", "tip":"Set clear goals. Push toward them.", "food":"cooling pitta foods"},
    "Anuradha":        {"energy":"devoted friendship", "dosha":"Pitta", "tip":"Strengthen relationships and alliances.", "food":"moderate balanced meals"},
    "Jyeshtha":        {"energy":"protective leadership", "dosha":"Vata", "tip":"Take charge. Protect those in your care.", "food":"warm root vegetables"},
    "Mula":            {"energy":"root investigation", "dosha":"Vata", "tip":"Go to the root of any issue.", "food":"grounding root vegetables"},
    "Purva Ashadha":   {"energy":"invincible momentum", "dosha":"Pitta", "tip":"Your convictions carry you forward.", "food":"cooling hydrating foods"},
    "Uttara Ashadha":  {"energy":"final victory", "dosha":"Pitta", "tip":"Complete what you started.", "food":"wholesome balanced"},
    "Shravana":        {"energy":"deep listening", "dosha":"Kapha", "tip":"Listen more than you speak today.", "food":"traditional nourishing foods"},
    "Dhanishtha":      {"energy":"rhythmic abundance", "dosha":"Pitta", "tip":"Music and rhythm improve everything today.", "food":"iron-rich foods"},
    "Shatabhisha":     {"energy":"healing solitude", "dosha":"Vata", "tip":"Solo work and healing are favored.", "food":"herbal medicines, water"},
    "Purva Bhadrapada":{"energy":"fierce transformation", "dosha":"Pitta", "tip":"Deep change is happening. Trust it.", "food":"sattvic pure foods"},
    "Uttara Bhadrapada":{"energy":"deep wisdom", "dosha":"Kapha", "tip":"Contemplation and wisdom work best.", "food":"nourishing kapha foods"},
    "Revati":          {"energy":"compassionate completion", "dosha":"Kapha", "tip":"Complete cycles with love.", "food":"gentle easily digestible"},
}

PLANET_ENERGY_TODAY = {
    "Sun":     "Authority, clarity, and leadership energy is heightened",
    "Moon":    "Emotional intelligence and public connection are amplified",
    "Mars":    "Action, courage, and physical energy peak today",
    "Mercury": "Communication, deals, and analytical thinking are sharp",
    "Jupiter": "Expansion, wisdom, and generosity flow easily",
    "Venus":   "Beauty, love, and creative expression are heightened",
    "Saturn":  "Discipline, responsibility, and long-term thinking prevail",
    "Rahu":    "Foreign connections and unconventional opportunities emerge",
    "Ketu":    "Spiritual insights and detachment bring clarity",
}

WOW_DAILY_TRIGGERS = {
    "moon_conjunct_jupiter": {
        "name": "Moon meets Jupiter today",
        "wow":  "This is a Gajakesari moment — rare alignment of mind and wisdom. Decisions made today carry unusual fortune. Trust your gut on big matters.",
        "rarity": "uncommon",
    },
    "moon_in_pushya": {
        "name": "Moon in Pushya Nakshatra",
        "wow":  "Pushya is the most auspicious nakshatra for beginnings. If you start something today — a business, a journey, a commitment — it carries divine blessing.",
        "rarity": "monthly",
    },
    "jupiter_transit_change": {
        "name": "Jupiter changing signs",
        "wow":  "Jupiter moves to a new sign — a major 12-month cycle shift begins. The area of life Jupiter is entering gets a year of expansion and opportunity.",
        "rarity": "annual",
    },
    "moon_on_natal_sun": {
        "name": "Moon activating your Sun today",
        "wow":  "The Moon is transiting your natal Sun's position — your identity, authority, and public presence are spotlit today. Be visible. Lead.",
        "rarity": "monthly",
    },
    "moon_on_natal_moon": {
        "name": "Moon returns to natal Moon",
        "wow":  "Monthly Moon return — your emotional intelligence peaks. Intuition is at maximum. Trust what you feel today over what you think.",
        "rarity": "monthly",
    },
    "moon_on_natal_jupiter": {
        "name": "Moon activating your Jupiter today",
        "wow":  "Fortune is spotlit. What you reach for today has an extra blessing on it. Good day for important asks, launches, and financial decisions.",
        "rarity": "monthly",
    },
    "full_moon": {
        "name": "Full Moon — Purnima",
        "wow":  "Emotions peak, manifestations complete, and the month's energy comes to a head. What did you set in motion at the New Moon? It reaches fullness now.",
        "rarity": "monthly",
    },
    "new_moon": {
        "name": "New Moon — Amavasya",
        "wow":  "The darkest moment before the new cycle. Perfect for internal work, ancestor prayers, and setting intentions for the coming month.",
        "rarity": "monthly",
    },
}


def get_current_moon_nakshatra(natal_chart: dict = None) -> tuple:
    """Get current Moon nakshatra from Swiss Ephemeris."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        now = datetime.utcnow()
        jd  = swe.julday(now.year, now.month, now.day,
                          now.hour + now.minute/60.0)
        pos, _ = swe.calc_ut(jd, swe.MOON)
        ayanamsa    = swe.get_ayanamsa(jd)
        sidereal    = (pos[0] - ayanamsa) % 360

        NAKSHATRAS = [
            "Ashvini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
            "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
            "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
            "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha",
            "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati",
        ]

        nak_idx  = int(sidereal / (360/27))
        nak_name = NAKSHATRAS[nak_idx % 27]
        moon_sign= SIGNS[int(sidereal / 30)]
        return nak_name, moon_sign, round(sidereal % 30, 2)
    except Exception as e:
        return "Rohini", "Taurus", 0.0


def get_todays_planetary_hour() -> dict:
    """Calculate current planetary hour."""
    now     = datetime.now()
    weekday = now.weekday()
    day_lord= DAY_LORD[weekday]

    # Find position in hour sequence starting from day lord
    day_lord_idx = PLANETARY_HOUR_SEQUENCE.index(day_lord)
    hour_of_day  = now.hour  # 0-23

    # Each day has 24 planetary hours
    current_hour_lord_idx = (day_lord_idx + hour_of_day) % 7
    current_hour_lord = PLANETARY_HOUR_SEQUENCE[current_hour_lord_idx]

    return {
        "day_lord":          day_lord,
        "current_hour_lord": current_hour_lord,
        "hour_energy":       PLANET_ENERGY_TODAY.get(current_hour_lord, ""),
        "best_activity": {
            "Sun":     "authority decisions, career moves, meetings with seniors",
            "Moon":    "emotional conversations, public work, family matters",
            "Mars":    "physical work, gym, courage-requiring tasks",
            "Mercury": "emails, contracts, negotiations, study",
            "Jupiter": "teaching, learning, financial planning, spiritual practice",
            "Venus":   "creative work, relationships, beauty, pleasure",
            "Saturn":  "systematic work, long-term planning, discipline",
        }.get(current_hour_lord, "general work"),
    }


def detect_daily_wow(natal_chart: dict, current_moon_nak: str,
                     current_moon_sign: str) -> list:
    """Detect WOW moments active today."""
    wow_today = []
    now       = datetime.utcnow()
    planets   = natal_chart.get("planets", {})

    # Moon in Pushya
    if current_moon_nak == "Pushya":
        wow_today.append(WOW_DAILY_TRIGGERS["moon_in_pushya"])

    # Moon return to natal positions
    natal_moon_sign = planets.get("Moon", {}).get("sign","")
    if current_moon_sign == natal_moon_sign:
        wow_today.append(WOW_DAILY_TRIGGERS["moon_on_natal_moon"])

    natal_sun_sign = planets.get("Sun", {}).get("sign","")
    if current_moon_sign == natal_sun_sign:
        wow_today.append(WOW_DAILY_TRIGGERS["moon_on_natal_sun"])

    natal_jup_sign = planets.get("Jupiter", {}).get("sign","")
    if current_moon_sign == natal_jup_sign:
        wow_today.append(WOW_DAILY_TRIGGERS["moon_on_natal_jupiter"])

    # Full/New Moon check
    try:
        import swisseph as swe
        jd = swe.julday(now.year, now.month, now.day, now.hour)
        sun_pos,  _ = swe.calc_ut(jd, swe.SUN)
        moon_pos, _ = swe.calc_ut(jd, swe.MOON)
        diff = abs(moon_pos[0] - sun_pos[0]) % 360
        if diff > 180: diff = 360 - diff
        if diff < 12:
            wow_today.append(WOW_DAILY_TRIGGERS["new_moon"])
        elif abs(diff - 180) < 12:
            wow_today.append(WOW_DAILY_TRIGGERS["full_moon"])
    except Exception:
        pass

    return wow_today[:3]  # max 3 WOW moments per day


def build_daily_prediction_prompt(
    natal_chart: dict,
    dashas: dict,
    birth_date: str,
    first_name: str = "",
    gender: str = "",
    current_md_lord: str = "",
    current_ad_lord: str = "",
    concern: str = "general",
) -> str:
    """
    Build the complete daily prediction context for LLM.
    Includes WOW moments, planetary hours, Moon nakshatra, and dasha.
    """
    now     = datetime.now()
    weekday = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][now.weekday()]
    date_str= now.strftime("%B %d, %Y")

    moon_nak, moon_sign, moon_deg = get_current_moon_nakshatra(natal_chart)
    planetary_hour = get_todays_planetary_hour()
    wow_today      = detect_daily_wow(natal_chart, moon_nak, moon_sign)
    nak_data       = MOON_NAKSHATRA_TIPS.get(moon_nak, {})

    # Current dasha context
    dasha_str = f"{current_md_lord}-{current_ad_lord}" if current_ad_lord else current_md_lord

    # Age and life stage
    try:
        age = (date.today() - date.fromisoformat(birth_date[:10])).days // 365
    except Exception:
        age = 35

    name = first_name or "Explorer"

    wow_block = ""
    if wow_today:
        wow_block = "\n⭐ TODAY'S WOW MOMENTS:\n"
        for w in wow_today:
            wow_block += f"  {w['name']}: {w['wow']}\n"

    prompt = f"""You are Antar — a precise Vedic astrology AI.
Generate TODAY'S DAILY SIGNAL for {name}, age {age}.

TODAY: {weekday}, {date_str}

COSMIC WEATHER TODAY:
  Moon: {moon_sign} ({moon_nak} nakshatra, {moon_deg}°)
  Moon nakshatra energy: {nak_data.get('energy','')}
  Dosha activated: {nak_data.get('dosha','')}
  Ayurveda tip: {nak_data.get('tip','')}
  Food recommendation: {nak_data.get('food','')}

PLANETARY HOUR NOW:
  Day lord: {planetary_hour['day_lord']}
  Current hour lord: {planetary_hour['current_hour_lord']}
  Hour energy: {planetary_hour['hour_energy']}
  Best for: {planetary_hour['best_activity']}
{wow_block}
NATAL CHART CONTEXT:
  Lagna: {natal_chart.get('lagna',{{}}).get('sign','') if isinstance(natal_chart.get('lagna'),dict) else ''}
  Moon: {natal_chart.get('planets',{{}}).get('Moon',{{}}).get('sign','')} in {natal_chart.get('planets',{{}}).get('Moon',{{}}).get('nakshatra','')}
  Active Dasha: {dasha_str}
  Atmakaraka: {natal_chart.get('atmakaraka','')}

GENERATE A DAILY SIGNAL with these exact sections:

**YOUR SIGNAL RIGHT NOW**
[2 sentences — what is the dominant energy today for THIS person based on their natal chart + today's cosmic weather. Make it specific to their Moon nakshatra and current dasha. Do NOT be generic.]

**THE PATTERN THAT'S ACTIVE**
[2 sentences — how does today's energy interact with their current dasha period. What theme is being amplified?]

**TODAY'S WOW** (only include if wow_today has items)
[1-2 sentences — explain the WOW moment in plain language. Make it feel special and rare.]

**YOUR MOVE TODAY**
[Exactly 2 lines:]
Start: [one specific action to take today]
Slow down on: [one specific thing to avoid today]

**AYURVEDA TODAY**
[1 sentence — the specific food or practice for today's Moon nakshatra energy]

**TODAY'S REMEDY**
[1 Lal Kitab or planetary remedy specific to their current dasha lord]

Rules:
- NO generic horoscope language
- Reference the specific nakshatra ({moon_nak}) by name
- Reference their current dasha ({dasha_str}) specifically
- Keep total under 250 words
- Make {name} feel seen — not like one of millions
"""
    return prompt


async def generate_daily_signal(
    natal_chart: dict,
    dashas: dict,
    birth_date: str,
    chart_id: str,
    first_name: str = "",
    gender: str = "",
    language: str = "en",
) -> dict:
    """
    Generate and cache daily signal.
    Checks if today's signal already exists in DB before calling LLM.
    """
    import openai
    from supabase import create_client

    today = date.today().isoformat()

    try:
        sb = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        )

        # Check cache — don't regenerate if already done today
        cached = sb.table("daily_signals").select("*").eq(
            "chart_id", chart_id
        ).eq("signal_date", today).execute()

        if cached.data:
            return cached.data[0]
    except Exception:
        sb = None

    # Get current dasha
    now = datetime.utcnow()
    current_md = current_ad = ""
    for row in dashas.get("vimsottari", []):
        level = row.get("level") or row.get("type","")
        try:
            sd = datetime.strptime(str(row.get("start_date",""))[:10],"%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date",""))[:10],"%Y-%m-%d")
            if sd <= now <= ed:
                lord = row.get("lord_or_sign") or row.get("planet_or_sign","")
                if level == "mahadasha":   current_md = lord
                elif level == "antardasha": current_ad = lord
        except Exception:
            pass

    # Build prompt
    prompt = build_daily_prediction_prompt(
        natal_chart=natal_chart, dashas=dashas,
        birth_date=birth_date, first_name=first_name,
        gender=gender, current_md_lord=current_md,
        current_ad_lord=current_ad,
    )

    # Call LLM
    system_prompt = (
        "You are Antar — a precise Vedic astrology AI. "
        "Generate daily signals that feel personal and specific — never generic. "
        "Reference the exact nakshatra, dasha period, and natal chart provided. "
        "Be direct and concrete. Maximum 250 words total."
    )

    try:
        client = openai.AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        )
        resp = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":prompt},
            ],
            temperature=0.4,
            max_tokens=600,
            timeout=30,
        )
        signal_text = resp.choices[0].message.content.strip()
    except Exception as e:
        signal_text = f"Daily signal unavailable: {e}"

    # Detect WOW
    moon_nak, moon_sign, _ = get_current_moon_nakshatra(natal_chart)
    wow_today = detect_daily_wow(natal_chart, moon_nak, moon_sign)
    planetary_hour = get_todays_planetary_hour()

    result = {
        "chart_id":       chart_id,
        "signal_date":    today,
        "signal_text":    signal_text,
        "moon_nakshatra": moon_nak,
        "moon_sign":      moon_sign,
        "day_lord":       planetary_hour["day_lord"],
        "hour_lord":      planetary_hour["current_hour_lord"],
        "wow_today":      wow_today,
        "has_wow":        len(wow_today) > 0,
        "dasha_string":   f"{current_md}-{current_ad}" if current_ad else current_md,
        "ayurveda_tip":   MOON_NAKSHATRA_TIPS.get(moon_nak,{}).get("tip",""),
        "food_today":     MOON_NAKSHATRA_TIPS.get(moon_nak,{}).get("food",""),
    }

    # Cache in DB
    try:
        if sb:
            sb.table("daily_signals").upsert(result,
                on_conflict="chart_id,signal_date").execute()
    except Exception:
        pass

    return result
