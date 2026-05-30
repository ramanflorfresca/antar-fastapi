"""
antar_engine/home_composer.py

Home endpoint composition — assembles four HorizonView blocks
(today / month / year / cycle) per HOME_API_Contract.md.

Thin orchestration only. No LLM calls. Reuses:
  - lal_kitab_masik   (masik phal house math + PLANET_NATURE + HOUSE_THEMES)
  - muhurta_engine    (best/avoid time windows for "today")
  - dasha_periods     (current MD/AD — looked up in main.py, passed in)

Polarity rule (per contract):
  positive  →  "use" set, chain (cause/remedy/chakra/practice) all None
  negative  →  "use" None, chain populated
The composer enforces this XOR — engines never decide it directly.
"""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any

from antar_engine.lal_kitab_masik import (
    HOUSE_THEMES, PLANET_NATURE, POWERFUL_HOUSES, DIFFICULT_HOUSES,
    _months_since_birthday,
)


# ── Static maps (English source; @translate_response translates at response time) ──

ENERGY_LANG = {
    "Sun":     "your authority and self-direction",
    "Moon":    "your emotional steadiness",
    "Mars":    "your drive and ability to act",
    "Mercury": "your clarity of thought and speech",
    "Jupiter": "your sense of meaning and growth",
    "Venus":   "your relationships and harmony",
    "Saturn":  "your discipline and patience",
    "Rahu":    "your ambition and focus",
    "Ketu":    "your detachment and inner stillness",
}

# Planet → chakra (mirrors chakra_engine PLANET_CHAKRAS primary)
PLANET_TO_CHAKRA = {
    "Sun":     {"name": "Solar Plexus", "governs": "Confidence, will, personal power"},
    "Moon":    {"name": "Sacral",       "governs": "Feeling, flow, emotional balance"},
    "Mars":    {"name": "Root",         "governs": "Stability, action, survival drive"},
    "Mercury": {"name": "Throat",       "governs": "Voice, clarity, honest expression"},
    "Jupiter": {"name": "Crown",        "governs": "Wisdom, meaning, big-picture sight"},
    "Venus":   {"name": "Heart",        "governs": "Love, harmony, connection"},
    "Saturn":  {"name": "Root",         "governs": "Foundations, discipline, time"},
    "Rahu":    {"name": "Third Eye",    "governs": "Intuition, vision, perception"},
    "Ketu":    {"name": "Crown",        "governs": "Letting go, inner stillness"},
}

# Mantra seed — allowed jargon per contract (mantra seed in practice.name)
MANTRA_SEED = {
    "Sun": "RAM", "Moon": "VAM", "Mars": "LAM", "Mercury": "HAM",
    "Jupiter": "OM", "Venus": "YAM", "Saturn": "LAM",
    "Rahu": "SHAM", "Ketu": "OM",
}

PRACTICE_BY_PLANET = {
    "Sun":     ("Solar Plexus Breath · RAM", 5,
                ["Sit upright with hands on belly",
                 "Inhale 4 counts into the upper belly",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper RAM",
                 "Repeat for 5 minutes"]),
    "Moon":    ("Sacral Breath · VAM", 5,
                ["Sit comfortably, hands on lower belly",
                 "Inhale 4 counts, feel the belly soften",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper VAM",
                 "Repeat for 5 minutes"]),
    "Mars":    ("Root Breath · LAM", 5,
                ["Sit grounded, both feet flat",
                 "Inhale 4 counts, feel feet press down",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper LAM",
                 "Repeat for 5 minutes"]),
    "Mercury": ("Throat Breath · HAM", 5,
                ["Sit tall, chin slightly tucked",
                 "Inhale 4 counts",
                 "Hold 7 counts",
                 "Exhale 8 counts, whisper HAM",
                 "Repeat for 5 minutes"]),
    "Jupiter": ("Crown Breath · OM", 5,
                ["Sit tall, eyes soft",
                 "Inhale 5 counts",
                 "Hold 5 counts",
                 "Exhale 7 counts, whisper OM",
                 "Repeat for 5 minutes"]),
    "Venus":   ("Heart Breath · YAM", 5,
                ["Sit with one hand on the heart",
                 "Inhale 4 counts into the chest",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper YAM",
                 "Repeat for 5 minutes"]),
    "Saturn":  ("Root Breath · LAM", 7,
                ["Sit grounded, feet flat",
                 "Inhale slowly for 5 counts",
                 "Hold 5 counts",
                 "Exhale 7 counts, whisper LAM",
                 "Repeat for 7 minutes"]),
    "Rahu":    ("Third Eye Breath · SHAM", 5,
                ["Sit upright, eyes closed",
                 "Inhale 4 counts, attention between brows",
                 "Hold 4 counts",
                 "Exhale 6 counts, whisper SHAM",
                 "Repeat for 5 minutes"]),
    "Ketu":    ("Crown Breath · OM", 5,
                ["Sit tall, hands resting upward",
                 "Inhale 5 counts",
                 "Hold 5 counts",
                 "Exhale 7 counts, whisper OM",
                 "Repeat for 5 minutes"]),
}

PLANET_DO = {
    "Sun":     "Lead from your own initiative. Make one decision that is yours alone.",
    "Moon":    "Take care of your inner world. Rest, eat well, soft conversations.",
    "Mars":    "Channel energy into one physical task and finish it.",
    "Mercury": "Use the clear head for planning and solo work. Confirm details in writing.",
    "Jupiter": "Reach out to a mentor or share what you have learned with someone.",
    "Venus":   "Invest in a relationship — small, warm, in person.",
    "Saturn":  "Do the slow, structural work that has been waiting.",
    "Rahu":    "Set one ambitious target for the week and break it into a single first step.",
    "Ketu":    "Make space — declutter a corner, drop one obligation, sit quietly.",
}
PLANET_DONT = {
    "Sun":     "Do not wait for permission you do not actually need.",
    "Moon":    "Do not make big choices when feelings are running high.",
    "Mars":    "Do not pick a fight to release pressure.",
    "Mercury": "Do not start big conversations or sign commitments.",
    "Jupiter": "Do not over-promise or over-explain.",
    "Venus":   "Do not smooth over something that actually needs a hard conversation.",
    "Saturn":  "Do not push faster than the work allows. No shortcuts today.",
    "Rahu":    "Do not chase a new shiny goal before finishing what is open.",
    "Ketu":    "Do not drift. Pick one anchor for the day before letting go.",
}

# Short plain-English phrase per AD planet — used to express the MD->AD
# sub-chapter in the Cycle horizon. Replaced by real LK interpretation in
# Phase 2. No planet names leak: the planet is mapped to an energy theme.
AD_PLANET_THEMES = {
    "Sun":     "self & visibility",
    "Moon":    "feeling & nurturing",
    "Mars":    "energy & action",
    "Mercury": "communication & exchange",
    "Jupiter": "growth & meaning",
    "Venus":   "connection & comfort",
    "Saturn":  "discipline & structure",
    "Rahu":    "ambition & the unfamiliar",
    "Ketu":    "release & inward turn",
}

PLANET_AREAS = {
    "Sun":     ["Identity", "Career"],
    "Moon":    ["Family", "Wellbeing"],
    "Mars":    ["Action", "Health"],
    "Mercury": ["Focus", "Communication"],
    "Jupiter": ["Growth", "Learning"],
    "Venus":   ["People", "Relationships"],
    "Saturn":  ["Work", "Discipline"],
    "Rahu":    ["Ambition", "Career"],
    "Ketu":    ["Inner Life", "Letting Go"],
}

WEEKDAY_EN = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
MONTH_EN   = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
MONTH_FULL = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]

CYCLE_INFO = (
    "A phase of life where a planet's influence shapes your path. "
    "Each cycle lasts years, then changes."
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _safe_json(v: Any) -> dict:
    """Mirror of main.py _safe_jsonb — chart_data/lal_kitab_data may be a
    JSON string instead of native JSONB."""
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    if isinstance(v, dict):
        return v
    return {}


def _now_local(tz_offset_min: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=int(tz_offset_min or 0))


def _format_today_range(now: datetime) -> str:
    return f"{WEEKDAY_EN[now.weekday()]} · {MONTH_EN[now.month - 1]} {now.day}"


def _format_month_range(now: datetime) -> str:
    return f"{MONTH_FULL[now.month - 1].upper()} {now.year}"


def _format_year_range(birth_date: str, now: datetime) -> str:
    try:
        born = date.fromisoformat((birth_date or "")[:10])
        age = (now.date() - born).days // 365
        return f"YEAR {age + 1}"
    except Exception:
        return f"{now.year}"


def _format_cycle_range(md_row: Optional[dict]) -> str:
    if not md_row:
        return ""
    try:
        sd = date.fromisoformat(str(md_row.get("start_date", ""))[:10])
        ed = date.fromisoformat(str(md_row.get("end_date", ""))[:10])
        return f"{MONTH_EN[sd.month - 1]} {sd.year} – {MONTH_EN[ed.month - 1]} {ed.year}"
    except Exception:
        return ""


def _natal_houses(chart_data: dict) -> dict:
    """Extract {planet: house} from chart_data. Handles both dict and list shapes."""
    planets = chart_data.get("planets") or chart_data.get("planet_positions") or {}
    if isinstance(planets, dict):
        return {
            p: int(d.get("house") or 0)
            for p, d in planets.items()
            if isinstance(d, dict)
        }
    if isinstance(planets, list):
        out = {}
        for p in planets:
            if isinstance(p, dict):
                nm = p.get("name") or p.get("planet")
                if nm:
                    out[nm] = int(p.get("house") or 0)
        return out
    return {}


def _running_year(birth_date: str) -> int:
    try:
        born = date.fromisoformat((birth_date or "")[:10])
        age = (date.today() - born).days // 365
        return max(1, min(120, age + 1))
    except Exception:
        return 1


def _varshphal_placements(birth_date: str, natal_houses: dict) -> dict:
    ry = _running_year(birth_date)
    return {
        p: ((h - 1 + (ry - 1)) % 12) + 1
        for p, h in natal_houses.items()
        if 1 <= (h or 0) <= 12
    }


def _masik_placements(birth_date: str, natal_houses: dict) -> dict:
    varsh = _varshphal_placements(birth_date, natal_houses)
    off = _months_since_birthday(birth_date)
    return {p: ((h - 1 + off) % 12) + 1 for p, h in varsh.items()}


def _classify(placements: dict) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
    strong = [(p, h) for p, h in placements.items() if h in POWERFUL_HOUSES]
    weak   = [(p, h) for p, h in placements.items() if h in DIFFICULT_HOUSES]
    weak.sort(key=lambda x: x[1])
    strong.sort(key=lambda x: -x[1])
    return strong, weak


def _resolve_polarity(strong: list, weak: list) -> str:
    if len(weak) > len(strong):
        return "negative"
    return "positive"


def _dominant_weak_planet(weak: list, current_md: str = "") -> Optional[str]:
    if not weak:
        return None
    if current_md:
        for p, _ in weak:
            if p.lower() == current_md.lower():
                return p
    return weak[0][0]


def _dominant_strong_planet(strong: list, current_md: str = "") -> Optional[str]:
    if not strong:
        return None
    if current_md:
        for p, _ in strong:
            if p.lower() == current_md.lower():
                return p
    return strong[0][0]


# ── Common chain (positive vs negative) ─────────────────────────────────────

CAUSE_TEXT = {
    "Sun":     "Your self-direction feels uncertain — outside noise is louder than your own signal.",
    "Moon":    "Your emotional steadiness is unsettled — small things land harder than usual.",
    "Mars":    "Your drive feels blocked — starts and finishes are harder.",
    "Mercury": "Your thinking is scattered — timing and details feel slippery.",
    "Jupiter": "Your sense of meaning feels far away — motivation is thin.",
    "Venus":   "Your connections feel strained — warmth needs effort.",
    "Saturn":  "Your patience is being tested — progress feels slow.",
    "Rahu":    "Your focus is pulled in too many directions — decide what matters.",
    "Ketu":    "You feel adrift — small anchors will help.",
}
REMEDY_TEXT = {
    "Sun":     "Pick one decision and own it before the day ends.",
    "Moon":    "Protect sleep and quiet time tonight. Eat warm food.",
    "Mars":    "Move your body for ten minutes before any difficult task.",
    "Mercury": "Slow down. Confirm anything important in writing.",
    "Jupiter": "Read something nourishing for ten minutes. Skip the doom-scroll.",
    "Venus":   "Send one warm message to someone you care about.",
    "Saturn":  "Choose one boring foundational task and complete it fully.",
    "Rahu":    "Close three open tabs — literal or mental.",
    "Ketu":    "Pick one anchor (a meal, a walk, a person) and show up to it.",
}

USE_MAPS = {
    "today": {
        "Sun":     "Lead with your own initiative — make the visible move.",
        "Moon":    "Lean on warm conversations and steady routines.",
        "Mars":    "Take direct action on something you have been delaying.",
        "Mercury": "Front-load the thinking, planning, and writing.",
        "Jupiter": "Teach, mentor, or share — the room is with you.",
        "Venus":   "Reach for connection — a meal, a call, a small gift.",
        "Saturn":  "Do the foundational work — slow and durable wins.",
        "Rahu":    "Push on an ambition — bold direct action lands.",
        "Ketu":    "Edit, release, simplify — clarity is yours.",
    },
    "month": {
        "Sun":     "Make the visible move you have been postponing this month.",
        "Moon":    "Anchor your routines — home, sleep, family steady you now.",
        "Mars":    "This is the month to start and finish — pick one ambitious project.",
        "Mercury": "Use this month for planning, writing, and clear communication.",
        "Jupiter": "Teach or learn — the door is open.",
        "Venus":   "Invest in the people who matter — relationships flower now.",
        "Saturn":  "Build the foundation — durable work compounds this month.",
        "Rahu":    "Front-load visible work — momentum is with you.",
        "Ketu":    "Simplify — drop one obligation that has been weighing.",
    },
    "year": {
        "Sun":     "This is the year to step into leadership.",
        "Moon":    "A year to root your home life and emotional foundations.",
        "Mars":    "Direct action lands this year — start what you have been planning.",
        "Mercury": "A year for clear communication and visible thinking work.",
        "Jupiter": "A year of growth, learning, and meaning.",
        "Venus":   "A year for relationships — invest deeply in the people who matter.",
        "Saturn":  "A year for patient, foundational work that pays off later.",
        "Rahu":    "Front-load visible work before the summer.",
        "Ketu":    "A year to simplify — let go of what is no longer yours.",
    },
    "cycle": {
        "Sun":     "Use this chapter to claim your authority and direction.",
        "Moon":    "A chapter to deepen emotional roots and family.",
        "Mars":    "A chapter of direct action and finishing what you start.",
        "Mercury": "A chapter of clear thinking, planning, and communication.",
        "Jupiter": "A chapter of growth, teaching, and meaning.",
        "Venus":   "A chapter of relationships, art, and harmony.",
        "Saturn":  "A chapter of foundational work — slow, durable, real.",
        "Rahu":    "A chapter to chase ambition with focus.",
        "Ketu":    "A chapter to release, simplify, and turn inward.",
    },
}


_DIGNITY_CHARGE = {
    "exalted": 0.92, "own": 0.78, "friendly": 0.60,
    "neutral": 0.45, "debilitated": 0.18,
}


def _planet_charge(chart_data: dict, planet: str) -> float:
    """Real per-chart chakra charge from planetary dignity (0..1)."""
    if not planet:
        return 0.40
    try:
        from antar_engine.antar_ephemeris import _planet_strength as _dignity
        planets = chart_data.get("planets") or chart_data.get("planet_positions") or {}
        pdata = planets.get(planet) if isinstance(planets, dict) else None
        sign = (pdata.get("sign", "") if isinstance(pdata, dict) else "") or ""
        return _DIGNITY_CHARGE.get(_dignity(planet, sign), 0.45)
    except Exception:
        return 0.40


def _year_stretch_dynamic(chart_data: dict, now: datetime) -> dict:
    """
    Best/worst sub-windows of the coming year from real transit events.
    best  = highest-activity peak-window month run.
    worst = the month of the year's single most significant critical date.
    Falls back to the static season pair on any failure (e.g. no swisseph).
    """
    static = {"best": "Spring", "worst": "Autumn"}
    try:
        from antar_engine.transit_events import compute_transit_events_in_range
        from antar_engine.annual_planning import (
            _aggregate_year_peak_windows, _compute_critical_dates,
        )
        start = now.date()
        try:
            end = start.replace(year=start.year + 1)
        except ValueError:
            end = start.replace(year=start.year + 1, day=28)
        events = compute_transit_events_in_range(chart_data, start, end, include_fast=False)
        if not events:
            return static
        peaks = _aggregate_year_peak_windows(events)
        best_dom = max(
            (d for d in peaks.values() if d.get("months")),
            key=lambda d: d.get("score", 0), default=None,
        )
        best = best_dom["months"] if best_dom and best_dom.get("months") else static["best"]
        worst = static["worst"]
        crit = _compute_critical_dates(events, top_n=1)
        if crit:
            iso = (crit[0].get("raw_date") or "")[:10]
            try:
                cd = date.fromisoformat(iso)
                _mon = cd.strftime("%B")
                worst = (f"Early {_mon}" if cd.day <= 10
                         else f"Late {_mon}" if cd.day >= 20 else _mon)
            except Exception:
                pass
        return {"best": best, "worst": worst}
    except Exception:
        return static


def _build_chain_negative(weak_planet: str, charge: float = 0.40) -> dict:
    chakra = PLANET_TO_CHAKRA.get(weak_planet) or PLANET_TO_CHAKRA["Mercury"]
    name, minutes, steps = PRACTICE_BY_PLANET.get(weak_planet) or PRACTICE_BY_PLANET["Mercury"]
    return {
        "use":      None,
        "cause":    {"planet": weak_planet, "text": CAUSE_TEXT.get(weak_planet, "")},
        "remedy":   REMEDY_TEXT.get(weak_planet, "Pause, breathe, and confirm what matters in writing."),
        "chakra":   {"name": chakra["name"], "governs": chakra["governs"], "charge": round(charge, 2)},
        "practice": {"name": name, "minutes": minutes, "steps": list(steps)},
    }


def _build_chain_positive(strong_planet: str, horizon: str) -> dict:
    use_map = USE_MAPS.get(horizon, USE_MAPS["today"])
    return {
        "use":      use_map.get(strong_planet, "Lean into the strength that is available now."),
        "cause":    None,
        "remedy":   None,
        "chakra":   None,
        "practice": None,
    }


# ── Headline / gist / areas / stretch ───────────────────────────────────────

def _build_headline_gist(horizon: str, polarity: str) -> Tuple[str, str]:
    if polarity == "positive":
        return {
            "today": ("A clear day — energy is on your side.",
                      "Good for momentum, action, and visible work."),
            "month": ("A month with the wind behind you.",
                      "Pick one thing to push on and finish it."),
            "year":  ("A year of forward motion.",
                      "Set the direction now; the months will follow."),
            "cycle": ("A chapter built for steady progress.",
                      "Lean into the strength of this period."),
        }[horizon]
    return {
        "today": ("A quiet day — clarity is here, but outside momentum is low.",
                  "Good for thinking, not for pushing. One area is under pressure."),
        "month": ("A month to plan more than to push.",
                  "One area asks for attention. Take it slow."),
        "year":  ("A year of recalibration.",
                  "Foundations matter more than fireworks."),
        "cycle": ("A chapter asking for patience.",
                  "The lesson is in slowing down, not speeding up."),
    }[horizon]


def _build_areas(strong: list, weak: list) -> list:
    areas: list = []
    seen: set = set()
    for p, _ in strong[:2]:
        nm = (PLANET_AREAS.get(p) or [p])[0]
        if nm in seen:
            continue
        seen.add(nm)
        first_theme = (PLANET_NATURE.get(p, "") or "").split(",")[0].strip() or "this area"
        areas.append({
            "name": nm, "bars": 3, "care": False,
            "note": f"Strong — favourable for {first_theme}.",
        })
    if weak:
        wp, _ = weak[0]
        nm = (PLANET_AREAS.get(wp) or [wp])[0]
        if nm not in seen:
            areas.append({
                "name": nm, "bars": 0, "care": True,
                "note": "Under pressure — postpone decisions in this area.",
            })
            seen.add(nm)
    while len(areas) < 2:
        areas.append({
            "name": "Wellbeing", "bars": 2, "care": False,
            "note": "Steady — keep your usual routine.",
        })
    return areas[:3]


def _build_stretch(horizon: str) -> dict:
    return {
        "today": {"best": "Late morning",   "worst": "Mid-afternoon"},
        "month": {"best": "First half",     "worst": "Last week"},
        "year":  {"best": "Spring",         "worst": "Autumn"},
        "cycle": {"best": "Opening third",  "worst": "Closing third"},
    }[horizon]


# ── Per-horizon composition ─────────────────────────────────────────────────

def _muhurta_windows(chart_row: dict, chart_data: dict,
                      now: datetime, tz_offset_min: int) -> Tuple[Optional[str], Optional[str]]:
    """Return (bestTime, avoidTime) localized strings, or (None, None) on failure."""
    try:
        from antar_engine.muhurta_engine import compute_muhurtas
        lat = float(chart_row.get("latitude") or chart_data.get("latitude") or 0)
        lon = float(chart_row.get("longitude") or chart_data.get("longitude") or 0)
        if not lat or not lon:
            return None, None
        muh = compute_muhurtas(now, lat, lon, tz_offset=float(tz_offset_min) / 60.0)
        ab = (muh or {}).get("abhijit_muhurta") or {}
        rk = (muh or {}).get("rahu_kalam") or {}
        best  = (f"{ab['start_local']} – {ab['end_local']}"
                 if ab.get("start_local") and ab.get("end_local") else None)
        avoid = (f"{rk['start_local']} – {rk['end_local']}"
                 if rk.get("start_local") and rk.get("end_local") else None)
        return best, avoid
    except Exception as e:
        print(f"[home_composer] muhurta calc skipped: {e}")
        return None, None


def _compose_for_horizon(horizon: str,
                          chart_row: dict, chart_data: dict, lk_data: dict,
                          current_md_row: Optional[dict], current_ad_row: Optional[dict],
                          tz_offset_min: int) -> dict:
    natal = _natal_houses(chart_data)
    bd = chart_row.get("birth_date", "") or ""
    md_planet = (current_md_row or {}).get("planet_or_sign", "") or ""

    # AD sub-chapter context (cycle horizon only; harmless defaults elsewhere).
    # Field is `planet_or_sign` on the dasha_periods row (same as MD).
    ad_planet  = None
    ad_house   = 0
    md_end_iso = (current_md_row or {}).get("end_date")
    ad_end_iso = (current_ad_row or {}).get("end_date")

    if horizon == "today" or horizon == "month":
        placements = _masik_placements(bd, natal)
    elif horizon == "year":
        placements = _varshphal_placements(bd, natal)
    else:  # cycle — driven by current MD planet's natal house only
        placements = {}

    if horizon == "cycle":
        if not md_planet:
            md_planet = "Jupiter"
        natal_house = natal.get(md_planet, 0)
        if natal_house in DIFFICULT_HOUSES:
            strong, weak = [], [(md_planet, natal_house)]
        else:
            strong, weak = [(md_planet, natal_house or 1)], []

        # Read the AD planet (already loaded in main.py, passed through).
        if current_ad_row:
            ad_planet = current_ad_row.get("planet_or_sign") or None
        ad_house = natal.get(ad_planet, 0) if ad_planet else 0
    else:
        strong, weak = _classify(placements)

    polarity = _resolve_polarity(strong, weak)
    wp = _dominant_weak_planet(weak, md_planet)
    sp = _dominant_strong_planet(strong, md_planet) or (md_planet if horizon == "cycle" else "Mercury")

    headline, gist = _build_headline_gist(horizon, polarity)
    # MD->AD sub-chapter: only when there is a distinct AD planet.
    if horizon == "cycle" and ad_planet and ad_planet != md_planet:
        _theme = AD_PLANET_THEMES.get(ad_planet, "a new phase")
        gist = f"{gist} Right now, the {_theme} chapter inside it."
    chain = (_build_chain_negative(wp, _planet_charge(chart_data, wp)) if polarity == "negative" and wp
             else _build_chain_positive(sp, horizon))

    now = _now_local(tz_offset_min if horizon == "today" else 0)
    if horizon == "today":
        range_str = _format_today_range(now)
        best_t, avoid_t = _muhurta_windows(chart_row, chart_data, now, tz_offset_min)
        pivot = wp if polarity == "negative" and wp else sp
        do_text   = PLANET_DO.get(pivot,   PLANET_DO["Mercury"])
        dont_text = PLANET_DONT.get(pivot, PLANET_DONT["Mercury"])
        tab = "Today"
    elif horizon == "month":
        range_str = _format_month_range(now)
        best_t = avoid_t = None
        do_text = dont_text = None
        tab = "This Month"
    elif horizon == "year":
        range_str = _format_year_range(bd, now)
        best_t = avoid_t = None
        do_text = dont_text = None
        tab = "This Year"
    else:
        range_str = _format_cycle_range(current_md_row)
        best_t = avoid_t = None
        do_text = dont_text = None
        tab = "Current Cycle"

    phase_block = None
    if horizon == "cycle":
        phase_block = {
            "mahadasha":  {"planet": md_planet, "ends": md_end_iso},
            "antardasha": ({"planet": ad_planet, "ends": ad_end_iso}
                           if ad_planet else None),
        }

    view = {
        "tab":       tab,
        "range":     range_str,
        "polarity":  polarity,
        "headline":  headline,
        "gist":      gist,
        "cycleName": (f"{md_planet} cycle" if horizon == "cycle" and md_planet else None),
        "info":      (CYCLE_INFO if horizon == "cycle" else None),
        "do":        do_text,
        "dont":      dont_text,
        "bestTime":  best_t,
        "avoidTime": avoid_t,
        "areas":     _build_areas(strong, weak),
        "stretch":   (_year_stretch_dynamic(chart_data, now) if horizon == "year" else _build_stretch(horizon)),
        "phase":     phase_block,
    }
    # Polarity XOR — chain merged last
    view.update(chain)
    return view


def compose_home_payload(chart_id: str, chart_row: dict, chart_data: dict, lk_data: dict,
                          current_md_row: Optional[dict], current_ad_row: Optional[dict],
                          language: str, tz_offset: int) -> dict:
    first_name = chart_row.get("first_name") or "Friend"
    initial    = (first_name[:1] or "F").upper()
    horizons   = {}
    for h in ("today", "month", "year", "cycle"):
        horizons[h] = _compose_for_horizon(
            h, chart_row, chart_data, lk_data,
            current_md_row, current_ad_row, int(tz_offset or 0),
        )
    return {
        "chart_id":     chart_id,
        "language":     language,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "user":         {"name": first_name, "initial": initial},
        "horizons":     horizons,
    }
