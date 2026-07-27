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
NARRATION_STATIC = """You are the narration layer for Antar's Today card. The
prediction ENGINE has already decided what matters today — WHICH life-areas are
live for this person, which way each leans, and how strongly. You never choose
or change the topic. You narrate the engine's decision warmly and specifically.

VOICE — a wise, warm friend who can see this person's whole life and genuinely
cares how their day goes. Open with "Dear {first_name}," using the name in the
live data; if it is empty, open with "Today,". Second person throughout. Calm,
personal, concrete. Never a cold to-do list, never mystical, never hedging.

WHAT YOU WRITE:
- "headline": ONE warm, characterizing line, max 90 characters — the shape of
  the whole day, not a single task. Not a rating, not a bare warning.
- "highlight": a short, warm walk through the day. Start with the greeting, then
  give ONE short beat (1-2 sentences) for EACH entry in "drivers", strongest
  first. Finish with ONE closing line that points to the timing — the best
  window and the single move that matters most.

HARD RULES:
1. COVERAGE — narrate EVERY entry in "drivers", no more and no fewer. Each entry
   is a life-area the engine actually computed. Four drivers means four beats.
   Never merge them into one; never add a beat that isn't there.
2. NO INVENTION — you may name ONLY the life-areas present in "drivers". Never
   mention a father, mother, sibling, child, partner, network, or an expense
   unless a driver names it. If it is not in the data, it did not happen — leave
   it out. (Enforced in code: invented areas are rejected and the read is
   regenerated.)
3. GROUND each beat in its driver — use its "signal" (amplified = lean in;
   caution = ease off gently), its "reasons", and its "concrete_nouns": name one
   or two of the literal life-things it points to ("your father", "a mentor",
   "a new loan", "your partner") tied to the day. Never write the abstract
   bucket alone ("focus on work", "relationships need attention").
4. THROUGH-LINE — "through_line" is the felt texture of the chapter this person
   is living right now (e.g. "earned and real", "expansive and fortunate"). Let
   it color the whole reading and tie the beats together. Never name it as a
   thing; never say "chapter", "period", or "lord".
5. COMMIT to each area's direction. Amplified = clearly favorable, said warmly.
   Caution = clear, kind caution. Never "mixed", never a hedge.
6. Use "weighing_on_user" to speak to what this person is actually carrying;
   never name it or say "you asked about".
7. CLOSE on the timing — weave "best_window" / "best_for" into the one move to
   make today, and "avoid_window" / "avoid_what" only if a caution beat calls
   for it. This precise timing is Antar's gift; end the reading on it.
8. ZERO jargon: no planet names, no Sanskrit, no houses, no astrology terms, no
   "the energy of X", no weekday names, no dates. No questions, no emojis, no
   exclamation marks. Second person. English only.

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
    panchanga: Optional[dict] = None,
    day_frame: Optional[dict] = None,
) -> str:
    """Static block + per-day JSON tail (below the KV split)."""
    hora = engine.get("todays_move") or engine.get("hora") or {}
    lk_daily = lk_daily or {}
    panchanga = panchanga or {}
    # Panchanga texture — QUALITY words + plain month emphasis ONLY (never the
    # Sanskrit limb names; rule 6 / _JARGON_RX would reject them). Surfaces the
    # karana (second-half-of-day) quality and the month lord's plain theme.
    def _qword(q):
        q = (q or "").lower()
        # check 'inauspic' BEFORE 'auspic' — the latter is a substring of it.
        if "inauspic" in q or "caution" in q or "avoid" in q or "difficult" in q:
            return "caution"
        if "auspic" in q or "favor" in q or "favour" in q:
            return "favorable"
        return "neutral"
    payload = {
        "date": date_str,
        "first_name": (first_name or "").split(" ")[0][:24],
        "domains": engine.get("highlight_domains") or [],
        "areas": engine.get("highlight_areas") or [],
        "through_line": (engine.get("evidence") or {}).get("dasha_tone", ""),
        "direction": engine.get("direction"),
        "strength": engine.get("strength"),
        "drivers": drivers or [],
        "second_half_quality": _qword(panchanga.get("karana_quality")),
        "month_emphasis": panchanga.get("masa_theme") or "",
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
    # [prompt-registry 2026-06-10] contract header + editable body from the
    # registry; identical '## LIVE DATA' KV-cache split as before.
    from antar_engine.prompt_registry import build_system_prompt
    _sys = build_system_prompt("today", json.dumps(payload, ensure_ascii=False))
    # [frame-contract 2026-07-24] The day's binding orientation, byte-identical
    # to the block the signal call receives — see antar_engine/day_frame.py.
    # Appended AFTER build_system_prompt so it lands below the '## LIVE DATA'
    # KV split; it is per-chart and per-day and must not enter the shared
    # cached prefix. An open day appends nothing.
    try:
        from antar_engine.day_frame import frame_constraint_block
        _fb = frame_constraint_block(day_frame)
        if _fb:
            _sys = _sys + "\n\n" + _fb
    except Exception:
        pass
    return _sys


# ── driver summary: _debug_reasoning votes -> narratable conclusions ─────────

# vote source-kind -> (plain reason, ordering rank). Chart-specific reasons are
# the strongest "why", attention next, personal context last. ZERO jargon:
# these are conclusions, never the mechanism (no houses, planets, or scores).
_DRIVER_REASON = {
    "lk_amplify": ("this area is specifically lit for you today", 0),
    "lk_avoid":   ("your own pattern asks for extra care here today", 0),
    "moon_house": ("this is where your attention naturally lands today", 1),
    "patra":      ("it connects to what you're focused on right now", 2),
    "dasha":      ("this is the chapter your life is moving through right now", 0),
}


# [life-context 2026-07-13] A house is multivalent — the 5th is children AND
# creativity / romance / ventures; the 7th is a spouse AND business partners /
# deals / the public. Never assert a life fact we don't know: only surface
# "a child" or "your spouse" when the chart's own status positively supports it;
# otherwise use the house's neutral meanings. (Kulbir: children_status=
# no_children_unsure -> the 5th must read as a venture/creativity, not "a child".)
_HAS_KIDS_POS = {"has_children", "have_children", "have_kids", "has_kids",
                 "parent", "kids", "children", "yes"}
_PARTNERED_POS = {"married", "partnered", "engaged", "in_relationship",
                  "relationship", "committed", "cohabiting"}
_CHILD_WORDS = re.compile(r"(?i)\b(child|children|kid|kids|son|daughter|baby)\b")
_SPOUSE_WORDS = re.compile(r"(?i)\b(spouse|wife|husband)\b")


def _has_kids(ctx) -> bool:
    return str((ctx or {}).get("children_status") or "").strip().lower() in _HAS_KIDS_POS


def _is_partnered(ctx) -> bool:
    return str((ctx or {}).get("marital_status") or "").strip().lower() in _PARTNERED_POS


def _apply_life_context(domain, nouns, theme, ctx):
    """Drop assumed-relationship nouns the user's status doesn't support and
    reword the theme. Safe default: assume nothing unless positively known."""
    if not ctx:
        return nouns, theme
    if domain in ("children", "child") and not _has_kids(ctx):
        nouns = [n for n in nouns if not _CHILD_WORDS.search(n)] or \
                ["a creative project", "a venture or idea", "something you're making"]
        if _CHILD_WORDS.search(theme or ""):
            theme = "creativity, romance and the things you make"
    if domain in ("partner", "partnership", "marriage") and not _is_partnered(ctx):
        nouns = [n for n in nouns if not _SPOUSE_WORDS.search(n)] or \
                ["a partner or close collaborator", "a deal or agreement"]
        if _SPOUSE_WORDS.search(theme or ""):
            theme = "your partnerships and the deals you make"
    return nouns, theme


def summarize_drivers(debug: Optional[dict], chosen: Optional[list] = None,
                      context: Optional[dict] = None) -> list:
    """Turn the engine's _debug_reasoning into a per-chosen-domain driver list:
        [{"domain": "money", "signal": "amplified",
          "reasons": ["this area is specifically lit for you today", ...]}, ...]
    Reads only the structured votes (already jargon-free); never the raw LK
    text or the el_movimiento sentence (which carry mechanism/jargon).
    `context` (children_status / marital_status) gates assumed-life nouns."""
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
        elif kind.startswith("dasha"):
            key = "dasha"
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
            from antar_engine.life_areas import AREA_HOUSE as _AREA_HOUSE
            # Prefer the actually-activated house (Moon-attention vote); else
            # fall back to the fine area's own anchor house so LK-only votes
            # (e.g. father via the 9th) still resolve the right nouns.
            _hs = house_for.get(d)
            if _hs is None:
                _hs = _AREA_HOUSE.get(d)
            _direction = "positive" if signal == "amplified" else "adverse"
            _sig = resolve_signal(_hs, d, _direction, limit=3)
            nouns = _sig.get("nouns", [])
            theme = _sig.get("theme", "")
            phrase = _sig.get("phrase", "")
            # [life-context] don't name a child/spouse the user doesn't have.
            nouns, theme = _apply_life_context(d, nouns, theme, context)
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
    # [jargon-synonyms 2026-07-24] The list above names the TERMS but not their
    # SYNONYMS, and the model reaches for a synonym precisely when it senses the
    # plain term is unwelcome. A live card opened with "A rare nodal return is
    # active" — "rahu"/"ketu" would have been rejected, "nodal" sailed through.
    # Anything a reader would have to look up belongs here.
    r"nodal|nodes?|eclipse|natal|sidereal|ephemeris|jyotish|vedic|"
    r"sade\s*sati|conjunct\w*|trine|sextile|karmic|karma|"
    r"solar\s+return|lunar\s+return|equinox|solstice|planetary|planets?|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"\d{1,2}(?:st|nd|rd|th)\s+house|house\s+\d{1,2})\b"
)

# [cycle-claims 2026-07-24] "something that happens once every 18-19 years" is a
# factual astronomical claim, and the daily card is the wrong surface to make
# one: the reader cannot check it, it explains nothing about their day, and it
# was not computed — the model supplied it from its own knowledge. The
# no-invention gate below only validates LIFE AREAS, so a claim like this passed
# every check we had. The daily card talks about the reader's life, not about
# the sky's arithmetic.
_CYCLE_CLAIM_RX = re.compile(
    r"(?i)("
    r"once\s+(?:in|every)\s+[\w\s-]{0,12}?\d+\s*(?:[-–]\s*\d+\s*)?years?|"
    r"every\s+\d+\s*(?:[-–]\s*\d+\s*)?years?|"
    r"\d+\s*(?:[-–]\s*\d+\s*)?[-\s]year\s+cycle|"
    # [gate-widen 2026-07-27] compare view proved these slip through both models
    r"karmic(?:\s+(?:reset|axis|cycle|gateway|gate|window|node|lesson|theme|reckoning))?|"
    r"(?:cosmic|celestial|astral)\s+\w+"
    r")"
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


# Life-area mentions the narrator might invent. Each phrase -> the fine
# area that MUST have been voted for the prose to name it. Deliberately
# limited to the relative/network/expense nouns the model tends to
# embroider (father/mother/siblings/children/partner/network/expense);
# a false reject only falls back to the grounded engine template, so we
# err strict. Generic words (home, family, loss) are intentionally NOT
# here — only unambiguous, person-or-ledger nouns.
_AREA_MENTIONS = [
    (re.compile(r"(?i)\b(father|dad)\b"), "father"),
    (re.compile(r"(?i)\b(mother|mom|mum)\b"), "home"),
    (re.compile(r"(?i)\b(sibling|siblings|brother|sister)\b"), "siblings"),
    (re.compile(r"(?i)\b(children|kids?|daughter|son)\b"), "children"),
    (re.compile(r"(?i)\b(partner|spouse|marriage|husband|wife)\b"), "partner"),
    (re.compile(r"(?i)\b(network|friends?|allies|colleagues?)\b"), "network"),
    (re.compile(r"(?i)\b(expense|expenses|spending|overspend\w*)\b"), "expense"),
]


def ungrounded_areas(text: str, allowed: set) -> set:
    """Areas the prose names that were NOT computed (not in `allowed`)."""
    hits = set()
    for rx, area in _AREA_MENTIONS:
        if area not in allowed and rx.search(text or ""):
            hits.add(area)
    return hits


def parse_and_validate(raw: str, language: str = "en",
                       allowed_areas: Optional[set] = None) -> Optional[dict]:
    """Parse Claude's JSON and enforce the contract. None = use the template.
    When allowed_areas is given, the no-invention gate rejects any prose that
    names a life-area no source voted for."""
    obj = _extract_json(raw)
    if not obj:
        return None
    headline = (obj.get("headline") or "").strip()
    highlight = (obj.get("highlight") or "").strip()
    if not headline or not highlight:
        return None

    # Reject RAW jargon leaks outright — a strip-rewritten sentence reads
    # mangled; the engine's clean template is the better fallback.
    _jm = _JARGON_RX.search(headline) or _JARGON_RX.search(highlight)
    if _jm:
        print(f"[today-narration] jargon gate rejected {_jm.group(0)!r} (pre-strip)")
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
    if not (80 <= len(highlight) <= 1300):
        return None
    if "?" in headline or "?" in highlight:
        return None
    if "!" in headline or "!" in highlight:
        return None
    _jm = _JARGON_RX.search(headline) or _JARGON_RX.search(highlight)
    if _jm:
        print(f"[today-narration] jargon gate rejected {_jm.group(0)!r} (post-strip)")
        return None
    _cm = _CYCLE_CLAIM_RX.search(headline) or _CYCLE_CLAIM_RX.search(highlight)
    if _cm:
        print(f"[today-narration] cycle-claim gate rejected {_cm.group(0)!r}")
        return None
    # [Fix C] no-invention gate — the model may only speak to computed votes.
    if allowed_areas is not None:
        _bad = ungrounded_areas(headline + " " + highlight, set(allowed_areas))
        if _bad:
            print(f"[today-narration] no-invention gate rejected "
                  f"{sorted(_bad)} (allowed={sorted(allowed_areas)})")
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
