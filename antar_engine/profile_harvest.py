"""
antar_engine/profile_harvest.py
Keep the durable facts a user hands us inside their question.   2026-07-22

A field-coverage audit over the live base found the personalisation layer was
running on almost nothing:

    current_city          26/179   14.5%
    profession             1/179    0.6%      <- one user
    ventures               1/179    0.6%
    career_stage           3/179    1.7%
    marital_status         5/179    2.8%

venture_context, life_context and vocational_fit all read those fields. For
99.4% of users they read an empty string, so every "is this work right for you"
answer was reasoning about a person the engine knew nothing about.

Meanwhile /api/v1/ask never wrote a single field back. Users say "my SaaS
business", "my wife", "my restaurant in Bogota" — once a day, in their own
words — and we discarded it and asked them to fill in a settings form instead.

This module extracts only what is stated plainly, and the caller writes it ONLY
into fields that are currently empty. Two rules make that safe:

  * Never overwrite. A value the user typed into settings always beats one
    inferred from a sentence.
  * Never guess. Every marker here is an explicit self-statement ("my startup",
    "I am married"). Absence of a marker returns nothing rather than a default.

All matching is WORD-BOUNDED. An earlier bug in this codebase matched the
substring "arr" inside "m-arr-ied" and routed a marriage question to business;
substring matching on human sentences is how that happens.
"""

import re
from typing import Dict, Optional

# ── career stage ─────────────────────────────────────────────────────────
# Ordered: the first match wins, so the most specific claim is listed first.
_CAREER_STAGE = (
    ("running_business", (
        # up to three describing words may sit between "my" and the noun:
        # "my wholesale cloth business", "my small import export firm".
        # "company" is deliberately ABSENT: employees say "my company" as often
        # as founders do ("my company keeps delaying appraisals"), so it cannot
        # distinguish the two. "my own company" is unambiguous and is kept.
        r"\bmy (?:own )?(?:[\w-]+ ){0,3}(?:startup|business|firm|agency|practice|venture)\b",
        r"\bmy own company\b",
        r"my (?:saas|product|app|platform|brand|restaurant|clinic|studio)",
        r"i (?:run|own|founded|started) (?:a|an|my|the) \w+",
        r"\bmy (?:clients?|customers?)\b",
        r"\bour (?:startup|company|revenue|arr|mrr)\b",
        r"\bi am a founder\b", r"\bi'm a founder\b",
        r"\bmi (?:empresa|negocio|emprendimiento)\b",
    )),
    ("employed", (
        r"\bmy (?:job|boss|manager|employer|office|salary|appraisal|promotion)\b",
        r"\bmy (?:team lead|reporting manager)\b",
        r"\bi work (?:at|for|in) \w+",
        r"\bmi (?:trabajo|jefe|empleo)\b",
    )),
    ("seeking", (
        r"\b(?:looking|searching) for a (?:new )?job\b",
        r"\bjob (?:hunt|search|interview)\b",
        r"\bi (?:am|'m) unemployed\b", r"\bout of work\b",
        r"\bbuscando (?:trabajo|empleo)\b",
    )),
    ("studying", (
        r"\bmy (?:studies|exams?|college|university|course|degree)\b",
        r"\bi (?:am|'m) (?:a )?(?:student|studying)\b",
        r"\bmis estudios\b",
    )),
)

# ── marital / children ───────────────────────────────────────────────────
_MARITAL = (
    ("married",  (r"\bmy (?:wife|husband|spouse)\b", r"\bi (?:am|'m) married\b",
                  r"\bmy marriage\b", r"\bmi (?:esposa|esposo|marido|mujer)\b")),
    ("divorced", (r"\bmy (?:ex-wife|ex-husband|ex wife|ex husband)\b",
                  r"\bi (?:am|'m) divorced\b", r"\bmy divorce\b", r"\bmi divorcio\b")),
    ("dating",   (r"\bmy (?:girlfriend|boyfriend|partner|fiance|fiancee|fiancé|fiancée)\b",
                  r"\bmi (?:novia|novio)\b")),
    ("single",   (r"\bi (?:am|'m) single\b", r"\bstill unmarried\b", r"\bsoy soltero\b",
                  r"\bsoy soltera\b")),
)
_CHILDREN = (
    ("has_children", (r"\bmy (?:son|daughter|kids?|children|child)\b",
                      r"\bmi (?:hijo|hija|hijos)\b")),
    ("expecting",    (r"\b(?:we|my wife|my partner) (?:are|is) expecting\b",
                      r"\bpregnan(?:t|cy)\b", r"\bembarazad")),
)


def _first_match(text: str, table) -> Optional[tuple]:
    for value, patterns in table:
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                return value, m.group(0)
    return None


def harvest_profile_facts(question: str, existing: Optional[Dict] = None) -> Dict:
    """Durable facts stated in `question`, as {field: {"value", "evidence"}}.

    `existing` is the chart record. Any field that already holds a value is
    skipped entirely — a fact the user entered deliberately outranks one
    inferred from a sentence, and re-deriving it every day risks flipping a
    correct value on a stray phrase.

    Returns {} when the question states nothing durable, which is the common
    case and must stay cheap.
    """
    q = (question or "").strip()
    if len(q) < 8:
        return {}
    existing = existing or {}
    out: Dict[str, Dict] = {}

    def _offer(field, value, evidence):
        cur = existing.get(field)
        if isinstance(cur, str) and cur.strip():
            return
        if isinstance(cur, (list, tuple)) and len(cur):
            return
        if cur not in (None, "", [], {}):
            return
        out[field] = {"value": value, "evidence": evidence}

    hit = _first_match(q, _CAREER_STAGE)
    if hit:
        _offer("career_stage", hit[0], hit[1])

    hit = _first_match(q, _MARITAL)
    if hit:
        _offer("marital_status", hit[0], hit[1])

    hit = _first_match(q, _CHILDREN)
    if hit:
        _offer("children_status", hit[0], hit[1])

    # Sector comes from the existing detector rather than a second vocabulary,
    # so "my cloth wholesale" resolves the same way here as when the reading
    # itself decides which significators to use.
    try:
        from antar_engine.venture_context import detect_venture_nature
        nat = detect_venture_nature(q)
        if nat and nat.get("nature"):
            _offer("ventures", [nat["nature"]], nat["nature"])
    except Exception:
        pass

    return out


def apply_harvest(supabase, chart_id: str, facts: Dict) -> Dict:
    """Persist harvested facts. Best-effort and never raises.

    Writing must never be able to break an answer that has already been
    computed, so every failure — a missing column, a migration not yet run, a
    transient network error — is swallowed and reported in the return value
    instead of propagating.
    """
    if not (supabase and chart_id and facts):
        return {"written": [], "skipped": []}
    payload = {k: v["value"] for k, v in facts.items()}
    try:
        supabase.table("charts").update(payload).eq("id", chart_id).execute()
        return {"written": sorted(payload.keys()), "skipped": []}
    except Exception as e:
        # Retry field-by-field: one unknown column must not lose the others.
        written, skipped = [], []
        for k, v in payload.items():
            try:
                supabase.table("charts").update({k: v}).eq("id", chart_id).execute()
                written.append(k)
            except Exception:
                skipped.append(k)
        return {"written": written, "skipped": skipped, "error": str(e)[:160]}
