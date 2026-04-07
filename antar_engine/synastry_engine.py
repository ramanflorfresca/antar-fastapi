"""
antar_engine/synastry_engine.py
Synastry FIELD×MODE Compatibility Layer

Compares two people's dominant FIELD and MODE signatures to produce
a pairing verdict in Agency language.

Architecture:
  Layer 1 — FIELD family compatibility (6 families, 36 pairings)
  Layer 2 — MODE family compatibility (4 families, 16 pairings)
  Layer 3 — Archetype pairing name + Claude verdict sentence

Usage:
    from antar_engine.synastry_engine import compute_field_mode_synastry
    result = compute_field_mode_synastry(archetype_a, archetype_b, name_a, name_b)
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# FIELD FAMILIES — group 27 fields into 6 archetypal families
# ═══════════════════════════════════════════════════════════════════

FIELD_FAMILY = {
    # COMMAND family — leadership, authority, victory, strategy
    "AUTHORITY":   "COMMAND",
    "VICTORY":     "COMMAND",
    "STRATEGY":    "COMMAND",
    "SIGNAL":      "COMMAND",
    "FOUNDATION":  "COMMAND",
    "EXECUTION":   "COMMAND",
    "MOMENTUM":    "COMMAND",

    # ALLIANCE family — connection, brokering, networks, adaptation
    "ALLIANCE":    "ALLIANCE",
    "ADAPTATION":  "ALLIANCE",
    "ANCHOR":      "ALLIANCE",
    "BRIDGE":      "ALLIANCE",

    # SPARK family — ignition, discovery, disruption, storm
    "STORM":       "SPARK",
    "DISCOVERY":   "SPARK",
    "THRESHOLD":   "SPARK",
    "SIGNAL":      "SPARK",

    # DEPTH family — completion, recovery, precision
    "COMPLETION":  "DEPTH",
    "RECOVERY":    "DEPTH",
    "DEPTH":       "DEPTH",
    "ARCHIVE":     "DEPTH",

    # NURTURE family — care, growth, abundance
    "NURTURE":     "NURTURE",
    "GROWTH":      "NURTURE",
    "ABUNDANCE":   "NURTURE",
    "HARVEST":     "NURTURE",

    # EXPANSION family — vision, scale
    "EXPANSION":   "EXPANSION",
    "VISION":      "EXPANSION",
    "BROADCAST":   "EXPANSION",
}

# ═══════════════════════════════════════════════════════════════════
# MODE FAMILIES — group 12 modes into 4 families
# ═══════════════════════════════════════════════════════════════════

MODE_FAMILY = {
    # DRIVE — action, force, initiation, disruption, building
    "DRIVE":       "DRIVE",
    "DISRUPT":     "DRIVE",
    "BUILD":       "DRIVE",
    "LAUNCH":      "DRIVE",
    "PUSH":        "DRIVE",

    # PENETRATE — depth, structure, dissolution, seeking
    "PENETRATE":   "PENETRATE",
    "STRUCTURE":   "PENETRATE",
    "DISSOLVE":    "PENETRATE",
    "SEEK":        "PENETRATE",
    "HOLD":        "PENETRATE",

    # BALANCE — harmony, connection, refinement, protection
    "BALANCE":     "BALANCE",
    "CONNECT":     "BALANCE",
    "REFINE":      "BALANCE",
    "PROTECT":     "BALANCE",
    "ADAPT":       "BALANCE",

    # EXPAND — vision, scale, distribution
    "EXPAND":      "EXPAND",
    "AMPLIFY":     "EXPAND",
    "BROADCAST":   "EXPAND",
}

# ═══════════════════════════════════════════════════════════════════
# FIELD FAMILY PAIRING TABLE
# (family_a, family_b) → {dynamic, label, description}
# Symmetric — engine normalizes order
# ═══════════════════════════════════════════════════════════════════

FIELD_PAIRING = {
    # Same family
    ("ALLIANCE",   "ALLIANCE"):  {"dynamic": "resonance",     "label": "NETWORK FUSION",    "description": "Double broker energy — unmatched reach when aligned"},
    ("COMMAND",    "COMMAND"):   {"dynamic": "resonance",     "label": "DUAL COMMAND",      "description": "Two authority centers — powerful but needs clear lanes"},
    ("DEPTH",      "DEPTH"):     {"dynamic": "resonance",     "label": "DUAL DEPTH",        "description": "Deep mastery pairing — slow but extraordinarily precise"},
    ("EXPANSION",  "EXPANSION"): {"dynamic": "resonance",     "label": "DUAL VISION",       "description": "Both think in decades — execution gap is the risk"},
    ("NURTURE",    "NURTURE"):   {"dynamic": "resonance",     "label": "DUAL NURTURE",      "description": "High care, high sustainability — can lack urgency"},
    ("SPARK",      "SPARK"):     {"dynamic": "resonance",     "label": "DUAL IGNITION",     "description": "Explosive creative energy — needs grounding or burns fast"},

    # Complementary — keys sorted alphabetically
    ("ALLIANCE",   "COMMAND"):   {"dynamic": "complementary", "label": "AUTHORITY + REACH", "description": "One commands, one connects — high-leverage partnership"},
    ("ALLIANCE",   "EXPANSION"): {"dynamic": "complementary", "label": "NETWORK + VISION",  "description": "Relationships meet scale — built for platform plays"},
    ("ALLIANCE",   "SPARK"):     {"dynamic": "complementary", "label": "BROKER + CATALYST", "description": "One opens doors, one lights the room — natural deal team"},
    ("COMMAND",    "EXPANSION"): {"dynamic": "complementary", "label": "AUTHORITY + VISION","description": "One sets direction, one sees the horizon — strong founder pair"},
    ("COMMAND",    "SPARK"):     {"dynamic": "complementary", "label": "COMMAND + IGNITION","description": "Authority with fire — builds fast, lands hard"},
    ("COMMAND",    "NURTURE"):   {"dynamic": "complementary", "label": "CARE + AUTHORITY",  "description": "One builds loyalty, one drives results — strong operator pair"},
    ("DEPTH",      "EXPANSION"): {"dynamic": "complementary", "label": "MASTERY + SCALE",   "description": "Deep expertise meets wide vision — category-defining pair"},
    ("DEPTH",      "SPARK"):     {"dynamic": "complementary", "label": "IGNITION + MASTERY","description": "Creativity backed by precision — rare and potent combination"},
    ("EXPANSION",  "NURTURE"):   {"dynamic": "complementary", "label": "ROOTS + WINGS",     "description": "Sustainability meets ambition — builds to last"},

    # Tension — keys sorted alphabetically
    ("ALLIANCE",   "DEPTH"):     {"dynamic": "tension",       "label": "NETWORK VS MASTERY","description": "Breadth meets depth — different operating rhythms"},
    ("ALLIANCE",   "NURTURE"):   {"dynamic": "tension",       "label": "CONNECT VS SUSTAIN","description": "Expansion instinct vs consolidation instinct — manageable"},
    ("COMMAND",    "DEPTH"):     {"dynamic": "tension",       "label": "SPEED VS PRECISION","description": "Authority wants fast decisions; depth needs full data — productive friction"},
    ("DEPTH",      "NURTURE"):   {"dynamic": "tension",       "label": "PRECISION VS FLOW", "description": "Analysis vs intuition — can balance if roles are clear"},
    ("EXPANSION",  "SPARK"):     {"dynamic": "tension",       "label": "FIRE VS SCALE",     "description": "Both want big — execution rhythm differs"},
    ("NURTURE",    "SPARK"):     {"dynamic": "tension",       "label": "IGNITION VS GROWTH","description": "Disruption meets sustainability — creative tension"},
}

# ═══════════════════════════════════════════════════════════════════
# MODE FAMILY PAIRING TABLE
# ═══════════════════════════════════════════════════════════════════

MODE_PAIRING = {
    # Same family (already symmetric)
    ("DRIVE",      "DRIVE"):     {"dynamic": "amplified",     "label": "DUAL DRIVE",        "description": "High velocity — watch for burnout or collision"},
    ("BALANCE",    "BALANCE"):   {"dynamic": "amplified",     "label": "DUAL HARMONY",      "description": "Smooth operations — may avoid necessary conflict"},
    ("EXPAND",     "EXPAND"):    {"dynamic": "amplified",     "label": "DUAL EXPANSION",    "description": "Big thinking — needs someone to execute"},
    ("PENETRATE",  "PENETRATE"): {"dynamic": "amplified",     "label": "DUAL DEPTH",        "description": "Both go deep — extraordinary focus, slow start"},

    # Complementary — keys sorted alphabetically
    ("BALANCE",    "DRIVE"):     {"dynamic": "complementary", "label": "FORCE + FINESSE",   "description": "Action meets diplomacy — strong negotiation pair"},
    ("DRIVE",      "EXPAND"):    {"dynamic": "complementary", "label": "PUSH + SCALE",      "description": "Execution meets vision — natural growth engine"},
    ("BALANCE",    "PENETRATE"): {"dynamic": "complementary", "label": "PRECISION + FLOW",  "description": "Analysis balanced by harmony — strong decision pair"},
    ("EXPAND",     "PENETRATE"): {"dynamic": "complementary", "label": "DEPTH + REACH",     "description": "Deep insight at scale — rare operating combination"},
    ("BALANCE",    "EXPAND"):    {"dynamic": "complementary", "label": "HARMONY + SCALE",   "description": "Sustainable growth — builds without breaking"},

    # Tension — keys sorted alphabetically
    ("DRIVE",      "PENETRATE"): {"dynamic": "tension",       "label": "SPEED VS DEPTH",    "description": "One moves fast, one goes deep — needs role clarity"},
    ("EXPAND",     "PENETRATE"): {"dynamic": "tension",       "label": "SCALE VS DETAIL",   "description": "Big picture vs granular — productive if respected"},
}


# Famous archetype combos get a named pairing
# ═══════════════════════════════════════════════════════════════════

ARCHETYPE_PAIRINGS = {
    # ── BROKER (114 charts — most common) ────────────────────────
    ("THE BROKER",      "THE MEDIATOR"):    ("THE NETWORK PAIR",        "Two connectors — unmatched relational range."),
    ("THE BROKER",      "THE GUARDIAN"):    ("THE RELIABLE CLOSE",      "One protects the relationship, one closes it."),
    ("THE BROKER",      "THE CATALYST"):    ("THE DEALMAKERS",          "Selling the future. One opens doors. One lights fires."),
    ("THE BROKER",      "THE REBEL"):       ("THE WILD CARD DEAL",      "Unconventional transaction. High risk, high reward."),
    ("THE BROKER",      "THE CRAFTSMAN"):   ("THE PRECISION + REACH",   "Deep expertise, wide network — formidable."),
    ("THE BROKER",      "THE CHAMPION"):    ("THE CLOSING PAIR",        "Drive meets transaction. Nothing stays open long."),
    ("THE BROKER",      "THE FINISHER"):    ("THE DEAL ENGINE",         "One structures, one completes. High execution synergy."),
    ("THE BROKER",      "THE NETWORKER"):   ("THE MULTIPLIER",          "Access meets transaction. One opens doors, one closes them."),
    ("THE BROKER",      "THE COMMANDER"):   ("THE EXECUTIVE DEAL",      "Mandate plus reach — authority that moves markets."),
    ("THE BROKER",      "THE OPERATOR"):    ("THE TREASURY",            "Wealth movement meets execution. High financial intelligence."),
    ("THE BROKER",      "THE FORGER"):      ("THE BUILDER DEAL",        "One builds the asset, one monetizes it."),
    ("THE BROKER",      "THE PATRON"):      ("THE SPONSOR PAIR",        "Capital meets connection — high-leverage backing."),
    ("THE BROKER",      "THE HAND"):        ("THE OPERATOR PAIR",       "One brokers, one delivers. Clean division of labor."),
    ("THE BROKER",      "THE MULTIPLIER"):  ("THE SCALE DEAL",          "One finds the deal, one scales the asset."),
    ("THE BROKER",      "THE BEDROCK"):     ("THE STABLE CLOSE",        "Reliability backs the transaction. Trust is the asset."),
    ("THE BROKER",      "THE AMPLIFIER"):   ("THE SIGNAL PAIR",         "Reach meets broadcast. Information moves fast."),
    ("THE BROKER",      "THE SCOUT"):       ("THE DISCOVERY DEAL",      "One finds the opportunity, one closes it."),
    ("THE BROKER",      "THE ACCELERATOR"): ("THE FAST CLOSE",          "Speed meets transaction. Built for rapid deals."),
    ("THE BROKER",      "THE ENGINE"):      ("THE POWER DEAL",          "One generates, one distributes. Sustained output."),
    ("THE BROKER",      "THE HEALER"):      ("THE TRUST PAIR",          "One restores, one connects. High relational capital."),

    # ── MEDIATOR (14 charts) ──────────────────────────────────────
    ("THE MEDIATOR",    "THE GUARDIAN"):    ("THE HARMONY PAIR",        "Care plus diplomacy — high relational intelligence."),
    ("THE MEDIATOR",    "THE CATALYST"):    ("THE REACTION",            "Raw energy refined into connection."),
    ("THE MEDIATOR",    "THE REBEL"):       ("THE CHESS PLAYERS",       "One challenges the rules, one navigates them."),
    ("THE MEDIATOR",    "THE CRAFTSMAN"):   ("THE PRECISION PAIR",      "Harmony meets mastery — smooth and exact."),
    ("THE MEDIATOR",    "THE CHAMPION"):    ("THE DIPLOMAT + DRIVE",    "Soft power backed by hard momentum."),
    ("THE MEDIATOR",    "THE FINISHER"):    ("THE RESOLUTION PAIR",     "One mediates, one closes. Conflict becomes completion."),
    ("THE MEDIATOR",    "THE NETWORKER"):   ("THE CONNECTOR PAIR",      "Double connection energy — unmatched relational range."),
    ("THE MEDIATOR",    "THE COMMANDER"):   ("THE DIPLOMAT + FORCE",    "Soft power backed by hard authority."),
    ("THE MEDIATOR",    "THE OPERATOR"):    ("THE COMFORT PAIR",        "Stability plus diplomacy. Great for client operations."),

    # ── GUARDIAN (11 charts) ──────────────────────────────────────
    ("THE GUARDIAN",    "THE CATALYST"):    ("THE BUILDER PAIR",        "One starts fires. One keeps them burning."),
    ("THE GUARDIAN",    "THE REBEL"):       ("THE TENSION PAIR",        "One protects, one disrupts. Constant negotiation."),
    ("THE GUARDIAN",    "THE CRAFTSMAN"):   ("THE FOUNDATION PAIR",     "Protection meets precision — nothing breaks here."),
    ("THE GUARDIAN",    "THE CHAMPION"):    ("THE FORTRESS PAIR",       "Authority and drive — built to last."),
    ("THE GUARDIAN",    "THE COMMANDER"):   ("THE COMMAND + SHIELD",    "Force backed by protection. Durable power."),
    ("THE GUARDIAN",    "THE OPERATOR"):    ("THE TRADITIONAL POWER",   "Classic hierarchy. Works in legacy organizations."),
    ("THE GUARDIAN",    "THE NETWORKER"):   ("THE TRUSTED HUB",         "Access plus reliability — high-trust network."),

    # ── CATALYST (6 charts) ───────────────────────────────────────
    ("THE CATALYST",    "THE REBEL"):       ("THE SUPERNOVA",           "High heat, high chaos. Brilliant for 0-to-1."),
    ("THE CATALYST",    "THE CRAFTSMAN"):   ("THE PRECISION IGNITION",  "Creativity backed by precision — rare and potent."),
    ("THE CATALYST",    "THE CHAMPION"):    ("THE STRIKE FORCE",        "Ignition plus drive — moves fast and hard."),
    ("THE CATALYST",    "THE COMMANDER"):   ("THE COMMAND + FIRE",      "Authority plus ignition — nothing stays still."),
    ("THE CATALYST",    "THE OPERATOR"):    ("THE CONTROLLED BURN",     "Disruption with a safety net. One breaks, one fixes."),
    ("THE CATALYST",    "THE NETWORKER"):   ("THE VIRAL PAIR",          "Ideas that spread instantly. High-energy growth."),

    # ── REBEL (5 charts) ─────────────────────────────────────────
    ("THE REBEL",       "THE CRAFTSMAN"):   ("THE DISRUPTOR",           "Breaking old systems with surgical intent."),
    ("THE REBEL",       "THE CHAMPION"):    ("THE CHAOS AGENTS",        "Unpredictable force. Great for launching."),
    ("THE REBEL",       "THE COMMANDER"):   ("THE COUP",                "Inevitable friction unless one bends."),
    ("THE REBEL",       "THE OPERATOR"):    ("THE WILD ENGINE",         "Raw disruption meets systems — explosive."),

    # ── CRAFTSMAN (5 charts) ──────────────────────────────────────
    ("THE CRAFTSMAN",   "THE CHAMPION"):    ("THE EXECUTION PAIR",      "Precision meets drive. Built to deliver."),
    ("THE CRAFTSMAN",   "THE COMMANDER"):   ("THE GATEKEEPER",          "Mastery backed by authority. High-standard pair."),
    ("THE CRAFTSMAN",   "THE OPERATOR"):    ("THE OPTIMIZER",           "One refines, one stabilizes. Operational excellence."),
    ("THE CRAFTSMAN",   "THE FINISHER"):    ("THE COMPLETION PAIR",     "Both finish what others start. Nothing left undone."),

    # ── CHAMPION (5 charts) ───────────────────────────────────────
    ("THE CHAMPION",    "THE COMMANDER"):   ("THE POWER PAIR",          "Two forces of authority — define lanes or collide."),
    ("THE CHAMPION",    "THE OPERATOR"):    ("THE DRIVE + SYSTEMS",     "Momentum meets structure. Scales well."),
    ("THE CHAMPION",    "THE FINISHER"):    ("THE CLOSER PAIR",         "Both drive to completion. High output."),

    # ── FINISHER (5 charts) ───────────────────────────────────────
    ("THE FINISHER",    "THE COMMANDER"):   ("THE MANDATE CLOSE",       "Authority plus completion — decisive and final."),
    ("THE FINISHER",    "THE OPERATOR"):    ("THE EMPIRE",              "Built for the long haul. Stability and completion."),
    ("THE FINISHER",    "THE NETWORKER"):   ("THE RELIABLE HUB",        "One builds systems, one activates channels."),

    # ── COMMANDER (4 charts) ─────────────────────────────────────
    ("THE COMMANDER",   "THE OPERATOR"):    ("THE HIERARCHY",           "Chain of command clear. Works in mature organizations."),
    ("THE COMMANDER",   "THE NETWORKER"):   ("THE POWER BROKER",        "Access to power. One knows everyone, one commands."),
    ("THE COMMANDER",   "THE MULTIPLIER"):  ("THE CROWN",               "Power plus scale. High-status, high-impact."),

    # ── OPERATOR (4 charts) ──────────────────────────────────────
    ("THE OPERATOR",    "THE MULTIPLIER"):  ("THE SCALE PAIR",          "Systems meet multiplication. Built for growth."),
    ("THE OPERATOR",    "THE NETWORKER"):   ("THE ENGINE PAIR",         "Structure meets access. One builds, one distributes."),

    # ── FORGER (3 charts) ────────────────────────────────────────
    ("THE FORGER",      "THE CHAMPION"):    ("THE IRON PAIR",           "Both forge under pressure. Extraordinary resilience."),
    ("THE FORGER",      "THE COMMANDER"):   ("THE FOUNDRY",             "Authority shapes raw material into legacy."),

    # ── MULTIPLIER (2 charts) ────────────────────────────────────
    ("THE MULTIPLIER",  "THE NETWORKER"):   ("THE AMPLIFIER PAIR",      "One creates scale, one activates reach."),

    # ── PATRON (2 charts) ────────────────────────────────────────
    ("THE PATRON",      "THE CATALYST"):    ("THE SPONSOR + SPARK",     "Capital meets ignition. High-leverage backing."),
    ("THE PATRON",      "THE FOUNDER"):     ("THE BACKING PAIR",        "Vision funded. One sees it, one backs it."),
}



# ═══════════════════════════════════════════════════════════════════
# SYNASTRY SCORE CONTRIBUTION
# ═══════════════════════════════════════════════════════════════════

DYNAMIC_SCORE = {
    "resonance":     10,   # Same family — natural alignment
    "complementary": 15,   # Different but fitting — highest value
    "amplified":      8,   # Same mode — strong but risk of echo
    "tension":        3,   # Friction — not bad, needs awareness
}


# ═══════════════════════════════════════════════════════════════════
# CORE FUNCTION
# ═══════════════════════════════════════════════════════════════════

def compute_field_mode_synastry(
    archetype_a: dict,
    archetype_b: dict,
    name_a: str = "Person A",
    name_b: str = "Person B",
) -> dict:
    """
    Compare two archetype dicts and return a synastry result.

    archetype_a / archetype_b shape (from charts.character_archetype):
    {
        "name": "THE BROKER",
        "field": "ALLIANCE",
        "mode": "PENETRATE",
        "tagline": "...",
        ...
    }

    Returns:
    {
        "archetype_a": "THE BROKER",
        "archetype_b": "THE CATALYST",
        "field_a": "ALLIANCE",
        "mode_a": "PENETRATE",
        "field_b": "SPARK",
        "mode_b": "EXPAND",
        "field_family_a": "ALLIANCE",
        "field_family_b": "SPARK",
        "mode_family_a": "PENETRATE",
        "mode_family_b": "EXPAND",
        "field_dynamic": "complementary",
        "field_label": "BROKER + CATALYST",
        "field_description": "One opens doors, one lights the room",
        "mode_dynamic": "tension",
        "mode_label": "DEPTH + REACH",
        "mode_description": "...",
        "pairing_name": "THE ACCELERATOR PAIR",
        "pairing_tagline": "One opens doors. One lights fires.",
        "score_contribution": 18,
        "verdict": "HIGH ACTIVATION",
        "verdict_detail": "...",
    }
    """
    if not archetype_a or not archetype_b:
        return {}

    arch_name_a = archetype_a.get("name", "UNKNOWN")
    arch_name_b = archetype_b.get("name", "UNKNOWN")
    # DB stores as dominant_field / dominant_mode
    field_a = archetype_a.get("dominant_field") or archetype_a.get("field", "")
    mode_a  = archetype_a.get("dominant_mode")  or archetype_a.get("mode", "")
    field_b = archetype_b.get("dominant_field") or archetype_b.get("field", "")
    mode_b  = archetype_b.get("dominant_mode")  or archetype_b.get("mode", "")

    # Get family groupings
    field_fam_a = FIELD_FAMILY.get(field_a, field_a)
    field_fam_b = FIELD_FAMILY.get(field_b, field_b)
    mode_fam_a  = MODE_FAMILY.get(mode_a, mode_a)
    mode_fam_b  = MODE_FAMILY.get(mode_b, mode_b)

    # Look up FIELD pairing (normalize order)
    field_key = _normalize_key(field_fam_a, field_fam_b)
    field_pair = FIELD_PAIRING.get(field_key, {
        "dynamic": "neutral",
        "label": f"{field_fam_a} + {field_fam_b}",
        "description": "Distinct operating fields — independent strengths",
    })

    # Look up MODE pairing
    mode_key = _normalize_key(mode_fam_a, mode_fam_b)
    mode_pair = MODE_PAIRING.get(mode_key, {
        "dynamic": "neutral",
        "label": f"{mode_fam_a} + {mode_fam_b}",
        "description": "Different execution rhythms — coordination needed",
    })

    # Named archetype pairing
    pairing_key = _normalize_key(arch_name_a, arch_name_b)
    pairing_name, pairing_tagline = ARCHETYPE_PAIRINGS.get(
        pairing_key,
        (f"{arch_name_a} + {arch_name_b}", f"{name_a} and {name_b} bring distinct strengths.")
    )

    # Score contribution
    field_score = DYNAMIC_SCORE.get(field_pair["dynamic"], 5)
    mode_score  = DYNAMIC_SCORE.get(mode_pair["dynamic"], 5)
    score_contribution = field_score + mode_score

    # Verdict
    verdict, verdict_detail = _compute_verdict(
        field_pair["dynamic"], mode_pair["dynamic"],
        arch_name_a, arch_name_b, name_a, name_b,
        field_pair["description"], mode_pair["description"]
    )

    return {
        "archetype_a":      arch_name_a,
        "archetype_b":      arch_name_b,
        "field_a":          field_a,
        "mode_a":           mode_a,
        "field_b":          field_b,
        "mode_b":           mode_b,
        "field_family_a":   field_fam_a,
        "field_family_b":   field_fam_b,
        "mode_family_a":    mode_fam_a,
        "mode_family_b":    mode_fam_b,
        "field_dynamic":    field_pair["dynamic"],
        "field_label":      field_pair["label"],
        "field_description":field_pair["description"],
        "mode_dynamic":     mode_pair["dynamic"],
        "mode_label":       mode_pair["label"],
        "mode_description": mode_pair["description"],
        "pairing_name":     pairing_name,
        "pairing_tagline":  pairing_tagline,
        "score_contribution": score_contribution,
        "verdict":          verdict,
        "verdict_detail":   verdict_detail,
    }


def _normalize_key(a: str, b: str) -> tuple:
    """Return tuple in alphabetical order for symmetric lookup."""
    return (min(a, b), max(a, b))


def _compute_verdict(
    field_dyn: str, mode_dyn: str,
    arch_a: str, arch_b: str,
    name_a: str, name_b: str,
    field_desc: str, mode_desc: str,
) -> tuple:
    """Compute verdict label and detail sentence."""

    combo = (field_dyn, mode_dyn)

    if combo in [("complementary", "complementary"), ("complementary", "amplified")]:
        verdict = "HIGH ACTIVATION"
        detail = f"{field_desc}. Execution rhythms align — this pairing accelerates both."

    elif combo in [("resonance", "complementary"), ("complementary", "resonance")]:
        verdict = "STRONG ALIGNMENT"
        detail = f"{field_desc}. {mode_desc}. Natural fit with room to grow."

    elif combo in [("resonance", "resonance"), ("amplified", "amplified")]:
        verdict = "MIRROR PAIR"
        detail = f"Strong natural resonance — risk of echo chamber. Deliberate role separation recommended."

    elif combo in [("complementary", "tension"), ("tension", "complementary")]:
        verdict = "PRODUCTIVE TENSION"
        detail = f"{field_desc}. {mode_desc}. The friction here is generative — not a warning."

    elif combo in [("resonance", "tension"), ("tension", "resonance")]:
        verdict = "MIXED SIGNALS"
        detail = f"Field alignment is strong. Execution styles differ — define lanes early."

    elif combo in [("tension", "tension")]:
        verdict = "FRICTION PAIR"
        detail = f"{field_desc}. {mode_desc}. High friction — can work with clear roles and mutual respect."

    elif combo in [("tension", "neutral"), ("neutral", "tension")]:
        verdict = "MIXED SIGNALS"
        detail = f"{field_desc}. Execution styles differ — define lanes early."

    elif combo in [("neutral", "neutral")]:
        verdict = "INDEPENDENT PAIR"
        detail = f"Distinct operating domains — independent strengths. Coordination is the key variable."

    else:
        verdict = "NEUTRAL PAIRING"
        detail = f"{field_desc}. Independent strengths — coordination is the key variable."

    return verdict, detail


# ═══════════════════════════════════════════════════════════════════
# HELPER — fetch or compute archetype for a chart
# ═══════════════════════════════════════════════════════════════════

def get_or_compute_archetype(chart_id: str, chart_data: dict, supabase) -> dict:
    """
    Fetch character_archetype from DB if stored.
    If not, compute on-the-fly from chart_data.
    Returns archetype dict or {}.
    """
    try:
        res = supabase.table("charts").select("character_archetype, planet_signatures").eq("id", chart_id).single().execute()
        if res.data and res.data.get("character_archetype"):
            return res.data["character_archetype"]
    except Exception as e:
        logger.warning(f"[synastry] Could not fetch archetype for {chart_id}: {e}")

    # Compute on-the-fly
    try:
        from antar_engine.natal_signatures import compute_natal_signatures, derive_archetype
        sigs = compute_natal_signatures(chart_data)
        return derive_archetype(sigs)
    except Exception as e:
        logger.warning(f"[synastry] Could not compute archetype for {chart_id}: {e}")
        return {}
