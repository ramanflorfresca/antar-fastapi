"""
Voice Prompter — v5.1 LLM Prompt Builder
==========================================
Builds Claude prompts that render findings in energy-systems voice.

The LLM receives:
  - Energy vocabulary for the target planet
  - Template structure (A/B/C)
  - Finding context (chart data, dasha, remedy)
  - Strict voice rules + forbidden terms

Returns a structured prompt string for Claude to render.

Author: Antar Engine · April 2026
"""

from typing import Dict, Optional, Any

from .energy_vocabulary import PLANET_ENERGY_VOCABULARY, get_energy_name
from .templates import select_template, get_template_text
from .forbidden_terms import FORBIDDEN_TERMS


def build_voice_prompt(
    finding_id: str,
    finding_category: str,
    target_planet: Optional[str],
    why_plain_language: str,
    remedy_action: str,
    what_not_to_do: str,
    expected_observation: str,
    archetype_label: str = "",
    current_md: str = "",
    current_ad: str = "",
    user_comfortable_with_chakras: bool = False,
) -> str:
    """
    Build a Claude prompt for rendering a finding in v5.1 voice.

    Returns a complete prompt string ready for LLM.generate().
    """
    # Get energy vocabulary
    energy_vocab = PLANET_ENERGY_VOCABULARY.get(target_planet, {}) if target_planet else {}
    energy_name = energy_vocab.get("energy_name", "this energy pattern")

    # Select template
    template_id = select_template(finding_category, finding_id)

    # Determine felt-sense based on category
    if finding_category == "POSITIVE":
        felt_sense = energy_vocab.get("felt_when_strong", "")
    else:
        felt_sense = energy_vocab.get("felt_when_weak", "")

    # Build chakra note
    chakra_note = ""
    if user_comfortable_with_chakras and energy_vocab.get("chakra"):
        chakra_note = f"Optionally anchor in chakra: {energy_vocab['chakra']}"

    # Build forbidden terms list (abbreviated for prompt)
    forbidden_summary = (
        "NEVER use: planet names as subjects ('Your Jupiter'), 'Lal Kitab', "
        "'astrologically', 'propitiate', 'appease', 'evil', 'cursed', 'You must', "
        "'You should', 'guaranteed', 'This will fix', house numbers (H1, H6), "
        "'dushthana', 'kendra', 'yogakaraka', 'Mahapurusha', 'Viparita', "
        "'navamsha', 'Mahadasha', 'lagna', 'nakshatra', 'dosha', 'graha'."
    )

    prompt = f"""You are writing a short, warm, specific piece of guidance to a user.
Tone: thoughtful friend with deep wisdom, not astrologer, not guru, not therapist.

CRITICAL VOICE RULES:
1. Use energy-systems language, NOT planet-deity language.
2. Start with "Your {energy_name}..."
3. Use felt-sense language user can self-verify: "{felt_sense}"
4. Describe the remedy in plain action terms — no tradition-naming.
5. Keep total length 120-180 words.
6. End with a specific "pause this" suggestion — kinder than "don't do".
{f'7. {chakra_note}' if chakra_note else ''}

{forbidden_summary}

USE: "You may have noticed...", "running dim/strong", "To support this...",
"Over a few weeks, notice...", "This is common in...", "One thing to pause..."

CONTEXT:
- User's archetype: {archetype_label or 'not classified'}
- Current life chapter: {current_md or 'not specified'} main / {current_ad or 'not specified'} sub
- Finding: {finding_id}
- Category: {finding_category}
- What's happening: {why_plain_language}
- Practice to recommend: {remedy_action}
- What to observe: {expected_observation}
- What to pause: {what_not_to_do}

Write in Template {template_id} structure:
{get_template_text(template_id)}

Keep it human, not clinical. The user should feel seen, not diagnosed."""

    return prompt


def build_batch_voice_prompts(
    actionability_blocks: list,
    chart_data: dict,
    user_context: Optional[dict] = None,
) -> list:
    """
    Build voice prompts for all actionability blocks.
    Returns list of (finding_id, prompt) tuples.
    """
    archetype = chart_data.get("archetype", {})
    arch_label = ""
    if isinstance(archetype, dict):
        arch_label = archetype.get("name", "")
    elif isinstance(archetype, str):
        arch_label = archetype

    current_dasha = chart_data.get("current_dasha", {})
    md = current_dasha.get("md_lord", "") if isinstance(current_dasha, dict) else ""
    ad = current_dasha.get("ad_lord", "") if isinstance(current_dasha, dict) else ""

    comfortable_chakras = False
    if user_context:
        comfortable_chakras = user_context.get("comfortable_with_chakras", False)

    prompts = []
    for block in actionability_blocks:
        # Handle both dict and dataclass
        if hasattr(block, "finding_id"):
            fid = block.finding_id
            fcat = block.finding_category
            planet = _finding_to_planet(fid)
            why = block.why_plain_language
            remedy_action = ""
            if block.lal_kitab_activation:
                remedy_action = block.lal_kitab_activation.get("action", "")
            expected = ""
            if block.lal_kitab_activation:
                expected = block.lal_kitab_activation.get("expected_observation", "")
            dont = block.what_not_to_do
        else:
            fid = block.get("finding_id", "")
            fcat = block.get("finding_category", "NEUTRAL")
            planet = _finding_to_planet(fid)
            why = block.get("why_plain_language", "")
            activation = block.get("lal_kitab_activation", {}) or {}
            remedy_action = activation.get("action", "")
            expected = activation.get("expected_observation", "")
            dont = block.get("what_not_to_do", "")

        prompt = build_voice_prompt(
            finding_id=fid,
            finding_category=fcat,
            target_planet=planet,
            why_plain_language=why,
            remedy_action=remedy_action,
            what_not_to_do=dont,
            expected_observation=expected,
            archetype_label=arch_label,
            current_md=md,
            current_ad=ad,
            user_comfortable_with_chakras=comfortable_chakras,
        )
        prompts.append((fid, prompt))

    return prompts


def _finding_to_planet(finding_id: str) -> Optional[str]:
    """Extract planet from finding ID if possible."""
    planet_map = {
        "focus_split_risk": "Rahu",
        "moon_md_h2_pressure": "Moon",
    }
    if finding_id in planet_map:
        return planet_map[finding_id]
    # d60_karma findings may have planet in ID
    if finding_id.startswith("d60_karma_"):
        return finding_id.replace("d60_karma_", "")
    return None
