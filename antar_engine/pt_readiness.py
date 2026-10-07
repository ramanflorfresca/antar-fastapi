"""
[pt-gate] Per-surface Portuguese readiness registry.

Brazil launch strategy: the frontend always sends language=pt for PT users;
the BACKEND decides per surface whether to serve Portuguese or fall back to
clean English. Never Spanish, never mixed.

Flip a surface to True ONLY after it has been verified clean in PT
(Part C of the language sprint). No frontend deploy is needed to turn a
surface on — edit this dict, commit, push.

Surface keys match either the endpoint's translate_response endpoint_name
(decorated surfaces) or the literal string passed to gate_language() in the
endpoint body (source-generated surfaces).
"""

PT_READY = {
    # ── Response-time translated (Haiku via translation_middleware). ──
    # PT comes from machine translation of the English source at response
    # time — clean by construction, no mixed-language risk.
    "home": True,
    "predict_week": True,
    "upcoming-themes": True,
    "day-deep": True,

    # ── Source-generated per-language — known PT defects (Part C). ──
    "welcome": True,             # [loc-3] v2 engine has authored PT prompt; the gate was the only blocker
    "weekly-briefing": True,     # [loc-3] hard LANGUAGE block prepended as reinforcement
    "monthly-deepdive": True,    # [loc-3] hard LANGUAGE block prepended as reinforcement
    "annual-plan": True,         # [loc-3] hard LANGUAGE block prepended as reinforcement
    "daily-week": True,          # [loc-3] pt routes signal prose through gated middleware
    "executive-summary": True,   # [loc-3] pt/fr middleware route added
    "dashboard": True,           # [loc-3] es/pt/fr middleware route added
    "life-arc": True,            # [loc-3] cache-path translate_dict covers pt/fr
    "practices-schedule": True,  # [loc-3] middleware backstop covers pt/fr
}

# Unlisted surfaces hit the gate only through translation_middleware, whose
# PT output is response-time machine translation (the clean path) — so the
# registry default is True. Source-generated surfaces must be wired
# explicitly through gate_language() AND listed above.
# [fr-gate 2026-07-04] French mirrors the PT launch pattern:
# response-time machine-translated surfaces are clean by construction
# (registry default True); source-generated surfaces stay English
# until each is verified natively in FR. Same keys as PT_READY.
FR_READY = {
    "welcome": False,
    "weekly-briefing": False,
    "monthly-deepdive": False,
    "annual-plan": False,
    "daily-week": True,        # [loc-3] middleware-routed
    "executive-summary": True, # [loc-3] middleware-routed
    "dashboard": True,         # [loc-3] middleware-routed
    "life-arc": True,          # [loc-3] middleware-routed
    "practices-schedule": True, # [loc-3] middleware-routed
}

# [hi 2026-10-07] Hindi (Devanagari). Response-time translated surfaces are served in
# Hindi (the translator is script-gated). The SOURCE-GENERATED surfaces below have no
# translation pass and no native Hindi prompt, so they are served in English —
# explicitly (the gate logs it), never a silent Hinglish/English swap. Flip to True
# only after the surface is wired through the translator and read by a native speaker.
HI_READY = {
    "welcome": False,
    "weekly-briefing": False,
}

_DEFAULT = True


def gate_language(surface: str, language: str, default: bool = _DEFAULT) -> str:
    """Return the language this surface should actually serve.

    Normalizes locale codes (pt-BR -> pt), whitelists en/es/pt, and
    downgrades pt -> en when the surface is not PT-ready. es is never
    substituted for pt.
    """
    lang = (language or "en").strip().lower().replace("_", "-")
    if lang in ("hi-latn", "hinglish"):
        # Roman-script Hindi is not a translated language on any gated surface.
        # Explicit English (unchanged behaviour), never a guess at another language.
        return "en"
    lang = lang.split("-")[0]
    if lang not in ("en", "es", "pt", "fr", "hi"):
        return "en"
    _registry = {"pt": PT_READY, "fr": FR_READY, "hi": HI_READY}.get(lang)
    if _registry is not None and not _registry.get(surface, default):
        if lang == "hi":
            import logging
            logging.getLogger(__name__).warning(
                "[lang-gate] surface=%s requested=hi served=en (not Hindi-ready)", surface)
        return "en"
    return lang
