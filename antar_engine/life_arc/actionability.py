"""
Actionability Layer — v5: WHY + WHAT TO DO + WHAT NOT TO DO + Remedies
=======================================================================
Transforms chart analysis into user-actionable guidance.

Every finding the signature produces gets an ActionabilityBlock answering:
  1. WHY — why is this showing up (plain language)
  2. WHAT TO DO — concrete action this week
  3. WHAT NOT TO DO — specific behavior to stop
  4. WHAT TO ACTIVATE — Lal Kitab remedy supporting positive direction
  5. WHAT TO DEACTIVATE — object/pattern/habit feeding the negative

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from .remedies.lal_kitab_database import LalKitabRemedy
from .remedies.remedy_selector import (
    select_appropriate_remedy,
    select_deactivation_remedy,
)


@dataclass
class ActionabilityBlock:
    finding_id: str
    finding_category: str       # POSITIVE | NEGATIVE | NEUTRAL
    severity: str               # high | moderate | low | peak

    why_plain_language: str
    what_to_do_now: str
    what_not_to_do: str

    lal_kitab_activation: Optional[Dict[str, Any]] = None
    lal_kitab_deactivation: Optional[Dict[str, str]] = None

    dasha_context: str = ""
    timeframe: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ─── FINDING EXTRACTORS ────────────────────────────────────────────────────

def _extract_findings(business_fit_result: dict) -> List[dict]:
    """
    Extract actionable findings from business_fit analyze output.
    Each finding becomes a dict with: id, category, severity, planet, detail.
    """
    findings = []

    # 1. Primary activation (yogakaraka)
    pa = business_fit_result.get("primary_activation")
    if pa:
        findings.append({
            "id": "yogakaraka_activation",
            "category": "POSITIVE",
            "severity": "high",
            "planet": pa.get("yogakaraka_planet"),
            "detail": pa,
        })

    # 2. Mahapurusha stack
    mp = business_fit_result.get("mahapurusha_stack", {})
    if mp.get("count", 0) >= 1:
        findings.append({
            "id": "mahapurusha_stack",
            "category": "POSITIVE",
            "severity": "peak" if mp.get("tier") == "stacked" else "high",
            "planet": None,  # Multiple planets
            "detail": mp,
        })

    # 3. Focus-split risk
    fs = business_fit_result.get("focus_split_risk")
    if fs:
        findings.append({
            "id": "focus_split_risk",
            "category": "NEGATIVE",
            "severity": fs.get("severity", "moderate"),
            "planet": "Rahu",
            "detail": fs,
        })

    # 4. Critical warnings (v4)
    for cw in business_fit_result.get("critical_warnings", []):
        findings.append({
            "id": cw.get("type", "unknown_warning"),
            "category": "NEGATIVE" if cw.get("severity") != "info" else "POSITIVE",
            "severity": cw.get("severity", "moderate"),
            "planet": _warning_type_to_planet(cw.get("type")),
            "detail": cw,
        })

    # 5. Wealth archetype
    wa = business_fit_result.get("wealth_archetype", {})
    if wa.get("primary_archetype"):
        findings.append({
            "id": f"archetype_{wa['primary_archetype'].lower()}",
            "category": "POSITIVE",
            "severity": "high" if wa.get("primary_score", 0) >= 6 else "moderate",
            "planet": None,
            "detail": wa,
        })

    # 6. Karmic warnings (D-60)
    for kw in business_fit_result.get("karmic_warnings", []):
        if isinstance(kw, str):
            # Parse "Mercury has Rakshasa karma..." format
            planet = kw.split(" ")[0] if kw else None
            findings.append({
                "id": f"d60_karma",
                "category": "NEGATIVE",
                "severity": "moderate",
                "planet": planet,
                "detail": {"warning": kw},
            })
        elif isinstance(kw, dict):
            findings.append({
                "id": "d60_karma",
                "category": "NEGATIVE",
                "severity": "moderate",
                "planet": kw.get("planet"),
                "detail": kw,
            })

    # 7. Dushthana wealth patterns (v3)
    dw = business_fit_result.get("dushthana_wealth", {})
    if dw.get("any_detected"):
        findings.append({
            "id": "dushthana_wealth_active",
            "category": "POSITIVE",
            "severity": "high",
            "planet": None,
            "detail": dw,
        })

    return findings


def _warning_type_to_planet(warning_type: Optional[str]) -> Optional[str]:
    """Map warning types to their primary planet."""
    mapping = {
        "viparita_stack": None,
        "identity_overwhelm": None,
        "moon_md_h2_pressure": "Moon",
        "hora_business_mismatch": None,
    }
    return mapping.get(warning_type)


# ─── WHY/DO/DON'T GENERATORS ───────────────────────────────────────────────

_WHY_TEMPLATES = {
    "yogakaraka_activation": (
        "Your hardest-working planet ({planet}) sits in a position that "
        "directly supports your wealth architecture. This is a core strength "
        "placement — it's your superpower, not a burden."
    ),
    "mahapurusha_stack": (
        "You have {count} of the rarest 'great-person' patterns simultaneously. "
        "This combination shows up in charts of people who build lasting institutions "
        "— not quick exits."
    ),
    "focus_split_risk": (
        "Your 11th house has multiple planets including your desire-amplification "
        "energy — this makes opportunities constantly appear, which feels like a "
        "blessing but historically causes you to run parallel ventures and compound none."
    ),
    "viparita_stack": (
        "Your chart has {count} rise-through-adversity patterns stacked. "
        "This is the architecture where crises become the engine, not the obstacle. "
        "The worse it looks, the bigger the outcome."
    ),
    "identity_overwhelm": (
        "Your chart concentrates {h1_count} planets in your identity house but "
        "your production houses are nearly empty. This makes you magnetic and "
        "respected, but wealth comes through who you ARE, not what you BUILD operationally."
    ),
    "moon_md_h2_pressure": (
        "Your emotional energy is running your life's current main chapter and "
        "it sits in your wealth house. This creates pressure to build 'bigger/more visible' "
        "wealth — the exact trap that pushes toward capital-heavy pivots."
    ),
    "hora_business_mismatch": (
        "Your wealth-type design favors {d2_channel} ventures, but "
        "your current top business category ({business_category}) opposes this. "
        "Historical pattern: people with your design lose capital in mismatched ventures."
    ),
    "dushthana_wealth_active": (
        "Your chart has active transformation-house wealth patterns. "
        "Classical readings mark these houses negatively, but in modern context "
        "they produce wealth through disruption, service, or foreign/digital channels."
    ),
    "d60_karma": (
        "Your karmic marker for {planet} carries a specific pattern needing "
        "resolution. In practice: honesty-tests and pattern-recurrence in "
        "{planet}'s domain will keep presenting until resolved well."
    ),
}

_DO_TEMPLATES = {
    "yogakaraka_activation": (
        "Commit fully to your primary vehicle. {planet} pays off through "
        "persistent disciplined work — not pivots, not side-bets."
    ),
    "mahapurusha_stack": (
        "Commit to institutional building. Use your partner/co-founder "
        "roles for partnerships and enterprise, not operations."
    ),
    "focus_split_risk": (
        "Designate ONE primary vehicle publicly (to yourself, to partners, "
        "to family). The other becomes secondary/delegated."
    ),
    "identity_overwhelm": (
        "Return to consulting/advisory — that's your chart's actual wealth "
        "channel. Leverage existing brand and relationships to advise, "
        "don't try to operate a platform yourself."
    ),
    "moon_md_h2_pressure": (
        "For any major business decision during this period: wait 72 hours "
        "after the emotional impulse before acting. Run it past someone with "
        "cold disciplined energy before committing capital."
    ),
    "hora_business_mismatch": (
        "Consider pivoting the venture concept toward your natural wealth-type "
        "expression. Instead of operating, advise/broker/consult to that industry."
    ),
    "d60_karma": (
        "Over-document every deal term in {planet}'s domain. Err on the side "
        "of transparent disclosure even when not strictly required."
    ),
    "dushthana_wealth_active": (
        "Lean into the transformation-house strength. Your chart's wealth engine "
        "runs through disruption and service channels, not traditional ones."
    ),
}

_DONT_TEMPLATES = {
    "yogakaraka_activation": (
        "Do not scatter across multiple ventures. Don't chase trends. "
        "Don't abandon your primary vehicle for a shinier opportunity."
    ),
    "mahapurusha_stack": (
        "Do not try to become a disruptive-founder type — your chart isn't "
        "built for that architecture. Do not take on solo operational ventures."
    ),
    "focus_split_risk": (
        "Don't take on a third venture. Don't let 'interesting opportunities' "
        "distract from execution focus."
    ),
    "identity_overwhelm": (
        "Do not re-enter physical operations, manufacturing, or capital-heavy "
        "infrastructure. Do not trust classical readings that call this a Raj Yoga "
        "without checking production-house activation."
    ),
    "moon_md_h2_pressure": (
        "Do not start new capital-heavy ventures during this period. "
        "Do not trust 'status-building' emotional conviction — "
        "it's the current life-chapter talking, not the chart's actual wealth architecture."
    ),
    "hora_business_mismatch": (
        "Do not add capital to ventures opposing your wealth-type design. "
        "Even at apparent opportunity, the structural mismatch will consume rather than compound."
    ),
    "d60_karma": (
        "Do not manipulate information asymmetry for gain in {planet}'s domain. "
        "Do not leave intentional ambiguity. The pattern specifically returns on these shortcuts."
    ),
    "dushthana_wealth_active": (
        "Don't fight the transformation-house placement by seeking 'safe' traditional "
        "ventures. Your chart's wealth engine needs disruption-compatible vehicles."
    ),
}


def _format_template(template: str, finding: dict) -> str:
    """Fill template with finding-specific data."""
    detail = finding.get("detail", {})
    planet = finding.get("planet", "this planet")

    replacements = {
        "planet": planet or "this planet",
        "count": str(detail.get("count", detail.get("viparita_count", "multiple"))),
        "h1_count": str(detail.get("h1_count", detail.get("h1_planets", "several"))),
        "d2_channel": detail.get("d2_channel", detail.get("dominant_channel", "your natural")),
        "business_category": detail.get("business_category", "current"),
    }

    result = template
    for k, v in replacements.items():
        result = result.replace(f"{{{k}}}", str(v))
    return result


# ─── MAIN ENRICHMENT FUNCTION ──────────────────────────────────────────────

def enrich_signature_with_actionability(
    business_fit_result: dict,
    chart_data: dict,
    user_context: Optional[dict] = None,
) -> List[ActionabilityBlock]:
    """
    For each finding in the signature output, attach ActionabilityBlock.

    Args:
        business_fit_result: Output from analyze_business_fit()
        chart_data: Full chart data dict
        user_context: Optional user preferences for remedy filtering

    Returns:
        List of ActionabilityBlock objects, one per significant finding.
    """
    findings = _extract_findings(business_fit_result)
    blocks = []

    for finding in findings:
        fid = finding["id"]
        category = finding["category"]
        severity = finding["severity"]
        planet = finding.get("planet")

        # Generate WHY / DO / DON'T
        # Use archetype-specific key if available, else generic
        base_key = fid.split("_")[0] if fid.startswith("archetype_") else fid
        if base_key.startswith("archetype"):
            # Archetype findings don't need standard templates
            why = finding["detail"].get("primary_description", "")
            do_now = f"Align ventures with {finding['detail'].get('primary_label', 'your')} archetype strengths."
            dont = f"Avoid ventures in the disfavored list: {', '.join(finding['detail'].get('disfavored_vehicles', [])[:2])}."
        else:
            why_tmpl = _WHY_TEMPLATES.get(fid, "")
            do_tmpl = _DO_TEMPLATES.get(fid, "")
            dont_tmpl = _DONT_TEMPLATES.get(fid, "")

            why = _format_template(why_tmpl, finding) if why_tmpl else ""
            do_now = _format_template(do_tmpl, finding) if do_tmpl else ""
            dont = _format_template(dont_tmpl, finding) if dont_tmpl else ""

        # Select activation remedy
        activation = None
        remedy = select_appropriate_remedy(
            finding_type=fid,
            finding_category=category,
            target_planet=planet,
            chart_data=chart_data,
            user_context=user_context,
        )
        if remedy:
            activation = {
                "remedy_id": remedy.remedy_id,
                "action": remedy.action,
                "materials": remedy.materials,
                "frequency": remedy.frequency,
                "duration": remedy.duration,
                "day_of_week": remedy.day_of_week,
                "expected_observation": remedy.expected_observation,
                "confidence": remedy.confidence,
            }

        # Select deactivation guidance
        deactivation = select_deactivation_remedy(fid, planet, chart_data)

        # Extract dasha context if available
        dasha_ctx = ""
        current_dasha = chart_data.get("current_dasha", {})
        if isinstance(current_dasha, dict):
            md = current_dasha.get("md_lord", "")
            ad = current_dasha.get("ad_lord", "")
            if md:
                dasha_ctx = f"Current main chapter: {md}"
                if ad:
                    dasha_ctx += f", sub-chapter: {ad}"

        # Determine timeframe
        timeframe = _determine_timeframe(fid, severity, category)

        block = ActionabilityBlock(
            finding_id=fid,
            finding_category=category,
            severity=severity,
            why_plain_language=why,
            what_to_do_now=do_now,
            what_not_to_do=dont,
            lal_kitab_activation=activation,
            lal_kitab_deactivation=deactivation,
            dasha_context=dasha_ctx,
            timeframe=timeframe,
        )
        blocks.append(block)

    return blocks


def _determine_timeframe(finding_id: str, severity: str, category: str) -> str:
    """Determine appropriate timeframe for action."""
    timeframes = {
        "yogakaraka_activation": "This season — commit and persist",
        "mahapurusha_stack": "Long-term institutional building (years)",
        "focus_split_risk": "Act before next dasha transition",
        "identity_overwhelm": "Begin transition this quarter",
        "moon_md_h2_pressure": "Through current life-chapter (2-3 years)",
        "hora_business_mismatch": "Before next major capital commitment",
        "dushthana_wealth_active": "Ongoing — lean into this strength",
    }

    tf = timeframes.get(finding_id)
    if tf:
        return tf

    if severity in ("high", "peak"):
        return "This week — take first step"
    elif category == "NEGATIVE":
        return "Next 3 months — course correct"
    else:
        return "This season"


def actionability_summary(blocks: List[ActionabilityBlock]) -> dict:
    """
    Produce a summary of all actionability blocks for API output.
    """
    positive = [b for b in blocks if b.finding_category == "POSITIVE"]
    negative = [b for b in blocks if b.finding_category == "NEGATIVE"]
    with_remedies = [b for b in blocks if b.lal_kitab_activation is not None]

    return {
        "total_findings": len(blocks),
        "positive_findings": len(positive),
        "negative_findings": len(negative),
        "remedies_available": len(with_remedies),
        "blocks": [b.to_dict() for b in blocks],
        "priority_action": blocks[0].what_to_do_now if blocks else "",
        "priority_avoidance": (
            negative[0].what_not_to_do if negative else ""
        ),
    }
