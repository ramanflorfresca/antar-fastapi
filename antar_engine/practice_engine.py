"""
practice_engine.py — Antar Practice & Remedies Engine
=====================================================
Reads stored lal_kitab_data + jaimini_data from charts table (JSONB).
Produces a personalized, priority-ranked practice schedule.

ZERO extra DB queries — everything from stored chart data.
ZERO jargon in output — all labels are plain English.

Input:  chart row (dict) with chart_data, lal_kitab_data, jaimini_data, current_country
Output: PracticeSchedule (primary practice, mantra, sleeping alerts, rin clearing, 7-day plan)

❆ ANTAR · antar.world · Sprint P · March 31, 2026
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from typing import Optional
import json
import hashlib

def _safe_json(data):
    """Parse JSONB that Supabase returns as string."""
    if data is None: return {}
    if isinstance(data, str):
        try: return json.loads(data)
        except: return {}
    if isinstance(data, (dict, list)): return data
    return {}




# ════════════════════════════════════════════
# 1. PLANET → PLAIN ENGLISH MAPPING
# ════════════════════════════════════════════

PLANET_ENERGY = {
    "Sun":     {"label": "Identity & Authority",   "domain": "career",       "color": "#F59E0B", "day": "Sunday",    "chakra": "Solar Plexus",  "element": "Fire"},
    "Moon":    {"label": "Emotional Clarity",       "domain": "wellbeing",    "color": "#94A3B8", "day": "Monday",    "chakra": "Sacral",        "element": "Water"},
    "Mars":    {"label": "Action & Courage",        "domain": "career",       "color": "#EF4444", "day": "Tuesday",   "chakra": "Root",          "element": "Fire"},
    "Mercury": {"label": "Communication & Clarity", "domain": "career",       "color": "#22C55E", "day": "Wednesday", "chakra": "Throat",        "element": "Earth"},
    "Jupiter": {"label": "Wisdom & Expansion",      "domain": "growth",       "color": "#F59E0B", "day": "Thursday",  "chakra": "Crown",         "element": "Ether"},
    "Venus":   {"label": "Love & Creativity",       "domain": "relationship", "color": "#EC4899", "day": "Friday",    "chakra": "Heart",         "element": "Water"},
    "Saturn":  {"label": "Discipline & Structure",   "domain": "career",       "color": "#8B5CF6", "day": "Saturday",  "chakra": "Root",          "element": "Air"},
    "Rahu":    {"label": "Ambition & Breakthrough",  "domain": "growth",       "color": "#6366F1", "day": "Saturday",  "chakra": "Third Eye",     "element": "Air"},
    "Ketu":    {"label": "Intuition & Release",      "domain": "spiritual",    "color": "#A78BFA", "day": "Tuesday",   "chakra": "Crown",         "element": "Fire"},
}

# Jaimini Karaka → Chakra mapping (from user's spec)
KARAKA_CHAKRA = {
    "AK":  {"chakra": "Sahasrara (Crown)",   "label": "Soul Purpose",       "focus": "Meditation on life direction and identity",          "color": "#A78BFA"},
    "AmK": {"chakra": "Manipura (Solar Plexus)", "label": "Career DNA",     "focus": "Confidence, willpower, professional instinct",      "color": "#F59E0B"},
    "DK":  {"chakra": "Svadhisthana (Sacral)",   "label": "Partner Blueprint", "focus": "Emotional fluidity, creativity, relationships",  "color": "#EC4899"},
    "MK":  {"chakra": "Anahata (Heart)",     "label": "Foundation",          "focus": "Emotional security, home life, inner peace",        "color": "#22C55E"},
    "GK":  {"chakra": "Muladhara (Root)",    "label": "Obstacle Catalyst",   "focus": "Physical health, survival instincts, grounding",    "color": "#EF4444"},
    "BK":  {"chakra": "Vishuddha (Throat)",  "label": "Wisdom & Guidance",   "focus": "Communication, teaching, mentorship",              "color": "#3B82F6"},
    "PK":  {"chakra": "Ajna (Third Eye)",    "label": "Legacy & Children",   "focus": "Vision, creativity, future planning",              "color": "#6366F1"},
}


# ════════════════════════════════════════════
# 2. MANTRA DATABASE
# ════════════════════════════════════════════

MANTRAS = {
    "Sun": {
        "sanskrit": "Om Hraam Hreem Hroum Sah Suryaya Namaha",
        "phonetic": "Ohm Hraam Hreem Hrowm Sah Soor-yaa-ya Na-ma-ha",
        "affirmation": "I am confident, visible, and worthy of recognition.",
        "count": 7, "time": "morning, facing east",
    },
    "Moon": {
        "sanskrit": "Om Shraam Shreem Shroum Sah Chandraya Namaha",
        "phonetic": "Ohm Shraam Shreem Shrowm Sah Chan-dra-ya Na-ma-ha",
        "affirmation": "I am emotionally clear, calm, and deeply present.",
        "count": 11, "time": "evening, before sleep",
    },
    "Mars": {
        "sanskrit": "Om Kraam Kreem Kroum Sah Bhaumaya Namaha",
        "phonetic": "Ohm Kraam Kreem Krowm Sah Bhow-ma-ya Na-ma-ha",
        "affirmation": "I act with courage and channel my energy with purpose.",
        "count": 7, "time": "morning, before work",
    },
    "Mercury": {
        "sanskrit": "Om Braam Breem Broum Sah Budhaya Namaha",
        "phonetic": "Ohm Braam Breem Browm Sah Bud-haa-ya Na-ma-ha",
        "affirmation": "I communicate with precision and think with clarity.",
        "count": 9, "time": "morning, before meetings or writing",
    },
    "Jupiter": {
        "sanskrit": "Om Graam Greem Groum Sah Gurave Namaha",
        "phonetic": "Ohm Graam Greem Growm Sah Gu-ra-vay Na-ma-ha",
        "affirmation": "I am wise, expansive, and open to growth.",
        "count": 11, "time": "morning, facing north-east",
    },
    "Venus": {
        "sanskrit": "Om Draam Dreem Droum Sah Shukraya Namaha",
        "phonetic": "Ohm Draam Dreem Drowm Sah Shook-raa-ya Na-ma-ha",
        "affirmation": "I attract love, beauty, and creative abundance.",
        "count": 11, "time": "morning or evening",
    },
    "Saturn": {
        "sanskrit": "Om Praam Preem Proum Sah Shanaye Namaha",
        "phonetic": "Ohm Praam Preem Prowm Sah Sha-nay-yay Na-ma-ha",
        "affirmation": "I am disciplined, patient, and build things that last.",
        "count": 11, "time": "morning, especially Saturday",
    },
    "Rahu": {
        "sanskrit": "Om Bhraam Bhreem Bhroum Sah Rahave Namaha",
        "phonetic": "Ohm Bhraam Bhreem Bhrowm Sah Ra-ha-vay Na-ma-ha",
        "affirmation": "I channel my ambition wisely and break through limits.",
        "count": 18, "time": "evening, during quiet reflection",
    },
    "Ketu": {
        "sanskrit": "Om Sraam Sreem Sroum Sah Ketave Namaha",
        "phonetic": "Ohm Sraam Sreem Srowm Sah Kay-ta-vay Na-ma-ha",
        "affirmation": "I release what no longer serves me and trust my intuition.",
        "count": 7, "time": "morning, during meditation",
    },
}


# ════════════════════════════════════════════
# 3. REMEDY DATABASE (LOCALE-GATED)
# ════════════════════════════════════════════

REMEDIES = {
    "Sun": {
        "IN": {"action": "Offer water to the Sun every morning. Donate wheat on Sundays.", "item": "copper coin in flowing water"},
        "GLOBAL": {"action": "Spend 5 minutes in morning sunlight. Volunteer for a leadership role this week.", "item": "wear warm gold or orange on Sunday"},
    },
    "Moon": {
        "IN": {"action": "Offer milk to a Shiva temple on Monday. Keep silver with you.", "item": "white flowers at home"},
        "GLOBAL": {"action": "Take a 10-minute walk by water this week. Write down three feelings you've been avoiding.", "item": "keep a small silver item in your pocket on Monday"},
    },
    "Mars": {
        "IN": {"action": "Donate red lentils on Tuesday. Carry a copper coin.", "item": "sweet bread to a dog on Tuesday"},
        "GLOBAL": {"action": "Do 15 minutes of intense exercise on Tuesday. Channel frustration into a physical goal.", "item": "wear red or maroon on Tuesday"},
    },
    "Mercury": {
        "IN": {"action": "Feed green vegetables to a cow on Wednesday. Donate to an education cause.", "item": "green moong dal to birds"},
        "GLOBAL": {"action": "Write one difficult email you've been avoiding. Read 15 pages of a new book.", "item": "wear green on Wednesday"},
    },
    "Jupiter": {
        "IN": {"action": "Donate yellow sweets on Thursday. Touch the feet of an elder or teacher.", "item": "turmeric tilak on forehead Thursday morning"},
        "GLOBAL": {"action": "Express gratitude to a mentor or teacher this week. Teach someone one thing you know.", "item": "wear yellow on Thursday"},
    },
    "Venus": {
        "IN": {"action": "Donate white clothes to a woman on Friday. Offer white flowers.", "item": "rice and sugar to ants on Friday"},
        "GLOBAL": {"action": "Create something beautiful this week — cook, paint, arrange flowers. Compliment someone sincerely.", "item": "wear white or pastel on Friday"},
    },
    "Saturn": {
        "IN": {"action": "Donate mustard oil on Saturday. Serve food to workers.", "item": "iron nails buried under a tree on Saturday"},
        "GLOBAL": {"action": "Volunteer at a shelter or food bank this Saturday. Help someone who serves others.", "item": "wear black or navy on Saturday"},
    },
    "Rahu": {
        "IN": {"action": "Donate blue clothes to a sweeper. Keep silver square piece.", "item": "coal in flowing water on Saturday"},
        "GLOBAL": {"action": "Pause before your next impulsive decision. Meditate on the difference between desire and need.", "item": "keep a small sandalwood item near your desk"},
    },
    "Ketu": {
        "IN": {"action": "Feed a stray dog. Donate a brown blanket.", "item": "bananas to a temple on Tuesday"},
        "GLOBAL": {"action": "Spend 10 minutes in silence today. Let go of one attachment — delete, donate, or forgive.", "item": "wear earth tones on Tuesday"},
    },
}


# Rin (karmic debt) plain English + clearing practices
RIN_CLEARING = {
    "self_debt": {
        "label": "Self Pattern",
        "why": "A repeated cycle of self-sabotage has been identified in your chart. You tend to undermine your own success right before breakthrough moments.",
        "IN": "Donate wheat and jaggery on Sunday. Feed a brown cow.",
        "GLOBAL": "Write a letter of forgiveness to yourself. Commit to one act of self-care daily for 21 days.",
        "duration": "21 days",
    },
    "father_debt": {
        "label": "Authority Pattern",
        "why": "There's friction with authority figures or father-type relationships that keeps recurring. This pattern limits your professional growth.",
        "IN": "Offer water to the Sun for 43 days. Respect father figures.",
        "GLOBAL": "Reach out to an older male mentor this week. Offer genuine respect to someone in authority, even if difficult.",
        "duration": "43 days",
    },
    "mother_debt": {
        "label": "Nurture Pattern",
        "why": "Emotional security feels unstable. The relationship with your mother or home foundation carries unresolved weight.",
        "IN": "Offer milk on Monday. Serve your mother or a mother figure.",
        "GLOBAL": "Call your mother (or mother figure) this week. Create one ritual of home comfort — cook a family recipe, rearrange a space.",
        "duration": "21 days",
    },
    "guru_debt": {
        "label": "Wisdom Pattern",
        "why": "Your growth is blocked by a disconnection from learning or mentorship. Knowledge that should flow to you is being diverted.",
        "IN": "Donate yellow items on Thursday. Touch the feet of a teacher. Visit a temple.",
        "GLOBAL": "Express gratitude to a past teacher. Donate to an education charity. Read a book that challenges your thinking.",
        "duration": "21 days",
    },
    "spouse_debt": {
        "label": "Partnership Pattern",
        "why": "Relationship patterns repeat — the same conflicts, the same distance. Something from the past is echoing into current partnerships.",
        "IN": "Donate white items on Friday. Serve your partner with respect.",
        "GLOBAL": "Write an honest letter to your partner (send or don't). Practice one act of unconditional kindness toward them daily.",
        "duration": "21 days",
    },
}


# Sleeping planet awakening (plain English)
AWAKENING = {
    "Sun":     {"why": "Your ability to be seen and recognized is dormant. Opportunities exist but you're invisible to them.",
                "IN": "Place a copper coin in flowing water on Sunday. Offer water to the rising sun for 7 days.",
                "GLOBAL": "Stand in morning sunlight for 5 minutes daily. Take one action this week that makes you visible — publish, present, or speak up."},
    "Moon":    {"why": "Your emotional intelligence is blocked. Decisions feel cloudy and relationships feel distant.",
                "IN": "Keep a silver item with you. Offer milk on Monday evenings.",
                "GLOBAL": "Journal for 10 minutes before bed each night this week. Name three emotions you felt today."},
    "Mars":    {"why": "Your ability to take decisive action is stuck. You know what to do but can't seem to start.",
                "IN": "Donate red lentils on Tuesday. Carry a copper item.",
                "GLOBAL": "Do something physically challenging this week — a hard workout, a cold shower, a brave conversation. Break the inertia."},
    "Mercury": {"why": "Your communication and analytical abilities are foggy. Words don't land, deals stall, ideas feel stuck.",
                "IN": "Feed birds green moong on Wednesday. Donate to education.",
                "GLOBAL": "Write 500 words about anything — a journal entry, a letter, a plan. Clear the mental blockage through writing."},
    "Jupiter": {"why": "Your wisdom energy is dormant. Growth opportunities pass by because the learning channel is blocked.",
                "IN": "Donate yellow sweets on Thursday. Respect teachers and elders.",
                "GLOBAL": "Express gratitude to a mentor this week. Wear yellow on Thursday. Read something that expands your thinking."},
    "Venus":   {"why": "Your ability to attract — love, beauty, resources — is suppressed. Life feels functional but joyless.",
                "IN": "Offer white flowers on Friday. Donate white items to a woman.",
                "GLOBAL": "Create something beautiful this week. Take yourself somewhere aesthetically inspiring. Wear white on Friday."},
    "Saturn":  {"why": "Your discipline and long-term building capacity is blocked. Hard work isn't compounding into results.",
                "IN": "Donate mustard oil on Saturday. Serve workers and laborers.",
                "GLOBAL": "Volunteer your time this Saturday. Help someone who does hard physical work. Wear black or navy."},
    "Rahu":    {"why": "Your ability to break through into new territory is stuck. Ambition exists but the path forward is unclear.",
                "IN": "Donate blue items on Saturday. Keep sandalwood near you.",
                "GLOBAL": "Identify one unconventional approach to your biggest current challenge. Meditate on what you're truly chasing vs. what you need."},
    "Ketu":    {"why": "Your intuition and ability to release the past is blocked. You're holding on to something that's holding you back.",
                "IN": "Feed a stray dog. Donate a brown blanket on Tuesday.",
                "GLOBAL": "Spend 20 minutes in complete silence. Identify one thing you need to let go of and take one concrete step to release it."},
}


# ════════════════════════════════════════════
# 4. DATA CLASSES
# ════════════════════════════════════════════

@dataclass
class MantraCard:
    planet: str              # internal only — never shown to user
    energy_label: str        # "Discipline & Structure"
    mantra_text: str         # Sanskrit OR affirmation based on locale
    pronunciation: str       # phonetic guide (IN only) or empty
    affirmation: str         # always present
    count: int               # repetition count
    time_suggestion: str     # "morning, especially Saturday"
    locale: str              # "IN" or "GLOBAL"

@dataclass
class PracticeCard:
    practice_id: str         # "jupiter_awakening_thursday"
    priority: int            # 1 = primary, 2 = secondary, 3 = supporting
    energy_label: str        # "Wisdom & Expansion"
    domain: str              # "growth", "career", "relationship"
    why: str                 # plain English reason
    what: str                # one specific action
    how: str                 # step-by-step instruction
    day: str                 # "Thursday" or "Daily"
    duration: str            # "21 days" or "This week" or "Every Saturday until June"
    practice_type: str       # "remedy" | "awakening" | "rin_clearing" | "convergence"
    convergence_score: float # 0.0–1.0, higher = more systems agree
    color: str               # hex color for UI
    chakra: str              # "Solar Plexus" — for UI energy display

@dataclass
class SleepingAlert:
    energy_label: str        # "Wisdom & Expansion"
    why: str                 # "Your wisdom energy is dormant..."
    practice: str            # the awakening action
    domain: str
    color: str
    duration: str            # "21 days"

@dataclass
class RinCard:
    label: str               # "Wisdom Pattern"
    why: str                 # plain English
    clearing_practice: str   # locale-gated action
    duration: str            # "21 days"
    domain: str

@dataclass
class DayPlan:
    day_name: str            # "Monday"
    date_str: str            # "2026-04-01"
    energy_label: str        # "Emotional Clarity"
    primary_action: str      # what to do that day
    mantra: str              # that day's mantra/affirmation
    color: str               # hex color for UI
    is_today: bool

@dataclass
class ChakraStatus:
    karaka: str              # "AK" — internal
    label: str               # "Soul Purpose"
    chakra_name: str         # "Crown"
    focus: str               # "Meditation on life direction"
    status: str              # "Flowing" | "Stressed" | "Dormant"
    color: str
    completion_pct: int      # 0-100

@dataclass
class PracticeSchedule:
    generated_at: str
    cache_key: str           # for fire-and-forget caching
    locale: str
    primary_practice: PracticeCard
    mantra_of_the_day: MantraCard
    sleeping_alerts: list    # List[SleepingAlert]
    rin_cards: list          # List[RinCard]
    supporting_practices: list  # List[PracticeCard] (max 2)
    weekly_plan: list        # List[DayPlan] (7 days)
    chakra_map: list         # List[ChakraStatus]
    streak_data: dict        # {"current": 0, "longest": 0, "total_completed": 0}
    convergence_summary: str # "3 of 4 systems agree: career energy peaks this month"


# ════════════════════════════════════════════
# 5. CORE ENGINE
# ════════════════════════════════════════════

def generate_practice_schedule(
    chart_data: dict,
    jaimini_data: dict,
    lal_kitab_data: dict,
    current_country: str = "US",
    birth_date: str = None,
    streak_data: dict = None,
) -> dict:
    """
    Main entry point. Reads stored data, returns full PracticeSchedule as dict.
    ZERO extra DB queries.

    Args:
        chart_data: charts.chart_data JSONB (planets, houses, lagna, etc.)
        jaimini_data: charts.jaimini_data JSONB (karakas, dashas, arudhas)
        lal_kitab_data: charts.lal_kitab_data JSONB (varshphal, sleeping, rin, etc.)
        current_country: ISO country code for locale gate
        birth_date: for age calculation (Umra)
        streak_data: from practice_log table if available
    """
    locale = "IN" if current_country == "IN" else "GLOBAL"
    today = date.today()

    # ── Extract key data from stored JSONB ──
    # Hotfix: Supabase JSONB may arrive as string
    chart_data = _safe_json(chart_data)
    jaimini_data = _safe_json(jaimini_data)
    lal_kitab_data = _safe_json(lal_kitab_data)
    if isinstance(streak_data, str):
        try: streak_data = json.loads(streak_data)
        except: streak_data = None

    planets = _extract_planets(chart_data)
    lagna = _extract_lagna(chart_data)
    karakas = _extract_karakas(jaimini_data)
    current_dasha = _extract_current_dasha(jaimini_data)
    varshphal = _extract_varshphal(lal_kitab_data)
    sleeping = _extract_sleeping_planets(lal_kitab_data)
    rin_debts = _extract_rin(lal_kitab_data)
    enemy_houses = _extract_enemy_houses(lal_kitab_data)
    masik_phal = _extract_masik_phal(lal_kitab_data)
    age = _calculate_age(birth_date) if birth_date else None

    # ── 1. Score convergence for each planet ──
    convergence = _score_planet_convergence(
        planets, karakas, current_dasha, varshphal, sleeping, masik_phal, age
    )

    # ── 2. Determine primary planet (highest convergence) ──
    primary_planet = _select_primary_planet(convergence, sleeping)

    # ── 3. Build practices ──
    primary_practice = _build_primary_practice(primary_planet, convergence, sleeping, locale)
    supporting = _build_supporting_practices(convergence, primary_planet, sleeping, locale)
    mantra = _build_mantra_card(primary_planet, locale)
    sleeping_alerts = _build_sleeping_alerts(sleeping, locale)
    rin_cards = _build_rin_cards(rin_debts, locale)
    weekly_plan = _build_weekly_plan(convergence, primary_planet, locale, today)
    chakra_map = _build_chakra_map(karakas, sleeping, convergence)
    convergence_summary = _build_convergence_summary(convergence, primary_planet)

    # ── 4. Cache key (recompute weekly) ──
    week_key = today.isocalendar()[1]
    cache_input = f"{lagna}_{primary_planet}_{week_key}_{today.year}"
    cache_key = hashlib.md5(cache_input.encode()).hexdigest()[:12]

    schedule = PracticeSchedule(
        generated_at=datetime.utcnow().isoformat(),
        cache_key=cache_key,
        locale=locale,
        primary_practice=primary_practice,
        mantra_of_the_day=mantra,
        sleeping_alerts=sleeping_alerts,
        rin_cards=rin_cards,
        supporting_practices=supporting,
        weekly_plan=weekly_plan,
        chakra_map=chakra_map,
        streak_data=streak_data or {"current": 0, "longest": 0, "total_completed": 0},
        convergence_summary=convergence_summary,
    )

    return _schedule_to_dict(schedule)


# ════════════════════════════════════════════
# 6. CONVERGENCE SCORING
# ════════════════════════════════════════════

def _score_planet_convergence(planets, karakas, current_dasha, varshphal, sleeping, masik_phal, age):
    """
    Score each planet 0.0–1.0 based on how many systems point to it.
    Higher score = this planet's energy needs the most attention RIGHT NOW.
    """
    scores = {}

    for planet in PLANET_ENERGY:
        score = 0.0
        reasons = []

        # Jaimini Dasha — is this planet the lord of the current dasha sign?
        if current_dasha and current_dasha.get("lord") == planet:
            score += 0.3
            reasons.append("active in your current life chapter")

        # Jaimini Karaka — is this planet a key karaka?
        karaka_role = None
        for k in (karakas or []):
            if k.get("planet") == planet:
                karaka_role = k.get("karaka")
                # AK and AmK get higher weight
                if karaka_role in ("AK", "AmK"):
                    score += 0.25
                    reasons.append(f"core to your {KARAKA_CHAKRA.get(karaka_role, {}).get('label', 'identity')}")
                else:
                    score += 0.15
                    reasons.append(f"connected to your {KARAKA_CHAKRA.get(karaka_role, {}).get('label', 'life pattern')}")
                break

        # Varshphal — is this planet the year lord or in a strong annual house?
        if varshphal:
            if varshphal.get("year_lord") == planet:
                score += 0.25
                reasons.append("driving energy for your entire year")
            annual_placements = varshphal.get("annual_placements", {})
            if planet in annual_placements:
                house = annual_placements[planet]
                if house in (1, 4, 5, 7, 9, 10, 11):  # favorable houses
                    score += 0.1
                    reasons.append("well-placed this year")
                elif house in (6, 8, 12):  # challenging houses
                    score += 0.2  # needs MORE attention
                    reasons.append("needs extra support this year")

        # Sleeping planet — blocked = highest priority
        if planet in [s.get("planet") for s in (sleeping or [])]:
            score += 0.35
            reasons.append("currently blocked and needs awakening")

        # Masik Phal — monthly activation
        if masik_phal and masik_phal.get("active_planet") == planet:
            score += 0.15
            reasons.append("activated this month")

        # Umra age activation
        if age:
            umra_planets = _get_umra_planets(age, planets)
            if planet in umra_planets:
                score += 0.1
                reasons.append("age-activated this year")

        scores[planet] = {"score": min(score, 1.0), "reasons": reasons}

    return scores


def _get_umra_planets(age, planets):
    """Umra age activation — which houses (and their lords) are active at this age."""
    UMRA_TABLE = {
        1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [6], 7: [7],
        8: [8], 9: [9], 10: [10], 11: [11], 12: [12],
        15: [5], 16: [3], 22: [10], 30: [9], 34: [7],
        36: [8], 48: [10], 54: [11], 60: [12],
    }
    active_houses = UMRA_TABLE.get(age, [])
    # Map houses to their lords (simplified — real impl uses chart_data)
    return []  # placeholder — would need house-lord mapping from chart_data


# ════════════════════════════════════════════
# 7. BUILDERS
# ════════════════════════════════════════════

def _select_primary_planet(convergence, sleeping):
    """Pick the ONE planet with highest convergence. Sleeping planets get priority boost."""
    sleeping_planets = [s.get("planet") for s in (sleeping or [])]

    best_planet = None
    best_score = -1

    for planet, data in convergence.items():
        score = data["score"]
        # Sleeping planet boost: if tied, sleeping planet wins
        if planet in sleeping_planets:
            score += 0.05
        if score > best_score:
            best_score = score
            best_planet = planet

    return best_planet or "Jupiter"  # fallback


def _build_primary_practice(planet, convergence, sleeping, locale):
    """Build the ONE primary practice card."""
    info = PLANET_ENERGY.get(planet, PLANET_ENERGY["Jupiter"])
    remedy = REMEDIES.get(planet, REMEDIES["Jupiter"])
    conv = convergence.get(planet, {"score": 0.5, "reasons": []})

    is_sleeping = planet in [s.get("planet") for s in (sleeping or [])]

    if is_sleeping:
        awakening = AWAKENING.get(planet, AWAKENING["Jupiter"])
        why = awakening["why"]
        what = awakening[locale]
        practice_type = "awakening"
        duration = "21 days"
    else:
        why = _build_why_text(planet, conv["reasons"])
        what = remedy[locale]["action"]
        practice_type = "convergence" if conv["score"] >= 0.5 else "remedy"
        duration = "This week" if conv["score"] < 0.7 else "21 days — this is a priority cycle"

    how = _build_how_text(planet, what, locale)

    return PracticeCard(
        practice_id=f"{planet.lower()}_{practice_type}_{info['day'].lower()}",
        priority=1,
        energy_label=info["label"],
        domain=info["domain"],
        why=why,
        what=what,
        how=how,
        day=info["day"],
        duration=duration,
        practice_type=practice_type,
        convergence_score=conv["score"],
        color=info["color"],
        chakra=info["chakra"],
    )


def _build_supporting_practices(convergence, primary_planet, sleeping, locale):
    """Build 1-2 supporting practices (different from primary)."""
    sorted_planets = sorted(
        convergence.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    supporting = []
    for planet, data in sorted_planets:
        if planet == primary_planet:
            continue
        if data["score"] < 0.2:
            continue
        if len(supporting) >= 2:
            break

        info = PLANET_ENERGY.get(planet, PLANET_ENERGY["Jupiter"])
        remedy = REMEDIES.get(planet, REMEDIES["Jupiter"])
        is_sleeping = planet in [s.get("planet") for s in (sleeping or [])]

        if is_sleeping:
            aw = AWAKENING.get(planet, {})
            what = aw.get(locale, remedy[locale]["action"])
            ptype = "awakening"
        else:
            what = remedy[locale]["action"]
            ptype = "remedy"

        supporting.append(PracticeCard(
            practice_id=f"{planet.lower()}_{ptype}_{info['day'].lower()}",
            priority=len(supporting) + 2,
            energy_label=info["label"],
            domain=info["domain"],
            why=_build_why_text(planet, data["reasons"]),
            what=what,
            how=_build_how_text(planet, what, locale),
            day=info["day"],
            duration="This week",
            practice_type=ptype,
            convergence_score=data["score"],
            color=info["color"],
            chakra=info["chakra"],
        ))

    return supporting


def _build_mantra_card(planet, locale):
    """Build the mantra/affirmation card for the primary planet."""
    m = MANTRAS.get(planet, MANTRAS["Jupiter"])
    info = PLANET_ENERGY.get(planet, PLANET_ENERGY["Jupiter"])

    if locale == "IN":
        text = m["sanskrit"]
        pronunciation = m["phonetic"]
    else:
        text = m["affirmation"]
        pronunciation = ""

    return MantraCard(
        planet=planet,
        energy_label=info["label"],
        mantra_text=text,
        pronunciation=pronunciation,
        affirmation=m["affirmation"],
        count=m["count"],
        time_suggestion=m["time"],
        locale=locale,
    )


def _build_sleeping_alerts(sleeping, locale):
    """Build alert cards for each sleeping planet."""
    alerts = []
    for s in (sleeping or []):
        planet = s.get("planet", "Jupiter")
        aw = AWAKENING.get(planet, AWAKENING["Jupiter"])
        info = PLANET_ENERGY.get(planet, PLANET_ENERGY["Jupiter"])
        alerts.append(SleepingAlert(
            energy_label=info["label"],
            why=aw["why"],
            practice=aw[locale],
            domain=info["domain"],
            color=info["color"],
            duration="21 days",
        ))
    return alerts


def _build_rin_cards(rin_debts, locale):
    """Build cards for active karmic debts."""
    cards = []
    for rin in (rin_debts or []):
        rin_type = rin.get("type", "self_debt")
        clearing = RIN_CLEARING.get(rin_type, RIN_CLEARING["self_debt"])
        cards.append(RinCard(
            label=clearing["label"],
            why=clearing["why"],
            clearing_practice=clearing[locale],
            duration=clearing["duration"],
            domain="spiritual",
        ))
    return cards


def _build_weekly_plan(convergence, primary_planet, locale, today):
    """Build a 7-day plan with one action per day."""
    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    DAY_PLANET = {
        "Monday": "Moon", "Tuesday": "Mars", "Wednesday": "Mercury",
        "Thursday": "Jupiter", "Friday": "Venus", "Saturday": "Saturn", "Sunday": "Sun",
    }

    # Find start of this week (Monday)
    days_since_monday = today.weekday()  # Monday=0
    monday = today - timedelta(days=days_since_monday)

    plan = []
    for i, day_name in enumerate(DAY_ORDER):
        day_date = monday + timedelta(days=i)
        planet = DAY_PLANET[day_name]
        info = PLANET_ENERGY[planet]
        remedy = REMEDIES.get(planet, REMEDIES["Jupiter"])
        mantra = MANTRAS.get(planet, MANTRAS["Jupiter"])

        # If this day's planet is the primary planet, emphasize it
        if planet == primary_planet:
            action = remedy[locale]["action"] + " ← This is your primary practice day."
        else:
            # Lighter action for non-primary days
            action = remedy[locale].get("item", remedy[locale]["action"])

        plan.append(DayPlan(
            day_name=day_name,
            date_str=day_date.isoformat(),
            energy_label=info["label"],
            primary_action=action,
            mantra=mantra["affirmation"] if locale == "GLOBAL" else mantra["sanskrit"],
            color=info["color"],
            is_today=(day_date == today),
        ))

    return plan


def _build_chakra_map(karakas, sleeping, convergence):
    """Map Jaimini Karakas to Chakras with status."""
    chakra_list = []
    sleeping_planets = [s.get("planet") for s in (sleeping or [])]

    for k in (karakas or []):
        karaka_code = k.get("karaka", "")
        planet = k.get("planet", "")
        chakra_info = KARAKA_CHAKRA.get(karaka_code)
        if not chakra_info:
            continue

        conv = convergence.get(planet, {"score": 0})
        score = conv["score"] if isinstance(conv, dict) else 0

        if planet in sleeping_planets:
            status = "Dormant"
            completion = int(score * 30)  # low
        elif score >= 0.6:
            status = "Flowing"
            completion = int(score * 100)
        else:
            status = "Stressed"
            completion = int(score * 60)

        chakra_list.append(ChakraStatus(
            karaka=karaka_code,
            label=chakra_info["label"],
            chakra_name=chakra_info["chakra"].split("(")[-1].rstrip(")") if "(" in chakra_info["chakra"] else chakra_info["chakra"],
            focus=chakra_info["focus"],
            status=status,
            color=chakra_info["color"],
            completion_pct=min(completion, 100),
        ))

    return chakra_list


def _build_convergence_summary(convergence, primary_planet):
    """One-line summary of how many systems agree."""
    primary = convergence.get(primary_planet, {"score": 0.5, "reasons": []})
    n_reasons = len(primary["reasons"])
    energy = PLANET_ENERGY.get(primary_planet, {}).get("label", "primary")

    if n_reasons >= 4:
        return f"Strong alignment: {n_reasons} indicators confirm your {energy.lower()} energy is the focus right now."
    elif n_reasons >= 2:
        return f"Multiple signals point to {energy.lower()} energy as your priority this period."
    else:
        return f"Your {energy.lower()} energy is gently active. Light practice recommended."


# ════════════════════════════════════════════
# 8. TEXT BUILDERS (ZERO JARGON)
# ════════════════════════════════════════════

def _build_why_text(planet, reasons):
    """Build a plain-English WHY from convergence reasons."""
    info = PLANET_ENERGY.get(planet, {})
    energy = info.get("label", "life energy")

    if not reasons:
        return f"Your {energy.lower()} is active right now. A small, focused action can amplify it."

    if len(reasons) == 1:
        return f"Your {energy.lower()} is {reasons[0]}. A focused practice helps you make the most of this window."

    # Multiple reasons = stronger signal
    reason_text = reasons[0]
    for r in reasons[1:]:
        reason_text += f", and {r}"
    return f"Your {energy.lower()} is {reason_text}. Multiple indicators confirm this is a priority."


def _build_how_text(planet, what, locale):
    """Build step-by-step HOW from the WHAT action."""
    info = PLANET_ENERGY.get(planet, {})
    day = info.get("day", "any day")
    time = MANTRAS.get(planet, {}).get("time", "morning")

    steps = [
        f"Best day: {day}. Best time: {time}.",
        what,
        f"Pair with today's mantra (see below) for maximum effect.",
        "Mark as complete when done — consistency matters more than perfection.",
    ]
    return " → ".join(steps)


# ════════════════════════════════════════════
# 9. DATA EXTRACTORS (from stored JSONB)
# ════════════════════════════════════════════

def _extract_planets(chart_data):
    """Extract planet positions from chart_data JSONB."""
    if not chart_data:
        return {}
    if isinstance(chart_data, str): chart_data = _safe_json(chart_data)
    return chart_data.get("planets", chart_data.get("planet_positions", {}))


def _extract_lagna(chart_data):
    if not chart_data:
        return "Aries"
    if isinstance(chart_data, str): chart_data = _safe_json(chart_data)
    return chart_data.get("lagna", chart_data.get("ascendant", {}).get("sign", "Aries"))


def _extract_karakas(jaimini_data):
    if not jaimini_data:
        return []
    if isinstance(jaimini_data, str): jaimini_data = _safe_json(jaimini_data)
    return jaimini_data.get("karakas", jaimini_data.get("chara_karakas", []))


def _extract_current_dasha(jaimini_data):
    if not jaimini_data:
        return None
    if isinstance(jaimini_data, str): jaimini_data = _safe_json(jaimini_data)
    dashas = jaimini_data.get("chara_dasha", jaimini_data.get("dasha_periods", []))
    for d in dashas:
        if d.get("active") or d.get("is_current"):
            return d
    return dashas[0] if dashas else None


def _extract_varshphal(lk_data):
    if not lk_data:
        return None
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    return lk_data.get("varshphal", lk_data.get("current_varshphal"))


def _extract_sleeping_planets(lk_data):
    if not lk_data:
        return []
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    return lk_data.get("sleeping_planets", lk_data.get("sleeping", []))


def _extract_rin(lk_data):
    if not lk_data:
        return []
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    return lk_data.get("rin_debts", lk_data.get("karmic_debts", lk_data.get("rin", [])))


def _extract_enemy_houses(lk_data):
    if not lk_data:
        return []
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    return lk_data.get("enemy_houses", [])


def _extract_masik_phal(lk_data):
    if not lk_data:
        return None
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    return lk_data.get("masik_phal", lk_data.get("monthly"))


def _calculate_age(birth_date_str):
    try:
        if isinstance(birth_date_str, str):
            bd = datetime.fromisoformat(birth_date_str.replace("Z", "+00:00")).date()
        else:
            bd = birth_date_str
        today = date.today()
        return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    except Exception:
        return None


# ════════════════════════════════════════════
# 10. SERIALIZATION
# ════════════════════════════════════════════

def _schedule_to_dict(schedule: PracticeSchedule) -> dict:
    """Convert dataclass tree to JSON-serializable dict."""
    def _dc_to_dict(obj):
        if hasattr(obj, '__dataclass_fields__'):
            return {k: _dc_to_dict(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, list):
            return [_dc_to_dict(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: _dc_to_dict(v) for k, v in obj.items()}
        return obj

    return _dc_to_dict(schedule)


# ════════════════════════════════════════════
# 11. FASTAPI ENDPOINT HELPERS
# ════════════════════════════════════════════

def format_practice_for_predict_prompt(schedule: dict) -> str:
    """
    Format the practice schedule as a context block for the /predict LLM prompt.
    This ensures predictions reference the user's active practices.
    """
    primary = schedule.get("primary_practice", {})
    mantra = schedule.get("mantra_of_the_day", {})
    sleeping = schedule.get("sleeping_alerts", [])
    rin = schedule.get("rin_cards", [])

    lines = ["ACTIVE PRACTICES:"]
    lines.append(f"  Primary: {primary.get('energy_label', 'N/A')} — {primary.get('what', 'N/A')}")
    lines.append(f"  Type: {primary.get('practice_type', 'remedy')} | Convergence: {primary.get('convergence_score', 0):.0%}")

    if mantra:
        lines.append(f"  Mantra: {mantra.get('affirmation', '')}")

    if sleeping:
        lines.append(f"  SLEEPING ENERGIES: {', '.join(s.get('energy_label', '') for s in sleeping)}")

    if rin:
        lines.append(f"  KARMIC PATTERNS: {', '.join(r.get('label', '') for r in rin)}")

    streak = schedule.get("streak_data", {})
    if streak.get("current", 0) > 0:
        lines.append(f"  Streak: {streak['current']} days active")

    return "\n".join(lines)


# ════════════════════════════════════════════
# 12. SELF-TEST
# ════════════════════════════════════════════

if __name__ == "__main__":
    # Test with Ramandeep's mock data
    test_chart = {"planets": {"Sun": {"sign": "Scorpio"}, "Moon": {"sign": "Pisces"}, "Mars": {"sign": "Sagittarius"}, "Saturn": {"sign": "Cancer"}, "Jupiter": {"sign": "Pisces"}, "Venus": {"sign": "Scorpio"}, "Mercury": {"sign": "Libra"}, "Rahu": {"sign": "Scorpio"}, "Ketu": {"sign": "Taurus"}}, "lagna": "Capricorn"}
    test_jaimini = {"karakas": [{"karaka": "AK", "planet": "Mars", "sign_name": "Sagittarius"}, {"karaka": "AmK", "planet": "Saturn", "sign_name": "Cancer"}, {"karaka": "DK", "planet": "Sun", "sign_name": "Scorpio"}, {"karaka": "BK", "planet": "Mercury", "sign_name": "Libra"}, {"karaka": "MK", "planet": "Venus", "sign_name": "Scorpio"}, {"karaka": "PK", "planet": "Jupiter", "sign_name": "Pisces"}, {"karaka": "GK", "planet": "Moon", "sign_name": "Pisces"}], "chara_dasha": [{"sign_name": "Aries", "lord": "Mars", "years": 8, "start": "2024-11-25", "end": "2032-11-25", "active": True}]}
    test_lk = {"varshphal": {"year_lord": "Saturn", "annual_placements": {"Saturn": 10, "Sun": 1, "Jupiter": 3}}, "sleeping_planets": [{"planet": "Jupiter", "house": 3, "reason": "In dusthana with no benefic support"}], "rin_debts": [{"type": "guru_debt", "planet": "Jupiter", "house": 6}], "masik_phal": {"active_planet": "Saturn", "month": "April"}}

    result = generate_practice_schedule(
        chart_data=test_chart,
        jaimini_data=test_jaimini,
        lal_kitab_data=test_lk,
        current_country="US",
        birth_date="1974-11-26",
    )

    print(json.dumps(result, indent=2, default=str))
