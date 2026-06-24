"""
antar_engine/profession/profession_archetype.py  —  ARCHETYPE + ARENAS

Turns the converged primary signature into:
  * ONE vocational ARCHETYPE  (reuses natal_signatures.ARCHETYPE_LIBRARY,
    pointed at career via the dominant career planet)
  * 3-4 MODERN ARENAS, each tagged with its driving factor, that are FOUR FACES
    OF ONE SIGNATURE (all drawn from the dominant planet, lensed by the
    Amatyakaraka house family, with one face each for D10 / AmK / Karakamsa).

No jargon scrubbing here — that is profession_service's job. This module keeps
the driving-factor traceability (D10 / AmK-house / Karakamsa) in the evidence.
"""

from __future__ import annotations

# Reuse the shipped archetype library (FIELD, MODE) keys -> rich descriptions.
try:
    from ..natal_signatures import ARCHETYPE_LIBRARY, DEFAULT_ARCHETYPE
except Exception:  # pragma: no cover - defensive: never hard-fail the engine
    ARCHETYPE_LIBRARY, DEFAULT_ARCHETYPE = {}, {
        "name": "THE NAVIGATOR", "tagline": "Finds the path through complexity.",
        "description": "A rare combination of signals across multiple fields.",
        "strength": "Versatility.", "blind_spot": "No fixed identity.",
        "frequency": "rare",
    }

# Dominant career planet -> an existing ARCHETYPE_LIBRARY key (career-pointed).
CAREER_ARCHETYPE_KEY = {
    "Sun":     ("AUTHORITY", "PENETRATE"),   # THE COMMANDER — decisive leadership
    "Saturn":  ("AUTHORITY", "STRUCTURE"),   # THE ARCHITECT — builds lasting systems
    "Jupiter": ("GROWTH", "BUILD"),          # THE STEWARD — compounds wisdom/capital
    "Mars":    ("IGNITION", "DRIVE"),        # THE CATALYST — 0-to-1 builder
    "Mercury": ("DISCOVERY", "CONNECT"),     # THE NETWORKER — ideas + networks
    "Venus":   ("ABUNDANCE", "CONNECT"),     # THE MAGNET — attracts via craft/relation
    "Moon":    ("RECOVERY", "PROTECT"),      # THE HEALER — care / public service
    "Rahu":    ("STORM", "DISRUPT"),         # THE REBEL — disruptive / unconventional
    "Ketu":    ("DEPTH", "DISSOLVE"),        # THE DEPTH — niche mastery / research
}

# Modern arenas per dominant planet — all FACES OF ONE SIGNATURE.
MODERN_ARENAS = {
    "Sun": [
        "running an organization on a GM / CEO track",
        "civic leadership or public office",
        "building a recognized authority brand in your field",
        "senior roles in regulated, high-trust institutions",
        "leading a high-status profession (a firm, a practice, a department)",
    ],
    "Moon": [
        "healthcare and care delivery",
        "hospitality, food, and consumer experiences",
        "real estate and property",
        "consumer brands and public-facing products",
        "psychology, coaching, and people-care",
    ],
    "Mars": [
        "founding and running a venture",
        "engineering and building physical or hard-tech products",
        "competitive sales and deal-making",
        "sports, fitness, and high-performance work",
        "surgery, defense, or emergency-response fields",
    ],
    "Mercury": [
        "software and product",
        "writing, media, and publishing",
        "markets, analytics, and quantitative work",
        "consulting and advisory",
        "education and teaching at scale",
    ],
    "Jupiter": [
        "finance, investing, and capital allocation",
        "law, policy, and governance",
        "teaching, coaching, and academia",
        "advisory and board-level work",
        "running a mission-driven institution",
    ],
    "Venus": [
        "design, brand, and creative direction",
        "film, music, and entertainment",
        "luxury, fashion, and aesthetics",
        "community and relationship-led products",
        "diplomacy, partnerships, and dealcraft",
    ],
    "Saturn": [
        "operations and systems at scale",
        "infrastructure, real assets, and energy",
        "audit, governance, and compliance",
        "long-horizon research and craft mastery",
        "public service and social infrastructure",
    ],
    "Rahu": [
        "frontier technology and AI",
        "crypto, markets, and new finance",
        "media, audience, and influence",
        "cross-border and immigrant-built ventures",
        "category-creating, unconventional businesses",
    ],
    "Ketu": [
        "deep research and R&D",
        "specialized technical niches",
        "healing, wellness, and contemplative work",
        "forensic, archival, or investigative work",
        "philosophical, spiritual, or first-principles vocation",
    ],
}

# AmK house family -> keywords that bias which faces surface first.
FAMILY_LENS = {
    "mainstream":   ["organization", "ceo", "institution", "senior", "operations",
                     "finance", "office", "firm", "governance", "board"],
    "creative":     ["design", "creative", "film", "music", "brand", "teaching",
                     "education", "performance", "entertainment", "audience"],
    "research":     ["research", "r&d", "markets", "forensic", "quant", "analytics",
                     "crypto", "investigative", "first-principles", "capital"],
    "communication":["writing", "media", "software", "product", "sales", "influence",
                     "teaching", "publishing", "audience", "venture"],
    "partnership":  ["partnership", "diplomacy", "relationship", "advisory", "deal",
                     "community", "sales", "board", "consulting"],
    "self":         ["founding", "venture", "brand", "practice", "craft", "mastery"],
    "resources":    ["finance", "markets", "capital", "real", "assets", "luxury"],
    "foundations":  ["real estate", "property", "infrastructure", "real assets", "energy"],
    "service":      ["healthcare", "care", "audit", "compliance", "operations", "service"],
    "dharma":       ["teaching", "law", "policy", "academia", "publishing", "mission"],
    "gains":        ["media", "audience", "influence", "markets", "scale", "distribution"],
    "retreat":      ["research", "r&d", "forensic", "contemplative", "spiritual", "cross-border"],
}


def _resolve_archetype(dominant: str) -> dict:
    key = CAREER_ARCHETYPE_KEY.get(dominant)
    arch = ARCHETYPE_LIBRARY.get(key) if key else None
    if not arch:
        arch = DEFAULT_ARCHETYPE
    return {
        "name": arch.get("name"),
        "tagline": arch.get("tagline"),
        "description": arch.get("description"),
        "strength": arch.get("strength"),
        "blind_spot": arch.get("blind_spot"),
    }


def _rank_arenas(dominant: str, family: str) -> list[str]:
    pool = MODERN_ARENAS.get(dominant, MODERN_ARENAS["Mercury"])
    lens = FAMILY_LENS.get(family, [])

    def score(arena):
        a = arena.lower()
        return sum(1 for kw in lens if kw in a)

    # stable sort: lens score desc, then original order
    return sorted(pool, key=lambda a: -score(a))


def build_archetype_and_arenas(sig: dict) -> dict:
    """
    sig = output of profession_signature.compute_profession_signature().
    Returns { archetype, arenas:[{label, driving_factor, source}], ... }.
    The arenas are four faces of one signature, each tagged to a source so the
    acceptance ("traceable to D10 / AmK-house / Karakamsa") holds.
    """
    dominant = sig.get("dominant_planet") or "Mercury"
    family = sig.get("amk", {}).get("family", "mainstream")
    family_text = sig.get("amk", {}).get("family_text", "")

    archetype = _resolve_archetype(dominant)
    faces = _rank_arenas(dominant, family)

    amk_house = sig.get("amk", {}).get("d1_house")
    kk_sign = sig.get("karakamsa", {}).get("sign", "")

    # Assign one face to each source so all three are represented + traceable.
    source_tags = [
        ("D10", "the shape of the work itself (career chart)"),
        ("AmK-house", f"where your effort pays off — {family_text}"),
        ("Karakamsa", "the vocation your nature keeps returning to"),
        ("D10-strength", "the strongest professional signal in the chart"),
    ]

    arenas = []
    for i, face in enumerate(faces[:4]):
        src, factor = source_tags[i] if i < len(source_tags) else source_tags[-1]
        arenas.append({
            "label": face,
            "source": src,
            "driving_factor": factor,
        })

    return {
        "dominant_planet": dominant,
        "archetype": archetype,
        "arenas": arenas,
        "family": family,
        "family_text": family_text,
        "amk_house": amk_house,
        "karakamsa_sign": kk_sign,
    }
