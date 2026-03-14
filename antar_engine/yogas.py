"""
antar_engine/yogas.py
Detect major Vedic yogas from D1 chart.
Returns list of active yogas with strength and interpretation.
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

# Exaltation signs
EXALTATION = {
    "Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
    "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra",
    "Rahu":"Gemini","Ketu":"Sagittarius"
}

# Debilitation signs
DEBILITATION = {
    "Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
    "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries",
    "Rahu":"Sagittarius","Ketu":"Gemini"
}

# Own signs
OWN_SIGN = {
    "Sun":["Leo"],"Moon":["Cancer"],"Mars":["Aries","Scorpio"],
    "Mercury":["Gemini","Virgo"],"Jupiter":["Sagittarius","Pisces"],
    "Venus":["Taurus","Libra"],"Saturn":["Capricorn","Aquarius"]
}

# Kendra houses (angular)
KENDRA = [1, 4, 7, 10]

# Trikona houses (trinal)
TRIKONA = [1, 5, 9]

# Dusthana houses (malefic)
DUSTHANA = [6, 8, 12]


def _get_house(planet: str, planets: dict) -> int:
    return planets.get(planet, {}).get("house", 0)

def _get_sign(planet: str, planets: dict) -> str:
    return planets.get(planet, {}).get("sign", "")

def _is_exalted(planet: str, planets: dict) -> bool:
    sign = _get_sign(planet, planets)
    return EXALTATION.get(planet) == sign

def _is_debilitated(planet: str, planets: dict) -> bool:
    sign = _get_sign(planet, planets)
    return DEBILITATION.get(planet) == sign

def _is_own_sign(planet: str, planets: dict) -> bool:
    sign = _get_sign(planet, planets)
    return sign in OWN_SIGN.get(planet, [])

def _in_same_house(p1: str, p2: str, planets: dict) -> bool:
    h1 = _get_house(p1, planets)
    h2 = _get_house(p2, planets)
    return h1 > 0 and h1 == h2

def _get_lagna_idx(lagna_sign: str) -> int:
    return SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

def _house_lord(house_num: int, lagna_sign: str) -> str:
    lagna_idx = _get_lagna_idx(lagna_sign)
    sign_idx = (lagna_idx + house_num - 1) % 12
    return SIGN_LORDS.get(SIGNS[sign_idx], "")

def _lord_in_house(house_lord_planet: str, target_house: int, planets: dict) -> bool:
    return _get_house(house_lord_planet, planets) == target_house


def detect_all_yogas(planets: dict, lagna_sign: str) -> list:
    """
    Detect all major Vedic yogas from D1 chart.
    Returns list of yoga dicts with name, strength, planets, effect.
    """
    yogas = []
    lagna_idx = _get_lagna_idx(lagna_sign)

    def add_yoga(name, strength, involved_planets, effect, category="general"):
        yogas.append({
            "name":     name,
            "strength": strength,  # "strong" | "moderate" | "weak"
            "planets":  involved_planets,
            "effect":   effect,
            "category": category,
        })

    # ── Pancha Mahapurusha Yogas ──────────────────────────────────
    # Mars in Kendra in own/exalted sign
    mars_house = _get_house("Mars", planets)
    if mars_house in KENDRA and (_is_own_sign("Mars", planets) or _is_exalted("Mars", planets)):
        add_yoga("Ruchaka Yoga", "strong", ["Mars"],
                 "Exceptional courage, physical strength, leadership ability. Mars energy gives commanding presence.",
                 "mahapurusha")

    # Mercury in Kendra in own/exalted
    merc_house = _get_house("Mercury", planets)
    if merc_house in KENDRA and (_is_own_sign("Mercury", planets) or _is_exalted("Mercury", planets)):
        add_yoga("Bhadra Yoga", "strong", ["Mercury"],
                 "Outstanding intelligence, communication ability, business acumen. Mercury gifts make this person exceptional in intellect.",
                 "mahapurusha")

    # Jupiter in Kendra in own/exalted
    jup_house = _get_house("Jupiter", planets)
    if jup_house in KENDRA and (_is_own_sign("Jupiter", planets) or _is_exalted("Jupiter", planets)):
        add_yoga("Hamsa Yoga", "strong", ["Jupiter"],
                 "Wisdom, spiritual depth, teaching ability. Jupiter's grace brings fortune and recognition.",
                 "mahapurusha")

    # Venus in Kendra in own/exalted
    ven_house = _get_house("Venus", planets)
    if ven_house in KENDRA and (_is_own_sign("Venus", planets) or _is_exalted("Venus", planets)):
        add_yoga("Malavya Yoga", "strong", ["Venus"],
                 "Beauty, artistic talent, refined tastes, wealth through Venus domains. Magnetic personality.",
                 "mahapurusha")

    # Saturn in Kendra in own/exalted
    sat_house = _get_house("Saturn", planets)
    if sat_house in KENDRA and (_is_own_sign("Saturn", planets) or _is_exalted("Saturn", planets)):
        add_yoga("Sasa Yoga", "strong", ["Saturn"],
                 "Authority, discipline, long-lasting success through persistence. Saturn rewards patient effort.",
                 "mahapurusha")

    # ── Raj Yogas ────────────────────────────────────────────────
    kendra_lords = [_house_lord(h, lagna_sign) for h in KENDRA]
    trikona_lords = [_house_lord(h, lagna_sign) for h in TRIKONA]

    for kl in set(kendra_lords):
        for tl in set(trikona_lords):
            if kl == tl:
                # Same planet rules both kendra and trikona = powerful Raj Yoga
                p_house = _get_house(kl, planets)
                if p_house in KENDRA or p_house in TRIKONA:
                    add_yoga(f"Raj Yoga ({kl})",
                             "strong" if p_house in [1,4,7,10,5,9] else "moderate",
                             [kl],
                             f"{kl} rules both an angular and trinal house — natural authority, success, and recognition.",
                             "raj_yoga")
            elif _in_same_house(kl, tl, planets):
                add_yoga(f"Raj Yoga ({kl}-{tl} conjunction)",
                         "moderate",
                         [kl, tl],
                         f"Angular and trinal house lords together — career success and fortune combine.",
                         "raj_yoga")

    # ── Dhana Yogas (wealth) ──────────────────────────────────────
    # 2nd lord and 11th lord in same house or mutual aspect
    lord_2  = _house_lord(2, lagna_sign)
    lord_11 = _house_lord(11, lagna_sign)
    if _in_same_house(lord_2, lord_11, planets):
        add_yoga("Dhana Yoga (2nd-11th)",
                 "strong",
                 [lord_2, lord_11],
                 "Wealth accumulation indicated — income and assets combine for financial prosperity.",
                 "wealth")

    # 5th lord and 9th lord combined = great fortune
    lord_5 = _house_lord(5, lagna_sign)
    lord_9 = _house_lord(9, lagna_sign)
    if _in_same_house(lord_5, lord_9, planets):
        add_yoga("Lakshmi Yoga (5th-9th)",
                 "strong",
                 [lord_5, lord_9],
                 "Fortune and intelligence combine — exceptional financial and creative abundance.",
                 "wealth")

    # Jupiter in 2nd, 5th, 9th, or 11th = Dhana Yoga
    if jup_house in [2, 5, 9, 11]:
        add_yoga("Dhana Yoga (Jupiter)",
                 "moderate",
                 ["Jupiter"],
                 "Jupiter in a wealth house — financial expansion and prosperity through wisdom and abundance.",
                 "wealth")

    # ── Gajakesari Yoga ──────────────────────────────────────────
    moon_house = _get_house("Moon", planets)
    jup_house  = _get_house("Jupiter", planets)
    moon_jup_dist = abs(moon_house - jup_house)
    if moon_jup_dist in [0, 3, 6, 9] or (12 - moon_jup_dist) in [3, 6, 9]:
        strength = "strong" if _in_same_house("Moon", "Jupiter", planets) else "moderate"
        add_yoga("Gajakesari Yoga",
                 strength,
                 ["Jupiter", "Moon"],
                 "Jupiter-Moon interaction — wisdom, public recognition, emotional intelligence, and good fortune.",
                 "general")

    # ── Budhaditya Yoga ──────────────────────────────────────────
    if _in_same_house("Sun", "Mercury", planets):
        # Sun-Mercury conjunction — intelligence and authority
        strength = "strong" if not _is_debilitated("Mercury", planets) else "weak"
        add_yoga("Budhaditya Yoga",
                 strength,
                 ["Sun", "Mercury"],
                 "Sun and Mercury together — sharp intellect combined with natural authority. Strong analytical and communication ability.",
                 "intelligence")

    # ── Viparita Raj Yoga ────────────────────────────────────────
    # Lords of 6th, 8th, 12th in those houses = paradoxical rise
    for house_pair in [(6,8), (6,12), (8,12)]:
        lord_a = _house_lord(house_pair[0], lagna_sign)
        lord_b = _house_lord(house_pair[1], lagna_sign)
        if (_get_house(lord_a, planets) in [6,8,12] and
            _get_house(lord_b, planets) in [6,8,12]):
            add_yoga(f"Viparita Raj Yoga ({house_pair[0]}-{house_pair[1]})",
                     "moderate",
                     [lord_a, lord_b],
                     "Difficult house lords in difficult houses — unexpected rise through adversity. Success that comes through transformation of obstacles.",
                     "raj_yoga")

    # ── Neechabhanga Raj Yoga ────────────────────────────────────
    # Debilitated planet cancelled by exaltation sign lord in Kendra
    for planet in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
        if _is_debilitated(planet, planets):
            debil_sign = DEBILITATION.get(planet, "")
            sign_lord = SIGN_LORDS.get(debil_sign, "")
            lord_house = _get_house(sign_lord, planets)
            if lord_house in KENDRA:
                add_yoga(f"Neechabhanga Raj Yoga ({planet})",
                         "moderate",
                         [planet, sign_lord],
                         f"{planet} is debilitated but its cancellation creates unexpected strength — what appears as weakness becomes a source of unique power.",
                         "raj_yoga")

    # ── Kemadruma Yoga (no planets flanking Moon) ────────────────
    # Moon with no planets in adjacent houses = emotional isolation
    moon_h = _get_house("Moon", planets)
    adjacent_houses = [(moon_h - 2) % 12 + 1, moon_h % 12 + 1]
    has_flanking = any(
        _get_house(p, planets) in adjacent_houses
        for p in ["Sun","Mars","Mercury","Jupiter","Venus","Saturn"]
    )
    if not has_flanking and not _in_same_house("Moon", "Jupiter", planets):
        add_yoga("Kemadruma Yoga",
                 "weak",
                 ["Moon"],
                 "Moon without flanking planets — periods of emotional isolation, self-reliance, or feeling unsupported are themes to watch.",
                 "challenge")

    # ── Chandra-Mangala Yoga ─────────────────────────────────────
    if _in_same_house("Moon", "Mars", planets):
        add_yoga("Chandra-Mangala Yoga",
                 "moderate",
                 ["Moon", "Mars"],
                 "Moon and Mars together — financial drive through emotional intensity. Entrepreneurial energy. Can be restless.",
                 "wealth")

    # ── Guru-Chandala Yoga ───────────────────────────────────────
    if _in_same_house("Jupiter", "Rahu", planets):
        add_yoga("Guru-Chandala Yoga",
                 "moderate",
                 ["Jupiter", "Rahu"],
                 "Jupiter and Rahu together — unconventional wisdom, breaking traditional rules, foreign or unusual knowledge. Can indicate spiritual challenges.",
                 "challenge")

    # ── Grahan Yoga (eclipse conjunction) ────────────────────────
    for luminary in ["Sun", "Moon"]:
        if _in_same_house(luminary, "Rahu", planets) or _in_same_house(luminary, "Ketu", planets):
            node = "Rahu" if _in_same_house(luminary, "Rahu", planets) else "Ketu"
            add_yoga(f"Grahan Yoga ({luminary}-{node})",
                     "moderate",
                     [luminary, node],
                     f"{luminary} with {node} — intense karmic themes around the {luminary.lower()}'s domain. Transformation through this planet's significations.",
                     "karmic")

    # ── Amala Yoga ───────────────────────────────────────────────
    # 10th from Moon occupied by natural benefic = spotless reputation
    moon_h = _get_house("Moon", planets)
    tenth_from_moon = (moon_h + 9 - 1) % 12 + 1
    benefics_in_10th_from_moon = [
        p for p in ["Jupiter","Venus","Mercury"]
        if _get_house(p, planets) == tenth_from_moon
    ]
    if benefics_in_10th_from_moon:
        add_yoga("Amala Yoga",
                 "moderate",
                 benefics_in_10th_from_moon,
                 "Benefic planet in 10th from Moon — spotless reputation, respected career, lasting legacy.",
                 "reputation")

    # ── Remove duplicates ────────────────────────────────────────
    seen = set()
    unique_yogas = []
    for y in yogas:
        key = y["name"]
        if key not in seen:
            seen.add(key)
            unique_yogas.append(y)

    # Sort: strong first, then moderate, then weak
    order = {"strong": 0, "moderate": 1, "weak": 2}
    unique_yogas.sort(key=lambda x: order.get(x["strength"], 3))

    return unique_yogas


def yogas_to_prompt_block(yogas: list) -> str:
    """Format yogas into a concise LLM prompt block."""
    if not yogas:
        return "YOGAS: No major yogas detected."

    strong   = [y for y in yogas if y["strength"] == "strong"]
    moderate = [y for y in yogas if y["strength"] == "moderate"]

    lines = ["YOGAS PRESENT IN THIS CHART:"]

    if strong:
        lines.append("  STRONG YOGAS (highest impact):")
        for y in strong:
            lines.append(f"    • {y['name']}: {y['effect']}")

    if moderate:
        lines.append("  MODERATE YOGAS:")
        for y in moderate[:4]:  # cap at 4 to avoid prompt bloat
            lines.append(f"    • {y['name']}: {y['effect']}")

    challenge = [y for y in yogas if y.get("category") == "challenge"]
    if challenge:
        lines.append("  CHALLENGES:")
        for y in challenge:
            lines.append(f"    • {y['name']}: {y['effect']}")

    return "\n".join(lines)
