"""
antar_engine/natal_signatures.py
Natal Planet Signatures + Character Archetype Engine

For each natal planet: nakshatra → FIELD, sign → MODE → signature
Derives dominant FIELD × MODE → maps to archetype library
Tie-breaking: FIELD tie → Sun's FIELD wins, MODE tie → Moon's MODE wins

Storage: charts.planet_signatures (JSONB), charts.character_archetype (JSONB)
Compute: once at chart creation (new charts) or on first /predict call (existing charts)
"""

from typing import Optional

# ── 27 Nakshatras → FIELD ────────────────────────────────────────────
NAK_TO_FIELD = {
    "Ashwini":           "IGNITION",
    "Bharani":           "THRESHOLD",
    "Krittika":          "EDGE",
    "Rohini":            "GROWTH",
    "Mrigashira":        "DISCOVERY",
    "Ardra":             "STORM",
    "Punarvasu":         "RECOVERY",
    "Pushya":            "ANCHOR",
    "Ashlesha":          "STRATEGY",
    "Magha":             "AUTHORITY",
    "Purva Phalguni":    "ABUNDANCE",
    "Uttara Phalguni":   "COMPLETION",
    "Hasta":             "EXECUTION",
    "Chitra":            "SIGNAL",
    "Swati":             "ADAPTATION",
    "Vishakha":          "VICTORY",
    "Anuradha":          "ALLIANCE",
    "Jyeshtha":          "AUTHORITY",
    "Mula":              "ROOT",
    "Purva Ashadha":     "MOMENTUM",
    "Uttara Ashadha":    "FOUNDATION",
    "Shravana":          "SIGNAL",
    "Dhanishtha":        "MOMENTUM",
    "Shatabhisha":       "DEPTH",
    "Purva Bhadrapada":  "STORM",
    "Uttara Bhadrapada": "DEPTH",
    "Revati":            "COMPLETION",
}

# ── 12 Signs → MODE ──────────────────────────────────────────────────
SIGN_TO_MODE = {
    "Aries":       "DRIVE",
    "Taurus":      "BUILD",
    "Gemini":      "CONNECT",
    "Cancer":      "PROTECT",
    "Leo":         "EXPAND",
    "Virgo":       "REFINE",
    "Libra":       "BALANCE",
    "Scorpio":     "PENETRATE",
    "Sagittarius": "SEEK",
    "Capricorn":   "STRUCTURE",
    "Aquarius":    "DISRUPT",
    "Pisces":      "DISSOLVE",
}

# ── 20 Archetype Library ─────────────────────────────────────────────
ARCHETYPE_LIBRARY = {
    ("AUTHORITY", "STRUCTURE"): {
        "name": "THE ARCHITECT",
        "tagline": "Built to lead systems.",
        "description": "You don't just build things — you build things that outlast you. Your authority is structural, not personal. People follow the system you create.",
        "strength": "Sustainable creation. What you build compounds.",
        "blind_spot": "Slow to launch. You optimize when you should be shipping.",
        "frequency": "4% of charts",
    },
    ("IGNITION", "DRIVE"): {
        "name": "THE CATALYST",
        "tagline": "Pure 0-to-1 energy.",
        "description": "You start things others won't touch. The blank page, the first call, the impossible project — that's your natural habitat.",
        "strength": "Fearless initiation. You move before others see the path.",
        "blind_spot": "Burns out at the 80% mark. Finish what you ignite.",
        "frequency": "3% of charts",
    },
    ("GROWTH", "BUILD"): {
        "name": "THE STEWARD",
        "tagline": "Scales assets over decades.",
        "description": "You compound. Slowly, deliberately, and with devastating patience. You don't win quarters — you win decades.",
        "strength": "Patient abundance. You never lose what you build.",
        "blind_spot": "Underestimates urgency. Sometimes the window is short.",
        "frequency": "6% of charts",
    },
    ("DISCOVERY", "CONNECT"): {
        "name": "THE NETWORKER",
        "tagline": "Bridges people and ideas.",
        "description": "You see connections others miss. You know someone who knows someone — and that network is your real asset.",
        "strength": "Political genius. You navigate human systems effortlessly.",
        "blind_spot": "Paralyzed by complexity when you need to go it alone.",
        "frequency": "5% of charts",
    },
    ("STRATEGY", "REFINE"): {
        "name": "THE ALCHEMIST",
        "tagline": "Optimizes for perfection.",
        "description": "You take raw material — ideas, people, processes — and refine them until they're exceptional. You see what's missing.",
        "strength": "Precision. You get details right that others can't even see.",
        "blind_spot": "Misses the big picture. Perfect can be the enemy of done.",
        "frequency": "5% of charts",
    },
    ("MOMENTUM", "EXPAND"): {
        "name": "THE VISIONARY",
        "tagline": "Never stays in one place.",
        "description": "You think in trajectories, not positions. Where others see a destination, you see a launching pad.",
        "strength": "Turns success into empire. Every win becomes the next beginning.",
        "blind_spot": "Overextends. You expand into territory you can't hold.",
        "frequency": "4% of charts",
    },
    ("STORM", "DISRUPT"): {
        "name": "THE REBEL",
        "tagline": "Thrives in chaos and innovation.",
        "description": "You destroy what's obsolete to clear ground for what's next. You're not difficult — you're ahead of the curve.",
        "strength": "Necessary disruption. You see the old model dying before anyone else.",
        "blind_spot": "Collateral damage. Not everything needs to burn.",
        "frequency": "3% of charts",
    },
    ("AUTHORITY", "PENETRATE"): {
        "name": "THE COMMANDER",
        "tagline": "Cuts through resistance decisively.",
        "description": "You don't persuade — you cut through. This is why you close deals others can't, and why you make enemies faster than allies.",
        "strength": "Gets results fast. When precision matters, you deliver.",
        "blind_spot": "Makes enemies. Not everyone wants the truth as directly as you do.",
        "frequency": "2% of charts",
    },
    ("RECOVERY", "PROTECT"): {
        "name": "THE HEALER",
        "tagline": "Restores what's broken.",
        "description": "You walk into broken situations and make them whole. Businesses, people, relationships — you see the path back.",
        "strength": "Deep repair. You fix what others have given up on.",
        "blind_spot": "Takes on others' pain as your own. Set the boundary.",
        "frequency": "5% of charts",
    },
    ("ANCHOR", "BALANCE"): {
        "name": "THE ANCHOR",
        "tagline": "Holds steady in chaos.",
        "description": "When everything is moving, you're the fixed point. Teams, families, organizations orient around your stability.",
        "strength": "Unshakable. You hold when others fold.",
        "blind_spot": "Resists necessary change. Sometimes the anchor needs to lift.",
        "frequency": "4% of charts",
    },
    ("ABUNDANCE", "CONNECT"): {
        "name": "THE MAGNET",
        "tagline": "Attracts people and resources effortlessly.",
        "description": "You don't chase — you attract. Opportunities, people, money — they find you when you're operating correctly.",
        "strength": "Natural charisma. Your presence is an asset.",
        "blind_spot": "Dependent on external validation. The signal dims when you doubt.",
        "frequency": "4% of charts",
    },
    ("EXECUTION", "REFINE"): {
        "name": "THE HAND",
        "tagline": "Flawless precision in action.",
        "description": "You execute at a level others can only watch. When precision is the difference between winning and losing, you're the person in the room.",
        "strength": "Mastery. You get it right when it matters.",
        "blind_spot": "Misses the strategic frame. Execution without direction is wasted.",
        "frequency": "4% of charts",
    },
    ("DISCOVERY", "SEEK"): {
        "name": "THE COMPASS",
        "tagline": "Finds what others overlook.",
        "description": "You orient in unknown territory. First mover, early adopter, pathfinder — you arrive before the road exists.",
        "strength": "Sees opportunity in the gap before the gap closes.",
        "blind_spot": "Never stays put long enough to compound the win.",
        "frequency": "3% of charts",
    },
    ("ROOT", "DEPTH"): {
        "name": "THE ROOT",
        "tagline": "Goes to the origin of everything.",
        "description": "You don't treat symptoms — you diagnose root causes. In any system, you find what's actually driving the outcome.",
        "strength": "Uncovers foundational truth others never reach.",
        "blind_spot": "Gets lost in the past. The root matters less than the next step.",
        "frequency": "3% of charts",
    },
    ("SIGNAL", "DISRUPT"): {
        "name": "THE SIGNAL",
        "tagline": "Broadcasts what needs to be heard.",
        "description": "You cut through noise and say the thing no one else will say — clearly, loudly, at exactly the right moment.",
        "strength": "Heard when it counts. Your timing is your weapon.",
        "blind_spot": "Heard but not always understood. Translate the signal.",
        "frequency": "3% of charts",
    },
    ("ABUNDANCE", "FLOW"): {
        "name": "THE ABUNDANCE",
        "tagline": "Attracts wealth naturally.",
        "description": "Scarcity doesn't live in your chart. When you're aligned, resources flow toward you without force.",
        "strength": "Never truly lacks. Abundance is your baseline.",
        "blind_spot": "Wastes surplus. What flows in flows out without structure.",
        "frequency": "4% of charts",
    },
    ("EDGE", "PENETRATE"): {
        "name": "THE EDGE",
        "tagline": "Lives on the boundary of what's possible.",
        "description": "You push limits for a living. The frontier is your home — the edge between what exists and what could.",
        "strength": "First to the limit. You define where the wall is.",
        "blind_spot": "Falls off the edge. The frontier has a drop on both sides.",
        "frequency": "2% of charts",
    },
    ("DEPTH", "DISSOLVE"): {
        "name": "THE DEPTH",
        "tagline": "Sees through illusion to essence.",
        "description": "You see what's real when everyone else sees the story. Illusion dissolves in your presence.",
        "strength": "Unmatched insight. You get to truth faster than any process.",
        "blind_spot": "Useless in daily practical life without a translator.",
        "frequency": "2% of charts",
    },
    ("COMPLETION", "BALANCE"): {
        "name": "THE COMPLETION",
        "tagline": "Finishes what others abandon.",
        "description": "You close loops. The orphaned project, the unresolved conflict, the half-built system — you finish it.",
        "strength": "Graceful endings. You know when something is done.",
        "blind_spot": "Starts nothing new. You wait for others to begin.",
        "frequency": "3% of charts",
    },
    ("THRESHOLD", "DISRUPT"): {
        "name": "THE THRESHOLD",
        "tagline": "Crosses boundaries others fear.",
        "description": "You go first. Every boundary that expands — in markets, relationships, territories — was crossed by someone like you.",
        "strength": "First mover advantage. You shape the rules others play by.",
        "blind_spot": "Alone at the frontier. Bring someone with you.",
        "frequency": "2% of charts",
    },

    # ── Extended combinations ────────────────────────────────────────
    ("ALLIANCE", "PENETRATE"): {
        "name": "THE BROKER",
        "tagline": "Cuts to the truth in every relationship.",
        "description": "You build alliances others can't — because you say what no one else will say. You see through the social performance to what people actually want, and you negotiate from that truth.",
        "strength": "Trusted precisely because you're direct. You close what others can't.",
        "blind_spot": "Your directness can feel like a weapon. People need to feel safe before they can be honest with you.",
        "frequency": "3% of charts",
    },
    ("ALLIANCE", "BALANCE"): {
        "name": "THE DIPLOMAT",
        "tagline": "Holds relationships in perfect tension.",
        "description": "You keep opposing forces in productive relationship. Where others see conflict, you see negotiation. Your presence prevents wars.",
        "strength": "Political genius. You make deals that hold.",
        "blind_spot": "Avoids necessary confrontation. Some things need to break before they can be rebuilt.",
        "frequency": "3% of charts",
    },
    ("ALLIANCE", "BUILD"): {
        "name": "THE GUILD MASTER",
        "tagline": "Builds networks that become institutions.",
        "description": "You don't just connect people — you construct ecosystems. The organizations, communities, and alliances you build outlast you.",
        "strength": "Network compounds. What you build becomes infrastructure.",
        "blind_spot": "Slow to cut ties that are no longer serving the network.",
        "frequency": "3% of charts",
    },
    ("ALLIANCE", "STRUCTURE"): {
        "name": "THE INSTITUTION",
        "tagline": "Turns relationships into lasting systems.",
        "description": "You formalize what others leave informal. Partnerships, teams, communities — you give them structure that makes them durable.",
        "strength": "What you build doesn't fall apart when you leave.",
        "blind_spot": "Over-structures human dynamics. Not every relationship needs a contract.",
        "frequency": "2% of charts",
    },
    ("AUTHORITY", "DRIVE"): {
        "name": "THE ENFORCER",
        "tagline": "Authority in motion — unstoppable.",
        "description": "You lead from the front. Your authority isn't positional — it's kinetic. You move and others follow because they can't keep up otherwise.",
        "strength": "Gets things done. No committee, no consensus — results.",
        "blind_spot": "Runs over people who needed more time. Slow down at the human moments.",
        "frequency": "3% of charts",
    },
    ("AUTHORITY", "BUILD"): {
        "name": "THE FOUNDER",
        "tagline": "Builds empires through sheer will.",
        "description": "You combine authority with the patience to build something real. You don't just command — you construct. The organization becomes an extension of your vision.",
        "strength": "Creates durable authority. What you build carries your standard.",
        "blind_spot": "Builds dependency. People can't function without your direction.",
        "frequency": "3% of charts",
    },
    ("AUTHORITY", "EXPAND"): {
        "name": "THE EMPEROR",
        "tagline": "Expands authority into new territory.",
        "description": "You lead by conquest — not of people, but of markets, ideas, and categories. Every win becomes the base for the next campaign.",
        "strength": "Territorial expansion. You claim ground others didn't know existed.",
        "blind_spot": "Overextends. Hold what you've taken before you take more.",
        "frequency": "2% of charts",
    },
    ("GROWTH", "EXPAND"): {
        "name": "THE MULTIPLIER",
        "tagline": "Grows everything it touches.",
        "description": "You don't just grow things — you multiply them. Resources, teams, ideas — in your hands they compound faster than anyone expects.",
        "strength": "Abundance multiplier. Your presence accelerates everything.",
        "blind_spot": "Grows too many things at once. Focus is the force multiplier.",
        "frequency": "4% of charts",
    },
    ("GROWTH", "CONNECT"): {
        "name": "THE ECOSYSTEM",
        "tagline": "Grows through connection, not competition.",
        "description": "You understand that growth is relational. Your best results come when you're building something others can plug into.",
        "strength": "Creates abundance for everyone in the network.",
        "blind_spot": "Gives too much. Your generosity can be exploited.",
        "frequency": "3% of charts",
    },
    ("MOMENTUM", "STRUCTURE"): {
        "name": "THE ENGINE",
        "tagline": "Builds unstoppable systems.",
        "description": "You combine momentum with structure — you don't just move fast, you build machines that move fast permanently. Processes, systems, organizations that run themselves.",
        "strength": "Sustainable velocity. You build speed that compounds.",
        "blind_spot": "Optimizes the wrong thing. Make sure the machine is pointed right.",
        "frequency": "3% of charts",
    },
    ("STRATEGY", "PENETRATE"): {
        "name": "THE SURGEON",
        "tagline": "Precise cuts that change everything.",
        "description": "You diagnose and operate. Where others apply pressure broadly, you find the exact point that, when moved, moves everything else.",
        "strength": "Surgical precision. One right move beats ten good moves.",
        "blind_spot": "Can feel cold. People need to know you see them, not just the problem.",
        "frequency": "3% of charts",
    },
    ("STRATEGY", "EXPAND"): {
        "name": "THE GRANDMASTER",
        "tagline": "Thinks ten moves ahead.",
        "description": "You play a different game than everyone in the room. While others react, you're executing a plan they haven't seen yet.",
        "strength": "Strategic advantage. You win before the game starts.",
        "blind_spot": "Underestimates randomness. Not everything can be planned.",
        "frequency": "2% of charts",
    },
    ("IGNITION", "CONNECT"): {
        "name": "THE SPARK",
        "tagline": "Ignites others into action.",
        "description": "You don't just start things — you start people. Your energy is contagious. Rooms change when you walk in.",
        "strength": "Activation energy. You turn potential into kinetic.",
        "blind_spot": "Sparks fade. Build the fire before you move to the next one.",
        "frequency": "3% of charts",
    },
    ("IGNITION", "STRUCTURE"): {
        "name": "THE LAUNCHER",
        "tagline": "Starts things that actually survive.",
        "description": "You have the rare combination of ignition and structure — you don't just start, you start right. Your launches have foundations.",
        "strength": "Durable beginnings. What you start doesn't collapse.",
        "blind_spot": "Over-prepares the launch. Sometimes done is better than right.",
        "frequency": "2% of charts",
    },
    ("RECOVERY", "BUILD"): {
        "name": "THE REBUILDER",
        "tagline": "Reconstructs what's been destroyed.",
        "description": "You walk into ruins and build something better than what was there before. Post-crisis, post-failure, post-loss — that's your activation condition.",
        "strength": "Turns wreckage into foundation. You see structure in the debris.",
        "blind_spot": "Needs the breakdown to activate. You can build proactively too.",
        "frequency": "3% of charts",
    },
    ("SIGNAL", "EXPAND"): {
        "name": "THE BROADCASTER",
        "tagline": "Amplifies signal to reach everyone.",
        "description": "You don't just communicate — you transmit at scale. Your message reaches people who weren't looking for it.",
        "strength": "Reach. Your signal carries further than anyone expects.",
        "blind_spot": "Scale without depth. Make sure the signal is worth broadcasting.",
        "frequency": "3% of charts",
    },
    ("FOUNDATION", "BUILD"): {
        "name": "THE ARCHITECT",
        "tagline": "Builds on bedrock.",
        "description": "You don't build on sand. Everything you create has structural integrity — it can hold weight, survive stress, and be built upon.",
        "strength": "What you build lasts. Others build on top of your work.",
        "blind_spot": "Takes too long to start. The foundation doesn't need to be perfect before you build.",
        "frequency": "4% of charts",
    },
    ("FOUNDATION", "STRUCTURE"): {
        "name": "THE BEDROCK",
        "tagline": "The ground others stand on.",
        "description": "You are the stable base. Organizations, families, teams — they orient around your steadiness without always knowing it.",
        "strength": "Unshakable foundation. Everything built on you holds.",
        "blind_spot": "Invisible. Your contribution is structural — make sure it's acknowledged.",
        "frequency": "3% of charts",
    },
    ("DEPTH", "PENETRATE"): {
        "name": "THE INVESTIGATOR",
        "tagline": "Gets to the bottom of everything.",
        "description": "Surface explanations don't satisfy you. You go deeper than anyone asked you to — and you find what's actually there.",
        "strength": "Truth finding. You surface what would otherwise stay hidden.",
        "blind_spot": "Gets lost underground. Come back up with what you found.",
        "frequency": "2% of charts",
    },
    ("ADAPTATION", "CONNECT"): {
        "name": "THE CHAMELEON",
        "tagline": "Moves between worlds effortlessly.",
        "description": "You adapt your signal to any frequency. Boardroom, street, studio — you're fluent in every context.",
        "strength": "Access. You get into rooms others can't because you speak every language.",
        "blind_spot": "No fixed identity can make you invisible. Plant a flag.",
        "frequency": "3% of charts",
    },
    ("ADAPTATION", "DISRUPT"): {
        "name": "THE SHAPESHIFTER",
        "tagline": "Disrupts by becoming what's needed.",
        "description": "You don't fight the system — you become something the system can't categorize. You disrupt by being unclassifiable.",
        "strength": "Uncatchable. You move faster than any category.",
        "blind_spot": "Hard to trust. People need to know who you actually are.",
        "frequency": "2% of charts",
    },
    ("VICTORY", "DRIVE"): {
        "name": "THE CHAMPION",
        "tagline": "Wins and keeps winning.",
        "description": "You compete at a level others find exhausting. Winning isn't an outcome for you — it's a standard.",
        "strength": "Relentless. You don't stop when it gets hard.",
        "blind_spot": "Wins at the wrong things. Make sure the game is worth playing.",
        "frequency": "3% of charts",
    },
    ("VICTORY", "STRUCTURE"): {
        "name": "THE GENERAL",
        "tagline": "Wins through superior organization.",
        "description": "You outmaneuver, not outmuscle. Your wins come from preparation, positioning, and structure — not brute force.",
        "strength": "Strategic wins that hold. You don't win by accident.",
        "blind_spot": "Over-plans. Sometimes the best move is the unexpected one.",
        "frequency": "2% of charts",
    },
    ("ROOT", "STRUCTURE"): {
        "name": "THE ARCHAEOLOGIST",
        "tagline": "Excavates the truth beneath everything.",
        "description": "You go back to the source. History, patterns, origins — you understand that everything happening now has a root cause somewhere in the past.",
        "strength": "Foundational clarity. You solve problems at the source, not the symptom.",
        "blind_spot": "The past is data, not destiny. What are you building forward?",
        "frequency": "2% of charts",
    },
}

# Default archetype for unmapped combinations
DEFAULT_ARCHETYPE = {
    "name": "THE NAVIGATOR",
    "tagline": "Finds the path through complexity.",
    "description": "Your chart carries a rare combination of signals. You operate at the intersection of multiple fields — adaptable, hard to categorize, harder to stop.",
    "strength": "Versatility. You move between worlds others can't enter.",
    "blind_spot": "No fixed identity can make you invisible. Plant a flag.",
    "frequency": "rare",
}


def compute_natal_signatures(chart_data: dict) -> dict:
    """
    Compute FIELD×MODE signature for each natal planet.
    Uses chart_data['planets'] which has nakshatra and sign for each planet.

    Returns:
        {
            "sun":     {"field": "AUTHORITY", "mode": "PENETRATE", "nakshatra": "Jyeshtha", "sign": "Scorpio"},
            "moon":    {...},
            ...
        }
    """
    planets_raw = chart_data.get("planets", {})
    signatures = {}

    PLANET_KEYS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

    for planet in PLANET_KEYS:
        pdata = planets_raw.get(planet, {})
        if not isinstance(pdata, dict):
            continue

        nakshatra = pdata.get("nakshatra", "") or ""
        sign      = pdata.get("sign", "") or ""

        field = NAK_TO_FIELD.get(nakshatra, "SIGNAL")
        mode  = SIGN_TO_MODE.get(sign, "BALANCE")

        signatures[planet.lower()] = {
            "field":     field,
            "mode":      mode,
            "nakshatra": nakshatra,
            "sign":      sign,
        }

    return signatures


def derive_archetype(signatures: dict) -> dict:
    """
    From planet signatures, derive dominant FIELD and MODE.
    Tie-breaking: FIELD tie → Sun's FIELD, MODE tie → Moon's MODE.

    Returns full archetype dict.
    """
    from collections import Counter

    field_counts = Counter()
    mode_counts  = Counter()

    for planet, sig in signatures.items():
        if sig.get("field"):
            field_counts[sig["field"]] += 1
        if sig.get("mode"):
            mode_counts[sig["mode"]] += 1

    # Dominant FIELD — tie goes to Sun
    sun_field  = signatures.get("sun", {}).get("field", "AUTHORITY")
    max_field_count = max(field_counts.values()) if field_counts else 0
    top_fields = [f for f, c in field_counts.items() if c == max_field_count]
    dominant_field = sun_field if sun_field in top_fields else top_fields[0]

    # Dominant MODE — tie goes to Moon
    moon_mode  = signatures.get("moon", {}).get("mode", "BUILD")
    max_mode_count = max(mode_counts.values()) if mode_counts else 0
    top_modes  = [m for m, c in mode_counts.items() if c == max_mode_count]
    dominant_mode = moon_mode if moon_mode in top_modes else top_modes[0]

    # Lookup archetype
    archetype = ARCHETYPE_LIBRARY.get(
        (dominant_field, dominant_mode),
        DEFAULT_ARCHETYPE
    )

    return {
        "name":            archetype["name"],
        "tagline":         archetype["tagline"],
        "description":     archetype["description"],
        "strength":        archetype["strength"],
        "blind_spot":      archetype["blind_spot"],
        "frequency":       archetype["frequency"],
        "dominant_field":  dominant_field,
        "dominant_mode":   dominant_mode,
        "field_counts":    dict(field_counts),
        "mode_counts":     dict(mode_counts),
    }


def ensure_signatures(chart_id: str, chart_data: dict, supabase) -> tuple:
    """
    Check if chart has signatures. If not, compute and store.
    Returns (planet_signatures, character_archetype).

    Call at start of /predict and /daily-signal.
    """
    try:
        row = supabase.table("charts") \
            .select("planet_signatures,character_archetype") \
            .eq("id", chart_id) \
            .single() \
            .execute()

        existing_sigs     = row.data.get("planet_signatures")
        existing_archtype = row.data.get("character_archetype")

        if existing_sigs and existing_archtype:
            return existing_sigs, existing_archtype

        # Compute
        print(f"[signatures] Computing natal signatures for chart {chart_id}")
        sigs      = compute_natal_signatures(chart_data)
        archetype = derive_archetype(sigs)

        # Store
        supabase.table("charts").update({
            "planet_signatures":  sigs,
            "character_archetype": archetype,
        }).eq("id", chart_id).execute()

        print(f"[signatures] Stored — archetype: {archetype['name']} ({archetype['dominant_field']}×{archetype['dominant_mode']})")
        return sigs, archetype

    except Exception as e:
        print(f"[signatures] Error (non-fatal): {e}")
        # Compute in-memory without storing
        sigs      = compute_natal_signatures(chart_data)
        archetype = derive_archetype(sigs)
        return sigs, archetype


def build_signature_context_block(planet_signatures: dict, character_archetype: dict) -> str:
    """
    Build plain-English context block for injection into /predict prompt.
    No Sanskrit, no planet names in output — instrument language only.
    """
    if not character_archetype:
        return ""

    name        = character_archetype.get("name", "")
    tagline     = character_archetype.get("tagline", "")
    description = character_archetype.get("description", "")
    strength    = character_archetype.get("strength", "")
    blind_spot  = character_archetype.get("blind_spot", "")
    dom_field   = character_archetype.get("dominant_field", "")
    dom_mode    = character_archetype.get("dominant_mode", "")
    frequency   = character_archetype.get("frequency", "")

    lines = [
        "=== USER'S CORE SIGNATURE ===",
        f"Archetype: {name} — {tagline}",
        f"Dominant Pattern: {dom_field} FIELD × {dom_mode} MODE",
        f"Rarity: {frequency}",
        "",
        f"Who they are: {description}",
        f"Their edge: {strength}",
        f"Their blind spot: {blind_spot}",
        "",
        "Planet signatures:",
    ]

    PLANET_LABELS = {
        "sun":     "Identity Signal",
        "moon":    "Emotional Radar",
        "mars":    "Action Drive",
        "mercury": "Processing Speed",
        "jupiter": "Growth Amplifier",
        "venus":   "Magnetism Field",
        "saturn":  "Structural Load",
        "rahu":    "Ambition Engine",
        "ketu":    "Intuition Compass",
    }

    for planet, label in PLANET_LABELS.items():
        sig = planet_signatures.get(planet, {})
        if sig:
            lines.append(f"  {label}: {sig.get('field','?')} × {sig.get('mode','?')}")

    lines.append("")
    lines.append("INSTRUCTION: Reference the user's archetype and dominant pattern when answering.")
    lines.append(f"Frame advice through their {dom_field}×{dom_mode} wiring — not generic.")
    lines.append("=== END CORE SIGNATURE ===")

    return "\n".join(lines)
