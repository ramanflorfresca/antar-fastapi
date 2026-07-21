"""
antar_engine/venture_context.py
Who is acting, and what kind of venture is it?  (2026-07-21)

Two things the Ask engine could not previously see, both of which change which
houses and significators a business question should actually be read from.

1. AGENCY — "sales" is only the 3rd house when the USER is the one selling.
   A founder whose team or partners sell is asking about the 7th (clients and
   partners) and the 6th (staff and service delivery), not their own outreach.
   Reading a founder's sales question from the 3rd measures the wrong person.

2. NATURE — a software venture runs on Mercury and Rahu; a restaurant runs on
   Venus and Moon; a foundry runs on Mars and Saturn. Same 10th house, entirely
   different significators. Without this every venture was read identically.

Both are DERIVED, never invented: when the question carries no signal the
functions return "unknown"/None and callers keep their existing defaults.
"""

from typing import Dict, List, Optional, Tuple

# ── 1. AGENCY ────────────────────────────────────────────────────────────
_OTHERS_MARKERS = (
    "my team", "our team", "the team", "my staff", "our staff", "employees",
    "my employees", "sales team", "sales guys", "sales people", "salespeople",
    "reps", "my reps", "my partner is", "my partners are", "my cofounder",
    "co-founder", "cofounder", "someone else", "other people are",
    "others are", "they sell", "they are selling", "we sell", "we are selling",
    "my people", "the guys", "agency", "resellers", "distributors",
    "mi equipo", "mis empleados", "mi socio", "ellos venden",
)
_SELF_MARKERS = (
    "i sell", "i am selling", "i'm selling", "i do the selling", "i close",
    "myself", "on my own", "by myself", "solo founder", "i am the only",
    "i'm the only", "just me", "i handle", "i run everything",
    "yo vendo", "yo mismo", "por mi cuenta",
)

# Houses to read a growth/sales question from, by who actually acts.
#   7  = clients, partners, the market (the "other" party)
#   6  = staff, service delivery, day-to-day execution, competitors
#   11 = gains, customers, income realised
#   3  = the user's OWN outreach, marketing, communication effort
_AGENCY_HOUSES = {
    "others": [7, 6, 11],
    "self":   [3, 7, 11],
}


def detect_agency(question: str, career_stage: Optional[str] = None) -> str:
    """"self" | "others" | "unknown" — who is doing the work being asked about.

    Explicit language in the question always wins. `career_stage` is only a
    tiebreaker: someone running their own thing is more likely asking about a
    team than about their personal outreach, but that is a lean, not a fact.
    """
    q = (question or "").lower()
    if not q:
        return "unknown"
    if any(m in q for m in _OTHERS_MARKERS):
        return "others"
    if any(m in q for m in _SELF_MARKERS):
        return "self"
    return "unknown"


def houses_for_agency(agency: str) -> Optional[List[int]]:
    """House set implied by agency, or None to keep the caller's default."""
    return list(_AGENCY_HOUSES[agency]) if agency in _AGENCY_HOUSES else None


# ── 2. VENTURE NATURE ────────────────────────────────────────────────────
# Ordered most-specific first: "fintech" must beat the bare "finance" lean.
_VENTURE_NATURE: Tuple[Tuple[str, Tuple[str, ...], List[str], str], ...] = (
    ("tech", (
        "saas", "software", "app", "platform", "api", "ai ", " ai", "ml ",
        "machine learning", "startup", "tech", "developer", "engineering",
        "product", "code", "data", "cloud", "crypto", "web3", "automation",
        "tecnologia", "tecnología", "aplicacion", "aplicación",
    ), ["Mercury", "Rahu"],
        "software and data ventures run on Mercury (logic, product) with Rahu "
        "(disruption, scale, the unconventional)"),
    ("finance", (
        "fintech", "trading", "investment firm", "hedge", "lending", "insurance",
        "brokerage", "financiera",
    ), ["Jupiter", "Mercury"],
        "financial ventures run on Jupiter (capital, expansion) with Mercury "
        "(calculation, dealing)"),
    ("content", (
        "content", "media", "youtube", "podcast", "creator", "publishing",
        "film", "music", "design studio", "marketing agency", "contenido",
    ), ["Venus", "Mercury"],
        "content and media ventures run on Venus (aesthetics, audience) with "
        "Mercury (communication)"),
    # Food is NOT retail: a restaurant is read from Venus+Moon as nourishment
    # and repeat custom, a shop from Venus+Mercury as desirability and trade.
    # Keeping "restaurant" in the retail markers made them indistinguishable.
    ("retail", (
        "retail", "store", "shop", "ecommerce", "e-commerce", "boutique",
        "tienda", "comercio",
    ), ["Venus", "Mercury"],
        "retail runs on Venus (desirability, what people want) with Mercury "
        "(trade, turnover)"),
    ("manufacturing", (
        "manufactur", "factory", "production", "hardware", "construction",
        "logistics", "supply chain", "fabrica", "fábrica",
    ), ["Mars", "Saturn"],
        "manufacturing and construction run on Mars (machinery, drive) with "
        "Saturn (process, endurance)"),
    ("wholesale", (
        "wholesale", "wholesaler", "distribution", "distributor", "trading house",
        "bulk supply", "b2b supply", "mayorista", "distribuidor",
    ), ["Mercury", "Moon"],
        "wholesale and distribution run on Mercury (trade, margin, turnover) "
        "with Moon (volume, circulation, the public's demand)"),
    ("import_export", (
        "import", "export", "import-export", "cross-border", "customs",
        "shipping", "freight", "overseas trade", "importacion", "exportacion",
    ), ["Mercury", "Rahu"],
        "import-export runs on Mercury (trade) with Rahu (foreign, distance, "
        "the unconventional route) — the 9th and 12th carry it"),
    ("textile", (
        "cloth", "textile", "garment", "apparel", "fabric", "fashion label",
        "clothing", "saree", "tela", "ropa",
    ), ["Venus", "Mercury"],
        "cloth and garments run on Venus (beauty, adornment, desirability) with "
        "Mercury (trade)"),
    ("food", (
        "restaurant", "cafe", "cloud kitchen", "catering", "bakery", "food truck",
        "restaurante", "cafeteria", "panaderia",
    ), ["Venus", "Moon"],
        "food and hospitality run on Venus (taste, pleasure) with Moon "
        "(nourishment, the public, repeat custom)"),
    ("realestate", (
        "real estate", "property development", "builder", "construction firm",
        "brokerage of property", "inmobiliaria",
    ), ["Mars", "Venus"],
        "real estate runs on Mars (land, building) with Venus (value, the deal)"),
    ("education_biz", (
        "school", "edtech", "coaching institute", "training institute", "academy",
        "tutoring", "academia",
    ), ["Jupiter", "Mercury"],
        "education ventures run on Jupiter (teaching, authority) with Mercury "
        "(curriculum, communication)"),
    ("services", (
        "consulting", "consultancy", "agency", "services", "freelance",
        "coaching", "training", "recruit", "servicios", "consultoria",
    ), ["Mercury", "Jupiter"],
        "service ventures run on Mercury (skill, dealing) with Jupiter "
        "(counsel, reputation)"),
    ("health", (
        "clinic", "healthcare", "medical", "wellness", "pharma", "hospital",
        "salud", "clinica", "clínica",
    ), ["Sun", "Mars"],
        "health ventures run on Sun (vitality, authority) with Mars "
        "(intervention, surgery)"),
)


def detect_venture_nature(question: str, context: str = "") -> Optional[Dict]:
    """{"nature", "karakas", "why"} or None when the text says nothing.

    None is meaningful: it means "keep the generic business significators"
    rather than guessing a sector the user never mentioned.
    """
    blob = f"{question or ''} {context or ''}".lower()
    if not blob.strip():
        return None
    for nature, markers, karakas, why in _VENTURE_NATURE:
        if any(m in blob for m in markers):
            return {"nature": nature, "karakas": list(karakas), "why": why}
    return None


def venture_context_block(question: str, career_stage: Optional[str] = None,
                          context: str = "", ventures=None,
                          profession: str = "") -> Dict:
    """Everything this module can infer, for the reading context.

    `ventures` and `profession` come from the chart record. They are consulted
    because the question often does not name the sector — someone asks "growth
    is slow", not "my wholesale cloth business is slow" — while the profile may
    already say it. This is the difference between reading "a business" and
    reading THIS business: cloth is Venus, trade is Mercury, import-export pulls
    in Rahu and the 9th/12th. Same 10th house, different verdict.
    """
    extra = " ".join([
        context or "",
        " ".join(ventures) if isinstance(ventures, (list, tuple)) else str(ventures or ""),
        profession or "",
    ]).strip()
    agency = detect_agency(question, career_stage)
    nature = detect_venture_nature(question, extra)
    return {
        "agency": agency,
        "agency_houses": houses_for_agency(agency),
        "nature": (nature or {}).get("nature"),
        "nature_karakas": (nature or {}).get("karakas"),
        "nature_why": (nature or {}).get("why"),
    }
