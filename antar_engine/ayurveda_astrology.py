"""
antar_engine/ayurveda_astrology.py
Ayurveda + Astrology food and lifestyle recommendations
based on planetary periods and natal chart.
No user input needed — pure calculation.
"""

# Planetary Ayurveda associations
PLANET_DOSHA = {
    "Sun":     {"dosha": "Pitta",       "element": "Fire",         "taste": "pungent, bitter"},
    "Moon":    {"dosha": "Kapha/Vata",  "element": "Water",        "taste": "sweet, salty"},
    "Mars":    {"dosha": "Pitta",       "element": "Fire/Earth",   "taste": "pungent, sour"},
    "Mercury": {"dosha": "Vata/Pitta",  "element": "Earth/Air",    "taste": "astringent, sweet"},
    "Jupiter": {"dosha": "Kapha",       "element": "Ether/Water",  "taste": "sweet, salty"},
    "Venus":   {"dosha": "Kapha/Vata",  "element": "Water/Air",    "taste": "sweet, sour"},
    "Saturn":  {"dosha": "Vata",        "element": "Air/Space",    "taste": "astringent, pungent"},
    "Rahu":    {"dosha": "Vata",        "element": "Air/Space",    "taste": "astringent"},
    "Ketu":    {"dosha": "Pitta/Vata",  "element": "Fire/Air",     "taste": "pungent, bitter"},
}

PLANET_AYURVEDA_FOODS = {
    "Sun": {
        "planet_quality": "Solar energy — vitality, leadership, ego",
        "strengthen_with": [
            "Wheat and wheat products — Sun's grain",
            "Saffron milk — golden solar energy",
            "Almonds soaked overnight — brain and vitality",
            "Orange and yellow foods — carrots, oranges, turmeric",
            "Cardamom in your morning drink",
            "Jaggery instead of white sugar",
        ],
        "balance_with": [
            "Coconut water on Sundays",
            "Rose petal jam (gulkand) — cools excess Pitta",
            "Coriander seeds in food — reduces heat",
        ],
        "avoid_if_afflicted": [
            "Excess spicy food — amplifies already high Pitta",
            "Alcohol — depletes solar ojas",
            "Processed salt",
        ],
        "best_day": "Sunday",
        "remedy_food": "Wheat halwa with ghee offered to Sun deity on Sunday morning",
        "herb": "Ashwagandha — builds solar strength (ojas)",
    },
    "Moon": {
        "planet_quality": "Lunar energy — mind, emotions, intuition, mother",
        "strengthen_with": [
            "White foods — milk, rice, white sesame",
            "Kheer (rice pudding) on Monday evenings",
            "Coconut in any form — coconut water, coconut chutney",
            "Pearl millet (bajra) rotis — Moon's grain",
            "Fennel seeds after meals — calms mind",
            "Chamomile or brahmi tea before sleep",
        ],
        "balance_with": [
            "Shatavari in warm milk — deeply nourishing",
            "Moonflower honey",
            "Lotus seeds — calms excess Vata",
        ],
        "avoid_if_afflicted": [
            "Cold beverages — aggravate watery Kapha",
            "Excess dairy if Kapha dominant",
            "Eating after 8pm — Moon rules digestion at night",
        ],
        "best_day": "Monday",
        "remedy_food": "Offer rice pudding to the Moon on full Moon night",
        "herb": "Shatavari — the great nourisher, balances Moon energy",
    },
    "Mars": {
        "planet_quality": "Martian energy — action, ambition, conflict, courage",
        "strengthen_with": [
            "Red lentils (masoor dal) — Mars' pulse",
            "Beetroot — builds blood and Mars energy",
            "Pomegranate — blood builder",
            "Red rice or red quinoa",
            "Dates and figs — iron-rich, builds strength",
            "Ginger in every meal — activates Mars fire",
        ],
        "balance_with": [
            "Coriander chutney — cools excess heat",
            "Buttermilk (chaas) with cumin — digestive cooling",
            "Amla (Indian gooseberry) — balances Pitta",
        ],
        "avoid_if_afflicted": [
            "Excess meat — amplifies aggression",
            "Very spicy food — already high Pitta",
            "Alcohol on Tuesday",
            "Fried foods",
        ],
        "best_day": "Tuesday",
        "remedy_food": "Red lentil dal with ghee on Tuesday",
        "herb": "Triphala — cleanses and balances Mars excesses",
    },
    "Mercury": {
        "planet_quality": "Mercury energy — communication, intelligence, trade, nervous system",
        "strengthen_with": [
            "Green moong dal — Mercury's pulse",
            "All green vegetables — spinach, methi, curry leaves",
            "Green cardamom in chai",
            "Mint chutney with meals",
            "Almonds and walnuts — nervous system food",
            "Green apples",
        ],
        "balance_with": [
            "Brahmi ghee — sharpens Mercury (intellect)",
            "Tulsi tea — Mercury's herb",
            "Sesame seeds — grounds Mercury's Vata",
        ],
        "avoid_if_afflicted": [
            "Processed and junk food — dulls Mercury",
            "Excess talking while eating",
            "Inconsistent meal times — Mercury needs rhythm",
        ],
        "best_day": "Wednesday",
        "remedy_food": "Green moong dal khichdi on Wednesday",
        "herb": "Brahmi — the intelligence herb, feeds Mercury",
    },
    "Jupiter": {
        "planet_quality": "Jupiter energy — wisdom, expansion, luck, teacher, liver",
        "strengthen_with": [
            "Yellow foods — yellow dal, turmeric, banana",
            "Chickpeas (chana) — Jupiter's pulse",
            "Turmeric milk (haldi doodh) on Thursday evenings",
            "Saffron — Jupiter's spice",
            "Banana on Thursday mornings",
            "Sweet potato — grounding and nourishing",
        ],
        "balance_with": [
            "Triphala churna — cleanses Jupiter's organ (liver)",
            "Bitter gourd (karela) juice — detoxifies",
            "Fennel and cumin water — aids Jupiter digestion",
        ],
        "avoid_if_afflicted": [
            "Excess sweets — Jupiter already sweet",
            "Overeating — Jupiter rules expansion",
            "Very fatty foods — burdens the liver",
        ],
        "best_day": "Thursday",
        "remedy_food": "Yellow dal with turmeric and ghee on Thursday",
        "herb": "Vidanga and turmeric — Jupiter's herbs",
    },
    "Venus": {
        "planet_quality": "Venus energy — beauty, love, luxury, reproduction, kidneys",
        "strengthen_with": [
            "White kidney beans or rajma — Venus' pulse",
            "Rice with ghee — Venus loves sweetness and richness",
            "Saffron, rose, cardamom in foods",
            "Gulkand (rose jam) — Venus food",
            "Cow's milk — especially on Fridays",
            "Sweet fruits — white grapes, figs, pears",
            "Mishri (rock sugar) instead of sugar",
        ],
        "balance_with": [
            "Rose water in drinks and cooking",
            "Cucumber and coconut — cooling Venus",
            "Fennel seeds — digestive and Venus-balancing",
        ],
        "avoid_if_afflicted": [
            "Artificial sweeteners",
            "Excess alcohol — depletes Venus ojas",
            "Onion and garlic on Fridays (traditional)",
        ],
        "best_day": "Friday",
        "remedy_food": "Rice kheer with rose and saffron on Friday",
        "herb": "Shatavari and rose — Venus herbs for reproductive health",
    },
    "Saturn": {
        "planet_quality": "Saturn energy — discipline, karma, bones, longevity, structure",
        "strengthen_with": [
            "Black sesame (til) — Saturn's seed",
            "Black urad dal — Saturn's pulse",
            "Mustard oil in cooking on Saturdays",
            "Dark leafy greens — kale, fenugreek",
            "Black pepper in everything",
            "Iron-rich foods — spinach, dates",
            "Sesame laddoos on Saturdays",
        ],
        "balance_with": [
            "Sesame oil massage before bath on Saturday",
            "Ashwagandha — strengthens Saturn's domain (bones, longevity)",
            "Turmeric and black pepper together",
        ],
        "avoid_if_afflicted": [
            "Non-vegetarian food on Saturday (traditional)",
            "Cold and dry foods — increase Vata",
            "Stale or leftover food",
            "Eating alone in darkness",
        ],
        "best_day": "Saturday",
        "remedy_food": "Black sesame laddoos on Saturday, donated to poor",
        "herb": "Ashwagandha — Saturn's herb for endurance and structure",
    },
    "Rahu": {
        "planet_quality": "Rahu energy — ambition, illusion, technology, foreign, sudden events",
        "strengthen_with": [
            "Barley (jau) — Rahu's grain",
            "Garlic and onion — Rahu foods",
            "Coconut — offered to Rahu for pacification",
            "Urad dal and sesame together",
            "Blue/purple foods — blueberries, purple cabbage",
        ],
        "balance_with": [
            "Coconut water on Saturdays",
            "Fasting on Saturdays — calms Rahu",
            "Neem juice or neem in food — purifies",
        ],
        "avoid_if_afflicted": [
            "Excess alcohol — Rahu amplifies addiction patterns",
            "Leftover and stale food",
            "Eating non-vegetarian at night",
            "Black-colored foods during Rahu periods",
        ],
        "best_day": "Saturday (with Saturn)",
        "remedy_food": "Coconut and sesame offered on Saturday",
        "herb": "Neem and tulsi — purify Rahu's shadow energies",
    },
    "Ketu": {
        "planet_quality": "Ketu energy — liberation, spirituality, past life, sudden losses, moksha",
        "strengthen_with": [
            "Horse gram (kulthi dal) — Ketu's pulse",
            "Sesame in all forms",
            "Root vegetables — carrots, radish, beetroot",
            "Fasting on Tuesdays — Ketu responds to austerity",
            "Simple, sattvic food — avoid elaborate meals",
        ],
        "balance_with": [
            "Turmeric and saffron — purify Ketu",
            "Ghee — the most sattvic food",
            "Silence while eating — Ketu is the silent planet",
        ],
        "avoid_if_afflicted": [
            "Non-vegetarian food",
            "Overly stimulating foods",
            "Eating with electronic screens",
            "Processed and artificial food",
        ],
        "best_day": "Tuesday",
        "remedy_food": "Til (sesame) and jaggery laddoos",
        "herb": "Triphala and ashwagandha — Ketu's herbs for grounding",
    },
}

DOSHA_GENERAL_GUIDANCE = {
    "Pitta": {
        "description": "Fire dominant — transformative but can burn",
        "balance_foods": [
            "Cooling foods — cucumber, mint, coriander, coconut",
            "Sweet fruits — melons, grapes, pears",
            "Dairy — milk, ghee, butter (in moderation)",
            "Cooling spices — cardamom, fennel, coriander",
        ],
        "avoid": ["Chilli", "Tomatoes in excess", "Alcohol", "Vinegar", "Sour foods"],
        "eat_at": "Regular meal times — Pitta needs routine",
    },
    "Vata": {
        "description": "Air dominant — creative but can scatter",
        "balance_foods": [
            "Warm, cooked, oily foods — nothing raw or cold",
            "Grounding foods — root vegetables, heavy grains",
            "Sweet, sour, salty tastes",
            "Sesame oil in cooking",
            "Warm milk with ghee before bed",
        ],
        "avoid": ["Raw salads", "Cold drinks", "Dry crackers", "Beans without soaking", "Excess caffeine"],
        "eat_at": "Same time every day — Vata needs grounding",
    },
    "Kapha": {
        "description": "Earth/Water dominant — stable but can stagnate",
        "balance_foods": [
            "Light, dry, warm foods",
            "Pungent, bitter, astringent tastes",
            "Honey instead of sugar",
            "Spicy foods — ginger, black pepper, mustard",
            "Light grains — millets, corn, barley",
        ],
        "avoid": ["Dairy excess", "Fried food", "Sweet excess", "Heavy oils", "Cold food"],
        "eat_at": "Skip breakfast occasionally — Kapha can fast",
    },
}


def get_planetary_food_guidance(
    mahadasha_lord: str,
    antardasha_lord: str,
    concern: str = "general",
    language: str = "en"
) -> dict:
    """
    Returns Ayurveda + Astrology food guidance for current dasha period.
    Called from prompt_builder to inject into predictions.
    """
    md_guidance = PLANET_AYURVEDA_FOODS.get(mahadasha_lord, {})
    ad_guidance = PLANET_AYURVEDA_FOODS.get(antardasha_lord, {})
    md_dosha    = PLANET_DOSHA.get(mahadasha_lord, {})
    ad_dosha    = PLANET_DOSHA.get(antardasha_lord, {})

    if not md_guidance:
        return {}

    return {
        "mahadasha_lord":         mahadasha_lord,
        "antardasha_lord":        antardasha_lord,
        "mahadasha_quality":      md_guidance.get("planet_quality", ""),
        "primary_dosha":          md_dosha.get("dosha", ""),
        "strengthen_foods":       md_guidance.get("strengthen_with", [])[:4],
        "balance_foods":          md_guidance.get("balance_with", [])[:2],
        "avoid_foods":            md_guidance.get("avoid_if_afflicted", [])[:3],
        "best_day_practice":      md_guidance.get("remedy_food", ""),
        "primary_herb":           md_guidance.get("herb", ""),
        "antardasha_modifier":    ad_guidance.get("planet_quality", ""),
        "antardasha_foods":       ad_guidance.get("strengthen_with", [])[:2],
        "best_day":               md_guidance.get("best_day", ""),
        "framing": (
            f"During your {mahadasha_lord} period, "
            f"your body responds best to {md_dosha.get('element','')} foods. "
            f"The {mahadasha_lord} energy in your life right now "
            f"can be supported — and balanced — through what you eat."
        ),
    }


def ayurveda_context_block(food_guidance: dict) -> str:
    """Formats food guidance into a prompt block for LLM."""
    if not food_guidance:
        return ""

    foods_eat   = "\n".join(f"  - {f}" for f in food_guidance.get("strengthen_foods", []))
    foods_avoid = "\n".join(f"  - {f}" for f in food_guidance.get("avoid_foods", []))
    herb        = food_guidance.get("primary_herb", "")

    return f"""
=== AYURVEDA + ASTROLOGY GUIDANCE (include in response) ===

Current planetary period: {food_guidance.get('mahadasha_lord')}-{food_guidance.get('antardasha_lord')}
Dominant energy: {food_guidance.get('mahadasha_quality','')}
Body constitution activated: {food_guidance.get('primary_dosha','')}

FOODS THAT SUPPORT THIS PERIOD:
{foods_eat}

FOODS TO REDUCE:
{foods_avoid}

WEEKLY PRACTICE:
{food_guidance.get('best_day_practice','')}

HERB FOR THIS PERIOD:
{herb}

FRAMING FOR USER:
{food_guidance.get('framing','')}

INSTRUCTIONS:
- Include ONE short Ayurveda food suggestion in section 6 (Recalibration Practices)
- Frame as: "Ayurveda for your {food_guidance.get('mahadasha_lord','')} period:"
- Give 2-3 specific foods to eat MORE of right now
- Give 1 food/drink to reduce
- Mention the weekly practice briefly
- Frame as: "try this for 7 days and notice what shifts"
- NEVER be prescriptive about medical conditions
- Keep it to 3-4 lines maximum

=== END AYURVEDA BLOCK ===
"""
