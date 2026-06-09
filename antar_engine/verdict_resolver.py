"""
antar_engine/verdict_resolver.py
─────────────────────────────────
WS0 of the "stable deterministic verdict" sprint.

CORE PRINCIPLE (per founder brief):
  Python computes, Claude narrates, never calculates.
  This holds for the chart math but was breaking at the conclusion.
  This module owns the conclusion. Same chart + concern + date +
  timeframe → identical verdict band and identical verdict_line,
  every call. Claude only rephrases for tone; it may not flip the
  call, change the timeframe, or invert the move.

WHAT THIS MODULE PRODUCES (the public contract):
    {
        "verdict":      "FAVORABLE" | "MIXED" | "WEAK" | "FLAT",
        "verdict_line": "<Python-authored one-line conclusion>",
        "timeframe":    "today" | "now" | "this_week" | "this_month"
                      | "this_year" | "when" | "none",
        "window":       {                                # scoped to timeframe
            "label":               "...",
            "date_range":          "...",
            "intraday_boundary":   "21:53 local" | None,
        },
        "the_move":     "<one verb-first action sentence>",
        "anchor":       {"source": ..., "detail": ...} | None,
        "confidence":   "high" | "medium" | "low",
        "secondary_note": "<optional context sentence, never headline>",
    }

THE TWO BIG GUARDS WS0 GIVES YOU FREE:
  1. Verdict stability — same inputs map deterministically to the
     same band, then to the same Python-authored sentence template.
  2. Timeframe honesty — a "today"/"now" question CANNOT return a
     multi-year-deferral headline. Deferrals are demoted to
     `secondary_note`; the primary verdict_line addresses today.

This module is pure. No LLM in this path. No network IO. No cache —
inputs ARE the cache key.
"""

from __future__ import annotations
from datetime import datetime, date as _date, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────
# Public constants
# ─────────────────────────────────────────────────────────────────────

VERDICT_FAVORABLE = "FAVORABLE"
VERDICT_MIXED     = "MIXED"
VERDICT_WEAK      = "WEAK"
VERDICT_FLAT      = "FLAT"

TIMEFRAME_TODAY   = "today"
TIMEFRAME_NOW     = "now"
TIMEFRAME_WEEK    = "this_week"
TIMEFRAME_MONTH   = "this_month"
TIMEFRAME_YEAR    = "this_year"
TIMEFRAME_WHEN    = "when"
TIMEFRAME_NONE    = "none"

# Tactical timeframes are the ones where a multi-year-deferral headline
# would be dishonest. WS1 guard uses this set.
_TACTICAL = {TIMEFRAME_TODAY, TIMEFRAME_NOW}


# ─────────────────────────────────────────────────────────────────────
# WS1 — Timeframe extractor
# ─────────────────────────────────────────────────────────────────────

# Order matters — most specific first. Each entry is
# (timeframe, list of markers). Spanish + English in one pass.
_TIMEFRAME_MARKERS: List[Tuple[str, List[str]]] = [
    (TIMEFRAME_NOW,   [
        "right now", "this moment", "this minute", "this very moment",
        "at this moment", "in this moment", "now?", "now.", "now,",
        "ahora mismo", "en este momento", "en este instante",
    ]),
    (TIMEFRAME_TODAY, [
        "today", "tonight", "this morning", "this afternoon",
        "this evening", "today's", "for today", "this hour",
        "hoy", "esta tarde", "esta noche", "esta mañana",
    ]),
    (TIMEFRAME_WEEK,  [
        "this week", "the next 7 days", "the next seven days",
        "the coming week", "esta semana", "la próxima semana",
        "la proxima semana",
    ]),
    (TIMEFRAME_MONTH, [
        "this month", "the next 30 days", "the next month",
        "este mes", "el próximo mes", "el proximo mes",
    ]),
    (TIMEFRAME_YEAR,  [
        "this year", "the next 12 months", "in 2026", "in 2027",
        "este año", "el próximo año", "el proximo ano",
    ]),
    (TIMEFRAME_WHEN,  [
        "when will", "when can", "when do", "when does", "when is",
        "what year", "which year", "by when",
        "cuándo voy", "cuando voy", "cuándo será", "cuando sera",
        "en qué año", "en que año",
    ]),
]


def extract_timeframe(question: Optional[str]) -> str:
    """Return one of the TIMEFRAME_* constants. Conservative: when no
    marker is present, returns NONE so the resolver answers the general
    status of the area rather than over-committing to a horizon."""
    if not question:
        return TIMEFRAME_NONE
    q = str(question).lower()
    for tf, markers in _TIMEFRAME_MARKERS:
        for m in markers:
            if m in q:
                return tf
    return TIMEFRAME_NONE


def is_tactical_timeframe(tf: str) -> bool:
    """True when answering for today / right now."""
    return tf in _TACTICAL


# ─────────────────────────────────────────────────────────────────────
# Scoring — reuse precision_windows._score_date for today; for longer
# horizons, pick the best window's score in that horizon.
# ─────────────────────────────────────────────────────────────────────

def _score_today(
    chart_data: Dict[str, Any],
    dashas: Dict[str, Any],
    current_transits: Any,
    concern: str,
    detected_yogas: List[str],
    user_correlations: List[Dict[str, Any]],
    today: datetime,
) -> Tuple[float, List[str]]:
    """Direct call into the existing precision_windows scorer for today
    only. Returns (score 0-10, list[str] reasons). Never raises —
    failure returns (0.0, [])."""
    try:
        from antar_engine.precision_windows import _score_date, _build_transit_map
        transit_map = _build_transit_map(current_transits) if isinstance(current_transits, list) else (
            current_transits if isinstance(current_transits, dict) else {}
        )
        # When current_transits is a dict keyed by planet name like
        # {"Saturn": {"sign": "..."}}, _build_transit_map only handles
        # the list-of-dicts form, so we re-normalise here.
        if isinstance(current_transits, dict) and not transit_map:
            transit_map = {
                str(p): (v.get("sign") or v.get("current_sign") or v.get("transit_sign") or "")
                for p, v in current_transits.items()
                if isinstance(v, dict)
            }
        score, reasons = _score_date(
            target_date=today,
            chart_data=chart_data or {},
            dashas=dashas or {},
            transit_map=transit_map or {},
            concern=concern,
            detected_yogas=detected_yogas or [],
            user_correlations=user_correlations or [],
        )
        return float(score or 0.0), list(reasons or [])
    except Exception:
        return 0.0, []


def _score_horizon(
    precision_windows: List[Dict[str, Any]],
    today: datetime,
    horizon_days: int,
) -> Tuple[float, Optional[Dict[str, Any]]]:
    """Pick the best precision_window whose start_date falls inside the
    horizon. Returns (peak_score, window or None). For tactical/today
    we IGNORE windows that start in the future."""
    if not precision_windows:
        return 0.0, None
    best_score = 0.0
    best_window = None
    cutoff = today + timedelta(days=horizon_days)
    for w in precision_windows:
        if w.get("is_intraday"):
            continue
        s = w.get("start_date")
        if isinstance(s, datetime):
            start_dt = s
        elif isinstance(s, str):
            try:
                start_dt = datetime.fromisoformat(s[:10])
            except Exception:
                continue
        else:
            continue
        if start_dt > cutoff:
            continue
        try:
            sc = float(w.get("score", 0))
        except (TypeError, ValueError):
            sc = 0.0
        if sc > best_score:
            best_score = sc
            best_window = w
    return best_score, best_window


def _rarity_bonus_for_concern(
    rarity_signals: List[Dict[str, Any]],
    area_karakas: List[str],
    area_keywords: List[str],
) -> Tuple[float, Optional[Dict[str, Any]]]:
    """Score boost from a rarity signal that genuinely matches the
    asked area. Range 0-2."""
    if not rarity_signals:
        return 0.0, None
    karakas = {k.lower() for k in (area_karakas or [])}
    best_bonus = 0.0
    matched: Optional[Dict[str, Any]] = None
    for sig in rarity_signals:
        planets = [str(p).lower() for p in (sig.get("planets") or [])]
        blob = " ".join(str(sig.get(k, "")) for k in ("title", "message", "type")).lower()
        karaka_hit = any(p in karakas for p in planets)
        kw_hit = any(kw in blob for kw in (area_keywords or []))
        if not (karaka_hit or kw_hit):
            continue
        try:
            r = float(sig.get("rarity_score", 0))
        except (TypeError, ValueError):
            r = 0.0
        bonus = min(2.0, r / 5.0)
        if bonus > best_bonus:
            best_bonus = bonus
            matched = sig
    return best_bonus, matched


def _intraday_present(precision_windows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the intraday window if WS4 populated one, else None."""
    for w in (precision_windows or []):
        if w.get("is_intraday"):
            return w
    return None


# ─────────────────────────────────────────────────────────────────────
# Band mapping — fixed thresholds
# ─────────────────────────────────────────────────────────────────────

def _band(
    has_anchor: bool,
    today_score: float,
    horizon_score: float,
    rarity_bonus: float,
    tf: str,
) -> Tuple[str, float, str]:
    """Returns (verdict_band, combined_score, confidence).

    For tactical timeframes (today/now) the combined score is dominated
    by `today_score` — a strong future window does NOT save a flat
    today. For non-tactical timeframes the horizon score dominates.

    No anchor at all → FLAT, regardless of score (true generic check).
    """
    if not has_anchor and rarity_bonus < 0.1 and today_score < 1.5 and horizon_score < 1.5:
        return VERDICT_FLAT, 0.0, "low"

    if tf in _TACTICAL:
        combined = today_score + rarity_bonus
    else:
        combined = max(today_score, horizon_score) + rarity_bonus

    combined = round(max(0.0, min(combined, 10.0)), 2)

    if combined >= 6.0:
        band = VERDICT_FAVORABLE
        conf = "high"
    elif combined >= 4.0:
        band = VERDICT_MIXED
        conf = "medium"
    elif combined >= 1.8:
        band = VERDICT_WEAK
        conf = "medium" if has_anchor else "low"
    else:
        band = VERDICT_FLAT
        conf = "low"

    return band, combined, conf


# ─────────────────────────────────────────────────────────────────────
# Python-authored verdict_line + the_move templates
# (boring, deterministic, plain-English — Claude rephrases tone only)
# ─────────────────────────────────────────────────────────────────────

# Per concern, a tiny library of substantive nouns we use to fill the
# Python-authored sentences. Keeps DOMAIN_VOCABULARY alive without
# leaking energy labels.
# [b-life-nouns] V2.2 gap (b): subjects now name the decision being weighed,
# not the bare category. Doctrine: "concrete life-nouns, not abstractions."
_CONCERN_NOUNS: Dict[str, Dict[str, str]] = {
    "speculation":  {"subject": "the speculative call you're weighing", "act": "deploy capital", "watch": "the speculative read"},
    "property":     {"subject": "the property move you're sitting on",    "act": "move on a purchase", "watch": "the property read"},
    "career":       {"subject": "the career step you're considering",      "act": "make the career move", "watch": "the career read"},
    "finance":      {"subject": "the money decision in front of you",   "act": "act on the money decision", "watch": "the money read"},
    "wealth":       {"subject": "the wealth move you're weighing",      "act": "act on the wealth move", "watch": "the wealth read"},
    "loss":         {"subject": "the drain you're trying to plug",   "act": "plug the leak", "watch": "the drain pattern"},
    "marriage":     {"subject": "the partnership conversation in front of you", "act": "have the partnership conversation", "watch": "the partnership read"},
    "love":         {"subject": "the relationship call you're weighing", "act": "have the relationship conversation", "watch": "the relationship read"},
    "reconciliation":{"subject":"the reconnection you're considering","act": "make the move to reconnect", "watch": "the reconnection read"},
    "divorce":      {"subject": "the separation decision in front of you", "act": "make the split move", "watch": "the separation read"},
    "health":       {"subject": "the health decision in front of you",  "act": "act on the health decision", "watch": "the health read"},
    "foreign":      {"subject": "the relocation move you're weighing", "act": "make the relocation move", "watch": "the relocation read"},
    "spiritual":    {"subject": "the dharma move you're considering", "act": "act on the dharma move", "watch": "the purpose read"},
    "family":       {"subject": "the family decision in front of you", "act": "act on the family decision", "watch": "the family read"},
    "children":     {"subject": "the family-growth question you're weighing", "act": "act on the family move", "watch": "the family read"},
    "general":      {"subject": "the main move you're weighing", "act": "act on the main move", "watch": "the read"},
}


def _nouns(concern: str) -> Dict[str, str]:
    return _CONCERN_NOUNS.get((concern or "general").lower(), _CONCERN_NOUNS["general"])


def _is_es(language: Optional[str]) -> bool:
    return (language or "en").lower().startswith("es")


def _compose_verdict_line(
    band: str,
    tf: str,
    concern: str,
    language: str,
    anchor: Optional[Dict[str, Any]] = None,
    redirect: Optional[Dict[str, Any]] = None,
) -> str:
    # [b-life-nouns] V2.2 gap (b): when `anchor` carries a concrete date_range
    # (precision_window source), weave it into FAVORABLE / MIXED non-tactical
    # lines so the read names a real window instead of waving at "soon".
    nouns = _nouns(concern)
    subj = nouns["subject"]
    # [b-life-nouns] subjects are now full phrases ("the property move you're
    # sitting on"); .title() mangles apostrophes ("You'Re"). Cap only the
    # first character for sentence-start positions.
    subj_cap = (subj[:1].upper() + subj[1:]) if subj else subj
    is_es = _is_es(language)
    tactical = tf in _TACTICAL

    # Extract a usable anchor phrase (only date_range is safe — labels and
    # rarity titles may carry Sanskrit / planet names). Sanitised by the
    # presence-check pattern: must look like a date span.
    anchor_phrase = ""
    if anchor and isinstance(anchor, dict):
        _detail = str(anchor.get("detail") or "")
        # Heuristic: a date_range contains a digit and an en-dash or hyphen.
        if any(c.isdigit() for c in _detail) and any(d in _detail for d in ("–", "-", "to")):
            anchor_phrase = _detail

    if band == VERDICT_FLAT:
        if redirect:
            ga = (redirect.get("guessed_area") or "another area").lower()
            if is_es:
                return f"Hoy {subj} está neutral — lo que sí está activo es {ga}."
            return f"{subj_cap} is flat for you today — what's actually live is {ga}."
        if tactical:
            if is_es:
                return f"Hoy {subj} está en una ventana neutral — sin señal específica."
            return f"{subj_cap} is flat for you today — no specific signal."
        if is_es:
            return f"No hay una señal específica para {subj} ahora mismo."
        return f"Nothing unusual is active for {subj} right now."

    if band == VERDICT_WEAK:
        if tactical:
            if is_es:
                return f"Hoy es una ventana floja para {subj} — frena las apuestas grandes."
            return f"Today is a soft window for {subj} — hold off on big moves."
        if is_es:
            return f"{subj_cap} está flojo para ti ahora — ventana floja."
        return f"{subj_cap} is soft for you right now — not a strong window."

    if band == VERDICT_MIXED:
        if tactical:
            if is_es:
                return f"Hoy {subj} está mixto — sigue con lo pequeño, no fuerces lo grande."
            return f"{subj_cap} is mixed today — keep moving the small pieces, do not force the big one."
        if anchor_phrase:
            if is_es:
                return f"{subj_cap} está mixto — apoyo estructural, ventana estrecha en {anchor_phrase}."
            return f"{subj_cap} is mixed — structurally supportive, with a narrow window around {anchor_phrase}."
        if is_es:
            return f"{subj_cap} está mixto — apoyo estructural, ventana estrecha."
        return f"{subj_cap} is mixed — structurally supportive, narrow timing."

    # FAVORABLE
    if tactical:
        if is_es:
            return f"Hoy {subj} está bien apoyado — actúa ahora."
        return f"{subj_cap} is well-supported for you today — act now."
    if anchor_phrase:
        if is_es:
            return f"{subj_cap} está bien apoyado por tu carta — especialmente {anchor_phrase}."
        return f"{subj_cap} is well-supported by your chart — especially {anchor_phrase}."
    if is_es:
        return f"{subj_cap} está bien apoyado por tu carta."
    return f"{subj_cap} is well-supported by your chart."


def _compose_move(
    band: str,
    tf: str,
    concern: str,
    language: str,
    anchor: Optional[Dict[str, Any]] = None,
    redirect: Optional[Dict[str, Any]] = None,
) -> str:
    nouns = _nouns(concern)
    act = nouns["act"]
    watch = nouns["watch"]
    is_es = _is_es(language)

    if band == VERDICT_FLAT:
        if redirect:
            ga = (redirect.get("guessed_area") or "the live area").lower()
            if is_es:
                return f"Aprovecha la ventana abierta en {ga} en lugar de forzar {nouns['subject']}."
            return f"Pivot to {ga} where the window is open instead of forcing {nouns['subject']}."
        if is_es:
            return f"Quédate con tu rutina base; no fuerces {act} hoy."
        return f"Hold your baseline routine; do not force {act} today."

    if band == VERDICT_WEAK:
        if is_es:
            return f"Frena {act}; revisa de nuevo {watch} en 24-48 horas."
        return f"Hold off on {act}; re-check {watch} in 24-48 hours."

    if band == VERDICT_MIXED:
        if is_es:
            return f"Mueve la pieza pequeña hoy; reserva {act} para una ventana más fuerte."
        return f"Move the small piece today; save {act} for a stronger window."

    # FAVORABLE
    if is_es:
        return f"{act.title()} dentro de la ventana indicada."
    return f"{act.title()} within the window shown."


def _format_window(
    horizon_window: Optional[Dict[str, Any]],
    intraday_window: Optional[Dict[str, Any]],
    tf: str,
) -> Dict[str, Any]:
    label = ""
    date_range = ""
    intraday_boundary = None
    if intraday_window and tf in _TACTICAL:
        date_range = str(intraday_window.get("date_range") or "")
        label = str(intraday_window.get("window_label") or "Intraday window")
        # The intraday "now → 21:53 local" form already encodes the
        # boundary in date_range; surface the boundary separately too.
        reasons = intraday_window.get("reasons") or []
        if reasons:
            intraday_boundary = str(reasons[0])
    elif horizon_window:
        date_range = str(horizon_window.get("date_range") or "")
        label = str(horizon_window.get("window_label") or "Window")
    return {
        "label": label,
        "date_range": date_range,
        "intraday_boundary": intraday_boundary,
    }


def _compose_secondary_note(
    band: str,
    tf: str,
    concern: str,
    language: str,
    horizon_window: Optional[Dict[str, Any]],
) -> Optional[str]:
    """WS1 deferral cap: a today/now question may NOT headline a
    multi-month/multi-year deferral. If the structurally-best window
    is far away, it shows up here as context — never as the verdict."""
    if tf not in _TACTICAL or not horizon_window:
        return None
    date_range = str(horizon_window.get("date_range") or "")
    if not date_range:
        return None
    is_es = _is_es(language)
    subj = _nouns(concern)["subject"]
    if is_es:
        return f"La ventana estructural más fuerte para {subj} llega {date_range}; eso es contexto, no la llamada de hoy."
    return f"The strongest structural window for {subj} is {date_range}; that's context, not today's call."


# ─────────────────────────────────────────────────────────────────────
# Public entry
# ─────────────────────────────────────────────────────────────────────

def resolve_domain_verdict(
    *,
    chart_id: str,
    concern: str,
    question: str,
    today: Optional[datetime] = None,
    chart_data: Optional[Dict[str, Any]] = None,
    dashas: Optional[Dict[str, Any]] = None,
    current_transits: Any = None,
    detected_yogas: Optional[List[str]] = None,
    user_correlations: Optional[List[Dict[str, Any]]] = None,
    rarity_signals: Optional[List[Dict[str, Any]]] = None,
    precision_windows: Optional[List[Dict[str, Any]]] = None,
    anchor_decision: Optional[Dict[str, Any]] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """The deterministic resolver. Returns the verdict dict described
    at the top of the module. Never raises — every failure path
    degrades to a FLAT verdict so /predict never falls through."""
    today = today or datetime.utcnow()
    tf = extract_timeframe(question)

    # WS2 — wider domain scan (life_area_map). Imported here to keep
    # this module's dependency surface minimal at import time.
    try:
        from antar_engine.life_area_map import area_karakas
        karakas = area_karakas(concern)
    except Exception:
        karakas = []
    try:
        from antar_engine.domain_anchor import _AREA_KEYWORDS  # type: ignore
        keywords = _AREA_KEYWORDS.get((concern or "general").lower(), [])
    except Exception:
        keywords = []

    # Anchor decision from has_domain_anchor (computed earlier in /predict).
    has_anchor = bool((anchor_decision or {}).get("has_anchor"))
    redirect = (anchor_decision or {}).get("redirect_candidate")
    anchor = (anchor_decision or {}).get("anchor")

    # Score today directly (tactical answers must reflect today).
    today_score, today_reasons = _score_today(
        chart_data or {}, dashas or {}, current_transits, concern,
        detected_yogas or [], user_correlations or [], today,
    )

    # For non-tactical timeframes, pick the best window inside the
    # asked horizon. Today/now skips this.
    if tf == TIMEFRAME_WEEK:
        horizon_days = 7
    elif tf == TIMEFRAME_MONTH:
        horizon_days = 31
    elif tf == TIMEFRAME_YEAR:
        horizon_days = 366
    elif tf == TIMEFRAME_WHEN:
        horizon_days = 366
    else:
        horizon_days = 0

    horizon_score, horizon_window = _score_horizon(
        precision_windows or [], today, horizon_days or 366,
    )

    rarity_bonus, matched_rarity = _rarity_bonus_for_concern(
        rarity_signals or [], karakas, keywords,
    )

    band, combined, conf = _band(has_anchor, today_score, horizon_score, rarity_bonus, tf)

    intraday_window = _intraday_present(precision_windows or [])
    window_dict = _format_window(horizon_window, intraday_window, tf)

    verdict_line = _compose_verdict_line(band, tf, concern, language, anchor, redirect)
    the_move    = _compose_move(band, tf, concern, language, anchor, redirect)
    secondary   = _compose_secondary_note(band, tf, concern, language, horizon_window)

    # Resolved anchor: prefer the explicit anchor; fall back to matched
    # rarity; then anchor_decision.
    resolved_anchor: Optional[Dict[str, Any]] = anchor
    if not resolved_anchor and matched_rarity:
        resolved_anchor = {
            "source": "rarity_signal",
            "detail": matched_rarity.get("title") or matched_rarity.get("type"),
        }

    return {
        "verdict":        band,
        "verdict_line":   verdict_line,
        "timeframe":      tf,
        "window":         window_dict,
        "the_move":       the_move,
        "anchor":         resolved_anchor,
        "redirect_candidate": redirect,
        "confidence":     conf,
        "secondary_note": secondary,
        # Diagnostics — useful in logs, not surfaced to the user.
        "_debug": {
            "today_score":   round(today_score, 2),
            "horizon_score": round(horizon_score, 2),
            "rarity_bonus":  round(rarity_bonus, 2),
            "combined":      combined,
            "today_reasons": today_reasons[:4],
            "has_anchor":    has_anchor,
            "chart_id":      chart_id,
        },
    }


# ─────────────────────────────────────────────────────────────────────
# Prompt fixation — turns the verdict into a "FIXED FACTS" block
# the prompt builder injects into the system prompt.
# ─────────────────────────────────────────────────────────────────────

def build_fixed_facts_block(verdict: Dict[str, Any], language: str = "en") -> str:
    """Returns the system-prompt block that pins the conclusion.
    The block forbids re-derivation, timeframe drift, and inversion."""
    if not verdict:
        return ""
    is_es = _is_es(language)
    lines: List[str] = []
    lines.append("")
    lines.append("═══ FIXED FACTS — DO NOT CHANGE ═══")
    lines.append("Python has computed the verdict, the timeframe, the window")
    lines.append("and the move. You NARRATE these facts in plain language;")
    lines.append("you do NOT re-derive, soften, invert, or change the timeframe.")
    lines.append("")
    lines.append(f"VERDICT (band):   {verdict.get('verdict', '')}")
    lines.append(f"VERDICT LINE:     {verdict.get('verdict_line', '')}")
    lines.append(f"TIMEFRAME:        {verdict.get('timeframe', '')}")
    w = verdict.get("window") or {}
    if w.get("date_range"):
        lines.append(f"WINDOW:           {w.get('label','')} — {w.get('date_range','')}")
    if w.get("intraday_boundary"):
        lines.append(f"INTRADAY:         {w.get('intraday_boundary','')}")
    lines.append(f"THE MOVE:         {verdict.get('the_move', '')}")
    if verdict.get("secondary_note"):
        lines.append(f"SECONDARY NOTE:   {verdict.get('secondary_note')}")
    lines.append("")
    lines.append("HARD RULES:")
    lines.append("  - Your `signal_line` MUST be the VERDICT LINE (or a tone-")
    lines.append("    rephrasing that preserves its meaning, band, and timeframe).")
    lines.append("  - Your `action_item` MUST be THE MOVE.")
    lines.append("  - Your `timing_window` MUST be the WINDOW above.")
    lines.append("  - Your `plain_summary` may add 1-3 sentences of context but")
    lines.append("    MUST NOT flip the band, change the timeframe, or invert the")
    lines.append("    move. A TODAY verdict CANNOT be answered as a multi-year")
    lines.append("    deferral. If you want to mention a longer horizon, put it")
    lines.append("    AFTER today's call as one note — never as the headline.")
    lines.append("  - Never emit 'wait until ___' / 'wait until when ___'.")
    lines.append("  - Never end with a fishing / clarifying question.")
    lines.append("  - Keep DOMAIN_VOCABULARY (runway, leverage, positioning).")
    lines.append("    Never emit internal energy labels like")
    lines.append("    'structure-and-persistence', 'identity-and-authority',")
    lines.append("    'release-and-dissolution', 'growth-and-wisdom',")
    lines.append("    'action-and-drive', etc. Use single nouns.")
    if is_es:
        lines.append("  - Idioma: español.")
    lines.append("═══ END FIXED FACTS ═══")
    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# [band-consistency] compose_plain_summary
# Band-consistent plain_summary used by main.py when Claude's narration
# drifts off the band (positive prose on FLAT/WEAK, etc.). FAVORABLE
# and MIXED bands keep Claude's voice — only FLAT/WEAK get rewritten
# to prevent the verdict ↔ summary contradiction.
# ─────────────────────────────────────────────────────────────────────

def compose_plain_summary(verdict: dict, language: str = "en") -> str:
    """Python-authored plain_summary aligned with the band. Always
    safe to call — returns empty string when verdict is missing."""
    if not verdict:
        return ""
    band = verdict.get("verdict") or ""
    tf = verdict.get("timeframe") or ""
    concern = (verdict.get("_debug") or {}).get("chart_id") and ""  # unused
    # Pull concern back out via the verdict_line — we kept the noun-map.
    # We re-derive subject from the verdict_line's first word.
    line = verdict.get("verdict_line") or ""
    is_es = (language or "en").lower().startswith("es")
    secondary = verdict.get("secondary_note") or ""
    redirect = verdict.get("redirect_candidate") or None

    # Find the subject token from verdict_line (its leading word).
    # That's good enough — verdict_line begins with the concern noun.
    first = line.split(" — ")[0].split(".")[0]

    if band == VERDICT_FLAT:
        if redirect:
            ga = (redirect.get("guessed_area") or "another area").lower()
            if is_es:
                body = (
                    f"{first}. Hoy no hay una señal de carta específica para esta"
                    f" ventana. Lo que sí está vivo es {ga} — esa es la ventana"
                    " donde el momento favorece tu siguiente movimiento."
                )
            else:
                body = (
                    f"{first}. There is no chart-specific signal active for this"
                    f" area today. What IS live for you is {ga} — that is where"
                    " the timing actually favours a next move."
                )
        else:
            if is_es:
                body = (
                    f"{first}. Hoy es una ventana neutral — nada inusual está"
                    " activo en tu carta para esta área. Mueve la rutina base,"
                    " no fuerces nada porque la fecha lo pida."
                )
            else:
                body = (
                    f"{first}. Today is a neutral window — nothing unusual is"
                    " active in your chart for this area. Move your baseline"
                    " routine; do not force a step because the date demands one."
                )
        if secondary:
            body += " " + secondary
        return body

    if band == VERDICT_WEAK:
        if is_es:
            body = (
                f"{first}. Hoy es una ventana floja para esta área — la energía"
                " es muestra-y-revisión, no compromiso. Apúrate a las piezas"
                " pequeñas; reserva las apuestas grandes para una ventana más"
                " fuerte."
            )
        else:
            body = (
                f"{first}. Today is a soft window for this area — the energy"
                " favours review and small moves, not commitment. Move the"
                " small pieces; hold the big bets for a stronger window."
            )
        if secondary:
            body += " " + secondary
        return body

    # MIXED / FAVORABLE: Claude's voice is preserved; caller skips this.
    return ""
