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

# One plain line per (domain, band). Bands:
#   rise    — strong, clean opportunity (lean in)
#   caution — opportunity but flagged risky (move, but keep a stop)
#   protect — genuine risk / adverse (protect more than push)
#   quiet   — neutral / nothing pulling (steady, no big moves)
_LINES: Dict[str, Dict[str, str]] = {
    "work": {
        "rise":    "Your effort is seen today — push the visible work and let it land.",
        "caution": "Momentum at work is real, but don't overcommit — move one clear step.",
        "protect": "Go steady at work today — protect your standing, avoid new commitments.",
        "quiet":   "Work is even today — routine effort carries you further than any big push.",
    },
    "authority": {
        "rise":    "A senior or decision-maker is receptive — make the ask, take the meeting.",
        "caution": "Standing is on the rise, but tread carefully with those above you.",
        "protect": "Handle authority and paperwork gently today — don't force a decision.",
        "quiet":   "No pressure from above today — a calm day for your reputation.",
    },
    "money": {
        "rise":    "Money flows your way today — chase what you're owed and lock in a gain.",
        "caution": "Income looks good, but keep a stop on any big spend or bet.",
        "protect": "Hold money still today — postpone big purchases and transfers.",
        "quiet":   "A quiet money day — tend the cushion, no dramatic moves needed.",
    },
    "speculation": {
        "rise":    "A venture or creative project is lit — back it, within limits.",
        "caution": "A venture tempts you today — real upside, real downside; cap your risk.",
        "protect": "Skip the gamble today — a creative or joint-money bet can unravel.",
        "quiet":   "No strong pull toward risk today — steady beats speculative.",
    },
    "home": {
        "rise":    "Home feels warm today — a good evening to settle and reset.",
        "caution": "Home needs a light touch today — small comforts over big changes.",
        "protect": "Guard your rest and home base today — settle for less, and that's okay.",
        "quiet":   "Home is steady today — ordinary care keeps it running smoothly.",
    },
    "travel": {
        "rise":    "The road opens today — a trip or far-off matter moves in your favor.",
        "caution": "A journey or foreign matter has upside and snags — build in a buffer.",
        "protect": "Keep trips short and simple today — small journeys can bring small snags.",
        "quiet":   "No big movement today — stay close, keep it local.",
    },
    "relationship": {
        "rise":    "Connection comes easy today — reach out, mend, or make the ask.",
        "caution": "A close relationship is warm but tender — listen more than you push.",
        "protect": "Go easy in close conversations today — let small frictions pass.",
        "quiet":   "A calm day for connection — a warm word from someone close is likely.",
    },
    "family": {
        "rise":    "Family is a source of strength today — lean on it, give a little back.",
        "caution": "Family ground is a bit soft today — step carefully, don't force decisions.",
        "protect": "Hold off on hard family talks today — the timing isn't with you.",
        "quiet":   "Family life is even today — small, ordinary care holds it together.",
    },
    "health": {
        "rise":    "Energy is on your side today — put it to good use.",
        "caution": "Your body's running warm today — keep it simple, don't overdo it.",
        "protect": "Your body feels the strain — slow down, breathe, guard your peace.",
        "quiet":   "Health is steady today — keep the habit, no heroics needed.",
    },
    "spiritual": {
        "rise":    "Your head is clear today — a good day to plan, reflect, or decide.",
        "caution": "Turn inward a little today — fewer inputs, clearer head.",
        "protect": "Protect your quiet today — noise and overthinking cost more than usual.",
        "quiet":   "A settled inner day — a little stillness goes a long way.",
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
