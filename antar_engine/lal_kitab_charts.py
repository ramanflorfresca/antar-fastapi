# antar_engine/lal_kitab_charts.py
"""
Lal Kitab Chart Generator
==========================
Varshphal (annual) and Mashaphal (monthly) generation + dedicated storage.

Relationship to lal_kitab_db.py
---------------------------------
lal_kitab_db.py     → LalKitabEngine.build_and_save()
                      writes charts.lal_kitab_data  (hot-path jsonb cache)
lal_kitab_charts.py → LalKitabChartGenerator
                      writes lal_kitab_varshphal_charts + lal_kitab_mashaphal_charts
                      (queryable history, includes Mashaphal)

Call order at chart creation
------------------------------
1. LalKitabEngine(supabase).build_and_save(chart_id, birth_date)
   → hot cache, used by /predict immediately
2. LalKitabChartGenerator(supabase).generate_and_store_varshphal(user_id, chart_id)
   → history tables, used by dedicated /lal-kitab endpoints

Query budgets
--------------
generate_and_store_varshphal  : 5 queries
generate_mashaphal            : 3 queries
get_current_varshphal         : 1 query
get_current_mashaphal         : 1 query (3 if generating on-demand)
"""

import calendar
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from supabase import Client

from antar_engine.varshaphal_table import get_annual_house
from antar_engine.lal_kitab_db import (
    PLANET_PRIORITY,
    _SPECIAL_CYCLES,
    _extract_natal_houses,
)


class LalKitabChartGenerator:
    """Generate and store Varshphal and Mashaphal charts."""

    def __init__(self, supabase: Client):
        self.db = supabase

    # ─────────────────────────────────────────────────────────────────────
    # VARSHPHAL
    # ─────────────────────────────────────────────────────────────────────

    def generate_varshphal(
        self,
        user_id: str,
        chart_id: str,
        target_year: Optional[int] = None,
        store: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate Varshphal for the user's current birthday year and store it.
        Returns the stored dict including its UUID (needed to generate Mashaphal).
        Queries: 4  (placements in-memory via varshaphal_table.py).
        """
        # Q1: natal chart
        chart_res = (
            self.db.table("charts")
            .select("chart_data, birth_date")
            .eq("id", chart_id)
            .single()
            .execute()
        )
        if not chart_res.data:
            raise ValueError(f"Chart {chart_id} not found")

        chart_data     = chart_res.data["chart_data"]
        birth_date_str = chart_res.data["birth_date"]
        birth_date     = datetime.strptime(birth_date_str, "%Y-%m-%d").date()

        if target_year is None:
            today     = date.today()
            last_bday = birth_date.replace(year=today.year)
            if last_bday > today:
                last_bday = last_bday.replace(year=today.year - 1)
            target_year = last_bday.year

        age          = target_year - birth_date.year
        running_year = max(1, min(120, age + 1))   # replaces broken ((age-1)%12)+1

        natal_houses  = _extract_natal_houses(chart_data)

        # Q2: bulk varshphal placements (uses authentic 120-row table)
        placements    = self._bulk_varshphal_placements(age, natal_houses)

        # Q3: planet ID map
        planet_id_map = self._get_planet_id_map(list(placements.keys()))

        # Q4: bulk predictions
        predictions   = self._bulk_predictions(placements, planet_id_map)

        # Q5: bulk remedies (top 5 planets)
        remedies      = self._bulk_remedies_dict(placements, planet_id_map, max_planets=5)

        special = _SPECIAL_CYCLES.get(age)

        row = {
            "user_id":            user_id,
            "chart_id":           chart_id,
            "year":               target_year,
            "age":                age,
            "table_age":          running_year,   # running year (age+1), not (age-1)%12+1
            "placements":         placements,
            "predictions":        predictions,
            "remedies":           remedies,
            "is_special_cycle":   special is not None,
            "cycle_type":         str(age) if special else None,
            "cycle_significance": special["significance"] if special else None,
            "updated_at":         datetime.utcnow().isoformat(),
        }

        if store:
            result = (
                self.db.table("lal_kitab_varshphal_charts")
                .upsert(row, on_conflict="user_id,year")
                .execute()
            )
            if result.data:
                row["id"] = result.data[0]["id"]

            # Also write back to charts.lal_kitab_data so /predict hot path
            # always sees fresh data (this is what format_lk_context_from_stored reads)
            lk_data_for_hot_path = {
                "age":                age,
                "table_age":          running_year,
                "placements":         placements,
                "is_special_cycle":   special is not None,
                "cycle_significance": special["significance"] if special else None,
                "predictions":        predictions,
                "remedies_summary":   list(remedies.values())[:4] if remedies else [],
            }
            self.db.table("charts").update({
                "lal_kitab_data": lk_data_for_hot_path,
                "lk_age":         age,
                "lk_computed_at": datetime.utcnow().isoformat(),
            }).eq("id", chart_id).execute()

        return row

    def get_current_varshphal(self, user_id: str) -> Optional[Dict[str, Any]]:
        today  = date.today()
        result = (
            self.db.table("lal_kitab_varshphal_charts")
            .select("*")
            .eq("user_id", user_id)
            .gte("year", today.year - 1)
            .lte("year", today.year + 1)
            .order("year", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_varshphal_history(
        self, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        result = (
            self.db.table("lal_kitab_varshphal_charts")
            .select("id, year, age, table_age, is_special_cycle, cycle_significance, placements, created_at")
            .eq("user_id", user_id)
            .order("year", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def save_llm_reading(self, varshphal_id: str, reading: str) -> None:
        self.db.table("lal_kitab_varshphal_charts").update({
            "llm_reading":  reading,
            "reading_short": reading[:400] if reading else None,
            "updated_at":   datetime.utcnow().isoformat(),
        }).eq("id", varshphal_id).execute()

    # ─────────────────────────────────────────────────────────────────────
    # MASHAPHAL
    # ─────────────────────────────────────────────────────────────────────

    def generate_mashaphal(
        self,
        varshphal_id: str,
        month_offset: int,
        store: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate one month's Mashaphal.

        month_offset: 0 = first month (birthday month), 11 = last month.
        Lal Kitab rule: each month, every planet advances +1 house (mod 12, 1-based).
        Queries: 3.
        """
        if not 0 <= month_offset <= 11:
            raise ValueError(f"month_offset must be 0-11, got {month_offset}")

        # Q1: Varshphal + birth_date via join
        varsh_res = (
            self.db.table("lal_kitab_varshphal_charts")
            .select("*, charts(birth_date)")
            .eq("id", varshphal_id)
            .single()
            .execute()
        )
        if not varsh_res.data:
            raise ValueError(f"Varshphal {varshphal_id} not found")

        varsh      = varsh_res.data
        birth_date = datetime.strptime(
            varsh["charts"]["birth_date"], "%Y-%m-%d"
        ).date()

        varshphal_start      = birth_date.replace(year=varsh["year"])
        month_start          = _add_months(varshphal_start, month_offset)

        varshphal_placements: Dict[str, int] = varsh["placements"]
        mashaphal_placements: Dict[str, int] = {
            planet: ((house - 1 + month_offset) % 12) + 1
            for planet, house in varshphal_placements.items()
        }

        # Q2: planet ID map
        planet_id_map = self._get_planet_id_map(list(mashaphal_placements.keys()))

        # Q3: bulk predictions for this month's placements
        predictions = self._bulk_predictions(mashaphal_placements, planet_id_map)

        # Remedies: inherit from Varshphal (same annual practices, monthly emphasis shifts)
        monthly_remedies = varsh.get("remedies") or {}

        mashaphal = {
            "varshphal_id":         varshphal_id,
            "user_id":              varsh["user_id"],
            "month_number":         month_offset + 1,
            "month_name":           month_start.strftime("%B"),
            "calendar_month":       month_start.month,
            "calendar_year":        month_start.year,
            "mashaphal_placements": mashaphal_placements,
            "monthly_predictions":  predictions,
            "monthly_remedies":     monthly_remedies,
            "important_dates":      [],
        }

        if store:
            result = (
                self.db.table("lal_kitab_mashaphal_charts")
                .upsert(mashaphal, on_conflict="varshphal_id,month_number")
                .execute()
            )
            if result.data:
                mashaphal["id"] = result.data[0]["id"]

        return mashaphal

    def generate_all_mashaphal(
        self, varshphal_id: str, store: bool = True
    ) -> List[Dict[str, Any]]:
        return [
            self.generate_mashaphal(varshphal_id, offset, store=store)
            for offset in range(12)
        ]

    def get_current_mashaphal(self, user_id: str) -> Optional[Dict[str, Any]]:
        today  = date.today()
        result = (
            self.db.table("lal_kitab_mashaphal_charts")
            .select("*")
            .eq("user_id", user_id)
            .eq("calendar_month", today.month)
            .eq("calendar_year", today.year)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_or_generate_current_mashaphal(
        self, user_id: str, birth_date_str: str
    ) -> Optional[Dict[str, Any]]:
        """Returns this month's Mashaphal, generating on-demand if needed."""
        cached = self.get_current_mashaphal(user_id)
        if cached:
            return cached

        varshphal = self.get_current_varshphal(user_id)
        if not varshphal:
            return None

        today       = date.today()
        birth_date  = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        varsh_start = birth_date.replace(year=varshphal["year"])
        months_elapsed = (
            (today.year - varsh_start.year) * 12
            + (today.month - varsh_start.month)
        )
        month_offset = months_elapsed % 12

        return self.generate_mashaphal(varshphal["id"], month_offset, store=True)

    # ─────────────────────────────────────────────────────────────────────
    # REMEDY TRACKING
    # ─────────────────────────────────────────────────────────────────────

    def track_remedy(
        self,
        user_id: str,
        varshphal_id: str,
        remedy_id: int,
        remedy_name: str,
        instructions: str,
        duration: Optional[str] = None,
        materials: Optional[List[str]] = None,
        status: str = "in_progress",
        notes: Optional[str] = None,
    ) -> Optional[str]:
        today  = date.today()
        result = (
            self.db.table("lal_kitab_remedy_tracking")
            .upsert(
                {
                    "user_id":       user_id,
                    "remedy_id":     remedy_id,
                    "varshphal_id":  varshphal_id,
                    "remedy_name":   remedy_name,
                    "instructions":  instructions,
                    "duration":      duration,
                    "materials":     materials or [],
                    "status":        status,
                    "notes":         notes,
                    "started_at":    today.isoformat() if status == "in_progress" else None,
                    "completed_at":  today.isoformat() if status == "completed" else None,
                    "updated_at":    datetime.utcnow().isoformat(),
                },
                on_conflict="user_id,remedy_id,varshphal_id",
            )
            .execute()
        )
        return result.data[0]["id"] if result.data else None

    def get_remedy_tracking(
        self, user_id: str, varshphal_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        q = (
            self.db.table("lal_kitab_remedy_tracking")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
        )
        if varshphal_id:
            q = q.eq("varshphal_id", varshphal_id)
        return q.execute().data or []

    # ─────────────────────────────────────────────────────────────────────
    # NOTIFICATIONS
    # ─────────────────────────────────────────────────────────────────────

    def schedule_birthday_reminder(
        self, user_id: str, birthday: date, days_before: int = 7
    ) -> None:
        scheduled_for = birthday - timedelta(days=days_before)
        self.db.table("lal_kitab_notifications").insert({
            "user_id":           user_id,
            "notification_type": "birthday_soon",
            "scheduled_for":     scheduled_for.isoformat(),
            "notification_data": {"birthday": birthday.isoformat()},
        }).execute()

    def schedule_new_varshphal_notification(
        self, user_id: str, varshphal_year: int, notify_on: date
    ) -> None:
        self.db.table("lal_kitab_notifications").insert({
            "user_id":           user_id,
            "notification_type": "new_varshphal",
            "scheduled_for":     notify_on.isoformat(),
            "notification_data": {"varshphal_year": varshphal_year},
        }).execute()

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        result = (
            self.db.table("lal_kitab_notifications")
            .select("*")
            .lte("scheduled_for", date.today().isoformat())
            .is_("sent_at", "null")
            .execute()
        )
        return result.data or []

    def mark_notification_sent(self, notification_id: str) -> None:
        self.db.table("lal_kitab_notifications").update(
            {"sent_at": datetime.utcnow().isoformat()}
        ).eq("id", notification_id).execute()

    # ─────────────────────────────────────────────────────────────────────
    # BIRTHDAY CRON ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────

    def generate_for_birthday(
        self, user_id: str, chart_id: str, birth_date: date
    ) -> Dict[str, Any]:
        """
        Called by the daily cron job for users with upcoming birthdays.
        Generates next year's Varshphal, pre-generates all 12 Mashaphal,
        and schedules a 'new_varshphal' notification.
        """
        next_year = date.today().year + 1
        varshphal = self.generate_and_store_varshphal(
            user_id=user_id,
            chart_id=chart_id,
            target_year=next_year,
        )

        varshphal_id = varshphal.get("id")
        if varshphal_id:
            try:
                self.generate_all_mashaphal(varshphal_id, store=True)
            except Exception as e:
                print(f"Mashaphal pre-gen error (non-fatal): {e}")
            try:
                self.schedule_new_varshphal_notification(
                    user_id=user_id,
                    varshphal_year=next_year,
                    notify_on=birth_date,
                )
            except Exception as e:
                print(f"Notification schedule error (non-fatal): {e}")

        return varshphal


    # backward-compat alias
    generate_and_store_varshphal = generate_varshphal

    # ─────────────────────────────────────────────────────────────────────
    # PRIVATE: bulk DB helpers
    # ─────────────────────────────────────────────────────────────────────

    def _bulk_varshphal_placements(
        self, age: int, natal_houses: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Compute annual house for each planet using the authentic 120-row table.
        No DB query needed — pure in-memory lookup via get_annual_house().
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

    def _bulk_predictions(
        self, placements: Dict[str, int], planet_id_map: Dict[str, int]
    ) -> List[Dict]:
        planet_ids = list(planet_id_map.values())
        house_nums = list(set(placements.values()))
        if not planet_ids:
            return []
        result = (
            self.db.table("lal_kitab_predictions")
            .select("planet_id, house_number, prediction_template, positive_effect, negative_effect")
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
                "negative":   row.get("negative_effect"),
            })
        return out

    def _bulk_remedies_dict(
        self,
        placements: Dict[str, int],
        planet_id_map: Dict[str, int],
        max_planets: int = 5,
    ) -> Dict[str, List[Dict]]:
        top_planets = [p for p in PLANET_PRIORITY if p in placements][:max_planets]
        planet_ids  = [planet_id_map[p] for p in top_planets if p in planet_id_map]
        house_nums  = list({placements[p] for p in top_planets})
        if not planet_ids:
            return {}
        result = (
            self.db.table("lal_kitab_remedies")
            .select("planet_id, house_number, name, instructions, duration, timing, materials, remedy_type")
            .in_("planet_id", planet_ids)
            .in_("house_number", house_nums)
            .execute()
        )
        id_planet = {v: k for k, v in planet_id_map.items()}
        out: Dict[str, List[Dict]] = {}
        for row in (result.data or []):
            planet = id_planet.get(row["planet_id"])
            if not planet or placements.get(planet) != row["house_number"]:
                continue
            out.setdefault(planet, []).append({
                "name":         row["name"],
                "instructions": row["instructions"],
                "duration":     row["duration"],
                "timing":       row["timing"],
                "materials":    row.get("materials") or [],
                "remedy_type":  row["remedy_type"],
            })
        return out


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _add_months(d: date, months: int) -> date:
    """Add N months to a date, clamping to end of month."""
    month = d.month - 1 + months
    year  = d.year + month // 12
    month = month % 12 + 1
    day   = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
