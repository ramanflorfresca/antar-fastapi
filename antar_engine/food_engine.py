"""
food_engine.py — Chart-level Food (Ahar) engine.

PHASE A — deterministic (NO LLM): produces a "food brief", not foods.
  dosha tendency (lagna element + Moon sign + dominant planet) ->
  guna-need direction (fixed rule table) -> period modifier off the
  current Vimsottari MD (reuses the endpoint's existing dasha read) ->
  planetary affinity (engine planet weekday anchor + afflicted-malefic
  reduce tag).

PHASE B — Haiku localization (the ONLY LLM job): turns the locked
  favor/reduce quality tags into real everyday local foods for
  (region, language). The LLM NEVER decides what is good/bad for the
  chart — direction is locked in Phase A.

GUARDRAILS (ED-safety, deterministic filter on LLM output):
  reject any digit/quantity, portion/serving/diet/restrict/weight-loss/
  burn/deficit language, meal-by-meal schedules, planet names, jargon.
  Fail -> regenerate once tightened -> fall back to category-level
  generic (no food list). Never ship a banned-language list.

CACHE: chart_food_cache keyed by hash(brief signature + region +
language). Chart-stable — regenerates only on period shift.

Emitted as top-level `chart_food` on /predict/daily-practice. Free.
"""
from antar_engine.constants import HAIKU_MODEL

from __future__ import annotations
import asyncio
import hashlib
import json
import os
import re
from datetime import date
from typing import Optional

# ─────────────────────────── PHASE A: FIXED KNOWLEDGE ───────────────────────

SIGN_ELEMENT = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}

# element -> dosha tendency (classical mapping, simplified to one vote each)
ELEMENT_DOSHA = {"earth": "kapha", "water": "kapha", "fire": "pitta", "air": "vata"}

PLANET_DOSHA = {
    "Sun": "pitta", "Mars": "pitta", "Ketu": "pitta",
    "Moon": "kapha", "Venus": "kapha", "Jupiter": "kapha",
    "Saturn": "vata", "Rahu": "vata", "Mercury": "vata",
}

# Guna-need direction per dosha — the "what makes me X" axis. FIXED.
#   sattva = clarity/light/calm-focus; rajas = drive/heat/restlessness;
#   tamas = heavy/sleepy/dull.
GUNA_BY_DOSHA = {
    "kapha": {  # base risk = tamas -> lift it
        "risk": "tamas",
        "favor": ["clarifying", "light", "warm", "lightly-spiced"],
        "reduce": ["heavy", "fried", "cold", "oily", "excess-dairy"],
    },
    "pitta": {  # base risk = rajas -> cool it
        "risk": "rajas",
        "favor": ["cooling", "clarifying", "fresh", "calming"],
        "reduce": ["very-spicy", "sour", "fermented", "stimulants"],
    },
    "vata": {   # ungrounded -> ground it
        "risk": "rajas",
        "favor": ["warm", "grounding", "moist", "cooked"],
        "reduce": ["raw", "cold", "dry", "excess-stimulants"],
    },
}

# Period modifier — read off the current Vimsottari MD lord (passed in;
# never recomputed here).
HOT_PLANETS = {"Sun", "Mars", "Ketu"}      # overheated stretch -> pull rajas down
HEAVY_PLANETS = {"Saturn", "Rahu"}          # low/heavy stretch -> lift tamas

# Planetary food-family affinity (quality TAGS, never foods).
PLANET_FAVOR_FAMILY = {
    "Sun": "golden-warm", "Moon": "soft-moist", "Mars": "lightly-warming",
    "Mercury": "green-fresh", "Jupiter": "golden-nourishing",
    "Venus": "fresh-sweet", "Saturn": "simple-grounding",
    "Rahu": "clean-simple", "Ketu": "light-cleansing",
}
PLANET_REDUCE_FAMILY = {
    "Sun": "excess-salty", "Moon": "excess-dairy", "Mars": "very-spicy",
    "Mercury": "over-processed", "Jupiter": "over-sweet",
    "Venus": "over-rich", "Saturn": "heavy-oily",
    "Rahu": "stale-processed", "Ketu": "over-fermented",
}
PLANET_WEEKDAY = {
    "Sun": "Sunday", "Moon": "Monday", "Mars": "Tuesday",
    "Mercury": "Wednesday", "Jupiter": "Thursday", "Venus": "Friday",
    "Saturn": "Saturday", "Rahu": "Saturday", "Ketu": "Tuesday",
}

DISCLAIMER = ("General lifestyle information, not medical or dietary advice. "
              "For nutrition or health decisions, consult a qualified professional.")


# ─────────────────────────── PHASE A: EXTRACTORS ─────────────────────────────

def _norm_sign(s) -> str:
    if isinstance(s, dict):
        s = s.get("sign") or s.get("rashi") or ""
    if not isinstance(s, str):
        return ""
    s = s.strip().capitalize()
    return s if s in SIGN_ELEMENT else ""


def _lagna_sign(chart: dict) -> str:
    chart = chart or {}
    return _norm_sign(chart.get("lagna") or chart.get("lagna_sign")
                      or (chart.get("ascendant") or {}).get("sign") or "")


def _moon_sign(chart: dict) -> str:
    planets = (chart or {}).get("planets") or {}
    return _norm_sign((planets.get("Moon") or {}))


def _engine_planet(chart: dict) -> Optional[dict]:
    """Chart's beneficial ENGINE planet — reuse the deterministic gemstone
    selector (yogakaraka -> lagna lord -> strongest benefic lord)."""
    try:
        from antar_engine.practice_engine import select_chart_gemstone, _extract_planets, _extract_lagna
        gem = select_chart_gemstone(_extract_planets(chart), _extract_lagna(chart))
        return gem  # {planet, weekday, ...} or None
    except Exception:
        return None


def _afflicted_malefic(chart: dict) -> Optional[str]:
    """A functional malefic for this lagna sitting debilitated -> ease its foods."""
    try:
        from antar_engine.practice_engine import (
            GEM_FUNCTIONAL_MALEFICS, _gem_dignity_rank, _gem_planet_sign)
        lagna = _lagna_sign(chart)
        planets = (chart or {}).get("planets") or {}
        for m in sorted(GEM_FUNCTIONAL_MALEFICS.get(lagna, set()) | {"Rahu", "Ketu"}):
            if _gem_dignity_rank(m, _gem_planet_sign(planets, m)) == 1:
                return m
    except Exception:
        pass
    return None


def _current_md_planet(dashas: dict) -> str:
    """Current Vimsottari MD lord from the endpoint's existing dasha read."""
    try:
        today = date.today().isoformat()
        for d in (dashas or {}).get("vimsottari", []):
            lvl = str(d.get("level") or "").lower()
            if lvl and "maha" not in lvl:
                continue
            start = str(d.get("start_date") or d.get("start") or "")[:10]
            end = str(d.get("end_date") or d.get("end") or "")[:10]
            if start and end and start <= today <= end:
                return str(d.get("planet_or_sign") or d.get("lord_or_sign") or "")
    except Exception:
        pass
    return ""


# ─────────────────────────── PHASE A: BRIEF BUILDER ──────────────────────────

def build_food_brief(chart: dict, dashas: dict, current_country: str = "",
                     language: str = "en") -> dict:
    """Deterministic food brief. Chart-stable until period shift. NO LLM."""
    lagna = _lagna_sign(chart)
    moon = _moon_sign(chart)
    engine = _engine_planet(chart) or {}
    engine_pl = engine.get("planet") or ""

    # 1. Dosha tendency: one vote each — lagna element, Moon-sign element,
    #    dominant (engine) planet. Tie -> dual dosha.
    votes = {}
    for d in (ELEMENT_DOSHA.get(SIGN_ELEMENT.get(lagna, ""), None),
              ELEMENT_DOSHA.get(SIGN_ELEMENT.get(moon, ""), None),
              PLANET_DOSHA.get(engine_pl, None)):
        if d:
            votes[d] = votes.get(d, 0) + 1
    if not votes:
        votes = {"kapha": 1}
    top = max(votes.values())
    leaders = [d for d in ("kapha", "pitta", "vata") if votes.get(d) == top]
    dosha = "-".join(leaders[:2]) if len(leaders) > 1 else leaders[0]

    # 2. Guna-need direction (fixed table; dual dosha merges, deduped).
    favor, reduce = [], []
    for d in leaders[:2]:
        g = GUNA_BY_DOSHA[d]
        favor += [t for t in g["favor"] if t not in favor]
        reduce += [t for t in g["reduce"] if t not in reduce]

    # 3. Period modifier off the current dasha state (reused, not recomputed).
    md = _current_md_planet(dashas)
    if md in HOT_PLANETS:
        period_modifier = "cool_the_period"   # overheated -> pull rajas down
        for t in ("very-spicy", "stimulants", "fermented"):
            if t not in reduce:
                reduce.append(t)
        if "cooling" not in favor:
            favor.append("cooling")
    elif md in HEAVY_PLANETS:
        period_modifier = "lighten_the_period"  # heavy stretch -> lift tamas
        for t in ("light", "warm", "lightly-spiced"):
            if t not in favor:
                favor.append(t)
        for t in ("heavy", "fried"):
            if t not in reduce:
                reduce.append(t)
    else:
        period_modifier = "steady"

    # 4. Planetary affinity: engine planet's food family (esp. its weekday,
    #    already anchored in the stack); ease an afflicted malefic's family.
    if engine_pl and PLANET_FAVOR_FAMILY.get(engine_pl):
        t = PLANET_FAVOR_FAMILY[engine_pl]
        if t not in favor:
            favor.append(t)
    weekday_anchor = engine.get("weekday") or PLANET_WEEKDAY.get(engine_pl, "")
    if weekday_anchor == "contextual":
        weekday_anchor = ""
    afflicted = _afflicted_malefic(chart)
    if afflicted and PLANET_REDUCE_FAMILY.get(afflicted):
        t = PLANET_REDUCE_FAMILY[afflicted]
        if t not in reduce:
            reduce.append(t)

    region = (current_country or "").strip().upper() or "GLOBAL"
    lang = (str(language or "en").split("_")[0].split("-")[0].lower()) or "en"
    return {
        "dosha": dosha,
        "favor": favor,
        "reduce": reduce,
        "weekday_anchor": weekday_anchor,
        "period_modifier": period_modifier,
        "region": region,
        "language": lang,
        # internal — never serialized to the client (popped in get_chart_food)
        "_engine_planet": engine_pl,
        "_md_planet": md,
        "_afflicted": afflicted or "",
    }


def brief_signature(brief: dict) -> str:
    """Cache key = hash(signature + region + language). Period-stable."""
    sig = "|".join([
        brief.get("dosha", ""),
        ",".join(brief.get("favor", [])),
        ",".join(brief.get("reduce", [])),
        brief.get("period_modifier", ""),
        brief.get("weekday_anchor", ""),
        brief.get("region", ""),
        brief.get("language", ""),
    ])
    return hashlib.md5(sig.encode()).hexdigest()[:24]


# ─────────────────────────── GUARDRAILS (ED-SAFETY) ──────────────────────────

# Any digit = any quantity -> banned outright (units, portions, schedules
# all carry numbers; "no amounts" is the rule, so digits fail fast).
_DIGIT_RX = re.compile(r"\d")
_BANNED_RX = re.compile(
    r"(?i)(\bportion\w*\b|\bserving\w*\b|\bweight[- ]?loss\b|\blose weight\b|"
    r"\bweigh\w*\b|\brestrict\w*\b|\bcut (?:out|down)\b|\bdiet\w*\b|"
    r"\bburn\w*\b|\bdeficit\w*\b|\bcalorie\w*\b|\bkcal\b|\bgrams?\b|"
    r"\bounces?\b|\bfasting\b|\bskip (?:meals?|breakfast|lunch|dinner)\b|"
    r"\b(?:breakfast|lunch|dinner)\s*[:\-]|\bfor (?:breakfast|lunch|dinner)\b|"
    r"\bmeal[- ]?plan\w*\b)"
)
# Zero astrological jargon in user-facing text (stack rule 12).
_JARGON_RX = re.compile(
    r"(?i)\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"nakshatra|dasha|mahadasha|antardasha|lagna|ascendant|transit|"
    r"zodiac|horoscope|astrolog\w*|kapha|pitta|vata|dosha|"
    r"sattv\w*|rajas\w*|tamas\w*|\d{1,2}(?:st|nd|rd|th)\s+house)\b"
)

EFFECT_TAGS = {"sharpen", "energize", "ground"}


def _texts_of(payload: dict):
    for item in payload.get("nourish", []):
        yield str(item.get("food", ""))
    for item in payload.get("ease_off", []):
        yield str(item.get("food", ""))
    yield str(payload.get("why", ""))
    yield str(payload.get("weekday_note", ""))


def validate_food_output(payload) -> Optional[dict]:
    """Deterministic filter. Any violation -> None (caller regenerates/falls back)."""
    if not isinstance(payload, dict):
        return None
    nourish = payload.get("nourish")
    ease_off = payload.get("ease_off")
    why = payload.get("why")
    note = payload.get("weekday_note", "")
    if not isinstance(nourish, list) or not (3 <= len(nourish) <= 6):
        return None
    if not isinstance(ease_off, list) or not (2 <= len(ease_off) <= 4):
        return None
    if not isinstance(why, str) or not (20 <= len(why) <= 600):
        return None
    clean_n, clean_e = [], []
    for it in nourish:
        if not isinstance(it, dict):
            return None
        food = str(it.get("food", "")).strip()
        tag = str(it.get("effect_tag", "")).strip().lower()
        if not food or len(food) > 80 or tag not in EFFECT_TAGS:
            return None
        clean_n.append({"food": food, "effect_tag": tag})
    for it in ease_off:
        if not isinstance(it, dict):
            return None
        food = str(it.get("food", "")).strip()
        if not food or len(food) > 80:
            return None
        clean_e.append({"food": food})
    out = {"nourish": clean_n, "ease_off": clean_e,
           "why": why.strip(), "weekday_note": str(note or "").strip()[:200]}
    for txt in _texts_of(out):
        if _DIGIT_RX.search(txt) or _BANNED_RX.search(txt) or _JARGON_RX.search(txt):
            return None
    return out


def _generic_fallback(brief: dict) -> dict:
    """Category-level generic — NO food list, fail-safe."""
    favor = ", ".join(t.replace("-", " ") for t in brief.get("favor", [])[:4])
    reduce = ", ".join(t.replace("-", " ") for t in brief.get("reduce", [])[:3])
    why = (f"This period favors {favor} foods. "
           f"Ease off {reduce} foods when you can — gently, never strictly.")
    note = (f"{brief['weekday_anchor']} is a natural day to lean into this."
            if brief.get("weekday_anchor") else "")
    return {"nourish": [], "ease_off": [], "why": why, "weekday_note": note,
            "fallback": True}


# ─────────────────────────── PHASE B: HAIKU LOCALIZATION ─────────────────────

FOOD_MODEL = os.getenv("FOOD_LOCALIZE_MODEL", HAIKU_MODEL)
_FOOD_TIMEOUT_S = float(os.getenv("FOOD_LOCALIZE_TIMEOUT_S", "8.0"))
_CACHE_TABLE = "chart_food_cache"

_anthropic_client = None


def _get_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _anthropic_client


# Static block (byte-stable for KV cache); live brief goes below the split.
_LOCALIZE_STATIC = """You localize a fixed nourishment direction into everyday local foods.

The chart engine has ALREADY decided the direction — which food qualities to
FAVOR and which to gently REDUCE. You never decide what is good or bad for
this person; you only express the locked quality tags as real, everyday,
affordable foods that are common in the given region.

HARD RULES:
1. "nourish": 4 to 6 everyday foods or simple home dishes common in region
   <region>, each one expressing the FAVOR tags. Each item:
   {"food": "...", "effect_tag": "sharpen"|"energize"|"ground"}.
2. "ease_off": 2 to 4 everyday foods matching the REDUCE tags, each item
   {"food": "..."}. Neutral wording — "ease off", never "avoid" or "cut".
3. "why": two or three plain sentences linking these qualities to feeling
   lighter, clearer and steadier. No science claims, no body-shape talk.
4. "weekday_note": one warm line tying <weekday_anchor> (if given) to leaning
   into the nourish list a little more that day. Empty string if no anchor.
5. POSITIVE nourishment framing only. Food TYPES, never meal plans. NEVER
   any number, quantity, unit, portion, serving, calorie, weight, diet,
   restriction, fasting or schedule language. No medical claims.
6. Write in language <language>. Keep proper dish names canonical.
7. ZERO jargon: no planet names, no Sanskrit, no dosha/guna words, no
   astrology terms.
8. Output STRICT JSON and nothing else:
   {"nourish":[...], "ease_off":[...], "why":"...", "weekday_note":"..."}

## LIVE DATA
"""

_TIGHTEN = ("\nREMINDER: your previous attempt violated the rules. ABSOLUTELY NO "
            "digits, quantities, units, portions, servings, diet/weight/restrict/"
            "burn language, meal schedules, or astrology/dosha words anywhere.")


def _public_brief(brief: dict) -> dict:
    return {k: v for k, v in brief.items() if not k.startswith("_")}


async def _haiku_localize(brief: dict, tightened: bool = False) -> Optional[dict]:
    client = _get_client()
    system = _LOCALIZE_STATIC + json.dumps(_public_brief(brief), ensure_ascii=False)
    if tightened:
        system += _TIGHTEN
    resp = await asyncio.wait_for(
        client.messages.create(
            model=FOOD_MODEL,
            max_tokens=700,
            temperature=0.4,
            system=system,
            messages=[{"role": "user", "content":
                       f"Localize for region={brief['region']} language={brief['language']}."}],
        ),
        timeout=_FOOD_TIMEOUT_S,
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "text", None))
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return validate_food_output(json.loads(raw[start:end + 1]))
    except Exception:
        return None


# ─────────────────────────── CACHE + ENTRY POINT ─────────────────────────────

def _cache_read(supabase, key: str) -> Optional[dict]:
    try:
        res = supabase.table(_CACHE_TABLE).select("payload")             .eq("cache_key", key).limit(1).execute()
        if res.data:
            p = res.data[0].get("payload")
            if isinstance(p, str):
                p = json.loads(p)
            if isinstance(p, dict):
                return p
    except Exception as e:
        print(f"[chart-food] cache read skipped: {e}")
    return None


def _cache_write(supabase, key: str, payload: dict) -> None:
    try:
        supabase.table(_CACHE_TABLE).upsert(
            {"cache_key": key, "payload": payload},
            on_conflict="cache_key").execute()
    except Exception as e:
        print(f"[chart-food] cache write skipped (table missing?): {e}")


async def get_chart_food(supabase, chart: dict, dashas: dict,
                         current_country: str = "", language: str = "en") -> dict:
    """Full pipeline: Phase A brief -> cache -> Phase B Haiku -> guardrails.
    Always returns a safe dict; never raises."""
    brief = build_food_brief(chart, dashas, current_country, language)
    key = brief_signature(brief)
    base = {**_public_brief(brief), "cache_key": key, "disclaimer": DISCLAIMER}

    cached = _cache_read(supabase, key)
    if cached and validate_food_output(cached):
        return {**base, **validate_food_output(cached)}

    localized = None
    try:
        localized = await _haiku_localize(brief)
        if localized is None:  # regenerate ONCE, tightened
            localized = await _haiku_localize(brief, tightened=True)
    except Exception as e:
        print(f"[chart-food] localization failed: {e}")
        localized = None

    if localized is None:  # fail safe — category-level generic, no list
        return {**base, **_generic_fallback(brief)}

    _cache_write(supabase, key, localized)
    return {**base, **localized}
