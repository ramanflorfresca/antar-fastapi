"""
antar_engine/ayurveda_astrology.py
Ayurveda + Astrology food and lifestyle recommendations
based on planetary periods and natal chart.
No user input needed — pure calculation.
"""

# Planetary Ayurveda associations
import re

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


# ─────────────────────────────────────────────────────────────────────────────
# Daily food guidance
# ─────────────────────────────────────────────────────────────────────────────
# [food-daily 2026-07-20] get_planetary_food_guidance() above is DASHA-scoped —
# a multi-year constitutional signal. Useful, but it cannot answer "what should
# I eat today", because it returns the same answer for years at a time.
#
# This follows the SAME graha the day's colour follows (color_therapy.
# resolve_day_graha), so the day card reads as one instruction — "wear saffron,
# eat warm golden foods" — rather than two unrelated recommendations derived
# from different planets.
#
# The tara mode matters and has a direct culinary analogue:
#   strengthen -> strengthen_with  (feed the graha; the day supports it)
#   balance    -> balance_with     (pacify; the day's graha runs against you,
#                                   and stoking it is the wrong move)


# [graha-reason 2026-07-20] Food advice needs its mechanism too. "Eat black
# sesame" is folklore; "Saturn is dry and airy today — warm, oily, grounding
# food steadies it" is a physiological claim the user can feel the truth of.
# The mechanism is already in PLANET_DOSHA: each graha maps to a dosha, and
# each dosha has a known direction of imbalance and its culinary correction.
_DOSHA_MECHANISM = {
    "Pitta":      ("runs hot today", "so eat cooling and go light on spice"),
    "Vata":       ("runs dry and restless today", "so warm, oily, grounding food settles it"),
    "Kapha":      ("runs heavy today", "so keep it light and warm"),
    "Kapha/Vata": ("swings between heavy and restless today", "so keep meals warm, simple and regular"),
    "Vata/Pitta": ("runs restless and hot today", "so keep mealtimes steady and go easy on spice"),
    "Pitta/Vata": ("runs hot and scattered today", "so eat cooling but grounding"),
}


# What eating a graha's own foods FEEDS, when the day supports that graha
# (strengthen mode). Distinct from the dosha correction, which is for pacifying
# an agitated graha (balance mode).
_GRAHA_FEEDS = {
    "Sun":     "vitality and confidence",
    "Moon":    "calm and emotional steadiness",
    "Mars":    "drive and stamina",
    "Mercury": "mental sharpness",
    "Jupiter": "steadiness and good judgement",
    "Venus":   "ease and warmth",
    "Saturn":  "endurance and patience",
    "Rahu":    "focus for unconventional work",
    "Ketu":    "depth and concentration",
}


# A 1–2 word food CHARACTER for the garnish line ("eat {texture} food"), by
# mode. The frontend garnish used to parse this out of the why_eat prose, which
# broke the moment the strengthen wording changed to "…feed your drive and
# stamina" (no texture word to extract). So the backend now states it outright.
#   strengthen -> the character of the graha's own building foods
#   balance    -> the dosha-correction direction (matches the why_eat clause)
_GRAHA_TEXTURE = {
    "Sun":     "warm",
    "Moon":    "cooling",
    "Mars":    "warm, hearty",
    "Mercury": "fresh, light",
    "Jupiter": "warm, nourishing",
    "Venus":   "sweet, rich",
    "Saturn":  "warm, grounding",
    "Rahu":    "grounding",
    "Ketu":    "light, simple",
}

# The leading texture adjectives inside each _DOSHA_MECHANISM correction clause,
# for the balance-mode garnish. Kept explicit rather than regex-parsed so the
# garnish never drifts from the sentence.
_DOSHA_TEXTURE = {
    "Vata":       "warm, grounding",
    "Kapha":      "light, warm",
    "Kapha/Vata": "warm, simple",
    "Vata/Pitta": "steady, mild",
    "Pitta/Vata": "cooling, grounding",
}


def _food_texture(planet: str, mode: str) -> str:
    """A short adjective for the garnish 'eat {texture} food' line — mode-correct
    and always populated so the card never drops the eat clause."""
    if mode == "strengthen":
        return _GRAHA_TEXTURE.get(planet, "")
    dosha = (PLANET_DOSHA.get(planet) or {}).get("dosha", "")
    # Pitta pacifies with cooling; the rest come from the explicit table above.
    if dosha == "Pitta":
        return "cooling"
    return _DOSHA_TEXTURE.get(dosha, "")


def _food_reason(planet: str, mode: str) -> str:
    """One clause explaining WHY these foods — and it MUST match the mode.

    [food-mode-fix 2026-07-20] This used to ignore `mode` and always return the
    dosha-PACIFYING reason ("Mars runs hot, so eat cooling"). But on a
    STRENGTHEN day the food list is the graha's own building foods (red lentils,
    beetroot for Mars) — heating, not cooling — so a strengthen list got a
    "cool it down" explanation. Direct contradiction on the card.

    strengthen -> feed the graha's energy (the day supports it).
    balance    -> pacify the dosha (the graha is agitated / against you today).
    """
    if mode == "strengthen":
        feeds = _GRAHA_FEEDS.get(planet)
        return f"{planet} carries the day, so these foods feed your {feeds}" if feeds else ""
    dosha = (PLANET_DOSHA.get(planet) or {}).get("dosha", "")
    tendency, correction = _DOSHA_MECHANISM.get(dosha, ("", ""))
    if not tendency:
        return ""
    return f"{planet} {tendency}, {correction}"



# [food-plain 2026-07-20] The dataset entries carry their own trailing
# explanation and Ayurvedic vocabulary, written for a practitioner:
#
#   "Shatavari in warm milk - deeply nourishing"
#   "Lotus seeds - calms excess Vata"
#   "Cold beverages - aggravate watery Kapha"
#
# Shipped verbatim into a list, that is a wall of text with three separate
# mini-explanations, and "Vata"/"Kapha" mean nothing to the reader. The card
# already carries ONE mechanism line; the items themselves only need to name
# the food. Cut everything after the dash, drop parenthetical asides, and drop
# any item still carrying dosha vocabulary rather than showing jargon.
_DOSHA_WORDS = ("vata", "pitta", "kapha", "ojas", "ama ")


def _plain_food(items, limit=3):
    out = []
    for raw in items or []:
        s = str(raw)
        s = re.split(r"\s+[-\u2013\u2014]\s+", s)[0]      # cut the explanation tail
        s = re.sub(r"\s*\([^)]*\)", "", s)                # drop "(til)", "(traditional)"
        s = re.sub(r"\s{2,}", " ", s).strip(" ,;")
        if not s or len(s) < 3:
            continue
        if any(w in s.lower() for w in _DOSHA_WORDS):     # never show dosha jargon
            continue
        out.append(s[:1].upper() + s[1:])
        if len(out) >= limit:
            break
    return out


def food_for_day(nakshatra, weekday_index, tara_quality=None,
                 dasha_md=None, dasha_ad=None) -> dict:
    """Today's eat / avoid guidance. Returns {} when inputs are unusable —
    the surface then shows nothing rather than inventing a diet."""
    try:
        from antar_engine.color_therapy import resolve_day_graha
    except Exception:
        return {}

    g = resolve_day_graha(nakshatra, weekday_index, tara_quality)
    planet = g.get("planet")
    entry = PLANET_AYURVEDA_FOODS.get(planet) or {}
    if not entry:
        return {}

    _WD = ["Monday", "Tuesday", "Wednesday", "Thursday",
           "Friday", "Saturday", "Sunday"]
    try:
        today_name = _WD[int(weekday_index) % 7]
    except (TypeError, ValueError):
        today_name = ""

    strengthen = entry.get("strengthen_with", []) or []
    balance    = entry.get("balance_with", []) or []
    avoid      = entry.get("avoid_if_afflicted", []) or []

    # [food-daily 2026-07-20] 14 of the entries name a specific weekday
    # ("Mustard oil in cooking on Saturdays", "Alcohol on Tuesday"). Those are
    # correct as standing practice but wrong as TODAY's instruction: a Monday
    # card was rendering "Mustard oil ... on Saturdays". Strip the day clause
    # when today is not that day, and drop the item entirely if nothing
    # actionable survives — never show a user an instruction for another day.
    _DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday")

    def _today_safe(items, today_name):
        out = []
        for s in items or []:
            named = [d for d in _DAYS if d in s]
            if not named:
                out.append(s)
                continue
            if today_name and today_name in named:
                out.append(s)          # it IS that day — keep as written
                continue
            # strip a trailing/inline day clause: "X on Saturdays", "X on Tuesday"
            cleaned = re.sub(r"\s*(?:—\s*)?\b(?:especially\s+)?on\s+\w+days?\b", "", s)
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,—-")
            # if the day WAS the instruction (e.g. "Fasting on Saturdays"),
            # nothing meaningful is left — drop it rather than show a fragment
            if len(cleaned) >= 8 and not cleaned.lower().startswith("fasting"):
                out.append(cleaned)
        return out

    strengthen = _today_safe(strengthen, today_name)
    balance    = _today_safe(balance, today_name)
    avoid      = _today_safe(avoid, today_name)

    if g.get("mode") == "balance":
        eat = (balance or strengthen)[:3]
        why = (f"{planet} runs against you today — eat to settle it, not to "
               f"stoke it.")
    else:
        eat = strengthen[:3]
        why = f"{planet} carries the day — these foods feed that energy."

    # The remedy dish is day-bound ("Wheat halwa ... on Sunday morning"). Showing
    # it on a Friday tells the user to do something on a different day, which is
    # exactly the kind of small incoherence that makes a reading confusing. Only
    # surface it when TODAY is that day.
    best_day = (entry.get("best_day") or "").strip()
    remedy = entry.get("remedy_food", "") if best_day and best_day == today_name else ""

    # On a balance day the graha is already agitated, so its afflicted-foods
    # list is exactly what to stay off. On a strengthen day the same list is
    # still the sensible avoid, just less urgent.
    # [food-duration 2026-07-20] Ayurvedic correction is CUMULATIVE, not
    # same-day. Telling someone to eat black sesame today without saying how
    # long implies a one-day fix, which is not how any of this works and is the
    # kind of claim that makes the whole thing feel arbitrary.
    #
    # Duration scales with WHY this graha matters today, which is the honest
    # distinction:
    #
    #   balance mode   -> today. The tara is adverse NOW; this is acute
    #                     settling, not a programme.
    #   strengthen     -> one mandala (40 days), the classical unit for
    #                     remedial dietary practice. Long enough for a real
    #                     shift, short enough to actually attempt.
    #   dasha lord     -> the graha is running the user's CURRENT period, so
    #                     this is not a passing transit. Worth sustaining for
    #                     as long as the period lasts.
    _md = (dasha_md or "").strip().title()
    _ad = (dasha_ad or "").strip().title()
    if planet in (_md, _ad) and planet:
        _which = "mahadasha" if planet == _md else "antardasha"
        duration_days = None
        duration = (f"{planet} is running your current {_which}, so this is not a "
                    f"one-day fix &mdash; sustaining it through the period is what shifts things")
    elif g.get("mode") == "balance":
        duration_days = 1
        duration = "Just for today &mdash; this is settling, not a programme"
    else:
        duration_days = 40
        duration = ("Hold this for about 40 days &mdash; one mandala &mdash; and the "
                    "effect compounds; a single day changes little")

    return {
        "planet":      planet,
        "mode":        g.get("mode"),
        "duration":    duration.replace("&mdash;", "\u2014"),
        "duration_days": duration_days,
        "eat":         _plain_food(eat, 3),
        "avoid":       _plain_food(avoid, 2),
        "herb":        entry.get("herb", ""),
        # [food-plain] The remedy dish is a RITUAL ("offer rice pudding to the
        # Moon on full Moon night"), not dietary advice. On a card that is
        # meant to answer "what do I eat today" it read as nonsense. Kept in
        # the payload for a future practice surface; the day card must not
        # render it.
        "remedy_dish": remedy,
        "remedy_is_ritual": True,
        "best_day":    best_day,
        "is_best_day": bool(remedy),
        "why":         why,
        # the mechanism, not the mythology
        "why_eat":     _food_reason(planet, g.get("mode")),
        # explicit garnish adjective so the card's "eat {texture} food" line
        # never has to parse it back out of why_eat (which breaks on strengthen)
        "texture":     _food_texture(planet, g.get("mode")),
        "why_avoid":   (f"these push {planet} further in the direction it is "
                        f"already leaning") if avoid else "",
    }
