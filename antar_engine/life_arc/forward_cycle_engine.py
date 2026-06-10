"""
antar_engine/life_arc/forward_cycle_engine.py
=============================================
Forward-predictive engine for the Cycle tab. Produces:
    {"verdict": str, "arc": {...}, "cycle_timeline": [now, sub_chapter, turn, new_chapter]}

DOCTRINE — gated ECS (Cowork brief 2026-06-10):
    ECS = D_gate × Varga_mult × amplifier

  D_gate ∈ [0,1]
      Linkage between the period lord (AD or PD lord) and the event's target
      house in D1: ownership +0.40, occupation +0.30, aspect +0.20, plus a
      dual-system +0.20 bonus when Chara dasha rashi-lord ALSO links the same
      house. D_gate == 0 → event removed from the candidate set entirely. This
      is the gate that kills transit-only false fires.

  Varga_mult ∈ [0.3, 1.15]   (Tier 1 stub: 1.0 always)
      Tier 2 will swap in D9 for relationship events / D10 for career events.
      Debilitated → suppress (<1), vargottama/exalted → boost (>1).

  amplifier ∈ [0,1]   (saturating)
      amplifier = 1 − (1−karaka_match)(1−double_transit)(1−varshphal)
      karaka_match    ∈ {0, 1.0}        — period lord IS the event's karaka
      double_transit  ∈ {0, 0.3, 0.7, 1.0} — Lahiri-gated DT at window midpoint
      varshphal       = 0.0             — Tier 3, deferred

Conviction:
    ECS ≥ 0.85 → "high"  (BUT clamped to "medium" while Varga_mult is stubbed)
    0.55 ≤ ECS < 0.85 → "medium"
    ECS < 0.55 → "subtle" — theme only, no named event emitted

Voice contract — same gate as the 5 prediction surfaces:
    Planet-free. No sign / house number / Sanskrit / engine name in any
    user-facing string. Period lords (Saturn, Rahu...) never surface — user
    sees themes + dates only.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from antar_engine import vimsottari, constants

from antar_engine.life_arc.event_taxonomy import (
    EVENT_TAXONOMY,
    event_target_houses,
    event_category,
    event_karaka_planet,
    event_title,
    KARAKA_DOMAIN_MAP,
)


# ─── tier-1 displayed-conviction clamp ───────────────────────────────────────
# While Varga_mult is stubbed to 1.0 we deliberately under-promise.
# A D1-only "high" is exactly the marriage-the-navamsha-denies failure.
TIER1_DISPLAY_CAP = "medium"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# Graha drishti as SIGN OFFSETS from the occupied sign (matches double_transit).
SIGN_ASPECT_OFFSETS = {
    "Jupiter": (0, 4, 6, 8),
    "Saturn":  (0, 2, 6, 9),
    "Mars":    (0, 3, 6, 7),
    "Rahu":    (0, 4, 6, 8),
    "Ketu":    (0, 4, 6, 8),
}
_DEFAULT_OFFSETS = (0, 6)

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ─── month-of-month phrasing (early / mid- / late) ───────────────────────────

def _month_phrase(d: datetime) -> str:
    """'Sep 2026' base; 'early Sep 2026' / 'late Sep 2026' / 'mid-Sep 2026'
    when day-of-month sits clearly in the third of the month."""
    base = f"{MONTH_ABBR[d.month - 1]} {d.year}"
    day = d.day
    if day <= 10:
        return f"early {base}"
    if day >= 20:
        return f"late {base}"
    return f"mid-{base}"


def _plain_month(d: datetime) -> str:
    return f"{MONTH_ABBR[d.month - 1]} {d.year}"


# ─── chart-data utilities ───────────────────────────────────────────────────

def _lagna_sign_idx(chart_data: dict) -> int:
    lagna = chart_data.get("lagna") or {}
    if isinstance(lagna, dict):
        si = lagna.get("sign_index")
        if isinstance(si, int):
            return si % 12
        nm = lagna.get("sign")
        if isinstance(nm, str) and nm in SIGNS:
            return SIGNS.index(nm)
    return 0


def _planet_sign_idx(chart_data: dict, planet: str) -> Optional[int]:
    pd = (chart_data.get("planets") or {}).get(planet) or {}
    if not isinstance(pd, dict):
        return None
    si = pd.get("sign_index")
    if isinstance(si, int):
        return si % 12
    nm = pd.get("sign")
    if isinstance(nm, str) and nm in SIGNS:
        return SIGNS.index(nm)
    return None


def _house_from_lagna(sign_idx: int, lagna_idx: int) -> int:
    """1-indexed house, 1..12."""
    return ((sign_idx - lagna_idx + 12) % 12) + 1


def _planet_owns_houses(planet: str, lagna_idx: int) -> List[int]:
    """Houses (1..12) ruled by `planet` from this lagna. Nodes own nothing."""
    if planet in ("Rahu", "Ketu"):
        return []
    out: List[int] = []
    for h in range(1, 13):
        sign_idx = (lagna_idx + h - 1) % 12
        if SIGN_LORD.get(SIGNS[sign_idx]) == planet:
            out.append(h)
    return out


def _planet_occupies_house(planet: str, chart_data: dict, lagna_idx: int) -> Optional[int]:
    si = _planet_sign_idx(chart_data, planet)
    if si is None:
        return None
    return _house_from_lagna(si, lagna_idx)


def _planet_aspects_houses(planet: str, chart_data: dict, lagna_idx: int) -> List[int]:
    """Houses graha-drishti'd by `planet` from its natal sign."""
    si = _planet_sign_idx(chart_data, planet)
    if si is None:
        return []
    offsets = SIGN_ASPECT_OFFSETS.get(planet, _DEFAULT_OFFSETS)
    return sorted({_house_from_lagna((si + o) % 12, lagna_idx) for o in offsets})


# ─── structured periods (current + next AD/PD/MD) ────────────────────────────

def _struct_period(p: dict) -> dict:
    """Slim a vimsottari period to the fields the engine uses."""
    return {
        "lord":  p.get("lord"),
        "start": p.get("start_datetime"),
        "end":   p.get("end_datetime"),
    }


def _pds_within(ad: dict) -> List[dict]:
    """Same proportional logic as phase_analyzer._compute_pratyantardashas."""
    seq = constants.VIMSOTTARI_SEQUENCE
    years_map = constants.VIMSOTTARI_YEARS
    ad_lord = ad["lord"]
    start_idx = seq.index(ad_lord)
    total = (ad["end_datetime"] - ad["start_datetime"]).total_seconds()
    pds: List[dict] = []
    cur = ad["start_datetime"]
    for i in range(9):
        lord = seq[(start_idx + i) % 9]
        dur = total * (years_map[lord] / 120.0)
        end = cur + timedelta(seconds=dur)
        pds.append({"lord": lord, "start_datetime": cur, "end_datetime": end})
        cur = end
    return pds


def get_cycle_periods(chart_data: dict, birth_jd: float,
                      now: Optional[datetime] = None) -> Optional[dict]:
    """
    Return structured current_md / current_ad / current_pd / next_ad / next_md
    with started+ends datetimes. The brief's contract.

    Returns None if no active MD found (chart's dasha range exceeded).
    """
    now = now or _now_utc()
    result = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
    mds = result.get("mahadashas") or []
    ads = result.get("antardashas") or []
    if not mds:
        return None

    cur_md_idx = None
    for i, md in enumerate(mds):
        if md["start_datetime"] <= now < md["end_datetime"]:
            cur_md_idx = i
            break
    if cur_md_idx is None:
        return None

    current_md = mds[cur_md_idx]
    next_md = mds[cur_md_idx + 1] if cur_md_idx + 1 < len(mds) else None

    md_ads = [a for a in ads
              if a.get("parent_lord") == current_md["lord"]
              and a["start_datetime"] >= current_md["start_datetime"]
              and a["end_datetime"] <= current_md["end_datetime"] + timedelta(seconds=1)]
    md_ads.sort(key=lambda a: a["start_datetime"])

    cur_ad_idx = None
    for i, ad in enumerate(md_ads):
        if ad["start_datetime"] <= now < ad["end_datetime"]:
            cur_ad_idx = i
            break

    current_ad = md_ads[cur_ad_idx] if cur_ad_idx is not None else None
    next_ad = (md_ads[cur_ad_idx + 1]
               if cur_ad_idx is not None and cur_ad_idx + 1 < len(md_ads)
               else None)

    current_pd = None
    if current_ad:
        pds = _pds_within(current_ad)
        for pd in pds:
            if pd["start_datetime"] <= now < pd["end_datetime"]:
                current_pd = pd
                break

    return {
        "current_md": _struct_period(current_md),
        "current_ad": _struct_period(current_ad) if current_ad else None,
        "current_pd": _struct_period(current_pd) if current_pd else None,
        "next_ad":    _struct_period(next_ad) if next_ad else None,
        "next_md":    _struct_period(next_md) if next_md else None,
    }


# ─── D_gate ─────────────────────────────────────────────────────────────────

def _linkage(planet: str, target_houses: List[int],
             chart_data: dict, lagna_idx: int) -> float:
    if not planet or not target_houses:
        return 0.0
    owns = set(_planet_owns_houses(planet, lagna_idx))
    occ_h = _planet_occupies_house(planet, chart_data, lagna_idx)
    aspects = set(_planet_aspects_houses(planet, chart_data, lagna_idx))
    tset = set(target_houses)
    score = 0.0
    if owns & tset:
        score += 0.40
    if occ_h and occ_h in tset:
        score += 0.30
    if aspects & tset:
        score += 0.20
    return min(score, 1.0)


def d_gate(period_lord: str, event_type: str,
           chart_data: dict, chara_rashi_lord: Optional[str] = None) -> float:
    """
    Necessary precondition. 0.0 → event removed from candidate set.
    Dual-system +0.20 bonus when Chara dasha rashi-lord also links the house.
    """
    target_houses = event_target_houses(event_type)
    if not target_houses:
        return 0.0
    lagna_idx = _lagna_sign_idx(chart_data)
    base = _linkage(period_lord, target_houses, chart_data, lagna_idx)
    if base <= 0:
        return 0.0
    if chara_rashi_lord and chara_rashi_lord != period_lord:
        ch = _linkage(chara_rashi_lord, target_houses, chart_data, lagna_idx)
        if ch > 0:
            base = min(base + 0.20, 1.0)
    return base


# ─── Varga_mult — Tier 1 STUB (returns 1.0) ─────────────────────────────────

def varga_multiplier(event_type: str, period_lord: str,
                     chart_data: dict,
                     d9: Optional[dict] = None,
                     d10: Optional[dict] = None) -> float:
    """
    Tier 2 hook: D9 for relationship events, D10 for career events.
    Tier 1 returns 1.0 — neutral — so the rest of the engine drops in
    Tier 2 with zero code rewrite.
    """
    return 1.0


# ─── amplifier ──────────────────────────────────────────────────────────────

def _karaka_match(period_lord: str, event_type: str, chart_data: dict) -> float:
    """1.0 when period_lord IS the classical karaka of the event. Also fires
    when the 7-karaka assignment from jaimini_engine ties period_lord to the
    event's domain."""
    if not period_lord:
        return 0.0
    if period_lord == event_karaka_planet(event_type):
        return 1.0
    # Look up the 7-karaka assignment (AmK/DK/GK/...) for period_lord
    try:
        from antar_engine.jaimini_engine import compute_7_karakas, Planet
        planets_raw = chart_data.get("planets") or {}
        planets: Dict[str, Any] = {}
        for nm, pdata in planets_raw.items():
            if not isinstance(pdata, dict):
                continue
            planets[nm] = Planet(
                name=nm,
                sign=pdata.get("sign_index", 0),
                degree=pdata.get("longitude", 0.0),
                degree_in_sign=pdata.get("degree", 0.0),
                retrograde=pdata.get("retrograde", False),
                nakshatra=pdata.get("nakshatra", ""),
            )
        karakas = compute_7_karakas(planets)
        for k in karakas:
            if k.planet == period_lord:
                domains = KARAKA_DOMAIN_MAP.get(k.karaka) or ()
                if event_category(event_type) in domains:
                    return 1.0
                break
    except Exception:
        pass
    return 0.0


def _double_transit_score(event_type: str, chart_data: dict,
                          window_midpoint: date) -> float:
    """Saturn+Jupiter DT on event target houses at window midpoint.
    fires=1.0 / likely=0.7 / weak=0.3 / none=0. Lahiri-hardcoded inside
    double_transit.sidereal_sign_indices()."""
    target_houses = event_target_houses(event_type)
    if not target_houses:
        return 0.0
    try:
        from antar_engine.double_transit import dt_state_for_event
        state = dt_state_for_event(chart_data, target_houses, window_midpoint)
        verdict = (state or {}).get("classical_verdict") or "none"
        return {"fires": 1.0, "likely": 0.7, "weak": 0.3, "none": 0.0}.get(verdict, 0.0)
    except Exception:
        return 0.0


def _varshphal_score(event_type: str, chart_data: dict,
                     window_midpoint: date) -> float:
    """Tier 3 — deferred."""
    return 0.0


def amplifier(period_lord: str, event_type: str, chart_data: dict,
              window_midpoint: date) -> float:
    k = _karaka_match(period_lord, event_type, chart_data)
    dt = _double_transit_score(event_type, chart_data, window_midpoint)
    vp = _varshphal_score(event_type, chart_data, window_midpoint)
    # Saturating: 1 − ∏(1 − xᵢ). Confirmations never exceed 1.
    return 1.0 - (1.0 - k) * (1.0 - dt) * (1.0 - vp)


# ─── conviction mapping ─────────────────────────────────────────────────────

def _conviction(ecs: float) -> str:
    if ecs >= 0.85:
        raw = "high"
    elif ecs >= 0.55:
        raw = "medium"
    else:
        raw = "subtle"
    # Tier-1 displayed cap: a D1-only "high" is the marriage-the-navamsha-denies
    # failure. Until Varga_mult is live, raw=="high" is displayed as TIER1_DISPLAY_CAP.
    if raw == "high":
        return TIER1_DISPLAY_CAP
    return raw


# ─── leak gate ──────────────────────────────────────────────────────────────

import re as _re

_LEAK_RX = _re.compile(
    r"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu|"
    r"Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|"
    r"Capricorn|Aquarius|Pisces|"
    r"MD|AD|PD|SD|antardasha|mahadasha|pratyantardasha|dasha|"
    r"nakshatra|navamsa|navamsha|jaimini|vimshottari|vimsottari|chara|"
    r"lagna|karaka|graha|rashi|atmakaraka|amatyakaraka|darakaraka)\b"
    r"|\b\d+(?:st|nd|rd|th)\s+house\b"
)

_VOWELS = ("a", "e", "i", "o", "u")


def _an_article(text: str) -> str:
    """Replace 'A <vowel-word>' with 'An <vowel-word>' anywhere in the string."""
    if not text:
        return text
    return _re.sub(r"\bA (?=[aeiouAEIOU])", "An ", text)


def _scrub_leaks(text: str) -> str:
    """Final defense-in-depth: any leaked planet/sign/house/Sanskrit token
    becomes 'this period' (verb-safe substitute). Always followed by _an_article."""
    if not isinstance(text, str) or not text:
        return text
    cleaned = _LEAK_RX.sub("this period", text)
    # Collapse any double spaces from substitution
    cleaned = _re.sub(r"\s{2,}", " ", cleaned)
    return _an_article(cleaned).strip()


# ─── label formatters ───────────────────────────────────────────────────────

def _when_label(kind: str, end_dt: datetime) -> str:
    if not end_dt:
        return ""
    if kind == "now":
        return f"until {_month_phrase(end_dt)}"
    if kind == "sub_chapter":
        return f"through {_plain_month(end_dt)}"
    if kind == "turn":
        return f"around {_month_phrase(end_dt)}"
    if kind == "new_chapter":
        return f"new chapter {_plain_month(end_dt)}"
    return _plain_month(end_dt)


def _window_label(start: datetime, end: datetime) -> str:
    if not start or not end:
        return ""
    mid = start + (end - start) / 2
    return f"around {_month_phrase(mid)}"


# ─── verdict + bodies + arc ─────────────────────────────────────────────────

def _condition(planet: str, chart_data: dict) -> str:
    """exalted / debilitated / own sign / mixed — same logic as
    phase_analyzer._assess_lord_condition, kept local so the forward engine
    has no cross-module dependency on internal helpers."""
    if not planet:
        return "mixed"
    pd = (chart_data.get("planets") or {}).get(planet) or {}
    si = pd.get("sign_index", -99)
    if not isinstance(si, int):
        return "mixed"
    exalt = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
             "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7}
    debil = {"Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
             "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1}
    own = {"Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
           "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
           "Rahu": [10], "Ketu": [7]}
    if si == exalt.get(planet, -1):
        return "exalted"
    if si == debil.get(planet, -1):
        return "debilitated"
    if si in own.get(planet, []):
        return "own sign"
    return "mixed"


def _verdict_line(current_ad_lord: str, top_event_type: Optional[str],
                  chart_data: dict) -> str:
    """One-liner, planet-free, verdict-first. Tone from AD-lord condition
    only (planet name never surfaces). Life-noun from the top event's
    primary target house."""
    cond = _condition(current_ad_lord, chart_data)
    tone_map = {
        "exalted":     "Steady ground",
        "own sign":    "Steady ground",
        "debilitated": "Slow build — protect the basics",
        "mixed":       "A mixed stretch, with one clear lane",
    }
    tone = tone_map.get(cond, "A mixed stretch, with one clear lane")
    life_clause = ""
    if top_event_type:
        houses = event_target_houses(top_event_type)
        if houses:
            try:
                from antar_engine.house_significations import HOUSE_SIGNIFICATIONS
                theme = (HOUSE_SIGNIFICATIONS.get(houses[0]) or {}).get("theme", "")
                if theme:
                    life_clause = f" — {theme} gets tested before it gets paid"
            except Exception:
                pass
    line = f"{tone}{life_clause}."
    return _scrub_leaks(line)


def _node_body(kind: str, current_ad_lord: str, top_event_type: Optional[str],
               chart_data: dict) -> str:
    """Plain prose body for each node. Verdict-first, one orientation
    action where the brief calls for it (now / sub_chapter)."""
    cond = _condition(current_ad_lord, chart_data)
    base = {
        "now":          "The nearest, tightest stretch — what you do now sets the tone for the months that follow.",
        "sub_chapter":  "A longer phase nested inside the chapter. Slow, deliberate moves compound here.",
        "turn":         "The tone shifts. Same chapter, different texture — adjust what you commit to.",
        "new_chapter":  "A new long chapter opens. Different ground, different rules.",
    }.get(kind, "")
    action = ""
    if kind in ("now", "sub_chapter") and top_event_type:
        houses = event_target_houses(top_event_type)
        if houses:
            try:
                from antar_engine.house_significations import HOUSE_SIGNIFICATIONS, _norm_dir
                _ = _norm_dir  # imported for completeness; not strictly needed here
                direction = "positive" if cond in ("exalted", "own sign") else "adverse"
                sig = HOUSE_SIGNIFICATIONS.get(houses[0]) or {}
                phrase = sig.get(direction) or sig.get("positive") or ""
                if phrase:
                    action = f" Your move: focus on {phrase}."
            except Exception:
                pass
    return _scrub_leaks(base + action)


def _node_title(kind: str) -> str:
    return {
        "now":          "Right now",
        "sub_chapter":  "The phase you're in",
        "turn":         "A turn ahead",
        "new_chapter":  "A new chapter",
    }.get(kind, kind)


def _arc_block(current_md: dict, next_md: Optional[dict], now: datetime) -> dict:
    cm_start = current_md["start"]
    cm_end = current_md["end"]
    nm_start = (next_md or {}).get("start") or cm_end
    try:
        total = (cm_end - cm_start).total_seconds()
        elapsed = (now - cm_start).total_seconds()
        pct = max(0.0, min(1.0, elapsed / total)) if total > 0 else 0.0
    except Exception:
        pct = 0.0
    return {
        "began_label":  f"Began {cm_start.year}",
        "here_label":   "You're here",
        "end_label":    f"New chapter {_plain_month(nm_start)}",
        "pct_elapsed":  round(pct, 2),
    }


# ─── event candidate generation per node ────────────────────────────────────

def _events_for_node(period_lord: str, window_start: datetime,
                     window_end: datetime, chart_data: dict,
                     chara_rashi_lord: Optional[str]) -> List[dict]:
    """Enumerate the EVENT_TAXONOMY, gate by D_gate, rank by ECS, format.
    Subtle (ECS<0.55) events emit no named entry — theme only."""
    if not period_lord or not window_start or not window_end:
        return []
    mid_date = (window_start + (window_end - window_start) / 2).date()
    out: List[Tuple[float, str, dict]] = []
    for event_type in EVENT_TAXONOMY.keys():
        dg = d_gate(period_lord, event_type, chart_data, chara_rashi_lord)
        if dg <= 0:
            continue
        vm = varga_multiplier(event_type, period_lord, chart_data)
        amp = amplifier(period_lord, event_type, chart_data, mid_date)
        ecs = dg * vm * amp
        conv = _conviction(ecs)
        if conv == "subtle":
            continue
        out.append((ecs, event_type, {
            "_event_type": event_type,  # internal — stripped before emit
            "title":        _scrub_leaks(event_title(event_type)),
            "category":     event_category(event_type),
            "window_label": _window_label(window_start, window_end),
            "conviction":   conv,
        }))
    out.sort(key=lambda x: -x[0])
    # Cap at 2 per node — surface is meant to land, not overwhelm.
    return [e for _ecs, _et, e in out[:2]]


# ─── top-level builder ──────────────────────────────────────────────────────

def _chara_rashi_lord(chart_data: dict, birth_date_str: str,
                      now: datetime) -> Optional[str]:
    """Look up Jaimini Chara dasha current rashi → its sign-lord."""
    try:
        from antar_engine.jaimini_engine import (
            compute_chara_dasha, get_current_dasha, Planet,
        )
        lagna_idx = _lagna_sign_idx(chart_data)
        planets_raw = chart_data.get("planets") or {}
        planets: Dict[str, Any] = {}
        for nm, pdata in planets_raw.items():
            if not isinstance(pdata, dict):
                continue
            planets[nm] = Planet(
                name=nm,
                sign=pdata.get("sign_index", 0),
                degree=pdata.get("longitude", 0.0),
                degree_in_sign=pdata.get("degree", 0.0),
                retrograde=pdata.get("retrograde", False),
                nakshatra=pdata.get("nakshatra", ""),
            )
        bd = birth_date_str[:10].split("-")
        birth_dt = datetime(int(bd[0]), int(bd[1]), int(bd[2]))
        all_mds = compute_chara_dasha(lagna_idx, planets, birth_dt, num_cycles=3)
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        cur_md, _ = get_current_dasha(all_mds, now_naive)
        if cur_md and getattr(cur_md, "sign_name", None) in SIGNS:
            return SIGN_LORD.get(cur_md.sign_name)
    except Exception:
        return None
    return None


def build_forward_cycle(chart_data: dict, birth_jd: float,
                        now: Optional[datetime] = None,
                        birth_date_str: str = "",
                        language: str = "en") -> dict:
    """
    Returns {"verdict": str, "arc": {...}, "cycle_timeline": [...]} or a
    cleanly-empty stub so a forward-engine bug never tanks the rest of
    /life-arc. language is accepted for forward compat (Tier 1 produces
    English templates; the existing translate_response layer handles ES).
    """
    now = now or _now_utc()
    empty = {"verdict": "", "arc": {}, "cycle_timeline": []}
    try:
        periods = get_cycle_periods(chart_data, birth_jd, now)
    except Exception:
        return empty
    if not periods or not periods.get("current_md"):
        return empty

    current_md = periods["current_md"]
    current_ad = periods.get("current_ad")
    current_pd = periods.get("current_pd")
    next_ad = periods.get("next_ad")
    next_md = periods.get("next_md")

    # Short-MD fallback: if AD < ~12 months, drop sub_chapter to PD-grain
    short_md = False
    if current_ad and current_ad["start"] and current_ad["end"]:
        if (current_ad["end"] - current_ad["start"]).days < 365:
            short_md = True

    chara_lord = _chara_rashi_lord(chart_data, birth_date_str or "1970-01-01", now)

    # Build nodes
    nodes: List[dict] = []

    # now = current PD (Rao sharpener)
    if current_pd and current_pd["lord"]:
        pd_events = _events_for_node(
            current_pd["lord"], current_pd["start"], current_pd["end"],
            chart_data, chara_lord,
        )  # 'now' node carries no events by brief — condition-only framing
        top_now_evt = pd_events[0].get("title") if pd_events else None  # for tone only
        _ = top_now_evt  # suppress lint; verdict pulls from sub_chapter top
        nodes.append({
            "kind":       "now",
            "when_label": _when_label("now", current_pd["end"]),
            "title":      _node_title("now"),
            "body":       _node_body("now", (current_ad or {}).get("lord"),
                                     None, chart_data),
            "events":     [],
        })

    # sub_chapter = current AD (or, in short-MD fallback, current PD again — but
    # we already showed it as 'now'; in that case use next_ad as the visible AD).
    sc_period = current_ad
    if short_md and next_ad:
        sc_period = next_ad
    sc_events: List[dict] = []
    if sc_period and sc_period["lord"]:
        sc_events = _events_for_node(
            sc_period["lord"], sc_period["start"], sc_period["end"],
            chart_data, chara_lord,
        )
        nodes.append({
            "kind":       "sub_chapter",
            "when_label": _when_label("sub_chapter", sc_period["end"]),
            "title":      _node_title("sub_chapter"),
            "body":       _node_body("sub_chapter", sc_period["lord"],
                                     sc_events[0].get("_event_type") if sc_events else None,
                                     chart_data),
            "events":     [{k: v for k, v in e.items() if k != "_event_type"}
                           for e in sc_events],
        })

    # turn = next AD boundary
    if next_ad and next_ad["lord"]:
        turn_events = _events_for_node(
            next_ad["lord"], next_ad["start"], next_ad["end"],
            chart_data, chara_lord,
        )
        nodes.append({
            "kind":       "turn",
            "when_label": _when_label("turn", next_ad["start"]),
            "title":      _node_title("turn"),
            "body":       _node_body("turn", next_ad["lord"], None, chart_data),
            "events":     [{k: v for k, v in e.items() if k != "_event_type"}
                           for e in turn_events],
        })

    # new_chapter = next MD
    if next_md and next_md["lord"]:
        nodes.append({
            "kind":       "new_chapter",
            "when_label": _when_label("new_chapter", next_md["start"]),
            "title":      _node_title("new_chapter"),
            "body":       _node_body("new_chapter", next_md["lord"], None, chart_data),
            "events":     [],
        })

    # Verdict driven by the sub_chapter AD's condition + top sc event noun
    top_sc_event_type = None
    if sc_events:
        # We need event_type back — re-look it up by matching title (cheap, deterministic).
        for et, meta in EVENT_TAXONOMY.items():
            if meta.get("title") == sc_events[0].get("title"):
                top_sc_event_type = et
                break
    verdict = _verdict_line(
        (current_ad or {}).get("lord") or current_md.get("lord"),
        top_sc_event_type,
        chart_data,
    )

    arc = _arc_block(current_md, next_md, now)

    # Final defense-in-depth scrub on every user-facing string
    for n in nodes:
        n["when_label"] = _scrub_leaks(n.get("when_label", ""))
        n["title"]      = _scrub_leaks(n.get("title", ""))
        n["body"]       = _scrub_leaks(n.get("body", ""))
        for e in (n.get("events") or []):
            e["title"]        = _scrub_leaks(e.get("title", ""))
            e["window_label"] = _scrub_leaks(e.get("window_label", ""))

    return {
        "verdict":        _scrub_leaks(verdict),
        "arc":            arc,
        "cycle_timeline": nodes,
    }
