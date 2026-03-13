"""
antar_engine/desh.py

DESH — Country Chart & Condition Engine
────────────────────────────────────────────────────────────────────
Desh = Place / Country / Environment

Three layers:
  1. Country natal chart (fixed — the country's birth chart)
  2. Country current dasha (calculated from country's birth)
  3. Country current condition (transit analysis for the country)
  + 1-2 liner for display in the app

Also contains:
  4. Desh-Patra intersection (how country energy meets personal energy)
  5. Astrocartography scaffold (Phase 2)

Country birth dates used:
  Most use Independence Day as the natal chart.
  Some use constitution date where more appropriate.
  All use midnight 00:00 local time unless noted.

Usage:
    from antar_engine.desh import get_desh_context, get_country_oneliner

    desh = get_desh_context("IN", supabase, current_transits)
    # desh.current_period = "Mars Mahadasha"
    # desh.period_quality = "Action & Growth Period"
    # desh.one_liner = "India is in a bold infrastructure push — entrepreneurial energy is high."
    # desh.full_insight = "..."
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from supabase import Client


# ── Country birth data ────────────────────────────────────────────────────────
# (date, time, lat, lng, timezone_offset, notes)

COUNTRY_BIRTH_DATA = {
    # ── South Asia ──
    "IN": {
        "name":     "India",
        "date":     "1947-08-15",
        "time":     "00:00",
        "lat":      28.6139,
        "lng":      77.2090,
        "tz":       5.5,
        "notes":    "Independence at midnight, New Delhi",
    },
    "PK": {
        "name":     "Pakistan",
        "date":     "1947-08-14",
        "time":     "00:00",
        "lat":      33.7294,
        "lng":      73.0931,
        "tz":       5.0,
        "notes":    "Independence, Islamabad",
    },
    "BD": {
        "name":     "Bangladesh",
        "date":     "1971-03-26",
        "time":     "00:00",
        "lat":      23.8103,
        "lng":      90.4125,
        "tz":       6.0,
        "notes":    "Declaration of independence, Dhaka",
    },
    "LK": {
        "name":     "Sri Lanka",
        "date":     "1948-02-04",
        "time":     "00:00",
        "lat":      6.9271,
        "lng":      79.8612,
        "tz":       5.5,
        "notes":    "Independence, Colombo",
    },

    # ── Latin America ──
    "MX": {
        "name":     "Mexico",
        "date":     "1810-09-16",
        "time":     "00:00",
        "lat":      19.4326,
        "lng":      -99.1332,
        "tz":       -6.0,
        "notes":    "Cry of Dolores, Mexico City",
    },
    "CO": {
        "name":     "Colombia",
        "date":     "1810-07-20",
        "time":     "00:00",
        "lat":      4.7110,
        "lng":      -74.0721,
        "tz":       -5.0,
        "notes":    "Declaration, Bogotá",
    },
    "AR": {
        "name":     "Argentina",
        "date":     "1816-07-09",
        "time":     "00:00",
        "lat":      -34.6037,
        "lng":      -58.3816,
        "tz":       -3.0,
        "notes":    "Independence, Buenos Aires",
    },
    "BR": {
        "name":     "Brazil",
        "date":     "1822-09-07",
        "time":     "00:00",
        "lat":      -15.7801,
        "lng":      -47.9292,
        "tz":       -3.0,
        "notes":    "Independence cry, Brasília",
    },
    "CL": {
        "name":     "Chile",
        "date":     "1818-02-12",
        "time":     "00:00",
        "lat":      -33.4489,
        "lng":      -70.6693,
        "tz":       -4.0,
        "notes":    "Independence, Santiago",
    },
    "PE": {
        "name":     "Peru",
        "date":     "1821-07-28",
        "time":     "00:00",
        "lat":      -12.0464,
        "lng":      -77.0428,
        "tz":       -5.0,
        "notes":    "Independence, Lima",
    },
    "VE": {
        "name":     "Venezuela",
        "date":     "1811-07-05",
        "time":     "00:00",
        "lat":      10.4806,
        "lng":      -66.9036,
        "tz":       -4.5,
        "notes":    "Independence, Caracas",
    },

    # ── USA & Canada ──
    "US": {
        "name":     "United States",
        "date":     "1776-07-04",
        "time":     "17:10",   # Sibley chart — most widely used
        "lat":      39.9526,
        "lng":      -75.1652,
        "tz":       -5.0,
        "notes":    "Sibley chart, Philadelphia",
    },
    "CA": {
        "name":     "Canada",
        "date":     "1867-07-01",
        "time":     "00:00",
        "lat":      45.4215,
        "lng":      -75.6972,
        "tz":       -5.0,
        "notes":    "Confederation, Ottawa",
    },

    # ── Europe ──
    "GB": {
        "name":     "United Kingdom",
        "date":     "1801-01-01",
        "time":     "00:00",
        "lat":      51.5074,
        "lng":      -0.1278,
        "tz":       0.0,
        "notes":    "Acts of Union, London",
    },
    "DE": {
        "name":     "Germany",
        "date":     "1990-10-03",
        "time":     "00:00",
        "lat":      52.5200,
        "lng":      13.4050,
        "tz":       1.0,
        "notes":    "Reunification, Berlin",
    },
    "FR": {
        "name":     "France",
        "date":     "1958-10-04",
        "time":     "00:00",
        "lat":      48.8566,
        "lng":      2.3522,
        "tz":       1.0,
        "notes":    "Fifth Republic, Paris",
    },

    # ── Middle East ──
    "AE": {
        "name":     "UAE",
        "date":     "1971-12-02",
        "time":     "00:00",
        "lat":      24.4539,
        "lng":      54.3773,
        "tz":       4.0,
        "notes":    "Federation, Abu Dhabi",
    },
    "SA": {
        "name":     "Saudi Arabia",
        "date":     "1932-09-23",
        "time":     "00:00",
        "lat":      24.7136,
        "lng":      46.6753,
        "tz":       3.0,
        "notes":    "Unification, Riyadh",
    },

    # ── East Asia ──
    "CN": {
        "name":     "China",
        "date":     "1949-10-01",
        "time":     "15:00",   # Proclamation time
        "lat":      39.9042,
        "lng":      116.4074,
        "tz":       8.0,
        "notes":    "PRC proclamation, Beijing",
    },
    "JP": {
        "name":     "Japan",
        "date":     "1947-05-03",
        "time":     "00:00",
        "lat":      35.6762,
        "lng":      139.6503,
        "tz":       9.0,
        "notes":    "Modern constitution, Tokyo",
    },
    "SG": {
        "name":     "Singapore",
        "date":     "1965-08-09",
        "time":     "10:00",
        "lat":      1.3521,
        "lng":      103.8198,
        "tz":       8.0,
        "notes":    "Independence",
    },

    # ── Africa ──
    "ZA": {
        "name":     "South Africa",
        "date":     "1994-04-27",
        "time":     "00:00",
        "lat":      -25.7479,
        "lng":      28.2293,
        "tz":       2.0,
        "notes":    "First democratic elections, Pretoria",
    },
    "NG": {
        "name":     "Nigeria",
        "date":     "1960-10-01",
        "time":     "00:00",
        "lat":      9.0765,
        "lng":      7.3986,
        "tz":       1.0,
        "notes":    "Independence, Abuja",
    },
}


# ── Country period quality descriptions ──────────────────────────────────────
# What each dasha means at a NATIONAL level
# (different from personal dasha meanings)

COUNTRY_DASHA_THEMES = {
    "Sun":     {
        "quality":     "National Identity & Leadership Period",
        "energy":      "Strong centralized leadership. National pride peaks. "
                       "Government authority consolidates. International visibility rises.",
        "economy":     "Government-led economic activity. Infrastructure projects. "
                       "State-owned enterprises favored.",
        "society":     "Nationalism rises. Unity narratives dominant. "
                       "Leaders become symbols.",
        "caution":     "Authoritarianism risk. Individual freedoms may be tested.",
    },
    "Moon":    {
        "quality":     "Social Welfare & People's Period",
        "energy":      "Masses become politically active. Social movements rise. "
                       "Agriculture and food security in focus.",
        "economy":     "Consumer economy active. Real estate and housing demand rises. "
                       "Agriculture sector important.",
        "society":     "Women's issues and maternal welfare highlighted. "
                       "Immigration and migration themes prominent.",
        "caution":     "Emotional volatility in public sentiment. "
                       "Flooding and water-related events possible.",
    },
    "Mars":    {
        "quality":     "Action & Infrastructure Period",
        "energy":      "Bold government action. Infrastructure push. Military activity. "
                       "Decisive leadership. Entrepreneurial spirit rises.",
        "economy":     "Manufacturing, construction, real estate boom. "
                       "Energy sector active. Defense spending rises.",
        "society":     "Competitive national spirit. Sports achievements notable. "
                       "Conflict and disputes may arise.",
        "caution":     "Military conflicts, border tensions, industrial accidents.",
    },
    "Mercury": {
        "quality":     "Commerce & Technology Period",
        "energy":      "Trade and commerce flourish. Technology sector booms. "
                       "Education and media prominent. Diplomatic activity peaks.",
        "economy":     "IT, telecommunications, financial services, trade all active. "
                       "Export-oriented growth. Startups thrive.",
        "society":     "Media and journalism prominent. Literacy and education focus. "
                       "Youth culture influential.",
        "caution":     "Information overload. Misinformation and scams rise. "
                       "Trade disputes possible.",
    },
    "Jupiter": {
        "quality":     "Expansion & Prosperity Period",
        "energy":      "Overall national growth and optimism. Foreign investment rises. "
                       "Education and wisdom institutions flourish. "
                       "Religious and cultural renaissance.",
        "economy":     "GDP growth. Financial sector expansion. Higher education investment. "
                       "Tourism and pilgrimage boom.",
        "society":     "Optimism and faith in institutions. Legal reforms. "
                       "International prestige rises.",
        "caution":     "Over-expansion. Debt accumulation. Religious tensions possible.",
    },
    "Venus":   {
        "quality":     "Culture & Prosperity Period",
        "energy":      "Arts, culture, entertainment flourish. Luxury consumption rises. "
                       "Diplomatic relations improve. Tourism peaks.",
        "economy":     "Consumer goods, luxury, entertainment, hospitality boom. "
                       "Foreign exchange from tourism. Trade agreements improve.",
        "society":     "Cultural output at peak. Film, music, arts prominent. "
                       "Gender equality movements rise.",
        "caution":     "Complacency. Overindulgence in luxury. "
                       "Superficiality in governance.",
    },
    "Saturn":  {
        "quality":     "Discipline & Restructuring Period",
        "energy":      "Hard work and discipline define the era. Structural reforms. "
                       "Long-term institution building. Reality checks on debt and excess.",
        "economy":     "Austerity possible. Infrastructure (slow) built. "
                       "Agricultural and labor sectors prominent.",
        "society":     "Working class issues prominent. Labor movements. "
                       "Inequality becomes impossible to ignore.",
        "caution":     "Economic hardship. Strict governance. "
                       "Natural disasters, droughts.",
    },
    "Rahu":    {
        "quality":     "Transformation & Foreign Influence Period",
        "energy":      "Rapid, disruptive change. Foreign influence peaks. "
                       "Technology leaps. Unconventional leadership rises. "
                       "National identity questioned.",
        "economy":     "Foreign investment and foreign companies dominant. "
                       "Tech disruption. Cryptocurrency and new finance possible.",
        "society":     "Cultural identity confusion. Social media dominant. "
                       "Immigration surges. Unconventional social movements.",
        "caution":     "Political instability. Corruption exposure. "
                       "Identity crises. Epidemic potential.",
    },
    "Ketu":    {
        "quality":     "Spiritual & Karmic Resolution Period",
        "energy":      "Nation confronts its karma. Spiritual and religious renaissance. "
                       "Past unresolved issues surface. Simplification and return to roots.",
        "economy":     "Economic uncertainty. Traditional sectors revive. "
                       "Foreign investment retreats.",
        "society":     "Spiritual revival. Traditional values reassert. "
                       "Dissatisfaction with materialism.",
        "caution":     "Epidemics, mysterious events, loss of territory. "
                       "Leadership confusion.",
    },
}


# ── Desh context data class ───────────────────────────────────────────────────

@dataclass
class DeshContext:
    """Complete country context for the prediction engine."""

    country_code: str
    country_name: str

    # Current period data
    current_period: str          # e.g. "Mars Mahadasha"
    period_quality: str          # e.g. "Action & Infrastructure Period"
    period_years: str            # e.g. "2025-2032"
    period_energy: str           # full description
    period_economy: str
    period_society: str
    period_caution: str

    # Display text
    one_liner: str               # 1-2 sentences for app display
    full_insight: str            # full paragraph for "Read more"

    # Intersection with personal chart
    personal_intersection: str   # how country energy meets this user's energy


# ── Main getter ───────────────────────────────────────────────────────────────

def get_desh_context(
    country_code: str,
    supabase: Client,
    chart_data: dict = None,
    language: str = "en",
) -> Optional[DeshContext]:
    """
    Get the complete Desh context for a country.

    First tries to load from nation_charts table in Supabase.
    Falls back to calculated estimate if not found.
    """
    if not country_code:
        return None

    cc = country_code.upper()

    # Try to load from DB first (pre-calculated and stored)
    try:
        result = supabase.table("nation_charts").select("*").eq(
            "country_code", cc
        ).execute()

        if result.data:
            row     = result.data[0]
            period  = row.get("current_mahadasha", "Unknown")
            years   = row.get("mahadasha_period", "")
            theme   = COUNTRY_DASHA_THEMES.get(period, {})

            one_liner    = _build_one_liner(cc, period, years, theme, language)
            full_insight = _build_full_insight(cc, period, years, theme, language)
            intersection = _build_intersection(period, chart_data) if chart_data else ""

            return DeshContext(
                country_code=cc,
                country_name=COUNTRY_BIRTH_DATA.get(cc, {}).get("name", cc),
                current_period=f"{period} Mahadasha",
                period_quality=theme.get("quality", ""),
                period_years=years,
                period_energy=theme.get("energy", ""),
                period_economy=theme.get("economy", ""),
                period_society=theme.get("society", ""),
                period_caution=theme.get("caution", ""),
                one_liner=one_liner,
                full_insight=full_insight,
                personal_intersection=intersection,
            )
    except Exception as e:
        print(f"Desh DB error: {e}")

    return None


def get_country_oneliner(
    country_code: str,
    supabase: Client,
    language: str = "en",
) -> str:
    """
    Quick helper — just the 1-2 liner for display on home screen.
    """
    desh = get_desh_context(country_code, supabase, language=language)
    if desh:
        return desh.one_liner
    return ""


def desh_to_context_block(desh: DeshContext, patra=None) -> str:
    """
    Convert Desh context to LLM context block.
    Injected into prompt alongside predictions and patra.
    """
    if not desh:
        return ""

    lines = [
        "═══ DESH — COUNTRY CONTEXT ═══",
        f"Country: {desh.country_name}",
        f"Current national period: {desh.current_period} ({desh.period_years})",
        f"National energy: {desh.period_quality}",
        f"",
        f"What this means for {desh.country_name} right now:",
        f"General: {desh.period_energy}",
        f"Economy: {desh.period_economy}",
        f"Society: {desh.period_society}",
        f"Watch for: {desh.period_caution}",
    ]

    if desh.personal_intersection:
        lines += [
            "",
            "How this country energy intersects with this person's chart:",
            desh.personal_intersection,
        ]

    lines += [
        "═══ END DESH ═══",
    ]

    return "\n".join(lines)


# ── Intersection engine ───────────────────────────────────────────────────────

def _build_intersection(country_period: str, chart_data: dict) -> str:
    """
    Determines how the country's current energy intersects
    with the individual's personal chart.
    """
    if not chart_data:
        return ""

    lagna     = chart_data["lagna"]["sign"]
    moon_sign = chart_data["planets"]["Moon"]["sign"]

    # Simple intersection logic
    # Country Mars period + person's Mars strong = amplified action
    # Country Jupiter period + person's Jupiter dasha = double blessing
    # Country Saturn period + person's Sade Sati = double pressure

    intersection_map = {
        "Mars": {
            "Aries":  "The national action energy strongly supports your natural initiative.",
            "Scorpio":"The national drive aligns with your transformative power.",
            "Capricorn": "The national infrastructure push favors your disciplined approach.",
            "default": "The national boldness energy is available to you — but channel it, don't react from it.",
        },
        "Jupiter": {
            "Sagittarius": "The national prosperity energy amplifies your natural abundance.",
            "Pisces":  "The national growth wave supports your spiritual and creative expansion.",
            "Cancer":  "The national expansion favors home, family, and emotional growth for you.",
            "default": "The national growth energy creates a favorable backdrop for your personal expansion.",
        },
        "Saturn": {
            "Capricorn": "The national discipline period is demanding but your natural Saturn energy handles it.",
            "Aquarius":  "The national restructuring aligns with your capacity for systemic thinking.",
            "default": "The national pressure period is real — your strongest move is disciplined, patient work.",
        },
        "Rahu": {
            "Gemini":  "The national transformation energy feeds your natural adaptability.",
            "default": "The national transformation period brings opportunities through unconventional paths.",
        },
        "Mercury": {
            "Gemini":  "The national communication and tech boom strongly favors your natural gifts.",
            "Virgo":   "The national commerce period supports your analytical and service approach.",
            "default": "The national commerce and tech wave is available to those who communicate clearly.",
        },
        "Venus": {
            "Taurus":  "The national cultural prosperity period amplifies your natural Venus energy.",
            "Libra":   "The national harmony period supports your relational and diplomatic strengths.",
            "default": "The national culture and prosperity wave supports creative and relational pursuits.",
        },
    }

    planet_map = intersection_map.get(country_period, {})
    lagna_specific = planet_map.get(lagna, "")
    moon_specific  = planet_map.get(moon_sign, "")
    default        = planet_map.get("default", "")

    if lagna_specific:
        return lagna_specific
    if moon_specific:
        return moon_specific
    return default


def _build_one_liner(
    cc: str,
    period: str,
    years: str,
    theme: dict,
    language: str,
) -> str:
    """Build the 1-2 liner shown on the home screen."""

    country_name = COUNTRY_BIRTH_DATA.get(cc, {}).get("name", cc)
    quality      = theme.get("quality", "a significant period")
    energy_first = theme.get("energy", "").split(".")[0] if theme.get("energy") else ""

    if language == "es":
        return (
            f"{country_name} está en su período de {quality} ({years}). "
            f"{energy_first}."
        )
    elif language.startswith("pt"):
        return (
            f"{country_name} está em seu período de {quality} ({years}). "
            f"{energy_first}."
        )
    else:
        return (
            f"{country_name} is in its {quality} ({years}). "
            f"{energy_first}."
        )


def _build_full_insight(
    cc: str,
    period: str,
    years: str,
    theme: dict,
    language: str,
) -> str:
    """Build the full insight for 'Read more' expansion."""

    country_name = COUNTRY_BIRTH_DATA.get(cc, {}).get("name", cc)

    return (
        f"{country_name} is currently in its {period} Mahadasha ({years}), "
        f"a {theme.get('quality', 'significant')} period. "
        f"{theme.get('energy', '')} "
        f"Economically: {theme.get('economy', '')} "
        f"Socially: {theme.get('society', '')} "
        f"Areas to watch: {theme.get('caution', '')}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# ASTROCARTOGRAPHY SCAFFOLD (Phase 2)
# ══════════════════════════════════════════════════════════════════════════════

"""
Phase 2 Implementation Plan:

Astrocartography maps planetary lines across the world.
For each planet, 4 lines exist:
  - Ascendant line (AC): planet rising on the horizon
  - Midheaven line (MC): planet at career peak
  - Descendant line (DC): planet setting
  - IC line: planet at nadir

What each line means in a location:

  Sun AC/MC:    Fame, authority, identity expression peak
  Moon AC:      Emotional, intuitive, connected to locals
  Jupiter AC/MC: Luck, expansion, prosperity — best for business/life
  Venus AC:     Love, beauty, harmony — best for romance, art
  Saturn AC/MC: Hard work, discipline, karmic lessons
  Mars AC/MC:   Action, conflict, energy — military, sport, debate
  Mercury MC:   Communication success, writing, business
  Rahu AC:      Destiny calling, ambition, transformation
  Ketu AC:      Spiritual, past life connections, withdrawal

Algorithm (Swiss Ephemeris):
  For each planet, calculate the longitude where each angle
  (AC, MC, DC, IC) coincides with the planet's position.
  Draw these as vertical/curved lines on a world map.

Database schema when ready:
  CREATE TABLE astrocartography_readings (
    id UUID PRIMARY KEY,
    user_id UUID,
    chart_id UUID,
    latitude FLOAT,
    longitude FLOAT,
    city_name TEXT,
    country_code TEXT,
    planet TEXT,
    line_type TEXT,  -- AC/MC/DC/IC
    interpretation TEXT,
    strength FLOAT,  -- 0-1, how close to the line
    generated_at TIMESTAMPTZ,
    is_relocation BOOLEAN DEFAULT FALSE  -- true if user is considering moving
  );

API endpoint when ready:
  POST /api/v1/astrocartography
  Body: {
    chart_id: str,
    target_location: { lat, lng, city, country_code },
    question: "Is Dubai good for my career?"
  }
  Response: {
    lines_nearby: [...],
    location_reading: "...",
    recommendation: "..."
  }

Frontend: 
  Interactive world map (Leaflet.js or Mapbox)
  Colored planetary lines overlaid
  User can tap any city to get their reading for that location
  Especially powerful for: expats, people considering relocation,
  digital nomads, those in LATAM/India considering UAE or USA
"""

# ── Desh-Patra-Kaal synthesis ─────────────────────────────────────────────────

def build_desh_kaal_patra_block(
    desh,          # DeshContext
    patra,         # PatraProfile
    predictions,   # from predictions.py
) -> str:
    """
    The master synthesis block that combines all 3 layers.
    This is the most important context block in the entire system.
    Every prediction should be filtered through this.
    """

    lines = [
        "═══════════════════════════════════════════════════════",
        "DESH-KAAL-PATRA SYNTHESIS",
        "The complete context for this prediction.",
        "Every statement must be filtered through all 3 layers.",
        "═══════════════════════════════════════════════════════",
        "",
    ]

    # PATRA summary
    if patra:
        lines += [
            f"THE PERSON (Patra):",
            f"  Age {patra.age} — {patra.life_stage_name}",
            f"  {patra.marital_status.replace('_', ' ').title()} | {patra.career_stage.replace('_', ' ').title()}",
            f"  Currently in: {patra.current_country}",
        ]
        if patra.age_trigger:
            lines += [f"  ⚡ Age trigger: {patra.age_trigger[:80]}..."]
        lines.append("")

    # DESH summary
    if desh:
        lines += [
            f"THE COUNTRY (Desh):",
            f"  {desh.country_name} — {desh.current_period} ({desh.period_years})",
            f"  {desh.period_quality}",
            f"  Economy: {desh.period_economy[:80]}...",
        ]
        if desh.personal_intersection:
            lines += [f"  Personal intersection: {desh.personal_intersection[:100]}..."]
        lines.append("")

    # KAAL summary
    if predictions:
        top_pred = predictions.get("lead", {})
        lines += [
            f"THE TIME (Kaal):",
            f"  Highest signal: Layer {top_pred.get('layer', 1)} | "
            f"{int(top_pred.get('confidence', 0)*100)}% confidence",
            f"  {top_pred.get('what', '')[:100]}...",
            "",
        ]

    lines += [
        "SYNTHESIS INSTRUCTION FOR AI:",
        "Read all 3 layers above before generating your response.",
        "The prediction must make sense for:",
        f"  → A {patra.age if patra else '?'}-year-old in {patra.life_stage_name if patra else '?'} stage",
        f"  → Living in {desh.country_name if desh else '?'} during {desh.current_period if desh else '?'}",
        f"  → With the cosmic timing signals shown above",
        "If these 3 layers conflict, acknowledge the tension honestly.",
        "If they align, make the amplification explicit.",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)
