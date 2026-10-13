"""[seasons 2026-10-13] "Your next three years": the running chapter's shifts that fall inside the next 36 months, each with
its real dates, the engine's own plain words, and a per-chart read.

The per-chart read is what a generic table cannot say: whether that planet is a functional benefic or malefic for THIS rising
sign (the same tables the day score uses) and which houses it rules (from the rising sign and sign lordship), in plain words.
So Jupiter reads "supportive" in general but "growth with a cost" for a Capricorn rising chart, where it rules the 3rd and 12th.
Deterministic; builds on phase_view's shifts; invents no dates. Pure functions."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
SIGN_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
             "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
HOUSE_WORD = {"en": {1: "you and your vitality", 2: "money and speech", 3: "effort and communication", 4: "home and peace",
                     5: "creativity and children", 6: "work, service and health", 7: "partnerships", 8: "change and shared money",
                     9: "fortune and mentors", 10: "career and visibility", 11: "gains and your network", 12: "spending, rest and distance"},
              "es": {1: "tú y tu vitalidad", 2: "dinero y palabra", 3: "esfuerzo y comunicación", 4: "hogar y paz",
                     5: "creatividad e hijos", 6: "trabajo, servicio y salud", 7: "pareja y alianzas", 8: "cambio y dinero compartido",
                     9: "fortuna y mentores", 10: "carrera y visibilidad", 11: "ganancias y red", 12: "gasto, descanso y distancia"}}
_ORD = {"en": {1: "1st", 2: "2nd", 3: "3rd"}, "es": {}}


def _lang(language) -> str:
    return "es" if str(language or "en").lower().startswith("es") else "en"


def _ord(n: int, lg: str) -> str:
    if lg == "es":
        return f"{n}.º"
    return _ORD["en"].get(n) or f"{n}th"


def houses_ruled(planet: str, lagna_sign: str) -> List[int]:
    if lagna_sign not in SIGNS or planet not in SIGN_LORD.values():
        return []
    i = SIGNS.index(lagna_sign)
    return [h + 1 for h in range(12) if SIGN_LORD[SIGNS[(i + h) % 12]] == planet]


def _acts_through(planet: str, chart_data: Optional[dict]) -> Optional[str]:
    """Rahu and Ketu rule no sign; they act through the planet that rules the sign they sit in."""
    try:
        sign = ((chart_data or {}).get("planets") or {}).get(planet, {}).get("sign")
        return SIGN_LORD.get(sign)
    except Exception:
        return None


def chart_read(planet: str, lagna_sign: str, chart_data: Optional[dict], engine_nature: str, lg: str) -> Dict[str, Any]:
    """{tone: supportive|testing|mixed|neutral, houses: [...], note: plain sentence}. Never raises."""
    out: Dict[str, Any] = {"tone": engine_nature if engine_nature in ("supportive", "testing") else "neutral", "houses": [], "note": ""}
    try:
        from antar_engine.practice_engine import is_functional_benefic, is_functional_malefic
        via = None
        target = planet
        if planet in ("Rahu", "Ketu"):
            via = _acts_through(planet, chart_data)
            target = via or ""
            fn = 0
        else:
            fn = 1 if is_functional_benefic(planet, lagna_sign) else (-1 if is_functional_malefic(planet, lagna_sign) else 0)
        if via:
            fn = 1 if is_functional_benefic(via, lagna_sign) else (-1 if is_functional_malefic(via, lagna_sign) else 0)
        hs = houses_ruled(target, lagna_sign) if target else []
        eng = engine_nature
        if eng == "supportive" and fn < 0:
            tone = "mixed"
        elif eng == "testing" and fn > 0:
            tone = "mixed"
        elif eng == "supportive" or fn > 0:
            tone = "supportive"
        elif eng == "testing" or fn < 0:
            tone = "testing"
        else:
            tone = "neutral"
        out["tone"], out["houses"] = tone, hs
        if hs:
            words = "; ".join(HOUSE_WORD[lg][h] for h in hs)
            names = " and ".join(_ord(h, lg) for h in hs)
            fnw = {1: ("supportive for you", "favorable para ti"), -1: ("a strain for you", "una carga para ti"),
                   0: ("neutral for you", "neutral para ti")}[fn][1 if lg == "es" else 0]
            lead = ("Esta etapa trabaja a través del planeta que rige donde se sitúa Rahu o Ketu. " if via and lg == "es"
                    else "This planet has no house of its own, so it acts through the planet that rules where it sits. " if via else "")
            tail = {"mixed": ("So the gains come with a cost.", "As\u00ed que lo bueno viene con un costo."),
                    "testing": ("So expect it to test you.", "As\u00ed que espera que te ponga a prueba."),
                    "supportive": ("So it tends to help.", "As\u00ed que tiende a ayudar."),
                    "neutral": ("", "")}[tone][1 if lg == "es" else 0]
            if lg == "es":
                out["note"] = f"{lead}Para tu ascendente es {fnw}: rige tus casas {names} ({words}). {tail}".strip()
            else:
                out["note"] = f"{lead}For your rising sign it is {fnw}: it rules your {names} house{'s' if len(hs) > 1 else ''} ({words}). {tail}".strip()
    except Exception:
        pass
    return out


def build(phase: Optional[dict], chart_data: Optional[dict], language: str = "en", today: Optional[date] = None,
          months: int = 36) -> Dict[str, Any]:
    lg = _lang(language)
    today = today or date.today()
    if not phase or not phase.get("available"):
        return {"version": "seasons-1", "available": False, "seasons": []}
    lagna = ((chart_data or {}).get("lagna") or {}).get("sign") if isinstance((chart_data or {}).get("lagna"), dict) else (chart_data or {}).get("lagna")
    horizon = date(today.year + (today.month - 1 + months) // 12, (today.month - 1 + months) % 12 + 1, 1)
    items = []
    cur = phase.get("shift")
    if cur:
        items.append((cur, True))
    for u in phase.get("upcoming_shifts") or []:
        try:
            if date.fromisoformat(str(u["start"])[:10]) < horizon:
                items.append((u, False))
        except (KeyError, ValueError):
            continue
    seasons = []
    for x, now in items:
        s, e = str(x.get("start") or "")[:10], str(x.get("end") or "")[:10]
        cr = chart_read(x.get("planet") or "", lagna or "", chart_data, x.get("nature") or "", lg)
        name = x.get("plain_name") or ""
        years = (("Ahora" if lg == "es" else "Now") + f" – {e[:4]}") if now else f"{s[:4]} – {e[:4]}"
        seasons.append({"key": f"{(x.get('planet') or '').lower()}-{s[:7]}", "now": now, "planet": x.get("planet"), "start": s, "end": e,
                        "years": years, "title": (f"Temporada de {name.lower()}" if lg == "es" else f"{name} season"),
                        "line": x.get("line") or "", "helps": x.get("helps") or "", "watch": x.get("watch") or "",
                        "tone": cr["tone"], "houses": cr["houses"], "note": cr["note"]})
    ch = phase.get("chapter") or {}
    return {"version": "seasons-1", "available": bool(seasons), "horizon_end": horizon.isoformat(),
            "chapter": {"title": ch.get("plain_name"), "end": ch.get("end"), "line": ch.get("line")}, "seasons": seasons}
