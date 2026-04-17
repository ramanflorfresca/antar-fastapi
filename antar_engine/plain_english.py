"""
plain_english.py
Sprint C1 — Plain English Engine

Post-processes raw /predict LLM output into a strict JSON structure.
Runs as a second Claude Sonnet call after the main prediction.
Never crashes the parent /predict request — always returns a safe fallback.
"""

import json
import logging
import re
from typing import Optional
import httpx
from antar_engine.symptom_library import build_diagnostic_prompt_block, get_domain_vocabulary, get_primary_symptom


logger = logging.getLogger(__name__)

# ═══ E1: EMOTIONAL INTELLIGENCE LAYER ═══
# Detects emotional state from question text and adapts Claude's tone.
# Does NOT change the verdict or score — only the delivery.

EMOTIONAL_KEYWORDS = {
    "desperate": [
        "ever find", "never find", "always alone", "no one", "give up", "hopeless",
        "scared", "afraid", "terrified", "panic", "anxiety", "depressed",
        "crying", "broken", "lost everything", "stuck forever", "worth it",
        "will i ever", "am i doomed", "no hope", "cant take", "falling apart",
        "will things ever", "is there any hope", "feel so alone",
    ],
    "hopeful": [
        "finally", "dream come true", "hoping", "praying", "please tell me",
        "is there a chance", "possible", "one day", "meant to be", "destiny",
        "will my luck", "turning point", "light at the end", "things looking up",
    ],
    "angry": [
        "unfair", "betrayed", "cheated", "lied to", "robbed", "screwed",
        "revenge", "justice", "punish", "how dare", "sick of", "fed up",
        "they ruined", "backstabbed", "stolen from me",
    ],
}

# Business phrases that contain emotional words but aren't emotional
EMOTION_EXCLUSIONS = [
    "dying to close", "killing it", "crushing it", "scared money",
    "afraid of missing", "lost opportunity", "broken deal",
]




def validate_and_fix_structured_response(raw_response: str, question: str, language: str = "en") -> dict:
    """
    Parse and validate the structured JSON response from the LLM.
    
    Handles:
    1. LLM wrapping JSON in markdown ```json blocks
    2. LLM adding preamble before the JSON
    3. Timing contradiction detection (plain_summary vs timing_window)
    4. Missing fields — fills with safe defaults
    5. Jargon detection — flags if any forbidden terms slipped through
    """
    import json, re
    
    FORBIDDEN = [
        "processing speed", "fortune vector", "authority signal", 
        "growth amplifier", "magnetism field", "structural load",
        "capital runway", "action drive", "house ", "nakshatra",
        "dasha", "yoga", "karaka", "lagna", "rashi", "bhava",
        "vimsottari", "jaimini", "lal kitab", "mahadasha", "antardasha",
    ]
    
    # Strip markdown code blocks if present
    text = raw_response.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    # Find JSON object in response
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if not json_match:
        # LLM didn't return JSON — build fallback
        return _build_fallback_response(question, language)
    
    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return _build_fallback_response(question, language)
    
    # Validate required fields
    required = ["signal_line", "plain_summary", "action_item", "timing_window"]
    for field in required:
        if field not in data or not data[field]:
            data[field] = _fallback_field(field, question, language)
    
    # Check for timing contradiction
    summary_lower = data.get("plain_summary", "").lower()
    timing_lower = data.get("timing_window", "").lower()
    
    contradiction = False
    # If plain_summary says "now is your window" but timing says "closing"
    if any(w in summary_lower for w in ["now is your", "ahora es tu", "ventana abierta"]):
        if any(w in timing_lower for w in ["closing", "cerrando", "past", "pasado"]):
            contradiction = True
            data["contradiction_detected"] = True
    
    # Check for forbidden jargon that slipped through
    jargon_found = []
    for field in ["plain_summary", "signal_line", "action_item"]:
        text_lower = data.get(field, "").lower()
        for term in FORBIDDEN:
            if term in text_lower:
                jargon_found.append(term)
    
    if jargon_found:
        data["jargon_detected"] = jargon_found
        # Strip the jargon terms
        for field in ["plain_summary", "signal_line", "action_item"]:
            for term in jargon_found:
                data[field] = re.sub(
                    re.escape(term), "", data[field], flags=re.IGNORECASE
                ).strip()
    
    # Ensure action_item starts with verb
    action = data.get("action_item", "")
    if action and not action[0].isupper():
        data["action_item"] = action[0].upper() + action[1:]
    
    # Ensure confidence is valid
    if data.get("confidence") not in ["high", "medium", "low"]:
        data["confidence"] = "medium"
    
    return data


def _build_fallback_response(question: str, language: str = "en") -> dict:
    """Safe fallback when LLM doesn't return valid JSON"""
    is_es = language == "es"
    return {
        "signal_line": "Antar está procesando tu pregunta." if is_es else "Antar is processing your question.",
        "plain_summary": "Tu pregunta ha sido recibida. Pregunta de nuevo para una respuesta más específica." if is_es else "Your question has been received. Ask again for a more specific answer.",
        "action_item": "Reformula tu pregunta con más contexto específico." if is_es else "Rephrase your question with more specific context.",
        "timing_window": "",
        "why_this": "",
        "confidence": "low",
        "domain": "general",
        "verdict": "WAIT",
    }


def _fallback_field(field: str, question: str, language: str) -> str:
    """Fallback values for missing fields"""
    is_es = language == "es"
    defaults = {
        "signal_line": "Señal procesándose." if is_es else "Signal processing.",
        "plain_summary": "Revisa tu pregunta para una respuesta más precisa." if is_es else "Review your question for a more precise answer.",
        "action_item": "Espera la señal completa." if is_es else "Wait for the full signal.",
        "timing_window": "",
    }
    return defaults.get(field, "")

def detect_emotional_tone(question: str) -> str:
    """
    Detect emotional state from question text.
    Returns: "desperate" | "hopeful" | "angry" | "neutral"

    Checks exclusions first to avoid false positives on business jargon.
    """
    q = question.lower()

    # Check exclusions — business phrases that look emotional but aren't
    for exclusion in EMOTION_EXCLUSIONS:
        if exclusion in q:
            return "neutral"

    # Check emotional keywords
    for tone, keywords in EMOTIONAL_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return tone

    return "neutral"


def get_time_modifier(hour_utc: int) -> str:
    """
    Detect late-night queries (0-5 AM UTC).
    Returns: "late_night" | "normal"

    Late-night questions get warmer tone — someone reaching out at 2am
    is probably anxious or can't sleep.
    """
    if 0 <= hour_utc < 6:
        return "late_night"
    return "normal"


def build_emotional_prompt_block(tone: str, time_mod: str) -> str:
    """
    Build the prompt injection block for Claude based on detected emotion.
    Returns empty string for neutral tone (no injection needed).
    """
    blocks = []

    if tone == "desperate":
        blocks.append(
            "EMOTIONAL CONTEXT: The user is in emotional distress. "
            "Lead with acknowledgment — one sentence that shows you hear them. "
            "Use softer language: 'the energy suggests' instead of 'the verdict is'. "
            "If the answer is difficult, frame it as 'not yet' rather than 'no'. "
            "End with grounding: a concrete small step they can take TODAY. "
            "Never dismiss their feelings. Never use platitudes. "
            "The verdict doesn't change — only the delivery."
        )
    elif tone == "hopeful":
        blocks.append(
            "EMOTIONAL CONTEXT: The user is carrying hope. Honor it. "
            "Don't inflate expectations but don't crush them either. "
            "If the verdict is negative, frame it as timing — 'the window isn't open yet' "
            "rather than a flat no. End with what they CAN do now to prepare. "
            "Match their energy without overpromising."
        )
    elif tone == "angry":
        blocks.append(
            "EMOTIONAL CONTEXT: The user is angry. Don't match the energy. "
            "Don't dismiss it either. Validate the feeling in ONE sentence, "
            "then pivot to what the data actually shows. "
            "Frame THE MOVE as reclaiming power and clarity, not seeking revenge. "
            "Be direct, not clinical."
        )

    if time_mod == "late_night":
        blocks.append(
            "TIME CONTEXT: The user is reaching out late at night. "
            "This suggests urgency or insomnia. Be warm but grounding. "
            "Keep it concise — they need clarity, not a lecture. "
            "Don't add more to worry about."
        )

    if blocks:
        return "\n\n" + "\n".join(blocks) + "\n"
    return ""


# ── Constants ────────────────────────────────────────────────────────────────

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1000

BANNED_TERMS = [
    "mahadasha", "antardasha", "atmakaraka", "amatyakaraka",
    "navamsa", "darakaraka", "putrakaraka", "bhava", "graha",
    "nakshatra", "rashi", "vimsottari", "ashtottari", "jaimini",
    "lagna", "yogakaraka", "vargottama", "muhurta", "panchanga",
    "tithi", "karana", "yoga", "vara", "hora", "ayanamsa",
    "ephemeris", "varshphal", "masik", "teva", "umra"
]

VALID_DOMAINS = [
    "career", "wealth", "love", "children", "health", "foreign",
    "legal", "business", "loans", "property", "education", "luck",
    "travel", "spirituality", "father", "mother", "siblings", "enemies", "general"
]

PLAIN_ENGLISH_SYSTEM_PROMPT = """
You are Antar's response formatter. You receive a raw astrological analysis
and a user's question. You return ONLY a valid JSON object — nothing else.
No preamble. No markdown. No explanation outside the JSON.

YOUR JOB:
1. Read the raw analysis
2. Read the user's question  
3. Return a JSON object that directly answers the question in plain language

STRICT RULES:
- plain_summary must directly answer what the user asked
- plain_summary must NOT contradict timing_window (never say "now is your window" 
  if timing_window says a window is closing)
- plain_summary must contain ZERO astrological terms (no house numbers, no planet 
  names, no dasha names, no nakshatra names, no yoga names)
- signal_line must be under 12 words, no jargon
- action_item must start with an action verb (Write, Call, Schedule, Move, Stop...)
- timing_window must use plain dates ("April–September 2026") not codes
- If the question asks WHEN → the answer must be in plain_summary and timing_window
- If the question asks WHY → explain in plain human terms what's causing it
- If the question asks SHOULD I → give a clear verdict with reasoning
- language field: respond in the SAME language as the question

FORBIDDEN WORDS in plain_summary, signal_line, action_item:
Processing Speed, Fortune Vector, Authority Signal, Growth Amplifier,
Magnetism Field, Structural Load, Capital Runway, Action Drive,
Ambition Engine, Emotional Radar, Intuition Compass, Revenue Pipeline,
Alliance Sync, Hungry Becoming, Creative Pulse, Velocity Engine,
Foundation Shield, Wisdom Lens, Health Matrix, Resource Grid,
Authority Engine, System Vitals, Capital Reserves, Conflict Shield,
house, nakshatra, dasha, yoga, karaka, lagna, rashi, bhava,
Vimsottari, Jaimini, Lal Kitab, mahadasha, antardasha,
any planet name (Mercury, Venus, Mars, Saturn, Jupiter, Rahu, Ketu)

RETURN THIS EXACT JSON STRUCTURE:
{
  "signal_line": "One sentence under 12 words. The core answer.",
  "plain_summary": "2-4 sentences. Direct answer to the question. Plain language. No jargon. Must be consistent with timing_window.",
  "action_item": "One specific action. Starts with a verb. Specific and dated if possible.",
  "timing_window": "Plain date range or timeframe. E.g. 'April–September 2026' or 'Next 3 weeks'",
  "why_this": "1-2 sentences explaining WHY this is happening in plain terms.",
  "confidence": "high | medium | low",
  "domain": "finance | career | relationships | health | location | general",
  "verdict": "RESOLVE | WAIT | ACT NOW | AVOID | STRENGTHEN | RELEASE"
}
"""


# ── Core function ────────────────────────────────────────────────────────────

async def generate_plain_english(
    raw_prediction: str,
    chart_context: dict,
    lk_context: Optional[str] = None,
    api_key: Optional[str] = None
) -> dict:
    """
    Convert raw /predict output into structured plain English.

    Args:
        raw_prediction: Full text from main Claude /predict call
        chart_context: dict with keys: lagna, dasha, age, country, concern
        lk_context: Optional Lal Kitab summary block string
        api_key: Anthropic API key (reads from env if not passed)

    Returns:
        dict with keys: plain_summary, action_item, signal_line,
                        timing_window, confidence, all_domains
    """
    import os
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        logger.error("plain_english: ANTHROPIC_API_KEY not set")
        return _fallback(raw_prediction, chart_context)

    user_message = _build_user_message(raw_prediction, chart_context, lk_context)
    
    # LANGUAGE LOCK — match user's question language
    _lang = (chart_context or {}).get("language", "en")
    if _lang and _lang.lower() in ("es", "spanish", "español"):
        user_message = (
            "CRITICAL: Respond in Spanish (español). All fields in the JSON output "
            "(plain_summary, action_item, signal_line, timing_window, why_this) "
            "MUST be written in Spanish. Do not translate to English.\n\n"
            + user_message
        )
    elif _lang and _lang.lower() in ("pt", "portuguese", "português"):
        user_message = (
            "CRITICAL: Respond in Portuguese. All JSON fields in Portuguese only.\n\n"
            + user_message
        )
    elif _lang and _lang.lower() in ("fr", "french", "français"):
        user_message = (
            "CRITICAL: Respond in French. All JSON fields in French only.\n\n"
            + user_message
        )
    elif _lang and _lang.lower() in ("hi", "hindi"):
        user_message = (
            "CRITICAL: Respond in Hindi. All JSON fields in Hindi only.\n\n"
            + user_message
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "system": PLAIN_ENGLISH_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_message}]
                }
            )
            resp.raise_for_status()
            data = resp.json()

        raw_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw_text += block.get("text", "")

        parsed = _parse_json(raw_text)
        validated = _validate_and_clean(parsed, chart_context)
        return validated

    except httpx.HTTPStatusError as e:
        logger.error(f"plain_english HTTP error: {e.response.status_code} — {e.response.text[:200]}")
        return _fallback(raw_prediction, chart_context)
    except Exception as e:
        logger.error(f"plain_english failed: {e}")
        return _fallback(raw_prediction, chart_context)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_user_message(raw_prediction: str, chart_context: dict, lk_context: Optional[str]) -> str:
    age = chart_context.get("age", "unknown")
    country = chart_context.get("country", "unknown")
    concern = chart_context.get("concern", "general")
    dasha = chart_context.get("dasha", "")

    parts = [
        f"USER CONTEXT: Age {age}, Country: {country}, Question domain: {concern}",
    ]
    if dasha:
        parts.append(f"Current planetary cycle: {dasha}")
    if lk_context:
        parts.append(f"\nLAL KITAB CONTEXT:\n{lk_context[:600]}")

    parts.append(f"\nRAW PREDICTION TO REWRITE:\n{raw_prediction[:2000]}")
    return "\n".join(parts)


def _parse_json(text: str) -> dict:
    """Extract JSON from Claude response, handles markdown fences and multiline values."""
    text = text.strip()

    # Strip markdown fences if present
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object within the text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            # Try sanitizing literal newlines inside string values
            sanitized = _sanitize_json_newlines(match.group())
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass

    # Last resort: try sanitizing the full text
    sanitized = _sanitize_json_newlines(text)
    try:
        return json.loads(sanitized)
    except json.JSONDecodeError:
        pass

    logger.warning("plain_english: could not parse JSON from Claude response")
    return {}


def _sanitize_json_newlines(text: str) -> str:
    """
    Replace literal newlines inside JSON string values with \\n.
    Handles cases where Claude outputs real newlines instead of \\n in strings.
    """
    import re as _re
    result = []
    in_string = False
    escape_next = False
    for i, ch in enumerate(text):
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == '\n':
            result.append('\\n')
            continue
        if in_string and ch == '\r':
            continue
        result.append(ch)
    return ''.join(result)


def _validate_and_clean(parsed: dict, chart_context: dict) -> dict:
    """Validate fields, strip jargon, enforce constraints."""
    result = {}

    # plain_summary
    ps = parsed.get("plain_summary", "")
    result["plain_summary"] = _strip_jargon(ps) if ps else None

    # action_item — must start with a verb
    ai = parsed.get("action_item", "")
    if ai:
        ai = _strip_jargon(ai)
        # Warn if it doesn't start with a verb (heuristic: not starting with capital verb)
        if ai and not _starts_with_verb(ai):
            logger.warning(f"plain_english: action_item may not start with verb: {ai[:60]}")
    result["action_item"] = ai if ai else None

    # signal_line — enforce 15-word limit
    sl = parsed.get("signal_line", "")
    if sl:
        sl = _strip_jargon(sl)
        words = sl.split()
        if len(words) > 15:
            sl = " ".join(words[:15])
            logger.warning("plain_english: signal_line truncated to 15 words")
    result["signal_line"] = sl if sl else None

    # timing_window — reject vague values
    tw = parsed.get("timing_window", "")
    vague = ["soon", "coming months", "in the future", "shortly", "eventually"]
    if any(v in tw.lower() for v in vague):
        logger.warning(f"plain_english: vague timing_window rejected: {tw}")
        tw = "Next 4 weeks"
    result["timing_window"] = tw if tw else "Next 4 weeks"

    # confidence
    conf = parsed.get("confidence", "medium").lower()
    if conf not in ("high", "medium", "low"):
        conf = "medium"
    result["confidence"] = conf

    # all_domains — validate against known domains
    raw_domains = parsed.get("all_domains", [])
    if isinstance(raw_domains, list):
        domains = [d.lower() for d in raw_domains if isinstance(d, str) and d.lower() in VALID_DOMAINS]
    else:
        domains = []
    # Always include the concern domain
    concern = chart_context.get("concern", "general")
    if concern and concern not in domains:
        domains.insert(0, concern)
    result["all_domains"] = domains if domains else ["general"]

    # PROBABILITY ENFORCEMENT — inject if user asked "will I" and Claude forgot
    _raw_q = (chart_context or {}).get("question", "") or (chart_context or {}).get("concern", "")
    _raw_q_lower = str(_raw_q).lower()
    _will_triggers = ["will i", "will my", "will this", "what are my chances",
                      "is it possible", "can i ever", "am i going to", "chances of",
                      "voy a", "cuales son mis", "es posible", "puedo",
                      "probability", "likelihood", "odds"]
    _is_probability_q = any(t in _raw_q_lower for t in _will_triggers)

    if _is_probability_q:
        _summary = (result.get("plain_summary") or "") + " " + (result.get("signal_line") or "")
        _has_pct = any(c in _summary for c in ["%", "percent", "por ciento"])
        if not _has_pct:
            # Claude forgot — inject computed probability based on confidence
            _conf = result.get("confidence", "medium")
            if isinstance(_conf, str):
                _pct_map = {"very high": 78, "high": 65, "medium": 50, "low": 32, "very low": 20}
                _pct = _pct_map.get(_conf.lower(), 50)
            elif isinstance(_conf, (int, float)):
                _pct = int(float(_conf) * 100) if _conf <= 1 else int(_conf)
            else:
                _pct = 50
            # Prepend to plain_summary
            if result.get("plain_summary"):
                result["plain_summary"] = f"PROBABILITY: {_pct}%. " + result["plain_summary"]
            if result.get("signal_line") and "%" not in result["signal_line"]:
                result["signal_line"] = f"{_pct}% — " + result["signal_line"]

    # why_this — new field from v6 prompt
    why_this = parsed.get("why_this", "")
    if why_this:
        why_this = _strip_jargon(why_this)
    result["why_this"] = why_this if why_this else None

    # bridge_practice_note — from v7 remedy bridge
    bpn = parsed.get("bridge_practice_note", "")
    result["bridge_practice_note"] = bpn if bpn else None

    # --- TIMING CONTRADICTION CHECK ---
    # Detect if plain_summary contradicts timing_window and log a warning
    try:
        _summary = result.get("plain_summary", "").lower()
        _timing = result.get("timing_window", "").lower()
        _friction_words = {"close", "closing", "block", "blocked", "friction", "avoid",
                           "caution", "wait", "delay", "difficult", "challenging", "not now"}
        _positive_words = {"strong", "peak", "active", "open", "opportunity", "best time",
                           "favorable", "window is open", "act now", "move now"}
        _timing_has_friction = any(w in _timing for w in _friction_words)
        _summary_has_positive = any(w in _summary for w in _positive_words)
        _timing_has_positive = any(w in _timing for w in _positive_words)
        _summary_has_friction = any(w in _summary for w in _friction_words)
        if _timing_has_friction and _summary_has_positive:
            import logging
            logging.getLogger("plain_english").warning(
                f"TIMING CONTRADICTION DETECTED: timing_window='{result.get('timing_window')}' "
                f"but plain_summary has positive framing. Chart may receive wrong signal. "
                f"Summary: '{result.get('plain_summary', '')[:100]}'"
            )
            # CORRECTION: patch plain_summary to preserve the friction/wait signal
            _negation_words = {"not", "don't", "avoid", "wait", "delay",
                               "hold off", "isn't", "won't", "pause", "caution"}
            _ps = result.get("plain_summary") or ""
            _ps_lower = _ps.lower()
            if _ps and not any(w in _ps_lower for w in _negation_words):
                result["plain_summary"] = (
                    "This is not the right moment to push forward. " + _ps
                )
                logging.getLogger("plain_english").info(
                    "plain_english: auto-corrected positive plain_summary to match friction timing"
                )
        elif _timing_has_positive and _summary_has_friction:
            import logging
            logging.getLogger("plain_english").warning(
                f"TIMING CONTRADICTION DETECTED: timing_window='{result.get('timing_window')}' "
                f"but plain_summary has friction framing. "
                f"Summary: '{result.get('plain_summary', '')[:100]}'"
            )
    except Exception:
        pass  # Never crash the prediction over a logging check
    # --- END TIMING CONTRADICTION CHECK ---


    return result


# ═══ ENERGY TRANSLATION MAP ═══
# Replaces planet names with energy frequencies in user-facing text
ENERGY_MAP = {
    "rahu":    "your ambition and breakthrough energy",
    "ketu":    "your intuition and release energy",
    "saturn":  "your discipline and structure energy",
    "jupiter": "your growth and wisdom energy",
    "mars":    "your action and drive energy",
    "venus":   "your love and partnership energy",
    "mercury": "your communication and intellect energy",
    "sun":     "your identity and authority energy",
    "moon":    "your emotional and nurturing energy",
}

# Dasha/period translations
PERIOD_MAP = {
    "rahu period":    "Ambition cycle",
    "rahu-saturn":    "Ambition-meets-Structure phase",
    "rahu-jupiter":   "Ambition-meets-Growth phase",
    "rahu-mercury":   "Ambition-meets-Communication phase",
    "rahu-venus":     "Ambition-meets-Magnetism phase",
    "rahu-mars":      "Ambition-meets-Execution phase",
    "rahu-moon":      "Ambition-meets-Emotional phase",
    "rahu-sun":       "Ambition-meets-Authority phase",
    "rahu-ketu":      "Ambition-meets-Extraction phase",
    "saturn period":  "Structure cycle",
    "jupiter period": "Growth cycle",
    "mars period":    "Execution cycle",
    "venus period":   "Magnetism cycle",
    "mercury period": "Communication cycle",
    "sun period":     "Authority cycle",
    "moon period":    "Emotional cycle",
    "ketu period":    "Extraction cycle",
    "mars-moon":      "Execution-meets-Emotional phase",
    "mars-saturn":    "Execution-meets-Structure phase",
    "mars-jupiter":   "Execution-meets-Growth phase",
    "mars-venus":     "Execution-meets-Magnetism phase",
    "mars-mercury":   "Execution-meets-Communication phase",
    "mars-rahu":      "Execution-meets-Ambition phase",
    "mars-sun":       "Execution-meets-Authority phase",
    "mars-ketu":      "Execution-meets-Extraction phase",
}

def _strip_jargon(text: str) -> str:
    """Replace planet names with energy frequencies and remove banned terms."""
    # Step 1: Replace dasha/period combinations first (longer matches first)
    for period_term, energy_label in sorted(PERIOD_MAP.items(), key=lambda x: -len(x[0])):
        pattern = re.compile(r'\b' + re.escape(period_term) + r'\b', re.IGNORECASE)
        text = pattern.sub(energy_label, text)

    # Step 2: Replace standalone planet names with energy translations
    for planet, energy in ENERGY_MAP.items():
        pattern = re.compile(r'\b' + re.escape(planet) + r'\b', re.IGNORECASE)
        text = pattern.sub(energy, text)

    # Step 3: Remove remaining banned Sanskrit terms
    for term in BANNED_TERMS:
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        text = pattern.sub("", text)

    # Clean up double spaces and orphaned punctuation
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r' ,', ',', text)
    text = re.sub(r' \.', '.', text)
    # Strip house number references (e.g., "10th house", "8th house lord")
    import re as _re
    text = _re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\s+house\s*(?:lord)?', '', text)
    text = _re.sub(r'\bhouse\s+\d{1,2}\b', '', text)

    return text.strip()


def _starts_with_verb(text: str) -> bool:
    """Heuristic: action items should start with a capital verb."""
    common_verbs = [
        "schedule", "reach", "write", "avoid", "focus", "start", "stop",
        "send", "call", "meet", "review", "prepare", "apply", "move",
        "take", "make", "set", "build", "create", "ask", "tell", "check",
        "sign", "delay", "prioritize", "reconnect", "spend", "save",
        "consult", "confirm", "submit", "pause", "launch", "complete"
    ]
    first_word = text.split()[0].lower() if text else ""
    return first_word in common_verbs


def _fallback(raw_prediction: str, chart_context: dict) -> dict:
    """Safe fallback — never crashes /predict."""
    concern = chart_context.get("concern", "general")
    summary = raw_prediction[:400] if raw_prediction else None
    # Try to strip jargon even from fallback
    if summary:
        summary = _strip_jargon(summary)
    return {
        "plain_summary": summary,
        "action_item": None,
        "signal_line": None,
        "timing_window": "Next 4 weeks",
        "confidence": "medium",
        "all_domains": [concern] if concern else ["general"],
        "why_this": None,
        "bridge_practice_note": None
    }


# ── Quality check (used in tests) ────────────────────────────────────────────

def quality_check(result: dict) -> list[str]:
    """
    Run the 5-point quality gate on a plain_english result.
    Returns list of failure strings. Empty list = pass.
    """
    failures = []

    ps = result.get("plain_summary", "") or ""
    ai = result.get("action_item", "") or ""
    sl = result.get("signal_line", "") or ""
    tw = result.get("timing_window", "") or ""

    # Gate 1: plain_summary must exist
    if not ps:
        failures.append("FAIL Gate 1: plain_summary is empty")

    # Gate 2: zero jargon in plain_summary and action_item
    for term in BANNED_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', ps, re.IGNORECASE):
            failures.append(f"FAIL Gate 2: banned term '{term}' in plain_summary")
        if re.search(r'\b' + re.escape(term) + r'\b', ai, re.IGNORECASE):
            failures.append(f"FAIL Gate 2: banned term '{term}' in action_item")

    # Gate 3: action_item starts with a verb
    if ai and not _starts_with_verb(ai):
        failures.append(f"FAIL Gate 3: action_item does not start with a verb: '{ai[:60]}'")

    # Gate 4: timing_window is specific
    vague = ["soon", "coming months", "in the future", "shortly", "eventually"]
    if any(v in tw.lower() for v in vague):
        failures.append(f"FAIL Gate 4: vague timing_window: '{tw}'")

    # Gate 5: signal_line under 15 words
    if sl and len(sl.split()) >= 15:
        failures.append(f"FAIL Gate 5: signal_line is {len(sl.split())} words (max 14): '{sl}'")

    return failures
