"""
antar_engine/predictions.py

Layered Confidence Prediction Engine
──────────────────────────────────────────────────────────────────────
Drop this file into your antar_engine/ folder.
Zero changes needed to existing code.

Data contracts (matches your existing main.py exactly):
  chart_data  → from supabase charts.chart_data
                lagna: { sign, sign_index, degree }
                planets: { Sun/Moon/etc: { sign, sign_index, degree,
                           nakshatra, nakshatra_lord, nakshatra_portion } }

  dashas      → from get_dashas_for_chart()
                { "jaimini": [...], "vimsottari": [...], "ashtottari": [...] }
                each item: { lord_or_sign, start, end, duration }

  transits    → from transits.calculate_transits()
                list of dicts with planet + current_sign

  life_events → from supabase life_events table
                list of { event_date, event_type, description }

──────────────────────────────────────────────────────────────────────
Layer 1 — Dasha timing windows       (confidence ~0.90, always shown)
Layer 2 — Dasha + transit confluence (confidence ~0.82, when 2+ align)
Layer 3 — Natal yoga activation      (confidence ~0.78, when yoga active)
Layer 4 — Personal life event mirror (confidence grows with data, YOUR MOAT)

CRITICAL RULE: No house numbers or planet names in user-facing text.
Translate everything to energy language. Every prediction answers:
  WHAT → WHY → WHAT IT MEANS → INVITATION → WINDOW

── v2 additions ──────────────────────────────────────────────────────
+ build_wow_fields()  → tldr, mission_checklist, trackable_predictions
  These three fields power the flywheel UI (TL;DR card, 90-day mission,
  prediction tracker). Called from build_layered_predictions() and
  appended to the return dict automatically.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from supabase import Client
import hashlib


# ── Sign / Planet reference tables ────────────────────────────────────────────

_SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

_SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

def _sign_idx(sign: str) -> int:
    try:
        return _SIGNS.index(sign)
    except ValueError:
        return 0

def _lord(sign: str) -> str:
    return _SIGN_LORDS.get(sign, sign)

def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt[:10])
        except:
            continue
    return datetime.utcnow()


# ── Energy Language — NEVER expose house numbers to user ──────────────────────

DASHA_ENERGY = {
    "Sun":     "a period of soul-level identity work — stepping into your own authority",
    "Moon":    "a deep emotional cycle — your inner world, home, and emotional foundations come alive",
    "Mars":    "a high-energy action period — courage and decisive action are your fuel",
    "Mercury": "an intellectual cycle — communication, business, and the power of your mind are highlighted",
    "Jupiter": "an expansive growth period — the universe is leaning toward yes for you",
    "Venus":   "a long season of the heart — love, beauty, and creative expression as teachers",
    "Saturn":  "a clarifying pressure — Saturn is asking what is truly real and lasting in your life",
    "Rahu":    "a period of hungry becoming — ambition, transformation, and the pull toward something new",
    "Ketu":    "a releasing cycle — your soul is lightening its load to make room for something truer",
}

DASHA_THEMES = {
    "Sun":     {
        "domain":     "identity, purpose, career, and your relationship with authority",
        "positive":   "Visibility rises. Recognition arrives. You step into leadership naturally.",
        "shadow":     "Ego friction, need for external validation, conflicts with authority figures may surface.",
        "invitation": "Step fully into who you are — without waiting for permission from anyone."
    },
    "Moon":    {
        "domain":     "emotional world, home, family, mother, and the depth of your inner life",
        "positive":   "Emotional richness, home blessings, deep relationships, intuition sharpens.",
        "shadow":     "Mood cycles, emotional sensitivity heightened, mother's health may be a focus.",
        "invitation": "Build your inner security so deeply that the outer world cannot shake it."
    },
    "Mars":    {
        "domain":     "energy, courage, property, physical vitality, and the capacity for bold action",
        "positive":   "Property gains possible, physical strength peaks, bold moves are rewarded.",
        "shadow":     "Impatience, conflicts, risk of accidents — energy must be consciously channeled.",
        "invitation": "Channel your extraordinary energy into what actually matters most."
    },
    "Mercury": {
        "domain":     "intellect, communication, business, writing, education, and trade",
        "positive":   "Business opportunities open, communication mastery, educational achievements.",
        "shadow":     "Overthinking, scattered focus, miscommunication if not careful.",
        "invitation": "Trust the clarity of your mind and speak your truth with precision."
    },
    "Jupiter": {
        "domain":     "wisdom, expansion, marriage, children, wealth, spiritual growth, and good fortune",
        "positive":   "Peak blessings — marriage, children, wealth, wisdom all expand naturally.",
        "shadow":     "Over-expansion, false optimism — expand with wisdom, not just enthusiasm.",
        "invitation": "Expand boldly. What you build in this period has unusual staying power."
    },
    "Venus":   {
        "domain":     "love, beauty, marriage, creativity, luxury, and the refinement of life",
        "positive":   "Romance flourishes, creative success arrives, social grace and charm are magnetic.",
        "shadow":     "Over-indulgence, relationship complications, attachment to comfort.",
        "invitation": "Let love teach you depth — not just pleasure, but genuine transformation."
    },
    "Saturn":  {
        "domain":     "karma, discipline, hard work, structure, longevity, and the truth about your life",
        "positive":   "What you build with integrity now will outlast everything. Lasting success through real work.",
        "shadow":     "Delays, isolation, depression, chronic patterns surfacing to be addressed.",
        "invitation": "Do the real work. Saturn rewards what is genuine and punishes what is not."
    },
    "Rahu":    {
        "domain":     "ambition, foreign connections, technology, obsession, and unconventional paths",
        "positive":   "Rapid material rise, foreign success, technological mastery, unconventional recognition.",
        "shadow":     "Illusion, deception, addiction, identity confusion — keep your eyes open.",
        "invitation": "Pursue your ambitions fully — but with your eyes open to what is truly real."
    },
    "Ketu":    {
        "domain":     "spirituality, past life resolution, detachment, sudden events, and liberation",
        "positive":   "Spiritual breakthrough, past karma releases, profound wisdom and psychic clarity.",
        "shadow":     "Confusion, sudden losses, disconnection from the external world.",
        "invitation": "Trust the releasing. What falls away was never truly yours to begin with."
    },
}

CONCERN_CONTEXT = {
    "career": {
        "Sun":     "Your professional world is your primary stage right now.",
        "Saturn":  "Career structures are being tested for what is genuinely sustainable.",
        "Jupiter": "A real window for professional advancement and recognition is open.",
        "Mercury": "Communication and business acumen are your greatest career tools.",
        "Mars":    "Bold action and initiative in your professional life are rewarded.",
        "Rahu":    "Unconventional, technology-driven, or foreign career paths open up.",
        "Venus":   "Creative work and relationship-based career opportunities flourish.",
    },
    "relationships": {
        "Venus":   "Love and connection are the primary teacher in your life right now.",
        "Moon":    "Emotional bonds are deepening — what is real becomes clear.",
        "Jupiter": "An unusually auspicious period for love, partnership, and marriage.",
        "Saturn":  "Relationships are being refined — real ones deepen, conditional ones surface.",
        "Rahu":    "Unusual, transformative, or foreign connections are possible.",
        "Mars":    "Passion is high — channel it toward genuine connection, not conflict.",
        "Ketu":    "Past patterns in relationships are surfacing to be finally resolved.",
    },
    "finances": {
        "Jupiter": "Financial expansion is genuinely supported — act toward abundance.",
        "Venus":   "Money flows through beauty, creativity, and relationships.",
        "Saturn":  "Slow, disciplined wealth-building is the path — no shortcuts work now.",
        "Mercury": "Business acumen and communication create financial opportunity.",
        "Rahu":    "Unconventional financial paths and quick gains are possible.",
        "Mars":    "Real estate and bold financial moves can succeed.",
        "Sun":     "Income through authority, government, or leadership roles.",
    },
    "health": {
        "Sun":     "Vitality and physical energy are in focus — honor your body's needs.",
        "Moon":    "Emotional and mental wellbeing are the foundation of physical health now.",
        "Saturn":  "Chronic patterns may surface — address the root, not just the symptom.",
        "Mars":    "Physical energy is high — channel it or it turns into inflammation.",
        "Ketu":    "Mysterious or spiritual dimensions of health may emerge.",
        "Mercury": "Nervous system and stress patterns need conscious management.",
        "Jupiter": "Health generally supported — but watch for excess and liver.",
    },
    "spirituality": {
        "Jupiter": "Wisdom and spiritual growth are fully open and supported.",
        "Ketu":    "Liberation, past life resolution, and deep spiritual practice are active.",
        "Saturn":  "Deep karmic work IS the spiritual practice right now.",
        "Moon":    "Emotional purification and inner clarity are the spiritual path.",
        "Sun":     "Connecting with your soul's authentic purpose is the spiritual work.",
        "Rahu":    "Unconventional spiritual paths and mystical experiences may unfold.",
        "Venus":   "Devotion, beauty, and love as spiritual practice.",
    },
    "general": {},
}

YOGA_DATA = {
    "Raja Yoga":     ("a pattern of authority and recognition woven into your chart at birth",
                      "Leadership and elevated status are not accidents in your life — they are written in."),
    "Dhana Yoga":    ("a pattern of financial flow and material abundance in your chart",
                      "Wealth has a natural affinity with your chart. In the right periods, it flows."),
    "Lakshmi Yoga":  ("a rare pattern of grace, fortune, and Lakshmi's blessing",
                      "Fortune follows conscious action for you — the potential is exceptional."),
    "Hamsa Yoga":    ("a pattern of wisdom, teaching, and spiritual authority",
                      "You carry the energy of a natural teacher and wisdom-keeper."),
    "Malavya Yoga":  ("a pattern of beauty, charm, and refined artistic success",
                      "Venus energy is elevated in your chart — art, love, and beauty respond to you."),
    "Sasa Yoga":     ("a pattern of mass influence, discipline, and enduring legacy",
                      "You have the capacity for leadership that reaches large numbers of people."),
    "Ruchaka Yoga":  ("a pattern of courage, decisiveness, and pioneering energy",
                      "You carry warrior energy — built for bold action and leadership under pressure."),
    "Bhadra Yoga":   ("a pattern of intellectual mastery and business excellence",
                      "Your mind is your greatest instrument. It is sharper than most."),
    "Kemadruma Yoga":("a pattern that builds the deepest form of self-reliance",
                      "Your journey teaches you to find security from within — this becomes your greatest strength."),
    "Vish Yoga":     ("a pattern of profound emotional sensitivity and depth",
                      "Your emotional depth, worked with consciously, transforms into extraordinary wisdom and empathy."),
    "Grahan Yoga":   ("a pattern of deep karmic clearing around identity or emotional life",
                      "You are doing alchemical work — clearing ancient patterns to reveal your true light."),
    "Viparita Raja Yoga": ("a pattern of rising through and because of difficulty",
                           "Your greatest victories come through — not despite — life's most challenging periods."),
}

YOGA_ACTIVATORS = {
    "Raja Yoga":     ["Sun","Jupiter","Mars","Moon"],
    "Dhana Yoga":    ["Jupiter","Venus","Mercury"],
    "Lakshmi Yoga":  ["Jupiter","Venus"],
    "Hamsa Yoga":    ["Jupiter"],
    "Malavya Yoga":  ["Venus"],
    "Sasa Yoga":     ["Saturn"],
    "Ruchaka Yoga":  ["Mars"],
    "Bhadra Yoga":   ["Mercury"],
    "Kemadruma Yoga":["Moon","Saturn"],
    "Vish Yoga":     ["Saturn","Moon"],
    "Grahan Yoga":   ["Rahu","Ketu","Sun","Moon"],
    "Viparita Raja Yoga": ["Saturn","Rahu","Ketu"],
}


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — Dasha Timing Windows
# ══════════════════════════════════════════════════════════════════════════════

def layer1_dasha_windows(chart_data: dict, dashas: dict, concern: str = "general") -> list[dict]:
    """
    High-confidence predictions from dasha timing alone.
    Mathematical. Always true for this chart. Confidence ~0.90.
    """
    predictions = []
    now = datetime.utcnow()

    vim  = dashas.get("vimsottari", [])
    jai  = dashas.get("jaimini", [])

    # ── Current Vimsottari Mahadasha ──────────────────────────────────────
    current_vim_md = _current_period(vim, now)
    if current_vim_md:
        planet   = current_vim_md["lord_or_sign"]
        end_dt   = _parse_dt(current_vim_md["end"])
        months_left = max(1, int((end_dt - now).days / 30))
        theme    = DASHA_THEMES.get(planet, DASHA_THEMES["Saturn"])
        energy   = DASHA_ENERGY.get(planet, f"a {planet} energy cycle")
        concern_line = CONCERN_CONTEXT.get(concern, {}).get(planet, "")

        predictions.append({
            "layer":      1,
            "confidence": 0.92,
            "type":       "current_chapter",
            "title":      "Your Current Soul Chapter",
            "what":       f"You are in {energy}.",
            "why":        (f"Your soul's journey has a precise rhythm — and right now the chapter "
                           f"being written is about {theme['domain']}. This is not random. "
                           f"This is exactly the curriculum your chart called for at this stage of your life."),
            "what_it_means": (f"{theme['positive']} "
                              f"{concern_line} "
                              f"Watch also for: {theme['shadow']}"),
            "invitation": f"This period is asking you to: {theme['invitation']}",
            "window":     f"This chapter has approximately {months_left} months remaining.",
        })

        # ── Current Vimsottari Antardasha ──────────────────────────────────
        current_vim_ad = _current_antardasha(vim, now)
        if current_vim_ad and current_vim_ad["lord_or_sign"] != planet:
            ad_planet  = current_vim_ad["lord_or_sign"]
            ad_end     = _parse_dt(current_vim_ad["end"])
            ad_months  = max(1, int((ad_end - now).days / 30))
            ad_theme   = DASHA_THEMES.get(ad_planet, DASHA_THEMES["Saturn"])
            ad_energy  = DASHA_ENERGY.get(ad_planet, f"a {ad_planet} sub-theme")

            predictions.append({
                "layer":      1,
                "confidence": 0.88,
                "type":       "sub_theme",
                "title":      "The Sub-Theme Active Right Now",
                "what":       f"Within your larger chapter, right now {ad_energy} is the sub-theme coloring everything.",
                "why":        (f"Life has both long chapters and shorter sub-themes running inside them. "
                               f"Your current sub-theme through {ad_planet}'s energy brings "
                               f"{ad_theme['domain']} into the foreground of your daily experience."),
                "what_it_means": ad_theme["positive"],
                "invitation": ad_theme["invitation"],
                "window":     f"This sub-theme continues for approximately {ad_months} more months.",
            })

    # ── Next Jaimini Mahadasha preview (if within 18 months) ──────────────
    next_jai_md = _next_period(jai, now)
    if next_jai_md:
        next_sign    = next_jai_md["lord_or_sign"]
        next_planet  = _lord(next_sign)
        next_start   = _parse_dt(next_jai_md["start"])
        months_until = int((next_start - now).days / 30)

        if 0 < months_until <= 18:
            next_theme  = DASHA_THEMES.get(next_planet, DASHA_THEMES.get(next_sign, DASHA_THEMES["Saturn"]))
            next_energy = DASHA_ENERGY.get(next_planet, DASHA_ENERGY.get(next_sign, f"a new cycle"))

            predictions.append({
                "layer":      1,
                "confidence": 0.88,
                "type":       "next_chapter",
                "title":      "The Chapter That Is Coming",
                "what":       f"In approximately {months_until} months, {next_energy} begins.",
                "why":        (f"Every cycle prepares you for the next. What you are building and learning "
                               f"right now is specifically preparing you for a period of {next_theme['domain']}."),
                "what_it_means": f"The coming period brings: {next_theme['positive']}",
                "invitation": f"Begin preparing now: {next_theme['invitation']}",
                "window":     f"This new chapter begins around {next_start.strftime('%B %Y')}.",
            })

    return predictions


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — Dasha + Transit Confluence
# ══════════════════════════════════════════════════════════════════════════════

def layer2_confluence(
    chart_data: dict,
    dashas: dict,
    current_transits: list,
    concern: str = "general"
) -> list[dict]:
    """
    Medium-high confidence predictions when dasha + transit agree.
    The universe sending the same message through two channels simultaneously.
    Confidence ~0.80-0.87.
    """
    predictions = []
    now  = datetime.utcnow()
    vim  = dashas.get("vimsottari", [])

    current_md = _current_period(vim, now)
    current_ad = _current_antardasha(vim, now)
    md_planet  = current_md["lord_or_sign"] if current_md else ""
    ad_planet  = current_ad["lord_or_sign"] if current_ad else ""

    lagna_idx  = _sign_idx(chart_data["lagna"]["sign"])
    moon_sign  = chart_data["planets"]["Moon"]["sign"]
    moon_idx   = _sign_idx(moon_sign)

    # Build transit map: planet → current sign
    transit_map = {}
    for t in current_transits:
        if isinstance(t, dict):
            p = t.get("planet", t.get("name", ""))
            s = t.get("current_sign", t.get("sign", t.get("transit_sign", "")))
            if p and s:
                transit_map[p] = s

    # ── Check: Jupiter over lagna / 5th / 9th ─────────────────────────────
    jup_sign = transit_map.get("Jupiter", "")
    if jup_sign:
        jup_house = ((_sign_idx(jup_sign) - lagna_idx) % 12) + 1
        if jup_house in [1, 5, 9]:
            predictions.append({
                "layer":      2,
                "confidence": 0.87,
                "type":       "jupiter_blessing",
                "title":      "An Expansive Opening Is Active",
                "what":       "An expansive growth energy is moving through one of the most auspicious areas of your chart right now.",
                "why":        ("When Jupiter's expansive energy moves through certain areas of your chart, "
                               "it acts like rain on fertile soil — what you plant grows faster, "
                               "doors open more easily, and the universe seems to lean toward yes."),
                "what_it_means": CONCERN_CONTEXT.get(concern, {}).get("Jupiter",
                                 "Growth and expansion are genuinely available to you right now."),
                "invitation": "This is your window. Whatever you have been hesitating on — move toward it now. This window has a timeline.",
                "window":     "Active now. Jupiter moves signs approximately every 12 months.",
                "intensity":  "very_high",
            })

    # ── Check: Saturn near natal Moon (Sade Sati) ─────────────────────────
    sat_sign = transit_map.get("Saturn", "")
    if sat_sign:
        sat_idx   = _sign_idx(sat_sign)
        distance  = min((sat_idx - moon_idx) % 12, (moon_idx - sat_idx) % 12)
        if distance <= 1:
            phase = "at its peak in" if sat_idx == moon_idx else "moving through"
            predictions.append({
                "layer":      2,
                "confidence": 0.90,
                "type":       "sade_sati",
                "title":      "A Deep Refinement Cycle Is Active",
                "what":       f"A profound clarifying pressure is {phase} your emotional world right now.",
                "why":        ("Saturn is moving through your emotional landscape asking one fundamental question: "
                               "what here is real? What relationships, patterns, and beliefs are genuine — "
                               "and which are built on sand? This is not punishment. This is the sculptor at work."),
                "what_it_means": CONCERN_CONTEXT.get(concern, {}).get("Saturn",
                                 "Structures in your life are being refined. What is real will remain. What is not will surface."),
                "invitation": ("Get radically honest with yourself. What needs to change? "
                               "What are you holding that is costing more than it is giving? "
                               "The clarity that comes from this period is permanent."),
                "window":     "This refinement cycle lasts 2.5 years per phase (7.5 years total). Work with it consciously.",
                "intensity":  "very_high",
            })

    # ── Check: Active dasha planet also strong in transit ─────────────────
    if ad_planet and transit_map.get(ad_planet):
        transit_sign  = transit_map[ad_planet]
        transit_house = ((_sign_idx(transit_sign) - lagna_idx) % 12) + 1
        if transit_house in [1, 4, 5, 7, 9, 10, 11]:
            ad_energy = DASHA_ENERGY.get(ad_planet, f"a {ad_planet} energy")
            predictions.append({
                "layer":      2,
                "confidence": 0.82,
                "type":       "dasha_transit_double",
                "title":      "Two Cycles Speaking the Same Language",
                "what":       f"Right now two cycles are both pointing through {ad_energy} simultaneously.",
                "why":        ("When the universe sends the same message through two different channels at once, "
                               "it means: this is not a coincidence. This is a real, high-signal window. "
                               "The timing is unusually precise."),
                "what_it_means": CONCERN_CONTEXT.get(concern, {}).get(ad_planet,
                                 f"Pay close attention to {DASHA_THEMES.get(ad_planet, {}).get('domain', 'your current themes')} right now."),
                "invitation": "Act with intention during this window. High-signal periods reward conscious action.",
                "window":     "Active for the duration of your current sub-cycle.",
                "intensity":  "high",
            })

    # ── Check: Double Jupiter (MD + AD both Jupiter) ──────────────────────
    if md_planet == "Jupiter" and ad_planet == "Jupiter":
        predictions.append({
            "layer":      2,
            "confidence": 0.93,
            "type":       "double_jupiter",
            "title":      "A Rare Double Expansion Window",
            "what":       "Two Jupiter cycles are activating simultaneously — this is one of the rarest and most auspicious configurations in your life.",
            "why":        ("Jupiter's expansive, blessing energy is amplified through both your major and minor "
                           "cycle simultaneously. This kind of double activation happens once or twice in a lifetime."),
            "what_it_means": ("Marriage, children, wealth, wisdom, and recognition are all at their highest potential. "
                              "Whatever Jupiter represents in your chart — it is fully open right now."),
            "invitation": "Act toward your highest aspirations right now. Do not wait. This window is real and it has an end date.",
            "window":     "Use every month of this period intentionally.",
            "intensity":  "exceptional",
        })

    # ── Check: Double Saturn (heavy period — frame with compassion) ───────
    if md_planet == "Saturn" and ad_planet == "Saturn":
        predictions.append({
            "layer":      2,
            "confidence": 0.91,
            "type":       "double_saturn",
            "title":      "A Period of Maximum Karmic Refinement",
            "what":       "Two Saturn cycles are active simultaneously — one of life's most intensely clarifying periods.",
            "why":        ("Saturn never breaks you. It breaks what was never truly you. "
                           "What you lose in this period is what was costing you the most — "
                           "even when it doesn't feel that way in the moment."),
            "what_it_means": CONCERN_CONTEXT.get(concern, {}).get("Saturn",
                             "This period is stripping away what is not real to reveal what is. Trust the process."),
            "invitation": ("Discipline, integrity, patience, and genuine service. "
                           "These are not just remedies — they are the only path through. "
                           "What you build with real work right now will outlast everything."),
            "window":     "This intensity continues for the duration of the double Saturn period.",
            "intensity":  "very_high",
        })

    return predictions


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — Natal Yoga Activation
# ══════════════════════════════════════════════════════════════════════════════

def layer3_yoga_activation(
    chart_data: dict,
    dashas: dict,
    detected_yogas: list[str],
    concern: str = "general"
) -> list[dict]:
    """
    Pattern-based predictions from natal yoga activation.
    The seed planted at birth, flowering in its right season.
    Confidence ~0.78.
    """
    if not detected_yogas:
        return []

    predictions = []
    now = datetime.utcnow()
    vim = dashas.get("vimsottari", [])

    current_md = _current_period(vim, now)
    current_ad = _current_antardasha(vim, now)
    md_planet  = current_md["lord_or_sign"] if current_md else ""
    ad_planet  = current_ad["lord_or_sign"] if current_ad else ""

    for yoga_name in detected_yogas:
        if yoga_name not in YOGA_DATA:
            continue

        yoga_energy, yoga_desc = YOGA_DATA[yoga_name]
        activators  = YOGA_ACTIVATORS.get(yoga_name, [])
        is_active   = (md_planet in activators or ad_planet in activators or
                       _lord(md_planet) in activators)

        if is_active:
            predictions.append({
                "layer":      3,
                "confidence": 0.80,
                "type":       "yoga_active",
                "title":      "A Soul Pattern Is Flowering Right Now",
                "what":       f"There is {yoga_energy} — and it is being activated by the current period of your life.",
                "why":        (f"This pattern was woven into your chart at birth, like a seed. "
                               f"Seeds need their season. Your season has arrived. {yoga_desc}"),
                "what_it_means": _yoga_concern_text(yoga_name, concern),
                "invitation": "This is not luck. This is your chart delivering what was always promised. Show up for it fully.",
                "window":     "Active throughout your current dasha period.",
                "yoga_name":  yoga_name,
            })
        else:
            future_activator = activators[0] if activators else "a future period"
            predictions.append({
                "layer":      3,
                "confidence": 0.72,
                "type":       "yoga_upcoming",
                "title":      "A Pattern Waiting for Its Season",
                "what":       f"There is {yoga_energy} in your chart. Its full season has not yet arrived.",
                "why":        (f"{yoga_desc} "
                               f"The current period is preparation. The full activation arrives "
                               f"when a {future_activator} cycle begins."),
                "what_it_means": f"The potential is real. Right now is the time to plant seeds, not harvest them.",
                "invitation": "Prepare now for what is coming. The foundation you build today is what that future season will stand on.",
                "window":     f"Full activation expected in a future {future_activator} period.",
                "yoga_name":  yoga_name,
            })

    return predictions


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — Personal Life Event Mirror (The Moat)
# ══════════════════════════════════════════════════════════════════════════════

def layer4_personal_mirror(
    user_id: str,
    chart_data: dict,
    dashas: dict,
    life_events: list,
    supabase: Client,
    concern: str = "general"
) -> list[dict]:
    """
    Predictions derived from the user's own life event history.
    Gets stronger with every event logged. Confidence grows with data.
    This is the moat — no other app can build this because they don't collect events.
    Minimum 3 events needed to activate.
    """
    if not life_events or len(life_events) < 3:
        return []

    predictions = []
    now  = datetime.utcnow()
    vim  = dashas.get("vimsottari", [])
    all_dashas = (dashas.get("vimsottari", []) +
                  dashas.get("jaimini", []) +
                  dashas.get("ashtottari", []))

    current_md = _current_period(vim, now)
    current_ad = _current_antardasha(vim, now)
    md_planet  = current_md["lord_or_sign"] if current_md else ""
    ad_planet  = current_ad["lord_or_sign"] if current_ad else ""

    correlations = _get_or_build_correlations(user_id, life_events, all_dashas, supabase)

    for corr in correlations[:2]:
        dasha_period = corr.get("dasha_period", "")
        occurrences  = corr.get("occurrences", 0)
        event_type   = corr.get("event_type", "significant shift")
        pattern      = corr.get("pattern", "")
        examples     = corr.get("examples", [])

        is_active = (dasha_period == md_planet or dasha_period == ad_planet)

        if is_active and occurrences >= 2:
            example_lines = []
            for ex in examples[:2]:
                if ex.get("year") and ex.get("description"):
                    example_lines.append(f"In {ex['year']}, {ex['description']}.")
            example_text = " ".join(example_lines)

            confidence = min(0.55 + (occurrences * 0.10), 0.88)

            predictions.append({
                "layer":      4,
                "confidence": confidence,
                "type":       "personal_mirror",
                "title":      "Your Own Story Speaks",
                "what":       f"We've noticed a pattern in your own life: whenever {pattern}, something significant shifts around {event_type}.",
                "why":        (f"{example_text} "
                               f"That same energy is active in your chart right now. "
                               f"Your personal history is your most accurate oracle."),
                "what_it_means": (f"Based on your own patterns — seen {occurrences} times — "
                                  f"a {event_type} development is likely in this period."),
                "invitation": ("You already know how this goes. You have moved through this before. "
                               "The question is: what will you do differently this time?"),
                "window":     "This pattern is currently active.",
                "occurrences": occurrences,
                "event_type":  event_type,
            })

    return predictions


# ══════════════════════════════════════════════════════════════════════════════
# WOW FIELDS — TL;DR, 90-Day Mission, Prediction Tracker
# ══════════════════════════════════════════════════════════════════════════════
#
# These are injected into the LLM prompt so the model generates them as
# structured JSON objects alongside its normal prose response.
# They power the three flywheel UI components:
#   1. TL;DR card  (first thing user sees — kills wall-of-text problem)
#   2. Mission checklist  (90-day mission as a persistent UI object)
#   3. Prediction tracker (close the loop — users mark claims as confirmed)
#
# HOW IT WORKS
# ─────────────────────────────────────────────────────────────────────────────
# build_wow_fields_prompt_block() returns a string injected into the LLM
# prompt. It instructs the model to emit a structured JSON block at the END
# of its response, wrapped in <WOW_FIELDS>...</WOW_FIELDS> tags.
#
# parse_wow_fields_from_response() extracts and parses that block.
# It is safe — falls back to empty dicts/lists on any parse error.
#
# Both are called in your /predict endpoint, e.g.:
#
#   prompt      = build_predict_prompt(...) + build_wow_fields_prompt_block(predictions, concern)
#   raw         = llm.complete(prompt)
#   wow         = parse_wow_fields_from_response(raw)
#   clean_text  = strip_wow_block_from_response(raw)
#
# The wow dict contains: { tldr, mission_checklist, trackable_predictions }
# Pass these directly into your API response alongside the prose text.
# ══════════════════════════════════════════════════════════════════════════════

def build_wow_fields_prompt_block(predictions: dict, concern: str) -> str:
    """
    Returns a prompt block to append to build_predict_prompt() output.
    Instructs the LLM to emit structured flywheel data after its prose.

    The lead prediction window is extracted to anchor the mission timeline
    and the trackable_predictions verify_by dates.
    """
    lead      = predictions.get("lead", {})
    lead_window = lead.get("window", "the next 6–12 months")
    lead_what   = lead.get("what", "")
    concern_label = concern.replace("_", " ").title()

    now = datetime.utcnow()
    # Derive a sensible verify_by: 9 months out by default, end of year at most
    verify_default = (now + timedelta(days=270)).strftime("%Y-%m-%d")
    verify_short   = (now + timedelta(days=180)).strftime("%Y-%m-%d")

    return f"""

═══ WOW FIELDS — STRUCTURED OUTPUT (append AFTER your normal response) ═══

After completing your 7-section response above, append EXACTLY the following
JSON block, wrapped in <WOW_FIELDS> tags. This is parsed by the app to power
the TL;DR card, 90-day mission checklist, and prediction tracker.

RULES FOR GENERATING WOW FIELDS:
1. tldr.hook — the single most surprising, specific insight from THIS reading.
   Max 18 words. Must make the user think "how does it know that about me?"
   Pull from the most personal or chart-specific line in your response.
   Do NOT use generic phrases like "your chart shows" or "the stars say."

2. tldr.window — the exact date range you already named in section 4.
   Format: "Mon YYYY" or "Mon–Mon YYYY". Copy it exactly.

3. tldr.action — the START action from section 5, compressed to ≤10 words,
   imperative tense. No hedging. No "consider" or "try."

4. mission_checklist — 4 items ONLY. Map to actual weeks/days:
   - Item 1: Week 1 — what to BEGIN observing or doing immediately
   - Item 2: Day 30 — first review milestone
   - Item 3: Day 60 — an act or structural decision based on what was observed
   - Item 4: Day 90 — return and close the loop
   Make each task specific to THIS person's concern ({concern_label}) and chart pattern.
   milestone_type must be one of: observe | act | review | complete

5. trackable_predictions — 2–3 items. These must be CONCRETE and FALSIFIABLE:
   - The user must be able to say "yes this happened" or "no it didn't"
   - claim: 1 sentence, specific, no vague language
   - verify_by: ISO date string. Use {verify_short} for near-term, {verify_default} for medium-term
   - category: timing | event | inner_shift
   Pull directly from the specific windows and outcomes named in your response.

Context for your WOW FIELDS generation:
  Lead signal: {lead_what}
  Active window from reading: {lead_window}
  Concern: {concern_label}

<WOW_FIELDS>
{{
  "tldr": {{
    "hook": "<single most surprising specific insight — max 18 words>",
    "window": "<exact date range from section 4>",
    "action": "<START action from section 5 in ≤10 words, imperative>"
  }},
  "mission_checklist": [
    {{
      "week": "Week 1",
      "task": "<specific observational task for this person>",
      "milestone_type": "observe"
    }},
    {{
      "week": "Day 30",
      "task": "<first review milestone — what pattern to look for>",
      "milestone_type": "review"
    }},
    {{
      "week": "Day 60",
      "task": "<structural action based on what was observed>",
      "milestone_type": "act"
    }},
    {{
      "week": "Day 90",
      "task": "Return to Antar. Your pattern is now your roadmap.",
      "milestone_type": "complete"
    }}
  ],
  "trackable_predictions": [
    {{
      "id": "<slug-from-claim>",
      "claim": "<concrete falsifiable prediction from your response>",
      "verify_by": "{verify_short}",
      "category": "timing"
    }},
    {{
      "id": "<slug-from-claim>",
      "claim": "<concrete falsifiable prediction from your response>",
      "verify_by": "{verify_default}",
      "category": "event"
    }}
  ]
}}
</WOW_FIELDS>

═══ END WOW FIELDS ═══
"""


def parse_wow_fields_from_response(raw_response: str) -> dict:
    """
    Extract and parse the <WOW_FIELDS>...</WOW_FIELDS> block from the LLM response.
    Returns a dict with tldr, mission_checklist, trackable_predictions.
    Falls back to safe empty structures on any parse failure — never raises.
    """
    import json, re

    empty = {
        "tldr": None,
        "mission_checklist": [],
        "trackable_predictions": [],
    }

    try:
        match = re.search(r"<WOW_FIELDS>(.*?)</WOW_FIELDS>", raw_response, re.DOTALL)
        if not match:
            return empty

        raw_json = match.group(1).strip()
        parsed   = json.loads(raw_json)

        # Validate tldr
        tldr = parsed.get("tldr", {})
        if not isinstance(tldr, dict) or not tldr.get("hook"):
            tldr = None

        # Validate mission_checklist
        mission = parsed.get("mission_checklist", [])
        if not isinstance(mission, list):
            mission = []
        mission = [
            m for m in mission
            if isinstance(m, dict) and m.get("week") and m.get("task")
        ][:4]

        # Validate trackable_predictions
        trackable = parsed.get("trackable_predictions", [])
        if not isinstance(trackable, list):
            trackable = []
        trackable = [
            t for t in trackable
            if isinstance(t, dict) and t.get("id") and t.get("claim") and t.get("verify_by")
        ][:3]

        return {
            "tldr":                  tldr,
            "mission_checklist":     mission,
            "trackable_predictions": trackable,
        }

    except Exception as e:
        print(f"[parse_wow_fields] parse error: {e}")
        return empty


def strip_wow_block_from_response(raw_response: str) -> str:
    """
    Remove the <WOW_FIELDS>...</WOW_FIELDS> block from the LLM response
    before returning prose text to the frontend.
    Also strips the ═══ WOW FIELDS header line if present.
    """
    import re
    # Remove the full WOW_FIELDS section including the delimiter lines
    cleaned = re.sub(
        r"\n?═══ WOW FIELDS.*?═══ END WOW FIELDS ═══\n?",
        "",
        raw_response,
        flags=re.DOTALL,
    )
    # Belt-and-suspenders: remove any orphaned tags
    cleaned = re.sub(r"<WOW_FIELDS>.*?</WOW_FIELDS>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


def _prediction_hash(prediction_text: str) -> str:
    """Short stable hash of a prediction string — used as localStorage key prefix."""
    return hashlib.md5(prediction_text.encode()).hexdigest()[:8]


# ══════════════════════════════════════════════════════════════════════════════
# MASTER BUILDER — Combines all 4 layers
# ══════════════════════════════════════════════════════════════════════════════

def build_layered_predictions(
    user_id: Optional[str],
    chart_data: dict,
    dashas: dict,
    current_transits: list,
    life_events: list,
    supabase: Client,
    concern: str = "general",
    detected_yogas: list[str] = None,
) -> dict:
    """
    Main entry point. Call this from your /predict endpoint.
    Returns structured predictions dict ready to pass into prompt_builder.py.

    Usage in main.py:
        from antar_engine.predictions import build_layered_predictions
        predictions = build_layered_predictions(
            user_id=user_id,
            chart_data=chart_data,
            dashas=dashas_response,
            current_transits=current_transits,
            life_events=life_events,
            supabase=supabase,
            concern=_detect_concern(request.question),
            detected_yogas=detected_yogas,
        )

    v2: The returned dict now includes wow_prompt_block — append this to
    your LLM prompt string so the model emits WOW_FIELDS automatically.
    After the LLM call, use parse_wow_fields_from_response() and
    strip_wow_block_from_response() to split prose from structured data.
    """
    l1 = layer1_dasha_windows(chart_data, dashas, concern)
    l2 = layer2_confluence(chart_data, dashas, current_transits, concern)
    l3 = layer3_yoga_activation(chart_data, dashas, detected_yogas or [], concern)
    l4 = layer4_personal_mirror(user_id, chart_data, dashas, life_events, supabase, concern) if user_id else []

    all_preds = sorted(l1 + l2 + l3 + l4, key=lambda x: x["confidence"], reverse=True)

    # Store high-confidence predictions for fulfillment tracking
    if user_id and all_preds:
        _store_predictions(user_id, all_preds, supabase)

    result = {
        "layer_1":            l1,
        "layer_2":            l2,
        "layer_3":            l3,
        "layer_4":            l4,
        "all_predictions":    all_preds,
        "lead":               all_preds[0] if all_preds else {},
        "total_signals":      len(all_preds),
        "highest_confidence": all_preds[0]["confidence"] if all_preds else 0,
        "has_personal_data":  len(l4) > 0,
        "concern":            concern,
        # v2: WOW FIELDS prompt block — append to your LLM prompt string
        "wow_prompt_block":   build_wow_fields_prompt_block(
                                  {"lead": all_preds[0] if all_preds else {}, "all_predictions": all_preds},
                                  concern,
                              ),
    }

    return result


def predictions_to_context_block(predictions: dict, chart_data: dict, concern: str) -> str:
    """
    Convert layered predictions into a clean prose context block
    for the LLM system prompt. Matches your existing prompt style.
    """
    moon_nak = chart_data["planets"]["Moon"]["nakshatra"]
    lagna    = chart_data["lagna"]["sign"]
    atm      = _find_atmakaraka(chart_data)

    lines = [
        "═══ LAYERED PREDICTION SIGNALS (use these as your foundation) ═══",
        f"Soul signature: {lagna} rising, {moon_nak} Moon nakshatra",
        f"Soul's core lesson (Atmakaraka): {DASHA_ENERGY.get(atm, atm)}",
        f"Primary concern: {concern}",
        f"Total signals: {predictions['total_signals']} | "
        f"Highest confidence: {int(predictions['highest_confidence']*100)}% | "
        f"Personal data: {'YES — use Layer 4 personal mirror' if predictions['has_personal_data'] else 'Building — 3+ events needed'}",
        "",
    ]

    for pred in predictions["all_predictions"][:5]:
        lines += [
            f"[Layer {pred['layer']} | {int(pred['confidence']*100)}% confidence | {pred['title']}]",
            f"WHAT: {pred['what']}",
            f"WHY: {pred['why']}",
            f"MEANING: {pred['what_it_means']}",
            f"INVITATION: {pred['invitation']}",
            f"WINDOW: {pred['window']}",
            "",
        ]

    lines.append("═══ END PREDICTION SIGNALS ═══")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# CONCERN DETECTION — auto-detect from question text
# ══════════════════════════════════════════════════════════════════════════════

def detect_concern(question: str) -> str:
    """
    Full 10-domain concern router. Order matters — specific before general.
    """
    q = question.lower()

    if any(w in q for w in ["specul","gambl","lotter","casino","bet ","betting","poker",
                             "stock market","stocks","trading","crypto","invest in",
                             "should i buy","should i sell","day trad","forex"]):
        return "speculation"

    if any(w in q for w in ["divorce","separate","separation","break up","breakup","split",
                             "end my marriage","leaving my wife","leaving my husband",
                             "spouse left","marriage failing","marriage over","failing",
                             "should i leave","leave my partner","leave my spouse"]):
        return "divorce"

    if any(w in q for w in ["love","romance","romantic","crush","dating","date",
                             "boyfriend","girlfriend","soulmate","when will i meet",
                             "find love","find someone","will i get married",
                             "love marriage","heartbreak","fall in love","in love"]):
        return "love"

    if any(w in q for w in ["marriage","married","wedding","husband","wife","spouse",
                             "my partner","my marriage"]):
        return "marriage"

    if any(w in q for w in ["foreign","abroad","overseas","travel","immigrat","visa",
                             "move to","relocat","settle in","work in","study in",
                             "move abroad","international","other country","another country",
                             "leave india","leave country"]):
        return "foreign"

    if any(w in q for w in ["loss","losing money","lost money","financial loss","debt trap",
                             "bankruptcy","ruined","drained","money gone","savings gone",
                             "why am i losing","why do i lose","bad luck with money",
                             "expenses","expenditure","spending too much","losing everything"]):
        return "loss"

    if any(w in q for w in ["funding","investor","investors","capital","raise money",
                             "raise funds","vc","venture","angel invest","grant",
                             "borrow","bank loan","seed round","series","get funded",
                             "cashflow","cash flow"]):
        return "finance"

    if any(w in q for w in ["wealth","rich","wealthy","make money","earn money","income",
                             "salary","savings","property","real estate","assets",
                             "net worth","passive income","when will i be rich",
                             "financial freedom","profit"]):
        return "wealth"

    if any(w in q for w in ["financ","money","business","revenue","budget","payment","afford"]):
        return "finance"

    if any(w in q for w in ["health","sick","illness","disease","hospital","surgery",
                             "recover","pain","body","fatigue","tired","stress",
                             "anxiety","mental health","depression","healing"]):
        return "health"

    if any(w in q for w in ["career","job","work","profession","promotion","startup",
                             "company","office","boss","fired","resign","quit",
                             "new job","interview","opportunity","recognition",
                             "success","entrepreneur"]):
        return "career"

    if any(w in q for w in ["spiritual","meditation","dharma","karma","moksha","purpose",
                             "meaning","soul","life purpose","why am i here","destiny",
                             "awakening","consciousness"]):
        return "spiritual"

    return "general"


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _current_period(periods: list, now: datetime) -> Optional[dict]:
    for p in periods:
        if _parse_dt(p["start"]) <= now <= _parse_dt(p["end"]):
            return p
    return periods[0] if periods else None

def _current_antardasha(periods: list, now: datetime) -> Optional[dict]:
    current_md = _current_period(periods, now)
    if not current_md:
        return None
    md_start = _parse_dt(current_md["start"])
    md_end   = _parse_dt(current_md["end"])
    sub_periods = [
        p for p in periods
        if _parse_dt(p["start"]) >= md_start
        and _parse_dt(p["end"]) <= md_end
        and p["lord_or_sign"] != current_md["lord_or_sign"]
    ]
    for p in sub_periods:
        if _parse_dt(p["start"]) <= now <= _parse_dt(p["end"]):
            return p
    return None

def _next_period(periods: list, now: datetime) -> Optional[dict]:
    for p in periods:
        if _parse_dt(p["start"]) > now:
            return p
    return None

def _find_atmakaraka(chart_data: dict) -> str:
    max_deg = -1
    atm     = "Sun"
    for planet, data in chart_data["planets"].items():
        if planet in ("Rahu", "Ketu"):
            continue
        deg = float(data.get("degree", 0))
        if deg > max_deg:
            max_deg = deg
            atm = planet
    return atm

def _yoga_concern_text(yoga_name: str, concern: str) -> str:
    mapping = {
        "Raja Yoga": {
            "career":       "Leadership and recognition are genuinely available to you in your professional life.",
            "relationships":"You attract partners of real quality and substance.",
            "finances":     "Authority and leadership roles bring financial reward.",
        },
        "Dhana Yoga": {
            "finances":     "Wealth has a natural affinity with your chart — this period activates it.",
            "career":       "Career success in this period translates directly into financial gain.",
        },
        "Malavya Yoga": {
            "relationships":"Love and beauty respond naturally to you — relationships flourish.",
            "career":       "Creative and artistic work brings real recognition.",
        },
        "Sasa Yoga": {
            "career":       "Large-scale leadership affecting many people is your path.",
            "finances":     "Patient, disciplined wealth-building is powerfully supported.",
        },
        "Hamsa Yoga": {
            "career":       "Teaching, wisdom-sharing, and advisory roles are your natural domain.",
            "spirituality": "Spiritual authority and genuine wisdom are opening up.",
        },
        "Kemadruma Yoga": {
            "relationships":"Learning to love without depending on love for your security — this is the work.",
            "general":      "Building unshakeable inner security is both the challenge and the gift.",
        },
        "Vish Yoga": {
            "health":       "Emotional wellbeing is the foundation of physical health — this needs attention.",
            "relationships":"Deep emotional sensitivity in relationships needs conscious management.",
        },
    }
    concern_map = mapping.get(yoga_name, {})
    return concern_map.get(concern, concern_map.get("general",
           f"This pattern is directly relevant to your {concern} journey right now."))

def _get_or_build_correlations(
    user_id: str,
    events: list,
    all_dashas: list,
    supabase: Client,
) -> list[dict]:
    try:
        stored = supabase.table("user_correlations") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("confidence_score", desc=True) \
            .limit(5) \
            .execute()
        if stored.data and len(stored.data) >= 1:
            return stored.data
    except Exception as e:
        print(f"Correlation load error: {e}")
    return _build_correlations(user_id, events, all_dashas, supabase)

def _build_correlations(
    user_id: str,
    events: list,
    all_dashas: list,
    supabase: Client,
) -> list[dict]:
    correlations = []

    by_type: dict[str, list] = {}
    for evt in events:
        etype = evt.get("event_type", "general")
        by_type.setdefault(etype, []).append(evt)

    for event_type, type_events in by_type.items():
        if len(type_events) < 2:
            continue

        dasha_counts: dict[str, int] = {}
        examples = []

        for evt in type_events:
            evt_dt = _parse_dt(evt["event_date"])
            for d in all_dashas:
                if _parse_dt(d["start"]) <= evt_dt <= _parse_dt(d["end"]):
                    lord = d["lord_or_sign"]
                    dasha_counts[lord] = dasha_counts.get(lord, 0) + 1
                    if len(examples) < 3:
                        examples.append({
                            "year":        evt_dt.year,
                            "description": evt.get("description", event_type),
                            "dasha":       lord,
                        })
                    break

        if not dasha_counts:
            continue

        top_dasha = max(dasha_counts, key=dasha_counts.get)
        count     = dasha_counts[top_dasha]

        if count >= 2:
            planet  = _lord(top_dasha)
            energy  = DASHA_ENERGY.get(planet, DASHA_ENERGY.get(top_dasha, f"{top_dasha} energy is present"))
            pattern = energy

            corr = {
                "user_id":            user_id,
                "event_type":         event_type,
                "dasha_period":       top_dasha,
                "pattern":            pattern,
                "occurrences":        count,
                "confidence_score":   min(0.50 + count * 0.10, 0.88),
                "examples":           examples,
                "last_triggered_date": datetime.utcnow().isoformat(),
            }
            correlations.append(corr)

            try:
                supabase.table("user_correlations").upsert(
                    corr,
                    on_conflict="user_id,event_type,dasha_period"
                ).execute()
            except Exception as e:
                print(f"Correlation store error: {e}")

    return correlations

def _store_predictions(user_id: str, predictions: list, supabase: Client):
    """Store high-confidence predictions for fulfillment tracking."""
    now = datetime.utcnow()
    for pred in predictions:
        if pred.get("confidence", 0) < 0.75:
            continue
        try:
            supabase.table("user_predictions").upsert({
                "user_id":               user_id,
                "generated_at":          now.isoformat(),
                "prediction_window_end": (now + timedelta(days=180)).isoformat(),
                "category":              pred.get("type", "general"),
                "prediction_text":       pred.get("what", ""),
                "confidence_layer":      pred.get("layer", 1),
                "planets_involved":      json_safe(pred.get("planets", [])),
                "fulfilled":             False,
            }, on_conflict="user_id,generated_at,category").execute()
        except Exception as e:
            print(f"Prediction store error: {e}")

def json_safe(obj):
    import json
    try:
        json.dumps(obj)
        return obj
    except:
        return str(obj)
