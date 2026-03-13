"""
antar_engine/patra_conversation.py

Smart Conversational Patra Extraction
──────────────────────────────────────────────────────────────────────
Real astrologers don't ask "what's your financial situation?"
They look at the chart, notice Venus is afflicted, and say:
"I'm seeing some tension around partnerships and money — 
 has that been showing up in your life?"

This module does the same thing:
  1. Reads the chart and active dashas
  2. Generates chart-specific questions that feel natural
  3. Extracts Patra data from the answers without the user
     knowing they're filling out a form
  4. Also extracts Patra passively from things users 
     naturally say in chat (onboarding, life events, questions)

The user never sees a form. They see a wise guide 
asking questions that feel surprisingly personal.
"""

from __future__ import annotations
from typing import Optional


# ── Chart-driven question triggers ────────────────────────────────────────────
# Each trigger looks at chart conditions and generates a natural question.
# The answer extracts one or more Patra fields.

def get_smart_patra_questions(chart_data: dict, dashas: dict) -> list[dict]:
    """
    Generate chart-specific natural questions.
    Each question is derived from something real in the chart.

    Returns list of:
    {
        "id":         str,
        "question":   str,    ← what the user sees/hears
        "reason":     str,    ← internal: why this question was triggered
        "options":    list,   ← tap options (or None for open text)
        "extracts":   list,   ← which Patra fields this answer fills
    }
    """
    questions = []

    lagna      = chart_data["lagna"]["sign"]
    moon_sign  = chart_data["planets"]["Moon"]["sign"]
    moon_nak   = chart_data["planets"]["Moon"]["nakshatra"]
    vim_dasha  = dashas.get("vimsottari", [{}])[0].get("lord_or_sign", "")
    jai_dasha  = dashas.get("jaimini", [{}])[0].get("lord_or_sign", "")

    planets    = chart_data["planets"]
    venus      = planets.get("Venus", {})
    jupiter    = planets.get("Jupiter", {})
    saturn     = planets.get("Saturn", {})
    mars       = planets.get("Mars", {})
    sun        = planets.get("Sun", {})
    moon       = planets.get("Moon", {})

    # ── RELATIONSHIP questions ─────────────────────────────────────
    # Triggered by: Venus dasha, 7th lord activity, or Moon in relational signs

    if vim_dasha == "Venus" or venus.get("sign") in ["Libra", "Taurus", "Pisces"]:
        questions.append({
            "id":      "relationship_venus_dasha",
            "question": (
                "Your chart has a very active Venus energy right now. "
                "Are you navigating this in a relationship, or is this "
                "energy looking for somewhere to go?"
            ),
            "reason":  "Venus dasha or exalted Venus active",
            "options": [
                {"label": "In a relationship",     "value": "in_relationship",  "patra": {"marital_status": "in_relationship"}},
                {"label": "Married",               "value": "married",          "patra": {"marital_status": "married"}},
                {"label": "Single — ready",        "value": "single",           "patra": {"marital_status": "single"}},
                {"label": "It's complicated",      "value": "separated",        "patra": {"marital_status": "separated"}},
                {"label": "Recently out of one",   "value": "divorced",         "patra": {"marital_status": "divorced"}},
            ],
            "extracts": ["marital_status"],
        })

    elif moon_sign in ["Cancer", "Scorpio", "Pisces"] or vim_dasha == "Moon":
        questions.append({
            "id":      "relationship_moon_dasha",
            "question": (
                "Your Moon is in a deeply feeling sign. "
                "Is this emotional depth being channelled through "
                "a close partnership right now?"
            ),
            "reason":  "Emotional moon sign or Moon dasha",
            "options": [
                {"label": "Yes — in a relationship",  "value": "in_relationship", "patra": {"marital_status": "in_relationship"}},
                {"label": "Yes — married",            "value": "married",         "patra": {"marital_status": "married"}},
                {"label": "No — processing solo",     "value": "single",          "patra": {"marital_status": "single"}},
                {"label": "Going through a split",    "value": "separated",       "patra": {"marital_status": "separated"}},
            ],
            "extracts": ["marital_status"],
        })

    else:
        questions.append({
            "id":      "relationship_general",
            "question": (
                "To give you the most relevant reading — "
                "are you navigating life as a solo person right now, "
                "or within a partnership?"
            ),
            "reason":  "General relationship status needed",
            "options": [
                {"label": "Solo",                 "value": "single",           "patra": {"marital_status": "single"}},
                {"label": "In a relationship",    "value": "in_relationship",  "patra": {"marital_status": "in_relationship"}},
                {"label": "Married",              "value": "married",          "patra": {"marital_status": "married"}},
                {"label": "Separated / Divorced", "value": "divorced",         "patra": {"marital_status": "divorced"}},
                {"label": "Widowed",              "value": "widowed",          "patra": {"marital_status": "widowed"}},
            ],
            "extracts": ["marital_status"],
        })

    # ── CHILDREN questions ────────────────────────────────────────
    # Triggered by: Jupiter dasha (children's karaka), 5th house,
    # or user is in householder life stage

    if vim_dasha == "Jupiter":
        questions.append({
            "id":      "children_jupiter_dasha",
            "question": (
                "Jupiter is your active planet right now — "
                "this is the planet of children, wisdom, and expansion. "
                "Is Jupiter blessing you through children already, "
                "or is this energy still building?"
            ),
            "reason":  "Jupiter dasha active — 5th house themes prominent",
            "options": [
                {"label": "I have young children",     "value": "young_children",        "patra": {"children_status": "young_children"}},
                {"label": "My children are older",     "value": "older_children",        "patra": {"children_status": "older_children"}},
                {"label": "Expecting a child",         "value": "expecting",             "patra": {"children_status": "expecting"}},
                {"label": "Hoping for children",       "value": "no_children_wants",     "patra": {"children_status": "no_children_wants"}},
                {"label": "Not the path I'm on",       "value": "no_children_by_choice", "patra": {"children_status": "no_children_by_choice"}},
            ],
            "extracts": ["children_status"],
        })

    elif jupiter.get("sign") in ["Cancer", "Pisces", "Sagittarius"]:
        questions.append({
            "id":      "children_strong_jupiter",
            "question": (
                "You have a very strong Jupiter in your chart — "
                "Jupiter rules children and family legacy. "
                "Has Jupiter's energy around family already manifested "
                "for you, or is it still ahead?"
            ),
            "reason":  "Strong Jupiter placement",
            "options": [
                {"label": "Yes — I have children",     "value": "young_children",    "patra": {"children_status": "young_children"}},
                {"label": "Children are grown",        "value": "adult_children",    "patra": {"children_status": "adult_children"}},
                {"label": "Expecting soon",            "value": "expecting",         "patra": {"children_status": "expecting"}},
                {"label": "Still ahead for me",        "value": "no_children_wants", "patra": {"children_status": "no_children_wants"}},
                {"label": "Probably not my path",      "value": "no_children_by_choice", "patra": {"children_status": "no_children_by_choice"}},
            ],
            "extracts": ["children_status"],
        })

    # ── CAREER questions ──────────────────────────────────────────
    # Triggered by: Saturn dasha, Mercury dasha, Sun placement, Rahu

    if vim_dasha == "Saturn":
        questions.append({
            "id":      "career_saturn_dasha",
            "question": (
                "Saturn is your active planet — it's asking you to "
                "build something real and lasting. "
                "Is Saturn applying this pressure to an established career, "
                "or is it helping you figure out what to build?"
            ),
            "reason":  "Saturn dasha — career restructuring themes",
            "options": [
                {"label": "I'm established — refining",  "value": "senior_career",  "patra": {"career_stage": "senior_career"}},
                {"label": "Mid-career — pushing forward", "value": "mid_career",    "patra": {"career_stage": "mid_career"}},
                {"label": "Building my own thing",       "value": "entrepreneur",   "patra": {"career_stage": "entrepreneur"}},
                {"label": "In transition — figuring it out", "value": "transition", "patra": {"career_stage": "transition"}},
                {"label": "Early in my path",            "value": "early_career",   "patra": {"career_stage": "early_career"}},
                {"label": "Retired",                     "value": "retired",        "patra": {"career_stage": "retired"}},
            ],
            "extracts": ["career_stage"],
        })

    elif vim_dasha == "Rahu":
        questions.append({
            "id":      "career_rahu_dasha",
            "question": (
                "Rahu is hungry and ambitious in your chart right now. "
                "Is this ambition pointed at your own venture, "
                "climbing inside an organization, or something you're "
                "still discovering?"
            ),
            "reason":  "Rahu dasha — ambition and foreign themes",
            "options": [
                {"label": "My own business / startup",   "value": "entrepreneur",   "patra": {"career_stage": "entrepreneur"}},
                {"label": "Corporate — climbing",        "value": "mid_career",     "patra": {"career_stage": "mid_career"}},
                {"label": "Senior leadership",           "value": "senior_career",  "patra": {"career_stage": "senior_career"}},
                {"label": "Creative / independent",      "value": "creative",       "patra": {"career_stage": "creative"}},
                {"label": "Still discovering",           "value": "transition",     "patra": {"career_stage": "transition"}},
                {"label": "Studying / preparing",        "value": "student",        "patra": {"career_stage": "student"}},
            ],
            "extracts": ["career_stage"],
        })

    elif vim_dasha in ["Sun", "Mercury"]:
        questions.append({
            "id":      "career_sun_mercury",
            "question": (
                "Your chart is pointing strongly toward your professional world. "
                "Where would you say you are in your work life right now?"
            ),
            "reason":  "Sun or Mercury dasha — professional themes",
            "options": [
                {"label": "Just starting out",       "value": "early_career",   "patra": {"career_stage": "early_career"}},
                {"label": "Established professional", "value": "mid_career",    "patra": {"career_stage": "mid_career"}},
                {"label": "Running my own business",  "value": "entrepreneur",  "patra": {"career_stage": "entrepreneur"}},
                {"label": "Senior / leadership",      "value": "senior_career", "patra": {"career_stage": "senior_career"}},
                {"label": "Creative path",            "value": "creative",      "patra": {"career_stage": "creative"}},
                {"label": "In transition",            "value": "transition",    "patra": {"career_stage": "transition"}},
            ],
            "extracts": ["career_stage"],
        })

    # ── FINANCIAL questions ───────────────────────────────────────
    # Triggered by: 2nd/11th house lord, Venus, Jupiter conditions

    if vim_dasha in ["Venus", "Jupiter"]:
        questions.append({
            "id":      "financial_abundance_dasha",
            "question": (
                "This is typically an expansive period financially. "
                "Is the expansion you're sensing building on an already "
                "stable foundation, or are you working to establish that "
                "foundation first?"
            ),
            "reason":  "Venus or Jupiter dasha — financial expansion themes",
            "options": [
                {"label": "Already stable — growing",   "value": "growing",    "patra": {"financial_status": "growing"}},
                {"label": "Stable — protecting it",     "value": "stable",     "patra": {"financial_status": "stable"}},
                {"label": "Building toward stability",  "value": "debt",       "patra": {"financial_status": "debt"}},
                {"label": "Established — legacy focus", "value": "wealthy",    "patra": {"financial_status": "wealthy"}},
                {"label": "In a financial transition",  "value": "transition", "patra": {"financial_status": "transition"}},
            ],
            "extracts": ["financial_status"],
        })

    elif vim_dasha == "Saturn":
        questions.append({
            "id":      "financial_saturn_pressure",
            "question": (
                "Saturn periods often bring financial lessons. "
                "Is Saturn teaching you about building wealth, "
                "protecting it, or recovering after a contraction?"
            ),
            "reason":  "Saturn dasha — financial discipline themes",
            "options": [
                {"label": "Building — working hard",    "value": "stable",     "patra": {"financial_status": "stable"}},
                {"label": "Recovering — rebuilding",    "value": "debt",       "patra": {"financial_status": "debt"}},
                {"label": "Protecting what I have",     "value": "growing",    "patra": {"financial_status": "growing"}},
                {"label": "In transition financially",  "value": "transition", "patra": {"financial_status": "transition"}},
            ],
            "extracts": ["financial_status"],
        })

    # ── HEALTH questions ──────────────────────────────────────────
    # Only triggered if Saturn, Mars, or Ketu are active
    # (not asked if no health signals — too intrusive otherwise)

    ketu_dasha = vim_dasha == "Ketu"
    mars_afflicted = mars.get("sign") in ["Cancer", "Gemini"]
    saturn_dasha = vim_dasha == "Saturn"

    if ketu_dasha or saturn_dasha or mars_afflicted:
        questions.append({
            "id":      "health_saturn_ketu",
            "question": (
                "Saturn and Ketu periods often ask us to pay attention "
                "to the body. Is your physical energy something you're "
                "working with or working around right now?"
            ),
            "reason":  "Saturn/Ketu dasha or Mars affliction — health awareness",
            "options": [
                {"label": "Strong — no concerns",          "value": "excellent",      "patra": {"health_status": "excellent"}},
                {"label": "Managing something minor",      "value": "minor_issues",   "patra": {"health_status": "minor_issues"}},
                {"label": "Living with a chronic thing",   "value": "chronic",        "patra": {"health_status": "chronic"}},
                {"label": "Recovering — rebuilding",       "value": "recovery",       "patra": {"health_status": "recovery"}},
                {"label": "Emotional / mental health",     "value": "mental_health",  "patra": {"health_status": "mental_health"}},
            ],
            "extracts": ["health_status"],
        })

    return questions


# ── Passive extraction from chat messages ────────────────────────────────────
# The user says things naturally. We extract Patra from what they say.

PASSIVE_PATTERNS = {
    # Relationship signals
    "marital_status": {
        "married": [
            "my wife", "my husband", "my spouse", "we got married",
            "my marriage", "married life", "my partner and i",
        ],
        "in_relationship": [
            "my boyfriend", "my girlfriend", "my partner", "we've been together",
            "we've been dating", "my significant other",
        ],
        "single": [
            "i'm single", "not in a relationship", "haven't found",
            "looking for love", "i live alone",
        ],
        "divorced": [
            "my divorce", "after my divorce", "i got divorced", "my ex-wife",
            "my ex-husband", "my ex-partner",
        ],
        "widowed": [
            "after i lost my", "my late husband", "my late wife",
            "when my husband passed", "when my wife passed",
        ],
    },

    # Children signals
    "children_status": {
        "young_children": [
            "my kids", "my children", "my toddler", "my baby",
            "my son is", "my daughter is", "school pickup", "daycare",
            "my 3-year-old", "my 5-year-old", "my 7-year-old",
        ],
        "expecting": [
            "pregnant", "expecting a baby", "due in", "we're having a baby",
        ],
        "older_children": [
            "my teenager", "my teen", "my kid is in high school",
            "my son is 15", "my daughter is 17",
        ],
        "adult_children": [
            "my adult kids", "my son is 25", "my daughter got married",
            "my grandkids", "my grandchildren", "i'm a grandparent",
        ],
        "no_children_wants": [
            "want to have kids", "trying to have a baby", "trying to conceive",
            "ivf", "fertility", "we're trying",
        ],
    },

    # Career signals
    "career_stage": {
        "entrepreneur": [
            "my startup", "my business", "i run a", "i own a",
            "my company", "i founded", "my clients", "my agency",
            "i'm a founder", "my team", "my staff",
        ],
        "senior_career": [
            "my team", "my department", "i manage", "i lead",
            "i'm a director", "i'm a vp", "i'm a ceo", "i'm a coo",
            "board meeting", "my reports",
        ],
        "student": [
            "i'm studying", "in college", "at university", "my degree",
            "my thesis", "my exams", "grad school",
        ],
        "transition": [
            "between jobs", "just quit", "left my job", "laid off",
            "career change", "switching fields", "figuring out what's next",
        ],
        "creative": [
            "my art", "my music", "i'm a writer", "my film", "my design",
            "my photography", "creative work",
        ],
        "retired": [
            "i'm retired", "after retirement", "since i retired",
            "my pension", "i used to work",
        ],
    },

    # Financial signals
    "financial_status": {
        "debt": [
            "struggling financially", "in debt", "money is tight",
            "can't afford", "loan repayment", "financial pressure",
        ],
        "growing": [
            "doing well financially", "good income", "growing my wealth",
            "investing", "portfolio", "saving aggressively",
        ],
        "wealthy": [
            "financial freedom", "don't need to work",
            "investment income", "passive income covers",
        ],
    },

    # Health signals
    "health_status": {
        "chronic": [
            "chronic", "diabetes", "hypertension", "autoimmune",
            "thyroid", "my condition", "managing my health",
        ],
        "recovery": [
            "recovering from", "after my surgery", "post-surgery",
            "healing from", "rehab", "physical therapy",
        ],
        "mental_health": [
            "anxiety", "depression", "therapy", "my therapist",
            "mental health", "panic attacks", "burnout",
        ],
    },
}


def extract_patra_from_text(text: str) -> dict:
    """
    Passively extract Patra fields from anything the user types.
    Called on every message in the chat.

    Returns dict of extracted fields (only those found, not all).
    Example: {"marital_status": "married", "career_stage": "entrepreneur"}
    """
    text_lower = text.lower()
    extracted = {}

    for field, value_patterns in PASSIVE_PATTERNS.items():
        for value, patterns in value_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    extracted[field] = value
                    break  # first match wins for this field
            if field in extracted:
                break   # don't overwrite with a weaker match

    return extracted


# ── Onboarding conversational flow ───────────────────────────────────────────

def get_onboarding_conversation(chart_data: dict, dashas: dict) -> list[dict]:
    """
    Returns a short guided conversation for onboarding.
    Max 3 questions. Feels like a consultation, not a form.

    Each message has:
      type: "message" | "question"
      content: the text shown
      question_id: for questions, the ID
      options: for questions, the tap options
    """
    questions = get_smart_patra_questions(chart_data, dashas)

    lagna     = chart_data["lagna"]["sign"]
    vim_dasha = dashas.get("vimsottari", [{}])[0].get("lord_or_sign", "")
    vim_end   = dashas.get("vimsottari", [{}])[0].get("end", "")

    # Opening message
    flow = [
        {
            "type":    "message",
            "content": (
                f"Your chart is calculated. Before I give you your first reading, "
                f"let me ask you three quick things. "
                f"The more I understand about your life right now, "
                f"the more specific I can be."
            ),
        }
    ]

    # Add up to 3 chart-driven questions
    for i, q in enumerate(questions[:3]):
        if i > 0:
            flow.append({
                "type":    "message",
                "content": "Good. One more:",
            })
        flow.append({
            "type":       "question",
            "content":    q["question"],
            "question_id": q["id"],
            "options":    q["options"],
            "extracts":   q["extracts"],
        })

    # Closing before first reading
    flow.append({
        "type":    "message",
        "content": (
            f"Perfect. That helps me understand where you are in your life. "
            f"You're currently in your {vim_dasha} period. "
            f"Let me show you what that means for you specifically."
        ),
    })

    return flow


# ── Frontend prompt for Emergent + Lovable ───────────────────────────────────

FRONTEND_DKP_PROMPT = """
Replace the static Patra form with a smart conversational system.

RULE: The app never shows a form with demographic questions.
The questions come from the chart and feel like a consultation.

═══ WHERE PATRA COLLECTION HAPPENS ═══

1. ONBOARDING — after the Proof Loop revelation screen
   
   Before navigating to the dashboard, show a brief conversation:
   
   This is NOT a form. It's a chat-style flow with:
   - A message from Antar
   - A question with tap-to-select options (max 5 options)
   - After each answer, Antar acknowledges it and asks the next
   - Max 3 questions total
   - Always ends with Antar saying something specific about the chart
   
   Get questions from: GET /api/v1/predict/patra-onboarding
   (pass chart_id — backend returns chart-specific questions)
   
   Example flow:
   
   [Antar message bubble]
   "Your chart is calculated. Before I give you your first reading,
    let me ask you three quick things."
   
   [Antar question bubble + tap options]
   "Jupiter is very active in your chart right now — this is the 
    planet of expansion and family. Is Jupiter's energy already 
    blessing you through children, or is that energy still building?"
   
   [User taps: "I have young children"]
   
   [Antar acknowledge + next question]
   "That's significant — Jupiter with young children creates a very 
    specific kind of expansion. One more thing..."
   
   This takes 60 seconds. Feels like talking to someone wise, 
   not filling out a form.

2. PROFILE TAB — "Your Life Context" section (after patra_complete = false)
   
   Show a single card:
   "Help Antar understand your life better"
   "Your predictions become 3x more personal."
   [Start 60-second setup] button
   
   Tapping this opens the same conversational flow as onboarding
   (if user skipped it) or shows current answers if already done.
   
   If patra_complete = true: show a subtle summary card:
   "You are in your [life_stage] · [marital] · [career]"
   Tap to edit any answer.

3. PASSIVE EXTRACTION — always running in the background
   
   Every message the user sends to AI Chat gets analyzed for 
   Patra signals.
   
   If the user says "my wife and I are looking at schools for 
   our 5-year-old" — the system silently extracts:
     marital_status = "married"
     children_status = "young_children"
   
   Frontend receives extracted fields in the predict API response
   under: patra_updates: { marital_status: "married", ... }
   
   When patra_updates is non-empty:
   → silently call POST /api/v1/user/patra with the updates
   → no notification to the user
   → next prediction will automatically be more personalized
   
   After 3+ passive extractions: show a gentle notification:
   "Antar is getting to know you. Your readings are becoming
    more personal." (then dismiss automatically after 3 seconds)

4. LIFE EVENTS — the richest source of Patra data
   
   When a user logs a life event, extract Patra automatically:
   
   Event type: "marriage" → marital_status = "married"
   Event type: "birth_of_child" → children_status = "young_children"  
   Event type: "started_business" → career_stage = "entrepreneur"
   Event type: "retirement" → career_stage = "retired"
   Event type: "diagnosis" → health_status = "chronic"
   
   No question asked. Just update silently.

═══ NEW API ENDPOINT NEEDED ═══

GET /api/v1/predict/patra-onboarding?chart_id={chart_id}

Returns:
{
  "conversation": [
    { "type": "message", "content": "..." },
    { 
      "type": "question", 
      "content": "...",
      "question_id": "...",
      "options": [
        { "label": "...", "value": "...", "patra": {...} }
      ]
    }
  ]
}

The backend generates chart-specific questions using 
patra_conversation.get_onboarding_conversation()

═══ PATRA UPDATES IN PREDICT RESPONSE ═══

The /predict response now returns an optional field:
  patra_updates: { field: value, ... }

When this is non-null and non-empty:
→ call POST /api/v1/user/patra silently in background
→ no UI change, no message to user
→ the next prediction will use the updated context

═══ THE ONLY RULE ═══

The user should never feel like they're filling out a form.
They should feel like Antar is paying attention to their life.
"""
