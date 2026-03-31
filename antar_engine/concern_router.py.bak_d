"""
antar_engine/concern_router.py

Concern-based context router.
Maps any question to a focus domain.
Each domain gets:
  1. Priority context — which data goes FIRST to LLM
  2. System instruction override — what lens to use
  3. Banned topics — what NOT to discuss
  4. Required elements — what MUST be mentioned
  5. Answer format — how to structure the response
"""

from typing import Optional

# ── Concern detection ─────────────────────────────────────────────

CONCERN_KEYWORDS = {
    "finance": [
        "money","wealth","rich","income","salary","earn","financial",
        "investment","stock","shares","returns","profit","loss","savings",
        "billionaire","millionaire","afford","expensive","cheap","funds",
        "revenue","cash","assets","net worth","portfolio","crypto","fd",
        "mutual fund","sip","nifty","sensex","real estate investment"
    ],
    "career": [
        "career","job","work","profession","occupation","business","startup",
        "company","office","boss","promotion","fired","resign","interview",
        "hiring","position","role","designation","corporate","mnc","job offer",
        "switch job","career change","professional","entrepreneur","freelance",
        "consulting","government job","ias","ips","civil service","exam",
        "placement","campus","internship"
    ],
    "relationship": [
        "love","relationship","partner","girlfriend","boyfriend","dating",
        "romance","romantic","affair","feelings","crush","attract","soulmate",
        "compatibility","match","meet someone","find love","heart","breakup",
        "patch up","long distance","commitment","propose","engagement"
    ],
    "marriage": [
        "marriage","marry","wedding","spouse","husband","wife","rishta",
        "arrange marriage","love marriage","in-laws","dowry","shaadi",
        "nikah","vivah","second marriage","remarry","divorce","separation",
        "marital","conjugal","married life"
    ],
    "children": [
        "children","child","baby","pregnancy","pregnant","conceive","ivf",
        "fertility","son","daughter","kid","progeny","adopt","adoption",
        "motherhood","fatherhood","miscarriage","delivery","birth"
    ],
    "health": [
        "health","sick","illness","disease","pain","doctor","hospital",
        "medicine","treatment","surgery","operation","recover","cure",
        "diagnosis","chronic","diabetes","cancer","heart","blood pressure",
        "mental health","anxiety","depression","stress","sleep","diet",
        "fitness","exercise","weight","body"
    ],
    "legal": [
        "legal","court","case","lawsuit","police","fir","complaint","judge",
        "lawyer","advocate","bail","arrest","jail","prison","dispute",
        "property dispute","land case","cheating case","fraud","criminal",
        "civil case","hearing","verdict","settlement","fight case","win case"
    ],
    "foreign": [
        "abroad","foreign","overseas","visa","immigration","migrate","settle",
        "usa","uk","canada","australia","europe","gulf","dubai","singapore",
        "pr","green card","citizenship","work permit","study abroad"
    ],
    "property": [
        "property","house","flat","apartment","land","plot","real estate",
        "buy home","rent","mortgage","emi","construction","builder",
        "registry","possession","new home","home loan"
    ],
    "spiritual": [
        "spiritual","meditation","moksha","karma","dharma","liberation",
        "enlightenment","guru","temple","pilgrimage","mantra","prayer",
        "god","religion","faith","soul","purpose","meaning of life",
        "past life","rebirth","reincarnation"
    ],
    "education": [
        "education","study","exam","result","degree","university","college",
        "school","marks","score","pass","fail","admission","course","mba",
        "engineering","medicine","law school","higher education","phd",
        "research","scholarship","entrance","jee","neet","cat","upsc"
    ],
    "daily": [
        "today","tomorrow","this week","this month","right now","currently",
        "at this moment","daily","day","tonight","morning","evening"
    ],
    "general": [],  # fallback
}

# ── Domain configurations ────────────────────────────────────────

DOMAIN_CONFIGS = {

    "finance": {
        "display_name": "Wealth & Finance",
        "priority_data": [
            "WEALTH ENGINE SCORE AND VERDICT",
            "D2 Hora chart (wealth chart) — which hora are key planets in",
            "Jupiter house and sign (primary wealth significator)",
            "Venus house (luxury and material comfort)",
            "Rahu house (unconventional wealth)",
            "2nd house (savings/family wealth) and 11th house (income/gains)",
            "Lord of 2nd and 11th house positions",
            "Dhana Yoga combinations found",
            "Current dasha lord's wealth signification",
            "D60 karma for Jupiter and Venus (past life wealth pattern)",
        ],
        "system_instruction": """WEALTH FOCUS MODE — prioritize financial data.
Answer this wealth/money question by leading with:
1. Lead with the WEALTH ENGINE SCORE and verdict as the foundation
2. Identify the PRIMARY wealth combinations present (Rahu in 11th, Jupiter in 2nd, etc.)
3. Explain the CURRENT financial chapter based on active dasha
4. Give the PEAK wealth window (which dasha period = maximum earning)
5. Reference D2 Hora chart for wealth type (Sun hora = self-made, Moon hora = inherited/public)
6. If D60 shows challenging Jupiter/Venus karma: explain as "a pattern where wealth arrives but needs to be consciously preserved"
7. ONE specific Lal Kitab remedy for wealth activation
8. End with: "Your most important financial action this week is: [specific action]"


MUST MENTION: specific score, peak period years, wealth type, one remedy""",
        "required_elements": [
            "wealth score from engine",
            "peak wealth window years",
            "wealth type (unconventional/traditional/earned)",
            "specific remedy",
        ],
        "answer_format": """
**Your Wealth Picture**
[2 sentences — score and overall verdict in plain language]

**What's Working For You**
[2-3 specific combinations from the wealth engine]

**Your Peak Window**
[Specific years — which dasha period = maximum financial growth]

**The Pattern to Break**
[If D60 karma challenging — what recurring pattern to address]

**Do This Now**
[One specific financial action + one Lal Kitab remedy]""",
    },

    "career": {
        "display_name": "Career & Business",
        "priority_data": [
            "D10 Dashamsa lagna and planets (career chart — most important)",
            "10th house of D1 — planets and lord",
            "career path signal planet — career's guiding force",
            "Narayana Dasha current period — external career events",
            "Sun position (authority/government)",
            "Saturn position (service/discipline)",
            "Mercury position (business/communication)",
            "Rahu in career houses (unconventional path)",
            "Raj Yoga presence and activation status",
            "Current dasha lord's career signification",
        ],
        "system_instruction": """CAREER FOCUS MODE — prioritize career data.
Answer this career/job question by leading with:
1. Lead with D10 Dashamsa lagna — this is the career chart. What does it say?
2. Identify the career path signal planet and its current strength
3. Reference Narayana Dasha — this system specifically times CAREER events
4. What is the current dasha lord saying about professional life?
5. Is there a Raj Yoga? Is it activated by current timing?
6. Job vs business verdict from the engine — which path is supported?
7. Peak career authority window — when does this person reach their zenith?
8. ONE remedy for career activation

Answer format:
**Your Career Blueprint** — what the career chart shows fundamentally
**Right Now** — what the current timing says about professional life
**Your Authority Window** — when career peaks
**Job vs Business** — which path the chart favors
**Your Move** — one specific action + remedy



**Right Now (2025-2026)**
[Current dasha career themes]

**Your Authority Window**
[When career peaks — specific years]

**Job or Business?**
[Direct recommendation from engine]

**Your Move**
[One specific action today + remedy]""",
    },

    "relationship": {
        "display_name": "Love & Relationships",
        "priority_data": [
            "Venus house and sign (love and attraction)",
            "5th house (romance and heart connections)",
            "Moon sign (emotional nature and compatibility)",
            "D9 soul chart — soul-level relationship chart",
            "partner signal planet — partner's nature",
            "7th house condition for partnerships",
            "Current dasha lord's relationship signification",
            "Mars position (passion and desire)",
            "Affairs engine analysis",
            "D60 Venus karma (past life relationship patterns)",
        ],
        "system_instruction": """RELATIONSHIP FOCUS MODE — prioritize love/relationship data.
Answer this relationship question by leading with:
1. Venus position — where is love energy directed in this chart?
2. 5th house — what does the heart want? What kind of love is activated?
3. Moon sign — emotional nature and what kind of partner completes this person
4. D9 soul chart — the soul's truth about relationships (deeper than surface)
5. partner signal planet planet — what the partner will be like (planet's qualities)
6. Current dasha — is this a relationship-activation period?
7. D60 Venus karma — are there past-life patterns affecting love now?
8. Timing — when is the next significant romantic activation?

Be warm, specific, and emotionally intelligent. This is sensitive territory.
Never be dismissive. Even challenging placements have wisdom.
ONE remedy for Venus/relationship activation.



**The Partner You're Drawn To**
[partner signal planet + Moon sign reading]

**Right Now**
[Current dasha relationship theme]

**Timing**
[When next significant romantic activation]

**What Helps**
[One Venus remedy + one emotional practice]""",
    },

    "marriage": {
        "display_name": "Marriage & Spouse",
        "priority_data": [
            "7th house — house of marriage and life partner",
            "7th lord position and strength",
            "Venus position (marriage karaka for men)",
            "Jupiter position (marriage karaka for women)",
            "D9 soul chart ascendant and 7th house (soul marriage chart)",
            "D9 Venus and Jupiter positions",
            "partner signal planet planet and sign",
            "Divorce risk engine score",
            "Second marriage indicators",
            "Current dasha lord's marriage signification",
        ],
        "system_instruction": """MARRIAGE FOCUS MODE — prioritize marriage data.
Answer this marriage question by leading with:

1. 7th house condition — is this a strong or challenged marriage house?
2. 7th lord — where is marriage energy going in the chart?
3. D9 soul chart 7th house — the soul's truth about the marriage
4. partner signal planet — what is the spouse's nature? Use the planet's qualities.
5. Marriage timing — when is the chart activated for marriage?
6. Divorce risk score — mention if elevated with specific reasons
7. Second marriage indicators — mention if present
8. Lal Kitab annual chart for THIS year — what does the annual chart say about marriage this year?

Be sensitive. Marriage questions often come from pain or hope.
Be honest but constructive. Challenges can be remedied.
ONE specific Lal Kitab remedy for marriage.

MUST reference: D9 soul chart, partner signal planet nature, this year's annual chart""",
        "required_elements": [
            "7th house reading",
            "D9 navamsa marriage indication",
            "partner signal planet partner nature",
            "marriage timing",
            "Lal Kitab remedy",
        ],
        "answer_format": """
**Your Marriage Blueprint**
[7th house + D9 reading]

**Your Spouse's Nature**
[partner signal planet planet qualities in plain language]

**This Year (annual chart)**
[Annual chart reading for marriage matters]

**Timing**
[When marriage is activated]

**Remedy**
[Specific Lal Kitab remedy for marriage]""",
    },

    "legal": {
        "display_name": "Legal Matters",
        "priority_data": [
            "Legal cases engine score and verdict",
            "6th house (litigation and disputes)",
            "6th lord position and strength",
            "Saturn position (justice and karma)",
            "Mars position (conflict and disputes)",
            "Rahu position (foreign legal or government matters)",
            "D30 Trimsamsa — misfortune chart for legal risk",
            "Current dasha lord's legal signification",
            "Jail yoga assessment",
            "Winning indicators in chart",
        ],
        "system_instruction": """LEGAL FOCUS MODE — prioritize legal data.
Answer this legal question by leading with:
1. Legal engine verdict — is the chart favorable or challenging for this case?
2. 6th house strength — how strong is the person's ability to fight/defend?
3. Saturn and Mars positions — are they supporting or opposing?
4. D30 Trimsamsa — does the misfortune chart show active legal risk?
5. Current dasha — does the dasha lord bring legal victory or delay?
6. Winning indicators — specifically what in the chart supports winning
7. Risk indicators — what needs attention
8. Timing — when is the case likely to resolve?
9. TWO remedies — one for the dasha lord, one for Saturn (justice planet)

Be direct. Legal questions need clear answers.
Never say "consult a lawyer" — they already have one. They want the cosmic timing.
Frame the answer as: what the chart shows, what period is favorable, what to do.

MUST mention: winning score, timing of resolution, specific remedies""",
        "required_elements": [
            "legal engine score",
            "winning indicators",
            "timing of resolution",
            "two specific remedies",
        ],
        "answer_format": """
**What the Chart Shows**
[Legal engine verdict + 6th house reading]

**Your Strengths in This Case**
[Winning indicators in plain language]

**Watch Out For**
[Risk factors — what could delay or complicate]

**Timing**
[When case likely resolves based on dasha]

**Do These Two Things**
[Saturn remedy + dasha lord remedy]""",
    },

    "health": {
        "display_name": "Health & Body",
        "priority_data": [
            "Health engine score and watch areas",
            "D27 Bhamsa — physical strength chart",
            "Lagna and lagna lord (body constitution)",
            "Moon position (mental and emotional health)",
            "Saturn position (chronic conditions)",
            "Mars position (inflammation and accidents)",
            "6th house (disease) and 8th house (chronic)",
            "Current dasha lord's health theme",
            "D30 active health risks",
            "Ayurveda dosha from Moon nakshatra",
        ],
        "system_instruction": """HEALTH FOCUS MODE — prioritize health data.
Answer this health question by leading with:
1. D27 Bhamsa — physical constitution strength
2. Health engine watch areas — specific body systems at risk
3. Current dasha lord's health theme — what physical themes are active NOW
4. D30 Trimsamsa — any active health risk planets?
5. Moon condition — mental and emotional health
6. Saturn and Mars positions — chronic vs acute risk
7. Ayurveda dosha alignment (Vata/Pitta/Kapha) from Moon nakshatra
8. Specific health practices for this chart
9. TWO remedies — one for the body part/system at risk, one for current dasha lord

Frame health insights as awareness and prevention, not diagnosis. Always add 'get professional checkups'.
Frame as: "your chart suggests attention to..." not "you have..."
Focus on preventive wisdom and remedies.

MUST mention: specific watch areas, dosha, current dasha health theme""",
        "required_elements": [
            "D27 strength reading",
            "watch areas (specific)",
            "current dasha health theme",
            "dosha recommendation",
        ],
        "answer_format": """
**Your Physical Blueprint**
[D27 + constitution reading]

**What Needs Attention Now**
[Current dasha health themes — active right now]

**Watch Areas**
[Specific body systems — always add "get checked regularly"]

**Your Dosha Balance**
[Ayurveda reading from Moon nakshatra]

**Practices and Remedies**
[Two specific practices + one Lal Kitab remedy]""",
    },

    "foreign": {
        "display_name": "Foreign Settlement",
        "priority_data": [
            "Foreign settlement engine score and verdict",
            "12th house (foreign lands)",
            "9th house (long journeys and fortune abroad)",
            "Rahu position (foreign karma)",
            "12th lord and 9th lord positions",
            "Moon sign (movable = travel friendly)",
            "D9 soul chart for foreign indicators",
            "Current dasha lord's foreign signification",
            "Visa/immigration timing from dasha",
        ],
        "system_instruction": """FOREIGN FOCUS MODE — prioritize foreign/immigration data.
Answer this foreign settlement question by leading with:

1. Foreign settlement engine score — strong/moderate/weak indicators
2. Rahu position — Rahu in 1/7/9/12 = strong foreign connection
3. 12th house — the house of foreign lands
4. 9th lord in 12th or 12th lord in 9th = strongest foreign destiny
5. Moon sign type — movable sign Moon = easier relocation
6. Which country/direction? (based on sign and planet combinations)
7. Current dasha — does it support foreign moves?
8. Best timing window for immigration/relocation
9. ONE remedy to strengthen foreign prospects

DIRECTION MAPPING:
  Aries/Scorpio/Mars → East
  Taurus/Libra/Venus → South-East
  Gemini/Virgo/Mercury → North
  Cancer/Moon → North-West
  Leo/Sun → East
  Sagittarius/Pisces/Jupiter → North-East
  Capricorn/Aquarius/Saturn → West
  Rahu → South-West (foreign, unconventional)""",
        "required_elements": [
            "foreign settlement score",
            "Rahu and 12th house reading",
            "best timing window",
            "direction/country indicator",
        ],
        "answer_format": """
**Your Foreign Destiny**
[Settlement score + Rahu reading]

**Strongest Indicators**
[What specifically supports foreign life]

**Direction and Type**
[Which direction/country type is favored]

**Timing**
[Best window for move or application]

**What to Do**
[One specific action + remedy]""",
    },

    "spiritual": {
        "display_name": "Spirituality & Purpose",
        "priority_data": [
            "D20 Vimshamsa — spiritual progress chart",
            "D60 Shashtiamsa — past life karma and soul mission",
            "Ketu position (past life spiritual practice)",
            "Jupiter position (wisdom and dharma)",
            "12th house (liberation and moksha)",
            "9th house (dharma and higher purpose)",
            "soul's core signal planet (soul's core mission)",
            "Karakamsha sign (soul's operating platform)",
            "Current dasha — spiritual activation periods",
            "WOW effects related to spirituality",
        ],
        "system_instruction": """SPIRITUAL FOCUS MODE — prioritize soul/purpose data.
Answer this spiritual question by leading with:
1. Soul's core signal planet — what is this soul's core mission? (in plain language)
2. Karakamsha — what is the soul's operating platform this life?
3. D20 Vimshamsa — what spiritual path is indicated?
4. Ketu position — what spiritual merit came from past lives?
5. D60 karma — what is the karmic theme of this incarnation?
6. 12th house — how does liberation manifest for this chart?
7. Current dasha — is this a spiritually activating period?
8. WOW effects — any extraordinary spiritual combinations?
9. ONE specific spiritual practice for this chart

Be profound but accessible. Spiritual seekers want depth.
Connect cosmic patterns to everyday experience.
Frame D60 challenging karma as "the soul chose this to learn X"

MUST mention: soul's core signal mission, D20 spiritual path, Ketu's past-life gift""",
        "required_elements": [
            "soul's core signal mission",
            "D20 spiritual path",
            "Ketu past life gift",
            "specific practice",
        ],
        "answer_format": """
**Your Soul's Mission**
[Soul's core signal in plain language]

**What You Brought From Past Lives**
[Ketu + D60 positive karma]

**Your Spiritual Path**
[D20 Vimshamsa reading]

**What This Life Is For**
[Integration of all soul indicators]

**Your Practice**
[One specific spiritual practice for this chart]""",
    },

    "daily": {
        "display_name": "Today & Now",
        "priority_data": [
            "TODAY'S PANCHANGA — 5 limbs of the day",
            "Moon nakshatra energy today",
            "Current planetary hour",
            "Rahu Kalam (avoid this time)",
            "Abhijit Muhurta (best time today)",
            "Lucky hours by activity",
            "WOW moments active today",
            "Current dasha theme",
            "Daily do and don't list",
        ],
        "system_instruction": """DAILY FOCUS MODE — prioritize today's Panchanga and timing.
Answer this daily question by leading with:
1. Moon nakshatra — what energy is the Moon broadcasting today?
2. Day lord — whose day is it and what does that mean practically?
3. Panchanga quality — is today auspicious, neutral, or to be navigated carefully?
4. Rahu Kalam — specifically mention the time to avoid
5. Best time today (Abhijit Muhurta)
6. Lucky hours for their specific concern
7. WOW moment if any — make it special
8. One do and one don't for today
9. Connect current dasha to today's energy

Make it feel like a morning briefing from a wise friend.
Specific times. Specific actions. No vagueness.
Reference the nakshatra by name — it makes it feel personal.

MUST mention: nakshatra name, Rahu Kalam time, best time, one do + one don't""",
        "required_elements": [
            "nakshatra energy",
            "Rahu Kalam time",
            "best time today",
            "one do + one don't",
        ],
        "answer_format": """
**Today's Energy**
[Nakshatra + day lord in plain language]

**Best Time Today**
[Abhijit Muhurta — for important actions]

**Avoid**
[Rahu Kalam time + one thing to skip today]

**Your Move Today**
[One specific action based on today's energy]

**Tonight**
[One closing practice or reflection]""",
    },

    "general": {
        "display_name": "General Reading",
        "priority_data": [
            "Current dasha period theme",
            "Top 3 active yogas",
            "Strongest house in chart",
            "Current Narayana Dasha",
            "D60 most prominent karma",
            "WOW effects present",
        ],
        "system_instruction": """GENERAL LIFE READING MODE.
Give a holistic reading covering the most active themes right now.

1. What is the dominant theme of the current life chapter?
2. What are the 2-3 strongest combinations working in their favor?
3. What is the most important thing to focus on right now?
4. What does the current timing indicate across all life areas?
5. ONE most important remedy for this period

Be holistic but focused. Don't try to cover everything.
Pick the 2-3 most resonant themes and go deep on them.
End with a clear direction for the next 90 days.""",
        "required_elements": [
            "current chapter theme",
            "strongest active combinations",
            "90-day direction",
        ],
        "answer_format": """
**Your Current Chapter**
[Dasha theme in plain language]

**What's Working For You**
[2-3 strongest active combinations]

**What Needs Attention**
[1-2 things to be aware of]

**Next 90 Days**
[Specific direction and focus]

**Your Practice**
[One remedy + one action]""",
    },
}


def detect_concern(question: str, context: str = "") -> str:
    """Detect the primary concern from a question."""
    q_lower = (question + " " + context).lower()

    scores = {}
    for concern, keywords in CONCERN_KEYWORDS.items():
        if concern == "general":
            continue
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            scores[concern] = score

    if not scores:
        return "general"

    # Handle ambiguity — marriage > relationship if both present
    if scores.get("marriage", 0) > 0 and scores.get("relationship", 0) > 0:
        return "marriage"

    return max(scores, key=scores.get)


def get_domain_config(concern: str) -> dict:
    """Get the full domain configuration for a concern."""
    return DOMAIN_CONFIGS.get(concern, DOMAIN_CONFIGS["general"])


def build_concern_system_prompt(concern: str) -> str:
    """Build the complete system prompt for a specific concern."""
    config = get_domain_config(concern)
    base_rules = """
UNIVERSAL RULES (always apply regardless of focus):
- Never use Sanskrit/technical terms — translate everything to plain language
- Python engine verdicts are FACTS — explain them, never contradict
- Reference specific planets and placements — never be vague
- One specific remedy per response — concrete and actionable
- Under 300 words unless question requires depth
- Age 50+: focus on legacy/health/wisdom
- Challenging karma: frame as "a pattern being resolved"
- When 2+ timing systems agree: "both your timing systems confirm this"
"""
    return config["system_instruction"] + base_rules


def get_priority_context_instruction(concern: str) -> str:
    """Get instruction for context builder about what to prioritize."""
    config = get_domain_config(concern)
    items  = config["priority_data"]
    lines  = [f"PRIORITY CONTEXT FOR {config['display_name'].upper()} QUESTION:"]
    lines += [f"  {i+1}. {item}" for i, item in enumerate(items)]
    lines += ["", "Focus the LLM's attention on these elements first."]
    return "\n".join(lines)


def get_answer_format(concern: str) -> str:
    """Get the required answer format for a concern."""
    config = get_domain_config(concern)
    return config.get("answer_format", "")
