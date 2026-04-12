#!/usr/bin/env python3
"""
patch_panchang_daily.py

Adds Panchang (5 daily elements) to the daily-week prediction context.
This is what makes Today predictions actually daily instead of weekly.

Panchang = Tithi + Vara + Nakshatra + Yoga + Karana
These change every ~12-27 hours and give the true quality of each day.

Also adds Chandra Bala (Moon's strength relative to natal Moon)
and current dasha lord transit position.

Run: python patch_panchang_daily.py
"""

import shutil

TARGET = "antar_engine/daily_prediction_engine.py"
BACKUP = "antar_engine/daily_prediction_engine.py.bak_panchang"

with open(TARGET, "r") as f:
    content = f.read()

shutil.copy(TARGET, BACKUP)
print(f"Backup: {BACKUP}")

# ── PATCH 1: Add Panchang calculator ──────────────────────────────────────

PANCHANG_FUNCTION = '''

def calculate_panchang(dt_utc, lat: float, lon: float) -> dict:
    """
    Calculate the 5 daily Panchang elements for a given datetime + location.
    
    Returns:
        tithi: lunar day (1-30), name, quality
        vara: weekday lord and themes
        nakshatra: Moon's star, deity, quality, do/don't
        yoga: Sun+Moon yoga name and quality
        karana: half-tithi, quality
        chandra_rashi: Moon's current sign
    """
    import swisseph as swe
    from datetime import timezone

    # Convert to Julian Day
    jd = swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
    )

    # Get Sun and Moon longitudes
    sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
    moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]

    # ── Tithi ──────────────────────────────────────────────────────
    tithi_deg = (moon_lon - sun_lon) % 360
    tithi_num = int(tithi_deg / 12) + 1  # 1-30

    TITHI_NAMES = [
        "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
        "Shashthi","Saptami","Ashtami","Navami","Dashami",
        "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
        "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
        "Shashthi","Saptami","Ashtami","Navami","Dashami",
        "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
    ]
    TITHI_QUALITY = {
        1:"neutral", 2:"auspicious", 3:"auspicious", 4:"mixed",
        5:"auspicious", 6:"mixed", 7:"auspicious", 8:"mixed",
        9:"mixed", 10:"auspicious", 11:"auspicious", 12:"auspicious",
        13:"mixed", 14:"inauspicious", 15:"auspicious",
        16:"neutral", 17:"auspicious", 18:"auspicious", 19:"mixed",
        20:"auspicious", 21:"mixed", 22:"auspicious", 23:"mixed",
        24:"mixed", 25:"auspicious", 26:"auspicious", 27:"auspicious",
        28:"mixed", 29:"inauspicious", 30:"inauspicious"
    }

    tithi = {
        "number": tithi_num,
        "name": TITHI_NAMES[tithi_num - 1],
        "quality": TITHI_QUALITY.get(tithi_num, "neutral"),
        "paksha": "Shukla" if tithi_num <= 15 else "Krishna",
    }

    # ── Vara (weekday) ─────────────────────────────────────────────
    weekday = dt_utc.weekday()  # 0=Mon, 6=Sun
    VARA = [
        {"lord":"Moon",    "name":"Monday",    "themes":"Emotions, home, mother, mind, water",
         "good_for":"Emotional conversations, family matters, intuitive decisions",
         "avoid":"Major business moves, confrontation"},
        {"lord":"Mars",    "name":"Tuesday",   "themes":"Action, courage, energy, competition",
         "good_for":"Bold moves, physical activity, negotiations, new initiatives",
         "avoid":"Emotional decisions, overspending"},
        {"lord":"Mercury", "name":"Wednesday", "themes":"Communication, intellect, trade, travel",
         "good_for":"Writing, contracts, learning, networking, short trips",
         "avoid":"Major financial commitments"},
        {"lord":"Jupiter", "name":"Thursday",  "themes":"Wisdom, expansion, teachers, wealth",
         "good_for":"Education, spiritual practice, seeking guidance, investments",
         "avoid":"Arguments, harsh speech"},
        {"lord":"Venus",   "name":"Friday",    "themes":"Love, beauty, pleasure, creativity, wealth",
         "good_for":"Relationships, creative work, luxury, social events",
         "avoid":"Starting confrontational matters"},
        {"lord":"Saturn",  "name":"Saturday",  "themes":"Structure, discipline, karma, endurance",
         "good_for":"Long-term planning, hard work, resolving old matters",
         "avoid":"Starting new ventures, celebrations"},
        {"lord":"Sun",     "name":"Sunday",    "themes":"Vitality, authority, father, leadership, visibility",
         "good_for":"Career moves, leadership, visibility, government matters",
         "avoid":"Starting new relationships"},
    ]
    vara = VARA[weekday]

    # ── Nakshatra (Moon's star) ────────────────────────────────────
    nakshatra_num = int(moon_lon / (360/27))  # 0-26
    NAKSHATRAS = [
        {"name":"Ashwini","deity":"Ashwins","quality":"swift","good_for":"Starting new things, medical matters, travel"},
        {"name":"Bharani","deity":"Yama","quality":"fierce","good_for":"Completing difficult tasks, transformation"},
        {"name":"Krittika","deity":"Agni","quality":"mixed","good_for":"Cooking, purification, sharp actions"},
        {"name":"Rohini","deity":"Brahma","quality":"fixed","good_for":"Agriculture, building, sensual pleasures, stability"},
        {"name":"Mrigashira","deity":"Soma","quality":"soft","good_for":"Searching, exploration, gentle activities"},
        {"name":"Ardra","deity":"Rudra","quality":"sharp","good_for":"Cutting through obstacles, research, destructive work"},
        {"name":"Punarvasu","deity":"Aditi","quality":"moveable","good_for":"Return journeys, renewals, buying/selling"},
        {"name":"Pushya","deity":"Brihaspati","quality":"auspicious","good_for":"Almost everything — most auspicious nakshatra"},
        {"name":"Ashlesha","deity":"Naga","quality":"sharp","good_for":"Occult matters, research, medicine"},
        {"name":"Magha","deity":"Pitrs","quality":"fierce","good_for":"Honoring ancestors, authority matters, father-related"},
        {"name":"Purva Phalguni","deity":"Bhaga","quality":"fierce","good_for":"Creativity, pleasure, relaxation"},
        {"name":"Uttara Phalguni","deity":"Aryaman","quality":"fixed","good_for":"Friendships, contracts, getting favors"},
        {"name":"Hasta","deity":"Savitar","quality":"swift","good_for":"Crafts, healing, stealing — quick activities"},
        {"name":"Chitra","deity":"Vishwakarma","quality":"soft","good_for":"Art, architecture, wearing new clothes"},
        {"name":"Swati","deity":"Vayu","quality":"moveable","good_for":"Business, trade, learning, independence"},
        {"name":"Vishakha","deity":"Indra-Agni","quality":"mixed","good_for":"Achieving goals, political matters"},
        {"name":"Anuradha","deity":"Mitra","quality":"soft","good_for":"Friendships, devotion, group activities"},
        {"name":"Jyeshtha","deity":"Indra","quality":"sharp","good_for":"Leadership, authority, competitive situations"},
        {"name":"Mula","deity":"Nirriti","quality":"sharp","good_for":"Research, getting to root causes, medicine"},
        {"name":"Purva Ashadha","deity":"Apas","quality":"fierce","good_for":"Water activities, purification, travel"},
        {"name":"Uttara Ashadha","deity":"Vishwadevas","quality":"fixed","good_for":"Long-term projects, victory, stability"},
        {"name":"Shravana","deity":"Vishnu","quality":"moveable","good_for":"Learning, listening, travel, communication"},
        {"name":"Dhanishta","deity":"Ashta Vasus","quality":"moveable","good_for":"Music, wealth, community activities"},
        {"name":"Shatabhisha","deity":"Varuna","quality":"moveable","good_for":"Healing, occult, isolation, research"},
        {"name":"Purva Bhadrapada","deity":"Ajaikapada","quality":"fierce","good_for":"Intensity, transformation, occult"},
        {"name":"Uttara Bhadrapada","deity":"Ahirbudhnya","quality":"fixed","good_for":"Stability, depth, spiritual practice"},
        {"name":"Revati","deity":"Pushan","quality":"soft","good_for":"Completion, travel, nourishment, spiritual practice"},
    ]
    nakshatra = NAKSHATRAS[nakshatra_num]
    nakshatra["number"] = nakshatra_num + 1
    nakshatra["moon_lon"] = round(moon_lon, 2)

    # ── Yoga (Sun + Moon combined) ─────────────────────────────────
    yoga_deg = (sun_lon + moon_lon) % 360
    yoga_num = int(yoga_deg / (360/27))
    YOGAS = [
        ("Vishkambha","mixed"),("Priti","auspicious"),("Ayushman","auspicious"),
        ("Saubhagya","auspicious"),("Shobhana","auspicious"),("Atiganda","inauspicious"),
        ("Sukarma","auspicious"),("Dhriti","auspicious"),("Shoola","inauspicious"),
        ("Ganda","inauspicious"),("Vriddhi","auspicious"),("Dhruva","auspicious"),
        ("Vyaghata","inauspicious"),("Harshana","auspicious"),("Vajra","mixed"),
        ("Siddhi","auspicious"),("Vyatipata","inauspicious"),("Variyan","mixed"),
        ("Parigha","inauspicious"),("Shiva","auspicious"),("Siddha","auspicious"),
        ("Sadhya","auspicious"),("Shubha","auspicious"),("Shukla","auspicious"),
        ("Brahma","auspicious"),("Mahendra","auspicious"),("Vaidhriti","inauspicious"),
    ]
    yoga_name, yoga_quality = YOGAS[yoga_num]
    yoga = {"number": yoga_num+1, "name": yoga_name, "quality": yoga_quality}

    # ── Karana (half-tithi) ────────────────────────────────────────
    karana_num = int(tithi_deg / 6) % 11
    KARANAS = [
        ("Bava","auspicious"),("Balava","auspicious"),("Kaulava","auspicious"),
        ("Taitila","auspicious"),("Garaja","mixed"),("Vanija","auspicious"),
        ("Vishti","inauspicious"),("Shakuni","mixed"),("Chatushpada","mixed"),
        ("Naga","mixed"),("Kimstughna","mixed"),
    ]
    karana_name, karana_quality = KARANAS[karana_num]
    karana = {"name": karana_name, "quality": karana_quality}

    # ── Moon sign (Chandra Rashi) ──────────────────────────────────
    moon_sign_num = int(moon_lon / 30)
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    moon_sign = SIGNS[moon_sign_num]

    # ── Overall day quality from Panchang ─────────────────────────
    qualities = [
        tithi["quality"], yoga["quality"], karana["quality"]
    ]
    auspicious_count = qualities.count("auspicious")
    inauspicious_count = qualities.count("inauspicious")

    if inauspicious_count >= 2:
        panchang_quality = "challenging"
    elif auspicious_count >= 2:
        panchang_quality = "favorable"
    else:
        panchang_quality = "mixed"

    return {
        "tithi": tithi,
        "vara": vara,
        "nakshatra": nakshatra,
        "yoga": yoga,
        "karana": karana,
        "moon_sign": moon_sign,
        "panchang_quality": panchang_quality,
        "summary": (
            f"{vara['name']}, {nakshatra['name']} nakshatra, "
            f"{tithi['name']} tithi ({tithi['quality']}), "
            f"{yoga_name} yoga ({yoga_quality})"
        )
    }


def get_chandra_bala(natal_moon_sign: str, current_moon_sign: str) -> dict:
    """
    Calculate Moon's strength relative to natal Moon position.
    Chandra Bala = strength of transit Moon from natal Moon.
    
    Houses 1,3,6,7,10,11 from natal Moon = beneficial
    Houses 4,8,12 from natal Moon = Chandrashtama (inauspicious ~2.5 days)
    """
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    
    try:
        natal_idx = SIGNS.index(natal_moon_sign)
        current_idx = SIGNS.index(current_moon_sign)
    except ValueError:
        return {"strength": "neutral", "house_from_moon": 0}

    house_from_moon = ((current_idx - natal_idx) % 12) + 1

    STRENGTH = {
        1:"favorable", 2:"neutral", 3:"favorable", 4:"unfavorable",
        5:"neutral", 6:"favorable", 7:"favorable", 8:"unfavorable",
        9:"neutral", 10:"favorable", 11:"favorable", 12:"unfavorable"
    }

    strength = STRENGTH.get(house_from_moon, "neutral")
    is_chandrashtama = house_from_moon in [4, 8, 12]

    return {
        "strength": strength,
        "house_from_moon": house_from_moon,
        "is_chandrashtama": is_chandrashtama,
        "plain": (
            "Moon transiting unfavorably from your natal Moon — be careful with decisions today. Avoid starting new things." 
            if is_chandrashtama else
            "Moon well-placed from your natal Moon — your instincts are reliable today."
            if strength == "favorable" else
            "Moon in neutral position from natal Moon."
        )
    }
'''

# Insert after imports in daily_prediction_engine.py
if "def calculate_panchang" not in content:
    # Find first function definition to insert before
    import re
    match = re.search(r'^def \w+', content, re.MULTILINE)
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + PANCHANG_FUNCTION + "\n\n" + content[insert_pos:]
        print("✅ Inserted calculate_panchang() and get_chandra_bala()")
    else:
        content = content + "\n\n" + PANCHANG_FUNCTION
        print("✅ Appended calculate_panchang() and get_chandra_bala()")
else:
    print("ℹ️  calculate_panchang() already exists — skipping")

# ── PATCH 2: Add Panchang to daily prediction context ─────────────────────

PANCHANG_CONTEXT_INJECTION = '''
    # ── Add Panchang context ──────────────────────────────────────────
    try:
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        
        # Get chart location for accurate Panchang
        birth_lat = chart_data.get("birth_lat", 28.6)  # Default Delhi
        birth_lon = chart_data.get("birth_lon", 77.2)
        
        panchang = calculate_panchang(now_utc, birth_lat, birth_lon)
        
        # Get Chandra Bala
        natal_moon = chart_data.get("moon_sign", "")
        current_moon = panchang.get("moon_sign", "")
        chandra_bala = get_chandra_bala(natal_moon, current_moon)
        
        # Add to prediction context
        if "panchang" not in context_parts:
            context_parts["panchang"] = {
                "today": panchang,
                "chandra_bala": chandra_bala,
                "plain_summary": (
                    f"TODAY'S PANCHANG: {panchang['summary']}. "
                    f"Moon in {panchang['moon_sign']}. "
                    f"Overall quality: {panchang['panchang_quality']}. "
                    f"Chandra Bala: {chandra_bala['strength']} "
                    f"(house {chandra_bala['house_from_moon']} from natal Moon). "
                    f"{chandra_bala['plain']}"
                )
            }
    except Exception as e:
        print(f"Panchang calculation error: {e}")
    # ── End Panchang ──────────────────────────────────────────────────
'''

# Find where daily context is assembled and add Panchang
if "panchang" not in content.lower():
    # Try to find context assembly
    if "context_parts" in content:
        # Find a good insertion point near context assembly
        insert_marker = "context_parts["
        idx = content.find(insert_marker)
        if idx > 0:
            # Find the end of the context_parts block
            line_end = content.find("\n\n", idx)
            if line_end > 0:
                content = content[:line_end] + "\n" + PANCHANG_CONTEXT_INJECTION + content[line_end:]
                print("✅ Added Panchang to daily context")
    else:
        print("⚠️  Could not find context assembly — add Panchang context manually")
        print("    Call calculate_panchang() and add result to your LLM context")

# ── Write file ─────────────────────────────────────────────────────────────
with open(TARGET, "w") as f:
    f.write(content)

print("\n✅ Patch complete")
print("Verify:")
print("python3 -c \"import ast; ast.parse(open('antar_engine/daily_prediction_engine.py').read()); print('OK')\"")
print("git add -A && git commit -m 'feat: panchang + chandra bala in daily predictions' && git push")
print()
print("Test:")
print("curl -s 'https://antar-fastapi-production.up.railway.app/api/v1/daily-week/de02bb52-d43a-4b09-be25-b45a07bfbf8a?language=es' \\")
print("  | python3 -m json.tool | grep -A 10 'panchang'")
