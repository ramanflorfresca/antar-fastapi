"""
today_narration.py — Part 6 of the Today redesign: Claude narrates the
ENGINE-chosen highlight.

Contract (founder brief, 2026-06-04):
  * The engine (today_highlight.py) picks the 1–2 domains + direction +
    strength deterministically. Claude NEVER chooses the topic — it only
    narrates the chosen one.
  * Claude receives: chosen domain(s), direction, hora windows (TODAY'S
    MOVE), the derived nudge, and soft patra context — and writes a
    committed characterizing headline + a 3–4 line highlight. Plain
    GPS-coach voice, zero jargon, no trailing questions.
  * Quiet days are NOT narrated (no manufactured drama) — the engine's
    honest template stands.
  * EN-source only; @translate_response localizes es/pt at response time.
  * The engine's template headline/highlight remain the fallback on ANY
    failure (LLM error, bad JSON, jargon leak, validation miss).

KV cache: the static instruction block is byte-identical across calls; the
per-day payload goes below the "## LIVE DATA" split that call_llm_claude()
already splits on for prompt caching.

DB cache: one narration per (chart_id, local-date, language) in
today_narration_cache (SQL provided with the patch). A fingerprint of the
engine's choice (domains + direction) is stored with the payload — if the
engine's pick shifts intra-day, the cache misses and we re-narrate.
"""

from __future__ import annotations
import json
import re
from typing import Optional

# ── Static instruction block (NEVER edit casually: byte-stability = KV hit) ──
NARRATION_STATIC = """You are the narration layer for Antar's Today card.

The prediction ENGINE has already decided what matters today — which life
domain(s) dominate, which direction the day leans (positive or adverse), and
how strongly. Your only job is to narrate that decision in plain, committed,
useful language. You never choose or change the topic.

VOICE — GPS coach: calm, direct, specific. You tell the person what kind of
day this is and how to drive it. Never mystical, never hedging, never asking.

HARD RULES:
1. Write ONLY about the chosen domain(s) in the live data. Never mention any
   other life area.
2. Commit to the given direction. positive = clearly favorable, say so
   plainly; adverse = clear caution, say so plainly. Never "mixed", never
   "on one hand", never a five-domain hedge.
3. "headline": ONE committed, characterizing line, max 90 characters. Not a
   rating ("Good day"), not a bare warning ("Be careful"). It characterizes
   the day, e.g. "A day to close the money loop you've been avoiding."
4. "highlight": 3-4 short lines, max 70 words total, on only the chosen
   domain(s). Concrete and behavioral. You may echo the timing window or the
   nudge in passing, but never quote them verbatim.
4b. GROUND every line in the "drivers" list. Each driver names a chosen domain,
   its signal (amplified = lean in; caution = ease off), and the plain reasons
   it is live today. Narrate WHY this domain is lit — not merely that it is.
   Never introduce a driver that is not in the list, and never state a number,
   score, or the mechanism behind it.
4c. BE CONCRETE — name the actual thing, not the bucket. Each driver carries
   "concrete_nouns" (the literal life-things it points to — e.g. your mother,
   your boss, a loan or credit line, a vehicle, your partner, property) and a
   "this_could_touch" phrasing. Name 2-3 of these specific nouns with the day's
   timing — "review any new loan or credit line today", "your boss is likely to
   back you", "a home or vehicle expense may come up". NEVER write the abstract
   bucket alone ("relationships need attention", "focus on work"). Selective,
   not scattershot: name only the nouns given for the chosen domain(s) — do not
   list every possibility. The nouns ARE results, so naming them is correct;
   still never name the house, planet, or number behind them.
5. Use the "weighing_on_user" context, when present, to sharpen relevance —
   speak to what this person is actually carrying. Do not name the context
   itself or say "you asked about".
6. ZERO jargon: no planet names, no Sanskrit, no houses, no astrology terms,
   no "the energy of X", no weekday names, no dates.
7. No questions anywhere. No emojis. No exclamation marks. Second person.
8. English only.
9. Output STRICT JSON and nothing else: {"headline": "...", "highlight": "..."}

## LIVE DATA
"""


def build_narration_system(
    engine: dict,
    nudge: Optional[str],
    first_name: str = "",
    patra_domains: Optional[list] = None,
    lk_daily: Optional[dict] = None,
    date_str: str = "",
    drivers: Optional[list] = None,
) -> str:
    """Static block + per-day JSON tail (below the KV split)."""
    hora = engine.get("todays_move") or engine.get("hora") or {}
    lk_daily = lk_daily or {}
    payload = {
        "date": date_str,
        "first_name": (first_name or "").split(" ")[0][:24],
        "domains": engine.get("highlight_domains") or [],
        "direction": engine.get("direction"),
        "strength": engine.get("strength"),
        "drivers": drivers or [],
        "weighing_on_user": patra_domains or [],
        "day_quality": lk_daily.get("day_quality_for_user") or "",
        "engine_draft_headline": engine.get("headline") or "",
        "engine_draft_highlight": engine.get("highlight") or "",
        "best_window": hora.get("best_window") or "",
        "best_for": hora.get("best_for") or "",
        "avoid_window": hora.get("avoid_window") or "",
        "avoid_what": hora.get("avoid_what") or "",
        "nudge": nudge or "",
    }
    return NARRATION_STATIC + json.dumps(payload, ensure_ascii=False)


# ── driver summary: _debug_reasoning votes -> narratable conclusions ─────────

# vote source-kind -> (plain reason, ordering rank). Chart-specific reasons are
# the strongest "why", attention next, personal context last. ZERO jargon:
# these are conclusions, never the mechanism (no houses, planets, or scores).
_DRIVER_REASON = {
    "lk_amplify": ("this area is specifically lit for you today", 0),
    "lk_avoid":   ("your own pattern asks for extra care here today", 0),
    "moon_house": ("this is where your attention naturally lands today", 1),
    "patra":      ("it connects to what you're focused on right now", 2),
}


def summarize_drivers(debug: Optional[dict], chosen: Optional[list] = None) -> list:
    """Turn the engine's _debug_reasoning into a per-chosen-domain driver list:
        [{"domain": "money", "signal": "amplified",
          "reasons": ["this area is specifically lit for you today", ...]}, ...]
    Reads only the structured votes (already jargon-free); never the raw LK
    text or the el_movimiento sentence (which carry mechanism/jargon)."""
    if not isinstance(debug, dict):
        return []
    chosen = chosen or debug.get("chosen") or []
    if not chosen:
        return []
    net = debug.get("net") or {}
    votes = debug.get("votes") or []

    by_domain: dict = {d: [] for d in chosen}
    house_for: dict = {}                       # domain -> the ACTIVATED house
    for v in votes:
        parts = str(v).split(":")
        if len(parts) < 3:
            continue
        kind, domain = parts[1], parts[2]
        if domain not in by_domain:
            continue
        # normalize "moon_house9" -> "moon_house" AND capture the real house #.
        if kind.startswith("moon_house"):
            key = "moon_house"
            try:
                house_for[domain] = int(kind[len("moon_house"):])
            except Exception:
                pass
        else:
            key = kind
        entry = _DRIVER_REASON.get(key)
        if entry and entry not in by_domain[domain]:
            by_domain[domain].append(entry)

    out = []
    for d in chosen:
        reasons = sorted(by_domain[d], key=lambda e: e[1])
        try:
            signal = "amplified" if float(net.get(d, 0)) >= 0 else "caution"
        except Exception:
            signal = "amplified"
        # NOUN LAYER (2026-06-07): translate the activated house into the
        # literal life-nouns it points to (mother, boss, loan, vehicle...),
        # direction-bound and capped at 2-3. Prefer the actually-activated
        # house (Moon-attention vote); fall back to the domain's primary house
        # only when no house is in hand (LK amplify/avoid path).
        nouns, theme, phrase = [], "", ""
        try:
            from antar_engine.house_significations import resolve_signal
            _direction = "positive" if signal == "amplified" else "adverse"
            _sig = resolve_signal(house_for.get(d), d, _direction, limit=3)
            nouns = _sig.get("nouns", [])
            theme = _sig.get("theme", "")
            phrase = _sig.get("phrase", "")
        except Exception:
            pass
        out.append({
            "domain": d,
            "signal": signal,
            "reasons": [r for r, _ in reasons] or
                       ["this is the clearest signal in your day"],
            "concrete_nouns": nouns,
            "life_area": theme,
            "this_could_touch": phrase,
        })
    return out


# ── Output validation — fall back to the engine template on ANY miss ─────────

_JARGON_RX = re.compile(
    r"(?i)\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"nakshatra|dasha|mahadasha|antardasha|tithi|muhurta|hora|lagna|"
    r"ascendant|retrograde|transit|zodiac|horoscope|astrolog\w*|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"\d{1,2}(?:st|nd|rd|th)\s+house|house\s+\d{1,2})\b"
)


def _extract_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    txt = raw.strip()
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.IGNORECASE)
    start, end = txt.find("{"), txt.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(txt[start:end + 1])
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def parse_and_validate(raw: str, language: str = "en") -> Optional[dict]:
    """Parse Claude's JSON and enforce the contract. None = use the template."""
    obj = _extract_json(raw)
    if not obj:
        return None
    headline = (obj.get("headline") or "").strip()
    highlight = (obj.get("highlight") or "").strip()
    if not headline or not highlight:
        return None

    # Reject RAW jargon leaks outright — a strip-rewritten sentence reads
    # mangled; the engine's clean template is the better fallback.
    if _JARGON_RX.search(headline) or _JARGON_RX.search(highlight):
        return None

    # Defense-in-depth: run the standard strip layer, then re-check.
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        headline = apply_user_facing_strips(headline, language=language,
                                            field_type="headline")
        highlight = apply_user_facing_strips(highlight, language=language,
                                             field_type="plain")
    except Exception:
        pass

    headline = re.sub(r"\s+", " ", headline).strip()
    highlight = highlight.strip()

    if not (10 <= len(headline) <= 120):
        return None
    if not (80 <= len(highlight) <= 700):
        return None
    if "?" in headline or "?" in highlight:
        return None
    if "!" in headline or "!" in highlight:
        return None
    if _JARGON_RX.search(headline) or _JARGON_RX.search(highlight):
        return None
    return {"headline": headline, "highlight": highlight}


# ── DB cache (today_narration_cache) ─────────────────────────────────────────

def _fingerprint(engine: dict) -> dict:
    return {
        "domains": list(engine.get("highlight_domains") or []),
        "direction": engine.get("direction"),
    }


def narration_cache_read(supabase, chart_id: str, date_str: str,
                         engine: dict, language: str = "en") -> Optional[dict]:
    """Cached narration for today, IF the engine's pick hasn't shifted."""
    try:
        res = supabase.table("today_narration_cache").select("payload") \
            .eq("chart_id", chart_id).eq("narration_date", date_str) \
            .eq("language", language).limit(1).execute()
        if not res.data:
            return None
        payload = res.data[0].get("payload")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                return None
        if not isinstance(payload, dict):
            return None
        if payload.get("_fp") != _fingerprint(engine):
            return None  # engine choice shifted intra-day — re-narrate
        if payload.get("headline") and payload.get("highlight"):
            return {"headline": payload["headline"],
                    "highlight": payload["highlight"]}
        return None
    except Exception as e:
        print(f"[today-narration] cache read skipped: {e}")
        return None


def narration_cache_write(supabase, chart_id: str, date_str: str,
                          engine: dict, narration: dict,
                          language: str = "en") -> None:
    try:
        supabase.table("today_narration_cache").upsert({
            "chart_id": chart_id,
            "narration_date": date_str,
            "language": language,
            "payload": {**narration, "_fp": _fingerprint(engine)},
        }, on_conflict="chart_id,narration_date,language").execute()
    except Exception as e:
        print(f"[today-narration] cache write skipped (table missing?): {e}")
