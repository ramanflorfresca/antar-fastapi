"""
Timeline Builder — Surface B: Life Arc
=======================================
Assembles timeline_visual_data from phase analysis + predicted events.
Output is structured data the frontend can render as a horizontal timeline.

Author: Antar Engine · April 2026
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any


def build_timeline(
    current_phase: dict,
    predicted_events: list,
    horizon_months: int = 12,
    diagnostic: dict = None,
) -> dict:
    """
    Build structured timeline data for frontend rendering.
    Includes phase shift dates, event windows, peak dates.
    """
    now = datetime.now(timezone.utc)
    start_date = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=30 * horizon_months)).strftime("%Y-%m-%d")

    landmarks = []

    # ── Phase shift landmarks from Vimsottari ────────────────────────────
    vim = current_phase.get("vimsottari", {})

    # PD end
    pd_end = vim.get("pd_end_date")
    if pd_end and _is_in_horizon(pd_end, now, horizon_months):
        pd_lord = vim.get("pd", "Unknown")
        landmarks.append({
            "date": pd_end,
            "type": "phase_shift",
            # cyclecontract: planet name + chapter-jargon stripped;
            # date stays — the user still sees "Inner window shifts — YYYY-MM-DD".
            "label": "Inner window shifts",
            "significance": "low",
        })

    # AD end (major shift)
    ad_end = vim.get("ad_end_date")
    if ad_end and _is_in_horizon(ad_end, now, horizon_months):
        ad_lord = vim.get("ad", "Unknown")
        md_lord = vim.get("md", "Unknown")
        landmarks.append({
            "date": ad_end,
            "type": "phase_shift",
            # cyclecontract: drop planet/AD/sub-chapter wording.
            "label": "A new stretch begins",
            "significance": "high",
        })

    # MD end (if in horizon — rare but possible)
    md_end = vim.get("md_end_date")
    if md_end and _is_in_horizon(md_end, now, horizon_months):
        md_lord = vim.get("md", "Unknown")
        landmarks.append({
            "date": md_end,
            "type": "phase_shift",
            # cyclecontract: drop planet name; "major chapter" wording is fine.
            "label": "A major chapter closes",
            "significance": "critical",
        })

    # ── Diagnostic next phase shift ──────────────────────────────────────
    if diagnostic:
        nps = diagnostic.get("next_phase_shift", {})
        nps_date = nps.get("date")
        if nps_date and _is_in_horizon(nps_date, now, horizon_months):
            # Check if we already have this date (avoid duplicate with AD end)
            existing_dates = {l["date"] for l in landmarks}
            if nps_date not in existing_dates:
                landmarks.append({
                    "date": nps_date,
                    "type": "phase_shift",
                    "label": nps.get("label", "Phase shift"),
                    "significance": "high",
                })

    # ── Event window landmarks ───────────────────────────────────────────
    for event in predicted_events:
        window = event.get("window", {})
        w_start = window.get("start")
        w_end = window.get("end")
        peak = window.get("peak_month")
        label = event.get("event_label", "Predicted event")

        if w_start and _is_in_horizon(w_start, now, horizon_months):
            landmarks.append({
                "date": w_start,
                "type": "event_window_start",
                "label": f"{label} window opens",
                "significance": "medium",
            })

        if peak:
            peak_date = f"{peak}-01"
            if _is_in_horizon(peak_date, now, horizon_months):
                landmarks.append({
                    "date": peak_date,
                    "type": "event_peak",
                    "label": f"{label} peak probability",
                    "significance": "high",
                })

        if w_end and _is_in_horizon(w_end, now, horizon_months):
            landmarks.append({
                "date": w_end,
                "type": "event_window_end",
                "label": f"{label} window closes",
                "significance": "low",
            })

    # Sort by date
    landmarks.sort(key=lambda l: l["date"])

    return {
        "start": start_date,
        "end": end_date,
        "landmarks": landmarks,
    }


def _is_in_horizon(date_str: str, now: datetime, horizon_months: int) -> bool:
    """Check if a date string falls within the forecast horizon."""
    try:
        target = datetime.strptime(date_str[:10], "%Y-%m-%d")
        # Strip tz from now for comparison with naive parsed dates
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        horizon_end = now_naive + timedelta(days=30 * horizon_months)
        return now_naive <= target <= horizon_end
    except (ValueError, TypeError):
        return False
