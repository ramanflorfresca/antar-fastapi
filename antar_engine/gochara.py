"""
Gochara (transits counted from the natal Moon) with vedha, after B.V. Raman's Hindu Predictive Astrology, ch. XXXIV.
Deterministic, no LLM. Read every transit from the natal Moon sign. Jupiter and Saturn set the year's background,
Sun/Mars/Mercury/Venus the month, the Moon the day. A favourable house is cancelled when another planet stands in its
paired obstruction (vedha) house. Only vedha pairs the scan of the book gives reliably are applied (Sun, Moon, Jupiter);
Mars, Saturn, Mercury and Venus are shown unadjusted and flagged so. Rahu and Ketu are always unfavourable. Sun and
Saturn, and Moon and Mercury, never obstruct each other.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional

from antar_engine.transit_signs import transit_signs

FAVOURABLE = {"Sun": (3, 6, 10, 11), "Moon": (1, 3, 6, 7, 10, 11), "Mars": (3, 6, 11), "Mercury": (2, 4, 6, 8, 10, 11),
              "Jupiter": (2, 5, 7, 9, 11), "Venus": (1, 2, 3, 4, 5, 8, 9, 11, 12), "Saturn": (3, 6, 11)}
VEDHA = {"Sun": {11: 5, 3: 9, 10: 4, 6: 12},
         "Moon": {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8},
         "Jupiter": {2: 12, 5: 4, 7: 3, 9: 10, 11: 8}}
NO_VEDHA = {frozenset(("Sun", "Saturn")), frozenset(("Moon", "Mercury"))}
CADENCE = {"Jupiter": "year", "Saturn": "year", "Sun": "month", "Mars": "month", "Mercury": "month", "Venus": "month",
           "Moon": "day", "Rahu": "year", "Ketu": "year"}

# plain effect per planet and state; no planet names (what each stands for instead)
TEXT = {
    "Jupiter": {"good": ("Luck, good advice and growth are on your side in this stretch.",
                         "La suerte, los buenos consejos y el crecimiento están de tu lado en esta etapa."),
                "blocked": ("A helpful stretch for luck and advice is held back by something in the way.",
                            "Una etapa favorable para la suerte y los consejos está frenada por algo en el camino."),
                "bad": ("Luck and guidance feel thinner than usual in this stretch; go slower on big bets.",
                        "La suerte y la guía se sienten más escasas en esta etapa; ve más despacio con las apuestas grandes.")},
    "Saturn": {"good": ("Hard work and discipline pay off in this stretch.",
                        "El trabajo duro y la disciplina dan fruto en esta etapa."),
               "blocked": ("Hard work should pay off, but a hindrance delays the result.",
                           "El trabajo duro debería dar fruto, pero un obstáculo retrasa el resultado."),
               "bad": ("This stretch asks for patience; effort is slow to show results.",
                       "Esta etapa pide paciencia; el esfuerzo tarda en dar resultados.")},
    "Sun": {"good": ("Authority and confidence work for you this month.", "La autoridad y la confianza juegan a tu favor este mes."),
            "blocked": ("Confidence is there, but something obstructs it this month.", "La confianza está, pero algo la obstruye este mes."),
            "bad": ("Authority and confidence are harder to command this month.", "La autoridad y la confianza cuestan más este mes.")},
    "Mars": {"good": ("Drive and courage are strong this month; push what matters.", "El impulso y el valor están fuertes este mes; empuja lo importante."),
             "blocked": ("Drive is strong, but a hindrance slows it this month.", "El impulso es fuerte, pero un obstáculo lo frena este mes."),
             "bad": ("Drive runs hot or scattered this month; avoid needless conflict.", "El impulso va acalorado o disperso este mes; evita conflictos innecesarios.")},
    "Mercury": {"good": ("Clear thinking and deal-making go well this month.", "El pensamiento claro y las negociaciones van bien este mes."),
                "blocked": ("Deals and thinking could go well, but something gets in the way.", "Las negociaciones y el pensamiento podrían ir bien, pero algo estorba."),
                "bad": ("Check details twice in deals and messages this month.", "Revisa dos veces los detalles en acuerdos y mensajes este mes.")},
    "Venus": {"good": ("Comfort, partnership and pleasant dealings come easier this month.", "La comodidad, la pareja y los tratos agradables fluyen más fácil este mes."),
              "blocked": ("Partnership and comfort are favoured, but something holds them back.", "La pareja y la comodidad están favorecidas, pero algo las frena."),
              "bad": ("Comfort and partnership need more care than usual this month.", "La comodidad y la pareja requieren más cuidado que de costumbre este mes.")},
    "Moon": {"good": ("A steady, supportive day for your mood and plans.", "Un día estable y de apoyo para tu ánimo y tus planes."),
             "blocked": ("A day that starts well but gets obstructed.", "Un día que empieza bien pero se obstruye."),
             "bad": ("A day to keep plans light; mood and energy run lower.", "Un día para planes ligeros; el ánimo y la energía van más bajos.")},
}


def house_from(moon_sign: int, planet_sign: int) -> int:
    return (planet_sign - moon_sign) % 12 + 1


def state_on(moon_sign: int, d: date) -> Dict[str, dict]:
    """For each transiting planet on a date: house from natal Moon and its state (good / blocked / bad)."""
    signs = transit_signs(d)
    houses = {p: house_from(moon_sign, s) for p, s in signs.items()}
    out = {}
    for p, h in houses.items():
        if p in ("Rahu", "Ketu"):
            out[p] = {"house": h, "state": "bad", "vedha_checked": False}
            continue
        if h not in FAVOURABLE[p]:
            out[p] = {"house": h, "state": "bad", "vedha_checked": p in VEDHA}
            continue
        v = VEDHA.get(p, {}).get(h)
        blocked = v is not None and any(q != p and houses[q] == v and frozenset((p, q)) not in NO_VEDHA for q in houses)
        out[p] = {"house": h, "state": "blocked" if blocked else "good", "vedha_checked": p in VEDHA}
    return out


def _line(p, st, lang):
    t = TEXT[p][st["state"]]
    return {"planet_key": p, "cadence": CADENCE[p], "house_from_moon": st["house"], "state": st["state"],
            "vedha_checked": st["vedha_checked"], "text": t[1] if lang == "es" else t[0]}


def outlook(moon_sign: int, start: date, days: int = 7, language: str = "en") -> dict:
    """Weekly Gochara: background (Jupiter, Saturn), this-month planets, and the Moon day by day."""
    now = state_on(moon_sign, start)
    dayrows = []
    for i in range(days):
        d = start + timedelta(days=i)
        m = state_on(moon_sign, d)["Moon"]
        dayrows.append({"date": d.isoformat(), "house_from_moon": m["house"], "state": m["state"]})
    changes = {}
    end_state = state_on(moon_sign, start + timedelta(days=days - 1))
    for p in ("Sun", "Mars", "Mercury", "Venus", "Jupiter", "Saturn"):
        if end_state[p]["state"] != now[p]["state"]:
            changes[p] = end_state[p]["state"]
    lang = "es" if language == "es" else "en"
    return {
        "frame": "moon_sign_gochara",
        "background": [_line(p, now[p], lang) for p in ("Jupiter", "Saturn")],
        "this_month": [_line(p, now[p], lang) for p in ("Sun", "Mars", "Mercury", "Venus")],
        "moon_days": [{**r, "text": TEXT["Moon"][r["state"]][1 if lang == "es" else 0]} for r in dayrows],
        "best_days": [r["date"] for r in dayrows if r["state"] == "good"],
        "slow_days": [r["date"] for r in dayrows if r["state"] == "bad"],
        "changes_this_week": changes,
    }
