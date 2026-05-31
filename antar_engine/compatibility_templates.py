"""
antar_engine/compatibility_templates.py

Phase-1 prose templates for the 6-layer compatibility surface (POST /api/v1/compat).

Plain English only. No Sanskrit, no planet names as scaffolding, no house numbers.
Templates accept ONLY {a_name} and {b_name} substitutions. {a_name} is the
signed-in user (chart A); {b_name} is the other person (chart B).

Direction lock (prose only — never affects scoring):
  - employee        : A is the SENIOR/employer, B is the report being read.
  - boss-or-manager : A is the JUNIOR/report, B is the manager being read.

Layers (fixed order): soul, chemistry, public, lifepath, communication, friction.
Badges: FLOW (>=75), MIXED (50-74), STRAIN (<50).

Coverage authored in Phase 1:
  - All 90 base lines  (5 reasons x 6 layers x 3 badges)
  - managerial lines for employee + boss-or-manager (2 x 6 x 3 = 36)
  - 21 headlines + 21 details (7 reasons x 3 tiers)
  - 18 generic fallback lines (6 layers x 3 badges) — last-resort, never crash
sales / marketing / finance fall back to the managerial line set until authored.
"""

LAYER_NAMES = {
    "soul":          "Soul & values",
    "chemistry":     "Chemistry & rapport",
    "public":        "Public & visibility",
    "lifepath":      "Lifepath & timing",
    "communication": "Communication & trust",
    "friction":      "Friction & growth",
}

LAYER_ORDER = ["soul", "chemistry", "public", "lifepath", "communication", "friction"]
BADGES = ("FLOW", "MIXED", "STRAIN")

# ── Generic fallback lines (6 layers x 3 badges) ────────────────────────────
# Used only if a specific (reason, layer, badge[, role]) line is missing.
_GENERIC = {
    "soul": {
        "FLOW":   "You and {b_name} are working from the same set of values.",
        "MIXED":  "You and {b_name} share some core values and diverge on others.",
        "STRAIN": "Your values and {b_name}'s pull in different directions.",
    },
    "chemistry": {
        "FLOW":   "The rapport with {b_name} comes easily.",
        "MIXED":  "Rapport with {b_name} is real but takes some warming up.",
        "STRAIN": "The natural rhythm between you and {b_name} is off-beat.",
    },
    "public": {
        "FLOW":   "Together you and {b_name} read well to the outside world.",
        "MIXED":  "How you and {b_name} come across to others is a mixed picture.",
        "STRAIN": "You and {b_name} send mixed signals to the people around you.",
    },
    "lifepath": {
        "FLOW":   "Your timing and {b_name}'s are moving in step right now.",
        "MIXED":  "Your seasons and {b_name}'s only partly overlap.",
        "STRAIN": "You and {b_name} are in different seasons at the moment.",
    },
    "communication": {
        "FLOW":   "You and {b_name} understand each other quickly.",
        "MIXED":  "Communication with {b_name} works with some deliberate effort.",
        "STRAIN": "You and {b_name} talk past each other more than you'd like.",
    },
    "friction": {
        "FLOW":   "There's little hidden friction between you and {b_name}.",
        "MIXED":  "Some friction sits under the surface with {b_name} — manageable.",
        "STRAIN": "There's real friction to navigate between you and {b_name}.",
    },
}

# ── Base reason lines: 5 reasons x 6 layers x 3 badges = 90 ──────────────────
_BASE_LINES = {
    "romantic": {
        "soul": {
            "FLOW":   "At the deepest level you and {b_name} want the same things from life.",
            "MIXED":  "Your core values and {b_name}'s mostly align, with a few real differences to honor.",
            "STRAIN": "What you treasure and what {b_name} treasures aren't the same — name it early.",
        },
        "chemistry": {
            "FLOW":   "The attraction and ease with {b_name} is natural and unforced.",
            "MIXED":  "There's real chemistry with {b_name}, though it needs tending to stay alive.",
            "STRAIN": "The spark with {b_name} runs hot and cold — closeness takes conscious effort.",
        },
        "public": {
            "FLOW":   "As a couple you and {b_name} are read warmly by the people around you.",
            "MIXED":  "How you show up together is fine, if not the headline of this match.",
            "STRAIN": "The way you and {b_name} present as a pair can feel out of sync to others.",
        },
        "lifepath": {
            "FLOW":   "Your life chapters and {b_name}'s are opening in the same direction right now.",
            "MIXED":  "You and {b_name} are partly in step on timing — some seasons align, some don't.",
            "STRAIN": "You and {b_name} are in different life seasons, which tests patience.",
        },
        "communication": {
            "FLOW":   "You and {b_name} feel heard by each other; trust comes easily.",
            "MIXED":  "You and {b_name} communicate well once you name how you each process things.",
            "STRAIN": "You move at different speeds than {b_name} — hold space before stress hits.",
        },
        "friction": {
            "FLOW":   "Little hidden tension sits between you and {b_name}.",
            "MIXED":  "Some friction with {b_name} is workable if you stay honest about it.",
            "STRAIN": "There's a friction pattern with {b_name} that the relationship will keep teaching you.",
        },
    },
    "business": {
        "soul": {
            "FLOW":   "Your values align with {b_name}'s — the partnership rests on shared ground.",
            "MIXED":  "You and {b_name} hold different priorities; workable if you name them early.",
            "STRAIN": "Your sense of what matters pulls against {b_name}'s — expect tension over priorities.",
        },
        "chemistry": {
            "FLOW":   "Working day-to-day with {b_name} flows easily.",
            "MIXED":  "The working rapport with {b_name} is solid once you find your rhythm.",
            "STRAIN": "The day-to-day working style with {b_name} grates until you build structure.",
        },
        "public": {
            "FLOW":   "To clients and partners, you and {b_name} read as a credible team.",
            "MIXED":  "Your public face as a team with {b_name} is workable but uneven.",
            "STRAIN": "You and {b_name} project different things to the market — align the story.",
        },
        "lifepath": {
            "FLOW":   "You and {b_name} are in matching seasons — good timing to build together.",
            "MIXED":  "Your timing and {b_name}'s partly line up; sequence the big moves carefully.",
            "STRAIN": "You and {b_name} are on different clocks right now — pace the commitments.",
        },
        "communication": {
            "FLOW":   "You and {b_name} negotiate and decide cleanly together.",
            "MIXED":  "You and {b_name} communicate well with agreed channels and written follow-ups.",
            "STRAIN": "You and {b_name} read situations differently — put decisions in writing.",
        },
        "friction": {
            "FLOW":   "Little structural friction sits between you and {b_name}.",
            "MIXED":  "Some friction with {b_name} is manageable with clear roles and reviews.",
            "STRAIN": "There's real friction with {b_name} that needs discipline to clear.",
        },
    },
    "cofounder": {
        "soul": {
            "FLOW":   "You and {b_name} are building toward the same mission at heart.",
            "MIXED":  "Your missions overlap with {b_name}'s but aren't identical — align on the 'why'.",
            "STRAIN": "What drives you and what drives {b_name} point at different futures.",
        },
        "chemistry": {
            "FLOW":   "You and {b_name} click under pressure — the working bond holds.",
            "MIXED":  "You and {b_name} work well together once trust is earned in the trenches.",
            "STRAIN": "Under pressure you and {b_name} default to different modes that clash.",
        },
        "public": {
            "FLOW":   "As founders you and {b_name} present as a power pair to the room.",
            "MIXED":  "Your founder image with {b_name} is solid but needs clearer role lines.",
            "STRAIN": "You and {b_name} compete for the same spotlight — divide the stage.",
        },
        "lifepath": {
            "FLOW":   "Your runways and {b_name}'s line up for years of building together.",
            "MIXED":  "You and {b_name} share a few aligned years — plan around the gaps.",
            "STRAIN": "Your timelines diverge from {b_name}'s — the shared runway is short.",
        },
        "communication": {
            "FLOW":   "You and {b_name} can have hard conversations without breaking trust.",
            "MIXED":  "You and {b_name} communicate well if you name the pattern before stress hits.",
            "STRAIN": "You and {b_name} handle conflict differently — build a conflict protocol now.",
        },
        "friction": {
            "FLOW":   "Little destructive friction sits between you and {b_name}.",
            "MIXED":  "Friction with {b_name} is survivable with clear equity and roles.",
            "STRAIN": "There's a friction pattern with {b_name} that will surface at the first hard pivot.",
        },
    },
    "friend": {
        "soul": {
            "FLOW":   "You and {b_name} see the world through a similar lens.",
            "MIXED":  "You and {b_name} share a lot and differ on a few things that matter.",
            "STRAIN": "You and {b_name} value different things at the core of the friendship.",
        },
        "chemistry": {
            "FLOW":   "Time with {b_name} is easy and energizing.",
            "MIXED":  "You and {b_name} enjoy each other, though the energy varies.",
            "STRAIN": "Your natural energy and {b_name}'s don't always match up.",
        },
        "public": {
            "FLOW":   "In a group, you and {b_name} bring out the best in the room.",
            "MIXED":  "You and {b_name} are fine in a crowd, closer one-on-one.",
            "STRAIN": "In groups you and {b_name} pull in different social directions.",
        },
        "lifepath": {
            "FLOW":   "You and {b_name} are in life seasons that keep you close right now.",
            "MIXED":  "Your seasons and {b_name}'s overlap enough to stay connected with effort.",
            "STRAIN": "You and {b_name} are in different chapters — staying close takes intention.",
        },
        "communication": {
            "FLOW":   "You and {b_name} get each other quickly and forgive easily.",
            "MIXED":  "You and {b_name} talk well once you account for different styles.",
            "STRAIN": "You and {b_name} misread each other unless you say things plainly.",
        },
        "friction": {
            "FLOW":   "Little hidden friction sits between you and {b_name}.",
            "MIXED":  "Some friction with {b_name} is easy to absorb if you address it lightly.",
            "STRAIN": "There's a recurring friction with {b_name} worth naming out loud.",
        },
    },
    "family": {
        "soul": {
            "FLOW":   "You and {b_name} share a deep, values-level bond.",
            "MIXED":  "You and {b_name} are bonded but hold some genuinely different values.",
            "STRAIN": "You and {b_name} love each other across a real values gap.",
        },
        "chemistry": {
            "FLOW":   "Being around {b_name} feels natural and steadying.",
            "MIXED":  "Time with {b_name} is warm, with the usual family ups and downs.",
            "STRAIN": "The day-to-day rhythm with {b_name} can rub, even with love underneath.",
        },
        "public": {
            "FLOW":   "To the wider family, you and {b_name} present a united front.",
            "MIXED":  "How you and {b_name} appear to relatives is mostly steady.",
            "STRAIN": "You and {b_name} get read differently by the family — mind the dynamics.",
        },
        "lifepath": {
            "FLOW":   "Your life seasons and {b_name}'s support each other right now.",
            "MIXED":  "You and {b_name} are partly in step — some seasons help, some strain.",
            "STRAIN": "You and {b_name} are in different seasons, which colors the relationship now.",
        },
        "communication": {
            "FLOW":   "You and {b_name} can speak openly and be understood.",
            "MIXED":  "You and {b_name} communicate well when you slow down and listen.",
            "STRAIN": "You and {b_name} fall into old patterns — name them to break them.",
        },
        "friction": {
            "FLOW":   "Little unspoken friction sits between you and {b_name}.",
            "MIXED":  "Some friction with {b_name} is manageable with a little patience.",
            "STRAIN": "There's a long-standing friction with {b_name} the bond keeps surfacing.",
        },
    },
}

# ── New-reason lines (direction-locked), managerial role authored ───────────
# employee: A = senior/employer reading B (the report).
# boss-or-manager: A = junior/report reading B (the manager).
_NEW_LINES = {
    "employee": {
        "managerial": {
            "soul": {
                "FLOW":   "{b_name}'s sense of what matters lines up with how you run things.",
                "MIXED":  "{b_name} holds some different priorities than you do — set expectations early.",
                "STRAIN": "{b_name} is driven by different things than the role rewards — watch the fit.",
            },
            "chemistry": {
                "FLOW":   "{b_name} will settle into your way of working quickly.",
                "MIXED":  "{b_name} finds a rhythm with you after a clear onboarding.",
                "STRAIN": "{b_name}'s working style takes real adjustment to fit how you operate.",
            },
            "public": {
                "FLOW":   "{b_name} will represent you cleanly — their visible work reflects what you'd want shown.",
                "MIXED":  "{b_name} represents you reasonably; give clear guidance on the external story.",
                "STRAIN": "{b_name} may present the work differently than you'd choose — align on the message.",
            },
            "lifepath": {
                "FLOW":   "{b_name} is in a season that fits steady commitment to your team right now.",
                "MIXED":  "{b_name}'s timing partly fits the role — expect some pull from other priorities.",
                "STRAIN": "{b_name} is in a season that may pull them elsewhere before long.",
            },
            "communication": {
                "FLOW":   "{b_name} takes direction well and keeps you in the loop.",
                "MIXED":  "{b_name} communicates well once you set the cadence and channels.",
                "STRAIN": "{b_name} processes direction differently — be explicit and confirm in writing.",
            },
            "friction": {
                "FLOW":   "Little friction sits between how you lead and how {b_name} works.",
                "MIXED":  "Some friction with {b_name} is manageable with clear structure and check-ins.",
                "STRAIN": "There's a friction pattern with {b_name} that will need active managing.",
            },
        },
    },
    "boss-or-manager": {
        "managerial": {
            "soul": {
                "FLOW":   "What {b_name} stands for lines up with what you want from your work.",
                "MIXED":  "You and {b_name} value some different things — know where they'll push you.",
                "STRAIN": "{b_name} is driven by different things than you are — expect values tension.",
            },
            "chemistry": {
                "FLOW":   "You'll find your footing under {b_name} quickly.",
                "MIXED":  "Working under {b_name} settles once you learn their rhythm.",
                "STRAIN": "{b_name}'s working style will take real adjustment on your side.",
            },
            "public": {
                "FLOW":   "{b_name} will show your work in a good light to the people above.",
                "MIXED":  "{b_name} represents your work reasonably; make your contributions visible.",
                "STRAIN": "{b_name} may not surface your work the way you'd want — be proactive about visibility.",
            },
            "lifepath": {
                "FLOW":   "{b_name} is in a season that supports investing in you right now.",
                "MIXED":  "{b_name}'s timing partly supports your growth — some windows are better than others.",
                "STRAIN": "{b_name} is in a season focused elsewhere — don't expect heavy mentorship now.",
            },
            "communication": {
                "FLOW":   "{b_name} gives clear direction and is easy to read.",
                "MIXED":  "{b_name} communicates well once you learn how they like to be updated.",
                "STRAIN": "{b_name} communicates differently than you'd prefer — ask for specifics early.",
            },
            "friction": {
                "FLOW":   "Little friction sits between how {b_name} manages and how you work.",
                "MIXED":  "Some friction under {b_name} is manageable if you name it respectfully.",
                "STRAIN": "There's a friction pattern with {b_name} you'll need to navigate carefully.",
            },
        },
    },
}

# ── Headlines: 7 reasons x 3 tiers ──────────────────────────────────────────
_HEADLINES = {
    "romantic": {
        "FLOW":   "A love that moves in step — ease now, depth over time.",
        "MIXED":  "Real love with real edges — it works when you both stay honest.",
        "STRAIN": "A demanding, growth-heavy connection — beautiful, but it asks a lot.",
    },
    "business": {
        "FLOW":   "Two builders whose energies move in step — this partnership compounds.",
        "MIXED":  "Two builders who pull in different directions — but harder together than alone, if you mind the gaps.",
        "STRAIN": "Two builders whose timing doesn't match — this needs real discipline to clear the friction.",
    },
    "cofounder": {
        "FLOW":   "A rare founder match — complementary edges and a shared runway.",
        "MIXED":  "A strong founder fit with clear gaps — define roles and equity early.",
        "STRAIN": "Different chapters, different missions — this would be high-maintenance to build.",
    },
    "friend": {
        "FLOW":   "An easy, energizing friendship that holds across seasons.",
        "MIXED":  "A good friendship that stays close with a little intention.",
        "STRAIN": "A friendship across a real gap — it survives on effort, not autopilot.",
    },
    "family": {
        "FLOW":   "A steadying bond — love and rhythm both pulling the same way.",
        "MIXED":  "A warm bond with the usual family edges — patience carries it.",
        "STRAIN": "Deep love across a real gap — the relationship keeps asking for understanding.",
    },
    "employee": {
        "FLOW":   "A strong fit for the role — {b_name} should slot in and deliver.",
        "MIXED":  "A workable fit — {b_name} can do well here with clear structure.",
        "STRAIN": "A stretch fit — {b_name} would need active managing to thrive in this role.",
    },
    "boss-or-manager": {
        "FLOW":   "A manager you can grow under — {b_name}'s style fits how you work.",
        "MIXED":  "A workable manager fit — you'll do well under {b_name} with clear expectations.",
        "STRAIN": "A demanding fit — working under {b_name} will take real adjustment.",
    },
}

# ── Details: 7 reasons x 3 tiers ────────────────────────────────────────────
_DETAILS = {
    "romantic": {
        "FLOW":   "{a_name} and {b_name} share a foundation that supports both ease and depth. The pattern favors a relationship that feels natural now and grows sturdier over time, as long as you keep choosing each other.",
        "MIXED":  "{a_name} and {b_name} have genuine connection alongside genuine differences. This is a relationship that rewards honesty — name the gaps early and they become growth rather than grievance.",
        "STRAIN": "{a_name} and {b_name} carry a connection that runs intense and growth-heavy. It won't always feel easy; it will feel necessary. The question isn't whether you're compatible but whether you're both ready to grow.",
    },
    "business": {
        "FLOW":   "{a_name} and {b_name} bring complementary strengths to a working partnership. The pattern supports steady building, shared decisions, and the kind of trust that compounds over years rather than months.",
        "MIXED":  "{a_name} and {b_name} can build something real, with a few areas that need structure. Clear roles, written agreements, and named expectations turn the friction into a productive division of labor.",
        "STRAIN": "{a_name} and {b_name} are on different clocks and read situations differently. A partnership is possible, but only with strong structure — defined roles, written decisions, and regular reviews to clear the friction.",
    },
    "cofounder": {
        "FLOW":   "{a_name} and {b_name} show a rare founder alignment — complementary roles and years of shared runway. This is the kind of pairing you can build on without second-guessing the foundation.",
        "MIXED":  "{a_name} and {b_name} have a strong cofounder fit with specific gaps to close. Settle equity, roles, and decision rights early and the partnership can carry real weight.",
        "STRAIN": "{a_name} and {b_name} are building toward different futures on different timelines. A venture together would be high-maintenance — go in clear-eyed about where the strain will surface.",
    },
    "friend": {
        "FLOW":   "{a_name} and {b_name} have an easy, energizing friendship that tends to hold through life's changes. Little maintenance required — the connection refills itself.",
        "MIXED":  "{a_name} and {b_name} have a solid friendship that stays close with a little intention. Keep showing up through the off-seasons and it deepens.",
        "STRAIN": "{a_name} and {b_name} are good for each other across a real gap in rhythm or values. The friendship lasts on effort and honesty rather than autopilot.",
    },
    "family": {
        "FLOW":   "{a_name} and {b_name} share a steadying family bond where love and daily rhythm pull the same way. A relationship that supports both people through the long arc.",
        "MIXED":  "{a_name} and {b_name} have a warm bond with the ordinary family edges. Patience and a little listening carry it through the friction.",
        "STRAIN": "{a_name} and {b_name} love each other across a real values or rhythm gap. The bond endures, but it keeps asking both people for understanding and room.",
    },
    "employee": {
        "FLOW":   "Read as a role fit, {b_name} should settle into how {a_name} runs things and deliver with little friction. Set the expectations once and expect steady, reliable work.",
        "MIXED":  "Read as a role fit, {b_name} can do well for {a_name} with clear structure and onboarding. The gaps are workable; name them and put a cadence in place.",
        "STRAIN": "Read as a role fit, {b_name} would need active managing to thrive under {a_name}. Be honest about where the friction sits before committing to the placement.",
    },
    "boss-or-manager": {
        "FLOW":   "Read as a reporting fit, {a_name} should grow well under {b_name} — their style and timing support investing in you. A manager worth learning from.",
        "MIXED":  "Read as a reporting fit, {a_name} can do well under {b_name} with clear expectations on both sides. Learn their rhythm and make your work visible.",
        "STRAIN": "Read as a reporting fit, working under {b_name} will take real adjustment for {a_name}. Get specifics early and be proactive about how your contributions are seen.",
    },
}


# ── Accessors (handle fallback + safe formatting) ───────────────────────────

def _fmt(tmpl: str, a_name: str, b_name: str) -> str:
    try:
        return tmpl.format(a_name=a_name, b_name=b_name)
    except Exception:
        return tmpl


def get_line(reason: str, layer: str, badge: str, role: str | None,
             a_name: str, b_name: str) -> str:
    """Resolve a one-sentence layer line with full fallback chain."""
    tmpl = None
    if reason in _NEW_LINES:
        role_key = role if (role and role in _NEW_LINES[reason]) else "managerial"
        tmpl = (_NEW_LINES[reason].get(role_key, {}).get(layer, {}).get(badge)
                or _NEW_LINES[reason].get("managerial", {}).get(layer, {}).get(badge))
    else:
        tmpl = _BASE_LINES.get(reason, {}).get(layer, {}).get(badge)
    if not tmpl:
        tmpl = _GENERIC.get(layer, {}).get(badge, "")
    return _fmt(tmpl, a_name, b_name)


def get_headline(reason: str, tier: str, a_name: str, b_name: str) -> str:
    tmpl = _HEADLINES.get(reason, {}).get(tier) or _HEADLINES["business"][tier]
    return _fmt(tmpl, a_name, b_name)


def get_detail(reason: str, tier: str, a_name: str, b_name: str) -> str:
    tmpl = _DETAILS.get(reason, {}).get(tier) or _DETAILS["business"][tier]
    return _fmt(tmpl, a_name, b_name)


def template_counts() -> dict:
    """Self-report authored coverage (used by the verification harness)."""
    base = sum(len(b) for r in _BASE_LINES.values() for b in r.values())
    new = sum(len(b) for r in _NEW_LINES.values() for role in r.values()
              for b in role.values())
    return {
        "base_lines": base,                       # expect 90
        "new_role_lines": new,                    # expect 36 (managerial x2)
        "headlines": sum(len(t) for t in _HEADLINES.values()),  # 21
        "details": sum(len(t) for t in _DETAILS.values()),      # 21
        "generic_fallback": sum(len(b) for b in _GENERIC.values()),  # 18
    }
