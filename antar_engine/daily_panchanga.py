"""
antar_engine/daily_panchanga.py

Daily Panchanga and Lucky Timing Engine.
Calculates the 5 limbs of the day + auspicious windows.

Panchanga = 5 elements:
  1. Vara    — day lord
  2. Tithi   — lunar day (1-30)
  3. Nakshatra — Moon's position
  4. Yoga    — Sun + Moon combination (27 yogas)
  5. Karana  — half-tithi (11 karanas)

Plus:
  - Rahu Kalam (avoid)
  - Yamaganda (avoid)
  - Abhijit Muhurta (most auspicious)
  - Lucky hours by activity type
  - Color, number, mantra of the day
"""

from datetime import datetime, date, timedelta
import os

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

# 27 Yogas (Sun longitude + Moon longitude = yoga)
YOGAS_27 = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana",
    "Atiganda","Sukarma","Dhriti","Shula","Ganda",
    "Vriddhi","Dhruva","Vyaghata","Harshana","Vajra",
    "Siddhi","Vyatipata","Variyan","Parigha","Shiva",
    "Siddha","Sadhya","Shubha","Shukla","Brahma",
    "Indra","Vaidhriti"
]

# Yoga quality
YOGA_QUALITY = {
    "Vishkambha": "inauspicious", "Priti": "auspicious",
    "Ayushman": "auspicious", "Saubhagya": "auspicious",
    "Shobhana": "auspicious", "Atiganda": "inauspicious",
    "Sukarma": "auspicious", "Dhriti": "auspicious",
    "Shula": "inauspicious", "Ganda": "inauspicious",
    "Vriddhi": "auspicious", "Dhruva": "auspicious",
    "Vyaghata": "inauspicious", "Harshana": "auspicious",
    "Vajra": "inauspicious", "Siddhi": "auspicious",
    "Vyatipata": "inauspicious", "Variyan": "neutral",
    "Parigha": "inauspicious", "Shiva": "auspicious",
    "Siddha": "auspicious", "Sadhya": "auspicious",
    "Shubha": "auspicious", "Shukla": "auspicious",
    "Brahma": "auspicious", "Indra": "auspicious",
    "Vaidhriti": "inauspicious"
}

# 11 Karanas
KARANAS = [
    "Bava","Balava","Kaulava","Taitila","Garija",
    "Vanija","Vishti","Shakuni","Chatushpada","Naga","Kimstughna"
]

KARANA_QUALITY = {
    "Vishti": "inauspicious — avoid important work",
    "Shakuni": "mixed",
    "Chatushpada": "mixed",
    "Naga": "inauspicious",
    "Kimstughna": "auspicious",
    "Bava": "auspicious", "Balava": "auspicious",
    "Kaulava": "auspicious", "Taitila": "auspicious",
    "Garija": "auspicious", "Vanija": "auspicious",
}

# Tithi quality
TITHI_QUALITY = {
    1: "auspicious", 2: "auspicious", 3: "neutral",
    4: "inauspicious", 5: "auspicious", 6: "auspicious",
    7: "auspicious", 8: "neutral", 9: "inauspicious",
    10: "auspicious", 11: "auspicious", 12: "auspicious",
    13: "neutral", 14: "inauspicious", 15: "auspicious",
    16: "auspicious", 17: "auspicious", 18: "neutral",
    19: "inauspicious", 20: "auspicious", 21: "auspicious",
    22: "auspicious", 23: "neutral", 24: "inauspicious",
    25: "auspicious", 26: "auspicious", 27: "auspicious",
    28: "neutral", 29: "inauspicious", 30: "auspicious",
}

TITHI_NAMES = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dvadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dvadashi","Trayodashi","Chaturdashi","Amavasya"
]

# Rahu Kalam by weekday (as fraction of day, 8 equal parts)
# Each part = day_duration / 8
RAHU_KALAM_PART = {
    0: 8,  # Monday — 8th part (last before sunset)
    1: 7,  # Tuesday — 7th
    2: 5,  # Wednesday — 5th
    3: 6,  # Thursday — 6th
    4: 4,  # Friday — 4th
    5: 3,  # Saturday — 3rd
    6: 2,  # Sunday — 2nd
}

YAMAGANDA_PART = {
    0: 4, 1: 3, 2: 2, 3: 1, 4: 7, 5: 6, 6: 5
}

GULIKA_PART = {
    0: 6, 1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 7
}

# Day lord properties
DAY_LORD_PROPS = {
    "Sun": {
        "color": "Orange/Gold/Saffron",
        "number": 1,
        "metal": "Gold",
        "gem": "Ruby",
        "mantra": "Om Suryaya Namah (108 times at sunrise)",
        "deity": "Surya",
        "favorable_for": ["government work", "authority meetings", "father/senior interactions", "health checkups", "leadership decisions"],
        "avoid": ["new beginnings in Saturn domains", "confronting authority without preparation"],
        "fast": "No food till sunset (optional Sun fast)",
    },
    "Moon": {
        "color": "White/Silver/Pearl",
        "number": 2,
        "metal": "Silver",
        "gem": "Pearl/Moonstone",
        "mantra": "Om Chandraya Namah (108 times)",
        "deity": "Chandra",
        "favorable_for": ["family matters", "emotional conversations", "public meetings", "travel near water", "mother interactions", "creative work"],
        "avoid": ["major financial decisions", "confrontations"],
        "fast": "White foods only, or milk fast",
    },
    "Mars": {
        "color": "Red/Coral",
        "number": 9,
        "metal": "Copper",
        "gem": "Red Coral",
        "mantra": "Om Angarakaya Namah (108 times)",
        "deity": "Hanuman",
        "favorable_for": ["gym/exercise", "surgery (if needed)", "property decisions", "courage-requiring tasks", "police/legal matters", "confronting obstacles"],
        "avoid": ["new partnerships", "emotional conversations"],
        "fast": "No salt, visit Hanuman temple",
    },
    "Mercury": {
        "color": "Green/Emerald",
        "number": 5,
        "metal": "Bronze",
        "gem": "Emerald",
        "mantra": "Om Budhaya Namah (108 times)",
        "deity": "Vishnu",
        "favorable_for": ["signing contracts", "business deals", "learning/study", "writing", "communication", "negotiations", "IT work"],
        "avoid": ["emotional impulsive decisions", "purely physical work"],
        "fast": "Green vegetables, donate books",
    },
    "Jupiter": {
        "color": "Yellow/Gold",
        "number": 3,
        "metal": "Gold",
        "gem": "Yellow Sapphire",
        "mantra": "Om Guruve Namah (108 times)",
        "deity": "Brihaspati",
        "favorable_for": ["financial planning", "teaching", "learning", "starting new ventures", "religious activities", "seeking blessings", "important decisions"],
        "avoid": ["cutting hair", "shaving", "arguments with teachers"],
        "fast": "Yellow foods, donate to teachers",
    },
    "Venus": {
        "color": "White/Pink/Sky Blue",
        "number": 6,
        "metal": "Silver",
        "gem": "Diamond/White Sapphire",
        "mantra": "Om Shukraya Namah (108 times)",
        "deity": "Lakshmi",
        "favorable_for": ["relationship matters", "creative work", "luxury purchases", "art", "music", "beauty treatments", "romantic conversations", "vehicle purchases"],
        "avoid": ["aggressive behavior", "harsh conversations"],
        "fast": "White foods, donate to women",
    },
    "Saturn": {
        "color": "Black/Dark Blue/Purple",
        "number": 8,
        "metal": "Iron/Lead",
        "gem": "Blue Sapphire/Amethyst",
        "mantra": "Om Shanaischaraya Namah (108 times)",
        "deity": "Shani",
        "favorable_for": ["disciplined work", "serving others", "long-term planning", "karmic completion tasks", "donating to poor"],
        "avoid": ["new ventures", "risky decisions", "cutting iron/metal items"],
        "fast": "Donate oil, serve workers",
    },
}

# Nakshatra lucky activities
NAKSHATRA_DO_DONT = {
    "Ashvini":    {"do":["start new projects","take medicine","travel"],
                   "dont":["avoid emotional confrontations","excessive talking"]},
    "Bharani":    {"do":["creative work","intense focus tasks"],
                   "dont":["avoid new beginnings","public disputes"]},
    "Krittika":   {"do":["precision work","cutting/editing","decisive action"],
                   "dont":["avoid fire hazards","anger"]},
    "Rohini":     {"do":["business","romance","planting","luxury purchases"],
                   "dont":["avoid confrontations","harsh speech"]},
    "Mrigashira": {"do":["research","learning","travel","artistic work"],
                   "dont":["avoid finalizing deals","commitments"]},
    "Ardra":      {"do":["innovation","transformation work","research"],
                   "dont":["avoid important beginnings","travel if possible"]},
    "Punarvasu":  {"do":["returning to projects","healing","spiritual practice"],
                   "dont":["avoid new major commitments"]},
    "Pushya":     {"do":["EVERYTHING — most auspicious nakshatra","starting businesses","investments","marriage rituals"],
                   "dont":["difficult to find anything inauspicious"]},
    "Ashlesha":   {"do":["research","secret work","studying hidden topics"],
                   "dont":["avoid trusting new people","new beginnings"]},
    "Magha":      {"do":["authority assertion","ancestral rituals","important meetings"],
                   "dont":["avoid disrespecting seniors","arrogance"]},
    "Purva Phalguni": {"do":["romance","creativity","pleasure","beauty work"],
                       "dont":["avoid difficult intellectual work","conflict"]},
    "Uttara Phalguni":{"do":["contracts","commitments","partnerships","service work"],
                       "dont":["avoid self-indulgence"]},
    "Hasta":      {"do":["craftsmanship","hands-on work","healing","travel"],
                   "dont":["avoid laziness","scattered thinking"]},
    "Chitra":     {"do":["art","design","beautification","construction"],
                   "dont":["avoid ugliness","harsh environments"]},
    "Swati":      {"do":["business","trade","travel","flexible approaches"],
                   "dont":["avoid forcing outcomes","rigidity"]},
    "Vishakha":   {"do":["goal-setting","competitive activities","achieving targets"],
                   "dont":["avoid compromising on goals","distraction"]},
    "Anuradha":   {"do":["friendship","teamwork","social activities","alliances"],
                   "dont":["avoid isolation","grudges"]},
    "Jyeshtha":   {"do":["leadership","protection of others","authority work"],
                   "dont":["avoid ego battles","overprotecting"]},
    "Mula":       {"do":["root-cause analysis","deep research","transformation"],
                   "dont":["avoid new beginnings","superficial work"]},
    "Purva Ashadha":{"do":["planning","strategy","declaration of intent"],
                     "dont":["avoid giving up","changing course midway"]},
    "Uttara Ashadha":{"do":["completing projects","final decisions","dharmic work"],
                      "dont":["avoid procrastination","leaving things unfinished"]},
    "Shravana":   {"do":["listening","learning","sacred study","music"],
                   "dont":["avoid excessive talking","hasty decisions"]},
    "Dhanishtha": {"do":["music","rhythm-based work","wealth activities"],
                   "dont":["avoid marital discord","arguments at home"]},
    "Shatabhisha":{"do":["healing","medicine","solitary work","innovation"],
                   "dont":["avoid social pressure","noisy environments"]},
    "Purva Bhadrapada":{"do":["transformation work","spiritual practice","major changes"],
                        "dont":["avoid complacency","status quo"]},
    "Uttara Bhadrapada":{"do":["wisdom work","charitable acts","deep learning"],
                         "dont":["avoid haste","shallow thinking"]},
    "Revati":     {"do":["completing cycles","travel","compassionate work","endings"],
                   "dont":["avoid new major beginnings","aggression"]},
}


def calculate_panchanga(lat: float = 28.6, lng: float = 77.2) -> dict:
    """Calculate today's Panchanga using Swiss Ephemeris."""
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        now = datetime.utcnow()
        # Adjust for IST (UTC+5:30) as default — would use user's timezone in production
        local_offset = (lng / 15.0)  # rough timezone from longitude
        local_time = now + timedelta(hours=local_offset)

        jd = swe.julday(now.year, now.month, now.day,
                         now.hour + now.minute/60.0)

        ayanamsa = swe.get_ayanamsa(jd)

        # Sun and Moon longitudes
        sun_pos,  _ = swe.calc_ut(jd, swe.SUN)
        moon_pos, _ = swe.calc_ut(jd, swe.MOON)

        sun_sid  = (sun_pos[0] - ayanamsa) % 360
        moon_sid = (moon_pos[0] - ayanamsa) % 360

        # Tithi (lunar day)
        tithi_deg = (moon_sid - sun_sid) % 360
        tithi_num = int(tithi_deg / 12) + 1  # 1-30
        tithi_name = TITHI_NAMES[tithi_num - 1]
        tithi_quality = TITHI_QUALITY.get(tithi_num, "neutral")

        # Nakshatra
        NAKSHATRAS = [
            "Ashvini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
            "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni",
            "Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha",
            "Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana",
            "Dhanishtha","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
        ]
        nak_idx  = int(moon_sid / (360/27))
        nakshatra= NAKSHATRAS[nak_idx % 27]
        moon_sign= SIGNS[int(moon_sid / 30)]

        # Yoga (Sun + Moon combined)
        yoga_deg = (sun_sid + moon_sid) % 360
        yoga_idx = int(yoga_deg / (360/27))
        yoga_name = YOGAS_27[yoga_idx % 27]
        yoga_quality = YOGA_QUALITY.get(yoga_name, "neutral")

        # Karana (half tithi)
        karana_idx = int(tithi_deg / 6) % 11
        karana_name = KARANAS[karana_idx]
        karana_quality = KARANA_QUALITY.get(karana_name, "neutral")

        # Vara (day lord)
        weekday = local_time.weekday()
        day_lords = ["Moon","Mars","Mercury","Jupiter","Venus","Saturn","Sun"]
        vara = day_lords[weekday]

        # Calculate time windows
        # Approximate sunrise/sunset (simplified — 6am/6pm local)
        sunrise_hour = 6.0
        sunset_hour  = 18.0
        day_duration = sunset_hour - sunrise_hour  # 12 hours

        part_duration = day_duration / 8.0  # each part = 1.5 hours

        def time_window(part_num: int) -> str:
            """Convert part number to time string."""
            start = sunrise_hour + (part_num - 1) * part_duration
            end   = start + part_duration
            def fmt(h):
                hh = int(h)
                mm = int((h - hh) * 60)
                period = "AM" if hh < 12 else "PM"
                hh12 = hh % 12 or 12
                return f"{hh12}:{mm:02d} {period}"
            return f"{fmt(start)} – {fmt(end)}"

        rahu_part  = RAHU_KALAM_PART.get(weekday, 2)
        yama_part  = YAMAGANDA_PART.get(weekday, 4)
        gulika_part= GULIKA_PART.get(weekday, 6)

        rahu_kalam  = time_window(rahu_part)
        yamaganda   = time_window(yama_part)
        gulika_kalam= time_window(gulika_part)

        # Abhijit Muhurta — 24 mins before to 24 mins after solar noon
        solar_noon = (sunrise_hour + sunset_hour) / 2
        abhijit_start = solar_noon - 0.4
        abhijit_end   = solar_noon + 0.4
        def fmt_h(h):
            hh = int(h); mm = int((h-hh)*60)
            p = "AM" if hh<12 else "PM"; hh12 = hh%12 or 12
            return f"{hh12}:{mm:02d} {p}"
        abhijit = f"{fmt_h(abhijit_start)} – {fmt_h(abhijit_end)}"

        # Lucky hours by category for today
        PLANETARY_HOUR_SEQUENCE = ["Sun","Venus","Mercury","Moon","Saturn","Jupiter","Mars"]
        day_lord_idx = PLANETARY_HOUR_SEQUENCE.index(vara) if vara in PLANETARY_HOUR_SEQUENCE else 0

        FAVORABLE_HOURS = {
            "business":     ["Mercury", "Jupiter", "Sun"],
            "love":         ["Venus", "Moon", "Jupiter"],
            "health":       ["Sun", "Jupiter", "Moon"],
            "travel":       ["Mercury", "Moon", "Jupiter"],
            "finance":      ["Jupiter", "Venus", "Mercury"],
            "spiritual":    ["Jupiter", "Moon", "Ketu"],
            "important_decisions": ["Jupiter", "Sun", "Mercury"],
        }

        lucky_hours = {}
        for category, favorable_planets in FAVORABLE_HOURS.items():
            windows = []
            for hour_num in range(24):
                planet_idx = (day_lord_idx + hour_num) % 7
                planet = PLANETARY_HOUR_SEQUENCE[planet_idx]
                if planet in favorable_planets:
                    h = hour_num
                    period = "AM" if h < 12 else "PM"
                    h12    = h % 12 or 12
                    windows.append(f"{h12}:00 {period}")
                if len(windows) >= 3:
                    break
            lucky_hours[category] = windows

        # Nakshatra do/don't
        nak_advice = NAKSHATRA_DO_DONT.get(nakshatra, {})
        do_today   = nak_advice.get("do", [])
        dont_today = nak_advice.get("dont", [])

        # Day lord properties
        day_props = DAY_LORD_PROPS.get(vara, {})

        # Overall day quality
        quality_score = 0
        if tithi_quality == "auspicious": quality_score += 2
        if yoga_quality  == "auspicious": quality_score += 2
        if karana_quality!= "inauspicious": quality_score += 1
        day_quality = "excellent" if quality_score >= 4 else "good" if quality_score >= 2 else "neutral"

        return {
            "date":         local_time.strftime("%A, %B %d, %Y"),
            "vara":         vara,
            "tithi":        tithi_name,
            "tithi_num":    tithi_num,
            "tithi_quality":tithi_quality,
            "nakshatra":    nakshatra,
            "moon_sign":    moon_sign,
            "yoga":         yoga_name,
            "yoga_quality": yoga_quality,
            "karana":       karana_name,
            "karana_quality":karana_quality,
            "day_quality":  day_quality,
            "rahu_kalam":   rahu_kalam,
            "yamaganda":    yamaganda,
            "gulika_kalam": gulika_kalam,
            "abhijit_muhurta": abhijit,
            "lucky_hours":  lucky_hours,
            "do_today":     do_today[:4],
            "dont_today":   dont_today[:3],
            "day_color":    day_props.get("color",""),
            "day_number":   day_props.get("number",""),
            "day_mantra":   day_props.get("mantra",""),
            "day_gem":      day_props.get("gem",""),
            "day_favorable_for": day_props.get("favorable_for",[])[:4],
            "day_avoid":    day_props.get("avoid",[])[:2],
            "sun_sign":     SIGNS[int(sun_sid/30)],
            "sun_longitude": round(sun_sid, 2),
            "moon_longitude": round(moon_sid, 2),
        }

    except Exception as e:
        return {"error": str(e), "date": str(datetime.now().date())}


def build_daily_panchanga_block(panchanga: dict, natal_chart: dict = None) -> str:
    """Format Panchanga for LLM context and user display."""
    if not panchanga or panchanga.get("error"):
        return f"Panchanga unavailable: {panchanga.get('error','')}"

    lines = [
        "═══════════════════════════════════════════════════════",
        f"TODAY'S PANCHANGA — {panchanga.get('date','')}",
        "═══════════════════════════════════════════════════════",
        "",
        "THE 5 LIMBS OF TODAY:",
        f"  Vara (Day):       {panchanga['vara']} — {DAY_LORD_PROPS.get(panchanga['vara'],{{}}).get('favorable_for',[''])[:2]}",
        f"  Tithi (Lunar day):{panchanga['tithi']} (#{panchanga['tithi_num']}) — {panchanga['tithi_quality']}",
        f"  Nakshatra:        {panchanga['nakshatra']} in {panchanga['moon_sign']}",
        f"  Yoga:             {panchanga['yoga']} — {panchanga['yoga_quality']}",
        f"  Karana:           {panchanga['karana']} — {panchanga['karana_quality']}",
        "",
        f"OVERALL DAY QUALITY: {panchanga['day_quality'].upper()}",
        "",
        "TIMING WINDOWS:",
        f"  ✓ Abhijit Muhurta (MOST AUSPICIOUS): {panchanga['abhijit_muhurta']}",
        f"  ✗ Rahu Kalam (AVOID): {panchanga['rahu_kalam']}",
        f"  ✗ Yamaganda (avoid if possible): {panchanga['yamaganda']}",
        "",
        "LUCKY HOURS BY ACTIVITY:",
    ]

    for activity, hours in panchanga.get("lucky_hours",{}).items():
        if hours:
            lines.append(f"  {activity.replace('_',' ').title():<28}: {', '.join(hours[:2])}")

    lines += [
        "",
        "TODAY — DO:",
    ]
    for item in panchanga.get("do_today",[]):
        lines.append(f"  ✓ {item}")

    lines += ["", "TODAY — AVOID:"]
    for item in panchanga.get("dont_today",[]):
        lines.append(f"  ✗ {item}")

    lines += [
        "",
        "TODAY'S PROPERTIES:",
        f"  Color:   {panchanga.get('day_color','')}",
        f"  Number:  {panchanga.get('day_number','')}",
        f"  Gem:     {panchanga.get('day_gem','')}",
        f"  Mantra:  {panchanga.get('day_mantra','')}",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)


def format_daily_for_user(panchanga: dict, natal_signal: str = "") -> dict:
    """
    Format the complete daily experience for the frontend.
    This is what the dashboard 'Today' tab shows.
    """
    if not panchanga or panchanga.get("error"):
        return {}

    # Determine overall vibe
    if panchanga["day_quality"] == "excellent":
        vibe = "A powerful day — cosmic energy strongly supports action"
    elif panchanga["yoga_quality"] == "inauspicious":
        vibe = "A day to be thoughtful — avoid major new beginnings"
    elif panchanga["nakshatra"] == "Pushya":
        vibe = "Pushya nakshatra — one of the most auspicious days of the month"
    else:
        vibe = f"{panchanga['vara']} energy — {DAY_LORD_PROPS.get(panchanga['vara'],{}).get('favorable_for',[''])[0]} favored"

    return {
        "headline":        f"{panchanga['vara']}day · {panchanga['nakshatra']} · {panchanga['tithi']}",
        "vibe":            vibe,
        "day_quality":     panchanga["day_quality"],
        "best_time":       panchanga["abhijit_muhurta"],
        "avoid_time":      panchanga["rahu_kalam"],
        "do_today":        panchanga.get("do_today",[])[:3],
        "dont_today":      panchanga.get("dont_today",[])[:2],
        "lucky_hours":     panchanga.get("lucky_hours",{}),
        "color":           panchanga.get("day_color",""),
        "number":          panchanga.get("day_number",""),
        "mantra":          panchanga.get("day_mantra",""),
        "nakshatra":       panchanga["nakshatra"],
        "moon_sign":       panchanga["moon_sign"],
        "tithi":           panchanga["tithi"],
        "yoga":            panchanga["yoga"],
        "yoga_quality":    panchanga["yoga_quality"],
        "rahu_kalam":      panchanga["rahu_kalam"],
        "abhijit":         panchanga["abhijit_muhurta"],
        "natal_signal":    natal_signal,
        "panchanga_5":     {
            "vara":       panchanga["vara"],
            "tithi":      f"{panchanga['tithi']} ({panchanga['tithi_quality']})",
            "nakshatra":  panchanga["nakshatra"],
            "yoga":       f"{panchanga['yoga']} ({panchanga['yoga_quality']})",
            "karana":     f"{panchanga['karana']} ({panchanga['karana_quality']})",
        },
    }
