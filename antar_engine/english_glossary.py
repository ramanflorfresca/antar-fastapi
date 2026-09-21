# english_glossary.py
"""
Sprint EN-GLOSS-1 — English Sanskrit-gloss rules, generated at source.

English-generating prompts inject build_english_glossary_block() so the model
keeps no-Sanskrit by default and glosses only when unavoidable. This is the
English-side equivalent of what the ES/PT translator does — but produced in
the English prompt, NOT via the translator (which is untouched).
"""

ALLOWED_WITH_GLOSS = {
    # Proper-noun lunar nodes with no clean English equivalent.
    # Coach voice translates these entirely (no Sanskrit at all).
    # Mentor voice uses the term with a first-mention bracket gloss.
    "Rahu": "your karmic amplifier node",
    "Ketu": "your karmic release point",
}

FORBIDDEN = {
    # [de-jargon 2026-09-21] Sanskrit -> PLAIN life language. The old
    # replacements were still jargon ("planetary cycle", "sub-cycle", "angular
    # house") — a user saw "your current major planetary cycle lord is transiting
    # a zone of hidden assets". Replace with everyday life-chapter language.
    "Mahadasha":       "the chapter of life you're in",
    "Antardasha":      "the phase inside your current chapter",
    "Pratyantardasha": "this shorter stretch of weeks",
    "Vimshottari":     "your life-timing pattern",
    "Ashtottari":      "your life-timing pattern",
    "Sade Sati":       "a roughly seven-year stretch of pressure and consolidation",
    "Kendra":          "a strong, action-ready area of life",
    "Trikona":         "a fortunate, easy-flowing area of life",
    "Dushthana":       "a demanding, testing area of life",
    "Lagna":           "your core self and how you meet the world",
    "Viparita Raja Yoga": "a pattern that turns setbacks into strength",
    "Mahapurusha":     "a standout strength in your character",
    "Vargottama":      "an especially strong part of you",
    "Atmakaraka":      "your soul's driving theme",
    "Karakamsa":       "your soul's core theme",
    "Upapada":         "your relationship anchor",
}


def build_english_glossary_block(voice_tier: str = "coach") -> str:
    """
    Returns the prompt block to inject into English-generating prompts.
    voice_tier: 'coach' (default) or 'mentor'.
    """
    forbidden_lines = "\n".join(
        f'  - "{term}" -> use "{replacement}"'
        for term, replacement in FORBIDDEN.items()
    )

    if voice_tier == "mentor":
        # Mentor voice: Rahu/Ketu may appear by name with gloss on first mention.
        allowed_lines = "\n".join(
            f'  - "{term}" is allowed. On FIRST mention only, follow with " ({gloss})". '
            f'Subsequent mentions in the same response: bare term, no gloss.'
            for term, gloss in ALLOWED_WITH_GLOSS.items()
        )
        allowed_section = (
            "ALLOWED SANSKRIT TERMS (Mentor voice - first mention gets bracket gloss):\n"
            f"{allowed_lines}"
        )
    else:
        # Coach voice: Rahu/Ketu must be translated completely, never named.
        coach_lines = "\n".join(
            f'  - "{term}": never write the word "{term}" anywhere. Use energy language '
            f'such as "{gloss}". When the chart data labels a dasha, sub-cycle, period '
            f'or "chapter" by "{term}", name that period ONLY by its energy quality '
            f'(for example: an amplification chapter, a release-and-detachment chapter). '
            f'Never append "{term}" in parentheses after the energy phrase.'
            for term, gloss in ALLOWED_WITH_GLOSS.items()
        )
        allowed_section = (
            "COACH VOICE - HARD RULE FOR THE LUNAR NODES (Rahu, Ketu):\n"
            'The words "Rahu" and "Ketu" must NEVER appear in your output - not as a\n'
            "bare word, not inside parentheses, not as a gloss, not even once.\n"
            'This OVERRIDES any energy-first "energy name (Planet)" formatting rule\n'
            "stated earlier in this prompt: that parenthetical-planet format does NOT\n"
            "apply to Rahu or Ketu. Replace them with energy language entirely.\n"
            f"{coach_lines}"
        )

    return f"""
## ENGLISH LANGUAGE RULES (Sanskrit handling)

You are writing in English. Apply these rules strictly. Where they conflict
with any formatting rule stated earlier in this prompt, THESE RULES WIN.

FORBIDDEN SANSKRIT TERMS (must be replaced - never appear in output, even with gloss):
{forbidden_lines}

{allowed_section}

NEVER USE THESE MECHANICS WORDS (they read as astrology jargon):
- "lord", "ruler of", "cycle lord", "period lord"
- "transiting", "transit", "moving through", "passing through a zone/house"
- "zone", "house", "placement", "aspect", "aspecting", "conjunct"
Instead, name the LIFE AREA and what is happening in it, plainly. Do NOT write
"your cycle lord is transiting a zone of hidden assets and inheritance" — write
"this is a stretch that stirs shared money, debts and inheritance, and the gain
is slow to arrive." Describe the life, never the machinery.

GENERAL PRINCIPLE:
- Default: translate the concept, do not name it. Example: instead of "Mahadasha" write "the chapter of life you're in."
- Only Rahu and Ketu have first-mention bracket-gloss treatment, and only in Mentor voice.
- All other Sanskrit/Vedic technical terms must be fully translated into plain English.
- Glosses, when used, are 6 words or fewer and contain no Sanskrit.
- Nakshatra names: do not display in user-facing English output. Use the energy description instead.
- Planet names (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn) are fine in their English form at Mentor voice; in Coach voice use energy language per the existing voice rules.
""".strip()
