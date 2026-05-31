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
        "why_this_works": {"en": "The Sun rules the steady core of confidence and vitality. When weak, the self dims and recognition won't land. The seed mantra rekindles that central fire, the morning movement floods the body with light, and the Lal Kitab offering discharges the debt that keeps the Sun shadowed.",
                          "es": "El Sol rige el núcleo estable de la confianza y la vitalidad. Cuando está débil, el yo se atenúa y el reconocimiento no llega. El mantra semilla reaviva ese fuego central, el movimiento matinal inunda el cuerpo de luz, y la ofrenda de Lal Kitab descarga la deuda que mantiene al Sol en sombra."},
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
        "why_this_works": {"en": "The Moon rules the emotional baseline and the felt sense of safety. When weak, the mind churns and rest won't come. The mantra steadies the inner tide, the restorative posture signals safety to the nervous system, and the silver and milk are the Lal Kitab way of feeding the Moon.",
                          "es": "La Luna rige la base emocional y la sensación de seguridad. Cuando está débil, la mente se agita y el descanso no llega. El mantra calma la marea interior, la postura restaurativa le indica seguridad al sistema nervioso, y la plata y la leche son la forma de Lal Kitab de alimentar a la Luna."},
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
        "why_this_works": {"en": "Mars rules drive and clean boundaries. When weak, energy leaks and force turns to friction. The mantra tempers the fire, the strong stance retrains controlled power, and the Tuesday offering settles Mars's karmic charge the Lal Kitab way.",
                          "es": "Marte rige el impulso y los límites limpios. Cuando está débil, la energía se filtra y la fuerza se vuelve fricción. El mantra templa el fuego, la postura firme reentrena el poder controlado, y la ofrenda del martes asienta la carga kármica de Marte al modo de Lal Kitab."},
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
        "why_this_works": {"en": "Mercury rules the channels through which thought becomes word and word becomes action. When weak, those channels jam. The mantra clears the seed-vibration, the breath rebalances the hemispheres, and the daily action discharges Mercury's karmic debts in Lal Kitab form.",
                          "es": "Mercurio rige los canales por los que el pensamiento se vuelve palabra y la palabra se vuelve acción. Cuando está débil, esos canales se atascan. El mantra limpia la vibración semilla, la respiración reequilibra los hemisferios, y la acción diaria descarga las deudas kármicas de Mercurio al modo de Lal Kitab."},
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
        "why_this_works": {"en": "Jupiter rules expansion and grace. When weak, the world feels stingy and growth dries up. The mantra reopens the channel of fortune, the balancing posture trains steady uprightness, and the Thursday giving discharges Jupiter's debt the Lal Kitab way — generosity restores the flow.",
                          "es": "Júpiter rige la expansión y la gracia. Cuando está débil, el mundo se siente tacaño y el crecimiento se seca. El mantra reabre el canal de la fortuna, la postura de equilibrio entrena una verticalidad estable, y la entrega del jueves descarga la deuda de Júpiter al modo de Lal Kitab — la generosidad restaura el flujo."},
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
        "why_this_works": {"en": "Venus rules sweetness, relating, and the flow of value. When weak, connection and pleasure go flat. The mantra restores the seed-tone of harmony, the heart-opening posture softens defended places, and the Friday giving settles Venus's debt the Lal Kitab way.",
                          "es": "Venus rige la dulzura, el vínculo y el flujo del valor. Cuando está débil, la conexión y el placer se apagan. El mantra restaura el tono semilla de la armonía, la postura que abre el pecho ablanda lo defendido, y la entrega del viernes asienta la deuda de Venus al modo de Lal Kitab."},
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
        "why_this_works": {"en": "Saturn rules slow-build, structure, and patience. When weak, time itself feels antagonistic — deadlines slip, momentum dies. The mantra is the seed sound of Saturn's energy; the daily action discharges karmic debt the way Lal Kitab prescribes; the body practice trains the nervous system to settle into Saturn's rhythm. None of this is fast. That's the point.",
                          "es": "Saturno rige la construcción lenta, la estructura y la paciencia. Cuando está débil, el tiempo mismo se siente antagonista — los plazos resbalan, el impulso muere. El mantra es el sonido semilla de la energía de Saturno; la acción diaria descarga la deuda kármica como prescribe Lal Kitab; la práctica corporal entrena al sistema nervioso a asentarse en el ritmo de Saturno. Nada de esto es rápido. Ese es el punto."},
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
        "why_this_works": {"en": "Rahu rules hunger and the pull toward the new. When agitated, it scatters the mind into anxious chasing. The mantra contains the static, the inversion drains the over-revved nervous system, and feeding crows is the Lal Kitab way of settling Rahu's restless charge.",
                          "es": "Rahu rige el hambre y el tirón hacia lo nuevo. Cuando se agita, dispersa la mente en una persecución ansiosa. El mantra contiene la estática, la inversión drena el sistema nervioso sobreacelerado, y alimentar cuervos es la forma de Lal Kitab de asentar la carga inquieta de Rahu."},
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
        "why_this_works": {"en": "Ketu rules release and the inward turn. When unsettled, it leaves you rootless and scattered. The mantra steadies the dispersing energy, the forward fold returns you to the ground, and the quiet practice gives Ketu its proper channel — focus through surrender, not grasping.",
                          "es": "Ketu rige la liberación y el giro hacia adentro. Cuando está inquieto, te deja sin raíces y disperso. El mantra calma la energía que se dispersa, el pliegue hacia adelante te devuelve al suelo, y la práctica silenciosa le da a Ketu su canal propio — enfoque a través de la entrega, no del aferramiento."},
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
        "sanskrit": m.get("sanskrit"),
        "transliteration": m.get("translit"),
        "count": m.get("count"),
        "duration_minutes": m.get("duration_minutes"),
        "when": m.get("when"),
        "audio_url": f"{AUDIO_BASE}/{audio_path}-{lang}.mp3",
        "tone_hz": entry.get("frequency_hz"),
    }


def get_planet_content(planet: str, language: str = "en") -> dict:
    """Localised content block for one planet — every piece from the same entry."""
    entry = PRACTICE_LIBRARY.get(planet)
    if not entry:
        return {}
    da = entry["daily_action"]
    return {
        "what_it_governs": _loc(entry["what_it_governs"], language),
        "when_weak_symptoms": _loc(entry["when_weak_symptoms"], language),
        "mantra": build_mantra_response(planet, language),
        "body": dict(entry["body"]),
        "breath": dict(entry["breath"]),
        "daily_action": {"title": da["title"], "detail": _loc(da["detail"], language), "frequency": da["frequency"]},
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
    cond_clause = f" (currently reading as {cond})" if weak else ""

    if scope == "dasha_period":
        return (f"You are in a {planet} period right now{cond_clause} — {stone} prepares the "
                f"body and mind for this chapter. The mantra comes first; the stone is an "
                f"optional amplifier, never a replacement.")
    if scope == "varshphal_year":
        return (f"{planet} is emphasised in your year ahead{cond_clause} — {stone} is a "
                f"year-bounded support, not a permanent fixture. Begin with the mantra; the "
                f"stone is optional.")
    # natal_weakness (permanent recommendation) and any default.
    return (f"{planet} is weak in your birth chart{cond_clause}. Your daily practice already "
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
    cond_clause = f" (currently {cond} in your chart)" if weak else ""

    if scope == "dasha_period":
        return (f"You are in a {planet} period right now{cond_clause} — {planet} food prepares the "
                f"body for the period's quality. Food is the most consistent daily lever you have; "
                f"every meal is a small recalibration of {planet}'s energy.")
    if scope == "varshphal_year":
        return (f"This year's annual chart highlights {planet}{cond_clause} — {planet}-aligned food "
                f"supports the year ahead. Small daily shifts in what you eat compound over the months.")
    # natal_weakness (default).
    return (f"{planet} is weak in your birth chart{cond_clause}. Food is the most consistent daily "
            f"lever you have — every meal is a small recalibration of {planet}'s quality in your body.")


def personalize_food(planet, scope="natal_weakness", language="en", chart=None, conditions=None):
    """PRACTICE_LIBRARY[planet]['food'] (deep copy) with why_for_this_user personalised."""
    base = build_food_response(planet, language)
    if not base:
        return None
    base["why_for_this_user"] = build_food_personalization(
        planet, scope, chart=chart, conditions=conditions, language=language)
    return base
