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


# ─────────────────────────────────────────────────────────────────────
# [gap2-noun-splice 2026-06-09] Subject-clause splicers.
# The verdict resolver authors signal_line + plain_summary from a
# template — Claude's noun naming is lost during the override. These
# helpers re-introduce the confirmed noun into the SUBJECT clause
# without altering the verdict adjective or window phrase.
# ─────────────────────────────────────────────────────────────────────

import re as _re


# Concern → conservative subject phrase the template usually opens
# with. We rewrite the OPENING subject if it matches one of these.
# Only domains in _VENTURE_DOMAINS get spliced.
_CONCERN_SUBJECT_RE = {
    "speculation": _re.compile(
        r"^(?:the\s+)?speculative\s+(?:call|move|trade|bet|deployment)"
        r"(?:\s+you'?re\s+(?:weighing|considering|eyeing))?",
        _re.IGNORECASE,
    ),
    "career": _re.compile(
        r"^(?:the\s+)?(?:career\s+(?:move|decision|step|conversation)|"
        r"professional\s+positioning|your\s+career)",
        _re.IGNORECASE,
    ),
    "finance": _re.compile(
        r"^(?:the\s+)?(?:financial\s+(?:decision|move|position)|"
        r"capital\s+(?:deployment|move)|your\s+(?:money|finances))",
        _re.IGNORECASE,
    ),
    "wealth": _re.compile(
        r"^(?:the\s+)?wealth\s+(?:position|move|build)",
        _re.IGNORECASE,
    ),
    "funding": _re.compile(
        r"^(?:the\s+)?(?:funding\s+(?:round|conversation)|capital\s+raise)",
        _re.IGNORECASE,
    ),
    "money": _re.compile(
        r"^(?:your\s+)?(?:money|finances)\s+(?:position|move|today|tomorrow)?",
        _re.IGNORECASE,
    ),
    "business": _re.compile(
        r"^(?:the\s+)?(?:business\s+(?:move|call|decision)|your\s+business)",
        _re.IGNORECASE,
    ),
}


def _noun_phrase(ventures, profession: str) -> str:
    """Build a subject phrase from confirmed nouns. Prefers ventures
    (more specific). Caps at 2 names ('Antar and TezopsAI'). Falls
    back to 'your <profession>' when no ventures."""
    vs = _coerce_ventures(ventures)
    if vs:
        if len(vs) == 1:
            return vs[0]
        if len(vs) == 2:
            return f"{vs[0]} and {vs[1]}"
        return f"{vs[0]}, {vs[1]} and others"
    p = _coerce_profession(profession)
    if p:
        # 'Founder + CEO' → 'as a Founder + CEO' subject form.
        return f"your work as {p}"
    return ""


def rewrite_signal_line(line: str, ventures, profession: str, concern: str) -> str:
    """Replace the template SUBJECT clause with the noun phrase.

    Examples (subject in [brackets]):
        IN : '[The speculative call you're weighing] is flat for you tomorrow.'
        OUT: '[Antar and TezopsAI] are flat for you tomorrow.'

        IN : '[Professional positioning] is favorable today.'
        OUT: '[Antar and TezopsAI] are favorable today.'

    No-op when:
      - concern not in venture-domain family,
      - or no noun is present,
      - or the line doesn't match a known subject pattern.
    """
    if not isinstance(line, str) or not line:
        return line
    if not is_venture_domain(concern):
        return line
    noun = _noun_phrase(ventures, profession)
    if not noun:
        return line

    domain = (concern or "general").lower()
    pat = _CONCERN_SUBJECT_RE.get(domain)
    if not pat:
        return line

    # Adjust the copula for singular vs compound subject.
    # "X is" vs "X and Y are". Tiny heuristic.
    _is_compound = (
        " and " in noun or
        noun.count(",") >= 1 or
        len(_coerce_ventures(ventures)) >= 2
    )

    out, n = pat.subn(noun, line, count=1)
    if not n:
        return line

    # Fix verb agreement if the template said 'is' and we now have a
    # compound subject. Only the FIRST 'is' immediately after the
    # noun (within 30 chars) is rewritten.
    if _is_compound:
        head = out[:120]
        tail = out[120:]
        head = _re.sub(
            r"^(\s*" + _re.escape(noun) + r")\s+is\b",
            r"\1 are",
            head,
            count=1,
        )
        out = head + tail

    # Sentence-start capitalization fix — when the noun phrase starts
    # with a lowercase word ('your work as CFO'), bump the first letter.
    if out and out[0].islower():
        out = out[0].upper() + out[1:]

    return out


def rewrite_plain_summary(text: str, ventures, profession: str, concern: str) -> str:
    """Splice the noun into the OPENING clause of plain_summary.

    Strategy: if the first sentence matches a template subject pattern,
    rewrite that sentence the same way as signal_line. Subsequent
    sentences are left alone (we're not paraphrasing the whole prose,
    just naming the subject).
    """
    if not isinstance(text, str) or not text:
        return text
    if not is_venture_domain(concern):
        return text
    noun = _noun_phrase(ventures, profession)
    if not noun:
        return text

    # Split on first sentence boundary.
    parts = _re.split(r"(\.\s+|\!\s+|\?\s+)", text, maxsplit=1)
    if not parts:
        return text
    first = parts[0]
    rest = "".join(parts[1:]) if len(parts) > 1 else ""

    new_first = rewrite_signal_line(first, ventures, profession, concern)
    if new_first == first:
        return text
    return new_first + rest
