"""
antar_engine/double_transit.py — KN Rao Double Transit layer (deterministic).

Event Prediction Engine v2, build-order step 2/4 (2026-06-05).

GEOMETRY (computable, whole-sign / sidereal Lahiri):
  Jupiter aspects the sign it OCCUPIES + 5th, 7th, 9th signs from it  (4 signs)
  Saturn  aspects the sign it OCCUPIES + 3rd, 7th, 10th signs from it (4 signs)
  A sign receiving aspect/occupation from BOTH = Double Transit (DT) on it.

TARGETS (per event, per reference frame):
  the event house's sign, the house LORD's natal (D1) sign, and the lord's
  NAVAMSA (D9) sign — all three are tested, not just the house.

FRAMES:
  primary = from the MOON (Janma Rashi), confirmation = from the LAGNA.
  DEFAULT RULE (founder-confirmed 2026-06-05, confidence-weighter NOT hard
  gate): Moon-only DT = "likely"; Moon + Lagna agree = "fires".
  Lagna-only = "weak". Neither = "none".

CLASSICAL vs FUNCTIONAL (VP Goel refinement):
  classical  = Saturn + Jupiter.
  functional = a config-passed planet pair (event lord / yogakaraka / MD lord),
  same geometry, each planet contributing its own graha-drishti sign set.

WINDOWS:
  dt_forming_windows() scans ahead to find when DT next forms on the targets
  (the deterministic source for "the trigger doesn't form until [window]").
  mars_trigger_windows() narrows with Mars transits; Moon position is exposed
  for day-level narrowing downstream.

NO VERDICTS, NO PROSE — facts only. The LLM reads the combination.
Internal module: planet/house names here never reach the frontend directly
(output_strips owns user-facing text).
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Optional

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# Graha drishti as SIGN OFFSETS from the occupied sign (0 = occupied sign).
# Consistent with aspects_engine.ASPECT_RULES ([5,7,9] etc. as house counts):
# house count n -> offset n-1.
SIGN_ASPECT_OFFSETS = {
    "Jupiter": (0, 4, 6, 8),   # occupied, 5th, 7th, 9th
    "Saturn":  (0, 2, 6, 9),   # occupied, 3rd, 7th, 10th
    "Mars":    (0, 3, 6, 7),   # occupied, 4th, 7th, 8th
    "Rahu":    (0, 4, 6, 8),
    "Ketu":    (0, 4, 6, 8),
}
_DEFAULT_OFFSETS = (0, 6)      # everyone else: occupied + 7th


def aspected_signs(planet: str, sign_idx: int) -> set[int]:
    """Sign indices a transiting planet occupies/aspects (whole-sign)."""
    offsets = SIGN_ASPECT_OFFSETS.get(planet, _DEFAULT_OFFSETS)
    return {(sign_idx + o) % 12 for o in offsets}


# ── ephemeris (sidereal Lahiri, same setup as transits.py / lk_trigger.py) ──

_PLANET_IDS = {
    "Sun": "SUN", "Moon": "MOON", "Mars": "MARS", "Mercury": "MERCURY",
    "Jupiter": "JUPITER", "Venus": "VENUS", "Saturn": "SATURN",
}


def _jd(when: date | datetime) -> float:
    import swisseph as swe
    if isinstance(when, datetime):
        return swe.julday(when.year, when.month, when.day,
                          when.hour + when.minute / 60.0)
    return swe.julday(when.year, when.month, when.day, 12.0)  # noon UT


def sidereal_sign_indices(when: date | datetime,
                          planets: tuple[str, ...]) -> dict[str, int]:
    """Sidereal (Lahiri) sign index 0-11 for the requested planets at `when`.
    Rahu/Ketu via TRUE_NODE — same as transits.get_current_positions."""
    import swisseph as swe
    swe.set_ephe_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe"))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    jd = _jd(when)
    out: dict[str, int] = {}
    for p in planets:
        if p in ("Rahu", "Ketu"):
            lon, _ = swe.calc_ut(jd, swe.TRUE_NODE, flags=flags)
            deg = lon[0] if p == "Rahu" else (lon[0] + 180.0) % 360.0
        elif p in _PLANET_IDS:
            lon, _ = swe.calc_ut(jd, getattr(swe, _PLANET_IDS[p]), flags=flags)
            deg = lon[0]
        else:
            continue
        out[p] = int(deg / 30) % 12
    return out


# ── targets ─────────────────────────────────────────────────────────────────

def build_targets(chart_data: dict, houses: list[int], frame: str,
                  d9: Optional[dict] = None,
                  extra_planets: Optional[list[str]] = None) -> list[dict]:
    """
    DT target set for an event, counted from `frame` ("lagna" or "moon").
    For each event house: the house's sign, the house lord's natal D1 sign,
    and the lord's D9 (navamsa) sign. `extra_planets` adds karaka-style
    targets (e.g. Venus for marriage, AmK planet for career): their D1 + D9
    signs.
    Returns [{"kind", "house", "planet", "sign_index", "sign", "label"}].
    """
    planets = (chart_data or {}).get("planets") or {}
    lagna = (chart_data or {}).get("lagna") or {}
    lagna_idx = lagna.get("sign_index")
    if not isinstance(lagna_idx, int):
        lagna_idx = SIGN_INDEX.get(lagna.get("sign", ""), 0)

    if frame == "moon":
        moon = planets.get("Moon") or {}
        ref_idx = moon.get("sign_index")
        if not isinstance(ref_idx, int):
            ref_idx = SIGN_INDEX.get(moon.get("sign", ""), lagna_idx)
    else:
        ref_idx = lagna_idx

    def _planet_sign_idx(p: str) -> Optional[int]:
        d = planets.get(p) or {}
        si = d.get("sign_index")
        if isinstance(si, int):
            return si % 12
        s = d.get("sign")
        return SIGN_INDEX.get(s) if s in SIGN_INDEX else None

    targets, seen = [], set()

    def _add(kind, sign_idx, house=None, planet=None):
        if sign_idx is None:
            return
        key = (kind, house, planet, sign_idx)
        if key in seen:
            return
        seen.add(key)
        targets.append({
            "kind": kind, "house": house, "planet": planet,
            "sign_index": sign_idx, "sign": SIGNS[sign_idx],
            "label": (f"house {house} ({SIGNS[sign_idx]})" if kind == "house"
                      else f"{planet} {'D9' if kind.endswith('navamsa') else 'natal'} sign {SIGNS[sign_idx]}"),
        })

    for h in houses:
        house_sign_idx = (ref_idx + h - 1) % 12
        _add("house", house_sign_idx, house=h)
        lord = SIGN_LORDS[SIGNS[house_sign_idx]]
        _add("lord_natal", _planet_sign_idx(lord), house=h, planet=lord)
        if d9 and lord in d9 and isinstance(d9[lord].get("sign_index"), int):
            _add("lord_navamsa", d9[lord]["sign_index"], house=h, planet=lord)

    for p in (extra_planets or []):
        _add("karaka_natal", _planet_sign_idx(p), planet=p)
        if d9 and p in d9 and isinstance(d9[p].get("sign_index"), int):
            _add("karaka_navamsa", d9[p]["sign_index"], planet=p)

    return targets


# ── the DT check ────────────────────────────────────────────────────────────

def _pair_hits(targets: list[dict], positions: dict[str, int],
               pair: tuple[str, str]) -> dict:
    """Which targets are under aspect/occupation from BOTH planets of `pair`."""
    a, b = pair
    if a not in positions or b not in positions:
        return {"computable": False, "hits": [], "sets": {}}
    set_a = aspected_signs(a, positions[a])
    set_b = aspected_signs(b, positions[b])
    both = set_a & set_b
    hits = [t for t in targets if t["sign_index"] in both]
    return {
        "computable": True,
        "hits": hits,
        "sets": {
            a: {"sign": SIGNS[positions[a]], "aspects": sorted(SIGNS[i] for i in set_a)},
            b: {"sign": SIGNS[positions[b]], "aspects": sorted(SIGNS[i] for i in set_b)},
        },
    }


def dt_state_for_event(chart_data: dict, houses: list[int],
                       target_date: date | datetime,
                       d9: Optional[dict] = None,
                       extra_planets: Optional[list[str]] = None,
                       functional_pair: Optional[tuple[str, str]] = None,
                       positions: Optional[dict[str, int]] = None) -> dict:
    """
    Full Double Transit state for one event on one date. Deterministic facts:
      classical (Saturn+Jupiter) per frame (moon primary, lagna confirm),
      verdict label per DEFAULT RULE (fires/likely/weak/none),
      optional functional pair, Mars/Moon current positions for narrowing.
    `positions` ({planet: sign_idx}) overrides the ephemeris — for tests and
    for callers that already computed transit state.
    """
    needed = {"Saturn", "Jupiter", "Mars", "Moon"}
    if functional_pair:
        needed |= set(functional_pair)
    if positions is None:
        positions = sidereal_sign_indices(target_date, tuple(sorted(needed)))

    frames = {}
    for frame in ("moon", "lagna"):
        targets = build_targets(chart_data, houses, frame, d9=d9,
                                extra_planets=extra_planets)
        classical = _pair_hits(targets, positions, ("Saturn", "Jupiter"))
        frames[frame] = {
            "targets": targets,
            "classical_hits": classical["hits"],
            "classical_hit": bool(classical["hits"]),
            "aspect_sets": classical["sets"],
        }

    moon_hit = frames["moon"]["classical_hit"]
    lagna_hit = frames["lagna"]["classical_hit"]
    if moon_hit and lagna_hit:
        verdict = "fires"          # both frames agree → certain
    elif moon_hit:
        verdict = "likely"         # Moon-only → likely (default rule)
    elif lagna_hit:
        verdict = "weak"           # Lagna-only, no Janma-rashi support
    else:
        verdict = "none"

    out = {
        "date": (target_date.date() if isinstance(target_date, datetime)
                 else target_date).isoformat(),
        "rule": "confidence-weighter (moon primary, lagna confirm)",
        "classical_verdict": verdict,
        "frames": frames,
        "narrowing": {
            "mars_sign": SIGNS[positions["Mars"]] if "Mars" in positions else None,
            "mars_aspects": (sorted(SIGNS[i] for i in aspected_signs("Mars", positions["Mars"]))
                             if "Mars" in positions else []),
            "moon_sign": SIGNS[positions["Moon"]] if "Moon" in positions else None,
        },
    }

    if functional_pair and functional_pair[0] != functional_pair[1]:
        f_moon = _pair_hits(frames["moon"]["targets"], positions, functional_pair)
        f_lagna = _pair_hits(frames["lagna"]["targets"], positions, functional_pair)
        if f_moon["computable"]:
            fm, fl = bool(f_moon["hits"]), bool(f_lagna["hits"])
            out["functional"] = {
                "pair": list(functional_pair),
                "verdict": ("fires" if fm and fl else "likely" if fm
                            else "weak" if fl else "none"),
                "moon_frame_hits": f_moon["hits"],
                "lagna_frame_hits": f_lagna["hits"],
            }
    return out


# ── forward windows ─────────────────────────────────────────────────────────

def _scan_windows(target_signs: set[int], start: date, months: int,
                  pair: tuple[str, str], step_days: int) -> list[dict]:
    """Step through time; collapse consecutive DT-on-target dates to windows."""
    windows: list[dict] = []
    open_start = None
    last_hit_signs: set[int] = set()
    d = start
    end = start + timedelta(days=int(months * 30.44))
    while d <= end:
        positions = sidereal_sign_indices(d, pair)
        if len(positions) == 2:
            both = (aspected_signs(pair[0], positions[pair[0]])
                    & aspected_signs(pair[1], positions[pair[1]]))
            hit = both & target_signs
        else:
            hit = set()
        if hit and open_start is None:
            open_start, last_hit_signs = d, set(hit)
        elif hit:
            last_hit_signs |= hit
        elif open_start is not None:
            windows.append({"start": open_start.isoformat(),
                            "end": (d - timedelta(days=step_days)).isoformat(),
                            "signs_hit": sorted(SIGNS[i] for i in last_hit_signs)})
            open_start, last_hit_signs = None, set()
        d += timedelta(days=step_days)
    if open_start is not None:
        windows.append({"start": open_start.isoformat(),
                        "end": end.isoformat(), "open_ended": True,
                        "signs_hit": sorted(SIGNS[i] for i in last_hit_signs)})
    return windows


def dt_forming_windows(targets: list[dict], start: date, months: int = 24,
                       pair: tuple[str, str] = ("Saturn", "Jupiter"),
                       step_days: int = 15) -> list[dict]:
    """When does Double Transit form on any target within the horizon?
    Saturn/Jupiter move slowly — 15-day steps resolve month-level windows."""
    return _scan_windows({t["sign_index"] for t in targets}, start, months,
                         pair, step_days)


def mars_trigger_windows(targets: list[dict], start: date, months: int = 12,
                         step_days: int = 3) -> list[dict]:
    """Mars aspect/occupation windows over the targets — narrows the
    Saturn/Jupiter year down toward the month/date (pair Mars with itself
    degenerates, so test Mars alone)."""
    target_signs = {t["sign_index"] for t in targets}
    windows: list[dict] = []
    open_start = None
    d = start
    end = start + timedelta(days=int(months * 30.44))
    while d <= end:
        pos = sidereal_sign_indices(d, ("Mars",))
        hit = bool(pos) and bool(aspected_signs("Mars", pos["Mars"]) & target_signs)
        if hit and open_start is None:
            open_start = d
        elif not hit and open_start is not None:
            windows.append({"start": open_start.isoformat(),
                            "end": (d - timedelta(days=step_days)).isoformat()})
            open_start = None
        d += timedelta(days=step_days)
    if open_start is not None:
        windows.append({"start": open_start.isoformat(),
                        "end": end.isoformat(), "open_ended": True})
    return windows
