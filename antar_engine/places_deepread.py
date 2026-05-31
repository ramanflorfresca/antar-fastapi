"""
antar_engine/places_deepread.py
─────────────────────────────────────────────────────────────────────────────
PLACES — LLM deep-read prompt builder.  Phase 2.

When /city is called with deep_read=true, the endpoint feeds these facts to
Claude Sonnet to synthesise an immersive 2-3 paragraph reading of how a place
feels for a given concern.  The facts are pre-translated into energy/axis
language here, so no planet names, house numbers, or Sanskrit ever enter the
prompt — and the response still passes through the default user-facing strip
(source="llm") as a second safety net.

NO verdicts: the model is instructed to render texture, never "move here".
"""

from __future__ import annotations

from typing import Optional

from antar_engine.places_composer import _lang, _domain, _axis  # reuse phrasing

DEEP_READ_SYSTEM = (
    "You are Antar, a calm, precise guide who reads how a place would feel for "
    "a person, based on their life-map. You speak in plain, warm, embodied "
    "language about energy and texture — never astrology jargon. "
    "HARD RULES: (1) Never tell the person to move somewhere or not to — only "
    "describe the texture and the trade-offs. (2) Never use technical terms, "
    "planet names, house numbers, sign names, or Sanskrit. (3) Speak in second "
    "person ('you'). (4) Keep it to 2-3 short paragraphs. (5) Be honest about "
    "friction where it exists; do not flatter a place."
)

_TIER_FEEL = {
    "FLOW": {"en": "broadly supportive", "es": "ampliamente favorable"},
    "MIXED": {"en": "mixed — support and friction together", "es": "mixta — apoyo y fricción juntos"},
    "STRAIN": {"en": "demanding, asking for care", "es": "exigente, que pide cuidado"},
}

_POLARITY_FEEL = {
    "supportive": {"en": "a supportive current", "es": "una corriente de apoyo"},
    "mixed": {"en": "an uneven current", "es": "una corriente desigual"},
    "friction": {"en": "a current under strain", "es": "una corriente tensionada"},
}

_BAND_FEEL = {
    "strong": {"en": "very close and strongly felt", "es": "muy cerca y muy presente"},
    "moderate": {"en": "near, felt in the background", "es": "cercana, presente de fondo"},
    "ignored": {"en": "faint", "es": "tenue"},
}


def _signal_phrase(sig: dict, lang: str) -> str:
    pol = _POLARITY_FEEL.get(sig.get("polarity", "mixed"), _POLARITY_FEEL["mixed"])[lang]
    band = _BAND_FEEL.get(sig.get("band", "moderate"), _BAND_FEEL["moderate"])[lang]
    axis = _axis(sig.get("angle", ""), lang)
    dist = int(round(sig.get("distance_km", 0)))
    if lang == "es":
        return f"- {pol} sobre {axis}, {band} (~{dist}km)"
    return f"- {pol} along {axis}, {band} (~{dist}km)"


def build_deep_read_prompt(
    scored: dict,
    relocation: dict,
    active_lines: list,
    concern: Optional[str],
    language: str,
) -> str:
    """Compose the user prompt of energy-framed facts for the deep read."""
    lang = _lang(language)
    city = scored.get("city", {}).get("name", "this place")
    domain = _domain(concern, lang) if concern else ("your life overall" if lang == "en" else "tu vida en general")
    tier = scored.get("tier", "MIXED")
    score = scored.get("score", 0)
    tier_feel = _TIER_FEEL.get(tier, _TIER_FEEL["MIXED"])[lang]

    signals = scored.get("_signals", [])[:4]
    sig_block = "\n".join(_signal_phrase(s, lang) for s in signals) or (
        "- (no strong currents cross nearby)" if lang == "en" else "- (no cruzan corrientes fuertes cerca)"
    )

    # Relocation framed as an inner-baseline shift, no sign names.
    shift = relocation.get("lagna_shift_houses", 0) or 0
    if lang == "es":
        reloc_line = (
            "Tu base interior se mantiene parecida aquí." if shift == 0
            else "Tu base interior y tu forma de presentarte se reorganizan de forma notable en este lugar."
        )
    else:
        reloc_line = (
            "Your inner baseline stays close to home here." if shift == 0
            else "Your inner baseline and the way you show up reorganise noticeably in this place."
        )

    watch = scored.get("_watch", [])
    has_hidden = any(w.get("kind") == "hidden_cost_house" for w in watch)
    has_friction = any(w.get("kind") == "friction_line" for w in watch)
    watch_notes = []
    if has_hidden:
        watch_notes.append(
            "energía que puede escaparse en costos no visibles" if lang == "es"
            else "energy that can drain into costs you don't see coming"
        )
    if has_friction:
        watch_notes.append(
            "una corriente que pide más paciencia" if lang == "es"
            else "a current that asks for extra patience"
        )
    watch_block = ("; ".join(watch_notes)) if watch_notes else (
        "ninguna fricción marcada" if lang == "es" else "no marked friction"
    )

    lang_name = {"en": "English", "es": "Spanish", "pt": "Portuguese",
                 "hi": "Hindi", "hinglish": "Hinglish"}.get(language.lower(), "English")

    if lang == "es":
        head = (
            f"Escribe una lectura inmersiva de cómo se sentiría {city} para {domain}.\n"
            f"Idioma de salida: {lang_name}.\n\n"
            f"Textura general: {tier_feel} (intensidad {score}/100).\n"
            f"Corrientes activas:\n{sig_block}\n\n"
            f"Reubicación interior: {reloc_line}\n"
            f"A vigilar: {watch_block}.\n\n"
            "Teje esto en 2-3 párrafos cálidos en segunda persona. Sin jerga, sin "
            "nombres técnicos, sin decirle a la persona que se mude o no se mude."
        )
    else:
        head = (
            f"Write an immersive reading of how {city} would feel for {domain}.\n"
            f"Output language: {lang_name}.\n\n"
            f"Overall texture: {tier_feel} (intensity {score}/100).\n"
            f"Active currents:\n{sig_block}\n\n"
            f"Inner relocation: {reloc_line}\n"
            f"Watch for: {watch_block}.\n\n"
            "Weave this into 2-3 warm, second-person paragraphs. No jargon, no "
            "technical names, and never tell the person to move or not move."
        )
    return head
