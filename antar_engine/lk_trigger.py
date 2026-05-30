"""
antar_engine/lk_trigger.py — the matches_trigger predicate for LK_CONDITIONS.

Decides, for one chart on one day, which LK_CONDITIONS rows fire.

KEY INTERPRETATION (founder-confirmed 2026-05-30: house-from-lagna):
  trigger["natal_house"] is read as HOUSE-FROM-LAGNA — i.e. the transit planet
  currently occupies that house of the natal chart (whole-sign, lagna-relative),
  which is what calculate_current_transits returns as `current_house`. The row
  CONTENT (10=career, 5=creativity, 6=conflict, 8=hidden, 12=loss) are all
  lagna-house significations, so this is the defensible reading. If the intended
  meaning is "house counted from the planet's own natal position", change
  _transit_in_house() — the firing set is completely different.

Sleeping = Definition 3 (RCJ-1952), wired to aspects_engine.ASPECT_RULES:
  a planet sleeps if it aspects NO other natal planet, EXCEPT a planet sitting
  in its own pakka ghar is always awake. (Aspect-only; conjunction does not
  awaken — faithful to "aspects no planet". Half-rule OFF.)

duration_min_days = computed via Swiss Ephemeris: days since the transit planet
  entered its current sidereal sign (whole-sign house == sign, so sign-entry ==
  house-entry). Uses the same Lahiri/ephe setup as transits_engine.
"""
from __future__ import annotations
from datetime import datetime, timedelta
import os

from antar_engine.aspects_engine import ASPECT_RULES

# ── PAKKA GHAR (founder-locked 2026-05-30, incl. Rahu [3,6]) ────────────────
PAKKA_GHAR = {
    "Sun": [1], "Moon": [4], "Mars": [3, 8], "Mercury": [6, 7],
    "Jupiter": [2, 5, 9, 11, 12], "Venus": [7], "Saturn": [8, 10],
    "Rahu": [3, 6], "Ketu": [6],
}

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


# ── helpers to read the (possibly stringified-JSON) inputs ──────────────────
def _safe(obj):
    """Parse JSONB-as-string; never assume native dict (project rule 8)."""
    if isinstance(obj, str):
        try:
            import json
            obj = json.loads(obj)
        except Exception:
            return {}
    return obj if isinstance(obj, dict) else {}


def _natal_planets(natal_state) -> dict:
    """Return {planet: {'house': int, 'sign': str}} from natal_state."""
    ns = _safe(natal_state)
    pl = ns.get("planets", ns)          # planets dict, or the state itself
    pl = _safe(pl)
    return {k: v for k, v in pl.items() if isinstance(v, dict) and v.get("house")}


def _transit_by_planet(transits) -> dict:
    out = {}
    for t in (transits or []):
        if isinstance(t, dict) and t.get("planet") and "error" not in t:
            out[t["planet"]] = t
    return out


# ── aspects / sleeping (Definition 3) ───────────────────────────────────────
def _aspected_houses(planet: str, house: int) -> set:
    return {((house - 1 + (n - 1)) % 12) + 1 for n in ASPECT_RULES.get(planet, [7])}


def is_sleeping(planet: str, natal_planets: dict) -> bool:
    """Definition 3 (RCJ-1952): aspects no other natal planet; pakka ghar = awake."""
    data = natal_planets.get(planet)
    if not data:
        return False
    house = data["house"]
    if house in PAKKA_GHAR.get(planet, []):      # in own pakka ghar → awake
        return False
    occ = {}
    for p, d in natal_planets.items():
        occ.setdefault(d["house"], []).append(p)
    targets = _aspected_houses(planet, house)
    aspects_someone = any(o != planet for h in targets for o in occ.get(h, []))
    return not aspects_someone


# ── transit duration via ephemeris ──────────────────────────────────────────
def _sidereal_sign_index(planet: str, when: datetime) -> int | None:
    """Sidereal (Lahiri) sign index 0-11 for a planet at a UTC datetime."""
    try:
        import swisseph as swe
        swe.set_ephe_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe"))
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ids = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
               "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
               "Rahu": swe.MEAN_NODE, "Ketu": swe.MEAN_NODE}
        if planet not in ids:
            return None
        jd = swe.julday(when.year, when.month, when.day, when.hour + when.minute / 60.0)
        pos, _ = swe.calc_ut(jd, ids[planet])
        sid = (pos[0] - swe.get_ayanamsa(jd)) % 360
        idx = int(sid / 30)
        if planet == "Ketu":
            idx = (idx + 6) % 12
        return idx
    except Exception:
        return None  # ephemeris unavailable → caller fails open


def days_in_current_house(planet: str, now: datetime | None = None, max_lookback: int = 1000) -> int | None:
    """
    Days since `planet` entered its current sidereal sign (== current whole-sign
    house). Coarse-to-fine back-step. Returns None if ephemeris unavailable
    (caller treats None as 'settled', failing open).
    """
    now = now or datetime.utcnow()
    cur = _sidereal_sign_index(planet, now)
    if cur is None:
        return None
    # coarse step back until the sign differs
    step = 8
    back = step
    while back <= max_lookback:
        if _sidereal_sign_index(planet, now - timedelta(days=back)) != cur:
            break
        back += step
    else:
        return max_lookback  # been in-sign at least this long
    # refine within the [back-step, back] window to the day
    lo, hi = back - step, back
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _sidereal_sign_index(planet, now - timedelta(days=mid)) == cur:
            lo = mid
        else:
            hi = mid
    return lo


# ── transit-in-house test (the flagged interpretation) ──────────────────────
def _transit_in_house(tinfo: dict, natal_house: int) -> bool:
    return tinfo.get("current_house") == natal_house


def _transit_over_natal(transits_by_planet: dict, transit_planet: str,
                        natal_planets: dict, natal_planet: str) -> bool:
    """True if `transit_planet`'s current sign == `natal_planet`'s natal sign."""
    t = transits_by_planet.get(transit_planet)
    n = natal_planets.get(natal_planet)
    if not t or not n:
        return False
    return t.get("current_sign") == n.get("sign")


# ── yoga checks ─────────────────────────────────────────────────────────────
def _house_of(natal_planets, p):
    d = natal_planets.get(p)
    return d["house"] if d else None


def _yoga_fires(trigger: dict, natal_planets: dict, tbp: dict) -> bool:
    name = trigger.get("yoga_name")
    if name == "vish":
        if _house_of(natal_planets, "Saturn") != _house_of(natal_planets, "Moon"):
            return False
        if _house_of(natal_planets, "Saturn") is None:
            return False
        return (_transit_over_natal(tbp, "Moon", natal_planets, "Saturn")
                or _transit_over_natal(tbp, "Saturn", natal_planets, "Moon"))
    if name == "guru_chandala":
        if _house_of(natal_planets, "Jupiter") != _house_of(natal_planets, "Rahu"):
            return False
        if _house_of(natal_planets, "Jupiter") is None:
            return False
        return (_transit_over_natal(tbp, "Jupiter", natal_planets, "Rahu")
                or _transit_over_natal(tbp, "Rahu", natal_planets, "Jupiter"))
    if name == "kemadruma":
        moon_h = _house_of(natal_planets, "Moon")
        if moon_h is None:
            return False
        second = (moon_h % 12) + 1
        twelfth = ((moon_h - 2) % 12) + 1
        occupied = {d["house"] for d in natal_planets.values()}
        if second in occupied or twelfth in occupied:
            return False  # not Kemadruma — Moon has a neighbour
        return any(_transit_over_natal(tbp, mal, natal_planets, "Moon")
                   for mal in ("Saturn", "Mars", "Rahu", "Ketu"))
    if name == "shri":
        moon_h = _house_of(natal_planets, "Moon")
        jup_h = _house_of(natal_planets, "Jupiter")
        if moon_h is None or jup_h is None:
            return False
        from_moon = ((jup_h - moon_h) % 12) + 1
        if from_moon not in (1, 4, 7, 10):
            return False  # Jupiter not in kendra from Moon
        # activation: Jupiter transiting over a natal benefic's position
        return any(_transit_over_natal(tbp, "Jupiter", natal_planets, b)
                   for b in ("Jupiter", "Venus", "Mercury", "Moon"))
    return False


# ── the predicate ───────────────────────────────────────────────────────────
def matches_trigger(trigger: dict, natal_state, transits, dasha, *, now: datetime | None = None) -> bool:
    """
    Does this condition's trigger fire for the chart today?
    natal_state: chart LK natal data (planets dict, possibly JSON string)
    transits:    list from calculate_current_transits
    dasha:       dict with 'md_lord'
    """
    natal_planets = _natal_planets(natal_state)
    tbp = _transit_by_planet(transits)
    md_lord = _safe(dasha).get("md_lord") if isinstance(dasha, (str, dict)) else (dasha or {}).get("md_lord")
    ttype = trigger.get("type")

    if ttype == "yoga":
        return _yoga_fires(trigger, natal_planets, tbp)

    if ttype == "transit_with_dasha":
        planet = trigger.get("planet")
        if md_lord != planet:
            return False
        # planet must actually be transiting (have a position); natal_house "any"
        return planet in tbp

    if ttype == "transit":
        planet = trigger.get("planet")
        t = tbp.get(planet)
        if not t:
            return False
        # 1. house-from-lagna match (see KEY INTERPRETATION)
        if not _transit_in_house(t, trigger.get("natal_house")):
            return False
        # 2. natal-state gate
        if trigger.get("natal_state_required") == "sleeping" and not is_sleeping(planet, natal_planets):
            return False
        # 3. dasha gate
        if trigger.get("dasha_match") == "MD" and md_lord != planet:
            return False
        # 4. duration gate (ephemeris). None => fail open (settled).
        dmin = trigger.get("duration_min_days")
        if dmin:
            d = days_in_current_house(planet, now)
            if d is not None and d < dmin:
                return False
        return True

    return False
