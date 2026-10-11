"""[partner-roles 2026-10-11] WHO SHOULD LEAD WHAT between two people building something together — deterministic, explainable.

Not an LLM guess: each person is scored on six work lanes from the chart, the two are compared lane by lane, and the read says who
leads, what to share and where NEITHER is built for it. Pure functions over chart_data + dashas; no network, no LLM.

Lanes (v1) and what feeds them
  tech        Mercury, Rahu (systems, technology), Ketu (deep specialist craft), Mars (engineering)      houses 3, 5, 6
  ops         Saturn (process, staying power), Mars (execution), Mercury (detail)                        houses 6, 10, 3
  sales       Mercury (deals, speech), Venus (relationships), Jupiter                                    houses 2, 3, 7   (owner: communication / clients)
  vision      Sun (direction, authority), Jupiter (judgement), Rahu (ambition)                           houses 1, 9, 10
  finance     Jupiter, Saturn, Mercury (accounts), Venus (money)                                         houses 2, 11
  creative    Venus, Moon, Mercury                                                                      houses 4, 5

Score of one lane for one person, 0..1:  0.30 D-1  +  0.30 D-10  +  0.25 Jaimini  +  0.15 dasha
  D-1      planets that carry the lane (dignity x house strength) and the lords / occupants of the lane's houses (Parashari)
  D-10     the same read on the career chart — what the person is built to DO
  Jaimini  Amatyakaraka (career karaka) 0.15 + Atmakaraka (the drive they will not give up) 0.10 — the planet's own lane votes x its strength;
           the karakas are the STORED ones (charts.jaimini_data.karakas), not recomputed
  dasha    what is switched on NOW (timing, not nature): Vimshottari Mahadasha 0.06 + Antardasha 0.04 lords' lane votes, plus the running
           CHARA (Jaimini) Antardasha sign 0.05 — the sign's lord and the planets in it vote their lanes, and when the Amatyakaraka sits in
           1 / 5 / 9 / 10 / 11 FROM that dasha sign (the rotated chart) the career karaka is "live" and its lanes get a lift

Dignity: exalted 1.0 / own 0.85 / debilitated 0.2 / otherwise 0.55.  House: kendra+trikona 1.0, 3/6/11 0.9, 2 0.75, 8/12 0.45.
CONVERGENCE: the two systems are scored separately — PARASHARI (D-1 + D-10 + Vimshottari: 0.30 / 0.30 / 0.10 of the 1.0) and JAIMINI
(Amatyakaraka + Atmakaraka + Chara dasha: 0.25 / 0.05) — and a lane has a LEADER only when both systems put the same person ahead. When they
split, the lane is CONTESTED: shown as open, never as a confident lead. Same rule for the partnership gate (7th house vs the Darakaraka).
Two people within 0.06 of each other in a lane SHARE it; a lane where both are under 0.45 is a GAP (hire / outsource for it).
v1 weights are a starting point to refine against real partnerships — the module's job is that the answer is stable and the reasons are named."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from antar_engine.d10_career import SIGN_LORD, SIGNS, _EXALT, _OWN, _DEBIL, _amatyakaraka

LANES = ("tech", "ops", "sales", "vision", "finance", "creative")

LANE_PLANETS: Dict[str, Dict[str, float]] = {
    "tech":     {"Mercury": 1.0, "Rahu": 0.9, "Ketu": 0.5, "Mars": 0.4},
    "ops":      {"Saturn": 1.0, "Mars": 0.9, "Mercury": 0.3},
    "sales":    {"Mercury": 0.8, "Venus": 0.6, "Jupiter": 0.2},
    "vision":   {"Sun": 1.0, "Jupiter": 0.8, "Rahu": 0.2},
    "finance":  {"Jupiter": 0.9, "Saturn": 0.6, "Mercury": 0.5, "Venus": 0.4},
    "creative": {"Venus": 1.0, "Moon": 0.7, "Mercury": 0.3},
}
LANE_HOUSES: Dict[str, tuple] = {
    "tech": (3, 5, 6), "ops": (6, 10, 3), "sales": (2, 3, 7), "vision": (1, 9, 10), "finance": (2, 11), "creative": (4, 5),
}
W_D1, W_D10, W_JAI, W_DASHA = 0.30, 0.30, 0.25, 0.15
W_AMK, W_AK = 0.15, 0.10
W_MD, W_AD, W_CAD = 0.06, 0.04, 0.05
AMK_LIVE_HOUSES = (1, 5, 9, 10, 11)
SHARE_BAND, GAP_BELOW = 0.06, 0.45

_HOUSE_FACTOR = {1: 1.0, 4: 1.0, 5: 1.0, 7: 1.0, 9: 1.0, 10: 1.0, 3: 0.9, 6: 0.9, 11: 0.9, 2: 0.75, 8: 0.45, 12: 0.45}
_RAHU_KETU = ("Rahu", "Ketu")

_NAME = {
    "en": {"tech": "technology & product", "ops": "operations & execution", "sales": "sales & clients",
           "vision": "vision & leadership", "finance": "finance", "creative": "creative & brand"},
    "es": {"tech": "tecnolog\u00eda / producto", "ops": "operaciones / ejecuci\u00f3n", "sales": "ventas / clientes",
           "vision": "visi\u00f3n / liderazgo", "finance": "finanzas", "creative": "creatividad / marca"},
}
_PLANET_ES = {"Sun": "el Sol", "Moon": "la Luna", "Mars": "Marte", "Mercury": "Mercurio", "Jupiter": "Júpiter", "Venus": "Venus",
              "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"}

_TX = {
    "en": {
        "title": "How to work with {b}",
        "nature": "{who} {is_} strongest in {lanes}.",
        "you": "You", "is_you_n": "are", "is_other_n": "is", "lead": "{who} should lead {lanes}", "basis": " ({basis})",
        "lead_join": "; ", "lead_h": "Who should lead what: ",
        "share": "Share {lanes}: you are close enough that neither should own it alone.",
        "gap": "Neither of you is built for {lanes}. Hire, partner or outsource it rather than assume one of you will absorb it.",
        "now": "Right now {who} {is_} in {md}–{ad}{chara}, which switches on {lanes}.", "chara": " (and the {sign} Chara period)",
        "is_you": "are", "is_other": "is", "cap_is_you": "are", "cap_is_other": "is", "partial": "Timing for {who} is not on file, so the read for {who} rests on the chart alone.",
        "fact": "{planet} in {sign}, house {h}", "fact_d10": "{planet} in D10 house {h}",
        "ak": "{planet} as the soul planet", "amk": "{planet} as the career planet",
        "close": "This is the chart's read of nature and timing; roles still need to be agreed in writing.",
        "cap_solo": "{who} {is_} built to run things alone: the 7th house (partners and contracts) does not read as supportive in the birth chart and the career chart ({basis}). A co-founder split rarely holds. Work together on narrow, written terms such as advisor, investor or contractor.",
        "cap_cond": "{who} can partner, but only with clear written terms: the 7th house reads mixed ({basis}).", "cap_split": "{who} can partner, but the two systems point different ways: the 7th house and the Darakaraka (the partner planet) disagree. Agree the terms in writing before building together ({basis}).",
        "cap_ok": "Both of you can partner: the 7th house reads supportive in the birth chart and the career chart.",
        "cap_basis": "birth chart: {l1} rules the 7th, in house {h1}{o1}; career chart: {l10} rules the 7th, in house {h10}{o10}",
        "occ": ", with {occ}", "contested": "The two systems split on {lanes}: Parashari (the birth and career charts) and Jaimini (the karakas and Chara period) put different people ahead. Treat it as open and decide it together rather than assign it.", "agree": "Both systems agree on the leads above (Parashari with Vimshottari, Jaimini with Chara).", "cap_after_solo": "Read the split below as who should own what inside a defined scope, not as a co-founder arrangement.",
    },
    "es": {
        "title": "Cómo trabajar con {b}",
        "nature": "{who} {is_} más fuerte en {lanes}.",
        "you": "Tú", "is_you_n": "eres", "is_other_n": "es", "lead": "{who} debería liderar {lanes}", "basis": " ({basis})",
        "lead_join": "; ", "lead_h": "Quién debería liderar qué: ",
        "share": "Compartan {lanes}: están tan cerca que ninguno debería ser dueño único.",
        "gap": "Ninguno de los dos está hecho para {lanes}. Contraten, asóciense o externalicen en lugar de suponer que uno lo absorberá.",
        "now": "Ahora mismo {who} {is_} en {md}–{ad}{chara}, lo que activa {lanes}.", "chara": " (y el periodo Chara de {sign})",
        "is_you": "estás", "is_other": "está", "cap_is_you": "rindes", "cap_is_other": "rinde",
        "partial": "Los tiempos de {who} no están disponibles, así que su lectura se basa solo en la carta.",
        "fact": "{planet} en {sign}, casa {h}", "fact_d10": "{planet} en la casa {h} del D10",
        "ak": "{planet} como planeta del alma", "amk": "{planet} como planeta de la carrera",
        "close": "Es la lectura de la carta sobre naturaleza y tiempos; los roles aún deben acordarse por escrito.",
        "cap_solo": "{who} {is_} mejor en solitario: la casa 7 (socios y contratos) no se lee favorable en la carta natal ni en la de carrera ({basis}). Un reparto de cofundadores rara vez se sostiene. Trabajen con términos acotados y por escrito, como asesor, inversionista o contratista.",
        "cap_cond": "{who} puede asociarse, pero solo con términos claros por escrito: la casa 7 se lee mixta ({basis}).", "cap_split": "{who} puede asociarse, pero los dos sistemas apuntan en direcciones distintas: la casa 7 y el Darakaraka (el planeta de la pareja o socio) no coinciden. Acuerden los términos por escrito antes de construir juntos ({basis}).",
        "cap_ok": "Los dos pueden asociarse: la casa 7 se lee favorable en la carta natal y en la de carrera.",
        "cap_basis": "carta natal: {l1} rige la casa 7, en la casa {h1}{o1}; carta de carrera: {l10} rige la casa 7, en la casa {h10}{o10}",
        "occ": ", con {occ}", "contested": "Los dos sistemas se dividen en {lanes}: Parashari (carta natal y de carrera) y Jaimini (karakas y periodo Chara) ponen adelante a personas distintas. Trátenlo como abierto y decídanlo juntos en lugar de asignarlo.", "agree": "Los dos sistemas coinciden en los liderazgos de arriba (Parashari con Vimshottari, Jaimini con Chara).", "cap_after_solo": "Lean el reparto de abajo como quién responde de qué dentro de un alcance definido, no como un acuerdo de cofundadores.",
    },
}
_SIGN_ES = {"Aries": "Aries", "Taurus": "Tauro", "Gemini": "Géminis", "Cancer": "Cáncer", "Leo": "Leo", "Virgo": "Virgo",
            "Libra": "Libra", "Scorpio": "Escorpio", "Sagittarius": "Sagitario", "Capricorn": "Capricornio",
            "Aquarius": "Acuario", "Pisces": "Piscis"}


# ── strength ────────────────────────────────────────────────────────────────
def _dig(planet: str, sign: str) -> float:
    if planet in _RAHU_KETU:
        return 0.55
    if _EXALT.get(planet) == sign:
        return 1.0
    if sign in _OWN.get(planet, set()):
        return 0.85
    if _DEBIL.get(planet) == sign:
        return 0.2
    return 0.55


def _strength(planet: str, sign: str, house) -> float:
    try:
        return _dig(planet, sign) * _HOUSE_FACTOR.get(int(house), 0.7)
    except (TypeError, ValueError):
        return _dig(planet, sign) * 0.7


def _lagna_sign(chart: dict) -> Optional[str]:
    lg = (chart or {}).get("lagna")
    sg = lg.get("sign") if isinstance(lg, dict) else lg
    return sg if sg in SIGNS else None


def _d10(chart: dict) -> dict:
    d = ((chart or {}).get("divisional_charts") or {}).get("d10") or {}
    lg = d.get("lagna")
    lg = lg.get("sign") if isinstance(lg, dict) else lg
    return {"lagna": lg if lg in SIGNS else None, "planets": d.get("planets") or {}}


def _sign_of_house(lagna: str, h: int) -> str:
    return SIGNS[(SIGNS.index(lagna) + h - 1) % 12]


def _house_read(planets: dict, lagna: Optional[str], houses: tuple) -> float:
    """Parashari: how strong the lords (and occupants) of the lane's houses are, 0..1, from the given chart's own placements."""
    if not lagna or not planets:
        return 0.0
    vals = []
    for h in houses:
        lord = SIGN_LORD[_sign_of_house(lagna, h)]
        pl = planets.get(lord) or {}
        if pl.get("sign"):
            vals.append(_strength(lord, pl["sign"], pl.get("house")))
        for p, v in planets.items():
            if v.get("house") == h and v.get("sign") and p not in _RAHU_KETU:
                vals.append(_strength(p, v["sign"], h) * 0.8)
    return sum(vals) / len(vals) if vals else 0.0


def _planet_read(planets: dict, lane: str) -> float:
    w = LANE_PLANETS[lane]
    num = den = 0.0
    for p, wt in w.items():
        pl = planets.get(p) or {}
        if pl.get("sign"):
            num += wt * _strength(p, pl["sign"], pl.get("house"))
        den += wt
    return num / den if den else 0.0


def _chart_read(planets: dict, lagna: Optional[str], lane: str) -> float:
    return 0.5 * _planet_read(planets, lane) + 0.5 * _house_read(planets, lagna, LANE_HOUSES[lane])


def _stored_karakas(chart: dict, jaimini: Optional[dict]) -> dict:
    """{AK, AmK, DK ...: planet} from charts.jaimini_data.karakas (the ones the platform already generates); else computed from degrees."""
    out = {}
    try:
        for k in ((jaimini or {}).get("karakas") or []):
            if isinstance(k, dict) and k.get("karaka") and k.get("planet"):
                out[k["karaka"]] = k["planet"]
    except Exception:
        out = {}
    planets = (chart or {}).get("planets") or {}
    if "AmK" not in out:
        a = _amatyakaraka(planets)
        if a:
            out["AmK"] = a
    if "AK" not in out:
        a = (chart or {}).get("atmakaraka")
        a = a.get("planet") if isinstance(a, dict) else a
        if a:
            out["AK"] = a
    if "DK" not in out:
        try:
            from antar_engine.compatibility_session_engine import _get_darakaraka
            d = _get_darakaraka(planets)
            if d:
                out["DK"] = d
        except Exception:
            pass
    return out


def _stored_window_covers(rec: Optional[dict], now: datetime) -> Optional[str]:
    """The sign of a stored jaimini_data.current_md / current_ad snapshot, but ONLY while its own dates still cover today."""
    try:
        if not isinstance(rec, dict) or rec.get("sign_name") not in SIGNS:
            return None
        sd = datetime.strptime(str(rec.get("start"))[:10], "%Y-%m-%d")
        ed = datetime.strptime(str(rec.get("end"))[:10], "%Y-%m-%d")
        return rec["sign_name"] if sd <= now <= ed else None
    except Exception:
        return None


def chara_running(dashas: dict, today: Optional[datetime] = None, jaimini: Optional[dict] = None) -> tuple:
    """(Chara Mahadasha sign, Chara Antardasha sign) running today. Live rows from dashas['jaimini'] first; the platform stores only
    the Mahadasha rows, so the Antardasha comes from the stored jaimini_data snapshot while ITS dates cover today (never a stale one)."""
    now = today or datetime.utcnow()
    md = ad = ""
    for row in ((dashas or {}).get("jaimini") or []):
        level = str(row.get("level") or row.get("type") or "").lower()
        try:
            sd = datetime.strptime(str(row.get("start_date") or row.get("start"))[:10], "%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date") or row.get("end"))[:10], "%Y-%m-%d")
        except Exception:
            continue
        if sd <= now <= ed:
            sg = row.get("lord_or_sign") or row.get("planet_or_sign") or ""
            if sg not in SIGNS:
                continue
            if level.startswith("maha") and not md:
                md = sg
            elif level.startswith("antar") and not ad:
                ad = sg
    md = md or (_stored_window_covers((jaimini or {}).get("current_md"), now) or "")
    ad = ad or (_stored_window_covers((jaimini or {}).get("current_ad"), now) or "")
    return md, ad


def _chara_lane(chart: dict, ad_sign: str, amk: Optional[str], lane: str) -> float:
    """0..1: the running Chara AD sign's lord + the planets sitting in it vote the lane; the AmK 'live' from that sign lifts its lanes."""
    if ad_sign not in SIGNS:
        return 0.0
    w = LANE_PLANETS[lane]
    planets = (chart or {}).get("planets") or {}
    votes = [w.get(SIGN_LORD[ad_sign], 0.0)]
    votes += [w.get(p, 0.0) for p, v in planets.items() if v.get("sign") == ad_sign]
    base = max(votes) if votes else 0.0
    bonus = 0.0
    if amk and (planets.get(amk) or {}).get("sign") in SIGNS:
        house_from_dasha = (SIGNS.index(planets[amk]["sign"]) - SIGNS.index(ad_sign)) % 12 + 1
        if house_from_dasha in AMK_LIVE_HOUSES:
            bonus = 0.5 * w.get(amk, 0.0)
    return min(1.0, base + bonus)


def _ak(chart: dict) -> Optional[str]:
    a = (chart or {}).get("atmakaraka")
    a = a.get("planet") if isinstance(a, dict) else a
    return a if a in {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"} else None


def _karaka_lane(chart: dict, planet: Optional[str], lane: str) -> float:
    if not planet:
        return 0.0
    wt = LANE_PLANETS[lane].get(planet, 0.0)
    if not wt:
        return 0.0
    pl = (chart.get("planets") or {}).get(planet) or {}
    d10pl = (_d10(chart)["planets"]).get(planet) or {}
    s1 = _strength(planet, pl.get("sign", ""), pl.get("house")) if pl.get("sign") else 0.5
    s10 = _strength(planet, d10pl.get("sign", ""), d10pl.get("house")) if d10pl.get("sign") else s1
    return wt * (s1 + s10) / 2



# ── GATE: can this person be a partner / co-founder at all? ────────────────────────────────────────────────
# Owner rule: before who-leads-what, check each person's 7th house (partners, contracts) in D-1 AND D-10 — someone built to run
# everything alone (the Ambani / Musk / Jobs pattern) is not a co-founder however well the lanes split.
_BENEFIC_7 = {"Jupiter": 0.14, "Venus": 0.12, "Mercury": 0.08, "Moon": 0.06}
_MALEFIC_7 = {"Saturn": -0.12, "Mars": -0.14, "Rahu": -0.14, "Ketu": -0.10, "Sun": -0.12}
CAP_CAPABLE, CAP_SOLO = 0.55, 0.42


def _seventh(planets: dict, lagna: Optional[str]) -> Optional[dict]:
    """0..1 reading of ONE chart's 7th house: its lord (dignity x house, a dusthana lord is weak) and its occupants."""
    if not lagna or not planets:
        return None
    sign7 = _sign_of_house(lagna, 7)
    lord = SIGN_LORD[sign7]
    lp = planets.get(lord) or {}
    lord_s = _strength(lord, lp["sign"], lp.get("house")) if lp.get("sign") else 0.45
    occ = [(p, v) for p, v in planets.items() if v.get("house") == 7 and p in {**_BENEFIC_7, **_MALEFIC_7}]
    delta = sum({**_BENEFIC_7, **_MALEFIC_7}[p] * (0.6 + 0.4 * (_dig(p, v.get("sign", "")))) for p, v in occ)
    score = max(0.0, min(1.0, 0.6 * lord_s + 0.4 * 0.55 + delta))
    return {"score": round(score, 3), "lord": lord, "lord_house": lp.get("house"), "lord_sign": lp.get("sign"),
            "occupants": [p for p, _ in occ]}


def partnership_capacity(chart: dict, jaimini: Optional[dict] = None) -> dict:
    """{score 0..1, level: capable | conditional | solo, d1, d10, dk, facts}. Never raises."""
    try:
        planets = (chart or {}).get("planets") or {}
        d1 = _seventh(planets, _lagna_sign(chart))
        d10c = _d10(chart)
        d10 = _seventh(d10c["planets"], d10c["lagna"]) if d10c["planets"] else None
        parts = [x["score"] for x in (d1, d10) if x]
        if not parts:
            return {"score": None, "level": "unknown", "d1": None, "d10": None, "dk": None}
        score = sum(parts) / len(parts)
        dk = _stored_karakas(chart or {}, jaimini).get("DK")
        score = round(max(0.0, min(1.0, score)), 3)
        level = "capable" if score >= CAP_CAPABLE else "solo" if score < CAP_SOLO else "conditional"
        # JAIMINI reads the same question through the Darakaraka (the partner significator): its strength in D-1 and D-10.
        # The two systems should give the same answer; when one says capable and the other solo it is CONDITIONAL, said as a split.
        jlevel, contested = None, False
        d10pl = d10c["planets"]
        if dk in planets and planets[dk].get("sign"):
            s1 = _strength(dk, planets[dk]["sign"], planets[dk].get("house"))
            s10 = _strength(dk, d10pl[dk]["sign"], d10pl[dk].get("house")) if (dk in d10pl and d10pl[dk].get("sign")) else s1
            dks = (s1 + s10) / 2
            jlevel = "capable" if dks >= 0.60 else "solo" if dks < 0.35 else "conditional"
            if {level, jlevel} == {"capable", "solo"}:
                level, contested = "conditional", True
        return {"score": score, "level": level, "d1": d1, "d10": d10, "dk": dk, "jaimini_level": jlevel, "contested": contested}
    except Exception:
        return {"score": None, "level": "unknown", "d1": None, "d10": None, "dk": None}


def running_lords(dashas: dict, today: Optional[datetime] = None) -> tuple:
    """(Mahadasha lord, Antardasha lord) running today, '' when unknown."""
    now = today or datetime.utcnow()
    md = ad = ""
    for row in ((dashas or {}).get("vimsottari") or []):
        level = str(row.get("level") or row.get("type") or "").lower()
        try:
            sd = datetime.strptime(str(row.get("start_date") or row.get("start"))[:10], "%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date") or row.get("end"))[:10], "%Y-%m-%d")
        except Exception:
            continue
        if sd <= now <= ed:
            lord = row.get("lord_or_sign") or row.get("planet_or_sign") or ""
            if level.startswith("maha") and not md:
                md = lord
            elif level.startswith("antar") and not ad:
                ad = lord
    return md, ad


def _dasha_lane(md: str, ad: str, lane: str, chara: float = 0.0, chara_on: bool = False) -> float:
    w = LANE_PLANETS[lane]
    num = W_MD * w.get(md, 0.0) + W_AD * w.get(ad, 0.0) + (W_CAD * chara if chara_on else 0.0)
    den = (W_MD + W_AD if (md or ad) else 0.0) + (W_CAD if chara_on else 0.0)
    return num / den if den else 0.0


def score_person(chart: dict, dashas: dict, today: Optional[datetime] = None, jaimini: Optional[dict] = None) -> dict:
    """{lane: score 0..1, 'parts': {...}} for one person. Never raises; missing data lowers a part to 0 rather than failing."""
    chart = chart or {}
    planets = chart.get("planets") or {}
    lag = _lagna_sign(chart)
    d10 = _d10(chart)
    kar = _stored_karakas(chart, jaimini)
    amk, ak = kar.get("AmK"), kar.get("AK")
    md, ad = running_lords(dashas, today)
    c_md, c_ad_only = chara_running(dashas, today, jaimini)
    c_ad = c_ad_only or c_md          # no Antardasha available: the Mahadasha sign is the running Chara period
    out: Dict[str, float] = {}
    parts: Dict[str, dict] = {}
    psys: Dict[str, Optional[float]] = {}
    jsys: Dict[str, Optional[float]] = {}
    have = {"d1": bool(planets), "d10": bool(d10["planets"]), "jaimini": bool(amk or ak), "dasha": bool(md or c_ad)}
    wts = {"d1": W_D1, "d10": W_D10, "jaimini": W_JAI, "dasha": W_DASHA}
    tot = sum(w for k, w in wts.items() if have[k]) or 1.0     # a part with no data is LEFT OUT, never scored as 0 (weakness)
    for lane in LANES:
        d1 = _chart_read(planets, lag, lane)
        d10s = _chart_read(d10["planets"], d10["lagna"], lane) if have["d10"] else 0.0
        jai = (W_AMK * _karaka_lane(chart, amk, lane) + W_AK * _karaka_lane(chart, ak, lane)) / (W_AMK + W_AK) if have["jaimini"] else 0.0
        das = _dasha_lane(md, ad, lane, _chara_lane(chart, c_ad, amk, lane), bool(c_ad)) if have["dasha"] else 0.0
        out[lane] = round((W_D1 * d1 * have["d1"] + W_D10 * d10s * have["d10"] + W_JAI * jai * have["jaimini"] + W_DASHA * das * have["dasha"]) / tot, 4)
        parts[lane] = {"d1": round(d1, 3), "d10": round(d10s, 3), "jaimini": round(jai, 3), "dasha": round(das, 3)}
        # the same lane read by each SYSTEM alone (dasha: Vimshottari -> Parashari, Chara -> Jaimini)
        vim = _dasha_lane(md, ad, lane) if (md or ad) else 0.0
        cha = _chara_lane(chart, c_ad, amk, lane) if c_ad else 0.0
        pw = {"d1": W_D1 * have["d1"], "d10": W_D10 * have["d10"], "vim": (W_MD + W_AD) * bool(md or ad)}
        jw = {"jai": W_JAI * have["jaimini"], "cha": W_CAD * bool(c_ad)}
        pden, jden = sum(pw.values()), sum(jw.values())
        psys[lane] = round((pw["d1"] * d1 + pw["d10"] * d10s + pw["vim"] * vim) / pden, 4) if pden else None
        jsys[lane] = round((jw["jai"] * jai + jw["cha"] * cha) / jden, 4) if jden else None
    return {"scores": out, "parashari": psys, "jaimini": jsys, "parts": parts, "amk": amk, "ak": ak, "dk": kar.get("DK"), "md": md, "ad": ad, "chara_md": c_md, "chara_ad": c_ad, "have": have}


def _top_fact(chart: dict, lane: str, lang: str) -> str:
    """The single placement that most supports this person in this lane, in words."""
    tx = _TX[lang]
    planets = chart.get("planets") or {}
    d10pl = _d10(chart)["planets"]
    best, best_s, kind = None, -1.0, "d1"
    for p, wt in LANE_PLANETS[lane].items():
        for src, pls in (("d1", planets), ("d10", d10pl)):
            pl = pls.get(p) or {}
            if pl.get("sign"):
                s = wt * _strength(p, pl["sign"], pl.get("house"))
                if s > best_s:
                    best, best_s, kind = (p, pl), s, src
    if not best:
        return ""
    p, pl = best
    nm = p if lang == "en" else _PLANET_ES.get(p, p)
    sg = pl.get("sign", "") if lang == "en" else _SIGN_ES.get(pl.get("sign", ""), pl.get("sign", ""))
    return (tx["fact_d10"] if kind == "d10" else tx["fact"]).format(planet=nm, sign=sg, h=pl.get("house", "?"))


def _cap_basis(cap: dict, lang: str) -> str:
    tx = _TX[lang]
    d1, d10 = cap.get("d1") or {}, cap.get("d10") or {}
    pn = (lambda x: x) if lang == "en" else (lambda x: _PLANET_ES.get(x, x))
    oc = lambda d: (tx["occ"].format(occ=", ".join(pn(o) for o in d["occupants"])) if d.get("occupants") else "")
    if not d1 or not d10:
        return ""
    return tx["cap_basis"].format(l1=pn(d1["lord"]), h1=d1.get("lord_house", "?"), o1=oc(d1),
                                  l10=pn(d10["lord"]), h10=d10.get("lord_house", "?"), o10=oc(d10))


def compare(chart_a: dict, dashas_a: dict, chart_b: dict, dashas_b: dict, name_b: str = "", lang: str = "en",
            today: Optional[datetime] = None, jaimini_a: Optional[dict] = None, jaimini_b: Optional[dict] = None) -> Optional[dict]:
    """The who-leads-what read for A (the reader, "you") and B. None when either chart has no usable planets."""
    try:
        lang = lang if lang in _TX else "en"
        if not ((chart_a or {}).get("planets") and (chart_b or {}).get("planets")):
            return None
        a, b = score_person(chart_a, dashas_a, today, jaimini_a), score_person(chart_b, dashas_b, today, jaimini_b)
        tx, nm = _TX[lang], _NAME[lang]
        # a GAP is a lane that is in the bottom half of BOTH people's own ranking — neither is built for it (judged against each
        # person's other lanes, not against the pair's single best lane, which would hide a real lead)
        low = lambda sc: set(sorted(LANES, key=lambda l: sc["scores"][l])[:3])
        both_low = low(a) & low(b)
        leads_a, leads_b, shared, gap_c, contested = [], [], [], [], []

        def _side(lane, sysname):
            """+1 A ahead / -1 B ahead / 0 level (within the share band) / None when a system has no data for either person."""
            xa, xb = a[sysname].get(lane), b[sysname].get(lane)
            if xa is None or xb is None:
                return None
            d = xa - xb
            return 0 if abs(d) < SHARE_BAND else (1 if d > 0 else -1)
        for lane in LANES:
            sa, sb = a["scores"][lane], b["scores"][lane]
            if lane in both_low:
                gap_c.append((max(sa, sb), lane))
                continue
            ps, js = _side(lane, "parashari"), _side(lane, "jaimini")
            if ps is not None and js is not None and ps * js < 0:
                contested.append(lane)               # one system puts A ahead, the other B: an open lane, not a lead
            elif abs(sa - sb) < SHARE_BAND:
                shared.append(lane)
            elif sa > sb:
                leads_a.append((lane, sa - sb))
            else:
                leads_b.append((lane, sb - sa))
        gaps = [l for _, l in sorted(gap_c)[:2]]          # the two weakest at most
        leads_a.sort(key=lambda x: -x[1])
        leads_b.sort(key=lambda x: -x[1])
        nat = lambda sc: [l for l, _ in sorted(sc["scores"].items(), key=lambda kv: -kv[1])[:2]]
        join = lambda xs: (", ".join(xs[:-1]) + (" y " if lang == "es" else " and ") + xs[-1]) if len(xs) > 1 else "".join(xs)
        lanes_txt = lambda ls: join([nm[l] for l in ls])
        name_b = (name_b or "").strip() or ("la otra persona" if lang == "es" else "the other person")
        you = tx["you"]

        cap_a, cap_b = partnership_capacity(chart_a, jaimini_a), partnership_capacity(chart_b, jaimini_b)
        lines = [tx["title"].format(b=name_b), ""]
        solo = False
        caps = []
        for who, cap, is_ in ((you, cap_a, tx["cap_is_you"]), (name_b, cap_b, tx["cap_is_other"])):
            if cap["level"] == "solo":
                solo = True
                caps.append(tx["cap_solo"].format(who=who, is_=is_, basis=_cap_basis(cap, lang)))
            elif cap["level"] == "conditional":
                caps.append(tx["cap_split" if cap.get("contested") else "cap_cond"].format(who=who, basis=_cap_basis(cap, lang)))
        if not caps and cap_a["level"] == "capable" and cap_b["level"] == "capable":
            caps.append(tx["cap_ok"])
        lines += caps + ([tx["cap_after_solo"]] if solo else []) + ([""] if caps else [])
        lines.append(tx["nature"].format(who=you, is_=tx["is_you_n"], lanes=lanes_txt(nat(a))) + " "
                     + tx["nature"].format(who=name_b, is_=tx["is_other_n"], lanes=lanes_txt(nat(b))))
        lead_bits = []
        for who, chart, ls in ((you, chart_a, leads_a), (name_b, chart_b, leads_b)):
            if not ls:
                continue
            top = [l for l, _ in ls[:3]]
            facts = []
            for l in top:
                f = _top_fact(chart, l, lang)
                if f and f not in facts:
                    facts.append(f)
            lead_bits.append(tx["lead"].format(who=who, lanes=lanes_txt(top)) + (tx["basis"].format(basis="; ".join(facts[:2])) if facts else ""))
        if lead_bits:
            lines.append(tx["lead_h"] + tx["lead_join"].join(lead_bits) + ".")
        if shared:
            lines.append(tx["share"].format(lanes=lanes_txt(shared)))
        if contested:
            lines.append(tx["contested"].format(lanes=lanes_txt(contested)))
        elif lead_bits and a["have"]["jaimini"] and b["have"]["jaimini"]:
            lines.append(tx["agree"])
        if gaps:
            lines.append(tx["gap"].format(lanes=lanes_txt(gaps)))
        for who, is_, sc in ((you, tx["is_you"], a), (name_b, tx["is_other"], b)):
            if sc["md"] or sc.get("chara_ad"):
                pn = (lambda x: x) if lang == "en" else (lambda x: _PLANET_ES.get(x, x))
                top = [l for l, v in sorted(sc["parts"].items(), key=lambda kv: -kv[1]["dasha"]) if sc["parts"][l]["dasha"] > 0][:2]
                if top:
                    ch = (tx["chara"].format(sign=sc["chara_ad"] if lang == "en" else _SIGN_ES.get(sc["chara_ad"], sc["chara_ad"])) if sc.get("chara_ad") else "")
                    lines.append(tx["now"].format(who=who, is_=is_, md=pn(sc["md"]), ad=pn(sc["ad"] or sc["md"]), chara=ch, lanes=lanes_txt(top)))
        for who, sc in ((you, a), (name_b, b)):
            if not sc["have"]["dasha"]:
                lines.append(tx["partial"].format(who=who))
        lines.append(tx["close"])
        return {
            "version": "partner-roles-1", "language": lang,
            "weights": {"d1": W_D1, "d10": W_D10, "jaimini": W_JAI, "dasha": W_DASHA, "amk": W_AMK, "ak": W_AK, "vim_md": W_MD, "vim_ad": W_AD, "chara_ad": W_CAD},
            "you": {"scores": a["scores"], "leads": [l for l, _ in leads_a], "amk": a["amk"], "ak": a["ak"], "dk": a["dk"], "md": a["md"], "ad": a["ad"], "chara_ad": a["chara_ad"]},
            "other": {"scores": b["scores"], "leads": [l for l, _ in leads_b], "amk": b["amk"], "ak": b["ak"], "dk": b["dk"], "md": b["md"], "ad": b["ad"], "chara_ad": b["chara_ad"]},
            "capacity": {"you": {k: cap_a[k] for k in ("score", "level")}, "other": {k: cap_b[k] for k in ("score", "level")},
                         "solo": solo},
            "shared": shared, "gaps": gaps, "contested": contested, "partial": [k for k, sc in (("you", a), ("other", b)) if not all(sc["have"].values())],
            "text": "\n".join(lines),
        }
    except Exception as e:                       # never break the page — but never fail silently either
        print(f"[partner-roles] compare failed: {type(e).__name__}: {e}")
        return None
