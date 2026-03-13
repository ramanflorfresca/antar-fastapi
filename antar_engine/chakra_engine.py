"""
antar_engine/chakra_engine.py

Chakra Balance Engine
──────────────────────────────────────────────────────────────────────
WHAT THIS DOES:
  Connects the user's current astrological state (dasha, transits,
  afflicted planets) to their chakra system and generates:

  1. Which chakras are currently STRESSED or BLOCKED
     (based on afflicted planets in current dasha/transit)

  2. Which chakras are currently ACTIVATED and FLOWING
     (based on strong planets in current dasha/transit)

  3. A PERSONALIZED daily chakra practice
     (specific to this person's chart + current timing)

  4. A CHAKRA ARC for the current life chapter
     (which chakras will be active over the next 12-18 months)

WHY THIS IS POWERFUL:
  Most wellness apps give generic chakra advice.
  Most astrology apps give generic planet advice.
  Nobody has connected the two — with real chart data.

  Antar can say:
  "Right now your Muladhara (root chakra) is stressed because
  Saturn is running in your chart and you have a Ketu placement
  affecting your security foundation. Here is a specific daily
  practice to balance it. In 8 months, as Jupiter activates,
  your Anahata (heart chakra) will begin opening — prepare now."

  That is a WOW moment. Nobody else does this.

DATA SOURCE:
  Uses /mnt/user-data/outputs/json/chakras.json which has:
  - 7 chakras with planets, practices, physical/emotional symptoms
  - Already in the codebase

USAGE:
    from antar_engine.chakra_engine import get_chakra_reading

    chakra = get_chakra_reading(
        chart_data=chart_data,
        dashas=dashas,
        current_transits=current_transits,
    )
    # Returns ChakraReading with stressed, flowing, and practice data
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional


# ── Chakra database (from chakras.json, hardcoded here for zero file deps) ───

CHAKRAS = [
    {
        "id": "muladhara",
        "name": "Muladhara",
        "english": "Root Chakra",
        "number": 1,
        "color": "#C1121F",
        "bija_mantra": "LAM",
        "hz": 256,
        "element": "Earth",
        "planets": ["Mars", "Saturn", "Ketu"],
        "signs": ["Aries", "Capricorn", "Scorpio"],
        "blocked_physical": ["lower back pain", "fatigue", "immune issues", "bone problems"],
        "blocked_emotional": ["fear", "financial anxiety", "feeling ungrounded", "survival panic"],
        "balanced_signs": ["feeling safe", "financially secure", "grounded", "present"],
        "life_domain": "security, survival, home, finances, physical foundation",
        "meditation": "Visualize a bright red spinning wheel at the base of your spine. Feel roots growing from your body into the earth.",
        "affirmation": "I am safe. I am grounded. I belong. The earth supports me.",
        "yoga_poses": ["Mountain Pose", "Warrior I", "Child's Pose"],
        "pranayama": "Sama Vritti — equal breathing, 4 counts in, 4 counts out",
        "foods": ["root vegetables", "red foods", "beetroot", "protein"],
        "color_therapy": "Wear or surround yourself with red and earthy tones",
        "crystal": ["Red Jasper", "Black Tourmaline", "Hematite"],
        "nature_practice": "Walk barefoot on earth. Hug a tree. Sit on the ground.",
    },
    {
        "id": "svadhisthana",
        "name": "Svadhisthana",
        "english": "Sacral Chakra",
        "number": 2,
        "color": "#FB8500",
        "bija_mantra": "VAM",
        "hz": 396,
        "element": "Water",
        "planets": ["Moon", "Venus", "Jupiter"],
        "signs": ["Cancer", "Taurus", "Pisces"],
        "blocked_physical": ["lower back", "reproductive issues", "hip tightness", "kidney issues"],
        "blocked_emotional": ["creative blocks", "guilt", "shame", "emotional numbness", "relationship issues"],
        "balanced_signs": ["creative flow", "emotional intelligence", "healthy pleasure", "adaptability"],
        "life_domain": "creativity, emotions, pleasure, relationships, sensuality",
        "meditation": "Visualize an orange crescent moon at your sacrum. Feel fluidity and creative energy flowing.",
        "affirmation": "I embrace pleasure. My creativity flows freely. I honor my emotions.",
        "yoga_poses": ["Hip Circles", "Pigeon Pose", "Goddess Pose", "Happy Baby"],
        "pranayama": "Bhramari — Humming Bee breath, 5 minutes",
        "foods": ["orange foods", "sweet fruits", "nuts", "coconut water"],
        "color_therapy": "Wear orange. Spend time near water.",
        "crystal": ["Carnelian", "Orange Calcite", "Tiger's Eye"],
        "nature_practice": "Swim, bathe in a river or the sea. Dance freely.",
    },
    {
        "id": "manipura",
        "name": "Manipura",
        "english": "Solar Plexus Chakra",
        "number": 3,
        "color": "#F59E0B",
        "bija_mantra": "RAM",
        "hz": 528,
        "element": "Fire",
        "planets": ["Sun", "Mars", "Jupiter"],
        "signs": ["Leo", "Aries", "Sagittarius"],
        "blocked_physical": ["digestive issues", "liver problems", "fatigue", "adrenal exhaustion"],
        "blocked_emotional": ["lack of confidence", "shame", "powerlessness", "aggression", "control issues"],
        "balanced_signs": ["confidence", "personal power", "healthy ambition", "self-discipline", "clarity"],
        "life_domain": "personal power, confidence, willpower, identity, career drive",
        "meditation": "Visualize a bright yellow sun at your solar plexus. Feel warmth, power, and confidence radiating from this center.",
        "affirmation": "I am powerful. I am confident. I act from my deepest truth.",
        "yoga_poses": ["Warrior III", "Boat Pose", "Plank", "Sun Salutations"],
        "pranayama": "Kapalabhati — rapid exhale breath, 2 minutes",
        "foods": ["yellow foods", "ginger", "turmeric", "whole grains", "legumes"],
        "color_therapy": "Wear yellow. Sunbathe mindfully.",
        "crystal": ["Citrine", "Yellow Jasper", "Pyrite"],
        "nature_practice": "Sit in sunlight. Practice in the morning when the sun is rising.",
    },
    {
        "id": "anahata",
        "name": "Anahata",
        "english": "Heart Chakra",
        "number": 4,
        "color": "#22C55E",
        "bija_mantra": "YAM",
        "hz": 639,
        "element": "Air",
        "planets": ["Venus", "Moon", "Jupiter"],
        "signs": ["Libra", "Cancer", "Pisces"],
        "blocked_physical": ["heart issues", "lung problems", "upper back tension", "immune weakness"],
        "blocked_emotional": ["loneliness", "grief", "inability to love", "codependency", "bitterness"],
        "balanced_signs": ["compassion", "love", "forgiveness", "empathy", "inner peace", "connection"],
        "life_domain": "love, relationships, compassion, forgiveness, connection, healing",
        "meditation": "Visualize a green light radiating from your heart center. With each breath, expand this light further. Feel love filling every cell.",
        "affirmation": "I give and receive love freely. My heart is open. I am worthy of deep connection.",
        "yoga_poses": ["Camel Pose", "Fish Pose", "Cobra", "Bridge Pose"],
        "pranayama": "Anulom Vilom — alternate nostril breathing, 10 minutes",
        "foods": ["green foods", "leafy greens", "broccoli", "herbs", "green tea"],
        "color_therapy": "Wear green or pink. Spend time in nature.",
        "crystal": ["Rose Quartz", "Green Aventurine", "Malachite", "Emerald"],
        "nature_practice": "Walk through forests. Tend to plants. Practice loving kindness meditation outdoors.",
    },
    {
        "id": "vishuddha",
        "name": "Vishuddha",
        "english": "Throat Chakra",
        "number": 5,
        "color": "#4ECDC4",
        "bija_mantra": "HAM",
        "hz": 741,
        "element": "Space/Ether",
        "planets": ["Mercury", "Jupiter"],
        "signs": ["Gemini", "Sagittarius", "Virgo"],
        "blocked_physical": ["thyroid issues", "sore throat", "neck tension", "hearing problems"],
        "blocked_emotional": ["fear of speaking", "lying", "inability to express", "feeling unheard"],
        "balanced_signs": ["clear communication", "authentic expression", "listening deeply", "creative voice"],
        "life_domain": "communication, truth, expression, teaching, writing, creative voice",
        "meditation": "Visualize a blue spinning wheel at your throat. With each exhale, release what you haven't said. With each inhale, receive the courage to speak your truth.",
        "affirmation": "I speak my truth. I am heard. My voice matters.",
        "yoga_poses": ["Shoulder Stand", "Fish Pose", "Lion Pose", "Neck rolls"],
        "pranayama": "Ujjayi — Ocean breath, slow and conscious, 10 minutes",
        "foods": ["blue foods", "blueberries", "blackberries", "herbal teas", "warm liquids"],
        "color_therapy": "Wear blue or turquoise. Sing, chant, or hum daily.",
        "crystal": ["Lapis Lazuli", "Blue Kyanite", "Aquamarine", "Sodalite"],
        "nature_practice": "Sing outdoors. Practice chanting mantras. Speak your intentions aloud to the sky.",
    },
    {
        "id": "ajna",
        "name": "Ajna",
        "english": "Third Eye Chakra",
        "number": 6,
        "color": "#8B5CF6",
        "bija_mantra": "OM",
        "hz": 852,
        "element": "Light",
        "planets": ["Saturn", "Rahu", "Ketu", "Jupiter"],
        "signs": ["Capricorn", "Aquarius", "Sagittarius", "Pisces"],
        "blocked_physical": ["headaches", "eye strain", "sinus issues", "insomnia", "hormone imbalance"],
        "blocked_emotional": ["confusion", "poor intuition", "inability to see patterns", "overthinking", "delusion"],
        "balanced_signs": ["clear intuition", "insight", "wisdom", "vision", "pattern recognition"],
        "life_domain": "intuition, wisdom, insight, spiritual vision, mental clarity, pattern recognition",
        "meditation": "Focus gently between the eyebrows. Visualize a deep indigo or violet light. Ask your inner wisdom one question and simply wait.",
        "affirmation": "I trust my intuition. I see clearly. My inner wisdom guides me.",
        "yoga_poses": ["Child's Pose (forehead to ground)", "Downward Dog", "Eagle Pose"],
        "pranayama": "Nadi Shodhana — alternate nostril breathing, slow, 15 minutes",
        "foods": ["purple foods", "purple grapes", "eggplant", "figs", "dark chocolate", "walnuts"],
        "color_therapy": "Wear indigo or violet. Spend time in darkness and silence.",
        "crystal": ["Amethyst", "Labradorite", "Fluorite", "Lapis Lazuli"],
        "nature_practice": "Stargaze. Meditate at dawn or dusk. Practice silence.",
    },
    {
        "id": "sahasrara",
        "name": "Sahasrara",
        "english": "Crown Chakra",
        "number": 7,
        "color": "#F0A500",
        "bija_mantra": "AUM",
        "hz": 963,
        "element": "Consciousness",
        "planets": ["Jupiter", "Ketu", "Sun"],
        "signs": ["Sagittarius", "Pisces", "Leo"],
        "blocked_physical": ["depression", "chronic exhaustion", "neurological issues", "sensitivity to light"],
        "blocked_emotional": ["spiritual disconnection", "feeling meaningless", "existential crisis", "rigid beliefs"],
        "balanced_signs": ["divine connection", "inner peace", "trust in life", "higher purpose", "transcendence"],
        "life_domain": "spiritual connection, higher purpose, divine trust, transcendence, liberation",
        "meditation": "Visualize a golden or white light entering through the crown of your head. Feel it filling your entire body. Rest in pure awareness with no agenda.",
        "affirmation": "I am connected to something greater. I trust the intelligence of life. I am guided.",
        "yoga_poses": ["Headstand (Sirsasana)", "Lotus Pose", "Savasana", "Meditation"],
        "pranayama": "Surya Bhedana — sun piercing breath, morning practice",
        "foods": ["fasting", "light foods", "white or violet foods", "pure water"],
        "color_therapy": "White, violet, or gold. Minimize screen time. Spend time in silence.",
        "crystal": ["Clear Quartz", "Diamond", "Selenite", "White Calcite"],
        "nature_practice": "Sit under the sky and practice pure presence. Stargazing, mountain meditation.",
    },
]

# Planet → chakra mapping (which chakras each planet governs)
PLANET_CHAKRAS = {
    "Sun":     ["manipura", "sahasrara"],
    "Moon":    ["svadhisthana", "anahata"],
    "Mars":    ["muladhara", "manipura"],
    "Mercury": ["vishuddha"],
    "Jupiter": ["svadhisthana", "anahata", "ajna", "sahasrara"],
    "Venus":   ["svadhisthana", "anahata"],
    "Saturn":  ["muladhara", "ajna"],
    "Rahu":    ["ajna", "muladhara"],
    "Ketu":    ["muladhara", "sahasrara", "ajna"],
}

# Planet states that stress a chakra
STRESS_STATES = {
    "debilitated",
    "combust",
    "retrograde_malefic",
    "afflicted",
    "in_enemy_sign",
}

DASHA_ENERGY_SHORT = {
    "Sun":     "Identity & Purpose",
    "Moon":    "Emotional Depth",
    "Mars":    "Action & Courage",
    "Mercury": "Intellect & Communication",
    "Jupiter": "Expansive Growth",
    "Venus":   "Heart & Beauty",
    "Saturn":  "Clarifying Pressure",
    "Rahu":    "Hungry Becoming",
    "Ketu":    "Releasing & Liberation",
}

# Signs where each planet is debilitated (weakened)
DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
    "Saturn": "Aries",
}

# Signs where each planet is exalted (strengthened)
EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra",
}


def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt[:10])
        except:
            continue
    return datetime.utcnow()

def _current_period(periods: list, now: datetime) -> Optional[dict]:
    for p in periods:
        if _parse_dt(p["start"]) <= now <= _parse_dt(p["end"]):
            return p
    return periods[0] if periods else None

def _current_antardasha(periods: list, now: datetime) -> Optional[dict]:
    current_md = _current_period(periods, now)
    if not current_md:
        return None
    md_start = _parse_dt(current_md["start"])
    md_end   = _parse_dt(current_md["end"])
    sub = [
        p for p in periods
        if _parse_dt(p["start"]) >= md_start
        and _parse_dt(p["end"]) <= md_end
        and p["lord_or_sign"] != current_md["lord_or_sign"]
    ]
    for p in sub:
        if _parse_dt(p["start"]) <= now <= _parse_dt(p["end"]):
            return p
    return None

def _get_chakra_by_id(chakra_id: str) -> Optional[dict]:
    for c in CHAKRAS:
        if c["id"] == chakra_id:
            return c
    return None

def _build_transit_map(current_transits: list) -> dict:
    transit_map = {}
    for t in current_transits:
        if isinstance(t, dict):
            p = t.get("planet", t.get("name", ""))
            s = t.get("current_sign", t.get("sign", t.get("transit_sign", "")))
            if p and s:
                transit_map[p] = s
    return transit_map

def _is_planet_stressed(planet: str, chart_data: dict, current_transits: list) -> bool:
    """Check if a planet is currently under stress based on natal + transit state."""
    planets = chart_data.get("planets", {})
    natal = planets.get(planet, {})
    natal_sign = natal.get("sign", "")

    # Check natal debilitation
    if DEBILITATION.get(planet) == natal_sign:
        return True

    # Check transit stress (planet transiting over its debilitation sign)
    transit_map = _build_transit_map(current_transits)
    transit_sign = transit_map.get(planet, "")
    if DEBILITATION.get(planet) == transit_sign:
        return True

    return False

def _is_planet_strong(planet: str, chart_data: dict, current_transits: list) -> bool:
    """Check if a planet is currently strong based on natal + transit."""
    planets = chart_data.get("planets", {})
    natal = planets.get(planet, {})
    natal_sign = natal.get("sign", "")

    # Natal exaltation
    if EXALTATION.get(planet) == natal_sign:
        return True

    # Transit exaltation
    transit_map = _build_transit_map(current_transits)
    transit_sign = transit_map.get(planet, "")
    if EXALTATION.get(planet) == transit_sign:
        return True

    return False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def get_chakra_reading(
    chart_data: dict,
    dashas: dict,
    current_transits: list,
) -> dict:
    """
    Main entry point. Returns a complete chakra reading.

    Returns:
        {
            "stressed_chakras": [...],   # List of chakra dicts with context
            "flowing_chakras":  [...],   # List of chakra dicts with context
            "primary_practice": {...},   # The single most important practice
            "daily_sequence":   [...],   # 3-step daily practice
            "chapter_arc":      str,     # How the chakra system will evolve
            "current_chapter_chakra": str, # The dominant chakra of current life chapter
        }
    """
    now = datetime.utcnow()
    vim = dashas.get("vimsottari", [])

    current_md = _current_period(vim, now)
    current_ad = _current_antardasha(vim, now)
    md_planet = current_md["lord_or_sign"] if current_md else "Sun"
    ad_planet = current_ad["lord_or_sign"] if current_ad else "Moon"

    stressed_chakra_ids = set()
    flowing_chakra_ids  = set()
    stress_reasons      = {}
    flow_reasons        = {}

    # ── Step 1: Dasha-based chakra activation ─────────────────────────────

    # Current MD activates its chakras
    for chakra_id in PLANET_CHAKRAS.get(md_planet, []):
        if _is_planet_stressed(md_planet, chart_data, current_transits):
            stressed_chakra_ids.add(chakra_id)
            stress_reasons[chakra_id] = (
                f"Your current life chapter ({DASHA_ENERGY_SHORT.get(md_planet, md_planet)}) "
                f"is running through a planet under pressure — "
                f"this stress flows directly into the {_get_chakra_by_id(chakra_id)['english'] if _get_chakra_by_id(chakra_id) else chakra_id}."
            )
        elif _is_planet_strong(md_planet, chart_data, current_transits):
            flowing_chakra_ids.add(chakra_id)
            flow_reasons[chakra_id] = (
                f"Your current life chapter ({DASHA_ENERGY_SHORT.get(md_planet, md_planet)}) "
                f"is running through a strong planet — "
                f"this strength is flowing into and activating the {_get_chakra_by_id(chakra_id)['english'] if _get_chakra_by_id(chakra_id) else chakra_id}."
            )
        else:
            # Active but neutral — add to flowing with lighter reason
            flowing_chakra_ids.add(chakra_id)
            flow_reasons[chakra_id] = (
                f"Your {DASHA_ENERGY_SHORT.get(md_planet, md_planet)} chapter is activating this energy center."
            )

    # Current AD adds its influence
    for chakra_id in PLANET_CHAKRAS.get(ad_planet, []):
        if chakra_id not in stressed_chakra_ids and chakra_id not in flowing_chakra_ids:
            flowing_chakra_ids.add(chakra_id)
            flow_reasons[chakra_id] = (
                f"The {DASHA_ENERGY_SHORT.get(ad_planet, ad_planet)} sub-theme is gently activating this energy center."
            )

    # ── Step 2: Transit-based stress ──────────────────────────────────────

    transit_map = _build_transit_map(current_transits)

    # Saturn transiting over debilitation → muladhara + ajna stress
    sat_sign = transit_map.get("Saturn", "")
    if sat_sign and DEBILITATION.get("Saturn") == sat_sign:
        stressed_chakra_ids.add("muladhara")
        stressed_chakra_ids.add("ajna")
        stress_reasons["muladhara"] = (
            "Saturn is in a weakened position in transit — "
            "this creates pressure on your Root Chakra (security, stability, foundations)."
        )

    # Jupiter strong in transit → anahata + sahasrara flowing
    jup_sign = transit_map.get("Jupiter", "")
    if jup_sign and EXALTATION.get("Jupiter") == jup_sign:
        flowing_chakra_ids.add("anahata")
        flowing_chakra_ids.add("sahasrara")
        flow_reasons["anahata"]   = "Jupiter's expansive energy in transit is opening your Heart Chakra."
        flow_reasons["sahasrara"] = "Jupiter exalted in transit is activating your Crown Chakra — spiritual wisdom is available."

    # ── Step 3: Natal afflictions ─────────────────────────────────────────

    planets_data = chart_data.get("planets", {})
    for planet, data in planets_data.items():
        natal_sign = data.get("sign", "")
        if DEBILITATION.get(planet) == natal_sign:
            for chakra_id in PLANET_CHAKRAS.get(planet, []):
                stressed_chakra_ids.add(chakra_id)
                if chakra_id not in stress_reasons:
                    stress_reasons[chakra_id] = (
                        f"{planet}'s energy is under lifelong stress in your blueprint — "
                        f"this means the {_get_chakra_by_id(chakra_id)['english'] if _get_chakra_by_id(chakra_id) else chakra_id} "
                        f"requires extra conscious attention and practice."
                    )

    # ── Step 4: Remove duplicates (stressed takes priority) ───────────────

    flowing_chakra_ids -= stressed_chakra_ids

    # ── Step 5: Build enriched chakra objects ─────────────────────────────

    def enrich_chakra(chakra_id: str, is_stressed: bool) -> dict:
        chakra = _get_chakra_by_id(chakra_id)
        if not chakra:
            return None
        reason = stress_reasons.get(chakra_id) if is_stressed else flow_reasons.get(chakra_id, "")
        return {
            **chakra,
            "is_stressed":     is_stressed,
            "context_reason":  reason,
            "urgency":         "high" if is_stressed else "moderate",
        }

    stressed = [c for c in [enrich_chakra(cid, True)  for cid in stressed_chakra_ids] if c]
    flowing  = [c for c in [enrich_chakra(cid, False) for cid in flowing_chakra_ids]  if c]

    # Sort by chakra number
    stressed.sort(key=lambda x: x["number"])
    flowing.sort(key=lambda x: x["number"])

    # ── Step 6: Primary practice (most stressed chakra) ───────────────────

    primary_chakra = stressed[0] if stressed else (flowing[0] if flowing else CHAKRAS[3])  # default to heart

    primary_practice = {
        "chakra_name":    primary_chakra["name"],
        "english_name":   primary_chakra["english"],
        "chakra_color":   primary_chakra["color"],
        "bija_mantra":    primary_chakra["bija_mantra"],
        "context":        primary_chakra.get("context_reason", ""),
        "meditation":     primary_chakra["meditation"],
        "affirmation":    primary_chakra["affirmation"],
        "pranayama":      primary_chakra["pranayama"],
        "yoga_poses":     primary_chakra["yoga_poses"][:3],
        "foods":          primary_chakra["foods"][:4],
        "crystal":        primary_chakra["crystal"][:2],
        "nature_practice":primary_chakra["nature_practice"],
        "color_therapy":  primary_chakra["color_therapy"],
    }

    # ── Step 7: Daily sequence (3-step practice) ──────────────────────────

    daily_sequence = _build_daily_sequence(
        primary_chakra=primary_chakra,
        md_planet=md_planet,
        stressed_chakras=stressed[:2],
    )

    # ── Step 8: Chapter arc ───────────────────────────────────────────────

    chapter_arc = _build_chapter_arc(
        md_planet=md_planet,
        ad_planet=ad_planet,
        stressed=stressed,
        flowing=flowing,
    )

    return {
        "stressed_chakras":        stressed[:3],
        "flowing_chakras":         flowing[:3],
        "primary_practice":        primary_practice,
        "daily_sequence":          daily_sequence,
        "chapter_arc":             chapter_arc,
        "current_chapter_chakra":  primary_chakra["name"],
        "current_chapter_color":   primary_chakra["color"],
        "total_stressed":          len(stressed),
        "total_flowing":           len(flowing),
        "summary": _build_summary(md_planet, stressed, flowing),
    }


def _build_daily_sequence(
    primary_chakra: dict,
    md_planet: str,
    stressed_chakras: list,
) -> list[dict]:
    """Build a 3-step daily practice sequence."""

    # Step 1: Morning grounding (always starts with root or primary chakra)
    root_chakra = _get_chakra_by_id("muladhara")

    step1_chakra = root_chakra if primary_chakra["id"] != "muladhara" else primary_chakra
    step1 = {
        "step": 1,
        "timing": "Morning — 5 minutes",
        "practice": "Grounding breath",
        "chakra": step1_chakra["name"],
        "color": step1_chakra["color"],
        "instruction": (
            f"Sit with feet flat on the floor. "
            f"Take 10 slow breaths. With each exhale, feel yourself becoming heavier, "
            f"more rooted. Chant '{step1_chakra['bija_mantra']}' silently with each breath. "
            f"Affirmation: {step1_chakra['affirmation']}"
        ),
        "duration_minutes": 5,
    }

    # Step 2: Primary chakra practice (the main work)
    step2 = {
        "step": 2,
        "timing": "Morning or midday — 10-15 minutes",
        "practice": f"{primary_chakra['english']} activation",
        "chakra": primary_chakra["name"],
        "color": primary_chakra["color"],
        "instruction": (
            f"{primary_chakra['meditation']} "
            f"Pranayama: {primary_chakra['pranayama']}. "
            f"Affirmation: {primary_chakra['affirmation']}"
        ),
        "duration_minutes": 12,
    }

    # Step 3: Integration (crown or ajna — always closes upward)
    closing_chakra = _get_chakra_by_id("ajna")
    step3 = {
        "step": 3,
        "timing": "Evening — 5 minutes",
        "practice": "Integration and release",
        "chakra": closing_chakra["name"],
        "color": closing_chakra["color"],
        "instruction": (
            "Sit quietly. Close your eyes. Take 5 deep breaths. "
            "Ask your inner wisdom: what does today want me to know? "
            "Simply listen without forcing an answer. "
            f"Chant '{closing_chakra['bija_mantra']}' 9 times. "
            "Release the day completely."
        ),
        "duration_minutes": 5,
    }

    return [step1, step2, step3]


def _build_chapter_arc(
    md_planet: str,
    ad_planet: str,
    stressed: list,
    flowing: list,
) -> str:
    """Build a narrative of the chakra arc for the current life chapter."""

    md_energy = DASHA_ENERGY_SHORT.get(md_planet, md_planet)
    ad_energy = DASHA_ENERGY_SHORT.get(ad_planet, ad_planet)

    stressed_names = [c["english"] for c in stressed[:2]]
    flowing_names  = [c["english"] for c in flowing[:2]]

    stressed_text = (
        f"Your {', '.join(stressed_names)} {'is' if len(stressed_names) == 1 else 'are'} "
        f"under pressure and calling for attention."
    ) if stressed_names else "No major chakra blockages are detected right now."

    flowing_text = (
        f"Your {', '.join(flowing_names)} {'is' if len(flowing_names) == 1 else 'are'} "
        f"activated and supporting your growth."
    ) if flowing_names else "Your chakra system is in a quiet, neutral state."

    return (
        f"In your current {md_energy} chapter, your energy system is being shaped by "
        f"{md_planet}'s influence on your chakras. {stressed_text} "
        f"{flowing_text} "
        f"The sub-theme of {ad_energy} is adding its influence through the "
        f"chakras it governs. "
        f"Working consciously with the practices below will help you move "
        f"with this chapter rather than against it."
    )


def _build_summary(md_planet: str, stressed: list, flowing: list) -> str:
    """One-paragraph summary of the chakra state."""
    md_energy = DASHA_ENERGY_SHORT.get(md_planet, md_planet)
    n_stressed = len(stressed)
    n_flowing  = len(flowing)

    if n_stressed == 0:
        return (
            f"Your chakra system is relatively balanced right now. "
            f"Your {md_energy} chapter is activating {n_flowing} energy {'center' if n_flowing == 1 else 'centers'}. "
            f"The daily practice below will help you work with this energy intentionally."
        )
    elif n_stressed <= 2:
        stressed_names = [c["english"] for c in stressed]
        return (
            f"Your {md_energy} chapter is creating pressure in "
            f"{'your ' + stressed_names[0] if n_stressed == 1 else 'two energy centers: ' + ' and '.join(stressed_names)}. "
            f"This is not a problem — it is a signal. "
            f"The daily practice below is specifically designed to work with this."
        )
    else:
        return (
            f"Your {md_energy} chapter is a period of significant chakra activation. "
            f"Multiple energy centers are under pressure simultaneously — "
            f"this often accompanies major life transitions. "
            f"Consistent daily practice during this period will make an enormous difference."
        )


def chakra_reading_to_context_block(chakra_reading: dict) -> str:
    """
    Convert chakra reading to LLM context block for prompt_builder.py.
    """
    if not chakra_reading:
        return ""

    stressed = chakra_reading.get("stressed_chakras", [])
    flowing  = chakra_reading.get("flowing_chakras", [])
    primary  = chakra_reading.get("primary_practice", {})

    lines = ["═══ CHAKRA SYSTEM STATE (current timing) ═══"]

    if stressed:
        lines.append(f"STRESSED/BLOCKED: {', '.join(c['english'] for c in stressed)}")
        for c in stressed[:2]:
            lines.append(f"  → {c['english']}: {c.get('context_reason', '')}")

    if flowing:
        lines.append(f"ACTIVATED/FLOWING: {', '.join(c['english'] for c in flowing[:3])}")

    if primary:
        lines.append(f"PRIMARY PRACTICE: {primary.get('chakra_name', '')} — {primary.get('context', '')}")

    lines.append(f"CHAPTER ARC: {chakra_reading.get('chapter_arc', '')}")
    lines.append("═══ END CHAKRA STATE ═══")

    return "\n".join(lines)
