"""
antar_engine/house_significations.py — the house → literal-noun layer.

THE GAP THIS CLOSES (user feedback, 2026-06-07): competitors translate an
activated house into LITERAL life-nouns (mother, boss, vehicle, loan / credit
card, service staff, partner, property); we stopped at abstract domain buckets
(work / body / money). Same chart input — one more translation step we skipped.

This is the single canonical map (consolidates the four scattered copies:
chart_context_builder.HOUSE_KARAKAS, proof_points.KEY_HOUSE_MEANINGS,
transit_alerts_engine.TRANSIT_HOUSE_MEANING, welcome_signal.HOUSE_MEANING).
It is shared by ALL FOUR period narrators (Today / Month / Year / Cycle) so
noun-level reads are the default everywhere, not an inconsistency.

GUARDRAILS BUILT IN (precision is the edge, not Barnum padding):
  * Naming a NOUN is naming a RESULT — that is the rule, not a violation. The
    house number and planet never leave this module; only the nouns do.
  * SELECTIVE: select_nouns() caps at 2-3 and prefers the domain-relevant
    subset, so a read names "a new loan or credit line" (6th in a money
    context) — not the 6th's entire signification list.
  * DIRECTION-AWARE: the same house reads opposite by polarity — 4th positive =
    "support from home / a property gain"; 4th adverse = "a home or vehicle
    expense / your mother may need care". select_phrase() carries that.

Internal module — output_strips + each narrator's _JARGON_RX still gate the
final user-facing text; these nouns are jargon-free by construction.
"""

from __future__ import annotations
from typing import Optional

# direction normalization: every caller's vocabulary → positive | adverse | any
_DIR = {
    "positive": "positive", "amplified": "positive", "favorable": "positive",
    "favourable": "positive", "good": "positive", "+": "positive",
    "adverse": "adverse", "caution": "adverse", "negative": "adverse",
    "difficult": "adverse", "challenging": "adverse", "-": "adverse",
}


def _norm_dir(direction: Optional[str]) -> str:
    return _DIR.get((direction or "").strip().lower(), "any")


# ── the table ────────────────────────────────────────────────────────────────
# Per house:
#   theme      — short plain life-area label (for the narrator's framing)
#   nouns      — literal nouns, ordered by everyday salience (the default pool)
#   by_domain  — domain-context refinements (which nouns matter in which read);
#                domain keys span BOTH vocabularies in use:
#                Today (money/work/relationships/body/mind) and
#                Month (wealth/career/home/learning/health/relationships/spiritual)
#   positive / adverse — ready direction-bound phrasings (a terse model still lands it)

HOUSE_SIGNIFICATIONS = {
    1: {
        "theme": "you yourself — body and energy",
        "nouns": ["your energy", "your health", "how you come across", "a fresh start"],
        "by_domain": {"body": ["your energy", "your health"],
                      "health": ["your energy", "your health"],
                      "mind": ["how you come across", "your sense of self"]},
        "positive": "strong vitality and a clear sense of yourself",
        "adverse": "low energy — pace yourself and protect your health",
    },
    2: {
        "theme": "savings, family and what you say",
        "nouns": ["your savings", "close family", "your words", "food and possessions"],
        "by_domain": {"money": ["your savings", "money you keep"],
                      "wealth": ["your savings", "money you keep"],
                      "relationships": ["close family"],
                      "mind": ["your words", "what you say"]},
        "positive": "money kept and warmth at home; your word carries weight",
        "adverse": "a drain on savings or a family tension — and guard your words",
    },
    3: {
        "theme": "effort, siblings and short trips",
        "nouns": ["a sibling", "a short trip", "your own effort", "messages and calls", "a skill"],
        "by_domain": {"work": ["your own effort", "a skill", "messages and calls"],
                      "career": ["your own effort", "a skill"],
                      "relationships": ["a sibling"]},
        "positive": "a bold move pays off; a sibling or a short trip helps",
        "adverse": "scattered effort or a sibling friction — focus narrowly",
    },
    4: {
        "theme": "home, mother and property",
        "nouns": ["your mother", "home or property", "a vehicle", "land", "peace of mind"],
        "by_domain": {"money": ["property", "a vehicle"],
                      "wealth": ["property", "a vehicle", "land"],
                      "home": ["home", "your mother", "a vehicle", "property"],
                      "relationships": ["your mother", "family at home"],
                      "body": ["rest at home", "peace of mind"],
                      "mind": ["peace of mind", "your foundations"]},
        "positive": "support from home; a property or vehicle gain",
        "adverse": "a home or vehicle expense, or your mother may need care",
    },
    5: {
        "theme": "children, creativity and romance",
        "nouns": ["a child", "a creative project", "romance", "studies", "an investment or bet"],
        "by_domain": {"money": ["an investment or bet (be careful)"],
                      "learning": ["studies", "a creative project"],
                      "relationships": ["romance", "a child"],
                      "mind": ["a creative project", "a new idea"]},
        "positive": "a creative win, good news about children, or romance",
        "adverse": "hold off on speculation; a child or project needs patience",
    },
    6: {
        "theme": "loans, daily work and health upkeep",
        "nouns": ["a loan or credit line", "debt", "the people who work for you",
                  "a dispute", "your daily routine", "health upkeep"],
        "by_domain": {"money": ["a new loan or credit line", "debt", "a credit card"],
                      "wealth": ["a loan or credit line", "debt"],
                      "work": ["the people who work for you", "a workplace dispute",
                               "your daily workload"],
                      "career": ["the people who work for you", "a workplace dispute"],
                      "body": ["your daily health routine"],
                      "health": ["your daily health routine", "a recurring complaint"]},
        "positive": "debt cleared, a dispute resolved, your routine paying off",
        "adverse": "review any new loan or credit line; watch a dispute and your health routine",
    },
    7: {
        "theme": "your partner and the deals you make",
        "nouns": ["your partner", "a business partner", "a deal or contract", "clients or the public"],
        "by_domain": {"relationships": ["your partner", "your spouse"],
                      "work": ["a business partner", "a deal or contract", "clients"],
                      "career": ["a business partner", "a contract", "clients"],
                      "money": ["a deal or contract"]},
        "positive": "a partnership strengthens or a deal comes together",
        "adverse": "a partnership strain — read any contract carefully before signing",
    },
    8: {
        "theme": "shared money and sudden change",
        "nouns": ["joint money", "an inheritance or settlement", "taxes or insurance",
                  "a sudden change", "something hidden"],
        "by_domain": {"money": ["joint money", "an inheritance or settlement",
                                 "taxes or insurance"],
                      "wealth": ["joint money", "an inheritance", "taxes"],
                      "body": ["a deeper health matter — get it checked"],
                      "health": ["a deeper health matter — get it checked"]},
        "positive": "a windfall, settlement, or money through someone else",
        "adverse": "a sudden expense or a hidden cost — keep a buffer",
    },
    9: {
        "theme": "father, fortune and the long view",
        "nouns": ["your father", "a long trip", "a mentor or teacher", "higher study", "your luck"],
        "by_domain": {"relationships": ["your father", "a mentor"],
                      "learning": ["higher study", "a teacher"],
                      "spiritual": ["your beliefs", "a teacher or guide"],
                      "work": ["a mentor", "a lucky break"]},
        "positive": "good fortune, a mentor's help, or a meaningful long trip",
        "adverse": "your father may need attention, or a belief gets tested",
    },
    10: {
        "theme": "career, your boss and reputation",
        "nouns": ["your boss", "your career", "your reputation", "an official or authority"],
        "by_domain": {"work": ["your boss", "a promotion", "your reputation"],
                      "career": ["your boss", "a promotion", "your standing",
                                 "an official or authority"],
                      "money": ["a raise or career income"],
                      "mind": ["your public standing"]},
        "positive": "your boss backs you; recognition or a real career step",
        "adverse": "friction with someone in authority — protect your reputation",
    },
    11: {
        "theme": "income, gains and your network",
        "nouns": ["income", "a gain or payout", "your network or friends",
                  "a goal reached", "an elder sibling"],
        "by_domain": {"money": ["income", "a gain or payout"],
                      "wealth": ["income", "a payout", "a goal reached"],
                      "work": ["your network", "a goal reached"],
                      "career": ["your network", "a goal reached"],
                      "relationships": ["a friend", "your network"]},
        "positive": "income arrives, a goal lands, or your network comes through",
        "adverse": "a friend or a goal may let you down — don't over-rely on either",
    },
    12: {
        "theme": "expenses, rest and letting go",
        "nouns": ["an expense", "a foreign matter or trip", "rest or retreat",
                  "letting something go", "a hospital or recovery"],
        "by_domain": {"money": ["an expense", "a foreign cost"],
                      "wealth": ["an expense", "money leaving quietly"],
                      "body": ["rest and recovery", "sleep"],
                      "health": ["rest and recovery"],
                      "spiritual": ["retreat", "quiet and letting go"],
                      "mind": ["quiet", "letting something go"]},
        "positive": "a restful reset or a worthwhile foreign opportunity",
        "adverse": "an unexpected expense or an energy leak — build in rest",
    },
}

# Best-effort house when only a domain bucket is known (no activated house in
# hand — e.g. Today's LK amplify/avoid path). Prefer the actually-activated
# house when the caller has one; this is the fallback only.
DOMAIN_PRIMARY_HOUSE = {
    "money": 11, "wealth": 11, "work": 10, "career": 10,
    "relationships": 7, "body": 1, "health": 1, "mind": 5,
    "home": 4, "learning": 5, "spiritual": 9,
}


# ── Life-context noun gating ────────────────────────────────────────────────
# A house is real regardless of circumstance, but the NOUN we use to name it
# is not. The 7th is always "partnership"; whether that reads as "your spouse"
# or "a business partner" depends entirely on who is reading.
#
# Telling a divorced, single reader that "a few disagreements with your spouse"
# are coming does not land as a near-miss — it proves the system doesn't know
# them, and every correct thing around it stops being believable. One wrong
# noun costs more trust than five right houses earn.
#
# Rule: suppress a noun only on KNOWN contradicting facts. Unknown never
# suppresses (same principle as event_gating.stage_factor) — with no data we
# fall back to the neutral noun rather than guessing at someone's private life.
_NOUN_REQUIRES = {
    "your spouse":  "partnered",
    "your partner": "partnered",
    "your wife":    "partnered",
    "your husband": "partnered",
    "romance":      "not_partnered_ok",   # fine for single; odd for married
    "a child":      "has_children",
    "your children": "has_children",
    # "your boss" assumes an employer. Only use it when we KNOW the reader is
    # employed — self-employed / business owners / unknown get the neutral 10th-
    # house nouns (reputation, work standing, an authority figure) instead.
    "your boss":    "employed",
    "the boss":     "employed",
    "your manager": "employed",
    "your employer": "employed",
}


def _life_allows(noun: str, life: Optional[dict]) -> bool:
    """False only when life context KNOWN-contradicts the noun."""
    if not life:
        return True
    req = _NOUN_REQUIRES.get(str(noun).strip().lower())
    if not req:
        return True
    if req == "partnered":
        # Known single / divorced / widowed and not currently partnered.
        if life.get("partnered") is False:
            return False
    elif req == "has_children":
        if life.get("has_children") is False:
            return False
    elif req == "not_partnered_ok":
        # "romance" is not wrong for a married reader, just less apt — allow.
        return True
    elif req == "employed":
        # only name "your boss" when employment is KNOWN-true; self-employed
        # (False) or unknown (None) fall back to the neutral 10th-house nouns.
        if life.get("employed") is not True:
            return False
    return True


def select_nouns(house: int, direction: Optional[str] = None,
                 domain: Optional[str] = None, limit: int = 3,
                 life: Optional[dict] = None) -> list:
    """The 2-3 literal nouns an activated house points to, domain-filtered.
    Caps at `limit` (default 3) — never the full signification list.

    `life` is an optional {partnered: bool|None, has_children: bool|None}
    from life_context. Nouns the reader's known circumstances contradict are
    dropped; if that empties a domain pool we fall back to the house's neutral
    nouns so the house still gets named, just not in the wrong words."""
    # [life-gate] when no explicit life dict is passed, fall back to the active
    # context (set by life-arc / other orchestrators). This makes EVERY noun
    # selection in a gated context respect the reader's known facts — no
    # hunting down each call site to thread `life=` through.
    if life is None:
        try:
            from antar_engine.life_context import active_life
            life = active_life()
        except Exception:
            life = None
    sig = HOUSE_SIGNIFICATIONS.get(house)
    if not sig:
        return []
    pool = None
    if domain:
        pool = sig.get("by_domain", {}).get(domain)
    if not pool:
        pool = sig.get("nouns", [])
    if life:
        gated = [n for n in pool if _life_allows(n, life)]
        if not gated:
            # Domain pool fully contradicted — fall back to the neutral list,
            # gated the same way, so the house is still named.
            gated = [n for n in sig.get("nouns", []) if _life_allows(n, life)]
        pool = gated or pool
    # de-dup, preserve order, cap
    seen, out = set(), []
    for n in pool:
        if n not in seen:
            seen.add(n)
            out.append(n)
        if len(out) >= max(1, limit):
            break
    return out


def select_phrase(house: int, direction: Optional[str] = None) -> str:
    """Ready direction-bound phrasing for the house (a terse model still lands)."""
    sig = HOUSE_SIGNIFICATIONS.get(house)
    if not sig:
        return ""
    d = _norm_dir(direction)
    if d == "positive":
        return sig.get("positive", "")
    if d == "adverse":
        return sig.get("adverse", "")
    # unknown direction: neutral theme statement
    return sig.get("theme", "")


def house_theme(house: int) -> str:
    return (HOUSE_SIGNIFICATIONS.get(house) or {}).get("theme", "")


def nouns_for_domain(domain: str, direction: Optional[str] = None,
                     limit: int = 3) -> dict:
    """When only a domain bucket is known: resolve to its primary house and
    return {house, theme, nouns, phrase}. Best-effort (see DOMAIN_PRIMARY_HOUSE)."""
    h = DOMAIN_PRIMARY_HOUSE.get((domain or "").lower())
    if not h:
        return {}
    return {
        "house": h,
        "theme": house_theme(h),
        "nouns": select_nouns(h, direction, domain, limit),
        "phrase": select_phrase(h, direction),
    }


def resolve_signal(house: Optional[int], domain: Optional[str],
                   direction: Optional[str] = None, limit: int = 3) -> dict:
    """Unified entry for narrators: prefer the ACTUALLY-activated house; fall
    back to the domain's primary house only when no house is in hand.
    Returns {house, theme, nouns, phrase} or {} if nothing resolvable."""
    if isinstance(house, int) and house in HOUSE_SIGNIFICATIONS:
        return {
            "house": house,
            "theme": house_theme(house),
            "nouns": select_nouns(house, direction, domain, limit),
            "phrase": select_phrase(house, direction),
        }
    if domain:
        return nouns_for_domain(domain, direction, limit)
    return {}
