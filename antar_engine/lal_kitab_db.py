# antar_engine/lal_kitab_db.py
"""
Lal Kitab DB Engine — production version
==========================================

TWO EXECUTION PATHS — never mix them:

  HOT PATH  (/predict — called on every question):
    format_lk_context_from_stored(chart_record["lal_kitab_data"], concern)
    → reads the jsonb already on the chart row, zero extra DB queries
    → returns a string block appended to the LLM system prompt

  COLD PATH  (chart creation + user-facing remedy cards):
    LalKitabEngine.build_and_save(chart_id, birth_date)
    → runs at chart creation, saves result to charts.lal_kitab_data
    → never called during /predict

  CONVERGENCE  (inside /predict, after hot path):
    score_lk_convergence(placements, concern)
    → pure python, zero DB queries, already embedded in hot-path output

Query budget:
  Chart creation  : 3 queries total (placements are in-memory, no DB query)
  /predict        : 0 extra queries (reads stored jsonb)
  Frontend cards  : 1 query (remedies for 3 planets with IN clause)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from supabase import Client

from antar_engine.varshaphal_table import get_annual_house


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

PLANET_PRIORITY = [
    "Sun", "Moon", "Mars", "Saturn", "Jupiter",
    "Rahu", "Ketu", "Venus", "Mercury",
]

BENEFIC_ANNUAL_HOUSES     = {1, 2, 4, 5, 7, 9, 10, 11}
CHALLENGING_ANNUAL_HOUSES = {6, 8, 12}

DOMAIN_PLANETS: Dict[str, List[str]] = {
    "career":    ["Sun", "Saturn", "Mercury"],
    "wealth":    ["Jupiter", "Venus", "Moon"],
    "marriage":  ["Venus", "Jupiter", "Moon"],
    "love":      ["Venus", "Moon"],
    "health":    ["Saturn", "Mars", "Sun"],
    "children":  ["Jupiter", "Moon"],
    "spiritual": ["Ketu", "Saturn", "Jupiter"],
    "property":  ["Mars", "Saturn", "Moon"],
    "foreign":   ["Rahu", "Moon"],
    "education": ["Mercury", "Jupiter"],
    "legal":     ["Saturn", "Mars", "Sun"],
}

_SPECIAL_CYCLES: Dict[int, Dict] = {
    35: {
        "significance": "The 35-year karmic reset — major life restructuring indicated",
        "focus":        "Career, relationships, life direction",
    },
    47: {
        "significance": "Wisdom and teaching phase — share your knowledge",
        "focus":        "Mentorship, writing, teaching",
    },
    60: {
        "significance": "Second Saturn return — legacy crystallisation",
        "focus":        "Retirement planning, life review, legacy",
    },
    70: {
        "significance": "Double 35 — profound spiritual transition",
        "focus":        "Spiritual liberation, detachment",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# HOT PATH — zero DB queries, called inside /predict
# ─────────────────────────────────────────────────────────────────────────────

def format_lk_context_from_stored(
    lk_data: Optional[Dict],
    concern: str = "career",
    max_prediction_hints: int = 3,
) -> str:
    """
    Build the Lal Kitab block for the LLM system prompt.
    Reads chart_record["lal_kitab_data"] — ZERO extra DB queries.

    Call this inside /predict after chart_record is already loaded.
    Returns "" if no lal_kitab_data stored (old charts before migration 07).
    """
    if not lk_data or not lk_data.get("placements"):
        return ""

    placements: Dict[str, int] = lk_data["placements"]
    age:        int             = lk_data.get("age", 0)
    table_age:  int             = lk_data.get("table_age", 0)
    is_special: bool            = lk_data.get("is_special_cycle", False)
    cycle_note: Optional[str]   = lk_data.get("cycle_significance")

    lines = [f"LAL KITAB VARSHPHAL — Age {age} (cycle year {table_age}):"]

    if is_special and cycle_note:
        lines.append(f"  *** SPECIAL CYCLE: {cycle_note} ***")

    for planet in PLANET_PRIORITY:
        house = placements.get(planet)
        if house is None:
            continue
        lines.append(f"  {_planet_energy(planet)}: annual {_house_theme(house)}")

    conv = score_lk_convergence(placements, concern)
    if conv:
        lines.append(f"  {conv}")

    stored_predictions = lk_data.get("predictions", [])
    if stored_predictions:
        ranked = _rank_predictions_by_concern(stored_predictions, concern)
        hints  = [
            f"  ({p['planet']}): {p['positive']}"
            for p in ranked[:max_prediction_hints]
            if p.get("positive")
        ]
        if hints:
            lines.append("  Annual opportunities:")
            lines.extend(hints)

    return "\n".join(lines)


def score_lk_convergence(placements: Dict[str, int], concern: str) -> str:
    """
    One-line convergence note for the LLM prompt.
    Checks whether annual placements support or challenge the concern domain.
    Pure Python — zero DB queries.
    """
    planets = DOMAIN_PLANETS.get(concern, [])
    if not planets:
        return ""

    supporting  = [p for p in planets if placements.get(p) in BENEFIC_ANNUAL_HOUSES]
    challenging = [p for p in planets if placements.get(p) in CHALLENGING_ANNUAL_HOUSES]

    if supporting and challenging:
        return (
            f"Lal Kitab MIXED for {concern}: "
            f"{', '.join(supporting)} in favourable annual zones, "
            f"{', '.join(challenging)} need practical remedy."
        )
    if supporting:
        return f"Lal Kitab SUPPORTS {concern}: {', '.join(supporting)} in favourable annual zones."
    if challenging:
        return (
            f"Lal Kitab CAUTION for {concern}: "
            f"{', '.join(challenging)} in challenging annual zones — remedies recommended."
        )
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# COLD PATH — runs at chart creation only
# ─────────────────────────────────────────────────────────────────────────────

class LalKitabEngine:
    """
    DB-backed engine. Called ONCE at chart creation.
    Never instantiated inside /predict.
    """

    def __init__(self, supabase: Client):
        self.db = supabase

    def build_and_save(self, chart_id: str, birth_date: str) -> Dict:
        """
        Compute Varshphal and save to charts.lal_kitab_data.
        Returns the stored dict for immediate use in the create response.

        Call this at the end of create_chart(), after the chart row is inserted.
        Total DB queries: 3  (placements now use in-memory table, saving 1 query).
        """
        age          = _age_from_birth_date(birth_date)
        running_year = max(1, min(120, age + 1))   # replaces broken ((age-1)%12)+1

        # Query 1: natal chart
        chart_result = (
            self.db.table("charts")
            .select("chart_data")
            .eq("id", chart_id)
            .single()
            .execute()
        )
        if not chart_result.data:
            raise ValueError(f"Chart {chart_id} not found")

        chart_data   = chart_result.data["chart_data"]
        natal_houses = _extract_natal_houses(chart_data)

        # Varshphal placements — pure in-memory, no DB query needed
        placements = self._bulk_varshphal_placements(age, natal_houses)

        # Query 2 (planet ID map) + Query 3a (remedies) combined approach:
        all_planet_names = list(placements.keys())
        planet_id_map    = self._get_planet_id_map(all_planet_names)

        # Query 3a: bulk remedies (top 4 planets)
        remedies_summary = self._bulk_remedies(placements, planet_id_map, max_planets=4)

        # Query 3b: bulk predictions (all planets, same planet_id_map)
        predictions = self._bulk_predictions(placements, planet_id_map)

        special = _SPECIAL_CYCLES.get(age)

        lk_data = {
            "age":                age,
            "table_age":          running_year,   # running year (age+1), not (age-1)%12+1
            "placements":        placements,
            "is_special_cycle":  special is not None,
            "cycle_significance": special["significance"] if special else None,
            "remedies_summary":  remedies_summary,
            "predictions":       predictions,
        }

        self.db.table("charts").update({
            "lal_kitab_data":  lk_data,
            "lk_age":          age,
            "lk_computed_at":  datetime.utcnow().isoformat(),
        }).eq("id", chart_id).execute()

        return lk_data

    def get_remedy_cards(
        self,
        lk_data: Dict,
        concern: str = "career",
        locale: str = "US",
        max_cards: int = 3,
    ) -> List[Dict]:
        """
        Frontend-ready remedy cards for the Deep Dive panel.
        ONE query using IN() clause — not 2*N queries.
        Locale gates the detail level: IN = full ritual, all others = softened.
        """
        placements: Dict[str, int] = lk_data.get("placements", {})
        if not placements:
            return []

        ordered     = _concern_ordered_planets(concern)
        top_planets = [p for p in ordered if p in placements][:max_cards]
        if not top_planets:
            return []

        planet_id_map = self._get_planet_id_map(top_planets)
        planet_ids    = list(planet_id_map.values())
        house_nums    = [placements[p] for p in top_planets]

        result = (
            self.db.table("lal_kitab_remedies")
            .select(
                "planet_id, house_number, name, instructions, "
                "duration, timing, materials, contraindications"
            )
            .in_("planet_id", planet_ids)
            .in_("house_number", house_nums)
            .eq("remedy_type", "specific")
            .execute()
        )

        id_planet = {v: k for k, v in planet_id_map.items()}
        cards = []

        for row in (result.data or []):
            planet = id_planet.get(row["planet_id"])
            if not planet or placements.get(planet) != row["house_number"]:
                continue

            card = {
                "planet":           planet,
                "planet_energy":    _planet_energy(planet),
                "house":            row["house_number"],
                "duration":         row["duration"],
                "timing":           row["timing"],
                "contraindication": row.get("contraindications"),
                "system_label":     "Lal Kitab" if locale == "IN" else "Annual energy practice",
            }

            if locale == "IN":
                card["name"]        = row["name"]
                card["instruction"] = row["instructions"]
                card["materials"]   = row.get("materials") or []
            else:
                card["name"]        = _significance_label(planet)
                card["instruction"] = _soften_instruction(row["instructions"])
                card["materials"]   = None

            cards.append(card)
            if len(cards) >= max_cards:
                break

        return cards

    def save_history(
        self,
        user_id: str,
        chart_id: str,
        lk_data: Dict,
        llm_reading: Optional[str] = None,
    ) -> Optional[str]:
        """Upsert annual reading to user_varshphal_history."""
        result = (
            self.db.table("user_varshphal_history")
            .upsert(
                {
                    "user_id":              user_id,
                    "chart_id":             chart_id,
                    "age":                  lk_data["age"],
                    "year":                 datetime.now().year,
                    "varshphal_placements": lk_data["placements"],
                    "special_cycle":        lk_data.get("is_special_cycle", False),
                    "reading":              llm_reading,
                },
                on_conflict="user_id,year",
            )
            .execute()
        )
        return result.data[0]["id"] if result.data else None

    def track_remedy_completion(
        self,
        user_id: str,
        remedy_id: int,
        varshphal_year: int,
        status: str = "in_progress",
    ) -> None:
        """Upsert remedy tracking. status: pending|in_progress|completed|abandoned"""
        self.db.table("user_remedy_completions").upsert(
            {
                "user_id":        user_id,
                "remedy_id":      remedy_id,
                "varshphal_year": varshphal_year,
                "started_at":     date.today().isoformat(),
                "status":         status,
            },
            on_conflict="user_id,remedy_id,varshphal_year",
        ).execute()

    def get_remedy_completions(
        self, user_id: str, varshphal_year: int
    ) -> List[Dict]:
        result = (
            self.db.table("user_remedy_completions")
            .select("*, lal_kitab_remedies(name, timing, duration)")
            .eq("user_id", user_id)
            .eq("varshphal_year", varshphal_year)
            .execute()
        )
        return result.data or []

    def generate_reading_prompt(self, lk_data: Dict, concern: str = "general") -> str:
        """
        Full LLM prompt for a dedicated /varshphal endpoint (not /predict).
        Use this when you want a standalone Varshphal reading page.
        """
        age        = lk_data.get("age", 0)
        table_age  = lk_data.get("table_age", 0)
        special    = lk_data.get("cycle_significance")
        placements = lk_data.get("placements", {})
        preds      = lk_data.get("predictions", [])
        remedies   = lk_data.get("remedies_summary", [])

        lines = [
            "You are Antar, providing a Lal Kitab annual chart reading.",
            f"Age: {age} (cycle year {table_age}).",
            "",
        ]

        if special:
            lines += [f"SPECIAL CYCLE: {special}", ""]

        lines.append("Annual planetary placements:")
        for planet in PLANET_PRIORITY:
            house = placements.get(planet)
            if house:
                lines.append(f"  {_planet_energy(planet)} → {_house_theme(house)}")

        if preds:
            lines += ["", "Predicted effects:"]
            for pred in _rank_predictions_by_concern(preds, concern):
                lines.append(f"  {pred['planet']}: {pred['prediction']}")
                if pred.get("positive"):
                    lines.append(f"    Opportunity: {pred['positive']}")
                if pred.get("caution"):
                    lines.append(f"    Caution: {pred['caution']}")

        if remedies:
            lines += ["", "Recommended annual practices:"]
            for r in remedies:
                lines.append(f"  {r['name']}: {r['instructions']}")
                lines.append(f"    Duration: {r['duration']} | Timing: {r['timing']}")
                if r.get("contraindications"):
                    lines.append(f"    Note: {r['contraindications']}")

        conv = score_lk_convergence(placements, concern)
        if conv:
            lines += ["", f"Convergence note: {conv}"]

        lines += [
            "",
            "Instructions:",
            "- Translate placements to energy language. No raw house numbers as the lead.",
            "- Lead with theme and meaning, not planet name.",
            "- Integrate with Vimsottari, Jaimini, and Ashtottari context already provided.",
            "- When all four timing systems agree, flag as high-confidence signal.",
            "- For non-Indian users, frame remedies as grounding practices, not rituals.",
        ]

        return "\n".join(lines)

    # ── private query helpers ─────────────────────────────────────────────

    def _bulk_varshphal_placements(
        self, age: int, natal_houses: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Compute annual house for each planet using the authentic 120-row table.
        Pure in-memory — no DB query. Eliminates the old lal_kitab_varshphal table lookup.
        """
        return {
            planet: get_annual_house(natal_house, age)
            for planet, natal_house in natal_houses.items()
            if 1 <= natal_house <= 12
        }

    def _get_planet_id_map(self, planet_names: List[str]) -> Dict[str, int]:
        if not planet_names:
            return {}
        result = (
            self.db.table("lal_kitab_planets")
            .select("id, planet_name")
            .in_("planet_name", planet_names)
            .execute()
        )
        return {row["planet_name"]: row["id"] for row in (result.data or [])}

    def _bulk_remedies(
        self,
        placements: Dict[str, int],
        planet_id_map: Dict[str, int],
        max_planets: int = 4,
    ) -> List[Dict]:
        top_planets = [p for p in PLANET_PRIORITY if p in placements][:max_planets]
        planet_ids  = [planet_id_map[p] for p in top_planets if p in planet_id_map]
        house_nums  = list({placements[p] for p in top_planets})

        if not planet_ids:
            return []

        result = (
            self.db.table("lal_kitab_remedies")
            .select(
                "planet_id, house_number, name, instructions, "
                "duration, timing, materials, contraindications"
            )
            .in_("planet_id", planet_ids)
            .in_("house_number", house_nums)
            .eq("remedy_type", "specific")
            .execute()
        )

        id_planet = {v: k for k, v in planet_id_map.items()}
        seen, out = set(), []

        for row in (result.data or []):
            planet = id_planet.get(row["planet_id"])
            if not planet or planet in seen:
                continue
            if placements.get(planet) != row["house_number"]:
                continue
            seen.add(planet)
            out.append({
                "planet":            planet,
                "house":             row["house_number"],
                "name":              row["name"],
                "instructions":      row["instructions"],
                "duration":          row["duration"],
                "timing":            row["timing"],
                "materials":         row.get("materials") or [],
                "contraindications": row.get("contraindications"),
            })

        return out

    def _bulk_predictions(
        self,
        placements: Dict[str, int],
        planet_id_map: Dict[str, int],
    ) -> List[Dict]:
        planet_ids = list(planet_id_map.values())
        house_nums = list(set(placements.values()))

        if not planet_ids:
            return []

        result = (
            self.db.table("lal_kitab_predictions")
            .select(
                "planet_id, house_number, "
                "prediction_template, positive_effect, negative_effect"
            )
            .in_("planet_id", planet_ids)
            .in_("house_number", house_nums)
            .execute()
        )

        id_planet = {v: k for k, v in planet_id_map.items()}
        out = []

        for row in (result.data or []):
            planet = id_planet.get(row["planet_id"])
            if not planet or placements.get(planet) != row["house_number"]:
                continue
            out.append({
                "planet":     planet,
                "house":      row["house_number"],
                "prediction": row["prediction_template"],
                "positive":   row.get("positive_effect"),
                "caution":    row.get("negative_effect"),
            })

        return out


# ─────────────────────────────────────────────────────────────────────────────
# PURE PYTHON HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _age_from_birth_date(birth_date: str) -> int:
    today = date.today()
    born  = date.fromisoformat(birth_date)
    return today.year - born.year - (
        (today.month, today.day) < (born.month, born.day)
    )


def _extract_natal_houses(chart_data: Dict) -> Dict[str, int]:
    return {
        planet: pdata.get("house", pdata.get("sign_index", 0) + 1)
        for planet, pdata in chart_data.get("planets", {}).items()
    }


def _concern_ordered_planets(concern: str) -> List[str]:
    relevant = DOMAIN_PLANETS.get(concern, [])
    rest     = [p for p in PLANET_PRIORITY if p not in relevant]
    return relevant + rest


def _rank_predictions_by_concern(
    predictions: List[Dict], concern: str
) -> List[Dict]:
    relevant = set(DOMAIN_PLANETS.get(concern, []))
    return sorted(predictions, key=lambda p: (0 if p["planet"] in relevant else 1))


def _planet_energy(planet: str) -> str:
    return {
        "Sun":     "Identity & Purpose energy",
        "Moon":    "Emotional Depth energy",
        "Mars":    "Action & Courage energy",
        "Mercury": "Intellect & Communication energy",
        "Jupiter": "Expansive Growth energy",
        "Venus":   "Heart & Beauty energy",
        "Saturn":  "Clarifying Pressure energy",
        "Rahu":    "Hungry Becoming energy",
        "Ketu":    "Releasing & Liberation energy",
    }.get(planet, f"{planet} energy")


def _house_theme(house: int) -> str:
    return {
        1:  "identity zone",
        2:  "wealth & speech zone",
        3:  "courage & initiative zone",
        4:  "home & roots zone",
        5:  "children & creativity zone",
        6:  "service & health zone",
        7:  "partnerships zone",
        8:  "transformation zone",
        9:  "fortune & dharma zone",
        10: "career & status zone",
        11: "gains & income zone",
        12: "spirituality & release zone",
    }.get(house, f"zone {house}")


def _significance_label(planet: str) -> str:
    return {
        "Sun":     "Building confidence and clarity",
        "Moon":    "Emotional grounding practice",
        "Mars":    "Channelling energy constructively",
        "Mercury": "Sharpening communication and focus",
        "Jupiter": "Expanding wisdom and gratitude",
        "Venus":   "Cultivating beauty and connection",
        "Saturn":  "Discipline and karmic clearing",
        "Rahu":    "Grounding ambition in purpose",
        "Ketu":    "Spiritual release and detachment",
    }.get(planet, "Annual energy practice")


def _soften_instruction(instruction: str) -> str:
    replacements = [
        ("Throw a copper coin in flowing water",  "Connect with natural flow each morning"),
        ("Feed crows for 43 days",                "A nature-offering practice at sunrise for 43 days"),
        ("Feed birds with wheat daily",           "A daily sunrise offering to nature"),
        ("Water a peepal tree for 43 days",       "A daily nature-connection practice for 43 days"),
        ("Donate black blankets on Saturdays",    "A service and giving practice on Saturdays"),
        ("Pour mustard oil at the base of",       "An offering practice at"),
        ("Offer coconut at a Bhairav temple",     "A ritual offering at a sacred space"),
        ("Offer mustard oil at Shani temple",     "A grounding offering practice on Saturdays"),
        ("Bury 6 copper squares",                 "A grounding ritual with copper"),
        ("Bury 7 copper squares",                 "A grounding ritual with copper"),
        ("Throw red lentils into flowing water",  "An offering to flowing water on Tuesdays"),
        ("Feed a white cow with rice and jaggery","A nature-nourishing offering practice"),
        ("Perform ancestral rituals",             "A practice of honouring your lineage"),
    ]
    result = instruction
    for original, soft in replacements:
        if original.lower() in result.lower():
            result = result.replace(original, soft)
    return result
