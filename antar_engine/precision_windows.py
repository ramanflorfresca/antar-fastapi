"""
antar_engine/precision_windows.py

Precision Window Engine
──────────────────────────────────────────────────────────────────────
WHAT THIS DOES:
  Takes a user's concern (career, marriage, wealth, health, legal...)
  and returns the TOP 3 SPECIFIC DATE WINDOWS in the next 12 months
  when that concern is most energetically supported.

  Each window has:
    - Start date + end date
    - Score (1-10 — how strong this window is)
    - Why this window is powerful (which layers are active)
    - Exactly what to do in this window
    - What to avoid

  This is what nobody else does. Every other app says "Jupiter is good
  for you this year." We say "March 15 – April 2 is your strongest
  career window. Score 9/10. Here is exactly what to do."

HOW SCORING WORKS:
  Each day is scored across 4 dimensions:

  Dimension 1 — Dasha Quality (0-3 points)
    Is the current Mahadasha planet favorable for this concern?
    Is the Antardasha planet favorable?
    Are they in mutual support?

  Dimension 2 — Transit Quality (0-3 points)
    Is Jupiter in a favorable house from lagna?
    Is Saturn moving away from Moon (Sade Sati ending)?
    Is the concern's karaka planet well-placed in transit?

  Dimension 3 — Yoga Activation (0-2 points)
    Is a relevant yoga being activated by current periods?

  Dimension 4 — Personal Pattern (0-2 points)
    Has this person historically had good results in this
    concern during similar dasha configurations?
    (Requires 3+ life events to activate)

  Max score: 10
  Threshold for showing: 6+

USAGE:
    from antar_engine.precision_windows import find_precision_windows

    windows = find_precision_windows(
        chart_data=chart_data,
        dashas=dashas,
        current_transits=current_transits,
        concern="career",
        detected_yogas=["Raja Yoga", "Dhana Yoga"],
        user_correlations=[],   # from supabase user_correlations table
        months_ahead=12,
    )
    # Returns list of PrecisionWindow dicts, top 3 by score
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional


# ── Sign reference ────────────────────────────────────────────────────────────

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# For each concern: which planets as MD/AD = favorable
CONCERN_FAVORABLE_PLANETS = {
    "career":        {"Jupiter", "Sun", "Mercury", "Mars", "Rahu"},
    "marriage":      {"Venus", "Jupiter", "Moon"},
    "wealth":        {"Jupiter", "Venus", "Mercury", "Rahu", "Sun"},
    "health":        {"Jupiter", "Moon", "Sun"},
    "legal":         {"Jupiter", "Mars", "Sun"},
    "children":      {"Jupiter", "Moon"},
    "property":      {"Mars", "Venus", "Moon"},
    "education":     {"Jupiter", "Mercury", "Moon"},
    "spirituality":  {"Jupiter", "Ketu", "Moon", "Saturn"},
    "foreign":       {"Rahu", "Jupiter", "Moon"},
    "business":      {"Mercury", "Jupiter", "Venus", "Rahu"},
    "relationships": {"Venus", "Jupiter", "Moon"},
    "general":       {"Jupiter", "Venus", "Mercury", "Sun"},
}

# Planets that suppress each concern
CONCERN_SUPPRESSOR_PLANETS = {
    "career":        {"Saturn", "Ketu"},
    "marriage":      {"Saturn", "Rahu", "Ketu"},
    "wealth":        {"Saturn", "Ketu"},
    "health":        {"Saturn", "Rahu", "Ketu", "Mars"},
    "legal":         {"Saturn"},
    "children":      {"Saturn", "Rahu", "Ketu"},
    "property":      {"Saturn", "Rahu"},
    "education":     {"Rahu", "Ketu"},
    "spirituality":  {"Rahu"},
    "foreign":       {"Saturn"},
    "business":      {"Saturn", "Ketu"},
    "relationships": {"Saturn", "Rahu"},
    "general":       {"Saturn", "Ketu"},
}

# Favorable transit houses for Jupiter (from lagna)
JUPITER_FAVORABLE_HOUSES = {1, 2, 5, 7, 9, 11}
JUPITER_UNFAVORABLE_HOUSES = {4, 6, 8, 12}

# What each window score means in human language
WINDOW_INTENSITY_LABELS = {
    (9, 10): ("exceptional", "This is the strongest window in your chart for the coming year. Rare alignment."),
    (7,  8): ("very_strong", "A powerful window. Multiple timing layers are supporting you simultaneously."),
    (6,  7): ("strong",      "A solid window. Timing is working in your favor here."),
    (5,  6): ("moderate",    "A reasonable window. Timing is neutral-to-favorable."),
    (0,  5): ("weak",        "Not an optimal window. Better windows are coming."),
}

DASHA_ENERGY_SHORT = {
    "Sun":     "Identity & Purpose",
    "Moon":    "Emotional Depth",
    "Mars":    "Action & Courage",
    "Mercury": "Intellect & Communication",
    "Jupiter": "Expansive Growth",
    "Venus":   "Heart & Beauty",
    "Saturn":  "Clarifying Pressure",
    "Rahu":    "Hungry Becoming",
    "Ketu":    "Releasing & Liberation",
}

# Yogas relevant to each concern
CONCERN_YOGAS = {
    "career":        ["Raja Yoga", "Ruchaka Yoga", "Sasa Yoga", "Bhadra Yoga"],
    "wealth":        ["Dhana Yoga", "Lakshmi Yoga", "Raja Yoga", "Hamsa Yoga"],
    "marriage":      ["Malavya Yoga"],
    "health":        ["Hamsa Yoga"],
    "spirituality":  ["Hamsa Yoga", "Viparita Raja Yoga"],
    "general":       ["Raja Yoga", "Dhana Yoga", "Lakshmi Yoga"],
    "business":      ["Dhana Yoga", "Bhadra Yoga", "Ruchaka Yoga"],
    "relationships": ["Malavya Yoga", "Raja Yoga"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt[:10])
        except:
            continue
    return datetime.utcnow()

def _sign_idx(sign: str) -> int:
    try:
        return SIGNS.index(sign)
    except ValueError:
        return 0

def _lord(sign: str) -> str:
    return SIGN_LORDS.get(sign, sign)

def _get_period_at_date(periods: list, target_date: datetime) -> Optional[dict]:
    """Get the active dasha period at a specific target date."""
    for p in periods:
        if _parse_dt(p["start"]) <= target_date <= _parse_dt(p["end"]):
            return p
    return None

def _get_antardasha_at_date(periods: list, target_date: datetime) -> Optional[dict]:
    """Get the active antardasha at a specific target date."""
    current_md = _get_period_at_date(periods, target_date)
    if not current_md:
        return None
    md_start = _parse_dt(current_md["start"])
    md_end   = _parse_dt(current_md["end"])
    sub = [
        p for p in periods
        if _parse_dt(p["start"]) >= md_start
        and _parse_dt(p["end"]) <= md_end
        and p["lord_or_sign"] != current_md["lord_or_sign"]
    ]
    for p in sub:
        if _parse_dt(p["start"]) <= target_date <= _parse_dt(p["end"]):
            return p
    return None

def _build_transit_map(current_transits: list) -> dict:
    transit_map = {}
    for t in current_transits:
        if isinstance(t, dict):
            p = t.get("planet", t.get("name", ""))
            s = t.get("current_sign", t.get("sign", t.get("transit_sign", "")))
            if p and s:
                transit_map[p] = s
    return transit_map

def _get_intensity_label(score: float) -> tuple:
    for (low, high), (label, description) in WINDOW_INTENSITY_LABELS.items():
        if low <= score <= high:
            return label, description
    return "moderate", "Timing is neutral."

def _format_date_range(start: datetime, end: datetime) -> str:
    if start.month == end.month:
        return f"{start.strftime('%B %d')}–{end.strftime('%d, %Y')}"
    return f"{start.strftime('%B %d')} – {end.strftime('%B %d, %Y')}"


# ══════════════════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _score_date(
    target_date: datetime,
    chart_data: dict,
    dashas: dict,
    transit_map: dict,
    concern: str,
    detected_yogas: list,
    user_correlations: list,
) -> tuple[float, list[str]]:
    """
    Score a specific date for a specific concern. Returns (score, reasons).
    Score is 0-10.
    """
    score = 0.0
    reasons = []
    lagna_sign = chart_data.get("lagna", {}).get("sign", "Aries")
    lagna_idx = _sign_idx(lagna_sign)
    moon_sign = chart_data.get("planets", {}).get("Moon", {}).get("sign", "Aries")
    moon_idx = _sign_idx(moon_sign)

    favorable = CONCERN_FAVORABLE_PLANETS.get(concern, set())
    suppressors = CONCERN_SUPPRESSOR_PLANETS.get(concern, set())

    # ── DIMENSION 1: Dasha Quality (0-3 points) ──────────────────────────

    vim = dashas.get("vimsottari", [])
    md = _get_period_at_date(vim, target_date)
    ad = _get_antardasha_at_date(vim, target_date)

    if md:
        md_planet = md["lord_or_sign"]
        if md_planet in favorable:
            score += 1.5
            reasons.append(f"{DASHA_ENERGY_SHORT.get(md_planet, md_planet)} chapter is active")
        elif md_planet in suppressors:
            score -= 0.5

    if ad:
        ad_planet = ad["lord_or_sign"]
        if ad_planet in favorable:
            score += 1.0
            reasons.append(f"{DASHA_ENERGY_SHORT.get(ad_planet, ad_planet)} sub-theme amplifies")
        elif ad_planet in suppressors:
            score -= 0.3

    # Mutual support bonus: both MD and AD are favorable
    if md and ad:
        md_p = md["lord_or_sign"]
        ad_p = ad["lord_or_sign"]
        if md_p in favorable and ad_p in favorable:
            score += 0.5
            reasons.append("double timing support — both major and sub-cycle aligned")

    # ── DIMENSION 2: Transit Quality (0-3 points) ──────────────────────

    jup_sign = transit_map.get("Jupiter", "")
    if jup_sign:
        jup_house = ((_sign_idx(jup_sign) - lagna_idx) % 12) + 1
        if jup_house in JUPITER_FAVORABLE_HOUSES:
            score += 1.5
            reasons.append(f"expansive growth energy in a favorable area of the chart")
        elif jup_house in JUPITER_UNFAVORABLE_HOUSES:
            score -= 0.5

    # Saturn position relative to Moon
    sat_sign = transit_map.get("Saturn", "")
    if sat_sign:
        sat_idx = _sign_idx(sat_sign)
        distance = (sat_idx - moon_idx) % 12
        if distance in [0, 1, 11]:  # Sade Sati
            score -= 0.5
        elif distance in [3, 7, 10]:  # Saturn trine/sextile Moon — supportive
            score += 0.3
            reasons.append("stabilizing pressure energy supports steady progress")

    # Karaka (significator) transit for this concern
    karakas = {
        "career":    "Sun",
        "marriage":  "Venus",
        "wealth":    "Jupiter",
        "children":  "Jupiter",
        "health":    "Sun",
        "property":  "Mars",
        "education": "Mercury",
        "spiritual": "Ketu",
    }
    karaka = karakas.get(concern, "Jupiter")
    karaka_sign = transit_map.get(karaka, "")
    if karaka_sign:
        karaka_house = ((_sign_idx(karaka_sign) - lagna_idx) % 12) + 1
        if karaka_house in [1, 2, 5, 9, 10, 11]:
            score += 0.5
            reasons.append(f"the natural significator of {concern} is well-placed in transit")

    # ── DIMENSION 3: Yoga Activation (0-2 points) ──────────────────────

    relevant_yogas = CONCERN_YOGAS.get(concern, [])
    active_relevant = [y for y in detected_yogas if y in relevant_yogas]

    if active_relevant:
        score += min(len(active_relevant) * 0.8, 1.5)
        yoga_names = " + ".join(active_relevant[:2])
        reasons.append(f"{yoga_names} — a natal pattern supporting {concern} is flowering")

    # ── DIMENSION 4: Personal Pattern (0-2 points) ─────────────────────

    if user_correlations and md:
        md_planet = md["lord_or_sign"] if md else ""
        for corr in user_correlations:
            # Check if this dasha period has historically been good for this concern
            if (corr.get("dasha_period") == md_planet and
                corr.get("event_type", "").lower().replace(" ", "_") in concern.lower()):
                pattern_score = min(corr.get("occurrences", 1) * 0.5, 1.5)
                score += pattern_score
                reasons.append(f"your personal history confirms: this timing has worked for you before")
                break

    return round(min(score, 10.0), 1), reasons


# ══════════════════════════════════════════════════════════════════════════════
# WINDOW CLUSTERING
# ══════════════════════════════════════════════════════════════════════════════

def _cluster_high_score_dates(
    daily_scores: list[tuple[datetime, float, list]],
    min_score: float = 6.0,
    gap_days: int = 7,
) -> list[dict]:
    """
    Takes daily scores and clusters consecutive high-score days into windows.
    Merges windows that are within gap_days of each other.
    Returns list of window dicts sorted by average score.
    """
    if not daily_scores:
        return []

    high_score_days = [(d, s, r) for d, s, r in daily_scores if s >= min_score]
    if not high_score_days:
        return []

    # Cluster consecutive days
    clusters = []
    current_cluster = [high_score_days[0]]

    for i in range(1, len(high_score_days)):
        prev_date = current_cluster[-1][0]
        curr_date = high_score_days[i][0]

        if (curr_date - prev_date).days <= gap_days:
            current_cluster.append(high_score_days[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [high_score_days[i]]

    clusters.append(current_cluster)

    # Convert clusters to window dicts
    windows = []
    for cluster in clusters:
        if not cluster:
            continue

        start_date = cluster[0][0]
        end_date = cluster[-1][0]
        avg_score = sum(s for _, s, _ in cluster) / len(cluster)
        peak_score = max(s for _, s, _ in cluster)

        # Get the most common reasons from the cluster
        all_reasons = []
        for _, _, reasons in cluster:
            all_reasons.extend(reasons)

        reason_counts = {}
        for r in all_reasons:
            reason_counts[r] = reason_counts.get(r, 0) + 1
        top_reasons = sorted(reason_counts, key=reason_counts.get, reverse=True)[:3]

        intensity_label, intensity_desc = _get_intensity_label(peak_score)

        windows.append({
            "start_date":      start_date,
            "end_date":        end_date,
            "date_range":      _format_date_range(start_date, end_date),
            "score":           round(peak_score, 1),
            "avg_score":       round(avg_score, 1),
            "duration_days":   (end_date - start_date).days + 1,
            "intensity":       intensity_label,
            "intensity_desc":  intensity_desc,
            "reasons":         top_reasons,
            "cluster_size":    len(cluster),
        })

    # Sort by score descending
    windows.sort(key=lambda x: x["score"], reverse=True)
    return windows


# ══════════════════════════════════════════════════════════════════════════════
# WHAT TO DO GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

CONCERN_WINDOW_ACTIONS = {
    "career": [
        "Apply for the position. Reach out to the contact. Send the proposal.",
        "Have the career conversation you have been postponing.",
        "Launch. Announce. Make the professional move that needs making.",
        "Negotiate. Ask for the raise, the promotion, the contract.",
    ],
    "wealth": [
        "Make the investment. Sign the financial agreement.",
        "Launch the revenue stream. Start the wealth-building action.",
        "Have the money conversation. Negotiate the deal.",
        "Review and restructure your financial foundations.",
    ],
    "marriage": [
        "Have the relationship conversation that matters.",
        "Deepen the commitment. Meet new people with intention.",
        "Say what you need to say to the person you love.",
        "Take the relationship to the next level.",
    ],
    "health": [
        "Begin the health protocol. Start the treatment.",
        "Make the appointment. Start the practice.",
        "Build the health habit that will last.",
        "Address the health concern you have been avoiding.",
    ],
    "legal": [
        "Push the legal matter forward. File. Engage.",
        "Have the legal conversation. Get the advice.",
        "Prepare your case and present it.",
        "Resolve the dispute. This window favors you.",
    ],
    "business": [
        "Launch the product. Sign the partnership. Make the business move.",
        "Secure the funding. Close the deal.",
        "Start the business. Register. Build.",
        "Expand. Hire. Scale.",
    ],
    "spirituality": [
        "Begin the practice. Commit to the retreat.",
        "Go deeper into your spiritual work.",
        "Make the pilgrimage. Sit with the teacher.",
        "Meditate daily. This window amplifies inner work.",
    ],
    "general": [
        "Act on your most important priority.",
        "Make the move you have been considering.",
        "Begin. The timing is supporting you.",
    ],
}

import random

def _generate_action_text(concern: str, window: dict) -> str:
    """Generate specific action text for a window based on concern and intensity."""
    actions = CONCERN_WINDOW_ACTIONS.get(concern, CONCERN_WINDOW_ACTIONS["general"])
    base_action = actions[hash(window["date_range"]) % len(actions)]

    reasons_text = ""
    if window["reasons"]:
        reasons_text = f" Why: {window['reasons'][0]}."

    return f"{base_action}{reasons_text}"


def _generate_avoid_text(concern: str, window: dict) -> str:
    """What to avoid during this window."""
    avoids = {
        "career":   "Avoid passive waiting. Don't let perfect be the enemy of good enough to start.",
        "wealth":   "Avoid speculation and impulsive financial decisions. Act on what is real.",
        "marriage": "Avoid ultimatums. Avoid making permanent decisions from temporary emotions.",
        "health":   "Avoid skipping the practice. Consistency in this window matters more than intensity.",
        "legal":    "Avoid aggressive posturing. Let facts and preparation do the work.",
        "business": "Avoid overextension. Focus on the most important move, not all moves.",
        "spiritual":"Avoid distraction. This window rewards singular focus on inner work.",
        "general":  "Avoid overthinking. Act from clarity, not from fear.",
    }
    return avoids.get(concern, avoids["general"])


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def find_precision_windows(
    chart_data: dict,
    dashas: dict,
    current_transits: list,
    concern: str = "general",
    detected_yogas: list = None,
    user_correlations: list = None,
    months_ahead: int = 12,
    top_n: int = 3,
) -> list[dict]:
    """
    Find the top N precision windows for a concern in the next months_ahead months.

    Returns list of window dicts, each containing:
        date_range     → "March 15–April 2, 2026"
        score          → 8.5 (out of 10)
        intensity      → "very_strong"
        intensity_desc → human description of the intensity
        reasons        → ["Jupiter expansion active", "double timing support"]
        what_to_do     → specific action text
        what_to_avoid  → what not to do
        duration_days  → 18
        window_label   → "Your Strongest Career Window"  (for the #1 window)
    """
    now = datetime.utcnow()
    detected_yogas = detected_yogas or []
    user_correlations = user_correlations or []
    transit_map = _build_transit_map(current_transits)

    # Score every day in the window
    daily_scores = []
    current_date = now

    for day_offset in range(months_ahead * 30):
        target_date = now + timedelta(days=day_offset)
        score, reasons = _score_date(
            target_date=target_date,
            chart_data=chart_data,
            dashas=dashas,
            transit_map=transit_map,
            concern=concern,
            detected_yogas=detected_yogas,
            user_correlations=user_correlations,
        )
        daily_scores.append((target_date, score, reasons))

    # Cluster into windows
    windows = _cluster_high_score_dates(daily_scores, min_score=5.5)

    # Take top N and enrich with action text
    top_windows = windows[:top_n]

    for i, window in enumerate(top_windows):
        window["what_to_do"]    = _generate_action_text(concern, window)
        window["what_to_avoid"] = _generate_avoid_text(concern, window)
        window["rank"]          = i + 1
        window["window_label"]  = (
            f"Your Strongest {concern.title()} Window" if i == 0
            else f"Second Window" if i == 1
            else f"Third Window"
        )

    return top_windows


def precision_windows_to_context_block(windows: list[dict], concern: str) -> str:
    """
    Convert precision windows to LLM context block.
    Injected into prompt_builder.py alongside other context.
    """
    if not windows:
        return ""

    lines = [f"═══ PRECISION TIMING WINDOWS — {concern.upper()} ═══"]

    for w in windows:
        lines += [
            f"[Window {w['rank']}: {w['date_range']} — Score {w['score']}/10]",
            f"Intensity: {w['intensity_desc']}",
            f"Why powerful: {'; '.join(w['reasons'][:2])}",
            f"Action: {w['what_to_do']}",
            f"Duration: {w['duration_days']} days",
            "",
        ]

    lines.append("═══ END PRECISION WINDOWS ═══")
    return "\n".join(lines)
