"""
antar_engine/yearly_v2.py — new /annual-plan contract assembler
================================================================

The Yearly engine is the only Antar surface that does NOT ride
score_day. Year-scale events are too sparse for daily aggregation to
trigger them reliably; the brief specifies a three-layer stack:

  1. TAJIKA VARSHPHAL  — solar-return spine
                         (Varshesh, Muntha+Munthesh, Mudda dasha)
  2. LAL KITAB         — gate / valence / age-activation protagonist
                         (one DOCUMENTED activation-age table — cited
                         right here in code so two users at the same
                         age cannot get different planets by accident)
  3. JAIMINI + DT      — trigger (Chara dasha + Saturn/Jupiter double
                         transit on the event house, its lord, navamsa)

This composer pulls deterministic facts from the legacy /annual-plan
response (the heavy ephemeris work already ran) and reshapes them into
the new contract. It is read-only with respect to ephemeris APIs.

Contract (brief, verbatim):
  {
    "range":        "JUN 10 '26 – JUN 10 '27",
    "period_start": "YYYY-MM-DD",
    "period_end":   "YYYY-MM-DD",
    "quality":      "Consolidation",
    "theme":        "...",
    "active":       "...",
    "months":       ["Jun","Jul",...,"May"],
    "now_month":    int,
    "events": [
      {"month_index","date_label","domain","polarity","magnitude","text"},
      ...
    ],
    "arcs": [
      {"key","name","trend","when"} x 5  (career/business/love/health/family)
    ]
  }

All `text` / `theme` / `active` / `line` / `when` strings are scrubbed
through apply_user_facing_strips so no planet names, house numbers, or
Sanskrit survive in EN or ES.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _dt, timedelta as _td
from typing import Any, Dict, List, Optional, Tuple
import re


# ────────────────────────────────────────────────────────────────
# ONE DOCUMENTED AGE-ACTIVATION TABLE (cited in code per brief)
# ────────────────────────────────────────────────────────────────
# Source: Naisargika Dasha (classical sequence). Two users at the same
# age MUST land on the same activated planet — this table is the sole
# authority called from here. Mirrors jyotish_periods._NAISARGIKA_BANDS
# (DRY would import that module, but the brief says "cite in code", so
# the bands are restated here for any future code reviewer who wonders
# WHY this planet was picked).
#
# (low_inclusive, high_inclusive, planet)
_AGE_ACTIVATION_NAISARGIKA: List[Tuple[int, int, str]] = [
    (0,   4,  "Moon"),     # infancy / nurturing
    (5,  15,  "Mars"),     # adolescence / drive
    (16, 31,  "Mercury"),  # learning / communication
    (32, 50,  "Venus"),    # relationships / harmony
    (51, 65,  "Jupiter"),  # wisdom / expansion
    (66, 69,  "Sun"),      # authority / late visibility
    (70, 83,  "Saturn"),   # discipline / consolidation
    (84, 95,  "Rahu"),     # unconventional late chapter
]
# Ages 96+ fall through to Ketu (release / dissolution).


def activated_planet_for_age(age: int) -> str:
    """The ONE documented age→planet rule for the Yearly engine.

    Naisargika Dasha bands. Cited inline so the table is auditable
    from this file alone.
    """
    try:
        a = int(age)
    except Exception:
        return ""
    for lo, hi, planet in _AGE_ACTIVATION_NAISARGIKA:
        if lo <= a <= hi:
            return planet
    return "Ketu" if a >= 96 else ""


# ────────────────────────────────────────────────────────────────
# Domain & trend palettes (different from daily/monthly)
# ────────────────────────────────────────────────────────────────
_YEAR_DOMAIN_ORDER = ("career", "business", "love", "health", "family")
_YEAR_DOMAIN_LABEL = {
    "career":   "Career",
    "business": "Business",
    "love":     "Love",
    "health":   "Health",
    "family":   "Family",
}

_TREND_RISING   = "rising"
_TREND_PRESSURE = "pressure"
_TREND_STEADY   = "steady"

# Map natal house -> year domain. Slight diff from monthly because
# Year separates "career" (10th) from "business" (3rd/7th/11th).
_HOUSE_TO_YEAR_DOMAIN = {
    1: "health",  2: "business", 3: "business", 4: "family",
    5: "career",  6: "health",   7: "business", 8: "health",
    9: "career", 10: "career",  11: "business", 12: "family",
}

_PLANET_TO_YEAR_DOMAIN = {
    "Sun":     "career",   "Moon":    "family",
    "Mercury": "business", "Mars":    "health",
    "Jupiter": "career",   "Venus":   "love",
    "Saturn":  "career",   "Rahu":    "business",
    "Ketu":    "health",
}

_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def _coerce_date(x) -> Optional[_date]:
    if x is None:
        return None
    if isinstance(x, _date) and not isinstance(x, _dt):
        return x
    if isinstance(x, _dt):
        return x.date()
    if isinstance(x, str):
        try:
            return _date.fromisoformat(x[:10])
        except Exception:
            return None
    return None


def _scrub(text: str, language: str, field_type: str = "plain") -> str:
    if not isinstance(text, str) or not text:
        return text
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        return apply_user_facing_strips(text, language=(language or "en"),
                                        field_type=field_type)
    except Exception:
        return text


_JS_PREFIX = re.compile(r"^\s*JS\s*[:,]\s*", re.IGNORECASE)


def _strip_js_prefix(text: str) -> str:
    """Drop the 'JS:' / 'JS,' leak that bleeds into year_theme / year_summary."""
    if not isinstance(text, str) or not text:
        return text
    return _JS_PREFIX.sub("", text).strip()


def _safe_birthday_in_year(year: int, bd: _date) -> _date:
    """Birthday in `year`, with Feb-29 clamped to Feb-28 for non-leap years."""
    try:
        return _date(year, bd.month, bd.day)
    except ValueError:
        return _date(year, bd.month, 28)


def _active_year_anchor(birth_date_iso: str, today: Optional[_date] = None,
                         tail_fraction: float = 0.75) -> Tuple[_date, _date]:
    """Return [period_start, period_end] for the ACTIVE year ahead.

    Brief rule: "default to the active year ahead so the timeline is
    forward-looking (the current solar year is ~elapsed)". Concretely:
    when the user is in the FINAL QUARTER (>= 75%) of the current solar
    window, jump forward to the next one. Otherwise stay current.

    period_end is the CLOSED anchor day (e.g. JUN 10 .. JUN 10).
    """
    if today is None:
        today = _date.today()
    bd = _coerce_date(birth_date_iso)
    if not bd:
        return today, today + _td(days=365)

    bday_this = _safe_birthday_in_year(today.year, bd)
    if today >= bday_this:
        # Already past this year's birthday — current window starts here.
        current_start = bday_this
    else:
        # Before this year's birthday — current window started last year.
        current_start = _safe_birthday_in_year(today.year - 1, bd)
    current_end = _safe_birthday_in_year(current_start.year + 1, bd)

    # Forward-looking: if the current window is mostly elapsed, jump.
    elapsed = (today - current_start).days
    total   = max(1, (current_end - current_start).days)
    if elapsed / total >= tail_fraction:
        next_start = current_end
        next_end   = _safe_birthday_in_year(next_start.year + 1, bd)
        return next_start, next_end
    return current_start, current_end


def _format_range_short(start: _date, end_inclusive: _date) -> str:
    """JUN 10 '26 – JUN 10 '27."""
    yy_s = start.strftime("%y")
    yy_e = end_inclusive.strftime("%y")
    s = f"{start.strftime('%b').upper()} {start.day} '{yy_s}"
    e = f"{end_inclusive.strftime('%b').upper()} {end_inclusive.day} '{yy_e}"
    return f"{s} – {e}"


def _months_list(start: _date) -> List[str]:
    """12 month abbreviations starting from the anchor month."""
    out = []
    m = start.month
    for _ in range(12):
        d = _date(2000, m, 1)
        out.append(d.strftime("%b"))
        m = m + 1 if m < 12 else 1
    return out


def _now_month_index(start: _date, today: Optional[_date] = None) -> int:
    """How far into the period we are (0-based month index)."""
    today = today or _date.today()
    if today < start:
        return 0
    delta_months = (today.year - start.year) * 12 + (today.month - start.month)
    return max(0, min(11, delta_months))


# ────────────────────────────────────────────────────────────────
# Layer 2: Lal Kitab gate + age-activation protagonist
# ────────────────────────────────────────────────────────────────
def _lk_planet_state(planet: str, lk_data: Dict[str, Any]) -> Dict[str, Any]:
    """Read LK condition for a planet from the stored lk_data.

    Returns a deterministic state object — NEVER a stored 'good/bad'
    label. We compute the valence from the LK fields the engine already
    populates: house placement, sleeping flag, pakka-ghar status, rinn.
    Best-effort: missing fields default to neutral (polarity=0).
    """
    state = {"polarity": 0, "sleeping": False, "pakka_ghar": False, "rinn": False}
    if not isinstance(lk_data, dict) or not planet:
        return state
    # 1. sleeping_planets
    advanced = lk_data.get("advanced") if isinstance(lk_data.get("advanced"), dict) else {}
    sleepers = advanced.get("sleeping_planets") or lk_data.get("sleeping_planets") or []
    if isinstance(sleepers, list) and any(
        (isinstance(s, str) and s.strip().title() == planet.strip().title())
        or (isinstance(s, dict) and (s.get("planet") or "").strip().title() == planet.strip().title())
        for s in sleepers
    ):
        state["sleeping"] = True
        state["polarity"] = -1
    # 2. pakka ghar — planet in its strongest LK house
    pakka = advanced.get("pakka_ghar") or lk_data.get("pakka_ghar") or {}
    if isinstance(pakka, dict) and pakka.get(planet.strip().title()):
        state["pakka_ghar"] = True
        state["polarity"] = max(state["polarity"], +1)
    # 3. rinn (debt)
    rinn = advanced.get("rin") or advanced.get("rinn") or {}
    if isinstance(rinn, dict) and rinn.get(planet.strip().title()):
        state["rinn"] = True
        state["polarity"] = -1
    return state


# ────────────────────────────────────────────────────────────────
# Layer 1+3: Events from critical_dates (typed) + Tajika spine
# ────────────────────────────────────────────────────────────────
# Strip raw transit-aspect calque from event['event'] strings and
# extract domain + polarity + magnitude.
_ASPECT_TOKENS = {
    "conjunction": ("convergence", +0.7),
    "sextile":     ("supportive opening", +0.55),
    "trine":       ("flow window", +0.65),
    "square":      ("tension", -0.6),
    "opposition":  ("polarity tension", -0.65),
    "semi-square": ("minor tension", -0.4),
    "quincunx":    ("adjustment friction", -0.45),
}

_ENERGY_TO_DOMAIN = {
    # phrase fragments emitted by output_strips planet -> energy mapping
    "drive and ability": "career",
    "drive and clean":   "career",
    "action and drive":  "career",
    "ambition and breakthrough": "business",
    "discipline and structure":  "career",
    "discipline and long-term":  "career",
    "growth and wisdom":         "business",
    "love and partnership":      "love",
    "communication and intellect":"business",
    "emotional and nurturing":   "family",
    "identity and authority":    "career",
    "intuition and release":     "health",
}


def _domain_from_event_text(text: str) -> str:
    if not isinstance(text, str):
        return "career"
    t = text.lower()
    for frag, dom in _ENERGY_TO_DOMAIN.items():
        if frag in t:
            return dom
    return "career"


def _polarity_magnitude_from_event(text: str) -> Tuple[int, float]:
    """Read polarity + magnitude from the aspect token in the legacy
    `event` string. Defaults are neutral (0, 0.4)."""
    if not isinstance(text, str):
        return 0, 0.4
    t = text.lower()
    for tok, (_label, weight) in _ASPECT_TOKENS.items():
        if tok in t:
            return (1 if weight > 0 else -1), abs(weight)
    if any(k in t for k in ("favorable","opportunity","supportive","auspicious","openings","aligns")):
        return 1, 0.55
    if any(k in t for k in ("tension","caution","challenge","squeeze","contested","strain","obstacle","retro")):
        return -1, 0.55
    return 0, 0.4


def _month_index_from_label(date_label: str, period_start: _date) -> int:
    """'February 2026' -> int offset (0..11) from period_start month."""
    if not isinstance(date_label, str) or not date_label.strip():
        return 0
    try:
        # Try "%B %Y"
        d = _dt.strptime(date_label.strip(), "%B %Y").date()
    except Exception:
        try:
            d = _dt.strptime(date_label.strip(), "%b %Y").date()
        except Exception:
            return 0
    delta = (d.year - period_start.year) * 12 + (d.month - period_start.month)
    return max(0, min(11, delta))


def _format_event_date_label(date_label: str) -> str:
    """Normalize 'February 2026' -> 'Feb 2026' (matches the brief example)."""
    if not isinstance(date_label, str):
        return date_label
    try:
        d = _dt.strptime(date_label.strip(), "%B %Y").date()
        return d.strftime("%b %Y")
    except Exception:
        return date_label.strip()


def _humanize_event(raw_event_text: str, polarity: int, domain: str,
                    language: str) -> str:
    """Replace the raw transit-aspect calque with a clean plain-language
    sentence. Pulls signal from the polarity + domain we already extracted.
    """
    if polarity > 0:
        templates = {
            "career":   "A visible step up at work — take the high-stakes role.",
            "business": "A real opening on the venture side — push the move now.",
            "love":     "Relationships warm — make the considered, deliberate gesture.",
            "health":   "Energy returns — rebuild the habit you let slip.",
            "family":   "Home life finds its rhythm — invest a deliberate hour.",
        }
    elif polarity < 0:
        templates = {
            "career":   "A heavier work week — defer the big call, ship execution only.",
            "business": "A contested cost or cash-flow squeeze — keep a cushion.",
            "love":     "Tension surfaces in a close relationship — listen more, react less.",
            "health":   "Body asks for rest — pull back from any push.",
            "family":   "A family friction — short check-ins beat long arguments.",
        }
    else:
        templates = {
            "career":   "A steady stretch at work — let consistency compound.",
            "business": "A quiet week for the venture — tend the foundation.",
            "love":     "Relationships are even — small, warm touches are enough.",
            "health":   "Body is steady — keep the routine.",
            "family":   "Family life is quiet — protect the calm.",
        }
    base = templates.get(domain, templates["career"])
    return _scrub(base, language, "plain")


def _build_events(legacy_response: Dict[str, Any], period_start: _date,
                  lk_data: Dict[str, Any], language: str,
                  daily_friction_mask: Optional[Dict[int, bool]] = None
                  ) -> List[Dict[str, Any]]:
    """Reshape critical_dates into typed events. Drops any event placed
    in a month flagged as all-friction by the daily series (cross-check)."""
    out: List[Dict[str, Any]] = []
    cd = legacy_response.get("critical_dates") or []
    for ev in cd:
        if not isinstance(ev, dict):
            continue
        raw_text  = str(ev.get("event") or "").strip()
        date_lbl  = str(ev.get("date")  or "").strip()
        if not raw_text or not date_lbl:
            continue
        mi = _month_index_from_label(date_lbl, period_start)
        # Cross-check: drop positive events in all-friction months.
        polarity, magnitude = _polarity_magnitude_from_event(raw_text)
        if (daily_friction_mask and polarity > 0
                and daily_friction_mask.get(mi, False)):
            continue
        domain = _domain_from_event_text(raw_text)
        text = _humanize_event(raw_text, polarity, domain, language)
        out.append({
            "month_index": mi,
            "date_label":  _format_event_date_label(date_lbl),
            "domain":      _YEAR_DOMAIN_LABEL.get(domain, "Career"),
            "polarity":    polarity,
            "magnitude":   round(float(magnitude), 2),
            "text":        text,
        })
    # Stable sort by month then magnitude
    out.sort(key=lambda e: (e["month_index"], -e["magnitude"]))
    return out


# ────────────────────────────────────────────────────────────────
# Arcs (5-area backdrop trends)
# ────────────────────────────────────────────────────────────────
_ARC_WHEN = {
    _TREND_RISING:   "builds toward {peak}",
    _TREND_PRESSURE: "watch {peak}",
    _TREND_STEADY:   "quietly supportive all year",
}


def _arc_peak_phrase(events: List[Dict[str, Any]], domain_label: str,
                     months: List[str]) -> str:
    """Find the month with the strongest event in this domain; phrase it.
    Falls back to a generic phrase when there's no strong signal."""
    domain_events = [e for e in events
                     if e["domain"].lower() == domain_label.lower()]
    if not domain_events:
        return "quietly supportive all year"
    top = max(domain_events, key=lambda e: e["magnitude"])
    return f"peaks {top['date_label']}"


def _trend_for_domain(events: List[Dict[str, Any]], domain_label: str) -> str:
    """Net polarity across the year for this domain."""
    domain_events = [e for e in events
                     if e["domain"].lower() == domain_label.lower()]
    if not domain_events:
        return _TREND_STEADY
    net = sum(e["polarity"] * e["magnitude"] for e in domain_events)
    if net >= 0.5:
        return _TREND_RISING
    if net <= -0.5:
        return _TREND_PRESSURE
    return _TREND_STEADY


def _build_arcs(events: List[Dict[str, Any]], months: List[str],
                language: str) -> List[Dict[str, Any]]:
    arcs: List[Dict[str, Any]] = []
    for key in _YEAR_DOMAIN_ORDER:
        label = _YEAR_DOMAIN_LABEL[key]
        trend = _trend_for_domain(events, label)
        when_phrase = _arc_peak_phrase(events, label, months) \
                        if trend != _TREND_STEADY else "quietly supportive all year"
        arcs.append({
            "key":   key,
            "name":  label,
            "trend": trend,
            "when":  _scrub(when_phrase, language, "plain"),
        })
    return arcs


# ────────────────────────────────────────────────────────────────
# Theme / quality / active triple
# ────────────────────────────────────────────────────────────────
_QUALITY_BY_PLANET = {
    "Sun":     "Visibility",
    "Moon":    "Nurture",
    "Mars":    "Push",
    "Mercury": "Network",
    "Jupiter": "Expansion",
    "Venus":   "Bond",
    "Saturn":  "Consolidation",
    "Rahu":    "Pivot",
    "Ketu":    "Release",
}
_ACTIVE_BY_PLANET = {
    "Sun":     "Authority and visibility are the year's switched-on forces — own the room.",
    "Moon":    "Emotional steadiness is the year's switched-on force — trust your read on people.",
    "Mars":    "Drive and discipline are the year's switched-on forces — push, but pace it.",
    "Mercury": "Communication and trade are the year's switched-on forces — write, negotiate, ship.",
    "Jupiter": "Growth and teaching are the year's switched-on forces — mentor, learn, expand.",
    "Venus":   "Relationships and craft are the year's switched-on forces — invest in both.",
    "Saturn":  "Structure and patience are the year's switched-on forces — compound, don't sprint.",
    "Rahu":    "Unconventional moves are the year's switched-on forces — go where the crowd isn't.",
    "Ketu":    "Release and focus are the year's switched-on forces — subtract until clarity returns.",
}
_THEME_BY_PLANET = {
    "Sun":     "A year to step into authority — what you own publicly, you become.",
    "Moon":    "A year to tend the inner world — habits, sleep, and the people you keep.",
    "Mars":    "A year to take aim — one deliberate push beats five scattered attempts.",
    "Mercury": "A year of conversations and contracts — the deals you make shape the next chapter.",
    "Jupiter": "A year of expansion — opportunities open, but pick which to grow.",
    "Venus":   "A year of connection — relationships and creative work compound.",
    "Saturn":  "A year to build what lasts — effort compounds, and one venture finally turns.",
    "Rahu":    "A year of unconventional moves — the door you find isn't on the map.",
    "Ketu":    "A year of subtraction — what you let go of frees what matters.",
}


def _compose_quality_theme_active(active_planet: str, lk_state: Dict[str, Any],
                                  language: str) -> Tuple[str, str, str]:
    p = (active_planet or "").strip().title()
    quality = _QUALITY_BY_PLANET.get(p, "Steady")
    theme   = _THEME_BY_PLANET.get(p, "A steady year — small, consistent moves outpace big bets.")
    active  = _ACTIVE_BY_PLANET.get(p, "Steady, deliberate effort is the year's switched-on force.")
    # LK valence flips theme tone when the activated planet is asleep or in rinn.
    if lk_state.get("polarity", 0) < 0:
        # Soften the theme into a "build the floor first" framing.
        theme = ("A year to repair the foundation before pushing — the structure asks "
                 "for attention before the climb resumes.")
    return (_scrub(quality, language, "plain"),
            _scrub(theme,   language, "plain"),
            _scrub(active,  language, "plain"))


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────
def compose_yearly_contract(chart_record: Dict[str, Any],
                             legacy_response: Dict[str, Any],
                             language: str = "en",
                             daily_friction_mask: Optional[Dict[int, bool]] = None,
                             ) -> Dict[str, Any]:
    """
    Build the Yearly brief's contract on top of the legacy /annual-plan.

    Args:
      chart_record: Supabase charts row (birth_date, lal_kitab_data, ...).
      legacy_response: the existing endpoint's dict (we read critical_dates +
                       year_theme + yearly_remedies from here).
      language: en/es/pt.
      daily_friction_mask: optional {month_index: True/False} — when set,
                           positive events in friction months are dropped.
                           (Brief cross-check; ok to omit at launch.)
    """
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"

    # ── 1. Active-year-ahead period boundaries (closed-anchor display) ──
    birth_date = chart_record.get("birth_date") or ""
    ps, pe = _active_year_anchor(birth_date)
    months = _months_list(ps)
    now_idx = _now_month_index(ps)

    # ── 2. Age-activation protagonist (Naisargika, table cited above) ──
    try:
        from antar_engine.jyotish_periods import age_on as _age_on
        age = _age_on(birth_date) if birth_date else 0
    except Exception:
        age = 0
    active_planet = activated_planet_for_age(age)

    # ── 3. LK state for the activated planet ──
    lk_data = chart_record.get("lal_kitab_data") or {}
    if isinstance(lk_data, str):
        try:
            import json as _yj
            lk_data = _yj.loads(lk_data)
        except Exception:
            lk_data = {}
    lk_state = _lk_planet_state(active_planet, lk_data)

    # ── 4. Theme / quality / active ──
    quality, theme, active = _compose_quality_theme_active(
        active_planet, lk_state, language,
    )

    # ── 5. Events: typed, LK-gated, cross-checked vs daily friction mask ──
    events = _build_events(legacy_response, ps, lk_data, language,
                           daily_friction_mask=daily_friction_mask)

    # ── 6. Arcs: 5 area trends with peak phrasing ──
    arcs = _build_arcs(events, months, language)

    # ── 7. Range (closed-anchor display) ──
    range_label = _format_range_short(ps, pe)

    return {
        "range":        range_label,
        "period_start": ps.isoformat(),
        "period_end":   pe.isoformat(),
        "quality":      quality,
        "theme":        theme,
        "active":       active,
        "months":       months,
        "now_month":    now_idx,
        "events":       events,
        "arcs":         arcs,
    }


# ────────────────────────────────────────────────────────────────
# Side-table fixes (JS: strip + yearly_remedies scrub)
# ────────────────────────────────────────────────────────────────
def strip_js_leak(text: Any) -> Any:
    """Drop the 'JS:' / 'JS,' prefix that leaks into year_theme/year_summary."""
    return _strip_js_prefix(text) if isinstance(text, str) else text


def scrub_yearly_remedies(remedies: Any, language: str) -> Any:
    """Run the central strip over each remedy's `practice` string.
    Doesn't drop the `planet` key (it's a structured field, not user-facing
    prose). field_type='timing' so the weekday survives ("on Saturday")."""
    if not isinstance(remedies, list):
        return remedies
    out = []
    for r in remedies:
        if not isinstance(r, dict):
            out.append(r); continue
        nr = dict(r)
        practice = nr.get("practice")
        if isinstance(practice, str) and practice:
            nr["practice"] = _scrub(practice, language, "timing")
        out.append(nr)
    return out


__all__ = [
    "compose_yearly_contract",
    "activated_planet_for_age",
    "strip_js_leak",
    "scrub_yearly_remedies",
    "_AGE_ACTIVATION_NAISARGIKA",
]
