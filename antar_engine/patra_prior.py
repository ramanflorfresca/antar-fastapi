"""
patra_prior.py — Layer B of the Today highlight selection: who this person is.

A quiet Bayesian-style prior on which life-domains are likely weighing on THIS
user, built ONLY from data already collected (no new onboarding step):

  1. BEHAVIOUR (strongest, most current): the domains of their recent Ask
     questions — explore questions from `intent_classify_log`, yes/no questions
     from `prashna_log`. Recent repeated topics outrank everything else here.
  2. STATED CONCERN (the baseline): `charts.signup_reason` — "why you came to
     Antar", written once by the frontend from onboarding. Used when behaviour
     is thin.
  3. LIFE-STAGE (gentle): age from birth_date via the same stage boundaries as
     antar_engine/patra.py.

The output is a SOFT tilt dict {domain: weight} on the locked palette
(money / work / relationships / body / mind). today_highlight.py caps each
domain's tilt at 1.0 and treats it as weighting only — it can never override
the chart-reality layer (C) or manufacture a highlight on its own.

Every external read is fail-open: missing tables, missing columns, empty
history all degrade to {} (or a partial tilt) without raising. The user never
sees the word "patra" and nothing in this module produces user-facing text.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional

# Behaviour beats baseline: the most-asked recent domain gets the biggest tilt.
W_BEHAVIOR_TOP = 0.8
W_BEHAVIOR_SECOND = 0.4
W_BASELINE = 0.5          # stated signup concern (split across compound reasons)
W_LIFESTAGE = 0.25        # gentle, never decisive
BEHAVIOR_LOOKBACK_DAYS = 30
BEHAVIOR_MIN_ASKS = 2     # fewer than this and the baseline stays in charge

# ── taxonomy → locked selectable palette ────────────────────────────────────
# Intent/prashna/concern vocabularies collapse onto money/work/relationships/
# body/mind. Unmappable values (travel, general, ...) are skipped on purpose.
_DOMAIN_TO_SELECTABLE = {
    # money
    "finance": "money", "funding": "money", "wealth": "money", "money": "money",
    "property": "money", "speculation": "money", "loss": "money",
    # work
    "career": "work", "business": "work", "legal": "work", "work": "work",
    "job": "work", "promotion": "work",
    # relationships
    "relationship": "relationships", "relationships": "relationships",
    "marriage": "relationships", "love": "relationships",
    "divorce": "relationships", "children": "relationships",
    "family": "relationships", "compatibility": "relationships",
    # body
    "health": "body", "body": "body", "fitness": "body",
    # mind
    "education": "mind", "purpose": "mind", "spiritual": "mind",
    "growth": "mind", "mind": "mind", "clarity": "mind",
}

# signup_reason categories (frontend writes e.g. "career_money",
# "love_relationships") — substring → (domain, weight-share) pairs.
_REASON_KEYS = [
    ("career",   [("work", 1.0)]),
    ("money",    [("money", 1.0)]),
    ("financ",   [("money", 1.0)]),
    ("wealth",   [("money", 1.0)]),
    ("business", [("work", 1.0)]),
    ("love",     [("relationships", 1.0)]),
    ("relation", [("relationships", 1.0)]),
    ("marriage", [("relationships", 1.0)]),
    ("family",   [("relationships", 1.0)]),
    ("children", [("relationships", 1.0)]),
    ("health",   [("body", 1.0)]),
    ("body",     [("body", 1.0)]),
    ("spirit",   [("mind", 1.0)]),
    ("growth",   [("mind", 1.0)]),
    ("purpose",  [("mind", 1.0)]),
    ("clarity",  [("mind", 1.0)]),
    ("direction", [("mind", 1.0)]),
]


def _norm(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None
    return _DOMAIN_TO_SELECTABLE.get(str(domain).strip().lower())


def _reason_tilt(signup_reason: Optional[str]) -> dict:
    """Stated concern -> baseline tilt. Compound reasons split W_BASELINE."""
    if not signup_reason:
        return {}
    s = str(signup_reason).strip().lower()
    hits = []
    for key, pairs in _REASON_KEYS:
        if key in s:
            for d, share in pairs:
                if d not in [h[0] for h in hits]:
                    hits.append((d, share))
    if not hits:
        return {}
    per = W_BASELINE if len(hits) == 1 else W_BASELINE * (1.0 / len(hits)) * 2.0
    per = min(per, W_BASELINE)
    return {d: per for d, _ in hits}


def _life_stage_tilt(birth_date: Optional[str]) -> dict:
    """Age → gentle domain lean. Same stage boundaries as patra.py."""
    try:
        bd = datetime.strptime(str(birth_date)[:10], "%Y-%m-%d")
    except Exception:
        return {}
    age = (datetime.now(timezone.utc).replace(tzinfo=None) - bd).days / 365.25
    if age < 25:        # formation: direction + first work
        return {"mind": W_LIFESTAGE, "work": W_LIFESTAGE}
    if age < 35:        # early householder: building career + bonds
        return {"work": W_LIFESTAGE, "money": W_LIFESTAGE, "relationships": W_LIFESTAGE * 0.6}
    if age < 50:        # householder/consolidation: money + work weight up
        return {"money": W_LIFESTAGE, "work": W_LIFESTAGE * 0.8}
    if age < 65:        # consolidation→vanaprastha: body + money
        return {"body": W_LIFESTAGE, "money": W_LIFESTAGE * 0.8}
    return {"body": W_LIFESTAGE, "mind": W_LIFESTAGE * 0.8}


def _behavior_counts(chart_id: str, sb) -> dict:
    """Domains of recent Ask questions, recency-weighted. Fail-open to {}."""
    counts: dict = {}
    since = (datetime.now(timezone.utc) - timedelta(days=BEHAVIOR_LOOKBACK_DAYS)).isoformat()

    def _add(domain, created_at):
        d = _norm(domain)
        if not d:
            return
        w = 1.0
        try:
            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - dt).days > 7:
                w = 0.5      # older than a week counts half
        except Exception:
            pass
        counts[d] = counts.get(d, 0.0) + w

    # Explore questions — the Haiku/keyword intent log.
    try:
        r = sb.table("intent_classify_log") \
            .select("haiku_domain, keyword_domain, created_at") \
            .eq("chart_id", chart_id).gte("created_at", since) \
            .order("created_at", desc=True).limit(20).execute()
        for row in (r.data or []):
            _add(row.get("haiku_domain") or row.get("keyword_domain"), row.get("created_at"))
    except Exception:
        pass     # table may not exist yet — fail open

    # Yes/No questions — prashna log.
    try:
        r = sb.table("prashna_log") \
            .select("domain, created_at") \
            .eq("chart_id", chart_id).gte("created_at", since) \
            .order("created_at", desc=True).limit(10).execute()
        for row in (r.data or []):
            _add(row.get("domain"), row.get("created_at"))
    except Exception:
        pass

    return counts


def _stored_reason(chart_id: str, sb) -> Optional[str]:
    """charts.signup_reason — separate fail-open read so a missing column can
    never break the main daily-signal chart query."""
    try:
        r = sb.table("charts").select("signup_reason").eq("id", chart_id).limit(1).execute()
        if r.data:
            return r.data[0].get("signup_reason")
    except Exception:
        pass
    return None


def build_patra_tilt(chart_id: str, sb, birth_date: Optional[str] = None,
                     signup_reason: Optional[str] = None) -> dict:
    """Compose the Layer-B tilt. Soft weights only; today_highlight caps at 1.0.

    Behaviour beats baseline: when the user has BEHAVIOR_MIN_ASKS+ recent asks,
    their actual question domains take the big weights and the stated signup
    concern only tops up; with thin history the stated concern is the baseline.
    """
    tilt: dict = {}

    def _bump(d, w):
        if d and w > 0:
            tilt[d] = round(tilt.get(d, 0.0) + w, 3)

    # 1. behaviour
    counts = _behavior_counts(chart_id, sb) if (chart_id and sb is not None) else {}
    total_asks = sum(counts.values())
    if counts and total_asks >= BEHAVIOR_MIN_ASKS:
        ranked = sorted(counts, key=counts.get, reverse=True)
        _bump(ranked[0], W_BEHAVIOR_TOP)
        if len(ranked) > 1 and counts[ranked[1]] >= 1.0:
            _bump(ranked[1], W_BEHAVIOR_SECOND)

    # 2. stated concern (baseline)
    if signup_reason is None and chart_id and sb is not None:
        signup_reason = _stored_reason(chart_id, sb)
    for d, w in _reason_tilt(signup_reason).items():
        _bump(d, w)

    # 3. life stage (gentle)
    for d, w in _life_stage_tilt(birth_date).items():
        _bump(d, w)

    return tilt
