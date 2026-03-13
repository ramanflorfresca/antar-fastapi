"""
antar_engine/patra.py

PATRA — Life Circumstances Engine
────────────────────────────────────────────────────────────────────
Patra = the vessel / the person / their current circumstances.

Vedic astrology has always required knowing:
  - Age and life stage (student, householder, vanaprastha, sannyasa)
  - Marital status and relationship context
  - Whether children exist (changes Jupiter predictions entirely)
  - Career stage (seeking, building, consolidating, transitioning)
  - Financial context (debt, stable, growing, wealthy)
  - Health concerns (changes Saturn/Mars/Ketu readings)
  - Location history (where they've lived, where they are now)

Without Patra, the same prediction goes to a 22-year-old and
a 55-year-old and means nothing to either.

Usage:
    from antar_engine.patra import build_patra_context, get_life_stage

    patra = build_patra_context(user_profile, chart_data)
    # Returns rich context block for the LLM
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ── Life Stage System ─────────────────────────────────────────────────────────
# Based on traditional ashrama system + modern life stage research

LIFE_STAGES = {
    "brahmacharya":   (0,  25,  "Student & Formation",
                       "Identity forming. Education, first loves, finding direction. "
                       "Jupiter predictions favour learning and discovery. "
                       "Saturn teaches discipline. Rahu pulls toward ambition."),

    "early_householder": (25, 35, "Early Householder",
                       "Building foundations. Career establishing, relationships deepening, "
                       "possibly marriage and first children. Jupiter brings partnership "
                       "and career growth. Saturn tests whether foundations are real."),

    "householder":    (35, 50, "Peak Householder",
                       "Full life engagement. Career at peak, family responsibilities at height, "
                       "financial consolidation. Jupiter expands what already exists. "
                       "Saturn restructures what isn't working. Rahu brings ambition peaks."),

    "consolidation":  (50, 60, "Consolidation",
                       "Harvesting and refining. Career legacy, children leaving home, "
                       "health coming into focus, deeper meaning sought. "
                       "Jupiter brings wisdom and recognition. Saturn brings health lessons. "
                       "Ketu begins its spiritual pull."),

    "vanaprastha":    (60, 75, "Elder & Wisdom",
                       "Withdrawal from peak activity. Grandchildren, spiritual deepening, "
                       "legacy focus. Jupiter brings spiritual authority. "
                       "Ketu brings liberation. Saturn brings clarity about what truly mattered."),

    "sannyasa":       (75, 120, "Elder Sage",
                       "Full withdrawal into the essential. Spiritual completion. "
                       "Every planet's energy turns inward and toward moksha."),
}

# ── Circumstance modifiers ────────────────────────────────────────────────────

MARITAL_CONTEXT = {
    "single":        "Not yet in primary partnership. Venus/7th house themes are prospective. "
                     "Jupiter in Venus dasha = potential marriage window. "
                     "Relationship predictions are about meeting, not maintaining.",

    "in_relationship": "In relationship, not yet married. Partnership themes active. "
                     "7th house and Venus predictions relate to deepening commitment or marriage timing.",

    "married":       "In committed partnership. Venus/7th house themes relate to marriage quality, "
                     "not finding a partner. Jupiter dasha may bring children. "
                     "Saturn tests whether the marriage foundation is real.",

    "separated":     "In marital transition. Saturn and Rahu themes of restructuring are central. "
                     "Venus predictions are about healing, not new romance yet.",

    "divorced":      "Post-marital. Has moved through the Saturn/Rahu restructuring. "
                     "New Venus window may be opening. Independence and self-sufficiency themes.",

    "widowed":       "Has experienced profound loss. Ketu and 8th house themes of transformation "
                     "have been lived. Spiritual depth is elevated. Jupiter brings new meaning.",
}

CHILDREN_CONTEXT = {
    "no_children_wants": "No children yet, desires them. Jupiter dasha predictions should "
                         "include child potential. 5th house themes are anticipatory.",

    "no_children_unsure": "No children. Future open. 5th house predictions are about creative "
                          "output, not just biological children.",

    "no_children_by_choice": "Chosen to not have children. 5th house predictions relate "
                              "to creative legacy, students, passion projects.",

    "expecting":     "Expecting first/subsequent child. Jupiter is highly active. "
                     "5th house is currently manifest. Health of pregnancy is primary concern.",

    "young_children": "Has young children at home. Jupiter's role is active parent. "
                      "Financial and home predictions carry extra weight.",

    "older_children": "Children growing or grown. Transitioning from active parent role. "
                      "Jupiter now relates to wisdom transmission and grandchildren potential.",

    "adult_children": "Children independent. Parental role complete. Jupiter shifts to "
                      "grandchildren, legacy, mentoring others.",
}

CAREER_CONTEXT = {
    "student":       "In education/training. Mercury and Jupiter are primary. "
                     "Career predictions are about direction and first steps.",

    "job_seeking":   "Between roles or seeking first position. Mars activation needed. "
                     "Jupiter opening predictions are highly relevant right now.",

    "early_career":  "0-5 years in field. Building skills and reputation. "
                     "Saturn teaches discipline. Jupiter opens doors. Mercury sharpens tools.",

    "mid_career":    "Established professional. 5-15 years in field. "
                     "Advancement, leadership, and domain mastery are themes.",

    "senior_career": "Senior professional or leader. Influence, legacy, team leadership. "
                     "Saturn consolidates. Jupiter brings recognition.",

    "entrepreneur":  "Running own business. Mars (initiative), Mercury (communication), "
                     "Jupiter (expansion), Saturn (systems) all highly relevant.",

    "creative":      "Creative professional. Venus primary. Mercury for communication. "
                     "Jupiter for recognition and expansion of creative work.",

    "transition":    "In career transition or considering one. Rahu brings new paths. "
                     "Saturn clears what no longer fits. This is a restructuring period.",

    "retired":       "Post-career. Financial stability themes shift to legacy and purpose. "
                     "Jupiter brings wisdom sharing. Saturn brings completion.",
}

HEALTH_CONTEXT = {
    "excellent":     "Strong vitality. Health predictions are preventive and optimizing.",

    "minor_issues":  "Managing minor health matters. Some Saturn or Mars attention needed. "
                     "Health predictions should include maintenance and awareness.",

    "chronic":       "Living with chronic condition. Saturn is a teacher here. "
                     "Health predictions focus on management, energy preservation, "
                     "and finding what supports the body.",

    "recovery":      "In recovery from illness, surgery, or health event. "
                     "Mars and Saturn themes of rebuilding. Jupiter brings healing support.",

    "mental_health": "Navigating mental/emotional health. Moon and Mercury are central. "
                     "Predictions should acknowledge emotional reality. "
                     "Remedies emphasize Moon practices, water, rest.",
}

FINANCIAL_CONTEXT = {
    "debt":          "Managing financial debt or pressure. Saturn themes of discipline. "
                     "Venus/Jupiter predictions about financial relief and rebuilding.",

    "stable":        "Financially stable. Building from a solid base. "
                     "Jupiter predictions about growth. Saturn about protection.",

    "growing":       "Financial trajectory positive and growing. "
                     "Jupiter and Venus themes of expansion are highly active.",

    "wealthy":       "Financial abundance established. Predictions shift to "
                     "legacy, giving, investment, and meaning beyond money.",

    "transition":    "In financial transition (job change, divorce, business change). "
                     "Saturn restructuring + Jupiter opening predictions both relevant.",
}


# ── Life Stage Age Triggers ───────────────────────────────────────────────────
# Key ages in Vedic astrology where life themes shift sharply

AGE_TRIGGERS = {
    # Saturn milestones
    29: "First Saturn return — the great reality check. "
        "Life structures that aren't genuine begin to shake. "
        "This is not punishment — this is Saturn asking: "
        "what are you actually building?",

    36: "Saturn square — mid-career and relationship audit. "
        "What you've built in the first Saturn cycle is being evaluated.",

    58: "Second Saturn return — legacy and final restructuring. "
        "What truly matters becomes undeniably clear.",

    # Jupiter milestones
    24: "First Jupiter return — optimism, opportunity, first major expansion. "
        "Often: first real career opportunity or significant relationship.",

    36: "Second Jupiter return — mid-life expansion. "
        "Often brings marriage, children, or major career advancement.",

    48: "Third Jupiter return — wisdom expansion. "
        "Recognition, teaching, deeper purpose.",

    60: "Fourth Jupiter return — elder wisdom. "
        "Spiritual authority, grandchildren, legacy.",

    # Rahu/Ketu axis (18.6 year cycle)
    18: "Rahu return — identity hunger peaks. Ambition, restlessness, becoming.",
    37: "Ketu return — spiritual pull begins. Questioning what was built.",
    56: "Rahu return — second hunger cycle. Legacy ambition.",
}


# ── Patra Data Class ──────────────────────────────────────────────────────────

@dataclass
class PatraProfile:
    """Complete life circumstances of a person."""

    # Calculated
    age: int
    life_stage_key: str
    life_stage_name: str
    life_stage_description: str
    age_trigger: Optional[str] = None

    # User-provided circumstances
    marital_status: str = "unknown"         # single/in_relationship/married/separated/divorced/widowed
    children_status: str = "no_children_unsure"
    career_stage: str = "mid_career"
    health_status: str = "excellent"
    financial_status: str = "stable"

    # Location history
    birth_country: str = ""
    current_country: str = ""
    lived_abroad: bool = False
    countries_lived: list = field(default_factory=list)

    # Derived context blocks (populated by build_patra_context)
    marital_context: str = ""
    children_context: str = ""
    career_context: str = ""
    health_context: str = ""
    financial_context: str = ""

    # Concern from current question
    primary_concern: str = "general"


# ── Main builder ──────────────────────────────────────────────────────────────

def build_patra_context(
    birth_date: str,
    user_profile: dict,
    primary_concern: str = "general",
) -> PatraProfile:
    """
    Build the complete Patra profile from user data.

    Args:
        birth_date: "YYYY-MM-DD" from chart data
        user_profile: dict from user's profile/preferences in DB
            Keys: marital_status, children_status, career_stage,
                  health_status, financial_status, birth_country,
                  current_country, countries_lived
        primary_concern: detected concern from question

    Returns:
        PatraProfile with all context blocks populated
    """
    # Calculate age
    birth_dt = datetime.strptime(birth_date[:10], "%Y-%m-%d")
    today    = datetime.utcnow()
    age      = today.year - birth_dt.year - (
        (today.month, today.day) < (birth_dt.month, birth_dt.day)
    )

    # Determine life stage
    stage_key, stage_name, stage_desc = _get_life_stage(age)

    # Check age triggers
    age_trigger = None
    for trigger_age, trigger_text in AGE_TRIGGERS.items():
        if abs(age - trigger_age) <= 1:   # within 1 year of trigger
            age_trigger = trigger_text
            break

    patra = PatraProfile(
        age=age,
        life_stage_key=stage_key,
        life_stage_name=stage_name,
        life_stage_description=stage_desc,
        age_trigger=age_trigger,
        marital_status=user_profile.get("marital_status", "unknown"),
        children_status=user_profile.get("children_status", "no_children_unsure"),
        career_stage=user_profile.get("career_stage", "mid_career"),
        health_status=user_profile.get("health_status", "excellent"),
        financial_status=user_profile.get("financial_status", "stable"),
        birth_country=user_profile.get("birth_country", ""),
        current_country=user_profile.get("current_country", ""),
        lived_abroad=user_profile.get("lived_abroad", False),
        countries_lived=user_profile.get("countries_lived", []),
        primary_concern=primary_concern,
    )

    # Populate context blocks
    patra.marital_context   = MARITAL_CONTEXT.get(patra.marital_status, "")
    patra.children_context  = CHILDREN_CONTEXT.get(patra.children_status, "")
    patra.career_context    = CAREER_CONTEXT.get(patra.career_stage, "")
    patra.health_context    = HEALTH_CONTEXT.get(patra.health_status, "")
    patra.financial_context = FINANCIAL_CONTEXT.get(patra.financial_status, "")

    return patra


def patra_to_context_block(patra: PatraProfile) -> str:
    """
    Convert Patra profile to LLM context block.
    Injected into prompt_builder alongside predictions context.
    """
    lines = [
        "═══ PATRA — LIFE CIRCUMSTANCES (filter ALL predictions through this) ═══",
        f"Age: {patra.age} | Life Stage: {patra.life_stage_name}",
        f"Stage context: {patra.life_stage_description}",
    ]

    if patra.age_trigger:
        lines += [
            "",
            f"⚡ AGE TRIGGER ACTIVE: {patra.age_trigger}",
            "This age milestone must be acknowledged in the prediction.",
        ]

    if patra.marital_status != "unknown":
        lines += ["", f"Relationship: {MARITAL_CONTEXT.get(patra.marital_status, '')}"]

    if patra.children_status:
        lines += [f"Children: {CHILDREN_CONTEXT.get(patra.children_status, '')}"]

    if patra.career_stage:
        lines += [f"Career: {CAREER_CONTEXT.get(patra.career_stage, '')}"]

    if patra.health_status and patra.health_status != "excellent":
        lines += [f"Health: {HEALTH_CONTEXT.get(patra.health_status, '')}"]

    if patra.financial_status:
        lines += [f"Financial: {FINANCIAL_CONTEXT.get(patra.financial_status, '')}"]

    if patra.birth_country != patra.current_country and patra.current_country:
        lines += [
            "",
            f"Location: Born in {patra.birth_country}, currently in {patra.current_country}.",
            "This person is living away from their birth country. "
            "Rahu/foreign themes may be relevant. "
            "Astrocartography lines for current location should be considered.",
        ]

    lines += [
        "",
        f"Primary concern: {patra.primary_concern}",
        "",
        "INSTRUCTION: Every prediction must be filtered through these circumstances.",
        "A Jupiter prediction for a 28-year-old single person is completely different",
        "from the same Jupiter prediction for a 45-year-old with three children.",
        "Make it specific to THIS person's actual life situation.",
        "═══ END PATRA ═══",
    ]

    return "\n".join(lines)


def get_circumstance_questions() -> list[dict]:
    """
    Returns the questions to ask users to build their Patra profile.
    Used by frontend for the profile setup / onboarding step 2.
    """
    return [
        {
            "field":    "marital_status",
            "question": "What's your relationship status?",
            "options": [
                {"value": "single",           "label": "Single"},
                {"value": "in_relationship",  "label": "In a relationship"},
                {"value": "married",          "label": "Married"},
                {"value": "separated",        "label": "Separated"},
                {"value": "divorced",         "label": "Divorced"},
                {"value": "widowed",          "label": "Widowed"},
            ],
        },
        {
            "field":    "children_status",
            "question": "What's your situation with children?",
            "options": [
                {"value": "no_children_wants",     "label": "No children yet — hoping to"},
                {"value": "no_children_unsure",    "label": "No children — open to it"},
                {"value": "no_children_by_choice", "label": "No children — by choice"},
                {"value": "expecting",             "label": "Expecting a child"},
                {"value": "young_children",        "label": "Have young children"},
                {"value": "older_children",        "label": "Have older children"},
                {"value": "adult_children",        "label": "Children are grown"},
            ],
        },
        {
            "field":    "career_stage",
            "question": "Where are you in your career?",
            "options": [
                {"value": "student",       "label": "Still studying"},
                {"value": "job_seeking",   "label": "Looking for work"},
                {"value": "early_career",  "label": "Early career (0-5 years)"},
                {"value": "mid_career",    "label": "Established professional"},
                {"value": "senior_career", "label": "Senior / leadership role"},
                {"value": "entrepreneur",  "label": "Running my own business"},
                {"value": "creative",      "label": "Creative professional"},
                {"value": "transition",    "label": "Career transition"},
                {"value": "retired",       "label": "Retired"},
            ],
        },
        {
            "field":    "financial_status",
            "question": "How would you describe your financial situation?",
            "options": [
                {"value": "debt",        "label": "Managing debt or financial pressure"},
                {"value": "stable",      "label": "Stable — getting by comfortably"},
                {"value": "growing",     "label": "Growing — things are improving"},
                {"value": "wealthy",     "label": "Financially established"},
                {"value": "transition",  "label": "In financial transition"},
            ],
        },
        {
            "field":    "health_status",
            "question": "How is your health?",
            "options": [
                {"value": "excellent",      "label": "Good — no major concerns"},
                {"value": "minor_issues",   "label": "Managing some minor issues"},
                {"value": "chronic",        "label": "Living with a chronic condition"},
                {"value": "recovery",       "label": "Recovering from illness or surgery"},
                {"value": "mental_health",  "label": "Navigating mental/emotional health"},
            ],
        },
    ]


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_life_stage(age: int) -> tuple[str, str, str]:
    for key, (min_age, max_age, name, desc) in LIFE_STAGES.items():
        if min_age <= age < max_age:
            return key, name, desc
    return "sannyasa", "Elder Sage", LIFE_STAGES["sannyasa"][3]
