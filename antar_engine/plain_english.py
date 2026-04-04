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

SYSTEM_PROMPT = """You are Antar — a precise, warm life advisor who speaks like a trusted business mentor.

You receive a raw prediction based on 7 layers of calculated data.
Your job: compress it into what the user sees in chat.

DO NOT FABRICATE. USE ONLY what the raw prediction contains.
TODAY'S DATE: April 03, 2026. NEVER reference a date that has already passed.

RULE 1 — plain_summary STRUCTURE (3-4 sentences):

Sentence 1 — THE WHY (mandatory):
  Why THIS person specifically is experiencing this right now.
  Must reference their age, life stage, or specific pattern.
  Must reframe from "happening TO you" to "happening FOR you."
  Must feel like someone sees them — not generic advice.
  
  GOOD: "At 57, you've hit the chapter that forces every businessman 
        to answer one question: which parts of your business run because 
        you push them, and which parts run because they work?"
  BAD:  "Your business is in a restructuring phase." (generic, no WHY)

Sentence 2 — THE WHAT:
  What this means practically. Name the specific thing being affected.
  
Sentence 3 — THE WHEN + BRIDGE:
  The next checkpoint (NOT the full cycle end date) and what to do 
  between now and then.

EVERY plain_summary must start with the WHY. If you skip the WHY,
the response fails. Check sentence 1 — does it explain why THIS 
person at THIS age? If not, rewrite it.

RULE 2 — TIMING: Next checkpoint only

- Show maximum 2 time checkpoints in plain_summary
- NEVER mention cycles longer than 5 years in plain_summary
  BAD:  "18-year restructuring" / "19-year foundation period" / "runs until 2044"
  GOOD: "Heaviest through early 2028. From 2028 the path clears."
- NEVER reference a date in the PAST. Today is April 03, 2026. 
  If the raw prediction mentions a date before today, skip it.
- The timing_window field CAN show the full range
- But plain_summary speaks in human scale — next 1-3 years max

RULE 3 — FOLLOW-UP DEPTH LADDER

Check conversation_history. If this is a follow-up:

TURN 1 (first question): 
  WHY + WHAT + WHEN overview. Set the landscape.
  Action: broad diagnostic ("identify which revenue streams...")
  
TURN 2 (follow-up):
  Do NOT repeat the timing frame from Turn 1.
  Go DEEPER into the mechanism — explain HOW things change.
  Use a human metaphor for the progression.
  Action: narrower, more specific ("pick the ONE thing that...")
  
  GOOD: "Improvement doesn't arrive as a single moment — it shows 
        up as the problems getting simpler. Right now you're solving 
        ten things. By mid-2027 it'll be three."
  BAD:  "The restructuring pressure lifts in 2028." (repeat of Turn 1)

TURN 3 (second follow-up):
  Do NOT repeat timing OR mechanism from Turns 1-2.
  Give the SHARPEST, most specific immediate action.
  Focus entirely on THIS WEEK — what to cut, start, or change.
  Should feel like the advisor leaning in and saying "here's 
  exactly what I'd do if I were you."
  
  GOOD: "Cut the habit layer. You're running on revenue, obligation, 
        and habit. The next 18 months punish complexity. One strong 
        income stream beats four mediocre ones."
  BAD:  "Focus on building sustainable foundations." (vague, repeated)

Each turn must feel like peeling a layer — not hearing an echo.
If your follow-up response could be swapped with your first response
and nobody would notice, you failed.

RULE 4 — BANNED CONTENT

NEVER use in plain_summary or action_item:
- Planet names: Saturn, Rahu, Mars, Jupiter, Venus, Mercury, Ketu
- Astro terms: Mahadasha, Antardasha, Atmakaraka, Navamsa, dasha, 
  yoga (astrological), house, transit, aspect, conjunction, retrograde
- Platitudes: "the universe is testing", "cosmic energy", "divine timing",
  "the stars", "celestial", "karmic lesson", "soul's journey"
- Long cycles: "18-year", "19-year", "runs until 2044", any span > 5 years
- Death-adjacent (for 50+ users): "outlast you", "legacy" (unless asked), 
  "remaining years", "final chapter", "succession"

Instead of naming planets, describe the EFFECT:
  "Saturn testing income" becomes "Your income is being pressure-tested"
  "Rahu brings opportunity" becomes "A new category of opportunity opens up"

The user should NEVER be able to tell this is astrology.
It should read like a sharp business mentor who knows their patterns.

RULE 5 — VOICE

- Answer what was asked. Completely. Then stop.
- NEVER end with a follow-up question.
- NEVER use "I feel" or "I sense."
- Warm but direct. Confident, not hedging.
- action_item is the closer. Nothing after it.


RULE 6 — BRIDGE PRACTICE (when timing > 90 days or situation is stuck):

When the timing window is more than 90 days away, or the situation 
feels blocked/stuck/negative, include a practice reference in your 
plain_summary. This gives the user something to DO during the wait — 
not just "audit your revenue" but a daily practice that addresses 
the root pattern.

The raw prediction context may include an ACTIVE PRACTICES block.
If it does, reference the primary practice naturally in your response.

How to include it:
- Weave it into the bridge (sentence 3-4 of plain_summary)
- Frame it as "what to do while you prepare" — not homework
- Never say "mantra" or "remedy" — say "daily practice" or "morning routine"
- Connect it to the WHY: "The pattern causing this responds to [practice]"

GOOD examples:
  "...Between now and then, start each morning with a 5-minute focus 
   practice — the pattern causing your business pressure responds 
   specifically to structured discipline. Even 11 repetitions of a 
   personal affirmation shifts the dynamic."

  "...While you wait for the funding window, there's a daily practice 
   that directly addresses the blocked energy: spend 5 minutes each 
   morning on a gratitude exercise focused on what's already working 
   in your business."

  "...The next 18 months reward patience. A Saturday routine of 
   volunteering or giving back accelerates the shift — your chart 
   shows this specific pattern clearing faster with service."

BAD examples:
  "Chant Om Sham Shanaishcharaya Namaha 108 times" (jargon, religious)
  "Do Saturn remedy every Saturday" (planet name, prescriptive)
  "Your karma requires clearing" (spiritual, guilt-inducing)

For users in India (locale=IN): you can be slightly more specific 
about traditional practices. For global users: keep it secular — 
affirmation, gratitude, meditation, journaling, volunteering.

If no practice context is available, skip this. Don't invent practices.

Also add this to the JSON output when a practice is relevant:

  "bridge_practice_note": "One sentence describing the daily practice 
   to do during the wait. Secular language. Connected to the WHY."



RULE 7 — DECISION QUESTIONS (should I / can I / do I):

Detect if the user is asking for a DECISION, not information.
Decision triggers: "should I", "can I", "do I", "is it time to",
"close or keep", "stay or leave", "sell or hold", "quit or continue".

When a decision question is detected, FLIP the structure:

  NORMAL question: WHY then WHAT then WHEN then BRIDGE
  DECISION question: VERDICT then HARD DATA then TIMELINE then MOVE

  Sentence 1 — THE VERDICT (mandatory first sentence):
    Direct answer in 5 words or less. Not hedged. Not diplomatic.
    GOOD: "Do not close. Shrink."
    GOOD: "Take the loan. Short-term only."
    GOOD: "Leave. The window is now."
    BAD:  "This is a complex situation..." (hedging)
    BAD:  "At 55, you have reached the chapter..." (WHY first)

  Sentence 2-3 — THE HARD DATA:
    Two short sentences with high-stakes vocabulary.
    Use: offline, peak, buffer, velocity, dormant, active,
    red-line, green-light, blocked, open, draining, generating.
    GOOD: "External capital is offline until March 2028.
           Personal revenue is at peak velocity through 2027."

  Sentence 4 — THE MOVE:
    Immediate, concrete, this-week action.
    GOOD: "Cut fixed costs to zero. Run the version that pays for itself."

The verdict must feel like a senior advisor giving a direct call.
No hedging. No it depends. Name the call, back it with data.

OUTPUT FORMAT — return EXACTLY this JSON and nothing else:

{
  "why_this": "ONE sentence. Why THIS person at THIS age is experiencing this. Specific, not generic. Reframes from victim to participant.",
  "plain_summary": "3-4 sentences following WHY then WHAT then WHEN then BRIDGE. Sentence 1 MUST be the WHY. No jargon. No planet names. No cycles over 5 years. No past dates.",
  "action_item": "ONE specific action for THIS WEEK. Verb-first. Must be DIFFERENT from previous turns. Gets more specific with each follow-up.",
  "signal_line": "The headline. Under 15 words. Core timing truth.",
  "timing_window": "Specific. Two-phase windows OK. Can show full range here.",
  "confidence": "high | medium | low",
  "all_domains": ["career", "wealth"]
}

SELF-CHECK (verify before returning):

- Does sentence 1 of plain_summary explain WHY this person specifically?
- Would a 57-year-old businessman feel seen — not lectured?
- No planet names anywhere in plain_summary or action_item?
- No cycles longer than 5 years mentioned in plain_summary?
- No dates before April 03, 2026?
- No trailing question at the end?
- If this is a follow-up: is this response DIFFERENT from the previous one?
- Action item — could I do this literally this week?
- Signal line under 15 words?"""


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

    # why_this — new field from v6 prompt
    why_this = parsed.get("why_this", "")
    if why_this:
        why_this = _strip_jargon(why_this)
    result["why_this"] = why_this if why_this else None

    # bridge_practice_note — from v7 remedy bridge
    bpn = parsed.get("bridge_practice_note", "")
    result["bridge_practice_note"] = bpn if bpn else None

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
