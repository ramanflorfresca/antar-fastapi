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
_JAI_EVENT = {"career": "career", "marriage": "relationship", "education": "learning"}
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
        "why_both": "Two independent timing methods point to this period.",
        "why_one": "One timing method points strongly to this period.",
        "why_weak": "One timing method points to this period.",
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
                      "testing": "A testing year. Lean on the remedies and keep plans simple."},
        "remedy_for": "For {theme}",
        "special": "This is a turning-point year in your cycle.",
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
        "why_both": "Dos métodos de tiempo independientes señalan este periodo.",
        "why_one": "Un método de tiempo señala con fuerza este periodo.",
        "why_weak": "Un método de tiempo señala este periodo.",
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
                      "testing": "Un año de pruebas. Apóyate en los remedios y mantén los planes simples."},
        "remedy_for": "Para {theme}",
        "special": "Este es un año de inflexión en tu ciclo.",
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
        r["strength"] = "strong" if len(r["srcs"]) == 2 else ("good" if r["top"] else "possible")
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
    """Lal Kitab annual (varshphal) view in plain language: what favours, what to watch, remedies."""
    if not lk:
        return None
    tx = T[loc]
    th = tx["themes"]
    good = sorted({th[g["house"]] for g in lk.get("good_placements", [])})
    bad = sorted({th[b["house"]] for b in lk.get("bad_placements", [])})
    good = [g for g in good if g not in bad]            # a theme that is both good and bad is "mixed": treat as watch
    quiet = sorted({th[d["house"]] for d in lk.get("dormant_areas", []) if "house" in d} -
                   set(good) - set(bad))
    ng, nb = len(good), len(bad)
    tone = "favourable" if ng >= nb + 2 else ("testing" if nb >= ng + 2 else "mixed")
    parts = [tx["year_tone"][tone]]
    if good:
        parts.append(tx["year_good"].format(items=", ".join(good)))
    if bad:
        parts.append(tx["year_watch"].format(items=", ".join(bad)))
    if quiet:
        parts.append(tx["year_quiet"].format(items=", ".join(quiet)))
    if lk.get("special_cycle"):
        parts.append(tx["special"])
    remedies = []
    houses = lk.get("annual_houses", {})
    for planet, rs in (lk.get("remedies") or {}).items():
        theme = th.get(houses.get(planet, 0), "")
        for r in rs:
            do = r.get("do", "")
            if not do or not _plain_ok(do):
                continue
            remedies.append({"for": tx["remedy_for"].format(theme=theme) if theme else "",
                             "do": do, "timing": r.get("timing", ""), "duration": r.get("duration", "")})
    return {"tone": tone, "summary": " ".join(parts), "good": good, "watch": bad, "quiet": quiet,
            "remedies": remedies[:4]}


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
            why = (tx["why_both"] if len(r["srcs"]) == 2
                   else tx["why_one"] if r["strength"] in ("good", "strong") else tx["why_weak"])
            if peak:
                why += " " + tx["why_peak"].format(peak=_fmt(loc, *peak))
            w = {"start": r["span"][0], "end": r["span"][1], "label": _fmt(loc, *r["span"]),
                 "peak": list(peak) if peak else None, "strength": r["strength"],
                 "strength_label": tx["strength"][r["strength"]], "both_systems": len(r["srcs"]) == 2,
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
    annual = (forecast.get("lal_kitab") or {}).get("annual") or []
    return {"available": True, "locale": loc, "summary": summary, "areas": areas,
            "cautions": cautions, "year": _year_block(annual[0] if annual else None, loc), "notes": notes}
