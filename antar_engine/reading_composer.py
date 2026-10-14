"""
Reading composer: turns the deterministic event forecast into a plain-language 24-month
decision calendar. No LLM, no technical terms in the output (no planet, sign, dasha or
house names). Two independent timing systems (Jaimini Chara, Parashari Vimshottari) are
merged per life area: a window both systems point to is "strong"; one system with its own
top tier is "good"; otherwise "possible". The narrower Jaimini window is reported as the
"peak" inside the broader season. Money/career windows built on a birth-time-sensitive
chart layer are capped at "good" and flagged so the app can ask the user to confirm the time.
Locales: en, es.
"""
from datetime import date
from typing import Dict, List, Optional

AREAS = ("money", "career", "relationship", "learning")
_PAR_EVENT = {"money": "money", "career": "career", "marriage": "relationship", "study": "learning"}
_JAI_EVENT = {"money": "money", "career": "career", "marriage": "relationship", "education": "learning"}
_RANK = {"possible": 0, "good": 1, "strong": 2}

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
}
T = {
    "en": {
        "area": {"money": "Money", "career": "Career", "relationship": "Relationships", "learning": "Learning"},
        "headline": {"money": "Income opens up", "career": "A step up is likely",
                     "relationship": "A turning point in a close relationship or partnership",
                     "learning": "A good stretch to learn something new"},
        "action": {"money": "Pitch, raise, price up and close deals in this window. Keep costs flexible.",
                   "career": "Put yourself forward: ask for the role, the scope or the title.",
                   "relationship": "Have the important conversation. Don't force a decision outside this window.",
                   "learning": "Start the course, certification or new skill now."},
        "why_both": "Two independent signals agree on this period.",
        "why_three": "Three independent signals agree on this period.",
        "why_one": "One strong signal points to this period.",
        "why_weak": "One signal points to this period.",
        "why_peak": "The most active stretch is {peak}.",
        "strength": {"strong": "Strong", "good": "Good", "possible": "Possible"},
        "caution_head": "A pressure period",
        "caution_action": "Keep commitments light, protect your health and cash, and avoid big risks.",
        "birth_time": "Some of the money and career timing depends on your exact birth time. Confirm it to sharpen these dates.",
        "birth_time_edge": "Your birth time sits right on an edge: a difference of a minute would change part of the money and career timing, so that part is held back.",
        "none": "No strong opening stands out in the next 24 months. Use it to build steadily.",
        "summary": "Your best window: {area}, {dates}.",
        "themes": {1: "your drive and identity", 2: "savings and family", 3: "effort and courage",
                   4: "home and peace of mind", 5: "children and creativity", 6: "health and daily work",
                   7: "partnerships", 8: "hidden and sudden matters", 9: "luck and guidance",
                   10: "career and standing", 11: "income and gains", 12: "expenses and foreign matters"},
        "year_good": "Working in your favour this year: {items}.",
        "year_watch": "Handle with care this year: {items}.",
        "year_quiet": "Quiet this year (little movement either way): {items}.",
        "year_tone": {"favourable": "A supportive year overall.", "mixed": "A mixed year: real gains and real tests.",
                      "testing": "A testing year. Lean on the remedies and keep plans simple.",
                      "quiet": "The traditional text has nothing specific for your placements this year."},
        "remedy_for": "For {theme}",
        "special": "This is a turning-point year in your cycle.",
        "focus_title": "Your focus for the next six months",
        "focus_head": {"money": "Focus on income", "career": "Focus on your next step up",
                       "relationship": "Focus on your closest relationship or partnership",
                       "learning": "Focus on learning one thing properly",
                       "protect": "Protect your energy and cash", "build": "Build steadily"},
        "focus_step": {"money": "This week, list the three deals or clients closest to closing and put a date on each.",
                       "career": "This week, write down the role or scope you want and ask one person who decides on it.",
                       "relationship": "This week, set up the conversation you have been putting off.",
                       "learning": "This week, pick the course or skill and book the first session.",
                       "protect": "This week, list your fixed costs and cut one commitment that isn't paying you back.",
                       "build": "This week, pick the one project that matters most and finish its next step."},
        "focus_active": "Active now", "focus_starts": "Starts {when}",
        "focus_also": "Also in view",
        "focus_avoid": "Go lightly in {label}. {action}",
    },
    "es": {
        "area": {"money": "Dinero", "career": "Carrera", "relationship": "Relaciones", "learning": "Aprendizaje"},
        "headline": {"money": "Se abren ingresos", "career": "Es probable un ascenso",
                     "relationship": "Un punto de inflexión en una relación o sociedad cercana",
                     "learning": "Buen momento para aprender algo nuevo"},
        "action": {"money": "Presenta, levanta capital, sube precios y cierra acuerdos en esta ventana. Mantén los costos flexibles.",
                   "career": "Da un paso al frente: pide el puesto, el alcance o el título.",
                   "relationship": "Ten la conversación importante. No fuerces una decisión fuera de esta ventana.",
                   "learning": "Empieza ahora el curso, la certificación o la nueva habilidad."},
        "why_both": "Dos señales independientes coinciden en este periodo.",
        "why_three": "Tres señales independientes coinciden en este periodo.",
        "why_one": "Una señal fuerte apunta a este periodo.",
        "why_weak": "Una señal apunta a este periodo.",
        "why_peak": "El tramo más activo es {peak}.",
        "strength": {"strong": "Fuerte", "good": "Bueno", "possible": "Posible"},
        "caution_head": "Un periodo de presión",
        "caution_action": "Mantén los compromisos ligeros, cuida tu salud y tu caja, y evita riesgos grandes.",
        "birth_time": "Parte del tiempo de dinero y carrera depende de tu hora exacta de nacimiento. Confírmala para afinar estas fechas.",
        "birth_time_edge": "Tu hora de nacimiento está justo en un límite: un minuto de diferencia cambiaría parte del tiempo de dinero y carrera, así que esa parte se reserva.",
        "none": "No destaca una oportunidad fuerte en los próximos 24 meses. Úsalo para construir con constancia.",
        "summary": "Tu mejor ventana: {area}, {dates}.",
        "themes": {1: "tu impulso e identidad", 2: "ahorros y familia", 3: "esfuerzo y valentía",
                   4: "hogar y tranquilidad", 5: "hijos y creatividad", 6: "salud y trabajo diario",
                   7: "relaciones y sociedades", 8: "asuntos ocultos y repentinos", 9: "suerte y guía",
                   10: "carrera y posición", 11: "ingresos y ganancias", 12: "gastos y asuntos en el extranjero"},
        "year_good": "A tu favor este año: {items}.",
        "year_watch": "Maneja con cuidado este año: {items}.",
        "year_quiet": "Tranquilo este año (poco movimiento): {items}.",
        "year_tone": {"favourable": "Un año de apoyo en general.", "mixed": "Un año mixto: ganancias reales y pruebas reales.",
                      "testing": "Un año de pruebas. Apóyate en los remedios y mantén los planes simples.",
                      "quiet": "El texto tradicional no dice nada específico sobre tus posiciones este año."},
        "remedy_for": "Para {theme}",
        "special": "Este es un año de inflexión en tu ciclo.",
        "focus_title": "Tu enfoque para los próximos seis meses",
        "focus_head": {"money": "Enfócate en los ingresos", "career": "Enfócate en tu próximo ascenso",
                       "relationship": "Enfócate en tu relación o sociedad más cercana",
                       "learning": "Enfócate en aprender bien una cosa",
                       "protect": "Protege tu energía y tu dinero", "build": "Construye con constancia"},
        "focus_step": {"money": "Esta semana, haz una lista de los tres tratos o clientes más cerca de cerrar y ponle fecha a cada uno.",
                       "career": "Esta semana, escribe el puesto o alcance que quieres y pídeselo a una persona que decida.",
                       "relationship": "Esta semana, organiza la conversación que has estado posponiendo.",
                       "learning": "Esta semana, elige el curso o la habilidad y reserva la primera sesión.",
                       "protect": "Esta semana, lista tus costos fijos y recorta un compromiso que no te devuelve nada.",
                       "build": "Esta semana, elige el proyecto que más importa y termina su siguiente paso."},
        "focus_active": "Activo ahora", "focus_starts": "Empieza {when}",
        "focus_also": "También a la vista",
        "focus_avoid": "Ve con calma en {label}. {action}",
    },
}


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def _fmt(loc: str, a: str, b: str) -> str:
    m = MONTHS[loc]
    da, db = _d(a), _d(b)
    if (da.year, da.month) == (db.year, db.month):
        return f"{m[da.month - 1]} {da.year}"
    if da.year == db.year:
        return f"{m[da.month - 1]} – {m[db.month - 1]} {da.year}"
    return f"{m[da.month - 1]} {da.year} – {m[db.month - 1]} {db.year}"


def _overlap(a, b) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _clip(span, today: str):
    s, e = max(span[0], today), span[1]
    return (s, e) if e >= today else None


def _collect(fc: dict, fragile: bool, today: str) -> Dict[str, List[dict]]:
    """Per area: list of {src, season/peak span, top (bool)}."""
    out: Dict[str, List[dict]] = {a: [] for a in AREAS}
    for s in fc.get("parashari", {}).get("spans", []):
        area = _PAR_EVENT.get(s["event"])
        sp = _clip((s["start"], s["end"]), today)
        if area and sp:
            out[area].append({"src": "par", "span": sp, "top": s["grade"] == "strong",
                              "d10": area in ("money", "career")})
    _MDK = {"marriage": "relationship", "career": "career", "money": "money"}
    for s in fc.get("mandook", {}).get("spans", []):
        area = _MDK.get(s["event"])
        sp = _clip((s["start"], s["end"]), today)
        if area and sp:
            out[area].append({"src": "mdk", "span": sp, "peak": sp, "top": False, "d10": False})
    for s in fc.get("event_spans", []):
        area = _JAI_EVENT.get(s["event"])
        if not area:
            continue
        if s["event"] == "education" and s["tier"] != "triple":
            continue
        sp = _clip((s["start"], s["end"]), today)
        pk = _clip(tuple(s.get("peak", (s["start"], s["end"]))), today)
        if sp:
            out[area].append({"src": "jai", "span": sp, "peak": pk or sp, "top": s["tier"] == "triple", "d10": False})
    if not fragile:
        for s in fc.get("d10", {}).get("spans", []):
            sp = _clip((s["start"], s["end"]), today)
            pk = _clip(tuple(s.get("peak", (s["start"], s["end"]))), today)
            if sp:
                out["money"].append({"src": "jai", "span": sp, "peak": pk or sp,
                                     "top": s.get("gain_score", 0) >= 4, "d10": True})
    return out


def _merge_area(items: List[dict], fragile: bool) -> List[dict]:
    res: List[dict] = []
    for it in sorted(items, key=lambda x: x["span"]):
        placed = False
        for r in res:
            if _overlap(r["span"], it["span"]):
                r["span"] = (min(r["span"][0], it["span"][0]), max(r["span"][1], it["span"][1]))
                r["srcs"].add(it["src"]); r["top"] |= it["top"]; r["d10"] |= it["d10"]
                if it["src"] == "jai":
                    r["peaks"].append(it["peak"])
                placed = True
                break
        if not placed:
            res.append({"span": it["span"], "srcs": {it["src"]}, "top": it["top"], "d10": it["d10"],
                        "peaks": [it["peak"]] if it["src"] == "jai" else []})
    for r in res:
        r["strength"] = "strong" if len(r["srcs"]) >= 2 else ("good" if r["top"] else "possible")
        if fragile and r["d10"] and r["strength"] == "strong":
            r["strength"] = "good"
    return res


_PLANET_WORDS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu",
                 "sol", "luna", "marte", "mercurio", "júpiter", "venus", "saturno")


def _plain_ok(text: str) -> bool:
    low = text.lower()
    return not any(w in low.replace("saturday", "").replace("sunday", "").replace("monday", "")
                   for w in ("rahu", "ketu", "jupiter", "saturn ", "saturn,", "saturn.", "mars", "mercury", "venus "))


def _year_block(lk: dict, loc: str) -> Optional[dict]:
    """Lal Kitab year view (Roop Chand's annual rules that apply to this chart this year), in plain language."""
    if not lk:
        return None
    tx = T[loc]
    items = lk.get("rc") or []

    def pick(tone):
        out, seen = [], set()
        for i in items:
            t = i.get("es") if loc == "es" else i.get("en")
            if i["tone"] == tone and t and t not in seen:
                seen.add(t)
                out.append(t)
        return out

    good, bad = pick("good"), pick("bad")
    ng, nb = len(good), len(bad)
    tone = "quiet" if not (ng or nb) else ("favourable" if ng >= nb + 2 else ("testing" if nb >= ng + 2 else "mixed"))
    parts = [tx["year_tone"][tone]]
    remedies, seen = [], set()
    for i in items:
        r = i.get("remedy_es") if loc == "es" else i.get("remedy_en")
        if i["tone"] == "bad" and r and r not in seen:
            seen.add(r)
            remedies.append({"for": "", "do": r, "timing": "", "duration": ""})
    if remedies:
        remedies.append({"for": "", "do": lk.get("principle", {}).get(loc) or lk.get("principle", {}).get("en", ""),
                         "timing": "", "duration": "43"})
    return {"tone": tone, "summary": " ".join(parts), "good": good[:5], "watch": bad[:5], "quiet": [],
            "remedies": remedies[:4], "year_lord": lk.get("year_lord"), "rules_used": [i["id"] for i in items]}


_FOCUS_ORDER = ("money", "career", "relationship", "learning")   # tie-break: owner's product focus order
HORIZON_DAYS = 183


def _days(a: str, b: str) -> int:
    return (_d(b) - _d(a)).days


def _focus_block(areas: List[dict], cautions: List[dict], loc: str, today_s: str) -> dict:
    """Antar-driven focus for the next six months: one primary focus chosen by the engine."""
    tx = T[loc]
    t0 = _d(today_s)
    h_end = date.fromordinal(t0.toordinal() + HORIZON_DAYS).isoformat()

    def overlap(a, b):
        lo, hi = max(a, today_s), min(b, h_end)
        return max(0, _days(lo, hi)) if lo <= hi else 0

    cands = []
    for ar in areas:
        for w in ar["windows"]:
            ov = overlap(w["start"], w["end"])
            if ov > 0:
                cands.append({"area": ar["area"], "w": w, "ov": ov, "rank": _RANK[w["strength"]]})
    cands.sort(key=lambda c: (-c["rank"], -c["ov"], _FOCUS_ORDER.index(c["area"])))

    caution_days = 0
    pressure = None
    for c in cautions:
        ov = overlap(c["start"], c["end"])
        caution_days += ov
        if ov and pressure is None:
            pressure = c
    # Protect only when pressure dominates AND nothing strong or good is active; otherwise the
    # pressure becomes a "go lightly" note beside a real focus.
    protect = caution_days >= int(HORIZON_DAYS * 0.6) and not (cands and cands[0]["rank"] >= 1)

    def when(w):
        return tx["focus_active"] if w["start"] <= today_s else tx["focus_starts"].format(
            when=_fmt(loc, w["start"], w["start"]))

    if protect:
        mode, key, win = "protect", "protect", None
    elif cands and cands[0]["rank"] >= 1:
        mode, key, win = "push", cands[0]["area"], cands[0]["w"]
    elif cands:
        mode, key, win = "build", cands[0]["area"], cands[0]["w"]
    else:
        mode, key, win = "build", "build", None

    primary = {"area": key if key in _FOCUS_ORDER else None, "headline": tx["focus_head"][key],
               "first_step": tx["focus_step"][key]}
    if win:
        primary.update({"window": win["label"], "timing": when(win), "strength": win["strength"],
                        "strength_label": win["strength_label"], "why": win["why"], "action": win["action"]})
    also = []
    for c in cands:
        if c["area"] != primary["area"] and len(also) < 2:
            also.append({"area": c["area"], "headline": tx["focus_head"][c["area"]], "window": c["w"]["label"],
                         "timing": when(c["w"]), "strength_label": c["w"]["strength_label"]})
    avoid = None
    if pressure and not protect:
        avoid = {"label": pressure["label"], "text": tx["focus_avoid"].format(label=pressure["label"], action=pressure["action"])}
    return {"title": tx["focus_title"], "horizon": [today_s, h_end], "mode": mode,
            "primary": primary, "also": also, "avoid": avoid}


def compose(forecast: dict, locale: str = "en", today: Optional[date] = None) -> dict:
    loc = locale if locale in T else "en"
    tx = T[loc]
    if not forecast.get("available"):
        return {"available": False}
    today_s = (today or date.today()).isoformat()
    sens = forecast.get("d10", {}).get("sensitivity", {})
    fragile = bool(sens.get("gate", sens.get("fragile")))      # gate lifted when the user confirmed an exact time
    per_area = {a: _merge_area(v, fragile) for a, v in _collect(forecast, fragile, today_s).items()}

    areas, best = [], None
    for a in AREAS:
        wins = []
        for r in sorted(per_area[a], key=lambda x: x["span"]):
            peak = None
            if r["peaks"]:
                lo = min(p[0] for p in r["peaks"]); hi = max(p[1] for p in r["peaks"])
                if (lo, hi) != r["span"]:
                    peak = (lo, hi)
            why = (tx["why_three"] if len(r["srcs"]) >= 3 else tx["why_both"] if len(r["srcs"]) == 2
                   else tx["why_one"] if r["strength"] in ("good", "strong") else tx["why_weak"])
            if peak:
                why += " " + tx["why_peak"].format(peak=_fmt(loc, *peak))
            w = {"start": r["span"][0], "end": r["span"][1], "label": _fmt(loc, *r["span"]),
                 "peak": list(peak) if peak else None, "strength": r["strength"],
                 "strength_label": tx["strength"][r["strength"]], "both_systems": len(r["srcs"]) >= 2,
                 "headline": tx["headline"][a], "why": why, "action": tx["action"][a]}
            wins.append(w)
            key = (_RANK[r["strength"]], -len(r["span"][0]))
            if best is None or _RANK[r["strength"]] > _RANK[best[1]["strength"]] or \
                    (_RANK[r["strength"]] == _RANK[best[1]["strength"]] and w["start"] < best[1]["start"]):
                best = (a, w)
        areas.append({"area": a, "title": tx["area"][a], "windows": wins})

    cautions = []
    c_all = list(forecast.get("caution_spans", [])) + list(forecast.get("parashari", {}).get("caution_spans", []))
    spans = []
    for c in c_all:
        sp = _clip((c["start"], c["end"]), today_s)
        if sp:
            spans.append({"span": sp})
    merged = []
    for it in sorted(spans, key=lambda x: x["span"]):
        if merged and _overlap(merged[-1], it["span"]):
            merged[-1] = (merged[-1][0], max(merged[-1][1], it["span"][1]))
        else:
            merged.append(it["span"])
    for sp in merged:
        cautions.append({"start": sp[0], "end": sp[1], "label": _fmt(loc, *sp),
                         "headline": tx["caution_head"], "action": tx["caution_action"]})

    summary = (tx["summary"].format(area=tx["area"][best[0]], dates=best[1]["label"]) if best else tx["none"])
    exact = str(sens.get("accuracy") or "").lower() == "exact"
    notes = [tx["birth_time_edge"] if exact else tx["birth_time"]] if fragile else []
    focus = _focus_block(areas, cautions, loc, today_s)
    annual = (forecast.get("lal_kitab") or {}).get("annual") or []
    return {"available": True, "locale": loc, "summary": summary, "areas": areas,
            "focus": focus, "cautions": cautions,
            "year": _year_block(annual[0] if annual else None, loc), "notes": notes}
