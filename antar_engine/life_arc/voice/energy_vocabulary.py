"""
Energy Vocabulary — v5.1 Voice & Wording Framework
====================================================
Planet → Energy-systems translation table.

Every planet gets a primary energy name and felt-sense descriptors
so users can self-verify the reading against their own experience.

FROM: Planet-deity language (Vedic astrology register)
TO:   Energy-systems language (body-intuitive register)

Author: Antar Engine · April 2026
"""

from typing import Dict, Optional


PLANET_ENERGY_VOCABULARY: Dict[str, Dict[str, str]] = {
    "Sun": {
        "energy_name": "identity and authority energy",
        "alt_names": "vitality flow, inner-authority current, visibility energy",
        "chakra": "Manipura (solar plexus)",
        "felt_when_strong": (
            "confident in own authority, comfortable being seen, "
            "natural sense of direction"
        ),
        "felt_when_weak": (
            "doubt about your own judgment, shrinking from visibility, "
            "confusion about 'who's in charge' of your life"
        ),
        "life_domain": (
            "leadership, confidence, father-figure relationships, "
            "career-visibility, self-worth"
        ),
    },
    "Moon": {
        "energy_name": "emotional and responsive energy",
        "alt_names": "sensitivity current, receptive flow, inner-mirror energy",
        "chakra": "Ajna (third eye) / Sahasrara (crown)",
        "felt_when_strong": (
            "emotionally steady, intuition clear, comfortable with own feelings, "
            "nurturing capacity available"
        ),
        "felt_when_weak": (
            "emotional reactivity, mood swings, mother-relationship tension, "
            "difficulty self-soothing, over-sensitivity or emotional numbness"
        ),
        "life_domain": (
            "feelings, mother, home, public-facing reputation, "
            "emotional intelligence, comfort-seeking"
        ),
    },
    "Mars": {
        "energy_name": "action and drive energy",
        "alt_names": "execution current, forward-push flow, warrior energy",
        "chakra": "Muladhara (root)",
        "felt_when_strong": (
            "clear willingness to act, confrontation doesn't scare you, "
            "execution happens, healthy boundaries"
        ),
        "felt_when_weak": (
            "procrastination, conflict-avoidance, feeling blocked from starting, "
            "anger buried or exploding, inflammation/blood issues"
        ),
        "life_domain": (
            "physical action, courage, conflict, brothers, "
            "operational work, competition, stamina"
        ),
    },
    "Mercury": {
        "energy_name": "communication and clarity energy",
        "alt_names": "connection flow, articulation current, bridge-making energy",
        "chakra": "Vishuddha (throat)",
        "felt_when_strong": (
            "clear thinking, words arrive easily, deal-making flows, "
            "understanding others quickly, writing unlocks"
        ),
        "felt_when_weak": (
            "mental fog, miscommunications repeating, contracts going sideways, "
            "writer's block, networking feels forced"
        ),
        "life_domain": (
            "communication, business dealings, writing, "
            "short-range networks, siblings, analytical thinking"
        ),
    },
    "Jupiter": {
        "energy_name": "growth and wisdom energy",
        "alt_names": "expansion current, teacher flow, higher-knowing energy",
        "chakra": "Sahasrara (crown) / Ajna",
        "felt_when_strong": (
            "ideas expanding, mentors appearing, natural teacher-student relationships, "
            "optimism-with-feet-on-ground, wise counsel available"
        ),
        "felt_when_weak": (
            "ideas feeling dry, mentors unavailable, advice not landing, "
            "expansion blocked, belief system wobbly, dharma unclear"
        ),
        "life_domain": (
            "wisdom, teaching, children, philosophy, "
            "long-range expansion, mentor/mentee relationships, dharma"
        ),
    },
    "Venus": {
        "energy_name": "beauty and harmony energy",
        "alt_names": "attraction flow, relational current, pleasure-allowing energy",
        "chakra": "Anahata (heart)",
        "felt_when_strong": (
            "relationships flow, aesthetic sense alive, pleasure without guilt, "
            "refinement available, partnership magnetism"
        ),
        "felt_when_weak": (
            "relationship friction, material comfort blocked, beauty-appreciation dimmed, "
            "over-indulgence or deprivation pattern, creativity stagnant"
        ),
        "life_domain": (
            "relationships, marriage, pleasure, luxury, aesthetics, "
            "partnership-wealth, creative harmony"
        ),
    },
    "Saturn": {
        "energy_name": "structure and persistence energy",
        "alt_names": "discipline current, foundation flow, long-horizon energy",
        "chakra": "Muladhara (root) / Manipura",
        "felt_when_strong": (
            "able to commit to the long haul, realistic about what matters, "
            "structure built naturally, boundaries hold, patience available"
        ),
        "felt_when_weak": (
            "obstacles recurring, delays multiplying, feeling like "
            "'the universe is against me', joint/knee issues, "
            "chronic exhaustion, fatherly-authority conflicts"
        ),
        "life_domain": (
            "time, discipline, persistence, institutions, "
            "elder-figure relationships, long-term building, service to masses"
        ),
    },
    "Rahu": {
        "energy_name": "desire and amplification energy",
        "alt_names": "hunger current, ambition flow, boundary-breaking energy",
        "chakra": "Manipura (when healthy) / throat-mind (when distorted)",
        "felt_when_strong": (
            "unconventional ambition channeled well, willingness to do what "
            "others won't, foreign/cross-cultural flow, disruption-clarity"
        ),
        "felt_when_weak": (
            "scattered obsession, addictions (substance, relationship, work), "
            "sudden losses, chasing-mirages pattern, "
            "confusion about 'what I actually want'"
        ),
        "life_domain": (
            "unconventional paths, foreign ventures, digital/modern work, "
            "disruption, amplification of desire, ancestry shadow patterns"
        ),
    },
    "Ketu": {
        "energy_name": "release and dissolution energy",
        "alt_names": "liberation current, letting-go flow, spiritual-distillation energy",
        "chakra": "Sahasrara (crown) / Ajna",
        "felt_when_strong": (
            "ability to let go of what's done, spiritual insight, "
            "detachment from unnecessary, past-life skill accessible"
        ),
        "felt_when_weak": (
            "feeling detached when you should be present, "
            "sudden unexpected endings, isolation pattern, "
            "feeling 'nothing matters' during important moments"
        ),
        "life_domain": (
            "spirituality, detachment, past-life patterns, "
            "sudden endings, unconventional knowledge, inheritance issues"
        ),
    },
}


def get_energy_name(planet: str) -> str:
    """Get the energy-systems name for a planet."""
    vocab = PLANET_ENERGY_VOCABULARY.get(planet, {})
    return vocab.get("energy_name", f"{planet} energy")


def get_felt_sense(planet: str, is_strong: bool = True) -> str:
    """Get the felt-sense description for a planet's state."""
    vocab = PLANET_ENERGY_VOCABULARY.get(planet, {})
    key = "felt_when_strong" if is_strong else "felt_when_weak"
    return vocab.get(key, "")


def get_chakra(planet: str) -> str:
    """Get the chakra anchor for a planet."""
    vocab = PLANET_ENERGY_VOCABULARY.get(planet, {})
    return vocab.get("chakra", "")


# ─── Life-noun layer (energy-voice retirement, Cowork 2026-06-10) ───────────
# Doctrine: energy_name is retired from PREDICTION surfaces (Current Cycle,
# Today, Ask) and stays in Practice only. Prediction narration uses concrete
# life-nouns sourced from life_domain. These helpers are the single resolver.

# Short period labels for display scalars and prompt facts — life-nouns only,
# no "energy" wording, frontend-template safe ("filtered through <label>").
CYCLE_PERIOD_LIFE_LABELS: Dict[str, str] = {
    "Sun":     "leadership and visibility",
    "Moon":    "home and emotional life",
    "Mars":    "action and competition",
    "Mercury": "communication and business",
    "Jupiter": "wisdom and mentorship",
    "Venus":   "relationships and creative harmony",
    "Saturn":  "discipline and long-term building",
    "Rahu":    "ambition and unconventional paths",
    "Ketu":    "release and inner work",
}

# Tokens inside life_domain strings that must never reach a prompt or user.
_LIFE_NOUN_BANNED = ("dharma",)


def get_life_nouns(planet: str, n: int = 3) -> list:
    """First n concrete life-nouns from the planet's life_domain.
    Sanskrit tokens filtered. Returns [] for unknown planets."""
    vocab = PLANET_ENERGY_VOCABULARY.get(planet, {})
    domain = vocab.get("life_domain", "")
    nouns = []
    for part in domain.split(","):
        p = part.strip()
        if not p:
            continue
        if any(b in p.lower() for b in _LIFE_NOUN_BANNED):
            continue
        nouns.append(p)
        if len(nouns) >= n:
            break
    return nouns


def get_life_phrase(planet: str, default: str = "this period's focus") -> str:
    """Short life-noun label for a period lord — the prediction-surface
    replacement for get_energy_name(). Returns `default` when the planet
    is unknown (pass default="" to detect misses)."""
    if not planet:
        return default
    label = CYCLE_PERIOD_LIFE_LABELS.get(planet)
    if label:
        return label
    nouns = get_life_nouns(planet, 2)
    if nouns:
        return " and ".join(nouns)
    return default
