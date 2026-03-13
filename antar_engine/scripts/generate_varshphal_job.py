#!/usr/bin/env python3
# scripts/generate_varshphal_job.py
"""
Daily cron job — Varshphal generation and notification dispatch.
Run: 0 6 * * * cd /path/to/antarai && python3 scripts/generate_varshphal_job.py

Steps:
  1. Find users with birthdays in the next DAYS_AHEAD days
  2. Generate their next-year Varshphal + all 12 Mashaphal
  3. Schedule birthday_soon notification
  4. Dispatch any pending notifications (stub — swap print for your push provider)

Requires in .env:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY   (service role bypasses RLS)
"""

import os
import sys
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine.lal_kitab_charts import LalKitabChartGenerator

load_dotenv()

DAYS_AHEAD = 7


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be in .env")
    return create_client(url, key)


def find_upcoming_birthdays(supabase, days_ahead: int) -> list:
    """
    Return [{user_id, chart_id, birth_date}] for users whose birthday (month-day)
    falls within the next N days. Reads from charts table.
    """
    today   = date.today()
    results = []

    charts = (
        supabase.table("charts")
        .select("id, user_id, birth_date")
        .not_.is_("user_id", "null")
        .execute()
    )

    for row in (charts.data or []):
        try:
            bd = datetime.strptime(row["birth_date"], "%Y-%m-%d").date()
        except Exception:
            continue

        try:
            this_year_bday = bd.replace(year=today.year)
        except ValueError:
            this_year_bday = date(today.year, 2, 28)

        next_year_bday = this_year_bday.replace(year=today.year + 1)

        for bday in (this_year_bday, next_year_bday):
            if 0 <= (bday - today).days <= days_ahead:
                results.append({
                    "user_id":   row["user_id"],
                    "chart_id":  row["id"],
                    "birth_date": bd,
                })
                break

    return results


def dispatch_pending_notifications(generator: LalKitabChartGenerator) -> int:
    """
    Mark pending notifications sent.
    TODO: replace print with your push/email/SMS provider.
    """
    pending = generator.get_pending_notifications()
    count   = 0
    for notif in pending:
        try:
            print(
                f"[notify] user={notif['user_id']} "
                f"type={notif['notification_type']} "
                f"data={notif.get('notification_data', {})}"
            )
            generator.mark_notification_sent(notif["id"])
            count += 1
        except Exception as e:
            print(f"[notify error] {notif.get('id')}: {e}")
    return count


def main():
    supabase  = get_supabase()
    generator = LalKitabChartGenerator(supabase)
    today     = date.today()

    print(f"[{today}] Varshphal job starting (days_ahead={DAYS_AHEAD})")

    upcoming  = find_upcoming_birthdays(supabase, DAYS_AHEAD)
    print(f"  Upcoming birthdays: {len(upcoming)}")

    generated = 0
    for entry in upcoming:
        try:
            varshphal = generator.generate_for_birthday(
                entry["user_id"], entry["chart_id"], entry["birth_date"]
            )
            print(f"  + user={entry['user_id']} year={varshphal.get('year')}")
            generated += 1
        except Exception as e:
            print(f"  ! user={entry['user_id']}: {e}")

    print(f"  Generated {generated}/{len(upcoming)}")

    dispatched = dispatch_pending_notifications(generator)
    print(f"  Notifications dispatched: {dispatched}")
    print(f"[{today}] Done")


if __name__ == "__main__":
    main()
