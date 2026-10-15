"""
Year view organised around the person, not the sources. Everything the engine knows for a life area is merged into ONE card:
  pattern : how you are built in this area (standing statement)
  season  : what is running and when (the strongest stretch, plus the best timed statement)
  move    : one thing to do      watch : one thing to avoid, with what to do instead
The areas the person cares about NOW lead (`focus`, at most 2); the rest fold under `also`.
Relevance = what they have been asking (last 30 days) > their situation (work, partner, children, studying) > how strongly a window is running.
Method, book and rule names never appear; each statement carries only an opaque `ref`.
"""
import re
from datetime import date, timedelta
from typing import Dict, List, Optional

from antar_engine import focus_plan, public_view, rule_registry as rr, when_engine

AREAS = [  # key, subjects, label en/es, one-line empty-state hint is not needed: empty areas are skipped
    ("money", ("money", "funding"), {"en": "Money and funding", "es": "Dinero y financiamiento"}),
    ("work", ("career", "job", "business"), {"en": "Work and business", "es": "Trabajo y negocio"}),
    ("partnership", ("love", "marriage"), {"en": "Partnership", "es": "Pareja"}),
    ("family", ("children",), {"en": "Family and children", "es": "Familia e hijos"}),
    ("learning", ("education",), {"en": "Learning", "es": "Aprendizaje"}),
    ("home", ("property", "foreign"), {"en": "Home and travel", "es": "Hogar y viajes"}),
    ("health", ("health",), {"en": "Health and energy", "es": "Salud y energía"}),
    ("inner", ("spirituality",), {"en": "Inner life", "es": "Vida interior"}),
]
BUSINESS = ("business", ("money", "funding", "career", "job", "business"), {"en": "Business and money", "es": "Negocio y dinero"})


def _areas(life: Optional[dict]) -> list:
    """Astrology reads income, funding, business and career from different parts of the chart, but a person who runs their own
    business acts on ONE goal: so for them these merge into one 'business' area (the engines underneath stay separate)."""
    if (life or {}).get("employed") is False:
        return [BUSINESS] + [a for a in AREAS if a[0] not in ("money", "work")]
    return list(AREAS)


GOAL = {"money": {"en": "Grow your income", "es": "Hacer crecer tus ingresos"},
        "business": {"en": "Grow the business: clients, pricing and funding", "es": "Hacer crecer el negocio: clientes, precios y financiamiento"},
        "work": {"en": "Move your career forward", "es": "Avanzar en tu carrera"},
        "partnership": {"en": "Build a lasting partnership", "es": "Construir una pareja duradera"},
        "family": {"en": "Look after your family", "es": "Cuidar a tu familia"},
        "learning": {"en": "Learn and finish what you started", "es": "Aprender y terminar lo que empezaste"},
        "home": {"en": "Settle your home and travel plans", "es": "Ordenar tu hogar y tus viajes"},
        "health": {"en": "Rebuild your energy", "es": "Recuperar tu energía"},
        "inner": {"en": "Deepen your inner practice", "es": "Profundizar tu práctica interior"}}
MANTRA_PLANET = {"money": "Jupiter", "business": "Mercury", "work": "Saturn", "partnership": "Venus", "family": "Jupiter",
                 "learning": "Mercury", "home": "Moon", "health": "Sun", "inner": "Jupiter"}
LABELS_EXTRA = {"en": {"focus_title": "for the next 3 months, focus on", "goal": "Your goal", "bring": "What the next months bring",
                       "do": "Do", "avoid": "Avoid", "instead": "Instead", "remedies": "Remedies", "mantra": "Mantra", "when": "When",
                       "best_window": "Best window", "avoid_window": "Take care", "plan_months": "Month by month", "plan": "Your plan", "near": "Next 3 months", "beyond": "Beyond",
                       "plan_chapters": "Chapters in these months", "plan_turns": "Turning points", "supports": "Touches this topic",
                       "quiet": "Quiet for this", "tone_good": "Supportive", "tone_mixed": "Mixed", "tone_bad": "Careful"},
                "es": {"focus_title": "en los próximos 3 meses, enfócate en", "goal": "Tu meta", "bring": "Lo que traen los próximos meses",
                       "do": "Haz", "avoid": "Evita", "instead": "En su lugar", "remedies": "Remedios", "mantra": "Mantra", "when": "Cuándo",
                       "best_window": "Mejor ventana", "avoid_window": "Cuidado", "plan_months": "Mes a mes", "plan": "Tu plan", "near": "Próximos 3 meses", "beyond": "Más adelante",
                       "plan_chapters": "Capítulos de estos meses", "plan_turns": "Puntos de giro", "supports": "Toca este tema",
                       "quiet": "Tranquilo para esto", "tone_good": "Favorable", "tone_mixed": "Mixto", "tone_bad": "Con cuidado"}}
LABELS = {"en": {"pattern": "Your pattern", "season": "Your season", "move": "Your move", "watch": "Watch",
                 "support": "Do this to support it", "care": "Keep your body steady", "window": "Window", "take_care": "Take care"},
          "es": {"pattern": "Tu patrón", "season": "Tu temporada", "move": "Tu paso", "watch": "Ojo con",
                 "support": "Haz esto para apoyarlo", "care": "Mantén tu cuerpo estable", "window": "Ventana", "take_care": "Cuidado"}}
def _labels(lang: str) -> dict:
    return {**LABELS[lang], **LABELS_EXTRA[lang]}


TOPIC_WORDS = {"business": ("money", "fund", "income", "dinero", "financ", "invest", "speculat", "career", "job", "work", "business", "client", "startup", "carrera", "empleo", "negocio", "trabajo"),
               "money": ("money", "fund", "income", "dinero", "financ", "invest", "speculat"),
               "work": ("career", "job", "work", "business", "client", "carrera", "empleo", "negocio", "trabajo"),
               "partnership": ("love", "marri", "relation", "partner", "amor", "matrimonio", "pareja"),
               "family": ("child", "family", "hijo", "famil"), "learning": ("educat", "study", "estudi"),
               "home": ("property", "home", "foreign", "travel", "abroad", "propiedad", "viaje", "extranjero"),
               "health": ("health", "salud"), "inner": ("spirit", "espirit")}
MAX_FOCUS = 2
_YEAR_LEVEL = re.compile(r"\b(this|a favou?rable|an? \w+) year\b", re.I)          # year-scale statements are a season, not a standing pattern
_NEEDS_PARTNER = re.compile(r"\b(spouse|husband|wife|in-laws?|your partner|tu esposo|tu esposa|tu pareja|tu cónyuge|tu marido)\b", re.I)
_NEEDS_KIDS = re.compile(r"\byour (children|child|kids?|sons?|daughters?)\b|\btus? (hij[oa]s?)\b", re.I)


def _gate_ok(text: Optional[str], life: Optional[dict]) -> bool:
    """Never state a present-tense fact about a spouse or children the person is not known to have (same rule as the narration layer)."""
    if not text:
        return True
    life = life or {}
    if _NEEDS_PARTNER.search(text) and life.get("partnered") is not True:
        return False
    if _NEEDS_KIDS.search(text) and life.get("has_children") is not True:
        return False
    return True


def _recent_share(recent_topics: List[str]) -> Dict[str, float]:
    counts: Dict[str, int] = {}
    for t in recent_topics or []:
        tl = str(t or "").lower()
        for area, words in TOPIC_WORDS.items():
            if any(w in tl for w in words):
                counts[area] = counts.get(area, 0) + 1
    tot = sum(counts.values()) or 1
    return {a: c / tot for a, c in counts.items()}


def _life_fit(area: str, life: Optional[dict]) -> float:
    life = life or {}
    f = 0.0
    if area == "business":
        f += 1.5                                  # runs their own business: income, funding and clients are the live questions
    if area in ("money", "work") and life.get("employed") is False:
        f += 1.0
    if area == "work" and life.get("employed") is True:
        f += 1.0
    if area == "partnership":
        if life.get("partnered") is False:
            f += 1.0
        elif life.get("marital") == "married":
            f -= 1.5                              # already married: marriage-timing is not the live topic
    if area == "family" and life.get("has_children") is True:
        f += 0.5
    if area == "learning" and life.get("career_stage") == "studying":
        f += 1.0
    return f


_MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}
_STRENGTH_WORD = {"en": {"strong": "Strong support", "good": "Good support", "possible": "A lighter signal"},
                  "es": {"strong": "Mucho apoyo", "good": "Buen apoyo", "possible": "Una señal más ligera"}}


def _mon(iso: str, lang: str) -> str:
    return f"{_MON[lang][int(iso[5:7]) - 1]} {iso[:4]}"


def _season_sentence(season: dict, lang: str) -> str:
    """When no timed statement exists for the window, say it in plain words from the window itself."""
    w = _STRENGTH_WORD[lang].get(season.get("strength"), _STRENGTH_WORD[lang]["possible"])
    s = f"{w} through {_mon(season['end'], lang)}." if lang == "en" else f"{w} hasta {_mon(season['end'], lang)}."
    pk = (season.get("peaks") or [])[:1]
    if pk:
        a, b = pk[0]["start"], pk[0]["end"]
        s += (f" Strongest from {_mon(a, lang)} to {_mon(b, lang)}." if lang == "en" else f" Más fuerte de {_mon(a, lang)} a {_mon(b, lang)}.")
    return s


def _pattern(ctx, subjects, lang, life=None) -> Optional[dict]:
    evs = rr.for_subject(rr.applicable(ctx), subjects[0]) if subjects else []
    for s in subjects[1:]:
        evs += rr.for_subject(rr.applicable(ctx), s)
    best = None
    for e in evs:
        if e.tone in ("good", "info") and e.plain.get(lang) and _gate_ok(e.plain.get(lang), life) and not _YEAR_LEVEL.search(e.plain.get(lang)) and (best is None or (e.precision == "specific", e.tone == "good") > (best.precision == "specific", best.tone == "good")):
            best = e
    return {"text": best.plain[lang], "ref": public_view.ref_for(best.rule_id)} if best else None


def _support(ctx, subjects, lang, used: Optional[set] = None) -> Optional[dict]:
    """One practical remedy for the area, from the remedies live now or within six months (what to do to support it)."""
    try:
        cal = rr.remedy_calendar(ctx, lang, subjects[0])
        items = list(cal.get("this_month", [])) + list(cal.get("six_months", []))
        for s in subjects[1:]:
            c2 = rr.remedy_calendar(ctx, lang, s)
            items += list(c2.get("this_month", [])) + list(c2.get("six_months", []))
        for it in items:
            steps = it.get("steps") or []
            if steps and (used is None or it.get("rule_id") not in used):
                if used is not None:
                    used.add(it.get("rule_id"))               # two cards never get the same remedy
                return {"text": steps[0], "duration": it.get("duration"), "purpose": it.get("purpose"),
                        "ref": public_view.ref_for(it.get("rule_id"))}
    except Exception:
        pass
    return None


def _care(library: dict) -> Optional[dict]:
    """One body-care habit (diet / routine) to keep you steady while you push: the best wellness theme that carries a remedy."""
    for t in ((library.get("wellness") or {}).get("themes") or []):
        if t.get("remedy"):
            return {"text": t["remedy"], "why": t.get("text"), "ref": public_view.ref_for(t.get("rule_id"))}
    return None


def _window(season: Optional[dict], watch: Optional[dict]) -> Optional[dict]:
    """The row's one-line status: a dated 'window' while the support is running, 'care' when only a caution applies."""
    if season and season.get("start") and season.get("end"):
        kind = "care" if (season.get("strength") == "possible" and watch) else "window"
        pk = (season.get("peaks") or [None])[0]
        # the row shows the STRONGEST stretch when there is one (that is what differs between areas); `through` is the support's end
        return {"kind": kind, "start": pk["start"] if pk else season["start"], "end": pk["end"] if pk else season["end"],
                "through": season["end"]}
    if watch:
        return {"kind": "care", "start": None, "end": None}
    return None


def _also_hint(card: dict, focus_cards: list) -> Optional[str]:
    """A one-line hint for a folded area: only a dated, specific season line. Never a standing trait (those read as flattery), never the
    health area (the body-care line says it), never a sentence already shown in a focus card."""
    if card.get("area") == "health":
        return None
    season = card.get("season") or {}
    text = season.get("text")
    if not text:
        return None
    shown = {t for f in focus_cards for t in ((f.get("season") or {}).get("text"), (f.get("pattern") or {}).get("text"))}
    return None if text in shown else text


def _detail(ctx, library: dict, life: Optional[dict], lang: str, area: str, cards: list, card: dict, months: int = 6) -> dict:
    """The one page for ONE topic: goal, what the next months bring, what to do, what to avoid (with what to do instead),
    remedies, mantra and the windows. Only statements that belong to this topic; nothing from other areas."""
    subjects = next((a[1] for a in _areas(life) if a[0] == area), ())
    lean = [i for ln in ("vimshottari", "jaimini") for i in library[ln]["lean_in"] if i.get("subject") in subjects and _gate_ok(i.get("text"), life)]
    watch = [i for ln in ("vimshottari", "jaimini") for i in library[ln]["watch"] if i.get("subject") in subjects and _gate_ok(i.get("text"), life)]
    seen = set()

    def _once(items):
        out = []
        for i in items:
            if i["text"] not in seen:
                seen.add(i["text"])
                out.append(i)
        return out
    bring = [{"text": i["text"], "ref": public_view.ref_for(i["rule_id"])} for i in _once(lean)][:3]
    avoid = [{"text": i["text"], "instead": i.get("do"), "ref": public_view.ref_for(i["rule_id"]),
              "start": i.get("start"), "end": i.get("end")} for i in _once(watch)][:3]
    do = [card["move"]] if card.get("move") else []
    remedies = []
    try:
        seen_r = set()
        for sj in subjects:
            cal = rr.remedy_calendar(ctx, lang, sj)
            for it in list(cal.get("this_month", [])) + list(cal.get("six_months", [])):
                steps = it.get("steps") or []
                if steps and it.get("rule_id") not in seen_r and len(remedies) < 3:
                    seen_r.add(it.get("rule_id"))
                    remedies.append({"text": steps[0], "duration": it.get("duration"), "why": it.get("problem"),
                                     "ref": public_view.ref_for(it.get("rule_id"))})
    except Exception:
        pass
    mantra = None
    try:
        from antar_engine.remedies import PLANET_MANTRAS
        m = PLANET_MANTRAS.get(MANTRA_PLANET.get(area))
        if m:
            mantra = {"text": m["simple"], "count": m.get("count"), "day": m.get("recommended_day"), "purpose": m.get("purpose")}
    except Exception:
        pass
    season = card.get("season") or {}
    windows = {"best": ({"start": season.get("start"), "end": season.get("end"), "peaks": season.get("peaks") or []}
                        if season.get("start") else None),
               "avoid": [{"start": a["start"], "end": a["end"]} for a in avoid if a.get("start") and a.get("end")]}
    try:
        plan_months = months if months >= 6 else min(6, months * 2)       # 3-month focus, but the plan shows up to 6 months of what is coming
        ch = focus_plan.chapters(ctx, subjects, plan_months, lang)
        tp = focus_plan.turning_points(ctx, card["label"], subjects, plan_months, lang)
        peaks = (card.get("season") or {}).get("peaks")
        plan = {"timeline": focus_plan.timeline(ctx, ch, tp, peaks, months, lang), "near_months": months,
                "months": focus_plan.months_strip(ctx, subjects, plan_months, lang, peaks), "chapters": ch, "turns": tp}
    except Exception:
        plan = None
    return {"area": area, "label": card["label"], "goal": GOAL.get(area, {}).get(lang), "window": card.get("window"),
            "bring": bring, "do": do, "avoid": avoid, "remedies": remedies, "mantra": mantra, "windows": windows, "plan": plan}


def build(ctx, library: dict, life: Optional[dict] = None, recent_topics: Optional[List[str]] = None,
          lang: str = "en", pinned: Optional[List[str]] = None, kp: Optional[Dict[str, dict]] = None,
          horizon_months: int = 6, area: Optional[str] = None) -> dict:
    lang = "es" if lang == "es" else "en"
    share = _recent_share(recent_topics or [])
    cards, used_remedies = [], set()
    for key, subjects, label in _areas(life):
        lean = [i for ln in ("vimshottari", "jaimini") for i in library[ln]["lean_in"] if i.get("subject") in subjects]
        watch = [i for ln in ("vimshottari", "jaimini") for i in library[ln]["watch"] if i.get("subject") in subjects]
        lean = [i for i in lean if _gate_ok(i.get("text"), life)]
        watch = [i for i in watch if _gate_ok(i.get("text"), life)]
        wins = []
        for s in subjects:
            w = when_engine.build(ctx, s, lang, kp=(kp or {}).get(s), horizon_months=horizon_months)
            wins += w["agree"]
        wins.sort(key=lambda w: (-w["signals"], w["start"]))
        pattern = _pattern(ctx, subjects, lang, life)
        move = None
        for s in subjects:
            ww = rr._windows(ctx, s, lang)
            if ww:
                move = ww[0].get("action")
                break
        if not (lean or watch or wins or pattern):
            continue
        season = None
        if wins or lean:
            season = {"text": (lean[0]["text"] if lean else None), "ref": public_view.ref_for(lean[0]["rule_id"]) if lean else None,
                      "start": wins[0]["start"] if wins else lean[0].get("start"), "end": wins[0]["end"] if wins else lean[0].get("end"),
                      "strength": wins[0]["strength"] if wins else "possible", "peaks": (wins[0].get("peaks") if wins else []) or []}
        if season and not season.get("text") and season.get("start") and season.get("end"):
            season["text"] = _season_sentence(season, lang)
        activation = (2.0 if wins and wins[0]["strength"] == "strong" else 1.0 if wins else 0.0)
        score = 3.0 * share.get(key, 0.0) + 1.5 * max(_life_fit(key, life), -1.0) + 1.0 * activation * 0.5
        if pinned and key in pinned:
            score += 100.0
        w0 = watch[0] if watch else None
        watch_card = {"text": w0["text"], "do": w0.get("do"), "ref": public_view.ref_for(w0["rule_id"])} if w0 else None
        cards.append({"area": key, "label": label[lang], "_score": score, "window": _window(season, watch_card),
                      "pattern": pattern, "season": season, "move": move, "support": _support(ctx, subjects, lang, used_remedies),
                      "watch": {"text": w0["text"], "do": w0.get("do"), "ref": public_view.ref_for(w0["rule_id"])} if w0 else None})
    cards.sort(key=lambda c: -c["_score"])
    focus = [c for c in cards if c["_score"] > 0.4][:MAX_FOCUS] or cards[:1]
    focus_keys = {c["area"] for c in focus}
    also = [c for c in cards if c["area"] not in focus_keys]
    clean = lambda c: {k: v for k, v in c.items() if k != "_score"}
    if area in ("money", "work") and (life or {}).get("employed") is False:
        area = "business"                          # the circles say Money / Career; a founder's one card is Business and money
    want = next((c for c in cards if c["area"] == area), None) if area else None
    detail = _detail(ctx, library, life, lang, area, cards, want, horizon_months) if want else None
    return {"labels": _labels(lang), "horizon_months": horizon_months, "detail": detail, "care": _care(library), "focus": [clean(c) for c in focus],
            "card": clean(want) if want else None,
            "also": [{"area": c["area"], "label": c["label"], "window": c.get("window"), "hint": _also_hint(c, [f for f in focus])} for c in also],
            "horizon": library.get("horizon")}
