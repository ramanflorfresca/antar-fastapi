"""
EXPERIMENTAL KP read for speculation questions, behind the `kp_speculation` app_config flag ('off' | 'all' | chart ids).
Verdict from the KP module (11th-cusp sub lord test) plus up to 6 dated windows where the running periods and the
transits both support gain. Always labelled low confidence; KP is not validated against outcomes. Deterministic.
"""
from datetime import date
from typing import List, Optional

HORIZON_DAYS = 730
MAX_WINDOWS = 6

TEXT = {
    "en": {"yes": "A supportive read for speculation, with low confidence.",
           "conditional": "A mixed read: gains are possible, but only if the follow-through lines up first.",
           "no": "An unsupportive read for speculation.",
           "none": "No dated window stands out.",
           "note": "Experimental and low confidence: this method has not been checked against outcomes yet. "
                   "It is a caution about timing, not a call on any bet; risk only what you can afford to lose."},
    "es": {"yes": "Una lectura favorable para la especulación, con baja confianza.",
           "conditional": "Una lectura mixta: hay posibilidad de ganancias, pero solo si primero se alinea el seguimiento.",
           "no": "Una lectura desfavorable para la especulación.",
           "none": "No destaca ninguna ventana con fecha.",
           "note": "Experimental y de baja confianza: este método aún no se ha contrastado con resultados. "
                   "Es una advertencia sobre el momento, no una recomendación de apuesta; arriesga solo lo que puedas perder."},
}


def enabled_for(supabase, chart_id: str) -> bool:
    try:
        from antar_engine import app_config
        v = str(app_config.get(supabase, "kp_speculation", "off")).strip().lower()
    except Exception:
        return False
    if v in ("", "off", "false", "0"):
        return False
    if v in ("all", "on"):
        return True
    return str(chart_id).lower() in {x.strip() for x in v.split(",")}


def _windows(chart, start_jd: float) -> List[tuple]:
    from antar_engine.kp import kp_timing as kt, kp_significators as ks
    sigs = {p for p in ks.ALL_PLANETS if kt._net_positive(chart, p, {2, 5, 6, 11}, {8, 12})}
    periods = kt.build_timeline(chart, start_jd + HORIZON_DAYS + 400.0)
    out, st, j, last = [], None, start_jd, None
    while j <= start_jd + HORIZON_DAYS:
        if kt._combined_pass(periods, sigs, j, "ad_pd", True):
            st = j if st is None else st
            last = j
        elif st is not None:
            out.append((st, last + 3.0))
            st = None
        j += 3.0
    if st is not None:
        out.append((st, last + 3.0))
    return out


def build(chart_record: dict, language: str = "en", today: Optional[date] = None) -> Optional[dict]:
    import swisseph as swe
    from antar_engine.kp import kp_significators as ks
    from antar_engine.kp.kp_service import _build_chart
    chart = _build_chart(chart_record)
    if not chart:
        return None
    lang = "es" if language == "es" else "en"
    t = TEXT[lang]
    today = today or date.today()
    start = swe.julday(today.year, today.month, today.day, 12.0)
    v = ks.verdict(chart, "speculation")
    wins = []
    for a, b in _windows(chart, start)[:MAX_WINDOWS]:
        ya, ma, da = swe.revjul(a)[:3]
        yb, mb, db = swe.revjul(b)[:3]
        wins.append({"start": date(ya, ma, da).isoformat(), "end": date(yb, mb, db).isoformat()})
    return {"experimental": True, "confidence": "low", "verdict": v["verdict"], "headline": t.get(v["verdict"], t["conditional"]),
            "windows": wins, "windows_note": None if wins else t["none"], "note": t["note"]}
