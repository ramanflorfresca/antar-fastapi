"""
ANTAR — Verification Engine
Sprint 1.4: Generates verification questions from chart history

Scans the user's dasha transitions and planetary periods to generate
binary (YES/NO) questions about past life events. When the user confirms,
their Precision Score levels up, creating sunk-cost credibility.

Usage:
    from antar_engine.verification_engine import generate_verification_queue
    queue = await generate_verification_queue(chart_id, supabase_client)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# DASHA TRANSITION → LIFE EVENT MAPPING
# Each dasha transition maps to a predictable life theme shift
# ═══════════════════════════════════════════════════════════════════

DASHA_EVENT_MAP = {
    # Mahadasha transitions — major life chapter shifts
    "Sun": {
        "start_event": "authority_shift",
        "question_template": "System detected an Authority Shift around {date}. Did your role, status, or public visibility change?",
        "options": ["Promotion/New Role", "Public Recognition", "Leadership Change", "Nothing Happened"],
        "domain": "career",
    },
    "Moon": {
        "start_event": "emotional_reset",
        "question_template": "System detected an Emotional Reset around {date}. Did you experience a major change in your home life, mood, or inner world?",
        "options": ["Relocation/Move", "Family Change", "Emotional Shift", "Nothing Happened"],
        "domain": "relationship",
    },
    "Mars": {
        "start_event": "action_surge",
        "question_template": "System detected an Action Surge around {date}. Did you start something bold — a business, project, or physical challenge?",
        "options": ["New Venture", "Major Decision", "Physical Challenge", "Nothing Happened"],
        "domain": "career",
    },
    "Mercury": {
        "start_event": "communication_pivot",
        "question_template": "System detected a Communication Pivot around {date}. Did your work, skills, or primary mode of expression change?",
        "options": ["Skill Upgrade", "New Role/Industry", "Business Pivot", "Nothing Happened"],
        "domain": "career",
    },
    "Jupiter": {
        "start_event": "expansion_wave",
        "question_template": "System detected a Growth Expansion around {date}. Did you experience a windfall, opportunity, or major gain?",
        "options": ["Financial Gain", "New Opportunity", "Education/Growth", "Nothing Happened"],
        "domain": "wealth",
    },
    "Venus": {
        "start_event": "magnetism_shift",
        "question_template": "System detected a Magnetism Shift around {date}. Did your key relationship, lifestyle, or creative expression change?",
        "options": ["New Relationship", "Lifestyle Upgrade", "Creative Shift", "Nothing Happened"],
        "domain": "relationship",
    },
    "Saturn": {
        "start_event": "structural_pressure",
        "question_template": "System detected Structural Pressure around {date}. Did you face a career setback, health issue, or forced restructuring?",
        "options": ["Career Setback", "Health Issue", "Financial Restructure", "Nothing Happened"],
        "domain": "career",
    },
    "Rahu": {
        "start_event": "ambition_disruption",
        "question_template": "System detected an Ambition Disruption around {date}. Did you face an unexpected change — obsessive new goal, industry shift, or foreign connection?",
        "options": ["Industry/Role Pivot", "Foreign Connection", "Obsessive New Goal", "Nothing Happened"],
        "domain": "career",
    },
    "Ketu": {
        "start_event": "release_event",
        "question_template": "System detected a Release Event around {date}. Did you let go of something major — a job, relationship, belief, or possession?",
        "options": ["Left a Job", "Ended Relationship", "Spiritual Shift", "Nothing Happened"],
        "domain": "general",
    },
}

# Antardasha (sub-period) transitions — more specific events
ANTARDASHA_EVENT_MAP = {
    "Saturn-Saturn": {
        "question_template": "System detected Deep Structural Pressure around {date}. Did you face a prolonged challenge — career stall, health grind, or forced patience?",
        "options": ["Career Stall", "Health Challenge", "Financial Pressure", "Nothing Happened"],
        "domain": "career",
    },
    "Rahu-Saturn": {
        "question_template": "System detected an Ambition-Structure Collision around {date}. Did your big ambition hit a wall — regulatory block, funding freeze, or forced slowdown?",
        "options": ["Funding Block", "Regulatory Issue", "Forced Pivot", "Nothing Happened"],
        "domain": "wealth",
    },
    "Mars-Moon": {
        "question_template": "System detected an Action-Emotion Clash around {date}. Did you face a conflict between what you wanted to do and what you felt?",
        "options": ["Work-Life Conflict", "Aggressive Decision", "Emotional Breakthrough", "Nothing Happened"],
        "domain": "relationship",
    },
    "Jupiter-Venus": {
        "question_template": "System detected a Growth-Magnetism Peak around {date}. Did something good happen — a windfall, new relationship, or lifestyle upgrade?",
        "options": ["Financial Windfall", "New Relationship", "Lifestyle Upgrade", "Nothing Happened"],
        "domain": "wealth",
    },
    "Venus-Saturn": {
        "question_template": "System detected Relationship Pressure around {date}. Did you face a commitment test — marriage stress, partnership renegotiation, or delayed gratification?",
        "options": ["Partnership Strain", "Commitment Decision", "Delayed Reward", "Nothing Happened"],
        "domain": "relationship",
    },
    "Moon-Venus": {
        "question_template": "System detected Emotional-Creative Peak around {date}. Did you experience heightened emotional sensitivity, creative inspiration, or romantic intensity?",
        "options": ["Creative Breakthrough", "Romantic Intensity", "Emotional Sensitivity", "Nothing Happened"],
        "domain": "relationship",
    },
}


# ═══════════════════════════════════════════════════════════════════
# VERIFICATION QUEUE GENERATOR
# ═══════════════════════════════════════════════════════════════════

async def generate_verification_queue(
    chart_id: str,
    supabase,
    max_questions: int = 5,
    lookback_years: int = 10
) -> List[Dict]:
    """
    Generate a verification queue of past events for the user to confirm.
    
    Queries the dasha_periods table for this chart, finds past transitions,
    and generates binary verification questions.
    
    Args:
        chart_id: UUID of the chart
        supabase: Supabase client instance
        max_questions: Maximum questions to return (default 5)
        lookback_years: How far back to look (default 10 years)
        
    Returns:
        List of verification question dicts, each with:
        - question: str (the question text)
        - options: List[str] (possible answers)
        - domain: str (life domain)
        - event_type: str (dasha transition type)
        - event_date: str (approximate date)
        - dasha_period: str (e.g., "Saturn-Saturn")
    """
    queue = []
    now = datetime.utcnow()
    cutoff = now - timedelta(days=lookback_years * 365)
    
    try:
        # Fetch dasha periods for this chart
        result = supabase.table("dasha_periods").select(
            "planet_or_sign, start_date, end_date, level"
        ).eq("chart_id", chart_id).eq(
            "system", "vimsottari"
        ).gte("start_date", cutoff.isoformat()).lte(
            "start_date", now.isoformat()
        ).order("start_date", desc=True).execute()
        
        if not result.data:
            logger.info(f"No dasha periods found for chart {chart_id}")
            return _generate_fallback_queue(chart_id)
        
        periods = result.data
        
        # Also check which predictions have already been rated
        rated_result = supabase.table("predictions").select(
            "id, accuracy_rating"
        ).eq("chart_id", chart_id).not_.is_(
            "accuracy_rating", "null"
        ).execute()
        
        total_rated = len(rated_result.data) if rated_result.data else 0
        
        # Group by level: 1 = Mahadasha, 2 = Antardasha
        mahadashas = [p for p in periods if p.get("level") == 1]
        antardashas = [p for p in periods if p.get("level") == 2]
        
        # Generate questions from Mahadasha transitions
        for md in mahadashas:
            planet = md.get("planet_or_sign", "").strip()
            start_date = md.get("start_date", "")
            
            if planet in DASHA_EVENT_MAP:
                event = DASHA_EVENT_MAP[planet]
                date_str = _format_event_date(start_date)
                
                if date_str:
                    queue.append({
                        "question": event["question_template"].format(date=date_str),
                        "options": event["options"],
                        "domain": event["domain"],
                        "event_type": event["start_event"],
                        "event_date": date_str,
                        "dasha_period": planet,
                        "level": "major",
                        "source": "mahadasha_transition",
                    })
        
        # Generate questions from Antardasha transitions
        for ad in antardashas:
            planet = ad.get("planet_or_sign", "").strip()
            start_date = ad.get("start_date", "")
            
            # Build combined key (e.g., "Saturn-Saturn" or "Rahu-Mars")
            # The planet_or_sign for level 2 should be the sub-period planet
            # We need to find its parent mahadasha
            parent_md = _find_parent_mahadasha(ad, mahadashas)
            if parent_md:
                combined = f"{parent_md.get('planet_or_sign', '').strip()}-{planet}"
                
                if combined in ANTARDASHA_EVENT_MAP:
                    event = ANTARDASHA_EVENT_MAP[combined]
                    date_str = _format_event_date(start_date)
                    
                    if date_str:
                        queue.append({
                            "question": event["question_template"].format(date=date_str),
                            "options": event["options"],
                            "domain": event["domain"],
                            "event_type": f"antardasha_{combined.lower()}",
                            "event_date": date_str,
                            "dasha_period": combined,
                            "level": "specific",
                            "source": "antardasha_transition",
                        })
        
        # Deduplicate and sort (specific before major, recent first)
        seen_dates = set()
        unique_queue = []
        for q in queue:
            date_key = q["event_date"][:7]  # YYYY-MM
            if date_key not in seen_dates:
                seen_dates.add(date_key)
                unique_queue.append(q)
        
        # Sort: specific events first, then recent first
        unique_queue.sort(key=lambda q: (
            0 if q["level"] == "specific" else 1,
            q["event_date"]
        ), reverse=False)
        
        # Brief B — drop items the user has already rated via
        # POST /verification/{chart_id}/rate so the queue shrinks as they rate.
        _rated_rows = _fetch_verification_ratings(chart_id, supabase)
        if _rated_rows:
            _rated_keys = {
                (r.get("event_type"), r.get("event_date")) for r in _rated_rows
            }
            unique_queue = [
                q for q in unique_queue
                if (q.get("event_type"), q.get("event_date")) not in _rated_keys
            ]
            total_rated += len(_rated_rows)

        # Add metadata
        for q in unique_queue:
            q["total_rated"] = total_rated
            q["current_level"] = max(1, min(10, total_rated // 2 + 1))
            q["next_level"] = q["current_level"] + 1
            q["verifications_needed"] = max(0, (q["current_level"] * 2) - total_rated)
        
        return unique_queue[:max_questions]
        
    except Exception as e:
        logger.error(f"Verification queue generation failed: {e}")
        return _generate_fallback_queue(chart_id)


def _find_parent_mahadasha(antardasha: dict, mahadashas: list) -> Optional[dict]:
    """Find the parent Mahadasha for a given Antardasha based on date range."""
    ad_start = antardasha.get("start_date", "")
    
    for md in mahadashas:
        md_start = md.get("start_date", "")
        md_end = md.get("end_date", "")
        
        if md_start and md_end and ad_start:
            if md_start <= ad_start <= md_end:
                return md
    
    return None


def _format_event_date(date_str: str) -> Optional[str]:
    """Format a date string to 'Month YYYY' for display."""
    if not date_str:
        return None
    
    try:
        if isinstance(date_str, str):
            # Handle various formats
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f",
                       "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%S.%f+00:00"]:
                try:
                    dt = datetime.strptime(date_str[:len(fmt.replace('%', 'X'))], fmt)
                    return dt.strftime("%B %Y")
                except (ValueError, IndexError):
                    continue
            # Last resort: try just the date part
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00").split("+")[0].split("T")[0])
            return dt.strftime("%B %Y")
        return None
    except Exception:
        return None


def _generate_fallback_queue(chart_id: str) -> List[Dict]:
    """
    Generate a basic fallback queue when dasha data isn't available.
    Uses generic life-stage questions based on common transition points.
    """
    now = datetime.utcnow()
    
    fallback = [
        {
            "question": f"System detected a Career Shift around {(now - timedelta(days=730)).strftime('%B %Y')}. Did your professional situation change significantly?",
            "options": ["Job Change", "Promotion", "New Business", "Nothing Major"],
            "domain": "career",
            "event_type": "generic_career",
            "event_date": (now - timedelta(days=730)).strftime("%Y-%m"),
            "dasha_period": "unknown",
            "level": "general",
            "source": "fallback",
            "total_rated": 0,
            "current_level": 1,
            "next_level": 2,
            "verifications_needed": 2,
        },
        {
            "question": f"System detected Financial Turbulence around {(now - timedelta(days=365)).strftime('%B %Y')}. Did you experience a significant financial event?",
            "options": ["Income Change", "Major Expense", "Investment Event", "Nothing Major"],
            "domain": "wealth",
            "event_type": "generic_wealth",
            "event_date": (now - timedelta(days=365)).strftime("%Y-%m"),
            "dasha_period": "unknown",
            "level": "general",
            "source": "fallback",
            "total_rated": 0,
            "current_level": 1,
            "next_level": 2,
            "verifications_needed": 2,
        },
        {
            "question": f"System detected a Relationship Transition around {(now - timedelta(days=540)).strftime('%B %Y')}. Did a key relationship change?",
            "options": ["New Relationship", "Breakup/Separation", "Deepening Bond", "Nothing Major"],
            "domain": "relationship",
            "event_type": "generic_relationship",
            "event_date": (now - timedelta(days=540)).strftime("%Y-%m"),
            "dasha_period": "unknown",
            "level": "general",
            "source": "fallback",
            "total_rated": 0,
            "current_level": 1,
            "next_level": 2,
            "verifications_needed": 2,
        },
    ]
    
    return fallback


# ═══════════════════════════════════════════════════════════════════
# PRECISION SCORE CALCULATOR
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# VERIFICATION RATINGS STORE  (Brief B, Issue 1)
# Queue items are generated dynamically and carry no row id, so ratings
# are keyed by (chart_id, event_type, event_date) in verification_ratings.
# Migration SQL lives in patch_b1.py's docstring.
# ═══════════════════════════════════════════════════════════════════

def _fetch_verification_ratings(chart_id, supabase):
    """
    Return verification_ratings rows for a chart.
    Defensive: returns [] if the table does not exist yet (pre-migration).
    """
    try:
        res = supabase.table("verification_ratings").select(
            "event_type, event_date, accuracy_rating"
        ).eq("chart_id", chart_id).execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"verification_ratings fetch failed (table may be missing): {e}")
        return []


def store_verification_rating(chart_id, event_type, event_date,
                              domain, dasha_period, accuracy_rating, supabase):
    """
    Upsert a verification-queue rating.
    Idempotent on (chart_id, event_type, event_date) — re-rating overwrites.
    """
    from datetime import datetime, timezone
    row = {
        "chart_id": chart_id,
        "event_type": event_type,
        "event_date": event_date,
        "domain": domain or None,
        "dasha_period": dasha_period or None,
        "accuracy_rating": int(accuracy_rating),
        "rated_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("verification_ratings").upsert(
        row, on_conflict="chart_id,event_type,event_date"
    ).execute()
    return row


async def calculate_precision_score(chart_id: str, supabase) -> Dict:
    """
    Calculate the user's Precision Score based on verified predictions.
    
    Returns:
        {
            "level": 3,
            "level_display": "3.1",  # includes micro-ticks from calibration
            "total_rated": 6,
            "total_accurate": 5,
            "accuracy_pct": 83,
            "next_level_in": 2,  # verifications needed
            "max_level": 10
        }
    """
    try:
        result = supabase.table("predictions").select(
            "accuracy_rating"
        ).eq("chart_id", chart_id).not_.is_(
            "accuracy_rating", "null"
        ).execute()
        
        _ver_rows = _fetch_verification_ratings(chart_id, supabase)
        if not result.data and not _ver_rows:
            return {
                "level": 1,
                "level_display": "1",
                "total_rated": 0,
                "total_accurate": 0,
                "accuracy_pct": 0,
                "next_level_in": 2,
                "max_level": 10,
            }
        
        _pred_rows = result.data or []
        total_rated = len(_pred_rows) + len(_ver_rows)
        total_accurate = (
            sum(1 for r in _pred_rows if r.get("accuracy_rating") == 1)
            + sum(1 for r in _ver_rows if r.get("accuracy_rating") == 1)
        )
        accuracy_pct = round((total_accurate / total_rated) * 100) if total_rated > 0 else 0
        
        level = min(10, total_rated // 2 + 1)
        remainder = total_rated % 2
        level_display = f"{level}.{remainder * 5}" if remainder else str(level)
        
        next_level_in = max(0, ((level) * 2) - total_rated)
        
        return {
            "level": level,
            "level_display": level_display,
            "total_rated": total_rated,
            "total_accurate": total_accurate,
            "accuracy_pct": accuracy_pct,
            "next_level_in": next_level_in,
            "max_level": 10,
        }
        
    except Exception as e:
        logger.error(f"Precision score calculation failed: {e}")
        return {
            "level": 1,
            "level_display": "1",
            "total_rated": 0,
            "total_accurate": 0,
            "accuracy_pct": 0,
            "next_level_in": 2,
            "max_level": 10,
        }


# ═══════════════════════════════════════════════════════════════════
# API ENDPOINT HELPER
# ═══════════════════════════════════════════════════════════════════

async def get_verification_data(chart_id: str, supabase) -> Dict:
    """
    Combined helper for the frontend — returns both queue and score.
    Wire this to: GET /api/v1/verification/{chart_id}
    """
    queue = await generate_verification_queue(chart_id, supabase)
    score = await calculate_precision_score(chart_id, supabase)
    
    return {
        "verification_queue": queue,
        "precision_score": score,
        "has_pending": len(queue) > 0,
        "message": f"Confirm {score['next_level_in']} more events to reach Level {min(10, score['level'] + 1)}." if score['next_level_in'] > 0 else "Maximum precision reached.",
    }
