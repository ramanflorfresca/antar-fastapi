"""[pair-view 2026-10-11] The data behind the redesigned connection screen: a fit strip, who owns what, and the next two years side by side.

The old reading was paragraphs. The same facts, shaped to be seen in seconds:

  tiles    flows / needs care / open — from the six fit layers and, for partners, the lanes nobody owns yet
  lanes    one row per work area with its owner (you | other | shared | open) — from partner_roles
  seasons  a one- or two-word SEASON for each person across the next 6 months, 6-12 months and year 2, from each person's own running Vimshottari
           sub-periods, plus whether the two seasons line up. A season is a character of the period (push forward / build structure / grow and teach …),
           NOT a prediction of events. Outward seasons (push, lead, act, trade, grow, relate) and inward ones (build, tend, refine) are "out of sync" when
           they differ — the one sentence that matters: decide early who sets the pace.

Deterministic, no LLM, no chart words in any user-facing string. en + es."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from antar_engine import partner_roles as P

PERIODS = ("next_6_months", "6_to_12_months", "year_2")
PERIOD_LABELS = {"en": ["Next 6 months", "6 to 12 months", "Year 2"], "es": ["Próximos 6 meses", "De 6 a 12 meses", "Año 2"]}
_OFFSETS = (90, 270, 540)           # the day inside each period whose running sub-period names the season

# lord -> (key, group, label en, label es)
SEASON: Dict[str, tuple] = {
    "Rahu":    ("push", "out", "Reach and experiment", "Explorar y probar"),
    "Sun":     ("lead", "out", "Take the lead", "Tomar la delantera"),
    "Mars":    ("act", "out", "Move fast", "Actuar con rapidez"),
    "Mercury": ("trade", "out", "Deals and talks", "Tratos y conversaciones"),
    "Jupiter": ("grow", "out", "Grow and teach", "Crecer y enseñar"),
    "Venus":   ("relate", "out", "Build relationships", "Construir relaciones"),
    "Saturn":  ("build", "in", "Build structure", "Construir estructura"),
    "Moon":    ("tend", "in", "Steady and tend", "Estabilidad y cuidado"),
    "Ketu":    ("refine", "in", "Simplify and refine", "Simplificar y afinar"),
}
_TX = {
    "en": {
        "flows": "Working together", "care": "Tend these", "open": "Who decides", "friction_low": "Little friction between you", "friction_high": "Friction to manage",
        "open_n": "{n} areas have no owner yet", "open_1": "1 area has no owner yet", "open_0": "Every area has an owner",
        "care_none": "Nothing flagged",
        "sync": "Your seasons line up: you can move at the same pace.",
        "out_a": "You are moving outward and {b} inward ({when}). Agree who sets the pace then.",
        "out_b": "{b} is moving outward and you inward ({when}). Agree who sets the pace then.",
        "mixed": "You are out of step in {n} of the 3 periods marked Out. Agree who sets the pace in those.",
        "you": "You", "no_data": "Timing for {who} is not on file, so there is no season to show.",
    },
    "es": {
        "flows": "Trabajar juntos", "care": "Para cuidar", "open": "Quién decide", "friction_low": "Poca fricción entre ustedes", "friction_high": "Fricción por manejar",
        "open_n": "{n} áreas sin dueño todavía", "open_1": "1 área sin dueño todavía", "open_0": "Cada área tiene dueño",
        "care_none": "Nada señalado",
        "sync": "Sus temporadas coinciden: pueden avanzar al mismo ritmo.",
        "out_a": "Tú vas hacia afuera y {b} hacia adentro ({when}). Acuerden quién marca el ritmo entonces.",
        "out_b": "{b} va hacia afuera y tú hacia adentro ({when}). Acuerden quién marca el ritmo entonces.",
        "mixed": "No van al mismo ritmo en {n} de los 3 periodos marcados Out. Acuerden quién marca el ritmo en esos.",
        "you": "Tú", "no_data": "Los tiempos de {who} no están disponibles, así que no hay temporada que mostrar.",
    },
}
_CARE = {
    "en": {"soul": "shared priorities", "chemistry": "day to day", "public": "how you show up", "lifepath": "timing", "communication": "communication and trust",
           "friction": "handling disagreement"},
    "es": {"soul": "prioridades compartidas", "chemistry": "el día a día", "public": "cómo se presentan", "lifepath": "los tiempos", "communication": "comunicación y confianza",
           "friction": "manejar desacuerdos"},
}


def _d(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def lord_on(dashas: dict, when: date) -> str:
    """The Antardasha lord running on `when` (the Mahadasha lord when no sub-period row covers it). '' when unknown."""
    md = ad = ""
    for row in ((dashas or {}).get("vimsottari") or []):
        s, e = _d(row.get("start_date") or row.get("start")), _d(row.get("end_date") or row.get("end"))
        if not (s and e and s <= when <= e):
            continue
        lvl = str(row.get("level") or row.get("type") or "").lower()
        lord = row.get("lord_or_sign") or row.get("planet_or_sign") or ""
        if lvl.startswith("antar") and not ad:
            ad = lord
        elif lvl.startswith("maha") and not md:
            md = lord
    return ad or md


def seasons_for(dashas: dict, today: Optional[date] = None, lang: str = "en") -> Optional[List[dict]]:
    """Three seasons (next 6 months / 6-12 months / year 2) or None when this person has no usable timing."""
    today = today or datetime.utcnow().date()
    out = []
    for off in _OFFSETS:
        lord = lord_on(dashas, today + timedelta(days=off))
        s = SEASON.get(lord)
        if not s:
            return None
        out.append({"key": s[0], "group": s[1], "label": s[3] if lang == "es" else s[2]})
    return out


def build(session_out: dict, dashas_a: dict, dashas_b: dict, language: str = "en", today: Optional[date] = None) -> Optional[dict]:
    """The pair-view object for one saved connection. Never raises."""
    try:
        lang = language if language in _TX else "en"
        tx = _TX[lang]
        today = today or datetime.utcnow().date()
        roles = session_out.get("roles") if isinstance(session_out.get("roles"), dict) else None
        layers = [l for l in (session_out.get("layers") or []) if isinstance(l, dict)]
        by = {l.get("layer_key"): l for l in layers}
        fr = by.get("friction")
        flows = {"state": "flows" if (fr and (fr.get("score") or 0) >= 60) else "care",
                 "label": tx["flows"], "text": tx["friction_low"] if (fr and (fr.get("score") or 0) >= 60) else tx["friction_high"]}
        low = [k for k, l in sorted(((k, l) for k, l in by.items() if k != "friction"), key=lambda kv: kv[1].get("score") or 0) if (l.get("score") or 0) < 55][:3]
        care = {"label": tx["care"], "areas": low, "text": ", ".join(_CARE[lang][k] for k in low[:2]) if low else tx["care_none"]}
        lanes, open_n = [], 0
        if roles and roles.get("kind") != "hierarchy":
            nm = P._NAME[lang]
            you, other = roles["you"].get("leads", []), roles["other"].get("leads", [])
            shared, openl = roles.get("shared", []), list(roles.get("contested", [])) + list(roles.get("gaps", []))
            for lane in P.LANES:
                owner = "you" if lane in you else "other" if lane in other else "shared" if lane in shared else "open" if lane in openl else "shared"
                lanes.append({"lane": lane, "label": nm[lane], "owner": owner})
            open_n = sum(1 for l in lanes if l["owner"] == "open")
        open_t = {"label": tx["open"], "n": open_n, "text": tx["open_0"] if open_n == 0 else tx["open_1"] if open_n == 1 else tx["open_n"].format(n=open_n)}
        a, b = seasons_for(dashas_a, today, lang), seasons_for(dashas_b, today, lang)
        seasons = None
        name_b = (session_out.get("name_b") or "").strip().split(" ")[0] if session_out.get("name_b") else ""
        if a and b:
            sync = [x["group"] == y["group"] for x, y in zip(a, b)]
            if all(sync):
                summary = tx["sync"]
            elif any(sync):
                summary = tx["mixed"].format(n=sum(1 for ok in sync if not ok))
            else:
                first = next(i for i, ok in enumerate(sync) if not ok)
                summary = tx["out_a" if a[first]["group"] == "out" else "out_b"].format(b=name_b or ("la otra persona" if lang == "es" else "the other person"), when=PERIOD_LABELS[lang][first].lower())
            seasons = {"periods": list(PERIODS), "period_labels": PERIOD_LABELS[lang], "you": a, "other": b, "in_sync": sync, "summary": summary}
        else:
            who = tx["you"] if not a else (name_b or "the other person")
            seasons = {"periods": list(PERIODS), "period_labels": PERIOD_LABELS[lang], "you": a, "other": b, "in_sync": None, "summary": tx["no_data"].format(who=who)}
        return {"version": "pair-view-1", "language": lang, "tiles": {"flows": flows, "care": care, "open": open_t}, "lanes": lanes, "seasons": seasons}
    except Exception as e:
        print(f"[pair-view] failed: {type(e).__name__}: {e}")
        return None
