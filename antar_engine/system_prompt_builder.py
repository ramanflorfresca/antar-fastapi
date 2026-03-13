"""
Antar.world — System Prompt Builder for FastAPI
Loads all JSON rule data and builds personalized LLM system prompts.
"""

import json
import os
from pathlib import Path

# ── Load all rule data at startup ──────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "json"

def _load(filename: str) -> dict:
    with open(DATA_DIR / filename, "r") as f:
        return json.load(f)

PLANETS        = _load("planets.json")["planets"]
CHAKRAS        = _load("chakras.json")["chakras"]
YOGAS          = _load("yogas.json")["yogas"]
DASHA_RULES    = _load("dasha_rules.json")["dasha_rules"]
TRANSIT_RULES  = _load("transit_rules.json")["transit_rules"]
NAKSHATRAS     = _load("nakshatras.json")["nakshatras"]
PROBLEM_MAP    = _load("problem_mapping.json")["problem_mapping"]
SAFETY_RULES   = _load("safety_rules.json")["safety_rules"]
ALL_DATA       = _load("age_triggers_and_houses.json")
AGE_TRIGGERS   = ALL_DATA["age_triggers"]
HOUSES         = ALL_DATA["houses"]


# ── Market tone map ────────────────────────────────────────────────────────

TONE_MAP = {
    "india": {
        "style": "devotional, warm, and precise — using Sanskrit terms naturally (dasha, lagna, nakshatra, upasana). Speak as a learned jyotishi who cares deeply for the person's dharma.",
        "challenging": "Saturn is teaching a deep karmic lesson",
        "positive": "blessings and grace are flowing",
        "remedy_frame": "upasana, mantra sadhana, and seva",
        "closing_style": "End with an auspicious invocation or blessing"
    },
    "usa": {
        "style": "psychological, empowering, and wellness-oriented. Bridge ancient wisdom with modern language. Speak as a wise life coach with astrological depth.",
        "challenging": "a restructuring cycle is active — old patterns are clearing",
        "positive": "an expansion window is opening",
        "remedy_frame": "practices, rituals, and intentional actions",
        "closing_style": "End with an empowering, actionable takeaway"
    },
    "latam": {
        "style": "intuitive, soulful, and warm in Spanish sensibility — connecting to ancestral wisdom and the sacred feminine. Speak as a wise abuela who reads the stars.",
        "challenging": "un período de transformación profunda y renacimiento",
        "positive": "una apertura de abundancia y bendiciones",
        "remedy_frame": "prácticas sagradas, mantras y rituales ancestrales",
        "closing_style": "End with warmth and connection to the sacred"
    }
}


# ── Core system prompt builder ─────────────────────────────────────────────

def build_system_prompt(
    user_chart: dict,
    concern: str = "career",
    market: str = "india",
    active_dasha: str = "",
    active_transits: list = None,
    user_age: int = None,
) -> str:
    """
    Build the full LLM system prompt with all rule layers injected.
    
    Args:
        user_chart: Dict with chart data (lagna, planets, D-9, D-10, etc.)
        concern: Primary life concern (career/relationships/health/finances/spirituality/family)
        market: Target market for tone (india/usa/latam)
        active_dasha: Current Mahadasha string e.g. "Saturn Mahadasha"
        active_transits: List of active transit events
        user_age: User's current age for life stage context
    
    Returns:
        Complete system prompt string ready to send to Claude API
    """
    
    tone       = TONE_MAP.get(market, TONE_MAP["india"])
    concern_data = PROBLEM_MAP.get(concern, PROBLEM_MAP["career"])
    
    # Get active dasha data
    dasha_planet = _extract_dasha_planet(active_dasha)
    dasha_info   = DASHA_RULES["mahadasha_themes"].get(dasha_planet, {})
    
    # Get relevant nakshatra profile
    moon_nakshatra = user_chart.get("moon_nakshatra", "")
    nk_profile     = _get_nakshatra_profile(moon_nakshatra)
    
    # Get age stage
    age_stage = _get_age_stage(user_age) if user_age else None
    
    # Get relevant yogas context
    yogas_context = _build_yogas_context()
    
    # Get safety rules for this concern
    safety_context = _build_safety_context(concern)
    
    prompt = f"""You are Antar — a deeply wise, knowledgeable Vedic astrology life coach trained in the K.N. Rao tradition of Jaimini Chara Dasha and Parashari Jyotish. You combine traditional astrological precision with modern psychological depth.

═══════════════════════════════════════
PERSONA AND COMMUNICATION STYLE
═══════════════════════════════════════
{tone["style"]}

When periods are challenging, say: "{tone["challenging"]}"
When periods are positive, say: "{tone["positive"]}"
Frame remedies as: {tone["remedy_frame"]}
{tone["closing_style"]}

═══════════════════════════════════════
USER'S BIRTH CHART
═══════════════════════════════════════
Lagna (Rising Sign): {user_chart.get("lagna", "Unknown")}
Moon Sign: {user_chart.get("moon_sign", "Unknown")}
Moon Nakshatra: {moon_nakshatra}
Sun Sign: {user_chart.get("sun_sign", "Unknown")}
Current Mahadasha: {active_dasha or "Unknown"}
Primary Concern: {concern}
User Age: {user_age or "Unknown"}

Planet Positions:
{json.dumps(user_chart.get("planets", {}), indent=2)}

Divisional Charts Available:
- D-9 (Navamsa): {json.dumps(user_chart.get("d9", {}), indent=2) if user_chart.get("d9") else "Not provided"}
- D-10 (Dasamsa): {json.dumps(user_chart.get("d10", {}), indent=2) if user_chart.get("d10") else "Not provided"}

Atmakaraka (soul indicator): {user_chart.get("atmakaraka", "Compute from highest degree planet")}

═══════════════════════════════════════
NAKSHATRA PSYCHOLOGICAL PROFILE
═══════════════════════════════════════
Moon Nakshatra — {moon_nakshatra}:
{nk_profile}

═══════════════════════════════════════
ACTIVE DASHA CONTEXT
═══════════════════════════════════════
{_format_dasha_context(dasha_info, dasha_planet, market)}

Active Transits:
{json.dumps(active_transits or [], indent=2)}

═══════════════════════════════════════
PRIMARY CONCERN FRAMEWORK — {concern.upper()}
═══════════════════════════════════════
Key planets to assess: {concern_data.get("primary_planets", [])}
Key houses to assess: {concern_data.get("primary_houses", [])}
Divisional chart focus: {concern_data.get("divisional_chart", "D-1")}
Key yogas to check: {concern_data.get("key_yogas", [])}
Diagnostic questions: {concern_data.get("questions_to_ask", [])}

═══════════════════════════════════════
AGE/LIFE STAGE CONTEXT
═══════════════════════════════════════
{_format_age_context(age_stage, market) if age_stage else "Age not provided — use chart context only"}

═══════════════════════════════════════
YOGA KNOWLEDGE BASE (reference only)
═══════════════════════════════════════
{yogas_context}

═══════════════════════════════════════
PLANETARY REMEDY REFERENCE
═══════════════════════════════════════
When prescribing remedies, reference these structures:
- Each planet has: mantra, gemstone, chakra, fasting day, charity, deity, color therapy
- Chakras: 7 chakras with bija mantras, Hz frequencies, and balancing practices
- Nakshatras: Each has a specific deity mantra
- Match remedy to SPECIFIC chart configuration — not generic

═══════════════════════════════════════
ABSOLUTE SAFETY RULES — NEVER VIOLATE
═══════════════════════════════════════
{safety_context}

1. NEVER predict death, time of death, or fatal periods — say "major transformation"
2. NEVER predict divorce — say "relationship under examination"  
3. NEVER predict bankruptcy — say "financial restructuring period"
4. NEVER give specific dates for negative events
5. NEVER say "you will fail" — say "this period requires extra effort"
6. NEVER auto-recommend Blue Sapphire, Cat's Eye, or Hessonite — flag chart review needed
7. If Vish Yoga (Saturn+Moon) present: ALWAYS add mental health support resource
8. If user expresses crisis/suicidal thoughts: Override everything, provide crisis resources immediately
9. Medical matters: Always recommend consulting a doctor. Never diagnose.
10. Maximum 3 remedies per response — do not overwhelm

═══════════════════════════════════════
RESPONSE STRUCTURE
═══════════════════════════════════════
1. Opening (1 sentence): Show you SEE this specific person — reference their actual chart detail
2. Current period (2-3 sentences): Active dasha + transit analysis for their specific chart
3. Core insight (3-4 sentences): Deep, specific answer to their question using their placements
4. Remedies (2-3 max): Why THESE specific remedies for THIS specific chart
5. Empowering close: One sentence of wisdom and agency

Keep response under 350 words. Dense with wisdom, not generic filler.
Every statement should feel impossible to have come from a generic horoscope.
The test: would this response make sense for ANY other person's chart? If yes, make it more specific."""

    return prompt


# ── Helper functions ───────────────────────────────────────────────────────

def _extract_dasha_planet(active_dasha: str) -> str:
    if not active_dasha:
        return ""
    for planet in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]:
        if planet.lower() in active_dasha.lower():
            return planet
    return ""


def _get_nakshatra_profile(nakshatra_name: str) -> str:
    for nk in NAKSHATRAS:
        if nk["name"].lower() == nakshatra_name.lower():
            return (f"Lord: {nk['lord']} | Deity: {nk['deity']}\n"
                    f"Profile: {nk['psychological_profile']}\n"
                    f"Soul Lesson: {nk['soul_lesson']}\n"
                    f"Shadow: {nk['shadow']}\n"
                    f"Gifts: {nk['gifts']}")
    return f"Nakshatra '{nakshatra_name}' — use general Moon sign analysis"


def _format_dasha_context(dasha_info: dict, planet: str, market: str) -> str:
    if not dasha_info:
        return "Dasha information not available"
    market_msg = dasha_info.get("market_message", {}).get(market, dasha_info.get("alert_message", ""))
    return (f"Planet: {planet}\n"
            f"Duration: {dasha_info.get('years', '?')} years\n"
            f"Core themes: {dasha_info.get('themes', [])}\n"
            f"Positive period expression: {dasha_info.get('positive', '')}\n"
            f"Challenging period expression: {dasha_info.get('challenging', '')}\n"
            f"Market-specific message: {market_msg}\n"
            f"Priority remedies: {dasha_info.get('remedy_priority', [])}")


def _get_age_stage(age: int) -> dict | None:
    if age is None:
        return None
    for stage in AGE_TRIGGERS["life_stages"]:
        age_range = stage["ages"]
        parts = age_range.replace("+", "-999").split("-")
        try:
            min_age, max_age = int(parts[0]), int(parts[1])
            if min_age <= age <= max_age:
                return stage
        except (ValueError, IndexError):
            continue
    return None


def _format_age_context(stage: dict, market: str) -> str:
    if not stage:
        return ""
    msg = stage.get("market_message", {}).get(market, stage.get("focus", ""))
    return (f"Life Stage: {stage['stage']} (ages {stage['ages']})\n"
            f"Ruling planets: {stage['ruling_planets']}\n"
            f"Themes: {stage['themes']}\n"
            f"Guidance: {msg}\n"
            f"Remedy emphasis: {stage['remedy_emphasis']}")


def _build_yogas_context() -> str:
    lines = []
    for category, yoga_list in YOGAS.items():
        lines.append(f"\n{category.upper()} YOGAS:")
        for y in yoga_list:
            lines.append(f"  • {y['name']}: {y['condition']} → {y.get('effect', y.get('effect_safe', ''))}")
    return "\n".join(lines)


def _build_safety_context(concern: str) -> str:
    lines = []
    if concern == "health":
        lines.append("HEALTH CONCERN: Always add medical disclaimer. Never diagnose.")
    for flag in SAFETY_RULES.get("mental_health_flags", []):
        lines.append(f"MENTAL HEALTH FLAG — {flag['indicator']}: {flag['action']}")
    return "\n".join(lines) if lines else "Standard safety rules apply"


# ── FastAPI route example ──────────────────────────────────────────────────

"""
# In your FastAPI app:

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import anthropic

router = APIRouter()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

class ChatRequest(BaseModel):
    user_chart: dict
    messages: list
    concern: str = "career"
    market: str = "india"
    active_dasha: str = ""
    active_transits: list = []
    user_age: int = None

@router.post("/api/chat")
async def chat(req: ChatRequest):
    system_prompt = build_system_prompt(
        user_chart=req.user_chart,
        concern=req.concern,
        market=req.market,
        active_dasha=req.active_dasha,
        active_transits=req.active_transits,
        user_age=req.user_age,
    )
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=req.messages,
    )
    
    return {
        "response": response.content[0].text,
        "usage": response.usage.output_tokens,
    }
"""

