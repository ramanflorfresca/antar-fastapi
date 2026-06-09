"""
antar_engine/natal_promise.py
─────────────────────────────
V2.2 Layer 1 — Natal Promise: CAN it happen?

Composes the V2.2 four-pass scoring:

    classical baseline → modern translation → Lal Kitab → archetype/vehicle_fit gate

Each pass adds (or subtracts) deterministic points to a single `raw` score.
The final verdict is one of:

    STRUCTURALLY_SUPPORTED  (raw >= 30)
    NEUTRAL                 (0 <= raw < 30)
    STRUCTURALLY_BLOCKED    (raw < 0)

KEY DESIGN POINTS (per founder brief):
  - Modern translation runs INSIDE this function. A flat classical -30
    for dushthana lord must be recoverable by viparita / strong-6 /
    Rahu-disruptor signatures. A late ±15 overlay can NEVER recover a
    -30; the layers compose at score level, not as a final tweak.
  - Archetype gate runs LAST. Vehicle_fit adds +15 / -20. This is the
    "this chart's promise for THIS vehicle" judgement.
  - Pure function. No LLM. No DB. No network. Same inputs → same output.
  - Never raises. Failure paths return verdict=NEUTRAL with a reason.

PUBLIC API:
  calculate_natal_promise(chart_data, life_area_config, archetype=None)
      → {verdict, score, classical, modern, lk, vehicle_fit, archetype,
         reasoning_technical: [str]}
  vehicle_fit(archetype_name, concern) → "fit" | "neutral" | "mismatch"
  resolve_wealth_archetype(chart_data) → archetype name or None
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────
# Reference tables
# ─────────────────────────────────────────────────────────────────────

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

_SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

# Exaltation signs per planet (classical Parashari).
_EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra", "Rahu": "Taurus", "Ketu": "Scorpio",
}
_DEBILITATION = {p: _SIGNS[(_SIGNS.index(s) + 6) % 12] for p, s in _EXALTATION.items()}

# Own signs.
_OWN_SIGNS = {
    "Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"],
    "Rahu": ["Aquarius", "Gemini"], "Ketu": ["Scorpio", "Sagittarius"],
}

# Friendship (simplified to dignity bucket — not full Tatkalik).
_FRIEND_SIGNS = {
    "Sun":     {"Aries", "Sagittarius", "Cancer", "Scorpio", "Pisces"},
    "Moon":    {"Taurus", "Gemini", "Virgo", "Libra"},
    "Mars":    {"Leo", "Sagittarius", "Pisces"},
    "Mercury": {"Taurus", "Libra"},
    "Jupiter": {"Aries", "Leo", "Scorpio"},
    "Venus":   {"Gemini", "Virgo", "Capricorn", "Aquarius"},
    "Saturn":  {"Gemini", "Virgo", "Taurus"},
    "Rahu":    {"Cancer", "Capricorn", "Virgo"},
    "Ketu":    {"Aries", "Sagittarius", "Pisces"},
}

# Vedic graha-drishti — list of OFFSETS (1=conjunction-aspect, 7=opposition).
# Every planet aspects 7. Mars +4/+8. Jupiter +5/+9. Saturn +3/+10.
# Rahu/Ketu commonly treated like Jupiter (5/9).
_ASPECT_OFFSETS = {
    "Sun":     {7},
    "Moon":    {7},
    "Mercury": {7},
    "Venus":   {7},
    "Mars":    {4, 7, 8},
    "Jupiter": {5, 7, 9},
    "Saturn":  {3, 7, 10},
    "Rahu":    {5, 7, 9},
    "Ketu":    {5, 7, 9},
}

_BENEFICS = {"Jupiter", "Venus", "Mercury"}  # Moon counted as benefic when waxing
_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}


# ─────────────────────────────────────────────────────────────────────
# Chart-shape helpers — tolerant to multiple shapes
# ─────────────────────────────────────────────────────────────────────

def _sidx(sign: Optional[str]) -> Optional[int]:
    if not sign:
        return None
    try:
        return _SIGNS.index(str(sign))
    except ValueError:
        return None


def _lagna_sign(chart_data: Dict[str, Any]) -> str:
    lg = chart_data.get("lagna") or {}
    if isinstance(lg, dict):
        return lg.get("sign", "") or ""
    return ""


def _planet_block(chart_data: Dict[str, Any], planet: str) -> Dict[str, Any]:
    """Return the chart_data['planets'][planet] block, normalising shape.
    Some payloads key by name ('Sun'), some by integer id."""
    planets = chart_data.get("planets") or {}
    if not isinstance(planets, dict):
        return {}
    if planet in planets and isinstance(planets[planet], dict):
        return planets[planet]
    # Case-insensitive fallback.
    for k, v in planets.items():
        if isinstance(k, str) and k.lower() == planet.lower() and isinstance(v, dict):
            return v
    return {}


def _sign_of_planet(chart_data: Dict[str, Any], planet: str) -> str:
    return _planet_block(chart_data, planet).get("sign", "") or ""


def _house_of_planet(chart_data: Dict[str, Any], planet: str) -> Optional[int]:
    """Prefer the explicit 'house' field; fall back to computing from
    sign + lagna."""
    b = _planet_block(chart_data, planet)
    h = b.get("house")
    if isinstance(h, int) and 1 <= h <= 12:
        return h
    lagna_idx = _sidx(_lagna_sign(chart_data))
    p_idx = _sidx(b.get("sign"))
    if lagna_idx is None or p_idx is None:
        return None
    return ((p_idx - lagna_idx) % 12) + 1


def _sign_of_house(lagna_sign: str, house: int) -> str:
    lagna_idx = _sidx(lagna_sign)
    if lagna_idx is None or not (1 <= house <= 12):
        return ""
    return _SIGNS[(lagna_idx + house - 1) % 12]


def _lord_of_house(lagna_sign: str, house: int) -> str:
    sign = _sign_of_house(lagna_sign, house)
    return _SIGN_LORDS.get(sign, "")


def _is_exalted(planet: str, sign: str) -> bool:
    return bool(planet and sign and _EXALTATION.get(planet) == sign)


def _is_debilitated(planet: str, sign: str) -> bool:
    return bool(planet and sign and _DEBILITATION.get(planet) == sign)


def _is_own_sign(planet: str, sign: str) -> bool:
    return bool(planet and sign and sign in _OWN_SIGNS.get(planet, []))


def _is_friend_sign(planet: str, sign: str) -> bool:
    return bool(planet and sign and sign in _FRIEND_SIGNS.get(planet, set()))


def _is_strong_karaka(chart_data: Dict[str, Any], planet: str) -> bool:
    """Strong = exalted, own sign, or strong friend sign. Conservative."""
    sign = _sign_of_planet(chart_data, planet)
    if not sign:
        return False
    if _is_exalted(planet, sign) or _is_own_sign(planet, sign):
        return True
    if _is_friend_sign(planet, sign):
        return True
    return False


def _is_weak_karaka(chart_data: Dict[str, Any], planet: str) -> bool:
    """Weak = debilitated. (We don't penalise enemy sign here — too
    many false positives without full Tatkalik computation.)"""
    sign = _sign_of_planet(chart_data, planet)
    return _is_debilitated(planet, sign)


def _aspects_house(chart_data: Dict[str, Any], planet: str, house: int) -> bool:
    """Does `planet` cast a graha-drishti to `house` (from natal lagna)?"""
    p_house = _house_of_planet(chart_data, planet)
    if p_house is None:
        return False
    offsets = _ASPECT_OFFSETS.get(planet, {7})
    for off in offsets:
        target = ((p_house - 1 + (off - 1)) % 12) + 1
        if target == house:
            return True
    return False


def _benefics_aspecting(chart_data: Dict[str, Any], house: int) -> List[str]:
    hits = [p for p in _BENEFICS if _aspects_house(chart_data, p, house)]
    # Moon counted as benefic when waxing — simple heuristic via degree
    # gap to Sun, fall back to including it conservatively if degree absent.
    sun_b = _planet_block(chart_data, "Sun")
    moon_b = _planet_block(chart_data, "Moon")
    sun_lon = sun_b.get("longitude") or sun_b.get("degree_total")
    moon_lon = moon_b.get("longitude") or moon_b.get("degree_total")
    if isinstance(sun_lon, (int, float)) and isinstance(moon_lon, (int, float)):
        waxing = ((float(moon_lon) - float(sun_lon)) % 360.0) < 180.0
        if waxing and _aspects_house(chart_data, "Moon", house):
            hits.append("Moon")
    return hits


def _malefics_aspecting(chart_data: Dict[str, Any], house: int) -> List[str]:
    return [p for p in _MALEFICS if _aspects_house(chart_data, p, house)]


# ─────────────────────────────────────────────────────────────────────
# Modern translation primitives
# ─────────────────────────────────────────────────────────────────────

def _viparita_in_play(chart_data: Dict[str, Any], lagna_sign: str) -> Optional[Tuple[int, int]]:
    """Viparita Raja Yoga = a dushthana (6/8/12) house lord placed in a
    dushthana house. Returns (lord_of_house, host_house) or None."""
    for src in (6, 8, 12):
        lord = _lord_of_house(lagna_sign, src)
        host = _house_of_planet(chart_data, lord)
        if host in (6, 8, 12) and host != src:
            # Bonus: the classic full viparita requires mutual dushthana
            # placement — we accept any dushthana lord in any dushthana
            # other than its own (mainstream simplification).
            return (src, host)
    return None


def _strong_planet_in_house(chart_data: Dict[str, Any], house: int) -> Optional[str]:
    """Return the dignified planet sitting in `house`, if any."""
    for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
              "Saturn", "Rahu", "Ketu"):
        if _house_of_planet(chart_data, p) == house:
            sign = _sign_of_planet(chart_data, p)
            if _is_exalted(p, sign) or _is_own_sign(p, sign) or _is_friend_sign(p, sign):
                return p
    return None


def _rahu_house(chart_data: Dict[str, Any]) -> Optional[int]:
    return _house_of_planet(chart_data, "Rahu")


# ─────────────────────────────────────────────────────────────────────
# Wealth-archetype resolver (uses life_arc.archetype_classifier when
# available; otherwise heuristic fallback so /predict never blocks).
# ─────────────────────────────────────────────────────────────────────

def resolve_wealth_archetype(chart_data: Dict[str, Any]) -> Optional[str]:
    """Try the canonical classifier first; if it errors or returns no
    primary, derive a coarse archetype from the chart's signature.
    Returns one of the WEALTH_ARCHETYPES keys or None."""
    try:
        from antar_engine.life_arc.archetype_classifier import classify_wealth_archetype
        res = classify_wealth_archetype(chart_data) or {}
        prim = res.get("primary_archetype")
        if isinstance(prim, str) and prim:
            return prim
    except Exception:
        pass
    # Heuristic fallback.
    lagna = _lagna_sign(chart_data)
    if not lagna:
        return None
    if _viparita_in_play(chart_data, lagna):
        return "DISRUPTOR"
    if _strong_planet_in_house(chart_data, 6):
        return "MASS_SERVER"
    # Strong Saturn or Jupiter in kendra → SYSTEMATIC / INSTITUTIONAL.
    for p in ("Saturn", "Jupiter"):
        h = _house_of_planet(chart_data, p)
        if h in (1, 4, 7, 10) and _is_strong_karaka(chart_data, p):
            return "INSTITUTIONAL" if p == "Jupiter" else "SYSTEMATIC"
    # 1H stellium → CHARISMA.
    in_h1 = sum(1 for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                             "Venus", "Saturn")
                if _house_of_planet(chart_data, p) == 1)
    if in_h1 >= 3:
        return "CHARISMA"
    return None


# ─────────────────────────────────────────────────────────────────────
# Vehicle-fit matrix — archetype × concern → "fit"/"neutral"/"mismatch"
# ─────────────────────────────────────────────────────────────────────

VEHICLE_FIT_MATRIX: Dict[str, Dict[str, str]] = {
    "DISRUPTOR": {
        "speculation": "fit",
        "finance":     "fit",
        "wealth":      "fit",
        "career":      "fit",
        "loss":        "fit",  # rise-through-adversity is the engine
        "property":    "mismatch",
        "family":      "mismatch",
    },
    "MASS_SERVER": {
        "career":      "fit",
        "finance":     "fit",
        "wealth":      "fit",
        "health":      "fit",
        "property":    "neutral",
        "speculation": "mismatch",
    },
    "SYSTEMATIC": {
        "career":      "fit",
        "finance":     "fit",
        "wealth":      "fit",
        "spiritual":   "fit",
        "property":    "fit",
        "speculation": "mismatch",
    },
    "CHARISMA": {
        "career":      "fit",
        "marriage":    "fit",
        "love":        "fit",
        "wealth":      "fit",
        "finance":     "fit",
        "loss":        "mismatch",
    },
    "INSTITUTIONAL": {
        "career":      "fit",
        "finance":     "fit",
        "wealth":      "fit",
        "spiritual":   "fit",
        "family":      "fit",
        "speculation": "mismatch",
    },
}


def vehicle_fit(archetype: Optional[str], concern: str) -> str:
    """Return "fit" / "neutral" / "mismatch" for an archetype × concern
    pair. Unknown archetypes default to neutral."""
    if not archetype:
        return "neutral"
    return VEHICLE_FIT_MATRIX.get(archetype, {}).get(
        (concern or "").strip().lower(), "neutral"
    )


# ─────────────────────────────────────────────────────────────────────
# THE function — calculate_natal_promise
# ─────────────────────────────────────────────────────────────────────

def calculate_natal_promise(
    chart_data: Optional[Dict[str, Any]],
    life_area_config: Optional[Dict[str, Any]],
    archetype: Optional[str] = None,
    concern: Optional[str] = None,
) -> Dict[str, Any]:
    """V2.2 Layer 1 — score whether the chart structurally supports the
    asked life area. Returns the verdict bundle described at the top
    of the module.

    Inputs:
      chart_data       — the full natal payload (planets+lagna).
      life_area_config — LIFE_AREA_MAP[concern] (primary, secondary, karaka).
      archetype        — wealth archetype (optional; we resolve when missing).
      concern          — string key used for vehicle_fit lookup.

    Returns: a dict with keys verdict, score, classical, modern, lk,
    vehicle_fit, archetype, reasoning_technical. NEVER raises — bad
    inputs return verdict=NEUTRAL with a reason."""
    reasons: List[str] = []
    if not chart_data or not isinstance(chart_data, dict):
        return _empty(reason="no chart_data")
    if not life_area_config or not isinstance(life_area_config, dict):
        return _empty(reason="no life_area_config")

    lagna_sign = _lagna_sign(chart_data)
    if not lagna_sign:
        return _empty(reason="no lagna sign")

    primary = life_area_config.get("primary")
    if not isinstance(primary, int) or not (1 <= primary <= 12):
        return _empty(reason=f"invalid primary house: {primary!r}")
    karakas = list(life_area_config.get("karaka") or [])

    # ── 1. CLASSICAL BASELINE ─────────────────────────────────────
    classical = 0
    lord = _lord_of_house(lagna_sign, primary)
    if lord:
        lord_house = _house_of_planet(chart_data, lord)
        if lord_house in {1, 2, 4, 5, 7, 9, 10, 11}:
            classical += 25
            reasons.append(f"primary lord {lord} in kendra/trikona/upachaya (h{lord_house}) +25")
        elif lord_house in {3, 6, 8, 12}:
            classical -= 30
            reasons.append(f"primary lord {lord} in dushthana (h{lord_house}) -30")
        lord_sign = _sign_of_planet(chart_data, lord)
        if _is_exalted(lord, lord_sign):
            classical += 15
            reasons.append(f"primary lord {lord} exalted in {lord_sign} +15")
        elif _is_debilitated(lord, lord_sign):
            classical -= 25
            reasons.append(f"primary lord {lord} debilitated in {lord_sign} -25")
        elif _is_own_sign(lord, lord_sign):
            classical += 10
            reasons.append(f"primary lord {lord} in own sign +10")

    for k in karakas:
        if _is_strong_karaka(chart_data, k):
            classical += 10
            reasons.append(f"karaka {k} strong +10")
        elif _is_weak_karaka(chart_data, k):
            classical -= 15
            reasons.append(f"karaka {k} weak -15")

    benefics = _benefics_aspecting(chart_data, primary)
    malefics = _malefics_aspecting(chart_data, primary)
    if benefics:
        classical += 10 * len(benefics)
        reasons.append(f"benefics aspecting h{primary}: {benefics} +{10*len(benefics)}")
    if malefics:
        classical -= 5 * len(malefics)
        reasons.append(f"malefics aspecting h{primary}: {malefics} -{5*len(malefics)}")

    # ── 2. MODERN TRANSLATION ─────────────────────────────────────
    modern = 0
    vip = _viparita_in_play(chart_data, lagna_sign)
    if vip and (primary in {6, 8, 12} or lord and _house_of_planet(chart_data, lord) in {6, 8, 12}):
        modern += 40
        reasons.append(f"viparita: dushthana lord of h{vip[0]} in h{vip[1]} +40")

    strong_h6 = _strong_planet_in_house(chart_data, 6)
    if strong_h6 and primary in {2, 6, 10, 11}:
        modern += 20
        reasons.append(f"strong {strong_h6} in h6 (MASS_SERVER engine) +20")

    rh = _rahu_house(chart_data)
    if rh in {11} or rh in {6, 8, 12}:
        if primary in {5, 7, 10, 11} or (concern and concern in {"finance", "wealth", "career"}):
            modern += 25
            reasons.append(f"Rahu in h{rh} (disruptor/unicorn marker) +25")

    # ── 3. LAL KITAB PASS ─────────────────────────────────────────
    # Use chart_data['lal_kitab_data'] if present; otherwise skip
    # (returns 0). Conservative — won't bonus/penalise without data.
    lk_adj = 0
    lk = chart_data.get("lal_kitab_data") or chart_data.get("lal_kitab") or {}
    if isinstance(lk, dict) and lk:
        try:
            from antar_engine.lk_conditions import has_pakka_ghar_support, has_blocked_house  # type: ignore
            if has_pakka_ghar_support(lk, primary):
                lk_adj += 15
                reasons.append(f"LK pakka ghar support h{primary} +15")
            if has_blocked_house(lk, primary):
                lk_adj -= 15
                reasons.append(f"LK house blocked h{primary} -15")
        except Exception:
            # Soft skip — never crash promise calc on LK shape drift.
            pass

    raw = classical + modern + lk_adj

    # ── 4. ARCHETYPE / VEHICLE-FIT GATE ──────────────────────────
    arch = archetype or resolve_wealth_archetype(chart_data)
    fit = vehicle_fit(arch, concern or "")
    if fit == "fit":
        raw += 15
        reasons.append(f"archetype {arch} ↔ {concern} → fit +15")
    elif fit == "mismatch":
        raw -= 20
        reasons.append(f"archetype {arch} ↔ {concern} → mismatch -20")

    # ── 5. VERDICT ───────────────────────────────────────────────
    if raw >= 30:
        verdict = "STRUCTURALLY_SUPPORTED"
    elif raw >= 0:
        verdict = "NEUTRAL"
    else:
        verdict = "STRUCTURALLY_BLOCKED"

    return {
        "verdict": verdict,
        "score": int(raw),
        "classical": int(classical),
        "modern": int(modern),
        "lk": int(lk_adj),
        "vehicle_fit": fit,
        "archetype": arch,
        "reasoning_technical": reasons,
        "has_structural_promise": verdict == "STRUCTURALLY_SUPPORTED",
    }


def _empty(reason: str = "") -> Dict[str, Any]:
    return {
        "verdict": "NEUTRAL",
        "score": 0,
        "classical": 0,
        "modern": 0,
        "lk": 0,
        "vehicle_fit": "neutral",
        "archetype": None,
        "reasoning_technical": [f"degraded: {reason}"] if reason else [],
        "has_structural_promise": False,
    }
