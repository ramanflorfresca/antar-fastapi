"""[decision-i18n 2026-10-10] Spanish vocabulary for the decision blocks (Today / This Month / This Year / Ask).

The blocks are DETERMINISTIC templates, so Spanish is written natively here — not machine-translated — and the
Spanish payloads feed them a mix of native-Spanish prose (haz_hoy, build_this_year, priority_actions …) and
English structural labels (domain labels, arc names, `lit_domain`, tara labels). Every English label the
composers can meet has an entry below; an UNKNOWN label returns None so the caller omits the clause rather than
leak English into a Spanish answer.

Only `es` is wired. Adding `pt` = one more column in each table + the template dicts in the composers."""
from __future__ import annotations

from datetime import date

PLANET = {"es": {"Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio", "Jupiter": "Júpiter",
                 "Venus": "Venus", "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"}}
SIGN = {"es": {"Aries": "Aries", "Taurus": "Tauro", "Gemini": "Géminis", "Cancer": "Cáncer", "Leo": "Leo",
               "Virgo": "Virgo", "Libra": "Libra", "Scorpio": "Escorpio", "Sagittarius": "Sagitario",
               "Capricorn": "Capricornio", "Aquarius": "Acuario", "Pisces": "Piscis"}}
MONTH_LONG = {"es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                     "octubre", "noviembre", "diciembre"]}
MONTH_SHORT = {"es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}
# Spanish month names (long + short) -> number, for parsing dates out of Spanish prose
MONTH_NUM_ES = {**{m: i for i, m in enumerate(MONTH_LONG["es"], 1)}, **{m: i for i, m in enumerate(MONTH_SHORT["es"], 1)},
                "sept": 9, "setiembre": 9}

# the engine's domain keys (active_domains[].key) → Spanish
DOMAIN = {"es": {"speculation": "la especulación", "travel": "los viajes", "money": "el dinero", "work": "el trabajo",
                 "relationship": "las relaciones", "family": "la familia", "health": "la salud", "home": "el hogar",
                 "authority": "los asuntos legales", "spiritual": "tu vida interior"}}
# short noun for "commit to X" / "time the X" in holds / breaks
DOMAIN_NOUN = {"es": {"money": "la decisión de ahorro o cobro", "work": "el trabajo visible", "travel": "la planificación de viajes",
                      "speculation": "el tamaño de las apuestas", "relationship": "la conversación importante",
                      "family": "los asuntos familiares", "health": "la rutina de salud",
                      "home": "las decisiones sobre el hogar y la propiedad", "authority": "los asuntos legales o de autoridad"}}
DOMAIN_RISK = {"es": {"travel": "viajes largos", "speculation": "apuestas especulativas", "work": "una sobrecarga de trabajo",
                      "money": "compras grandes", "relationship": "una conversación difícil"}}

# Today: evidence.chosen keys
LEAD = {"es": {"work": "el trabajo y la reputación", "network": "los ingresos y tu red de contactos", "money": "el dinero",
               "father": "la fortuna, los mentores y la visión a largo plazo", "body": "la salud y la energía",
               "relationship": "las relaciones cercanas", "family": "la familia", "travel": "los viajes", "home": "el hogar y la propiedad"}}
# Today: domains[].key (v2 / legacy) — a "needs care" area
CARE = {"es": {"mind": "La mente", "body": "La salud", "work": "La carrera", "money": "El dinero", "family": "La familia",
               "relationship": "Las relaciones", "love": "El amor", "spiritual": "La vida interior", "travel": "Los viajes",
               "home": "El hogar", "speculation": "Los riesgos y la especulación", "career": "La carrera"}}
# Today: the Moon's house from the lagna → what it lights (English text comes from the payload's own lit_domain)
HOUSE_LIT = {"es": {1: "tú y tu vitalidad", 2: "dinero y familia", 3: "iniciativa y comunicación", 4: "hogar y paz interior",
                    5: "creatividad y aprendizaje", 6: "trabajo diario y obstáculos", 7: "pareja y alianzas",
                    8: "cambios profundos y dinero compartido", 9: "fortuna y viajes", 10: "carrera y reputación",
                    11: "ingresos y red de contactos", 12: "descanso, el exterior y la vida interior"}}
# the tara label the engine ships (moon_transit._QUALITY_LABEL) → Spanish
QUALITY = {"es": {"strongly in your favour": "muy a tu favor", "in your favour": "a tu favor", "neutral": "neutra",
                  "handle with care": "con cuidado", "runs against you": "va en tu contra"}}
SIGNAL_DIR = {"es": {"friction": "fricción", "adverse": "adverso", "supportive": "favorable"}}

# This Year: arcs[].key / .trend
ARC = {"es": {"career": "la carrera", "business": "el negocio", "wealth": "el dinero", "love": "el amor", "health": "la salud",
              "family": "la familia", "home": "el hogar", "travel": "los viajes", "education": "los estudios"}}
TREND = {"es": {"rising": "va en ascenso", "pressure": "está bajo presión", "falling": "está bajo presión"}}


def planet(name: str, lang: str) -> str:
    return PLANET.get(lang, {}).get(name, name)


def sign(name: str, lang: str) -> str:
    return SIGN.get(lang, {}).get(name, name)


def date_long(d: date, lang: str) -> str:
    """April 25, 2029 / 25 de abril de 2029"""
    if lang == "es":
        return f"{d.day} de {MONTH_LONG['es'][d.month - 1]} de {d.year}"
    return d.strftime("%B %-d, %Y")


def date_short(d: date, lang: str) -> str:
    """Oct 14 / 14 oct"""
    if lang == "es":
        return f"{d.day} {MONTH_SHORT['es'][d.month - 1]}"
    return d.strftime("%b %-d")


def month_year(d: date, lang: str) -> str:
    """Nov 2026 / nov 2026"""
    if lang == "es":
        return f"{MONTH_SHORT['es'][d.month - 1]} {d.year}"
    return d.strftime("%b %Y")


def quality(label: str, lang: str):
    return QUALITY.get(lang, {}).get((label or "").strip().lower())


MON_EN_ES = {"Jan": "ene", "Feb": "feb", "Mar": "mar", "Apr": "abr", "May": "may", "Jun": "jun", "Jul": "jul",
             "Aug": "ago", "Sep": "sep", "Oct": "oct", "Nov": "nov", "Dec": "dic"}


def es_label(label: str) -> str:
    """'Oct 26 \u2013 Nov 1' -> '26 oct \u2013 1 nov'; 'Oct 10\u201316' -> '10\u201316 oct' (English v2 week labels in a Spanish answer)."""
    import re
    s = label or ""
    s = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s*([\u2013-])\s*(\d{1,2})\b",
               lambda m: f"{m.group(2)}{m.group(3)}{m.group(4)} {MON_EN_ES[m.group(1)]}", s)
    s = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\b",
               lambda m: f"{m.group(2)} {MON_EN_ES[m.group(1)]}", s)
    return s


def join_list(items, lang: str) -> str:
    items = [i for i in items if i]
    word = {"es": "y", "en": "and"}.get(lang, "and")
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {word} " + items[-1]
