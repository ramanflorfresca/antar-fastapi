"""
Lal Kitab Remedy Database — v5 Actionability Layer
====================================================
Classical Lal Kitab remedies organized by planet.
All remedies are sourced from Lal Kitab tradition (Pandit Roop Chand Joshi, 1941).

Design principles:
  - Kitchen-simple materials (no gemstones, no expensive items)
  - Self-administered (no practitioner required)
  - Failure modes documented (when to stop)
  - Confidence labeled (high / moderate / experimental)

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class LalKitabRemedy:
    remedy_id: str
    target_planet: str
    target_condition: str

    action: str
    materials: List[str]
    frequency: str          # Daily / Weekly / Once / 43-day cycle
    duration: str
    day_of_week: Optional[str] = None
    time_of_day: Optional[str] = None

    source: str = "Lal Kitab tradition"
    confidence: str = "high"  # high / moderate / experimental

    expected_observation: str = ""
    failure_mode: str = ""

    # Context guards — when NOT to use this remedy
    contraindications: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# SATURN REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

SATURN_REMEDIES = [
    LalKitabRemedy(
        remedy_id="saturn_flour_water_mustard",
        target_planet="Saturn",
        target_condition="Saturn affliction (Sade Sati, Saturn dushthana, Saturn-Rahu conjunction)",
        action="Throw a mixture of kneaded flour, mustard oil, and water into a flowing river or drain on Saturday mornings. Do not look back after throwing.",
        materials=["wheat flour (small quantity, palm-sized)", "mustard oil (few drops)", "water"],
        frequency="Weekly",
        duration="43 Saturdays",
        day_of_week="Saturday",
        time_of_day="before sunrise",
        source="Lal Kitab tradition — Saturn affliction neutralization",
        confidence="high",
        expected_observation="Reduction in obstacle-domain struggles (delays, chronic issues, knee/joint problems) over 43-week cycle.",
        failure_mode="If no improvement observed after 21 Saturdays, stop — indicates this specific approach needs adjustment.",
        contraindications=["saturn_yogakaraka_active"],
    ),
    LalKitabRemedy(
        remedy_id="saturn_feed_black_dog",
        target_planet="Saturn",
        target_condition="Saturn-Ketu affliction, career stagnation",
        action="Feed a black dog mustard oil-coated bread on Saturdays.",
        materials=["one piece of bread (chapati or slice)", "mustard oil"],
        frequency="Weekly",
        duration="11 Saturdays minimum",
        day_of_week="Saturday",
        time_of_day="morning",
        source="Lal Kitab — Saturn animal-propitiation",
        confidence="high",
        expected_observation="Career obstruction easing, unexpected help from unexpected sources.",
        failure_mode="Skip if no black dog available; don't substitute — use Saturn flour-water remedy instead.",
        contraindications=["saturn_yogakaraka_active"],
    ),
    LalKitabRemedy(
        remedy_id="saturn_iron_workplace",
        target_planet="Saturn",
        target_condition="Saturn yogakaraka activation support",
        action="Keep a small piece of iron (horseshoe nail or small iron bar) in your workplace. Donate something black (black gram, mustard oil, iron) to someone in need on Saturdays.",
        materials=["small iron piece", "black gram or mustard oil for donation"],
        frequency="Weekly donation, continuous iron presence",
        duration="Through current dasha transition",
        day_of_week="Saturday",
        time_of_day="morning",
        source="Lal Kitab — Saturn activation support",
        confidence="high",
        expected_observation="Operational decisions clearer, mission-aligned partnerships forming.",
        failure_mode="If workplace feels heavier rather than clearer after 21 days, remove iron — Saturn may be over-activated.",
        contraindications=[],  # This IS the yogakaraka remedy
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# RAHU REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

RAHU_REMEDIES = [
    LalKitabRemedy(
        remedy_id="rahu_coconut_water",
        target_planet="Rahu",
        target_condition="Rahu-induced confusion, sudden losses, addictions, detachment from reality",
        action="Break a coconut and throw it in running water. Don't look back.",
        materials=["one coconut"],
        frequency="Once or repeat on difficult days",
        duration="One-time OR on each Rahu transit shift",
        day_of_week="Saturday or during Rahu's strong period",
        time_of_day="morning",
        source="Lal Kitab — Rahu affliction",
        confidence="high",
        expected_observation="Mental clarity returning, confusion reducing within days.",
        failure_mode="If Rahu is in a strong supporting position (disruptor-type pattern), don't do this — you're neutralizing your own wealth engine.",
        contraindications=["rahu_wealth_engine", "rahu_h11_gains", "rahu_h10_career"],
    ),
    LalKitabRemedy(
        remedy_id="rahu_silver_square",
        target_planet="Rahu",
        target_condition="Rahu negatively placed (H5 gambling, H7 relationship chaos, H12 foreign-loss)",
        action="Keep a small square piece of silver in your wallet.",
        materials=["small silver square (can be flat coin)"],
        frequency="Continuous",
        duration="Until Rahu sub-period changes",
        source="Lal Kitab — Rahu stabilization",
        confidence="high",
        expected_observation="Reduced impulsivity, less speculative/addictive behavior.",
        failure_mode="Remove if Rahu main-period starts — Rahu activation phase needs different approach.",
        contraindications=["rahu_md_active"],
    ),
    LalKitabRemedy(
        remedy_id="rahu_silver_wire_scatter",
        target_planet="Rahu",
        target_condition="Rahu scatter-impulse, focus-split risk, H11 opportunity-overload",
        action="Keep a small piece of silver wire in your wallet. On Saturdays, feed crows or birds.",
        materials=["silver wire (small piece)", "grain or bread for birds"],
        frequency="Daily (silver), weekly (bird feeding)",
        duration="Through Rahu main-period peak",
        day_of_week="Saturday for feeding",
        time_of_day="morning",
        source="Lal Kitab — Rahu scatter stabilization",
        confidence="high",
        expected_observation="Fewer distracting opportunities, clearer focus on chosen vehicle.",
        failure_mode="If scatter-impulse doesn't reduce after 43 days, the issue may be chart-structural rather than Rahu-specific.",
        contraindications=[],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# MARS REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

MARS_REMEDIES = [
    LalKitabRemedy(
        remedy_id="mars_sweet_to_sisters",
        target_planet="Mars",
        target_condition="Mars affliction causing anger, conflict, blood/inflammation issues, operational stress",
        action="Offer sweets to younger sisters or female children on Tuesdays.",
        materials=["any sweet (gur, halwa, mithai)"],
        frequency="Weekly",
        duration="Ongoing if Mars is permanently afflicted; 43 days for temporary issue",
        day_of_week="Tuesday",
        time_of_day="afternoon",
        source="Lal Kitab — Mars propitiation",
        confidence="high",
        expected_observation="Reduced conflict-domain tensions, smoother operational work.",
        failure_mode="Doesn't work if Mars is yogakaraka — don't suppress needed drive energy.",
        contraindications=["mars_yogakaraka_active"],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# SUN REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

SUN_REMEDIES = [
    LalKitabRemedy(
        remedy_id="sun_water_offering",
        target_planet="Sun",
        target_condition="Weak Sun (debilitated, combust), low confidence, authority issues",
        action="Offer water to the rising Sun from a copper vessel. Face east.",
        materials=["copper vessel", "water", "optionally red flower or roli"],
        frequency="Daily",
        duration="Ongoing",
        time_of_day="sunrise",
        source="Lal Kitab + Vedic common practice",
        confidence="high",
        expected_observation="Increased confidence, better relationships with authority figures.",
        failure_mode="Effect reduces if Sun is already strong; then do only on Sundays.",
        contraindications=[],
    ),
    LalKitabRemedy(
        remedy_id="sun_jaggery_copper",
        target_planet="Sun",
        target_condition="Sun in dushthana without exaltation compensation",
        action="Keep jaggery (gur) and a copper coin wrapped in a red cloth in your workplace.",
        materials=["jaggery (small piece)", "copper coin", "red cloth"],
        frequency="Continuous",
        duration="Replace every 43 days",
        day_of_week="Start on Sunday",
        time_of_day="morning",
        source="Lal Kitab — Sun workplace propitiation",
        confidence="moderate",
        expected_observation="Recognition at work, authority respecting your contribution.",
        failure_mode="If workplace circumstance doesn't improve in 86 days (2 cycles), job itself may not be chart-fit.",
        contraindications=[],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# JUPITER REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

JUPITER_REMEDIES = [
    LalKitabRemedy(
        remedy_id="jupiter_saffron_tilak",
        target_planet="Jupiter",
        target_condition="Weak Jupiter, wisdom/teaching blocked, Jupiter in dushthana",
        action="Apply saffron tilak on forehead. Consume pinch of saffron in milk.",
        materials=["saffron (small pinch)", "milk"],
        frequency="Daily",
        duration="Ongoing during Jupiter-affliction periods",
        day_of_week="Especially Thursday",
        time_of_day="morning",
        source="Lal Kitab — Jupiter activation",
        confidence="high",
        expected_observation="Clarity in decisions, wisdom to teach/advise, mentor relationships improving.",
        failure_mode="If no effect after 43 days, the source may be deeper (karmic) — requires different approach.",
        contraindications=[],
    ),
    LalKitabRemedy(
        remedy_id="jupiter_feed_teachers",
        target_planet="Jupiter",
        target_condition="Jupiter-guru karma activation, karmic clearing needed",
        action="Offer food or financial help to a teacher, priest, or spiritual person on Thursdays.",
        materials=["food or money"],
        frequency="Weekly",
        duration="21 Thursdays for karmic clearing",
        day_of_week="Thursday",
        source="Lal Kitab — Jupiter karmic clearing",
        confidence="high",
        expected_observation="Wisdom-domain opportunities opening, teachers/mentors appearing.",
        failure_mode="Must be genuine, not transactional; if doing for reward, remedy deactivates.",
        contraindications=[],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# VENUS REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

VENUS_REMEDIES = [
    LalKitabRemedy(
        remedy_id="venus_cow_ghee",
        target_planet="Venus",
        target_condition="Venus afflicted, relationship issues, material comfort blocked",
        action="Feed cows ghee-coated chapati on Fridays.",
        materials=["chapati", "ghee"],
        frequency="Weekly",
        duration="21 Fridays",
        day_of_week="Friday",
        time_of_day="morning",
        source="Lal Kitab — Venus propitiation",
        confidence="high",
        expected_observation="Relationship harmony, financial ease, material improvements.",
        failure_mode="If Venus is already strong (Malavya Mahapurusha), may reduce karmic growth — use sparingly.",
        contraindications=["venus_malavya_active"],
    ),
    LalKitabRemedy(
        remedy_id="venus_silver_daily",
        target_planet="Venus",
        target_condition="Venus activation for identity-overwhelm CHARISMA archetype",
        action="Wear something silver daily (ring, chain, or silver wire in wallet). On Fridays, offer white flowers or milk-based sweets.",
        materials=["silver item (ring, chain, or wire)", "white flowers or milk sweets on Fridays"],
        frequency="Daily + Friday",
        duration="Ongoing",
        day_of_week="Friday for offerings",
        source="Lal Kitab — Venus relationship-channel activation",
        confidence="high",
        expected_observation="Relationships converting into advisory income, reputation rebuilding.",
        failure_mode="If no relationship-income shift after 43 days, the business-model itself may need adjustment.",
        contraindications=[],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# MERCURY REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

MERCURY_REMEDIES = [
    LalKitabRemedy(
        remedy_id="mercury_green_cloth_tulsi",
        target_planet="Mercury",
        target_condition="Mercury afflicted, communication/business issues, Mercury karmic pattern",
        action="Wrap green or yellow cloth around a Tulsi plant. Water the plant daily.",
        materials=["green or yellow cloth", "Tulsi plant"],
        frequency="Daily watering",
        duration="43 days minimum",
        day_of_week="Start on Wednesday",
        time_of_day="morning",
        source="Lal Kitab — Mercury activation",
        confidence="high",
        expected_observation="Business dealings improving, communication clearer, honesty-tests passing.",
        failure_mode="Must actually care for the plant; if it dies, remedy is deactivated.",
        contraindications=[],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# KETU REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

KETU_REMEDIES = [
    LalKitabRemedy(
        remedy_id="ketu_dog_feeding",
        target_planet="Ketu",
        target_condition="Ketu causing detachment, child issues, unexpected losses",
        action="Feed stray dogs on any day, especially Saturdays.",
        materials=["bread, milk, or leftover food"],
        frequency="Weekly or as feasible",
        duration="Ongoing",
        day_of_week="Saturday preferred",
        source="Lal Kitab — Ketu propitiation",
        confidence="high",
        expected_observation="Unexpected help appearing, detachment pattern softening.",
        failure_mode="Doesn't work if motivation is purely transactional.",
        contraindications=[],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# MOON REMEDIES
# ═══════════════════════════════════════════════════════════════════════════

MOON_REMEDIES = [
    LalKitabRemedy(
        remedy_id="moon_milk_offering",
        target_planet="Moon",
        target_condition="Moon afflicted, emotional instability, mental pressure during Moon main-period",
        action="Offer milk to a temple or flowing water on Mondays. Sleep with a silver coin or silver glass of water near your head.",
        materials=["milk (small quantity)", "silver coin or glass"],
        frequency="Weekly (offering), daily (silver near bed)",
        duration="Ongoing during Moon afflictions",
        day_of_week="Monday",
        time_of_day="morning",
        source="Lal Kitab + Shiva worship tradition",
        confidence="high",
        expected_observation="Emotional stability, clearer decision-making in wealth-anxiety periods.",
        failure_mode="If emotional pressure persists beyond 43 days, may need deeper karmic approach.",
        contraindications=[],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# MASTER INDEX
# ═══════════════════════════════════════════════════════════════════════════

ALL_REMEDIES: Dict[str, List[LalKitabRemedy]] = {
    "Saturn": SATURN_REMEDIES,
    "Rahu": RAHU_REMEDIES,
    "Mars": MARS_REMEDIES,
    "Sun": SUN_REMEDIES,
    "Jupiter": JUPITER_REMEDIES,
    "Venus": VENUS_REMEDIES,
    "Mercury": MERCURY_REMEDIES,
    "Ketu": KETU_REMEDIES,
    "Moon": MOON_REMEDIES,
}

# Flat lookup by remedy_id
REMEDY_BY_ID: Dict[str, LalKitabRemedy] = {}
for _planet_remedies in ALL_REMEDIES.values():
    for _r in _planet_remedies:
        REMEDY_BY_ID[_r.remedy_id] = _r


def get_remedies_for_planet(planet: str) -> List[LalKitabRemedy]:
    """Get all remedies for a specific planet."""
    return ALL_REMEDIES.get(planet, [])


def get_remedy_by_id(remedy_id: str) -> Optional[LalKitabRemedy]:
    """Look up a specific remedy by ID."""
    return REMEDY_BY_ID.get(remedy_id)
