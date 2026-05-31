"""
antar_engine/practice_scopes.py
─────────────────────────────────────────────────────────────────────────────
Practice redesign — negative-anchored, multi-scale detectors.  Phase 1.

Five time-scales, each with a detector that returns the active negative
remediations (anchored to what is *causing friction*, not to a "priority
planet").  Entries are uniformly shaped; the composer ranks and dresses them.

Reuses: places_conditions (natal dignity), lal_kitab_advanced (sleeping + rin),
varshaphal_table (annual LK house progression), swisseph (transits).
"""

from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional

try:
    import swisseph as swe
    _SWE = True
except Exception:                                       # pragma: no cover
    swe = None
    _SWE = False

from antar_engine.places_conditions import (
    compute_all_conditions, SIGN_LORDS_BY_INDEX,
)

MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
DUSTHANA = {6, 8, 12}

SCOPES = {
    "natal_weakness": {"label": "Natal weakness", "ttl_days": None},
    "dasha_period":   {"label": "Dasha period", "ttl_days": "varies"},
    "varshphal_year": {"label": "Varshphal (yearly LK)", "ttl_days": 365},
    "monthly_lk":     {"label": "Monthly chart (LK)", "ttl_days": 30},
    "daily_transit":  {"label": "Today's transit", "ttl_days": 1},
}

_PID = {"Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4,
        "Jupiter": 5, "Saturn": 6, "Rahu": 10}


def _lang(language: str) -> str:
    return "es" if str(language).lower().startswith("es") else "en"


def _planets(chart: dict) -> dict:
    return (chart or {}).get("planets", {}) or {}


def _house(chart: dict, planet: str) -> Optional[int]:
    rec = _planets(chart).get(planet, {})
    h = rec.get("house")
    return int(h) if h is not None else None


def _lagna_index(chart: dict) -> Optional[int]:
    lg = chart.get("lagna")
    if isinstance(lg, dict) and lg.get("sign_index") is not None:
        return int(lg["sign_index"])
    from antar_engine.places_relocation import SIGN_INDEX
    s = chart.get("lagna_sign")
    return SIGN_INDEX.get(s)


def _functional_malefic_lords(chart: dict) -> set:
    """Lords of the dusthana houses (6/8/12) from the lagna — functional malefics."""
    li = _lagna_index(chart)
    if li is None:
        return set()
    return {SIGN_LORDS_BY_INDEX[(li + h - 1) % 12] for h in (6, 8, 12)}


# ─────────────────────────────────────────────────────────────────────────────
# Bilingual why-paragraphs
# ─────────────────────────────────────────────────────────────────────────────

def _why(scope: str, planet: str, kind: str, lang: str, **kw) -> str:
    T = {
        ("natal_weakness", "debilitated"): {
            "en": f"{planet} is weak in your birth chart. The friction shows up wherever {planet} governs — it asks for daily, patient attention.",
            "es": f"{planet} está débil en tu carta de nacimiento. La fricción aparece donde {planet} gobierna — pide atención diaria y paciente."},
        ("natal_weakness", "combust"): {
            "en": f"{planet} is overshadowed by the Sun in your chart — its signal gets drowned out. Daily practice gives it back its own voice.",
            "es": f"{planet} está eclipsado por el Sol en tu carta — su señal se ahoga. La práctica diaria le devuelve su propia voz."},
        ("natal_weakness", "sleeping"): {
            "en": f"{planet} is dormant in your chart — its gifts are present but asleep. Daily practice is how you wake it.",
            "es": f"{planet} está dormido en tu carta — sus dones están presentes pero dormidos. La práctica diaria es cómo lo despiertas."},
        ("natal_weakness", "dusthana"): {
            "en": f"{planet} sits in a difficult house with no friendly support, so its energy drains rather than builds. Daily tending steadies it.",
            "es": f"{planet} está en una casa difícil sin apoyo amistoso, así que su energía se escapa en vez de construir. El cuidado diario lo estabiliza."},
        ("natal_weakness", "sandhi"): {
            "en": f"{planet} sits right at the edge of a sign — a tender, unstable spot. Daily practice gives it ground.",
            "es": f"{planet} está justo en el borde de un signo — un punto tierno e inestable. La práctica diaria le da suelo."},
        ("natal_weakness", "rin"): {
            "en": f"Your chart carries a karmic debt tied to {planet}. Lal Kitab treats this with steady, humble daily acts until the debt settles.",
            "es": f"Tu carta lleva una deuda kármica ligada a {planet}. Lal Kitab la trata con actos diarios constantes y humildes hasta que la deuda se salda."},
        ("dasha_period", "md"): {
            "en": f"You are in a {planet} chapter, and {planet} runs strained in your chart. For the length of this period its rough edge is amplified — tend it until the chapter turns.",
            "es": f"Estás en un capítulo de {planet}, y {planet} viene tensionado en tu carta. Durante este periodo su borde áspero se amplifica — atiéndelo hasta que el capítulo cambie."},
        ("dasha_period", "ad"): {
            "en": f"{planet} is the active sub-period right now and it runs strained in your chart — a shorter, sharper pull worth tending while it lasts.",
            "es": f"{planet} es el subperiodo activo ahora mismo y viene tensionado en tu carta — un tirón más corto y agudo que vale la pena atender mientras dure."},
        ("varshphal_year", "house"): {
            "en": f"In your chart for this year, {planet} falls into a draining position. The theme it touches asks for attention across the whole year.",
            "es": f"En tu carta de este año, {planet} cae en una posición que desgasta. El tema que toca pide atención durante todo el año."},
        ("varshphal_year", "yoga"): {
            "en": f"This year's chart puts {planet} with {kw.get('other','another hard planet')} — a friction pairing that colors the year. Tend it through the solar year.",
            "es": f"La carta de este año pone a {planet} con {kw.get('other','otro planeta difícil')} — una combinación de fricción que tiñe el año. Atiéndela durante el año solar."},
        ("monthly_lk", "transit"): {
            "en": f"This month, {planet} moves through a sensitive part of your chart. It's a passing pressure — tend it through the month.",
            "es": f"Este mes, {planet} atraviesa una parte sensible de tu carta. Es una presión pasajera — atiéndela durante el mes."},
        ("daily_transit", "hit"): {
            "en": f"Today {kw.get('agent','a hard planet')} presses on your {planet} point — short-term reactivity that resolves overnight. A small practice steadies the day.",
            "es": f"Hoy {kw.get('agent','un planeta duro')} presiona tu punto de {planet} — reactividad de corto plazo que se resuelve durante la noche. Una pequeña práctica estabiliza el día."},
    }
    return T.get((scope, kind), {}).get(lang, "")


# ─────────────────────────────────────────────────────────────────────────────
# Detectors
# ─────────────────────────────────────────────────────────────────────────────

def detect_natal_weakness(chart: dict, language: str = "en", conditions: Optional[dict] = None) -> list[dict]:
    lang = _lang(language)
    conditions = conditions or compute_all_conditions(chart)
    out: dict[str, dict] = {}

    def _add(planet, kind, sev, detail):
        if planet in out and out[planet]["severity"] >= sev:
            return
        out[planet] = {
            "scope": "natal_weakness", "planet": planet, "supporting_planets": [],
            "severity": sev, "trigger_detail": detail,
            "duration_label": ("Diario, continuo" if lang == "es" else "Daily, ongoing"),
            "ttl_days": None, "why_paragraph": _why("natal_weakness", planet, kind, lang),
        }

    for planet, meta in conditions.items():
        cond = meta.get("condition")
        if cond == "debilitated":
            _add(planet, "debilitated", 0.8, f"{planet} debilitated in natal chart")
        elif cond == "combust":
            _add(planet, "combust", 0.7, f"{planet} combust (too close to the Sun)")
        elif cond == "sleeping":
            _add(planet, "sleeping", 0.6, f"{planet} sleeping per Lal Kitab")

    # In a dusthana with no benefic in the same house.
    pl = _planets(chart)
    for planet in list(_PID) + ["Ketu"]:
        h = _house(chart, planet)
        if h in DUSTHANA:
            same = [p for p, d in pl.items() if d.get("house") == h and p != planet]
            if not any(p in BENEFICS for p in same):
                _add(planet, "dusthana", 0.6, f"{planet} in a difficult house without friendly support")

    # Sign-edge (sandhi).
    for planet, rec in pl.items():
        deg = rec.get("degree")
        if deg is not None and (float(deg) <= 1.0 or float(deg) >= 29.0):
            _add(planet, "sandhi", 0.45, f"{planet} at the edge of a sign")

    # Lal Kitab debts (rin).
    try:
        from antar_engine.lal_kitab_advanced import calculate_comprehensive_rin
        for r in calculate_comprehensive_rin(pl):
            p = r.get("planet")
            if p:
                _add(p, "rin", 0.7, f"Lal Kitab debt linked to {p}")
    except Exception:
        pass

    return sorted(out.values(), key=lambda e: -e["severity"])


def detect_dasha_negatives(chart: dict, today_date: date, language: str = "en",
                           conditions: Optional[dict] = None, dashas: Optional[dict] = None) -> list[dict]:
    lang = _lang(language)
    conditions = conditions or compute_all_conditions(chart)
    if not dashas:
        return []
    from antar_engine.places_intel import get_dasha_context
    dctx = get_dasha_context(dashas, language)
    if not dctx:
        return []
    fmal = _functional_malefic_lords(chart)
    out = []

    def _bad(lord):
        if not lord:
            return None
        c = conditions.get(lord, {}).get("condition")
        if c in ("debilitated", "combust", "sleeping"):
            return c
        if lord in fmal:
            return "functional_malefic"
        if _house(chart, lord) in DUSTHANA:
            return "dusthana"
        return None

    md = dctx.get("md_lord")
    if _bad(md):
        out.append({
            "scope": "dasha_period", "planet": md, "supporting_planets": [],
            "severity": 0.72,
            "trigger_detail": f"Major-period lord {md} runs strained ({_bad(md)})",
            "duration_label": (f"Hasta {dctx.get('md_ends')}" if lang == "es" else f"Until {dctx.get('md_ends')}") if dctx.get("md_ends") else ("Periodo actual" if lang == "es" else "Current period"),
            "ttl_days": "varies", "why_paragraph": _why("dasha_period", md, "md", lang),
            "_md_ends": dctx.get("md_ends"),
        })
    ad = dctx.get("ad_lord")
    if ad and ad != md and _bad(ad):
        out.append({
            "scope": "dasha_period", "planet": ad, "supporting_planets": [],
            "severity": 0.62,
            "trigger_detail": f"Sub-period lord {ad} runs strained ({_bad(ad)})",
            "duration_label": (f"Hasta {dctx.get('ad_ends')}" if lang == "es" else f"Until {dctx.get('ad_ends')}") if dctx.get("ad_ends") else ("Subperiodo actual" if lang == "es" else "Current sub-period"),
            "ttl_days": "varies", "why_paragraph": _why("dasha_period", ad, "ad", lang),
        })
    return out


def _age_at_last_birthday(birth_date: Optional[str], today: date) -> Optional[int]:
    if not birth_date:
        return None
    try:
        s = str(birth_date)[:10]
        by, bm, bd = int(s[:4]), int(s[5:7]), int(s[8:10])
        age = today.year - by - ((today.month, today.day) < (bm, bd))
        return age if 0 <= age <= 120 else None
    except Exception:
        return None


def detect_varshphal_negatives(chart: dict, today_date: date, language: str = "en",
                               birth_date: Optional[str] = None) -> list[dict]:
    lang = _lang(language)
    age = _age_at_last_birthday(birth_date or chart.get("birth_date"), today_date)
    if age is None:
        return []
    try:
        from antar_engine.varshaphal_table import get_annual_house
    except Exception:
        return []

    pl = _planets(chart)
    annual = {}
    for planet, rec in pl.items():
        nh = rec.get("house")
        if nh:
            try:
                annual[planet] = get_annual_house(int(nh), age)
            except Exception:
                continue

    # Solar-year window label.
    start_label = next_label = ""
    bd = birth_date or chart.get("birth_date")
    if bd:
        try:
            s = str(bd)[:10]
            bm = int(s[5:7])
            start = date(today_date.year if today_date.month >= bm else today_date.year - 1, bm, 1)
            nxt = date(start.year + 1, bm, 1)
            start_label = start.strftime("%b %Y")
            next_label = nxt.strftime("%b %Y")
        except Exception:
            pass
    dur = (f"{start_label} a {next_label}" if lang == "es" else f"{start_label} to {next_label}") if start_label else \
          ("Este año solar" if lang == "es" else "This solar year")

    out = []
    seen = set()
    for planet, ah in annual.items():
        if planet in MALEFICS and ah in (8, 12) and planet not in seen:
            seen.add(planet)
            out.append({
                "scope": "varshphal_year", "planet": planet, "supporting_planets": [],
                "severity": 0.6, "trigger_detail": f"{planet} falls in a draining annual position this year",
                "duration_label": dur, "ttl_days": 365,
                "why_paragraph": _why("varshphal_year", planet, "house", lang),
            })
    # Malefic-malefic annual pairing.
    by_house = {}
    for planet, ah in annual.items():
        if planet in MALEFICS:
            by_house.setdefault(ah, []).append(planet)
    for ah, ps in by_house.items():
        if len(ps) >= 2:
            p0 = ps[0]
            if p0 not in seen:
                seen.add(p0)
                out.append({
                    "scope": "varshphal_year", "planet": p0, "supporting_planets": ps[1:],
                    "severity": 0.58, "trigger_detail": f"{' + '.join(ps)} share an annual house this year",
                    "duration_label": dur, "ttl_days": 365,
                    "why_paragraph": _why("varshphal_year", p0, "yoga", lang, other=ps[1]),
                })
    return sorted(out, key=lambda e: -e["severity"])[:2]


def _today_jd(today_date: date) -> Optional[float]:
    if not _SWE:
        return None
    return swe.julday(today_date.year, today_date.month, today_date.day, 12.0)


def _transit_lons(jd: float) -> dict:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    out = {}
    for name, pid in {"Mars": 4, "Saturn": 6, "Rahu": 10}.items():
        try:
            out[name] = swe.calc_ut(jd, pid, flags)[0][0] % 360.0
        except Exception:
            pass
    if "Rahu" in out:
        out["Ketu"] = (out["Rahu"] + 180.0) % 360.0
    return out


def _sep(a, b):
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def detect_monthly_lk_negatives(chart: dict, today_date: date, language: str = "en") -> list[dict]:
    """Malefic transiting a natal dusthana sign during the current month."""
    lang = _lang(language)
    jd = _today_jd(today_date)
    if jd is None:
        return []
    li = _lagna_index(chart)
    if li is None:
        return []
    # Natal 8th / 12th whole-sign indices.
    sensitive_signs = {(li + 7) % 12, (li + 11) % 12}
    tl = _transit_lons(jd)
    out = []
    seen = set()
    for planet, lon in tl.items():
        if planet in MALEFICS and int(lon // 30) in sensitive_signs and planet not in seen:
            seen.add(planet)
            out.append({
                "scope": "monthly_lk", "planet": planet, "supporting_planets": [],
                "severity": 0.5, "trigger_detail": f"{planet} transits a sensitive area of your chart this month",
                "duration_label": ("Este mes" if lang == "es" else "This month"), "ttl_days": 30,
                "why_paragraph": _why("monthly_lk", planet, "transit", lang),
            })
    return out[:2]


def detect_daily_transit_negatives(chart: dict, today_date: date, language: str = "en") -> list[dict]:
    """Hard transit conjunct/opposite a sensitive natal point (Moon, lagna, lagna-lord)."""
    lang = _lang(language)
    jd = _today_jd(today_date)
    if jd is None:
        return []
    tl = _transit_lons(jd)
    pl = _planets(chart)
    li = _lagna_index(chart)

    points = []  # (planet_label_for_remedy, natal_lon)
    if "Moon" in pl and pl["Moon"].get("longitude") is not None:
        points.append(("Moon", float(pl["Moon"]["longitude"])))
    if li is not None:
        lg = chart.get("lagna", {})
        ldeg = lg.get("degree") if isinstance(lg, dict) else None
        lagna_lon = li * 30.0 + (float(ldeg) if ldeg is not None else float(chart.get("lagna_deg", 0) or 0))
        lord = SIGN_LORDS_BY_INDEX[li]
        points.append((lord, lagna_lon))  # lagna point → strengthen the lagna lord
        if lord in pl and pl[lord].get("longitude") is not None:
            points.append((lord, float(pl[lord]["longitude"])))

    out = []
    seen = set()
    for agent, tlon in tl.items():
        if agent not in MALEFICS:
            continue
        for planet, nlon in points:
            sep = _sep(tlon, nlon)
            if (sep <= 6.0 or abs(sep - 180.0) <= 6.0) and planet not in seen:
                seen.add(planet)
                out.append({
                    "scope": "daily_transit", "planet": planet, "supporting_planets": [agent],
                    "severity": 0.5, "trigger_detail": f"{agent} presses on your natal {planet} point today",
                    "duration_label": ("Solo hoy" if lang == "es" else "Today only"), "ttl_days": 1,
                    "why_paragraph": _why("daily_transit", planet, "hit", lang, agent=agent),
                })
    return out[:2]


def detect_all_scopes(chart: dict, today_date: date, language: str = "en",
                      conditions: Optional[dict] = None, dashas: Optional[dict] = None,
                      birth_date: Optional[str] = None) -> list[dict]:
    conditions = conditions or compute_all_conditions(chart)
    actives = []
    actives += detect_natal_weakness(chart, language, conditions)
    actives += detect_dasha_negatives(chart, today_date, language, conditions, dashas)
    actives += detect_varshphal_negatives(chart, today_date, language, birth_date)
    actives += detect_monthly_lk_negatives(chart, today_date, language)
    actives += detect_daily_transit_negatives(chart, today_date, language)
    return actives
