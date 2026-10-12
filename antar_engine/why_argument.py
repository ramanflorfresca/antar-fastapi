"""[why-argument 2026-10-12] The Why sheet as an ARGUMENT for this answer, not a glossary.

Owner, 2026-10-12: a sheet that explains what Rahu or Venus means is what a hundred other apps do.
What only Antar can show is why THIS answer says THIS: which timing methods decided it, what each one
found and when its support ends, whether the area itself is built to deliver, where the chart is thin
and what helps, and what would change it.

Everything is read from the convergence result the answer was built on (ask_consultation.conv:
per-method locks with window, planet, role; the divisional-chart check; the promise band; the
window and the next opening) plus the chart. Nothing is computed here that the answer did not
already use, and nothing is forecast. en + es; None for other languages and when there is nothing
truthful to say (the sheet then falls back to the plain reason).
"""
from datetime import date
from typing import Any, Dict, List, Optional

from antar_engine import ask_basis as B
from antar_engine import ask_basis_es as BE
from antar_engine import decision_i18n as I18
from antar_engine import meanings as M

_MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}

_ORDER = ("vimshottari", "chara", "varshphal", "yogini")

_T = {
    "en": {
        "m": {"vimshottari": "Your life chapters", "chara": "Your sign-based cycle", "varshphal": "Your year chart",
              "yogini": "Your short cycle"},
        "agrees": "agrees", "sits": "sits this out",
        "light": "Counted lightly: it comes from the same star as your life chapters.",
        "vim": {"chapter": "Your long chapter is {p}: it {role} your {area} area, {w}.",
                "shift": "Your current shift is {p}: it {role} your {area} area, {w}."},
        "role": {"rules": "rules", "occupies": "sits in"},
        "vim_no": "Your life chapters do not touch your {area} area in the next two years.",
        "yog": {"chapter": "The short cycle is {p}: it {role} your {area} area, {w}.",
                "shift": "The short cycle is {p}: it {role} your {area} area, {w}."},
        "yog_no": "Your short cycle does not touch your {area} area in the next two years.",
        "chara_ruler": "The running sign period is {sign}. Its ruler, {p}, rules your {area} area, {w}.",
        "chara_sign": "The running sign period is {sign}, which sits in your {area} area, {w}.",
        "chara_no": "Your sign-based cycle does not activate your {area} area in the next two years.",
        "year": "This year's chart brings {ps} into your {area} area, valid {w}.",
        "year_no": "This year's chart does not move the planets that matter for {area} into it.",
        "all": "All {n} timing methods agree.", "some": "{k} of {n} timing methods agree; {out} sits this out.",
        "none": "No timing method points at this in the next two years.",
        "varga": {"d10": "career chart", "d9": "relationship chart"},
        "vc": "Your {v} backs this: the area itself is built to deliver, not only open.",
        "vd": "Your {v} weakens this: the promise is thinner than the timing suggests, so plan for steady effort, not luck.",
        "band": {"weak": "The chart's natural promise for {area} is modest. The window is real; it rewards steady effort.",
                 "absent": "The chart does not give {area} a strong natural promise. Treat the window as something to work toward."},
        "thin": "{p} {role} your {area} area, and it is {term}: {plain}",
        "thin_role": {"lord": "runs", "support": "is the main support for"},
        "ends_first": "The support from {m} ends {d}, so the strongest stretch comes before then. After that {k} {meth} carry it until {late}.",
        "ends_same": "Support runs until {late}.",
        "next": "The next opening after that: {label}.",
        "meth_one": "method", "meth_many": "methods",
        "to": "to", "open_now": "open now",
    },
    "es": {
        "m": {"vimshottari": "Tus etapas de vida", "chara": "Tu ciclo por signos", "varshphal": "Tu carta del año",
              "yogini": "Tu ciclo corto"},
        "agrees": "coincide", "sits": "no apunta aquí",
        "light": "Cuenta menos: viene de la misma estrella que tus etapas de vida.",
        "vim": {"chapter": "Tu etapa larga es {p}: {role} tu área de {area}, {w}.",
                "shift": "Tu cambio actual es {p}: {role} tu área de {area}, {w}."},
        "role": {"rules": "rige", "occupies": "está en"},
        "vim_no": "Tus etapas de vida no tocan tu área de {area} en los próximos dos años.",
        "yog": {"chapter": "El ciclo corto es {p}: {role} tu área de {area}, {w}.",
                "shift": "El ciclo corto es {p}: {role} tu área de {area}, {w}."},
        "yog_no": "Tu ciclo corto no toca tu área de {area} en los próximos dos años.",
        "chara_ruler": "El periodo de signo en curso es {sign}. Su regente, {p}, rige tu área de {area}, {w}.",
        "chara_sign": "El periodo de signo en curso es {sign}, que está en tu área de {area}, {w}.",
        "chara_no": "Tu ciclo por signos no activa tu área de {area} en los próximos dos años.",
        "year": "La carta de este año lleva a {ps} a tu área de {area}, válida {w}.",
        "year_no": "La carta de este año no lleva a esa área los planetas que importan para {area}.",
        "all": "Los {n} métodos de tiempo coinciden.", "some": "{k} de {n} métodos de tiempo coinciden; {out} no apunta aquí.",
        "none": "Ningún método de tiempo apunta a esto en los próximos dos años.",
        "varga": {"d10": "carta de carrera", "d9": "carta de relaciones"},
        "vc": "Tu {v} lo respalda: el área está hecha para dar resultados, no solo abierta.",
        "vd": "Tu {v} lo debilita: la promesa es más delgada que el momento, así que cuenta con esfuerzo constante, no con suerte.",
        "band": {"weak": "La promesa natural de la carta para {area} es modesta. La ventana es real; premia el esfuerzo constante.",
                 "absent": "La carta no da a {area} una promesa natural fuerte. Trata la ventana como algo hacia lo que trabajar."},
        "thin": "{p} {role} tu área de {area}, y está {term}: {plain}",
        "thin_role": {"lord": "rige", "support": "es el apoyo principal de"},
        "ends_first": "El apoyo de {m} termina en {d}, así que el tramo más fuerte llega antes. Después {k} {meth} lo sostienen hasta {late}.",
        "ends_same": "El apoyo dura hasta {late}.",
        "next": "La siguiente apertura después de eso: {label}.",
        "meth_one": "método", "meth_many": "métodos",
        "to": "a", "open_now": "abierta ahora",
    },
}


def _d(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _mon(d: date, lg: str) -> str:
    return f"{_MON[lg][d.month - 1]} {d.year}"


def _range(s: Optional[date], e: Optional[date], lg: str) -> str:
    if not s or not e:
        return ""
    a, b = _mon(s, lg), _mon(e, lg)
    return a if a == b else f"{a} – {b}"


def _pn(planet: str, lg: str) -> str:
    """"Comfort (Venus)" — plain name with the Vedic name beside it."""
    p = M.planet(planet, lg)
    if not p:
        return planet
    own = I18.planet(planet, "es") if lg == "es" else planet
    return f"{p['name']} ({own})"


def _area(concern: str, lg: str) -> str:
    return (BE._TOPIC if lg == "es" else B._TOPIC).get(concern, concern)


def build(conv: Optional[dict], concern: str, chart_data: Any, language: str = "en",
          today: Optional[date] = None, timing: Optional[str] = None) -> Optional[dict]:
    try:
        if str(language or "en").split("-")[0].lower() not in ("en", "es"):
            return None
        lg = M.lang_of(language)
        t = _T[lg]
        today = today or date.today()
        locks = (conv or {}).get("locks") or {}
        if not locks:
            return None
        area = _area(concern, lg)

        methods: List[dict] = []
        active_ends = []
        for key in _ORDER:
            k = locks.get(key)
            if k is None:
                continue
            s, e = _d(k.get("start")), _d(k.get("end"))
            w = _range(s, e, lg)
            planet = _pn(k["planet"], lg) if k.get("planet") else ""
            if not k.get("active"):
                line = {"vimshottari": t["vim_no"], "chara": t["chara_no"], "varshphal": t["year_no"],
                        "yogini": t["yog_no"]}[key].format(area=area)
            elif key == "vimshottari":
                line = t["vim"][k.get("kind") or "chapter"].format(p=planet, role=t["role"].get(k.get("role"), t["role"]["occupies"]), area=area, w=w)
            elif key == "yogini":
                line = t["yog"][k.get("kind") or "chapter"].format(p=planet, role=t["role"].get(k.get("role"), t["role"]["occupies"]), area=area, w=w)
            elif key == "chara":
                sign = k.get("sign") or ""
                sign = I18.sign(sign, "es") if lg == "es" else sign
                line = (t["chara_sign"] if k.get("role") == "sign" else t["chara_ruler"]).format(sign=sign, p=planet, area=area, w=w)
            else:
                names = [_pn(p, lg) for p in (k.get("planets") or [k.get("planet")]) if p]
                ps = (", ".join(names[:-1]) + (" and " if lg == "en" else " y ") + names[-1]) if len(names) > 1 else (names[0] if names else "")
                line = t["year"].format(ps=ps, area=area, w=w)
            m = {"key": key, "title": t["m"][key], "agrees": bool(k.get("active")),
                 "state_label": t["agrees"] if k.get("active") else t["sits"], "line": line, "window": w}
            if key == "yogini":
                m["note"] = t["light"]
            methods.append(m)
            if k.get("active") and e:
                active_ends.append((e, key))
        if not methods:
            return None

        agree = sum(1 for m in methods if m["agrees"])
        n = len(methods)
        out = [m["title"].lower() if lg == "en" else m["title"] for m in methods if not m["agrees"]]
        agreement = (t["none"] if agree == 0 else t["all"].format(n=n) if agree == n
                     else t["some"].format(k=agree, n=n, out=", ".join(out)))

        # is the promise real: the divisional chart, then the chart's natural promise
        promise = []
        from antar_engine import ask_consultation as AC
        vk = AC._CONCERN_VARGA.get((concern or "").lower())
        vs = ((conv or {}).get("varga_confirm") or {}).get("status")
        if vk and vs in ("confirmed", "denied"):
            promise.append(t["vc" if vs == "confirmed" else "vd"].format(v=t["varga"][vk]))
        band = (conv or {}).get("promise_band")
        if band in ("weak", "absent"):
            promise.append(t["band"][band].format(area=area))

        # where it is thin: the planet that runs the area, or its main support, when it is combust or debilitated
        thin: List[dict] = []
        planets = (chart_data or {}).get("planets") or {}
        lagna = ((chart_data or {}).get("lagna") or {}).get("sign")
        from antar_engine.ask_consultation import CONCERN_HOUSES, CONCERN_KARAKAS
        houses = CONCERN_HOUSES.get(concern)
        if houses and lagna in B._SIGNS and planets:
            h = B._PRIMARY.get(concern, houses[0])
            lord = B._LORD[B._SIGNS[(B._SIGNS.index(lagna) + h - 1) % 12]]
            cands = [("lord", lord)] + [("support", k) for k in (CONCERN_KARAKAS.get(concern) or [])[:1] if k != lord]
            d9 = B.d9_planets(chart_data)
            for role, name in cands:
                row = planets.get(name) or {}
                if not row.get("sign"):
                    continue
                for note in B._dignity(name, row["sign"], planets, d9):
                    tm = M.term_for_note(note, lg)
                    key = "combust" if note.startswith("combust") else "debilitated" if note.startswith("debilitated") else None
                    if not (tm and key):
                        continue
                    thin.append({"line": t["thin"].format(p=_pn(name, lg), role=t["thin_role"][role], area=area,
                                                          term=tm["term"].lower(), plain=tm["plain"][0].lower() + tm["plain"][1:]),
                                 "helps": M.TERMS[key]["helps_" + lg]})
        thin = thin[:2]

        # what would change it: when each method's support ends
        change = []
        main_ends = [x for x in active_ends if x[1] != "yogini"] or active_ends   # the lightly-counted cycle never sets the pace
        if active_ends:
            main_ends.sort()
            first_end, first_key = main_ends[0]
            last_end = max(e for e, _ in active_ends)
            late = _mon(last_end, lg)
            if first_end < last_end:
                carry = sum(1 for e, kk in active_ends if e > first_end and kk != "yogini")
                change.append(t["ends_first"].format(m=t["m"][first_key].lower(),
                                                     d=_mon(first_end, lg), k=carry,
                                                     meth=t["meth_one"] if carry == 1 else t["meth_many"], late=late))
            else:
                change.append(t["ends_same"].format(late=late))
        nxt = (conv or {}).get("next_window_label")
        if nxt:
            change.append(t["next"].format(label=nxt))

        ws, we = _d((conv or {}).get("window_start")), _d((conv or {}).get("window_end"))
        call = {"label": (timing or "").strip() or (conv or {}).get("window_label") or _range(ws, we, lg) or None,
                "open_now": bool(ws and we and ws <= today <= we)}
        return {"call": call, "methods": methods, "agreement": {"agree": agree, "of": n, "line": agreement},
                "promise": promise, "thin": thin, "change": change}
    except Exception:
        return None
