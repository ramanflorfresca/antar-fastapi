"""
antar_engine/divisional_career.py

Divisional Chart Career & Wealth Analysis Engine
──────────────────────────────────────────────────────────────────────
Answers:
  "What career works best for me?"
  "What line of work gives me the most growth?"
  "When will my funding happen?"
  "What is my peak earning potential?"
  "Am I suited for entrepreneurship or employment?"

Charts used:
  D-1  Rashi         → overall life, lagna lord, 10th house lord
  D-9  Navamsa       → soul purpose, deeper career potential
  D-10 Dashamsha     → career specifically, professional destiny
  D-2  Hora          → wealth accumulation, financial flow
  D-24 Chaturvimsa   → education and skills

All calculations are REAL-TIME from stored birth chart.
Nothing here needs to be pre-saved.

The output feeds into prompt_builder as a context block.
DeepSeek then gives the human narrative.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ── Sign data ─────────────────────────────────────────────────────────────────

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

# ── Planet career domains ─────────────────────────────────────────────────────

PLANET_CAREER_DOMAINS = {
    "Sun": {
        "fields":      ["Government", "Administration", "Politics", "Leadership",
                        "Medicine (senior)", "Gold/Precious metals", "Father-related work"],
        "work_style":  "Authority, leadership, recognition. Works best with autonomy.",
        "peak_timing": "Sun dasha/antardasha, Sunday transits, summer months",
        "wealth_type": "Salary, authority bonuses, government grants",
        "growth_mode": "Through recognition and rising in hierarchy",
    },
    "Moon": {
        "fields":      ["Healthcare", "Nursing", "Hospitality", "Food & Beverage",
                        "Real Estate", "Psychology", "Import-Export", "Public relations",
                        "Fashion", "Childcare"],
        "work_style":  "Intuitive, people-oriented, nurturing. Works best with the public.",
        "peak_timing": "Moon dasha, Monday transits, full moon periods",
        "wealth_type": "Variable income, tips, public-facing business",
        "growth_mode": "Through public reputation and emotional connection",
    },
    "Mars": {
        "fields":      ["Engineering", "Surgery", "Military", "Sports", "Construction",
                        "Real Estate development", "Manufacturing", "Police/Law enforcement",
                        "Entrepreneurship", "Fire safety", "Metallurgy"],
        "work_style":  "Action-oriented, competitive, decisive. Works best independently.",
        "peak_timing": "Mars dasha, Tuesday transits, Mars-Jupiter conjunctions",
        "wealth_type": "Performance bonuses, contracts, competitive wins",
        "growth_mode": "Through bold action and competitive dominance",
    },
    "Mercury": {
        "fields":      ["Technology", "Writing", "Journalism", "Trading", "Accounting",
                        "Consulting", "Education", "Publishing", "Marketing", "Law",
                        "Data Science", "Communication industries", "Startups"],
        "work_style":  "Analytical, communicative, multi-tasking. Works best with ideas.",
        "peak_timing": "Mercury dasha, Wednesday transits, Mercury direct periods",
        "wealth_type": "Intellectual property, consulting fees, trading profits",
        "growth_mode": "Through expertise, communication, and networks",
    },
    "Jupiter": {
        "fields":      ["Finance", "Banking", "Law", "Teaching", "Philosophy",
                        "International business", "Publishing", "Religion", "Consulting",
                        "Non-profit leadership", "Academia", "Venture capital"],
        "work_style":  "Expansive, wisdom-sharing, growth-oriented. Works best as a guide.",
        "peak_timing": "Jupiter dasha, Thursday transits, Jupiter direct periods",
        "wealth_type": "Investments, dividends, advisory fees, institutional money",
        "growth_mode": "Through expansion, wisdom, and trusted relationships",
    },
    "Venus": {
        "fields":      ["Arts", "Music", "Film", "Fashion", "Beauty", "Luxury goods",
                        "Hospitality", "Interior design", "Jewellery", "Entertainment",
                        "Diplomacy", "Relationship counselling", "Photography"],
        "work_style":  "Creative, aesthetic, harmony-seeking. Works best with beauty.",
        "peak_timing": "Venus dasha, Friday transits, Venus-Jupiter periods",
        "wealth_type": "Creative royalties, luxury commissions, aesthetic services",
        "growth_mode": "Through beauty, relationships, and aesthetic excellence",
    },
    "Saturn": {
        "fields":      ["Law", "Government service", "Mining", "Agriculture", "Oil & Gas",
                        "Real Estate (long-term)", "Waste management", "Construction",
                        "Research", "Auditing", "Social work", "Academia (structured)"],
        "work_style":  "Disciplined, systematic, long-term. Works best with structure.",
        "peak_timing": "Saturn dasha (slow build), Saturday transits, age 36-42 especially",
        "wealth_type": "Slow and steady accumulation, pension, property appreciation",
        "growth_mode": "Through patience, mastery, and long-term systems",
    },
    "Rahu": {
        "fields":      ["Technology", "AI/Cutting-edge tech", "Foreign companies",
                        "Media & Influence", "Politics (unconventional)", "Import-Export",
                        "Research into unknown", "Cryptocurrency", "Film/Fame",
                        "International organizations"],
        "work_style":  "Ambitious, unconventional, foreign-connected. Breaks rules.",
        "peak_timing": "Rahu dasha (18 years of fast rise), eclipses, foreign opportunities",
        "wealth_type": "Windfall, sudden gains, foreign money, disruptive business",
        "growth_mode": "Through disruption, foreign connections, and ambition",
    },
    "Ketu": {
        "fields":      ["Spirituality", "Research", "Healing", "Alternative medicine",
                        "Mysticism", "Technical expertise (niche)", "Isolation-based work",
                        "Archives", "Ancient knowledge"],
        "work_style":  "Detached, intuitive, expert. Works best alone in specialized fields.",
        "peak_timing": "Ketu dasha (liberation, past skills resurface)",
        "wealth_type": "Minimal but sufficient, or sudden windfall from past karma",
        "growth_mode": "Through past-life mastery resurfacing",
    },
}

# ── 10th lord career themes ───────────────────────────────────────────────────

TENTH_LORD_THEMES = {
    "Sun":     "Leadership, authority, government, recognition-based career",
    "Moon":    "Public-facing, nurturing, hospitality, emotional service",
    "Mars":    "Action, competition, engineering, entrepreneurship, courage",
    "Mercury": "Communication, intellect, trade, technology, education",
    "Jupiter": "Wisdom, expansion, finance, teaching, advisory",
    "Venus":   "Arts, beauty, creativity, luxury, harmony",
    "Saturn":  "Long-term, structured, disciplined, mastery over time",
    "Rahu":    "Unconventional, disruptive, foreign, ambition-driven",
    "Ketu":    "Specialized expertise, spiritual, past-life skills",
}

# ── Atmakaraka career influence ───────────────────────────────────────────────

ATMAKARAKA_CAREER = {
    "Sun":     "Soul purpose through leadership and self-expression. Career is about authority.",
    "Moon":    "Soul purpose through nurturing and public service. Career is about care.",
    "Mars":    "Soul purpose through courage and action. Career is about building.",
    "Mercury": "Soul purpose through communication and intellect. Career is about expression.",
    "Jupiter": "Soul purpose through wisdom and expansion. Career is about guiding others.",
    "Venus":   "Soul purpose through beauty and love. Career is about creating harmony.",
    "Saturn":  "Soul purpose through discipline and justice. Career is about service to many.",
    "Rahu":    "Soul is hungry for achievement. Career is about becoming, not just being.",
}

# ── Amatyakaraka (career karaka) ─────────────────────────────────────────────

AMATYAKARAKA_CAREER = {
    "Sun":     "Career prospers through recognition, authority, and senior positions",
    "Moon":    "Career prospers through public connection, intuition, and nurturing roles",
    "Mars":    "Career prospers through initiative, courage, and competitive energy",
    "Mercury": "Career prospers through communication, analysis, and intellectual work",
    "Jupiter": "Career prospers through wisdom, expansion, and advisory roles",
    "Venus":   "Career prospers through creativity, aesthetics, and relationships",
    "Saturn":  "Career prospers through discipline, mastery, and long-term commitment",
    "Rahu":    "Career prospers through ambition, foreign connections, and disruption",
    "Ketu":    "Career prospers through specialized expertise and detached excellence",
}


# ── Divisional chart calculator ───────────────────────────────────────────────

def calculate_divisional_position(longitude: float, division: int) -> dict:
    """
    Calculate planet's position in a divisional chart.

    Args:
        longitude: planet's absolute longitude (0-360)
        division: 9 for D-9, 10 for D-10, 2 for D-2, etc.

    Returns:
        { sign_index, sign, degree_in_sign }
    """
    # Degree within sign (0-30)
    sign_index    = int(longitude / 30) % 12
    degree_in_sign = longitude % 30

    # Which portion of the sign (each sign divided into 'division' parts)
    portion_size  = 30.0 / division
    portion_num   = int(degree_in_sign / portion_size)   # 0-based

    # D-chart sign calculation
    if division == 9:
        # Navamsa: Movable → Aries, Fixed → Capricorn, Dual → Cancer
        navamsa_starts = {
            0: 0,   # Aries → starts from Aries
            1: 9,   # Taurus → starts from Capricorn
            2: 0,   # Gemini → starts from Aries  (actually Cancer for dual)
            3: 3,   # Cancer → starts from Cancer
            4: 0,   # Leo (movable-ish) → Aries
            5: 3,   # Virgo → Cancer (dual)
            6: 6,   # Libra → Libra (movable)
            7: 9,   # Scorpio → Capricorn (fixed)
            8: 3,   # Sagittarius → Cancer (dual)
            9: 6,   # Capricorn → Libra (movable)
            10: 9,  # Aquarius → Capricorn (fixed)
            11: 3,  # Pisces → Cancer (dual)
        }
        # Traditional navamsa: movable=Aries, fixed=Capricorn, dual=Cancer
        sign_type = sign_index % 3   # 0=movable, 1=fixed, 2=dual
        if sign_type == 0:   navamsa_start = 0   # Aries
        elif sign_type == 1: navamsa_start = 9   # Capricorn
        else:                navamsa_start = 3   # Cancer
        d_sign_index = (navamsa_start + portion_num) % 12

    elif division == 10:
        # Dashamsha: odd signs → Aries onward, even signs → Capricorn onward
        if sign_index % 2 == 0:   # odd sign (Aries, Gemini, Leo...)
            d_sign_index = portion_num % 12
        else:                      # even sign (Taurus, Cancer, Virgo...)
            d_sign_index = (9 + portion_num) % 12   # Capricorn onward

    elif division == 2:
        # Hora: Sun hora (Leo) or Moon hora (Cancer)
        # First half of any sign → ruled by Sun (Leo) or Moon (Cancer)
        # Odd signs: first half = Sun, second half = Moon
        # Even signs: first half = Moon, second half = Sun
        if sign_index % 2 == 0:   # odd sign
            d_sign_index = 4 if portion_num == 0 else 3   # Leo or Cancer
        else:                      # even sign
            d_sign_index = 3 if portion_num == 0 else 4   # Cancer or Leo

    else:
        # Generic formula for other divisions
        d_sign_index = (sign_index * division + portion_num) % 12

    return {
        "sign_index":     d_sign_index,
        "sign":           SIGNS[d_sign_index],
        "lord":           SIGN_LORDS[SIGNS[d_sign_index]],
        "original_sign":  SIGNS[sign_index],
        "portion_num":    portion_num,
    }


def get_all_divisional_positions(chart_data: dict, division: int) -> dict:
    """
    Get all planets' positions in a given divisional chart.

    Returns: { planet_name: { sign, sign_index, lord } }
    """
    planets_div = {}
    for planet, data in chart_data["planets"].items():
        longitude = data.get("longitude")
        if longitude is None:
            continue
        planets_div[planet] = calculate_divisional_position(longitude, division)

    # Lagna
    lagna_lng = chart_data["lagna"].get("longitude")
    if lagna_lng is None:
        # Reconstruct from sign + degree
        lagna_sign = chart_data["lagna"]["sign"]
        lagna_deg  = chart_data["lagna"].get("degree", 0)
        lagna_lng  = SIGN_INDEX[lagna_sign] * 30 + lagna_deg
    planets_div["Lagna"] = calculate_divisional_position(lagna_lng, division)

    return planets_div


# ── Career analysis builder ───────────────────────────────────────────────────

@dataclass
class CareerAnalysis:
    """Complete career and wealth analysis from divisional charts."""

    # D-1 indicators
    d1_lagna:          str = ""
    d1_10th_lord:      str = ""
    d1_10th_sign:      str = ""
    d1_career_theme:   str = ""

    # D-10 indicators (career chart)
    d10_lagna:         str = ""
    d10_10th_lord:     str = ""
    d10_career_theme:  str = ""
    d10_strong_planets: list = field(default_factory=list)

    # D-9 indicators (soul purpose)
    d9_lagna:          str = ""
    d9_atmakaraka_sign: str = ""
    d9_soul_purpose:   str = ""

    # D-2 indicators (wealth)
    d2_lagna:          str = ""
    d2_wealth_lord:    str = ""
    d2_wealth_type:    str = ""

    # Karakas
    atmakaraka:        str = ""
    amatyakaraka:      str = ""
    ak_career:         str = ""
    amk_career:        str = ""

    # Best career fields (synthesized)
    primary_fields:    list = field(default_factory=list)
    secondary_fields:  list = field(default_factory=list)
    work_style:        str = ""

    # Entrepreneurship vs employment
    entrepreneur_score: float = 0.0
    employment_score:   float = 0.0
    recommendation:    str = ""

    # Wealth analysis
    wealth_timing:     list = field(default_factory=list)
    wealth_type:       str = ""
    peak_earning_period: str = ""

    # Funding / investment timing (for entrepreneurs)
    funding_indicators: list = field(default_factory=list)
    funding_timing:    str = ""

    # Dasha timing for career peak
    career_peak_dasha: str = ""
    current_career_phase: str = ""


def build_career_analysis(
    chart_data: dict,
    dashas: dict,
    patra=None,
) -> CareerAnalysis:
    """
    Master function. Analyzes D-1, D-9, D-10, D-2 and returns
    a complete CareerAnalysis object.

    Args:
        chart_data: from Supabase charts.chart_data
        dashas: from get_dashas_for_chart()
        patra: from build_patra_context() (optional but improves accuracy)
    """
    analysis = CareerAnalysis()

    planets   = chart_data["planets"]
    lagna_sign = chart_data["lagna"]["sign"]

    # ── D-1 Analysis ──────────────────────────────────────────────

    # 10th house from lagna
    lagna_idx    = SIGN_INDEX[lagna_sign]
    tenth_idx    = (lagna_idx + 9) % 12
    tenth_sign   = SIGNS[tenth_idx]
    tenth_lord   = SIGN_LORDS[tenth_sign]

    analysis.d1_lagna       = lagna_sign
    analysis.d1_10th_sign   = tenth_sign
    analysis.d1_10th_lord   = tenth_lord
    analysis.d1_career_theme = TENTH_LORD_THEMES.get(tenth_lord, "")

    # ── D-10 Analysis ────────────────────────────────────────────

    d10_positions  = get_all_divisional_positions(chart_data, 10)
    d10_lagna      = d10_positions.get("Lagna", {})
    d10_lagna_sign = d10_lagna.get("sign", "")
    d10_lagna_idx  = SIGN_INDEX.get(d10_lagna_sign, 0)
    d10_tenth_idx  = (d10_lagna_idx + 9) % 12
    d10_tenth_sign = SIGNS[d10_tenth_idx]
    d10_tenth_lord = SIGN_LORDS[d10_tenth_sign]

    analysis.d10_lagna        = d10_lagna_sign
    analysis.d10_10th_lord    = d10_tenth_lord
    analysis.d10_career_theme = TENTH_LORD_THEMES.get(d10_tenth_lord, "")

    # Planets in D-10 10th house → strong career indicators
    d10_strong = []
    for planet, pos in d10_positions.items():
        if planet == "Lagna":
            continue
        if pos.get("sign_index") == d10_tenth_idx:
            d10_strong.append(planet)
    analysis.d10_strong_planets = d10_strong

    # ── D-9 Analysis ─────────────────────────────────────────────

    d9_positions = get_all_divisional_positions(chart_data, 9)
    d9_lagna     = d9_positions.get("Lagna", {})
    analysis.d9_lagna = d9_lagna.get("sign", "")

    # Atmakaraka in D-9 (key soul indicator)
    atmakaraka = _get_atmakaraka(planets)
    analysis.atmakaraka = atmakaraka
    ak_d9_pos  = d9_positions.get(atmakaraka, {})
    analysis.d9_atmakaraka_sign = ak_d9_pos.get("sign", "")
    analysis.d9_soul_purpose    = ATMAKARAKA_CAREER.get(atmakaraka, "")
    analysis.ak_career          = ATMAKARAKA_CAREER.get(atmakaraka, "")

    # Amatyakaraka (career planets karaka)
    amatyakaraka = _get_amatyakaraka(planets)
    analysis.amatyakaraka = amatyakaraka
    analysis.amk_career   = AMATYAKARAKA_CAREER.get(amatyakaraka, "")

    # ── D-2 Analysis (Wealth) ─────────────────────────────────────

    d2_positions  = get_all_divisional_positions(chart_data, 2)
    d2_lagna      = d2_positions.get("Lagna", {})
    d2_lagna_sign = d2_lagna.get("sign", "")
    d2_2nd_idx    = (SIGN_INDEX.get(d2_lagna_sign, 0) + 1) % 12
    d2_2nd_lord   = SIGN_LORDS[SIGNS[d2_2nd_idx]]

    analysis.d2_lagna      = d2_lagna_sign
    analysis.d2_wealth_lord = d2_2nd_lord
    analysis.d2_wealth_type = PLANET_CAREER_DOMAINS.get(d2_2nd_lord, {}).get("wealth_type", "")

    # ── Synthesize career fields ──────────────────────────────────

    field_scores = {}
    for planet, weight in [
        (tenth_lord, 3.0),       # D-1 10th lord — highest weight
        (d10_tenth_lord, 3.0),   # D-10 10th lord — equally high
        (atmakaraka, 2.0),       # soul purpose
        (amatyakaraka, 2.5),     # career karaka
        (d2_2nd_lord, 1.5),      # wealth indicator
    ]:
        domains = PLANET_CAREER_DOMAINS.get(planet, {})
        for field in domains.get("fields", []):
            field_scores[field] = field_scores.get(field, 0) + weight

    # D-10 strong planets add bonus
    for planet in d10_strong:
        for field in PLANET_CAREER_DOMAINS.get(planet, {}).get("fields", []):
            field_scores[field] = field_scores.get(field, 0) + 1.5

    sorted_fields  = sorted(field_scores.items(), key=lambda x: x[1], reverse=True)
    analysis.primary_fields   = [f for f, s in sorted_fields[:5]]
    analysis.secondary_fields = [f for f, s in sorted_fields[5:10]]

    # Work style from dominant planet
    dominant_planet = tenth_lord if tenth_lord == d10_tenth_lord else amatyakaraka
    analysis.work_style = PLANET_CAREER_DOMAINS.get(dominant_planet, {}).get("work_style", "")

    # ── Entrepreneur vs Employment ────────────────────────────────

    entrepreneur_planets = {"Mars", "Rahu", "Sun"}
    employment_planets   = {"Saturn", "Moon", "Mercury", "Jupiter"}

    e_score, emp_score = 0.0, 0.0
    for planet, weight in [
        (tenth_lord, 2), (d10_tenth_lord, 2), (atmakaraka, 1.5), (amatyakaraka, 1.5)
    ]:
        if planet in entrepreneur_planets:
            e_score   += weight
        if planet in employment_planets:
            emp_score += weight

    # Mars lagna or strong Mars → entrepreneur boost
    if lagna_sign in ["Aries", "Scorpio"] or planets.get("Mars", {}).get("sign") in ["Aries", "Capricorn"]:
        e_score += 1

    analysis.entrepreneur_score = e_score
    analysis.employment_score   = emp_score
    analysis.recommendation     = (
        "Self-employment and entrepreneurship are strongly indicated."
        if e_score > emp_score else
        "Employment within an organization or institution suits you well, "
        "with room for leadership as you grow."
        if emp_score > e_score + 2 else
        "You can thrive in both — the key is having autonomy within structure."
    )

    # ── Wealth timing from dashas ─────────────────────────────────

    wealth_planets = {tenth_lord, d10_tenth_lord, amatyakaraka, "Jupiter", "Venus"}
    wealth_timing  = []
    for period in dashas.get("vimsottari", [])[:12]:
        planet = period.get("lord_or_sign", "")
        if planet in wealth_planets:
            wealth_timing.append({
                "planet": planet,
                "start":  period.get("start", ""),
                "end":    period.get("end", ""),
                "reason": f"{planet} is your {_get_planet_role(planet, tenth_lord, d10_tenth_lord, atmakaraka, amatyakaraka)}",
                "wealth_type": PLANET_CAREER_DOMAINS.get(planet, {}).get("wealth_type", ""),
            })
    analysis.wealth_timing = wealth_timing[:4]

    if wealth_timing:
        analysis.peak_earning_period = (
            f"{wealth_timing[0]['planet']} period "
            f"({wealth_timing[0]['start'][:7]} to {wealth_timing[0]['end'][:7]})"
        )

    # ── Funding / Investment timing (for entrepreneurs) ──────────

    funding_planets = {"Jupiter", "Rahu", "Venus", tenth_lord, d10_tenth_lord}
    funding_indicators = []
    for period in dashas.get("vimsottari", [])[:10]:
        planet = period.get("lord_or_sign", "")
        if planet in {"Jupiter", "Rahu"} or planet == tenth_lord:
            funding_indicators.append({
                "planet":   planet,
                "start":    period.get("start", ""),
                "end":      period.get("end", ""),
                "strength": "Strong" if planet in {"Jupiter", "Rahu"} else "Moderate",
                "reason":   (
                    "Jupiter dasha brings institutional support and trust" if planet == "Jupiter" else
                    "Rahu dasha brings sudden windfalls and foreign investment" if planet == "Rahu" else
                    f"{planet} dasha activates your career house"
                ),
            })
    analysis.funding_indicators = funding_indicators[:3]
    if funding_indicators:
        f = funding_indicators[0]
        analysis.funding_timing = (
            f"Strongest funding window: {f['planet']} period "
            f"({f['start'][:7]} to {f['end'][:7]}) — {f['reason']}"
        )

    # ── Current career phase ──────────────────────────────────────

    current_dasha = dashas.get("vimsottari", [{}])[0]
    current_planet = current_dasha.get("lord_or_sign", "")
    analysis.career_peak_dasha = analysis.peak_earning_period
    analysis.current_career_phase = _get_current_career_phase(
        current_planet, tenth_lord, d10_tenth_lord, atmakaraka
    )

    return analysis


def career_analysis_to_context_block(analysis: CareerAnalysis) -> str:
    """
    Convert CareerAnalysis to LLM context block.
    Inject into prompt_builder for career-related questions.
    """
    funding_text = ""
    if analysis.funding_indicators:
        funding_text = "\nFUNDING / INVESTMENT WINDOWS:\n"
        for f in analysis.funding_indicators:
            funding_text += (
                f"  {f['planet']} period ({f['start'][:7]}–{f['end'][:7]}): "
                f"{f['strength']} — {f['reason']}\n"
            )

    wealth_text = ""
    if analysis.wealth_timing:
        wealth_text = "\nWEALTH PEAK PERIODS:\n"
        for w in analysis.wealth_timing[:3]:
            wealth_text += f"  {w['planet']} ({w['start'][:7]}–{w['end'][:7]}): {w['reason']}\n"

    return f"""
═══ CAREER & WEALTH ANALYSIS (D-1 / D-9 / D-10 / D-2) ═══

D-1 Career indicators:
  10th house: {analysis.d1_10th_sign} — lord: {analysis.d1_10th_lord}
  Theme: {analysis.d1_career_theme}

D-10 (Career chart):
  10th lord: {analysis.d10_10th_lord}
  Theme: {analysis.d10_career_theme}
  Strong planets in D-10 career house: {', '.join(analysis.d10_strong_planets) or 'None'}

D-9 Soul purpose:
  Atmakaraka: {analysis.atmakaraka} — {analysis.ak_career}
  Amatyakaraka: {analysis.amatyakaraka} — {analysis.amk_career}

D-2 Wealth:
  Wealth lord: {analysis.d2_wealth_lord}
  Wealth type: {analysis.d2_wealth_type}

BEST CAREER FIELDS (ranked by chart strength):
  Primary:   {', '.join(analysis.primary_fields)}
  Secondary: {', '.join(analysis.secondary_fields)}

WORK STYLE: {analysis.work_style}

ENTREPRENEURSHIP vs EMPLOYMENT:
  Score: Entrepreneur {analysis.entrepreneur_score:.1f} | Employment {analysis.employment_score:.1f}
  Recommendation: {analysis.recommendation}

CURRENT CAREER PHASE: {analysis.current_career_phase}
{wealth_text}
PEAK EARNING PERIOD: {analysis.peak_earning_period}
{funding_text}
═══ END CAREER ANALYSIS ═══

INSTRUCTION: Use this data to give a specific, personal career reading.
Translate ALL technical data into energy language.
Never say "your D-10 10th lord" — say "your professional destiny chart points to..."
Never say "Amatyakaraka Jupiter" — say "your career's highest expression comes through wisdom and expansion..."
Always include concrete career fields AND the timing of when they peak.
"""


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_atmakaraka(planets: dict) -> str:
    """Planet with highest degree in any sign = Atmakaraka."""
    highest_deg = -1
    atmakaraka  = "Sun"
    for planet, data in planets.items():
        if planet in ("Rahu", "Ketu"):
            continue
        deg = data.get("degree", 0)
        if deg > highest_deg:
            highest_deg = deg
            atmakaraka  = planet
    return atmakaraka


def _get_amatyakaraka(planets: dict) -> str:
    """Planet with second highest degree = Amatyakaraka (career significator)."""
    degrees = []
    for planet, data in planets.items():
        if planet in ("Rahu", "Ketu"):
            continue
        degrees.append((planet, data.get("degree", 0)))
    degrees.sort(key=lambda x: x[1], reverse=True)
    return degrees[1][0] if len(degrees) > 1 else "Jupiter"


def _get_planet_role(planet, tenth_lord, d10_lord, atmakaraka, amatyakaraka) -> str:
    roles = []
    if planet == tenth_lord:    roles.append("D-1 career lord")
    if planet == d10_lord:      roles.append("D-10 career lord")
    if planet == atmakaraka:    roles.append("Atmakaraka")
    if planet == amatyakaraka:  roles.append("Amatyakaraka")
    if planet == "Jupiter":     roles.append("natural wealth karaka")
    return " + ".join(roles) if roles else "wealth-connected planet"


def _get_current_career_phase(current_planet, tenth_lord, d10_lord, atmakaraka) -> str:
    if current_planet in (tenth_lord, d10_lord):
        return (
            f"PEAK — You are in your career's most activated dasha ({current_planet}). "
            f"This is a window to push hard professionally."
        )
    if current_planet == atmakaraka:
        return (
            f"SOUL ALIGNMENT — Your {current_planet} dasha is connecting career "
            f"to soul purpose. Work that feels meaningful is most rewarded now."
        )
    if current_planet in ("Jupiter", "Venus"):
        return (
            f"EXPANSION — {current_planet} dasha brings growth, opportunity, "
            f"and favorable professional conditions."
        )
    if current_planet == "Saturn":
        return (
            f"FOUNDATION — Saturn dasha rewards discipline and mastery. "
            f"Slow but permanent career growth. Build systems, not just wins."
        )
    if current_planet == "Rahu":
        return (
            f"AMBITION — Rahu dasha brings rapid, unconventional career rises. "
            f"Foreign connections and disruption create opportunity."
        )
    if current_planet == "Ketu":
        return (
            f"CONSOLIDATION — Ketu dasha asks you to deepen expertise. "
            f"Past skills resurface. External ambition reduces."
        )
    return f"ACTIVE — {current_planet} dasha shapes professional life in specific ways."
