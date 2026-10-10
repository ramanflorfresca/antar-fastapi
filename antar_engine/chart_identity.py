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
    and which lord it hands over to, PLUS the nearer sub-chapter (antardasha)
    handover. Any gap is simply omitted."""
    rows = vim_rows if isinstance(vim_rows, list) else []
    out: Dict[str, Any] = {}
    maha_end: Optional[date] = None
    antar_end: Optional[date] = None

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
            out["antar_ends"] = ed.isoformat()
            antar_end = ed
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
    # [chapter-card 2026-10-01] the nearer, actionable shift: the antardasha
    # (sub-chapter) handover. The maha handover can be 15+ years out, so leading
    # the card with it reads as "nothing changes for a generation". Capture the
    # next antardasha so the card can surface the near shift instead.
    if antar_end:
        for r in rows:
            if (r.get("level") or "").lower() not in ("antardasha", "bhukti"):
                continue
            if _parse_day(r.get("start_date") or r.get("start")) == antar_end:
                out["next_antar"] = _lord(r)
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
            if sun["sign"] == moon["sign"]:
                bits.append(f"Tu ser esencial y tu mundo interior comparten {S(sun['sign'])} "
                            f"— cómo actúas y cómo sientes tiran en la misma dirección.")
            else:
                bits.append(f"Tu ser esencial se mueve por {S(sun['sign'])} mientras que tu "
                            f"mundo interior es {S(moon['sign'])} — cómo actúas y cómo sientes "
                            f"vienen de fuentes distintas.")
        if atma and PL(atma):
            bits.append(f"El hilo al que tu vida vuelve una y otra vez es {PL(atma)}.")
        if chapter.get("maha"):
            m = chapter["maha"]
            line = (f"Ahora mismo estás en un largo capítulo sobre {PL(m)}"
                    if PL(m) else "Ahora mismo estás en un capítulo distinto de tu vida")
            if chapter.get("maha_ends"):
                line += f", y se cierra el {chapter['maha_ends']}"
                if chapter.get("next_maha") and PL(chapter["next_maha"]):
                    line += f", dando paso a una fase de {PL(chapter['next_maha'])}"
            bits.append(line + ".")
    elif lang == "pt":
        if asc_sign:
            line = f"Você se apresenta ao mundo como {S(asc_sign)}"
            if PL(asc_lord):
                line += f", então {PL(asc_lord)} molda como você aparece"
            bits.append(line + ".")
        if sun and moon:
            if sun["sign"] == moon["sign"]:
                bits.append(f"Seu ser essencial e seu mundo interior compartilham {S(sun['sign'])} "
                            f"— como você age e como você sente puxam na mesma direção.")
            else:
                bits.append(f"Seu ser essencial funciona em {S(sun['sign'])} enquanto seu "
                            f"mundo interior é {S(moon['sign'])} — como você age e como você "
                            f"sente vêm de fontes diferentes.")
        if atma and PL(atma):
            bits.append(f"O fio ao qual sua vida sempre retorna é {PL(atma)}.")
        if chapter.get("maha"):
            m = chapter["maha"]
            line = (f"Agora você está num longo capítulo sobre {PL(m)}"
                    if PL(m) else "Agora você está num capítulo distinto da sua vida")
            if chapter.get("maha_ends"):
                line += f", e ele se encerra em {chapter['maha_ends']}"
                if chapter.get("next_maha") and PL(chapter["next_maha"]):
                    line += f", passando para uma fase de {PL(chapter['next_maha'])}"
            bits.append(line + ".")
    else:
        if asc_sign:
            line = f"You meet the world as {asc_sign}"
            if PL(asc_lord):
                line += f", so {PL(asc_lord)} shapes how you show up"
            bits.append(line + ".")
        if sun and moon:
            if sun["sign"] == moon["sign"]:
                bits.append(f"Your core self and your inner world share {sun['sign']} "
                            f"— how you act and how you feel pull the same way.")
            else:
                bits.append(f"Your core self runs on {sun['sign']} while your inner world is "
                            f"{moon['sign']} — how you act and how you feel are drawn from "
                            f"different wells.")
        if atma and PL(atma):
            bits.append(f"The thread your life keeps returning to is {PL(atma)}.")
        if chapter.get("maha"):
            # [jargon-fix] never name the planet in user-facing prose — use the
            # plain energy phrase only (the card + this reading are user surfaces).
            m = chapter["maha"]
            line = (f"Right now you are in a long chapter about {PL(m)}"
                    if PL(m) else "Right now you are in a distinct life chapter")
            if chapter.get("maha_ends"):
                line += f", and it closes on {chapter['maha_ends']}"
                if chapter.get("next_maha") and PL(chapter["next_maha"]):
                    line += f", handing over to a phase of {PL(chapter['next_maha'])}"
            bits.append(line + ".")
    return " ".join(bits)


# ── chart_summary: the "your chart in 60 seconds" card ───────────────────────
# Plain life-language only (no planet, house or yoga names) so the You tab can
# render it verbatim. Deterministic, built in-language, no LLM. See
# Antar.world/SPEC_backend_fields_chart_summary_relation_why_2026-10-10.md.

_DEBILITATED = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
                "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries"}
_HARD_HOUSES = (6, 8, 12)
_GROWTH_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

_MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
}

_SUMMARY_COPY = {
    "en": {
        "acts_from": "You act from {x}.",
        "shows_up": "{x} shapes how you show up.",
        "edge": "Under pressure, watch for {x} — pause before you commit.",
        "phase": "You are in a long chapter about {m}.",
        "phase_next": "You are in a long chapter about {m}; around {d} it hands over to {n}.",
    },
    "es": {
        "acts_from": "Actúas desde {x}.",
        "shows_up": "{x} moldea cómo apareces.",
        "edge": "Bajo presión, cuidado con {x} — haz una pausa antes de comprometerte.",
        "phase": "Estás en un largo capítulo sobre {m}.",
        "phase_next": "Estás en un largo capítulo sobre {m}; hacia {d} da paso a {n}.",
    },
    "pt": {
        "acts_from": "Você age a partir de {x}.",
        "shows_up": "{x} molda como você aparece.",
        "edge": "Sob pressão, cuidado com {x} — faça uma pausa antes de se comprometer.",
        "phase": "Você está num longo capítulo sobre {m}.",
        "phase_next": "Você está num longo capítulo sobre {m}; por volta de {d} ele passa para {n}.",
    },
}


# The decision habit each planet's weakness shows up as. Written per planet (not
# a noun swap) so the line says something a person recognizes. Copy is owner-
# approved wording only once signed off; see the PR description.
_EDGE_HABIT = {
    "en": {"Sun": "the need for credit or control", "Moon": "mood and gut reaction",
           "Mars": "impatience and the urge to win", "Mercury": "overthinking and talking yourself round",
           "Jupiter": "overconfidence or taking on too much", "Venus": "comfort and keeping the peace",
           "Saturn": "over-caution and delay", "Rahu": "chasing whatever is new and shiny",
           "Ketu": "pulling back or losing interest"},
    "es": {"Sun": "la necesidad de reconocimiento o control", "Moon": "el estado de ánimo y la reacción visceral",
           "Mars": "la impaciencia y las ganas de ganar", "Mercury": "darle demasiadas vueltas a todo",
           "Jupiter": "el exceso de confianza o cargar con demasiado", "Venus": "la comodidad y mantener la paz",
           "Saturn": "el exceso de cautela y la demora", "Rahu": "perseguir lo nuevo y brillante",
           "Ketu": "retirarte o perder el interés"},
    "pt": {"Sun": "a necessidade de crédito ou controle", "Moon": "o humor e a reação instintiva",
           "Mars": "a impaciência e a vontade de vencer", "Mercury": "pensar demais e se convencer do contrário",
           "Jupiter": "o excesso de confiança ou assumir demais", "Venus": "o conforto e manter a paz",
           "Saturn": "o excesso de cautela e o atraso", "Rahu": "perseguir o que é novo e brilhante",
           "Ketu": "se afastar ou perder o interesse"},
}


def _month_year(lang: str, iso: Any) -> str:
    d = _parse_day(iso)
    if not d:
        return ""
    return f"{_MONTHS.get(lang, _MONTHS['en'])[d.month - 1]} {d.year}"


def _growth_planet(planets: Any, maha: str) -> Optional[str]:
    """The planet most likely to pull this chart's decisions off course: a
    debilitated one first, else one sitting in a hard house; ties go to the
    running chapter's planet, then a fixed order (deterministic)."""
    cands = []
    for p in _GROWTH_ORDER:
        pl = _placement(planets, p)
        if not pl:
            continue
        debil = _DEBILITATED.get(p) == pl.get("sign")
        hard = pl.get("house") in _HARD_HOUSES
        if debil or hard:
            cands.append((0 if debil else 1, 0 if p == maha else 1, _GROWTH_ORDER.index(p), p))
    return min(cands)[3] if cands else None


def build_chart_summary(planets: Any, asc_lord: Optional[str], atma: Optional[str],
                        yogas: List[Dict[str, Any]], chapter: Dict[str, Any],
                        lang: str = "en") -> Optional[Dict[str, Any]]:
    """{strengths[3], growth_edge, phase, phase_ends}, or None when fewer than
    three distinct strengths can be named (never padded with generic lines).
    `yogas` is the already de-jargoned, ranked list from build_chart_identity."""
    c = _SUMMARY_COPY[lang]
    PL = lambda p: _plain_l(lang, p)
    strengths: List[str] = []
    used_planets = set()

    def _add(text: str) -> None:
        if text and text not in strengths:
            strengths.append(text)

    # Independence: a yoga title, the soul-planet line and the rising-sign-lord
    # line each rest on different evidence; skip a planet line whose planet was
    # already used so the same energy is never counted twice.
    for y in yogas:
        if y.get("kind") == "strength" and y.get("strength", "").lower() in ("strong", "moderate"):
            _add(y.get("name", ""))
        if len(strengths) >= 2:
            break
    for planet, key in ((atma, "acts_from"), (asc_lord, "shows_up")):
        if planet and planet not in used_planets and PL(planet) and len(strengths) < 3:
            used_planets.add(planet)
            x = PL(planet)
            _add(c[key].format(x=x[:1].upper() + x[1:] if key == "shows_up" else x))
    if len(strengths) < 3:
        return None

    maha = chapter.get("maha") or ""
    # The chart's own "area to mind" (already plain + localized) beats a planet
    # template: it is specific to this person. Fall back to the planet habit.
    growth_edge = next((y.get("name") for y in yogas if y.get("kind") == "mind" and y.get("name")), None)
    if not growth_edge:
        edge_planet = _growth_planet(planets, maha)
        habit = _EDGE_HABIT.get(lang, _EDGE_HABIT["en"]).get(edge_planet or "")
        growth_edge = c["edge"].format(x=habit) if habit else None

    # The nearer handover (sub-chapter vs chapter) — never lead with a date 15y out.
    ends = nxt = None
    ends_sub = chapter.get("antar_ends"); ends_maha = chapter.get("maha_ends")
    if ends_sub and chapter.get("next_antar") and (not ends_maha or ends_sub < ends_maha):
        ends, nxt = ends_sub, chapter.get("next_antar")
    elif ends_maha and chapter.get("next_maha"):
        ends, nxt = ends_maha, chapter.get("next_maha")
    phase = None
    if PL(maha):
        when = _month_year(lang, ends)
        phase = (c["phase_next"].format(m=PL(maha), d=when, n=PL(nxt))
                 if when and nxt and PL(nxt) else c["phase"].format(m=PL(maha)))

    return {"strengths": strengths[:3], "growth_edge": growth_edge,
            "phase": phase, "phase_ends": ends if phase else None}



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

    # Top yogas, strongest first. De-jargoned at render time: the user-facing
    # `name` is a plain decision-relevant label (never a Sanskrit yoga name),
    # `effect` a plain line. `kind` = strength|mind lets the FE group them.
    # See antar_engine/yogas.plain_yoga. The detection `name` (a Sanskrit
    # internal key downstream engines pattern-match on) is deliberately NOT
    # emitted — the payload itself is a user-reachable surface.
    from antar_engine.yogas import plain_yoga as _plain_yoga
    yogas = []
    for y in (cd.get("yogas") or []):
        if isinstance(y, dict) and y.get("name"):
            _pl = _plain_yoga(y.get("name"), lang)
            yogas.append({
                "name":     _pl["title"],
                "effect":   _pl["effect_en"] or y.get("effect", ""),
                "strength": y.get("strength", ""),
                "kind":     _pl["kind"],
            })
    _rank = {"strong": 0, "moderate": 1, "weak": 2}
    yogas.sort(key=lambda y: _rank.get((y.get("strength") or "").lower(), 3))

    # [jargon-fix 2026-09-30] current_period is a USER-REACHABLE payload surface
    # (the FE's "chapter you're in" card renders these fields verbatim), so it
    # must carry PLAIN language, never planet names — same rule the yogas block
    # above follows. Previously these were run through _planet_l, which only
    # LOCALIZES the planet name (Rahu stayed "Rahu"), leaking "You're in your
    # Rahu chapter / into Jupiter". Emit the plain energy phrase instead
    # ("ambition and the unfamiliar", "growth and wisdom"); _reading() still gets
    # the raw `chapter` dict, so the prose line is unaffected.
    chapter_loc = dict(chapter) if chapter else {}
    for _k in ("maha", "antar", "pratyantar", "next_maha", "next_antar"):
        if chapter_loc.get(_k):
            chapter_loc[_k] = _plain_l(lang, chapter_loc[_k]) or chapter_loc[_k]
    # [chapter-card 2026-10-01] Surface the NEXT MEANINGFUL SHIFT for the card —
    # the nearer of the sub-chapter (antardasha) handover vs the maha handover, so
    # the card never leads with a date 15+ years out. Prefer the sub shift when it
    # lands before the maha one. Plain + localized; the FE renders these two.
    _ne_sub = chapter.get("antar_ends"); _nxt_sub = chapter_loc.get("next_antar")
    _ne_maha = chapter.get("maha_ends"); _nxt_maha = chapter_loc.get("next_maha")
    if _ne_sub and _nxt_sub and (not _ne_maha or _ne_sub < _ne_maha):
        chapter_loc["next_shift_on"] = _ne_sub
        chapter_loc["next_shift_to"] = _nxt_sub
    elif _ne_maha and _nxt_maha:
        chapter_loc["next_shift_on"] = _ne_maha
        chapter_loc["next_shift_to"] = _nxt_maha

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
        "chart_summary": build_chart_summary(planets, asc_lord, atma, yogas, chapter, lang),
        "reading": _reading(asc_sign, asc_lord, sun, moon, atma, chapter, lang),
    }
