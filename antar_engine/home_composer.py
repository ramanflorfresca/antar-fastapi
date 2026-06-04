"""
antar_engine/home_composer.py

Home endpoint composition — assembles four HorizonView blocks
(today / month / year / cycle) per HOME_API_Contract.md.

Thin orchestration only. No LLM calls. Reuses:
  - lal_kitab_masik   (masik phal house math + PLANET_NATURE + HOUSE_THEMES)
  - muhurta_engine    (best/avoid time windows for "today")
  - dasha_periods     (current MD/AD — looked up in main.py, passed in)

Polarity rule (per contract):
  positive  →  "use" set, chain (cause/remedy/chakra/practice) all None
  negative  →  "use" None, chain populated
The composer enforces this XOR — engines never decide it directly.
"""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any

from antar_engine.lal_kitab_masik import (
    HOUSE_THEMES, PLANET_NATURE, POWERFUL_HOUSES, DIFFICULT_HOUSES,
    _months_since_birthday,
)


# ── Static maps (English source; @translate_response translates at response time) ──

ENERGY_LANG = {
    "Sun":     "your authority and self-direction",
    "Moon":    "your emotional steadiness",
    "Mars":    "your drive and ability to act",
    "Mercury": "your clarity of thought and speech",
    "Jupiter": "your sense of meaning and growth",
    "Venus":   "your relationships and harmony",
    "Saturn":  "your discipline and patience",
    "Rahu":    "your ambition and focus",
    "Ketu":    "your detachment and inner stillness",
}

# Planet → chakra (mirrors chakra_engine PLANET_CHAKRAS primary)
PLANET_TO_CHAKRA = {
    "Sun":     {"name": "Solar Plexus", "governs": "Confidence, will, personal power"},
    "Moon":    {"name": "Sacral",       "governs": "Feeling, flow, emotional balance"},
    "Mars":    {"name": "Root",         "governs": "Stability, action, survival drive"},
    "Mercury": {"name": "Throat",       "governs": "Voice, clarity, honest expression"},
    "Jupiter": {"name": "Crown",        "governs": "Wisdom, meaning, big-picture sight"},
    "Venus":   {"name": "Heart",        "governs": "Love, harmony, connection"},
    "Saturn":  {"name": "Root",         "governs": "Foundations, discipline, time"},
    "Rahu":    {"name": "Third Eye",    "governs": "Intuition, vision, perception"},
    "Ketu":    {"name": "Crown",        "governs": "Letting go, inner stillness"},
}

# Mantra seed — allowed jargon per contract (mantra seed in practice.name)
MANTRA_SEED = {
    "Sun": "RAM", "Moon": "VAM", "Mars": "LAM", "Mercury": "HAM",
    "Jupiter": "OM", "Venus": "YAM", "Saturn": "LAM",
    "Rahu": "SHAM", "Ketu": "OM",
}

PRACTICE_BY_PLANET = {
    "Sun":     ("Solar Plexus Breath · RAM", 5,
                ["Sit upright with hands on belly",
                 "Inhale 4 counts into the upper belly",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper RAM",
                 "Repeat for 5 minutes"]),
    "Moon":    ("Sacral Breath · VAM", 5,
                ["Sit comfortably, hands on lower belly",
                 "Inhale 4 counts, feel the belly soften",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper VAM",
                 "Repeat for 5 minutes"]),
    "Mars":    ("Root Breath · LAM", 5,
                ["Sit grounded, both feet flat",
                 "Inhale 4 counts, feel feet press down",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper LAM",
                 "Repeat for 5 minutes"]),
    "Mercury": ("Throat Breath · HAM", 5,
                ["Sit tall, chin slightly tucked",
                 "Inhale 4 counts",
                 "Hold 7 counts",
                 "Exhale 8 counts, whisper HAM",
                 "Repeat for 5 minutes"]),
    "Jupiter": ("Crown Breath · OM", 5,
                ["Sit tall, eyes soft",
                 "Inhale 5 counts",
                 "Hold 5 counts",
                 "Exhale 7 counts, whisper OM",
                 "Repeat for 5 minutes"]),
    "Venus":   ("Heart Breath · YAM", 5,
                ["Sit with one hand on the heart",
                 "Inhale 4 counts into the chest",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper YAM",
                 "Repeat for 5 minutes"]),
    "Saturn":  ("Root Breath · LAM", 7,
                ["Sit grounded, feet flat",
                 "Inhale slowly for 5 counts",
                 "Hold 5 counts",
                 "Exhale 7 counts, whisper LAM",
                 "Repeat for 7 minutes"]),
    "Rahu":    ("Third Eye Breath · SHAM", 5,
                ["Sit upright, eyes closed",
                 "Inhale 4 counts, attention between brows",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper SHAM",
                 "Repeat for 5 minutes"]),
    "Ketu":    ("Crown Breath · OM", 5,
                ["Sit tall, hands resting upward",
                 "Inhale 5 counts",
                 "Hold 5 counts",
                 "Exhale 7 counts, whisper OM",
                 "Repeat for 5 minutes"]),
}

PLANET_DO = {
    "Sun":     "Lead from your own initiative. Make one decision that is yours alone.",
    "Moon":    "Take care of your inner world. Rest, eat well, soft conversations.",
    "Mars":    "Channel energy into one physical task and finish it.",
    "Mercury": "Use the clear head for planning and solo work. Confirm details in writing.",
    "Jupiter": "Reach out to a mentor or share what you have learned with someone.",
    "Venus":   "Invest in a relationship — small, warm, in person.",
    "Saturn":  "Do the slow, structural work that has been waiting.",
    "Rahu":    "Set one ambitious target for the week and break it into a single first step.",
    "Ketu":    "Make space — declutter a corner, drop one obligation, sit quietly.",
}
PLANET_DONT = {
    "Sun":     "Do not wait for permission you do not actually need.",
    "Moon":    "Do not make big choices when feelings are running high.",
    "Mars":    "Do not pick a fight to release pressure.",
    "Mercury": "Do not start big conversations or sign commitments.",
    "Jupiter": "Do not over-promise or over-explain.",
    "Venus":   "Do not smooth over something that actually needs a hard conversation.",
    "Saturn":  "Do not push faster than the work allows. No shortcuts today.",
    "Rahu":    "Do not chase a new shiny goal before finishing what is open.",
    "Ketu":    "Do not drift. Pick one anchor for the day before letting go.",
}

# Short plain-English phrase per AD planet — used to express the MD->AD
# sub-chapter in the Cycle horizon. Replaced by real LK interpretation in
# Phase 2. No planet names leak: the planet is mapped to an energy theme.
AD_PLANET_THEMES = {
    "Sun":     "self & visibility",
    "Moon":    "feeling & nurturing",
    "Mars":    "energy & action",
    "Mercury": "communication & exchange",
    "Jupiter": "growth & meaning",
    "Venus":   "connection & comfort",
    "Saturn":  "discipline & structure",
    "Rahu":    "ambition & the unfamiliar",
    "Ketu":    "release & inward turn",
}

PLANET_AREAS = {
    "Sun":     ["Identity", "Career"],
    "Moon":    ["Family", "Wellbeing"],
    "Mars":    ["Action", "Health"],
    "Mercury": ["Focus", "Communication"],
    "Jupiter": ["Growth", "Learning"],
    "Venus":   ["People", "Relationships"],
    "Saturn":  ["Work", "Discipline"],
    "Rahu":    ["Ambition", "Career"],
    "Ketu":    ["Inner Life", "Letting Go"],
}

WEEKDAY_EN = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
MONTH_EN   = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
MONTH_FULL = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]

CYCLE_INFO = (
    "A phase of life where a planet's influence shapes your path. "
    "Each cycle lasts years, then changes."
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _safe_json(v: Any) -> dict:
    """Mirror of main.py _safe_jsonb — chart_data/lal_kitab_data may be a
    JSON string instead of native JSONB."""
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    if isinstance(v, dict):
        return v
    return {}


def _now_local(tz_offset_min: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=int(tz_offset_min or 0))


def _format_today_range(now: datetime) -> str:
    return f"{WEEKDAY_EN[now.weekday()]} · {MONTH_EN[now.month - 1]} {now.day}"


def _format_month_range(now: datetime) -> str:
    return f"{MONTH_FULL[now.month - 1].upper()} {now.year}"


def _format_year_range(birth_date: str, now: datetime) -> str:
    try:
        born = date.fromisoformat((birth_date or "")[:10])
        age = (now.date() - born).days // 365
        return f"YEAR {age + 1}"
    except Exception:
        return f"{now.year}"


def _format_cycle_range(md_row: Optional[dict]) -> str:
    if not md_row:
        return ""
    try:
        sd = date.fromisoformat(str(md_row.get("start_date", ""))[:10])
        ed = date.fromisoformat(str(md_row.get("end_date", ""))[:10])
        return f"{MONTH_EN[sd.month - 1]} {sd.year} – {MONTH_EN[ed.month - 1]} {ed.year}"
    except Exception:
        return ""


def _natal_houses(chart_data: dict) -> dict:
    """Extract {planet: house} from chart_data. Handles both dict and list shapes."""
    planets = chart_data.get("planets") or chart_data.get("planet_positions") or {}
    if isinstance(planets, dict):
        return {
            p: int(d.get("house") or 0)
            for p, d in planets.items()
            if isinstance(d, dict)
        }
    if isinstance(planets, list):
        out = {}
        for p in planets:
            if isinstance(p, dict):
                nm = p.get("name") or p.get("planet")
                if nm:
                    out[nm] = int(p.get("house") or 0)
        return out
    return {}


def _running_year(birth_date: str) -> int:
    try:
        born = date.fromisoformat((birth_date or "")[:10])
        age = (date.today() - born).days // 365
        return max(1, min(120, age + 1))
    except Exception:
        return 1


def _varshphal_placements(birth_date: str, natal_houses: dict) -> dict:
    ry = _running_year(birth_date)
    return {
        p: ((h - 1 + (ry - 1)) % 12) + 1
        for p, h in natal_houses.items()
        if 1 <= (h or 0) <= 12
    }


def _masik_placements(birth_date: str, natal_houses: dict) -> dict:
    varsh = _varshphal_placements(birth_date, natal_houses)
    off = _months_since_birthday(birth_date)
    return {p: ((h - 1 + off) % 12) + 1 for p, h in varsh.items()}


def _classify(placements: dict) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
    strong = [(p, h) for p, h in placements.items() if h in POWERFUL_HOUSES]
    weak   = [(p, h) for p, h in placements.items() if h in DIFFICULT_HOUSES]
    weak.sort(key=lambda x: x[1])
    strong.sort(key=lambda x: -x[1])
    return strong, weak


def _resolve_polarity(strong: list, weak: list) -> str:
    if len(weak) > len(strong):
        return "negative"
    return "positive"


def _dominant_weak_planet(weak: list, current_md: str = "") -> Optional[str]:
    if not weak:
        return None
    if current_md:
        for p, _ in weak:
            if p.lower() == current_md.lower():
                return p
    return weak[0][0]


def _dominant_strong_planet(strong: list, current_md: str = "") -> Optional[str]:
    if not strong:
        return None
    if current_md:
        for p, _ in strong:
            if p.lower() == current_md.lower():
                return p
    return strong[0][0]


# ── Common chain (positive vs negative) ─────────────────────────────────────

CAUSE_TEXT = {
    "Sun":     "Your self-direction feels uncertain — outside noise is louder than your own signal.",
    "Moon":    "Your emotional steadiness is unsettled — small things land harder than usual.",
    "Mars":    "Your drive feels blocked — starts and finishes are harder.",
    "Mercury": "Your thinking is scattered — timing and details feel slippery.",
    "Jupiter": "Your sense of meaning feels far away — motivation is thin.",
    "Venus":   "Your connections feel strained — warmth needs effort.",
    "Saturn":  "Your patience is being tested — progress feels slow.",
    "Rahu":    "Your focus is pulled in too many directions — decide what matters.",
    "Ketu":    "You feel adrift — small anchors will help.",
}
REMEDY_TEXT = {
    "Sun":     "Pick one decision and own it before the day ends.",
    "Moon":    "Protect sleep and quiet time tonight. Eat warm food.",
    "Mars":    "Move your body for ten minutes before any difficult task.",
    "Mercury": "Slow down. Confirm anything important in writing.",
    "Jupiter": "Read something nourishing for ten minutes. Skip the doom-scroll.",
    "Venus":   "Send one warm message to someone you care about.",
    "Saturn":  "Choose one boring foundational task and complete it fully.",
    "Rahu":    "Close three open tabs — literal or mental.",
    "Ketu":    "Pick one anchor (a meal, a walk, a person) and show up to it.",
}


# ── Curated Upaay Library (single, locale-independent) ───────────────────────
# Replaces the IN/GLOBAL locale fork for Home surfaces. Each row keeps the
# verbatim source string in `traditional_original` (retained for a future
# "advanced traditional" toggle, NOT emitted) and the universalised `curated`
# string (emitted). Every curated string is authored strip-safe under
# field_type='timing': it keeps its day-of-week and contains no planet/deity
# names. Founder-approved 2026-05-30.
UPAAY_LIBRARY = {'Sun': {'day': 'Sunday',
         'primary': {'traditional_original': 'Offer water to the Sun every morning. Donate wheat '
                                             'on Sundays.',
                     'curated': 'On Sunday morning, stand outside facing the sunrise and pour a '
                                'small cup of clean water onto the earth. During the week, give a '
                                'portion of wheat, whole grain, or golden food (bread, honey, '
                                'fresh fruit) to someone older than you.'},
         'awakening': {'traditional_original': 'Offer water to Sun daily at sunrise for 43 days',
                       'curated': 'For 7 weeks, on each Sunday at sunrise, offer water to the '
                                  'rising sunlight by pouring it slowly onto the earth or into a '
                                  'flowing stream while facing east. On the first Sunday, also '
                                  'place a small piece of copper or red-toned metal into running '
                                  'water.'},
         'rin_clearing': {'traditional_original': 'Offer water to the Sun for 43 days. Respect '
                                                  'father figures.',
                          'curated': 'For 7 weeks, on each Sunday morning, offer water to the '
                                     'rising sunlight by pouring it onto earth at sunrise. During '
                                     'those weeks, find one specific way to honor your father, a '
                                     "father-figure, or any older man you've been at odds with — "
                                     'speak respectfully to him, ask his advice, give him '
                                     'something useful.'}},
 'Moon': {'day': 'Monday',
          'primary': {'traditional_original': 'Offer milk to a Shiva temple on Monday. Keep silver '
                                              'with you.',
                      'curated': 'On Monday evening, pour a small amount of milk onto the roots of '
                                 'a tree or into flowing water. Carry a small silver object — a '
                                 'coin, a ring, a thin chain — somewhere on your person through '
                                 'the week. Keep fresh white flowers in the room where you sleep.'},
          'awakening': {'traditional_original': 'Offer milk to Shiva on Mondays. Keep silver '
                                                'article.',
                        'curated': 'For 4 weeks, on each Monday evening, pour a small amount of '
                                   'milk onto the roots of a living tree or into a stream. Keep a '
                                   'small silver object on you continuously through those 4 weeks '
                                   '— only remove it to bathe.'},
          'rin_clearing': {'traditional_original': 'Offer milk on Monday. Serve your mother or a '
                                                   'mother figure.',
                           'curated': 'On Monday evening, pour milk onto the roots of a tree. That '
                                      'same week, do one tangible act of service for your mother, '
                                      'a mother-figure, or any woman who has cared for you — cook '
                                      'a meal for her, help with her errands, sit and listen to '
                                      'her without your phone.'}},
 'Mars': {'day': 'Tuesday',
          'primary': {'traditional_original': 'Donate red lentils on Tuesday. Carry a copper coin.',
                      'curated': 'On Tuesday, give away something red and edible — red lentils, '
                                 'red apples, a pomegranate, tomatoes — to someone who needs it. '
                                 'Carry a small piece of copper (a coin, a wire ring, a small '
                                 'charm) in your pocket through the week. Give a piece of sweet '
                                 'bread to a dog if one is near you.'},
          'awakening': {'traditional_original': 'Visit Hanuman temple on Tuesdays. Donate blood '
                                                'once.',
                        'curated': 'For 6 weeks, on each Tuesday, give away red food (lentils, '
                                   'fruit, tomatoes) to someone who needs it, and carry a copper '
                                   'object through the week.'},
          'rin_clearing': {'traditional_original': '',
                           'curated': 'For 6 weeks, on each Tuesday morning, recite or write out '
                                      'one acknowledgment of a moment where your anger caused harm '
                                      '— to someone you spoke harshly to, someone you cut off, '
                                      "someone you fought with. You don't have to send it. Then "
                                      'give away something red and edible to someone in need. The '
                                      'act clears the anger-debt this cycle has been carrying.'}},
 'Mercury': {'day': 'Wednesday',
             'primary': {'traditional_original': 'Feed green vegetables to a cow on Wednesday. '
                                                 'Donate to an education cause.',
                         'curated': 'On Wednesday, give fresh green leaves or vegetables to a '
                                    'four-legged animal — a cow, a goat, a horse — or feed green '
                                    'moong (whole green mung beans) to birds. That same week, give '
                                    "money or time to an education cause: a school, a teacher's "
                                    "classroom fund, a child's tuition, a book donation."},
             'awakening': {'traditional_original': 'Donate books to students. Feed green grass to '
                                                   'cow.',
                           'curated': 'For 7 weeks, on each Wednesday, feed green moong or fresh '
                                      'green plant matter to birds or a four-legged animal. Once '
                                      'during these 7 weeks, donate at least one book to a '
                                      'student, library, or learning space.'},
             'rin_clearing': {'traditional_original': '',
                              'curated': 'For 7 weeks, on each Wednesday, write one truthful '
                                         "message you've been avoiding — an apology for a lie, a "
                                         'clarification you owe, a half-finished promise — and '
                                         'send at least one. That same Wednesday, give green food '
                                         'to an animal or a bird. The act clears the speech-debt '
                                         'this cycle has been carrying.'}},
 'Jupiter': {'day': 'Thursday',
             'primary': {'traditional_original': 'Donate yellow sweets on Thursday. Touch the feet '
                                                 'of an elder or teacher.',
                         'curated': 'On Thursday, give a yellow-toned gift — sweets, turmeric, a '
                                    "yellow flower, a book, money for someone's education — to a "
                                    'teacher, mentor, healer, or any elder whose wisdom you '
                                    'respect. On Thursday morning, place a small mark of turmeric '
                                    'or a yellow pigment on your forehead, between the brows.'},
             'awakening': {'traditional_original': 'Donate yellow sweets on Thursdays. Respect '
                                                   'teachers.',
                           'curated': 'For 7 weeks, on each Thursday, give something yellow '
                                      '(sweets, turmeric, a flower, a book) to a teacher, mentor, '
                                      'or elder. Wear something yellow on those Thursdays. By the '
                                      "seventh Thursday, write down one thing you've learned from "
                                      'any of these elders during the cycle.'},
             'rin_clearing': {'traditional_original': 'Donate yellow items on Thursday. Touch the '
                                                      'feet of a teacher. Visit a temple.',
                              'curated': 'For 7 weeks, on each Thursday, give a yellow gift to a '
                                         'teacher or mentor — past or present. Once during these 7 '
                                         'weeks, return to a teacher who shaped you and either '
                                         'thank them in writing, visit them, or send them a gift. '
                                         'If they are no longer alive, leave the gift at a place '
                                         'of learning in their name (a library, school, or '
                                         'classroom).'}},
 'Venus': {'day': 'Friday',
           'primary': {'traditional_original': 'Donate white clothes to a woman on Friday. Offer '
                                               'white flowers.',
                       'curated': 'On Friday, give a soft white gift — white clothes, white '
                                  'flowers, silk, cream, white sweets — to a woman who is not '
                                  'family (a friend, colleague, someone you meet kindly). That '
                                  'same Friday, scatter a small handful of uncooked rice mixed '
                                  'with sugar near an anthill, a garden bed, or any patch of earth '
                                  'where small creatures gather.'},
           'awakening': {'traditional_original': 'Gift wife white clothes. Donate on Fridays.',
                         'curated': 'For 6 weeks, on each Friday, give a small white or soft gift '
                                    'to a woman who matters to you — a partner, mother, sister, '
                                    'friend, daughter. If your situation makes that hard, give a '
                                    'small luxury to yourself that brings comfort (self-comfort '
                                    'and pleasure count here too). The pattern is what counts: 6 '
                                    'Fridays of gentle generosity.'},
           'rin_clearing': {'traditional_original': 'Donate white items on Friday. Serve your '
                                                    'partner with respect.',
                            'curated': 'For 6 weeks, on each Friday, do one tangible act of care '
                                       'for your partner — cook for them, clean something they '
                                       'normally clean, give them an hour of your full presence '
                                       'without phone or distraction. Give a white gift to them or '
                                       'to a woman in your life on the first and last Friday of '
                                       'the cycle.'}},
 'Saturn': {'day': 'Saturday',
            'primary': {'traditional_original': 'Donate mustard oil on Saturday. Serve food to '
                                                'workers.',
                        'curated': 'On Saturday, give a dark-toned, practical gift — oil, black '
                                   'sesame seeds, dark cloth, coffee, dark chocolate, money — to '
                                   'someone who labors in service (a cleaner, delivery worker, '
                                   'security guard, gardener, anyone whose work is repetitive and '
                                   'undervalued). On Saturday afternoon, place a small piece of '
                                   'iron (a nail, an old key, a horseshoe nail) at the base of a '
                                   'tree and leave it there.'},
            'awakening': {'traditional_original': 'Serve workers and poor on Saturdays. Donate '
                                                  'oil.',
                          'curated': 'For 7 weeks, on each Saturday afternoon, give something '
                                     'tangible — food, money, warm clothing, oil, coffee — to a '
                                     'worker who serves and is rarely thanked. On the first '
                                     "Saturday, place a small piece of iron at a tree's base and "
                                     'leave it there for the full 7 weeks.'},
            'rin_clearing': {'traditional_original': '',
                             'curated': 'For 7 weeks, on each Saturday morning, do one piece of '
                                        "work you've been avoiding — the boring task, the call you "
                                        "owe, the form that's been waiting, the apology that needs "
                                        'writing. Do not do it for praise or recognition. You may '
                                        'tell one accountability partner (a therapist, coach, or '
                                        'trusted friend) that you are doing the practice, but do '
                                        'not seek their validation for completing it. On Saturday '
                                        'afternoon, give a dark-toned gift (oil, coffee, money) to '
                                        'a worker. The act clears the labor-debt that accrues — '
                                        'work avoided becomes work owed.'}},
 'Rahu': {'day': 'Saturday',
          'primary': {'traditional_original': 'Donate blue clothes to a sweeper. Keep silver '
                                              'square piece.',
                      'curated': 'On Saturday, give a dark blue or grey gift (clothes, a blanket, '
                                 'money) to a cleaner, sweeper, or anyone whose work removes dirt '
                                 'and disorder from public spaces. Keep a small square piece of '
                                 'silver in your wallet or on your desk. On Saturday at sunset, '
                                 'release a piece of charcoal, ash, or burnt wood into flowing '
                                 'water — a stream, river, drain, or running tap — and as it goes, '
                                 'name aloud one obsession or anxious loop you want to release.'},
          'awakening': {'traditional_original': 'Feed crows. Keep elephant figurine. Donate on '
                                                'Saturdays.',
                        'curated': 'For 6 weeks, on each Saturday, scatter food (bread, grain, '
                                   'leftover rice) for crows or any black birds in your area. Keep '
                                   'a small figure or image of an elephant, or a sandalwood '
                                   "object, somewhere you'll see it daily. On Saturdays, give a "
                                   'blue or grey gift to a cleaner or sweeper.'},
          'rin_clearing': {'traditional_original': '',
                           'curated': 'For 6 weeks, on each Saturday at sunset, write down one '
                                      'obsession, fantasy, or fear that has been running your mind '
                                      'on repeat — then burn the paper or release it into flowing '
                                      'water. Tell no one. The act clears the shadow-debt of '
                                      'obsession — what we feed in private accumulates as weight '
                                      'on the hidden mind.'}},
 'Ketu': {'day': 'Tuesday/Thursday',
          'primary': {'traditional_original': 'Feed a stray dog. Donate a brown blanket.',
                      'curated': 'On Tuesday or Thursday, give food to a stray dog — your own, a '
                                 "neighbor's, or one in your neighborhood. Once a year, donate a "
                                 'brown or earth-toned blanket to a shelter or a person sleeping '
                                 'outside. On Tuesday, leave a small offering of bananas, fruit, '
                                 'or food at a place that holds spiritual meaning for you — a '
                                 'small altar at home, a tree you sit under, any space that feels '
                                 'sacred to you.'},
          'awakening': {'traditional_original': 'Keep cat. Donate blankets. Spiritual practice '
                                                'daily.',
                        'curated': 'For 7 weeks, on each Tuesday or Thursday, feed a stray dog or '
                                   'care for an animal that lives near humans without belonging to '
                                   'them. Donate at least one warm blanket during the cycle. '
                                   'Establish a 5-minute daily silent practice — sitting quietly, '
                                   'breathing, prayer in your own tradition, or simply staring at '
                                   "nothing — and don't break it."},
          'rin_clearing': {'traditional_original': '',
                           'curated': 'For 7 weeks, on each Tuesday or Thursday, reclaim 30 '
                                      'minutes of silent solitude — no phone, no music, no input. '
                                      'Sit alone or walk alone. During the cycle, give one '
                                      'possession away to someone who needs it more — not what you '
                                      "don't want, but something you have some attachment to. The "
                                      'act clears the release-debt of holding on — what we cling '
                                      'to past its time becomes weight on the planet of letting '
                                      'go.'}}}


def _resolve_remedy(planet: str, variant: str = "primary") -> str:
    """Curated upaay string for a planet (single, locale-independent).

    Emits UPAAY_LIBRARY[planet][variant]["curated"]. traditional_original is
    retained in the data but never emitted here. Falls back to the legacy
    REMEDY_TEXT one-liner if the library lacks a row. Returns a STRING — the
    response shape is unchanged (remedy was already a string).
    """
    if not planet:
        return REMEDY_TEXT.get("Mercury", "")
    row = (UPAAY_LIBRARY.get(planet) or {}).get(variant) or {}
    curated = row.get("curated")
    if curated:
        return curated
    return REMEDY_TEXT.get(
        planet, "Pause, breathe, and confirm what matters in writing.")


def _strip_home_payload(payload, language: str = "en"):
    """User-facing strips for a Home payload, with `remedy` routed through
    field_type='timing' (weekday-preserving) instead of 'plain'.

    The curated upaay in `remedy` intentionally carries a day-of-week
    ("On Tuesday, ..."). The 'plain' sweep deletes day names; 'timing' keeps
    them while still stripping planet names + Vedic jargon as defense-in-depth.
    Every other string keeps the standard 'plain' treatment, matching prior
    behaviour exactly.
    """
    from antar_engine.output_strips import apply_user_facing_strips as _apply

    # Structured planet-label fields — pass through unstripped, mirroring the
    # @translate_response fields_to_skip on /home. Prevents the strip from
    # turning phase.*.planet / cycleName (e.g. "Saturn") into an energy phrase.
    _KEEP = {"planet", "cycleName"}

    def _walk_curated(node):
        """lkRead subtree (Step 6): source='curated_static' — keep planet names
        as actors (Path B), still strip house numbers / Sanskrit / raw scores."""
        if isinstance(node, dict):
            return {kk: _walk_curated(vv) for kk, vv in node.items()}
        if isinstance(node, list):
            return [_walk_curated(x) for x in node]
        if isinstance(node, str):
            return _apply(node, language=language, field_type="plain",
                          source="curated_static", depth="user")
        return node

    def _walk(node):
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                if k in _KEEP:
                    out[k] = v
                elif k == "lkRead":
                    # [today-v2] Part 5 — Path B reversed for the Today
                    # card: planet labels ("SATURN-MARS IS WEAK") must not
                    # reach the UI. Full plain strip converts planet names
                    # to energy language; houses/Sanskrit already stripped.
                    out[k] = _walk(v)
                elif k == "remedy":
                    # UPAAY_LIBRARY curated (Step 6): timing keeps the weekday,
                    # source='curated_static' keeps planet-as-actor (Path B);
                    # houses/Sanskrit/scores still stripped.
                    if isinstance(v, str):
                        out[k] = _apply(v, language=language,
                                        field_type="timing", source="curated_static",
                                        depth="user")
                    elif isinstance(v, dict):
                        out[k] = {kk: (_apply(vv, language=language,
                                              field_type="timing", source="curated_static",
                                              depth="user")
                                       if isinstance(vv, str) else vv)
                                  for kk, vv in v.items()}
                    else:
                        out[k] = v
                elif isinstance(v, (dict, list)):
                    out[k] = _walk(v)
                elif isinstance(v, str):
                    out[k] = _apply(v, language=language,
                                    field_type="plain", depth="user")
                else:
                    out[k] = v
            return out
        if isinstance(node, list):
            return [_walk(x) for x in node]
        return node

    return _walk(payload)

USE_MAPS = {
    "today": {
        "Sun":     "Lead with your own initiative — make the visible move.",
        "Moon":    "Lean on warm conversations and steady routines.",
        "Mars":    "Take direct action on something you have been delaying.",
        "Mercury": "Front-load the thinking, planning, and writing.",
        "Jupiter": "Teach, mentor, or share — the room is with you.",
        "Venus":   "Reach for connection — a meal, a call, a small gift.",
        "Saturn":  "Do the foundational work — slow and durable wins.",
        "Rahu":    "Push on an ambition — bold direct action lands.",
        "Ketu":    "Edit, release, simplify — clarity is yours.",
    },
    "month": {
        "Sun":     "Make the visible move you have been postponing this month.",
        "Moon":    "Anchor your routines — home, sleep, family steady you now.",
        "Mars":    "This is the month to start and finish — pick one ambitious project.",
        "Mercury": "Use this month for planning, writing, and clear communication.",
        "Jupiter": "Teach or learn — the door is open.",
        "Venus":   "Invest in the people who matter — relationships flower now.",
        "Saturn":  "Build the foundation — durable work compounds this month.",
        "Rahu":    "Front-load visible work — momentum is with you.",
        "Ketu":    "Simplify — drop one obligation that has been weighing.",
    },
    "year": {
        "Sun":     "This is the year to step into leadership.",
        "Moon":    "A year to root your home life and emotional foundations.",
        "Mars":    "Direct action lands this year — start what you have been planning.",
        "Mercury": "A year for clear communication and visible thinking work.",
        "Jupiter": "A year of growth, learning, and meaning.",
        "Venus":   "A year for relationships — invest deeply in the people who matter.",
        "Saturn":  "A year for patient, foundational work that pays off later.",
        "Rahu":    "Front-load visible work before the summer.",
        "Ketu":    "A year to simplify — let go of what is no longer yours.",
    },
    "cycle": {
        "Sun":     "Use this chapter to claim your authority and direction.",
        "Moon":    "A chapter to deepen emotional roots and family.",
        "Mars":    "A chapter of direct action and finishing what you start.",
        "Mercury": "A chapter of clear thinking, planning, and communication.",
        "Jupiter": "A chapter of growth, teaching, and meaning.",
        "Venus":   "A chapter of relationships, art, and harmony.",
        "Saturn":  "A chapter of foundational work — slow, durable, real.",
        "Rahu":    "A chapter to chase ambition with focus.",
        "Ketu":    "A chapter to release, simplify, and turn inward.",
    },
}


_DIGNITY_CHARGE = {
    "exalted": 0.92, "own": 0.78, "friendly": 0.60,
    "neutral": 0.45, "debilitated": 0.18,
}


def _planet_charge(chart_data: dict, planet: str) -> float:
    """Real per-chart chakra charge from planetary dignity (0..1)."""
    if not planet:
        return 0.40
    try:
        from antar_engine.antar_ephemeris import _planet_strength as _dignity
        planets = chart_data.get("planets") or chart_data.get("planet_positions") or {}
        pdata = planets.get(planet) if isinstance(planets, dict) else None
        sign = (pdata.get("sign", "") if isinstance(pdata, dict) else "") or ""
        return _DIGNITY_CHARGE.get(_dignity(planet, sign), 0.45)
    except Exception:
        return 0.40


def _year_stretch_dynamic(chart_data: dict, now: datetime) -> dict:
    """
    Best/worst sub-windows of the coming year from real transit events.
    best  = highest-activity peak-window month run.
    worst = the month of the year's single most significant critical date.
    Falls back to the static season pair on any failure (e.g. no swisseph).
    """
    static = {"best": "Spring", "worst": "Autumn"}
    try:
        from antar_engine.transit_events import compute_transit_events_in_range
        from antar_engine.annual_planning import (
            _aggregate_year_peak_windows, _compute_critical_dates,
        )
        start = now.date()
        try:
            end = start.replace(year=start.year + 1)
        except ValueError:
            end = start.replace(year=start.year + 1, day=28)
        events = compute_transit_events_in_range(chart_data, start, end, include_fast=False)
        if not events:
            return static
        peaks = _aggregate_year_peak_windows(events)
        best_dom = max(
            (d for d in peaks.values() if d.get("months")),
            key=lambda d: d.get("score", 0), default=None,
        )
        best = best_dom["months"] if best_dom and best_dom.get("months") else static["best"]
        worst = static["worst"]
        crit = _compute_critical_dates(events, top_n=1)
        if crit:
            iso = (crit[0].get("raw_date") or "")[:10]
            try:
                cd = date.fromisoformat(iso)
                _mon = cd.strftime("%B")
                worst = (f"Early {_mon}" if cd.day <= 10
                         else f"Late {_mon}" if cd.day >= 20 else _mon)
            except Exception:
                pass
        return {"best": best, "worst": worst}
    except Exception:
        return static


def _build_chain_negative(weak_planet: str, charge: float = 0.40,
                          cause_override: str = None) -> dict:
    chakra = PLANET_TO_CHAKRA.get(weak_planet) or PLANET_TO_CHAKRA["Mercury"]
    name, minutes, steps = PRACTICE_BY_PLANET.get(weak_planet) or PRACTICE_BY_PLANET["Mercury"]
    return {
        "use":      None,
        "cause":    {"planet": weak_planet, "text": (cause_override or CAUSE_TEXT.get(weak_planet, ""))},
        "remedy":   _resolve_remedy(weak_planet),
        "chakra":   {"name": chakra["name"], "governs": chakra["governs"], "charge": round(charge, 2)},
        "practice": {"name": name, "minutes": minutes, "steps": list(steps)},
    }


def _build_chain_positive(strong_planet: str, horizon: str) -> dict:
    use_map = USE_MAPS.get(horizon, USE_MAPS["today"])
    return {
        "use":      use_map.get(strong_planet, "Lean into the strength that is available now."),
        "cause":    None,
        "remedy":   None,
        "chakra":   None,
        "practice": None,
    }


# ── Headline / gist / areas / stretch ───────────────────────────────────────

def _build_headline_gist(horizon: str, polarity: str) -> Tuple[str, str]:
    if polarity == "positive":
        return {
            "today": ("A clear day — energy is on your side.",
                      "Good for momentum, action, and visible work."),
            "month": ("A month with the wind behind you.",
                      "Pick one thing to push on and finish it."),
            "year":  ("A year of forward motion.",
                      "Set the direction now; the months will follow."),
            "cycle": ("A chapter built for steady progress.",
                      "Lean into the strength of this period."),
        }[horizon]
    return {
        "today": ("A quiet day — clarity is here, but outside momentum is low.",
                  "Good for thinking, not for pushing. One area is under pressure."),
        "month": ("A month to plan more than to push.",
                  "One area asks for attention. Take it slow."),
        "year":  ("A year of recalibration.",
                  "Foundations matter more than fireworks."),
        "cycle": ("A chapter asking for patience.",
                  "The lesson is in slowing down, not speeding up."),
    }[horizon]


def _build_areas(strong: list, weak: list,
                 dignity: dict = None, flagged: set = None) -> list:
    """When `dignity` is provided (Today branch), bars reflect real LK dignity
    and `care` reflects the flagged set. Otherwise behaviour is unchanged
    (Month/Year/Cycle keep their constant bars)."""
    flagged = flagged or set()
    areas: list = []
    seen: set = set()

    def _bars(p, default):
        if dignity is not None and p in dignity:
            return _bars_from_dignity(dignity[p])
        return default

    for p, _ in strong[:2]:
        nm = (PLANET_AREAS.get(p) or [p])[0]
        if nm in seen:
            continue
        seen.add(nm)
        first_theme = (PLANET_NATURE.get(p, "") or "").split(",")[0].strip() or "this area"
        areas.append({
            "name": nm, "bars": _bars(p, 3), "care": p in flagged,
            "note": f"Strong — favourable for {first_theme}.",
        })
    if weak:
        wp, _ = weak[0]
        nm = (PLANET_AREAS.get(wp) or [wp])[0]
        if nm not in seen:
            areas.append({
                "name": nm, "bars": _bars(wp, 0),
                "care": (wp in flagged) if flagged else True,
                "note": "Under pressure — postpone decisions in this area.",
            })
            seen.add(nm)
    while len(areas) < 2:
        areas.append({
            "name": "Wellbeing", "bars": 2, "care": False,
            "note": "Steady — keep your usual routine.",
        })
    return areas[:3]


def _build_stretch(horizon: str) -> dict:
    return {
        "today": {"best": "Late morning",   "worst": "Mid-afternoon"},
        "month": {"best": "First half",     "worst": "Last week"},
        "year":  {"best": "Spring",         "worst": "Autumn"},
        "cycle": {"best": "Opening third",  "worst": "Closing third"},
    }[horizon]


# ── Per-horizon composition ─────────────────────────────────────────────────

def _muhurta_windows(chart_row: dict, chart_data: dict,
                      now: datetime, tz_offset_min: int) -> Tuple[Optional[str], Optional[str]]:
    """Return (bestTime, avoidTime) localized strings, or (None, None) on failure."""
    try:
        from antar_engine.muhurta_engine import compute_muhurtas
        # Muhurta windows anchor to the user's CURRENT location —
        # country capital when known (and different from birth country),
        # else birth coords.
        _cc = (chart_row.get("current_country") or "").strip().upper()
        _bcc = (chart_row.get("birth_country") or chart_row.get("country_code") or "").strip().upper()
        lat = lon = 0.0
        if _cc and _cc != _bcc:
            try:
                from antar_engine.day_chart_engine import COUNTRY_COORDS as _MCC
                if _cc in _MCC:
                    lat, lon = float(_MCC[_cc][0]), float(_MCC[_cc][1])
            except Exception:
                lat = lon = 0.0
        if not lat or not lon:
            lat = float(chart_row.get("latitude") or chart_data.get("latitude") or 0)
            lon = float(chart_row.get("longitude") or chart_data.get("longitude") or 0)
        if not lat or not lon:
            return None, None
        muh = compute_muhurtas(now, lat, lon, tz_offset=float(tz_offset_min) / 60.0)
        ab = (muh or {}).get("abhijit_muhurta") or {}
        rk = (muh or {}).get("rahu_kalam") or {}
        best  = (f"{ab['start_local']} – {ab['end_local']}"
                 if ab.get("start_local") and ab.get("end_local") else None)
        avoid = (f"{rk['start_local']} – {rk['end_local']}"
                 if rk.get("start_local") and rk.get("end_local") else None)
        return best, avoid
    except Exception as e:
        print(f"[home_composer] muhurta calc skipped: {e}")
        return None, None


# ── Today: real transits over natal, read through Lal Kitab ──────────────────

KENDRA_TRIKONA_HOUSES = {1, 4, 5, 7, 9, 10}
DUSHTHANA_HOUSES      = {6, 8, 12}
SLOW_MOVERS           = {"Saturn", "Rahu", "Ketu"}

# LK dignity word → 0..1 score
_LK_DIGNITY_SCORE = {"dignified": 0.85, "neutral": 0.45, "afflicted": 0.20}

# Natal house → plain-English life sector (no jargon, no house numbers leak)
HOUSE_SECTOR = {
    1:  "your sense of self",
    2:  "your finances and security",
    3:  "your communication and courage",
    4:  "your home and inner peace",
    5:  "your creativity and joy",
    6:  "your work and health",
    7:  "your relationships",
    8:  "shared matters and change",
    9:  "your luck and beliefs",
    10: "your career and public life",
    11: "your goals and gains",
    12: "your rest and letting go",
}


def _bars_from_dignity(d: float) -> int:
    if d >= 0.75:
        return 3
    if d >= 0.50:
        return 2
    if d >= 0.25:
        return 1
    return 0


def _today_transit_signal(chart_data: dict, lk_data: dict, natal: dict,
                          now: datetime, tz_offset_min: int,
                          md_planet: str = "") -> dict:
    """
    Build the Today signal from TODAY'S real transits over the natal chart,
    read through the Lal Kitab day-lord diagnostic.

    Returns the shape the Today branch of _compose_for_horizon consumes:
      { strong:[(planet,house)], weak:[(planet,house)], polarity:str,
        conditions:{planet:plain_cause}, dignity:{planet:0..1}, flagged:set }
    """
    strong: list = []
    weak: list = []
    conditions: dict = {}
    dignity: dict = {}
    flagged: set = set()

    if lk_data is None:
        print("[home_composer] _today_transit_signal: lk_data is None — "
              "LK overlay degraded to transit-only (graceful default)")

    # 1. Today's real transits over the natal chart.
    report = {}
    try:
        from antar_engine import transit_engine as _te
        report = _te.get_full_transit_report(chart_data, date=now) or {}
    except Exception as e:
        print(f"[home_composer] _today_transit_signal: transit report failed: {e}")

    # house_activation: {natal_house: [transiting planets]} (whole-sign from lagna)
    house_activation = report.get("house_activation") or {}
    transit_house: dict = {}
    for h, planets in house_activation.items():
        try:
            hi = int(h)
        except Exception:
            continue
        for p in (planets or []):
            transit_house[p] = hi

    # 2. Lal Kitab day-lord diagnostic for today (arg order: lk_data, chart_data).
    lk = {}
    try:
        from antar_engine.lal_kitab_advanced import compute_lk_daily_diagnostic
        lk = compute_lk_daily_diagnostic(
            lk_data=lk_data or {}, chart_data=chart_data,
            target_date=now.date(), language="en",
        ) or {}
    except Exception as e:
        print(f"[home_composer] _today_transit_signal: lk diagnostic failed: {e}")

    lk_available = bool(lk.get("available"))
    day_lord     = lk.get("day_lord")
    lk_status    = lk.get("day_lord_status") or {}
    lk_dignity   = lk_status.get("dignity")          # dignified/neutral/afflicted
    lk_sleeping  = bool(lk_status.get("sleeping"))
    day_quality  = lk.get("day_quality_for_user")    # favorable/neutral/caution

    # 3. Classify each transiting planet by transit house + LK overlay.
    #    `dignity[p]` is TODAY'S effective favorability (drives areas.bars),
    #    not raw natal dignity: a flagged/weak transit caps it low so an
    #    "under pressure" area never renders high bars.
    for p, h in transit_house.items():
        d = _planet_charge(chart_data, p)
        if lk_available and day_lord and p == day_lord:
            d = _LK_DIGNITY_SCORE.get(lk_dignity, d)
            if lk_sleeping:
                d = min(d, 0.20)

        day_lord_flagged = (
            lk_available and day_lord == p and
            (lk_sleeping or lk_dignity == "afflicted" or day_quality == "caution")
        )
        if day_lord_flagged:
            dignity[p] = round(min(d, 0.20), 2)
            weak.append((p, h)); flagged.add(p); continue
        if h in DUSHTHANA_HOUSES:
            dignity[p] = round(min(d, 0.25), 2)
            weak.append((p, h)); flagged.add(p); continue
        dignity[p] = round(d, 2)
        if h in KENDRA_TRIKONA_HOUSES and d >= 0.5:
            strong.append((p, h))

    # 4. Plain-English cause text for flagged planets (no jargon, no planet names).
    for p in list(flagged):
        sector = HOUSE_SECTOR.get(transit_house.get(p, 0),
                                  "an important part of your life")
        energy = ENERGY_LANG.get(p, "your energy")
        conditions[p] = (f"{energy[0].upper()}{energy[1:]} is moving through a "
                         f"slower phase around {sector} today.")

    # defensive: strip any jargon that could leak (built clean, but enforce)
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        conditions = apply_user_facing_strips(
            conditions, language="en", field_type="plain",
        )
    except Exception as e:
        print(f"[home_composer] _today_transit_signal: strips skipped: {e}")

    # 5. Ordering — MD planet first, then day-lord, then slow-movers.
    def _rank(item):
        p = item[0]
        s = 0
        if md_planet and p.lower() == md_planet.lower():
            s -= 100
        if day_lord and p == day_lord:
            s -= 50
        if p in SLOW_MOVERS:
            s -= 10
        return s
    weak.sort(key=_rank)
    strong.sort(key=_rank)

    # 6. Polarity — LK day quality dominant; transit count is the tiebreaker.
    if lk_available and day_quality == "caution":
        polarity = "negative"
    elif lk_available and day_quality == "favorable":
        polarity = "positive"
    else:
        polarity = "negative" if len(weak) > len(strong) else "positive"

    return {
        "strong": strong,
        "weak": weak,
        "polarity": polarity,
        "conditions": conditions,
        "dignity": dignity,
        "flagged": flagged,
        "available": lk_available or bool(house_activation),
    }


def _compose_for_horizon(horizon: str,
                          chart_row: dict, chart_data: dict, lk_data: dict,
                          current_md_row: Optional[dict], current_ad_row: Optional[dict],
                          tz_offset_min: int) -> dict:
    natal = _natal_houses(chart_data)
    bd = chart_row.get("birth_date", "") or ""
    md_planet = (current_md_row or {}).get("planet_or_sign", "") or ""

    # AD sub-chapter context (cycle horizon only; harmless defaults elsewhere).
    # Field is `planet_or_sign` on the dasha_periods row (same as MD).
    ad_planet  = None
    ad_house   = 0
    md_end_iso = (current_md_row or {}).get("end_date")
    ad_end_iso = (current_ad_row or {}).get("end_date")

    today_signal = None
    now_today = _now_local(tz_offset_min)
    if horizon == "today":
        today_signal = _today_transit_signal(
            chart_data, lk_data, natal, now_today, tz_offset_min, md_planet,
        )
        placements = {}
    elif horizon == "month":
        placements = _masik_placements(bd, natal)
    elif horizon == "year":
        placements = _varshphal_placements(bd, natal)
    else:  # cycle — driven by current MD planet's natal house only
        placements = {}

    if horizon == "cycle":
        if not md_planet:
            md_planet = "Jupiter"
        natal_house = natal.get(md_planet, 0)
        if natal_house in DIFFICULT_HOUSES:
            strong, weak = [], [(md_planet, natal_house)]
        else:
            strong, weak = [(md_planet, natal_house or 1)], []

        # Read the AD planet (already loaded in main.py, passed through).
        if current_ad_row:
            ad_planet = current_ad_row.get("planet_or_sign") or None
        ad_house = natal.get(ad_planet, 0) if ad_planet else 0
    elif today_signal is not None:
        strong, weak = today_signal["strong"], today_signal["weak"]
    else:
        strong, weak = _classify(placements)

    if today_signal is not None:
        polarity = today_signal["polarity"]
    else:
        polarity = _resolve_polarity(strong, weak)
    wp = _dominant_weak_planet(weak, md_planet)
    sp = _dominant_strong_planet(strong, md_planet) or (md_planet if horizon == "cycle" else "Mercury")

    headline, gist = _build_headline_gist(horizon, polarity)
    # MD->AD sub-chapter: only when there is a distinct AD planet.
    if horizon == "cycle" and ad_planet and ad_planet != md_planet:
        _theme = AD_PLANET_THEMES.get(ad_planet, "a new phase")
        gist = f"{gist} Right now, the {_theme} chapter inside it."
    lk_cause = None
    if today_signal is not None and wp:
        lk_cause = (today_signal.get("conditions") or {}).get(wp)
    chain = (_build_chain_negative(wp, _planet_charge(chart_data, wp), lk_cause) if polarity == "negative" and wp
             else _build_chain_positive(sp, horizon))

    now = _now_local(tz_offset_min if horizon == "today" else 0)
    if horizon == "today":
        range_str = _format_today_range(now)
        best_t, avoid_t = _muhurta_windows(chart_row, chart_data, now, tz_offset_min)
        pivot = wp if polarity == "negative" and wp else sp
        do_text   = PLANET_DO.get(pivot,   PLANET_DO["Mercury"])
        dont_text = PLANET_DONT.get(pivot, PLANET_DONT["Mercury"])
        tab = "Today"
    elif horizon == "month":
        range_str = _format_month_range(now)
        best_t = avoid_t = None
        do_text = dont_text = None
        tab = "This Month"
    elif horizon == "year":
        range_str = _format_year_range(bd, now)
        best_t = avoid_t = None
        do_text = dont_text = None
        tab = "This Year"
    else:
        range_str = _format_cycle_range(current_md_row)
        best_t = avoid_t = None
        do_text = dont_text = None
        tab = "Current Cycle"

    phase_block = None
    if horizon == "cycle":
        phase_block = {
            "mahadasha":  {"planet": md_planet, "ends": md_end_iso},
            "antardasha": ({"planet": ad_planet, "ends": ad_end_iso}
                           if ad_planet else None),
        }

    view = {
        "tab":       tab,
        "range":     range_str,
        "polarity":  polarity,
        "headline":  headline,
        "gist":      gist,
        "cycleName": (f"{md_planet} cycle" if horizon == "cycle" and md_planet else None),
        "info":      (CYCLE_INFO if horizon == "cycle" else None),
        "do":        do_text,
        "dont":      dont_text,
        "bestTime":  best_t,
        "avoidTime": avoid_t,
        "areas":     _build_areas(
            strong, weak,
            today_signal.get("dignity") if today_signal else None,
            today_signal.get("flagged") if today_signal else None,
        ),
        "stretch":   (_year_stretch_dynamic(chart_data, now) if horizon == "year" else _build_stretch(horizon)),
        "phase":     phase_block,
    }
    # ── LK conditions read (Step 5) — additive, zero-regression ────────────
    # Specific Lal Kitab condition read for Today, attached as `lkRead`. When a
    # non-flat condition fires it carries the precise headline / cause / use /
    # do / dont + gentling_prefix / crisis_footer / modifiers from the curated
    # LK_CONDITIONS library. Additive by default — does NOT overwrite the shipped
    # template fields; the frontend promotes lkRead to primary once verified.
    # The whole block is guarded: any failure leaves lkRead=None and the existing
    # card untouched. recent_headlines=[] for now (no 14-day history yet; source
    # it from chart_daily_headlines to make gentling/crisis live).
    if horizon == "today":
        view["lkRead"] = None
        try:
            from antar_engine.lk_conditions import LK_CONDITIONS
            from antar_engine.lk_trigger import matches_trigger
            from antar_engine.composition import compose_daily_card
            from antar_engine.transits_engine import calculate_current_transits
            _tr = (calculate_current_transits(chart_data) or {}).get("current_transits", [])
            _dasha = {"md_lord": md_planet}
            _fired = []
            for _cid, _cond in LK_CONDITIONS.items():
                try:
                    if matches_trigger(_cond["trigger"], chart_data, _tr, _dasha):
                        _fired.append({**_cond, "id": _cid})
                except Exception:
                    continue
            _card = compose_daily_card(_fired, md_planet, [], now_today.date())
            if _card.get("polarity") != "flat":
                # [today-v2] Part 4 — no remedy concept on Today: the
                # remedy_planet/remedy_variant pointers are engine-internal
                # and must not reach the frontend payload.
                _card.pop("remedy_planet", None)
                _card.pop("remedy_variant", None)
                view["lkRead"] = _card
        except Exception as _lke:
            print(f"[home_composer] lkRead skipped (non-fatal): {_lke}")

    # Polarity XOR — chain merged last
    view.update(chain)
    if horizon == "today":
        # [today-v2] Part 4 — NO per-day remedy. A remedy (upaay) acts on
        # the dasha/varshphal timescale (~21-43 days); per-day it is
        # meaningless. Real remedies live in the Practice tab. Month/year/
        # cycle horizons keep their chain remedy (correct timescale).
        view["remedy"] = None
        # [today-v2] Part 5 — no planet-label chips on the Today card:
        # cause.planet was passed through unstripped (_KEEP); replace with
        # the plain energy phrase so the UI never renders "SATURN".
        if isinstance(view.get("cause"), dict) and view["cause"].get("planet"):
            _cp = view["cause"]["planet"]
            view["cause"]["planet"] = ENERGY_LANG.get(_cp, "this energy")
    return view


def compose_home_payload(chart_id: str, chart_row: dict, chart_data: dict, lk_data: dict,
                          current_md_row: Optional[dict], current_ad_row: Optional[dict],
                          language: str, tz_offset: int) -> dict:
    first_name = chart_row.get("first_name") or "Friend"
    initial    = (first_name[:1] or "F").upper()
    horizons   = {}
    for h in ("today", "month", "year", "cycle"):
        horizons[h] = _compose_for_horizon(
            h, chart_row, chart_data, lk_data,
            current_md_row, current_ad_row, int(tz_offset or 0),
        )
    return {
        "chart_id":     chart_id,
        "language":     language,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "user":         {"name": first_name, "initial": initial},
        "horizons":     horizons,
    }
