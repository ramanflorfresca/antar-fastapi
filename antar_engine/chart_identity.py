"""
antar_engine/chart_identity.py

[chart-identity 2026-07-25] The "this is your chart" summary for the profile /
account surface: ascendant, Sun, Moon, the soul planet, the running dasha
chapter, and the strongest yogas — with a short plain-language reading.

This is the ONE surface where sign and planet names belong. Everywhere else the
product speaks in plain life-language (see the Today jargon gate); here the user
is looking AT their own chart and has asked to see it, so the vocabulary is the
point. The `reading` field still gives a plain paragraph for anyone who wants
the meaning without the terms.

Pure functions — no DB, no network — so they unit-test off a chart_data dict and
a vimsottari rows list. The route wires them to Supabase.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

# Sign each planet rules — for the plain "your rising sign is ruled by…" line.
_SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# One plain word per planet, for the reading line. No mechanics, no Sanskrit.
_PLANET_PLAIN = {
    "Sun": "identity and purpose", "Moon": "emotion and instinct",
    "Mars": "drive and courage", "Mercury": "mind and communication",
    "Jupiter": "growth and wisdom", "Venus": "love and value",
    "Saturn": "discipline and time", "Rahu": "ambition and the unfamiliar",
    "Ketu": "detachment and the past",
}

_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th",
            7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}

# [chart-identity i18n 2026-09-14] Localize the chart-vocabulary surface for
# es/pt. Signs and planet names get proper localized forms; nakshatras stay
# (Sanskrit proper nouns); house labels become "casa N"; the plain phrases and
# the reading paragraph are built in-language. Yoga `effect` prose is translated
# at the endpoint via @translate_response. en falls through to the base maps.
_SIGN_L10N = {
    "es": {"Aries": "Aries", "Taurus": "Tauro", "Gemini": "Géminis", "Cancer": "Cáncer",
           "Leo": "Leo", "Virgo": "Virgo", "Libra": "Libra", "Scorpio": "Escorpio",
           "Sagittarius": "Sagitario", "Capricorn": "Capricornio", "Aquarius": "Acuario",
           "Pisces": "Piscis"},
    "pt": {"Aries": "Áries", "Taurus": "Touro", "Gemini": "Gêmeos", "Cancer": "Câncer",
           "Leo": "Leão", "Virgo": "Virgem", "Libra": "Libra", "Scorpio": "Escorpião",
           "Sagittarius": "Sagitário", "Capricorn": "Capricórnio", "Aquarius": "Aquário",
           "Pisces": "Peixes"},
}
_PLANET_L10N = {
    "es": {"Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio",
           "Jupiter": "Júpiter", "Venus": "Venus", "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"},
    "pt": {"Sun": "Sol", "Moon": "Lua", "Mars": "Marte", "Mercury": "Mercúrio",
           "Jupiter": "Júpiter", "Venus": "Vênus", "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"},
}
_PLANET_PLAIN_L10N = {
    "es": {"Sun": "identidad y propósito", "Moon": "emoción e instinto",
           "Mars": "impulso y coraje", "Mercury": "mente y comunicación",
           "Jupiter": "crecimiento y sabiduría", "Venus": "amor y valor",
           "Saturn": "disciplina y tiempo", "Rahu": "ambición y lo desconocido",
           "Ketu": "desapego y el pasado"},
    "pt": {"Sun": "identidade e propósito", "Moon": "emoção e instinto",
           "Mars": "impulso e coragem", "Mercury": "mente e comunicação",
           "Jupiter": "crescimento e sabedoria", "Venus": "amor e valor",
           "Saturn": "disciplina e tempo", "Rahu": "ambição e o desconhecido",
           "Ketu": "desapego e o passado"},
}
_ORDINAL_L10N = {
    "es": {h: f"casa {h}" for h in range(1, 13)},
    "pt": {h: f"casa {h}" for h in range(1, 13)},
}


def _lang3(language: Optional[str]) -> str:
    l = (language or "en").split("-")[0].lower()
    return l if l in ("es", "pt") else "en"


def _sign_l(lang: str, s: Optional[str]) -> Optional[str]:
    return _SIGN_L10N.get(lang, {}).get(s, s) if s else s


def _planet_l(lang: str, p: Optional[str]) -> Optional[str]:
    return _PLANET_L10N.get(lang, {}).get(p, p) if p else p


def _plain_l(lang: str, p: Optional[str]) -> str:
    if lang in _PLANET_PLAIN_L10N:
        return _PLANET_PLAIN_L10N[lang].get(p, "")
    return _PLANET_PLAIN.get(p, "")


def _ord_l(lang: str, h: Any) -> Optional[str]:
    if h is None:
        return None
    return _ORDINAL_L10N.get(lang, _ORDINAL).get(h)


def _planet(planets: Any, name: str) -> Dict[str, Any]:
    """A planet's placement dict from either storage format, or {}."""
    if isinstance(planets, dict):
        p = planets.get(name)
        return p if isinstance(p, dict) else {}
    if isinstance(planets, list):
        for p in planets:
            if isinstance(p, dict) and (p.get("name") or p.get("planet")) == name:
                return p
    return {}


def _placement(planets: Any, name: str) -> Optional[Dict[str, Any]]:
    p = _planet(planets, name)
    if not p or not p.get("sign"):
        return None
    return {
        "sign": p.get("sign"),
        "house": p.get("house"),
        "nakshatra": p.get("nakshatra"),
    }


def _parse_day(s: Any) -> Optional[date]:
    try:
        return datetime.fromisoformat(str(s)[:10]).date()
    except (ValueError, TypeError):
        return None


def _running_chapter(vim_rows: Any, today: date) -> Dict[str, Any]:
    """Current maha / antar / pratyantar lords + when the maha hands over,
    and which lord it hands over to. Any gap is simply omitted."""
    rows = vim_rows if isinstance(vim_rows, list) else []
    out: Dict[str, Any] = {}
    maha_end: Optional[date] = None

    def _lord(r):
        return r.get("lord_or_sign") or r.get("planet_or_sign")

    for r in rows:
        lvl = (r.get("level") or "").lower()
        sd = _parse_day(r.get("start_date") or r.get("start"))
        ed = _parse_day(r.get("end_date") or r.get("end"))
        if not (sd and ed and sd <= today <= ed):
            continue
        if lvl == "mahadasha":
            out["maha"] = _lord(r)
            out["maha_ends"] = ed.isoformat()
            maha_end = ed
        elif lvl in ("antardasha", "bhukti"):
            out["antar"] = _lord(r)
        elif lvl == "pratyantardasha":
            out["pratyantar"] = _lord(r)

    # The mahadasha that starts exactly when this one ends is the next chapter.
    if maha_end:
        for r in rows:
            if (r.get("level") or "").lower() != "mahadasha":
                continue
            if _parse_day(r.get("start_date") or r.get("start")) == maha_end:
                out["next_maha"] = _lord(r)
                break
    return out


def _reading(asc_sign, asc_lord, sun, moon, atma, chapter, lang: str = "en") -> str:
    """A short plain-language paragraph — the meaning without the mechanics,
    built directly in the target language (en/es/pt)."""
    bits: List[str] = []
    S = lambda s: _sign_l(lang, s)
    P = lambda p: _planet_l(lang, p)
    PL = lambda p: _plain_l(lang, p)
    if lang == "es":
        if asc_sign:
            line = f"Te presentas ante el mundo como {S(asc_sign)}"
            if PL(asc_lord):
                line += f", así que {PL(asc_lord)} moldea cómo apareces"
            bits.append(line + ".")
        if sun and moon:
            bits.append(f"Tu ser esencial se mueve por {S(sun['sign'])} mientras que tu "
                        f"mundo interior es {S(moon['sign'])} — cómo actúas y cómo sientes "
                        f"vienen de fuentes distintas.")
        if atma and PL(atma):
            bits.append(f"El hilo al que tu vida vuelve una y otra vez es {PL(atma)}.")
        if chapter.get("maha"):
            m = chapter["maha"]
            line = f"Ahora mismo estás en un capítulo de {P(m)}"
            if PL(m):
                line += f" — una larga temporada sobre {PL(m)}"
            if chapter.get("maha_ends"):
                line += f", y se cierra el {chapter['maha_ends']}"
                if chapter.get("next_maha"):
                    nxt = chapter["next_maha"]
                    line += f", dando paso a una temporada de {P(nxt)} sobre {PL(nxt) or P(nxt)}"
            bits.append(line + ".")
    elif lang == "pt":
        if asc_sign:
            line = f"Você se apresenta ao mundo como {S(asc_sign)}"
            if PL(asc_lord):
                line += f", então {PL(asc_lord)} molda como você aparece"
            bits.append(line + ".")
        if sun and moon:
            bits.append(f"Seu ser essencial funciona em {S(sun['sign'])} enquanto seu "
                        f"mundo interior é {S(moon['sign'])} — como você age e como você "
                        f"sente vêm de fontes diferentes.")
        if atma and PL(atma):
            bits.append(f"O fio ao qual sua vida sempre retorna é {PL(atma)}.")
        if chapter.get("maha"):
            m = chapter["maha"]
            line = f"Agora você está num capítulo de {P(m)}"
            if PL(m):
                line += f" — uma longa temporada sobre {PL(m)}"
            if chapter.get("maha_ends"):
                line += f", e ele se encerra em {chapter['maha_ends']}"
                if chapter.get("next_maha"):
                    nxt = chapter["next_maha"]
                    line += f", passando para uma temporada de {P(nxt)} sobre {PL(nxt) or P(nxt)}"
            bits.append(line + ".")
    else:
        if asc_sign:
            line = f"You meet the world as {asc_sign}"
            if PL(asc_lord):
                line += f", so {PL(asc_lord)} shapes how you show up"
            bits.append(line + ".")
        if sun and moon:
            bits.append(f"Your core self runs on {sun['sign']} while your inner world is "
                        f"{moon['sign']} — how you act and how you feel are drawn from "
                        f"different wells.")
        if atma and PL(atma):
            bits.append(f"The thread your life keeps returning to is {PL(atma)}.")
        if chapter.get("maha"):
            m = chapter["maha"]
            line = f"Right now you are in a {m}"
            if PL(m):
                line += f" chapter — a long season about {PL(m)}"
            if chapter.get("maha_ends"):
                line += f", and it closes on {chapter['maha_ends']}"
                if chapter.get("next_maha"):
                    nxt = chapter["next_maha"]
                    line += f", handing over to a {nxt} season of {PL(nxt) or nxt}"
            bits.append(line + ".")
    return " ".join(bits)


def build_chart_identity(chart_data: Any, vim_rows: Any = None,
                         name: str = "", today: Optional[date] = None,
                         language: str = "en") -> Dict[str, Any]:
    """{name, ascendant, sun, moon, atmakaraka, current_period, yogas, reading}.

    Returns {"available": False} only when the chart has no ascendant AND no
    Sun — i.e. it is not a real chart. Otherwise every present field is filled
    and missing ones are null, so a partial chart still renders.
    """
    cd = chart_data if isinstance(chart_data, dict) else {}
    today = today or date.today()
    lang = _lang3(language)

    lagna = cd.get("lagna") if isinstance(cd.get("lagna"), dict) else {}
    asc_sign = lagna.get("sign")
    asc_deg = lagna.get("degree")
    planets = cd.get("planets") or cd.get("planet_positions")

    sun = _placement(planets, "Sun")
    moon = _placement(planets, "Moon")

    if not asc_sign and not sun:
        return {"available": False}

    atma = cd.get("atmakaraka")
    if isinstance(atma, dict):
        atma = atma.get("planet") or atma.get("name")

    chapter = _running_chapter(vim_rows, today)
    asc_lord = _SIGN_LORD.get(asc_sign or "")

    # Top yogas, prose-safe: name + effect only, strongest first.
    yogas = []
    for y in (cd.get("yogas") or []):
        if isinstance(y, dict) and y.get("name"):
            yogas.append({"name": y.get("name"), "effect": y.get("effect", ""),
                          "strength": y.get("strength", "")})
    _rank = {"strong": 0, "moderate": 1, "weak": 2}
    yogas.sort(key=lambda y: _rank.get((y.get("strength") or "").lower(), 3))

    # Localize the running-chapter lords (Rahu/Ketu unchanged by the map).
    chapter_loc = dict(chapter) if chapter else {}
    for _k in ("maha", "antar", "pratyantar", "next_maha"):
        if chapter_loc.get(_k):
            chapter_loc[_k] = _planet_l(lang, chapter_loc[_k])

    def _place_loc(pl):
        return {
            "sign": _sign_l(lang, pl.get("sign")),
            "house": pl.get("house"),
            "nakshatra": pl.get("nakshatra"),   # Sanskrit proper noun — kept
            "house_label": _ord_l(lang, pl.get("house")),
        }

    return {
        "available": True,
        "name": name or "",
        "language": lang,
        "ascendant": {
            "sign": _sign_l(lang, asc_sign),
            "degree": round(asc_deg, 1) if isinstance(asc_deg, (int, float)) else None,
            "ruled_by": _planet_l(lang, asc_lord),
        } if asc_sign else None,
        "sun": _place_loc(sun) if sun else None,
        "moon": _place_loc(moon) if moon else None,
        "atmakaraka": {"planet": _planet_l(lang, atma), "means": _plain_l(lang, atma)} if atma else None,
        "current_period": chapter_loc or None,
        "yogas": yogas[:3],
        "reading": _reading(asc_sign, asc_lord, sun, moon, atma, chapter, lang),
    }
