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

CONCERNS = ["money", "career", "love", "health", "peace", "family"]
ANGLES = ["AC", "MC", "DC", "IC"]
POLARITIES = ["supportive", "mixed", "friction"]
TIERS = ["FLOW", "MIXED", "STRAIN"]

# ── Domain reframes (house numbers never surface) ───────────────────────────
DOMAIN = {
    "en": {
        "money": "your resources", "career": "your working life",
        "love": "your relating life", "health": "your body and vitality",
        "peace": "your inner ground", "family": "your roots and home",
    },
    "es": {
        "money": "tus recursos", "career": "tu vida laboral",
        "love": "tu vida afectiva", "health": "tu cuerpo y vitalidad",
        "peace": "tu terreno interior", "family": "tus raíces y tu hogar",
    },
}

# ── City "signature" — WHAT each place is good for ──────────────────────────
# [places-signature 2026-07-12] The score alone never says what a place is FOR.
# Each city's strongest concern-line (planet + angle) names the specific energy
# it channels; these plain phrases render that as a "best for" chip + one line,
# WITHOUT emitting planet names (so the jargon scrub leaves them untouched).
# Short energy label per planet — the "what it channels" in a couple of words.
PLANET_ENERGY_SHORT = {
    "en": {
        "Sun": "leadership & visibility", "Moon": "emotional connection",
        "Mars": "drive & boldness", "Mercury": "skill & trade",
        "Jupiter": "growth & guidance", "Venus": "relationships & taste",
        "Saturn": "structure & discipline", "Rahu": "ambition & bold leaps",
        "Ketu": "focus & letting go",
    },
    "es": {
        "Sun": "liderazgo y visibilidad", "Moon": "conexión emocional",
        "Mars": "empuje y audacia", "Mercury": "habilidad y comercio",
        "Jupiter": "crecimiento y guía", "Venus": "vínculos y buen gusto",
        "Saturn": "estructura y disciplina", "Rahu": "ambición y saltos audaces",
        "Ketu": "enfoque y soltar",
    },
}
# The concern noun that fronts the "best for" chip: "<Concern> through <energy>".
CONCERN_NOUN = {
    "en": {"money": "Money", "career": "Career", "love": "Love",
           "health": "Health", "peace": "Peace", "family": "Family"},
    "es": {"money": "Dinero", "career": "Carrera", "love": "Amor",
           "health": "Salud", "peace": "Paz", "family": "Familia"},
}
# Short axis phrase — WHERE the energy plays out (compact form of AXIS).
AXIS_SHORT = {
    "en": {"MC": "your public work and standing", "AC": "how you show up day to day",
           "DC": "your partnerships and one-to-one deals", "IC": "your home and inner base"},
    "es": {"MC": "tu trabajo visible y tu reputación", "AC": "cómo te presentas cada día",
           "DC": "tus alianzas y tratos uno a uno", "IC": "tu hogar y tu base interior"},
}
# How the energy serves this specific concern — the closing clause of the line.
SIGNATURE_CHANNEL = {
    "en": {"money": "value tends to arrive this way",
           "career": "your work tends to rise this way",
           "love": "connection tends to come this way",
           "health": "vitality tends to steady this way",
           "peace": "calm tends to settle this way",
           "family": "roots tend to deepen this way"},
    "es": {"money": "el valor tiende a llegar por esta vía",
           "career": "tu trabajo tiende a crecer por esta vía",
           "love": "la conexión tiende a llegar por esta vía",
           "health": "la vitalidad tiende a estabilizarse por esta vía",
           "peace": "la calma tiende a asentarse por esta vía",
           "family": "las raíces tienden a profundizar por esta vía"},
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
# [places-jargon 2026-07-12] Plain axis reframes. The old values leaked the
# technical word "axis" (e.g. "the visible-work axis", "the partnership axis")
# into user-facing reason lines — inconsistent with AC ("the way you arrive and
# are seen"). Now fully plain, no "axis"/"eje".
AXIS = {
    "en": {
        "MC": "your public standing and visible work", "AC": "the way you arrive and are seen",
        "DC": "your partnerships and close one-to-one ties", "IC": "your home and foundations",
    },
    "es": {
        "MC": "tu reputación y tu trabajo visible", "AC": "la forma en que llegas y te ven",
        "DC": "tus alianzas y tus vínculos cercanos", "IC": "tu hogar y tus cimientos",
    },
}

# ── Sentence frames per polarity (filled with planet / axis / domain / dist) ─
_PRIMARY_FRAMES = {
    "en": {
        "supportive": "{planet}'s pull is strong in this place, pouring steady strength into {axis} — {domain} finds an easier current here.",
        "mixed":      "{planet}'s pull reaches this place and touches {axis}, but the support is uneven — {domain} moves in fits and starts here.",
        "friction":   "{planet}'s pull reaches this place, yet {planet} is under strain for you — showing up on {axis} here comes with visible friction in {domain}.",
    },
    "es": {
        "supportive": "La fuerza de {planet} llega con claridad a este lugar y vierte apoyo constante en {axis} — {domain} encuentra una corriente más fácil aquí.",
        "mixed":      "La fuerza de {planet} llega a este lugar y toca {axis}, pero el apoyo es desigual — {domain} avanza a tramos aquí.",
        "friction":   "La fuerza de {planet} llega a este lugar, pero {planet} está bajo tensión para ti — su presencia en {axis} trae fricción visible en {domain}.",
    },
}

# ── Watch-out frames ────────────────────────────────────────────────────────
_WATCH_FRAMES = {
    "en": {
        "friction_line": "{planet} runs close here while under strain for you — expect {domain} to ask for more patience than usual.",
        "hidden_cost_house": "{planet} settles into the hidden-cost ground of this place — energy can drain into things you don't see coming. Build slack into your timelines.",
        "endings_house": "{planet} falls into the endings-and-release ground here — cycles close faster than elsewhere; keep what matters portable.",
    },
    "es": {
        "friction_line": "{planet} pasa cerca aquí mientras está bajo tensión para ti — {domain} pedirá más paciencia de lo habitual.",
        "hidden_cost_house": "{planet} se asienta en el terreno de los costos ocultos de este lugar — la energía puede escaparse en lo que no ves venir. Deja margen en tus plazos.",
        "endings_house": "{planet} cae en el terreno de los cierres aquí — los ciclos terminan más rápido que en otros sitios; mantén lo importante portátil.",
    },
}

# ── Texture lines (one per concern x tier) ──────────────────────────────────
_TEXTURE = {
    "en": {
        ("career", "FLOW"):   "For {domain}, the map opens up — several places carry your working strengths on supportive ground.",
        ("career", "MIXED"):  "For {domain}, the map is workable but mixed — strength and friction sit close together across these places.",
        ("career", "STRAIN"): "For {domain}, the map asks for care — the strongest places still come with a pull you'll want to plan around.",
        ("love", "FLOW"):     "For {domain}, the relating lines fall warmly — a handful of places soften how you meet and are met.",
        ("love", "MIXED"):    "For {domain}, the relating lines are uneven — closeness and challenge share the same ground here.",
        ("love", "STRAIN"):   "For {domain}, the relating lines run tight — even the kinder places ask you to move slowly.",
        ("peace", "FLOW"):     "For {domain}, the foundation lines settle easily — these places let you exhale.",
        ("peace", "MIXED"):    "For {domain}, the foundation lines are mixed — quiet is available but not automatic across these places.",
        ("peace", "STRAIN"):   "For {domain}, true rest is harder to find on this map — the calmest places still hum underneath.",
        ("money", "FLOW"):   "For {domain}, the resource lines gather well — several places back the way value flows to you.",
        ("money", "MIXED"):  "For {domain}, the resource lines are mixed — growth is there, but it wants steadier hands in these places.",
        ("money", "STRAIN"): "For {domain}, the resource lines run thin — the better places reward patience over speed.",
        ("family", "FLOW"):   "For {domain}, the home-and-roots lines fall kindly — these places hold family close.",
        ("family", "MIXED"):  "For {domain}, the home-and-roots lines are mixed — belonging is available but takes tending here.",
        ("family", "STRAIN"): "For {domain}, the home-and-roots lines feel stretched — the warmest places still ask for effort.",
        ("health", "FLOW"):   "For {domain}, the supportive lines settle well — several places help the body find an easy, restorative rhythm.",
        ("health", "MIXED"):  "For {domain}, the lines are mixed — recovery is possible but the body wants steadier pacing here.",
        ("health", "STRAIN"): "For {domain}, the lines run tight — even the calmer places ask you to protect your energy.",
    },
    "es": {
        ("career", "FLOW"):   "Para {domain}, el mapa se abre — varios lugares llevan tus fuerzas laborales sobre terreno favorable.",
        ("career", "MIXED"):  "Para {domain}, el mapa es viable pero mixto — fuerza y fricción conviven en estos lugares.",
        ("career", "STRAIN"): "Para {domain}, el mapa pide cuidado — incluso los mejores lugares traen una tensión que conviene prever.",
        ("love", "FLOW"):     "Para {domain}, las líneas afectivas caen con calidez — algunos lugares suavizan cómo te encuentras con el otro.",
        ("love", "MIXED"):    "Para {domain}, las líneas afectivas son desiguales — cercanía y reto comparten el mismo terreno.",
        ("love", "STRAIN"):   "Para {domain}, las líneas afectivas van tensas — incluso los lugares más amables piden ir despacio.",
        ("peace", "FLOW"):     "Para {domain}, las líneas de base se asientan con facilidad — estos lugares te dejan respirar.",
        ("peace", "MIXED"):    "Para {domain}, las líneas de base son mixtas — la calma está disponible pero no es automática.",
        ("peace", "STRAIN"):   "Para {domain}, el verdadero descanso cuesta más en este mapa — incluso los lugares más calmos vibran por debajo.",
        ("money", "FLOW"):   "Para {domain}, las líneas de recursos se reúnen bien — varios lugares respaldan cómo fluye el valor hacia ti.",
        ("money", "MIXED"):  "Para {domain}, las líneas de recursos son mixtas — hay crecimiento, pero pide manos firmes.",
        ("money", "STRAIN"): "Para {domain}, las líneas de recursos van escasas — los mejores lugares premian la paciencia.",
        ("family", "FLOW"):   "Para {domain}, las líneas de hogar y raíces caen con amabilidad — estos lugares sostienen a la familia.",
        ("family", "MIXED"):  "Para {domain}, las líneas de hogar y raíces son mixtas — la pertenencia existe pero hay que cultivarla.",
        ("family", "STRAIN"): "Para {domain}, las líneas de hogar y raíces se sienten estiradas — los lugares más cálidos aún piden esfuerzo.",
        ("health", "FLOW"):   "Para {domain}, las líneas favorables se asientan bien — varios lugares ayudan al cuerpo a encontrar un ritmo reparador.",
        ("health", "MIXED"):  "Para {domain}, las líneas son mixtas — la recuperación es posible pero el cuerpo pide un ritmo más estable.",
        ("health", "STRAIN"): "Para {domain}, las líneas van tensas — incluso los lugares más calmos piden cuidar tu energía.",
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
        ("peace", "FLOW"):     "{city} lets {domain} exhale.",
        ("peace", "MIXED"):    "{city} offers quiet to {domain}, but not automatically.",
        ("peace", "STRAIN"):   "{city} hums underneath {domain}'s calm.",
        ("money", "FLOW"):   "{city} backs the way value flows to you.",
        ("money", "MIXED"):  "{city} grows {domain} with steadier hands.",
        ("money", "STRAIN"): "{city} rewards patience over speed for {domain}.",
        ("family", "FLOW"):   "{city} holds {domain} close.",
        ("family", "MIXED"):  "{city} keeps {domain} workable, with tending.",
        ("family", "STRAIN"): "{city} stretches {domain} — warmth here takes effort.",
        ("health", "FLOW"):   "{city} helps {domain} find a restorative rhythm.",
        ("health", "MIXED"):  "{city} supports {domain}, with steadier pacing.",
        ("health", "STRAIN"): "{city} asks you to protect {domain} here.",
    },
    "es": {
        ("career", "FLOW"):   "{city} lleva {domain} sobre una corriente estable.",
        ("career", "MIXED"):  "{city} funciona para {domain}, con algunos bordes que prever.",
        ("career", "STRAIN"): "{city} le pide algo a {domain} antes de devolver.",
        ("love", "FLOW"):     "{city} suaviza cómo te encuentras con los demás.",
        ("love", "MIXED"):    "{city} mezcla cercanía y reto para {domain}.",
        ("love", "STRAIN"):   "{city} va tensa para {domain} — ve despacio aquí.",
        ("peace", "FLOW"):     "{city} deja respirar a {domain}.",
        ("peace", "MIXED"):    "{city} ofrece calma a {domain}, pero no sola.",
        ("peace", "STRAIN"):   "{city} vibra bajo la calma de {domain}.",
        ("money", "FLOW"):   "{city} respalda cómo fluye el valor hacia ti.",
        ("money", "MIXED"):  "{city} hace crecer {domain} con manos firmes.",
        ("money", "STRAIN"): "{city} premia la paciencia para {domain}.",
        ("family", "FLOW"):   "{city} sostiene {domain} de cerca.",
        ("family", "MIXED"):  "{city} mantiene {domain} viable, con cuidado.",
        ("family", "STRAIN"): "{city} estira {domain} — la calidez aquí cuesta.",
        ("health", "FLOW"):   "{city} ayuda a {domain} a encontrar un ritmo reparador.",
        ("health", "MIXED"):  "{city} apoya {domain}, con un ritmo más estable.",
        ("health", "STRAIN"): "{city} pide cuidar {domain} aquí.",
    },
}

# ── Global pattern (one per concern x tier) ─────────────────────────────────
_GLOBAL = {
    "en": {
        "FLOW":   "Your strongest ground for {domain} clusters where your key supports and friendly local conditions meet.",
        "MIXED":  "Your map for {domain} is a patchwork — strength and friction trade places from region to region.",
        "STRAIN": "No place hands {domain} an easy ride; the differences here are about which trade-off suits you.",
    },
    "es": {
        "FLOW":   "Tu terreno más fuerte para {domain} se agrupa donde tus apoyos clave y las condiciones locales amistosas se encuentran.",
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


# ═════════════════════════════════════════════════════════════════════════════
# Phase 3 — 4-layer reasoning (NATAL / DASHA / AGE / INTENT) template banks
# ═════════════════════════════════════════════════════════════════════════════

CONDITIONS = ["exalted", "own_sign", "friend", "neutral", "enemy",
              "debilitated", "combust", "sleeping"]

# NATAL — keyed by condition; {planet},{domain},{placed} interpolated.
_NATAL_FRAMES = {
    "en": {
        "exalted":     "Your {planet} — at its strongest in you — is one of your real strengths for {domain}{placed}.",
        "own_sign":    "Your {planet} — on solid home ground in you — gives {domain} dependable footing here{placed}.",
        "friend":      "Your {planet} sits in friendly territory, lending quiet support to {domain} here{placed}.",
        "neutral":     "Your {planet} is steady but unremarkable for {domain} here — neither lift nor drag{placed}.",
        "enemy":       "Your {planet} works against some resistance for {domain} here — it delivers, but it costs{placed}.",
        "debilitated": "Your {planet} is a weak spot for you, so {domain} in a place like this asks more of you than it returns{placed}.",
        "combust":     "Your {planet} is easily overshadowed in you — its voice for {domain} can get drowned out here{placed}.",
        "sleeping":    "Your {planet} is dormant for you — {domain} here needs you to wake it deliberately{placed}.",
    },
    "es": {
        "exalted":     "Tu {planet} — en su punto más fuerte en ti — es una de tus verdaderas fortalezas para {domain}{placed}.",
        "own_sign":    "Tu {planet} — sobre terreno propio y firme en ti — le da a {domain} un apoyo confiable aquí{placed}.",
        "friend":      "Tu {planet} está en territorio amigo, dando apoyo silencioso a {domain} aquí{placed}.",
        "neutral":     "Tu {planet} es estable pero discreto para {domain} aquí — ni impulso ni lastre{placed}.",
        "enemy":       "Tu {planet} trabaja con cierta resistencia para {domain} aquí — cumple, pero cuesta{placed}.",
        "debilitated": "Tu {planet} es un punto débil para ti, así que {domain} en un lugar así te pide más de lo que devuelve{placed}.",
        "combust":     "Tu {planet} se eclipsa con facilidad en ti — su voz para {domain} puede ahogarse aquí{placed}.",
        "sleeping":    "Tu {planet} está dormido para ti — {domain} aquí necesita que lo despiertes deliberadamente{placed}.",
    },
}

# Relocated-house clause ("placed") appended when the karaka lands in a
# concern-relevant house at this relocation. No house numbers — domain words.
_PLACED_CLAUSE = {
    "en": ", and this place puts it front and centre",
    "es": ", y este lugar lo pone en primer plano",
}

# DASHA — kind ∈ current | upcoming | building | neutral; {planet} interpolated.
_DASHA_FRAMES = {
    "en": {
        "current":  "Your {planet} period is live, and this place puts it front and centre — the chapter you're in takes visible form here.",
        "upcoming": "{planet} opens the long chapter you're about to enter, and this place gives that next chapter its visible form — you'd be arriving early to your own future.",
        "building": "{planet} is on your horizon, and this place is tuned to the chapter building toward you rather than the one you're leaving.",
        "neutral":  "The timing here is quiet — nothing about this place amplifies your current chapter, so it works on your baseline strengths alone.",
    },
    "es": {
        "current":  "Tu periodo de {planet} está activo, y este lugar lo pone en primer plano — el capítulo en el que estás toma aquí forma visible.",
        "upcoming": "{planet} abre el largo capítulo en el que estás a punto de entrar, y este lugar le da forma visible a ese próximo capítulo — llegarías temprano a tu propio futuro.",
        "building": "{planet} está en tu horizonte, y este lugar está afinado al capítulo que se acerca, no al que dejas.",
        "neutral":  "El momento aquí es tranquilo — nada de este lugar amplifica tu capítulo actual, así que funciona por tus fuerzas de base.",
    },
}

# AGE — match_kind ∈ match | mismatch | quiet | neutral; {chapter},{city}.
_AGE_FRAMES = {
    "en": {
        "match":    "The pace of {city} aligns with the {chapter} phase you're in — the city's rhythm matches your chapter's rhythm.",
        "mismatch": "{city} runs at sprint pace, but you're in the {chapter} phase — the place pushes faster than your chapter wants.",
        "quiet":    "{city} offers quiet compounding — a gentle fit for the {chapter} phase you're in.",
        "neutral":  "{city}'s tempo neither helps nor fights the {chapter} phase you're in.",
    },
    "es": {
        "match":    "El ritmo de {city} encaja con la fase de {chapter} en la que estás — el pulso de la ciudad coincide con el de tu capítulo.",
        "mismatch": "{city} va a ritmo de sprint, pero estás en la fase de {chapter} — el lugar empuja más rápido de lo que tu capítulo quiere.",
        "quiet":    "{city} ofrece una capitalización tranquila — un encaje suave para la fase de {chapter} en la que estás.",
        "neutral":  "El tempo de {city} ni ayuda ni pelea con la fase de {chapter} en la que estás.",
    },
}

# ONE-LINE headline per concern x tier.
_ONE_LINE = {
    "en": {
        ("career", "FLOW"):   "Where your strongest working planet meets the rhythm of the place.",
        ("career", "MIXED"):  "A working fit with edges worth knowing.",
        ("career", "STRAIN"): "A place that asks before it gives, for your working life.",
        ("love", "FLOW"):     "Where your relating planets are met, not tested.",
        ("love", "MIXED"):    "Closeness and challenge in the same air.",
        ("love", "STRAIN"):   "A place that asks your relating life to slow down.",
        ("peace", "FLOW"):     "Where your inner ground finally exhales.",
        ("peace", "MIXED"):    "Quiet is here, but not automatic.",
        ("peace", "STRAIN"):   "Calm you'd have to build, not find.",
        ("money", "FLOW"):   "Where the way value flows to you is backed.",
        ("money", "MIXED"):  "Growth that wants steadier hands.",
        ("money", "STRAIN"): "Resources that reward patience over speed.",
        ("family", "FLOW"):   "Where roots and home are held close.",
        ("family", "MIXED"):  "Belonging that takes some tending.",
        ("family", "STRAIN"): "Warmth that here takes real effort.",
        ("health", "FLOW"):   "Where the body finds an easy, restorative rhythm.",
        ("health", "MIXED"):  "Recovery is here, but the body wants steadier pacing.",
        ("health", "STRAIN"): "Vitality you'd have to protect, not assume.",
    },
    "es": {
        ("career", "FLOW"):   "Donde tu planeta laboral más fuerte se encuentra con el ritmo del lugar.",
        ("career", "MIXED"):  "Un encaje laboral con bordes que conviene conocer.",
        ("career", "STRAIN"): "Un lugar que pide antes de dar, para tu vida laboral.",
        ("love", "FLOW"):     "Donde tus planetas afectivos son recibidos, no probados.",
        ("love", "MIXED"):    "Cercanía y reto en el mismo aire.",
        ("love", "STRAIN"):   "Un lugar que le pide a tu vida afectiva ir más despacio.",
        ("peace", "FLOW"):     "Donde tu terreno interior por fin respira.",
        ("peace", "MIXED"):    "Hay calma, pero no automática.",
        ("peace", "STRAIN"):   "Una calma que tendrías que construir, no encontrar.",
        ("money", "FLOW"):   "Donde se respalda la forma en que el valor fluye hacia ti.",
        ("money", "MIXED"):  "Un crecimiento que pide manos más firmes.",
        ("money", "STRAIN"): "Recursos que premian la paciencia sobre la velocidad.",
        ("family", "FLOW"):   "Donde las raíces y el hogar se sostienen de cerca.",
        ("family", "MIXED"):  "Una pertenencia que requiere cuidado.",
        ("family", "STRAIN"): "Una calidez que aquí cuesta esfuerzo real.",
        ("health", "FLOW"):   "Donde el cuerpo encuentra un ritmo reparador.",
        ("health", "MIXED"):  "Hay recuperación, pero el cuerpo pide un ritmo más estable.",
        ("health", "STRAIN"): "Una vitalidad que tendrías que proteger, no dar por hecha.",
    },
}


def _materialise_layers() -> dict:
    out = {"natal": {}, "dasha": {}, "age": {}, "one_line": {}}
    for lang in ("en", "es"):
        for concern in CONCERNS:
            for cond in CONDITIONS:
                out["natal"][(lang, concern, cond)] = _NATAL_FRAMES[lang][cond]
            for kind in ("current", "upcoming", "building", "neutral"):
                out["dasha"][(lang, concern, kind)] = _DASHA_FRAMES[lang][kind]
            for tier in TIERS:
                out["one_line"][(lang, concern, tier)] = _ONE_LINE[lang][(concern, tier)]
        for mk in ("match", "mismatch", "quiet", "neutral"):
            out["age"][(lang, mk)] = _AGE_FRAMES[lang][mk]
    return out


LAYER_TEMPLATES = _materialise_layers()
