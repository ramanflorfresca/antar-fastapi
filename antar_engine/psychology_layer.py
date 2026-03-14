"""
antar_engine/psychology_layer.py
Psychological profiling from natal chart for deeper predictions.
Age-aware, gender-aware, archetype-aware.
"""
from datetime import date

# Soul archetype from Atmakaraka
SOUL_ARCHETYPES = {
    "Sun":     {
        "archetype":    "The Leader",
        "core_drive":   "impact, recognition, legacy",
        "shadow":       "ego, need for approval, burnout",
        "gift":         "vision, authority, inspiration",
        "framing":      "You are here to lead and be seen. Your pattern asks: are you building something that outlasts you?",
    },
    "Moon":    {
        "archetype":    "The Nurturer",
        "core_drive":   "connection, belonging, emotional truth",
        "shadow":       "people-pleasing, emotional overwhelm, codependency",
        "gift":         "empathy, intuition, emotional intelligence",
        "framing":      "You are here to connect and nourish. Your pattern asks: are you filling others from a full cup or an empty one?",
    },
    "Mercury": {
        "archetype":    "The Thinker",
        "core_drive":   "understanding, mastery, communication",
        "shadow":       "overthinking, analysis paralysis, scattered focus",
        "gift":         "intelligence, adaptability, teaching",
        "framing":      "You are here to understand and communicate. Your pattern asks: are you sharing what you know or hoarding it?",
    },
    "Venus":   {
        "archetype":    "The Harmonizer",
        "core_drive":   "beauty, love, connection, abundance",
        "shadow":       "people-pleasing, avoidance of conflict, over-giving",
        "gift":         "aesthetics, diplomacy, magnetism",
        "framing":      "You are here to create beauty and harmony. Your pattern asks: are you choosing ease or are you choosing truth?",
    },
    "Mars":    {
        "archetype":    "The Warrior",
        "core_drive":   "action, achievement, courage, protection",
        "shadow":       "aggression, impatience, burnout from overdoing",
        "gift":         "energy, initiative, bold action",
        "framing":      "You are here to act and protect. Your pattern asks: are you fighting for what matters or fighting out of habit?",
    },
    "Jupiter": {
        "archetype":    "The Teacher",
        "core_drive":   "wisdom, expansion, meaning, faith",
        "shadow":       "overconfidence, excess, preachiness",
        "gift":         "generosity, optimism, teaching",
        "framing":      "You are here to expand and teach. Your pattern asks: are you growing or just accumulating?",
    },
    "Saturn":  {
        "archetype":    "The Builder",
        "core_drive":   "structure, legacy, mastery through patience",
        "shadow":       "fear, limitation, excessive control",
        "gift":         "discipline, endurance, wisdom through experience",
        "framing":      "You are here to build what lasts. Your pattern asks: are you building from fear or from purpose?",
    },
    "Rahu":    {
        "archetype":    "The Explorer",
        "core_drive":   "novelty, ambition, breaking limits, the new",
        "shadow":       "obsession, illusion, restlessness, addiction",
        "gift":         "innovation, courage to cross boundaries",
        "framing":      "You are here to explore what others won't. Your pattern asks: are you chasing the new because it serves you, or to escape the now?",
    },
    "Ketu":    {
        "archetype":    "The Mystic",
        "core_drive":   "liberation, depth, spiritual truth, letting go",
        "shadow":       "detachment, isolation, nihilism",
        "gift":         "spiritual depth, non-attachment, past-life wisdom",
        "framing":      "You are here to release and liberate. Your pattern asks: what are you still holding that your soul is ready to let go?",
    },
}

# Life stage psychological context (Erikson + Vedic Ashrama)
LIFE_STAGE_PSYCHOLOGY = {
    "Brahmacharya": {  # 0-25: Student stage
        "age_range":     (0, 25),
        "stage_name":    "Formation",
        "erikson_stage": "Identity vs Role Confusion",
        "core_question": "Who am I and what do I stand for?",
        "psychological_needs": [
            "Identity formation — finding your own values",
            "Breaking from parental patterns",
            "First real-world testing of self",
        ],
        "saturn_context": "Pre-Saturn return — building raw material",
        "prediction_lens": (
            "This person is in identity formation. "
            "Frame predictions as: 'who you are becoming' not 'who you are.' "
            "Emphasize potential and building blocks, not fixed outcomes."
        ),
    },
    "Grihastha": {  # 25-50: Householder stage
        "age_range":     (25, 50),
        "stage_name":    "Building",
        "erikson_stage": "Generativity vs Stagnation",
        "core_question": "Am I building something that matters?",
        "psychological_needs": [
            "Achievement and contribution",
            "Relationship depth and commitment",
            "Career and financial establishment",
        ],
        "saturn_context": "Between Saturn returns — maximum building energy",
        "prediction_lens": (
            "This person is in peak building phase. "
            "Frame predictions around: building, establishing, contributing. "
            "Practical, actionable, specific to their current domain."
        ),
    },
    "Vanaprastha": {  # 50-75: Forest dweller / wisdom stage
        "age_range":     (50, 75),
        "stage_name":    "Mastery",
        "erikson_stage": "Integrity vs Despair",
        "core_question": "Has my life meant something?",
        "psychological_needs": [
            "Legacy and meaning-making",
            "Passing wisdom to next generation",
            "Deepening rather than broadening",
        ],
        "saturn_context": "Post-second Saturn return — legacy crystallization",
        "prediction_lens": (
            "This person is in wisdom and legacy phase. "
            "Frame predictions around: meaning, legacy, depth, refinement. "
            "Less about building new, more about what endures."
        ),
    },
    "Sannyasa": {  # 75+: Renunciation / liberation
        "age_range":     (75, 120),
        "stage_name":    "Liberation",
        "erikson_stage": "Integrity",
        "core_question": "What is truly essential?",
        "psychological_needs": [
            "Spiritual completion",
            "Release of worldly attachment",
            "Peace and acceptance",
        ],
        "saturn_context": "Third Saturn return territory — deep karma resolution",
        "prediction_lens": (
            "This person is in liberation phase. "
            "Frame predictions with spiritual depth and acceptance. "
            "Focus on inner peace, completion, and legacy."
        ),
    },
}

# Saturn return awareness
SATURN_RETURN_CONTEXT = {
    "first_return": {
        "age_range": (27, 30),
        "meaning": "First Saturn return — identity restructuring",
        "what_happens": (
            "Everything built on an inauthentic foundation "
            "is restructured now. Career, relationships, identity — "
            "Saturn tests what is real."
        ),
        "prediction_note": (
            "This person is in their first Saturn return. "
            "Whatever feels like it is 'falling apart' is actually "
            "being rebuilt on a truer foundation. Frame disruption as correction."
        ),
    },
    "between_returns": {
        "age_range": (30, 58),
        "meaning": "Productive building phase",
        "what_happens": "Peak output and contribution window",
        "prediction_note": "Full building capacity active.",
    },
    "second_return": {
        "age_range": (58, 61),
        "meaning": "Second Saturn return — legacy crystallization",
        "what_happens": (
            "What have you actually built? "
            "Saturn demands accounting and authentic legacy."
        ),
        "prediction_note": (
            "This person is in their second Saturn return. "
            "Frame predictions around legacy, authenticity, and "
            "what truly matters vs what was obligation."
        ),
    },
}

# Gender-aware prediction framing
GENDER_PREDICTION_LENS = {
    "female": {
        "general_note": (
            "Frame predictions with awareness that this person "
            "may navigate societal expectations around gender, family pressure, "
            "and work-life balance differently. "
            "Acknowledge these forces explicitly when relevant — "
            "do not pretend they don't exist."
        ),
        "career_lens": (
            "Career predictions for women: acknowledge that 'timing' "
            "windows may interact with family planning decisions. "
            "Be specific about windows without being prescriptive."
        ),
        "relationship_lens": (
            "Relationship predictions: acknowledge that societal "
            "expectations around marriage timing may create pressure. "
            "Frame their chart's natural timing as their truth — "
            "not society's timeline."
        ),
    },
    "male": {
        "general_note": (
            "Frame predictions with awareness that this person "
            "may carry pressure around financial provision, "
            "status, and stoicism. "
            "Acknowledge these patterns when the chart shows "
            "emotional or vulnerability signals."
        ),
        "career_lens": "Standard career framing applies.",
        "relationship_lens": (
            "Relationship predictions for men: acknowledge that "
            "vulnerability and emotional expression may be "
            "undervalued. Frame emotional intelligence as "
            "a strength signal in the chart."
        ),
    },
    "non-binary": {
        "general_note": (
            "Frame predictions without binary gender assumptions. "
            "Use 'they/them' energy language. "
            "Focus on the chart's pure archetypal energies "
            "without gender overlay."
        ),
        "career_lens":       "Standard framing, remove gender assumptions.",
        "relationship_lens": "Frame around connection and authenticity, not roles.",
    },
}


def get_psychology_profile(
    chart_data: dict,
    birth_date: str,
    gender: str = "unknown",
    concern: str = "general",
) -> dict:
    """
    Build psychological profile for prediction personalization.
    Pure calculation — no user input beyond chart data.
    """
    # Calculate age
    try:
        born = date.fromisoformat(birth_date[:10])
        today = date.today()
        age = today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )
    except Exception:
        age = 35  # default

    # Get Atmakaraka (soul signal) — highest degree planet
    planets = chart_data.get("planets", {})
    ak_planet = "Sun"
    max_deg = 0
    for planet, data in planets.items():
        if planet in ("Rahu", "Ketu"):
            continue
        deg = data.get("degree", 0) or data.get("longitude", 0) % 30
        if deg > max_deg:
            max_deg = deg
            ak_planet = planet

    # Get life stage
    life_stage_key = "Grihastha"
    life_stage_data = {}
    for key, stage in LIFE_STAGE_PSYCHOLOGY.items():
        lo, hi = stage["age_range"]
        if lo <= age < hi:
            life_stage_key = key
            life_stage_data = stage
            break

    # Check Saturn return
    saturn_context = ""
    for _, sr in SATURN_RETURN_CONTEXT.items():
        lo, hi = sr["age_range"]
        if lo <= age <= hi:
            saturn_context = sr["prediction_note"]
            break

    # Soul archetype
    archetype = SOUL_ARCHETYPES.get(ak_planet, SOUL_ARCHETYPES["Sun"])

    # Gender lens
    gender_lower = gender.lower() if gender else "unknown"
    if "female" in gender_lower or gender_lower in ("f", "woman", "women"):
        gender_key = "female"
    elif "male" in gender_lower or gender_lower in ("m", "man", "men"):
        gender_key = "male"
    elif "non" in gender_lower or "binary" in gender_lower:
        gender_key = "non-binary"
    else:
        gender_key = "male"  # default neutral

    gender_lens = GENDER_PREDICTION_LENS.get(gender_key, {})

    return {
        "age":              age,
        "atmakaraka":       ak_planet,
        "archetype":        archetype.get("archetype", ""),
        "core_drive":       archetype.get("core_drive", ""),
        "archetype_shadow": archetype.get("shadow", ""),
        "archetype_gift":   archetype.get("gift", ""),
        "archetype_framing":archetype.get("framing", ""),
        "life_stage":       life_stage_data.get("stage_name", "Building"),
        "life_stage_lens":  life_stage_data.get("prediction_lens", ""),
        "core_question":    life_stage_data.get("core_question", ""),
        "saturn_context":   saturn_context,
        "gender_note":      gender_lens.get("general_note", ""),
        "gender_career":    gender_lens.get("career_lens", ""),
        "gender_relation":  gender_lens.get("relationship_lens", ""),
    }


def psychology_prompt_block(psych: dict, concern: str = "general") -> str:
    """Format psychology profile into LLM prompt block."""
    if not psych:
        return ""

    saturn_note = f"\nSATURN RETURN CONTEXT: {psych['saturn_context']}" \
                  if psych.get("saturn_context") else ""

    gender_note = f"\nGENDER AWARENESS: {psych.get('gender_note','')}" \
                  if psych.get("gender_note") else ""

    concern_gender = ""
    if concern == "career" and psych.get("gender_career"):
        concern_gender = f"\nCAREER GENDER LENS: {psych['gender_career']}"
    elif concern in ("love","marriage","divorce") and psych.get("gender_relation"):
        concern_gender = f"\nRELATIONSHIP GENDER LENS: {psych['gender_relation']}"

    return f"""
=== PSYCHOLOGICAL PROFILE (use to deepen predictions) ===

AGE: {psych.get('age')} years old
LIFE STAGE: {psych.get('life_stage')} — {psych.get('core_question','')}
SOUL ARCHETYPE: {psych.get('archetype','')} — driven by {psych.get('core_drive','')}
ARCHETYPE FRAMING: {psych.get('archetype_framing','')}
SHADOW TO WATCH: {psych.get('archetype_shadow','')}
GIFT TO AMPLIFY: {psych.get('archetype_gift','')}

LIFE STAGE PREDICTION LENS:
{psych.get('life_stage_lens','')}
{saturn_note}
{gender_note}
{concern_gender}

INSTRUCTIONS:
- Reference the soul archetype subtly in section 3 (soul level data)
- Frame the prediction through the life stage lens
- Age {psych.get('age')} means: {psych.get('life_stage','')} energy is dominant
- DO NOT say "you are a [archetype] archetype" — translate to experience language
- DO NOT mention Atmakaraka by name — say "your soul's core signal"
- The prediction should feel written for a {psych.get('age')}-year-old specifically

=== END PSYCHOLOGICAL PROFILE ===
"""
