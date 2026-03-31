"""
Jaimini Compatibility Engine v2 — Complete 6-Layer Synastry
=============================================================
Antar v2.0 — Role-Based Compatibility

6 Layers:
  1. Atmakaraka (AK) Connection — Soul Direction
  2. Role-Karaka Match — DK+UL (relationship) or AmK+KL (business)
     Now includes: DK cross-match vs partner's AK/AmK
  3. Arudha Interaction — Public Image
  4. Nakshatra Kuta — Modernized traditional matching
  5. DKP (Desh Kal Patra) — Real-world context (country, age, economics)
  6. Timing + Lal Kitab — Relationship-active dashas + LK enemy house check

Output rule: Show conclusions, not calculations.

Author: Antar Engine Team
Date: March 31, 2026
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import date
import math


# ═══════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
SIGN_TO_INDEX = {name: i for i, name in enumerate(SIGN_NAMES)}

NAKSHATRAS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]
NAK_TO_INDEX = {n: i for i, n in enumerate(NAKSHATRAS)}

# Nakshatra Kuta tables
NADI_GROUPS = [0,1,2]*9  # Adi=0, Madhya=1, Antya=2, cycling
GANA = [
    "Deva","Manushya","Rakshasa","Deva","Manushya","Rakshasa",
    "Deva","Manushya","Rakshasa","Rakshasa","Manushya","Deva",
    "Deva","Rakshasa","Deva","Rakshasa","Deva","Rakshasa",
    "Rakshasa","Manushya","Manushya","Deva","Rakshasa","Rakshasa",
    "Manushya","Manushya","Deva"
]
YONI_ANIMALS = [
    "Horse","Elephant","Goat","Serpent","Dog","Cat","Rat","Goat","Cat",
    "Rat","Cow","Bull","Buffalo","Tiger","Buffalo","Deer","Deer","Hare",
    "Dog","Monkey","Mongoose","Monkey","Lion","Horse","Lion","Cow","Elephant"
]
YONI_ENEMIES = {
    "Horse": "Buffalo", "Buffalo": "Horse",
    "Elephant": "Lion", "Lion": "Elephant",
    "Dog": "Hare", "Hare": "Dog",
    "Cat": "Rat", "Rat": "Cat",
    "Goat": "Monkey", "Monkey": "Goat",
    "Serpent": "Mongoose", "Mongoose": "Serpent",
    "Cow": "Tiger", "Tiger": "Cow",
    "Deer": "Dog", "Bull": "Bull",
}

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
    """Complete Jaimini chart data for compatibility."""
    name: str
    age: int
    country: str
    country_label: str
    nakshatra: str
    moon_sign: int
    karakas: Dict[str, Dict]  # {label: {planet, sign_name, sign_index}}
    arudha_lagna: int
    upapada_lagna: int
    karakamsa: int
    lagna: int
    current_md_sign: int
    current_ad_sign: int
    md_years_remaining: float
    md_total_years: int
    vimsottari_md: str = ""
    vimsottari_ad: str = ""
    lk_enemy_houses: List[int] = field(default_factory=list)
    lk_sleeping_planets: List[str] = field(default_factory=list)
    planets_in_signs: Dict[int, List[str]] = field(default_factory=dict)

    @property
    def ak_sign(self) -> int:
        return self.karakas.get("AK", {}).get("sign_index", 0)

    @property
    def amk_sign(self) -> int:
        return self.karakas.get("AmK", {}).get("sign_index", 0)

    @property
    def dk_sign(self) -> int:
        return self.karakas.get("DK", {}).get("sign_index", 0)

    @property
    def dasha_phase(self) -> str:
        progress = 1.0 - (self.md_years_remaining / max(self.md_total_years, 1))
        if progress < 0.25: return "growth"
        elif progress < 0.60: return "peak"
        elif progress < 0.85: return "completion"
        else: return "reset"


@dataclass
class LayerResult:
    """Result from one compatibility layer."""
    layer_id: str
    layer_number: int
    layer_name: str
    weight: float
    passed: bool
    score: float
    headline: str
    detail: str
    badge: str = ""
    badges: List[str] = field(default_factory=list)
    extra: Dict = field(default_factory=dict)


@dataclass
class CompatibilityReport:
    """Complete 6-layer compatibility result."""
    mode: CompatMode
    person_a: str
    person_b: str
    layers: List[LayerResult]
    convergence_score: float
    confidence: str
    headline: str
    summary: str
    passed_count: int
    warnings: List[str]
    catalysts: List[str]
    strongest_layer: str
    weakest_layer: str


# ═══════════════════════════════════════════════════════
# Core Functions
# ═══════════════════════════════════════════════════════

def sign_distance(from_sign: int, to_sign: int) -> int:
    return ((to_sign - from_sign) % 12) + 1


def get_rashi_drishti(sign_idx: int) -> List[int]:
    mod = sign_idx % 3
    if mod == 0:  # movable
        return [s for s in [1, 4, 7, 10] if s != (sign_idx + 1) % 12]
    elif mod == 1:  # fixed
        return [s for s in [0, 3, 6, 9] if s != (sign_idx - 1) % 12]
    else:  # dual
        return [s for s in [2, 5, 8, 11] if s != sign_idx]


def signs_aspect(a: int, b: int) -> bool:
    return b in get_rashi_drishti(a) or a in get_rashi_drishti(b)


# ═══════════════════════════════════════════════════════
# Nakshatra Kuta Engine
# ═══════════════════════════════════════════════════════

def compute_nakshatra_kuta(nak_a: str, nak_b: str) -> Dict:
    """Compute modernized Kuta matching. Returns score/36 with details."""
    idx_a = NAK_TO_INDEX.get(nak_a, -1)
    idx_b = NAK_TO_INDEX.get(nak_b, -1)
    if idx_a < 0 or idx_b < 0:
        return {"score": 0, "max": 36, "percentage": 0, "details": []}

    total = 0
    details = []

    # 1. Nadi (8 pts)
    nadi_ok = NADI_GROUPS[idx_a] != NADI_GROUPS[idx_b]
    pts = 8 if nadi_ok else 0
    total += pts
    details.append({
        "name": "Nadi", "pts": pts, "max": 8,
        "label": "Different constitution — healthy" if nadi_ok else "Same constitution — needs awareness"
    })

    # 2. Gana (6 pts)
    ga, gb = GANA[idx_a], GANA[idx_b]
    if ga == gb:
        pts = 6
    elif "Rakshasa" in (ga, gb) and ga != gb:
        pts = 0
    else:
        pts = 3
    total += pts
    details.append({
        "name": "Gana", "pts": pts, "max": 6,
        "label": f"{ga} × {gb}: {'Same temperament' if pts == 6 else 'Temperament clash' if pts == 0 else 'Manageable'}"
    })

    # 3. Yoni (4 pts)
    ya, yb = YONI_ANIMALS[idx_a], YONI_ANIMALS[idx_b]
    if ya == yb:
        pts = 4
    elif YONI_ENEMIES.get(ya) == yb:
        pts = 0
    else:
        pts = 2
    total += pts
    details.append({
        "name": "Yoni", "pts": pts, "max": 4,
        "label": f"{ya} × {yb}: {'Same nature' if pts == 4 else 'Natural tension' if pts == 0 else 'Compatible'}"
    })

    # 4. Bhakoot (7 pts)
    sign_a = (idx_a * 12) // 27
    sign_b = (idx_b * 12) // 27
    dist = sign_distance(sign_a, sign_b)
    dist_r = sign_distance(sign_b, sign_a)
    bhak_bad = dist in {6, 8, 12} or dist_r in {6, 8, 12}
    pts = 0 if bhak_bad else 7
    total += pts
    details.append({
        "name": "Bhakoot", "pts": pts, "max": 7,
        "label": "Moon signs harmonious" if pts == 7 else "6/8/12 axis — financial/health friction"
    })

    # 5. Tara (3 pts)
    tara = ((idx_b - idx_a + 27) % 27) % 9
    tara_bad = tara in {2, 4, 6, 8}
    pts = 0 if tara_bad else 3
    total += pts
    details.append({
        "name": "Tara", "pts": pts, "max": 3,
        "label": "Favorable star alignment" if pts == 3 else "Challenging star axis"
    })

    # 6-8. Simplified secondary markers
    secondary = 5 if not bhak_bad and not tara_bad else 2
    total += secondary
    details.append({
        "name": "Vashya+Dina+Mahendra", "pts": secondary, "max": 8,
        "label": "Secondary compatibility markers"
    })

    total = min(total, 36)
    return {
        "score": total,
        "max": 36,
        "percentage": round((total / 36) * 100),
        "details": details,
    }


# ═══════════════════════════════════════════════════════
# Layer Functions
# ═══════════════════════════════════════════════════════

def layer_1_ak_connection(a: JaiminiChart, b: JaiminiChart) -> LayerResult:
    ak_a, ak_b = a.ak_sign, b.ak_sign
    mutual = ak_b in get_rashi_drishti(ak_a) and ak_a in get_rashi_drishti(ak_b)
    one_way = ak_b in get_rashi_drishti(ak_a) or ak_a in get_rashi_drishti(ak_b)
    same = ak_a == ak_b
    dist = sign_distance(ak_a, ak_b)
    trikona = dist in {1, 5, 9}

    if same:
        return LayerResult("ak", 1, "Soul Direction", 0.20, True, 1.0,
            "Your souls speak the same language",
            f"Both AKs in {SIGN_NAMES[ak_a]}. Rare — same karmic signature.",
            badge="Soul Twins")
    elif mutual:
        return LayerResult("ak", 1, "Soul Direction", 0.20, True, 0.90,
            "Deep karmic resonance",
            f"{a.name}'s AK ({SIGN_NAMES[ak_a]}) and {b.name}'s AK ({SIGN_NAMES[ak_b]}) mutually aspect. Souls recognize each other.",
            badge="Mutual Lock")
    elif one_way:
        return LayerResult("ak", 1, "Soul Direction", 0.20, True, 0.68,
            "One soul reaches for the other",
            "Natural magnetism flows more in one direction. Awareness keeps it healthy.",
            badge="Karmic Pull")
    elif trikona:
        return LayerResult("ak", 1, "Soul Direction", 0.20, True, 0.55,
            "Same frequency, different channel",
            "Soul purposes harmonize naturally through different expressions.",
            badge="Trikona")
    elif dist in {6, 8, 12}:
        return LayerResult("ak", 1, "Soul Direction", 0.20, False, 0.15,
            "Transformative tension",
            f"{dist}th house axis creates friction. Growth accelerator if both are willing.",
            badge="Friction")
    else:
        return LayerResult("ak", 1, "Soul Direction", 0.20, False, 0.30,
            "No instinctive soul pull",
            "Connection needs intentional cultivation — it won't just happen.",
            badge="Neutral")


def layer_2_relationship(a: JaiminiChart, b: JaiminiChart) -> LayerResult:
    score = 0.0
    badges = []
    findings = []

    # DK cross-match: your DK vs their AK/AmK (the new requirement)
    dk_cross_a = signs_aspect(a.dk_sign, b.ak_sign) or signs_aspect(a.dk_sign, b.amk_sign)
    dk_cross_b = signs_aspect(b.dk_sign, a.ak_sign) or signs_aspect(b.dk_sign, a.amk_sign)
    if dk_cross_a or dk_cross_b:
        score += 0.25
        badges.append("Cross-Karaka Link")
        findings.append("Partner indicators connect to each other's core identity — not just surface attraction.")

    # DK↔DK
    if signs_aspect(a.dk_sign, b.dk_sign):
        score += 0.20
        badges.append("DK Resonance")

    # DK-UL lock
    if a.dk_sign == b.upapada_lagna or b.dk_sign == a.upapada_lagna:
        score += 0.25
        badges.append("DK-UL Lock")
        findings.append("Classic Jaimini marriage signature.")

    # UL alignment
    ul_dist = sign_distance(a.upapada_lagna, b.upapada_lagna)
    if ul_dist in {1, 5, 7, 9}:
        score += 0.15
        badges.append("UL Harmony")

    # Marriage axis
    if (a.upapada_lagna + 6) % 12 == b.lagna or (b.upapada_lagna + 6) % 12 == a.lagna:
        score += 0.15
        badges.append("Marriage Axis")

    score = min(score, 1.0)
    if score >= 0.65:
        headline = "Strong romantic chemistry"
    elif score >= 0.35:
        headline = "Compatible but not magnetic"
    else:
        headline = "Low natural romantic pull"

    detail = " ".join(findings) if findings else "No strong DK or UL connections."

    return LayerResult("role", 2, "Relationship DNA", 0.20, score >= 0.35,
        score, headline, detail, badges=badges)


def layer_2_business(a: JaiminiChart, b: JaiminiChart) -> LayerResult:
    score = 0.0
    badges = []
    findings = []

    if signs_aspect(a.amk_sign, b.amk_sign):
        score += 0.25
        badges.append("Career DNA Link")
        findings.append("Professional energies amplify each other.")

    # Professional Catalyst: AmK→10th from partner's AL
    b_10 = (b.arudha_lagna + 9) % 12
    a_10 = (a.arudha_lagna + 9) % 12

    if a.amk_sign == b_10 or a.amk_sign in get_rashi_drishti(b_10):
        score += 0.25
        badges.append("Professional Catalyst")
        findings.append(f"{a.name}'s career energy activates {b.name}'s authority zone.")

    if b.amk_sign == a_10 or b.amk_sign in get_rashi_drishti(a_10):
        score += 0.25
        findings.append(f"{b.name}'s career energy activates {a.name}'s authority zone.")

    kl_dist = sign_distance(a.karakamsa, b.karakamsa)
    if kl_dist in {1, 5, 9, 10}:
        score += 0.25
        badges.append("Soul Purpose Aligned")
        findings.append("Soul purposes are complementary for shared ventures.")

    score = min(score, 1.0)
    headline = "Strong professional synergy" if score >= 0.65 else \
               "Viable partnership" if score >= 0.35 else "Weak professional match"

    return LayerResult("role", 2, "Business DNA", 0.20, score >= 0.35,
        score, headline, " ".join(findings) if findings else "No strong connections.",
        badges=badges)


def layer_3_arudha(a: JaiminiChart, b: JaiminiChart, mode: CompatMode) -> LayerResult:
    al_dist = sign_distance(a.arudha_lagna, b.arudha_lagna)
    al_dist_r = sign_distance(b.arudha_lagna, a.arudha_lagna)
    label = "power couple" if mode == CompatMode.RELATIONSHIP else "successful partnership"

    if al_dist in {1, 5, 9} or al_dist_r in {1, 5, 9}:
        return LayerResult("arudha", 3, "Public Image", 0.15, True, 0.90,
            f"The world sees you as a {label}",
            "Public images amplify each other naturally.", badge="Power Pair")
    elif al_dist == 7 or al_dist_r == 7:
        return LayerResult("arudha", 3, "Public Image", 0.15, True, 0.75,
            "You fill each other's public gaps",
            "Complementary Arudhas — natural pairing.", badge="Complementary")
    elif al_dist in {2, 11} or al_dist_r in {2, 11}:
        return LayerResult("arudha", 3, "Public Image", 0.15, True, 0.55,
            "Together you attract more money",
            "Material synergy — combined image draws opportunities.", badge="Wealth Sync")
    elif al_dist in {6, 8, 12} and al_dist_r in {6, 8, 12}:
        return LayerResult("arudha", 3, "Public Image", 0.15, False, 0.15,
            "The world may not understand this",
            "Public image clash — requires deliberate positioning.", badge="Low Visibility")
    else:
        return LayerResult("arudha", 3, "Public Image", 0.15, False, 0.35,
            "Neither remarkable nor resistant",
            "No strong Arudha connection.", badge="Neutral")


def layer_4_nakshatra(a: JaiminiChart, b: JaiminiChart) -> LayerResult:
    kuta = compute_nakshatra_kuta(a.nakshatra, b.nakshatra)
    pct = kuta["percentage"]
    passed = pct >= 50

    if pct >= 70:
        headline = "Strong natural compatibility"
    elif pct >= 50:
        headline = "Workable with effort"
    else:
        headline = "Low traditional compatibility — Jaimini layers matter more"

    return LayerResult("nakshatra", 4, "Nakshatra Match", 0.15, passed,
        pct / 100.0, headline,
        f"{kuta['score']}/{kuta['max']} points. {a.nakshatra} × {b.nakshatra}.",
        badge="Strong Kuta" if pct >= 70 else "Moderate" if pct >= 50 else "Low Kuta",
        extra={"kuta": kuta})


def layer_5_dkp(a: JaiminiChart, b: JaiminiChart, mode: CompatMode) -> LayerResult:
    """Desh Kal Patra — real-world context layer."""
    score = 1.0
    findings = []

    same_country = a.country == b.country
    age_diff = abs(a.age - b.age)
    age_threshold = 15 if mode == CompatMode.RELATIONSHIP else 25

    if same_country:
        findings.append(f"Both in {a.country_label} — shared economic and cultural context.")
    else:
        score -= 0.25
        findings.append(f"Cross-border: {a.country_label} × {b.country_label}. Different economic cycles.")

    if age_diff > age_threshold:
        score -= 0.20
        findings.append(f"{age_diff}-year gap: different life stages and career windows.")
    else:
        findings.append(f"{age_diff}-year gap is manageable for {mode.value} context.")

    if same_country and age_diff <= age_threshold:
        findings.append("Shared context amplifies all other compatibility signals.")

    score = max(score, 0.0)
    passed = score >= 0.60

    if score >= 0.80:
        headline = "Same world, same rules"
        badge = "Context Match"
    elif score >= 0.50:
        headline = "Some real-world friction"
        badge = "Mixed Context"
    else:
        headline = "Different worlds — practical challenges ahead"
        badge = "Context Gap"

    return LayerResult("dkp", 5, "Real-World Context", 0.10, passed,
        score, headline, " ".join(findings), badge=badge)


def layer_6_timing_lk(a: JaiminiChart, b: JaiminiChart, mode: CompatMode) -> LayerResult:
    """Timing check + Lal Kitab enemy house cross-check."""
    # LK enemy house check
    enemy_overlap = [h for h in a.lk_enemy_houses if h in b.lk_enemy_houses]
    sleeping_conflict = any(
        p in [k.get("planet", "") for k in b.karakas.values()]
        for p in a.lk_sleeping_planets
    )
    lk_clear = len(enemy_overlap) == 0 and not sleeping_conflict
    lk_conflicts = []
    if enemy_overlap:
        lk_conflicts.append(f"Shared enemy houses: {enemy_overlap}. Karmic debt amplifies.")
    if sleeping_conflict:
        lk_conflicts.append("Sleeping planet matches partner's key karaka — energy misalignment.")

    # Phase analysis
    phase_a = a.dasha_phase
    phase_b = b.dasha_phase
    aligned = phase_a == phase_b
    compatible_phases = {frozenset({"growth", "peak"}), frozenset({"peak", "completion"})}
    compatible = aligned or frozenset({phase_a, phase_b}) in compatible_phases
    divergent_phases = {frozenset({"growth", "completion"}), frozenset({"reset", "peak"})}
    divergent = frozenset({phase_a, phase_b}) in divergent_phases

    # Relationship-active dasha check (marriage event logic)
    def is_rel_active(chart: JaiminiChart) -> bool:
        md_to_ul = sign_distance(chart.current_md_sign, chart.upapada_lagna)
        al_7 = sign_distance(chart.current_md_sign, chart.arudha_lagna)
        dk_aspect = signs_aspect(chart.current_md_sign, chart.dk_sign)
        return md_to_ul in {1, 2, 7} or al_7 == 7 or dk_aspect

    a_rel_active = is_rel_active(a)
    b_rel_active = is_rel_active(b)
    both_rel_active = a_rel_active and b_rel_active

    # Score
    if aligned:
        timing_score = 1.0
    elif compatible:
        timing_score = 0.70
    elif divergent:
        timing_score = 0.20
    else:
        timing_score = 0.50

    if mode == CompatMode.RELATIONSHIP:
        if both_rel_active:
            timing_score = min(timing_score + 0.20, 1.0)
        elif not a_rel_active and not b_rel_active:
            timing_score = max(timing_score - 0.15, 0.0)

    # Apply LK penalty
    final_score = timing_score if lk_clear else timing_score * 0.70

    # Headline
    if not lk_clear:
        headline = "Karmic friction detected"
    elif mode == CompatMode.RELATIONSHIP and both_rel_active:
        headline = "Both in relationship-active windows right now"
    elif aligned:
        headline = "Perfect sync — same chapter of life"
    elif compatible:
        headline = "Compatible timing"
    elif divergent:
        headline = "One is closing doors, the other is opening them"
    else:
        headline = "Neutral timing"

    detail_parts = []
    if lk_conflicts:
        detail_parts.extend(lk_conflicts)
    detail_parts.append(f"{a.name}: {PHASE_LABELS[phase_a]}. {b.name}: {PHASE_LABELS[phase_b]}.")
    if mode == CompatMode.RELATIONSHIP and both_rel_active:
        detail_parts.append("Both dashas activate the marriage axis.")

    passed = final_score >= 0.50 and lk_clear

    return LayerResult("timing_lk", 6, "Timing & Karma", 0.20, passed,
        final_score, headline, " ".join(detail_parts),
        badge="Karma Alert" if not lk_clear else ("Timing ✓" if timing_score >= 0.70 else "Timing ~"),
        extra={
            "timing": {
                "phase_a": PHASE_LABELS[phase_a],
                "phase_b": PHASE_LABELS[phase_b],
                "aligned": aligned,
                "divergent": divergent,
                "both_rel_active": both_rel_active,
                "a_rel_active": a_rel_active,
                "b_rel_active": b_rel_active,
            },
            "lk": {
                "clear": lk_clear,
                "conflicts": lk_conflicts,
                "enemy_overlap": enemy_overlap,
            }
        })


# ═══════════════════════════════════════════════════════
# Main Engine
# ═══════════════════════════════════════════════════════

def run_compatibility(
    chart_a: JaiminiChart,
    chart_b: JaiminiChart,
    mode: CompatMode = CompatMode.RELATIONSHIP
) -> CompatibilityReport:
    """Run the complete 6-layer compatibility analysis."""

    layers = []
    warnings = []
    catalysts = []

    # Layer 1: AK
    l1 = layer_1_ak_connection(chart_a, chart_b)
    layers.append(l1)
    if not l1.passed:
        warnings.append("Soul alignment requires conscious effort from both sides.")

    # Layer 2: Role-based
    if mode == CompatMode.RELATIONSHIP:
        l2 = layer_2_relationship(chart_a, chart_b)
    else:
        l2 = layer_2_business(chart_a, chart_b)
    layers.append(l2)

    # Layer 3: Arudha
    l3 = layer_3_arudha(chart_a, chart_b, mode)
    layers.append(l3)
    if not l3.passed and l3.score <= 0.20:
        warnings.append("Public perception may not match this pairing's private strength.")

    # Layer 4: Nakshatra
    l4 = layer_4_nakshatra(chart_a, chart_b)
    layers.append(l4)
    if not l4.passed:
        warnings.append("Traditional Nakshatra compatibility below threshold — lean on Jaimini layers.")

    # Layer 5: DKP
    l5 = layer_5_dkp(chart_a, chart_b, mode)
    layers.append(l5)

    # Layer 6: Timing + LK
    l6 = layer_6_timing_lk(chart_a, chart_b, mode)
    layers.append(l6)
    if l6.extra.get("lk", {}).get("conflicts"):
        warnings.append("Lal Kitab enemy house overlap — shared karmic debt amplifies challenges.")
    if l6.extra.get("timing", {}).get("divergent"):
        pa = l6.extra["timing"]["phase_a"]
        pb = l6.extra["timing"]["phase_b"]
        warnings.append(f"Timing Divergence: {chart_a.name} in {pa}, {chart_b.name} in {pb}.")
    if mode == CompatMode.RELATIONSHIP and not l6.extra.get("timing", {}).get("a_rel_active") and not l6.extra.get("timing", {}).get("b_rel_active"):
        warnings.append("Neither chart in relationship-active dasha. Timing may not support new commitments.")

    # Convergence
    conv = sum(l.score * l.weight for l in layers)
    score = min(round(conv * 100, 1), 100)
    confidence = "high" if score >= 72 else "medium" if score >= 48 else "low"
    passed_count = sum(1 for l in layers if l.passed)

    # Strongest / Weakest
    strongest = max(layers, key=lambda l: l.score)
    weakest = min(layers, key=lambda l: l.score)

    # Conclusion-first headline (THE RULE)
    mode_label = "relationship" if mode == CompatMode.RELATIONSHIP else "partnership"
    if passed_count >= 5:
        headline = f"{score}% aligned. This {mode_label} has deep roots."
        summary = f"Your strongest connection is {strongest.layer_name.lower()}. " + \
                  (f"Watch: {weakest.layer_name.lower()}." if warnings else "No significant friction.")
    elif passed_count >= 3:
        headline = f"{score}% aligned. Solid foundation with room to grow."
        summary = f"Your strongest connection is {strongest.layer_name.lower()}. Your friction point is {weakest.layer_name.lower()}."
    elif passed_count >= 1:
        headline = f"{score}% aligned. This needs work."
        summary = f"Only {passed_count}/6 layers connect. Bright spot: {strongest.layer_name.lower()}. Challenge: {weakest.layer_name.lower()}."
    else:
        headline = f"{score}% aligned. The stars don't favor this — but stars aren't everything."
        summary = "No strong layer connections. If you both want this, you'll need to build what the charts don't provide."

    # Catalysts
    if l1.passed:
        catalysts.append(f"Soul alignment through {SIGN_NAMES[chart_a.ak_sign]} ↔ {SIGN_NAMES[chart_b.ak_sign]}")
    if l2.passed and l2.badges:
        catalysts.append(" + ".join(l2.badges))
    if l3.passed:
        catalysts.append(f"Public image: {l3.badge}")
    if l6.extra.get("timing", {}).get("both_rel_active"):
        catalysts.append("Both in relationship-active windows NOW")

    return CompatibilityReport(
        mode=mode,
        person_a=chart_a.name,
        person_b=chart_b.name,
        layers=layers,
        convergence_score=score,
        confidence=confidence,
        headline=headline,
        summary=summary,
        passed_count=passed_count,
        warnings=warnings,
        catalysts=catalysts,
        strongest_layer=strongest.layer_name,
        weakest_layer=weakest.layer_name,
    )


# ═══════════════════════════════════════════════════════
# Serialization / Integration
# ═══════════════════════════════════════════════════════

def report_to_json(report: CompatibilityReport) -> Dict:
    """Convert to JSON for API response + synastry_report JSONB storage."""
    return {
        "mode": report.mode.value,
        "person_a": report.person_a,
        "person_b": report.person_b,
        "convergence_score": report.convergence_score,
        "confidence": report.confidence,
        "headline": report.headline,
        "summary": report.summary,
        "passed_count": report.passed_count,
        "strongest_layer": report.strongest_layer,
        "weakest_layer": report.weakest_layer,
        "layers": [
            {
                "id": l.layer_id,
                "num": l.layer_number,
                "name": l.layer_name,
                "weight": l.weight,
                "passed": l.passed,
                "score": round(l.score, 3),
                "headline": l.headline,
                "detail": l.detail,
                "badge": l.badge,
                "badges": l.badges,
                "extra": l.extra,
            }
            for l in report.layers
        ],
        "warnings": report.warnings,
        "catalysts": report.catalysts,
    }


def report_to_prompt_block(report: CompatibilityReport) -> str:
    """Format for Ask Antar LLM system prompt."""
    lines = [
        f"COMPATIBILITY ({report.mode.value.upper()}): {report.person_a} × {report.person_b}",
        f"Score: {report.convergence_score}% ({report.confidence})",
        f"Verdict: {report.headline}",
        f"Summary: {report.summary}",
        f"Strongest: {report.strongest_layer} | Weakest: {report.weakest_layer}",
        "",
    ]
    for l in report.layers:
        tag = "PASS" if l.passed else "FAIL"
        lines.append(f"  L{l.layer_number} [{tag}] {l.layer_name}: {l.headline}")
        lines.append(f"    {l.detail}")

    if report.warnings:
        lines.append("\n  WARNINGS:")
        for w in report.warnings:
            lines.append(f"    - {w}")

    return "\n".join(lines)


def build_chart_from_db(name: str, age: int, country: str, country_label: str,
                        nakshatra: str, moon_sign: int, lagna_idx: int,
                        jaimini_data: Dict, lk_data: Optional[Dict] = None,
                        vimsottari_md: str = "", vimsottari_ad: str = "") -> JaiminiChart:
    """
    Build JaiminiChart from stored DB data.
    jaimini_data comes from charts.jaimini_data JSONB.
    lk_data comes from charts.lal_kitab_data JSONB.
    """
    karakas = {}
    for k in jaimini_data.get("karakas", []):
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

    try:
        end_date = date.fromisoformat(md.get("end", "2032-01-01")[:10])
        remaining = max((end_date - date.today()).days / 365.25, 0)
    except Exception:
        remaining = md_years / 2

    # LK data
    lk_enemy = []
    lk_sleeping = []
    if lk_data:
        lk_enemy = lk_data.get("enemy_houses", [])
        lk_sleeping = lk_data.get("sleeping_planets", [])

    return JaiminiChart(
        name=name,
        age=age,
        country=country,
        country_label=country_label,
        nakshatra=nakshatra,
        moon_sign=moon_sign,
        karakas=karakas,
        arudha_lagna=al,
        upapada_lagna=ul,
        karakamsa=kl,
        lagna=lagna_idx,
        current_md_sign=md_sign,
        current_ad_sign=ad_sign,
        md_years_remaining=remaining,
        md_total_years=md_years,
        vimsottari_md=vimsottari_md,
        vimsottari_ad=vimsottari_ad,
        lk_enemy_houses=lk_enemy,
        lk_sleeping_planets=lk_sleeping,
    )
