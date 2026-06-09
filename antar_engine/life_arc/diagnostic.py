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
    """Use Claude to generate a rich, specific diagnostic.

    [narration-contract 2026-06-08] Inputs are pre-translated to
    energy-systems language so the model never sees planet names; the
    output is also walked through output_strips as defense in depth.
    The diagnostic was the largest rule-#12 jargon offender in the
    codebase (30 leaks per audit) — both layers close it.
    """
    from antar_engine.life_arc.voice.energy_vocabulary import (
        get_energy_name as _energy_name,
    )

    md_raw = vim.get("md", "Unknown")
    ad_raw = vim.get("ad", "Unknown")
    pd_raw = vim.get("pd", "Unknown")
    md = _energy_name(md_raw)
    ad = _energy_name(ad_raw)
    pd = _energy_name(pd_raw)

    # Psychology tension strings still contain planet names. Translate
    # them in-flight so the prompt context is fully plain-domain.
    _tension = str(psychology.get("tension") or "")
    for _planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                    "Venus", "Saturn", "Rahu", "Ketu"):
        _tension = _tension.replace(_planet, _energy_name(_planet))

    # Map slow-transit house-from-Moon to a plain-life sector for the
    # prompt's context block. Internal-only; the model never echoes
    # the house number.
    _HOUSE_SECTOR = {
        1: "your sense of self", 2: "your finances and security",
        3: "your communication and short-distance work",
        4: "your home and inner foundation",
        5: "your creativity and joy",
        6: "your work and health routine",
        7: "your partnerships", 8: "shared matters and change",
        9: "your luck and beliefs",
        10: "your career and public role",
        11: "your goals and gains",
        12: "your rest and letting go",
    }
    _jup_h = overlay.get("jupiter_house_from_moon")
    _sat_h = overlay.get("saturn_house_from_moon")
    _jup_sector = _HOUSE_SECTOR.get(_jup_h, "an unspecified sector") if isinstance(_jup_h, int) else "dormant"
    _sat_sector = _HOUSE_SECTOR.get(_sat_h, "an unspecified sector") if isinstance(_sat_h, int) else "dormant"
    _growth_energy = _energy_name("Jupiter")
    _discipline_energy = _energy_name("Saturn")

    prompt = f"""You are generating a life diagnostic for Antar (a life navigation AI).

Current state (internal labels — NEVER echo these literally):
- Major chapter: {md} (ends {vim.get('md_end_date')})
- Sub-chapter: {ad} (ends {vim.get('ad_end_date')})
- Micro-chapter: {pd} (ends {vim.get('pd_end_date')})
- Sade Sati: {overlay.get('sade_sati_status', 'dormant')}
- {_growth_energy} is currently moving through {_jup_sector}.
- {_discipline_energy} is currently moving through {_sat_sector}.
- Archetype: {archetype_name}
- Known tension: {_tension}

Generate a JSON diagnostic with this EXACT structure:
{{
  "current_stuckness_sources": [
    {{
      "source": "Your [life-domain] is [under pressure / blocked / strained / charged]",
      "explanation": "2-3 sentences. Name 2+ concrete life-nouns (your career, your savings, your partner, a contract, your daily routine). Plain everyday language.",
      "duration_remaining_months": <integer>
    }}
  ],
  "what_to_lean_into": ["Verb-first imperative tied to a life-noun.", "...", "..."],
  "what_to_avoid": ["Verb-first 'Avoid X' or 'Skip Y' tied to a life-noun.", "...", "..."],
  "next_phase_shift": {{
    "date": "{next_shift['date']}",
    "label": "Plain-language label — what kind of chapter opens. NEVER 'Saturn major / Rahu sub' or any planet name.",
    "character": "2-3 sentences. What changes. Name 2+ life-nouns. Verdict-adjective shape — 'opens', 'tightens', 'broadens'. NEVER name a planet.",
    "preparation_advice": "1-2 sentences. Verb-first imperative. NEVER name a planet."
  }}
}}

HARD RULES (rule-#12 violations void the output):
1. SOURCE shape: verdict-first directive — "Your [life-domain] is
   [under pressure / blocked / strained / charged / favorable / mixed]".
   Examples (shape only, do not copy):
     * "Your career is under pressure from the discipline chapter."
     * "Your daily routine is strained — health asks for slow care."
     * "Your partnerships are charged — a decision waits."
   FORBIDDEN: "Venus MD / Saturn AD pairing", "Saturn in 3rd house from Moon",
   "Saturn major / Mars sub", "Ketu micro-phase", or ANY planet name.
2. NEVER mention planets, signs, houses, nakshatras, dashas, antardashas,
   ascendants, zodiac, retrogrades, Sanskrit terms, or any astrology jargon.
   Translate everything to plain life domains.
3. Lean-into and avoid items lead with an imperative verb (Build, Protect,
   Postpone, Hold, Close, Start, Limit, Move, Skip, Wait).
4. Concrete nouns required: your career, your savings, your partner,
   your home, a contract, a senior, your boss, your daily routine, a loan,
   your father, etc. NEVER abstract energy-words alone
   (vitality, systems, foundations, momentum, growth) as the only nouns.
5. Be specific about durations + windows (calculate from the end dates).
6. Avoid items should reference specific timing (e.g., "before November 2026").
7. Language: {language}.
8. Return ONLY valid JSON, no markdown formatting.

Generate now:"""

    system = ("You are Antar's diagnostic engine. Output valid JSON only. "
              "Be specific, warm, and actionable. ZERO jargon — no planet "
              "names, no houses, no Sanskrit, no astrology terms. Every "
              "stuckness source must be a verdict-first directive about a "
              "life domain, never a dasha label.")

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

    # ── Defense-in-depth: walk the whole diagnostic through the
    # output_strips layer. apply_user_facing_strips handles dicts +
    # lists + strings recursively, so every field gets scrubbed even
    # if the prompt rules above are partially ignored.
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        diagnostic = apply_user_facing_strips(
            diagnostic, language=language or "en", field_type="plain",
        )
    except Exception as _strip_err:
        # Non-fatal — better a leak than a 500. Log and pass through.
        print(f"[life_arc.diagnostic] strip layer skipped: {_strip_err}")

    return diagnostic


def _fallback_diagnostic(vim: dict, overlay: dict, psychology: dict, next_shift: dict) -> dict:
    """Rule-based diagnostic when Claude is unavailable.
    [cycle-andres-fix 2026-06-09] All planet names translated via
    _energy_name before use."""
    from antar_engine.life_arc.voice.energy_vocabulary import (
        get_energy_name as _energy_name,
    )
    md = _energy_name(vim.get("md", "Unknown"))
    ad = _energy_name(vim.get("ad", "Unknown"))
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
            "explanation": "A long structural pressure on your emotional foundation compresses motivation. Mind feels heavy, not absent.",
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
