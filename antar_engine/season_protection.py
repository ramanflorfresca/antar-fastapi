"""
antar_engine/season_protection.py
"Protect this season" — the dedicated remedy section for the CURRENT malefic
pressure, gathered in one place. 2026-09-24

Owner's ask: the app diagnoses hard moments (This Year TAKE CARE, the daily
WHAT TO AVOID, a demanding dasha) but never prescribes the mitigation. Rather
than staple a remedy onto every diagnostic surface (the code rule is "Today
carries no remedy"), this gathers the remedies for what actually runs hard
RIGHT NOW into one honest section:

  • the VARSHPHAL layer — the ruler of the current solar-return year, if it is
    afflicted in the chart, and
  • the DASHA layer — any currently-active period lord that runs hard.

Framing rule (matches the whole product): these SOFTEN the season — they never
avert a guaranteed event. A remedy tied to a "certain" bad event would double-
claim (the event is fated AND the cure works); we make neither claim. Each card
leads with a plain BEHAVIOURAL steadying step, then offers the classical
material/observance layer for those who want it. The narrator rule holds: no
planet, house, sign or Sanskrit reaches the user — only the life area and the
plain act.

Deterministic; never raises; returns {available: False} when nothing runs hard
enough to need protecting (a genuinely clear season needs no remedy).
"""
from __future__ import annotations

from typing import Optional

try:
    from antar_engine.material_advice import (
        _house_lords_from_lagna, _affliction_and_support, _material,
        _next_birthday_iso,
    )
except Exception:  # pragma: no cover - engine must degrade, never crash the app
    def _house_lords_from_lagna(_s): return {}
    def _affliction_and_support(*a, **k): return 0.0, 0.0, "", ""
    def _material(_p): return {"color": "", "gem": "", "metal": ""}
    def _next_birthday_iso(_b): return ""

try:
    from antar_engine.relationships import _house_of
except Exception:
    def _house_of(_p, _pl): return None

# What life area a house stands for — plain language, no house numbers reach the user.
_HOUSE_AREA = {
    1:  "your own footing and vitality",
    2:  "money and family",
    3:  "your day-to-day efforts and communication",
    4:  "home, family, and your peace of mind",
    5:  "children, creative work, and anything speculative",
    6:  "health, debts, and conflicts",
    7:  "partnership and close relationships",
    8:  "sudden change, shared money, and upheaval",
    9:  "luck, mentors, and belief",
    10: "career and reputation",
    11: "income, gains, and your network",
    12: "expenses, rest, and things quietly slipping away",
}

# Plain BEHAVIOURAL steadying step per graha — the primary, non-superstitious lever.
_STEADY = {
    "Sun":     "Ease off proving a point — clashes with people in authority cost the most now; lead by steadiness, not by winning the argument.",
    "Moon":    "Protect your rest and your mood — don't make big calls on a low day, and keep the people close to you close.",
    "Mars":    "Cool the temper before it costs you — hold back on conflict, sharp words, and rushed risks this stretch.",
    "Mercury": "Slow your words and re-read the details — double-check messages, contracts, and numbers before you send or sign.",
    "Jupiter": "Don't over-extend or over-promise — be honest about your limits and skip the too-optimistic bet.",
    "Venus":   "Keep spending and indulgence in check, and tend your relationships gently rather than avoiding them.",
    "Saturn":  "Move slower and finish what's half-done — don't force timelines or push against authority; patience is the remedy.",
    "Rahu":    "Avoid shortcuts and too-good-to-be-true offers — keep your dealings clean, documented, and above board.",
    "Ketu":    "Don't withdraw or drift — hold your routines and stay engaged, and let go of what is genuinely already ending.",
}

# Classical observance per graha — item/behaviour based, NEVER names the graha.
_OBSERVANCE = {
    "Sun":     "Offer water to the rising sun each morning, and give a little to elders or a father-figure cause.",
    "Moon":    "Keep a glass of water by your bed, offer water or milk, and look after your mother or an elder woman.",
    "Mars":    "Give sweets or donate to a cause on Tuesdays, and keep a calm, giving hand.",
    "Mercury": "Feed birds, give something green, and keep your commitments precise.",
    "Jupiter": "Give to a teacher, a student, or a place of learning or worship, and offer something yellow.",
    "Venus":   "Give to a woman in need or offer something white, and keep your home clean and pleasant.",
    "Saturn":  "Give to those in need on Saturdays — feed someone hungry or offer mustard oil; quiet service eases it most.",
    "Rahu":    "Give away something in dark colours and keep your word to someone who is counting on it.",
    "Ketu":    "Feed a dog or give quietly to the needy, and keep one small daily act of service.",
}


def _watch_area(planet: str, chart_data: dict, house_lords: dict) -> str:
    """The single life area under pressure from this graha — the dusthana it sits
    in if any, else the first meaningful house it rules. Plain language only."""
    pl = (chart_data.get("planets") or {})
    h = _house_of(planet, pl)
    if h in (6, 8, 12):
        return _HOUSE_AREA.get(h, "")
    lords = [hh for hh, L in (house_lords or {}).items() if L == planet]
    # prefer a "loud" house it rules (money/home/career/gains) over a neutral one
    for pref in (2, 4, 7, 10, 11, 5, 8, 6, 12):
        if pref in lords:
            return _HOUSE_AREA.get(pref, "")
    if h:
        return _HOUSE_AREA.get(h, "")
    return ""


def _affliction_card(planet: str, scope: str, window: str,
                     chart_data: dict, lk_data, house_lords) -> Optional[dict]:
    """Build one protection card for a graha that runs hard, or None if it's not
    actually afflicted enough to need protecting."""
    fav, avo, _fr, av = _affliction_and_support(planet, chart_data, lk_data, house_lords)
    # Only protect a genuine affliction — never manufacture a remedy for a clear planet.
    if not (avo >= 2.0 and avo >= fav):
        return None
    area = _watch_area(planet, chart_data, house_lords)
    mat = _material(planet)
    card = {
        "scope": scope,               # "This year" / "This chapter"
        "window": window or "",
        "under_pressure": area,       # plain life area
        "what_runs_hard": av or "runs harder than usual for you right now",
        "steady": _STEADY.get(planet, "Move a little slower and don't force the hard calls this stretch."),
        "observance": _OBSERVANCE.get(planet, ""),
        # material lever: AVOID amplifying the strained colour on what you wear.
        # Key is `shade` (not `color`) so the colour word localizes for es/pt —
        # the global i18n skip protects the key `color`. Mirrors material-year.
        "avoid_wearing": ({"shade": mat.get("color", ""), "why":
                           "don't amplify a strained area on what you wear this stretch"}
                          if mat.get("color") else None),
    }
    return card


def protect_this_season(chart_data: dict, birth_date, dashas: dict,
                        lk_data: Optional[dict] = None) -> dict:
    """The 'Protect this season' section. Gathers the varshphal-year and current-
    dasha afflictions that actually run hard, each with a plain steadying step and
    an optional classical observance. Empty (available False) on a clear season."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not (cd.get("planets") and lagna):
            return {"available": False}
        house_lords = _house_lords_from_lagna(lagna)

        cards = []
        seen = set()          # graha names already carded
        seen_areas = set()    # life areas already carded — no heading twice

        def _add(card):
            """Append a card unless its life area is already covered — two grahas
            can afflict the same area (e.g. both the 8th), and showing the same
            heading twice reads as a glitch. First (strongest-priority) wins; a
            card with no area is always kept."""
            if not card:
                return False
            area = (card.get("under_pressure") or "").strip().lower()
            if area and area in seen_areas:
                return False
            if area:
                seen_areas.add(area)
            cards.append(card)
            return True

        # ── VARSHPHAL layer: the ruler of the current solar-return year ──
        year_lord = None
        try:
            from antar_engine.lal_kitab_advanced import year_lord_for
            year_lord = year_lord_for(birth_date) if birth_date else None
        except Exception:
            year_lord = None
        _yr_window = ""
        if birth_date:
            _end = _next_birthday_iso(birth_date)
            if _end:
                _yr_window = f"through {_end}"
        if year_lord:
            c = _affliction_card(year_lord, "This year", _yr_window,
                                 cd, lk_data, house_lords)
            if _add(c):
                seen.add(str(year_lord).title())

        # ── DASHA layer: any currently-active period lord that runs hard ──
        try:
            from antar_engine.concern_engines import _current_dasha_lords
            active = _current_dasha_lords(dashas or {})
        except Exception:
            active = set()
        for lord in sorted(active):
            p = str(lord).title()
            if p in seen or p not in _STEADY:  # skip year-lord dup + chara signs
                continue
            c = _affliction_card(p, "This chapter", "", cd, lk_data, house_lords)
            _add(c)          # dedupes by area; keeps first per area
            seen.add(p)      # graha handled either way

        if not cards:
            # A genuinely clear season — say so honestly, offer no busy-work remedy.
            return {
                "available": True,
                "headline": "Protect this season",
                "clear": True,
                "intro": ("Nothing in your chart is running hard enough right now to need "
                          "protecting — this is a clear stretch. Keep your usual steady habits."),
                "cards": [],
                "note": "",
            }

        return {
            "available": True,
            "headline": "Protect this season",
            "clear": False,
            "intro": ("These soften the season — they don't undo it or guarantee an outcome. "
                      "Start with the steadying step; the traditional observance is there if "
                      "you want it. Small, steady, and entirely optional."),
            "cards": cards[:3],
            "note": ("A gemstone is the one potent lever here — never wear a stone you were "
                     "told to avoid, and set any stone with a qualified jeweller-astrologer."),
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
