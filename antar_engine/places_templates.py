"""
antar_engine/places_templates.py
─────────────────────────────────────────────────────────────────────────────
PLACES — template bank (Phase 1, NO LLM).

Curated, verdict-free strings.  Planet names are allowed as actors (Path B /
source="curated_static").  NO house numbers, NO Sanskrit — houses are reframed
to life-domain language and angles to plain-English axes.

Coverage (materialised into PLACES_TEMPLATES at import):
    primary_reasons : 5 concerns x 4 angles x 3 polarities  = 60
    watch_outs      : per kind x concern                     ~ 30
    texture_lines   : 5 concerns x 3 tiers                   = 15
    headlines       : 5 concerns x 3 tiers                   = 15
"""

from __future__ import annotations

CONCERNS = ["career", "love", "rest", "wealth", "family"]
ANGLES = ["AC", "MC", "DC", "IC"]
POLARITIES = ["supportive", "mixed", "friction"]
TIERS = ["FLOW", "MIXED", "STRAIN"]

# ── Domain reframes (house numbers never surface) ───────────────────────────
DOMAIN = {
    "en": {
        "career": "your working life", "love": "your relating life",
        "rest": "your inner ground", "wealth": "your resources",
        "family": "your roots and home",
    },
    "es": {
        "career": "tu vida laboral", "love": "tu vida afectiva",
        "rest": "tu terreno interior", "wealth": "tus recursos",
        "family": "tus raíces y tu hogar",
    },
}

# ── Planet names as actors (Path B). Localised for display only. ────────────
PLANET_NAME = {
    "en": {"Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Mercury": "Mercury",
           "Jupiter": "Jupiter", "Venus": "Venus", "Saturn": "Saturn",
           "Rahu": "Rahu", "Ketu": "Ketu"},
    "es": {"Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio",
           "Jupiter": "Júpiter", "Venus": "Venus", "Saturn": "Saturno",
           "Rahu": "Rahu", "Ketu": "Ketu"},
}

# ── Angle reframes (plain axes, no jargon) ──────────────────────────────────
AXIS = {
    "en": {
        "MC": "the visible-work axis", "AC": "the way you arrive and are seen",
        "DC": "the partnership axis", "IC": "the home-and-foundations axis",
    },
    "es": {
        "MC": "el eje del trabajo visible", "AC": "la forma en que llegas y te ven",
        "DC": "el eje de la pareja", "IC": "el eje del hogar y los cimientos",
    },
}

# ── Sentence frames per polarity (filled with planet / axis / domain / dist) ─
_PRIMARY_FRAMES = {
    "en": {
        "supportive": "{planet}'s {angle} line crosses within {distance}km, and it pours steady strength into {axis} here — {domain} finds an easier current.",
        "mixed":      "{planet}'s {angle} line crosses within {distance}km. It touches {axis}, but the support is uneven — {domain} moves in fits and starts here.",
        "friction":   "{planet}'s {angle} line crosses within {distance}km, yet {planet} sits under strain in your chart — presence on {axis} here comes with visible friction in {domain}.",
    },
    "es": {
        "supportive": "La línea {angle} de {planet} cruza a menos de {distance}km y vierte fuerza constante en {axis} aquí — {domain} encuentra una corriente más fácil.",
        "mixed":      "La línea {angle} de {planet} cruza a menos de {distance}km. Toca {axis}, pero el apoyo es desigual — {domain} avanza a tramos aquí.",
        "friction":   "La línea {angle} de {planet} cruza a menos de {distance}km, pero {planet} está tensionado en tu carta — su presencia en {axis} trae fricción visible en {domain}.",
    },
}

# ── Watch-out frames ────────────────────────────────────────────────────────
_WATCH_FRAMES = {
    "en": {
        "friction_line": "{planet} runs close here while under strain in your chart — expect {domain} to ask for more patience than usual.",
        "hidden_cost_house": "{planet} settles into the hidden-cost ground of this place — energy can drain into things you don't see coming. Build slack into your timelines.",
        "endings_house": "{planet} falls into the endings-and-release ground here — cycles close faster than elsewhere; keep what matters portable.",
    },
    "es": {
        "friction_line": "{planet} pasa cerca aquí mientras está tensionado en tu carta — {domain} pedirá más paciencia de lo habitual.",
        "hidden_cost_house": "{planet} se asienta en el terreno de los costos ocultos de este lugar — la energía puede escaparse en lo que no ves venir. Deja margen en tus plazos.",
        "endings_house": "{planet} cae en el terreno de los cierres aquí — los ciclos terminan más rápido que en otros sitios; mantén lo importante portátil.",
    },
}

# ── Texture lines (one per concern x tier) ──────────────────────────────────
_TEXTURE = {
    "en": {
        ("career", "FLOW"):   "For {domain}, the map opens up — several places carry your working karakas on supportive ground.",
        ("career", "MIXED"):  "For {domain}, the map is workable but mixed — strength and friction sit close together across these places.",
        ("career", "STRAIN"): "For {domain}, the map asks for care — the strongest places still come with a pull you'll want to plan around.",
        ("love", "FLOW"):     "For {domain}, the relating lines fall warmly — a handful of places soften how you meet and are met.",
        ("love", "MIXED"):    "For {domain}, the relating lines are uneven — closeness and challenge share the same ground here.",
        ("love", "STRAIN"):   "For {domain}, the relating lines run tight — even the kinder places ask you to move slowly.",
        ("rest", "FLOW"):     "For {domain}, the foundation lines settle easily — these places let you exhale.",
        ("rest", "MIXED"):    "For {domain}, the foundation lines are mixed — quiet is available but not automatic across these places.",
        ("rest", "STRAIN"):   "For {domain}, true rest is harder to find on this map — the calmest places still hum underneath.",
        ("wealth", "FLOW"):   "For {domain}, the resource lines gather well — several places back the way value flows to you.",
        ("wealth", "MIXED"):  "For {domain}, the resource lines are mixed — growth is there, but it wants steadier hands in these places.",
        ("wealth", "STRAIN"): "For {domain}, the resource lines run thin — the better places reward patience over speed.",
        ("family", "FLOW"):   "For {domain}, the home-and-roots lines fall kindly — these places hold family close.",
        ("family", "MIXED"):  "For {domain}, the home-and-roots lines are mixed — belonging is available but takes tending here.",
        ("family", "STRAIN"): "For {domain}, the home-and-roots lines feel stretched — the warmest places still ask for effort.",
    },
    "es": {
        ("career", "FLOW"):   "Para {domain}, el mapa se abre — varios lugares llevan tus karakas laborales sobre terreno favorable.",
        ("career", "MIXED"):  "Para {domain}, el mapa es viable pero mixto — fuerza y fricción conviven en estos lugares.",
        ("career", "STRAIN"): "Para {domain}, el mapa pide cuidado — incluso los mejores lugares traen una tensión que conviene prever.",
        ("love", "FLOW"):     "Para {domain}, las líneas afectivas caen con calidez — algunos lugares suavizan cómo te encuentras con el otro.",
        ("love", "MIXED"):    "Para {domain}, las líneas afectivas son desiguales — cercanía y reto comparten el mismo terreno.",
        ("love", "STRAIN"):   "Para {domain}, las líneas afectivas van tensas — incluso los lugares más amables piden ir despacio.",
        ("rest", "FLOW"):     "Para {domain}, las líneas de base se asientan con facilidad — estos lugares te dejan respirar.",
        ("rest", "MIXED"):    "Para {domain}, las líneas de base son mixtas — la calma está disponible pero no es automática.",
        ("rest", "STRAIN"):   "Para {domain}, el verdadero descanso cuesta más en este mapa — incluso los lugares más calmos vibran por debajo.",
        ("wealth", "FLOW"):   "Para {domain}, las líneas de recursos se reúnen bien — varios lugares respaldan cómo fluye el valor hacia ti.",
        ("wealth", "MIXED"):  "Para {domain}, las líneas de recursos son mixtas — hay crecimiento, pero pide manos firmes.",
        ("wealth", "STRAIN"): "Para {domain}, las líneas de recursos van escasas — los mejores lugares premian la paciencia.",
        ("family", "FLOW"):   "Para {domain}, las líneas de hogar y raíces caen con amabilidad — estos lugares sostienen a la familia.",
        ("family", "MIXED"):  "Para {domain}, las líneas de hogar y raíces son mixtas — la pertenencia existe pero hay que cultivarla.",
        ("family", "STRAIN"): "Para {domain}, las líneas de hogar y raíces se sienten estiradas — los lugares más cálidos aún piden esfuerzo.",
    },
}

# ── Headlines (one per concern x tier) ──────────────────────────────────────
_HEADLINE = {
    "en": {
        ("career", "FLOW"):   "{city} carries {domain} on a steady current.",
        ("career", "MIXED"):  "{city} works for {domain}, with a few edges to plan around.",
        ("career", "STRAIN"): "{city} asks something of {domain} before it gives back.",
        ("love", "FLOW"):     "{city} softens how you meet others.",
        ("love", "MIXED"):    "{city} mixes closeness and challenge for {domain}.",
        ("love", "STRAIN"):   "{city} runs tight for {domain} — move slowly here.",
        ("rest", "FLOW"):     "{city} lets {domain} exhale.",
        ("rest", "MIXED"):    "{city} offers quiet to {domain}, but not automatically.",
        ("rest", "STRAIN"):   "{city} hums underneath {domain}'s calm.",
        ("wealth", "FLOW"):   "{city} backs the way value flows to you.",
        ("wealth", "MIXED"):  "{city} grows {domain} with steadier hands.",
        ("wealth", "STRAIN"): "{city} rewards patience over speed for {domain}.",
        ("family", "FLOW"):   "{city} holds {domain} close.",
        ("family", "MIXED"):  "{city} keeps {domain} workable, with tending.",
        ("family", "STRAIN"): "{city} stretches {domain} — warmth here takes effort.",
    },
    "es": {
        ("career", "FLOW"):   "{city} lleva {domain} sobre una corriente estable.",
        ("career", "MIXED"):  "{city} funciona para {domain}, con algunos bordes que prever.",
        ("career", "STRAIN"): "{city} le pide algo a {domain} antes de devolver.",
        ("love", "FLOW"):     "{city} suaviza cómo te encuentras con los demás.",
        ("love", "MIXED"):    "{city} mezcla cercanía y reto para {domain}.",
        ("love", "STRAIN"):   "{city} va tensa para {domain} — ve despacio aquí.",
        ("rest", "FLOW"):     "{city} deja respirar a {domain}.",
        ("rest", "MIXED"):    "{city} ofrece calma a {domain}, pero no sola.",
        ("rest", "STRAIN"):   "{city} vibra bajo la calma de {domain}.",
        ("wealth", "FLOW"):   "{city} respalda cómo fluye el valor hacia ti.",
        ("wealth", "MIXED"):  "{city} hace crecer {domain} con manos firmes.",
        ("wealth", "STRAIN"): "{city} premia la paciencia para {domain}.",
        ("family", "FLOW"):   "{city} sostiene {domain} de cerca.",
        ("family", "MIXED"):  "{city} mantiene {domain} viable, con cuidado.",
        ("family", "STRAIN"): "{city} estira {domain} — la calidez aquí cuesta.",
    },
}

# ── Global pattern (one per concern x tier) ─────────────────────────────────
_GLOBAL = {
    "en": {
        "FLOW":   "Your strongest ground for {domain} clusters where supportive karaka lines and friendly relocated houses meet.",
        "MIXED":  "Your map for {domain} is a patchwork — strength and friction trade places from region to region.",
        "STRAIN": "No place hands {domain} an easy ride; the differences here are about which trade-off suits you.",
    },
    "es": {
        "FLOW":   "Tu terreno más fuerte para {domain} se agrupa donde las líneas karaka favorables y las casas reubicadas amistosas se encuentran.",
        "MIXED":  "Tu mapa para {domain} es un mosaico — fuerza y fricción se alternan de región en región.",
        "STRAIN": "Ningún lugar le da a {domain} un camino fácil; aquí la diferencia está en qué compromiso te conviene.",
    },
}


def _materialise() -> dict:
    """Build the explicit PLACES_TEMPLATES dict the contract describes."""
    out = {"primary_reasons": {}, "watch_outs": {}, "texture_lines": {}, "headlines": {}}
    for lang in ("en", "es"):
        for concern in CONCERNS:
            for angle in ANGLES:
                for pol in POLARITIES:
                    out["primary_reasons"][(lang, concern, angle, pol)] = _PRIMARY_FRAMES[lang][pol]
            for tier in TIERS:
                out["texture_lines"][(lang, concern, tier)] = _TEXTURE[lang][(concern, tier)]
                out["headlines"][(lang, concern, tier)] = _HEADLINE[lang][(concern, tier)]
        for kind, frame in _WATCH_FRAMES[lang].items():
            out["watch_outs"][(lang, kind)] = frame
    return out


PLACES_TEMPLATES = _materialise()
