"""
antar_engine/readability.py — COWORK BRIEF 1, STEP 2
Deterministic readability scoring + ONE bounded auto-simplify re-pass.

Order contract (enforced at the call sites, restated here):
    narrate -> strip jargon -> maybe_simplify -> strip jargon again -> return

- readability_score(text): deterministic, no LLM. Sentence/word stats.
- maybe_simplify(text, language, surface): score; if too_complex, ONE Haiku
  re-pass with a tight rewrite prompt; re-score; return best of
  {original, rewrite}. Hard cap: one re-pass (bounded latency). Never raises —
  any failure returns the original text with simplified=False.

Debug shape (exposed in each surface's _debug field by the call sites):
    {"text": str, "simplified": bool,
     "score_before": dict, "score_after": dict | None}
"""
from antar_engine.constants import HAIKU_MODEL
import os
import re
from typing import Optional

# Thresholds — starting points per brief; tune on real output.
AVG_SENTENCE_WORDS_MAX = 22.0
LONGEST_SENTENCE_WORDS_MAX = 32
LONG_WORD_RATIO_MAX = 0.18

SIMPLIFY_MODEL = os.getenv("READABILITY_SIMPLIFY_MODEL", HAIKU_MODEL)
_SIMPLIFY_MAX_TOKENS = 700

# Toggle: READABILITY_SIMPLIFY=off disables the LLM re-pass (scoring still runs).
def _enabled() -> bool:
    return (os.getenv("READABILITY_SIMPLIFY", "on") or "on").lower() not in ("off", "0", "false")


_anthropic_client = None


def _get_client():
    """Lazy AsyncAnthropic, reused across calls (same pattern as
    translation_middleware)."""
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _anthropic_client


# ── deterministic scoring ────────────────────────────────────────────────────

_SENT_SPLIT_RX = re.compile(r"(?<=[.!?…])\s+|\n+")
_WORD_RX = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ'’\-]+")
_VOWEL_GROUP_RX = re.compile(r"[aeiouyáéíóúàèìòùâêîôûäëïöü]+", re.IGNORECASE)
_MD_NOISE_RX = re.compile(r"\*\*|\*|__|#+\s|`")


def _sentences(text: str) -> list:
    clean = _MD_NOISE_RX.sub(" ", text or "")
    return [s.strip() for s in _SENT_SPLIT_RX.split(clean) if s.strip() and _WORD_RX.search(s)]


def _is_long_word(w: str) -> bool:
    # >12 chars OR 4+ vowel groups (syllable-ish proxy, works for en/es/pt)
    return len(w) > 12 or len(_VOWEL_GROUP_RX.findall(w)) >= 4


def readability_score(text: str) -> dict:
    """Deterministic, no LLM. Sentence-length + long-word stats."""
    sents = _sentences(text or "")
    if not sents:
        return {"avg_sentence_words": 0.0, "longest_sentence_words": 0,
                "long_word_ratio": 0.0, "too_complex": False}
    counts = []
    words_all = []
    for s in sents:
        ws = _WORD_RX.findall(s)
        counts.append(len(ws))
        words_all.extend(ws)
    avg = sum(counts) / len(counts)
    longest = max(counts)
    long_ratio = (sum(1 for w in words_all if _is_long_word(w)) / len(words_all)) if words_all else 0.0
    return {
        "avg_sentence_words": round(avg, 2),
        "longest_sentence_words": longest,
        "long_word_ratio": round(long_ratio, 4),
        "too_complex": (avg > AVG_SENTENCE_WORDS_MAX
                        or longest > LONGEST_SENTENCE_WORDS_MAX
                        or long_ratio > LONG_WORD_RATIO_MAX),
    }


def _complexity_key(score: dict) -> tuple:
    """For best-of comparison: fewer threshold breaches, then lower stats."""
    breaches = (
        int(score["avg_sentence_words"] > AVG_SENTENCE_WORDS_MAX)
        + int(score["longest_sentence_words"] > LONGEST_SENTENCE_WORDS_MAX)
        + int(score["long_word_ratio"] > LONG_WORD_RATIO_MAX)
    )
    return (breaches, score["longest_sentence_words"], score["avg_sentence_words"],
            score["long_word_ratio"])


# ── the one bounded simplify re-pass ─────────────────────────────────────────

_LANG_NAME = {"en": "English", "es": "Spanish", "pt": "Portuguese"}

_SIMPLIFY_SYSTEM = (
    "You rewrite text so a 12-year-old gets it on first read. Shorter sentences, "
    "everyday words, same meaning. Keep the verdict in the first sentence and keep "
    "the action at the end. Do not add new claims, names, dates, or numbers that are "
    "not in the original. Never use the words 'energy', 'vibration', or 'alignment'. "
    "Never use astrology terms, planet names, or Sanskrit. Keep the SAME language as "
    "the input. Preserve any markdown section headers exactly. Output ONLY the "
    "rewritten text — no preamble, no quotes, no commentary."
)


async def maybe_simplify(text: str, language: str = "en",
                         surface: str = "unknown") -> dict:
    """Score; if too_complex, ONE Haiku re-pass; re-score; return the better.
    Never raises. Return: {"text", "simplified", "score_before", "score_after"}."""
    out = {"text": text, "simplified": False,
           "score_before": None, "score_after": None}
    try:
        if not isinstance(text, str) or len(text.split()) < 8:
            return out
        before = readability_score(text)
        out["score_before"] = before
        if not before["too_complex"] or not _enabled():
            return out
        lang_name = _LANG_NAME.get((language or "en").lower()[:2], "English")
        client = _get_client()
        resp = await client.messages.create(
            model=SIMPLIFY_MODEL,
            max_tokens=_SIMPLIFY_MAX_TOKENS,
            system=_SIMPLIFY_SYSTEM,
            messages=[{
                "role": "user",
                "content": (f"Language: {lang_name}. Rewrite this so a 12-year-old "
                            f"gets it on first read:\n\n{text}"),
            }],
        )
        rewrite = (resp.content[0].text or "").strip()
        if not rewrite:
            return out
        after = readability_score(rewrite)
        out["score_after"] = after
        # best of {original, rewrite} — one pass, no loop.
        if _complexity_key(after) < _complexity_key(before):
            out["text"] = rewrite
            out["simplified"] = True
        print(f"[readability] surface={surface} lang={language} fired=1 "
              f"kept={'rewrite' if out['simplified'] else 'original'} "
              f"before={before} after={after}")
        return out
    except Exception as e:  # never break a surface for readability
        print(f"[readability] surface={surface} non-fatal: {e}")
        return out


async def simplify_payload_fields(payload: dict, fields: list,
                                  language: str = "en", surface: str = "unknown",
                                  strip_fn=None, debug_key: str = "_readability") -> dict:
    """Wire-helper for dict payloads: for each named string field, run
    maybe_simplify; re-strip with strip_fn AFTER the rewrite (the rewrite could
    reintroduce a banned word). Attaches per-field debug under payload[debug_key].
    In-place + returned. Never raises."""
    if not isinstance(payload, dict):
        return payload
    dbg = {}
    for f in fields:
        try:
            v = payload.get(f)
            if not isinstance(v, str) or not v.strip():
                continue
            r = await maybe_simplify(v, language=language, surface=f"{surface}.{f}")
            new_text = r["text"]
            if r["simplified"] and callable(strip_fn):
                try:
                    stripped = strip_fn(new_text)
                    if isinstance(stripped, str) and stripped.strip():
                        new_text = stripped
                except Exception:
                    pass
            payload[f] = new_text
            if r["score_before"] is not None:
                dbg[f] = {"simplified": r["simplified"],
                          "score_before": r["score_before"],
                          "score_after": r["score_after"]}
        except Exception as e:
            print(f"[readability] field={f} non-fatal: {e}")
    if dbg:
        try:
            existing = payload.get(debug_key)
            if isinstance(existing, dict):
                existing.update(dbg)
            else:
                payload[debug_key] = dbg
        except Exception:
            pass
    return payload
