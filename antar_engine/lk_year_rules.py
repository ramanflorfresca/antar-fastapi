"""
lk_year_rules.py — Lal Kitab Varshphal (year) RULE DATA, Phase 1.

Source: Pt. Roop Chand Joshi's Lal Kitab, as rendered in
  • "Lal Kitab — Sure Shot Betting and Remedies" (Umesh Sharma / Subhash Jain)
  • "Text Book of Lal Kitab — Based on Five Traditional Classics (1939–1952)"
Both supplied by the founder; rules distilled (not reproduced) for encoding.

This module holds VALIDATED FACTS only (planet ages, significators, the
dormant→awakening event table, dusthana/event houses). It does NOT yet hold the
planet×house verdicts or the benefic/malefic special-rule gates — those come in
Phase 2 after the "Details: Planets in Various Houses", "Ameliorations"
(remedies) and "How Planets Relate / Awakening of Dormant Planets" sections are
extracted.

The ANNUAL CHART SPINE already exists and is authentic:
    antar_engine.varshaphal_table.VARSHAPHAL_TABLE / get_annual_house
The REMEDY table already exists:
    antar_engine.lal_kitab.REMEDIES  (validate vs the book's "Ameliorations")

NOT WIRED into any endpoint yet — pure data, safe to import.
"""

# ── LK planet influence-spans ("age" of each planet) ─────────────────────────
# Book: Jupiter 16, Sun 21, Moon 24, Venus 25, Mars 28, Mercury 34, Saturn 36,
# Rahu 42, Ketu 48. (Matches data/age_triggers_and_houses.json maturity ages.)
LK_PLANET_AGES = {
    "Jupiter": 16, "Sun": 21, "Moon": 24, "Venus": 25, "Mars": 28,
    "Mercury": 34, "Saturn": 36, "Rahu": 42, "Ketu": 48,
}

# ── Significators (karaka life-nouns), per Roop Chand ─────────────────────────
# Spouse is gender-dependent — see spouse_karaka(). The book: "the lady's
# husband is Jupiter" (woman → Jupiter); the husband–wife bond runs through
# Venus (man → wife = Venus). Mars governs opposite-sex *relations*, energy and
# property — NOT the husband-karaka.
LK_SIGNIFICATORS = {
    "Sun":     ["father", "authority", "government / status", "health", "the self"],
    "Moon":    ["mother", "mind", "emotions", "mental peace", "the public"],
    "Mars":    ["energy", "courage", "property / land", "siblings",
                "opposite-sex relations", "disputes / blood"],
    "Mercury": ["business", "learning / education", "money", "speech",
                "sister / daughter / sister-in-law"],
    "Jupiter": ["wisdom", "wealth / gold", "dharma", "teacher", "children",
                "husband (for a woman)"],
    "Venus":   ["marriage", "spouse / wife (for a man)", "luxury", "vehicles",
                "pleasure", "beauty"],
    "Saturn":  ["profession / labour", "servants", "longevity",
                "justice / litigation", "delays", "iron / oil / machinery"],
    "Rahu":    ["foreign", "in-laws", "sudden / unexpected", "technology",
                "illusion / anxiety"],
    "Ketu":    ["son / progeny", "spirituality", "grandfather",
                "loss / separation", "the occult"],
}


def spouse_karaka(gender: str) -> str:
    """Book husband-karaka rule: woman → Jupiter (husband), man → Venus (wife).
    Unknown/other gender → None (read the 7th house generically instead)."""
    g = (gender or "").strip().lower()
    if g in ("f", "female", "woman", "w"):
        return "Jupiter"
    if g in ("m", "male", "man"):
        return "Venus"
    return None


# ── Dormant→awakening event table (Book 1, p86) ──────────────────────────────
# A planet stays "dormant" until the listed life-event occurs after the min age;
# its ill-effect tends to surface in the listed years. This is the LK life-event
# spine. Houses are added in Phase 2 (event fires strongest via 6/8/12 + transit).
LK_DORMANT_EVENTS = {
    "Jupiter": {"trigger": "starting a business or job",            "min_age": 16, "ill_years": [6, 22]},
    "Sun":     {"trigger": "a government contract or job",          "min_age": 22, "ill_years": [2, 24]},
    "Moon":    {"trigger": "starting formal education",             "min_age": 24, "ill_years": [1, 25]},
    "Venus":   {"trigger": "the native's marriage",                 "min_age": 25, "ill_years": [3, 28]},
    "Mars":    {"trigger": "a relationship with the opposite sex",  "min_age": 28, "ill_years": [5, 34]},
    "Mercury": {"trigger": "business, or marriage of a daughter/sister", "min_age": 34, "ill_years": [2, 36]},
    "Saturn":  {"trigger": "owning a house",                        "min_age": 36, "ill_years": [6, 42]},
    "Rahu":    {"trigger": "relations with in-laws beginning",      "min_age": 42, "ill_years": [2, 48]},
    "Ketu":    {"trigger": "the birth of a child",                  "min_age": 48, "ill_years": [3, 51]},
}

# ── House classification for the year reading ────────────────────────────────
DUSTHANA = (6, 8, 12)          # trouble houses
EVENT_HOUSE = 8                # sudden/unexpected event (loss OR unexpected gain)
KENDRA = (1, 4, 7, 10)         # strong / supported
TRIKONA = (1, 5, 9)            # fortunate
# Saturn is benefic in Jupiter's houses (book): 2, 5, 9, 12.
SATURN_BENEFIC_HOUSES = (2, 5, 9, 12)


def planet_significations(planet: str, gender: str = "") -> list:
    """Life-nouns a planet rules this year. Adds the gender-correct spouse tag
    so the reader can say 'your husband/wife' when the spouse karaka is lit."""
    base = list(LK_SIGNIFICATORS.get(planet, []))
    if planet == spouse_karaka(gender):
        tag = "your husband" if planet == "Jupiter" else "your wife"
        if tag not in base:
            base = [tag] + base
    return base


# ── SPECIAL RULES ────────────────────────────────────────────────────────────
# Bait / transfer (Book 1, p83-84): when a planet turns malefic in the year it
# does not always hit its own domain — it transfers the ill-effect onto a "bait"
# relation. This is the precision layer for WHO/WHAT suffers.
LK_BAIT_TRANSFER = {
    "Mars":    {"bait": "Ketu",   "suffers": "the native's son (via Saturn)"},
    "Venus":   {"bait": "Moon",   "suffers": "the mother (eye trouble)"},
    "Jupiter": {"bait": "Ketu",   "suffers": "children / maternal uncle"},
    "Sun":     {"bait": "Ketu",   "suffers": "the Ketu domain (son, legs)"},
    "Moon":    {"bait": "Jupiter/Mars/Sun", "suffers": "its friend-planets' domains"},
    # Shadow planets act DIRECTLY on what they signify (no bait):
    "Rahu":    {"bait": None,     "suffers": "in-laws (wife's / sister's side)"},
    "Ketu":    {"bait": None,     "suffers": "the native's son, or his own legs"},
}

# Clean relationship principles (Book 1, p85 "Important of this table").
# Encoded as facts; the FULL 9-planet friend/foe grid OCR'd noisily and is
# pending a clean pass + founder confirmation before it gates predictions.
LK_RELATION_PRINCIPLES = [
    "Moon and Venus are equal in strength but mutually inimical.",
    "Mars and Saturn are equal in power, but Mars is inimical to Saturn.",
    "Moon and Mercury are equal in strength, but Mercury is inimical to Moon.",
    "Rahu and Jupiter are silent together; but in the 2nd house Rahu is subordinate to Jupiter.",
    "Mercury-Jupiter and Moon-Mercury are inimical, EXCEPT when posited together "
    "in the 2nd or 4th house — there they form a strong wealth/prosperity friendship.",
]

# Awakening of dormant planets (Book 1, p85-86): a dormant house is awakened by
# doing the remedy of the planet mapped to that house number.
# NOTE: houses 7-12 still to be OCR'd — marked None until confirmed.
LK_DORMANT_AWAKEN_HOUSE = {
    1: "Mars", 2: "Moon", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Rahu",
    7: "Venus", 8: "Moon", 9: "Jupiter", 10: "Saturn", 11: "Jupiter", 12: "Ketu",
}

# ── Planetary relationships (DIRECTIONAL — A may befriend B while B is foe to A).
# Friend in the same house strengthens; foe in the same house spoils. Mercury's
# row is the one OCR-ambiguous cell (the book prints two non-identical rows) —
# flagged for founder confirmation.
LK_FRIEND_FOE = {
    "Sun":     {"friends": ["Jupiter", "Moon", "Mars"],            "foes": ["Venus", "Saturn", "Rahu", "Ketu"], "same": []},
    "Moon":    {"friends": ["Venus", "Mars", "Jupiter"],           "foes": ["Sun", "Mercury", "Rahu", "Ketu"],  "same": ["Saturn"]},
    "Mars":    {"friends": ["Sun", "Moon", "Jupiter"],             "foes": ["Mercury", "Ketu", "Rahu"],         "same": ["Saturn", "Venus"]},
    "Mercury": {"friends": ["Sun", "Saturn", "Rahu", "Mars"],      "foes": ["Moon", "Ketu", "Venus"],           "same": ["Saturn", "Ketu", "Jupiter"], "_uncertain": True},
    "Jupiter": {"friends": ["Sun", "Moon", "Mars"],               "foes": ["Mercury", "Venus", "Saturn", "Rahu"], "same": []},
    "Venus":   {"friends": ["Saturn", "Mercury", "Ketu"],          "foes": ["Sun", "Moon", "Rahu", "Mars"],     "same": ["Mars", "Jupiter"]},
    "Saturn":  {"friends": ["Mercury", "Venus", "Rahu"],           "foes": ["Moon", "Sun", "Mars"],             "same": ["Ketu", "Jupiter"]},
    "Rahu":    {"friends": ["Mercury", "Venus", "Ketu"],           "foes": ["Saturn", "Sun", "Mars"],           "same": ["Moon", "Jupiter"]},
    "Ketu":    {"friends": ["Jupiter", "Saturn", "Mercury", "Venus", "Rahu"], "foes": ["Moon", "Mars"],         "same": ["Sun"]},
}

# ── Two-planet conjunction / "acts-as" rules (Book 1, pp.80-84). When the two
# named planets share a house this year, apply the effect/transform.
# 4-tuple: (planetA, planetB, technical_effect, PLAIN user-facing phrasing).
LK_COMBINATIONS = [
    ("Rahu", "Ketu", "together act as an artificial Venus (wealth/ease shifts)",
     "two hidden forces combine and stir matters of money, comfort and closeness"),
    ("Rahu", "Ketu", "in the 4th house, malefic effect is suppressed (virtuous)",
     "two hidden forces settle and soften the year's hardest edges"),
    ("Saturn", "Jupiter", "together turn virtuous — Jupiter converts Saturn's malefic to benefic",
     "patience and good judgment combine — a hard area becomes workable"),
    ("Sun", "Mercury", "together make Mars benefic (good for age & children)",
     "confidence and clear thinking combine and work in your favour"),
    ("Sun", "Saturn", "together make Mars malefic",
     "pride and pressure combine — guard your temper and your health"),
    ("Moon", "Rahu", "together harm Mercury's people (sister, daughter) and commerce",
     "restlessness mixes with mood — watch your business and the women close to you"),
    ("Sun", "Venus", "together act as Jupiter for matters of children",
     "warmth and affection combine — a good stretch for children"),
    ("Sun", "Jupiter", "together act as Moon for parents",
     "confidence and wisdom combine — good for home and parents"),
]

# ── Plain user-facing life-area label per planet (NO planet names, NO house
# numbers). The spouse label is added gender-correctly by the engine.
PLAIN_DOMAIN = {
    "Sun":     "your standing and your father",
    "Moon":    "your home and your mother",
    "Mars":    "your drive, property and siblings",
    "Mercury": "your work, money and communication",
    "Jupiter": "your growth, learning and children",
    "Venus":   "your relationships and comforts",
    "Saturn":  "your career and responsibilities",
    "Rahu":    "sudden and unfamiliar matters",
    "Ketu":    "what you're letting go of and inner life",
}

# ── Special planet states (Book 1, pp.84-86). Short criteria for the engine.
LK_PLANET_STATES = {
    "blind":       "two+ planets in the 10th — they blind each other; career instability",
    "night_blind": "Sun in 4th with Saturn in 7th — harms finances & family",
    "virtuous":    "a malefic neutralised: Rahu/Ketu in 4th, malefic+Moon, Saturn in 11th, or Saturn+Jupiter together",
    "companion":   "two planets in each other's natural houses — mutual aversion neutralised",
    "competitive": "two friends joined by an enemy planet — friendship turns to enmity, native harmed",
    "established": "a planet free of any malefic/shadow — strong, strongly shapes destiny",
    "dormant":     "a planet giving no effect until its remedy (see LK_DORMANT_AWAKEN_HOUSE) or its triggering life-event",
}


# ── Planet × house YEAR verdicts (distilled; Book 1 "Details: Planets in
# Various Houses"). good/bad = short domain summary, refs = the book's
# "Sr. No." remedy indices for that planet. Fills in incrementally — the
# engine falls back to significator + house meaning where a cell is absent.
LK_HOUSE_VERDICTS = {
    "Jupiter": {
        1:  {"good": "learning, law/medicine/editing, high inheritance, educated family",
             "bad": "blood disorders, education broken by ancestral debt, hard on father", "refs": [6, 7, 10, 12]},
        2:  {"good": "wealth, high education, in-law support, business profit",
             "bad": "family ruin, fines, poor spouse health, loss in gold/jewelry trade", "refs": [5, 6, 10, 11, 12]},
        3:  {"good": "wisdom, wealth, serves siblings, gains from travel, writing/editing",
             "bad": "disrepute via children, insults elders, quarrelsome, cheating", "refs": [2, 3, 4, 8, 9, 11]},
        4:  {"good": "high learning, owns house+vehicle, scholarship/lottery/inheritance, good for parents",
             "bad": "self-harm, poor eyesight, affairs → loss of family happiness, childlessness/poverty", "refs": [5, 6, 10, 11, 12]},
        5:  {"good": "a son brings progress, wise counsel, success in love, lottery profit, generational wealth",
             "bad": "", "refs": []},
        6:  {"good": "receives unasked, fame, defeats foes, servants, joy from children",
             "bad": "poor luck/poor till 34, anxiety, aimless, troubles father, breathing disorders", "refs": [1, 2, 3, 9, 12]},
        7:  {"good": "shines after marriage, partnership profit, religion/astrology",
             "bad": "grief from son, weak support from wife, other women, theft, financial suffering", "refs": [2, 5, 6, 7, 10]},
        8:  {"good": "rich, estate owner, secrecy-keeper, in-law resources (wife brings), long family lifespan",
             "bad": "lives off others, other women, debt despite earnings, cowardice, blood disorders/hypertension", "refs": [1, 2, 6, 7, 8, 11]},
        9:  {"good": "rich-yet-yogi, religious, jewelry-business profit, children's felicity, fame from writing",
             "bad": "poverty/conflict with children & father, harms in-laws, pawns gold", "refs": [2, 5, 11]},
        10: {"good": "profit in craft/work, servants, ruler/org-head, bright luck, completes education",
             "bad": "bad for father, new contacts suffer, wishes smothered, loss of gold", "refs": [1, 2, 6, 9, 12]},
        11: {"good": "worldly ease, top administrative honor, many servants, dutiful son, mansions/vehicles",
             "bad": "no inheritance despite rich father, distresses spouse → ruin, harmed by children/in-laws, troubled old age", "refs": [5, 6, 7, 8, 11]},
        12: {"good": "felicity from children, medicine career, religious/blessed, philanthropic with wealth",
             "bad": "effort without avail, anti-religion, cheating intent, distress from offspring, liver/breathing trouble", "refs": [2, 4, 9, 11]},
    },
    "Sun": {
        1:  {"good": "king-like authority, ties to high officials, independent, travel profits, good for father",
             "bad": "hypertension, anger, eye trouble, conflict with the state, vehicle mishap, education blocked", "refs": [4, 5, 9, 12, 13]},
        2:  {"good": "honor/name in society, expert craftsman, factory owner, court recognition, learned",
             "bad": "trouble via women, loss of money/property in conflict, distress from children & spouse, distresses father", "refs": [1, 2, 3, 11]},
        3:  {"good": "victorious in courts, firm resolve, business/job progress, profit from brothers, math/astrology",
             "bad": "theft, quarrels with kin, bad for mother's family, insults from society", "refs": [1, 2, 4, 11]},
        4:  {"good": "profit from sea-voyages, govt honor, real-estate gains, wife earns, transport profit",
             "bad": "hypertension, work obstacles, eye trouble, vehicle accidents, family strife, insulted by women", "refs": [5, 9, 11, 13]},
        5:  {"good": "govt honor, high status, gambling/lottery profit, high education + mystic sciences, upturn after a son's birth",
             "bad": "insulted by women, worry from children, bad for mother's side, dishonest/sickly, commerce loss", "refs": [4, 8, 9, 10, 13]},
        6:  {"good": "victorious in litigation/govt matters, firm conviction, high-statured family, fame, good for father",
             "bad": "", "refs": []},
        7:  {"good": "luck shines after marriage, benefic for in-laws, partnership profit, litigation resolves easily",
             "bad": "marriage delay, subjugated to spouse, serious illness, break-up with spouse, eye/skin trouble, friction with officials", "refs": [5, 9, 11, 13]},
        8:  {"good": "revives the neglected, big-hearted, money from in-laws, fame, partnership profit, long happy life",
             "bad": "money wasted via other women, litigation loss, embezzlement, spouse differences or untimely loss, eye problems", "refs": [1, 2, 4, 8, 13]},
        9:  {"good": "profit from state administration, religious work, luck through hard work, long-lived family",
             "bad": "distress for father, bad for in-laws, troubled travel, loss in overseas ventures, opposed by spouse's siblings", "refs": [5, 8, 9, 12, 14]},
        10: {"good": "king-like status, leadership, owns vehicle+house, rich, business/govt profit, good for father, able children",
             "bad": "decline in a high job, commerce loss, election defeat, unhappy from children, swinging finances", "refs": [1, 2, 8, 11, 13]},
        11: {"good": "stays clear of vice, honest, friends/kin support, comforts, obedient spouse & children, high aspirations",
             "bad": "untruthful, non-veg harms children, bad for brothers, conflict with paternal uncles/aunts, travel injury/loss", "refs": [1, 2, 3, 5, 10, 12]},
        12: {"good": "profit from overseas commerce",
             "bad": "loss from overseas business/travel, eye disease, ruins ancestral property, harassed by adversaries, mental strain", "refs": [1, 2, 9, 11, 13]},
    },
    "Moon": {
        1:  {"good": "wise, works for all, sea-voyage/govt profit, serves mother, harmony with mother & spouse, moral",
             "bad": "fear of drowning, mental strain, late children, weak vitality, heart disease", "refs": [1, 2, 5, 13, 14]},
        2:  {"good": "good children, sweet speech, profit in white goods, property/wealth from father & in-laws, fame",
             "bad": "sister's ill-health, child/education hindrance, spendthrift, intoxicants, hard on father", "refs": [2, 5, 12, 13, 14]},
        3:  {"good": "distinguished, honored in ruling & intellectual circles, smart, long-living, theft-protected, long journeys",
             "bad": "money loss without theft, sleep disorder, hard on father, insults from kin, loss from journeys", "refs": [2, 3, 6, 7]},
        4:  {"good": "profit from ancestral business + sea travel, liberal, water/white-goods profit, obedient to mother, estate/vehicle joys",
             "bad": "ungrateful, wastes inheritance, family strife", "refs": [2, 5, 10, 13]},
        5:  {"good": "royal favor, victorious, progeny progress, long life", "bad": "oblique conduct, commerce loss, learning blocked, greedy", "refs": [2, 10, 13, 14]},
        6:  {"good": "good for sister/aunt/daughter, sympathetic, job changes", "bad": "loss in dairy/animals, stomach/kidney issues, bad for mother early", "refs": [1, 7, 9, 13]},
        7:  {"good": "wealth at every step, good spouse, overseas profit", "bad": "money shortage, other women, spouse break-up, addictions", "refs": [5, 9, 11, 12]},
        8:  {"good": "reveres parents, long life, good for in-laws", "bad": "govt/court loss, bad for self/mother early, gambling, heart/epilepsy", "refs": [1, 3, 8, 14]},
        9:  {"good": "owns ships/aircraft, honored, religious travel, psychologist", "bad": "petty wanderer, deluded, bad for parents, milk/water loss", "refs": [1, 2, 5, 11, 14]},
        10: {"good": "", "bad": "", "refs": []},
        11: {"good": "joy from mother/progeny, water/milk profit, lawyer/engineer/officer", "bad": "sea-voyage loss, education blocked, no/delayed children, impotence", "refs": [2, 4, 6, 8]},
        12: {"good": "overseas fortune, mysticism/astrology, popular with opposite sex", "bad": "past griefs, wastes inheritance, self-harming, insults, ruins in-laws", "refs": [1, 11, 12, 13]},
    },
    "Venus": {
        1:  {"good": "nurturing, loves vehicles/pets, dresses well, generous, pleasure-rich", "bad": "chases opposite sex, late marriage, sickly/distant spouse, wealth-waster", "refs": [1, 2, 5, 10, 11]},
        2:  {"good": "wealthy officer, artist, profit in cosmetics/perfume, good for in-laws", "bad": "troubled family, childless/adopts, ties with the promiscuous, sickly spouse", "refs": [2, 4, 8, 9, 10]},
        3:  {"good": "both spouses work, devoted spouse, profit from sacred-place work", "bad": "unhappy though rich, sick spouse, sibling losses, travel losses, affairs", "refs": [2, 7, 10]},
        4:  {"good": "mother's care, estate/vehicles, inheritance, amiable monogamous spouse", "bad": "unhappy home, mother-spouse conflict, jilted, progeny trouble, intoxicants", "refs": [4, 9, 10]},
        5:  {"good": "high-status spouse, lottery gains, officer, success in love, happy children", "bad": "in-law trouble, scandal if immoral, late son, abortion risk", "refs": [5, 7, 9, 10]},
        6:  {"good": "own and father's families prosper, becomes govt officer, beats enemies", "bad": "barren wife or troublesome son, many daughters, kidney/skin disease", "refs": [4, 7, 8, 10]},
        7:  {"good": "long life, easeful family, in-law profit, good business partnership", "bad": "progeny hindrance, brother-in-law loss, overspends on spouse, illness risk", "refs": [2, 5, 7, 9, 10]},
        8:  {"good": "aid in litigation, spouse's words come true, in-law yield, foreknowing", "bad": "harms in-laws, hen-pecked, illness, sibling discord, impotence, money waste", "refs": [4, 6, 7, 9]},
        9:  {"good": "ancestral wealth grows, public officer, love-marriage, spiritual, good spouse", "bad": "severe ill-luck, grief-filled family, blood disorder, ill-fated siblings", "refs": [1, 2, 3, 10]},
        10: {"good": "12-yr profit after wedding, photography/music, cosmetics/transport gains, just", "bad": "progeny distress, dim/blind wife, promiscuity, chronic disease", "refs": [2, 4, 5, 9]},
        11: {"good": "discerning, no money shortage, good spouse/children, arts profit, progress after wedding", "bad": "friend/kin discord, cheats women, frequent job changes, son-anxiety", "refs": [1, 2, 3, 4, 8]},
        12: {"good": "caring spouse, gains in spouse's name, happy, mystic/arts interests", "bad": "spouse suffers first, promiscuity with disease, short co-living, spouse may die early", "refs": [3, 6, 7, 9, 10]},
    },
    "Mars": {
        1:  {"good": "profit in wood/iron/housing/machinery; wealth ~28; firm, fearless", "bad": "bad for mother; short-lived/sickly spouse; bad-tempered, accident-prone, eye disease", "refs": [2, 7, 8, 12]},
        2:  {"good": "eldest brother nurtures siblings; good for father; firm decisions; progress after marriage", "bad": "hindered education, hard life; difficulty begetting sons; business losses", "refs": [1, 2, 7, 8]},
        3:  {"good": "has siblings; serves all; wins over enemies; luck rises after marriage", "bad": "bad destiny, losses, debts; kin exploit him; court losses, heart/stomach trouble", "refs": [2, 4, 5, 6, 14]},
        4:  {"good": "house and vehicle; courageous, just; profit in automobiles; ancestral inheritance", "bad": "childless/adopts; hard on spouse/mother-in-law; dull marriage; fire-accident risk", "refs": [1, 2, 3, 5, 9]},
        5:  {"good": "banking/loans business; noble spouse, many sons; medicine trade; blessed lineage", "bad": "difficult first birth; miscarriage risk; son trouble; losses from other women, gambling", "refs": [1, 4, 7, 8]},
        6:  {"good": "progress after marriage; late sons bring ease; good repute, long life", "bad": "late/no progeny, adopts; accident fear, cowardly, sickly, wealth-waster", "refs": [2, 4, 8, 14]},
        7:  {"good": "nourishing family head; wealthy, judge/leader; high official; wishes fulfilled", "bad": "quarrelsome, poor fate; two marriages, short-lived spouse; blood disorders", "refs": [3, 4, 9]},
        8:  {"good": "brave, hardworking, tolerant, victor of conflicts; pleases spouse; in-law profit", "bad": "opposes brothers, cheats; theft/fire loss; mother surgery, wife miscarriages, short-lived", "refs": [2, 6, 8]},
        9:  {"good": "harmony with brothers; victorious, state official, self-made; long rich life", "bad": "unhappy, lives far from family; very bad fate; ill-famed; trouble for father", "refs": [4, 8, 14]},
        10: {"good": "wealth from birth; high officer in forces; plenty of estate; aids social matters", "bad": "loses/sells gold; theft cases, bad name; conflict with authority/prison; trade loss", "refs": [2, 3, 5, 9]},
        11: {"good": "parents rich when native ~13; highly placed, self-made, rich, many friends", "bad": "in debt despite income; no help from kin; bad for mother's side; few children", "refs": [1, 4, 7, 8]},
        12: {"good": "large family head; profit in sweets/sugar/honey; courageous, serves poor; in-law benefits", "bad": "risk to elder brother till 28; imprisonment, suicidal thoughts; obstacles near success", "refs": [4, 7, 8]},
    },
    "Mercury": {
        1:  {"good": "learned, govt official, prestigious degrees, profit from overseas trade", "bad": "mischievous mind, quarrelsome, intoxicants, drawn to black magic", "refs": [2, 4, 6]},
        2:  {"good": "quick-witted, rich, happy, lecturer; bookseller/publisher/stationery profit", "bad": "gambling/shares losses, risk to father, losses in journeys", "refs": [2, 4, 8]},
        3:  {"good": "practices medicine, high education, travel profit, teaching, long life", "bad": "bad luck, money loss in commerce, spendthrift, harm to maternal kin", "refs": [2, 3, 9]},
        4:  {"good": "relieves others' distress, ruler's favour, happy home, writer/editor", "bad": "spouse trouble/breakup, loss in commerce, harm to mother's folks", "refs": [2, 9, 12]},
        5:  {"good": "highly qualified, exam success, consultant/govt servant, astrology interest", "bad": "opposition from children, education hindrance, defame, stomach disorders", "refs": [2, 9, 10, 13]},
        6:  {"good": "doctor/chemist, printing/writing profit, yogi with good foretelling", "bad": "daughter/sister distress, nervous weakness, skin disorders, harm from rulers", "refs": [1, 2, 4, 10]},
        7:  {"good": "overseas trade profit, marriage abroad, owns house/vehicle, wise spouse", "bad": "less amiable family, separation from spouse, loan/partnership losses", "refs": [2, 4, 6, 10]},
        8:  {"good": "happy resolve after 34, rich, learned, senior govt officer, in-laws profit", "bad": "nervous debility, partnership losses, defame, short life, suicidal tendency", "refs": [1, 2, 9, 12]},
        9:  {"good": "serving family, religious, journey profit, high officer, music/astrology", "bad": "ungrateful, breaks word, speech defects, slippery luck, progeny worry", "refs": [1, 2, 3, 8]},
        10: {"good": "agreeable, crafty, sea-voyage profit, editor/writer, knows many languages", "bad": "ill-omened for father, money loss, commerce losses, intoxicants", "refs": [1, 2, 3, 8]},
        11: {"good": "luck rises after 34, shines and nurtures siblings, good-fortune years", "bad": "self-harm from indiscretions, progeny worry, cheating among kin", "refs": [1, 2, 3, 13]},
        12: {"good": "wealth/estate profit, tantra/astrology interest, inherits good property", "bad": "untrustworthy, intoxication, money/progeny worry, lottery losses", "refs": [1, 2, 4, 8]},
    },
    "Saturn": {
        1:  {"good": "long-lived; doctor or high govt officer; father prospers after birth", "bad": "eye trouble; poor education; wastes/loses parental estate; quarrelsome", "refs": [2, 4, 5, 6]},
        2:  {"good": "just, wise; owns vehicle/facilities; profit in coal, leather, property", "bad": "no gains despite effort; bad for in-laws; drawn to intoxicants", "refs": [6, 9, 10, 11]},
        3:  {"good": "dominates enemies; sharp perception; long life; high ruling post", "bad": "quarrels with elder brother; losses in voyages; untruthful; dog-bite fear", "refs": [3, 6, 8, 12]},
        4:  {"good": "owned house and vehicle; happy family; gains from foreign journeys", "bad": "lacks finances; paralysis/kidney disease; rented living; short-lived parents", "refs": [1, 2, 6, 10, 11]},
        5:  {"good": "well-off; good justice; children; gains in film/photography", "bad": "stomach surgery; fines/jailing; first son may not survive; poor luck", "refs": [5, 6, 12]},
        6:  {"good": "never short of wealth; many children; high post; law/old-valuables profit", "bad": "alcohol/meat indulgence; kidney problems; litigation losses with govt", "refs": [1, 2, 3, 5, 6, 10]},
        7:  {"good": "very rich at 36-39; profit from journeys and govt post; big estate", "bad": "cheat/cruel for money yet poor; weaponry fear; unhappy from children", "refs": [5, 8]},
        8:  {"good": "long life; researcher; profit abroad in commerce and partnerships", "bad": "slavery spells; long sickness building house; wall cracks; yearly accidents", "refs": [3, 6, 8, 10, 11]},
        9:  {"good": "lucky, benevolent; astrology interest; big profit in house deals", "bad": "eyes others' wealth/spouse; gambler, jealous, vengeful; losses in iron/wood", "refs": [2, 4, 5, 6]},
        10: {"good": "many properties; tenfold growth; honor and ruling-circle respect", "bad": "intoxicants halt progress; cruel; trouble for parents; estate losses", "refs": [2, 8, 12, 13]},
        11: {"good": "lucky, govt officer; house and vehicle; rich in-laws; never childless", "bad": "lives apart from elder brother; education obstacles; trickery brings ruin", "refs": [1, 6, 9, 11]},
        12: {"good": "baldness brings wealth; estates, big family, luxury houses; helps others", "bad": "crime litigation, fine/punishment; eye problems; henpecked; child troubles", "refs": [1, 5, 6, 9, 12]},
    },
    "Rahu": {
        1:  {"good": "mother's family thrives, big family, govt profit, calm", "bad": "isolation in bad times, blasphemer, wayward, little progress", "refs": [2, 6, 10, 12]},
        2:  {"good": "wealthy, needs met, high officer, profit from spouse", "bad": "theft blame, intoxicants/gambling, legal harm, in-law trouble", "refs": [3, 7, 8, 9]},
        3:  {"good": "steady progress, word is powerful, estates, happy family", "bad": "wavering, friends deny debts, progeny unhappy early", "refs": [3, 4, 9, 10, 14]},
        4:  {"good": "big promotion at 42, in-law estates rise, learned, high official", "bad": "govt loss, two wives/waste, accident fear, mother's side suffers", "refs": [1, 7, 11, 12]},
        5:  {"good": "upright conduct, trade profit, kind, rich, officer favor", "bad": "late/no children, first-child risk, father/in-law death risk", "refs": [2, 3, 4, 6, 9]},
        6:  {"good": "wins enemies, rich, long life, firm resolve, awakened luck", "bad": "wayward, bad company, weapon fear, big swindler, family ruin", "refs": [1, 8, 14]},
        7:  {"good": "wealth/estates, victor over foes, govt officer, ample funds", "bad": "spouse loss, betting loss, contacts ruined, separation risk", "refs": [2, 6, 10, 12]},
        8:  {"good": "luck rises 28-42, in-law money, marriage before 34", "bad": "bad company defames, gambling, litigation, uniform-job loss", "refs": [2, 3, 4, 8, 12]},
        9:  {"good": "honored, many servants, godly, family-loving, happy progeny", "bad": "duped by false saints, sons die in pregnancy, jailed, defamed", "refs": [3, 4, 9, 10, 14]},
        10: {"good": "fair fame, good conduct, ease and wealth, long life", "bad": "head injury/fall, weak eyes, education hampered, money loss", "refs": [4, 8, 12]},
        11: {"good": "rich, happy progeny, owns house/vehicle, wins quarrels", "bad": "wealth wasted, fire/eye/leg loss, penury till 36", "refs": [2, 4, 5, 11, 12]},
        12: {"good": "restful sleep, rich, big family, secret knowledge, in-law luck", "bad": "can't bear family burden, air-castles, suicidal, limb atrophy", "refs": [1, 2, 7, 13, 14]},
    },
    "Ketu": {
        1:  {"good": "steady progress; eldest serves parents; good progeny; long journeys", "bad": "false notions; loss from others' counsel; below-navel disease; father dog-bite", "refs": [1, 2, 6, 8]},
        2:  {"good": "agent/cashier/high officer; govt grants; long journeys; grateful, aids kin", "bad": "promiscuity; distress to father; job changes no progress; gambling; intoxicants", "refs": [1, 2, 5, 8, 9]},
        3:  {"good": "grateful; helps kin/brothers/friends; 1-3 sons; elders favor", "bad": "urinary disease; vagabond; far from siblings; daughters worry; spouse break-up", "refs": [4, 6, 10]},
        4:  {"good": "moneyed; own house and vehicle; serves guru/parents; firm resolve", "bad": "far from mother; short life of mother/son; diabetes; joint-pain; accidents", "refs": [1, 3, 5]},
        5:  {"good": "large family of sons/grandsons; robust; religious; rich", "bad": "vile company grows with age; children breathing problems; poor", "refs": []},
        6:  {"good": "brave victorious progeny defeats enemies; overseas living; sons", "bad": "stomach/legs/skin disease; dog bite; ruins family; wastes money", "refs": [12]},
        7:  {"good": "wealth grows till 40; brave numerous progeny", "bad": "first spouse dies, second follows; affairs; false promises; stress and disease", "refs": [2, 6, 10]},
        8:  {"good": "two marriages; rich; beautiful well-disposed wife; long lifespan", "bad": "urinary-organ disease; joint-pain; boils; alcohol/meat; spouse ill health", "refs": []},
        9:  {"good": "high progress few job changes; obedient to father; overseas; high officer", "bad": "bad for mother's side; distress to maternal uncle; issueless; vile company", "refs": [1, 4, 8]},
        10: {"good": "outstanding rich; success in profit ventures; international sportsman; servants", "bad": "years 45-48 loss-making; mother's poor health; eye problems; son anxiety", "refs": [1, 8, 11]},
        11: {"good": "clear future vision; builds big estate; govt regard; gains from journeys", "bad": "issueless or mother/son one dies; house loss; money waste; mental distress", "refs": [2, 5, 6, 12]},
        12: {"good": "high progress; overseas profit; property satisfaction; victor over enemies", "bad": "wastes ancestral estate; bad fame and insults; dog-bite fear; cheat/thug; childless", "refs": [1, 5, 8]},
    },
}

# ── Per-planet "Sr. No." remedy master lists (book "Measures for … up-grading
# in 12 houses"). The house verdicts cite these by number; the engine resolves
# refs to text here (falls back to lal_kitab.REMEDIES). Fills incrementally.
LK_REMEDY_LIST = {
    "Jupiter": {
        1: "Keep a fast on Thursdays.", 2: "Plant a sacred-fig in a public place; worship Hari.",
        3: "Offer heartfelt salutations to Hari.", 4: "Wear a yellow topaz, or tie turmeric-root in yellow cloth on the arm.",
        5: "Apply a turmeric/saffron mark on the forehead.", 6: "Wear pure gold (not if Jupiter is in the 6th).",
        7: "Take a little saffron; apply on navel and forehead.", 8: "Serve Brahmins, your family guru and saints.",
        9: "Hold Garud Purana recitations at family deaths.", 10: "Use yellow generously in home décor.",
        11: "Keep and tend yellow flowering plants.",
        12: "If Jupiter is benefic don't donate Jupiter things; if malefic, don't accept them.",
    },
    "Sun": {
        1: "Keep a fast on Sundays.",
        2: "Offer sweet water to the Sun (or hold Harivamsha Purana readings).",
        3: "Donate wheat, jaggery and copper at a religious place.",
        4: "Keep your conduct clean and blameless.",
        5: "Wear a red ruby in a copper ring on the right ring finger.",
        6: "Float a copper coin down flowing water.",
        7: "Keep the home's main entrance to the east.",
        8: "Keep an open patio/courtyard in the house.",
        9: "Feed roasted wheat and jaggery to monkeys; care for them.",
        10: "Feed brown ants a mix of rice, sugar and white sesame.",
        11: "Keep harmonious contact with local officials.",
        12: "Drive copper nails into the four legs of the bed.",
        13: "Avoid black-marketing, smuggling or illegal hoarding.",
        14: "If the Sun is exalted don't donate Sun things; if in fall, don't accept them.",
    },
    "Venus": {
        1: "Keep a fast on Fridays.", 2: "Serve those around you; care for guests.",
        3: "Donate ghee, potatoes, camphor and mica at a religious place.",
        4: "Donate or serve a good cow (or give cow-feed).", 5: "Wear a diamond.",
        6: "Bury white sorghum, or flow it in water, or feed it to a cow.",
        7: "Agree with and serve your spouse.", 8: "Use perfume; keep fresh fragrance.",
        9: "Always wear decent, undamaged clothes.",
        10: "If Venus is ascending don't donate Venus items; if in fall, don't accept them.",
    },
    "Mars": {
        1: "Keep a fast on Tuesdays.", 2: "Recite the Gayatri mantra regularly.",
        3: "Flow red lentils, coral, honey or vermillion down running water.",
        4: "Offer a sweet mouth-freshener to visiting guests.",
        5: "Flow jaggery-sesame sweets down a water stream.",
        6: "Flow sweets or candy down water (for ascending Mars).",
        7: "Wear coral or a pure copper item.", 8: "Serve your brother and wife's brother.",
        9: "Sleep on a deer-hide sheet.",
        10: "Keep barley grains tied in a red cloth washed in cow-milk in your pocket.",
        11: "Keep a red handkerchief with you most of the time.",
        12: "Wear a pure silver item.",
        13: "Avoid the bastard-teak tree; and one-eyed, bald or issueless men.",
        14: "Do not take a house from an issueless person, even free.",
    },
    "Mercury": {
        1: "Keep a fast on Wednesdays.", 2: "Devi recitation; feed sweets at noon.",
        3: "Flow green lentils and green things down water.",
        4: "Remove non-working phones, radios, TVs and electronics from home.",
        5: "Hole copper coins and flow them down a water stream.",
        6: "Wear an emerald in a tin ring on the left finger.",
        7: "Care for a parrot or goat (Mercury in 2nd/4th).",
        8: "Do not grow basil, money-plant or green plants at home.",
        9: "Pierce the left nostril for 96 hours.",
        10: "Serve daughter, sister and father's sister; take their blessings.",
        11: "Burn yellow shells and flow the ashes in water (ancestral debt).",
        12: "Give green bangles and clothing to eunuchs.",
        13: "Do not keep charmed water, ashes or saint idols at home.",
        14: "Do not keep new unbaked clay utensils at home.",
    },
    "Saturn": {
        1: "Keep a fast on Saturdays.", 2: "Stay fully compliant with the law.",
        3: "Do a rite at a Bhairon temple.", 4: "Donate black lentils, leather and iron articles.",
        5: "Keep milk where serpents abide; care for a black buffalo.",
        6: "Do not lie; donate mustard oil.", 7: "Avoid alcohol and meat/fish.",
        8: "Wear a blue sapphire (if it suits) or a black-horseshoe ring on the middle finger.",
        9: "Serve and care for your paternal uncle; take his blessings.",
        10: "Feed rice, sugar and white sesame to black ants.",
        11: "Feed mustard-oiled chapatti to dogs and crows.",
        12: "Never cheat labourers of their correct dues.",
        13: "If Saturn is exalted don't donate Saturn things; if in fall, don't accept them.",
    },
    "Moon": {
        1: "Keep a fast on Mondays.", 2: "Wear a real white pearl or a silver ornament.",
        3: "Offer milk-water on a Shiva lingam.", 4: "Donate milk, rice or silver.",
        5: "Keep milk under the bed's head side; pour it on acacia roots.",
        6: "Take the blessings of your mother and grandmother.",
        7: "Fix silver pins to the cot legs.", 8: "Keep a glass jar of water; sip Ganges water.",
        9: "Bathe in the Ganges or a good river.", 10: "Bathe in clean river water.",
        11: "Clean all house water-tanks every six months.",
        12: "Don't install a water pump under the house roof.",
        13: "If the Moon is exalted don't donate Moon things; if in fall, don't accept them.",
    },
    "Rahu": {
        1: "Revere Devi Saraswati.", 2: "Never take free electrical goods, blue clothing or steel.",
        3: "Help give a maiden's hand in marriage.", 4: "Donate mustard, sapphire or tobacco (not for self).",
        5: "Don't hoard unused steel or wear blue/sapphire.",
        6: "Donate radishes/barley by weight, or flow charcoal down water.",
        7: "Wear a hessonite (gomed).", 8: "No false witness; keep cordial with in-laws.",
        9: "Don't cut off from family or rush to head it.", 10: "Feed a seven-grain mix to birds.",
        11: "Don't use tobacco in any form.", 12: "Don't waft smoke from an open yard.",
        13: "Keep no chimney/smoke-vent in the kitchen.", 14: "Never lie or cheat in dealings.",
    },
    "Ketu": {
        1: "Worship Ganesh.", 2: "Take a seamless gold ring and two beds as gifts from in-laws.",
        3: "Donate an off-white cow, or serve cows.", 4: "Float sesame, lemon and plantain in water.",
        5: "Don't sleep on a broken bed/floor.", 6: "Wear a black-and-white (hauladari) stone.",
        7: "Avoid low-ethics company; stay ethical.", 8: "Care for and serve boys under age nine.",
        9: "Eat/offer sour foods (lemon, tamarind).", 10: "Donate blankets to night shelters.",
        11: "Float white and black sesame in flowing water.", 12: "Seek Ayurvedic care for vitality if needed.",
    },
}
