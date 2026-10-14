"""
antar_engine/vastu_rules.py

The Vastu-Jyotish (Parashari-based) RULES TABLE — pure data, no logic. 2026-10-14

Owner chose the tradition: Vastu-Jyotish, Parashari-based. Every line the user
sees is built from a row here, so nothing is LLM-invented and every row carries a
`src` id. Spec: Antar.world/VASTU_JYOTISH_RULES_SPEC_2026-10-14.md

VERIFICATION STATUS (read before shipping): no primary text has been chosen yet.
Rows tagged verified=False are the widely repeated general Vastu / Vastu-Jyotish
attributions, written from the standard framework, NOT checked against a page of
a named book. The planet <-> compass-zone map (ZONES) is the best-attested part;
the object-placement rows (OBJECTS) are the least. The route is therefore behind
the `vastu_enabled` app_config flag (default OFF) until the owner signs the rows
off — see VERIFIED below.

Faith-neutral by design: "devotional image or statue", never a named deity or
house of worship (matches tests/test_faith_neutral.py).
"""
from __future__ import annotations

# Flip to True only after the owner reviews/cites the rows. The engine copies it
# into the payload's `meta.rules_verified`; the route flag is the real gate.
VERIFIED = False

TRADITION = "vastu_jyotish_parashari"

# ── Compass zones ────────────────────────────────────────────────────────────
# code -> plain label. Order is clockwise from East.
ZONE_ORDER = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]

ZONE_LABEL = {
    "E": "East", "SE": "South-East", "S": "South", "SW": "South-West",
    "W": "West", "NW": "North-West", "N": "North", "NE": "North-East",
}

# Zone -> governing grahas, primary first, with a weight. A secondary lord only
# breaks a tie when the primary is neutral (see vastu_engine._zone_class).
# Rahu holds SW; Ketu is the 180-degree opposite of Rahu, so it holds NE
# (owner rule 2026-10-14: "Ketu should be opposite of Rahu").
ZONE_LORDS = {
    "E":  ["Sun"],
    "SE": ["Venus"],
    "S":  ["Mars"],
    "SW": ["Rahu"],
    "W":  ["Saturn"],
    "NW": ["Moon"],
    "N":  ["Mercury"],
    "NE": ["Jupiter", "Ketu"],
}

# Inverse: graha -> the zone it governs.
PLANET_ZONE = {p: z for z, lords in ZONE_LORDS.items() for p in lords}

# Plain-language "what this zone is about" — NO graha / house names.
ZONE_GOVERNS = {
    "E":  "recognition, vitality and a good start to the day",
    "SE": "comfort, relationships, money flow and creative energy",
    "S":  "drive, courage and standing your ground",
    "SW": "stability, roots, support and staying power",
    "W":  "steady effort, discipline and the rewards of long work",
    "NW": "movement, mood, travel and your social circle",
    "N":  "opportunity, communication and commerce",
    "NE": "clarity, learning, guidance and inner calm",
}

# Parashari dig bala (directional strength) — house where each graha is strong.
# Used ONLY as a tie-break between equally scored zones, never as added evidence
# (it is the same graha, so it is correlated with its own score).
DIG_BALA_HOUSE = {
    "Jupiter": 1, "Mercury": 1,
    "Sun": 10, "Mars": 10,
    "Saturn": 7,
    "Moon": 4, "Venus": 4,
}

# ── Surfacing caps ───────────────────────────────────────────────────────────
# A chart can strain many planets at once; telling someone 6 of 8 directions are
# a problem is fear-selling and carries no information. Only the worst few are
# surfaced as "needs a lighter touch", only the best few as "supports you". A
# capped planet becomes NEUTRAL, never the opposite, so this can only drop a
# claim, not contradict the colour/gem read (which caps its lists at four).
MAX_NEEDS_CARE = 2
MAX_STRONG = 3

# ── Safe classical envelopes ─────────────────────────────────────────────────
# The chart personalises ONLY inside these sets (owner decision 2026-10-14).
SLEEP_HEAD_ENVELOPE = ["S", "E"]        # head toward South or East, never North
WORK_FACING_ENVELOPE = ["N", "E", "NE"]
EAT_FACING_ENVELOPE = ["E", "N"]
# Tie-break when the chart has no preference: first item wins.

# ── Object-placement rows ────────────────────────────────────────────────────
# id, plain label, best zones, avoid zones, note, contested.
# `contested` = traditions disagree; the note says so rather than picking a side.
# All rows verified=False until the owner signs off (see header).
OBJECTS = [
    {
        "id": "devotional_images",
        "label": "Devotional images or statues of a deity or sacred figure",
        "best": ["NE", "E", "N"],
        "avoid": ["SW", "S", "SE"],
        "note": ("Keep them out of bedrooms and bathrooms, and never on a wall that "
                 "backs onto a toilet. A clean, uncluttered corner matters more than the size."),
        "contested": False,
    },
    {
        "id": "ancestor_photos",
        "label": "Photographs of ancestors or loved ones who have passed",
        "best": ["S"],
        "avoid": ["NE", "E", "N"],
        "note": ("Traditionally on the south wall, never in the prayer or meditation corner, "
                 "the bedroom, or facing the main entrance."),
        "contested": False,
    },
    {
        "id": "distressing_images",
        "label": "Pictures of war, violence, wild or fighting animals, or sad scenes",
        "best": [],
        "avoid": list(ZONE_ORDER),
        "note": ("Best kept out of the main living and sleeping areas altogether. "
                 "Calm landscapes and growth scenes are the traditional choice."),
        "contested": False,
    },
    {
        "id": "elephant_statues",
        "label": "Elephant statues",
        "best": ["SW", "W"],
        "avoid": ["NE", "SE"],
        "note": ("Traditionally kept as a pair, and not in the bedroom. Traditions disagree on "
                 "the trunk: raised is read as ambition and protection, lowered as steadiness "
                 "and blessings flowing in. Choose by what you want more of."),
        "contested": True,
    },
    {
        "id": "water_features",
        "label": "Fountains, aquariums and other water features",
        "best": ["NE", "N", "E"],
        "avoid": ["SW", "S", "SE"],
        "note": "Keep the water clean and moving; stagnant or dirty water cancels the benefit.",
        "contested": False,
    },
    {
        "id": "mirrors",
        "label": "Mirrors",
        "best": ["N", "E"],
        "avoid": ["S", "SW"],
        "note": "Never facing the bed or the front door.",
        "contested": False,
    },
    {
        "id": "heavy_furniture",
        "label": "Heavy furniture, big storage and stone or metal pieces",
        "best": ["SW", "S", "W"],
        "avoid": ["NE", "N", "E"],
        "note": "Keep the north-east and east open and light; weight belongs to the south-west.",
        "contested": False,
    },
    {
        "id": "safe_or_cash",
        "label": "A safe or cash box",
        "best": ["SW", "N"],
        "avoid": ["NE", "SE"],
        "note": "Traditionally placed so the door opens toward the north.",
        "contested": False,
    },
    {
        "id": "fire_sources",
        "label": "Stove, heaters and strong electrical equipment",
        "best": ["SE", "NW"],
        "avoid": ["NE", "N"],
        "note": "Fire and water zones should not share a wall.",
        "contested": False,
    },
    {
        "id": "indoor_plants",
        "label": "Indoor plants",
        "best": ["N", "NE", "E"],
        "avoid": [],
        "note": ("Small, leafy plants are the traditional choice; tall heavy ones suit the "
                 "south-west. Avoid thorny plants indoors and remove dried or dead ones."),
        "contested": False,
    },
    {
        "id": "clocks",
        "label": "Wall clocks",
        "best": ["N", "E", "NE"],
        "avoid": ["S"],
        "note": "Keep them working and on time; a stopped clock is read as stalled progress.",
        "contested": False,
    },
    {
        "id": "shoes_and_waste",
        "label": "Shoe racks and dustbins",
        "best": ["W", "NW"],
        "avoid": ["NE", "E", "N"],
        "note": "Keep them out of sight of the entrance where you can.",
        "contested": False,
    },
]

# ── Period lines (dasha overlay) ─────────────────────────────────────────────
# Plain templates. `{zone}` is the compass label. Only two classes ever surface;
# a neutral period is suppressed (forecast-surfacing principle: lead strong and
# at-risk, suppress neutral).
PERIOD_TEXT = {
    "strong": {
        "do": ("Use your {zone} area for the decisions, meetings and work that matter most "
               "this stretch. Keep it bright, tidy and open."),
        "avoid": "Don't let it turn into a storage dump or a place for broken things.",
    },
    "needs_care": {
        "do": ("Keep your {zone} area light, tidy and uncluttered this stretch, and let "
               "good light in."),
        "avoid": ("Avoid putting your bed head, your desk or a prayer corner there for now, "
                  "and hold off on heavy storage or renovation in that area."),
    },
}

# Zone class -> plain user-facing label.
CLASS_LABEL = {
    "strong": "Supports you",
    "steady": "Neutral for you",
    "needs_care": "Needs a lighter touch",
}

# Why-lines for the personal directions (plain, no graha names).
DIRECTION_WHY = {
    "strong": "this direction is one of the most supportive for your chart",
    "steady": "your chart has no strong preference here, so the traditional default stands",
    "needs_care": "your chart asks for a lighter touch in this direction, so the other safe option is used",
}

# Content for the "i" info panel — what it is, how it is worked out, what it isn't.
INFO = {
    "title": "About Vastu directions",
    "what_it_is": ("Vastu is the traditional Indian science of how the directions of a "
                   "home line up with the people living in it. Here it is read through "
                   "your birth chart, so the advice is yours, not generic."),
    "what_it_does": ("It shows which of the eight directions support you and which need "
                     "a lighter touch, which way to sleep, work and eat, where common "
                     "household objects sit best, and which area of your home is in "
                     "focus during your current life period."),
    "how_worked_out": ("Each direction is tied to one of the planets in your chart. We "
                       "check how strong or strained that planet is for you, and your "
                       "current life period decides which direction is in focus now."),
    "what_it_isnt": ("This is traditional guidance, not a prediction, and it never asks "
                     "you to rebuild anything. Every suggestion is a small, reversible "
                     "change such as moving a bed, a desk or an object."),
}
