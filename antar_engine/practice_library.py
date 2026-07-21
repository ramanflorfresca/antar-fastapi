"""
antar_engine/practice_library.py
─────────────────────────────────────────────────────────────────────────────
Practice content — ONE source of truth per planet.  Phase 1 (redesign).

Hard rule enforced by construction: a planet's remediation only ever draws
content from that planet's entry.  A Saturn remediation can never surface
Mercury content.

Prose fields that reach the user (governs / symptoms / affirmation /
why_this_works / daily_action.detail) carry {en, es}.  Mantra Sanskrit /
transliteration are language-neutral.  Body cue and breath pattern are kept
technical (English); they are short and instruction-like.
"""

from __future__ import annotations

import os

# Public Supabase storage bucket for pre-generated mantra audio (one rep, looped
# client-side).  Derived from SUPABASE_URL so it follows the environment.
AUDIO_BASE = (
    os.getenv("SUPABASE_URL", "https://ovszdbymflpwnynmpgqk.supabase.co").rstrip("/")
    + "/storage/v1/object/public/practice-audio"
)


def _audio_lang(language: str) -> str:
    l = str(language or "en").lower().split("-")[0]
    return l if l in ("en", "es", "pt") else "en"


def _loc(field, lang: str):
    """Pick en/es from a bilingual field; pass through plain values."""
    if isinstance(field, dict) and ("en" in field or "es" in field):
        l = "es" if str(lang).lower().startswith("es") else "en"
        return field.get(l) or field.get("en")
    return field


PRACTICE_LIBRARY = {
    "Sun": {
        "what_it_governs": {"en": "Authority, vitality, confidence, recognition, the father, the self at its center.",
                            "es": "Autoridad, vitalidad, confianza, reconocimiento, el padre, el yo en su centro."},
        "when_weak_symptoms": {"en": "Confidence flickers, recognition slips away, authority figures feel like obstacles, low vitality.",
                              "es": "La confianza vacila, el reconocimiento se escapa, las figuras de autoridad se sienten como obstáculos, baja vitalidad."},
        "mantra": {"primary": "Om Hraam Hreem Hraum Sah Suryaya Namaha", "sanskrit": "ॐ ह्रां ह्रीं ह्रौं सः सूर्याय नमः",
                   "translit": "OM HRAAM HREEM HRAUM SAH SURYAYA NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "At sunrise, facing east"},
        "body": {"name": "Sun Salutation (Surya Namaskar)", "minutes": 5,
                 "cue": "Move with the breath. Reach tall on the inhale, fold with the exhale. Let the spine wake from the base up."},
        "breath": {"name": "Bright Breath (Kapalabhati, gentle)", "pattern": "Short active exhales, passive inhales", "rounds": 3},
        "daily_action": {"title": "Offer water to the rising Sun",
                         "detail": {"en": "At sunrise, offer water from a copper vessel toward the Sun. Donate wheat or jaggery on Sundays. Respect your father and elders.",
                                    "es": "Al amanecer, ofrece agua desde un recipiente de cobre hacia el Sol. Dona trigo o panela los domingos. Honra a tu padre y a los mayores."},
                         "frequency": "Every Sunday for 9 weeks"},
        "affirmation": {"en": "I take up my space. My worth does not need permission. I shine without apology.",
                        "es": "Ocupo mi espacio. Mi valor no necesita permiso. Brillo sin disculparme."},
        "chakras_balanced": ["heart", "solar_plexus"],
        "why_this_works": {"en": "This energy is the steady core of confidence and vitality. When it runs low, the self dims and recognition won't land. The seed mantra rekindles that central fire, the morning movement floods the body with light, and the Lal Kitab offering discharges the debt that keeps it shadowed.",
                          "es": "Esta energía es el núcleo estable de la confianza y la vitalidad. Cuando está baja, el yo se atenúa y el reconocimiento no llega. El mantra semilla reaviva ese fuego central, el movimiento matinal inunda el cuerpo de luz, y la ofrenda de Lal Kitab descarga la deuda que la mantiene en sombra."},
        "frequency_hz": 126,
    },
    "Moon": {
        "what_it_governs": {"en": "Emotion, mind, comfort, the mother, memory, how you are received by others.",
                            "es": "Emoción, mente, comodidad, la madre, la memoria, cómo te reciben los demás."},
        "when_weak_symptoms": {"en": "Mood swings, restlessness, feeling unsupported, poor sleep, emotional reactivity.",
                              "es": "Cambios de humor, inquietud, sentirte sin apoyo, mal sueño, reactividad emocional."},
        "mantra": {"primary": "Om Shraam Shreem Shraum Sah Chandraya Namaha", "sanskrit": "ॐ श्रां श्रीं श्रौं सः चन्द्राय नमः",
                   "translit": "OM SHRAAM SHREEM SHRAUM SAH CHANDRAYA NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Monday evening, near water or moonlight"},
        "body": {"name": "Reclined Bound Angle (Supta Baddha Konasana)", "minutes": 5,
                 "cue": "Lie back, soles together, knees wide. Let gravity open the chest. Soften the belly with every exhale."},
        "breath": {"name": "Ocean Breath (Ujjayi)", "pattern": "Slow inhale and exhale with a soft throat hush", "rounds": 12},
        "daily_action": {"title": "Offer milk / keep silver",
                         "detail": {"en": "On Mondays, offer milk to flowing water or at a Shiva temple. Keep a small silver article with you. Care for your mother.",
                                    "es": "Los lunes, ofrece leche a agua corriente o en un templo de Shiva. Lleva contigo un pequeño objeto de plata. Cuida de tu madre."},
                         "frequency": "Every Monday for 9 weeks"},
        "affirmation": {"en": "I am safe to feel. My emotions are weather, not walls. I let comfort in.",
                        "es": "Es seguro sentir. Mis emociones son clima, no muros. Dejo entrar la calma."},
        "chakras_balanced": ["sacral", "third_eye"],
        "why_this_works": {"en": "This energy sets the emotional baseline and the felt sense of safety. When it runs low, the mind churns and rest won't come. The mantra steadies the inner tide, the restorative posture signals safety to the nervous system, and the silver and milk are the Lal Kitab way of feeding it.",
                          "es": "Esta energía marca la base emocional y la sensación de seguridad. Cuando está baja, la mente se agita y el descanso no llega. El mantra calma la marea interior, la postura restaurativa le indica seguridad al sistema nervioso, y la plata y la leche son la forma de Lal Kitab de alimentarla."},
        "frequency_hz": 210,
    },
    "Mars": {
        "what_it_governs": {"en": "Drive, courage, energy, action, boundaries, siblings, the will to push.",
                            "es": "Impulso, coraje, energía, acción, límites, hermanos, la voluntad de empujar."},
        "when_weak_symptoms": {"en": "Energy runs out fast, anger leaks sideways, plans stall, boundaries collapse, accidents and friction.",
                              "es": "La energía se agota rápido, la ira se filtra de lado, los planes se estancan, los límites colapsan, fricción y accidentes."},
        "mantra": {"primary": "Om Kram Kreem Kraum Sah Bhaumaya Namaha", "sanskrit": "ॐ क्रां क्रीं क्रौं सः भौमाय नमः",
                   "translit": "OM KRAM KREEM KRAUM SAH BHAUMAYA NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Tuesday morning, facing south"},
        "body": {"name": "Warrior II (Virabhadrasana II)", "minutes": 4,
                 "cue": "Front knee bent, arms wide and steady. Gaze past the front hand. Feel power without strain."},
        "breath": {"name": "Bellows Breath (Bhastrika, moderate)", "pattern": "Equal forceful inhale and exhale", "rounds": 6},
        "daily_action": {"title": "Give sweets at a Hanuman temple / donate red lentils",
                         "detail": {"en": "On Tuesdays, offer sweets at a Hanuman temple or donate red masoor lentils. Channel anger into physical work, not people.",
                                    "es": "Los martes, ofrece dulces en un templo de Hanuman o dona lentejas rojas (masoor). Canaliza la ira en trabajo físico, no en las personas."},
                         "frequency": "Every Tuesday for 9 weeks"},
        "affirmation": {"en": "My energy is mine to direct. I act with aim, not heat. I hold my ground cleanly.",
                        "es": "Mi energía es mía para dirigir. Actúo con dirección, no con calor. Sostengo mi lugar con limpieza."},
        "chakras_balanced": ["root", "solar_plexus"],
        "why_this_works": {"en": "This energy rules drive and clean boundaries. When it runs low, effort leaks and force turns to friction. The mantra tempers the fire, the strong stance retrains controlled power, and the Tuesday offering settles the karmic charge the Lal Kitab way.",
                          "es": "Esta energía rige el impulso y los límites limpios. Cuando está baja, el esfuerzo se filtra y la fuerza se vuelve fricción. El mantra templa el fuego, la postura firme reentrena el poder controlado, y la ofrenda del martes asienta la carga kármica al modo de Lal Kitab."},
        "frequency_hz": 144,
    },
    "Mercury": {
        "what_it_governs": {"en": "Communication, analysis, learning, words, transactions, networks.",
                            "es": "Comunicación, análisis, aprendizaje, palabras, transacciones, redes."},
        "when_weak_symptoms": {"en": "Words don't land, deals stall, ideas feel stuck, brain fog, miscommunication compounds.",
                              "es": "Las palabras no aterrizan, los tratos se estancan, las ideas se atascan, niebla mental, la mala comunicación se acumula."},
        "mantra": {"primary": "Om Bum Budhaye Namaha", "sanskrit": "ॐ बुं बुधाय नमः",
                   "translit": "OM BUM BUDHAYE NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Wednesday morning, or any morning before important conversations"},
        "body": {"name": "Seated Spinal Twist (Ardha Matsyendrasana)", "minutes": 3,
                 "cue": "Spine long. Twist from the navel, not the shoulders. Breathe into the kidneys."},
        "breath": {"name": "Alternate Nostril Breathing (Nadi Shodhana)", "pattern": "Inhale left, exhale right, inhale right, exhale left", "rounds": 9},
        "daily_action": {"title": "Donate green moong dal, feed a cow",
                         "detail": {"en": "On Wednesday, give green moong dal to someone who needs it, or feed fresh green grass to a cow. If no cow, scatter green vegetables for birds.",
                                    "es": "El miércoles, da moong dal verde a quien lo necesite, o alimenta con pasto verde fresco a una vaca. Si no hay vaca, esparce verduras verdes para las aves."},
                         "frequency": "Every Wednesday for 9 weeks"},
        "affirmation": {"en": "My words land. My thinking is clear. I speak only what is true and useful.",
                        "es": "Mis palabras aterrizan. Mi pensamiento es claro. Solo digo lo que es verdadero y útil."},
        "chakras_balanced": ["throat", "third_eye"],
        "why_this_works": {"en": "This energy rules the channels through which thought becomes word and word becomes action. When it runs low, those channels jam. The mantra clears the seed-vibration, the breath rebalances the hemispheres, and the daily action discharges the karmic debt in Lal Kitab form.",
                          "es": "Esta energía rige los canales por los que el pensamiento se vuelve palabra y la palabra se vuelve acción. Cuando está baja, esos canales se atascan. El mantra limpia la vibración semilla, la respiración reequilibra los hemisferios, y la acción diaria descarga la deuda kármica al modo de Lal Kitab."},
        "frequency_hz": 282,
    },
    "Jupiter": {
        "what_it_governs": {"en": "Wisdom, growth, fortune, teachers, faith, expansion, generosity.",
                            "es": "Sabiduría, crecimiento, fortuna, maestros, fe, expansión, generosidad."},
        "when_weak_symptoms": {"en": "Growth stalls, opportunities dry up, faith wavers, advisors mislead, a sense of contraction.",
                              "es": "El crecimiento se estanca, las oportunidades se secan, la fe flaquea, los consejeros confunden, una sensación de contracción."},
        "mantra": {"primary": "Om Graam Greem Graum Sah Gurave Namaha", "sanskrit": "ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः",
                   "translit": "OM GRAAM GREEM GRAUM SAH GURAVE NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Thursday morning, facing northeast"},
        "body": {"name": "Tree Pose (Vrksasana)", "minutes": 4,
                 "cue": "Root one foot down, lift the other to the inner leg. Grow tall through the crown. Steady, not rigid."},
        "breath": {"name": "Three-Part Breath (Dirga)", "pattern": "Fill belly, ribs, chest; empty in reverse", "rounds": 9},
        "daily_action": {"title": "Donate yellow / respect teachers",
                         "detail": {"en": "On Thursdays, donate yellow items — turmeric, chana dal, yellow sweets — and offer respect to a teacher or mentor.",
                                    "es": "Los jueves, dona objetos amarillos — cúrcuma, chana dal, dulces amarillos — y muestra respeto a un maestro o mentor."},
                         "frequency": "Every Thursday for 9 weeks"},
        "affirmation": {"en": "I make room to grow. I trust that good arrives. I give, and the channel opens.",
                        "es": "Hago espacio para crecer. Confío en que el bien llega. Doy, y el canal se abre."},
        "chakras_balanced": ["crown", "sacral"],
        "why_this_works": {"en": "This energy rules expansion and grace. When it runs low, the world feels stingy and growth dries up. The mantra reopens the channel of fortune, the balancing posture trains steady uprightness, and the Thursday giving discharges the debt the Lal Kitab way — generosity restores the flow.",
                          "es": "Esta energía rige la expansión y la gracia. Cuando está baja, el mundo se siente tacaño y el crecimiento se seca. El mantra reabre el canal de la fortuna, la postura de equilibrio entrena una verticalidad estable, y la entrega del jueves descarga la deuda al modo de Lal Kitab — la generosidad restaura el flujo."},
        "frequency_hz": 183,
    },
    "Venus": {
        "what_it_governs": {"en": "Love, beauty, pleasure, relationships, art, value, harmony.",
                            "es": "Amor, belleza, placer, relaciones, arte, valor, armonía."},
        "when_weak_symptoms": {"en": "Relationships feel dry, pleasure goes flat, money won't flow, a loss of taste and ease.",
                              "es": "Las relaciones se sienten secas, el placer se apaga, el dinero no fluye, pérdida del gusto y la soltura."},
        "mantra": {"primary": "Om Draam Dreem Draum Sah Shukraya Namaha", "sanskrit": "ॐ द्रां द्रीं द्रौं सः शुक्राय नमः",
                   "translit": "OM DRAAM DREEM DRAUM SAH SHUKRAYA NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Friday morning, facing southeast"},
        "body": {"name": "Camel Pose (Ustrasana, gentle)", "minutes": 3,
                 "cue": "Open the front of the heart. Hands to the lower back or heels. Lead with the chest, not the chin."},
        "breath": {"name": "Heart-Smiling Breath", "pattern": "Inhale 5 · soft hold 2 · exhale 6", "rounds": 9},
        "daily_action": {"title": "Donate white / care for women in the family",
                         "detail": {"en": "On Fridays, donate white items — sugar, rice, white cloth — and offer kindness or a gift to the women in your family.",
                                    "es": "Los viernes, dona objetos blancos — azúcar, arroz, tela blanca — y ofrece amabilidad o un regalo a las mujeres de tu familia."},
                         "frequency": "Every Friday for 9 weeks"},
        "affirmation": {"en": "I am worthy of sweetness. I let love and beauty in. Value flows to me with ease.",
                        "es": "Merezco la dulzura. Dejo entrar el amor y la belleza. El valor fluye hacia mí con soltura."},
        "chakras_balanced": ["heart", "sacral"],
        "why_this_works": {"en": "This energy rules sweetness, relating, and the flow of value. When it runs low, connection and pleasure go flat. The mantra restores the seed-tone of harmony, the heart-opening posture softens defended places, and the Friday giving settles the debt the Lal Kitab way.",
                          "es": "Esta energía rige la dulzura, el vínculo y el flujo del valor. Cuando está baja, la conexión y el placer se apagan. El mantra restaura el tono semilla de la armonía, la postura que abre el pecho ablanda lo defendido, y la entrega del viernes asienta la deuda al modo de Lal Kitab."},
        "frequency_hz": 221,
    },
    "Saturn": {
        "what_it_governs": {"en": "Structure, discipline, time, slow build, responsibility, fathers, elders, work that compounds.",
                            "es": "Estructura, disciplina, tiempo, construcción lenta, responsabilidad, mayores, el trabajo que se capitaliza."},
        "when_weak_symptoms": {"en": "Work that won't compound, plans that stall, conflict around responsibility, fear of authority, chronic procrastination.",
                              "es": "Trabajo que no cuaja, planes que se estancan, conflicto en torno a la responsabilidad, miedo a la autoridad, procrastinación crónica."},
        "mantra": {"primary": "Om Sham Shanaye Namaha", "sanskrit": "ॐ शं शनैश्चराय नमः",
                   "translit": "OM SHAM SHANAISHCHARAYA NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Before sunset, facing west"},
        "body": {"name": "Mountain Pose (Tadasana)", "minutes": 3,
                 "cue": "Feet planted. Spine long. Crown lifting. Shoulders softening. Feel the weight evenly through both feet."},
        "breath": {"name": "Extended Exhale", "pattern": "Inhale 4 · Exhale 8", "rounds": 9},
        "daily_action": {"title": "Feed black dogs / give black sesame to crows",
                         "detail": {"en": "On a Saturday, give roti mixed with black sesame oil to a black dog, or scatter black sesame seeds where crows gather. Don't tell anyone you did this.",
                                    "es": "Un sábado, da roti con aceite de sésamo negro a un perro negro, o esparce semillas de sésamo negro donde se reúnen los cuervos. No le cuentes a nadie que lo hiciste."},
                         "frequency": "Every Saturday for 9 weeks"},
        "affirmation": {"en": "I move at the pace of building. I let what's slow be slow. I trust the long arc.",
                        "es": "Avanzo al ritmo de la construcción. Dejo que lo lento sea lento. Confío en el arco largo."},
        "chakras_balanced": ["root", "throat"],
        "why_this_works": {"en": "This energy rules slow-build, structure, and patience. When it runs low, time itself feels antagonistic — deadlines slip, momentum dies. The mantra is its seed sound; the daily action discharges karmic debt the way Lal Kitab prescribes; the body practice trains the nervous system to settle into its rhythm. None of this is fast. That's the point.",
                          "es": "Esta energía rige la construcción lenta, la estructura y la paciencia. Cuando está baja, el tiempo mismo se siente antagonista — los plazos resbalan, el impulso muere. El mantra es su sonido semilla; la acción diaria descarga la deuda kármica como prescribe Lal Kitab; la práctica corporal entrena al sistema nervioso a asentarse en su ritmo. Nada de esto es rápido. Ese es el punto."},
        "frequency_hz": 295,
    },
    "Rahu": {
        "what_it_governs": {"en": "Ambition, the foreign and unconventional, obsession, sudden change, hunger for more.",
                            "es": "Ambición, lo extranjero y no convencional, obsesión, cambio súbito, hambre de más."},
        "when_weak_symptoms": {"en": "Anxiety, scattered obsession, confusion, sudden disruptions, chasing things that don't satisfy.",
                              "es": "Ansiedad, obsesión dispersa, confusión, disrupciones súbitas, perseguir cosas que no satisfacen."},
        "mantra": {"primary": "Om Bhraam Bhreem Bhraum Sah Rahave Namaha", "sanskrit": "ॐ भ्रां भ्रीं भ्रौं सः राहवे नमः",
                   "translit": "OM BHRAAM BHREEM BHRAUM SAH RAHAVE NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Saturday at dusk, facing southwest"},
        "body": {"name": "Legs-Up-the-Wall (Viparita Karani)", "minutes": 6,
                 "cue": "Legs resting up the wall, arms wide. Let the racing mind drain downward. Nothing to chase here."},
        "breath": {"name": "Long Exhale with Pause", "pattern": "Inhale 4 · Exhale 6 · Pause 4", "rounds": 9},
        "daily_action": {"title": "Feed crows / donate to the marginalized",
                         "detail": {"en": "Feed crows regularly. On Saturdays, donate to people on the margins — the homeless, the overlooked. Keep an honest relationship with your ambition.",
                                    "es": "Alimenta a los cuervos con regularidad. Los sábados, dona a personas en los márgenes — sin hogar, ignorados. Mantén una relación honesta con tu ambición."},
                         "frequency": "Daily (crows) + every Saturday for 9 weeks"},
        "affirmation": {"en": "I want clearly, not compulsively. I ground my ambition. Enough is a place I can stand.",
                        "es": "Deseo con claridad, no por compulsión. Aterrizo mi ambición. Lo suficiente es un lugar donde puedo estar."},
        "chakras_balanced": ["third_eye", "root"],
        "why_this_works": {"en": "This energy rules hunger and the pull toward the new. When agitated, it scatters the mind into anxious chasing. The mantra contains the static, the inversion drains the over-revved nervous system, and feeding crows is the Lal Kitab way of settling its restless charge.",
                          "es": "Esta energía rige el hambre y el tirón hacia lo nuevo. Cuando se agita, dispersa la mente en una persecución ansiosa. El mantra contiene la estática, la inversión drena el sistema nervioso sobreacelerado, y alimentar cuervos es la forma de Lal Kitab de asentar su carga inquieta."},
        "frequency_hz": 268,
    },
    "Ketu": {
        "what_it_governs": {"en": "Detachment, spirituality, focus, the past, what falls away, liberation.",
                            "es": "Desapego, espiritualidad, enfoque, el pasado, lo que se desprende, liberación."},
        "when_weak_symptoms": {"en": "Feeling lost or rootless, sudden endings, spiritual emptiness, scattered focus, things slipping away.",
                              "es": "Sentirte perdido o sin raíces, finales súbitos, vacío espiritual, foco disperso, cosas que se escapan."},
        "mantra": {"primary": "Om Sraam Sreem Sraum Sah Ketave Namaha", "sanskrit": "ॐ स्रां स्रीं स्रौं सः केतवे नमः",
                   "translit": "OM SRAAM SREEM SRAUM SAH KETAVE NAMAHA", "count": 108, "duration_minutes": 15,
                   "when": "Evening, in stillness, facing any direction"},
        "body": {"name": "Child's Pose (Balasana)", "minutes": 5,
                 "cue": "Fold forward, forehead down, arms resting. Let the back body widen. Surrender weight to the floor."},
        "breath": {"name": "Witness Breath", "pattern": "Natural breath, simply watched, no control", "rounds": 12},
        "daily_action": {"title": "Keep a dog / donate blankets",
                         "detail": {"en": "Care for a dog if you can. Donate blankets to those without shelter. Keep a small, steady spiritual practice — even five minutes daily.",
                                    "es": "Cuida de un perro si puedes. Dona mantas a quienes no tienen refugio. Mantén una práctica espiritual pequeña y constante — aunque sean cinco minutos al día."},
                         "frequency": "Daily practice + ongoing donations"},
        "affirmation": {"en": "I let go cleanly. I trust what falls away. I am rooted even as I release.",
                        "es": "Suelto con limpieza. Confío en lo que se desprende. Estoy enraizado incluso al soltar."},
        "chakras_balanced": ["crown", "root"],
        "why_this_works": {"en": "This energy rules release and the inward turn. When unsettled, it leaves you rootless and scattered. The mantra steadies the dispersing pull, the forward fold returns you to the ground, and the quiet practice gives it its proper channel — focus through surrender, not grasping.",
                          "es": "Esta energía rige la liberación y el giro hacia adentro. Cuando está inquieta, te deja sin raíces y disperso. El mantra calma la energía que se dispersa, el pliegue hacia adelante te devuelve al suelo, y la práctica silenciosa le da su canal propio — enfoque a través de la entrega, no del aferramiento."},
        "frequency_hz": 304,
    },
}


def build_mantra_response(planet: str, language: str = "en") -> dict:
    """
    Mantra block in the API shape: name / sanskrit / transliteration / count /
    duration_minutes / when / audio_url / tone_hz.  audio_url points at the
    pre-generated, language-specific file (one rep, looped client-side); tone_hz
    is the planet's classical pitch for the client-side Web Audio oscillator.
    """
    entry = PRACTICE_LIBRARY.get(planet, {})
    m = entry.get("mantra", {})
    lang = _audio_lang(language)
    audio_path = m.get("audio_path", planet.lower())
    return {
        "name": m.get("primary"),
        "type": "bija",
        "sanskrit": m.get("sanskrit"),
        "transliteration": m.get("translit"),
        "count": m.get("count"),
        "duration_minutes": m.get("duration_minutes"),
        "when": m.get("when"),
        "audio_url": f"{AUDIO_BASE}/{audio_path}-{lang}.mp3",
        "tone_hz": entry.get("frequency_hz"),
    }


# Breath practices display a duration in the UI but the library entries carry
# only pattern/rounds. Authored minutes per planet (sized to the rounds).
_BREATH_MINUTES = {"Sun": 3, "Moon": 4, "Mars": 3, "Mercury": 3, "Jupiter": 4,
                   "Venus": 4, "Saturn": 5, "Rahu": 4, "Ketu": 5}


def _with_minutes(block: dict, fallback: int = None) -> dict:
    """Emit a copy carrying BOTH `minutes` and `duration_minutes` (same value),
    so every frontend key-choice resolves. None stays None intentionally."""
    out = dict(block)
    m = out.get("minutes", fallback)
    out["minutes"] = m
    out["duration_minutes"] = m
    return out


# [practice-i18n 2026-07-20] The pose/breath/action TITLES were authored as plain
# strings while their prose siblings (detail, why_this_works) carry {en, es}. A
# Spanish user therefore read "Warrior II" and "Bellows Breath" as headings above
# a fully Spanish description. The ES copy lives here rather than restructuring
# 54 literals inline across the nine entries: purely additive, so the English
# path is byte-identical and a missing key simply falls back to English.
# Sanskrit names are kept in parentheses — they are the pose's proper name.
_ES_PRACTICE = {
    "Sun": {
        "body_name": "Saludo al Sol (Surya Namaskar)",
        "body_cue": "Muévete con la respiración. Estírate hacia arriba al inhalar, pliégate al exhalar. Deja que la columna despierte desde la base.",
        "breath_name": "Respiración Luminosa (Kapalabhati, suave)",
        "breath_pattern": "Exhalaciones cortas y activas, inhalaciones pasivas",
        "da_title": "Ofrece agua al Sol naciente",
        "da_frequency": "Cada domingo durante 9 semanas",
    },
    "Moon": {
        "body_name": "Ángulo Atado Reclinado (Supta Baddha Konasana)",
        "body_cue": "Recuéstate, plantas de los pies juntas, rodillas abiertas. Deja que la gravedad abra el pecho. Suaviza el vientre con cada exhalación.",
        "breath_name": "Respiración Oceánica (Ujjayi)",
        "breath_pattern": "Inhala y exhala lento con un susurro suave en la garganta",
        "da_title": "Ofrece leche / guarda plata",
        "da_frequency": "Cada lunes durante 9 semanas",
    },
    "Mars": {
        "body_name": "Guerrero II (Virabhadrasana II)",
        "body_cue": "Rodilla delantera flexionada, brazos amplios y firmes. Mirada más allá de la mano delantera. Siente el poder sin tensión.",
        "breath_name": "Respiración de Fuelle (Bhastrika, moderada)",
        "breath_pattern": "Inhalación y exhalación forzadas por igual",
        "da_title": "Ofrece dulces en un templo de Hanuman / dona lentejas rojas",
        "da_frequency": "Cada martes durante 9 semanas",
    },
    "Mercury": {
        "body_name": "Torsión Espinal Sentada (Ardha Matsyendrasana)",
        "body_cue": "Columna larga. Gira desde el ombligo, no desde los hombros. Respira hacia los riñones.",
        "breath_name": "Respiración Alterna (Nadi Shodhana)",
        "breath_pattern": "Inhala izquierda, exhala derecha, inhala derecha, exhala izquierda",
        "da_title": "Dona moong dal verde, alimenta a una vaca",
        "da_frequency": "Cada miércoles durante 9 semanas",
    },
    "Jupiter": {
        "body_name": "Postura del Árbol (Vrksasana)",
        "body_cue": "Enraiza un pie, lleva el otro a la pierna interna. Crece alto por la coronilla. Firme, no rígido.",
        "breath_name": "Respiración en Tres Partes (Dirga)",
        "breath_pattern": "Llena vientre, costillas, pecho; vacía en orden inverso",
        "da_title": "Dona amarillo / honra a los maestros",
        "da_frequency": "Cada jueves durante 9 semanas",
    },
    "Venus": {
        "body_name": "Postura del Camello (Ustrasana, suave)",
        "body_cue": "Abre el frente del corazón. Manos en la zona lumbar o en los talones. Guía con el pecho, no con el mentón.",
        "breath_name": "Respiración del Corazón Sonriente",
        "breath_pattern": "Inhala 5 · retén suave 2 · exhala 6",
        "da_title": "Dona blanco / cuida a las mujeres de la familia",
        "da_frequency": "Cada viernes durante 9 semanas",
    },
    "Saturn": {
        "body_name": "Postura de la Montaña (Tadasana)",
        "body_cue": "Pies firmes. Columna larga. Coronilla que se eleva. Hombros que se suavizan. Siente el peso repartido en ambos pies.",
        "breath_name": "Exhalación Extendida",
        "breath_pattern": "Inhala 4 · Exhala 8",
        "da_title": "Alimenta perros negros / ofrece ajonjolí negro a los cuervos",
        "da_frequency": "Cada sábado durante 9 semanas",
    },
    "Rahu": {
        "body_name": "Piernas en la Pared (Viparita Karani)",
        "body_cue": "Piernas apoyadas en la pared, brazos abiertos. Deja que la mente acelerada se vacíe hacia abajo. Aquí no hay nada que perseguir.",
        "breath_name": "Exhalación Larga con Pausa",
        "breath_pattern": "Inhala 4 · Exhala 6 · Pausa 4",
        "da_title": "Alimenta cuervos / dona a quienes están al margen",
        "da_frequency": "Diario (cuervos) + cada sábado durante 9 semanas",
    },
    "Ketu": {
        "body_name": "Postura del Niño (Balasana)",
        "body_cue": "Pliégate hacia adelante, frente al suelo, brazos en reposo. Deja que la espalda se ensanche. Entrega el peso al suelo.",
        "breath_name": "Respiración Testigo",
        "breath_pattern": "Respiración natural, simplemente observada, sin control",
        "da_title": "Ten un perro / dona cobijas",
        "da_frequency": "Práctica diaria + donaciones continuas",
    },
}


def get_planet_content(planet: str, language: str = "en") -> dict:
    """Localised content block for one planet — every piece from the same entry."""
    entry = PRACTICE_LIBRARY.get(planet)
    if not entry:
        return {}
    da = entry["daily_action"]
    # Only es has curated title copy; every other language keeps the English
    # source, matching _loc()'s en/es contract.
    es = _ES_PRACTICE.get(planet, {}) if str(language).lower().startswith("es") else {}

    body = _with_minutes(entry["body"])
    if es.get("body_name"):
        body["name"] = es["body_name"]
    if es.get("body_cue"):
        body["cue"] = es["body_cue"]

    breath = _with_minutes(entry["breath"], fallback=_BREATH_MINUTES.get(planet, 3))
    if es.get("breath_name"):
        breath["name"] = es["breath_name"]
    if es.get("breath_pattern"):
        breath["pattern"] = es["breath_pattern"]

    return {
        "what_it_governs": _loc(entry["what_it_governs"], language),
        "when_weak_symptoms": _loc(entry["when_weak_symptoms"], language),
        "mantra": build_mantra_response(planet, language),
        "body": body,
        "breath": breath,
        "daily_action": {"title": es.get("da_title") or da["title"], "detail": _loc(da["detail"], language), "frequency": es.get("da_frequency") or da["frequency"], "minutes": None, "duration_minutes": None},
        "affirmation": _loc(entry["affirmation"], language),
        "chakras_balanced": list(entry["chakras_balanced"]),
        "why_this_works": _loc(entry["why_this_works"], language),
        "frequency_hz": entry["frequency_hz"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# GEMSTONE (RATNA) LAYER — appended by patch_gemstone_practice.py. Additive.
# ───────────────────────────────────────────────────────────────────────────
# Permanent-wear remedial layer for the Practice surface. NOT daily practice.
# Order of remediation is always: mantra (mandatory) -> yantra -> ONLY THEN the
# stone (optional). Prose fields are authored in English and translated to
# es/pt via the existing translate_dict pipeline; gemstone NAMES are localized
# deterministically from GEMSTONE_NAME_I18N; Sanskrit names stay Sanskrit.
# ═══════════════════════════════════════════════════════════════════════════

# Durable scopes that justify a permanent-wear recommendation. Transient
# triggers (daily_transit / monthly_lk) must NOT surface a gemstone.
GEMSTONE_SCOPES = {"natal_weakness", "dasha_period", "varshphal_year"}

# Leaf prose keys the translation pipeline may translate (es/pt). Names,
# Sanskrit, color_hex and risk_level are deliberately excluded.
GEMSTONE_TRANSLATABLE_FIELDS = [
    "description", "why_for_this_user", "preparation", "recommended_order",
    "sourcing", "weight_guideline", "weight_carats_range",
    "metal_primary", "metal_alternate", "finger", "hand",
    "first_wear_day", "first_wear_time", "cautions", "note",
]

# Stone names — the one field translated by a controlled map, not the LLM.
GEMSTONE_NAME_I18N = {
    "Ruby":            {"en": "Ruby",            "es": "Rub\u00ed",          "pt": "Rubi"},
    "Pearl":           {"en": "Pearl",           "es": "Perla",         "pt": "P\u00e9rola"},
    "Red Coral":       {"en": "Red Coral",       "es": "Coral Rojo",    "pt": "Coral Vermelho"},
    "Emerald":         {"en": "Emerald",         "es": "Esmeralda",     "pt": "Esmeralda"},
    "Yellow Sapphire": {"en": "Yellow Sapphire", "es": "Zafiro Amarillo","pt": "Safira Amarela"},
    "Diamond":         {"en": "Diamond",         "es": "Diamante",      "pt": "Diamante"},
    "Blue Sapphire":   {"en": "Blue Sapphire",   "es": "Zafiro Azul",   "pt": "Safira Azul"},
    "Hessonite Garnet":{"en": "Hessonite Garnet","es": "Granate Hesonita","pt": "Granada Hessonita"},
    "Cat's Eye":       {"en": "Cat's Eye",       "es": "Ojo de Gato",   "pt": "Olho de Gato"},
}


GEMSTONE_LIBRARY = {
    "Sun": {
        "name": "Ruby", "sanskrit": "Manik", "color_hex": "#C72E48",
        "risk_level": "low",
        "metal_primary": "Gold", "metal_alternate": "Panchadhatu (5-metal alloy)",
        "finger": "Ring finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "3-6 carats",
        "weight_guideline": "Rule of thumb: 1/12th of body weight in grams; 3-5 carats suits most adults.",
        "first_wear_day": "Sunday", "first_wear_time": "At sunrise on Sunday, in the Sun hora",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Suryaya Namaha 108 times. Wear it at sunrise without showing it to others on the first day.",
        "description": "The Sun rules vitality, confidence, authority and recognition. Ruby amplifies the Sun's fire — it strengthens a favorable Sun and steadies the felt sense of self-worth.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Red Garnet", "note": "Affordable Sun substitute — warm red family, gentle vitality boost"},
            {"name": "Red Spinel", "note": "Closest natural alternative to Ruby — similar fire, lower cost"},
            {"name": "Sunstone", "note": "Lowest-cost option — soft, supportive solar warmth"},
        ],
        "cautions": [
            "Ruby amplifies both sides of the Sun — if your natal Sun is afflicted, consult a qualified astrologer first.",
            "Avoid combining with Blue Sapphire, Hessonite, or Cat's Eye in the same hand — these are the Sun's adversaries.",
            "Use only natural, certified, untreated Ruby — glass-filled or heat-treated stones are energetically inert.",
        ],
        "sourcing": "Look for GIA, IGI, or GRS certification. Burmese (Mogok) rubies are the classical origin; Ceylon stones are also valued. Expect $150-$1500+ per carat for natural, untreated stone.",
        "recommended_order": "Mantra (Om Suryaya Namaha, 108 daily) → Gold Sun yantra → copper Sun pendant → ONLY THEN consider Ruby. The mantra is mandatory. The stone is optional.",
    },
    "Moon": {
        "name": "Pearl", "sanskrit": "Moti", "color_hex": "#F4F4F4",
        "risk_level": "low",
        "metal_primary": "Silver", "metal_alternate": "Panchadhatu (5-metal alloy) or White Gold",
        "finger": "Little finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "4-7 carats",
        "weight_guideline": "Pearls are worn generously — 4-7 carats (or larger) is common, sized to the finger.",
        "first_wear_day": "Monday", "first_wear_time": "Monday morning in the Moon hora, ideally on a waxing-moon Monday",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Chandraya Namaha 108 times. Wear it on Monday morning, calmly and privately.",
        "description": "The Moon rules emotion, mind, comfort and how you are received. Pearl cools and steadies the Moon — it softens emotional reactivity and supports rest and inner safety.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Moonstone", "note": "Affordable Moon substitute — calming, classically lunar"},
            {"name": "White Coral", "note": "Gentle lunar support — steadies mood at low cost"},
            {"name": "Rainbow Moonstone", "note": "Lowest-cost option — soft, soothing Moon vibration"},
        ],
        "cautions": [
            "Pearl is gentle, but if your natal Moon is severely afflicted, confirm suitability with an astrologer.",
            "Avoid combining with Hessonite or Cat's Eye in the same hand — the nodes unsettle the Moon.",
            "Choose natural, certified pearls (not plastic or shell-coated imitations).",
        ],
        "sourcing": "Natural or cultured saltwater pearls (Basra, South Sea). Look for a lab certificate of natural/cultured origin. Expect $30-$400+ per carat depending on luster and origin.",
        "recommended_order": "Mantra (Om Chandraya Namaha, 108 daily) → Silver Moon yantra → silver pendant → ONLY THEN consider Pearl. The mantra is mandatory. The stone is optional.",
    },
    "Mars": {
        "name": "Red Coral", "sanskrit": "Moonga", "color_hex": "#D14A3A",
        "risk_level": "low",
        "metal_primary": "Copper or Gold", "metal_alternate": "Panchadhatu (5-metal alloy)",
        "finger": "Ring finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "6-12 carats",
        "weight_guideline": "Red Coral is worn fairly large — 6-12 carats is typical, sized to the finger.",
        "first_wear_day": "Tuesday", "first_wear_time": "Tuesday at sunrise, in the Mars hora",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Angarakaya Namaha 108 times. Wear it on Tuesday at sunrise.",
        "description": "Mars rules drive, courage, energy and clean boundaries. Red Coral strengthens Mars — it supports steady stamina and channels force into aim rather than friction.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Carnelian", "note": "Affordable Mars substitute — warm, energizing, grounding"},
            {"name": "Red Jasper", "note": "Steady Mars support — endurance and courage at low cost"},
            {"name": "Bloodstone", "note": "Lowest-cost option — classical Mars vitality stone"},
        ],
        "cautions": [
            "Red Coral can heat an already-fiery temperament — if your Mars is strong or afflicted, consult first.",
            "Avoid combining with Emerald in the same hand — Mercury and Mars are adversaries.",
            "Use natural, untreated coral; dyed or reconstituted coral is energetically inert.",
        ],
        "sourcing": "Natural Italian (Mediterranean) or Japanese coral, undyed. Look for a gemological certificate of natural origin. Expect $20-$200+ per carat.",
        "recommended_order": "Mantra (Om Angarakaya Namaha, 108 daily) → Copper Mars yantra → copper pendant → ONLY THEN consider Red Coral. The mantra is mandatory. The stone is optional.",
    },
    "Mercury": {
        "name": "Emerald", "sanskrit": "Panna", "color_hex": "#4FAE5F",
        "risk_level": "low",
        "metal_primary": "Gold", "metal_alternate": "Panchadhatu (5-metal alloy) or Silver",
        "finger": "Little finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "3-6 carats",
        "weight_guideline": "3-6 carats suits most adults; emerald is potent, so moderate weights are common.",
        "first_wear_day": "Wednesday", "first_wear_time": "Wednesday morning, in the Mercury hora",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Budhaya Namaha 108 times. Wear it on Wednesday morning.",
        "description": "Mercury rules communication, analysis, learning and exchange. Emerald clears Mercury's channels — it supports clear speech, steady focus and sound judgment.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Green Tourmaline", "note": "Affordable Mercury substitute — clear green family, mentally supportive"},
            {"name": "Peridot", "note": "Gentle Mercury support — clarity and ease at lower cost"},
            {"name": "Aventurine", "note": "Lowest-cost option — soft, supportive Mercury vibration"},
        ],
        "cautions": [
            "Emerald is potent — if your natal Mercury is heavily afflicted, confirm suitability with an astrologer.",
            "Avoid combining with Pearl or Red Coral in the same hand — these clash with Mercury.",
            "Choose natural, certified emerald; heavily oil-/resin-filled stones are weaker and may fracture.",
        ],
        "sourcing": "Colombian, Zambian, or Brazilian emerald with GIA/IGI/GRS certification noting treatment level. Expect $100-$2000+ per carat depending on clarity and origin.",
        "recommended_order": "Mantra (Om Budhaya Namaha, 108 daily) → Gold Mercury yantra → bronze pendant → ONLY THEN consider Emerald. The mantra is mandatory. The stone is optional.",
    },
    "Jupiter": {
        "name": "Yellow Sapphire", "sanskrit": "Pukhraj", "color_hex": "#E0A23B",
        "risk_level": "low",
        "metal_primary": "Gold", "metal_alternate": "Panchadhatu (5-metal alloy)",
        "finger": "Index finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "3-6 carats",
        "weight_guideline": "Rule of thumb: 1/12th of body weight in grams; 3-5 carats suits most adults.",
        "first_wear_day": "Thursday", "first_wear_time": "Thursday at sunrise, in the Jupiter hora",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Gurave Namaha 108 times. Wear it on Thursday at sunrise.",
        "description": "Jupiter rules wisdom, growth, fortune and faith. Yellow Sapphire expands Jupiter's grace — it supports optimism, good counsel and a felt sense of opportunity opening.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Yellow Topaz (Sunela)", "note": "Affordable Jupiter substitute — same golden family, gentler effect"},
            {"name": "Citrine", "note": "Warm Jupiter support — abundance and optimism at low cost"},
            {"name": "Heliodor", "note": "Lowest-cost option — soft golden Jupiter vibration"},
        ],
        "cautions": [
            "Yellow Sapphire is broadly benefic, but if your natal Jupiter is afflicted, confirm with an astrologer.",
            "Avoid combining with Diamond, Emerald, or Blue Sapphire in the same hand — these oppose Jupiter.",
            "Use only natural, certified, untreated Yellow Sapphire — diffusion-treated stones are inert.",
        ],
        "sourcing": "Ceylon (Sri Lanka) yellow sapphire with GIA/IGI/GRS certification. Expect $80-$1000+ per carat for natural, untreated stone.",
        "recommended_order": "Mantra (Om Gurave Namaha, 108 daily) → Gold Jupiter yantra → gold pendant → ONLY THEN consider Yellow Sapphire. The mantra is mandatory. The stone is optional.",
    },
    "Venus": {
        "name": "Diamond", "sanskrit": "Heera", "color_hex": "#DFE5F0",
        "risk_level": "medium",
        "metal_primary": "White Gold or Platinum", "metal_alternate": "Silver",
        "finger": "Middle finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "0.5-1.5 carats",
        "weight_guideline": "Diamond is worn small — even 0.3-1 carat is effective; weight matters far less than purity.",
        "first_wear_day": "Friday", "first_wear_time": "Friday at sunrise, in the Venus hora",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Shukraya Namaha 108 times. Wear it on Friday at sunrise.",
        "description": "Venus rules love, beauty, pleasure, art and the flow of value. Diamond amplifies Venus — it supports harmony, refinement and ease in relating and resources.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "White Sapphire", "note": "Affordable Venus substitute — colorless and brilliant, very close in effect"},
            {"name": "White Zircon", "note": "Bright Venus support — diamond-like sparkle at a fraction of the cost"},
            {"name": "Clear Quartz", "note": "Lowest-cost option — gentle, clarifying Venus vibration"},
        ],
        "cautions": [
            "Diamond is rarely harmful but cost-prohibitive — a White Sapphire does similar work for far less.",
            "Watch Sun–Saturn–Venus combinations: if Venus sits with the Sun or Saturn in difficult ways, have a qualified astrologer review before committing.",
            "Use only natural, certified diamond — lab-grown and treated stones differ energetically in this tradition.",
        ],
        "sourcing": "GIA-certified natural diamond; even a small, clean stone works. Expect $1000-$8000+ per carat — which is exactly why the substitutes below are recommended first.",
        "recommended_order": "Mantra (Om Shukraya Namaha, 108 daily) → Silver Venus yantra → White Sapphire (honest substitute) → ONLY THEN consider Diamond. The mantra is mandatory. The stone is optional.",
    },
    "Saturn": {
        "name": "Blue Sapphire", "sanskrit": "Neelam", "color_hex": "#3D5BC9",
        "risk_level": "high",
        "metal_primary": "Silver", "metal_alternate": "Panchadhatu (5-metal alloy) or Iron",
        "finger": "Middle finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "4-6 carats",
        "weight_guideline": "Rule of thumb: 1/12th of body weight in grams. Start at the lower end during the trial.",
        "first_wear_day": "Saturday", "first_wear_time": "Before sunrise on Saturday, in the Saturn hora",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Sham Shanaye Namaha 108 times. Wear it silently before sunrise on Saturday, without showing it to others on the first day.",
        "description": "Saturn rules slow-build, discipline, structure and karmic patience. Blue Sapphire amplifies Saturn's energy — both its benefic and malefic sides. When the chart's Saturn is favorable the stone accelerates rewards; when unfavorable, it amplifies losses.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Amethyst (Jamuniya)", "note": "Affordable Saturn substitute — same color family, gentler effect"},
            {"name": "Iolite (Kaka Neeli)", "note": "Often called 'water sapphire' — softer Saturn energy"},
            {"name": "Lapis Lazuli", "note": "Lowest-cost option — minimal but supportive Saturn vibration"},
        ],
        "cautions": [
            "TEST FIRST — wear for 3-7 days before any permanent commitment. If you experience nightmares, sudden financial loss, illness, accidents, or family conflict, remove it immediately.",
            "Avoid combining with Diamond, Pearl, or Red Coral in the same hand — these are Saturn's enemies.",
            "Do NOT wear if your natal Saturn is a functional malefic for your lagna without expert consultation.",
            "Only natural, certified, untreated Blue Sapphire. Heat-treated or synthetic stones are energetically inert.",
        ],
        "sourcing": "GIA, IGI, or GRS certification. Origin matters — Kashmir/Ceylon (Sri Lanka) sapphires are traditional. Expect $200-$2000+ per carat for natural stone.",
        "recommended_order": "Mantra (Om Sham Shanaye Namaha, 108 daily) → Silver Saturn yantra → Iron pendant → ONLY THEN consider Blue Sapphire. The mantra is mandatory. The stone is optional.",
    },
    "Rahu": {
        "name": "Hessonite Garnet", "sanskrit": "Gomed", "color_hex": "#C97A2F",
        "risk_level": "high",
        "metal_primary": "Silver or Panchadhatu (5-metal alloy)", "metal_alternate": "Ashtadhatu (8-metal alloy)",
        "finger": "Middle finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "6-9 carats",
        "weight_guideline": "Hessonite is worn fairly large — 6-9 carats is typical. Start at the lower end during the trial.",
        "first_wear_day": "Saturday", "first_wear_time": "Saturday at dusk / during Rahu kaal, worn with care",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Rahave Namaha 108 times. Wear it quietly at dusk on Saturday, without showing it to others on the first day.",
        "description": "Rahu rules ambition, the unconventional, obsession and sudden change. Hessonite channels Rahu — it can sharpen focus and worldly drive, but on a wrong chart it amplifies anxiety and disruption.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Spessartite Garnet", "note": "Affordable Rahu substitute — warm orange family, gentler nodal effect"},
            {"name": "Honey Topaz", "note": "Softer Rahu support — steadies ambition at lower cost"},
            {"name": "Brown Tourmaline", "note": "Lowest-cost option — grounding, minimal Rahu vibration"},
        ],
        "cautions": [
            "TEST FIRST — wear for 3-7 days before any permanent commitment. If you experience anxiety, nightmares, sudden losses, accidents, or scattered confusion, remove it immediately.",
            "Avoid combining with Ruby, Pearl, or Red Coral in the same hand — the luminaries and Mars clash with Rahu.",
            "Do NOT wear if Rahu is poorly placed for your lagna without expert consultation — nodal stones are unforgiving.",
            "Only natural, certified, untreated Hessonite. Treated or synthetic stones are energetically inert.",
        ],
        "sourcing": "Ceylon (Sri Lanka) hessonite with GIA/IGI/GRS certification. Expect $20-$150+ per carat for natural stone.",
        "recommended_order": "Mantra (Om Rahave Namaha, 108 daily) → Silver Rahu yantra → Ashtadhatu pendant → ONLY THEN consider Hessonite. The mantra is mandatory. The stone is optional.",
    },
    "Ketu": {
        "name": "Cat's Eye", "sanskrit": "Lehsuniya", "color_hex": "#B8A04A",
        "risk_level": "high",
        "metal_primary": "Silver or Panchadhatu (5-metal alloy)", "metal_alternate": "Ashtadhatu (8-metal alloy)",
        "finger": "Middle finger", "hand": "Right hand (left for left-handed people)",
        "weight_carats_range": "3-6 carats",
        "weight_guideline": "3-6 carats is typical. Start at the lower end during the trial.",
        "first_wear_day": "Tuesday or Thursday", "first_wear_time": "Tuesday or Thursday at sunrise, in a quiet hora",
        "preparation": "Soak the ring in raw cow's milk, Ganga water and tulsi leaves for 30 minutes. Holding the ring, recite Om Ketave Namaha 108 times. Wear it quietly at sunrise, without showing it to others on the first day.",
        "description": "Ketu rules detachment, focus, spirituality and what falls away. Cat's Eye channels Ketu — it can deepen intuition and protection, but on a wrong chart it amplifies sudden endings and rootlessness.",
        "why_for_this_user": "",
        "substitutes": [
            {"name": "Chrysoberyl", "note": "Affordable Cat's Eye substitute — same family, gentler nodal effect"},
            {"name": "Tiger's Eye", "note": "Softer Ketu support — grounding focus at low cost"},
            {"name": "Hawk's Eye", "note": "Lowest-cost option — calm, minimal Ketu vibration"},
        ],
        "cautions": [
            "TEST FIRST — wear for 3-7 days before any permanent commitment. If you experience sudden endings, illness, accidents, or a sense of rootlessness, remove it immediately.",
            "Avoid combining with Ruby, Pearl, or Red Coral in the same hand — the luminaries and Mars clash with Ketu.",
            "Do NOT wear if Ketu is poorly placed for your lagna without expert consultation — nodal stones are unforgiving.",
            "Only natural, certified, untreated Cat's Eye (chrysoberyl). Fibre-optic glass imitations are energetically inert.",
        ],
        "sourcing": "Natural chrysoberyl cat's eye with a sharp, centred band, GIA/IGI/GRS certified. Expect $50-$500+ per carat depending on the eye's clarity.",
        "recommended_order": "Mantra (Om Ketave Namaha, 108 daily) → Silver Ketu yantra → Ashtadhatu pendant → ONLY THEN consider Cat's Eye. The mantra is mandatory. The stone is optional.",
    },
}

# Literally attach a `gemstone` block to every PRACTICE_LIBRARY entry, so
# PRACTICE_LIBRARY[planet]["gemstone"] is populated for all 9 planets.
for _gp, _gdata in GEMSTONE_LIBRARY.items():
    if _gp in PRACTICE_LIBRARY:
        PRACTICE_LIBRARY[_gp]["gemstone"] = _gdata


def _gem_base_lang(language):
    l = str(language or "en").lower().split("_")[0].split("-")[0]
    return l if l in ("en", "es", "pt") else "en"


def build_gemstone_response(planet, language="en"):
    """Localised gemstone block for one planet (independent deep copy).

    Stone NAME is localised from GEMSTONE_NAME_I18N; Sanskrit, color_hex and
    risk_level stay verbatim; all prose stays English here and is translated to
    es/pt downstream by the translate_dict pipeline.
    """
    g = (PRACTICE_LIBRARY.get(planet) or {}).get("gemstone")
    if not g:
        return None
    base = _gem_base_lang(language)
    out = dict(g)
    out["name"] = GEMSTONE_NAME_I18N.get(g["name"], {}).get(base, g["name"])
    out["substitutes"] = [dict(s) for s in g.get("substitutes", [])]
    out["cautions"] = list(g.get("cautions", []))
    return out


# Plain-language replacements for jargon condition words in narration.
_COND_PLAIN = {"debilitated": "weak", "combust": "overshadowed",
               "sleeping": "dormant", "afflicted": "strained", "fallen": "weak"}


def _cond_plain(cond):
    return _COND_PLAIN.get(str(cond).lower(), cond)


def _prose_energy(planet):
    """EN energy phrase for narration — planet names never reach narration."""
    try:
        from antar_engine.practice_scopes import PLANET_ENERGY
        return PLANET_ENERGY["en"].get(planet, "this energy")
    except Exception:
        return "this energy"


def build_personalization(planet, scope, chart=None, conditions=None, language="en"):
    """One-sentence, chart-aware reason for `why_for_this_user`, framed by scope.

    Authored in English; translated to es/pt by the pipeline. Mantra-first,
    stone-optional framing is preserved in every variant.
    """
    g = (PRACTICE_LIBRARY.get(planet) or {}).get("gemstone", {})
    stone = g.get("name", "the stone")
    cond = ((conditions or {}).get(planet) or {}).get("condition")
    weak = isinstance(cond, str) and cond.lower() in (
        "debilitated", "combust", "weak", "afflicted", "fallen", "enemy")
    cond_clause = f" (currently reading as {_cond_plain(cond)})" if weak else ""

    if scope == "dasha_period":
        return (f"You are in a chapter that leans on {_prose_energy(planet)}{cond_clause} — {stone} prepares the "
                f"body and mind for this chapter. The mantra comes first; the stone is an "
                f"optional amplifier, never a replacement.")
    if scope == "varshphal_year":
        return (f"This year ahead emphasises {_prose_energy(planet)}{cond_clause} — {stone} is a "
                f"year-bounded support, not a permanent fixture. Begin with the mantra; the "
                f"stone is optional.")
    # natal_weakness (permanent recommendation) and any default.
    return (f"The part of you that carries {_prose_energy(planet)} runs weak in your birth chart{cond_clause}. Your daily practice already "
            f"strengthens it — the gemstone is an OPTIONAL advanced amplifier you may add later, "
            f"never a replacement for the practice.")


def personalize_gemstone(planet, scope="natal_weakness", language="en", chart=None, conditions=None):
    """PRACTICE_LIBRARY[planet]['gemstone'] localised + personalised for the user."""
    base = build_gemstone_response(planet, language)
    if not base:
        return None
    base["why_for_this_user"] = build_personalization(
        planet, scope, chart=chart, conditions=conditions, language=language)
    return base


# ═══════════════════════════════════════════════════════════════════════════
# AYURVEDA FOOD (AHAR) LAYER — appended by patch_food_practice.py. Additive.
# ───────────────────────────────────────────────────────────────────────────
# Daily, free, reversible dietary remedy. Sits alongside mantra/body/breath/
# daily-action/gemstone but is DAILY PRACTICE, not advanced commitment. Cultural
# anchor: South Indian / Tamil weekday-dish tradition (attribution, surfaced as
# the per-dish region tag). No medical claims. Prose is authored in English and
# translated to es/pt via translate_dict; dish NAMES stay canonical.
# ═══════════════════════════════════════════════════════════════════════════

import copy as _food_copy

# Durable scopes where a dietary shift is meaningful. Transient triggers
# (daily_transit / monthly_lk) must NOT surface food.
FOOD_SCOPES = {"natal_weakness", "dasha_period", "varshphal_year"}

# Leaf prose keys the translation pipeline may translate (es/pt). Dish NAMES
# (todays_dish.name) are excluded — Tamil/Sanskrit dish names are cultural
# markers, not English to translate.
FOOD_TRANSLATABLE_FIELDS = [
    "one_line", "why_for_this_user", "dosha", "best_time", "best_day",
    "description", "detail", "quantity", "regional_note", "region",
    "eat_more", "avoid", "moderate", "ingredients", "title",
    "primary", "secondary",
]

FOOD_LIBRARY = {
    "Sun": {
        "one_line": "The Sun wants warm, golden, building foods — eat to feed vitality and steady confidence.",
        "why_for_this_user": "",
        "dosha": "The Sun rules Pitta (fire). When the Sun is weak, vitality dims and confidence flickers. Sun food is warming, building, and golden — it rekindles the body's central fire.",
        "eat_more": [
            "Whole wheat", "Jaggery (gur)", "Red lentils (masoor dal)", "Carrots and beetroot",
            "Dates and oranges", "Almonds", "Ginger", "Cardamom",
        ],
        "cooking_medium": {
            "primary": "Ghee", "secondary": "Olive oil",
            "avoid": "Refined seed oils",
        },
        "best_day": "Sunday",
        "best_time": "At sunrise or in the morning — the Sun favors an early, substantial first meal over late-night eating.",
        "todays_dish": {
            "name": "Wheat Halwa with Jaggery",
            "region": "Tamil / Pan-Indian tradition",
            "description": "Cracked wheat roasted in ghee, simmered with jaggery, cardamom and almonds until glossy. Offered to Surya at sunrise on Sunday, then eaten warm.",
            "ingredients": [
                "Cracked wheat, 1 cup", "Jaggery, 3/4 cup", "Ghee, 3 tbsp",
                "Cardamom, 4 pods", "Almonds, 10", "Water, 2 cups",
            ],
        },
        "annadanam": {
            "title": "Feed wheat and jaggery to ascetics",
            "detail": "On Sunday, offer wheat-based food with jaggery to wandering ascetics, brahmins, or anyone in service of others. The Sun rules authority and recognition — feeding those who renounce it discharges solar karma.",
            "quantity": "Enough for at least one person; more if you can.",
        },
        "avoid": [
            "Excess salt", "Sour and heavily fermented foods", "Late-night heavy meals",
        ],
        "moderate": [
            "Chilies and very spicy food — the Sun is already hot", "Coffee in excess",
        ],
        "regional_note": "In Tamil tradition, Sunday morning often features wheat-based dishes — wheat pongal or wheat halwa. The Tirupati 'Suriyan' offering of wheat-rice with jaggery to the Sun god echoes the same lineage.",
    },
    "Moon": {
        "one_line": "The Moon wants moist, white, soft foods — eat to soothe the mind and steady the emotions.",
        "why_for_this_user": "",
        "dosha": "The Moon rules Kapha and Vata (water and air). When the Moon is weak, the mind churns and rest won't come. Moon food is moist, white, and soft — it cools and steadies the emotional baseline.",
        "eat_more": [
            "Rice", "Milk and fresh yogurt", "White pumpkin (ash gourd)", "Coconut",
            "Melons", "White sesame", "Ghee", "Fennel",
        ],
        "cooking_medium": {
            "primary": "Ghee", "secondary": "Coconut oil",
            "avoid": "Mustard oil on Mondays",
        },
        "best_day": "Monday",
        "best_time": "Morning, with a calm, unhurried meal — the Moon dislikes eating in agitation.",
        "todays_dish": {
            "name": "Thayir Sadam (Curd Rice)",
            "region": "Tamil / South Indian tradition",
            "description": "Soft-cooked rice mixed with fresh yogurt and a little milk, tempered with mustard seeds, curry leaves and grated ginger. Cooling, soothing, and quintessentially Monday.",
            "ingredients": [
                "Cooked rice, 1 cup", "Fresh yogurt, 1 cup", "Milk, 2 tbsp",
                "Mustard seeds, 1 tsp", "Curry leaves, a sprig", "Ginger, grated, 1 tsp", "Salt",
            ],
        },
        "annadanam": {
            "title": "Offer rice and milk to mothers",
            "detail": "On Monday morning, give rice and milk to women in need, mothers, or caregivers. The Moon rules the mother principle — nourishing those who nourish others feeds the Moon in your own chart.",
            "quantity": "Enough for at least one person; rice and milk for a small family if you can.",
        },
        "avoid": [
            "Stale or leftover food", "Excess salt", "Deep-fried foods", "Reheated old meals",
        ],
        "moderate": [
            "Sour foods late in the day", "Caffeine, which disturbs lunar calm",
        ],
        "regional_note": "Across Tamil Nadu, Monday breakfast is often curd rice or paal payasam (milk kheer). Many Iyer households make 'Annapurna' offerings on Mondays — sharing cooked rice with neighbors.",
    },
    "Mars": {
        "one_line": "Mars wants hot, red, energizing foods — eat to fuel drive, but with care if your fire already runs high.",
        "why_for_this_user": "",
        "dosha": "Mars rules Pitta (fire). When Mars is weak, energy leaks and boundaries collapse; when over-strong, it overheats. Mars food is hot, red and activating — use it to fuel clean drive, not friction.",
        "eat_more": [
            "Red lentils (masoor dal)", "Beetroot", "Red chilies (moderate)", "Pomegranate",
            "Jaggery", "Tamarind (sour)", "Mustard greens", "Ginger and garlic",
        ],
        "cooking_medium": {
            "primary": "Mustard oil", "secondary": "Sesame oil",
            "avoid": "Excess ghee",
        },
        "best_day": "Tuesday",
        "best_time": "Midday, when digestive fire is strongest — Mars food is heavy to digest late.",
        "todays_dish": {
            "name": "Puli Sadam (Tamarind Rice)",
            "region": "Tamil / South Indian tradition",
            "description": "Rice tossed with a tamarind-and-red-chili paste, tempered in sesame oil with mustard seeds and curry leaves. Tangy, fiery and activating — the classic Tuesday rice.",
            "ingredients": [
                "Cooked rice, 1 cup", "Tamarind paste, 2 tbsp", "Red chilies, 2",
                "Mustard seeds, 1 tsp", "Curry leaves, a sprig", "Sesame oil, 2 tbsp",
                "Peanuts, 2 tbsp", "Salt",
            ],
        },
        "annadanam": {
            "title": "Feed laborers and athletes",
            "detail": "On Tuesday, offer red lentils, jaggery and rice to soldiers, athletes, manual laborers, or anyone who works with their body. Mars rules the warrior and the worker — feeding them settles Mars's karmic charge.",
            "quantity": "Enough for at least one person; tradition favors feeding the physically active.",
        },
        "avoid": [
            "Excess raw or red meat if your Mars already runs hot", "Alcohol", "Excess deep-fried food",
        ],
        "moderate": [
            "Very spicy food if you anger easily", "Sour pickles in large amounts",
        ],
        "regional_note": "Tamil Tuesdays favor sour and spicy preparations — puli sadam, tomato rice, milagu rasam (black pepper rasam). Murugan temples (the South Indian Mars deity) distribute tamarind rice as prasadam.",
    },
    "Mercury": {
        "one_line": "Mercury wants light, green, fresh foods — eat to clear the mind and sharpen communication.",
        "why_for_this_user": "",
        "dosha": "Mercury is tridoshic with a Vata-Pitta tilt. When Mercury is weak, thinking scatters and words don't land. Mercury food is light, green and fresh — it clears the mental channels.",
        "eat_more": [
            "Green moong dal", "Green leafy vegetables", "Bottle gourd", "Mint and basil",
            "Cilantro", "Raw salads", "Sprouts", "Bitter gourd",
        ],
        "cooking_medium": {
            "primary": "Sesame oil", "secondary": "Light ghee",
            "avoid": "Heavy or repeatedly-reheated oils",
        },
        "best_day": "Wednesday",
        "best_time": "Light meals through the day — Mercury favors freshness and frequent small portions over one heavy meal.",
        "todays_dish": {
            "name": "Pasi Paruppu Sadam (Moong Dal Rice)",
            "region": "Tamil / South Indian tradition",
            "description": "Yellow moong dal cooked soft with rice, finished with ghee, cumin and a handful of fresh coriander. Light, clean and easy to digest — the simple Wednesday meal.",
            "ingredients": [
                "Yellow moong dal, 1/2 cup", "Rice, 1/2 cup", "Cumin, 1 tsp",
                "Ghee, 1 tbsp", "Fresh coriander, a handful", "Ginger, 1 tsp", "Salt",
            ],
        },
        "annadanam": {
            "title": "Feed students and scholars",
            "detail": "On Wednesday, offer green vegetables, moong dal and green leaves to students, scholars, accountants, or anyone who works with the mind. Mercury rules intellect and commerce — feeding the learned feeds Mercury.",
            "quantity": "Enough for at least one person; green produce for a student household if you can.",
        },
        "avoid": [
            "Heavy meats", "Excess dairy", "Overcooked or stale food", "Heavy late dinners",
        ],
        "moderate": [
            "Fried snacks", "Strong, dulling spices that cloud the mind",
        ],
        "regional_note": "Wednesday in Tamil households leans toward lighter, simpler meals — moong dal khichdi, sprouts, and fresh vegetable poriyal. Krishna devotees offer fresh green leaves to the deity on Wednesdays.",
    },
    "Jupiter": {
        "one_line": "Jupiter wants warm, yellow, ghee-rich foods — eat to feed wisdom, optimism and growth.",
        "why_for_this_user": "",
        "dosha": "Jupiter rules Kapha (water and earth). When Jupiter is weak, growth stalls and faith wavers. Jupiter food is warm, yellow and ghee-rich — it reopens the channel of fortune and expansion.",
        "eat_more": [
            "Turmeric", "Chana dal and toor dal", "Bananas", "Mangoes, pineapple and papaya",
            "Ghee", "Saffron", "Fennel and cardamom", "Yellow pumpkin",
        ],
        "cooking_medium": {
            "primary": "Ghee", "secondary": "Coconut oil for South Indian dishes",
            "avoid": "Refined seed oils",
        },
        "best_day": "Thursday",
        "best_time": "Morning or midday — Thursday is traditionally a ghee-rich, vegetarian, temple-visiting day.",
        "todays_dish": {
            "name": "Chana Dal with Banana Sheera",
            "region": "Tamil / Pan-Indian tradition",
            "description": "Yellow chana dal simmered with turmeric and ghee, served beside banana sheera — ripe banana cooked in ghee with cardamom and jaggery. Warm, golden, and nourishing.",
            "ingredients": [
                "Chana dal, 1 cup", "Turmeric, 1/2 tsp", "Ghee, 3 tbsp",
                "Ripe banana, 2", "Jaggery, 1/4 cup", "Cardamom, 4 pods", "Salt",
            ],
        },
        "annadanam": {
            "title": "Feed teachers and elders",
            "detail": "On Thursday, offer chana dal, rice, ghee and bananas to teachers, students, and wise elders. Jupiter rules the wisdom-givers — feeding those who teach and guide is the most direct way to feed Jupiter.",
            "quantity": "Enough for at least one person; a full meal for a teacher or guru if you can.",
        },
        "avoid": [
            "Alcohol on Thursday", "Leftover food", "Refined white sugar — use jaggery instead", "Heavily fried seed-oil food",
        ],
        "moderate": [
            "Very heavy meals that overload Kapha", "Excess salt",
        ],
        "regional_note": "Tamil Iyer and Iyengar tradition reserves Thursday for 'Guruvaaram' — strict vegetarianism, ghee-rich meals, and temple visits. Sai Baba devotees famously hold free annadanam (food charity) on Thursdays.",
    },
    "Venus": {
        "one_line": "Venus wants sweet, fragrant, dairy-rich foods — eat to feed beauty, harmony and ease.",
        "why_for_this_user": "",
        "dosha": "Venus rules Kapha (water). When Venus is weak, sweetness and connection go flat. Venus food is sweet, fragrant, and dairy-rich — pastel and pleasing, it restores the body's sense of value and harmony.",
        "eat_more": [
            "Basmati rice", "Dairy — milk, paneer, fresh cream", "Sweet fruits — grapes and dates",
            "Fennel seeds", "White pumpkin", "Jaggery or sugar in moderation", "Rose and cardamom",
        ],
        "cooking_medium": {
            "primary": "Ghee", "secondary": "Saffron-infused milk",
            "avoid": "Pungent, garlic-heavy oils on Fridays",
        },
        "best_day": "Friday",
        "best_time": "Midday or early evening — Friday meals are often sweet and shared, with a ghee lamp lit beforehand.",
        "todays_dish": {
            "name": "Elumichai Sadam with Sweet Pongal",
            "region": "Tamil / South Indian tradition",
            "description": "Tangy lemon rice (rice tempered with mustard, turmeric and lemon) paired with sweet pongal — rice and moong dal cooked with jaggery and ghee. Light and sweet together, the classic Friday pairing.",
            "ingredients": [
                "Cooked rice, 1 cup", "Lemon, 1", "Turmeric, 1/4 tsp", "Mustard seeds, 1 tsp",
                "Moong dal, 1/4 cup", "Jaggery, 1/2 cup", "Ghee, 2 tbsp", "Cardamom and cashews",
            ],
        },
        "annadanam": {
            "title": "Offer sweets to young women and artists",
            "detail": "On Friday, give rice, sugar, dairy and sweets to young women, brides, performers, and artists. Venus rules beauty, the feminine, and the arts — honoring them with sweetness feeds Venus.",
            "quantity": "Enough for at least one person; sweets to share with several if you can.",
        },
        "avoid": [
            "Bitter foods in excess", "Garlic — Venus dislikes pungency on its day", "Sour ferments",
        ],
        "moderate": [
            "Sugar — sweet but not to excess", "Very salty food",
        ],
        "regional_note": "Friday in Tamil households is Lakshmi/Shakti day. Sweet rice dishes, payasam (kheer), and floral garnishes are common, and many homes light a ghee lamp before the Friday meal.",
    },
    "Saturn": {
        "one_line": "Saturn wants slow-cooked, grounding, dark foods. Build patience through what you eat.",
        "why_for_this_user": "",
        "dosha": "Saturn rules Vata (air and space). When Saturn is weak or afflicted, the body shows Vata excess: dryness, anxiety, constipation, scattered thinking. Saturn food is dense, oily, and warming.",
        "eat_more": [
            "Black sesame seeds (til)", "Urad dal (black lentils)", "Eggplant (brinjal)",
            "Black pepper and asafoetida (hing)", "Slow-cooked grains — millet, barley",
            "Mustard greens and spinach", "Black grapes, blackberries, prunes",
        ],
        "cooking_medium": {
            "primary": "Mustard oil", "secondary": "Sesame oil (especially black sesame)",
            "avoid": "Refined vegetable oils, excess ghee",
        },
        "best_day": "Saturday",
        "best_time": "Before sunset — Saturn does not favor late-night eating. Last meal by 7 PM ideal.",
        "todays_dish": {
            "name": "Ellu Sadam (Black Sesame Rice)",
            "region": "Tamil / South Indian tradition",
            "description": "Roasted black sesame ground with red chilies and urad dal, mixed into rice with sesame oil. Eaten on Saturday as a Shani propitiation dish. Grounding, warming, dense.",
            "ingredients": [
                "Black sesame seeds, 2 tbsp", "Urad dal, 1 tbsp", "Red chilies, 2",
                "Curry leaves", "Sesame oil, 2 tbsp", "Cooked rice, 1 cup", "Salt",
            ],
        },
        "annadanam": {
            "title": "Feed the elderly / serve workers",
            "detail": "On Saturday, cook urad dal khichdi with sesame oil and offer it to elderly people, manual laborers, or anyone older than your father. Saturn rules age, labor, and patience — feeding those who embody these qualities discharges Saturn karma.",
            "quantity": "Enough for at least one person; tradition says nine if possible.",
        },
        "avoid": [
            "Sugar in excess (Saturn dislikes sweetness on its day)",
            "Refined / packaged food (Saturn rewards effort, not convenience)",
            "Onion, garlic for some traditions on Saturday",
            "Late-night eating after sunset",
            "Tamasic foods — heavy meats, stale food, fermented in excess",
        ],
        "moderate": [
            "Salt — necessary but not heavy", "Sour foods — small portions only",
        ],
        "regional_note": "In Tamil Brahmin households, Saturday is 'Shani Vaaram' — a fast or one-meal day is traditional, with that meal being ellu sadam (sesame rice) or urad dal khichdi. The dish is offered first to Shani at the temple, then consumed.",
    },
    "Rahu": {
        "one_line": "Rahu wants dense, grounding, hing-tempered foods — eat to settle scattered, anxious energy.",
        "why_for_this_user": "",
        "dosha": "Rahu aggravates Vata (air and space). When Rahu is agitated, the mind scatters into anxious chasing. Rahu food is dense, grounding, and warmed with asafoetida — it anchors the over-revved nervous system.",
        "eat_more": [
            "Mustard", "Black sesame", "Asafoetida (hing)", "Urad dal",
            "Tamarind", "Smoked or roasted foods in moderation", "Root vegetables",
        ],
        "cooking_medium": {
            "primary": "Mustard oil", "secondary": "Sesame oil",
            "avoid": "Processed, synthetic, or packaged oils",
        },
        "best_day": "Saturday",
        "best_time": "Earlier in the day; avoid important new eating habits during Rahu Kalam, the daily 1.5-hour Rahu window.",
        "todays_dish": {
            "name": "Khichdi with Hing Tempering",
            "region": "Tamil / North Indian tradition",
            "description": "Rice and urad dal cooked soft into khichdi, finished with a heavy asafoetida-and-mustard tempering in mustard oil. Dense and grounding — it settles Rahu's scattered energy.",
            "ingredients": [
                "Rice, 1/2 cup", "Urad dal, 1/2 cup", "Asafoetida (hing), 1/2 tsp",
                "Mustard seeds, 1 tsp", "Mustard oil, 2 tbsp", "Cumin, 1 tsp", "Salt",
            ],
        },
        "annadanam": {
            "title": "Feed the marginalized in Rahu Kalam",
            "detail": "On Saturday, during Rahu Kalam, offer mustard oil, sesame, and a black blanket to the homeless, the socially excluded, or anyone living at the margins. Rahu rules the outsider — feeding them grounds Rahu's restless charge.",
            "quantity": "Enough for at least one person; feeding stray dogs or temple sweepers also counts.",
        },
        "avoid": [
            "Onion and garlic (they intensify Rahu's chaos)", "Alcohol", "Recreational substances", "Processed and synthetic food",
        ],
        "moderate": [
            "Smoked and fermented foods — small amounts ground, excess unsettles", "Very stimulating spices",
        ],
        "regional_note": "Tamil tradition emphasizes 'anna daanam' (food charity) specifically during Rahu Kalam, the 1.5-hour Rahu period each day — feeding stray dogs, beggars, or temple sweepers is held to ground Rahu energy.",
    },
    "Ketu": {
        "one_line": "Ketu wants simple, dry, ascetic foods — eat lightly to support focus and inner detachment.",
        "why_for_this_user": "",
        "dosha": "Ketu intensifies a subtle, spiritual Pitta. When Ketu is unsettled, you feel rootless and scattered. Ketu food is simple, dry, and ascetic — restraint itself is the remedy, so lightness matters more than richness.",
        "eat_more": [
            "Red lentils (masoor)", "White sesame", "Tulsi (holy basil)", "Raw nuts",
            "Simple grains", "Fasting foods — sabudana, kuttu flour", "Fruit",
        ],
        "cooking_medium": {
            "primary": "Sesame oil", "secondary": "Minimal oil overall — Ketu favors restraint",
            "avoid": "Rich, heavy, or complex oil blends",
        },
        "best_day": "Tuesday or Thursday",
        "best_time": "Light, often a single simple meal — Ketu's day overlaps with partial-fast (vrat) traditions.",
        "todays_dish": {
            "name": "Sabudana Khichdi",
            "region": "Pan-Indian fasting tradition",
            "description": "Pearl tapioca tossed with roasted peanuts, cumin and a little ghee. A classic fasting food — simple, light, and undemanding, in keeping with Ketu's ascetic quality.",
            "ingredients": [
                "Sabudana (tapioca pearls), 1 cup", "Peanuts, 1/4 cup", "Cumin, 1 tsp",
                "Ghee, 1 tbsp", "Green chili, 1", "Curry leaves", "Rock salt",
            ],
        },
        "annadanam": {
            "title": "Feed sadhus and seekers",
            "detail": "Offer red lentils and sesame to sadhus, ascetics, and those on a spiritual path. Ketu rules detachment and liberation — feeding those who have renounced the world feeds Ketu in your chart.",
            "quantity": "Enough for at least one person; simple sattvic food, given without display.",
        },
        "avoid": [
            "Heavy meats", "Alcohol", "Gluttony and over-eating", "Complex, heavily-spiced dishes",
        ],
        "moderate": [
            "Strong stimulants", "Rich desserts",
        ],
        "regional_note": "Ketu remedies often overlap with fasting (vrat) traditions. Tamil Saivites observe weekly partial fasts on Ketu's day — eating only sabudana, fruit, or sattvic vegetarian preparations.",
    },
}

# Literally attach a `food` block to every PRACTICE_LIBRARY entry, so
# PRACTICE_LIBRARY[planet]["food"] is populated for all 9 planets.
for _fp, _fdata in FOOD_LIBRARY.items():
    if _fp in PRACTICE_LIBRARY:
        PRACTICE_LIBRARY[_fp]["food"] = _fdata


def build_food_response(planet, language="en"):
    """Independent deep copy of one planet's food block.

    All prose stays English here; dish names stay canonical. es/pt translation
    of the prose fields happens downstream via the translate_dict pipeline.
    `language` is accepted for signature parity and future use.
    """
    f = (PRACTICE_LIBRARY.get(planet) or {}).get("food")
    if not f:
        return None
    return _food_copy.deepcopy(f)


def build_food_personalization(planet, scope, chart=None, conditions=None, language="en"):
    """One-sentence, chart-aware reason for food.why_for_this_user, framed by scope."""
    cond = ((conditions or {}).get(planet) or {}).get("condition")
    weak = isinstance(cond, str) and cond.lower() in (
        "debilitated", "combust", "weak", "afflicted", "fallen", "enemy")
    cond_clause = f" (currently {_cond_plain(cond)} in your chart)" if weak else ""

    if scope == "dasha_period":
        return (f"You are in a chapter that leans on {_prose_energy(planet)}{cond_clause} — the matching food prepares the "
                f"body for the period's quality. Food is the most consistent daily lever you have; "
                f"every meal is a small recalibration of that energy.")
    if scope == "varshphal_year":
        return (f"This year highlights {_prose_energy(planet)}{cond_clause} — the aligned food path "
                f"supports the year ahead. Small daily shifts in what you eat compound over the months.")
    # natal_weakness (default).
    return (f"The part of you that carries {_prose_energy(planet)} runs weak in your birth chart{cond_clause}. Food is the most consistent daily "
            f"lever you have — every meal is a small recalibration of that energy in your body.")


def personalize_food(planet, scope="natal_weakness", language="en", chart=None, conditions=None):
    """PRACTICE_LIBRARY[planet]['food'] (deep copy) with why_for_this_user personalised."""
    base = build_food_response(planet, language)
    if not base:
        return None
    base["why_for_this_user"] = build_food_personalization(
        planet, scope, chart=chart, conditions=conditions, language=language)
    return base


# ═══════════════════════════════════════════════════════════════════════════
# YANTRA + DAAN + VRAT LAYER — appended by patch_remedies3_practice.py. Additive.
# ───────────────────────────────────────────────────────────────────────────
# Completes the 9-piece remedy stack. Cultural form is incidental; the principle
# is universal. Each remedy carries explicit Western/LATAM adaptation: yantras
# offer Hermetic-sigil + sacred-geometry + Catholic-medallion alternates; daan
# gives region-appropriate places to give (iglesia / comedor / shelter / mosque
# / a person on the street); vrat is voluntary, three-tier, and fronted by a
# hard medical disclaimer. Prose is authored in English and translated to es/pt
# via translate_dict; proper nouns stay in their original form.
# ═══════════════════════════════════════════════════════════════════════════
import copy as _r3_copy

# Per-remedy durable-scope gates. Daan additionally applies to monthly_lk
# (one Saturday of giving is meaningful even in a month window); yantra and
# vrat are too commitment-heavy for transient triggers.
YANTRA_SCOPES = {"natal_weakness", "dasha_period", "varshphal_year"}
VRAT_SCOPES = {"natal_weakness", "dasha_period", "varshphal_year"}
DAAN_SCOPES = {"natal_weakness", "dasha_period", "varshphal_year", "monthly_lk"}

# Translatable leaf keys per remedy (es/pt). Proper nouns are excluded:
# yantra `name`/`sanskrit`/`mantra`, western_alternates[].name, magic-square and
# sigil names, religious medallion names — all stay in their original form.
YANTRA_TRANSLATABLE_FIELDS = [
    "why_for_this_user", "type", "description", "size", "placement_traditional",
    "energization", "daily_practice", "rationale_western", "cautions", "sourcing",
    "metal_primary", "metal_alternate",
    # [practice-leaks] alternates are planet-scrubbed to clean EN before the
    # translate step, so the old proper-noun exclusion no longer applies.
    "western_alternates",
]
DAAN_TRANSLATABLE_FIELDS = [
    "one_line", "why_for_this_user", "day", "best_time", "principle",
    "rationale_universal", "frequency", "item", "quantity",
    "recipients_traditional", "traditional", "universal", "region", "form",
]
VRAT_TRANSLATABLE_FIELDS = [
    "one_line", "why_for_this_user", "day", "type_traditional", "type_modified",
    "type_minimal", "duration", "what_to_eat", "avoid", "intention",
    "medical_disclaimer", "catholic_parallel", "rationale_universal", "benefits",
]

# EXACT medical disclaimer — byte-identical across all 9 vrat entries.
_VRAT_MED_DISCLAIMER = (
    "Fasting is contraindicated for: diabetes (Type 1 and uncontrolled Type 2), "
    "pregnancy and breastfeeding, eating disorders or history of them, blood "
    "pressure medication, blood thinners, kidney conditions, and certain other "
    "medical conditions. ALWAYS consult your physician before beginning any "
    "fasting practice. If you cannot fast safely, the principle is still available "
    "through reduced consumption, simpler meals, or skipping one item — intention "
    "over strictness."
)

_VRAT_CATHOLIC_PARALLEL = (
    "If you are Catholic or Christian, Lent and Friday abstinence from meat operate "
    "on the same principle — voluntary restraint that refines the spirit. Apply that "
    "familiar discipline on this day; the form you already know carries the intention."
)

_VRAT_RATIONALE = (
    "Fasting is universal — Islamic Ramadan, Christian Lent, Jewish Yom Kippur, "
    "Buddhist Uposatha and Hindu vrat all use voluntary restraint to clarify body "
    "and mind. Some traditions observe it; none require it. Choose your own level."
)

_DAAN_RATIONALE = (
    "Daan is not Hindu-only. Christianity has limosna and tithing, Islam has zakat "
    "and sadaqah, Judaism has tzedakah, Buddhism has dana (the same Sanskrit root). "
    "The act — give the right thing to the right person on the right day — is "
    "universal; the location is incidental. A coin to someone in need on the street "
    "is as valid as any temple donation."
)

_DAAN_REGIONS = [
    {"region": "South Asia",    "form": "Temple, mandir, dharmshala, or ashram"},
    {"region": "Latin America", "form": "Iglesia, comedor popular, asilo de ancianos, or albergue"},
    {"region": "United States", "form": "Homeless shelter, food bank, senior center, or parish church"},
    {"region": "Middle East",   "form": "Mosque, charitable organization, or refugee aid center"},
    {"region": "Anywhere",      "form": "Directly to a person in need on the street"},
]

_DAAN_FREQUENCY = (
    "Weekly during a dasha; monthly for a natal weakness. Seven consecutive givings "
    "is the traditional minimum."
)


def _yantra(name, ytype, metal_primary, metal_alternate, mantra, alts,
            description, energization, daily_practice, placement, cautions, sourcing):
    return {
        "name": name, "sanskrit": name, "type": ytype,
        "description": description, "why_for_this_user": "",
        "metal_primary": metal_primary, "metal_alternate": metal_alternate,
        "size": "About 7.5cm x 7.5cm (3in) for the altar; a 2.5cm (1in) pendant for wear",
        "placement_traditional": placement,
        "energization": energization, "daily_practice": daily_practice,
        "mantra": mantra,
        "western_alternates": alts,
        "rationale_western": (
            "Sacred geometry is universal. The planet's frequency does not require "
            "Sanskrit to be received — what matters is the metal, the geometric "
            "coherence, and the daily intention. Pick the lineage that resonates "
            "with you; the metal, day, and mantra count stay the same."
        ),
        "cautions": cautions, "sourcing": sourcing,
    }


def _alt(name, description):
    return {"name": name, "description": description}


REMEDY3_LIBRARY = {
    "Sun": {
        "yantra": _yantra(
            "Surya Yantra", "3x3 magic square (every line sums to 15)",
            "Gold", "Copper", "Om Suryaya Namaha",
            [
                _alt("Sun cross / solar wheel", "An equal-armed cross within a circle — the oldest Western solar emblem, carrying the same centred, radiant geometry as the Surya Yantra."),
                _alt("Sun sigil (Hermetic)", "The classical solar glyph (a dot within a circle) engraved on gold or copper — the alchemical carrier of the Sun's frequency."),
                _alt("Sacred Heart medal (Catholic)", "The radiant Sacred Heart echoes solar vitality and the dignified, life-giving centre the Sun rules."),
            ],
            "A 3x3 magic square whose rows, columns and diagonals each sum to 15, engraved on gold or copper. A small altar plate or pendant; expect roughly $15-$120 depending on metal and size.",
            "On a Sunday at sunrise, wash the plate in clean water, place it facing east, light a ghee lamp, and recite Om Suryaya Namaha 108 times with the rising sun in view.",
            "Each morning, glance at the plate, take one slow breath, and silently recite Om Suryaya Namaha three times before the day begins.",
            "East-facing, on the eastern side of the altar or by a window that catches the morning sun.",
            ["A yantra supports practice; it does not replace it.", "Keep it clean and undisturbed — treat it as a focal object, not decoration."],
            "Any reputable metal-craft or devotional shop; for a pendant choose solid gold or copper rather than plated.",
        ),
        "daan": {
            "one_line": "Give golden, warming things to those who carry authority or have renounced it — on Sunday morning.",
            "why_for_this_user": "", "day": "Sunday",
            "best_time": "Sunday morning before noon; the Sun hora at sunrise is best.",
            "items_to_give": [
                {"item": "Wheat", "quantity": "1 kg"},
                {"item": "Jaggery (gur)", "quantity": "250 g"},
                {"item": "Red cloth", "quantity": "1 piece"},
                {"item": "A copper item or coin", "quantity": "1"},
            ],
            "recipients_traditional": [
                "Brahmins or priests", "Your father or father-figures", "Leaders and public servants", "Wandering ascetics",
            ],
            "where_to_give": {
                "traditional": "Hindu temple grounds, a Surya shrine, or an ashram.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "The Sun rules authority, recognition and vitality. Giving warmth and gold-coloured staples honours and redistributes solar dignity.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Sunday — fruits and milk by day, a simple meal, to steady vitality and ego.",
            "why_for_this_user": "", "day": "Sunday",
            "type_traditional": "Sunrise to sunset on fruits and milk only, no salt; a simple meal after sunset.",
            "type_modified": "Skip lunch; a light fruit breakfast and a simple, lightly-salted dinner.",
            "type_minimal": "Eat one less item than usual and choose simpler food. Intention matters more than strictness.",
            "duration": "Minimum 7 consecutive Sundays.",
            "what_to_eat": ["Fresh fruit", "Milk", "A little jaggery", "Wheat-based simple food after sunset"],
            "avoid": ["Salt (traditionally)", "Meat", "Alcohol", "Heavy fried food"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to steady my vitality and quiet my ego.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["Steadier energy and confidence", "A calmer relationship with recognition", "A simple weekly reset"],
        },
    },
    "Moon": {
        "yantra": _yantra(
            "Chandra Yantra", "4x4 magic square",
            "Silver", "Panchadhatu (5-metal alloy)", "Om Chandraya Namaha",
            [
                _alt("Crescent / vesica piscis", "The crescent and the vesica piscis are the West's enduring lunar and feminine geometries — soft, receptive, watery."),
                _alt("Moon sigil (Hermetic)", "The crescent glyph engraved on silver — the alchemical carrier of the Moon's cool, reflective frequency."),
                _alt("Virgin Mary medal (Catholic)", "The Marian medal carries the nurturing, maternal, consoling quality the Moon rules."),
            ],
            "A 4x4 magic square engraved on silver. A small altar plate or pendant; expect roughly $15-$120 depending on metal and size.",
            "On a Monday evening near water or moonlight, wash the plate in milk then water, light a lamp, and recite Om Chandraya Namaha 108 times.",
            "Each evening, hold the plate a moment, breathe slowly, and recite Om Chandraya Namaha three times.",
            "Northwest of the altar, or near a window that receives moonlight.",
            ["A yantra supports practice; it does not replace it.", "Keep silver clean; tarnish dulls the focal quality."],
            "Choose solid silver rather than plated; any reputable devotional or silversmith shop.",
        ),
        "daan": {
            "one_line": "Give rice, milk and white things to mothers and the thirsty — on Monday morning.",
            "why_for_this_user": "", "day": "Monday",
            "best_time": "Monday morning before noon; the Moon hora is best.",
            "items_to_give": [
                {"item": "Rice", "quantity": "1 kg"},
                {"item": "Milk", "quantity": "1 litre"},
                {"item": "White cloth", "quantity": "1 piece"},
                {"item": "Sugar", "quantity": "250 g"},
            ],
            "recipients_traditional": [
                "Mothers and caregivers", "Women in need", "Those who give water to others", "Anyone thirsty or unwell",
            ],
            "where_to_give": {
                "traditional": "A Shiva or Devi temple, or a place that serves water and food.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "The Moon rules the mother principle, comfort and emotional safety. Giving nourishing white staples feeds the Moon's caring quality.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Monday — fruits, milk and curd by day — to soothe the mind.",
            "why_for_this_user": "", "day": "Monday",
            "type_traditional": "Sunrise to sunset on fruits, milk and curd; a simple meal after sunset.",
            "type_modified": "Skip lunch; a light dairy-and-fruit breakfast and a simple dinner.",
            "type_minimal": "Eat one less item than usual and choose simpler, soothing food. Intention over strictness.",
            "duration": "Minimum 7 consecutive Mondays.",
            "what_to_eat": ["Fresh fruit", "Milk and curd", "Rice", "Coconut water"],
            "avoid": ["Salt (traditionally)", "Stale or leftover food", "Alcohol", "Heavy fried food"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to soothe and steady my mind.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["Calmer mood and easier rest", "Less emotional reactivity", "A gentle weekly reset"],
        },
    },
    "Mars": {
        "yantra": _yantra(
            "Mangal Yantra", "Triangular (fire) geometry",
            "Copper", "Gold or panchadhatu", "Om Angarakaya Namaha",
            [
                _alt("Mars sigil (Hermetic)", "The classical Mars glyph engraved on copper — the alchemical carrier of martial drive and protective force."),
                _alt("Pentagram (5-point, fire)", "The upright five-point star, a Western fire-and-protection geometry that mirrors Mars's directed energy."),
                _alt("St. Michael medal (Catholic)", "St. Michael the warrior-archangel carries Mars's protective courage and clean fighting spirit."),
            ],
            "A triangular fire-geometry yantra engraved on copper. A small altar plate or pendant; expect roughly $15-$110 depending on metal and size.",
            "On a Tuesday morning facing south, wash the plate in water, light a lamp, and recite Om Angarakaya Namaha 108 times.",
            "Each morning, look at the plate, take one strong breath, and recite Om Angarakaya Namaha three times.",
            "South-facing, on the southern side of the altar.",
            ["A yantra supports practice; it does not replace it.", "Mars energy is strong — pair the plate with the calming breath rather than over-charging it."],
            "Solid copper is traditional and inexpensive; any reputable metal-craft shop.",
        ),
        "daan": {
            "one_line": "Give red, energetic staples to soldiers, athletes and laborers — on Tuesday.",
            "why_for_this_user": "", "day": "Tuesday",
            "best_time": "Tuesday morning; the Mars hora is best.",
            "items_to_give": [
                {"item": "Red lentils (masoor dal)", "quantity": "500 g"},
                {"item": "Jaggery", "quantity": "250 g"},
                {"item": "A copper item", "quantity": "1"},
                {"item": "Red cloth", "quantity": "1 piece"},
            ],
            "recipients_traditional": [
                "Soldiers and security workers", "Brothers and younger men", "Athletes", "Manual laborers",
            ],
            "where_to_give": {
                "traditional": "A Hanuman or Murugan temple, or a place that serves working men.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "Mars rules courage, energy and the warrior-worker. Giving red, building staples to the physically active settles Mars's charge.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Tuesday — one simple meal — to temper heat into clean drive.",
            "why_for_this_user": "", "day": "Tuesday",
            "type_traditional": "One meal at sunset, no salt, and no grain in some traditions.",
            "type_modified": "Skip lunch; a light breakfast and a simple, low-spice dinner.",
            "type_minimal": "Eat one less item than usual and cut the spice. Intention over strictness.",
            "duration": "Minimum 7 consecutive Tuesdays.",
            "what_to_eat": ["Fruit", "Lentil-based simple food", "Jaggery", "Plenty of water"],
            "avoid": ["Salt (traditionally)", "Red meat", "Alcohol", "Very spicy or fried food"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to temper my heat into clean, aimed energy.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["Cooler temper, cleaner boundaries", "Energy directed by aim, not heat", "A weekly discipline of restraint"],
        },
    },
    "Mercury": {
        "yantra": _yantra(
            "Budh Yantra", "Hexagonal geometry",
            "Brass or gold", "Bronze or panchadhatu", "Om Budhaya Namaha",
            [
                _alt("Caduceus", "The twin-serpent staff is the West's emblem of Mercury — communication, exchange and the meeting of opposites."),
                _alt("Mercury sigil (Hermetic)", "The classical Mercury glyph engraved on brass — the alchemical carrier of intellect and quicksilver clarity."),
                _alt("St. Christopher medal (Catholic)", "St. Christopher, patron of travelers and messengers, carries Mercury's quality of safe passage and clear exchange."),
            ],
            "A hexagonal-geometry yantra engraved on brass or gold. A small altar plate or pendant; expect roughly $15-$120 depending on metal and size.",
            "On a Wednesday morning, wash the plate in water, light a lamp, and recite Om Budhaya Namaha 108 times before any important conversation.",
            "Each morning, glance at the plate, breathe once, and recite Om Budhaya Namaha three times.",
            "North-facing, on the northern side of the altar.",
            ["A yantra supports practice; it does not replace it.", "Keep the plate near your study or work desk for daily contact."],
            "Solid brass or gold; any reputable metal-craft or devotional shop.",
        ),
        "daan": {
            "one_line": "Give green staples and learning materials to students and scholars — on Wednesday.",
            "why_for_this_user": "", "day": "Wednesday",
            "best_time": "Wednesday morning; the Mercury hora is best.",
            "items_to_give": [
                {"item": "Green moong dal", "quantity": "500 g"},
                {"item": "Green leafy vegetables", "quantity": "1 bunch"},
                {"item": "Green cloth", "quantity": "1 piece"},
                {"item": "Books or pens", "quantity": "as you can"},
            ],
            "recipients_traditional": [
                "Students", "Scholars and teachers", "Accountants and clerks", "Writers and scribes",
            ],
            "where_to_give": {
                "traditional": "A temple, a school, or a place of learning.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "Mercury rules intellect, communication and commerce. Giving green staples and learning tools to the studious feeds Mercury.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Wednesday — one light vegetarian meal — to clear the mind.",
            "why_for_this_user": "", "day": "Wednesday",
            "type_traditional": "One meal, green and vegetarian, no meat.",
            "type_modified": "Skip a meal; keep the day light, fresh and vegetarian.",
            "type_minimal": "Eat one less item than usual and keep it fresh and green. Intention over strictness.",
            "duration": "Minimum 7 consecutive Wednesdays.",
            "what_to_eat": ["Green vegetables", "Moong dal", "Fresh salads and sprouts", "Fruit"],
            "avoid": ["Meat", "Heavy or stale food", "Alcohol", "Over-rich dishes"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to clear and sharpen my mind.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["Clearer thinking and speech", "Lighter, more focused energy", "A fresh weekly reset"],
        },
    },
    "Jupiter": {
        "yantra": _yantra(
            "Guru Yantra", "4x4 magic square",
            "Gold", "Panchadhatu", "Om Gurave Namaha",
            [
                _alt("Hexagram / Solomon's Seal", "The six-point star, the West's emblem of divine wisdom and the union of heaven and earth — Jupiter's expansive grace."),
                _alt("Jupiter sigil (Hermetic)", "The classical Jupiter glyph engraved on gold — the alchemical carrier of fortune, growth and benevolence."),
                _alt("St. Anthony medal (Catholic)", "St. Anthony, the great teacher and finder of what is lost, carries Jupiter's guiding, restoring wisdom."),
            ],
            "A 4x4 magic square engraved on gold. A small altar plate or pendant; expect roughly $20-$150 depending on metal and size.",
            "On a Thursday morning facing northeast, wash the plate in water, light a ghee lamp, and recite Om Gurave Namaha 108 times.",
            "Each morning, look at the plate, breathe once with gratitude, and recite Om Gurave Namaha three times.",
            "Northeast-facing, on the northeastern side of the altar.",
            ["A yantra supports practice; it does not replace it.", "Thursday is the ideal day to keep it clean and re-light its lamp."],
            "Solid gold or gold-plated brass; any reputable devotional shop.",
        ),
        "daan": {
            "one_line": "Give yellow staples and books to teachers, gurus and students — on Thursday.",
            "why_for_this_user": "", "day": "Thursday",
            "best_time": "Thursday morning; the Jupiter hora is best.",
            "items_to_give": [
                {"item": "Chana dal", "quantity": "500 g"},
                {"item": "Turmeric", "quantity": "100 g"},
                {"item": "Yellow cloth", "quantity": "1 piece"},
                {"item": "Bananas", "quantity": "a bunch"},
            ],
            "recipients_traditional": [
                "Teachers and mentors", "Priests and clergy", "Gurus and spiritual guides", "Students",
            ],
            "where_to_give": {
                "traditional": "A temple, an ashram, or a place of teaching.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "Jupiter rules wisdom, growth and the wisdom-givers. Giving yellow staples and learning to teachers feeds Jupiter most directly.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Thursday — one meal, no grain, fruit and banana — to invite growth.",
            "why_for_this_user": "", "day": "Thursday",
            "type_traditional": "One meal, no grains, banana and fruits.",
            "type_modified": "Skip lunch; a light fruit breakfast and a simple grain-free dinner.",
            "type_minimal": "Eat one less item than usual and favour fruit. Intention over strictness.",
            "duration": "Minimum 7 consecutive Thursdays.",
            "what_to_eat": ["Banana and fruit", "Milk", "A little ghee", "Yellow foods like chana"],
            "avoid": ["Grains (traditionally)", "Alcohol", "Refined sugar", "Leftover food"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to make room for growth and grace.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["A sense of opening and optimism", "More room for growth", "A weekly practice of faith"],
        },
    },
    "Venus": {
        "yantra": _yantra(
            "Shukra Yantra", "7x7 geometry",
            "Silver or platinum", "White gold or panchadhatu", "Om Shukraya Namaha",
            [
                _alt("Rose cross", "The rose upon the cross, a Western emblem of beauty, love and refined feeling — Venus's harmonising grace."),
                _alt("Venus sigil (Hermetic)", "The classical Venus glyph engraved on silver — the alchemical carrier of love, beauty and value."),
                _alt("Virgin of Guadalupe medal (Catholic)", "The Guadalupana carries Venus's tender, beautiful, devotional feminine grace, deeply loved across Latin America."),
            ],
            "A 7x7 geometry yantra engraved on silver or platinum. A small altar plate or pendant; expect roughly $20-$160 depending on metal and size.",
            "On a Friday morning facing southeast, wash the plate in rose water then clean water, light a lamp, and recite Om Shukraya Namaha 108 times.",
            "Each day, glance at the plate, breathe softly, and recite Om Shukraya Namaha three times.",
            "Southeast-facing, on the southeastern side of the altar.",
            ["A yantra supports practice; it does not replace it.", "Keep it with something fragrant or floral to honour Venus's quality."],
            "Solid silver or platinum; any reputable silversmith or devotional shop.",
        ),
        "daan": {
            "one_line": "Give sweet, white and beautiful things to women, girls and artists — on Friday.",
            "why_for_this_user": "", "day": "Friday",
            "best_time": "Friday morning or early evening; the Venus hora is best.",
            "items_to_give": [
                {"item": "Rice", "quantity": "1 kg"},
                {"item": "Sugar or white sweets", "quantity": "250 g"},
                {"item": "Perfume or flowers", "quantity": "1"},
                {"item": "White cloth", "quantity": "1 piece"},
            ],
            "recipients_traditional": [
                "Women and girls", "Brides and young mothers", "Artists and musicians", "Performers",
            ],
            "where_to_give": {
                "traditional": "A Lakshmi or Devi temple, or a place that supports women and the arts.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "Venus rules beauty, the feminine and the arts. Giving sweet, beautiful things to those who embody them feeds Venus.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Friday — one white, simple meal — to restore sweetness and harmony.",
            "why_for_this_user": "", "day": "Friday",
            "type_traditional": "One meal of white food (rice and milk), no spice.",
            "type_modified": "Skip a meal; keep the day's food simple, white and mild.",
            "type_minimal": "Eat one less item than usual and keep it mild. Intention over strictness.",
            "duration": "Minimum 7 consecutive Fridays.",
            "what_to_eat": ["Rice", "Milk and mild dairy", "Sweet fruit", "A little sugar or jaggery"],
            "avoid": ["Heavy spice", "Garlic (traditionally)", "Alcohol", "Sour ferments"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to restore sweetness and harmony.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["More ease and sweetness in relating", "A softer, more harmonious week", "A gentle aesthetic reset"],
        },
    },
    "Saturn": {
        "yantra": _yantra(
            "Shani Yantra", "5x5 magic square (every row, column and diagonal sums to 15)",
            "Silver or iron", "Iron (most traditional) or copper", "Om Sham Shanaye Namaha",
            [
                _alt("Sator Square", "A Latin 5x5 word square found in 1st-century Roman ruins (SATOR AREPO TENET OPERA ROTAS), mathematically and structurally equivalent to the Shani Yantra — a palindromic grid of disciplined order."),
                _alt("Saturn sigil (Hermetic)", "The classical Saturn glyph engraved on lead or iron — the alchemical carrier of Saturn's slow, structuring frequency."),
                _alt("St. Joseph medal (Catholic)", "St. Joseph, patron of patient labor, quiet discipline and the working craftsman, carries exactly Saturn's virtues."),
            ],
            "A 5x5 magic square whose every row, column and diagonal sums to 15, engraved on silver or iron. A small altar plate or pendant; expect roughly $15-$120 depending on metal and size.",
            "On a Saturday before sunrise, wash the plate in water, place it facing west, light a sesame-oil lamp, and recite Om Sham Shanaye Namaha 108 times silently.",
            "Each evening before sunset, touch the plate, take one long slow breath, and recite Om Sham Shanaye Namaha three times.",
            "Northwest corner of the altar, facing east.",
            ["A yantra supports practice; it does not replace it.", "Iron is the most traditional metal but rusts — keep it dry and oiled.", "Treat it as a focal object, kept clean and undisturbed."],
            "Iron or silver from any reputable metal-craft shop; the Sator Square can also be hand-engraved on an iron disc.",
        ),
        "daan": {
            "one_line": "Give dark, grounding staples to the elderly, laborers and the marginalized — on Saturday.",
            "why_for_this_user": "", "day": "Saturday",
            "best_time": "Saturday morning before noon; during the Saturn hora is best.",
            "items_to_give": [
                {"item": "Black sesame seeds (til)", "quantity": "250 g"},
                {"item": "Urad dal (black lentils)", "quantity": "250 g"},
                {"item": "Mustard oil", "quantity": "500 ml"},
                {"item": "An iron item", "quantity": "1"},
                {"item": "A black blanket", "quantity": "1"},
            ],
            "recipients_traditional": [
                "Elderly people, especially anyone older than your father",
                "Manual laborers and day-wage workers",
                "Beggars and those who ask",
                "The marginalized and overlooked",
            ],
            "where_to_give": {
                "traditional": "Hindu temple grounds, a Shani Mandir, or an ashram.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "Saturn rules age, labor, patience and karmic weight. Giving dark, grounding staples to those who already carry weight discharges Saturn karma.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Saturday — one simple meal, the discipline that builds patience over time.",
            "why_for_this_user": "", "day": "Saturday",
            "type_traditional": "Eka-bhukta (one meal) at sunset, simple khichdi, no salt.",
            "type_modified": "Skip lunch; a simple breakfast and a light, lightly-salted dinner. No strict no-salt rule.",
            "type_minimal": "Eat one less item than usual and choose simpler food. Intention matters more than strictness.",
            "duration": "Minimum 7 consecutive Saturdays. 49 Saturdays for full Sade Sati support.",
            "what_to_eat": ["Simple khichdi", "Whole grains like millet or barley", "Sesame", "Water and warm fluids"],
            "avoid": ["Salt (traditionally)", "Sugar and refined food", "Alcohol", "Late-night eating after sunset"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to build patience, structure and endurance.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["Greater patience and steadiness", "A trained capacity for restraint", "Support through Saturn's pressure periods"],
        },
    },
    "Rahu": {
        "yantra": _yantra(
            "Rahu Yantra", "Bindu (central-dot) point pattern",
            "Silver / panchadhatu", "Ashtadhatu (8-metal alloy)", "Om Rahave Namaha",
            [
                _alt("Ouroboros", "The serpent swallowing its own tail — the West's emblem of cycles, hunger and the endless turning Rahu rules."),
                _alt("Dragon's Head sigil", "In Western astrology Rahu is the Dragon's Head (Caput Draconis); its sigil engraved on silver carries the node's forward pull."),
                _alt("St. Jude medal (Catholic)", "St. Jude, patron of lost and desperate causes, carries Rahu's themes of the outsider and the seemingly impossible."),
            ],
            "A bindu (central-dot) point-pattern yantra engraved on silver or panchadhatu. A small altar plate or pendant; expect roughly $15-$120 depending on metal and size.",
            "On a Saturday at dusk facing southwest, wash the plate in water, light a lamp, and recite Om Rahave Namaha 108 times.",
            "Each day, look at the central point, breathe slowly to settle, and recite Om Rahave Namaha three times.",
            "Southwest-facing, on the southwestern side of the altar.",
            ["A yantra supports practice; it does not replace it.", "Rahu is unsettling energy — pair the plate with grounding breath, not over-charging."],
            "Silver or panchadhatu from a reputable devotional shop; nodal yantras are best sourced certified.",
        ),
        "daan": {
            "one_line": "Give dark, warming things to outcasts, the homeless and foreigners — on Saturday, in Rahu Kalam.",
            "why_for_this_user": "", "day": "Saturday (during Rahu Kalam)",
            "best_time": "Saturday during Rahu Kalam, the daily 1.5-hour Rahu window.",
            "items_to_give": [
                {"item": "A black blanket", "quantity": "1"},
                {"item": "Mustard oil", "quantity": "500 ml"},
                {"item": "Incense / smoke offering", "quantity": "1 pack"},
                {"item": "Black sesame", "quantity": "250 g"},
            ],
            "recipients_traditional": [
                "Outcasts and the socially excluded", "The homeless", "The chronically ill and shunned", "Foreigners and migrants",
            ],
            "where_to_give": {
                "traditional": "Given directly in Rahu Kalam — to stray dogs, beggars, or temple sweepers.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "Rahu rules the outsider, the foreign and the marginalized. Feeding and clothing those at the edges grounds Rahu's restless charge.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Saturday — a short, complete fast in Rahu Kalam — to settle scattered energy.",
            "why_for_this_user": "", "day": "Saturday (during Rahu Kalam)",
            "type_traditional": "A complete 1.5-hour fast during Rahu Kalam.",
            "type_modified": "Eat nothing through the Rahu Kalam window; keep the rest of the day simple.",
            "type_minimal": "During Rahu Kalam, pause eating and sit quietly for a few minutes. Intention over strictness.",
            "duration": "Minimum 7 consecutive Saturdays.",
            "what_to_eat": ["Outside Rahu Kalam: simple grounding food", "Khichdi", "Water", "Warm, settling fluids"],
            "avoid": ["Onion and garlic (traditionally)", "Alcohol and substances", "Processed food", "Important new ventures during Rahu Kalam"],
            "intention": "Set silently at sunrise: 'During Rahu Kalam I pause and restrict, to settle my scattered energy.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["Calmer, less anxious energy", "Less compulsive chasing", "A grounded weekly pause"],
        },
    },
    "Ketu": {
        "yantra": _yantra(
            "Ketu Yantra", "Triangular (descending) geometry",
            "Silver / panchadhatu", "Ashtadhatu (8-metal alloy)", "Om Ketave Namaha",
            [
                _alt("Ouroboros (tail)", "The serpent's tail half of the Ouroboros — the West's emblem of completion, release and what falls away, which Ketu rules."),
                _alt("Dragon's Tail sigil", "In Western astrology Ketu is the Dragon's Tail (Cauda Draconis); its sigil engraved on silver carries the node's letting-go."),
                _alt("St. Francis medal (Catholic)", "St. Francis, who renounced wealth for simplicity and the spirit, carries Ketu's detachment and inward turn."),
            ],
            "A descending-triangle geometry yantra engraved on silver or panchadhatu. A small altar plate or pendant; expect roughly $15-$120 depending on metal and size.",
            "On a Tuesday or Thursday evening in stillness, wash the plate in water, light a lamp, and recite Om Ketave Namaha 108 times.",
            "Each evening, rest your gaze on the plate, breathe and let go, and recite Om Ketave Namaha three times.",
            "On the altar in a quiet corner; Ketu does not require a fixed direction.",
            ["A yantra supports practice; it does not replace it.", "Ketu's quality is renunciation — keep the plate simple and undecorated."],
            "Silver or panchadhatu from a reputable devotional shop.",
        ),
        "daan": {
            "one_line": "Give simple, ascetic things to sadhus and spiritual seekers — on Tuesday or Thursday.",
            "why_for_this_user": "", "day": "Tuesday or Thursday",
            "best_time": "Tuesday or Thursday, in a quiet part of the day.",
            "items_to_give": [
                {"item": "A brown or grey blanket", "quantity": "1"},
                {"item": "Red lentils (masoor)", "quantity": "500 g"},
                {"item": "Sesame", "quantity": "250 g"},
            ],
            "recipients_traditional": [
                "Sadhus and renunciates", "Ascetics and monks", "Those on a spiritual path", "The quietly devout",
            ],
            "where_to_give": {
                "traditional": "An ashram, a monastery, or wherever renunciates gather.",
                "universal": "Anywhere people in need actually are — your local context determines the form, not the principle.",
                "examples_by_region": _DAAN_REGIONS,
            },
            "principle": "Ketu rules detachment, the spiritual and what falls away. Giving simple things to those who have renounced feeds Ketu.",
            "rationale_universal": _DAAN_RATIONALE, "frequency": _DAAN_FREQUENCY,
        },
        "vrat": {
            "one_line": "Voluntary restraint on Tuesday or Thursday — a half-day fast, simple food — for focus and detachment.",
            "why_for_this_user": "", "day": "Tuesday or Thursday",
            "type_traditional": "Half-day fast, then simple sattvic food.",
            "type_modified": "Skip one meal; keep the day's food plain and minimal.",
            "type_minimal": "Eat one less item than usual and keep it simple. Intention over strictness.",
            "duration": "Minimum 7 consecutive observances on your chosen day.",
            "what_to_eat": ["Simple sattvic food", "Fruit", "Sabudana or fasting grains", "Water"],
            "avoid": ["Heavy meats", "Alcohol", "Over-eating", "Complex, heavily-spiced dishes"],
            "intention": "Set silently at sunrise: 'I voluntarily restrict today to sharpen my focus and loosen my grip.'",
            "medical_disclaimer": _VRAT_MED_DISCLAIMER, "catholic_parallel": _VRAT_CATHOLIC_PARALLEL,
            "rationale_universal": _VRAT_RATIONALE,
            "benefits": ["Sharper focus and inner quiet", "An easier time letting go", "A weekly turn inward"],
        },
    },
}

# Attach yantra / daan / vrat to every PRACTICE_LIBRARY entry (all 9 planets).
for _r3p, _r3data in REMEDY3_LIBRARY.items():
    if _r3p in PRACTICE_LIBRARY:
        for _rk in ("yantra", "daan", "vrat"):
            PRACTICE_LIBRARY[_r3p][_rk] = _r3data[_rk]


_REMEDY3_KEYS = ("yantra", "daan", "vrat")


def build_remedy_response(remedy_type, planet, language="en"):
    """Independent deep copy of one planet's yantra / daan / vrat block."""
    if remedy_type not in _REMEDY3_KEYS:
        return None
    block = (PRACTICE_LIBRARY.get(planet) or {}).get(remedy_type)
    if not block:
        return None
    return _r3_copy.deepcopy(block)


def build_remedy_personalization(remedy_type, planet, scope, chart=None,
                                 conditions=None, language="en"):
    """Chart-aware why_for_this_user for yantra / daan / vrat, framed by scope."""
    cond = ((conditions or {}).get(planet) or {}).get("condition")
    weak = isinstance(cond, str) and cond.lower() in (
        "debilitated", "combust", "weak", "afflicted", "fallen", "enemy")
    cc = f" (currently {_cond_plain(cond)} in your chart)" if weak else ""

    if remedy_type == "yantra":
        body = ("this yantra is a daily geometric anchor — energize it once and let it "
                "hold a steadying frequency in your space while your practice does the deeper work")
    elif remedy_type == "daan":
        body = ("giving the right thing to the right person on the remedy's own day discharges "
                "the old pattern directly — the most active remedy in the stack, and it costs only intention")
    else:  # vrat
        body = ("a voluntary one-day fast on the remedy's day builds the discipline this energy "
                "rewards — keep it gentle and safe; intention matters far more than strictness")

    if scope == "dasha_period":
        return f"You are in a chapter that leans on {_prose_energy(planet)}{cc} — {body}."
    if scope == "varshphal_year":
        return f"This year highlights {_prose_energy(planet)}{cc} — {body}."
    return f"The part of you that carries {_prose_energy(planet)} runs weak in your birth chart{cc}. Here {body}."


def personalize_remedy(remedy_type, planet, scope="natal_weakness", language="en",
                       chart=None, conditions=None):
    """PRACTICE_LIBRARY[planet][remedy_type] (deep copy) with why_for_this_user set."""
    base = build_remedy_response(remedy_type, planet, language)
    if not base:
        return None
    base["why_for_this_user"] = build_remedy_personalization(
        remedy_type, planet, scope, chart=chart, conditions=conditions, language=language)
    return base
