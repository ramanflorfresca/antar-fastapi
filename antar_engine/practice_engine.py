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




# Planetary sound frequencies (Hz) — same vibrational energy as beej mantras
PLANET_FREQUENCIES_MAP = {
    "Sun": 126.22, "Moon": 210.42, "Mars": 144.72, "Mercury": 141.27,
    "Jupiter": 183.58, "Venus": 221.23, "Saturn": 147.85,
    "Rahu": 432.00, "Ketu": 136.10,
}

# Traditional mantra repetition counts per planet
PLANET_COUNTS_MAP = {
    "Sun": 7, "Moon": 11, "Mars": 7, "Mercury": 9,
    "Jupiter": 11, "Venus": 11, "Saturn": 11, "Rahu": 18, "Ketu": 7,
}

# ─── Planet Practice Metadata (LK tradition + plain language framing) ───────
PLANET_PRACTICE_META = {
    "Sun": {
        "why": "Your sense of identity and self-worth is the energy being worked on right now. This practice builds the internal confidence that makes external recognition possible.",
        "why_science": "Repetitive intention-setting at the same time daily recalibrates your reticular activating system — the brain's filter that decides what opportunities to notice.",
        "why_india": "This energy governs identity, self-worth, and inner authority. When it is blocked, recognition and authority become effortful. The practice re-attunes your energy field to a steadier rhythm.",
        "duration_days": 7,
        "duration_label": "7 days",
        "duration_reason": "7 mirrors the solar weekly cycle. One full week resets the pattern.",
        "best_day": "Sunday",
        "best_time": "sunrise, facing east",
        "sessions_per_week": 7,
        "count": 7,
        "completion_milestone": "After 7 days, notice whether opportunities for visibility feel more natural.",
        "ongoing": False,
        "streak_type": "daily",
    },
    "Moon": {
        "why": "Your emotional processing patterns are being recalibrated. This practice creates a pause between feeling and reacting — giving you clarity instead of reactivity.",
        "why_science": "The Moon's cycle directly affects human fluid systems and sleep rhythms. Consistent evening practice syncs your nervous system to a calmer biological rhythm.",
        "why_india": "This energy governs the mind and emotional memory. When it is blocked it creates anxiety, over-attachment, and sleep issues. The practice clears the emotional field.",
        "duration_days": 11,
        "duration_label": "11 days",
        "duration_reason": "11 is the number of emotional completion in Vedic numerology. One cycle of the Moon's emotional arc.",
        "best_day": "Monday",
        "best_time": "evening, before sleep",
        "sessions_per_week": 7,
        "count": 11,
        "completion_milestone": "After 11 days, emotional decisions should feel less reactive and more grounded.",
        "ongoing": False,
        "streak_type": "daily",
    },
    "Mars": {
        "why": "Your action energy and drive need direction right now. This practice channels aggression and impatience into decisive, purposeful movement instead of scattered effort.",
        "why_science": "High-intensity breath patterns (like Kapalabhati) activate the sympathetic nervous system constructively — releasing accumulated stress hormones without aggression.",
        "why_india": "This energy governs vital force and the capacity to execute. When it is afflicted it creates accidents, conflicts, and wasted effort. The practice redirects this force.",
        "duration_days": 49,
        "duration_label": "7 Tuesdays",
        "duration_reason": "This energy needs 7 consecutive Tuesday cycles to fully redirect. Tuesday is when this pattern is most receptive.",
        "best_day": "Tuesday",
        "best_time": "morning, after exercise",
        "sessions_per_week": 1,
        "count": 7,
        "completion_milestone": "After 7 Tuesdays, notice whether impulsive decisions have decreased.",
        "ongoing": False,
        "streak_type": "weekly_tuesday",
    },
    "Mercury": {
        "why": "Your communication clarity and analytical precision are the focus right now. This practice sharpens how you express ideas and reduces overthinking loops.",
        "why_science": "Vocal repetition of structured sound patterns activates Broca's area and the prefrontal cortex simultaneously — literally training clearer thinking and expression.",
        "why_india": "This energy governs intellect and speech. When it is weak it causes miscommunication, contracts gone wrong, and scattered thinking. The practice restores precision.",
        "duration_days": 9,
        "duration_label": "9 days",
        "duration_reason": "9 completes a Mercury cognitive cycle. Enough repetition to build a new communication habit.",
        "best_day": "Wednesday",
        "best_time": "morning, before important conversations",
        "sessions_per_week": 7,
        "count": 9,
        "completion_milestone": "After 9 days, notice whether your communication feels more precise and less anxious.",
        "ongoing": False,
        "streak_type": "daily",
    },
    "Jupiter": {
        "why": "Your capacity for growth, wisdom, and expansion is being activated. This practice opens you to learning and opportunities that your current beliefs might be filtering out.",
        "why_science": "21 days is the neurological minimum to form a new cognitive habit. Gratitude and expansion practices literally rewire the brain's default mode network toward opportunity-seeking.",
        "why_india": "This energy governs life purpose and the capacity to learn. When it is weak the mind closes to growth and creates arrogance or missed opportunities. The practice restores receptivity.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "21 days (3 lunar weeks) is the minimum to shift a belief pattern. This is the slowest-moving expansion energy and requires sustained intention.",
        "best_day": "Thursday",
        "best_time": "morning, ideally before learning something new",
        "sessions_per_week": 7,
        "count": 11,
        "completion_milestone": "After 21 days, notice whether mentors, teachers, or growth opportunities appear more readily.",
        "ongoing": True,
        "streak_type": "daily",
    },
    "Venus": {
        "why": "Your relationship patterns and creative expression are the focus. This practice softens defensiveness and opens you to giving and receiving more freely.",
        "why_science": "Loving-kindness practices (the emotional equivalent of Venus remedies) measurably increase oxytocin, reduce cortisol, and improve relationship satisfaction within 21 days.",
        "why_india": "This energy governs desire, beauty, and relationships. When it is afflicted it creates relationship dissatisfaction, financial over-indulgence, and blocked creativity. The practice restores flow.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "Relationship cycles run on a 21-day rhythm. 21 days is enough to shift a core relationship pattern.",
        "best_day": "Friday",
        "best_time": "evening, in a calm space",
        "sessions_per_week": 7,
        "count": 11,
        "completion_milestone": "After 21 days, notice whether your key relationships feel more fluid and less effortful.",
        "ongoing": True,
        "streak_type": "daily",
    },
    "Saturn": {
        "why": "Your relationship with discipline, long-term thinking, and karmic patterns is being worked on. This practice builds the tolerance for delay that turns ambition into lasting results.",
        "why_science": "40 days is the clinical minimum for breaking a deeply ingrained behavioral pattern (used in addiction recovery, habit formation research). Saturn rules exactly this kind of structural change.",
        "why_india": "This energy governs cause and effect and discipline through endurance. It only responds to sustained effort — there are no shortcuts. The practice activates patience as a strategic tool.",
        "duration_days": 40,
        "duration_label": "40 days",
        "duration_reason": "40 days is the minimum commitment cycle for structural change. Long-term structures only shift through demonstrated sustained discipline.",
        "best_day": "Saturday",
        "best_time": "early morning, before the day begins",
        "sessions_per_week": 7,
        "count": 11,
        "completion_milestone": "After 40 days, notice whether patience in key situations has increased and whether chronic delays are easing.",
        "ongoing": True,
        "streak_type": "daily",
    },
    "Rahu": {
        "why": "Your relationship with obsession, ambition, and unconventional paths is being recalibrated. This practice helps you use disruptive energy constructively instead of compulsively.",
        "why_science": "18 days of consistent mindfulness around a specific pattern is enough to create metacognitive awareness — the ability to observe your own obsessive tendencies without being controlled by them.",
        "why_india": "This energy governs illusion and worldly obsession. It amplifies whatever it touches — this practice channels that amplification toward chosen goals rather than unconscious patterns.",
        "duration_days": 18,
        "duration_label": "18 days",
        "duration_reason": "18 days is one full nodal completion cycle for this pattern. 18 consecutive days creates a full micro-cycle.",
        "best_day": "Saturday",
        "best_time": "before sunset",
        "sessions_per_week": 7,
        "count": 18,
        "completion_milestone": "After 18 days, notice whether obsessive thought loops around one particular desire have softened.",
        "ongoing": False,
        "streak_type": "daily",
    },
    "Ketu": {
        "why": "Your capacity for release, detachment, and trusting your intuition is being developed. This practice helps you let go of outcomes that are blocking your next chapter.",
        "why_science": "Detachment practices activate the default mode network differently than goal-focused thinking — they increase insight and creativity by reducing cognitive fixation.",
        "why_india": "This energy governs liberation and inherited wisdom. It creates confusion when resisted but clarity when surrendered to. The practice activates the wisdom side of this pattern.",
        "duration_days": 7,
        "duration_label": "7 days",
        "duration_reason": "Release energy works in 7-day cycles. One week of consistent practice completes one detachment arc.",
        "best_day": "Saturday",
        "best_time": "evening or before sleep",
        "sessions_per_week": 7,
        "count": 7,
        "completion_milestone": "After 7 days, notice whether one thing you have been holding onto feels lighter.",
        "ongoing": False,
        "streak_type": "daily",
    },
}
# Remedy duration logic based on Lal Kitab house affliction type
REMEDY_DURATION_RULES = {
    "sleeping_planet": {
        "duration_days": 21,
        "duration_label": "21 days",
        "reason": "A sleeping planet needs 21 days of consistent activation to wake up. Think of it as physical therapy for an underused muscle — skipping days resets the progress.",
        "frequency": "daily",
    },
    "rin_clearing": {
        "duration_days": 40,
        "duration_label": "40 days without interruption",
        "reason": "Karmic patterns took years to form. 40 uninterrupted days is the minimum to interrupt the cycle. Even one missed day traditionally requires restarting — not as punishment, but because the pattern needs continuous counter-pressure.",
        "frequency": "daily",
        "warning": "Do not break the streak. If you miss a day, restart from day 1.",
    },
    "convergence": {
        "duration_days": 21,
        "duration_label": "21 days",
        "reason": "When multiple timing systems point to the same planet, 21 days of practice synchronizes your actions with the active energy window.",
        "frequency": "daily",
    },
    "weekly": {
        "duration_days": 49,
        "duration_label": "7 weeks",
        "reason": "Some planetary energies only open on specific days of the week. 7 consecutive weeks on the right day completes one full planetary cycle.",
        "frequency": "weekly",
    },
}



# ════════════════════════════════════════════
# 1. PLANET → PLAIN ENGLISH MAPPING
# ════════════════════════════════════════════

PLANET_ENERGY = {
    "Sun":     {"label": "Vitality & Purpose",   "domain": "career",       "color": "#F59E0B", "day": "Sunday",    "chakra": "Solar Plexus",  "element": "Fire"},
    "Moon":    {"label": "Emotional Clarity",       "domain": "wellbeing",    "color": "#94A3B8", "day": "Monday",    "chakra": "Sacral",        "element": "Water"},
    "Mars":    {"label": "Courage & Drive",        "domain": "career",       "color": "#EF4444", "day": "Tuesday",   "chakra": "Root",          "element": "Fire"},
    "Mercury": {"label": "Communication & Clarity", "domain": "career",       "color": "#22C55E", "day": "Wednesday", "chakra": "Throat",        "element": "Earth"},
    "Jupiter": {"label": "Wisdom & Expansion",      "domain": "growth",       "color": "#F59E0B", "day": "Thursday",  "chakra": "Crown",         "element": "Ether"},
    "Venus":   {"label": "Harmony & Connection",       "domain": "relationship", "color": "#EC4899", "day": "Friday",    "chakra": "Heart",         "element": "Water"},
    "Saturn":  {"label": "Discipline & Structure",   "domain": "career",       "color": "#8B5CF6", "day": "Saturday",  "chakra": "Root",          "element": "Air"},
    "Rahu":    {"label": "Amplification & Ambition",  "domain": "growth",       "color": "#6366F1", "day": "Saturday",  "chakra": "Third Eye",     "element": "Air"},
    "Ketu":    {"label": "Release & Insight",      "domain": "spiritual",    "color": "#A78BFA", "day": "Tuesday",   "chakra": "Crown",         "element": "Fire"},
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
        "IN": {"action": "Offer water at sunrise every morning. Donate wheat on Sundays.", "item": "copper coin in flowing water"},
        "GLOBAL": {"action": "Spend 5 minutes in morning sunlight. Volunteer for a leadership role this week.", "item": "wear warm gold or orange on Sunday"},
    },
    "Moon": {
        "IN": {"action": "Offer milk to a Shiva temple on Monday. Keep silver with you.", "item": "white flowers at home"},
        "GLOBAL": {"action": "Take a 10-minute walk by water this week. Write down three feelings you've been avoiding.", "item": "keep a small silver item in your pocket on Monday"},
    },
    "Mars": {
        "IN": {"action": "Donate red lentils on Tuesday. Carry a copper coin for the day.", "item": "sweet bread to a dog on Tuesday"},
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
        "IN": "Offer water at sunrise for 43 days. Respect father figures.",
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
                "IN": "Place a copper coin in flowing water on Sunday. Offer water to the rising light for 7 days.",
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
    frequency_hz: float = 136.10   # planetary frequency in Hz
    # Mantra meta — WHY + duration
    mantra_why: str = ""
    mantra_duration_days: int = 21
    mantra_duration_label: str = "21 days"
    mantra_duration_reason: str = ""
    mantra_best_time: str = "morning"
    mantra_completion_milestone: str = ""
    mantra_streak_type: str = "daily"

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
    frequency_hz: float = 136.10   # planetary frequency in Hz
    mantra_count: int = 11         # repetition count
    # Practice meta — WHY + duration + counter
    practice_why: str = ""
    practice_why_science: str = ""
    duration_days: int = 21
    duration_label: str = "21 days"
    duration_reason: str = ""
    best_day: str = ""
    best_time: str = "morning"
    completion_milestone: str = ""
    streak_type: str = "daily"
    is_ongoing: bool = False

@dataclass
class SleepingAlert:
    energy_label: str        # "Wisdom & Expansion"
    why: str                 # "Your wisdom energy is dormant..."
    practice: str            # the awakening action
    domain: str
    color: str
    duration: str            # "21 days"
    remedy_why: str = ""
    remedy_why_science: str = ""
    duration_days: int = 21
    duration_label: str = "21 days"
    duration_reason: str = ""
    streak_warning: str = ""

@dataclass
class RinCard:
    label: str               # "Wisdom Pattern"
    why: str                 # plain English
    clearing_practice: str   # locale-gated action
    duration: str            # "21 days"
    domain: str
    remedy_why: str = ""
    remedy_why_science: str = ""
    duration_days: int = 40
    duration_label: str = "40 days without interruption"
    duration_reason: str = ""
    streak_warning: str = ""

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
    vimsottari_md: dict = None,
    vimsottari_ad: dict = None,
    next_md: dict = None,
    practice_counts: dict = None,
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
        planets, karakas, current_dasha, varshphal, sleeping, masik_phal, age,
        vimsottari_md=vimsottari_md, vimsottari_ad=vimsottari_ad, next_md=next_md,
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
    # Extract moon_nakshatra for group-based chakra baselines
    _moon_nak_for_chakra = (chart_data or {}).get("planets", {}).get("Moon", {}).get("nakshatra", "")
    chakra_map = _build_chakra_map(karakas, sleeping, convergence, practice_counts=practice_counts, moon_nakshatra=_moon_nak_for_chakra)
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

    _sched_out = _schedule_to_dict(schedule)
    # [gemstone-engine] chart-level primary stone from the ENGINE planet.
    # Additive + guarded: any failure leaves chart_gemstone=None and the
    # schedule payload otherwise byte-identical to before.
    try:
        _sched_out["chart_gemstone"] = select_chart_gemstone(planets, lagna)
    except Exception as _gem_err:
        print(f"[gemstone-engine] non-fatal: {_gem_err}")
        _sched_out["chart_gemstone"] = None
    return _sched_out


# ════════════════════════════════════════════
# 6. CONVERGENCE SCORING
# ════════════════════════════════════════════


# ════════════════════════════════════════════
# 5.5 GEMSTONE (RATNA) ENGINE — chart-level
# ════════════════════════════════════════════
# Deterministic primary-stone selector. ONE stone, from the chart's ENGINE
# planet — never "strengthen everything", never a functional malefic.
# Selection order: yogakaraka -> lagna lord (if it functions benefic and is
# not debilitated) -> strongest benefic-functioning kendra/trikona lord.
# Output dict is INTERNAL: the `planet` field and `why` note are for the
# narrator/translation layer and must never reach the UI raw.

GEM_SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}
GEM_SIGN_ORDER = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius",
                  "Pisces"]
GEM_EXALTATION = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
                  "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
                  "Saturn": "Libra"}
GEM_DEBILITATION = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
                    "Mercury": "Pisces", "Jupiter": "Capricorn",
                    "Venus": "Virgo", "Saturn": "Aries"}
GEM_OWN_SIGNS = {"Sun": ["Leo"], "Moon": ["Cancer"],
                 "Mars": ["Aries", "Scorpio"], "Mercury": ["Gemini", "Virgo"],
                 "Jupiter": ["Sagittarius", "Pisces"],
                 "Venus": ["Taurus", "Libra"],
                 "Saturn": ["Capricorn", "Aquarius"]}

# planet -> stone / metal / first-wear weekday (brief-specified table)
GEM_BY_PLANET = {
    "Sun":     {"stone": "Ruby",            "metal": "gold",            "weekday": "Sunday"},
    "Moon":    {"stone": "Pearl",           "metal": "silver",          "weekday": "Monday"},
    "Mars":    {"stone": "Red Coral",       "metal": "gold/copper",     "weekday": "Tuesday"},
    "Mercury": {"stone": "Emerald",         "metal": "gold/silver",     "weekday": "Wednesday"},
    "Jupiter": {"stone": "Yellow Sapphire", "metal": "gold",            "weekday": "Thursday"},
    "Venus":   {"stone": "Diamond",         "metal": "silver/platinum", "weekday": "Friday"},
    "Saturn":  {"stone": "Blue Sapphire",   "metal": "silver",          "weekday": "Saturday"},
    "Rahu":    {"stone": "Hessonite",       "metal": "silver",          "weekday": "Saturday"},
    "Ketu":    {"stone": "Cat's Eye",       "metal": "silver",          "weekday": "contextual"},
}

# Saturn / Rahu / Ketu stones are trial-wear: watch for adverse effects.
# Blue Sapphire is the single riskiest stone — even when Saturn is a
# legitimate engine planet (yogakaraka for Taurus/Libra, lagna lord for
# Capricorn/Aquarius) it stays test_first, never casually defaulted to.
GEM_TEST_FIRST = {"Saturn", "Rahu", "Ketu"}

# Classical yogakarakas (single planet ruling both a kendra and a trikona).
GEM_YOGAKARAKA_BY_LAGNA = {
    "Taurus": "Saturn", "Libra": "Saturn",
    "Cancer": "Mars", "Leo": "Mars",
    "Capricorn": "Venus", "Aquarius": "Venus",
}

# Parashari functional malefics per lagna (Rahu/Ketu always excluded too).
GEM_FUNCTIONAL_MALEFICS = {
    "Aries":       {"Mercury", "Saturn"},
    "Taurus":      {"Moon", "Jupiter", "Mars"},
    "Gemini":      {"Mars", "Sun", "Jupiter"},
    "Cancer":      {"Mercury", "Venus", "Saturn"},
    "Leo":         {"Mercury", "Venus", "Saturn"},
    "Virgo":       {"Mars", "Jupiter", "Moon"},
    "Libra":       {"Jupiter", "Sun", "Mars"},
    "Scorpio":     {"Mercury", "Venus"},
    "Sagittarius": {"Venus", "Saturn"},
    "Capricorn":   {"Mars", "Jupiter", "Moon"},
    "Aquarius":    {"Moon", "Mars", "Jupiter"},
    "Pisces":      {"Sun", "Venus", "Saturn", "Mercury"},
}

# [chakra-2axis] FUNCTIONAL_BENEFICS
# Parashari functional-benefic baseline per lagna.  Used by the chakra
# two-axis valence (V) calculation.  Calibration-tunable post-launch.
# Kendra-trikona lords + yogakaraka + lagna lord; Rahu/Ketu excluded.
FUNCTIONAL_BENEFICS_BY_LAGNA = {
    "Aries":       {"Sun", "Jupiter", "Mars"},
    "Taurus":      {"Sun", "Saturn", "Mercury", "Venus"},
    "Gemini":      {"Venus", "Mercury", "Saturn"},
    "Cancer":      {"Mars", "Jupiter", "Moon"},
    "Leo":         {"Mars", "Jupiter", "Sun"},
    "Virgo":       {"Venus", "Mercury"},
    "Libra":       {"Saturn", "Mercury", "Venus"},
    "Scorpio":     {"Jupiter", "Moon", "Sun"},
    "Sagittarius": {"Sun", "Mars", "Jupiter"},
    "Capricorn":   {"Venus", "Mercury", "Saturn"},
    "Aquarius":    {"Venus", "Sun", "Saturn"},
    "Pisces":      {"Moon", "Mars", "Jupiter"},
}


def _normalize_lagna(lagna_sign):
    """Capitalise to a single sign-name token; tolerate dict / dirty input."""
    if isinstance(lagna_sign, dict):
        lagna_sign = lagna_sign.get("sign") or lagna_sign.get("rashi") or ""
    if not isinstance(lagna_sign, str):
        return ""
    return lagna_sign.strip().capitalize()


def is_functional_benefic(planet: str, lagna_sign) -> bool:
    """True iff `planet` is a Parashari functional benefic for `lagna_sign`."""
    lg = _normalize_lagna(lagna_sign)
    if not lg or planet in ("Rahu", "Ketu"):
        return False
    return planet in FUNCTIONAL_BENEFICS_BY_LAGNA.get(lg, set())


def is_functional_malefic(planet: str, lagna_sign) -> bool:
    """True iff `planet` is a Parashari functional malefic for `lagna_sign`."""
    lg = _normalize_lagna(lagna_sign)
    if not lg:
        return False
    if planet in ("Rahu", "Ketu"):
        return True
    return planet in GEM_FUNCTIONAL_MALEFICS.get(lg, set())

# Internal life-domain notes for the narrator to translate (never to UI raw).
GEM_DOMAINS = {
    "Sun":     "leadership, visibility, vitality",
    "Moon":    "emotional steadiness, intuition, rest",
    "Mars":    "drive, courage, decisive action",
    "Mercury": "communication, commerce, learning",
    "Jupiter": "growth, wisdom, mentorship, fortune",
    "Venus":   "creativity, relationships, wealth, refinement",
    "Saturn":  "discipline, endurance, long-term structure",
    "Rahu":    "ambition, unconventional gains",
    "Ketu":    "insight, detachment, inner depth",
}

GEM_DOMAINS_ES = {
    "Sun":     "el liderazgo visible y la vitalidad",
    "Moon":    "la estabilidad emocional, la intuición y el descanso",
    "Mars":    "el impulso, el coraje y la acción decidida",
    "Mercury": "la comunicación, el comercio y el aprendizaje",
    "Jupiter": "el crecimiento, la sabiduría y la fortuna",
    "Venus":   "la creatividad, las relaciones y la riqueza que las sigue",
    "Saturn":  "la disciplina, la resistencia y la estructura a largo plazo",
    "Rahu":    "la ambición y las ganancias poco convencionales",
    "Ketu":    "la percepción y la profundidad interior",
}


def narrate_gem_why(planet: str, risk_tier: str = "safe", language: str = "en") -> str:
    """Plain-language gemstone line, narrated FROM the engine planet.
    NO planet name, NO Sanskrit, conclusions-not-calculations. Deterministic —
    same energy-translation narrator pattern as the other practice cards."""
    if str(language or "en").lower().startswith("es"):
        dom = GEM_DOMAINS_ES.get(planet, "tu fortaleza central")
        why = (f"Fortalece la parte de ti que gobierna {dom} — el motor de tus años "
               f"fuertes. Una sola piedra, elegida por la fortaleza central de tu "
               f"carta, usada para alimentarla.")
        if risk_tier == "test_first":
            why += (" Tómala primero como prueba: úsala poco tiempo y observa cómo "
                    "respondes antes de comprometerte.")
        return why
    dom = GEM_DOMAINS.get(planet, "your core strength")
    why = (f"Strengthens the part of you that governs {dom} — the engine of your "
           f"strong years. One stone, chosen for your chart's core strength, "
           f"worn to feed it.")
    if risk_tier == "test_first":
        why += (" Treat it as a trial first: wear it briefly and watch how you "
                "respond before committing.")
    return why


def _gem_lagna_sign(lagna):
    """Normalize lagna to a capitalized sign name ('Capricorn')."""
    if isinstance(lagna, dict):
        lagna = lagna.get("sign") or lagna.get("rashi") or ""
    if not isinstance(lagna, str):
        return ""
    lagna = lagna.strip().capitalize()
    return lagna if lagna in GEM_SIGN_LORDS else ""


def _gem_planet_sign(planets, planet):
    """Placement sign of a planet from the stored planets dict."""
    p = (planets or {}).get(planet)
    if isinstance(p, dict):
        return (p.get("sign") or p.get("rashi") or "").strip().capitalize()
    return ""


def _gem_dignity_rank(planet, sign):
    """5 exalted / 4 own / 3 friendly / 2 neutral / 1 debilitated.
    Friendly/neutral split mirrors antar_ephemeris._planet_strength."""
    if not sign:
        return 2
    if sign == GEM_EXALTATION.get(planet):
        return 5
    if sign == GEM_DEBILITATION.get(planet):
        return 1
    if sign in GEM_OWN_SIGNS.get(planet, []):
        return 4
    lord = GEM_SIGN_LORDS.get(sign, "")
    return 3 if lord in ("Jupiter", "Venus", "Moon") else 2


def select_chart_gemstone(planets, lagna):
    """ONE primary stone from the chart's ENGINE planet. Deterministic, no LLM.

    Engine-planet selection (in order):
      1. Yogakaraka, if the lagna has one.
      2. Lagna lord, only if it functions benefic AND is not debilitated.
      3. Strongest benefic-functioning kendra/trikona lord (dignity-ranked;
         trikona lordship breaks ties, then fixed planet order).
    Functional malefics for the lagna (and Rahu/Ketu) are never selected.

    Returns {stone, planet, risk_tier, metal, weekday, why} or None.
    INTERNAL — `planet` and `why` are for the narrator, never the UI.
    """
    lagna_sign = _gem_lagna_sign(lagna)
    if not lagna_sign:
        return None
    malefics = set(GEM_FUNCTIONAL_MALEFICS.get(lagna_sign, set())) | {"Rahu", "Ketu"}

    engine, basis = None, ""

    # 1. Yogakaraka
    yk = GEM_YOGAKARAKA_BY_LAGNA.get(lagna_sign)
    if yk and yk not in malefics:
        engine, basis = yk, "yogakaraka"

    # 2. Lagna lord (functions benefic by definition; skip if debilitated)
    if engine is None:
        ll = GEM_SIGN_LORDS.get(lagna_sign)
        if ll and ll not in malefics:
            if _gem_dignity_rank(ll, _gem_planet_sign(planets, ll)) > 1:
                engine, basis = ll, "lagna lord (functions benefic)"

    # 3. Strongest benefic-functioning kendra/trikona lord
    if engine is None:
        lagna_idx = GEM_SIGN_ORDER.index(lagna_sign)
        trikona_bonus = {9: 0.3, 5: 0.2, 1: 0.1}  # tie-break only
        fixed = ["Jupiter", "Venus", "Mercury", "Moon", "Sun", "Mars", "Saturn"]
        best, best_key = None, None
        for house in (1, 4, 5, 7, 9, 10):
            sign = GEM_SIGN_ORDER[(lagna_idx + house - 1) % 12]
            lord = GEM_SIGN_LORDS[sign]
            if lord in malefics:
                continue
            rank = _gem_dignity_rank(lord, _gem_planet_sign(planets, lord))
            key = (rank + trikona_bonus.get(house, 0.0),
                   -fixed.index(lord) if lord in fixed else -99)
            if best_key is None or key > best_key:
                best, best_key = lord, key
        if best:
            engine, basis = best, "strongest benefic kendra/trikona lord"

    if engine is None or engine not in GEM_BY_PLANET:
        return None

    g = GEM_BY_PLANET[engine]
    risk = "test_first" if engine in GEM_TEST_FIRST else "safe"
    # `why` is narrated plain language (no planet name, no Sanskrit). The
    # engine planet stays INTERNAL under `_planet` — narrate FROM it, never
    # expose it. why_es is a working field the endpoint swaps in for es and
    # drops from every response.
    return {
        "stone": g["stone"],
        "risk_tier": risk,
        "metal": g["metal"],
        "weekday": g["weekday"],
        "why": narrate_gem_why(engine, risk, "en"),
        "why_es": narrate_gem_why(engine, risk, "es"),
        "_planet": engine,
        "_basis": basis,
    }


def _score_planet_convergence(planets, karakas, current_dasha, varshphal, sleeping, masik_phal, age, vimsottari_md=None, vimsottari_ad=None, next_md=None):
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

        # Vimsottari Mahadasha lord — PRIMARY dasha system
        vim_md = vimsottari_md or {}
        if vim_md.get("planet_or_sign") == planet:
            score += 0.30
            # [class-b 2026-06-09] engine name removed from user-facing reasons.
            reasons.append("ruling your current major life chapter")

        # Vimsottari Antardasha lord — current sub-chapter
        vim_ad = vimsottari_ad or {}
        if vim_ad.get("planet_or_sign") == planet:
            score += 0.20
            reasons.append("active in your current sub-chapter")

        # Chapter transition bonus — MD ending within 6 months
        if vim_md.get("planet_or_sign") == planet:
            try:
                from datetime import datetime as _dt_vim, timedelta as _td_vim
                _md_end = _dt_vim.fromisoformat(vim_md.get("end_date", "")[:10])
                _months_left = (_md_end - _dt_vim.now()).days / 30
                if 0 < _months_left <= 6:
                    score += 0.15
                    reasons.append(f"chapter ending in {int(_months_left)} months — strengthen now")
            except Exception:
                pass

        # Next MD lord — new chapter starting within 6 months needs preparation
        _next_md = next_md or {}
        if _next_md.get("planet_or_sign") == planet:
            try:
                from datetime import datetime as _dt_nxt
                _md_start = _dt_nxt.fromisoformat(_next_md.get("start_date", "")[:10])
                _months_until = (_md_start - _dt_nxt.now()).days / 30
                if 0 < _months_until <= 6:
                    score += 0.20
                    reasons.append(f"new chapter starting in {int(_months_until)} months — prepare this energy")
            except Exception:
                pass

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
        frequency_hz=PLANET_FREQUENCIES_MAP.get(planet, 136.10),
        mantra_count=PLANET_COUNTS_MAP.get(planet, 11),
        # Practice meta — WHY + duration + counter
        practice_why=PLANET_PRACTICE_META.get(planet, {}).get(
            "why_india" if locale == "IN" else "why", ""
        ),
        practice_why_science=PLANET_PRACTICE_META.get(planet, {}).get("why_science", ""),
        duration_days=PLANET_PRACTICE_META.get(planet, {}).get("duration_days", 21),
        duration_label=PLANET_PRACTICE_META.get(planet, {}).get("duration_label", "21 days"),
        duration_reason=PLANET_PRACTICE_META.get(planet, {}).get("duration_reason", ""),
        best_day=PLANET_PRACTICE_META.get(planet, {}).get("best_day", ""),
        best_time=PLANET_PRACTICE_META.get(planet, {}).get("best_time", "morning"),
        completion_milestone=PLANET_PRACTICE_META.get(planet, {}).get("completion_milestone", ""),
        streak_type=PLANET_PRACTICE_META.get(planet, {}).get("streak_type", "daily"),
        is_ongoing=PLANET_PRACTICE_META.get(planet, {}).get("ongoing", False),
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
            frequency_hz=PLANET_FREQUENCIES_MAP.get(planet, 136.10),
            mantra_count=PLANET_COUNTS_MAP.get(planet, 11),
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
        frequency_hz=PLANET_FREQUENCIES_MAP.get(planet, 136.10),
        # Mantra meta — WHY + duration
        mantra_why=PLANET_PRACTICE_META.get(planet, {}).get(
            "why_india" if locale == "IN" else "why", ""
        ),
        mantra_duration_days=PLANET_PRACTICE_META.get(planet, {}).get("duration_days", 21),
        mantra_duration_label=PLANET_PRACTICE_META.get(planet, {}).get("duration_label", "21 days"),
        mantra_duration_reason=PLANET_PRACTICE_META.get(planet, {}).get("duration_reason", ""),
        mantra_best_time=PLANET_PRACTICE_META.get(planet, {}).get("best_time", "morning"),
        mantra_completion_milestone=PLANET_PRACTICE_META.get(planet, {}).get("completion_milestone", ""),
        mantra_streak_type=PLANET_PRACTICE_META.get(planet, {}).get("streak_type", "daily"),
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
            remedy_why=f"Your {info['label']} energy is currently dormant in your chart. This means opportunities in this area pass by unnoticed — not because they don't exist, but because the channel to receive them is blocked. This practice activates the channel.",
            remedy_why_science="Consistent behavioral repetition in a specific domain (service, gratitude, creativity) activates neural pathways associated with that domain — literally making your brain more receptive to related opportunities.",
            duration_days=REMEDY_DURATION_RULES["sleeping_planet"]["duration_days"],
            duration_label=REMEDY_DURATION_RULES["sleeping_planet"]["duration_label"],
            duration_reason=REMEDY_DURATION_RULES["sleeping_planet"]["reason"],
            streak_warning="Consistency matters. Skipping days slows the activation process.",
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
            remedy_why="A repeating pattern has been detected in this area of your life — the same situation keeps showing up in different forms. This isn't bad luck. It's a signal that a particular response pattern needs to change. This practice is the counter-pattern.",
            remedy_why_science="Repeating life patterns often trace to unconscious behavioral loops — responses that once protected you but now create the exact problems you're trying to avoid. Consistent counter-behavior for 40 days interrupts the loop at the neurological level.",
            duration_days=REMEDY_DURATION_RULES["rin_clearing"]["duration_days"],
            duration_label=REMEDY_DURATION_RULES["rin_clearing"]["duration_label"],
            duration_reason=REMEDY_DURATION_RULES["rin_clearing"]["reason"],
            streak_warning=REMEDY_DURATION_RULES["rin_clearing"]["warning"],
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


def _build_chakra_map(karakas, sleeping, convergence, practice_counts=None, moon_nakshatra=None):
    """Map Jaimini Karakas to Chakras with status. Falls back to default map when karakas empty."""
    # Nakshatra group baseline adjustments
    _chakra_baselines = {}
    if moon_nakshatra:
        try:
            from antar_engine.nakshatra_groups import get_nakshatra_group, get_chakra_group_baseline
            _nak_group = get_nakshatra_group(moon_nakshatra)
            _chakra_baselines = get_chakra_group_baseline(_nak_group)
        except Exception:
            _chakra_baselines = {}

    chakra_list = []
    sleeping_planets = [s.get("planet") for s in (sleeping or [])]

    # FALLBACK: If no karakas (jaimini_data missing), build default from natal planets
    if not karakas or len(karakas) == 0:
        default_karaka_map = [
            {"karaka": "AK", "planet": "Sun"},
            {"karaka": "AmK", "planet": "Moon"},
            {"karaka": "BK", "planet": "Mars"},
            {"karaka": "MK", "planet": "Mercury"},
            {"karaka": "PK", "planet": "Jupiter"},
            {"karaka": "GK", "planet": "Venus"},
            {"karaka": "DK", "planet": "Saturn"},
        ]
        karakas = default_karaka_map

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

        # Practice completion boost: +2% per completed day in last 30 days (cap +30%)
        _pc = (practice_counts or {}).get(planet, 0)
        _practice_boost = min(_pc * 2, 30)
        completion = completion + _practice_boost

        # Nakshatra group baseline adjustment
        _c_name = chakra_info["chakra"].split("(")[-1].rstrip(")") if "(" in chakra_info["chakra"] else chakra_info["chakra"]
        _baseline_adj = _chakra_baselines.get(_c_name, 0)
        completion = max(0, min(100, completion + _baseline_adj))

        # Status can UPGRADE based on boosted completion
        if completion >= 70 and status != "Flowing":
            status = "Flowing"
        elif completion >= 40 and status == "Dormant":
            status = "Stressed"

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
    """Extract planet positions from chart_data or lal_kitab_data JSONB."""
    if not chart_data:
        return {}
    if isinstance(chart_data, str): chart_data = _safe_json(chart_data)
    p = chart_data.get("planets", chart_data.get("planet_positions", {}))
    if p:
        return p
    np = chart_data.get("natal_planets", {})
    if np:
        return np
    return {}


def _extract_lagna(chart_data):
    if not chart_data:
        return "Aries"
    if isinstance(chart_data, str): chart_data = _safe_json(chart_data)
    return chart_data.get("lagna", chart_data.get("lagna_sign", chart_data.get("ascendant", {}).get("sign", "Aries")))


def _extract_karakas(jaimini_data):
    if not jaimini_data:
        return []
    karakas = (
        jaimini_data.get("karakas") or
        jaimini_data.get("chara_karakas") or
        jaimini_data.get("karaka_assignments") or
        []
    )
    # Normalize: if it's a dict (key=karaka, val=planet or dict), convert to list format
    if isinstance(karakas, dict):
        _norm_list = []
        for k, v in karakas.items():
            planet = v.get("planet") if isinstance(v, dict) else str(v) if v else None
            if planet:
                _norm_list.append({"karaka": k, "planet": planet})
        karakas = _norm_list
    # Normalize: values inside list entries may be dicts like {"planet": "Mars"}
    if karakas and isinstance(karakas, list) and len(karakas) > 0:
        if isinstance(karakas[0], dict) and "planet" in karakas[0]:
            pass  # already correct format
        elif isinstance(karakas[0], dict):
            # Try to normalize unknown dict shape
            _norm_list = []
            for entry in karakas:
                planet = entry.get("planet") or entry.get("name") or None
                karaka = entry.get("karaka") or entry.get("role") or ""
                if planet:
                    _norm_list.append({"karaka": karaka, "planet": planet})
            karakas = _norm_list
    return karakas


def _extract_current_dasha(jaimini_data):
    """Extract current Mahadasha. Structure: {current_md: {lord, sign_name, ...}}"""
    if not jaimini_data:
        return None
    if isinstance(jaimini_data, str): jaimini_data = _safe_json(jaimini_data)
    if isinstance(jaimini_data, list):
        return None
    md = jaimini_data.get("current_md")
    if md and isinstance(md, dict):
        return md
    dashas = jaimini_data.get("chara_dasha", jaimini_data.get("dasha_periods", []))
    for d in dashas:
        if d.get("active") or d.get("is_current"):
            return d
    return dashas[0] if dashas else None


def _extract_varshphal(lk_data):
    """Compute varshphal from stored placements if not pre-computed."""
    if not lk_data:
        return None
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    if isinstance(lk_data, list): return None
    v = (
        lk_data.get("varshphal") or
        lk_data.get("varshphal_data") or
        (lk_data.get("advanced") or {}).get("varshphal") or
        lk_data.get("current_varshphal")
    )
    if v:
        # Also normalize year_lord lookup
        if isinstance(v, dict) and not v.get("year_lord"):
            v["year_lord"] = (
                v.get("lord") or
                v.get("year_planet") or
                lk_data.get("year_lord") or
                None
            )
        return v
    placements = lk_data.get("placements", {})
    if not placements:
        return None
    year_lord = None
    annual_placements = {}
    for planet, lk_house in placements.items():
        annual_placements[planet] = lk_house
        if lk_house == 1:
            year_lord = planet
    if not year_lord:
        for planet, lk_house in placements.items():
            if lk_house == 10:
                year_lord = planet
                break
    return {"year_lord": year_lord, "annual_placements": annual_placements}


def _extract_sleeping_planets(lk_data):
    """Compute sleeping planets from LK placements. Sleeping = in dusthana (6,8,12)."""
    if not lk_data:
        return []
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    if isinstance(lk_data, list): return []
    sp = (
        (lk_data.get("advanced") or lk_data).get("sleeping_planets") or
        lk_data.get("sleeping") or
        (lk_data.get("advanced") or {}).get("sleeping_planets") or
        (lk_data.get("advanced") or {}).get("sleeping") or
        []
    )
    # Normalize: some entries are strings not dicts
    if sp and isinstance(sp[0], str):
        sp = [{"planet": p, "house": 0, "effect": "blocked"} for p in sp]
    if sp:
        return sp
    placements = lk_data.get("placements", {})
    if not placements:
        return []
    DUSTHANA = {6, 8, 12}
    BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
    benefic_houses = set()
    for planet, house in placements.items():
        if planet in BENEFICS:
            benefic_houses.add(house)
    sleeping = []
    for planet, house in placements.items():
        if house in DUSTHANA:
            has_support = house in benefic_houses and planet not in BENEFICS
            if not has_support:
                sleeping.append({"planet": planet, "house": house, "reason": f"In LK house {house} with no benefic support"})
    return sleeping


def _extract_rin(lk_data):
    """Compute Rin (karmic debts) from LK placements."""
    if not lk_data:
        return []
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    if isinstance(lk_data, list): return []
    r = (
        (lk_data.get("advanced") or lk_data).get("rin_debts") or
        lk_data.get("rin") or
        (lk_data.get("advanced") or {}).get("rin_debts") or
        (lk_data.get("advanced") or {}).get("rin") or
        (lk_data.get("advanced") or {}).get("karmic_debts") or
        []
    )
    if r:
        return r
    placements = lk_data.get("placements", {})
    if not placements:
        return []
    debts = []
    RIN_RULES = [
        ("Sun", {6, 12}, "father_debt"),
        ("Moon", {6, 8, 12}, "mother_debt"),
        ("Jupiter", {6, 8, 12}, "guru_debt"),
        ("Venus", {6, 8}, "spouse_debt"),
        ("Saturn", {1, 8}, "self_debt"),
    ]
    for planet, bad_houses, debt_type in RIN_RULES:
        lk_house = placements.get(planet)
        if lk_house and lk_house in bad_houses:
            debts.append({"type": debt_type, "planet": planet, "house": lk_house})
    return debts


def _extract_enemy_houses(lk_data):
    if not lk_data:
        return []
    return lk_data.get("enemy_houses", [])


def _extract_masik_phal(lk_data):
    """Extract or compute monthly activation from LK data."""
    if not lk_data:
        return None
    if isinstance(lk_data, str): lk_data = _safe_json(lk_data)
    if isinstance(lk_data, list): return None
    mp = lk_data.get("masik_phal", lk_data.get("monthly"))
    if mp:
        return mp
    placements = lk_data.get("placements", {})
    if not placements:
        return None
    month = date.today().month
    active_planet = None
    for planet, house in placements.items():
        if house == month or house == (month % 12) + 1:
            active_planet = planet
            break
    if active_planet:
        return {"active_planet": active_planet, "month": date.today().strftime("%B")}
    return None


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
    # Ramandeep's ACTUAL data from Supabase
    test_chart = {"natal_planets": {"Sun": {"sign": "Scorpio", "house": 11}, "Moon": {"sign": "Pisces", "house": 3}, "Mars": {"sign": "Libra", "house": 10}, "Saturn": {"sign": "Gemini", "house": 6}, "Jupiter": {"sign": "Aquarius", "house": 2}, "Venus": {"sign": "Scorpio", "house": 11}, "Mercury": {"sign": "Libra", "house": 10}, "Rahu": {"sign": "Scorpio", "house": 11}, "Ketu": {"sign": "Taurus", "house": 5}}, "lagna_sign": "Capricorn"}
    test_jaimini = {"karakas": [{"karaka": "AK", "planet": "Sun"}, {"karaka": "AmK", "planet": "Moon"}, {"karaka": "BK", "planet": "Mars"}, {"karaka": "MK", "planet": "Mercury"}, {"karaka": "PK", "planet": "Jupiter"}, {"karaka": "GK", "planet": "Venus"}, {"karaka": "DK", "planet": "Saturn"}], "current_md": {"lord": "Venus", "sign_name": "Taurus"}, "current_ad": {"lord": "Mercury", "sign_name": "Virgo"}}
    test_lk = {"placements": {"Sun": 8, "Ketu": 11, "Mars": 6, "Moon": 4, "Rahu": 8, "Venus": 8, "Saturn": 7, "Jupiter": 9, "Mercury": 6}, "natal_planets": {"Sun": {"sign": "Scorpio", "house": 11}}, "age": 51, "lagna_sign": "Capricorn"}

    result = generate_practice_schedule(
        chart_data=test_chart,
        jaimini_data=test_jaimini,
        lal_kitab_data=test_lk,
        current_country="US",
        birth_date="1974-11-26",
    )

    print(json.dumps(result, indent=2, default=str))
