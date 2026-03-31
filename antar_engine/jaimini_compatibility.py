"""
Jaimini Compatibility Engine — Triple-Lock Synastry
====================================================
Antar v2.0 — Role-Based Compatibility (NOT Guna Milan)

This module implements a Jaimini-driven "DNA Match" between two soul purposes.
It runs three distinct layers for every compatibility check:

  Layer 1: Atmakaraka (AK) Connection — Soul Direction alignment
  Layer 2: Role-Karaka Match — Context-specific (Relationship / Business / Co-founder)
  Layer 3: Arudha Interaction — Public Image compatibility

Plus:
  Layer 4: Chara Dasha Timeline Sync — Chapter Alignment check
  Layer 5: Lal Kitab Enemy House Cross-Check

Author: Antar Engine Team
Date: March 31, 2026
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
from datetime import date


# ═══════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_TO_INDEX = {name: i for i, name in enumerate(SIGN_NAMES)}

SIGN_TYPES = {
    0: "movable", 1: "fixed", 2: "dual",
    3: "movable", 4: "fixed", 5: "dual",
    6: "movable", 7: "fixed", 8: "dual",
    9: "movable", 10: "fixed", 11: "dual",
}

# Favorable positions from one AL to another (1-indexed house distances)
FAVORABLE_AL_POSITIONS = {1, 5, 7, 9}

# Strong positions for Arudha compatibility
POWER_COUPLE_POSITIONS = {1, 5, 9}  # Trikona = "Power Couple"
COMPLEMENTARY_POSITIONS = {7}        # Opposition = complementary energy

# Chara Dasha phase labels
PHASE_LABELS = {
    "growth": "Growth Phase",
    "peak": "Peak Phase",
    "completion": "Completion Phase",
    "reset": "Reset Phase",
}


class CompatMode(Enum):
    RELATIONSHIP = "relationship"
    BUSINESS = "business"
    COFOUNDER = "cofounder"


# ═══════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════

@dataclass
class JaiminiChart:
    """Extracted Jaimini data for one person."""
    name: str
    # 7 Karakas: karaka_label -> {"planet": str, "sign_name": str, "sign_index": int}
    karakas: Dict[str, Dict]
    arudha_lagna: int        # sign index 0-11
    upapada_lagna: int       # sign index 0-11
    karakamsa: int           # sign index 0-11
    lagna: int               # sign index 0-11
    current_md_sign: int     # current Chara Dasha MD sign index
    current_ad_sign: int     # current Chara Dasha AD sign index
    md_years_remaining: float
    md_total_years: int
    planets_in_signs: Dict[int, List[str]] = field(default_factory=dict)

    @property
    def ak_sign(self) -> int:
        return self.karakas["AK"]["sign_index"]

    @property
    def amk_sign(self) -> int:
        return self.karakas["AmK"]["sign_index"]

    @property
    def dk_sign(self) -> int:
        return self.karakas["DK"]["sign_index"]

    @property
    def dasha_phase(self) -> str:
        """Determine life phase based on MD progress."""
        progress = 1.0 - (self.md_years_remaining / max(self.md_total_years, 1))
        if progress < 0.25:
            return "growth"
        elif progress < 0.60:
            return "peak"
        elif progress < 0.85:
            return "completion"
        else:
            return "reset"


@dataclass
class LayerResult:
    """Result of one synastry layer check."""
    layer_name: str
    layer_number: int
    passed: bool
    score: float          # 0.0 - 1.0
    headline: str
    detail: str
    badges: List[str] = field(default_factory=list)
    karaka_connections: List[Dict] = field(default_factory=list)


@dataclass
class SynastryReport:
    """Complete Triple-Lock Synastry result."""
    mode: CompatMode
    person_a: str
    person_b: str
    layers: List[LayerResult]
    convergence_score: float     # 0-100
    confidence: str              # "high" / "medium" / "low"
    timing_alignment: Dict
    headline: str
    summary: str
    warnings: List[str]
    catalysts: List[str]


# ═══════════════════════════════════════════════════════
# Core Jaimini Logic Functions
# ═══════════════════════════════════════════════════════

def sign_distance(from_sign: int, to_sign: int) -> int:
    """Calculate 1-indexed house distance from one sign to another."""
    return ((to_sign - from_sign) % 12) + 1


def get_rashi_drishti(sign_index: int) -> List[int]:
    """
    Return list of sign indices that a given sign aspects via Rashi Drishti.

    Movable (0,3,6,9) -> Fixed signs except adjacent
    Fixed (1,4,7,10) -> Movable signs except adjacent
    Dual (2,5,8,11) -> Other Dual signs
    """
    sign_type = SIGN_TYPES[sign_index]

    if sign_type == "movable":
        fixed_signs = [1, 4, 7, 10]
        adjacent = (sign_index + 1) % 12
        return [s for s in fixed_signs if s != adjacent]

    elif sign_type == "fixed":
        movable_signs = [0, 3, 6, 9]
        adjacent = (sign_index - 1) % 12
        return [s for s in movable_signs if s != adjacent]

    else:  # dual
        dual_signs = [2, 5, 8, 11]
        return [s for s in dual_signs if s != sign_index]


def signs_aspect_each_other(sign_a: int, sign_b: int) -> bool:
    """Check if sign_a aspects sign_b via Rashi Drishti (mutual or one-way)."""
    return sign_b in get_rashi_drishti(sign_a) or sign_a in get_rashi_drishti(sign_b)


def check_argala(source_sign: int, target_sign: int, planets_map: Dict[int, List[str]]) -> Dict:
    """
    Check if source_sign has Argala (intervention) on target_sign.
    Returns dict with argala_type and whether obstructed.
    """
    dist = sign_distance(target_sign, source_sign)
    result = {"has_argala": False, "type": None, "obstructed": False}

    if dist == 2:  # 2nd house argala
        obstruct_sign = (target_sign + 11) % 12  # 12th house
        result["has_argala"] = bool(planets_map.get(source_sign))
        result["type"] = "wealth_support"
        result["obstructed"] = bool(planets_map.get(obstruct_sign))

    elif dist == 4:  # 4th house argala
        obstruct_sign = (target_sign + 9) % 12  # 10th house
        result["has_argala"] = bool(planets_map.get(source_sign))
        result["type"] = "emotional_support"
        result["obstructed"] = bool(planets_map.get(obstruct_sign))

    elif dist == 11:  # 11th house argala
        obstruct_sign = (target_sign + 2) % 12  # 3rd house
        result["has_argala"] = bool(planets_map.get(source_sign))
        result["type"] = "gain_catalyst"
        result["obstructed"] = bool(planets_map.get(obstruct_sign))

    return result


# ═══════════════════════════════════════════════════════
# Layer 1: Atmakaraka (AK) Connection
# ═══════════════════════════════════════════════════════

def run_layer_1_ak_connection(a: JaiminiChart, b: JaiminiChart) -> LayerResult:
    """
    Check if Person A's AK aspects Person B's AK via Rashi Drishti.
    This determines if their souls are moving in the same direction.
    """
    ak_a = a.ak_sign
    ak_b = b.ak_sign

    # Check mutual Rashi Drishti between AK signs
    a_aspects_b = ak_b in get_rashi_drishti(ak_a)
    b_aspects_a = ak_a in get_rashi_drishti(ak_b)
    mutual = a_aspects_b and b_aspects_a

    # Check same sign
    same_sign = ak_a == ak_b

    # Check trikona (1, 5, 9) relationship
    dist = sign_distance(ak_a, ak_b)
    trikona = dist in {1, 5, 9}

    # Score calculation
    score = 0.0
    badges = []
    connections = []

    if same_sign:
        score = 1.0
        badges.append("Soul Twins")
        headline = "Soul Mirror Found"
        detail = (
            f"Both Atmakarakas occupy {SIGN_NAMES[ak_a]}. "
            f"This is exceedingly rare — your souls carry the same karmic signature. "
            f"Expect deep, almost telepathic understanding."
        )
    elif mutual:
        score = 0.90
        badges.append("Mutual Soul Aspect")
        headline = "Deep Karmic Resonance"
        detail = (
            f"{a.name}'s AK ({SIGN_NAMES[ak_a]}) and {b.name}'s AK ({SIGN_NAMES[ak_b]}) "
            f"mutually aspect each other. Your souls recognize each other — "
            f"this connection transcends circumstance."
        )
    elif a_aspects_b or b_aspects_a:
        score = 0.70
        direction = a.name if a_aspects_b else b.name
        receiver = b.name if a_aspects_b else a.name
        badges.append("One-Way Soul Aspect")
        headline = "Karmic Pull Detected"
        detail = (
            f"{direction}'s soul energy reaches {receiver}. "
            f"One person naturally pulls the other into their orbit. "
            f"This creates magnetism but requires conscious balance."
        )
    elif trikona:
        score = 0.55
        badges.append("Trikona Harmony")
        headline = "Harmonic Soul Frequency"
        detail = (
            f"AK signs are in a {dist}th house (trikona) relationship. "
            f"Your life purposes operate on the same frequency, "
            f"though through different expressions."
        )
    else:
        score = 0.25
        dist_actual = sign_distance(ak_a, ak_b)
        if dist_actual in {6, 8, 12}:
            badges.append("Karmic Friction")
            headline = "Karmic Friction Zone"
            detail = (
                f"AK signs are in a {dist_actual}th house relationship — "
                f"this creates friction that can be transformative if both parties "
                f"are committed to growth. Not a dealbreaker, but requires awareness."
            )
            score = 0.15
        else:
            headline = "Neutral Soul Alignment"
            detail = (
                f"AK signs don't directly aspect each other. "
                f"The connection won't be instinctive — it needs conscious cultivation."
            )

    connections.append({
        "from_karaka": "AK",
        "from_person": a.name,
        "from_sign": SIGN_NAMES[ak_a],
        "to_karaka": "AK",
        "to_person": b.name,
        "to_sign": SIGN_NAMES[ak_b],
        "aspect_type": "mutual" if mutual else ("one_way" if (a_aspects_b or b_aspects_a) else "none"),
    })

    return LayerResult(
        layer_name="Atmakaraka Connection",
        layer_number=1,
        passed=score >= 0.50,
        score=score,
        headline=headline,
        detail=detail,
        badges=badges,
        karaka_connections=connections,
    )


# ═══════════════════════════════════════════════════════
# Layer 2: Role-Karaka Match (Context-Dependent)
# ═══════════════════════════════════════════════════════

def run_layer_2_relationship(a: JaiminiChart, b: JaiminiChart) -> LayerResult:
    """
    Relationship mode: Analyze DK + UL of both charts.
    DK = Darakaraka (spouse karaka), UL = Upapada Lagna (marriage point).
    """
    score = 0.0
    badges = []
    connections = []
    findings = []

    # Check 1: A's DK aspects B's DK
    dk_aspect = signs_aspect_each_other(a.dk_sign, b.dk_sign)
    if dk_aspect:
        score += 0.30
        badges.append("DK Resonance")
        findings.append(
            f"Darakarakas connect — both charts carry compatible partner signatures."
        )
        connections.append({
            "from_karaka": "DK", "from_person": a.name, "from_sign": SIGN_NAMES[a.dk_sign],
            "to_karaka": "DK", "to_person": b.name, "to_sign": SIGN_NAMES[b.dk_sign],
            "aspect_type": "rashi_drishti",
        })

    # Check 2: A's DK sign matches B's UL or vice versa
    dk_ul_match = (a.dk_sign == b.upapada_lagna) or (b.dk_sign == a.upapada_lagna)
    if dk_ul_match:
        score += 0.30
        badges.append("DK-UL Lock")
        findings.append(
            f"One person's spouse indicator lands directly on the other's marriage point. "
            f"This is a classic Jaimini marriage signature."
        )

    # Check 3: UL to UL relationship
    ul_dist = sign_distance(a.upapada_lagna, b.upapada_lagna)
    ul_favorable = ul_dist in {1, 5, 7, 9}
    if ul_favorable:
        score += 0.20
        badges.append("UL Harmony")
        findings.append(
            f"Upapada Lagnas are in a favorable {ul_dist}th house relationship."
        )

    # Check 4: A's 7th from UL = B's lagna or vice versa
    a_7th_from_ul = (a.upapada_lagna + 6) % 12
    b_7th_from_ul = (b.upapada_lagna + 6) % 12
    if a_7th_from_ul == b.lagna or b_7th_from_ul == a.lagna:
        score += 0.20
        badges.append("Marriage Axis Aligned")
        findings.append(
            f"The marriage axis directly connects to the partner's identity."
        )

    score = min(score, 1.0)
    passed = score >= 0.40

    headline = (
        "Strong Relationship DNA" if score >= 0.70
        else "Compatible Patterns" if score >= 0.40
        else "Low Natural Affinity"
    )

    detail = " ".join(findings) if findings else (
        f"No strong DK or UL connections found between the charts. "
        f"The relationship may work, but the astrological 'pull' isn't innate."
    )

    return LayerResult(
        layer_name="Relationship DNA (DK + UL)",
        layer_number=2,
        passed=passed,
        score=score,
        headline=headline,
        detail=detail,
        badges=badges,
        karaka_connections=connections,
    )


def run_layer_2_business(a: JaiminiChart, b: JaiminiChart) -> LayerResult:
    """
    Business / Co-founder mode: Analyze AmK + Karakamsa.
    AmK = career DNA, Karakamsa = soul purpose.
    """
    score = 0.0
    badges = []
    connections = []
    findings = []

    # Check 1: AmK cross-aspect
    amk_aspect = signs_aspect_each_other(a.amk_sign, b.amk_sign)
    if amk_aspect:
        score += 0.25
        badges.append("Career DNA Link")
        findings.append(
            f"Amatyakarakas connect — both professional energies amplify each other."
        )
        connections.append({
            "from_karaka": "AmK", "from_person": a.name, "from_sign": SIGN_NAMES[a.amk_sign],
            "to_karaka": "AmK", "to_person": b.name, "to_sign": SIGN_NAMES[b.amk_sign],
            "aspect_type": "rashi_drishti",
        })

    # Check 2: A's AmK aspects B's 10th from AL (and vice versa)
    b_10th_from_al = (b.arudha_lagna + 9) % 12
    a_10th_from_al = (a.arudha_lagna + 9) % 12

    if a.amk_sign in get_rashi_drishti(b_10th_from_al) or a.amk_sign == b_10th_from_al:
        score += 0.25
        badges.append("Professional Catalyst")
        findings.append(
            f"{a.name}'s career energy directly activates {b.name}'s public authority zone. "
            f"Professional Catalyst Found."
        )

    if b.amk_sign in get_rashi_drishti(a_10th_from_al) or b.amk_sign == a_10th_from_al:
        score += 0.25
        if "Professional Catalyst" not in badges:
            badges.append("Professional Catalyst")
        findings.append(
            f"{b.name}'s career energy activates {a.name}'s public authority zone."
        )

    # Check 3: Karakamsa compatibility
    kl_dist = sign_distance(a.karakamsa, b.karakamsa)
    kl_favorable = kl_dist in {1, 5, 9, 10}
    if kl_favorable:
        score += 0.25
        badges.append("Soul Purpose Aligned")
        findings.append(
            f"Karakamsas are in a {kl_dist}th house relationship — "
            f"soul purposes are naturally complementary for shared ventures."
        )

    score = min(score, 1.0)
    passed = score >= 0.40

    headline = (
        "Strong Business DNA" if score >= 0.70
        else "Viable Partnership" if score >= 0.40
        else "Weak Professional Synergy"
    )

    detail = " ".join(findings) if findings else (
        f"No strong AmK or Karakamsa connections. "
        f"The business partnership lacks natural astrological catalysts."
    )

    return LayerResult(
        layer_name="Business DNA (AmK + Karakamsa)",
        layer_number=2,
        passed=passed,
        score=score,
        headline=headline,
        detail=detail,
        badges=badges,
        karaka_connections=connections,
    )


# ═══════════════════════════════════════════════════════
# Layer 3: Arudha Lagna Interaction (Public Image)
# ═══════════════════════════════════════════════════════

def run_layer_3_arudha(a: JaiminiChart, b: JaiminiChart, mode: CompatMode) -> LayerResult:
    """
    Check if Person A's AL is in a favorable position from Person B's AL.
    Favorable: 1, 5, 9 (Power Couple) or 7 (Complementary).
    """
    dist_a_to_b = sign_distance(a.arudha_lagna, b.arudha_lagna)
    dist_b_to_a = sign_distance(b.arudha_lagna, a.arudha_lagna)

    score = 0.0
    badges = []
    connections = []

    label = "Power Couple" if mode == CompatMode.RELATIONSHIP else "Successful Partnership"

    # Check both directions
    best_dist = min(dist_a_to_b, dist_b_to_a, key=lambda d: 0 if d in FAVORABLE_AL_POSITIONS else 1)

    if dist_a_to_b in POWER_COUPLE_POSITIONS or dist_b_to_a in POWER_COUPLE_POSITIONS:
        score = 0.90
        badges.append(label)
        headline = f"{label} Confirmed"
        detail = (
            f"Arudha Lagnas are in a trikona relationship — the world sees you as a {label.lower()}. "
            f"Your public images amplify each other naturally."
        )
    elif dist_a_to_b == 7 or dist_b_to_a == 7:
        score = 0.75
        badges.append("Complementary Image")
        headline = "Complementary Public Image"
        detail = (
            f"AL-to-AL in 7th house — the world sees you as a natural pair. "
            f"Your public identities fill each other's gaps."
        )
    elif dist_a_to_b in {2, 11} or dist_b_to_a in {2, 11}:
        score = 0.55
        badges.append("Wealth Amplifier")
        headline = "Material Synergy"
        detail = (
            f"AL relationship suggests mutual financial benefit. "
            f"Together, you attract more material success than apart."
        )
    elif dist_a_to_b in {6, 8, 12} and dist_b_to_a in {6, 8, 12}:
        score = 0.15
        badges.append("Image Friction")
        headline = "Public Image Clash"
        detail = (
            f"Arudha Lagnas are in a 6/8/12 relationship — "
            f"the world may not understand this partnership. "
            f"Success is possible but requires deliberate public positioning."
        )
    else:
        score = 0.35
        headline = "Neutral Public Perception"
        detail = (
            f"No strong Arudha connection. The partnership won't be remarkable to the outside world, "
            f"but won't face external resistance either."
        )

    connections.append({
        "from_karaka": "AL", "from_person": a.name, "from_sign": SIGN_NAMES[a.arudha_lagna],
        "to_karaka": "AL", "to_person": b.name, "to_sign": SIGN_NAMES[b.arudha_lagna],
        "aspect_type": "house_distance",
        "distance": dist_a_to_b,
    })

    return LayerResult(
        layer_name="Arudha Interaction (Public Image)",
        layer_number=3,
        passed=score >= 0.50,
        score=score,
        headline=headline,
        detail=detail,
        badges=badges,
        karaka_connections=connections,
    )


# ═══════════════════════════════════════════════════════
# Layer 4: Chara Dasha Timeline Sync
# ═══════════════════════════════════════════════════════

def run_layer_4_timing(a: JaiminiChart, b: JaiminiChart) -> Dict:
    """
    Compare Chara Dasha phases to check timeline alignment.
    Returns timing analysis dict (not a scored layer, but a warning system).
    """
    phase_a = a.dasha_phase
    phase_b = b.dasha_phase

    aligned = phase_a == phase_b
    compatible = (
        aligned
        or {phase_a, phase_b} == {"growth", "peak"}
        or {phase_a, phase_b} == {"peak", "completion"}
    )

    divergent = {phase_a, phase_b} == {"growth", "completion"} or {phase_a, phase_b} == {"reset", "peak"}

    if aligned:
        label = "Perfect Sync"
        detail = f"Both are in a {PHASE_LABELS[phase_a]}. You're in the same chapter of life."
        urgency = "none"
    elif compatible:
        label = "Compatible Timing"
        detail = (
            f"{a.name} is in a {PHASE_LABELS[phase_a]} while {b.name} is in a {PHASE_LABELS[phase_b]}. "
            f"These phases complement each other."
        )
        urgency = "low"
    elif divergent:
        label = "Timing Divergence"
        detail = (
            f"One is closing doors while the other is opening them. "
            f"{a.name}: {PHASE_LABELS[phase_a]}. {b.name}: {PHASE_LABELS[phase_b]}. "
            f"This doesn't mean failure — it means patience is required."
        )
        urgency = "high"
    else:
        label = "Neutral Timing"
        detail = (
            f"{a.name}: {PHASE_LABELS[phase_a]}. {b.name}: {PHASE_LABELS[phase_b]}. "
            f"No strong timing alignment or divergence."
        )
        urgency = "medium"

    # Check AD sync
    ad_aspect = signs_aspect_each_other(a.current_ad_sign, b.current_ad_sign)

    return {
        "label": label,
        "detail": detail,
        "urgency": urgency,
        "phase_a": PHASE_LABELS[phase_a],
        "phase_b": PHASE_LABELS[phase_b],
        "ad_sync": ad_aspect,
        "ad_detail": (
            "Current sub-periods aspect each other — immediate chemistry is strong."
            if ad_aspect else
            "Sub-periods don't connect right now — chemistry may take time to build."
        ),
    }


# ═══════════════════════════════════════════════════════
# Convergence Score Calculator
# ═══════════════════════════════════════════════════════

def calculate_convergence(layers: List[LayerResult], timing: Dict) -> Tuple[float, str]:
    """
    Calculate final convergence score from all layers.

    Weights:
    - Layer 1 (AK): 35% — soul alignment is foundational
    - Layer 2 (Role): 35% — context-specific match
    - Layer 3 (Arudha): 20% — public image
    - Timing bonus: 10%

    Returns (score 0-100, confidence label).
    """
    weights = {1: 0.35, 2: 0.35, 3: 0.20}
    weighted_sum = sum(
        layer.score * weights.get(layer.layer_number, 0)
        for layer in layers
    )

    # Timing bonus
    timing_bonus = 0.0
    if timing["urgency"] == "none":
        timing_bonus = 0.10
    elif timing["urgency"] == "low":
        timing_bonus = 0.06
    elif timing["urgency"] == "medium":
        timing_bonus = 0.02

    if timing["ad_sync"]:
        timing_bonus += 0.03

    raw_score = (weighted_sum + timing_bonus) * 100
    score = min(max(round(raw_score, 1), 0), 100)

    if score >= 75:
        confidence = "high"
    elif score >= 50:
        confidence = "medium"
    else:
        confidence = "low"

    return score, confidence


# ═══════════════════════════════════════════════════════
# Main Engine: run_compatibility()
# ═══════════════════════════════════════════════════════

def run_compatibility(
    chart_a: JaiminiChart,
    chart_b: JaiminiChart,
    mode: CompatMode = CompatMode.RELATIONSHIP
) -> SynastryReport:
    """
    Run the complete Triple-Lock Synastry analysis.

    Args:
        chart_a: JaiminiChart for Person A
        chart_b: JaiminiChart for Person B
        mode: CompatMode (relationship / business / cofounder)

    Returns:
        SynastryReport with all layers, score, and insights
    """
    layers = []

    # Layer 1: AK Connection (same for all modes)
    layer_1 = run_layer_1_ak_connection(chart_a, chart_b)
    layers.append(layer_1)

    # Layer 2: Role-specific
    if mode == CompatMode.RELATIONSHIP:
        layer_2 = run_layer_2_relationship(chart_a, chart_b)
    else:
        layer_2 = run_layer_2_business(chart_a, chart_b)
    layers.append(layer_2)

    # Layer 3: Arudha Interaction
    layer_3 = run_layer_3_arudha(chart_a, chart_b, mode)
    layers.append(layer_3)

    # Layer 4: Timing
    timing = run_layer_4_timing(chart_a, chart_b)

    # Convergence
    score, confidence = calculate_convergence(layers, timing)

    # Collect all badges
    all_badges = []
    for layer in layers:
        all_badges.extend(layer.badges)

    # Generate warnings
    warnings = []
    if not layer_1.passed:
        warnings.append(
            "Soul alignment is weak. This connection needs conscious effort to sustain."
        )
    if timing["urgency"] == "high":
        warnings.append(
            f"Timing Divergence: {timing['detail']}"
        )
    if not layer_3.passed:
        warnings.append(
            "Public image compatibility is low — the world may question this pairing."
        )

    # Generate catalysts
    catalysts = []
    for layer in layers:
        for conn in layer.karaka_connections:
            if conn["aspect_type"] in ("mutual", "rashi_drishti"):
                catalysts.append(
                    f"{conn['from_karaka']} ({conn['from_person']}) → "
                    f"{conn['to_karaka']} ({conn['to_person']}): "
                    f"{SIGN_NAMES[SIGN_TO_INDEX[conn['from_sign']]]} ↔ {conn['to_sign']}"
                )

    # Generate headline and summary
    passed_count = sum(1 for l in layers if l.passed)
    if passed_count == 3:
        headline = "Triple-Lock Verified ✓"
        summary = (
            f"All three synastry layers align. This {mode.value} connection has strong "
            f"astrological backing across soul, role, and public dimensions."
        )
    elif passed_count == 2:
        headline = "Double-Lock Confirmed"
        summary = (
            f"Two of three layers confirm compatibility. The connection is viable "
            f"with awareness of the weaker dimension."
        )
    elif passed_count == 1:
        headline = "Single Lock Only"
        summary = (
            f"Only one compatibility layer is strong. This {mode.value} may face challenges "
            f"unless both parties consciously address the gaps."
        )
    else:
        headline = "No Locks Engaged"
        summary = (
            f"None of the three synastry layers show strong alignment. "
            f"This doesn't guarantee failure, but the connection lacks natural astrological support."
        )

    return SynastryReport(
        mode=mode,
        person_a=chart_a.name,
        person_b=chart_b.name,
        layers=layers,
        convergence_score=score,
        confidence=confidence,
        timing_alignment=timing,
        headline=headline,
        summary=summary,
        warnings=warnings,
        catalysts=catalysts,
    )


def synastry_to_json(report: SynastryReport) -> Dict:
    """Convert SynastryReport to JSON-serializable dict for API response and DB storage."""
    return {
        "mode": report.mode.value,
        "person_a": report.person_a,
        "person_b": report.person_b,
        "convergence_score": report.convergence_score,
        "confidence": report.confidence,
        "headline": report.headline,
        "summary": report.summary,
        "layers": [
            {
                "layer_number": l.layer_number,
                "layer_name": l.layer_name,
                "passed": l.passed,
                "score": round(l.score, 3),
                "headline": l.headline,
                "detail": l.detail,
                "badges": l.badges,
                "karaka_connections": l.karaka_connections,
            }
            for l in report.layers
        ],
        "timing_alignment": report.timing_alignment,
        "warnings": report.warnings,
        "catalysts": report.catalysts,
    }


def synastry_to_prompt_block(report: SynastryReport) -> str:
    """Format synastry result as an LLM system prompt block for Ask Antar."""
    lines = [
        f"COMPATIBILITY ANALYSIS ({report.mode.value.upper()})",
        f"Persons: {report.person_a} × {report.person_b}",
        f"Convergence: {report.convergence_score}% ({report.confidence})",
        f"Verdict: {report.headline}",
        "",
    ]
    for layer in report.layers:
        status = "PASS" if layer.passed else "FAIL"
        lines.append(f"  Layer {layer.layer_number} [{status}]: {layer.headline}")
        lines.append(f"    {layer.detail}")
        if layer.badges:
            lines.append(f"    Badges: {', '.join(layer.badges)}")
        lines.append("")

    lines.append(f"  Timing: {report.timing_alignment['label']}")
    lines.append(f"    {report.timing_alignment['detail']}")

    if report.warnings:
        lines.append("")
        lines.append("  WARNINGS:")
        for w in report.warnings:
            lines.append(f"    - {w}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# Integration: build_from_jaimini_data()
# ═══════════════════════════════════════════════════════

def build_chart_from_jaimini_data(name: str, jaimini_data: Dict, lagna_index: int) -> JaiminiChart:
    """
    Build a JaiminiChart from stored jaimini_data JSONB.
    This connects to the existing DB schema where jaimini_data is stored on the charts table.
    """
    karakas_raw = jaimini_data.get("karakas", [])
    karakas = {}
    for k in karakas_raw:
        karakas[k["karaka"]] = {
            "planet": k["planet"],
            "sign_name": k["sign_name"],
            "sign_index": SIGN_TO_INDEX.get(k["sign_name"], 0),
        }

    al = SIGN_TO_INDEX.get(jaimini_data.get("arudha_lagna", {}).get("sign_name", "Aries"), 0)
    ul = SIGN_TO_INDEX.get(jaimini_data.get("upapada_lagna", {}).get("sign_name", "Aries"), 0)
    kl = SIGN_TO_INDEX.get(jaimini_data.get("karakamsa", {}).get("sign_name", "Aries"), 0)

    md = jaimini_data.get("current_md", {})
    ad = jaimini_data.get("current_ad", {})

    md_sign = SIGN_TO_INDEX.get(md.get("sign_name", "Aries"), 0)
    ad_sign = SIGN_TO_INDEX.get(ad.get("sign_name", "Aries"), 0)

    md_years = md.get("years", 8)
    # Calculate remaining years from end date
    md_end = md.get("end", "2032-01-01")
    try:
        end_date = date.fromisoformat(md_end[:10])
        remaining = (end_date - date.today()).days / 365.25
    except Exception:
        remaining = md_years / 2

    return JaiminiChart(
        name=name,
        karakas=karakas,
        arudha_lagna=al,
        upapada_lagna=ul,
        karakamsa=kl,
        lagna=lagna_index,
        current_md_sign=md_sign,
        current_ad_sign=ad_sign,
        md_years_remaining=max(remaining, 0),
        md_total_years=md_years,
    )
