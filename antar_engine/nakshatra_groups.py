"""
nakshatra_groups.py — Three-group nakshatra classification system.
Classical Nadi/Trine grouping:
  Group 1 (1-9): Creation energy — action-first, early manifestation
  Group 2 (10-18): Sustaining energy — strategic, middle manifestation
  Group 3 (19-27): Wisdom energy — reflective, late manifestation
"""
from typing import Dict, Optional, Tuple

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
    "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Nakshatra lords (Vimsottari sequence repeating)
NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
]


def get_nakshatra_index(nakshatra_name: str) -> int:
    """Return 0-26 index for a nakshatra name. -1 if not found."""
    try:
        return NAKSHATRAS.index(nakshatra_name)
    except ValueError:
        # Try case-insensitive match
        for i, n in enumerate(NAKSHATRAS):
            if n.lower() == nakshatra_name.lower():
                return i
        return -1


def get_nakshatra_group(nakshatra_name: str) -> int:
    """Return group number (1, 2, or 3) for a nakshatra. 0 if unknown."""
    idx = get_nakshatra_index(nakshatra_name)
    if idx < 0:
        return 0
    if idx <= 8:
        return 1
    if idx <= 17:
        return 2
    return 3


def get_group_profile(group: int) -> Dict:
    """Return the full profile for a nakshatra group."""
    profiles = {
        1: {
            "group": 1,
            "name": "Creation Energy",
            "character": "Action-oriented, high physical vitality, impulsive, initiating",
            "event_timing": "early",  # events manifest early in dasha windows
            "pd_bias": "early",       # prefer early PDs in AD window
            "tone": "punchy",
            "tone_instruction": (
                "This user has Group 1 energy (creation, action-oriented). "
                "Lead with what to DO, then why. Shorter sentences. "
                "Less philosophy, more action. 'Here's what to do. Go.'"
            ),
            "strong_chakras": ["Root", "Sacral", "Solar Plexus"],
            "weak_chakras": ["Crown", "Third Eye"],
            "event_style": "sudden, physical, boom-or-bust",
            "career_style": "entrepreneurship, sales, trading, sports, emergency services, military",
            "relationship_style": "passionate, impulsive, intense start, risk of burnout",
        },
        2: {
            "group": 2,
            "name": "Sustaining Energy",
            "character": "Strategic, structural, balanced, politically aware",
            "event_timing": "middle",
            "pd_bias": "middle",
            "tone": "balanced",
            "tone_instruction": (
                "This user has Group 2 energy (sustaining, strategic). "
                "Equal weight to analysis and action. "
                "'Here's the pattern. Here's the strategy. Here's the move.'"
            ),
            "strong_chakras": ["Solar Plexus", "Heart", "Throat"],
            "weak_chakras": [],  # balanced across all
            "event_style": "structured, negotiated, process-driven",
            "career_style": "management, law, architecture, engineering, politics, banking",
            "relationship_style": "stable, commitment-oriented, status-conscious",
        },
        3: {
            "group": 3,
            "name": "Wisdom Energy",
            "character": "Reflective, philosophical, pattern-recognition, old soul",
            "event_timing": "late",
            "pd_bias": "late",
            "tone": "reflective",
            "tone_instruction": (
                "This user has Group 3 energy (wisdom, reflective). "
                "Lead with WHY and PATTERN, then action. "
                "'Here's what this means. Here's the deeper pattern. "
                "And here's the one thing to do about it.'"
            ),
            "strong_chakras": ["Crown", "Third Eye", "Throat"],
            "weak_chakras": ["Root", "Sacral"],
            "event_style": "gradual, internal first then external, contemplative",
            "career_style": "research, consulting, teaching, writing, technology architecture, advisory",
            "relationship_style": "deep understanding, slow to commit, meaning-seeking",
        },
    }
    return profiles.get(group, profiles[2])  # default to Group 2 if unknown


def get_cross_group_dynamic(group_a: int, group_b: int) -> Dict:
    """
    Return the relationship dynamic between two nakshatra groups.
    Used in compatibility engine.
    """
    key = tuple(sorted([group_a, group_b]))
    dynamics = {
        (1, 1): {
            "dynamic": "Explosive Energy",
            "description": "Two creation energies together — passionate, intense, high initial chemistry",
            "strength": "Powerful momentum, shared drive, physical chemistry",
            "risk": "Burnout, competition, both want to lead",
            "advice": "Focus on sustainability. Take turns leading. Build rest into the rhythm.",
            "compatibility_modifier": -1,  # slight deduction — needs work
        },
        (1, 2): {
            "dynamic": "Builder & Driver",
            "description": "Action energy meets strategic energy — one drives, one structures",
            "strength": "Complementary — one initiates, one sustains. Good working partnership.",
            "risk": "Group 1 feels slowed down. Group 2 feels rushed.",
            "advice": "Respect the pacing difference. Group 1 brings energy, Group 2 brings strategy.",
            "compatibility_modifier": 1,  # natural complement
        },
        (1, 3): {
            "dynamic": "Fire & Water",
            "description": "Action energy meets wisdom energy — natural complement but communication gap",
            "strength": "Each has what the other lacks. Deep mutual fascination.",
            "risk": "Group 1 acts before Group 3 finishes thinking. Communication timing mismatch.",
            "advice": "Group 1: slow down for the wisdom. Group 3: don't overthink the action.",
            "compatibility_modifier": 2,  # strongest complement
        },
        (2, 2): {
            "dynamic": "Stable Foundation",
            "description": "Two sustaining energies — stable, reliable, structured",
            "strength": "Mutual understanding, shared values around stability and growth",
            "risk": "Stagnation. Both maintain, neither disrupts. Can become too comfortable.",
            "advice": "Intentionally introduce growth challenges. Travel together. Try new things.",
            "compatibility_modifier": 0,  # neutral
        },
        (2, 3): {
            "dynamic": "Strategy & Depth",
            "description": "Strategic energy meets wisdom energy — intellectual rapport",
            "strength": "Deep conversations, mutual respect, shared long-term thinking",
            "risk": "Both can be too cerebral. Lacking spontaneity and physical energy.",
            "advice": "Add physical activities and playfulness. Don't let every interaction be a strategy session.",
            "compatibility_modifier": 1,  # good match
        },
        (3, 3): {
            "dynamic": "Deep Understanding",
            "description": "Two wisdom energies — profound connection, shared inner world",
            "strength": "Know each other without words. Spiritual connection. Pattern recognition.",
            "risk": "Low activation energy. Can get stuck in philosophical mode. Material world neglected.",
            "advice": "Ground the relationship in physical activity and material goals. Meditate together but also build together.",
            "compatibility_modifier": -1,  # needs grounding
        },
    }
    return dynamics.get(key, dynamics[(2, 2)])  # default to neutral


def get_pd_bias_multiplier(group: int, pd_position: str) -> float:
    """
    Return a confidence multiplier for PD position based on nakshatra group.

    pd_position: "early" (first third of ADs in the window),
                 "middle" (second third), "late" (final third)

    Group 1 events happen early -> early PDs get boosted
    Group 3 events happen late -> late PDs get boosted
    """
    multipliers = {
        1: {"early": 1.3, "middle": 1.0, "late": 0.7},
        2: {"early": 0.9, "middle": 1.3, "late": 0.9},
        3: {"early": 0.7, "middle": 1.0, "late": 1.3},
    }
    return multipliers.get(group, {}).get(pd_position, 1.0)


def get_chakra_group_baseline(group: int) -> Dict[str, int]:
    """
    Return baseline chakra completion adjustments by group.
    Applied BEFORE practice completions and convergence scoring.

    Returns dict: { "Root": +10, "Crown": -5, ... }
    Positive = natural strength, Negative = natural weakness.
    """
    baselines = {
        1: {
            "Root": 10, "Sacral": 8, "Solar Plexus": 5,
            "Heart": 0, "Throat": -3,
            "Third Eye": -8, "Crown": -10,
        },
        2: {
            "Root": 0, "Sacral": 0, "Solar Plexus": 5,
            "Heart": 5, "Throat": 5,
            "Third Eye": 0, "Crown": 0,
        },
        3: {
            "Root": -10, "Sacral": -8, "Solar Plexus": -3,
            "Heart": 0, "Throat": 3,
            "Third Eye": 8, "Crown": 10,
        },
    }
    return baselines.get(group, baselines[2])


def format_nakshatra_for_prompt(nakshatra_name: str) -> str:
    """
    Format nakshatra group info as a context block for LLM prompts.
    """
    group = get_nakshatra_group(nakshatra_name)
    if group == 0:
        return ""
    profile = get_group_profile(group)
    return (
        f"NAKSHATRA GROUP: {nakshatra_name} — Group {group} ({profile['name']})\n"
        f"  {profile['tone_instruction']}\n"
        f"  Event timing tendency: {profile['event_timing']} in dasha windows\n"
        f"  Natural strengths: {', '.join(profile['strong_chakras'])} chakras\n"
        f"  Career affinity: {profile['career_style']}\n"
        f"  Relationship style: {profile['relationship_style']}"
    )
