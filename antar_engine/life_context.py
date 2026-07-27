"""
antar_engine/life_context.py

LIFE CONTEXT — single source of truth for "what is actually happening in
this person's life right now." Wires the captured situation (Patra) into
every prediction surface so reads are situation-aware, not generic.

Background (see Antar.world/PATRA_PHASE0_AUDIT_2026-06-15.md):
  * There is ONE store — the `charts` row — with TWO unreconciled column
    sets that were never mapped to each other:
      - onboarding writes  : life_work / life_relationship / life_kids
      - /api/v1/user/patra : career_stage / marital_status / children_status
                             / health_status / financial_status
  * Prediction surfaces read ONLY the patra-named columns, so the onboarding
    life_* capture was read by nothing. This module reconciles them.

Canonical (normalized) vocabulary returned to callers:
    career_stage    : studying | job | running_business | in_transition | None
    marital_status  : single | relationship | married | divorced | None
    children_status : yes | no | None
    health_status   : <pass-through string> | None   (optional dimension)
    financial_status: <pass-through string> | None   (optional dimension)
    has_context     : bool — True iff ANY dimension is actually present

DOCTRINE
  * NEVER fabricate. When a dimension is absent we return None and surfaces
    fall back to a situation-neutral read.
  * The patra columns carry Postgres schema DEFAULTS for almost every chart
    (career_stage='mid_career', marital_status='unknown', etc.). A value that
    equals its default sentinel is treated as ABSENT — otherwise the default
    would mask, and override, the user's real onboarding life_* answer. This
    is the bug the sprint fixes, so the precedence is deliberate:
        real patra value  >  mapped life_* value  >  None
  * Situation sharpens framing and domain selection. It does NOT license
    dated event claims. Honesty guardrail travels with every surface.

Usage:
    from antar_engine.life_context import get_life_context, life_context_to_prompt_block

    lc = get_life_context(chart_record=chart_record)          # no extra fetch
    lc = get_life_context(chart_id, supabase=supabase)        # fetches the row
    block = life_context_to_prompt_block(lc)                  # "" when absent
"""

from __future__ import annotations
from typing import Optional


# ── Schema-default sentinels ──────────────────────────────────────────────────
# A patra column equal to its sentinel is a Postgres default, NOT user input,
# and must be treated as absent so it can't override a real life_* answer.
_PATRA_DEFAULT_SENTINELS = {
    "career_stage":     "mid_career",
    "marital_status":   "unknown",
    "children_status":  "no_children_unsure",
    "health_status":    "excellent",
    "financial_status": "stable",
}

# NB: "none" is NOT an empty token — for life_kids it is a real answer
# ("no children"). Field-specific maps decide what "none" means.
_EMPTY_TOKENS = {"", "unknown", "null", "n/a", "na"}


# ── Vocabulary maps (source value → canonical) ────────────────────────────────
# career_stage canonical: studying | job | running_business | in_transition
_CAREER_FROM_PATRA = {
    "student":       "studying",
    "job_seeking":   "in_transition",
    "early_career":  "job",
    "mid_career":    "job",          # only reached when NOT the default sentinel
    "senior_career": "job",
    "entrepreneur":  "running_business",
    "creative":      "job",
    "transition":    "in_transition",
    "retired":       None,            # out of canonical scope → neutral
}
# Onboarding life_work tokens. "building" = a business not yet stable (founder
# ruling 2026-06-15) → running_business.
_CAREER_FROM_LIFE_WORK = {
    "building":          "running_business",
    "business":          "running_business",
    "running_business":  "running_business",
    "entrepreneur":      "running_business",
    "founder":           "running_business",
    "self_employed":     "running_business",
    "job":               "job",
    "employed":          "job",
    "employee":          "job",
    "working":           "job",
    "career":            "job",
    "studying":          "studying",
    "student":           "studying",
    "school":            "studying",
    "transition":        "in_transition",
    "between":           "in_transition",
    "seeking":           "in_transition",
    "unemployed":        "in_transition",
}

# marital_status canonical: single | relationship | married | divorced
_MARITAL_FROM_PATRA = {
    "single":          "single",
    "never_married":   "single",
    "unmarried":       "single",
    "in_relationship": "relationship",
    "in_a_relationship": "relationship",
    "partnered":       "relationship",
    "dating":          "relationship",
    "married":         "married",
    "separated":       "divorced",     # post-marital restructuring
    "divorced":        "divorced",
    "widowed":         "divorced",      # post-marital; avoids "go find someone"
}
_MARITAL_FROM_LIFE_RELATIONSHIP = {
    "single":     "single",
    "alone":      "single",
    "partnered":  "relationship",
    "relationship": "relationship",
    "dating":     "relationship",
    "married":    "married",
    "engaged":    "relationship",
    "divorced":   "divorced",
    "separated":  "divorced",
    "widowed":    "divorced",
}

# children_status canonical: yes | no
_CHILDREN_YES = {
    "yes", "has_children", "have_children", "young_children", "older_children",
    "adult_children", "expecting", "kids", "parent",
}
_CHILDREN_NO = {
    "no", "none", "no_children", "no_children_wants", "no_children_by_choice",
    "childless",
}


# ── Internal helpers ──────────────────────────────────────────────────────────
def _clean(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in _EMPTY_TOKENS:
        return None
    return s


def _patra_real(row: dict, col: str) -> Optional[str]:
    """Return the patra column value only if it is real (not the schema default)."""
    v = _clean(row.get(col))
    if v is None:
        return None
    if v == _PATRA_DEFAULT_SENTINELS.get(col):
        return None
    return v


def real_patra_value(row: dict, col: str) -> Optional[str]:
    """Public wrapper over _patra_real, for callers outside this module.

    Several places in main.py read these columns directly with a hardcoded
    fallback — `chart_record.get("health_status", "excellent")` — which turns a
    schema default into an asserted fact about a real person. Every one of the
    92 live charts carries "excellent" health and "stable" finances because
    those are COLUMN DEFAULTS, not answers anybody gave. Use this instead.
    """
    return _patra_real(row, col)


def _norm_career(row: dict) -> Optional[str]:
    real = _patra_real(row, "career_stage")
    if real is not None:
        return _CAREER_FROM_PATRA.get(real, "job")
    lw = _clean(row.get("life_work"))
    if lw is not None:
        return _CAREER_FROM_LIFE_WORK.get(lw)
    return None


def _norm_marital(row: dict) -> Optional[str]:
    real = _patra_real(row, "marital_status")
    if real is not None:
        return _MARITAL_FROM_PATRA.get(real)
    lr = _clean(row.get("life_relationship"))
    if lr is not None:
        return _MARITAL_FROM_LIFE_RELATIONSHIP.get(lr)
    return None


def _norm_children(row: dict) -> Optional[str]:
    real = _patra_real(row, "children_status")
    if real is not None:
        if real in _CHILDREN_YES:
            return "yes"
        if real in _CHILDREN_NO:
            return "no"
        return None
    lk = _clean(row.get("life_kids"))
    if lk is not None:
        if lk in _CHILDREN_YES:
            return "yes"
        if lk in _CHILDREN_NO:
            return "no"
    return None


def _norm_optional(row: dict, col: str) -> Optional[str]:
    """health_status / financial_status — pass real value through, else None."""
    return _patra_real(row, col)


def _empty() -> dict:
    return {
        "career_stage":     None,
        "marital_status":   None,
        "children_status":  None,
        "health_status":    None,
        "financial_status": None,
        "has_context":      False,
    }


def _fetch_chart_row(chart_id: str, supabase) -> Optional[dict]:
    if not chart_id or supabase is None:
        return None
    cols = ("life_work,life_relationship,life_kids,career_stage,"
            "marital_status,children_status,health_status,financial_status")
    try:
        res = supabase.table("charts").select(cols).eq("id", chart_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:   # never let context lookup break a read
        print(f"[life_context] fetch failed chart={chart_id}: {e}")
    return None


# ── Public API ────────────────────────────────────────────────────────────────
def get_life_context(chart_id: Optional[str] = None, *,
                     chart_record: Optional[dict] = None,
                     supabase=None) -> dict:
    """
    Normalized, situation-aware life context for a chart.

    Pass `chart_record` when the surface already loaded the row (no extra
    DB round-trip). Otherwise pass `chart_id` + `supabase` to fetch it.

    Returns a dict with the canonical keys above and `has_context`. Never
    raises; absent dimensions are None and `has_context` is False.
    """
    row = chart_record if chart_record is not None else _fetch_chart_row(chart_id, supabase)
    if not row:
        return _empty()

    career    = _norm_career(row)
    marital   = _norm_marital(row)
    children  = _norm_children(row)
    health    = _norm_optional(row, "health_status")
    financial = _norm_optional(row, "financial_status")

    has = any(x is not None for x in (career, marital, children, health, financial))
    return {
        "career_stage":     career,
        "marital_status":   marital,
        "children_status":  children,
        "health_status":    health,
        "financial_status": financial,
        "has_context":      has,
    }


# ── Prompt-side rendering ─────────────────────────────────────────────────────
# These blocks are injected into the LLM context (prompt-side), NOT returned to
# the user. Downstream narration + output_strips scrub any jargon before the
# user sees anything, so house/domain guidance here is acceptable.

_CAREER_FRAMING = {
    "studying":         "They are studying / skill-building. Frame career as "
                        "learning, foundation, and 4th/5th-house skill growth — "
                        "NOT corporate-ladder advancement.",
    "job":              "They hold a job / are in employment. Frame career around "
                        "advancement, performance, and leadership within a role.",
    "running_business": "They are running a business that is not yet stable. "
                        "Money/career reads weight entrepreneurial framing "
                        "(8th/11th/7th); FUNDING is a first-class domain. Frame "
                        "around runway, customers, and capital — not salary.",
    "in_transition":    "They are between roles / in transition. Frame career "
                        "around the next step, openings, and re-direction.",
}
_MARITAL_FRAMING = {
    "single":       "They are single. Relationship reads are about meeting / "
                    "approach and timing (7th-lord / Darakaraka) — finding, not "
                    "maintaining.",
    "relationship": "They are in a relationship, not married. Relationship reads "
                    "are about deepening commitment or the path to marriage — "
                    "never steer them toward seeking someone new.",
    "married":      "They are married. Relationship reads DEEPEN the partnership "
                    "(quality, the 7th) — never steer them toward seeking a new "
                    "partner.",
    "divorced":     "They are post-marital (divorced / separated / widowed). "
                    "Frame around independence and a possible new chapter — "
                    "gently, never assume they want to re-partner.",
}
_CHILDREN_FRAMING = {
    "yes": "They have (or are expecting) children. 5th-house reads relate to "
           "existing children and parenting, not the prospect of having them.",
    "no":  "They have no children. 5th-house reads are about creativity and "
           "open future — do not assume children are imminent.",
}


def life_context_to_prompt_block(lc: dict) -> str:
    """
    Render the life context as an LLM instruction block. Returns "" when there
    is no context (so the surface produces a clean situation-neutral read).
    """
    if not lc or not lc.get("has_context"):
        return ""

    lines = ["=== LIFE CONTEXT — make this read specific to THIS person's situation ==="]
    if lc.get("career_stage"):
        lines.append("- " + _CAREER_FRAMING[lc["career_stage"]])
    if lc.get("marital_status"):
        lines.append("- " + _MARITAL_FRAMING[lc["marital_status"]])
    if lc.get("children_status"):
        lines.append("- " + _CHILDREN_FRAMING[lc["children_status"]])
    if lc.get("health_status"):
        lines.append(f"- Health context present: {lc['health_status']}. Acknowledge "
                     "energy/wellbeing where relevant.")
    if lc.get("financial_status"):
        fin = str(lc["financial_status"]).lower()
        if any(t in fin for t in ("debt", "struggl", "tight", "broke", "loss",
                                  "crisis", "deuda", "apret")):
            lines.append(
                "- MONEY IS TIGHT and there is DEBT. Read the 6th house as a live "
                "condition, not an abstraction. Two hard rules follow. "
                "(1) NEVER prescribe a remedy that costs money — no gemstones, no "
                "yantras to buy, no paid rituals, no donations framed as an "
                "obligation. Recommending a stone to someone servicing debt is "
                "the single fastest way to lose their trust, and it is advice "
                "that makes their situation worse. Use free remedies only: "
                "mantra, fasting, timing, discipline, service. "
                "(2) Do not suggest investing, lending, expanding or large "
                "purchases. Frame money reads around recovery, cashflow, "
                "renegotiation and staying solvent — not growth."
            )
        else:
            lines.append(f"- Financial context: {lc['financial_status']}. Let it shape "
                         "how bold the money advice is allowed to be.")
    lines.append("HONESTY: situation sharpens framing and domain choice only. It does "
                 "NOT license dated event claims — stay humble on exact timing.")
    lines.append("=== END LIFE CONTEXT ===")
    return "\n".join(lines)


# ── Noun-gating facts [life-context 2026-07-19] ─────────────────────────────

def resolve_life_facts(row: Optional[dict]) -> Optional[dict]:
    """
    Reduce a chart row to the tri-state facts the noun layer needs:
        {"partnered": True|False|None, "has_children": True|False|None}

    True/False mean KNOWN; None means we have no data and the caller must not
    infer anything. This is deliberately narrow — it exists to stop the reading
    calling someone's 7th house "your spouse" when they are single or divorced,
    which reads as the system not knowing them and discredits everything around
    it. It is not a general profile.

    "divorced" maps to partnered=False: the marriage is real history the chart
    may well be describing, but the present-tense noun "your spouse" is wrong.
    Returns None when nothing is known, so callers can skip gating entirely.
    """
    if not isinstance(row, dict):
        return None
    marital = _norm_marital(row)         # single|relationship|married|divorced|None
    children = _norm_children(row)       # yes|no|None

    partnered: Optional[bool]
    if marital in ("married", "relationship"):
        partnered = True
    elif marital in ("single", "divorced"):
        partnered = False
    else:
        partnered = None

    has_children: Optional[bool]
    if children == "yes":
        has_children = True
    elif children == "no":
        has_children = False
    else:
        has_children = None

    # employed: True = has an employer/boss, False = self-employed/business
    # owner, None = unknown. Gates "your boss" in the noun layer so we never
    # tell a business owner (or someone we know nothing about) about their boss.
    employed: Optional[bool] = None
    _cs = str((row.get("career_stage") or "")).strip().lower()
    _lw = str((row.get("life_work") or "")).strip().lower()
    _prof = str((row.get("profession") or "")).strip().lower()
    if (_cs in ("entrepreneur", "self_employed", "founder", "business_owner")
            or _lw in ("business", "entrepreneur", "self_employed")
            or _prof in ("founder", "business", "entrepreneur", "self-employed",
                         "business owner", "ceo")):
        employed = False
    elif _cs in ("early_career", "mid_career", "senior_career", "corporate",
                 "employed", "professional"):
        employed = True

    # Always return the dict (even all-None): the employed gate must fire on
    # UNKNOWN employment too — "your boss" is only apt when employed is known-
    # true. partnered/children gates still only trigger on explicit False, so
    # returning all-None never over-gates them. Callers that look for known
    # facts check specific keys `is not None`, so an all-None dict is safe.
    return {"partnered": partnered, "has_children": has_children,
            "employed": employed,
            "marital": marital, "children": children}
