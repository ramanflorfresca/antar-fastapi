"""
antar_engine/circle_copy.py
───────────────────────────
Plain-words copy for Circle (the two-sided People tab): relation nouns, the shared
"Between us" page, the joint check-back question and the pair-aware Ask answer.

Same rules as topic_copy: en / es / pt / hinglish (anything else, Devanagari `hi` included,
is served in English and the response says so); no system names, no pricing, no consent
logic, nothing that claims more than the dated windows say. Every string lives here so the
jargon guard (tests/test_circle.py) has ONE place to prove clean.
"""
from __future__ import annotations

from typing import Dict

from antar_engine import topic_copy as C

LANGS = C.COPY_LANGUAGES


def lang_of(raw) -> str:
    return C.serve_language(raw)


def pick(table: Dict[str, dict], lang: str):
    return table.get(lang) or table["en"]


# ── relation nouns: what the OTHER person is to me ──────────────────────────────
# keys = people_links relations, plus "advisee" (the display-only inverse of advisor)
REL_NOUN: Dict[str, Dict[str, str]] = {
    "en": {"romantic": "Partner", "spouse": "Husband or wife", "business": "Business partner",
           "cofounder": "Cofounder", "friend": "Friend", "family": "Family",
           "sibling": "Brother or sister", "parent": "Parent", "child": "Child",
           "advisor": "Advisor or mentor", "advisee": "Mentee", "employee": "Team member",
           "boss": "Manager"},
    "es": {"romantic": "Pareja", "spouse": "Esposo o esposa", "business": "Socio de negocio",
           "cofounder": "Cofundador", "friend": "Amigo", "family": "Familia",
           "sibling": "Hermano o hermana", "parent": "Madre o padre", "child": "Hijo o hija",
           "advisor": "Asesor o mentor", "advisee": "Aprendiz", "employee": "Miembro del equipo",
           "boss": "Jefe o jefa"},
    "pt": {"romantic": "Parceiro", "spouse": "Marido ou esposa", "business": "Sócio de negócio",
           "cofounder": "Cofundador", "friend": "Amigo", "family": "Família",
           "sibling": "Irmão ou irmã", "parent": "Mãe ou pai", "child": "Filho ou filha",
           "advisor": "Conselheiro ou mentor", "advisee": "Mentorado", "employee": "Membro da equipe",
           "boss": "Chefe"},
    "hinglish": {"romantic": "Partner", "spouse": "Pati ya patni", "business": "Business partner",
                 "cofounder": "Cofounder", "friend": "Dost", "family": "Parivaar",
                 "sibling": "Bhai ya behen", "parent": "Mata ya pita", "child": "Beta ya beti",
                 "advisor": "Salahkaar ya mentor", "advisee": "Mentee", "employee": "Team member",
                 "boss": "Manager"},
}

# The personal heading each relation sits under on the Circle home ("My parents", "My team"),
# in display order. Parent/child etc. are the relation keys the circle stores.
GROUP_ORDER = ("spouse", "romantic", "child", "parent", "sibling", "family", "cofounder",
               "business", "employee", "boss", "friend", "advisor", "advisee")
GROUP_HEADING: Dict[str, Dict[str, str]] = {
    "en": {"spouse": "My spouse", "romantic": "My partner", "child": "My kids", "parent": "My parents",
           "sibling": "My siblings", "family": "My family", "cofounder": "My co-founder",
           "business": "My business partner", "employee": "My team", "boss": "My manager",
           "friend": "My friends", "advisor": "My guides", "advisee": "People I mentor"},
    "es": {"spouse": "Mi esposo o esposa", "romantic": "Mi pareja", "child": "Mis hijos", "parent": "Mis padres",
           "sibling": "Mis hermanos", "family": "Mi familia", "cofounder": "Mi cofundador",
           "business": "Mi socio de negocio", "employee": "Mi equipo", "boss": "Mi jefe",
           "friend": "Mis amigos", "advisor": "Mis guías", "advisee": "Quienes oriento"},
    "pt": {"spouse": "Meu marido ou esposa", "romantic": "Meu parceiro", "child": "Meus filhos", "parent": "Meus pais",
           "sibling": "Meus irmãos", "family": "Minha família", "cofounder": "Meu cofundador",
           "business": "Meu sócio de negócio", "employee": "Minha equipe", "boss": "Meu chefe",
           "friend": "Meus amigos", "advisor": "Meus guias", "advisee": "Quem eu oriento"},
    "hinglish": {"spouse": "Mera jeevansathi", "romantic": "Mera partner", "child": "Mere bachche",
                 "parent": "Mere mummy-papa", "sibling": "Mere bhai-behen", "family": "Mera parivaar",
                 "cofounder": "Mera cofounder", "business": "Mera business partner", "employee": "Meri team",
                 "boss": "Mera manager", "friend": "Mere dost", "advisor": "Mere margdarshak",
                 "advisee": "Jinhe main guide karta hoon"},
}


def group_heading(rel: str, lang: str) -> str:
    t = pick(GROUP_HEADING, lang)
    return t.get(rel) or GROUP_HEADING["en"].get(rel) or "My people"


def group_order(rel: str) -> int:
    return GROUP_ORDER.index(rel) if rel in GROUP_ORDER else len(GROUP_ORDER)


# what A is to B, given what B is to A
INVERSE = {"parent": "child", "child": "parent", "employee": "boss", "boss": "employee",
           "advisor": "advisee", "advisee": "advisor"}


def inverse_relation(rel: str) -> str:
    return INVERSE.get(rel, rel)


def rel_noun(rel: str, lang: str) -> str:
    t = pick(REL_NOUN, lang)
    return t.get(rel) or REL_NOUN["en"].get(rel) or str(rel).replace("-", " ").title()


# ── the shared page ──────────────────────────────────────────────────────────
BULLET: Dict[str, Dict[str, str]] = {
    "en": {
        "best_both": "You both have an open stretch for {area} on these days.",
        "best_overlap": "Only the days you share are shown, so this is where your two stretches line up.",
        "care_one": "At least one of you is in a stretch that asks for care around {area} on these days.",
        "care_why": "That makes it a better time to go slowly together than to commit to something big.",
    },
    "es": {
        "best_both": "Los dos tienen un tramo abierto para {area} en estos días.",
        "best_overlap": "Solo se muestran los días que comparten, así que aquí coinciden sus dos tramos.",
        "care_one": "Al menos uno de ustedes está en un tramo que pide cuidado con {area} en estos días.",
        "care_why": "Eso lo hace mejor momento para ir despacio juntos que para comprometerse con algo grande.",
    },
    "pt": {
        "best_both": "Vocês dois têm um trecho aberto para {area} nestes dias.",
        "best_overlap": "Só aparecem os dias que vocês compartilham, então é aqui que os dois trechos se alinham.",
        "care_one": "Pelo menos um de vocês está num trecho que pede cuidado com {area} nestes dias.",
        "care_why": "Isso faz deste um bom momento para ir devagar juntos, e não para se comprometer com algo grande.",
    },
    "hinglish": {
        "best_both": "Aap dono ke liye {area} ka khula stretch in dinon mein hai.",
        "best_overlap": "Sirf wahi din dikhaye gaye hain jo aap dono ke common hain, yaani jahan dono stretch milte hain.",
        "care_one": "Aap mein se kam se kam ek ka stretch in dinon mein {area} par savdhaani maangta hai.",
        "care_why": "Isliye ye saath mein dheere chalne ka waqt hai, koi bada commitment karne ka nahin.",
    },
}

BASED_ON_BOTH: Dict[str, str] = {
    "en": "Both of your charts", "es": "Las cartas de los dos",
    "pt": "Os mapas de vocês dois", "hinglish": "Aap dono ke charts",
}

NONE_BEST: Dict[str, str] = {
    "en": "No shared open stretch for {area} in {span}. Your good stretches don't land on the same days.",
    "es": "No hay un tramo abierto compartido para {area} en {span}. Sus buenos tramos no caen en los mismos días.",
    "pt": "Não há um trecho aberto compartilhado para {area} em {span}. Os bons trechos de vocês não caem nos mesmos dias.",
    "hinglish": "{span} mein {area} ke liye koi common khula stretch nahin hai. Aap dono ke achhe stretch ek hi din par nahin padte.",
}
NONE_ALL: Dict[str, str] = {
    "en": "Nothing lines up for the two of you in {span}. That is a real answer: it is a steady stretch, not a missing one.",
    "es": "Nada coincide para ustedes dos en {span}. Es una respuesta real: es un tramo estable, no uno que falte.",
    "pt": "Nada se alinha para vocês dois em {span}. É uma resposta real: é um trecho estável, não um que falta.",
    "hinglish": "{span} mein aap dono ke liye kuch bhi common nahin banta. Ye sach mein ek jawab hai: ye sthir stretch hai, koi kami nahin.",
}
CARE_NOTE: Dict[str, str] = {
    "en": "One or both of you is in a careful stretch on these days.",
    "es": "Uno o los dos están en un tramo de cuidado en estos días.",
    "pt": "Um ou os dois estão num trecho de cuidado nestes dias.",
    "hinglish": "Aap mein se ek ya dono in dinon mein savdhaani wale stretch mein hain.",
}
SPAN: Dict[str, Dict[str, str]] = {
    "month": {k: v["month"] for k, v in C.WHOLE_SPAN.items()},
    "season": {k: v["season"] for k, v in C.WHOLE_SPAN.items()},
}

HEADLINE_BEST: Dict[str, str] = {
    "en": "Your best shared window: {topic}, {range}.",
    "es": "Su mejor ventana compartida: {topic}, {range}.",
    "pt": "A melhor janela de vocês: {topic}, {range}.",
    "hinglish": "Aap dono ki sabse achhi shared window: {topic}, {range}.",
}
HEADLINE_NONE: Dict[str, str] = {
    "en": "No shared open window right now. That is a real answer, not a missing one.",
    "es": "Ahora no hay una ventana abierta compartida. Es una respuesta real, no una que falte.",
    "pt": "Agora não há uma janela aberta compartilhada. É uma resposta real, não uma que falta.",
    "hinglish": "Abhi koi shared khuli window nahin hai. Ye sach mein ek jawab hai, koi kami nahin.",
}

DAY_UNSHARED: Dict[str, str] = {
    "en": "They haven't turned on sharing their day.",
    "es": "Esta persona no ha activado compartir su día.",
    "pt": "Essa pessoa não ativou o compartilhamento do dia dela.",
    "hinglish": "Unhone apna din share karna on nahin kiya hai.",
}

# ── the one-line "next shared window" on the Circle list ──
NEXT_WINDOW: Dict[str, Dict[str, str]] = {
    "open": {
        "en": "Your next shared open stretch: {range}.",
        "es": "Su próximo tramo abierto compartido: {range}.",
        "pt": "O próximo trecho aberto de vocês: {range}.",
        "hinglish": "Aap dono ka agla shared khula stretch: {range}.",
    },
    "care": {
        "en": "A shared stretch that asks for care: {range}.",
        "es": "Un tramo compartido que pide cuidado: {range}.",
        "pt": "Um trecho compartilhado que pede cuidado: {range}.",
        "hinglish": "Ek shared stretch jo savdhaani maangta hai: {range}.",
    },
}

# ── Ask chips on the pair page (each names the person + a joint marker the Ask resolver reads) ──
CHIPS: Dict[str, Dict[str, str]] = {
    "en": {"sign": "When should {name} and I sign something?",
           "money": "When is a good time for {name} and me to talk about money?",
           "work": "When should {name} and I start something together?",
           "love": "When is a good time for {name} and me to have a heart-to-heart?"},
    "es": {"sign": "¿Cuándo deberíamos {name} y yo firmar algo?",
           "money": "¿Cuándo es un buen momento para que {name} y yo hablemos de dinero?",
           "work": "¿Cuándo deberíamos {name} y yo empezar algo juntos?",
           "love": "¿Cuándo es un buen momento para que {name} y yo hablemos con el corazón?"},
    "pt": {"sign": "Quando eu e {name} devemos assinar algo?",
           "money": "Quando é um bom momento para eu e {name} conversarmos sobre dinheiro?",
           "work": "Quando eu e {name} devemos começar algo juntos?",
           "love": "Quando é um bom momento para eu e {name} termos uma conversa sincera?"},
    "hinglish": {"sign": "{name} aur main kab kuch sign karein?",
                 "money": "{name} aur main paise ki baat kab karein?",
                 "work": "{name} aur main saath mein kuch kab shuru karein?",
                 "love": "{name} aur main dil ki baat kab karein?"},
}
CHIP_TOPIC = {"sign": "business", "money": "money", "work": "career", "love": "love"}

# ── pair-aware Ask answer ────────────────────────────────────────────────────
ASK_BEST: Dict[str, str] = {
    "en": "For {topic} with {name}, your best shared window is {range}. {why}",
    "es": "Para {topic} con {name}, su mejor ventana compartida es {range}. {why}",
    "pt": "Para {topic} com {name}, a melhor janela de vocês é {range}. {why}",
    "hinglish": "{name} ke saath {topic} ke liye aap dono ki sabse achhi shared window {range} hai. {why}",
}
ASK_NONE: Dict[str, str] = {
    "en": "For {topic} with {name}, your open stretches don't land on the same days in the next 30 days or this season. I won't invent a window: better to wait, or keep it light until one opens.",
    "es": "Para {topic} con {name}, sus tramos abiertos no caen en los mismos días en los próximos 30 días ni en esta etapa. No voy a inventar una ventana: mejor esperar, o mantenerlo ligero hasta que se abra una.",
    "pt": "Para {topic} com {name}, os trechos abertos de vocês não caem nos mesmos dias nos próximos 30 dias nem nesta fase. Não vou inventar uma janela: melhor esperar, ou manter leve até que uma se abra.",
    "hinglish": "{name} ke saath {topic} ke liye agle 30 din ya is daur mein aap dono ke khule stretch ek hi din par nahin padte. Main koi window gadhunga nahin: behtar hai ruk jaayein, ya halka rakhein jab tak ek na khule.",
}
ASK_CARE: Dict[str, str] = {
    "en": "Be careful around {range}: at least one of you is in a stretch that asks for care.",
    "es": "Ojo alrededor de {range}: al menos uno de ustedes está en un tramo que pide cuidado.",
    "pt": "Atenção em torno de {range}: pelo menos um de vocês está num trecho que pede cuidado.",
    "hinglish": "{range} ke aaspaas savdhaan rahein: aap mein se kam se kam ek ka stretch savdhaani maangta hai.",
}
ASK_NEXT: Dict[str, str] = {
    "en": "Open the Between us page to see every shared window.",
    "es": "Abre la página Entre nosotros para ver todas las ventanas compartidas.",
    "pt": "Abra a página Entre nós para ver todas as janelas compartilhadas.",
    "hinglish": "Saari shared windows dekhne ke liye Between us page kholiye.",
}

# ── joint check-back ─────────────────────────────────────────────────────────
JOINT_QUESTION: Dict[str, Dict[str, str]] = {
    "best": {
        "en": "Your shared {topic} window, {range}, has passed. Did it hold for the two of you?",
        "es": "Su ventana compartida de {topic}, {range}, ya pasó. ¿Se cumplió para ustedes dos?",
        "pt": "A janela compartilhada de {topic}, {range}, já passou. Ela se confirmou para vocês dois?",
        "hinglish": "Aap dono ka shared {topic} window, {range}, nikal gaya. Kya woh aap dono ke liye sahi nikla?",
    },
    "watch": {
        "en": "The shared caution we flagged for {topic}, {range}, has passed. Did it turn out to matter?",
        "es": "La precaución compartida que marcamos para {topic}, {range}, ya pasó. ¿Resultó importar?",
        "pt": "O cuidado compartilhado que apontamos para {topic}, {range}, já passou. Ele fez diferença?",
        "hinglish": "{topic} ke liye jo shared savdhaani batayi thi, {range}, nikal gayi. Kya woh sach mein matter kiya?",
    },
}

TEXTS = (REL_NOUN, GROUP_HEADING, BULLET, BASED_ON_BOTH, NONE_BEST, NONE_ALL, CARE_NOTE, HEADLINE_BEST,
         HEADLINE_NONE, DAY_UNSHARED, CHIPS, ASK_BEST, ASK_NONE, ASK_CARE, ASK_NEXT,
         JOINT_QUESTION["best"], JOINT_QUESTION["watch"], NEXT_WINDOW["open"], NEXT_WINDOW["care"])    # for the jargon guard
