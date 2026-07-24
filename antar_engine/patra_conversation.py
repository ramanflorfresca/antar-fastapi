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

# [patra-catalog] single source of truth for question copy (en/es, dejargoned)
from antar_engine.patra_catalog import render_question


# ── Chart-driven question triggers ────────────────────────────────────────────
# Each trigger looks at chart conditions and generates a natural question.
# The answer extracts one or more Patra fields.

def get_smart_patra_questions(
    chart_data: dict,
    dashas: dict,
    language: Optional[str] = "en",
) -> list[dict]:
    """
    Generate chart-specific onboarding questions, rendered in the caller's
    language from antar_engine.patra_catalog.

    Branching logic (which question fires for whom) stays here — it reads
    the chart.  All USER-FACING copy lives in patra_catalog.PATRA_QUESTIONS
    and is dejargoned + localized (en/es) there.

    Returns a list of question dicts in the shape the frontend expects:
        {id, question, reason, options[{label, value, patra}], extracts}

    `language` defaults to "en"; "es" returns Spanish strings.  Unknown
    language codes fall back to English inside render_question().
    """
    questions: list[dict] = []

    lagna      = chart_data["lagna"]["sign"]
    moon_sign  = chart_data["planets"]["Moon"]["sign"]
    # (moon_nak kept available in case future branches need it)
    moon_nak   = chart_data["planets"]["Moon"].get("nakshatra", "")
    vim_dasha  = dashas.get("vimsottari", [{}])[0].get("lord_or_sign", "")
    jai_dasha  = dashas.get("jaimini",    [{}])[0].get("lord_or_sign", "")

    planets    = chart_data["planets"]
    venus      = planets.get("Venus",   {})
    jupiter    = planets.get("Jupiter", {})
    saturn     = planets.get("Saturn",  {})
    mars       = planets.get("Mars",    {})
    sun        = planets.get("Sun",     {})
    moon       = planets.get("Moon",    {})

    def _emit(qid: str) -> None:
        q = render_question(qid, language)
        if q:
            questions.append(q)

    # ── RELATIONSHIP ─────────────────────────────────────────────
    if vim_dasha == "Venus" or venus.get("sign") in ["Libra", "Taurus", "Pisces"]:
        _emit("relationship_venus_dasha")
    elif moon_sign in ["Cancer", "Scorpio", "Pisces"] or vim_dasha == "Moon":
        _emit("relationship_moon_dasha")
    else:
        _emit("relationship_general")

    # ── CHILDREN ─────────────────────────────────────────────────
    if vim_dasha == "Jupiter":
        _emit("children_jupiter_dasha")
    elif jupiter.get("sign") in ["Cancer", "Pisces", "Sagittarius"]:
        _emit("children_strong_jupiter")

    # ── CAREER ───────────────────────────────────────────────────
    if vim_dasha == "Saturn":
        _emit("career_saturn_dasha")
    elif vim_dasha == "Rahu":
        _emit("career_rahu_dasha")
    elif vim_dasha in ["Sun", "Mercury"]:
        _emit("career_sun_mercury")

    # ── FINANCIAL ────────────────────────────────────────────────
    if vim_dasha in ["Venus", "Jupiter"]:
        _emit("financial_abundance_dasha")
    elif vim_dasha == "Saturn":
        _emit("financial_saturn_pressure")

    # ── HEALTH ───────────────────────────────────────────────────
    # Only triggered if Saturn, Mars, or Ketu are active (too intrusive otherwise).
    ketu_dasha      = vim_dasha == "Ketu"
    mars_afflicted  = mars.get("sign") in ["Cancer", "Gemini"]
    saturn_dasha    = vim_dasha == "Saturn"
    if ketu_dasha or saturn_dasha or mars_afflicted:
        _emit("health_saturn_ketu")

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

# [i18n] framing copy for the patra onboarding flow.  Framing-only —
# the chart-driven questions themselves still live in get_smart_patra_questions()
# and are English-only as of 2026-04-22 (see patch_patra_framing_language.py).
# The CLOSING message deliberately does NOT reference the dasha planet name
# (e.g. "Saturn period") — that violated project rule #12 (no Sanskrit /
# astrological jargon in user-facing text).  The jargon-free phrasing still
# lands the "this moment" beat.
_PATRA_FRAMING = {
    "en": {
        "opening": (
            "Your chart is calculated. Before I give you your first reading, "
            "let me ask you three quick things. "
            "The more I understand about your life right now, "
            "the more specific I can be."
        ),
        "interstitial": "Good. One more:",
        "closing": (
            "Perfect. That helps me understand where you are in your life. "
            "Let me show you what your chart says about this moment for you specifically."
        ),
    },
    "es": {
        "opening": (
            "Tu carta está calculada. Antes de darte tu primera lectura, "
            "déjame hacerte tres preguntas rápidas. "
            "Cuanto más entienda sobre tu vida ahora mismo, "
            "más específico puedo ser."
        ),
        "interstitial": "Bien. Una más:",
        "closing": (
            "Perfecto. Eso me ayuda a entender dónde estás en tu vida. "
            "Déjame mostrarte lo que tu carta dice sobre este momento para ti en específico."
        ),
    },
}


def _patra_framing(language: Optional[str]) -> dict:
    """Pick the framing strings for en/es.  Defaults to English."""
    code = (language or "en").lower()[:2]
    return _PATRA_FRAMING.get(code) or _PATRA_FRAMING["en"]


def get_onboarding_conversation(
    chart_data: dict,
    dashas: dict,
    language: Optional[str] = "en",
) -> list[dict]:
    """
    Returns a short guided conversation for onboarding.
    Max 3 questions. Feels like a consultation, not a form.

    Each message has:
      type: "message" | "question"
      content: the text shown
      question_id: for questions, the ID
      options: for questions, the tap options

    `language` controls the framing messages only.  The chart-driven
    question bodies in get_smart_patra_questions() are still English-only
    and will be localized in a separate pass.
    """
    questions = get_smart_patra_questions(chart_data, dashas, language=language)
    framing = _patra_framing(language)

    # Opening message
    flow = [
        {
            "type":    "message",
            "content": framing["opening"],
        }
    ]

    # Add up to 3 chart-driven questions
    for i, q in enumerate(questions[:3]):
        if i > 0:
            flow.append({
                "type":    "message",
                "content": framing["interstitial"],
            })
        flow.append({
            "type":       "question",
            "content":    q["question"],
            "question_id": q["id"],
            "options":    q["options"],
            "extracts":   q["extracts"],
        })

    # Closing before first reading — jargon-free (no dasha planet name)
    flow.append({
        "type":    "message",
        "content": framing["closing"],
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
