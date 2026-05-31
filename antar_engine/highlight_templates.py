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
