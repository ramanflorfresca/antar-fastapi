"""
antar_engine/event_evidence.py — whole-board deterministic evidence block.

Event Prediction Engine v2, PHASE 1 (founder rulings 2026-06-05).

Python computes the WHOLE board as facts — dasha tree (MD-AD-PD-SD), chara
MD-sign-as-lagna rotation + karakas, divisionals, yogas, varshphal gate,
LK sleeping planets, and the full TRANSIT STATE incl. Double Transit.
NO verdicts, NO timing synthesis — the LLM does the combination reading
downstream (Phase 2). The chart is read whole: every house's lord +
occupants stay visible, never one domain in isolation.

ENGINE CONSOLIDATION (founder rulings, Phase 0 → Phase 1):
  * Vimshottari MD-AD-PD-SD: vimsottari.calculate_vimsottari_from_chart +
    phase_analyzer's _find_current_period/_compute_pratyantardashas/
    _compute_sookshma_dashas — the ONLY subdivision implementation in the
    codebase. Fallback to subdividing the current AD *row* with the same
    phase_analyzer helpers ONLY when chart_data.birth_jd is missing.
  * Chara + karakas + moving-lagna: jaimini_engine ONLY
    (build_jaimini_context via calculate_jaimini_analysis). jaimini.py and
    karakas.py are DEPRECATED for the evidence path — never read here.
  * KARAKAS: 7-scheme, ranked by degree-in-sign desc (jaimini_engine basis).
    8-karaka/Rahu explicitly ruled OUT.
  * STALENESS: chara MD/AD computed LIVE at target date; the
    jaimini_data JSONB current_md/current_ad snapshot is NEVER read (rots).
    DB dasha_periods chara rows are cross-checked (db_md_agrees fact) but
    not authoritative — they come from the deprecated jaimini.py engine,
    whose sequence-direction/lordship rules differ for some lagnas.

Reuses confirmed-good infra: d_charts_calculator (divisionals + dignity),
varshaphal_table, lk_trigger.is_sleeping, yoga_engine (key casing fixed in
this sprint), double_transit (Lahiri, consistent with natal).

SCOPE NOTES carried as board facts (recorded, not fixed — founder ruling):
  * D30 is a simplified odd/even mapping (not classical unequal-degree
    Trimshamsha) and D11 uses the generic divisional fallback → health
    questions flagged lower-confidence on the board.
  * lk_trigger uses MEAN_NODE for Rahu vs transits.py TRUE_NODE — on record;
    irrelevant to Sat/Jup double transit.

Internal module: planet/house names here never reach the frontend directly
(output_strips owns user-facing text).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from antar_engine.d_charts_calculator import (
    SIGNS, SIGN_INDEX, SIGN_LORDS,
    get_all_d_charts, get_d1_from_chart_data, _planet_strength,
)
from antar_engine import double_transit as dt

logger = logging.getLogger(__name__)

# ── Event map (spec table, v2 FINAL) ────────────────────────────────────────
# houses are read from the relevant lagna; funding is multi-house BY DESIGN —
# the engine reads ALL and the dasha + DT show which is lit.
EVENT_MAP = {
    "funding":    {"houses": [11, 2, 8, 6], "divisions": [10, 2, 11]},
    # foreign_move and domestic_move are now distinct; "relocation" kept as a
    # legacy alias defaulting to foreign houses (for back-compat with any caller
    # passing "relocation" without disambiguation).
    "relocation": {"houses": [12, 9, 3, 4], "divisions": [1, 4]},
    "foreign_move":  {"houses": [12, 9, 3], "divisions": [1, 12]},
    "domestic_move": {"houses": [4, 3, 11], "divisions": [1, 4],
                      "note": "4=home/inner-foundation, 3=short-distance change of place, 11=goal-satisfaction"},
    "marriage":   {"houses": [7, 2],        "divisions": [9],
                   "extra_dt_planets": ["Venus"]},
    # [evmap-2026-06-07] children: 5H (children), 9H (putrakaraka/dharma),
    # 2H (family). D7 = saptamamsha (children divisional).
    "children":   {"houses": [5, 9, 2],     "divisions": [7, 9],
                   "extra_dt_planets": ["Jupiter"]},
    # [evmap-2026-06-07] reconciliation: 7H (partnership), 5H (romance/heart),
    # 4H (emotional re-binding). D9 confirms the bond. Distinct from marriage
    # (a new partnership) and divorce (separation) — this is RE-binding.
    "reconciliation": {"houses": [7, 5, 4], "divisions": [9, 4],
                       "extra_dt_planets": ["Venus", "Moon"]},
    "career":     {"houses": [10, 6, 11],   "divisions": [10, 9],
                   "extra_dt_planets": ["AmK"]},
    "health":     {"houses": [1, 6, 8],     "divisions": [1, 30],
                   "low_confidence": "D30 simplified + D11 generic mapping — "
                                     "health divisional evidence is "
                                     "lower-confidence (founder scope note)"},
    "litigation": {"houses": [6, 8, 12],    "divisions": [1]},
    "general":    {"houses": [10, 11, 2],   "divisions": [10, 9]},
}

# detect_concern vocabulary → spec event
CONCERN_TO_EVENT = {
    "finance": "funding", "funding": "funding", "wealth": "funding",
    "loss": "funding", "speculation": "funding", "money": "funding",
    "career": "career", "business": "career", "education": "career",
    "marriage": "marriage", "love": "marriage", "divorce": "marriage",
    # [evmap-2026-06-07] children was routed to "marriage" (wrong divisional);
    # now uses its own recipe (D7).
    "children": "children",
    # [evmap-2026-06-07] reconciliation gets its own recipe (D9 + 4H).
    "reconciliation": "reconciliation",
    "health": "health",
    "legal": "litigation",
    # [evmap-2026-06-07] property + domestic move → domestic_move (4H);
    # foreign → foreign_move (12H). Caller can pre-disambiguate by keyword.
    "property": "domestic_move",
    "domestic_move": "domestic_move",
    "foreign": "foreign_move",
    "foreign_move": "foreign_move",
    # "relocation" remains a back-compat alias mapping to the multi-house
    # legacy recipe — new code should pass "foreign_move" or "domestic_move".
    "relocation": "relocation",
    "spiritual": "general", "general": "general",
}

# yoga_engine.DOMAIN_DETECTORS keys it actually knows
_YOGA_DOMAIN = {
    "funding": "funding", "career": "funding", "general": "funding",
    "relocation": "property", "marriage": "marriage",
    "health": "health", "litigation": "legal",
}

_HOUSE_TAGS = {
    "kendra": {1, 4, 7, 10}, "trikona": {1, 5, 9},
    "dusthana": {6, 8, 12}, "upachaya": {3, 6, 10, 11},
    "wealth": {2, 11},
}


# ── small helpers ───────────────────────────────────────────────────────────

def _safe_json(v):
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _parse_d(s) -> Optional[date]:
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _rows(dashas, system):
    return (dashas or {}).get(system, []) or []


def _level(r) -> str:
    return str(r.get("level") or r.get("type", "")).lower()


def _lord(r) -> str:
    return r.get("lord_or_sign") or r.get("planet_or_sign", "")


def _win(r):
    return (_parse_d(r.get("start_date") or r.get("start")),
            _parse_d(r.get("end_date") or r.get("end")))


def _current_row(dashas, system, levels, today):
    for r in _rows(dashas, system):
        if _level(r) not in levels:
            continue
        s, e = _win(r)
        if s and e and s <= today < e:
            return r
    return None


def _lagna_idx(chart_data) -> int:
    lagna = (chart_data or {}).get("lagna") or {}
    si = lagna.get("sign_index")
    if isinstance(si, int) and 0 <= si <= 11:
        return si
    return SIGN_INDEX.get(lagna.get("sign", ""), 0)


def _planet_sign_idx(planets: dict, p: str) -> Optional[int]:
    d = planets.get(p) or {}
    si = d.get("sign_index")
    if isinstance(si, int):
        return si % 12
    return SIGN_INDEX.get(d.get("sign", "")) if d.get("sign") in SIGN_INDEX else None


def _house_tags(h: int) -> list[str]:
    return sorted(tag for tag, hs in _HOUSE_TAGS.items() if h in hs)


def _iso(d) -> Optional[str]:
    if isinstance(d, datetime):
        return d.date().isoformat()
    return d.isoformat() if isinstance(d, date) else None


# ── Vimshottari tree: phase_analyzer implementations ONLY ───────────────────

def _lord_profile(planet: str, chart_data: dict, lagna_idx: int) -> dict:
    """Where he sits, whom he sits with, what he owns (reading step 2)."""
    planets = (chart_data or {}).get("planets") or {}
    d = planets.get(planet) or {}
    sign = d.get("sign", "")
    house = d.get("house")
    with_planets = [p for p, pd_ in planets.items()
                    if p != planet and isinstance(pd_, dict)
                    and pd_.get("house") == house and house]
    owns = [h for h in range(1, 13)
            if SIGN_LORDS[SIGNS[(lagna_idx + h - 1) % 12]] == planet]
    return {
        "planet": planet, "sign": sign, "house_from_lagna": house,
        "dignity": _planet_strength(planet, sign) if sign else "unknown",
        "conjunct": with_planets, "owns_houses": owns,
        "house_tags": _house_tags(house) if isinstance(house, int) else [],
    }


def _period_out(p: Optional[dict]) -> Optional[dict]:
    if not p:
        return None
    return {"lord": p["lord"], "start": _iso(p["start_datetime"]),
            "end": _iso(p["end_datetime"])}


def _vim_tree_live(chart_data: dict, birth_jd: float, now: datetime):
    """MD-AD-PD-SD via vimsottari + phase_analyzer helpers (the one true
    subdivision implementation).

    Returns (tree, reason). On success: (dict, None). On failure: (None, reason)
    where `reason` distinguishes the THREE non-success cases so a crash is never
    mislabeled as a data gap (founder fix-now 2026-06-05):
      * "phase_analyzer import error: ..."  — dependency chain unavailable
      * "live tree exception: <Type>: ..."  — the compute actually RAISED
        (full traceback logged via logger.exception)
      * "no active MD for current date"     — genuine data state, not a crash
    """
    try:
        from antar_engine import vimsottari
        from antar_engine.life_arc.phase_analyzer import (
            _find_current_period, _compute_pratyantardashas,
            _compute_sookshma_dashas,
        )
    except Exception as e:
        logger.exception("[evidence] phase_analyzer chain import failed")
        return None, f"phase_analyzer import error: {e}"
    try:
        result = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
        mds, ads = result["mahadashas"], result["antardashas"]
        cur_md = _find_current_period(mds, now)
        if not cur_md:
            return None, "no active MD for current date"
        md_ads = [a for a in ads if a.get("parent_lord") == cur_md["lord"]
                  and a["start_datetime"] >= cur_md["start_datetime"]
                  and a["end_datetime"] <= cur_md["end_datetime"] + timedelta(seconds=1)]
        cur_ad = _find_current_period(md_ads, now)
        cur_pd = cur_sd = None
        upcoming_pds = []
        if cur_ad:
            pds = _compute_pratyantardashas(cur_ad)
            cur_pd = _find_current_period(pds, now)
            upcoming_pds = [p for p in pds if p["start_datetime"] >= now][:4]
            if cur_pd:
                sds = _compute_sookshma_dashas(cur_pd)
                cur_sd = _find_current_period(sds, now)
        return {"md": cur_md, "ad": cur_ad, "pd": cur_pd, "sd": cur_sd,
                "upcoming_pds": upcoming_pds, "source": "phase_analyzer"}, None
    except Exception as e:
        # A real crash in the live chain — log the traceback and report it AS a
        # crash, never as "birth_jd missing" (that masked the bug before).
        logger.exception("[evidence] live vim tree raised — NOT a data gap")
        return None, f"live tree exception: {type(e).__name__}: {e}"


def _vim_tree_from_rows(dashas: dict, today: date,
                        fallback_reason: str = "birth_jd missing") -> Optional[dict]:
    """Fallback path: MD/AD from dasha_periods rows; PD/SD by subdividing the
    AD row with phase_analyzer's helpers — no new math. tz-aware UTC throughout
    so _find_current_period (which now receives tz-aware `now`) doesn't blow
    up on offset-naive vs offset-aware comparisons. `fallback_reason` is the
    auditable WHY we are not on the live path (e.g. "birth_jd missing" vs
    "live tree unavailable")."""
    md_row = _current_row(dashas, "vimsottari", ("mahadasha", "1"), today)
    ad_row = _current_row(dashas, "vimsottari", ("antardasha", "antar", "2"), today)
    if not md_row:
        return None

    def _row_period(r):
        s, e = _win(r)
        if not (s and e):
            return None
        return {"lord": _lord(r),
                "start_datetime": datetime.combine(s, datetime.min.time(), tzinfo=timezone.utc),
                "end_datetime": datetime.combine(e, datetime.min.time(), tzinfo=timezone.utc),
                # [pd-sd-fix] phase_analyzer._compute_pratyantardashas reads
                # ad["duration_years"]; the row-fallback AD omitted it, so PD/SD
                # evidence silently fell back to unavailable. Supply it (value
                # only needs to be > 0 — it cancels inside the proportional math).
                "duration_years": max((e - s).days / 365.25, 0.0)}

    now = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)
    out = {"md": _row_period(md_row), "ad": _row_period(ad_row),
           "pd": None, "sd": None, "upcoming_pds": [],
           "source": f"dasha_periods rows ({fallback_reason})"}
    if out["ad"]:
        try:
            from antar_engine.life_arc.phase_analyzer import (
                _find_current_period, _compute_pratyantardashas,
                _compute_sookshma_dashas,
            )
            pds = _compute_pratyantardashas(out["ad"])
            out["pd"] = _find_current_period(pds, now)
            out["upcoming_pds"] = [p for p in pds if p["start_datetime"] >= now][:4]
            if out["pd"]:
                sds = _compute_sookshma_dashas(out["pd"])
                out["sd"] = _find_current_period(sds, now)
        except Exception as e:
            logger.warning("[evidence] row-fallback PD/SD unavailable: %s", e)
    return out


def _vimshottari_block(dashas, chart_data, lagna_idx, event_houses, today) -> dict:
    planets = (chart_data or {}).get("planets") or {}
    # tz-aware UTC: vimsottari output is tz-aware (utils.datetime_from_jd),
    # phase_analyzer._find_current_period compares against `now` — mixing
    # tz-naive `now` with tz-aware periods raised TypeError and silently
    # collapsed the live tree to row-fallback. (Fixed 2026-06-05.)
    now = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)

    def _connects(p: str) -> list[str]:
        how = []
        if not p:
            return how
        for h in event_houses:
            if SIGN_LORDS[SIGNS[(lagna_idx + h - 1) % 12]] == p:
                how.append(f"{p} rules house {h}")
        if (planets.get(p) or {}).get("house") in event_houses:
            how.append(f"{p} occupies house {(planets.get(p) or {}).get('house')}")
        return how

    birth_jd = (chart_data or {}).get("birth_jd")
    tree = None
    if birth_jd is None:
        # genuinely absent — NOT a crash. Row-fallback is the correct path.
        fallback_reason = "birth_jd absent from chart_data"
    else:
        tree, live_reason = _vim_tree_live(chart_data, birth_jd, now)
        # live_reason is None on success; carries the real cause otherwise
        # (import error / live tree exception / no active MD) so the source
        # label never masks a crash as a data gap.
        fallback_reason = live_reason or "live tree unavailable"
    if tree is None:
        tree = _vim_tree_from_rows(dashas, today, fallback_reason)

    block: dict = {"md": None, "ad": None, "pd": None, "sd": None,
                   "source": (tree or {}).get("source", "unavailable"),
                   "promise": {"md_connects": False, "ad_connects": False, "how": []}}
    if not tree:
        return block

    for key in ("md", "ad"):
        p = tree.get(key)
        if p:
            block[key] = _period_out(p)
            block[key]["profile"] = _lord_profile(p["lord"], chart_data, lagna_idx)
            how = _connects(p["lord"])
            if how:
                block["promise"][f"{key}_connects"] = True
                prefix = "" if key == "md" else "AD: "
                block["promise"]["how"] += [prefix + h for h in how]

    if tree.get("pd"):
        block["pd"] = _period_out(tree["pd"])
        block["pd"]["connects_event"] = bool(_connects(tree["pd"]["lord"]))
        block["pd"]["upcoming"] = [
            {**_period_out(p), "connects_event": bool(_connects(p["lord"]))}
            for p in tree.get("upcoming_pds", [])
        ]
    block["sd"] = _period_out(tree.get("sd"))

    # cross-check: does the DB MD row agree with the live tree? (PD coverage
    # in dasha_periods is known-inconsistent — this is the auditable fact)
    md_row = _current_row(dashas, "vimsottari", ("mahadasha", "1"), today)
    if md_row and block["md"]:
        block["db_md_agrees"] = (_lord(md_row) == block["md"]["lord"])
    return block


# ── Chara: jaimini_engine ONLY (live, never the JSONB snapshot) ─────────────

_KARAKA_TAGS = {"AK": "Atmakaraka", "AmK": "Amatyakaraka", "BK": "Bhratrukaraka",
                "MK": "Matrukaraka", "PK": "Putrakaraka", "GK": "Gnatikaraka",
                "DK": "Darakaraka"}


def _chara_block(dashas, chart_data, birth_date, today) -> dict:
    """Chara MD/AD + 7 karakas + rotations, computed LIVE at `today` via
    jaimini_engine (founder ruling: jaimini.py / karakas.py deprecated here;
    jaimini_data JSONB current_md/current_ad never read — staleness rule)."""
    planets = (chart_data or {}).get("planets") or {}
    block: dict = {"md_sign": None, "ad_sign": None, "rotated_houses": None,
                   "karakas": [], "source": "jaimini_engine live",
                   "ranking_basis": "degree-in-sign desc, 7-scheme (founder ruling)"}
    born = _parse_d(birth_date)
    if not (born and planets):
        block["error"] = "birth_date or planets missing"
        return block

    try:
        from antar_engine.jaimini_engine import calculate_jaimini_analysis
        lagna_idx = _lagna_idx(chart_data)
        # D9 dict for karakamsa — from the same divisional calculator the
        # rest of the board uses (sign index is all jaimini_engine needs).
        d9_for_karakamsa = {}
        try:
            from antar_engine.d_charts_calculator import get_d_chart
            d9_for_karakamsa = {p: {"sign": v["sign_index"]}
                                for p, v in get_d_chart(chart_data, 9).items()
                                if p != "Lagna"}
        except Exception:
            pass
        ctx = calculate_jaimini_analysis(
            lagna_sign=lagna_idx,
            planets_dict=planets,
            d9_planets_dict=d9_for_karakamsa,
            birth_date_str=born.isoformat(),
            target_date_str=today.isoformat(),
        )["context"]
    except Exception as e:
        logger.warning("[evidence] jaimini_engine failed: %s", e)
        block["error"] = f"jaimini_engine unavailable: {e}"
        return block

    if ctx.current_md:
        md = ctx.current_md
        block["md_sign"] = {"sign": md.sign_name, "start": _iso(md.start_date),
                            "end": _iso(md.end_date), "lord": md.lord,
                            "direction": md.direction}
        md_idx = md.sign

        # every house from MD-lagna: lord + occupants (cross-connections
        # must stay visible — whole-chart rule)
        rotated, occ = {}, {}
        for p in planets:
            si = _planet_sign_idx(planets, p)
            if si is not None:
                occ.setdefault((si - md_idx) % 12 + 1, []).append(p)
        for h in range(1, 13):
            hsign = SIGNS[(md_idx + h - 1) % 12]
            rotated[h] = {"sign": hsign, "lord": SIGN_LORDS[hsign],
                          "occupants": occ.get(h, []), "tags": _house_tags(h)}
        block["rotated_houses"] = rotated

        # all 7 karakas placed in the MD-rotated chart
        for k in ctx.karakas:
            house_from_md = (k.sign - md_idx) % 12 + 1
            block["karakas"].append({
                "abbr": k.karaka, "name": _KARAKA_TAGS.get(k.karaka, k.karaka),
                "planet": k.planet, "sign": SIGNS[k.sign],
                "degree_in_sign": round(k.degree_in_sign, 2),
                "house_from_md_lagna": house_from_md,
                "dignity": _planet_strength(k.planet, SIGNS[k.sign]),
                "house_tags": _house_tags(house_from_md),
            })

    if ctx.current_ad:
        ad = ctx.current_ad
        block["ad_sign"] = {"sign": ad.sign_name, "start": _iso(ad.start_date),
                            "end": _iso(ad.end_date), "lord": ad.lord}

    # jaimini_engine's own moving-lagna read (rotates to the ACTIVE sign —
    # AD if running, else MD) + the supporting structures.
    block["moving_lagna"] = ctx.moving_lagna_analysis or {}
    block["arudha_lagna"] = {"sign": ctx.arudha_lagna.sign_name}
    block["upapada_lagna"] = {"sign": ctx.upapada_lagna.sign_name}
    block["karakamsa"] = {"sign": ctx.karakamsa_sign_name}
    block["rashi_drishti_from_md"] = [SIGNS[s] for s in (ctx.rashi_drishti_from_md or [])]
    block["rashi_drishti_from_ad"] = [SIGNS[s] for s in (ctx.rashi_drishti_from_ad or [])]

    # cross-check vs DB rows (deprecated jaimini.py engine wrote them;
    # sequence-direction/lordship rules differ for some lagnas — auditable)
    md_row = _current_row(dashas, "jaimini", ("mahadasha", "1"), today)
    if md_row and block["md_sign"]:
        block["db_md_agrees"] = (_lord(md_row) == block["md_sign"]["sign"])
        block["db_md_row_sign"] = _lord(md_row)
    return block


# ── Varshphal gate + LK sleeping ────────────────────────────────────────────

def _varshphal_block(chart_data, birth_date, event_houses, today) -> dict:
    born = _parse_d(birth_date)
    out: dict = {"window": None, "annual_moves": {}, "event_house_hits": [],
                 "gate_open": False, "lk_sleeping": []}
    planets = (chart_data or {}).get("planets") or {}

    # LK sleeping (Definition 3) — independent of birthday math
    try:
        from antar_engine.lk_trigger import is_sleeping
        natal = {p: {"house": d.get("house"), "sign": d.get("sign")}
                 for p, d in planets.items()
                 if isinstance(d, dict) and d.get("house")}
        out["lk_sleeping"] = sorted(p for p in natal if is_sleeping(p, natal))
    except Exception as e:
        logger.warning("[evidence] lk sleeping failed: %s", e)

    if not born:
        return out
    try:
        from antar_engine.varshaphal_table import get_annual_house
    except Exception:
        return out

    age = (today - born).days // 365
    try:
        last_bday = born.replace(year=today.year)
    except ValueError:
        last_bday = born.replace(year=today.year, day=28)
    if last_bday > today:
        last_bday = last_bday.replace(year=last_bday.year - 1)
    out["window"] = {"start": _iso(last_bday),
                     "end": _iso(last_bday.replace(year=last_bday.year + 1))}

    for p, d in planets.items():
        nh = d.get("house") if isinstance(d, dict) else None
        if nh and 1 <= nh <= 12:
            ah = get_annual_house(nh, age)
            hit = ah in event_houses
            out["annual_moves"][p] = {"natal_house": nh, "annual_house": ah,
                                      "hits_event_house": hit,
                                      "sleeping": p in out["lk_sleeping"]}
            if hit:
                out["event_house_hits"].append(p)
    out["gate_open"] = bool(out["event_house_hits"])
    return out


# ── main assembler ──────────────────────────────────────────────────────────

def build_whole_board(chart_data: dict, jaimini_data, dashas: dict,
                      birth_date, concern: str,
                      current_date: Optional[date] = None,
                      inception: Optional[dict] = None,
                      dt_horizon_months: int = 24,
                      dt_positions: Optional[dict] = None) -> dict:
    """
    Assemble the deterministic whole-board evidence block for one chart and
    one concern. Pure facts; JSON-serializable; no verdict, no window choice.
    `jaimini_data` is accepted for API compatibility but NEVER read for
    current periods (staleness rule). `dt_positions` ({planet: sign_idx})
    overrides the ephemeris for the DT layer (tests / pre-computed state);
    window scans are skipped when supplied.
    """
    today = current_date or date.today()
    chart_data = _safe_json(chart_data)
    planets = chart_data.get("planets") or {}
    notes: list[str] = []

    event = CONCERN_TO_EVENT.get(concern or "general", "general")
    spec = EVENT_MAP[event]
    event_houses = spec["houses"]
    lagna_idx = _lagna_idx(chart_data)

    if spec.get("low_confidence"):
        notes.append(spec["low_confidence"])
    notes.append("lk_trigger Rahu=MEAN_NODE vs transits TRUE_NODE — on record, "
                 "no DT impact (founder scope note)")

    # ── divisionals: event vargas + D9 alongside everything (strength-test)
    divisions = sorted({d for d in spec["divisions"] if d != 1} | {9})
    d_charts = get_all_d_charts(chart_data, divisions) if planets else {}
    d_charts["d1"] = get_d1_from_chart_data(chart_data) if planets else {}
    if 11 in divisions:
        notes.append("D11 uses the calculator's generic divisional mapping "
                     "(no dedicated Labhamsa rule yet)")
    if 30 in divisions:
        notes.append("D30 uses the calculator's simplified odd/even mapping "
                     "(not classical unequal-degree Trimshamsha)")

    divisional_out = {}
    for key, chart in d_charts.items():
        divisional_out[key] = {
            p: {"sign": v.get("sign"), "dignity": v.get("strength")}
            for p, v in chart.items()
        }

    # ── houses from lagna: lord + occupants for ALL 12 (whole chart)
    occ: dict[int, list[str]] = {}
    for p, d in planets.items():
        h = d.get("house") if isinstance(d, dict) else None
        if isinstance(h, int):
            occ.setdefault(h, []).append(p)
    houses_from_lagna = {}
    for h in range(1, 13):
        hsign = SIGNS[(lagna_idx + h - 1) % 12]
        lord = SIGN_LORDS[hsign]
        houses_from_lagna[h] = {
            "sign": hsign, "lord": lord,
            "lord_sign": (planets.get(lord) or {}).get("sign"),
            "lord_house": (planets.get(lord) or {}).get("house"),
            "occupants": occ.get(h, []),
            "tags": _house_tags(h),
            "event_house": h in event_houses,
        }

    # ── dasha tree (Vimshottari MD-AD-PD-SD via phase_analyzer chain)
    vim = _vimshottari_block(dashas, chart_data, lagna_idx, event_houses, today)
    if vim.get("pd") is None and vim.get("md") is not None:
        notes.append("PD/SD unavailable for this chart "
                     f"(tree source: {vim.get('source')})")

    # ── chara: jaimini_engine live (MD-sign-as-lagna + karakas)
    chara = _chara_block(dashas, chart_data, birth_date, today)

    # ── yogas (mechanical detectors; key casing fixed in yoga_engine)
    yogas_out = []
    try:
        from antar_engine.yoga_engine import detect_yogas_for_question
        yoga_domain = _YOGA_DOMAIN.get(event, "funding")
        for y in detect_yogas_for_question(yoga_domain, chart_data, d_charts) or []:
            if y.get("present"):
                yogas_out.append({k: y.get(k) for k in
                                  ("name", "strength", "description", "timing_note")})
    except Exception as e:
        logger.warning("[evidence] yoga detection failed: %s", e)
        notes.append("yoga detection unavailable")

    # ── varshphal gate + LK sleeping
    varsh = _varshphal_block(chart_data, birth_date, event_houses, today)

    # ── Double Transit state (classical + functional) + windows
    dt_out: dict = {}
    try:
        d9_chart = d_charts.get("d9") or {}
        extra = []
        for x in spec.get("extra_dt_planets", []):
            if x == "AmK":
                amk = next((k["planet"] for k in chara.get("karakas", [])
                            if k.get("abbr") == "AmK"), None)
                if amk:
                    extra.append(amk)
            else:
                extra.append(x)

        md_lord = (vim.get("md") or {}).get("lord")
        primary_lord = houses_from_lagna[event_houses[0]]["lord"]
        functional_pair = None
        if md_lord and md_lord != primary_lord:
            functional_pair = (primary_lord, md_lord)

        dt_out = dt.dt_state_for_event(
            chart_data, event_houses, today,
            d9=d9_chart, extra_planets=extra or None,
            functional_pair=functional_pair,
            positions=dt_positions,
        )
        # forward windows: when does the trigger form (or repeat)?
        if dt_positions is None:
            moon_targets = dt_out["frames"]["moon"]["targets"]
            dt_out["forming_windows"] = dt.dt_forming_windows(
                moon_targets, today, months=dt_horizon_months)
            if dt_out.get("classical_verdict") in ("fires", "likely"):
                dt_out["mars_narrowing_windows"] = dt.mars_trigger_windows(
                    moon_targets, today, months=12)
    except Exception as e:
        logger.warning("[evidence] double transit failed: %s", e)
        notes.append("double transit unavailable (ephemeris error)")

    # ── promise vs trigger (the spec's mechanical rule, stated as facts)
    dasha_promise = bool(vim["promise"]["md_connects"] or vim["promise"]["ad_connects"])
    promise_vs_trigger = {
        "dasha_promise": dasha_promise,
        "dt_trigger": dt_out.get("classical_verdict", "unknown"),
        "varshphal_gate_open": varsh.get("gate_open", False),
        "rule": "promise without DT = coming-not-yet; DT without promise = "
                "noise-ignore; both = fires; varshphal gates THIS year",
    }

    return {
        "spec": "event-prediction-v2/whole-board",
        "generated": {"date": today.isoformat(), "concern": concern,
                      "event": event, "event_houses": event_houses,
                      "divisions": [f"d{d}" for d in sorted({1} | set(divisions))]},
        "lagna": {"sign": SIGNS[lagna_idx]},
        "moon": {"sign": (planets.get("Moon") or {}).get("sign"),
                 "nakshatra": (planets.get("Moon") or {}).get("nakshatra")},
        "divisionals": divisional_out,
        "houses_from_lagna": houses_from_lagna,
        "vimshottari": vim,
        "chara": chara,
        "yogas_present": yogas_out,
        "varshphal": varsh,
        "double_transit": dt_out,
        "promise_vs_trigger": promise_vs_trigger,
        "inception": inception or None,
        "notes": notes,
    }
