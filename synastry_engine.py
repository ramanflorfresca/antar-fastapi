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
    # AUTHORITY family — leadership, command, visibility
    "AUTHORITY":   "COMMAND",
    "SIGNAL":      "COMMAND",
    "FOUNDATION":  "COMMAND",
    "STRUCTURE":   "COMMAND",

    # ALLIANCE family — connection, brokering, networks
    "ALLIANCE":    "ALLIANCE",
    "BRIDGE":      "ALLIANCE",
    "NETWORK":     "ALLIANCE",
    "CHANNEL":     "ALLIANCE",

    # SPARK family — ignition, creativity, disruption
    "SPARK":       "SPARK",
    "FLAME":       "SPARK",
    "IGNITION":    "SPARK",
    "CATALYST":    "SPARK",

    # DEPTH family — investigation, precision, mastery
    "DEPTH":       "DEPTH",
    "PRECISION":   "DEPTH",
    "MASTERY":     "DEPTH",
    "ARCHIVE":     "DEPTH",

    # NURTURE family — care, growth, sustenance
    "NURTURE":     "NURTURE",
    "GROWTH":      "NURTURE",
    "HARVEST":     "NURTURE",
    "FLOW":        "NURTURE",

    # EXPANSION family — vision, philosophy, scale
    "EXPANSION":   "EXPANSION",
    "VISION":      "EXPANSION",
    "HORIZON":     "EXPANSION",
    "BROADCAST":   "EXPANSION",
}

# ═══════════════════════════════════════════════════════════════════
# MODE FAMILIES — group 12 modes into 4 families
# ═══════════════════════════════════════════════════════════════════

MODE_FAMILY = {
    # DRIVE — action, force, initiation
    "IGNITE":      "DRIVE",
    "PUSH":        "DRIVE",
    "LAUNCH":      "DRIVE",

    # PENETRATE — depth, precision, investigation
    "PENETRATE":   "PENETRATE",
    "HOLD":        "PENETRATE",
    "ANCHOR":      "PENETRATE",

    # BALANCE — harmony, mediation, adaptation
    "BALANCE":     "BALANCE",
    "ADAPT":       "BALANCE",
    "REFINE":      "BALANCE",

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
    ("COMMAND",    "COMMAND"):    {"dynamic": "resonance",     "label": "DUAL COMMAND",      "description": "Two authority centers — powerful but needs clear lanes"},
    ("ALLIANCE",   "ALLIANCE"):  {"dynamic": "resonance",     "label": "NETWORK FUSION",    "description": "Double broker energy — unmatched reach when aligned"},
    ("SPARK",      "SPARK"):     {"dynamic": "resonance",     "label": "DUAL IGNITION",     "description": "Explosive creative energy — needs grounding or burns fast"},
    ("DEPTH",      "DEPTH"):     {"dynamic": "resonance",     "label": "DUAL DEPTH",        "description": "Deep mastery pairing — slow but extraordinarily precise"},
    ("NURTURE",    "NURTURE"):   {"dynamic": "resonance",     "label": "DUAL NURTURE",      "description": "High care, high sustainability — can lack urgency"},
    ("EXPANSION",  "EXPANSION"): {"dynamic": "resonance",     "label": "DUAL VISION",       "description": "Both think in decades — execution gap is the risk"},

    # Complementary pairings
    ("COMMAND",    "ALLIANCE"):  {"dynamic": "complementary", "label": "AUTHORITY + REACH", "description": "One commands, one connects — high-leverage partnership"},
    ("COMMAND",    "SPARK"):     {"dynamic": "complementary", "label": "COMMAND + IGNITION","description": "Authority with fire — builds fast, lands hard"},
    ("COMMAND",    "EXPANSION"): {"dynamic": "complementary", "label": "AUTHORITY + VISION","description": "One sets direction, one sees the horizon — strong founder pair"},
    ("ALLIANCE",   "SPARK"):     {"dynamic": "complementary", "label": "BROKER + CATALYST", "description": "One opens doors, one lights the room — natural deal team"},
    ("ALLIANCE",   "EXPANSION"): {"dynamic": "complementary", "label": "NETWORK + VISION",  "description": "Relationships meet scale — built for platform plays"},
    ("SPARK",      "DEPTH"):     {"dynamic": "complementary", "label": "IGNITION + MASTERY","description": "Creativity backed by precision — rare and potent combination"},
    ("DEPTH",      "EXPANSION"): {"dynamic": "complementary", "label": "MASTERY + SCALE",   "description": "Deep expertise meets wide vision — category-defining pair"},
    ("NURTURE",    "COMMAND"):   {"dynamic": "complementary", "label": "CARE + AUTHORITY",  "description": "One builds loyalty, one drives results — strong operator pair"},
    ("NURTURE",    "EXPANSION"): {"dynamic": "complementary", "label": "ROOTS + WINGS",     "description": "Sustainability meets ambition — builds to last"},

    # Tension pairings
    ("COMMAND",    "DEPTH"):     {"dynamic": "tension",       "label": "SPEED VS PRECISION","description": "Authority wants fast decisions; depth needs full data — productive friction"},
    ("COMMAND",    "NURTURE"):   {"dynamic": "tension",       "label": "DRIVE VS CARE",     "description": "Results vs relationships — needs conscious navigation"},
    ("ALLIANCE",   "DEPTH"):     {"dynamic": "tension",       "label": "NETWORK VS MASTERY","description": "Breadth meets depth — different operating rhythms"},
    ("ALLIANCE",   "NURTURE"):   {"dynamic": "tension",       "label": "CONNECT VS SUSTAIN","description": "Expansion instinct vs consolidation instinct — manageable"},
    ("SPARK",      "NURTURE"):   {"dynamic": "tension",       "label": "IGNITION VS GROWTH","description": "Disruption meets sustainability — creative tension"},
    ("SPARK",      "EXPANSION"): {"dynamic": "tension",       "label": "FIRE VS SCALE",     "description": "Both want big — execution rhythm differs"},
    ("DEPTH",      "NURTURE"):   {"dynamic": "tension",       "label": "PRECISION VS FLOW", "description": "Analysis vs intuition — can balance if roles are clear"},
}

# ═══════════════════════════════════════════════════════════════════
# MODE FAMILY PAIRING TABLE
# ═══════════════════════════════════════════════════════════════════

MODE_PAIRING = {
    # Same family
    ("DRIVE",      "DRIVE"):     {"dynamic": "amplified",     "label": "DUAL DRIVE",        "description": "High velocity — watch for burnout or collision"},
    ("PENETRATE",  "PENETRATE"): {"dynamic": "amplified",     "label": "DUAL DEPTH",        "description": "Both go deep — extraordinary focus, slow start"},
    ("BALANCE",    "BALANCE"):   {"dynamic": "amplified",     "label": "DUAL HARMONY",      "description": "Smooth operations — may avoid necessary conflict"},
    ("EXPAND",     "EXPAND"):    {"dynamic": "amplified",     "label": "DUAL EXPANSION",    "description": "Big thinking — needs someone to execute"},

    # Complementary
    ("DRIVE",      "BALANCE"):   {"dynamic": "complementary", "label": "FORCE + FINESSE",   "description": "Action meets diplomacy — strong negotiation pair"},
    ("DRIVE",      "EXPAND"):    {"dynamic": "complementary", "label": "PUSH + SCALE",      "description": "Execution meets vision — natural growth engine"},
    ("PENETRATE",  "EXPAND"):    {"dynamic": "complementary", "label": "DEPTH + REACH",     "description": "Deep insight at scale — rare operating combination"},
    ("PENETRATE",  "BALANCE"):   {"dynamic": "complementary", "label": "PRECISION + FLOW",  "description": "Analysis balanced by harmony — strong decision pair"},
    ("BALANCE",    "EXPAND"):    {"dynamic": "complementary", "label": "HARMONY + SCALE",   "description": "Sustainable growth — builds without breaking"},

    # Tension
    ("DRIVE",      "PENETRATE"): {"dynamic": "tension",       "label": "SPEED VS DEPTH",    "description": "One moves fast, one goes deep — needs role clarity"},
    ("EXPAND",     "PENETRATE"): {"dynamic": "tension",       "label": "SCALE VS DETAIL",   "description": "Big picture vs granular — productive if respected"},
}

# ═══════════════════════════════════════════════════════════════════
# ARCHETYPE PAIRING NAMES
# Famous archetype combos get a named pairing
# ═══════════════════════════════════════════════════════════════════

ARCHETYPE_PAIRINGS = {
    # ── BROKER pairings ───────────────────────────────────────────
    ("THE BROKER",      "THE CATALYST"):    ("THE DEALMAKERS",         "Selling the future. One opens doors. One lights fires."),
    ("THE BROKER",      "THE COMMANDER"):   ("THE EXECUTIVE DEAL",     "Mandate plus transaction. Authority meets reach."),
    ("THE BROKER",      "THE MEDIATOR"):    ("THE NETWORK PAIR",       "Two connectors — unmatched relational range."),
    ("THE BROKER",      "THE FOUNDER"):     ("THE DEALMAKERS",         "Selling the future. Best for fundraising and high-stakes sales."),
    ("THE BROKER",      "THE OPERATOR"):    ("THE TREASURY",           "Wealth movement meets execution. High financial intelligence."),
    ("THE BROKER",      "THE MULTIPLIER"):  ("THE MULTIPLIER DEAL",    "One finds the deal, one scales the asset."),
    ("THE BROKER",      "THE SURGEON"):     ("THE PRECISION + REACH",  "Deep expertise, wide network — formidable."),
    ("THE BROKER",      "THE GUARDIAN"):    ("THE RELIABLE CLOSE",     "One protects the relationship, one closes it."),
    ("THE BROKER",      "THE REBEL"):       ("THE WILD CARD DEAL",     "Unconventional transaction. High risk, high reward."),
    ("THE BROKER",      "THE NETWORKER"):   ("THE MULTIPLIER",         "Access meets transaction. One opens doors, one closes them."),
    ("THE BROKER",      "THE AMPLIFIER"):   ("THE CLOSING PAIR",       "Charm closes the deal. High-ticket sales synergy."),
    ("THE BROKER",      "THE ENGINE"):      ("THE DEAL ENGINE",        "One structures the deal, one powers execution."),

    # ── COMMANDER / AUTHORITY pairings ───────────────────────────
    ("THE COMMANDER",   "THE CATALYST"):    ("THE STRIKE FORCE",       "Command and ignition — moves fast and hard."),
    ("THE COMMANDER",   "THE GUARDIAN"):    ("THE FORTRESS PAIR",      "Authority and protection — built to last."),
    ("THE COMMANDER",   "THE FOUNDER"):     ("THE COMMAND CENTER",     "Both want control. Works when domains are separated."),
    ("THE COMMANDER",   "THE OPERATOR"):    ("THE HIERARCHY",          "Chain of command is clear. Works in mature organizations."),
    ("THE COMMANDER",   "THE MULTIPLIER"):  ("THE CROWN",              "Power plus scale. High-status, high-impact pairing."),
    ("THE COMMANDER",   "THE MEDIATOR"):    ("THE DIPLOMAT + FORCE",   "Soft power backed by hard authority."),
    ("THE COMMANDER",   "THE REBEL"):       ("THE COUP",               "Inevitable friction unless one bends. High tension."),
    ("THE COMMANDER",   "THE NETWORKER"):   ("THE POWER BROKER",       "Access to power. One knows everyone, one commands respect."),
    ("THE COMMANDER",   "THE AMPLIFIER"):   ("THE CROWN",              "Power plus charm. High-status pairing."),
    ("THE COMMANDER",   "THE SURGEON"):     ("THE GATEKEEPER",         "Tension between precision and mandate. Works if Authority trusts."),

    # ── CATALYST pairings ────────────────────────────────────────
    ("THE CATALYST",    "THE GUARDIAN"):    ("THE BUILDER PAIR",       "One starts fires. One keeps them burning."),
    ("THE CATALYST",    "THE FOUNDER"):     ("THE ECHO CHAMBER",       "Both dream. Execution gap risk. Needs a Steward to ground it."),
    ("THE CATALYST",    "THE OPERATOR"):    ("THE CONTROLLED BURN",    "Disruption with a safety net. One breaks, one fixes."),
    ("THE CATALYST",    "THE MULTIPLIER"):  ("THE SCALE PAIR",         "Fast growth that actually sticks."),
    ("THE CATALYST",    "THE MEDIATOR"):    ("THE REACTION",           "Raw energy refined into connection. Creative and relational."),
    ("THE CATALYST",    "THE REBEL"):       ("THE SUPERNOVA",          "High heat, high chaos. Brilliant for 0-to-1, risky for scale."),
    ("THE CATALYST",    "THE NETWORKER"):   ("THE VIRAL PAIR",         "Ideas that spread instantly. High-energy growth."),
    ("THE CATALYST",    "THE AMPLIFIER"):   ("THE ATTRACTION",         "Ideas plus charm. High-influence fundraising."),
    ("THE CATALYST",    "THE SURGEON"):     ("THE PRECISION IGNITION", "Creativity backed by precision — rare and potent."),
    ("THE CATALYST",    "THE ENGINE"):      ("THE LAUNCHER",           "One ignites, one sustains. Classic start-and-build duo."),

    # ── FOUNDER / VISIONARY pairings ─────────────────────────────
    ("THE FOUNDER",     "THE OPERATOR"):    ("THE EXECUTION PAIR",     "Vision meets systems — the classic startup duo."),
    ("THE FOUNDER",     "THE MULTIPLIER"):  ("THE SCALE PAIR",         "What one builds, the other multiplies."),
    ("THE FOUNDER",     "THE SURGEON"):     ("THE INVENTION",          "One sees the future, one builds it. Founder + CTO."),
    ("THE FOUNDER",     "THE GUARDIAN"):    ("THE ROOTS + WINGS",      "Sustainability meets ambition — builds to last."),
    ("THE FOUNDER",     "THE NETWORKER"):   ("THE SIGNAL",             "One sees the future, the other tells everyone about it."),
    ("THE FOUNDER",     "THE AMPLIFIER"):   ("THE MIRROR PAIR",        "Both attract. High external focus, low internal execution."),
    ("THE FOUNDER",     "THE REBEL"):       ("THE REVOLUTION",         "Change at any cost. Great for transformation, risky for stability."),

    # ── OPERATOR / STEWARD pairings ──────────────────────────────
    ("THE OPERATOR",    "THE MULTIPLIER"):  ("THE EMPIRE",             "Built for the long haul. Absolute stability and operational excellence."),
    ("THE OPERATOR",    "THE SURGEON"):     ("THE OPTIMIZER",          "One refines, one stabilizes. Operational excellence."),
    ("THE OPERATOR",    "THE NETWORKER"):   ("THE RELIABLE HUB",       "One builds the system, one activates the channels."),
    ("THE OPERATOR",    "THE GUARDIAN"):    ("THE TRADITIONAL POWER",  "Classic hierarchy. Works well in legacy organizations."),
    ("THE OPERATOR",    "THE AMPLIFIER"):   ("THE COMFORT PAIR",       "Stability plus charm. Great for client-facing operations."),
    ("THE OPERATOR",    "THE REBEL"):       ("THE CONTROLLED BURN",    "Disruption with a safety net. One breaks, one fixes."),
    ("THE OPERATOR",    "THE ENGINE"):      ("THE PRECISION PAIR",     "Hyper-optimized. Great for R&D or complex engineering."),

    # ── MULTIPLIER pairings ──────────────────────────────────────
    ("THE MULTIPLIER",  "THE SURGEON"):     ("THE VALUE EXTRACTOR",    "One finds the deal, one optimizes the asset. PE energy."),
    ("THE MULTIPLIER",  "THE NETWORKER"):   ("THE ENGINE",             "Structure meets access. One builds, one distributes."),
    ("THE MULTIPLIER",  "THE AMPLIFIER"):   ("THE INFLUENCE PAIR",     "Charisma squared. High social capital."),
    ("THE MULTIPLIER",  "THE REBEL"):       ("THE DISRUPTOR",          "Breaking old systems to build the new. Best for pivot moments."),

    # ── MEDIATOR pairings ────────────────────────────────────────
    ("THE MEDIATOR",    "THE GUARDIAN"):    ("THE HARMONY PAIR",       "Care plus diplomacy — high relational intelligence."),
    ("THE MEDIATOR",    "THE NETWORKER"):   ("THE CONNECTOR PAIR",     "Double connection energy — unmatched reach when aligned."),
    ("THE MEDIATOR",    "THE REBEL"):       ("THE CHESS PLAYERS",      "Strategic tension. One challenges the rules, one navigates them."),

    # ── SURGEON / PRECISION pairings ─────────────────────────────
    ("THE SURGEON",     "THE NETWORKER"):   ("THE IDEA AMPLIFIER",     "One creates, one distributes. High synergy for tech."),
    ("THE SURGEON",     "THE GUARDIAN"):    ("THE BLUEPRINT",          "Planning meets precision — the ultimate detail pair."),
    ("THE SURGEON",     "THE REBEL"):       ("THE PRECISION DISRUPTOR","Breaking with surgical intent. Deliberate destruction."),
    ("THE SURGEON",     "THE AMPLIFIER"):   ("THE POLISHED INVENTION", "One builds, one sells. Great for product-led companies."),

    # ── NETWORKER pairings ───────────────────────────────────────
    ("THE NETWORKER",   "THE GUARDIAN"):    ("THE TRUSTED HUB",        "Access plus reliability — high-trust relationship network."),
    ("THE NETWORKER",   "THE REBEL"):       ("THE CHAOS AGENTS",       "Unpredictable. Great for launching, dangerous for operating."),
    ("THE NETWORKER",   "THE AMPLIFIER"):   ("THE INFLUENCE PAIR",     "Charisma squared. High social capital, low operational focus."),

    # ── GUARDIAN pairings ────────────────────────────────────────
    ("THE GUARDIAN",    "THE REBEL"):       ("THE TENSION PAIR",       "One protects, one disrupts. Constant negotiation required."),
    ("THE GUARDIAN",    "THE AMPLIFIER"):   ("THE COMFORT PAIR",       "Warmth plus visibility. Great for community-driven brands."),

    # ── REBEL pairings ───────────────────────────────────────────
    ("THE REBEL",       "THE AMPLIFIER"):   ("THE SEDUCTIVE REBEL",    "Charm plus disruption. High influence, low predictability."),
    ("THE REBEL",       "THE ENGINE"):      ("THE WILD ENGINE",        "Raw force meets disruption — explosive but hard to steer."),
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
    field_a = archetype_a.get("field", "")
    mode_a  = archetype_a.get("mode", "")
    field_b = archetype_b.get("field", "")
    mode_b  = archetype_b.get("mode", "")

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
    return tuple(sorted([a, b]))


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
