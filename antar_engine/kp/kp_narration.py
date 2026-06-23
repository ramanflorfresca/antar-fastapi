"""
kp_narration.py  —  A5: jargon-free rendering of the KP verdict bundle.

Turns a structured KP result into concrete user text: a verdict, a dated/timed
window, one action, and a 0-3 conviction meter. ZERO KP jargon — no sub-lord,
significator, house number, planet, or nakshatra ever appears. Output is run
through the project's output_strips as a defensive backstop.

EN + ES (the two languages the app supports). Respects the language param.
"""

import swisseph as swe

_MONTHS = {
    "en": ["", "January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "es": ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
}

_VERDICT = {
    "en": {
        "yes": "Yes — conditions support this.",
        "no": "Not right now — conditions don't back this.",
        "conditional": "Possible, but only once one piece falls into place first.",
    },
    "es": {
        "yes": "Sí — las condiciones lo respaldan.",
        "no": "Ahora no — las condiciones no lo respaldan.",
        "conditional": "Posible, pero solo cuando antes encaje una pieza.",
    },
}

_WINDOW_LEAD = {"en": "Clearest window: ", "es": "Ventana más clara: "}
_NO_WINDOW = {"en": "No clear window in the months ahead.",
              "es": "Sin ventana clara en los próximos meses."}
_ACTION_LEAD = {"en": "Your move: ", "es": "Tu paso: "}
_CONVICTION_LABEL = {
    "en": {0: "very low", 1: "low", 2: "moderate", 3: "strong"},
    "es": {0: "muy baja", 1: "baja", 2: "moderada", 3: "fuerte"},
}


def _jd_to_month_year(jd, language):
    y, m, d, _h = swe.revjul(jd)
    months = _MONTHS.get(language, _MONTHS["en"])
    return f"{months[int(m)]} {int(y)}"


def _window_text(window, language):
    if not window or window.get("start_jd") is None:
        return _NO_WINDOW.get(language, _NO_WINDOW["en"])
    a = _jd_to_month_year(window["start_jd"], language)
    b = _jd_to_month_year(window["end_jd"], language)
    rng = a if a == b else f"{a} – {b}"
    return _WINDOW_LEAD.get(language, _WINDOW_LEAD["en"]) + rng


def _meter(confidence):
    c = max(0, min(3, int(confidence or 0)))
    return "●" * c + "○" * (3 - c)


def _strip(text, language):
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        return apply_user_facing_strips(text, language=language, field_type="plain")
    except Exception:
        return text


def narrate(bundle, language="en"):
    """
    bundle: {verdict, confidence, drivers[], window:{start_jd,end_jd}|None,
             action?}  ->  jargon-free dict for the client.
    """
    language = "es" if str(language).lower().startswith("es") else "en"
    verdict = bundle.get("verdict", "conditional")
    confidence = int(bundle.get("confidence", 0) or 0)

    headline = _VERDICT[language].get(verdict, _VERDICT[language]["conditional"])
    drivers = [d for d in (bundle.get("drivers") or []) if d]
    why = drivers[1] if len(drivers) > 1 else (drivers[0] if drivers else "")

    window_text = _window_text(bundle.get("window"), language)

    action = bundle.get("action")
    if not action:
        action = ("Move when the window opens; don't force it before."
                  if language == "en" else
                  "Avanza cuando se abra la ventana; no la fuerces antes.")

    answer = headline if not why else f"{headline} {why}"
    return {
        "answer": _strip(answer, language),
        "window": _strip(window_text, language),
        "action": _strip(_ACTION_LEAD[language] + action, language),
        "conviction": confidence,            # 0-3 integer
        "conviction_meter": _meter(confidence),
        "conviction_label": _CONVICTION_LABEL[language][max(0, min(3, confidence))],
    }
