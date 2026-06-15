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
import os

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

# ── timeframe-router maps (COWORK brief) ────────────────────────────────────
# Internal scope -> user-facing timeframe layer.
TIMEFRAME_BY_SCOPE = {
    "varshphal_year": "this_year",
    "monthly_lk":     "this_month",
    "dasha_period":   "current_cycle",
    "natal_weakness": "natal_baseline",
    "daily_transit":  "today",
}
# Timeframe layer -> commitment-horizon cadence (mantra/breath/yoga inside the
# practice stay daily; this is the horizon of the *reason*, per brief doctrine).
CADENCE_BY_TIMEFRAME = {
    "this_year":      "varshphal_scale",
    "this_month":     "weekly",
    "current_cycle":  "dasha_scale",
    "natal_baseline": "daily_tunein",
    "today":          "one_time",
}
# Lead priority: which timeframe owns the headline practice. Year > Month >
# Cycle. natal_baseline + today are background/acute — never the lead when any
# time-active leadable layer is present.
TIMEFRAME_LEAD_PRIORITY = {
    "this_year":      4,
    "this_month":     3,
    "current_cycle":  2,
    "today":          1,
    "natal_baseline": 0,
}
LEADABLE_TIMEFRAMES = {"this_year", "this_month", "current_cycle"}

_PID = {"Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4,
        "Jupiter": 5, "Saturn": 6, "Rahu": 10}


# ── Energy-language map — NO planet names in user-facing narration ──────────
# (internal fields like `planet` / `trigger_detail` keep the raw name)
PLANET_ENERGY = {
    "en": {
        "Sun":     "your visibility and self-direction",
        "Moon":    "your emotional steadiness",
        "Mars":    "your drive and ability to act",
        "Mercury": "your clarity of thought and speech",
        "Jupiter": "your sense of meaning and growth",
        "Venus":   "your capacity for love, beauty and connection",
        "Saturn":  "your discipline and long-term structure",
        "Rahu":    "your ambition and focus",
        "Ketu":    "your capacity to let go and turn inward",
    },
    "es": {
        "Sun":     "tu visibilidad y direcci\u00f3n propia",
        "Moon":    "tu estabilidad emocional",
        "Mars":    "tu impulso y capacidad de actuar",
        "Mercury": "tu claridad de pensamiento y palabra",
        "Jupiter": "tu sentido de prop\u00f3sito y crecimiento",
        "Venus":   "tu capacidad de amor, belleza y conexi\u00f3n",
        "Saturn":  "tu disciplina y estructura a largo plazo",
        "Rahu":    "tu ambici\u00f3n y enfoque",
        "Ketu":    "tu capacidad de soltar y mirar hacia adentro",
    },
}


def _energy(planet: str, lang: str = "en") -> str:
    return PLANET_ENERGY.get(lang, PLANET_ENERGY["en"]).get(
        planet, "this energy" if lang != "es" else "esta energ\u00eda")


def _lang(language: str) -> str:
    return "es" if str(language).lower().startswith("es") else "en"


def _dur3(language, en, es, pt):
    """3-language duration string (patch_language_fidelity). pt no longer falls to en."""
    b = str(language).split("_")[0].split("-")[0].lower()
    return {"en": en, "es": es, "pt": pt}.get(b, en)


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
    # Energy-language narration — the planet name NEVER appears in the
    # user-facing why_paragraph. Internal fields carry the raw name.
    e = _energy(planet, lang)
    E = (e[:1].upper() + e[1:]) if e else e
    T = {
        ("natal_weakness", "debilitated"): {
            "en": f"The part of you that carries {e} runs weak in your birth chart. The friction shows up wherever that energy is asked for — it wants daily, patient attention.",
            "es": f"La parte de ti que lleva {e} est\u00e1 d\u00e9bil en tu carta de nacimiento. La fricci\u00f3n aparece donde se necesita esa energ\u00eda — pide atenci\u00f3n diaria y paciente."},
        ("natal_weakness", "combust"): {
            "en": f"{E} gets drowned out in your chart — its signal is overshadowed. Daily practice gives it back its own voice.",
            "es": f"{E} queda eclipsada en tu carta — su se\u00f1al se ahoga. La pr\u00e1ctica diaria le devuelve su propia voz."},
        ("natal_weakness", "sleeping"): {
            "en": f"{E} is dormant in your chart — present but asleep. Daily practice is how you wake it.",
            "es": f"{E} est\u00e1 dormida en tu carta — presente pero dormida. La pr\u00e1ctica diaria es c\u00f3mo la despiertas."},
        ("natal_weakness", "dusthana"): {
            "en": f"{E} sits in a draining position, so it leaks rather than builds. Daily tending steadies it.",
            "es": f"{E} est\u00e1 en una posici\u00f3n que desgasta — se escapa en vez de construir. El cuidado diario la estabiliza."},
        ("natal_weakness", "sandhi"): {
            "en": f"{E} sits at a tender, unstable edge in your chart. Daily practice gives it ground.",
            "es": f"{E} est\u00e1 en un borde tierno e inestable de tu carta. La pr\u00e1ctica diaria le da suelo."},
        ("natal_weakness", "rin"): {
            "en": f"Your chart carries an old debt tied to {e}. It settles through steady, humble daily acts.",
            "es": f"Tu carta lleva una deuda antigua ligada a {e}. Se salda con actos diarios constantes y humildes."},
        ("dasha_period", "md"): {
            "en": f"This chapter of your life runs on {e}, and that energy is strained in your chart. While the period lasts its rough edge is amplified — tend it until the chapter turns.",
            "es": f"Este cap\u00edtulo de tu vida corre sobre {e}, y esa energ\u00eda viene tensionada en tu carta. Mientras dure el periodo su borde \u00e1spero se amplifica — ati\u00e9ndelo hasta que el cap\u00edtulo cambie."},
        ("dasha_period", "ad"): {
            "en": f"The current sub-period leans on {e}, which runs strained in your chart — a shorter, sharper pull worth tending while it lasts.",
            "es": f"El subperiodo actual se apoya en {e}, que viene tensionada en tu carta — un tir\u00f3n m\u00e1s corto y agudo que vale la pena atender mientras dure."},
        ("varshphal_year", "house"): {
            "en": f"This year puts {e} in a draining position. The theme it touches asks for attention across the whole year.",
            "es": f"Este a\u00f1o pone {e} en una posici\u00f3n que desgasta. El tema que toca pide atenci\u00f3n durante todo el a\u00f1o."},
        ("varshphal_year", "yoga"): {
            "en": f"This year pairs {e} with another source of friction — a combination that colors the year. Tend it through the solar year.",
            "es": f"Este a\u00f1o combina {e} con otra fuente de fricci\u00f3n — una mezcla que ti\u00f1e el a\u00f1o. Ati\u00e9ndela durante el a\u00f1o solar."},
        ("monthly_lk", "transit"): {
            "en": f"This month, a passing pressure moves across {e}. It fades on its own — tend it through the month.",
            "es": f"Este mes, una presi\u00f3n pasajera atraviesa {e}. Se disuelve sola — ati\u00e9ndela durante el mes."},
        ("daily_transit", "hit"): {
            "en": f"Today something presses on {e} — short-term reactivity that resolves overnight. A small practice steadies the day.",
            "es": f"Hoy algo presiona {e} — reactividad de corto plazo que se resuelve durante la noche. Una peque\u00f1a pr\u00e1ctica estabiliza el d\u00eda."},
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
            "duration_label": _dur3(language, "Daily, ongoing", "Diario, continuo", "Diário, contínuo"),
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
            "duration_label": _dur3(language, f"Until {dctx.get('md_ends')}", f"Hasta {dctx.get('md_ends')}", f"Até {dctx.get('md_ends')}") if dctx.get("md_ends") else _dur3(language, "Current period", "Periodo actual", "Período atual"),
            "ttl_days": "varies", "why_paragraph": _why("dasha_period", md, "md", lang),
            "_md_ends": dctx.get("md_ends"),
        })
    ad = dctx.get("ad_lord")
    if ad and ad != md and _bad(ad):
        out.append({
            "scope": "dasha_period", "planet": ad, "supporting_planets": [],
            "severity": 0.62,
            "trigger_detail": f"Sub-period lord {ad} runs strained ({_bad(ad)})",
            "duration_label": _dur3(language, f"Until {dctx.get('ad_ends')}", f"Hasta {dctx.get('ad_ends')}", f"Até {dctx.get('ad_ends')}") if dctx.get("ad_ends") else _dur3(language, "Current sub-period", "Subperiodo actual", "Subperíodo atual"),
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
    dur = _dur3(language, f"{start_label} to {next_label}", f"{start_label} a {next_label}", f"{start_label} a {next_label}") if start_label else _dur3(language, "This solar year", "Este año solar", "Este ano solar")

    out = []
    seen = set()
    # [timeframe-router] Phase-2 sleeping rule = the PRIMARY 'this year' signal.
    # Additive: the Tajika malefic-in-8/12 logic below is kept as a secondary
    # year contributor, de-duped by planet (sleeping entries claim `seen` first).
    # Behind PRACTICE_SLEEP_GATE (default on).
    if os.getenv("PRACTICE_SLEEP_GATE", "on").strip().lower() not in ("off", "0", "false"):
        try:
            from antar_engine.varshphal_chart import build_varshphal_chart
            from antar_engine.lk_rules.sleeping import (
                evaluate_sleeping_planets, PRIORITY_AWAKEN, YEAR_CAUTION_AWAKEN,
            )
            _vc = build_varshphal_chart(chart, bd or chart.get("birth_date"), today_date)
            _sleep = evaluate_sleeping_planets(_vc, chart)
            _SLEEP_SEV = {PRIORITY_AWAKEN: 0.75, YEAR_CAUTION_AWAKEN: 0.66}
            _SLEEP_KIND = {PRIORITY_AWAKEN: "sleeping", YEAR_CAUTION_AWAKEN: "caution"}
            for _p in _sleep.get("firing", []):
                _planet = _p.get("planet")
                _outcome = _p.get("outcome")
                if _planet and _outcome in _SLEEP_SEV and _planet not in seen:
                    seen.add(_planet)
                    _e = _energy(_planet, lang)
                    _E = (_e[:1].upper() + _e[1:]) if _e else _e
                    if _outcome == PRIORITY_AWAKEN:
                        _wp = (f"Tu carta anual pone {_e} a dormir este año — esta es "
                               f"la ventana para despertarla, y todo el año solar acompaña el trabajo."
                               if lang == "es" else
                               f"Your annual chart puts {_e} to sleep this year — this is "
                               f"the window to wake it, and the whole solar year supports the work.")
                    else:
                        _wp = (f"{_E} normalmente está despierta en ti, pero la carta de este "
                               f"año la atenúa. Cuidarla durante el año solar evita que se apague."
                               if lang == "es" else
                               f"{_E} normally runs awake for you, but this year's chart dims it. "
                               f"Tending it across the solar year keeps it from going quiet.")
                    out.append({
                        "scope": "varshphal_year", "planet": _planet,
                        "supporting_planets": [], "severity": _SLEEP_SEV[_outcome],
                        "trigger_detail": f"{_planet} {_outcome} in the annual chart this year",
                        "duration_label": dur, "ttl_days": 365,
                        "sleep_outcome": _outcome,
                        "why_paragraph": _wp,
                    })
        except Exception:
            pass
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
                "duration_label": _dur3(language, "This month", "Este mes", "Este mês"), "ttl_days": 30,
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
                    "duration_label": _dur3(language, "Today only", "Solo hoy", "Apenas hoje"), "ttl_days": 1,
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
    # [timeframe-router] stamp the user-facing timeframe layer on every active.
    for _e in actives:
        _e["timeframe_source"] = TIMEFRAME_BY_SCOPE.get(_e.get("scope"))
    return actives
