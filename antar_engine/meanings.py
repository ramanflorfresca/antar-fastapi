"""[why-factors 2026-10-12] ONE table of what each planet and house means, in plain words.

Source: Antar.world/DRAFT_planet_and_house_meanings_for_review.md (v3, approved by the owner
2026-10-12). Used by antar_engine/why_factors.py for the "Why this reading" sheet, and the
source for the Glossary, so the wording is identical everywhere.

Rules the text follows (and tests/test_meanings.py enforces):
  - plain words first; the Vedic name is a label, never the only name
  - a difficult energy is "testing", never "bad"; every hard line has what helps
  - nothing forecasts a specific event, an illness, a death or a lifespan
  - en + es. Other languages fall back to English at the call site (a wrong-language line is
    worse than the English one).
"""
from typing import Dict, Optional

LANGS = ("en", "es")

# nature: the plain two-word split. "testing" asks for effort; it is not "bad".
NATURE = {
    "supportive": {"en": "supportive", "es": "de apoyo"},
    "testing": {"en": "testing", "es": "exigente"},
}

PLANETS: Dict[str, dict] = {
    "Sun": {"nature": "testing", "en": {
        "name": "Authority", "verb": "I shine", "covers": "confidence, purpose, being seen; career standing, vitality, father figures",
        "watch": "ego clashes, conflict with authority, drained vitality", "helps": "humility, rest, sharing credit"},
        "es": {"name": "Autoridad", "verb": "Yo brillo", "covers": "confianza, propósito, ser visto; posición profesional, vitalidad, figuras paternas",
               "watch": "choques de ego, conflicto con la autoridad, vitalidad agotada", "helps": "humildad, descanso, compartir el mérito"}},
    "Moon": {"nature": "supportive", "en": {
        "name": "Mind", "verb": "I feel", "covers": "feeling, mood, what you need; emotional steadiness, home, sleep, mother",
        "watch": "mood swings, restless sleep, over-reacting", "helps": "routine, sleep, time near water or in quiet"},
        "es": {"name": "Mente", "verb": "Yo siento", "covers": "sentimiento, ánimo, lo que necesitas; estabilidad emocional, hogar, sueño, madre",
               "watch": "cambios de ánimo, sueño inquieto, reaccionar de más", "helps": "rutina, sueño, tiempo cerca del agua o en calma"}},
    "Mars": {"nature": "testing", "en": {
        "name": "Drive", "verb": "I act", "covers": "energy, courage, taking action; effort, competition, property, stamina",
        "watch": "anger, accidents, injuries, inflammation, surgery", "helps": "a physical outlet, patience before acting, care with safety"},
        "es": {"name": "Impulso", "verb": "Yo actúo", "covers": "energía, valentía, pasar a la acción; esfuerzo, competencia, propiedad, resistencia",
               "watch": "enojo, accidentes, lesiones, inflamación, cirugía", "helps": "una salida física, paciencia antes de actuar, cuidado con la seguridad"}},
    "Mercury": {"nature": "supportive", "en": {
        "name": "Intellect", "verb": "I think", "covers": "thinking, speaking, trading, learning; communication, contracts, study, commerce",
        "watch": "miscommunication, nerves, skin, over-thinking", "helps": "writing it down, reading terms twice, pausing"},
        "es": {"name": "Intelecto", "verb": "Yo pienso", "covers": "pensar, hablar, comerciar, aprender; comunicación, contratos, estudio, comercio",
               "watch": "malentendidos, nervios, piel, pensar de más", "helps": "ponerlo por escrito, leer los términos dos veces, hacer una pausa"}},
    "Jupiter": {"nature": "supportive", "en": {
        "name": "Growth", "verb": "I expand", "covers": "wisdom, guidance, generosity; teachers, children, luck, long-term growth",
        "watch": "over-promising, excess, weight", "helps": "moderation, a mentor"},
        "es": {"name": "Crecimiento", "verb": "Yo me expando", "covers": "sabiduría, guía, generosidad; maestros, hijos, suerte, crecimiento a largo plazo",
               "watch": "prometer de más, excesos, peso", "helps": "moderación, un mentor"}},
    "Venus": {"nature": "supportive", "en": {
        "name": "Comfort", "verb": "I enjoy", "covers": "love, beauty, harmony, enjoyment; relationships, money for comfort, the arts, fertility and vitality",
        "watch": "over-indulgence, relationship strain, overspending", "helps": "boundaries, honest talk, a budget"},
        "es": {"name": "Confort", "verb": "Yo disfruto", "covers": "amor, belleza, armonía, disfrute; relaciones, dinero para el confort, las artes, fertilidad y vitalidad",
               "watch": "excesos, tensión en las relaciones, gastar de más", "helps": "límites, hablar con honestidad, un presupuesto"}},
    "Saturn": {"nature": "testing", "en": {
        "name": "Discipline", "verb": "I build", "covers": "time, patience, structure, limits; slow-built results, duty, responsibility, endurance",
        "watch": "delay, heaviness, grief, loneliness, a sense of pressure", "helps": "steady effort, support, not carrying it alone"},
        "es": {"name": "Disciplina", "verb": "Yo construyo", "covers": "tiempo, paciencia, estructura, límites; resultados lentos, deber, responsabilidad, resistencia",
               "watch": "retrasos, pesadez, duelo, soledad, sensación de presión", "helps": "esfuerzo constante, apoyo, no cargarlo en soledad"}},
    "Rahu": {"nature": "testing", "en": {
        "name": "Ambition", "verb": "I reach", "covers": "hunger, novelty, going beyond the usual; foreign things, technology, sudden rises",
        "watch": "obsession, illusion, over-reach, risky shortcuts", "helps": "checking facts, grounded advice, one step at a time"},
        "es": {"name": "Ambición", "verb": "Yo aspiro", "covers": "hambre, novedad, ir más allá de lo habitual; lo extranjero, la tecnología, ascensos repentinos",
               "watch": "obsesión, ilusión, pasarse de la raya, atajos arriesgados", "helps": "verificar los hechos, consejo con los pies en la tierra, un paso a la vez"}},
    "Ketu": {"nature": "testing", "en": {
        "name": "Release", "verb": "I let go", "covers": "letting go, insight, detachment; withdrawal, sudden endings, intuition, the uncanny",
        "watch": "feeling lost, abrupt endings, disconnection", "helps": "quiet practice, finishing what is real, acceptance"},
        "es": {"name": "Desapego", "verb": "Yo suelto", "covers": "soltar, intuición, desapego; retiro, finales repentinos, lo inexplicable",
               "watch": "sentirse perdido, finales abruptos, desconexión", "helps": "práctica silenciosa, terminar lo que es real, aceptación"}},
}

HOUSES: Dict[int, dict] = {
    1: {"en": {"name": "You", "q": "Who am I?", "covers": "body, temperament, first impressions, vitality", "watch": "low energy, self-doubt", "helps": "steady routines and rest"},
        "es": {"name": "Tú", "q": "¿Quién soy?", "covers": "cuerpo, temperamento, primeras impresiones, vitalidad", "watch": "poca energía, dudas sobre ti", "helps": "rutinas estables y descanso"}},
    2: {"en": {"name": "Money and family", "q": "What do I value?", "covers": "earnings, savings, speech, the family you come from", "watch": "money worries, sharp words at home", "helps": "a budget and calm speech"},
        "es": {"name": "Dinero y familia", "q": "¿Qué valoro?", "covers": "ingresos, ahorros, la palabra, la familia de la que vienes", "watch": "preocupaciones de dinero, palabras duras en casa", "helps": "un presupuesto y hablar con calma"}},
    3: {"en": {"name": "Effort", "q": "How do I try?", "covers": "courage, skills, siblings, short journeys, communication", "watch": "scattered effort, friction with siblings", "helps": "one focused project"},
        "es": {"name": "Esfuerzo", "q": "¿Cómo lo intento?", "covers": "valentía, habilidades, hermanos, viajes cortos, comunicación", "watch": "esfuerzo disperso, fricción con hermanos", "helps": "un solo proyecto enfocado"}},
    4: {"en": {"name": "Home", "q": "Where do I belong?", "covers": "home, mother, inner peace, property, vehicles", "watch": "unrest at home, property or vehicle trouble", "helps": "rest and maintenance"},
        "es": {"name": "Hogar", "q": "¿A dónde pertenezco?", "covers": "hogar, madre, paz interior, propiedad, vehículos", "watch": "inquietud en casa, problemas de propiedad o vehículo", "helps": "descanso y mantenimiento"}},
    5: {"en": {"name": "Creativity", "q": "What do I create?", "covers": "children, learning, creativity, romance, speculation", "watch": "poor judgement in risk and romance", "helps": "slowing down before betting or committing"},
        "es": {"name": "Creatividad", "q": "¿Qué creo?", "covers": "hijos, aprendizaje, creatividad, romance, especulación", "watch": "mal criterio en riesgos y romance", "helps": "ir más despacio antes de apostar o comprometerte"}},
    6: {"en": {"name": "Daily work", "q": "How do I serve?", "covers": "routines, service, health upkeep, debts, rivals and opposition", "watch": "conflict at work, debts, health upkeep slipping", "helps": "clear agreements and routine"},
        "es": {"name": "Trabajo diario", "q": "¿Cómo sirvo?", "covers": "rutinas, servicio, cuidado de la salud, deudas, rivales y oposición", "watch": "conflicto en el trabajo, deudas, descuido de la salud", "helps": "acuerdos claros y rutina"}},
    7: {"en": {"name": "Partnership", "q": "Who do I meet?", "covers": "marriage, close partners, business partners, public dealings, contracts", "watch": "partner friction, contract disputes", "helps": "written terms and honest talks"},
        "es": {"name": "Pareja", "q": "¿A quién encuentro?", "covers": "matrimonio, parejas cercanas, socios, trato con el público, contratos", "watch": "fricción con la pareja, disputas de contrato", "helps": "términos por escrito y conversaciones honestas"}},
    8: {"en": {"name": "Change", "q": "What transforms me?", "covers": "shared money, sudden shifts, research, what is hidden, inheritance, and endurance: how you come through hard times", "watch": "sudden upheaval, shared-money surprises", "helps": "reserves and avoiding hidden risk"},
        "es": {"name": "Cambio", "q": "¿Qué me transforma?", "covers": "dinero compartido, cambios repentinos, investigación, lo oculto, herencia, y resistencia: cómo atraviesas los momentos difíciles", "watch": "sobresaltos, sorpresas con dinero compartido", "helps": "reservas y evitar riesgos ocultos"}},
    9: {"en": {"name": "Fortune", "q": "What do I believe?", "covers": "luck, mentors, belief, higher learning, long journeys, father", "watch": "mentors fall away, plans lose direction", "helps": "seeking guidance"},
        "es": {"name": "Fortuna", "q": "¿En qué creo?", "covers": "suerte, mentores, creencias, estudios superiores, viajes largos, padre", "watch": "los mentores se alejan, los planes pierden rumbo", "helps": "buscar orientación"}},
    10: {"en": {"name": "Career", "q": "What do I achieve?", "covers": "work, standing, authority, what you are known for", "watch": "setbacks in standing, friction with a boss", "helps": "patience and quality work"},
         "es": {"name": "Carrera", "q": "¿Qué logro?", "covers": "trabajo, posición, autoridad, aquello por lo que te conocen", "watch": "reveses en tu posición, fricción con un jefe", "helps": "paciencia y trabajo de calidad"}},
    11: {"en": {"name": "Gains", "q": "What do I gain?", "covers": "income streams, networks, friends, goals met", "watch": "delayed gains, a thin network", "helps": "keeping contacts warm"},
         "es": {"name": "Ganancias", "q": "¿Qué gano?", "covers": "fuentes de ingreso, redes, amigos, metas cumplidas", "watch": "ganancias demoradas, una red escasa", "helps": "mantener vivos los contactos"}},
    12: {"en": {"name": "Rest and release", "q": "What do I release?", "covers": "rest, expenses, foreign places, solitude, endings, private pleasures, sleep. The house of letting go, not only of loss", "watch": "leaking money, poor sleep, isolation", "helps": "rest, limits on spending, quiet routines"},
         "es": {"name": "Descanso y desapego", "q": "¿Qué suelto?", "covers": "descanso, gastos, lugares extranjeros, soledad, finales, placeres privados, sueño. La casa de soltar, no solo de pérdida", "watch": "fugas de dinero, mal sueño, aislamiento", "helps": "descanso, límites al gasto, rutinas tranquilas"}},
}

AIMS = {
    "dharma": {"houses": (1, 5, 9), "en": "purpose, values, principles", "es": "propósito, valores, principios"},
    "artha": {"houses": (2, 6, 10), "en": "material security: money, work, service", "es": "seguridad material: dinero, trabajo, servicio"},
    "kama": {"houses": (3, 7, 11), "en": "desire, connection, gains", "es": "deseo, conexión, ganancias"},
    "moksha": {"houses": (4, 8, 12), "en": "release, rest, the inner life", "es": "desprendimiento, descanso, la vida interior"},
}

# strength terms the chart-facts line already uses, in plain words. Keys are the exact notes
# ask_basis._dignity produces (prefix match for "combust").
TERMS = {
    "vargottama": {"en": "Vargottama", "es": "Vargottama",
                   "plain_en": "In the same sign in your main chart and its detailed chart, so its energy is steady and consistent.",
                   "plain_es": "En el mismo signo en tu carta principal y en su carta detallada, por eso su energía es estable y constante."},
    "exalted": {"en": "Exalted", "es": "Exaltado",
                "plain_en": "In a sign where it is strong, so it expresses easily.",
                "plain_es": "En un signo donde es fuerte, por eso se expresa con facilidad."},
    "debilitated": {"en": "Debilitated", "es": "Debilitado",
                    "plain_en": "In a sign where it needs support, so this area asks for extra care. It does not mean it fails.",
                    "plain_es": "En un signo donde necesita apoyo, por eso esta área pide cuidado extra. No significa que falle.",
                    "helps_en": "Give that area extra support: preparation, advice and patience.",
                    "helps_es": "Dale a esa área apoyo extra: preparación, consejo y paciencia."},
    "own sign": {"en": "In its own sign", "es": "En su propio signo",
                 "plain_en": "At home in its own sign, so it works comfortably.",
                 "plain_es": "En casa, en su propio signo, por eso funciona con comodidad."},
    "combust": {"en": "Combust", "es": "Combusto",
                "plain_en": "Close to the Sun, so its own voice is absorbed into the Sun's purpose and it works quietly. A reason to give that area deliberate effort.",
                "plain_es": "Cerca del Sol, por eso su propia voz se absorbe en el propósito del Sol y trabaja en silencio. Una razón para dedicar esfuerzo deliberado a esa área.",
                "helps_en": "Give that area deliberate effort: one direct, visible step, instead of waiting for it to happen.",
                "helps_es": "Dedica a esa área un esfuerzo deliberado: un paso directo y visible, en lugar de esperar a que ocurra."},
}


def lang_of(language) -> str:
    return "es" if str(language or "").lower().startswith("es") else "en"


def planet(name: str, language: str = "en") -> Optional[dict]:
    """{name, verb, covers, watch, helps, nature, nature_label, vedic} for a planet, or None."""
    p = PLANETS.get(name)
    if not p:
        return None
    lg = lang_of(language)
    t = p[lg]
    return {**t, "vedic": name, "nature": p["nature"], "nature_label": NATURE[p["nature"]][lg]}


def house(n: int, language: str = "en") -> Optional[dict]:
    h = HOUSES.get(n)
    if not h:
        return None
    lg = lang_of(language)
    aim = next((k for k, v in AIMS.items() if n in v["houses"]), None)
    return {**h[lg], "number": n, "aim": aim, "aim_line": AIMS[aim][lg] if aim else ""}


def term_for_note(note: str, language: str = "en") -> Optional[dict]:
    """{term, plain} for one of ask_basis._dignity's notes ("exalted", "in its own sign",
    "vargottama (strong in the navamsa)", "combust (weakened by the Sun)", "debilitated")."""
    n = str(note or "").lower()
    key = ("vargottama" if n.startswith("vargottama") else "combust" if n.startswith("combust")
           else "exalted" if n.startswith("exalted") else "debilitated" if n.startswith("debilitated")
           else "own sign" if "own sign" in n else None)
    if not key:
        return None
    lg = lang_of(language)
    t = TERMS[key]
    return {"term": t[lg], "plain": t["plain_" + lg]}
