"""
antar_engine/prashna_engine.py

Prashna (Horary) Astrology Engine
===================================
Cast a chart for the EXACT moment a question is asked.
No birth data needed. The question chart reveals the answer.

Classical Prashna rules (K.N. Rao + Krishnamurti + traditional):
  1. Lagna of question moment = strength of the question
  2. Significator house for the question type
  3. Moon = mind, emotional state, what's really being asked
  4. Benefic/malefic aspects to significator = yes/no
  5. Tajika Ithasala = approaching aspect = YES (will happen)
  6. Tajika Ishrafa = separating aspect = NO (won't happen)
  7. Timing = degrees to exact aspect = time units until outcome

Supported question types:
  job, career, business, money, wealth, marriage, relationship,
  love, children, health, travel, foreign, property, legal,
  spiritual, education, vehicle, government, exam, interview
"""

from datetime import datetime, date
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
UPACHAYA  = [3, 6, 10, 11]

NAKSHATRAS = [
    "Ashvini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni",
    "Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha",
    "Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana",
    "Dhanishtha","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# Question type → significator houses + karaka planets
QUESTION_SIGNIFICATORS = {
    "job":          {"houses":[6,10], "karakas":["Sun","Saturn","Mercury"], "topic":"employment and service"},
    "career":       {"houses":[10,1], "karakas":["Sun","Saturn","Mercury"], "topic":"career trajectory"},
    "promotion":    {"houses":[10,11],"karakas":["Sun","Jupiter"],          "topic":"career advancement"},
    "business":     {"houses":[7,10], "karakas":["Mercury","Jupiter"],      "topic":"business success"},
    "money":        {"houses":[2,11], "karakas":["Jupiter","Venus"],        "topic":"financial gains"},
    "wealth":       {"houses":[2,11], "karakas":["Jupiter","Venus"],        "topic":"wealth accumulation"},
    "loan":         {"houses":[6,8],  "karakas":["Saturn","Rahu"],          "topic":"debt and loans"},
    "marriage":     {"houses":[7,2],  "karakas":["Venus","Jupiter"],        "topic":"marriage"},
    "relationship": {"houses":[7,5],  "karakas":["Venus","Moon"],           "topic":"romantic relationship"},
    "love":         {"houses":[5,7],  "karakas":["Venus","Moon"],           "topic":"love and romance"},
    "breakup":      {"houses":[6,12], "karakas":["Saturn","Mars"],          "topic":"separation"},
    "divorce":      {"houses":[6,12], "karakas":["Saturn","Mars","Rahu"],   "topic":"divorce"},
    "children":     {"houses":[5,9],  "karakas":["Jupiter","Moon"],         "topic":"children and progeny"},
    "pregnancy":    {"houses":[5,9],  "karakas":["Jupiter","Moon"],         "topic":"pregnancy"},
    "health":       {"houses":[1,6],  "karakas":["Sun","Moon"],             "topic":"health and recovery"},
    "surgery":      {"houses":[6,8],  "karakas":["Mars","Sun"],             "topic":"surgery outcome"},
    "travel":       {"houses":[3,9],  "karakas":["Mercury","Moon"],         "topic":"travel"},
    "foreign":      {"houses":[9,12], "karakas":["Rahu","Jupiter"],         "topic":"foreign matters"},
    "property":     {"houses":[4,12], "karakas":["Mars","Moon"],            "topic":"property"},
    "legal":        {"houses":[6,7],  "karakas":["Saturn","Mars"],          "topic":"legal matters"},
    "court":        {"houses":[6,7],  "karakas":["Saturn","Mars"],          "topic":"court case"},
    "education":    {"houses":[4,9],  "karakas":["Mercury","Jupiter"],      "topic":"education"},
    "exam":         {"houses":[4,5],  "karakas":["Mercury","Jupiter"],      "topic":"exam result"},
    "interview":    {"houses":[1,10], "karakas":["Mercury","Sun"],          "topic":"interview success"},
    "vehicle":      {"houses":[4,12], "karakas":["Venus","Mars"],           "topic":"vehicle purchase"},
    "government":   {"houses":[6,10], "karakas":["Sun","Saturn"],           "topic":"government matters"},
    "spiritual":    {"houses":[9,12], "karakas":["Jupiter","Ketu"],         "topic":"spiritual progress"},
    "lost":         {"houses":[2,7],  "karakas":["Moon","Mercury"],         "topic":"lost item recovery"},
    "theft":        {"houses":[2,7],  "karakas":["Saturn","Rahu","Mars"],   "topic":"theft recovery"},
    "missing":      {"houses":[1,7],  "karakas":["Moon","Mercury"],         "topic":"missing person"},
    "investment":   {"houses":[5,11], "karakas":["Jupiter","Mercury"],      "topic":"investment outcome"},
    "startup":      {"houses":[1,10,11],  "karakas":["Mercury","Rahu","Jupiter"],"topic":"startup success"},
}

# Moon nakshatra quality for Prashna
PRASHNA_NAKSHATRA = {
    "Ashvini":    ("good","swift result"),
    "Bharani":    ("mixed","heavy karma involved"),
    "Krittika":   ("good","sharp decisive outcome"),
    "Rohini":     ("excellent","very favorable, abundance"),
    "Mrigashira": ("good","searching energy, partial success"),
    "Ardra":      ("difficult","storms, delays, transformation"),
    "Punarvasu":  ("good","return, renewal, second chance"),
    "Pushya":     ("excellent","most auspicious, YES answer likely"),
    "Ashlesha":   ("difficult","hidden motives, deception possible"),
    "Magha":      ("good","authority supports, ancestors bless"),
    "Purva Phalguni":("good","pleasure, creative success"),
    "Uttara Phalguni":("excellent","stable success, partnership works"),
    "Hasta":      ("good","craftsmanship succeeds, travel good"),
    "Chitra":     ("good","bright outcome, beautiful result"),
    "Swati":      ("mixed","independent outcome, unpredictable"),
    "Vishakha":   ("good","goals achieved through determination"),
    "Anuradha":   ("good","friendship and cooperation bring success"),
    "Jyeshtha":   ("mixed","elder's wisdom needed, complex outcome"),
    "Mula":       ("difficult","root disruption, avoid new beginnings"),
    "Purva Ashadha":("good","invincible momentum, victory"),
    "Uttara Ashadha":("excellent","final victory, lasting success"),
    "Shravana":   ("good","listening leads to success"),
    "Dhanishtha": ("good","wealth and rhythm, musical success"),
    "Shatabhisha":("mixed","healing possible, unconventional path"),
    "Purva Bhadrapada":("difficult","fierce energy, transformation"),
    "Uttara Bhadrapada":("good","deep wisdom brings success"),
    "Revati":     ("good","completion, compassionate outcome"),
}

# Tajika aspect orbs (degrees)
TAJIKA_ASPECTS = {
    "conjunction": 0,
    "sextile":    60,
    "square":     90,
    "trine":      120,
    "opposition": 180,
}
TAJIKA_ORB = 8  # degrees


def cast_prashna_chart(
    question_time: datetime = None,
    lat: float = 28.6139,
    lng: float = 77.2090,
    timezone_offset: float = 5.5,
) -> dict:
    """
    Cast a Prashna chart for the exact moment of the question.
    Returns complete chart data for the question moment.
    """
    import swisseph as swe

    if question_time is None:
        question_time = datetime.utcnow()

    # Convert to JD
    utc_time = question_time
    if question_time.tzinfo is not None:
        from datetime import timezone
        utc_time = question_time.astimezone(timezone.utc).replace(tzinfo=None)

    jd = swe.julday(
        utc_time.year, utc_time.month, utc_time.day,
        utc_time.hour + utc_time.minute/60.0 + utc_time.second/3600.0
    )

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayanamsa = swe.get_ayanamsa(jd)

    # Calculate houses
    houses, ascmc = swe.houses_ex(jd, lat, lng, b'P', swe.FLG_SIDEREAL)
    asc_long = ascmc[0]
    lagna_long = (asc_long - ayanamsa) % 360
    lagna_sign = SIGNS[int(lagna_long / 30)]
    lagna_deg  = lagna_long % 30

    lagna_idx = SIGNS.index(lagna_sign)

    # Calculate planets
    PLANET_IDS = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN,
        "Rahu": swe.MEAN_NODE,
    }

    planets = {}
    for name, pid in PLANET_IDS.items():
        pos, _ = swe.calc_ut(jd, pid)
        long_trop = pos[0]
        if name == "Rahu":
            long_trop = (long_trop + 180) % 360  # True node → Rahu
            long_trop = pos[0]  # Actually Rahu is the mean node directly

        long_sid = (long_trop - ayanamsa) % 360
        sign_idx  = int(long_sid / 30)
        sign_name = SIGNS[sign_idx]
        degree    = long_sid % 30
        house     = ((sign_idx - lagna_idx) % 12) + 1
        nak_idx   = int(long_sid / (360/27))

        planets[name] = {
            "sign":      sign_name,
            "degree":    round(degree, 2),
            "longitude": round(long_sid, 4),
            "house":     house,
            "nakshatra": NAKSHATRAS[nak_idx % 27],
        }

    # Ketu = opposite of Rahu
    rahu_long = planets["Rahu"]["longitude"]
    ketu_long = (rahu_long + 180) % 360
    ketu_sign_idx = int(ketu_long / 30)
    planets["Ketu"] = {
        "sign":      SIGNS[ketu_sign_idx],
        "degree":    round(ketu_long % 30, 2),
        "longitude": round(ketu_long, 4),
        "house":     ((ketu_sign_idx - lagna_idx) % 12) + 1,
        "nakshatra": NAKSHATRAS[int(ketu_long/(360/27)) % 27],
    }

    # Moon nakshatra
    moon_nak  = planets["Moon"]["nakshatra"]
    nak_quality, nak_desc = PRASHNA_NAKSHATRA.get(moon_nak, ("mixed","moderate"))

    return {
        "question_time": question_time.isoformat(),
        "jd":            jd,
        "lagna":         {"sign": lagna_sign, "degree": round(lagna_deg, 2)},
        "lagna_lord":    SIGN_LORDS.get(lagna_sign, ""),
        "planets":       planets,
        "moon_nakshatra": moon_nak,
        "moon_nak_quality": nak_quality,
        "moon_nak_desc":    nak_desc,
        "lat":           lat,
        "lng":           lng,
    }


def detect_question_type(question: str) -> tuple:
    """Detect what type of question is being asked."""
    q_lower = question.lower()

    KEYWORDS = {
        "job":        ["job","employment","hired","get hired","job offer"],
        "career":     ["career","profession","path","calling"],
        "promotion":  ["promotion","promoted","raise","increment","senior"],
        "business":   ["business","company","startup","venture","enterprise"],
        "money":      ["money","salary","income","earn","financial"],
        "wealth":     ["wealth","rich","billionaire","wealthy","affluent"],
        "loan":       ["loan","debt","borrow","repay","emi","credit"],
        "marriage":   ["marry","marriage","wedding","spouse","husband","wife"],
        "relationship":["relationship","partner","girlfriend","boyfriend","dating"],
        "love":       ["love","romance","romantic","fall in love","soulmate"],
        "breakup":    ["breakup","break up","separate","split","end relationship"],
        "divorce":    ["divorce","separated","divorce"],
        "children":   ["children","child","baby","conceive","parent"],
        "pregnancy":  ["pregnant","pregnancy","conceive","ivf","fertility"],
        "health":     ["health","illness","sick","disease","recover","cure"],
        "surgery":    ["surgery","operation","hospital","procedure"],
        "travel":     ["travel","trip","journey","visit","go to"],
        "foreign":    ["abroad","foreign","immigration","visa","overseas","move"],
        "property":   ["property","house","flat","apartment","buy home","land"],
        "legal":      ["legal","lawyer","case","court","lawsuit","dispute"],
        "court":      ["court","judge","hearing","verdict","trial"],
        "education":  ["education","study","course","degree","university","college"],
        "exam":       ["exam","test","result","pass","fail","score"],
        "interview":  ["interview","selection","placement","offer letter"],
        "vehicle":    ["car","vehicle","bike","motorcycle","buy car"],
        "government": ["government","ias","ips","civil service","government job"],
        "spiritual":  ["spiritual","meditation","moksha","enlightenment","guru"],
        "investment": ["invest","investment","stock","share","mutual fund","crypto"],
        "startup":    ["startup","fundraise","investor","pitch","funding","seed"],
        "lost":       ["lost","missing item","where is","find"],
        "theft":      ["stolen","theft","robbery","burglar"],
    }

    scores = {}
    for qtype, keywords in KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            scores[qtype] = score

    if not scores:
        return "career", QUESTION_SIGNIFICATORS["career"]

    best = max(scores, key=scores.get)
    return best, QUESTION_SIGNIFICATORS.get(best, QUESTION_SIGNIFICATORS["career"])


def analyze_tajika_aspects(planets: dict, sig_house: int, lagna_idx: int) -> dict:
    """
    Tajika aspect analysis — approaching vs separating.
    Ithasala (approaching) = YES, will happen
    Ishrafa (separating) = NO, won't happen
    Musaripha = transfer of light = through a third party
    """
    # Get significator sign
    sig_sign_idx = (lagna_idx + sig_house - 1) % 12

    # Find planets in or aspecting the significator house
    sig_planets = [p for p, d in planets.items()
                   if d.get("house") == sig_house]

    # Find approaching aspects (Ithasala)
    ithasala = []
    ishrafa  = []

    for p1_name, p1_data in planets.items():
        for p2_name, p2_data in planets.items():
            if p1_name >= p2_name:
                continue

            p1_long = p1_data.get("longitude", 0)
            p2_long = p2_data.get("longitude", 0)

            diff = abs(p1_long - p2_long) % 360
            if diff > 180:
                diff = 360 - diff

            # Check each Tajika aspect
            for asp_name, asp_deg in TAJIKA_ASPECTS.items():
                orb = abs(diff - asp_deg)
                if orb <= TAJIKA_ORB:
                    # Is it applying (approaching) or separating?
                    # Slower planet catching faster = applying
                    # If p1 is faster and moving away = separating
                    is_applying = orb < 3  # within 3° = very close, applying

                    entry = {
                        "planet1":   p1_name,
                        "planet2":   p2_name,
                        "aspect":    asp_name,
                        "orb":       round(orb, 2),
                        "applying":  is_applying,
                        "quality":   "benefic" if (p1_name in BENEFICS and p2_name in BENEFICS) else
                                     "malefic" if (p1_name in MALEFICS and p2_name in MALEFICS) else
                                     "mixed",
                    }

                    if is_applying:
                        ithasala.append(entry)
                    else:
                        ishrafa.append(entry)

    return {
        "ithasala":     ithasala[:5],
        "ishrafa":      ishrafa[:5],
        "sig_planets":  sig_planets,
        "applying_count": len(ithasala),
        "separating_count": len(ishrafa),
    }


def calculate_prashna_answer(
    prashna_chart: dict,
    question_type: str,
    significator: dict,
    natal_chart: dict = None,
) -> dict:
    """
    Core Prashna analysis — produces YES/NO/MAYBE + timing + explanation.

    Rules applied:
    1. Lagna strength
    2. Moon quality (nakshatra + house)
    3. Significator house condition
    4. Karaka planet strength
    5. Tajika aspects
    6. Benefic/malefic balance
    7. Hora (planetary hour at question time)
    """
    planets   = prashna_chart.get("planets", {})
    lagna     = prashna_chart.get("lagna", {})
    lagna_sign= lagna.get("sign", "Aries")
    lagna_lord= prashna_chart.get("lagna_lord", "")
    lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

    moon_nak_quality = prashna_chart.get("moon_nak_quality", "mixed")
    moon_h   = planets.get("Moon", {}).get("house", 0)
    moon_sign= planets.get("Moon", {}).get("sign", "")

    sig_houses  = significator.get("houses", [10])
    sig_karakas = significator.get("karakas", ["Sun"])
    sig_house   = sig_houses[0]

    # Positive and negative indicators
    yes_factors = []
    no_factors  = []
    score       = 50  # start neutral

    # 1. LAGNA STRENGTH
    lagna_lord_h = planets.get(lagna_lord, {}).get("house", 0)
    if lagna_lord_h in KENDRA + TRIKONA:
        yes_factors.append(f"Lagna lord {lagna_lord} in house {lagna_lord_h} — question has strong foundation")
        score += 10
    elif lagna_lord_h in DUSTHANA:
        no_factors.append(f"Lagna lord {lagna_lord} in house {lagna_lord_h} — question faces obstacles")
        score -= 10

    lagna_planets = [p for p,d in planets.items() if d.get("house")==1]
    if any(p in BENEFICS for p in lagna_planets):
        yes_factors.append(f"Benefic in lagna — favorable first impression, matter proceeds well")
        score += 10
    if any(p in MALEFICS for p in lagna_planets):
        no_factors.append(f"Malefic in lagna — obstacles and delays in the matter")
        score -= 10

    # 2. MOON QUALITY
    if moon_nak_quality == "excellent":
        yes_factors.append(f"Moon in excellent nakshatra ({prashna_chart.get('moon_nakshatra')}) — very favorable for this question")
        score += 20
    elif moon_nak_quality == "good":
        yes_factors.append(f"Moon in good nakshatra ({prashna_chart.get('moon_nakshatra')}) — positive energy for this matter")
        score += 10
    elif moon_nak_quality == "difficult":
        no_factors.append(f"Moon in difficult nakshatra ({prashna_chart.get('moon_nakshatra')}) — timing is challenging")
        score -= 15

    if moon_h in KENDRA + TRIKONA:
        yes_factors.append(f"Moon in angular/trinal house {moon_h} — emotional alignment with outcome")
        score += 10
    elif moon_h in DUSTHANA:
        no_factors.append(f"Moon in house {moon_h} — emotional anxiety around this matter, clarity lacking")
        score -= 10

    # 3. SIGNIFICATOR HOUSE
    planets_in_sig = [p for p,d in planets.items() if d.get("house")==sig_house]
    if any(p in BENEFICS for p in planets_in_sig):
        yes_factors.append(f"Benefic planet in house {sig_house} (significator) — matter is supported")
        score += 15
    if any(p in MALEFICS for p in planets_in_sig):
        no_factors.append(f"Malefic in house {sig_house} — significator house under pressure")
        score -= 10

    # 4. KARAKA STRENGTH
    for karaka in sig_karakas[:2]:
        k_house = planets.get(karaka, {}).get("house", 0)
        k_sign  = planets.get(karaka, {}).get("sign", "")
        if k_house in KENDRA + TRIKONA:
            yes_factors.append(f"Karaka {karaka} in house {k_house} — karaka strong, supports positive outcome")
            score += 12
        if k_sign == EXALTATION.get(karaka):
            yes_factors.append(f"Karaka {karaka} exalted in {k_sign} — exceptionally powerful, YES strongly indicated")
            score += 20
        if k_sign == DEBILITATION.get(karaka):
            no_factors.append(f"Karaka {karaka} debilitated in {k_sign} — karaka weak, delays or denial")
            score -= 15
        if k_house in DUSTHANA:
            no_factors.append(f"Karaka {karaka} in house {k_house} — karaka in difficulty, obstacles")
            score -= 10

    # 5. TAJIKA ASPECTS
    tajika = analyze_tajika_aspects(planets, sig_house, lagna_idx)
    if tajika["applying_count"] > tajika["separating_count"]:
        yes_factors.append(f"Tajika Ithasala — {tajika['applying_count']} approaching aspects — matter is moving toward completion")
        score += 15
    elif tajika["separating_count"] > tajika["applying_count"]:
        no_factors.append(f"Tajika Ishrafa — aspects separating — matter is moving away, timing off")
        score -= 10

    # 6. JUPITER OVERALL
    jup_h = planets.get("Jupiter", {}).get("house", 0)
    if jup_h in KENDRA + TRIKONA:
        yes_factors.append(f"Jupiter in house {jup_h} — divine blessing on the matter")
        score += 10

    # 7. RAHU/KETU FACTOR
    rahu_h = planets.get("Rahu", {}).get("house", 0)
    if rahu_h == sig_house:
        no_factors.append(f"Rahu in significator house {sig_house} — unconventional or delayed outcome")
        score -= 5

    # VERDICT
    score = min(95, max(10, score))

    if score >= 75:
        verdict = "YES"
        confidence = "high"
        explanation = "Multiple strong positive indicators align. The matter will proceed favorably."
    elif score >= 60:
        verdict = "YES — with effort"
        confidence = "moderate"
        explanation = "Positive outcome likely but requires active effort and patience."
    elif score >= 45:
        verdict = "UNCERTAIN"
        confidence = "low"
        explanation = "Mixed indicators — the outcome depends on actions taken in the coming weeks."
    elif score >= 30:
        verdict = "DELAY"
        confidence = "moderate"
        explanation = "Matter will happen but not immediately. Timing needs adjustment."
    else:
        verdict = "NOT NOW"
        confidence = "high"
        explanation = "Current conditions are not favorable. Wait for a better planetary period."

    # TIMING ESTIMATE
    timing = _estimate_prashna_timing(planets, sig_house, score, question_type)

    # REMEDY
    remedy = _prashna_remedy(question_type, sig_karakas, no_factors)

    return {
        "verdict":      verdict,
        "confidence":   confidence,
        "score":        score,
        "explanation":  explanation,
        "yes_factors":  yes_factors,
        "no_factors":   no_factors,
        "timing":       timing,
        "tajika":       tajika,
        "remedy":       remedy,
        "moon_quality": moon_nak_quality,
        "question_type": question_type,
        "significator_house": sig_house,
    }


def _estimate_prashna_timing(
    planets: dict, sig_house: int, score: int, question_type: str
) -> str:
    """Estimate timing of outcome from planetary positions."""
    moon_h = planets.get("Moon", {}).get("house", 0)
    moon_sign = planets.get("Moon", {}).get("sign", "")

    MOVABLE = ["Aries","Cancer","Libra","Capricorn"]
    FIXED   = ["Taurus","Leo","Scorpio","Aquarius"]
    DUAL    = ["Gemini","Virgo","Sagittarius","Pisces"]

    if score >= 70:
        if moon_sign in MOVABLE:
            return "Soon — within weeks (movable sign Moon suggests swift movement)"
        elif moon_sign in FIXED:
            return "Slowly but surely — 3-6 months (fixed sign Moon indicates steady progress)"
        else:
            return "2-4 months (dual sign Moon — moderate pace, some back and forth)"
    elif score >= 50:
        if moon_sign in MOVABLE:
            return "1-3 months with effort required"
        elif moon_sign in FIXED:
            return "6-12 months — patience is essential"
        else:
            return "3-6 months — fluctuating progress"
    else:
        return "Timing unclear — not favorable in near term. Revisit in 3-6 months."


def _prashna_remedy(question_type: str, karakas: list, no_factors: list) -> str:
    """Specific Prashna remedy based on question type and weak factors."""
    REMEDIES = {
        "job":        "Offer water to Sun at sunrise for 11 days. Visit Hanuman temple on Tuesday.",
        "career":     "Chant Sun mantra (Om Suryaya Namah) 108 times daily. Keep workplace clean.",
        "business":   "Offer green items to Mercury on Wednesday. Keep Saraswati image at workplace.",
        "money":      "Offer yellow sweets to Jupiter on Thursday. Keep silver coin in wallet.",
        "marriage":   "Offer white flowers to Venus on Friday. Fast on Fridays for 7 weeks.",
        "relationship":"Venus remedy: Keep rose quartz. Offer perfume to Venus on Friday.",
        "children":   "Jupiter remedy: Offer yellow sweets Thursday. Keep baby elephant figurine.",
        "health":     "Sun remedy: Sunrise water offering. Moon remedy: Milk to Shiva on Monday.",
        "travel":     "Mercury remedy: Donate green items Wednesday. Chant Ganesh mantra before travel.",
        "foreign":    "Rahu remedy: Feed crows. Keep elephant. Donate on Saturdays.",
        "property":   "Mars remedy: Visit Hanuman temple Tuesday. Donate land or plants.",
        "legal":      "Saturn remedy: Serve poor Saturday. Jupiter remedy: Donate to education.",
        "education":  "Mercury + Jupiter remedy: Donate books. Study under a pipal tree.",
        "investment": "Jupiter remedy: Thursday yellow sweets. Keep account books clean.",
        "startup":    "Mercury (communication) + Jupiter (expansion): Combined remedies active.",
    }

    base = REMEDIES.get(question_type, f"Strengthen {karakas[0] if karakas else 'key planet'} through its natural remedy.")

    if no_factors:
        base += " Additionally: address the obstacles identified in the analysis."

    return base


def run_prashna(
    question: str,
    lat: float = 28.6139,
    lng: float = 77.2090,
    question_time: datetime = None,
    natal_chart: dict = None,
) -> dict:
    """
    Complete Prashna analysis for a question asked right now.
    Main entry point.
    """
    if question_time is None:
        question_time = datetime.utcnow()

    # Cast prashna chart
    prashna_chart = cast_prashna_chart(
        question_time=question_time,
        lat=lat, lng=lng,
    )

    if prashna_chart.get("error"):
        return {"error": prashna_chart["error"]}

    # Detect question type
    q_type, significator = detect_question_type(question)

    # Analyze
    analysis = calculate_prashna_answer(
        prashna_chart=prashna_chart,
        question_type=q_type,
        significator=significator,
        natal_chart=natal_chart,
    )

    # Build LLM prompt for narrative answer
    llm_prompt = build_prashna_llm_prompt(
        question=question,
        prashna_chart=prashna_chart,
        analysis=analysis,
        q_type=q_type,
        significator=significator,
    )

    return {
        "question":       question,
        "question_type":  q_type,
        "question_topic": significator.get("topic",""),
        "asked_at":       question_time.isoformat(),
        "prashna_chart":  prashna_chart,
        "analysis":       analysis,
        "verdict":        analysis["verdict"],
        "confidence":     analysis["confidence"],
        "score":          analysis["score"],
        "timing":         analysis["timing"],
        "yes_factors":    analysis["yes_factors"],
        "no_factors":     analysis["no_factors"],
        "remedy":         analysis["remedy"],
        "llm_prompt":     llm_prompt,
        "lagna":          prashna_chart["lagna"],
        "moon_nakshatra": prashna_chart["moon_nakshatra"],
        "moon_quality":   prashna_chart["moon_nak_quality"],
    }


def build_prashna_llm_prompt(
    question: str,
    prashna_chart: dict,
    analysis: dict,
    q_type: str,
    significator: dict,
) -> str:
    """Build the LLM prompt for Prashna narrative response."""
    planets = prashna_chart.get("planets", {})
    lagna   = prashna_chart.get("lagna", {})

    yes_str = "\n".join(f"  + {f}" for f in analysis["yes_factors"][:4])
    no_str  = "\n".join(f"  - {f}" for f in analysis["no_factors"][:3])

    system = """You are Antar — a precise Vedic astrology AI answering a Prashna (horary) question.
CRITICAL RULES:
- Never use Sanskrit terms (no Ithasala, Ishrafa, Dusthana, Karaka)
- Answer in plain psychological and practical language
- Lead with the VERDICT — be direct
- Explain WHY in plain English
- Give specific timing if favorable
- Give ONE specific remedy at the end
- Keep under 200 words total
- Sound like a wise mentor, not a textbook"""

    moon_data  = planets.get('Moon', {})
    moon_sign  = moon_data.get('sign','')
    moon_house = moon_data.get('house','')

    prompt = f"""PRASHNA QUESTION: "{question}"
QUESTION TYPE: {q_type} — {significator.get('topic','')}

PRASHNA CHART:
  Lagna: {lagna.get('sign','')} at {lagna.get('degree','')}°
  Moon: {moon_sign} in {prashna_chart.get('moon_nakshatra','')} (house {moon_house})
  Moon quality: {prashna_chart.get('moon_nak_quality','')} — {prashna_chart.get('moon_nak_desc','')}

PYTHON ENGINE VERDICT: {analysis['verdict']} (score: {analysis['score']}/100, confidence: {analysis['confidence']})
TIMING: {analysis['timing']}

SUPPORTING FACTORS (favorable):
{yes_str if yes_str else '  None significant'}

CHALLENGING FACTORS:
{no_str if no_str else '  None significant'}

REMEDY: {analysis['remedy']}

Generate a Prashna answer using this structure:

**The Answer**
[1-2 sentences — direct verdict in plain language. "{analysis['verdict']}" means what practically?]

**Why**
[2-3 sentences — explain the key factors in plain psychological language. Never say "Dusthana" — say "challenging position". Never say "Karaka" — say "key planet for this matter".]

**When**
[1-2 sentences — timing estimate in plain language]

**What to do**
[1 sentence — the specific remedy translated into plain action]"""

    return prompt
