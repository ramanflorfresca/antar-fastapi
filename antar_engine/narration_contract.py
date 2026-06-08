"""
narration_contract.py — Ask Narration Contract gate (measurement layer).

Scores any user-facing "read" string against the 4 contract rules from
ASK_NARRATION_CONTRACT_AUDIT_2026-06-07.md:

  R1. VERDICT FIRST     — sentence 1 leads with the answer (or honest
                          "reflective read" opener).
  R2. NAMED NOUNS       — at least 2 concrete life-nouns drawn from the
                          activated houses for the question's domain.
                          NOT abstract "energy / runway / vitality" words.
  R3. WINDOW            — a specific date, month, week, or quarter.
  R4. CONCRETE ACTION   — an imperative-verb action, NOT a trailing
                          reflective question.

Also surfaces project-rule-#12 violations (planet / sign / house# / Sanskrit
in user-facing prose), which the existing `output_strips` module strips but
does not measure.

Pure-Python, no I/O, no side effects — safe to import anywhere.

USAGE
-----

    from antar_engine.narration_contract import score_read, DOMAIN_HOUSES

    score = score_read(
        read=resp["read"],
        houses=DOMAIN_HOUSES["speculation"],   # or evidence-derived list
        next_step=resp.get("next"),
    )
    if not score["passes_contract"]:
        # log / re-prompt / fall through to template
        ...

Step 1 of the contract sprint: MEASUREMENT only. Step 5 wires it as a hard
gate with a re-prompt fallback (per founder rule, the fallback must NOT be a
generic template — that rebuilds the very problem we're solving).
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# ════════════════════════════════════════════════════════════════════════════
# 1. BANNED-ENERGY LEXICON
# ════════════════════════════════════════════════════════════════════════════
# The "all predictions are generic" disease lives in these words. They are
# the abstract domain/energy nouns that get used INSTEAD of concrete
# life-nouns. The contract is violated whenever a read leans on them.
#
# Founder list (from sprint brief): vitality, systems, foundations,
# infrastructure, energy, momentum, alignment, growth.
# Audit-derived additions: runway, capacity, structural, dynamic, channel,
# framework, support (abstract), potential, opportunity, breakthroughs.
#
# Some of these have legitimate concrete senses ("a structural beam",
# "growth chart") — the gate flags occurrences but the human reviewer judges
# context. Most prose hits in our 5 surfaces are the abstract sense.
BANNED_ENERGY_WORDS: frozenset[str] = frozenset({
    # founder spec
    "vitality", "systems", "foundations", "foundation",
    "infrastructure", "momentum", "alignment", "growth",
    # audit-derived
    "runway", "capacity", "structural", "structurally", "dynamic",
    "channel", "framework", "potential", "breakthroughs",
    # NOTE on context-dependent words: these are banned ONLY when bare
    # (no concrete noun head). Implemented in _BANNED_BARE below.
    # - "flow":  banned in "good flow today"; OK in "money flow favors you".
    # - "support": banned in "exceptional support"; OK in "his support".
    # - "opportunity/opportunities": banned in "stay open to opportunity";
    #     OK in "income opportunities" / "career opportunities".
    # - "energy": banned in "today's energy"; OK in the
    #     energy-translation idiom "your X and Y energy" (the rule-#12
    #     compliant planet-name replacement).
})

# Soft-banned: bare-noun ban — flagged ONLY when not preceded by a
# CONCRETE noun head. "Money flow" / "income opportunities" / "your
# discipline and patience energy" all pass. "The flow" / "potential
# opportunities" / "today's energy" all fail.
_BANNED_BARE: frozenset[str] = frozenset({
    "flow", "support", "opportunity", "opportunities", "energy",
})


# ════════════════════════════════════════════════════════════════════════════
# 2. PROJECT-RULE-#12 JARGON LEAK DETECTORS
# ════════════════════════════════════════════════════════════════════════════
# CLAUDE.md rule #12: "Zero Sanskrit or astrological jargon in any
# user-facing text." These regexes DETECT leaks; stripping is the job of
# antar_engine.output_strips.

_PLANETS_RE = re.compile(
    r"\b(Saturn|Mars|Jupiter|Venus|Mercury|Sun|Moon|Rahu|Ketu)\b",
    re.IGNORECASE,
)
_SIGNS_RE = re.compile(
    r"\b(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|"
    r"Sagittarius|Capricorn|Aquarius|Pisces)\b",
    re.IGNORECASE,
)
_HOUSE_NUM_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)\s+house\b|\bhouse\s+\d{1,2}\b",
    re.IGNORECASE,
)
# Sanskrit / Vedic technical terms that should never reach the user.
# "rising" + "ascendant" are included because year audit found "Capricorn
# rising" leaking through prose. "Kemadruma" appeared in /home lkRead.
_SKT_RE = re.compile(
    r"\b(dasha|antardasha|paryantar|mahadasha|nakshatra|rashi|lagna|"
    r"Kemadruma|chitta|graha|rising|ascendant|paryanta|"
    r"varshphal|mashaphal|tajika|navamsa|dashamsa|hora|karana)\b",
    re.IGNORECASE,
)

JARGON_PATTERNS: Dict[str, re.Pattern] = {
    "planet":    _PLANETS_RE,
    "sign":      _SIGNS_RE,
    "house_num": _HOUSE_NUM_RE,
    "skt":       _SKT_RE,
}


# ════════════════════════════════════════════════════════════════════════════
# 3. HOUSE → CONCRETE LIFE-NOUNS MAP
# ════════════════════════════════════════════════════════════════════════════
# The contract demands that activated houses translate to NAMED nouns the
# user recognizes — not "your wealth area" but "your savings", "a contract",
# "your mother". Derived from the worked example in the contract brief and
# from `project_house_noun_template_from_cycle` (the /life-arc diagnostic's
# noun template).
#
# Each list is ORDERED by how concrete/specific the noun is — most concrete
# first. The matcher scans for any occurrence in the read.
HOUSE_NOUNS: Dict[int, List[str]] = {
    # Each entry is a HEAD NOUN (or short head-noun phrase) — the matcher
    # looks for it as a substring of the lowercased read, so variants like
    # "hidden or higher-risk gains" still hit "gains". Keep entries SHORT
    # to maximize legitimate matches without false positives.
    1:  ["reputation", "appearance", "your name", "identity",
         "your body"],
    2:  ["savings", "income", "family money", "family wealth",
         "your voice", "spoken words", "food you eat"],
    3:  ["contract", "document", "siblings", "short trip",
         "courage", "an email", "your phone", "deal detail"],
    4:  ["your home", "property", "your car", "your vehicle",
         "your mother", "real estate", "where you live"],
    5:  ["children", "speculative bet", "creative project",
         "romance", "performance", "speculation",
         "a stock", "side bet"],
    6:  ["loan", "credit decision", "debts", "health routine",
         "daily routine", "competitor", "an enemy",
         "a doctor", "service work"],
    7:  ["partner", "spouse", "open enemy", "business deal",
         "contract", "counterpart", "a client"],
    8:  ["hidden gains", "higher-risk gains", "inheritance",
         "other people's money", "others' money", "investment",
         "a secret", "high-risk bet", "insurance", "windfall"],
    9:  ["mentor", "your father", "long-distance trip",
         "higher learning", "teacher", "court matter",
         "international travel", "publisher"],
    10: ["boss", "authority figure", "senior", "career",
         "public role", "your job", "promotion"],
    11: ["gains", "income from your network", "elder sibling",
         "social circle", "aspiration", "windfall payment",
         "check arriving"],
    12: ["foreign land", "expenses", "hospital stay",
         "your sleep", "retreat", "a loss", "hidden expense",
         "spiritual practice", "your bedroom"],
}


# ════════════════════════════════════════════════════════════════════════════
# 4. DOMAIN → ACTIVATED HOUSES (for /ask when no evidence block is passed)
# ════════════════════════════════════════════════════════════════════════════
# When a /ask call has no event-recipe evidence to draw houses from, the
# narrator can still pick nouns from the question's domain houses. This is
# the FALLBACK the contract requires: "still pull 2-3 nouns from the
# question's domain houses ... not a self-reflection prompt."
#
# Standard Jyotish house karakatwas — money lives in 2/11 (income/gains),
# 8 (other-people's money + risk), 5 (speculation/creativity).
DOMAIN_HOUSES: Dict[str, List[int]] = {
    "money":        [2, 11, 8, 5],
    "speculation":  [5, 8, 11, 2],
    "income":       [2, 11, 10, 6],
    "career":       [10, 6, 11, 2],
    "job":          [10, 6, 7],
    "relocation":   [4, 12, 3, 9],
    "travel":       [3, 9, 12],
    "love":         [7, 5, 4],
    "relationship": [7, 5, 4, 8],
    "marriage":     [7, 8, 2, 4],
    "family":       [4, 2, 3, 9],
    "children":     [5, 9, 2],
    "health":       [1, 6, 8, 12],
    "education":    [4, 5, 9, 2],
    "property":     [4, 12, 8],
    "lawsuit":      [6, 8, 9],
    "general":      [1, 10, 7, 4],
}


# ════════════════════════════════════════════════════════════════════════════
# 5. STRUCTURAL HEURISTICS
# ════════════════════════════════════════════════════════════════════════════

# Verdict-first openers. Order matters: more specific first.
# The contract allows: Yes / Likely / Not yet / "This is a reflective read"
# plus theme-first ("Money flow favors you today…", "Raman, this month …").
_VERDICT_OPENERS_RE = re.compile(
    r"^\s*("
    r"yes\b|no\b|likely\b|not\s*yet\b|maybe\b|"
    r"this\s+is\s+a\s+reflect(ion|ive)\b|"
    r"good\s+(for|day|time)\b|"
    r"bad\s+(for|day|time)\b|"
    r"today\b|tomorrow\b|this\s+week\b|this\s+month\b|this\s+year\b|"
    # Personalized salutation followed by clause:  "Raman, …" / "Raman: …"
    r"[A-Z][a-z]+[,:]\s"
    r")",
    re.IGNORECASE,
)

# Directional verbs anywhere in the first ~12 tokens that make a sentence
# a verdict even without a verdict-opener keyword. Example:
# "Money flow favors you today —" → "favors" is the directional verb.
_DIRECTIONAL_VERB_RE = re.compile(
    r"\b(favors?|supports?|rewards?|backs?|pushes?\s+back|blocks?|"
    r"helps?|hurts?|works?\s+for|works?\s+against|opens?|closes?|"
    r"tightens?|loosens?|amplif(?:y|ies)|delays?|protects?|"
    r"clears?|stalls?|stalls?|gates?|gives?|takes?\s+away)\b",
    re.IGNORECASE,
)

# Window patterns — dates, months, quarters, time-of-day, relative ranges.
_WINDOW_RE = re.compile(
    r"\b(?:"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
    r")[a-z]*\.?(?:\s+\d{1,2})?(?:[,\s]+\d{4})?\b|"
    r"\b\d{4}-\d{2}-\d{2}\b|"
    r"\b(?:today|tomorrow|tonight|this\s+(?:week|month|year|quarter)|"
    r"next\s+(?:\d+\s+)?(?:day|week|month|quarter|year)s?|"
    r"in\s+\d+\s+(?:day|week|month)s?|"
    r"week\s+of\s+\w+)\b|"
    r"\b(?:Q[1-4]|H[12]|first\s+half|second\s+half|"
    r"early|mid|late)\s+(?:\d{4}|\w+)\b|"
    r"\b(?:morning|afternoon|evening|midday|midnight|noon|"
    r"late\s+morning|early\s+morning|after\s+sunset)\b",
    re.IGNORECASE,
)

# Imperative-verb opener for concrete-action detection.
_IMPERATIVE_VERBS: frozenset[str] = frozenset({
    "ask", "avoid", "book", "call", "cancel", "check", "choose",
    "close", "commit", "delay", "do", "eat", "finish", "fix",
    "hold", "limit", "make", "meet", "move", "open", "pay",
    "pick", "postpone", "protect", "put", "review", "say", "schedule",
    "send", "sign", "sit", "sleep", "spend", "start", "stay",
    "stop", "take", "tell", "use", "verify", "wait", "walk",
    "write", "drop", "delete", "skip", "remove", "reach",
})

# Trailing-question detector — contract bans the closing reflective Q.
_TRAILING_Q_RE = re.compile(r"[?]\s*$")


# ════════════════════════════════════════════════════════════════════════════
# 6. SCORING FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def has_verdict_first(read: str) -> bool:
    """R1 — does sentence 1 lead with the answer?

    Two paths to pass:
      a) Explicit verdict opener:  Yes / Likely / Not yet / This is a
         reflective read / Today / Good for … / "Raman, …"
      b) Directional verb in sentence 1: "[X] favors/supports/blocks/…
         you" pattern carries the verdict implicitly.
    """
    if not read or not isinstance(read, str):
        return False
    s = read.lstrip()
    if _VERDICT_OPENERS_RE.match(s):
        return True
    # Sentence 1 = up to first '.'  (cap at 240 chars to avoid runaway)
    sent1 = s.split(".", 1)[0][:240]
    return bool(_DIRECTIONAL_VERB_RE.search(sent1))


def find_banned_energy(text: str) -> List[str]:
    """Return sorted unique banned-energy words found in text.

    A FAIL signal for R2: every banned-energy hit is a place the read
    chose abstraction over a named life-noun.

    Two-pass:
      pass A: hard-banned words (vitality, systems, energy, momentum, …)
      pass B: soft-banned bare-noun words (flow, support, opportunity) —
              flagged ONLY when the word stands alone (no concrete head
              modifier like "money flow" or "your support").
    """
    if not text or not isinstance(text, str):
        return []
    # Normalize possessives so "today's energy" tokenizes as
    # ["today", "energy"], not ["today", "s", "energy"] — otherwise
    # the "s" wrongly anchors "energy" as concrete.
    normalized = re.sub(r"'s\b", "", text)
    tokens = re.findall(r"\b[A-Za-z][a-z]+\b", normalized)
    low = [t.lower() for t in tokens]
    # Pass A: hard ban
    hits = {t for t in low if t in BANNED_ENERGY_WORDS}
    # Pass B: bare-noun ban — flagged when the word stands without a
    # concrete-noun modifier on its left. "Money flow" / "income
    # opportunities" / "your discipline and patience energy" all pass.
    # "The flow" / "today's energy" / "exceptional support" all fail.
    #
    # ABSTRACT_MODS = modifiers that DON'T anchor — articles, possessives,
    # generic adjectives, and other banned-energy words.
    _ABSTRACT_MODS = {
        "the", "an", "a", "your", "good", "bad", "open", "much",
        "more", "less", "exceptional", "great", "active", "strong",
        "weak", "high", "low", "this", "that", "some", "any",
        "little", "today", "tomorrow", "tonight", "yesterday",
        "now", "morning", "afternoon", "evening", "currently",
        "around",
    } | BANNED_ENERGY_WORDS
    # When previous token is a recognised concrete head, it ANCHORS the
    # bare word — pass. (Articles fall through to fail.)
    for i, w in enumerate(low):
        if w not in _BANNED_BARE:
            continue
        prev = low[i - 1] if i > 0 else ""
        # Special carve-out for energy-translation idiom: any
        # "[word1] and [word2] energy" form is the rule-#12 compliant
        # planet-name replacement and is NEVER a banned hit.
        if (w == "energy" and i >= 3
                and low[i - 2] == "and"
                and low[i - 1] not in _ABSTRACT_MODS):
            continue
        if prev and prev not in _ABSTRACT_MODS:
            continue
        hits.add(w)
    return sorted(hits)


def find_jargon_leaks(text: str) -> Dict[str, List[str]]:
    """Return per-category jargon hits (planet/sign/house_num/skt).

    Rule-#12 violation map. Empty dict = clean.
    """
    if not text or not isinstance(text, str):
        return {}
    out: Dict[str, List[str]] = {}
    for kind, pat in JARGON_PATTERNS.items():
        # findall on multi-group regexes returns tuples — flatten.
        raw = pat.findall(text)
        flat = []
        for r in raw:
            if isinstance(r, tuple):
                flat.extend([x for x in r if x])
            else:
                flat.append(r)
        if flat:
            out[kind] = sorted({h.strip() for h in flat if h.strip()})
    return out


def count_concrete_nouns(
    text: str,
    houses: List[int],
) -> Tuple[int, List[str]]:
    """R2 — count concrete life-nouns matching the activated houses.

    Returns (count, sorted_hits). Substring match on lowercased text;
    de-duplicated. Counts UNIQUE nouns, not occurrences — the contract
    wants 2-3 different nouns, not 3 mentions of the same one.
    """
    if not text or not houses or not isinstance(text, str):
        return (0, [])
    low = text.lower()
    candidates: List[str] = []
    for h in houses:
        candidates.extend(HOUSE_NOUNS.get(h, []))
    matched: List[str] = []
    seen: set[str] = set()
    for noun in candidates:
        nlow = noun.lower()
        if nlow in seen:
            continue
        if nlow in low:
            matched.append(noun)
            seen.add(nlow)
    return (len(matched), sorted(matched))


def has_window(text: str) -> bool:
    """R3 — does the text carry a specific date / window / time-of-day?"""
    if not text or not isinstance(text, str):
        return False
    return bool(_WINDOW_RE.search(text))


def has_concrete_action(text: str) -> bool:
    """R4 — imperative-verb action, NOT a trailing reflective question.

    Heuristic: text starts with an imperative verb (or contains an
    imperative sentence near the start) AND does not end in '?'.
    """
    if not text or not isinstance(text, str):
        return False
    stripped = text.strip()
    if _TRAILING_Q_RE.search(stripped):
        return False
    # First word of any sentence is an imperative verb.
    for chunk in re.split(r"[.!]\s+", stripped, maxsplit=3):
        m = re.match(r"\s*([A-Za-z]+)", chunk)
        if m and m.group(1).lower() in _IMPERATIVE_VERBS:
            return True
    return False


def score_read(
    read: str,
    houses: List[int],
    next_step: Optional[str] = None,
) -> Dict:
    """Score a single user-facing read against the 4-rule contract.

    Args:
        read:      The main user-facing narrative string (e.g. /ask `read`,
                   /home `today.gist`, /monthly-deepdive `overview`).
        houses:    Activated house numbers — from the evidence block when
                   available, else DOMAIN_HOUSES[domain_key].
        next_step: Optional separate "next action" field (e.g. /ask `next`,
                   /home `today.do`). Window + concrete-action checks scan
                   this in addition to `read`.

    Returns:
        Dict with per-rule booleans, leak surfaces, and `passes_contract`.
    """
    read = read or ""
    next_step = next_step or ""

    energy_leaks = find_banned_energy(read)
    jargon = find_jargon_leaks(read + " " + next_step)
    noun_count, noun_hits = count_concrete_nouns(read, houses)

    has_v = has_verdict_first(read)
    has_w = has_window(read) or has_window(next_step)
    # Action: prefer next_step if provided, fall through to read.
    has_a = (
        has_concrete_action(next_step) if next_step
        else has_concrete_action(read)
    )

    passes = bool(
        has_v
        and noun_count >= 2
        and has_w
        and has_a
        and not jargon  # rule-#12 violations also fail the contract
    )

    return {
        "verdict_first":     has_v,
        "noun_count":        noun_count,
        "nouns_found":       noun_hits,
        "window_present":    has_w,
        "concrete_action":   has_a,
        "energy_leaks":      energy_leaks,
        "jargon_leaks":      jargon,
        "passes_contract":   passes,
    }


def explain_failure(score: Dict) -> List[str]:
    """Human-readable list of why a score didn't pass. Empty if it passed."""
    if score.get("passes_contract"):
        return []
    reasons: List[str] = []
    if not score.get("verdict_first"):
        reasons.append("R1 fail: sentence 1 does not lead with verdict / theme.")
    n = score.get("noun_count", 0)
    if n < 2:
        reasons.append(
            f"R2 fail: only {n} concrete life-noun(s) from activated houses "
            f"(need 2+)."
        )
    if score.get("energy_leaks"):
        reasons.append(
            f"R2 weakness: banned-energy words present: "
            f"{', '.join(score['energy_leaks'])}."
        )
    if not score.get("window_present"):
        reasons.append("R3 fail: no specific window / date / time-of-day.")
    if not score.get("concrete_action"):
        reasons.append(
            "R4 fail: no concrete imperative action "
            "(or trailing reflective question)."
        )
    if score.get("jargon_leaks"):
        leak_summary = "; ".join(
            f"{k}={','.join(v)}" for k, v in score["jargon_leaks"].items()
        )
        reasons.append(f"Rule-#12 leak: {leak_summary}.")
    return reasons


# ════════════════════════════════════════════════════════════════════════════
# 7. CONCERN → NOUN PALETTE (for /ask reflective-mode noun injection)
# ════════════════════════════════════════════════════════════════════════════
# `detect_concern()` (predictions.py / concern_router.py) returns concerns
# like "finance", "career", "love", "domestic_move", "foreign_move". The
# gate's DOMAIN_HOUSES uses cleaner keys ("money", "career", "love",
# "relocation"). This bridge maps between them so the /ask reflective-
# mode prompt can pull a noun palette from the right houses.

_CONCERN_TO_DOMAIN: Dict[str, str] = {
    # finance family
    "finance":     "money",
    "funding":     "money",
    "wealth":      "money",
    "loss":        "money",
    "money":       "money",
    "speculation": "speculation",
    # career family
    "career":      "career",
    "business":    "career",
    "job":         "job",
    # relationship family
    "love":           "love",
    "marriage":       "marriage",
    "relationship":   "relationship",
    "divorce":        "relationship",
    "reconciliation": "relationship",
    "children":       "children",
    # location / property
    "domestic_move": "relocation",
    "foreign_move":  "relocation",
    "foreign":       "relocation",
    "property":      "property",
    # other domains
    "travel":     "travel",
    "health":     "health",
    "education":  "education",
    "legal":      "lawsuit",
    "lawsuit":    "lawsuit",
    # everything else falls through to "general"
    "spiritual":  "general",
    "general":    "general",
}


def concern_to_noun_palette(concern: str, k: int = 5) -> List[str]:
    """Map a /ask concern label to up to `k` concrete house-nouns.

    This is the noun palette fed to the /ask reflective-mode prompt:
    "you MUST name at least 2 of these in your read." The palette is
    drawn from DOMAIN_HOUSES[domain] → HOUSE_NOUNS[house], de-duplicated
    in house-priority order so the most domain-relevant nouns lead.

    Examples:
        >>> concern_to_noun_palette("speculation", k=4)
        ['children', 'speculative bet', 'creative project', 'romance']
        >>> concern_to_noun_palette("finance", k=4)
        ['savings', 'income', 'family money', 'family wealth']
        >>> concern_to_noun_palette("career", k=3)
        ['boss', 'authority figure', 'senior']
    """
    domain = _CONCERN_TO_DOMAIN.get((concern or "general").lower(), "general")
    houses = DOMAIN_HOUSES.get(domain, DOMAIN_HOUSES["general"])
    # Round-robin across the activated houses so a multi-house domain
    # like "love" (7,5,4) draws one noun from EACH before doubling up
    # on house 7 — otherwise we'd get all of house 7's nouns (partner,
    # spouse, OPEN ENEMY, BUSINESS DEAL) and drown the actual love
    # nouns from houses 5 + 4.
    palette: List[str] = []
    seen: set[str] = set()
    lists = [list(HOUSE_NOUNS.get(h, [])) for h in houses]
    max_len = max((len(lst) for lst in lists), default=0)
    for col in range(max_len):
        for lst in lists:
            if col >= len(lst):
                continue
            noun = lst[col]
            low = noun.lower()
            if low in seen:
                continue
            palette.append(noun)
            seen.add(low)
            if len(palette) >= k:
                return palette
    return palette


# ════════════════════════════════════════════════════════════════════════════
# 8. MODULE-LEVEL CONSTANTS EXPORT
# ════════════════════════════════════════════════════════════════════════════
__all__ = [
    "BANNED_ENERGY_WORDS",
    "JARGON_PATTERNS",
    "HOUSE_NOUNS",
    "DOMAIN_HOUSES",
    "has_verdict_first",
    "find_banned_energy",
    "find_jargon_leaks",
    "count_concrete_nouns",
    "has_window",
    "has_concrete_action",
    "score_read",
    "explain_failure",
    "concern_to_noun_palette",
]
