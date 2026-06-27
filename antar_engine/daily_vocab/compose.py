"""
antar_engine/daily_vocab/compose.py — builds the structured `concrete` block for
the daily surface from already-computed primitives (panchanga + transit standing
+ chart-relative precision). PURE: no LLM, no Swiss Ephemeris.

The caller (home_composer for prod, or the backtest harness for review) is
responsible for computing the inputs with the live engines and passing them in.
This keeps the vocab + conviction logic deterministic and fully unit-testable
without an ephemeris.

OUTPUT SCHEMA (any field below its conviction floor = absent = not rendered):
{
  "body_focus":           {"text": str, "tier": "soft"} | absent,
  "food_lean":            {"text": str}                 | absent,
  "mood_tone":            {"text": str}                 | absent,
  "romance_read":         {"text": str}                 | absent,
  "favourable_direction": {"text": str}                 | absent,
  "lucky_color":          {"text": str}                 | absent,
  "best_window":          str | None,        # reused from upstream
  "steer_clear_window":   str | None,        # reused from upstream
  "event_watch":          {"text": str, "tier": "watch"} | absent,   # Tier B, usually absent
  "_debug": {...}         # internal only — dropped by public_view()
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from antar_engine.daily_vocab import tables as T
from antar_engine.daily_vocab import conviction as C

_HARD_ASPECTS = {"conjunction", "square", "opposition"}
_WARM_DAYLORDS = {"Sun", "Mars", "Jupiter"}     # warming food agreement
_COMFORT_DAYLORDS = {"Moon", "Venus"}           # comfort food agreement
_LIGHT_DAYLORDS = {"Mercury", "Saturn"}         # light food agreement
_FAVORABLE_TARA = {"very_favorable", "favorable"}
_CAUTION_TARA = {"unfavorable", "caution", "cautious"}


# ─────────────────────────────────────────────────────────────────────
# Small input normalizers for the engine-agnostic transit_contacts list
# ─────────────────────────────────────────────────────────────────────

def _contacts(transit_contacts: Optional[List[dict]]) -> List[dict]:
    """Normalize the standing-transit list. Each item:
        {planet, house, aspect_to_natal?, orb?, target_house?}
    Silently drops malformed rows so a bad upstream never crashes the day."""
    out: List[dict] = []
    for c in (transit_contacts or []):
        if not isinstance(c, dict):
            continue
        p = (c.get("planet") or "").strip().title()
        h = c.get("house")
        if not p or not isinstance(h, int) or not (1 <= h <= 12):
            continue
        out.append({
            "planet": p,
            "house": h,
            "aspect_to_natal": (c.get("aspect_to_natal") or None),
            "orb": c.get("orb"),
            "target_house": c.get("target_house"),
        })
    return out


def _daylord_reinforced(day_lord: Optional[str], contacts: List[dict]) -> bool:
    """True if the day-lord planet is itself an active standing transit (in an
    angle 1/4/7/10 or making a tight aspect) — a small reinforcement signal."""
    if not day_lord:
        return False
    for c in contacts:
        if c["planet"] != day_lord:
            continue
        if c["house"] in (1, 4, 7, 10):
            return True
        if c["aspect_to_natal"] in _HARD_ASPECTS or c["aspect_to_natal"] in ("trine", "sextile"):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────
# Per-field builders. Each returns (text|None, confidence, factors, drivers)
# `drivers` = internal house/planet reasons (debug only, never user-facing).
# ─────────────────────────────────────────────────────────────────────

def _build_food(moon_sign, day_lord, tithi_quality):
    sign = T.norm_sign(moon_sign)
    if not sign:
        return None, 0.0, [], []
    element = T.SIGN_ELEMENT.get(sign)
    if not element:
        return None, 0.0, [], []
    text = T.ELEMENT_FOOD_LEAN[element][0].upper() + T.ELEMENT_FOOD_LEAN[element][1:] + "."
    factors = [("element_known", 0.15)]
    drivers = [f"moon_element={element}"]
    # day-lord taste agreement
    agree = (
        (element in ("fire", "earth") and day_lord in _WARM_DAYLORDS) or
        (element == "water" and day_lord in _COMFORT_DAYLORDS) or
        (element == "air" and day_lord in _LIGHT_DAYLORDS)
    )
    if agree:
        factors.append(("daylord_taste_agrees", 0.20))
        drivers.append(f"daylord={day_lord}:taste_agrees")
    if (tithi_quality or "").lower() == "auspicious":
        factors.append(("tithi_auspicious", 0.10))
    conf = C.confidence(0.40, factors)
    return text, conf, factors, drivers


def _build_mood(moon_nak, moon_sign, natal_moon_sign, tara_quality):
    nak = T.norm_nakshatra(moon_nak)
    if not nak:
        return None, 0.0, [], []
    prof = T.NAKSHATRA_ENERGY[nak]
    energy = prof["energy"]
    aligned = prof["aligned"][0] if prof["aligned"] else None
    friction = prof["friction"][0] if prof["friction"] else None
    factors = [("nakshatra_energy", 0.20)]
    drivers = [f"moon_nak={nak}"]

    parts = [f"You'll likely feel {energy} today."]
    if aligned and friction:
        parts.append(f"Good for {aligned}; less so for {friction}.")
    elif aligned:
        parts.append(f"A good day for {aligned}.")

    sign = T.norm_sign(moon_sign)
    nat = T.norm_sign(natal_moon_sign)
    clash = bool(sign and nat and sign in T.MOON_FRICTION_MAP.get(nat, []))
    matched = bool(sign and nat and sign == nat)
    if clash:
        parts.insert(0, "The mood may sit a little crosswise with your usual rhythm — give yourself room.")
        factors.append(("moon_friction_clear", 0.15))  # [perchart] natal-moon modifier weighs more
        drivers.append(f"moon_friction:{sign}_vs_natal_{nat}")
    elif matched:
        parts.append("This sits close to your natural rhythm, so you should feel at home in it.")
        factors.append(("moon_friction_clear", 0.15))  # [perchart] natal-moon modifier weighs more
        drivers.append("moon_matches_natal")

    if tara_quality in _FAVORABLE_TARA:
        factors.append(("tara_strong", 0.15))
        drivers.append(f"tara={tara_quality}")
    elif tara_quality in _CAUTION_TARA:
        factors.append(("tara_strong", 0.15))
        drivers.append(f"tara={tara_quality}")

    conf = C.confidence(0.45, factors)
    return " ".join(parts), conf, factors, drivers


def _moon_house(contacts):
    for c in contacts:
        if c["planet"] == "Moon":
            return c["house"]
    return None


def _build_body(contacts, moon_sign):
    """Soft, NON-medical 'gentle attention' read keyed off TIME-BOUND signals so
    it varies day to day and isn't slow-transit wallpaper:
      - a fast malefic (Sun/Mars) perfecting a hard aspect today (orb <= 1.5),
      - a slow malefic (Saturn/Rahu/Ketu) only when genuinely exact (orb <= 0.5),
      - else the Moon transiting the 6th (health/workload) today.
    A permanent slow standing aspect is background, never the daily claim."""
    factors: List = []
    drivers: List = []
    cand = None  # (kind, orb_for_sort, body_house, planet, weight)

    for c in contacts:
        p = c["planet"]
        if p not in T.MALEFICS:
            continue
        asp = c["aspect_to_natal"]
        orb = c["orb"]
        if asp not in _HARD_ASPECTS or not isinstance(orb, (int, float)):
            continue
        body_house = c.get("target_house") or c["house"]
        if not (isinstance(body_house, int) and 1 <= body_house <= 12):
            continue
        if p in T.FAST_MALEFICS and orb <= 1.5:
            w = round(0.30 - min(orb, 1.5) * 0.06, 3)
            if cand is None or orb < cand[1]:
                cand = ("fast_exact", orb, body_house, p, w)
        elif p in T.SLOW_MALEFICS and orb <= 0.5:
            if cand is None or orb < cand[1]:
                cand = ("slow_perfecting", orb, body_house, p, 0.22)

    if cand is None and _moon_house(contacts) == 6:
        cand = ("moon_sixth", 9.9, 6, "Moon", 0.25)

    if cand is None:
        return None, 0.0, [], []

    kind, orb, body_house, planet, w = cand
    part = T.HOUSE_BODY.get(body_house, "your body")
    advice = T.PLANET_BODY_ADVICE.get(planet, "go a little gentler than usual")
    factors.append((f"body_{kind}", w))
    drivers.append(f"{planet}_{kind}_house{body_house}_orb{orb}")
    conf = C.confidence(0.30, factors)
    text = f"{part[0].upper() + part[1:]} may want a little attention today — {advice}."
    return text, conf, factors, drivers


def _build_romance(contacts, weekday, moon_nak):
    factors: List = []
    drivers: List = []
    wd = (weekday or "").strip().title()
    if wd == "Friday":
        factors.append(("venus_day", 0.25))
        drivers.append("friday")
    # benefic touching 5th/7th
    for c in contacts:
        if c["planet"] in ("Venus", "Jupiter", "Moon"):
            if c["house"] in (5, 7) or c.get("target_house") in (5, 7):
                factors.append(("benefic_5_7", 0.30))  # [perchart] benefic in YOUR 5th/7th clears floor alone
                drivers.append(f"{c['planet']}_house{c['house']}")
                break
    nak = T.norm_nakshatra(moon_nak)
    if nak in T.WARM_NAKSHATRAS:
        factors.append(("warm_nakshatra", 0.15))
        drivers.append(f"warm_nak={nak}")

    if not factors:
        return None, 0.0, [], []
    conf = C.confidence(0.20, factors)
    keys = {f[0] for f in factors}
    if "benefic_5_7" in keys:
        text = ("Connection flows easily today — a good moment to say the warm "
                "thing you've been meaning to, or to plan something together.")
    elif "venus_day" in keys:
        text = ("A warm, easy day for connection — a kind word or a little real "
                "time together goes a long way.")
    else:  # warm nakshatra only
        text = ("A gentle, affectionate undertone to the day — lead with warmth "
                "rather than intensity.")
    return text, conf, factors, drivers


def _build_direction(day_lord, tara_quality, reinforced):
    if not day_lord:
        return None, 0.0, [], []
    direction = T.PLANET_DIRECTION.get(day_lord)
    if not direction:
        return None, 0.0, [], []
    factors = []
    drivers = [f"daylord={day_lord}:dik={direction}"]
    if tara_quality in _FAVORABLE_TARA:
        factors.append(("tara_favorable", 0.20))
    if reinforced:
        factors.append(("daylord_reinforced", 0.15))
    conf = C.confidence(0.35, factors)
    text = (f"Facing {direction} for an important conversation or a stretch of "
            f"focused work gives you a small edge today.")
    return text, conf, factors, drivers


def _build_color(day_lord, tara_quality, reinforced):
    if not day_lord:
        return None, 0.0, [], []
    color = T.DAY_LORD_COLOR.get(day_lord)
    if not color:
        return None, 0.0, [], []
    factors = []
    drivers = [f"daylord={day_lord}:color={color}"]
    if tara_quality in _FAVORABLE_TARA:
        factors.append(("tara_favorable", 0.15))
    if reinforced:
        factors.append(("daylord_reinforced", 0.20))
    conf = C.confidence(0.30, factors)
    text = f"A touch of {color} suits the day if you're choosing what to wear."
    return text, conf, factors, drivers


def _build_event_watch(contacts, tithi_quality, tara_quality):
    """TIER B — hard gate. Fires only when >=2 INDEPENDENT factors converge AND
    at least one is TIME-BOUND (a real 'today' trigger), so it stays episodic
    rather than tripping every day on a permanent slow standing. Phrased as a
    soft 'unhurried day', never an assertion."""
    timebound: List = []
    context: List = []
    drivers: List = []
    domain_house: Optional[int] = None

    def _set_domain(h):
        nonlocal domain_house
        if domain_house is None and isinstance(h, int):
            domain_house = h

    for c in contacts:
        p = c["planet"]
        asp = c["aspect_to_natal"]
        orb = c["orb"]
        hard = asp in _HARD_ASPECTS and isinstance(orb, (int, float))
        if not hard:
            continue
        if p in T.FAST_MALEFICS and orb <= 1.5:
            timebound.append((f"{p.lower()}_exact", 0.20))
            drivers.append(f"{p}_{asp}_orb{orb}")
            _set_domain(c.get("target_house") or c["house"])
        elif p in T.SLOW_MALEFICS and orb <= 0.5:
            timebound.append((f"{p.lower()}_perfecting", 0.18))
            drivers.append(f"{p}_{asp}_orb{orb}")
            _set_domain(c.get("target_house") or c["house"])

    mh = _moon_house(contacts)
    if mh in (6, 8, 12):
        timebound.append((f"moon_dusthana_{mh}", 0.18))
        drivers.append(f"moon_house{mh}")
        _set_domain(mh)

    # Context factors — never sufficient alone; can be the 2nd converging factor.
    if (tithi_quality or "").lower() == "inauspicious":
        context.append(("tithi_inauspicious", 0.10)); drivers.append("tithi_inauspicious")
    if tara_quality in _CAUTION_TARA:
        context.append(("tara_caution", 0.10)); drivers.append(f"tara={tara_quality}")

    factors = timebound + context
    keys = {f[0] for f in factors}
    conf = C.confidence(0.30, factors)
    # gate: a real today-trigger present, >=2 independent factors, high conf.
    if not timebound or not C.passes_tier_b(len(keys), conf):
        return None, conf, factors, drivers

    domain = T.EVENT_DOMAIN_BY_HOUSE.get(domain_house or -1) or "anything high-stakes"
    text = (f"An unhurried day for {domain} — give it extra time and a second "
            f"look, and you'll be fine.")
    return text, conf, factors, drivers


# ─────────────────────────────────────────────────────────────────────
# Public entry
# ─────────────────────────────────────────────────────────────────────

def _pick_lord(personal, day, table):
    """[perchart-lord] Use the chart's period (dasha) lord for a personal
    field when it maps in `table`; else fall back to the weekday lord so
    the field is never dropped (e.g. Ketu has no color)."""
    if personal and personal in table:
        return personal
    return day


def compute_concrete_block(
    *,
    today_moon_sign: Optional[str],
    today_moon_nak: Optional[str],
    natal_moon_sign: Optional[str] = None,
    natal_moon_nak: Optional[str] = None,
    natal_lagna_sign: Optional[str] = None,
    weekday: Optional[str] = None,
    tithi_quality: Optional[str] = None,
    transit_contacts: Optional[List[dict]] = None,
    precision: Optional[Dict[str, Any]] = None,
    best_window: Optional[str] = None,
    steer_clear_window: Optional[str] = None,
    language: str = "en",
    personal_lord: Optional[str] = None,  # [perchart-lord] chart's current dasha lord
) -> Dict[str, Any]:
    """Build the daily `concrete` block. Always returns a dict (possibly with
    only window fields). Fields below their conviction floor are omitted."""
    precision = precision or {}
    tara_quality = precision.get("tara_quality")
    contacts = _contacts(transit_contacts)
    day_lord = T.day_lord_for(weekday)
    reinforced = _daylord_reinforced(day_lord, contacts)

    debug: Dict[str, Any] = {}
    public: Dict[str, Any] = {}

    def _consider(field, text, conf, factors, drivers, tier=None):
        debug[field] = {
            "confidence": conf,
            "surfaced": False,
            "factors": [f[0] for f in factors],
            "drivers": drivers,
        }
        if text and C.passes_tier_a(field, conf):
            entry = {"text": text}
            if tier:
                entry["tier"] = tier
            public[field] = entry
            debug[field]["surfaced"] = True

    # Tier A
    _consider("food_lean", *_build_food(today_moon_sign, day_lord, tithi_quality))
    _consider("mood_tone", *_build_mood(today_moon_nak, today_moon_sign, natal_moon_sign, tara_quality))
    _consider("body_focus", *_build_body(contacts, today_moon_sign), tier="soft")
    _consider("romance_read", *_build_romance(contacts, weekday, today_moon_nak))
    # [perchart-lord] color + direction read off the chart's current period
    # lord (dasha) so they are personal; fall back to the weekday lord.
    _dir_lord = _pick_lord(personal_lord, day_lord, T.PLANET_DIRECTION)
    _col_lord = _pick_lord(personal_lord, day_lord, T.DAY_LORD_COLOR)
    _consider("favourable_direction", *_build_direction(_dir_lord, tara_quality, _daylord_reinforced(_dir_lord, contacts)))
    _consider("lucky_color", *_build_color(_col_lord, tara_quality, _daylord_reinforced(_col_lord, contacts)))

    # Reused upstream windows (already conviction-filtered upstream; pass through)
    public["best_window"] = best_window or None
    public["steer_clear_window"] = steer_clear_window or None

    # Tier B — hard gate, usually absent
    ew_text, ew_conf, ew_factors, ew_drivers = _build_event_watch(contacts, tithi_quality, tara_quality)
    debug["event_watch"] = {
        "confidence": ew_conf,
        "surfaced": bool(ew_text),
        "factors": [f[0] for f in ew_factors],
        "drivers": ew_drivers,
    }
    if ew_text:
        public["event_watch"] = {"text": ew_text, "tier": "watch"}

    # Defense-in-depth: strip every user-facing text field. Text is already
    # jargon-free by construction; this guarantees it.
    public = _strip_public(public, language)

    public["_debug"] = debug
    return public


def _strip_public(public: Dict[str, Any], language: str) -> Dict[str, Any]:
    try:
        from antar_engine.output_strips import apply_user_facing_strips
    except Exception:
        return public
    out: Dict[str, Any] = {}
    for k, v in public.items():
        if isinstance(v, dict) and "text" in v:
            v = dict(v)
            try:
                v["text"] = apply_user_facing_strips(
                    v["text"], language=language, field_type="plain", depth="user"
                )
            except Exception:
                pass
            out[k] = v
        else:
            out[k] = v
    return out


def public_view(block: Dict[str, Any]) -> Dict[str, Any]:
    """The user-facing block with the internal debug channel removed."""
    return {k: v for k, v in (block or {}).items() if k != "_debug"}


def populated_fields(block: Dict[str, Any]) -> List[str]:
    """Names of the Tier-A/B text fields actually surfaced (windows excluded)."""
    names = ("body_focus", "food_lean", "mood_tone", "romance_read",
             "favourable_direction", "lucky_color", "event_watch")
    return [n for n in names if isinstance(block.get(n), dict) and block[n].get("text")]
