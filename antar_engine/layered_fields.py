"""
antar_engine/layered_fields.py
──────────────────────────────
Shared helpers for the layered-fidelity prediction surface (hook → substance →
depth), emitted PER DOMAIN by This Month / This Year / Current Cycle.

DOCTRINE (why this module exists)
  Python computes WHAT is true (the domain, the event-noun, the window, the
  conviction). The LLM only PHRASES it. This module is the single place that:
    1. normalises every engine's domain vocabulary down to the canonical FIVE,
    2. maps every engine's confidence signal to one 0–3 conviction scalar,
    3. assembles the {domain,status_label,status_color,conviction,hook,
       substance,depth} field,
    4. VALIDATES the result against altitude + conviction + no-hallucination
       rules and against the user-facing strips.

  It is ADDITIVE and QUARANTINED: import it, call it, but nothing here is wired
  into a live endpoint until the surface patches land. Gate every live call on
  ``is_enabled()`` (env LAYERED_FIELDS, default "shadow").

  NO swisseph, NO network, NO Supabase — pure functions, sandbox-testable.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Kill switch
# ─────────────────────────────────────────────────────────────────────────────
def is_enabled() -> bool:
    """shadow|on|primary => compute & attach.  off => skip entirely.

    Default 'shadow' = build the block but the surface patch must attach it
    behind a flag so it can never overwrite a shipped field.
    """
    return (os.environ.get("LAYERED_FIELDS", "shadow") or "shadow").lower() in (
        "shadow",
        "on",
        "primary",
    )


def mode() -> str:
    return (os.environ.get("LAYERED_FIELDS", "shadow") or "shadow").lower()


# ─────────────────────────────────────────────────────────────────────────────
# The canonical five domains (consistent across Month AND Year)
# ─────────────────────────────────────────────────────────────────────────────
CANONICAL_DOMAINS: Tuple[str, ...] = (
    "career",
    "money",
    "relationships",
    "health",
    "family",
)

# Every domain string any engine can emit → one of the five.
# Founder-locked 2026-06-24:
#   career ← career + learning   (skill-building is vocational)
#   money  ← wealth              relationships ← relationships
#   health ← health              family ← home
#   spiritual → ROUTE TO PRACTICE — excluded from domain rows entirely
#     (spiritual == energy-voice; doctrine = energy-voice lives in Practice
#      ONLY, never on a prediction surface). Use route_domain() → None.
# Edge: foreign/relocation has no canonical home; routed to career (a move in
# this engine is most often career-driven). One-line flip if that's wrong.
_DOMAIN_NORMALIZE: Dict[str, str] = {
    # career bucket
    "career": "career",
    "work": "career",
    "job": "career",
    "learning": "career",        # founder-locked: skill-building is vocational
    "education": "career",
    "communication": "career",
    "ambition": "career",
    "identity": "career",
    "action": "career",
    "discipline": "career",
    "foreign": "career",         # edge — reviewable
    "relocation": "career",      # edge — reviewable
    # money bucket
    "money": "money",
    "wealth": "money",
    "finance": "money",
    "financial": "money",
    "speculation": "money",
    "loss": "money",
    "gains": "money",
    # relationships bucket
    "relationships": "relationships",
    "relationship": "relationships",
    "marriage": "relationships",
    "love": "relationships",
    "people": "relationships",
    "reconciliation": "relationships",
    "divorce": "relationships",
    "partnership": "relationships",
    # health bucket  (body / vitality / wellbeing — NOT spiritual)
    "health": "health",
    "wellbeing": "health",
    "wellness": "health",
    "vitality": "health",
    # family bucket
    "family": "family",
    "home": "family",            # founder-locked
    "children": "family",
    "property": "family",
    "roots": "family",
}

# Domains that must NOT appear as prediction rows — redirected to Practice.
# These are energy-voice / inner-work themes (Ketu, dharma, moksha).
_PRACTICE_ONLY = {
    "spiritual",
    "spirituality",
    "dharma",
    "moksha",
    "inner life",
    "letting go",
}

# When an unknown domain shows up, fall back here rather than dropping the row.
_UNMAPPED_FALLBACK = "career"


def route_domain(raw: Optional[str]) -> Optional[str]:
    """Primary API. Returns a canonical domain, or None when the input must be
    routed to Practice (excluded from prediction rows per doctrine).
    """
    key = (str(raw).strip().lower() if raw else "")
    if key in _PRACTICE_ONLY or key.rstrip("s") in _PRACTICE_ONLY:
        return None
    if not key:
        return _UNMAPPED_FALLBACK
    if key in _DOMAIN_NORMALIZE:
        return _DOMAIN_NORMALIZE[key]
    key2 = key.rstrip("s")
    return _DOMAIN_NORMALIZE.get(key2, _UNMAPPED_FALLBACK)


def normalize_domain(raw: Optional[str]) -> str:
    """Like route_domain but never returns None — practice-only inputs collapse
    to the fallback. Prefer route_domain() so spiritual rows can be dropped.
    """
    dom = route_domain(raw)
    return dom if dom is not None else _UNMAPPED_FALLBACK


def is_practice_only(raw: Optional[str]) -> bool:
    return route_domain(raw) is None


def route_domain_strict(raw: Optional[str]) -> Optional[str]:
    """Like route_domain but returns None for ANYTHING not explicitly mapped —
    no career fallback. Use for noisy upstream vocabularies (lk_month, transit
    hot-domains) whose labels (emotion, trade, comfort, luxury…) must NOT be
    silently bucketed into career. Practice-only inputs also return None.
    """
    key = (str(raw).strip().lower() if raw else "")
    if not key or key in _PRACTICE_ONLY or key.rstrip("s") in _PRACTICE_ONLY:
        return None
    if key in _DOMAIN_NORMALIZE:
        return _DOMAIN_NORMALIZE[key]
    return _DOMAIN_NORMALIZE.get(key.rstrip("s"))  # None if unmapped


# ─────────────────────────────────────────────────────────────────────────────
# Conviction: ONE 0–3 scalar from whatever signal a surface has
# ─────────────────────────────────────────────────────────────────────────────
# 3 = HIGH   : hook MAY name a concrete event + window
# 2 = MEDIUM : name the domain, SOFTEN the claim (may / tends to), no hard event
# 1 = LOW    : directional read only, no specific event
# 0 = NONE   : steady / no signal — flat directional line
CONV_HIGH, CONV_MED, CONV_LOW, CONV_NONE = 3, 2, 1, 0


def conviction_from_score(score: Optional[float], *, scale_max: float = 10.0) -> int:
    """Shared path (founder-locked): derive 0–3 from ONE timing-strength score so
    the same domain shows the same dot-count on Month, Year and Cycle.

    Calibrated to the precision_windows scale (0–10, surface threshold 6.0):
      >= 0.80*max -> 3,  >= 0.60*max -> 2,  >= 0.35*max -> 1,  else 0.
    """
    if score is None:
        return CONV_NONE
    try:
        s = float(score)
    except (TypeError, ValueError):
        return CONV_NONE
    if scale_max <= 0:
        return CONV_NONE
    frac = max(0.0, min(1.0, s / scale_max))
    if frac >= 0.80:
        return CONV_HIGH
    if frac >= 0.60:
        return CONV_MED
    if frac >= 0.35:
        return CONV_LOW
    return CONV_NONE


def conviction_from_layers(layers_agreeing: Optional[int], *, directional: bool = False) -> int:
    """Convergence path (life-arc forward_events): layers 1–3 → 0–3.

    Mirrors the existing dated-card gate: 3 agreeing layers is the only
    'name a dated event' tier; a 2-layer 'directional' event is soft (LOW).
    """
    try:
        n = int(layers_agreeing or 0)
    except (TypeError, ValueError):
        n = 0
    if n >= 3 and not directional:
        return CONV_HIGH
    if n >= 2:
        return CONV_LOW if directional else CONV_MED
    if n >= 1:
        return CONV_LOW
    return CONV_NONE


_CONV_STR = {"high": CONV_HIGH, "medium": CONV_MED, "low": CONV_LOW, "subtle": CONV_NONE}


def conviction_from_string(s: Optional[str]) -> int:
    return _CONV_STR.get((s or "").strip().lower(), CONV_NONE)


def bars_to_conviction(bars: Optional[int]) -> int:
    """Year strength bars (0–3) used ONLY as a conviction fallback."""
    try:
        return max(CONV_NONE, min(CONV_HIGH, int(bars)))
    except (TypeError, ValueError):
        return CONV_NONE


def conviction_for_domain(
    *,
    precision_score: Optional[float] = None,
    score_scale_max: float = 10.0,
    layers_agreeing: Optional[int] = None,
    directional: bool = False,
    conviction_str: Optional[str] = None,
    bars: Optional[int] = None,
) -> int:
    """THE single 0–3 conviction for a domain, normalised so the dots mean the
    same thing on Month, Year AND Cycle (founder Decision 1).

    Priority (spine → fallback):
      1. precision-window score  (the shared timing-strength spine)
      2. convergence layers_agreeing (+directional gate)
      3. an engine conviction string ("high/medium/low/subtle")
      4. Year strength bars  (fallback only)
      5. 0
    The first signal that is actually present wins; bars never override a real
    precision score.
    """
    if precision_score is not None:
        return conviction_from_score(precision_score, scale_max=score_scale_max)
    if layers_agreeing is not None:
        return conviction_from_layers(layers_agreeing, directional=directional)
    if conviction_str:
        return conviction_from_string(conviction_str)
    if bars is not None:
        return bars_to_conviction(bars)
    return CONV_NONE


def cap_conviction(conviction: int, altitude: str) -> int:
    """Cycle altitude is multi-year + already medium-capped upstream; never let a
    cycle domain carry a 3-dot 'will happen' claim. Month/Year may reach 3.
    """
    c = max(CONV_NONE, min(CONV_HIGH, int(conviction)))
    if altitude == ALT_CYCLE:
        return min(c, CONV_MED)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Status chip (≤2 words) + semantic colour
# ─────────────────────────────────────────────────────────────────────────────
STATUS_COLORS: Tuple[str, ...] = ("positive", "steady", "caution", "pressure")

# polarity (engine) → (status_color, {conviction_bucket: label})
_STATUS_BY_POLARITY: Dict[str, Tuple[str, Dict[str, str]]] = {
    "positive": ("positive", {"bold": "Move now", "soft": "Lean in"}),
    "mixed":    ("steady",   {"bold": "Mixed",    "soft": "Mixed"}),
    "steady":   ("steady",   {"bold": "Hold steady", "soft": "Hold steady"}),
    "caution":  ("caution",  {"bold": "Go slow",  "soft": "Go slow"}),
    "negative": ("pressure", {"bold": "Under pressure", "soft": "Ease off"}),
    "pressure": ("pressure", {"bold": "Under pressure", "soft": "Ease off"}),
}


def status_for(polarity: Optional[str], conviction: int) -> Tuple[str, str]:
    """Return (status_label, status_color). Label ≤2 words."""
    pol = (polarity or "steady").strip().lower()
    color, labels = _STATUS_BY_POLARITY.get(pol, _STATUS_BY_POLARITY["steady"])
    bucket = "bold" if conviction >= CONV_MED else "soft"
    return labels[bucket], color


# ─────────────────────────────────────────────────────────────────────────────
# Altitude
# ─────────────────────────────────────────────────────────────────────────────
ALT_MONTH = "month"   # dated move: concrete noun + specific week window
ALT_YEAR = "year"     # arc of the domain across the year, NO week-level dates
ALT_CYCLE = "cycle"   # chapter-phase character, multi-year, directional only

# A week-level date token = a day-of-month number, an explicit date range, or a
# "this week / next week" phrase. Months/seasons/quarters are arc-level and OK.
_WEEK_DATE_RE = re.compile(
    r"\b("
    r"\d{1,2}\s*[–\-]\s*\d{1,2}"            # 25–31 / 25-31  (day range)
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}"  # Jun 25
    r"|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"        # 25 Jun
    r"|this\s+week|next\s+week|the\s+\d{1,2}(?:st|nd|rd|th)"
    r"|\bweek\s+of\b"
    r")\b",
    re.IGNORECASE,
)


def has_week_date(text: Optional[str]) -> bool:
    return bool(text) and bool(_WEEK_DATE_RE.search(text))


# ─────────────────────────────────────────────────────────────────────────────
# Validators (run AFTER the LLM phrases the computed input)
# ─────────────────────────────────────────────────────────────────────────────
# Hard-claim tokens forbidden below conviction 3.
_BOLD_CLAIM_RE = re.compile(
    r"\b(will\s+\w+|guaranteed|definitely|certainly|lands\s+this\s+week|"
    r"happens\s+this\s+week|is\s+going\s+to)\b",
    re.IGNORECASE,
)


def validate_altitude(field: Dict[str, Any], altitude: str) -> Tuple[bool, str]:
    """Year hook must carry NO week-level date; Month hook MUST carry one."""
    hook = field.get("hook") or ""
    if altitude == ALT_YEAR and has_week_date(hook):
        return False, "year hook contains a week-level date (must be arc-level)"
    if altitude == ALT_MONTH:
        # Only HIGH-conviction month hooks are required to name a window; a
        # soft/low month hook legitimately has no date.
        if field.get("conviction", 0) >= CONV_HIGH and not has_week_date(hook):
            return False, "high-conviction month hook is missing its week window"
    if altitude == ALT_CYCLE and has_week_date(hook):
        return False, "cycle hook contains a week-level date (must be directional)"
    return True, ""


def validate_conviction_boldness(field: Dict[str, Any]) -> Tuple[bool, str]:
    """A 2-dot domain may not carry a 3-dot ('will happen') claim."""
    conviction = int(field.get("conviction", 0))
    if conviction >= CONV_HIGH:
        return True, ""
    for key in ("hook", "substance", "depth"):
        if _BOLD_CLAIM_RE.search(field.get(key) or ""):
            return False, f"{key} carries a hard claim above conviction={conviction}"
    return True, ""


_MONTHWORD_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.IGNORECASE)


def _norm_dates(text: str) -> str:
    """Lowercase + truncate every month word to 3 letters so 'June 25' and
    'Jun 25' compare equal, and collapse whitespace. Lets the validator accept a
    sourced date regardless of how the model spelled the month."""
    t = _MONTHWORD_RE.sub(lambda m: m.group(1).lower(), (text or "").lower())
    return re.sub(r"\s+", " ", t)


def validate_no_unsourced_tokens(
    field: Dict[str, Any],
    *,
    sourced_nouns: Optional[List[str]] = None,
    sourced_windows: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """Reject output containing a DATE token not present in the computed input.

    We only police dates here (the highest hallucination risk). Any date-shaped
    token in the copy must trace to a window string the engine actually supplied
    (priority_actions dates, best_week / caution_week, score_day_*). Month spelling
    is normalised on both sides so 'June 22' matches a sourced 'Jun 22'. Nouns are
    advisory (the LLM may rephrase them) so they are not hard-gated.
    """
    sourced_blob = _norm_dates(" ".join(sourced_windows or []))
    for key in ("hook", "substance", "depth"):
        text = field.get(key) or ""
        for m in _WEEK_DATE_RE.finditer(text):
            tok = _norm_dates(m.group(0).strip())
            if tok not in sourced_blob:
                return False, f"{key} introduces unsourced date token {tok!r}"
    return True, ""


_BIJA_RE = re.compile(r"\b(?:om|aum)\b[\w\s]*\b(?:namah|namaha|namo)\b", re.IGNORECASE)


def scrub_remedies(remedies: Any, language: str = "en") -> Any:
    """ISSUE 4 — bija mantras (Om Suryaya Namaha) and planet names must NOT appear
    on a prediction surface (Practice owns remedies). Drops bija-mantra entries
    entirely and strips planet names / jargon from any survivors; removes the raw
    ``planet`` key. Returns a list of {practice} (or the input unchanged if not a
    list).
    """
    if not isinstance(remedies, list):
        return remedies
    try:
        from antar_engine.output_strips import apply_user_facing_strips
    except Exception:
        apply_user_facing_strips = None  # type: ignore
    out: List[Dict[str, Any]] = []
    for r in remedies:
        if not isinstance(r, dict):
            continue
        practice = str(r.get("practice") or r.get("text") or "")
        if not practice or _BIJA_RE.search(practice):
            continue  # bija mantra → Practice-only; drop from this surface
        if apply_user_facing_strips is not None:
            try:
                practice = apply_user_facing_strips(
                    practice, language, field_type="plain", depth="user"
                )
            except Exception:
                pass
        out.append({"practice": practice})
    return out


def scrub_field(field: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
    """Run the single user-facing strips enforcement point on hook/substance/depth.

    Lazy import keeps this module importable in any context. field_type='plain'
    strips energy words, planet names, house numbers, day-of-week and es bleed.
    """
    try:
        from antar_engine.output_strips import apply_user_facing_strips
    except Exception:
        return field  # strips unavailable — leave text untouched, surface logs
    for key in ("hook", "substance", "depth"):
        if field.get(key):
            field[key] = apply_user_facing_strips(
                field[key], language, field_type="plain", depth="user"
            )
    return field


# ─────────────────────────────────────────────────────────────────────────────
# Assembler
# ─────────────────────────────────────────────────────────────────────────────
def assemble_domain_field(
    *,
    domain: str,
    polarity: str,
    conviction: int,
    altitude: str,
    hook: str,
    substance: str,
    depth: str,
    language: str = "en",
    sourced_windows: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Build ONE validated, scrubbed domain field.

    Returns the field dict with an extra ``_valid`` bool and ``_reasons`` list so
    the surface patch can decide (in shadow) whether to attach or fall back. The
    caller supplies copy the LLM already phrased from computed input; this only
    normalises, scores the chip, scrubs and validates — it never invents text.

    Returns None when the domain routes to Practice (spiritual / inner-work) and
    must not appear as a prediction row.
    """
    dom = route_domain(domain)
    if dom is None:
        return None  # routed to Practice — excluded from prediction rows
    conv = cap_conviction(conviction, altitude)
    status_label, status_color = status_for(polarity, conv)

    field: Dict[str, Any] = {
        "domain": dom,
        "status_label": status_label,
        "status_color": status_color,
        "conviction": conv,
        "hook": hook or "",
        "substance": substance or "",
        "depth": depth or "",
    }
    field = scrub_field(field, language)

    reasons: List[str] = []
    for ok, why in (
        validate_altitude(field, altitude),
        validate_conviction_boldness(field),
        validate_no_unsourced_tokens(field, sourced_windows=sourced_windows),
    ):
        if not ok:
            reasons.append(why)

    field["_valid"] = not reasons
    field["_reasons"] = reasons
    return field


# ─────────────────────────────────────────────────────────────────────────────
# Cycle helpers (phase fields + far-future year-level relabel)
# ─────────────────────────────────────────────────────────────────────────────
_MONTH_TOKEN_RE = re.compile(
    r"\b(?:early|mid|late)?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"[a-z]*\b",
    re.IGNORECASE,
)


def months_between(start_iso: str, now_iso: str) -> Optional[int]:
    """Whole months from now to a window start (negative if in the past)."""
    try:
        sy, sm = int(start_iso[:4]), int(start_iso[5:7])
        ny, nm = int(now_iso[:4]), int(now_iso[5:7])
        return (sy - ny) * 12 + (sm - nm)
    except (ValueError, TypeError, IndexError):
        return None


def yearlevel_label(
    window_start_iso: str,
    now_iso: str,
    window_label: str,
    *,
    months_threshold: int = 18,
) -> str:
    """Founder-locked: a legitimate far-future card renders YEAR-level on Cycle —
    'a major step around 2029', never 'late Jul 2029'. Within the near horizon the
    original month-stamped label is kept.
    """
    mo = months_between(window_start_iso, now_iso)
    if mo is None or mo <= months_threshold:
        return window_label
    try:
        yr = int(window_start_iso[:4])
    except (ValueError, TypeError):
        return window_label
    # If the label already names no month, leave it; else year-level it.
    if not _MONTH_TOKEN_RE.search(window_label or ""):
        return window_label
    return f"around {yr}"


def _split_sentences(text: str, n: int = 2) -> str:
    """First n sentences of a body, for the always-visible substance tier."""
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


def build_phase_fields(
    *,
    title: str,
    body: str,
    event_convictions: Optional[List[str]] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """Cycle altitude: derive hook/substance/depth/conviction for a phase node from
    its already-narrated title/body (NO new LLM call). Conviction = the strongest
    attached event, cycle-capped to medium; phases with no event read directional.
    """
    convs = [conviction_from_string(c) for c in (event_convictions or [])]
    base = max(convs) if convs else CONV_LOW
    conv = cap_conviction(base, ALT_CYCLE)

    field: Dict[str, Any] = {
        "hook": title or "",
        "substance": _split_sentences(body, 2),
        "depth": body or "",
        "conviction": conv,
    }
    field = scrub_field(field, language)
    return field


# ─────────────────────────────────────────────────────────────────────────────
# Self-test (sandbox: python antar_engine/layered_fields.py)
# ─────────────────────────────────────────────────────────────────────────────
def _selftest() -> int:
    failures: List[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    # domain normalisation (founder-locked map)
    check("home→family", route_domain("home") == "family")
    check("learning→career", route_domain("learning") == "career")
    check("wealth→money", route_domain("wealth") == "money")
    check("marriage→relationships", route_domain("marriage") == "relationships")
    check("health→health", route_domain("health") == "health")
    check("unknown→fallback", route_domain("zzz") == _UNMAPPED_FALLBACK)
    check("plural Relationships", route_domain("Relationships") == "relationships")
    # spiritual routes to Practice (None), NOT health
    check("spiritual→practice(None)", route_domain("spiritual") is None)
    check("inner life→practice(None)", route_domain("Inner Life") is None)
    check("letting go→practice(None)", route_domain("letting go") is None)
    check("is_practice_only(spiritual)", is_practice_only("spiritual") is True)
    check("is_practice_only(career) False", is_practice_only("career") is False)
    check("normalize never None", normalize_domain("spiritual") == _UNMAPPED_FALLBACK)
    # strict router drops noisy upstream labels instead of bucketing to career
    check("strict: emotion→None", route_domain_strict("emotion") is None)
    check("strict: trade→None", route_domain_strict("trade") is None)
    check("strict: learning→career", route_domain_strict("learning") == "career")
    check("strict: children→family", route_domain_strict("children") == "family")
    check("strict: spiritual→None", route_domain_strict("spiritual") is None)

    # unified conviction_for_domain (spine → fallback priority)
    check("unified: precision spine wins", conviction_for_domain(precision_score=9.0, bars=0) == 3)
    check("unified: layers when no score", conviction_for_domain(layers_agreeing=2) == 2)
    check("unified: directional softens", conviction_for_domain(layers_agreeing=3, directional=True) == 1)
    check("unified: string fallback", conviction_for_domain(conviction_str="high") == 3)
    check("unified: bars last resort", conviction_for_domain(bars=2) == 2)
    check("unified: nothing→0", conviction_for_domain() == 0)
    check("bars never beat score", conviction_for_domain(precision_score=4.0, bars=3) == 1)

    # conviction from shared score
    check("score 9→3", conviction_from_score(9.0) == 3)
    check("score 6.5→2", conviction_from_score(6.5) == 2)
    check("score 4→1", conviction_from_score(4.0) == 1)
    check("score 1→0", conviction_from_score(1.0) == 0)
    check("score None→0", conviction_from_score(None) == 0)

    # conviction from layers + directional gate
    check("3 layers→3", conviction_from_layers(3) == 3)
    check("3 layers directional→1", conviction_from_layers(3, directional=True) == 1)
    check("2 layers→2", conviction_from_layers(2) == 2)
    check("1 layer→1", conviction_from_layers(1) == 1)

    # cycle cap
    check("cycle caps 3→2", cap_conviction(3, ALT_CYCLE) == 2)
    check("month keeps 3", cap_conviction(3, ALT_MONTH) == 3)

    # status chip
    lbl, col = status_for("positive", 3)
    check("positive bold→Move now/positive", lbl == "Move now" and col == "positive")
    lbl, col = status_for("positive", 1)
    check("positive soft→Lean in", lbl == "Lean in")
    lbl, col = status_for("negative", 2)
    check("negative→pressure", col == "pressure")

    # week-date detection
    check("detect 'Jun 25'", has_week_date("position around Jun 25"))
    check("detect '25–31'", has_week_date("window 25–31"))
    check("detect 'this week'", has_week_date("the call lands this week"))
    check("month-only not week", not has_week_date("career concentrates in spring"))
    check("'April' arc-level ok", not has_week_date("a step up around April"))

    # altitude validation
    yr_bad = {"hook": "schedule it Jun 25–Jul 1", "conviction": 3}
    ok, _ = validate_altitude(yr_bad, ALT_YEAR)
    check("year rejects week date", not ok)
    yr_ok = {"hook": "career is where the year concentrates", "conviction": 2}
    ok, _ = validate_altitude(yr_ok, ALT_YEAR)
    check("year accepts arc hook", ok)
    mo_bad = {"hook": "a step up is coming", "conviction": 3}
    ok, _ = validate_altitude(mo_bad, ALT_MONTH)
    check("month-high needs window", not ok)
    mo_soft = {"hook": "work stays steady", "conviction": 1}
    ok, _ = validate_altitude(mo_soft, ALT_MONTH)
    check("month-soft no window ok", ok)

    # conviction boldness gate
    ok, _ = validate_conviction_boldness({"hook": "the deal will close", "conviction": 2})
    check("2-dot rejects 'will'", not ok)
    ok, _ = validate_conviction_boldness({"hook": "the deal may move", "conviction": 2})
    check("2-dot accepts 'may'", ok)
    ok, _ = validate_conviction_boldness({"hook": "the deal will close", "conviction": 3})
    check("3-dot allows 'will'", ok)

    # unsourced date gate
    ok, _ = validate_no_unsourced_tokens(
        {"hook": "act around Jun 25"}, sourced_windows=["Jun 25–Jul 1"]
    )
    check("sourced date passes", ok)
    ok, _ = validate_no_unsourced_tokens(
        {"hook": "act around Aug 12"}, sourced_windows=["Jun 25–Jul 1"]
    )
    check("unsourced date fails", not ok)
    # month-spelling normalisation: 'June 22' copy vs 'Jun 22' source PASSES
    ok, _ = validate_no_unsourced_tokens(
        {"hook": "the week of June 22 is the one to use"},
        sourced_windows=["Week of Jun 22"],
    )
    check("June↔Jun normalised pass", ok)

    # end-to-end assemble
    f = assemble_domain_field(
        domain="wealth",
        polarity="positive",
        conviction=3,
        altitude=ALT_MONTH,
        hook="line up the money move around Jun 25",
        substance="A clear opening to act on the financial step you've been weighing.",
        depth="The supporting window is narrow but real; prepare the paperwork first.",
        sourced_windows=["Jun 25–Jul 1"],
    )
    check("assemble domain→money", f["domain"] == "money")
    check("assemble valid", f["_valid"] is True)
    check("assemble has 6 core keys", all(
        k in f for k in ("domain", "status_label", "status_color", "conviction", "hook", "substance", "depth")
    ))

    # assemble drops a practice-only domain
    f2 = assemble_domain_field(
        domain="spiritual", polarity="steady", conviction=2, altitude=ALT_YEAR,
        hook="inner work deepens this year", substance="x", depth="y",
    )
    check("assemble spiritual→None", f2 is None)

    # cycle: far-future year-level relabel
    check("far-future month→year", yearlevel_label("2029-07-15", "2026-06-24", "late Jul 2029") == "around 2029")
    check("near-future kept", yearlevel_label("2026-09-01", "2026-06-24", "early Sep 2026") == "early Sep 2026")
    check("already-year-level kept", yearlevel_label("2029-07-15", "2026-06-24", "a window forms around 2029") == "a window forms around 2029")

    # cycle: phase fields from title/body
    pf = build_phase_fields(
        title="A steadier stretch opens",
        body="The next sub-chapter settles the ground under you. Decisions get easier. Old friction eases.",
        event_convictions=["high", "low"],
    )
    check("phase hook=title", pf["hook"] == "A steadier stretch opens")
    check("phase conviction capped medium", pf["conviction"] == 2)
    check("phase substance trimmed", pf["substance"].count(".") <= 2 and len(pf["substance"]) < len(pf["depth"]))
    pf2 = build_phase_fields(title="t", body="b", event_convictions=None)
    check("phase no-events→directional(1)", pf2["conviction"] == 1)

    # remedies scrub (ISSUE 4): bija mantras dropped, planet keys gone
    rem = scrub_remedies([
        {"planet": "Sun", "practice": "Om Suryaya Namaha — for vitality. Chant 108 times."},
        {"planet": "Saturn", "practice": "Om Shanaye Namaha — for discipline."},
        {"planet": "Moon", "practice": "Take a slow walk near water in the evening."},
    ])
    check("remedies dropped bija", len(rem) == 1)
    check("remedies no planet key", all("planet" not in r for r in rem))
    check("remedies kept clean practice", "walk near water" in rem[0]["practice"])

    if failures:
        print(f"SELFTEST FAIL ({len(failures)}): " + "; ".join(failures))
        return 1
    print("SELFTEST PASS — all layered_fields checks green")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
