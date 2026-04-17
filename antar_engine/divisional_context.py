"""
antar_engine/divisional_context.py

Extract D9 (Navamsha) and D10 (Dashamsha) divisional chart context
for injection into the predict endpoint and upcoming-themes confidence
adjustment.

Handles both d9/D9 case variants.
"""

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
STRONG_VENUS_SIGNS = {"Taurus", "Libra", "Pisces", "Cancer"}
WEAK_VENUS_SIGNS = {"Virgo", "Aries", "Scorpio"}
STRONG_SUN_SIGNS = {"Aries", "Leo", "Sagittarius"}


def extract_d9_context(chart_data: dict) -> dict:
    """Extract D9 Navamsha context for relationship/soul analysis."""
    div = chart_data.get("divisional_charts", {})
    d9 = div.get("d9") or div.get("D9") or {}
    if not d9:
        return {}

    planets = d9.get("planets", {})
    lagna_raw = d9.get("lagna", "")
    lagna_sign = lagna_raw.get("sign", lagna_raw) if isinstance(lagna_raw, dict) else str(lagna_raw)

    venus = planets.get("Venus", {})
    venus_sign = venus.get("sign", "")
    moon = planets.get("Moon", {})
    jupiter = planets.get("Jupiter", {})

    # Relationship strength assessment
    if venus_sign in STRONG_VENUS_SIGNS:
        rel_strength = "strong"
    elif venus_sign in WEAK_VENUS_SIGNS:
        rel_strength = "difficult"
    else:
        rel_strength = "moderate"

    # 7th lord analysis
    seventh_lord = ""
    house_lords = d9.get("house_lords", {})
    if isinstance(house_lords, dict):
        h7 = house_lords.get(7, house_lords.get("7", {}))
        if isinstance(h7, dict):
            seventh_lord = h7.get("lord", "")
        elif isinstance(h7, str):
            seventh_lord = h7

    return {
        "available": True,
        "lagna": lagna_sign,
        "planets": {p: v.get("sign", "") for p, v in planets.items()},
        "venus": venus_sign,
        "venus_house": venus.get("house", ""),
        "moon": moon.get("sign", ""),
        "jupiter": jupiter.get("sign", ""),
        "7th_lord": seventh_lord,
        "relationship_strength": rel_strength,
    }


def extract_d10_context(chart_data: dict) -> dict:
    """Extract D10 Dashamsha context for career analysis."""
    div = chart_data.get("divisional_charts", {})
    d10 = div.get("d10") or div.get("D10") or {}
    if not d10:
        return {}

    planets = d10.get("planets", {})
    lagna_raw = d10.get("lagna", "")
    lagna_sign = lagna_raw.get("sign", lagna_raw) if isinstance(lagna_raw, dict) else str(lagna_raw)

    sun = planets.get("Sun", {})
    sun_sign = sun.get("sign", "")
    jupiter = planets.get("Jupiter", {})
    saturn = planets.get("Saturn", {})

    # Career strength assessment
    sun_strong = sun_sign in STRONG_SUN_SIGNS
    jup_in_kendra = jupiter.get("house", 0) in (1, 4, 7, 10)
    if sun_strong and jup_in_kendra:
        career_strength = "strong"
    elif sun_sign in WEAK_VENUS_SIGNS or saturn.get("house", 0) in (6, 8, 12):
        career_strength = "needs_effort"
    else:
        career_strength = "moderate"

    # 10th lord analysis
    tenth_lord = ""
    house_lords = d10.get("house_lords", {})
    if isinstance(house_lords, dict):
        h10 = house_lords.get(10, house_lords.get("10", {}))
        if isinstance(h10, dict):
            tenth_lord = h10.get("lord", "")
        elif isinstance(h10, str):
            tenth_lord = h10

    return {
        "available": True,
        "lagna": lagna_sign,
        "planets": {p: v.get("sign", "") for p, v in planets.items()},
        "sun": sun_sign,
        "sun_house": sun.get("house", ""),
        "jupiter_house": jupiter.get("house", ""),
        "saturn_house": saturn.get("house", ""),
        "10th_lord": tenth_lord,
        "career_strength": career_strength,
    }


def format_d9_for_prompt(d9_ctx: dict) -> str:
    """Format D9 context as a prompt block for the LLM."""
    if not d9_ctx or not d9_ctx.get("available"):
        return ""

    lines = ["D9 NAVAMSHA (Soul & Relationship Chart):"]
    lines.append(f"  Lagna: {d9_ctx.get('lagna', '?')}")
    lines.append(f"  Venus: {d9_ctx.get('venus', '?')} (house {d9_ctx.get('venus_house', '?')}) — relationship indicator")
    lines.append(f"  Moon: {d9_ctx.get('moon', '?')} — emotional fulfillment")
    lines.append(f"  Jupiter: {d9_ctx.get('jupiter', '?')} — wisdom & dharma")

    rel = d9_ctx.get("relationship_strength", "moderate")
    if rel == "strong":
        lines.append("  Relationship signal: STRONG — Venus well-placed for partnerships")
    elif rel == "difficult":
        lines.append("  Relationship signal: CHALLENGED — Venus needs conscious effort in partnerships")
    else:
        lines.append("  Relationship signal: MODERATE — standard relationship dynamics")

    seventh = d9_ctx.get("7th_lord", "")
    if seventh:
        lines.append(f"  7th lord: {seventh}")

    return "\n".join(lines)


def format_d10_for_prompt(d10_ctx: dict) -> str:
    """Format D10 context as a prompt block for the LLM."""
    if not d10_ctx or not d10_ctx.get("available"):
        return ""

    lines = ["D10 DASHAMSHA (Career & Professional Chart):"]
    lines.append(f"  Lagna: {d10_ctx.get('lagna', '?')}")
    lines.append(f"  Sun: {d10_ctx.get('sun', '?')} (house {d10_ctx.get('sun_house', '?')}) — authority & leadership")
    lines.append(f"  Jupiter: house {d10_ctx.get('jupiter_house', '?')} — expansion in career")
    lines.append(f"  Saturn: house {d10_ctx.get('saturn_house', '?')} — discipline & longevity")

    career = d10_ctx.get("career_strength", "moderate")
    if career == "strong":
        lines.append("  Career signal: STRONG — Sun and Jupiter support professional authority")
    elif career == "needs_effort":
        lines.append("  Career signal: NEEDS EFFORT — career growth requires extra push and discipline")
    else:
        lines.append("  Career signal: MODERATE — steady career trajectory")

    tenth = d10_ctx.get("10th_lord", "")
    if tenth:
        lines.append(f"  10th lord: {tenth}")

    return "\n".join(lines)
