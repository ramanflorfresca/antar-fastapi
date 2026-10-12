"""[basis-plain 2026-10-12] The "📍 why" line under an Ask answer, in plain words.

The technical version ("You're running Rahu–Rahu (sub-period ends Apr 25, 2029). Your 2nd house (money) is ruled by Saturn, which sits in your 6th house in Gemini. Jupiter, the main significator
here, is in your 2nd house, vargottama…") stays available as payload["basis_facts"] for anyone who wants it; the line people READ (WhatsApp has no collapse) says what it means:
the stretch of life you're in, the channel this area works through and whether it is strong or under strain, and whether the part of the chart that carries it is strong. en + es. Never raises; "" when nothing can be said.
"""
import re
from datetime import datetime
from typing import Any, Optional

_STRONG = ("exalted", "in its own sign", "vargottama", "exaltado", "en su propio signo")
_WEAK = ("debilitated", "combust", "debilitado", "combusto")
_MON_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _strength(notes) -> str:
    s = any(any(n.startswith(m) for m in _STRONG) for n in notes or [])
    w = any(any(n.startswith(m) for m in _WEAK) for n in notes or [])
    return "mixed" if s and w else "strong" if s else "weak" if w else ""


def _season_until(dashas, lang):
    """(season phrase, 'Mon YYYY') from the running Vimshottari lords, or (None, '')."""
    from antar_engine import ask_basis as B, positioning as P
    per = B._period(dashas)
    m = re.match(r"You're running (\w+)–(\w+) \(sub-period ends (.+)\)", per or "")
    if not m:
        return None, ""
    lead_for = (P._T[lang]["seasons"].get(m.group(1)) or (None, None))[0]
    try:
        d = datetime.strptime(m.group(3), "%b %d, %Y")
        until = f"{_MON_ES[d.month - 1]} {d.year}" if lang == "es" else d.strftime("%b %Y")
    except Exception:
        until = ""
    return lead_for, until


def build(concern: str, chart_data: Any, dashas: Any, language: str = "en") -> str:
    try:
        lang = "es" if language == "es" else "en"
        if language not in ("en", "es"):
            return ""
        from antar_engine import ask_basis as B
        from antar_engine.ask_consultation import CONCERN_HOUSES, CONCERN_KARAKAS
        houses = CONCERN_HOUSES.get(concern)
        planets = (chart_data or {}).get("planets") or {}
        lagna = ((chart_data or {}).get("lagna") or {}).get("sign")
        if not houses or lagna not in B._SIGNS or not planets:
            return ""
        h = B._PRIMARY.get(concern, houses[0])
        lord = B._LORD[B._SIGNS[(B._SIGNS.index(lagna) + h - 1) % 12]]
        pl = planets.get(lord) or {}
        if lang == "es":
            from antar_engine import ask_basis_es as E
            topic, channel = E._TOPIC.get(concern, concern), E._CHANNEL.get(pl.get("house"), "")
        else:
            topic, channel = B._TOPIC.get(concern, concern), B._CHANNEL.get(pl.get("house"), "")
        d9 = B.d9_planets(chart_data)
        bits = []
        lead_for, until = _season_until(dashas, lang)
        if lead_for:
            bits.append((f"You're in a long stretch of {lead_for}" + (f" (this part runs to {until})" if until else "") + ".") if lang == "en" else
                        (f"Estás en una etapa larga de {lead_for}" + (f" (esta parte llega hasta {until})" if until else "") + "."))
        if channel and pl.get("sign"):
            st = _strength(B._dignity(lord, pl["sign"], planets, d9))
            tail_en = {"strong": ", and that channel is strong", "weak": ", though that channel is under strain", "mixed": ", with both strengths and strains", "": ""}[st]
            tail_es = {"strong": " y ese canal es fuerte", "weak": ", aunque ese canal está bajo tensión", "mixed": ", con fortalezas y tensiones", "": ""}[st]
            bits.append(f"Your {topic} area works through {channel}{tail_en}." if lang == "en" else f"Tu área de {topic} funciona a través de {channel}{tail_es}.")
        for k in (CONCERN_KARAKAS.get(concern) or [])[:1]:
            if k == lord:
                continue
            kp = planets.get(k) or {}
            if kp.get("sign"):
                st = _strength(B._dignity(k, kp["sign"], planets, d9))
                if st:
                    word_en = {"strong": "strong", "weak": "under strain", "mixed": "mixed"}[st]
                    word_es = {"strong": "fuerte", "weak": "bajo tensión", "mixed": "con altibajos"}[st]
                    bits.append(f"The main support for {topic} is {word_en}." if lang == "en" else f"El principal apoyo de {topic} está {word_es}.")
        return " ".join(bits).strip()
    except Exception:
        return ""
