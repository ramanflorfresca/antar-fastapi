"""
antar_engine/lal_kitab_teva.py

Teva — Annual Planet Position Table (Lal Kitab).
Reads current transiting planet positions from transits_engine
and applies Lal Kitab house-specific effects and remedies.

No duplicate calculation — Swiss Ephemeris runs once in transits_engine.
Teva adds the LK interpretation layer on top.
"""

# LK transit effects — what each planet means in each natal house THIS year
LK_TRANSIT_EFFECTS = {
    "Jupiter": {
        1:  ("Excellent year for health and personality", "Offer yellow flowers at temple on Thursdays"),
        2:  ("Wealth and family blessings — income rises", "Donate yellow sweets on Thursdays"),
        3:  ("Courage and communication expand", "Feed crows yellow food on Thursdays"),
        4:  ("Home improvements, mother's blessings", "Plant a banana tree at home"),
        5:  ("Children, intelligence, creativity peak", "Teach or mentor someone — pass knowledge on"),
        6:  ("Enemies weakened, debts reduce", "Donate to a school or place of learning"),
        7:  ("Marriage and partnerships blessed", "Respect your spouse with gifts on Thursdays"),
        8:  ("Hidden wisdom unlocked, inheritance possible", "Study sacred texts — wisdom comes now"),
        9:  ("Exceptional fortune year — dharma strong", "Visit a holy place. Father's blessings matter now"),
        10: ("Career peak — authority and recognition", "Start important work on Thursdays"),
        11: ("Major gains year — aspirations fulfilled", "Donate to elder siblings or mentors"),
        12: ("Spiritual growth, foreign opportunities", "Meditate daily. Foreign connections open"),
    },
    "Saturn": {
        1:  ("Health needs attention — slow but steady", "Donate oil on Saturdays. Serve workers"),
        2:  ("Wealth delays — patience required", "Donate black sesame on Saturdays"),
        3:  ("Courage blocked — avoid rash decisions", "Feed crows on Saturdays"),
        4:  ("Home disruptions, property issues", "Respect servants and workers at home"),
        5:  ("Children matters delayed, speculation risky", "Avoid gambling. Teach children discipline"),
        6:  ("Enemies and debts increase — stay alert", "Donate to laborers. Avoid litigation"),
        7:  ("Marriage under pressure — communicate carefully", "Honor spouse. Never argue on Saturdays"),
        8:  ("Transformation period — deep restructuring", "Accept change. Donate at cremation grounds"),
        9:  ("Father relationship needs attention", "Serve father or elderly men with respect"),
        10: ("Career restructuring — slow but lasting", "Work diligently. Results come after delay"),
        11: ("Gains delayed but certain", "Donate to poor on Saturdays. Be patient"),
        12: ("Expenses rise, spiritual lessons", "Meditate. Accept losses as karma clearing"),
    },
    "Rahu": {
        1:  ("Identity confusion — foreign influences strong", "Donate coal or mustard oil on Saturdays"),
        2:  ("Unconventional wealth — foreign income possible", "Avoid harsh speech. Feed fish"),
        3:  ("Bold communication — media opportunities", "Channel courage into creative ventures"),
        4:  ("Home disruptions — property matters complex", "Keep home clean and clear of clutter"),
        5:  ("Unconventional children situations, speculation", "Avoid risky investments this year"),
        6:  ("Hidden enemies — health from unknown causes", "Donate to hospitals. Stay grounded"),
        7:  ("Unusual partnerships — foreign spouse possible", "Be discerning in new relationships"),
        8:  ("Sudden transformation — inheritance possible", "Accept sudden changes as opportunities"),
        9:  ("Unorthodox dharma — foreign spiritual paths", "Question beliefs constructively"),
        10: ("Sudden career opportunities — unconventional path", "Take calculated risks in career"),
        11: ("Massive gains possible — stay ethical", "Donate part of gains to charity"),
        12: ("Foreign travel strong — hidden expenses", "Donate on Saturdays. Spiritual practice"),
    },
    "Ketu": {
        1:  ("Spiritual focus — worldly detachment", "Keep cat. Daily meditation"),
        2:  ("Detachment from wealth — ancestral matters", "Honor ancestors. Donate food"),
        3:  ("Spiritual communication — past life siblings", "Write or teach spiritual subjects"),
        4:  ("Detachment from home — past life mother karma", "Serve mother. Donate blankets"),
        5:  ("Past life children karma — spiritual intelligence", "Teach children spiritual values"),
        6:  ("Past life enemies dissolve — karma clears", "Forgive enemies. Donate to hospitals"),
        7:  ("Detachment in marriage — spiritual partnership", "Spiritual practice with spouse"),
        8:  ("Deep occult access — past life wisdom", "Study astrology or sacred sciences"),
        9:  ("Past life dharma — spiritual father figure", "Visit temples. Respect spiritual teachers"),
        10: ("Past life career karma — detachment from status", "Work for meaning not recognition"),
        11: ("Detachment from gains — spiritual aspirations", "Donate gains. Avoid attachment"),
        12: ("Liberation energy strong — moksha path open", "Intensive spiritual practice this year"),
    },
    "Mars": {
        1:  ("High energy year — leadership strong", "Channel energy into productive work"),
        2:  ("Financial aggression — bold wealth moves", "Donate wheat to poor on Tuesdays"),
        3:  ("Exceptional courage — communication bold", "Start brave ventures now"),
        4:  ("Property matters active — home energy high", "Buy or improve property this year"),
        5:  ("Competitive children — speculative energy", "Sports and competition favored"),
        6:  ("Enemies defeated — debts resolved", "Take on challenges boldly"),
        7:  ("Partnership conflicts possible — assert carefully", "Avoid ego clashes with partner"),
        8:  ("Accident risk — transformation through action", "Drive carefully. Avoid surgery if possible"),
        9:  ("Fortune through courage — dharmic action", "Take principled bold action"),
        10: ("Career aggression — leadership recognized", "Assert yourself in career now"),
        11: ("Gains through boldness — income rises", "Take calculated financial risks"),
        12: ("Hidden expenses — energy leaks", "Avoid Mars transiting 12th — rest and recover"),
    },
    "Venus": {
        1:  ("Beauty and charm strong — relationships bloom", "Wear white on Fridays"),
        2:  ("Wealth through art and relationships", "Donate to women on Fridays"),
        3:  ("Creative communication — artistic expression", "Create or appreciate art now"),
        4:  ("Home beautification — domestic happiness", "Decorate home. Host family"),
        5:  ("Romance and children blessed", "Express love openly this year"),
        6:  ("Relationship challenges — health from luxury", "Moderate indulgences"),
        7:  ("Marriage peak — partnerships blessed", "Invest in relationship quality now"),
        8:  ("Hidden relationships — transformation through love", "Be honest in all relationships"),
        9:  ("Fortune through relationships", "Travel with partner. Spiritual together"),
        10: ("Career through beauty and relationships", "Leverage charm in professional life"),
        11: ("Gains through women and arts", "Collaborate with female partners"),
        12: ("Secret relationships — foreign love", "Be transparent to avoid complications"),
    },
    "Mercury": {
        1:  ("Sharp intellect year — communication peak", "Start writing or learning projects"),
        2:  ("Business intelligence — wealth through communication", "Trade and negotiate boldly"),
        3:  ("Exceptional communication skills active", "Write, speak, teach — all favored"),
        4:  ("Intellectual home environment", "Study at home. Educate children"),
        5:  ("Creative intelligence peak — speculation possible", "Use intellect in speculation carefully"),
        6:  ("Intellectual enemies — litigation possible", "Document everything. Avoid verbal conflicts"),
        7:  ("Business partnerships favored", "Sign contracts and agreements now"),
        8:  ("Research and investigation sharp", "Deep research yields results now"),
        9:  ("Higher learning peak — foreign education", "Study philosophy or higher subjects"),
        10: ("Career through intellect and communication", "Present ideas boldly in career"),
        11: ("Gains through business and communication", "Network and negotiate for gains"),
        12: ("Intellectual expenses — foreign communication", "Manage communication costs"),
    },
    "Sun": {
        1:  ("Authority and soul energy peak", "Offer water to Sun at sunrise daily"),
        2:  ("Family leadership — financial authority", "Take charge of family finances"),
        3:  ("Courageous self-expression", "Lead communication boldly"),
        4:  ("Authority at home — father energy strong", "Honor father. Take charge at home"),
        5:  ("Creative authority — children in spotlight", "Express creativity with confidence"),
        6:  ("Authority over enemies — government help", "Assert rights. Seek government support"),
        7:  ("Partnership authority — ego in relationships", "Lead partnerships without dominating"),
        8:  ("Authority over hidden matters", "Investigate hidden issues with confidence"),
        9:  ("Dharmic authority — fortune through leadership", "Lead with principles"),
        10: ("Career peak — maximum authority year", "Take on leadership roles now"),
        11: ("Authority brings gains", "Lead groups and organizations"),
        12: ("Authority in foreign or spiritual matters", "Lead spiritual or foreign projects"),
    },
    "Moon": {
        1:  ("Emotional sensitivity peak — public visibility", "Offer milk to Shiva on Mondays"),
        2:  ("Emotional wealth — family nourishment", "Feed family well. Donate milk"),
        3:  ("Emotional communication — intuitive expression", "Write from the heart"),
        4:  ("Emotional home bliss — mother's blessings", "Spend time with mother"),
        5:  ("Emotional creativity — children's happiness", "Express emotions creatively"),
        6:  ("Emotional health challenges — sensitivity high", "Avoid stress. Rest and nourish"),
        7:  ("Emotional partnerships — public relationships", "Nurture partner emotionally"),
        8:  ("Emotional transformation — deep feelings", "Allow feelings to surface and heal"),
        9:  ("Emotional fortune — intuitive dharma", "Trust intuition in spiritual matters"),
        10: ("Public emotional recognition", "Show authentic emotions in public life"),
        11: ("Emotional gains — public popularity", "Connect emotionally with large groups"),
        12: ("Emotional release — spiritual sensitivity", "Meditate. Release emotional burdens"),
    },
}

# LK fixed sign → house mapping (sign IS the house — lagna irrelevant)
LK_SIGN_TO_HOUSE = {
    "Aries": 1, "Taurus": 2, "Gemini": 3, "Cancer": 4,
    "Leo": 5, "Virgo": 6, "Libra": 7, "Scorpio": 8,
    "Sagittarius": 9, "Capricorn": 10, "Aquarius": 11, "Pisces": 12,
}

SLOW_PLANETS = {"Jupiter", "Saturn", "Rahu", "Ketu"}


def build_teva_context_block(transit_data: dict, natal_lagna: str = "") -> str:
    """
    Build Teva annual planet table for LLM context.
    IMPORTANT: LK uses fixed sign-to-house mapping, NOT lagna-based houses.
    Aries=1, Taurus=2 ... Pisces=12 regardless of lagna.
    """
    transits = transit_data.get("current_transits", [])
    if not transits:
        return "TEVA: Transit data not available"

    lines = [
        "TEVA — ANNUAL PLANET TABLE (Lal Kitab)",
        "NOTE: LK uses fixed houses — Aries=1, Taurus=2 ... Pisces=12",
        "",
        "SLOW PLANET TRANSITS (year-long effects — highest priority):",
    ]

    slow_found = False
    for t in transits:
        planet = t.get("planet","")
        if planet not in SLOW_PLANETS:
            continue
        if "error" in t:
            continue

        slow_found   = True
        sign         = t.get("current_sign","")
        lk_house     = LK_SIGN_TO_HOUSE.get(sign, 0)  # LK fixed house
        natal_house  = t.get("natal_house", 0)
        effect_data  = LK_TRANSIT_EFFECTS.get(planet, {}).get(lk_house, ("",""))
        effect       = effect_data[0] if effect_data else ""
        remedy       = effect_data[1] if effect_data else ""

        lines.append(f"  {'⚡' if planet in ('Jupiter','Rahu') else '⚠'} {planet} in {sign} → LK house {lk_house}")
        lines.append(f"    Effect: {effect}")
        if remedy:
            lines.append(f"    Remedy: {remedy}")
        if t.get("transit_over_natal"):
            lines.append(f"    ★ Transiting over natal {planet} — DOUBLE intensity this year")

    if not slow_found:
        lines.append("  No slow planet data available")

    lines += ["", "FAST PLANET TRANSITS (month-level effects):"]

    for t in transits:
        planet = t.get("planet","")
        if planet in SLOW_PLANETS:
            continue
        if "error" in t:
            continue

        sign        = t.get("current_sign","")
        lk_house    = LK_SIGN_TO_HOUSE.get(sign, 0)
        effect_data = LK_TRANSIT_EFFECTS.get(planet, {}).get(lk_house, ("",""))
        effect      = effect_data[0] if effect_data else ""

        lines.append(f"  • {planet} in {sign} → LK house {lk_house}: {effect}")

    lines += [
        "",
        "TEVA RULES FOR PREDICTION:",
        "  • Slow planets (Jupiter/Saturn/Rahu/Ketu) = year-long theme",
        "  • Fast planets = month-level emphasis",
        "  • When transit house matches Dasha theme = HIGH confidence timing",
        "  • Transit over natal planet = double activation — strongest signal",
        "  • Always mention slow planet transits when answering timing questions",
    ]

    return "\n".join(lines)
