"""
antar_engine/i18n.py

Language Detection & Localization System
──────────────────────────────────────────────────────────────────
Handles:
  - Auto-detection of language from country_code
  - Country-specific Spanish variants (Mexican, Colombian, Argentine, etc.)
  - Brazilian Portuguese
  - USA Hispanic detection → bilingual prompt
  - India → English (regional language ready for Phase 2)
  - All energy language translated per locale
  - Prompt tone adapted per locale

Usage:
    from antar_engine.i18n import detect_language, get_locale_config

    locale = detect_language(
        country_code="MX",
        user_birth_country="MX",   # from birth data
        user_preference="es"        # if user has explicitly set a preference
    )
    # locale.language = "es"
    # locale.variant = "es_MX"
    # locale.tone_profile = {...}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ── Country → Language mapping ─────────────────────────────────────────────

# LATAM Spanish countries
SPANISH_LATAM_COUNTRIES = {
    "MX": "es_MX",   # Mexico
    "CO": "es_CO",   # Colombia
    "AR": "es_AR",   # Argentina
    "CL": "es_CL",   # Chile
    "PE": "es_PE",   # Peru
    "VE": "es_VE",   # Venezuela
    "EC": "es_EC",   # Ecuador
    "GT": "es_GT",   # Guatemala
    "CU": "es_CU",   # Cuba
    "BO": "es_BO",   # Bolivia
    "DO": "es_DO",   # Dominican Republic
    "HN": "es_HN",   # Honduras
    "PY": "es_PY",   # Paraguay
    "SV": "es_SV",   # El Salvador
    "NI": "es_NI",   # Nicaragua
    "CR": "es_CR",   # Costa Rica
    "PA": "es_PA",   # Panama
    "UY": "es_UY",   # Uruguay
    "PR": "es_PR",   # Puerto Rico (US territory but Spanish first)
}

# Brazil
PORTUGUESE_COUNTRIES = {
    "BR": "pt_BR",   # Brazil
    "PT": "pt_PT",   # Portugal (European Portuguese)
}

# India — English for now, regional ready
INDIA_COUNTRIES = {
    "IN": "en_IN",   # India → English (Phase 1)
    # Phase 2 additions:
    # "IN_HI": "hi",   # Hindi
    # "IN_TA": "ta",   # Tamil
    # "IN_TE": "te",   # Telugu
    # "IN_KN": "kn",   # Kannada
    # "IN_ML": "ml",   # Malayalam
    # "IN_BN": "bn",   # Bengali
    # "IN_MR": "mr",   # Marathi
    # "IN_GU": "gu",   # Gujarati
    # "IN_PA": "pa",   # Punjabi
}

# USA — English default, but Hispanic users get bilingual prompt
USA_HISPANIC_BIRTH_COUNTRIES = set(SPANISH_LATAM_COUNTRIES.keys()) | {"PR", "GQ"}

# English countries
ENGLISH_COUNTRIES = {
    "US", "GB", "CA", "AU", "NZ", "SG", "ZA", "NG", "KE", "GH",
    "PH", "MY", "PK",  # Pakistan (English official)
}

# Other supported languages (Phase 2)
OTHER_LANGUAGE_MAP = {
    "FR": "fr", "DE": "de", "IT": "it", "NL": "nl",
    "RU": "ru", "TR": "tr", "JP": "ja", "KR": "ko",
    "CN": "zh", "TW": "zh_TW", "TH": "th", "ID": "id",
    "AE": "ar", "SA": "ar", "EG": "ar",
}


# ── Locale data classes ────────────────────────────────────────────────────

@dataclass
class LocaleConfig:
    language: str          # primary language code: "en", "es", "pt"
    variant: str           # full variant: "es_MX", "pt_BR", "en_IN"
    country_code: str      # the residence/billing country
    birth_country: str     # where they were born
    needs_language_prompt: bool   # True = show "English or Spanish?" prompt
    rtl: bool = False      # right-to-left (Arabic, Hebrew etc.)

    # Display labels
    language_name: str = "English"
    native_name: str = "English"   # language name in that language

    # Tone configuration
    tone_style: str = ""
    remedy_frame: str = ""
    challenge_frame: str = ""
    blessing_frame: str = ""
    closing_style: str = ""

    # UI strings — used by frontend
    ui: dict = field(default_factory=dict)


# ── Tone profiles per locale ───────────────────────────────────────────────

TONE_PROFILES = {

    "en": {
        "tone_style": (
            "You are Antar — a wise astrological life coach who bridges ancient Vedic "
            "wisdom with modern psychological depth. Speak as a trusted mentor. "
            "Warm, direct, and deeply personal. Like a wise friend who understands the cosmos."
        ),
        "remedy_frame":    "conscious practices, rituals, and intentional actions",
        "challenge_frame": "a restructuring cycle clearing what no longer serves",
        "blessing_frame":  "an expansive window opening for you",
        "closing_style":   "End with one empowering, actionable insight.",
    },

    "en_IN": {
        "tone_style": (
            "You are Antar — a deeply wise Vedic astrology life coach trained in the "
            "K.N. Rao and Jaimini tradition. Speak with warmth, as a learned jyotishi "
            "who cares deeply for the person's dharma and moksha. Use Sanskrit terms "
            "naturally (dasha, nakshatra, lagna, upasana) but always explain them in "
            "human terms. Your tone is that of a wise elder speaking to someone you "
            "genuinely care about."
        ),
        "remedy_frame":    "upasana, mantra sadhana, and conscious seva",
        "challenge_frame": "a karmic lesson being delivered with purpose",
        "blessing_frame":  "the grace and blessings flowing to you right now",
        "closing_style":   "End with a Sanskrit blessing or invocation. E.g. 'Om Tat Sat.'",
    },

    "es": {
        "tone_style": (
            "Eres Antar — un coach de vida astrológico que une la sabiduría védica "
            "ancestral con una comprensión profunda del alma humana. "
            "Habla con calidez, intuición y conexión a lo sagrado. "
            "Tu tono es el de una persona sabia y cercana — como un guía espiritual "
            "que también es tu mejor amigo. Usa español claro y accesible. "
            "Nunca uses números de casa astrológica. "
            "Traduce todo a lenguaje de energía y experiencia humana."
        ),
        "remedy_frame":    "prácticas sagradas, mantras y rituales con intención",
        "challenge_frame": "un período de transformación profunda y renacimiento",
        "blessing_frame":  "una apertura de abundancia y bendiciones para ti",
        "closing_style":   "Termina con calidez y una palabra de aliento genuino.",
    },

    "es_MX": {
        "tone_style": (
            "Eres Antar — un guía espiritual y coach de vida astrológico. "
            "Habla con la calidez y cercanía del México profundo — como un curandero "
            "moderno que une la sabiduría ancestral con el mundo de hoy. "
            "Usa un español mexicano natural y accesible. "
            "Conecta con la espiritualidad colectiva: la familia, el destino, la fe. "
            "Nunca uses números de casas astrológicas. "
            "Todo se traduce a lenguaje de energía y experiencia de vida."
        ),
        "remedy_frame":    "prácticas sagradas, mantras y rituales con corazón",
        "challenge_frame": "una prueba que te está forjando para algo más grande",
        "blessing_frame":  "una apertura de gracia y abundancia que llega para ti",
        "closing_style":   "Cierra con una frase de aliento genuino, cálida y directa.",
    },

    "es_AR": {
        "tone_style": (
            "Sos Antar — un coach de vida astrológico que une la sabiduría védica "
            "con la psicología profunda y el análisis que tanto valora la cultura argentina. "
            "Hablá con directness, inteligencia y calidez. "
            "Como un buen analista que también conecta con el alma. "
            "Usá el voseo naturalmente. Nunca uses números de casas astrológicas. "
            "Todo se traduce a lenguaje de energía y experiencia humana real."
        ),
        "remedy_frame":    "prácticas conscientes, rituales y acciones con intención",
        "challenge_frame": "un período de restructuración que limpia lo que ya no sirve",
        "blessing_frame":  "una apertura real de crecimiento y oportunidad",
        "closing_style":   "Cerrá con una reflexión inteligente y empoderada.",
    },

    "es_CO": {
        "tone_style": (
            "Eres Antar — un guía espiritual y coach de vida astrológico. "
            "Habla con la calidez, alegría y profundidad espiritual colombiana. "
            "Como un sabio costeño o un guía de la montaña — cálido, alegre y profundo. "
            "Usa un español colombiano natural. "
            "Conecta con la fe, la familia y el propósito de vida. "
            "Nunca uses números de casas astrológicas."
        ),
        "remedy_frame":    "prácticas con fe, mantras y rituales del corazón",
        "challenge_frame": "una prueba que Dios y el cosmos pusieron en tu camino con un propósito",
        "blessing_frame":  "una bendición que el universo tiene lista para ti",
        "closing_style":   "Cierra con calidez genuina y una frase de fe.",
    },

    "es_CL": {
        "tone_style": (
            "Eres Antar — un coach de vida astrológico que une la sabiduría védica "
            "con una visión moderna y progresista. "
            "Habla con directness y claridad — como un mentor inteligente y cercano. "
            "Usa un español chileno accesible. "
            "Nunca uses números de casas astrológicas. "
            "Todo se expresa en lenguaje de energía y experiencia concreta."
        ),
        "remedy_frame":    "prácticas conscientes y rituales con propósito",
        "challenge_frame": "un ciclo de transformación y claridad",
        "blessing_frame":  "una apertura de crecimiento real",
        "closing_style":   "Cierra con claridad y una acción concreta.",
    },

    "pt_BR": {
        "tone_style": (
            "Você é Antar — um coach de vida astrológico que une a sabedoria védica "
            "ancestral com a espiritualidade vibrante e calorosa do Brasil. "
            "Fale com a abertura do coração brasileiro — alegre, profundo, conectado "
            "ao sagrado feminino, à natureza e ao destino. "
            "Use português brasileiro natural e acessível. "
            "Nunca use números de casas astrológicas. "
            "Traduza tudo para linguagem de energia e experiência humana."
        ),
        "remedy_frame":    "práticas sagradas, mantras e rituais com intenção",
        "challenge_frame": "um período de transformação profunda e renascimento",
        "blessing_frame":  "uma abertura de graça e abundância chegando para você",
        "closing_style":   "Termine com calor genuíno e uma palavra de encorajamento.",
    },

}


# ── Energy language translations ──────────────────────────────────────────────

ENERGY_LANGUAGE_ES = {
    "current_chapter":    "Tu capítulo actual del alma",
    "next_chapter":       "El capítulo que viene",
    "sub_theme":          "El sub-tema activo ahora",
    "yoga_active":        "Un patrón del alma está floreciendo",
    "personal_mirror":    "Tu propia historia habla",
    "what":               "QUÉ está pasando",
    "why":                "POR QUÉ está pasando",
    "what_it_means":      "QUÉ significa para ti",
    "invitation":         "TU INVITACIÓN",
    "window":             "LA VENTANA",
    "your_move":          "TU MOVIMIENTO",
    "the_practice":       "LA PRÁCTICA",

    # Dasha energies in Spanish
    "Sun_dasha":     "un período de trabajo en tu identidad — stepping into tu propia autoridad",
    "Moon_dasha":    "un ciclo emocional profundo — tu mundo interior, hogar y raíces en foco",
    "Mars_dasha":    "un período de alta energía y acción — el coraje es tu combustible",
    "Mercury_dasha": "un ciclo intelectual — comunicación, negocios y el poder de tu mente",
    "Jupiter_dasha": "un período de expansión — el universo está diciendo sí para ti",
    "Venus_dasha":   "una larga temporada del corazón — el amor y la belleza como maestros",
    "Saturn_dasha":  "una presión clarificadora — Saturno pregunta: ¿qué es verdaderamente real?",
    "Rahu_dasha":    "un período de hambre de ser — ambición, transformación y lo nuevo",
    "Ketu_dasha":    "un ciclo de soltar — tu alma está aligerando su carga para algo más verdadero",
}

ENERGY_LANGUAGE_PT = {
    "current_chapter":    "Seu capítulo atual da alma",
    "next_chapter":       "O capítulo que vem",
    "sub_theme":          "O sub-tema ativo agora",
    "yoga_active":        "Um padrão da alma está florescendo",
    "personal_mirror":    "Sua própria história fala",
    "what":               "O QUE está acontecendo",
    "why":                "POR QUE está acontecendo",
    "what_it_means":      "O QUE significa para você",
    "invitation":         "SUA CONVITE",
    "window":             "A JANELA",
    "your_move":          "SEU MOVIMENTO",
    "the_practice":       "A PRÁTICA",

    # Dasha energies in Portuguese
    "Sun_dasha":     "um período de trabalho na sua identidade — assumindo sua própria autoridade",
    "Moon_dasha":    "um ciclo emocional profundo — seu mundo interior, lar e raízes em foco",
    "Mars_dasha":    "um período de alta energia e ação — coragem é seu combustível",
    "Mercury_dasha": "um ciclo intelectual — comunicação, negócios e o poder da sua mente",
    "Jupiter_dasha": "um período de expansão — o universo está dizendo sim para você",
    "Venus_dasha":   "uma longa temporada do coração — amor e beleza como mestres",
    "Saturn_dasha":  "uma pressão clarificadora — Saturno pergunta: o que é verdadeiramente real?",
    "Rahu_dasha":    "um período de fome de ser — ambição, transformação e o novo",
    "Ketu_dasha":    "um ciclo de soltar — sua alma está aliviando sua carga para algo mais verdadeiro",
}


# ── UI String translations ────────────────────────────────────────────────────

UI_STRINGS = {

    "en": {
        "good_morning": "Good Morning",
        "good_afternoon": "Good Afternoon",
        "good_evening": "Good Evening",
        "your_day_ahead": "Your Day Ahead",
        "current_chapter": "Your Current Chapter",
        "months_remaining": "{n} months remaining",
        "life_areas": "Life Areas",
        "career": "Career",
        "love": "Love",
        "health": "Health",
        "finance": "Finance",
        "ai_chat_title": "Ask Antar",
        "ai_chat_subtitle": "Hi, I'm here to guide you through life's cosmic journey.",
        "ask_placeholder": "Ask about your destiny...",
        "insights_title": "Insights",
        "insights_subtitle": "Today's Personalized Guidance",
        "calendar_title": "Calendar",
        "calendar_subtitle": "Your Cosmic Timeline",
        "profile_title": "Profile",
        "life_milestones": "Life Milestones",
        "add_event": "Log a Life Event",
        "your_chart_knew": "Your Chart Knew",
        "unlock_patterns": "Unlock Your Personal Patterns",
        "log_3_events": "Log {n} more events to unlock your personal pattern analysis.",
        "patterns_found": "We found {n} patterns in your life story.",
        "daily_elevation": "Daily Elevation",
        "play_mantra": "Play Mantra",
        "confidence_score": "Confidence",
        "key_factors": "What's Behind This Reading",
        "what_if": "What If Analysis",
        "nation_climate": "Nation's Astrological Climate",
        "read_more": "Read more",
        "your_move": "Your Move",
        "the_practice": "The Practice",
        "streak_days": "{n} day streak",
        "next_milestone": "{n} to next milestone",
        "unlock_full": "Unlock Full Readings",
        "save_chart": "Save your birth chart",
        "gemstone_disclaimer": "Consult a Vedic astrologer before wearing gemstones. Shown for awareness only.",
        "loading_reading": "Reading your chart...",
        "loading_dashas": "Calculating your soul's timeline...",
        "loading_transits": "Analyzing current cosmic weather...",
        "loading_patterns": "Finding your personal patterns...",
        "error_retry": "Unable to load your reading right now. Tap to retry.",
        "language_prompt_title": "Choose Your Language",
        "language_prompt_body": "We noticed you may prefer Spanish. Would you like to continue in Spanish or English?",
        "language_english": "Continue in English",
        "language_spanish": "Continuar en Español",
        "power_windows": "Your Power Windows This Month",
        "upcoming_events": "Upcoming Events",
        "did_this_happen": "Did this happen?",
        "yes_it_happened": "Yes! It happened",
        "not_yet": "Not yet",
        "prediction_fulfilled": "Your chart noted this. The pattern grows clearer.",
        "notifications_title": "Cosmic Timing Alerts",
        "notifications_subtitle": "Only when it truly matters",
        "home": "Home",
        "calendar_tab": "Calendar",
        "chat_tab": "AI Chat",
        "insights_tab": "Insights",
        "profile_tab": "Profile",
        "suggestions": "Ask about",
        "today_chip": "Today",
        "dasha_chip": "My Chapter",
        "proof_loop_title": "Before I show you your future...",
        "proof_loop_subtitle": "Let me prove I already know your past.",
        "proof_loop_body": "Tell me 3 significant things that happened in your life. I'll show you exactly where they appear in your chart.",
        "proof_loop_button": "Show Me What My Chart Knew →",
        "revelation_title": "Your Chart Knew",
        "revelation_subtitle": "Your chart had this written {years} years before it happened.",
        "revelation_accuracy": "Your personal accuracy: {pct}%",
        "revelation_button": "Show Me What's Coming →",
        "your_personal_accuracy": "Your Personal Accuracy",
        "accuracy_building": "Accuracy builds as your predictions age",
    },

    "es": {
        "good_morning": "Buenos Días",
        "good_afternoon": "Buenas Tardes",
        "good_evening": "Buenas Noches",
        "your_day_ahead": "Tu Día Por Delante",
        "current_chapter": "Tu Capítulo Actual",
        "months_remaining": "{n} meses restantes",
        "life_areas": "Áreas de Vida",
        "career": "Carrera",
        "love": "Amor",
        "health": "Salud",
        "finance": "Finanzas",
        "ai_chat_title": "Pregunta a Antar",
        "ai_chat_subtitle": "Hola, estoy aquí para guiarte en tu viaje cósmico.",
        "ask_placeholder": "Pregunta sobre tu destino...",
        "insights_title": "Perspectivas",
        "insights_subtitle": "Tu Guía Personalizada de Hoy",
        "calendar_title": "Calendario",
        "calendar_subtitle": "Tu Línea de Tiempo Cósmica",
        "profile_title": "Perfil",
        "life_milestones": "Momentos de Vida",
        "add_event": "Registrar un Momento de Vida",
        "your_chart_knew": "Tu Carta lo Sabía",
        "unlock_patterns": "Descubre Tus Patrones Personales",
        "log_3_events": "Registra {n} momentos más para desbloquear tu análisis personal.",
        "patterns_found": "Encontramos {n} patrones en tu historia de vida.",
        "daily_elevation": "Elevación Diaria",
        "play_mantra": "Reproducir Mantra",
        "confidence_score": "Confianza",
        "key_factors": "Qué Hay Detrás de Esta Lectura",
        "what_if": "Análisis ¿Qué Pasaría Si?",
        "nation_climate": "Clima Astrológico del País",
        "read_more": "Leer más",
        "your_move": "Tu Movimiento",
        "the_practice": "La Práctica",
        "streak_days": "{n} días seguidos",
        "next_milestone": "{n} para el próximo hito",
        "unlock_full": "Desbloquear Lecturas Completas",
        "save_chart": "Guarda tu carta natal",
        "gemstone_disclaimer": "Consulta a un astrólogo védico antes de usar piedras. Solo para conocimiento.",
        "loading_reading": "Leyendo tu carta...",
        "loading_dashas": "Calculando la línea de tiempo de tu alma...",
        "loading_transits": "Analizando el clima cósmico actual...",
        "loading_patterns": "Encontrando tus patrones personales...",
        "error_retry": "No se pudo cargar tu lectura ahora. Toca para reintentar.",
        "language_prompt_title": "Elige Tu Idioma",
        "language_prompt_body": "¿Prefieres continuar en español o en inglés?",
        "language_english": "Continue in English",
        "language_spanish": "Continuar en Español",
        "power_windows": "Tus Ventanas de Poder Este Mes",
        "upcoming_events": "Próximos Eventos",
        "did_this_happen": "¿Esto ocurrió?",
        "yes_it_happened": "¡Sí! Ocurrió",
        "not_yet": "Aún no",
        "prediction_fulfilled": "Tu carta lo anotó. El patrón se hace más claro.",
        "notifications_title": "Alertas de Timing Cósmico",
        "notifications_subtitle": "Solo cuando realmente importa",
        "home": "Inicio",
        "calendar_tab": "Calendario",
        "chat_tab": "Chat IA",
        "insights_tab": "Perspectivas",
        "profile_tab": "Perfil",
        "suggestions": "Pregunta sobre",
        "today_chip": "Hoy",
        "dasha_chip": "Mi Capítulo",
        "proof_loop_title": "Antes de mostrarte tu futuro...",
        "proof_loop_subtitle": "Déjame probarte que ya conozco tu pasado.",
        "proof_loop_body": "Cuéntame 3 cosas significativas que te han pasado. Te mostraré exactamente dónde aparecen en tu carta.",
        "proof_loop_button": "Muéstrame Lo Que Mi Carta Sabía →",
        "revelation_title": "Tu Carta Lo Sabía",
        "revelation_subtitle": "Tu carta tenía esto escrito {years} años antes de que ocurriera.",
        "revelation_accuracy": "Tu precisión personal: {pct}%",
        "revelation_button": "Muéstrame Lo Que Viene →",
        "your_personal_accuracy": "Tu Precisión Personal",
        "accuracy_building": "La precisión crece con el tiempo",
    },

    "pt_BR": {
        "good_morning": "Bom Dia",
        "good_afternoon": "Boa Tarde",
        "good_evening": "Boa Noite",
        "your_day_ahead": "Seu Dia à Frente",
        "current_chapter": "Seu Capítulo Atual",
        "months_remaining": "{n} meses restantes",
        "life_areas": "Áreas da Vida",
        "career": "Carreira",
        "love": "Amor",
        "health": "Saúde",
        "finance": "Finanças",
        "ai_chat_title": "Pergunte ao Antar",
        "ai_chat_subtitle": "Olá, estou aqui para guiá-lo em sua jornada cósmica.",
        "ask_placeholder": "Pergunte sobre seu destino...",
        "insights_title": "Perspectivas",
        "insights_subtitle": "Sua Orientação Personalizada de Hoje",
        "calendar_title": "Calendário",
        "calendar_subtitle": "Sua Linha do Tempo Cósmica",
        "profile_title": "Perfil",
        "life_milestones": "Momentos de Vida",
        "add_event": "Registrar um Momento de Vida",
        "your_chart_knew": "Seu Mapa Sabia",
        "unlock_patterns": "Descubra Seus Padrões Pessoais",
        "log_3_events": "Registre mais {n} momentos para desbloquear sua análise pessoal.",
        "patterns_found": "Encontramos {n} padrões na sua história de vida.",
        "daily_elevation": "Elevação Diária",
        "play_mantra": "Tocar Mantra",
        "confidence_score": "Confiança",
        "key_factors": "O Que Está Por Trás Desta Leitura",
        "what_if": "Análise E Se",
        "nation_climate": "Clima Astrológico do País",
        "read_more": "Ler mais",
        "your_move": "Seu Movimento",
        "the_practice": "A Prática",
        "streak_days": "{n} dias seguidos",
        "next_milestone": "{n} para o próximo marco",
        "unlock_full": "Desbloquear Leituras Completas",
        "save_chart": "Salve seu mapa natal",
        "gemstone_disclaimer": "Consulte um astrólogo védico antes de usar pedras. Apenas para conhecimento.",
        "loading_reading": "Lendo seu mapa...",
        "loading_dashas": "Calculando a linha do tempo da sua alma...",
        "loading_transits": "Analisando o clima cósmico atual...",
        "loading_patterns": "Encontrando seus padrões pessoais...",
        "error_retry": "Não foi possível carregar sua leitura agora. Toque para tentar novamente.",
        "language_prompt_title": "Escolha Seu Idioma",
        "language_prompt_body": "Prefere continuar em português ou inglês?",
        "language_english": "Continue in English",
        "language_spanish": "Continuar em Português",
        "power_windows": "Suas Janelas de Poder Este Mês",
        "upcoming_events": "Próximos Eventos",
        "did_this_happen": "Isso aconteceu?",
        "yes_it_happened": "Sim! Aconteceu",
        "not_yet": "Ainda não",
        "prediction_fulfilled": "Seu mapa anotou isso. O padrão fica mais claro.",
        "notifications_title": "Alertas de Timing Cósmico",
        "notifications_subtitle": "Apenas quando realmente importa",
        "home": "Início",
        "calendar_tab": "Calendário",
        "chat_tab": "Chat IA",
        "insights_tab": "Perspectivas",
        "profile_tab": "Perfil",
        "suggestions": "Pergunte sobre",
        "today_chip": "Hoje",
        "dasha_chip": "Meu Capítulo",
        "proof_loop_title": "Antes de mostrar seu futuro...",
        "proof_loop_subtitle": "Deixe-me provar que já conheço seu passado.",
        "proof_loop_body": "Conte-me 3 coisas significativas que aconteceram na sua vida. Vou mostrar exatamente onde aparecem no seu mapa.",
        "proof_loop_button": "Mostre O Que Meu Mapa Sabia →",
        "revelation_title": "Seu Mapa Sabia",
        "revelation_subtitle": "Seu mapa tinha isso escrito {years} anos antes de acontecer.",
        "revelation_accuracy": "Sua precisão pessoal: {pct}%",
        "revelation_button": "Mostre O Que Vem →",
        "your_personal_accuracy": "Sua Precisão Pessoal",
        "accuracy_building": "A precisão cresce com o tempo",
    },
}

# Spanish variants inherit from "es" base, override where needed
for variant in ["es_MX", "es_AR", "es_CO", "es_CL", "es_PE", "es_VE",
                "es_EC", "es_GT", "es_DO", "es_HN", "es_BO"]:
    UI_STRINGS[variant] = dict(UI_STRINGS["es"])  # inherit all from es base

# Argentine voseo overrides
UI_STRINGS["es_AR"].update({
    "good_morning":    "Buen Día",
    "good_evening":    "Buenas Noches",
    "ai_chat_subtitle": "Hola, estoy acá para guiarte en tu viaje cósmico.",
    "ask_placeholder": "Preguntá sobre tu destino...",
    "add_event":       "Registrá un Momento de Vida",
    "proof_loop_body": "Contame 3 cosas significativas que te pasaron. Te voy a mostrar exactamente dónde aparecen en tu carta.",
})

# PT-BR full strings already defined above


# ── Main detection function ────────────────────────────────────────────────────

def detect_language(
    residence_country: str,
    birth_country: Optional[str] = None,
    user_preference: Optional[str] = None,
) -> LocaleConfig:
    """
    Main entry point. Determines the correct locale for a user.

    Args:
        residence_country: Country code where user currently lives (from IP or profile)
        birth_country: Country code where user was born (from birth data entry)
        user_preference: Explicit language preference set by user ("en", "es", "pt", etc.)

    Returns:
        LocaleConfig with all display, tone, and UI settings
    """

    # User explicit preference always wins
    if user_preference:
        return _build_locale(
            language=user_preference,
            variant=user_preference,
            residence=residence_country or "US",
            birth=birth_country or residence_country or "US",
            needs_prompt=False,
        )

    cc = (residence_country or "US").upper()
    bc = (birth_country or cc).upper()

    # ── LATAM Spanish ──────────────────────────────────────────
    if cc in SPANISH_LATAM_COUNTRIES:
        variant = SPANISH_LATAM_COUNTRIES[cc]
        return _build_locale("es", variant, cc, bc, needs_prompt=False)

    # ── Brazil ─────────────────────────────────────────────────
    if cc in PORTUGUESE_COUNTRIES:
        variant = PORTUGUESE_COUNTRIES[cc]
        return _build_locale("pt", variant, cc, bc, needs_prompt=False)

    # ── India ──────────────────────────────────────────────────
    if cc in INDIA_COUNTRIES:
        return _build_locale("en", "en_IN", cc, bc, needs_prompt=False)

    # ── USA + Hispanic birth country → bilingual prompt ────────
    if cc == "US" and bc in USA_HISPANIC_BIRTH_COUNTRIES:
        return _build_locale("en", "en", cc, bc, needs_prompt=True)

    # ── USA + Puerto Rico birth ─────────────────────────────────
    if cc == "US" and bc == "PR":
        return _build_locale("en", "en", cc, bc, needs_prompt=True)

    # ── Other English countries ─────────────────────────────────
    if cc in ENGLISH_COUNTRIES:
        return _build_locale("en", "en", cc, bc, needs_prompt=False)

    # ── Fallback: English ───────────────────────────────────────
    return _build_locale("en", "en", cc, bc, needs_prompt=False)


def get_ui_strings(variant: str) -> dict:
    """
    Get all UI strings for a given locale variant.
    Falls back to base language, then English.
    """
    if variant in UI_STRINGS:
        return UI_STRINGS[variant]
    base = variant.split("_")[0]
    if base in UI_STRINGS:
        return UI_STRINGS[base]
    return UI_STRINGS["en"]


def get_tone_profile(variant: str) -> dict:
    """
    Get the LLM tone profile for a given locale.
    Falls back to base language, then English.
    """
    if variant in TONE_PROFILES:
        return TONE_PROFILES[variant]
    base = variant.split("_")[0]
    if base in TONE_PROFILES:
        return TONE_PROFILES[base]
    return TONE_PROFILES["en"]


def get_energy_language(variant: str) -> dict:
    """
    Get the energy language translation dict for a locale.
    """
    base = variant.split("_")[0]
    if base == "es":
        return ENERGY_LANGUAGE_ES
    if base == "pt":
        return ENERGY_LANGUAGE_PT
    return {}  # English — use the defaults in predictions.py


# ── Private helpers ────────────────────────────────────────────────────────────

def _build_locale(
    language: str,
    variant: str,
    residence: str,
    birth: str,
    needs_prompt: bool,
) -> LocaleConfig:
    tone    = get_tone_profile(variant)
    ui      = get_ui_strings(variant)

    lang_names = {
        "en": ("English", "English"),
        "es": ("Spanish", "Español"),
        "pt": ("Portuguese", "Português"),
        "hi": ("Hindi", "हिन्दी"),
        "ta": ("Tamil", "தமிழ்"),
        "te": ("Telugu", "తెలుగు"),
    }
    base     = language.split("_")[0]
    lname, nname = lang_names.get(base, ("English", "English"))

    return LocaleConfig(
        language=language,
        variant=variant,
        country_code=residence,
        birth_country=birth,
        needs_language_prompt=needs_prompt,
        language_name=lname,
        native_name=nname,
        tone_style=tone.get("tone_style", ""),
        remedy_frame=tone.get("remedy_frame", ""),
        challenge_frame=tone.get("challenge_frame", ""),
        blessing_frame=tone.get("blessing_frame", ""),
        closing_style=tone.get("closing_style", ""),
        ui=ui,
    )


# ── FastAPI integration helper ─────────────────────────────────────────────────

def get_locale_from_request(
    country_code: Optional[str],
    birth_country: Optional[str],
    user_language_preference: Optional[str],
) -> LocaleConfig:
    """
    Call this in your FastAPI endpoints to get the locale.
    Integrates with your existing chart_record data.

    Usage in main.py:
        from antar_engine.i18n import get_locale_from_request

        locale = get_locale_from_request(
            country_code=chart_record.get("country_code"),
            birth_country=chart_record.get("birth_country"),
            user_language_preference=chart_record.get("language_preference"),
        )

        # Pass to prompt_builder:
        prompt = build_predict_prompt(
            ...
            language=locale.language,
            country_code=locale.country_code,
            tone_override=locale.tone_style,
        )

        # Pass to response:
        return PredictResponse(
            ...
            ui_language=locale.variant,
            needs_language_prompt=locale.needs_language_prompt,
        )
    """
    return detect_language(
        residence_country=country_code,
        birth_country=birth_country,
        user_preference=user_language_preference,
    )


# ── Phase 2: India regional languages scaffold ─────────────────────────────────
# Uncomment when ready to add regional Indian languages

"""
INDIA_REGIONAL_LANGUAGES = {
    "Hindi":     ("hi", "HI", "हिन्दी"),
    "Tamil":     ("ta", "TA", "தமிழ்"),
    "Telugu":    ("te", "TE", "తెలుగు"),
    "Kannada":   ("kn", "KN", "ಕನ್ನಡ"),
    "Malayalam": ("ml", "ML", "മലയാളം"),
    "Bengali":   ("bn", "BN", "বাংলা"),
    "Marathi":   ("mr", "MR", "मराठी"),
    "Gujarati":  ("gu", "GU", "ગુજરાતી"),
    "Punjabi":   ("pa", "PA", "ਪੰਜਾਬੀ"),
    "Odia":      ("or", "OR", "ଓଡ଼ିଆ"),
}

# When a user in India selects a regional language:
# 1. Store language_preference in their profile
# 2. Pass to detect_language(user_preference="hi")  
# 3. The prompt_builder will switch to that language automatically
# 4. DeepSeek handles all Indian languages natively
"""

