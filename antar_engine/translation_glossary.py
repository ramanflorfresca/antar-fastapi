"""
antar_engine/translation_glossary.py

Loc-4 — Vedic translation glossary + translator system-prompt builder.

Per the "Loc-4 Sanskrit Term Handling Refinement" addendum: Sanskrit technical
terms are preserved, but on FIRST use within each individual string they get a
brief parenthetical explanation; planet names are localized (Rahu/Ketu kept).

NOTE: this file is the glossary half of Loc-4. The translation middleware
(decorator, cache, _call_translator, per-endpoint rollout) is defined by the
main Loc-4 brief (COWORK_Loc4_LLM_Translation_Middleware.md) and is not wired
in yet — this module is inert until that middleware imports it.
"""

VEDIC_GLOSSARY = {
    # Sanskrit terms with brief Spanish/Portuguese explanations for first-use parenthetical
    "term_explanations": {
        "es": {
            "Mahadasha": "ciclo planetario principal",
            "Antardasha": "subperíodo planetario",
            "Pratyantardasha": "sub-subperíodo",
            "Sookshma Dasha": "subperíodo fino",
            "lagna": "punto ascendente",
            "rasi": "signo lunar",
            "nakshatra": "mansión lunar",
            "navamsa": "carta de matrimonio y dharma",
            "gochar": "tránsito planetario",
            "Raj Yoga": "combinación de poder",
            "Mahapurusha": "yoga de gran personalidad",
            "Viparita Raja Yoga": "combinación de éxito por adversidad",
            "Neechabhanga": "cancelación de debilitamiento",
            "dharma": "propósito de vida",
            "karma": "acción y consecuencia",
            "mantra": "fórmula sagrada",
            "yantra": "diagrama sagrado",
            "puja": "ritual de ofrenda",
        },
        "pt": {
            "Mahadasha": "ciclo planetário principal",
            "Antardasha": "subperíodo planetário",
            "Pratyantardasha": "sub-subperíodo",
            "Sookshma Dasha": "subperíodo fino",
            "lagna": "ponto ascendente",
            "rasi": "signo lunar",
            "nakshatra": "mansão lunar",
            "navamsa": "carta de casamento e dharma",
            "gochar": "trânsito planetário",
            "Raj Yoga": "combinação de poder",
            "Mahapurusha": "yoga de grande personalidade",
            "Viparita Raja Yoga": "combinação de sucesso pela adversidade",
            "Neechabhanga": "cancelamento de enfraquecimento",
            "dharma": "propósito de vida",
            "karma": "ação e consequência",
            "mantra": "fórmula sagrada",
            "yantra": "diagrama sagrado",
            "puja": "ritual de oferenda",
        },
    },

    # Planet names — translate to localized form
    "translate_planets": {
        "es": {
            "Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio",
            "Jupiter": "Júpiter", "Venus": "Venus", "Saturn": "Saturno",
            "Rahu": "Rahu", "Ketu": "Ketu",
        },
        "pt": {
            "Sun": "Sol", "Moon": "Lua", "Mars": "Marte", "Mercury": "Mercúrio",
            "Jupiter": "Júpiter", "Venus": "Vênus", "Saturn": "Saturno",
            "Rahu": "Rahu", "Ketu": "Ketu",
        },
    },
}


def build_translation_system_prompt(language_name: str, language_code: str) -> str:
    """
    Builds the system prompt for the translator LLM with the appropriate glossary.
    """
    explanations = VEDIC_GLOSSARY["term_explanations"].get(language_code, {})

    # Build the explanation table for the prompt
    explanation_lines = []
    for sanskrit_term, brief_explanation in explanations.items():
        explanation_lines.append(f"  - {sanskrit_term} → first use: \"{sanskrit_term} ({brief_explanation})\", subsequent uses: \"{sanskrit_term}\"")
    explanation_block = "\n".join(explanation_lines)

    planet_translations = VEDIC_GLOSSARY["translate_planets"].get(language_code, {})
    planet_lines = [f"  - {en} → {target}" for en, target in planet_translations.items()]
    planet_block = "\n".join(planet_lines)

    return f"""You are a translator for Antar, a Vedic astrology platform.

Translate English strings into {language_name} while preserving the following rules:

1. SANSKRIT TERMS — first-use parenthetical pattern:
   On the FIRST occurrence of a Sanskrit term in a response, include a brief parenthetical explanation.
   On SUBSEQUENT occurrences of the same term in the same response, use the term alone.

{explanation_block}

   Example (Spanish):
   - Input: "Your Mahadasha is ending. The next Mahadasha will be Rahu's."
   - Output: "Tu Mahadasha (ciclo planetario principal) está terminando. La próxima Mahadasha será la de Rahu."

   Note: "Mahadasha" appears twice in the input; only the FIRST is followed by the parenthetical explanation.

2. PLANET NAMES — translate to localized form:
{planet_block}
   Keep Rahu and Ketu as-is in all languages.

3. VOICE AND TONE:
   - Antar is a "precision instrument" — voice is precise, conditional, slightly clinical
   - DO NOT use manifestation language ("the universe is sending you...", "align with energy", "vibrations")
   - DO use conditional precision ("if X happens, then Y is likely", "watch for Z in this window")
   - Use formal "usted" form in Spanish for serious contexts
   - Use "você" in Brazilian Portuguese

4. CULTURAL REGISTER:
   - LATAM-neutral Spanish (not Spain Spanish: "manejar" not "conducir", "computadora" not "ordenador")
   - Brazilian Portuguese (not European Portuguese: "você" not "tu", "trem" not "comboio")
   - Vedic concepts should feel native and educational, not exotic

5. FORMAT REQUIREMENTS:
   - Output must be valid JSON matching the input structure exactly
   - Preserve ALL keys exactly — only translate values
   - Preserve markdown formatting (**, *, _, line breaks, lists) inside translated strings
   - Preserve numbers, dates, percentages, currencies, and proper nouns
   - Preserve any HTML tags if present

6. STRING-BY-STRING TRANSLATION CONTEXT:
   IMPORTANT: Each input string is independent. Sanskrit terms may appear across multiple strings.
   For first-use parenthetical, apply the rule WITHIN each individual string:
   - If "Mahadasha" appears in string A and string B, BOTH get the parenthetical on first use within their own string
   - The first-use rule applies PER STRING, not across the entire response

   This ensures each piece of UI text is self-explanatory even when shown in isolation.

Return ONLY the JSON object. No preamble, no markdown code fences."""
