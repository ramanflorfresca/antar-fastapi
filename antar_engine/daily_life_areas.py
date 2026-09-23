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

# One entry per (domain, band): a two-sided DESCRIPTION ("line") + a short,
# concrete MICRO-MOVE ("move"). [yoga-parity 2026-09-23] Benchmarked against a
# competitor whose daily reads more actionable because every area is a
# self-contained state -> honest tension -> "do X". So each line now carries the
# tension in-line (the honest "but"), and build_day_map appends the move to the
# TOP-RANKED areas only (see move_lead) — the lead areas read as actionable as
# theirs, without turning all six areas into a wall of instructions (the failure
# mode this map was built to avoid). Quiet areas carry no move (nothing to act on).
# Bands:
#   rise    — strong, clean opportunity (area is favored/opening)
#   caution — opportunity but flagged risky (mixed: upside with friction under it)
#   protect — genuine risk / adverse (area is strained / under pressure)
#   quiet   — neutral / nothing pulling (steady, even)
_LINES: Dict[str, Dict[str, Dict[str, str]]] = {
    "work": {
        "rise":    {"line": "Your work is moving today — the effort you've put in is landing and being noticed; the only real risk is taking on more than fits.", "move": "ride the momentum, but keep one thing you can drop."},
        "caution": {"line": "There's real momentum at work today, though it comes with a pull to take on too much.", "move": "push it forward, and promise less than you're tempted to."},
        "protect": {"line": "Work carries some drag today — support is slow and progress asks for patience; forcing it tends to backfire.", "move": "hold new commitments, and keep what you agree to reversible."},
        "quiet":   {"line": "Work runs even today — steady and ordinary, nothing pulling hard either way.", "move": ""},
    },
    "authority": {
        "rise":    {"line": "Your standing is favored today — the people above you are receptive and doors are open, so don't sit on the opening.", "move": "make the ask while the door's open."},
        "caution": {"line": "Your standing is rising today, but official matters carry a little friction alongside it.", "move": "advance the relationships today, not the paperwork."},
        "protect": {"line": "Official matters and paperwork press in today — support is slow and the weight is real.", "move": "don't sign or file anything final; let it wait."},
        "quiet":   {"line": "No pressure from above today — your reputation sits calm and steady.", "move": ""},
    },
    "money": {
        "rise":    {"line": "Money moves your way today — income and what you're owed flow in, and the strength is real; spending just tends to creep up right alongside it.", "move": "take the inflow, but keep a light eye on the outflow."},
        "caution": {"line": "Money is active today — the income is strong, but spending rises right alongside it.", "move": "let any big purchase wait a day."},
        "protect": {"line": "The money strain presses in from more than one side today — spending is up and the flow feels tight.", "move": "hold any big purchase or transfer; let money sit still."},
        "quiet":   {"line": "Your wallet is quiet today — nothing dramatic, the cushion holds steady.", "move": ""},
    },
    "speculation": {
        "rise":    {"line": "A venture or creative bet is lit today — the upside is genuinely live, but the downside doesn't go away with it.", "move": "take the bet small, with a hard stop set first."},
        "caution": {"line": "A venture tempts today — the upside is real, but so is the downside sitting under it.", "move": "cap the stake before you start, and walk at the line."},
        "protect": {"line": "Risk runs against you today — a creative or joint-money bet is prone to unravel.", "move": "sit this one out; it isn't your window."},
        "quiet":   {"line": "No strong pull toward risk today — the speculative side sits flat.", "move": ""},
    },
    "home": {
        "rise":    {"line": "Home feels warm today — comfort and a quieter ease settle in.", "move": "let yourself actually rest in it."},
        "caution": {"line": "Home brings small comforts today, though it asks for a lighter touch than usual.", "move": "go gentle on the household friction."},
        "protect": {"line": "Your home base feels the strain today — rest runs short and the ground feels thin.", "move": "protect your sleep, and lighten the load at home."},
        "quiet":   {"line": "Home is steady today — ordinary and running smoothly.", "move": ""},
    },
    "travel": {
        "rise":    {"line": "The road opens today — a trip or far-off matter moves in your favor.", "move": "make the move; the timing is with you."},
        "caution": {"line": "Short trips bring both ease and small snags today — the flow is mixed.", "move": "leave a little early, and keep the plan loose."},
        "protect": {"line": "Getting around is bumpy today — small journeys tend to carry small setbacks.", "move": "leave early and pad the schedule."},
        "quiet":   {"line": "Little movement today — things stay close and local.", "move": ""},
    },
    "relationship": {
        "rise":    {"line": "Warmth and good feeling are yours today — closeness comes easily.", "move": "say the warm thing; don't let it pass."},
        "caution": {"line": "A close relationship is warm but tender today — feelings sit near the surface.", "move": "lead with warmth, and skip the hard conversation."},
        "protect": {"line": "Closeness feels friction today — small tensions catch more easily than usual.", "move": "let the small stuff pass without comment."},
        "quiet":   {"line": "Connection is calm today — a warm word from someone close is likely.", "move": ""},
    },
    "family": {
        "rise":    {"line": "Family is a source of strength today — the ties hold and give back.", "move": "lean on them; let them show up for you."},
        "caution": {"line": "Family ground is a little soft today — matters there ask for extra care.", "move": "handle the family matter gently, not head-on."},
        "protect": {"line": "Family carries extra weight today — the timing on the harder matters is off.", "move": "postpone the hard family decision."},
        "quiet":   {"line": "Family life is even today — small, ordinary care holds it together.", "move": ""},
    },
    "health": {
        "rise":    {"line": "Energy is on your side today — the body feels willing and strong; the trap is spending all of it.", "move": "use it, but bank a little for tomorrow."},
        "caution": {"line": "The body runs warm today — the vitality is there but it can tip into overdoing it.", "move": "use the energy, but don't redline it."},
        "protect": {"line": "The body feels the strain today — energy runs low and rest feels thin.", "move": "keep meals simple, and rest before you're empty."},
        "quiet":   {"line": "Wellbeing is steady today — the usual rhythm holds.", "move": ""},
    },
    "spiritual": {
        "rise":    {"line": "Your mind is clear today — thinking is sharp and settled.", "move": "make the call that needs a clear head."},
        "caution": {"line": "The inner weather is busy today — a little more noise in the head than usual.", "move": "cut the inputs; take one thing at a time."},
        "protect": {"line": "The mind feels crowded today — overthinking and noise press in.", "move": "fewer inputs today; step away from the noise."},
        "quiet":   {"line": "A settled inner day — quiet and even underneath.", "move": ""},
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


def _compose(cell: dict, with_move: bool) -> str:
    """A day-map line: the two-sided description, plus the concrete micro-move as
    a trailing sentence when this is a lead (top-ranked) area and a move exists."""
    line = (cell or {}).get("line") or ""
    move = (cell or {}).get("move") or ""
    if with_move and move:
        move = move[0].upper() + move[1:]
        return f"{line} {move}"
    return line


def build_day_map(active_domains: Optional[list],
                  quiet_domains: Optional[list],
                  life_ctx: Optional[dict] = None,
                  max_areas: int = 6,
                  move_lead: int = 2) -> List[dict]:
    """Return an ordered, plain-language 'your day, area by area' list:
      [{key, label, line, tone}] — lead (active/ranked) areas first, then the
    most-activated quiet ones, capped at max_areas.

    The top `move_lead` areas carry a concrete micro-move appended to the line
    (so the lead reads as actionable as the competition); the rest stay pure
    description, so the card doesn't become a wall of instructions.

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
        cell = _LINES[key].get(_band(dom)) or _LINES[key].get("quiet")
        line = _compose(cell, with_move=len(out) < move_lead)
        out.append({
            "key":   key,
            "label": FRIENDLY_LABEL.get(key, (dom.get("label") or key).title()),
            "line":  line,
            "tone":  dom.get("polarity") or "neutral",
        })
        if len(out) >= max_areas:
            break
    return out
