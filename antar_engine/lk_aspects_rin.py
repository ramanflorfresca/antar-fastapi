"""
Lal Kitab Aspects and Rin (Debt) Rules
=======================================
TWO SYSTEMS — both unique to Lal Kitab, not in standard Parashari:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM 1 — LAL KITAB ASPECTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In Parashari every planet aspects the 7th house from itself.
Lal Kitab has DIFFERENT aspect rules — more complex, house-specific:

  - Every planet aspects the house directly OPPOSITE (7th from it) — same as Parashari
  - PLUS special aspects unique to each planet:
      Sun    → also aspects H4, H5, H9, H10 from its house
      Moon   → also aspects H5, H7 from its house (and receives from H7)
      Mars   → special aspects H4, H8 from its house
      Mercury→ aspects H4, H7 from its house
      Jupiter→ special aspects H5, H7, H9 from its house (same as Parashari)
      Venus  → aspects H3, H7 from its house
      Saturn → special aspects H3, H10 from its house
      Rahu   → aspects H5, H9 from its house
      Ketu   → aspects H5, H9 from its house (mirror of Rahu)

  KEY LALKITAB RULE: When a planet aspects a house, it "sees" and influences
  that house. The nature of influence depends on:
    - Whether the aspecting planet is friendly or enemy to house lord
    - Whether the house is empty or occupied
    - The strength of the aspecting planet

  CRITICAL LALKITAB ASPECT RULES:
    - Planet in H1 aspects H4, H5, H7, H9, H10 (Sun case — strongest lagna placement)
    - Saturn in H1 aspects H3, H7, H10 — restricts these house matters
    - Rahu aspects are considered malefic — they "smoke out" the houses they touch
    - Jupiter aspects are always protective — houses Jupiter sees are shielded
    - Enemy planets aspecting each other = tension, conflict in life areas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM 2 — RIN (ANCESTRAL DEBT) RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rin = debt. Lal Kitab identifies three categories of ancestral/karmic debt
based on specific planetary combinations in the chart:

  Pitru Rin (Father's Debt):
    - Sun weak/afflicted + Saturn afflicting H1/H4/H9
    - Sun in H6, H8, or H12
    - Ketu in H5 or H9 (breaks blessings from father line)
    
  Matru Rin (Mother's Debt):
    - Moon weak/afflicted (debilitated or in enemy sign)
    - Moon in H6 or H8
    - Rahu aspecting Moon or H4 (mother's house)
    
  Stri Rin (Spouse/Female Debt) — includes past-life partner karma:
    - Venus afflicted by Saturn or Rahu
    - Venus in H6, H8, or H12
    - 7th house afflicted by 2+ malefics
    - Mars + Venus in same house (Mangal Dosh modifier)
    
  Bhatru Rin (Sibling Debt):
    - Mars debilitated or in H8/H12
    - 3rd lord afflicted by Saturn/Rahu
    
  Putra Rin (Children Debt):
    - Jupiter debilitated or in H6/H8/H12
    - 5th lord with Saturn or Rahu
    - Ketu in H5 (most classic Putra Rin indicator)

RIN REMEDIES in Lal Kitab are specific rituals to clear ancestral debt.
They are different from planetary remedies — they target the lineage, not the planet.

For Antar purposes we surface: "You carry [X] debt in your chart. 
This is why [career/marriage/children] has faced [specific pattern].
Here is the remedy."
"""

from __future__ import annotations
from typing import List, Dict


# ── LAL KITAB ASPECT TABLE ────────────────────────────────────────────────────
# planet → list of houses it aspects (counted FROM its own house, inclusive of 7th)
# e.g. Sun aspects 4th, 5th, 7th, 9th, 10th from its position

LK_ASPECTS_FROM_PLANET = {
    # (houses from planet's house that it aspects, 7 always included)
    "Sun":     [4, 5, 7, 9, 10],
    "Moon":    [5, 7],
    "Mars":    [4, 7, 8],
    "Mercury": [4, 7],
    "Jupiter": [5, 7, 9],
    "Venus":   [3, 7],
    "Saturn":  [3, 7, 10],
    "Rahu":    [5, 7, 9],
    "Ketu":    [5, 7, 9],
}

# Natural friendships (for aspect quality assessment)
NATURAL_FRIENDS = {
    "Sun":     ["Moon", "Mars", "Jupiter"],
    "Moon":    ["Sun", "Mercury"],
    "Mars":    ["Sun", "Moon", "Jupiter"],
    "Mercury": ["Sun", "Venus"],
    "Jupiter": ["Sun", "Moon", "Mars"],
    "Venus":   ["Mercury", "Saturn"],
    "Saturn":  ["Mercury", "Venus"],
    "Rahu":    ["Saturn", "Mercury", "Venus"],
    "Ketu":    ["Mars", "Venus", "Saturn"],
}
NATURAL_ENEMIES = {
    "Sun":     ["Venus", "Saturn"],
    "Moon":    ["None"],
    "Mars":    ["Mercury"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"],
    "Venus":   ["Sun", "Moon"],
    "Saturn":  ["Sun", "Moon", "Mars"],
    "Rahu":    ["Sun", "Moon", "Mars"],
    "Ketu":    ["Sun", "Moon"],
}

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS  = {"Moon", "Mercury", "Jupiter", "Venus"}


def _planet_house(chart_data: dict, planet: str) -> int:
    return chart_data.get("planets", {}).get(planet, {}).get("house", 0)

def _planets_in_house(chart_data: dict, house: int) -> List[str]:
    return [p for p, d in chart_data.get("planets", {}).items()
            if d.get("house", 0) == house]

def _planet_sign_index(chart_data: dict, planet: str) -> int:
    return chart_data.get("planets", {}).get(planet, {}).get("sign_index", -1)

def _is_debilitated(chart_data: dict, planet: str) -> bool:
    DEBIT = {"Sun":6,"Moon":7,"Mars":3,"Mercury":11,"Jupiter":9,"Venus":5,"Saturn":0}
    return _planet_sign_index(chart_data, planet) == DEBIT.get(planet, -1)

def _is_strong(chart_data: dict, planet: str) -> bool:
    OWN   = {"Sun":[4],"Moon":[3],"Mars":[0,7],"Mercury":[2,5],
             "Jupiter":[8,11],"Venus":[1,6],"Saturn":[9,10]}
    EXALT = {"Sun":0,"Moon":1,"Mars":9,"Mercury":5,"Jupiter":3,"Venus":11,"Saturn":6}
    si = _planet_sign_index(chart_data, planet)
    return si in OWN.get(planet,[]) or si == EXALT.get(planet,-1)

def _aspects_house(aspector: str, aspector_house: int, target_house: int) -> bool:
    """Does aspector in aspector_house aspect target_house?"""
    offsets = LK_ASPECTS_FROM_PLANET.get(aspector, [7])
    for offset in offsets:
        if ((aspector_house + offset - 1 - 1) % 12) + 1 == target_house:
            return True
    return False

def _get_aspectees_of(chart_data: dict, planet: str) -> List[int]:
    """Return list of houses that this planet aspects."""
    house = _planet_house(chart_data, planet)
    if not house:
        return []
    offsets = LK_ASPECTS_FROM_PLANET.get(planet, [7])
    return [((house + o - 1 - 1) % 12) + 1 for o in offsets]


# ── ASPECT SIGNAL RULES ───────────────────────────────────────────────────────

# Format: (aspector, aspected_house): signal dict
# We cover the most impactful combinations:
#   Saturn aspects → restriction / karma in that house
#   Jupiter aspects → protection / expansion in that house
#   Rahu aspects   → obsession / amplification + disruption
#   Mars aspects   → energy / aggression / conflict in that house
#   Ketu aspects   → detachment / past-life completion in that house

LK_ASPECT_RULES: Dict[tuple, dict] = {

    # ── SATURN ASPECTS ─────────────────────────────────────────
    ("Saturn", 1): {"domain":"health","confidence":0.82,"is_pain":True,
        "prediction":"Saturn aspects your ascendant — your identity and physical body carry Saturn's weight. Life begins with extra difficulty but builds exceptional resilience. Chronic health patterns need proactive management. This aspect produces profound discipline when worked with consciously.",
        "warning":"Health routines, sleep, and physical structure are non-negotiable — not optional self-care."},

    ("Saturn", 7): {"domain":"marriage","confidence":0.83,"is_pain":True,
        "prediction":"Saturn aspects your 7th house — marriage and partnerships are delayed, tested, or carry karmic weight. The right partner arrives late but is exceptionally durable. Business partnerships require written agreements — verbal trust is not enough.",
        "warning":"Don't rush into marriage under social pressure. Saturn in 7th aspect rewards patience with lifetime partnership quality."},

    ("Saturn", 4): {"domain":"family","confidence":0.80,"is_pain":True,
        "prediction":"Saturn aspects your 4th house — home and domestic life carry restriction and karmic learning. Property acquisition is delayed. The relationship with mother or homeland involves difficulty that eventually deepens both parties.",
        "warning":"Real estate investments need extra legal due diligence under this aspect."},

    ("Saturn", 10): {"domain":"career","confidence":0.85,"is_pain":False,
        "prediction":"Saturn aspects your 10th house — this is one of Lal Kitab's most powerful career aspect combinations. Career rises through discipline, hard work, and authority. Recognition comes after 35 but becomes unshakeable. Government, structured institutions, and senior roles are supported.",
        "warning":""},

    ("Saturn", 5): {"domain":"children","confidence":0.78,"is_pain":True,
        "prediction":"Saturn aspects your 5th house — children and creative intelligence face Saturn's restriction. Children may come late or require extra care. Creative work benefits from structure over spontaneity.",
        "warning":"If children are desired, address Saturn's placement through remedies before attempting conception."},

    ("Saturn", 9): {"domain":"spiritual","confidence":0.78,"is_pain":True,
        "prediction":"Saturn aspects your 9th house — luck and father's blessings carry karma and delay. Fortune arrives through hard work, not divine grace. The spiritual path involves serious practice, not easy faith.",
        "warning":""},

    # ── JUPITER ASPECTS ─────────────────────────────────────────
    ("Jupiter", 1): {"domain":"health","confidence":0.88,"is_pain":False,
        "prediction":"Jupiter aspects your ascendant — your personality and body are protected and expanded by Jupiter's wisdom. Natural optimism, good health recovery, and a magnetic presence. This aspect brings teachers, guides, and helpers throughout life.",
        "warning":""},

    ("Jupiter", 5): {"domain":"children","confidence":0.90,"is_pain":False,
        "prediction":"Jupiter aspects your 5th house — children, creativity, and intelligence are strongly blessed. Children bring joy and carry spiritual advancement. Creative intelligence is a soul-level gift. Education and teaching are natural strengths.",
        "warning":""},

    ("Jupiter", 7): {"domain":"marriage","confidence":0.88,"is_pain":False,
        "prediction":"Jupiter aspects your 7th house — marriage and partnerships receive Jupiter's full blessing. The spouse brings wisdom, expansion, and prosperity. Business partnerships are protected. Legal matters involving partnerships tend to resolve fairly.",
        "warning":""},

    ("Jupiter", 9): {"domain":"spiritual","confidence":0.90,"is_pain":False,
        "prediction":"Jupiter aspects your 9th house — fortune, higher wisdom, and dharma are powerfully blessed. Good luck is genuine and recurring. Spiritual practice brings tangible results. The father's blessings are strong. Teachers and guides appear when needed.",
        "warning":""},

    ("Jupiter", 4): {"domain":"family","confidence":0.85,"is_pain":False,
        "prediction":"Jupiter aspects your 4th house — home, mother, and domestic life are blessed with expansion and harmony. Property acquisition is supported. The home environment brings growth and happiness. Mother is a source of wisdom.",
        "warning":""},

    # ── RAHU ASPECTS ─────────────────────────────────────────────
    ("Rahu", 5): {"domain":"career","confidence":0.80,"is_pain":True,
        "prediction":"Rahu aspects your 5th house — creative intelligence is amplified but unstable. Brilliant unconventional ideas emerge, but speculative risk-taking can destroy gains. Children's matters carry karmic complexity. Technology and innovative thinking are highlighted.",
        "warning":"NEVER speculate with borrowed money. Rahu's 5th aspect supercharges creativity but equally amplifies gambling losses."},

    ("Rahu", 7): {"domain":"marriage","confidence":0.80,"is_pain":True,
        "prediction":"Rahu aspects your 7th house — partnerships are karmic, intense, and unconventional. The spouse may be from a different background or bring surprise. Business partnerships carry hidden agendas — investigate thoroughly before committing.",
        "warning":"Prenuptial agreements and written business contracts are specifically protective under Rahu's 7th aspect."},

    ("Rahu", 9): {"domain":"spiritual","confidence":0.78,"is_pain":True,
        "prediction":"Rahu aspects your 9th house — spiritual path is unconventional, foreign, or breaks from tradition. Fortune comes through unusual channels. The father's lineage carries disruption or departure from convention.",
        "warning":"Be cautious about unorthodox teachers who promise shortcuts to wisdom."},

    ("Rahu", 1): {"domain":"health","confidence":0.82,"is_pain":True,
        "prediction":"Rahu aspects your ascendant — your identity is subject to amplification, illusion, and reinvention. Strong ambition and unusual appearance or personality. Foreign lands, technology, and unconventional paths are naturally drawn to you.",
        "warning":"Ground spiritual and mental health practices are specifically protective — Rahu on lagna creates identity confusion without anchoring."},

    # ── MARS ASPECTS ─────────────────────────────────────────────
    ("Mars", 4): {"domain":"family","confidence":0.80,"is_pain":True,
        "prediction":"Mars aspects your 4th house — home environment carries tension, conflict, or excessive energy. Real estate disputes are possible. Mother's health may need attention. Channel Mars's 4th aspect into home renovation and physical improvement of living space.",
        "warning":"Avoid aggressive communication at home. Mars in 4H aspect needs a physical outlet — not emotional confrontation."},

    ("Mars", 7): {"domain":"marriage","confidence":0.82,"is_pain":True,
        "prediction":"Mars aspects your 7th house — Mangal (Kuja) Dosh in full effect. Marriage carries intensity, conflict potential, and high passion simultaneously. The spouse is strong-willed. Relationships require active conflict resolution skills.",
        "warning":"Mangal Dosh: matching with a partner who also has Mars in 1/4/7/8/12 neutralizes this combination. Consult a Lal Kitab practitioner before marriage commitment."},

    ("Mars", 8): {"domain":"health","confidence":0.80,"is_pain":True,
        "prediction":"Mars aspects your 8th house — sudden events, surgical procedures, and transformation through crisis are more likely. This is also Mars's most investigative, research-oriented energy. Hidden matters come to light forcefully.",
        "warning":"Life insurance, health screenings, and emergency preparedness are specifically recommended under this aspect."},

    ("Mars", 1): {"domain":"health","confidence":0.78,"is_pain":True,
        "prediction":"Mars aspects your ascendant — physical aggression, high energy, and impulsive action define the body-mind interface. Accidents and inflammation are more likely. Channel this energy into regular intense physical exercise or it redirects as anger.",
        "warning":"Never skip physical exercise under this aspect. Mars on lagna REQUIRES a physical outlet."},

    # ── KETU ASPECTS ─────────────────────────────────────────────
    ("Ketu", 5): {"domain":"children","confidence":0.78,"is_pain":True,
        "prediction":"Ketu aspects your 5th house — past-life karmic completion around children and creative intelligence. Children may arrive after spiritual work or carry unusual destiny. Creative gifts are spiritually oriented rather than commercially motivated.",
        "warning":""},

    ("Ketu", 9): {"domain":"spiritual","confidence":0.82,"is_pain":False,
        "prediction":"Ketu aspects your 9th house — profound past-life spiritual accumulation is carried into this life. The dharmic path is intuitive rather than prescribed. Foreign or cross-cultural wisdom traditions resonate deeply. Fortune comes through surrendering control.",
        "warning":""},

    ("Ketu", 7): {"domain":"marriage","confidence":0.78,"is_pain":True,
        "prediction":"Ketu aspects your 7th house — partnership karma from past lives. Relationships have a fated quality. The soul is completing a partnership cycle — either deep reunion or conscious dissolution. Spiritual partnerships are more fulfilling than conventional marriages.",
        "warning":""},

    # ── SUN ASPECTS ───────────────────────────────────────────────
    ("Sun", 4): {"domain":"family","confidence":0.80,"is_pain":False,
        "prediction":"Sun aspects your 4th house — home and family carry solar authority and pride. Real estate and family legacy are highlighted. The father's influence on home life is strong. Government-related property transactions are supported.",
        "warning":"Don't dominate family dynamics — Sun in 4H aspect benefits from sharing authority rather than centralizing it."},

    ("Sun", 5): {"domain":"career","confidence":0.83,"is_pain":False,
        "prediction":"Sun aspects your 5th house — creative intelligence and leadership are solar gifts. Teaching, performing, and leading are natural. Children carry father's pride and ambition. Speculative ventures in government or authority-related fields can succeed.",
        "warning":""},

    ("Sun", 9): {"domain":"spiritual","confidence":0.85,"is_pain":False,
        "prediction":"Sun aspects your 9th house — father's blessings and fortune are strongly supported. Dharma, religion, and higher education carry solar energy. Government sponsorship or authority-backed educational advancement is possible.",
        "warning":""},

    ("Sun", 10): {"domain":"career","confidence":0.88,"is_pain":False,
        "prediction":"Sun aspects your 10th house — career authority and public recognition are solar gifts. Government roles, leadership positions, and institutional authority are naturally supported. Your professional reputation is built on genuine competence and confidence.",
        "warning":""},

    # ── VENUS ASPECTS ─────────────────────────────────────────────
    ("Venus", 3): {"domain":"career","confidence":0.80,"is_pain":False,
        "prediction":"Venus aspects your 3rd house — communication, creative writing, and sibling relationships carry Venusian beauty and diplomacy. Artistic communication — writing, speaking, performing — is a natural gift. The relationship with siblings (especially sisters) is warm.",
        "warning":""},

    ("Venus", 7): {"domain":"marriage","confidence":0.88,"is_pain":False,
        "prediction":"Venus aspects your 7th house — marriage and partnerships receive Venus's full blessing. The spouse is beautiful, artistic, or deeply loving. Romantic and business partnerships flourish. Luxury, harmony, and aesthetic pleasure in relationships are natural.",
        "warning":""},
}


# ── RIN (ANCESTRAL DEBT) RULES ────────────────────────────────────────────────

def detect_pitru_rin(chart_data: dict) -> dict | None:
    """
    Pitru Rin = Father's Debt / Ancestral male-line debt.
    Indicators: Sun weak/afflicted; Ketu in H5 or H9; Saturn afflicting H9.
    """
    sun_house   = _planet_house(chart_data, "Sun")
    ketu_house  = _planet_house(chart_data, "Ketu")
    saturn_house= _planet_house(chart_data, "Saturn")
    sun_weak    = _is_debilitated(chart_data, "Sun")

    # Sun in pain houses
    sun_in_pain = sun_house in (6, 8, 12)

    # Ketu in dharma houses
    ketu_in_dharma = ketu_house in (5, 9)

    # Saturn aspecting 9H (father/fortune house)
    saturn_aspects_9 = _aspects_house("Saturn", saturn_house, 9) if saturn_house else False

    # Multiple afflictions to H9 — who occupies it
    h9_planets = _planets_in_house(chart_data, 9)
    h9_malefics = [p for p in h9_planets if p in MALEFICS]

    score = sum([sun_weak, sun_in_pain, ketu_in_dharma, saturn_aspects_9, len(h9_malefics) >= 2])

    if score < 1:
        return None

    return {
        "rin_type":   "Pitru Rin",
        "rin_hindi":  "पितृ ऋण",
        "domain":     "spiritual",
        "confidence": 0.70 + score * 0.05,
        "indicators": {
            "sun_weak":          sun_weak,
            "sun_in_pain_house": sun_in_pain,
            "ketu_in_dharma":    ketu_in_dharma,
            "saturn_aspects_9":  saturn_aspects_9,
            "h9_malefics":       h9_malefics,
        },
        "prediction": (
            "Pitru Rin (Father's Ancestral Debt) is indicated in your chart. "
            "This is not a curse — it is an unresolved karmic account from the paternal lineage "
            "that your soul agreed to balance. The pattern shows as: obstacles that seem "
            "disproportionate to effort, delayed fortune, or a complicated relationship with "
            "father figures and authority. The debt predates you — it belongs to the lineage."
        ),
        "life_pattern": (
            "Career recognition comes later than deserved. Father relationship is complex. "
            "Fortune requires more effort than peers seem to need."
        ),
        "remedy": (
            "Lal Kitab Pitru Rin Remedy: "
            "(1) Feed crows every Saturday — crows represent Saturn/ancestors in Lal Kitab. "
            "(2) Offer water to the Sun at sunrise every day while reciting your father's name. "
            "(3) Perform Pitru Tarpan (ancestral offering) on Amavasya (new moon) — "
            "can be done with simple water and black sesame. "
            "(4) Plant a peepal tree or donate to maintain one. "
            "Doing these for 43 consecutive days creates a noticeable shift."
        ),
        "is_pain_signal": True,
        "rule_id": "RIN_PITRU",
    }


def detect_matru_rin(chart_data: dict) -> dict | None:
    """
    Matru Rin = Mother's Debt / Female ancestral line debt.
    Indicators: Moon weak/afflicted; Rahu aspecting Moon or H4; Moon in H6/H8.
    """
    moon_house   = _planet_house(chart_data, "Moon")
    rahu_house   = _planet_house(chart_data, "Rahu")
    moon_weak    = _is_debilitated(chart_data, "Moon")
    moon_in_pain = moon_house in (6, 8, 12)

    # Rahu aspecting Moon's house
    rahu_aspects_moon = _aspects_house("Rahu", rahu_house, moon_house) if rahu_house and moon_house else False

    # Rahu in or aspecting H4 (mother's house)
    rahu_in_h4        = rahu_house == 4
    rahu_aspects_h4   = _aspects_house("Rahu", rahu_house, 4) if rahu_house else False

    # Saturn in H4
    saturn_in_h4 = _planet_house(chart_data, "Saturn") == 4

    score = sum([moon_weak, moon_in_pain, rahu_aspects_moon,
                 rahu_in_h4 or rahu_aspects_h4, saturn_in_h4])

    if score < 1:
        return None

    return {
        "rin_type":   "Matru Rin",
        "rin_hindi":  "मातृ ऋण",
        "domain":     "health",
        "confidence": 0.70 + score * 0.05,
        "indicators": {
            "moon_weak":         moon_weak,
            "moon_in_pain":      moon_in_pain,
            "rahu_aspects_moon": rahu_aspects_moon,
            "rahu_near_h4":      rahu_in_h4 or rahu_aspects_h4,
            "saturn_in_h4":      saturn_in_h4,
        },
        "prediction": (
            "Matru Rin (Mother's Ancestral Debt) is present in your chart. "
            "This manifests as patterns of emotional insecurity, difficulty receiving nurturing, "
            "or a complicated relationship with the mother or maternal figures. "
            "Mental peace and domestic stability require more conscious effort than for most people. "
            "The debt belongs to the maternal lineage — your soul is completing what was left unresolved."
        ),
        "life_pattern": (
            "Emotional turbulence that seems rooted in early life. "
            "Home and domestic happiness require sustained effort. "
            "Relationship with mother may be loving but complicated."
        ),
        "remedy": (
            "Lal Kitab Matru Rin Remedy: "
            "(1) Serve your mother or any elderly woman — feed her, give her white clothing. "
            "(2) Keep a silver glass of water on your bedside table — pour it at a tree root each morning. "
            "(3) On Mondays, offer white flowers and milk at a Shiva temple. "
            "(4) Feed white cows with rice and jaggery for 11 Mondays. "
            "(5) Most important: never criticize your mother, even silently. "
            "The remedy works through genuine respect, not just ritual."
        ),
        "is_pain_signal": True,
        "rule_id": "RIN_MATRU",
    }


def detect_stri_rin(chart_data: dict) -> dict | None:
    """
    Stri Rin = Spouse/Female partner debt from past lives.
    Indicators: Venus afflicted by Saturn/Rahu; Venus in H6/H8/H12;
                7th house afflicted by 2+ malefics; Mars-Venus same house.
    """
    venus_house  = _planet_house(chart_data, "Venus")
    saturn_house = _planet_house(chart_data, "Saturn")
    rahu_house   = _planet_house(chart_data, "Rahu")
    mars_house   = _planet_house(chart_data, "Mars")
    venus_weak   = _is_debilitated(chart_data, "Venus")
    venus_in_pain= venus_house in (6, 8, 12)

    # Saturn or Rahu in same house as Venus
    saturn_conj_venus = saturn_house == venus_house if venus_house else False
    rahu_conj_venus   = rahu_house   == venus_house if venus_house else False

    # Saturn or Rahu aspecting Venus's house
    saturn_asp_venus = _aspects_house("Saturn", saturn_house, venus_house) if saturn_house and venus_house else False
    rahu_asp_venus   = _aspects_house("Rahu",   rahu_house,  venus_house) if rahu_house and venus_house else False

    # 7H malefics
    h7_planets  = _planets_in_house(chart_data, 7)
    h7_malefics = [p for p in h7_planets if p in MALEFICS]

    # Mars-Venus conjunction
    mars_venus_conj = (mars_house == venus_house and mars_house > 0)

    score = sum([venus_weak, venus_in_pain,
                 saturn_conj_venus or rahu_conj_venus,
                 saturn_asp_venus  or rahu_asp_venus,
                 len(h7_malefics) >= 2, mars_venus_conj])

    if score < 1:
        return None

    return {
        "rin_type":   "Stri Rin",
        "rin_hindi":  "स्त्री ऋण",
        "domain":     "marriage",
        "confidence": 0.68 + score * 0.05,
        "indicators": {
            "venus_weak":          venus_weak,
            "venus_in_pain":       venus_in_pain,
            "saturn_rahu_on_venus":saturn_conj_venus or rahu_conj_venus,
            "saturn_rahu_asp_venus":saturn_asp_venus or rahu_asp_venus,
            "h7_malefics":         h7_malefics,
            "mars_venus_conj":     mars_venus_conj,
        },
        "prediction": (
            "Stri Rin (Partner/Female Ancestral Debt) is present in your chart. "
            "Past-life unresolved karma with a female partner or female ancestral figure "
            "is replaying in your relationship patterns. "
            "This shows as: patterns of conflict or hurt in romantic partnerships, "
            "feeling chronically misunderstood by partners, or attracting partners "
            "who trigger specific wounds. This is not your fault — it predates you."
        ),
        "life_pattern": (
            "Relationship patterns repeat until the karmic account is consciously addressed. "
            "Venus periods bring both the intensity of Stri Rin and the opportunity to clear it."
        ),
        "remedy": (
            "Lal Kitab Stri Rin Remedy: "
            "(1) Respect and serve the women in your family — mother, sisters, wife — actively. "
            "(2) On Fridays, donate white sweets to married women. "
            "(3) Float rose petals in flowing water for 11 consecutive Fridays. "
            "(4) Never speak harshly to or about women — this is the primary remedy. "
            "(5) If Venus is in H12: donate perfumes to elderly women and wear fresh flowers. "
            "The debt clears through genuine honoring, not just ritual performance."
        ),
        "is_pain_signal": True,
        "rule_id": "RIN_STRI",
    }


def detect_putra_rin(chart_data: dict) -> dict | None:
    """
    Putra Rin = Children debt / blocked 5th house blessings.
    Indicators: Jupiter weak; Ketu in H5; 5th lord afflicted.
    """
    jupiter_house = _planet_house(chart_data, "Jupiter")
    ketu_house    = _planet_house(chart_data, "Ketu")
    saturn_house  = _planet_house(chart_data, "Saturn")
    jupiter_weak  = _is_debilitated(chart_data, "Jupiter")
    jupiter_pain  = jupiter_house in (6, 8, 12)
    ketu_in_h5    = ketu_house == 5

    # Saturn aspecting or in H5
    saturn_in_h5     = saturn_house == 5
    saturn_asp_h5    = _aspects_house("Saturn", saturn_house, 5) if saturn_house else False

    score = sum([jupiter_weak, jupiter_pain, ketu_in_h5,
                 saturn_in_h5 or saturn_asp_h5])

    if score < 1:
        return None

    return {
        "rin_type":   "Putra Rin",
        "rin_hindi":  "पुत्र ऋण",
        "domain":     "children",
        "confidence": 0.68 + score * 0.05,
        "indicators": {
            "jupiter_weak":      jupiter_weak,
            "jupiter_in_pain":   jupiter_pain,
            "ketu_in_h5":        ketu_in_h5,
            "saturn_near_h5":    saturn_in_h5 or saturn_asp_h5,
        },
        "prediction": (
            "Putra Rin (Children Ancestral Debt) is present in your chart. "
            "This manifests as delays in having children, challenges in parenting, "
            "or feeling a deep gap in the area of legacy and creative self-expression. "
            "Past-life karma around children — whether from abandonment, loss, "
            "or unfulfilled parental duties — is being worked through. "
            "The soul chose this path specifically to heal this lineage pattern."
        ),
        "life_pattern": (
            "Children may come late or require significant effort. "
            "Creative work and teaching others' children can partially fulfill this energy "
            "while the karmic account is being cleared."
        ),
        "remedy": (
            "Lal Kitab Putra Rin Remedy: "
            "(1) Teach or mentor children — even informally. This is the most powerful remedy. "
            "(2) Feed and care for a dog (symbolizes Jupiter's protective nature). "
            "(3) Water a peepal tree every Thursday for 43 weeks. "
            "(4) Donate to children's education or orphanages on Thursdays. "
            "(5) If Ketu is in H5: perform Ganesha puja on Ganesh Chaturthi — "
            "Ketu in H5 specifically responds to Ganesha worship."
        ),
        "is_pain_signal": True,
        "rule_id": "RIN_PUTRA",
    }


def detect_bhatru_rin(chart_data: dict) -> dict | None:
    """
    Bhatru Rin = Sibling debt.
    Mars weak or in H8/H12; 3rd lord afflicted.
    """
    mars_house   = _planet_house(chart_data, "Mars")
    saturn_house = _planet_house(chart_data, "Saturn")
    rahu_house   = _planet_house(chart_data, "Rahu")
    mars_weak    = _is_debilitated(chart_data, "Mars")
    mars_in_pain = mars_house in (8, 12)

    saturn_asp_3 = _aspects_house("Saturn", saturn_house, 3) if saturn_house else False
    rahu_in_3    = rahu_house == 3
    rahu_asp_3   = _aspects_house("Rahu", rahu_house, 3) if rahu_house else False

    score = sum([mars_weak, mars_in_pain, saturn_asp_3, rahu_in_3 or rahu_asp_3])

    if score < 2:   # Require 2+ indicators for Bhatru Rin to surface
        return None

    return {
        "rin_type":   "Bhatru Rin",
        "rin_hindi":  "भ्रातृ ऋण",
        "domain":     "family",
        "confidence": 0.65 + score * 0.05,
        "indicators": {
            "mars_weak":      mars_weak,
            "mars_in_pain":   mars_in_pain,
            "saturn_asp_3":   saturn_asp_3,
            "rahu_near_h3":   rahu_in_3 or rahu_asp_3,
        },
        "prediction": (
            "Bhatru Rin (Sibling Ancestral Debt) is present in your chart. "
            "Past-life unresolved karma with a sibling or sibling-like figure "
            "creates current patterns of conflict, competition, or severed connection "
            "with brothers and sisters. The debt may also manifest as lack of sibling support "
            "or as carrying responsibilities that should have been shared."
        ),
        "life_pattern": (
            "Sibling relationships carry unresolved tension. "
            "Self-effort and courage (3rd house themes) require more conscious development."
        ),
        "remedy": (
            "Lal Kitab Bhatru Rin Remedy: "
            "(1) Help your siblings financially or practically — even small gestures count. "
            "(2) Donate red lentils and copper on Tuesdays. "
            "(3) Feed red ants with sugar on Tuesdays. "
            "(4) Never take legal action against siblings if it can be avoided. "
            "Reconciliation and active support are the fastest remedy for Bhatru Rin."
        ),
        "is_pain_signal": True,
        "rule_id": "RIN_BHATRU",
    }


# ── MAIN ENTRY POINTS ─────────────────────────────────────────────────────────

def apply_lk_aspect_rules(chart_data: dict, concern: str) -> list:
    """
    Fire Lal Kitab aspect rules for this chart.
    For each planet, compute which houses it aspects.
    If a rule exists for (planet, aspected_house), fire it.
    """
    signals = []
    for planet, pdata in chart_data.get("planets", {}).items():
        house = pdata.get("house", 0)
        if not house:
            continue
        aspected_houses = _get_aspectees_of(chart_data, planet)
        for target_house in aspected_houses:
            rule = LK_ASPECT_RULES.get((planet, target_house))
            if not rule:
                continue

            signals.append({
                "system":           "lk_aspect",
                "planet":           planet,
                "aspected_house":   target_house,
                "rule_id":          f"LKA_{planet}_H{target_house}",
                "domain":           rule["domain"],
                "confidence":       rule["confidence"],
                "prediction":       rule["prediction"],
                "warning":          rule.get("warning", ""),
                "remedy_planet":    planet,
                "concern_relevance":0.90 if rule["domain"] == concern else 0.55,
                "is_pain_signal":   rule.get("is_pain", False),
            })

    return signals


def apply_rin_rules(chart_data: dict, concern: str) -> list:
    """
    Detect all Rin (debt) patterns in the chart.
    Converts rin dicts into the standard signal format.
    """
    signals = []
    detectors = [
        detect_pitru_rin,
        detect_matru_rin,
        detect_stri_rin,
        detect_putra_rin,
        detect_bhatru_rin,
    ]

    for detector in detectors:
        rin = detector(chart_data)
        if not rin:
            continue

        signals.append({
            "system":           "lk_rin",
            "planet":           "Saturn",   # rin is always Saturn/karma energy
            "rin_type":         rin["rin_type"],
            "rin_hindi":        rin.get("rin_hindi", ""),
            "rule_id":          rin["rule_id"],
            "domain":           rin["domain"],
            "confidence":       rin["confidence"],
            "prediction":       rin["prediction"],
            "warning":          rin.get("life_pattern", ""),
            "remedy":           rin["remedy"],
            "remedy_planet":    "Saturn",
            "concern_relevance":0.88 if rin["domain"] == concern else 0.60,
            "is_pain_signal":   True,
            "rin_indicators":   rin["indicators"],
        })

    return signals
