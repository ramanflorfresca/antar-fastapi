"""
Year view organised around the person, not the sources. Everything the engine knows for a life area is merged into ONE card:
  pattern : how you are built in this area (standing statement)
  season  : what is running and when (the strongest stretch, plus the best timed statement)
  move    : one thing to do      watch : one thing to avoid, with what to do instead
The areas the person cares about NOW lead (`focus`, at most 2); the rest fold under `also`.
Relevance = what they have been asking (last 30 days) > their situation (work, partner, children, studying) > how strongly a window is running.
Method, book and rule names never appear; each statement carries only an opaque `ref`.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional

from antar_engine import public_view, rule_registry as rr, when_engine

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
LABELS = {"en": {"pattern": "Your pattern", "season": "Your season", "move": "Your move", "watch": "Watch"},
          "es": {"pattern": "Tu patrón", "season": "Tu temporada", "move": "Tu paso", "watch": "Ojo con"}}
TOPIC_WORDS = {"money": ("money", "fund", "income", "dinero", "financ", "invest", "speculat"),
               "work": ("career", "job", "work", "business", "client", "carrera", "empleo", "negocio", "trabajo"),
               "partnership": ("love", "marri", "relation", "partner", "amor", "matrimonio", "pareja"),
               "family": ("child", "family", "hijo", "famil"), "learning": ("educat", "study", "estudi"),
               "home": ("property", "home", "foreign", "travel", "abroad", "propiedad", "viaje", "extranjero"),
               "health": ("health", "salud"), "inner": ("spirit", "espirit")}
MAX_FOCUS = 2


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
    if area in ("money", "work") and life.get("employed") is False:
        f += 1.0                                  # self-employed: income and work are the live questions
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


def _pattern(ctx, subjects, lang) -> Optional[dict]:
    evs = rr.for_subject(rr.applicable(ctx), subjects[0]) if subjects else []
    for s in subjects[1:]:
        evs += rr.for_subject(rr.applicable(ctx), s)
    best = None
    for e in evs:
        if e.tone in ("good", "info") and e.plain.get(lang) and (best is None or (e.precision == "specific", e.tone == "good") > (best.precision == "specific", best.tone == "good")):
            best = e
    return {"text": best.plain[lang], "ref": public_view.ref_for(best.rule_id)} if best else None


def build(ctx, library: dict, life: Optional[dict] = None, recent_topics: Optional[List[str]] = None,
          lang: str = "en", pinned: Optional[List[str]] = None, kp: Optional[Dict[str, dict]] = None) -> dict:
    lang = "es" if lang == "es" else "en"
    share = _recent_share(recent_topics or [])
    cards = []
    for key, subjects, label in AREAS:
        lean = [i for ln in ("vimshottari", "jaimini") for i in library[ln]["lean_in"] if i.get("subject") in subjects]
        watch = [i for ln in ("vimshottari", "jaimini") for i in library[ln]["watch"] if i.get("subject") in subjects]
        wins = []
        for s in subjects:
            w = when_engine.build(ctx, s, lang, kp=(kp or {}).get(s))
            wins += w["agree"]
        wins.sort(key=lambda w: (-w["signals"], w["start"]))
        pattern = _pattern(ctx, subjects, lang)
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
        activation = (2.0 if wins and wins[0]["strength"] == "strong" else 1.0 if wins else 0.0)
        score = 3.0 * share.get(key, 0.0) + 1.5 * max(_life_fit(key, life), -1.0) + 1.0 * activation * 0.5
        if pinned and key in pinned:
            score += 100.0
        w0 = watch[0] if watch else None
        cards.append({"area": key, "label": label[lang], "_score": score,
                      "pattern": pattern, "season": season, "move": move,
                      "watch": {"text": w0["text"], "do": w0.get("do"), "ref": public_view.ref_for(w0["rule_id"])} if w0 else None})
    cards.sort(key=lambda c: -c["_score"])
    focus = [c for c in cards if c["_score"] > 0.4][:MAX_FOCUS] or cards[:1]
    focus_keys = {c["area"] for c in focus}
    also = [c for c in cards if c["area"] not in focus_keys]
    clean = lambda c: {k: v for k, v in c.items() if k != "_score"}
    return {"labels": LABELS[lang], "focus": [clean(c) for c in focus],
            "also": [{"area": c["area"], "label": c["label"],
                      "hint": (c["season"] or {}).get("text") or (c["pattern"] or {}).get("text")} for c in also],
            "horizon": library.get("horizon")}
