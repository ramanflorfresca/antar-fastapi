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

# ── Role-specific lines ─────────────────────────────────────────────────────
# Previously only "managerial" existed, so get_line() fell back to it for
# sales/marketing/finance and all four roles produced identical copy — the role
# picker changed the score by a point or two and nothing a user could read.
# These are written per function: a sales seat fails differently than a finance
# seat, and the line should say so.

_NEW_LINES["employee"]["sales"] = {
    "soul": {
        "FLOW":   "{b_name} wants what a sales seat rewards — the drive is real, not performed.",
        "MIXED":  "{b_name} will chase the number, but check what they think they're selling.",
        "STRAIN": "{b_name} isn't motivated by what this seat pays out — quota will feel like a costume.",
    },
    "chemistry": {
        "FLOW":   "{b_name} builds rapport fast — the thing you can't train.",
        "MIXED":  "{b_name} warms up after a cycle or two; early calls will be stiffer than later ones.",
        "STRAIN": "Rapport is effortful for {b_name} — expect a longer ramp on relationship-led deals.",
    },
    "public": {
        "FLOW":   "{b_name} carries your name well in the room — put them in front of buyers.",
        "MIXED":  "{b_name} represents you fine; brief them tightly before the big meetings.",
        "STRAIN": "Watch how {b_name} tells your story externally — the pitch may drift.",
    },
    "lifepath": {
        "FLOW":   "{b_name}'s timing supports a push — they have the appetite for a heavy quarter.",
        "MIXED":  "{b_name}'s attention is partly elsewhere; a big number this year is a stretch, not a gift.",
        "STRAIN": "This isn't {b_name}'s season for grind — pipeline will slip before they say so.",
    },
    "communication": {
        "FLOW":   "{b_name} handles objections cleanly and updates you without being chased.",
        "MIXED":  "{b_name} sells well but reports unevenly — set a forecast cadence early.",
        "STRAIN": "{b_name} goes quiet under pressure, which is when you most need the truth.",
    },
    "friction": {
        "FLOW":   "{b_name} takes rejection without carrying it — that's rare and worth paying for.",
        "MIXED":  "Losses land harder on {b_name} than they'll admit; check in after a bad month.",
        "STRAIN": "Rejection sticks to {b_name} — churn risk is real in a high-no seat.",
    },
}

_NEW_LINES["employee"]["marketing"] = {
    "soul": {
        "FLOW":   "{b_name} believes in the kind of thing you're building — taste and mission line up.",
        "MIXED":  "{b_name}'s instincts differ from your brand in places; align on the story before the spend.",
        "STRAIN": "{b_name} would build a different brand than the one you have.",
    },
    "chemistry": {
        "FLOW":   "{b_name} reads a room and an audience the same way you do.",
        "MIXED":  "{b_name}'s read on the audience is decent but needs your correction on tone.",
        "STRAIN": "{b_name}'s sense of what appeals runs against yours — expect creative rounds.",
    },
    "public": {
        "FLOW":   "{b_name} is a genuine asset to how the market sees you.",
        "MIXED":  "{b_name} handles the public story competently; keep approval on the big swings.",
        "STRAIN": "{b_name}'s public instincts could cost you brand equity — supervise external work.",
    },
    "lifepath": {
        "FLOW":   "{b_name} is in a building season — good for a brand that needs patient compounding.",
        "MIXED":  "{b_name} can run campaigns now but a long brand arc may outlast their focus.",
        "STRAIN": "{b_name}'s timing favours short bursts, not the slow work brand actually needs.",
    },
    "communication": {
        "FLOW":   "{b_name} writes and briefs clearly — the message survives the handoff.",
        "MIXED":  "{b_name} communicates well in one register; test them outside their comfort format.",
        "STRAIN": "Message discipline is the risk with {b_name} — expect drift between channels.",
    },
    "friction": {
        "FLOW":   "{b_name} takes creative criticism as material, not injury.",
        "MIXED":  "{b_name} defends their work harder than they take notes — keep feedback specific.",
        "STRAIN": "Critique lands personally with {b_name} — creative review will be costly.",
    },
}

_NEW_LINES["employee"]["finance"] = {
    "soul": {
        "FLOW":   "{b_name} is genuinely motivated by order and correctness — the seat suits them.",
        "MIXED":  "{b_name} values some things this seat doesn't reward; confirm they want the rigour.",
        "STRAIN": "{b_name} is not built for a role where being right matters more than being fast.",
    },
    "chemistry": {
        "FLOW":   "{b_name} works easily with you without needing much social scaffolding.",
        "MIXED":  "{b_name} is more transactional with you than warm — fine for the function.",
        "STRAIN": "Working closely with {b_name} takes effort; keep the interface formal.",
    },
    "public": {
        "FLOW":   "{b_name} can face auditors, investors, or a board without you in the room.",
        "MIXED":  "{b_name} handles external financial conversations adequately with prep.",
        "STRAIN": "Don't put {b_name} in front of investors or auditors unaccompanied.",
    },
    "lifepath": {
        "FLOW":   "{b_name}'s season supports steady, unglamorous work — exactly what closes books.",
        "MIXED":  "{b_name} can hold the cadence, though month-end may compete with other pulls.",
        "STRAIN": "{b_name}'s timing pulls toward change, which is the wrong energy for controls.",
    },
    "communication": {
        "FLOW":   "{b_name} raises problems early and in writing — the trait that prevents surprises.",
        "MIXED":  "{b_name} reports accurately but late, or on time but thin — pick your cadence.",
        "STRAIN": "{b_name} tends to sit on bad numbers. In finance that's the expensive failure.",
    },
    "friction": {
        "FLOW":   "{b_name} holds the line on process without making it personal.",
        "MIXED":  "{b_name} bends on process under pressure — decide now which controls are hard.",
        "STRAIN": "{b_name} avoids the confrontation that enforcing controls requires.",
    },
}

# Working *under* someone in that function — the same six layers, read from
# the other direction.
_NEW_LINES["boss-or-manager"]["sales"] = {
    "soul": {
        "FLOW":   "{b_name} measures what you also think matters — you'll agree on what a win is.",
        "MIXED":  "{b_name} defines success by the number; make sure that's a game you want.",
        "STRAIN": "{b_name} rewards things you don't value — you'll feel it in every review.",
    },
    "chemistry": {
        "FLOW":   "{b_name} likes working with you, and in a sales org that opens doors.",
        "MIXED":  "You'll get on with {b_name} once you've delivered a quarter.",
        "STRAIN": "You and {b_name} don't click naturally — your numbers will have to speak.",
    },
    "public": {
        "FLOW":   "{b_name} sells your wins upward — credit reaches the people who matter.",
        "MIXED":  "{b_name} shares credit unevenly; make your contribution legible yourself.",
        "STRAIN": "{b_name} takes the room. Expect to fight to be seen.",
    },
    "lifepath": {
        "FLOW":   "{b_name} is in a season of expansion — good years to be on their team.",
        "MIXED":  "{b_name}'s trajectory supports you in some windows, not all.",
        "STRAIN": "{b_name} is in a contracting phase; their pressure will land on you.",
    },
    "communication": {
        "FLOW":   "{b_name} gives you the number, the context, and the reason behind both.",
        "MIXED":  "{b_name} tells you what to hit, not always why — ask for the reasoning.",
        "STRAIN": "{b_name} communicates in targets and silence. You'll be guessing.",
    },
    "friction": {
        "FLOW":   "{b_name} handles a bad month without turning it on you.",
        "MIXED":  "{b_name} gets sharp when the pipeline thins — don't take it as a verdict.",
        "STRAIN": "{b_name} manages by pressure when numbers slip. Know that before you sign.",
    },
}

_NEW_LINES["boss-or-manager"]["marketing"] = {
    "soul": {
        "FLOW":   "You and {b_name} would build the same brand — taste is aligned at the root.",
        "MIXED":  "{b_name}'s taste overlaps yours but isn't it; expect to bend on some work.",
        "STRAIN": "{b_name} wants a brand you don't believe in. That gets tiring fast.",
    },
    "chemistry": {
        "FLOW":   "{b_name} gets your instincts without long explanation.",
        "MIXED":  "{b_name} comes around to your ideas — usually a round or two later.",
        "STRAIN": "Your creative instincts read as wrong to {b_name} on first pass.",
    },
    "public": {
        "FLOW":   "{b_name} puts your work in front of the right people with your name on it.",
        "MIXED":  "{b_name} shows the work upward, though not always with attribution.",
        "STRAIN": "Your work will travel under {b_name}'s name more than yours.",
    },
    "lifepath": {
        "FLOW":   "{b_name}'s season supports patient brand work — you'll be allowed to build.",
        "MIXED":  "{b_name} will back long work in some quarters and demand numbers in others.",
        "STRAIN": "{b_name} needs short-term proof right now. Brand work will be squeezed.",
    },
    "communication": {
        "FLOW":   "{b_name} gives usable creative direction — specific, not vibes.",
        "MIXED":  "{b_name}'s feedback needs translating; ask for examples rather than adjectives.",
        "STRAIN": "{b_name} critiques by feel and changes their mind. Get decisions in writing.",
    },
    "friction": {
        "FLOW":   "Disagreements with {b_name} stay about the work.",
        "MIXED":  "Creative disagreement with {b_name} is survivable if you pick your battles.",
        "STRAIN": "Pushing back on {b_name}'s taste costs you standing. Weigh that.",
    },
}

_NEW_LINES["boss-or-manager"]["finance"] = {
    "soul": {
        "FLOW":   "You and {b_name} both think being right matters more than being quick.",
        "MIXED":  "{b_name} weighs risk differently than you — worth surfacing before it's live.",
        "STRAIN": "{b_name}'s relationship with risk and rules isn't yours. That's a hard mismatch.",
    },
    "chemistry": {
        "FLOW":   "{b_name} is straightforward to work with — no politics tax.",
        "MIXED":  "{b_name} keeps it professional and cool; don't read distance as disapproval.",
        "STRAIN": "The working relationship with {b_name} will stay effortful.",
    },
    "public": {
        "FLOW":   "{b_name} backs your numbers in the room, which is the whole job.",
        "MIXED":  "{b_name} supports your work externally with preparation.",
        "STRAIN": "{b_name} may not defend your numbers when they're questioned. Document everything.",
    },
    "lifepath": {
        "FLOW":   "{b_name} is in a steady season — good for learning the craft properly.",
        "MIXED":  "{b_name}'s focus shifts; some periods will be well-supervised and some won't.",
        "STRAIN": "{b_name} is distracted right now. In finance that means you carry the risk.",
    },
    "communication": {
        "FLOW":   "{b_name} is exact about what they want and when. You'll rarely be surprised.",
        "MIXED":  "{b_name} assumes context you may not have — confirm the ask in writing.",
        "STRAIN": "{b_name} is vague until the deadline, then precise about what's wrong.",
    },
    "friction": {
        "FLOW":   "{b_name} takes a flagged error as useful, not as an accusation.",
        "MIXED":  "{b_name} is uneven about bad news — lead with the fix.",
        "STRAIN": "Raising a problem to {b_name} carries a cost. That's dangerous in this function.",
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


# ── V2: per-layer short headlines (6 layers x 3 badges = 18) ────────────────
_LAYER_HEADLINES = {
    "soul": {
        "FLOW": "Deep values resonance.", "MIXED": "Shared ground, real differences.",
        "STRAIN": "Values pull apart.",
    },
    "chemistry": {
        "FLOW": "Natural, easy attraction.", "MIXED": "Real spark, needs tending.",
        "STRAIN": "Off-beat rhythm.",
    },
    "public": {
        "FLOW": "Read well by the world.", "MIXED": "A mixed public picture.",
        "STRAIN": "Mixed signals to others.",
    },
    "lifepath": {
        "FLOW": "Timing moves in step.", "MIXED": "Seasons partly overlap.",
        "STRAIN": "Different life seasons.",
    },
    "communication": {
        "FLOW": "You understand each other.", "MIXED": "Works with deliberate effort.",
        "STRAIN": "You talk past each other.",
    },
    "friction": {
        "FLOW": "Little hidden friction.", "MIXED": "Manageable friction underneath.",
        "STRAIN": "Real friction to navigate.",
    },
}

# Tier (HIGH/MID/LOW) <-> badge (FLOW/MIXED/STRAIN) for V2 template keys.
_TIER_TO_BADGE = {"HIGH": "FLOW", "MID": "MIXED", "LOW": "STRAIN"}


def v2_layer_headline(layer: str, badge: str) -> str:
    return _LAYER_HEADLINES.get(layer, {}).get(badge, "")


def v2_layer_prose(reason: str, layer: str, badge: str, role, a_name: str, b_name: str) -> tuple:
    """(headline, detail) for one layer. detail reuses the authored line set."""
    headline = v2_layer_headline(layer, badge)
    detail = get_line(reason, layer, badge, role, a_name, b_name)
    return headline, detail


def v2_overall(reason: str, badge: str, a_name: str, b_name: str) -> tuple:
    """(headline, summary) for the overall read."""
    return get_headline(reason, badge, a_name, b_name), get_detail(reason, badge, a_name, b_name)


def _build_v2_templates() -> dict:
    """
    Coverage artifact keyed (reason, layer, TIER) — composed from the authored
    line sets so the V2 deliverable exposes the documented TEMPLATES table.
    """
    out = {}
    for reason in ("romantic", "business", "cofounder", "friend", "family"):
        for layer in LAYER_ORDER:
            for tier, badge in _TIER_TO_BADGE.items():
                out[(reason, layer, tier)] = _BASE_LINES[reason][layer][badge]
    for reason in ("employee", "boss-or-manager"):
        for layer in LAYER_ORDER:
            for tier, badge in _TIER_TO_BADGE.items():
                out[(reason, layer, tier)] = _NEW_LINES[reason]["managerial"][layer][badge]
    return out


TEMPLATES = _build_v2_templates()  # 7 x 6 x 3 = 126 line templates


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


# ── Additional specialist roles (employee direction only) ───────────────────
# One-way by design: these read "how will this person be, working for me".

_NEW_LINES["employee"]["social"] = {
    "soul": {
        "FLOW":   "{b_name} actually cares about the audience, not just the metrics.",
        "MIXED":  "{b_name} will chase engagement — decide now whether that's the goal.",
        "STRAIN": "{b_name} wants attention for its own sake. Your brand will pay for it.",
    },
    "chemistry": {
        "FLOW":   "{b_name} has the instinct for tone that can't be briefed into someone.",
        "MIXED":  "{b_name} finds the voice eventually; the first months will read as off-brand.",
        "STRAIN": "{b_name}'s natural register isn't your audience's. That gap shows publicly.",
    },
    "public": {
        "FLOW":   "{b_name} is safe with the keys to your public accounts.",
        "MIXED":  "{b_name} handles the feed well; keep approval on anything reactive.",
        "STRAIN": "{b_name} posting unsupervised is a real risk — put a review gate in place.",
    },
    "lifepath": {
        "FLOW":   "{b_name} is in a visible season — their reach compounds while they're with you.",
        "MIXED":  "{b_name} can hold a calendar, but the always-on cadence may wear thin.",
        "STRAIN": "The relentlessness of social will burn {b_name} out in this period.",
    },
    "communication": {
        "FLOW":   "{b_name} writes fast and on-message, and knows when not to reply.",
        "MIXED":  "{b_name} is quick but uneven — agree the escalation rule for a pile-on.",
        "STRAIN": "{b_name} answers publicly from the gut. That's how a small issue becomes a day.",
    },
    "friction": {
        "FLOW":   "{b_name} handles a bad comment thread without absorbing it.",
        "MIXED":  "Criticism online sticks to {b_name} more than they let on.",
        "STRAIN": "{b_name} takes a pile-on personally and will escalate rather than de-escalate.",
    },
}

_NEW_LINES["employee"]["operations"] = {
    "soul": {
        "FLOW":   "{b_name} genuinely likes order — this is the rare person who wants the job.",
        "MIXED":  "{b_name} tolerates process without loving it; expect drift without check-ins.",
        "STRAIN": "{b_name} is bored by process, and ops is mostly process.",
    },
    "chemistry": {
        "FLOW":   "{b_name} coordinates across your team without friction.",
        "MIXED":  "{b_name} works well with some of your team and not others — watch the seams.",
        "STRAIN": "{b_name} rubs people the wrong way, which is expensive in a coordinating seat.",
    },
    "public": {
        "FLOW":   "{b_name} can hold vendor and partner relationships on your behalf.",
        "MIXED":  "{b_name} manages suppliers adequately; keep the big negotiations yourself.",
        "STRAIN": "Don't hand {b_name} your vendor relationships without oversight.",
    },
    "lifepath": {
        "FLOW":   "{b_name} is in a consolidating season — the right energy for building systems.",
        "MIXED":  "{b_name} can maintain the machine, though rebuilding it may be a stretch now.",
        "STRAIN": "{b_name} is in a restless phase. Ops needs someone who wants the steady grind.",
    },
    "communication": {
        "FLOW":   "{b_name} closes loops and tells you what slipped before you ask.",
        "MIXED":  "{b_name} keeps things moving but reports thinly — ask for written status.",
        "STRAIN": "{b_name} lets things slip quietly. In ops, silence is the failure mode.",
    },
    "friction": {
        "FLOW":   "{b_name} holds process under pressure instead of abandoning it.",
        "MIXED":  "{b_name} cuts corners when the week gets hard — agree what's non-negotiable.",
        "STRAIN": "{b_name} abandons the system exactly when it matters most.",
    },
}

_NEW_LINES["employee"]["cfo"] = {
    "soul": {
        "FLOW":   "{b_name} treats stewardship of money as a duty, not a task.",
        "MIXED":  "{b_name}'s instincts on capital differ from yours — align before you raise or spend.",
        "STRAIN": "{b_name}'s relationship with risk is not one you should hand the treasury to.",
    },
    "chemistry": {
        "FLOW":   "You and {b_name} can disagree about numbers without it becoming personal.",
        "MIXED":  "{b_name} keeps a professional distance — workable, occasionally cold.",
        "STRAIN": "The working relationship is strained, and a CFO who can't tell you hard truths is useless.",
    },
    "public": {
        "FLOW":   "{b_name} holds a board or an investor room with credibility.",
        "MIXED":  "{b_name} manages external financial scrutiny with preparation.",
        "STRAIN": "{b_name} will not hold up under board or diligence pressure.",
    },
    "lifepath": {
        "FLOW":   "{b_name}'s season supports the long view a CFO seat requires.",
        "MIXED":  "{b_name} can steward the near term; a multi-year arc is less certain.",
        "STRAIN": "{b_name} is in a volatile phase — wrong timing for custody of the balance sheet.",
    },
    "communication": {
        "FLOW":   "{b_name} brings you bad numbers early and without decoration.",
        "MIXED":  "{b_name} reports accurately but softens the framing — read past it.",
        "STRAIN": "{b_name} manages the message rather than the truth. That is the CFO failure mode.",
    },
    "friction": {
        "FLOW":   "{b_name} will say no to you and mean it — which is the point of the role.",
        "MIXED":  "{b_name} pushes back inconsistently; they may fold when you push hard.",
        "STRAIN": "{b_name} won't hold the line against you. Don't put them in the seat that must.",
    },
}

_NEW_LINES["employee"]["ceo"] = {
    "soul": {
        "FLOW":   "{b_name} wants to build the same thing you do, for the same reasons.",
        "MIXED":  "{b_name}'s sense of the mission overlaps yours but diverges under pressure.",
        "STRAIN": "{b_name} would take the company somewhere you don't want it to go.",
    },
    "chemistry": {
        "FLOW":   "People want to follow {b_name} — the part of leadership you can't install.",
        "MIXED":  "{b_name} earns loyalty slowly; the first year will be quieter than you'd like.",
        "STRAIN": "{b_name} doesn't naturally command a room, which makes everything else harder.",
    },
    "public": {
        "FLOW":   "{b_name} represents the company well to market, press and capital.",
        "MIXED":  "{b_name} is credible externally with preparation and a tight narrative.",
        "STRAIN": "{b_name} as the public face of this company is a liability, not an asset.",
    },
    "lifepath": {
        "FLOW":   "{b_name} is entering a season of authority — the timing supports a top seat.",
        "MIXED":  "{b_name}'s arc supports leading for a while, not necessarily for the whole ride.",
        "STRAIN": "{b_name}'s period pulls away from responsibility. Wrong moment for this seat.",
    },
    "communication": {
        "FLOW":   "{b_name} sets direction people can actually act on.",
        "MIXED":  "{b_name} communicates vision well and detail poorly — pair them accordingly.",
        "STRAIN": "{b_name} leaves people guessing at the strategy. That compounds through the org.",
    },
    "friction": {
        "FLOW":   "{b_name} takes hard news without shooting the messenger.",
        "MIXED":  "{b_name} gets brittle in a bad quarter — the team will feel it.",
        "STRAIN": "{b_name} manages by pressure under stress, and that culture spreads from the top.",
    },
}

_NEW_LINES["employee"]["engineering"] = {
    "soul": {
        "FLOW":   "{b_name} cares whether the thing is actually well built.",
        "MIXED":  "{b_name} ships, though craft and speed pull at them differently than at you.",
        "STRAIN": "{b_name}'s idea of done isn't yours. Expect that argument repeatedly.",
    },
    "chemistry": {
        "FLOW":   "{b_name} collaborates well — reviews won't turn into standoffs.",
        "MIXED":  "{b_name} works better alone than in pairs; scope their work accordingly.",
        "STRAIN": "{b_name} is hard to work alongside, and engineering is a team sport now.",
    },
    "public": {
        "FLOW":   "{b_name} can talk to customers or a conference without you translating.",
        "MIXED":  "{b_name} explains their work adequately outside the team with prep.",
        "STRAIN": "Keep {b_name} away from customer-facing technical conversations.",
    },
    "lifepath": {
        "FLOW":   "{b_name}'s season supports deep focused building.",
        "MIXED":  "{b_name} can deliver, though attention may fragment across the year.",
        "STRAIN": "{b_name} is in a scattered period — bad timing for a hard technical push.",
    },
    "communication": {
        "FLOW":   "{b_name} flags blockers early and writes things down.",
        "MIXED":  "{b_name} goes heads-down and surfaces late — set a check-in rhythm.",
        "STRAIN": "{b_name} disappears into problems silently. You'll find out when it's late.",
    },
    "friction": {
        "FLOW":   "{b_name} takes code review as improvement, not judgement.",
        "MIXED":  "{b_name} defends decisions longer than needed but gets there.",
        "STRAIN": "Review with {b_name} becomes territorial. That poisons a team fast.",
    },
}

_NEW_LINES["employee"]["people"] = {
    "soul": {
        "FLOW":   "{b_name} genuinely believes people are the point, which this seat requires.",
        "MIXED":  "{b_name} cares about people and process unevenly — check which one wins.",
        "STRAIN": "{b_name} sees people work as administration. That's the wrong instinct here.",
    },
    "chemistry": {
        "FLOW":   "People open up to {b_name}. That's the whole job and it can't be trained.",
        "MIXED":  "{b_name} builds trust slowly — fine, but slower than you may need.",
        "STRAIN": "People won't confide in {b_name}, which makes this role structurally hard.",
    },
    "public": {
        "FLOW":   "{b_name} represents your culture credibly to candidates.",
        "MIXED":  "{b_name} recruits adequately; sharpen their pitch before senior hires.",
        "STRAIN": "{b_name} will misrepresent your culture externally, in either direction.",
    },
    "lifepath": {
        "FLOW":   "{b_name} is in a settled season — the steadiness people work needs.",
        "MIXED":  "{b_name} can hold the function though their own attention may wander.",
        "STRAIN": "{b_name} is in a turbulent period. People will sense it and trust less.",
    },
    "communication": {
        "FLOW":   "{b_name} handles a hard conversation without making it worse.",
        "MIXED":  "{b_name} manages routine conversations well and difficult ones unevenly.",
        "STRAIN": "{b_name} avoids the hard conversation, which is most of this job.",
    },
    "friction": {
        "FLOW":   "{b_name} holds confidence and stays neutral when it's costly.",
        "MIXED":  "{b_name} can be pulled into taking sides — watch that in disputes.",
        "STRAIN": "{b_name} carries others' conflict into their own. That compounds badly here.",
    },
}

_NEW_LINES["employee"]["legal"] = {
    "soul": {
        "FLOW":   "{b_name} has a real instinct for principle, not just for rules.",
        "MIXED":  "{b_name} knows the rules; on grey areas your judgements will differ.",
        "STRAIN": "{b_name}'s sense of where the line sits isn't yours. That is dangerous here.",
    },
    "chemistry": {
        "FLOW":   "{b_name} works with you without turning every question into a memo.",
        "MIXED":  "{b_name} is formal with you — appropriate, if occasionally slow.",
        "STRAIN": "The relationship is effortful, and you'll stop asking. That's the real risk.",
    },
    "public": {
        "FLOW":   "{b_name} holds up opposite counsel or a regulator.",
        "MIXED":  "{b_name} represents you competently in routine external matters.",
        "STRAIN": "{b_name} will be outmatched in a serious external negotiation.",
    },
    "lifepath": {
        "FLOW":   "{b_name}'s season supports the patience long matters require.",
        "MIXED":  "{b_name} can carry current matters; a multi-year case is less certain.",
        "STRAIN": "{b_name} is in a period that fights against patience. Litigation would suffer.",
    },
    "communication": {
        "FLOW":   "{b_name} tells you the risk in plain words and then gives you a decision.",
        "MIXED":  "{b_name} is thorough but buries the answer — ask for the recommendation first.",
        "STRAIN": "{b_name} hedges everything. You'll get no usable answer when you need one.",
    },
    "friction": {
        "FLOW":   "{b_name} tells you no early, which is cheaper than late.",
        "MIXED":  "{b_name} raises concerns but can be talked past — decide what's absolute.",
        "STRAIN": "{b_name} won't hold a position against you. In legal, that's the whole value.",
    },
}

# ── Marriage: distinct from dating ─────────────────────────────────────────
_NEW_LINES["marriage"] = {"managerial": {
    "soul": {
        "FLOW":   "You and {b_name} want the same shape of life — the foundation marriage rests on.",
        "MIXED":  "You and {b_name} share most values and diverge on some that matter. Name them before, not after.",
        "STRAIN": "You and {b_name} are building toward different lives. Marriage magnifies that, it doesn't resolve it.",
    },
    "chemistry": {
        "FLOW":   "Physical and emotional rhythm between you and {b_name} is easy and likely to last.",
        "MIXED":  "Attraction between you and {b_name} is real but needs tending — it won't run on its own.",
        "STRAIN": "Physical rhythms differ enough that it will need conscious attention, early.",
    },
    "public": {
        "FLOW":   "You and {b_name} function well as a couple in the world — families and social life included.",
        "MIXED":  "You and {b_name} present well together with a little effort around family expectations.",
        "STRAIN": "The public and family side of this marriage will take real work.",
    },
    "lifepath": {
        "FLOW":   "Your life arcs with {b_name} move in step — the seasons of growth line up.",
        "MIXED":  "Some of your years with {b_name} align and some pull apart. Plan around the gaps.",
        "STRAIN": "Your timelines diverge. Long stretches will feel like living parallel lives.",
    },
    "communication": {
        "FLOW":   "You and {b_name} can say hard things to each other and stay close.",
        "MIXED":  "You and {b_name} communicate well until stress — then old patterns return.",
        "STRAIN": "Under pressure you and {b_name} stop reaching each other. In a marriage that compounds.",
    },
    "friction": {
        "FLOW":   "Little corrosive friction sits between you — disagreements stay recoverable.",
        "MIXED":  "There's friction between you and {b_name} that is workable if it's named rather than stored.",
        "STRAIN": "There is a real friction pattern here. It doesn't make the marriage wrong, but it makes it work.",
    },
}}


# ── Marriage headlines + details ───────────────────────────────────────────
# Registered after the fact so the marriage reason doesn't silently inherit the
# business copy via get_headline()'s fallback.
_HEADLINES["marriage"] = {
    "FLOW":   "A marriage with real foundations — this one is built to hold.",
    "MIXED":  "A workable marriage that asks for honesty early rather than patience later.",
    "STRAIN": "A demanding match — possible, but it will ask a great deal of you both.",
}

_DETAILS["marriage"] = {
    "FLOW":   ("{a_name} and {b_name} have the rarer thing: alignment that survives ordinary life. "
               "Values, timing and temperament support each other rather than compete. Protect it by "
               "not taking it for granted."),
    "MIXED":  ("{a_name} and {b_name} have genuine ground to build on and specific gaps to close. "
               "Marriage doesn't dissolve those gaps — it makes them daily. Named early they become "
               "the structure of the relationship; left unspoken they become the argument you keep having."),
    "STRAIN": ("{a_name} and {b_name} face real structural differences — in values, timing, or "
               "temperament. This isn't a verdict against the marriage; karmically intense pairings "
               "are often the most transformative. But it will need conscious work, not hope."),
}
