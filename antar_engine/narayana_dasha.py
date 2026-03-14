"""
antar_engine/narayana_dasha.py

Jaimini Narayana Dasha (also called Padakrama Dasha)
————————————————————————————————————————————————————
The most powerful Jaimini dasha for timing:
  - Career peaks and falls
  - Raj Yoga activation
  - Authority and recognition windows
  - When specific house themes manifest

Rules:
  1. Sign-based dasha (like Chara) — each sign gets a period
  2. Duration = count of signs from that sign to its lord
     - Odd signs (Aries=1,Gemini=3,Leo=5,Libra=7,Sag=9,Aquarius=11):
       count FORWARD from sign to lord (inclusive of lord)
     - Even signs (Taurus=2,Cancer=4,Virgo=6,Scorpio=8,Cap=10,Pisces=12):
       count BACKWARD from sign to lord (inclusive of lord)
  3. Rahu/Ketu: use their dispositor's sign
  4. If lord is IN the sign: duration = 12 years
  5. Starting sign:
     - Compare Lagna vs 7th house strength
     - Stronger starts the sequence
     - Strength: more planets = stronger; if equal, lagna wins
  6. Sequence goes forward from starting sign

Special rules for Raj Yoga:
  - When Narayana Dasha sign contains Raj Yoga planets → peak activation
  - When dasha sign lord is in kendra/trikona → favorable
  - When dasha sign is aspected by Jupiter → expansion period
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Tuple

SIGNS_LIST = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS_BY_NAME = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# 1-indexed: odd signs are 1,3,5,7,9,11 (Aries,Gemini,Leo,Libra,Sag,Aquarius)
ODD_SIGNS_0  = [0, 2, 4, 6, 8, 10]   # 0-indexed odd signs
EVEN_SIGNS_0 = [1, 3, 5, 7, 9, 11]   # 0-indexed even signs

PLANET_SIGN_IDX = {
    "Sun": 4, "Moon": 3, "Mars": 0,    # Natural own sign (first one)
    "Mercury": 2, "Jupiter": 8, "Venus": 1,
    "Saturn": 9, "Rahu": 6, "Ketu": 0,  # Rahu→Libra, Ketu→Aries (dispositors used in practice)
}


def _count_signs_forward(start_idx: int, end_idx: int) -> int:
    """Count signs from start to end going FORWARD, inclusive of end."""
    if start_idx == end_idx:
        return 12
    count = 0
    current = start_idx
    while True:
        current = (current + 1) % 12
        count += 1
        if current == end_idx:
            return count


def _count_signs_backward(start_idx: int, end_idx: int) -> int:
    """Count signs from start to end going BACKWARD, inclusive of end."""
    if start_idx == end_idx:
        return 12
    count = 0
    current = start_idx
    while True:
        current = (current - 1) % 12
        count += 1
        if current == end_idx:
            return count


def get_narayana_dasha_years(sign_idx: int, planet_signs: Dict[str, int]) -> int:
    """
    Calculate Narayana Dasha years for a given sign.

    Args:
        sign_idx:     0-based sign index (0=Aries...11=Pisces)
        planet_signs: dict of planet → sign_idx from birth chart

    Returns:
        Duration in years (1-12)
    """
    sign_name = SIGNS_LIST[sign_idx]
    lord_name = SIGN_LORDS_BY_NAME[sign_name]

    # Get lord's sign from actual chart
    lord_sign_idx = planet_signs.get(lord_name, PLANET_SIGN_IDX.get(lord_name, 0))

    # If lord is in own sign → 12 years
    if lord_sign_idx == sign_idx:
        return 12

    # Odd sign → count forward
    if sign_idx in ODD_SIGNS_0:
        years = _count_signs_forward(sign_idx, lord_sign_idx)
    else:
        # Even sign → count backward
        years = _count_signs_backward(sign_idx, lord_sign_idx)

    return max(1, min(12, years))


def _determine_starting_sign(lagna_idx: int, planet_signs: Dict[str, int],
                              planets_houses: Dict[str, int]) -> int:
    """
    Determine which sign starts the Narayana Dasha sequence.
    Compare Lagna (1st house) vs 7th house — stronger one starts.

    Strength criteria:
    1. Sign with more planets in it
    2. If equal, Lagna wins
    3. If lagna lord is in lagna → lagna starts
    4. If 7th lord is in 7th → 7th starts
    """
    seventh_idx = (lagna_idx + 6) % 12

    # Count planets in lagna and 7th
    lagna_planets  = sum(1 for s in planet_signs.values() if s == lagna_idx)
    seventh_planets = sum(1 for s in planet_signs.values() if s == seventh_idx)

    # Check if lords are in own sign
    lagna_lord = SIGN_LORDS_BY_NAME[SIGNS_LIST[lagna_idx]]
    seventh_lord = SIGN_LORDS_BY_NAME[SIGNS_LIST[seventh_idx]]
    lagna_lord_in_lagna   = planet_signs.get(lagna_lord) == lagna_idx
    seventh_lord_in_seventh = planet_signs.get(seventh_lord) == seventh_idx

    # Decision
    if lagna_lord_in_lagna and not seventh_lord_in_seventh:
        return lagna_idx
    if seventh_lord_in_seventh and not lagna_lord_in_lagna:
        return seventh_idx
    if lagna_planets > seventh_planets:
        return lagna_idx
    if seventh_planets > lagna_planets:
        return seventh_idx

    # Default: lagna starts
    return lagna_idx


def _calculate_first_dasha_balance(
    start_sign_idx: int,
    birth_jd: float,
    planet_signs: Dict[str, int],
    lagna_idx: int,
    lagna_degree: float,
) -> float:
    """
    Calculate how much of the first dasha has elapsed at birth.
    Based on how far through the lagna sign the ascendant degree is.

    Fraction elapsed = lagna_degree / 30
    Remaining = total_years * (1 - fraction_elapsed)
    """
    total_years = get_narayana_dasha_years(start_sign_idx, planet_signs)
    fraction_elapsed = lagna_degree / 30.0
    remaining = total_years * (1.0 - fraction_elapsed)
    return max(0.01, remaining)


def calculate_narayana_dasha(chart_data: dict, birth_jd: float) -> dict:
    """
    Calculate complete Narayana Dasha from birth chart.

    Returns dict with:
        mahadashas:  list of 12 sign periods
        antardashas: list of sub-periods within each mahadasha
    """
    planets  = chart_data.get("planets", {})
    lagna    = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","Aries") if isinstance(lagna, dict) else "Aries"
    lagna_deg  = lagna.get("degree", 0) if isinstance(lagna, dict) else 0
    lagna_idx  = SIGNS_LIST.index(lagna_sign) if lagna_sign in SIGNS_LIST else 0

    # Build planet_signs dict (0-based sign index for each planet)
    planet_signs = {}
    for planet, data in planets.items():
        sign = data.get("sign","")
        if sign in SIGNS_LIST:
            planet_signs[planet] = SIGNS_LIST.index(sign)

    # Determine starting sign
    start_sign_idx = _determine_starting_sign(lagna_idx, planet_signs, {})

    # Get birth datetime from JD
    import swisseph as swe
    y, m, d, h = swe.revjul(birth_jd)
    birth_dt = datetime(int(y), int(m), int(d),
                         int(h), int((h % 1) * 60))

    # Calculate first dasha balance
    first_balance = _calculate_first_dasha_balance(
        start_sign_idx, birth_jd, planet_signs, lagna_idx, lagna_deg)

    # Generate all 12 sign periods
    mahadashas  = []
    antardashas = []
    current_dt  = birth_dt

    # Generate enough cycles to cover 120 years
    i = 0
    cycle = 0
    max_years = 120
    while (current_dt - birth_dt).days / 365.25 < max_years:
        sign_idx  = (start_sign_idx + i) % 12
        sign_name = SIGNS_LIST[sign_idx]
        full_years = get_narayana_dasha_years(sign_idx, planet_signs)

        # First dasha balance only applies at the very beginning
        if i == 0 and cycle == 0:
            period_years = first_balance
        else:
            period_years = float(full_years)

        years_int = int(period_years)
        frac      = period_years - years_int
        end_dt    = current_dt + relativedelta(years=years_int) + \
                    timedelta(days=frac * 365.25)

        md = {
            "sign":          sign_name,
            "sign_index":    sign_idx,
            "sign_lord":     SIGN_LORDS_BY_NAME[sign_name],
            "start_date":    current_dt.strftime("%Y-%m-%d"),
            "end_date":      end_dt.strftime("%Y-%m-%d"),
            "start_datetime": current_dt,
            "end_datetime":   end_dt,
            "duration_years": round(period_years, 4),
            "full_years":     full_years,
            "sequence":       (cycle * 12) + (i % 12),
        }
        mahadashas.append(md)

        # Calculate antardashas for this mahadasha
        # Antardasha sequence: starts from same sign, goes forward
        ad_current = current_dt
        for j in range(12):
            ad_sign_idx  = (sign_idx + j) % 12
            ad_sign_name = SIGNS_LIST[ad_sign_idx]
            ad_years_full = get_narayana_dasha_years(ad_sign_idx, planet_signs)

            # AD proportion = (ad_years / 12) * MD years
            ad_proportion = (ad_years_full / 12.0) * period_years
            ad_years_int  = int(ad_proportion)
            ad_frac       = ad_proportion - ad_years_int
            ad_end        = ad_current + relativedelta(years=ad_years_int) + \
                            timedelta(days=ad_frac * 365.25)

            antardashas.append({
                "sign":          ad_sign_name,
                "sign_index":    ad_sign_idx,
                "sign_lord":     SIGN_LORDS_BY_NAME[ad_sign_name],
                "parent_sign":   sign_name,
                "start_date":    ad_current.strftime("%Y-%m-%d"),
                "end_date":      ad_end.strftime("%Y-%m-%d"),
                "start_datetime": ad_current,
                "end_datetime":   ad_end,
                "duration_years": round(ad_proportion, 4),
                "sequence":       j,
                "parent_sequence": (cycle * 12) + (i % 12),
            })
            ad_current = ad_end

        current_dt = end_dt
        i += 1
        if i % 12 == 0:
            cycle += 1

    return {
        "mahadashas":  mahadashas,
        "antardashas": antardashas,
        "start_sign":  SIGNS_LIST[start_sign_idx],
        "lagna_sign":  lagna_sign,
    }


def get_current_narayana_period(narayana: dict, now: datetime = None) -> Tuple[Optional[dict], Optional[dict]]:
    """Get current Narayana Dasha mahadasha and antardasha."""
    if now is None:
        now = datetime.utcnow()

    current_md = current_ad = None

    for md in narayana.get("mahadashas", []):
        sd = md["start_datetime"] if isinstance(md["start_datetime"], datetime) else \
             datetime.strptime(md["start_date"], "%Y-%m-%d")
        ed = md["end_datetime"] if isinstance(md["end_datetime"], datetime) else \
             datetime.strptime(md["end_date"], "%Y-%m-%d")
        sd = sd.replace(tzinfo=None)
        ed = ed.replace(tzinfo=None)
        now_n = now.replace(tzinfo=None)
        if sd <= now_n <= ed:
            current_md = md
            break

    if current_md:
        for ad in narayana.get("antardashas", []):
            if ad.get("parent_sign") != current_md["sign"]:
                continue
            sd = ad["start_datetime"] if isinstance(ad["start_datetime"], datetime) else \
                 datetime.strptime(ad["start_date"], "%Y-%m-%d")
            ed = ad["end_datetime"] if isinstance(ad["end_datetime"], datetime) else \
                 datetime.strptime(ad["end_date"], "%Y-%m-%d")
            sd = sd.replace(tzinfo=None)
            ed = ed.replace(tzinfo=None)
            now_n = now.replace(tzinfo=None)
            if sd <= now_n <= ed:
                current_ad = ad
                break

    return current_md, current_ad


def analyze_narayana_period(
    period_sign: str,
    chart_data: dict,
    yogas: list,
    is_antardasha: bool = False,
) -> dict:
    """
    Analyze the quality and themes of a Narayana Dasha period.

    Key rules:
    - Planets in the dasha sign = activated during this period
    - Raj Yoga in dasha sign or aspecting it = Raj Yoga manifests
    - Lord of dasha sign in kendra/trikona = favorable
    - Dasha sign = 10th from lagna → career peak
    - Dasha sign aspected by Jupiter → expansion and fortune
    """
    SIGNS_STR = SIGNS_LIST
    KENDRA    = [1, 4, 7, 10]
    TRIKONA   = [1, 5, 9]
    DUSTHANA  = [6, 8, 12]

    planets   = chart_data.get("planets", {})
    lagna     = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","") if isinstance(lagna,dict) else str(lagna)
    lagna_idx  = SIGNS_STR.index(lagna_sign) if lagna_sign in SIGNS_STR else 0
    house_lords= chart_data.get("house_lords",{})

    period_idx = SIGNS_STR.index(period_sign) if period_sign in SIGNS_STR else 0
    house_from_lagna = ((period_idx - lagna_idx) % 12) + 1
    period_lord = SIGN_LORDS_BY_NAME[period_sign]
    lord_house  = planets.get(period_lord, {}).get("house", 0)

    # Planets in this sign (activated)
    activated_planets = [p for p, d in planets.items()
                         if d.get("sign") == period_sign]

    # Raj Yoga activation check
    raj_yogas_active = []
    for yoga in yogas:
        if yoga.get("strength") == "strong" and "Raj" in yoga.get("name",""):
            yoga_planets = yoga.get("planets",[])
            # If any yoga planet is in the dasha sign or dasha sign lord is yoga planet
            if period_lord in yoga_planets or any(
                planets.get(p,{}).get("sign") == period_sign for p in yoga_planets
            ):
                raj_yogas_active.append(yoga["name"])

    # Quality assessment
    highlights = []
    warnings   = []
    score      = 50  # base

    # House quality of the period sign
    if house_from_lagna in KENDRA:
        highlights.append(f"Narayana period in angular house {house_from_lagna} — major life events, visibility")
        score += 15
    elif house_from_lagna in TRIKONA:
        highlights.append(f"Narayana period in trinal house {house_from_lagna} — fortune, dharma, blessing")
        score += 20
    elif house_from_lagna in DUSTHANA:
        warnings.append(f"Narayana period in difficult house {house_from_lagna} — challenges, transformation")
        score -= 15

    # Lord's strength
    if lord_house in KENDRA or lord_house in TRIKONA:
        highlights.append(f"Period lord {period_lord} in house {lord_house} — strong, delivers results")
        score += 15
    elif lord_house in DUSTHANA:
        warnings.append(f"Period lord {period_lord} in house {lord_house} — weakened, obstacles in delivery")
        score -= 10

    # Planets activated
    if activated_planets:
        highlights.append(f"Activated planets: {', '.join(activated_planets)} — these planets' life themes peak")
        score += len(activated_planets) * 5

    # Raj Yoga
    if raj_yogas_active:
        highlights.append(f"RAJ YOGA ACTIVATED: {', '.join(raj_yogas_active)} — authority and recognition peak")
        score += 25

    # Jupiter aspect on period sign
    jup_house = planets.get("Jupiter", {}).get("house", 0)
    jup_aspects = [jup_house, (jup_house+4)%12 or 12,
                   (jup_house+6)%12 or 12, (jup_house+8)%12 or 12]
    if house_from_lagna in jup_aspects:
        highlights.append(f"Jupiter aspects this period sign — divine expansion and protection")
        score += 15

    # 10th house period = career peak
    if house_from_lagna == 10:
        highlights.append("NARAYANA IN 10TH — career authority peak. This is when you reach the top.")
        score += 20

    # 7th house period = partnerships
    if house_from_lagna == 7:
        highlights.append("Narayana in 7th — major partnerships, business deals, possible marriage timing")
        score += 10

    overall_quality = (
        "exceptional" if score >= 90 else
        "excellent"   if score >= 75 else
        "favorable"   if score >= 60 else
        "neutral"     if score >= 45 else
        "challenging"
    )

    return {
        "period_sign":        period_sign,
        "house_from_lagna":   house_from_lagna,
        "period_lord":        period_lord,
        "lord_house":         lord_house,
        "activated_planets":  activated_planets,
        "raj_yogas_active":   raj_yogas_active,
        "highlights":         highlights,
        "warnings":           warnings,
        "quality":            overall_quality,
        "score":              min(99, max(10, score)),
    }


def build_narayana_context_block(
    chart_data: dict,
    narayana: dict,
    yogas: list = None,
) -> str:
    """Build Narayana Dasha context block for LLM."""
    if not narayana or not narayana.get("mahadashas"):
        return ""

    if yogas is None:
        yogas = chart_data.get("yogas",[])

    now = datetime.utcnow()
    current_md, current_ad = get_current_narayana_period(narayana, now)

    lines = [
        "═══════════════════════════════════════════════════════",
        "JAIMINI NARAYANA DASHA (Career & Authority Timing)",
        f"Starting sign: {narayana.get('start_sign','')}",
        "═══════════════════════════════════════════════════════",
        "",
        "NARAYANA RULES:",
        "  • Sign-based timing for career peaks and Raj Yoga activation",
        "  • Dasha in 10th house sign = career authority peaks",
        "  • Dasha sign with Raj Yoga planets = authority manifests",
        "  • Dasha sign lord in kendra/trikona = results delivered fully",
        "  • Jupiter aspecting dasha sign = fortune and expansion",
        "",
    ]

    if current_md:
        md_analysis = analyze_narayana_period(
            current_md["sign"], chart_data, yogas)

        lines += [
            f"CURRENT NARAYANA MAHADASHA: {current_md['sign']} ({current_md['start_date'][:4]}–{current_md['end_date'][:4]})",
            f"  House from lagna: {md_analysis['house_from_lagna']}",
            f"  Period lord: {md_analysis['period_lord']} in house {md_analysis['lord_house']}",
            f"  Quality: {md_analysis['quality'].upper()} (score {md_analysis['score']}/100)",
        ]

        if md_analysis["activated_planets"]:
            lines.append(f"  Activated planets: {', '.join(md_analysis['activated_planets'])}")

        if md_analysis["raj_yogas_active"]:
            lines.append(f"  ⭐ RAJ YOGA ACTIVE: {', '.join(md_analysis['raj_yogas_active'])}")

        for h in md_analysis["highlights"]:
            lines.append(f"  ✓ {h}")
        for w in md_analysis["warnings"]:
            lines.append(f"  ⚠ {w}")

    if current_ad:
        ad_analysis = analyze_narayana_period(
            current_ad["sign"], chart_data, yogas, is_antardasha=True)
        lines += [
            "",
            f"CURRENT NARAYANA ANTARDASHA: {current_ad['sign']} (until {current_ad['end_date'][:7]})",
            f"  Quality: {ad_analysis['quality'].upper()} | House: {ad_analysis['house_from_lagna']}",
        ]
        if ad_analysis["raj_yogas_active"]:
            lines.append(f"  ⭐ Sub-period Raj Yoga: {', '.join(ad_analysis['raj_yogas_active'])}")

    # Upcoming peak periods (next 2 mahadashas)
    upcoming_peaks = []
    for md in narayana.get("mahadashas",[]):
        try:
            sd = datetime.strptime(md["start_date"],"%Y-%m-%d")
            if sd > now:
                analysis = analyze_narayana_period(md["sign"], chart_data, yogas)
                if analysis["score"] >= 70:
                    upcoming_peaks.append(
                        f"  {md['sign']} MD ({md['start_date'][:4]}–{md['end_date'][:4]}) — "
                        f"{analysis['quality'].upper()}, house {analysis['house_from_lagna']}"
                        + (f" — RAJ YOGA" if analysis['raj_yogas_active'] else "")
                    )
        except Exception:
            pass

    if upcoming_peaks:
        lines += ["", "UPCOMING PEAK NARAYANA PERIODS:"]
        lines += upcoming_peaks[:3]

    lines += [
        "",
        "NARAYANA vs VIMSOTTARI CONFLUENCE:",
        "  When Narayana MD sign matches Vimsottari MD lord's sign → 85%+ confidence",
        "  Narayana activates EXTERNAL events; Vimsottari activates INTERNAL themes",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)


def narayana_to_db_rows(narayana: dict, chart_id: str) -> list:
    """Convert Narayana Dasha to DB rows for dasha_periods table."""
    rows = []
    for md in narayana.get("mahadashas",[]):
        rows.append({
            "chart_id":       chart_id,
            "system":         "narayana",
            "type":           "mahadasha",
            "planet_or_sign": md["sign"],
            "start_date":     md["start_date"],
            "end_date":       md["end_date"],
            "duration_years": md["duration_years"],
            "sequence":       md["sequence"],
            "metadata": {
                "sign_lord":   md["sign_lord"],
                "full_years":  md["full_years"],
                "parent_lord": "",
                "type":        "mahadasha",
            },
        })
    for ad in narayana.get("antardashas",[]):
        rows.append({
            "chart_id":       chart_id,
            "system":         "narayana",
            "type":           "antardasha",
            "planet_or_sign": ad["sign"],
            "start_date":     ad["start_date"],
            "end_date":       ad["end_date"],
            "duration_years": ad["duration_years"],
            "sequence":       ad["sequence"],
            "metadata": {
                "sign_lord":   ad["sign_lord"],
                "parent_lord": ad["parent_sign"],
                "type":        "antardasha",
            },
        })
    return rows
