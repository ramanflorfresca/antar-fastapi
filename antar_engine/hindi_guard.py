"""
antar_engine/hindi_guard.py — deterministic Devanagari guard for answers served in `hi`.

Owner rule: ZERO tolerance for answering in the wrong language. A reader who picked
हिन्दी must never receive English or Roman-script Hinglish. The Ask pipeline is ~5k
lines of guards written against English / es / pt / Hinglish text and merges copy from
many modules, so rather than trusting every upstream path to write Devanagari, the
FINAL payload is checked here:

  1. every prose string that is not mostly Devanagari is found — SENTENCE by sentence,
     so one English sentence inside an otherwise-Hindi paragraph cannot hide in the ratio;
  2. those sentences are translated to Devanagari (Haiku, script-gated, one retry — the
     same translator the other surfaces use);
  3. anything still not Devanagari is REPLACED, never shipped: the core answer fields get
     a deterministic Hindi fallback line; list items (chips) are dropped; other prose
     fields are removed.

`mode`, `verdict`, ids, dates, numbers and URLs are never touched.
"""
from __future__ import annotations

import logging
import re
from typing import Awaitable, Callable, Optional

from antar_engine.lang_registry import fallback_text, script_counts

logger = logging.getLogger(__name__)

# Never language-checked: structural / enum / identifier keys.
SKIP_KEYS = frozenset({
    "mode", "verdict", "lean", "locked", "locked_until", "verify_after", "tier", "band", "scope",
    "id", "chart_id", "user_id", "uuid", "url", "image_url", "icon", "color", "language",
    "created_at", "updated_at", "generated_at", "timestamp", "date", "lane", "concern", "domain",
    "kind", "type", "key", "status", "_translation_status", "intent", "area", "source",
    "timeframe", "tz", "tz_offset", "horary_number",
})

# Core answer fields: when the translator cannot make them Hindi they are replaced
# by a generic Hindi line rather than removed (the card must still say something honest).
CORE_FIELDS = {"read": "read", "next": "next", "why": "why"}

_SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")

Translator = Callable[[dict], Awaitable[dict]]


def sentence_is_bad(sentence: str, min_latin: int = 4, min_ratio: float = 0.5) -> bool:
    """True when a sentence is not Hindi: enough Latin letters AND Devanagari is under
    half of the letters. A Hindi sentence carrying a name, "Antar", a month abbreviation
    or a number passes; an English or Roman-script sentence does not."""
    dev, lat = script_counts(sentence)
    if lat < min_latin:
        return False
    return dev / (dev + lat) < min_ratio


def text_is_hindi(text: str) -> bool:
    """No sentence in `text` fails the Devanagari test."""
    return not any(sentence_is_bad(s) for s in _SENT_SPLIT.split(text or "") if s.strip())


def _split_keep(text: str) -> list:
    """Split into sentences keeping each trailing separator so the text reassembles."""
    out, pos = [], 0
    for m in _SENT_SPLIT.finditer(text):
        out.append(text[pos:m.start()])
        out.append(text[m.start():m.end()])
        pos = m.end()
    out.append(text[pos:])
    return out  # [sent, sep, sent, sep, ..., sent]


async def _default_translator(strings: dict) -> dict:
    from antar_engine.translation_middleware import _call_translator
    return await _call_translator(strings, "hi")


def _walk(node, owner=None):
    """Yield (container, key, value, owner) for every string leaf not under a skipped key.
    `owner` = (list, index) of the nearest list ELEMENT that holds the leaf (a chip dict),
    so an unrepairable leaf can drop the whole element instead of leaving a half-empty one."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k in SKIP_KEYS:
                continue
            if isinstance(v, str):
                yield node, k, v, owner
            elif isinstance(v, (dict, list)):
                yield from _walk(v, owner)
    elif isinstance(node, list):
        for i, v in enumerate(list(node)):
            if isinstance(v, str):
                yield node, i, v, (node, i)
            elif isinstance(v, (dict, list)):
                yield from _walk(v, (node, i))


async def enforce_hindi(payload, translator: Optional[Translator] = None) -> dict:
    """Make every prose string in `payload` Devanagari or remove/replace it.

    Mutates and returns `payload`. Returns the stats in `payload["_hi_guard"]` only when
    `_HI_GUARD_STATS` is set by a caller (kept out of the response by default).
    Never raises: a translator failure is treated as "could not repair" and the
    replace/drop step still runs, so the output is Hindi-or-nothing either way.
    """
    translate = translator or _default_translator
    if not isinstance(payload, (dict, list)):
        return payload

    # 1. gather bad sentences
    jobs = {}          # job id -> sentence
    plans = []         # (container, key, [parts]) with ("raw", text) | ("job", id)
    n = 0
    for cont, key, val, owner in _walk(payload):
        if text_is_hindi(val):
            continue
        parts = _split_keep(val)
        plan = []
        for i, seg in enumerate(parts):
            if i % 2 == 1 or not seg.strip() or not sentence_is_bad(seg):
                plan.append(("raw", seg))
            else:
                jid = f"s{n}"
                n += 1
                jobs[jid] = seg.strip()
                plan.append(("job", jid))
        plans.append((cont, key, plan, owner))

    if not jobs:
        return payload

    # 2. translate them (never fatal)
    done = {}
    try:
        got = await translate(dict(jobs))
        for jid, src in jobs.items():
            tr = got.get(jid) if isinstance(got, dict) else None
            if isinstance(tr, str) and tr.strip() and not sentence_is_bad(tr):
                done[jid] = tr.strip()
    except Exception as e:  # noqa: BLE001 — the guard must never break an answer
        logger.warning("[hi-guard] translator failed: %s", e)

    # 3. reassemble; replace / drop whatever is still not Hindi
    drop_list_idx = {}   # id(list) -> [indexes]
    replaced = dropped = fixed = 0
    for cont, key, plan, owner in plans:
        bad_left = False
        out = []
        for kind, v in plan:
            if kind == "raw":
                out.append(v)
            elif v in done:
                out.append(done[v])
                fixed += 1
            else:
                bad_left = True
                out.append("")
        if not bad_left:
            cont[key] = "".join(out)
            continue
        if isinstance(cont, dict) and key in CORE_FIELDS:
            cont[key] = fallback_text(CORE_FIELDS[key], "hi")
            replaced += 1
        elif owner is not None:
            # a chip / list element that cannot be made Hindi goes away whole
            drop_list_idx.setdefault(id(owner[0]), (owner[0], []))[1].append(owner[1])
            dropped += 1
        else:
            # keep any Hindi sentences that survived; if nothing Hindi is left, remove the field
            kept = "".join(out).strip()
            if kept and text_is_hindi(kept):
                cont[key] = kept
            else:
                cont.pop(key, None)
            dropped += 1
    for cont, idxs in drop_list_idx.values():
        for i in sorted(set(idxs), reverse=True):
            del cont[i]

    logger.info("[hi-guard] sentences fixed=%d replaced=%d dropped=%d", fixed, replaced, dropped)
    return payload
