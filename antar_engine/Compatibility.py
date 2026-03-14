"""
antar_engine/compatibility.py
Vedic Compatibility Engine — D1 + D9 + House Analysis
Ashtakoot + Synastry + Dasha Timing + Psychology Layer

Philosophy: Opposites attract and help us grow (yin-yang).
We flag differences as growth opportunities, not just problems.
Score shown as % match with nuanced narrative.
"""

from datetime import datetime, date
from typing import Optional

# ── Nakshatra data ─────────────────────────────────────────────────────────
NAKSHATRAS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha",
    "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

NAKSHATRA_LORDS = [
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
]

# Nakshatra gender (M/F) for Yoni compatibility
NAKSHATRA_GENDER = {
    "Ashwini":"M","Bharani":"F","Krittika":"F","Rohini":"M",
    "Mrigashira":"F","Ardra":"F","Punarvasu":"M","Pushya":"M",
    "Ashlesha":"F","Magha":"M","Purva Phalguni":"F","Uttara Phalguni":"M",
    "Hasta":"M","Chitra":"F","Swati":"M","Vishakha":"F",
    "Anuradha":"F","Jyeshtha":"F","Mula":"F","Purva Ashadha":"F",
    "Uttara Ashadha":"M","Shravana":"F","Dhanishtha":"M",
    "Shatabhisha":"M","Purva Bhadrapada":"M","Uttara Bhadrapada":"F","Revati":"F"
}

# Nakshatra Gana (nature): Dev/Manav/Rakshasa
NAKSHATRA_GANA = {
    "Ashwini":"Dev","Bharani":"Manav","Krittika":"Rakshasa","Rohini":"Manav",
    "Mrigashira":"Dev","Ardra":"Manav","Punarvasu":"Dev","Pushya":"Dev",
    "Ashlesha":"Rakshasa","Magha":"Rakshasa","Purva Phalguni":"Manav","Uttara Phalguni":"Manav",
    "Hasta":"Dev","Chitra":"Rakshasa","Swati":"Dev","Vishakha":"Rakshasa",
    "Anuradha":"Dev","Jyeshtha":"Rakshasa","Mula":"Rakshasa","Purva Ashadha":"Manav",
    "Uttara Ashadha":"Manav","Shravana":"Dev","Dhanishtha":"Rakshasa",
    "Shatabhisha":"Rakshasa","Purva Bhadrapada":"Manav","Uttara Bhadrapada":"Dev","Revati":"Dev"
}

# Nakshatra Nadi (energy channel): Adi/Madhya/Antya
NAKSHATRA_NADI = {
    "Ashwini":"Adi","Bharani":"Madhya","Krittika":"Antya","Rohini":"Antya",
    "Mrigashira":"Madhya","Ardra":"Adi","Punarvasu":"Adi","Pushya":"Madhya",
    "Ashlesha":"Antya","Magha":"Antya","Purva Phalguni":"Madhya","Uttara Phalguni":"Adi",
    "Hasta":"Adi","Chitra":"Madhya","Swati":"Antya","Vishakha":"Antya",
    "Anuradha":"Madhya","Jyeshtha":"Adi","Mula":"Adi","Purva Ashadha":"Madhya",
    "Uttara Ashadha":"Antya","Shravana":"Antya","Dhanishtha":"Madhya",
    "Shatabhisha":"Adi","Purva Bhadrapada":"Adi","Uttara Bhadrapada":"Madhya","Revati":"Antya"
}

# Zodiac signs (0=Aries through 11=Pisces)
SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

# Sign rulers
SIGN_RULER = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# Planet friendship table
PLANET_FRIENDS = {
    "Sun":     {"friends":["Moon","Mars","Jupiter"],    "neutral":["Mercury"],          "enemies":["Venus","Saturn","Rahu","Ketu"]},
    "Moon":    {"friends":["Sun","Mercury"],            "neutral":["Mars","Jupiter","Venus","Saturn"], "enemies":["Rahu","Ketu"]},
    "Mars":    {"friends":["Sun","Moon","Jupiter"],     "neutral":["Venus","Saturn"],   "enemies":["Mercury","Rahu","Ketu"]},
    "Mercury": {"friends":["Sun","Venus"],              "neutral":["Mars","Jupiter","Saturn"], "enemies":["Moon","Rahu","Ketu"]},
    "Jupiter": {"friends":["Sun","Moon","Mars"],        "neutral":["Saturn"],           "enemies":["Mercury","Venus","Rahu","Ketu"]},
    "Venus":   {"friends":["Mercury","Saturn"],         "neutral":["Mars","Jupiter"],   "enemies":["Sun","Moon","Rahu","Ketu"]},
    "Saturn":  {"friends":["Mercury","Venus"],          "neutral":["Jupiter"],          "enemies":["Sun","Moon","Mars","Rahu","Ketu"]},
    "Rahu":    {"friends":["Venus","Saturn"],           "neutral":["Mercury","Jupiter"],"enemies":["Sun","Moon","Mars"]},
    "Ketu":    {"friends":["Mars","Jupiter"],           "neutral":["Venus","Saturn"],   "enemies":["Sun","Moon","Mercury"]},
}

# Dasha sequence and years
DASHA_SEQUENCE = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
DASHA_YEARS = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,"Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}

# Yin-Yang archetype pairs (opposites that attract and grow together)
YIN_YANG_PAIRS = {
    ("Mars","Moon"):   "Action meets intuition — the doer and the feeler. Mars provides direction, Moon provides wisdom. Classic growth pair.",
    ("Saturn","Moon"): "Structure meets emotion — Saturn grounds Moon's waves, Moon softens Saturn's edges.",
    ("Rahu","Ketu"):   "The nodes — if one has Rahu strong and the other Ketu, this is a karmic mirror relationship. Deep past-life connection.",
    ("Sun","Saturn"):  "Ego meets humility — Sun learns patience, Saturn learns joy. Difficult but transformative.",
    ("Jupiter","Rahu"):"Expansion meets obsession — Jupiter moderates Rahu's excesses, Rahu pushes Jupiter's limits.",
    ("Venus","Mars"):  "Classic masculine-feminine polarity. Attraction and friction are two sides of the same coin.",
    ("Mercury","Jupiter"): "Logic meets wisdom — Mercury sharpens Jupiter's ideas, Jupiter expands Mercury's thinking.",
}


# ── Ashtakoot System (8-point compatibility, 36 total points) ──────────────

def _get_nakshatra_index(nakshatra_name: str) -> int:
    try:
        return NAKSHATRAS.index(nakshatra_name)
    except ValueError:
        return 0

def _varna_score(chart_a: dict, chart_b: dict) -> dict:
    """Varna — spiritual/psychological compatibility. Max 1 point."""
    VARNA_MAP = {
        "Brahmin":  ["Cancer","Scorpio","Pisces"],
        "Kshatriya":["Aries","Leo","Sagittarius"],
        "Vaishya":  ["Taurus","Virgo","Capricorn"],
        "Shudra":   ["Gemini","Libra","Aquarius"],
    }
    VARNA_ORDER = ["Shudra","Vaishya","Kshatriya","Brahmin"]

    def get_varna(sign):
        for v, signs in VARNA_MAP.items():
            if sign in signs:
                return v
        return "Vaishya"

    moon_a = chart_a.get("planets",{}).get("Moon",{}).get("sign","Aries")
    moon_b = chart_b.get("planets",{}).get("Moon",{}).get("sign","Aries")
    va, vb = get_varna(moon_a), get_varna(moon_b)

    score = 1 if VARNA_ORDER.index(va) >= VARNA_ORDER.index(vb) else 0
    return {
        "name": "Varna",
        "max": 1,
        "score": score,
        "a_value": va,
        "b_value": vb,
        "dimension": "Spiritual alignment",
        "match_pct": score * 100,
        "narrative_match": f"Both operate from a {va} consciousness — naturally aligned approach to life's purpose.",
        "narrative_work": f"Different spiritual frameworks ({va} vs {vb}). One is more structure-oriented, the other more expansive. This is growth territory — not a dealbreaker.",
        "yin_yang": "Different varnas can complement — the Brahmin learns practicality from Vaishya, the Vaishya gains depth from Brahmin." if va != vb else "",
    }

def _vashya_score(chart_a: dict, chart_b: dict) -> dict:
    """Vashya — mutual attraction and influence. Max 2 points."""
    VASHYA_GROUPS = {
        "Manav":   ["Aries","Taurus","Gemini","Virgo"],
        "Chatushpad":["Cancer","Sagittarius","Capricorn"],
        "Jalchar":  ["Pisces","Cancer"],
        "Vanchar":  ["Leo","Scorpio"],
        "Keeta":    ["Scorpio"],
    }
    VASHYA_COMPAT = {
        ("Manav","Manav"):       2,
        ("Chatushpad","Manav"):  1,
        ("Manav","Chatushpad"):  1,
        ("Jalchar","Manav"):     1,
        ("Chatushpad","Chatushpad"): 2,
    }

    def get_group(sign):
        for g, signs in VASHYA_GROUPS.items():
            if sign in signs:
                return g
        return "Manav"

    moon_a = chart_a.get("planets",{}).get("Moon",{}).get("sign","Aries")
    moon_b = chart_b.get("planets",{}).get("Moon",{}).get("sign","Aries")
    ga, gb = get_group(moon_a), get_group(moon_b)

    score = VASHYA_COMPAT.get((ga, gb), VASHYA_COMPAT.get((gb, ga), 0))
    return {
        "name": "Vashya",
        "max": 2,
        "score": score,
        "a_value": ga,
        "b_value": gb,
        "dimension": "Mutual attraction",
        "match_pct": round(score / 2 * 100),
        "narrative_match": "Natural gravitational pull toward each other. Attraction is effortless.",
        "narrative_work": "Attraction may require more conscious cultivation. The magnetism is there — it needs nurturing.",
        "yin_yang": "Low Vashya doesn't mean low attraction — it means the attraction is more intellectual or karmic than immediate.",
    }

def _tara_score(chart_a: dict, chart_b: dict) -> dict:
    """Tara — birth star compatibility. Max 3 points."""
    nak_a = chart_a.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    nak_b = chart_b.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    idx_a = _get_nakshatra_index(nak_a)
    idx_b = _get_nakshatra_index(nak_b)

    # Count from A's nakshatra to B's
    count = ((idx_b - idx_a) % 27) + 1
    tara_num = ((count - 1) % 9) + 1

    # Tara categories
    GOOD_TARAS = [1, 3, 5, 7]  # Janma, Vipat reduction, Kshema, Mitra, Param Mitra
    NEUTRAL_TARAS = [2, 6]
    BAD_TARAS = [4, 8, 9]

    if tara_num in GOOD_TARAS:
        score = 3
        label = "Favorable"
    elif tara_num in NEUTRAL_TARAS:
        score = 1
        label = "Neutral"
    else:
        score = 0
        label = "Challenging"

    TARA_NAMES = {1:"Janma",2:"Sampat",3:"Vipat",4:"Kshema",5:"Pratyak",
                  6:"Sadhana",7:"Naidhana",8:"Mitra",9:"Param Mitra"}

    return {
        "name": "Tara",
        "max": 3,
        "score": score,
        "a_value": nak_a,
        "b_value": nak_b,
        "dimension": "Destiny alignment",
        "match_pct": round(score / 3 * 100),
        "tara_label": label,
        "tara_number": tara_num,
        "narrative_match": f"Star alignment supports the relationship's longevity and shared destiny.",
        "narrative_work": f"The star pattern suggests this relationship requires more conscious navigation. The challenge IS the growth.",
        "yin_yang": "Challenging Tara often indicates a karmic relationship — one that teaches what comfortable relationships don't.",
    }

def _yoni_score(chart_a: dict, chart_b: dict) -> dict:
    """Yoni — natural instinct and physical compatibility. Max 4 points."""
    YONI_MAP = {
        "Ashwini":"Horse","Shatabhisha":"Horse",
        "Bharani":"Elephant","Revati":"Elephant",
        "Pushya":"Goat","Krittika":"Goat",
        "Rohini":"Serpent","Mrigashira":"Serpent",
        "Moola":"Dog","Ardra":"Dog",
        "Ashlesha":"Cat","Punarvasu":"Cat",
        "Magha":"Rat","Purva Phalguni":"Rat",
        "Uttara Phalguni":"Cow","Uttara Bhadrapada":"Cow",
        "Swati":"Buffalo","Hasta":"Buffalo",
        "Vishakha":"Tiger","Chitra":"Tiger",
        "Jyeshtha":"Deer","Anuradha":"Deer",
        "Purva Ashadha":"Monkey","Shravana":"Monkey",
        "Purva Bhadrapada":"Lion","Dhanishtha":"Lion",
        "Uttara Ashadha":"Mongoose",
    }
    FRIENDLY_YONI = {
        ("Horse","Horse"):4,("Elephant","Elephant"):4,("Cat","Cat"):4,
        ("Dog","Dog"):4,("Rat","Rat"):4,("Cow","Cow"):4,
        ("Tiger","Tiger"):4,("Deer","Deer"):4,("Monkey","Monkey"):4,
        ("Lion","Lion"):4,("Goat","Goat"):4,("Buffalo","Buffalo"):4,
        ("Horse","Deer"):3,("Deer","Horse"):3,
        ("Dog","Deer"):3,("Deer","Dog"):3,
        ("Rat","Elephant"):2,("Elephant","Rat"):1,
        ("Cat","Dog"):1,("Dog","Cat"):1,
        ("Mongoose","Serpent"):0,("Serpent","Mongoose"):0,
    }

    nak_a = chart_a.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    nak_b = chart_b.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    ya = YONI_MAP.get(nak_a, "Horse")
    yb = YONI_MAP.get(nak_b, "Horse")

    score = FRIENDLY_YONI.get((ya, yb), FRIENDLY_YONI.get((yb, ya), 2))
    score = min(4, score)

    return {
        "name": "Yoni",
        "max": 4,
        "score": score,
        "a_value": ya,
        "b_value": yb,
        "dimension": "Physical & instinctual harmony",
        "match_pct": round(score / 4 * 100),
        "narrative_match": "Natural physical rhythm and instinctual understanding. Bodies are in sync.",
        "narrative_work": "Different natural rhythms. Physical connection requires more communication and patience. Not impossible — different.",
        "yin_yang": "Opposite Yoni animals often have the most intense chemistry — the friction creates heat.",
    }

def _graha_maitri_score(chart_a: dict, chart_b: dict) -> dict:
    """Graha Maitri — mental/psychological compatibility. Max 5 points."""
    moon_a = chart_a.get("planets",{}).get("Moon",{}).get("sign","Aries")
    moon_b = chart_b.get("planets",{}).get("Moon",{}).get("sign","Aries")
    ruler_a = SIGN_RULER.get(moon_a, "Sun")
    ruler_b = SIGN_RULER.get(moon_b, "Sun")

    if ruler_a == ruler_b:
        score = 5
        rel = "Same ruler"
    elif ruler_b in PLANET_FRIENDS.get(ruler_a, {}).get("friends", []):
        score = 4
        rel = "Mutual friends"
    elif ruler_b in PLANET_FRIENDS.get(ruler_a, {}).get("neutral", []):
        score = 3
        rel = "Neutral"
    elif ruler_b in PLANET_FRIENDS.get(ruler_a, {}).get("enemies", []):
        score = 1
        rel = "Enemies"
    else:
        score = 2
        rel = "Mixed"

    return {
        "name": "Graha Maitri",
        "max": 5,
        "score": score,
        "a_value": f"{moon_a} ({ruler_a})",
        "b_value": f"{moon_b} ({ruler_b})",
        "dimension": "Mind-to-mind connection",
        "relationship": rel,
        "match_pct": round(score / 5 * 100),
        "narrative_match": f"Your minds operate on compatible frequencies. Conversations flow naturally. {ruler_a} and {ruler_b} are aligned.",
        "narrative_work": f"Different mental operating systems ({ruler_a} vs {ruler_b}). One thinks in systems, the other in feelings — or vice versa. This is the most growth-producing friction.",
        "yin_yang": f"When {ruler_a} and {ruler_b} energies differ, one partner sees what the other misses. Two different minds solving the same problem is more powerful than two identical ones.",
    }

def _gana_score(chart_a: dict, chart_b: dict) -> dict:
    """Gana — temperament compatibility. Max 6 points."""
    nak_a = chart_a.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    nak_b = chart_b.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    gana_a = NAKSHATRA_GANA.get(nak_a, "Manav")
    gana_b = NAKSHATRA_GANA.get(nak_b, "Manav")

    GANA_SCORES = {
        ("Dev","Dev"):6, ("Manav","Manav"):6, ("Rakshasa","Rakshasa"):6,
        ("Dev","Manav"):5, ("Manav","Dev"):5,
        ("Manav","Rakshasa"):1, ("Rakshasa","Manav"):1,
        ("Dev","Rakshasa"):0, ("Rakshasa","Dev"):0,
    }
    score = GANA_SCORES.get((gana_a, gana_b), 3)

    GANA_DESC = {
        "Dev": "divine temperament — idealistic, spiritual, rule-following",
        "Manav": "human temperament — practical, worldly, flexible",
        "Rakshasa": "intense temperament — passionate, rule-breaking, powerful"
    }

    return {
        "name": "Gana",
        "max": 6,
        "score": score,
        "a_value": f"{gana_a} ({GANA_DESC.get(gana_a,'')})",
        "b_value": f"{gana_b} ({GANA_DESC.get(gana_b,'')})",
        "dimension": "Temperament & lifestyle",
        "match_pct": round(score / 6 * 100),
        "narrative_match": f"Both carry {gana_a} energy — shared approach to life, similar values, natural temperament alignment.",
        "narrative_work": f"A {gana_a} and {gana_b} pairing creates productive tension. The idealist and the realist. The passionate and the practical. Classic growth pair.",
        "yin_yang": f"Dev-Rakshasa is the most intense pairing — the saint and the rebel. History's most transformative partnerships often have this combination. The Dev grounds the Rakshasa; the Rakshasa liberates the Dev.",
    }

def _bhakoot_score(chart_a: dict, chart_b: dict) -> dict:
    """Bhakoot — emotional and financial compatibility. Max 7 points."""
    moon_a = chart_a.get("planets",{}).get("Moon",{}).get("sign","Aries")
    moon_b = chart_b.get("planets",{}).get("Moon",{}).get("sign","Aries")
    idx_a = SIGNS.index(moon_a) if moon_a in SIGNS else 0
    idx_b = SIGNS.index(moon_b) if moon_b in SIGNS else 0

    count = ((idx_b - idx_a) % 12) + 1
    reverse = ((idx_a - idx_b) % 12) + 1

    GOOD = [1, 3, 5, 7, 9, 11]
    BAD = [2, 4, 6, 8, 10, 12]

    if count in GOOD and reverse in GOOD:
        score = 7
        label = "Highly compatible"
    elif count in GOOD or reverse in GOOD:
        score = 4
        label = "Moderately compatible"
    else:
        score = 0
        label = "Challenging — requires work"

    return {
        "name": "Bhakoot",
        "max": 7,
        "score": score,
        "a_value": moon_a,
        "b_value": moon_b,
        "dimension": "Emotional & financial flow",
        "label": label,
        "moon_distance": count,
        "match_pct": round(score / 7 * 100),
        "narrative_match": "Emotional rhythms align. Financial attitudes compatible. Growth can be built together without constant friction.",
        "narrative_work": "Emotional tidal patterns differ. One may be more expansive when the other contracts. This requires communication, not avoidance. The tension actually protects both from extremes.",
        "yin_yang": "Challenging Bhakoot pairs often have extraordinary financial creativity together — each extreme corrects the other's blind spot.",
    }

def _nadi_score(chart_a: dict, chart_b: dict) -> dict:
    """Nadi — genetic/energetic compatibility. Max 8 points."""
    nak_a = chart_a.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    nak_b = chart_b.get("planets",{}).get("Moon",{}).get("nakshatra","Ashwini")
    nadi_a = NAKSHATRA_NADI.get(nak_a, "Adi")
    nadi_b = NAKSHATRA_NADI.get(nak_b, "Madhya")

    if nadi_a == nadi_b:
        score = 0
        label = "Same Nadi — Nadi Dosha present"
    else:
        score = 8
        label = "Different Nadi — favorable"

    return {
        "name": "Nadi",
        "max": 8,
        "score": score,
        "a_value": nadi_a,
        "b_value": nadi_b,
        "dimension": "Constitutional compatibility",
        "label": label,
        "nadi_dosha": nadi_a == nadi_b,
        "match_pct": round(score / 8 * 100),
        "narrative_match": "Different Nadi channels — energetically complementary. The Vedic sages considered this the most important factor for long-term health in the relationship.",
        "narrative_work": "Same Nadi (Nadi Dosha) is the most significant challenge in Ashtakoot. Traditional remedy: perform Nadi Dosha Nivaran puja. Modern interpretation: extra attention to physical health patterns and constitutional differences.",
        "yin_yang": "Same Nadi means similar constitutional energy — less complementarity but deep understanding of each other's physical rhythms.",
    }


# ── D9 (Navamsa) Compatibility ─────────────────────────────────────────────

def _get_navamsa_sign(longitude: float) -> str:
    """Calculate Navamsa sign from tropical longitude."""
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30
    navamsa_num = int(degree_in_sign / (30 / 9))
    fire_signs = [0, 4, 8]    # Aries, Leo, Sagittarius
    earth_signs = [1, 5, 9]   # Taurus, Virgo, Capricorn
    air_signs = [2, 6, 10]    # Gemini, Libra, Aquarius
    water_signs = [3, 7, 11]  # Cancer, Scorpio, Pisces

    if sign_num in fire_signs:
        start = 0
    elif sign_num in earth_signs:
        start = 9
    elif sign_num in air_signs:
        start = 6
    else:
        start = 3

    navamsa_sign_num = (start + navamsa_num) % 12
    return SIGNS[navamsa_sign_num]

def _d9_compatibility(chart_a: dict, chart_b: dict) -> dict:
    """D9 Navamsa compatibility — soul level, deeper resonance."""
    planets_a = chart_a.get("planets", {})
    planets_b = chart_b.get("planets", {})

    results = {}
    key_planets = ["Sun","Moon","Venus","Mars","Jupiter","Saturn"]

    for planet in key_planets:
        long_a = planets_a.get(planet, {}).get("longitude", 0)
        long_b = planets_b.get(planet, {}).get("longitude", 0)
        nav_a = _get_navamsa_sign(long_a)
        nav_b = _get_navamsa_sign(long_b)
        ruler_a = SIGN_RULER.get(nav_a, "Sun")
        ruler_b = SIGN_RULER.get(nav_b, "Sun")

        if ruler_b in PLANET_FRIENDS.get(ruler_a, {}).get("friends", []):
            compat = "strong"
            score = 3
        elif ruler_b in PLANET_FRIENDS.get(ruler_a, {}).get("neutral", []):
            compat = "moderate"
            score = 2
        else:
            compat = "challenging"
            score = 1

        results[planet] = {
            "a_navamsa": nav_a,
            "b_navamsa": nav_b,
            "compatibility": compat,
            "score": score,
        }

    venus_compat = results.get("Venus", {}).get("compatibility", "moderate")
    moon_compat  = results.get("Moon",  {}).get("compatibility", "moderate")
    mars_compat  = results.get("Mars",  {}).get("compatibility", "moderate")

    total  = sum(v.get("score", 2) for v in results.values())
    max_sc = len(key_planets) * 3

    return {
        "planet_analysis": results,
        "overall_score": round(total / max_sc * 100),
        "venus_compatibility": venus_compat,
        "moon_compatibility":  moon_compat,
        "mars_compatibility":  mars_compat,
        "soul_connection": (
            "Soul-level resonance is strong — the D9 confirms what the D1 shows."
            if total / max_sc > 0.65 else
            "The D9 reveals a karmic depth beneath the surface. What appears challenging in D1 may be transformative at the soul level."
        ),
        "narrative": (
            f"At the soul level (D9 Navamsa): Venus in {results.get('Venus',{}).get('a_navamsa','?')} "
            f"meets {results.get('Venus',{}).get('b_navamsa','?')} — "
            f"{'deep romantic resonance' if venus_compat == 'strong' else 'love that requires cultivation'}. "
            f"Moon in {results.get('Moon',{}).get('a_navamsa','?')} meets {results.get('Moon',{}).get('b_navamsa','?')} — "
            f"{'natural emotional understanding' if moon_compat == 'strong' else 'emotional growth through difference'}."
        ),
    }


# ── House Analysis (1, 5, 7, 9 houses) ────────────────────────────────────

def _house_compatibility(chart_a: dict, chart_b: dict) -> dict:
    """
    Check how B's planets fall in A's houses and vice versa.
    Key houses: 1 (self/identity), 5 (love/creativity),
                7 (partnership), 9 (dharma/fortune).
    """
    planets_b = chart_b.get("planets", {})
    lagna_a   = chart_a.get("lagna",   {})
    lagna_a_sign = lagna_a.get("sign", "Aries") if isinstance(lagna_a, dict) else "Aries"
    lagna_a_idx  = SIGNS.index(lagna_a_sign) if lagna_a_sign in SIGNS else 0

    house_placements = {}
    key_houses = {1: "Identity & self", 5: "Love & creativity",
                  7: "Partnership", 9: "Dharma & fortune"}

    for planet, data in planets_b.items():
        if planet in ("Rahu","Ketu"):
            continue
        planet_sign = data.get("sign", "Aries")
        if planet_sign not in SIGNS:
            continue
        planet_sign_idx = SIGNS.index(planet_sign)
        house = ((planet_sign_idx - lagna_a_idx) % 12) + 1

        if house in key_houses:
            if house not in house_placements:
                house_placements[house] = []
            house_placements[house].append(planet)

    # Score
    score_map = {1: 70, 5: 90, 7: 95, 9: 85}
    house_scores = {}
    for house, planets in house_placements.items():
        base = score_map.get(house, 60)
        house_scores[house] = {
            "house":   house,
            "meaning": key_houses.get(house, ""),
            "planets": planets,
            "score":   base,
            "narrative": _house_narrative(house, planets),
        }

    # Check 7th house specifically
    seventh_planets = house_placements.get(7, [])
    fifth_planets   = house_placements.get(5, [])

    return {
        "house_placements": house_scores,
        "seventh_house_activation": len(seventh_planets) > 0,
        "seventh_planets": seventh_planets,
        "fifth_house_activation": len(fifth_planets) > 0,
        "fifth_planets": fifth_planets,
        "overall_score": round(sum(v["score"] for v in house_scores.values()) / max(len(house_scores), 1)),
        "narrative": _house_summary(house_placements, lagna_a_sign),
    }

def _house_narrative(house: int, planets: list) -> str:
    planet_str = ", ".join(planets) if planets else "no planets"
    narratives = {
        1: f"Their {planet_str} activates your 1st house — they directly influence your sense of self and identity. Powerful personal impact.",
        5: f"Their {planet_str} in your 5th house — this is a creative, romantic, joyful activation. They bring out your playfulness and passion.",
        7: f"Their {planet_str} sits in your 7th house of partnership — this is a profound indicator of long-term union and mutual commitment.",
        9: f"Their {planet_str} illuminates your 9th house — they expand your worldview, dharma, and fortune. A teacher-student or growth dynamic.",
    }
    return narratives.get(house, "")

def _house_summary(placements: dict, lagna: str) -> str:
    activated = list(placements.keys())
    if 7 in activated and 5 in activated:
        return "Both the 5th and 7th houses are activated — this is a rare romantic AND partnership signature. Deep love with long-term potential."
    elif 7 in activated:
        return "The 7th house is strongly activated — this is written in the partnership chart as a significant relationship."
    elif 5 in activated:
        return "The 5th house activation shows strong romantic chemistry and creative synergy."
    elif 9 in activated:
        return "The 9th house activation suggests this relationship expands both people's dharma and fortune."
    else:
        return "House activation is subtle — the relationship works through shared values and gradual deepening rather than immediate chemistry."


# ── Dasha Timing Alignment ─────────────────────────────────────────────────

def _dasha_timing_alignment(chart_a: dict, chart_b: dict,
                            birth_date_a: str, birth_date_b: str) -> dict:
    """
    Check if both people are in compatible dasha periods right now.
    Key insight: are both in expansion periods? Both in consolidation?
    Or are they out of sync?
    """
    EXPANSION_DASHAS    = ["Jupiter","Venus","Moon","Mercury"]
    CONSOLIDATION_DASHAS = ["Saturn","Ketu"]
    ACTION_DASHAS       = ["Mars","Sun","Rahu"]

    def classify_dasha(planet):
        if planet in EXPANSION_DASHAS:    return "expansion"
        if planet in CONSOLIDATION_DASHAS: return "consolidation"
        return "action"

    # Get current dasha from chart_data
    def get_current_dasha(chart_data):
        dashas = chart_data.get("current_dasha", "")
        if isinstance(dashas, str) and "-" in dashas:
            parts = dashas.split("-")
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
        return dashas, ""

    md_a, ad_a = get_current_dasha(chart_a)
    md_b, ad_b = get_current_dasha(chart_b)

    type_a = classify_dasha(md_a)
    type_b = classify_dasha(md_b)

    # Both in same type = aligned
    if type_a == type_b:
        alignment = "synchronized"
        score = 90
        narrative = (
            f"Both of you are in {type_a} energy right now — "
            f"your life chapters are moving in the same rhythm. "
            f"What you're building individually aligns with what you can build together."
        )
    elif {type_a, type_b} == {"expansion", "action"}:
        alignment = "complementary"
        score = 75
        narrative = (
            f"One of you is in expansion ({md_a}), the other in action ({md_b}). "
            f"This is a high-energy combination — the expander provides vision, "
            f"the actor executes. Classic yin-yang timing."
        )
    elif "consolidation" in [type_a, type_b]:
        alignment = "asymmetric"
        score = 55
        narrative = (
            f"One person is in a consolidation/internal period ({md_a if type_a == 'consolidation' else md_b}), "
            f"the other in active growth. "
            f"This creates a subtle tension — one wants to go deeper, one wants to expand. "
            f"Requires patience and respect for different rhythms."
        )
    else:
        alignment = "neutral"
        score = 65
        narrative = "Dasha timing is neutral — neither strongly aligned nor challenging."

    # Check if both will enter similar periods in next 5 years
    future_insight = ""
    if md_a != md_b:
        future_insight = (
            f"Watch the period when both of you enter Jupiter or Venus dasha — "
            f"those windows are the most powerful for joint growth."
        )

    return {
        "alignment":      alignment,
        "score":          score,
        "person_a_dasha": f"{md_a}-{ad_a}",
        "person_b_dasha": f"{md_b}-{ad_b}",
        "type_a":         type_a,
        "type_b":         type_b,
        "narrative":      narrative,
        "future_insight": future_insight,
        "yin_yang": (
            "Asymmetric dasha timing is not bad — it means one person's growth "
            "season is the other's reflection season. They teach each other "
            "what the other's period cannot provide alone."
        ),
    }


# ── Business-Specific Analysis ─────────────────────────────────────────────

def _business_compatibility(chart_a: dict, chart_b: dict) -> dict:
    """
    Additional layer for business partnerships.
    Mercury (deals), Jupiter (trust/growth), Saturn (commitment),
    10th house (career), 11th house (gains).
    """
    planets_a = chart_a.get("planets", {})
    planets_b = chart_b.get("planets", {})

    # Mercury compatibility (communication, contracts)
    merc_a = planets_a.get("Mercury", {}).get("sign", "Gemini")
    merc_b = planets_b.get("Mercury", {}).get("sign", "Gemini")
    merc_ruler_a = SIGN_RULER.get(merc_a, "Mercury")
    merc_ruler_b = SIGN_RULER.get(merc_b, "Mercury")

    if merc_ruler_b in PLANET_FRIENDS.get(merc_ruler_a, {}).get("friends", []) or merc_a == merc_b:
        comm_score = 90
        comm_label = "Excellent"
        comm_narrative = "Communication styles are naturally compatible. Contracts and negotiations will flow well."
    elif merc_ruler_b in PLANET_FRIENDS.get(merc_ruler_a, {}).get("neutral", []):
        comm_score = 65
        comm_label = "Good"
        comm_narrative = "Communication works well with some adaptation. Agree on communication channels early."
    else:
        comm_score = 40
        comm_label = "Needs structure"
        comm_narrative = "Very different communication styles. Build in structured communication protocols — weekly reviews, written agreements. The friction can be productive if channeled."

    # Jupiter compatibility (trust, expansion)
    jup_a = planets_a.get("Jupiter", {}).get("sign", "Sagittarius")
    jup_b = planets_b.get("Jupiter", {}).get("sign", "Sagittarius")
    jup_score = 85 if SIGN_RULER.get(jup_a) == SIGN_RULER.get(jup_b) else 65

    # Saturn compatibility (long-term commitment, structure)
    sat_a = planets_a.get("Saturn", {}).get("sign", "Capricorn")
    sat_b = planets_b.get("Saturn", {}).get("sign", "Capricorn")
    sat_compat = abs(SIGNS.index(sat_a if sat_a in SIGNS else "Capricorn") -
                     SIGNS.index(sat_b if sat_b in SIGNS else "Capricorn"))
    sat_score = 90 if sat_compat in [0, 6] else 70 if sat_compat in [3, 9] else 55

    overall_biz = round((comm_score + jup_score + sat_score) / 3)

    return {
        "overall_score": overall_biz,
        "communication": {
            "score":     comm_score,
            "label":     comm_label,
            "narrative": comm_narrative,
        },
        "trust_expansion": {
            "score":     jup_score,
            "narrative": "Strong shared vision for growth." if jup_score >= 75 else "Different growth philosophies — complement each other if roles are clearly defined.",
        },
        "long_term_structure": {
            "score":     sat_score,
            "narrative": "Compatible long-term commitment patterns." if sat_score >= 70 else "Different approaches to structure and commitment. Put everything in writing.",
        },
        "best_contract_window": "Look for Jupiter-Jupiter transits for signing agreements — typically March-April and September-October windows.",
        "role_suggestion": _suggest_business_roles(chart_a, chart_b),
    }

def _suggest_business_roles(chart_a: dict, chart_b: dict) -> dict:
    """Suggest complementary business roles based on dominant planets."""
    def dominant_planet(chart):
        planets = chart.get("planets", {})
        # Simple heuristic: lagna lord
        lagna = chart.get("lagna", {})
        lagna_sign = lagna.get("sign", "Aries") if isinstance(lagna, dict) else "Aries"
        return SIGN_RULER.get(lagna_sign, "Sun")

    ROLE_MAP = {
        "Sun":     "Visionary CEO / Public face / Leadership",
        "Moon":    "Customer relations / HR / Culture / Nurturing the team",
        "Mars":    "Operations / Execution / Sales / Business development",
        "Mercury": "Strategy / Communications / Marketing / Negotiations",
        "Jupiter": "Advisory / Mentoring / Legal / Finance / Expansion",
        "Venus":   "Creative direction / Brand / Design / Partnerships",
        "Saturn":  "Administration / Systems / Long-term planning / COO",
        "Rahu":    "Innovation / Technology / Foreign markets / Disruption",
        "Ketu":    "Research / Specialized expertise / Behind-the-scenes",
    }

    dom_a = dominant_planet(chart_a)
    dom_b = dominant_planet(chart_b)

    return {
        "person_a_strength": ROLE_MAP.get(dom_a, "Leadership"),
        "person_b_strength": ROLE_MAP.get(dom_b, "Operations"),
        "complementary": dom_a != dom_b,
        "note": (
            f"Person A's {dom_a} energy suggests {ROLE_MAP.get(dom_a,'leadership')} strength. "
            f"Person B's {dom_b} energy suggests {ROLE_MAP.get(dom_b,'operations')} strength. "
            + ("These are complementary — clear role division will maximize both." if dom_a != dom_b
               else "Same dominant energy — guard against blind spots you both share. Bring in advisors with different planetary signatures.")
        ),
    }


# ── Yin-Yang Psychology Analysis ──────────────────────────────────────────

def _yin_yang_analysis(chart_a: dict, chart_b: dict) -> dict:
    """
    Identify where opposites attract and create growth.
    Reverse psychology: differences are features, not bugs.
    """
    planets_a = chart_a.get("planets", {})
    planets_b = chart_b.get("planets", {})

    insights = []

    # Check for opposite/complementary planet emphasis
    for (p1, p2), description in YIN_YANG_PAIRS.items():
        # Check if A has p1 prominent and B has p2 prominent (or vice versa)
        has_a_p1 = planets_a.get(p1, {}).get("sign") is not None
        has_b_p2 = planets_b.get(p2, {}).get("sign") is not None
        if has_a_p1 and has_b_p2:
            insights.append({
                "pair": f"{p1}-{p2}",
                "description": description,
                "type": "growth_through_difference",
            })

    # Moon sign polarity
    moon_a = planets_a.get("Moon", {}).get("sign", "Aries")
    moon_b = planets_b.get("Moon", {}).get("sign", "Aries")
    if moon_a in SIGNS and moon_b in SIGNS:
        idx_a = SIGNS.index(moon_a)
        idx_b = SIGNS.index(moon_b)
        if abs(idx_a - idx_b) == 6:
            insights.append({
                "pair": f"{moon_a}-{moon_b} Moon",
                "description": "Opposite Moon signs — the most intense emotional polarity in Vedic astrology. You feel what the other cannot. This is profound complementarity.",
                "type": "moon_opposition",
            })

    # Lagna compatibility
    lagna_a_sign = (chart_a.get("lagna", {}) or {}).get("sign", "Aries")
    lagna_b_sign = (chart_b.get("lagna", {}) or {}).get("sign", "Aries")
    if lagna_a_sign in SIGNS and lagna_b_sign in SIGNS:
        la_idx = SIGNS.index(lagna_a_sign)
        lb_idx = SIGNS.index(lagna_b_sign)
        if abs(la_idx - lb_idx) == 6:
            insights.append({
                "pair": f"{lagna_a_sign}-{lagna_b_sign} Lagna",
                "description": "Opposite rising signs — you present to the world in complementary ways. One is the other's mirror for how they appear to the world.",
                "type": "lagna_opposition",
            })

    growth_areas = []
    if not insights:
        growth_areas.append("This pairing has more harmony than opposition — the growth comes from depth rather than friction.")

    return {
        "yin_yang_pairs": insights[:3],
        "growth_areas": growth_areas,
        "core_message": (
            "The places where you are most different are not problems to solve — "
            "they are the exact locations where you help each other grow. "
            "The Vedic tradition calls this 'Kshema' — the sheltering of each other's weaknesses."
        ),
    }


# ── Master Compatibility Function ─────────────────────────────────────────

def calculate_compatibility(
    chart_a: dict,
    chart_b: dict,
    name_a: str = "Person A",
    name_b: str = "Person B",
    birth_date_a: str = "",
    birth_date_b: str = "",
    compatibility_type: str = "relationship",  # 'relationship' | 'business'
    language: str = "en",
) -> dict:
    """
    Master compatibility calculation.
    Returns comprehensive compatibility report with:
    - Ashtakoot score (D1)
    - D9 Navamsa overlay
    - House analysis (1,5,7,9)
    - Dasha timing alignment
    - Business analysis (if type=business)
    - Yin-yang psychology
    - Overall % match with narrative
    """

    # ── Ashtakoot ──────────────────────────────────────────────
    varna   = _varna_score(chart_a, chart_b)
    vashya  = _vashya_score(chart_a, chart_b)
    tara    = _tara_score(chart_a, chart_b)
    yoni    = _yoni_score(chart_a, chart_b)
    graha   = _graha_maitri_score(chart_a, chart_b)
    gana    = _gana_score(chart_a, chart_b)
    bhakoot = _bhakoot_score(chart_a, chart_b)
    nadi    = _nadi_score(chart_a, chart_b)

    ashta_components = [varna,vashya,tara,yoni,graha,gana,bhakoot,nadi]
    ashta_total  = sum(c["score"] for c in ashta_components)
    ashta_max    = sum(c["max"]   for c in ashta_components)
    ashta_pct    = round(ashta_total / ashta_max * 100)

    # ── D9 ─────────────────────────────────────────────────────
    d9 = _d9_compatibility(chart_a, chart_b)

    # ── House analysis (A's perspective + B's perspective) ────
    house_ab = _house_compatibility(chart_a, chart_b)
    house_ba = _house_compatibility(chart_b, chart_a)

    # ── Dasha timing ───────────────────────────────────────────
    dasha_timing = _dasha_timing_alignment(
        chart_a, chart_b, birth_date_a, birth_date_b
    )

    # ── Yin-yang ───────────────────────────────────────────────
    yin_yang = _yin_yang_analysis(chart_a, chart_b)

    # ── Business layer ─────────────────────────────────────────
    biz = _business_compatibility(chart_a, chart_b) \
          if compatibility_type == "business" else None

    # ── Weighted overall score ─────────────────────────────────
    weights = {
        "ashtakoot":   0.35,
        "d9":          0.20,
        "houses":      0.20,
        "dasha":       0.15,
        "yin_yang":    0.10,
    }
    house_score = round((house_ab["overall_score"] + house_ba["overall_score"]) / 2)

    overall_pct = round(
        ashta_pct            * weights["ashtakoot"] +
        d9["overall_score"]  * weights["d9"]        +
        house_score          * weights["houses"]     +
        dasha_timing["score"]* weights["dasha"]      +
        70                   * weights["yin_yang"]
    )
    overall_pct = min(98, max(20, overall_pct))

    # ── Narrative interpretation ───────────────────────────────
    if overall_pct >= 80:
        overall_label   = "Exceptional alignment"
        overall_headline = f"{overall_pct}% — A rare configuration. Both the conscious and soul-level charts agree."
        overall_message  = (
            f"{name_a} and {name_b} carry a pattern that the Vedic system recognizes "
            f"as genuinely rare. The Ashtakoot score of {ashta_total}/{ashta_max} places you "
            f"in the top tier of compatibility. More importantly, the D9 Navamsa confirms "
            f"what the surface chart shows — this resonance runs deeper than circumstance."
        )
    elif overall_pct >= 65:
        overall_label    = "Strong foundation"
        overall_headline = f"{overall_pct}% — Strong alignment with clear growth edges."
        overall_message  = (
            f"The pattern between {name_a} and {name_b} shows a solid foundation with "
            f"specific areas of productive friction. The {ashta_total}/{ashta_max} Ashtakoot score "
            f"indicates genuine compatibility. The areas that score lower are not problems — "
            f"they are the exact places where you help each other grow."
        )
    elif overall_pct >= 50:
        overall_label    = "Growth relationship"
        overall_headline = f"{overall_pct}% — A relationship built for transformation."
        overall_message  = (
            f"The chart between {name_a} and {name_b} shows a relationship that will not "
            f"feel easy — it will feel necessary. The Ashtakoot of {ashta_total}/{ashta_max} "
            f"indicates more growth energy than comfort energy. History's most transformative "
            f"partnerships score in this range. The question is not 'are we compatible' "
            f"but 'are we both ready to grow?'"
        )
    else:
        overall_label    = "Karmic connection"
        overall_headline = f"{overall_pct}% — Deeply karmic, intensely growth-oriented."
        overall_message  = (
            f"A low Ashtakoot ({ashta_total}/{ashta_max}) does not mean wrong — it means "
            f"this is a karmic relationship that carries significant past-life energy. "
            f"These relationships are the most intense, the most transformative, and "
            f"require the most conscious navigation. They are not accidents."
        )

    # ── What will flow / What needs work ──────────────────────
    strengths = []
    growth_areas = []

    for comp in ashta_components:
        pct = comp["match_pct"]
        if pct >= 75:
            strengths.append({
                "dimension": comp["dimension"],
                "score": pct,
                "narrative": comp["narrative_match"],
            })
        elif pct <= 40:
            growth_areas.append({
                "dimension": comp["dimension"],
                "score": pct,
                "narrative": comp["narrative_work"],
                "yin_yang": comp.get("yin_yang", ""),
            })

    # Add dasha timing to appropriate section
    if dasha_timing["score"] >= 75:
        strengths.append({
            "dimension": "Life timing",
            "score": dasha_timing["score"],
            "narrative": dasha_timing["narrative"],
        })
    else:
        growth_areas.append({
            "dimension": "Life timing",
            "score": dasha_timing["score"],
            "narrative": dasha_timing["narrative"],
            "yin_yang": dasha_timing["yin_yang"],
        })

    return {
        "overall": {
            "score_pct":  overall_pct,
            "label":      overall_label,
            "headline":   overall_headline,
            "message":    overall_message,
        },
        "ashtakoot": {
            "total":      ashta_total,
            "max":        ashta_max,
            "score_pct":  ashta_pct,
            "components": ashta_components,
        },
        "d9_navamsa":   d9,
        "house_analysis": {
            "a_perspective": house_ab,
            "b_perspective": house_ba,
        },
        "dasha_timing":  dasha_timing,
        "yin_yang":      yin_yang,
        "business":      biz,
        "strengths":     strengths[:4],
        "growth_areas":  growth_areas[:4],
        "five_dimensions": {
            "mind_connection":     graha["match_pct"],
            "emotional_resonance": bhakoot["match_pct"],
            "physical_harmony":    yoni["match_pct"],
            "life_timing":         dasha_timing["score"],
            "soul_depth":          d9["overall_score"],
        },
        "names": {"a": name_a, "b": name_b},
        "compatibility_type": compatibility_type,
    }
