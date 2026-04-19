"""
Diagnostic Engine — Surface B: Life Arc
========================================
Generates the diagnostic block:
- Current stuckness sources (specific dasha/transit causes)
- What to lean into
- What to avoid
- Next phase shift with preparation advice

Uses Claude for synthesis, with structured JSON output.

Author: Antar Engine · April 2026
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any


# ─── Dasha Psychology Library (Starter) ──────────────────────────────────────

DASHA_PSYCHOLOGY = {
    ("Venus", "Saturn"): {
        "tension": "Venus wants flow and enjoyment; Saturn wants discipline and delay. These are at odds — you feel pulled in two directions about the same decisions.",
        "lean_into": ["Disciplined daily work (Saturn-aligned)", "Building what will launch later", "Elder mentor relationships"],
        "avoid": ["Abrupt career exits", "Major financial commitments", "Forcing breakthroughs"],
    },
    ("Venus", "Mercury"): {
        "tension": "Venus brings desire for beauty and harmony; Mercury brings analytical clarity. This is a launch-ready combination — decisions become cleaner.",
        "lean_into": ["Communication-heavy initiatives", "Creative projects with structure", "Networking and partnerships"],
        "avoid": ["Overthinking opportunities (analysis paralysis)", "Ignoring intuition in favor of data only"],
    },
    ("Venus", "Ketu"): {
        "tension": "Venus seeks connection and material comfort; Ketu dissolves attachments. You may feel detachment from things you previously valued — this is intentional spiritual pruning.",
        "lean_into": ["Spiritual practice", "Letting go of outdated goals", "Simplification"],
        "avoid": ["Starting new relationships impulsively", "Large purchases", "Resisting the detachment process"],
    },
    ("Venus", "Venus"): {
        "tension": "Double Venus amplifies desire for beauty, love, comfort. Risk of overindulgence, but also peak creative expression.",
        "lean_into": ["Creative expression", "Relationship deepening", "Aesthetic projects"],
        "avoid": ["Financial overextension", "Confusing pleasure with progress"],
    },
    ("Venus", "Sun"): {
        "tension": "Venus seeks harmony; Sun seeks authority. Good for leadership in creative or relationship-oriented domains.",
        "lean_into": ["Public-facing roles", "Creative leadership", "Personal branding"],
        "avoid": ["Ego conflicts in partnerships", "Ignoring collaborative input"],
    },
    ("Venus", "Moon"): {
        "tension": "Venus and Moon both prioritize emotional well-being. Highly receptive period — emotional sensitivity is heightened.",
        "lean_into": ["Emotional intelligence work", "Home and family matters", "Artistic expression"],
        "avoid": ["Emotional reactivity in business decisions", "Neglecting practical matters"],
    },
    ("Venus", "Mars"): {
        "tension": "Venus wants peace; Mars wants action. Creates passionate energy but also potential conflict in relationships.",
        "lean_into": ["Physical activity", "Competitive ventures", "Passion projects"],
        "avoid": ["Impulsive decisions", "Relationship conflicts", "Starting fights you can't finish"],
    },
    ("Venus", "Rahu"): {
        "tension": "Venus meets amplification. Desires are magnified — can lead to breakthroughs or obsession.",
        "lean_into": ["Ambitious creative projects", "Unconventional partnerships", "Technology-meets-art ventures"],
        "avoid": ["Getting lost in fantasy", "Ungrounded ambition", "Substance use"],
    },
    ("Venus", "Jupiter"): {
        "tension": "Venus and Jupiter are both benefics. Expansive, fortunate period — but risk of overconfidence.",
        "lean_into": ["Education", "Travel", "Wealth-building", "Teaching"],
        "avoid": ["Overcommitting", "Assuming everything will work out without effort"],
    },
    ("Jupiter", "Saturn"): {
        "tension": "Jupiter expands; Saturn contracts. The push-pull creates slow but durable growth. Patience is the key theme.",
        "lean_into": ["Long-term planning", "Structured learning", "Building institutions"],
        "avoid": ["Get-rich-quick schemes", "Ignoring responsibilities", "Overexpansion"],
    },
    ("Saturn", "Saturn"): {
        "tension": "Double Saturn: peak discipline, peak pressure. This is a karmic reckoning period — results directly reflect effort.",
        "lean_into": ["Serious work", "Health routines", "Debt reduction", "Structural repairs"],
        "avoid": ["Shortcuts", "Avoiding responsibilities", "Pessimism spirals"],
    },
}

# Default for unknown combinations
DEFAULT_PSYCHOLOGY = {
    "tension": "The current chapter lords create a dynamic tension that requires balancing competing priorities.",
    "lean_into": ["Consistent daily effort", "Self-reflection", "Building foundations"],
    "avoid": ["Impulsive major decisions", "Ignoring the body's signals"],
}


def _get_dasha_psychology(md: str, ad: str) -> dict:
    """Look up dasha pairing psychology, with fallback."""
    key = (md, ad)
    if key in DASHA_PSYCHOLOGY:
        return DASHA_PSYCHOLOGY[key]
    # Try reversed
    rev_key = (ad, md)
    if rev_key in DASHA_PSYCHOLOGY:
        return DASHA_PSYCHOLOGY[rev_key]
    return DEFAULT_PSYCHOLOGY


def _compute_next_phase_shift(current_phase: dict) -> dict:
    """
    Determine the next significant phase shift (AD change).
    """
    vim = current_phase.get("vimsottari", {})
    ad_end = vim.get("ad_end_date")
    md = vim.get("md", "Unknown")
    ad = vim.get("ad", "Unknown")

    if not ad_end:
        return {
            "date": "Unknown",
            "label": "Next sub-chapter transition",
            "character": "Unable to determine — dasha data incomplete.",
            "preparation_advice": "Focus on consistent daily work.",
        }

    return {
        "date": ad_end,
        "label": f"{md} MD / next AD begins",
        "character": "",  # Will be filled by Claude or fallback
        "preparation_advice": "",
    }


# ─── Claude-Powered Diagnostic ──────────────────────────────────────────────

async def generate_diagnostic(
    chart_data: dict,
    current_phase: dict,
    archetype_name: str = "",
    language: str = "en",
    claude_caller=None,
) -> dict:
    """
    Generate the diagnostic block using Claude for synthesis.
    Falls back to rule-based generation if Claude unavailable.
    """
    vim = current_phase.get("vimsottari", {})
    overlay = current_phase.get("transit_overlay", {})
    md = vim.get("md", "Unknown")
    ad = vim.get("ad", "Unknown")
    pd = vim.get("pd", "Unknown")

    psychology = _get_dasha_psychology(md, ad)
    next_shift = _compute_next_phase_shift(current_phase)

    # Try Claude for rich diagnostic
    if claude_caller:
        try:
            return await _claude_diagnostic(
                vim, overlay, psychology, next_shift,
                archetype_name, language, claude_caller
            )
        except Exception as e:
            print(f"[life_arc.diagnostic] Claude error, using fallback: {e}")

    # Fallback: rule-based
    return _fallback_diagnostic(vim, overlay, psychology, next_shift)


async def _claude_diagnostic(
    vim: dict,
    overlay: dict,
    psychology: dict,
    next_shift: dict,
    archetype_name: str,
    language: str,
    claude_caller,
) -> dict:
    """Use Claude to generate a rich, specific diagnostic."""
    md = vim.get("md", "Unknown")
    ad = vim.get("ad", "Unknown")

    prompt = f"""You are generating a life diagnostic for Antar (a life navigation AI).

Current state:
- Major chapter: {md} (ends {vim.get('md_end_date')})
- Sub-chapter: {ad} (ends {vim.get('ad_end_date')})
- Micro-chapter: {vim.get('pd')} (ends {vim.get('pd_end_date')})
- Sade Sati: {overlay.get('sade_sati_status', 'dormant')}
- Jupiter house from Moon: {overlay.get('jupiter_house_from_moon')}
- Saturn house from Moon: {overlay.get('saturn_house_from_moon')}
- Archetype: {archetype_name}
- Known tension: {psychology['tension']}

Generate a JSON diagnostic with this EXACT structure:
{{
  "current_stuckness_sources": [
    {{
      "source": "specific dasha or transit name",
      "explanation": "2-3 sentences explaining what this creates practically",
      "duration_remaining_months": <integer>
    }}
  ],
  "what_to_lean_into": ["specific action 1", "specific action 2", "specific action 3"],
  "what_to_avoid": ["specific thing 1", "specific thing 2", "specific thing 3"],
  "next_phase_shift": {{
    "date": "{next_shift['date']}",
    "label": "{next_shift['label']}",
    "character": "2-3 sentences describing what the next phase brings",
    "preparation_advice": "1-2 sentences on how to prepare"
  }}
}}

RULES:
1. Stuckness sources must name SPECIFIC dashas or transits (e.g., "Venus MD / Saturn AD pairing")
2. Do NOT use Sanskrit terms — translate everything
3. Be specific about durations (calculate from the end dates provided)
4. Lean-into items should be actionable, not generic
5. Avoid items should reference specific timing (e.g., "before November 2026")
6. Language: {language}
7. Return ONLY valid JSON, no markdown formatting

Generate now:"""

    system = "You are Antar's diagnostic engine. Output valid JSON only. Be specific, warm, and actionable. No jargon."

    text, _ = await claude_caller(prompt, system_override=system)

    # Parse JSON from response
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    if text.startswith("json"):
        text = text[4:].strip()

    diagnostic = json.loads(text)
    return diagnostic


def _fallback_diagnostic(vim: dict, overlay: dict, psychology: dict, next_shift: dict) -> dict:
    """Rule-based diagnostic when Claude is unavailable."""
    md = vim.get("md", "Unknown")
    ad = vim.get("ad", "Unknown")
    ad_end = vim.get("ad_end_date", "Unknown")

    stuckness = []

    # Dasha-based stuckness
    stuckness.append({
        "source": f"{md} MD / {ad} AD pairing",
        "explanation": psychology["tension"],
        "duration_remaining_months": _months_until(ad_end),
    })

    # Sade Sati stuckness
    sade_status = overlay.get("sade_sati_status", "dormant")
    if "dormant" not in sade_status.lower():
        parts = sade_status.split(",")
        months_str = parts[1].strip().split()[0] if len(parts) > 1 else "0"
        try:
            months = int(months_str)
        except ValueError:
            months = 0
        stuckness.append({
            "source": f"Sade Sati ({parts[0].strip()})",
            "explanation": "Saturn transiting your natal Moon compresses emotional-mental resources. Motivation feels heavy, not absent.",
            "duration_remaining_months": months,
        })

    # Next phase shift
    next_shift["character"] = f"The transition from {ad} to the next sub-chapter brings a shift in energy and decision-making clarity."
    next_shift["preparation_advice"] = f"Use the remaining months to build what you will launch in the next sub-chapter."

    return {
        "current_stuckness_sources": stuckness,
        "what_to_lean_into": psychology["lean_into"],
        "what_to_avoid": psychology["avoid"],
        "next_phase_shift": next_shift,
    }


def _months_until(date_str: str) -> int:
    """Calculate months from now until a date string."""
    if not date_str or date_str == "Unknown":
        return 0
    try:
        target = datetime.strptime(date_str[:10], "%Y-%m-%d")
        now = datetime.utcnow()  # naive is fine here — just calculating month diff
        delta = target - now
        return max(0, int(delta.days / 30))
    except Exception:
        return 0
