"""
ANTAR — Symptom Reference Library
Sprint 1.1: The "Medical Dictionary" for the Diagnostic Engine

Maps astrological chart conditions to business/life symptoms,
domain-specific jargon, and strategic verdicts.

This is the centralized translation layer. Instead of hardcoding
"Saturn in 10th = career delay" across files, everything routes
through this library.

Usage:
    from antar_engine.symptom_library import scan_chart_symptoms, get_domain_vocabulary
"""

from typing import List, Dict, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
# HOUSE LORDS BY SIGN (0=Aries...11=Pisces)
# ═══════════════════════════════════════════════════════════════════

SIGN_LORDS = {
    0: 'Mars',     # Aries
    1: 'Venus',    # Taurus
    2: 'Mercury',  # Gemini
    3: 'Moon',     # Cancer
    4: 'Sun',      # Leo
    5: 'Mercury',  # Virgo
    6: 'Venus',    # Libra
    7: 'Mars',     # Scorpio
    8: 'Jupiter',  # Sagittarius
    9: 'Saturn',   # Capricorn
    10: 'Saturn',  # Aquarius
    11: 'Jupiter', # Pisces
}

PLANET_IDS = {
    'Sun': 0, 'Moon': 1, 'Mars': 2, 'Mercury': 3,
    'Jupiter': 4, 'Venus': 5, 'Saturn': 6
}


# ═══════════════════════════════════════════════════════════════════
# SYMPTOM REFERENCE TABLE
# Each entry: trigger condition → symptom → domain jargon → verdict
# ═══════════════════════════════════════════════════════════════════

SYMPTOM_LIBRARY = [
    # ─── CAREER / AUTHORITY (10H) ───
    {
        "id": "AUTHORITY_FRICTION",
        "domain": "career",
        "house": 10,
        "trigger": "10H_lord_retrograde",
        "condition_fn": "lord_retrograde",
        "symptom": "Authority engine running in reverse — visibility delayed",
        "status_label": "HIGH FRICTION",
        "verdict": "HOLD POSITION",
        "jargon": {
            "ceo": "Board visibility is offline. Do not pitch. Consolidate internally.",
            "employee": "Promotion cycle is paused. Build leverage quietly.",
            "general": "Career authority is building in private. Don't force visibility."
        },
        "action": "Audit your current positioning. Do not launch anything public before {timing}."
    },
    {
        "id": "AUTHORITY_COMBUST",
        "domain": "career",
        "house": 10,
        "trigger": "10H_lord_combust",
        "condition_fn": "lord_combust",
        "symptom": "Authority signal burned out — overexposure risk",
        "status_label": "OVEREXPOSED",
        "verdict": "RETREAT AND RESET",
        "jargon": {
            "ceo": "You're over-leveraging your personal brand. Pull back from public commitments.",
            "employee": "You're overextended. Decline the next two asks.",
            "general": "Your career energy is exhausted from overexposure. Step back to recharge."
        },
        "action": "Decline one commitment this week. Protect your energy for {timing}."
    },
    {
        "id": "AUTHORITY_EXALTED",
        "domain": "career",
        "house": 10,
        "trigger": "10H_lord_exalted",
        "condition_fn": "lord_exalted",
        "symptom": "Authority signal at peak — window open",
        "status_label": "PEAK AUTHORITY",
        "verdict": "EXECUTE NOW",
        "jargon": {
            "ceo": "Your boardroom leverage is at maximum. Push the strategic initiative.",
            "employee": "Your manager sees your value right now. Ask for what you want.",
            "general": "Career momentum is at peak. Make your move."
        },
        "action": "Schedule the critical meeting this week. Timing favors bold action."
    },
    {
        "id": "AUTHORITY_SATURN_PRESSURE",
        "domain": "career",
        "house": 10,
        "trigger": "saturn_in_10H",
        "condition_fn": "planet_in_house",
        "condition_args": {"planet": "Saturn", "house": 10},
        "symptom": "Structural load on career — slow grind, no shortcuts",
        "status_label": "STRUCTURAL PRESSURE",
        "verdict": "GRIND MODE",
        "jargon": {
            "ceo": "This is the build-in-silence phase. Results compound but don't show yet.",
            "employee": "Seniority is accumulating. Patience is the strategy.",
            "general": "Career progress is real but invisible. Keep building."
        },
        "action": "Document your wins privately. They compound after {timing}."
    },
    {
        "id": "6H_PRESSURE",
        "domain": "career",
        "house": 6,
        "trigger": "6H_lord_afflicted",
        "condition_fn": "lord_afflicted",
        "symptom": "Workplace friction — competitors or conflicts active",
        "status_label": "COMPETITIVE HEAT",
        "verdict": "DEFEND POSITION",
        "jargon": {
            "ceo": "A rival or internal faction is mobilizing. Tighten your inner circle.",
            "employee": "Workplace politics heating up. Stay neutral, document everything.",
            "general": "Professional friction is rising. Don't engage — outperform."
        },
        "action": "Identify the source of friction and neutralize with documentation, not confrontation."
    },

    # ─── WEALTH / CAPITAL (2H, 8H, 11H) ───
    {
        "id": "CAPITAL_GRIDLOCK",
        "domain": "wealth",
        "house": 8,
        "trigger": "8H_lord_retrograde",
        "condition_fn": "lord_retrograde",
        "symptom": "External capital frozen — funding channels blocked",
        "status_label": "CAPITAL GRIDLOCK",
        "verdict": "HIBERNATE",
        "jargon": {
            "ceo": "External funding is offline. Do not take new debt. Pivot to advisory revenue.",
            "investor": "Portfolio is in holding pattern. Wait for the restructure to complete.",
            "general": "Incoming money from external sources is delayed. Live lean."
        },
        "action": "Cut one overhead expense this week. Preserve runway until {timing}."
    },
    {
        "id": "GAINS_BLOCKED",
        "domain": "wealth",
        "house": 11,
        "trigger": "11H_lord_retrograde",
        "condition_fn": "lord_retrograde",
        "symptom": "Revenue pipeline stalled — expected gains delayed",
        "status_label": "PIPELINE STALL",
        "verdict": "RESTRUCTURE INFLOW",
        "jargon": {
            "ceo": "Receivables are going to slip. Renegotiate payment terms now.",
            "investor": "Expected returns will be delayed. Rebalance expectations.",
            "general": "Expected income is delayed. Adjust your cash flow expectations."
        },
        "action": "Follow up on every outstanding receivable this week. Don't wait for them to come."
    },
    {
        "id": "WEALTH_EXPANSION",
        "domain": "wealth",
        "house": 2,
        "trigger": "2H_lord_exalted_or_jupiter",
        "condition_fn": "lord_exalted_or_jupiter_in_house",
        "condition_args": {"house": 2},
        "symptom": "Earning capacity amplified — accumulation window open",
        "status_label": "CAPITAL EXPANSION",
        "verdict": "ACCUMULATE",
        "jargon": {
            "ceo": "Revenue efficiency is peaking. Double down on highest-margin activity.",
            "investor": "Accumulation phase. Increase allocation to core positions.",
            "general": "Your earning power is strong right now. Save aggressively."
        },
        "action": "Identify your highest-revenue activity and allocate 70% of effort there."
    },
    {
        "id": "WEALTH_LEAK",
        "domain": "wealth",
        "house": 12,
        "trigger": "12H_activated_with_malefic",
        "condition_fn": "malefic_in_house",
        "condition_args": {"house": 12},
        "symptom": "Capital leakage — expenses outpacing inflow",
        "status_label": "BURN RATE CRITICAL",
        "verdict": "PLUG THE LEAK",
        "jargon": {
            "ceo": "Burn rate exceeds runway projections. Cut non-essential spend.",
            "investor": "Capital is leaving faster than entering. Audit every outflow.",
            "general": "You're spending more than you realize. Track every expense this week."
        },
        "action": "Cancel or pause the largest non-essential subscription or commitment today."
    },

    # ─── RELATIONSHIPS / ALLIANCE (7H) ───
    {
        "id": "ALLIANCE_FRICTION",
        "domain": "relationship",
        "house": 7,
        "trigger": "7H_lord_retrograde",
        "condition_fn": "lord_retrograde",
        "symptom": "Partnership signal reversed — misalignment active",
        "status_label": "PARTNER MISALIGNMENT",
        "verdict": "RECALIBRATE EXPECTATIONS",
        "jargon": {
            "married": "Your partner is processing internally. Don't push for resolution — wait.",
            "business": "Your co-founder/partner is rethinking terms. Clarify roles before it escalates.",
            "general": "Key relationship is in a re-evaluation phase. Listen more than speak."
        },
        "action": "Have one honest conversation this week. Ask what they need, not what you want."
    },
    {
        "id": "ALLIANCE_CONVERGENCE",
        "domain": "relationship",
        "house": 7,
        "trigger": "7H_lord_exalted_or_venus",
        "condition_fn": "lord_exalted_or_venus_in_house",
        "condition_args": {"house": 7},
        "symptom": "Partnership energy peak — alignment window open",
        "status_label": "DEEP SYNC",
        "verdict": "ADVANCE THE RELATIONSHIP",
        "jargon": {
            "married": "Emotional resonance is high. Initiate the conversation you've been delaying.",
            "business": "Partner alignment is peaking. Lock in the agreement now.",
            "general": "Your key relationship is in its strongest phase. Make commitments."
        },
        "action": "Propose the next step in the relationship this week — whatever that means for you."
    },
    {
        "id": "ALLIANCE_12H_LEAK",
        "domain": "relationship",
        "house": 12,
        "trigger": "7H_lord_in_12H",
        "condition_fn": "lord_in_specific_house",
        "condition_args": {"source_house": 7, "target_house": 12},
        "symptom": "Relationship energy draining — hidden dissatisfaction",
        "status_label": "SILENT DISCONNECT",
        "verdict": "SURFACE THE ISSUE",
        "jargon": {
            "married": "Unspoken resentment is building. Address it before it calcifies.",
            "business": "Your partner has one foot out. Have the direct conversation.",
            "general": "Something unspoken is eroding the relationship. Name it."
        },
        "action": "Ask directly: 'Is there something we're not addressing?' — this week."
    },

    # ─── HEALTH / SYSTEM VITALS (1H, 6H, 8H) ───
    {
        "id": "VITALS_DEPLETED",
        "domain": "health",
        "house": 1,
        "trigger": "lagna_lord_weak",
        "condition_fn": "lord_weak",
        "symptom": "Core energy depleted — burnout risk elevated",
        "status_label": "ENERGY CRITICAL",
        "verdict": "RECOVERY MODE",
        "jargon": {
            "ceo": "You're running on reserves. Cancel 3 meetings this week.",
            "general": "Your body is telling you to slow down. Listen before it forces you."
        },
        "action": "Sleep 8 hours tonight. Block 2 hours of empty space on your calendar tomorrow."
    },
    {
        "id": "VITALS_STRONG",
        "domain": "health",
        "house": 1,
        "trigger": "lagna_lord_strong",
        "condition_fn": "lord_strong",
        "symptom": "Core energy high — physical resilience peak",
        "status_label": "PEAK VITALS",
        "verdict": "PUSH HARDER",
        "jargon": {
            "ceo": "Physical reserves are high. This is the sprint window — use it.",
            "general": "Your energy is at a high point. Take on the thing you've been avoiding."
        },
        "action": "Start the challenging physical or mental task you've been postponing."
    },
]


# ═══════════════════════════════════════════════════════════════════
# DOMAIN VOCABULARY — used in prompt injection
# ═══════════════════════════════════════════════════════════════════

DOMAIN_VOCABULARY = {
    "career": {
        "nouns": ["authority", "positioning", "visibility", "leverage", "mandate"],
        "verbs": ["consolidate", "execute", "pivot", "defend", "escalate"],
        "status_terms": ["PEAK AUTHORITY", "HIGH FRICTION", "STRUCTURAL PRESSURE", "EXECUTING", "ON HOLD"],
        "tone": "chairman_board_advisor",
        "instruction": "Speak like a trusted Chairman advising a CEO. Use words like leverage, positioning, mandate, visibility window. Never use astrology terms."
    },
    "wealth": {
        "nouns": ["runway", "overhead", "equity", "burn rate", "capital", "pipeline", "receivables"],
        "verbs": ["restructure", "accumulate", "hibernate", "pivot", "deploy"],
        "status_terms": ["CAPITAL GRIDLOCK", "PIPELINE STALL", "CAPITAL EXPANSION", "BURN RATE CRITICAL", "RESTRUCTURE REQUIRED"],
        "tone": "cfo_strategic_advisor",
        "instruction": "Speak like a CFO in a boardroom. Use words like runway, overhead, burn rate, capital deployment, pipeline. Never use astrology terms."
    },
    "relationship": {
        "nouns": ["alignment", "sync", "convergence", "stability", "resonance", "disconnect"],
        "verbs": ["recalibrate", "advance", "surface", "anchor", "release"],
        "status_terms": ["DEEP SYNC", "PARTNER MISALIGNMENT", "SILENT DISCONNECT", "CONVERGENCE WINDOW", "STABLE"],
        "tone": "conflict_mediator",
        "instruction": "Speak like a high-end conflict mediator. Use words like alignment, sync, convergence, resonance, disconnect. Never use astrology terms."
    },
    "health": {
        "nouns": ["vitals", "reserves", "resilience", "recovery", "capacity", "threshold"],
        "verbs": ["restore", "protect", "push", "monitor", "intervene"],
        "status_terms": ["PEAK VITALS", "ENERGY CRITICAL", "RECOVERY MODE", "MONITORING", "STABLE"],
        "tone": "executive_physician",
        "instruction": "Speak like an executive physician. Use words like vitals, reserves, capacity, recovery protocol. Never use astrology terms."
    },
    "finance": {
        "nouns": ["runway", "overhead", "equity", "burn rate", "capital", "pipeline"],
        "verbs": ["restructure", "accumulate", "hibernate", "pivot", "deploy"],
        "status_terms": ["CAPITAL GRIDLOCK", "PIPELINE STALL", "CAPITAL EXPANSION", "BURN RATE CRITICAL"],
        "tone": "cfo_strategic_advisor",
        "instruction": "Speak like a CFO in a boardroom. Use words like runway, overhead, burn rate, capital deployment. Never use astrology terms."
    },
    "legal": {
        "nouns": ["exposure", "leverage", "liability", "positioning", "terms"],
        "verbs": ["protect", "document", "escalate", "settle", "withdraw"],
        "status_terms": ["HIGH EXPOSURE", "LEVERAGE ADVANTAGE", "NEUTRAL POSITIONING", "SETTLEMENT WINDOW"],
        "tone": "general_counsel",
        "instruction": "Speak like a General Counsel advising on risk. Use words like exposure, leverage, liability, positioning. Never use astrology terms."
    },
    "general": {
        "nouns": ["momentum", "clarity", "direction", "energy", "timing"],
        "verbs": ["focus", "execute", "pause", "recalibrate", "advance"],
        "status_terms": ["ON TRACK", "RECALIBRATION NEEDED", "PEAK WINDOW", "HOLDING PATTERN"],
        "tone": "trusted_advisor",
        "instruction": "Speak like a trusted strategic advisor. Use clear, direct language. Never use astrology terms."
    },
}


# ═══════════════════════════════════════════════════════════════════
# CHART SCANNER — detects active symptoms from natal chart
# ═══════════════════════════════════════════════════════════════════

def _get_house_sign(chart_data: dict, house_num: int) -> int:
    """Get the sign index (0-11) for a given house number (1-12)."""
    lagna_sign = chart_data.get("lagna_sign", 0)
    if isinstance(lagna_sign, str):
        sign_names = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                      "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
        lagna_sign = sign_names.index(lagna_sign) if lagna_sign in sign_names else 0
    return (lagna_sign + house_num - 1) % 12


def _get_house_lord(chart_data: dict, house_num: int) -> str:
    """Get the lord planet name for a given house."""
    house_sign = _get_house_sign(chart_data, house_num)
    return SIGN_LORDS.get(house_sign, "Saturn")


def _find_planet_data(chart_data: dict, planet_name: str) -> Optional[dict]:
    """Find planet data by name in chart_data.planets (handles both id-keyed and name-keyed)."""
    planets = chart_data.get("planets", {})
    for pid, pdata in planets.items():
        if isinstance(pdata, dict):
            if pdata.get("name", "").lower() == planet_name.lower():
                return pdata
    return None


def _is_planet_retrograde(planet_data: dict) -> bool:
    """Check if planet is retrograde (negative daily speed)."""
    if not planet_data:
        return False
    speed = planet_data.get("daily_speed", planet_data.get("speed", 0))
    return speed < 0


def _is_planet_combust(planet_data: dict, chart_data: dict) -> bool:
    """Check if planet is combust (within combustion orb of Sun)."""
    if not planet_data:
        return False
    sun_data = _find_planet_data(chart_data, "Sun")
    if not sun_data:
        return False
    
    planet_lon = planet_data.get("longitude", 0)
    sun_lon = sun_data.get("longitude", 0)
    diff = abs(planet_lon - sun_lon)
    if diff > 180:
        diff = 360 - diff
    
    # Combustion orbs by planet
    planet_name = planet_data.get("name", "")
    orbs = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}
    orb = orbs.get(planet_name, 15)
    return diff < orb


def _is_planet_exalted(planet_data: dict) -> bool:
    """Check if planet is in its exaltation sign."""
    if not planet_data:
        return False
    sign = planet_data.get("sign", -1)
    exaltation = {0: 0, 1: 1, 2: 9, 3: 5, 4: 3, 5: 11, 6: 6}  # Sun:Aries, Moon:Taurus, etc.
    planet_name = planet_data.get("name", "")
    pid = PLANET_IDS.get(planet_name, -1)
    return exaltation.get(pid) == sign


def _is_planet_weak(planet_data: dict, chart_data: dict) -> bool:
    """Planet is weak if retrograde, combust, or debilitated."""
    if not planet_data:
        return True
    debilitation = {0: 6, 1: 7, 2: 3, 3: 11, 4: 9, 5: 5, 6: 0}
    planet_name = planet_data.get("name", "")
    pid = PLANET_IDS.get(planet_name, -1)
    sign = planet_data.get("sign", -1)
    is_debilitated = debilitation.get(pid) == sign
    return _is_planet_retrograde(planet_data) or _is_planet_combust(planet_data, chart_data) or is_debilitated


def _is_planet_strong(planet_data: dict, chart_data: dict) -> bool:
    """Planet is strong if exalted, in own sign, or well-placed."""
    if not planet_data:
        return False
    own_signs = {0: [4], 1: [3], 2: [0, 7], 3: [2, 5], 4: [8, 11], 5: [1, 6], 6: [9, 10]}
    planet_name = planet_data.get("name", "")
    pid = PLANET_IDS.get(planet_name, -1)
    sign = planet_data.get("sign", -1)
    is_own = sign in own_signs.get(pid, [])
    return _is_planet_exalted(planet_data) or is_own


def _is_malefic(planet_name: str) -> bool:
    """Natural malefics: Sun, Mars, Saturn, Rahu, Ketu."""
    return planet_name.lower() in ["sun", "mars", "saturn", "rahu", "ketu"]


def _planet_in_house(chart_data: dict, planet_name: str, house_num: int) -> bool:
    """Check if a specific planet is in a specific house."""
    pdata = _find_planet_data(chart_data, planet_name)
    if not pdata:
        return False
    return pdata.get("house") == house_num


def _malefic_in_house(chart_data: dict, house_num: int) -> bool:
    """Check if any natural malefic is in the given house."""
    planets = chart_data.get("planets", {})
    for pid, pdata in planets.items():
        if isinstance(pdata, dict):
            if _is_malefic(pdata.get("name", "")) and pdata.get("house") == house_num:
                return True
    return False


def _lord_in_specific_house(chart_data: dict, source_house: int, target_house: int) -> bool:
    """Check if the lord of source_house is placed in target_house."""
    lord_name = _get_house_lord(chart_data, source_house)
    lord_data = _find_planet_data(chart_data, lord_name)
    if not lord_data:
        return False
    return lord_data.get("house") == target_house


def scan_chart_symptoms(chart_data: dict) -> List[Dict]:
    """
    Scan a natal chart for active symptoms.
    Returns a list of triggered symptoms with their verdicts and jargon.
    
    Args:
        chart_data: dict with keys: lagna_sign, planets{}, etc.
        
    Returns:
        List of symptom dicts, sorted by severity (worst first).
    """
    active_symptoms = []
    
    for symptom in SYMPTOM_LIBRARY:
        house = symptom["house"]
        condition = symptom["condition_fn"]
        triggered = False
        
        lord_name = _get_house_lord(chart_data, house)
        lord_data = _find_planet_data(chart_data, lord_name)
        
        if condition == "lord_retrograde":
            triggered = _is_planet_retrograde(lord_data)
        elif condition == "lord_combust":
            triggered = _is_planet_combust(lord_data, chart_data)
        elif condition == "lord_exalted":
            triggered = _is_planet_exalted(lord_data)
        elif condition == "lord_afflicted":
            triggered = _is_planet_weak(lord_data, chart_data)
        elif condition == "lord_weak":
            triggered = _is_planet_weak(lord_data, chart_data)
        elif condition == "lord_strong":
            triggered = _is_planet_strong(lord_data, chart_data)
        elif condition == "planet_in_house":
            args = symptom.get("condition_args", {})
            triggered = _planet_in_house(chart_data, args.get("planet", ""), args.get("house", 0))
        elif condition == "malefic_in_house":
            args = symptom.get("condition_args", {})
            triggered = _malefic_in_house(chart_data, args.get("house", 0))
        elif condition == "lord_exalted_or_jupiter_in_house":
            args = symptom.get("condition_args", {})
            h = args.get("house", 2)
            triggered = _is_planet_exalted(lord_data) or _planet_in_house(chart_data, "Jupiter", h)
        elif condition == "lord_exalted_or_venus_in_house":
            args = symptom.get("condition_args", {})
            h = args.get("house", 7)
            triggered = _is_planet_exalted(lord_data) or _planet_in_house(chart_data, "Venus", h)
        elif condition == "lord_in_specific_house":
            args = symptom.get("condition_args", {})
            triggered = _lord_in_specific_house(chart_data, args.get("source_house", 1), args.get("target_house", 12))
        
        if triggered:
            active_symptoms.append({
                "id": symptom["id"],
                "domain": symptom["domain"],
                "house": house,
                "symptom": symptom["symptom"],
                "status_label": symptom["status_label"],
                "verdict": symptom["verdict"],
                "jargon": symptom["jargon"],
                "action": symptom["action"],
            })
    
    # Sort: negative verdicts first (HIBERNATE, RETREAT > HOLD > EXECUTE)
    verdict_severity = {
        "HIBERNATE": 0, "RETREAT AND RESET": 1, "PLUG THE LEAK": 2,
        "RECOVERY MODE": 3, "DEFEND POSITION": 4, "HOLD POSITION": 5,
        "SURFACE THE ISSUE": 5, "RECALIBRATE EXPECTATIONS": 5,
        "RESTRUCTURE INFLOW": 5, "GRIND MODE": 6,
        "ACCUMULATE": 7, "ADVANCE THE RELATIONSHIP": 7,
        "EXECUTE NOW": 8, "PUSH HARDER": 8,
    }
    active_symptoms.sort(key=lambda s: verdict_severity.get(s["verdict"], 5))
    
    return active_symptoms


def get_primary_symptom(chart_data: dict, domain: str = None) -> Optional[Dict]:
    """
    Get the single most critical active symptom, optionally filtered by domain.
    This is what powers the dashboard greeting and the verdict header.
    """
    symptoms = scan_chart_symptoms(chart_data)
    if domain:
        domain_symptoms = [s for s in symptoms if s["domain"] == domain]
        return domain_symptoms[0] if domain_symptoms else None
    return symptoms[0] if symptoms else None


def get_domain_status(chart_data: dict) -> Dict[str, Dict]:
    """
    Get the status of all 4 primary domains for dashboard display.
    Returns: { "career": { status_label, verdict, symptom }, ... }
    """
    symptoms = scan_chart_symptoms(chart_data)
    
    domain_status = {}
    for domain in ["career", "wealth", "relationship", "health"]:
        domain_syms = [s for s in symptoms if s["domain"] == domain]
        if domain_syms:
            primary = domain_syms[0]
            domain_status[domain] = {
                "status_label": primary["status_label"],
                "verdict": primary["verdict"],
                "symptom": primary["symptom"],
                "action": primary["action"],
                "id": primary["id"],
            }
        else:
            domain_status[domain] = {
                "status_label": "STABLE",
                "verdict": "MONITOR",
                "symptom": "No active disruption detected",
                "action": "Continue current trajectory",
                "id": None,
            }
    
    return domain_status


def get_domain_vocabulary(domain: str) -> Dict:
    """Get the vocabulary and tone instruction for a specific domain."""
    return DOMAIN_VOCABULARY.get(domain, DOMAIN_VOCABULARY["general"])


def build_diagnostic_prompt_block(chart_data: dict, question: str, concern: str = None) -> str:
    """
    Build a diagnostic context block to inject into the Claude prompt.
    This is the "pre-scan" that runs BEFORE Claude speaks.
    
    Returns a text block that goes into the system prompt.
    """
    from antar_engine.prashna_engine import detect_domain
    
    # Detect domain from question
    domain_name, houses = detect_domain(question) if question else ("general", [10])
    if concern and concern in DOMAIN_VOCABULARY:
        domain_name = concern
    
    # Get active symptoms
    symptoms = scan_chart_symptoms(chart_data)
    domain_symptoms = [s for s in symptoms if s["domain"] == domain_name]
    all_critical = [s for s in symptoms if s["verdict"] in ("HIBERNATE", "RETREAT AND RESET", "PLUG THE LEAK", "RECOVERY MODE")]
    
    # Get vocabulary
    vocab = get_domain_vocabulary(domain_name)
    
    # Build the block
    lines = []
    lines.append("=" * 60)
    lines.append("DIAGNOSTIC PRE-SCAN (use this to frame your response)")
    lines.append("=" * 60)
    lines.append(f"DOMAIN: {domain_name.upper()}")
    lines.append(f"TONE: {vocab['tone']}")
    lines.append(f"INSTRUCTION: {vocab['instruction']}")
    lines.append("")
    
    if domain_symptoms:
        primary = domain_symptoms[0]
        lines.append(f"PRIMARY SYMPTOM DETECTED: {primary['symptom']}")
        lines.append(f"STATUS: {primary['status_label']}")
        lines.append(f"VERDICT: {primary['verdict']}")
        lines.append(f"SUGGESTED ACTION: {primary['action']}")
        
        # Add jargon hint
        jargon = primary["jargon"]
        if "general" in jargon:
            lines.append(f"PHRASING GUIDE: {jargon['general']}")
    else:
        lines.append("NO ACTIVE DISRUPTION IN THIS DOMAIN.")
        lines.append("STATUS: STABLE")
    
    if all_critical and domain_name not in [s["domain"] for s in all_critical]:
        lines.append("")
        lines.append("CROSS-DOMAIN ALERT:")
        for cs in all_critical[:2]:
            lines.append(f"  - {cs['domain'].upper()}: {cs['status_label']} ({cs['verdict']})")
    
    lines.append("")
    lines.append(f"VOCABULARY TO USE: {', '.join(vocab['nouns'][:5])}")
    lines.append(f"ACTION VERBS: {', '.join(vocab['verbs'][:5])}")
    lines.append("=" * 60)
    
    return "\n".join(lines)
