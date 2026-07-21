# -*- coding: utf-8 -*-
"""Spanish localization for the deterministic remedial layer of the day card.

[remedial-es 2026-07-20] The daily-week engine composes the colour / food /
timing block from templated English (color_therapy, ayurveda_astrology,
moon_transit). The LLM prose is translated by _translate_daily_signals_es, but
that block never was, so a Spanish user (Jonatan, CO) saw "Wear Red/Coral · eat
warm, hearty food" in English on an otherwise-Spanish card.

This module rebuilds ONLY the fields the day card renders, in Spanish, driven by
the STRUCTURED fields already in the payload (planet, mode, duration_days) plus
exact-match phrase maps for the composed reasons. It never fuzzy-parses free
text: every English source here is a bounded template output, so an exact-match
miss falls back to the English string rather than mistranslating. Deterministic,
no LLM, no per-serve cost — consistent with how es is done elsewhere.

Entry point: localize_remedial_es(day) mutates day['color'/'food'/'moon_shift'].
"""
from typing import Any, Dict, Optional

# ── planets ──────────────────────────────────────────────────────────────
# Subject form (sentence-initial), for "{Planet} lleva el día…".
_PLANET_SUBJECT = {
    "Sun": "El Sol", "Moon": "La Luna", "Mars": "Marte", "Mercury": "Mercurio",
    "Jupiter": "Júpiter", "Venus": "Venus", "Saturn": "Saturno",
    "Rahu": "Rahu", "Ketu": "Ketu",
}

# ── colour names ─────────────────────────────────────────────────────────
_COLOR = {
    "Red/Coral": "Rojo/Coral",
    "White/Silver/Pearl": "Blanco/Plata/Perla",
    "White/Pink/Sky Blue": "Blanco/Rosa/Azul cielo",
    "Orange/Gold/Saffron": "Naranja/Oro/Azafrán",
    "Yellow/Gold": "Amarillo/Oro",
    "Green/Emerald": "Verde/Esmeralda",
    "Black/Dark Blue/Purple": "Negro/Azul oscuro/Púrpura",
    "Smoky Grey/Deep Blue": "Gris humo/Azul profundo",
    "Brown/Earth/Multicolour": "Marrón/Tierra/Multicolor",
}

# ── why_wear: "activates {area} — {outcome}"  /  "supports {enhances}" ────
# Exact-match maps keyed on the English template pieces (from _HOUSE_AREA /
# graha_effect), so the rebuild is deterministic.
_AREA = {
    "presence and health": "presencia y salud",
    "money and family": "dinero y familia",
    "communication and initiative": "comunicación e iniciativa",
    "home and peace of mind": "hogar y paz mental",
    "creativity and children": "creatividad e hijos",
    "competition and routine": "competencia y rutina",
    "partners and clients": "socios y clientes",
    "shared money and change": "dinero compartido y cambio",
    "luck, mentors and travel": "suerte, mentores y viajes",
    "career and visibility": "carrera y visibilidad",
    "income and networks": "ingresos y contactos",
    "rest and letting go": "descanso y soltar",
}
_OUTCOME = {
    "you should come across the way you intend today":
        "hoy deberías proyectarte tal como pretendes",
    "money and family matters should sit easier today":
        "los asuntos de dinero y familia deberían fluir mejor hoy",
    "speaking up and reaching out should land well today":
        "hablar y tender puentes debería salir bien hoy",
    "home and headspace should feel settled today":
        "el hogar y la mente deberían sentirse asentados hoy",
    "creative work and matters with children go smoothly":
        "el trabajo creativo y los asuntos con los hijos fluyen",
    "you should hold your ground in anything contested":
        "deberías mantener tu terreno en cualquier disputa",
    "one-to-one dealings should go smoothly today":
        "los tratos uno a uno deberían fluir hoy",
    "shared money and anything mid-transition move your way":
        "el dinero compartido y lo que está en transición se mueve a tu favor",
    "advice and openings should come more easily today":
        "los consejos y las oportunidades deberían llegar con más facilidad hoy",
    "work matters should move smoothly today":
        "los asuntos de trabajo deberían avanzar con fluidez hoy",
    "income and the people around you work in your favour":
        "los ingresos y la gente a tu alrededor juegan a tu favor",
    "stepping back should cost you less than usual":
        "dar un paso atrás debería costarte menos de lo habitual",
}
# graha_effect: enhances (for "supports {enhances}") and risk (for why_soften)
_ENHANCES = {
    "authority and being seen clearly": "autoridad y ser visto con claridad",
    "emotional steadiness and reading people well":
        "estabilidad emocional y leer bien a la gente",
    "decisiveness and physical drive": "decisión e impulso físico",
    "clear speech and quick analysis": "habla clara y análisis ágil",
    "judgement, generosity and the long view":
        "juicio, generosidad y visión de largo plazo",
    "rapport, taste and easy negotiation":
        "sintonía, gusto y negociación fácil",
    "patience, structure and staying power":
        "paciencia, estructura y aguante",
    "unconventional moves and visibility":
        "movidas poco convencionales y visibilidad",
    "focus and depth of research":
        "concentración y profundidad de investigación",
}
_RISK = {
    "ego hardening into a stand-off with someone senior":
        "que el ego se endurezca en un pulso con alguien de rango",
    "moods swinging faster than the situation warrants":
        "que los estados de ánimo oscilen más rápido de lo que la situación amerita",
    "speed turning into conflict you cannot walk back":
        "que la velocidad se convierta en un conflicto del que no puedas volver",
    "words landing sharper than you meant them":
        "que las palabras salgan más filosas de lo que pretendías",
    "over-promising, or expanding past what you can hold":
        "prometer de más o expandirte más allá de lo que puedes sostener",
    "smoothing over a hard truth that needed saying":
        "suavizar una verdad dura que hacía falta decir",
    "heaviness hardening into delay or isolation":
        "que la pesadez se endurezca en demora o aislamiento",
    "overreach, or a shortcut that costs more later":
        "excederte, o un atajo que cuesta más después",
    "withdrawing so far you miss a signal that mattered":
        "retirarte tanto que se te escape una señal importante",
}

# ── food: why_eat rebuilt from planet + mode ─────────────────────────────
_GRAHA_FEEDS = {
    "Sun": "vitalidad y confianza",
    "Moon": "calma y estabilidad emocional",
    "Mars": "empuje y resistencia",
    "Mercury": "agilidad mental",
    "Jupiter": "serenidad y buen juicio",
    "Venus": "soltura y calidez",
    "Saturn": "aguante y paciencia",
    "Rahu": "concentración para lo poco convencional",
    "Ketu": "profundidad y concentración",
}
# balance mode: "{Planet} {tendency}, {correction}", keyed by dosha
_DOSHA_MECHANISM = {
    "Pitta": ("se calienta hoy", "así que come fresco y baja el picante"),
    "Vata": ("se vuelve seco e inquieto hoy",
             "así que comida tibia, aceitosa y que asiente lo estabiliza"),
    "Kapha": ("se vuelve pesado hoy", "así que mantenlo ligero y tibio"),
    "Kapha/Vata": ("oscila entre pesado e inquieto hoy",
                   "así que comidas tibias, simples y regulares"),
    "Vata/Pitta": ("se vuelve inquieto y caliente hoy",
                   "así que mantén horarios de comida estables y modera el picante"),
    "Pitta/Vata": ("se vuelve caliente y disperso hoy",
                   "así que come fresco pero que asiente"),
}
# planet -> dosha. Import the canonical map rather than mirror it (Venus is
# Kapha/Vata, not Kapha — a hand-copy silently drifts). No circular import:
# ayurveda_astrology does not import this module.
try:
    from antar_engine.ayurveda_astrology import PLANET_DOSHA as _PD_SRC
    _PLANET_DOSHA = {p: (v or {}).get("dosha", "") for p, v in _PD_SRC.items()}
except Exception:  # pragma: no cover - defensive
    _PLANET_DOSHA = {}
_GRAHA_TEXTURE = {
    "Sun": "tibia", "Moon": "fresca", "Mars": "tibia y sustanciosa",
    "Mercury": "fresca y ligera", "Jupiter": "tibia y nutritiva",
    "Venus": "dulce y rica", "Saturn": "tibia y que asienta",
    "Rahu": "que asienta", "Ketu": "ligera y simple",
}
_DOSHA_TEXTURE = {
    "Vata": "tibia y que asienta", "Kapha": "ligera y tibia",
    "Kapha/Vata": "tibia y simple", "Vata/Pitta": "estable y suave",
    "Pitta/Vata": "fresca y que asienta",
}

# ── food ingredient names ────────────────────────────────────────────────
_FOOD = {
    "Alcohol": "Alcohol",
    "All green vegetables": "Todas las verduras verdes",
    "Almonds and walnuts": "Almendras y nueces",
    "Almonds soaked overnight": "Almendras remojadas de un día para otro",
    "Amla": "Amla",
    "Artificial sweeteners": "Edulcorantes artificiales",
    "Ashwagandha": "Ashwagandha",
    "Barley": "Cebada",
    "Beetroot": "Remolacha",
    "Bitter gourd juice": "Jugo de melón amargo",
    "Black pepper in everything": "Pimienta negra en todo",
    "Black sesame": "Sésamo negro",
    "Black urad dal": "Urad dal negro",
    "Blue/purple foods": "Alimentos azules/morados",
    "Brahmi ghee": "Ghee de brahmi",
    "Buttermilk with cumin": "Suero de leche con comino",
    "Cardamom in your morning drink": "Cardamomo en tu bebida de la mañana",
    "Chamomile or brahmi tea before sleep": "Té de manzanilla o brahmi antes de dormir",
    "Chickpeas": "Garbanzos",
    "Coconut": "Coco",
    "Coconut in any form": "Coco en cualquier forma",
    "Cold and dry foods": "Alimentos fríos y secos",
    "Cold beverages": "Bebidas frías",
    "Coriander chutney": "Chutney de cilantro",
    "Coriander seeds in food": "Semillas de cilantro en la comida",
    "Cow's milk": "Leche de vaca",
    "Cucumber and coconut": "Pepino y coco",
    "Dark leafy greens": "Verduras de hoja verde oscura",
    "Dates and figs": "Dátiles e higos",
    "Eating after 8pm": "Comer después de las 8 de la noche",
    "Eating alone in darkness": "Comer solo a oscuras",
    "Eating non-vegetarian at night": "Comer carne por la noche",
    "Eating with electronic screens": "Comer frente a pantallas",
    "Excess alcohol": "Exceso de alcohol",
    "Excess meat": "Exceso de carne",
    "Excess spicy food": "Exceso de comida picante",
    "Excess sweets": "Exceso de dulces",
    "Excess talking while eating": "Hablar en exceso mientras comes",
    "Fennel and cumin water": "Agua de hinojo y comino",
    "Fennel seeds": "Semillas de hinojo",
    "Fennel seeds after meals": "Semillas de hinojo después de comer",
    "Fried foods": "Frituras",
    "Garlic and onion": "Ajo y cebolla",
    "Ghee": "Ghee",
    "Ginger in every meal": "Jengibre en cada comida",
    "Green apples": "Manzanas verdes",
    "Green cardamom in chai": "Cardamomo verde en el chai",
    "Green moong dal": "Moong dal verde",
    "Gulkand": "Gulkand",
    "Horse gram": "Kulthi (grano de caballo)",
    "Inconsistent meal times": "Horarios de comida irregulares",
    "Iron-rich foods": "Alimentos ricos en hierro",
    "Jaggery instead of white sugar": "Panela en lugar de azúcar blanca",
    "Kheer on Monday evenings": "Kheer las noches de lunes",
    "Leftover and stale food": "Sobras y comida rancia",
    "Lotus seeds": "Semillas de loto",
    "Mint chutney with meals": "Chutney de menta con las comidas",
    "Mishri instead of sugar": "Mishri en lugar de azúcar",
    "Moonflower honey": "Miel de flor de luna",
    "Neem juice or neem in food": "Jugo de neem o neem en la comida",
    "Non-vegetarian food": "Comida no vegetariana",
    "Onion and garlic": "Cebolla y ajo",
    "Orange and yellow foods": "Alimentos naranjas y amarillos",
    "Overeating": "Comer en exceso",
    "Overly stimulating foods": "Alimentos demasiado estimulantes",
    "Pearl millet rotis": "Rotis de mijo perla",
    "Pomegranate": "Granada",
    "Processed and artificial food": "Comida procesada y artificial",
    "Processed and junk food": "Comida procesada y chatarra",
    "Processed salt": "Sal procesada",
    "Red lentils": "Lentejas rojas",
    "Red rice or red quinoa": "Arroz rojo o quinua roja",
    "Rice with ghee": "Arroz con ghee",
    "Root vegetables": "Verduras de raíz",
    "Rose petal jam": "Mermelada de pétalos de rosa",
    "Rose water in drinks and cooking": "Agua de rosas en bebidas y cocina",
    "Saffron": "Azafrán",
    "Saffron milk": "Leche con azafrán",
    "Saffron, rose, cardamom in foods": "Azafrán, rosa y cardamomo en las comidas",
    "Sesame in all forms": "Sésamo en todas sus formas",
    "Sesame seeds": "Semillas de sésamo",
    "Shatavari in warm milk": "Shatavari en leche tibia",
    "Silence while eating": "Silencio al comer",
    "Simple, sattvic food": "Comida simple y sáttvica",
    "Stale or leftover food": "Comida rancia o sobras",
    "Sweet fruits": "Frutas dulces",
    "Sweet potato": "Batata",
    "Triphala churna": "Triphala churna",
    "Tulsi tea": "Té de tulsi",
    "Turmeric and black pepper together": "Cúrcuma y pimienta negra juntas",
    "Turmeric and saffron": "Cúrcuma y azafrán",
    "Urad dal and sesame together": "Urad dal y sésamo juntos",
    "Very fatty foods": "Alimentos muy grasos",
    "Very spicy food": "Comida muy picante",
    "Wheat and wheat products": "Trigo y productos de trigo",
    "White foods": "Alimentos blancos",
    "White kidney beans or rajma": "Frijoles blancos o rajma",
    "Yellow foods": "Alimentos amarillos",
    # day-clause variants that survive _today_safe: kept whole on the matching
    # weekday, partially stripped (leaving "mornings"/"evenings") on others.
    "Fennel": "Hinojo", "Barley water": "Agua de cebada",
    "Alcohol on Tuesday": "Alcohol los martes",
    "Banana mornings": "Plátano por las mañanas",
    "Banana on Thursday mornings": "Plátano los jueves por la mañana",
    "Black-colored foods during Rahu periods": "Alimentos de color negro durante los períodos de Rahu",
    "Coconut water": "Agua de coco",
    "Coconut water on Saturdays": "Agua de coco los sábados",
    "Coconut water on Sundays": "Agua de coco los domingos",
    "Fasting on Saturdays": "Ayuno los sábados",
    "Fasting on Tuesdays": "Ayuno los martes",
    "Kheer evenings": "Kheer por las noches",
    "Mustard oil in cooking": "Aceite de mostaza en la cocina",
    "Mustard oil in cooking on Saturdays": "Aceite de mostaza en la cocina los sábados",
    "Non-vegetarian food on Saturday": "Comida no vegetariana los sábados",
    "Onion and garlic on Fridays": "Cebolla y ajo los viernes",
    "Sesame oil massage before bath": "Masaje con aceite de sésamo antes del baño",
    "Sesame oil massage before bath on Saturday": "Masaje con aceite de sésamo antes del baño los sábados",
    "Turmeric milk evenings": "Leche con cúrcuma por las noches",
    "Turmeric milk on Thursday evenings": "Leche con cúrcuma los jueves por la noche",
}


def _t_planet(p: str) -> str:
    return _PLANET_SUBJECT.get((p or "").strip().title(), p or "")


def _es_food_list(items):
    out = []
    for it in items or []:
        out.append(_FOOD.get(it, it))   # unmapped -> keep English, never guess
    return out


def _es_why_eat(planet: str, mode: str) -> Optional[str]:
    p = (planet or "").strip().title()
    subj = _t_planet(p)
    if not subj:
        return None
    if mode == "strengthen":
        feeds = _GRAHA_FEEDS.get(p)
        return f"{subj} lleva el día, así que estos alimentos nutren tu {feeds}" if feeds else None
    dosha = _PLANET_DOSHA.get(p, "")
    tc = _DOSHA_MECHANISM.get(dosha)
    if not tc:
        return None
    return f"{subj} {tc[0]}, {tc[1]}"


def _es_texture(planet: str, mode: str) -> Optional[str]:
    p = (planet or "").strip().title()
    if mode == "strengthen":
        return _GRAHA_TEXTURE.get(p)
    dosha = _PLANET_DOSHA.get(p, "")
    if dosha == "Pitta":
        return "fresca"
    return _DOSHA_TEXTURE.get(dosha)


def _es_duration(planet: str, duration_days) -> Optional[str]:
    subj = _t_planet(planet)
    if duration_days is None:
        if not subj:
            return None
        return (f"{subj} rige tu período actual, así que esto no es un arreglo de un "
                f"día — sostenerlo durante todo el período es lo que genera el cambio")
    if duration_days == 1:
        return "Solo por hoy — esto es para asentar, no es un programa"
    if duration_days == 40:
        return ("Mantenlo unos 40 días — un mandala — y el efecto se acumula; "
                "un solo día cambia poco")
    return None


def _es_why_wear(text: str) -> Optional[str]:
    """Rebuild 'activates {area} — {outcome}' or 'supports {enhances}' in Spanish
    by exact-matching the template pieces. Returns None on any miss."""
    if not isinstance(text, str) or not text.strip():
        return None
    t = text.strip()
    if t.startswith("activates "):
        body = t[len("activates "):]
        for sep in (" — ", " - "):
            if sep in body:
                area, outcome = body.split(sep, 1)
                a, o = _AREA.get(area.strip()), _OUTCOME.get(outcome.strip())
                if a and o:
                    return f"activa {a} — {o}"
                return None
        return None
    if t.startswith("supports "):
        e = _ENHANCES.get(t[len("supports "):].strip())
        return f"favorece {e}" if e else None
    return None


def _localize_color_es(color: Dict[str, Any]) -> None:
    if not isinstance(color, dict):
        return
    for k in ("primary", "support", "soften"):
        v = color.get(k)
        if isinstance(v, str) and v in _COLOR:
            color[k] = _COLOR[v]
    ww = _es_why_wear(color.get("why_wear"))
    if ww:
        color["why_wear"] = ww
    ws = color.get("why_soften")
    if isinstance(ws, str) and ws in _RISK:
        color["why_soften"] = _RISK[ws]


def _localize_food_es(food: Dict[str, Any]) -> None:
    if not isinstance(food, dict):
        return
    planet, mode = food.get("planet"), food.get("mode")
    food["eat"] = _es_food_list(food.get("eat"))
    food["avoid"] = _es_food_list(food.get("avoid"))
    we = _es_why_eat(planet, mode)
    if we:
        food["why_eat"] = we
    tx = _es_texture(planet, mode)
    if tx:
        food["texture"] = tx
    du = _es_duration(planet, food.get("duration_days"))
    if du:
        food["duration"] = du


def _localize_moon_shift_es(ms: Dict[str, Any]) -> None:
    if not isinstance(ms, dict):
        return
    split = ms.get("split")
    if not isinstance(split, dict):
        return
    at = split.get("at") or ms.get("changes_at")
    direction = split.get("direction")
    if not at:
        return
    if direction == "improves":
        split["headline"] = f"Mejora a tu favor a las {at}"
    elif direction == "declines":
        split["headline"] = f"Se pone más difícil después de las {at}"
    elif direction == "neutral":
        split["headline"] = f"El tono del día cambia a las {at}"


def localize_remedial_es(day: Dict[str, Any]) -> Dict[str, Any]:
    """In-place Spanish localization of a day's colour/food/timing block.
    Safe on partial/None fields; unmapped strings keep their English value."""
    if not isinstance(day, dict):
        return day
    _localize_color_es(day.get("color"))
    _localize_food_es(day.get("food"))
    _localize_moon_shift_es(day.get("moon_shift"))
    return day
