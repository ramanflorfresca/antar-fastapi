# antar_engine/lal_kitab.py
"""
Lal Kitab Varshphal and Remedies Module
========================================
Implements the unique Lal Kitab system of Varshphal (annual charts)
and its distinctive, practical remedies.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from antar_engine.varshaphal_table import VARSHAPHAL_TABLE, get_annual_house

SPECIAL_CYCLES = {
    35: "The 35-year karmic reset — major life restructuring indicated",
    47: "Wisdom and teaching phase — share your knowledge",
    60: "Second Saturn return — legacy crystallization",
    70: "Double 35 — profound spiritual transition",
}


# ─────────────────────────────────────────────────────────────────────────────
# REMEDY DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LalKitabRemedy:
    name: str
    instructions: str
    duration: str
    timing: str
    significance: str
    materials: List[str]
    contraindications: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# REMEDIES DATABASE  (syntax errors from original corrected)
# ─────────────────────────────────────────────────────────────────────────────

REMEDIES: Dict[str, Dict] = {

    "Sun": {
        1: LalKitabRemedy(
            name="Sun in 1st House Remedy",
            instructions="Throw a copper coin in flowing water daily. Begin all important work after eating something sweet.",
            duration="40 days", timing="Sunday mornings at sunrise",
            significance="Clears ego blocks and strengthens vitality",
            materials=["Copper coin", "Sweet food", "Water"],
        ),
        5: LalKitabRemedy(
            name="Sun in 5th House Remedy",
            instructions="Feed whole wheat bread to cows on Sundays for 11 weeks.",
            duration="11 weeks", timing="Every Sunday",
            significance="Enhances creativity and children's welfare",
            materials=["Whole wheat bread"],
        ),
        6: LalKitabRemedy(
            name="Sun in 6th House Remedy",
            instructions="Bury 6 copper squares in government land on a Sunday.",
            duration="One-time ritual", timing="Sunday, during waxing moon",
            significance="Resolves career instability and workplace conflicts",
            materials=["6 copper squares"],
            contraindications="Do not bury on your own property",
        ),
        7: LalKitabRemedy(
            name="Sun in 7th House Remedy",
            instructions="Bury 7 copper squares in grassland on a Sunday. Offer sweet yogurt to spouse.",
            duration="One-time + 7 days", timing="Sunday",
            significance="Heals marital discord and business partnerships",
            materials=["7 copper squares", "Sweet yogurt"],
        ),
        8: LalKitabRemedy(
            name="Sun in 8th House Remedy",
            instructions="Donate copper vessels to a temple on Sundays for 8 weeks.",
            duration="8 weeks", timing="Sunday mornings",
            significance="Removes obstacles in inheritance and longevity",
            materials=["Copper vessels"],
        ),
        12: LalKitabRemedy(
            name="Sun in 12th House Remedy",
            instructions="Feed birds with wheat daily at sunrise.",
            duration="48 days", timing="Sunrise",
            significance="Reduces expenditure and improves spiritual progress",
            materials=["Wheat grains"],
        ),
        "general": LalKitabRemedy(
            name="General Sun Strengthening",
            instructions="Offer water to the Sun at sunrise. Wear copper ring on ring finger.",
            duration="Daily", timing="Sunrise",
            significance="Overall vitality and confidence",
            materials=["Water", "Copper ring"],
        ),
    },

    "Moon": {
        1: LalKitabRemedy(
            name="Moon in 1st House Remedy",
            instructions="Keep a silver-coated glass of water near head while sleeping. Pour it at root of acacia tree in morning.",
            duration="43 days", timing="Night (place), morning (pour)",
            significance="Calms emotional turbulence and anxiety",
            materials=["Silver glass", "Water"],
        ),
        4: LalKitabRemedy(
            name="Moon in 4th House Remedy",
            instructions="Feed milk and rice to mother or any elderly woman on Mondays.",
            duration="11 weeks", timing="Monday mornings",
            significance="Strengthens mother's health and domestic peace",
            materials=["Milk", "Rice"],
        ),
        7: LalKitabRemedy(
            name="Moon in 7th House Remedy",
            instructions="Offer white flowers and camphor at a Shiva temple on Mondays.",
            duration="7 weeks", timing="Monday evenings",
            significance="Harmonizes marital relationships",
            materials=["White flowers", "Camphor"],
        ),
        8: LalKitabRemedy(
            name="Moon in 8th House Remedy",
            instructions="Feed a white cow with rice and jaggery for 8 Mondays.",
            duration="8 weeks", timing="Monday mornings",
            significance="Removes hidden obstacles and fears",
            materials=["Rice", "Jaggery"],
        ),
        "general": LalKitabRemedy(
            name="General Moon Strengthening",
            instructions="Drink water from a silver glass. Practice mindfulness during full moon.",
            duration="Ongoing", timing="Evenings, especially Mondays",
            significance="Emotional balance and intuition",
            materials=["Silver glass"],
        ),
    },

    "Mars": {
        1: LalKitabRemedy(
            name="Mars in 1st House Remedy",
            instructions="Throw red lentils into flowing water on Tuesdays. Help brothers financially.",
            duration="7 weeks", timing="Tuesday mornings",
            significance="Channels aggression into constructive energy",
            materials=["Red lentils"],
        ),
        4: LalKitabRemedy(
            name="Mars in 4th House Remedy",
            instructions="Offer red cloth and vermilion to Hanuman temple on Tuesdays.",
            duration="7 weeks", timing="Tuesday",
            significance="Resolves property disputes and domestic conflicts",
            materials=["Red cloth", "Vermilion"],
        ),
        7: LalKitabRemedy(
            name="Mars in 7th House Remedy",
            instructions="Pour honey into flowing water. Keep a small red chilli packet at home entrance.",
            duration="11 weeks", timing="Tuesday evenings",
            significance="Reduces marital conflicts",
            materials=["Honey", "Red chillies"],
        ),
        8: LalKitabRemedy(
            name="Mars in 8th House Remedy",
            instructions="Offer coconut at a Bhairav temple on Tuesdays.",
            duration="8 weeks", timing="Tuesday",
            significance="Removes sudden accidents and hidden enemies",
            materials=["Coconut"],
            contraindications="Do not look back after leaving",
        ),
        "general": LalKitabRemedy(
            name="General Mars Strengthening",
            instructions="Donate red items on Tuesdays.",
            duration="Ongoing", timing="Tuesdays",
            significance="Courage and energy",
            materials=["Red lentils", "Red cloth"],
        ),
    },

    "Mercury": {
        1: LalKitabRemedy(
            name="Mercury in 1st House Remedy",
            instructions="Clean teeth with alum powder. Donate green lentils on Wednesdays.",
            duration="43 days", timing="Wednesday mornings",
            significance="Improves speech and communication",
            materials=["Alum", "Green lentils"],
        ),
        2: LalKitabRemedy(
            name="Mercury in 2nd House Remedy",
            instructions="Donate a goat to a needy person. Feed green fodder to cows.",
            duration="One-time", timing="Wednesday",
            significance="Enhances wealth and family harmony",
            materials=["Green fodder"],
        ),
        5: LalKitabRemedy(
            name="Mercury in 5th House Remedy",
            instructions="Wear a copper coin in a green thread around neck.",
            duration="Ongoing", timing="Wednesday",
            significance="Improves children's intelligence",
            materials=["Copper coin", "Green thread"],
        ),
        7: LalKitabRemedy(
            name="Mercury in 7th House Remedy",
            instructions="Offer green gram and sweets to married women on Wednesdays.",
            duration="7 weeks", timing="Wednesday",
            significance="Harmonizes business partnerships",
            materials=["Green gram", "Sweets"],
        ),
        "general": LalKitabRemedy(
            name="General Mercury Strengthening",
            instructions="Study or recite knowledge texts. Donate books to students.",
            duration="Ongoing", timing="Wednesdays",
            significance="Sharpens intellect and communication",
            materials=["Books", "Green items"],
        ),
    },

    "Jupiter": {
        1: LalKitabRemedy(
            name="Jupiter in 1st House Remedy",
            instructions="Water a peepal tree for 43 days. Apply saffron tilak on forehead.",
            duration="43 days", timing="Thursday mornings",
            significance="Enhances wisdom and fortune",
            materials=["Water", "Saffron"],
        ),
        5: LalKitabRemedy(
            name="Jupiter in 5th House Remedy",
            instructions="Teach underprivileged children. Donate yellow items on Thursdays.",
            duration="11 weeks", timing="Thursday",
            significance="Blessings for children and creativity",
            materials=["Yellow clothes", "Sweets"],
        ),
        9: LalKitabRemedy(
            name="Jupiter in 9th House Remedy",
            instructions="Feed teachers on Thursdays. Respect your own teachers.",
            duration="Ongoing", timing="Thursday",
            significance="Enhances luck and father's blessings",
            materials=["Food", "Yellow items"],   # FIXED: was missing =
        ),
        10: LalKitabRemedy(
            name="Jupiter in 10th House Remedy",
            instructions="Offer yellow flowers at Vishnu temple. Donate yellow lentils.",
            duration="7 weeks", timing="Thursday",
            significance="Career growth and recognition",
            materials=["Yellow flowers", "Yellow lentils"],
        ),
        "general": LalKitabRemedy(
            name="General Jupiter Strengthening",
            instructions="Practice gratitude daily. Offer turmeric to water.",
            duration="Ongoing", timing="Thursdays",
            significance="Wisdom, wealth, and expansion",
            materials=["Turmeric", "Yellow items"],
        ),
    },

    "Venus": {
        1: LalKitabRemedy(
            name="Venus in 1st House Remedy",
            instructions="Throw a blue flower into a drain for 43 days. Use rose water daily.",
            duration="43 days", timing="Friday mornings",
            significance="Enhances charm and attractiveness",
            materials=["Blue flowers", "Rose water"],
        ),
        4: LalKitabRemedy(
            name="Venus in 4th House Remedy",
            instructions="Decorate home with fresh flowers on Fridays. Offer milk to Shiva.",
            duration="Ongoing", timing="Friday",
            significance="Domestic happiness and luxury",
            materials=["Flowers", "Milk"],
        ),
        7: LalKitabRemedy(
            name="Venus in 7th House Remedy",
            instructions="Offer white sweets to couples on Fridays.",
            duration="7 Fridays", timing="Friday",
            significance="Strong marriage and romantic fulfillment",
            materials=["White sweets"],
        ),
        12: LalKitabRemedy(
            name="Venus in 12th House Remedy",
            instructions="Float rose petals in flowing water. Donate perfumes to elderly.",
            duration="43 days", timing="Friday evenings",
            significance="Balanced expenses and spiritual luxury",
            materials=["Rose petals", "Perfumes"],
        ),
        "general": LalKitabRemedy(
            name="General Venus Strengthening",
            instructions="Use perfumes and keep fresh flowers at home.",
            duration="Ongoing", timing="Fridays",
            significance="Love, beauty, and relationships",
            materials=["Flowers", "Perfumes"],
        ),
    },

    "Saturn": {
        1: LalKitabRemedy(
            name="Saturn in 1st House Remedy",
            instructions="Feed crows for 43 days. Pour mustard oil at base of a peepal tree.",
            duration="43 days", timing="Saturday mornings before sunrise",
            significance="Reduces delays and chronic health issues",
            materials=["Black sesame", "Mustard oil"],   # FIXED: was missing =
        ),
        6: LalKitabRemedy(
            name="Saturn in 6th House Remedy",
            instructions="Donate black blankets on Saturdays. Feed black dogs.",
            duration="7 Saturdays", timing="Saturday",
            significance="Removes debts and legal troubles",
            materials=["Black blankets"],
        ),
        8: LalKitabRemedy(
            name="Saturn in 8th House Remedy",
            instructions="Offer mustard oil at Shani temple. Light a sesame oil lamp.",
            duration="8 Saturdays", timing="Saturday evening",
            significance="Mitigates sudden losses and health crises",
            materials=["Mustard oil", "Sesame oil"],
        ),
        10: LalKitabRemedy(
            name="Saturn in 10th House Remedy",
            instructions="Serve elderly people. Donate iron items to labour workers.",
            duration="Ongoing", timing="Saturdays",
            significance="Career stability and authority",
            materials=["Iron items", "Black clothes"],
        ),
        "general": LalKitabRemedy(
            name="General Saturn Strengthening",
            instructions="Respect elders. Avoid alcohol. Donate black sesame on Saturdays.",
            duration="Ongoing", timing="Saturdays",
            significance="Discipline, karma, and longevity",
            materials=["Black sesame", "Mustard oil"],
            contraindications="Blue sapphire only after expert chart analysis",
        ),
    },

    "Rahu": {
        1: LalKitabRemedy(
            name="Rahu in 1st House Remedy",
            instructions="Throw barley into flowing water. Feed ants with sugar.",
            duration="43 days", timing="Saturday",
            significance="Reduces confusion and identity crisis",
            materials=["Barley", "Sugar"],
        ),
        4: LalKitabRemedy(
            name="Rahu in 4th House Remedy",
            instructions="Donate blue or black items. Offer coconut at Bhairav temple.",
            duration="7 Saturdays", timing="Saturday",
            significance="Domestic harmony and property matters",   # FIXED: was missing =
            materials=["Coconut", "Blue cloth"],
        ),
        7: LalKitabRemedy(
            name="Rahu in 7th House Remedy",
            instructions="Donate radish and brinjal. Feed monkeys with gram.",
            duration="7 weeks", timing="Saturday",
            significance="Unconventional marriages and foreign partnerships",
            materials=["Radish", "Brinjal", "Gram"],
        ),
        12: LalKitabRemedy(
            name="Rahu in 12th House Remedy",
            instructions="Travel purposefully. Donate in foreign lands or to foreign charities.",
            duration="Ongoing", timing="During Rahu periods",
            significance="Spiritual growth and foreign settlement",
            materials=["Travel", "Foreign currency"],
        ),
        "general": LalKitabRemedy(
            name="General Rahu Strengthening",
            instructions="Donate coconuts. Avoid excessive ambition in Rahu periods.",
            duration="Ongoing", timing="Saturdays during Rahu dasha",
            significance="Clarity and unconventional success",
            materials=["Coconut", "Barley"],
        ),
    },

    "Ketu": {
        1: LalKitabRemedy(
            name="Ketu in 1st House Remedy",
            instructions="Feed a white and black dog. Donate sesame seeds.",
            duration="43 days", timing="Tuesday or Saturday",
            significance="Spiritual awakening and detachment",
            materials=["Sesame seeds"],
        ),
        4: LalKitabRemedy(
            name="Ketu in 4th House Remedy",
            instructions="Offer white flowers at Ganesha temple. Donate multicolored blankets.",
            duration="7 weeks", timing="Tuesday",
            significance="Domestic peace and ancestral blessings",
            materials=["White flowers", "Multicolored blankets"],
        ),
        8: LalKitabRemedy(
            name="Ketu in 8th House Remedy",
            instructions="Perform ancestral rituals. Donate at cremation ground.",
            duration="One-time", timing="Tuesday or Saturday",   # FIXED: was missing =
            significance="Resolves karmic blocks and sudden events",
            materials=["Sesame", "Copper"],                       # FIXED: was missing =
            contraindications="Do not perform alone",
        ),
        "general": LalKitabRemedy(
            name="General Ketu Strengthening",
            instructions="Practice meditation. Donate to spiritual organisations.",
            duration="Ongoing", timing="Tuesdays",
            significance="Spiritual growth and wisdom",
            materials=["White items", "Sesame"],
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# VARSHPHAL DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VarshphalChart:
    age: int
    table_age: int
    placements: Dict[str, int]   # planet -> annual house (1-12)
    natal_chart: Dict
    is_special_cycle: bool = False
    cycle_significance: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def calculate_varshphal_chart(natal_chart: Dict, age: int) -> VarshphalChart:
    """
    Generate Varshphal chart for a specific age using the authentic Lal Kitab table.

    Args:
        natal_chart : D-1 chart dict from chart.calculate_chart()
        age         : Years completed at last birthday (e.g. 55 if person just turned 55)

    Returns:
        VarshphalChart with all planetary placements in the annual chart
    """
    # running_year = age + 1  (age 55 → running year 56 → row 56 of table)
    running_year = max(1, min(120, age + 1))

    placements = {}
    for planet, data in natal_chart["planets"].items():
        natal_house = data.get("house", data.get("sign_index", 0) + 1)
        if 1 <= natal_house <= 12:
            placements[planet] = get_annual_house(natal_house, age)

    is_special = age in SPECIAL_CYCLES
    return VarshphalChart(
        age=age,
        table_age=running_year,   # stored as running_year for clarity
        placements=placements,
        natal_chart=natal_chart,
        is_special_cycle=is_special,
        cycle_significance=SPECIAL_CYCLES.get(age),
    )


def get_remedies_for_planet(
    planet: str,
    house: int,
    include_general: bool = True,
) -> List[LalKitabRemedy]:
    """House-specific remedy + optional general remedy for a planet."""
    remedies = []
    if planet not in REMEDIES:
        return remedies
    pr = REMEDIES[planet]
    if house in pr:
        remedies.append(pr[house])
    if include_general and "general" in pr:
        remedies.append(pr["general"])
    return remedies


def get_all_varshphal_remedies(
    varshphal: VarshphalChart,
    include_general: bool = True,
    max_planets: int = 4,
) -> Dict[str, List[LalKitabRemedy]]:
    """
    Return remedies for all planets in the Varshphal chart.
    Limited to max_planets most significant planets to avoid overwhelm.
    Priority: Sun, Moon, Lagna lord, Atmakaraka, then others.
    """
    PRIORITY = ["Sun", "Moon", "Mars", "Saturn", "Jupiter", "Rahu",
                "Ketu", "Venus", "Mercury"]
    all_remedies = {}
    for planet in PRIORITY:
        if planet not in varshphal.placements:
            continue
        house = varshphal.placements[planet]
        remedies = get_remedies_for_planet(planet, house, include_general)
        if remedies:
            all_remedies[planet] = remedies
        if len(all_remedies) >= max_planets:
            break
    return all_remedies


def get_top_remedy(varshphal: VarshphalChart) -> Optional[LalKitabRemedy]:
    """Single most relevant remedy — used for daily practice card."""
    remedies = get_all_varshphal_remedies(varshphal, include_general=False, max_planets=1)
    if remedies:
        planet = next(iter(remedies))
        return remedies[planet][0] if remedies[planet] else None
    return None


def format_varshphal_for_prompt(varshphal: VarshphalChart) -> str:
    """Compact LLM-ready block for /predict system prompt."""
    lines = [
        f"LAL KITAB VARSHPHAL — Age {varshphal.age} (running year {varshphal.table_age}):"
    ]
    if varshphal.is_special_cycle:
        lines.append(f"  *** SPECIAL CYCLE: {varshphal.cycle_significance} ***")
    for planet, house in sorted(varshphal.placements.items()):
        lines.append(f"  {planet}: annual house {house}")
    return "\n".join(lines)


def format_remedies_for_prompt(
    remedies: Dict[str, List[LalKitabRemedy]],
    energy_language: bool = True,
) -> str:
    """
    Format remedies for LLM prompt context.
    energy_language=True: soften to 'practical practice' framing,
    not raw ritual instructions (for non-Indian audiences).
    """
    if not remedies:
        return ""
    lines = ["RECOMMENDED PRACTICES (Lal Kitab):"]
    for planet, remedy_list in remedies.items():
        for r in remedy_list[:1]:   # only first remedy per planet
            if energy_language:
                lines.append(
                    f"  [{planet} energy] {r.significance}. "
                    f"Practice: {r.instructions} ({r.duration})"
                )
            else:
                lines.append(f"  {r.name}: {r.instructions} — {r.duration}")
            if r.contraindications:
                lines.append(f"    ⚠ {r.contraindications}")
    return "\n".join(lines)


def lk_to_db_json(varshphal: VarshphalChart) -> Dict:
    """Serialise Varshphal result for storage in charts.lal_kitab_data jsonb column."""
    return {
        "age": varshphal.age,
        "table_age": varshphal.table_age,
        "placements": varshphal.placements,
        "is_special_cycle": varshphal.is_special_cycle,
        "cycle_significance": varshphal.cycle_significance,
    }


def ordinal(n: int) -> str:
    suffix = {1:"st",2:"nd",3:"rd"}.get(n % 10 if not 10<=n%100<=20 else 0, "th")
    return f"{n}{suffix}"
