"""
antar_engine/topic_copy.py
──────────────────────────
Plain-words copy for the topic picker (GET /chart/{id}/topics) and the topic
read (GET /chart/{id}/topic-read). Every user-facing string the topic engine
emits comes from here, so the no-jargon guard (tests/test_topic_engine.py)
has ONE place to prove clean.

Languages: en, es, pt, hinglish (Roman-script Hindi). Anything else —
including Devanagari `hi` (a separate task) and `fr` — is served in English and
the response says `language: "en"`, so a card is never half one language and
half another. English-only keyword logic is a known silent bug class: nothing
in the engine branches on words, only on these keyed tables.

Owner rules baked into the wording (do not loosen):
  • Money / Business speak about TIMING and approach only — never "you will be
    rich" and never a promise a venture works (closed negative studies).
  • Health speaks rhythm and routine only — never a diagnosis.
  • No system names ("dasha", "Jaimini", "transit", planets, houses…).
  • No prices, no consent logic.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, Optional

TOPIC_KEYS = ("money", "career", "love", "health", "business", "peace", "family")
SCALES = ("today", "month", "season", "year")
COPY_LANGUAGES = ("en", "es", "pt", "hinglish")


def serve_language(raw) -> str:
    """The language the copy will actually be written in."""
    try:
        from antar_engine.lang_registry import normalize_language
        lang = normalize_language(raw, log=False)
    except Exception:
        lang = "en"
    return lang if lang in COPY_LANGUAGES else "en"


# ── labels, areas ────────────────────────────────────────────────────────────
LABEL: Dict[str, Dict[str, str]] = {
    "en": {"money": "Money", "career": "Career", "love": "Love", "health": "Health",
           "business": "Business", "peace": "Peace", "family": "Family"},
    "es": {"money": "Dinero", "career": "Carrera", "love": "Amor", "health": "Salud",
           "business": "Negocio", "peace": "Paz", "family": "Familia"},
    "pt": {"money": "Dinheiro", "career": "Carreira", "love": "Amor", "health": "Saúde",
           "business": "Negócio", "peace": "Paz", "family": "Família"},
    "hinglish": {"money": "Paisa", "career": "Career", "love": "Pyaar", "health": "Sehat",
                 "business": "Business", "peace": "Sukoon", "family": "Parivaar"},
}

# lower-case noun phrase used mid-sentence ("the chapter you're in is tied to …")
AREA: Dict[str, Dict[str, str]] = {
    "en": {"money": "money and income", "career": "your work", "love": "close relationships",
           "health": "your body's rhythm", "business": "ventures and partnerships",
           "peace": "your inner calm", "family": "home and family"},
    "es": {"money": "el dinero y los ingresos", "career": "tu trabajo",
           "love": "las relaciones cercanas", "health": "el ritmo de tu cuerpo",
           "business": "los negocios y las alianzas", "peace": "tu calma interior",
           "family": "el hogar y la familia"},
    "pt": {"money": "o dinheiro e a renda", "career": "o seu trabalho",
           "love": "as relações próximas", "health": "o ritmo do seu corpo",
           "business": "os negócios e as parcerias", "peace": "a sua calma interior",
           "family": "a casa e a família"},
    "hinglish": {"money": "paise aur income", "career": "aapka kaam",
                 "love": "kareebi rishte", "health": "aapke sharir ki lay",
                 "business": "business aur partnerships", "peace": "aapka andar ka sukoon",
                 "family": "ghar aur parivaar"},
}

# ── status tags ──────────────────────────────────────────────────────────────
TAG: Dict[str, Dict[str, str]] = {
    "en": {"active": "active now", "care": "needs care now", "open": "window opens {mon}",
           "care_from": "take care from {mon}", "quiet": "quiet", "steady": "steady"},
    "es": {"active": "activo ahora", "care": "pide cuidado ahora", "open": "se abre una ventana en {mon}",
           "care_from": "cuidado desde {mon}", "quiet": "tranquilo", "steady": "estable"},
    "pt": {"active": "ativo agora", "care": "pede cuidado agora", "open": "uma janela abre em {mon}",
           "care_from": "cuidado a partir de {mon}", "quiet": "tranquilo", "steady": "estável"},
    "hinglish": {"active": "abhi active", "care": "abhi dhyaan chahiye",
                 "open": "{mon} mein window khulegi", "care_from": "{mon} se dhyaan rakhein",
                 "quiet": "shaant", "steady": "sthir"},
}

MONTHS: Dict[str, tuple] = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"),
    "pt": ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"),
    "hinglish": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
}


def month_name(d: date, lang: str) -> str:
    return MONTHS.get(lang, MONTHS["en"])[d.month - 1]


def day_label(d: date, lang: str) -> str:
    m = month_name(d, lang)
    return f"{m} {d.day}" if lang in ("en", "hinglish") else f"{d.day} {m}"


def day_label_y(d: date, lang: str) -> str:
    return f"{day_label(d, lang)}, {d.year}" if lang in ("en", "hinglish") else f"{day_label(d, lang)} {d.year}"


def range_label(start: date, end: date, lang: str) -> str:
    if start == end:
        return day_label(start, lang)
    return f"{day_label(start, lang)} – {day_label(end, lang)}"


# ── time-scale lead-ins ──────────────────────────────────────────────────────
SPAN_LEAD: Dict[str, Dict[str, str]] = {
    "en": {"today": "Today", "month": "This month", "season": "This season", "year": "This year"},
    "es": {"today": "Hoy", "month": "Este mes", "season": "Esta etapa", "year": "Este año"},
    "pt": {"today": "Hoje", "month": "Este mês", "season": "Esta fase", "year": "Este ano"},
    "hinglish": {"today": "Aaj", "month": "Is mahine", "season": "Is daur mein", "year": "Is saal"},
}

PERIOD_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"today": "Today", "month": "Next 30 days", "season": "This season, to {end}",
           "year": "Your year, {start} – {end}"},
    "es": {"today": "Hoy", "month": "Próximos 30 días", "season": "Esta etapa, hasta {end}",
           "year": "Tu año, {start} – {end}"},
    "pt": {"today": "Hoje", "month": "Próximos 30 dias", "season": "Esta fase, até {end}",
           "year": "O seu ano, {start} – {end}"},
    "hinglish": {"today": "Aaj", "month": "Agle 30 din", "season": "Is daur mein, {end} tak",
                 "year": "Aapka saal, {start} – {end}"},
}

WINDOW_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"best": "Best window", "watch": "Watch", "whole": "All of {span}"},
    "es": {"best": "Mejor ventana", "watch": "Ojo", "whole": "Todo: {span}"},
    "pt": {"best": "Melhor janela", "watch": "Atenção", "whole": "Todo: {span}"},
    "hinglish": {"best": "Best window", "watch": "Dhyaan", "whole": "Poora {span}"},
}
WHOLE_SPAN: Dict[str, Dict[str, str]] = {
    "en": {"today": "today", "month": "the next 30 days", "season": "this season", "year": "this year"},
    "es": {"today": "hoy", "month": "los próximos 30 días", "season": "esta etapa", "year": "este año"},
    "pt": {"today": "hoje", "month": "os próximos 30 dias", "season": "esta fase", "year": "este ano"},
    "hinglish": {"today": "aaj", "month": "agle 30 din", "season": "yeh daur", "year": "yeh saal"},
}

# ── claims: lower-case sentence cores, joined to the span lead ───────────────
# mode: open (a real supportive stretch) | care (a real demanding stretch) | steady
CORE: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "money": {"open": "money matters have better backing than usual, so it is a good stretch to act on income, pricing and plans",
                  "care": "money asks for care, so slow down on big commitments and re-read the terms"},
        "career": {"open": "work moves get real support, so it is a good time to speak up, apply or make your case",
                   "care": "work asks for patience, so avoid forcing a decision and keep your record clean"},
        "love": {"open": "close relationships are more open than usual, so it is a good time to reach out and be direct",
                 "care": "relationships need gentleness, so avoid big conversations when you are tired or rushed"},
        "health": {"open": "your rhythm is easier to build on, so it is a good time to restart a routine of sleep, food and movement",
                   "care": "your body asks for a steadier rhythm, so protect sleep and rest and do not push through tiredness"},
        "business": {"open": "decisions and partnerships are better timed than usual, so commit to a step you have already prepared",
                     "care": "commitments are better held back, so test small before you put money or people behind anything"},
        "peace": {"open": "inner calm is easier to reach, so it is a good time to simplify and make room for stillness",
                  "care": "your mind runs more restless than usual, so keep evenings quiet and cut what you can"},
        "family": {"open": "home and family feel more connected, so it is a good time to be together and settle household matters",
                   "care": "family matters need care, so listen first and leave big household decisions for later"},
    },
    "es": {
        "money": {"open": "los asuntos de dinero tienen mejor respaldo que de costumbre, así que es buen momento para actuar sobre ingresos, precios y planes",
                  "care": "el dinero pide cuidado, así que baja el ritmo en compromisos grandes y relee las condiciones"},
        "career": {"open": "tus movimientos en el trabajo reciben apoyo real, así que es buen momento para hablar, postularte o defender tu caso",
                   "care": "el trabajo pide paciencia, así que evita forzar una decisión y cuida tu historial"},
        "love": {"open": "las relaciones cercanas están más abiertas que de costumbre, así que es buen momento para acercarte y ser directo",
                 "care": "las relaciones piden suavidad, así que evita las conversaciones grandes cuando estés cansado o apurado"},
        "health": {"open": "tu ritmo es más fácil de construir, así que es buen momento para retomar una rutina de sueño, comida y movimiento",
                   "care": "tu cuerpo pide un ritmo más estable, así que protege el sueño y el descanso y no te exijas pasando el cansancio"},
        "business": {"open": "las decisiones y las alianzas están mejor ubicadas en el tiempo que de costumbre, así que compromete un paso que ya tengas preparado",
                     "care": "conviene aplazar los compromisos, así que prueba en pequeño antes de poner dinero o gente detrás de algo"},
        "peace": {"open": "la calma interior es más fácil de alcanzar, así que es buen momento para simplificar y dejar espacio a la quietud",
                  "care": "tu mente anda más inquieta que de costumbre, así que mantén las noches tranquilas y recorta lo que puedas"},
        "family": {"open": "el hogar y la familia se sienten más unidos, así que es buen momento para estar juntos y resolver asuntos de la casa",
                   "care": "los asuntos familiares piden cuidado, así que escucha primero y deja las decisiones grandes del hogar para después"},
    },
    "pt": {
        "money": {"open": "os assuntos de dinheiro têm mais respaldo que o habitual, então é um bom momento para agir sobre renda, preços e planos",
                  "care": "o dinheiro pede cuidado, então vá mais devagar em compromissos grandes e releia as condições"},
        "career": {"open": "os seus movimentos no trabalho recebem apoio real, então é um bom momento para falar, se candidatar ou defender o seu caso",
                   "care": "o trabalho pede paciência, então evite forçar uma decisão e cuide do seu histórico"},
        "love": {"open": "as relações próximas estão mais abertas que o habitual, então é um bom momento para se aproximar e ser direto",
                 "care": "as relações pedem delicadeza, então evite conversas grandes quando estiver cansado ou com pressa"},
        "health": {"open": "o seu ritmo está mais fácil de construir, então é um bom momento para retomar uma rotina de sono, comida e movimento",
                   "care": "o seu corpo pede um ritmo mais estável, então proteja o sono e o descanso e não force o cansaço"},
        "business": {"open": "as decisões e as parcerias estão mais bem situadas no tempo que o habitual, então assuma um passo que você já preparou",
                     "care": "é melhor adiar compromissos, então teste em pequeno antes de pôr dinheiro ou pessoas por trás de algo"},
        "peace": {"open": "a calma interior está mais fácil de alcançar, então é um bom momento para simplificar e abrir espaço para a quietude",
                  "care": "a sua mente está mais inquieta que o habitual, então mantenha as noites calmas e corte o que puder"},
        "family": {"open": "a casa e a família parecem mais unidas, então é um bom momento para estarem juntos e resolver assuntos da casa",
                   "care": "os assuntos de família pedem cuidado, então ouça primeiro e deixe as decisões grandes da casa para depois"},
    },
    "hinglish": {
        "money": {"open": "paise ke maamle ko is baar behtar support hai, isliye income, pricing aur plans par kaam karne ka achha waqt hai",
                  "care": "paise mein dhyaan chahiye, isliye bade commitments mein ruk kar chalein aur terms dobara padhein"},
        "career": {"open": "kaam mein aapki chaal ko sach mein support mil raha hai, isliye bolne, apply karne ya apni baat rakhne ka achha waqt hai",
                   "care": "kaam mein sabr chahiye, isliye faisla zabardasti na karein aur apna record saaf rakhein"},
        "love": {"open": "kareebi rishte aam se zyada khule hain, isliye pehal karne aur seedhi baat karne ka achha waqt hai",
                 "care": "rishton mein narmi chahiye, isliye thake ya jaldi mein bade baat-cheet se bachein"},
        "health": {"open": "aapki lay banana aasaan hai, isliye neend, khaane aur halchal ki routine dobara shuru karne ka achha waqt hai",
                   "care": "sharir ek sthir lay maangta hai, isliye neend aur aaram bachayein aur thakaan ke bawajood khud ko na kheenchein"},
        "business": {"open": "faisle aur partnerships ka timing aam se behtar hai, isliye jo kadam aap pehle se taiyaar kar chuke hain wo uthayein",
                     "care": "commitments ko rokna behtar hai, isliye paisa ya log lagane se pehle chhote star par test karein"},
        "peace": {"open": "andar ka sukoon paana aasaan hai, isliye cheezein saral karne aur shaanti ko jagah dene ka achha waqt hai",
                  "care": "mann aam se zyada bechain hai, isliye shaamein shaant rakhein aur jo kaat sakein kaatein"},
        "family": {"open": "ghar aur parivaar zyada jude mehsoos honge, isliye saath rehne aur ghar ke maamle suljhane ka achha waqt hai",
                   "care": "parivaar ke maamlon mein dhyaan chahiye, isliye pehle sunein aur ghar ke bade faisle baad ke liye chhodein"},
    },
}

# "nothing sharp" — one template per language, {label} = lower-case topic phrase
STEADY_CORE: Dict[str, str] = {
    "en": "nothing sharp is pulling on {area}, so keep your usual pace",
    "es": "nada fuerte tira sobre {area}, así que mantén tu ritmo habitual",
    "pt": "nada forte puxa sobre {area}, então mantenha o seu ritmo habitual",
    "hinglish": "{area} par kuch tez nahin kheench raha, isliye apni aam raftaar rakhein",
}
LEAD_JOIN: Dict[str, str] = {"en": "{lead}, {core}.", "es": "{lead}, {core}.",
                             "pt": "{lead}, {core}.", "hinglish": "{lead} {core}."}

# ── your move (one action) ───────────────────────────────────────────────────
MOVE: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "money": {"open": "Pick the one money decision you have been putting off and act on it within the window.",
                  "care": "Wait a night before any money commitment, and write down the number you are truly comfortable with.",
                  "steady": "Keep your routine and review one recurring expense."},
        "career": {"open": "Make the one ask or application you have been rehearsing, inside the window.",
                   "care": "Finish what is open before you start anything new.",
                   "steady": "Keep your head down and do one piece of work you can be proud of."},
        "love": {"open": "Reach out to the person on your mind and say one honest, kind thing.",
                 "care": "Pause before replying when you feel tense, and choose a calmer hour to talk.",
                 "steady": "Spend one unhurried hour with someone who matters."},
        "health": {"open": "Fix one bedtime and one wake time for the next seven days.",
                   "care": "Cut one late night or one skipped meal this week, and keep it cut.",
                   "steady": "Keep your usual routine and add a ten-minute walk."},
        "business": {"open": "Take the one step you have already prepared, and keep it small enough to reverse.",
                     "care": "Test with something small before you commit money, people or a date.",
                     "steady": "Use the quiet to tidy numbers and notes rather than start something new."},
        "peace": {"open": "Give yourself ten quiet minutes at the same time each day.",
                  "care": "Switch your screen off an hour before sleep and keep one evening free.",
                  "steady": "Keep a short daily pause, even five minutes."},
        "family": {"open": "Plan one meal or outing together, with phones away.",
                   "care": "Listen first in the next family talk, and decide nothing big that day.",
                   "steady": "Check in with one relative you have not spoken to lately."},
    },
    "es": {
        "money": {"open": "Elige la decisión de dinero que has ido posponiendo y actúa dentro de la ventana.",
                  "care": "Espera una noche antes de cualquier compromiso de dinero y anota la cifra con la que de verdad te sientes cómodo.",
                  "steady": "Mantén tu rutina y revisa un gasto recurrente."},
        "career": {"open": "Haz la petición o la postulación que has estado ensayando, dentro de la ventana.",
                   "care": "Termina lo que tienes abierto antes de empezar algo nuevo.",
                   "steady": "Mantén el foco y haz un trabajo del que te sientas orgulloso."},
        "love": {"open": "Escribe a esa persona que tienes en mente y dile algo honesto y amable.",
                 "care": "Haz una pausa antes de responder cuando estés tenso y elige una hora más calmada para hablar.",
                 "steady": "Pasa una hora sin prisa con alguien que importa."},
        "health": {"open": "Fija una hora de dormir y una de despertar durante los próximos siete días.",
                   "care": "Quita esta semana una noche tardía o una comida saltada, y mantenlo así.",
                   "steady": "Mantén tu rutina y suma una caminata de diez minutos."},
        "business": {"open": "Da el paso que ya tienes preparado y mantenlo lo bastante pequeño como para poder revertirlo.",
                     "care": "Prueba con algo pequeño antes de comprometer dinero, gente o una fecha.",
                     "steady": "Aprovecha la calma para ordenar cifras y notas en vez de empezar algo nuevo."},
        "peace": {"open": "Regálate diez minutos de silencio a la misma hora cada día.",
                  "care": "Apaga la pantalla una hora antes de dormir y deja una noche libre.",
                  "steady": "Mantén una pausa diaria corta, aunque sean cinco minutos."},
        "family": {"open": "Planea una comida o salida juntos, sin celulares.",
                   "care": "Escucha primero en la próxima conversación familiar y no decidas nada grande ese día.",
                   "steady": "Escribe a un familiar con quien hace tiempo no hablas."},
    },
    "pt": {
        "money": {"open": "Escolha a decisão de dinheiro que você vem adiando e aja dentro da janela.",
                  "care": "Espere uma noite antes de qualquer compromisso de dinheiro e anote o valor com o qual você se sente realmente confortável.",
                  "steady": "Mantenha a rotina e revise uma despesa recorrente."},
        "career": {"open": "Faça o pedido ou a candidatura que você vem ensaiando, dentro da janela.",
                   "care": "Termine o que está em aberto antes de começar algo novo.",
                   "steady": "Mantenha o foco e faça um trabalho do qual você se orgulhe."},
        "love": {"open": "Procure a pessoa em quem você pensa e diga algo honesto e gentil.",
                 "care": "Faça uma pausa antes de responder quando estiver tenso e escolha uma hora mais calma para conversar.",
                 "steady": "Passe uma hora sem pressa com alguém importante."},
        "health": {"open": "Fixe um horário de dormir e um de acordar pelos próximos sete dias.",
                   "care": "Corte esta semana uma noite tarde ou uma refeição pulada, e mantenha assim.",
                   "steady": "Mantenha a rotina e inclua uma caminhada de dez minutos."},
        "business": {"open": "Dê o passo que você já preparou e mantenha-o pequeno o bastante para poder reverter.",
                     "care": "Teste com algo pequeno antes de comprometer dinheiro, pessoas ou uma data.",
                     "steady": "Aproveite a calma para organizar números e anotações em vez de começar algo novo."},
        "peace": {"open": "Reserve dez minutos de silêncio no mesmo horário todos os dias.",
                  "care": "Desligue a tela uma hora antes de dormir e deixe uma noite livre.",
                  "steady": "Mantenha uma pausa diária curta, mesmo que sejam cinco minutos."},
        "family": {"open": "Planeje uma refeição ou um passeio juntos, sem celulares.",
                   "care": "Ouça primeiro na próxima conversa de família e não decida nada grande nesse dia.",
                   "steady": "Procure um parente com quem você não fala há tempo."},
    },
    "hinglish": {
        "money": {"open": "Paise ka wo ek faisla chuniye jo aap taal rahe hain aur window ke andar uspar kaam kijiye.",
                  "care": "Paise ke kisi bhi commitment se pehle ek raat ruk jaiye aur wo rakam likhiye jisme aap sach mein comfortable hain.",
                  "steady": "Apni routine rakhiye aur ek baar-baar aane wala kharcha dekhiye."},
        "career": {"open": "Wo ek maang ya application kijiye jiski aap taiyaari kar rahe the, window ke andar.",
                   "care": "Naya kuch shuru karne se pehle jo khula hai use poora kijiye.",
                   "steady": "Dhyaan se kaam kijiye aur ek aisa kaam kijiye jispar garv ho."},
        "love": {"open": "Jis insaan ka khayal aa raha hai use sampark kijiye aur ek sachchi, pyaari baat kahiye.",
                 "care": "Tanaav mein jawab dene se pehle ruk jaiye aur baat karne ke liye shaant waqt chuniye.",
                 "steady": "Kisi khaas ke saath ek aaram ka ghanta bitaiye."},
        "health": {"open": "Agle saat din ke liye sone aur uthne ka ek fixed waqt rakhiye.",
                   "care": "Is hafte ek der raat ya ek chhoota hua khaana hataiye, aur hataaye rakhiye.",
                   "steady": "Apni routine rakhiye aur das minute ki sair jodiye."},
        "business": {"open": "Wo ek kadam uthaiye jo aap pehle se taiyaar kar chuke hain, aur use itna chhota rakhiye ki palta ja sake.",
                     "care": "Paisa, log ya tareekh lagane se pehle chhoti cheez se test kijiye.",
                     "steady": "Shaanti ka use hisaab aur notes sahi karne mein kijiye, naya shuru karne mein nahin."},
        "peace": {"open": "Roz ek hi waqt par khud ko das minute ki chuppi dijiye.",
                  "care": "Sone se ek ghanta pehle screen band kijiye aur ek shaam khaali rakhiye.",
                  "steady": "Roz ek chhota pause rakhiye, paanch minute hi sahi."},
        "family": {"open": "Saath mein ek khaana ya outing plan kijiye, phone door rakh kar.",
                   "care": "Agli parivaar ki baat mein pehle sunein aur us din koi bada faisla na karein.",
                   "steady": "Kisi aise rishtedaar se baat kijiye jisse kaafi samay se baat nahin hui."},
    },
}

# ── remedy block ─────────────────────────────────────────────────────────────
REMEDY_SUMMARY: Dict[str, str] = {
    "en": "Start with the free steps. Each one is small and works on its own.",
    "es": "Empieza con los pasos gratuitos. Cada uno es pequeño y funciona por sí solo.",
    "pt": "Comece pelos passos gratuitos. Cada um é pequeno e funciona sozinho.",
    "hinglish": "Muft kadamon se shuru kijiye. Har kadam chhota hai aur akele bhi kaam karta hai.",
}
FREE_STEPS: Dict[str, Dict[str, tuple]] = {
    "en": {
        "money": ("Before any money decision this week, wait one night and write down the number you are comfortable with.",
                  "Give a small amount, or an hour of your time, to someone who needs it, quietly."),
        "career": ("Finish one task you have been avoiding before you start anything new.",
                   "Thank one person who helped your work, in writing."),
        "love": ("Say one honest, kind thing to someone close, in person if you can.",
                 "Put your phone away for one meal with them."),
        "health": ("Keep a fixed bedtime and wake time for seven days.",
                   "Take a ten-minute walk after your main meal."),
        "business": ("Write down the one commitment you are weighing and what you would lose if it failed, then decide.",
                     "Talk it through with one person who will tell you honestly."),
        "peace": ("Sit in silence for five minutes at the same time each day.",
                  "Switch your screen off an hour before sleep."),
        "family": ("Share one meal with your family without phones.",
                   "Call one relative you have been meaning to call."),
    },
    "es": {
        "money": ("Antes de cualquier decisión de dinero esta semana, espera una noche y anota la cifra con la que estás cómodo.",
                  "Da una pequeña cantidad, o una hora de tu tiempo, a alguien que lo necesite, en silencio."),
        "career": ("Termina una tarea que has estado evitando antes de empezar algo nuevo.",
                   "Agradece por escrito a una persona que ayudó a tu trabajo."),
        "love": ("Dile algo honesto y amable a alguien cercano, en persona si puedes.",
                 "Guarda el celular durante una comida con esa persona."),
        "health": ("Mantén una hora fija de dormir y de despertar durante siete días.",
                   "Camina diez minutos después de tu comida principal."),
        "business": ("Anota el compromiso que estás pensando y lo que perderías si fallara, y luego decide.",
                     "Háblalo con una persona que te dirá la verdad."),
        "peace": ("Siéntate en silencio cinco minutos a la misma hora cada día.",
                  "Apaga la pantalla una hora antes de dormir."),
        "family": ("Compartan una comida en familia sin celulares.",
                   "Llama a un familiar a quien querías llamar."),
    },
    "pt": {
        "money": ("Antes de qualquer decisão de dinheiro esta semana, espere uma noite e anote o valor com o qual você está confortável.",
                  "Dê uma pequena quantia, ou uma hora do seu tempo, a alguém que precise, em silêncio."),
        "career": ("Termine uma tarefa que você vem evitando antes de começar algo novo.",
                   "Agradeça por escrito a uma pessoa que ajudou o seu trabalho."),
        "love": ("Diga algo honesto e gentil a alguém próximo, pessoalmente se puder.",
                 "Guarde o celular durante uma refeição com essa pessoa."),
        "health": ("Mantenha um horário fixo de dormir e de acordar por sete dias.",
                   "Caminhe dez minutos depois da refeição principal."),
        "business": ("Anote o compromisso que você está pensando e o que perderia se falhasse, e depois decida.",
                     "Converse com uma pessoa que vai dizer a verdade."),
        "peace": ("Sente-se em silêncio por cinco minutos no mesmo horário todos os dias.",
                  "Desligue a tela uma hora antes de dormir."),
        "family": ("Façam uma refeição em família sem celulares.",
                   "Ligue para um parente para quem você queria ligar."),
    },
    "hinglish": {
        "money": ("Is hafte paise ke kisi bhi faisle se pehle ek raat ruk kar wo rakam likhiye jisme aap comfortable hain.",
                  "Kisi zarooratmand ko chupke se thodi rakam ya ek ghanta apna waqt dijiye."),
        "career": ("Naya kuch shuru karne se pehle ek taala hua kaam poora kijiye.",
                   "Jisne aapke kaam mein madad ki use likhkar shukriya kahiye."),
        "love": ("Kisi kareebi se ek sachchi, pyaari baat kahiye, ho sake to aamne-saamne.",
                 "Unke saath ek khaane ke dauran phone door rakhiye."),
        "health": ("Saat din tak sone aur uthne ka ek fixed waqt rakhiye.",
                   "Mukhya khaane ke baad das minute tahliye."),
        "business": ("Jis commitment par soch rahe hain use likhiye aur ye bhi ki fail hone par kya khoyenge, phir faisla kijiye.",
                     "Ek aise insaan se baat kijiye jo sach bolega."),
        "peace": ("Roz ek hi waqt par paanch minute chup baithiye.",
                  "Sone se ek ghanta pehle screen band kijiye."),
        "family": ("Parivaar ke saath ek khaana phone ke bina khaiye.",
                   "Ek rishtedaar ko phone kijiye jise karna chahte the."),
    },
}
MANTRA_STEP: Dict[str, str] = {
    "en": "If it feels right, chant {name}: 11 times, or 108 if you have the time.",
    "es": "Si lo sientes adecuado, recita {name}: 11 veces, o 108 si tienes tiempo.",
    "pt": "Se parecer certo, recite {name}: 11 vezes, ou 108 se tiver tempo.",
    "hinglish": "Agar theek lage to {name} ka jaap kijiye: 11 baar, ya samay ho to 108 baar.",
}
STONE_STEP: Dict[str, str] = {
    "en": "Optional, and only if you want it: {stone} is the traditional supporting stone for your chart. The free steps come first, and you can skip this one.",
    "es": "Opcional, y solo si quieres: {stone} es la piedra de apoyo tradicional para tu carta. Primero van los pasos gratuitos, y puedes omitir este.",
    "pt": "Opcional, e só se quiser: {stone} é a pedra de apoio tradicional para o seu mapa. Os passos gratuitos vêm primeiro, e você pode pular este.",
    "hinglish": "Optional, aur sirf agar aap chahein: {stone} aapke chart ka paramparik sahayak patthar hai. Muft kadam pehle, aur ise chhod bhi sakte hain.",
}

# ── why / reasoning ──────────────────────────────────────────────────────────
WHY_BULLET: Dict[str, Dict[str, str]] = {
    "en": {
        "chapter_core": "The chapter you are in right now is tied directly to {area}.",
        "chapter_theme": "The chapter you are in right now touches the themes behind {area}.",
        "agree": "A second way of reading your timeline points the same way.",
        "signals_open": "Slow-moving influences support {area} between {start} and {end}.",
        "signals_care": "Slow-moving influences press on {area} between {start} and {end}.",
        "signals_open_day": "Slow-moving influences support {area} on {start}.",
        "signals_care_day": "Slow-moving influences press on {area} on {start}.",
        "none_dated": "Nothing is dated sharply inside this stretch, so this is a steady read and not a dated window.",
        "approx_time": "Your birth time is not exact, so treat the dates as approximate.",
        "no_time": "Without your birth time, this read is a rough guide, not a precise one.",
    },
    "es": {
        "chapter_core": "La etapa en la que estás ahora está ligada directamente a {area}.",
        "chapter_theme": "La etapa en la que estás ahora toca los temas detrás de {area}.",
        "agree": "Una segunda forma de leer tu línea de tiempo apunta en la misma dirección.",
        "signals_open": "Influencias lentas apoyan {area} entre el {start} y el {end}.",
        "signals_care": "Influencias lentas presionan {area} entre el {start} y el {end}.",
        "signals_open_day": "Influencias lentas apoyan {area} el {start}.",
        "signals_care_day": "Influencias lentas presionan {area} el {start}.",
        "none_dated": "Nada está fechado con precisión en este tramo, así que es una lectura estable y no una ventana con fechas.",
        "approx_time": "Tu hora de nacimiento no es exacta, así que toma las fechas como aproximadas.",
        "no_time": "Sin tu hora de nacimiento, esta lectura es una guía aproximada, no precisa.",
    },
    "pt": {
        "chapter_core": "A fase em que você está agora está ligada diretamente a {area}.",
        "chapter_theme": "A fase em que você está agora toca os temas por trás de {area}.",
        "agree": "Uma segunda forma de ler a sua linha do tempo aponta na mesma direção.",
        "signals_open": "Influências lentas apoiam {area} entre {start} e {end}.",
        "signals_care": "Influências lentas pressionam {area} entre {start} e {end}.",
        "signals_open_day": "Influências lentas apoiam {area} em {start}.",
        "signals_care_day": "Influências lentas pressionam {area} em {start}.",
        "none_dated": "Nada está datado com precisão neste trecho, então é uma leitura estável e não uma janela com datas.",
        "approx_time": "A sua hora de nascimento não é exata, então trate as datas como aproximadas.",
        "no_time": "Sem a sua hora de nascimento, esta leitura é um guia aproximado, não preciso.",
    },
    "hinglish": {
        "chapter_core": "Aap jis daur mein hain wo seedha {area} se juda hai.",
        "chapter_theme": "Aap jis daur mein hain wo {area} ke peeche ke vishayon ko chhooti hai.",
        "agree": "Aapki timeline padhne ka doosra tareeka bhi isi taraf ishara karta hai.",
        "signals_open": "Dheemi chalne wale prabhav {start} se {end} ke beech {area} ko support karte hain.",
        "signals_care": "Dheemi chalne wale prabhav {start} se {end} ke beech {area} par dabaav daalte hain.",
        "signals_open_day": "Dheemi chalne wale prabhav {start} ko {area} ko support karte hain.",
        "signals_care_day": "Dheemi chalne wale prabhav {start} ko {area} par dabaav daalte hain.",
        "none_dated": "Is stretch mein kuch bhi tez taareekh ke saath nahin hai, isliye ye sthir padhai hai, dated window nahin.",
        "approx_time": "Aapka janm samay exact nahin hai, isliye taareekhon ko lagbhag maniye.",
        "no_time": "Janm samay ke bina ye padhai ek mota andaaza hai, sahi nahin.",
    },
}
BASED_ON: Dict[str, Dict[str, str]] = {
    "en": {"chapter": "Your current chapter", "today": "Today's movement",
           "month": "The next 30 days", "year": "Your year"},
    "es": {"chapter": "Tu etapa actual", "today": "El movimiento de hoy",
           "month": "Los próximos 30 días", "year": "Tu año"},
    "pt": {"chapter": "A sua fase atual", "today": "O movimento de hoje",
           "month": "Os próximos 30 dias", "year": "O seu ano"},
    "hinglish": {"chapter": "Aapka maujooda daur", "today": "Aaj ki chaal",
                 "month": "Agle 30 din", "year": "Aapka saal"},
}
CONFIDENCE_NOTE: Dict[str, Dict[str, str]] = {
    "en": {"high": "High confidence: several independent signs agree and the dates are specific.",
           "medium": "Medium confidence: the main signs agree, but the dates are broad.",
           "low": "Lower confidence: treat this as a gentle lean, not a promise."},
    "es": {"high": "Confianza alta: varias señales independientes coinciden y las fechas son concretas.",
           "medium": "Confianza media: las señales principales coinciden, pero las fechas son amplias.",
           "low": "Confianza menor: tómalo como una inclinación suave, no como una promesa."},
    "pt": {"high": "Confiança alta: vários sinais independentes concordam e as datas são específicas.",
           "medium": "Confiança média: os sinais principais concordam, mas as datas são amplas.",
           "low": "Confiança menor: encare como uma inclinação suave, não uma promessa."},
    "hinglish": {"high": "Zyada bharosa: kai alag sanket sahmat hain aur taareekhein khaas hain.",
                 "medium": "Madhyam bharosa: mukhya sanket sahmat hain, par taareekhein chaudi hain.",
                 "low": "Kam bharosa: ise halka jhukaav samjhein, vaada nahin."},
}

# ── reveal lines ─────────────────────────────────────────────────────────────
PLANET: Dict[str, Dict[str, str]] = {
    "en": {"Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Mercury": "Mercury", "Jupiter": "Jupiter",
           "Venus": "Venus", "Saturn": "Saturn", "Rahu": "Rahu", "Ketu": "Ketu"},
    "es": {"Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio", "Jupiter": "Júpiter",
           "Venus": "Venus", "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"},
    "pt": {"Sun": "Sol", "Moon": "Lua", "Mars": "Marte", "Mercury": "Mercúrio", "Jupiter": "Júpiter",
           "Venus": "Vênus", "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"},
    "hinglish": {"Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Mercury": "Mercury", "Jupiter": "Jupiter",
                 "Venus": "Venus", "Saturn": "Saturn", "Rahu": "Rahu", "Ketu": "Ketu"},
}
REVEAL_BIG: Dict[str, str] = {
    "en": "Since {start} you are in a {planet} chapter. It runs until {end}.",
    "es": "Desde {start} estás en una etapa de {planet}. Dura hasta {end}.",
    "pt": "Desde {start} você está em uma fase de {planet}. Ela vai até {end}.",
    "hinglish": "{start} se aap {planet} ke daur mein hain. Ye {end} tak chalega.",
}
REVEAL_STRETCH: Dict[str, str] = {
    "en": "{area} stretch, from {start} to {end}.",
    "es": "Un tramo {area}, de {start} a {end}.",
    "pt": "Um trecho {area}, de {start} a {end}.",
    "hinglish": "{area} daur, {start} se {end} tak.",
}
# life-area adjective for the reveal's second line, keyed by house number
REVEAL_AREA: Dict[str, Dict[int, str]] = {
    "en": {1: "A self-focused", 2: "A money-focused", 3: "A drive-and-effort focused", 4: "A home-focused",
           5: "A creative and learning-focused", 6: "A service-and-effort focused", 7: "A partnership-focused",
           8: "A deep-change focused", 9: "A learning-and-luck focused", 10: "A work-focused",
           11: "A gains-and-network focused", 12: "A rest-and-letting-go focused"},
    "es": {1: "centrado en ti", 2: "centrado en el dinero", 3: "centrado en el esfuerzo y la iniciativa",
           4: "centrado en el hogar", 5: "centrado en la creatividad y el aprendizaje",
           6: "centrado en el servicio y el esfuerzo", 7: "centrado en las alianzas",
           8: "centrado en cambios profundos", 9: "centrado en el aprendizaje y la suerte",
           10: "centrado en el trabajo", 11: "centrado en logros y redes",
           12: "centrado en el descanso y en soltar"},
    "pt": {1: "focado em você", 2: "focado em dinheiro", 3: "focado em esforço e iniciativa",
           4: "focado na casa", 5: "focado em criatividade e aprendizado",
           6: "focado em serviço e esforço", 7: "focado em parcerias",
           8: "focado em mudanças profundas", 9: "focado em aprendizado e sorte",
           10: "focado no trabalho", 11: "focado em conquistas e rede de contatos",
           12: "focado em descanso e desapego"},
    "hinglish": {1: "Khud par kendrit", 2: "Paise par kendrit", 3: "Mehnat aur pehal par kendrit",
                 4: "Ghar par kendrit", 5: "Rachnatmakta aur seekhne par kendrit",
                 6: "Seva aur mehnat par kendrit", 7: "Partnership par kendrit",
                 8: "Gehre badlaav par kendrit", 9: "Seekhne aur kismat par kendrit",
                 10: "Kaam par kendrit", 11: "Laabh aur network par kendrit",
                 12: "Aaram aur chhodne par kendrit"},
}


def pick(table: Dict[str, dict], lang: str):
    """The language's table, English if the language has none."""
    return table.get(lang) or table["en"]


FULL_MONTHS: Dict[str, tuple] = {
    "en": ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"),
    "pt": ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
           "setembro", "outubro", "novembro", "dezembro"),
    "hinglish": ("January", "February", "March", "April", "May", "June", "July", "August",
                 "September", "October", "November", "December"),
}


def month_year(d: date, lang: str) -> str:
    m = pick(FULL_MONTHS, lang)[d.month - 1]
    return f"{m} {d.year}" if lang in ("en", "hinglish") else f"{m} de {d.year}"


REVEAL_BIG_FROM_BIRTH: Dict[str, str] = {
    "en": "You are in a {planet} chapter. It runs until {end}.",
    "es": "Estás en una etapa de {planet}. Dura hasta {end}.",
    "pt": "Você está em uma fase de {planet}. Ela vai até {end}.",
    "hinglish": "Aap {planet} ke daur mein hain. Ye {end} tak chalega.",
}
