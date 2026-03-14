"""
antar_engine/divisional_analysis_engines.py

Interpretation engines for D16, D20, D24, D27, D30, D60.
Each engine:
  1. Reads the divisional chart planets
  2. Applies specific rules for that chart's domain
  3. Cross-references with D1 for confirmation
  4. Returns scored verdicts for LLM context

Rules sourced from classical texts:
  D24 — Chaturvimsamsa: education, learning, Saraswati
  D30 — Trimsamsa: misfortune, illness, evil, problems
  D16 — Shodashamsa: vehicles, comforts, happiness
  D20 — Vimshamsa: spiritual progress, mantra siddhi
  D27 — Bhamsa: physical strength, stamina, vitality
  D60 — Shashtiamsa: past life karma (handled in divisional_charts.py)
"""

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]
SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}
EXALTATION = {
    "Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
    "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra"
}
DEBILITATION = {
    "Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
    "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries"
}
BENEFICS = ["Jupiter","Venus","Moon","Mercury"]
MALEFICS  = ["Saturn","Mars","Sun","Rahu","Ketu"]
KENDRA    = [1, 4, 7, 10]
TRIKONA   = [1, 5, 9]
DUSTHANA  = [6, 8, 12]


def _h(p, planets): return planets.get(p, {}).get("house", 0)
def _s(p, planets): return planets.get(p, {}).get("sign", "")
def _is_exalted(p, planets): return _s(p,planets) == EXALTATION.get(p,"")
def _is_debilitated(p, planets): return _s(p,planets) == DEBILITATION.get(p,"")


# ══════════════════════════════════════════════════════════════
# D24 — CHATURVIMSAMSA (Education & Learning)
# ══════════════════════════════════════════════════════════════

D24_RULES = {
    # Mercury strong = intellectual excellence
    # Jupiter strong = wisdom and higher learning
    # 4th house (foundation education) + 5th house (intelligence) + 9th (higher)
    # Saraswati yoga: Mercury + Jupiter + Venus in kendra/trikona = genius
}

def analyze_d24_education(d24: dict, d1_planets: dict) -> dict:
    """
    D24 Chaturvimsamsa — education, academic achievement, learning capacity.

    Key rules:
    - Mercury in 1/4/5/9/10 = sharp intellect, academic excellence
    - Jupiter in 1/4/5/9 = wisdom, higher education, philosophical depth
    - 5th house strong = intelligence peak
    - 9th house strong = higher education, foreign study
    - Saraswati Yoga = Mercury+Jupiter+Venus all in kendra/trikona
    - Malefics in 4th = education interrupted
    - Saturn in 5th = slow but deep learner
    - Rahu in 5th = unconventional education, technology fields
    """
    if not d24 or not d24.get("planets"):
        return {}

    planets = d24.get("planets", {})
    lagna   = d24.get("lagna", "")

    merc_h = _h("Mercury", planets)
    jup_h  = _h("Jupiter", planets)
    sun_h  = _h("Sun", planets)
    sat_h  = _h("Saturn", planets)
    rahu_h = _h("Rahu", planets)
    ven_h  = _h("Venus", planets)
    moon_h = _h("Moon", planets)

    indicators  = []
    challenges  = []
    score       = 40  # base

    # Mercury analysis
    if merc_h in KENDRA + TRIKONA:
        indicators.append(f"Mercury in D24 house {merc_h} — sharp analytical mind, academic excellence natural")
        score += 20
    if _is_exalted("Mercury", planets):
        indicators.append("Mercury exalted in D24 — extraordinary intellectual capacity, potential for mastery")
        score += 15
    if merc_h in DUSTHANA:
        challenges.append(f"Mercury in D24 house {merc_h} — learning has obstacles, alternative paths to knowledge")
        score -= 10

    # Jupiter analysis
    if jup_h in [1, 4, 5, 9]:
        indicators.append(f"Jupiter in D24 house {jup_h} — blessed with wisdom, higher education flows naturally")
        score += 20
    if _is_exalted("Jupiter", planets):
        indicators.append("Jupiter exalted in D24 (Cancer) — exceptional wisdom, teaching ability, philosophical genius")
        score += 20
    if _is_debilitated("Jupiter", planets):
        challenges.append("Jupiter debilitated in D24 — wisdom comes through unconventional paths, not traditional academia")
        score -= 10

    # Saraswati Yoga in D24
    if (merc_h in KENDRA + TRIKONA and
        jup_h in KENDRA + TRIKONA and
        ven_h in KENDRA + TRIKONA):
        indicators.append("SARASWATI YOGA in D24 — Mercury+Jupiter+Venus all in good houses — exceptional learning, arts, and wisdom")
        score += 25

    # 5th house (intelligence)
    planets_in_5 = [p for p,d in planets.items() if d.get("house")==5]
    if "Jupiter" in planets_in_5 or "Mercury" in planets_in_5:
        indicators.append(f"Benefic in D24 5th house — intelligence and creativity peak")
        score += 10
    if sat_h == 5:
        challenges.append("Saturn in D24 5th — slow and methodical learner, depth over speed, late bloomer academically")
    if rahu_h == 5:
        indicators.append("Rahu in D24 5th — unconventional education, technology, foreign learning")

    # 9th house (higher education)
    planets_in_9 = [p for p,d in planets.items() if d.get("house")==9]
    if "Jupiter" in planets_in_9:
        indicators.append("Jupiter in D24 9th — higher education, possible PhD/research, foreign study possible")
        score += 15

    # Cross-reference D1
    d1_merc_house = d1_planets.get("Mercury",{}).get("house",0)
    d1_jup_house  = d1_planets.get("Jupiter",{}).get("house",0)
    if d1_merc_house in KENDRA and merc_h in KENDRA:
        indicators.append("Mercury strong in BOTH D1 and D24 — confirmed exceptional intellect")
        score += 10

    score = min(95, max(20, score))

    # Determine education type
    edu_type = []
    if merc_h in [1,3,5,10]: edu_type.append("technical/analytical fields")
    if jup_h in [1,9,12]:    edu_type.append("philosophy/law/spirituality")
    if rahu_h in [1,5,9]:    edu_type.append("technology/foreign education")
    if ven_h in [1,5]:       edu_type.append("arts/creative fields")
    if sun_h in [1,9,10]:    edu_type.append("government/authority fields")

    return {
        "score":          score,
        "verdict":        ("Exceptional academic potential — education is a core strength" if score >= 75
                          else "Good education — consistent effort yields strong results" if score >= 50
                          else "Education through non-traditional paths — life experience matters more"),
        "indicators":     indicators,
        "challenges":     challenges,
        "education_type": edu_type,
        "foreign_study":  rahu_h in [5,9,12] or jup_h == 9,
        "saraswati_yoga": (merc_h in KENDRA+TRIKONA and jup_h in KENDRA+TRIKONA and ven_h in KENDRA+TRIKONA),
        "lagna":          lagna,
    }


# ══════════════════════════════════════════════════════════════
# D30 — TRIMSAMSA (Misfortune & Problems)
# ══════════════════════════════════════════════════════════════

D30_MALEFIC_SIGNS = {
    "Aries":      {"lord":"Mars", "nature":"accidents, fire, aggression"},
    "Aquarius":   {"lord":"Saturn", "nature":"chronic problems, delays, depression"},
    "Scorpio":    {"lord":"Mars", "nature":"hidden enemies, surgery, transformation"},
    "Capricorn":  {"lord":"Saturn", "nature":"cold, isolation, chronic illness"},
    "Virgo":      {"lord":"Mercury", "nature":"nervous problems, digestive, criticism"},
    "Cancer":     {"lord":"Moon", "nature":"emotional problems, family issues"},
}

D30_BENEFIC_SIGNS = {
    "Taurus":     "stability, material support even in problems",
    "Gemini":     "communication helps resolve problems",
    "Leo":        "authority and pride preserve dignity",
    "Libra":      "balance and justice in adverse times",
    "Sagittarius":"dharma and wisdom protect",
    "Pisces":     "spiritual grace, problems dissolve",
}

def analyze_d30_misfortune(d30: dict, d1_planets: dict, current_md_lord: str = "") -> dict:
    """
    D30 Trimsamsa — misfortune, illness, evil, moral failings.

    Classical rules:
    - Planet in malefic D30 sign = that planet brings specific misfortune during its dasha
    - Lagna lord in malefic D30 sign = general misfortune tendency
    - Benefics in D30 = protect against worst outcomes
    - Lagna in benefic sign = generally protected
    - Malefics in 6/8/12 of D30 = serious problems
    - Jupiter in D30 = divine protection
    - Active MD lord's D30 position = current risk
    """
    if not d30 or not d30.get("planets"):
        return {}

    planets  = d30.get("planets", {})
    lagna    = d30.get("lagna", "")
    lagna_lord = SIGN_LORDS.get(lagna, "")

    warnings     = []
    protections  = []
    active_risks = []
    score_risk   = 0

    # Check each planet's D30 sign
    for planet, data in planets.items():
        sign = data.get("sign", "")
        house= data.get("house", 0)

        if sign in D30_MALEFIC_SIGNS:
            nature = D30_MALEFIC_SIGNS[sign]["nature"]
            warnings.append({
                "planet":     planet,
                "d30_sign":   sign,
                "nature":     nature,
                "when_active": f"During {planet} Mahadasha or Antardasha",
                "severity":   "high" if planet in MALEFICS else "moderate",
            })
            score_risk += 15 if planet in MALEFICS else 8

        elif sign in D30_BENEFIC_SIGNS:
            protections.append(f"{planet} in {sign} — {D30_BENEFIC_SIGNS[sign]}")

        # Malefic in dusthana of D30 = amplified problems
        if planet in MALEFICS and house in DUSTHANA:
            warnings.append({
                "planet":     planet,
                "d30_sign":   sign,
                "nature":     f"{planet} in D30 house {house} — amplified difficulty during its dasha",
                "when_active": f"During {planet} Mahadasha or Antardasha",
                "severity":   "high",
            })
            score_risk += 20

    # Lagna lord in D30
    lagna_lord_sign = _s(lagna_lord, planets) if lagna_lord else ""
    if lagna_lord_sign in D30_MALEFIC_SIGNS:
        warnings.append({
            "planet":     lagna_lord,
            "d30_sign":   lagna_lord_sign,
            "nature":     f"Lagna lord in malefic D30 — general misfortune tendency in life",
            "when_active": f"Especially during {lagna_lord} period",
            "severity":   "high",
        })
        score_risk += 25

    # Jupiter as protector
    jup_h = _h("Jupiter", planets)
    if jup_h in KENDRA + TRIKONA:
        protections.append(f"Jupiter in D30 house {jup_h} — divine protection, extreme misfortune averted")
        score_risk -= 20

    # Current MD lord active risk
    if current_md_lord:
        md_sign = _s(current_md_lord, planets)
        if md_sign in D30_MALEFIC_SIGNS:
            active_risks.append({
                "planet":  current_md_lord,
                "nature":  D30_MALEFIC_SIGNS[md_sign]["nature"],
                "urgency": "ACTIVE NOW — apply remedy immediately",
            })

    # Lagna protection
    if lagna in D30_BENEFIC_SIGNS:
        protections.append(f"D30 lagna in {lagna} — {D30_BENEFIC_SIGNS[lagna]}")
        score_risk -= 15

    score_risk = min(90, max(5, score_risk))

    return {
        "risk_score":   score_risk,
        "verdict":      ("High misfortune indicators — active remedies essential" if score_risk >= 60
                        else "Moderate risk — some planetary periods bring challenges" if score_risk >= 35
                        else "Generally protected — misfortune is manageable"),
        "warnings":     sorted(warnings, key=lambda x: 0 if x["severity"]=="high" else 1),
        "protections":  protections,
        "active_risks": active_risks,
        "lagna":        lagna,
        "instruction":  "D30 planets in malefic signs = their dasha periods bring specific problems. Apply that planet's remedy proactively.",
    }


# ══════════════════════════════════════════════════════════════
# D16 — SHODASHAMSA (Vehicles & Happiness)
# ══════════════════════════════════════════════════════════════

def analyze_d16_vehicles(d16: dict, d1_planets: dict) -> dict:
    """
    D16 Shodashamsa — vehicles, comforts, happiness, pleasure.

    Rules:
    - Venus strong = luxury vehicles, material comfort
    - 4th house strong = property + vehicles
    - Moon strong = happiness and emotional comfort
    - Saturn in 4th/7th = vehicle troubles, delayed comfort
    - Mars in 4/8 = vehicle accidents
    - Jupiter in kendra = protected, comfortable life
    - Rahu in 4th = foreign vehicle, frequent changes
    """
    if not d16 or not d16.get("planets"):
        return {}

    planets = d16.get("planets", {})
    lagna   = d16.get("lagna", "")

    ven_h  = _h("Venus", planets)
    moon_h = _h("Moon", planets)
    sat_h  = _h("Saturn", planets)
    mars_h = _h("Mars", planets)
    jup_h  = _h("Jupiter", planets)
    rahu_h = _h("Rahu", planets)

    indicators  = []
    challenges  = []
    score       = 40

    if ven_h in KENDRA + TRIKONA:
        indicators.append(f"Venus in D16 house {ven_h} — luxury vehicles, material comfort flows naturally")
        score += 20
    if _is_exalted("Venus", planets):
        indicators.append("Venus exalted in D16 — exceptional material comfort, luxury vehicles confirmed")
        score += 20

    if moon_h in [1, 4, 10, 11]:
        indicators.append(f"Moon in D16 house {moon_h} — emotional happiness and domestic comfort")
        score += 15

    if jup_h in KENDRA:
        indicators.append(f"Jupiter in D16 house {jup_h} — divine protection, comfortable life, vehicles preserved")
        score += 15

    if rahu_h == 4:
        indicators.append("Rahu in D16 4th — foreign vehicle, unconventional comfort, frequent upgrades")
        score += 5

    if sat_h in [4, 7]:
        challenges.append(f"Saturn in D16 house {sat_h} — vehicles come late, maintenance issues, delayed comfort")
        score -= 15

    if mars_h in [4, 8]:
        challenges.append(f"Mars in D16 house {mars_h} — vehicle accident risk, apply Mars remedy before major journeys")
        score -= 10

    # D1 cross-reference
    d1_ven_h = d1_planets.get("Venus",{}).get("house",0)
    if d1_ven_h in [4,11] and ven_h in KENDRA:
        indicators.append("Venus strong in both D1 and D16 — confirmed luxury vehicle and comfort destiny")
        score += 10

    score = min(90, max(15, score))

    return {
        "score":       score,
        "verdict":     ("Excellent vehicle and comfort yoga — luxury is natural" if score >= 70
                       else "Good material comfort — vehicles and conveniences come" if score >= 50
                       else "Comfort comes with effort — vehicles may have challenges"),
        "indicators":  indicators,
        "challenges":  challenges,
        "vehicle_type": ("luxury/foreign" if ven_h in [1,4,11] and _is_exalted("Venus",planets)
                        else "comfortable/standard" if ven_h in KENDRA+TRIKONA
                        else "practical/delayed"),
        "lagna":       lagna,
    }


# ══════════════════════════════════════════════════════════════
# D20 — VIMSHAMSA (Spirituality & Mantra Siddhi)
# ══════════════════════════════════════════════════════════════

def analyze_d20_spirituality(d20: dict, d1_planets: dict) -> dict:
    """
    D20 Vimshamsa — spiritual progress, mantra siddhi, religious merit.

    Rules:
    - Jupiter strong = spiritual wisdom, teacher quality
    - Ketu strong = past life spiritual practice, easy siddhi
    - 9th house (dharma) + 12th house (moksha) + 8th house (occult)
    - Moon strong = devotion, bhakti path
    - Saturn in good position = karma yoga
    - Sun strong = jnana yoga path
    - Malefics in 9th/12th = spiritual obstacles
    - Benefics in 9th/12th = spiritual merit
    """
    if not d20 or not d20.get("planets"):
        return {}

    planets = d20.get("planets", {})
    lagna   = d20.get("lagna", "")

    jup_h  = _h("Jupiter", planets)
    ketu_h = _h("Ketu", planets)
    moon_h = _h("Moon", planets)
    sat_h  = _h("Saturn", planets)
    sun_h  = _h("Sun", planets)
    ven_h  = _h("Venus", planets)
    mars_h = _h("Mars", planets)

    paths      = []
    indicators = []
    challenges = []
    score      = 30

    # Jupiter — wisdom path
    if jup_h in KENDRA + TRIKONA:
        indicators.append(f"Jupiter in D20 house {jup_h} — spiritual wisdom flows naturally, teacher/guru energy")
        score += 20
        paths.append("Jnana/Guru yoga")

    # Ketu — liberation path
    if ketu_h in [1, 4, 9, 12]:
        indicators.append(f"Ketu in D20 house {ketu_h} — strong past life spiritual merit, liberation accessible")
        score += 20
        paths.append("Moksha/Ketu path")

    # Moon — devotion
    if moon_h in [1, 4, 9]:
        indicators.append(f"Moon in D20 house {moon_h} — deep devotion, bhakti yoga is natural path")
        score += 15
        paths.append("Bhakti yoga")

    # Saturn — karma yoga
    if sat_h in [9, 10, 12]:
        indicators.append(f"Saturn in D20 house {sat_h} — karma yoga, spiritual growth through disciplined service")
        score += 15
        paths.append("Karma yoga")

    # Sun — self-realization
    if sun_h in [1, 9]:
        indicators.append(f"Sun in D20 house {sun_h} — self-realization path, strong spiritual identity")
        score += 15
        paths.append("Raja yoga/self-inquiry")

    # Venus — mantra/tantra
    if ven_h in [1, 9, 12]:
        indicators.append(f"Venus in D20 house {ven_h} — mantra siddhi, devotional arts, tantric path")
        score += 10
        paths.append("Mantra/devotional arts")

    # Malefics in spiritual houses
    if mars_h in [9, 12]:
        challenges.append(f"Mars in D20 house {mars_h} — spiritual practice disturbed by ego/aggression")
        score -= 10

    # Strong spiritual combination
    if jup_h in [1,9] and ketu_h in [1,9,12]:
        indicators.append("STRONG MOKSHA YOGA in D20 — Jupiter + Ketu in spiritual houses — liberation is the life purpose")
        score += 15

    # D1 cross-reference
    d1_ketu_h = d1_planets.get("Ketu",{}).get("house",0)
    if d1_ketu_h in [9,12] and ketu_h in [1,9,12]:
        indicators.append("Ketu strong in both D1 and D20 — confirmed spiritual path, past life practice")
        score += 10

    score = min(92, max(15, score))

    return {
        "score":      score,
        "verdict":    ("Strong spiritual destiny — this chart carries moksha potential" if score >= 65
                      else "Spiritual interests present — practice deepens this life" if score >= 40
                      else "Worldly orientation — spirituality comes in later life"),
        "indicators": indicators,
        "challenges": challenges,
        "paths":      list(set(paths)),
        "lagna":      lagna,
    }


# ══════════════════════════════════════════════════════════════
# D27 — BHAMSA (Physical Strength & Vitality)
# ══════════════════════════════════════════════════════════════

def analyze_d27_strength(d27: dict, d1_planets: dict, birth_date: str = "") -> dict:
    """
    D27 Bhamsa/Nakshatramsa — physical strength, stamina, vitality, sports.

    Rules:
    - Mars strong = physical strength, sports, courage
    - Sun strong = vital force, constitution
    - Saturn in bad position = chronic weakness
    - Moon strong = mental stamina, resilience
    - 1st house strong = overall physical power
    - 6th house (service/health) condition
    - Malefics in 1st = physical challenges
    - Exalted Mars = exceptional physical power
    """
    if not d27 or not d27.get("planets"):
        return {}

    planets = d27.get("planets", {})
    lagna   = d27.get("lagna", "")

    mars_h = _h("Mars", planets)
    sun_h  = _h("Sun", planets)
    moon_h = _h("Moon", planets)
    sat_h  = _h("Saturn", planets)
    jup_h  = _h("Jupiter", planets)
    rahu_h = _h("Rahu", planets)

    indicators = []
    challenges = []
    score      = 40

    # Mars — physical power
    if mars_h in KENDRA + TRIKONA:
        indicators.append(f"Mars in D27 house {mars_h} — strong physical constitution, athletic ability")
        score += 20
    if _is_exalted("Mars", planets):
        indicators.append("Mars exalted in D27 — exceptional physical strength, sports/military excellence")
        score += 25

    # Sun — vitality
    if sun_h in [1, 9, 10]:
        indicators.append(f"Sun in D27 house {sun_h} — strong vital force, good immunity, leadership stamina")
        score += 15
    if _is_exalted("Sun", planets):
        indicators.append("Sun exalted in D27 — exceptional vitality, strong constitution throughout life")
        score += 15

    # Moon — resilience
    if moon_h in [1, 4, 10, 11]:
        indicators.append(f"Moon in D27 house {moon_h} — mental resilience, emotional stamina")
        score += 10

    # Jupiter — protection
    if jup_h in KENDRA:
        indicators.append(f"Jupiter in D27 house {jup_h} — divine protection of health and strength")
        score += 10

    # Challenges
    if sat_h in [1, 6, 8]:
        challenges.append(f"Saturn in D27 house {sat_h} — chronic weakness tendency, cold/bone vulnerability")
        score -= 15
    if rahu_h in [1, 6, 8]:
        challenges.append(f"Rahu in D27 house {rahu_h} — unusual health issues, neurological sensitivity")
        score -= 10
    if _is_debilitated("Mars", planets):
        challenges.append("Mars debilitated in D27 — physical strength inconsistent, immune system needs care")
        score -= 15
    if _is_debilitated("Sun", planets):
        challenges.append("Sun debilitated in D27 — vitality fluctuates, heart and constitution need attention")
        score -= 10

    # D1 cross-reference
    d1_mars_h = d1_planets.get("Mars",{}).get("house",0)
    if d1_mars_h in KENDRA and mars_h in KENDRA:
        indicators.append("Mars strong in both D1 and D27 — confirmed exceptional physical power")
        score += 10

    score = min(92, max(15, score))

    return {
        "score":       score,
        "verdict":     ("Exceptional physical strength — sports, military, physical excellence" if score >= 75
                       else "Good physical constitution — health maintained with normal care" if score >= 50
                       else "Physical vulnerability — proactive health management important"),
        "indicators":  indicators,
        "challenges":  challenges,
        "sports_yoga": mars_h in KENDRA and _is_exalted("Mars", planets),
        "vitality_level": ("high" if score >= 70 else "moderate" if score >= 50 else "needs_attention"),
        "lagna":       lagna,
    }


# ══════════════════════════════════════════════════════════════
# D60 INTERPRETATION (builds on divisional_charts.py data)
# ══════════════════════════════════════════════════════════════

def analyze_d60_karma(d60: dict, d1_planets: dict, current_md_lord: str = "") -> dict:
    """
    D60 Shashtiamsa — past life karma cross-reference with D1.

    Key insight: D60 explains WHY D1 patterns repeat.
    Planet in challenging D60 karma = that planet's D1 themes
    carry karmic debt from past lives.
    """
    if not d60:
        return {}

    planet_analysis = d60.get("planet_analysis", {})
    positive_karma  = d60.get("positive_karma", [])
    challenging_karma = d60.get("challenging_karma", [])

    # Cross-reference with D1 house positions
    karma_explanations = []
    active_karma       = []

    for planet, d60_data in planet_analysis.items():
        d1_house = d1_planets.get(planet, {}).get("house", 0)
        karma_name = d60_data.get("karma_name","")
        karma_desc = d60_data.get("karma_desc","")
        is_challenging = d60_data.get("is_challenging", False)
        is_positive    = d60_data.get("is_positive", False)

        if d1_house and is_challenging:
            karma_explanations.append({
                "planet":      planet,
                "d1_house":    d1_house,
                "karma":       karma_name,
                "explanation": f"{planet} in D1 house {d1_house} carries {karma_name} karma — "
                               f"recurring challenges in {_house_meaning(d1_house)} are karmic debts being resolved",
                "remedy":      f"Serve {planet}'s natural significations. Apply its Lal Kitab remedy actively.",
            })

        if planet == current_md_lord:
            active_karma.append({
                "planet":  planet,
                "karma":   karma_name,
                "nature":  karma_desc,
                "urgency": "ACTIVE — this planet's karma is being processed RIGHT NOW in its dasha",
            })

    return {
        "positive_karma":       positive_karma[:3],
        "challenging_karma":    challenging_karma[:3],
        "karma_explanations":   karma_explanations[:4],
        "active_karma":         active_karma,
        "lagna_karma":          d60.get("lagna_karma", ("","")),
        "instruction":          "D60 reveals WHY patterns repeat. Reference it when user asks about recurring themes or why something keeps happening.",
    }


def _house_meaning(house: int) -> str:
    meanings = {
        1:"self/identity", 2:"wealth/family", 3:"courage/siblings",
        4:"home/mother", 5:"children/intelligence", 6:"health/enemies",
        7:"marriage/partnerships", 8:"transformation/longevity",
        9:"dharma/fortune", 10:"career/authority", 11:"gains/income",
        12:"spirituality/losses",
    }
    return meanings.get(house, f"house {house} themes")


# ══════════════════════════════════════════════════════════════
# MASTER RUNNER — all divisional analyses
# ══════════════════════════════════════════════════════════════

def run_divisional_analyses(
    chart_data: dict,
    current_md_lord: str = "",
    birth_date: str = "",
) -> dict:
    """
    Run all divisional chart analysis engines.
    Returns complete verdicts for LLM context.
    """
    planets  = chart_data.get("planets", {})
    divs     = chart_data.get("divisional_charts", {})

    results = {
        "d24_education":   analyze_d24_education(divs.get("d24",{}), planets),
        "d30_misfortune":  analyze_d30_misfortune(divs.get("d30",{}), planets, current_md_lord),
        "d16_vehicles":    analyze_d16_vehicles(divs.get("d16",{}), planets),
        "d20_spirituality":analyze_d20_spirituality(divs.get("d20",{}), planets),
        "d27_strength":    analyze_d27_strength(divs.get("d27",{}), planets, birth_date),
        "d60_karma":       analyze_d60_karma(divs.get("d60",{}), planets, current_md_lord),
    }

    return results


def build_divisional_context_block(analyses: dict, concern: str = "general") -> str:
    """
    Build context block for LLM — all divisional chart verdicts.
    Focus on concern-relevant charts first.
    """
    if not analyses:
        return ""

    # Map concerns to relevant charts
    CONCERN_PRIORITY = {
        "education":    ["d24_education"],
        "study":        ["d24_education"],
        "vehicle":      ["d16_vehicles"],
        "car":          ["d16_vehicles"],
        "spiritual":    ["d20_spirituality", "d60_karma"],
        "moksha":       ["d20_spirituality", "d60_karma"],
        "health":       ["d27_strength", "d30_misfortune"],
        "strength":     ["d27_strength"],
        "problem":      ["d30_misfortune", "d60_karma"],
        "why":          ["d60_karma"],
        "karma":        ["d60_karma"],
        "pattern":      ["d60_karma"],
        "misfortune":   ["d30_misfortune"],
    }

    concern_lower   = concern.lower()
    priority_charts = []
    for kw, charts in CONCERN_PRIORITY.items():
        if kw in concern_lower:
            priority_charts.extend(charts)

    lines = [
        "═══════════════════════════════════════════════════════",
        "DIVISIONAL CHART ANALYSIS (D16/D20/D24/D27/D30/D60)",
        "═══════════════════════════════════════════════════════",
    ]

    CHART_LABELS = {
        "d24_education":    "D24 EDUCATION & LEARNING",
        "d30_misfortune":   "D30 MISFORTUNE & PROBLEMS",
        "d16_vehicles":     "D16 VEHICLES & COMFORT",
        "d20_spirituality": "D20 SPIRITUAL PROGRESS",
        "d27_strength":     "D27 PHYSICAL STRENGTH",
        "d60_karma":        "D60 PAST LIFE KARMA",
    }

    # Sort — priority charts first
    chart_order = priority_charts + [c for c in analyses.keys() if c not in priority_charts]

    for chart_key in chart_order:
        data = analyses.get(chart_key, {})
        if not data:
            continue

        label = CHART_LABELS.get(chart_key, chart_key.upper())
        lines.append(f"\n{label}:")

        if chart_key == "d60_karma":
            if data.get("positive_karma"):
                lines.append("  Positive karma (gifts from past lives):")
                for pk in data["positive_karma"][:2]:
                    lines.append(f"    ✓ {pk}")
            if data.get("challenging_karma"):
                lines.append("  Challenging karma (debts being resolved):")
                for ck in data["challenging_karma"][:2]:
                    lines.append(f"    ⚠ {ck}")
            if data.get("karma_explanations"):
                lines.append("  Cross-reference with D1:")
                for ke in data["karma_explanations"][:2]:
                    lines.append(f"    → {ke['explanation']}")
            if data.get("active_karma"):
                for ak in data["active_karma"]:
                    lines.append(f"  ⭐ ACTIVE NOW: {ak['urgency']}")
                    lines.append(f"     {ak['planet']} karma ({ak['karma']}): {ak['nature']}")
            continue

        # Standard charts
        score_key = next((k for k in ["score","risk_score"] if k in data), None)
        if score_key:
            lines.append(f"  Score: {data[score_key]}/100")
        if data.get("verdict"):
            lines.append(f"  Verdict: {data['verdict']}")

        ind_key = next((k for k in ["indicators","warnings","protections"] if data.get(k)), None)
        if ind_key:
            items = data[ind_key]
            for item in (items[:3] if isinstance(items[0],str) else [i.get("nature","") or i.get("planet","") for i in items[:3]]):
                prefix = "✓" if ind_key in ["indicators","protections"] else "⚠"
                lines.append(f"  {prefix} {item}")

        warn_key = next((k for k in ["challenges","warnings"] if k!=ind_key and data.get(k)), None)
        if warn_key:
            items = data[warn_key]
            for item in (items[:2] if isinstance(items[0],str) else [i.get("nature","") or i.get("planet","") for i in items[:2]]):
                lines.append(f"  ⚠ {item}")

        # Special fields
        if chart_key == "d24_education" and data.get("education_type"):
            lines.append(f"  Best fields: {', '.join(data['education_type'][:3])}")
            if data.get("saraswati_yoga"):
                lines.append(f"  ⭐ SARASWATI YOGA detected in D24")
        if chart_key == "d20_spirituality" and data.get("paths"):
            lines.append(f"  Spiritual path: {' + '.join(data['paths'][:2])}")
        if chart_key == "d27_strength":
            lines.append(f"  Vitality level: {data.get('vitality_level','').upper()}")
            if data.get("sports_yoga"):
                lines.append(f"  ⭐ SPORTS/MARTIAL YOGA in D27")
        if chart_key == "d16_vehicles":
            lines.append(f"  Vehicle type: {data.get('vehicle_type','')}")
        if chart_key == "d30_misfortune" and data.get("active_risks"):
            for ar in data["active_risks"]:
                lines.append(f"  🔴 ACTIVE RISK: {ar['nature']} — {ar['urgency']}")

    lines += [
        "",
        "DIVISIONAL CHART RULES FOR LLM:",
        "  D24: Confirms or denies D1 education indicators. Saraswati yoga = genius level.",
        "  D30: Active malefic planet = expect problems in its domain during its dasha.",
        "  D16: Venus strength here confirms vehicle/comfort destiny.",
        "  D20: Ketu+Jupiter in spiritual houses = moksha accessible this life.",
        "  D27: Mars strength here confirms physical power and sports ability.",
        "  D60: ALWAYS reference when user asks WHY something keeps happening.",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)
