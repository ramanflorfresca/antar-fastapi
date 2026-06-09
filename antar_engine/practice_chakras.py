"""
antar_engine/practice_chakras.py
─────────────────────────────────────────────────────────────────────────────
Chakra ↔ planet diagnostic.  Phase 1 (practice redesign).

Derives each of the 7 chakra states from its ruling planets' natal conditions
(reusing places_conditions).  Planet names are allowed as actors (Path B);
no house numbers appear.
"""

from __future__ import annotations

from typing import Optional

CHAKRA_RULERS = {
    "crown":        ["Ketu", "Jupiter"],
    "third_eye":    ["Jupiter", "Moon", "Saturn"],
    "throat":       ["Mercury", "Saturn"],
    "heart":        ["Venus", "Sun"],
    "solar_plexus": ["Sun", "Mars"],
    "sacral":       ["Moon", "Venus", "Jupiter"],
    "root":         ["Mars", "Saturn"],
}

CHAKRA_ORDER = ["crown", "third_eye", "throat", "heart", "solar_plexus", "sacral", "root"]

_STRONG = {"exalted", "own_sign", "friend"}
_WEAK = {"debilitated", "combust", "sleeping"}
_AFFLICTED = {"debilitated", "combust", "sleeping", "enemy"}

# ── Quantitative scoring (score_pct) ─────────────────────────────────────────
SIGNS_12 = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
            "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
_BENEFIC_ASPECTS = {"Jupiter": (5, 7, 9), "Venus": (7,), "Mercury": (7,), "Moon": (7,)}
_KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}

PLANET_STRENGTH_PCT = {
    "exalted": 95, "own_sign": 85, "moolatrikona": 80, "friend": 70,
    "neutral": 55, "enemy": 38, "debilitated": 18, "combust": 22, "sleeping": 25,
}


# [chakra-2axis] BEGIN
# ─────────────────────────────────────────────────────────────────────────────
# Two-axis chakra model (magnitude × valence).  Added by patch_chakra_two_axis.
# Reads existing engine outputs (Bhinnashtakavarga, dignity, functional
# benefic/malefic, LK sleeping/rin, dasha activation) and recombines them with
# documented weights — no new astronomy, no new LLM math.
# ─────────────────────────────────────────────────────────────────────────────

# Canonical planet→chakra mapping with explicit weights.  Single source of
# truth.  2 rulers per chakra, weights sum to 1.  All 9 grahas covered.
CANONICAL_CHAKRA_WEIGHTS = {
    "crown":        {"Jupiter": 0.6, "Ketu":    0.4},
    "third_eye":    {"Jupiter": 0.6, "Rahu":    0.4},
    "throat":       {"Mercury": 0.6, "Saturn":  0.4},
    "heart":        {"Venus":   0.6, "Sun":     0.4},
    "solar_plexus": {"Sun":     0.6, "Mars":    0.4},
    "sacral":       {"Moon":    0.6, "Venus":   0.4},
    "root":         {"Mars":    0.6, "Saturn":  0.4},
}

# Lazy import-safe map of sign name → 0-based index (Aries = 0).
_SIGN_INDEX = {s: i for i, s in enumerate([
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
])}

# Dignity → valence contribution (V axis).
_DIGNITY_V = {
    "exalted": 0.30, "own_sign": 0.30, "moolatrikona": 0.30,
    "friend": 0.10, "neutral": 0.0, "enemy": -0.10,
    "debilitated": -0.30, "combust": -0.10, "sleeping": 0.0,
}

# Combust / retrograde modifiers on M (magnitude).
_M_COMBUST_SUB = 0.15
_M_RETROGRADE_SUB = 0.05

# Wellness output spread (Correction A — additive, not multiplicative).
# wellness = round(100 * clamp(0.5 + 0.2*V + 0.2*V*M, 0, 1))
_W_BASE = 0.5
_W_V    = 0.20
_W_VM   = 0.20

# Constants intentionally exposed for post-launch calibration; do not change
# the structure (separate M/V/state/wellness fields) — only these numbers.
_M_W_NATAL   = 0.45
_M_W_TIME    = 0.35
_M_W_TRANSIT = 0.20

_TIME_W_MD = 1.00
_TIME_W_AD = 0.70
_TIME_W_PD = 0.40
_TIME_W_NONE = 0.15

_STATE_M_HI = 0.66
_STATE_M_LO = 0.33
_STATE_V_HI = +0.20
_STATE_V_LO = -0.20


def _safe_int_or_none(v):
    try:
        return int(v)
    except Exception:
        return None


def _planet_sign_index(planet, chart):
    p = ((chart or {}).get("planets") or {}).get(planet) or {}
    si = _safe_int_or_none(p.get("sign_index"))
    if si is None:
        sign = p.get("sign")
        if sign in _SIGN_INDEX:
            si = _SIGN_INDEX[sign]
    return si


def _lagna_sign_name(chart):
    """Return capitalized lagna sign name or empty string."""
    if not chart:
        return ""
    lg = chart.get("lagna")
    if isinstance(lg, dict):
        s = lg.get("sign")
        if isinstance(s, str) and s:
            return s.strip().capitalize()
    s = chart.get("lagna_sign")
    if isinstance(s, str) and s:
        return s.strip().capitalize()
    return ""


def _natal_bindus_norm(planet, chart, ashtakavarga):
    """Per-planet natal-sign Bhinnashtakavarga bindus / 8 → 0..1.
    Rahu / Ketu / missing planet default to 4 (neutral) per founder ruling."""
    if planet in ("Rahu", "Ketu"):
        return 4 / 8.0
    if not ashtakavarga:
        return 4 / 8.0
    bh = ashtakavarga.get("bhinnashtakavarga") if isinstance(ashtakavarga, dict) else None
    if not isinstance(bh, dict) or planet not in bh:
        return 4 / 8.0
    arr = bh.get(planet) or []
    si = _planet_sign_index(planet, chart)
    if si is None or not (0 <= si < len(arr)):
        return 4 / 8.0
    try:
        return max(0.0, min(1.0, float(arr[si]) / 8.0))
    except Exception:
        return 4 / 8.0


def _dasha_role(planet, dashas):
    """Return 'md' | 'ad' | 'pd' | '' for this planet in the current dasha tree."""
    if not dashas:
        return ""
    try:
        from antar_engine.places_intel import get_dasha_context
        ctx = get_dasha_context(dashas, "en") or {}
    except Exception:
        ctx = {}
    if ctx.get("md_lord") == planet:
        return "md"
    if ctx.get("ad_lord") == planet:
        return "ad"
    pd_lord = ctx.get("pd_lord") or (dashas.get("current_pd") or {}).get("planet")
    if pd_lord == planet:
        return "pd"
    return ""


def _time_score(role):
    return {
        "md": _TIME_W_MD,
        "ad": _TIME_W_AD,
        "pd": _TIME_W_PD,
    }.get(role, _TIME_W_NONE)


def _transit_score(planet, chart, transits, conditions):
    """0..1 — base 0.5, boost on kendra/trikona transit or high transit bindu,
    boost on Sade Sati, minus combust / retrograde.  Conservative when transit
    data is absent: stays at base 0.5 with the natal-condition combust/retro
    modifier applied."""
    s = 0.5
    p_cond = (conditions or {}).get(planet, {}).get("condition", "")
    if p_cond == "combust":
        s -= _M_COMBUST_SUB
    # Live transit shape: {"transits": {planet: {"sign_index", "retrograde",
    # "house_from_lagna"}}}.  Tolerant of missing pieces.
    t = ((transits or {}).get("transits") or {}).get(planet) or {}
    if t.get("retrograde"):
        s -= _M_RETROGRADE_SUB
    h_from_lagna = t.get("house_from_lagna")
    if h_from_lagna in (1, 4, 5, 7, 9, 10):
        s += 0.20
    elif h_from_lagna in (3, 6, 8, 12):
        s -= 0.05
    if (transits or {}).get("sade_sati") and planet == "Saturn":
        s += 0.20
    # Optional: transit Bhinnashtakavarga bindus (if a precomputed dict given).
    ta = (transits or {}).get("transit_bindus") or {}
    if isinstance(ta, dict) and isinstance(ta.get(planet), (int, float)):
        if ta[planet] >= 5:
            s += 0.10
        elif ta[planet] <= 2:
            s -= 0.10
    return max(0.0, min(1.0, s))


def _is_afflicted_by_malefic(planet, chart, lagna_sign):
    """True if same house or 7th aspect from a functional malefic for lagna."""
    if not chart or not lagna_sign:
        return False
    try:
        from antar_engine.practice_engine import is_functional_malefic
    except Exception:
        return False
    p_house = _planet_house(chart, planet)
    if not p_house:
        return False
    planets = (chart or {}).get("planets") or {}
    for q, qd in planets.items():
        if q == planet:
            continue
        if not is_functional_malefic(q, lagna_sign):
            continue
        qh = _planet_house(chart, q)
        if not qh:
            continue
        if qh == p_house or ((p_house - qh) % 12) + 1 == 7:
            return True
    return False


def _planet_lk_flags(planet, lk_data):
    """Return (sleeping_bool, rin_bool) reading the stored lal_kitab_data."""
    sleeping = rin = False
    if not isinstance(lk_data, dict):
        return False, False
    adv = lk_data.get("advanced") or {}
    sl = adv.get("sleeping_planets") or lk_data.get("sleeping_planets") or []
    if isinstance(sl, list):
        for s in sl:
            if isinstance(s, str) and s == planet:
                sleeping = True
                break
            if isinstance(s, dict) and s.get("planet") == planet:
                sleeping = True
                break
    rin_list = adv.get("rin") or adv.get("rin_planets") or lk_data.get("rin") or []
    if isinstance(rin_list, list):
        for r in rin_list:
            if isinstance(r, str) and r == planet:
                rin = True
                break
            if isinstance(r, dict) and r.get("planet") == planet:
                rin = True
                break
    return sleeping, rin


def _compute_M(planet, chart, conditions, dashas, transits, ashtakavarga):
    """Magnitude — 'how lit up' (0..1)."""
    natal = _natal_bindus_norm(planet, chart, ashtakavarga)
    role = _dasha_role(planet, dashas)
    time_s = _time_score(role)
    transit_s = _transit_score(planet, chart, transits, conditions)
    m = (_M_W_NATAL * natal) + (_M_W_TIME * time_s) + (_M_W_TRANSIT * transit_s)
    return max(0.0, min(1.0, m))


def _compute_V(planet, chart, conditions, lk_data, lagna_sign):
    """Valence — 'helping or hurting' (-1..+1)."""
    from antar_engine.practice_engine import (
        is_functional_benefic, is_functional_malefic,
    )
    v = 0.0
    # function
    if is_functional_benefic(planet, lagna_sign):
        v += 0.40
    elif is_functional_malefic(planet, lagna_sign):
        v -= 0.40
    # dignity (independent of M's natal term)
    cond = (conditions or {}).get(planet, {}).get("condition", "")
    v += _DIGNITY_V.get(cond, 0.0)
    # affliction (aspect/conjunction by functional malefic)
    if _is_afflicted_by_malefic(planet, chart, lagna_sign):
        v -= 0.20
    # lal kitab
    sleeping, rin = _planet_lk_flags(planet, lk_data)
    if sleeping:
        v -= 0.40
    if rin:
        v -= 0.50
    # house — dushthana only subtracts when classically afflicted there
    h = _planet_house(chart, planet)
    if h in (6, 8, 12):
        if cond in ("debilitated", "combust") or _is_afflicted_by_malefic(planet, chart, lagna_sign):
            v -= 0.10
    return max(-1.0, min(1.0, v))


def _state_from_axes(m, v):
    if m >= _STATE_M_HI and v >= _STATE_V_HI:
        return "FLOWING"
    if m >= _STATE_M_HI and v <= _STATE_V_LO:
        return "FRICTION"
    if m < _STATE_M_LO and v <= _STATE_V_LO:
        return "DEPLETED"
    if m < _STATE_M_LO and v >= _STATE_V_HI:
        return "DORMANT"
    return "NEEDS_BALANCE"


def _wellness_from_axes(m, v):
    """Correction A — additive form.  M amplifies V instead of gating it."""
    raw = _W_BASE + (_W_V * v) + (_W_VM * v * m)
    return int(round(100 * max(0.0, min(1.0, raw))))


# Legacy state mapping (backwards compat for any frontend still reading the
# old enum).  The new STATE field is the authoritative one.
_LEGACY_STATE_FROM_NEW = {
    "FLOWING":       "strong",
    "FRICTION":      "weak",
    "DEPLETED":      "blocked",
    "DORMANT":       "balanced",
    "NEEDS_BALANCE": "balanced",
}
# [chakra-2axis] END



def _planet_house(chart, planet):
    """House (1-12) of a planet; uses chart's house field, else whole-sign fallback."""
    pdata = ((chart or {}).get("planets") or {}).get(planet) or {}
    h = pdata.get("house")
    if isinstance(h, int) and 1 <= h <= 12:
        return h
    sign = pdata.get("sign")
    lagna = (chart or {}).get("lagna") or {}
    lsign = lagna.get("sign") if isinstance(lagna, dict) else None
    if sign in SIGNS_12 and lsign in SIGNS_12:
        return ((SIGNS_12.index(sign) - SIGNS_12.index(lsign)) % 12) + 1
    return None


def _benefic_aspect_info(chart, target_house):
    """(aspected_by_benefic, benefic_in_kendra_or_trikona) for `target_house`."""
    if not target_house:
        return (False, False)
    planets = (chart or {}).get("planets") or {}
    aspected = from_kt = False
    for b in _BENEFICS:
        if b not in planets:
            continue
        hb = _planet_house(chart, b)
        if not hb:
            continue
        offset = ((target_house - hb) % 12) + 1
        if offset in _BENEFIC_ASPECTS[b]:
            aspected = True
            if hb in _KENDRA_TRIKONA:
                from_kt = True
    return (aspected, from_kt)


def _ruler_strength(planet, condition, chart):
    """0-100 strength of one ruling planet, with house + benefic-aspect modifiers."""
    s = PLANET_STRENGTH_PCT.get(condition, 55)
    h = _planet_house(chart, planet)
    if h is not None:
        aspected, from_kt = _benefic_aspect_info(chart, h)
        if h in (6, 8, 12) and not aspected:
            s -= 10
        if aspected and from_kt:
            s += 5
    return max(0, min(100, s))


def _chakra_score_pct(states, chart):
    """Average of the chakra's ruling planets' strengths, 0-100 int."""
    vals = [_ruler_strength(p, c, chart) for p, c in states]
    if not vals:
        return 55
    return int(round(max(0, min(100, sum(vals) / len(vals)))))


def _state_from_score(score_pct):
    if score_pct >= 80:
        return "strong"
    if score_pct >= 60:
        return "balanced"
    if score_pct >= 35:
        return "weak"
    return "blocked"

# Plain-language condition word for the reason string.
_COND_WORD = {
    "en": {"exalted": "exalted", "own_sign": "in its own sign", "friend": "well-placed",
           "neutral": "neutral", "enemy": "strained", "debilitated": "weak",
           "combust": "overshadowed", "sleeping": "dormant"},
    "es": {"exalted": "exaltada", "own_sign": "en su propio signo", "friend": "bien sostenida",
           "neutral": "neutral", "enemy": "tensionada", "debilitated": "débil",
           "combust": "eclipsada", "sleeping": "dormida"},
}


# ── Chakra balancing mantras (bija) + Solfeggio tone for the chakra sheet ────
CHAKRA_MANTRAS = {
    "root":         {"name": "Om Lam",  "sanskrit": "ॐ लं",  "translit": "OM LAM",  "tone_hz": 396},
    "sacral":       {"name": "Om Vam",  "sanskrit": "ॐ वं",  "translit": "OM VAM",  "tone_hz": 417},
    "solar_plexus": {"name": "Om Ram",  "sanskrit": "ॐ रं",  "translit": "OM RAM",  "tone_hz": 528},
    "heart":        {"name": "Om Yam",  "sanskrit": "ॐ यं",  "translit": "OM YAM",  "tone_hz": 639},
    "throat":       {"name": "Om Aim",  "sanskrit": "ॐ ऐं",  "translit": "OM AIM",  "tone_hz": 741},
    "third_eye":    {"name": "Om Ksham","sanskrit": "ॐ क्षं", "translit": "OM KSHAM","tone_hz": 852},
    "crown":        {"name": "Om",      "sanskrit": "ॐ",     "translit": "OM",      "tone_hz": 963},
}


def build_chakra_mantra_response(chakra_key: str, language: str = "en") -> dict:
    """Chakra-specific balancing mantra with audio_url + tone_hz, or {}."""
    from antar_engine.practice_library import AUDIO_BASE, _audio_lang
    m = CHAKRA_MANTRAS.get(chakra_key)
    if not m:
        return {}
    lang = _audio_lang(language)
    return {
        "name": m["name"],
        "sanskrit": m["sanskrit"],
        "transliteration": m["translit"],
        "count": 108,
        "duration_minutes": 12,
        "audio_url": f"{AUDIO_BASE}/chakra-{chakra_key}-{lang}.mp3",
        "tone_hz": m["tone_hz"],
    }


def _lang(language: str) -> str:
    return "es" if str(language).lower().startswith("es") else "en"


def _reason(rulers_states: list[tuple], state: str, lang: str) -> str:
    from antar_engine.practice_scopes import _energy as _nrg
    _conn = "se lee" if lang == "es" else "reads"
    parts = [f"{_nrg(p, lang)} {_conn} {_COND_WORD[lang].get(c, c)}" for p, c in rulers_states]
    joined = (" y " if lang == "es" else " and ").join(parts) if len(parts) <= 2 else \
        ((", ".join(parts[:-1])) + (" y " if lang == "es" else " and ") + parts[-1])
    if lang == "es":
        tail = {"strong": "— este centro tiene buen sostén.",
                "balanced": "— este centro está equilibrado.",
                "weak": "— este centro pide atención.",
                "blocked": "— este centro está bloqueado y necesita trabajo."}[state]
        return f"{joined.capitalize()} {tail}"
    tail = {"strong": "— this center is well supported.",
            "balanced": "— this center is balanced.",
            "weak": "— this center needs attention.",
            "blocked": "— this center is blocked and needs work."}[state]
    return f"{joined.capitalize()} {tail}"


def compute_chakra_states(
    chart: dict,
    conditions: Optional[dict] = None,
    priority_planet: Optional[str] = None,
    language: str = "en",
    *,
    ashtakavarga: Optional[dict] = None,
    dashas: Optional[dict] = None,
    lk_data: Optional[dict] = None,
    transits: Optional[dict] = None,
    lagna_sign: Optional[str] = None,
) -> dict:
    """
    Two-axis chakra diagnostic.  For every chakra returns:
      state          : FLOWING | FRICTION | DEPLETED | DORMANT | NEEDS_BALANCE
      magnitude      : 0..1
      valence        : -1..+1
      wellness       : 0..100 (drives the % UI shows)
      score_pct      : alias of wellness (legacy frontend reads this field)
      reason         : plain-language one-liner (energy-translation; no jargon)
      priority       : primary | secondary | none
      active_dasha   : True iff a contributing planet is the current MD or AD
      planets        : {planet: {M, V, wellness, state, weight}}
    """
    lang = _lang(language)
    if conditions is None:
        from antar_engine.places_conditions import compute_all_conditions
        conditions = compute_all_conditions(chart)
    if not lagna_sign:
        lagna_sign = _lagna_sign_name(chart)

    # Per-planet axes computed once, reused across chakras.
    per_planet = {}
    try:
        from antar_engine.places_intel import get_dasha_context
        _dctx = get_dasha_context(dashas, "en") if dashas else {}
    except Exception:
        _dctx = {}
    md_lord = (_dctx or {}).get("md_lord")
    ad_lord = (_dctx or {}).get("ad_lord")

    for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                   "Venus", "Saturn", "Rahu", "Ketu"):
        m = _compute_M(planet, chart, conditions, dashas, transits, ashtakavarga)
        v = _compute_V(planet, chart, conditions, lk_data, lagna_sign)
        st = _state_from_axes(m, v)
        w = _wellness_from_axes(m, v)
        per_planet[planet] = {
            "M": round(m, 3),
            "V": round(v, 3),
            "wellness": w,
            "state": st,
        }

    out = {}
    for chakra in CHAKRA_ORDER:
        weights = CANONICAL_CHAKRA_WEIGHTS.get(chakra, {})
        if not weights:
            out[chakra] = {
                "state": "NEEDS_BALANCE",
                "magnitude": 0.0, "valence": 0.0,
                "wellness": 50, "score_pct": 50,
                "active_dasha": False,
                "priority": "none", "reason": "",
                "planets": {},
            }
            continue

        # Weighted means of M, V, wellness — order-independent; weights sum to 1.
        total_w = sum(weights.values()) or 1.0
        sum_m = sum(per_planet[p]["M"] * w for p, w in weights.items())
        sum_v = sum(per_planet[p]["V"] * w for p, w in weights.items())
        sum_w = sum(per_planet[p]["wellness"] * w for p, w in weights.items())
        chakra_m = sum_m / total_w
        chakra_v = sum_v / total_w
        chakra_wellness = int(round(max(0.0, min(100.0, sum_w / total_w))))
        # Chakra state = state-of-weighted-mean, BUT escalate on affliction:
        # an afflicted ruler is not painted over by a healthier partner.  The
        # wellness % already smooths via the weighted mean — the state field
        # should still flag friction/depletion when present.  Thresholds and
        # weights stay as documented; this is rollup logic, not threshold drift.
        chakra_state = _state_from_axes(chakra_m, chakra_v)
        _ruler_states = [(p, w, per_planet[p]["state"]) for p, w in weights.items()]
        # FRICTION / DEPLETED on any ruler with weight ≥ 0.4 wins over a mean.
        for p, w, st_p in _ruler_states:
            if w >= 0.4 and st_p == "FRICTION":
                chakra_state = "FRICTION"
                break
        if chakra_state != "FRICTION":
            for p, w, st_p in _ruler_states:
                if w >= 0.4 and st_p == "DEPLETED":
                    chakra_state = "DEPLETED"
                    break
        # DORMANT on the primary ruler propagates (a sleeping primary defines
        # the chakra), but never overrides an active affliction above.
        if chakra_state not in ("FRICTION", "DEPLETED"):
            primary = max(weights.items(), key=lambda kv: kv[1])[0]
            if per_planet[primary]["state"] == "DORMANT":
                chakra_state = "DORMANT"
        # FLOWING only if BOTH rulers are non-afflicted AND the mean clears the
        # threshold — prevents a single positive ruler from inflating a chakra
        # that has a deeply afflicted partner.
        if chakra_state == "FLOWING":
            if any(st_p in ("FRICTION", "DEPLETED") for _, _, st_p in _ruler_states):
                chakra_state = "NEEDS_BALANCE"

        active_dasha = any(p in weights for p in (md_lord, ad_lord) if p)

        if priority_planet and priority_planet in weights:
            priority = "primary"
        elif chakra_state in ("FRICTION", "DEPLETED"):
            priority = "secondary"
        else:
            priority = "none"

        # Reason — pull each ruler's dignity condition for the legacy narrator
        states_for_reason = []
        for p in weights:
            c = (conditions or {}).get(p, {}).get("condition")
            if c:
                states_for_reason.append((p, c))
        legacy_state = _LEGACY_STATE_FROM_NEW.get(chakra_state, "balanced")
        try:
            reason = _reason(states_for_reason, legacy_state, lang) if states_for_reason else ""
        except Exception:
            reason = ""

        out[chakra] = {
            # New (authoritative)
            "state": chakra_state,
            "magnitude": round(chakra_m, 3),
            "valence": round(chakra_v, 3),
            "wellness": chakra_wellness,
            "active_dasha": bool(active_dasha),
            # Legacy aliases for backwards compatibility
            "score_pct": chakra_wellness,
            "priority": priority,
            "reason": reason,
            # Per-planet breakdown (lets the UI render planet glow/size)
            "planets": {p: dict(per_planet[p], weight=weights[p]) for p in weights},
        }
    return out
