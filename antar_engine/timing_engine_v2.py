"""
antar_engine/timing_engine_v2.py

Dasha Timing Engine — All Life Domains
──────────────────────────────────────────────────────────────────────
WHAT THIS FILE DOES:
  Given a life domain (legal, wealth, marriage, children, health...)
  and the user's dasha periods, finds:
    1. Which dasha periods are most relevant
    2. Whether a window is NOW / UPCOMING / PAST
    3. What specifically happens in that window
    4. How urgent it is

WHY THIS IS THE ANSWER TO "WHEN":
  Yogas answer CAN IT HAPPEN
  Timing answers WHEN

  Together: "Your Dhana Yoga is strong [can happen]
             AND you are entering Jupiter mahadasha in 2026 [when]
             → This is your primary wealth-building window.
                It opens in 14 months."

IMPORTANT:
  We use dasha_periods already stored in DB.
  No new calculations needed here.
  Just intelligent filtering and interpretation.
"""

from __future__ import annotations
from datetime import datetime
from antar_engine.d_charts_calculator import (
    get_house_lord, SIGN_INDEX, SIGNS, SIGN_LORDS
)


# ── Domain timing planet lists ────────────────────────────────────────────────
# For each domain: which planets, when active in dasha, signal that domain

DOMAIN_TIMING = {

    "wealth": {
        "house_lords":    [2, 9, 11],          # resolve to planets per chart
        "fixed_planets":  ["Jupiter", "Venus"],
        "amplifiers":     ["Rahu"],             # Rahu adds windfall quality
        "suppressors":    ["Saturn", "Ketu"],   # slow down / delay
        "planet_meanings": {
            "Jupiter": "The great expander — investments multiply, income grows organically, institutional wealth.",
            "Venus":   "Graceful abundance — luxury, aesthetics, and relationship-based prosperity flow.",
            "Rahu":    "Sudden unexpected gains — foreign money, disruptive business, windfall events.",
            "Sun":     "Authority-based income — salary, government, recognition bonuses.",
            "Mercury": "Business and intellectual income — consulting, trading, communication work.",
            "Moon":    "Public-facing income — variable but potentially large through popularity.",
        },
    },

    "billionaire": {
        "house_lords":   [1, 2, 9, 10, 11],
        "fixed_planets": ["Jupiter", "Rahu", "Sun"],
        "amplifiers":    ["Venus", "Mercury"],
        "suppressors":   ["Saturn", "Ketu"],
        "planet_meanings": {
            "Jupiter": "The mega-expansion period. Institutional support, compounding growth, trusted investor relationships.",
            "Rahu":    "Disruption creates empire. Foreign connections, unconventional strategies, rapid scaling.",
            "Sun":     "Authority and recognition peak. Leadership in a major institution or industry.",
        },
    },

    "funding": {
        "house_lords":   [2, 7, 11],
        "fixed_planets": ["Jupiter", "Rahu"],
        "amplifiers":    ["Mercury", "Venus"],
        "suppressors":   ["Saturn", "Ketu"],
        "planet_meanings": {
            "Jupiter": "Trust peak — investors believe in you. Institutional funding, angel rounds, credibility is highest.",
            "Rahu":    "Disruptive funding — VCs, foreign investors, crypto/tech money. Fast but volatile.",
            "Venus":   "Relationship-based funding — people invest in YOU, not just the idea. Personal brand matters.",
            "Mercury": "Smart money — investors trust your intellect and data. Good for seed rounds.",
        },
    },

    "legal": {
        "house_lords":   [6, 7],
        "fixed_planets": ["Jupiter", "Mars"],
        "amplifiers":    ["Sun"],
        "suppressors":   ["Saturn"],   # Saturn delays but eventually helps in 6th
        "planet_meanings": {
            "Jupiter": "Best period for legal resolution — justice prevails. Favorable judges. Win or favorable settlement.",
            "Mars":    "Active fighting period — engage fully. Don't back down. Energy and persistence are rewarded.",
            "Sun":     "Authority supports you. Government, official channels, senior people help the case.",
            "Saturn":  "Long, slow period — delays are likely. But Saturn in 6th eventually defeats enemies. Stay patient.",
            "Rahu":    "Unexpected turns — surprise evidence, unconventional strategy, or sudden reversal possible.",
            "6th_lord": "The case itself becomes most active — critical hearings, key developments.",
        },
    },

    "health": {
        "house_lords":   [1, 8],
        "fixed_planets": ["Jupiter", "Moon"],
        "amplifiers":    ["Sun"],
        "suppressors":   ["Saturn", "Rahu", "Ketu"],
        "planet_meanings": {
            "Jupiter": "Healing and recovery period. Best time for treatment, surgery, and restoration.",
            "Moon":    "Emotional healing and mental restoration. Mind-body work is most effective.",
            "Sun":     "Vitality peaks. Energy returns. Good period for physical strength building.",
            "Saturn":  "Chronic issues may surface. Long-term management required. Discipline in health habits rewarded.",
            "Rahu":    "Unusual or mysterious health events. Alternative medicine may help where conventional fails.",
            "Ketu":    "Past karmic health patterns surface. Spiritual healing and detachment from illness identity helps.",
        },
    },

    "marriage": {
        "house_lords":   [7, 2],
        "fixed_planets": ["Venus", "Jupiter"],
        "amplifiers":    ["Moon"],
        "suppressors":   ["Saturn", "Rahu"],
        "planet_meanings": {
            "Venus":   "Primary marriage window — highest probability of meeting and committing to a partner.",
            "Jupiter": "Expansion through relationship — marriage that brings growth and wisdom.",
            "Moon":    "Emotional readiness peaks — deep connection and genuine intimacy possible.",
            "7th_lord": "The partnership sector is activated — relationship events are most likely.",
            "Saturn":  "Serious, committed partnership — may feel heavy but is durable. Karmic relationship possible.",
        },
    },

    "children": {
        "house_lords":   [5, 9],
        "fixed_planets": ["Jupiter"],
        "amplifiers":    ["Moon", "Venus"],
        "suppressors":   ["Saturn", "Rahu"],
        "planet_meanings": {
            "Jupiter": "Strongest fertility and children window. The putrakaraka is active.",
            "Moon":    "Emotional readiness for parenthood. Nurturing energy at peak.",
            "Venus":   "Creation energy is high. Love and fertility combined.",
            "5th_lord": "The children house itself is activated — most significant conception window.",
        },
    },

    "property": {
        "house_lords":   [4, 12],
        "fixed_planets": ["Mars", "Saturn"],
        "amplifiers":    ["Jupiter", "Moon"],
        "suppressors":   ["Rahu"],
        "planet_meanings": {
            "Mars":    "Property acquisition energy — buying, building, and real estate action.",
            "Saturn":  "Long-term property holding — the right time to invest for the future.",
            "Jupiter": "Expansive home — upgrading, moving to a better place, expanding property.",
            "Moon":    "Emotional home — finding where you truly belong.",
            "4th_lord": "The home and property house is activated — moves, purchases, and changes.",
        },
    },

    "foreign": {
        "house_lords":   [9, 12],
        "fixed_planets": ["Rahu"],
        "amplifiers":    ["Jupiter", "Saturn"],
        "suppressors":   ["Moon", "Ketu"],
        "planet_meanings": {
            "Rahu":    "Foreign opportunity arrives. The pull toward abroad is strongest. Visas and international doors open.",
            "Jupiter": "Expansion through foreign lands — education, opportunity, wisdom gained abroad.",
            "Saturn":  "Long-term foreign settlement — building roots in a foreign country.",
            "12th_lord": "The foreign settlement house is activated — departure, immigration events.",
        },
    },

    "education": {
        "house_lords":   [4, 5, 9],
        "fixed_planets": ["Mercury", "Jupiter"],
        "amplifiers":    ["Moon"],
        "suppressors":   ["Rahu", "Saturn"],
        "planet_meanings": {
            "Mercury": "Peak learning and intellectual absorption. Best period for studies, exams, certifications.",
            "Jupiter": "Higher education and wisdom. University, research, and philosophy flourish.",
            "Moon":    "Memory and intuitive learning are strongest. Good for creative and arts education.",
            "5th_lord": "The learning and intelligence house is activated.",
        },
    },

    "career": {
        "house_lords":   [1, 10],
        "fixed_planets": ["Sun", "Saturn", "Mercury"],
        "amplifiers":    ["Jupiter", "Rahu"],
        "suppressors":   ["Moon", "Ketu"],
        "planet_meanings": {
            "Sun":     "Authority and recognition peak. Leadership roles and senior positions open.",
            "Saturn":  "Career foundation — slow build but permanent. Mastery is rewarded.",
            "Mercury": "Communication, business, and intellectual career peak.",
            "Jupiter": "Expansion, advisory roles, and career growth through wisdom.",
            "Rahu":    "Rapid unconventional rise — foreign opportunities, disruptive career moves.",
            "10th_lord": "The career house itself is activated — promotions, recognition, major professional events.",
        },
    },
}


# ── Core timing function ──────────────────────────────────────────────────────

def get_timing_windows(
    domain: str,
    dashas: dict,
    lagna_sign: str,
    limit: int = 6,
) -> list[dict]:
    """
    Main function. Returns timing windows for any life domain.

    Args:
        domain:     "wealth" | "legal" | "marriage" | "children" etc.
        dashas:     from get_dashas_for_chart() — already in DB
        lagna_sign: from chart_data["lagna"]["sign"]
        limit:      max windows to return

    Returns list of timing window dicts sorted by relevance.
    """
    config = DOMAIN_TIMING.get(domain, DOMAIN_TIMING["career"])

    # Resolve house lords to actual planets
    fixed  = set(config.get("fixed_planets", []))
    amp    = set(config.get("amplifiers", []))
    supp   = set(config.get("suppressors", []))

    for house_num in config.get("house_lords", []):
        planet_key = f"{house_num}th_lord"
        lord = get_house_lord(lagna_sign, house_num)
        fixed.add(lord)
        # Also add the generic key so meanings work
        config.setdefault("planet_meanings", {})[planet_key] = (
            config["planet_meanings"].get(planet_key, f"The {house_num}th house lord is activated")
        )

    now = datetime.utcnow()
    windows = []

    for period in dashas.get("vimsottari", [])[:20]:
        planet = period.get("lord_or_sign", "")
        if planet not in fixed and planet not in amp:
            continue

        start_str = period.get("start", "")
        end_str   = period.get("end", "")
        try:
            start_dt = datetime.strptime(start_str[:10], "%Y-%m-%d")
            end_dt   = datetime.strptime(end_str[:10], "%Y-%m-%d")
        except Exception:
            continue

        is_current = start_dt <= now <= end_dt
        is_past    = end_dt < now
        is_future  = start_dt > now
        years_away = round((start_dt - now).days / 365.25, 1) if is_future else 0
        years_left = round((end_dt - now).days / 365.25, 1) if is_current else 0
        is_suppressed = planet in supp

        # Quality rating
        if planet in fixed and not is_suppressed:
            quality = "primary"
        elif planet in amp:
            quality = "supporting"
        else:
            quality = "secondary"

        meaning = (
            config.get("planet_meanings", {}).get(planet) or
            f"{planet} dasha activates {domain} themes"
        )

        window = {
            "planet":       planet,
            "start":        start_str[:10],
            "end":          end_str[:10],
            "is_current":   is_current,
            "is_past":      is_past,
            "is_future":    is_future,
            "years_away":   years_away,
            "years_left":   years_left,
            "quality":      quality,
            "is_suppressed": is_suppressed,
            "meaning":      meaning,
            "urgency":      _get_urgency(is_current, years_away, quality),
            "action":       _get_action(domain, planet, is_current, is_future),
            "duration_years": round((end_dt - start_dt).days / 365.25, 1),
        }
        windows.append(window)

    # Sort: current > future (soonest first) > past
    windows.sort(key=lambda w: (
        0 if w["is_current"] else 1 if w["is_future"] else 2,
        w.get("years_away", 0)
    ))

    return windows[:limit]


def _get_urgency(is_current: bool, years_away: float, quality: str) -> str:
    if is_current:
        return "ACT NOW"
    if years_away <= 1:
        return "IMMINENT — prepare now"
    if years_away <= 3:
        return "APPROACHING"
    if years_away <= 7:
        return "BUILDING"
    return "LONG-TERM"


def _get_action(domain: str, planet: str, is_current: bool, is_future: bool) -> str:
    """What should the user actually DO during this window?"""
    actions = {
        "wealth": {
            "current":  "Invest aggressively. Expand income streams. Say yes to financial opportunities.",
            "upcoming": "Clear debts, improve credit, build the foundation. Prepare for the expansion window.",
        },
        "legal": {
            "current":  "Engage fully with the case. Don't settle prematurely. Push forward now.",
            "upcoming": "Gather evidence and build your legal team. The fighting window is coming.",
        },
        "marriage": {
            "current":  "Be open and available. The meeting is possible now. Say yes to social connections.",
            "upcoming": "Work on yourself and your availability. Clear old relationship patterns.",
        },
        "children": {
            "current":  "This is the conception window. Medical support aligned with this period has best results.",
            "upcoming": "Prepare physically and emotionally. The fertility window is approaching.",
        },
        "health": {
            "current":  "Begin treatment and healing practices now. The body is most receptive.",
            "upcoming": "Prepare for the healing window. Address underlying issues before it opens.",
        },
        "funding": {
            "current":  "Pitch aggressively. Send proposals. Meet investors. The trust is highest now.",
            "upcoming": "Build your network and refine your pitch. The funding window is approaching.",
        },
        "property": {
            "current":  "Look and commit. Property decisions made now tend to be good long-term.",
            "upcoming": "Save and prepare. The property window is coming.",
        },
    }
    timing = "current" if is_current else "upcoming"
    return actions.get(domain, {}).get(timing, "Focus on this area and take aligned action.")


# ── Summary builder ───────────────────────────────────────────────────────────

def build_timing_context(
    domain: str,
    windows: list[dict],
    yogas: list[dict],
) -> str:
    """
    Assemble timing data into a readable context block for the LLM.
    """
    active_yogas  = [y for y in yogas if y.get("present")]
    strong_yogas  = [y for y in active_yogas if y.get("strength") in ("strong","very strong")]
    current_windows = [w for w in windows if w["is_current"]]
    future_windows  = [w for w in windows if w["is_future"]]
    past_windows    = [w for w in windows if w["is_past"]]

    yoga_score = len(active_yogas) / max(len(yogas), 1)
    potential  = "high" if yoga_score >= 0.6 else "moderate" if yoga_score >= 0.4 else "limited"

    lines = [
        f"DOMAIN: {domain.upper()}",
        f"POTENTIAL: {potential.upper()} ({len(active_yogas)}/{len(yogas)} indicators present)",
        "",
    ]

    if strong_yogas:
        lines.append("STRONGEST INDICATORS:")
        for y in strong_yogas[:3]:
            lines.append(f"  ✓ {y['name']} [{y['strength']}]")
            lines.append(f"    {y['implication']}")
            lines.append(f"    Timing: {y.get('timing_note','')}")
        lines.append("")

    if current_windows:
        lines.append("⚡ ACTIVE NOW:")
        for w in current_windows:
            lines.append(f"  {w['planet']} period ({w['start']} → {w['end']}) — {w['years_left']}y remaining")
            lines.append(f"  → {w['meaning']}")
            lines.append(f"  → DO: {w['action']}")
        lines.append("")

    if future_windows:
        lines.append("UPCOMING WINDOWS:")
        for w in future_windows[:3]:
            lines.append(f"  {w['planet']} period ({w['start']} → {w['end']}) — opens in {w['years_away']}y [{w['urgency']}]")
            lines.append(f"  → {w['meaning']}")
        lines.append("")

    if not current_windows and not future_windows:
        lines.append("NOTE: No strong timing windows found in upcoming dashas.")
        lines.append("This may be a period of consolidation rather than peak activation.")
        lines.append("")

    lines.append(f"INSTRUCTION: Use the above to answer WHEN specifically.")
    lines.append("Give the user actual years. Be direct about whether this is NOW or FUTURE.")
    lines.append("If NOW: create urgency. If FUTURE: give prep advice.")

    return "\n".join(lines)
