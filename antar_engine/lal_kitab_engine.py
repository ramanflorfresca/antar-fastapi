"""
antar_engine/lal_kitab_engine.py
Complete Lal Kitab analysis — house rules, remedies, and debts.
Lal Kitab is a distinct system from classical Vedic astrology.
Key principle: planets in houses (not signs) determine everything.
"""

# ── Lal Kitab Planet-in-House Interpretations ──────────────────────────────
# Each planet in each house has specific effects on life domains
# Source: Traditional Lal Kitab rules

LK_PLANET_IN_HOUSE = {
    "Sun": {
        1:  {"effect": "Strong, authoritative personality. Father's lineage strong. Government favor. Health excellent if not afflicted.", "remedy": "Offer water to Sun daily at sunrise. Avoid ego.", "domain": "self/authority"},
        2:  {"effect": "Wealthy family but father may have issues. Good for government jobs. Speak less, gain more.", "remedy": "Keep copper coin in wallet. Donate wheat.", "domain": "wealth"},
        3:  {"effect": "Brave, self-made. Brothers may cause problems. Good for writing and communication careers.", "remedy": "Feed crows. Help brothers.", "domain": "courage/siblings"},
        4:  {"effect": "Mother's health may suffer. Property gains in second half of life. Happiness from hard work.", "remedy": "Respect mother. Avoid disputes over property.", "domain": "home"},
        5:  {"effect": "Intelligent, creative children. Government recognition. Political career favorable.", "remedy": "Offer jaggery to Sun. Donate to education.", "domain": "children/intelligence"},
        6:  {"effect": "Defeats enemies. Government service favored. Health issues from heat/bile.", "remedy": "Serve father daily. Donate food to poor.", "domain": "enemies/service"},
        7:  {"effect": "Late marriage or marital issues. Spouse may be domineering. Partnership disputes.", "remedy": "Never take dowry. Gift wife jewelry.", "domain": "marriage"},
        8:  {"effect": "Longevity but accidents possible. Hidden enemies. Inheritance through legal battles.", "remedy": "Avoid non-vegetarian on Sundays. Keep ruby.", "domain": "longevity/hidden"},
        9:  {"effect": "Fortunate, religious father. Good luck. Higher education abroad possible.", "remedy": "Respect father. Never disrespect religious leaders.", "domain": "fortune/dharma"},
        10: {"effect": "Excellent career in government/authority. Fame. Self-made success. Father supports.", "remedy": "Offer water to Sun at sunrise. Keep work honest.", "domain": "career/fame"},
        11: {"effect": "Gains from government. Elder siblings supportive. Fixed assets accumulate.", "remedy": "Donate wheat on Sundays. Help elder siblings.", "domain": "gains"},
        12: {"effect": "Foreign lands bring success. Hidden expenditure. Eyes may have issues. Spiritual liberation.", "remedy": "Donate copper on Sundays. Eye care important.", "domain": "foreign/moksha"},
    },
    "Moon": {
        1:  {"effect": "Emotional, sensitive, public-facing career. Mother very influential. Mind fluctuates.", "remedy": "Respect mother. Offer milk to Shiva. Keep silver.", "domain": "self/mind"},
        2:  {"effect": "Wealthy family, good food. Mother's blessings bring wealth. Speech sweet.", "remedy": "Donate milk on Mondays. Keep well hydrated.", "domain": "wealth/family"},
        3:  {"effect": "Artistic, communicative siblings. Short travels beneficial. Writing talent.", "remedy": "Keep silver in pocket. Drink water in silver vessel.", "domain": "communication"},
        4:  {"effect": "Very blessed by mother. Owns property. Emotional happiness from home.", "remedy": "Keep moon-related items at home. Milk diet beneficial.", "domain": "home/mother"},
        5:  {"effect": "Creative, artistic children. Emotional intelligence high. Speculation favorable.", "remedy": "Offer milk to Moon on full moon night.", "domain": "children/creativity"},
        6:  {"effect": "Health issues from cold/water. Emotional enemies. Service to women beneficial.", "remedy": "Donate milk to poor. Keep digestive health.", "domain": "health/enemies"},
        7:  {"effect": "Beautiful, emotional spouse. Marriage brings emotional fulfillment. Business with women.", "remedy": "Gift wife silver jewelry. Offer water to Moon.", "domain": "marriage"},
        8:  {"effect": "Psychic abilities. Hidden matters accessible. Longevity through emotional stability.", "remedy": "Offer water to ancestors on new moon.", "domain": "occult/longevity"},
        9:  {"effect": "Fortune through mother. Travel for religious purposes. Dreams are prophetic.", "remedy": "Visit pilgrimage sites with mother.", "domain": "fortune/religion"},
        10: {"effect": "Career in public life, entertainment, or hospitality. Fame from mother's blessings.", "remedy": "Never disrespect mother. Offer milk to workplace.", "domain": "career/public"},
        11: {"effect": "Gains from women and public. Elder sister very supportive. Income fluctuates.", "remedy": "Keep silver vessel at home. Donate to women.", "domain": "gains"},
        12: {"effect": "Spiritual liberation. Foreign lands beneficial. Emotional isolation may occur.", "remedy": "Meditate near water. Keep fasts on Mondays.", "domain": "spirituality/foreign"},
    },
    "Mars": {
        1:  {"effect": "Aggressive, energetic, physically strong. Property gains. Brothers may create issues.", "remedy": "Donate blood. Help brothers. Keep coral.", "domain": "self/energy"},
        2:  {"effect": "Harsh speech can damage wealth. Disputes in family. Red coral in gold beneficial.", "remedy": "Control anger. Donate red lentils on Tuesdays.", "domain": "speech/wealth"},
        3:  {"effect": "Brave, self-made. Brothers are both support and obstacle. Military/police success.", "remedy": "Never fight with brothers. Donate blood on birthday.", "domain": "courage/brothers"},
        4:  {"effect": "Property gains through struggle. Mother may have health issues. Home disputes possible.", "remedy": "Plant red flowers at home. Respect mother.", "domain": "property/home"},
        5:  {"effect": "Intelligent, competitive children. Sports success. Speculative gains.", "remedy": "Keep a sword (small) at home. Donate honey.", "domain": "children/sports"},
        6:  {"effect": "Defeats all enemies. Excellent for police/military/surgery. Competitive success.", "remedy": "Help the weak. Donate blood periodically.", "domain": "enemies/service"},
        7:  {"effect": "Passionate but conflicted marriage. Spouse may be aggressive. Business partnerships volatile.", "remedy": "Never argue on Tuesdays. Gift spouse red items.", "domain": "marriage"},
        8:  {"effect": "Accidents and surgery possible. Interest in occult. Hidden enemies. Short life if very weak.", "remedy": "Keep knife/sword away from home. Pray to Hanuman.", "domain": "accidents/occult"},
        9:  {"effect": "Father may face legal issues. Religious debates. Fortune through action and courage.", "remedy": "Visit Hanuman temple on Tuesdays. Donate red lentils.", "domain": "father/dharma"},
        10: {"effect": "Excellent career in technical fields, surgery, military, police, engineering.", "remedy": "Keep workplace organized. Donate to soldiers.", "domain": "career/technical"},
        11: {"effect": "Gains through property and real estate. Elder brother brings wealth. Income from Mars fields.", "remedy": "Help elder brothers. Donate red items on Tuesdays.", "domain": "gains/property"},
        12: {"effect": "Hidden enemies dangerous. Expenditure on Mars-ruled items. Foreign travel for work.", "remedy": "Keep feet clean. Donate to hospitals.", "domain": "hidden enemies/foreign"},
    },
    "Mercury": {
        1:  {"effect": "Intelligent, communicative, young-looking. Business-minded. Multiple skills.", "remedy": "Keep emerald. Feed green grass to cow. Donate books.", "domain": "intellect/communication"},
        2:  {"effect": "Excellent for business and trade. Witty speech brings wealth. Family intelligent.", "remedy": "Donate books to students. Keep parrot as pet.", "domain": "wealth/business"},
        3:  {"effect": "Very skilled in communication. Writers, journalists, traders. Sibling relations complex.", "remedy": "Donate green items on Wednesdays. Write daily.", "domain": "communication/writing"},
        4:  {"effect": "Intellectual home environment. Mother educated. Property through business.", "remedy": "Keep books at home. Donate green vegetables.", "domain": "home/intellect"},
        5:  {"effect": "Highly intelligent children. Education success. Speculative gains through analysis.", "remedy": "Donate stationery to students. Keep emerald.", "domain": "intelligence/children"},
        6:  {"effect": "Analytical mind defeats enemies. Excellent for medicine, law, accounting.", "remedy": "Donate medicine to poor. Help young students.", "domain": "service/health"},
        7:  {"effect": "Intellectual spouse. Business partnership successful. Communication in marriage key.", "remedy": "Never lie in partnerships. Gift spouse books.", "domain": "marriage/partnership"},
        8:  {"effect": "Hidden knowledge, research talent. Occult through intellect. Inheritance through paperwork.", "remedy": "Meditate. Keep a journal of dreams.", "domain": "research/occult"},
        9:  {"effect": "Education abroad. Philosophical mind. Father may be businessman or intellectual.", "remedy": "Donate books to temples. Study religious texts.", "domain": "education/dharma"},
        10: {"effect": "Excellent for business, media, writing, teaching, IT, trading, accounting.", "remedy": "Keep workplace communication clear. Donate to education.", "domain": "career/business"},
        11: {"effect": "Gains through business and communication. Friend circle brings opportunities.", "remedy": "Help friends in business. Donate green on Wednesdays.", "domain": "gains/friends"},
        12: {"effect": "Hidden talents. Writing in isolation produces best work. Foreign business beneficial.", "remedy": "Meditate daily. Keep writing journal private.", "domain": "isolation/foreign"},
    },
    "Jupiter": {
        1:  {"effect": "Blessed life. Natural wisdom and generosity. Protected by divine grace. Good health.", "remedy": "Donate yellow items on Thursdays. Help teachers.", "domain": "wisdom/blessing"},
        2:  {"effect": "Very wealthy family. Excellent for accumulated wealth. Speech brings blessings.", "remedy": "Donate yellow food on Thursdays. Keep gold.", "domain": "wealth/family"},
        3:  {"effect": "Philosophical siblings. Writing on wisdom topics. Short journeys to sacred places.", "remedy": "Donate books on religion. Help younger siblings.", "domain": "wisdom/siblings"},
        4:  {"effect": "Blessed home and mother. Property gains easily. Happiness is the natural state.", "remedy": "Keep a temple at home. Donate to women.", "domain": "home/happiness"},
        5:  {"effect": "Excellent for children — they will be accomplished. High intelligence. Spiritual depth.", "remedy": "Teach children wisdom. Donate to schools.", "domain": "children/intelligence"},
        6:  {"effect": "Defeats enemies through wisdom. Health generally good. Service through teaching.", "remedy": "Donate to hospitals and schools. Serve teachers.", "domain": "service/health"},
        7:  {"effect": "Wise, educated spouse. Marriage blessed. Legal partnerships successful.", "remedy": "Gift spouse religious books. Never disrespect spouse.", "domain": "marriage/partnership"},
        8:  {"effect": "Long life. Interest in philosophy and occult. Inheritance from teachers or elders.", "remedy": "Study sacred texts. Donate on Thursdays.", "domain": "longevity/philosophy"},
        9:  {"effect": "Extremely fortunate. Religious father. Higher education exceptional. Divine blessings.", "remedy": "Respect all teachers. Visit temples regularly.", "domain": "fortune/dharma"},
        10: {"effect": "Highly respected career. Teaching, law, finance, religion. Recognition comes.", "remedy": "Teach others without expectation. Keep workplace ethical.", "domain": "career/respect"},
        11: {"effect": "Exceptional gains. Elder siblings very supportive. Income grows steadily.", "remedy": "Donate yellow items on Thursdays. Help elder siblings.", "domain": "gains/income"},
        12: {"effect": "Spiritual liberation. Foreign teaching possible. Expenditure on religious causes.", "remedy": "Donate to temples abroad. Meditate daily.", "domain": "spirituality/moksha"},
    },
    "Venus": {
        1:  {"effect": "Beautiful appearance, artistic, romantic. Wealth through beauty or art. Materialistic.", "remedy": "Respect women. Donate white items on Fridays.", "domain": "beauty/love"},
        2:  {"effect": "Wealthy family. Beautiful voice. Income from artistic pursuits. Enjoy life.", "remedy": "Keep white flowers at home. Donate to women.", "domain": "wealth/pleasure"},
        3:  {"effect": "Artistic siblings. Creative writing. Short travels for pleasure. Love of beauty.", "remedy": "Gift sister white clothes. Donate perfume.", "domain": "creativity/travel"},
        4:  {"effect": "Beautiful home. Happy mother. Luxury in domestic life. Vehicles and property.", "remedy": "Keep white flowers at home. Respect mother.", "domain": "home/luxury"},
        5:  {"effect": "Creative, artistic children. Love affairs prominent. Speculation through Venus fields.", "remedy": "Never break promises in love. Donate to arts.", "domain": "love/creativity"},
        6:  {"effect": "Health issues from Venus significations. Hidden relationships possible. Sweet defeats enemies.", "remedy": "Maintain physical health. Donate to women's causes.", "domain": "health/relationships"},
        7:  {"effect": "Beautiful, loving spouse. Excellent for marriage. Business partnerships very successful.", "remedy": "Gift spouse jewelry. Honor all commitments.", "domain": "marriage/pleasure"},
        8:  {"effect": "Long life through partner. Hidden wealth. Secret relationships. Inheritance.", "remedy": "Keep intimate life private. Donate on Fridays.", "domain": "inheritance/hidden"},
        9:  {"effect": "Fortunate through beauty and art. Father may be artistic. Religious travel with spouse.", "remedy": "Visit temples with spouse. Donate white on Fridays.", "domain": "fortune/religion"},
        10: {"effect": "Career in arts, beauty, entertainment, fashion, luxury goods. Fame through Venus fields.", "remedy": "Maintain ethical standards in career. Help women.", "domain": "career/arts"},
        11: {"effect": "Gains from Venus fields. Women bring income. Elder sister very important.", "remedy": "Gift elder sister white clothes. Donate perfume.", "domain": "gains/women"},
        12: {"effect": "Expenditure on luxury. Secret love affairs possible. Spiritual liberation through beauty.", "remedy": "Keep intimate matters private. Donate to women.", "domain": "foreign/spirituality"},
    },
    "Saturn": {
        1:  {"effect": "Slow but steady life. Discipline builds everything. Hard work always rewarded eventually.", "remedy": "Serve servants and workers. Oil lamps on Saturdays.", "domain": "discipline/longevity"},
        2:  {"effect": "Wealth through persistent work. Family hardships early life. Honest speech.", "remedy": "Never lie. Donate black sesame on Saturdays.", "domain": "wealth/speech"},
        3:  {"effect": "Self-made through hard work. Sibling responsibilities. Discipline in communication.", "remedy": "Help servants and workers. Donate iron items.", "domain": "work/siblings"},
        4:  {"effect": "Property through sustained effort. Mother's health challenges. Home built slowly.", "remedy": "Keep sesame at home entrance. Respect servants.", "domain": "property/effort"},
        5:  {"effect": "Children come late or with difficulty. Intelligence through discipline. Karmic children.", "remedy": "Donate to orphanages. Teach underprivileged children.", "domain": "children/karma"},
        6:  {"effect": "Very powerful for defeating enemies through patience. Service and healthcare success.", "remedy": "Serve the poor on Saturdays. Donate oil.", "domain": "service/enemies"},
        7:  {"effect": "Late marriage or older/serious spouse. Partnerships require patience to succeed.", "remedy": "Gift spouse iron items. Never rush partnerships.", "domain": "marriage/partnership"},
        8:  {"effect": "Very long life. Interest in death and rebirth. Hidden wealth accumulates slowly.", "remedy": "Study philosophy. Donate to cremation grounds.", "domain": "longevity/occult"},
        9:  {"effect": "Dharma through hard work. Father faces hardships. Fortune delayed but certain.", "remedy": "Serve father diligently. Donate on Saturdays.", "domain": "dharma/father"},
        10: {"effect": "Success through sustained effort and discipline. Authority gained late. Long career.", "remedy": "Serve workers honestly. Keep career ethical.", "domain": "career/authority"},
        11: {"effect": "Gains through iron/land/service industries. Elder brothers face hardships.", "remedy": "Help workers and servants. Donate iron on Saturdays.", "domain": "gains/service"},
        12: {"effect": "Spiritual liberation through discipline and renunciation. Foreign work possible.", "remedy": "Donate to poor on Saturdays. Meditate at night.", "domain": "spirituality/liberation"},
    },
    "Rahu": {
        1:  {"effect": "Unusual, unconventional personality. Foreign connections. Ambition drives everything.", "remedy": "Keep elephant figurine. Feed crows on Saturdays.", "domain": "ambition/foreign"},
        2:  {"effect": "Wealth through unconventional means. Family secrets. Foreign income possible.", "remedy": "Never lie for money. Donate to orphans.", "domain": "wealth/secrets"},
        3:  {"effect": "Unconventional communication. Technology fields. Foreign travel frequently.", "remedy": "Help widows. Donate blue items on Saturdays.", "domain": "technology/travel"},
        4:  {"effect": "Property through foreign connections. Mother may have health issues. Restless at home.", "remedy": "Keep home clean. Respect mother.", "domain": "property/foreign"},
        5:  {"effect": "Unusual children or difficult conception. Speculative losses possible. Past karma.", "remedy": "Never abort. Donate to orphanages.", "domain": "children/karma"},
        6:  {"effect": "Hidden enemies dangerous. Foreign competition. Unusual diseases possible.", "remedy": "Keep snake image. Donate on Saturdays.", "domain": "hidden enemies/health"},
        7:  {"effect": "Unusual or foreign spouse. Non-traditional partnership. Legal complications.", "remedy": "Never deceive partner. Respect spouse's family.", "domain": "marriage/foreign"},
        8:  {"effect": "Sudden events and transformations. Accidents possible. Occult powers.", "remedy": "Avoid risky activities. Keep sandalwood.", "domain": "transformation/accidents"},
        9:  {"effect": "Unconventional dharma. Foreign religious influence. Father may be from different background.", "remedy": "Respect all religions. Donate on Saturdays.", "domain": "dharma/foreign"},
        10: {"effect": "Career in foreign fields, technology, politics, or unconventional work. Sudden rise.", "remedy": "Keep career ethical. Avoid shortcuts.", "domain": "career/technology"},
        11: {"effect": "Gains from foreign sources. Unconventional income streams. Large social network.", "remedy": "Help orphans. Donate regularly on Saturdays.", "domain": "gains/foreign"},
        12: {"effect": "Foreign settlement likely. Hidden spiritual power. Liberation through transformation.", "remedy": "Meditate. Keep foreign connections ethical.", "domain": "foreign/liberation"},
    },
    "Ketu": {
        1:  {"effect": "Spiritual, detached personality. Past life wisdom. Health through spirituality.", "remedy": "Keep cat as pet. Donate blankets to poor.", "domain": "spirituality/detachment"},
        2:  {"effect": "Detachment from family wealth. Speech unusual. Past life family karma active.", "remedy": "Feed dogs. Donate multi-colored items.", "domain": "karma/detachment"},
        3:  {"effect": "Spiritual communication. Past life siblings. Pilgrimages beneficial.", "remedy": "Help younger siblings. Donate on Tuesdays.", "domain": "spirituality/siblings"},
        4:  {"effect": "Detachment from home. Mother with spiritual nature. Property karma from past life.", "remedy": "Keep spiritual items at home. Respect mother.", "domain": "home/karma"},
        5:  {"effect": "Ketu in 5th is challenging for children — delays or issues. Very spiritual intelligence.", "remedy": "Adopt a child. Donate to orphanages.", "domain": "children/spirituality"},
        6:  {"effect": "Past life debts active through enemies. Unusual diseases. Spiritual healing beneficial.", "remedy": "Donate blankets. Keep spiritual practices.", "domain": "karma/enemies"},
        7:  {"effect": "Karmic marriage. Spouse may have past life connection. Spiritual partnership.", "remedy": "Never disrespect spouse. Meditate together.", "domain": "marriage/karma"},
        8:  {"effect": "Very spiritual, moksha indicator. Psychic abilities. Past life occult knowledge.", "remedy": "Study spirituality seriously. Meditate daily.", "domain": "moksha/occult"},
        9:  {"effect": "Past life spiritual merit. Unconventional dharma. Father may be spiritual or absent.", "remedy": "Serve spiritual teachers. Donate on Thursdays.", "domain": "dharma/past_life"},
        10: {"effect": "Career in spirituality, research, or behind-the-scenes work. Hidden talent.", "remedy": "Keep work private until successful. Meditate.", "domain": "career/hidden"},
        11: {"effect": "Detachment from gains — what comes easily goes easily. Spiritual gains instead.", "remedy": "Donate gains regularly. Help the poor.", "domain": "gains/spirituality"},
        12: {"effect": "Strongest Ketu placement — full moksha. Liberation is the life purpose.", "remedy": "Meditate daily. Renounce gradually.", "domain": "moksha/liberation"},
    },
}

# Lal Kitab Rin (debts) — karmic debts based on planetary placements
LK_KARMIC_DEBTS = {
    "Sun_6_or_12": "Karmic debt to father or government. Repay through service and honesty.",
    "Moon_6_or_12": "Karmic debt to mother or women. Repay through care and respect.",
    "Mars_4_or_8": "Karmic debt related to property or siblings. Repay through sharing.",
    "Saturn_5_or_7": "Karmic debt to servants or previous generation. Repay through service.",
    "Rahu_1_or_7": "Foreign karmic debt. Unconventional repayment needed.",
    "Ketu_1_or_8": "Spiritual karmic debt from past life. Meditation and service.",
}


def calculate_lal_kitab_analysis(planets: dict, lagna_sign: str) -> dict:
    """
    Full Lal Kitab analysis for a chart.
    Returns house-by-house analysis, remedies, and karmic debts.
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

    lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0
    analysis = {}
    all_remedies = []
    karmic_debts = []
    key_insights = []

    for planet, data in planets.items():
        house = data.get("house", 0)
        if not house or planet not in LK_PLANET_IN_HOUSE:
            continue

        house_rules = LK_PLANET_IN_HOUSE[planet].get(house, {})
        if not house_rules:
            continue

        effect  = house_rules.get("effect", "")
        remedy  = house_rules.get("remedy", "")
        domain  = house_rules.get("domain", "")

        analysis[f"{planet}_in_{house}"] = {
            "planet":  planet,
            "house":   house,
            "effect":  effect,
            "remedy":  remedy,
            "domain":  domain,
        }

        if remedy:
            all_remedies.append({
                "planet": planet,
                "house":  house,
                "remedy": remedy,
            })

        # Check for karmic debts
        debt_key = f"{planet}_{house}_or_{(house % 12)}"
        for debt_pattern, debt_desc in LK_KARMIC_DEBTS.items():
            parts = debt_pattern.split("_")
            if parts[0] == planet and str(house) in parts[1:]:
                karmic_debts.append({
                    "planet": planet,
                    "house":  house,
                    "debt":   debt_desc,
                })

    # Key insights — most impactful placements
    KEY_HOUSES = [1, 2, 4, 7, 9, 10, 11]
    POWER_PLANETS = ["Jupiter", "Saturn", "Rahu", "Mars", "Sun"]

    for planet in POWER_PLANETS:
        house = planets.get(planet, {}).get("house", 0)
        if house in KEY_HOUSES:
            rules = LK_PLANET_IN_HOUSE.get(planet, {}).get(house, {})
            if rules.get("effect"):
                key_insights.append({
                    "planet":  planet,
                    "house":   house,
                    "insight": rules["effect"],
                    "domain":  rules.get("domain",""),
                })

    # Lagna lord placement
    lagna_lord = SIGN_LORDS.get(lagna_sign, "")
    lagna_lord_house = planets.get(lagna_lord, {}).get("house", 0)
    lagna_insight = ""
    if lagna_lord and lagna_lord_house:
        lagna_insight = (
            f"Lagna lord {lagna_lord} is in house {lagna_lord_house} — "
            f"life energy directed toward {_house_meaning(lagna_lord_house)}"
        )

    return {
        "planet_in_house_analysis": analysis,
        "key_insights":             key_insights[:5],
        "remedies":                 all_remedies[:6],
        "karmic_debts":             karmic_debts,
        "lagna_lord_placement":     lagna_insight,
        "total_analyzed":           len(analysis),
    }


def _house_meaning(house: int) -> str:
    meanings = {
        1:"self and identity",2:"wealth and family",3:"courage and communication",
        4:"home and mother",5:"children and intelligence",6:"service and enemies",
        7:"marriage and partnerships",8:"transformation and longevity",
        9:"dharma and fortune",10:"career and authority",11:"gains and income",
        12:"spirituality and liberation"
    }
    return meanings.get(house, f"house {house} themes")


def lal_kitab_prompt_block(lk_analysis: dict, age: int = 35) -> str:
    """Format Lal Kitab analysis for LLM prompt."""
    if not lk_analysis:
        return ""

    lines = ["=== LAL KITAB ANALYSIS ==="]

    # Lagna lord
    if lk_analysis.get("lagna_lord_placement"):
        lines.append(f"Lagna lord: {lk_analysis['lagna_lord_placement']}")

    # Key insights
    if lk_analysis.get("key_insights"):
        lines.append("\nKEY LAL KITAB INSIGHTS:")
        for ins in lk_analysis["key_insights"]:
            lines.append(f"  {ins['planet']} in house {ins['house']}: {ins['insight']}")

    # Karmic debts
    if lk_analysis.get("karmic_debts"):
        lines.append("\nKARMIC DEBTS (Rin) ACTIVE:")
        for debt in lk_analysis["karmic_debts"]:
            lines.append(f"  {debt['planet']} house {debt['house']}: {debt['debt']}")

    # Remedies (age-appropriate)
    remedies = lk_analysis.get("remedies", [])
    if remedies:
        lines.append("\nTOP REMEDIES:")
        for r in remedies[:3]:
            lines.append(f"  {r['planet']}: {r['remedy']}")

    lines.append("=== END LAL KITAB ===")
    return "\n".join(lines)
