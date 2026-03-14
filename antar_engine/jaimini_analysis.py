"""
antar_engine/jaimini_analysis.py

Full Jaimini analysis engine:
  1. Extract 7 Charakarakas from D1 chart
  2. Calculate Karakamsha (AK in D9)
  3. Rotating Chara Dasha lagna technique
  4. GK/AK/AmK house positions from active dasha lagna
  5. Rashi aspects (Jaimini style)
  6. Warnings and confluence scoring
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# Movable, Fixed, Dual classification
MOVABLE = ["Aries","Cancer","Libra","Capricorn"]
FIXED   = ["Taurus","Leo","Scorpio","Aquarius"]
DUAL    = ["Gemini","Virgo","Sagittarius","Pisces"]

KARAKA_NAMES = [
    "Atmakaraka",    # AK  — highest degree
    "Amatyakaraka",  # AmK — 2nd
    "Bhratrukaraka", # BK  — 3rd
    "Matrukaraka",   # MK  — 4th
    "Putrakaraka",   # PK  — 5th
    "Gnatikaraka",   # GK  — 6th
    "Darakaraka",    # DK  — 7th/lowest
]

KARAKA_ABBREV = {
    "Atmakaraka":    "AK",
    "Amatyakaraka":  "AmK",
    "Bhratrukaraka": "BK",
    "Matrukaraka":   "MK",
    "Putrakaraka":   "PK",
    "Gnatikaraka":   "GK",
    "Darakaraka":    "DK",
}

KARAKA_MEANING = {
    "Atmakaraka":    "soul purpose — what the soul came to learn and master",
    "Amatyakaraka":  "career, livelihood, advisors, means of success",
    "Bhratrukaraka": "siblings, courage, initiative, communication",
    "Matrukaraka":   "mother, home, property, emotional foundation",
    "Putrakaraka":   "children, intelligence, past life merit, creativity",
    "Gnatikaraka":   "enemies, disease, competition, obstacles, relatives",
    "Darakaraka":    "spouse, business partner, 7th house significations",
}

# House positions that are POSITIVE for each karaka from Chara Dasha lagna
POSITIVE_HOUSES = {
    "Atmakaraka":    [1, 2, 4, 5, 7, 9, 10, 11],
    "Amatyakaraka":  [1, 2, 5, 9, 10, 11],
    "Bhratrukaraka": [1, 3, 5, 11],
    "Matrukaraka":   [1, 4, 5, 9],
    "Putrakaraka":   [1, 2, 5, 9, 11],
    "Gnatikaraka":   [3, 6, 10, 11],  # GK is good in upachaya houses
    "Darakaraka":    [1, 2, 5, 7, 9, 11],
}

# House positions that are WARNING/NEGATIVE for each karaka
WARNING_HOUSES = {
    "Atmakaraka":    [6, 8, 12],   # soul under pressure — difficult but karmic
    "Amatyakaraka":  [6, 8, 12],   # career obstacles
    "Bhratrukaraka": [6, 8, 12],   # sibling issues, courage tested
    "Matrukaraka":   [6, 8, 12],   # mother health, property disputes
    "Putrakaraka":   [6, 8, 12],   # children issues, creative blocks
    "Gnatikaraka":   [1, 5, 7, 9], # GK in good houses activates enemies visibly
    "Darakaraka":    [6, 8, 12],   # serious relationship/partnership crisis
}

# CRITICAL: GK in 6/8/12 from Chara Dasha lagna
CRITICAL_GK_HOUSES = [6, 8, 12]

# Karakamsha interpretations (what aspects the Karakamsha lagna)
KARAKAMSHA_PLANET_MEANING = {
    "Sun":     "authority, government service, leadership — soul purpose in public life",
    "Moon":    "public life, nurturing, emotional wisdom — soul purpose in service",
    "Mars":    "engineering, surgery, military, real estate — soul purpose in action",
    "Mercury": "business, technology, communication, writing — soul purpose in intellect",
    "Jupiter": "teaching, law, philosophy, advisory — soul purpose in wisdom",
    "Venus":   "arts, luxury, relationships, beauty — soul purpose in harmony",
    "Saturn":  "service, discipline, delayed achievement — soul purpose in karma",
    "Rahu":    "foreign, technology, disruption, unconventional — soul purpose in transformation",
    "Ketu":    "spirituality, research, past expertise, moksha — soul purpose in liberation",
}


def _parse_dt(s) -> datetime:
    if isinstance(s, datetime):
        return s
    try:
        return datetime.fromisoformat(str(s).replace("Z","+00:00"))
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d")
        except Exception:
            return datetime.utcnow()


def _house_from_signs(from_sign: str, to_sign: str) -> int:
    """Count house number of to_sign FROM from_sign (1-indexed)."""
    if from_sign not in SIGNS or to_sign not in SIGNS:
        return 0
    from_idx = SIGNS.index(from_sign)
    to_idx   = SIGNS.index(to_sign)
    return ((to_idx - from_idx) % 12) + 1


def extract_charakarakas(planets: dict) -> dict:
    """
    Extract 7 Charakarakas by ranking planets by degree (highest = AK).
    Rahu and Ketu are excluded. Rahu uses 30 - degree rule.
    Returns dict: karaka_name → {planet, sign, house, degree}
    """
    # Get degree within sign for each planet (exclude Rahu/Ketu)
    planet_degrees = {}
    for p, data in planets.items():
        if p in ("Rahu", "Ketu"):
            continue
        planet_degrees[p] = {
            "degree": data.get("degree", 0),  # degree within sign
            "sign":   data.get("sign", ""),
            "house":  data.get("house", 0),
        }

    # Sort by degree descending (highest degree = AK)
    sorted_planets = sorted(
        planet_degrees.items(),
        key=lambda x: x[1]["degree"],
        reverse=True,
    )

    karakas = {}
    for i, (planet, data) in enumerate(sorted_planets[:7]):
        karaka_name = KARAKA_NAMES[i]
        karakas[karaka_name] = {
            "planet":  planet,
            "sign":    data["sign"],
            "house":   data["house"],
            "degree":  round(data["degree"], 2),
            "abbrev":  KARAKA_ABBREV[karaka_name],
            "meaning": KARAKA_MEANING[karaka_name],
        }

    return karakas


def calculate_karakamsha(
    karakas: dict,
    d9_chart: dict,
) -> dict:
    """
    Karakamsha = sign occupied by Atmakaraka in D9 Navamsa.
    This sign in D1 = soul's operating platform for this life.
    """
    ak_planet = karakas.get("Atmakaraka", {}).get("planet", "")
    if not ak_planet or not d9_chart:
        return {"sign": "", "meaning": ""}

    # Find AK planet's sign in D9
    d9_planets = d9_chart.get("planets", {})
    ak_in_d9   = d9_planets.get(ak_planet, {})
    karakamsha_sign = ak_in_d9.get("sign", "")

    if not karakamsha_sign:
        return {"sign": "", "ak_planet": ak_planet}

    # What aspects the Karakamsha sign? (Jaimini rashi aspects)
    aspecting_signs = get_rashi_aspects(karakamsha_sign)

    # Which planets are in Karakamsha sign or aspecting it (in D1)?
    return {
        "sign":             karakamsha_sign,
        "ak_planet":        ak_planet,
        "aspecting_signs":  aspecting_signs,
        "meaning":          f"Soul platform: {karakamsha_sign} — ruled by {SIGN_LORDS.get(karakamsha_sign,'')}",
    }


def get_rashi_aspects(sign: str) -> list:
    """
    Jaimini Rashi aspects:
    - Movable signs aspect all Fixed signs except adjacent
    - Fixed signs aspect all Movable signs except adjacent
    - Dual signs aspect all other Dual signs
    """
    if sign not in SIGNS:
        return []

    sign_idx = SIGNS.index(sign)
    aspects  = []

    if sign in MOVABLE:
        # Aspects all Fixed except adjacent
        adjacent_idx = (sign_idx + 1) % 12
        adjacent = SIGNS[adjacent_idx]
        for s in FIXED:
            if s != adjacent:
                aspects.append(s)

    elif sign in FIXED:
        # Aspects all Movable except adjacent (behind it)
        adjacent_idx = (sign_idx - 1) % 12
        adjacent = SIGNS[adjacent_idx]
        for s in MOVABLE:
            if s != adjacent:
                aspects.append(s)

    elif sign in DUAL:
        # Aspects all other Dual signs
        for s in DUAL:
            if s != sign:
                aspects.append(s)

    return aspects


def analyze_chara_dasha_period(
    chara_dasha_sign: str,
    karakas: dict,
    planets: dict,
    lagna_sign: str,
) -> dict:
    """
    THE CORE JAIMINI TECHNIQUE:
    Take the active Chara Dasha sign as temporary lagna.
    Calculate where each karaka planet falls from this temporary lagna.
    Apply rules to determine quality of this period.
    """
    if not chara_dasha_sign:
        return {}

    period_analysis = {
        "dasha_lagna":   chara_dasha_sign,
        "dasha_lord":    SIGN_LORDS.get(chara_dasha_sign, ""),
        "karaka_houses": {},
        "warnings":      [],
        "highlights":    [],
        "overall_quality": "neutral",
        "confluence_factors": [],
    }

    # Calculate house of each karaka from Chara Dasha lagna
    for karaka_name, karaka_data in karakas.items():
        karaka_sign = karaka_data.get("sign", "")
        if not karaka_sign:
            continue

        house = _house_from_signs(chara_dasha_sign, karaka_sign)
        abbrev = KARAKA_ABBREV[karaka_name]
        planet = karaka_data.get("planet", "")

        period_analysis["karaka_houses"][karaka_name] = {
            "planet":  planet,
            "sign":    karaka_sign,
            "house":   house,
            "abbrev":  abbrev,
        }

        # Apply rules
        if karaka_name == "Gnatikaraka" and house in CRITICAL_GK_HOUSES:
            severity = "CRITICAL" if house == 8 else "WARNING"
            period_analysis["warnings"].append({
                "severity": severity,
                "karaka":   "GK",
                "planet":   planet,
                "house":    house,
                "message":  _gk_warning_message(planet, house),
                "remedy":   _get_lk_remedy_for_gk(planet, house),
            })

        elif karaka_name == "Darakaraka" and house in [6, 8, 12]:
            period_analysis["warnings"].append({
                "severity": "WARNING",
                "karaka":   "DK",
                "planet":   planet,
                "house":    house,
                "message":  f"DK ({planet}) in house {house} from dasha lagna — relationship/partnership stress in this period",
                "remedy":   "Strengthen 7th house: donate on Fridays, respect spouse/partner",
            })

        elif karaka_name == "Matrukaraka" and house in [6, 8]:
            period_analysis["warnings"].append({
                "severity": "WARNING",
                "karaka":   "MK",
                "planet":   planet,
                "house":    house,
                "message":  f"MK ({planet}) in house {house} — mother's health or property needs attention",
                "remedy":   "Care for mother actively. Resolve any property disputes.",
            })

        # Highlights
        if karaka_name == "Atmakaraka" and house in [1, 5, 9, 10, 11]:
            period_analysis["highlights"].append(
                f"AK ({planet}) in house {house} — soul purpose fully activated, peak period for {_house_theme(house)}"
            )
            period_analysis["confluence_factors"].append(f"AK in {house}th")

        if karaka_name == "Amatyakaraka" and house in [10, 11, 2]:
            period_analysis["highlights"].append(
                f"AmK ({planet}) in house {house} — career and financial peak, {_house_theme(house)}"
            )
            period_analysis["confluence_factors"].append(f"AmK in {house}th")

        if karaka_name == "Putrakaraka" and house in [1, 5, 9, 11]:
            period_analysis["highlights"].append(
                f"PK ({planet}) in house {house} — children, creativity, intelligence strongly activated"
            )

    # Overall quality
    warning_count   = len(period_analysis["warnings"])
    highlight_count = len(period_analysis["highlights"])
    critical_count  = sum(1 for w in period_analysis["warnings"] if w.get("severity") == "CRITICAL")

    if critical_count > 0:
        period_analysis["overall_quality"] = "critical_caution"
    elif warning_count > highlight_count:
        period_analysis["overall_quality"] = "challenging"
    elif highlight_count >= 2:
        period_analysis["overall_quality"] = "excellent"
    elif highlight_count == 1:
        period_analysis["overall_quality"] = "favorable"
    elif warning_count == 1:
        period_analysis["overall_quality"] = "moderate_caution"
    else:
        period_analysis["overall_quality"] = "neutral"

    return period_analysis


def _house_theme(house: int) -> str:
    themes = {
        1:"identity and self-expression", 2:"wealth and family",
        4:"home and happiness", 5:"intelligence and creativity",
        7:"partnerships", 9:"fortune and dharma",
        10:"career and authority", 11:"gains and ambitions",
    }
    return themes.get(house, f"house {house} themes")


def _gk_warning_message(planet: str, house: int) -> str:
    messages = {
        6: f"GK ({planet}) in 6th from dasha lagna — enemies active, health watch needed, legal disputes possible",
        8: f"GK ({planet}) in 8th from dasha lagna — CRITICAL: accidents, surgery, sudden losses, hidden enemies most dangerous",
        12: f"GK ({planet}) in 12th from dasha lagna — losses, hospitalization risk, isolation, foreign problems",
    }
    return messages.get(house, f"GK ({planet}) in house {house} — obstacle period")


def _get_lk_remedy_for_gk(planet: str, house: int) -> str:
    """Lal Kitab remedy for active GK warning."""
    remedies = {
        ("Mars",  6): "Donate blood. Help brothers. Avoid conflicts.",
        ("Mars",  8): "Keep knife away from home. Pray to Hanuman daily. Avoid risky activities.",
        ("Mars", 12): "Keep feet clean. Donate to hospitals. Avoid accidents.",
        ("Saturn",6): "Serve workers and poor. Oil lamps on Saturdays.",
        ("Saturn",8): "Study philosophy. Donate on Saturdays. Avoid risky behavior.",
        ("Saturn",12):"Meditate daily. Donate black sesame on Saturdays.",
        ("Rahu",  6): "Keep snake image. Feed crows. Donate blue items.",
        ("Rahu",  8): "Avoid risky activities. Keep sandalwood. Pray to Durga.",
        ("Rahu", 12): "Keep foreign connections ethical. Meditate. Donate on Saturdays.",
        ("Sun",   6): "Serve father daily. Donate food to poor.",
        ("Sun",   8): "Avoid ego battles. Keep ruby. Offer water to Sun.",
        ("Sun",  12): "Donate copper on Sundays. Eye care important.",
        ("Moon",  6): "Donate milk to poor. Keep digestive health.",
        ("Moon",  8): "Offer water to ancestors. Emotional stability practice.",
        ("Moon", 12): "Meditate near water. Keep fasts on Mondays.",
    }
    return remedies.get((planet, house),
           f"For {planet} in house {house}: Strengthen {planet} through its natural remedy. "
           f"Consult Lal Kitab for specific {planet} remedy.")


def get_current_chara_dasha(chara_dashas: dict, now: datetime = None) -> tuple:
    """
    Get current Chara Dasha mahadasha and antardasha.
    Returns (md_sign, md_start, md_end, ad_sign, ad_start, ad_end)
    """
    if now is None:
        now = datetime.utcnow()

    current_md = None
    current_ad = None

    for md in chara_dashas.get("mahadashas", []):
        sd = _parse_dt(md.get("start_date") or md.get("start_datetime",""))
        ed = _parse_dt(md.get("end_date")   or md.get("end_datetime",""))
        # Make timezone-naive for comparison
        sd = sd.replace(tzinfo=None) if sd.tzinfo else sd
        ed = ed.replace(tzinfo=None) if ed.tzinfo else ed
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        if sd <= now_naive <= ed:
            current_md = md
            break

    for ad in chara_dashas.get("antardashas", []):
        sd = _parse_dt(ad.get("start_date") or ad.get("start_datetime",""))
        ed = _parse_dt(ad.get("end_date")   or ad.get("end_datetime",""))
        sd = sd.replace(tzinfo=None) if sd.tzinfo else sd
        ed = ed.replace(tzinfo=None) if ed.tzinfo else ed
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        parent = ad.get("parent_sign","")
        if current_md and parent == current_md.get("sign","") and sd <= now_naive <= ed:
            current_ad = ad
            break

    md_sign  = current_md.get("sign","") if current_md else ""
    md_start = _parse_dt(current_md.get("start_date") or current_md.get("start_datetime","")).year if current_md else ""
    md_end   = _parse_dt(current_md.get("end_date") or current_md.get("end_datetime","")).year if current_md else ""
    ad_sign  = current_ad.get("sign","") if current_ad else ""
    ad_end_dt = _parse_dt(current_ad.get("end_date") or current_ad.get("end_datetime","")) if current_ad else None
    ad_end   = ad_end_dt.strftime("%b %Y") if ad_end_dt else ""

    return md_sign, md_start, md_end, ad_sign, ad_end


def build_jaimini_context_block(
    chart_data: dict,
    chara_dashas: dict,
    d9_chart: dict = None,
) -> str:
    """
    Build complete Jaimini analysis block for LLM context.
    This is what gets injected into the master context.
    """
    planets  = chart_data.get("planets", {})
    lagna    = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","") if isinstance(lagna, dict) else str(lagna)

    # 1. Extract Charakarakas
    karakas = extract_charakarakas(planets)

    # 2. Karakamsha
    if d9_chart is None:
        d9_chart = chart_data.get("divisional_charts",{}).get("d9",{})
    karakamsha = calculate_karakamsha(karakas, d9_chart)

    # 3. Current Chara Dasha
    md_sign, md_start, md_end, ad_sign, ad_end = get_current_chara_dasha(chara_dashas)

    # 4. Rotating lagna analysis for current MD
    md_analysis = analyze_chara_dasha_period(md_sign, karakas, planets, lagna_sign) if md_sign else {}

    # 5. Rotating lagna analysis for current AD (within MD)
    ad_analysis = analyze_chara_dasha_period(ad_sign, karakas, planets, lagna_sign) if ad_sign else {}

    # Build output block
    lines = [
        "═══════════════════════════════════════════════════════",
        "JAIMINI CHARA DASHA ANALYSIS",
        "═══════════════════════════════════════════════════════",
        "",
        "7 CHARAKARAKAS (soul significators — fixed from birth chart):",
    ]

    for kname, kdata in karakas.items():
        abbrev  = kdata.get("abbrev","")
        planet  = kdata.get("planet","")
        sign    = kdata.get("sign","")
        house   = kdata.get("house","")
        meaning = kdata.get("meaning","")
        lines.append(f"  {abbrev:<4} {kname:<16} → {planet} in {sign} (house {house}) — {meaning}")

    _ak_planet = karakas.get('Atmakaraka', {}).get('planet', '?')
    _kk_sign   = karakamsha.get('sign', '?')
    _kk_aspects = ', '.join(karakamsha.get('aspecting_signs', []))
    lines += [
        "",
        "KARAKAMSHA (soul's life purpose platform):",
        f"  AK ({_ak_planet}) in D9 = {_kk_sign} sign",
        "  This is the Karakamsha lagna — soul's operating domain",
        f"  Rashi aspects on Karakamsha: {_kk_aspects}",
        "",
        "CURRENT CHARA DASHA:",
        f"  Mahadasha sign: {md_sign} ({md_start}–{md_end})",
        f"  Antardasha sign: {ad_sign} (until {ad_end})",
    ]

    if md_analysis:
        lines += [
            "",
            f"ROTATING LAGNA ANALYSIS — {md_sign} as temporary lagna:",
            f"  Overall quality: {md_analysis.get('overall_quality','').upper()}",
            "",
            "  Karaka positions from this lagna:",
        ]
        for kname, kd in md_analysis.get("karaka_houses",{}).items():
            abbrev  = KARAKA_ABBREV.get(kname,"")
            planet  = kd.get("planet","")
            house   = kd.get("house","")
            sign    = kd.get("sign","")
            quality = ""
            if kname == "Gnatikaraka" and house in [6,8,12]:
                quality = " ← ⚠ WARNING"
            elif kname == "Atmakaraka" and house in [1,5,9,10,11]:
                quality = " ← ✓ PEAK"
            elif kname == "Amatyakaraka" and house in [10,11,2]:
                quality = " ← ✓ CAREER/WEALTH PEAK"
            elif kname == "Darakaraka" and house in [6,8,12]:
                quality = " ← ⚠ RELATIONSHIP STRESS"
            lines.append(f"    {abbrev:<4} {kname:<16}: {planet} in house {house} ({sign}){quality}")

    if md_analysis.get("highlights"):
        lines.append("")
        lines.append("  PERIOD HIGHLIGHTS:")
        for h in md_analysis["highlights"]:
            lines.append(f"    ✓ {h}")

    if md_analysis.get("warnings"):
        lines.append("")
        lines.append("  PERIOD WARNINGS (MUST mention remedies):")
        for w in md_analysis["warnings"]:
            lines.append(f"    ⚠ [{w.get('severity')}] {w.get('message')}")
            lines.append(f"      Remedy: {w.get('remedy')}")

    if ad_sign and ad_analysis:
        lines += [
            "",
            f"ANTARDASHA ROTATING LAGNA — {ad_sign} as sub-lagna:",
            f"  Quality: {ad_analysis.get('overall_quality','').upper()}",
        ]
        ad_warnings = ad_analysis.get("warnings",[])
        ad_highlights = ad_analysis.get("highlights",[])
        if ad_warnings:
            for w in ad_warnings:
                lines.append(f"  ⚠ AD WARNING: {w.get('message')}")
        if ad_highlights:
            for h in ad_highlights[:2]:
                lines.append(f"  ✓ AD HIGHLIGHT: {h}")

    # Confluence check
    confluence = md_analysis.get("confluence_factors",[]) + ad_analysis.get("confluence_factors",[])
    if confluence:
        lines += [
            "",
            f"CONFLUENCE FACTORS: {', '.join(confluence)}",
            "  → When Vimsottari and Jaimini both indicate same theme: confidence 85%+",
        ]

    lines += [
        "",
        "JAIMINI RULES REFERENCE:",
        "  • AK in houses 1,5,9,10,11 from Chara Dasha lagna = peak soul expression",
        "  • GK in houses 6,8,12 = enemy/health/loss warning — apply Lal Kitab remedy",
        "  • AmK in houses 10,11,2 = career and financial breakthrough",
        "  • DK in houses 6,8,12 = relationship/partnership under severe stress",
        "  • Rashi aspects: Movable aspects Fixed (not adjacent), Fixed aspects Movable (not adjacent), Dual aspects Dual",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)


def jaimini_from_dasha_rows(dasha_rows: list) -> dict:
    """
    Convert DB dasha_periods rows (jaimini system) into
    the {mahadashas, antardashas} format expected by get_current_chara_dasha.
    """
    mahadashas  = []
    antardashas = []

    for row in dasha_rows:
        if row.get("system") != "jaimini":
            continue
        level = row.get("type","")
        sign  = row.get("planet_or_sign","")
        sd    = str(row.get("start_date",""))
        ed    = str(row.get("end_date",""))
        meta  = row.get("metadata") or {}
        parent = meta.get("parent_lord","") if isinstance(meta,dict) else ""

        entry = {
            "sign":       sign,
            "sign_index": SIGNS.index(sign) if sign in SIGNS else 0,
            "start_date": sd,
            "end_date":   ed,
            "duration_years": row.get("duration_years", 0),
        }

        if level == "mahadasha":
            mahadashas.append(entry)
        elif level == "antardasha":
            entry["parent_sign"] = parent
            antardashas.append(entry)

    return {"mahadashas": mahadashas, "antardashas": antardashas}
