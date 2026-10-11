"""[medical-safety 2026-10-10] Questions about a MEDICAL PROCEDURE ("should I have the surgery now or later?").

Audit of 80 answers across 20 topics found the one answer that must never be improvised: for "Should I have the surgery
now or later?" the model wrote "the timing is genuinely supportive for a health procedure", "the window is open, and
waiting past it means the support thins out" and moves like "Book the surgical consultation this week — if you wait
past January you'll have to start the process again". A chart cannot say whether or when surgery is right, and an
invented deadline on a medical decision is a safety and store-review liability.

So these questions get a FIXED answer (en / es / pt, native text): the chart cannot decide this — that is for the
reader and their doctor; the only thing the chart is used for is how the reader is placed to RECOVER (the 6th-house
ruler's strength, same weakness test as the 📍 line); the move is: ask the surgeon for the specific risk of acting now
vs waiting, get a second opinion, plan extra recovery time and support. No verdict, no timing window, no deadline."""
from __future__ import annotations

import re

_EN = (r"surger(y|ies)|surgical|surgeon|transplant|chemo(therapy)?|radiotherapy|biopsy|angioplasty|c[- ]?section|"
       r"cesarean|caesarean|(hip|knee|joint) replacement|bypass|operated on|operate on me|"
       r"(have|get|undergo|schedule|book|need|do)\s+(?:\w+\s+){0,2}(?:an?\s+)?(operation|procedure)")
_ES = (r"cirug[ií]a|quir[uú]rgic[oa]|cirujan[oa]|trasplante|quimioterapia|radioterapia|biopsia|ces[aá]rea|"
       r"operarme|operarse|me operen|me operaran|me operarán|pr[oó]tesis de (rodilla|cadera)|operaci[oó]n (quir|m[eé]dica)|"
       r"(hacerme|someterme a|tener) (una )?(operaci[oó]n|intervenci[oó]n)")
_PT = (r"cirurgia|cir[uú]rgic[oa]|cirurgi[aã]o|transplante|quimioterapia|radioterapia|bi[oó]psia|cesari(ana|na)|"
       r"me operar|operar-me|opera[cç][aã]o (cir[uú]rgica|m[eé]dica)|pr[oó]tese de (joelho|quadril)|"
       r"(fazer|ter) (uma )?(opera[cç][aã]o|interven[cç][aã]o cir)")
_RX = re.compile(r"(?i)\b(?:" + "|".join((_EN, _ES, _PT)) + r")\b")

_TX = {
    "en": {
        "lead": "The chart can't say whether surgery is right for you or when to have it — that is a medical decision for you and your doctor.",
        "weak": " What it does show is how you are placed to recover: the ruler of your 6th house is weakened, so recovery tends to run slower than the effort you put in — build in more recovery time and support than you think you need.",
        "fine": " What it does show is how you are placed to recover: your health house is well supported, so good preparation and rest will count for a lot.",
        "tail": " Plan around your doctor's advice and your own recovery, not around a date from the chart.",
        "next": "Ask your surgeon for the specific risk of acting now versus waiting, get a second opinion before you commit, and plan extra recovery time and support around whatever date you choose.",
    },
    "es": {
        "lead": "La carta no puede decir si la cirugía es lo correcto para ti ni cuándo hacerla — esa es una decisión médica entre tú y tu médico.",
        "weak": " Lo que sí muestra es cómo estás para recuperarte: el regente de tu casa 6 está debilitado, así que la recuperación tiende a ir más lenta que el esfuerzo que haces — reserva más tiempo de recuperación y apoyo del que crees necesitar.",
        "fine": " Lo que sí muestra es cómo estás para recuperarte: tu casa de la salud está bien apoyada, así que una buena preparación y el descanso valdrán mucho.",
        "tail": " Organízate según el consejo de tu médico y tu propia recuperación, no según una fecha de la carta.",
        "next": "Pregunta a tu cirujano por el riesgo concreto de actuar ahora frente a esperar, pide una segunda opinión antes de decidir y reserva tiempo extra de recuperación y apoyo para la fecha que elijas.",
    },
    "pt": {
        "lead": "O mapa não pode dizer se a cirurgia é o certo para você nem quando fazê-la — essa é uma decisão médica entre você e o seu médico.",
        "weak": " O que ele mostra é como você está para se recuperar: o regente da sua casa 6 está enfraquecido, então a recuperação tende a ser mais lenta que o esforço que você faz — reserve mais tempo de recuperação e apoio do que acha necessário.",
        "fine": " O que ele mostra é como você está para se recuperar: a sua casa da saúde está bem apoiada, então uma boa preparação e o descanso farão muita diferença.",
        "tail": " Organize-se pela orientação do seu médico e pela sua própria recuperação, não por uma data do mapa.",
        "next": "Pergunte ao seu cirurgião qual é o risco específico de agir agora versus esperar, peça uma segunda opinião antes de decidir e reserve tempo extra de recuperação e apoio para a data que escolher.",
    },
}


def is_medical_procedure_q(question: str) -> bool:
    return bool(_RX.search(question or ""))


def safe_answer(chart_data, dashas, language: str = "en"):
    """{"read", "next"} in en / es / pt, or None for any other language (the caller keeps its normal path)."""
    tx = _TX.get(language)
    if not tx:
        return None
    recovery = ""
    try:
        from antar_engine import ask_basis as B
        planets = (chart_data or {}).get("planets") or {}
        lagna = ((chart_data or {}).get("lagna") or {}).get("sign")
        if planets and lagna in B._SIGNS:
            h = 6                                              # the house of illness and recovery
            lord = B._LORD[B._SIGNS[(B._SIGNS.index(lagna) + h - 1) % 12]]
            pl = planets.get(lord) or {}
            if pl.get("sign"):
                weak = any(n == "debilitated" or n.startswith("combust") for n in B._dignity(lord, pl["sign"], planets))
                recovery = tx["weak"] if weak else tx["fine"]
    except Exception:
        recovery = ""
    return {"read": tx["lead"] + recovery + tx["tail"], "next": tx["next"]}
