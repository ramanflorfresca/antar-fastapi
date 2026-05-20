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

GENERAL PRINCIPLE:
- Default: translate the concept, do not name it. Example: instead of "Mahadasha" write "your current 18-year planetary cycle."
- Only Rahu and Ketu have first-mention bracket-gloss treatment, and only in Mentor voice.
- All other Sanskrit/Vedic technical terms must be fully translated into plain English.
- Glosses, when used, are 6 words or fewer and contain no Sanskrit.
- Nakshatra names: do not display in user-facing English output. Use the energy description instead.
- Planet names (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn) are fine in their English form at Mentor voice; in Coach voice use energy language per the existing voice rules.
""".strip()
