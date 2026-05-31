"""
antar_engine/compatibility_deepread.py

Phase-2 optional deep-read synthesis for POST /api/v1/compat (deep_read=true).

Generates one short "how to use it / how to work with it" paragraph per layer via
Claude Sonnet, grounded ONLY in the already-computed layer scores/badges/lines and
the reason/role direction. Populates the per-layer `detail` field that Phase 1
reserved (the frontend already ignores it when absent).

Design:
  - Plain English, names allowed, NO Sanskrit / planet-as-scaffolding / house numbers.
  - English generation; the endpoint's translate layer handles es/pt (the `detail`
    key is already in the translate allowlist).
  - In-process cache keyed by (content hash of the layers, reason, role, day) so a
    pair's deep read is generated once per day per worker.
  - Fully graceful: returns {} if the client is unavailable or anything fails, so
    deep_read can never break the base response.
"""

import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DEEPREAD_MODEL = "claude-sonnet-4-20250514"

_DEEPREAD_CACHE = {}  # key -> {layer_key: detail}

_DIRECTION = {
    "employee": "A is the employer/senior; B is the person being evaluated for the role. Write the detail for the employer.",
    "boss-or-manager": "A is the junior/report; B is the manager. Write the detail for the report working under B.",
}


def _cache_key(layers, reason, role) -> str:
    basis = json.dumps(
        {"l": [(x["key"], x["badge"], x["line"]) for x in layers], "r": reason, "ro": role},
        sort_keys=True, ensure_ascii=False,
    )
    day = datetime.utcnow().date().isoformat()
    return f"{day}:{hashlib.sha256(basis.encode()).hexdigest()[:16]}"


def _build_prompt(layers, reason, role, a_name, b_name, overall_score) -> str:
    direction = _DIRECTION.get(reason, "")
    role_line = f"Role being read: {role}.\n" if role else ""
    layer_block = "\n".join(
        f"- {l['key']} ({l['name']}): badge={l['badge']}, one-liner=\"{l['line']}\""
        for l in layers
    )
    return f"""You are writing the expandable "detail" text for a relationship compatibility read between {a_name} (A) and {b_name} (B).

Relationship reason: {reason}. {role_line}{direction}
Overall alignment score: {overall_score}/100.

For each of the 6 layers below, write ONE short paragraph (2-3 sentences) of practical guidance:
- If the badge is FLOW or MIXED, frame it as "how to use it" — how to lean on this strength.
- If the badge is STRAIN, frame it as "how to work with it" — the concrete move that reduces the friction.

Layers:
{layer_block}

HARD RULES:
- Plain, warm, direct English. Speak to {a_name} about {b_name}.
- NO astrology jargon, NO Sanskrit, NO planet names, NO house numbers. Never say "compatible/incompatible" or "should hire / should not hire".
- No gendered terms (no husband/wife); use the names or "the other person".
- Return ONLY a JSON object keyed by the layer keys: soul, chemistry, public, lifepath, communication, friction. Each value is the paragraph string. No prose outside the JSON."""


async def build_deep_read(client, layers, reason, role, a_name, b_name,
                          overall_score, model: str = DEEPREAD_MODEL) -> dict:
    """Return {layer_key: detail_paragraph}. {} on any failure (never raises)."""
    if client is None or not layers:
        return {}
    ck = _cache_key(layers, reason, role)
    if ck in _DEEPREAD_CACHE:
        return _DEEPREAD_CACHE[ck]
    try:
        prompt = _build_prompt(layers, reason, role, a_name, b_name, overall_score)
        resp = await client.messages.create(
            model=model,
            max_tokens=1400,
            system="You write concise, jargon-free relationship guidance. Output strict JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            if text.count("```") >= 2:
                text = text.split("```", 2)[1]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:]
            text = text.strip().strip("`").strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            return {}
        keys = ("soul", "chemistry", "public", "lifepath", "communication", "friction")
        out = {k: str(data[k]).strip() for k in keys if isinstance(data.get(k), str) and data[k].strip()}
        _DEEPREAD_CACHE[ck] = out
        return out
    except Exception as e:
        logger.warning(f"[compat-deepread] non-fatal, skipping deep_read: {e}")
        return {}
