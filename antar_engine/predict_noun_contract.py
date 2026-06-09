"""
antar_engine/predict_noun_contract.py
──────────────────────────────────────
[gap2-life-nouns 2026-06-09] Required-if-present, never-invented-if-
absent. Builds a prompt block that demands the read NAME the user's
confirmed-present life nouns (profession + ventures) when the asked
concern is in the right domain family.

Doctrine: V2.2 — nouns enrich narration but never change the verdict
band, timeframe, or confidence. The block is silent (returns "") when
the chart row has no relevant noun, so /predict falls through to its
existing honest-flat behavior. Hallucination prevention by design:
the model is only told to name nouns we hand it.
"""

from __future__ import annotations
from typing import Any, List, Optional


# Domain routing — venture/profession nouns belong here.
# Health / relationship / children / property reads SHOULD NOT get
# the venture noun.
_VENTURE_DOMAINS = {
    "career", "wealth", "finance", "speculation",
    "funding", "money", "business",
}


def _coerce_ventures(v: Any) -> List[str]:
    """ventures can arrive as list, JSON string, or comma-separated
    string. Normalize to a list of non-empty stripped strings."""
    if not v:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        # Try a JSON parse first
        try:
            import json as _j
            parsed = _j.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
        # Fall back to comma-split
        return [p.strip() for p in s.split(",") if p.strip()]
    return []


def _coerce_profession(v: Any) -> str:
    """profession may be free-text. Normalize to stripped string or ""."""
    if not v:
        return ""
    return str(v).strip()


def is_venture_domain(concern: str) -> bool:
    return (concern or "general").lower() in _VENTURE_DOMAINS


def build_predict_noun_block(
    concern: str,
    chart_record: Optional[dict] = None,
    request_obj: Any = None,
) -> str:
    """Return a prompt block enforcing required-if-present nouns.

    Sources nouns in priority order: chart_record (persisted), then
    request_obj attributes (live request). Returns "" when:
      - the concern is not in the venture-domain family
      - OR no profession AND no ventures are present anywhere.

    Returns a single block of plain English instructions — NEVER lists
    nouns the model could fabricate from. The block is conservative:
    if only profession is known, only profession is required; if only
    ventures, only ventures.
    """
    if not is_venture_domain(concern):
        return ""

    cr = chart_record or {}

    # Pull from chart_record first (persisted, source of truth), then
    # fall back to live request_obj fields.
    ventures = _coerce_ventures(cr.get("ventures") or cr.get("active_ventures"))
    profession = _coerce_profession(cr.get("profession") or cr.get("role"))

    if request_obj is not None:
        if not ventures:
            ventures = _coerce_ventures(getattr(request_obj, "ventures", None))
        if not profession:
            profession = _coerce_profession(getattr(request_obj, "profession", None))

    if not ventures and not profession:
        return ""  # sparsity gate — never invent a noun

    parts = ["[NOUN CONTRACT — required-if-present, never-invented-if-absent]"]
    parts.append(
        "The user has confirmed life facts on their profile. You MUST name "
        "AT LEAST ONE of these concretely in the read. Generic professional "
        "language (\"professional positioning\", \"your work\", \"your "
        "business\") is INSUFFICIENT — name the actual noun below."
    )

    if profession:
        parts.append(f"  - Role: {profession}")
    if ventures:
        # Cap at 4 to keep prompts tight.
        names = ", ".join(ventures[:4])
        parts.append(f"  - Active ventures: {names}")

    parts.append(
        "RULES:"
    )
    parts.append(
        "  - DO name at least one venture or the role above by its actual "
        "name in `signal_line` AND `plain_summary`."
    )
    parts.append(
        "  - DO NOT invent ventures, funding rounds, deals, clients, roles, "
        "or projects beyond what is listed above. Anything not in this list "
        "is OFF-LIMITS."
    )
    parts.append(
        "  - If no chart signal fits the listed noun, name it plainly anyway "
        "(e.g. \"<venture> doesn't have a green light today\")."
    )
    parts.append(
        "  - This contract changes the PROSE only. Verdict band, timeframe, "
        "and confidence are Python-authored and must not change because of "
        "the noun."
    )

    return "\n".join(parts) + "\n"
