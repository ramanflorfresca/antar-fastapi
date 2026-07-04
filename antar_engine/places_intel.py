"""
antar_engine/places_intel.py
─────────────────────────────────────────────────────────────────────────────
PLACES — 4-layer chart intelligence support.  Phase 3.

Builds the global reasoning blocks for /places/concern:
  * chart_intelligence  — strongest / weakest planet for the concern, yogas, LK
  * dasha_context       — current vs upcoming major period, forward-looking
  * life_stage_context  — age → chapter and what it weights

All output is plain-language: planet names allowed as actors (Path B), but no
house numbers and no Sanskrit (yoga names are translated; a strip pass is the
backstop in the endpoint).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from antar_engine.places_concern import CONCERN_MAP

# ─────────────────────────────────────────────────────────────────────────────
# Age + life stage
# ─────────────────────────────────────────────────────────────────────────────

LIFE_STAGE_BY_AGE = [
    (0, 25, "foundation"),
    (25, 35, "ascending"),
    (35, 50, "consolidation"),
    (50, 65, "culmination"),
    (65, 99, "wisdom"),
]


def compute_age(birth_date: Optional[str]) -> Optional[int]:
    """Age in whole years from an ISO birth_date string, or None."""
    if not birth_date:
        return None
    try:
        s = str(birth_date)[:10]
        y, m, d = int(s[:4]), int(s[5:7]), int(s[8:10])
        today = datetime.now(timezone.utc).date()
        age = today.year - y - ((today.month, today.day) < (m, d))
        return age if 0 <= age <= 120 else None
    except Exception:
        try:
            return datetime.now(timezone.utc).year - int(str(birth_date)[:4])
        except Exception:
            return None


def life_stage_for_age(age: Optional[int]) -> Optional[str]:
    if age is None:
        return None
    for lo, hi, name in LIFE_STAGE_BY_AGE:
        if lo <= age < hi:
            return name
    return "wisdom" if age >= 65 else "foundation"


# city velocity ↔ chapter pace
_FAST_CHAPTERS = {"ascending", "foundation"}
_SLOW_CHAPTERS = {"consolidation", "culmination", "wisdom"}


def velocity_match(chapter: Optional[str], velocity: Optional[str]) -> str:
    """Return 'match' | 'mismatch' | 'quiet' | 'neutral' for AGE-layer phrasing."""
    if not chapter or not velocity:
        return "neutral"
    v = velocity.upper()
    if chapter in _FAST_CHAPTERS:
        return "match" if v in ("HIGH", "MEDIUM") else "neutral"
    if chapter in _SLOW_CHAPTERS:
        if v == "HIGH":
            return "mismatch"
        if v == "LOW":
            return "quiet"
        return "match"
    return "neutral"


_STAGE_PARA = {
    "en": {
        "foundation": "you are still laying foundations — the place you choose now shapes the skills and instincts you'll carry for decades. The recommendation favours range and exposure.",
        "ascending": "you are in the ascending phase — momentum compounds fastest now, so the recommendation weights places that match your drive and stretch you.",
        "consolidation": "you are in the consolidation phase — the place you choose now compounds for the next 15 years. The recommendation weights long-build alignment over fast wins.",
        "culmination": "you are in the culmination phase — this is about harvest and authority, so the recommendation favours places where your built strength is recognised.",
        "wisdom": "you are in the wisdom phase — the recommendation favours places that give back ease, meaning, and roots rather than more climb.",
    },
    "es": {
        "foundation": "aún estás poniendo cimientos — el lugar que elijas ahora moldea las habilidades e instintos que llevarás por décadas. La recomendación favorece amplitud y exposición.",
        "ascending": "estás en la fase ascendente — el impulso se acumula más rápido ahora, así que la recomendación prioriza lugares que igualen tu empuje y te exijan.",
        "consolidation": "estás en la fase de consolidación — el lugar que elijas ahora se capitaliza durante los próximos 15 años. La recomendación prioriza la alineación de largo plazo sobre las victorias rápidas.",
        "culmination": "estás en la fase de culminación — se trata de cosecha y autoridad, así que la recomendación favorece lugares donde tu fuerza construida sea reconocida.",
        "wisdom": "estás en la fase de sabiduría — la recomendación favorece lugares que devuelven calma, sentido y raíces más que más ascenso.",
    },
}


def build_life_stage_context(age: Optional[int], concern: str, language: str) -> Optional[dict]:
    if age is None:
        return None
    lang = "es" if str(language).lower().startswith("es") else "en"
    chapter = life_stage_for_age(age)
    body = _STAGE_PARA[lang].get(chapter, "")
    if lang == "es":
        para = f"A los {age}, {body}"
    else:
        para = f"At {age}, {body}"
    return {"age": age, "chapter": chapter, "paragraph": para}


# ─────────────────────────────────────────────────────────────────────────────
# Dasha context
# ─────────────────────────────────────────────────────────────────────────────

_ES_MONTHS = {
    "January": "enero", "February": "febrero", "March": "marzo", "April": "abril",
    "May": "mayo", "June": "junio", "July": "julio", "August": "agosto",
    "September": "septiembre", "October": "octubre", "November": "noviembre", "December": "diciembre",
}


def _fmt_month_year(iso: str, lang: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        s = dt.strftime("%B %Y")
        if lang == "es":
            for en, es in _ES_MONTHS.items():
                if s.startswith(en):
                    return s.replace(en, es)
        return s
    except Exception:
        return str(iso)[:7]


def _level(p: dict) -> str:
    return str(p.get("level") or p.get("type") or "").lower()


def _parse_dt(iso) -> Optional[datetime]:
    """Parse an ISO date/datetime to an aware UTC datetime (assume UTC if naive)."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _lord(p: dict) -> str:
    return p.get("lord_or_sign", "") or p.get("planet_or_sign", "")


def _start(p: dict):
    return p.get("start", "") or p.get("start_date", "")


def _end(p: dict):
    return p.get("end", "") or p.get("end_date", "")


def get_dasha_context(dashas: dict, language: str) -> Optional[dict]:
    """
    Build the forward-looking dasha block from get_dashas_for_chart() output.
    Within 12 months of an MD transition the paragraph references the NEXT MD.
    Robust to naive or tz-aware date strings.
    """
    lang = "es" if str(language).lower().startswith("es") else "en"
    vim = dashas.get("vimsottari") or dashas.get("Vimsottari") or []
    if not vim:
        return None

    now = datetime.now(timezone.utc)
    mds = [p for p in vim if _level(p) in ("mahadasha", "maha", "md", "1", "")]
    ads = [p for p in vim if _level(p) in ("antardasha", "antar", "ad", "bhukti", "2")]
    if not mds:
        mds = vim

    # Current MD: start <= now <= end; fall back to latest started; then first.
    def _current(periods):
        dated = [(p, _parse_dt(_start(p)), _parse_dt(_end(p))) for p in periods]
        for p, s, e in dated:
            if s and e and s <= now <= e:
                return p
        started = [(p, s) for p, s, e in dated if s and s <= now]
        if started:
            return max(started, key=lambda t: t[1])[0]
        return periods[0] if periods else {}

    cur_md = _current(mds)
    cur_start = _parse_dt(_start(cur_md))

    # Next MD: earliest MD that starts at/after current MD's start (and later).
    future = []
    for p in mds:
        s = _parse_dt(_start(p))
        if s and cur_start and s > cur_start:
            future.append((p, s))
    next_md = min(future, key=lambda t: t[1])[0] if future else {}

    md_lord = _lord(cur_md)
    md_end_iso = _end(cur_md)
    next_md_lord = _lord(next_md)

    # Current antardasha within the running MD.
    cur_ad = {}
    if ads:
        scoped = [p for p in ads if (p.get("parent_lord", "") in ("", md_lord))]
        cur_ad = _current(scoped or ads)
    ad_lord = _lord(cur_ad)
    ad_end_iso = _end(cur_ad)

    # Within 12 months of MD transition?
    within_12mo = False
    end_dt = _parse_dt(md_end_iso)
    if end_dt:
        within_12mo = 0 <= (end_dt - now).days <= 365

    md_ends = _fmt_month_year(md_end_iso, lang)
    ad_ends = _fmt_month_year(ad_end_iso, lang)

    if within_12mo and next_md_lord:
        if lang == "es":
            para = (f"Estás en los últimos meses de tu periodo de {md_lord} — esa fase se está cerrando. "
                    f"Desde {md_ends}, {next_md_lord} abre un nuevo capítulo largo. "
                    f"Las ciudades de abajo están puntuadas para el arco LARGO en el que entras, no el corto que termina.")
        else:
            para = (f"You are in the final months of your {md_lord} period — that phase is closing. "
                    f"From {md_ends}, {next_md_lord} begins a long new chapter. "
                    f"The cities below are scored for the LONG arc you are entering, not the short one closing.")
    else:
        if lang == "es":
            para = (f"Estás en tu periodo de {md_lord}"
                    + (f", con {ad_lord} activo ahora mismo" if ad_lord else "")
                    + f". Las ciudades de abajo están puntuadas para este capítulo"
                    + (f", que continúa hasta {md_ends}" if md_ends else "") + ".")
        else:
            para = (f"You are in your {md_lord} period"
                    + (f", with {ad_lord} active right now" if ad_lord else "")
                    + f". The cities below are scored for this chapter"
                    + (f", which runs to {md_ends}" if md_ends else "") + ".")

    return {
        "md_lord": md_lord,
        "md_ends": md_ends,
        "ad_lord": ad_lord,
        "ad_ends": ad_ends,
        "next_md_lord": next_md_lord,
        "within_12mo_transition": within_12mo,
        "paragraph": para,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Chart intelligence (strongest / weakest / yogas / LK)
# ─────────────────────────────────────────────────────────────────────────────

_PLANET_GOVERNS = {
    "en": {
        "Sun": "your authority, visibility, and sense of self",
        "Moon": "your emotional baseline and how you are received",
        "Mars": "your daily push, drive, and appetite for risk",
        "Mercury": "your communication, deal-making, and quick thinking",
        "Jupiter": "your growth, wisdom, and how fortune expands",
        "Venus": "your relationships, taste, and how value flows",
        "Saturn": "your effort, structure, and how you build over time",
        "Rahu": "your hunger for the new, foreign, and unconventional",
        "Ketu": "your detachment, focus, and inner withdrawal",
    },
    "es": {
        "Sun": "tu autoridad, visibilidad y sentido de identidad",
        "Moon": "tu base emocional y cómo te reciben",
        "Mars": "tu empuje diario, tu impulso y tu apetito de riesgo",
        "Mercury": "tu comunicación, tus tratos y tu agilidad mental",
        "Jupiter": "tu crecimiento, tu sabiduría y cómo se expande la fortuna",
        "Venus": "tus relaciones, tu gusto y cómo fluye el valor",
        "Saturn": "tu esfuerzo, tu estructura y cómo construyes con el tiempo",
        "Rahu": "tu hambre de lo nuevo, lo extranjero y lo no convencional",
        "Ketu": "tu desapego, tu enfoque y tu retiro interior",
    },
}

_COND_CLAUSE = {
    "en": {
        "exalted": "It is exalted in your chart — this is one of your real strengths.",
        "own_sign": "It stands on solid home ground — dependable footing for you.",
        "friend": "It sits in a friendly sign — generally supportive.",
        "neutral": "It is neutral in your chart — neither a strong help nor a drag.",
        "enemy": "It sits in an unfriendly sign — it works, but against some resistance.",
        "debilitated": "It is weakened in your chart — fast-moving environments here take more from you than they give.",
        "combust": "It is overshadowed in your chart — its signal is easily drowned out.",
        "sleeping": "It is dormant in your chart — its strength needs deliberate activation.",
    },
    "es": {
        "exalted": "Está exaltado en tu carta — una de tus verdaderas fortalezas.",
        "own_sign": "Está en su propio signo — terreno sólido y confiable para ti.",
        "friend": "Está en un signo amigo — en general te apoya.",
        "neutral": "Es neutral en tu carta — ni gran ayuda ni lastre.",
        "enemy": "Está en un signo poco amistoso — funciona, pero con cierta resistencia.",
        "debilitated": "Está debilitado en tu carta — los entornos veloces aquí te quitan más de lo que te dan.",
        "combust": "Está eclipsado en tu carta — su señal se ahoga con facilidad.",
        "sleeping": "Está dormido en tu carta — su fuerza necesita activación deliberada.",
    },
}

# Plain-language translations for the common yoga names (no Sanskrit, no numbers).
_YOGA_PLAIN = {
    "en": {
        "raj": "a natural authority combination — leadership is wired into your chart",
        "dhana": "a wealth combination — resources are part of your blueprint",
        "gajakesari": "a wisdom-and-standing combination that lifts your judgement",
        "budhaditya": "a sharp-mind combination that favours communication and craft",
        "vipreet": "a rise-through-difficulty pattern — setbacks tend to turn in your favour",
        "neecha": "a weakness that turns into an unusual strength",
        "pancha": "a strong foundational combination supporting steady success",
    },
    "es": {
        "raj": "una combinación de autoridad natural — el liderazgo está inscrito en tu carta",
        "dhana": "una combinación de riqueza — los recursos son parte de tu plano",
        "gajakesari": "una combinación de sabiduría y prestigio que eleva tu criterio",
        "budhaditya": "una combinación de mente aguda que favorece la comunicación y el oficio",
        "vipreet": "un patrón de ascenso a través de la dificultad — los reveses tienden a girar a tu favor",
        "neecha": "una debilidad que se convierte en una fuerza inusual",
        "pancha": "una combinación fundacional fuerte que sostiene el éxito constante",
    },
}


def _translate_yoga(name: str, lang: str) -> Optional[str]:
    low = (name or "").lower()
    for key, txt in _YOGA_PLAIN[lang].items():
        if key in low:
            return txt
    return None


def build_chart_intelligence(chart: dict, concern: str, conditions: dict, language: str) -> dict:
    lang = "es" if str(language).lower().startswith("es") else "en"
    karakas = CONCERN_MAP.get(concern, {}).get("karakas", [])
    present = [(k, conditions.get(k, {})) for k in karakas if k in conditions]

    def _note(planet, cond):
        gov = _PLANET_GOVERNS[lang].get(planet, "")
        clause = _COND_CLAUSE[lang].get(cond, "")
        if lang == "es":
            return f"{planet} rige {gov}. {clause}".strip()
        return f"{planet} rules {gov}. {clause}".strip()

    strongest = weakest = None
    if present:
        s = max(present, key=lambda kc: kc[1].get("weight", 0.9))
        w = min(present, key=lambda kc: kc[1].get("weight", 0.9))
        strongest = {"planet": s[0], "condition": s[1].get("condition", "neutral"),
                     "note": _note(s[0], s[1].get("condition", "neutral"))}
        if w[0] != s[0]:
            weakest = {"planet": w[0], "condition": w[1].get("condition", "neutral"),
                       "note": _note(w[0], w[1].get("condition", "neutral"))}

    # Yogas relevant to the concern, translated to plain language.
    relevant_yogas = []
    try:
        from antar_engine.astrological_rules import detect_yogas
        for y in detect_yogas(chart, concern)[:6]:
            t = _translate_yoga(y.get("name", ""), lang)
            if t and t not in relevant_yogas:
                relevant_yogas.append(t)
            if len(relevant_yogas) >= 3:
                break
    except Exception:
        pass

    # LK-relevant: karakas that are dormant for this concern (plain phrasing).
    relevant_lk = []
    for k in karakas:
        if conditions.get(k, {}).get("condition") == "sleeping":
            if lang == "es":
                relevant_lk.append(f"{k} está dormido — su aporte a este tema necesita activación deliberada.")
            else:
                relevant_lk.append(f"{k} is dormant — its contribution to this thread needs deliberate activation.")
        if len(relevant_lk) >= 3:
            break

    return {
        "strongest_for_concern": strongest,
        "weakest_for_concern": weakest,
        "relevant_yogas": relevant_yogas,
        "relevant_lk": relevant_lk,
    }
