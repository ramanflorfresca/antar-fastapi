"""
year_narration.py — [year-varshphal] Claude narrates the deterministic
Lal Kitab Varshphal year read (founder decision 2026-06-04).

Contract (mirrors today_narration.py / Part 6):
  * The ENGINE decides everything: varshphal placements, polarity, area
    intensities, muntha, dasha chapter, sleeping planets, slow transits —
    all computed by existing Python (home_composer / practice_engine /
    transits_engine). Claude NEVER chooses; it only narrates the decided
    state into a birthday-anchored annual read.
  * Output parity with This Month: committed headline + substantive body
    (4–6 lines) + a what-to-watch line. GPS-coach voice, zero jargon,
    no questions, EN-source only (response-time translation localizes).
  * The template headline/gist remain the fallback on ANY failure
    (LLM error, bad JSON, jargon leak, validation miss).

KV cache: static block is byte-identical across calls; the per-chart
payload sits below the "## LIVE DATA" split that call_llm_claude() splits
on for prompt caching.

DB cache: one narration per (chart_id, period_start, language) in
year_narration_cache (SQL ships with the patch). An engine fingerprint
(polarity + area bars + MD lord + muntha) invalidates on state shifts —
in practice once per birthday year, plus dasha boundaries.
"""

from __future__ import annotations
import json
import re
from typing import Optional

# ── Static instruction block (NEVER edit casually: byte-stability = KV hit) ──
YEAR_NARRATION_STATIC = """You are the narration layer for Antar's This Year view.

The prediction ENGINE has already computed this person's annual state from
their birth chart: which life areas the year strengthens, which it puts
under pressure, the year's overall direction, the long chapter it sits
inside, and the season to watch. Your only job is to narrate that decided
state as one coherent year-ahead read. You never choose or change the topics.

VOICE — GPS coach for a whole year: calm, direct, specific. You tell the
person what kind of year this is, where it concentrates, and how to drive
it. Never mystical, never hedging, never asking.

HARD RULES:
1. Narrate ONLY the areas and signals in the live data. Strong areas get
   the confident build; the pressured area gets honest, practical caution.
   Never invent a life area that is not listed.
2. Commit to the overall direction. positive = a year that rewards bold,
   visible moves — say so plainly. negative = a consolidation year — say
   so plainly. Never "mixed", never "on one hand".
3. "headline": ONE committed, characterizing line for the YEAR, max 90
   characters. Not a rating, not generic ("A good year ahead"). It should
   feel written for this person's specific mix.
4. "body": 4-6 short lines, 80-130 words. Structure: what the year is
   fundamentally about → where it concentrates (the strong areas, concretely)
   → the pressured area and how to hold it → how the long chapter colors the
   whole year. Concrete and behavioral; this is the read someone plans their
   year around.
4b. BE CONCRETE — name the actual life-things, not the abstract area. The
   "concrete_nouns" list holds the literal things this year touches (your boss,
   property, a vehicle, a loan or credit line, your father, savings, your
   partner). Weave 2-4 of these into the body so the read names real life, not
   categories — "a property or vehicle decision", "your standing with your boss",
   "income through your network". Never write the bare bucket ("focus on
   career", "relationships matter this year"). Selective, not a list: only the
   nouns that fit the strong/pressured areas. The nouns ARE results — naming
   them is correct; still never name a house number, planet, or sign.
5. "watch": 1-2 lines, max 40 words. The specific stretch or dynamic to
   watch (use the season window in the live data) and the one behavior that
   protects it.
6. ZERO jargon: no planet names, no Sanskrit, no signs, no houses, no
   "the energy of X", no astrology terms, no weekday names. Translate any
   internal term in the live data into plain life language.
7. No questions. No emojis. No exclamation marks. Second person.
8. English only.
8b. SINGLE-SOURCE: never assert that a specific life event (marriage,
   breakup, a child, relocation, job change, a purchase, a lawsuit) will
   happen in a specific dated window. Dated event calls come from a separate
   engine and are NOT in your data. Describe the year's conditions and the
   season to watch; never invent event timing.
9. Output STRICT JSON and nothing else:
   {"headline": "...", "body": "...", "watch": "..."}

READABILITY (NON-NEGOTIABLE):
- Write for a smart, busy person who knows nothing about astrology. Sound like a sharp human
  coach texting them — not a report, not a mystic.
- First sentence = the answer, in plain words. No build-up, no setup.
- One idea per sentence. Keep sentences under ~18 words. At most one "because/which/that"
  clause per sentence. Never stack clauses.
- Use everyday words. Ban abstract constructions: no "energy", "vibration", "alignment of",
  "structure-and-persistence", or any noun-energy phrasing. Say the concrete thing instead.
- If you explain why, ONE short why-sentence, concrete. No nested reasoning.
- End with ONE specific action the person can take.
- Active voice. Second person ("you"). No hedging stacks ("may possibly tend to").

## LIVE DATA
"""

_SLOW_PLANETS = ("Saturn", "Jupiter", "Rahu", "Ketu")


def build_year_engine_state(
    year: dict,
    attention: Optional[dict],
    muntha: str,
    highlights: list,
    chart_data: dict,
    lk_data: dict,
    birth_date: str,
    current_md_row: Optional[dict],
    next_md_row: Optional[dict],
) -> dict:
    """Assemble the deterministic annual state from what the engines already
    compute. Internal names (planets/signs) are allowed HERE — they are
    Claude's input; rule 6 forbids them in the OUTPUT."""
    state = {
        "year_range": year.get("range") or "",
        "polarity": year.get("polarity") or "",
        "areas": [
            {"name": a.get("name"), "bars": a.get("bars"),
             "under_pressure": bool(a.get("care")), "note": a.get("note")}
            for a in (year.get("areas") or []) if isinstance(a, dict)
        ],
        "season_watch": (year.get("stretch") or {}).get("worst") or "",
        "season_best": (year.get("stretch") or {}).get("best") or "",
        "template_use": year.get("use") or "",
        "muntha_sign": muntha or "",
        "engine_highlights": [
            h.get("text") for h in (highlights or [])
            if isinstance(h, dict) and h.get("text")
        ][:5],
    }
    # Long chapter (Vimsottari MD) + the handover, if known
    if isinstance(current_md_row, dict) and current_md_row.get("planet_or_sign"):
        state["long_chapter"] = {
            "lord": current_md_row.get("planet_or_sign"),
            "ends": str(current_md_row.get("end_date") or "")[:10],
        }
    if isinstance(next_md_row, dict) and next_md_row.get("planet_or_sign"):
        state["next_chapter"] = {
            "lord": next_md_row.get("planet_or_sign"),
            "starts": str(next_md_row.get("start_date") or "")[:10],
        }
    # Needs-attention diagnosis (planet allowed as input; issue is plain)
    if isinstance(attention, dict) and attention.get("flagged"):
        state["weak_signal"] = {
            "planet": attention.get("planet"),
            "issue": attention.get("issue"),
        }
    # Varshphal placements for this birthday year (already-shipped math)
    try:
        from antar_engine.home_composer import _natal_houses, _varshphal_placements
        natal = _natal_houses(chart_data)
        state["varshphal_houses"] = _varshphal_placements(birth_date, natal) or {}
    except Exception:
        state["varshphal_houses"] = {}
    # Sleeping planets (Lal Kitab) — same extractor the year endpoint uses
    try:
        from antar_engine import practice_engine as _pe
        sleeping = _pe._extract_sleeping_planets(lk_data) or []
        state["sleeping_planets"] = [
            s.get("planet") for s in sleeping if isinstance(s, dict) and s.get("planet")
        ]
    except Exception:
        state["sleeping_planets"] = []
    # Slow-planet transits (year-scale weather) — reuse the daily engine
    try:
        from antar_engine.transits_engine import calculate_current_transits
        _tr = (calculate_current_transits(chart_data) or {}).get("current_transits", [])
        state["slow_transits"] = [
            {"planet": t.get("planet"), "house": t.get("house"),
             "sign": t.get("sign")}
            for t in _tr
            if isinstance(t, dict) and t.get("planet") in _SLOW_PLANETS
        ]
    except Exception:
        state["slow_transits"] = []

    # ── noun layer (2026-06-07): translate the year's activated AREAS and the
    # slow-transit houses into the literal life-things they touch (your boss,
    # property, a loan, your father, savings...), direction-bound by whether
    # the area is under pressure. The narrator names these instead of abstract
    # areas. Internal-only houses; nouns are jargon-free.
    try:
        from antar_engine.house_significations import (
            nouns_for_domain, select_nouns,
        )
        _AREA_TO_DOMAIN = {
            "career": "career", "work": "career", "profession": "career",
            "wealth": "wealth", "money": "wealth", "finance": "wealth",
            "finances": "wealth", "health": "health", "body": "health",
            "relationship": "relationships", "relationships": "relationships",
            "love": "relationships", "family": "relationships",
            "home": "home", "property": "home",
            "learning": "learning", "education": "learning",
            "growth": "spiritual", "spiritual": "spiritual", "purpose": "spiritual",
        }
        _nouns_out, _seen = [], set()
        for a in (year.get("areas") or []):
            if not isinstance(a, dict) or not a.get("name"):
                continue
            _key = str(a.get("name")).strip().lower().split("/")[0].split(" ")[0]
            _dom = _AREA_TO_DOMAIN.get(_key)
            if not _dom:
                continue
            _dir = "adverse" if a.get("care") else "positive"
            _sig = nouns_for_domain(_dom, _dir, 3)
            for _n in (_sig.get("nouns") if _sig else []) or []:
                if _n not in _seen:
                    _seen.add(_n)
                    _nouns_out.append(_n)
            if len(_nouns_out) >= 6:
                break
        for _t in state.get("slow_transits", []):
            _h = _t.get("house")
            if isinstance(_h, int):
                for _n in select_nouns(_h, None, None, 2):
                    if _n not in _seen and len(_nouns_out) < 8:
                        _seen.add(_n)
                        _nouns_out.append(_n)
        state["concrete_nouns"] = _nouns_out[:8]
    except Exception:
        state["concrete_nouns"] = []
    return state


def build_year_narration_system(state: dict, first_name: str = "") -> str:
    payload = dict(state)
    payload["first_name"] = (first_name or "").split(" ")[0][:24]
    # [prompt-registry 2026-06-10] contract header + editable body from the
    # registry; identical '## LIVE DATA' KV-cache split as before.
    from antar_engine.prompt_registry import build_system_prompt
    return build_system_prompt("year", json.dumps(payload, ensure_ascii=False))


# ── Output validation — template fallback on ANY miss ────────────────────────

_JARGON_RX = re.compile(
    r"(?i)\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"nakshatra|dasha|mahadasha|antardasha|varshphal|muntha|tithi|"
    r"muhurta|hora|lagna|ascendant|retrograde|transit|zodiac|horoscope|"
    r"astrolog\w*|aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|"
    r"sagittarius|capricorn|aquarius|pisces|"
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


def parse_and_validate_year(raw: str, language: str = "en") -> Optional[dict]:
    """Parse Claude's JSON and enforce the contract. None = keep template."""
    obj = _extract_json(raw)
    if not obj:
        return None
    headline = (obj.get("headline") or "").strip()
    body = (obj.get("body") or "").strip()
    watch = (obj.get("watch") or "").strip()
    if not headline or not body or not watch:
        return None

    # Raw jargon leak -> reject outright (clean template beats mangled strip)
    for part in (headline, body, watch):
        if _JARGON_RX.search(part):
            return None

    # Defense-in-depth: standard strip layer, then re-check
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        headline = apply_user_facing_strips(headline, language=language,
                                            field_type="headline")
        body = apply_user_facing_strips(body, language=language,
                                        field_type="plain")
        watch = apply_user_facing_strips(watch, language=language,
                                         field_type="plain")
    except Exception:
        pass

    headline = re.sub(r"\s+", " ", headline).strip()
    body = body.strip()
    watch = re.sub(r"\s+", " ", watch).strip()

    if not (10 <= len(headline) <= 120):
        return None
    if not (200 <= len(body) <= 900):
        return None
    if not (20 <= len(watch) <= 280):
        return None
    for part in (headline, body, watch):
        if "?" in part or "!" in part:
            return None
        if _JARGON_RX.search(part):
            return None
    return {"headline": headline, "body": body, "watch": watch}


# ── DB cache (year_narration_cache) ──────────────────────────────────────────

def _fingerprint(state: dict) -> dict:
    return {
        "polarity": state.get("polarity"),
        "areas": [(a.get("name"), a.get("bars")) for a in (state.get("areas") or [])],
        "md": (state.get("long_chapter") or {}).get("lord"),
        "muntha": state.get("muntha_sign"),
    }


def _fp_key(state: dict) -> str:
    return json.dumps(_fingerprint(state), sort_keys=True, ensure_ascii=False)


def year_narration_cache_read(supabase, chart_id: str, period_start: str,
                              state: dict, language: str = "en") -> Optional[dict]:
    """Cached narration for this birthday year, IF the engine state holds."""
    try:
        res = supabase.table("year_narration_cache").select("payload") \
            .eq("chart_id", chart_id).eq("period_start", period_start) \
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
        if payload.get("_fp") != _fp_key(state):
            return None  # engine state shifted (dasha boundary etc.) — re-narrate
        if payload.get("headline") and payload.get("body") and payload.get("watch"):
            return {"headline": payload["headline"], "body": payload["body"],
                    "watch": payload["watch"]}
        return None
    except Exception as e:
        print(f"[year-narration] cache read skipped: {e}")
        return None


def year_narration_cache_write(supabase, chart_id: str, period_start: str,
                               state: dict, narration: dict,
                               language: str = "en") -> None:
    try:
        supabase.table("year_narration_cache").upsert({
            "chart_id": chart_id,
            "period_start": period_start,
            "language": language,
            "payload": {**narration, "_fp": _fp_key(state)},
        }, on_conflict="chart_id,period_start,language").execute()
    except Exception as e:
        print(f"[year-narration] cache write skipped (table missing?): {e}")
