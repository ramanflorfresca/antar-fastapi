"""
signal_age_guard.py — Age intelligence mixin for all Antar proactive signal generators.
Sprint W · antar.world · March 31, 2026

Apply this to:
  W-08 → build_proactive_context()    (daily signal)
  W-09 → weekly_briefing generator
  W-10 → monthly_deepdive + annual_plan generators

Usage in each generator:
    from signal_age_guard import build_age_guard_block, AGE_GUARD_INSTRUCTION

    # In context builder:
    age_block = build_age_guard_block(birth_date)

    # In system prompt assembly — prepend before sending to Claude:
    system_prompt = AGE_GUARD_INSTRUCTION.format(**age_block) + existing_system_prompt
"""

from age_utils import calculate_current_age, get_floor_age, filter_umra_activations


# ---------------------------------------------------------------------------
# Shared instruction fragment — prepend to ANY signal generator system prompt
# ---------------------------------------------------------------------------

AGE_GUARD_INSTRUCTION = """TEMPORAL GROUNDING — READ FIRST:
This user is {current_age} years old.
Temporal floor: {floor_age} years old.
NEVER reference themes, events, or life stages from before age {floor_age}.
Examples of what is forbidden for a {current_age}-year-old:
{forbidden_examples}
All dates referenced must resolve to the future. State the user's current age as a fact if relevant.

"""


# Age-domain reality guidance by life stage
_STAGE_FORBIDDEN = {
    "early_career":    # 20-32
        "- Do not reference retirement, legacy, succession, reviewing long patterns, or life completion.",
    "mid_career":      # 33-49
        "- Do not reference retirement or starting-out themes. Focus on growth, building, and peak career.",
    "peak_authority":  # 50-60
        "- Do not reference 'starting out', 'first relationship', 'building a family'. Focus on authority, legacy, wisdom.",
    "later_stage":     # 61+
        "- Do not reference early-career ambition, family formation, or impulsive youthful themes. Focus on legacy, completion, liberation.",
}


def _get_life_stage(age: int) -> str:
    if age <= 32:
        return "early_career"
    elif age <= 49:
        return "mid_career"
    elif age <= 60:
        return "peak_authority"
    else:
        return "later_stage"


def build_age_guard_block(birth_date: str) -> dict:
    """
    Builds the age guard context dict for a given birth date.
    Inject the result into AGE_GUARD_INSTRUCTION.format(**block).

    Returns:
        {
          "current_age": int,
          "floor_age": int,
          "forbidden_examples": str,  # bullet points for the system prompt
          "umra_upcoming": list[dict],
        }
    """
    age = calculate_current_age(birth_date)
    floor = get_floor_age(age)
    stage = _get_life_stage(age)
    forbidden = _STAGE_FORBIDDEN[stage]
    umra = filter_umra_activations(age, max_upcoming=2)

    return {
        "current_age": age,
        "floor_age": floor,
        "forbidden_examples": forbidden,
        "umra_upcoming": umra,
    }


def format_umra_block(umra_items: list[dict]) -> str:
    """Formats upcoming Umra activations as a plain-text context block."""
    if not umra_items:
        return ""
    lines = [
        f"  • House {u['house']} activates at age {u['activation_age']}: {u['theme']}"
        for u in umra_items
    ]
    return "Upcoming age activations (Lal Kitab):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# W-08 — Daily signal age guard
# ---------------------------------------------------------------------------

def apply_age_guard_to_daily(
    existing_context: str,
    existing_system_prompt: str,
    birth_date: str,
) -> tuple[str, str]:
    """
    Injects age intelligence into the daily signal context and system prompt.

    Args:
        existing_context:       The context block already built for the daily signal
        existing_system_prompt: The system prompt currently sent to Claude for daily signal
        birth_date:             'YYYY-MM-DD'

    Returns:
        (updated_context, updated_system_prompt)
    """
    block = build_age_guard_block(birth_date)
    umra_text = format_umra_block(block["umra_upcoming"])

    age_context_header = (
        f"USER AGE: {block['current_age']} years old. "
        f"Temporal floor: age {block['floor_age']}.\n"
        + (umra_text + "\n" if umra_text else "")
    )

    updated_context = age_context_header + existing_context
    updated_system_prompt = (
        AGE_GUARD_INSTRUCTION.format(**block) + existing_system_prompt
    )

    return updated_context, updated_system_prompt


# ---------------------------------------------------------------------------
# W-09 — Weekly briefing age guard
# ---------------------------------------------------------------------------

def apply_age_guard_to_weekly(
    existing_context: str,
    existing_system_prompt: str,
    birth_date: str,
) -> tuple[str, str]:
    """
    Weekly briefing is the most-read coaching signal.
    Age-appropriate language matters especially for 50+ users.

    Same signature as apply_age_guard_to_daily.
    Additional check: weekly briefing domain signals must not use life-stage-mismatched language.
    """
    block = build_age_guard_block(birth_date)
    age = block["current_age"]

    # Domain-specific age guidance appended for weekly briefing
    domain_guidance = _get_domain_guidance(age)

    age_context_header = (
        f"USER AGE: {age} years old. Temporal floor: age {block['floor_age']}.\n"
        f"{format_umra_block(block['umra_upcoming'])}\n"
    )

    weekly_addendum = f"\nDOMAIN LANGUAGE GUIDANCE FOR THIS USER'S AGE ({age}):\n{domain_guidance}\n"

    updated_context = age_context_header + existing_context
    updated_system_prompt = (
        AGE_GUARD_INSTRUCTION.format(**block)
        + weekly_addendum
        + existing_system_prompt
    )

    return updated_context, updated_system_prompt


# ---------------------------------------------------------------------------
# W-10 — Monthly deep-dive + annual plan age guard
# ---------------------------------------------------------------------------

def apply_age_guard_to_monthly(
    existing_context: str,
    existing_system_prompt: str,
    birth_date: str,
) -> tuple[str, str]:
    """
    Monthly deep-dive and annual plan.
    Must not reference life stages the user has already completed.
    """
    return apply_age_guard_to_weekly(existing_context, existing_system_prompt, birth_date)


def apply_age_guard_to_annual(
    existing_context: str,
    existing_system_prompt: str,
    birth_date: str,
) -> tuple[str, str]:
    """
    Annual plan — stricter guidance.
    Annual plan peak windows must be realistic for this user's age and life stage.
    """
    block = build_age_guard_block(birth_date)
    age = block["current_age"]

    annual_addendum = f"""
ANNUAL PLAN AGE RULES:
- Peak windows must be relevant to a {age}-year-old's actual life stage.
- Do not suggest "starting a family" peak windows for ages 50+.
- Do not suggest "retirement planning" peak windows for ages under 45.
- Career peak windows for 55+ should reference authority, legacy, and succession — not entry-level ambition.
- Frame all annual themes relative to what is genuinely possible and meaningful at age {age}.
"""

    age_context_header = (
        f"USER AGE: {age} years old. Temporal floor: age {block['floor_age']}.\n"
        f"{format_umra_block(block['umra_upcoming'])}\n"
    )

    updated_context = age_context_header + existing_context
    updated_system_prompt = (
        AGE_GUARD_INSTRUCTION.format(**block)
        + annual_addendum
        + existing_system_prompt
    )

    return updated_context, updated_system_prompt


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_domain_guidance(age: int) -> str:
    """Returns domain-specific language guidance by life stage."""
    if age < 33:
        return (
            "Career signals: focus on opportunity, growth, skill-building, early momentum.\n"
            "Relationship signals: focus on new connections, formation, learning compatibility.\n"
            "Wealth signals: focus on income growth, first assets, financial foundations.\n"
            "Health signals: focus on building habits, energy, physical foundations.\n"
        )
    elif age < 50:
        return (
            "Career signals: focus on advancement, leadership, peak performance, transitions.\n"
            "Relationship signals: focus on deepening, partnership decisions, long-term alignment.\n"
            "Wealth signals: focus on wealth-building, investment decisions, asset growth.\n"
            "Health signals: focus on maintenance, energy management, stress resilience.\n"
        )
    elif age < 62:
        return (
            "Career signals: focus on authority, reputation, legacy-building, mentoring others.\n"
            "Relationship signals: focus on depth, commitment quality, partnership evolution.\n"
            "Wealth signals: focus on consolidation, asset protection, income sustainability.\n"
            "Health signals: focus on longevity, vitality, prevention.\n"
        )
    else:
        return (
            "Career signals: focus on legacy, wisdom-sharing, meaningful contribution, succession.\n"
            "Relationship signals: focus on depth, companionship, wisdom in long partnerships.\n"
            "Wealth signals: focus on estate, inheritance planning, sustainable income.\n"
            "Health signals: focus on vitality, quality of life, spiritual wellbeing.\n"
        )
