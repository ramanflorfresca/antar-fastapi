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

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"
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

SYSTEM_PROMPT = """You are Antar — a precise, empathetic life navigation advisor.

You have received a raw astrological prediction for a user. Your job is to rewrite it 
as a clear, jargon-free life signal that any person can immediately understand and act on.

STRICT RULES:
- NO Sanskrit or astrological jargon of any kind in plain_summary or action_item
- Do NOT use these words: Mahadasha, Antardasha, Atmakaraka, Navamsa, Amatyakaraka, 
  Lagna, Nakshatra, Dasha, Rashi, Bhava, Graha, Yogakaraka, Varshphal, Teva, Umra
- Instead of "your Mahadasha lord" → say "the planetary cycle you are in"
- Instead of "Lagna lord" → say "your chart's ruling energy"
- action_item must start with a verb (Schedule, Reach out, Write, Avoid, Focus, etc.)
- timing_window must be SPECIFIC — never "soon" or "in the coming months"
- signal_line must be under 15 words

DO NOT FABRICATE. Base everything only on the prediction text provided.

Return ONLY valid JSON, no markdown, no preamble, no explanation:

{
  "plain_summary": "2-3 sentences. What is happening in their life right now. Zero jargon. Warm but precise.",
  "action_item": "ONE specific action they can take THIS WEEK. Verb-first. One sentence only.",
  "signal_line": "One headline sentence. Under 15 words. The core message.",
  "timing_window": "Specific window — e.g. 'Next 3 weeks' or 'Before April 15' or 'Now through June'",
  "confidence": "high or medium or low",
  "all_domains": ["career", "wealth"]
}

confidence guide:
- high = multiple data layers agree strongly on this signal
- medium = clear signal from 1-2 layers
- low = mixed signals or limited data"""


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
                    "system": SYSTEM_PROMPT,
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
        if not parsed:
            logger.warning("plain_english: empty parse — using fallback")
            return _fallback(raw_prediction, chart_context)
        validated = _validate_and_clean(parsed, chart_context)
        # If plain_summary still None after validate, use fallback
        if not validated.get("plain_summary"):
            logger.warning("plain_english: plain_summary null after validate — using fallback")
            return _fallback(raw_prediction, chart_context)
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
    """Extract JSON from Claude response, handles markdown fences."""
    text = text.strip()

    # Strip markdown fences if present
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    logger.warning("plain_english: could not parse JSON from Claude response")
    return {}


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

    return result


def _strip_jargon(text: str) -> str:
    """Remove banned Sanskrit/astrology terms from text."""
    for term in BANNED_TERMS:
        # Case-insensitive whole-word replacement
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        text = pattern.sub("[planetary cycle]", text)
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
        "all_domains": [concern] if concern else ["general"]
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
