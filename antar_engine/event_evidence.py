"""
antar_engine/event_evidence.py — whole-board deterministic evidence block.

Event Prediction Engine v2, build-order step 2/4 (2026-06-05).

Python computes the WHOLE board as facts — dasha tree (MD-AD-PD-SD), chara
MD-sign-as-lagna rotation + karakas, divisionals, yogas, varshphal gate,
LK sleeping planets, and the full TRANSIT STATE incl. Double Transit.
NO verdicts, NO timing synthesis, NO prose — the LLM does the combination
reading downstream (build-order step 3). The chart is read whole: every
house's lord + occupants stay visible, never one domain in isolation.

Reuses (never re-implements):
  d_charts_calculator  — divisionals + dignity + house lords
  vimsottari constants — sequence/years for PD/SD subdivision
  varshaphal_table     — annual house movement
  lk_trigger           — sleeping predicate (Definition 3 RCJ-1952)
  yoga_engine          — mechanical yoga detectors
  double_transit       — DT geometry (new, same sprint)

KNOWN DIVERGENCES (flagged, not silently chosen):
  * karakas here rank by DEGREE-WITHIN-SIGN descending (classical / KN Rao);
    karakas.py ranks by absolute longitude — different results possible.
    Board carries ranking_basis so the discrepancy is auditable.
  * D11 uses d_charts_calculator's generic fallback mapping (no dedicated
    Rudramsa/Labhamsa rule in the calculator yet) — noted in board.notes.
  * yoga_engine detectors read d_charts with UPPERCASE keys ("D2") while
    get_all_d_charts returns lowercase ("d2") — callers that pass lowercase
    get silent partial detection. This module passes BOTH key cases.

Internal module: planet/house names here never reach the frontend directly
(output_strips owns user-facing text).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from antar_engine.d_charts_calculator import (
    SIGNS, SIGN_INDEX, SIGN_LORDS,
    get_all_d_charts, get_d1_from_chart_data, _planet_strength,
)
from antar_engine import constants
from antar_engine import double_transit as dt

logger = logging.getLogger(__name__)

VIM_SEQUENCE = constants.VIMSOTTARI_SEQUENCE
VIM_YEARS = constants.VIMSOTTARI_YEARS
KARAKA_NAMES = constants.KARAKA_NAMES   # 1=Atmakaraka … 7=Darakaraka

# ── Event map (spec table, v2 FINAL) ────────────────────────────────────────
# houses are read from the relevant lagna; funding is multi-house BY DESIGN —
# the engine reads ALL and the dasha + DT show which is lit.
EVENT_MAP = {
    "funding":    {"houses": [11, 2, 8, 6], "divisions": [10, 2, 11]},
    "relocation": {"houses": [4, 3, 12],    "divisions": [1, 4]},
    "marriage":   {"houses": [7, 2],        "divisions": [9],
                   "extra_dt_planets": ["Venus"]},
    "career":     {"houses": [10, 6, 11],   "divisions": [10, 9],
                   "extra_dt_planets": ["AmK"]},   # resolved at runtime
    "health":     {"houses": [1, 6, 8],     "divisions": [1, 30]},
    "litigation": {"houses": [6, 8, 12],    "divisions": [1]},
    "general":    {"houses": [10, 11, 2],   "divisions": [10, 9]},
}

# detect_concern vocabulary → spec event
CONCERN_TO_EVENT = {
    "finance": "funding", "funding": "funding", "wealth": "funding",
    "loss": "funding", "speculation": "funding", "money": "funding",
    "career": "career", "business": "career", "education": "career",
    "marriage": "marriage", "love": "marriage", "divorce": "marriage",
    "children": "marriage",
    "health": "health",
    "legal": "litigation",
    "property": "relocation", "foreign": "relocation",
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
    return d.isoformat() if isinstance(d, (date, datetime)) else None


# ── Vimshottari tree: MD-AD from rows, PD-SD computed proportionally ────────

def _sub_periods(parent_lord: str, start: date, end: date) -> list[dict]:
    """Subdivide a period into its 9 sub-periods (sequence starts from the
    parent lord; each sub-lord's share = VIM_YEARS[lord]/120 of the span)."""
    if not (parent_lord in VIM_SEQUENCE and start and end and end > start):
        return []
    span = (end - start).total_seconds()
    out, cursor = [], datetime.combine(start, datetime.min.time())
    idx = VIM_SEQUENCE.index(parent_lord)
    for i in range(9):
        lord = VIM_SEQUENCE[(idx + i) % 9]
        sub_end = cursor + timedelta(seconds=span * VIM_YEARS[lord] / 120.0)
        out.append({"lord": lord, "start": cursor.date(), "end": sub_end.date()})
        cursor = sub_end
    out[-1]["end"] = end   # absorb rounding
    return out


def _containing(periods: list[dict], today: date) -> Optional[dict]:
    for p in periods:
        if p["start"] <= today < p["end"]:
            return p
    return None


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


def _vimshottari_block(dashas, chart_data, lagna_idx, event_houses, today) -> dict:
    md_row = _current_row(dashas, "vimsottari", ("mahadasha", "1"), today)
    ad_row = _current_row(dashas, "vimsottari", ("antardasha", "antar", "2"), today)

    block: dict = {"md": None, "ad": None, "pd": None, "sd": None,
                   "promise": {"md_connects": False, "ad_connects": False, "how": []}}

    planets = (chart_data or {}).get("planets") or {}

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

    if md_row:
        s, e = _win(md_row)
        lord = _lord(md_row)
        block["md"] = {"lord": lord, "start": _iso(s), "end": _iso(e),
                       "profile": _lord_profile(lord, chart_data, lagna_idx)}
        how = _connects(lord)
        if how:
            block["promise"]["md_connects"] = True
            block["promise"]["how"] += how

    if ad_row:
        s, e = _win(ad_row)
        lord = _lord(ad_row)
        block["ad"] = {"lord": lord, "start": _iso(s), "end": _iso(e),
                       "profile": _lord_profile(lord, chart_data, lagna_idx)}
        how = _connects(lord)
        if how:
            block["promise"]["ad_connects"] = True
            block["promise"]["how"] += [f"AD: {h}" for h in how]

        # PD inside the current AD, SD inside the current PD — computed here
        # (dasha_periods stores MD/AD only).
        pds = _sub_periods(lord, s, e)
        cur_pd = _containing(pds, today)
        if cur_pd:
            block["pd"] = {
                "lord": cur_pd["lord"],
                "start": _iso(cur_pd["start"]), "end": _iso(cur_pd["end"]),
                "connects_event": bool(_connects(cur_pd["lord"])),
                "upcoming": [{"lord": p["lord"], "start": _iso(p["start"]),
                              "end": _iso(p["end"]),
                              "connects_event": bool(_connects(p["lord"]))}
                             for p in pds if p["start"] >= today][:4],
            }
            sds = _sub_periods(cur_pd["lord"], cur_pd["start"], cur_pd["end"])
            cur_sd = _containing(sds, today)
            if cur_sd:
                block["sd"] = {"lord": cur_sd["lord"],
                               "start": _iso(cur_sd["start"]),
                               "end": _iso(cur_sd["end"])}
    return block


# ── Chara: MD sign as lagna, karakas in the rotated chart ───────────────────

def _karakas_by_degree_in_sign(planets: dict) -> list[dict]:
    """Classical chara karakas: 7 planets ranked by degree-within-sign DESC.
    (karakas.py ranks by absolute longitude — divergence flagged on the board.)"""
    ranked = []
    for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        d = planets.get(p) or {}
        lng = d.get("longitude")
        deg = (float(lng) % 30.0) if lng is not None else d.get("degree")
        if deg is None:
            continue
        ranked.append((p, float(deg), d.get("sign", "")))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return [{"rank": i + 1, "name": KARAKA_NAMES.get(i + 1, f"Karaka {i+1}"),
             "planet": p, "degree_in_sign": round(deg, 2), "sign": sign}
            for i, (p, deg, sign) in enumerate(ranked)]


_KARAKA_ABBR = {"Atmakaraka": "AK", "Amatyakaraka": "AmK", "Bhratrukaraka": "BK",
                "Matrukaraka": "MK", "Putrakaraka": "PK", "Gnatikaraka": "GK",
                "Darakaraka": "DK"}


def _chara_block(dashas, chart_data, today) -> dict:
    planets = (chart_data or {}).get("planets") or {}
    md_row = _current_row(dashas, "jaimini", ("mahadasha", "1"), today)
    ad_row = _current_row(dashas, "jaimini", ("antardasha", "antar", "2"), today)

    block: dict = {"md_sign": None, "ad_sign": None, "rotated_houses": None,
                   "karakas": [],
                   "ranking_basis": "degree-in-sign desc (classical; "
                                    "karakas.py uses absolute longitude)"}
    if md_row:
        s, e = _win(md_row)
        sign = _lord(md_row)
        if sign in SIGN_INDEX:
            block["md_sign"] = {"sign": sign, "start": _iso(s), "end": _iso(e)}
            md_idx = SIGN_INDEX[sign]

            # every house from MD-lagna: lord + occupants (cross-connections
            # must stay visible — whole-chart rule)
            rotated = {}
            occ: dict[int, list[str]] = {}
            for p in planets:
                si = _planet_sign_idx(planets, p)
                if si is not None:
                    occ.setdefault((si - md_idx) % 12 + 1, []).append(p)
            for h in range(1, 13):
                hsign = SIGNS[(md_idx + h - 1) % 12]
                rotated[h] = {"sign": hsign, "lord": SIGN_LORDS[hsign],
                              "occupants": occ.get(h, []),
                              "tags": _house_tags(h)}
            block["rotated_houses"] = rotated

            # all chara karakas placed in the rotated chart
            for k in _karakas_by_degree_in_sign(planets):
                si = _planet_sign_idx(planets, k["planet"])
                house_from_md = ((si - md_idx) % 12 + 1) if si is not None else None
                k["abbr"] = _KARAKA_ABBR.get(k["name"], k["name"][:3])
                k["house_from_md_lagna"] = house_from_md
                k["dignity"] = _planet_strength(k["planet"], k["sign"])
                k["house_tags"] = _house_tags(house_from_md) if house_from_md else []
                block["karakas"].append(k)

    if ad_row:
        s, e = _win(ad_row)
        block["ad_sign"] = {"sign": _lord(ad_row), "start": _iso(s), "end": _iso(e)}
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
    # dt_positions ({planet: sign_idx}) overrides the ephemeris for the DT
    # layer (tests / pre-computed transit state); window scans are skipped
    # when it is supplied since they need the real ephemeris.
    """
    Assemble the deterministic whole-board evidence block for one chart and
    one concern. Pure facts; JSON-serializable; no verdict, no window choice.
    """
    today = current_date or date.today()
    chart_data = _safe_json(chart_data)
    jaimini_data = _safe_json(jaimini_data)
    planets = chart_data.get("planets") or {}
    notes: list[str] = []

    event = CONCERN_TO_EVENT.get(concern or "general", "general")
    spec = EVENT_MAP[event]
    event_houses = spec["houses"]
    lagna_idx = _lagna_idx(chart_data)

    # ── divisionals: event vargas + D9 alongside everything (strength-test)
    divisions = sorted({d for d in spec["divisions"] if d != 1} | {9})
    d_charts = get_all_d_charts(chart_data, divisions) if planets else {}
    d_charts["d1"] = get_d1_from_chart_data(chart_data) if planets else {}
    if 11 in divisions:
        notes.append("D11 uses the calculator's generic divisional mapping "
                     "(no dedicated Labhamsa rule yet)")

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

    # ── dasha tree (Vimshottari MD-AD-PD-SD)
    vim = _vimshottari_block(dashas, chart_data, lagna_idx, event_houses, today)

    # ── chara: MD-sign-as-lagna + karakas
    chara = _chara_block(dashas, chart_data, today)

    # ── yogas (mechanical detectors; pass BOTH key cases — see header note)
    yogas_out = []
    try:
        from antar_engine.yoga_engine import detect_yogas_for_question
        d_both = dict(d_charts)
        d_both.update({k.upper(): v for k, v in d_charts.items()})
        yoga_domain = _YOGA_DOMAIN.get(event, "funding")
        for y in detect_yogas_for_question(yoga_domain, chart_data, d_both) or []:
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
