"""
The week ahead as three separately labelled lines (no blending):
  vimshottari : running major/sub/pratyantara/sookshma lords + Moon-based Gochara (gochara.py)
  jaimini     : timed library rules (K.N. Rao and other book rules) whose natal condition holds and whose dasha/transit
                activation holds on a day this week
  lal_kitab   : this year's Roop Chand annual rules and the age-cycle year lord
Deterministic; a line with nothing to say is empty. Accuracy gating comes later, from user check-ins.
"""
from datetime import date, timedelta
from typing import Optional

from antar_engine import gochara
from antar_engine import rule_registry as rr


def _book_lines(ctx, start: date, days: int, language: str) -> list:
    from antar_engine import book_rules, combo_rules
    by_id = {r["id"]: r for r in book_rules.load_rules()}
    seen, out = {}, []
    for i in range(days):
        d = start + timedelta(days=i)
        for ev in rr.timed_book_evidence(ctx, d):
            if combo_rules.is_impersonal(by_id.get(ev.rule_id[3:] if ev.rule_id.startswith("BK.") else ev.rule_id) or {}):
                continue                                  # same for everyone: not shown in the personal week
            if ev.rule_id in seen:
                seen[ev.rule_id]["days"].append(d.isoformat())
                continue
            row = {"rule_id": ev.rule_id, "book": ev.book, "tone": ev.tone, "subjects": ev.subjects,
                   "text": ev.plain.get(language) or ev.plain.get("en"), "days": [d.isoformat()]}
            seen[ev.rule_id] = row
            out.append(row)
    return _one_per_topic(out)


def _specificity(row: dict, rules_by_id: dict) -> int:
    r = rules_by_id.get(row["rule_id"][3:] if row["rule_id"].startswith("BK.") else row["rule_id"]) or {}
    return len(r.get("requires", [])) + len(r.get("activation", []))


def _one_per_topic(rows: list) -> list:
    """Show the most specific rule per (subject, tone); the rest ride along under `more` so nothing is hidden."""
    from antar_engine import book_rules
    by_id = {r["id"]: r for r in book_rules.load_rules()}
    best = {}
    for row in rows:
        for subj in (row["subjects"] or ["other"]):
            k = (subj, row["tone"])
            if k not in best or _specificity(row, by_id) > _specificity(best[k], by_id):
                best[k] = row
    keep = {id(v) for v in best.values()}
    shown = [r for r in rows if id(r) in keep]
    hidden = [r for r in rows if id(r) not in keep]
    for r in shown:
        r["more"] = [{"rule_id": h["rule_id"], "book": h["book"], "text": h["text"]}
                     for h in hidden if h["tone"] == r["tone"] and set(h["subjects"]) & set(r["subjects"])]
    return shown


def _lk_line(ctx, language: str) -> dict:
    from antar_engine import lk_year_lord
    out = {"year_lord": None, "rules": []}
    try:
        if ctx.birth_date:
            out["year_lord"] = lk_year_lord.year_lord_by_age(ctx.birth_date, ctx.today)
    except Exception:
        pass
    try:
        from antar_engine import rc_rules
        st = ctx.rc_state()
        for r in rc_rules.applying(st, "annual"):
            eff = (r.get("effect_es") if language == "es" else None) or r.get("effect")
            out["rules"].append({"rule_id": r.get("id"), "tone": r.get("tone"), "text": eff,
                                 "subjects": rc_rules.subjects_of(r)})
    except Exception:
        pass
    return out


# practical step per topic: written by us (not from the books), shown only beside a caution
STEPS = {
    "money": ("Hold off on big spending or new commitments; check the numbers twice before you pay or sign.",
              "Pospón gastos grandes o compromisos nuevos; revisa las cifras dos veces antes de pagar o firmar."),
    "funding": ("Don't sign terms in a hurry; get every condition in writing and give yourself a day before you agree.",
                "No firmes condiciones con prisa; pide todo por escrito y date un día antes de aceptar."),
    "career": ("Keep to the work in front of you; avoid starting a fight or making a big career move in this stretch.",
              "Concéntrate en el trabajo que tienes; evita pelear o dar un gran paso profesional en esta etapa."),
    "job": ("Don't resign or make a hard decision on a bad day; polish your résumé and keep options open instead.",
            "No renuncies ni decidas en un mal día; mejora tu currículum y mantén opciones abiertas."),
    "business": ("Delay launches and new partnerships; use this stretch to tighten what already works.",
                 "Retrasa lanzamientos y nuevas alianzas; usa esta etapa para afinar lo que ya funciona."),
    "love": ("Keep talks calm and short; save the big conversation for a better day.",
             "Mantén las charlas tranquilas y breves; deja la conversación importante para un mejor día."),
    "marriage": ("Don't force big decisions about the relationship now; listen more and decide later.",
                 "No fuerces decisiones importantes sobre la relación ahora; escucha más y decide después."),
    "children": ("Keep routines steady and be patient; avoid big changes in this stretch.",
                 "Mantén las rutinas estables y ten paciencia; evita grandes cambios en esta etapa."),
    "education": ("Break study into short daily blocks and avoid cramming; postpone big exams or applications if you can.",
                  "Divide el estudio en bloques cortos diarios y evita memorizar a última hora; pospón exámenes o solicitudes grandes si puedes."),
    "property": ("Don't close or sign property deals in this stretch; get documents checked first.",
                 "No cierres ni firmes tratos de propiedad en esta etapa; haz revisar los documentos primero."),
    "foreign": ("Double-check dates, documents and bookings before any travel or move abroad.",
                "Verifica fechas, documentos y reservas antes de viajar o mudarte al extranjero."),
    "spirituality": ("Keep a short, steady daily practice rather than doing a lot at once.",
                     "Mantén una práctica diaria corta y constante en lugar de hacer mucho de golpe."),
    "speculation": ("Skip speculative bets in this stretch; if you act, risk only what you can lose.",
                    "Evita las apuestas especulativas en esta etapa; si actúas, arriesga solo lo que puedas perder."),
    "health": ("Rest, keep a regular routine, and book the check-up you have been putting off.",
               "Descansa, mantén una rutina regular y agenda el chequeo que has ido posponiendo."),
}
PLANET_STEP_SUBJECT = {"Jupiter": "money", "Saturn": "career", "Sun": "career", "Mars": "love", "Mercury": "money",
                       "Venus": "love", "Moon": None}
MOON_STEP = ("Keep the day light: fewer commitments, no big decisions.", "Mantén el día ligero: menos compromisos, sin decisiones grandes.")
MAX_WATCH = 3
SUBJECT_AREA = {"money": "money", "funding": "money", "speculation": "money", "career": "work", "job": "work", "business": "work",
                "love": "partnership", "marriage": "partnership", "children": "family", "education": "learning",
                "property": "home", "foreign": "home", "health": "health", "spirituality": "inner"}


def _area(subjects) -> Optional[str]:
    for s_ in subjects or []:
        if s_ in SUBJECT_AREA:
            return SUBJECT_AREA[s_]
    return None


def _lang(pair, language):
    return pair[1] if language == "es" else pair[0]


def _action(subjects, remedy, language):
    if remedy:
        return remedy.get(language) or remedy.get("en")
    for sj in subjects or []:
        if sj in STEPS:
            return _lang(STEPS[sj], language)
    return None


def _blocks(out: dict, language: str) -> dict:
    """lean_in / watch across the lines. Every caution carries something to do; a caution with nothing to do is hidden.
    Order: timed book rules first, then Lal Kitab year, then this week's planetary positions."""
    from antar_engine import book_rules, rc_rules
    lean, watch = [], []
    by_id = {r["id"]: r for r in book_rules.load_rules()}
    for row in out["jaimini"]:
        rid = row["rule_id"][3:] if row["rule_id"].startswith("BK.") else row["rule_id"]
        item = {"line": "jaimini" if row["book"] == "K.N. Rao" else "book", "source": row["book"], "text": row["text"],
                "rule_id": row["rule_id"], "days": row["days"], "more": row.get("more", []), "area": _area(row.get("subjects"))}
        if row["tone"] == "good":
            lean.append(item)
        elif row["tone"] == "bad":
            rem = by_id.get(rid, {})
            remedy = {l: v for l, v in (("en", rem.get("remedy")), ("es", rem.get("remedy_es"))) if v} or None
            act = _action(row["subjects"], remedy, language)
            if act:
                watch.append({**item, "do": act})
    # The Lal Kitab annual rules describe the YEAR, not this week: they live in the year view (focus / season), never in the week.
    g = (out["vimshottari"].get("gochara") or {})
    for l in g.get("background", []) + g.get("this_month", []):
        item = {"line": "vimshottari", "source": "Raman, transits", "text": l["text"], "rule_id": "GOCHARA." + l["planet_key"],
                "area": _area([PLANET_STEP_SUBJECT.get(l["planet_key"])])}
        if l["state"] == "good":
            lean.append(item)
        else:
            act = _action([PLANET_STEP_SUBJECT.get(l["planet_key"])], None, language)
            if act:
                watch.append({**item, "do": act})
    if g.get("slow_days"):
        watch.append({"line": "vimshottari", "source": "Raman, transits", "rule_id": "GOCHARA.Moon",
                      "text": "Slower days this week: " + ", ".join(g["slow_days"]) if language != "es"
                      else "Días más lentos esta semana: " + ", ".join(g["slow_days"]),
                      "days": g["slow_days"], "do": _lang(MOON_STEP, language)})
    seen_do, uniq, extra = set(), [], []
    for w in watch:
        d = w.get("do")
        if d in seen_do:
            extra.append(w)               # same practical step as a caution already shown: held back, not repeated
        else:
            seen_do.add(d)
            uniq.append(w)
    return {"lean_in": lean, "watch": uniq[:MAX_WATCH], "watch_more": uniq[MAX_WATCH:] + extra}


def week(ctx, language: str = "en", days: int = 7, start: Optional[date] = None) -> dict:
    start = start or ctx.today
    moon = ctx.planets.get("Moon")
    vim = {"periods_now": ctx.periods_at(start), "gochara": None}
    if moon is not None:
        vim["gochara"] = gochara.outlook(moon.sign, start, days, language)
    out = {"start": start.isoformat(), "days": days,
           "vimshottari": vim,
           "jaimini": _book_lines(ctx, start, days, language),
           "lal_kitab": _lk_line(ctx, language)}
    out.update(_blocks(out, language))
    try:
        from antar_engine import reading_library
        out["wellness"] = reading_library.wellness(ctx, start, max(days, 30), language)
    except Exception:
        out["wellness"] = None
    return out
