"""
antar_engine/places_composer.py
─────────────────────────────────────────────────────────────────────────────
PLACES — template-driven prose composer (Phase 1, NO LLM).

Turns the structured signals from places_concern into the user-facing strings:
primary_reason, secondary_reasons, watch_outs, texture_line, headline,
global_pattern, and the city-drill-down detail.

Every string is verdict-free (patterns and texture, never "move here" /
"don't move here") and carries no house numbers or Sanskrit.  Planet names are
allowed as actors (Path B).
"""

from __future__ import annotations

from typing import Optional

from antar_engine.places_templates import (
    PLACES_TEMPLATES, DOMAIN, AXIS, _GLOBAL, PLANET_NAME, LAYER_TEMPLATES,
)


def _lang(language: Optional[str]) -> str:
    l = (language or "en").lower().split("-")[0]
    return l if l in ("en", "es") else "en"


def _domain(concern: str, lang: str) -> str:
    return DOMAIN[lang].get(concern, concern)


def _axis(angle: str, lang: str) -> str:
    return AXIS[lang].get(angle, angle)


def _planet(planet: str, lang: str) -> str:
    return PLANET_NAME[lang].get(planet, planet)


# ─────────────────────────────────────────────────────────────────────────────
# Per-city pieces
# ─────────────────────────────────────────────────────────────────────────────

# [places-band-reconcile 2026-06-28] A city's `tier` is the aggregate verdict
# across ALL its signals; a single supportive line must never let the card read
# more positive than that band (the old plain_summary inversion, redux). Cap the
# reason tone to the tier: FLOW may speak fully supportive, MIXED downgrades a
# supportive line to a trade-off, STRAIN reframes it as friction. Override frames
# reuse the recognised "<planet>'s <angle> line crosses within <d>km, and it ..."
# opening so the /concern planet-removal scrub strips them identically.
_BAND_POL_RANK = {"supportive": 2, "mixed": 1, "friction": 0}
_BAND_TIER_CAP = {"FLOW": 2, "MIXED": 1, "STRAIN": 0}
_BAND_OVERRIDE_FRAMES = {
    "en": {
        "MIXED": ("{planet}'s {angle} line crosses within {distance}km, and it touches "
                  "{axis} here \u2014 but it reads as a mixed current for {domain}, the lift "
                  "coming with some drag."),
        "STRAIN": ("{planet}'s {angle} line crosses within {distance}km, and it touches "
                   "{axis} here \u2014 but the wider ground runs strained for {domain}, so the "
                   "support is real yet uneven, with friction more than ease."),
    },
    "es": {
        "MIXED": ("La l\u00ednea {angle} de {planet} cruza a menos de {distance}km y toca {axis} "
                  "aqu\u00ed \u2014 pero se lee como una corriente mixta para {domain}, el impulso "
                  "viene con algo de arrastre."),
        "STRAIN": ("La l\u00ednea {angle} de {planet} cruza a menos de {distance}km y toca {axis} "
                   "aqu\u00ed \u2014 pero el terreno general est\u00e1 tensionado para {domain}, as\u00ed "
                   "que el apoyo es real pero desigual, con m\u00e1s fricci\u00f3n que facilidad."),
    },
}


def _band_reconcile(signal, tier, lang, concern):
    """Return a tier-appropriate override string when the signal's own polarity
    is MORE positive than its computed tier allows; else None (use the normal
    polarity frame). Guarantees a STRAIN/MIXED card never emits "easier current"
    / "steady strength" prose that contradicts its badge."""
    if not signal or tier not in _BAND_TIER_CAP:
        return None
    pol = signal.get("polarity", "mixed")
    if _BAND_POL_RANK.get(pol, 1) <= _BAND_TIER_CAP[tier]:
        return None  # signal not more positive than the band -> no override
    frames = _BAND_OVERRIDE_FRAMES.get(lang) or _BAND_OVERRIDE_FRAMES["en"]
    frame = frames.get(tier)
    if not frame:
        return None
    return frame.format(
        planet=_planet(signal["planet"], lang),
        angle=signal["angle"],
        distance=int(round(signal.get("distance_km", 0))),
        axis=_axis(signal["angle"], lang),
        domain=_domain(concern, lang),
    )


def compose_primary_reason(concern: str, signal: Optional[dict], lang: str, tier: Optional[str] = None) -> str:
    lang = _lang(lang)
    if not signal:
        # No karaka line near — lead with a gentle, true neutral statement.
        if lang == "es":
            return (f"Ninguna línea karaka fuerte para {_domain(concern, lang)} "
                    f"cruza cerca; este lugar es de fondo neutro para ese tema.")
        return (f"No strong karaka line for {_domain(concern, lang)} crosses "
                f"close by; this place reads as neutral ground for that thread.")
    _override = _band_reconcile(signal, tier, lang, concern)
    if _override is not None:
        return _override
    frame = PLACES_TEMPLATES["primary_reasons"].get(
        (lang, concern, signal["angle"], signal["polarity"])
    )
    if not frame:
        frame = PLACES_TEMPLATES["primary_reasons"].get((lang, concern, signal["angle"], "mixed"))
    return frame.format(
        planet=_planet(signal["planet"], lang),
        angle=signal["angle"],
        distance=int(round(signal["distance_km"])),
        axis=_axis(signal["angle"], lang),
        domain=_domain(concern, lang),
    )


def compose_secondary_reasons(concern: str, signals: list[dict], lang: str, limit: int = 2, tier: Optional[str] = None) -> list[str]:
    lang = _lang(lang)
    out = []
    for sig in signals[:limit]:
        _ov = _band_reconcile(sig, tier, lang, concern)
        if _ov is not None:
            out.append(_ov)
            continue
        frame = PLACES_TEMPLATES["primary_reasons"].get(
            (lang, concern, sig["angle"], sig["polarity"])
        ) or PLACES_TEMPLATES["primary_reasons"].get((lang, concern, sig["angle"], "mixed"))
        out.append(frame.format(
            planet=_planet(sig["planet"], lang), angle=sig["angle"],
            distance=int(round(sig["distance_km"])),
            axis=_axis(sig["angle"], lang), domain=_domain(concern, lang),
        ))
    return out


def compose_watch_outs(concern: str, watch_list: list[dict], lang: str, limit: int = 2) -> list[str]:
    lang = _lang(lang)
    out = []
    seen = set()
    for w in watch_list:
        kind = w.get("kind")
        if kind == "hidden_cost_house":
            tkey = "endings_house" if w.get("house") == 8 else "hidden_cost_house"
        elif kind == "friction_line":
            tkey = "friction_line"
        else:
            continue
        dedup = (tkey, w.get("planet"))
        if dedup in seen:
            continue
        seen.add(dedup)
        frame = PLACES_TEMPLATES["watch_outs"].get((lang, tkey))
        if frame:
            out.append(frame.format(planet=_planet(w.get("planet"), lang), domain=_domain(concern, lang)))
        if len(out) >= limit:
            break
    return out


def compose_headline(concern: str, tier: str, city_name: str, lang: str) -> str:
    lang = _lang(lang)
    frame = PLACES_TEMPLATES["headlines"].get((lang, concern, tier)) \
        or PLACES_TEMPLATES["headlines"].get((lang, concern, "MIXED"))
    return frame.format(city=city_name, domain=_domain(concern, lang))


def compose_one_line(concern: str, tier: str, lang: str) -> str:
    lang = _lang(lang)
    return (LAYER_TEMPLATES["one_line"].get((lang, concern, tier))
            or LAYER_TEMPLATES["one_line"].get((lang, concern, "MIXED"), ""))


def compose_watch_single(concern: str, watch_list: list[dict], lang: str):
    """Most important watch-out as a single string, or None (never an array)."""
    outs = compose_watch_outs(concern, watch_list, lang, limit=1)
    return outs[0] if outs else None


def enrich_ranked_city(concern: str, scored: dict, lang: str) -> dict:
    """Attach composed strings to a scored city; drop underscore internals."""
    lang = _lang(lang)
    signals = scored.get("_signals", [])
    top = signals[0] if signals else None
    return {
        "city": scored["city"]["name"],
        "country": scored["city"].get("country"),
        "country_code": scored["city"].get("country_code"),
        "lat": scored["city"]["lat"],
        "lon": scored["city"]["lon"],
        "score": scored["score"],
        "tier": scored["tier"],
        "primary_reason": compose_primary_reason(concern, top, lang, tier=scored.get("tier")),
        "secondary_reasons": compose_secondary_reasons(concern, signals[1:], lang, tier=scored.get("tier")),
        "watch_outs": compose_watch_outs(concern, scored.get("_watch", []), lang),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Concern-level pieces
# ─────────────────────────────────────────────────────────────────────────────

def _dominant_tier(ranked: list[dict]) -> str:
    if not ranked:
        return "STRAIN"
    top = ranked[: min(3, len(ranked))]
    order = {"FLOW": 0, "MIXED": 1, "STRAIN": 2}
    # Tier of the strongest city drives the texture.
    return sorted(top, key=lambda c: -c.get("score", 0))[0].get("tier", "MIXED")


def compose_texture_line(concern: str, ranked: list[dict], lang: str) -> str:
    lang = _lang(lang)
    tier = _dominant_tier(ranked)
    frame = PLACES_TEMPLATES["texture_lines"].get((lang, concern, tier)) \
        or PLACES_TEMPLATES["texture_lines"].get((lang, concern, "MIXED"))
    return frame.format(domain=_domain(concern, lang))


def compose_global_pattern(concern: str, ranked: list[dict], lang: str) -> str:
    lang = _lang(lang)
    tier = _dominant_tier(ranked)
    frame = _GLOBAL[lang].get(tier, _GLOBAL[lang]["MIXED"])
    return frame.format(domain=_domain(concern, lang))


def compose_compare_summary(concern: str, enriched: list[dict], lang: str) -> str:
    """
    Verdict-free comparison line across 2-3 cities (already enriched + sorted
    by score desc).  Names the steadier current; never says 'move here'.
    """
    lang = _lang(lang)
    dom = _domain(concern, lang)
    if not enriched:
        return ""
    lead = enriched[0]
    if len(enriched) == 1:
        return lead.get("primary_reason", "")
    spread = lead["score"] - enriched[-1]["score"]
    if lang == "es":
        if spread <= 6:
            return (f"Para {dom}, estos lugares se sienten parecidos en fuerza — "
                    f"la diferencia está en el matiz, no en el grado.")
        return (f"Para {dom}, {lead['city']} lleva la corriente más estable del grupo; "
                f"{enriched[-1]['city']} pide más de ti por el mismo tema.")
    if spread <= 6:
        return (f"For {dom}, these places feel close in strength — the difference is "
                f"in flavour, not degree.")
    return (f"For {dom}, {lead['city']} carries the steadier current of the group; "
            f"{enriched[-1]['city']} asks more of you for the same thread.")


def compose_city_detail(concern: Optional[str], scored: dict, lang: str) -> str:
    """Detail paragraph for the /city drill-down (concern optional)."""
    lang = _lang(lang)
    signals = scored.get("_signals", [])
    top = signals[0] if signals else None
    if concern:
        parts = [compose_primary_reason(concern, top, lang)]
        parts += compose_secondary_reasons(concern, signals[1:], lang, limit=1)
        return " ".join(p for p in parts if p)

    # No concern — describe the dominant active line in plain terms.
    if not top:
        if lang == "es":
            return "Ningún eje planetario fuerte cruza cerca; este lugar es de textura tranquila para ti."
        return "No strong planetary axis crosses close by; this place reads as quiet-textured for you."
    if lang == "es":
        return (f"{_planet(top['planet'], lang)} corre por {_axis(top['angle'], lang)} a unos "
                f"{int(round(top['distance_km']))}km — es la corriente más marcada de este lugar.")
    return (f"{_planet(top['planet'], lang)} runs along {_axis(top['angle'], lang)} about "
            f"{int(round(top['distance_km']))}km away — it's the most defined current this place carries.")
