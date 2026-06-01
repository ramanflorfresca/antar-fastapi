"""
highlight_templates.py — Layer-2 "concrete signal" content library.

Every prediction surface (Today / Tomorrow / Week / Month / Year / Cycle)
carries a poetic Layer-1 headline (existing) PLUS a Layer-2 list of concrete,
domain-tagged signals (NEW). This module is the single home for:

  * DOMAINS         — the locked domain palette (must match the frontend enum)
  * SCOPE_LIMITS    — max signals per surface (frontend renders up to 10)
  * SCOPE_FLOOR     — never emit fewer than this
  * LK_MICRO_TO_DOMAIN — maps the fine-grained Lal-Kitab day-domains
                         (authority/trade/relationships/...) onto locked domains
  * the English sentence templates, keyed (domain, scope, condition)

RULES (do not break):
  - Templates stay in ENGLISH. Translation to es/pt happens downstream via the
    @translate_response pipeline (it translates the highlight `text` leaf).
  - ZERO Sanskrit / astro jargon in any template — these strings are user-facing.
    No planet names, house numbers, nakshatra names, dasha names.
  - Each template is ONE concrete, falsifiable sentence (subject-verb-object).
  - Placeholders use str.format(): "{best_window}", "{avoid_window}", "{quarter}".
    A template with no placeholder is returned verbatim.

Phase status:
  - today / tomorrow  : fully authored (this is the wired Phase-1 surface).
  - week/month/year/cycle : seed entries + structure present; expanded in the
    follow-on phases that wire those endpoints. get_template() degrades safely.
"""

# ── Locked domain palette (mirror of the frontend DOMAINS map) ──────────────
DOMAINS = {
    "money":         {"label": "MONEY",   "color": "#D4A853", "icon": "₹"},
    "work":          {"label": "WORK",    "color": "#00D9B8", "icon": "▲"},
    "relationships": {"label": "PEOPLE",  "color": "#A78BFA", "icon": "♥"},
    "body":          {"label": "BODY",    "color": "#4FAE5F", "icon": "◯"},
    "mind":          {"label": "MIND",    "color": "#5BC0DE", "icon": "◇"},
    "watch":         {"label": "WATCH",   "color": "#E0A23B", "icon": "△"},
    "risk":          {"label": "AVOID",   "color": "#EF4444", "icon": "✕"},
    "opportunity":   {"label": "OPENING", "color": "#5FF5DE", "icon": "★"},
    "timing":        {"label": "WHEN",    "color": "#A78BFA", "icon": "◐"},
}
VALID_DOMAINS = set(DOMAINS.keys())

# ── Per-scope signal budget ─────────────────────────────────────────────────
SCOPE_LIMITS = {
    "today":    6,
    "tomorrow": 5,
    "week":     7,
    "month":    8,
    "year":     10,
    "cycle":    8,
}
SCOPE_FLOOR = 4          # backend never sends fewer than this when data allows
VALID_SCOPES = set(SCOPE_LIMITS.keys())


# ── Lal-Kitab fine domains -> locked domains ────────────────────────────────
# compute_lk_daily_diagnostic() emits domains_amplified_today /
# domains_to_avoid_today using this fine vocabulary. Collapse onto the locked
# palette so signals stay consistent with the frontend.
LK_MICRO_TO_DOMAIN = {
    # money
    "wealth-growth": "money", "trade": "money", "luxury": "money",
    "crecimiento financiero": "money", "comercio": "money", "lujo": "money",
    # work
    "authority": "work", "leadership": "work", "self-expression": "work",
    "discipline": "work", "structure": "work", "labor": "work",
    "long-term": "work", "communication": "work", "writing": "work",
    "learning": "work", "negotiation": "work", "action": "work",
    "initiative": "work", "courage": "work", "teaching": "work", "law": "work",
    "autoridad": "work", "liderazgo": "work", "autoexpresión": "work",
    "disciplina": "work", "estructura": "work", "trabajo": "work",
    "largo plazo": "work", "comunicación": "work", "escritura": "work",
    "aprendizaje": "work", "negociación": "work", "acción": "work",
    "iniciativa": "work", "coraje": "work", "enseñanza": "work", "ley": "work",
    # relationships (people)
    "relationships": "relationships", "diplomacy": "relationships",
    "mother": "relationships", "father": "relationships", "elders": "relationships",
    "children": "relationships", "home": "relationships",
    "relaciones": "relationships", "diplomacia": "relationships",
    "madre": "relationships", "padre": "relationships", "mayores": "relationships",
    "hijos": "relationships", "hogar": "relationships",
    # body
    "vitality": "body", "comfort": "body", "beauty": "body", "property": "body",
    "vitalidad": "body", "confort": "body", "belleza": "body", "propiedad": "body",
    # mind
    "emotion": "mind", "intuition": "mind", "wisdom": "mind", "creativity": "mind",
    "emoción": "mind", "intuición": "mind", "sabiduría": "mind",
    "creatividad": "mind",
    # watch
    "conflict": "watch", "conflicto": "watch",
}


def lk_micro_to_domain(micro: str) -> str:
    """Best-effort map an LK fine domain onto the locked palette. Defaults to work."""
    if not micro:
        return "work"
    return LK_MICRO_TO_DOMAIN.get(str(micro).strip().lower(), "work")


# ── Amplified / avoid sentence banks (locked domain -> concrete sentence) ────
# Fired when the day's diagnostic AMPLIFIES (good day) or flags AVOID for a
# domain. Same banks reused for today & tomorrow (tomorrow softened in composer).
AMPLIFIED_BY_DOMAIN = {
    "money":         "Money matters carry tailwind today — chase payments, send invoices, ask for what you're owed.",
    "work":          "Visible effort pays off today — push execution and let people see the work.",
    "relationships": "People respond warmly today — make the ask, mend the rift, send the message.",
    "body":          "Physical energy runs steady today — a good day for movement, rest, and routine care.",
    "mind":          "Your head is clear today — write, plan, and decide what's been sitting unresolved.",
    "opportunity":   "An opening is live today — the door that's been stuck moves if you push it now.",
}
AVOID_BY_DOMAIN = {
    "money":         "Hold off on new spending or speculative money moves today — timing isn't with you.",
    "work":          "Don't force big work commitments today — execution yes, decisions later.",
    "relationships": "Go easy in tense conversations today — postpone confrontation if you can.",
    "body":          "Don't overexert physically today — your reserves are lower than they feel.",
    "mind":          "Judgment is foggier than usual today — avoid choices that need a sharp head.",
}


# ── Dasha-lord life-chapter signature (current major/sub period planet) ──────
# These ground a MONEY / WORK / PEOPLE signal in the user's active life chapter.
# Jargon-safe: the planet name never appears, only its lived signature.
DASHA_SIGNATURE = {
    "Jupiter": ("money", "You're in a growth chapter — mentors, teaching, and money tend to find you; act on an opening today."),
    "Venus":   ("relationships", "You're in a chapter of relationships and comfort — partnerships and creative work are where today's leverage is."),
    "Saturn":  ("work", "You're in a slow-build chapter — unglamorous, structural effort compounds; do the boring task today."),
    "Sun":     ("work", "You're in a chapter of visibility and authority — step forward, be seen, own a decision today."),
    "Moon":    ("mind", "You're in an inward, emotional chapter — protect your peace and trust your read on people today."),
    "Mars":    ("work", "You're in a high-drive chapter — channel the heat into one hard push, not into a fight."),
    "Mercury": ("work", "You're in a chapter of communication and trade — conversations, writing, and deals move things today."),
    "Rahu":    ("opportunity", "You're in an ambitious, unconventional chapter — unusual openings appear; move fast but verify."),
    "Ketu":    ("mind", "You're in a stripping-back chapter — let go of what's done; clarity comes from subtraction today."),
}


# ── Nakshatra-energy MIND template (energy phrase is chart-derived) ──────────
def mind_from_energy(energy_phrase: str) -> str:
    energy_phrase = (energy_phrase or "").strip().rstrip(".")
    if not energy_phrase:
        return "Today's mental texture is steady — use it for focused, ordinary work."
    return f"Today's mental texture is {energy_phrase} — lean into work that matches that, not against it."


def aligned_action(aligned_first: str, domain_hint: str = "work") -> str:
    a = (aligned_first or "").strip().rstrip(".")
    if not a:
        return "Today favors steady, practical action over bold new moves."
    return f"Today favors {a} — put your best hours there."


def friction_action(friction_first: str) -> str:
    f = (friction_first or "").strip().rstrip(".")
    if not f:
        return "Friction is in the air — build in buffer time and don't overcommit."
    return f"Push back on {f} today — it'll cost more energy than it returns."


# ── Timing templates (ranges only; never an exact minute) ───────────────────
def best_window(window: str) -> str:
    window = (window or "").strip()
    if not window:
        return "Best window is the late morning — do anything that matters before the afternoon dip."
    return f"Best window: {window}. Use it for anything that actually matters."


def avoid_window(window: str) -> str:
    window = (window or "").strip()
    if not window:
        return "Avoid the dead hour after sunset for big decisions — wait for morning."
    return f"Steer clear of {window} for big decisions or signing anything."


# ── Body / watch helpers ────────────────────────────────────────────────────
def body_from_chandra(strength: str) -> str:
    s = (strength or "").strip().lower()
    if s in ("weak", "low", "poor"):
        return "Energy dips today — lighten the load, hydrate, and don't skip rest."
    if s in ("strong", "high", "excellent"):
        return "Energy runs high today — good for exercise and tackling what you've been avoiding."
    return "Energy is even today — keep to routine and you'll end the day with reserves left."


def watch_friction_day() -> str:
    return "Expect small obstacles today — things take longer than planned, so leave margin."


def watch_debt_active() -> str:
    return "An old loose end may resurface today — deal with it cleanly rather than dodging it."


# ── Seed entries for the longer scopes (expanded when those endpoints wire) ──
# Kept minimal and clearly chart-anchored. Phase-2+ fills these out (~200 total).
WEEK_SEEDS = {
    ("timing", "peak_day"):  "{peak_day} is the week's strongest day — schedule the big thing then.",
    ("watch",  "watch_day"): "Go light on {watch_day} — it's the week's friction point.",
}
MONTH_SEEDS = {
    ("money", "income_window"): "An income window opens this month — especially around {best_dates}.",
    ("timing", "major_dates"):  "Mark {best_dates}: the month's clearest stretch for commitments.",
}
YEAR_SEEDS = {
    ("timing", "quarter_arc"):  "Q{quarter} is where the year turns — plan the big move for that stretch.",
    ("work",  "career_inflect"): "A career inflection builds through the year — position for it early, not late.",
}
CYCLE_SEEDS = {
    ("money", "wealth_arc"):     "Wealth accelerates across this multi-year arc, with volatility along the way — build buffers.",
    ("timing", "subperiod"):     "The opening years set the foundation; the later years cash it in.",
}

SCOPE_SEEDS = {
    "week":  WEEK_SEEDS,
    "month": MONTH_SEEDS,
    "year":  YEAR_SEEDS,
    "cycle": CYCLE_SEEDS,
}


def get_seed(scope: str, domain: str, condition: str, **params) -> str:
    """Look up a longer-scope seed template and fill placeholders. '' if absent."""
    table = SCOPE_SEEDS.get(scope, {})
    tmpl = table.get((domain, condition))
    if not tmpl:
        return ""
    try:
        return tmpl.format(**params)
    except Exception:
        return tmpl


# ════════════════════════════════════════════════════════════════════════════
#  LONGER-SCOPE BANKS (Week / Month / Year / Cycle)
#  All English primitives. The month/year engines localize their OWN prose, so
#  highlights are built from non-prose primitives (planet names, enums, dasha
#  lords, dates) and translated downstream by @translate_response — never by
#  re-translating engine prose.
# ════════════════════════════════════════════════════════════════════════════

# Planet -> its dominant life domain (for month strong/weak planet lists).
PLANET_PRIMARY_DOMAIN = {
    "Sun":     "work",
    "Moon":    "mind",
    "Mars":    "work",
    "Mercury": "work",
    "Jupiter": "money",
    "Venus":   "relationships",
    "Saturn":  "work",
    "Rahu":    "opportunity",
    "Ketu":    "mind",
}


def planet_to_domain(planet: str) -> str:
    return PLANET_PRIMARY_DOMAIN.get((planet or "").strip().title(), "work")


# Free-text "area" label (year.areas, priority_actions[].domain) -> locked domain.
_AREA_KEYWORDS = [
    ("money", ("wealth", "money", "finance", "income", "cash", "dinero", "riqueza", "finanz")),
    ("work", ("career", "work", "profession", "job", "business", "carrera", "trabajo", "negocio")),
    ("body", ("health", "body", "vitality", "fitness", "salud", "cuerpo", "vitalidad")),
    ("relationships", ("relationship", "love", "family", "people", "partner", "relacion", "amor", "familia", "pareja")),
    ("mind", ("mind", "spirit", "inner", "peace", "mental", "mente", "espiritu", "paz")),
]


def area_to_domain(area: str) -> str:
    a = (area or "").strip().lower()
    for dom, keys in _AREA_KEYWORDS:
        if any(k in a for k in keys):
            return dom
    return "work"


# ── MONTH banks ─────────────────────────────────────────────────────────────
MONTH_STRONG_BY_DOMAIN = {
    "money":         "Money has momentum this month — push income-generating work and chase what you're owed.",
    "work":          "Work is where the month rewards you — take on the visible, high-stakes projects now.",
    "relationships": "Relationships deepen this month — invest in the people who actually matter.",
    "body":          "Your body holds up well this month — a strong window to build a habit that sticks.",
    "mind":          "Your head is clear this month — plan, learn, and make the calls you've been delaying.",
    "opportunity":   "An unusual opening is live this month — move on it before the window closes.",
}
MONTH_WEAK_BY_DOMAIN = {
    "money":         "Money runs tight this month — defer big purchases and keep a cushion.",
    "work":          "Work feels heavier this month — protect your energy and don't overcommit.",
    "relationships": "Relationships need patience this month — listen more, react less.",
    "body":          "Your body needs more rest this month — don't push through warning signs.",
    "mind":          "Focus scatters this month — simplify and do one thing at a time.",
}
MONTH_ENERGY = {
    "high":     "Energy runs high this month — front-load the ambitious work into the first half.",
    "low":      "Energy runs low this month — pace yourself and guard your recovery.",
    "mixed":    "The month swings between high and low — match effort to the day, not the calendar.",
    "moderate": "The month is steady — consistent effort will outrun any big burst.",
}


# ── YEAR banks ──────────────────────────────────────────────────────────────
YEAR_AREA_BY_DOMAIN = {
    "money":         "Money is a defining theme this year — the chart points to real movement in income.",
    "work":          "Career is where the year concentrates — position early for a step up.",
    "relationships": "Relationships carry weight this year — major bonds form, deepen, or resolve.",
    "body":          "Health earns its place on the list this year — the habits you build now compound.",
    "mind":          "This is an inner-growth year — clarity and perspective are the real gains.",
    "opportunity":   "A door opens this year that wasn't there before — be ready to walk through it.",
}
YEAR_POLARITY = {
    "positive": "The year tilts in your favor — be bold with the big moves, not timid.",
    "negative": "The year asks for discipline — consolidate, and don't expand on credit.",
    "neutral":  "A mixed year — the wins are real, but so are the speed bumps; plan for both.",
    "mixed":    "A mixed year — the wins are real, but so are the speed bumps; plan for both.",
}


def year_chapter(lord: str) -> str:
    """Reframe the current life-chapter signature for the year horizon."""
    sig = DASHA_SIGNATURE.get((lord or "").strip().title())
    if not sig:
        return ""
    domain, text = sig
    # Keep only the lead clause (drops any 'today'-anchored tail), re-anchor to year.
    text = text.split("—")[0].strip().rstrip(".")
    return domain, f"{text} — that's the backdrop for the whole year."


def year_transition(when: str) -> str:
    when = (when or "").strip()
    if when:
        return f"A new life chapter opens around {when} — the ground shifts, so prepare rather than react."
    return "A new life chapter opens later this year — the ground shifts, so prepare rather than react."


# ── WEEK banks (sourced from the 7-day signal array) ────────────────────────
def week_peak(day_label: str) -> str:
    day_label = (day_label or "").strip()
    if day_label:
        return f"{day_label} is the week's strongest day — schedule the thing that matters most then."
    return "Mid-week is the strongest stretch — schedule the thing that matters most then."


def week_watch(day_label: str) -> str:
    day_label = (day_label or "").strip()
    if day_label:
        return f"Go light on {day_label} — it's the week's friction point; leave margin."
    return "One day this week runs rough — keep your calendar loose so you can absorb it."


WEEK_ENERGY = {
    "high": "The week runs high overall — push your boldest work into it.",
    "low":  "The week runs low overall — protect recovery and keep commitments light.",
    "even": "The week is even — steady, unspectacular progress is the play.",
}


WEEK_THEME_BY_DOMAIN = {
    "money":         "Money is the week's recurring thread — most decisions circle back to it, so handle it deliberately.",
    "work":          "Work dominates the week — protect blocks of focus time and don't let it bleed everywhere.",
    "relationships": "People run through the whole week — a few key conversations decide how it goes.",
    "body":          "Your body sets the pace this week — energy management matters more than ambition.",
    "mind":          "The week is mentally demanding — guard your clarity and don't overschedule.",
}


def week_load(friction_count: int) -> str:
    return f"Most of the week runs rough ({friction_count} of 7 days) — keep commitments light and pick your spots."


def week_peak_window(day_label: str, start: str, end: str) -> str:
    day_label = (day_label or "").strip()
    win = " ".join(x for x in [(start or "").strip(), "–" if start and end else "", (end or "").strip()] if x).strip(" –")
    if day_label and win:
        return f"On {day_label}, your clearest window is {win} — line up anything important then."
    if day_label:
        return f"On {day_label}, do the most important thing in the late morning, before the afternoon dip."
    return "Mid-week late mornings are the clearest windows — line up anything important then."


def week_chapter(lord: str) -> str:
    sig = DASHA_SIGNATURE.get((lord or "").strip().title())
    if not sig:
        return ""
    domain, text = sig
    text = text.split("—")[0].strip().rstrip(".")
    return domain, f"{text} — let that steer where this week's effort goes."


# ── CYCLE banks (multi-year arc) ────────────────────────────────────────────
CYCLE_PHASE = {
    "opening":  "You're early in a multi-year chapter — this is the foundation-laying stretch, not the harvest.",
    "building": "You're in the build-out of a multi-year chapter — effort now compounds for years.",
    "peak":     "You're at the peak of a multi-year chapter — cash in what you've built; don't coast.",
    "closing":  "You're closing out a multi-year chapter — tie off loose ends and prepare for the shift.",
}


def cycle_chapter(lord: str) -> str:
    sig = DASHA_SIGNATURE.get((lord or "").strip().title())
    if not sig:
        return ""
    domain, text = sig
    text = text.split("—")[0].strip().rstrip(".")
    return domain, f"{text} — it shapes the whole multi-year arc you're in."


def cycle_event(domain: str, when: str) -> str:
    domain = domain if domain in VALID_DOMAINS else "opportunity"
    when = (when or "").strip()
    base = {
        "money":         "A real money shift is likely",
        "work":          "A career shift is likely",
        "relationships": "A major relationship shift is likely",
        "body":          "A health turning point is likely",
        "mind":          "An inner turning point is likely",
        "opportunity":   "A door is likely to open",
    }.get(domain, "A significant shift is likely")
    if when:
        return domain, f"{base} around {when} — position for it early rather than scrambling late."
    return domain, f"{base} within this arc — position for it early rather than scrambling late."


def cycle_next_shift(when: str) -> str:
    when = (when or "").strip()
    if when:
        return f"The next big turn lands around {when} — the chapter's whole tone changes then."
    return "The next big turn is on the horizon — the chapter's whole tone changes when it lands."


# ════════════════════════════════════════════════════════════════════════════
#  DEEP READ migration — the old FOUNDATION/RELATIONSHIPS/EXPANSION/INNER prose
#  themes collapse into one concise highlight per active theme. Theme keys come
#  from deep_read.py THEME_HOUSES; tone is "supportive" | "friction" | "mixed".
# ════════════════════════════════════════════════════════════════════════════
THEME_DOMAIN = {
    "foundation":    "mind",
    "relationships": "relationships",
    "work":          "work",
    "expansion":     "opportunity",
    "money":         "money",
    "body":          "body",
    "inner":         "mind",
}
THEME_SUPPORTIVE = {
    "foundation":    "Your foundations feel solid today — a good day for home, family, or anything that needs a stable base.",
    "relationships": "Relationships flow today — reach out, repair, or deepen a connection that matters.",
    "work":          "Work has momentum today — push the project that's been waiting for a green light.",
    "expansion":     "Growth is favored today — say yes to the opportunity, the trip, the bigger ask.",
    "money":         "Money matters go smoothly today — handle payments and follow up on what you're owed.",
    "body":          "Your body has good energy today — use it for movement or something you've been putting off.",
    "inner":         "Your inner world is clear today — reflect, release, and let go of what's already done.",
}
THEME_FRICTION = {
    "foundation":    "Foundations feel shaky today — don't overhaul home or living setup; steady the base first.",
    "relationships": "Relationships need care today — listen more than you speak and don't force resolution.",
    "work":          "Work feels uphill today — protect your focus and hold off on big decisions.",
    "expansion":     "Hold back on bold expansion today — the timing for the big move isn't ripe yet.",
    "money":         "Money needs caution today — defer large purchases and double-check the numbers.",
    "body":          "Your body is asking for rest today — ease off and don't push through fatigue.",
    "inner":         "Your inner world feels heavy today — be gentle with yourself; postpone emotional decisions.",
}


def theme_signal(key: str, tone: str):
    """Return (domain, text) for a deep-read theme, or None to skip a flat theme."""
    key = (key or "").strip().lower()
    tone = (tone or "").strip().lower()
    if key not in THEME_DOMAIN:
        return None
    if tone == "friction":
        return "risk", THEME_FRICTION.get(key, "")
    if tone in ("supportive", "mixed"):
        return THEME_DOMAIN[key], THEME_SUPPORTIVE.get(key, "")
    return None  # neutral / unscored themes contribute nothing
