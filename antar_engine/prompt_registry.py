"""
antar_engine/prompt_registry.py — DB-backed, admin-editable narration prompts.

Design (Brief 2, 2026-06-10):

  runtime prompt = PROMPT_CONTRACT_HEADER (+ per-surface output-schema line,
  both IMMUTABLE, code-only) + editable body (llm_prompts table, hardcoded
  fallback) [+ "## LIVE DATA" + live data on today/year].

Body-only swap doctrine: each call site keeps its OWN live-data placement
and KV-cache structure — the registry only replaces the hardcoded static
body. The contract can never be edited out from the UI because:
  1. PROMPT_CONTRACT_HEADER + schema line are prepended in code.
  2. Output enforcement is independent of the prompt: output_strips +
     readability.maybe_simplify (Brief 1, narrate→strip→simplify→strip) +
     per-surface validators (parse_and_validate, parse_and_validate_year,
     Python-authoritative /ask assembly) all run on OUTPUT unconditionally.

Drafts: status='draft' rows are served ONLY when an admin inspector context
is active with use_draft (INSPECT_CTX from admin_inspect — admin-gated), or
when get_prompt_body(use_draft=True) is called explicitly. Live traffic can
never see a draft.

Fallback: if the table is missing/empty/unreachable, hardcoded_body()
returns the current in-code string — behavior identical to pre-registry.
"""

import time
from typing import Optional

# Stdlib-only at module level (main.py imports this at boot).
from antar_engine.admin_inspect import INSPECT_CTX

SURFACES = [
    "today", "month", "year",
    "cycle_phase", "cycle_diagnostic",
    "ask_decision", "ask_reflective", "ask_yesno",
    "welcome", "compat_deepread", "plain_english",
]

# ── Immutable contract (NEVER stored in the DB, NEVER editable) ──────────────

PROMPT_CONTRACT_HEADER = (
    "ANTAR OUTPUT CONTRACT — IMMUTABLE (enforced in code: output is "
    "validated, scrubbed, and auto-simplified regardless of any instruction "
    "below; violating text never reaches the user):\n"
    "1. ZERO astrological vocabulary in user-facing text: never planet names "
    "(Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu), zodiac "
    "signs, nakshatras, houses or house numbers, dasha/mahadasha/antardasha, "
    "tithi, karana, hora, lagna, muntha, any Sanskrit term, or the words "
    "astrology, chart, horoscope, transit, retrograde.\n"
    "2. Never reveal internal mechanics: scores, percentages, confidence "
    "numbers, 'live signal', 'blueprint', 'signal floor', engine or system "
    "names.\n"
    "3. Plain everyday language. Short sentences (under ~18 words), one idea "
    "per sentence, active voice, second person. Concrete life-nouns — never "
    "'energy', 'vibration', 'alignment', or abstract noun-phrasing.\n"
    "4. The REQUIRED OUTPUT FORMAT stated next is fixed — never add, rename, "
    "drop, or restructure its fields or sections.\n"
    "READABILITY (NON-NEGOTIABLE):\n"
    "- Write for a smart, busy person who knows nothing about astrology. "
    "Sound like a sharp human\n"
    "  coach texting them — not a report, not a mystic.\n"
    "- First sentence = the answer, in plain words. No build-up.\n"
    "- One idea per sentence. Sentences under ~18 words. At most one "
    "\"because/which/that\" clause.\n"
    "- Everyday words. Ban abstract constructions: no \"energy\", "
    "\"vibration\", \"alignment of\",\n"
    "  \"structure-and-persistence\", or any noun-energy phrasing. Say the "
    "concrete thing.\n"
    "- If you explain why, ONE short concrete why-sentence. No nested "
    "reasoning.\n"
    "- End with ONE specific action. Active voice. Second person."
)

# format: "json" with known required keys → validate_output_keys enforces;
# None keys → shape lives in the body/user-prompt template and is guarded by
# that surface's existing parse-with-fallback.
SURFACE_SCHEMAS = {
    "today":            {"format": "json",  "required": ["headline", "highlight"]},
    "month":            {"format": "json",  "required": None},
    "year":             {"format": "json",  "required": ["headline", "body", "watch"]},
    "cycle_phase":      {"format": "prose", "required": None},
    "cycle_diagnostic": {"format": "json",  "required": ["current_stuckness_sources",
                                                         "what_to_lean_into",
                                                         "what_to_avoid",
                                                         "next_phase_shift"]},
    "ask_decision":     {"format": "json",  "required": ["read", "verdict", "timing",
                                                         "actions", "next"]},
    "ask_reflective":   {"format": "json",  "required": ["read", "next"]},
    "ask_yesno":        {"format": "json",  "required": ["why", "actions"]},
    "welcome":          {"format": "prose", "required": None},
    "compat_deepread":  {"format": "json",  "required": None},
    "plain_english":    {"format": "json",  "required": None},
}


# ── [schema-hoist 2026-06-10] Output-format templates are LOCKED in code ─────
# The field template each frontend pane renders lives HERE (immutable), not
# in the editable body. month/plain_english templates are lifted verbatim
# from the hardcoded constants (code = source of truth); the rest are static.

_MONTH_TEMPLATE_MARKERS = {
    "en": "Return ONLY this JSON:",
    "es": "Devuelve SOLO este JSON:",
    "pt": "Retorne APENAS este JSON:",
}
_PE_TEMPLATE_MARKER = "RETURN THIS EXACT JSON STRUCTURE:"

_STATIC_OUTPUT_TEMPLATES = {
    "today": ('Output STRICT JSON and nothing else: '
              '{"headline": "...", "highlight": "..."}'),
    "year": ('Output STRICT JSON and nothing else: '
             '{"headline": "...", "body": "...", "watch": "..."}'),
    "ask_decision": ('Reply with STRICT JSON only: '
                     '{"read": "...", "verdict": "...", "timing": "...", '
                     '"actions": ["...", "..."], "next": "..."}'),
    "ask_reflective": ('Reply with STRICT JSON only: '
                       '{"read": "...", "next": "..."}'),
    "ask_yesno": ('Reply with STRICT JSON only: '
                  '{"why": "...", "actions": ["...", "..."]}'),
    "cycle_diagnostic": ("Output valid JSON only, with fields exactly as "
                         "specified in the task instructions."),
    "compat_deepread": ("Output strict JSON only, with fields exactly as "
                        "specified in the task instructions."),
}

# Substrings removed from the EDITABLE body (idempotent; exact text of the
# template as it appears inside each legacy prompt constant).
_BODY_TEMPLATE_STRIPS = {
    "today": ['9. Output STRICT JSON and nothing else: '
              '{"headline": "...", "highlight": "..."}\n'],
    "year": ['9. Output STRICT JSON and nothing else:\n'
             '   {"headline": "...", "body": "...", "watch": "..."}\n'],
    "ask_decision": ['reply with STRICT JSON only: '
                     '{"read": "...", "verdict": "...", "timing": "...", '
                     '"actions": ["...", "..."], "next": "..."}. '],
    "ask_yesno": ['Reply with STRICT JSON only: '
                  '{"why": "...", "actions": ["...", "..."]}. '],
    "cycle_diagnostic": ["Output valid JSON only. "],
    "compat_deepread": [" Output strict JSON only."],
}


def _output_template(surface: str, language: str = "en"):
    """The locked, per-surface (and for month, per-language) output template."""
    if surface == "month":
        lang = _norm_lang(language)
        try:
            from antar_engine.monthly_deepdive import (
                MONTHLY_SYSTEM_PROMPT, MONTHLY_SYSTEM_PROMPT_ES,
                MONTHLY_SYSTEM_PROMPT_PT,
            )
            full = {"en": MONTHLY_SYSTEM_PROMPT, "es": MONTHLY_SYSTEM_PROMPT_ES,
                    "pt": MONTHLY_SYSTEM_PROMPT_PT}[lang]
            marker = _MONTH_TEMPLATE_MARKERS[lang]
            if marker in full:
                return marker + full.split(marker, 1)[1]
        except Exception:
            pass
        return ("Return ONLY the exact JSON structure the monthly surface "
                "renders — never add, rename, or drop fields.")
    if surface == "plain_english":
        try:
            from antar_engine.plain_english import PLAIN_ENGLISH_SYSTEM_PROMPT
            if _PE_TEMPLATE_MARKER in PLAIN_ENGLISH_SYSTEM_PROMPT:
                return (_PE_TEMPLATE_MARKER
                        + PLAIN_ENGLISH_SYSTEM_PROMPT.split(_PE_TEMPLATE_MARKER, 1)[1])
        except Exception:
            pass
        return ("Return ONLY the exact JSON structure the plain-english "
                "surface renders — never add, rename, or drop fields.")
    return _STATIC_OUTPUT_TEMPLATES.get(surface)


def strip_output_template(surface: str, language: str, text: str) -> str:
    """Remove the output template from an editable body (idempotent). Used
    by the hardcoded fallbacks AND the seed migration, so body never
    duplicates what the locked header already states."""
    if not isinstance(text, str):
        return text
    if surface == "month":
        marker = _MONTH_TEMPLATE_MARKERS.get(_norm_lang(language),
                                             _MONTH_TEMPLATE_MARKERS["en"])
        return text.split(marker, 1)[0].rstrip()
    if surface == "plain_english":
        return text.split(_PE_TEMPLATE_MARKER, 1)[0].rstrip()
    out = text
    for frag in _BODY_TEMPLATE_STRIPS.get(surface, []):
        out = out.replace(frag, "")
    return out


def _schema_line(surface: str, language: str = "en") -> str:
    tmpl = _output_template(surface, language)
    if tmpl:
        return ("REQUIRED OUTPUT (locked — not editable from the console):\n"
                + tmpl)
    sch = SURFACE_SCHEMAS.get(surface) or {}
    req = sch.get("required")
    if sch.get("format") == "json" and req:
        return ("REQUIRED OUTPUT: STRICT JSON with exactly these keys: "
                + ", ".join(f'"{k}"' for k in req) + ".")
    if sch.get("format") == "json":
        return ("REQUIRED OUTPUT: STRICT JSON exactly matching the field "
                "template given in the instructions below.")
    return ("REQUIRED OUTPUT: flowing prose exactly as specified in the "
            "instructions below — no JSON, no headings, no lists.")


def validate_output_keys(surface: str, obj) -> list:
    """Missing required keys for a JSON surface ([] when valid/not applicable)."""
    sch = SURFACE_SCHEMAS.get(surface) or {}
    req = sch.get("required")
    if sch.get("format") != "json" or not req:
        return []
    if not isinstance(obj, dict):
        return list(req)
    return [k for k in req if k not in obj or obj.get(k) in (None, "")]


# ── Hardcoded fallbacks (the pre-registry in-code strings) ───────────────────
# today/month/year/plain_english/welcome resolve lazily from their modules so
# the fallback always tracks the source constant. The inline-literal surfaces
# (ask_*, cycle_*, compat) are duplicated here verbatim; after the seed
# migration the DB is the source of truth and these are fallback-only.

_ASK_DECISION_FALLBACK = (
    "You are Antar, a grounded life coach. The user asked a timing/decision "
    "question. Using ONLY the consultation facts and chart context below, "
    "FIXED FACTS (absolute, override anything below): "
    "(1) Never state internal scores, percentages, confidence numbers, "
    "'live signal', 'blueprint', or 'signal floor' — describe room or "
    "constraint in plain words only. "
    "(2) Never use planet-trait nouns as the actor — 'discipline blocking X' "
    "becomes 'caution holding X back'. "
    "(3) Read carries AT MOST 3 threads — the 2-3 the chart most supports. "
    "READABILITY (NON-NEGOTIABLE): write for a smart, busy person who "
    "knows nothing about astrology — a sharp human coach texting them, "
    "not a report. First sentence = the answer in plain words, no "
    "build-up. One idea per sentence; sentences under 18 words; never "
    "stack clauses. Everyday words only — never 'energy', 'vibration', "
    "'alignment', or any noun-energy phrasing; say the concrete thing. "
    "At most ONE short, concrete why-sentence. Active voice, second "
    "person. read + next together stay UNDER 90 words. "
    "reply with STRICT JSON only: "
    '{"read": "...", "verdict": "...", "timing": "...", "actions": ["...", "..."], "next": "..."}. '
    "read = 2 to 3 sentences explaining WHY the verdict is what it is. "
    "DO NOT repeat the OPENING SENTENCE from the consultation facts. "
    "DO NOT name the verdict word (Likely / Yes / Not yet / No). "
    "DO NOT name any month, year, quarter, or specific date — those live "
    "in the OPENING SENTENCE Python writes for you. "
    "Start `read` directly with the reasoning (e.g. \"The dasha and annual chart agree, and the structure of your blueprint supports execution now.\"). "
    "verdict = one of YES, LIKELY, NOT_YET, NO (must match the VERDICT pinned in the facts). "
    "timing = the TIMING WINDOW from the consultation facts restated plainly — "
    "NEVER invent dates; if the facts say no window, describe a building phase. "
    "actions = 2 or 3 concrete moves tied to the chart signals that raise the "
    "odds. next = the single most important action this week. "
    "Never mention astrology, planets, houses, signs, nakshatras, dashas, "
    "scores, or any Sanskrit or technical term — plain everyday language only. "
)

_ASK_REFLECTIVE_FALLBACK = (
    "You are Antar, a grounded life coach. The user asked an open question for which "
    "the chart has NO specific timing prediction (no engine-computed verdict, no "
    "date window). Your job: name the dynamic CONCRETELY using real life-nouns the "
    "user recognises — never abstract energy-prose. "
    "FIXED FACTS (absolute, override anything below): "
    "(1) Never state internal scores, percentages, confidence numbers, "
    "'live signal', 'blueprint', or 'signal floor' — describe room or "
    "constraint in plain words only. "
    "(2) Never use planet-trait nouns as the actor — 'discipline blocking X' "
    "becomes 'caution holding X back'; 'authority pulling' becomes 'a senior "
    "call pulling'. Restate as the plain constraint, not the planet's trait. "
    "(3) Read must carry AT MOST 3 threads, not 5. Pick the 2-3 the chart "
    "most supports and drop the rest. "
    "READABILITY (NON-NEGOTIABLE): write for a smart, busy person who "
    "knows nothing about astrology — a sharp human coach texting them, "
    "not a report. First sentence = the answer in plain words, no "
    "build-up. One idea per sentence; sentences under 18 words; never "
    "stack clauses. Everyday words only — never 'energy', 'vibration', "
    "'alignment', or any noun-energy phrasing; say the concrete thing. "
    "At most ONE short, concrete why-sentence. Active voice, second "
    "person. read + next together stay UNDER 90 words. "
)

_ASK_YESNO_FALLBACK = (
    "You are Antar. The user asked a yes/no question. Reply with STRICT JSON only: "
    '{"why": "...", "actions": ["...", "..."]}. '
    "READABILITY (NON-NEGOTIABLE): why = ONE short sentence, under 18 "
    "words, everyday words — never 'energy', 'vibration', or abstract "
    "noun-phrasing. actions = plain verb-first moves, under 15 words "
    "each, naming the concrete thing to do. "
)

_CYCLE_PHASE_FALLBACK = (
    "You are Antar's life phase analyst. Write precise, warm, specific "
    "summaries. No jargon. No lists. One flowing paragraph. Short sentences "
    "— under 18 words each. Everyday words; never the word 'energy' or "
    "abstract noun-phrases. First sentence states the point."
)

_CYCLE_DIAGNOSTIC_FALLBACK = (
    "You are Antar's diagnostic engine. Output valid JSON only. "
    "Be specific, warm, and actionable. ZERO jargon — no planet "
    "names, no houses, no Sanskrit, no astrology terms. Every "
    "stuckness source must be a verdict-first directive about a "
    "life domain, never a dasha label."
)

_COMPAT_DEEPREAD_FALLBACK = (
    "You write concise, jargon-free relationship guidance. Short sentences, "
    "everyday words, no abstract 'energy' phrasing. Output strict JSON only."
)


def _fb_today() -> str:
    from antar_engine.today_narration import NARRATION_STATIC
    return NARRATION_STATIC.split("## LIVE DATA")[0].rstrip()


def _fb_year() -> str:
    from antar_engine.year_narration import YEAR_NARRATION_STATIC
    return YEAR_NARRATION_STATIC.split("## LIVE DATA")[0].rstrip()


def _fb_month() -> str:
    from antar_engine.monthly_deepdive import MONTHLY_SYSTEM_PROMPT
    return MONTHLY_SYSTEM_PROMPT


def _fb_plain_english() -> str:
    from antar_engine.plain_english import PLAIN_ENGLISH_SYSTEM_PROMPT
    return PLAIN_ENGLISH_SYSTEM_PROMPT


def _fb_welcome() -> str:
    # Template with {label} and {lang_rule} placeholders — the welcome call
    # site .format()s them (and falls back to this constant if a DB body has
    # broken placeholders).
    from antar_engine.onboarding_welcome import WELCOME_RULES_TEMPLATE
    return WELCOME_RULES_TEMPLATE


_FALLBACK_RESOLVERS = {
    "today": _fb_today,
    "month": _fb_month,
    "year": _fb_year,
    "cycle_phase": lambda: _CYCLE_PHASE_FALLBACK,
    "cycle_diagnostic": lambda: _CYCLE_DIAGNOSTIC_FALLBACK,
    "ask_decision": lambda: _ASK_DECISION_FALLBACK,
    "ask_reflective": lambda: _ASK_REFLECTIVE_FALLBACK,
    "ask_yesno": lambda: _ASK_YESNO_FALLBACK,
    "welcome": _fb_welcome,
    "compat_deepread": lambda: _COMPAT_DEEPREAD_FALLBACK,
    "plain_english": _fb_plain_english,
}

_fb_cache: dict = {}


def hardcoded_body(surface: str) -> str:
    # [schema-hoist 2026-06-10] fallback bodies are template-stripped — the
    # output template lives only in the locked header (_schema_line).
    if surface not in _fb_cache:
        _fb_cache[surface] = strip_output_template(
            surface, "en", _FALLBACK_RESOLVERS[surface]())
    return _fb_cache[surface]


# ── Runtime read (TTL-cached live rows; fallback on ANY problem) ─────────────

_LIVE_TTL_SECS = 60
_live_cache: dict = {}  # surface -> (body | None, expires_monotonic)


def _sb():
    """Supabase client — the app's global when inside the API process,
    else a fresh client from env (scripts)."""
    try:
        import main as _m
        if getattr(_m, "supabase", None) is not None:
            return _m.supabase
    except Exception:
        pass
    import os
    from supabase import create_client
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY"),
    )


def invalidate(surface: Optional[str] = None) -> None:
    if surface is None:
        _live_cache.clear()
    else:
        for k in [k for k in _live_cache if k[0] == surface]:
            _live_cache.pop(k, None)


def _norm_lang(language: Optional[str]) -> str:
    lang = (language or "en").split("-")[0].lower()
    return lang if lang in ("en", "es", "pt") else "en"


def _db_body(surface: str, status: str, language: str = "en") -> Optional[str]:
    r = (
        _sb().table("llm_prompts")
        .select("body")
        .eq("surface", surface)
        .eq("status", status)
        .eq("language", language)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    if r.data:
        b = r.data[0].get("body")
        if isinstance(b, str) and b.strip():
            return b
    return None


def _hardcoded_for(surface: str, language: str) -> str:
    """Language-aware hardcoded fallback. Only month ships non-EN bodies;
    every other surface falls back to its EN string."""
    if language != "en" and surface == "month":
        from antar_engine.monthly_deepdive import (
            MONTHLY_SYSTEM_PROMPT_ES, MONTHLY_SYSTEM_PROMPT_PT,
        )
        raw = MONTHLY_SYSTEM_PROMPT_ES if language == "es" else MONTHLY_SYSTEM_PROMPT_PT
        return strip_output_template("month", language, raw)
    return hardcoded_body(surface)


def get_prompt_body(surface: str, use_draft: Optional[bool] = None,
                    language: str = "en") -> str:
    """
    Editable prompt body for a surface+language. DB row wins; hardcoded
    string is the fallback (non-EN falls back to its hardcoded variant where
    one exists — month — else to the EN chain). use_draft=None resolves from
    the admin inspector context (INSPECT_CTX) — live traffic never carries
    that context, so drafts can never leak to users.
    """
    if surface not in SURFACES:
        raise KeyError(f"unknown prompt surface: {surface}")
    language = _norm_lang(language)

    if use_draft is None:
        _ctx = INSPECT_CTX.get()
        use_draft = bool(_ctx.get("use_draft")) if isinstance(_ctx, dict) else False

    if use_draft:
        try:
            b = _db_body(surface, "draft", language)
            if b is not None:
                return b
        except Exception as e:
            print(f"[prompt-registry] draft read failed for {surface}/{language} (non-fatal): {e}")
        # no draft → preview equals live
        return get_prompt_body(surface, use_draft=False, language=language)

    now = time.monotonic()
    key = (surface, language)
    hit = _live_cache.get(key)
    if hit and hit[1] > now:
        return hit[0] if hit[0] is not None else _hardcoded_for(surface, language)

    body = None
    try:
        body = _db_body(surface, "live", language)
    except Exception as e:
        print(f"[prompt-registry] live read failed for {surface}/{language} (fallback): {e}")
    _live_cache[key] = (body, now + _LIVE_TTL_SECS)
    return body if body is not None else _hardcoded_for(surface, language)


def get_system_prefix(surface: str, use_draft: Optional[bool] = None,
                      language: str = "en") -> str:
    """Immutable contract header + locked output template + editable body.
    [schema-hoist 2026-06-10] the body is template-stripped defensively so a
    DB row can never duplicate or contradict the locked template."""
    return (
        PROMPT_CONTRACT_HEADER + "\n" + _schema_line(surface, language) + "\n\n"
        + strip_output_template(surface, language,
                                get_prompt_body(surface, use_draft, language=language))
    )


def build_system_prompt(surface: str, live_data: str,
                        use_draft: Optional[bool] = None,
                        language: str = "en") -> str:
    """today/year shape: prefix above the '## LIVE DATA' KV-cache split,
    live data below it (call_llm_claude splits on the marker)."""
    body = get_system_prefix(surface, use_draft, language=language)
    # A DB body must never smuggle its own split marker.
    body = body.split("## LIVE DATA")[0].rstrip()
    return body + "\n## LIVE DATA\n" + (live_data or "")
