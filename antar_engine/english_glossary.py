# english_glossary.py
"""
Sprint EN-GLOSS-1 — English Sanskrit-gloss rules, generated at source.

English-generating prompts inject build_english_glossary_block() so the model
keeps no-Sanskrit by default and glosses only when unavoidable. This is the
English-side equivalent of what the ES/PT translator does — but produced in
the English prompt, NOT via the translator (which is untouched).
"""

ALLOWED_WITH_GLOSS = {
    # Proper-noun planet nodes with no clean English equivalent.
    # Gloss appears on FIRST mention only, bare term after.
    # Voice tier matters: Coach voice translates these entirely.
    # Mentor voice uses the term with gloss.
    "Rahu": "your karmic amplifier node",
    "Ketu": "your karmic release point",
}

FORBIDDEN = {
    # Sanskrit -> mandatory English replacement.
    # These have clean translations and recur enough that glossing
    # every time would pollute the output.
    "Mahadasha":       "your current major planetary cycle",
    "Antardasha":      "your current sub-cycle",
    "Pratyantardasha": "your current micro-cycle",
    "Vimshottari":     "the 120-year cycle system",
    "Ashtottari":      "the 108-year cycle system",
    "Sade Sati":       "the 7.5-year Saturn transit through and around your Moon sign",
    "Kendra":          "angular house",
    "Trikona":         "trine house",
    "Dushthana":       "challenge house",
    "Lagna":           "your rising sign",
    "Viparita Raja Yoga": "your reversal-into-strength pattern",
    "Mahapurusha":     "great-person pattern",
    "Vargottama":      "doubly strong placement",
    "Atmakaraka":      "your soul-significator planet",
    "Karakamsa":       "your soul-significator's sign in the divisional chart",
    "Upapada":         "your relationship anchor point",
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
        # Coach voice: Rahu/Ketu must be translated, not named.
        coach_lines = "\n".join(
            f'  - "{term}" -> use "{gloss}" (do not use the Sanskrit term)'
            for term, gloss in ALLOWED_WITH_GLOSS.items()
        )
        allowed_section = (
            "COACH VOICE - translate these terms, do not name them:\n"
            f"{coach_lines}"
        )

    return f"""
## ENGLISH LANGUAGE RULES (Sanskrit handling)

You are writing in English. Apply these rules strictly:

FORBIDDEN SANSKRIT TERMS (must be replaced - never appear in output, even with gloss):
{forbidden_lines}

{allowed_section}

GENERAL PRINCIPLE:
- Default: translate the concept, do not name it. Example: instead of "Mahadasha" write "your current 18-year planetary cycle."
- Only Rahu and Ketu have first-mention bracket-gloss treatment, and only in Mentor voice.
- All other Sanskrit/Vedic technical terms must be fully translated into plain English.
- Glosses, when used, are 6 words or fewer and contain no Sanskrit.
- Nakshatra names: do not display in user-facing English output. Use the energy description instead.
- Planet names (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn) are fine in their English form at Mentor voice; in Coach voice use energy language per the existing voice rules.
""".strip()
