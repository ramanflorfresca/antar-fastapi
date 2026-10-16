"""[day-strip 2026-10-15] The 7 days back / today / 7 days ahead strip for "Today in detail".

Every day is shaped from the SAME deterministic input the Today card already trusts: the day's score
(daily_v2.day_energy: friction < 4, steady >= 7, else light). No LLM text and no saved prose, so a day's chip can never
contradict the card for that day, and the strip agrees with /daily-week by construction.

Past days are RE-READ from the chart for that date (the saved daily cache only holds days warmed ahead of time, so most
past days were never stored). They say so (`source: "recomputed"`): honest, never presented as something we told the
user at the time."""
from __future__ import annotations

from datetime import date as _date, timedelta as _td
from typing import Optional

from antar_engine.daily_v2 import day_energy as _day_energy

VERSION = "day-strip-2"
DAYS_BACK = 7
DAYS_AHEAD = 7


def _d(x) -> Optional[_date]:
    try:
        return _date.fromisoformat(str(x)[:10])
    except Exception:
        return None


_COPY = {
    "en": {"best": "{d}: the strongest day ahead. A good day to start something, ask for something or close a deal.",
           "care": "{d}: a slower day. If it can wait, avoid signing, big spending or a hard conversation.",
           "line_best": "Best day {d}.", "line_care": "Slower day {d}.",
           "legend": [{"key": "steady", "label": "Good day", "meaning": "Act, ask and start things."},
                      {"key": "light", "label": "Steady day", "meaning": "Keep to your plan; nothing needs forcing."},
                      {"key": "friction", "label": "Tough day", "meaning": "Slow down; avoid big commitments if you can wait."}],
           "tags": {"best": "best", "care": "slower"}},
    "es": {"best": "{d}: el día más fuerte que viene. Buen día para empezar algo, pedir algo o cerrar un trato.",
           "care": "{d}: un día más lento. Si puede esperar, evita firmar, gastar mucho o una conversación difícil.",
           "line_best": "Mejor día {d}.", "line_care": "Día lento {d}.",
           "legend": [{"key": "steady", "label": "Día bueno", "meaning": "Actúa, pregunta y empieza cosas."},
                      {"key": "light", "label": "Día estable", "meaning": "Sigue tu plan; nada necesita forzarse."},
                      {"key": "friction", "label": "Día difícil", "meaning": "Ve despacio; evita grandes compromisos si puedes esperar."}],
           "tags": {"best": "mejor", "care": "lento"}},
}


def _day_name(dt: _date, lang: str) -> str:
    wk = {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
          "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]}[lang if lang in ("en", "es") else "en"]
    mo = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}[lang if lang in ("en", "es") else "en"]
    return f"{wk[dt.weekday()]} {mo[dt.month - 1]} {dt.day}"


def build_strip(days: list, today: _date, language: str = "en") -> dict:
    """days: engine day dicts (need `date` and `score`). Returns the strip; days with no usable date/score are left out."""
    lang = (language or "en").split("-")[0].lower()
    by_date = {}
    for raw in days or []:
        dt = _d((raw or {}).get("date"))
        if dt is not None and raw.get("score") is not None:
            by_date[dt] = raw
    out = []
    for off in range(-DAYS_BACK, DAYS_AHEAD + 1):
        dt = today + _td(days=off)
        raw = by_date.get(dt)
        if raw is None:
            out.append({"date": dt.isoformat(), "offset": off,
                        "kind": "today" if off == 0 else ("past" if off < 0 else "future"), "status": "no_reading"})
            continue
        de = _day_energy(raw, lang)
        out.append({"date": dt.isoformat(), "weekday": dt.strftime("%a"), "offset": off,
                    "kind": "today" if off == 0 else ("past" if off < 0 else "future"),
                    "status": "ready", "energy": {"key": de["key"], "label": de["label"], "tone": de["tone"]},
                    "score": de["score"], "source": "recomputed" if off < 0 else "live"})
    ahead = [x for x in out if x["kind"] == "future" and x["status"] == "ready"]
    best = max(ahead, key=lambda x: x["score"]) if ahead else None
    care = min(ahead, key=lambda x: x["score"]) if ahead else None
    cp = _COPY.get(lang) or _COPY["en"]
    # a "slower" day is only named when it really is a tough one (score band), and never the same day as the best one
    if care is not None and (care["energy"]["key"] != "friction" or (best is not None and care["date"] == best["date"])):
        care = None
    if best is not None and best["energy"]["key"] == "light" and best["score"] < 6:
        best = None   # no day this strong: do not call a middling day "the strongest"
    for x in out:
        x.pop("tag", None)
        if best is not None and x["date"] == best["date"]:
            x["tag"] = cp["tags"]["best"]
        elif care is not None and x["date"] == care["date"]:
            x["tag"] = cp["tags"]["care"]
    wl = {"best": None, "care": None, "text": None}
    parts = []
    if best is not None:
        lbl = _day_name(_d(best["date"]), lang)
        wl["best"] = {"date": best["date"], "label": lbl, "reason_plain": cp["best"].format(d=lbl)}
        parts.append(cp["line_best"].format(d=lbl))
    if care is not None:
        lbl = _day_name(_d(care["date"]), lang)
        wl["care"] = {"date": care["date"], "label": lbl, "reason_plain": cp["care"].format(d=lbl)}
        parts.append(cp["line_care"].format(d=lbl))
    wl["text"] = " ".join(parts) or None
    return {"date": today.isoformat(), "language": lang, "days": out,
            "best_ahead": best["date"] if best else None,
            "care_ahead": care["date"] if care else None,
            "week_line": wl, "legend": cp["legend"],
            "version": VERSION}
