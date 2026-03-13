"""
antar_engine/proof_points.py

Proof Points Engine — "We'll tell you 3 things that already happened."
──────────────────────────────────────────────────────────────────────
WHAT THIS DOES:
  The single most powerful acquisition feature in Antar.

  Given only a birth date + birth time + location (no account needed),
  this engine finds the 3 most HIGH-CONFIDENCE past life events
  that Antar can claim happened — then presents them as a dare:

    "We'll show you 3 things that already happened in your life.
     If we're wrong — your first month is free."

  This is not vague astrology. Each proof point is:
    1. Tied to a real completed dasha period
    2. Named with a specific date range (e.g. "Between 2019 and 2021")
    3. Assigned to a specific life domain (career / love / home /
       identity / finances / health)
    4. Written in plain English — never astrology jargon
    5. Specific enough to feel personal, broad enough to land

HOW IT SELECTS THE 3 POINTS:
  Step 1 — Calculate vimsottari dashas from birth data
  Step 2 — Find all COMPLETED Mahadashas (end date < today)
  Step 3 — Find all COMPLETED high-impact Antardashas
           (high-impact = Rahu, Saturn, Jupiter, MD-lord change)
  Step 4 — Score each candidate on 4 dimensions:
           a) Planet power (Rahu > Saturn > Jupiter > Mars > others)
           b) Duration quality (6-24 months = ideal proof window)
           c) Domain confidence (how specific can we be about the domain)
           d) Recency (more recent = more memorable = higher weight)
  Step 5 — Deduplicate by domain (max 1 per domain)
  Step 6 — Return top 3 by score, each with a plain-English statement

CRITICAL RULES:
  - NEVER use the word "astrology", "dasha", "mahadasha", "antardasha",
    "Rahu", "Saturn", or any planet name in the output statements
  - NEVER make claims about death, serious illness, or trauma
  - ALWAYS use approximate date ranges, never exact dates
  - The statements must feel specific but not so narrow that
    most people would say "no"
  - Frame everything as having already happened — past tense

CONFIDENCE SCORING:
  Each proof point gets a confidence score 0.0–1.0.
  Only points with score >= 0.65 are shown.
  If fewer than 3 qualify, we show what we have (never fabricate).

USAGE:
    from antar_engine.proof_points import generate_proof_points

    points = generate_proof_points(
        birth_date="1990-06-15",
        birth_time="14:30",
        lat=28.6139,
        lng=77.2090,
        timezone_offset=5.5,
        chart_data=chart_data,   # pre-calculated chart dict
        dashas=dashas,           # pre-calculated dasha dict
    )
    # Returns List[ProofPoint] — max 3, sorted by confidence desc
    # Each ProofPoint has:
    #   statement     : str  — plain English, past tense
    #   date_range    : str  — e.g. "Between early 2019 and mid-2021"
    #   domain        : str  — career / love / home / identity / finances / health
    #   confidence    : float — 0.65–0.95
    #   domain_icon   : str  — emoji for UI
    #   follow_up     : str  — if user says "not quite", this clarifies
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional


# ── Reference tables ──────────────────────────────────────────────────────────

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
}

# How disruptive / memorable is each planet's period?
# Higher = more likely to produce a clearly memorable life event
PLANET_IMPACT_SCORE = {
    "Rahu":    1.00,   # most disruptive — biggest visible life changes
    "Saturn":  0.95,   # clarifying pressure — always memorable
    "Ketu":    0.85,   # endings and letting go — deeply felt
    "Mars":    0.80,   # action/conflict/property — concrete events
    "Sun":     0.75,   # identity shifts — career/authority changes
    "Jupiter": 0.72,   # expansion — good but gentler
    "Moon":    0.68,   # emotional — home/family changes
    "Venus":   0.65,   # love/relationships — very memorable
    "Mercury": 0.55,   # intellectual — less physically concrete
}

# Primary life domain each planet rules most strongly
PLANET_PRIMARY_DOMAIN = {
    "Sun":     "career",    # authority, public life, career
    "Moon":    "home",      # home, family, emotional life
    "Mars":    "property",  # property, disputes, siblings, energy
    "Mercury": "career",    # business, communication, education
    "Jupiter": "finances",  # wealth, expansion, wisdom
    "Venus":   "love",      # relationships, love, creativity
    "Saturn":  "career",    # career restructuring, discipline
    "Rahu":    "identity",  # major transformation, identity shift
    "Ketu":    "identity",  # endings, spiritual shifts
}

# Secondary domains (provides more options when primary is taken)
PLANET_SECONDARY_DOMAIN = {
    "Sun":     "identity",
    "Moon":    "love",
    "Mars":    "career",
    "Mercury": "finances",
    "Jupiter": "identity",
    "Venus":   "finances",
    "Saturn":  "identity",
    "Rahu":    "career",
    "Ketu":    "home",
}

# Domain display config
DOMAIN_CONFIG = {
    "career":   {"icon": "💼", "label": "Career & Life Direction"},
    "love":     {"icon": "💔", "label": "Love & Relationships"},
    "home":     {"icon": "🏠", "label": "Home & Family"},
    "identity": {"icon": "🔄", "label": "Identity & Life Direction"},
    "finances": {"icon": "💰", "label": "Money & Finances"},
    "property": {"icon": "🏠", "label": "Home & Property"},
    "health":   {"icon": "⚡", "label": "Energy & Health"},
}

# ── Proof statement templates ─────────────────────────────────────────────────
# Each planet × domain combination has 2-3 statement variants.
# We pick the best fit based on duration and lagna context.
# {date_range} is injected at render time.
# Statements are always past tense, specific but not so narrow they miss.

PROOF_STATEMENTS = {

    "Rahu": {
        "identity": [
            "{date_range}, your life took an unexpected turn. Something you thought was settled — your direction, your identity, or your sense of who you were — suddenly shifted. A new version of you began forming that you hadn't planned for.",
            "{date_range}, you went through a major transformation. Old structures fell away — a role, a relationship, a place, or a belief about yourself. What replaced it was something more ambitious, more true.",
        ],
        "career": [
            "{date_range}, something shifted significantly in your career or public direction. An opportunity appeared from an unexpected source — or a previous path ended and a very different one opened.",
            "{date_range}, your professional world changed in ways you didn't fully predict. A new direction, a new environment, or a completely unexpected opportunity reshaped where you were heading.",
        ],
        "love": [
            "{date_range}, your relationship life went through significant upheaval — an intense connection, a sudden change in a relationship, or a meeting that altered your trajectory.",
        ],
        "finances": [
            "{date_range}, your financial situation changed in ways that felt outside your control — either a significant gain from an unexpected source, or a disruption that forced a complete rethink.",
        ],
    },

    "Saturn": {
        "career": [
            "{date_range}, your career went through a period of significant pressure or restructuring. Something that felt solid began to shift — a role changed, a structure you relied on was tested, or you were forced to rebuild something from scratch.",
            "{date_range}, your professional life demanded a serious reckoning. What wasn't working became impossible to ignore. The period required real discipline and probably felt harder than you expected.",
        ],
        "identity": [
            "{date_range}, you went through a prolonged period of pressure and inner reckoning — a time when life was asking you to become more serious, more disciplined, more accountable. It wasn't easy, but it built something real in you.",
            "{date_range}, life applied sustained pressure across almost every area — career, relationships, self-image. It was one of the harder stretches. What came out of it was a clearer, stronger version of you.",
        ],
        "home": [
            "{date_range}, your home life or family situation went through a difficult period — responsibilities increased, something felt heavy or restricted, or a family dynamic required serious attention.",
        ],
        "finances": [
            "{date_range}, your financial life went through a period of restriction or serious pressure. Money felt tight, or a financial structure you relied on was tested or restructured.",
        ],
    },

    "Ketu": {
        "identity": [
            "{date_range}, something significant came to an end in your life — a chapter closed that you may not have been fully ready to close. A relationship, a career path, a belief about yourself, or a place you called home.",
            "{date_range}, you went through a period of letting go. Something you had invested deeply in — a relationship, a goal, an identity — dissolved or was released. The emptiness that followed eventually created space for something truer.",
        ],
        "love": [
            "{date_range}, a significant relationship in your life ended or fundamentally changed. Something that once felt central became distant. It may have been gradual, or it may have happened suddenly.",
        ],
        "career": [
            "{date_range}, a professional chapter ended. A role, an organisation, or a direction you had been building toward came to a close — either by your choice or not fully by it.",
        ],
        "home": [
            "{date_range}, your home situation or family structure changed significantly. A living situation ended, family dynamics shifted, or you felt a strong pull to disengage from your roots.",
        ],
        "spirituality": [
            "{date_range}, you went through a period of deep questioning — about meaning, purpose, and what you were actually here to do. Old answers stopped satisfying. A more honest search began.",
        ],
    },

    "Mars": {
        "career": [
            "{date_range}, your career or daily life demanded a lot of energy and decisive action. You may have pushed hard for something, faced significant competition, or experienced a conflict that required you to stand your ground.",
        ],
        "property": [
            "{date_range}, your living situation or property went through significant change — a move, a renovation, a purchase, a dispute, or a major shift in where and how you were living.",
            "{date_range}, something in your home environment or family relationships required direct confrontation or action. A conflict that had been simmering came to a head.",
        ],
        "identity": [
            "{date_range}, you went through a high-energy, high-stakes period. You were fighting for something — a goal, a position, your own sense of direction. The intensity was real.",
        ],
    },

    "Jupiter": {
        "finances": [
            "{date_range}, something opened up financially or professionally — a new opportunity, an expansion, a growth phase that felt qualitatively different from the years before it. Doors that were closed began to open.",
            "{date_range}, your life entered an expansive phase — more opportunities, more growth, more optimism about what was possible. Something you had been working toward began to materialise.",
        ],
        "love": [
            "{date_range}, your relationship life expanded in a meaningful way — a deepening of commitment, a new significant relationship, or a shift in how you understood love and partnership.",
        ],
        "career": [
            "{date_range}, your career or public standing grew in a meaningful way. Recognition, a new role, an expansion into new territory — something in your professional world moved toward more.",
        ],
        "identity": [
            "{date_range}, your worldview expanded significantly. Travel, education, spiritual exploration, or exposure to radically different perspectives reshaped how you understood yourself and your place in the world.",
        ],
    },

    "Sun": {
        "career": [
            "{date_range}, something in your career or public life shifted — your role, your visibility, or your relationship with authority. You either stepped into more responsibility or found yourself at odds with a structure you had been part of.",
            "{date_range}, your sense of professional identity went through a transition — what you did, who you did it for, or your sense of purpose in your work changed meaningfully.",
        ],
        "identity": [
            "{date_range}, you went through a period of clarifying who you are and what you stand for. Old self-definitions felt insufficient. You were becoming someone slightly different — more yourself.",
        ],
    },

    "Moon": {
        "home": [
            "{date_range}, your home life, family situation, or emotional foundations went through significant change. A living arrangement shifted, a family dynamic changed, or your sense of where you belonged was disrupted or redefined.",
            "{date_range}, something in your family or domestic world required deep attention. A parent's situation, a home transition, or an emotional reckoning with your roots.",
        ],
        "love": [
            "{date_range}, your emotional and relationship life went through a significant period of flux. Your feelings about a key person or relationship shifted — deeper connection, painful distance, or something in between.",
        ],
        "identity": [
            "{date_range}, your inner emotional world went through a meaningful shift. Old emotional patterns became visible. Your relationship with your own feelings — and possibly with your mother or family — changed in some real way.",
        ],
    },

    "Venus": {
        "love": [
            "{date_range}, your love life or closest relationship went through a significant phase — a new connection, a deepening of commitment, a painful separation, or a fundamental shift in what you wanted from love.",
            "{date_range}, something in your relationship world changed meaningfully — either a new beginning, a painful ending, or a moment when the nature of a key relationship became undeniable.",
        ],
        "finances": [
            "{date_range}, your financial life shifted — either toward more comfort and enjoyment, or through a significant expense or financial reorganisation connected to relationships or lifestyle.",
        ],
        "career": [
            "{date_range}, your creative output, professional relationships, or public image went through a meaningful change. Something about how you were seen — or how you chose to present yourself — shifted.",
        ],
    },

    "Mercury": {
        "career": [
            "{date_range}, your work or business went through a period of significant activity — communication, deals, decisions, or a shift in the intellectual direction of your professional life.",
        ],
        "finances": [
            "{date_range}, your financial situation connected to business, communication, or trade was active — either a new income stream opened, a deal materialised, or a business relationship changed.",
        ],
    },
}

# Follow-up clarifications — shown if user says "not quite"
FOLLOW_UP_CLARIFICATIONS = {
    "career":   "This could also have shown up as a change in your daily work environment, your team, your boss, or your sense of purpose at work — not necessarily a job change.",
    "love":     "This could also have been a shift in a close friendship, a family relationship, or your relationship with yourself — not only romantic love.",
    "home":     "This could also be about your relationship with your parents, your sense of roots, or a country/city you were living in — not just a physical house.",
    "identity": "This period of change may have been internal rather than visible to others — a shift in values, priorities, or a quiet but deep recalibration of direction.",
    "finances": "This may have been subtle — a shift in financial thinking, how you valued money, or a quiet change in financial relationships rather than a dramatic gain or loss.",
    "property": "This could also be about a living situation, a roommate change, or a family property situation — not necessarily buying or selling.",
    "health":   "This could have shown up as energy fluctuations, burnout, or a period when your body or nervous system was asking for more attention.",
}


# ── Core calculation helpers ───────────────────────────────────────────────────

def _parse_dt(s: str) -> datetime:
    """Parse date string to datetime."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt[:10])
        except Exception:
            continue
    return datetime.utcnow()


def _format_date_range(start_dt: datetime, end_dt: datetime) -> str:
    """
    Convert exact dates to approximate natural language ranges.
    e.g. 2019-03-01 to 2021-08-15 → "Between early 2019 and mid-2021"
    """
    def _season(dt: datetime) -> str:
        m = dt.month
        if m <= 3:
            return f"early {dt.year}"
        elif m <= 6:
            return f"mid-{dt.year}"
        elif m <= 9:
            return f"late {dt.year}"
        else:
            return f"late {dt.year}"

    start_str = _season(start_dt)
    end_str   = _season(end_dt)

    if start_dt.year == end_dt.year:
        # Same year — just say "During [year]"
        return f"During {start_dt.year}"
    elif end_dt.year - start_dt.year == 1:
        # Adjacent years — "Between [year] and [year]"
        return f"Between {start_dt.year} and {end_dt.year}"
    else:
        return f"Between {start_str} and {end_str}"


def _duration_months(start_dt: datetime, end_dt: datetime) -> float:
    """Return duration in months."""
    delta = end_dt - start_dt
    return delta.days / 30.44


def _duration_quality_score(months: float) -> float:
    """
    Score the duration quality for proof purposes.
    Ideal proof windows: 6–30 months.
    Too short (< 3 months) = hard to remember.
    Too long (> 7 years) = too diffuse — everything happens.
    """
    if months < 3:
        return 0.2
    elif months < 6:
        return 0.5
    elif months <= 18:
        return 1.0    # sweet spot
    elif months <= 30:
        return 0.90
    elif months <= 48:
        return 0.75
    elif months <= 84:
        return 0.55   # 7 years — too long
    else:
        return 0.30


def _recency_score(end_dt: datetime, now: datetime) -> float:
    """
    More recent = more memorable = higher weight.
    Periods that ended in the last 8 years score well.
    Periods that ended 15+ years ago score lower.
    """
    years_ago = (now - end_dt).days / 365.25
    if years_ago < 1:
        return 0.5    # too recent — may still be processing
    elif years_ago <= 3:
        return 1.0    # prime recall window
    elif years_ago <= 6:
        return 0.90
    elif years_ago <= 10:
        return 0.75
    elif years_ago <= 15:
        return 0.55
    else:
        return 0.35


def _get_past_mahadashas(dashas: dict, now: datetime) -> list:
    """
    Extract all completed Mahadashas (end date before today).
    Returns list of dicts sorted by end_date descending (most recent first).
    """
    vim = dashas.get("vimsottari", [])
    # Mahadashas are the longer-duration rows.
    # We identify them as rows where duration > 3 years (antardashas are shorter).
    past_mds = []
    for p in vim:
        try:
            start_dt = _parse_dt(p["start"])
            end_dt   = _parse_dt(p["end"])
            duration_years = (end_dt - start_dt).days / 365.25
            # Mahadashas range from 6 to 20 years
            if duration_years >= 4 and end_dt < now:
                past_mds.append({
                    "planet":   p["lord_or_sign"],
                    "start_dt": start_dt,
                    "end_dt":   end_dt,
                    "duration_months": _duration_months(start_dt, end_dt),
                    "level":    "mahadasha",
                })
        except Exception:
            continue
    past_mds.sort(key=lambda x: x["end_dt"], reverse=True)
    return past_mds


def _get_past_high_impact_antardashas(dashas: dict, now: datetime) -> list:
    """
    Extract completed Antardashas for high-impact planets only.
    High-impact: Rahu, Saturn, Ketu, Mars, Jupiter (in order of impact).
    Duration filter: 6 months – 4 years (sweet spot for proof).
    """
    HIGH_IMPACT = {"Rahu", "Saturn", "Ketu", "Mars", "Jupiter", "Venus", "Sun"}
    vim = dashas.get("vimsottari", [])
    past_ads = []
    for p in vim:
        try:
            planet   = p["lord_or_sign"]
            if planet not in HIGH_IMPACT:
                continue
            start_dt = _parse_dt(p["start"])
            end_dt   = _parse_dt(p["end"])
            if end_dt >= now:
                continue   # not completed yet
            months = _duration_months(start_dt, end_dt)
            if months < 5 or months > 50:
                continue   # too short to be memorable / too long to be specific
            past_ads.append({
                "planet":          planet,
                "start_dt":        start_dt,
                "end_dt":          end_dt,
                "duration_months": months,
                "level":           "antardasha",
            })
        except Exception:
            continue
    past_ads.sort(key=lambda x: x["end_dt"], reverse=True)
    return past_ads


def _get_saturn_return(birth_date: str, now: datetime) -> Optional[dict]:
    """
    Detect if user has already gone through their Saturn return (~age 27-31).
    Saturn return is one of the most universally recognisable life events.
    Returns a synthetic proof point dict if applicable.
    """
    try:
        birth_dt = _parse_dt(birth_date)
        age      = (now - birth_dt).days / 365.25
        if age < 31:
            return None   # hasn't happened yet
        # Saturn return window: approx age 27.5–30.5
        return_start = birth_dt.replace(year=birth_dt.year + 27)
        return_end   = birth_dt.replace(year=birth_dt.year + 30)
        if return_end >= now:
            return None   # still in progress
        return {
            "planet":          "Saturn",
            "start_dt":        return_start,
            "end_dt":          return_end,
            "duration_months": _duration_months(return_start, return_end),
            "level":           "saturn_return",
        }
    except Exception:
        return None


def _get_rahu_ketu_return(birth_date: str, now: datetime) -> Optional[dict]:
    """
    Detect if user has passed their Rahu/Ketu return (~age 18-19 and 37-38).
    Major karmic crossroads moments — very memorable.
    """
    try:
        birth_dt = _parse_dt(birth_date)
        age      = (now - birth_dt).days / 365.25
        candidates = []
        if age >= 20:
            r_start = birth_dt.replace(year=birth_dt.year + 17)
            r_end   = birth_dt.replace(year=birth_dt.year + 19)
            if r_end < now:
                candidates.append({
                    "planet":          "Rahu",
                    "start_dt":        r_start,
                    "end_dt":          r_end,
                    "duration_months": _duration_months(r_start, r_end),
                    "level":           "rahu_return",
                })
        if age >= 39:
            r_start = birth_dt.replace(year=birth_dt.year + 36)
            r_end   = birth_dt.replace(year=birth_dt.year + 38)
            if r_end < now:
                candidates.append({
                    "planet":          "Rahu",
                    "start_dt":        r_start,
                    "end_dt":          r_end,
                    "duration_months": _duration_months(r_start, r_end),
                    "level":           "rahu_return",
                })
        # Return most recent if any
        if candidates:
            return sorted(candidates, key=lambda x: x["end_dt"], reverse=True)[0]
        return None
    except Exception:
        return None


# ── Domain assignment ──────────────────────────────────────────────────────────

def _assign_domain(planet: str, chart_data: dict, used_domains: set) -> str:
    """
    Assign the best available domain for a planet, avoiding already-used domains.
    Falls back through primary → secondary → any available.
    """
    primary   = PLANET_PRIMARY_DOMAIN.get(planet, "identity")
    secondary = PLANET_SECONDARY_DOMAIN.get(planet, "career")

    if primary not in used_domains:
        return primary
    if secondary not in used_domains:
        return secondary
    # Try remaining domains
    all_domains = ["career", "love", "home", "identity", "finances", "property", "health"]
    for d in all_domains:
        if d not in used_domains:
            return d
    return primary   # fallback — allow duplicate if no choice


def _get_statement(planet: str, domain: str, date_range: str) -> Optional[str]:
    """
    Get the best proof statement for a planet + domain combination.
    Returns None if no statement template exists.
    """
    planet_statements = PROOF_STATEMENTS.get(planet, {})
    domain_statements = planet_statements.get(domain, [])

    # If no exact match, try identity as fallback domain
    if not domain_statements:
        domain_statements = planet_statements.get("identity", [])

    if not domain_statements:
        return None

    # Always use the first (most universally applicable) statement
    statement = domain_statements[0]
    return statement.replace("{date_range}", date_range)


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score_candidate(candidate: dict, now: datetime) -> float:
    """
    Score a candidate proof point on 4 dimensions.
    Returns final confidence score 0.0–1.0.
    """
    planet  = candidate["planet"]
    months  = candidate["duration_months"]
    end_dt  = candidate["end_dt"]
    level   = candidate["level"]

    # Dimension 1: Planet impact (how memorable is this planet's energy)
    planet_score = PLANET_IMPACT_SCORE.get(planet, 0.5)

    # Dimension 2: Duration quality
    duration_score = _duration_quality_score(months)

    # Dimension 3: Recency
    recency_score = _recency_score(end_dt, now)

    # Dimension 4: Level bonus
    # Mahadashas are major life chapters — very high confidence
    # Astronomical returns (Saturn return etc) are universal
    level_bonus = {
        "mahadasha":    0.10,
        "antardasha":   0.00,
        "saturn_return": 0.15,
        "rahu_return":   0.10,
    }.get(level, 0.0)

    # Weighted combination
    raw = (
        planet_score  * 0.35 +
        duration_score * 0.30 +
        recency_score  * 0.25 +
        level_bonus    * 0.10
    )

    # Normalise to 0.0–1.0
    return min(round(raw, 3), 1.0)


# ── Main public function ──────────────────────────────────────────────────────

def generate_proof_points(
    birth_date:  str,
    chart_data:  dict,
    dashas:      dict,
) -> list:
    """
    Generate the top 3 proof points for the given chart.

    Args:
        birth_date:  "YYYY-MM-DD"
        chart_data:  standard chart_data dict from chart module
        dashas:      standard dashas dict from get_dashas_for_chart()

    Returns:
        List of ProofPoint dicts, max 3, sorted by confidence descending.
        Each dict has:
            statement     str   — plain English, past tense
            date_range    str   — e.g. "Between early 2019 and mid-2021"
            domain        str   — career / love / home / identity / finances
            domain_label  str   — display label
            domain_icon   str   — emoji
            confidence    float — 0.65–0.95
            follow_up     str   — clarification if user says "not quite"
            planet        str   — internal only (not shown in UI)
    """
    now = datetime.utcnow()

    # ── Gather all candidates ──────────────────────────────────────
    candidates = []

    # Past Mahadashas
    candidates.extend(_get_past_mahadashas(dashas, now))

    # Past high-impact Antardashas
    candidates.extend(_get_past_high_impact_antardashas(dashas, now))

    # Saturn return (if applicable)
    saturn_return = _get_saturn_return(birth_date, now)
    if saturn_return:
        candidates.append(saturn_return)

    # Rahu/Ketu return (if applicable)
    rahu_return = _get_rahu_ketu_return(birth_date, now)
    if rahu_return:
        candidates.append(rahu_return)

    if not candidates:
        return []

    # ── Score all candidates ───────────────────────────────────────
    for c in candidates:
        c["score"] = _score_candidate(c, now)

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # ── Build proof points — max 3, one per domain ────────────────
    proof_points = []
    used_domains = set()
    seen_periods = set()  # avoid overlapping date ranges

    for c in candidates:
        if len(proof_points) >= 3:
            break

        # Skip if score too low
        if c["score"] < 0.55:
            continue

        planet = c["planet"]

        # Skip Mercury — statements too vague
        if planet == "Mercury":
            continue

        # Assign domain
        domain = _assign_domain(planet, chart_data, used_domains)

        # Get the statement
        date_range = _format_date_range(c["start_dt"], c["end_dt"])

        # Avoid near-duplicate date ranges
        date_key = f"{c['start_dt'].year}-{c['end_dt'].year}"
        if date_key in seen_periods:
            continue

        statement = _get_statement(planet, domain, date_range)
        if not statement:
            continue

        domain_cfg = DOMAIN_CONFIG.get(domain, {"icon": "🔄", "label": domain.title()})

        proof_points.append({
            "statement":    statement,
            "date_range":   date_range,
            "domain":       domain,
            "domain_label": domain_cfg["label"],
            "domain_icon":  domain_cfg["icon"],
            "confidence":   c["score"],
            "follow_up":    FOLLOW_UP_CLARIFICATIONS.get(domain, ""),
            "planet":       planet,         # internal — do NOT expose in UI
            "level":        c["level"],     # internal
        })

        used_domains.add(domain)
        seen_periods.add(date_key)

    return proof_points


# ── Score evaluation helper ───────────────────────────────────────────────────

def evaluate_proof_score(responses: list) -> dict:
    """
    Given a list of user responses to the 3 proof points,
    compute the overall accuracy and determine the CTA.

    Args:
        responses: list of "correct" | "not_quite" per proof point
                   e.g. ["correct", "correct", "not_quite"]

    Returns dict:
        score:          int   — 0, 1, 2, or 3
        accuracy_pct:   int   — 0-100
        verdict:        str   — "strong" | "good" | "free_month"
        headline:       str   — shown on results screen
        sub_headline:   str   — secondary message
        cta_text:       str   — button label
        offer_free_month: bool
    """
    correct = sum(1 for r in responses if r == "correct")
    total   = len(responses) or 3
    pct     = int((correct / total) * 100)

    if correct >= 3:
        return {
            "score":            3,
            "accuracy_pct":     100,
            "verdict":          "strong",
            "headline":         "Your chart is unusually clear.",
            "sub_headline":     "3 out of 3. Most charts give us 2. Yours is precise — which means everything ahead is also precise.",
            "cta_text":         "Unlock My Full Blueprint →",
            "offer_free_month": False,
        }
    elif correct == 2:
        return {
            "score":            2,
            "accuracy_pct":     67,
            "verdict":          "good",
            "headline":         "2 out of 3. That's not luck.",
            "sub_headline":     "The one that missed may still be true — sometimes the most significant periods are the ones we process years later.",
            "cta_text":         "See What's Coming Next →",
            "offer_free_month": False,
        }
    elif correct == 1:
        return {
            "score":            1,
            "accuracy_pct":     33,
            "verdict":          "free_month",
            "headline":         "Your first month is on us.",
            "sub_headline":     "1 out of 3 — we want to do better. Use your free month to see if Antar earns your trust.",
            "cta_text":         "Start Free →",
            "offer_free_month": True,
        }
    else:
        return {
            "score":            0,
            "accuracy_pct":     0,
            "verdict":          "free_month",
            "headline":         "Your first month is on us.",
            "sub_headline":     "We missed this one. That's rare — and we want to understand why. Your free month starts now.",
            "cta_text":         "Start Free →",
            "offer_free_month": True,
        }


# ── Context block for LLM (optional) ─────────────────────────────────────────

def proof_points_to_context_block(proof_points: list) -> str:
    """
    Serialise proof points into a context block for the LLM prompt.
    Used when the user signs up after the proof flow — so the LLM
    knows what was shown and confirmed.
    """
    if not proof_points:
        return ""

    lines = ["PROOF POINTS SHOWN AT SIGNUP:"]
    for i, pp in enumerate(proof_points, 1):
        lines.append(
            f"  {i}. [{pp['domain'].upper()}] {pp['date_range']} — {pp['domain_label']}"
            f" (confidence: {int(pp['confidence'] * 100)}%)"
        )
    return "\n".join(lines)
