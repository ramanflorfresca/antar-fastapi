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
    ("ADAPTATION", "PENETRATE"): {
        "name": "THE SHAPESHIFTER",
        "tagline": "You don't just survive change — you become it before others see it coming.",
        "description": "You read shifting environments faster than anyone in the room. Where others freeze, you recalibrate. Your power is in your fluidity — you adopt what works, discard what doesn't, and move forward without sentimentality.",
        "strength": "Thrives in volatile, high-change environments where rigid players fail.",
        "blind_spot": "Can lose a consistent identity when adapting too often.",
        "frequency": "TOP 8% OF PROFILES",
    },
    ("STRATEGY", "EXPAND"): {
        "name": "THE ARCHITECT",
        "tagline": "You build systems that outlast you — because you designed them to.",
        "description": "You think in structures, frameworks, and long games. Where others react to the moment, you are already three moves ahead — designing the environment that makes winning inevitable.",
        "strength": "Turns complex problems into scalable, repeatable systems.",
        "blind_spot": "Can over-engineer solutions that need simplicity.",
        "frequency": "TOP 7% OF PROFILES",
    },
    ("SIGNAL", "SEEK"): {
        "name": "THE SCOUT",
        "tagline": "You find the signal in the noise before anyone else tunes in.",
        "description": "You are wired to detect what is emerging — trends, opportunities, people — before they become obvious. Your restlessness is not distraction; it is an antenna. You move toward what matters next.",
        "strength": "Early mover advantage — consistently identifies opportunities ahead of the market.",
        "blind_spot": "Can chase novelty and abandon things before they fully pay off.",
        "frequency": "TOP 9% OF PROFILES",
    },
    ("AUTHORITY", "DISSOLVE"): {
        "name": "THE CLOSER",
        "tagline": "You end uncertainty. When you walk in, decisions get made.",
        "description": "You carry a quiet force that cuts through ambiguity and gets things resolved. You don't need volume — you need precision. In rooms full of people avoiding the hard call, you make it.",
        "strength": "Can finalize deals, decisions, and situations others have been circling for months.",
        "blind_spot": "Can be perceived as dismissive when others need more processing time.",
        "frequency": "TOP 6% OF PROFILES",
    },
    ("COMPLETION", "DISSOLVE"): {
        "name": "THE FINISHER",
        "tagline": "You are the last 10% that most people never reach.",
        "description": "You have the rare ability to close what was started — to push through the final resistance, clean up the loose ends, and deliver what was promised. In a world full of starters, you are the one who actually ships.",
        "strength": "Brings projects, relationships, and cycles to clean resolution.",
        "blind_spot": "Can hold on past the point where letting go is the right move.",
        "frequency": "TOP 8% OF PROFILES",
    },
    ("STORM", "BALANCE"): {
        "name": "THE STABILIZER",
        "tagline": "You are the calm that makes the storm navigable.",
        "description": "You carry an unusual combination: the energy to drive through intense situations and the steadiness to keep everyone functional while doing it. People lean on you in crisis because you don't collapse under pressure.",
        "strength": "Maintains equilibrium and output in high-pressure, chaotic environments.",
        "blind_spot": "Can absorb others' chaos until it becomes your own.",
        "frequency": "TOP 7% OF PROFILES",
    },
    ("THRESHOLD", "REFINE"): {
        "name": "THE EDITOR",
        "tagline": "You see what something could be — and you cut away everything that isn't that.",
        "description": "You operate at the boundary between good and great. Your instinct is to improve, sharpen, and elevate. You are not a creator of first drafts — you are the intelligence that makes them worth keeping.",
        "strength": "Raises the quality ceiling of everything you touch.",
        "blind_spot": "Can be paralysed by perfectionism at moments that require momentum.",
        "frequency": "TOP 9% OF PROFILES",
    },
    ("DISCOVERY", "STRUCTURE"): {
        "name": "THE CARTOGRAPHER",
        "tagline": "You map unknown territory so others can follow.",
        "description": "You have a rare combination: the curiosity to explore and the discipline to document. You don't just find new things — you build the frameworks that make them usable. Your work creates roads where there were none.",
        "strength": "Translates frontier insight into structured, actionable knowledge.",
        "blind_spot": "Can spend more time mapping than moving forward.",
        "frequency": "TOP 8% OF PROFILES",
    },
    ("ANCHOR", "EXPAND"): {
        "name": "THE PATRON",
        "tagline": "You grow things — and you make sure the roots hold.",
        "description": "You combine the drive to scale with the instinct to protect what matters. You are not just a builder — you are a steward. You expand without losing the foundation that makes expansion sustainable.",
        "strength": "Creates growth that is both ambitious and durable.",
        "blind_spot": "Can slow expansion by over-protecting what has already been built.",
        "frequency": "TOP 10% OF PROFILES",
    },
    ("THRESHOLD", "DISSOLVE"): {
        "name": "THE GATEKEEPER",
        "tagline": "You decide what crosses the threshold — and what doesn't.",
        "description": "You sit at the boundary between what was and what comes next. Your power is discernment — knowing when to let something through and when to hold the line. You end one chapter so the next can begin cleanly.",
        "strength": "Exceptional at transitions, decisions, and knowing when cycles are complete.",
        "blind_spot": "Can block progress by holding boundaries past their usefulness.",
        "frequency": "TOP 9% OF PROFILES",
    },
    ("EDGE", "EXPAND"): {
        "name": "THE PIONEER",
        "tagline": "You go first — so others know it is possible.",
        "description": "You operate at the frontier. You are not comfortable in the middle of the pack, and you were never meant to be. Your role is to push into territory that hasn't been claimed, and to grow fast once you get there.",
        "strength": "First-mover instinct combined with the drive to scale what is found.",
        "blind_spot": "Can outpace the support structures needed to sustain what was built.",
        "frequency": "TOP 5% OF PROFILES",
    },
    ("DISCOVERY", "DRIVE"): {
        "name": "THE EXPLORER",
        "tagline": "You are not looking for comfort — you are looking for what is true.",
        "description": "You move through the world with relentless curiosity and the energy to act on what you find. You don't wait for permission to investigate, experiment, or push into new domains. Discovery is not a hobby — it is how you operate.",
        "strength": "Combines intellectual curiosity with the drive to test ideas in the real world.",
        "blind_spot": "Can burn through energy on exploration before consolidating gains.",
        "frequency": "TOP 8% OF PROFILES",
    },
    ("DISCOVERY", "EXPAND"): {
        "name": "THE MULTIPLIER",
        "tagline": "You find what works — then you scale it everywhere.",
        "description": "You have the rare ability to spot a good idea and immediately see how to grow it beyond its original context. You are not just curious — you are a force multiplier. What you touch tends to get bigger.",
        "strength": "Takes nascent insights and builds them into scalable advantage.",
        "blind_spot": "Can scale things before they are ready, creating fragile growth.",
        "frequency": "TOP 7% OF PROFILES",
    },
    ("ABUNDANCE", "PENETRATE"): {
        "name": "THE DEALMAKER",
        "tagline": "You see the value in everything — and you know how to unlock it.",
        "description": "You have an instinct for where value lives and a precision for extracting it. You don't just see opportunity — you see the specific angle that makes a deal work. Your conversations tend to end with agreements.",
        "strength": "Identifies and activates latent value that others overlook.",
        "blind_spot": "Can push too hard on deals that need more time to mature.",
        "frequency": "TOP 6% OF PROFILES",
    },
    ("ROOT", "CONNECT"): {
        "name": "THE ANCHOR",
        "tagline": "You are the person people come back to — because you were always there.",
        "description": "You provide stability through genuine connection. You don't chase relationships — you build them slowly, deeply, and permanently. In a world of transient networks, you are someone people trust with what actually matters.",
        "strength": "Creates deep, lasting loyalty that compounds over time.",
        "blind_spot": "Can prioritise stability over necessary disruption or change.",
        "frequency": "TOP 10% OF PROFILES",
    },
    ("STORM", "STRUCTURE"): {
        "name": "THE OPERATOR",
        "tagline": "You channel intensity into execution — nothing escapes your system.",
        "description": "You have the drive of a storm and the discipline of a machine. Where others burn out or scatter, you build the structure that makes high energy sustainable. You are the person who actually gets it done — at scale, under pressure.",
        "strength": "Converts intense drive into consistent, structured output.",
        "blind_spot": "Can over-systematise environments that need flexibility.",
        "frequency": "TOP 7% OF PROFILES",
    },
    ("ADAPTATION", "BALANCE"): {
        "name": "THE MEDIATOR",
        "tagline": "You hold the center while everything shifts around you.",
        "description": "You have a rare ability to stay grounded while environments change rapidly. You don't resist flux — you absorb it, process it, and keep everyone functional through it. Stability isn't something you find. It's something you create.",
        "strength": "Keeps complex, changing situations from falling apart.",
        "blind_spot": "Can over-accommodate to avoid conflict, losing your own position.",
        "frequency": "TOP 7% OF PROFILES",
    },
    ("STRATEGY", "PROTECT"): {
        "name": "THE GUARDIAN",
        "tagline": "You build walls before others know they need them.",
        "description": "You think strategically and defensively — always three moves ahead, anticipating threats before they materialise. You don't just plan for success. You plan for what could go wrong. The people in your orbit tend to be safer than they realise.",
        "strength": "Prevents failures that others never see coming.",
        "blind_spot": "Can over-protect and slow down necessary risk-taking.",
        "frequency": "TOP 8% OF PROFILES",
    },
    ("THRESHOLD", "DRIVE"): {
        "name": "THE CATALYST",
        "tagline": "You push people past the edge they thought was their limit.",
        "description": "You operate at the boundary of what is possible and you move fast. You have no patience for comfortable stagnation — not in yourself, not in others. Your presence accelerates things. People do more around you than they thought they could.",
        "strength": "Activates untapped potential in people and situations.",
        "blind_spot": "Can push too hard, burning out the people or systems around you.",
        "frequency": "TOP 6% OF PROFILES",
    },
    ("VICTORY", "PENETRATE"): {
        "name": "THE CHAMPION",
        "tagline": "You win — and you make sure everyone knows what winning looks like.",
        "description": "You combine competitive drive with precision. You don't just want to succeed — you want to understand exactly how and why you succeeded, so you can do it again. You set the standard others are measured against.",
        "strength": "Consistent high performance with the insight to replicate it.",
        "blind_spot": "Can define winning too narrowly, missing opportunities outside your frame.",
        "frequency": "TOP 5% OF PROFILES",
    },
    ("COMPLETION", "REFINE"): {
        "name": "THE CRAFTSMAN",
        "tagline": "You don't stop until it's right — and you always know the difference.",
        "description": "You have both the drive to finish and the eye to perfect. You don't just close the loop — you close it cleanly. Your work has a quality to it that comes from never accepting good enough when excellent is possible.",
        "strength": "Delivers completed work at a consistently high standard.",
        "blind_spot": "Can over-refine and delay delivery past the point of diminishing returns.",
        "frequency": "TOP 9% OF PROFILES",
    },
    ("STORM", "BUILD"): {
        "name": "THE FORGER",
        "tagline": "You create under pressure — intensity is your forge.",
        "description": "You do your best work when the stakes are high and the timeline is short. Where others need calm to create, you need friction. You build fast, build strong, and build in conditions that would stop most people entirely.",
        "strength": "Exceptional output under pressure and in resource-constrained environments.",
        "blind_spot": "Can manufacture urgency when patience would serve better.",
        "frequency": "TOP 7% OF PROFILES",
    },
    ("MOMENTUM", "SEEK"): {
        "name": "THE ACCELERATOR",
        "tagline": "You find velocity — and you refuse to let it die.",
        "description": "You have an instinct for what is gaining traction and the drive to pour fuel on it. You don't create from scratch — you amplify what is already moving. In your hands, small wins become big ones fast.",
        "strength": "Turns early signals into rapid, compounding progress.",
        "blind_spot": "Can sacrifice depth and durability for speed.",
        "frequency": "TOP 8% OF PROFILES",
    },
    ("ABUNDANCE", "EXPAND"): {
        "name": "THE AMPLIFIER",
        "tagline": "You don't just attract resources — you multiply them.",
        "description": "You have a natural magnetism for opportunity and the instinct to grow it beyond its original size. Wealth, relationships, and influence tend to accumulate around you — not by accident, but because you know how to make things bigger.",
        "strength": "Consistently grows resources, networks, and opportunities beyond their starting point.",
        "blind_spot": "Can overextend by trying to expand everything at once.",
        "frequency": "TOP 6% OF PROFILES",
    },
    # --- Added to close coverage gaps (billionaire chart analysis, v2) ---
    ("SIGNAL", "DRIVE"): {
        "name": "THE HERALD",
        "tagline": "Announces what is coming before others see it.",
        "description": "You sense pattern shifts early and act on them publicly. Empire-voice energy — the one who names the new reality while others are still defending the old one. Authority through being early and loud about what matters.",
        "strength": "Prophetic timing. You're three moves ahead on what becomes obvious.",
        "blind_spot": "Speed outruns proof. Stake fewer claims, stake them harder.",
        "frequency": "3% of charts",
    },
    ("SIGNAL", "STRUCTURE"): {
        "name": "THE PUBLIC ARCHITECT",
        "tagline": "Builds institutions that broadcast themselves.",
        "description": "You construct systems — brands, companies, movements — where the structure itself is the public signal. What you build doesn't need marketing because the shape of it speaks. Famous-by-design, not famous-for-fame.",
        "strength": "Institutional voice. Your creations become landmarks.",
        "blind_spot": "The spotlight you built can become the spotlight you can't escape. Plan for public scrutiny before it arrives.",
        "frequency": "2% of charts",
    },
    ("ROOT", "SEEK"): {
        "name": "THE FOUNDER-SEEKER",
        "tagline": "Goes deep to find what was always there.",
        "description": "You excavate rather than invent. Your genius is recognizing foundational truths — about an industry, a market, a human need — that others walk past. Builds empires on primal, almost ancestral instincts about what people actually want.",
        "strength": "Primal instinct for what endures. You build on bedrock.",
        "blind_spot": "Can mistake deep-held beliefs for universal truths. Test the foundation before you build the tower.",
        "frequency": "2% of charts",
    },
    ("VICTORY", "BALANCE"): {
        "name": "THE DIPLOMAT-WINNER",
        "tagline": "Wins without leaving enemies.",
        "description": "You compete, and you win, but your victories don't cost you allies. Inherited-legacy energy — the one who keeps the family empire thriving while modernizing it. Wins through harmony-maintenance, not through disruption.",
        "strength": "Victories that compound because no bridges burn.",
        "blind_spot": "Conflict-avoidance can delay necessary disruption. Some wars must be fought.",
        "frequency": "2% of charts",
    },
    ("DEPTH", "STRUCTURE"): {
        "name": "THE FORTRESS",
        "tagline": "Holds ground others can't breach.",
        "description": "You build defenses — financial, legal, psychological, operational — that outlast assaults. Private-empire energy. The one whose wealth is invisible because it's behind structure, not in display.",
        "strength": "Asymmetric protection. You lose less than you win.",
        "blind_spot": "Fortification becomes isolation. The moat can be a cage.",
        "frequency": "3% of charts",
    },
    ("DEPTH", "BUILD"): {
        "name": "THE UNDERGROUND-BUILDER",
        "tagline": "Constructs empires below the surface.",
        "description": "Your scale hides. You build holding companies, private networks, off-market positions. By the time the public sees what you built, you've already moved to the next layer.",
        "strength": "Stealth accumulation. You arrive fully-formed.",
        "blind_spot": "Invisibility has limits. Eventually the scale must be declared.",
        "frequency": "3% of charts",
    },
    ("RECOVERY", "STRUCTURE"): {
        "name": "THE TURNAROUND ARCHITECT",
        "tagline": "Rebuilds what others wrote off.",
        "description": "You specialize in broken systems. The failed company, the stalled team, the dead project — these wake up in your hands. Restructuring, refinancing, relaunching: your natural habitat.",
        "strength": "Phoenix engineering. Wreckage is your raw material.",
        "blind_spot": "Attracted to chaos that isn't actually salvageable. Know when to walk away.",
        "frequency": "4% of charts",
    },
    ("AUTHORITY", "CONNECT"): {
        "name": "THE POWER-BROKER",
        "tagline": "Connects decision-makers across silos.",
        "description": "Your authority is lateral, not vertical — you don't rule one domain, you move between them. Boards, advisory roles, ecosystem connectors. The person who knows who needs whom and why.",
        "strength": "Positional power. You compound relationships across decades.",
        "blind_spot": "Can live too much in brokering, too little in making. Build something that's only yours.",
        "frequency": "3% of charts",
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
        "sun":     "Sun (identity, authority, vitality)",
        "moon":    "Moon (emotion, mind, nurturing)",
        "mars":    "Mars (action, drive, energy)",
        "mercury": "Mercury (communication, intellect)",
        "jupiter": "Jupiter (growth, wisdom, expansion)",
        "venus":   "Venus (love, partnership, money)",
        "saturn":  "Saturn (discipline, structure, time)",
        "rahu":    "Rahu (ambition, breakthrough, foreign)",
        "ketu":    "Ketu (intuition, release, spirituality)",
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
