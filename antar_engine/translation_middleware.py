"""
antar_engine/translation_middleware.py

Loc-4 — LLM translation middleware.

The @translate_response decorator runs an endpoint's English response through
Claude Haiku for es/pt, cached per (endpoint, chart, language, content_hash).
English requests are an untouched passthrough (zero added latency/cost).

Three deliberate deviations from the Loc-4 brief (the brief's versions were
buggy for the actual Cluster F response shapes):

  1. content_hash is computed over the EXTRACTED translatable strings, not
     the whole response. Several Cluster F responses carry volatile fields
     (e.g. /remedies returns `generated_at`), so hashing the whole dict would
     produce a new hash on every call and the cache would NEVER hit —
     defeating the entire sprint. Hashing the translatable strings keeps the
     key stable.

  2. On a cache HIT the cached translated strings are re-applied onto the
     freshly-built response, so volatile metadata (generated_at, etc.) stays
     current rather than frozen at first-translation time.

  3. _extract_translatable applies `fields_to_translate` at the LEAF and
     always recurses into containers. The brief `continue`d past any dict key
     not in the allowlist — which skips the whole subtree, so a nested
     response like /remedies ({"remedies": [{"why": ...}]}) would translate
     nothing because the `remedies` container key isn't in the allowlist.

Clients (Supabase, Anthropic) are created lazily so importing this module
can never fail at startup.
"""
from antar_engine.constants import HAIKU_MODEL

import hashlib
import json
import re
import logging
import os
from functools import wraps

from antar_engine.translation_cache import get_cached_translation, save_translation
from antar_engine.translation_glossary import build_translation_system_prompt

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ("es", "pt", "fr")
TRANSLATOR_MODEL = HAIKU_MODEL

# Keys never sent to the translator — IDs, metadata, enums, volatile fields,
# and Sanskrit chart terms that must be preserved verbatim.
GLOBAL_SKIP_FIELDS = {
    "chart_id", "id", "uuid", "created_at", "updated_at", "timestamp",
    "generated_at", "_translation_status", "language", "score", "rating",
    "count", "latitude", "longitude", "url", "image_url", "icon", "color",
    "lagna", "rasi", "nakshatra",
    # [sig-hotfix 2026-07-04] Antar structural enums — frontends switch
    # on these values / cross-reference them against count-dict keys
    # (dominant_mode vs mode_counts). Never translate, on any surface.
    "mode", "match_level", "dominant_mode", "dominant_field",
    "verdict", "tier", "band", "scope", "practice_scope",
}

_anthropic_client = None

# [selection-wins 2026-07-26] Founder rule: the language is WHATEVER THE USER
# SELECTED — the decorator must never override the requested language with a
# stored preference. This set is now EMPTY: a requested 'en' means the user
# wants English and /home serves English. (Was {"home"}, which flipped a
# requested 'en' to a stored 'es' and made an explicit English toggle
# impossible — the exact confusion this rule removes.) The _stored_language_pref
# lookup below is retained only for a genuinely-absent language, and with an
# empty set it is currently unused; kept so a future no-language fallback can
# use it without re-adding the override behaviour.
LANG_RESCUE_SURFACES: set = set()

# chart_id -> (expires_at, preference). A preference changes roughly once in a
# user's lifetime, and this lookup sits on the bare-'en' path of every request
# to a rescued surface, so memoize it rather than hitting the DB each time.
_LANG_PREF_MEMO = {}
_LANG_PREF_TTL = 300.0


def _stored_language_pref(chart_id):
    """Return the chart's explicit language preference, or '' if none/unknown.

    Any failure is treated as 'no preference' — a language lookup must never be
    able to break a response.
    """
    if not chart_id:
        return ""
    import time as _t
    _hit = _LANG_PREF_MEMO.get(chart_id)
    if _hit and _hit[0] > _t.time():
        return _hit[1]
    try:
        from antar_engine.translation_cache import _get_supabase
        r = (_get_supabase().table("charts").select("language_preference")
             .eq("id", chart_id).limit(1).execute())
        pref = ((r.data[0].get("language_preference") or "").strip().lower()
                if r.data else "")
    except Exception as e:
        logger.warning(f"[lang-safety] preference lookup failed for "
                       f"{str(chart_id)[:8]}: {e}")
        return ""
    _LANG_PREF_MEMO[chart_id] = (_t.time() + _LANG_PREF_TTL, pref)
    return pref

# Lightweight per-process cache metrics, keyed by (endpoint_name, language).
# Resets on each deploy; with `--workers 4` each worker keeps its own copy, so
# treat the rolling rate as a rough real-time signal. The translation_cache
# table (created_at / last_accessed_at) is the durable source of truth.
_CACHE_METRICS = {}


def _get_anthropic():
    """Lazily create the AsyncAnthropic client. Reused across calls."""
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        try:
            from antar_engine.llm_log import wrap_claude_client as _wcc
            _anthropic_client = _wcc(_anthropic_client)
        except Exception:
            pass
    return _anthropic_client


def compute_content_hash(translatable: dict) -> str:
    """
    Stable cache key for a set of extracted translatable strings.

    Hashes ONLY the {path: english_string} pairs from _extract_translatable —
    never the full response — so volatile metadata (generated_at, timestamps)
    can never bust the cache. The JSON is fully canonicalised:
      * sort_keys=True       — key insertion order is irrelevant
      * separators=(",",":") — no incidental whitespace, fixed regardless of
                               any future json default change
      * ensure_ascii=False   — accented text serialised consistently as UTF-8
      * default=str          — defensive; translatable is already all-strings
    So two requests with identical translatable content always produce an
    identical hash and resolve to the same translation_cache row.
    """
    canonical = json.dumps(
        translatable,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _record_cache_event(endpoint_name, language, chart_id, content_hash, hit, n_strings=0):
    """
    Record a translation-cache hit/miss and emit one structured, greppable log
    line carrying all three dimensions: endpoint_name, language, chart_id
    (plus content_hash and a rolling per-(endpoint,language) hit rate).

    Verify caching effectiveness in production from the logs, e.g.:
        grep '[translation] cache=' <logs>
        grep 'cache=HIT'  <logs> | wc -l   vs   grep 'cache=MISS' <logs> | wc -l
        grep 'endpoint=remedies lang=es'   <logs>
    """
    counts = _CACHE_METRICS.setdefault((endpoint_name, language), {"hit": 0, "miss": 0})
    counts["hit" if hit else "miss"] += 1
    total = counts["hit"] + counts["miss"]
    rate = (counts["hit"] / total * 100.0) if total else 0.0
    logger.info(
        f"[translation] cache={'HIT' if hit else 'MISS'} "
        f"endpoint={endpoint_name} lang={language} "
        f"chart={(chart_id or 'none')[:8]} hash={content_hash} strings={n_strings} "
        f"rolling_hit_rate[{endpoint_name}/{language}]={counts['hit']}/{total} ({rate:.0f}%)"
    )


def get_cache_metrics() -> dict:
    """Snapshot of this worker's cache hit/miss counters, keyed 'endpoint/language'."""
    return {
        f"{ep}/{lang}": {**c, "hit_rate": round(c["hit"] / (c["hit"] + c["miss"]), 3)}
        for (ep, lang), c in _CACHE_METRICS.items()
        if (c["hit"] + c["miss"]) > 0
    }


def translate_response(fields_to_translate=None, fields_to_skip=None, endpoint_name=None):
    """
    Decorator that translates user-facing fields in an endpoint response.

    Args:
        fields_to_translate: allowlist of dict keys to translate (matched at any
            depth). If None, every string value is translated except those in
            the skip set.
        fields_to_skip: extra keys to never translate (added to GLOBAL_SKIP_FIELDS).
        endpoint_name: cache-key label (defaults to the function name).

    The decorated endpoint MUST accept a `language: str = "en"` parameter.
    English / unsupported languages are returned untouched.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            language = (kwargs.get("language") or "en").split("-")[0].lower()
            # [pt-gate] per-surface PT readiness: serve EN on surfaces not yet
            # verified clean in Portuguese. kwargs["language"] is overwritten so
            # the endpoint body and this decorator agree on the served language
            # (body generates + caches in the gated language; no mixed output).
            try:
                from antar_engine.pt_readiness import gate_language as _ptg
                language = _ptg(endpoint_name or func.__name__, language)
                if isinstance(kwargs.get("language"), str):
                    kwargs["language"] = language
            except Exception:
                pass
            # [lang-safety 2026-07-24] 'en' is the ambiguous DEFAULT an unresolved
            # client sends (stale localStorage, a signup that never synced); a
            # stored non-English preference is an explicit choice. Honor the
            # preference over a bare 'en' on opted-in surfaces only.
            #
            # This has to live here rather than in the endpoint body: `language`
            # is captured above and used for the translate_dict pass below, so a
            # body-local reassignment would compose in the resolved language and
            # then translate against the original one. kwargs is rewritten too,
            # for the same body/decorator agreement the pt-gate needs.
            _surface = endpoint_name or func.__name__
            if language == "en" and _surface in LANG_RESCUE_SURFACES:
                try:
                    _pref = _stored_language_pref(kwargs.get("chart_id"))
                    if _pref and _pref != "en":
                        from antar_engine.pt_readiness import gate_language as _ptg
                        _pref = _ptg(_surface, _pref)
                        if _pref != "en":
                            logger.info(f"[lang-safety] {_surface}: request 'en' "
                                        f"overridden to stored preference '{_pref}'")
                            language = _pref
                            if isinstance(kwargs.get("language"), str):
                                kwargs["language"] = language
                except Exception as _le:
                    logger.warning(f"[lang-safety] {_surface} rescue skipped: {_le}")
            response = await func(*args, **kwargs)
            if language not in SUPPORTED_LANGUAGES:
                return response
            # [loc-4 clusterF] Unwrap a Pydantic response_model object
            # (ChakraResponse, ProofPointsResponse, ...) into a plain dict so
            # its user-facing strings can be translated. FastAPI re-coerces the
            # returned dict back through the route's response_model on the way
            # out. The English passthrough above is left untouched.
            if not isinstance(response, (dict, list)):
                _dump = getattr(response, "model_dump", None) or getattr(response, "dict", None)
                if callable(_dump):
                    try:
                        response = _dump()
                    except Exception:
                        return response
            if not response or not isinstance(response, (dict, list)):
                return response
            try:
                return await translate_dict(
                    response,
                    language=language,
                    fields_to_translate=fields_to_translate,
                    fields_to_skip=fields_to_skip,
                    endpoint_name=endpoint_name or func.__name__,
                    chart_id=kwargs.get("chart_id"),
                )
            except Exception as e:
                logger.warning(
                    f"[translation] {endpoint_name or func.__name__} failed, "
                    f"serving English: {e}"
                )
                if isinstance(response, dict):
                    response["_translation_status"] = "fallback_to_english"
                return response

        return wrapper

    return decorator


async def translate_dict(
    data,
    language,
    fields_to_translate=None,
    fields_to_skip=None,
    endpoint_name="unknown",
    chart_id=None,
):
    """Translate user-facing strings in `data`, caching per content_hash."""
    skip_set = GLOBAL_SKIP_FIELDS | set(fields_to_skip or [])
    translatable = _extract_translatable(data, fields_to_translate, skip_set)
    if not translatable:
        return data

    # Stable cache key over the extracted strings only — see compute_content_hash.
    content_hash = compute_content_hash(translatable)

    cached = await get_cached_translation(
        endpoint_name=endpoint_name, chart_id=chart_id,
        language=language, content_hash=content_hash,
    )
    if cached:
        _record_cache_event(endpoint_name, language, chart_id, content_hash,
                            hit=True, n_strings=len(translatable))
        # Re-apply onto the current response so metadata stays fresh (deviation #2).
        return _apply_translations(data, cached, skip_set)

    _record_cache_event(endpoint_name, language, chart_id, content_hash,
                        hit=False, n_strings=len(translatable))
    translated = await _call_translator(translatable, language)

    await save_translation(
        endpoint_name=endpoint_name, chart_id=chart_id,
        language=language, content_hash=content_hash, translated_data=translated,
    )
    return _apply_translations(data, translated, skip_set)


def _extract_translatable(data, allowlist, skip_set, path=""):
    """
    Walk `data` and collect translatable string values as {path: english}.

    `allowlist` is applied at the LEAF: a string is collected if there is no
    allowlist, its key is in the allowlist, or it sits in a subtree whose key
    was allowlisted. Containers are always recursed into. (Deviation #3.)
    """
    out = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if key in skip_set:
                continue
            new_path = f"{path}.{key}" if path else key
            if isinstance(value, str):
                if len(value.strip()) > 2 and (not allowlist or key in allowlist):
                    out[new_path] = value
            elif isinstance(value, (dict, list)):
                # An allowlisted container makes its whole subtree translatable.
                child_allowlist = None if (allowlist and key in allowlist) else allowlist
                out.update(_extract_translatable(value, child_allowlist, skip_set, new_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_path = f"{path}[{i}]"
            if isinstance(item, str):
                # Bare list strings have no key — collect only when unconstrained
                # (an allowlisted parent passes allowlist=None down to here).
                if len(item.strip()) > 2 and not allowlist:
                    out[new_path] = item
            elif isinstance(item, (dict, list)):
                out.update(_extract_translatable(item, allowlist, skip_set, new_path))
    return out


def _apply_translations(data, translations, skip_set, path=""):
    """Walk `data` and replace strings whose path is in `translations`."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            if key in skip_set:
                result[key] = value
            elif isinstance(value, str) and new_path in translations:
                result[key] = translations[new_path]
            elif isinstance(value, (dict, list)):
                result[key] = _apply_translations(value, translations, skip_set, new_path)
            else:
                result[key] = value
        return result
    if isinstance(data, list):
        result = []
        for i, item in enumerate(data):
            new_path = f"{path}[{i}]"
            if isinstance(item, str) and new_path in translations:
                result.append(translations[new_path])
            elif isinstance(item, (dict, list)):
                result.append(_apply_translations(item, translations, skip_set, new_path))
            else:
                result.append(item)
        return result
    return data


# [translator-gate 2026-07-04] English function words that do not exist in
# es/pt/fr — two or more distinct hits means the "translation" is still
# English (Haiku has been observed returning English PARAPHRASES of the
# authored copy, which then shipped and got cached).
_ENGLISH_MARKERS = re.compile(
    r"\b(?:the|you|your|is|are|and|of|what|before|from|with|can|will|"
    r"finds?|sees?|others?|any)\b", re.IGNORECASE)


def _looks_english(text: str) -> bool:
    if not isinstance(text, str) or len(text.strip()) < 4:
        return False
    return len(set(m.lower() for m in _ENGLISH_MARKERS.findall(text))) >= 2


async def _translator_round(strings, language_name, system_prompt, extra_rule=""):
    """One translator call. Returns the parsed {path: translated} dict."""
    user_message = (
        f"Translate these English strings to {language_name}.\n"
        "Preserve the EXACT JSON structure. Translate ONLY the values, not the keys.\n"
        f"Every output value MUST be written entirely in {language_name} — "
        "returning English, or an English paraphrase, is an error.\n"
        + extra_rule +
        "\nInput (English):\n"
        f"{json.dumps(strings, ensure_ascii=False, indent=2)}\n\n"
        "Output the same JSON object with every value translated."
    )
    client = _get_anthropic()
    response = await client.messages.create(
        model=TRANSLATOR_MODEL,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        # Strip a ```json ... ``` fence if the model added one.
        if text.count("```") >= 2:
            text = text.split("```", 2)[1]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().strip("`").strip()
    translated = json.loads(text)
    if not isinstance(translated, dict):
        raise ValueError("translator did not return a JSON object")
    return translated


async def _call_translator(strings, target_language):
    """Translate a flat {path: english} dict via Claude Haiku. Returns {path: translated}."""
    language_name = {
        "es": "Spanish (LATAM neutral)",
        "pt": "Brazilian Portuguese",
        "fr": "French (France)",
    }[target_language]

    # 2-arg signature per the Loc-4 Sanskrit-handling addendum.
    system_prompt = build_translation_system_prompt(language_name, target_language)

    translated = await _translator_round(strings, language_name, system_prompt)

    # [translator-gate 2026-07-04] retry ONCE for values that came back
    # still-English; keep the ORIGINAL authored string (never a paraphrase)
    # for anything that fails twice. English-in-target is a rendering bug;
    # a silently rewritten English sentence is a voice bug — worse.
    _still_en = {k: strings[k] for k, v in translated.items()
                 if k in strings and isinstance(v, str) and _looks_english(v)}
    if _still_en:
        logger.warning(
            f"[translation] {len(_still_en)} value(s) returned in English — retrying once")
        try:
            retry = await _translator_round(
                _still_en, language_name, system_prompt,
                extra_rule=("REMINDER: your previous attempt returned English. "
                            f"Write every value in {language_name} only.\n"))
            for k, v in retry.items():
                if k in translated and isinstance(v, str) and not _looks_english(v):
                    translated[k] = v
        except Exception as _re:
            logger.warning(f"[translation] retry failed (non-fatal): {_re}")
        for k in _still_en:
            if _looks_english(translated.get(k, "")):
                logger.warning(f"[translation] still English after retry, keeping ORIGINAL: {k}")
                translated[k] = strings[k]

    # Any key the translator dropped or mangled falls back to its English source.
    for key, english in strings.items():
        if key not in translated or not isinstance(translated[key], str):
            logger.warning(f"[translation] key not returned cleanly, keeping English: {key}")
            translated[key] = english
    return translated
