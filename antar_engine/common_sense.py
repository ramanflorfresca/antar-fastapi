"""
common_sense.py
Sprint C4 — Common Sense Layer

Sits between the 7 intelligence layers and the Claude call.
Reads what's already been computed (patra, DKP, memory, concern)
and generates a reality-check instruction block for Claude.

No DB queries. No API calls. No LLM call.
Pure Python — adds ~5ms to /predict.

Purpose:
  - Age-appropriate framing (don't suggest children to a 60-year-old)
  - Life stage calibration (22-year-old wealth advice ≠ 45-year-old)
  - Feasibility grounding (foreign signal + visa reality = specific destination)
  - Contradiction detection (memory vs today's chart)
  - Confidence calibration (all layers aligned = say so, be direct)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ── Domain age-appropriateness rules ─────────────────────────────────────────

# (min_age, max_age, reframe_instruction)
DOMAIN_AGE_RULES = {
    "children": [
        (0,  18,  None),   # too young — reframe
        (18, 45,  None),   # normal window — no reframe
        (45, 55,  "Biological window narrowing. Frame children predictions as "
                  "legacy, mentoring, or relationship with existing children/nephews/nieces."),
        (55, 120, "Biological window closed for most. Reframe ALL 5th house / children "
                  "signals as creativity, legacy, wisdom transmission, or grandchildren."),
    ],
    "marriage": [
        (0,  18,  "Too young for marriage in most contexts. Reframe Venus/7th house as "
                  "early relationships, attraction, learning to relate."),
        (18, 45,  None),   # normal — no reframe
        (45, 60,  "Marriage is possible but frame as partnership and companionship, "
                  "not 'finding the one'. Reference current marital status."),
        (60, 120, "Frame romantic signals as companionship, deepening of existing bonds, "
                  "or spiritual partnership. Not new marriage unless specifically asked."),
    ],
    "career": [
        (0,  22,  "Career signals mean education choices, internships, first jobs. "
                  "Not senior roles or entrepreneurship yet."),
        (22, 35,  "Early career — accumulation phase. Skills, promotions, first ventures. "
                  "Not 'leadership legacy' yet."),
        (35, 55,  None),   # peak — no reframe needed
        (55, 65,  "Career signals mean consolidation, legacy roles, advisory positions. "
                  "Not starting over from scratch unless they've indicated a desire to transition."),
        (65, 120, "Career signals likely mean consulting, mentoring, or part-time engagement. "
                  "Full-time career pivot unlikely — frame accordingly."),
    ],
    "wealth": [
        (0,  22,  "Wealth signals at this age mean building savings habits, "
                  "avoiding debt, first investments. Not portfolio optimisation."),
        (22, 35,  "Wealth signals mean salary growth, emergency fund, first investments. "
                  "Conservative risk framing appropriate."),
        (35, 55,  None),   # no reframe
        (55, 65,  "Wealth signals mean preservation and income stability, not aggressive growth. "
                  "Retirement planning context is relevant."),
        (65, 120, "Wealth signals mean asset protection, inheritance planning, income from "
                  "existing assets. Not new wealth creation unless chart is exceptional."),
    ],
    "foreign": [
        (0,  18,  "Foreign signals mean study abroad or family travel. Not emigration."),
        (18, 45,  None),   # normal emigration window
        (45, 60,  "Foreign signals possible but ground in realistic visa and career options. "
                  "Note family/financial ties that may affect mobility."),
        (60, 120, "Foreign signals likely mean travel, spiritual pilgrimage, or visiting "
                  "family abroad. Permanent emigration at this age requires specific context."),
    ],
    "education": [
        (0,  30,  None),   # normal
        (30, 45,  "Education signals mean professional upskilling, MBA, certifications. "
                  "Not going back to university for a first degree."),
        (45, 120, "Education signals mean specialised knowledge acquisition, mentorship, "
                  "or teaching others. Frame as mastery not studentship."),
    ],
    "love": [
        (0,  18,  "Frame love signals as early relationships and learning to relate. "
                  "Not serious partnership."),
        (18, 120, None),
    ],
    "health": [
        (0,  35,  "Health signals likely mean energy management, lifestyle, "
                  "prevention. Serious illness unlikely unless chart is extreme."),
        (35, 55,  None),
        (55, 120, "Health signals carry more weight at this age. Be specific about "
                  "which body system the chart indicates. Recommend professional consultation "
                  "for any serious signal — never diagnose."),
    ],
    "business": [
        (0,  22,  "Business signals at this age mean side projects, learning to sell, "
                  "first ventures. Not scaling a company."),
        (22, 55,  None),
        (55, 120, "Business signals likely mean consulting, advisory, or monetising expertise. "
                  "Not starting a capital-intensive new venture unless specifically asked."),
    ],
    "funding": [
        (0,  22,  "Funding signals at this age mean scholarships, grants, family support. "
                  "Not VC or institutional funding."),
        (22, 55,  None),
        (55, 120, "Funding signals likely mean grants, consulting contracts, or angel investment. "
                  "Traditional VC unlikely at this stage — frame accordingly."),
    ],
}

# ── Life stage confidence modifiers ──────────────────────────────────────────

LIFE_STAGE_MODIFIERS = {
    "brahmacharya": {
        "career":   "At this life stage, career signals mean direction and first steps, not peak achievement.",
        "wealth":   "Focus on financial habits and avoiding debt — not investment returns.",
        "love":     "Early love and attraction signals are valid. Marriage is possible but frame as 'when the time comes'.",
        "children": "Children signals should be reframed as future potential, not current.",
    },
    "early_householder": {
        "career":   "Building phase — promotions, skill accumulation, first leadership roles.",
        "wealth":   "First investment phase — emergency fund, then growth.",
        "children": "Children predictions are age-appropriate and should be taken literally.",
        "foreign":  "High mobility age — emigration signals should be taken seriously.",
    },
    "householder": {
        # Peak life stage — most signals apply directly, minimal reframing
        "children": "Children predictions apply — but also frame as parenting quality, not just having them.",
    },
    "peak_authority": {
        "career":   "Authority and legacy roles — senior leadership, board positions, advisory roles.",
        "wealth":   "Wealth consolidation phase — protect what's built, strategic growth.",
        "children": "Predictions likely about adult children relationships, not having children.",
    },
    "vanaprastha": {
        "career":   "Consolidation and knowledge transfer. Not starting fresh.",
        "wealth":   "Preservation and income from existing assets.",
        "foreign":  "Travel and pilgrimage more likely than emigration.",
        "children": "Predictions about adult children and grandchildren.",
        "love":     "Deepening of existing bonds. Companionship over romance.",
    },
    "sannyasa": {
        "career":   "Wisdom sharing, legacy, consultancy. Not active career.",
        "wealth":   "Asset protection, inheritance, charitable giving.",
        "foreign":  "Spiritual travel, visiting family. Not emigration.",
        "children": "Grandchildren, legacy. Reframe children as lineage.",
        "love":     "Spiritual partnership, companionship.",
    },
}


# ── Main public function ──────────────────────────────────────────────────────

def build_common_sense_block(
    age:            Optional[int],
    life_stage:     Optional[str],
    concern:        str,
    country_code:   Optional[str],
    marital_status: Optional[str],
    children_status:Optional[str],
    dkp_context:    Optional[str],
    memory_result:  Optional[dict],
    birth_country:  Optional[str] = None,
    current_country: Optional[str] = None,
) -> str:
    """
    Build the Common Sense instruction block for Claude.

    Args:
        age:             User's age (from patra.age)
        life_stage:      Life stage key (from patra.life_stage_name or stage key)
        concern:         Current question domain
        country_code:    ISO country code
        marital_status:  From user profile
        children_status: From user profile
        dkp_context:     DKP block string (C2)
        memory_result:   Pattern memory dict (C3)

    Returns:
        str — instruction block appended to /predict system prompt
    """
    checks   = []
    warnings = []
    instructions = []
    confidence_modifier = "STANDARD"

    # ── Age reality check ────────────────────────────────────────
    age_reframe = _get_age_reframe(concern, age)
    if age_reframe:
        warnings.append(f"Age check ({age}y): {age_reframe}")
        instructions.append(age_reframe)
        confidence_modifier = "REFRAME"
    else:
        checks.append(f"Age check ({age}y): PASS — {concern} signal is age-appropriate")

    # ── Life stage calibration ────────────────────────────────────
    stage_note = _get_life_stage_note(life_stage, concern)
    if stage_note:
        instructions.append(f"Life stage note: {stage_note}")

    # ── Marital status context ────────────────────────────────────
    if concern in ("love", "marriage", "children") and marital_status:
        ms_note = _get_marital_note(concern, marital_status)
        if ms_note:
            instructions.append(ms_note)

    # ── Children status context ───────────────────────────────────
    if concern == "children" and children_status:
        ch_note = _get_children_note(children_status)
        if ch_note:
            instructions.append(ch_note)

    # ── DKP feasibility check ────────────────────────────────────
    if dkp_context and concern in ("foreign", "business", "funding", "career", "wealth"):
        dkp_note = _get_dkp_feasibility_note(concern, dkp_context, country_code)
        if dkp_note:
            instructions.append(f"Real-world feasibility: {dkp_note}")
            checks.append(f"DKP alignment: {dkp_note[:60]}...")

    # ── Contradiction detection (C3 x today) ─────────────────────
    if memory_result:
        contradiction = _detect_contradiction(memory_result, concern)
        if contradiction:
            warnings.append(f"Contradiction detected: {contradiction}")
            instructions.append(
                f"IMPORTANT: {contradiction}. Acknowledge this tension directly. "
                f"Explain what changed or which signal is currently stronger."
            )
            confidence_modifier = "EXPLAIN_TENSION"

    # ── Confidence calibration ────────────────────────────────────
    diagnostic = memory_result.get("diagnostic_mode", False) if memory_result else False

    if confidence_modifier == "REFRAME":
        conf_instruction = (
            "Confidence calibration: REFRAME REQUIRED — "
            "apply age/life-stage reframing instructions above before answering."
        )
    elif confidence_modifier == "EXPLAIN_TENSION":
        conf_instruction = (
            "Confidence calibration: TENSION — acknowledge the contradiction, "
            "then explain the current dominant signal."
        )
    elif diagnostic:
        conf_instruction = (
            "Confidence calibration: DIAGNOSTIC — see DIAGNOSTIC MODE above. "
            "Be direct. Give a diagnosis, not an open-ended answer."
        )
    elif not warnings:
        conf_instruction = (
            "Confidence calibration: HIGH — all checks passed. "
            "Be specific and direct. This person can act on this now. No hedging."
        )
    else:
        conf_instruction = (
            "Confidence calibration: STANDARD — some context applies above. "
            "Incorporate the notes without over-qualifying."
        )

    # ── Build final block ────────────────────────────────────────
    if not checks and not warnings and not instructions:
        return ""

    lines = [f"COMMON SENSE LAYER — Reality checks (age {age}, {country_code}, {concern}):"]

    if checks:
        for c in checks:
            lines.append(f"  ✓ {c}")

    if warnings:
        for w in warnings:
            lines.append(f"  ⚠ {w}")

    if instructions:
        lines.append("\nINSTRUCTIONS FOR THIS PREDICTION:")
        for i, inst in enumerate(instructions, 1):
            lines.append(f"  {i}. {inst}")

    lines.append(f"\n{conf_instruction}")

    return "\n".join(lines)


# ── Rule helpers ──────────────────────────────────────────────────────────────

def _get_age_reframe(concern: str, age: Optional[int]) -> Optional[str]:
    """Return reframe instruction if age makes the concern inappropriate."""
    if age is None:
        return None
    rules = DOMAIN_AGE_RULES.get(concern, [])
    for (min_age, max_age, instruction) in rules:
        if min_age <= age < max_age:
            return instruction  # None = no reframe needed
    return None


def _get_life_stage_note(life_stage: Optional[str], concern: str) -> Optional[str]:
    """Return life stage calibration note for the concern."""
    if not life_stage:
        return None
    # Normalise life stage key
    stage_key = life_stage.lower().replace(" ", "_").replace("&", "and")
    # Try direct match first
    stage_notes = LIFE_STAGE_MODIFIERS.get(stage_key, {})
    # Try partial match
    if not stage_notes:
        for key in LIFE_STAGE_MODIFIERS:
            if key in stage_key or stage_key in key:
                stage_notes = LIFE_STAGE_MODIFIERS[key]
                break
    return stage_notes.get(concern)


def _get_marital_note(concern: str, marital_status: str) -> Optional[str]:
    """Return marital context note."""
    ms = (marital_status or "").lower()
    if concern == "love":
        if ms in ("married", "committed"):
            return ("Person is in a committed relationship. Love signals mean relationship "
                    "quality, depth, and renewal — not finding a new partner.")
        if ms in ("divorced", "separated"):
            return ("Person has been through separation. Love signals carry emotional weight. "
                    "Be sensitive — frame as healing and new possibility, not pressure.")
    if concern == "marriage":
        if ms in ("married", "committed"):
            return ("Person is already married. Marriage signals mean deepening, "
                    "renewal, or resolving tensions — not finding a spouse.")
        if ms == "single":
            return "Person is single. Marriage timing predictions are directly relevant."
    return None


def _get_children_note(children_status: str) -> Optional[str]:
    """Return children context note."""
    cs = (children_status or "").lower()
    if "has_children" in cs or cs == "yes":
        return ("Person already has children. Children signals mean parenting quality, "
                "relationship with children, or their wellbeing — not conception.")
    if "wants" in cs or cs == "no_children_wants":
        return ("Person wants children. Children predictions are directly relevant "
                "and should be taken literally with timing specificity.")
    if "no_children" in cs and "wants" not in cs:
        return ("Person does not have children and has not indicated wanting them. "
                "Reframe 5th house signals as creativity, intellect, and speculation.")
    return None


def _get_dkp_feasibility_note(
    concern: str,
    dkp_context: str,
    country_code: Optional[str]
) -> Optional[str]:
    """Extract feasibility note from DKP context for the concern."""
    dkp_lower = dkp_context.lower()

    if concern == "foreign":
        # Look for emigration line in DKP
        for line in dkp_context.split("\n"):
            if "emigration" in line.lower() or "immigration" in line.lower():
                return line.strip()
        return None

    if concern in ("career", "business"):
        # Look for growing sectors
        for line in dkp_context.split("\n"):
            if "growing:" in line.lower():
                return f"Growing sectors in {country_code}: {line.split(':', 1)[-1].strip()}"
        # Check period quality
        if "contraction" in dkp_lower:
            return (f"Economic contraction in {country_code} — "
                    "frame career/business advice conservatively.")
        if "expansion" in dkp_lower:
            return f"Economic expansion in {country_code} — career and business signals have tailwind."
        return None

    if concern == "wealth":
        if "inflation" in dkp_lower:
            for line in dkp_context.split("\n"):
                if "economic climate" in line.lower():
                    return line.strip()
        return None

    if concern == "funding":
        for line in dkp_context.split("\n"):
            if "contracting" in line.lower() and any(
                w in line.lower() for w in ["startup", "venture", "funding", "tech"]
            ):
                return (f"{line.strip()} — "
                        "bootstrap or govt scheme may be more viable than VC.")
        return None

    return None


def _detect_contradiction(memory_result: dict, concern: str) -> Optional[str]:
    """
    Detect if today's concern contradicts recent memory advice.
    Example: memory said 'avoid new ventures' but today is asking about business launch.
    """
    if not memory_result:
        return None

    past = memory_result.get("past_predictions", [])
    if not past:
        return None

    # Look at the last 3 predictions for the same domain
    same_domain = [
        p for p in past[:5]
        if p.get("concern") == concern or concern in (p.get("all_domains") or [])
    ]

    if len(same_domain) < 2:
        return None

    # Simple contradiction detection — look for opposing signal words
    CAUTION_WORDS  = ["avoid", "wait", "hold", "delay", "caution", "not the time", "pause"]
    FORWARD_WORDS  = ["move", "act", "launch", "start", "apply", "opportunity", "now"]

    recent_signal  = (same_domain[0].get("signal_line", "") or "").lower()
    previous_signal = (same_domain[1].get("signal_line", "") or "").lower()

    recent_cautious  = any(w in recent_signal for w in CAUTION_WORDS)
    previous_forward = any(w in previous_signal for w in FORWARD_WORDS)
    recent_forward   = any(w in recent_signal for w in FORWARD_WORDS)
    previous_cautious = any(w in previous_signal for w in CAUTION_WORDS)

    if (recent_cautious and previous_forward) or (recent_forward and previous_cautious):
        return (
            f"Previous {concern} signal suggested "
            f"'{'caution' if previous_cautious else 'action'}' "
            f"but today's signal suggests "
            f"'{'caution' if recent_cautious else 'action'}'"
        )

    return None
