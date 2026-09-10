"""
antar_engine/daily_life_areas.py — [daily-life-map 2026-09-09]

The Today card was losing a "specificity" battle it was actually winning: our
reading is more grounded (personal geography, exact windows) but PRESENTED thin —
one or two areas, abstract lead, some jargon — while the competition maps the
user's WHOLE life head-to-toe in plain one-liners and therefore *feels* more
specific.

This turns the house_activation sweep (which already scores ALL ten life domains
with polarity + tone, ranked) into that comprehensive plain-language map — but
ordered by REAL activation (our moat), so we get their breadth AND our ranking.

Deterministic, zero-LLM, no jargon. Warm, plain, competition-legible labels +
one grounded line per area, keyed by (domain, band). Lead areas first.

Daily-only: monthly/yearly stay rank-and-suppress (a 10-area dump over a year is
noise; over a single day it's what people want).
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

# Warm, plain labels — the words a non-astrologer uses for their own life.
FRIENDLY_LABEL: Dict[str, str] = {
    "work":         "Work",
    "authority":    "Work & standing",
    "money":        "Your wallet",
    "speculation":  "Ventures & risk",
    "home":         "Rest & home",
    "travel":       "Getting around",
    "relationship": "Love & closeness",
    "family":       "Family",
    "health":       "Wellbeing",
    "spiritual":    "Inner life",
}

# One plain line per (domain, band). [predictive-voice 2026-09-10] These DESCRIBE
# what the day holds in each area (a forecast the user reads), NOT instructions —
# "the money strain presses in, spending rises" rather than "hold money still".
# The moves/watch layer on the card carries the advice; day_map is the prediction.
# Bands:
#   rise    — strong, clean opportunity (area is favored/opening)
#   caution — opportunity but flagged risky (mixed: upside with friction under it)
#   protect — genuine risk / adverse (area is strained / under pressure)
#   quiet   — neutral / nothing pulling (steady, even)
_LINES: Dict[str, Dict[str, str]] = {
    "work": {
        "rise":    "Your work is moving today — the effort you've put in is landing and being noticed.",
        "caution": "There's real momentum at work today, though it comes with a pull to take on too much.",
        "protect": "Work carries some drag today — support is slow and progress asks for patience.",
        "quiet":   "Work runs even today — steady and ordinary, nothing pulling hard either way.",
    },
    "authority": {
        "rise":    "Your standing is favored today — the people above you are receptive and doors are open.",
        "caution": "Your standing is rising today, but official matters carry a little friction alongside it.",
        "protect": "Official matters and paperwork press in today — support is slow and the weight is real.",
        "quiet":   "No pressure from above today — your reputation sits calm and steady.",
    },
    "money": {
        "rise":    "Money moves your way today — income and what you're owed flow in, and the strength is real.",
        "caution": "Money is active today — the income is strong, but spending rises right alongside it.",
        "protect": "The money strain presses in from more than one side today — spending is up and the flow feels tight.",
        "quiet":   "Your wallet is quiet today — nothing dramatic, the cushion holds steady.",
    },
    "speculation": {
        "rise":    "A venture or creative bet is lit today — the upside is genuinely live.",
        "caution": "A venture tempts today — the upside is real, but so is the downside sitting under it.",
        "protect": "Risk runs against you today — a creative or joint-money bet is prone to unravel.",
        "quiet":   "No strong pull toward risk today — the speculative side sits flat.",
    },
    "home": {
        "rise":    "Home feels warm today — comfort and a quieter ease settle in.",
        "caution": "Home brings small comforts today, though it asks for a lighter touch than usual.",
        "protect": "Your home base feels the strain today — rest runs short and the ground feels thin.",
        "quiet":   "Home is steady today — ordinary and running smoothly.",
    },
    "travel": {
        "rise":    "The road opens today — a trip or far-off matter moves in your favor.",
        "caution": "Short trips bring both ease and small snags today — the flow is mixed.",
        "protect": "Getting around is bumpy today — small journeys tend to carry small setbacks.",
        "quiet":   "Little movement today — things stay close and local.",
    },
    "relationship": {
        "rise":    "Warmth and good feeling are yours today — closeness comes easily.",
        "caution": "A close relationship is warm but tender today — feelings sit near the surface.",
        "protect": "Closeness feels friction today — small tensions catch more easily than usual.",
        "quiet":   "Connection is calm today — a warm word from someone close is likely.",
    },
    "family": {
        "rise":    "Family is a source of strength today — the ties hold and give back.",
        "caution": "Family ground is a little soft today — matters there ask for extra care.",
        "protect": "Family carries extra weight today — the timing on the harder matters is off.",
        "quiet":   "Family life is even today — small, ordinary care holds it together.",
    },
    "health": {
        "rise":    "Energy is on your side today — the body feels willing and strong.",
        "caution": "The body runs warm today — the vitality is there but it can tip into overdoing it.",
        "protect": "The body feels the strain today — energy runs low and rest feels thin.",
        "quiet":   "Wellbeing is steady today — the usual rhythm holds.",
    },
    "spiritual": {
        "rise":    "Your mind is clear today — thinking is sharp and settled.",
        "caution": "The inner weather is busy today — a little more noise in the head than usual.",
        "protect": "The mind feels crowded today — overthinking and noise press in.",
        "quiet":   "A settled inner day — quiet and even underneath.",
    },
}


def _band(dom: dict) -> str:
    """Map a scored domain to a line band using its polarity + caution + tone."""
    pol = (dom.get("polarity") or "neutral").lower()
    caution = bool(dom.get("caution"))
    try:
        tone = float(dom.get("tone") or 0.0)
    except (TypeError, ValueError):
        tone = 0.0
    if pol == "risk":
        return "protect"
    if pol == "opportunity":
        if caution:
            return "caution"
        return "rise" if tone > 0.4 else "caution" if tone < -0.1 else "rise"
    # neutral
    return "quiet"


def build_day_map(active_domains: Optional[list],
                  quiet_domains: Optional[list],
                  life_ctx: Optional[dict] = None,
                  max_areas: int = 6) -> List[dict]:
    """Return an ordered, plain-language 'your day, area by area' list:
      [{key, label, line, tone}] — lead (active/ranked) areas first, then the
    most-activated quiet ones, capped at max_areas.

    Only surfaces areas with a real signal: every active domain, plus quiet
    domains that have transit activity or a non-flat tone — so a truly dead area
    isn't padded in with filler."""
    active = list(active_domains or [])
    quiet = list(quiet_domains or [])

    # quiet areas worth showing: some transit activity or a leaning tone
    def _notable(q):
        try:
            tc = int(q.get("transit_count") or 0)
        except (TypeError, ValueError):
            tc = 0
        try:
            tone = abs(float(q.get("tone") or 0.0))
        except (TypeError, ValueError):
            tone = 0.0
        return tc > 0 or tone >= 1.0

    ordered = active + [q for q in quiet if _notable(q)]

    seen, out = set(), []
    for dom in ordered:
        key = (dom.get("key") or "").lower()
        if not key or key in seen or key not in _LINES:
            continue
        seen.add(key)
        line = _LINES[key].get(_band(dom)) or _LINES[key].get("quiet")
        out.append({
            "key":   key,
            "label": FRIENDLY_LABEL.get(key, (dom.get("label") or key).title()),
            "line":  line,
            "tone":  dom.get("polarity") or "neutral",
        })
        if len(out) >= max_areas:
            break
    return out
