"""
antar_engine/event_convergence.py
=================================
Event Engine Rebuild — Rao three-stage + Jaimini Padhati convergence
(Cowork brief 2026-06-10).

Replaces the flat per-lagna priority selection in dasha_event_mapper with the
documented convergence method. An event surfaces only where independent
systems agree on the same window:

  Stage 1  PROMISE      — per-chart placement read (house + lord + karaka +
                          divisional echo + placement-scored nodes).
                          No promise -> never predicted.
  Stage 2a BROAD TIMING — Vimsottari MD→AD→PD scan, sub-periods whose lord is
                          a Stage-1 significator. MD=era, AD=year, PD≈3 months.
  Stage 2b BROAD TIMING — Jaimini Chara dasha vote (UL/AL/DK/PK/AmK/MK/
                          Karakamsa conditions, Rashi Drishti, per the
                          project's jaimini_engine).
  Stage 3  TRIGGER      — K.N. Rao double transit (transit_engine layer):
                          among Stage-2 candidates, an event fires only where
                          transiting Jupiter AND Saturn both influence the
                          event house / its lord (+ D9 lord for marriage/
                          children; Lagna AND Moon reference frames).
  Stage 4  PRUNE        — life-stage age priors (event_engine_config, soft)
                          + confirmed-event pruning + class-gated convergence:
                          confidence = count of agreeing systems (0-3);
                          benign needs >=2/3, painful needs 3/3. Never pad.

Doctrine: Python computes, Claude narrates. Everything here is deterministic.
The _debug_reasoning lock trace is ADMIN-ONLY (full jargon, never stripped);
anything user-facing goes through the existing narration contract layers.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

# ── canonical vocab ──────────────────────────────────────────────────────────
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
              "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_INDEX = {s: i for i, s in enumerate(SIGN_NAMES)}
SIGN_RULER_IDX = {0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun",
                  5: "Mercury", 6: "Venus", 7: "Mars", 8: "Jupiter",
                  9: "Saturn", 10: "Saturn", 11: "Jupiter"}
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# Painful events require FULL 3/3 convergence (kills the fabricated-divorce
# class of error); everything else needs >=2 of 3.
PAINFUL_EVENTS = {
    "serious_partnership_ended", "professional_setback", "legal_entanglement",
    "financial_disruption", "loss_of_father", "loss_of_mother",
}
# Auspicious events: transiting Jupiter specifically must influence the
# event-house lord (Rao — "you do auspicious things under Jupiter").
AUSPICIOUS_EVENTS = {
    "serious_partnership_began", "family_expansion_first",
    "family_expansion_second",
}
# Events whose Stage-3 targets include the D9 sign of the event-house lord
# (Rao's navamsha research: marriage/children).
D9_TARGET_EVENTS = AUSPICIOUS_EVENTS

DEFAULT_PROMISE_FLOOR = 2.0


# ── shared helpers ───────────────────────────────────────────────────────────

def _safe_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _sign_idx(value) -> Optional[int]:
    """Accept sign name, index, or planet dict with sign/sign_index."""
    if value is None:
        return None
    if isinstance(value, int):
        return value % 12
    if isinstance(value, str):
        return SIGN_INDEX.get(value)
    if isinstance(value, dict):
        if value.get("sign_index") is not None:
            return int(value["sign_index"]) % 12
        return SIGN_INDEX.get(value.get("sign", ""))
    return None


def parashari_aspect_signs(planet: str, sign_idx: int) -> Set[int]:
    """Sign-level Parashari graha drishti: every planet aspects the 7th;
    Mars +4/8, Jupiter +5/9, Saturn +3/10 (1-indexed houses)."""
    extra = {"Mars": (3, 7), "Jupiter": (4, 8), "Saturn": (2, 9)}
    offsets = {6} | set(extra.get(planet, ()))
    return {(sign_idx + o) % 12 for o in offsets}


def _house_sign(lagna_idx: int, house: int) -> int:
    return (lagna_idx + house - 1) % 12


def _house_of_sign(lagna_idx: int, sign_idx: int) -> int:
    return ((sign_idx - lagna_idx) % 12) + 1


def _cfg_houses(cfg_row: Optional[dict], event_type: str) -> List[int]:
    raw = (cfg_row or {}).get("houses") or ""
    houses = []
    for tok in str(raw).split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= 12:
            houses.append(int(tok))
    if houses:
        return houses
    # ultra-fallback: 7 for partnership, 10 career, 4 home, 5 children, 12 foreign
    return {"serious_partnership_began": [7, 2, 5],
            "serious_partnership_ended": [7, 6, 8],
            "family_expansion_first": [5, 9],
            "family_expansion_second": [5, 9],
            "major_relocation": [12, 4, 9],
            "major_acquisition": [4, 2, 11],
            "career_pivot": [10, 6, 11],
            "business_start": [3, 7, 10, 11],
            "loss_of_father": [9, 8],
            "loss_of_mother": [4, 8],
            "professional_setback": [10, 6, 8],
            "legal_entanglement": [6, 8, 12],
            "financial_disruption": [2, 6, 8]}.get(event_type, [1])


# ── natal context (built once per chart) ─────────────────────────────────────

def build_natal_context(chart_data: dict) -> Optional[dict]:
    """
    Normalize chart_data into everything the stages need. Returns None when
    the chart lacks planets/lagna (caller stays silent — never fabricates).
    """
    cd = _safe_json(chart_data)
    planets = cd.get("planets") or {}
    lagna = cd.get("lagna") or {}
    lagna_idx = _sign_idx(lagna)
    if not planets or lagna_idx is None:
        return None

    moon_idx = _sign_idx(planets.get("Moon"))

    # Jaimini Planet objects (jaimini_engine dataclass)
    jaimini_planets = {}
    try:
        from antar_engine.jaimini_engine import Planet
        for name, p in planets.items():
            if not isinstance(p, dict):
                continue
            si = _sign_idx(p)
            if si is None:
                continue
            jaimini_planets[name] = Planet(
                name=name, sign=si,
                degree=float(p.get("longitude") or 0.0),
                degree_in_sign=float(p.get("degree") or 0.0),
                retrograde=bool(p.get("retrograde")),
                nakshatra=p.get("nakshatra") or "",
                nakshatra_lord=p.get("nakshatra_lord") or "",
            )
    except Exception:
        jaimini_planets = {}

    # D9 planets (sign-only is fine for karakamsa / D9 echo)
    d9_planets_idx: Dict[str, int] = {}
    d9_lagna_idx: Optional[int] = None
    d9 = (cd.get("divisional_charts") or {}).get("d9") or {}
    if isinstance(d9, dict):
        d9_lagna_idx = _sign_idx(d9.get("lagna"))
        for name, p in (d9.get("planets") or {}).items():
            si = _sign_idx(p)
            if si is not None:
                d9_planets_idx[name] = si

    d10 = (cd.get("divisional_charts") or {}).get("d10") or {}
    d10_planets_idx: Dict[str, int] = {}
    d10_lagna_idx: Optional[int] = None
    if isinstance(d10, dict):
        d10_lagna_idx = _sign_idx(d10.get("lagna"))
        for name, p in (d10.get("planets") or {}).items():
            si = _sign_idx(p)
            if si is not None:
                d10_planets_idx[name] = si

    def planet_sign(name: str) -> Optional[int]:
        return _sign_idx(planets.get(name))

    def house_lord(house: int) -> str:
        return SIGN_RULER_IDX[_house_sign(lagna_idx, house)]

    return {
        "planets": planets,
        "lagna_idx": lagna_idx,
        "moon_idx": moon_idx,
        "jaimini_planets": jaimini_planets,
        "d9_planets_idx": d9_planets_idx,
        "d9_lagna_idx": d9_lagna_idx,
        "d10_planets_idx": d10_planets_idx,
        "d10_lagna_idx": d10_lagna_idx,
        "planet_sign": planet_sign,
        "house_lord": house_lord,
    }


# ── Stage 1: PROMISE (placement-conditional, never a flat per-lagna list) ────

def stage1_promise(event_type: str, ctx: dict,
                   cfg_row: Optional[dict] = None) -> dict:
    """
    Is the event indicated in THIS chart, and how loudly?
    Returns {"indicated", "score", "factors", "significators",
             "houses", "primary_house", "lord", "lord_sign_idx",
             "d9_lord_sign_idx", "karaka"}.
    """
    houses = _cfg_houses(cfg_row, event_type)
    primary = houses[0]
    lagna_idx = ctx["lagna_idx"]
    planets = ctx["planets"]
    karaka = (cfg_row or {}).get("karaka") or ""

    primary_sign = _house_sign(lagna_idx, primary)
    lord = SIGN_RULER_IDX[primary_sign]
    lord_sign_idx = ctx["planet_sign"](lord)
    d9_lord_sign_idx = ctx["d9_planets_idx"].get(lord)

    score = 0.0
    factors: List[str] = []
    significators: Set[str] = set()

    # lords of every configured event house
    for h in houses:
        significators.add(SIGN_RULER_IDX[_house_sign(lagna_idx, h)])
    if karaka:
        significators.add(karaka)

    kendra_trikona = {1, 4, 5, 7, 9, 10}
    dusthana = {6, 8, 12}

    # 1. event-house lord placement
    if lord_sign_idx is not None:
        lord_house = _house_of_sign(lagna_idx, lord_sign_idx)
        if lord_house in houses:
            score += 1.5
            factors.append(f"{primary}H lord {lord} occupies event house {lord_house}")
        elif lord_house in kendra_trikona:
            score += 1.0
            factors.append(f"{primary}H lord {lord} in kendra/trikona ({lord_house}H)")
        elif lord_house in dusthana and event_type not in PAINFUL_EVENTS:
            score += 0.25
            factors.append(f"{primary}H lord {lord} in dusthana ({lord_house}H) — weak support")
        else:
            score += 0.5
            factors.append(f"{primary}H lord {lord} in {lord_house}H")

    # 2. occupants of the primary event house (+ aspects to it)
    occupants = []
    aspectors = []
    for name, p in planets.items():
        si = _sign_idx(p)
        if si is None:
            continue
        if si == primary_sign:
            occupants.append(name)
        elif name not in ("Rahu", "Ketu") and \
                primary_sign in parashari_aspect_signs(name, si):
            aspectors.append(name)
    for name in occupants[:2]:
        score += 1.0
        factors.append(f"{name} occupies the {primary}H")
        if name not in ("Rahu", "Ketu"):
            significators.add(name)
    if karaka and karaka in aspectors:
        score += 1.0
        factors.append(f"karaka {karaka} aspects the {primary}H")

    # 3. karaka placement
    k_sign = ctx["planet_sign"](karaka) if karaka else None
    if k_sign is not None:
        k_house = _house_of_sign(lagna_idx, k_sign)
        if k_house in houses:
            score += 1.5
            factors.append(f"karaka {karaka} occupies event house {k_house}")
        if lord_sign_idx is not None and k_sign == lord_sign_idx and karaka != lord:
            score += 1.0
            factors.append(f"karaka {karaka} conjunct {primary}H lord {lord}")

    # 4. nodes scored from PLACEMENT only (occupant-house + dispositor +
    #    nakshatra lord) — a flat node score is the Rishipal/relocation bug.
    for node in ("Rahu", "Ketu"):
        n = planets.get(node) or {}
        n_sign = _sign_idx(n)
        if n_sign is None:
            continue
        n_house = _house_of_sign(lagna_idx, n_sign)
        if n_house in houses:
            disp = SIGN_RULER_IDX[n_sign]
            nak_lord = (n.get("nakshatra_lord") or "") if isinstance(n, dict) else ""
            linked = disp in significators or nak_lord in significators
            if linked:
                score += 1.0
                factors.append(
                    f"{node} in event house {n_house}, dispositor {disp}"
                    f"{' / nak-lord ' + nak_lord if nak_lord else ''} ties to significators")
                significators.add(node)
            else:
                score += 0.25
                factors.append(f"{node} in event house {n_house} (unlinked dispositor {disp})")
        # foreign events: node anywhere with dispositor in 12/9/7 counts
        if event_type == "major_relocation" and node == "Rahu" and n_house not in houses:
            disp_sign = ctx["planet_sign"](SIGN_RULER_IDX[n_sign])
            if disp_sign is not None and \
                    _house_of_sign(lagna_idx, disp_sign) in (12, 9, 7):
                score += 0.5
                significators.add("Rahu")
                factors.append("Rahu dispositor in a foreign-axis house (12/9/7)")

    # 5. divisional echo — D9 for marriage/relationships, D10 for career
    if event_type in D9_TARGET_EVENTS or event_type == "serious_partnership_ended":
        d9_lagna = ctx["d9_lagna_idx"]
        if d9_lagna is not None and ctx["d9_planets_idx"]:
            d9_7th = (d9_lagna + 6) % 12
            d9_occ = [n for n, s in ctx["d9_planets_idx"].items() if s == d9_7th]
            if d9_occ:
                score += 0.75
                factors.append(f"D9 7th occupied by {','.join(d9_occ)}")
            if d9_lord_sign_idx is not None:
                d9_lord_house = ((d9_lord_sign_idx - d9_lagna) % 12) + 1
                if d9_lord_house in {1, 4, 5, 7, 9, 10}:
                    score += 0.75
                    factors.append(f"{primary}H lord strong in D9 ({d9_lord_house}H of navamsha)")
    if event_type in ("career_pivot", "professional_setback", "business_start"):
        d10_lagna = ctx["d10_lagna_idx"]
        if d10_lagna is not None and ctx["d10_planets_idx"]:
            lord10 = ctx["house_lord"](10)
            s10 = ctx["d10_planets_idx"].get(lord10)
            if s10 is not None and ((s10 - d10_lagna) % 12) + 1 in {1, 4, 5, 7, 9, 10}:
                score += 0.75
                factors.append(f"10H lord {lord10} strong in D10")

    floor = float((cfg_row or {}).get("promise_floor") or DEFAULT_PROMISE_FLOOR)
    score = round(min(score, 10.0), 2)
    return {
        "indicated": score >= floor,
        "score": score,
        "floor": floor,
        "factors": factors,
        "significators": significators,
        "houses": houses,
        "primary_house": primary,
        "lord": lord,
        "lord_sign_idx": lord_sign_idx,
        "d9_lord_sign_idx": d9_lord_sign_idx,
        "karaka": karaka,
    }


# ── Stage 2a: Vimsottari stack scan (MD era → AD year → PD ~3-month) ────────

def _rows_window(r) -> Tuple[str, str]:
    return (str(r.get("start_date") or r.get("start") or "")[:10],
            str(r.get("end_date") or r.get("end") or "")[:10])


def stage2a_vimsottari(significators: Set[str],
                       ads: List[dict],
                       pds: Optional[List[dict]],
                       from_date: str,
                       to_date: str) -> List[dict]:
    """
    Scan level-2 ADs (with metadata.parent_lord = MD) across [from_date,
    to_date]; flag sub-periods whose lord is a Stage-1 significator.
    PD rows (level 3, from dasha_periods backfill) narrow to ~3-month windows;
    live _compute_pds_for_ad is the fallback only.
    Returns candidates sorted by window_start.
    """
    from antar_engine.dasha_event_mapper import _compute_pds_for_ad

    pd_by_span: List[dict] = []
    for r in pds or []:
        s, e = _rows_window(r)
        if s and e:
            pd_by_span.append({"lord": r.get("planet_or_sign") or r.get("lord"),
                               "start": s, "end": e})

    out: List[dict] = []
    for ad in ads:
        s, e = _rows_window(ad)
        if not s or not e or e < from_date or s > to_date:
            continue
        ad_lord = ad.get("planet_or_sign") or ad.get("lord") or ""
        md_lord = ""
        meta = ad.get("metadata")
        if isinstance(meta, dict):
            md_lord = meta.get("parent_lord") or meta.get("parent_md") or ""
        ad_hit = ad_lord in significators
        md_hit = md_lord in significators
        if not ad_hit and not md_hit:
            continue
        strength = (2 if ad_hit else 0) + (1 if md_hit else 0)

        # PD narrowing: DB rows inside this AD first, live compute fallback
        ad_pds = [p for p in pd_by_span if s <= p["start"] and p["end"] <= e] \
            or _compute_pds_for_ad(ad_lord, s, e)
        pd_hits = [p for p in ad_pds
                   if (p.get("lord") or "") in significators
                   and p["end"] >= from_date and p["start"] <= to_date]
        if pd_hits:
            for p in pd_hits:
                out.append({
                    "window_start": max(p["start"], from_date),
                    "window_end": min(p["end"], to_date),
                    "granularity": "PD",
                    "md_lord": md_lord, "ad_lord": ad_lord,
                    "pd_lord": p.get("lord"),
                    "ad_start": s, "ad_end": e,
                    "vims_strength": strength + 1,
                })
        else:
            out.append({
                "window_start": max(s, from_date),
                "window_end": min(e, to_date),
                "granularity": "AD",
                "md_lord": md_lord, "ad_lord": ad_lord, "pd_lord": None,
                "ad_start": s, "ad_end": e,
                "vims_strength": strength,
            })
    out.sort(key=lambda c: c["window_start"])
    return out


# ── Stage 2b: Jaimini Chara dasha vote ───────────────────────────────────────

def _jaimini_static(ctx: dict) -> Optional[dict]:
    """Karakas, AL, UL, Karakamsa — computed once per chart."""
    jp = ctx.get("jaimini_planets") or {}
    if not jp:
        return None
    try:
        from antar_engine.jaimini_engine import (
            compute_7_karakas, compute_arudha_lagna, compute_upapada_lagna,
            compute_karakamsa, Planet)
        karakas = compute_7_karakas(jp)
        al = compute_arudha_lagna(ctx["lagna_idx"], jp)
        ul = compute_upapada_lagna(ctx["lagna_idx"], jp)
        d9p = {n: Planet(name=n, sign=s, degree=0.0, degree_in_sign=0.0)
               for n, s in (ctx.get("d9_planets_idx") or {}).items()}
        try:
            karakamsa = compute_karakamsa(karakas, d9p) if d9p else karakas[0].sign
        except Exception:
            karakamsa = karakas[0].sign
        return {"karakas": {k.karaka: k for k in karakas},
                "al": al, "ul": ul, "karakamsa": karakamsa}
    except Exception as e:
        print(f"[event_convergence] jaimini static failed: {e}")
        return None


def _jaimini_event_conditions(event_type: str, dasha_sign: int, ctx: dict,
                              st: dict) -> List[str]:
    """
    Per-event Chara-dasha sign conditions (project Jaimini spec + brief).
    Returns the list of condition strings met for this dasha sign.
    """
    from antar_engine.jaimini_engine import get_rashi_drishti
    lagna = ctx["lagna_idx"]
    karakas = st["karakas"]
    al, ul, karakamsa = st["al"], st["ul"], st["karakamsa"]
    drishti = set(get_rashi_drishti(dasha_sign))

    def hf(base: int) -> int:                     # house of dasha sign from base
        return ((dasha_sign - base) % 12) + 1

    def k_hit(key: str) -> bool:                  # contains or aspects karaka
        k = karakas.get(key)
        return bool(k) and (k.sign == dasha_sign or k.sign in drishti)

    met: List[str] = []
    if event_type in ("serious_partnership_began",):
        if hf(ul.sign) in (1, 7, 2):
            met.append(f"Chara sign is {hf(ul.sign)} from UL")
        if hf(al.sign) == 7:
            met.append("Chara sign is 7th from AL")
        if k_hit("DK"):
            met.append("Chara sign contains/aspects DK")
    elif event_type in ("family_expansion_first", "family_expansion_second"):
        if hf(lagna) in (1, 5, 9):
            met.append(f"Chara sign is {hf(lagna)} from Lagna")
        if k_hit("PK"):
            met.append("Chara sign contains/aspects PK")
        pk = karakas.get("PK")
        if pk and ((pk.sign - dasha_sign) % 12) + 1 == 5:
            met.append("PK in 5th from Moving Lagna")
    elif event_type in ("career_pivot", "business_start", "professional_setback"):
        amk = karakas.get("AmK")
        if amk and ((amk.sign - dasha_sign) % 12) + 1 in (1, 10, 11):
            met.append("AmK in 1/10/11 from Dasha sign")
        if dasha_sign == karakamsa or dasha_sign in get_rashi_drishti(karakamsa):
            met.append("Dasha sign is/aspects Karakamsa")
        if hf(al.sign) == 10:
            met.append("Chara sign is 10th from AL")
        if hf(lagna) in (10, 11):
            met.append(f"Chara sign is {hf(lagna)} from Lagna")
    elif event_type == "major_acquisition":
        if hf(lagna) == 4:
            met.append("Chara sign is 4th from Lagna")
        mk = karakas.get("MK")
        if mk and ((mk.sign - dasha_sign) % 12) + 1 == 4:
            met.append("MK in 4th from Moving Lagna")
        if k_hit("MK"):
            met.append("Chara sign contains/aspects MK")
    elif event_type == "major_relocation":
        h7 = (lagna + 6) % 12
        h9 = (lagna + 8) % 12
        if h7 in drishti or h9 in drishti or dasha_sign in (h7, h9):
            met.append("Chara sign is/aspects 7th or 9th from Lagna")
        rahu = ctx["planet_sign"]("Rahu")
        if rahu is not None and (rahu == dasha_sign or rahu in drishti):
            met.append("Chara sign contains/aspects Rahu")
        if hf(lagna) == 12 or SIGN_RULER_IDX[(lagna + 11) % 12] == \
                SIGN_RULER_IDX[dasha_sign]:
            met.append("12th-house involvement")
    elif event_type == "serious_partnership_ended":
        if k_hit("GK"):
            met.append("Chara sign contains/aspects GK")
        seventh = (lagna + 6) % 12
        if ((dasha_sign - seventh) % 12) + 1 in (6, 8, 12):
            met.append("Chara sign is 6/8/12 from the 7th house")
        # affliction to DK or UL: a malefic occupying/aspecting DK sign or UL
        dk = karakas.get("DK")
        affl = []
        for m in MALEFICS:
            ms = ctx["planet_sign"](m)
            if ms is None:
                continue
            from antar_engine.jaimini_engine import get_rashi_drishti as _rd
            if dk and (ms == dk.sign or dk.sign in _rd(ms)):
                affl.append(f"{m}→DK")
            if ms == ul.sign or ul.sign in _rd(ms):
                affl.append(f"{m}→UL")
        if affl and (k_hit("GK") or hf(ul.sign) in (1, 7, 2, 6, 8, 12)):
            met.append(f"DK/UL afflicted ({','.join(sorted(set(affl))[:3])})")
    elif event_type in ("loss_of_father", "loss_of_mother"):
        base_house = 9 if event_type == "loss_of_father" else 4
        base = (lagna + base_house - 1) % 12
        if ((dasha_sign - base) % 12) + 1 in (2, 7, 8, 12):
            met.append(f"Chara sign in maraka/loss axis from the {base_house}H")
        if k_hit("GK"):
            met.append("Chara sign contains/aspects GK")
    elif event_type in ("legal_entanglement", "financial_disruption"):
        if hf(lagna) in (6, 8, 12):
            met.append(f"Chara sign is {hf(lagna)} from Lagna (stress axis)")
        if k_hit("GK"):
            met.append("Chara sign contains/aspects GK")
    return met


def stage2b_jaimini(event_type: str, ctx: dict, birth_date: datetime,
                    from_date: str, to_date: str,
                    min_conditions: int = 2) -> List[dict]:
    """
    Walk the Chara-dasha timeline; every MD (and its ADs) whose sign meets
    >= min_conditions event conditions is a Jaimini vote window.
    Returns [{"start","end","sign","level","conditions"}].
    """
    st = _jaimini_static(ctx)
    if not st or not ctx.get("jaimini_planets"):
        return []
    try:
        from antar_engine.jaimini_engine import compute_chara_dasha
        mds = compute_chara_dasha(ctx["lagna_idx"], ctx["jaimini_planets"],
                                  birth_date, num_cycles=2)
    except Exception as e:
        print(f"[event_convergence] chara dasha failed: {e}")
        return []

    out: List[dict] = []
    for md in mds:
        ms, me = md.start_date.strftime("%Y-%m-%d"), md.end_date.strftime("%Y-%m-%d")
        if me < from_date or ms > to_date:
            continue
        md_met = _jaimini_event_conditions(event_type, md.sign, ctx, st)
        if len(md_met) >= min_conditions:
            out.append({"start": max(ms, from_date), "end": min(me, to_date),
                        "sign": SIGN_NAMES[md.sign], "level": "MD",
                        "conditions": md_met})
        # AD refinement inside qualifying-or-not MDs (AD sign can fire alone
        # when the MD sign is silent — Chara AD carries event power)
        for ad in md.sub_periods or []:
            as_, ae = ad.start_date.strftime("%Y-%m-%d"), ad.end_date.strftime("%Y-%m-%d")
            if ae < from_date or as_ > to_date:
                continue
            ad_met = _jaimini_event_conditions(event_type, ad.sign, ctx, st)
            if len(ad_met) >= min_conditions:
                out.append({"start": max(as_, from_date),
                            "end": min(ae, to_date),
                            "sign": SIGN_NAMES[ad.sign], "level": "AD",
                            "conditions": ad_met})
    return out


# ── window overlap helpers (used by the resolver) ────────────────────────────

def _days_between(a_iso: str, b_iso: str) -> int:
    try:
        a = datetime.strptime(a_iso[:10], "%Y-%m-%d")
        b = datetime.strptime(b_iso[:10], "%Y-%m-%d")
        return abs((b - a).days)
    except (ValueError, TypeError):
        return 10 ** 6


def _overlap_days(a_start: str, a_end: str, b_start: str, b_end: str) -> int:
    try:
        s = max(datetime.strptime(a_start[:10], "%Y-%m-%d"),
                datetime.strptime(b_start[:10], "%Y-%m-%d"))
        e = min(datetime.strptime(a_end[:10], "%Y-%m-%d"),
                datetime.strptime(b_end[:10], "%Y-%m-%d"))
        return max(0, (e - s).days)
    except (ValueError, TypeError):
        return 0


# ═════════════════════════════════════════════════════════════════════════════
# CONVERGENCE RESOLVER (Stage 3 + Stage 4 + class-gated surfacing)
# ═════════════════════════════════════════════════════════════════════════════

def format_converged_for_prompt(predictions: List[dict],
                                past_only: bool = False) -> str:
    """COMPUTED LIFE EVENT WINDOWS prompt block from converged predictions.
    Single source for every dated-event claim Claude narrates."""
    today = datetime.now().strftime("%Y-%m-%d")
    LABELS = {
        "serious_partnership_began": "Serious partnership window",
        "serious_partnership_ended": "Partnership transition window",
        "family_expansion_first": "Family expansion (first)",
        "family_expansion_second": "Family expansion (second)",
        "major_relocation": "Major relocation window",
        "major_acquisition": "Major acquisition window",
        "career_pivot": "Career pivot window",
        "business_start": "Business start window",
        "professional_setback": "Professional setback window",
        "legal_entanglement": "Legal entanglement window",
        "financial_disruption": "Financial disruption window",
        "loss_of_father": "Loss of father",
        "loss_of_mother": "Loss of mother",
    }
    lines = ["\n## COMPUTED LIFE EVENT WINDOWS "
             "(convergence engine — do not recalculate)\n"]
    n = 0
    for p in predictions or []:
        if past_only and str(p.get("window_end") or "") > today:
            continue
        label = LABELS.get(p.get("event_type"), p.get("event_type", ""))
        lines.append(
            f"{label}: {str(p['window_start'])[:7]} to "
            f"{str(p['window_end'])[:7]} — {p.get('confidence', 0)}/3 "
            f"independent timing systems agree")
        n += 1
    if not n:
        lines.append(
            "No event window reached the convergence gate. If asked when a "
            "specific life event happened, say the chart does not show a "
            "clear enough window to date it — do NOT estimate one.")
    lines.append(
        "\nUse ONLY these windows when answering questions about dated life "
        "events. Do not recalculate, do not invent timing, and do not "
        "assert any dated event that is not listed here.")
    return "\n".join(lines)


def _functional_solo_flags(ctx: dict) -> Tuple[bool, bool]:
    """Rao functional-significator refinement: the 9th and 10th birth-lords
    act as Jupiter/Saturn. When Jupiter or Saturn IS the 9th/10th lord, its
    single transit influence qualifies alone."""
    lords = {ctx["house_lord"](9), ctx["house_lord"](10)}
    return ("Jupiter" in lords, "Saturn" in lords)


def _merge_contiguous(cands: List[dict], gap_days: int = 7) -> List[dict]:
    """Merge contiguous qualifying candidates sharing the same MD+AD chain."""
    if not cands:
        return []
    cands = sorted(cands, key=lambda c: c["window_start"])
    out = [dict(cands[0])]
    for c in cands[1:]:
        last = out[-1]
        same_chain = (c.get("md_lord"), c.get("ad_lord")) == \
                     (last.get("md_lord"), last.get("ad_lord"))
        if same_chain and _days_between(last["window_end"], c["window_start"]) <= gap_days:
            last["window_end"] = max(last["window_end"], c["window_end"])
            last["vims_strength"] = max(last["vims_strength"], c["vims_strength"])
            if c.get("pd_lord") and not last.get("pd_lord"):
                last["pd_lord"] = c["pd_lord"]
        else:
            out.append(dict(c))
    return out


def converge_events(
    chart_data: dict,
    chart_record: dict,
    dasha_rows: List[dict],
    from_date: str,
    to_date: str,
    supabase=None,
    confirmed_events: Optional[Dict[str, str]] = None,
    event_types: Optional[List[str]] = None,
    position_fn=None,
    include_debug: bool = True,
    transit_overlap_min_days: int = 10,
) -> dict:
    """
    The Stage 1→4 convergence pipeline for one chart.

    dasha_rows: raw dasha_periods rows (any levels; filtered here).
    confirmed_events: {event_type: 'YYYY-MM-DD'} — a confirmed date prunes
        every other candidate for that event type (Stage 4).
    Returns {"predictions": [...], "skipped": {...}, "meta": {...}}.
    Each prediction: event_type, window_start, window_end, granularity,
    confidence (= lock count 0-3), locks{vims,jaimini,transit,count},
    reasoning, and _debug_reasoning (ADMIN-ONLY — full jargon, never strip).

    NEVER pads: where systems don't converge, the event type is absent.
    """
    from antar_engine.event_gating import (get_config, age_plausibility,
                                           stage_factor, gating_enabled)

    ctx = build_natal_context(chart_data)
    if not ctx:
        return {"predictions": [], "skipped": {"all": "no_chart_data"},
                "meta": {}}

    birth_date_str = str(chart_record.get("birth_date")
                         or _safe_json(chart_data).get("birth_date") or "")[:10]
    try:
        birth_dt = datetime.strptime(birth_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return {"predictions": [], "skipped": {"all": "no_birth_date"},
                "meta": {}}

    cfg = get_config(supabase)
    mds = [r for r in dasha_rows or [] if r.get("level") == 1]
    ads = [r for r in dasha_rows or [] if r.get("level") == 2]
    pds = [r for r in dasha_rows or [] if r.get("level") == 3]
    if not ads:
        return {"predictions": [], "skipped": {"all": "no_antardashas"},
                "meta": {}}

    # Stage-3 chronology: ONE build per chart span (no per-candidate ephemeris)
    chrono = {}
    chrono_err = None
    try:
        from antar_engine.transit_engine import (
            build_transit_chronology, double_transit_windows,
            event_transit_targets)
        chrono = build_transit_chronology(from_date, to_date,
                                          position_fn=position_fn)
        if not chrono.get("Jupiter") or not chrono.get("Saturn"):
            chrono_err = "empty_chronology"
    except Exception as e:
        chrono_err = f"chronology_failed: {e}"

    jup_solo, sat_solo = _functional_solo_flags(ctx)
    keys = event_types or [et for et in cfg.keys()]
    confirmed_events = confirmed_events or {}

    predictions: List[dict] = []
    skipped: Dict[str, str] = {}
    gating_on = gating_enabled()

    for event_type in keys:
        row = cfg.get(event_type)
        if row is not None and not row.get("enabled", True):
            skipped[event_type] = "disabled_in_config"
            continue
        dt_enabled = bool((row or {}).get("double_transit_enabled", True))

        # ── Stage 1: promise ─────────────────────────────────────────────
        promise = stage1_promise(event_type, ctx, row)
        if not promise["indicated"]:
            skipped[event_type] = (f"no_promise (score {promise['score']} "
                                   f"< floor {promise['floor']})")
            continue

        # ── Stage 2a: Vimsottari candidates ──────────────────────────────
        cands = stage2a_vimsottari(promise["significators"], ads, pds,
                                   from_date, to_date)
        if not cands:
            skipped[event_type] = "no_vimsottari_window"
            continue
        cands = _merge_contiguous(cands)

        # ── Stage 2b: Jaimini vote windows ───────────────────────────────
        jwins = stage2b_jaimini(event_type, ctx, birth_dt, from_date, to_date)

        # ── Stage 3: double-transit windows on event targets ─────────────
        dt_wins = []
        targets_info = {"targets": set(), "labels": {}}
        if chrono and not chrono_err and dt_enabled:
            targets_info = event_transit_targets(
                promise["houses"][:1],          # primary event house only
                ctx["lagna_idx"], ctx["moon_idx"],
                lord_sign_index=promise["lord_sign_idx"],
                d9_lord_sign_index=(promise["d9_lord_sign_idx"]
                                    if event_type in D9_TARGET_EVENTS else None),
            )
            require_jup_on = (promise["lord_sign_idx"]
                              if event_type in AUSPICIOUS_EVENTS else None)
            try:
                dt_wins = double_transit_windows(
                    targets_info["targets"], chrono, from_date, to_date,
                    jupiter_solo=jup_solo, saturn_solo=sat_solo,
                    require_jupiter_on=require_jup_on, merge_gap_days=3)
            except Exception as e:
                chrono_err = f"double_transit_failed: {e}"

        # ── lock each candidate ──────────────────────────────────────────
        scored: List[dict] = []
        for c in cands:
            j_hit = None
            for jw in jwins:
                if _overlap_days(c["window_start"], c["window_end"],
                                 jw["start"], jw["end"]) > 0:
                    j_hit = jw
                    break
            t_hit = None
            for dw in dt_wins:
                need = min(transit_overlap_min_days,
                           max(1, _days_between(c["window_start"],
                                                c["window_end"]) // 2))
                if _overlap_days(c["window_start"], c["window_end"],
                                 dw["start"], dw["end"]) >= need:
                    t_hit = dw
                    break
            locks = 1 + (1 if j_hit else 0) + (1 if t_hit else 0)

            # ── Stage 4: life-stage priors (SOFT down-weight, never veto)
            try:
                ws_dt = datetime.strptime(c["window_start"], "%Y-%m-%d")
                age = (ws_dt - birth_dt).days / 365.25
            except (ValueError, TypeError):
                age = -1.0
            af = age_plausibility(row, age) if (gating_on and age >= 0) else 1.0
            sf = stage_factor(row, chart_record, age) if gating_on else 1.0
            rank = (locks * 10 + c["vims_strength"] + promise["score"] / 4.0) \
                * max(af, 0.15) * max(sf, 0.1)
            scored.append({**c, "locks": locks, "jaimini_hit": j_hit,
                           "transit_hit": t_hit, "age_at_window": round(age, 1),
                           "age_factor": round(af, 2),
                           "stage_factor": round(sf, 2), "rank": rank})

        # Age prior is SOFT inside the configured band, but af == 0.0 means
        # OUTSIDE the band entirely (e.g. first child at age 9) — drop those
        # candidates whenever at least one in-band candidate exists. If the
        # whole set is out-of-band, keep it (the band itself may be miscal-
        # ibrated — founder tunes event_engine_config, engine stays honest).
        in_band = [c for c in scored if c["age_factor"] > 0.0]
        if in_band:
            scored = in_band
        else:
            # Whole candidate set is outside the configured age band. Only
            # FULL 3/3 convergence may override the prior (covers real
            # outliers like a marriage at 46); partial convergence cannot
            # resurrect an age-impossible event.
            scored = [c for c in scored if c["locks"] >= 3]

        # ── Stage 4: confirmed-event pruning ─────────────────────────────
        conf_date = str(confirmed_events.get(event_type) or "")[:10]
        if conf_date:
            tol = int((row or {}).get("window_tolerance_days") or 90)
            def _contains(c):
                try:
                    d = datetime.strptime(conf_date, "%Y-%m-%d")
                    s = datetime.strptime(c["window_start"], "%Y-%m-%d")
                    e = datetime.strptime(c["window_end"], "%Y-%m-%d")
                    return s - timedelta(days=tol) <= d <= e + timedelta(days=tol)
                except (ValueError, TypeError):
                    return False
            kept = [c for c in scored if _contains(c)]
            if kept:
                scored = kept     # confirmed date prunes all other candidates

        # ── convergence gate: 3/3 painful, >=2/3 benign — NEVER pad ──────
        required = int((row or {}).get("required_locks") or
                       (3 if event_type in PAINFUL_EVENTS else 2))
        qual = [c for c in scored if c["locks"] >= required]
        if not qual:
            best_locks = max((c["locks"] for c in scored), default=0)
            skipped[event_type] = (f"convergence_below_gate "
                                   f"(best {best_locks}/{required})")
            continue

        # instance selector: strongest convergence, NOT earliest
        qual.sort(key=lambda c: (-c["locks"], -c["rank"], c["window_start"]))
        best = qual[0]

        pred = {
            "event_type": event_type,
            "window_start": best["window_start"],
            "window_end": best["window_end"],
            "granularity": best["granularity"],
            "confidence": best["locks"],            # = convergence count 0-3
            "locks": {
                "vims": True,
                "jaimini": bool(best["jaimini_hit"]),
                "transit": bool(best["transit_hit"]),
                "count": best["locks"],
            },
            "md_lord": best.get("md_lord"),
            "ad_lord": best.get("ad_lord"),
            "pd_lord": best.get("pd_lord"),
            "promise_score": promise["score"],
            "age_at_window": best["age_at_window"],
            "qualifying_windows": len(qual),
            "reasoning": (
                f"{best['locks']}/3 systems converge on this window "
                f"(dasha chain{' + Jaimini' if best['jaimini_hit'] else ''}"
                f"{' + double transit' if best['transit_hit'] else ''})."
            ),
        }
        if include_debug:
            pred["_debug_reasoning"] = {
                "promise_strength": {"score": promise["score"],
                                     "factors": promise["factors"]},
                "dasha_chain": {
                    "md": best.get("md_lord"), "ad": best.get("ad_lord"),
                    "pd": best.get("pd_lord"),
                    "ad_span": [best.get("ad_start"), best.get("ad_end")],
                    "granularity": best["granularity"],
                    "vims_strength": best["vims_strength"],
                },
                "jaimini_condition": (
                    {"sign": best["jaimini_hit"]["sign"],
                     "level": best["jaimini_hit"]["level"],
                     "span": [best["jaimini_hit"]["start"],
                              best["jaimini_hit"]["end"]],
                     "conditions": best["jaimini_hit"]["conditions"]}
                    if best["jaimini_hit"] else None),
                "double_transit": (
                    {"span": [best["transit_hit"]["start"],
                              best["transit_hit"]["end"]],
                     "jupiter_sign": SIGN_NAMES[
                         best["transit_hit"]["trace"]["jupiter_sign"]]
                     if best["transit_hit"]["trace"].get("jupiter_sign") is not None else None,
                     "saturn_sign": SIGN_NAMES[
                         best["transit_hit"]["trace"]["saturn_sign"]]
                     if best["transit_hit"]["trace"].get("saturn_sign") is not None else None,
                     "houses_hit": sorted(
                         set(best["transit_hit"]["trace"]["jupiter_targets_hit"])
                         | set(best["transit_hit"]["trace"]["saturn_targets_hit"])),
                     "jupiter_solo": jup_solo, "saturn_solo": sat_solo}
                    if best["transit_hit"] else None),
                "locks": pred["locks"],
                "stage4": {"age_factor": best["age_factor"],
                           "stage_factor": best["stage_factor"],
                           "confirmed_event_pruned": bool(conf_date),
                           "required_locks": required},
                "targets": {str(k): v for k, v in
                            (targets_info.get("labels") or {}).items()},
            }
        predictions.append(pred)

    # ── Stage 4: sequential-dependency constraints ───────────────────────
    # second family expansion must START after the first's window begins;
    # partnership_ended must start after partnership_began (temporal paradox
    # = drop the ended call, never re-order silently).
    by_type = {p["event_type"]: p for p in predictions}
    first = by_type.get("family_expansion_first")
    second = by_type.get("family_expansion_second")
    if first and second and second["window_start"] <= first["window_end"]:
        predictions = [p for p in predictions
                       if p is not second]
        skipped["family_expansion_second"] = (
            "sequencing: window not after family_expansion_first")
    began = by_type.get("serious_partnership_began")
    ended = by_type.get("serious_partnership_ended")
    if ended and began and began["window_start"] >= ended["window_start"]:
        predictions = [p for p in predictions if p is not ended]
        skipped["serious_partnership_ended"] = (
            "sequencing: temporal paradox vs partnership_began")

    predictions.sort(key=lambda p: (-p["confidence"], p["window_start"]))
    return {
        "predictions": predictions,
        "skipped": skipped,
        "meta": {
            "engine": "convergence_v1",
            "span": [from_date, to_date],
            "chronology": "ok" if (chrono and not chrono_err) else
                          (chrono_err or "unavailable"),
            "functional_solo": {"jupiter": jup_solo, "saturn": sat_solo},
            "pd_source": "db_level3" if pds else "live_compute",
        },
    }
