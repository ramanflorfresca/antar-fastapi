"""[decision-i18n 2026-10-10] Spanish for the Ask chart-facts line, the "holds / breaks" lines and the fallback move.

Mirrors antar_engine/ask_basis.py one-to-one (same facts, same rules, same weakness test) with native Spanish
templates. Every function returns "" when the chart can't support a truthful line — never English text."""
from __future__ import annotations

from antar_engine import ask_basis as B
from antar_engine import decision_i18n as I18

L = "es"

_TOPIC = {"career": "carrera", "business": "negocio", "wealth": "dinero", "finance": "dinero", "funding": "financiación",
          "love": "relaciones", "marriage": "matrimonio", "children": "hijos", "health": "salud", "property": "propiedad",
          "family": "familia", "education": "estudios", "loss": "pérdidas", "speculation": "especulación",
          "legal": "asuntos legales", "reconciliation": "reconciliación"}
_CHANNEL = {1: "tu esfuerzo y tu presencia personal", 2: "el ahorro y el dinero de la familia",
            3: "tu iniciativa y tu comunicación", 4: "tu base en casa y la propiedad",
            5: "el trabajo creativo y la enseñanza", 6: "el trabajo diario, el servicio y las rutinas",
            7: "las alianzas y los acuerdos uno a uno", 8: "el dinero compartido y las reestructuraciones profundas",
            9: "los mentores, la enseñanza y los planes a largo plazo", 10: "tu trabajo público y tu reputación",
            11: "tu red de contactos y tus ganancias", 12: "el trabajo entre bastidores, los vínculos con el exterior y el descanso"}
_NOTE = {"exalted": "exaltado", "debilitated": "debilitado", "in its own sign": "en su propio signo"}
_COMBUST = "combusto (debilitado por el Sol)"

_ACT = {
    "career": "pon el esfuerzo en {ch} y lleva un resultado concreto a quienes deciden",
    "business": "pon el esfuerzo en {ch} y lanza la versión más pequeña que pueda generar ingresos",
    "love": "la cercanía te llega a través de {ch}, así que da el primer paso ahí en lugar de esperar a que te encuentren",
    "marriage": "la cercanía te llega a través de {ch}, así que da el primer paso ahí en lugar de esperar a que te encuentren",
    "reconciliation": "haz un primer contacto breve y directo dentro de tu ventana — la cercanía te llega a través de {ch}, así que acércate por ahí y deja que la otra persona decida el siguiente paso",
    "wealth": "haz crecer los ingresos a través de {ch} y mantén ese dinero separado de lo que consume el negocio",
    "finance": "haz crecer los ingresos a través de {ch} y mantén ese dinero separado de lo que consume el negocio",
    "property": "define tu tope y lo imprescindible antes de ver nada — {ch} impulsa esto",
    "funding": "prepara primero los registros — la solicitud pasa por {ch}",
    "children": "pon en orden tus finanzas y tu apoyo antes de que se abra la ventana — {ch} es donde se refleja esta área",
}
_BREAKS = {
    "career": "el esfuerzo se dispersa en varios frentes, o esperas un título en lugar de entregar un resultado visible",
    "business": "el esfuerzo se dispersa en varios frentes, o lanzas antes de que un primer cliente que pague lo demuestre",
    "wealth": "los gastos y compromisos suben tan rápido como los ingresos",
    "finance": "los gastos y compromisos suben tan rápido como los ingresos",
    "funding": "los gastos y compromisos suben tan rápido como los ingresos, o las cifras no están limpias cuando pides",
    "property": "te comprometes antes de fijar tu tope y aclarar tu deuda",
    "love": "el contacto se diluye y nadie da el primer paso deliberado",
    "marriage": "el contacto se diluye y nadie da el primer paso deliberado",
    "reconciliation": "el viejo patrón se repite igual, o el primer paso se precipita",
    "children": "las bases — salud, finanzas, apoyo — se dejan al azar",
    "family": "las bases — tiempo, dinero, paciencia — se dejan al azar",
    "health": "se aguanta la tensión sin dejar tiempo de recuperación",
    "education": "la práctica es irregular",
    "speculation": "el tamaño de la posición supera lo que puedes permitirte perder",
}
# group -> (holds when the ruler is fine, holds when weakened, what the weakness means)
_HOLDS = {
    "career": ("Se sostiene si canalizas el esfuerzo a través de {ch}, donde esta área de tu carta realmente rinde",
               "Se sostiene si lo construyes a través de {ch} y dejas que los resultados se acumulen",
               "el reconocimiento va por detrás del esfuerzo; el trabajo constante y visible vale más que esperar{until}"),
    "money": ("Se sostiene si haces crecer los ingresos a través de {ch}, donde tu carta realmente rinde",
              "Se sostiene si haces crecer los ingresos a través de {ch} y dejas que se acumulen",
              "los rendimientos van por detrás del esfuerzo; acumular vale más que perseguir{until}"),
    "property": ("Funciona si fijas primero tu tope y lo imprescindible y avanzas a través de {ch}",
                 "Funciona si fijas primero tu tope y lo imprescindible y avanzas a través de {ch}",
                 "la compra encuentra fricción; un periodo de reflexión te protege{until}"),
    "love": ("Se sostiene si la cercanía se construye con intención a través de {ch}",
             "Se sostiene si la cercanía se construye con intención a través de {ch}",
             "no llegará por inercia{until}"),
    "family": ("Se sostiene si afianzas las bases a través de {ch}", "Se sostiene si afianzas las bases a través de {ch}",
               "los resultados van por detrás del esfuerzo{until}"),
}


def _ord(h: int) -> str:
    return f"casa {h}"


def _notes(planet, sign, planets):
    out = []
    for n in B._dignity(planet, sign, planets):
        out.append(_COMBUST if n.startswith("combust") else _NOTE.get(n, ""))
    return [x for x in out if x]


def _period_raw(dashas):
    """(md, ad, ad_end_date) of the running Vimśottarī period, or None."""
    from datetime import date
    rows = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
    today = date.today()
    cur = {}
    for r in rows:
        lv = str(r.get("level", "")).lower()
        try:
            s, e = date.fromisoformat(str(r.get("start_date"))[:10]), date.fromisoformat(str(r.get("end_date"))[:10])
        except Exception:
            continue
        if s <= today < e:
            key = "md" if lv in ("mahadasha", "maha", "md", "1") else "ad" if lv in ("antardasha", "antar", "ad", "2") else None
            if key:
                cur[key] = (r.get("planet_or_sign") or r.get("lord_or_sign") or "", e)
    if "md" in cur and "ad" in cur:
        return cur["md"][0], cur["ad"][0], cur["ad"][1]
    return None


def running_period(dashas) -> str:
    p = _period_raw(dashas)
    if not p:
        return ""
    md, ad, end = p
    return (f"Estás en el periodo {I18.planet(md, L)}–{I18.planet(ad, L)} "
            f"(el subperiodo termina el {I18.date_long(end, L)})")


def _facts(concern, chart_data, dashas):
    from antar_engine.ask_consultation import CONCERN_HOUSES
    planets = (chart_data or {}).get("planets") or {}
    lagna = ((chart_data or {}).get("lagna") or {}).get("sign")
    houses = CONCERN_HOUSES.get(concern)
    if not houses or lagna not in B._SIGNS or not planets:
        return None
    h = B._PRIMARY.get(concern, houses[0])
    lord = B._LORD[B._SIGNS[(B._SIGNS.index(lagna) + h - 1) % 12]]
    pl = planets.get(lord) or {}
    if not isinstance(pl.get("house"), int) or not pl.get("sign"):
        return None
    weak = any(n == "debilitated" or n.startswith("combust") for n in B._dignity(lord, pl["sign"], planets))
    per = _period_raw(dashas)
    return {"planets": planets, "h": h, "lord": lord, "pl": pl, "weak": weak, "end": per[2] if per else None,
            "ch": _CHANNEL.get(pl["house"], "")}


def build_basis(concern, chart_data, dashas) -> str:
    try:
        from antar_engine.ask_consultation import CONCERN_KARAKAS
        f = _facts(concern, chart_data, dashas)
        if not f:
            return ""
        bits = []
        per = running_period(dashas)
        if per:
            bits.append(per + ".")
        notes = _notes(f["lord"], f["pl"]["sign"], f["planets"])
        bits.append(f"Tu {_ord(f['h'])} ({_TOPIC.get(concern, concern)}) está regida por {I18.planet(f['lord'], L)}, "
                    f"que está en tu {_ord(f['pl']['house'])} en {I18.sign(f['pl']['sign'], L)}"
                    + (", " + " y ".join(notes) if notes else "") + ".")
        for k in (CONCERN_KARAKAS.get(concern) or [])[:1]:
            if k == f["lord"]:
                continue
            kp = f["planets"].get(k) or {}
            if kp.get("sign") and isinstance(kp.get("house"), int):
                kn = _notes(k, kp["sign"], f["planets"])
                bits.append(f"{I18.planet(k, L)}, el principal significador aquí, está en tu {_ord(kp['house'])}"
                            + (", " + " y ".join(kn) if kn else "") + ".")
        return " ".join(bits).strip()
    except Exception:
        return ""


def conditions(concern, chart_data, dashas) -> str:
    try:
        from antar_engine.ask_consultation import CONCERN_KARAKAS
        if concern not in _BREAKS:
            return ""
        f = _facts(concern, chart_data, dashas)
        if not f or not f["ch"]:
            return ""
        grp = B._GROUP[concern]
        h, weak, ch = f["h"], f["weak"], f["ch"]
        until_p = f" (el subperiodo actual llega hasta el {I18.date_long(f['end'], L)})" if f["end"] else ""
        if grp == "health":
            tail = (f"El regente de tu {_ord(h)} está debilitado, así que la recuperación va más lenta que el esfuerzo que haces{until_p}"
                    if weak else "Tu casa de la salud está bien apoyada, así que los hábitos pequeños rinden mucho")
            return ("El riesgo se mantiene bajo si actúas pronto y proteges el sueño y el tiempo de recuperación. "
                    + tail + f". Se rompe si {_BREAKS[concern]}.")
        if grp == "speculation":
            tail = (f"El regente de tu {_ord(h)} está debilitado, así que las ganancias tienden a llegar a golpes y a escaparse{until_p}"
                    if weak else "Tu carta favorece las posiciones medidas y planeadas sobre las impulsivas")
            return ("Se sostiene si limitas lo que arriesgas a una cantidad que puedes permitirte perder. "
                    + tail + f". Se rompe si {_BREAKS[concern]}.")
        fine, weak_t, meaning = _HOLDS[grp]
        until = f" (el subperiodo actual llega hasta el {I18.date_long(f['end'], L)})" if f["end"] else ""
        holds = (weak_t.format(ch=ch) + f" — el regente de tu {_ord(h)} está debilitado: " + meaning.format(until=until)
                 if weak else fine.format(ch=ch))
        out = holds + ". "
        for k in (CONCERN_KARAKAS.get(concern) or [])[:1]:
            kp = f["planets"].get(k) or {}
            if k != f["lord"] and kp.get("sign") and any(
                    n == "debilitated" or n.startswith("combust") for n in B._dignity(k, kp["sign"], f["planets"])):
                out += (f"{I18.planet(k, L)}, el principal significador aquí, también está debilitado, así que esto "
                        "requiere un esfuerzo deliberado en lugar de llegar por sí solo. ")
        return out + f"Se rompe si {_BREAKS[concern]}."
    except Exception:
        return ""


def chart_move(concern, chart_data, dashas) -> str:
    try:
        if concern not in B._ACT:
            return ""
        f = _facts(concern, chart_data, dashas)
        if not f or not f["ch"]:
            return ""
        end = I18.date_long(f["end"], L) if f["end"] else ""
        if concern == "health":
            when = (f" Cuenta con una recuperación más lenta durante el subperiodo actual (hasta el {end}); "
                    "no esperes a que se arregle solo.") if (f["weak"] and end) else ""
            return "Ordena primero los horarios de sueño y comida, y revisa cuanto antes cualquier cosa inusual." + when
        if concern == "speculation":
            tail = f" Reevalúa cuando termine el subperiodo actual el {end}." if (f["weak"] and end) else ""
            return ("Fija lo máximo que puedes permitirte perder, escríbelo antes de colocar nada y detente en esa cifra — "
                    "las ganancias aquí llegan a golpes y se escapan." + tail)
        act = _ACT.get(concern)
        if not act:
            return ""
        lead = (f"Como el regente de tu {_ord(f['h'])} está debilitado, los resultados van por detrás del esfuerzo — "
                if f["weak"] else "")
        tail = f" Reevalúa cuando termine el subperiodo actual el {end}." if (f["weak"] and end) else ""
        out = lead + act.format(ch=f["ch"]) + "." + tail
        return out[0].upper() + out[1:]
    except Exception:
        return ""
