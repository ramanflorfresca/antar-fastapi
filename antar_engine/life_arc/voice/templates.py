"""
Voice Templates — v5.1 Wording Framework
==========================================
Three templates for rendering findings in energy-systems voice:
  A — Positive Activation (energy that's strong, user should engage)
  B — Negative Affliction (energy that's dimmed/distorted, needs support)
  C — Context Warning (dasha-specific or archetype-specific caution)

Author: Antar Engine · April 2026
"""

from typing import Optional


TEMPLATE_A = """Your {energy_name} — {energy_description} — is one of the strongest flows in your design. You may have noticed {felt_examples}.

To let it work through you this season, one practice: {remedy_action}.

Over a few weeks, notice whether {expected_observation}.

One thing to protect this energy: {what_not_to_do}."""


TEMPLATE_B = """Your {energy_name} — {energy_description} — has been running dim right now. You may have noticed {felt_examples}.

This is common in {life_context} and can be supported. One practice: {remedy_action}.

Over {timeframe}, notice whether {expected_observation}. If nothing shifts, that's information too — we'll try a different entry point.

While you're tending this energy, one thing to pause: {what_not_to_do}."""


TEMPLATE_C = """Right now, {dasha_context} is amplifying {pattern_description}. This means {what_user_may_face}.

This isn't a problem to fix — it's a phase to navigate carefully. The guidance: {what_to_do}; {what_not_to_do}.

One supportive practice during this phase: {remedy_action}.

{timing_note}"""


def select_template(finding_category: str, finding_type: str = "") -> str:
    """
    Select which template to use based on finding category and type.

    Returns: "A", "B", or "C"
    """
    # Context warnings get Template C
    context_types = {
        "focus_split_risk",
        "moon_md_h2_pressure",
        "hora_business_mismatch",
    }
    if finding_type in context_types:
        return "C"

    # Map finding types to specific templates
    type_overrides = {
        "yogakaraka_activation": "A",
        "mahapurusha_stack": "A",
        "dushthana_wealth_active": "A",  # reframe dushthana as transformative
        "viparita_stack": "A",           # rise-through-adversity = positive
        "identity_overwhelm": "B",
        "d60_karma": "B",               # karmic pattern = needs support
    }

    override = type_overrides.get(finding_type)
    if override:
        return override

    # Default: POSITIVE → A, NEGATIVE → B, NEUTRAL → C
    if finding_category == "POSITIVE":
        return "A"
    elif finding_category == "NEGATIVE":
        return "B"
    return "C"


def get_template_text(template_id: str) -> str:
    """Get the raw template text by ID."""
    templates = {"A": TEMPLATE_A, "B": TEMPLATE_B, "C": TEMPLATE_C}
    return templates.get(template_id, TEMPLATE_B)


def render_template(
    template_id: str,
    energy_name: str = "",
    energy_description: str = "",
    felt_examples: str = "",
    remedy_action: str = "",
    expected_observation: str = "",
    what_not_to_do: str = "",
    what_to_do: str = "",
    life_context: str = "this phase of life",
    timeframe: str = "a few weeks",
    dasha_context: str = "",
    pattern_description: str = "",
    what_user_may_face: str = "",
    timing_note: str = "",
) -> str:
    """
    Render a template with provided values.

    For LLM-rendered output, use voice_prompter.py instead.
    This is for deterministic (non-LLM) rendering.
    """
    tmpl = get_template_text(template_id)

    replacements = {
        "energy_name": energy_name,
        "energy_description": energy_description,
        "felt_examples": felt_examples,
        "remedy_action": remedy_action,
        "expected_observation": expected_observation,
        "what_not_to_do": what_not_to_do,
        "what_to_do": what_to_do,
        "life_context": life_context,
        "timeframe": timeframe,
        "dasha_context": dasha_context,
        "pattern_description": pattern_description,
        "what_user_may_face": what_user_may_face,
        "timing_note": timing_note,
    }

    result = tmpl
    for k, v in replacements.items():
        result = result.replace(f"{{{k}}}", v)
    return result.strip()
