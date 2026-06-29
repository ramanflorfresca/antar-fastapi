"""
Signature Matcher — Surface B: Life Arc
========================================
Scans the forecast horizon month-by-month, runs all enabled signatures
from the SIGNATURE_REGISTRY against each month's dasha/transit state,
and returns predicted events.

Supports dynamic signature library: only signatures with
enabled_in_library=True in their SIGNATURE_METADATA participate.

Author: Antar Engine · April 2026
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from antar_engine import vimsottari, transits, utils, constants


def _now_utc() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)
from antar_engine.life_arc.signatures import (
    wealth_jump, SIGNATURE_REGISTRY, get_enabled_signatures
)


# ─── Transit computation for future dates ────────────────────────────────────

def _get_transit_positions_for_date(target_date: datetime) -> dict:
    """Compute planetary positions for a future date using Swiss Ephemeris."""
    jd = utils.julian_day(target_date)
    return transits.get_current_positions(jd)


def _get_dasha_at_date(
    chart_data: dict, birth_jd: float, target_date: datetime
) -> dict:
    """Get the active MD and AD lords at a given date."""
    result = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
    mds = result["mahadashas"]
    ads = result["antardashas"]

    # Ensure target_date is tz-aware (vimsottari returns tz-aware datetimes)
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=timezone.utc)

    current_md = None
    for md in mds:
        if md["start_datetime"] <= target_date < md["end_datetime"]:
            current_md = md
            break

    current_ad = None
    if current_md:
        for ad in ads:
            if (ad.get("parent_lord") == current_md["lord"]
                    and ad["start_datetime"] <= target_date < ad["end_datetime"]):
                current_ad = ad
                break

    return {
        "md_lord": current_md["lord"] if current_md else None,
        "ad_lord": current_ad["lord"] if current_ad else None,
        "md_end": current_md["end_datetime"] if current_md else None,
        "ad_end": current_ad["end_datetime"] if current_ad else None,
    }


# ─── Window detection ───────────────────────────────────────────────────────

def _find_event_windows(monthly_results: list) -> list:
    """
    Group consecutive months where a signature fires or partially fires
    into event windows.
    """
    windows = []
    current_window = None

    for month_data in monthly_results:
        if month_data["fires"] or month_data["partial"]:
            if current_window is None:
                current_window = {
                    "start": month_data["date"],
                    "months": [month_data],
                    "has_full_fire": month_data["fires"],
                }
            else:
                current_window["months"].append(month_data)
                if month_data["fires"]:
                    current_window["has_full_fire"] = True
        else:
            if current_window is not None:
                current_window["end"] = current_window["months"][-1]["date"]
                windows.append(current_window)
                current_window = None

    # Close any open window
    if current_window is not None:
        current_window["end"] = current_window["months"][-1]["date"]
        windows.append(current_window)

    return windows


def _find_peak_month(months: list) -> str:
    """Find the month with the highest conditions_met score."""
    best = max(months, key=lambda m: m.get("conditions_met", 0))
    return best["date"].strftime("%Y-%m")


def _build_reasoning_public(window: dict, chart_data: dict) -> str:
    """Build user-facing reasoning (backward compat — calls generic with wealth_jump meta)."""
    return _build_reasoning_public_generic(window, chart_data, wealth_jump.SIGNATURE_METADATA)


def _build_reasoning_public_generic(window: dict, chart_data: dict, meta: dict) -> str:
    """Build user-facing reasoning from the window's best month data."""
    best_month = max(window["months"], key=lambda m: m.get("conditions_met", 0))
    parts = []

    # Dasha reasoning
    for d in best_month.get("dasha_match", []):
        parts.append(d)

    # Transit reasoning
    for t in best_month.get("transit_match", []):
        parts.append(t)

    # Historical match — only if we have validation data
    n = meta.get("positive_sample_size", 0)
    rate = meta.get("positive_rate")
    if n and rate:
        pct = int(rate * 100)
        count = int(n * rate)
        parts.append(
            f"Historical pattern match: {count} of {n} charts with identical "
            f"conditions experienced this event in the predicted window."
        )
    elif n:
        parts.append(
            f"Pattern detected across {n} reference charts."
        )
    else:
        parts.append(
            f"This pattern is in early validation (confidence: {meta.get('confidence', 'INDICATIVE')})."
        )

    return " ".join(parts)


def _build_actions(window: dict) -> list:
    """Generate actionable advice (backward compat — calls generic for wealth_jump)."""
    return _build_actions_generic(window, "wealth_jump")


def _build_actions_generic(window: dict, signature_name: str) -> list:
    """Generate actionable advice for a predicted event window."""
    peak = _find_peak_month(window["months"])
    peak_parts = peak.split("-")
    peak_year, peak_month_num = int(peak_parts[0]), int(peak_parts[1])

    # Month before peak
    prep_month = peak_month_num - 2 if peak_month_num > 2 else peak_month_num + 10
    prep_year = peak_year if peak_month_num > 2 else peak_year - 1

    month_names = ["", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    peak_name = ("early–mid " + month_names[peak_month_num]) if 1 <= peak_month_num <= 12 else "Unknown"
    prep_name = ("early–mid " + month_names[prep_month]) if 1 <= prep_month <= 12 else "Unknown"

    # Signature-specific action templates
    actions = _ACTION_TEMPLATES.get(signature_name)
    if actions:
        return [a.format(
            peak_name=peak_name, peak_year=peak_year,
            prep_name=prep_name, prep_year=prep_year
        ) for a in actions]

    # Fallback generic
    return [
        f"Pay attention to this area around {peak_name} {peak_year}",
        f"Start preparing in {prep_name} {prep_year}",
        f"Use this window for important decisions in this domain",
    ]


_ACTION_TEMPLATES = {
    "wealth_jump": [
        "Position for income expansion — negotiate salary, equity, contracts in the 2 months BEFORE peak ({prep_name} {prep_year})",
        "Large investment decisions favored during window",
        "Close pending deals in peak month ({peak_name} {peak_year})",
    ],
    "job_change": [
        "Update your resume and professional profile before {prep_name} {prep_year}",
        "Network actively and explore opportunities — this window favors career moves",
        "If considering a change, aim to finalize around {peak_name} {peak_year}",
    ],
    "marriage": [
        "If in a relationship, this is a favorable window for deepening commitment",
        "Social opportunities peak around {peak_name} {peak_year} — be open to meeting people",
        "Important partnership decisions are supported during this window",
    ],
    "wealth_loss": [
        "Review and strengthen financial safeguards before {prep_name} {prep_year}",
        "Avoid high-risk investments or large financial commitments during this window",
        "Build cash reserves — liquidity is your buffer around {peak_name} {peak_year}",
    ],
}


def _event_label_for(signature_name: str) -> str:
    """Map signature names to user-facing event labels."""
    return {
        "wealth_jump": "Significant income increase",
        "job_change": "Job or career transition",
        "marriage": "Marriage or committed partnership",
        "wealth_loss": "Financial stress window",
    }.get(signature_name, signature_name.replace("_", " ").title())


# ─── Main Entry Point ───────────────────────────────────────────────────────

async def match_signatures(
    chart_data: dict,
    birth_jd: float,
    horizon_months: int = 12,
    signatures_to_check: list = None,
) -> list:
    """
    Scan the horizon month-by-month, check each signature, return predicted events.

    For MVP: only wealth_jump is checked.
    """
    now = _now_utc()

    # Resolve which signatures to check
    if signatures_to_check is not None:
        sig_modules = [
            (name, SIGNATURE_REGISTRY[name])
            for name in signatures_to_check
            if name in SIGNATURE_REGISTRY
        ]
    else:
        sig_modules = get_enabled_signatures()

    predicted_events = []

    for sig_name, sig_module in sig_modules:
        meta = sig_module.SIGNATURE_METADATA

        # Scan each month in the horizon
        monthly_results = []
        for month_offset in range(horizon_months):
            target_date = now + timedelta(days=30 * month_offset)

            # Get dasha state at this month
            dasha_state = _get_dasha_at_date(chart_data, birth_jd, target_date)
            if not dasha_state["md_lord"] or not dasha_state["ad_lord"]:
                continue

            # Get transit positions for this month
            transit_pos = _get_transit_positions_for_date(target_date)

            # Run signature check (all signatures export check_signature)
            result = sig_module.check_signature(
                chart_data,
                dasha_state["md_lord"],
                dasha_state["ad_lord"],
                transit_pos,
            )
            result["date"] = target_date
            result["md_lord"] = dasha_state["md_lord"]
            result["ad_lord"] = dasha_state["ad_lord"]
            monthly_results.append(result)

        # Group into windows
        windows = _find_event_windows(monthly_results)

        for window in windows:
            if not window.get("has_full_fire"):
                continue  # Only report windows where all 3 conditions met at least once

            peak = _find_peak_month(window["months"])
            best = max(window["months"], key=lambda m: m.get("conditions_met", 0))

            event = {
                "signature": meta["name"],
                "signature_version": meta["version"],
                "event_label": meta.get("event_label", _event_label_for(meta["name"])),
                "confidence": meta["confidence"],
                "confidence_metadata": {
                    "signature_version": meta["version"],
                    "positive_sample_size": meta["positive_sample_size"],
                    "positive_rate": meta["positive_rate"],
                    "false_positive_rate": meta["false_positive_rate"],
                },
                "window": {
                    "start": window["start"].strftime("%b %Y"),
                    "end": window["end"].strftime("%b %Y"),
                    "peak_month": peak,
                },
                "reasoning_public": _build_reasoning_public_generic(
                    window, chart_data, meta
                ),
                "reasoning_technical": {
                    "natal_match": best.get("natal_match", []),
                    "dasha_match": best.get("dasha_match", []),
                    "transit_match": best.get("transit_match", []),
                    "missing": best.get("missing", []),
                },
                "actions_during_window": _build_actions_generic(window, meta["name"]),
            }
            predicted_events.append(event)

    return predicted_events
