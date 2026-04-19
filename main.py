#Antar Backend API
# Updated: full DKP + i18n + predictions integration + conversation memory
# ─────────────────────────────────────────────────────────────────────

import os
import uuid
from contextlib import asynccontextmanager
import json
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import AsyncOpenAI

# Antar engine modules
from antar_engine import chart, vimsottari, jaimini, ashtottari, utils, constants
from antar_engine.karakas import psychological_profile, get_all_karakas
from antar_engine import transits, divisional, timing_engine, nation_engine, remedy_selector
from antar_engine.natal_signatures import ensure_signatures, build_signature_context_block, compute_natal_signatures, derive_archetype
from antar_engine.country_context import get_country_context

# New modules
from antar_engine.plain_english import generate_plain_english
from antar_engine.desh_kal_patra import get_dkp_context
from antar_engine.pattern_memory import build_pattern_memory
from antar_engine.common_sense import build_common_sense_block
from antar_engine.welcome_signal import generate_welcome_signal, get_welcome_signal
from antar_engine.weekly_briefing import generate_weekly_briefing
from antar_engine.monthly_deepdive import generate_monthly_deepdive
from antar_engine.annual_planning import generate_annual_plan

from antar_engine.predictions import (
    build_layered_predictions,
    predictions_to_context_block,
    detect_concern,
)

# Use richer detect_concern from astrological_rules if available
try:
    from antar_engine.astrological_rules import detect_concern as _rules_detect_concern
    detect_concern = _rules_detect_concern
except ImportError:
    pass

load_dotenv(override=False)

from timezonefinder import TimezoneFinder
_TZF = TimezoneFinder()

# ══════════════════════════════════════════════════════════════════
# DOMAIN AUDIT RULES (Sprint D) - Complete
# Injected into /predict system prompt based on detected concern.
# Forces Claude to check SPECIFIC houses and divisional charts.
# ══════════════════════════════════════════════════════════════════

DOMAIN_AUDIT_RULES = {

    "finance": (
        "DOMAIN AUDIT - FUNDING / CAPITAL / FINANCE:\n"
        "You MUST check these specific chart elements and report findings:\n\n"
        "1. PRIMARY CHECK - 8th House (other people's money, funding, loans):\n"
        "   - Who is the 8th House Lord? What house is it sitting in?\n"
        "   - Is any planet currently transiting the 8th house?\n"
        "   - Is the 8th house activated in the current Antardasha?\n\n"
        "2. GAINS CHECK - 11th House (income, gains, fulfillment of desires):\n"
        "   - Who is the 11th House Lord? What house is it sitting in?\n"
        "   - Is the 11th house activated in the current dasha period?\n"
        "   - Any benefic aspects on 11th house?\n\n"
        "3. WEALTH CHECK - 2nd House (accumulated wealth, cash flow):\n"
        "   - Who is the 2nd House Lord? Status - strong, weak, combust?\n"
        "   - Any Dhana Yogas (wealth combinations) active?\n\n"
        "4. CAREER DIVISIONAL - D-10 (Dashamsha):\n"
        "   - Are the Artha houses (2, 6, 10) in D-10 supported?\n"
        "   - Is the D-10 lagna lord strong?\n\n"
        "5. JAIMINI CHECK:\n"
        "   - Where is Amatyakaraka (career significator) placed?\n"
        "   - Is Amatyakaraka in 6/8/12 from current Jaimini Chara Dasha sign?\n"
        "   - If yes = CAREER ENERGY MISALIGNED - report this.\n\n"
        "6. LAL KITAB CHECK:\n"
        "   - Are 8th or 11th houses Sleeping per Lal Kitab?\n"
        "   - If sleeping = BLOCKAGE - report what remedy awakens it.\n"
        "   - What does the Varshphal show for wealth houses?\n"
        "   - Does Muntha or Year Lord occupy 2nd, 8th, or 11th house?\n\n"
        "7. TIMING VERDICT:\n"
        "   - 8th+11th both supported = funding ACTIVE, give specific month\n"
        "   - 8th inactive + Varshphal neutral = funding BLOCKED, say when it unblocks\n"
        "   - 11th active + 8th weak = revenue yes, outside capital no\n"
        "   - AmK in 6/8/12 from dasha = realign positioning first\n"
        "   DO NOT give vague answers. Give a VERDICT based on the data."
    ),

    "career": (
        "DOMAIN AUDIT - CAREER / BUSINESS / PROFESSIONAL:\n"
        "Check: 10th House lord and placement, D-10 lagna lord strength,\n"
        "Amatyakaraka position, 6th house (competition), Sun strength,\n"
        "current dasha lord relationship to 10th, Lal Kitab sleeping planets in 10th,\n"
        "Varshphal year lord in career houses. Give specific timing for career activation."
    ),

    "foreign": (
        "DOMAIN AUDIT - FOREIGN SETTLEMENT AND TRAVEL:\n"
        "PROTOCOL: VELOCITY AUDIT\n\n"
        "1. 4th HOUSE (Home) INTEGRITY:\n"
        "   - Is the 4th Lord in the 6th, 8th, or 12th house?\n"
        "   - Is it afflicted by Rahu or Saturn?\n"
        "   - Affliction = weakening of ties to birthplace.\n\n"
        "2. 12th HOUSE (Foreign Residence) ACTIVATION:\n"
        "   - Is the 12th Lord active in the current Vimsottari Dasha?\n"
        "   - Any connection between 9th Lord (long travel) and 12th Lord?\n\n"
        "3. RAHU/MOON ALIGNMENT:\n"
        "   - Is Rahu or Moon in 7th, 9th, or 12th house?\n\n"
        "4. VERDICT:\n"
        "   - 4th stable + 12th dormant = STAY\n"
        "   - 4th afflicted + 12th/9th active = FLIGHT PATH CLEAR\n"
        "   Give specific month when the travel/settlement window opens."
    ),

    "relationship": (
        "DOMAIN AUDIT - RELATIONSHIP AND MARRIAGE:\n"
        "PROTOCOL: D-9 ENGINE DIAGNOSTIC\n\n"
        "1. D-1 BASELINE: 7th House Lord current strength and transit position.\n\n"
        "2. D-9 (Navamsha) AUDIT:\n"
        "   - Compare D-1 7th Lord position in D-9 chart.\n"
        "   - If it falls in D-9 6th, 8th, or 12th = INTERNAL FRICTION.\n\n"
        "3. VENUS/JUPITER STATUS:\n"
        "   - Venus (for men) or Jupiter (for women) - combust? Under Saturn aspect?\n\n"
        "4. DARAKARAKA: Which planet? Where placed? Strength?\n\n"
        "5. UPAPADA LAGNA: Sign, lord, planets there.\n\n"
        "6. VERDICT:\n"
        "   Do not predict love. Predict SYNC QUALITY.\n"
        "   e.g. 7th House active but D-9 Engine in recovery = delays until [Date]."
    ),

    "entrepreneurship": (
        "DOMAIN AUDIT - NEW BUSINESS / ENTREPRENEURSHIP:\n"
        "PROTOCOL: INDEPENDENCE AUDIT\n\n"
        "1. D-10: Is the 1st House (self-reliance) stronger than 7th (partnership)?\n\n"
        "2. ARTHA TRIAD: Scan 2nd, 6th, 10th houses in D-10 for Rahu or Mars.\n\n"
        "3. JAIMINI: Is Amatyakaraka in a sign currently undergoing Chara Dasha?\n\n"
        "4. VERDICT:\n"
        "   - D-10 1st Lord weak = STAY IN EMPLOYMENT\n"
        "   - 7th/10th Lords converging in Dasha = LAUNCH WINDOW OPEN\n"
        "   Give specific month for the launch window."
    ),

    "job_change": (
        "DOMAIN AUDIT - JOB CHANGE AND PROMOTION:\n"
        "PROTOCOL: VERTICAL RISE AUDIT\n\n"
        "1. 6th vs 10th BALANCE: 6th House (daily service) vs 10th House (authority).\n\n"
        "2. D-10 VITALS: Is current Antardasha lord well-placed in D-10?\n"
        "   If in 3rd, 6th, 10th, or 11th from D-10 Lagna = PROMOTION/GAIN.\n\n"
        "3. SATURN/SUN TRANSIT:\n"
        "   - Saturn hitting 10th = heavy workload\n"
        "   - Sun hitting 10th = recognition\n\n"
        "4. VERDICT:\n"
        "   Give specific date for vertical move window.\n"
        "   Until then specify steady cruise or preparation mode."
    ),

    "property": (
        "DOMAIN AUDIT - CHANGE OF RESIDENCE / PROPERTY:\n"
        "PROTOCOL: D-4 LOCATION SENSOR\n\n"
        "1. 3rd/4th HOUSE TRIGGER: Connection between 3rd Lord and 4th Lord.\n\n"
        "2. D-4 (Chaturthamsa) AUDIT: Is D-1 4th Lord in a movable sign in D-4?\n\n"
        "3. MARS/SATURN TRANSIT: Mars or Saturn hitting 4th house?\n\n"
        "4. VERDICT:\n"
        "   Give specific month when location sensor is triggered.\n"
        "   Specify upgrade vs relocation vs avoid fixed commitments."
    ),

    "legal": (
        "DOMAIN AUDIT - LEGAL, DISPUTES AND COMPETITION:\n"
        "PROTOCOL: VICTORY SENSOR (6th HOUSE)\n\n"
        "1. 6th HOUSE AUDIT:\n"
        "   - Check strength of 6th Lord. Is it in 6th, 8th, or 12th?\n"
        "   - Placement in 8/12 suggests winning through loss or hidden settlements.\n\n"
        "2. MARS/SATURN INFLUENCE:\n"
        "   - Is Mars (victory) or Saturn (justice/delay) aspecting the 6th house?\n\n"
        "3. D-6 (Shashtamsa) CHECK:\n"
        "   - 6th Lord exalted in D-6 = VICTORY THROUGH STRATEGY.\n\n"
        "4. VERDICT:\n"
        "   Give specific date when settlement signal activates.\n"
        "   If Saturn aspect active = delays until Saturn releases."
    ),

    "health_audit": (
        "DOMAIN AUDIT - HEALTH AND VITALITY:\n"
        "PROTOCOL: ENGINE COOLING AUDIT\n\n"
        "1. LAGNA LORD STATUS:\n"
        "   - Is 1st Lord currently combust or in a Maraka house (2nd/7th)?\n\n"
        "2. 8th HOUSE CHECK:\n"
        "   - Is current Antardasha lord placed in the 8th house?\n"
        "   - 8th house activation = internal maintenance required.\n\n"
        "3. SUN/MOON VITALS:\n"
        "   - Sun (physical energy) and Moon (mental clarity) under Rahu/Ketu pressure?\n\n"
        "4. VERDICT:\n"
        "   If Lagna lord weak + 8th active = low-vitality window until [Date].\n"
        "   Specify what to avoid during this cycle. Give date when vitality returns."
    ),

    "real_estate_audit": (
        "DOMAIN AUDIT - REAL ESTATE AND FIXED ASSETS:\n"
        "PROTOCOL: ASSET ACQUISITION SENSOR\n\n"
        "1. 4th HOUSE INTEGRITY: Is 4th Lord connected to 11th or 2nd Lord?\n\n"
        "2. MARS STATUS: Strength check. Retrograde = construction delays.\n\n"
        "3. D-4 ENGINE: 4th Lord of D-1 in D-4 Upachaya (3,6,10,11) = GROWTH.\n\n"
        "4. VERDICT:\n"
        "   - Connected + Mars strong = PURCHASE WINDOW OPEN\n"
        "   - Friction + Mars weak = window CLOSED until [Date]"
    ),

    "children": (
        "DOMAIN AUDIT - CHILDREN AND CREATIVITY:\n"
        "PROTOCOL: LEGACY/PROGENY AUDIT\n\n"
        "1. 5th HOUSE: Lord in fertile sign (Water/Earth) or dry (Fire/Air)?\n\n"
        "2. D-7 (Saptamsha): Check Jupiter and 9th Lord alignment in D-7.\n\n"
        "3. JUPITER TRANSIT: In 1st, 5th, or 9th house = GREEN LIGHT.\n\n"
        "4. VERDICT:\n"
        "   Jupiter in 1/5/9 + 5th fertile + D-7 supported = FERTILE WINDOW.\n"
        "   Give specific month when creation window peaks."
    ),

    "health": (
        "DOMAIN AUDIT - HEALTH:\n"
        "Check: Lagna lord strength (vitality), 6th house (disease), 8th house (chronic),\n"
        "Sun and Mars strength, current dasha lord natural signification,\n"
        "age-specific Umra vulnerabilities, Lal Kitab sleeping planets in 1/6/8."
    ),

    "general": (
        "DOMAIN AUDIT - GENERAL:\n"
        "Scan ALL major houses. Find the ONE area with highest activation in current dasha.\n"
        "Check D-10 for career, D-9 for relationships, D-2 for wealth.\n"
        "Find the sharpest signal and go deep on that single area."
    ),
}

# Domain aliases
DOMAIN_AUDIT_RULES["wealth"] = DOMAIN_AUDIT_RULES["finance"]
DOMAIN_AUDIT_RULES["funding"] = DOMAIN_AUDIT_RULES["finance"]
DOMAIN_AUDIT_RULES["business"] = DOMAIN_AUDIT_RULES["career"]
DOMAIN_AUDIT_RULES["startup"] = DOMAIN_AUDIT_RULES["finance"]
DOMAIN_AUDIT_RULES["travel"] = DOMAIN_AUDIT_RULES["foreign"]
DOMAIN_AUDIT_RULES["abroad"] = DOMAIN_AUDIT_RULES["foreign"]
DOMAIN_AUDIT_RULES["immigration"] = DOMAIN_AUDIT_RULES["foreign"]
DOMAIN_AUDIT_RULES["marriage"] = DOMAIN_AUDIT_RULES["relationship"]
DOMAIN_AUDIT_RULES["love"] = DOMAIN_AUDIT_RULES["relationship"]
DOMAIN_AUDIT_RULES["promotion"] = DOMAIN_AUDIT_RULES["job_change"]
DOMAIN_AUDIT_RULES["job"] = DOMAIN_AUDIT_RULES["job_change"]
DOMAIN_AUDIT_RULES["house"] = DOMAIN_AUDIT_RULES["property"]
DOMAIN_AUDIT_RULES["relocation"] = DOMAIN_AUDIT_RULES["property"]
DOMAIN_AUDIT_RULES["dispute"] = DOMAIN_AUDIT_RULES["legal"]
DOMAIN_AUDIT_RULES["court"] = DOMAIN_AUDIT_RULES["legal"]
DOMAIN_AUDIT_RULES["competition"] = DOMAIN_AUDIT_RULES["legal"]
DOMAIN_AUDIT_RULES["fertility"] = DOMAIN_AUDIT_RULES["children"]
DOMAIN_AUDIT_RULES["creativity"] = DOMAIN_AUDIT_RULES["children"]
DOMAIN_AUDIT_RULES["pregnancy"] = DOMAIN_AUDIT_RULES["children"]

# ── COMPATIBILITY AUDIT RULES ─────────────────────────────────────
COMPATIBILITY_AUDIT_RULES = {

    "business_partnership": (
        "COMPATIBILITY AUDIT - STARTUP AND BUSINESS PARTNERSHIP:\n"
        "PROTOCOL: CONVERGENCE AUDIT (D-1 and D-10)\n\n"
        "1. DASHA ALIGNMENT:\n"
        "   - Do both partners have 10th or 11th House activation in next 24 months?\n"
        "   - If Partner A is in Growth dasha but Partner B is in Loss/8th dasha = bleed.\n\n"
        "2. 7th HOUSE LINK:\n"
        "   - Does Partner A 7th Lord sit in a friendly house in Partner B chart?\n\n"
        "3. D-10 POWER:\n"
        "   - Sun/Mars strength = CEO. Saturn/Mercury = Operations.\n"
        "   - If roles complement = Functional Sync HIGH.\n\n"
        "4. VERDICT:\n"
        "   Report Operational Sync percentage. Flag timing mismatches with specific quarter."
    ),

    "romantic": (
        "COMPATIBILITY AUDIT - ROMANTIC AND MARRIAGE SYNC:\n"
        "PROTOCOL: VITALITY AND VIBE SYNC (D-1 and D-9)\n\n"
        "1. MOON/MIND SYNC: Moon signs in 6/8 or 12/2 = communication friction.\n\n"
        "2. D-9 ENGINE MATCH:\n"
        "   - 7th Lord of Partner A in Partner B D-9 hitting Lagna or 5/9 = deep.\n\n"
        "3. MARS/VENUS BATTERY: Manglik imbalance check.\n\n"
        "4. VERDICT:\n"
        "   Report Emotional Sync, Structural Sync (D-9), Engine Compatibility.\n"
        "   Never use soulmate. Use Operational Alignment."
    ),

    "investor": (
        "COMPATIBILITY AUDIT - INVESTOR / FUNDING SYNC:\n"
        "PROTOCOL: CAPITAL FLOW AUDIT (8th and 11th)\n\n"
        "1. 8th HOUSE BRIDGE: Investor 11th Lord aspects Founder 8th House = green light.\n\n"
        "2. AUTHORITY CONFLICT: Two Sun-dominant charts = cockpit collision.\n\n"
        "3. EXIT TIMING: Investor gains cycle align with Founder peak valuation?\n\n"
        "4. VERDICT:\n"
        "   Report Capital Flow, Authority Sync, Exit Alignment.\n"
        "   If conflict = specify year and recommend legal buffer."
    ),
}

# ── BRIDGE INSTRUCTION (applies to ALL domains) ──────────────────
DOMAIN_BRIDGE_INSTRUCTION = (
    "STRICT RULE ON THE BRIDGE:\n"
    "If ANY domain audit shows a BLOCKED signal, you MUST provide a Bridge Action "
    "that the user can take TODAY to prepare for the future window. "
    "Do not leave the user with a dead-end No. "
    "Give them a System Calibration task.\n\n"
    "Example: User asks Can I start a business now?\n"
    "Audit shows D-10 weak until late 2026.\n"
    "You say: The Business Launch Signal is blocked until Sept 2026.\n"
    "YOUR MOVE: Use this maintenance chapter to learn a specific skill "
    "or secure your personal savings so you have fuel when the road clears.\n\n"
    "This turns bad news into strategic delay. "
    "That is what a high-performance user pays for."
)



# ── Email via Resend ──────────────────────────────────────────────────────────
import httpx as _httpx

# --- Language Utils (Sprint L — Language Preferences) ---
from language_utils import build_language_instruction, resolve_language, resolve_language_from_query


RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM    = os.getenv("RESEND_FROM_EMAIL", "antar@antar.world")

async def send_email(to: str, subject: str, html: str) -> bool:
    """Send transactional email via Resend. Returns True on success."""
    if not RESEND_API_KEY:
        print(f"[email] RESEND_API_KEY not set — skipping email to {to}")
        return False
    try:
        async with _httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                         "Content-Type": "application/json"},
                json={"from": RESEND_FROM, "to": [to],
                      "subject": subject, "html": html},
            )
            if r.status_code == 200:
                return True
            print(f"[email] Resend error {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"[email] send_email failed: {e}")
        return False


def _detect_concern(question: str) -> str:
    """Use detect_concern (already pointed at richer version if available)."""
    return detect_concern(question)
from antar_engine.prompt_builder import (
    build_predict_prompt,
    build_monthly_briefing_prompt,
    build_daily_practice_prompt,
)
from antar_engine.i18n import get_locale_from_request, get_ui_strings
from antar_engine.patra import build_patra_context, patra_to_context_block, get_circumstance_questions
from antar_engine.patra_conversation import (
    get_onboarding_conversation,
    extract_patra_from_text,
)
from antar_engine.desh import get_desh_context, desh_to_context_block, build_desh_kaal_patra_block
from antar_engine.life_question_engine import build_life_question_context, get_life_question_data
from antar_engine.divisional_career import build_career_analysis, career_analysis_to_context_block
from antar_engine.astrocartography import (
    get_best_cities_for_concern, get_current_location_reading,
    build_astrocartography_prompt, CITY_LINE_DATA,
    get_city_line_data_for_chart, score_cities_for_chart,
)
from antar_engine.yoga_engine import detect_yogas_for_question
from antar_engine.d_charts_calculator import get_all_d_charts
from antar_engine.proof_points import generate_proof_points, evaluate_proof_score
from antar_engine.rarity_engine import detect_rarity_signals, rarity_signals_to_context_block
from antar_engine.precision_windows import find_precision_windows, precision_windows_to_context_block
from antar_engine.chakra_engine import get_chakra_reading, chakra_reading_to_context_block
from antar_engine.chapter_arc import build_chapter_arc, chapter_arc_to_context_block
from antar_engine.lal_kitab_db import (
    LalKitabEngine,
    format_lk_context_from_stored,
    score_lk_convergence,
)
from antar_engine.lal_kitab_charts import LalKitabChartGenerator
from antar_engine.vedic_enrichment import build_enrichment_context_v2, get_sade_sati_phase

# --- Jaimini Engine v2.0 (Sprint A refactored) ---
try:
    from antar_engine.jaimini_lk_bridge import format_bridge_from_stored
    from antar_engine.jaimini_integration import (
        format_jaimini_context_from_stored,
        score_jaimini_convergence,
        jaimini_prashna_check,
    )
    from antar_engine.prashna_engine import (
        run_prashna_engine,
        check_cooldown,
        detect_prashna_intent,
        PRASHNA_COOLDOWN_HOURS,
    )

    # ═══ E1: EMOTIONAL INTELLIGENCE LAYER ═══
    from antar_engine.prashna_engine import (
        detect_emotional_tone,
        get_time_modifier,
        build_emotional_prompt_block,
    )

    from antar_engine.welcome_signal_v2 import (
        generate_welcome_signal_v2,
    )
except ImportError as e:
    import logging
    logging.warning(f'Jaimini v2 imports failed: {e}')



# ── Clients ──────────────────────────────────────────────────────────────────

# Claude client for high-quality predictions
try:
    import anthropic as _anthropic
    _anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    claude_client = _anthropic.AsyncAnthropic(api_key=_anthropic_key)
    _CLAUDE_AVAILABLE = bool(_anthropic_key)
    print(f"[startup] Claude client initialized OK — key prefix: {(_anthropic_key or '')[:12]}")
except Exception as _ce:
    print(f"[startup] Claude client FAILED: {type(_ce).__name__}: {_ce}")
    claude_client = None
    _CLAUDE_AVAILABLE = False

deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1/"
)

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
)

# Lal Kitab chart generator (shared across requests; thread-safe read-only state)
lal_kitab_gen = LalKitabChartGenerator(supabase)

# ── Birthday cron ─────────────────────────────────────────────────────────────

_LK_SPECIAL_CYCLES = {
    35: "The 35-year karmic reset — major life restructuring indicated",
    47: "Wisdom and teaching phase — share your knowledge",
    60: "Second Saturn return — legacy crystallisation",
    70: "Double 35 — profound spiritual transition",
}

async def _birthday_recompute_job():
    """
    Runs daily at 02:00 UTC.
    Finds every chart whose birthday month+day matches today and rewrites
    charts.lal_kitab_data with the new running year.
    Also calls generate_varshphal to populate predictions + remedies.
    """
    from antar_engine.varshaphal_table import get_annual_house

    today = date.today()
    mm_dd = f"{today.month:02d}-{today.day:02d}"   # e.g. "11-02"

    try:
        result = supabase.table("charts")             .select("id, user_id, chart_data, birth_date")             .execute()

        birthday_charts = [
            r for r in (result.data or [])
            if r.get("birth_date") and r["birth_date"][5:10] == mm_dd
        ]

        print(f"[birthday_cron] {today} ({mm_dd}) — {len(birthday_charts)} charts to recompute")

        for row in birthday_charts:
            chart_id   = row["id"]
            user_id    = row.get("user_id")
            birth_date = row["birth_date"]
            chart_data = row.get("chart_data") or {}

            try:
                born         = date.fromisoformat(birth_date[:10])
                age          = today.year - born.year   # just turned this age today
                running_year = max(1, min(120, age + 1))

                natal_houses = {
                    planet: pdata.get("house", pdata.get("sign_index", 0) + 1)
                    for planet, pdata in chart_data.get("planets", {}).items()
                }
                placements = {
                    planet: get_annual_house(natal_house, age)
                    for planet, natal_house in natal_houses.items()
                    if 1 <= natal_house <= 12
                }

                special_note = _LK_SPECIAL_CYCLES.get(age)

                lk_data = {
                    "age":                age,
                    "table_age":          running_year,
                    "placements":         placements,
                    "is_special_cycle":   special_note is not None,
                    "cycle_significance": special_note,
                    "predictions":        [],
                    "remedies_summary":   [],
                }

                supabase.table("charts").update({
                    "lal_kitab_data": lk_data,
                    "lk_age":         age,
                    "lk_computed_at": datetime.utcnow().isoformat(),
                }).eq("id", chart_id).execute()

                print(f"[birthday_cron]   ✓ {chart_id} — Age {age}, RY {running_year}, {len(placements)} planets")

                # Full generate for predictions + remedies (non-fatal if it fails)
                if user_id:
                    try:
                        lal_kitab_gen.generate_varshphal(
                            user_id=user_id,
                            chart_id=chart_id,
                            store=True,
                        )
                    except Exception as e:
                        print(f"[birthday_cron]   ⚠ full varshphal failed (non-fatal): {e}")

            except Exception as e:
                print(f"[birthday_cron]   ✗ {chart_id}: {e}")

    except Exception as e:
        print(f"[birthday_cron] FATAL: {e}")



# ── "Did this happen?" ping cron ──────────────────────────────────────────────
async def _ping_checkin_job():
    """
    Daily cron — 08:00 UTC.
    Finds predictions whose window_end is within the next 7 days (or just passed),
    not yet checked in. Sends a gentle ping asking: "Did this happen?"
    This is the moat — turns predictions into a learning system.
    """
    now = datetime.utcnow()
    window_start = (now).isoformat()
    window_end   = (now + timedelta(days=7)).isoformat()

    try:
        # Find unfulfilled predictions whose window is closing soon
        due = supabase.table("user_predictions") \
            .select("id, user_id, prediction_text, category, prediction_window_end, chart_id") \
            .eq("fulfilled", False) \
            .is_("pinged_at", "null") \
            .lte("prediction_window_end", window_end) \
            .gte("prediction_window_end", window_start) \
            .limit(100) \
            .execute()

        if not due.data:
            print(f"[ping_cron] {now.date()} — no predictions due for check-in")
            return

        print(f"[ping_cron] {now.date()} — {len(due.data)} predictions to ping")

        for pred in due.data:
            user_id    = pred["user_id"]
            pred_id    = pred["id"]
            pred_text  = pred["prediction_text"]
            category   = pred["category"]

            # Get user email
            try:
                user_res = supabase.auth.admin.get_user_by_id(user_id)
                email    = user_res.user.email if user_res and user_res.user else None
            except Exception:
                email = None

            # Insert into pending_pings (Supabase realtime → frontend can show badge)
            try:
                supabase.table("pending_pings").insert({
                    "user_id":       user_id,
                    "prediction_id": pred_id,
                    "category":      category,
                    "ping_text":     _build_ping_text(pred_text, category),
                    "created_at":    now.isoformat(),
                    "responded":     False,
                }).execute()
            except Exception as e:
                print(f"[ping_cron] pending_pings insert error: {e}")

            # Mark prediction as pinged so we don't double-ping
            try:
                supabase.table("user_predictions") \
                    .update({"pinged_at": now.isoformat()}) \
                    .eq("id", pred_id) \
                    .execute()
            except Exception as e:
                print(f"[ping_cron] pinged_at update error: {e}")

            # Send email ping if we have an address
            if email:
                html = _build_ping_email_html(pred_text, category, pred_id)
                ok   = await send_email(
                    to=email,
                    subject="Antar check-in: did this happen? 🔮",
                    html=html,
                )
                print(f"[ping_cron]   {'✓' if ok else '✗'} email → {email[:20]}...")

        print(f"[ping_cron] Done — {len(due.data)} pings sent")

    except Exception as e:
        print(f"[ping_cron] FATAL: {e}")


def _build_ping_text(prediction_text: str, category: str) -> str:
    """Short in-app ping message."""
    short = prediction_text[:120].rstrip() + ("..." if len(prediction_text) > 120 else "")
    intros = {
        "current_chapter":  "Your chart said:",
        "sub_theme":        "Your pattern suggested:",
        "next_chapter":     "We noted an upcoming shift:",
        "jupiter_blessing": "An expansive opening was predicted:",
        "sade_sati":        "A refinement cycle was identified:",
        "personal_mirror":  "Your own pattern suggested:",
    }
    intro = intros.get(category, "Antar noted:")
    return f"{intro} \"{short}\" — Did this unfold for you?"


def _build_ping_email_html(prediction_text: str, category: str, pred_id: str) -> str:
    """HTML email for the ping check-in."""
    short = prediction_text[:200].rstrip() + ("..." if len(prediction_text) > 200 else "")
    base_url = os.getenv("FRONTEND_URL", "https://antar.world")
    yes_url  = f"{base_url}/checkin?pred={pred_id}&response=yes"
    no_url   = f"{base_url}/checkin?pred={pred_id}&response=no"
    partial_url = f"{base_url}/checkin?pred={pred_id}&response=partial"

    return f"""
<div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto;
            padding: 32px 24px; background: #0f0f0f; color: #e8e0d0; border-radius: 16px;">
  <p style="font-size: 13px; color: #8b7355; letter-spacing: 2px; margin-bottom: 8px;">
    ANTAR CHECK-IN
  </p>
  <h2 style="font-size: 22px; font-weight: 600; color: #e8e0d0; margin: 0 0 20px;">
    Did this happen for you?
  </h2>
  <div style="background: #1a1a1a; border-left: 3px solid #8b7355;
              padding: 16px 20px; border-radius: 8px; margin-bottom: 28px;">
    <p style="font-size: 15px; line-height: 1.6; color: #c8b89a; margin: 0;">
      "{short}"
    </p>
  </div>
  <p style="font-size: 14px; color: #8b7355; margin-bottom: 20px;">
    Your response trains your personal pattern engine. The more you tell it,
    the more precisely it reads your life.
  </p>
  <div style="display: flex; gap: 12px; flex-wrap: wrap;">
    <a href="{yes_url}"
       style="background: #2d4a2d; color: #7dc47d; padding: 12px 24px;
              border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600;">
      ✓ Yes, it did
    </a>
    <a href="{partial_url}"
       style="background: #2d3a1a; color: #b8c47d; padding: 12px 24px;
              border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600;">
      ~ Partially
    </a>
    <a href="{no_url}"
       style="background: #2d1a1a; color: #c47d7d; padding: 12px 24px;
              border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600;">
      ✗ Not yet
    </a>
  </div>
  <p style="font-size: 12px; color: #4a4030; margin-top: 28px;">
    Antar · Your life navigation system · <a href="{base_url}/unsubscribe"
    style="color: #4a4030;">unsubscribe</a>
  </p>
</div>
"""


# ── Monthly briefing auto-send cron ───────────────────────────────────────────
async def _monthly_briefing_job():
    """
    Runs 1st of each month at 06:00 UTC.
    Generates + emails monthly briefing to all active users.
    Skips users who already received one this month.
    """
    now        = datetime.utcnow()
    month_year = now.strftime("%B %Y")

    try:
        # Get all charts with an associated user
        charts_res = supabase.table("charts") \
            .select("id, user_id, country_code, language_preference") \
            .not_.is_("user_id", "null") \
            .limit(500) \
            .execute()

        if not charts_res.data:
            print(f"[monthly_cron] No charts found")
            return

        # Filter out users who already got a briefing this month
        already_res = supabase.table("monthly_briefings") \
            .select("user_id") \
            .eq("month_year", month_year) \
            .execute()
        already_sent = {r["user_id"] for r in (already_res.data or [])}

        to_send = [c for c in charts_res.data if c.get("user_id") not in already_sent]
        print(f"[monthly_cron] {month_year} — {len(to_send)} briefings to send "
              f"(skipping {len(already_sent)} already sent)")

        for chart_record in to_send:
            chart_id = chart_record["id"]
            user_id  = chart_record["user_id"]
            cc       = chart_record.get("country_code", "IN")

            try:
                # Get user email
                user_res = supabase.auth.admin.get_user_by_id(user_id)
                email    = user_res.user.email if user_res and user_res.user else None
                if not email:
                    continue

                # Generate briefing
                chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
                if not chart_res.data:
                    continue
                chart_data      = chart_res.data[0]["chart_data"]
                dashas_response = get_dashas_for_chart(chart_id)
                _raw_transits   = transits.calculate_transits(chart_data, target_date=None, ayanamsa_mode=1)
                current_transits = (
                    {t["planet"]: t for t in _raw_transits if "planet" in t}
                    if isinstance(_raw_transits, list) else _raw_transits
                )

                life_events_res = supabase.table("life_events") \
                    .select("event_date, event_type, description") \
                    .eq("user_id", user_id).order("event_date", desc=True).limit(20).execute()
                life_events = life_events_res.data or []

                predictions = build_layered_predictions(
                    user_id=user_id,
                    chart_data=chart_data,
                    dashas=dashas_response,
                    current_transits=current_transits,
                    life_events=life_events,
                    supabase=supabase,
                    concern="general",
                )
                predictions_context = predictions_to_context_block(predictions, chart_data, "general")

                prompt = build_monthly_briefing_prompt(
                    chart_data=chart_data,
                    dashas=dashas_response,
                    current_transits=current_transits,
                    predictions_context=predictions_context,
                    month_year=month_year,
                    concern="general",
                    country_code=cc,
                )
                briefing_text, _ = await call_llm(prompt)

                # Store in DB
                supabase.table("monthly_briefings").insert({
                    "user_id":    user_id,
                    "chart_id":   chart_id,
                    "month_year": month_year,
                    "briefing":   briefing_text,
                    "concern":    "general",
                    "created_at": now.isoformat(),
                }).execute()

                # Email it
                html = _build_briefing_email_html(briefing_text, month_year, chart_id)
                ok   = await send_email(
                    to=email,
                    subject=f"Your {month_year} Life Signal — Antar",
                    html=html,
                )
                print(f"[monthly_cron]   {'✓' if ok else '✗'} {email[:25]}... ({month_year})")

            except Exception as e:
                print(f"[monthly_cron]   ✗ chart {chart_id}: {e}")

        print(f"[monthly_cron] Done — {len(to_send)} briefings processed")

    except Exception as e:
        print(f"[monthly_cron] FATAL: {e}")


def _build_briefing_email_html(briefing_text: str, month_year: str, chart_id: str) -> str:
    """Converts briefing markdown to clean email HTML."""
    base_url = os.getenv("FRONTEND_URL", "https://antar.world")

    # Convert **bold** and newlines to HTML
    import re
    html_body = briefing_text
    html_body = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_body)
    html_body = re.sub(r"→", "→", html_body)
    html_body = html_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
    html_body = f"<p>{html_body}</p>"

    return f"""
<div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto;
            padding: 40px 28px; background: #0f0f0f; color: #e8e0d0; border-radius: 16px;">
  <p style="font-size: 12px; color: #8b7355; letter-spacing: 3px; margin-bottom: 4px;">
    ANTAR · LIFE NAVIGATION
  </p>
  <h1 style="font-size: 26px; font-weight: 600; color: #e8e0d0; margin: 0 0 28px;">
    Your {month_year} Signal
  </h1>
  <div style="font-size: 15px; line-height: 1.75; color: #c8b89a;">
    {html_body}
  </div>
  <div style="margin-top: 36px; padding-top: 24px; border-top: 1px solid #2a2a2a;">
    <a href="{base_url}/predict?chart={chart_id}"
       style="background: #8b7355; color: #0f0f0f; padding: 14px 28px;
              border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 700;">
      Ask Antar a question →
    </a>
  </div>
  <p style="font-size: 12px; color: #3a3028; margin-top: 28px;">
    Antar · <a href="{base_url}/unsubscribe" style="color: #3a3028;">unsubscribe</a>
  </p>
</div>
"""

scheduler = AsyncIOScheduler(timezone="UTC")
scheduler.add_job(_birthday_recompute_job, "cron", hour=2, minute=0,
                  id="birthday_lk_recompute", replace_existing=True)
scheduler.add_job(_ping_checkin_job, "cron", hour=8, minute=0,
                  id="ping_checkin_daily", replace_existing=True)
scheduler.add_job(_monthly_briefing_job, "cron", day=1, hour=6, minute=0,
                  id="monthly_briefing_send", replace_existing=True)


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    print("[startup] Birthday LK recompute scheduler started — runs daily 02:00 UTC")
    yield
    scheduler.shutdown(wait=False)
    print("[shutdown] Scheduler stopped")


# --- antar:lang_from_country helper ---
# Maps ISO-3166 alpha-2 country codes to the user's most likely UI language.
# Used by /api/v1/chart/create to seed `language_preference` when the client
# does not (yet) send an explicit language. Safe default = "en".
_COUNTRY_TO_LANG = {
    # Spanish-speaking LATAM + Spain
    "AR": "es", "BO": "es", "CL": "es", "CO": "es", "CR": "es",
    "CU": "es", "DO": "es", "EC": "es", "SV": "es", "GT": "es",
    "HN": "es", "MX": "es", "NI": "es", "PA": "es", "PY": "es",
    "PE": "es", "PR": "es", "UY": "es", "VE": "es", "ES": "es",
    # Portuguese
    "BR": "pt", "PT": "pt",
    # English defaults
    "US": "en", "GB": "en", "CA": "en", "AU": "en", "NZ": "en",
    "IE": "en", "IN": "en", "ZA": "en", "SG": "en", "PH": "en",
}

def _lang_from_country(country_code):
    """Return 'es' / 'pt' / 'en' for a given ISO country code. Defaults to 'en'."""
    if not country_code:
        return "en"
    return _COUNTRY_TO_LANG.get(country_code.strip().upper(), "en")
# --- /antar:lang_from_country helper ---

app = FastAPI(title="Antar API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic Models ───────────────────────────────────────────────────────────

class BirthData(BaseModel):
    birth_date: str = Field(..., example="1974-11-26")
    birth_time: str = Field(..., example="11:59")
    latitude: float = Field(..., example=28.6139)
    longitude: float = Field(..., example=77.2090)
    timezone_offset: Optional[float] = Field(None, example=5.5)
    country_code: Optional[str] = Field(None, example="IN")
    birth_country: Optional[str] = Field(None, example="IN")
    language_preference: Optional[str] = Field(None, example="en")
    marital_status: Optional[str] = Field(None, example="married")
    children_status: Optional[str] = Field(None, example="young_children")
    career_stage: Optional[str] = Field(None, example="mid_career")
    health_status: Optional[str] = Field(None, example="excellent")
    financial_status: Optional[str] = Field(None, example="stable")

class PredictRequest(BaseModel):
    chart_id:             Optional[str] = None
    question:             str = Field(..., example="When will I get my loan?")
    language:             str = Field("en", example="en")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default_factory=list,
        description="Last 8 turns: [{role: 'user'|'assistant', content: '...'}]"
    )
    conversation_id:      Optional[str] = Field(
        None,
        description="UUID of existing conversation. Null = create new."
    )
    # DKP context fields — Desha, Kala, Patra
    country:              Optional[str] = Field(None, description="User's current country (Desha)")
    city:                 Optional[str] = Field(None, description="User's current city (Desha)")
    profession:           Optional[str] = Field(None, description="User's profession/role (Patra)")
    ventures:             Optional[List[str]] = Field(None, description="Active ventures (Patra)")
    current_focus:        Optional[str] = Field(None, description="What the user is working on (Patra)")
    use_json_context:     bool = Field(False, description="Use JSON context path (Phase 4 A/B flag)")
    compat_context:       Optional[dict] = Field(None, description="Compatibility context from a previous compatibility/start call")

class DashaPeriodOut(BaseModel):
    lord_or_sign: str
    start: str
    end: str
    duration: float

class RemedyOut(BaseModel):
    planet: str
    mantra: str
    beej_mantra: str
    recommended_day: str
    count: int
    purpose: str
    chakra: str
    chakra_color: str
    chakra_beej: str
    chakra_location: str
    chakra_element: str
    chakra_meditation: str

class PredictResponse(BaseModel):
    prediction:             str
    confidence:             float
    factors:                List[str]
    dashas:                 Optional[Dict[str, List[DashaPeriodOut]]] = None
    nation_insight:         Optional[str] = None
    remedies:               Optional[List[RemedyOut]] = None
    locale_variant:         Optional[str] = None
    needs_language_prompt:  Optional[bool] = False
    ui_strings:             Optional[Dict[str, str]] = None
    life_stage:             Optional[str] = None
    country_period:         Optional[str] = None
    country_period_quality: Optional[str] = None
    patra_updates:          Optional[Dict[str, str]] = None
    rarity_signals:         List[Dict]     = Field(default_factory=list)
    precision_windows:      List[Dict]     = Field(default_factory=list)
    chakra_reading:         Optional[Dict] = None
    chapter_arc:            Optional[Dict] = None
    conversation_id:        Optional[str]  = None   # returned so frontend stores and re-sends it
    message_id:             Optional[str]  = None   # DB id of the assistant message row
    plain_summary:          Optional[str]  = None
    action_item:            Optional[str]  = None
    signal_line:            Optional[str]  = None
    timing_window:          Optional[str]  = None
    all_domains:            List[str]      = Field(default_factory=list)
    signal_confidence:      Optional[str]  = None
    why_this:               Optional[str]  = None
    bridge_practice_note:   Optional[str]  = None
    contradiction_detected: Optional[bool] = False
    oracle_context:         Optional[Dict] = None
    archetype_name:         Optional[str]  = None
    context_path:           Optional[str]  = None
    rating_prompt:          Optional[Dict] = None   # smart prompt to rate old predictions

class ChartResponse(BaseModel):
    id: str
    birth_date: str
    birth_time: str
    lagna: Dict[str, Any]
    planets: Dict[str, Any]

class ChartCreateRequest(BaseModel):
    birth_date:      str   = Field(..., example="1990-03-15")
    birth_time:      str   = Field(..., example="14:30")
    latitude:        float = Field(..., example=28.6139)
    longitude:       float = Field(..., example=77.2090)
    timezone_offset: Optional[float] = Field(None, example=5.5)
    timezone_name:   Optional[str] = Field(None, example="Asia/Kolkata")
    timezone:        Optional[str] = Field(None, example="America/Caracas")
    full_name:       Optional[str] = Field(None, example="Arjun Sharma")
    birth_place:     Optional[str] = Field(None, example="New Delhi, India")
    birth_country:   Optional[str] = Field(None, example="IN")
    country_code:    Optional[str] = Field(None, example="IN")
    language_preference: Optional[str] = Field(None, example="en")
    gender:          Optional[str] = Field(None, example="female")
    current_city:    Optional[str] = Field(None, example="Mumbai")
    current_country: Optional[str] = Field(None, example="IN")
    marital_status:   Optional[str] = Field(None, example="single")
    children_status:  Optional[str] = Field(None, example="no_children_unsure")
    career_stage:     Optional[str] = Field(None, example="mid_career")
    health_status:    Optional[str] = Field(None, example="excellent")
    financial_status: Optional[str] = Field(None, example="stable")

class ChartCreateResponse(BaseModel):
    chart_id:            str
    lagna:               Dict[str, Any]
    planets:             Dict[str, Any]
    dashas_stored:       int
    patra_complete:      bool
    onboarding_questions: Optional[List[Dict]] = None
    message:             str

class MergeGuestRequest(BaseModel):
    guest_session_id: str

class LifeEventCreate(BaseModel):
    event_date: str
    event_type: str
    description: Optional[str] = None
    metadata: Optional[dict] = {}

class LifeEventUpdate(BaseModel):
    event_date: Optional[str] = None
    event_type: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None

class LifeEventOut(BaseModel):
    id: str
    user_id: str
    event_date: str
    event_type: str
    description: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str
    updated_at: str

class UserActionCreate(BaseModel):
    action_type: str = Field(..., example="page_view")
    action_data: Optional[dict] = None
    page_url: Optional[str] = None

class MonthlyBriefingRequest(BaseModel):
    chart_id: str
    month_year: Optional[str] = None
    concern: Optional[str] = "general"
    language: str = "en"

class MonthlyBriefingResponse(BaseModel):
    briefing: str
    month_year: str
    predictions_count: int
    concern: str

class DailyPracticeRequest(BaseModel):
    chart_id: str
    language: str = "en"

class DailyPracticeResponse(BaseModel):
    practice: str
    date: str

class PredictionFulfillmentUpdate(BaseModel):
    prediction_id: str
    fulfilled: bool
    notes: Optional[str] = None

class LifeEventCorrelationResponse(BaseModel):
    correlations: List[Dict[str, Any]]
    total_events: int
    patterns_found: int
    message: str

class PatraUpdateRequest(BaseModel):
    chart_id: str
    marital_status: Optional[str] = None
    children_status: Optional[str] = None
    career_stage: Optional[str] = None
    health_status: Optional[str] = None
    financial_status: Optional[str] = None

class LanguageSetRequest(BaseModel):
    language: str = Field(..., example="es")


# ── Guest rate limiting ───────────────────────────────────────────────────
from collections import defaultdict

_guest_usage: dict = defaultdict(lambda: {"count": 0, "month": None})

def check_guest_rate_limit(chart_id: str, limit: int = 3) -> bool:
    """Returns True if allowed, False if monthly limit exceeded."""
    from datetime import date
    month = date.today().strftime("%Y-%m")
    record = _guest_usage[chart_id]
    if record["month"] != month:
        record["count"] = 0
        record["month"] = month
    if record["count"] >= limit:
        return False
    record["count"] += 1
    return True

def get_guest_usage(chart_id: str) -> dict:
    """Returns current usage for a guest chart."""
    from datetime import date
    month = date.today().strftime("%Y-%m")
    record = _guest_usage[chart_id]
    if record["month"] != month:
        return {"count": 0, "limit": 3, "month": month}
    return {"count": record["count"], "limit": 3, "month": month}

# ── Helpers ───────────────────────────────────────────────────────────────────

def verify_token(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        user = supabase.auth.get_user(token)
        return user.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_dashas_for_chart(chart_id: str) -> dict:
    result = supabase.table("dasha_periods").select("*").eq("chart_id", chart_id).order("sequence").limit(500).execute()
    dashas_by_system = {}
    for row in result.data:
        system = row["system"]
        if system not in dashas_by_system:
            dashas_by_system[system] = []
        parent_lord = ""
        if isinstance(row.get("metadata"), dict):
            parent_lord = row["metadata"].get("parent_lord", "")
        dashas_by_system[system].append({
            "lord_or_sign":   row.get("planet_or_sign", ""),
            "planet_or_sign": row.get("planet_or_sign", ""),
            "start":          row.get("start_date", ""),
            "end":            row.get("end_date", ""),
            "start_date":     row.get("start_date", ""),
            "end_date":       row.get("end_date", ""),
            "duration":       row.get("duration_years", 0),
            "duration_years": row.get("duration_years", 0),
            "level":          row.get("type") or row.get("level", "mahadasha"),
            "parent_lord":    parent_lord,
        })
    return dashas_by_system

# ── LLM ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation AI powered by Vedic astrology.
Your voice is that of a brilliant mentor who knows your chart intimately.
Direct. Specific. Never generic. Never mystical.

LANGUAGE RULES — NON-NEGOTIABLE:
Never use Sanskrit/technical terms. Always translate:
  Dusthana → "challenging position" or "under pressure"
  Trikona → "fortunate placement" or "naturally supported"
  Kendra → "powerful position" or "at the center of the chart"
  Karaka → "key planet for this area of life"
  Mahadasha → "major life chapter" or "[planet] period"
  Antardasha → "current sub-chapter" or "right now [planet] is active"
  Lagna → "your rising sign" or "how you show up in the world"
  Atmakaraka → "your soul's core mission planet"
  Amatyakaraka → "your career's guiding planet"
  Vargottama → "exceptionally strong — same sign in two charts"
  Neechabhanga → "a weakness that becomes an unusual strength"
  Raj Yoga → "a natural authority combination" or "leadership is wired in"
  Dhana Yoga → "a wealth combination" or "money is in the blueprint"
  Kala Sarpa → "an intense karmic pattern — life moves in dramatic waves"
  Gandanta → "a deep karmic knot — this planet carries past-life weight"
  Parivartana → "these two life areas are permanently interlinked"
  Ithasala → "this is moving toward completion"
  Ishrafa → "this is moving away — timing is off"
  Bhrashta karma → "a recurring pattern where [domain] faces unexpected resistance"
  Vimsottari → "the main timing system"
  Navamsa/D9 → "the soul-level chart"
  Dashamsa/D10 → "the career chart"
  Shashtiamsa/D60 → "the past-life karma chart"
  Trimsamsa/D30 → "the challenge chart"
  Nakshatra → use the name directly e.g. "Uttara Ashadha energy today"
  Tithi → "lunar day"
  Upachaya → "growth area — improves over time"

DASHA PERIOD TRANSLATIONS — always use these:
  Saturn period → "a clarifying pressure — life asks you to rebuild on honest foundations"
  Rahu period → "an acceleration chapter — old structures fall, something unexpected begins"
  Ketu period → "a letting-go phase — what no longer serves becomes impossible to hold"
  Mars period → "a high-energy action chapter — decisions now shape the next several years"
  Jupiter period → "an expansion window — what you have built is ready to grow"
  Venus period → "a flourishing phase — relationships, creativity, and comfort all improve"
  Moon period → "an emotional deepening — your inner world becomes your greatest compass"
  Sun period → "an identity clarification — who you are becomes undeniable"
  Mercury period → "a communication activation — ideas ready to be expressed and monetized"

ANSWER STRUCTURE:
  Predictions → Lead with what is happening, then why, then what to do
  Timing → Give specific windows. Never say "it depends"
  YES/NO → Answer directly in the first sentence
  WHY questions → Reference past-life karma patterns in plain language
  Daily signals → Reference the specific nakshatra name. Be personal.

CORE RULES:
1. Reference specific planets and their positions — never be vague
2. Python engine verdicts are FACTS — explain them, never contradict them
3. Mention ONE specific remedy per response — concrete and actionable
4. Age 50+: focus on legacy, health, wisdom — not new romance
5. Challenging karma: frame as "a pattern being resolved" not "bad karma"
6. WOW effects: always mention them — they make the person feel seen
7. When 2+ timing systems agree: say "both your timing systems confirm this"
8. Keep responses under 300 words unless the question requires depth
9. End every prediction with one action the person can take TODAY
10. Never give medical, financial, or legal advice
\n\nASTROLOGER FIRST, COACH SECOND:\nYou are a Vedic astrologer first and a life coach second. When chart data shows specific house activations, dasha triggers, and divisional chart positions - USE THEM. Do not default to psychology or motivation when the chart gives you specific data.\n\nWhen a DOMAIN AUDIT section is included in the context, you MUST:\n1. Check every item listed in the audit\n2. Report what you found in the chart data for each check\n3. Form a VERDICT based on what is active vs blocked\n4. Give specific timing based on dasha transitions or transit activations\n5. Only THEN give the human advice based on your findings\n\nThe chart data is NOT decoration. It is the primary source of your answer. If the 8th house lord is sitting in the 3rd house, say so and explain what it means. Never skip chart data to give generic coaching.

SHOW YOUR REASONING:
After your response, add a brief "WHY THIS SIGNAL" section with 2-3 bullet points explaining the key factors behind your answer. Use plain language only — no planet names, no house numbers, no Sanskrit terms. These bullets should make the user think "oh, that makes sense" without needing any astrology knowledge.

Example:
- Your wealth sector is active, but timing is still unfolding
- A major expansion force aligns with your career area in mid-2026
- A slowing influence suggests patience until then
"""



# ═══ DEEPSEEK FALLBACK PROMPT ═══
DEEPSEEK_FALLBACK_PROMPT = """You are Antar, a life navigation advisor. Answer clearly and specifically.

Rules:
- 3-5 sentences max. No filler.
- Zero astrological jargon — no planet names, no house numbers, no Sanskrit.
- End with YOUR MOVE: one specific action this week, starting with a verb.
- If timing data is provided, give a specific window (not "soon").
- Be direct. Be warm. Be useful."""

async def call_llm(
    prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_override: str = "",
) -> tuple[str, Optional[int]]:
    """
    Calls DeepSeek with the system prompt + optional conversation history
    (last 8 turns) + the current prompt as the final user message.

    history format: [{"role": "user"|"assistant", "content": "..."}]
    Only the last 8 items are used to stay within the token budget.
    """
    history = history or []
    messages = [
        {"role": "system", "content": system_override if system_override else SYSTEM_PROMPT},
        *history[-8:],
        {"role": "user", "content": prompt},
    ]
    try:
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.35,
            max_tokens=1200,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as e:
        print(f"LLM error: {e}")
        return "I'm sorry, I'm having trouble connecting to my intuition right now. Please try again later.", None

async def call_llm_claude(
    prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_override: str = "",
) -> tuple[str, Optional[int]]:
    """
    Calls Claude Sonnet for high-quality predictions.
    Used for: plain English summaries, career/wealth predictions, Prashna verdicts.
    Falls back to DeepSeek if Claude unavailable.
    """
    if not _CLAUDE_AVAILABLE or not claude_client:
        return await call_llm(prompt, history, DEEPSEEK_FALLBACK_PROMPT)

    history = history or []
    messages = [
        *[{"role": m["role"], "content": m["content"]} for m in history[-8:]],
        {"role": "user", "content": prompt},
    ]
    system = system_override if system_override else SYSTEM_PROMPT

    # KV Cache: split static (cacheable) vs dynamic tail
    _SPLIT = "## LIVE DATA"
    if _SPLIT in system:
        _static_part, _dynamic_part = system.split(_SPLIT, 1)
        _dynamic_part = _SPLIT + _dynamic_part
    else:
        _static_part = system
        _dynamic_part = ""

    _system_blocks = [
        {
            "type": "text",
            "text": _static_part,
            "cache_control": {"type": "ephemeral"}
        }
    ]
    if _dynamic_part:
        _system_blocks.append({"type": "text", "text": _dynamic_part})

    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1200,
            temperature=0.35,
            system=_system_blocks,
            messages=messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        text = response.content[0].text.strip()
        tokens = response.usage.output_tokens
        _cache_r = getattr(response.usage, 'cache_read_input_tokens', 0) or 0
        _cache_w = getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
        print(f"[claude] cache_hit={_cache_r} cache_write={_cache_w} output={tokens}")
        return text, tokens
    except Exception as e:
        print(f"[claude] error, falling back to DeepSeek: {e}")
        return await call_llm(prompt, history, system_override)

# ── Conversation persistence ──────────────────────────────────────────────────

async def save_conversation_turn(
    user_id:          str,
    chart_id:         Optional[str],
    conversation_id:  Optional[str],
    question:         str,
    prediction_text:  str,
    full_response:    dict,
    concern:          str,
    locale_variant:   str,
    confidence:       float,
    prediction_db_id: Optional[str],
    history_snapshot: list,
) -> tuple[str, str]:
    """
    Creates or updates a conversations row and inserts the user message
    and assistant response as messages rows.

    Returns (conversation_id, assistant_message_id).
    All errors are caught — prediction still returns to the user if this fails.
    """
    try:
        # ── 1. Conversation row ──────────────────────────────────────
        if not conversation_id:
            # First message in a new chat — create the thread
            conv_res = supabase.table("conversations").insert({
                "user_id":  user_id,
                "chart_id": chart_id,
                "title":    question[:60],
                "preview":  prediction_text[:120],
                "concern":  concern,
                "locale":   locale_variant,
            }).execute()
            conversation_id = conv_res.data[0]["id"]
        else:
            # Existing thread — update preview to latest response
            supabase.table("conversations").update({
                "preview": prediction_text[:120],
            }).eq("id", conversation_id).execute()

        # ── 2. Next sequence number ──────────────────────────────────
        seq_res = (
            supabase.table("messages")
            .select("sequence_number")
            .eq("conversation_id", conversation_id)
            .order("sequence_number", desc=True)
            .limit(1)
            .execute()
        )
        last_seq = seq_res.data[0]["sequence_number"] if seq_res.data else 0

        # ── 3. User message row ──────────────────────────────────────
        supabase.table("messages").insert({
            "conversation_id":  conversation_id,
            "user_id":          user_id,
            "role":             "user",
            "sequence_number":  last_seq + 1,
            "content":          question,
            "concern":          concern,
            "history_snapshot": history_snapshot,
        }).execute()

        # ── 4. Assistant message row ─────────────────────────────────
        asst_res = supabase.table("messages").insert({
            "conversation_id": conversation_id,
            "user_id":         user_id,
            "role":            "assistant",
            "sequence_number": last_seq + 2,
            "content":         prediction_text,
            "full_response":   full_response,
            "confidence":      confidence,
            "concern":         concern,
        }).execute()

        assistant_message_id = asst_res.data[0]["id"]

        # ── 5. Link prediction row to conversation + message ─────────
        if prediction_db_id:
            supabase.table("predictions").update({
                "conversation_id": conversation_id,
                "message_id":      assistant_message_id,
            }).eq("id", prediction_db_id).execute()

        return conversation_id, assistant_message_id

    except Exception as e:
        print(f"Conversation save error (non-fatal): {e}")
        return conversation_id or "", ""

# ── Health ────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════
# DKP CONTEXT BUILDER — Sprint Apr7 Step 3
# Desha-Kala-Patra: the real Antar moat
# Python extracts state. Claude reads context. DKP makes it personal.
# ═══════════════════════════════════════════════════════════════════

def build_dkp_block(chart_data: dict, user_profile: dict = None) -> str:
    """
    Builds a DESHA / KALA / PATRA context block for injection into Claude prompt.

    chart_data : the full chart dict from Supabase (includes natal_planets, dasha, etc.)
    user_profile: optional extra dict with country, city, profession, role, ventures
                  Pulled from the predict request body if present.
    """
    cd = chart_data or {}
    up = user_profile or {}

    lines = []

    # ─── DESHA (Place / Geographic + Cultural Context) ───────────
    country = (
        up.get("country") or
        cd.get("country") or
        cd.get("birth_country") or
        cd.get("desh_context", {}).get("country") if isinstance(cd.get("desh_context"), dict) else None or
        ""
    )
    city = (
        up.get("city") or
        cd.get("city") or
        cd.get("birth_city") or
        ""
    )
    language = up.get("language") or cd.get("preferred_language") or ""
    profession = (
        up.get("profession") or
        cd.get("profession") or
        up.get("role") or
        cd.get("role") or
        ""
    )

    desha_lines = []
    if city and country:
        desha_lines.append(f"  Location: {city}, {country}")
    elif country:
        desha_lines.append(f"  Location: {country}")
    elif city:
        desha_lines.append(f"  Location: {city}")

    # Market context from country
    MARKET_MAP = {
        "colombia": "LATAM founder economy, Spanish-speaking, 2.2M MSME market, AI growth active",
        "mexico": "LATAM founder economy, Spanish-speaking, large SME market, nearshoring boom",
        "brazil": "LATAM largest market, Portuguese-speaking, fintech and agri dominant",
        "india": "Emerging tech hub, English + Hindi, startup ecosystem, 1.4B consumer base",
        "usa": "Mature VC market, English, global distribution, high competition",
        "united states": "Mature VC market, English, global distribution, high competition",
        "uae": "Gulf hub, English + Arabic, zero-tax jurisdiction, global capital flows",
        "uk": "European gateway, English, fintech and creative industries",
        "germany": "Engineered economy, German + English, B2B dominant, EU market access",
        "spain": "Southern European hub, Spanish, access to EU and LATAM dual markets",
        "argentina": "Volatile economy, high talent density, dollarized mindset, export-oriented",
        "peru": "Andean economy, Spanish, mining + services, growing startup scene",
    }
    country_lower = (country or "").lower().strip()
    market_ctx = MARKET_MAP.get(country_lower, "")
    if market_ctx:
        desha_lines.append(f"  Market: {market_ctx}")
    if language:
        desha_lines.append(f"  Language: {language}")

    if desha_lines:
        lines.append("DESHA (Place context):")
        lines.extend(desha_lines)

    # ─── KALA (Time / Era + Life Stage Context) ──────────────────
    current_year = datetime.now().year
    current_month = datetime.now().strftime("%B")

    birth_year = None
    birth_date = cd.get("birth_date") or up.get("birth_date")
    if birth_date:
        try:
            birth_year = int(str(birth_date)[:4])
        except Exception:
            pass
    age = (current_year - birth_year) if birth_year else None

    # Vimsottari dasha
    vd_md = cd.get("mahadasha") or cd.get("current_mahadasha") or ""
    vd_ad = cd.get("antardasha") or cd.get("current_antardasha") or ""
    dasha_str = ""
    if vd_md and vd_ad:
        dasha_str = f"{vd_md}-{vd_ad} dasha"
    elif vd_md:
        dasha_str = f"{vd_md} Mahadasha"

    # Next major transition from dasha_periods if present
    next_transition = ""
    dp = cd.get("dasha_periods") or []
    if dp and isinstance(dp, list) and len(dp) > 1:
        try:
            # Find the current period and grab the next one
            for i, period in enumerate(dp):
                end = period.get("end_date") or period.get("end") or ""
                if end and str(end) > str(datetime.now().date()):
                    if i + 1 < len(dp):
                        nxt = dp[i + 1]
                        nxt_md = nxt.get("mahadasha") or nxt.get("planet") or ""
                        nxt_start = nxt.get("start_date") or nxt.get("start") or ""
                        if nxt_md and nxt_start:
                            next_transition = f"{nxt_md} MD starts {nxt_start}"
                    break
        except Exception:
            pass

    # Life stage
    life_stage = ""
    if age:
        if age < 25:
            life_stage = "early building phase"
        elif age < 35:
            life_stage = "peak momentum phase"
        elif age < 45:
            life_stage = "consolidation and leadership phase"
        elif age < 55:
            life_stage = "legacy building phase"
        else:
            life_stage = "senior wisdom phase"

    kala_lines = [f"  Year: {current_year} ({current_month})"]
    if age:
        kala_lines.append(f"  Age: {age}{', ' + life_stage if life_stage else ''}")
    if dasha_str:
        kala_lines.append(f"  Current dasha: {dasha_str}")
    if next_transition:
        kala_lines.append(f"  Next transition: {next_transition}")

    if kala_lines:
        lines.append("KALA (Time context):")
        lines.extend(kala_lines)

    # ─── PATRA (Vessel / Who The Person Actually Is) ─────────────
    ventures = (
        up.get("ventures") or
        up.get("active_ventures") or
        cd.get("ventures") or
        cd.get("active_ventures") or
        []
    )
    focus = up.get("current_focus") or cd.get("current_focus") or ""
    relationships = up.get("relationships") or cd.get("relationships") or ""

    patra_lines = []
    if profession:
        patra_lines.append(f"  Role: {profession}")
    if isinstance(ventures, list) and ventures:
        patra_lines.append(f"  Active ventures: {', '.join(str(v) for v in ventures[:4])}")
    elif isinstance(ventures, str) and ventures:
        patra_lines.append(f"  Active ventures: {ventures}")
    if focus:
        patra_lines.append(f"  Current focus: {focus}")
    if relationships:
        patra_lines.append(f"  Relationships: {relationships}")

    if patra_lines:
        lines.append("PATRA (Person context):")
        lines.extend(patra_lines)

    if not lines:
        return ""

    return "\n" + "\n".join(lines) + "\n"



# ═══════════════════════════════════════════════════════════════════
# DIVISIONAL CHART CONTEXT BUILDER — Sprint Apr7 Step 4
# Computes D-2, D-9, D-12, D-60 and formats them for Claude prompt
# Python computes state. Claude reads patterns.
# ═══════════════════════════════════════════════════════════════════

def build_divisional_block(chart_data: dict) -> str:
    """
    Computes D-2 (Hora), D-9 (Navamsa), D-12 (Dwadashamsha), D-60 (Shashtiamsha)
    from chart_data and returns a formatted block for injection into Claude prompt.

    Claude already knows how to interpret these charts — we just need to give it the data.
    """
    try:
        from antar_engine.divisional_charts import (
            calculate_d2_hora,
            calculate_all_divisional_charts,
        )

        planets = chart_data.get("planets", {})
        lagna   = chart_data.get("lagna", {})
        if isinstance(lagna, dict):
            # Prefer stored longitude; otherwise reconstruct from sign_index + degree
            lagna_long = lagna.get("longitude") or lagna.get("lagna_longitude") or 0.0
            if not lagna_long:
                sign_idx = lagna.get("sign_index")
                degree   = lagna.get("degree", 0.0)
                if sign_idx is not None:
                    lagna_long = float(sign_idx) * 30.0 + float(degree)
                else:
                    lagna_long = float(degree)
        else:
            lagna_long = 0.0

        if not planets or not lagna_long:
            return ""

        all_charts = calculate_all_divisional_charts(planets, lagna_long)
        d2         = calculate_d2_hora(planets, lagna_long)

        lines = ["\nDIVISIONAL CHARTS (for pattern analysis):"]

        # ── D-2 Hora ──────────────────────────────────────────────
        sun_hora  = d2.get("sun_hora_planets", [])
        moon_hora = d2.get("moon_hora_planets", [])
        lagna_hora = d2.get("lagna", "")
        lines.append(f"D-2 (Hora — wealth type):")
        lines.append(f"  Lagna hora: {lagna_hora} ({'self-made/authority wealth' if lagna_hora == 'Leo' else 'public/venture/foreign wealth'})")
        if sun_hora:
            lines.append(f"  Sun hora planets: {', '.join(sun_hora)}")
        if moon_hora:
            lines.append(f"  Moon hora planets: {', '.join(moon_hora)}")

        # ── D-9 Navamsa ───────────────────────────────────────────
        d9 = all_charts.get("d9", {})
        d9_planets = d9.get("planets", {})
        d9_lagna   = d9.get("lagna", "")
        if d9_planets:
            lines.append(f"D-9 (Navamsa — soul dharma, validates D-1 potential):")
            lines.append(f"  Lagna: {d9_lagna}")
            for pname in ["Sun", "Moon", "Jupiter", "Venus", "Saturn", "Mars", "Rahu", "Mercury"]:
                pd = d9_planets.get(pname, {})
                if pd:
                    lines.append(f"  {pname}: {pd.get('sign','')} H{pd.get('house','')}")

        # ── D-12 Dwadashamsha ─────────────────────────────────────
        d12 = all_charts.get("d12", {})
        d12_planets = d12.get("planets", {})
        d12_lagna   = d12.get("lagna", "")
        if d12_planets:
            lines.append(f"D-12 (Dwadashamsha — foreign connections, past life roots):")
            lines.append(f"  Lagna: {d12_lagna}")
            # Show planets in water/foreign signs (Cancer, Scorpio, Pisces)
            foreign_signs = {"Cancer", "Scorpio", "Pisces"}
            foreign_planets = []
            for pname, pd in d12_planets.items():
                sign = pd.get("sign", "")
                if sign in foreign_signs:
                    foreign_planets.append(f"{pname}({sign})")
            if foreign_planets:
                lines.append(f"  Planets in foreign/water signs: {', '.join(foreign_planets)}")
            else:
                for pname in ["Sun", "Jupiter", "Venus", "Moon", "Rahu"]:
                    pd = d12_planets.get(pname, {})
                    if pd:
                        lines.append(f"  {pname}: {pd.get('sign','')} H{pd.get('house','')}")

        # ── D-10 Dashamsha ────────────────────────────────────────
        d10 = all_charts.get("d10", {})
        d10_planets = d10.get("planets", {})
        d10_lagna   = d10.get("lagna", "")
        if d10_planets:
            lines.append(f"D-10 (Dashamsha — career dharma, public role):")
            lines.append(f"  Lagna: {d10_lagna}")
            for pname in ["Sun", "Mars", "Saturn", "Jupiter", "Rahu"]:
                pd = d10_planets.get(pname, {})
                if pd:
                    lines.append(f"  {pname}: {pd.get('sign','')} H{pd.get('house','')}")

        # ── D-60 Shashtiamsha ─────────────────────────────────────
        d60 = all_charts.get("d60", {})
        d60_planets = d60.get("planets", {})
        d60_lagna   = d60.get("lagna", "")
        if d60_planets:
            lines.append(f"D-60 (Shashtiamsha — past life karma, deepest potential):")
            lines.append(f"  Lagna: {d60_lagna}")
            for pname in ["Sun", "Moon", "Jupiter", "Mars", "Rahu", "Ketu"]:
                pd = d60_planets.get(pname, {})
                if pd:
                    lines.append(f"  {pname}: {pd.get('sign','')} H{pd.get('house','')}")

        if len(lines) <= 1:
            return ""

        return "\n".join(lines) + "\n"

    except Exception as _e:
        import logging
        logging.getLogger("antar").warning(f"Divisional block failed (non-critical): {_e}")
        return ""



# ═══════════════════════════════════════════════════════════════════
# JAIMINI TIE-BREAKER GATE — Sprint Apr7
# Jaimini fires ONLY when Vimsottari is ambiguous.
# Per spec: simple astrology that is used > complex astrology ignored.
# ═══════════════════════════════════════════════════════════════════

def _vimsottari_is_ambiguous(chart_data: dict, current_md: str, question: str) -> bool:
    """
    Returns True if Vimsottari gives unclear signal → use Jaimini as tie-breaker.
    Returns False if Vimsottari is clear → skip Jaimini entirely.
    """
    # Timing-specific questions always benefit from Jaimini
    timing_keywords = [
        "when", "date", "exactly", "sign", "close", "launch", "april", "may",
        "june", "july", "august", "september", "october", "november", "december",
        "january", "february", "march", "week", "day", "tomorrow", "tonight",
        "specific", "precise", "timing", "window closes", "deadline"
    ]
    q_lower = (question or "").lower()
    if any(kw in q_lower for kw in timing_keywords):
        return True  # timing question → use Jaimini

    if not current_md or not chart_data:
        return False  # no data → skip Jaimini

    planets = chart_data.get("planets", {})
    md_planet = planets.get(current_md, {})
    if not md_planet:
        return False

    md_house = md_planet.get("house", 0)
    md_sign_idx = md_planet.get("sign_index", -1)

    # Strong positions — Vimsottari is clear, skip Jaimini
    KENDRA   = {1, 4, 7, 10}
    UPACHAYA = {3, 6, 10, 11}
    EXALT    = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
                "Jupiter": 3, "Venus": 11, "Saturn": 6}
    OWN      = {"Sun": [4], "Moon": [3], "Mars": [0,7], "Mercury": [2,5],
                "Jupiter": [8,11], "Venus": [1,6], "Saturn": [9,10]}

    is_exalted  = EXALT.get(current_md) == md_sign_idx
    is_own_sign = md_sign_idx in OWN.get(current_md, [])
    is_kendra   = md_house in KENDRA
    is_upachaya = md_house in UPACHAYA

    if is_exalted or is_own_sign:
        return False  # clearly strong — Vimsottari is sufficient

    if is_kendra and not (md_house in {6, 8, 12}):
        return False  # angular and not dusthana — clear enough

    # Dusthana without dignity — ambiguous
    DUSTHANA = {6, 8, 12}
    if md_house in DUSTHANA and not is_exalted and not is_own_sign:
        return True

    # Neutral houses (2, 3, 5, 9, 11) with no special dignity — ambiguous
    if md_house not in KENDRA and md_house not in DUSTHANA:
        return True

    return False  # default: Vimsottari is clear



# ═══════════════════════════════════════════════════════════════════
# QUESTION MODE CLASSIFIER — Sprint Apr7
# Routes questions to the correct layer stack.
# Per spec: dashas load the gun, transits pull the trigger.
# ═══════════════════════════════════════════════════════════════════

# Maps symptom category keywords → instrument domain for diagnostic prompt
SYMPTOM_DOMAIN_MAP = {
    # keyword fragment → (instrument, backup_instrument)
    "losing clients":       ("career area",   "partnership area"),
    "losing money":         ("wealth area",   "transformation area"),
    "losing opportunities": ("luck area",     "career area"),
    "losing friends":       ("partnership area",      "home area"),
    "losing temper":        ("identity area",      "home area"),
    "losing focus":         ("courage area",   "identity area"),
    "stuck":                ("identity area",      "courage area"),
    "money":                ("wealth area",   "transformation area"),
    "clients":              ("career area",   "partnership area"),
    "deals":                ("partnership area",      "career area"),
    "relationship":         ("partnership area",      "home area"),
    "partner":              ("partnership area",      "home area"),
    "career":               ("career area",   "luck area"),
    "purpose":              ("luck area",     "career area"),
    "purpose":              ("luck area",     "career area"),
    "identity":             ("identity area",      "luck area"),
    "fire":                 ("courage area",    "identity area"),
    "spark":                ("creativity area",    "identity area"),
    "impostor":             ("career area",   "identity area"),
    "fraud":                ("career area",   "identity area"),
    "timing":               ("luck area",     "courage area"),
    "window":               ("luck area",     "courage area"),
    "drained":              ("identity area",      "home area"),
    "blocked":              ("identity area",      "courage area"),
    "trapped":              ("identity area",      "luck area"),
    "sleep":                ("identity area",      "home area"),
    "body":                 ("identity area",      "home area"),
    "decision":             ("courage area",   "luck area"),
    "choose":               ("courage area",   "partnership area"),
    "sabotage":             ("courage area",    "identity area"),
    "betrayed":             ("partnership area",      "work area"),
    "overlooked":           ("career area",   "gains area"),
    "invisible":            ("career area",   "partnership area"),
    "lonely":               ("partnership area",      "home area"),
    "ending":               ("luck area",     "identity area"),
    "waiting":              ("luck area",     "courage area"),
    "tested":               ("discipline area",    "identity area"),
    "punished":             ("discipline area",    "luck area"),
}

def _get_symptom_domain(question: str) -> tuple:
    """Return (primary_instrument, secondary_instrument) for a symptom question."""
    q = question.lower()
    for kw, domains in SYMPTOM_DOMAIN_MAP.items():
        if kw in q:
            return domains
    return ("System Vitals", "Fortune Vector")  # default

def _classify_question_mode(question: str) -> str:
    """
    Returns one of:
      "life_path" — D-1, D-2, D-9, D-10 only. No transits.
      "timing"    — Vimsottari + relevant transits ± Jaimini
      "daily"     — Moon + Mercury transits only

    Life-path: career direction, wealth type, marriage potential,
               relocation, life purpose, karma, billionaire potential
    Timing: when will X happen, funding window, launch date, sign date
    Daily: should I reply, today's energy, meeting outcome, this week
    """
    q = (question or "").lower().strip()

    # Daily mode keywords — short-term, day/week level
    DAILY_KW = [
        "today", "tonight", "tomorrow", "this morning", "this afternoon",
        "this evening", "right now", "should i reply", "should i respond",
        "should i send", "this meeting", "this call", "this week",
        "should i email", "should i message", "should i text",
        "how will today", "how will this meeting", "how will this call",
        "will they respond", "will he respond", "will she respond",
        "what time", "which day", "best day to",
    ]
    if any(kw in q for kw in DAILY_KW):
        return "daily"

    # Timing mode keywords — medium-term event triggers
    TIMING_KW = [
        "when will", "when does", "when should", "when can",
        "how long until", "how soon", "what month", "what year",
        "which month", "which quarter", "will it happen",
        "will i get", "will they sign", "will the deal",
        "will my funding", "will i close", "will i raise",
        "funding window", "launch date", "sign date", "close date",
        "april", "may", "june", "july", "august", "september",
        "october", "november", "december", "january", "february", "march",
        "2026", "2027", "2028", "next month", "next quarter", "next year",
        "timing", "window", "deadline", "by when", "exact date",
        "specific date", "will this customer", "will this client",
        "should i hire now", "should i launch now", "should i raise now",
    ]
    if any(kw in q for kw in TIMING_KW):
        return "timing"

    # Life-path mode — everything else
    # Explicitly life-path keywords (to be safe)
    LIFEPATH_KW = [
        "what career", "which career", "what should i do with my life",
        "wealth potential", "billionaire", "life purpose", "life path",
        "should i relocate", "should i move to", "best country",
        "marriage potential", "will i get married", "soul purpose",
        "what am i here for", "past life", "karma", "dharma",
        "what type of wealth", "wealth type", "my potential",
        "what is my", "who am i", "what kind of",
    ]
    if any(kw in q for kw in LIFEPATH_KW):
        return "life_path"

    # Symptom mode — user describing a pattern, block, or recurring problem
    SYMPTOM_KW = [
        "i keep ", "i keep losing", "i keep failing", "i keep getting",
        "i always ", "i always end up", "i always lose", "i always fail",
        "i feel stuck", "i feel blocked", "i feel like i'm going in circles",
        "nothing is working", "nothing works", "nothing seems to work",
        "every time i", "every time i try", "every time i get close",
        "something feels off", "something is off", "something is wrong",
        "why do i always", "why does this keep", "why can't i",
        "i can't seem to", "i can't close", "i can't get",
        "i struggle with", "i've been struggling", "i keep struggling",
        "pattern in my", "i notice a pattern", "repeating pattern",
        "it's been months", "it's been years", "for months now",
        "i'm stuck", "i've been stuck", "feels like a wall",
        "money keeps", "clients keep", "relationships keep",
        "deals keep falling", "opportunities keep", "people keep leaving",
        "i attract", "i keep attracting", "why do i attract",
        "blocked", "blockage", "obstacle", "resistance",
    ]
    if any(kw in q for kw in SYMPTOM_KW):
        return "symptom"

    # Default: timing (most questions are about when/whether something happens)
    return "timing"



def _is_jargon(text: str) -> bool:
    """Return True if text contains raw astrological computation language."""
    if not text:
        return True
    text_lower = text.lower()
    jargon = [
        "karakamsa", "dusthana", "mahadasha", "antardasha", "instrument lord",
        "sign aspects", "soul purpose resonance", "chara dasha",
        "power off", "sleeping", "structural load",
        "lord in", "bhava", "navamsa", "atmakaraka", "amatyakaraka",
        "upapada", "arudha", "varshphal", "masik",
    ]
    return any(j in text_lower for j in jargon)

def _safe_signal_line(signal_line: str, domain: str, language: str = "en") -> str:
    """Return signal_line if clean, otherwise return a safe ask-Antar prompt."""
    if _is_jargon(signal_line):
        if language == "es":
            return f"Pregunta a Antar sobre tu señal de {domain} esta semana."
        return f"Ask Antar about your {domain} signal this week."
    return signal_line



async def save_chat_message(
    supabase,
    chart_id: str,
    question: str,
    response_data: dict,
    language: str = "en"
) -> str:
    """
    Save a chat message (question + answer) to Supabase.
    Returns the message_id.
    
    Extracts:
    - domain from question keywords (finance/career/relationships/health)
    - question_type (timing/blockage/decision/opportunity)
    - key_date from timing_window field
    """
    import re as _re
    from datetime import datetime, timezone

    # ── Extract domain from question ──────────────────────────────
    q_lower = question.lower()
    domain = "general"
    if any(w in q_lower for w in [
        "cash", "money", "finance", "income", "revenue", "invest",
        "wealth", "salary", "profit", "business", "dinero", "plata",
        "riqueza", "ingresos", "negocio", "capital", "flujo"
    ]):
        domain = "finance"
    elif any(w in q_lower for w in [
        "career", "job", "work", "promotion", "boss", "company",
        "client", "project", "carrera", "trabajo", "empleo", "jefe"
    ]):
        domain = "career"
    elif any(w in q_lower for w in [
        "relationship", "partner", "love", "marriage", "dating",
        "relacion", "pareja", "amor", "matrimonio", "novio", "novia"
    ]):
        domain = "relationships"
    elif any(w in q_lower for w in [
        "health", "sick", "doctor", "pain", "energy", "tired",
        "salud", "enfermo", "doctor", "dolor", "energía", "cansado"
    ]):
        domain = "health"
    elif any(w in q_lower for w in [
        "move", "relocate", "travel", "city", "country",
        "mudar", "mover", "ciudad", "país", "viaje"
    ]):
        domain = "location"

    # ── Extract question type ──────────────────────────────────────
    question_type = "general"
    if any(w in q_lower for w in [
        "when", "cuándo", "how long", "cuánto tiempo", "date", "fecha"
    ]):
        question_type = "timing"
    elif any(w in q_lower for w in [
        "why", "por qué", "block", "bloqueo", "stuck", "atascado",
        "problem", "problema", "issue", "dificultad"
    ]):
        question_type = "blockage"
    elif any(w in q_lower for w in [
        "should i", "debo", "debería", "decision", "decisión",
        "choose", "elegir", "better", "mejor"
    ]):
        question_type = "decision"
    elif any(w in q_lower for w in [
        "opportunity", "oportunidad", "chance", "posibilidad",
        "good time", "buen momento", "window", "ventana"
    ]):
        question_type = "opportunity"

    # ── Extract key date from timing_window ───────────────────────
    timing_window = response_data.get("timing_window", "")
    key_date = None
    if timing_window:
        # Extract year-month patterns: "September 2026", "septiembre 2026"
        date_match = _re.search(
            r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|'
            r'septiembre|octubre|noviembre|diciembre|'
            r'january|february|march|april|may|june|july|august|'
            r'september|october|november|december)'
            r'\s+(\d{4})',
            timing_window.lower()
        )
        if date_match:
            key_date = date_match.group(0).title()
        else:
            # Try year only
            year_match = _re.search(r'(202[4-9]|203\d)', timing_window)
            if year_match:
                key_date = year_match.group(0)

    # ── Build record ──────────────────────────────────────────────
    record = {
        "chart_id": chart_id,
        "question": question,
        "plain_summary": response_data.get("plain_summary", ""),
        "signal_line": response_data.get("signal_line", ""),
        "action_item": response_data.get("action_item", ""),
        "timing_window": timing_window,
        "domain": domain,
        "question_type": question_type,
        "key_date": key_date,
        "confidence": response_data.get("signal_confidence", ""),
        "archetype_name": response_data.get("archetype_name", ""),
        "language": language,
        "why_this": response_data.get("why_this", ""),
        "bridge_practice_note": response_data.get("bridge_practice_note", ""),
        "contradiction_detected": response_data.get("contradiction_detected", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = supabase.table("chat_messages").insert(record).execute()
        if result.data:
            msg_id = result.data[0].get("id", "")
            return msg_id
    except Exception as e:
        print(f"save_chat_message error: {e}")

    return ""


async def get_recent_questions(
    supabase,
    chart_id: str,
    limit: int = 5,
    domain: str = None
) -> list:
    """
    Get recent Ask Antar questions for this chart.
    Used to build oracle_context for follow-up questions.
    """
    try:
        query = supabase.table("chat_messages").select(
            "question, signal_line, action_item, domain, key_date, created_at"
        ).eq("chart_id", chart_id).order(
            "created_at", desc=True
        ).limit(limit)

        if domain:
            query = query.eq("domain", domain)

        result = query.execute()
        return result.data or []
    except Exception as e:
        print(f"get_recent_questions error: {e}")
        return []


async def get_domain_pattern(supabase, chart_id: str) -> dict:
    """
    Returns a dict of how many times each domain has been asked.
    Used to personalise the dashboard (show finance signals first if
    user mostly asks about money).
    """
    try:
        result = supabase.table("chat_messages").select(
            "domain"
        ).eq("chart_id", chart_id).execute()

        if not result.data:
            return {}

        counts = {}
        for row in result.data:
            d = row.get("domain", "general")
            counts[d] = counts.get(d, 0) + 1

        # Sort by frequency
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
    except Exception as e:
        print(f"get_domain_pattern error: {e}")
        return {}


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Chart ─────────────────────────────────────────────────────────────────────

@app.get("/api/v1/chart/{chart_id}/signature")
async def get_chart_signature(chart_id: str, authorization: Optional[str] = Header(None)):
    """
    Returns natal planet signatures + character archetype for Blueprint tab.
    Computes and stores on first call if not already cached.
    """
    try:
        row = supabase.table("charts")             .select("planet_signatures,character_archetype,chart_data,first_name,name")             .eq("id", chart_id)             .single()             .execute()

        if not row.data:
            return {"error": "Chart not found"}

        planet_sigs  = row.data.get("planet_signatures")
        char_arch    = row.data.get("character_archetype")

        # Lazy compute if missing
        if not planet_sigs or not char_arch:
            chart_data = row.data.get("chart_data") or {}
            planet_sigs  = compute_natal_signatures(chart_data)
            char_arch    = derive_archetype(planet_sigs)
            supabase.table("charts").update({
                "planet_signatures":   planet_sigs,
                "character_archetype": char_arch,
            }).eq("id", chart_id).execute()

        first_name = row.data.get("first_name") or row.data.get("name", "")

        return {
            "chart_id":            chart_id,
            "first_name":          first_name,
            "planet_signatures":   planet_sigs,
            "character_archetype": char_arch,
        }

    except Exception as e:
        print(f"[signature] Error for {chart_id}: {e}")
        return {"error": str(e)}




# ─────────────────────────────────────────────────────────────────────────────
# PAST-EVENTS: Signature verification screen
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/chart/{chart_id}/past-events")
async def get_past_events(
    chart_id: str,
    min_confidence: int = 5,
    max_predictions: int = 5,
    authorization: Optional[str] = Header(None),
):
    """
    Returns high-confidence past-event predictions for the chart.
    Used by onboarding signature verification screen (Lovable).

    Query params:
      min_confidence : filter threshold 1-10 (default 5 = "moderate")
      max_predictions: cap on number returned (default 5)
    """
    try:
        from antar_engine.dasha_event_mapper import (
            map_all_events,
            find_event_window,
            EVENT_DISPLAY_LABELS,
            EVENT_DESCRIPTION,
            build_energy_explanation,
        )

        # ── 1. Fetch chart row ────────────────────────────────────────────
        chart_res = supabase.table("charts").select(
            "chart_data,birth_date,first_name,name,lagna_sign,marital_status,children_status"
        ).eq("id", chart_id).single().execute()

        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")

        cd          = chart_res.data.get("chart_data") or {}
        birth_date  = str(chart_res.data.get("birth_date", ""))
        birth_year  = int(birth_date[:4]) if birth_date and birth_date[:4].isdigit() else 1980
        lagna_raw   = cd.get("lagna") or {}
        lagna       = (lagna_raw.get("sign") if isinstance(lagna_raw, dict) else lagna_raw)                       or chart_res.data.get("lagna_sign") or "Capricorn"
        first_name  = chart_res.data.get("first_name") or chart_res.data.get("name") or ""
        today_str   = datetime.now().strftime("%Y-%m-%d")
        marital_status   = (chart_res.data.get("marital_status") or "").lower().strip()
        children_status  = (chart_res.data.get("children_status") or "").lower().strip()
        print(f"[PAST-EVENTS] chart={chart_id} lagna={lagna} marital={marital_status!r} children={children_status!r}")

        # ── 2. Fetch vimsottari antardashas ───────────────────────────────
        ads_res = supabase.table("dasha_periods")             .select("planet_or_sign,start_date,end_date,level,type,metadata")             .eq("chart_id", chart_id)             .eq("system", "vimsottari")             .order("start_date")             .execute()

        ads = [
            r for r in (ads_res.data or [])
            if r.get("level") == 2
            or str(r.get("type", "")).lower() in ("antardasha", "ad", "2")
        ]

        if not ads:
            # graceful: no dasha data yet
            return {
                "chart_id":             chart_id,
                "lagna":                lagna,
                "first_name":           first_name,
                "predictions":          [],
                "predictions_filtered": 0,
                "predictions_shown":    0,
                "fallback_message":     (
                    "Your dasha sequence hasn't been computed yet. "
                    "Visit your dashboard to generate your full blueprint."
                ),
            }

        # ── 3. Run all event windows ──────────────────────────────────────
        # map_all_events covers: serious_partnership_began, major_relocation,
        #   family_expansion_first, family_expansion_second, serious_partnership_ended
        raw_map = map_all_events(birth_year, lagna, ads)

        # Additional events not covered by map_all_events
        # map_future_events already scans all event types

        # ── 4. Score, filter, format ──────────────────────────────────────
        def _confidence_label(score: int) -> str:
            if score >= 8:
                return "high"
            if score >= 5:
                return "moderate"
            return "low"

        def _dasha_label(w: dict) -> str:
            md  = w.get("parent_md", "")
            ad  = w.get("planet", "")
            pd  = w.get("pd_lord", "")
            lbl = f"{md} MD + {ad} AD"
            if pd:
                lbl += f" + {pd} PD"
            return lbl

        def _human_window(start: str, end: str) -> str:
            try:
                s = datetime.fromisoformat(start)
                e = datetime.fromisoformat(end)
                if s.year == e.year and s.month == e.month:
                    # Same calendar month: "June 2006" not "June to June 2006"
                    return s.strftime('%B %Y')
                if s.year == e.year:
                    return f"{s.strftime('%B')} to {e.strftime('%B %Y')}"
                return f"{s.strftime('%B %Y')} to {e.strftime('%B %Y')}"
            except Exception:
                return f"{start[:7]} to {end[:7]}"

        CATEGORY_MAP = {
            "serious_partnership_began":  "relationship",
            "serious_partnership_ended":  "relationship",
            "family_expansion_first":     "family",
            "family_expansion_second":    "family",
            "major_relocation":           "transition",
            "major_acquisition":          "material",
            "career_pivot":               "transition",
            "loss_of_mother":             "loss",
            "loss_of_father":             "loss",
            "professional_setback":       "material",
            "legal_entanglement":         "conflict",
            "financial_disruption":       "material",
        }

        all_predictions = []
        for event_type, w in raw_map.items():
            if not w:
                continue
            win_end = w.get("window_end") or w.get("end") or ""
            # Keep only past events (window end before today)
            if win_end and win_end > today_str:
                continue
            score           = w.get("score", 5)
            candidate_count = w.get("candidate_count", 1)
            # Normalize priority score (1-10) to base confidence (2-7).
            # Top-priority planets (score=10) start at 7, not 10, so signals
            # below can differentiate without everything saturating at the cap.
            # Base: scale 0.6 keeps top-priority (score=10) capped at 6.
            # This prevents everything saturating at 9 — best unvalidated
            # event scores 6+1+1=8; multi-chart validated can reach 9 via
            # future natal-promise bonus.
            _base      = max(2, min(6, round(score * 0.6)))
            # +1 if the PD precision drill found a sub-period (higher certainty)
            _pd_bonus  = 1 if w.get("pd_lord") else 0
            # +1 if THREE or more candidate ADs corroborate (raised bar from 2→3)
            _corr      = 1 if candidate_count >= 3 else 0
            confidence = min(10, _base + _pd_bonus + _corr)
            # Fix C (confidence tier): ended without a preceding began → low confidence
            if event_type == "serious_partnership_ended" and w.get("_dependency_fail"):
                confidence = min(confidence, 3)
            # Fix C2: if began exists but itself scores below 5, cap ended at began level
            if event_type == "serious_partnership_ended":
                _began_w = raw_map.get("serious_partnership_began")
                if _began_w:
                    _began_score = _began_w.get("score", 5)
                    _began_base  = max(2, min(6, round(_began_score * 0.6)))
                    _began_pd    = 1 if _began_w.get("pd_lord") else 0
                    _began_conf  = _began_base + _began_pd
                    if _began_conf < 5:
                        confidence = min(confidence, _began_conf)
                        print(f"[CONF-C2] began_conf={_began_conf} → capping ended at {confidence}")
            # Fix E: children events require a detected partnership as prerequisite
            if event_type in ("family_expansion_first", "family_expansion_second"):
                if not raw_map.get("serious_partnership_began"):
                    confidence = max(1, confidence - 2)
            # Fix F: marital status reality check — cap based on known life status
            # Single/never_married → partnership events are speculative
            if marital_status in ("single", "never_married", "unmarried"):
                if event_type in ("serious_partnership_began", "serious_partnership_ended"):
                    confidence = min(confidence, 4)
            # Currently married → ending a current partnership is a false positive
            if marital_status in ("married", "partnered", "in_relationship", "in_a_relationship"):
                if event_type == "serious_partnership_ended":
                    confidence = min(confidence, 3)
            # Fix G: children status reality check
            if children_status in ("none", "no_children", "no_children_unsure", "childless"):
                if event_type in ("family_expansion_first", "family_expansion_second"):
                    confidence = min(confidence, 4)
            print(f"[CONF] event={event_type} score={score} base={_base} pd={_pd_bonus} corr={_corr} final={confidence} marital={marital_status!r} children={children_status!r}")
            if confidence < min_confidence:
                continue
            win_start = w.get("window_start") or w.get("start") or ""
            # Build energy explanation dict
            _energy_pred = {
                "md_lord":       w.get("parent_md"),
                "ad_lord":       w.get("planet"),
                "pd_lord":       w.get("pd_lord"),
                "transit_planet": w.get("transit_planet"),
            }
            all_predictions.append({
                "event_type":        event_type,
                "display_label":     EVENT_DISPLAY_LABELS.get(event_type, event_type),
                "description":       EVENT_DESCRIPTION.get(event_type, ""),
                "category":          CATEGORY_MAP.get(event_type, "other"),
                "window": {
                    "start":          win_start,
                    "end":            win_end,
                    "precision":      w.get("precision", "AD"),
                    "human_readable": _human_window(win_start, win_end) if win_start and win_end else "",
                },
                "dasha":             _dasha_label(w),
                "confidence":        confidence,
                "confidence_label":  _confidence_label(confidence),
                "explanation_short": w.get("reason", ""),
                "energy_explanation": build_energy_explanation(_energy_pred, event_type, lagna),
                "user_response":     None,
            })

        # Sort by confidence DESC
        all_predictions.sort(key=lambda x: -x["confidence"])
        shown             = all_predictions[:max_predictions]
        total_past        = len(all_predictions)
        filtered_out      = total_past - len(shown)

        # Fallback message for sparse charts
        fallback = None
        if len(shown) < 2:
            fallback = (
                "Your chart speaks in nuance, not headlines. Most charts have a "
                "few clear life events; yours threads its story through quieter "
                "patterns. Continue to your dashboard to explore your blueprint."
            )

        return {
            "chart_id":             chart_id,
            "lagna":                lagna,
            "first_name":           first_name,
            "predictions":          shown,
            "predictions_filtered": filtered_out,
            "predictions_shown":    len(shown),
            "fallback_message":     fallback,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[past-events] Error for {chart_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compute past events: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# UPCOMING-THEMES  —  LLM narration helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _build_upcoming_themes_prompt(chart_data, profile, future_windows, rahu_md_ads=None, voice_mode="mentor"):
    """
    Build the 3-layer prompt for Claude to narrate upcoming themes.
    voice_mode: 'coach' (no planet names, pure energy language) or 'mentor' (planet names + parentheticals)
    Returns the full prompt string.
    """
    from datetime import datetime as _dt

    cd = chart_data or {}
    planets = cd.get("planets", {})
    lagna_obj = cd.get("lagna", {})
    lagna = lagna_obj.get("sign") if isinstance(lagna_obj, dict) else lagna_obj

    # Layer 1: Chart DNA
    PLANET_PARENS = {
        "Sun": "identity, authority, vitality",
        "Moon": "emotions, mind, mother, nurturing",
        "Mars": "action, drive, courage, conflict",
        "Mercury": "communication, intellect, business, travel",
        "Jupiter": "growth, wisdom, children, expansion",
        "Venus": "love, beauty, partnership, money",
        "Saturn": "discipline, time, structure, hard lessons",
        "Rahu": "ambition, hunger, foreign, breakthrough",
        "Ketu": "detachment, liberation, past karma, spirituality",
    }
    HOUSE_LABELS = {
        1: "self & identity area", 2: "wealth & family area",
        3: "courage & communication area", 4: "home & foundation area",
        5: "children & creativity area", 6: "daily work & service area",
        7: "partnership & marriage area", 8: "transformation & hidden area",
        9: "luck & long journeys area", 10: "career & public life area",
        11: "gains & networks area", 12: "foreign & transcendence area",
    }

    planet_lines = []
    for pname, pdata in planets.items():
        if isinstance(pdata, dict):
            sign = pdata.get("sign", "?")
            house = pdata.get("house", 0)
            nak = pdata.get("nakshatra", "")
            area = HOUSE_LABELS.get(house, f"house {house}")
            parens = PLANET_PARENS.get(pname, "")
            planet_lines.append(f"    {pname} ({parens}) in {sign}, {area}, nakshatra {nak}")

    # Detect stelliums (3+ planets in same house)
    house_counts = {}
    for pname, pdata in planets.items():
        if isinstance(pdata, dict):
            h = pdata.get("house", 0)
            house_counts.setdefault(h, []).append(pname)
    stellium_lines = []
    for h, plist in house_counts.items():
        if len(plist) >= 3:
            area = HOUSE_LABELS.get(h, f"house {h}")
            stellium_lines.append(
                f"  Stellium: {' + '.join(plist)} in {area} — modern wealth/power signal"
            )

    # Layer 2: DKP
    first_name = profile.get("first_name") or profile.get("name") or "this person"
    birth_country = profile.get("birth_country") or "unknown"
    current_country = profile.get("current_country") or "unknown"
    current_city = profile.get("current_city") or ""
    career_stage = profile.get("career_stage") or "unknown"
    marital = profile.get("marital_status") or "unknown"
    children = profile.get("children_status") or "unknown"
    moon_sign = profile.get("moon_sign") or cd.get("moon_sign") or "unknown"
    moon_nak = profile.get("moon_nakshatra") or cd.get("moon_nakshatra") or "unknown"
    atmakaraka = cd.get("atmakaraka") or "unknown"
    birth_date = profile.get("birth_date") or ""

    age = ""
    if birth_date:
        try:
            by = int(str(birth_date)[:4])
            age = str(_dt.now().year - by)
        except Exception:
            pass

    # Nakshatra group (via nakshatra_groups module)
    from antar_engine.nakshatra_groups import get_nakshatra_group, get_group_profile, format_nakshatra_for_prompt
    _nak_group_num = get_nakshatra_group(moon_nak)
    _nak_profile = get_group_profile(_nak_group_num)
    if _nak_group_num == 1:
        nak_group = "Group 1 — creation energy, action-oriented, high physical vitality"
    elif _nak_group_num == 2:
        nak_group = "Group 2 — sustaining energy, strategic, structure-minded"
    elif _nak_group_num == 3:
        nak_group = "Group 3 — wisdom energy, reflective, pattern-recognition, guide archetype"
    else:
        nak_group = "unknown"
    nak_tone = _nak_profile["tone_instruction"]
    _nak_extra_context = format_nakshatra_for_prompt(moon_nak)

    # Voice mode instruction
    if voice_mode == "coach":
        voice_instruction = """
══════════════════════════════════════════════
VOICE MODE: COACH (this user is new — no planet names)
══════════════════════════════════════════════
CRITICAL: Do NOT use any planet names (Sun, Moon, Mars, Mercury, Jupiter, Venus,
Saturn, Rahu, Ketu). Instead, refer to energies by their QUALITY:
  Sun      → "your identity and authority energy"
  Moon     → "your emotional and nurturing energy"
  Mars     → "your drive and action energy"
  Mercury  → "your communication and intellect energy"
  Jupiter  → "a growth and wisdom energy" (use "a" for arriving energies)
  Venus    → "your love and partnership energy"
  Saturn   → "your discipline and structure energy"
  Rahu     → "your ambition and breakthrough energy"
  Ketu     → "your letting-go and liberation energy"

For life areas, use descriptive language:
  Instead of "your gains and networks area" say "the part of your life connected
  to gains, friendships, and your professional network"
  Instead of "your foreign and transcendence area" say "your inner world, foreign
  connections, and what you let go of"

For dasha terms:
  AD → "the first stretch" / "the next stretch" (not "sub-chapter")
  PD → "the moment things crystallize" (not "inner window")

For patterns:
  Stellium → "three powerful energies clustering together"
  Conjunction → "two energies working side by side"

The goal: the user FEELS the reading without learning new vocabulary.
Everything should sound like it's describing a part of THEM, not external forces.
"""
    else:
        voice_instruction = """
══════════════════════════════════════════════
VOICE MODE: MENTOR (this user is familiar with Vedic terminology)
══════════════════════════════════════════════
Use planet names with parenthetical on first mention:
  "Saturn planet of (discipline, structure)" — then "Saturn" alone after.
Use area labels: "your gains and networks area".
Use dasha translations: chapter, sub-chapter, inner window.
The user has built vocabulary through prior sessions — speak to their knowledge.
"""

    # Layer 3: Future windows
    window_lines = []
    for w in future_windows:
        et = w.get("event_type", "unknown")
        ws = w.get("window_start", "?")
        we = w.get("window_end", "?")
        planet = w.get("planet", "?")
        parent = w.get("parent_md", "?")
        score = w.get("score", 0)
        window_lines.append(f"    {et}: {ws} to {we} ({parent} chapter + {planet} sub-chapter, score={score})")

    # Rahu MD sub-chapters if available
    rahu_lines = []
    if rahu_md_ads:
        for ad in rahu_md_ads:
            lord = ad.get("planet_or_sign", "?")
            s = (ad.get("start_date") or "")[:10]
            e = (ad.get("end_date") or "")[:10]
            parens = PLANET_PARENS.get(lord, "")
            rahu_lines.append(f"    Rahu-{lord} ({parens}): {s} to {e}")

    # Planet → Chakra/Center mapping
    PLANET_CENTER = {
        "Sun": "Solar Plexus center — where confidence, willpower, and identity live",
        "Moon": "Sacral center — where emotions, intuition, and nurturing live",
        "Mars": "Root center — where security, physical vitality, and drive live",
        "Mercury": "Throat center — where communication, intellect, and expression live",
        "Jupiter": "Crown center — where wisdom, expansion, and higher purpose live",
        "Venus": "Heart center — where love, beauty, and partnership live",
        "Saturn": "Root center — where discipline, structure, and endurance live",
        "Rahu": "Third Eye center — where vision, ambition, and breakthrough live",
        "Ketu": "Crown center — where detachment, liberation, and spirituality live",
    }
    # Determine the primary planet driving the most significant window
    primary_planet = ""
    if future_windows:
        _fw0 = future_windows[0]
        primary_planet = _fw0.get("parent_md") or _fw0.get("planet") or ""
    center_link = ""
    if primary_planet and primary_planet in PLANET_CENTER:
        center_link = f"{primary_planet} · {PLANET_CENTER[primary_planet].split(' — ')[0]}"

    prompt = f"""You are Antar — a senior advisor who has studied this person's chart for years
and genuinely cares about their outcome. Not a fortune teller. Not a therapist.
Not a textbook. A mentor who sees the pattern clearly and tells them what to do about it.

You are writing a "Coming Up" prediction card for their dashboard.

THREE CORE PRINCIPLES:
1. Acknowledge the human, then show the chart
2. Reframe any weakness or difficulty as a natural phase, never as broken
3. End with agency — the user drives, Antar navigates

You have three layers of context:
1. Their birth chart (natal positions, karakas)
2. Their life context (DKP — where they live, what they do, who they are now)
3. The upcoming dasha window(s)

{nak_tone}
{_nak_extra_context}
{voice_instruction}
══════════════════════════════════════════════
VOCABULARY RULES (STRICT — violating these is a failure):
══════════════════════════════════════════════

PLANET NAMES:
  First mention: "Mars planet of (action, drive, energy)" — full parenthetical
  Subsequent mentions: "Mars" alone

HOUSE AREAS — NEVER use house numbers. Always say:
  H1="your identity and self area"  H2="your wealth and family area"
  H3="your courage and communication area"  H4="your home and foundation area"
  H5="your children and creativity area"  H6="your daily work and service area"
  H7="your partnership and marriage area"  H8="your transformation and hidden area"
  H9="your luck and long journeys area"  H10="your career and public life area"
  H11="your gains and networks area"  H12="your foreign and transcendence area"

DASHA PERIODS — NEVER use MD, AD, PD, mahadasha, antardasha, pratyantar, lord, lagna, dasha:
  MD = "chapter" (the big arc)
  AD = "sub-chapter" (the current focus)
  PD = "inner window" (the specific moment)

TIME LANGUAGE: "window" not "period". "chapter" not "phase". "transition" not "change".

CHAKRA/CENTER NAMES — use English: Root, Sacral, Solar Plexus, Heart, Throat, Third Eye, Crown
  First mention: add what it governs ("Your Root center — where security and physical vitality live")
  Subsequent: "Root center" alone

BANNED WORDS/PHRASES (never use these):
  "may" or "could" when stating chart facts — be direct
  "it seems like" — commit to the reading
  "based on your chart" — everything is; don't state the obvious
  "the universe" — too generic
  "manifest" — overused
  "journey" — overused
  "aligned" as vague positive
  "vibration" — use "frequency" or "energy"
  "divine timing" — say "your chart's timing"
  "trust the process" — give something specific to trust
  "everything happens for a reason" — tell them the reason
  "unfortunately" — reframe as natural phase
  "your chart says" — say "your energy map shows" or "the pattern in your chart is"

══════════════════════════════════════════════
METAPHOR LIBRARY (use these, not generic ones):
══════════════════════════════════════════════

For low/weak energy: "walking through water", "the pause between exhale and inhale",
  "a battery recharging before the next sprint", "soil resting between planting seasons"
For transition/chapter change: "the gear shift between third and fourth",
  "one chapter closing so the binding can hold the next"
For strong/activated energy: "a current that's been building and finally breaks the surface",
  "the ignition, not the spark — everything that follows is momentum",
  "three rivers converging into one channel"
For stellium/convergence: "three instruments playing the same note at different octaves",
  "a triple lock opening simultaneously"
DO NOT USE: war metaphors, death metaphors, gambling metaphors, generic nature metaphors

══════════════════════════════════════════════
ANTI-PATTERNS (what Antar NEVER does):
══════════════════════════════════════════════
- NEVER predict death or loss
- NEVER tell a married user their marriage will end
- NEVER end with a follow-up question ("Want me to explore...?" — NO)
- NEVER give a menu of 5 actions (one micro-action + one deeper practice, max two)
- NEVER apologize for what the chart shows — reframe as natural
- NEVER use astrology to explain away accountability

══════════════════════════════════════════════
COMING UP CARD FORMAT:
══════════════════════════════════════════════

Write a prediction for the most significant upcoming window.
- Headline: max 8 words, punchy, active voice
- Body: 150-200 words. Connect chart → life context → action.
- Show planet + center connection in the body naturally
- If a major chapter transition is happening (e.g. Mars→Rahu), lead with that — it's the headline
- Caution: one sentence — what to watch for
- YOUR MOVE: one specific, time-bound action before this window opens
- Energy tags: 2-4 chips for visual scanning
- Center link: which planet · which center is most activated

Return ONLY valid JSON, no markdown fences, no other text:
{{
  "headline": "short punchy headline, max 8 words",
  "body": "the prediction text, 150-200 words",
  "caution": "one sentence — what to watch for",
  "your_move": "one specific action before this window opens",
  "energy_tags": ["tag1", "tag2", "tag3"],
  "center_link": "{center_link}"
}}

══════════════════════════════════════════════
CHART CONTEXT:
══════════════════════════════════════════════
  Lagna: {lagna}
  Moon: {moon_sign} / {moon_nak} ({nak_group})
  Atmakaraka: {atmakaraka}
  Natal positions:
{chr(10).join(planet_lines)}
{chr(10).join(stellium_lines) if stellium_lines else "  No stelliums detected."}

LIFE CONTEXT (DKP):
  DESHA: Lives in {current_city + ", " if current_city else ""}{current_country}. Born in {birth_country}.
  KALA: Age {age}. {_dt.now().strftime("%B %Y")}.
        Career stage: {career_stage}.
  PATRA: Marital status: {marital}. Children: {children}.

UPCOMING WINDOWS (from mapper):
{chr(10).join(window_lines) if window_lines else "  No specific windows identified by mapper."}
{"MAJOR CHAPTER SUB-PERIOD SEQUENCE:" if rahu_lines else ""}
{chr(10).join(rahu_lines) if rahu_lines else ""}

REFERENCE EXAMPLE (for tone and structure — do NOT copy content):
HEADLINE: Your 18-Year Expansion Chapter Ignites
BODY: What you've been building under Mars planet of (action, drive, courage) — the
infrastructure, the co-founder relationship, the 17-country payment system — was
preparation. August 2026 is not a transition. It is an ignition. Rahu planet of
(ambition, breakthrough, foreign) begins its 18-year chapter activating the most
powerful cluster in your chart: three planets gathered in your gains and networks
area fire simultaneously. Your Third Eye center — where vision and breakthrough
live — is the energy channel opening here.
CAUTION: Rahu amplifies everything including overextension — the first 6 months
can feel like drinking from a firehose.
YOUR MOVE: Lock one anchor market before August — a specific target, a specific
segment — so when Rahu ignites, you're accelerating something already moving.
"""
    return prompt


import json as _json
import re as _re


async def _get_or_generate_upcoming_themes_llm(
    chart_id: str,
    chart_data: dict,
    profile: dict,
    future_windows: list,
    rahu_md_ads: list = None,
    refresh: bool = False,
    voice_mode: str = "coach",
):
    """
    Get cached Claude narration or generate fresh.
    Cache TTL: 30 days. Cache is invalidated if voice_mode changes.
    """
    from datetime import datetime, timedelta

    # Check cache first (unless refresh forced)
    if not refresh:
        try:
            cache_row = supabase.table("charts").select(
                "upcoming_themes_cache, upcoming_themes_cached_at"
            ).eq("id", chart_id).single().execute()
            if cache_row.data:
                cached = cache_row.data.get("upcoming_themes_cache")
                cached_at = cache_row.data.get("upcoming_themes_cached_at")
                if cached and cached_at:
                    # Invalidate cache if voice_mode changed
                    cached_vm = cached.get("_voice_mode") if isinstance(cached, dict) else None
                    if cached_vm and cached_vm != voice_mode:
                        print(f"[upcoming-themes-llm] Voice mode changed ({cached_vm}→{voice_mode}), regenerating")
                    else:
                        try:
                            cached_dt = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
                            now = datetime.now(cached_dt.tzinfo) if cached_dt.tzinfo else datetime.now()
                            if now - cached_dt < timedelta(days=30):
                                print(f"[upcoming-themes-llm] Cache hit for {chart_id} (voice={voice_mode})")
                                return cached
                        except Exception:
                            pass  # Stale or bad timestamp — regenerate
        except Exception as e:
            print(f"[upcoming-themes-llm] Cache read error: {e}")

    # Build prompt
    prompt = _build_upcoming_themes_prompt(chart_data, profile, future_windows, rahu_md_ads, voice_mode=voice_mode)

    # Call Claude (async — uses the global claude_client)
    print(f"[upcoming-themes-llm] Generating for {chart_id}...")
    try:
        resp = await claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = resp.content[0].text
        # Parse JSON from response (strip markdown fences if present)
        clean = _re.sub(r"```json\s*|```\s*", "", raw_text).strip()
        result = _json.loads(clean)
        # Tag with voice mode so cache can be invalidated on mode change
        result["_voice_mode"] = voice_mode

        # Cache in Supabase (fire-and-forget — don't block on failure)
        try:
            supabase.table("charts").update({
                "upcoming_themes_cache": result,
                "upcoming_themes_cached_at": datetime.now().isoformat(),
            }).eq("id", chart_id).execute()
            print(f"[upcoming-themes-llm] Generated + cached for {chart_id} (voice={voice_mode})")
        except Exception as ce:
            print(f"[upcoming-themes-llm] Cache write error (non-fatal): {ce}")

        return result
    except Exception as e:
        print(f"[upcoming-themes-llm] Claude error for {chart_id}: {e}")
        return None


@app.get("/api/v1/chart/{chart_id}/upcoming-themes")
async def get_upcoming_themes(
    chart_id: str,
    min_confidence: int = 5,
    max_predictions: int = 3,
    months_ahead: int = 24,
    refresh: bool = False,
    authorization: Optional[str] = Header(None),
):
    """
    Returns high-confidence FUTURE event predictions for the chart.
    Used by the dashboard "Coming Up" module.

    Query params:
      min_confidence : filter threshold 1-10 (default 5)
      max_predictions: cap on number returned (default 3)
      months_ahead   : look-ahead window in months (default 24)
    """
    try:
        from antar_engine.dasha_event_mapper import (
            map_future_events,
            find_event_window,
            EVENT_DISPLAY_LABELS,
            EVENT_DESCRIPTION,
            build_energy_explanation,
        )

        # ── 1. Fetch chart row ────────────────────────────────────────────
        chart_res = supabase.table("charts").select(
            "chart_data,birth_date,first_name,name,lagna_sign,marital_status,children_status,voice_mode"
        ).eq("id", chart_id).single().execute()

        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")

        cd          = chart_res.data.get("chart_data") or {}
        birth_date  = str(chart_res.data.get("birth_date", ""))
        birth_year  = int(birth_date[:4]) if birth_date and birth_date[:4].isdigit() else 1980
        lagna_raw   = cd.get("lagna") or {}
        lagna       = (lagna_raw.get("sign") if isinstance(lagna_raw, dict) else lagna_raw)                        or chart_res.data.get("lagna_sign") or "Capricorn"
        first_name  = chart_res.data.get("first_name") or chart_res.data.get("name") or ""
        today_str   = datetime.now().strftime("%Y-%m-%d")
        cutoff_date = (datetime.now() + timedelta(days=months_ahead * 30)).strftime("%Y-%m-%d")
        marital_status  = (chart_res.data.get("marital_status") or "").lower().strip()
        children_status = (chart_res.data.get("children_status") or "").lower().strip()

        # Voice mode: 'coach' (default for new users) or 'mentor' (graduated)
        _vm_raw = (chart_res.data.get("voice_mode") or "coach").lower().strip()
        voice_mode = _vm_raw if _vm_raw in ("coach", "mentor") else "coach"
        print(f"[UPCOMING-THEMES] chart={chart_id} lagna={lagna} voice={voice_mode} look_ahead={months_ahead}mo cutoff={cutoff_date}")

        # ── 2. Fetch vimsottari antardashas ───────────────────────────────
        ads_res = supabase.table("dasha_periods")             .select("planet_or_sign,start_date,end_date,level,type,metadata")             .eq("chart_id", chart_id)             .eq("system", "vimsottari")             .order("start_date")             .execute()

        ads = [
            r for r in (ads_res.data or [])
            if r.get("level") == 2
            or str(r.get("type", "")).lower() in ("antardasha", "ad", "2")
        ]

        if not ads:
            return {
                "chart_id":      chart_id,
                "lagna":         lagna,
                "first_name":    first_name,
                "themes":        [],
                "themes_shown":  0,
                "stable_message": (
                    "Your dasha sequence hasn't been computed yet. "
                    "Visit your dashboard to generate your full blueprint."
                ),
            }

        # ── 3. Run all event windows (same as past-events) ────────────────
        # Extract natal planets for nakshatra PD tightening
        natal_planets = cd.get("planets", {})

        raw_map = map_future_events(
            lagna, birth_year, ads,
            from_date=today_str,
            to_date=cutoff_date,
            natal_planets=natal_planets,
        )

        for extra_event in ("loss_of_mother", "major_acquisition"):
            if extra_event not in raw_map:
                raw_map[extra_event] = find_event_window(
                    extra_event, lagna, birth_year, ads
                )

        # ── 4. Confidence helpers (identical logic to past-events) ────────
        def _confidence_label(score: int) -> str:
            if score >= 8: return "high"
            if score >= 5: return "moderate"
            return "low"

        def _dasha_label(w: dict) -> str:
            md  = w.get("parent_md", "")
            ad  = w.get("planet", "")
            pd  = w.get("pd_lord", "")
            lbl = f"{md} MD + {ad} AD"
            if pd:
                lbl += f" + {pd} PD"
            return lbl

        def _human_window(start: str, end: str) -> str:
            try:
                s = datetime.fromisoformat(start)
                e = datetime.fromisoformat(end)
                if s.year == e.year and s.month == e.month:
                    return s.strftime('%B %Y')
                if s.year == e.year:
                    return f"{s.strftime('%B')} to {e.strftime('%B %Y')}"
                return f"{s.strftime('%B %Y')} to {e.strftime('%B %Y')}"
            except Exception:
                return f"{start[:7]} to {end[:7]}"

        def _months_until(date_str: str) -> int:
            try:
                d   = datetime.fromisoformat(date_str)
                now = datetime.now()
                return max(0, (d.year - now.year) * 12 + (d.month - now.month))
            except Exception:
                return 0

        CATEGORY_MAP_LOCAL = {
            "serious_partnership_began":  "relationship",
            "serious_partnership_ended":  "relationship",
            "family_expansion_first":     "family",
            "family_expansion_second":    "family",
            "major_relocation":           "transition",
            "major_acquisition":          "material",
            "career_pivot":               "transition",
            "loss_of_mother":             "loss",
            "loss_of_father":             "loss",
            "professional_setback":       "material",
            "legal_entanglement":         "conflict",
            "financial_disruption":       "material",
        }

        # ── 5. Score + filter to FUTURE windows ──────────────────────────

        # Events that should NEVER appear on dashboard Coming Up
        _EXCLUDE_FROM_UPCOMING = {
            'loss_of_mother',
            'loss_of_father',
        }

        future_predictions = []
        for event_type, w in raw_map.items():
            if not w:
                continue

            # ── QUALITY RULES ──────────────────────────────────────────
            # Rule 1: NEVER show death/loss predictions on dashboard.
            # These are deeply sensitive. Users should only encounter them
            # in Ask Antar if they specifically ask, never on a card.
            if event_type in _EXCLUDE_FROM_UPCOMING:
                continue

            # Rule 2: Don't predict "first child" if user already has children.
            # The mapper doesn't distinguish "first ever" from "next" — so if
            # children_status indicates existing children, skip this event type.
            if event_type == 'family_expansion_first':
                if children_status in (
                    'has_children', 'has_child', 'one', 'two', 'three',
                    '1', '2', '3', '4', 'multiple'
                ):
                    continue

            # Rule 3: Don't predict "partnership ended" if user is already
            # single, divorced, or separated — can't end what doesn't exist.
            if event_type == 'serious_partnership_ended':
                if marital_status in (
                    'single', 'divorced', 'separated', 'never_married',
                    'unmarried', 'widowed'
                ):
                    continue
            win_start = w.get("window_start") or w.get("start") or ""
            win_end   = w.get("window_end")   or w.get("end")   or ""

            # FUTURE only: window starts on/after today and within look-ahead cutoff
            if not win_start or win_start < today_str or win_start > cutoff_date:
                continue

            score           = w.get("score", 5)
            candidate_count = w.get("candidate_count", 1)
            _base      = max(2, min(6, round(score * 0.6)))
            _pd_bonus  = 1 if w.get("pd_lord") else 0
            _corr      = 1 if candidate_count >= 3 else 0
            confidence = min(10, _base + _pd_bonus + _corr)

            # Same reality-check adjustments as past-events
            if event_type == "serious_partnership_ended" and w.get("_dependency_fail"):
                confidence = min(confidence, 3)
            if event_type == "serious_partnership_ended":
                _began_w = raw_map.get("serious_partnership_began")
                if _began_w:
                    _began_conf = max(2, min(6, round(_began_w.get("score", 5) * 0.6)))                                   + (1 if _began_w.get("pd_lord") else 0)
                    if _began_conf < 5:
                        confidence = min(confidence, _began_conf)
            if event_type in ("family_expansion_first", "family_expansion_second"):
                if not raw_map.get("serious_partnership_began"):
                    confidence = max(1, confidence - 2)
            if marital_status in ("single", "never_married", "unmarried"):
                if event_type in ("serious_partnership_began", "serious_partnership_ended"):
                    confidence = min(confidence, 4)
            if marital_status in ("married", "partnered", "in_relationship", "in_a_relationship"):
                if event_type == "serious_partnership_ended":
                    confidence = min(confidence, 3)
            if children_status in ("none", "no_children", "no_children_unsure", "childless"):
                if event_type in ("family_expansion_first", "family_expansion_second"):
                    confidence = min(confidence, 4)

            print(f"[UPCOMING-CONF] event={event_type} score={score} base={_base} pd={_pd_bonus} corr={_corr} final={confidence}")

            if confidence < min_confidence:
                continue

            _energy_pred = {
                "md_lord":       w.get("parent_md"),
                "ad_lord":       w.get("planet"),
                "pd_lord":       w.get("pd_lord"),
                "transit_planet": w.get("transit_planet"),
            }

            future_predictions.append({
                "event_type":        event_type,
                "category":          CATEGORY_MAP_LOCAL.get(event_type, "other"),
                "display_label":     EVENT_DISPLAY_LABELS.get(event_type, event_type),
                "description":       EVENT_DESCRIPTION.get(event_type, ""),
                "window": {
                    "start":          win_start,
                    "end":            win_end,
                    "precision":      w.get("precision", "AD"),
                    "human_readable": _human_window(win_start, win_end) if win_start and win_end else "",
                },
                "dasha":             _dasha_label(w),
                "confidence":        confidence,
                "confidence_label":  _confidence_label(confidence),
                "energy_explanation": build_energy_explanation(_energy_pred, event_type, lagna),
                "framing":           "opening",
                "months_away":       _months_until(win_start),
            })

        # Sort: highest confidence first, then soonest
        future_predictions.sort(key=lambda x: (-x["confidence"], x["window"]["start"]))
        themes = future_predictions[:max_predictions]

        # === TRANSIT CONFIRMATION — boost confidence when transit aligns with dasha ===
        try:
            from antar_engine.transit_engine import get_full_transit_report
            for _th in themes:
                _ws = _th.get("window", {}).get("start", "")
                if not _ws:
                    continue
                try:
                    _wd = datetime.fromisoformat(_ws)
                    _future_transit = get_full_transit_report(cd, date=_wd)
                    _confirming = [mt for mt in _future_transit.get("major_transits", [])
                                   if mt.get("severity") in ("high", "positive")]
                    if _confirming:
                        _th["transit_confirmation"] = True
                        _th["transit_details"] = _confirming[0]["description"]
                        _th["confidence"] = min(10, _th.get("confidence", 5) + 1)
                        _th["confidence_label"] = (
                            "high" if _th["confidence"] >= 8
                            else "moderate" if _th["confidence"] >= 5
                            else "low"
                        )
                    else:
                        _th["transit_confirmation"] = False
                except Exception:
                    _th["transit_confirmation"] = None
        except Exception as _tce:
            print(f"[upcoming-themes] Transit confirmation failed (non-fatal): {_tce}")
        # === END TRANSIT CONFIRMATION ===

        # === D9/D10 CONFIDENCE ADJUSTMENT ===
        try:
            from antar_engine.divisional_context import extract_d9_context, extract_d10_context
            _d9_up = extract_d9_context(cd)
            _d10_up = extract_d10_context(cd)

            for _th in themes:
                _evt = _th.get("event_type", "")

                # Relationship events: D9 Venus strength adjusts confidence
                if _d9_up and _evt in ("serious_partnership_began", "serious_partnership_ended"):
                    _rs = _d9_up.get("relationship_strength", "moderate")
                    if _rs == "strong":
                        _th["confidence"] = min(10, _th.get("confidence", 5) + 1)
                        _th["d9_signal"] = "D9 Venus strong — relationship energy confirmed"
                    elif _rs == "difficult":
                        _th["confidence"] = max(1, _th.get("confidence", 5) - 1)
                        _th["d9_signal"] = "D9 Venus challenged — timing may shift"

                # Career events: D10 Sun/10th house adjusts confidence
                if _d10_up and _evt in ("career_pivot", "major_acquisition"):
                    _cs = _d10_up.get("career_strength", "moderate")
                    if _cs == "strong":
                        _th["confidence"] = min(10, _th.get("confidence", 5) + 1)
                        _th["d10_signal"] = "D10 career chart strong — professional shift confirmed"
                    elif _cs == "needs_effort":
                        _th["confidence"] = max(1, _th.get("confidence", 5) - 1)
                        _th["d10_signal"] = "D10 career chart needs effort — transition requires extra push"

                # Recalculate label after adjustment
                _c = _th.get("confidence", 5)
                _th["confidence_label"] = "high" if _c >= 8 else "moderate" if _c >= 5 else "low"
        except Exception as _dce:
            print(f"[upcoming-themes] D9/D10 confidence adjustment failed (non-fatal): {_dce}")
        # === END D9/D10 CONFIDENCE ADJUSTMENT ===

        stable = None
        if len(themes) < 2:
            stable = (
                f"Your current energies are strong and steady. The next "
                f"{months_ahead} months favor deepening what's already in motion "
                f"rather than starting entirely new chapters. Use this stability "
                f"to build — real progress compounds in windows like this."
            )

        # ── LLM Narration (Claude) ────────────────────────────────────────
        llm_card = None
        if themes and _CLAUDE_AVAILABLE:
            # Fetch Rahu MD sub-periods if any theme involves Rahu
            rahu_md_ads = []
            for t in themes:
                if "Rahu" in (t.get("dasha") or ""):
                    try:
                        rahu_ads = supabase.table("dasha_periods").select(
                            "planet_or_sign, start_date, end_date"
                        ).eq("chart_id", chart_id).eq("system", "vimsottari").eq(
                            "level", 2
                        ).gte("start_date", "2026-01-01").order("start_date").execute()
                        rahu_md_ads = rahu_ads.data or []
                    except Exception:
                        pass
                    break

            # Build future_windows list from scored themes
            _fw = [{
                "event_type":   t["event_type"],
                "window_start": t["window"]["start"],
                "window_end":   t["window"]["end"],
                "planet": (t.get("dasha") or "").split(" + ")[1].replace(" AD", "").replace(" PD", "").strip() if " + " in (t.get("dasha") or "") else "",
                "parent_md": (t.get("dasha") or "").split(" MD")[0].strip() if " MD" in (t.get("dasha") or "") else "",
                "score": t.get("confidence", 5),
            } for t in themes]

            try:
                llm_narration = await _get_or_generate_upcoming_themes_llm(
                    chart_id=chart_id,
                    chart_data=cd,
                    profile=chart_res.data,
                    future_windows=_fw,
                    rahu_md_ads=rahu_md_ads,
                    refresh=refresh,
                    voice_mode=voice_mode,
                )
                if llm_narration and isinstance(llm_narration, dict):
                    llm_card = {
                        "headline":     llm_narration.get("headline", ""),
                        "body":         llm_narration.get("body", ""),
                        "caution":      llm_narration.get("caution", ""),
                        "your_move":    llm_narration.get("your_move", ""),
                        "energy_tags":  llm_narration.get("energy_tags", []),
                        "center_link":  llm_narration.get("center_link", ""),
                        "voice_mode":   voice_mode,
                    }
            except Exception as llm_err:
                print(f"[upcoming-themes-llm] Non-fatal error: {llm_err}")

        return {
            "chart_id":       chart_id,
            "lagna":          lagna,
            "first_name":     first_name,
            "themes":         themes,
            "themes_shown":   len(themes),
            "stable_message": stable,
            "llm_narration":  llm_card,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[upcoming-themes] Error for {chart_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compute upcoming themes: {str(e)}")

@app.post("/api/v1/chart/{chart_id}/past-events/feedback")
async def submit_past_event_feedback(
    chart_id: str,
    feedback: dict,
    authorization: Optional[str] = Header(None),
):
    """
    Store user confirmation/correction of a past-event prediction.
    Payload: {"event_type": "...", "response": "yes|close|no", "actual_date": "YYYY-MM-DD" (optional)}

    Used to validate mapper accuracy and improve confidence calibration.
    Gracefully no-ops if the past_event_feedback table doesn't exist yet.
    """
    try:
        event_type  = feedback.get("event_type")
        response    = feedback.get("response")
        actual_date = feedback.get("actual_date")

        if response not in ("yes", "close", "no"):
            raise HTTPException(status_code=400, detail="response must be: yes, close, or no")

        try:
            supabase.table("past_event_feedback").insert({
                "chart_id":     chart_id,
                "event_type":   event_type,
                "response":     response,
                "actual_date":  actual_date,
                "submitted_at": datetime.now().isoformat(),
            }).execute()
        except Exception as db_err:
            # Table may not exist yet — log but don't block UX
            print(f"[past-events-feedback] DB insert skipped ({db_err})")

        return {"status": "recorded"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[past-events-feedback] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/chart/{chart_id}", response_model=ChartResponse)
async def get_chart(chart_id: str):
    result = supabase.table("charts").select("*").eq("id", chart_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Chart not found")
    r = result.data[0]
    response = ChartResponse(
        id=r["id"],
        birth_date=r["birth_date"],
        birth_time=r["birth_time"],
        lagna=r["chart_data"]["lagna"],
        planets=r["chart_data"]["planets"]
    )
    response_dict = response.dict()
    response_dict["lal_kitab"]        = r.get("lal_kitab_data")
    response_dict["panchanga"]        = r["chart_data"].get("panchanga")
    response_dict["sarvashtakavarga"] = r["chart_data"].get("sarvashtakavarga")
    return response_dict

# ── Predict ───────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════
# SPRINT E2: CONTRADICTION RESOLUTION
# ═══════════════════════════════════════════════════════════════

def _domains_overlap(predict_domain: str, prashna_domain: str) -> bool:
    """E2: Check if two domain strings refer to the same life area."""
    if not predict_domain or not prashna_domain:
        return False
    pd = predict_domain.lower().strip()
    pr = prashna_domain.lower().strip()
    if pd == pr:
        return True
    DOMAIN_GROUPS = {
        "career": {"career", "job", "promotion", "business", "promoted", "raise",
                   "interview", "hired", "fired", "resign", "boss", "work"},
        "finance": {"finance", "money", "investment", "wealth", "funding", "fund",
                    "loan", "equity", "investor", "series", "profit", "loss",
                    "stock", "crypto", "deal", "buy", "sell"},
        "relationship": {"relationship", "marriage", "love", "partner", "divorce",
                         "dating", "girlfriend", "boyfriend", "wife", "husband",
                         "engaged", "marry"},
        "legal": {"legal", "court", "lawsuit", "case", "judge", "litigation"},
        "health": {"health", "surgery", "illness", "sick", "doctor", "hospital",
                   "medicine", "recover", "disease"},
        "children": {"children", "child", "pregnant", "conceive", "kid", "son",
                     "daughter", "baby", "fertility"},
        "travel": {"travel", "foreign", "relocation", "immigration", "migrate",
                   "passport", "visa", "abroad", "relocate"},
        "education": {"education", "degree", "admission", "university", "school",
                      "exam", "test", "study"},
    }
    for group_name, keywords in DOMAIN_GROUPS.items():
        if pd in keywords and pr in keywords:
            return True
    return False


def get_recent_prashna_for_domain(chart_id: str, domain: str, hours: int = 72):
    """E2: Check if user asked the Oracle about this domain in the last N hours."""
    try:
        _cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        _result = supabase.table("prashna_log") \
            .select("verdict, score, timing, domain, question, created_at") \
            .eq("chart_id", chart_id) \
            .gte("created_at", _cutoff) \
            .order("created_at", desc=True) \
            .limit(5) \
            .execute()
        if not _result.data:
            return None
        for _row in _result.data:
            _pr_domain = _row.get("domain", "")
            if _domains_overlap(domain, _pr_domain):
                _hours_ago = (
                    datetime.now(timezone.utc) -
                    datetime.fromisoformat(_row["created_at"].replace("Z", "+00:00"))
                ).total_seconds() / 3600
                return {
                    "verdict": _row.get("verdict", ""),
                    "score": _row.get("score", 0),
                    "timing": _row.get("timing", ""),
                    "domain": _pr_domain,
                    "question": _row.get("question", ""),
                    "hours_ago": round(_hours_ago, 1),
                }
        return None
    except Exception as _e2_err:
        print(f"[E2] get_recent_prashna_for_domain failed: {_e2_err}")
        return None


def build_contradiction_context(recent_prashna: dict) -> str:
    """E2: Build prompt block telling Claude about a recent Oracle reading on the same domain."""
    return f"""
\u2550\u2550\u2550 RECENT ORACLE READING (same domain) \u2550\u2550\u2550
The user asked the Horary Oracle about this topic {recent_prashna['hours_ago']} hours ago.
Oracle verdict: {recent_prashna['verdict']} ({recent_prashna['score']}%)
Oracle timing: {recent_prashna['timing']}
Oracle domain: {recent_prashna['domain']}
Oracle question: \"{recent_prashna['question']}\"

IF your birth chart analysis contradicts the Oracle verdict:
- Explain that the birth chart shows STRUCTURAL timing (long-term patterns, dasha periods, slow transits)
- The Oracle shows TACTICAL momentum (the energy at the exact moment they asked)
- When they disagree, the timing is usually the real signal
- Birth chart = when the foundation is ready. Oracle = when the door opens.
- THE MOVE should account for both: prepare now (Oracle), don't overcommit yet (birth chart)
- Frame it as: \"Two lenses, same question — here's what each one sees.\"

IF your birth chart analysis AGREES with the Oracle verdict:
- Note the convergence: \"Both your birth chart and the Oracle point the same direction.\"
- This increases confidence. Say so.

DO NOT ignore the Oracle reading. DO NOT pretend it doesn't exist.
Acknowledge it explicitly and explain the difference.
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
"""




# ── Helper: convert sign name to 0-indexed int ──
_SIGNS_LIST = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
def _sign_name_to_idx(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val in _SIGNS_LIST:
        return _SIGNS_LIST.index(val)
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0

# ── Self-healing: recompute missing Jaimini on predict ──────────
async def _ensure_chart_complete(chart_id: str, chart_data: dict,
                                  chart_record: dict, supabase_client) -> dict:
    """
    Check for missing Jaimini layer and recompute silently.
    Returns updated chart_record with jaimini_data populated.
    """
    jaimini_data = chart_record.get("jaimini_data")
    if isinstance(jaimini_data, str):
        import json as _ecjson
        try:
            jaimini_data = _ecjson.loads(jaimini_data)
        except Exception:
            jaimini_data = None
    # Check if Jaimini is truly present (not empty dict)
    if jaimini_data and (jaimini_data.get("chara_karakas") or jaimini_data.get("karakas")):
        return chart_record  # already complete
    try:
        from antar_engine.jaimini_engine import (
            calculate_jaimini_analysis, jaimini_to_db_json
        )
        import json as _ecj2
        _cd = chart_data if isinstance(chart_data, dict) else (_ecj2.loads(chart_data) if isinstance(chart_data, str) else {})
        birth_date = str(chart_record.get("birth_date", _cd.get("birth_date", "")))[:10]
        _lagna_obj = _cd.get("lagna", {})
        _lagna_sign = _sign_name_to_idx(_lagna_obj.get("sign_num", _lagna_obj.get("sign_index", _lagna_obj.get("sign", 0)))) if isinstance(_lagna_obj, dict) else 0
        _planets = _cd.get("planets", {})
        _d9_data = (_cd.get("divisional_charts", {}).get("d9") or _cd.get("divisional_charts", {}).get("D9") or {}).get("planets", {})
        if not _d9_data:
            _d9_data = _cd.get("d9_planets", {})
        if birth_date and _planets:
            _result = calculate_jaimini_analysis(
                lagna_sign=_lagna_sign,
                planets_dict=_planets,
                d9_planets_dict=_d9_data or {},
                birth_date_str=birth_date,
            )
            _db = _result["db_json"]
            _db.pop("computed_at", None)
            supabase_client.table("charts").update({
                "jaimini_data": _db
            }).eq("id", chart_id).execute()
            chart_record["jaimini_data"] = _db
            print(f"[predict] Recomputed Jaimini for {chart_id}")
    except Exception as e:
        print(f"[predict] Jaimini recompute failed (non-blocking): {e}")
    return chart_record


@app.post("/api/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest, authorization: Optional[str] = Header(None)):
    user_id = None
    if authorization:
        try:
            user_id = verify_token(authorization)
        except HTTPException:
            pass

    if not request.chart_id:
        raise HTTPException(status_code=400, detail="chart_id required")

    # Persistent rate limiting — DB-backed, survives redeploys
    if request.chart_id:
        from antar_engine.subscription_engine import increment_usage
        # LIMITS DISABLED — free launch (re-enable post-PMF)
        # increment_usage(request.chart_id, "pred", supabase)

    # Guest rate limiting DISABLED — free launch
    if False:  # LIMIT DISABLED — was: if not user_id:
        if not check_guest_rate_limit(request.chart_id, limit=3):
            usage = get_guest_usage(request.chart_id)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "monthly_limit_reached",
                    "message": f"You have used your {usage['limit']} free readings this month.",
                    "used": usage["count"],
                    "limit": usage["limit"],
                    "resets": usage["month"],
                    "upgrade_url": "https://antar.world/upgrade",
                    "plans": [
                        {
                            "name": "Seeker",
                            "price_monthly": "$4.99",
                            "price_annual": "$39",
                            "features": [
                                "Unlimited predictions",
                                "Career & wealth reading",
                                "Mantra audio playback",
                                "Full prediction history",
                                "Monthly life briefing",
                            ]
                        },
                        {
                            "name": "Navigator",
                            "price_monthly": "$19.99",
                            "features": [
                                "Everything in Seeker",
                                "1 live reading/month",
                                "Astrocartography",
                                "Priority responses",
                            ]
                        }
                    ]
                }
            )

    # Log action
    try:
        supabase.table("user_actions").insert({
            "user_id": user_id,
            "action_type": "prediction_request",
            "action_data": {"question": request.question, "chart_id": request.chart_id},
            "timestamp": "now()"
        }).execute()
    except Exception as e:
        print(f"Action log error: {e}")

    # Fetch chart
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_record = chart_res.data[0]
    chart_data = chart_record["chart_data"]

    # --- DEBUG: chart data diagnostic ---
    import json as _dbg_json
    def _dbg_safe(v):
        if isinstance(v, str):
            try: return _dbg_json.loads(v)
            except: return {}
        return v if isinstance(v, dict) else {}
    _cd = _dbg_safe(chart_data)
    print(f"[predict debug] chart_data keys: {list(_cd.keys())[:20]}")
    print(f"[predict debug] jaimini_data: {bool(chart_record.get('jaimini_data'))}")
    print(f"[predict debug] lal_kitab_data: {bool(chart_record.get('lal_kitab_data'))}")
    print(f"[predict debug] d9: {bool(_cd.get('divisional_charts', {}).get('d9') or _cd.get('divisional_charts', {}).get('D9'))}")
    # --- END DEBUG ---

    # Self-heal missing layers (Jaimini)
    chart_record = await _ensure_chart_complete(
        request.chart_id, chart_data, chart_record, supabase
    )

    # Dashas
    dashas_response = get_dashas_for_chart(request.chart_id)

    # ================================================================
    # LOCATION QUESTION ROUTING → DeepSeek + Astrocartography engine
    # ================================================================
    # Detect location intent and route to DeepSeek for accuracy.
    # DeepSeek demonstrated better context-awareness for location questions
    # (stay-vs-move logic, LATAM focus, current city awareness).
    # ================================================================
    _LOCATION_KEYWORDS = [
        "city", "ciudad", "cities", "ciudades",
        "country", "pais", "location", "ubicacion", "ubicación",
        "move", "mover", "relocate", "mudarse",
        "where should i", "dónde debo", "donde debo",
        "best place", "mejor lugar", "mejor ciudad",
        "which city", "qué ciudad", "que ciudad",
        "startup growth", "wealth location", "billionaire",
        "latam", "latin america", "europe", "asia",
        "astrocartography", "astrocartografía", "planetary lines",
        "live", "vivir", "settle", "establecer",
        "bogota", "houston", "london", "mexico",
    ]

    _q_lower_loc = request.question.lower()
    _is_location_q = any(kw in _q_lower_loc for kw in _LOCATION_KEYWORDS)

    if _is_location_q and chart_record.get("astrocartography_data"):
        try:
            print(f"[predict] Location question detected — routing to DeepSeek astrocartography")

            from antar_engine.chart_context_builder_json import _fetch_dashas
            from antar_engine.astrocartography_recommender import recommend_cities
            import json as _loc_json, httpx as _loc_httpx, os as _loc_os

            _loc_dashas = _fetch_dashas(request.chart_id, supabase)

            # Detect intent from question
            _loc_intent = "general"
            _q_l = request.question.lower()
            if any(w in _q_l for w in ["startup", "empresa", "negocio", "business", "tech", "ai", "msme"]):
                _loc_intent = "startup"
            elif any(w in _q_l for w in ["billionaire", "billonario", "billion", "mil millones"]):
                _loc_intent = "billionaire"
            elif any(w in _q_l for w in ["wealth", "riqueza", "rich", "rico", "money", "dinero", "fortune"]):
                _loc_intent = "wealth"
            elif any(w in _q_l for w in ["career", "carrera", "job", "trabajo", "profession"]):
                _loc_intent = "career"
            elif any(w in _q_l for w in ["relationship", "relacion", "partner", "love", "amor", "marriage"]):
                _loc_intent = "relationships"

            # Detect region from question
            _loc_region = "global"
            if any(w in _q_l for w in ["latam", "latin", "colombia", "mexico", "brazil", "argentina", "chile", "peru"]):
                _loc_region = "latam"
            elif any(w in _q_l for w in ["europe", "europa", "london", "paris", "berlin", "madrid"]):
                _loc_region = "europe"
            elif any(w in _q_l for w in ["asia", "india", "singapore", "japan", "china", "dubai"]):
                _loc_region = "asia"
            elif any(w in _q_l for w in ["usa", "us", "united states", "houston", "austin", "new york"]):
                _loc_region = "north_america"

            # Extract natal yogas
            _loc_chart_data = chart_record.get("chart_data") or {}
            _loc_yogas = _loc_chart_data.get("yogas") or []
            if not _loc_yogas:
                _loc_planets = _loc_chart_data.get("planets", {})
                if (_loc_planets.get("Jupiter") or {}).get("house") == 2 and                    (_loc_planets.get("Venus") or {}).get("house") == 11:
                    _loc_yogas = [{"name": "Dhana Yoga", "planets": ["Jupiter", "Venus"]}]

            # Python ranking
            _loc_ranking = recommend_cities(
                chart_record=chart_record,
                dashas=_loc_dashas,
                natal_yogas=_loc_yogas,
                intent=_loc_intent,
                region=_loc_region,
                language=language,
                top_n=5,
            )

            # DeepSeek narrative
            _loc_dc = _loc_ranking.get("dasha_context", {})
            _loc_archetype = (chart_record.get("character_archetype") or {}).get("name", "")
            _loc_current_city = chart_record.get("current_city") or ""
            _loc_current_country = chart_record.get("current_country") or ""

            _loc_city_list = []
            for i, c in enumerate(_loc_ranking.get("top_cities", [])[:5]):
                _loc_city_list.append({
                    "rank":        i + 1,
                    "city":        c["city"],
                    "score":       c["score"],
                    "is_current":  c.get("is_current_location", False),
                    "dasha_notes": c.get("dasha_notes", []),
                    "yoga_notes":  c.get("yoga_notes", []),
                    "top_lines":   [{
                        "planet": l["planet"], "line": l["line"], "strength": l["strength"]
                    } for l in c.get("line_details", [])[:3]],
                })

            _loc_prompt = f"""You are Antar's astrocartography interpreter.
You receive deterministic scores from the Python engine. Do NOT calculate anything.

USER QUESTION: {request.question}

USER CONTEXT:
- Current location: {_loc_current_city or _loc_current_country or "unknown"}
- Intent detected: {_loc_intent}
- Region: {_loc_region}
- Archetype: {_loc_archetype}
- Dashas: Current MD {_loc_dc.get("current_md")} until {str(_loc_dc.get("current_md_end",""))[:10]} | Next MD {_loc_dc.get("next_md")} from {str(_loc_dc.get("next_md_start",""))[:10]} (18-year window)

PYTHON RANKING:
{_loc_json.dumps(_loc_city_list, indent=2)}

STAY-VS-MOVE: {_loc_ranking.get("stay_vs_move", "unknown")}
MISSING LINES: {", ".join(_loc_ranking.get("missing_lines", [])) or "none"}

Your job:
1. Answer the user's specific question directly in the first sentence
2. If stay_vs_move is "stay": explain why current location works
3. If "move": recommend the top city with exact timing
4. Mention missing lines honestly if relevant
5. End with YOUR MOVE — one specific action this week
6. Do NOT use planet names — use energy language
   (e.g., "expansion energy" not "Jupiter", "disruption channel" not "Rahu")

{"Respond entirely in Spanish." if language == "es" else "Respond in English."}

Keep response under 200 words. Be warm, specific, actionable."""

            _loc_ds_key = _loc_os.environ.get("DEEPSEEK_API_KEY", "")
            if not _loc_ds_key:
                raise ValueError("DEEPSEEK_API_KEY not set — falling back to Claude")

            _loc_resp = _loc_httpx.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {_loc_ds_key}"},
                json={
                    "model":       "deepseek-chat",
                    "messages":    [{"role": "user", "content": _loc_prompt}],
                    "temperature": 0.2,
                    "max_tokens":  400,
                },
                timeout=25.0,
            )
            _loc_answer = _loc_resp.json()["choices"][0]["message"]["content"].strip()
            print(f"[predict] Location answer from DeepSeek — {len(_loc_answer)} chars")

            # Save to chat_messages
            try:
                supabase.table("chat_messages").insert({
                    "chart_id":     request.chart_id,
                    "question":     request.question,
                    "plain_summary": _loc_answer,
                    "signal_line":  f"Location: {_loc_ranking.get('top_cities', [{}])[0].get('city', '')}",
                    "action_item":  "",
                    "domain":       "location",
                    "language":     language,
                }).execute()
            except Exception:
                pass

            return {
                "prediction":    _loc_answer,
                "plain_summary": _loc_answer,
                "confidence":    0.80,
                "factors":       [c["city"] for c in _loc_ranking.get("top_cities", [])[:3]],
                "signal_line":   f"Top location: {_loc_ranking.get('top_cities', [{}])[0].get('city', '')}",
                "action_item":   "",
                "timing_window": f"Next MD: {_loc_dc.get('next_md')} from {str(_loc_dc.get('next_md_start',''))[:10]}",
                "why_this":      f"Astrocartography + dasha alignment. Stay/move: {_loc_ranking.get('stay_vs_move')}",
                "model_used":    "deepseek-astrocartography",
                "rarity_signals": [],
                "precision_windows": [],
                "all_domains":   [],
            }

        except Exception as _loc_e:
            import traceback
            print(f"[predict] Location routing failed — falling back to Claude: {_loc_e}")
            print(f"[predict] {traceback.format_exc()[:300]}")
            # Fall through to normal Claude path
    # ================================================================
    # END LOCATION ROUTING
    # ================================================================


    # Life events
    life_events = []
    if user_id:
        ev = supabase.table("life_events").select("event_date, event_type, description") \
            .eq("user_id", user_id).order("event_date", desc=True).limit(20).execute()
        life_events = ev.data

    # Locale detection
    locale = get_locale_from_request(
        country_code=chart_record.get("country_code"),
        birth_country=chart_record.get("country_code"),
        user_language_preference=chart_record.get("language_preference"),
    )
    language = locale.language

    # Profile
    profile_text = psychological_profile(chart_data)

    # Transits
    _raw_transits = transits.calculate_transits(chart_data, target_date=None, ayanamsa_mode=1)
    # calculate_transits() returns a list; normalise to dict keyed by planet name
    current_transits = (
        {t["planet"]: t for t in _raw_transits if "planet" in t}
        if isinstance(_raw_transits, list) else _raw_transits
    )
    transit_summary = transits.summarize_transits(_raw_transits)

    # Country context — static cultural layer (always available)
    # C2: Use current residence country for DKP, not birth country
    country_code = chart_record.get("current_country") or chart_record.get("country_code")
    country_context = get_country_context(country_code) if country_code else ""

    # Timing
    timing_text = timing_engine.timing_insights(chart_data, dashas_response)

    # ── Connection context — inject if question mentions a known person ──────
    _connection_context = ""
    try:
        _conn_res = supabase.table("chart_connections").select("*") \
            .eq("chart_id_a", request.chart_id) \
            .order("updated_at", desc=True) \
            .execute()

        _connections = _conn_res.data or []
        _question_lower = (request.question or "").lower()

        # Find matching connection by name mention in question
        _matched_conn = None
        for _conn in _connections:
            _other_name = (_conn.get("name_b") or "").lower()
            if _other_name and _other_name in _question_lower:
                _matched_conn = _conn
                break

        # If no name match, use most recent connection if question implies relationship
        RELATION_KEYWORDS = [
            "partner", "cofounder", "co-founder", "colleague", "friend",
            "investor", "hire", "team", "relationship", "together",
            "they", "he", "she", "them", "their", "our", "we",
        ]
        if not _matched_conn and _connections:
            if any(kw in _question_lower for kw in RELATION_KEYWORDS):
                _matched_conn = _connections[0]

        if _matched_conn:
            _other_name   = _matched_conn.get("name_b", "this person")
            _compat_type  = _matched_conn.get("compat_type", "")
            _score        = _matched_conn.get("overall_score", 0)
            _pairing      = _matched_conn.get("pairing_name", "")
            _verdict      = _matched_conn.get("verdict", "")
            _summary      = _matched_conn.get("analysis_summary", "")[:400]
            _fm           = _matched_conn.get("field_mode_layer", {}) or {}
            _sb           = _matched_conn.get("score_breakdown", {}) or {}

            _connection_context = f"""
ACTIVE CONNECTION CONTEXT — {_other_name.upper()} ({_compat_type.upper()}):
Compatibility score: {_score}/100
Pairing archetype: {_pairing} — {_verdict}
Field dynamic: {_fm.get('field_label','')} ({_fm.get('field_dynamic','')})
Mode dynamic: {_fm.get('mode_label','')} ({_fm.get('mode_dynamic','')})
Dasha alignment: {_sb.get('dasha_label','')} — {_sb.get('dasha_window','')}
Analysis summary: {_summary}

When answering questions about {_other_name}, use this compatibility context.
Translate all astrological factors into plain energy language — no planet names, no house numbers.
Answer specifically about {_other_name}'s strengths/weaknesses for the question asked.
"""
            print(f"[predict] Connection context injected — {_other_name} ({_compat_type})")

    except Exception as _ce:
        print(f"[predict] Connection context non-fatal: {_ce}")

    # ── C2: Desh Kal Patra — real-world economic context ──────────
    dkp_context  = ""
    nation_insight = ""
    if country_code:
        try:
            from antar_engine.country_context import COUNTRY_CONTEXT
            _country_name = COUNTRY_CONTEXT.get(country_code, {}).get("name", country_code)
            dkp_context = await get_dkp_context(
                country_code=country_code,
                country_name=_country_name,
                supabase=supabase,
                deepseek_client=deepseek_client,
            )
            print(f"[predict] DKP loaded for {country_code} ({len(dkp_context)} chars)")
        except Exception as e:
            print(f"[predict] DKP failed (non-fatal): {e}")

        # Nation astrological insight — DISABLED (nation chart dasha broken, DKP covers this)
        # Restore when nation chart computation is fixed
        # try:
        #     nation_insight = nation_engine.get_nation_insight(
        #         country_code, supabase, deepseek_client, language
        #     )
        # except Exception as e:
        #     print(f"[predict] Nation insight error (non-fatal): {type(e).__name__}: {e}")
    # ── end C2 ───────────────────────────────────────────────────

    # ── Concern detection (must come before C3 and C4) ────────
    concern = _detect_concern(request.question)

    # ── PATRA (must come before C4) ──────────────────────────────
    user_profile = {
        "marital_status":   chart_record.get("marital_status", "unknown"),
        "children_status":  chart_record.get("children_status", "no_children_unsure"),
        "career_stage":     chart_record.get("career_stage", "mid_career"),
        "health_status":    chart_record.get("health_status", "excellent"),
        "financial_status": chart_record.get("financial_status", "stable"),
        "birth_country":    chart_record.get("country_code", ""),
        "current_country":  chart_record.get("current_country") or chart_record.get("country_code", ""),
        "countries_lived":  chart_record.get("countries_lived", []),
    }
    patra = build_patra_context(
        birth_date=chart_record["birth_date"],
        user_profile=user_profile,
        primary_concern=concern,
    )
    patra_context = patra_to_context_block(patra)

    # ── C3: Pattern Memory — Layer 7 ─────────────────────────────
    _memory = {}
    try:
        _memory = build_pattern_memory(
            chart_id=request.chart_id,
            current_concern=concern,
            current_question=request.question,
            supabase=supabase,
        )
        if _memory.get("diagnostic_mode"):
            print(f"[predict] C3 DIAGNOSTIC MODE — unresolved {concern} case detected")
        elif _memory.get("memory_block"):
            print(f"[predict] C3 memory loaded — {len(_memory['past_predictions'])} past predictions")
    except Exception as _mem_err:
        print(f"[predict] C3 pattern memory failed (non-fatal): {_mem_err}")
        _memory = {}
    # ── end C3 ───────────────────────────────────────────────────

    # ── C4: Common Sense Layer ───────────────────────────────────
    _cs_block = ""
    try:
        _cs_block = build_common_sense_block(
            age=getattr(patra, "age", None),
            life_stage=getattr(patra, "life_stage_name", None),
            concern=concern,
            country_code=country_code,
            marital_status=user_profile.get("marital_status"),
            children_status=user_profile.get("children_status"),
            dkp_context=dkp_context,
            memory_result=_memory,
            birth_country=chart_record.get("country_code"),
            current_country=chart_record.get("current_country"),
        )
        if _cs_block:
            print(f"[predict] C4 common sense — {len(_cs_block)} chars")

    except Exception as _cs_err:
        print(f"[predict] C4 common sense failed (non-fatal): {_cs_err}")
        _cs_block = ""
    # ── end C4 ───────────────────────────────────────────────────

    # ── E2: Contradiction Resolution ─────────────────────────────
    _contradiction_detected = False
    _oracle_context = None
    try:
        _recent_prashna = get_recent_prashna_for_domain(request.chart_id, concern, hours=72)
        if _recent_prashna:
            _contradiction_block = build_contradiction_context(_recent_prashna)
            # Will be prepended to prompt later via extra blocks
            _contradiction_detected = True
            _oracle_context = {
                "verdict": _recent_prashna["verdict"],
                "score": _recent_prashna["score"],
                "timing": _recent_prashna["timing"],
                "domain": _recent_prashna["domain"],
                "hours_ago": _recent_prashna["hours_ago"],
            }
            print(f"[E2] Contradiction context injected domain={concern} "
                  f"oracle={_recent_prashna['verdict']} hours_ago={_recent_prashna['hours_ago']}")
        else:
            _contradiction_block = ""
    except Exception as _e2_wire_err:
        print(f"[E2] Contradiction check failed (non-fatal): {_e2_wire_err}")
        _contradiction_block = ""
    # ── end E2 ───────────────────────────────────────────────────

    # Initialize dkp_block if not yet defined (defined later in DKP section ~line 1880)
    dkp_block = dkp_block if "dkp_block" in locals() else ""
    # Sprint D: domain-focused DKP note
    try:
        from antar_engine.desh_kal_patra import get_domain_dkp_note
        _domain_dkp = get_domain_dkp_note(concern, dkp_context, country_code or "")
        if _domain_dkp:
            dkp_block = (dkp_block or "") + f"\n\n{_domain_dkp}"
    except Exception as _ddkp_err:
        print(f"[predict] domain DKP note failed (non-fatal): {_ddkp_err}")

    # --- DIAGNOSTIC PRE-SCAN (Sprint 1.2) ---
    diagnostic_block = ""
    try:
        if chart_data and isinstance(chart_data, dict):
            diagnostic_block = build_diagnostic_prompt_block(
                chart_data,
                request.question if hasattr(request, 'question') else "",
                concern if 'concern' in dir() else None
            )
            if diagnostic_block:
                # Will be injected into prompt via extra context
                pass
    except Exception as e:
        import logging as _diag_log
        _diag_log.getLogger("antar").warning(f"Diagnostic pre-scan failed: {e}")
        diagnostic_block = ""
    # --- END DIAGNOSTIC PRE-SCAN ---

    # --- SYSTEM STATE INJECTION (Sprint Apr7 Step 2) ---
    system_state_block = ""
    try:
        import logging as _ss_log
        _ssl = _ss_log.getLogger("antar.system_state")

        # Pull instrument scores from executive_dashboard if available
        instr = {}
        try:
            from antar_engine.executive_dashboard import get_instrument_scores
            instr = get_instrument_scores(chart_data) if chart_data else {}
        except Exception as _ie:
            _ssl.debug(f"Instrument scores unavailable: {_ie}")

        # Pull LK sleeping/rin state
        lk_state = {}
        try:
            from antar_engine.lal_kitab_advanced import get_lk_state
            lk_state = get_lk_state(chart_data) if chart_data else {}
        except Exception as _lke:
            _ssl.debug(f"LK state unavailable: {_lke}")

        lines = ["\nCURRENT SYSTEM STATE:"]

        # Top 6 instrument gauges by score
        if instr:
            sorted_instr = sorted(instr.items(), key=lambda x: x[1].get("score", 0), reverse=True)
            for name, val in sorted_instr[:6]:
                _score  = val.get("score", 0)
                _status = val.get("status", "")
                _lock   = val.get("lock_level", "")
                _lock_str = f" — {_lock}" if _lock else ""
                lines.append(f"  {name}: {_status} ({_score}/100){_lock_str}")

        # Lal Kitab sleeping planets and active Rin debts
        sleeping = lk_state.get("sleeping_planets", []) if lk_state else []
        rins     = lk_state.get("active_rins", []) if lk_state else []
        if sleeping or rins:
            lines.append("KARMIC STATE (Lal Kitab):")
            for sp in sleeping[:3]:
                _planet    = sp.get("planet", sp) if isinstance(sp, dict) else sp
                _reason    = sp.get("reason", "") if isinstance(sp, dict) else ""
                _reason_str = f" — {_reason}" if _reason else ""
                lines.append(f"  Sleeping {_planet}{_reason_str}")
            for rin in rins[:2]:
                _rin_type  = rin.get("type", rin) if isinstance(rin, dict) else rin
                _effect    = rin.get("effect", "") if isinstance(rin, dict) else ""
                _effect_str = f" — affects {_effect}" if _effect else ""
                lines.append(f"  Active Rin: {_rin_type}{_effect_str}")

        if len(lines) > 1:
            system_state_block = "\n".join(lines) + "\n"
            _ssl.info("System state block ready for injection")
    except Exception as _sse:
        import logging as _fb_log
        _fb_log.getLogger("antar").warning(f"System state injection failed (non-critical): {_sse}")
        system_state_block = ""
    # --- END SYSTEM STATE INJECTION ---

    # --- DKP CONTEXT BLOCKS (Sprint Apr7 Step 3) ---
    dkp_block = ""
    try:
        # Pull user_profile from the request if present
        _up = {}
        if hasattr(request, "user_profile") and request.user_profile:
            _up = request.user_profile if isinstance(request.user_profile, dict) else {}
        # Also accept flat fields on the request body
        for _f in ("country", "city", "language", "profession", "role",
                   "ventures", "current_focus", "birth_date"):
            val = getattr(request, _f, None)
            if val and _f not in _up:
                _up[_f] = val

        dkp_block = build_dkp_block(chart_data, _up)
        if dkp_block:
            import logging as _dkp_log
            _dkp_log.getLogger("antar").info("DKP context block ready for injection")
    except Exception as _dkpe:
        import logging as _dkp_log2
        _dkp_log2.getLogger("antar").warning(f"DKP context injection failed (non-critical): {_dkpe}")
        dkp_block = ""
    # --- END DKP CONTEXT BLOCKS ---
    # --- DIVISIONAL CHARTS INJECTION (Sprint Apr7 Step 4) ---
    divisional_block = ""
    try:
        if chart_data and isinstance(chart_data, dict) and chart_data.get("planets"):
            divisional_block = build_divisional_block(chart_data)
            if divisional_block:
                import logging as _div_log
                _div_log.getLogger("antar").info("Divisional charts block computed and ready")
    except Exception as _dive:
        logger.warning(f"Divisional block computation failed (non-critical): {_dive}")
        divisional_block = ""
    # --- END DIVISIONAL CHARTS INJECTION ---





    # ── LIFE QUESTION ENGINE ───────────────────────────────────────
    life_question_context = ""
    try:
        life_question_context = build_life_question_context(
            question=request.question,
            chart_data=chart_data,
            dashas=dashas_response,
            patra=patra,
        )
    except Exception as e:
        print(f"Life question engine error: {e}")

    # ── DESH ───────────────────────────────────────────────────────
    desh = get_desh_context(
        country_code=country_code,
        supabase=supabase,
        chart_data=chart_data,
        language=language,
    )
    desh_context = desh_to_context_block(desh, patra)

    # ── YOGA DETECTION ────────────────────────────────────────────
    detected_yogas = []
    try:
        domain_for_yogas = concern if concern in (
            "wealth","legal","health","marriage","children",
            "property","foreign","education","career","billionaire","funding"
        ) else "career"
        relevant_divisions = {
            "wealth":[2,11], "billionaire":[2,10], "funding":[2,10],
            "legal":[6], "health":[6], "marriage":[9], "children":[7],
            "property":[4], "foreign":[12], "education":[24],
            "career":[9,10], "spirituality":[20],
        }.get(domain_for_yogas, [9,10])
        d_charts_for_yogas = get_all_d_charts(chart_data, relevant_divisions)
        yoga_results = detect_yogas_for_question(domain_for_yogas, chart_data, d_charts_for_yogas)
        detected_yogas = [y["name"] for y in yoga_results if y.get("present")]
    except Exception as e:
        print(f"Yoga detection error: {e}")

    # ── USER CORRELATIONS ─────────────────────────────────────────
    user_correlations_list = []
    if user_id:
        try:
            corr_res = supabase.table("user_correlations").select("*") \
                .eq("user_id", user_id).order("confidence_score", desc=True).execute()
            user_correlations_list = corr_res.data or []
        except Exception as e:
            print(f"Correlations fetch error: {e}")

    # ── RARITY SIGNALS ────────────────────────────────────────────
    rarity_signals = []
    try:
        rarity_signals = detect_rarity_signals(
            chart_data=chart_data,
            dashas=dashas_response,
            current_transits=current_transits,
            user_birth_date=chart_record["birth_date"],
        )
    except Exception as e:
        print(f"Rarity engine error: {e}")

    # ── PRECISION WINDOWS ─────────────────────────────────────────
    precision_windows = []
    try:
        precision_windows = find_precision_windows(
            chart_data=chart_data,
            dashas=dashas_response,
            current_transits=current_transits,
            concern=concern,
            detected_yogas=detected_yogas,
            user_correlations=user_correlations_list,
            months_ahead=12,
            top_n=3,
        )
    except Exception as e:
        print(f"Precision windows error: {e}")

    # ── CHAKRA READING ────────────────────────────────────────────
    chakra_reading_data = None
    try:
        chakra_reading_data = get_chakra_reading(
            chart_data=chart_data,
            dashas=dashas_response,
            current_transits=current_transits,
        )
    except Exception as e:
        print(f"Chakra engine error: {e}")

    # ── CHAPTER ARC ───────────────────────────────────────────────
    chapter_arc_data = None
    try:
        chapter_arc_data = build_chapter_arc(
            chart_data=chart_data,
            dashas=dashas_response,
            patra=patra,
        )
    except Exception as e:
        print(f"Chapter arc error: {e}")

    # ── LAL KITAB VARSHPHAL CONTEXT (zero extra DB queries) ───────
    lk_context = ""
    try:
        lk_context = format_lk_context_from_stored(
            lk_data=chart_record.get("lal_kitab_data"),
            concern=concern,
        )
    except Exception as e:
        print(f"Lal Kitab context error (non-fatal): {e}")

    # ── VEDIC ENRICHMENT CONTEXT ──────────────────────────────────
    enrichment_context = ""
    try:
        transit_map = {
            p: d.get("sign", "") for p, d in current_transits.items()
        } if isinstance(current_transits, dict) else {}
        enrichment_context = build_enrichment_context_v2(
            chart_data=chart_data,
            transit_planets=transit_map,
            concern=concern,
        )
    except Exception as e:
        print(f"Vedic enrichment context error (non-fatal): {e}")

    # ── SADE SATI PHASE ───────────────────────────────────────────
    sade_sati_context = ""
    try:
        moon_sign = chart_data["planets"]["Moon"]["sign"]
        sat_sign  = current_transits.get("Saturn", {}).get("sign", "") if isinstance(current_transits, dict) else ""
        if sat_sign:
            ss = get_sade_sati_phase(moon_sign, sat_sign)
            if ss:
                sade_sati_context = (
                    f"SADE SATI ACTIVE — Phase {ss['phase']} ({ss['phase_name']}): "
                    f"{ss['description']} Invitation: {ss['invitation']}"
                )
    except Exception as e:
        print(f"Sade sati context error (non-fatal): {e}")

    # ── LAYERED PREDICTIONS ───────────────────────────────────────
    predictions = build_layered_predictions(
        user_id=user_id,
        chart_data=chart_data,
        dashas=dashas_response,
        current_transits=current_transits,
        life_events=life_events,
        supabase=supabase,
        concern=concern,
        detected_yogas=detected_yogas,
    )
    predictions_context = predictions_to_context_block(predictions, chart_data, concern)

    # ── DKP SYNTHESIS ─────────────────────────────────────────────
    dkp_block = build_desh_kaal_patra_block(desh, patra, predictions)
    # C2: Append real-world economic context to existing dkp_block
    if dkp_context:
        dkp_block = (dkp_block or "") + "\n\n" + dkp_context

    # Append connection context if a matching person was found
    if _connection_context:
        dkp_block = (dkp_block or "") + "\n\n" + _connection_context
        print(f"[predict] Connection context appended to DKP block")

    # ── Compat context injection (from compatibility/start) ──────────
    if hasattr(request, "compat_context") and request.compat_context:
        _cc = request.compat_context
        _cc_name_b = _cc.get("name_b", "the other person")
        _cc_rel = _cc.get("relationship_type", "relationship")
        _cc_score = _cc.get("score", 0)
        _cc_dasha = _cc.get("chart_b_dasha", {})
        _compat_injection = f"""
COMPATIBILITY CONTEXT:
The user is asking about their {_cc_rel} with {_cc_name_b}.
Overall compatibility: {_cc_score}%
{_cc_name_b}'s current life chapter: {_cc_dasha.get('current_md', 'unknown')} energy cycle, {_cc_dasha.get('md_remaining_months', '?')} months remaining.
{_cc_name_b}'s phase: {_cc_dasha.get('phase_label', '')}
Answer this question in the context of BOTH people's current timing, not just the user's chart alone.
Do not use any planet names or astrological jargon — translate everything into plain energy language.
"""
        dkp_block = (dkp_block or "") + "\n\n" + _compat_injection
        print(f"[predict] Compat context injected for {_cc_name_b} ({_cc_rel})")

    # ── REMEDIES ──────────────────────────────────────────────────
    karakas_list = get_all_karakas(chart_data)
    user_age = patra.age

    remedy_objects = remedy_selector.select_remedies(
        supabase=supabase,
        chart_data=chart_data,
        dashas=dashas_response,
        transits=current_transits,
        user_age=user_age,
        question=request.question
    )
    remedies_out = _build_remedies(remedy_objects)

    # ── PROMPT ────────────────────────────────────────────────────
    rarity_context  = rarity_signals_to_context_block(rarity_signals)
    windows_context = precision_windows_to_context_block(precision_windows, concern)
    chakra_context  = chakra_reading_to_context_block(chakra_reading_data) if chakra_reading_data else ""
    arc_context     = chapter_arc_to_context_block(chapter_arc_data) if chapter_arc_data else ""

    # life_question_context is appended as an extra block below (prompt_builder
    # does not accept it as a kwarg — adding it there would crash every /predict)
    # Funding signals from rules engine v3 (6H/8H/12H aware)
    from antar_engine.astrological_rules import apply_funding_rules, get_funding_summary
    _funding_signals = apply_funding_rules(chart_data, concern, current_transits)
    _funding_summary = get_funding_summary(_funding_signals)

    # Build master context (D1-D12, yogas, LK, transits, anti-hallucination)
    _full_context = ""
    try:
        from antar_engine.chart_context_builder import build_complete_context
        from antar_engine.lal_kitab_engine import calculate_lal_kitab_analysis
        from antar_engine.transits_engine import calculate_current_transits
        _lk_data = calculate_lal_kitab_analysis(
            chart_data.get("planets", {}),
            chart_data.get("lagna", {}).get("sign", "") if isinstance(chart_data.get("lagna"), dict) else "",
        )
        # ── QUESTION MODE ROUTING — Sprint Apr7 ──────────────────────
        # ── Natal Signatures + Archetype (lazy compute / backfill) ──
        try:
            _planet_sigs, _char_archetype = ensure_signatures(
                request.chart_id, chart_data, supabase
            )
            _signature_block = build_signature_context_block(_planet_sigs, _char_archetype)
        except Exception as _sig_e:
            print(f"[predict] Signatures non-fatal error: {_sig_e}")
            _planet_sigs, _char_archetype, _signature_block = {}, {}, ""

        _question_mode = _classify_question_mode(request.question)
        print(f"[predict] Question mode: {_question_mode} for: {request.question[:60]}")

        if _question_mode == "life_path":
            _tr_data = {}
            print("[predict] Transits SKIPPED — life-path question")
        elif _question_mode == "daily":
            _tr_data_full = calculate_current_transits(chart_data)
            _tr_data = {k: v for k, v in (_tr_data_full or {}).items()
                        if any(p in str(k) for p in ["Moon", "Mercury"])
                        } if isinstance(_tr_data_full, dict) else _tr_data_full
            print("[predict] Transits filtered to Moon+Mercury — daily question")
        else:
            _tr_data = calculate_current_transits(chart_data)
            print("[predict] Full transits loaded — timing question")

        # Transit behavioral translation — plain English for Claude
        try:
            # _tr_data is a wrapper — actual transits are in current_transits key
            _tr_raw = _tr_data.get("current_transits", _tr_data) if isinstance(_tr_data, dict) else _tr_data
            # Normalize: could be list [{planet:..}] or dict {planet:{..}}
            if isinstance(_tr_raw, list):
                _tr_actual = {t["planet"]: t for t in _tr_raw if isinstance(t, dict) and "planet" in t}
            elif isinstance(_tr_raw, dict):
                _tr_actual = _tr_raw
            else:
                _tr_actual = {}
            if _tr_actual:
                _transit_list = []
                for _planet, _tdata in _tr_actual.items():
                    if isinstance(_tdata, dict):
                        _transit_list.append({
                            "planet": _planet,
                            "nakshatra": _tdata.get("nakshatra", "") or _tdata.get("nak_name", "") or _tdata.get("nakshatra_name", ""),
                            "sign": _tdata.get("sign", "") or _tdata.get("current_sign", "") or _tdata.get("transit_sign", ""),
                            "house": _tdata.get("house", 0) or _tdata.get("current_house", 0) or _tdata.get("transit_house", 0),
                        })
                _natal_planets = {}
                _raw_planets = chart_data.get("planets", {})
                if isinstance(_raw_planets, dict):
                    for _pname, _pdata in _raw_planets.items():
                        if isinstance(_pdata, dict):
                            _natal_planets[_pname] = {
                                "nakshatra": _pdata.get("nakshatra", ""),
                                "sign": _pdata.get("sign", ""),
                                "house": _pdata.get("house", 0),
                            }
                _user_prof = {
                    "first_name": chart_data.get("first_name") or chart_data.get("name", ""),
                    "current_country": chart_data.get("current_country", ""),
                }
                _transit_block = await build_transit_behavioral_block(
                    _transit_list, _natal_planets, _user_prof
                )
                if _transit_block:
                    # === TRANSIT ORDER FIX ===
                    # Don't += into _full_context here — build_complete_context()
                    # below will overwrite it. Stash instead, append after.
                    _pending_transit_block = _transit_block
                    print(f"[predict] Transit behavioral block stashed ({len(_transit_block)} chars)")
        except Exception as _tbe:
            print(f"[predict] Transit behavioral translation failed (non-fatal): {_tbe}")
        # ── END QUESTION MODE ROUTING ─────────────────────────────

        _chart_rec = supabase.table("charts").select("birth_date,gender,name").eq("id", request.chart_id).execute()
        _birth_dt  = _chart_rec.data[0].get("birth_date", "") if _chart_rec.data else ""
        _gender_v  = _chart_rec.data[0].get("gender", "") if _chart_rec.data else ""
        _name_v    = _chart_rec.data[0].get("name", "") if _chart_rec.data else ""
        _fname     = _name_v.split()[0] if _name_v else ""
        _full_context = build_complete_context(
            chart_data=chart_data,
            dashas={"vimsottari": dashas_response} if isinstance(dashas_response, list) else (dashas_response if isinstance(dashas_response, dict) else {"vimsottari": []}),
            birth_date=_birth_dt,
            first_name=_fname,
            gender=_gender_v,
            concern=concern,
            question=request.question,
            lk_analysis=_lk_data,
            transit_data=_tr_data,
            yogas=chart_data.get("yogas", []),
            divisional_charts=chart_data.get("divisional_charts", {}),
            question_mode=_question_mode,
            jaimini_data=_dbg_safe(chart_record.get("jaimini_data")) or None,
            lk_raw_data=_dbg_safe(chart_record.get("lal_kitab_data")) or _lk_data,
        )

        # ── Permanent completeness log ──
        print(f"[predict] chart={request.chart_id[:8]} "
              f"jaimini={bool(_dbg_safe(chart_record.get('jaimini_data')))} "
              f"lak={bool(chart_record.get('lal_kitab_data'))} "
              f"d9={bool((_cd.get('divisional_charts') or {}).get('d9') or (_cd.get('divisional_charts') or {}).get('D9'))} "
              f"varsha={bool(_birth_dt and _cd.get('planets'))} "
              f"transits={bool(_tr_data)}")

        # --- LAYER 2.5: JAIMINI CHARA DASHA (tie-breaker only) ---
        # Per spec: Jaimini fires ONLY when Vimsottari is ambiguous.
        # For 80% of questions, Vimsottari + divisional charts is sufficient.
        if "id" not in chart_data:
            chart_data["id"] = request.chart_id
        try:
            _vim_md = dashas_response.get("vimsottari", [{}])[0].get("lord_or_sign", "") if dashas_response else ""
            _use_jaimini = _vimsottari_is_ambiguous(chart_data, _vim_md, request.question)

            if _use_jaimini and chart_record.get("jaimini_data"):
                _full_context += "\n[JAIMINI TIE-BREAKER — Vimsottari signal is ambiguous or timing-specific]\n"
                _jaimini_block = format_jaimini_context_from_stored(chart_record)
                if _jaimini_block:
                    _full_context += _jaimini_block
                _concern = getattr(request, 'concern', '') or getattr(request, 'question', '') or ''
                _jaimini_conv = score_jaimini_convergence(chart_record, _concern)
                if _jaimini_conv:
                    _full_context += "\n" + _jaimini_conv + "\n"
                # Bridge only fires with Jaimini
                try:
                    _bridge_block = format_bridge_from_stored(chart_data)
                    if _bridge_block:
                        _full_context += _bridge_block
                except Exception as _be:
                    print(f"Bridge context failed (non-blocking): {_be}")
                print(f"[predict] Jaimini TIE-BREAKER fired for MD={_vim_md}")
            else:
                print(f"[predict] Jaimini SKIPPED — Vimsottari MD={_vim_md} is clear")
        except Exception as _je:
            print(f"Jaimini context failed (non-blocking): {_je}")
        # --- INJECT STEP 2+3 BLOCKS INTO FULL CONTEXT ---
        if system_state_block:
            _full_context += "\n" + system_state_block
        if dkp_block and dkp_block not in _full_context:
            _full_context += "\n" + dkp_block
        if divisional_block and divisional_block not in _full_context:
            _full_context += "\n" + divisional_block
        if diagnostic_block and diagnostic_block not in _full_context:
            _full_context += "\n" + diagnostic_block
        # Inject natal signature + archetype block
        if _signature_block and _signature_block not in _full_context:
            _full_context += "\n\n" + _signature_block
            print(f"[predict] Natal signature block injected — {_char_archetype.get('name','?')}")
        # --- END INJECT ---
        # === TRANSIT ORDER FIX (continued) ===
        # Re-append the stashed transit block now that build_complete_context
        # is done. This recovers the ~7s of Swiss Ephemeris work that was
        # being thrown away.
        try:
            _ptb = locals().get("_pending_transit_block")
            if _ptb:
                _full_context += "\n\n" + _ptb
                print(f"[predict] Transit behavioral block re-appended ({len(_ptb)} chars)")
        except Exception as _tbe2:
            print(f"[predict] Transit re-append failed (non-fatal): {_tbe2}")
        # === END TRANSIT ORDER FIX ===

        # === LIVE TRANSIT CONTEXT (Swiss Ephemeris) ===
        try:
            from antar_engine.transit_engine import get_full_transit_report, format_transit_for_prompt
            _live_transit = get_full_transit_report(chart_data)
            _live_transit_block = format_transit_for_prompt(_live_transit)
            if _live_transit_block:
                _full_context += "\n\n" + _live_transit_block
                print(f"[predict] Live transit context injected ({len(_live_transit_block)} chars)")
        except Exception as _lte:
            print(f"[predict] Live transit injection failed (non-fatal): {_lte}")
        # === END LIVE TRANSIT CONTEXT ===

        # === D9/D10 DIVISIONAL CHART CONTEXT ===
        try:
            from antar_engine.divisional_context import (
                extract_d9_context, extract_d10_context,
                format_d9_for_prompt, format_d10_for_prompt,
            )
            _d9_ctx = extract_d9_context(chart_data)
            _d10_ctx = extract_d10_context(chart_data)

            # Domain-gated injection: relationship → D9, career → D10, general → both
            _div_parts = []
            _concern_lower = (concern or "").lower()
            _q_lower = (request.question or "").lower()

            _is_relationship = _concern_lower in ("relationship", "marriage", "love", "partner", "compatibility") or any(
                kw in _q_lower for kw in ("relationship", "marriage", "love", "partner", "wife", "husband", "dating", "romantic")
            )
            _is_career = _concern_lower in ("career", "job", "business", "money", "wealth", "promotion") or any(
                kw in _q_lower for kw in ("career", "job", "business", "work", "promotion", "salary", "company", "professional")
            )

            if _is_relationship and _d9_ctx:
                _div_parts.append(format_d9_for_prompt(_d9_ctx))
            elif _is_career and _d10_ctx:
                _div_parts.append(format_d10_for_prompt(_d10_ctx))
            else:
                # General question — include both if available
                if _d9_ctx:
                    _div_parts.append(format_d9_for_prompt(_d9_ctx))
                if _d10_ctx:
                    _div_parts.append(format_d10_for_prompt(_d10_ctx))

            _div_block = "\n\n".join(_div_parts)
            if _div_block:
                _full_context += "\n\n" + _div_block
                print(f"[predict] D9/D10 divisional context injected ({len(_div_block)} chars, rel={_is_relationship}, career={_is_career})")
        except Exception as _dive:
            print(f"[predict] D9/D10 injection failed (non-fatal): {_dive}")
        # === END D9/D10 DIVISIONAL CHART CONTEXT ===

        print(f"[predict] Full context: {len(_full_context)} chars")
    except Exception as _ctx_e:
        import traceback
        print(f"[predict] Context build ERROR concern={concern}: {_ctx_e}")
        print(f"[predict] dashas_response type={type(dashas_response)} len={len(dashas_response) if hasattr(dashas_response,'__len__') else 'N/A'}")
        if isinstance(dashas_response, list) and dashas_response:
            print(f"[predict] first dasha row keys: {list(dashas_response[0].keys()) if isinstance(dashas_response[0],dict) else type(dashas_response[0])}")
        print(f"[predict] Traceback: {traceback.format_exc()}")

    # Diagnostic mode instruction — fires when user describes a symptom
    _symptom_instruction = ""
    if _question_mode == "symptom":
        _primary_domain, _secondary_domain = _get_symptom_domain(request.question)
        _symptom_instruction = f"""
DIAGNOSTIC MODE — USER DESCRIBED A SYMPTOM, NOT A QUESTION.
Primary instrument under investigation: {_primary_domain}
Secondary instrument: {_secondary_domain}

Follow this EXACT diagnostic sequence — do not skip steps:

STEP 1 — SCAN: Confirm which instruments this symptom maps to.
  Primary: {_primary_domain} | Secondary: {_secondary_domain}
  Look at what's happening in these domains in the chart context above.

STEP 2 — DIAGNOSE: Answer these 4 questions from the chart data:
  1. Is the instrument ({_primary_domain}) natally stressed or strong?
  2. What is the current dasha lord — is it a friend or enemy of this instrument?
  3. Is any current transit adding friction to {_primary_domain} right now?
  4. NATAL or ACTIVATION? Natal = this pattern has always existed. Activation = started in last 6-18 months due to dasha/transit shift.

STEP 3 — PRESCRIBE: One intervention based on diagnosis.
  If NATAL pattern: "This is a hardwired configuration. The leverage point is [specific action]."
  If ACTIVATION: "This is temporary. It lifts on [specific date] when [dasha/transit shifts]. Until then: [specific action]."
  NEVER say "things will improve" without a date or mechanism.

MANDATORY RESPONSE FORMAT:
✦ PATTERN IDENTIFIED: [What is actually happening — 10 words max, business language]

CAUSE: [2 sentences. Is this natal or activation? Which instrument + why.]

DIAGNOSIS: [{_primary_domain} is [under pressure / blocked / misfiring] because [specific chart reason].]

THE MOVE: [One action addressing the ROOT cause, not the surface symptom.]

LIFTS: [Specific date or condition when this pattern eases — or "permanent configuration, here's the workaround"]

CRITICAL RULES:
- Natal vs Activation distinction is MANDATORY — user needs to know if this is forever or temporary
- Never give generic "work on yourself" advice — every line must reference chart data
- No Sanskrit, no house numbers, no planet names — instrument labels only
- Under 150 words total
"""

    if _full_context and len(_full_context) > 500:
        print(f"[predict] Using master context ({len(_full_context)} chars) concern={concern}")
        _question_instruction = _symptom_instruction if _symptom_instruction else "Answer the question directly, referencing specific planets, houses, yogas, and dasha periods from the context above. No generic advice."
        prompt = _full_context + f"\n\nQUESTION: {request.question}\nCONCERN: {concern}\n\n{_question_instruction}"
    else:
        print(f"[predict] Master context empty — falling back to build_predict_prompt")
        prompt = build_predict_prompt(
            question=request.question,
            chart_data=chart_data,
            dashas=dashas_response,
            life_events=life_events,
            profile=profile_text,
            transit_summary=transit_summary,
            country_context=country_context,
            timing_text=timing_text,
            nation_insight=nation_insight,
            language=language,
            predictions_context=predictions_context,
            concern=concern,
            country_code=country_code or "US",
            patra_context=patra_context,
            desh_context=desh_context,
            dkp_block=dkp_block,
            funding_summary=_funding_summary,
        
        divisional_block=divisional_block,
        )

    # ── Question-mode gating for extra blocks ────────────────────
    _q_low = (request.question or "").lower()
    _is_health_spiritual = concern in ("health","spiritual","wellness") or any(
        kw in _q_low for kw in ["health","chakra","spiritual","energy","body","soul"]
    )
    _is_remedy_lk = any(kw in _q_low for kw in [
        "remedy","remedies","lal kitab","karma","luck","fix","help","weak"
    ]) or _question_mode in ("remedy","spiritual")
    _is_enrichment = concern in ("career","wealth","money","timing","relationship") or _question_mode in ("timing","career","wealth")
    _is_life_path  = _question_mode == "life_path" or any(kw in _q_low for kw in [
        "purpose","mission","destiny","why am i","life path","soul"
    ])

    _gated_extra_blocks = [
        ("rarity",       rarity_context,       True),
        ("windows",      windows_context,       True),
        ("arc",          arc_context,           True),
        ("chakra",       chakra_context,        _is_health_spiritual),
        ("lk",           lk_context,            _is_remedy_lk),
        ("enrichment",   enrichment_context,    _is_enrichment),
        ("sade_sati",    sade_sati_context,     bool(sade_sati_context)),
        ("life_question",life_question_context, _is_life_path),
        ("e2_contradiction", _contradiction_block if '_contradiction_block' in dir() else "", True),
    ]

    _extra_total = 0
    for _extra_name, _extra_block, _include in _gated_extra_blocks:
        try:
            if _extra_block and _include:
                prompt += f"\n\n{_extra_block}"
                _extra_total += len(_extra_block)
            elif _extra_block and not _include:
                pass  # Gated out
        except Exception as _eb_e:
            print(f"[predict] extra_block {_extra_name} error: {_eb_e}")
    print(f"[predict] Extra blocks injected: {_extra_total} chars")

    # ── LLM CALL — passes conversation history for multi-turn context ──
    # Use different system prompt for master context vs template
    # ── C3 + C4: Append memory, diagnostic, and common sense to prompt ──
    _memory_block     = (_memory or {}).get("memory_block", "")
    _diagnostic_block = (_memory or {}).get("diagnostic_block", "")

    for _block in [_memory_block, _diagnostic_block, _cs_block]:
        if not _block:
            continue
        prompt += f"\n\n{_block}"
    # Inject the diagnostic pre-scan block (Sprint 1.2)
    if diagnostic_block:
        prompt += f"\n\n{diagnostic_block}"
    # ── end C3+C4 injection ───────────────────────────────────────


    # ── Domain Audit Rules (Sprint D) ────────────────────────────
    _domain_rules_full = DOMAIN_AUDIT_RULES.get(concern, DOMAIN_AUDIT_RULES.get("general", ""))
    # Truncate domain audit to first 800 chars — rules are repetitive after that
    _domain_rules = _domain_rules_full[:800] if len(_domain_rules_full) > 800 else _domain_rules_full
    # HARD JARGON CONSTRAINT — prepended to EVERY prompt
    _hard_constraint = """
ABSOLUTE RULES (violating these rules means the response is rejected):
1. USE planet names with parenthetical context on first mention:
   Sun planet of (identity, authority, vitality), Moon planet of (emotion, mind, nurturing),
   Mars planet of (action, drive, energy), Mercury planet of (communication, intellect, adaptability),
   Jupiter planet of (growth, wisdom, expansion), Venus planet of (love, partnership, money),
   Saturn planet of (discipline, structure, time), Rahu planet of (ambition, breakthrough, foreign),
   Ketu planet of (intuition, release, spirituality).
   After first mention, use planet name alone.
2. NEVER use house numbers (1st house, 10th house). Use area labels:
   1st = identity area, 2nd = wealth area, 3rd = courage area, 4th = home area,
   5th = creativity area, 6th = work area, 7th = partnership area, 8th = transformation area,
   9th = luck area, 10th = career area, 11th = gains area, 12th = foreign area.
3. NEVER use Sanskrit terms (Yoga, Dasha, Nakshatra, Lagna, Rashi, Karaka, Amatyakaraka, Atmakaraka, Bhava, Graha, Navamsa, D9, D10, D1, Budhaditya, Muhurta, Panchami).
4. NEVER reference chart divisions or technical astrology concepts.
5. NEVER use FIELD×MODE codenames. These are DEPRECATED:
   Magnetism Field, Revenue Pipeline, Ambition Engine, Authority Signal, Emotional Radar,
   Growth Amplifier, Hungry Becoming, Alliance Sync, Creative Pulse, Velocity Engine,
   Foundation Shield, Wisdom Lens, Health Matrix, Resource Grid, Capital Runway,
   Processing Speed, Action Drive, Structural Load, Intuition Compass, System Vitals,
   Capital Reserves, Action Capacity, Creation Engine, Conflict Shield, Fortune Vector,
   Authority Engine, Global Vector.
6. NEVER use: MD, AD, PD, mahadasha, antardasha, pratyantar.
   Use: "chapter", "sub-chapter", "inner window".
7. NEVER use: drishti, bhava, rashi, graha, karaka in user-facing text.
5. The current year is 2026, NOT 2025. Today is """ + __import__('datetime').datetime.utcnow().strftime("%B %d, %Y") + """.
6. Answer the user's QUESTION directly. Do not explain astrological mechanics.
7. Use business/strategic language: positioning, leverage, runway, capacity, friction, momentum.
8. End with THE MOVE — one specific action for this week.
9. RESPONSE FORMAT — STRICT. Total response under 200 words.
10. STRUCTURE (mandatory):
    Line 1: ✦ VERDICT: [ACTION VERB]. [Direct call in 8 words or less]
    Line 2-3: One short paragraph (2-3 sentences max) explaining WHY using business language.
    Line 4: PROBABILITY: XX% (only if user asks chances/will/likelihood)
    Line 5-7: YOUR MOVE — three numbered actions:
        1. [Specific action for THIS week]
        2. [Specific action for next 2 weeks]
        3. [Specific action for next 30 days]
    Line 8: TIMING: [When the window opens/closes]
11. NO POETIC LANGUAGE. NO METAPHORS. NO "your visibility is real but...". 
12. NO MARKDOWN HEADERS (## or ###). NO LONG ESSAYS. Founders read in 30 seconds.

RESPONSE PATTERN:
1. State the verdict directly (first sentence)
2. Show the energy map evidence (which planets, which areas, what state)
3. Connect to the user's actual life context
4. Give timing with specific window
5. End with YOUR MOVE — one specific action. Never end with a question.

VOCABULARY RULES:
- Use planet names with parenthetical on first mention: "Saturn planet of (discipline, structure, time)"
- After first mention, use planet name alone: "Saturn"
- Never use house numbers. Use area labels: identity, wealth, courage, home, creativity, work, partnership, transformation, luck, career, gains, foreign.
- Never use: MD, AD, PD, mahadasha, antardasha, pratyantar. Use: chapter, sub-chapter, inner window.
- Never use FIELD×MODE codenames (deprecated).
- Never use: drishti, bhava, rashi, graha, karaka in user-facing text.
13. If user asks "will I", "what are my chances", "is it possible" — LEAD with PROBABILITY: XX%.
14. Treat the user like a busy founder/executive. They need answers, not analysis.

15. STRICT FORMAT — TOTAL RESPONSE UNDER 150 WORDS. NO EXCEPTIONS.

16. MANDATORY OUTPUT TEMPLATE for Will/Should/Can/What-are-my-chances questions:

   Line 1 (HEADLINE — under 12 words):
   [ONE SENTENCE answering the question directly]
   
   Line 2 (PROBABILITY — only for "will I" / "what are my chances" questions):
   PROBABILITY: XX% (use a real number from your analysis, never "high" or "low")
   
   Line 3-4 (WHY — 2 short sentences, max 30 words total):
   [Why the answer is what it is, in business language]
   
   Line 5-7 (NUMBERED ACTIONS):
   1. THIS WEEK: [one specific action]
   2. NEXT 2 WEEKS: [one specific action]
   3. BEFORE [date]: [one specific action]
   
   Line 8 (TIMING):
   WINDOW: [exact dates when window opens/closes]

17. NO POETIC LANGUAGE. Banned phrases:
    - "Your X is real, but..." 
    - "The window is open" without a date
    - "Magnetic presence", "authority engine peak leverage"
    - Any sentence longer than 20 words
    - Any paragraph over 3 sentences
    
18. RESPOND IN THE USER'S LANGUAGE. If language="es", respond entirely in Spanish.
    If language="en", respond entirely in English. NEVER mix languages.

19. If you write more than 150 words, you have FAILED. Cut it down.

20. The founder reads on a phone in 20 seconds. Optimize for SCAN, not READ.

21. HEADLINE RULE — ONE answer only. If the user asks "which of A, B, or C", the headline picks the WINNER in 8 words or less.
    GOOD: "Consulting wins. Real estate is backup."
    BAD: "Consulting pays now; real estate closes in 60 days; AI is 2027-2028 build."

22. NO COMPOUND SENTENCES IN THE HEADLINE. One subject. One verb. One verdict.

23. WHEN COMPARING OPTIONS, give a score for each:
    OPTION A (Consulting): 80% — immediate cash, zero risk
    OPTION B (Real Estate): 60% — closing window, execute by date
    OPTION C (AI Startup): 20% — wrong timing, defer

24. LANGUAGE LOCK: If language="es", the entire response is in Spanish. Including:
    - signal_line (in Spanish)
    - plain_summary (in Spanish)
    - action_item (in Spanish)
    - timing_window (in Spanish)
    Plain_english.py post-processing must NOT translate back to English.

25. NO ASTROLOGY METAPHORS OR CODENAMES. Banned:
    - Any FIELD×MODE codename (Magnetism Field, Revenue Pipeline, Ambition Engine, Authority Signal, etc)
    - "Capital Reserves under pressure", "Action Drive sub-cycle"
    Replace with plain language using planet names + area labels:
    - "Venus planet of (love, partnership) is active in your career area"
    - "Saturn is tightening your wealth area until June"
    - "Mars energy is high through May"
"""
    # ── Symptom → Practice Bridge ────────────────────────────────────────────
    if _question_mode == "symptom":
        try:
            from antar_engine.practice_engine import generate_practice_schedule, format_practice_for_predict_prompt
            from datetime import date as _date
            _week_of = _date.today() - __import__('datetime').timedelta(days=_date.today().weekday())
            # Try cache first
            _pcache = supabase.table("practice_schedule_cache") \
                .select("schedule_data") \
                .eq("chart_id", request.chart_id) \
                .eq("week_of", _week_of.isoformat()) \
                .execute()
            if _pcache.data:
                _psched = _pcache.data[0]["schedule_data"]
            else:
                # Fetch jaimini + lk data needed by practice engine
                _pr = supabase.table("charts").select(
                    "jaimini_data, lal_kitab_data, current_country, birth_date"
                ).eq("id", request.chart_id).single().execute()
                _pr_row = _pr.data or {}
                _psched = generate_practice_schedule(
                    chart_data=chart_data,
                    jaimini_data=_pr_row.get("jaimini_data") or {},
                    lal_kitab_data=_pr_row.get("lal_kitab_data") or {},
                    current_country=_pr_row.get("current_country") or "US",
                    birth_date=str(_pr_row.get("birth_date") or ""),
                )
            _practice_block = format_practice_for_predict_prompt(_psched)
            if _practice_block:
                _full_context += "\n\n" + _practice_block
                print(f"[predict] Symptom→Practice bridge injected ({len(_practice_block)} chars)")
        except Exception as _pbe:
            print(f"[predict] Practice bridge error (non-fatal): {_pbe}")
    # ── end practice bridge ───────────────────────────────────────────────────

    # Jargon-only constraint — prepended to ALL modes (format rules live in system prompt)
    _today_str = __import__('datetime').datetime.utcnow().strftime("%B %d, %Y")
    _jargon_only = (
        "ABSOLUTE RULES (no exceptions):\n"
        "1. USE planet names with parenthetical on first mention: "
        "Sun planet of (identity, authority, vitality), Moon planet of (emotion, mind, nurturing), "
        "Mars planet of (action, drive, energy), Jupiter planet of (growth, wisdom, expansion), "
        "Venus planet of (love, partnership, money), Saturn planet of (discipline, structure, time), "
        "Rahu planet of (ambition, breakthrough, foreign), Ketu planet of (intuition, release, spirituality). "
        "After first mention, use planet name alone.\n"
        "2. NEVER use house numbers. Use area labels: "
        "1st=identity area, 2nd=wealth area, 3rd=courage area, 4th=home area, "
        "5th=creativity area, 6th=work area, 7th=partnership area, 8th=transformation area, "
        "9th=luck area, 10th=career area, 11th=gains area, 12th=foreign area.\n"
        "3. NEVER use Sanskrit terms (Dasha, Nakshatra, Lagna, Yoga, Rashi, etc).\n"
        "4. NEVER use FIELD×MODE codenames (Magnetism Field, Revenue Pipeline, Ambition Engine, etc). DEPRECATED.\n"
        "5. NEVER use: MD, AD, PD, mahadasha, antardasha. Use: chapter, sub-chapter, inner window.\n"
        f"6. Today is {_today_str}. The current year is 2026.\n"
        "7. Answer the QUESTION directly. Lead with VERDICT in first sentence.\n"
        "8. THE MOVE at the end — one specific action for this week."
    )
    prompt = _jargon_only + "\n\n" + prompt
    if False:  # dead code block — keeps old symptom path reference intact
        _jargon_only = """ABSOLUTE RULES (no exceptions):
1. USE planet names with parenthetical on first mention (e.g. "Jupiter planet of (growth, wisdom)"). After first mention, planet name alone.
2. NEVER use house numbers. Use area labels (identity area, wealth area, career area, etc). NEVER use FIELD×MODE codenames.
3. NEVER use Sanskrit terms (Dasha, Nakshatra, Lagna, Yoga, Rashi, etc).
4. The current year is 2026. Today is """ + __import__('datetime').datetime.utcnow().strftime("%B %d, %Y") + """.
5. Use business language only: positioning, leverage, runway, capacity, friction, momentum.
6. Follow the DIAGNOSTIC FORMAT exactly as instructed — do not switch to VERDICT format.
"""
        prompt = _jargon_only + "\n\n" + prompt
        print(f"[predict] Symptom mode — diagnostic format active (hard constraint bypassed)")

    if _domain_rules:
        prompt = "\n\n" + _domain_rules + "\n\n" + DOMAIN_BRIDGE_INSTRUCTION + "\n\n" + prompt
        print(f"[predict] Domain audit rules injected for concern={concern}")

    _using_master = _full_context and len(_full_context) > 500
    print(f"[predict] using_master={_using_master} prompt_len={len(prompt)}")

    if _using_master:
        # Add concern focus to prompt (not system override — avoids empty responses)
        try:
            from antar_engine.concern_router import get_priority_context_instruction
            _priority_instr = get_priority_context_instruction(concern)
            prompt += f"\n\n{_priority_instr}"
        except Exception:
            pass
        prompt += "\n\nCRITICAL: Do NOT use 'YOUR SIGNAL RIGHT NOW' or 'THE PATTERN THAT\'S ACTIVE' as headers. Answer the question directly in the first sentence."

        # Sprint D: Use domain-specific system prompt as system_override
        try:
            from antar_engine.concern_router import build_concern_system_prompt
            _domain_system = build_concern_system_prompt(concern)
        except Exception:
            _domain_system = ""

        _format_rules = (
            "RESPONSE FORMAT (always follow):\n"
            "Line 1: ✦ VERDICT: [ACTION VERB]. [Direct call in 8 words or less]\n"
            "Lines 2-3: 2-3 sentences WHY in business language (no astrology jargon).\n"
            "Lines 4-6: YOUR MOVE — three numbered actions (this week / next 2 weeks / next 30 days).\n"
            "Line 7: TIMING: [exact window].\n"
            "TOTAL: under 150 words. No markdown headers. No poetic language.\n"
            "If user asks will/chances/probability: lead with PROBABILITY: XX%.\n"
        )
        _master_system = (_domain_system if _domain_system else (
            "You are Antar — a precise Vedic astrology AI. "
            "Answer directly using the data provided. "
            "Lead with the actual answer in the first sentence. "
        )) + "\n\n" + _format_rules
        # --- Sprint L: Language injection ---
        from language_utils import build_language_instruction, resolve_language
        _lang = resolve_language({"language": getattr(request, "language", None)}, chart_record)
        _lang_block = build_language_instruction(_lang)
        if _lang_block:
            _master_system = _lang_block + _master_system
            print(f"[predict] Language injection: {_lang}")
        # --- end Sprint L ---


        # ================================================================
        # JSON PATH (use_json_context=True) — Phase 4 JSON-first refactor
        # ================================================================
        if getattr(request, "use_json_context", False):
            # For past-event questions: clear prose context so it doesn't
            # contaminate Claude's reasoning. JSON path provides all needed context.
            _past_kw = ["when did","when was","what year","married","born","child",
                        "son","daughter","moved","divorc","america","foreign",
                        "cuándo","cuando","nació","hijo","hija","casé","mudé"]
            if any(kw in request.question.lower() for kw in _past_kw):
                _full_context = ""
                print(f"[json-v2] Past question detected — cleared prose context")
            try:
                print(f"[json-v2] JSON path activated for chart {request.chart_id}")
                from antar_engine.chart_context_builder_json import (
                    build_chart_context_json,
                    chart_static_to_json,
                    live_to_json,
                    estimate_token_count,
                )
                from antar_engine.predict_system_prompt_v2 import PREDICT_SYSTEM_PROMPT_V2

                _json_ctx = await build_chart_context_json(
                    chart_id=request.chart_id,
                    question=request.question,
                    concern=concern,
                    language=_lang if "_lang" in dir() else language,
                    supabase=supabase,
                )

                # ── PAST EVENT HISTORICAL DASHA INJECTION ─────────────────
                _past_keywords = [
                    "when did", "when was", "what year", "which year",
                    "when did i", "when were", "what happened", "how old",
                    "married", "marriage", "wedding",
                    "born", "birth", "child", "children", "son", "daughter",
                    "moved", "relocat", "immigrat", "america", "foreign",
                    "divorc", "separat", "ended", "split",
                    "cuándo", "cuando", "qué año", "que año",
                    "casé", "matrimonio", "boda", "nació", "hijo", "hija",
                    "mudé", "emigr", "divorcié", "separé", "terminó",
                ]
                _is_past_q = any(kw in request.question.lower() for kw in _past_keywords)

                if _is_past_q:
                    # Run Python DashaEventMapper — compute windows deterministically
                    try:
                        from antar_engine.dasha_event_mapper import map_all_events, format_for_prompt
                        _mapper_results = map_all_events(
                            birth_year=_birth_year,
                            lagna=_lagna_sign,
                            ads=_ads,
                        )
                        _mapper_block = format_for_prompt(_mapper_results)
                        _tl += _mapper_block
                        print(f"[json-v2] DashaEventMapper: {sum(1 for v in _mapper_results.values() if v)}/5 events computed")
                    except Exception as _me:
                        print(f"[json-v2] DashaEventMapper failed (non-fatal): {_me}")
                if _is_past_q:
                    try:
                        _hist = supabase.table("dasha_periods") \
                            .select("planet_or_sign,start_date,end_date,level,type,metadata,sequence") \
                            .eq("chart_id", request.chart_id) \
                            .eq("system", "vimsottari") \
                            .order("sequence") \
                            .execute()

                        _mds, _ads = [], []
                        for _row in _hist.data:
                            _lv = _row.get("level")
                            _tp = str(_row.get("type","")).lower()
                            if _lv == 1 or _tp in ("mahadasha","md","1"):
                                _mds.append(_row)
                            elif _lv == 2 or _tp in ("antardasha","ad","2"):
                                _ads.append(_row)

                        try:
                            _bd_row = supabase.table("charts") \
                                .select("birth_date,chart_data") \
                                .eq("id", request.chart_id) \
                                .single().execute()
                            _birth_year = int(str(_bd_row.data.get("birth_date","1974"))[:4])
                            _lagna_sign = (_bd_row.data.get("chart_data") or {}) \
                                .get("lagna", {}).get("sign", "unknown")
                        except Exception:
                            _birth_year = 1974
                            _lagna_sign = "unknown"

                        _tl = "\n\n## HISTORICAL VIMSOTTARI DASHA SEQUENCE\n"
                        _tl += f"Birth year: {_birth_year} | Lagna: {_lagna_sign}\n\n"
                        _tl += "MAHADASHAS:\n"
                        for _r in _mds:
                            _p = _r.get("planet_or_sign","")
                            _s = str(_r.get("start_date",""))[:10]
                            _e = str(_r.get("end_date",""))[:10]
                            _tl += f"  {_p} MD: {_s} to {_e}\n"

                        _ads_by_md = {}
                        for _r in _ads:
                            _parent = (_r.get("metadata") or {}).get("parent_lord","?")
                            if _parent not in _ads_by_md:
                                _ads_by_md[_parent] = []
                            _p = _r.get("planet_or_sign","")
                            _s = str(_r.get("start_date",""))[:10]
                            _e = str(_r.get("end_date",""))[:10]
                            _ads_by_md[_parent].append(f"    {_p} AD: {_s} to {_e}")

                        _tl += "\nANTARDASHAS BY MD:\n"
                        for _md_p, _ad_lines in _ads_by_md.items():
                            _tl += f"  {_md_p} MD:\n" + "\n".join(_ad_lines) + "\n"

                        _tl += f"""
## ELIGIBLE YEAR RANGES (birth year = {_birth_year})
  Marriage eligible:          {_birth_year+20} to {_birth_year+35}
  First child eligible:       {_birth_year+22} to {_birth_year+37} (must be after marriage)
  Second child:               first_child_year + 1 to + 4
  Foreign relocation:         {_birth_year+15} to {_birth_year+45}
  Divorce:                    marriage_year + 5 to + 25

Apply the classical AD priority rules from the system prompt.
State a specific year. Never predict past events as future windows.
"""
                        if isinstance(_json_ctx, dict):
                            _json_ctx["_historical_dasha"] = _tl
                        print(f"[json-v2] Past event: {len(_mds)} MDs, {len(_ads)} ADs, birth={_birth_year}, lagna={_lagna_sign}")

                    except Exception as _he:
                        print(f"[json-v2] Historical dasha failed (non-fatal): {_he}")
                # ── END PAST EVENT INJECTION ──────────────────────────────

                _static_json = chart_static_to_json(_json_ctx)
                _live_json   = live_to_json(_json_ctx)

                # System prompt = framework (cached) + static chart JSON (cached)
                # ## LIVE DATA marker = split point for KV cache
                _hist_suffix = _json_ctx.get("_historical_dasha", "") if isinstance(_json_ctx, dict) else ""
                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\n\n## CHART DATA (JSON)\n"
                    + _static_json
                    + "\n\n## LIVE DATA\n"
                    + _live_json
                    + (_hist_suffix if _hist_suffix else "")
                )

                # User message = just the question
                _json_user_prompt = (
                    f"Question: {request.question}\n"
                    f"Domain: {concern}\n"
                    "Respond with a JSON object exactly as specified in the output format."
                )

                print(f"[json-v2] system={len(_json_system)} chars "
                      f"(~{estimate_token_count(_json_system)} tokens), "
                      f"user={len(_json_user_prompt)} chars")

                _json_raw, _json_tokens = await call_llm_claude(
                    _json_user_prompt,
                    history=request.conversation_history or [],
                    system_override=_json_system,
                )

                # Parse structured response
                import json as _json_mod
                _json_text = _json_raw.strip()
                if _json_text.startswith("```"):
                    _json_text = _json_text.split("\n", 1)[-1]
                    _json_text = _json_text.rsplit("```", 1)[0]
                try:
                    _parsed = _json_mod.loads(_json_text)
                except Exception as _parse_err:
                    # Fallback: regex-extract known fields from truncated/malformed JSON
                    # Preserves usable content even when response was cut off mid-output
                    print(f"[json-v2] JSON parse failed ({_parse_err}) — attempting regex fallback")
                    import re as _re_mod
                    _parsed = {}
                    # Fields likely to be present as string values in the response
                    _str_fields = [
                        "verdict", "plain_summary", "signal_line", "action_item",
                        "timing_window", "why_this", "bridge_practice_note",
                        "confidence"
                    ]
                    for _field in _str_fields:
                        # Match "field": "value" — non-greedy, handles escaped quotes inside
                        _pattern = r'"' + _field + r'"\s*:\s*"((?:[^"\\]|\\.)*)"'
                        _m = _re_mod.search(_pattern, _json_text)
                        if _m:
                            # Unescape common JSON escapes
                            _val = _m.group(1).replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
                            _parsed[_field] = _val
                    # Extract layers_used array if present
                    _layers_match = _re_mod.search(r'"layers_used"\s*:\s*\[(.*?)\]', _json_text, _re_mod.DOTALL)
                    if _layers_match:
                        _layer_strs = _re_mod.findall(r'"((?:[^"\\]|\\.)*)"', _layers_match.group(1))
                        _parsed["layers_used"] = _layer_strs
                    else:
                        _parsed["layers_used"] = []
                    # Safety net: if we got NOTHING via regex, fall back to raw text
                    if not any(_parsed.get(f) for f in ["plain_summary", "signal_line", "verdict"]):
                        print(f"[json-v2] Regex fallback salvaged nothing — using raw text")
                        _parsed = {"plain_summary": _json_raw[:2000], "verdict": "", "signal_line": ""}
                    else:
                        _salvaged = [f for f in _str_fields if _parsed.get(f)]
                        print(f"[json-v2] Regex fallback salvaged: {_salvaged}")

                print(f"[json-v2] response parsed — confidence={_parsed.get('confidence','?')}")

                # Save to chat_messages if table exists
                try:
                    supabase.table("chat_messages").insert({
                        "chart_id": request.chart_id,
                        "question": request.question,
                        "plain_summary": _parsed.get("plain_summary", ""),
                        "signal_line": _parsed.get("signal_line", ""),
                        "action_item": _parsed.get("action_item", ""),
                        "timing_window": _parsed.get("timing_window", ""),
                        "confidence": {"high": 0.85, "medium": 0.65, "low": 0.45}.get(
                        str(_parsed.get("confidence", "medium")).lower(), 0.65),
                    "confidence_label": _parsed.get("confidence", "medium"),
                        "domain": concern,
                        "language": _lang if "_lang" in dir() else language,
                        "why_this": _parsed.get("why_this", ""),
                        "bridge_practice_note": _parsed.get("bridge_practice_note", ""),
                    }).execute()
                except Exception as _save_e:
                    print(f"[json-v2] chat_messages save failed (non-fatal): {_save_e}")

                # Map confidence string -> float for PredictResponse model
                _conf_map = {"high": 0.85, "medium": 0.65, "low": 0.45}
                _conf_str = str(_parsed.get("confidence", "medium")).lower()
                _conf_float = _conf_map.get(_conf_str, 0.65)
                _pred_text = (
                    _parsed.get("verdict", "") + " " + _parsed.get("plain_summary", "")
                ).strip()
                _factors = [str(x) for x in _parsed.get("layers_used", [])]

                return {
                    # Required fields (PredictResponse model)
                    "prediction":   _pred_text,
                    "confidence":   _conf_float,
                    "factors":      _factors,
                    # Optional structured fields for frontend
                    "plain_summary":        _parsed.get("plain_summary", ""),
                    "signal_line":          _parsed.get("signal_line", ""),
                    "action_item":          _parsed.get("action_item", ""),
                    "timing_window":        _parsed.get("timing_window", ""),
                    "why_this":             _parsed.get("why_this", ""),
                    "bridge_practice_note": _parsed.get("bridge_practice_note", ""),
                    "signal_confidence":    _conf_str,
                    "rarity_signals":       [],
                    "precision_windows":    [],
                    "all_domains":          [],
                }
            except Exception as _json_e:
                import traceback
                print(f"[json-v2] FAILED — falling back to prose path: {_json_e}")
                print(f"[json-v2] Traceback: {traceback.format_exc()}")
                # Fall through to existing prose path below
        # ================================================================
        # END JSON PATH
        # ================================================================
        # === KV CACHE FIX ===
        # Move _full_context into the system block (cacheable region) instead
        # of leaving it glued to the user prompt. Insert ## LIVE DATA marker
        # so call_llm_claude splits cached static block from per-call dynamic.
        # _full_context is mostly stable per chart (natal sig, DKP, Jaimini,
        # divisional charts, diagnostic). Anything dynamic per call stays in
        # the user prompt below.
        _cacheable_context = _full_context if _full_context else ""
        if _cacheable_context:
            # NOTE: _full_context already contains the canonical "## LIVE DATA"
            # marker (placed correctly by chart_context_builder.py after the
            # static Vedic rules block). Do NOT add a second marker here —
            # call_llm_claude splits on the first occurrence.
            _master_system = (
                _master_system
                + "\n\n=== CHART CONTEXT ===\n"
                + _cacheable_context
            )
            # Strip _full_context from the user prompt — it now lives in system
            # The user prompt becomes just question + concern + instruction
            _user_only_prompt = prompt
            if _full_context and _full_context in _user_only_prompt:
                _user_only_prompt = _user_only_prompt.replace(_full_context, "", 1).lstrip()
            prompt = _user_only_prompt
            print(f"[predict] KV cache: system={len(_master_system)} chars, user_prompt={len(prompt)} chars")

        # === END KV CACHE FIX ===

        prediction_text, tokens_used = await call_llm_claude(
            prompt,
            history=request.conversation_history or [],
            system_override=_master_system,
        )


    else:
        # Sprint D: domain system prompt for non-master path too
        try:
            from antar_engine.concern_router import build_concern_system_prompt
            _domain_system_fallback = build_concern_system_prompt(concern)
        except Exception:
            _domain_system_fallback = ""
        # --- Sprint L: Language injection (fallback path) ---
        if '_lang_block' not in dir() or not _lang_block:
            from language_utils import build_language_instruction, resolve_language
            _lang = resolve_language({"language": getattr(request, "language", None)}, chart_record)
            _lang_block = build_language_instruction(_lang)
        if _lang_block and _domain_system_fallback:
            _domain_system_fallback = _lang_block + _domain_system_fallback
        elif _lang_block:
            _domain_system_fallback = _lang_block
        # --- end Sprint L ---
        # --- Sprint L: Language injection (fallback path) ---
        if '_lang_block' not in dir() or not _lang_block:
            from language_utils import build_language_instruction, resolve_language
            _lang = resolve_language({"language": request.language}, chart_record)
            _lang_block = build_language_instruction(_lang)
        if _lang_block and _domain_system_fallback:
            _domain_system_fallback = _lang_block + _domain_system_fallback
        elif _lang_block:
            _domain_system_fallback = _lang_block
        # --- end Sprint L ---
        prediction_text, tokens_used = await call_llm_claude(
            prompt,
            history=request.conversation_history or [],
            system_override=_domain_system_fallback or "",
        )

    print(f"[predict] LLM response len={len(prediction_text) if prediction_text else 0} concern={concern}")
    # ── C1: Plain English post-processing ────────────────────────
    _pe = None
    try:
        _pe = await generate_plain_english(
            raw_prediction=prediction_text or "",
            chart_context={
                "lagna":      chart_record.get("lagna_sign"),
                "dasha":      chart_record.get("current_dasha"),
                "age":        getattr(patra, "age", None),
                "country":    getattr(request, "country", None) or chart_record.get("birth_country"),
                "city":       getattr(request, "city", None) or "",
                "profession": getattr(request, "profession", None) or "",
                "ventures":   getattr(request, "ventures", None) or [],
                "concern":    concern,
                "chart_data": chart_data,
                "language":   getattr(request, "language", "en"),
                "question":   request.question,
            },
            lk_context=lk_context or "",
        )
        print(f"[predict] plain_english ok — signal='{(_pe or {}).get('signal_line','')[:60]}'")
    except Exception as _pe_err:
        print(f"[predict] plain_english failed (non-fatal): {_pe_err}")
        _pe = None
    # ── end C1 ───────────────────────────────────────────────────

    confidence = predictions["highest_confidence"] or 0.75
    factors = [
        f"Layer 1: Dasha timing ({len(predictions['layer_1'])} signals)",
        f"Layer 2: Transit confluence ({len(predictions['layer_2'])} signals)",
        f"Layer 3: Yoga activation ({len(predictions['layer_3'])} signals)",
        f"Layer 4: Personal mirror ({len(predictions['layer_4'])} signals)",
        f"Concern: {concern}",
        f"Life stage: {patra.life_stage_name}",
        f"Country: {desh.period_quality if desh else 'N/A'}",
    ]

    # ── STORE PREDICTION — capture the DB id for conversation linking ──
    prediction_db_id = None
    try:
        pred_res = supabase.table("predictions").insert({
            "user_id":    user_id,
            "query":      request.question,
            "prompt":     prompt,
            "response": {
                "prediction": prediction_text,
                "confidence": confidence,
                "factors":    factors,
            },
            "confidence":  confidence,
            "factors":     factors,
            "created_at":  "now()",
            "tokens_used": tokens_used,
            "model":       "deepseek-chat",
            "chart_id":          request.chart_id,
            "concern":           concern,
            "question_mode":     _question_mode if '_question_mode' in dir() else None,
            "plain_summary":     _pe.get("plain_summary")   if _pe else None,
            "action_item":       _pe.get("action_item")     if _pe else None,
            "signal_line":       _pe.get("signal_line")     if _pe else None,
            "timing_window":     _pe.get("timing_window")   if _pe else None,
            "signal_confidence": _pe.get("confidence")      if _pe else None,
            "all_domains":       _pe.get("all_domains")     if _pe else [],
        }).execute()

        # ── Prediction tracking hook ──────────────────────────────
        try:
            from antar_engine.prediction_tracker import save_trackable_claim
            save_trackable_claim(
                chart_id=chart_id,
                prediction_id=str(pred_record.get("id", "")),
                prediction_text=prediction_response,
                concern=concern,
                sb=supabase,
            )
        except Exception:
            pass
        # ── End tracking hook ─────────────────────────────────────

        if pred_res.data:
            prediction_db_id = pred_res.data[0]["id"]
    except Exception as e:
        print(f"Prediction store error: {e}")

    # ── SAVE CONVERSATION TURN (auth users only) ──────────────────
    saved_conv_id = None
    saved_msg_id  = None
    if user_id:
        # Build the full response dict stored on the assistant message row.
        # The frontend reads this to rehydrate all three drawers when
        # the user reopens any past conversation — no re-fetch needed.
        full_response_for_db = {
            "prediction":        prediction_text,
            "confidence":        confidence,
            "factors":           factors,
            "remedies":          [r.dict() for r in remedies_out] if remedies_out else [],
            "chakra_reading":    chakra_reading_data,
            "chapter_arc":       chapter_arc_data,
            "rarity_signals":    rarity_signals,
            "precision_windows": [
                p.__dict__ if hasattr(p, "__dict__") else p
                for p in precision_windows
            ],
            "nation_insight":    desh.one_liner if desh else nation_insight,
            "life_stage":        patra.life_stage_name,
        }

        saved_conv_id, saved_msg_id = await save_conversation_turn(
            user_id=user_id,
            chart_id=request.chart_id,
            conversation_id=request.conversation_id,
            question=request.question,
            prediction_text=prediction_text,
            full_response=full_response_for_db,
            concern=concern,
            locale_variant=locale.variant or "US",
            confidence=confidence,
            prediction_db_id=prediction_db_id,
            history_snapshot=request.conversation_history or [],
        )

    # ── PASSIVE PATRA EXTRACTION ──────────────────────────────────
    patra_updates = extract_patra_from_text(request.question)

    if patra_updates and user_id:
        try:
            supabase.table("charts").update(patra_updates).eq(
                "id", request.chart_id
            ).execute()
            user_profile.update(patra_updates)
            patra = build_patra_context(
                birth_date=chart_record["birth_date"],
                user_profile=user_profile,
                primary_concern=concern,
            )
            patra_context = patra_to_context_block(patra)
        except Exception as e:
            print(f"Passive patra update error: {e}")

    # ── Normalize confidence to string ──
    if _pe and _pe.get("confidence"):
        _conf = _pe["confidence"]
        if isinstance(_conf, (int, float)):
            _pe["confidence"] = "high" if _conf >= 0.7 else ("medium" if _conf >= 0.4 else "low")

    # === RATING PROMPT — nudge user to rate old predictions ===
    _rating_prompt = None
    try:
        from datetime import datetime as _rp_dt, timedelta as _rp_td
        _7days_ago = (_rp_dt.utcnow() - _rp_td(days=7)).isoformat()
        _3days_ago = (_rp_dt.utcnow() - _rp_td(days=3)).isoformat()
        # Check if we should prompt (not prompted in last 3 days)
        _chart_meta = supabase.table("charts").select(
            "last_rating_prompt_at"
        ).eq("id", request.chart_id).single().execute()
        _last_prompt_at = (_chart_meta.data or {}).get("last_rating_prompt_at")
        _should_prompt = not _last_prompt_at or _last_prompt_at < _3days_ago
        if _should_prompt:
            # Find oldest unrated prediction older than 7 days
            _unrated = supabase.table("predictions").select(
                "id, signal_line, created_at"
            ).eq("chart_id", request.chart_id).is_(
                "accuracy_rating", "null"
            ).lt("created_at", _7days_ago).order(
                "created_at"
            ).limit(1).execute()
            if _unrated.data:
                _up = _unrated.data[0]
                _days_ago = (_rp_dt.utcnow() - _rp_dt.fromisoformat(
                    _up["created_at"].replace("Z", "").split("+")[0]
                )).days
                _rating_prompt = {
                    "prediction_id": _up["id"],
                    "signal_line": _up.get("signal_line", "")[:80],
                    "asked_date": _up["created_at"][:10],
                    "days_ago": _days_ago,
                    "question": f"You asked about this {_days_ago} days ago. Did it happen?",
                    "options": ["Yes, accurate", "Partially", "No, didn't happen", "Too early to tell"],
                }
                # Mark that we prompted
                supabase.table("charts").update(
                    {"last_rating_prompt_at": _rp_dt.utcnow().isoformat()}
                ).eq("id", request.chart_id).execute()
    except Exception as _rpe:
        print(f"[predict] Rating prompt generation failed (non-fatal): {_rpe}")
    # === END RATING PROMPT ===

    return PredictResponse(
        prediction=prediction_text,
        confidence=confidence,
        factors=factors,
        dashas=dashas_response,
        nation_insight=desh.one_liner if desh else nation_insight,
        remedies=remedies_out,
        locale_variant=locale.variant,
        needs_language_prompt=locale.needs_language_prompt,
        ui_strings=locale.ui,
        life_stage=patra.life_stage_name,
        country_period=desh.current_period if desh else None,
        country_period_quality=desh.period_quality if desh else None,
        patra_updates=patra_updates if patra_updates else None,
        rarity_signals=rarity_signals,
        precision_windows=precision_windows,
        chakra_reading=chakra_reading_data,
        chapter_arc=chapter_arc_data,
        conversation_id=saved_conv_id,
        message_id=saved_msg_id,
        plain_summary=(
            f"[{_char_archetype.get('name')}] " + _pe.get("plain_summary")
            if _pe and _pe.get("plain_summary") and _char_archetype and _char_archetype.get("name")
            else (_pe.get("plain_summary") if _pe else None)
        ),
        action_item=_pe.get("action_item") if _pe else None,
        signal_line=_pe.get("signal_line") if _pe else None,
        timing_window=_pe.get("timing_window") if _pe else None,
        all_domains=_pe.get("all_domains") if _pe else [],
        signal_confidence=_pe.get("confidence") if _pe else None,
        why_this=_pe.get("why_this") if _pe else None,
        bridge_practice_note=_pe.get("bridge_practice_note") if _pe else None,
        contradiction_detected=_contradiction_detected if '_contradiction_detected' in dir() else False,
        oracle_context=_oracle_context if '_oracle_context' in dir() else None,
        archetype_name=_char_archetype.get("name") if _char_archetype else None,
        rating_prompt=_rating_prompt,
    )

# ── Conversations ─────────────────────────────────────────────────────────────

@app.get("/api/v1/conversations")
async def list_conversations(
    limit:         int = 20,
    offset:        int = 0,
    authorization: str = Header(...),
):
    """
    Returns the user's conversation list ordered by most recent.
    Used to populate the chat sidebar.
    """
    user_id = verify_token(authorization)
    result = (
        supabase.table("conversations")
        .select("id, title, preview, message_count, last_message_at, concern, created_at")
        .eq("user_id", user_id)
        .eq("is_deleted", False)
        .order("last_message_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {"conversations": result.data or [], "total": len(result.data or [])}


@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    authorization:   str = Header(...),
):
    """
    Returns all messages for a conversation in sequence order.
    The full_response field on each assistant message rehydrates
    the drawers without making a new /predict call.
    """
    user_id = verify_token(authorization)

    # Verify ownership
    conv = (
        supabase.table("conversations")
        .select("id, user_id")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not conv.data:
        raise HTTPException(404, "Conversation not found")

    msgs = (
        supabase.table("messages")
        .select("id, role, sequence_number, content, full_response, confidence, concern, created_at")
        .eq("conversation_id", conversation_id)
        .order("sequence_number", desc=False)
        .execute()
    )
    return {"messages": msgs.data or [], "conversation_id": conversation_id}


@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    authorization:   str = Header(...),
):
    """
    Soft-deletes a conversation. Hidden from sidebar; messages retained in DB.
    """
    user_id = verify_token(authorization)
    supabase.table("conversations") \
        .update({"is_deleted": True}) \
        .eq("id", conversation_id) \
        .eq("user_id", user_id) \
        .execute()
    return {"status": "deleted", "conversation_id": conversation_id}

# ── Patra Onboarding Conversation ─────────────────────────────────────────────

@app.get("/api/v1/predict/patra-onboarding")
async def get_patra_onboarding(chart_id: str):
    """
    Returns chart-specific conversational questions for onboarding.
    """
    chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")

    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]
    dashas       = get_dashas_for_chart(chart_id)

    conversation = get_onboarding_conversation(chart_data, dashas)
    return {"conversation": conversation}

# ── Locale ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/locale/{country_code}")
async def get_locale(
    country_code: str,
    birth_country: Optional[str] = None,
):
    from antar_engine.i18n import detect_language
    locale = detect_language(
        residence_country=country_code,
        birth_country=birth_country,
        user_preference=None,
    )
    return {
        "language":              locale.language,
        "variant":               locale.variant,
        "needs_language_prompt": locale.needs_language_prompt,
        "language_name":         locale.language_name,
        "native_name":           locale.native_name,
        "ui_strings":            locale.ui,
    }

@app.post("/api/v1/user/set-language")
async def set_language(
    request: LanguageSetRequest,
    authorization: str = Header(...)
):
    user_id = verify_token(authorization)
    supabase.table("charts").update({
        "language_preference": request.language,
        "locale_variant": request.language,
    }).eq("user_id", user_id).execute()
    ui = get_ui_strings(request.language)
    return {"status": "ok", "language": request.language, "ui_strings": ui}

# ── Patra ─────────────────────────────────────────────────────────────────────

@app.get("/api/v1/user/patra/questions")
async def get_patra_questions():
    return {"questions": get_circumstance_questions()}

@app.post("/api/v1/user/patra")
async def update_patra(
    request: PatraUpdateRequest,
    authorization: str = Header(...)
):
    user_id = verify_token(authorization)
    update_data = {k: v for k, v in request.dict().items()
                   if k != "chart_id" and v is not None}
    update_data["patra_complete"] = True
    result = supabase.table("charts").update(update_data) \
        .eq("id", request.chart_id).eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "Chart not found")
    patra = build_patra_context(
        birth_date=result.data[0]["birth_date"],
        user_profile=update_data,
        primary_concern="general",
    )
    return {
        "status":          "updated",
        "life_stage":      patra.life_stage_name,
        "life_stage_desc": patra.life_stage_description,
        "age":             patra.age,
        "age_trigger":     patra.age_trigger,
    }

# ── Monthly Briefing ──────────────────────────────────────────────────────────

@app.post("/api/v1/predict/monthly-briefing", response_model=MonthlyBriefingResponse)
async def monthly_briefing(
    request: MonthlyBriefingRequest,
    authorization: Optional[str] = Header(None)
):
    user_id = None
    if authorization:
        try:
            user_id = verify_token(authorization)
        except HTTPException:
            pass

    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")
    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]

    dashas_response  = get_dashas_for_chart(request.chart_id)
    _raw_transits = transits.calculate_transits(chart_data, target_date=None, ayanamsa_mode=1)
    current_transits = (
        {t["planet"]: t for t in _raw_transits if "planet" in t}
        if isinstance(_raw_transits, list) else _raw_transits
    )

    life_events = []
    if user_id:
        ev = supabase.table("life_events").select("event_date, event_type, description") \
            .eq("user_id", user_id).order("event_date", desc=True).limit(3).execute()
        life_events = ev.data

    locale     = get_locale_from_request(
        country_code=chart_record.get("country_code"),
        birth_country=chart_record.get("birth_country"),
        user_language_preference=chart_record.get("language_preference"),
    )
    concern    = request.concern or "general"
    month_year = request.month_year or datetime.utcnow().strftime("%B %Y")

    predictions = build_layered_predictions(
        user_id=user_id,
        chart_data=chart_data,
        dashas=dashas_response,
        current_transits=current_transits,
        life_events=life_events,
        supabase=supabase,
        concern=concern,
    )
    predictions_context = predictions_to_context_block(predictions, chart_data, concern)

    prompt = build_monthly_briefing_prompt(
        chart_data=chart_data,
        dashas=dashas_response,
        current_transits=current_transits,
        predictions_context=predictions_context,
        month_year=month_year,
        concern=concern,
        country_code=chart_record.get("country_code", "US"),
    )
    briefing_text, _ = await call_llm(prompt)

    if user_id:
        try:
            supabase.table("monthly_briefings").insert({
                "user_id":    user_id,
                "chart_id":   request.chart_id,
                "month_year": month_year,
                "briefing":   briefing_text,
                "concern":    concern,
                "created_at": "now()",
            }).execute()
        except Exception as e:
            print(f"Briefing store error: {e}")

    return MonthlyBriefingResponse(
        briefing=briefing_text,
        month_year=month_year,
        predictions_count=predictions["total_signals"],
        concern=concern,
    )

# ── Daily Practice ────────────────────────────────────────────────────────────

@app.post("/api/v1/predict/daily-practice", response_model=DailyPracticeResponse)
async def daily_practice(
    request: DailyPracticeRequest,
    authorization: Optional[str] = Header(None)
):
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")
    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]
    dashas       = get_dashas_for_chart(request.chart_id)

    today = datetime.utcnow().strftime("%A, %B %d %Y")
    prompt = build_daily_practice_prompt(
        chart_data=chart_data,
        dashas=dashas,
        date=today,
        country_code=chart_record.get("country_code", "US"),
    )
    practice_text, _ = await call_llm(prompt)
    return DailyPracticeResponse(practice=practice_text, date=today)

# ── Prediction Fulfillment ────────────────────────────────────────────────────

@app.post("/api/v1/predict/fulfill")
async def fulfill_prediction(
    update: PredictionFulfillmentUpdate,
    authorization: str = Header(...)
):
    user_id = verify_token(authorization)
    result = supabase.table("user_predictions").update({
        "fulfilled":      update.fulfilled,
        "fulfilled_date": datetime.utcnow().isoformat() if update.fulfilled else None,
        "notes":          update.notes,
    }).eq("id", update.prediction_id).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(404, "Prediction not found")

    try:
        supabase.table("user_actions").insert({
            "user_id":     user_id,
            "action_type": "prediction_fulfilled" if update.fulfilled else "prediction_not_fulfilled",
            "action_data": {"prediction_id": update.prediction_id},
            "timestamp":   "now()",
        }).execute()
    except Exception as e:
        print(f"Action log error: {e}")

    return {
        "status":    "updated",
        "fulfilled": update.fulfilled,
        "message":   "Your chart noted this. The pattern grows clearer." if update.fulfilled
                     else "Noted. Not every signal manifests the same way.",
    }

# ── Life Events ───────────────────────────────────────────────────────────────

@app.get("/api/v1/user/profile")
async def get_user_profile(request: Request):
    """User profile — called by frontend Profile page. Returns language + chart basics."""
    try:
        chart_id = request.query_params.get("chart_id")
        if not chart_id:
            return {"language": "en", "career_stage": None, "relationship_stage": None}
        result = supabase.table("charts").select(
            "id, first_name, name, display_name, email, birth_date, "
            "birth_city, birth_country, current_city, current_country, "
            "lagna_sign, moon_sign, sun_sign, language, gender, "
            "marital_status, children_status, career_stage, lagna"
        ).eq("id", chart_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart = result.data
        return {
            "chart_id": chart_id,
            "id": chart.get("id", chart_id),
            "first_name": chart.get("first_name") or chart.get("name", ""),
            "name": chart.get("name", ""),
            "display_name": chart.get("display_name", ""),
            "email": chart.get("email", ""),
            "birth_date": str(chart.get("birth_date", "") or "")[:10],
            "birth_city": chart.get("birth_city", ""),
            "birth_country": chart.get("birth_country", ""),
            "current_city": chart.get("current_city", ""),
            "current_country": chart.get("current_country", ""),
            "lagna_sign": chart.get("lagna_sign", ""),
            "lagna": chart.get("lagna", ""),
            "moon_sign": chart.get("moon_sign", ""),
            "sun_sign": chart.get("sun_sign", ""),
            "language": chart.get("language") or "en",
            "gender": chart.get("gender", ""),
            "marital_status": chart.get("marital_status", ""),
            "children_status": chart.get("children_status", ""),
            "career_stage": chart.get("career_stage"),
            "relationship_stage": None,
            "remedy_style": "secular",
        }
    except Exception as e:
        print(f"[user/profile] {e}")
        return {"language": "en", "career_stage": None, "relationship_stage": None}

@app.post("/api/v1/user/life-events", response_model=LifeEventOut, status_code=201)
async def create_life_event(event: LifeEventCreate, authorization: str = Header(...)):
    user_id = verify_token(authorization)
    data = event.dict()
    data["user_id"] = user_id
    result = supabase.table("life_events").insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create life event")
    # Merge panchanga into result
    if panchanga and not panchanga.get("error"):
        result["panchanga"] = panchanga_formatted
        result["rahu_kalam"]     = panchanga.get("rahu_kalam","")
        result["abhijit"]        = panchanga.get("abhijit_muhurta","")
        result["lucky_hours"]    = panchanga.get("lucky_hours",{})
        result["do_today"]       = panchanga.get("do_today",[])
        result["dont_today"]     = panchanga.get("dont_today",[])
        result["day_color"]      = panchanga.get("day_color","")
        result["day_number"]     = panchanga.get("day_number","")
        result["day_mantra"]     = panchanga.get("day_mantra","")
        result["tithi"]          = panchanga.get("tithi","")
        result["yoga"]           = panchanga.get("yoga","")
        result["day_quality"]    = panchanga.get("day_quality","")
        result["panchanga_5"]    = panchanga_formatted.get("panchanga_5",{})

    return result.data[0]

@app.get("/api/v1/user/life-events", response_model=List[LifeEventOut])
async def get_life_events(
    authorization: str = Header(...),
    limit: int = 50,
    offset: int = 0
):
    user_id = verify_token(authorization)
    result = supabase.table("life_events").select("*") \
        .eq("user_id", user_id) \
        .order("event_date", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()
    return result.data

@app.get("/api/v1/user/life-events/{event_id}", response_model=LifeEventOut)
async def get_life_event(event_id: str, authorization: str = Header(...)):
    user_id = verify_token(authorization)
    result = supabase.table("life_events").select("*") \
        .eq("id", event_id).eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "Life event not found")
    return result.data[0]

@app.put("/api/v1/user/life-events/{event_id}", response_model=LifeEventOut)
async def update_life_event(
    event_id: str,
    event: LifeEventUpdate,
    authorization: str = Header(...)
):
    user_id = verify_token(authorization)
    update_data = {k: v for k, v in event.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(400, "No fields to update")
    result = supabase.table("life_events").update(update_data) \
        .eq("id", event_id).eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "Life event not found")
    return result.data[0]

@app.delete("/api/v1/user/life-events/{event_id}")
async def delete_life_event(event_id: str, authorization: str = Header(...)):
    user_id = verify_token(authorization)
    result = supabase.table("life_events").delete() \
        .eq("id", event_id).eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "Life event not found")
    return {"status": "deleted", "id": event_id}

# ── Correlations ──────────────────────────────────────────────────────────────

@app.get("/api/v1/user/correlations", response_model=LifeEventCorrelationResponse)
async def get_correlations(
    chart_id: str,
    authorization: str = Header(...)
):
    user_id = verify_token(authorization)

    events_resp = supabase.table("life_events").select("*") \
        .eq("user_id", user_id).order("event_date").execute()
    life_events = events_resp.data or []

    if len(life_events) < 3:
        return LifeEventCorrelationResponse(
            correlations=[],
            total_events=len(life_events),
            patterns_found=0,
            message=f"Log {3 - len(life_events)} more life events to unlock your personal pattern analysis.",
        )

    corr_resp = supabase.table("user_correlations").select("*") \
        .eq("user_id", user_id).order("confidence_score", desc=True).execute()
    correlations = corr_resp.data or []

    if not correlations:
        from antar_engine.predictions import _build_correlations
        dashas = get_dashas_for_chart(chart_id)
        all_dashas = (
            dashas.get("vimsottari", []) +
            dashas.get("jaimini", []) +
            dashas.get("ashtottari", [])
        )
        correlations = _build_correlations(user_id, life_events, all_dashas, supabase)

    formatted = [{
        "event_type":      c["event_type"],
        "pattern":         c["pattern"],
        "occurrences":     c["occurrences"],
        "confidence":      int(c["confidence_score"] * 100),
        "examples":        c.get("examples", []),
        "display_message": (
            f"Every time {c['pattern']}, something significant happens "
            f"in your {c['event_type']} life. "
            f"We've seen this {c['occurrences']} times in your history."
        ),
    } for c in correlations]

    return LifeEventCorrelationResponse(
        correlations=formatted,
        total_events=len(life_events),
        patterns_found=len(formatted),
        message=(
            f"We found {len(formatted)} personal patterns in your life story."
            if formatted else "Keep logging events — your patterns are building."
        ),
    )

# ── User Actions ──────────────────────────────────────────────────────────────

@app.post("/api/v1/user/action")
async def log_user_action(
    action: UserActionCreate,
    authorization: Optional[str] = Header(None)
):
    user_id = None
    if authorization:
        try:
            user_id = verify_token(authorization)
        except HTTPException:
            pass

    supabase.table("user_actions").insert({
        "user_id":     user_id,
        "action_type": action.action_type,
        "action_data": action.action_data,
        "page_url":    action.page_url,
        "timestamp":   "now()"
    }).execute()
    return {"status": "ok"}

# ── Merge Guest ───────────────────────────────────────────────────────────────

@app.post("/api/v1/user/merge-guest-data")
async def merge_guest_data(
    request: MergeGuestRequest,
    authorization: str = Header(...)
):
    user_id = verify_token(authorization)
    guest_resp = supabase.table("guest_sessions").select("*") \
        .eq("id", request.guest_session_id).execute()
    if not guest_resp.data:
        raise HTTPException(404, "Guest session not found")
    supabase.table("charts").update({"user_id": user_id, "guest_session_id": None}) \
        .eq("guest_session_id", request.guest_session_id).execute()
    supabase.table("predictions").update({"user_id": user_id, "guest_session_id": None}) \
        .eq("guest_session_id", request.guest_session_id).execute()
    supabase.table("guest_sessions").delete() \
        .eq("id", request.guest_session_id).execute()
    return {"status": "success"}

# ── Private helpers ───────────────────────────────────────────────────────────

def _build_remedies(remedy_objects: list) -> List[RemedyOut]:
    remedies_out = []
    for rem in remedy_objects:
        if "planet" in rem:
            remedies_out.append(RemedyOut(
                planet=rem["planet"],
                mantra=rem.get("mantra", rem.get("mantra_simple", "")),
                beej_mantra=rem.get("full_mantra", rem.get("mantra_beej", "")),
                recommended_day=rem.get("best_day", rem.get("fasting_day", rem.get("fasting", ""))),
                count=rem.get("count", 108),
                purpose=rem.get("purpose", rem.get("special_instructions", "")),
                chakra=rem.get("chakra", {}).get("chakra_name", "") if isinstance(rem.get("chakra"), dict) else "",
                chakra_color=rem.get("chakra", {}).get("color", ""),
                chakra_beej=rem.get("chakra", {}).get("bija_mantra", ""),
                chakra_location=rem.get("chakra", {}).get("location", ""),
                chakra_element=rem.get("chakra", {}).get("element", ""),
                chakra_meditation=rem.get("chakra", {}).get("visualization", "")
            ))
        elif rem.get("type") == "chakra" and "chakra" in rem:
            remedies_out.append(RemedyOut(
                planet="General",
                mantra=rem["chakra"].get("bija_mantra", ""),
                beej_mantra="",
                recommended_day="",
                count=0,
                purpose="Chakra balancing",
                chakra=rem["chakra"].get("chakra_name", ""),
                chakra_color=rem["chakra"].get("color", ""),
                chakra_beej=rem["chakra"].get("bija_mantra", ""),
                chakra_location=rem["chakra"].get("location", ""),
                chakra_element=rem["chakra"].get("element", ""),
                chakra_meditation=rem["chakra"].get("visualization", "")
            ))
    return remedies_out


# ══════════════════════════════════════════════════════════════════════════════
# CHART CREATE ENDPOINT — POST /api/v1/chart/create
# ══════════════════════════════════════════════════════════════════════════════

# ChartCreateRequest defined above

class ChartCreateResponse(BaseModel):
    chart_id:       str
    lagna:          str
    lagna_degree:   float
    moon_sign:      str
    sun_sign:       str
    atmakaraka:     str
    amatyakaraka:   str
    current_dasha:  str
    dasha_count:    int
    birth_city:     str
    birth_lat:      float
    birth_lng:      float
    timezone:       str
    message:        str
    signup_intent:  Optional[Dict[str, Any]] = None

CITY_COORDS_LOOKUP = {
    "mumbai":(19.0760,72.8777,"Asia/Kolkata"),
    "delhi":(28.6139,77.2090,"Asia/Kolkata"),
    "new delhi":(28.6139,77.2090,"Asia/Kolkata"),
    "bangalore":(12.9716,77.5946,"Asia/Kolkata"),
    "bengaluru":(12.9716,77.5946,"Asia/Kolkata"),
    "chennai":(13.0827,80.2707,"Asia/Kolkata"),
    "kolkata":(22.5726,88.3639,"Asia/Kolkata"),
    "hyderabad":(17.3850,78.4867,"Asia/Kolkata"),
    "pune":(18.5204,73.8567,"Asia/Kolkata"),
    "new york":(40.7128,-74.0060,"America/New_York"),
    "los angeles":(34.0522,-118.2437,"America/Los_Angeles"),
    "chicago":(41.8781,-87.6298,"America/Chicago"),
    "london":(51.5074,-0.1278,"Europe/London"),
    "dubai":(25.2048,55.2708,"Asia/Dubai"),
    "singapore":(1.3521,103.8198,"Asia/Singapore"),
    "toronto":(43.6532,-79.3832,"America/Toronto"),
    "sydney":(-33.8688,151.2093,"Australia/Sydney"),
    "berlin":(52.5200,13.4050,"Europe/Berlin"),
    "paris":(48.8566,2.3522,"Europe/Paris"),
    "sao paulo":(-23.5505,-46.6333,"America/Sao_Paulo"),
    "mexico city":(19.4326,-99.1332,"America/Mexico_City"),
    "tokyo":(35.6762,139.6503,"Asia/Tokyo"),
    "kuwait city":(29.3697,47.9783,"Asia/Kuwait"),
    "kuwait":(29.3697,47.9783,"Asia/Kuwait"),
    "riyadh":(24.7136,46.6753,"Asia/Riyadh"),
    "dubai":(25.2048,55.2708,"Asia/Dubai"),
    "abu dhabi":(24.4539,54.3773,"Asia/Dubai"),
    "doha":(25.2854,51.5310,"Asia/Qatar"),
    "muscat":(23.5880,58.3829,"Asia/Muscat"),
    "karachi":(24.8607,67.0011,"Asia/Karachi"),
    "lahore":(31.5204,74.3587,"Asia/Karachi"),
    "dhaka":(23.8103,90.4125,"Asia/Dhaka"),
    "colombo":(6.9271,79.8612,"Asia/Colombo"),
    "kathmandu":(27.7172,85.3240,"Asia/Kathmandu"),
    "nairobi":(-1.2921,36.8219,"Africa/Nairobi"),
    "johannesburg":(-26.2041,28.0473,"Africa/Johannesburg"),
    "lagos":(6.5244,3.3792,"Africa/Lagos"),
    "cairo":(30.0444,31.2357,"Africa/Cairo"),
    "amsterdam":(52.3676,4.9041,"Europe/Amsterdam"),
    "stockholm":(59.3293,18.0686,"Europe/Stockholm"),
    "zurich":(47.3769,8.5417,"Europe/Zurich"),
    "moscow":(55.7558,37.6173,"Europe/Moscow"),
    "istanbul":(41.0082,28.9784,"Europe/Istanbul"),
    "bangkok":(13.7563,100.5018,"Asia/Bangkok"),
    "jakarta":(-6.2088,106.8456,"Asia/Jakarta"),
    "manila":(14.5995,120.9842,"Asia/Manila"),
    "kuala lumpur":(3.1390,101.6869,"Asia/Kuala_Lumpur"),
    "hong kong":(22.3193,114.1694,"Asia/Hong_Kong"),
    "seoul":(37.5665,126.9780,"Asia/Seoul"),
    "auckland":(-36.8485,174.7633,"Pacific/Auckland"),
    "vancouver":(49.2827,-123.1207,"America/Vancouver"),
    "montreal":(45.5017,-73.5673,"America/Montreal"),
    "miami":(25.7617,-80.1918,"America/New_York"),
    "houston":(29.7604,-95.3698,"America/Chicago"),
    "dallas":(32.7767,-96.7970,"America/Chicago"),
    "seattle":(47.6062,-122.3321,"America/Los_Angeles"),
    "san francisco":(37.7749,-122.4194,"America/Los_Angeles"),
    "bogota":(4.7110,-74.0721,"America/Bogota"),
    "lima":(-12.0464,-77.0428,"America/Lima"),
    "santiago":(-33.4489,-70.6693,"America/Santiago"),
    "buenos aires":(-34.6037,-58.3816,"America/Argentina/Buenos_Aires"),
    "cairo":(30.0444,31.2357,"Africa/Cairo"),
}
COUNTRY_CAPITALS = {
    "IN":(20.5937,78.9629,"Asia/Kolkata"),
    "US":(39.7392,-104.9903,"America/New_York"),
    "GB":(51.5074,-0.1278,"Europe/London"),
    "AU":(-33.8688,151.2093,"Australia/Sydney"),
    "CA":(43.6532,-79.3832,"America/Toronto"),
    "AE":(25.2048,55.2708,"Asia/Dubai"),
    "SG":(1.3521,103.8198,"Asia/Singapore"),
    "DE":(52.5200,13.4050,"Europe/Berlin"),
    "FR":(48.8566,2.3522,"Europe/Paris"),
    "BR":(-23.5505,-46.6333,"America/Sao_Paulo"),
    "MX":(19.4326,-99.1332,"America/Mexico_City"),
}

async def _geocode_city(city: str, country: str) -> tuple:
    city_lower = city.lower().strip()
    if city_lower in CITY_COORDS_LOOKUP:
        return CITY_COORDS_LOOKUP[city_lower]
    for key, coords in CITY_COORDS_LOOKUP.items():
        if key in city_lower or city_lower in key:
            return coords
    google_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if google_key:
        try:
            import httpx, time
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={"address": f"{city}, {country}", "key": google_key}, timeout=5.0,
                )
                data = r.json()
                if data.get("results"):
                    loc = data["results"][0]["geometry"]["location"]
                    lat, lng = loc["lat"], loc["lng"]
                    tz_r = await client.get(
                        "https://maps.googleapis.com/maps/api/timezone/json",
                        params={"location":f"{lat},{lng}","timestamp":int(time.time()),"key":google_key}, timeout=5.0,
                    )
                    tz = tz_r.json().get("timeZoneId","UTC")
                    return lat, lng, tz
        except Exception as ge:
            print(f"Geocode error: {ge}")
    if country.upper() in COUNTRY_CAPITALS:
        return COUNTRY_CAPITALS[country.upper()]
    raise HTTPException(400, f"Could not geocode '{city}'. Please provide birth_lat and birth_lng.")

def _ak_amk(planets: dict):
    degs = [(p, d.get("degree",0)) for p,d in planets.items() if p not in ("Rahu","Ketu")]
    degs.sort(key=lambda x:x[1], reverse=True)
    ak  = degs[0][0] if degs else "Sun"
    amk = degs[1][0] if len(degs)>1 else "Jupiter"
    return ak, amk

def _current_dasha_str(dashas: dict) -> str:
    """Return current Mahadasha-Antardasha e.g. Mars-Moon"""
    now = datetime.utcnow()
    vim = dashas.get("vimsottari", [])
    current_maha = None
    current_antar = None
    for row in vim:
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign", "")
        level = row.get("level") or row.get("type", "mahadasha")
        start_str = row.get("start_date") or row.get("start", "")
        end_str   = row.get("end_date")   or row.get("end", "")
        if not start_str or not end_str:
            continue
        try:
            s = datetime.strptime(str(start_str)[:10], "%Y-%m-%d")
            e = datetime.strptime(str(end_str)[:10],   "%Y-%m-%d")
            if s <= now <= e:
                if level == "mahadasha":
                    current_maha = lord
                elif level in ("antardasha", "antar"):
                    current_antar = lord
        except Exception:
            continue
    if current_maha and current_antar:
        return f"{current_maha}-{current_antar}"
    if current_maha:
        return current_maha
    for row in vim:
        if (row.get("level") or row.get("type", "")) == "mahadasha":
            return row.get("lord_or_sign") or row.get("planet_or_sign", "Unknown")
    return "Unknown"


def _get_utc_offset_from_coords(lat: float, lng: float, birth_date: str, birth_time: str) -> float:
    """Derive correct UTC offset from birth lat/lng + birth datetime (DST-aware)."""
    try:
        import pytz
        from datetime import datetime as _dt
        tz_name = _TZF.timezone_at(lat=lat, lng=lng)
        if not tz_name:
            return 0.0
        tz = pytz.timezone(tz_name)
        dt_naive = _dt.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
        dt_local = tz.localize(dt_naive, is_dst=None)
        return dt_local.utcoffset().total_seconds() / 3600
    except Exception as e:
        print(f"[TZ] Could not resolve offset from coords: {e}")
        return 0.0

@app.post("/api/v1/chart/create")
async def create_chart(
    request: ChartCreateRequest,
    authorization: Optional[str] = Header(None),
):
    from antar_engine import chart as chart_module
    from antar_engine import vimsottari, jaimini, ashtottari

    user_id = None
    if authorization:
        try:
            user_id = verify_token(authorization)
        except HTTPException:
            pass

    if request.latitude and request.longitude:
        lat, lng = request.latitude, request.longitude
        timezone = getattr(request, "timezone_name", None) or getattr(request, "timezone", None) or "UTC"
    else:
        lat, lng, timezone = await _geocode_city(request.birth_place, request.birth_country)

    # ── TZ FIX: resolve UTC offset from the birth datetime, not utcnow() ─────
    # _tz_name_to_offset() in chart.py used datetime.utcnow() which gives the
    # *current* DST rule, not the historical rule at birth.  For example:
    #   • Venezuela 2007-2016 was UTC-4:30; using utcnow() gives -4 → wrong lagna
    #   • Any DST timezone: winter birth looked up in summer → 1-hour shift
    # pytz.localize(birth_datetime, is_dst=None) applies the correct historical rule.
    try:
        import pytz as _pytz_cr
        _tz_cr = _pytz_cr.timezone(timezone)
        _dt_naive_cr = datetime.strptime(
            f"{request.birth_date} {request.birth_time}", "%Y-%m-%d %H:%M"
        )
        _dt_local_cr = _tz_cr.localize(_dt_naive_cr, is_dst=None)
        _chart_tz_offset = _dt_local_cr.utcoffset().total_seconds() / 3600
    except Exception as _tz_err:
        # Fallback: use client-supplied timezone_offset
        _chart_tz_offset = float(getattr(request, "timezone_offset", 0.0) or 0.0)
        print(f"[TZ] pytz localize failed ({_tz_err}); falling back to request.timezone_offset={_chart_tz_offset}")
    # ── end TZ FIX ────────────────────────────────────────────────────────────

    try:
        chart_data = chart_module.calculate_chart(
            birth_date=request.birth_date,
            birth_time=request.birth_time,
            lat=lat, lng=lng,
            tz_offset=_chart_tz_offset,
            ayanamsa="lahiri",
        )
    except Exception as e:
        raise HTTPException(500, f"Chart calculation failed: {e}")

    def _normalise_dashas(raw) -> list:
        """
        Dasha modules return {mahadashas:[{lord, start_date, end_date, ...}], antardashas:[...]}
        OR a flat list (Jaimini). Normalise to flat list with keys:
        {lord_or_sign, start, end, duration_years, level, planet_or_sign}
        """
        if isinstance(raw, list):
            # Jaimini returns flat list with "sign" key — normalize keys
            normalized = []
            for item in raw:
                if isinstance(item, dict):
                    _lord_v = item.get("lord_or_sign", "") or item.get("lord", "") or item.get("sign", "") or item.get("planet_or_sign", "")
                    _sd = str(item.get("start_date", "") or item.get("start", ""))[:10]
                    _ed = str(item.get("end_date", "") or item.get("end", ""))[:10]
                    normalized.append({
                        "lord_or_sign":   _lord_v,
                        "planet_or_sign": _lord_v,
                        "start":          _sd,
                        "end":            _ed,
                        "start_date":     _sd,
                        "end_date":       _ed,
                        "duration_years": item.get("duration_years", 0),
                        "level":          item.get("level", "mahadasha"),
                        "parent_lord":    item.get("parent_lord", ""),
                    })
                else:
                    normalized.append(item)
            return normalized
        if not isinstance(raw, dict):
            return []
        flat = []
        for p in raw.get("mahadashas", []):
            sd = str(p.get("start_date", "") or "")[:10]
            ed = str(p.get("end_date",   "") or "")[:10]
            _lord_val = p.get("lord", "") or p.get("sign", "") or p.get("lord_or_sign", "")
            flat.append({
                "lord_or_sign":   _lord_val,
                "planet_or_sign": _lord_val,
                "start":          sd,
                "end":            ed,
                "start_date":     sd,
                "end_date":       ed,
                "duration_years": p.get("duration_years", 0),
                "level":          "mahadasha",
            })
        for p in raw.get("antardashas", []):
            sd = str(p.get("start_date", "") or "")[:10]
            ed = str(p.get("end_date",   "") or "")[:10]
            _lord_val_ad = p.get("lord", "") or p.get("sign", "") or p.get("lord_or_sign", "")
            flat.append({
                "lord_or_sign":   _lord_val_ad,
                "planet_or_sign": _lord_val_ad,
                "start":          sd,
                "end":            ed,
                "start_date":     sd,
                "end_date":       ed,
                "duration_years": p.get("duration_years", 0),
                "level":          "antardasha",
                "parent_lord":    p.get("parent_lord", ""),
            })
        return flat

    vim_dashas, jai_dashas, ash_dashas = [], [], []
    try: vim_dashas = _normalise_dashas(
            vimsottari.calculate_vimsottari_from_chart(chart_data, chart_data.get("birth_jd")))
    except Exception as e: print(f"Vimsottari error: {e}")
    try:
        from antar_engine.jaimini import build_planet_map
        import datetime as _dt
        _lagna     = chart_data.get("lagna", {})
        _lagna_sign = _lagna.get("sign","Aries") if isinstance(_lagna, dict) else "Aries"
        SIGNS_LIST = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                      "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
        _lagna_idx  = SIGNS_LIST.index(_lagna_sign) if _lagna_sign in SIGNS_LIST else 0
        _planet_longs = {
            p: (SIGNS_LIST.index(d.get("sign","Aries")) * 30 + d.get("degree", 0))
            for p, d in chart_data.get("planets", {}).items()
            if d.get("sign","") in SIGNS_LIST
        }
        _planet_sign_map = build_planet_map(_planet_longs)
        _bdate = _dt.date.fromisoformat(request.birth_date[:10])
        jai_dashas = _normalise_dashas(
            jaimini.compute_jaimini_dashas(_lagna_idx, _planet_sign_map, _bdate)
        )
    except Exception as e: print(f"Jaimini error: {e}")
    try: ash_dashas = _normalise_dashas(
            ashtottari.calculate_ashtottari_from_chart(chart_data, chart_data.get("birth_jd")))
    except Exception as e: print(f"Ashtottari error: {e}")

    dashas_combined = {"vimsottari": vim_dashas, "jaimini": jai_dashas, "ashtottari": ash_dashas}

    chart_id = str(uuid.uuid4())
    # Calculate timezone offset in hours from timezone string
    # CRITICAL: use birth_date not today — historical offsets differ (e.g. Venezuela was UTC-4.5 until 2016)
    try:
        import pytz
        from datetime import datetime as _dt
        _tz = pytz.timezone(timezone)
        # Use birth datetime for historical accuracy
        _birth_dt = _dt.strptime(str(request.birth_date)[:10], "%Y-%m-%d")
        _offset = _tz.utcoffset(_birth_dt).total_seconds() / 3600
    except Exception:
        # Fall back to user-provided offset if available
        _offset = float(getattr(request, "timezone_offset", 0.0) or 0.0)



    chart_row = {
        "id":                  chart_id,
        "user_id":             user_id,
        "first_name":          getattr(request, "first_name", None) or getattr(request, "name", None) or "",
        "birth_date":          request.birth_date,
        "birth_time":          request.birth_time,
        "latitude":            lat,
        "longitude":           lng,
        "gender":          getattr(request, "gender", "") or "",
        "current_city":    getattr(request, "current_city", "") or "",
        "current_country": getattr(request, "current_country", "") or "",
        "timezone_offset":     _offset,
        "country_code":        request.birth_country,
        "birth_city":      getattr(request, "birth_city", "") or request.birth_place or "",
        "birth_country":   request.birth_country or "",
        "name":            getattr(request, "name", None) or getattr(request, "first_name", None) or "",
        "display_name":    (getattr(request, "first_name", None) or getattr(request, "name", None) or "").split()[0] if (getattr(request, "first_name", None) or getattr(request, "name", None)) else "",
        "lagna_sign":      chart_data.get("lagna", {}).get("sign", ""),
        "moon_sign":       chart_data.get("planets", {}).get("Moon", {}).get("sign", ""),
        "moon_nakshatra":  chart_data.get("planets", {}).get("Moon", {}).get("nakshatra", ""),
        "sun_sign":        chart_data.get("planets", {}).get("Sun", {}).get("sign", ""),
        "chart_data":          {
            **chart_data,
            "divisional_charts": chart_data.get("divisional_charts", {}),
            "yogas":             chart_data.get("yogas", []),
            "house_lords":       chart_data.get("house_lords", {}),
            "atmakaraka":        chart_data.get("atmakaraka", ""),
        },
        "language_preference": _lang_from_country(request.birth_country),
        "patra_complete":      False,
    }
    try:
        supabase.table("charts").insert(chart_row).execute()

        # --- Jaimini v2: Compute and store Chara Dasha ---
        _jaimini_bd = str(request.birth_date)[:10] if request.birth_date else ""
        if "_lagna_sign" not in dir():
            _lagna_sign = chart_data.get("lagna", {}).get("sign", "Aries") if isinstance(chart_data.get("lagna"), dict) else "Aries"
        if not _jaimini_bd:
            print(f"[jaimini] Skipping v2 store — no birth_date for chart {chart_id}")
        else:
            try:
                _lagna_idx_j = constants.SIGNS.index(_lagna_sign) if isinstance(_lagna_sign, str) else int(_lagna_sign)
                _planets_for_jaimini = {}
                for pname, pdata in chart_data.get("planets", {}).items():
                    if isinstance(pdata, dict):
                        _planets_for_jaimini[pname] = pdata
                _d9_data = (chart_data.get("divisional_charts", {}).get("d9") or chart_data.get("divisional_charts", {}).get("D9") or {}).get("planets", {})
                if not _d9_data:
                    _d9_data = chart_data.get("d9_planets", {})
                from antar_engine.jaimini_engine import (
                    calculate_jaimini_analysis,
                    jaimini_to_db_json,
                )
                _lagna_obj2 = chart_data.get("lagna", {})
                _lagna_sign2 = _sign_name_to_idx(_lagna_obj2.get("sign_num", _lagna_obj2.get("sign_index", _lagna_obj2.get("sign", 0)))) if isinstance(_lagna_obj2, dict) else 0
                _d9_data2 = (chart_data.get("divisional_charts", {}).get("d9") or chart_data.get("divisional_charts", {}).get("D9") or {}).get("planets", {})
                if not _d9_data2:
                    _d9_data2 = chart_data.get("d9_planets", {})
                _jaimini_result = calculate_jaimini_analysis(
                    lagna_sign=_lagna_sign2,
                    planets_dict=_planets_for_jaimini,
                    d9_planets_dict=_d9_data2 or {},
                    birth_date_str=_jaimini_bd,
                )
                _jaimini_db = _jaimini_result["db_json"]
                _jaimini_db.pop("computed_at", None)
                supabase.table("charts").update({
                    "jaimini_data": _jaimini_db
                }).eq("id", chart_id).execute()
                print(f"[jaimini] Stored for chart {chart_id}")
            except Exception as _je:
                print(f"[jaimini] v2 store failed (non-blocking): {_je}")

        # Backfill advanced LK data (sleeping planets + Rin)
        try:
            from antar_engine.lal_kitab_advanced import detect_sleeping_planets, calculate_comprehensive_rin
            _lk_stored = supabase.table("charts").select("lal_kitab_data").eq("id", chart_id).single().execute()
            _lk_data = _lk_stored.data.get("lal_kitab_data") or {}
            if isinstance(_lk_data, str):
                import json as _lkjson
                _lk_data = _lkjson.loads(_lk_data)

            # Compute advanced fields
            _planets_for_lk = chart_data.get("planets", {})
            _sleeping = detect_sleeping_planets(_planets_for_lk)
            _rin = calculate_comprehensive_rin(_planets_for_lk)

            # Store under 'advanced' key
            _lk_data["advanced"] = {
                "sleeping_planets": _sleeping,
                "rin_debts": _rin,
            }
            supabase.table("charts").update({"lal_kitab_data": _lk_data}).eq("id", chart_id).execute()
            print(f"[chart/create] LK advanced stored — {len(_sleeping)} sleeping, {len(_rin)} rin")
        except Exception as _lke:
            print(f"[chart/create] LK advanced store failed (non-blocking): {_lke}")

        # Save yogas to separate table for queryability
        detected_yogas = chart_data.get("yogas", [])
        if detected_yogas:
            yoga_rows = [
                {
                    "chart_id":  chart_id,
                    "yoga_name": y.get("name",""),
                    "strength":  y.get("strength",""),
                    "category":  y.get("category",""),
                    "planets":   y.get("planets",[]),
                    "effect":    y.get("effect",""),
                }
                for y in detected_yogas
            ]
            try:
                supabase.table("chart_yogas").insert(yoga_rows).execute()
                print(f"[yogas] Saved {len(yoga_rows)} yogas for chart {chart_id}")
            except Exception as _ye:
                print(f"[yogas] Save error (non-fatal): {_ye}")
    except Exception as e:
        raise HTTPException(500, f"Failed to save chart: {e}")

    dasha_rows = []
    for system, periods in [("vimsottari",vim_dashas),("jaimini",jai_dashas),("ashtottari",ash_dashas)]:
        for i, p in enumerate(periods):
            lord = p.get("lord") or p.get("lord_or_sign") or p.get("planet_or_sign", "")
            # Get dates and strip to YYYY-MM-DD regardless of format
            sd = str(p.get("start_date") or p.get("start", ""))[:10]
            ed = str(p.get("end_date")   or p.get("end",   ""))[:10]
            # level column is INTEGER in DB — use sequence i
            # type column is TEXT — store mahadasha/antardasha
            level_name = p.get("level", "mahadasha")
            level_int  = 1 if level_name == "mahadasha" else (2 if level_name == "antardasha" else 3)
            dasha_rows.append({
                "chart_id":       chart_id,
                "system":         system,
                "type":           level_name,
                "level":          level_int,
                "planet_or_sign": lord,
                "start_date":     sd,
                "end_date":       ed,
                "duration_years": p.get("duration_years", 0),
                "sequence":       i,
                "parent_id":      None,
                "metadata":       {"parent_lord": p.get("parent_lord", ""), "type": level_name},
            })
    if dasha_rows:
        try:
            print(f"[dasha_insert] Attempting to insert {len(dasha_rows)} rows for chart {chart_id}")
            # Log first row so we can see what's being sent
            if dasha_rows:
                print(f"[dasha_insert] Sample row: {dasha_rows[0]}")
            for i in range(0, len(dasha_rows), 100):
                batch = dasha_rows[i:i+100]
                result = supabase.table("dasha_periods").insert(batch).execute()
                print(f"[dasha_insert] Batch {i//100+1}: inserted {len(result.data)} rows")
        except Exception as e:
            print(f"[dasha_insert] FAILED: {e}")
            print(f"[dasha_insert] First row was: {dasha_rows[0] if dasha_rows else 'empty'}")

    # ── Sprint E: Generate welcome signal in background ─────────
    try:
        import asyncio as _asyncio
        _first_name = getattr(request, "first_name", "") or getattr(request, "name", "") or ""
        _lagna_sign = chart_data.get("lagna", {}).get("sign", "")
        _moon_sign  = chart_data.get("planets", {}).get("Moon", {}).get("sign", "")
        _current_dasha = ""
        _vim = vim_dashas or []
        if _vim:
            _d = _vim[0]
            _current_dasha = _d.get("lord") or _d.get("lord_or_sign") or _d.get("planet_or_sign", "")

        # Fire and forget — don't block chart creation response
        # Sprint W: calculate age from birth_date so welcome signal is age-aware
        _birth_date_str = getattr(request, "birth_date", "") or ""
        try:
            from antar_engine.age_utils import calculate_current_age as _calc_age
            _welcome_age = _calc_age(str(_birth_date_str)[:10]) if _birth_date_str else None
        except Exception:
            _welcome_age = None

        _asyncio.create_task(generate_welcome_signal(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={"vimsottari": vim_dashas or []},
            first_name=_first_name,
            lagna=_lagna_sign,
            moon_sign=_moon_sign,
            current_dasha=_current_dasha,
            age=_welcome_age,
            birth_date=_birth_date_str,
            country_code=getattr(request, "birth_country", "") or "",
            supabase=supabase,
            claude_client=claude_client,
        ))
        print(f"[chart/create] Welcome signal task fired for {chart_id[:8]}")
    except Exception as _we:
        print(f"[chart/create] Welcome signal task failed (non-fatal): {_we}")
    # ── end Sprint E welcome ─────────────────────────────────────

    lk_data = None
    try:
        from antar_engine.varshaphal_table import get_annual_house
        from antar_engine.lal_kitab_advanced import build_lk_advanced_context
        from datetime import date as _date

        _born     = _date.fromisoformat(request.birth_date[:10])
        _age      = (_date.today() - _born).days // 365
        _planets  = chart_data.get("planets", {})
        _lagna    = chart_data.get("lagna", {})
        _lagna_sign = _lagna.get("sign","") if isinstance(_lagna, dict) else str(_lagna)

        # Annual house placements (Varshphal)
        _natal_houses = {
            p: d.get("house", 1)
            for p, d in _planets.items()
        }
        _placements = {
            p: get_annual_house(h, _age)
            for p, h in _natal_houses.items()
            if 1 <= h <= 12
        }

        lk_data = {
            "age":                _age,
            "placements":         _placements,
            "natal_planets":      {p: {"house": d.get("house"), "sign": d.get("sign")} for p, d in _planets.items()},
            "lagna_sign":         _lagna_sign,
            "birth_date":         request.birth_date,
            "is_special_cycle":   False,
            "cycle_significance": None,
        }

        # Save to charts table for hot path reads
        supabase.table("charts").update({
            "lal_kitab_data": lk_data,
        }).eq("id", chart_id).execute()

        print(f"[lk] Saved lal_kitab_data for chart {chart_id}")
    except Exception as e:
        print(f"[lk] lal_kitab_data error (non-fatal): {e}")

    planets = chart_data["planets"]
    ak, amk = _ak_amk(planets)


    # -- Telepathic Onboarding: Prashna-Intent Sensor --
    _signup_intent = None
    try:
        from antar_engine.prashna_intent import detect_signup_intent
        from datetime import datetime as _dt_tele, timezone as _tz_tele
        _signup_intent = detect_signup_intent(
            birth_lagna=chart_data["lagna"]["sign"],
            signup_timestamp=_dt_tele.now(_tz_tele.utc),
            signup_lat=float(lat),
            signup_lng=float(lng),
            first_name=getattr(request, "first_name", "") or "",
        )
        if _signup_intent and "error" not in _signup_intent:
            print(f"[chart/create] Telepathic intent: house={_signup_intent.get('intent_house')}, domain={_signup_intent.get('domain')}")
            try:
                supabase.table("charts").update({"signup_intent": _signup_intent}).eq("id", chart_id).execute()
            except Exception:
                pass
        else:
            _signup_intent = None
    except Exception as _intent_err:
        print(f"[chart/create] Intent detection failed (non-fatal): {_intent_err}")
        _signup_intent = None
    # -- end Telepathic Onboarding --

    # ── Compute natal signatures at chart creation ──────────────────
    try:
        _new_sigs      = compute_natal_signatures(chart_data)
        _new_archetype = derive_archetype(_new_sigs)
        supabase.table("charts").update({
            "planet_signatures":   _new_sigs,
            "character_archetype": _new_archetype,
        }).eq("id", chart_id).execute()
        print(f"[chart/create] Signatures stored — {_new_archetype.get('name','?')}")
    except Exception as _sig_create_e:
        print(f"[chart/create] Signatures non-fatal: {_sig_create_e}")

    return ChartCreateResponse(
        chart_id=chart_id,
        lagna=chart_data["lagna"]["sign"],
        lagna_degree=chart_data["lagna"].get("degree", 0),
        moon_sign=planets.get("Moon",{}).get("sign",""),
        sun_sign=planets.get("Sun",{}).get("sign",""),
        atmakaraka=ak, amatyakaraka=amk,
        current_dasha=_current_dasha_str(dashas_combined),
        dasha_count=len(dasha_rows),
        birth_city=request.birth_place or getattr(request, "birth_city", "") or "",
        birth_lat=lat, birth_lng=lng, timezone=timezone,
        message="Chart created successfully",
        signup_intent=_signup_intent,
    )

# ══════════════════════════════════════════════════════════════════════════════
# CAREER ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

class CareerRequest(BaseModel):
    chart_id: str
    question: Optional[str] = "What career works best for me and when is my peak?"
    include_funding: bool = False
    language: str = "en"

class CareerResponse(BaseModel):
    reading: str
    primary_fields: List[str]
    secondary_fields: List[str]
    work_style: str
    recommendation: str
    current_phase: str
    peak_earning_period: str
    funding_timing: Optional[str]
    wealth_timing: List[Dict]
    life_stage_note: Optional[str]

@app.post("/api/v1/career", response_model=CareerResponse)
async def get_career_reading(
    request: CareerRequest,
    authorization: Optional[str] = Header(None),
):
    user_id = None
    if authorization:
        try:
            user_id = verify_token(authorization)
        except HTTPException:
            pass

    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")
    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]
    dashas       = get_dashas_for_chart(request.chart_id)

    user_profile = {
        "marital_status":   chart_record.get("marital_status", "unknown"),
        "career_stage":     chart_record.get("career_stage", "mid_career"),
        "financial_status": chart_record.get("financial_status", "stable"),
        "birth_country":    chart_record.get("country_code", ""),
        "current_country":  chart_record.get("current_country") or chart_record.get("country_code", ""),
    }
    patra = build_patra_context(
        birth_date=chart_record["birth_date"],
        user_profile=user_profile,
        primary_concern="career",
    )

    from antar_engine.divisional_career import build_career_analysis, career_analysis_to_context_block
    career    = build_career_analysis(chart_data=chart_data, dashas=dashas, patra=patra)
    career_ctx = career_analysis_to_context_block(career)
    patra_ctx  = patra_to_context_block(patra)

    locale = get_locale_from_request(
        country_code=chart_record.get("country_code"),
        birth_country=chart_record.get("country_code"),
        user_language_preference=chart_record.get("language_preference"),
    )

    question = request.question or "What career works best for me and when is my peak?"
    if request.include_funding:
        question += " Also tell me when is the best window for funding or investment."

    prompt = f"""You are Antar — a Vedic astrology career coach.

{career_ctx}

{patra_ctx}

QUESTION: {question}

Answer in 5 sections:
1. YOUR PROFESSIONAL DESTINY — soul-level purpose, 2-3 sentences
2. YOUR STRONGEST CAREER FIELDS — 3-5 specific fields with one-line WHY each
3. HOW YOU WORK BEST — work style + entrepreneur vs employment (be direct)
4. YOUR CURRENT CAREER PHASE — what the active dasha means for career RIGHT NOW
5. WHEN YOUR CAREER PEAKS — specific dasha periods with actual years
{"6. FUNDING WINDOWS — when to raise money and what kind of funding" if request.include_funding else ""}

RULES: Never use technical terms (D-10, Atmakaraka, 10th lord).
Translate everything to energy language. Give actual years.
Respond in {locale.language}."""

    reading_text, _ = await call_llm(prompt)

    return CareerResponse(
        reading=reading_text,
        primary_fields=career.primary_fields,
        secondary_fields=career.secondary_fields,
        work_style=career.work_style,
        recommendation=career.recommendation,
        current_phase=career.current_career_phase,
        peak_earning_period=career.peak_earning_period,
        funding_timing=career.funding_timing if request.include_funding else None,
        wealth_timing=career.wealth_timing,
        life_stage_note=f"Calibrated for: {patra.life_stage_name} · {patra.career_stage.replace('_',' ').title()}",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ASTROCARTOGRAPHY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class AstroRequest(BaseModel):
    chart_id: str
    concern: str = "career"
    current_city: Optional[str] = None
    language: str = "en"

class AstroResponse(BaseModel):
    narrative: str
    top_cities: List[Dict]
    current_reading: Optional[Dict]
    concern: str

class CityReadingRequest(BaseModel):
    chart_id: str
    city: str
    language: str = "en"

class WaitlistRequest(BaseModel):
    email: str
    chart_id: Optional[str] = None
    name: Optional[str] = None

@app.post("/api/v1/astrocartography/best-cities", response_model=AstroResponse)
async def astrocartography_best_cities(
    request: AstroRequest,
    authorization: Optional[str] = Header(None),
):
    user_id = None
    if authorization:
        try:
            user_id = verify_token(authorization)
        except HTTPException:
            pass

    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")
    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]
    dashas       = get_dashas_for_chart(request.chart_id)

    user_profile = {
        "marital_status": chart_record.get("marital_status", "unknown"),
        "career_stage":   chart_record.get("career_stage", "mid_career"),
        "birth_country":  chart_record.get("birth_country", ""),
    }
    patra = build_patra_context(
        birth_date=chart_record["birth_date"],
        user_profile=user_profile,
        primary_concern=request.concern,
    )

    # Compute live planetary lines from birth JD, or fall back to hardcoded
    _birth_jd = chart_data.get("birth_jd")
    _city_line_data = get_city_line_data_for_chart(_birth_jd) if _birth_jd else CITY_LINE_DATA

    top_cities = get_best_cities_for_concern(
        concern=request.concern,
        city_line_data=_city_line_data,
        dashas=dashas,
        patra=patra,
    )

    current_reading = None
    if request.current_city:
        current_reading = get_current_location_reading(
            city=request.current_city,
            chart_data=chart_data,
            dashas=dashas,
        )

    locale = get_locale_from_request(
        country_code=chart_record.get("country_code"),
        birth_country=chart_record.get("birth_country"),
        user_language_preference=chart_record.get("language_preference"),
    )
    prompt = build_astrocartography_prompt(
        concern=request.concern,
        top_cities=top_cities,
        current_reading=current_reading,
        chart_data=chart_data,
        dashas=dashas,
        patra=patra,
        language=locale.language,
    )
    narrative, _ = await call_llm(prompt)

    # Cache the computed city_line_data in charts.astrocartography_data
    try:
        supabase.table("charts").update({
            "astrocartography_data": _city_line_data
        }).eq("id", request.chart_id).execute()
    except Exception as e:
        print(f"Astro cache error: {e}")

    return AstroResponse(
        narrative=narrative,
        top_cities=top_cities[:5],
        current_reading=current_reading,
        concern=request.concern,
    )


@app.post("/api/v1/astrocartography/city-reading")
async def astrocartography_city_reading(
    request: CityReadingRequest,
    authorization: Optional[str] = Header(None),
):
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")
    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]
    dashas       = get_dashas_for_chart(request.chart_id)

    reading = get_current_location_reading(
        city=request.city,
        chart_data=chart_data,
        dashas=dashas,
    )

    locale = get_locale_from_request(
        country_code=chart_record.get("country_code"),
        birth_country=chart_record.get("birth_country"),
        user_language_preference=chart_record.get("language_preference"),
    )

    prompt = f"""You are Antar. Describe what living in {request.city} means for this person astrologically.

City reading data:
{reading}

Keep it to 3-4 sentences. Be specific — name the energy, not the planet.
What does this city activate? What opportunities? What watch-outs?
End with: should they visit, move, or avoid this city right now?


RESPONSE RULES — CRITICAL:
1. Answer the user's question completely. Then stop.
2. NEVER end your response with a follow-up question like "Want me to look at a specific timeframe?" or "Should I explore what to focus on?" or "Would you like to know more?" The user asks the questions. You provide answers.
3. When the timing of an event is months or years away: Name the date clearly. Explain what to do BETWEEN NOW AND THEN. Frame the interim as PREPARATION, not waiting. The user should feel they have agency and a clear path. Never say "unfortunately you will have to wait."
4. End with a clear, specific, actionable recommendation. One thing. This week. Verb-first.

6. NEVER use planet names (Saturn, Rahu, Mars, Jupiter, Venus, Mercury, Ketu) when writing the parts of your response that the user will see directly. Describe the EFFECT instead of naming the cause. "Your income is being pressure-tested" not "Saturn is testing your income."
7. NEVER use spiritual platitudes like "the universe is testing you" or "cosmic energy" or "divine timing." Speak like a sharp business advisor who knows timing patterns, not a spiritual guide.
8. When the user is over 50, avoid death-adjacent framing like "outlast you" or "legacy" unless they specifically asked about succession. Frame longevity as freedom: "building something that runs without you pushing it daily."
9. When answering follow-up questions, check what you already said. Do NOT repeat the same timing frame. Each follow-up must add a new actionable layer — go deeper, not wider. If you already said "restructuring through 2027" do not say it again in the next response.

10. Every response should address the WHY — why this specific person is experiencing this specific situation right now. The WHY must be specific to their chart data (age, life stage, current chapter), must reframe from victim to participant, and must never use planet names or spiritual platitudes. The user should feel seen and understood, not lectured or patronized. Frame difficulties as chapters with purpose, not punishment.


5. When the chart shows a long cycle (10+ years), show the user the NEXT checkpoint (1-3 years), not the full runway. Never say "19-year period" or mention dates more than 5 years away. Frame it as phases: pressure phase → relief phase → growth phase. The user needs to see the next hill, not the entire mountain range.

Respond in {locale.language}."""

    narrative, _ = await call_llm(prompt)
    return {"city": request.city, "reading": reading, "narrative": narrative}


@app.get("/api/v1/astrocartography/{chart_id}")
async def get_astrocartography(chart_id: str, concern: str = "career", limit: int = 5):
    """GET endpoint for astrocartography — returns cached or computes on-the-fly."""
    try:
        # astrocartography_data column may not exist yet — fall back gracefully
        try:
            chart_res = supabase.table("charts").select(
                "chart_data, astrocartography_data, birth_date, current_country"
            ).eq("id", chart_id).single().execute()
        except Exception:
            chart_res = supabase.table("charts").select(
                "chart_data, birth_date, current_country"
            ).eq("id", chart_id).single().execute()
        if not chart_res.data:
            raise HTTPException(404, "Chart not found")
        chart_record = chart_res.data
        chart_data = chart_record.get("chart_data") or {}
        if isinstance(chart_data, str):
            import json as _acjson
            chart_data = _acjson.loads(chart_data)

        # 1. Try cached astrocartography_data first
        city_line_data = chart_record.get("astrocartography_data")
        if isinstance(city_line_data, str):
            import json as _acjson2
            city_line_data = _acjson2.loads(city_line_data)
        status = "cached" if city_line_data else "computed"

        # 2. If no cache, compute on-the-fly from birth_jd
        if not city_line_data:
            _birth_jd = chart_data.get("birth_jd")
            if _birth_jd:
                city_line_data = score_cities_for_chart(_birth_jd)
                # Cache it for next time
                try:
                    supabase.table("charts").update({
                        "astrocartography_data": city_line_data
                    }).eq("id", chart_id).execute()
                    print(f"[astrocartography] Computed and cached for {chart_id}")
                except Exception as _ce:
                    print(f"[astrocartography] Cache store failed: {_ce}")
            else:
                city_line_data = CITY_LINE_DATA  # fallback to hardcoded

        # 3. Score cities for the requested concern
        dashas = get_dashas_for_chart(chart_id)
        top_cities = get_best_cities_for_concern(
            concern=concern,
            city_line_data=city_line_data,
            dashas=dashas,
        )

        return {
            "chart_id": chart_id,
            "concern": concern,
            "top_cities": (top_cities or [])[:limit],
            "current_country": chart_record.get("current_country", ""),
            "status": status,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[astrocartography GET] Error for {chart_id}: {e}")
        import traceback; traceback.print_exc()
        return {
            "chart_id": chart_id,
            "concern": concern,
            "top_cities": [],
            "status": "error",
            "message": "Astrocartography is being computed for your chart.",
        }


@app.post("/api/v1/astrocartography/waitlist")
async def astrocartography_waitlist(request: WaitlistRequest):
    try:
        supabase.table("astrocartography_waitlist").insert({
            "email":      request.email,
            "chart_id":   request.chart_id,
            "name":       request.name,
            "created_at": "now()",
        }).execute()
    except Exception as e:
        print(f"Waitlist insert error: {e}")
    return {"status": "added", "message": "You are on the list. We will notify you when your city map is ready."}

# ══════════════════════════════════════════════════════════════════════════════
# CHAKRA ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

class ChakraRequest(BaseModel):
    chart_id: str
    language: str = "en"

class ChakraResponse(BaseModel):
    stressed_chakras:     List[Dict]
    flowing_chakras:      List[Dict]
    primary_practice:     Dict
    daily_sequence:       List[Dict]
    chapter_arc:          str
    current_chakra_name:  str
    current_chakra_color: str
    summary:              str

@app.post("/api/v1/chakra", response_model=ChakraResponse)
async def chakra_endpoint(
    request: ChakraRequest,
    authorization: Optional[str] = Header(None),
):
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")
    chart_record     = chart_res.data[0]
    chart_data       = chart_record["chart_data"]
    dashas           = get_dashas_for_chart(request.chart_id)
    _raw_transits = transits.calculate_transits(chart_data, target_date=None, ayanamsa_mode=1)
    current_transits = (
        {t["planet"]: t for t in _raw_transits if "planet" in t}
        if isinstance(_raw_transits, list) else _raw_transits
    )

    reading = get_chakra_reading(
        chart_data=chart_data,
        dashas=dashas,
        current_transits=current_transits,
    )

    return ChakraResponse(
        stressed_chakras    =reading["stressed_chakras"],
        flowing_chakras     =reading["flowing_chakras"],
        primary_practice    =reading["primary_practice"],
        daily_sequence      =reading["daily_sequence"],
        chapter_arc         =reading["chapter_arc"],
        current_chakra_name =reading["current_chapter_chakra"],
        current_chakra_color=reading["current_chapter_color"],
        summary             =reading["summary"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER ARC ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

class ChapterArcRequest(BaseModel):
    chart_id: str
    language: str = "en"

@app.post("/api/v1/chapter-arc")
async def chapter_arc_endpoint(
    request: ChapterArcRequest,
    authorization: Optional[str] = Header(None),
):
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")
    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]
    dashas       = get_dashas_for_chart(request.chart_id)

    user_profile = {
        "marital_status":   chart_record.get("marital_status", "unknown"),
        "children_status":  chart_record.get("children_status", "no_children_unsure"),
        "career_stage":     chart_record.get("career_stage", "mid_career"),
        "health_status":    chart_record.get("health_status", "excellent"),
        "financial_status": chart_record.get("financial_status", "stable"),
        "birth_country":    chart_record.get("country_code", ""),
        "current_country":  chart_record.get("current_country") or chart_record.get("country_code", ""),
        "countries_lived":  chart_record.get("countries_lived", []),
    }
    patra = build_patra_context(
        birth_date=chart_record["birth_date"],
        user_profile=user_profile,
        primary_concern="general",
    )

    arc = build_chapter_arc(chart_data=chart_data, dashas=dashas, patra=patra)
    return arc


# ══════════════════════════════════════════════════════════════════════════════
# PROOF POINTS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class ProofPointsRequest(BaseModel):
    chart_id: str

class ProofPointsResponse(BaseModel):
    proof_points: List[Dict]
    total:        int

class ProofEvalRequest(BaseModel):
    chart_id:  str
    responses: List[str]

@app.post("/api/v1/proof-points", response_model=ProofPointsResponse)
async def get_proof_points(request: ProofPointsRequest):
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")

    chart_record = chart_res.data[0]
    chart_data   = chart_record["chart_data"]
    dashas       = get_dashas_for_chart(request.chart_id)

    points = generate_proof_points(
        birth_date  = chart_record["birth_date"],
        chart_data  = chart_data,
        dashas      = dashas,
        first_name  = chart_record.get("name","").split()[0] if chart_record.get("name") else "",
        gender      = chart_record.get("gender",""),
        lagna_sign  = (chart_data.get("lagna",{}) or {}).get("sign","") if isinstance(chart_data.get("lagna"),dict) else chart_data.get("lagna",""),
    )

    clean_points = [
        {
            "statement":    p["statement"],
            "date_range":   p["date_range"],
            "domain":       p["domain"],
            "domain_label": p["domain_label"],
            "domain_icon":  p["domain_icon"],
            "confidence":   p["confidence"],
            "follow_up":    p["follow_up"],
        }
        for p in points
    ]
    return ProofPointsResponse(proof_points=clean_points, total=len(clean_points))


@app.post("/api/v1/proof-points/evaluate")
async def evaluate_proof_points(
    request: ProofEvalRequest,
    authorization: Optional[str] = Header(None),
):
    result = evaluate_proof_score(request.responses)

    if result["offer_free_month"]:
        try:
            supabase.table("charts").update({
                "proof_score":       result["score"],
                "free_month_earned": True,
            }).eq("id", request.chart_id).execute()
        except Exception as e:
            print(f"Free month flag error: {e}")
    else:
        try:
            supabase.table("charts").update({
                "proof_score": result["score"],
            }).eq("id", request.chart_id).execute()
        except Exception as e:
            print(f"Proof score save error: {e}")

    try:
        user_id = None
        if authorization:
            try:
                user_id = verify_token(authorization)
            except Exception:
                pass
        supabase.table("user_actions").insert({
            "user_id":     user_id,
            "action_type": "proof_loop_completed",
            "action_data": {
                "chart_id":  request.chart_id,
                "score":     result["score"],
                "responses": request.responses,
                "verdict":   result["verdict"],
            },
            "timestamp":   "now()",
        }).execute()
    except Exception as e:
        print(f"Proof loop log error: {e}")

    return result


# ══════════════════════════════════════════════════════════════════════════════
# LAL KITAB ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/chart/{chart_id}/remedies")
async def get_lk_remedies(
    chart_id: str,
    concern: str = "career",
    locale: str = "US",
):
    chart_res = supabase.table("charts").select("lal_kitab_data, country_code").eq("id", chart_id).execute()
    if not chart_res.data:
        raise HTTPException(404, "Chart not found")

    r       = chart_res.data[0]
    lk_data = r.get("lal_kitab_data")
    locale  = r.get("country_code", locale) or locale

    if not lk_data:
        return {"cards": [], "message": "Varshphal not yet computed for this chart"}

    try:
        engine = LalKitabEngine(supabase)
        cards  = engine.get_remedy_cards(lk_data, concern=concern, locale=locale, max_cards=3)
        return {
            "cards":            cards,
            "age":              lk_data.get("age"),
            "is_special_cycle": lk_data.get("is_special_cycle", False),
            "cycle_note":       lk_data.get("cycle_significance"),
        }
    except Exception as e:
        raise HTTPException(500, f"Remedy fetch failed: {e}")


@app.post("/api/v1/lal-kitab/varshphal/generate")
async def generate_varshphal_endpoint(
    chart_id: str,
    year: Optional[int] = None,
    authorization: str = Header(...),
):
    user_id = verify_token(authorization)
    try:
        varshphal = lal_kitab_gen.generate_varshphal(
            user_id=user_id,
            chart_id=chart_id,
            target_year=year,
            store=True,
        )
        return varshphal
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Varshphal generation failed: {e}")


@app.get("/api/v1/lal-kitab/varshphal/current")
async def get_current_varshphal_endpoint(authorization: str = Header(...)):
    user_id   = verify_token(authorization)
    varshphal = lal_kitab_gen.get_current_varshphal(user_id)
    if not varshphal:
        raise HTTPException(404, "No current Varshphal found. Chart may not have been created yet.")
    return varshphal


@app.get("/api/v1/lal-kitab/mashaphal/current")
async def get_current_mashaphal_endpoint(authorization: str = Header(...)):
    user_id   = verify_token(authorization)
    mashaphal = lal_kitab_gen.get_current_mashaphal(user_id)
    if not mashaphal:
        raise HTTPException(
            404,
            "No Mashaphal available. Ensure a Varshphal has been generated first.",
        )
    return mashaphal


@app.post("/api/v1/lal-kitab/mashaphal/generate-all")
async def generate_all_mashaphal_endpoint(
    varshphal_id: str,
    authorization: str = Header(...),
):
    verify_token(authorization)
    try:
        charts = lal_kitab_gen.generate_all_monthly_charts(varshphal_id, store=True)
        return {
            "generated": len(charts),
            "months": [
                {
                    "month_number":  c["month_number"],
                    "month_name":    c["month_name"],
                    "calendar_year": c["calendar_year"],
                }
                for c in charts
            ],
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Monthly chart generation failed: {e}")



# ── Prediction check-in response (from ping email link) ──────────────────────
@app.get("/api/v1/checkin")
async def prediction_checkin(pred: str, response: str):
    """
    Handles yes/no/partial responses from ping emails.
    pred = prediction_id, response = yes | no | partial
    """
    if response not in ("yes", "no", "partial"):
        raise HTTPException(400, "Invalid response")

    fulfilled      = response == "yes"
    partial        = response == "partial"
    fulfilled_date = datetime.utcnow().isoformat() if fulfilled or partial else None

    try:
        supabase.table("user_predictions").update({
            "fulfilled":       fulfilled or partial,
            "fulfilled_date":  fulfilled_date,
            "fulfillment_notes": response,
        }).eq("id", pred).execute()

        # Mark pending_ping as responded
        supabase.table("pending_pings") \
            .update({"responded": True, "response": response,
                     "responded_at": datetime.utcnow().isoformat()}) \
            .eq("prediction_id", pred).execute()

        # Update correlation confidence if partial or fulfilled
        if fulfilled or partial:
            pred_res = supabase.table("user_predictions") \
                .select("user_id, category") \
                .eq("id", pred).execute()
            if pred_res.data:
                uid = pred_res.data[0]["user_id"]
                cat = pred_res.data[0]["category"]
                # Bump correlation confidence for this pattern
                try:
                    supabase.rpc("increment_correlation_confidence", {
                        "p_user_id": uid, "p_category": cat, "p_delta": 0.05
                    }).execute()
                except Exception:
                    pass  # RPC may not exist yet — non-fatal

    except Exception as e:
        print(f"[checkin] Error: {e}")
        raise HTTPException(500, "Check-in update failed")

    base_url = os.getenv("FRONTEND_URL", "https://antar.world")
    messages = {
        "yes":     ("✓ Noted. Your pattern grows clearer.", "#7dc47d"),
        "partial": ("~ Partially. The signal is calibrating.", "#b8c47d"),
        "no":      ("✗ Noted. Even misses teach the system.", "#c47d7d"),
    }
    msg, color = messages[response]

    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""
<html><body style="font-family:-apple-system,sans-serif;background:#0f0f0f;
color:#e8e0d0;display:flex;align-items:center;justify-content:center;
height:100vh;margin:0;flex-direction:column;gap:16px;">
<p style="font-size:48px;margin:0">🔮</p>
<p style="font-size:22px;color:{color};font-weight:600">{msg}</p>
<p style="font-size:14px;color:#8b7355">Your Antar pattern engine is learning.</p>
<a href="{base_url}" style="margin-top:16px;color:#8b7355;font-size:13px;">
Return to Antar →</a>
</body></html>
""")


@app.post("/api/v1/lal-kitab/remedy/track")
async def track_remedy_endpoint(
    remedy_id:    int,
    varshphal_id: str,
    status:       str,
    notes:        str = "",
    authorization: str = Header(...),
):
    user_id = verify_token(authorization)

    remedy_name  = ""
    instructions = ""
    duration     = ""
    materials: List[str] = []

    try:
        r = supabase.table("lal_kitab_remedies") \
            .select("name, instructions, duration, materials") \
            .eq("id", remedy_id).single().execute()
        if r.data:
            remedy_name  = r.data.get("name", "")
            instructions = r.data.get("instructions", "")
            duration     = r.data.get("duration", "")
            materials    = r.data.get("materials") or []
    except Exception:
        pass

    lal_kitab_gen.track_remedy(
        user_id=user_id,
        remedy_id=remedy_id,
        varshphal_id=varshphal_id,
        status=status,
        remedy_name=remedy_name,
        instructions=instructions,
        duration=duration,
        materials=materials,
        notes=notes,
    )
    return {"status": "tracked", "remedy_id": remedy_id, "new_status": status}


# ── Entry point ───────────────────────────────────────────────────────────────


@app.post("/api/v1/compatibility")
async def get_compatibility(request: dict):
    """
    Vedic compatibility analysis — D1+D9+Houses+Dasha timing.
    Supports: relationship | business compatibility types.
    """
    from antar_engine.Compatibility import calculate_compatibility

    chart_id_a   = request.get("chart_id_a")
    chart_id_b   = request.get("chart_id_b")
    compat_type  = request.get("compatibility_type", "relationship")
    name_a       = request.get("name_a", "Person A")
    name_b       = request.get("name_b", "Person B")

    if not chart_id_a or not chart_id_b:
        raise HTTPException(400, "Both chart_id_a and chart_id_b required")

    res_a = supabase.table("charts").select("chart_data,birth_date").eq("id", chart_id_a).execute()
    res_b = supabase.table("charts").select("chart_data,birth_date").eq("id", chart_id_b).execute()

    if not res_a.data:
        raise HTTPException(404, f"Chart {chart_id_a} not found")
    if not res_b.data:
        raise HTTPException(404, f"Chart {chart_id_b} not found")

    chart_a      = res_a.data[0]["chart_data"]
    chart_b      = res_b.data[0]["chart_data"]
    birth_date_a = res_a.data[0].get("birth_date", "")
    birth_date_b = res_b.data[0].get("birth_date", "")

    # Inject current dasha strings
    dashas_a = get_dashas_for_chart(chart_id_a)
    dashas_b = get_dashas_for_chart(chart_id_b)
    chart_a["current_dasha"] = _current_dasha_str(dashas_a)
    chart_b["current_dasha"] = _current_dasha_str(dashas_b)

    result = calculate_compatibility(
        chart_a=chart_a,
        chart_b=chart_b,
        name_a=name_a,
        name_b=name_b,
        birth_date_a=birth_date_a,
        birth_date_b=birth_date_b,
        compatibility_type=compat_type,
    )
    return result


@app.post("/api/v1/timing/windows")
async def get_timing_windows(request: dict):
    """
    Auspicious timing windows for specific life events.
    Uses dasha confluence + transit analysis.
    """
    from antar_engine.timing_engine import timing_insights, upcoming_transit_windows

    chart_id = request.get("chart_id")
    concern  = request.get("concern", "general")
    language = request.get("language", "en")

    if not chart_id:
        raise HTTPException(400, "chart_id required")

    res = supabase.table("charts").select("chart_data").eq("id", chart_id).execute()
    if not res.data:
        raise HTTPException(404, "Chart not found")

    chart_data = res.data[0]["chart_data"]
    dashas     = get_dashas_for_chart(chart_id)

    try:
        insights = timing_insights(chart_data, dashas, supabase=supabase)
        transits = upcoming_transit_windows(chart_data)
    except Exception as e:
        raise HTTPException(500, f"Timing calculation failed: {e}")

    return {
        "chart_id":        chart_id,
        "concern":         concern,
        "timing_insights": insights,
        "transit_windows": transits[:6] if isinstance(transits, list) else [],
        "current_dasha":   _current_dasha_str(dashas),
    }



# ─────────────────────────────────────────────────────────────────────────────
# COMPATIBILITY SESSION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class CompatibilityStartRequest(BaseModel):
    chart_id_a:         str
    chart_id_b:         Optional[str] = None
    name_a:             str = "Person A"
    name_b:             str = "Person B"
    compatibility_type: str = "cofounder"
    birth_date_b:       Optional[str] = None
    birth_time_b:       Optional[str] = None
    birth_city_b:       Optional[str] = None
    birth_country_b:    Optional[str] = None
    latitude_b:         Optional[float] = None
    longitude_b:        Optional[float] = None
    timezone_b:         Optional[str] = None
    language:           Optional[str] = "en"


class CompatibilityContinueRequest(BaseModel):
    session_id:      str
    layer:           int
    startup_context: Optional[dict] = None
    product_context: Optional[str]  = None


def _compute_dasha_compatibility_score(dashas_a: dict, dashas_b: dict) -> dict:
    """
    Scores how aligned two people's current dasha periods are.

    Logic:
    - Both in expansive dashas (Jupiter, Rahu, Venus, Sun) → high score
    - One in contracting dasha (Saturn, Ketu, Mars) → moderate
    - Both in contracting dashas → low score
    - Dasha periods ending soon (< 2 years) → timing urgency flag

    Returns:
    {
        "score": int (0-100),
        "label": str,
        "window": str,
        "urgency": str,
        "detail": str,
    }
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    EXPANSIVE = {"Jupiter", "Rahu", "Venus", "Sun", "Moon"}
    CONTRACTING = {"Saturn", "Ketu", "Mars"}

    def get_current_md(dashas: dict) -> dict:
        periods = dashas.get("vimsottari", [])
        for p in periods:
            try:
                start = datetime.fromisoformat(str(p.get("start",""))[:10])
                end   = datetime.fromisoformat(str(p.get("end",""))[:10])
                if start.date() <= now.date() <= end.date():
                    return p
            except Exception:
                pass
        return periods[0] if periods else {}

    md_a = get_current_md(dashas_a)
    md_b = get_current_md(dashas_b)

    lord_a = md_a.get("lord_or_sign", "") or md_a.get("planet_or_sign", "")
    lord_b = md_b.get("lord_or_sign", "") or md_b.get("planet_or_sign", "")
    end_a  = md_a.get("end", "")
    end_b  = md_b.get("end", "")

    # Score based on dasha quality combination
    a_expansive = lord_a in EXPANSIVE
    b_expansive = lord_b in EXPANSIVE
    a_contract  = lord_a in CONTRACTING
    b_contract  = lord_b in CONTRACTING

    if a_expansive and b_expansive:
        score = 88
        label = "PEAK ALIGNMENT"
        detail = f"Both operating in expansive cycles — growth comes naturally together."
    elif a_expansive and b_contract:
        score = 62
        label = "ASYMMETRIC TIMING"
        detail = f"Different energy levels — one expanding while the other consolidates."
    elif a_contract and b_expansive:
        score = 62
        label = "ASYMMETRIC TIMING"
        detail = f"Different energy levels — one consolidating while the other expands."
    elif a_contract and b_contract:
        score = 45
        label = "CONSOLIDATION PHASE"
        detail = f"Both in consolidating cycles — this is a building period, not a launching one."
    else:
        score = 72
        label = "STABLE ALIGNMENT"
        detail = f"Neutral timing — neither strongly amplified nor blocked."

    # Check timing window — how long does current alignment last?
    try:
        end_dt_a = datetime.fromisoformat(str(end_a)[:10]) if end_a else None
        end_dt_b = datetime.fromisoformat(str(end_b)[:10]) if end_b else None
        ends = [d for d in [end_dt_a, end_dt_b] if d]
        earliest_end = min(ends) if ends else None
        if earliest_end:
            months_left = max(0, (earliest_end.year - now.year) * 12 + (earliest_end.month - now.month))
            if months_left <= 6:
                window = f"Window closing in {months_left} months"
                urgency = "NOW"
            elif months_left <= 18:
                window = f"Window open ~{months_left} months"
                urgency = "SOON"
            else:
                years_left = round(months_left / 12, 1)
                window = f"Window open ~{years_left} years"
                urgency = "STABLE"
        else:
            window = "Timing window unknown"
            urgency = "NEUTRAL"
    except Exception:
        window = ""
        urgency = "NEUTRAL"

    return {
        "score":   score,
        "label":   label,
        "window":  window,
        "urgency": urgency,
        "detail":  detail,
        "lord_a":  lord_a,
        "lord_b":  lord_b,
    }


def _compute_combined_timing(dasha_a: dict, dasha_b: dict, name_a: str = "Person A", name_b: str = "Person B") -> dict:
    """
    Determine if both people are in compatible life phases.
    Returns: alignment status, window description, months of overlap.
    """
    from datetime import datetime, timezone as _tz_mod
    now = datetime.now(_tz_mod.utc)

    RELATIONSHIP_ACTIVE = {"Venus", "Moon", "Jupiter"}
    EXPANSION_ACTIVE = {"Jupiter", "Rahu", "Sun"}

    # Extract current MD lord from vimsottari periods
    def _get_current_md(dashas: dict) -> tuple:
        """Returns (lord_name, remaining_months)"""
        periods = dashas.get("vimsottari", [])
        for p in periods:
            try:
                level = p.get("level", "mahadasha")
                if level != "mahadasha":
                    continue
                start = datetime.fromisoformat(str(p.get("start", "") or p.get("start_date", ""))[:10])
                end = datetime.fromisoformat(str(p.get("end", "") or p.get("end_date", ""))[:10])
                if start.date() <= now.date() <= end.date():
                    months_left = max(0, (end.year - now.year) * 12 + (end.month - now.month))
                    lord = p.get("lord_or_sign", "") or p.get("planet_or_sign", "") or p.get("lord", "")
                    return (lord, months_left)
            except Exception:
                pass
        # Fallback: first mahadasha
        for p in periods:
            if p.get("level", "mahadasha") == "mahadasha":
                lord = p.get("lord_or_sign", "") or p.get("planet_or_sign", "") or p.get("lord", "")
                return (lord, 0)
        return ("", 0)

    # Get current antardasha
    def _get_current_ad(dashas: dict) -> str:
        periods = dashas.get("vimsottari", [])
        for p in periods:
            try:
                level = p.get("level", "antardasha")
                if level != "antardasha":
                    continue
                start = datetime.fromisoformat(str(p.get("start", "") or p.get("start_date", ""))[:10])
                end = datetime.fromisoformat(str(p.get("end", "") or p.get("end_date", ""))[:10])
                if start.date() <= now.date() <= end.date():
                    return p.get("lord_or_sign", "") or p.get("planet_or_sign", "") or p.get("lord", "")
            except Exception:
                pass
        return ""

    md_a, remaining_a = _get_current_md(dasha_a)
    md_b, remaining_b = _get_current_md(dasha_b)
    ad_a = _get_current_ad(dasha_a)
    ad_b = _get_current_ad(dasha_b)

    # Determine phase label
    def _phase_label(remaining, total_approx=84):
        if remaining <= 0:
            return "Active Phase"
        pct = remaining / max(total_approx, 1)
        if pct > 0.75:
            return "The Opening Phase"
        elif pct > 0.5:
            return "The Building Phase"
        elif pct > 0.25:
            return "The Peak Phase"
        else:
            return "The Completion Phase"

    both_active = md_a in RELATIONSHIP_ACTIVE and md_b in RELATIONSHIP_ACTIVE
    one_active = (md_a in RELATIONSHIP_ACTIVE or md_b in RELATIONSHIP_ACTIVE) and not both_active
    overlap_months = min(remaining_a, remaining_b)

    if both_active:
        status = "aligned"
        label = "Both in active phases"
        description = f"Both are in expansive life phases. This window lasts {overlap_months} more months."
    elif one_active:
        active_person = name_a if md_a in RELATIONSHIP_ACTIVE else name_b
        status = "partial"
        label = "One person in active phase"
        description = f"{active_person} is in an active phase. The other is in a consolidation period."
    else:
        status = "misaligned"
        label = "Both in consolidation phases"
        description = "Neither person is in an expansion phase right now. Timing favors patience."
        overlap_months = 0

    return {
        "status": status,
        "label": label,
        "overlap_months": overlap_months,
        "description": description,
        "md_a": md_a,
        "md_b": md_b,
        "ad_a": ad_a,
        "ad_b": ad_b,
        "remaining_a": remaining_a,
        "remaining_b": remaining_b,
        "phase_label_a": _phase_label(remaining_a),
        "phase_label_b": _phase_label(remaining_b),
    }


@app.post("/api/v1/compatibility/start")
async def compatibility_start(request: CompatibilityStartRequest):
    from antar_engine.compatibility_session_engine import (
        build_person_brief, run_layer1_llm, detect_no_birth_time_chart
    )
    import uuid as _uuid

    # Check compatibility limit
    from antar_engine.subscription_engine import check_limit, increment_usage
    compat_check = check_limit(request.chart_id_a, "compat", supabase)
    if not compat_check["allowed"]:
        raise HTTPException(429, {
            "error": "compat_limit_reached",
            "message": f"Free plan includes 1 compatibility check. Upgrade for more.",
            "used": compat_check["used"],
            "limit": compat_check["limit"],
            "upgrade_url": "https://antar.world/upgrade",
        })

    res_a = supabase.table("charts").select("chart_data,birth_date,name").eq("id", request.chart_id_a).execute()
    if not res_a.data:
        raise HTTPException(404, f"Chart {request.chart_id_a} not found")
    chart_a  = res_a.data[0]["chart_data"]
    birth_a  = res_a.data[0].get("birth_date","")
    name_a   = request.name_a or (res_a.data[0].get("name","") or "").split()[0] or "Person A"
    dashas_a = get_dashas_for_chart(request.chart_id_a)
    has_time_a = not detect_no_birth_time_chart(chart_a)

    if request.chart_id_b:
        res_b = supabase.table("charts").select("chart_data,birth_date,name").eq("id", request.chart_id_b).execute()
        if not res_b.data:
            raise HTTPException(404, f"Chart {request.chart_id_b} not found")
        chart_b    = res_b.data[0]["chart_data"]
        birth_b    = res_b.data[0].get("birth_date","")
        chart_id_b = request.chart_id_b
        dashas_b   = get_dashas_for_chart(chart_id_b)
        has_time_b = not detect_no_birth_time_chart(chart_b)
    else:
        if not request.birth_date_b:
            raise HTTPException(400, "Either chart_id_b or birth_date_b required")
        birth_time_b = request.birth_time_b or "12:00"
        has_time_b   = bool(request.birth_time_b)
        city_b    = request.birth_city_b or "New Delhi"
        country_b = request.birth_country_b or "IN"

        # Use provided lat/lng/tz if available (from frontend city autocomplete)
        if request.latitude_b and request.longitude_b:
            coords_b = {
                "lat": request.latitude_b,
                "lng": request.longitude_b,
                "timezone": request.timezone_b or "UTC",
            }
        else:
            # Try internal geocoder, fall back to Nominatim for unknown cities
            coords_b = None
            try:
                _gc = await _geocode_city(city_b, country_b)
                if isinstance(_gc, (tuple, list)) and len(_gc) >= 2:
                    coords_b = {"lat": _gc[0], "lng": _gc[1], "timezone": _gc[2] if len(_gc) > 2 else "UTC"}
                elif isinstance(_gc, dict) and _gc.get("lat"):
                    coords_b = _gc
            except Exception:
                pass
            if not coords_b or not coords_b.get("lat"):
                try:
                    import httpx as _httpx
                    nom = await _httpx.AsyncClient().get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": f"{city_b}, {country_b}", "format": "json", "limit": 1},
                        headers={"User-Agent": "Antar/1.0"},
                        timeout=10,
                    )
                    nom_data = nom.json()
                    if nom_data:
                        coords_b = {
                            "lat": float(nom_data[0]["lat"]),
                            "lng": float(nom_data[0]["lon"]),
                            "timezone": getattr(request, "timezone", None) or f'UTC{int(getattr(request, "timezone_offset", 0) or 0):+d}',
                        }
                        try:
                            import timezonefinder as _tzf
                            tf = _tzf.TimezoneFinder()
                            tz = tf.timezone_at(lat=coords_b["lat"], lng=coords_b["lng"])
                            if tz: coords_b["timezone"] = tz
                        except Exception:
                            pass
                except Exception:
                    pass
        if not coords_b or not coords_b.get("lat"):
            raise HTTPException(400, f"Could not locate '{city_b}'. Try a larger nearby city.")

        # Check if this person already has a chart (same birth data + name under this chart_a)
        _existing_b = None
        try:
            _existing_b = supabase.table("charts").select("id").eq(
                "parent_chart_id", request.chart_id_a
            ).eq("name", request.name_b).eq(
                "birth_date", request.birth_date_b
            ).execute()
        except Exception:
            pass

        if _existing_b and _existing_b.data:
            chart_id_b = _existing_b.data[0]["id"]
            _res_b2 = supabase.table("charts").select("chart_data").eq("id", chart_id_b).execute()
            chart_b = _res_b2.data[0]["chart_data"] if _res_b2.data else {}
            dashas_b = get_dashas_for_chart(chart_id_b)
            print(f"[compat] Reusing existing sub-chart {chart_id_b} for {request.name_b}")
        else:
            from antar_engine.chart import calculate_chart
            chart_b = calculate_chart(
                birth_date=request.birth_date_b,
                birth_time=birth_time_b,
                lat=coords_b["lat"], lng=coords_b["lng"],
                timezone=coords_b.get("timezone", "UTC"),
            )
            chart_id_b = str(_uuid.uuid4())

            # Compute dashas for Chart B (same as chart/create)
            from antar_engine import vimsottari as _vim_mod, ashtottari as _ash_mod
            _vim_b, _jai_b, _ash_b = [], [], []
            def _normalise_dashas_b(raw):
                flat = []
                for p in raw:
                    if isinstance(p, dict) and "sub" in p:
                        sd = str(p.get("start_date","") or p.get("start",""))[:10]
                        ed = str(p.get("end_date","") or p.get("end",""))[:10]
                        flat.append({"lord_or_sign": p.get("lord",""), "planet_or_sign": p.get("lord",""), "start": sd, "end": ed, "start_date": sd, "end_date": ed, "duration_years": p.get("duration_years",0), "level": "mahadasha", "parent_lord": ""})
                        for s in p.get("sub",[]):
                            ssd = str(s.get("start_date","") or s.get("start",""))[:10]
                            sed = str(s.get("end_date","") or s.get("end",""))[:10]
                            flat.append({"lord_or_sign": s.get("lord",""), "planet_or_sign": s.get("lord",""), "start": ssd, "end": sed, "start_date": ssd, "end_date": sed, "duration_years": s.get("duration_years",0), "level": "antardasha", "parent_lord": s.get("parent_lord","")})
                    elif isinstance(p, dict):
                        sd = str(p.get("start_date","") or p.get("start",""))[:10]
                        ed = str(p.get("end_date","") or p.get("end",""))[:10]
                        flat.append({"lord_or_sign": p.get("lord","") or p.get("lord_or_sign","") or p.get("planet_or_sign",""), "planet_or_sign": p.get("lord","") or p.get("lord_or_sign","") or p.get("planet_or_sign",""), "start": sd, "end": ed, "start_date": sd, "end_date": ed, "duration_years": p.get("duration_years",0), "level": p.get("level","mahadasha"), "parent_lord": p.get("parent_lord","")})
                return flat
            try:
                _vim_b = _normalise_dashas_b(_vim_mod.calculate_vimsottari_from_chart(chart_b, chart_b.get("birth_jd")))
            except Exception as _ve:
                print(f"[compat] Chart B vimsottari error: {_ve}")
            try:
                _ash_b = _normalise_dashas_b(_ash_mod.calculate_ashtottari_from_chart(chart_b, chart_b.get("birth_jd")))
            except Exception as _ae:
                print(f"[compat] Chart B ashtottari error: {_ae}")

            # Compute timezone offset for Chart B
            _offset_b = 0.0
            try:
                import pytz as _pytz_b
                _tz_b = _pytz_b.timezone(coords_b.get("timezone", "UTC"))
                from datetime import datetime as _dt_b
                _birth_dt_b = _dt_b.strptime(str(request.birth_date_b)[:10], "%Y-%m-%d")
                _offset_b = _tz_b.utcoffset(_birth_dt_b).total_seconds() / 3600
            except Exception:
                pass

            # Store Chart B as real sub-chart
            supabase.table("charts").insert({
                "id": chart_id_b,
                "birth_date": request.birth_date_b,
                "birth_time": birth_time_b,
                "birth_city": city_b,
                "birth_country": country_b,
                "latitude": coords_b["lat"],
                "longitude": coords_b["lng"],
                "timezone": coords_b.get("timezone", "UTC"),
                "timezone_offset": _offset_b,
                "name": request.name_b,
                "chart_data": chart_b,
                "lagna_sign": chart_b.get("lagna", {}).get("sign", ""),
                "lagna_degree": chart_b.get("lagna", {}).get("degree", 0),
                "moon_sign": chart_b.get("planets", {}).get("Moon", {}).get("sign", ""),
                "moon_nakshatra": chart_b.get("planets", {}).get("Moon", {}).get("nakshatra", ""),
                "sun_sign": chart_b.get("planets", {}).get("Sun", {}).get("sign", ""),
                "parent_chart_id": request.chart_id_a,
                "chart_type": "compatibility",
            }).execute()

            # Store dasha periods for Chart B
            _dasha_rows_b = []
            for _sys, _periods in [("vimsottari", _vim_b), ("ashtottari", _ash_b)]:
                for _i, _p in enumerate(_periods):
                    _lord = _p.get("lord") or _p.get("lord_or_sign") or _p.get("planet_or_sign", "")
                    _sd = str(_p.get("start_date") or _p.get("start", ""))[:10]
                    _ed = str(_p.get("end_date") or _p.get("end", ""))[:10]
                    _level_name = _p.get("level", "mahadasha")
                    _level_int = 1 if _level_name == "mahadasha" else (2 if _level_name == "antardasha" else 3)
                    _dasha_rows_b.append({
                        "chart_id": chart_id_b,
                        "system": _sys,
                        "type": _level_name,
                        "level": _level_int,
                        "planet_or_sign": _lord,
                        "start_date": _sd,
                        "end_date": _ed,
                        "duration_years": _p.get("duration_years", 0),
                        "sequence": _i,
                        "parent_id": None,
                        "metadata": {"parent_lord": _p.get("parent_lord", ""), "type": _level_name},
                    })
            if _dasha_rows_b:
                try:
                    for _i in range(0, len(_dasha_rows_b), 100):
                        _batch = _dasha_rows_b[_i:_i+100]
                        supabase.table("dasha_periods").insert(_batch).execute()
                    print(f"[compat] Chart B dashas stored: {len(_dasha_rows_b)} rows")
                except Exception as _dbe:
                    print(f"[compat] Chart B dasha store non-fatal: {_dbe}")

            dashas_b = {"vimsottari": _vim_b, "ashtottari": _ash_b}
            print(f"[compat] Created sub-chart {chart_id_b} for {request.name_b} (parent={request.chart_id_a})")
        birth_b = request.birth_date_b

    _compat_type = request.compatibility_type or "cofounder"
    brief_a = build_person_brief(name_a, chart_a, dashas_a, birth_a, has_time_a, _compat_type)
    brief_b = build_person_brief(request.name_b, chart_b, dashas_b,
                                  birth_b if request.chart_id_b else request.birth_date_b,
                                  has_time_b, _compat_type)

    # ── FIX 3: Pre-compute timing and inject into briefs for Claude ──
    _pre_timing = _compute_combined_timing(dashas_a, dashas_b, name_a, request.name_b)
    _timing_inject = f"""
COMBINED TIMING CONTEXT:
{name_a} current cycle: {_pre_timing['md_a']} ({_pre_timing['phase_label_a']}, {_pre_timing['remaining_a']} months remaining)
{request.name_b} current cycle: {_pre_timing['md_b']} ({_pre_timing['phase_label_b']}, {_pre_timing['remaining_b']} months remaining)
Alignment status: {_pre_timing['status'].upper()} — {_pre_timing['description']}
Overlap window: {_pre_timing['overlap_months']} months
IMPORTANT: Lead with timing analysis — is NOW a good time for this {_compat_type}? Be specific about the window (months, not vague). No astrology jargon in output.
"""
    brief_b = brief_b + "\n" + _timing_inject

    layer1 = await run_layer1_llm(
        brief_a=brief_a, brief_b=brief_b,
        name_a=name_a, name_b=request.name_b,
        compat_type=request.compatibility_type,
        has_time_a=has_time_a, has_time_b=has_time_b,
    )

    # Extract score from layer1 text
    import re as _re
    score_match = _re.search(r'score[:\s]+(\d+)/100', layer1, _re.IGNORECASE)
    extracted_score = int(score_match.group(1)) if score_match else None

    # Increment compatibility usage
    from antar_engine.subscription_engine import increment_usage
    increment_usage(request.chart_id_a, "compat", supabase)

    session_id = str(_uuid.uuid4())
    try:
        supabase.table("compatibility_sessions").insert({
            "id": session_id,
            "chart_id_a": request.chart_id_a,
            "chart_id_b": chart_id_b,
            "name_a": name_a, "name_b": request.name_b,
            "compat_type": request.compatibility_type,
            "brief_a": brief_a, "brief_b": brief_b,
            "layer1_analysis": layer1,
            "has_time_a": has_time_a, "has_time_b": has_time_b,
            "current_layer": 1,
            "score": extracted_score,
        }).execute()
    except Exception as _se:
        print(f"[compat] session save error (non-fatal): {_se}")

    # ── FIELD×MODE Synastry Layer ────────────────────────────────────────────
    _field_mode_layer = {}
    try:
        from antar_engine.synastry_engine import compute_field_mode_synastry, get_or_compute_archetype
        _arch_a = get_or_compute_archetype(request.chart_id_a, chart_a, supabase)
        _arch_b = get_or_compute_archetype(chart_id_b, chart_b, supabase)
        if _arch_a and _arch_b:
            _field_mode_layer = compute_field_mode_synastry(_arch_a, _arch_b, name_a, request.name_b)
            print(f"[compat] Synastry: {_arch_a.get('name')} + {_arch_b.get('name')} = {_field_mode_layer.get('verdict')} field={_field_mode_layer.get('field_dynamic')} mode={_field_mode_layer.get('mode_dynamic')}")
            # Save to session
            try:
                supabase.table("compatibility_sessions").update({
                    "field_mode_synastry": _field_mode_layer
                }).eq("id", session_id).execute()
            except Exception as _sye:
                print(f"[compat] synastry save error (non-fatal): {_sye}")
    except Exception as _fe:
        print(f"[compat] synastry layer error (non-fatal): {_fe}")
    # ── end synastry ──────────────────────────────────────────────────────────

    # ── NAKSHATRA CROSS-GROUP DYNAMICS ───────────────────────────────────────
    _nakshatra_layer = {}
    try:
        from antar_engine.nakshatra_groups import get_nakshatra_group, get_cross_group_dynamic
        _safe_chart_a = _safe_json(chart_a) if isinstance(chart_a, str) else chart_a
        _safe_chart_b = _safe_json(chart_b) if isinstance(chart_b, str) else chart_b
        _moon_nak_a = (_safe_chart_a or {}).get("planets", {}).get("Moon", {}).get("nakshatra", "")
        _moon_nak_b = (_safe_chart_b or {}).get("planets", {}).get("Moon", {}).get("nakshatra", "")
        _group_a = get_nakshatra_group(_moon_nak_a) if _moon_nak_a else 0
        _group_b = get_nakshatra_group(_moon_nak_b) if _moon_nak_b else 0
        if _group_a and _group_b:
            _cross_group = get_cross_group_dynamic(_group_a, _group_b)
            _nakshatra_layer = {
                "person_a_group": _group_a,
                "person_b_group": _group_b,
                "person_a_nakshatra": _moon_nak_a,
                "person_b_nakshatra": _moon_nak_b,
                "dynamic_name": _cross_group["dynamic"],
                "description": _cross_group["description"],
                "strength": _cross_group["strength"],
                "risk": _cross_group["risk"],
                "advice": _cross_group["advice"],
                "compatibility_modifier": _cross_group["compatibility_modifier"],
            }
            print(f"[compat] Nakshatra dynamic: {_moon_nak_a}(G{_group_a}) x {_moon_nak_b}(G{_group_b}) = {_cross_group['dynamic']} (mod={_cross_group['compatibility_modifier']})")
    except Exception as _nke:
        print(f"[compat] nakshatra layer error (non-fatal): {_nke}")
    # ── end nakshatra ────────────────────────────────────────────────────────

    # ── Structured score breakdown ───────────────────────────────────────────
    _overall_score     = extracted_score or 72
    _personality_score = min(100, int((_field_mode_layer.get("score_contribution", 15) / 20) * 100)) if _field_mode_layer else 70
    _dasha_scores      = _compute_dasha_compatibility_score(dashas_a, dashas_b)
    _dasha_score       = _dasha_scores["score"]

    # ── Combined timing analysis (8-layer context) ──────────────────
    _combined_timing = _compute_combined_timing(dashas_a, dashas_b, name_a, request.name_b)
    print(f"[compat] Combined timing: {_combined_timing['status']} | A={_combined_timing['md_a']} B={_combined_timing['md_b']} | overlap={_combined_timing['overlap_months']}mo")

    # Weighted overall: 50% natal/personality + 30% dasha + 20% field_mode + nakshatra modifier
    _nak_modifier = _nakshatra_layer.get("compatibility_modifier", 0) if _nakshatra_layer else 0
    _weighted_overall = max(0, min(100, int(
        (_overall_score * 0.5) +
        (_dasha_score   * 0.3) +
        (_personality_score * 0.2) +
        _nak_modifier
    )))

    # Type-specific score labels
    _type_labels = {
        "relationship": {
            "score_a_label": "Emotional Resonance",
            "score_b_label": "Timing Alignment",
            "score_c_label": "Dynamic Fit",
        },
        "business": {
            "score_a_label": "Strategic Fit",
            "score_b_label": "Timing Alignment",
            "score_c_label": "Communication Match",
        },
        "cofounder": {
            "score_a_label": "Role Fit",
            "score_b_label": "Runway Alignment",
            "score_c_label": "Operating Rhythm",
        },
    }.get(request.compatibility_type, {
        "score_a_label": "Personality Match",
        "score_b_label": "Timing Alignment",
        "score_c_label": "Dynamic Fit",
    })

    _score_breakdown = {
        "overall":        _weighted_overall,
        "personality":    _overall_score,
        "dasha":          _dasha_score,
        "field_mode":     _personality_score,
        "dasha_label":    _dasha_scores["label"],
        "dasha_window":   _dasha_scores["window"],
        "dasha_urgency":  _dasha_scores["urgency"],
        "dasha_detail":   _dasha_scores["detail"],
        "score_a_label":  _type_labels["score_a_label"],
        "score_b_label":  _type_labels["score_b_label"],
        "score_c_label":  _type_labels["score_c_label"],
        "compat_type":    request.compatibility_type,
        "nakshatra_dynamic": _nakshatra_layer.get("dynamic_name", "") if _nakshatra_layer else "",
    }

    # ── Auto-save connection ─────────────────────────────────────────────────
    try:
        _analysis_summary = layer1[:600].strip() if layer1 else ""
        # Upsert — same pair + type = update, new pair = insert
        _existing_conn = supabase.table("chart_connections").select("id") \
            .eq("chart_id_a", request.chart_id_a) \
            .eq("chart_id_b", chart_id_b) \
            .eq("compat_type", request.compatibility_type) \
            .execute()

        _conn_data = {
            "chart_id_a":      request.chart_id_a,
            "chart_id_b":      chart_id_b,
            "name_a":          name_a,
            "name_b":          request.name_b,
            "compat_type":     request.compatibility_type,
            "session_id":      session_id,
            "overall_score":   _score_breakdown.get("overall", 0),
            "pairing_name":    _field_mode_layer.get("pairing_name", "") if _field_mode_layer else "",
            "verdict":         _field_mode_layer.get("verdict", "") if _field_mode_layer else "",
            "analysis_summary": _analysis_summary,
            "score_breakdown": _score_breakdown,
            "field_mode_layer": _field_mode_layer or {},
            "updated_at":      "now()",
        }

        if _existing_conn.data:
            supabase.table("chart_connections").update(_conn_data) \
                .eq("id", _existing_conn.data[0]["id"]).execute()
            print(f"[connections] Updated connection: {name_a} × {request.name_b} ({request.compatibility_type})")
        else:
            supabase.table("chart_connections").insert(_conn_data).execute()
            print(f"[connections] Saved connection: {name_a} × {request.name_b} ({request.compatibility_type})")
    except Exception as _conn_err:
        print(f"[connections] Auto-save non-fatal: {_conn_err}")

    return {
        "session_id":       session_id,
        "layer":            1,
        "chart_id_b":       chart_id_b,
        "analysis":         layer1,
        "has_time_a":       has_time_a,
        "has_time_b":       has_time_b,
        "confidence_pct":   90 if (has_time_a and has_time_b) else 65,
        "next_question":    "Would you like to analyze startup or business alignment?",
        "can_continue":     True,
        "field_mode_layer": _field_mode_layer or None,
        "nakshatra_layer":  _nakshatra_layer or None,
        "score_breakdown":  _score_breakdown,
        # ── NEW: 8-layer timing context ──
        "chart_b_dasha": {
            "current_md": _combined_timing.get("md_b", ""),
            "current_ad": _combined_timing.get("ad_b", ""),
            "md_remaining_months": _combined_timing.get("remaining_b", 0),
            "phase_label": _combined_timing.get("phase_label_b", ""),
        },
        "combined_timing": {
            "status": _combined_timing.get("status", ""),
            "label": _combined_timing.get("label", ""),
            "overlap_months": _combined_timing.get("overlap_months", 0),
            "description": _combined_timing.get("description", ""),
        },
        "timing": {
            "phase_a": _combined_timing.get("md_a", ""),
            "phase_b": _combined_timing.get("md_b", ""),
            "aligned": _combined_timing.get("status") == "aligned",
            "overlap_months": _combined_timing.get("overlap_months", 0),
            "description": _combined_timing.get("description", ""),
            "status": _combined_timing.get("status", ""),
            "label": _combined_timing.get("label", ""),
        },
    }


@app.post("/api/v1/compatibility/continue")
async def compatibility_continue(request: CompatibilityContinueRequest):
    from antar_engine.compatibility_session_engine import run_layer2_llm, run_layer3_llm

    res = supabase.table("compatibility_sessions").select("*").eq("id", request.session_id).execute()
    if not res.data:
        raise HTTPException(404, "Compatibility session not found")
    session = res.data[0]
    brief_a = session["brief_a"]
    brief_b = session["brief_b"]
    name_a  = session["name_a"]
    name_b  = session["name_b"]

    if request.layer == 2:
        if not request.startup_context:
            raise HTTPException(400, "startup_context required for layer 2")
        analysis = await run_layer2_llm(
            brief_a=brief_a, brief_b=brief_b,
            name_a=name_a, name_b=name_b,
            layer1_summary=session.get("layer1_analysis","")[:500],
            startup_context=request.startup_context,
        )
        supabase.table("compatibility_sessions").update({
            "layer2_analysis": analysis,
            "startup_context": request.startup_context,
            "current_layer": 2,
        }).eq("id", request.session_id).execute()
        return {"session_id": request.session_id, "layer": 2,
                "analysis": analysis, "can_continue": True,
                "next_question": "Would you like me to analyze your product or pitch deck?"}

    elif request.layer == 3:
        if not request.product_context:
            raise HTTPException(400, "product_context required for layer 3")
        analysis = await run_layer3_llm(
            brief_a=brief_a, brief_b=brief_b,
            name_a=name_a, name_b=name_b,
            layer1_summary=session.get("layer1_analysis","")[:400],
            layer2_summary=session.get("layer2_analysis","")[:400],
            product_context=request.product_context,
        )
        supabase.table("compatibility_sessions").update({
            "layer3_analysis": analysis,
            "product_context": request.product_context,
            "current_layer": 3,
        }).eq("id", request.session_id).execute()
        return {"session_id": request.session_id, "layer": 3,
                "analysis": analysis, "can_continue": False}

    raise HTTPException(400, "layer must be 2 or 3")


@app.get("/api/v1/compatibility/session/{session_id}")
async def get_compatibility_session(session_id: str):
    res = supabase.table("compatibility_sessions").select("*").eq("id", session_id).execute()
    if not res.data:
        raise HTTPException(404, "Session not found")
    s = res.data[0]
    return {
        "session_id":    session_id,
        "current_layer": s.get("current_layer", 1),
        "layer1":        s.get("layer1_analysis"),
        "layer2":        s.get("layer2_analysis"),
        "layer3":        s.get("layer3_analysis"),
        "has_time_a":    s.get("has_time_a", True),
        "has_time_b":    s.get("has_time_b", True),
        "compat_type":   s.get("compat_type"),
        "name_a":        s.get("name_a"),
        "name_b":        s.get("name_b"),
    }




@app.get("/api/v1/panchanga")
@app.post("/api/v1/panchanga")
async def get_panchanga(request: dict = {}):
    """
    Today's Panchanga — 5 limbs of the day.
    Includes lucky hours, do/don't, Rahu Kalam, Abhijit Muhurta.
    No chart_id needed — universal for the day.
    Optional: pass lat/lng for location-specific timing.
    """
    lat = request.get("lat", 28.6) if request else 28.6
    lng = request.get("lng", 77.2) if request else 77.2

    from antar_engine.daily_panchanga import calculate_panchanga, format_daily_for_user
    panchanga = calculate_panchanga(lat=lat, lng=lng)
    if panchanga.get("error"):
        raise HTTPException(500, f"Panchanga error: {panchanga['error']}")

    formatted = format_daily_for_user(panchanga)
    return {**panchanga, **formatted}




class PrashnaRequest(BaseModel):
    question:       str
    chart_id:       Optional[str] = None
    lat:            Optional[float] = 28.6139
    lng:            Optional[float] = 77.2090
    language:       Optional[str] = "en"
    generate_answer: Optional[bool] = True

@app.post("/api/v1/prashna")
async def ask_prashna(request: PrashnaRequest):
    """
    Prashna (Horary) Oracle — real-time YES/NO verdict engine.
    Uses Ithasala (Tajika) + 4-step scoring + Navamsa genuineness + VoC Moon.
    Python calculates ALL facts. Claude only explains in plain English.
    """
    import traceback
    import logging
    from fastapi.responses import JSONResponse
    logger = logging.getLogger('antar.prashna')
    from datetime import datetime, timezone

    try:
        chart_id = request.chart_id
        question = (request.question or "").strip()

        if not question:
            return JSONResponse(status_code=400, content={"error": "Question is required"})

        # ─── 1. Cooldown Check (24h between questions) ───
        try:
            last_prashna = supabase.table("prashna_log") \
                .select("created_at") \
                .eq("chart_id", chart_id) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()

            last_time = None
            if last_prashna.data and len(last_prashna.data) > 0:
                last_time = last_prashna.data[0].get("created_at")

            cooldown = check_cooldown(last_time, cooldown_hours=PRASHNA_COOLDOWN_HOURS)

            if not cooldown["allowed"]:
                return JSONResponse(status_code=429, content={
                    "error": "cooldown",
                    "message": cooldown.get("message", "Please wait before asking another question."),
                    "cooldown_until": cooldown.get("cooldown_until"),
                    "remaining_seconds": cooldown.get("remaining_seconds", 0),
                })
        except Exception as e:
            logger.warning(f"Cooldown check failed (table may not exist): {e}")

        # ─── 2. Fetch Chart Data ───
        chart_row = supabase.table("charts") \
            .select("user_id, chart_data, jaimini_data, lal_kitab_data, first_name, current_country, lagna_sign, latitude, longitude") \
            .eq("id", chart_id) \
            .single() \
            .execute()

        if not chart_row.data:
            return JSONResponse(status_code=404, content={"error": "Chart not found"})

        chart_data = chart_row.data
        jaimini_data = chart_data.get("jaimini_data")
        # Get current dasha from dasha_periods table (Vimsottari MD + AD)
        natal_dasha = "unknown"
        try:
            _dasha_rows = supabase.table("dasha_periods") \
                .select("planet_or_sign, system, type, level") \
                .eq("chart_id", chart_id) \
                .eq("system", "vimsottari") \
                .lte("start_date", datetime.now(timezone.utc).isoformat()) \
                .gte("end_date", datetime.now(timezone.utc).isoformat()) \
                .order("level") \
                .execute()
            if _dasha_rows.data:
                _md = next((r["planet_or_sign"] for r in _dasha_rows.data if r.get("level") == 1), None)
                _ad = next((r["planet_or_sign"] for r in _dasha_rows.data if r.get("level") == 2), None)
                if _md and _ad:
                    natal_dasha = f"{_md}-{_ad}"
                elif _md:
                    natal_dasha = _md
        except Exception as _de:
            logger.warning(f"Dasha lookup failed (non-blocking): {_de}")
        first_name = chart_data.get("first_name", "User")
        current_country = chart_data.get("current_country") or chart_data.get("country_code") or ""

        if isinstance(jaimini_data, str):
            try:
                jaimini_data = json.loads(jaimini_data)
            except Exception:
                jaimini_data = None

        # ─── 3. Coordinates: request > chart > default ───
        lat = request.lat
        lng = request.lng
        if not lat or lat == 28.6139:
            lat = chart_data.get("latitude") or 40.8215
        if not lng or lng == 77.2090:
            lng = chart_data.get("longitude") or -73.9876

        # ─── 4. Run Prashna Engine (Ithasala + 4-step scoring) ───
        timestamp = datetime.now(timezone.utc)
        locale = "IN" if current_country and current_country.upper() in ["IN", "INDIA"] else "global"


        # ═══ E1: Emotional tone for Prashna ═══
        _prashna_emotion = detect_emotional_tone(question) if 'detect_emotional_tone' in dir() else "neutral"
        _prashna_time = get_time_modifier(datetime.now(timezone.utc).hour) if 'get_time_modifier' in dir() else "normal"
        _prashna_emotion_block = build_emotional_prompt_block(_prashna_emotion, _prashna_time) if 'build_emotional_prompt_block' in dir() else ""

        engine_result = run_prashna_engine(
            question=question,
            lat=lat,
            lng=lng,
            timestamp=timestamp,
            jaimini_data=jaimini_data,
            natal_dasha=natal_dasha,
            natal_chart_data=chart_data.get("chart_data") if chart_data else None,
            user_name=first_name or "User",
            locale=locale,
        )

        # ─── 5. Call Claude to explain the verdict ───
        # Append emotional tone to prashna prompt
        _prashna_prompt = engine_result.get("claude_prompt", "")
        if _prashna_emotion_block:
            _prashna_prompt += _prashna_emotion_block

        explanation = ""
        try:
            result_tuple = await call_llm(
                prompt=question,
                system_override=_prashna_prompt,
            )
            explanation = result_tuple[0] if isinstance(result_tuple, tuple) else result_tuple
        except Exception as claude_err:
            logger.error(f"Claude call failed for prashna: {claude_err}")
            bd = engine_result["breakdown"]
            explanation = (
                f"{engine_result['verdict']} ({engine_result['score']}%). "
                f"{bd['ithasala'].get('reason', '')}. "
                f"Timing: {engine_result['timing']}."
            )

        # ─── 6. Remedy Card ───
        wp = engine_result.get("weakest_planet", {})
        if locale == "IN":
            _rem_map = {
                "Sun": "Offer water to the Sun at sunrise. Donate wheat on Sundays.",
                "Moon": "Wear white on Mondays. Keep a silver item with you.",
                "Mercury": "Feed green vegetables to a cow. Donate on Wednesdays.",
                "Venus": "Donate white clothes on Fridays. Offer white flowers.",
                "Mars": "Donate red lentils on Tuesdays. Serve with physical effort.",
                "Jupiter": "Donate yellow items on Thursdays. Respect your teachers.",
                "Saturn": "Donate mustard oil on Saturdays. Serve the elderly.",
            }
        else:
            _rem_map = {
                "Sun": "Express confidence in one decision today. Lead from the front.",
                "Moon": "Practice emotional grounding — 5 minutes of stillness before any big call.",
                "Mercury": "Write your intention down. Clarity comes through articulation.",
                "Venus": "Express appreciation to someone who supports you this week.",
                "Mars": "Channel energy into physical action — exercise before the decision.",
                "Jupiter": "Express gratitude to a mentor or teacher this week.",
                "Saturn": "Commit to one disciplined action. Follow through completely.",
            }
        remedy = {
            "planet": wp.get("planet", "Saturn"),
            "practice": _rem_map.get(wp.get("planet", "Saturn"), "Take one deliberate action this week."),
            "why": f"{wp.get('planet', 'Saturn')} needs strengthening — {', '.join(wp.get('reasons', ['general']))}",
        }

        # ─── 7. Log to prashna_log ───
        try:
            supabase.table("prashna_log").insert({
                "chart_id": chart_id,
                "question": question,
                "domain": engine_result.get("domain"),
                "verdict": engine_result["verdict"],
                "score": engine_result["score"],
                "label": engine_result["label"],
                "timing": engine_result["timing"],
                "explanation": explanation,
                "breakdown": json.dumps(engine_result["breakdown"], default=str),
                "prashna_chart": json.dumps(engine_result["prashna_chart"], default=str),
                "weakest_planet": wp.get("planet"),
                "cooldown_until": engine_result["cooldown_until"],
                "proof_bars": engine_result.get("proof_bars"),
                "domain_audit": engine_result.get("domain_audit"),
                "confluence": engine_result.get("confluence"),
            }).execute()
        except Exception as log_err:
            logger.warning(f"Failed to log prashna (non-blocking): {log_err}")

        # ─── 7b. Save to messages table (persistent chat history) ───
        try:
            _prashna_user_id = chart_data.get("user_id") or chart_id
            # Find or create a conversation for this chart's oracle questions
            _oracle_conv = supabase.table("conversations") \
                .select("id") \
                .eq("chart_id", chart_id) \
                .eq("concern", "oracle") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()

            if _oracle_conv.data:
                _oracle_conv_id = _oracle_conv.data[0]["id"]
                supabase.table("conversations").update({
                    "preview": f"Oracle: {engine_result['verdict']} ({engine_result['score']}%)",
                    "last_message_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", _oracle_conv_id).execute()
            else:
                _new_conv = supabase.table("conversations").insert({
                    "user_id": _prashna_user_id,
                    "chart_id": chart_id,
                    "title": "Prashna Oracle",
                    "preview": f"Oracle: {engine_result['verdict']} ({engine_result['score']}%)",
                    "concern": "oracle",
                }).execute()
                _oracle_conv_id = _new_conv.data[0]["id"]

            # Get next sequence number
            _seq_res = supabase.table("messages") \
                .select("sequence_number") \
                .eq("conversation_id", _oracle_conv_id) \
                .order("sequence_number", desc=True) \
                .limit(1) \
                .execute()
            _last_seq = _seq_res.data[0]["sequence_number"] if _seq_res.data else 0

            # User question message
            supabase.table("messages").insert({
                "conversation_id": _oracle_conv_id,
                "user_id": _prashna_user_id,
                "role": "user",
                "sequence_number": _last_seq + 1,
                "content": question,
                "concern": engine_result.get("domain", "general"),
            }).execute()

            # Oracle verdict message
            _verdict_content = (
                f"[ORACLE VERDICT] {engine_result['verdict']} ({engine_result['score']}%)\n"
                f"Domain: {engine_result['domain']}\n"
                f"Timing: {engine_result['timing']}\n\n"
                f"{explanation}\n\n"
                f"Remedy: {remedy.get('practice', '')}"
            )
            supabase.table("messages").insert({
                "conversation_id": _oracle_conv_id,
                "user_id": _prashna_user_id,
                "role": "assistant",
                "sequence_number": _last_seq + 2,
                "content": _verdict_content,
                "concern": engine_result.get("domain", "general"),
                "confidence": engine_result["score"] / 100.0,
                "full_response": {
                    "type": "prashna_verdict",
                    "verdict": engine_result["verdict"],
                    "score": engine_result["score"],
                    "domain": engine_result["domain"],
                    "timing": engine_result["timing"],
                    "proof_bars": engine_result.get("proof_bars"),
                    "domain_audit": engine_result.get("domain_audit"),
                    "cooldown_until": engine_result.get("cooldown_until"),
                },
            }).execute()

            print(f"[prashna] Saved to messages table conv={_oracle_conv_id}")
        except Exception as _msg_err:
            print(f"[prashna] Messages save failed (non-fatal): {_msg_err}")

        # ─── 8. Also save to legacy prashna_readings for backward compat ───
        try:
            supabase.table("prashna_readings").insert({
                "chart_id":      chart_id,
                "question":      question,
                "question_type": engine_result.get("domain", "general"),
                "verdict":       engine_result["verdict"],
                "score":         engine_result["score"],
                "confidence":    engine_result["label"],
                "timing":        engine_result["timing"],
                "narrative":     explanation,
                "prashna_data":  {
                    "prashna_chart":  engine_result["prashna_chart"],
                    "lagna":          engine_result["prashna_chart"].get("lagna_sign"),
                    "moon_nakshatra": engine_result["prashna_chart"].get("moon_nakshatra"),
                    "yes_factors":    [],
                    "no_factors":     [],
                },
            }).execute()
        except Exception:
            pass

        # ─── 9. Return Response ───
        return {
            "verdict":       engine_result["verdict"],
            "score":         engine_result["score"],
            "label":         engine_result["label"],
            "confidence":    engine_result["label"],
            "domain":        engine_result["domain"],
            "timing":        engine_result["timing"],
            "explanation":   explanation,
            "narrative":     explanation,
            "remedy":        remedy,
            "breakdown": {
                "lagna_strength":   engine_result["breakdown"]["lagna_strength"]["score"],
                "lord_connection":  engine_result["breakdown"]["lord_connection"]["score"],
                "ithasala": {
                    "type":   engine_result["breakdown"]["ithasala"]["type"],
                    "score":  engine_result["breakdown"]["ithasala"]["score"],
                    "aspect": engine_result["breakdown"]["ithasala"].get("aspect"),
                },
                "moon_validation":  engine_result["breakdown"]["moon_validation"]["score"],
                "void_of_course":   engine_result["breakdown"].get("void_of_course", {}).get("void_of_course", False),
                "navamsa_genuine":  engine_result["breakdown"].get("navamsa_genuineness", {}).get("genuine", True),
                "mutual_reception": engine_result["breakdown"]["mutual_reception"].get("found", False),
                "edge_yoga":        engine_result["breakdown"]["edge_yoga"]["yoga"] if engine_result["breakdown"].get("edge_yoga") else None,
                "jaimini_locks":    engine_result["breakdown"]["jaimini_locks"],
            },
            "prashna_chart":  engine_result["prashna_chart"],
            "cooldown_until": engine_result["cooldown_until"],
            "natal_context":  engine_result["natal_context"],
            # Legacy fields for backward compatibility
            "question_type":  engine_result.get("domain", "general"),
            "lagna":          engine_result["prashna_chart"].get("lagna_sign"),
            "moon_nakshatra": engine_result["prashna_chart"].get("moon_nakshatra"),
            "yes_factors":    [],
            "no_factors":     [],
            "analysis":       {"explanation": explanation},
            "proof_bars":     engine_result.get("proof_bars"),
            "domain_audit":   engine_result.get("domain_audit"),
            "confluence":     engine_result.get("confluence"),
        }

    except Exception as e:
        logger.error(f"Prashna engine error: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={
            "error": "Prashna engine failed",
            "detail": str(e),
        })


class PrashnaFollowupRequest(BaseModel):
    session_id:  str
    question:    str
    language:    Optional[str] = "en"

@app.post("/api/v1/prashna/followup")
async def prashna_followup(request: PrashnaFollowupRequest):
    """
    Follow-up question on an existing Prashna session.
    REUSES the same chart — no new chart cast.
    One Prashna chart = one session = unlimited follow-ups.
    """
    # Load session from DB
    res = supabase.table("prashna_readings").select("*").eq(
        "id", request.session_id
    ).execute()

    if not res.data:
        raise HTTPException(404, "Prashna session not found")

    row = res.data[0]

    # Reconstruct session object
    session = {
        "session_id":    request.session_id,
        "question":      row.get("question",""),
        "question_type": row.get("question_type",""),
        "asked_at":      str(row.get("created_at","")),
        "prashna_chart": row.get("prashna_data",{}).get("prashna_chart",{}),
        "analysis": {
            "score":       row.get("score", 50),
            "verdict":     row.get("verdict",""),
            "yes_factors": row.get("prashna_data",{}).get("yes_factors",[]),
            "no_factors":  row.get("prashna_data",{}).get("no_factors",[]),
            "explanation": "",
        },
        "verdict": row.get("verdict",""),
        "score":   row.get("score", 50),
    }

    # Analyze follow-up using same chart
    followup_result = analyze_prashna_followup(session, request.question)

    # Generate LLM narrative
    narrative = ""
    try:
        llm_prompt = followup_result.get("llm_prompt","")
        system_prompt = (
            "You are Antar answering a follow-up Prashna question. "
            "The SAME chart is being reused — no new chart cast. "
            "Reference the original question and verdict. "
            "Answer the follow-up specifically. "
            "Plain language only — no Sanskrit terms. Under 150 words."
        )
        narrative = await call_llm(
            prompt=llm_prompt,
            system_override=system_prompt,
            language=request.language,
            max_tokens=300,
        )
    except Exception as _le:
        narrative = followup_result.get("verdict","")

    # Save follow-up to DB
    try:
        supabase.table("prashna_followups").insert({
            "session_id":      request.session_id,
            "question":        request.question,
            "followup_type":   followup_result.get("followup_type",""),
            "verdict":         followup_result.get("verdict",""),
            "narrative":       narrative,
            "chart_reused_from": session.get("asked_at",""),
        }).execute()
    except Exception:
        pass

    return {
        "session_id":     request.session_id,
        "original_question": session["question"],
        "original_verdict":  session["verdict"],
        "followup_question": request.question,
        "followup_type":  followup_result.get("followup_type",""),
        "verdict":        followup_result.get("verdict",""),
        "narrative":      narrative,
        "chart_note":     f"Using same chart from {session['asked_at'][:16]} — Prashna principle: one question, one chart",
    }

@app.get("/api/v1/prashna/session/{session_id}")
async def get_prashna_session(session_id: str):
    """Get full Prashna session with all follow-ups."""
    res = supabase.table("prashna_readings").select("*").eq("id",session_id).execute()
    if not res.data:
        raise HTTPException(404, "Session not found")

    followups = supabase.table("prashna_followups").select("*").eq(
        "session_id", session_id
    ).order("created_at").execute()

    return {
        "session":    res.data[0],
        "followups":  followups.data if followups.data else [],
        "total_questions": 1 + len(followups.data if followups.data else []),
    }




@app.post("/api/v1/debug/context")
async def debug_context(request: dict):
    """Debug endpoint — returns context build result for a chart+concern."""
    chart_id = request.get("chart_id")
    concern  = request.get("concern","career")
    question = request.get("question","test")

    res = supabase.table("charts").select("chart_data,birth_date,gender,name").eq("id",chart_id).execute()
    if not res.data:
        return {"error":"chart not found"}

    row        = res.data[0]
    chart_data = row["chart_data"]
    birth_date = row.get("birth_date","")
    name       = row.get("name","")
    fname      = name.split()[0] if name else ""
    gender     = row.get("gender","")

    # Get dashas
    dasha_rows = supabase.table("dasha_periods").select("*").eq("chart_id",chart_id).eq("system","vimsottari").execute().data
    dashas_list = [{
        "lord_or_sign": r.get("planet_or_sign"),
        "level":        r.get("type"),
        "start_date":   str(r.get("start_date","")),
        "end_date":     str(r.get("end_date","")),
    } for r in dasha_rows]

    dashas = {"vimsottari": dashas_list}

    try:
        from antar_engine.chart_context_builder import build_complete_context
        from antar_engine.lal_kitab_engine import calculate_lal_kitab_analysis
        from antar_engine.transits_engine import calculate_current_transits

        lk = calculate_lal_kitab_analysis(
            chart_data.get("planets",{}),
            chart_data.get("lagna",{}).get("sign","") if isinstance(chart_data.get("lagna"),dict) else ""
        )
        tr = calculate_current_transits(chart_data)

        ctx = build_complete_context(
            chart_data=chart_data, dashas=dashas,
            birth_date=birth_date, first_name=fname,
            gender=gender, concern=concern, question=question,
            lk_analysis=lk, transit_data=tr,
            yogas=chart_data.get("yogas",[]),
            divisional_charts=chart_data.get("divisional_charts",{}),
        )
        return {
            "concern":     concern,
            "context_len": len(ctx),
            "context_ok":  len(ctx) > 500,
            "dashas_len":  len(dashas_list),
            "preview":     ctx[:500],
        }
    except Exception as e:
        import traceback
        return {
            "concern": concern,
            "error":   str(e),
            "trace":   traceback.format_exc(),
        }




# ── DAILY SIGNAL ──────────────────────────────────────────────────
@app.post("/api/v1/daily-signal")
@app.get("/api/v1/daily-signal/{chart_id}")
async def get_daily_signal_endpoint(chart_id: str = None, request: dict = {}):
    cid = chart_id or (request.get("chart_id") if request else None)
    if not cid:
        raise HTTPException(400, "chart_id required")
    try:
        from antar_engine.daily_prediction_engine import generate_daily_signal
        from antar_engine.daily_panchanga import calculate_panchanga, format_daily_for_user
        res = supabase.table("charts").select("chart_data,birth_date,name,gender,latitude,longitude").eq("id",cid).execute()
        if not res.data: raise HTTPException(404,"Chart not found")
        row = res.data[0]
        cd  = row["chart_data"]
        dashas = get_dashas_for_chart(cid) if callable(get_dashas_for_chart) else []
        dashas_dict = {"vimsottari":dashas} if isinstance(dashas,list) else dashas
        name = row.get("name","")
        result = await generate_daily_signal(
            natal_chart=cd, dashas=dashas_dict,
            birth_date=row.get("birth_date",""),
            chart_id=cid,
            first_name=name.split()[0] if name else "",
            gender=row.get("gender",""),
        )
        lat = float(row.get("latitude",28.6) or 28.6)
        lng = float(row.get("longitude",77.2) or 77.2)
        panchanga = calculate_panchanga(lat=lat, lng=lng)
        formatted  = format_daily_for_user(panchanga)
        result.update({
            "panchanga":   formatted,
            "rahu_kalam":  panchanga.get("rahu_kalam",""),
            "abhijit":     panchanga.get("abhijit_muhurta",""),
            "lucky_hours": panchanga.get("lucky_hours",{}),
            "do_today":    panchanga.get("do_today",[]),
            "dont_today":  panchanga.get("dont_today",[]),
            "day_color":   panchanga.get("day_color",""),
            "day_number":  panchanga.get("day_number",""),
            "day_mantra":  panchanga.get("day_mantra",""),
            "tithi":       panchanga.get("tithi",""),
            "yoga":        panchanga.get("yoga",""),
        })
        return result
    except HTTPException: raise
    except Exception as e:
        print(f"[daily-signal] Error for chart {cid}: {e}")
        import traceback; traceback.print_exc()
        return {
            "status": "error",
            "chart_id": cid,
            "signal_text": "Your signal is being computed. Check back in a moment.",
            "field": None,
            "friction": None,
            "panchanga": {},
            "error": str(e),
        }


# ── MUHURTA ───────────────────────────────────────────────────────
@app.post("/api/v1/muhurta/best-times")
async def get_muhurta_endpoint(request: dict):
    chart_id = request.get("chart_id")
    event    = request.get("event","general")
    if not chart_id: raise HTTPException(400,"chart_id required")
    try:
        from antar_engine.timing_engine import timing_insights
        res = supabase.table("charts").select("chart_data").eq("id",chart_id).execute()
        if not res.data: raise HTTPException(404,"Chart not found")
        cd = res.data[0]["chart_data"]
        dashas = get_dashas_for_chart(chart_id) if callable(get_dashas_for_chart) else []
        dashas_dict = {"vimsottari":dashas} if isinstance(dashas,list) else dashas
        MUHURTA_RULES = {
            "marriage":       {"best_day":"Wednesday or Thursday or Friday","note":"Start during waxing moon"},
            "business_start": {"best_day":"Wednesday or Thursday","note":"Shukla Paksha preferred"},
            "property_purchase":{"best_day":"Tuesday or Saturday","note":"4th house lord dasha ideal"},
            "travel":         {"best_day":"Wednesday or Thursday","note":"Avoid Ashlesha nakshatra"},
            "surgery":        {"best_day":"Tuesday","note":"Avoid Moon in body part sign"},
            "investment":     {"best_day":"Thursday or Friday","note":"Jupiter transit over 2nd/11th"},
        }
        rules = MUHURTA_RULES.get(event, MUHURTA_RULES["business_start"])
        vim = dashas_dict.get("vimsottari",[])
        current_dasha = ""
        from datetime import datetime
        now = datetime.utcnow()
        for row in vim:
            level = row.get("level") or row.get("type","")
            if level != "mahadasha": continue
            try:
                sd = datetime.strptime(str(row.get("start_date",""))[:10],"%Y-%m-%d")
                ed = datetime.strptime(str(row.get("end_date",""))[:10],"%Y-%m-%d")
                if sd <= now <= ed:
                    current_dasha = row.get("lord_or_sign") or row.get("planet_or_sign","")
                    break
            except: pass
        return {
            "chart_id":     chart_id,
            "event":        event,
            "current_dasha":current_dasha,
            "muhurta_rules":rules,
            "general_advice": f"For {event}: best on {rules.get('best_day','Thursday')}. {rules.get('note','')}",
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500, f"Muhurta error: {e}")


# ── VARSHPHAL ─────────────────────────────────────────────────────
@app.post("/api/v1/varshphal/annual")
async def get_varshphal_endpoint(request: dict):
    chart_id = request.get("chart_id")
    year     = request.get("year", datetime.utcnow().year)
    if not chart_id: raise HTTPException(400,"chart_id required")
    try:
        from datetime import date
        res = supabase.table("charts").select("chart_data,birth_date").eq("id",chart_id).execute()
        if not res.data: raise HTTPException(404,"Chart not found")
        row  = res.data[0]
        cd   = row["chart_data"]
        born = date.fromisoformat(str(row.get("birth_date","1970-01-01"))[:10])
        age  = year - born.year
        day_lords = ["Moon","Mars","Mercury","Jupiter","Venus","Saturn","Sun"]
        try:
            last_bday = born.replace(year=year)
            if last_bday > date.today(): last_bday = born.replace(year=year-1)
        except: last_bday = date(year, born.month, born.day)
        year_lord = day_lords[last_bday.weekday()]
        year_lord_house = cd.get("planets",{}).get(year_lord,{}).get("house",0)
        THEMES = {
            "Sun":"authority and career","Moon":"emotions and public life",
            "Mars":"action and property","Mercury":"communication and business",
            "Jupiter":"expansion and wisdom","Venus":"relationships and luxury",
            "Saturn":"discipline and karma",
        }
        return {
            "chart_id":   chart_id,
            "year":       year,
            "age":        age,
            "year_lord":  year_lord,
            "year_lord_house": year_lord_house,
            "year_quality": "good" if year_lord_house in [1,4,5,9,10,11] else "challenging" if year_lord_house in [6,8,12] else "neutral",
            "summary": f"Year {year} ruled by {year_lord} in house {year_lord_house}. Theme: {THEMES.get(year_lord,'')}.",
            "favorable_areas": THEMES.get(year_lord,"").split(" and "),
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500, f"Varshphal error: {e}")


# ── TRANSIT ALERTS ────────────────────────────────────────────────
@app.post("/api/v1/transit-alerts")
@app.get("/api/v1/transit-alerts/{chart_id}")
async def get_transit_alerts_endpoint(chart_id: str = None, request: dict = {}):
    cid = chart_id or (request.get("chart_id") if request else None)
    if not cid: raise HTTPException(400,"chart_id required")
    try:
        from antar_engine.transit_alerts_engine import generate_all_active_alerts, format_alerts_for_api
        from antar_engine.transits_engine import calculate_current_transits
        res = supabase.table("charts").select("chart_data").eq("id",cid).execute()
        if not res.data: raise HTTPException(404,"Chart not found")
        cd = res.data[0]["chart_data"]
        tr = calculate_current_transits(cd)
        alerts = generate_all_active_alerts(cd, tr)
        formatted = format_alerts_for_api(alerts)
        return {
            "chart_id":    cid,
            "alert_count": len(formatted),
            "alerts":      formatted,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500, f"Transit alerts error: {e}")








@app.get("/api/v1/debug-predict-context/{chart_id}")
async def debug_predict_context(
    chart_id: str,
    question: str = "What is my career direction for 2026?"
):
    """Shows exact JSON sent to Claude for a predict call."""
    import json as _dj
    try:
        from antar_engine.chart_context_builder_json import build_chart_context_json
        ctx = await build_chart_context_json(
            chart_id=chart_id,
            question=question,
            concern="general",
            language="en",
            supabase=supabase,
        )
        # Count tokens
        ctx_str = _dj.dumps(ctx, indent=2, default=str)
        token_estimate = len(ctx_str.split()) * 1.3
        return {
            "token_estimate": int(token_estimate),
            "char_count": len(ctx_str),
            "top_level_keys": list(ctx.keys()) if isinstance(ctx, dict) else [],
            "jaimini_present": bool((ctx.get("jaimini") or {}) if isinstance(ctx, dict) else False),
            "lal_kitab_present": bool((ctx.get("lal_kitab") or {}) if isinstance(ctx, dict) else False),
            "transits_present": bool((ctx.get("transits") or {}) if isinstance(ctx, dict) else False),
            "d9_present": bool((ctx.get("divisional_charts") or {}).get("d9") if isinstance(ctx, dict) else False),
            "varshaphal_present": bool((ctx.get("varshaphal") or {}) if isinstance(ctx, dict) else False),
            "full_context": ctx,
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()[:500]}

# --- JAIMINI BACKFILL ENDPOINT ---
@app.get("/api/v1/backfill-jaimini/{chart_id}")
async def backfill_jaimini(chart_id: str):
    try:
        from antar_engine.jaimini_engine import (
            calculate_jaimini_analysis,
            jaimini_to_db_json,
        )
        cr = supabase.table("charts").select("chart_data, birth_date").eq("id", chart_id).single().execute()
        if not cr.data:
            return {"error": "Chart not found"}
        cd = cr.data.get("chart_data", {})
        if isinstance(cd, str):
            import json as _bjson
            cd = _bjson.loads(cd)
        _bd = str(cr.data.get("birth_date", cd.get("birth_date", "1990-01-01")))[:10]
        _lagna_obj3 = cd.get("lagna", {})
        SIGNS_BF = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
        _raw_sign3 = _lagna_obj3.get("sign_num", _lagna_obj3.get("sign_index", _lagna_obj3.get("sign", 0))) if isinstance(_lagna_obj3, dict) else 0
        _lagna_sign3 = SIGNS_BF.index(_raw_sign3) if isinstance(_raw_sign3, str) and _raw_sign3 in SIGNS_BF else int(_raw_sign3 or 0)
        _planets3 = cd.get("planets", {})
        _d9_data3 = (cd.get("divisional_charts", {}).get("d9") or cd.get("divisional_charts", {}).get("D9") or {}).get("planets", {})
        if not _d9_data3:
            _d9_data3 = cd.get("d9_planets", {})
        _jaimini_result = calculate_jaimini_analysis(
            lagna_sign=_lagna_sign3,
            planets_dict=_planets3,
            d9_planets_dict=_d9_data3 or {},
            birth_date_str=_bd,
        )
        _jaimini_db = _jaimini_result["db_json"]
        _jaimini_db.pop("computed_at", None)
        supabase.table("charts").update({
            "jaimini_data": _jaimini_db
        }).eq("id", chart_id).execute()
        return {"status": "ok", "message": "Jaimini data backfilled for " + chart_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
# --- END JAIMINI BACKFILL ---

# --- EXECUTIVE SUMMARY ENDPOINT (auto-inserted) ---

# ─── Plain language translation for executive-summary dashboard signal ───────

_INSTRUMENT_TO_DOMAIN = {
    "SYSTEM_VITALS":      "salud",
    "CAPITAL_RESERVES":   "finanzas",
    "ACTION_CAPACITY":    "accion",
    "REAL_ESTATE_RADAR":  "hogar",
    "CREATION_ENGINE":    "creatividad",
    "CONFLICT_SHIELD":    "conflictos",
    "ALLIANCE_SYNC":      "relaciones",
    "CAPITAL_RUNWAY":     "transformacion",
    "FORTUNE_VECTOR":     "oportunidad",
    "AUTHORITY_ENGINE":   "carrera",
    "REVENUE_PIPELINE":   "ingresos",
    "GLOBAL_VECTOR":      "viajes",
}

_DOMAIN_NAMES_ES = {
    "carrera":        "Carrera",
    "ingresos":       "Ingresos",
    "relaciones":     "Relaciones",
    "finanzas":       "Finanzas",
    "salud":          "Salud y energía",
    "accion":         "Iniciativa",
    "hogar":          "Hogar y raíces",
    "creatividad":    "Creatividad",
    "conflictos":     "Manejo de conflictos",
    "transformacion": "Transformación",
    "oportunidad":    "Oportunidad",
    "viajes":         "Viajes y expansión",
}

_STATUS_TO_ES = {
    "ACTIVE":    "activo",
    "PREPARING": "preparando",
    "FRICTION":  "bajo presión",
    "PEAK":      "en su mejor momento",
    "DORMANT":   "dormido",
}

def _build_plain_dashboard_signal(instruments, language="es"):
    """Dict-based: instruments keyed by slug (vitals, reserves, action...)"""
    _NAMES_ES = {
        "vitals": "Salud y Energia", "reserves": "Ahorros y Riqueza",
        "action": "Valentia e Iniciativa", "real_estate": "Hogar y Raices",
        "creation": "Creatividad y Proyectos", "conflict": "Retos y Legal",
        "alliance": "Socios y Alianzas", "runway": "Transformacion",
        "fortune": "Oportunidad y Suerte", "authority": "Carrera y Autoridad",
        "revenue": "Ingresos y Negocios", "global_vec": "Viajes y Expansion",
        "global": "Viajes y Expansion",
    }
    if not instruments:
        return {"focus_area": "Energia general", "focus_message": "Tu senal se esta calculando.", "do_this": "Mantente en tu rutina hoy.", "caution_area": None, "caution_message": None, "avoid_this": None, "open_window": None, "open_window_message": None, "urgency": "low"}
    # Normalize: handle both dict and list
    if isinstance(instruments, dict):
        items = [(k, float(v.get("signal_score") or v.get("blueprint_score") or 0), (v.get("signal_status") or v.get("verdict") or "DORMANT").upper()) for k, v in instruments.items()]
    else:
        items = [(v.get("name","x"), float(v.get("signal_score") or v.get("blueprint_score") or 0), (v.get("signal_status") or v.get("verdict") or "DORMANT").upper()) for v in instruments]
    items.sort(key=lambda x: x[1], reverse=True)
    def nme(k): return _NAMES_ES.get(k, k.replace("_"," ").title())
    focus_key = next((k for k,s,st in items if st in ("ACTIVE","PEAK")), items[0][0] if items else None)
    caution_key = next((k for k,s,st in items if st == "FRICTION"), None)
    window_key = next((k for k,s,st in items if st == "PREPARING" and k != focus_key), None)
    top = items[0][1] if items else 0
    urgency = "high" if (caution_key and top > 65) else "medium" if caution_key else "low"
    focus_st = next((st for k,s,st in items if k == focus_key), "ACTIVE")
    st_map = {"ACTIVE":"activa","PEAK":"en su mejor momento","PREPARING":"preparandose","FRICTION":"bajo presion","DORMANT":"dormida","POSITION":"preparandose"}
    if language == "es":
        fname = nme(focus_key) if focus_key else "Energia general"
        flabel = st_map.get(focus_st, "activa")
        suffix = " Es buen momento para avanzar." if focus_st in ("ACTIVE","PEAK") else " Se esta preparando." if focus_st=="PREPARING" else ""
        return {
            "focus_area": fname, "focus_status": flabel,
            "focus_message": f"Tu energia de {fname.lower()} esta {flabel}.{suffix}",
            "do_this": f"Pon atencion activa a {fname.lower()} esta semana.",
            "caution_area": nme(caution_key) if caution_key else None,
            "caution_message": f"{nme(caution_key)} esta bajo presion ahora." if caution_key else None,
            "avoid_this": f"Evita decisiones en {nme(caution_key).lower()} esta semana." if caution_key else None,
            "open_window": nme(window_key) if window_key else None,
            "open_window_message": f"Una oportunidad en {nme(window_key).lower()} se esta preparando." if window_key else None,
            "urgency": urgency,
        }
    fname = focus_key.replace("_"," ").title() if focus_key else "General energy"
    return {
        "focus_area": fname,
        "focus_message": f"Your {fname.lower()} energy is active. Good time to move forward.",
        "do_this": f"Give active attention to {fname.lower()} this week.",
        "caution_area": caution_key if caution_key else None,
        "caution_message": f"{caution_key} is under pressure." if caution_key else None,
        "avoid_this": f"Avoid major {caution_key} decisions this week." if caution_key else None,
        "open_window": window_key if window_key else None,
        "open_window_message": f"A {window_key} opportunity is opening." if window_key else None,
        "urgency": urgency,
    }


def _default_signal(language: str = "es") -> dict:
    if language == "es":
        return {
            "focus_area": "Energía general",
            "focus_status": "calculando",
            "focus_message": "Tu señal se está calculando. Vuelve en unos minutos.",
            "do_this": "Mantén tu rutina habitual hoy.",
            "caution_area": None,
            "caution_message": None,
            "avoid_this": None,
            "open_window": None,
            "open_window_message": None,
            "urgency": "low"
        }
    return {
        "focus_area": "General energy",
        "focus_status": "calculating",
        "focus_message": "Your signal is being calculated. Check back in a few minutes.",
        "do_this": "Maintain your usual routine today.",
        "caution_area": None,
        "caution_message": None,
        "avoid_this": None,
        "open_window": None,
        "open_window_message": None,
        "urgency": "low"
    }

@app.get("/api/v1/executive-summary/{chart_id}")
async def get_executive_summary(chart_id: str, language: str = "es"):
    try:
        from antar_engine.symptom_library import build_executive_summary
        from datetime import datetime as _exdt
        cr = supabase.table("charts").select("chart_data, jaimini_data, lal_kitab_data").eq("id", chart_id).single().execute()
        if not cr.data:
            return {"error": "Chart not found"}
        cd = cr.data.get("chart_data", {})
        if isinstance(cd, str):
            try:
                import json as _jjson
                cd = _jjson.loads(cd)
            except:
                cd = {}
        jd = cr.data.get("jaimini_data", {})
        if isinstance(jd, str):
            try:
                import json as _jjson
                jd = _jjson.loads(jd)
            except:
                jd = {}
        lk = cr.data.get("lal_kitab_data", {})
        if isinstance(lk, str):
            try:
                import json as _jjson
                lk = _jjson.loads(lk)
            except:
                lk = {}
        now_str = _exdt.utcnow().isoformat()
        dr = supabase.table("dasha_periods").select("planet_or_sign, level, end_date").eq("chart_id", chart_id).eq("system", "vimsottari").lte("start_date", now_str).gte("end_date", now_str).order("level").execute()
        dasha_list = dr.data if dr.data else []
        current_dasha = ""
        md_row = None
        ad_row = None
        for d in dasha_list:
            if d.get("level") == 1:
                md_row = d
            if d.get("level") == 2:
                ad_row = d
        if md_row:
            current_dasha = md_row["planet_or_sign"].strip()
            if ad_row:
                current_dasha = current_dasha + "-" + ad_row["planet_or_sign"].strip()
        result = build_executive_summary(cd, jd, lk, current_dasha, dasha_list)
        instruments = result.get("instruments", {})
        # Translate symptom text to plain language
        if language == "es":
            for k, inst in instruments.items():
                inst["symptom_plain"] = _translate_instrument_symptom_es(
                    inst.get("symptom",""), inst.get("signal_status",""), inst.get("name","")
                )
                # Also translate instrument name to Spanish
                ES_NAMES = {
                    "Marriage & Partners": "Socios y Alianzas",
                    "Income & Network": "Ingresos y Red",
                    "Home & Property": "Hogar y Propiedad",
                    "Career & Status": "Carrera y Autoridad",
                    "Children & Intelligence": "Creatividad e Inteligencia",
                    "Wealth & Savings": "Riqueza y Ahorros",
                    "Enemies & Legal": "Retos y Legal",
                    "Funding & Transformation": "Transformacion",
                    "Health & Identity": "Salud e Identidad",
                    "Fortune & Expansion": "Suerte y Expansion",
                    "Spirituality & Loss": "Espiritualidad",
                    "Courage & Initiative": "Valentia e Iniciativa",
                }
                if inst.get("name") in ES_NAMES:
                    inst["name_es"] = ES_NAMES[inst["name"]]
                else:
                    inst["name_es"] = inst.get("name", k)
        result["plain_signal"] = _build_plain_dashboard_signal(instruments, language)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
# --- END EXECUTIVE SUMMARY ENDPOINT ---



# ═══════════════════════════════════════════════════════════════════

@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables"""
    import os
    return {
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_url_length": len(os.getenv("SUPABASE_URL", "")),
        "supabase_key_exists": os.getenv("SUPABASE_SERVICE_ROLE_KEY") is not None,
        "supabase_key_length": len(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")),
    }


# ── Prediction Tracking Endpoints ─────────────────────────────────

@app.post("/api/v1/predictions/feedback")
async def submit_prediction_feedback(request: dict):
    """User submits yes/no/partial on a prediction claim."""
    from antar_engine.prediction_tracker import record_feedback
    correlation_id = request.get("correlation_id")
    status         = request.get("status")
    note           = request.get("note", "")
    if not correlation_id or status not in ("yes", "no", "partial", "skipped"):
        raise HTTPException(400, "correlation_id and valid status required")
    result = record_feedback(correlation_id, status, note, supabase)
    return {"success": True, "updated": result}


@app.get("/api/v1/predictions/pending-feedback/{chart_id}")
async def get_pending_feedback_endpoint(chart_id: str):
    """Return predictions ready for user verification (max 3)."""
    from antar_engine.prediction_tracker import get_pending_feedback
    items = get_pending_feedback(chart_id, supabase)
    return {"pending": items, "count": len(items)}


@app.get("/api/v1/predictions/accuracy/{chart_id}")
async def get_prediction_accuracy_endpoint(chart_id: str):
    """Return accuracy score — powers the trust badge."""
    from antar_engine.prediction_tracker import get_accuracy_score
    return get_accuracy_score(chart_id, supabase)


# ── Alert System Endpoints ────────────────────────────────────────

@app.get("/api/v1/alerts/{chart_id}")
async def get_alerts(chart_id: str, unread_only: bool = False):
    """Get personal alerts for a chart — powers in-app badge."""
    query = supabase.table("user_alerts").select("*").eq(
        "chart_id", chart_id
    ).is_("dismissed_at", "null").order("created_at", desc=True).limit(20)

    if unread_only:
        query = query.is_("read_at", "null")

    res = query.execute()
    alerts = res.data or []
    unread_count = sum(1 for a in alerts if not a.get("read_at"))
    return {"alerts": alerts, "unread_count": unread_count}


@app.post("/api/v1/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """Mark alert as read — clears badge."""
    from datetime import timezone
    supabase.table("user_alerts").update({
        "read_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", alert_id).execute()
    return {"success": True}


@app.post("/api/v1/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str):
    """Dismiss alert permanently."""
    from datetime import timezone
    supabase.table("user_alerts").update({
        "dismissed_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", alert_id).execute()
    return {"success": True}


@app.post("/api/v1/alerts/subscribe")
async def subscribe_to_alerts(request: dict):
    """Save email for alert delivery."""
    chart_id = request.get("chart_id")
    email    = request.get("email")
    if not chart_id or not email:
        raise HTTPException(400, "chart_id and email required")
    supabase.table("charts").update({"email": email}).eq("id", chart_id).execute()
    return {"success": True, "message": "You will receive personal transit alerts at " + email}


@app.post("/api/v1/alerts/run-check")
async def manual_alert_check(request: dict):
    """Manually trigger alert check — for testing."""
    secret = request.get("secret", "")
    if secret != os.getenv("ALERT_SECRET", "antar-alerts-2026"):
        raise HTTPException(403, "Invalid secret")
    from antar_engine.alert_engine import run_daily_alert_check
    stats = run_daily_alert_check(supabase)
    return {"success": True, "stats": stats}


# ── Daily Alert Scheduler ─────────────────────────────────────────
import asyncio
from datetime import datetime as _dt

async def _daily_alert_job():
    """Runs daily at 6am UTC — checks all charts for personal alerts."""
    import asyncio
    while True:
        try:
            now = _dt.utcnow()
            # Sleep until next 6am UTC
            target = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now >= target:
                target = target.replace(day=target.day + 1)
            sleep_secs = (target - now).total_seconds()
            await asyncio.sleep(sleep_secs)

            from antar_engine.alert_engine import run_daily_alert_check
            stats = run_daily_alert_check(supabase)
            print(f"[alerts] Daily check: {stats}")
        except Exception as e:
            print(f"[alerts] Scheduler error: {e}")
            await asyncio.sleep(3600)

@app.on_event("startup")
async def start_alert_scheduler():
    asyncio.create_task(_daily_alert_job())
    print("[startup] Alert scheduler started — runs daily 06:00 UTC")


# ── Subscription / Paywall Endpoints ─────────────────────────────

@app.get("/api/v1/subscription/{chart_id}")
async def get_subscription_status(chart_id: str):
    """Get subscription plan + this month\'s usage."""
    from antar_engine.subscription_engine import (
        get_subscription, get_usage, PLANS
    )
    sub   = get_subscription(chart_id, supabase)
    usage = get_usage(chart_id, supabase)
    plan  = sub.get("plan", "free")
    plan_data = PLANS.get(plan, PLANS["free"])
    return {
        "plan":            plan,
        "status":          sub.get("status", "active"),
        "is_paid":         plan != "free",
        "pred_used":       usage.get("pred_count", 0),
        "pred_limit":      plan_data["pred_limit"],
        "ask_used":        usage.get("ask_count", 0),
        "ask_limit":       plan_data["ask_limit"],
        "compat_used":     usage.get("compat_count", 0),
        "compat_limit":    plan_data["compat_limit"],
        "period_end":      sub.get("current_period_end"),
        "features":        plan_data["features"],
    }


@app.get("/api/v1/subscription/what-youre-missing/{chart_id}")
async def get_upgrade_hook(chart_id: str):
    """
    Personalized upgrade hook — what will this user miss
    if they don\'t upgrade? Powers the upgrade modal.
    """
    from antar_engine.subscription_engine import get_what_youre_missing
    return get_what_youre_missing(chart_id, supabase)


@app.post("/api/v1/subscription/verify")
async def verify_subscription(request: dict):
    """
    Verify payment and activate subscription.
    Called after Stripe/Razorpay payment succeeds.
    Body: { chart_id, plan, provider, provider_sub_id, period_end }
    """
    from antar_engine.subscription_engine import activate_subscription
    chart_id       = request.get("chart_id")
    plan           = request.get("plan", "seeker")
    provider       = request.get("provider", "stripe")
    provider_sub_id= request.get("provider_sub_id", "")
    period_end     = request.get("period_end", "")

    if not chart_id:
        raise HTTPException(400, "chart_id required")

    result = activate_subscription(
        chart_id=chart_id,
        plan=plan,
        provider=provider,
        provider_sub_id=provider_sub_id,
        period_end_iso=period_end,
        sb=supabase,
    )
    return {"success": True, "subscription": result}


@app.post("/api/v1/subscription/stripe-webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook — auto-activate on payment."""
    import json
    body = await request.body()
    try:
        event = json.loads(body)
        if event["type"] == "checkout.session.completed":
            session  = event["data"]["object"]
            chart_id = session.get("client_reference_id", "")
            sub_id   = session.get("subscription", "")
            if chart_id and sub_id:
                from antar_engine.subscription_engine import activate_subscription
                from datetime import timedelta
                period_end = (
                    datetime.now(timezone.utc) + timedelta(days=30)
                ).isoformat()
                activate_subscription(
                    chart_id=chart_id,
                    plan="seeker",
                    provider="stripe",
                    provider_sub_id=sub_id,
                    period_end_iso=period_end,
                    sb=supabase,
                )
        return {"received": True}
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Payment Checkout Endpoints ────────────────────────────────────

@app.post("/api/v1/payments/stripe/create-checkout")
async def create_stripe_checkout_session(request: dict):
    """
    Create Stripe checkout session.
    Body: { chart_id, plan_key, success_url?, cancel_url? }
    plan_key: seeker_monthly | seeker_annual | navigator_monthly
    """
    from antar_engine.payment_engine import create_stripe_checkout
    chart_id    = request.get("chart_id", "")
    plan_key    = request.get("plan_key", "seeker_monthly")
    success_url = request.get("success_url", "https://antar.world/upgrade/success")
    cancel_url  = request.get("cancel_url",  "https://antar.world/upgrade")

    if not chart_id:
        raise HTTPException(400, "chart_id required")

    # Sprint L: Country-aware pricing — pass country for LATAM local currency
    country_code = request.get("current_country", "US")
    result = create_stripe_checkout(chart_id, plan_key, success_url, cancel_url, country_code=country_code)
    if result.get("error"):
        raise HTTPException(500, f"Stripe error: {result['error']}")
    return result


@app.post("/api/v1/payments/stripe/verify")
async def verify_stripe_payment(request: dict):
    """
    Verify Stripe checkout after redirect back from Stripe.
    Body: { session_id, chart_id }
    """
    from antar_engine.payment_engine import verify_stripe_session
    from antar_engine.subscription_engine import activate_subscription

    session_id = request.get("session_id", "")
    chart_id   = request.get("chart_id", "")

    if not session_id:
        raise HTTPException(400, "session_id required")

    result = verify_stripe_session(session_id)
    if result.get("error"):
        raise HTTPException(500, result["error"])
    if not result.get("verified"):
        raise HTTPException(402, "Payment not completed")

    # Activate subscription
    sub = activate_subscription(
        chart_id   = result["chart_id"] or chart_id,
        plan       = result["plan"],
        provider   = "stripe",
        provider_sub_id = result["sub_id"],
        period_end_iso  = result["period_end"],
        sb         = supabase,
    )
    return {"success": True, "plan": result["plan"], "subscription": sub}


@app.post("/api/v1/payments/stripe/webhook")
async def handle_stripe_webhook(request: Request):
    """Stripe webhook — handles all subscription lifecycle events."""
    import json
    from antar_engine.subscription_engine import activate_subscription
    body = await request.body()
    try:
        event = json.loads(body)
        event_type = event["type"]
        obj = event["data"]["object"]

        # ── NEW SUBSCRIPTION or PAYMENT COMPLETED ──
        if event_type in ("checkout.session.completed", "customer.subscription.created"):
            chart_id = (obj.get("client_reference_id") or
                        obj.get("metadata", {}).get("chart_id", ""))
            sub_id = (obj.get("subscription") or obj.get("id", ""))
            plan_key = obj.get("metadata", {}).get("plan", "seeker_monthly")
            plan = plan_key.split("_")[0]
            if chart_id:
                days = 366 if "annual" in plan_key or "yearly" in plan_key else 32
                period_end = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
                activate_subscription(
                    chart_id=chart_id, plan=plan,
                    provider="stripe", provider_sub_id=str(sub_id),
                    period_end_iso=period_end, sb=supabase,
                )
                print(f"[stripe webhook] Activated {plan} for {chart_id} (period: {days}d)")

        # ── SUBSCRIPTION UPDATED (plan change: monthly↔yearly, upgrade/downgrade) ──
        elif event_type == "customer.subscription.updated":
            chart_id = obj.get("metadata", {}).get("chart_id", "")
            sub_id = obj.get("id", "")
            # Get the new plan from the subscription items
            items = obj.get("items", {}).get("data", [])
            plan_key = obj.get("metadata", {}).get("plan", "")
            plan = plan_key.split("_")[0] if plan_key else ""
            # Check if subscription is still active
            status = obj.get("status", "")
            if chart_id and status in ("active", "trialing"):
                current_period_end = obj.get("current_period_end")
                if current_period_end:
                    from datetime import datetime as _dt
                    period_end = _dt.utcfromtimestamp(current_period_end).isoformat()
                else:
                    period_end = (datetime.now(timezone.utc) + timedelta(days=32)).isoformat()
                if plan:
                    activate_subscription(
                        chart_id=chart_id, plan=plan,
                        provider="stripe", provider_sub_id=str(sub_id),
                        period_end_iso=period_end, sb=supabase,
                    )
                    print(f"[stripe webhook] Updated {chart_id} to {plan} (period_end: {period_end})")
            elif chart_id and status in ("canceled", "unpaid", "past_due"):
                supabase.table("subscriptions").update({
                    "plan": "free", "is_paid": False,
                }).eq("chart_id", chart_id).execute()
                print(f"[stripe webhook] Downgraded {chart_id} to free (status: {status})")

        # ── SUBSCRIPTION CANCELLED ──
        elif event_type == "customer.subscription.deleted":
            chart_id = obj.get("metadata", {}).get("chart_id", "")
            if chart_id:
                supabase.table("subscriptions").update({
                    "plan": "free", "is_paid": False, "period_end": None,
                }).eq("chart_id", chart_id).execute()
                print(f"[stripe webhook] Cancelled {chart_id} → free")

        # ── RECURRING PAYMENT SUCCEEDED ──
        elif event_type == "invoice.payment_succeeded":
            sub_id = obj.get("subscription", "")
            chart_id = obj.get("subscription_details", {}).get("metadata", {}).get("chart_id", "")
            # Also check lines for metadata
            if not chart_id:
                lines = obj.get("lines", {}).get("data", [])
                for line in lines:
                    chart_id = line.get("metadata", {}).get("chart_id", "")
                    if chart_id:
                        break
            if chart_id and sub_id:
                # Extend period
                period_end = obj.get("period_end")
                if period_end:
                    from datetime import datetime as _dt
                    period_end_iso = _dt.utcfromtimestamp(period_end).isoformat()
                else:
                    period_end_iso = (datetime.now(timezone.utc) + timedelta(days=32)).isoformat()
                supabase.table("subscriptions").update({
                    "period_end": period_end_iso, "is_paid": True,
                }).eq("chart_id", chart_id).execute()
                print(f"[stripe webhook] Renewed {chart_id} (next: {period_end_iso})")

        # ── PAYMENT FAILED ──
        elif event_type == "invoice.payment_failed":
            chart_id = obj.get("subscription_details", {}).get("metadata", {}).get("chart_id", "")
            attempt = obj.get("attempt_count", 0)
            if chart_id:
                # After 3 failed attempts, Stripe cancels automatically
                # For now just log it — Stripe sends the user an email
                print(f"[stripe webhook] Payment failed for {chart_id} (attempt {attempt})")
                if attempt >= 3:
                    supabase.table("subscriptions").update({
                        "plan": "free", "is_paid": False,
                    }).eq("chart_id", chart_id).execute()
                    print(f"[stripe webhook] Downgraded {chart_id} after {attempt} failed payments")

        return {"received": True}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/v1/payments/razorpay/create-order")
async def create_razorpay_order_endpoint(request: dict):
    """
    Create Razorpay order for Indian payments.
    Body: { chart_id, plan_key }
    Returns order details for Razorpay JS checkout widget.
    """
    from antar_engine.payment_engine import create_razorpay_order
    chart_id = request.get("chart_id", "")
    plan_key = request.get("plan_key", "seeker_monthly")

    if not chart_id:
        raise HTTPException(400, "chart_id required")

    result = create_razorpay_order(chart_id, plan_key)
    if result.get("error"):
        raise HTTPException(500, f"Razorpay error: {result['error']}")
    return result


@app.post("/api/v1/payments/razorpay/verify")
async def verify_razorpay_payment_endpoint(request: dict):
    """
    Verify Razorpay payment after widget success callback.
    Body: { payment_id, order_id, signature, chart_id, plan_key }
    """
    from antar_engine.payment_engine import verify_razorpay_payment
    from antar_engine.subscription_engine import activate_subscription

    result = verify_razorpay_payment(
        payment_id = request.get("payment_id", ""),
        order_id   = request.get("order_id", ""),
        signature  = request.get("signature", ""),
        chart_id   = request.get("chart_id", ""),
        plan_key   = request.get("plan_key", "seeker_monthly"),
    )

    if result.get("error"):
        raise HTTPException(500, result["error"])
    if not result.get("verified"):
        raise HTTPException(402, f"Payment verification failed: {result.get('reason')}")

    sub = activate_subscription(
        chart_id        = result["chart_id"],
        plan            = result["plan"],
        provider        = "razorpay",
        provider_sub_id = result["sub_id"],
        period_end_iso  = result["period_end"],
        sb              = supabase,
    )
    return {"success": True, "plan": result["plan"], "subscription": sub}


@app.post("/api/v1/payments/razorpay/webhook")
async def handle_razorpay_webhook(request: Request):
    """Razorpay webhook — handle subscription renewals."""
    import json, hmac, hashlib
    body = await request.body()
    try:
        # Verify webhook signature
        secret    = os.getenv("RAZORPAY_KEY_SECRET", "").encode()
        signature = request.headers.get("x-razorpay-signature", "")
        digest    = hmac.new(secret, body, hashlib.sha256).hexdigest()

        if digest != signature:
            raise HTTPException(400, "Invalid signature")

        event = json.loads(body)
        if event.get("event") in ("payment.captured", "subscription.charged"):
            payload  = event.get("payload", {})
            payment  = payload.get("payment", {}).get("entity", {})
            notes    = payment.get("notes", {})
            chart_id = notes.get("chart_id", "")
            plan_key = notes.get("plan", "seeker_monthly")
            plan     = plan_key.split("_")[0]
            if chart_id:
                from antar_engine.subscription_engine import activate_subscription
                period_end = (
                    datetime.now(timezone.utc) + timedelta(days=32)
                ).isoformat()
                activate_subscription(
                    chart_id=chart_id, plan=plan,
                    provider="razorpay",
                    provider_sub_id=payment.get("id", ""),
                    period_end_iso=period_end, sb=supabase,
                )
        return {"received": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Remedies & Practices Endpoint ────────────────────────────────

@app.get("/api/v1/remedies/{chart_id}")
async def get_personal_remedies(
    chart_id: str,
    concern:  str = "general",
    question: str = "",
):
    """
    Returns 2-3 structured remedies specific to this chart right now.
    Each remedy includes WHY (diagnosis) + WHAT (practice) + HOW (exact instructions).
    Tied to active dasha + weak planets + current transits.
    """
    from antar_engine import remedy_selector
    from antar_engine.transits_engine import calculate_current_transits
    from datetime import date

    # Load chart
    res = supabase.table("charts").select(
        "chart_data,lal_kitab_data,birth_date,first_name,gender,"
        "career_stage,health_status,marital_status,lagna_sign"
    ).eq("id", chart_id).execute()

    if not res.data:
        raise HTTPException(404, "Chart not found")

    row         = res.data[0]
    chart_data  = row.get("chart_data", {})
    birth_date  = row.get("birth_date", "")
    first_name  = row.get("first_name", "") or "Explorer"

    if not chart_data or not chart_data.get("planets"):
        raise HTTPException(400, "Chart data incomplete")

    # Load dashas
    dasha_res = supabase.table("dasha_periods").select("*").eq(
        "chart_id", chart_id
    ).order("start_date").execute()
    dashas = {"vimsottari": dasha_res.data or []}

    # Get current dasha lord
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    current_md = current_ad = ""
    for d in dashas["vimsottari"]:
        try:
            sd = datetime.fromisoformat(str(d.get("start_date",""))[:10].replace("Z",""))
            ed = datetime.fromisoformat(str(d.get("end_date",""))[:10].replace("Z",""))
            if sd.date() <= now.date() <= ed.date():
                level  = d.get("level", 0)
                lord   = d.get("planet_or_sign","") or d.get("planet","") or d.get("lord","")
                system = d.get("system","vimsottari")
                if system == "vimsottari":
                    if level == 1:   current_md = lord
                    elif level == 2: current_ad = lord
        except Exception:
            pass

    # Build patra object for remedy personalisation
    class Patra:
        age          = (now.year - int(str(birth_date)[:4])) if birth_date else 35
        career_stage = row.get("career_stage","") or ""
        health_status= row.get("health_status","") or ""
        marital_status=row.get("marital_status","") or ""

    patra = Patra()

    # Select remedies
    remedy_objects = remedy_selector.select_remedies(
        supabase=supabase,
        chart_data=chart_data,
        dashas=dashas,
        transits={},
        user_age=patra.age,
        question=question or concern,
        patra=patra,
        limit=3,
    )

    # Build rich structured response
    planets     = chart_data.get("planets", {})
    lagna_sign  = chart_data.get("lagna", {}).get("sign", "")
    dasha_string= f"{current_md}-{current_ad}" if current_ad else current_md

    remedies = []
    for rem in remedy_objects:
        planet = rem.get("planet","")
        p_data = planets.get(planet, {})
        p_sign = p_data.get("sign","")
        p_house= p_data.get("house", 0)

        # Build WHY — the diagnosis
        priority_label = rem.get("priority_label","") or (
            "Amplify what's already working"
            if rem.get("type") == "strengthen"
            else "Recalibrate this energy pattern"
        )
        remedy_type    = rem.get("type","pacify")
        energy_lang    = rem.get("energy_language","")

        if priority_label == "Your current chapter needs support":
            why = (
                f"Your current life chapter is ruled by {planet}. "
                f"{planet} is in {p_sign} (house {p_house}) — "
                f"{'a challenging position that needs recalibration' if remedy_type == 'pacify' else 'a position that can be amplified'}. "
                f"{energy_lang}"
            )
        elif priority_label == "All timing systems point here":
            why = (
                f"Three separate timing systems — your life chapter, "
                f"annual chart, and current transits — all point to {planet} "
                f"as the most active pattern right now. {energy_lang}"
            )
        elif priority_label == "This year's clearing practice":
            why = (
                f"{planet} is in a challenging position in your annual chart this year. "
                f"This practice clears the resistance it's creating. {energy_lang}"
            )
        elif priority_label == "Amplify what's already working":
            why = (
                f"{planet} is exceptionally strong in your chart right now. "
                f"This practice amplifies that strength. {energy_lang}"
            )
        else:
            why = energy_lang or f"Recalibrates {planet} energy in your current pattern."

        # Build WHAT — the practice
        mantra   = rem.get("mantra","")
        count    = rem.get("count", 108)
        best_day = rem.get("best_day","")
        best_time= rem.get("best_time","")
        ritual   = rem.get("ritual","")
        charity  = rem.get("charity","")
        color    = rem.get("color","")
        food     = rem.get("food","")

        # Build HOW — exact instructions
        how_parts = []
        if mantra and best_time:
            how_parts.append(f"Chant {mantra} × {count} — {best_time}")
        elif mantra:
            how_parts.append(f"Chant {mantra} × {count}")
        if best_day:
            how_parts.append(f"Best day: {best_day}")
        if ritual:
            how_parts.append(ritual)
        if charity:
            how_parts.append(f"Donate: {charity}")
        if color:
            how_parts.append(f"Wear or use {color} today")
        if food:
            how_parts.append(f"Eat: {food}")

        remedies.append({
            "planet":         planet,
            "planet_sign":    p_sign,
            "planet_house":   p_house,
            "remedy_type":    remedy_type,
            "priority_label": priority_label,

            # The 3 layers
            "why":  why,
            "what": mantra or ritual or "See how instructions",
            "how":  how_parts,

            # Practice details
            "mantra":       mantra,
            "beej_mantra":  rem.get("full_mantra",""),
            "count":        count,
            "best_day":     best_day,
            "best_time":    best_time,
            "ritual":       ritual,
            "charity":      charity,
            "color":        color,
            "gemstone":     rem.get("gemstone",""),
            "metal":        rem.get("metal",""),

            # Chakra data (if present)
            "chakra":           rem.get("chakra",{}).get("chakra_name","") if isinstance(rem.get("chakra"),dict) else "",
            "chakra_color":     rem.get("chakra",{}).get("color","") if isinstance(rem.get("chakra"),dict) else "",
            "chakra_location":  rem.get("chakra",{}).get("location","") if isinstance(rem.get("chakra"),dict) else "",
            "chakra_meditation":rem.get("chakra",{}).get("visualization","") if isinstance(rem.get("chakra"),dict) else "",
        })

    # Get today's dasha-specific remedy (separate from day-lord mantra)
    dasha_remedy = None
    if current_md:
        from antar_engine.prompt_builder import SOUND_ALTERNATIVES
        sound = SOUND_ALTERNATIVES.get(current_md, {})
        dasha_planet_data = planets.get(current_md, {})
        dasha_sign  = dasha_planet_data.get("sign","")
        dasha_house = dasha_planet_data.get("house", 0)

        from antar_engine.remedy_engine import DEBILITATION
        is_weak = dasha_sign == DEBILITATION.get(current_md,"")

        dasha_remedy = {
            "planet":    current_md,
            "sign":      dasha_sign,
            "house":     dasha_house,
            "is_weak":   is_weak,
            "dasha":     dasha_string,
            "diagnosis": (
                f"Your {current_md} chapter is active"
                + (f" — {current_md} is weakened in {dasha_sign}, needs support" if is_weak
                   else f" — {current_md} in {dasha_sign} (house {dasha_house})")
            ),
            "mantra":     sound.get("mantra",""),
            "buddhist":   sound.get("buddhist",""),
            "universal":  sound.get("universal",""),
        }

    return {
        "chart_id":      chart_id,
        "first_name":    first_name,
        "dasha":         dasha_string,
        "concern":       concern,
        "remedies":      remedies,
        "dasha_remedy":  dasha_remedy,
        "remedy_count":  len(remedies),
        "generated_at":  now.isoformat(),
    }


# ── Compatibility Sessions List ───────────────────────────────────

@app.get("/api/v1/compatibility/sessions/{chart_id}")
async def list_compatibility_sessions(chart_id: str):
    """List all past compatibility checks for a user."""
    res = supabase.table("compatibility_sessions").select(
        "id,name_a,name_b,compat_type,score,current_layer,created_at,has_time_a,has_time_b"
    ).eq("chart_id_a", chart_id).order("created_at", desc=True).limit(20).execute()

    sessions = []
    for s in (res.data or []):
        sessions.append({
            "session_id":   s["id"],
            "name_b":       s.get("name_b",""),
            "compat_type":  s.get("compat_type","relationship"),
            "score":        s.get("score"),
            "layers_done":  s.get("current_layer", 1),
            "confidence":   90 if s.get("has_time_a") and s.get("has_time_b") else 65,
            "created_at":   s.get("created_at",""),
        })

    return {"sessions": sessions, "count": len(sessions)}


# ── Master Dashboard Endpoint ─────────────────────────────────────


# ─── Panchang plain language (27 nakshatras, 30 tithis, 7 varas) ─────────────

_NAK = {
    "Ashwini":           {"es": "inicio rápido y curación",      "en": "fast starts and healing"},
    "Bharani":           {"es": "transformación profunda",       "en": "deep transformation"},
    "Krittika":          {"es": "claridad y determinación",      "en": "clarity and determination"},
    "Rohini":            {"es": "crecimiento y abundancia",      "en": "growth and abundance"},
    "Mrigashira":        {"es": "búsqueda y curiosidad",         "en": "searching and curiosity"},
    "Ardra":             {"es": "tormenta y renovación",         "en": "storm and renewal"},
    "Punarvasu":         {"es": "renovación y retorno",          "en": "renewal and return"},
    "Pushya":            {"es": "nutrición y crecimiento",       "en": "nourishment and growth"},
    "Ashlesha":          {"es": "percepción y estrategia",       "en": "perception and strategy"},
    "Magha":             {"es": "poder y autoridad",             "en": "power and authority"},
    "Purva Phalguni":    {"es": "placer y creatividad",          "en": "pleasure and creativity"},
    "Uttara Phalguni":   {"es": "acuerdos y compromisos",        "en": "agreements and commitments"},
    "Hasta":             {"es": "habilidad y precisión",         "en": "skill and precision"},
    "Chitra":            {"es": "diseño y brillantez",           "en": "design and brilliance"},
    "Swati":             {"es": "independencia y movimiento",    "en": "independence and movement"},
    "Vishakha":          {"es": "enfoque y propósito",           "en": "focus and purpose"},
    "Anuradha":          {"es": "devoción y cooperación",        "en": "devotion and cooperation"},
    "Jyeshtha":          {"es": "autoridad y protección",        "en": "authority and protection"},
    "Mula":              {"es": "raíces y transformación",       "en": "roots and transformation"},
    "Purva Ashadha":     {"es": "invencibilidad y pureza",       "en": "invincibility and purification"},
    "Uttara Ashadha":    {"es": "victoria definitiva",           "en": "definitive victory"},
    "Shravana":          {"es": "escucha y aprendizaje",         "en": "listening and learning"},
    "Shatabhisha":       {"es": "sanación y misterio",           "en": "healing and mystery"},
    "Purva Bhadrapada":  {"es": "intensidad y fuego interior",   "en": "intensity and inner fire"},
    "Uttara Bhadrapada": {"es": "profundidad y sabiduría",       "en": "depth and wisdom"},
    "Revati":            {"es": "viaje y compasión",             "en": "journey and compassion"},
    "Abhijit":           {"es": "momento victorioso",            "en": "victorious moment"},
}

_NAK_ACTION = {
    "Ashwini":           {"es": "Bueno para lanzar proyectos nuevos.",               "en": "Good for launching new projects."},
    "Bharani":           {"es": "Día intenso para trabajo de fondo.",                "en": "Intense day for deep work."},
    "Krittika":          {"es": "Bueno para decisiones directas.",                   "en": "Good for direct decisions."},
    "Rohini":            {"es": "Excelente para negocios y creatividad.",            "en": "Excellent for business and creativity."},
    "Mrigashira":        {"es": "Bueno para investigar y explorar.",                 "en": "Good for research and exploration."},
    "Ardra":             {"es": "Permite soltar lo viejo.",                          "en": "Good for letting go."},
    "Punarvasu":         {"es": "Los segundos intentos tienen éxito hoy.",           "en": "Second attempts succeed today."},
    "Pushya":            {"es": "Uno de los mejores días del mes para iniciar.",     "en": "One of the best days to start anything."},
    "Ashlesha":          {"es": "Bueno para negociaciones profundas.",               "en": "Good for deep negotiations."},
    "Magha":             {"es": "Día para liderar y tomar decisiones grandes.",      "en": "Day to lead and make big decisions."},
    "Purva Phalguni":    {"es": "Bueno para arte, amor y descanso.",                 "en": "Good for art, love, and rest."},
    "Uttara Phalguni":   {"es": "Excelente para firmar contratos.",                  "en": "Excellent for signing contracts."},
    "Hasta":             {"es": "Bueno para trabajo detallado y manual.",            "en": "Good for detailed and hands-on work."},
    "Chitra":            {"es": "Energía creativa alta — bueno para crear.",         "en": "High creative energy — good for making things."},
    "Swati":             {"es": "Bueno para viajes y nuevas ideas.",                 "en": "Good for travel and new ideas."},
    "Vishakha":          {"es": "Energía fuerte para lograr metas.",                 "en": "Strong energy for achieving goals."},
    "Anuradha":          {"es": "Bueno para relaciones y trabajo en equipo.",        "en": "Good for relationships and teamwork."},
    "Jyeshtha":          {"es": "Día de liderazgo — toma el control.",               "en": "Leadership day — take charge."},
    "Mula":              {"es": "Día para sanar heridas profundas.",                 "en": "Day to heal deep wounds."},
    "Purva Ashadha":     {"es": "Energía para superar obstáculos.",                  "en": "Energy to overcome obstacles."},
    "Uttara Ashadha":    {"es": "Lo que inicies hoy tiene éxito duradero.",          "en": "What you start today has lasting success."},
    "Shravana":          {"es": "Bueno para absorber conocimiento nuevo.",           "en": "Good for absorbing new knowledge."},
    "Shatabhisha":       {"es": "Energía para trabajo profundo y solitario.",        "en": "Energy for deep, solo work."},
    "Purva Bhadrapada":  {"es": "Día para compromisos profundos.",                   "en": "Day for deep commitments."},
    "Uttara Bhadrapada": {"es": "Bueno para meditación y estudio serio.",            "en": "Good for meditation and serious study."},
    "Revati":            {"es": "Energía nutritiva — bueno para ayudar a otros.",    "en": "Nurturing energy — good for helping others."},
    "Abhijit":           {"es": "Ventana especial de éxito durante el mediodía.",    "en": "Special window of success around midday."},
}

_TITHI_MEANING = {
    "1st":  {"es": "energía de inicio — momento para comenzar",      "en": "new beginning energy — time to start"},
    "2nd":  {"es": "energía suave de planificación",                  "en": "gentle planning energy"},
    "3rd":  {"es": "energía de expansión y conexión",                 "en": "expansion and connection energy"},
    "4th":  {"es": "energía de construcción y estabilidad",           "en": "building and stability energy"},
    "5th":  {"es": "energía de riqueza — uno de los mejores días",    "en": "wealth energy — one of the best days"},
    "6th":  {"es": "energía de salud y vitalidad",                    "en": "health and vitality energy"},
    "7th":  {"es": "energía de movimiento y acción",                  "en": "movement and action energy"},
    "8th":  {"es": "energía de prueba — actúa con paciencia",         "en": "challenge energy — act with patience"},
    "9th":  {"es": "energía de fortuna — día auspicioso",             "en": "fortune energy — auspicious day"},
    "10th": {"es": "energía de éxito — bueno para cerrar tratos",     "en": "success energy — good for closing deals"},
    "11th": {"es": "energía espiritual elevada",                      "en": "elevated spiritual energy"},
    "12th": {"es": "energía de logros — completa pendientes",         "en": "achievement energy — complete what's pending"},
    "13th": {"es": "energía de victoria — día favorable",             "en": "victory energy — favorable day"},
    "14th": {"es": "energía intensa — requiere enfoque",              "en": "intense energy — requires focus"},
    "15th": {"es": "luna llena — energía máxima, todo se amplifica",  "en": "full moon — maximum energy, everything amplifies"},
    "16th": {"es": "energía de soltar y sanar",                       "en": "releasing and healing energy"},
    "17th": {"es": "energía de reflexión interior",                   "en": "inner reflection energy"},
    "18th": {"es": "energía de claridad y perspectiva",               "en": "clarity and perspective energy"},
    "19th": {"es": "energía de organización y preparación",           "en": "organization and preparation energy"},
    "20th": {"es": "energía de profundidad estratégica",              "en": "strategic depth energy"},
    "21st": {"es": "energía de transición — mantén flexibilidad",     "en": "transition energy — stay flexible"},
    "22nd": {"es": "energía de consolidación",                        "en": "consolidation energy"},
    "23rd": {"es": "energía introspectiva — escucha tu intuición",    "en": "introspective energy — listen to your intuition"},
    "24th": {"es": "energía de recuperación y descanso",              "en": "recovery and rest energy"},
    "25th": {"es": "energía de revisión interior",                    "en": "inner review energy"},
    "26th": {"es": "energía de introspección profunda — suelta lo viejo", "en": "deep introspection energy — release the old"},
    "27th": {"es": "energía de preparación final",                    "en": "final preparation energy"},
    "28th": {"es": "energía de cierre — libera lo que no sirve",      "en": "closing energy — release what no longer serves"},
    "29th": {"es": "energía de fin de ciclo",                         "en": "end of cycle energy"},
    "30th": {"es": "energía de luna nueva — cierre y comienzo",       "en": "new moon energy — closing and beginning"},
}

_VARA = {
    "Sunday":    {"es_day": "Domingo",   "planet_es": "Sol",       "planet_en": "Sun",      "es": "Bueno para liderazgo, visibilidad y autoridad.",         "en": "Good for leadership, visibility, and authority."},
    "Monday":    {"es_day": "Lunes",     "planet_es": "Luna",      "planet_en": "Moon",     "es": "Bueno para trabajo creativo, intuición y relaciones.",   "en": "Good for creative work, intuition, and relationships."},
    "Tuesday":   {"es_day": "Martes",    "planet_es": "Marte",     "planet_en": "Mars",     "es": "Bueno para iniciar y confrontar obstáculos.",            "en": "Good for starting things and confronting obstacles."},
    "Wednesday": {"es_day": "Miércoles", "planet_es": "Mercurio",  "planet_en": "Mercury",  "es": "Mejor día para reuniones, comunicación y contratos.",    "en": "Best day for meetings, communication, and contracts."},
    "Thursday":  {"es_day": "Jueves",    "planet_es": "Júpiter",   "planet_en": "Jupiter",  "es": "Bueno para aprender y tomar decisiones importantes.",    "en": "Good for learning and making important decisions."},
    "Friday":    {"es_day": "Viernes",   "planet_es": "Venus",     "planet_en": "Venus",    "es": "Bueno para relaciones, amor y creatividad.",             "en": "Good for relationships, love, and creativity."},
    "Saturday":  {"es_day": "Sábado",    "planet_es": "Saturno",   "planet_en": "Saturn",   "es": "Día para trabajo serio, disciplina y responsabilidad.",  "en": "Day for serious work, discipline, and responsibility."},
}

_ACTION_TRANS = {
    "research": {"es": "investigación", "en": "research"},
    "solo work": {"es": "trabajo en solitario", "en": "solo work"},
    "unconventional approaches": {"es": "enfoques innovadores", "en": "unconventional approaches"},
    "public-facing work": {"es": "trabajo público", "en": "public-facing work"},
    "partnerships": {"es": "asociaciones", "en": "partnerships"},
    "communication": {"es": "comunicación", "en": "communication"},
    "business meetings": {"es": "reuniones de negocios", "en": "business meetings"},
    "contracts": {"es": "contratos", "en": "contracts"},
    "creative work": {"es": "trabajo creativo", "en": "creative work"},
    "leadership": {"es": "liderazgo", "en": "leadership"},
    "presentations": {"es": "presentaciones", "en": "presentations"},
    "travel": {"es": "viajes", "en": "travel"},
    "learning": {"es": "aprendizaje", "en": "learning"},
    "relationships": {"es": "relaciones", "en": "relationships"},
    "physical activity": {"es": "actividad física", "en": "physical activity"},
    "meditation": {"es": "meditación", "en": "meditation"},
    "financial decisions": {"es": "decisiones financieras", "en": "financial decisions"},
    "new beginnings": {"es": "nuevos comienzos", "en": "new beginnings"},
    "deep work": {"es": "trabajo profundo", "en": "deep work"},
    "networking": {"es": "networking", "en": "networking"},
    "writing": {"es": "escritura", "en": "writing"},
    "healing": {"es": "sanación", "en": "healing"},
    "planning": {"es": "planificación", "en": "planning"},
}

def _build_panchang_card(day_data, language="es"):
    """
    Converts raw daily-week day into plain-language panchang.
    NEVER shows nakshatra names or tithi numbers to users.
    Only shows meaning.
    """
    if not day_data or not isinstance(day_data, dict):
        return {}

    lang = language if language in ("es", "en") else "es"
    nak       = day_data.get("moon_nakshatra", "")
    tithi     = day_data.get("tithi", "")
    day_name  = day_data.get("day", "")
    aligned   = day_data.get("aligned_for") or []
    friction  = day_data.get("friction_for") or []
    signal    = day_data.get("signal", "")
    move      = day_data.get("move", "")
    event_signal = day_data.get("event_signal") or {}
    score     = day_data.get("score", 5)
    is_friction = day_data.get("is_friction_day", False)

    nak_energy  = _NAK.get(nak, {}).get(lang, "")
    nak_action  = _NAK_ACTION.get(nak, {}).get(lang, "")
    tithi_meaning = _TITHI_MEANING.get(tithi, {}).get(lang, "")
    vara        = _VARA.get(day_name, {})

    def trans(items):
        return [_ACTION_TRANS.get(a, {}).get(lang, a) for a in items]

    if lang == "es":
        day_display = vara.get("es_day", day_name)
        planet      = vara.get("planet_es", "")
        vara_action = vara.get("es", "")

        # Headline: NO tithi numbers, NO nakshatra names
        # Just: "Lunes · energía de sanación y misterio"
        headline = f"{day_display} · energía de {nak_energy}" if nak_energy else day_display

        # Sub: what does today's energy mean + what to do
        energy_desc = f"{nak_action} {tithi_meaning}".strip()

        # Day context (planet)
        day_context = f"Día de {planet} — {vara_action}" if planet else vara_action

        day_quality = "Alta fricción — actúa con cuidado" if is_friction else ("Día fuerte" if score >= 7 else "Día favorable")

        event_out = None
        if event_signal and event_signal.get("fires"):
            cat_map = {"relationship":"relaciones","career":"carrera","wealth":"riqueza","health":"salud","general":"general"}
            event_out = {
                "category": cat_map.get(event_signal.get("category",""), event_signal.get("category","")),
                "hint": event_signal.get("hint",""),
                "strength": event_signal.get("strength",""),
                "follow_up": "Si algo pasa hoy en esta área — pregúntale a Antar."
            }
    else:
        day_display = day_name
        planet      = vara.get("planet_en", "")
        vara_action = vara.get("en", "")

        headline    = f"{day_display} · {nak_energy} energy" if nak_energy else day_display
        energy_desc = f"{nak_action} {tithi_meaning}".strip()
        day_context = f"{planet}'s day — {vara_action}" if planet else vara_action
        day_quality = "High friction — act carefully" if is_friction else ("Strong day" if score >= 7 else "Favorable day")

        event_out = None
        if event_signal and event_signal.get("fires"):
            event_out = {
                "category": event_signal.get("category",""),
                "hint": event_signal.get("hint",""),
                "strength": event_signal.get("strength",""),
                "follow_up": event_signal.get("follow_up","")
            }

    return {
        "headline":          headline,
        "energy_desc":       energy_desc,
        "day_context":       day_context,
        "day_quality":       day_quality,
        "do_today":          trans(aligned),
        "dont_today":        trans(friction),
        "signal":            signal,
        "move":              move,
        "event_signal":      event_out,
        "score":             score,
        "is_friction_day":   is_friction,
        "moon_nakshatra":    nak,
        "tithi":             tithi,
        "day":               day_display,
    }


@app.get("/api/v1/dashboard/{chart_id}")
async def get_dashboard(chart_id: str, language: str = 'es', ):
    """
    Single endpoint that returns all dashboard data.
    Powers the home page with all 6 sections.
    Parallel fetches for speed.
    """
    try:
        # ── Wire 5: Inject jaimini + lal_kitab into dashboard response ──
        _w5_result = await _get_dashboard_inner(chart_id, language=language)
        if isinstance(_w5_result, dict):
            try:
                _w5_chart = supabase.table('charts').select('jaimini_data, lal_kitab_data').eq('id', chart_id).single().execute()
                _w5_row = _w5_chart.data if _w5_chart and _w5_chart.data else {}
                _w5_result['jaimini'] = _safe_jsonb(_w5_row.get('jaimini_data', {}))
                _w5_result['lal_kitab'] = _safe_jsonb(_w5_row.get('lal_kitab_data', {}))
            except Exception:
                _w5_result.setdefault('jaimini', {})
                _w5_result.setdefault('lal_kitab', {})
        return _w5_result
    except Exception as e:
        import traceback
        raise HTTPException(500, f"Dashboard error: {str(e)} | {traceback.format_exc()[-300:]}")

async def _get_dashboard_inner(chart_id: str, language: str = "es"):
    import asyncio
    from datetime import date, timezone as _tz

    # Load chart
    chart_res = supabase.table("charts").select(
        "first_name,lagna_sign,lagna_degree,birth_date,gender,current_country,country_code,"
        "moon_sign,moon_nakshatra,sun_sign"
    ).eq("id", chart_id).execute()

    if not chart_res.data:
        raise HTTPException(404, "Chart not found")

    row        = chart_res.data[0]
    first_name = row.get("first_name","") or row.get("name","") or "Explorer"
    lagna      = row.get("lagna_sign","")
    moon_sign  = row.get("moon_sign","")
    moon_nak   = row.get("moon_nakshatra","")
    sun_sign   = row.get("sun_sign","")

    # Get current dasha
    now = datetime.now(timezone.utc)
    dasha_res = supabase.table("dasha_periods").select(
        "level,planet_or_sign,start_date,end_date,system"
    ).eq("chart_id", chart_id).eq("system","vimsottari").execute()

    current_md = current_ad = ""
    md_end_date = ""
    for d in (dasha_res.data or []):
        try:
            sd = datetime.fromisoformat(str(d.get("start_date",""))[:10])
            ed = datetime.fromisoformat(str(d.get("end_date",""))[:10])
            if sd.date() <= now.date() <= ed.date():
                level = d.get("level",0)
                lord  = d.get("planet_or_sign","")
                if level == 1:
                    current_md   = lord
                    md_end_date  = str(d.get("end_date",""))[:10]
                elif level == 2:
                    current_ad   = lord
        except Exception:
            pass

    dasha_string = f"{current_md}-{current_ad}" if (current_md and current_ad) else (current_md or current_ad)

    # Get today's cached signal
    today = date.today().isoformat()
    signal_res = supabase.table("daily_signals").select(
        "signal_text,moon_nakshatra,moon_sign,dasha_string,has_wow,wow_today,ayurveda_tip,food_today"
    ).eq("chart_id", chart_id).eq("signal_date", today).execute()

    signal_data = signal_res.data[0] if signal_res.data else {}

    # Get unread alerts
    alerts_res = supabase.table("user_alerts").select(
        "id,headline,urgency,alert_type,created_at,read_at"
    ).eq("chart_id", chart_id).is_("dismissed_at","null").order(
        "created_at", desc=True
    ).limit(5).execute()

    alerts      = alerts_res.data or []
    unread_count= sum(1 for a in alerts if not a.get("read_at"))

    # Get pending feedback count
    feedback_res = supabase.table("user_correlations").select(
        "id", count="exact"
    ).eq("chart_id", chart_id).eq("feedback_status","pending").lte(
        "show_after", now.isoformat()
    ).execute()
    pending_feedback = feedback_res.count or 0

    # Get accuracy score
    try:
        acc_res = supabase.table("prediction_accuracy").select("*").eq(
            "chart_id", chart_id
        ).execute()
        accuracy = acc_res.data[0] if acc_res.data else {}
    except Exception:
        accuracy = {}

    # Get subscription
    sub_res = supabase.table("subscriptions").select(
        "plan,status,current_period_end"
    ).eq("chart_id", chart_id).execute()
    sub  = sub_res.data[0] if sub_res.data else {}
    plan = sub.get("plan","free")

    # Get usage
    month = now.strftime("%Y-%m")
    usage_res = supabase.table("usage_tracking").select("*").eq(
        "chart_id", chart_id
    ).eq("usage_month", month).execute()
    usage = usage_res.data[0] if usage_res.data else {}

    # Get latest compatibility session
    compat_res = supabase.table("compatibility_sessions").select(
        "id,name_b,score,compat_type,created_at"
    ).eq("chart_id_a", chart_id).order(
        "created_at", desc=True
    ).limit(1).execute()
    latest_compat = compat_res.data[0] if compat_res.data else None

    # Get active remedies (dasha remedy from daily signal)
    dasha_remedy = signal_data.get("dasha_remedy") if signal_data else None

    # Build panchanga summary
    panchanga = signal_data.get("panchanga",{})
    if isinstance(panchanga, str):
        import json as _json
        try: panchanga = _json.loads(panchanga)
        except: panchanga = {}

    # Panchang from daily-week
    _pc = {}
    try:
        from antar_engine.daily_prediction_engine import build_daily_week
        _dw = build_daily_week(chart_id=chart_id, tz_offset=-5, language=language)
        _days = _dw.get('days', [])
        if _days: _pc = _build_panchang_card(_days[0], language)
    except Exception as _pe:
        print(f'[dashboard] panchang: {_pe}')

    # Life Arc (chapter_arc) — same data shown on Patterns page
    _life_arc_data = None
    try:
        from antar_engine.chapter_arc import build_chapter_arc
        _la_chart = supabase.table("charts").select("chart_data").eq("id", chart_id).single().execute()
        _la_chart_data = _la_chart.data.get("chart_data", {}) if _la_chart.data else {}
        if isinstance(_la_chart_data, str):
            import json as _lajson
            try: _la_chart_data = _lajson.loads(_la_chart_data)
            except: _la_chart_data = {}
        # Get vimsottari dashas for chapter arc
        _la_vim = supabase.table("dasha_periods").select(
            "planet_or_sign, start_date, end_date, level"
        ).eq("chart_id", chart_id).eq("system", "vimsottari").eq("level", 1).order("start_date").execute()
        _la_dashas = {"vimsottari": [
            {"lord_or_sign": d["planet_or_sign"], "start": d["start_date"], "end": d["end_date"]}
            for d in (_la_vim.data or [])
        ]}
        _life_arc_data = build_chapter_arc(chart_data=_la_chart_data, dashas=_la_dashas)
        # Translate life_arc fields for Spanish
        if _life_arc_data and language and language.startswith("es"):
            _CHAPTER_THEME_ES = {
                "The soul is stepping out of the shadow and into its own light.": "El alma esta saliendo de la sombra hacia su propia luz.",
                "An identity is being forged that cannot be taken away.": "Se esta forjando una identidad que no puede ser arrebatada.",
                "The full sun of who you are is at its zenith.": "El sol pleno de quien eres esta en su cenit.",
                "The harvest of hard-won identity is complete.": "La cosecha de una identidad ganada con esfuerzo esta completa.",
                "The inner world is becoming the teacher.": "El mundo interior se esta convirtiendo en el maestro.",
                "Emotional roots are being planted that will hold for a lifetime.": "Se estan plantando raices emocionales que duraran toda la vida.",
                "The deepest feeling is the clearest truth.": "El sentimiento mas profundo es la verdad mas clara.",
                "A river of feeling is becoming a deep, still lake.": "Un rio de emociones se esta convirtiendo en un lago profundo y quieto.",
                "The warrior in you is waking up.": "El guerrero en ti esta despertando.",
                "Courage is being built through use.": "El coraje se construye con la practica.",
                "The fire of will is at its brightest.": "El fuego de la voluntad esta en su maximo brillo.",
                "The battle is ending. The victor is ready for peace.": "La batalla esta terminando. El vencedor esta listo para la paz.",
                "The mind is sharpening like a new blade.": "La mente se afila como una hoja nueva.",
                "Intellect is becoming the primary tool.": "El intelecto se esta convirtiendo en la herramienta principal.",
                "The mind at its most precise and powerful.": "La mente en su punto mas preciso y poderoso.",
                "The library is full. The teaching begins.": "La biblioteca esta llena. La ensenanza comienza.",
                "The sky is getting larger.": "El cielo se esta haciendo mas grande.",
                "Abundance is being constructed, brick by brick.": "La abundancia se construye ladrillo a ladrillo.",
                "The harvest of expansion is here.": "La cosecha de la expansion esta aqui.",
                "What was received must now be given forward.": "Lo que se recibio ahora debe darse hacia adelante.",
                "The heart is learning how to love.": "El corazon esta aprendiendo a amar.",
                "Beauty is becoming a way of living.": "La belleza se esta convirtiendo en una forma de vivir.",
                "Love in its fullest expression.": "El amor en su expresion mas plena.",
                "What was beautiful remains in the heart forever.": "Lo que fue hermoso permanece en el corazon para siempre.",
                "The sculptor has arrived. The work begins.": "El escultor ha llegado. El trabajo comienza.",
                "What is real is being separated from what is not.": "Lo real se esta separando de lo que no lo es.",
                "Truth without ornamentation.": "La verdad sin adornos.",
                "The fire has burned. What remains is gold.": "El fuego ha ardido. Lo que queda es oro.",
                "Something new and unprecedented is beginning.": "Algo nuevo y sin precedentes esta comenzando.",
                "The old world is dissolving into the new.": "El viejo mundo se esta disolviendo en el nuevo.",
                "Transformation at maximum velocity.": "Transformacion a maxima velocidad.",
                "The dream and the reality are meeting.": "El sueno y la realidad se estan encontrando.",
                "Something essential is being uncovered beneath the layers.": "Algo esencial se esta descubriendo bajo las capas.",
                "The soul is lightening its load.": "El alma esta aligerando su carga.",
                "Liberation in the truest sense.": "Liberacion en el sentido mas verdadero.",
                "The last thing to be released is the releasing itself.": "Lo ultimo que hay que soltar es el soltar mismo.",
            }
            _PHASE_LABEL_ES = {
                "The Opening Phase": "La Fase de Apertura",
                "The Building Phase": "La Fase de Construccion",
                "The Peak Phase": "La Fase Pico",
                "The Completion Phase": "La Fase de Cierre",
                "Active Phase": "Fase Activa",
            }
            _PLANET_NAME_ES = {
                "Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio",
                "Jupiter": "Jupiter", "Venus": "Venus", "Saturn": "Saturno",
                "Rahu": "Rahu", "Ketu": "Ketu",
            }
            _ct = _life_arc_data.get("chapter_theme", "")
            _life_arc_data["chapter_theme"] = _CHAPTER_THEME_ES.get(_ct, _ct)
            _pl = _life_arc_data.get("phase_label", "")
            _life_arc_data["phase_label"] = _PHASE_LABEL_ES.get(_pl, _pl)
            _ce = _life_arc_data.get("current_energy", "")
            _life_arc_data["current_energy"] = _PLANET_NAME_ES.get(_ce, _ce)
            _ne = _life_arc_data.get("next_chapter_energy", "")
            _life_arc_data["next_chapter_energy"] = _PLANET_NAME_ES.get(_ne, _ne)
    except Exception as _lae:
        print(f'[dashboard] life_arc: {_lae}')

    return {
        "chart_id":    chart_id,
        "first_name":  first_name,

        # Section 1: Identity
        "lagna":       lagna,
        "moon_sign":   moon_sign,
        "moon_nakshatra": moon_nak,
        "sun_sign":    sun_sign,

        # Section 2: Current chapter
        "dasha":       dasha_string,
        "dasha_md":    current_md,
        "dasha_ad":    current_ad,
        "dasha_ends":  md_end_date,

        # Section 3: Today's signal
        "has_signal":  bool(signal_data),
        "signal_preview": (signal_data.get("signal_text","")[:200] if signal_data else ""),
        "moon_nak_today": signal_data.get("moon_nakshatra","") if signal_data else "",
        "rahu_kalam":  (panchanga.get("rahu_kalam","") if panchanga else "") or (signal_data.get("rahu_kalam","") if signal_data else ""),
        "abhijit":     (panchanga.get("abhijit","") if panchanga else "") or (signal_data.get("abhijit","") if signal_data else ""),
        "has_wow":     signal_data.get("has_wow", False) if signal_data else False,
        "do_today":    signal_data.get("do_today",[]) if signal_data else [],
        "dont_today":  signal_data.get("dont_today",[]) if signal_data else [],
        "panchanga_headline": panchanga.get("headline","") if panchanga else "",
        "day_quality": panchanga.get("day_quality","") if panchanga else "",

        # Section 4: Alerts
        "alerts":      alerts[:3],
        "unread_alerts": unread_count,

        # Section 5: Accuracy + feedback
        "accuracy_pct":      accuracy.get("accuracy_pct"),
        "total_tracked":     accuracy.get("total_tracked",0),
        "pending_feedback":  pending_feedback,

        # Section 6: Active remedy
        "dasha_remedy": dasha_remedy,

        # Section 7: Compatibility
        "latest_compat": latest_compat,

        # Section 8: Plan
        "plan":          plan,
        "is_paid":       plan != "free",
        "pred_used":     usage.get("pred_count",0),
        "pred_limit":    3 if plan == "free" else 999,
        "compat_used":   usage.get("compat_count",0),
        "compat_limit":  1 if plan == "free" else (10 if plan == "seeker" else 999),

        # Section 9: Locale
        "current_country": row.get("current_country", row.get("country_code", "")),
        "panchanga_headline":   _pc.get("headline", ""),
        "energy_desc_today":    _pc.get("energy_desc", ""),
        "day_context_today":    _pc.get("day_context", ""),
        "day_quality":          _pc.get("day_quality", ""),
        "do_today":             _pc.get("do_today", []),
        "dont_today":           _pc.get("dont_today", []),
        "signal_today":         _pc.get("signal", ""),
        "move_today":           _pc.get("move", ""),
        "event_signal_today":   _pc.get("event_signal"),
        "moon_nak_today":       _pc.get("moon_nakshatra", ""),
        "is_friction_day":      _pc.get("is_friction_day", False),

        # Section 10: Life Arc (chapter_arc) — powers dashboard Life Arc card
        "life_arc": _life_arc_data,
    }


# ── Google Auth Endpoints ─────────────────────────────────────────

@app.post("/api/v1/auth/link-chart")
async def link_chart_to_google(request: dict):
    """
    Links an anonymous chart to a Google-authenticated user.
    Called after Google Sign-in succeeds on the frontend.

    Body: {
        chart_id: string,       -- the anonymous chart from localStorage
        google_id: string,      -- user.id from Supabase Auth
        email: string,
        display_name: string,
        avatar_url: string
    }
    """
    chart_id     = request.get("chart_id","")
    google_id    = request.get("google_id","")
    email        = request.get("email","")
    display_name = request.get("display_name","")
    avatar_url   = request.get("avatar_url","")

    if not chart_id or not google_id:
        raise HTTPException(400, "chart_id and google_id required")

    # Check if this Google user already has a chart
    existing = supabase.table("charts").select("id").eq(
        "google_id", google_id
    ).execute()

    if existing.data:
        # User already has a chart — return existing chart_id
        # (don't create duplicate — just return the one they already have)
        existing_chart_id = existing.data[0]["id"]

        # Update profile info in case it changed
        supabase.table("charts").update({
            "email":        email,
            "display_name": display_name,
            "avatar_url":   avatar_url,
            "first_name":   display_name.split()[0] if display_name else "",
        }).eq("id", existing_chart_id).execute()

        return {
            "success":  True,
            "chart_id": existing_chart_id,
            "action":   "restored",
            "message":  "Welcome back — your chart has been restored",
        }

    # New user — link the anonymous chart to their Google account
    supabase.table("charts").update({
        "google_id":    google_id,
        "email":        email,
        "display_name": display_name,
        "avatar_url":   avatar_url,
        "first_name":   display_name.split()[0] if display_name else "",
    }).eq("id", chart_id).execute()

    return {
        "success":  True,
        "chart_id": chart_id,
        "action":   "linked",
        "message":  "Chart saved to your Google account",
    }



# ═══════════════════════════════════════════════════════════════════
# USER PREFERENCES — Language + Remedy Style (Sprint L)
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/v1/chart/update-preferences")
async def update_preferences(request: Request):
    import logging; logger = logging.getLogger("antar.preferences")
    from fastapi.responses import JSONResponse
    """
    Update user preferences: language and/or remedy_style.
    Called from frontend profile/settings page.
    Fire-and-forget from frontend — no blocking UI.
    """
    try:
        body = await request.json()
        chart_id = body.get("chart_id")

        if not chart_id:
            return JSONResponse(
                status_code=400,
                content={"error": "chart_id is required"}
            )

        # Validate language
        valid_languages = {"en", "hi", "hinglish", "es", "pt"}
        language = body.get("language")
        if language and language not in valid_languages:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid language. Must be one of: {', '.join(sorted(valid_languages))}"}
            )

        # Validate remedy_style
        remedy_style = body.get("remedy_style")
        if remedy_style is not None and remedy_style not in {"traditional", "secular"}:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid remedy_style. Must be 'traditional' or 'secular'."}
            )

        # Build update dict — only include fields that were sent
        updates = {}
        if language:
            updates["language"] = language
        if "remedy_style" in body:
            updates["remedy_style"] = remedy_style

        if not updates:
            return {"status": "ok", "message": "No changes"}

        # Update Supabase
        supabase.table("charts").update(updates).eq("id", chart_id).execute()

        # If language changed, clear caches so content regenerates in new language
        if language:
            try:
                supabase.table("practice_schedule_cache").delete().eq("chart_id", chart_id).execute()
            except Exception:
                pass
            try:
                supabase.table("welcome_signals").delete().eq("chart_id", chart_id).execute()
            except Exception:
                pass
            try:
                supabase.table("weekly_briefings").delete().eq("chart_id", chart_id).execute()
            except Exception:
                pass
            try:
                supabase.table("monthly_deepdives").delete().eq("chart_id", chart_id).execute()
            except Exception:
                pass

        logger.info(f"Preferences updated for {chart_id}: {updates}")
        return {"status": "ok", "updated": updates}

    except Exception as e:
        logger.error(f"update-preferences failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to update preferences"}
        )


@app.get("/api/v1/auth/restore/{google_id}")
async def restore_chart(google_id: str):
    """
    Restores chart_id for a returning Google user.
    Called on app load when Supabase session exists but localStorage is empty.
    """
    res = supabase.table("charts").select(
        "id,first_name,display_name,avatar_url,email,"
        "lagna_sign,moon_sign,moon_nakshatra,sun_sign"
    ).eq("google_id", google_id).order(
        "created_at", desc=True
    ).limit(1).execute()

    if not res.data:
        raise HTTPException(404, "No chart found for this account")

    row = res.data[0]

    # Get current dasha
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    dasha_res = supabase.table("dasha_periods").select(
        "level,planet_or_sign,system"
    ).eq("chart_id", row["id"]).eq("system","vimsottari").execute()

    current_md = current_ad = ""
    for d in (dasha_res.data or []):
        try:
            sd = datetime.fromisoformat(str(d.get("start_date",""))[:10].replace("Z",""))
            ed = datetime.fromisoformat(str(d.get("end_date",""))[:10].replace("Z",""))
            if sd.date() <= now.date() <= ed.date():
                level = d.get("level",0)
                lord  = d.get("planet_or_sign","")
                if level == 1:   current_md = lord
                elif level == 2: current_ad = lord
        except Exception:
            pass

    dasha = f"{current_md}-{current_ad}" if current_ad else current_md

    return {
        "chart_id":       row["id"],
        "first_name":     row.get("first_name","") or row.get("display_name","").split()[0] if row.get("display_name") else "",
        "display_name":   row.get("display_name",""),
        "avatar_url":     row.get("avatar_url",""),
        "email":          row.get("email",""),
        "lagna":          row.get("lagna_sign",""),
        "moon_sign":      row.get("moon_sign",""),
        "moon_nakshatra": row.get("moon_nakshatra",""),
        "sun_sign":       row.get("sun_sign",""),
        "current_dasha":  dasha,
    }


@app.get("/api/v1/auth/profile/{google_id}")
async def get_profile(google_id: str):
    """Get user profile for display in header/settings."""
    res = supabase.table("charts").select(
        "id,first_name,display_name,avatar_url,email,lagna_sign,moon_sign,created_at"
    ).eq("google_id", google_id).limit(1).execute()

    if not res.data:
        raise HTTPException(404, "Profile not found")

    row = res.data[0]

    # Get subscription
    sub_res = supabase.table("subscriptions").select("plan,status").eq(
        "chart_id", row["id"]
    ).execute()
    plan = sub_res.data[0].get("plan","free") if sub_res.data else "free"

    return {
        "chart_id":     row["id"],
        "display_name": row.get("display_name",""),
        "first_name":   row.get("first_name",""),
        "avatar_url":   row.get("avatar_url",""),
        "email":        row.get("email",""),
        "lagna":        row.get("lagna_sign",""),
        "moon_sign":    row.get("moon_sign",""),
        "plan":         plan,
        "member_since": str(row.get("created_at",""))[:10],
    }


# ── PDF Report Endpoint ───────────────────────────────────────────

@app.get("/api/v1/report/{chart_id}/pdf")
async def generate_life_report(chart_id: str):
    """
    Generate and download complete PDF life report.
    Requires Seeker or Navigator plan.
    """
    from antar_engine.subscription_engine import get_subscription
    from antar_engine.pdf_engine import generate_pdf_report
    from fastapi.responses import Response

    # Check subscription
    sub = get_subscription(chart_id, supabase)
    if sub.get("plan","free") == "free":
        raise HTTPException(403, {
            "error": "upgrade_required",
            "message": "PDF reports are available on Seeker and Navigator plans",
            "upgrade_url": "https://antar.world/upgrade",
        })

    # Get remedies for the report
    try:
        from antar_engine import remedy_selector
        chart_res = supabase.table("charts").select(
            "chart_data,birth_date,first_name,career_stage,health_status"
        ).eq("id", chart_id).execute()
        chart_data = chart_res.data[0]["chart_data"] if chart_res.data else {}
        dasha_res  = supabase.table("dasha_periods").select("*").eq(
            "chart_id", chart_id
        ).execute()
        dashas = {"vimsottari": dasha_res.data or []}
        remedies = remedy_selector.select_remedies(
            supabase=supabase, chart_data=chart_data,
            dashas=dashas, transits={}, user_age=35,
            question="general", patra=None, limit=3,
        )
    except Exception:
        remedies = []

    pdf_bytes = await generate_pdf_report(chart_id, supabase, remedies)

    # Determine content type
    content_type = "application/pdf"
    filename     = f"antar-report-{chart_id[:8]}.pdf"

    if pdf_bytes[:4] != b"%PDF":
        # Fallback HTML returned
        content_type = "text/html"
        filename     = f"antar-report-{chart_id[:8]}.html"

    return Response(
        content=pdf_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── C1: Prediction history endpoint ──────────────────────────────────────────
@app.get("/api/v1/predictions/{chart_id}")
async def get_prediction_history(chart_id: str, limit: int = 20):
    """Last N predictions for a chart with plain English output. Sprint C1-03."""
    try:
        result = supabase.table("predictions") \
            .select(
                "id, created_at, query, concern, "
                "plain_summary, action_item, signal_line, "
                "timing_window, signal_confidence, all_domains"
            ) \
            .eq("chart_id", chart_id) \
            .order("created_at", desc=True) \
            .limit(min(limit, 50)) \
            .execute()
        predictions = result.data or []
        return {"predictions": predictions, "total": len(predictions)}
    except Exception as e:
        print(f"[predictions] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch prediction history")


# ── C1: Domain signals endpoint ───────────────────────────────────────────────
@app.get("/api/v1/domain-signals/{chart_id}")
async def get_domain_signals(chart_id: str):
    """One signal_line per life domain from most recent prediction. Sprint C1-04."""
    domains = [
        "career", "wealth", "love", "children", "health", "foreign",
        "legal", "business", "loans", "property", "education", "luck",
        "travel", "spirituality", "father", "mother", "siblings",
        "enemies", "general"
    ]
    try:
        result = supabase.table("predictions") \
            .select("id, concern, signal_line, signal_confidence, timing_window, all_domains, created_at") \
            .eq("chart_id", chart_id) \
            .not_.is_("signal_line", "null") \
            .order("created_at", desc=True) \
            .limit(100) \
            .execute()
        predictions = result.data or []
        signals = {}
        for domain in domains:
            for pred in predictions:
                pred_domains = pred.get("all_domains") or []
                if domain in pred_domains or domain == pred.get("concern"):
                    signals[domain] = {
                        "signal_line":   pred.get("signal_line"),
                        "confidence":    pred.get("signal_confidence"),
                        "timing_window": pred.get("timing_window"),
                        "prediction_id": pred.get("id"),
                        "created_at":    pred.get("created_at"),
                    }
                    break
        return {
            "signals":      signals,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[domain-signals] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch domain signals")


# ── C3: Rate a prediction ─────────────────────────────────────────────────────
@app.post("/api/v1/predictions/{prediction_id}/rate")
async def rate_prediction(prediction_id: str, body: dict):
    """
    User rates whether a prediction came true.
    Body: { "rating": 1 }  — 1 = accurate, 0 = did not happen
    Sprint C3.
    """
    rating = body.get("rating")
    if rating not in (0, 1):
        raise HTTPException(status_code=400, detail="rating must be 0 or 1")
    try:
        result = supabase.table("predictions") \
            .update({"accuracy_rating": rating}) \
            .eq("id", prediction_id) \
            .execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return {"success": True, "prediction_id": prediction_id, "rating": rating}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[rate] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save rating")


# ── C3: Pattern summary for a chart ──────────────────────────────────────────
@app.get("/api/v1/patterns/{chart_id}")
async def get_pattern_summary(chart_id: str):
    """
    Returns pattern memory analysis for a chart:
    - Recurring themes
    - Unresolved cases
    - Accuracy summary
    - All past predictions with fulfillment status
    Sprint C3.
    """
    from antar_engine.pattern_memory import build_pattern_memory, _fetch_predictions, _infer_fulfillment, _detect_themes, _accuracy_summary

    try:
        past = _fetch_predictions(chart_id, supabase)
        if not past:
            return {
                "chart_id":         chart_id,
                "total_predictions": 0,
                "recurring_themes":  [],
                "unresolved_cases":  [],
                "accuracy_summary":  "",
                "predictions":       [],
            }

        past = _infer_fulfillment(past)

        unresolved = [
            p for p in past
            if p.get("fulfillment_status") == "inferred_unresolved"
        ]
        themes      = _detect_themes(past)
        acc_summary = _accuracy_summary(past)

        return {
            "chart_id":          chart_id,
            "total_predictions": len(past),
            "recurring_themes":  themes,
            "unresolved_cases":  [
                {
                    "id":           p.get("id"),
                    "concern":      p.get("concern"),
                    "signal_line":  p.get("signal_line"),
                    "timing_window":p.get("timing_window"),
                    "created_at":   p.get("created_at"),
                }
                for p in unresolved
            ],
            "accuracy_summary":  acc_summary,
            "predictions":       [
                {
                    "id":               p.get("id"),
                    "created_at":       p.get("created_at"),
                    "concern":          p.get("concern"),
                    "signal_line":      p.get("signal_line"),
                    "timing_window":    p.get("timing_window"),
                    "fulfillment_status": p.get("fulfillment_status"),
                    "accuracy_rating":  p.get("accuracy_rating"),
                }
                for p in past
            ],
        }

    except Exception as e:
        print(f"[patterns] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pattern summary")


# ── Sprint E: Welcome signal ──────────────────────────────────────────────────
@app.get("/api/v1/welcome/{chart_id}")
async def get_welcome(chart_id: str):
    """
    Returns the welcome signal for a chart.
    Generated automatically after chart creation.
    Sprint E.
    """
    try:
        signal = get_welcome_signal(chart_id, supabase)
        if signal:
            return signal
        # Not ready yet — generate now synchronously
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})
        planets      = chart_data.get("planets", {})
        # Get current dasha from dasha_periods table
        _current_dasha = ""
        try:
            from datetime import date
            _dasha_res = supabase.table("dasha_periods") \
                .select("planet_or_sign, start_date, end_date") \
                .eq("chart_id", chart_id) \
                .eq("system", "vimsottari") \
                .eq("level", 1) \
                .lte("start_date", str(date.today())) \
                .gte("end_date", str(date.today())) \
                .execute()
            if _dasha_res.data:
                _current_dasha = _dasha_res.data[0].get("planet_or_sign", "")
        except Exception:
            pass

        _bd = str(chart_record.get("birth_date", "") or "")[:10]
        try:
            from antar_engine.age_utils import calculate_current_age as _ca
            _sync_age = _ca(_bd) if _bd else None
        except Exception:
            _sync_age = None

        # Guard: new chart may still be computing — return generating status
        if not chart_data or not isinstance(chart_data, dict):
            return {
                "status": "generating",
                "chart_id": chart_id,
                "signal_1": None,
                "signal_2": None,
                "signal_3": None,
            }
        if chart_data.get("lagna") is None and chart_data.get("lagna_sign") is None:
            return {
                "status": "generating",
                "chart_id": chart_id,
                "signal_1": None,
                "signal_2": None,
                "signal_3": None,
            }

        result = await generate_welcome_signal_v2(
                chart_data=chart_record,
                birth_date=_bd,
                anthropic_client=claude_client,
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[welcome] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate welcome signal")


# ── Sprint E: Weekly briefing ─────────────────────────────────────────────────
@app.get("/api/v1/weekly-briefing/{chart_id}")
async def get_weekly_briefing(chart_id: str, refresh: bool = False):
    """
    Returns the weekly briefing for the current week.
    Auto-generated every Monday. Sprint E.
    """
    try:
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})
        planets      = chart_data.get("planets", {})

        # Get DKP context
        dkp_ctx = ""
        country_code = chart_record.get("current_country") or chart_record.get("country_code", "")
        if country_code:
            try:
                from antar_engine.country_context import COUNTRY_CONTEXT
                _name = COUNTRY_CONTEXT.get(country_code, {}).get("name", country_code)
                dkp_ctx = await get_dkp_context(
                    country_code=country_code,
                    country_name=_name,
                    supabase=supabase,
                    deepseek_client=deepseek_client,
                )
            except Exception:
                pass


        # Fetch current dasha from dasha_periods
        _current_dasha = ""
        try:
            from datetime import date as _date
            _dr = supabase.table("dasha_periods") \
                .select("planet_or_sign") \
                .eq("chart_id", chart_id) \
                .eq("system", "vimsottari") \
                .eq("level", 1) \
                .lte("start_date", str(_date.today())) \
                .gte("end_date", str(_date.today())) \
                .limit(1).execute()
            if _dr.data:
                _current_dasha = _dr.data[0].get("planet_or_sign", "")
        except Exception:
            pass
        result = await generate_weekly_briefing(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_record.get("lagna_sign", "") or chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=chart_record.get("moon_sign", "") or planets.get("Moon", {}).get("sign", ""),
            current_dasha=_current_dasha,
            age=None,
            country_code=country_code,
            dkp_context=dkp_ctx,
            supabase=supabase,
            claude_client=claude_client,
            force_refresh=refresh,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[weekly-briefing] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate weekly briefing")


# ── Sprint E: Monthly deep-dive ───────────────────────────────────────────────
@app.get("/api/v1/monthly-deepdive/{chart_id}")
async def get_monthly_deepdive(chart_id: str, refresh: bool = False):
    """
    Returns the monthly deep-dive for the current month.
    Auto-generated on the 1st. Sprint E.
    """
    try:
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})

        # Get LK context if available
        lk_ctx = ""
        try:
            from antar_engine.lal_kitab_db import format_lk_context_from_stored
            lk_ctx = format_lk_context_from_stored(chart_record) or ""
        except Exception:
            pass


        # Fetch current dasha from dasha_periods
        _current_dasha = ""
        try:
            from datetime import date as _date
            _dr = supabase.table("dasha_periods") \
                .select("planet_or_sign") \
                .eq("chart_id", chart_id) \
                .eq("system", "vimsottari") \
                .eq("level", 1) \
                .lte("start_date", str(_date.today())) \
                .gte("end_date", str(_date.today())) \
                .limit(1).execute()
            if _dr.data:
                _current_dasha = _dr.data[0].get("planet_or_sign", "")
        except Exception:
            pass
        result = await generate_monthly_deepdive(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_record.get("lagna_sign", "") or chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=chart_record.get("moon_sign", "") or chart_data.get("planets", {}).get("Moon", {}).get("sign", ""),
            current_dasha=_current_dasha,
            age=None,
            country_code=chart_record.get("current_country") or chart_record.get("country_code", ""),
            lk_context=lk_ctx,
            supabase=supabase,
            claude_client=claude_client,
            force_refresh=refresh,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[monthly-deepdive] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate monthly deep-dive")


# ── Sprint E: Annual plan ─────────────────────────────────────────────────────
@app.get("/api/v1/annual-plan/{chart_id}")
async def get_annual_plan(chart_id: str, refresh: bool = False):
    """
    Returns the annual plan for the current year.
    Auto-generated on birthday and January 1st. Sprint E.
    """
    try:
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})

        # Get DKP and LK context
        dkp_ctx = ""
        lk_ctx  = ""
        country_code = chart_record.get("current_country") or chart_record.get("country_code", "")
        try:
            from antar_engine.country_context import COUNTRY_CONTEXT
            _name = COUNTRY_CONTEXT.get(country_code, {}).get("name", country_code)
            dkp_ctx = await get_dkp_context(
                country_code=country_code,
                country_name=_name,
                supabase=supabase,
                deepseek_client=deepseek_client,
            )
        except Exception:
            pass
        try:
            from antar_engine.lal_kitab_db import format_lk_context_from_stored
            lk_ctx = format_lk_context_from_stored(chart_record) or ""
        except Exception:
            pass



        # Fetch current dasha from dasha_periods
        _current_dasha = ""
        try:
            from datetime import date as _date
            _dr = supabase.table("dasha_periods") \
                .select("planet_or_sign") \
                .eq("chart_id", chart_id) \
                .eq("system", "vimsottari") \
                .eq("level", 1) \
                .lte("start_date", str(_date.today())) \
                .gte("end_date", str(_date.today())) \
                .limit(1).execute()
            if _dr.data:
                _current_dasha = _dr.data[0].get("planet_or_sign", "")
        except Exception:
            pass
        result = await generate_annual_plan(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_record.get("lagna_sign", "") or chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=chart_record.get("moon_sign", "") or chart_data.get("planets", {}).get("Moon", {}).get("sign", ""),
            current_dasha=_current_dasha,
            birth_date=chart_record.get("birth_date", ""),
            age=None,
            country_code=country_code,
            dkp_context=dkp_ctx,
            lk_context=lk_ctx,
            supabase=supabase,
            claude_client=claude_client,
            force_refresh=refresh,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[annual-plan] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate annual plan")




# ═══════════════════════════════════════════════════════════════
# SPRINT P — PRACTICE ENGINE ENDPOINTS (auto-patched 2026-03-31)
# ═══════════════════════════════════════════════════════════════

from antar_engine.practice_engine import generate_practice_schedule, format_practice_for_predict_prompt
import json as _pjson
def _safe_jsonb(v):
    if isinstance(v, str):
        try: return _pjson.loads(v)
        except: return {}
    return v if isinstance(v, dict) else {}

from pydantic import BaseModel as _PracticeBaseModel
from antar_engine.symptom_library import scan_chart_symptoms, get_domain_status, build_diagnostic_prompt_block, get_primary_symptom, get_domain_vocabulary
from antar_engine.verification_engine import generate_verification_queue, calculate_precision_score, get_verification_data

class _PracticeCompleteReq(_PracticeBaseModel):
    practice_id: str
    user_note: str = None


def _translate_instrument_symptom_es(symptom, status, area_name):
    """Convert internal symptom jargon to plain Spanish."""
    if not symptom or not isinstance(symptom, str): 
        return _default_symptom_es(status, area_name)
    
    # Strip internal jargon patterns entirely
    import re
    # Remove "X (instrument lord) in dusthana annual house — ..." patterns
    cleaned = re.sub(r'[A-Z][a-z]+ [A-Z][a-z]+\s*\(instrument lord\)[^.]*\.?\s*', '', symptom)
    # Remove "X transiting through this instrument — ..." patterns  
    cleaned = re.sub(r'[A-Z][a-z]+ [A-Z][a-z]+\s*transiting through[^.]*\.?\s*', '', cleaned)
    # Remove "Processing Speed", "Action Drive", "Magnetism Field", "Intuition Compass" etc.
    for jargon in ["Processing Speed", "Action Drive", "Magnetism Field", "Intuition Compass",
                   "Ambition Engine", "Structural Load", "Fortune Vector", "Authority Signal",
                   "Growth Amplifier", "Emotional Radar", "Revenue Pipeline", "Alliance Sync",
                   "Capital Runway", "Hungry Becoming", "Creative Pulse", "Velocity Engine",
                   "Foundation Shield", "Wisdom Lens", "Health Matrix", "Resource Grid",
                   "Authority Engine", "System Vitals", "Capital Reserves", "Conflict Shield",
                   "instrument lord", "dusthana", "Argala", "unobstructed interventions",
                   "PRESSURE", "ACTIVE"]:
        cleaned = cleaned.replace(jargon, "")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(" .,—-")
    
    # If nothing meaningful remains, use status-based default
    if len(cleaned) < 10:
        return _default_symptom_es(status, area_name)
    return cleaned

def _default_symptom_es(status, area_name):
    """Plain Spanish description based on status."""
    name = area_name.lower() if area_name else "esta area"
    status = (status or "").upper()
    if status == "FRICTION":
        return f"Esta area necesita tu atencion ahora. Actua con cuidado."
    elif status == "ACTIVE":
        return f"Energia abierta. Buen momento para avanzar en {name}."
    elif status == "PEAK":
        return f"En su mejor momento. Prioriza {name} esta semana."
    elif status == "PREPARING":
        return f"Se esta preparando. La energia de {name} se abrira pronto."
    else:
        return f"Sin actividad significativa en {name} ahora."


def _translate_practice_schedule_es(sched):
    if not sched or not isinstance(sched, dict): return sched
    import copy; s = copy.deepcopy(sched)
    L = {"Love & Creativity":"Amor y Creatividad","Communication & Clarity":"Comunicacion y Claridad","Career & Authority":"Carrera y Autoridad","Health & Vitality":"Salud y Vitalidad","Wealth & Resources":"Riqueza y Recursos","Courage & Initiative":"Valentia e Iniciativa","Wisdom & Expansion":"Sabiduria y Expansion","Relationships & Harmony":"Relaciones y Armonia","Discipline & Structure":"Disciplina y Estructura","Transformation":"Transformacion"}
    TM = {"morning":"manana","evening":"tarde/noche","morning or evening":"manana o tarde/noche","evening, in a calm space":"tarde/noche en espacio tranquilo","morning, before important conversations":"manana antes de conversaciones importantes","morning, before meetings or writing":"manana antes de reuniones"}
    DY = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miercoles","Thursday":"Jueves","Friday":"Viernes","Saturday":"Sabado","Sunday":"Domingo"}
    TX = {"Your ability to attract — love, beauty, resources":"Tu capacidad de atraer — amor belleza recursos","Your ability to attract":"Tu capacidad de atraer","love, beauty, resources":"amor belleza recursos","is suppressed. Life feels functional but joyless":"esta bloqueada. La vida se siente funcional pero sin alegria","suppressed. Life feels functional but joyless":"bloqueada. La vida se siente funcional pero sin alegria","Create something beautiful this week":"Crea algo hermoso esta semana","Take yourself somewhere aesthetically inspiring":"Ve a un lugar que inspire belleza","Wear white on Friday":"Viste de blanco el viernes","Your communication and analytical abilities are foggy. Words don't land, deals stall, ideas feel stuck.":"Tu capacidad de comunicacion esta nublada. Las palabras no llegan, los tratos se frenan, las ideas se atascan.","Your communication and analytical abilities are foggy":"Tu capacidad de comunicacion esta nublada","Words don't land, deals stall, ideas feel stuck":"Las palabras no llegan, los tratos se frenan, las ideas se atascan","Strong alignment:":"Fuerte alineacion:","indicators confirm your":"indicadores confirman que tu energia de","energy is the focus right now":"es el enfoque ahora","love & creativity energy is the focus right now":"amor y creatividad es el enfoque ahora","love & creativity":"amor y creatividad","& creativity":"y creatividad","I attract love, beauty, and creative abundance.":"Atraigo amor, belleza y abundancia creativa.","I attract love, beauty, and creative abundance":"Atraigo amor, belleza y abundancia creativa","I am disciplined, patient, and build things that last":"Soy disciplinado/a paciente y construyo cosas que duran"}
    def t(v):
        if not v or not isinstance(v,str): return v
        for a,b in {**L,**TX}.items(): v=v.replace(a,b)
        return v
    def tp(p):
        if not p: return p
        if "energy_label" in p: p["energy_label"]=L.get(p["energy_label"],p["energy_label"])
        if "best_time" in p: p["best_time"]=TM.get(p["best_time"],p["best_time"])
        if "best_day" in p: p["best_day"]=DY.get(p["best_day"],p["best_day"])
        if "day" in p: p["day"]=DY.get(p["day"],p["day"])
        for f in ("why","what","how","practice_why","practice_why_science","duration_reason","completion_milestone"):
            if f in p: p[f]=t(p[f])
        return p
    if "primary_practice" in s: tp(s["primary_practice"])
    if "supporting_practices" in s: [tp(p) for p in s["supporting_practices"]]
    if "mantra_of_the_day" in s:
        m=s["mantra_of_the_day"]
        if "energy_label" in m: m["energy_label"]=L.get(m["energy_label"],m["energy_label"])
        if "affirmation" in m: m["affirmation"]=TX.get(m.get("affirmation",""),m.get("affirmation",""))
        if "mantra_best_time" in m: m["mantra_best_time"]=TM.get(m["mantra_best_time"],m["mantra_best_time"])
        if "mantra_duration_label" in m:
            _MDL_ES={"21 days":"21 dias","40 days":"40 dias","18 days":"18 dias","11 days":"11 dias","9 days":"9 dias","7 days":"7 dias","7 Tuesdays":"7 martes","7 weeks":"7 semanas"}
            m["mantra_duration_label"]=_MDL_ES.get(m["mantra_duration_label"],m["mantra_duration_label"])
    if "convergence_summary" in s:
        cs=s["convergence_summary"]
        for a,b in {**L,**TX}.items(): cs=cs.replace(a,b)
        s["convergence_summary"]=cs
    # --- Lal Kitab remedy translations (IN locale items) ---
    LK_REMEDY_ES = {
        "iron nails buried under a tree on Saturday": "Entierra clavos de hierro bajo un arbol el sabado",
        "copper coin in flowing water": "Moneda de cobre en agua corriente",
        "white flowers at home": "Flores blancas en casa",
        "sweet bread to a dog on Tuesday": "Pan dulce a un perro el martes",
        "green moong dal to birds": "Dal de moong verde a las aves",
        "turmeric tilak on forehead Thursday morning": "Tilak de curcuma en la frente el jueves por la manana",
        "rice and sugar to ants on Friday": "Arroz y azucar a las hormigas el viernes",
        "coal in flowing water on Saturday": "Carbon en agua corriente el sabado",
        "bananas to a temple on Tuesday": "Platanos a un templo el martes",
        "wear warm gold or orange on Sunday": "Viste dorado calido o naranja el domingo",
        "keep a small silver item in your pocket on Monday": "Lleva un objeto de plata en tu bolsillo el lunes",
        "wear red or maroon on Tuesday": "Viste rojo o granate el martes",
        "wear green on Wednesday": "Viste de verde el miercoles",
        "wear yellow on Thursday": "Viste de amarillo el jueves",
        "wear white or pastel on Friday": "Viste de blanco o pastel el viernes",
        "wear black or navy on Saturday": "Viste de negro o azul marino el sabado",
        "keep a small sandalwood item near your desk": "Ten un objeto de sandalo cerca de tu escritorio",
        "wear earth tones on Tuesday": "Viste tonos tierra el martes",
        "Feed birds green moong on Wednesday. Donate to education.": "Alimenta aves con moong verde el miercoles. Dona a causas educativas.",
        "Feed birds on Sunday. Offer water to the Sun.": "Alimenta aves el domingo. Ofrece agua al Sol.",
        "Donate milk or white items on Monday.": "Dona leche o articulos blancos el lunes.",
        "Offer red flowers on Tuesday. Light a lamp.": "Ofrece flores rojas el martes. Enciende una lampara.",
        "Light sesame oil lamp on Saturday.": "Enciende una lampara de aceite de sesamo el sabado.",
        "Donate yellow items on Thursday.": "Dona articulos amarillos el jueves.",
        "Offer white flowers on Friday.": "Ofrece flores blancas el viernes.",
        "Feed black sesame to birds at dusk.": "Alimenta aves con sesamo negro al anochecer.",
        "Donate multi-colored cloth on Saturday.": "Dona tela multicolor el sabado.",
    }
    # --- Remedy action translations (GLOBAL locale) ---
    REMEDY_ACTION_ES = {
        "Spend 5 minutes in morning sunlight. Volunteer for a leadership role this week.": "Pasa 5 minutos al sol de la manana. Ofrece liderazgo esta semana.",
        "Take a 10-minute walk by water this week. Write down three feelings you've been avoiding.": "Camina 10 minutos cerca del agua. Escribe tres emociones que has evitado.",
        "Do 15 minutes of intense exercise on Tuesday. Channel frustration into a physical goal.": "Haz 15 minutos de ejercicio intenso el martes. Canaliza la frustracion en una meta fisica.",
        "Write one difficult email you've been avoiding. Read 15 pages of a new book.": "Escribe ese email dificil que has evitado. Lee 15 paginas de un libro nuevo.",
        "Express gratitude to a mentor or teacher this week. Teach someone one thing you know.": "Agradece a un mentor esta semana. Ensena algo que sepas.",
        "Create something beautiful this week — cook, paint, arrange flowers. Compliment someone sincerely.": "Crea algo hermoso esta semana — cocina, pinta, arregla flores. Halaga a alguien con sinceridad.",
        "Volunteer at a shelter or food bank this Saturday. Help someone who serves others.": "Haz voluntariado este sabado. Ayuda a alguien que sirve a otros.",
        "Pause before your next impulsive decision. Meditate on the difference between desire and need.": "Pausa antes de tu proxima decision impulsiva. Medita sobre deseo vs necesidad.",
        "Spend 10 minutes in silence today. Let go of one attachment — delete, donate, or forgive.": "Pasa 10 minutos en silencio hoy. Suelta un apego — borra, dona o perdona.",
    }
    def t_remedy(v):
        if not v or not isinstance(v,str): return v
        if v in LK_REMEDY_ES: return LK_REMEDY_ES[v]
        if v in REMEDY_ACTION_ES: return REMEDY_ACTION_ES[v]
        # Try partial matches for compound strings (e.g. action + " ← This is your primary practice day.")
        for en,es in {**LK_REMEDY_ES, **REMEDY_ACTION_ES}.items():
            if en in v: v = v.replace(en, es)
        return v

    if "weekly_plan" in s:
        for d in s["weekly_plan"]:
            if "energy_label" in d: d["energy_label"]=L.get(d["energy_label"],d["energy_label"])
            if "day_name" in d: d["day_name"]=DY.get(d["day_name"],d["day_name"])
            if "primary_action" in d: d["primary_action"]=t_remedy(d["primary_action"])
            if "mantra" in d:
                aff = d["mantra"]
                if aff in TX: d["mantra"] = TX[aff]
    # Translate convergence_summary fully
    if "convergence_summary" in s:
        cs = s["convergence_summary"]
        # Full pattern translations
        CONV_PATTERNS_ES = {
            "Strong alignment:": "Fuerte alineacion:",
            "indicators confirm your": "indicadores confirman que tu energia de",
            "energy is the focus right now.": "es el enfoque ahora.",
            "Multiple signals point to": "Multiples senales apuntan a la energia de",
            "energy as your priority this period.": "como tu prioridad en este periodo.",
            "energy is gently active. Light practice recommended.": "esta suavemente activa. Se recomienda practica ligera.",
            "Your": "Tu energia de",
        }
        for en, es in {**L, **CONV_PATTERNS_ES}.items():
            cs = cs.replace(en, es)
        s["convergence_summary"] = cs
    # --- Planet name ES mapping ---
    PLANET_NAME_ES = {
        "Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio",
        "Jupiter": "Jupiter", "Venus": "Venus", "Saturn": "Saturno",
        "Rahu": "Rahu", "Ketu": "Ketu",
    }
    # --- Full-text remedy_why translations ---
    def t_remedy_why(text):
        """Translate remedy_why long-form paragraphs."""
        if not text or not isinstance(text, str): return text
        # Pattern A: dormant/sleeping planet
        if "currently dormant in your chart" in text:
            # Extract planet label from "Your {label} energy is currently dormant"
            import re as _re
            _m = _re.search(r"Your (.+?) energy is currently dormant", text)
            _label = _m.group(1) if _m else ""
            _label_es = PLANET_NAME_ES.get(_label, L.get(_label, _label))
            return (
                f"Tu energia de {_label_es} esta inactiva en tu carta ahora mismo. "
                f"Esto significa que las oportunidades en esta area pasan desapercibidas "
                f"— no porque no existan, sino porque el canal para recibirlas esta "
                f"bloqueado. Esta practica activa ese canal."
            )
        # Pattern B: repeating pattern / Rin
        if "repeating pattern has been detected" in text:
            return (
                "Se ha detectado un patron repetitivo en esta area de tu vida — "
                "la misma situacion sigue apareciendo de diferentes formas. No es mala "
                "suerte. Es una senal de que un patron de respuesta particular necesita "
                "cambiar. Esta practica es el contra-patron."
            )
        # Fallback: use the partial t() translator
        return t(text)

    def t_remedy_why_science(text):
        """Translate remedy_why_science paragraphs."""
        if not text or not isinstance(text, str): return text
        # Pattern A: "Consistent behavioral repetition..."
        if "Consistent behavioral repetition" in text:
            return (
                "La repeticion conductual consistente en un dominio especifico activa vias "
                "neuronales asociadas con ese dominio — literalmente hace que tu cerebro "
                "sea mas receptivo a oportunidades relacionadas."
            )
        # Pattern B: "Repeating life patterns..."
        if "Repeating life patterns" in text:
            return (
                "Los patrones de vida repetitivos frecuentemente se originan en bucles "
                "conductuales inconscientes — respuestas que alguna vez te protegieron "
                "pero que ahora crean exactamente los problemas que intentas evitar. El "
                "contra-comportamiento consistente durante 40 dias interrumpe el bucle a "
                "nivel neurologico."
            )
        return t(text)

    # --- practice_why translation (from PLANET_PRACTICE_META) ---
    PRACTICE_WHY_ES = {
        "Your sense of identity and self-worth is the energy being worked on right now. This practice builds the internal confidence that makes external recognition possible.":
            "Tu sentido de identidad y autoestima es la energia que se esta trabajando ahora. Esta practica construye la confianza interna que hace posible el reconocimiento externo.",
        "Your emotional processing patterns are being recalibrated. This practice creates a pause between feeling and reacting — giving you clarity instead of reactivity.":
            "Tus patrones de procesamiento emocional se estan recalibrando. Esta practica crea una pausa entre sentir y reaccionar — dandote claridad en lugar de reactividad.",
        "Your action energy and drive need direction right now. This practice channels aggression and impatience into decisive, purposeful movement instead of scattered effort.":
            "Tu energia de accion necesita direccion ahora. Esta practica canaliza la agresividad y la impaciencia en movimiento decisivo y con proposito.",
        "Your communication clarity and analytical precision are the focus right now. This practice sharpens how you express ideas and reduces overthinking loops.":
            "Tu claridad de comunicacion y precision analitica son el enfoque ahora. Esta practica agudiza como expresas ideas y reduce los bucles de sobre-analisis.",
        "Your capacity for growth, wisdom, and expansion is being activated. This practice opens you to learning and opportunities that your current beliefs might be filtering out.":
            "Tu capacidad de crecimiento, sabiduria y expansion se esta activando. Esta practica te abre al aprendizaje y oportunidades que tus creencias actuales pueden estar filtrando.",
        "Your relationship patterns and creative expression are the focus. This practice softens defensiveness and opens you to giving and receiving more freely.":
            "Tus patrones de relacion y expresion creativa son el enfoque. Esta practica suaviza la defensividad y te abre a dar y recibir mas libremente.",
        "Your relationship with discipline, long-term thinking, and karmic patterns is being worked on. This practice builds the tolerance for delay that turns ambition into lasting results.":
            "Tu relacion con la disciplina, el pensamiento a largo plazo y los patrones karmicos se esta trabajando. Esta practica construye la tolerancia a la espera que convierte la ambicion en resultados duraderos.",
        "Your relationship with obsession, ambition, and unconventional paths is being recalibrated. This practice helps you use disruptive energy constructively instead of compulsively.":
            "Tu relacion con la obsesion, la ambicion y los caminos no convencionales se esta recalibrando. Esta practica te ayuda a usar la energia disruptiva de forma constructiva.",
        "Your capacity for release, detachment, and trusting your intuition is being developed. This practice helps you let go of outcomes that are blocking your next chapter.":
            "Tu capacidad de soltar, desapego y confianza en tu intuicion se esta desarrollando. Esta practica te ayuda a soltar resultados que bloquean tu siguiente capitulo.",
    }
    PRACTICE_WHY_SCIENCE_ES = {
        "Repetitive intention-setting at the same time daily recalibrates your reticular activating system — the brain's filter that decides what opportunities to notice.":
            "La fijacion repetitiva de intencion a la misma hora recalibra tu sistema reticular activador — el filtro cerebral que decide que oportunidades notar.",
        "The Moon's cycle directly affects human fluid systems and sleep rhythms. Consistent evening practice syncs your nervous system to a calmer biological rhythm.":
            "El ciclo lunar afecta directamente los sistemas de fluidos y ritmos de sueno. La practica nocturna constante sincroniza tu sistema nervioso con un ritmo biologico mas calmado.",
        "High-intensity breath patterns (like Kapalabhati) activate the sympathetic nervous system constructively — releasing accumulated stress hormones without aggression.":
            "Los patrones de respiracion intensa activan el sistema nervioso simpatico de forma constructiva — liberando hormonas de estres acumuladas sin agresion.",
        "Vocal repetition of structured sound patterns activates Broca's area and the prefrontal cortex simultaneously — literally training clearer thinking and expression.":
            "La repeticion vocal de patrones de sonido estructurados activa el area de Broca y la corteza prefrontal simultaneamente — entrenando literalmente un pensamiento y expresion mas claros.",
        "21 days is the neurological minimum to form a new cognitive habit. Gratitude and expansion practices literally rewire the brain's default mode network toward opportunity-seeking.":
            "21 dias es el minimo neurologico para formar un nuevo habito cognitivo. Las practicas de gratitud y expansion literalmente reconectan la red de modo predeterminado del cerebro hacia la busqueda de oportunidades.",
        "Loving-kindness practices (the emotional equivalent of Venus remedies) measurably increase oxytocin, reduce cortisol, and improve relationship satisfaction within 21 days.":
            "Las practicas de bondad amorosa aumentan la oxitocina, reducen el cortisol y mejoran la satisfaccion en las relaciones en 21 dias.",
        "40 days is the clinical minimum for breaking a deeply ingrained behavioral pattern (used in addiction recovery, habit formation research). Saturn rules exactly this kind of structural change.":
            "40 dias es el minimo clinico para romper un patron conductual profundamente arraigado. Saturno gobierna exactamente este tipo de cambio estructural.",
        "18 days of consistent mindfulness around a specific pattern is enough to create metacognitive awareness — the ability to observe your own obsessive tendencies without being controlled by them.":
            "18 dias de atencion plena consistente alrededor de un patron especifico es suficiente para crear conciencia metacognitiva — la capacidad de observar tus propias tendencias obsesivas sin ser controlado por ellas.",
        "Detachment practices activate the default mode network differently than goal-focused thinking — they increase insight and creativity by reducing cognitive fixation.":
            "Las practicas de desapego activan la red de modo predeterminado de manera diferente al pensamiento enfocado en metas — aumentan la percepcion y creatividad al reducir la fijacion cognitiva.",
    }

    # --- Duration label translations ---
    DURATION_LABEL_ES = {
        "40 days without interruption": "40 dias sin interrupcion",
        "40 days": "40 dias",
        "21 days": "21 dias",
        "18 days": "18 dias",
        "11 days": "11 dias",
        "9 days": "9 dias",
        "7 days": "7 dias",
        "7 Tuesdays": "7 martes",
        "7 weeks": "7 semanas",
        "108 repetitions": "108 repeticiones",
        "This week": "Esta semana",
        "21 days — this is a priority cycle": "21 dias — este es un ciclo prioritario",
    }
    # --- Duration reason snippets ---
    DURATION_REASON_SNIPPETS_ES = {
        "7 mirrors the solar weekly cycle. One full week resets the pattern.": "7 refleja el ciclo solar semanal. Una semana completa reinicia el patron.",
        "11 is the number of emotional completion in Vedic numerology. One cycle of the Moon's emotional arc.": "11 es el numero de completacion emocional. Un ciclo del arco emocional lunar.",
        "Mars energy requires 7 consecutive Tuesday cycles to fully redirect. Tuesday is Mars's day — the energy is most receptive.": "La energia de Marte requiere 7 ciclos consecutivos de martes para redirigirse. El martes es el dia de Marte.",
        "9 completes a Mercury cognitive cycle. Enough repetition to build a new communication habit.": "9 completa un ciclo cognitivo de Mercurio. Suficiente repeticion para crear un nuevo habito de comunicacion.",
        "21 days (3 lunar weeks) is the minimum for Jupiter to shift a belief pattern. Jupiter is the slowest-moving benefic and requires sustained intention.": "21 dias (3 semanas lunares) es el minimo para que Jupiter cambie un patron de creencias.",
        "Venus rules 21-day relationship cycles. 21 days is enough to shift a core relationship pattern.": "Venus rige ciclos de relacion de 21 dias. 21 dias es suficiente para cambiar un patron de relacion fundamental.",
        "40 days is Saturn's minimum commitment cycle. Saturn governs long-term structures and only shifts through demonstrated sustained discipline.": "40 dias es el ciclo minimo de compromiso de Saturno. Saturno solo cambia a traves de disciplina sostenida demostrada.",
        "18 is Rahu's nodal completion number. 18 consecutive days creates one full Rahu micro-cycle.": "18 es el numero de completacion nodal de Rahu. 18 dias consecutivos crean un micro-ciclo completo de Rahu.",
        "Ketu works in 7-day release cycles. One week of consistent practice completes one detachment arc.": "Ketu trabaja en ciclos de 7 dias de liberacion. Una semana de practica consistente completa un arco de desapego.",
        "When multiple timing systems point to the same planet, 21 days of practice synchronizes your actions with the active energy window.": "Cuando multiples sistemas de tiempo apuntan al mismo planeta, 21 dias de practica sincronizan tus acciones con la ventana de energia activa.",
        "Some planetary energies only open on specific days of the week. 7 consecutive weeks on the right day completes one full planetary cycle.": "Algunas energias planetarias solo se abren en dias especificos. 7 semanas consecutivas en el dia correcto completan un ciclo planetario completo.",
        # --- Sleeping planet + Rin clearing duration reasons ---
        "A sleeping planet needs 21 days of consistent activation to wake up. Think of it as physical therapy for an underused muscle — skipping days resets the progress.": "Un planeta dormido necesita 21 dias de activacion consistente para despertar. Piensalo como fisioterapia para un musculo poco usado — saltarse dias reinicia el progreso.",
        "Karmic patterns took years to form. 40 uninterrupted days is the minimum to interrupt the cycle. Even one missed day traditionally requires restarting — not as punishment, but because the pattern needs continuous counter-pressure.": "Los patrones karmicos tardaron anos en formarse. 40 dias sin interrupcion es el minimo para interrumpir el ciclo. Incluso un dia perdido requiere reiniciar — no como castigo, sino porque el patron necesita presion contraria continua.",
    }

    # Apply full-text remedy_why translations
    # Translate sleeping_alerts and rin_cards
    if "sleeping_alerts" in s:
        for sa in s["sleeping_alerts"]:
            if "energy_label" in sa: sa["energy_label"]=L.get(sa["energy_label"],sa["energy_label"])
            if "remedy_why" in sa: sa["remedy_why"]=t_remedy_why(sa["remedy_why"])
            if "remedy_why_science" in sa: sa["remedy_why_science"]=t_remedy_why_science(sa["remedy_why_science"])
            if "duration_label" in sa: sa["duration_label"]=DURATION_LABEL_ES.get(sa["duration_label"], sa["duration_label"])
            if "duration" in sa: sa["duration"]=DURATION_LABEL_ES.get(sa["duration"], sa["duration"])
            if "duration_reason" in sa: sa["duration_reason"]=DURATION_REASON_SNIPPETS_ES.get(sa["duration_reason"], t(sa["duration_reason"]))
            for f in ("why","practice"):
                if f in sa: sa[f]=t(sa[f])
    if "rin_cards" in s:
        for rc in s["rin_cards"]:
            if "clearing_practice" in rc: rc["clearing_practice"]=t_remedy(rc["clearing_practice"])
            if "remedy_why" in rc: rc["remedy_why"]=t_remedy_why(rc["remedy_why"])
            if "remedy_why_science" in rc: rc["remedy_why_science"]=t_remedy_why_science(rc["remedy_why_science"])
            if "duration_label" in rc: rc["duration_label"]=DURATION_LABEL_ES.get(rc["duration_label"], rc["duration_label"])
            if "duration" in rc: rc["duration"]=DURATION_LABEL_ES.get(rc["duration"], rc["duration"])
            if "duration_reason" in rc: rc["duration_reason"]=DURATION_REASON_SNIPPETS_ES.get(rc["duration_reason"], t(rc["duration_reason"]))
            if "streak_warning" in rc and rc["streak_warning"]:
                _sw = rc["streak_warning"]
                if "Do not break the streak" in _sw: rc["streak_warning"] = "No rompas la racha. Si pierdes un dia, reinicia desde el dia 1."
            for f in ("why",):
                if f in rc: rc[f]=t(rc[f])
    # Translate primary_practice and supporting_practices
    # --- Completion milestone snippets ---
    MILESTONE_SNIPPETS_ES = {
        "After 7 days, notice whether opportunities for visibility feel more natural.": "Despues de 7 dias, nota si las oportunidades de visibilidad se sienten mas naturales.",
        "After 11 days, emotional decisions should feel less reactive and more grounded.": "Despues de 11 dias, las decisiones emocionales deberian sentirse menos reactivas y mas centradas.",
        "After 7 Tuesdays, notice whether impulsive decisions have decreased.": "Despues de 7 martes, nota si las decisiones impulsivas han disminuido.",
        "After 9 days, notice whether your communication feels more precise and less anxious.": "Despues de 9 dias, nota si tu comunicacion se siente mas precisa y menos ansiosa.",
        "After 21 days, notice whether mentors, teachers, or growth opportunities appear more readily.": "Despues de 21 dias, nota si mentores, maestros u oportunidades de crecimiento aparecen mas facilmente.",
        "After 21 days, notice whether your key relationships feel more fluid and less effortful.": "Despues de 21 dias, nota si tus relaciones clave se sienten mas fluidas y menos forzadas.",
        "After 40 days, notice whether patience in key situations has increased and whether chronic delays are easing.": "Despues de 40 dias, nota si la paciencia en situaciones clave ha aumentado y si los retrasos cronicos estan cediendo.",
        "After 18 days, notice whether obsessive thought loops around one particular desire have softened.": "Despues de 18 dias, nota si los bucles de pensamiento obsesivo alrededor de un deseo particular se han suavizado.",
        "After 7 days, notice whether one thing you have been holding onto feels lighter.": "Despues de 7 dias, nota si algo que has estado reteniendo se siente mas ligero.",
    }
    def _translate_practice_card(p):
        if not p: return
        if "what" in p: p["what"] = t_remedy(p["what"])
        if "practice_why" in p:
            p["practice_why"] = PRACTICE_WHY_ES.get(p["practice_why"], t(p["practice_why"]))
        if "practice_why_science" in p:
            p["practice_why_science"] = PRACTICE_WHY_SCIENCE_ES.get(p["practice_why_science"], t(p["practice_why_science"]))
        if "duration_label" in p:
            p["duration_label"] = DURATION_LABEL_ES.get(p["duration_label"], p["duration_label"])
        if "duration" in p:
            p["duration"] = DURATION_LABEL_ES.get(p["duration"], p["duration"])
        if "duration_reason" in p:
            p["duration_reason"] = DURATION_REASON_SNIPPETS_ES.get(p["duration_reason"], t(p["duration_reason"]))
        if "completion_milestone" in p:
            p["completion_milestone"] = MILESTONE_SNIPPETS_ES.get(p["completion_milestone"], t(p["completion_milestone"]))
    if "primary_practice" in s:
        _translate_practice_card(s["primary_practice"])
    if "supporting_practices" in s:
        for sp in s["supporting_practices"]:
            _translate_practice_card(sp)
    return s

@app.get("/api/v1/practices/{chart_id}/schedule")
async def get_practice_schedule_endpoint(chart_id: str, language: str = "es", refresh: bool = False):
    try:
        from datetime import date as _d, timedelta as _td
        _today = _d.today()
        _week_of = _today - _td(days=_today.weekday())
        if not refresh:
            _cache = supabase.table("practice_schedule_cache").select("schedule_data").eq("chart_id", chart_id).eq("week_of", _week_of.isoformat()).execute()
            if _cache.data and len(_cache.data) > 0:
                _sched = _cache.data[0]["schedule_data"]
                _streak = await _practice_get_streak(chart_id)
                _sched["streak_data"] = _streak
                if language == "es": _sched = _translate_practice_schedule_es(_sched)
                return {"status": "ok", "source": "cache", "schedule": _sched}
        _chart = supabase.table("charts").select("chart_data, jaimini_data, lal_kitab_data, current_country, birth_date").eq("id", chart_id).single().execute()
        if not _chart.data:
            return {"status": "error", "message": "Chart not found"}
        _c = _chart.data
        _streak = await _practice_get_streak(chart_id)

        # ── Fetch Vimsottari dasha periods (MD + AD) ──
        _vim_md = None
        _vim_ad = None
        _vim_next_md = None
        try:
            from datetime import date as _vd
            _vtoday = _vd.today().isoformat()
            _vim_res = supabase.table("dasha_periods").select(
                "planet_or_sign, start_date, end_date, level"
            ).eq("chart_id", chart_id).eq("system", "vimsottari").lte(
                "start_date", _vtoday
            ).gte("end_date", _vtoday).order("level").execute()
            for _vr in (_vim_res.data or []):
                if _vr.get("level") == 1:
                    _vim_md = _vr
                elif _vr.get("level") == 2:
                    _vim_ad = _vr
            if _vim_md:
                _vnext = supabase.table("dasha_periods").select(
                    "planet_or_sign, start_date, end_date"
                ).eq("chart_id", chart_id).eq("system", "vimsottari").eq(
                    "level", 1
                ).gt("start_date", _vim_md.get("end_date", "")).order(
                    "start_date"
                ).limit(1).execute()
                if _vnext.data:
                    _vim_next_md = _vnext.data[0]
        except Exception as _ve:
            print(f"[PRACTICE] Vimsottari fetch error (non-fatal): {_ve}")

        # ── Fetch practice completions for last 30 days ──
        _practice_counts = {}
        try:
            from datetime import datetime as _pdt, timedelta as _ptd
            _30ago = (_pdt.now() - _ptd(days=30)).isoformat()
            _plog = supabase.table("practice_log").select(
                "planet, completed_at"
            ).eq("chart_id", chart_id).gte(
                "completed_at", _30ago
            ).execute()
            for _pr_row in (_plog.data or []):
                _pp = _pr_row.get("planet", "")
                _practice_counts[_pp] = _practice_counts.get(_pp, 0) + 1
        except Exception as _ple:
            print(f"[PRACTICE] Practice log fetch error (non-fatal): {_ple}")

        _sched = generate_practice_schedule(
            chart_data=_safe_jsonb(_c.get("chart_data")),
            jaimini_data=_safe_jsonb(_c.get("jaimini_data")),
            lal_kitab_data=_safe_jsonb(_c.get("lal_kitab_data")),
            current_country=_c.get("current_country", "US"),
            birth_date=_c.get("birth_date"),
            streak_data=_streak,
            vimsottari_md=_vim_md,
            vimsottari_ad=_vim_ad,
            next_md=_vim_next_md,
            practice_counts=_practice_counts,
        )
        try:
            supabase.table("practice_schedule_cache").upsert({"chart_id": chart_id, "week_of": _week_of.isoformat(), "cache_key": _sched.get("cache_key", ""), "schedule_data": _sched}, on_conflict="chart_id,week_of").execute()
        except Exception:
            pass
        if language == "es": _sched = _translate_practice_schedule_es(_sched)
        return {"status": "ok", "source": "generated", "schedule": _sched}
    except Exception as e:
        print(f"[PRACTICE] Schedule error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/practices/{chart_id}/complete")
async def complete_practice_endpoint(chart_id: str, req: _PracticeCompleteReq):
    try:
        from datetime import datetime as _dt, date as _d, timedelta as _td
        _now = _dt.utcnow()
        _streak = await _practice_calc_streak(chart_id, _d.today())
        _planet = "Unknown"
        _ptype = "remedy"
        _planets = ["sun","moon","mars","mercury","jupiter","venus","saturn","rahu","ketu"]
        _types = ["convergence","awakening","remedy","rin_clearing","mantra"]
        for _p in req.practice_id.lower().split("_"):
            if _p in _planets: _planet = _p.capitalize()
            if _p in _types: _ptype = _p
        supabase.table("practice_log").insert({"chart_id": chart_id, "practice_id": req.practice_id, "planet": _planet, "practice_type": _ptype, "completed_at": _now.isoformat(), "streak_count": _streak + 1, "user_note": req.user_note}).execute()
        _new = _streak + 1
        if _new == 7: _msg = "7-day streak unlocked! You earned a free Deep Dive Location Audit."
        elif _new == 21: _msg = "21-day cycle complete. Your energy pattern has shifted."
        elif _new >= 3: _msg = f"{_new}-day streak! Consistency is building momentum."
        else: _msg = "Practice logged. Every day counts."
        return {"status": "ok", "streak_count": _new, "message": _msg}
    except Exception as e:
        print(f"[PRACTICE] Complete error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/v1/practices/{chart_id}/streak")
async def get_practice_streak_endpoint(chart_id: str):
    try:
        from datetime import date as _d, timedelta as _td
        _today = _d.today()
        _30ago = _today - _td(days=30)
        _log = supabase.table("practice_log").select("practice_id, practice_type, completed_at, streak_count, user_note, energy_label").eq("chart_id", chart_id).gte("created_at", _30ago.isoformat()).order("completed_at", desc=True).execute()
        _completions = _log.data or []
        _current = await _practice_calc_streak(chart_id, _today)
        _longest = max([c.get("streak_count", 0) for c in _completions], default=0)
        _longest = max(_longest, _current)
        _total = len([c for c in _completions if c.get("completed_at")])
        _cal = {}
        for c in _completions:
            if c.get("completed_at"):
                _cal[c["completed_at"][:10]] = {"practice_id": c.get("practice_id"), "practice_type": c.get("practice_type"), "note": c.get("user_note")}
        return {"status": "ok", "chart_id": chart_id, "current_streak": _current, "longest_streak": _longest, "total_completed": _total, "completion_rate": round(_total / 30 * 100) if _total else 0, "calendar": _cal, "history": _completions[:20]}
    except Exception as e:
        print(f"[PRACTICE] Streak error: {e}")
        return {"status": "error", "message": str(e)}

async def _practice_calc_streak(chart_id: str, today) -> int:
    try:
        from datetime import timedelta as _td
        _60ago = today - _td(days=60)
        _log = supabase.table("practice_log").select("completed_at").eq("chart_id", chart_id).not_.is_("completed_at", "null").gte("completed_at", _60ago.isoformat()).order("completed_at", desc=True).execute()
        if not _log.data: return 0
        _dates = set()
        for r in _log.data:
            if r.get("completed_at"): _dates.add(r["completed_at"][:10])
        _streak = 0
        _check = today
        if _check.isoformat() not in _dates:
            _check = today - _td(days=1)
            if _check.isoformat() not in _dates: return 0
        while _check.isoformat() in _dates:
            _streak += 1
            _check -= _td(days=1)
        return _streak
    except Exception:
        return 0

async def _practice_get_streak(chart_id: str) -> dict:
    from datetime import date as _d
    _current = await _practice_calc_streak(chart_id, _d.today())
    try:
        _max = supabase.table("practice_log").select("streak_count").eq("chart_id", chart_id).order("streak_count", desc=True).limit(1).execute()
        _longest = _max.data[0]["streak_count"] if _max.data else 0
    except Exception:
        _longest = 0
    try:
        _cnt = supabase.table("practice_log").select("id", count="exact").eq("chart_id", chart_id).not_.is_("completed_at", "null").execute()
        _total = _cnt.count or 0
    except Exception:
        _total = 0
    return {"current": max(_current, 0), "longest": max(_longest, _current), "total_completed": _total}

# ═══ END SPRINT P ENDPOINTS ═══


# ═══════════════════════════════════════════════════════════════
# VERIFICATION QUEUE — Sprint 1.4
# Generates binary verification questions from dasha history
# Powers the Precision Score gamification loop
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/verification/{chart_id}")
async def get_verification(chart_id: str):
    """
    Returns verification queue + precision score.
    Frontend uses this for the interactive Level Ring / SYSTEM AUDIT drawer.
    """
    try:
        data = await get_verification_data(chart_id, supabase)
        return data
    except Exception as e:
        logger.error(f"Verification endpoint failed: {e}")
        return {
            "verification_queue": [],
            "precision_score": {"level": 1, "level_display": "1", "total_rated": 0, "accuracy_pct": 0, "next_level_in": 2, "max_level": 10},
            "has_pending": False,
            "message": "Verification data unavailable.",
        }



# ═══════════════════════════════════════════════════════════════
# DASHBOARD STATUS — Sprint 1.2
# Returns live sensor data with active symptoms for each domain
# Powers the "Flight Deck" dashboard view
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# CLIENT ERROR LOGGING
# Frontend posts JS crashes here → visible in Railway logs
# grep: [CLIENT_ERROR]
# ═══════════════════════════════════════════════════════════════════

class ClientErrorRequest(BaseModel):
    msg: str = ""
    src: str = ""
    line: int = 0
    col: int = 0
    stack: str = ""
    chart_id: str = ""
    url: str = ""
    user_agent: str = ""

@app.post("/api/v1/client-error")
async def log_client_error(payload: ClientErrorRequest):
    import logging as _logging
    _log = _logging.getLogger("antar.client")
    try:
        _log.error(
            "[CLIENT_ERROR] chart=%s url=%s msg=%s src=%s:%s:%s stack=%s",
            payload.chart_id or "unknown",
            payload.url or "",
            payload.msg or "",
            payload.src or "",
            payload.line or 0,
            payload.col or 0,
            (payload.stack or "")[:500],
        )
    except Exception as _e:
        print(f"[CLIENT_ERROR] logging failed: {_e}")
    return {"ok": True}


@app.get("/api/v1/dashboard-status/{chart_id}")
async def get_dashboard_status(chart_id: str):
    """
    Returns the diagnostic status for all 4 domains + precision score.
    Used by the frontend Status tab to show AUTHORITY ENGINE: HIGH FRICTION etc.
    """
    try:
        # Load chart data
        chart_result = supabase.table("charts").select("chart_data").eq("id", chart_id).single().execute()
        if not chart_result.data:
            return {"error": "Chart not found"}, 404
        
        chart_data = chart_result.data.get("chart_data", {})
        
        # Get domain status from symptom library
        domain_status = get_domain_status(chart_data)
        
        # Get precision score
        precision = await calculate_precision_score(chart_id, supabase)
        
        # Get all active symptoms
        all_symptoms = scan_chart_symptoms(chart_data)
        
        return {
            "domains": {
                "career": {
                    "label": "AUTHORITY ENGINE",
                    **domain_status.get("career", {}),
                },
                "wealth": {
                    "label": "CAPITAL RUNWAY",
                    **domain_status.get("wealth", {}),
                },
                "relationship": {
                    "label": "ALLIANCE SYNC",
                    **domain_status.get("relationship", {}),
                },
                "health": {
                    "label": "SYSTEM VITALS",
                    **domain_status.get("health", {}),
                },
            },
            "precision_score": precision,
            "total_active_symptoms": len(all_symptoms),
            "critical_symptoms": [s for s in all_symptoms if s["verdict"] in ("HIBERNATE", "RETREAT AND RESET", "PLUG THE LEAK", "RECOVERY MODE")],
        }
    except Exception as e:
        logger.error(f"Dashboard status failed: {e}")
        return {
            "domains": {},
            "precision_score": {"level": 1, "total_rated": 0},
            "total_active_symptoms": 0,
            "critical_symptoms": [],
        }



# ═══════════════════════════════════════════════════════════════════
# ARCHETYPAL MATRIX — 27 Fields × 12 Modes = 324 action signatures
# Layer 2 of the WOW signal engine
# Source: Nakshatra FIELD + Sign MODE intersection system
# ═══════════════════════════════════════════════════════════════════

_FIELD_MODE_MATRIX = {
    # ASHWINI → IGNITION FIELD
    ("IGNITION","DRIVE"):      ("launch ignition",    "Start something now. The window is open."),
    ("IGNITION","BUILD"):      ("spark assembly",     "Assemble the pieces you have been gathering."),
    ("IGNITION","CONNECT"):    ("ignite exchange",    "A conversation today could start something significant."),
    ("IGNITION","PROTECT"):    ("flash shield",       "Act fast to protect what is just beginning."),
    ("IGNITION","LEAD"):       ("fire charge",        "Take the lead before the moment passes."),
    ("IGNITION","REFINE"):     ("spark calibration",  "One precise adjustment today unlocks momentum."),
    ("IGNITION","BALANCE"):    ("ignite equilibrium", "Restore balance quickly — the energy will not wait."),
    ("IGNITION","PENETRATE"):  ("pierce ignition",    "Cut through the noise and start the real thing."),
    ("IGNITION","EXPAND"):     ("blast outward",      "Push beyond your current boundary today."),
    ("IGNITION","STRUCTURE"):  ("frame ignition",     "Build the container before you light the fire."),
    ("IGNITION","DISRUPT"):    ("short-circuit start","Something unexpected breaks the usual launch pattern."),
    ("IGNITION","DISSOLVE"):   ("burn into mist",     "Let go of what is stalling. The energy will rebuild."),

    # BHARANI → THRESHOLD FIELD
    ("THRESHOLD","DRIVE"):     ("cross first line",   "Make the first move. Hesitation costs you the crossing."),
    ("THRESHOLD","BUILD"):     ("anchor threshold",   "Secure your position before moving through."),
    ("THRESHOLD","CONNECT"):   ("bridge entry",       "Your network is the key that opens this door."),
    ("THRESHOLD","PROTECT"):   ("guard the gate",     "Protect what you are about to enter. Not everything gets in."),
    ("THRESHOLD","LEAD"):      ("command crossing",   "Lead others through. Your authority creates the passage."),
    ("THRESHOLD","REFINE"):    ("clean threshold",    "Clear the path before you cross. Preparation is the move."),
    ("THRESHOLD","BALANCE"):   ("even passage",       "Both sides must be ready before you commit."),
    ("THRESHOLD","PENETRATE"): ("force through",      "The door will not open easily. Push anyway."),
    ("THRESHOLD","EXPAND"):    ("widen entry",        "Make room for more than just yourself."),
    ("THRESHOLD","STRUCTURE"): ("frame the door",     "Define the terms of entry before you walk through."),
    ("THRESHOLD","DISRUPT"):   ("break lintel",       "The old threshold is gone. Build a new one."),
    ("THRESHOLD","DISSOLVE"):  ("melt boundary",      "The limit you thought was fixed is not."),

    # KRITTIKA → PRECISION FIELD
    ("PRECISION","DRIVE"):     ("cut sharp",          "Move fast but cut clean. Speed without precision wastes the strike."),
    ("PRECISION","BUILD"):     ("measure twice",      "Do not build until you have the exact spec."),
    ("PRECISION","CONNECT"):   ("align joints",       "The connection only holds if the fit is exact."),
    ("PRECISION","PROTECT"):   ("guard the point",    "Defend the specific thing, not the general territory."),
    ("PRECISION","LEAD"):      ("sight target",       "Name the exact goal before you move the team."),
    ("PRECISION","REFINE"):    ("hone edge",          "One more pass of refinement changes the outcome."),
    ("PRECISION","BALANCE"):   ("level zero",         "Find exact center before you proceed."),
    ("PRECISION","PENETRATE"): ("needle strike",      "You know exactly where to press. Do it now."),
    ("PRECISION","EXPAND"):    ("scatter shot",       "Precision is lost in expansion mode. Pick one target."),
    ("PRECISION","STRUCTURE"): ("grid placement",     "Place each element exactly where it belongs."),
    ("PRECISION","DISRUPT"):   ("detune aim",         "Your aim is off today. Recalibrate before acting."),
    ("PRECISION","DISSOLVE"):  ("blur margins",       "Precision is not available. Work with approximation."),

    # ROHINI → GROWTH FIELD
    ("GROWTH","DRIVE"):        ("push growth",        "Apply direct energy to what is already growing."),
    ("GROWTH","BUILD"):        ("root foundation",    "Deepen the roots before you reach for height."),
    ("GROWTH","CONNECT"):      ("branch weave",       "Grow through connection. Reach toward others."),
    ("GROWTH","PROTECT"):      ("nourish cover",      "Protect the growing thing. It is not yet strong."),
    ("GROWTH","LEAD"):         ("crown rise",         "Your leadership creates the conditions for others to grow."),
    ("GROWTH","REFINE"):       ("prune shape",        "Cut what is not serving. Pruning is growth."),
    ("GROWTH","BALANCE"):      ("equal feed",         "Distribute resources evenly. Unbalanced growth collapses."),
    ("GROWTH","PENETRATE"):    ("root drill",         "Go deeper before you go higher. The roots decide everything."),
    ("GROWTH","EXPAND"):       ("wild spread",        "Growth is expansive today. Let it move without forcing direction."),
    ("GROWTH","STRUCTURE"):    ("trellis frame",      "Give the growing thing a structure to climb."),
    ("GROWTH","DISRUPT"):      ("graft shock",        "Introduce a foreign element to accelerate growth."),
    ("GROWTH","DISSOLVE"):     ("rot into soil",      "What is dying is feeding what comes next."),

    # MRIGASHIRA → DISCOVERY FIELD
    ("DISCOVERY","DRIVE"):     ("chase scent",        "Follow the lead. The answer is close — keep moving."),
    ("DISCOVERY","BUILD"):     ("track map",          "Document what you are finding. The map is the asset."),
    ("DISCOVERY","CONNECT"):   ("follow thread",      "Pull the thread someone else left. It leads somewhere."),
    ("DISCOVERY","PROTECT"):   ("hide trail",         "Do not reveal what you are looking for yet."),
    ("DISCOVERY","LEAD"):      ("unveil find",        "Share the discovery. Your leadership is the reveal."),
    ("DISCOVERY","REFINE"):    ("filter clue",        "Not all signals are real. Filter before you act."),
    ("DISCOVERY","BALANCE"):   ("weigh evidence",     "Consider both interpretations before you conclude."),
    ("DISCOVERY","PENETRATE"): ("dig secret",         "The answer is buried. Go deeper than the surface."),
    ("DISCOVERY","EXPAND"):    ("roam unknown",       "Leave the map behind. Today rewards wandering."),
    ("DISCOVERY","STRUCTURE"): ("catalog find",       "Organize what you have discovered before searching further."),
    ("DISCOVERY","DISRUPT"):   ("false signal",       "What you think you found may be misleading. Verify."),
    ("DISCOVERY","DISSOLVE"):  ("lose trail",         "The trail goes cold. Let go and start fresh tomorrow."),

    # ARDRA → STORM FIELD
    ("STORM","DRIVE"):         ("thunder charge",     "Move with force. The storm is behind you."),
    ("STORM","BUILD"):         ("lightning rod",      "Make yourself the conductor. Channel the disruption."),
    ("STORM","CONNECT"):       ("arc between",        "The storm creates connection between opposites."),
    ("STORM","PROTECT"):       ("shelter squall",     "Get the important things under cover before it hits."),
    ("STORM","LEAD"):          ("eye command",        "Lead from the calm center. The storm obeys the eye."),
    ("STORM","REFINE"):        ("calm debris",        "After the disruption, clean and refine what remains."),
    ("STORM","BALANCE"):       ("pressure equal",     "Balance the pressure on both sides or it breaks."),
    ("STORM","PENETRATE"):     ("strike deep",        "The storm opens things that were sealed. Go in now."),
    ("STORM","EXPAND"):        ("hurricane spread",   "The disruption is spreading. Decide if you ride it or shelter."),
    ("STORM","STRUCTURE"):     ("dam flood",          "Contain the chaos before it destroys the structure."),
    ("STORM","DISRUPT"):       ("random bolt",        "Something unpredictable hits. Do not over-interpret it."),
    ("STORM","DISSOLVE"):      ("rain into sea",      "Let the storm pass through you. Resistance makes it worse."),

    # PUNARVASU → RECOVERY FIELD
    ("RECOVERY","DRIVE"):      ("rebound fast",       "You have enough to move again. Do not wait for full recovery."),
    ("RECOVERY","BUILD"):      ("rebuild home",       "Start reconstruction now. The foundation is still sound."),
    ("RECOVERY","CONNECT"):    ("restitch bond",      "The connection that frayed can be repaired today."),
    ("RECOVERY","PROTECT"):    ("nurse wound",        "Give the injured thing what it needs. Do not rush it."),
    ("RECOVERY","LEAD"):       ("restore order",      "Your leadership is needed to rebuild what was lost."),
    ("RECOVERY","REFINE"):     ("clean infection",    "Remove what is corrupted before rebuilding."),
    ("RECOVERY","BALANCE"):    ("return center",      "You have drifted. Today is for coming back to yourself."),
    ("RECOVERY","PENETRATE"):  ("extract poison",     "Go into the wound and remove what is causing the damage."),
    ("RECOVERY","EXPAND"):     ("renew hope",         "The recovery opens a wider possibility than before."),
    ("RECOVERY","STRUCTURE"):  ("restore system",     "Rebuild the system first. Everything else depends on it."),
    ("RECOVERY","DISRUPT"):    ("heal broken",        "Unconventional healing is what is needed now."),
    ("RECOVERY","DISSOLVE"):   ("release trauma",     "Let the memory of the wound go. It is keeping you sick."),

    # PUSHYA → ANCHOR FIELD
    ("ANCHOR","DRIVE"):        ("anchor drag",        "Your speed is limited today. Work with the resistance."),
    ("ANCHOR","BUILD"):        ("foundation lock",    "Lock the foundation before you build higher."),
    ("ANCHOR","CONNECT"):      ("tether link",        "Create a connection that holds under pressure."),
    ("ANCHOR","PROTECT"):      ("hold safe",          "Your job today is to keep things stable. That is enough."),
    ("ANCHOR","LEAD"):         ("steady command",     "Lead with calm authority. Stability is your value today."),
    ("ANCHOR","REFINE"):       ("secure detail",      "Lock down the specifics. Loose ends create drift."),
    ("ANCHOR","BALANCE"):      ("weight center",      "Add ballast to what is rocking."),
    ("ANCHOR","PENETRATE"):    ("root spike",         "Drive the anchor deeper. The ground can take more."),
    ("ANCHOR","EXPAND"):       ("stretch anchor",     "You can grow but only as far as the anchor allows."),
    ("ANCHOR","STRUCTURE"):    ("pillar brace",       "Reinforce the structural supports. Now is the time."),
    ("ANCHOR","DISRUPT"):      ("break mooring",      "Something cuts the anchor loose. Decide if that is freedom or danger."),
    ("ANCHOR","DISSOLVE"):     ("sink anchor",        "Let it go to the bottom. Some things need to be released."),

    # ASHLESHA → STRATEGY FIELD
    ("STRATEGY","DRIVE"):      ("ambush rush",        "Move before they see you coming."),
    ("STRATEGY","BUILD"):      ("trap layout",        "Set the conditions before you make the ask."),
    ("STRATEGY","CONNECT"):    ("weave net",          "Build the web of connections now. You will need it later."),
    ("STRATEGY","PROTECT"):    ("coil defense",       "Wrap your position in layers. Do not expose the core."),
    ("STRATEGY","LEAD"):       ("chess move",         "Think three moves ahead before you act."),
    ("STRATEGY","REFINE"):     ("adjust plot",        "The strategy needs one adjustment. Find it."),
    ("STRATEGY","BALANCE"):    ("counterweight",      "Match their move with a counter. Do not over-respond."),
    ("STRATEGY","PENETRATE"):  ("venom strike",       "One precisely placed move neutralizes the threat."),
    ("STRATEGY","EXPAND"):     ("spread scheme",      "Widen the strategy. You are thinking too small."),
    ("STRATEGY","STRUCTURE"):  ("ladder plan",        "Build the strategy step by step. No shortcuts today."),
    ("STRATEGY","DISRUPT"):    ("break pattern",      "The expected move is the wrong move. Surprise them."),
    ("STRATEGY","DISSOLVE"):   ("vanish tactic",      "Withdraw the strategy. Make them think you have stopped."),

    # MAGHA → COMMAND FIELD
    ("COMMAND","DRIVE"):       ("order charge",       "Issue the directive and move. Your authority is the momentum."),
    ("COMMAND","BUILD"):       ("throne raise",       "Build the seat of power before you sit in it."),
    ("COMMAND","CONNECT"):     ("council call",       "Gather the key people. Command through consultation today."),
    ("COMMAND","PROTECT"):     ("shield reign",       "Defend your authority. Someone is testing it."),
    ("COMMAND","LEAD"):        ("crown decree",       "Make the decision only you can make. Do not delegate this one."),
    ("COMMAND","REFINE"):      ("audit rule",         "Review the rules you operate by. One needs updating."),
    ("COMMAND","BALANCE"):     ("judge seat",         "You are being asked to adjudicate. Be fair and decisive."),
    ("COMMAND","PENETRATE"):   ("purge command",      "Remove what is undermining your authority. Now."),
    ("COMMAND","EXPAND"):      ("empire spread",      "Your reach extends today. Use it deliberately."),
    ("COMMAND","STRUCTURE"):   ("hierarchy set",      "Clarify who reports to whom. Ambiguity is costing you."),
    ("COMMAND","DISRUPT"):     ("overthrow",          "The old authority structure is breaking. Position yourself."),
    ("COMMAND","DISSOLVE"):    ("abdicate mist",      "Step back from command. Let someone else hold it today."),

    # PURVA PHALGUNI → MAGNETISM FIELD
    ("MAGNETISM","DRIVE"):     ("pull charge",        "Your energy attracts today. Move toward what you want."),
    ("MAGNETISM","BUILD"):     ("attract mass",       "Build something worth gathering around."),
    ("MAGNETISM","CONNECT"):   ("charm link",         "Your personal magnetism opens doors today. Use it."),
    ("MAGNETISM","PROTECT"):   ("draw close",         "Pull your key people closer. Proximity is protection."),
    ("MAGNETISM","LEAD"):      ("magnetic presence",  "You do not need to speak loudly. Your presence is the signal."),
    ("MAGNETISM","REFINE"):    ("polish lure",        "Make the offer more attractive. One refinement changes everything."),
    ("MAGNETISM","BALANCE"):   ("equal attraction",   "You are attracting competing forces. Choose what you want."),
    ("MAGNETISM","PENETRATE"): ("hypnotic pull",      "Your influence cuts deep today. Use it responsibly."),
    ("MAGNETISM","EXPAND"):    ("spread charisma",    "Your reach is wider today. Show up in more places."),
    ("MAGNETISM","STRUCTURE"): ("frame allure",       "Create the context that makes you magnetic."),
    ("MAGNETISM","DISRUPT"):   ("repel field",        "Something is pushing the right people away. Find and remove it."),
    ("MAGNETISM","DISSOLVE"):  ("fade attraction",    "The magnetism is low today. Do not force connection."),

    # UTTARA PHALGUNI → FOUNDATION FIELD
    ("FOUNDATION","DRIVE"):    ("push bedrock",       "Drive into the foundation work. It is not glamorous but it is the move."),
    ("FOUNDATION","BUILD"):    ("lay stone",          "Every stone placed today is permanent. Work with that weight."),
    ("FOUNDATION","CONNECT"):  ("join base",          "Connect at the foundational level — values, not surface."),
    ("FOUNDATION","PROTECT"):  ("shield footing",     "Protect the base. If it cracks, everything above follows."),
    ("FOUNDATION","LEAD"):     ("throne base",        "Your authority rests on the foundation you have built. Stand on it."),
    ("FOUNDATION","REFINE"):   ("level ground",       "The ground is not level. Fix it before you build."),
    ("FOUNDATION","BALANCE"):  ("even footing",       "Ensure both parties are on equal ground before proceeding."),
    ("FOUNDATION","PENETRATE"):("drill pier",         "Go through the soft ground to the bedrock below."),
    ("FOUNDATION","EXPAND"):   ("widen base",         "Before expanding up, expand the base. Support the growth."),
    ("FOUNDATION","STRUCTURE"):("column grid",        "Place the structural columns in the right positions."),
    ("FOUNDATION","DISRUPT"):  ("crack slab",         "The foundation has a fault. Find it before it finds you."),
    ("FOUNDATION","DISSOLVE"): ("earth to mud",       "The ground is unstable today. Do not build."),

    # HASTA → EXECUTION FIELD
    ("EXECUTION","DRIVE"):     ("strike hand",        "Act now. The moment is in your hands."),
    ("EXECUTION","BUILD"):     ("craft tool",         "Build the instrument you need. Then use it."),
    ("EXECUTION","CONNECT"):   ("finger weave",       "Execute through collaboration. Your hands and theirs."),
    ("EXECUTION","PROTECT"):   ("palm guard",         "Shield the execution. Do not let interference reach it."),
    ("EXECUTION","LEAD"):      ("direct hand",        "Lead by doing. Show them the execution, do not just describe it."),
    ("EXECUTION","REFINE"):    ("perfect grip",       "Adjust your hold before you apply force."),
    ("EXECUTION","BALANCE"):   ("steady hand",        "Precision and patience. Do not rush the execution."),
    ("EXECUTION","PENETRATE"): ("dagger fist",        "Execute with surgical precision. One clean move."),
    ("EXECUTION","EXPAND"):    ("throw wide",         "Execute at scale. What worked small will work large today."),
    ("EXECUTION","STRUCTURE"): ("finger frame",       "Structure the execution step by step. No improvisation."),
    ("EXECUTION","DISRUPT"):   ("drop tool",          "Put it down. The execution is wrong. Reset."),
    ("EXECUTION","DISSOLVE"):  ("open hand",          "Release control of the outcome. Execute and let go."),

    # CHITRA → DESIGN FIELD
    ("DESIGN","DRIVE"):        ("sketch fast",        "Get the idea down now before it fades. Refine later."),
    ("DESIGN","BUILD"):        ("model clay",         "Build the prototype. Touch it. Test it."),
    ("DESIGN","CONNECT"):      ("pattern link",       "Find the pattern that connects the disparate pieces."),
    ("DESIGN","PROTECT"):      ("shell design",       "Design the container first. What holds the thing matters."),
    ("DESIGN","LEAD"):         ("blueprint crown",    "Your vision is the design. Share it clearly."),
    ("DESIGN","REFINE"):       ("trace line",         "Follow the existing line with more precision."),
    ("DESIGN","BALANCE"):      ("symmetry draft",     "Find the symmetry. The design needs a mirror."),
    ("DESIGN","PENETRATE"):    ("cut pattern",        "Cut through the noise to the essential form."),
    ("DESIGN","EXPAND"):       ("scale render",       "The design works at this size. Scale it up now."),
    ("DESIGN","STRUCTURE"):    ("grid plan",          "Put the design on the grid. Structure before beauty."),
    ("DESIGN","DISRUPT"):      ("break form",         "The existing design is wrong. Start from a different assumption."),
    ("DESIGN","DISSOLVE"):     ("melt shape",         "Let the design become fluid. The form is not yet decided."),

    # SWATI → ADAPTATION FIELD
    ("ADAPTATION","DRIVE"):    ("pivot charge",       "Change direction at full speed. Do not slow down to adapt."),
    ("ADAPTATION","BUILD"):    ("flex frame",         "Build in adaptability from the start."),
    ("ADAPTATION","CONNECT"):  ("reroute link",       "The direct path is blocked. Find the alternate connection."),
    ("ADAPTATION","PROTECT"):  ("bend shell",         "Flex the defense. Rigidity will break under this pressure."),
    ("ADAPTATION","LEAD"):     ("shift stance",       "Change your leadership approach. What worked before will not work now."),
    ("ADAPTATION","REFINE"):   ("tune drift",         "Minor adjustments to stay on course. Constant small corrections."),
    ("ADAPTATION","BALANCE"):  ("sway center",        "Move with the change while keeping your core stable."),
    ("ADAPTATION","PENETRATE"):("change angle",       "The direct approach is not working. Come at it from a different angle."),
    ("ADAPTATION","EXPAND"):   ("stretch fit",        "Expand your capacity to meet the new demand."),
    ("ADAPTATION","STRUCTURE"):("modular shift",      "Redesign for flexibility. Lock nothing down permanently."),
    ("ADAPTATION","DISRUPT"):  ("break adapt",        "Your adaptation pattern itself needs disrupting."),
    ("ADAPTATION","DISSOLVE"): ("flow around",        "Do not fight the obstacle. Flow around it."),

    # VISHAKHA → AMBITION FIELD
    ("AMBITION","DRIVE"):      ("climb fast",         "The window is open. Move toward the goal aggressively."),
    ("AMBITION","BUILD"):      ("ladder rise",        "Build each rung deliberately. The climb is the work."),
    ("AMBITION","CONNECT"):    ("network up",         "Your next level is one connection away. Make contact today."),
    ("AMBITION","PROTECT"):    ("secure gain",        "Lock in what you have already achieved before reaching further."),
    ("AMBITION","LEAD"):       ("throne reach",       "The position you want is reachable today. Reach."),
    ("AMBITION","REFINE"):     ("polish path",        "One refinement to your approach changes your trajectory."),
    ("AMBITION","BALANCE"):    ("scale even",         "Do not sacrifice one area of ambition for another today."),
    ("AMBITION","PENETRATE"):  ("tunnel up",          "Dig through the obstacle. The ambition is worth the effort."),
    ("AMBITION","EXPAND"):     ("leap far",           "Think bigger. The goal you have set is too small."),
    ("AMBITION","STRUCTURE"):  ("step ascent",        "Map the exact steps. Ambition without structure is fantasy."),
    ("AMBITION","DISRUPT"):    ("break ceiling",      "The limit is artificial. Push through it."),
    ("AMBITION","DISSOLVE"):   ("dissolve goal",      "The goal you are chasing is no longer right. Let it go."),

    # ANURADHA → ALLIANCE FIELD
    ("ALLIANCE","DRIVE"):      ("pact charge",        "Move together. The alliance is the force multiplier."),
    ("ALLIANCE","BUILD"):      ("bond forge",         "Create a commitment that holds under pressure."),
    ("ALLIANCE","CONNECT"):    ("handshake",          "The connection made today formalizes into partnership."),
    ("ALLIANCE","PROTECT"):    ("shield circle",      "The alliance is under threat. Protect it actively."),
    ("ALLIANCE","LEAD"):       ("alliance lead",      "Lead through partnership. Your power today is relational."),
    ("ALLIANCE","REFINE"):     ("clean oath",         "Clarify the terms of the alliance. Ambiguity creates cracks."),
    ("ALLIANCE","BALANCE"):    ("equal pact",         "Ensure the alliance benefits both parties equally."),
    ("ALLIANCE","PENETRATE"):  ("blood bond",         "Go deep in the commitment. Surface alliances will not hold."),
    ("ALLIANCE","EXPAND"):     ("spread union",       "Bring more people into the alliance. Expand the circle."),
    ("ALLIANCE","STRUCTURE"):  ("treaty frame",       "Formalize the agreement. Verbal commitments are not enough today."),
    ("ALLIANCE","DISRUPT"):    ("break alliance",     "An alliance that was serving you is now limiting you."),
    ("ALLIANCE","DISSOLVE"):   ("merge dissolve",     "The boundaries between you and your partner are dissolving. Decide if that is good."),

    # JYESHTHA → AUTHORITY FIELD
    ("AUTHORITY","DRIVE"):     ("power rush",         "Move with the full weight of your authority. Do not hesitate."),
    ("AUTHORITY","BUILD"):     ("throne build",       "Build the structure that makes your authority permanent."),
    ("AUTHORITY","CONNECT"):   ("command link",       "Your authority creates the connection. Use it to open doors."),
    ("AUTHORITY","PROTECT"):   ("shield rule",        "Defend your position. Someone is testing your authority."),
    ("AUTHORITY","LEAD"):      ("absolute lead",      "Take complete ownership of the decision. No committee today."),
    ("AUTHORITY","REFINE"):    ("audit power",        "Review how you are using your authority. One thing needs adjusting."),
    ("AUTHORITY","BALANCE"):   ("judge authority",    "You are being asked to make a ruling. Be fair and final."),
    ("AUTHORITY","PENETRATE"): ("deep command",       "Your authority cuts beneath the surface today. Use it surgically."),
    ("AUTHORITY","EXPAND"):    ("empire law",         "Extend your authority into new territory today."),
    ("AUTHORITY","STRUCTURE"): ("hierarchy lock",     "Clarify the chain of command. Ambiguity is undermining you."),
    ("AUTHORITY","DISRUPT"):   ("rebel authority",    "Challenge the authority above you. The timing is right."),
    ("AUTHORITY","DISSOLVE"):  ("fade power",         "Your authority is not effective today. Work through others."),

    # MULA → ROOT FIELD
    ("ROOT","DRIVE"):          ("tear root",          "Pull out what is blocking you at the source."),
    ("ROOT","BUILD"):          ("ground root",        "Plant the seed of something permanent today."),
    ("ROOT","CONNECT"):        ("root weave",         "Connect at the deepest level — origin, not surface."),
    ("ROOT","PROTECT"):        ("root hide",          "Protect the origin. Do not expose your core motivation."),
    ("ROOT","LEAD"):           ("tap deep",           "Lead from your deepest conviction today. Not strategy — truth."),
    ("ROOT","REFINE"):         ("prune root",         "Cut the root that is diverting your energy."),
    ("ROOT","BALANCE"):        ("equal depth",        "Both sides of the situation have deep roots. Honor that."),
    ("ROOT","PENETRATE"):      ("dig origin",         "Go to the source of the problem. The surface is a symptom."),
    ("ROOT","EXPAND"):         ("spread rhizome",     "Grow underground first. The visible expansion comes later."),
    ("ROOT","STRUCTURE"):      ("root system",        "Map the underlying structure. What feeds what."),
    ("ROOT","DISRUPT"):        ("uproot",             "Pull the whole thing out. Start from zero."),
    ("ROOT","DISSOLVE"):       ("rot return",         "What is dying is returning to the ground. Let it."),

    # PURVA ASHADHA → MOMENTUM FIELD
    ("MOMENTUM","DRIVE"):      ("push wave",          "Add force to what is already moving. Amplify the momentum."),
    ("MOMENTUM","BUILD"):      ("ramp build",         "Build the incline that creates unstoppable movement."),
    ("MOMENTUM","CONNECT"):    ("chain speed",        "Link the moving parts together. Speed through connection."),
    ("MOMENTUM","PROTECT"):    ("shield flow",        "Protect the momentum from interference. Do not let it be slowed."),
    ("MOMENTUM","LEAD"):       ("surge command",      "Lead by accelerating. Your job is to remove friction from the path."),
    ("MOMENTUM","REFINE"):     ("tune inertia",       "Adjust the trajectory without losing speed."),
    ("MOMENTUM","BALANCE"):    ("equal push",         "Apply pressure evenly. Uneven force creates spin."),
    ("MOMENTUM","PENETRATE"):  ("thrust deep",        "Drive the momentum into the core of the obstacle."),
    ("MOMENTUM","EXPAND"):     ("spread force",       "The momentum is expanding. Guide it rather than contain it."),
    ("MOMENTUM","STRUCTURE"):  ("frame motion",       "Give the momentum a channel. Unguided force is waste."),
    ("MOMENTUM","DISRUPT"):    ("stop sudden",        "Halt the momentum deliberately. Something needs to end."),
    ("MOMENTUM","DISSOLVE"):   ("slow fade",          "The momentum is bleeding out. Decide if it is worth saving."),

    # UTTARA ASHADHA → VICTORY FIELD
    ("VICTORY","DRIVE"):       ("win rush",           "The win is within reach. Push to the finish."),
    ("VICTORY","BUILD"):       ("trophy build",       "Build something that lasts beyond the victory."),
    ("VICTORY","CONNECT"):     ("claim link",         "Your win creates a connection. Honor it."),
    ("VICTORY","PROTECT"):     ("hold win",           "Protect what you have achieved. Victory can be reversed."),
    ("VICTORY","LEAD"):        ("crown victory",      "Lead your team to the finish. The win is collective."),
    ("VICTORY","REFINE"):      ("perfect win",        "Do not accept a partial victory. Refine until it is complete."),
    ("VICTORY","BALANCE"):     ("fair win",           "Win in a way you can defend. The method matters."),
    ("VICTORY","PENETRATE"):   ("decisive strike",    "One final penetrating move closes it."),
    ("VICTORY","EXPAND"):      ("triumph spread",     "The victory creates new territory. Move into it."),
    ("VICTORY","STRUCTURE"):   ("victory frame",      "Build the structure that makes the win permanent."),
    ("VICTORY","DISRUPT"):     ("upset win",          "The expected winner will not win today. Position accordingly."),
    ("VICTORY","DISSOLVE"):    ("dissolve defeat",    "What felt like a loss is clearing the path for real victory."),

    # SHRAVANA → SIGNAL FIELD
    ("SIGNAL","DRIVE"):        ("broadcast fast",     "Send the message now. The channel is open."),
    ("SIGNAL","BUILD"):        ("tower send",         "Build the transmission infrastructure. Reach further."),
    ("SIGNAL","CONNECT"):      ("link pulse",         "Your signal reaches someone important today. Stay open."),
    ("SIGNAL","PROTECT"):      ("whisper shield",     "Be selective about what you transmit. Not everything should be sent."),
    ("SIGNAL","LEAD"):         ("command call",       "Issue the signal that sets everything in motion."),
    ("SIGNAL","REFINE"):       ("clear noise",        "Remove the interference. Your signal is being diluted."),
    ("SIGNAL","BALANCE"):      ("equal transmit",     "Listen as much as you broadcast today."),
    ("SIGNAL","PENETRATE"):    ("frequency drill",    "Your signal reaches someone others cannot reach today."),
    ("SIGNAL","EXPAND"):       ("spread wave",        "The signal is going further than expected. Let it."),
    ("SIGNAL","STRUCTURE"):    ("signal frame",       "Create the protocol. Unstructured signals create confusion."),
    ("SIGNAL","DISRUPT"):      ("jam signal",         "Someone is interfering with your transmission. Find the source."),
    ("SIGNAL","DISSOLVE"):     ("static fade",        "The signal is weak today. Wait for a clearer channel."),

    # DHANISHTA → ABUNDANCE FIELD
    ("ABUNDANCE","DRIVE"):     ("wealth rush",        "Move toward the abundance. It is available today."),
    ("ABUNDANCE","BUILD"):     ("hoard build",        "Accumulate deliberately. What you gather now compounds."),
    ("ABUNDANCE","CONNECT"):   ("trade link",         "Exchange creates abundance today. Transact."),
    ("ABUNDANCE","PROTECT"):   ("store safe",         "Secure what you have. Abundance can disappear quickly."),
    ("ABUNDANCE","LEAD"):      ("lavish lead",        "Lead with generosity. Your abundance creates followership."),
    ("ABUNDANCE","REFINE"):    ("count abundance",    "Audit what you actually have. You may be richer than you think."),
    ("ABUNDANCE","BALANCE"):   ("fair share",         "Distribute the abundance. Hoarding it blocks the flow."),
    ("ABUNDANCE","PENETRATE"): ("mine deep",          "The wealth is deeper than the surface shows. Dig."),
    ("ABUNDANCE","EXPAND"):    ("overflow",           "The abundance exceeds the container. Expand the vessel."),
    ("ABUNDANCE","STRUCTURE"): ("wealth grid",        "Build the system that creates sustainable abundance."),
    ("ABUNDANCE","DISRUPT"):   ("scatter riches",     "The abundance is being scattered. Gather it before it is gone."),
    ("ABUNDANCE","DISSOLVE"):  ("abundance melt",     "What you thought was wealth is dissolving. Reassess."),

    # SHATABHISHA → CLARITY FIELD
    ("CLARITY","DRIVE"):       ("clear cut",          "Make the clear decision fast. The answer is known."),
    ("CLARITY","BUILD"):       ("lens build",         "Build the instrument that brings things into focus."),
    ("CLARITY","CONNECT"):     ("transparent link",   "Be completely clear in the connection. No ambiguity."),
    ("CLARITY","PROTECT"):     ("shield clarity",     "Protect your clear view. Do not let confusion in."),
    ("CLARITY","LEAD"):        ("bright command",     "Lead with complete clarity. Your people need to see clearly."),
    ("CLARITY","REFINE"):      ("purify sight",       "Remove the distortion. One thing is clouding your vision."),
    ("CLARITY","BALANCE"):     ("even focus",         "See both sides with equal clarity before deciding."),
    ("CLARITY","PENETRATE"):   ("X-ray see",          "You see through the surface today. Trust what you see."),
    ("CLARITY","EXPAND"):      ("wide clear",         "The clarity extends in all directions today. Use it."),
    ("CLARITY","STRUCTURE"):   ("crystal frame",      "Build the transparent structure. Make everything visible."),
    ("CLARITY","DISRUPT"):     ("blur clarity",       "Your clarity is being deliberately obscured. Find the source."),
    ("CLARITY","DISSOLVE"):    ("fog over",           "Clarity is not available today. Do not make permanent decisions."),

    # PURVA BHADRAPADA → EDGE FIELD
    ("EDGE","DRIVE"):          ("blade rush",         "Move with intensity. The edge is in the speed."),
    ("EDGE","BUILD"):          ("sharp build",        "Construct something with a cutting edge."),
    ("EDGE","CONNECT"):        ("cut link",           "Sever the connection that is dulling your edge."),
    ("EDGE","PROTECT"):        ("edge guard",         "Use your sharpness defensively. You are the barrier."),
    ("EDGE","LEAD"):           ("razor command",      "Lead with precision and intensity. No softness today."),
    ("EDGE","REFINE"):         ("hone edge",          "Sharpen the edge further. It is not yet as sharp as it needs to be."),
    ("EDGE","BALANCE"):        ("knife balance",      "Balance on the edge. Lean too far either way and it cuts you."),
    ("EDGE","PENETRATE"):      ("stab deep",          "The edge goes in deep today. Use it deliberately."),
    ("EDGE","EXPAND"):         ("spread edge",        "Your sharpness is extending its reach. Let it."),
    ("EDGE","STRUCTURE"):      ("blade frame",        "Build the structure that holds the edge in place."),
    ("EDGE","DISRUPT"):        ("blunt edge",         "Your sharpness is being dulled. Something is wrong."),
    ("EDGE","DISSOLVE"):       ("edge melt",          "The intensity dissolves. Rest the blade."),

    # UTTARA BHADRAPADA → DEPTH FIELD
    ("DEPTH","DRIVE"):         ("dive fast",          "Go deep quickly. The answer is not on the surface."),
    ("DEPTH","BUILD"):         ("well build",         "Dig the well before you need the water."),
    ("DEPTH","CONNECT"):       ("depth link",         "The connection today goes deep. It will last."),
    ("DEPTH","PROTECT"):       ("deep shield",        "Protect at the deepest level. Surface defense is not enough."),
    ("DEPTH","LEAD"):          ("abyss command",      "Lead from the deepest understanding. Others will follow."),
    ("DEPTH","REFINE"):        ("sound depth",        "Measure the depth before you proceed."),
    ("DEPTH","BALANCE"):       ("even deep",          "Both sides of the situation have equal depth. Honor it."),
    ("DEPTH","PENETRATE"):     ("trench dive",        "Go deeper than anyone else is willing to go."),
    ("DEPTH","EXPAND"):        ("wide depth",         "The depth is expanding. Follow it."),
    ("DEPTH","STRUCTURE"):     ("layer frame",        "Build in layers. Each level supports the next."),
    ("DEPTH","DISRUPT"):       ("surface break",      "What was deep is coming to the surface. Be ready."),
    ("DEPTH","DISSOLVE"):      ("sink infinite",      "The depth has no bottom today. Let go of needing to find it."),

    # REVATI → COMPLETION FIELD
    ("COMPLETION","DRIVE"):    ("end rush",           "Close it now. The energy will not be available again soon."),
    ("COMPLETION","BUILD"):    ("final build",        "The last piece is ready to be placed."),
    ("COMPLETION","CONNECT"):  ("last link",          "One final connection closes the loop."),
    ("COMPLETION","PROTECT"):  ("close shield",       "Protect the ending. Do not let it be reopened."),
    ("COMPLETION","LEAD"):     ("finish command",     "Lead the team to the finish line. You are almost there."),
    ("COMPLETION","REFINE"):   ("perfect end",        "One final refinement and it is done. Do not skip it."),
    ("COMPLETION","BALANCE"):  ("close even",         "End it with both parties satisfied. Clean closure."),
    ("COMPLETION","PENETRATE"):("final cut",          "Make the definitive move that ends it."),
    ("COMPLETION","EXPAND"):   ("dissolve bound",     "The completion opens into something larger. Let it."),
    ("COMPLETION","STRUCTURE"):("seal frame",         "Lock it down. Make the completion official and permanent."),
    ("COMPLETION","DISRUPT"):  ("break end",          "The ending is being prevented. Push through the resistance."),
    ("COMPLETION","DISSOLVE"): ("return to one",      "Everything completes by returning to its origin."),
}

# Mode map: moon sign → MODE name
_SIGN_TO_MODE = {
    "Aries": "DRIVE", "Taurus": "BUILD", "Gemini": "CONNECT",
    "Cancer": "PROTECT", "Leo": "LEAD", "Virgo": "REFINE",
    "Libra": "BALANCE", "Scorpio": "PENETRATE", "Sagittarius": "EXPAND",
    "Capricorn": "STRUCTURE", "Aquarius": "DISRUPT", "Pisces": "DISSOLVE",
}

# Field map: nakshatra → FIELD name
_NAK_TO_FIELD = {
    "Ashwini": "IGNITION", "Bharani": "THRESHOLD", "Krittika": "PRECISION",
    "Rohini": "GROWTH", "Mrigashira": "DISCOVERY", "Ardra": "STORM",
    "Punarvasu": "RECOVERY", "Pushya": "ANCHOR", "Ashlesha": "STRATEGY",
    "Magha": "COMMAND", "Purva Phalguni": "MAGNETISM", "Uttara Phalguni": "FOUNDATION",
    "Hasta": "EXECUTION", "Chitra": "DESIGN", "Swati": "ADAPTATION",
    "Vishakha": "AMBITION", "Anuradha": "ALLIANCE", "Jyeshtha": "AUTHORITY",
    "Mula": "ROOT", "Purva Ashadha": "MOMENTUM", "Uttara Ashadha": "VICTORY",
    "Shravana": "SIGNAL", "Dhanishta": "ABUNDANCE", "Shatabhisha": "CLARITY",
    "Purva Bhadrapada": "EDGE", "Uttara Bhadrapada": "DEPTH", "Revati": "COMPLETION",
}


# ═══════════════════════════════════════════════════════════════════
# TRANSIT LANGUAGE ENGINE
# Translates raw transit data into behavioral plain English
# Using FIELD×MODE matrix intersection system
# ═══════════════════════════════════════════════════════════════════

# Planet → what force it represents (plain language)
_PLANET_FORCE = {
    "Sun":     "a visibility and authority force",
    "Moon":    "an emotional and intuitive signal",
    "Mercury": "a communication and information force",
    "Venus":   "a relationship and value signal",
    "Mars":    "an action and conflict force",
    "Jupiter": "an expansion and opportunity force",
    "Saturn":  "a structural pressure and discipline force",
    "Rahu":    "an ambition and disruption force",
    "Ketu":    "a release and detachment signal",
}

# Planet → what life area it governs when transiting (plain language)
_PLANET_DOMAIN = {
    "Sun":     "your visibility, reputation, and authority",
    "Moon":    "your emotional state, home, and daily rhythm",
    "Mercury": "your communications, decisions, and information flow",
    "Venus":   "your relationships, finances, and creative work",
    "Mars":    "your energy, ambition, and conflicts",
    "Jupiter": "your growth, opportunities, and belief systems",
    "Saturn":  "your career structure, discipline, and long-term foundations",
    "Rahu":    "your ambitions, obsessions, and foreign connections",
    "Ketu":    "your detachments, spirituality, and past patterns",
}

# FIELD → what life texture it represents (plain language)
_FIELD_TEXTURE = {
    "IGNITION":   "new beginnings and starting energy",
    "THRESHOLD":  "transitions and crossing points",
    "PRECISION":  "accuracy, detail, and surgical decisions",
    "GROWTH":     "expansion, nurturing, and development",
    "DISCOVERY":  "searching, curiosity, and finding hidden things",
    "STORM":      "disruption, transformation, and clearing",
    "RECOVERY":   "healing, rebuilding, and restoration",
    "ANCHOR":     "stability, security, and foundational needs",
    "STRATEGY":   "planning, tactics, and calculated moves",
    "COMMAND":    "authority, legacy, and leadership presence",
    "MAGNETISM":  "attraction, charisma, and drawing things in",
    "FOUNDATION": "long-term building and structural integrity",
    "EXECUTION":  "hands-on action and skilled delivery",
    "DESIGN":     "creative vision and pattern recognition",
    "ADAPTATION": "flexibility, pivoting, and flow",
    "AMBITION":   "goal pursuit and upward movement",
    "ALLIANCE":   "partnerships, loyalty, and collective power",
    "AUTHORITY":  "seniority, command, and elder wisdom",
    "ROOT":       "origins, core motivations, and deep patterns",
    "MOMENTUM":   "unstoppable forward movement and timing",
    "VICTORY":    "completion, triumph, and final results",
    "SIGNAL":     "listening, receiving, and transmitting",
    "ABUNDANCE":  "wealth, generosity, and overflow",
    "CLARITY":    "seeing through confusion and gaining insight",
    "EDGE":       "intensity, sharpness, and going to extremes",
    "DEPTH":      "profound understanding and going beneath surfaces",
    "COMPLETION": "endings, closure, and returning to source",
}

# MODE → how the force is delivered (plain language)
_MODE_DELIVERY = {
    "DRIVE":     "directly and forcefully",
    "BUILD":     "steadily and with patience",
    "CONNECT":   "through relationships and communication",
    "PROTECT":   "defensively and with caution",
    "LEAD":      "through authority and visibility",
    "REFINE":    "through precision and improvement",
    "BALANCE":   "through fairness and equilibrium",
    "PENETRATE": "deeply and without surface compromise",
    "EXPAND":    "broadly and with optimism",
    "STRUCTURE": "systematically and with discipline",
    "DISRUPT":   "unexpectedly and unconventionally",
    "DISSOLVE":  "gradually and by releasing resistance",
}

# Planet pair → interaction type when transiting planet meets natal planet
_PLANET_INTERACTION = {
    ("Saturn", "Moon"):   "structural pressure on emotional security",
    ("Saturn", "Sun"):    "authority being tested by discipline",
    ("Saturn", "Mars"):   "ambition meeting resistance",
    ("Saturn", "Venus"):  "relationships being tested for depth",
    ("Saturn", "Mercury"):"communication becoming more careful",
    ("Saturn", "Jupiter"):"expansion being disciplined",
    ("Jupiter", "Moon"):  "emotional expansion and optimism",
    ("Jupiter", "Sun"):   "authority and visibility amplified",
    ("Jupiter", "Mars"):  "action and ambition supercharged",
    ("Jupiter", "Venus"): "relationships and finances expanding",
    ("Jupiter", "Saturn"):"structure meeting opportunity",
    ("Mars", "Sun"):      "energy and drive amplified",
    ("Mars", "Moon"):     "emotional intensity and conflict energy",
    ("Mars", "Venus"):    "desire and action in relationships",
    ("Mars", "Mercury"):  "sharp, aggressive communication",
    ("Rahu", "Moon"):     "obsession disrupting emotional patterns",
    ("Rahu", "Sun"):      "ambition disrupting identity",
    ("Rahu", "Venus"):    "desire and obsession in relationships",
    ("Ketu", "Moon"):     "detachment from emotional patterns",
    ("Ketu", "Sun"):      "releasing ego and identity",
    ("Venus", "Moon"):    "harmony and beauty entering daily life",
    ("Venus", "Mars"):    "desire and creativity activated",
    ("Mercury", "Moon"):  "mental activity affecting emotional state",
    ("Mercury", "Mars"):  "sharp thinking and quick decisions",
    ("Sun", "Moon"):      "public and private life in tension",
    ("Sun", "Saturn"):    "visibility meeting structure",
    ("Moon", "Sun"):      "emotional needs affecting public role",
}


def _get_transit_plain_context(
    transiting_planet: str,
    transiting_nakshatra: str,
    transiting_sign: str,
    natal_planet: str,
    natal_nakshatra: str,
    natal_sign: str,
) -> dict:
    """
    Layer 1+2: Compute the plain-language context for a transit event.
    Returns structured dict for Claude to narrate from.
    """
    # Get FIELD×MODE for both transiting and natal
    trans_field = _NAK_TO_FIELD.get(transiting_nakshatra, "SIGNAL")
    trans_mode = _SIGN_TO_MODE.get(transiting_sign, "CONNECT")
    natal_field = _NAK_TO_FIELD.get(natal_nakshatra, "ANCHOR")
    natal_mode = _SIGN_TO_MODE.get(natal_sign, "PROTECT")

    # Look up action signatures
    trans_sig = _FIELD_MODE_MATRIX.get((trans_field, trans_mode), ("read signal", "Stay alert."))
    natal_sig = _FIELD_MODE_MATRIX.get((natal_field, natal_mode), ("hold steady", "Maintain your position."))

    # Plain language components
    planet_force = _PLANET_FORCE.get(transiting_planet, "a planetary force")
    planet_domain = _PLANET_DOMAIN.get(transiting_planet, "your life circumstances")
    trans_texture = _FIELD_TEXTURE.get(trans_field, "change")
    trans_delivery = _MODE_DELIVERY.get(trans_mode, "steadily")
    natal_texture = _FIELD_TEXTURE.get(natal_field, "stability")
    interaction = _PLANET_INTERACTION.get(
        (transiting_planet, natal_planet),
        f"{transiting_planet} energy meeting your {natal_planet} patterns"
    )

    return {
        "transiting_planet": transiting_planet,
        "natal_planet": natal_planet,
        "trans_field": trans_field,
        "trans_mode": trans_mode,
        "natal_field": natal_field,
        "natal_mode": natal_mode,
        "trans_action": trans_sig[0].upper(),
        "natal_action": natal_sig[0].upper(),
        "planet_force": planet_force,
        "planet_domain": planet_domain,
        "trans_texture": trans_texture,
        "trans_delivery": trans_delivery,
        "natal_texture": natal_texture,
        "interaction": interaction,
    }


async def build_transit_behavioral_block(
    transits: list,
    natal_planets: dict,
    user_profile: dict,
    max_transits: int = 3,
) -> str:
    """
    Build a plain-English behavioral transit block for the predict prompt.

    Args:
        transits: List of active transit dicts with planet, nakshatra, sign, house
        natal_planets: Dict of natal planet data {name: {nakshatra, sign, house}}
        user_profile: Dict with first_name, age, current_country, profession
        max_transits: Max number of transits to translate (keep prompt lean)

    Returns:
        Plain-English transit block string for injection into predict prompt
    """
    if not transits:
        return ""

    if not claude_client:
        return _build_transit_block_fallback(transits, natal_planets)

    # Priority: Saturn, Jupiter, Rahu first (most impactful)
    PRIORITY_PLANETS = ["Saturn", "Rahu", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Ketu"]
    sorted_transits = sorted(
        transits,
        key=lambda t: PRIORITY_PLANETS.index(t.get("planet", "Moon"))
        if t.get("planet") in PRIORITY_PLANETS else 99
    )[:max_transits]

    transit_contexts = []
    for t in sorted_transits:
        trans_planet = t.get("planet", "")
        trans_nak = t.get("nakshatra", "") or t.get("nak", "") or t.get("nakshatra_name", "")
        trans_sign = t.get("sign", "")

        # Find closest natal planet (house match or aspect)
        natal_planet_name = t.get("natal_planet") or _find_natal_planet_for_transit(
            t.get("house", 1), natal_planets
        )
        natal_data = natal_planets.get(natal_planet_name, {})
        natal_nak = natal_data.get("nakshatra", "Pushya")
        natal_sign = natal_data.get("sign", "Cancer")

        if trans_planet and trans_nak:
            ctx = _get_transit_plain_context(
                trans_planet, trans_nak, trans_sign,
                natal_planet_name, natal_nak, natal_sign
            )
            transit_contexts.append(ctx)

    if not transit_contexts:
        return ""

    # Build prompt for Claude
    user_name = user_profile.get("first_name") or user_profile.get("name") or "the user"
    user_age = user_profile.get("age") or user_profile.get("user_age") or ""
    user_country = user_profile.get("current_country") or user_profile.get("country") or ""

    transit_descriptions = []
    for ctx in transit_contexts:
        transit_descriptions.append(
            f"- {ctx['transiting_planet']} in {ctx['trans_field']} x {ctx['trans_mode']} ({ctx['trans_action']}) hitting natal {ctx['natal_planet']} in {ctx['natal_field']} x {ctx['natal_mode']} ({ctx['natal_action']}) | {ctx['interaction']}"
            f"  Force: {ctx['planet_force']} arriving {ctx['trans_delivery']} "
            f"into {ctx['natal_texture']}"
        )

    prompt = f"""You are translating astrological transit data into behavioral plain English for a life intelligence app.

USER: {user_name}, {user_age}, in {user_country}

ACTIVE TRANSITS:
{chr(10).join(transit_descriptions)}

For each transit, write exactly 3 lines:
WHAT: What kind of force or event is arriving (no astrology terms)
WHERE: Which area of their life it hits (career/money/relationships/health/decisions)
DO: One specific behavioral move they should take

Rules:
- No planet names visible to user
- No nakshatra names visible to user  
- No "transit" or "aspect" language
- Plain English only — like a trusted advisor who happens to know the patterns
- Each DO must be specific and actionable, not general attitude
- If friction: acknowledge it, show how to work with it
- If opportunity: show exactly how to capture it
- Maximum 15 words per line

Format each transit as:
TRANSIT [N]:
WHAT: [one line]
WHERE: [one line]  
DO: [one line]

Output all {len(transit_contexts)} transit(s) in this format. Nothing else."""

    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        print(f"[transit-lang] Generated plain-English block for {len(transit_contexts)} transit(s)")
        return f"\n[BEHAVIORAL TRANSIT CONTEXT]\n{raw}\n"
    except Exception as e:
        print(f"[transit-lang] Claude call failed: {e}")
        return _build_transit_block_fallback(transits, natal_planets)


def _find_natal_planet_for_transit(house: int, natal_planets: dict) -> str:
    """Find the most relevant natal planet for a transit house."""
    HOUSE_PLANET_MAP = {
        1: "Sun", 2: "Venus", 3: "Mercury", 4: "Moon",
        5: "Jupiter", 6: "Mars", 7: "Venus", 8: "Saturn",
        9: "Jupiter", 10: "Sun", 11: "Jupiter", 12: "Saturn"
    }
    return HOUSE_PLANET_MAP.get(house, "Moon")


def _build_transit_block_fallback(transits: list, natal_planets: dict) -> str:
    """Fallback: build plain-English block without Claude."""
    lines = ["\n[CURRENT ENERGY PATTERNS]"]
    for t in transits[:3]:
        planet = t.get("planet", "")
        house = t.get("house", 0)
        force = _PLANET_FORCE.get(planet, "a planetary force")
        domain_map = {
            1: "your identity and presence",
            2: "your finances and values",
            3: "your communications and short trips",
            4: "your home and emotional foundation",
            5: "your creative work and children",
            6: "your health and daily work",
            7: "your partnerships and relationships",
            8: "your shared resources and transformation",
            9: "your beliefs and long-distance matters",
            10: "your career and public reputation",
            11: "your network and future goals",
            12: "your inner world and hidden matters",
        }
        domain = domain_map.get(house, "your circumstances")
        nak = t.get("nakshatra", "")
        trans_field = _NAK_TO_FIELD.get(nak, "SIGNAL")
        trans_sign = t.get("sign", "")
        trans_mode = _SIGN_TO_MODE.get(trans_sign, "CONNECT")
        sig = _FIELD_MODE_MATRIX.get((trans_field, trans_mode), ("read signal", "Stay alert."))
        lines.append(f"- {force} is active in {domain}: {sig[1]}")
    return "\n".join(lines) + "\n"


def _get_action_signature(nakshatra: str, moon_sign: str) -> dict:
    """
    Layer 1 + 2: Compute MODE × FIELD action signature.
    Returns dict with field, mode, action_phrase, description.
    """
    field = _NAK_TO_FIELD.get(nakshatra, "SIGNAL")
    mode = _SIGN_TO_MODE.get(moon_sign, "CONNECT")
    key = (field, mode)
    phrase_data = _FIELD_MODE_MATRIX.get(key, ("read signal", "Stay alert to what arrives today."))
    action_phrase, description = phrase_data
    return {
        "field": field,
        "mode": mode,
        "action_phrase": action_phrase.upper(),
        "description": description,
        "key": f"{field} × {mode}",
    }


def _compute_sd_trigger(scores: list, today_score: int) -> dict:
    """
    SD filter: fires WOW if today is an outlier vs the week.
    Returns dict with fires bool + confidence level.
    """
    import math
    if len(scores) < 3:
        # Cold start — use threshold fallback
        fires = today_score >= 7 or today_score <= 3
        return {
            "fires": fires,
            "confidence": "MEDIUM" if fires else "LOW",
            "reason": "threshold" if fires else "neutral",
            "week_avg": today_score,
            "std_dev": 0,
            "z_score": 0,
        }

    avg = sum(scores) / len(scores)
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    std = math.sqrt(variance) if variance > 0 else 0.1
    z_score = (today_score - avg) / std if std > 0 else 0

    fires = abs(z_score) >= 1.5
    if abs(z_score) >= 2.0:
        confidence = "VERY HIGH"
    elif abs(z_score) >= 1.5:
        confidence = "HIGH"
    else:
        confidence = "LOW"

    direction = "peak" if z_score > 0 else "friction"

    return {
        "fires": fires,
        "confidence": confidence,
        "reason": f"z={z_score:.1f} ({direction})",
        "week_avg": round(avg, 1),
        "std_dev": round(std, 1),
        "z_score": round(z_score, 2),
    }


# ═══════════════════════════════════════════════════════════════════

# Base templates per instrument — sent to Claude as the narrative seed
_WOW_BASE_TEMPLATES = {
    "AUTHORITY ENGINE":  ("recognition",  "A decision-maker notices your work today."),
    "REVENUE PIPELINE":  ("finance",      "An unexpected financial opening surfaces today."),
    "ALLIANCE SYNC":     ("relationship", "Someone significant re-enters your orbit today."),
    "CAPITAL RUNWAY":    ("finance",      "A money-related signal surfaces today."),
    "CREATION ENGINE":   ("opportunity",  "An unexpected creative or strategic opening appears today."),
    "CONFLICT SHIELD":   ("warning",      "Something that needs attention surfaces today."),
    "REAL ESTATE RADAR": ("movement",     "A change in your physical environment comes into focus today."),
    "FORTUNE VECTOR":    ("opportunity",  "An opening arrives from an unexpected direction today."),
    "GLOBAL VECTOR":     ("movement",     "A foreign connection or opportunity surfaces today."),
    "CAPITAL RESERVES":  ("finance",      "A financial pattern becomes clear today."),
    "SYSTEM VITALS":     ("health",       "Your energy signals something important today."),
    "ACTION CAPACITY":   ("decision",     "You will be asked to make a call you weren't expecting today."),
}

_STATUS_THRESHOLD = {"PEAK": 2, "ACTIVE": 1}

WEEKDAY_CONTEXT = {
    "Monday":    "a Monday — unexpected signals often arrive as the week kicks off",
    "Tuesday":   "a Tuesday — action-oriented energy, direct moves get noticed",
    "Wednesday": "a Wednesday — communication is amplified, messages carry weight",
    "Thursday":  "a Thursday — expansion energy, meetings and offers feel larger",
    "Friday":    "a Friday — relationship energy peaks, people reach out before the weekend",
    "Saturday":  "a Saturday — surprising for a weekend, which makes it more significant",
    "Sunday":    "a Sunday — rare for something professional to surface, which makes it meaningful",
}


# Country ISO → UTC offset map for daily-week start date
_COUNTRY_TZ_OFFSETS = {
    # USA — use Eastern as default (most populous timezone)
    "US": -5,
    # LATAM
    "CO": -5,   # Colombia
    "BR": -3,   # Brazil (Brasília)
    "AR": -3,   # Argentina
    "MX": -6,   # Mexico (Central — Mexico City)
    "PE": -5,   # Peru
    "CL": -4,   # Chile
    "PA": -5,   # Panama
    "EC": -5,   # Ecuador
    "BO": -4,   # Bolivia
    "PY": -4,   # Paraguay
    "UY": -3,   # Uruguay
    "VE": -4,   # Venezuela
    "GT": -6,   # Guatemala
    "HN": -6,   # Honduras
    "SV": -6,   # El Salvador
    "NI": -6,   # Nicaragua
    "CR": -6,   # Costa Rica
    "DO": -4,   # Dominican Republic
    "CU": -5,   # Cuba
    # Europe
    "GB": 0,
    "DE": 1,
    "FR": 1,
    "ES": 1,
    "IT": 1,
    "NL": 1,
    "PT": 0,
    # Asia / Middle East
    "IN": 5,    # India (+5:30 — use 5)
    "AE": 4,    # UAE
    "SG": 8,    # Singapore
    "JP": 9,    # Japan
    "AU": 10,   # Australia (AEST)
    # Africa
    "ZA": 2,    # South Africa
    "KE": 3,    # Kenya
    "NG": 1,    # Nigeria
    # Default
    "DEFAULT": 0,
}

def _get_local_start_date(tz_offset: int = None, current_country: str = None):
    """
    Returns today's date in the user's local timezone.
    Priority: explicit tz_offset > country lookup > UTC
    """
    from datetime import datetime, timedelta, timezone
    if tz_offset is None and current_country:
        tz_offset = _COUNTRY_TZ_OFFSETS.get(
            (current_country or "").upper(),
            _COUNTRY_TZ_OFFSETS["DEFAULT"]
        )
    if tz_offset is None:
        tz_offset = 0
    # Clamp to valid range
    tz_offset = max(-12, min(14, tz_offset))
    local_now = datetime.now(timezone.utc) + timedelta(hours=tz_offset)
    return local_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)



def _compute_user_age(birth_date_str: str) -> int:
    """Compute age from birth_date string YYYY-MM-DD."""
    try:
        from datetime import datetime
        bd = datetime.strptime(birth_date_str[:10], "%Y-%m-%d")
        today = datetime.utcnow()
        return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    except Exception:
        return 0


def _get_wow_cache(chart_id: str, instrument_name: str) -> dict:
    """Check if we have a cached WOW hint for this chart+instrument from today."""
    try:
        from datetime import datetime
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        result = supabase.table("charts").select("daily_wow_cache").eq("id", chart_id).single().execute()
        cache = result.data.get("daily_wow_cache") if result.data else None
        if cache and isinstance(cache, dict):
            if cache.get("date") == today_str and cache.get("instrument") == instrument_name:
                print(f"[daily-week] WOW cache HIT for {chart_id} — {instrument_name}")
                return cache
    except Exception as e:
        print(f"[daily-week] WOW cache read failed (non-fatal): {e}")
    return {}


def _save_wow_cache(chart_id: str, instrument_name: str, wow_data: dict):
    """Save WOW hint to Supabase cache."""
    try:
        from datetime import datetime
        cache_payload = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "instrument": instrument_name,
            **wow_data
        }
        supabase.table("charts").update(
            {"daily_wow_cache": cache_payload}
        ).eq("id", chart_id).execute()
        print(f"[daily-week] WOW cache SAVED for {chart_id}")
    except Exception as e:
        print(f"[daily-week] WOW cache save failed (non-fatal): {e}")


async def _call_claude_wow_hint(
    base_template: str,
    category: str,
    instrument_name: str,
    user_first_name: str,
    user_age: int,
    current_country: str,
    birth_city: str,
    gender: str,
    nakshatra: str,
    weekday: str,
    signal_score: float,
    strength: str,
    language: str = "en",
) -> str:
    """
    Call Claude to write ONE personalized WOW sentence.
    Claude narrates — it does not reason or explain.
    """
    try:
        weekday_ctx = WEEKDAY_CONTEXT.get(weekday, f"a {weekday}")
        strength_note = "exceptionally strong" if strength == "PEAK" else "clearly active"

        prompt = f"""You are writing a single-sentence daily signal hint for a life intelligence app.

USER PROFILE:
- Name: {user_first_name}
- Age: {user_age}
- Location: {current_country}
- Born in: {birth_city}
- Gender: {gender}

TODAY'S SIGNAL:
- Instrument: {instrument_name} (score: {signal_score}/100, strength: {strength_note})
- Category: {category}
- Base template: "{base_template}"
- Today is {weekday_ctx}
- Astrological quality today: {nakshatra} energy — precise, commanding, strategic

YOUR TASK:
Rewrite the base template as ONE sentence that feels personally relevant to this user.
- Use their location and life context naturally (not as a label)
- Reference the day of the week to make it feel live and real
- Keep it as a HINT — specific enough to be noticed, vague enough to apply
- No astrology terms. No planet names. No nakshatra names.
- Maximum 25 words.
- Do NOT start with "Today" — vary the opening.
- Never use double articles. Never write "the your", "a the", "the the", or "but the your". Proofread before returning.
- {f'Write the entire response in {language}.' if language != 'en' else 'Write in English.'}
- Output ONLY the single sentence. Nothing else."""

        if not claude_client:
            return base_template

        response = await claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=60,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        hint = response.content[0].text.strip().strip('"').strip("'")
        print(f"[daily-week] Claude WOW hint generated: {hint[:80]}...")
        return hint

    except Exception as e:
        print(f"[daily-week] Claude WOW call failed (non-fatal): {e}")
        return base_template  # fallback to hardcoded template



async def _call_claude_wow_hint_v2(
    action_signature: dict,
    is_friction: bool,
    score: int,
    week_avg: float,
    sd_confidence: str,
    user_first_name: str,
    user_age: int,
    current_country: str,
    birth_city: str,
    gender: str,
    weekday: str,
    instrument_name: str,
    signal_score: float,
    instrument_strength: str,
    language: str = "en",
) -> str:
    """
    Layer 3: Claude judge — friction-aware narration from matrix action signature.

    Sends: action phrase + friction context + user profile + confidence
    Gets back: ONE sentence that reads like a trailer, not a prediction.
    """
    try:
        field = action_signature.get("field", "SIGNAL")
        mode = action_signature.get("mode", "CONNECT")
        action_phrase = action_signature.get("action_phrase", "READ SIGNAL")
        base_description = action_signature.get("description", "Stay alert to what arrives today.")
        weekday_contexts = {
            "Monday":    "a Monday — the week is just opening",
            "Tuesday":   "a Tuesday — action and direct moves carry weight",
            "Wednesday": "a Wednesday — communication and negotiation are amplified",
            "Thursday":  "a Thursday — expansion and authority energy peaks",
            "Friday":    "a Friday — relationships and deals close",
            "Saturday":  "a Saturday — surprising for a weekend, which makes it significant",
            "Sunday":    "a Sunday — rare for something important to surface, which makes it meaningful",
        }
        weekday_ctx = weekday_contexts.get(weekday, f"a {weekday}")

        if is_friction:
            task = f"""The user is in {field} FIELD × {mode} MODE today.
Their score is {score}/10 — a FRICTION day (below their weekly average of {week_avg}).
Action signature: "{action_phrase}" — {base_description}

The energy is present but BLOCKED. Do not be blindly positive.
Write a signal that:
- Acknowledges the friction honestly
- Shows exactly HOW to use {action_phrase} energy DESPITE the resistance
- Gives a specific behavioral move, not a general attitude
- Feels like a trailer — hints at something specific without naming it"""
        else:
            task = f"""The user is in {field} FIELD × {mode} MODE today.
Their score is {score}/10 — a FLOW day (above their weekly average of {week_avg}).
Action signature: "{action_phrase}" — {base_description}

The energy is OPEN and available. Write a signal that:
- Capitalizes on the {action_phrase} energy specifically
- Tells them what to do TODAY that they cannot do on other days
- Feels like a trailer — hints at something specific without naming it
- Has urgency — this window is time-limited"""

        prompt = f"""You are writing a single-sentence WOW signal for a life intelligence app.

USER: {user_first_name}, {user_age} years old, based in {current_country}
TODAY: {weekday_ctx}
FIELD × MODE: {field} × {mode} = "{action_phrase}"
CHART SIGNAL: {instrument_name} at {signal_score}/100 ({instrument_strength})
CONFIDENCE: {sd_confidence}

{task}

RULES:
- Maximum 25 words
- No astrology terms. No planet names. No nakshatra names. No "FIELD" or "MODE" labels.
- Do NOT start with "Today"
- Write as if you know something they don't — a hint, not a prediction
- Use their professional/geographic context naturally
- Never use double articles. Never write "the your", "a the", "the the", or "but the your". Proofread before returning.
- {f'Write the entire response in {language}.' if language != 'en' else 'Write in English.'}
- Output ONLY the single sentence. Nothing else."""

        if not claude_client:
            return action_signature.get("description", "Stay alert to what arrives today.")

        response = await claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=60,
            temperature=0.75,
            messages=[{"role": "user", "content": prompt}]
        )
        hint = response.content[0].text.strip().strip('"').strip("'")
        print(f"[daily-week] WOW v2 hint: {hint[:80]}...")
        return hint

    except Exception as e:
        print(f"[daily-week] Claude WOW v2 call failed: {e}")
        return action_signature.get("description", "Stay alert to what arrives today.")



async def _get_wow_signal_for_chart_v2(
    chart_id: str,
    chart_data: dict,
    today_nakshatra: str,
    today_moon_sign: str,
    today_score: int,
    is_friction: bool,
    all_scores: list,
    weekday: str,
    language: str = "en",
) -> dict:
    """
    Full WOW signal pipeline v2:
    1. Compute action signature (Field × Mode matrix)
    2. SD filter — is today an outlier?
    3. Load executive summary — is there a PEAK/ACTIVE instrument?
    4. If both trigger: call Claude for personalized hint
    5. Cache 24hrs
    """
    try:
        # Layer 1+2: Action signature
        sig = _get_action_signature(today_nakshatra, today_moon_sign)

        # SD filter
        sd = _compute_sd_trigger(all_scores, today_score)

        # Executive summary — instrument lock check
        try:
            from antar_engine.symptom_library import build_executive_summary
            from datetime import datetime as _exdt
            import json as _jjson
            _cr = supabase.table("charts").select("chart_data, jaimini_data, lal_kitab_data").eq("id", chart_id).single().execute()
            if not _cr.data:
                return None
            _cd = _cr.data.get("chart_data", {})
            if isinstance(_cd, str):
                try: _cd = _jjson.loads(_cd)
                except: _cd = {}
            _jd = _cr.data.get("jaimini_data", {})
            if isinstance(_jd, str):
                try: _jd = _jjson.loads(_jd)
                except: _jd = {}
            _lk = _cr.data.get("lal_kitab_data", {})
            if isinstance(_lk, str):
                try: _lk = _jjson.loads(_lk)
                except: _lk = {}
            _now = _exdt.utcnow().isoformat()
            _dr = supabase.table("dasha_periods").select("planet_or_sign, level, end_date").eq("chart_id", chart_id).eq("system", "vimsottari").lte("start_date", _now).gte("end_date", _now).order("level").execute()
            _dasha_list = _dr.data if _dr.data else []
            _current_dasha = ""
            for _d in _dasha_list:
                if _d.get("level") == 1: _current_dasha = _d["planet_or_sign"].strip()
                if _d.get("level") == 2: _current_dasha += "-" + _d["planet_or_sign"].strip()
            exec_data = build_executive_summary(_cd, _jd, _lk, _current_dasha, _dasha_list)
            print(f"[daily-week] v2 exec summary loaded — {len(exec_data.get('instruments', {}))} instruments")
        except Exception as ex:
            print(f"[daily-week] v2 exec summary failed: {ex}")
            exec_data = {}

        # Find best instrument
        instruments_raw = exec_data.get("instruments", {})
        instruments = list(instruments_raw.values()) if isinstance(instruments_raw, dict) else instruments_raw
        _STATUS_THRESHOLD_LOCAL = {"PEAK": 2, "ACTIVE": 1}
        best_inst = None
        best_priority = 0
        for inst in instruments:
            if not isinstance(inst, dict): continue
            status = inst.get("signal_status", "")
            priority = _STATUS_THRESHOLD_LOCAL.get(status, 0)
            sig_score = inst.get("signal_score", 0)
            if priority > best_priority or (priority == best_priority and sig_score > (best_inst.get("signal_score", 0) if best_inst else 0)):
                if priority > 0:
                    best_inst = inst
                    best_priority = priority

        # Combined trigger: SD outlier OR strong instrument lock
        instrument_fires = best_inst is not None
        sd_fires = sd.get("fires", False)

        if not sd_fires and not instrument_fires:
            print(f"[daily-week] v2 WOW skipped — score={today_score} z={sd.get('z_score',0):.1f} no instrument")
            return None

        # Skip LOW confidence signals — not worth showing
        if not instrument_fires or (best_inst and best_inst.get("signal_status") not in ("PEAK", "ACTIVE")):
            if sd.get("confidence") == "LOW":
                print(f"[daily-week] v2 WOW skipped — LOW confidence only")
                return None

        inst_name = best_inst.get("label", "").upper() if best_inst else sig.get("field") + " ENGINE"
        inst_score = best_inst.get("signal_score", 0) if best_inst else today_score * 10
        inst_strength = best_inst.get("signal_status", "ACTIVE") if best_inst else "ACTIVE"

        # Confidence: both triggers = higher confidence
        if sd_fires and instrument_fires:
            confidence = "VERY HIGH" if sd.get("confidence") == "VERY HIGH" else "HIGH"
        elif instrument_fires and inst_strength == "PEAK":
            confidence = "HIGH"
        else:
            confidence = sd.get("confidence", "MEDIUM")

        # Check 24hr cache
        cached = _get_wow_cache(chart_id, inst_name)
        if cached.get("hint"):
            print(f"[daily-week] v2 WOW cache HIT")
            return {
                "fires": True,
                "strength": inst_strength,
                "confidence": confidence,
                "category": _map_instrument_to_category(inst_name),
                "instrument": inst_name,
                "signal_score": inst_score,
                "field": sig["field"],
                "mode": sig["mode"],
                "action_phrase": sig["action_phrase"],
                "hint": cached["hint"],
                "follow_up": "If something happens today in this area — ask Antar about it.",
                "cached": True,
            }

        # User profile
        user_first_name = chart_data.get("first_name") or chart_data.get("name") or "you"
        birth_date = chart_data.get("birth_date") or chart_data.get("dob") or ""
        user_age = _compute_user_age(birth_date) if birth_date else 0
        current_country = chart_data.get("current_country") or chart_data.get("birth_country") or ""
        birth_city = chart_data.get("birth_city") or ""
        gender = chart_data.get("gender") or ""

        # Claude Layer 3
        hint = await _call_claude_wow_hint_v2(
            action_signature=sig,
            is_friction=is_friction,
            score=today_score,
            week_avg=sd.get("week_avg", today_score),
            sd_confidence=confidence,
            user_first_name=user_first_name,
            user_age=user_age,
            current_country=current_country,
            birth_city=birth_city,
            gender=gender,
            weekday=weekday,
            instrument_name=inst_name,
            signal_score=inst_score,
            instrument_strength=inst_strength,
            language=language,
        )

        result = {
            "fires": True,
            "strength": inst_strength,
            "confidence": confidence,
            "category": _map_instrument_to_category(inst_name),
            "instrument": inst_name,
            "signal_score": inst_score,
            "field": sig["field"],
            "mode": sig["mode"],
            "action_phrase": sig["action_phrase"],
            "hint": hint,
            "follow_up": "If something happens today in this area — ask Antar about it.",
            "cached": False,
        }

        _save_wow_cache(chart_id, inst_name, result)
        return result

    except Exception as e:
        print(f"[daily-week] v2 WOW signal failed: {e}")
        return None


def _map_instrument_to_category(inst_name: str) -> str:
    inst_upper = inst_name.upper()
    if any(x in inst_upper for x in ["AUTHORITY", "CAREER", "CREATION", "ACTION"]):
        return "recognition"
    if any(x in inst_upper for x in ["REVENUE", "CAPITAL", "WEALTH", "ABUNDANCE"]):
        return "finance"
    if any(x in inst_upper for x in ["ALLIANCE", "SYNC", "RELATION"]):
        return "relationship"
    if any(x in inst_upper for x in ["GLOBAL", "VECTOR", "TRAVEL"]):
        return "movement"
    if any(x in inst_upper for x in ["CONFLICT", "SHIELD"]):
        return "warning"
    if any(x in inst_upper for x in ["VITALS", "HEALTH"]):
        return "health"
    return "opportunity"


async def _get_wow_signal_for_chart(chart_id: str, chart_data: dict, today_nakshatra: str, weekday: str, language: str = "en") -> dict:
    """
    Main WOW signal builder.
    1. Load executive summary
    2. Find highest-status instrument (PEAK > ACTIVE)
    3. Check 24hr cache
    4. If no cache: call Claude for personalized hint
    5. Return event_signal dict or None
    """
    try:
        # Load executive summary directly (no HTTP — avoids async deadlock)
        try:
            from antar_engine.symptom_library import build_executive_summary
            from datetime import datetime as _exdt
            import json as _jjson
            _cr = supabase.table("charts").select("chart_data, jaimini_data, lal_kitab_data").eq("id", chart_id).single().execute()
            if not _cr.data:
                return None
            _cd = _cr.data.get("chart_data", {})
            if isinstance(_cd, str):
                try: _cd = _jjson.loads(_cd)
                except: _cd = {}
            _jd = _cr.data.get("jaimini_data", {})
            if isinstance(_jd, str):
                try: _jd = _jjson.loads(_jd)
                except: _jd = {}
            _lk = _cr.data.get("lal_kitab_data", {})
            if isinstance(_lk, str):
                try: _lk = _jjson.loads(_lk)
                except: _lk = {}
            _now = _exdt.utcnow().isoformat()
            _dr = supabase.table("dasha_periods").select("planet_or_sign, level, end_date").eq("chart_id", chart_id).eq("system", "vimsottari").lte("start_date", _now).gte("end_date", _now).order("level").execute()
            _dasha_list = _dr.data if _dr.data else []
            _current_dasha = ""
            for _d in _dasha_list:
                if _d.get("level") == 1: _current_dasha = _d["planet_or_sign"].strip()
                if _d.get("level") == 2: _current_dasha += "-" + _d["planet_or_sign"].strip()
            exec_data = build_executive_summary(_cd, _jd, _lk, _current_dasha, _dasha_list)
            print(f"[daily-week] Executive summary loaded — {len(exec_data.get('instruments',[]))} instruments")
        except Exception as ex:
            print(f"[daily-week] Could not load executive summary: {ex}")
            return None

        instruments_raw = exec_data.get("instruments", {})
        # instruments is a dict keyed by name — convert to list of values
        if isinstance(instruments_raw, dict):
            instruments = list(instruments_raw.values())
        else:
            instruments = instruments_raw
        if not instruments:
            return None

        # Find highest-status instrument (PEAK first, then ACTIVE)
        best = None
        best_priority = 0
        for inst in instruments:
            status = inst.get("signal_status", "")
            priority = _STATUS_THRESHOLD.get(status, 0)
            sig_score = inst.get("signal_score", 0)
            if priority > best_priority or (priority == best_priority and sig_score > (best.get("signal_score", 0) if best else 0)):
                if priority > 0:
                    best = inst
                    best_priority = priority

        if not best:
            return None

        inst_name = best.get("label", best.get("name", "")).upper()
        status = best.get("signal_status", "ACTIVE")
        sig_score = best.get("signal_score", 0)
        strength = "PEAK" if status == "PEAK" else "ACTIVE"

        # Match to base template
        template_data = None
        for key, val in _WOW_BASE_TEMPLATES.items():
            if key in inst_name or inst_name in key:
                template_data = val
                break
        if not template_data:
            template_data = ("opportunity", "An unexpected signal surfaces today.")

        category, base_template = template_data

        # Check cache first
        cached = _get_wow_cache(chart_id, inst_name)
        if cached.get("hint"):
            return {
                "fires": True,
                "strength": cached.get("strength", strength),
                "category": cached.get("category", category),
                "instrument": inst_name,
                "signal_score": sig_score,
                "hint": cached["hint"],
                "follow_up": "If something happens today in this area — ask Antar about it.",
                "cached": True,
            }

        # Extract user profile
        user_first_name = chart_data.get("first_name") or chart_data.get("name") or "you"
        birth_date = chart_data.get("birth_date") or chart_data.get("dob") or ""
        user_age = _compute_user_age(birth_date) if birth_date else 0
        current_country = chart_data.get("current_country") or chart_data.get("birth_country") or ""
        birth_city = chart_data.get("birth_city") or ""
        gender = chart_data.get("gender") or ""

        # Call Claude for personalized hint
        hint = await _call_claude_wow_hint(
            base_template=base_template,
            category=category,
            instrument_name=inst_name,
            user_first_name=user_first_name,
            user_age=user_age,
            current_country=current_country,
            birth_city=birth_city,
            gender=gender,
            nakshatra=today_nakshatra,
            weekday=weekday,
            signal_score=sig_score,
            strength=strength,
            language=language,
        )

        wow_result = {
            "fires": True,
            "strength": strength,
            "category": category,
            "instrument": inst_name,
            "signal_score": sig_score,
            "hint": hint,
            "follow_up": "If something happens today in this area — ask Antar about it.",
            "cached": False,
        }

        # Save to cache
        _save_wow_cache(chart_id, inst_name, wow_result)

        return wow_result

    except Exception as e:
        print(f"[daily-week] WOW signal failed (non-fatal): {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# GET /api/v1/daily-week/{chart_id}  — 7-Day Daily Signal Engine
# ═══════════════════════════════════════════════════════════════════


# ============================================================
# HORA SPANISH TRANSLATION
# ============================================================

_HORA_WINDOW_ES = {
    "MAGNETISM WINDOW": "VENTANA DE ATRACCIÓN",
    "CONNECT WINDOW": "VENTANA DE CONEXIÓN",
    "REFLECT WINDOW": "VENTANA DE REFLEXIÓN",
    "PEAK WINDOW": "VENTANA DE PICO",
    "◆ PEAK WINDOW": "◆ VENTANA DE PICO",
    "RAHU WINDOW": "VENTANA DE RAHU",
    "KETU WINDOW": "VENTANA DE KETU",
    "EXPANSION WINDOW": "VENTANA DE EXPANSIÓN",
    "DRIVE WINDOW": "VENTANA DE IMPULSO",
    "AUTHORITY WINDOW": "VENTANA DE AUTORIDAD",
    "LOVE WINDOW": "VENTANA DE AMOR",
    "ATTRACTION WINDOW": "VENTANA DE ATRACCIÓN",
    "REFLECTION WINDOW": "VENTANA DE REFLEXIÓN",
    "DISCIPLINE WINDOW": "VENTANA DE DISCIPLINA",
    "STRUCTURE WINDOW": "VENTANA DE ESTRUCTURA",
    "COMMUNICATION WINDOW": "VENTANA DE COMUNICACIÓN",
    "SHADOW WINDOW": "VENTANA DE SOMBRA",
    "DISSOLUTION WINDOW": "VENTANA DE DISOLUCIÓN",
}

_HORA_FIELD_ES = {
    "EXPANSION": "EXPANSIÓN",
    "COMMAND": "MANDO",
    "CONNECTION": "CONEXIÓN",
    "ATTRACTION": "ATRACCIÓN",
    "REFLECTION": "REFLEXIÓN",
    "DISCIPLINE": "DISCIPLINA",
    "STRUCTURE": "ESTRUCTURA",
    "COMMUNICATION": "COMUNICACIÓN",
    "SHADOW": "SOMBRA",
}

_HORA_MODE_ES = {
    "EXPAND": "EXPANDIR",
    "DRIVE": "IMPULSAR",
    "ATTRACT": "ATRAER",
    "REFLECT": "REFLEJAR",
    "STRUCTURE": "ESTRUCTURAR",
    "CONNECT": "CONECTAR",
    "DISSOLVE": "DISOLVER",
}

_HORA_BY_RULER_ES = {
    "Jupiter": {
        "action": "Estrategia, planificación a largo plazo, mentoría, aprendizaje",
        "plain_message": "Piensa en grande. Sesiones de estrategia, planificación a largo plazo, conversaciones de mentoría. Esta es tu ventana de pensamiento más claro.",
    },
    "Mars": {
        "action": "Ejecución de alta intensidad, gimnasio, confrontaciones, llamadas en frío",
        "plain_message": "Alta energía, alta intensidad. Buena para el gimnasio, llamadas en frío, o empujar una tarea difícil. Canalízala o te canaliza a ti.",
    },
    "Sun": {
        "action": "Reuniones de alto nivel, decisiones de liderazgo, movimientos de visibilidad",
        "plain_message": "Tu ventana de mando está abierta. Envía esa propuesta. Toma la decisión. Ten la conversación de alto riesgo.",
    },
    "Venus": {
        "action": "Relaciones, negociación, acuerdos, trabajo creativo, cerrar con calidez",
        "plain_message": "Ventana de atracción. Buena para relaciones, negociación con calidez, trabajo creativo, cerrar con encanto en vez de presión.",
    },
    "Saturn": {
        "action": "Trabajo profundo, disciplina, documentación, auditoría, compromisos a largo plazo",
        "plain_message": "Ventana de estructura. Trabajo profundo, documentación, decisiones serias. Lento pero sólido — lo que construyas aquí dura.",
    },
    "Mercury": {
        "action": "Escritura, análisis, correos, llamadas, negociación, aprendizaje rápido",
        "plain_message": "Ventana de comunicación. Escribe el correo, haz la llamada, analiza los datos. Tu mente está ágil — úsala.",
    },
    "Moon": {
        "action": "Reflexión, descanso, planificar mañana, trabajo emocional, familia",
        "plain_message": "Baja la intensidad. Reflexiona, planea mañana, conversa con la familia. Ventana suave — no fuerces decisiones grandes.",
    },
    "Rahu": {
        "action": "Movimientos no convencionales, tecnología, apuestas calculadas",
        "plain_message": "Ventana de ruptura. Buena para movimientos no convencionales y tecnología — pero verifica dos veces antes de firmar.",
    },
    "Ketu": {
        "action": "Soltar, meditar, revisión, cierre de ciclos — NO inicies nada nuevo",
        "plain_message": "Ventana de disolución. No inicies nada nuevo. Buena para soltar, meditar, cerrar ciclos pendientes.",
    },
}


def _translate_hora_entry_es(h: dict) -> dict:
    """Translate a single hora dict in-place (returns same dict)."""
    if not isinstance(h, dict):
        return h

    # Window label
    if h.get("window") in _HORA_WINDOW_ES:
        h["window"] = _HORA_WINDOW_ES[h["window"]]

    # Field / mode
    if h.get("field") in _HORA_FIELD_ES:
        h["field"] = _HORA_FIELD_ES[h["field"]]
    if h.get("mode") in _HORA_MODE_ES:
        h["mode"] = _HORA_MODE_ES[h["mode"]]

    # Action + plain_message — key off ruler (always English from engine)
    ruler = h.get("ruler")
    if ruler and ruler in _HORA_BY_RULER_ES:
        tr = _HORA_BY_RULER_ES[ruler]
        h["action"] = tr["action"]
        h["plain_message"] = tr["plain_message"]

    return h


def _translate_hora_es(result: dict) -> dict:
    """Apply Spanish translation to full hora response dict."""
    if not isinstance(result, dict):
        return result

    if result.get("current_hora"):
        result["current_hora"] = _translate_hora_entry_es(result["current_hora"])

    if isinstance(result.get("upcoming_horas"), list):
        result["upcoming_horas"] = [
            _translate_hora_entry_es(h) for h in result["upcoming_horas"]
        ]

    if result.get("next_power_hora"):
        result["next_power_hora"] = _translate_hora_entry_es(result["next_power_hora"])

    return result

# ============================================================
# END HORA SPANISH TRANSLATION
# ============================================================

@app.get("/api/v1/hora/{chart_id}")
async def get_hora(chart_id: str, tz_offset: Optional[int] = None, n: int = 8, language: Optional[str] = "en"):
    """
    Kala Hora — Planetary Hour Timing Engine.
    Returns current hora + upcoming N horas with FIELD×MODE guidance.
    Includes WOW convergence if daily signal is available.
    """
    from antar_engine.hora_engine import get_hora_schedule, get_next_power_hora

    # Fetch chart for lat/lng and archetype
    chart_res = supabase.table("charts").select(
        "latitude, longitude, current_country, character_archetype"
    ).eq("id", chart_id).single().execute()

    if not chart_res.data:
        raise HTTPException(status_code=404, detail="Chart not found")

    row = chart_res.data
    lat = row.get("latitude") or 4.7110    # default Bogotá
    lng = row.get("longitude") or -74.0721

    # Auto-detect tz_offset from country if not provided
    if tz_offset is None:
        country = row.get("current_country", "")
        from main import _COUNTRY_TZ_OFFSETS
        tz_offset = _COUNTRY_TZ_OFFSETS.get(country, 0)

    # Get daily field + friction from daily signal (non-fatal)
    daily_field = None
    is_friction_day = False
    try:
        arch = row.get("character_archetype") or {}
        daily_field = arch.get("dominant_field")

        # Check today's daily signal for friction (v2 sync wrapper)
        from antar_engine.daily_prediction_engine import generate_weekly_signals_sync
        import json as _hj
        _raw_cd = row.get("chart_data") or {}
        if isinstance(_raw_cd, str):
            try: _raw_cd = _hj.loads(_raw_cd)
            except: _raw_cd = {}
        _hora_moon = "Aries"
        _hp = _raw_cd.get("planets") or _raw_cd.get("planet_positions") or []
        if isinstance(_hp, list):
            for _hpl in _hp:
                if isinstance(_hpl, dict) and (_hpl.get("name","").lower() == "moon" or _hpl.get("planet","").lower() == "moon"):
                    _hora_moon = _hpl.get("sign") or _hpl.get("rashi") or "Aries"
                    break
        _signals = generate_weekly_signals_sync(natal_moon_sign=_hora_moon)
        if _signals:
            is_friction_day = _signals[0].get("is_friction_day", False)
    except Exception as _de:
        pass  # non-fatal — hora works without daily integration

    result = get_hora_schedule(
        lat=lat,
        lng=lng,
        tz_offset=tz_offset,
        n_horas=n,
        daily_field=daily_field,
        is_friction_day=is_friction_day,
    )

    # Add next power hora for friction days
    if is_friction_day and daily_field and result.get("upcoming_horas"):
        result["next_power_hora"] = get_next_power_hora(
            result["upcoming_horas"], daily_field
        )

    # Spanish translation layer
    if (language or "en").lower() == "es":
        result = _translate_hora_es(result)

    return result


@app.get("/api/v1/hora/{chart_id}")
async def get_hora(chart_id: str, tz_offset: Optional[int] = None, n: int = 8):
    """
    Kala Hora — Planetary Hour Timing Engine.
    Returns current hora + upcoming N horas with FIELD×MODE guidance.
    Includes WOW convergence if daily signal is available.
    """
    from antar_engine.hora_engine import get_hora_schedule, get_next_power_hora

    # Fetch chart for lat/lng and archetype
    chart_res = supabase.table("charts").select(
        "latitude, longitude, current_country, character_archetype"
    ).eq("id", chart_id).single().execute()

    if not chart_res.data:
        raise HTTPException(status_code=404, detail="Chart not found")

    row = chart_res.data
    lat = row.get("latitude") or 4.7110    # default Bogotá
    lng = row.get("longitude") or -74.0721

    # Auto-detect tz_offset from country if not provided
    if tz_offset is None:
        country = row.get("current_country", "")
        from main import _COUNTRY_TZ_OFFSETS
        tz_offset = _COUNTRY_TZ_OFFSETS.get(country, 0)

    # Get daily field + friction from daily signal (non-fatal)
    daily_field = None
    is_friction_day = False
    try:
        arch = row.get("character_archetype") or {}
        daily_field = arch.get("dominant_field")

        # Check today's daily signal for friction (v2 sync wrapper)
        from antar_engine.daily_prediction_engine import generate_weekly_signals_sync
        import json as _hj
        _raw_cd = row.get("chart_data") or {}
        if isinstance(_raw_cd, str):
            try: _raw_cd = _hj.loads(_raw_cd)
            except: _raw_cd = {}
        _hora_moon = "Aries"
        _hp = _raw_cd.get("planets") or _raw_cd.get("planet_positions") or []
        if isinstance(_hp, list):
            for _hpl in _hp:
                if isinstance(_hpl, dict) and (_hpl.get("name","").lower() == "moon" or _hpl.get("planet","").lower() == "moon"):
                    _hora_moon = _hpl.get("sign") or _hpl.get("rashi") or "Aries"
                    break
        _signals = generate_weekly_signals_sync(natal_moon_sign=_hora_moon)
        if _signals:
            is_friction_day = _signals[0].get("is_friction_day", False)
    except Exception as _de:
        pass  # non-fatal — hora works without daily integration

    result = get_hora_schedule(
        lat=lat,
        lng=lng,
        tz_offset=tz_offset,
        n_horas=n,
        daily_field=daily_field,
        is_friction_day=is_friction_day,
    )

    # Add next power hora for friction days
    if is_friction_day and daily_field and result.get("upcoming_horas"):
        result["next_power_hora"] = get_next_power_hora(
            result["upcoming_horas"], daily_field
        )

    return result


@app.get("/api/v1/hora/{chart_id}")
async def get_hora(chart_id: str, tz_offset: Optional[int] = None, n: int = 8):
    """
    Kala Hora — Planetary Hour Timing Engine.
    Returns current hora + upcoming N horas with FIELD×MODE guidance.
    Includes WOW convergence if daily signal is available.
    """
    from antar_engine.hora_engine import get_hora_schedule, get_next_power_hora

    # Fetch chart for lat/lng and archetype
    chart_res = supabase.table("charts").select(
        "latitude, longitude, current_country, character_archetype"
    ).eq("id", chart_id).single().execute()

    if not chart_res.data:
        raise HTTPException(status_code=404, detail="Chart not found")

    row = chart_res.data
    lat = row.get("latitude") or 4.7110    # default Bogotá
    lng = row.get("longitude") or -74.0721

    # Auto-detect tz_offset from country if not provided
    if tz_offset is None:
        country = row.get("current_country", "")
        from main import _COUNTRY_TZ_OFFSETS
        tz_offset = _COUNTRY_TZ_OFFSETS.get(country, 0)

    # Get daily field + friction from daily signal (non-fatal)
    daily_field = None
    is_friction_day = False
    try:
        arch = row.get("character_archetype") or {}
        daily_field = arch.get("dominant_field")

        # Check today's daily signal for friction (v2 sync wrapper)
        from antar_engine.daily_prediction_engine import generate_weekly_signals_sync
        import json as _hj
        _raw_cd = row.get("chart_data") or {}
        if isinstance(_raw_cd, str):
            try: _raw_cd = _hj.loads(_raw_cd)
            except: _raw_cd = {}
        _hora_moon = "Aries"
        _hp = _raw_cd.get("planets") or _raw_cd.get("planet_positions") or []
        if isinstance(_hp, list):
            for _hpl in _hp:
                if isinstance(_hpl, dict) and (_hpl.get("name","").lower() == "moon" or _hpl.get("planet","").lower() == "moon"):
                    _hora_moon = _hpl.get("sign") or _hpl.get("rashi") or "Aries"
                    break
        _signals = generate_weekly_signals_sync(natal_moon_sign=_hora_moon)
        if _signals:
            is_friction_day = _signals[0].get("is_friction_day", False)
    except Exception as _de:
        pass  # non-fatal — hora works without daily integration

    result = get_hora_schedule(
        lat=lat,
        lng=lng,
        tz_offset=tz_offset,
        n_horas=n,
        daily_field=daily_field,
        is_friction_day=is_friction_day,
    )

    # Add next power hora for friction days
    if is_friction_day and daily_field and result.get("upcoming_horas"):
        result["next_power_hora"] = get_next_power_hora(
            result["upcoming_horas"], daily_field
        )

    return result


@app.get("/api/v1/hora/{chart_id}")
async def get_hora(chart_id: str, tz_offset: Optional[int] = None, n: int = 8):
    """
    Kala Hora — Planetary Hour Timing Engine.
    Returns current hora + upcoming N horas with FIELD×MODE guidance.
    Includes WOW convergence if daily signal is available.
    """
    from antar_engine.hora_engine import get_hora_schedule, get_next_power_hora

    # Fetch chart for lat/lng and archetype
    chart_res = supabase.table("charts").select(
        "latitude, longitude, current_country, character_archetype"
    ).eq("id", chart_id).single().execute()

    if not chart_res.data:
        raise HTTPException(status_code=404, detail="Chart not found")

    row = chart_res.data
    lat = row.get("latitude") or 4.7110    # default Bogotá
    lng = row.get("longitude") or -74.0721

    # Auto-detect tz_offset from country if not provided
    if tz_offset is None:
        country = row.get("current_country", "")
        from main import _COUNTRY_TZ_OFFSETS
        tz_offset = _COUNTRY_TZ_OFFSETS.get(country, 0)

    # Get daily field + friction from daily signal (non-fatal)
    daily_field = None
    is_friction_day = False
    try:
        arch = row.get("character_archetype") or {}
        daily_field = arch.get("dominant_field")

        # Check today's daily signal for friction (v2 sync wrapper)
        from antar_engine.daily_prediction_engine import generate_weekly_signals_sync
        import json as _hj
        _raw_cd = row.get("chart_data") or {}
        if isinstance(_raw_cd, str):
            try: _raw_cd = _hj.loads(_raw_cd)
            except: _raw_cd = {}
        _hora_moon = "Aries"
        _hp = _raw_cd.get("planets") or _raw_cd.get("planet_positions") or []
        if isinstance(_hp, list):
            for _hpl in _hp:
                if isinstance(_hpl, dict) and (_hpl.get("name","").lower() == "moon" or _hpl.get("planet","").lower() == "moon"):
                    _hora_moon = _hpl.get("sign") or _hpl.get("rashi") or "Aries"
                    break
        _signals = generate_weekly_signals_sync(natal_moon_sign=_hora_moon)
        if _signals:
            is_friction_day = _signals[0].get("is_friction_day", False)
    except Exception as _de:
        pass  # non-fatal — hora works without daily integration

    result = get_hora_schedule(
        lat=lat,
        lng=lng,
        tz_offset=tz_offset,
        n_horas=n,
        daily_field=daily_field,
        is_friction_day=is_friction_day,
    )

    # Add next power hora for friction days
    if is_friction_day and daily_field and result.get("upcoming_horas"):
        result["next_power_hora"] = get_next_power_hora(
            result["upcoming_horas"], daily_field
        )

    return result



def _translate_daily_signals_es(signals):
    """Translate daily-week signals array to Spanish."""
    if not signals: return signals
    import copy
    result = copy.deepcopy(signals)

    ENERGY = {
        "healing, mysterious": "sanacion y misterio",
        "creative, expressive": "creatividad y expresion",
        "action, courage": "accion y valentia",
        "communication, business": "comunicacion y negocios",
        "expansion, wisdom": "expansion y sabiduria",
        "love, creativity": "amor y creatividad",
        "discipline, karma": "disciplina y karma",
        "leadership, visibility": "liderazgo y visibilidad",
        "intuition, emotions": "intuicion y emociones",
        "transformation": "transformacion profunda",
        "growth, abundance": "crecimiento y abundancia",
        "deep, spiritual": "profundidad espiritual",
        "obstacles, caution": "dia de prueba",
        "fortune, auspicious": "fortuna y energia positiva",
    }
    ACTIONS = {
        "research": "investigacion",
        "solo work": "trabajo en solitario",
        "unconventional approaches": "enfoques innovadores",
        "public-facing work": "trabajo publico",
        "partnerships": "asociaciones",
        "communication": "comunicacion",
        "business meetings": "reuniones de negocios",
        "contracts": "contratos",
        "creative work": "trabajo creativo",
        "leadership": "liderazgo",
        "presentations": "presentaciones",
        "travel": "viajes",
        "learning": "aprendizaje",
        "relationships": "relaciones",
        "physical activity": "actividad fisica",
        "meditation": "meditacion",
        "financial decisions": "decisiones financieras",
        "new beginnings": "nuevos comienzos",
        "deep work": "trabajo profundo",
        "networking": "networking",
        "writing": "escritura",
        "healing": "sanacion",
        "planning": "planificacion",
        "inner work": "trabajo interior",
        "review": "revision",
        "preparation": "preparacion",
        "confrontation": "confrontacion directa",
        "audit": "auditoria",
        # --- Extended action translations (from NAKSHATRA_PROFILES) ---
        "starting projects": "iniciar proyectos",
        "health actions": "acciones de salud",
        "speed decisions": "decisiones rapidas",
        "long-term planning": "planificacion a largo plazo",
        "slow negotiations": "negociaciones lentas",
        "difficult conversations": "conversaciones dificiles",
        "ending cycles": "cerrar ciclos",
        "financial moves": "movimientos financieros",
        "new beginnings": "nuevos comienzos",
        "light social events": "eventos sociales ligeros",
        "cutting losses": "cortar perdidas",
        "clarity conversations": "conversaciones de claridad",
        "editing work": "trabajo de edicion",
        "diplomacy": "diplomacia",
        "compromise situations": "situaciones de compromiso",
        "relationship building": "construir relaciones",
        "financial planning": "planificacion financiera",
        "confrontation": "confrontacion",
        "endings": "finales",
        "exploration": "exploracion",
        "new contacts": "nuevos contactos",
        "commitment decisions": "decisiones de compromiso",
        "finalizing": "finalizar",
        "problem-solving": "resolucion de problemas",
        "technical work": "trabajo tecnico",
        "breakthrough thinking": "pensamiento disruptivo",
        "public appearances": "apariciones publicas",
        "recovery": "recuperacion",
        "relaunching stalled projects": "relanzar proyectos estancados",
        "intense focus": "enfoque intenso",
        "investments": "inversiones",
        "team building": "construir equipo",
        "risky moves": "movimientos arriesgados",
        "speculation": "especulacion",
        "negotiation": "negociacion",
        "uncovering hidden info": "descubrir informacion oculta",
        "trust-building": "construir confianza",
        "openness": "apertura",
        "leadership actions": "acciones de liderazgo",
        "legacy work": "trabajo de legado",
        "collaboration": "colaboracion",
        "blending in": "pasar desapercibido",
        "client entertainment": "entretenimiento de clientes",
        "creative projects": "proyectos creativos",
        "solo deep work": "trabajo profundo en solitario",
        "financial discipline": "disciplina financiera",
        "long-term agreements": "acuerdos a largo plazo",
        "institutional work": "trabajo institucional",
        "rapid pivots": "cambios rapidos",
        "detailed work": "trabajo detallado",
        "craftsmanship": "artesania",
        "healing actions": "acciones de sanacion",
        "big-picture strategy": "estrategia general",
        "delegation": "delegacion",
        "design": "diseno",
        "brand work": "trabajo de marca",
        "pitches": "presentaciones de pitch",
        "routine work": "trabajo rutinario",
        "slow processes": "procesos lentos",
        "flexibility": "flexibilidad",
        "trading": "comercio",
        "fixed commitments": "compromisos fijos",
        "goal-setting": "fijar metas",
        "competitive moves": "movimientos competitivos",
        "ambition-driven work": "trabajo impulsado por ambicion",
        "rest": "descanso",
        "casual socializing": "socializacion informal",
        "team loyalty": "lealtad de equipo",
        "friendship": "amistad",
        "structured work": "trabajo estructurado",
        "isolation": "aislamiento",
        "self-promotion": "autopromocion",
        "authority decisions": "decisiones de autoridad",
        "crisis management": "gestion de crisis",
        "protection": "proteccion",
        "partnership building": "construir alianzas",
        "softness": "suavidad",
        "root-cause analysis": "analisis de causa raiz",
        "philosophy": "filosofia",
        "stability": "estabilidad",
        "new launches": "nuevos lanzamientos",
        "pitching": "hacer pitch",
        "persuasion": "persuasion",
        "accepting defeat": "aceptar la derrota",
        "slowing down": "desacelerar",
        "finalizing wins": "consolidar victorias",
        "integrity-based decisions": "decisiones basadas en integridad",
        "launches": "lanzamientos",
        "compromise": "compromiso",
        "grey areas": "zonas grises",
        "mentorship": "mentoria",
        "advisory conversations": "conversaciones de asesoria",
        "speaking over others": "hablar por encima de otros",
        "impulsive action": "accion impulsiva",
        "wealth moves": "movimientos de riqueza",
        "group leadership": "liderazgo grupal",
        "bold action": "accion audaz",
        "detail work": "trabajo de detalle",
        "unconventional approaches": "enfoques innovadores",
        "public-facing work": "trabajo de cara al publico",
        "high-stakes decisions": "decisiones de alto riesgo",
        "transitions": "transiciones",
        "patience": "paciencia",
        "slow work": "trabajo lento",
        "teaching": "ensenanza",
        "settling matters": "resolver asuntos",
        "fast pivots": "cambios rapidos",
        "closing cycles": "cerrar ciclos",
        "charitable work": "trabajo caritativo",
        "spiritual clarity": "claridad espiritual",
        "new ventures": "nuevos emprendimientos",
        "competitive pressure": "presion competitiva",
        "exercise": "ejercicio",
        "creativity": "creatividad",
        "emotional conversations": "conversaciones emocionales",
        "signing contracts": "firmar contratos",
        # --- Part 2+3: additional action strings ---
        "launching": "lanzar proyectos",
        "negotiating": "negociar",
        "expanding": "expandir",
        "consolidating": "consolidar",
        "reviewing": "revisar",
        "executing": "ejecutar",
        "collaborating": "colaborar",
        "researching": "investigar",
        "presenting": "presentar",
        "selling": "vender",
        "hiring": "contratar",
        "fundraising": "levantar capital",
        "building systems": "construir sistemas",
        "making offers": "hacer ofertas",
        "closing deals": "cerrar tratos",
        "public speaking": "hablar en publico",
        "creating content": "crear contenido",
    }
    DAYS = {
        "Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miercoles",
        "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sabado","Sunday":"Domingo"
    }
    DAY_SHORT = {
        "Monday":"LUN","Tuesday":"MAR","Wednesday":"MIE",
        "Thursday":"JUE","Friday":"Vie","Saturday":"SAB","Sunday":"DOM"
    }
    QUALITY = {
        "Friction": "Friccion",
        "Caution": "Precaucion",
        "Good": "Bueno",
        "Strong": "Fuerte",
        "Excellent": "Excelente",
        "Neutral": "Neutral",
        "Mixed": "Mixto",
    }

    def t_actions(lst):
        return [ACTIONS.get(a, a) for a in (lst or [])]

    def t_signal(text):
        if not text: return text
        # Common patterns in signal text
        replacements = {
            "The energy today is": "La energia hoy es de",
        "The energy today creates": "La energia hoy crea",
        "internal friction": "friccion interna",
        "best used for inner work, review, and preparation rather than launching or confronting": "mejor para trabajo interior y revision que para lanzar o confrontar",
        "compassionate, completing": "compasion y culminacion",
        "completing, compassionate": "culminacion y compasion",
        "auspicious, nourishing": "auspicioso y nutritivo",
        "victorious, completing": "victoria y culminacion",
        "stable, building": "estabilidad y construccion",
        "expansive, optimistic": "expansion y optimismo",
        "sharp, communicative": "agudeza y comunicacion",
        "courageous, initiating": "coraje e iniciativa",
        "pleasurable, creative": "placer y creatividad",
        "disciplined, karmic": "disciplina y karma",
        "spiritual, releasing": "espiritualidad y soltar",
        "transformative, intense": "transformacion intensa",
        "quick, healing": "inicio rapido y sanacion",
        "swift, initiating": "velocidad e iniciativa",
        "swift, initiating —": "velocidad e iniciativa —",
        "sharp, decisive": "claridad y decision",
        "sharp, decisive —": "claridad y decision —",
        "bright, creative": "brillo y creatividad",
        "strong, determined": "fuerza y determinacion",
        "gentle, receptive": "suavidad y receptividad",
        "deep, mystical": "profundidad y misticismo",
        "bold, pioneering": "audacia y pionerismo",
        "graceful, artistic": "gracia y arte",
        "steady, practical": "constancia y practicidad",
        "abundant, growing": "abundancia y crecimiento",
        "The energy today": "La energia hoy",
        "stable, wise": "estabilidad y sabiduria",
        "stable, grounded": "estabilidad y arraigo",
        "focused, determined": "enfoque y determinacion",
        "deep, introspective": "profundidad e introspeccion",
        "social, charming": "energia social y encanto",
        "intense, transformative": "intensidad y transformacion",
        "victorious, unstoppable": "victoria e impulso",
        "curious, searching": "curiosidad y busqueda",
        "nurturing, compassionate": "nutricion y compasion",
        "powerful, authoritative": "poder y autoridad",
        "sharp, analytical": "agudeza y analisis",
        "flowing, adaptable": "fluidez y adaptabilidad",
        "independent, pioneering": "independencia y pionerismo",
        "devoted, faithful": "devocion y lealtad",
        "joyful, creative": "alegria y creatividad",
        "skillful, precise": "habilidad y precision",
        "bright, shining": "brillo y luminosidad",
        "renewing, optimistic": "renovacion y optimismo",
        "nourishing, auspicious": "nutricion y auspicio",
        "perceptive, strategic": "percepcion y estrategia",
        "invincible, purifying": "invencibilidad y pureza",
        "victorious, enduring": "victoria duradera",
        "listening, receptive": "escucha y receptividad",
        "healing, secretive": "sanacion y misterio",
        "intense, passionate": "intensidad y pasion",
        "deep, wise": "profundidad y sabiduria",
        "compassionate, journeying": "compasion y viaje",
        "healing, mysterious": "sanacion y misterio",
        "healing, mysterious —": "sanacion y misterio —",
        "is healing, mysterious": "es de sanacion y misterio",
        "action, courage": "accion y valentia",
        "communication, business": "comunicacion y negocios",
        "expansion, wisdom": "expansion y sabiduria",
        "love, creativity": "amor y creatividad",
        "discipline, karma": "disciplina y karma",
        "leadership, visibility": "liderazgo y visibilidad",
        "intuition, emotions": "intuicion y emociones",
        "growth, abundance": "crecimiento y abundancia",
        "creative, expressive": "creatividad y expresion",
        "amplifies emotional intelligence, intuition": "amplifica la inteligencia emocional y la intuicion",
        "making this a good window for research": "creando una buena ventana para la investigacion",
        "making this a good window for": "creando una buena ventana para",
        ", intuition,": ", intuicion,",
        "emotional intelligence": "inteligencia emocional",
            "lean into it": "aprovechala",
            "amplifies emotional intelligence, intuition": "amplifica la inteligencia emocional y la intuicion",
            "amplifies": "amplifica",
            "making this a good window for": "creando una buena ventana para",
            "making this a": "creando una",
            "good window for": "buena ventana para",
            "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
            "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sabado", "Sunday": "Domingo",
            "creates internal friction": "crea friccion interna",
            "best used for inner work, review, and preparation": "mejor usarla para trabajo interior, revision y preparacion",
            "rather than launching or confronting": "en vez de lanzar o confrontar",
            "overlay favors courage, direct action, confrontation": "favorece el coraje, accion directa y confrontacion",
            "but the": "pero la",
            "Moon energy": "posicion lunar",
            "position slows outer momentum": "frena el impulso externo",
            "creates a stable, grounded": "crea una energia estable y enraizada",
            "good for building": "bueno para construir",
            "favors communication": "favorece la comunicacion",
            "sharp thinking": "pensamiento claro",
        }
        for en, es in replacements.items():
            text = text.replace(en, es)
        return text

    def t_move(text):
        if not text: return text
        replacements = {
            "Take one concrete step today in:": "Da un paso concreto hoy en:",
            "Take one concrete step today": "Da un paso concreto hoy",
            "Avoid:": "Evita:",
            "Use today to audit, review, or strengthen one thing already in motion.": "Usa hoy para revisar o fortalecer algo ya en marcha.",
            "Hold new launches until energy lifts.": "Espera para lanzar algo nuevo.",
            "research": "investigacion",
            "solo work": "trabajo en solitario",
            "unconventional approaches": "enfoques innovadores",
            "public-facing work": "trabajo publico",
            "partnerships": "asociaciones",
            "communication": "comunicacion",
            "creative work": "trabajo creativo",
            "leadership": "liderazgo",
            "starting projects": "iniciar proyectos",
            "health actions": "acciones de salud",
            "long-term planning": "planificacion a largo plazo",
            "slow negotiations": "negociaciones lentas",
            "financial moves": "movimientos financieros",
            "problem-solving": "resolucion de problemas",
            "technical work": "trabajo tecnico",
            "investments": "inversiones",
            "team building": "construir equipo",
            "leadership actions": "acciones de liderazgo",
            "detailed work": "trabajo detallado",
            "goal-setting": "fijar metas",
            "negotiation": "negociacion",
            "flexibility": "flexibilidad",
            "closing cycles": "cerrar ciclos",
        }
        for en, es in replacements.items():
            text = text.replace(en, es)
        return text

    for day in result:
        if "energy" in day:
            day["energy"] = ENERGY.get(day["energy"], day["energy"])
        if "aligned_for" in day:
            day["aligned_for"] = t_actions(day["aligned_for"])
        if "friction_for" in day:
            day["friction_for"] = t_actions(day["friction_for"])
        if "signal" in day:
            day["signal"] = t_signal(day["signal"])
        if "move" in day:
            day["move"] = t_move(day["move"])
        if "day" in day:
            day["day_es"] = DAYS.get(day["day"], day["day"])
            day["day_short_es"] = DAY_SHORT.get(day["day"], day["day"][:3].upper())
        # Translate score label
        score = day.get("score", 5)
        is_friction = day.get("is_friction_day", False)
        if is_friction:
            day["quality_label"] = "Friccion"
            day["quality_label_es"] = "Friccion"
        elif score >= 8:
            day["quality_label_es"] = "Excelente"
        elif score >= 7:
            day["quality_label_es"] = "Fuerte"
        elif score >= 6:
            day["quality_label_es"] = "Bueno"
        elif score >= 4:
            day["quality_label_es"] = "Mixto"
        else:
            day["quality_label_es"] = "Precaucion"

    return result


@app.get("/api/v1/daily-week/{chart_id}")
async def get_daily_week(chart_id: str, language: str = "en"):
    """
    Returns 7-day daily signal array.
    Today: Python energy forecast + Claude-personalized WOW hint (if PEAK/ACTIVE)
    Days 2-7: Python energy forecast only
    WOW hint cached 24hrs in charts.daily_wow_cache

    Args:
        language: Language code (e.g. "en", "es", "hi"). Default "en".
    """
    try:
        # 1. Fetch chart
        chart_resp = supabase.table("charts").select("*").eq("id", chart_id).single().execute()
        if not chart_resp.data:
            raise HTTPException(status_code=404, detail=f"Chart not found: {chart_id}")
        chart_data = chart_resp.data

        # 2. Extract natal Moon sign
        natal_moon_sign = "Aries"
        planets = None
        raw = chart_data.get("chart_data") or chart_data
        if isinstance(raw, dict):
            planets = raw.get("planets") or raw.get("planet_positions")
        if planets:
            for p in planets:
                if isinstance(p, dict):
                    name = p.get("name", "").lower() or p.get("planet", "").lower()
                    if name == "moon":
                        natal_moon_sign = p.get("sign") or p.get("rashi") or "Aries"
                        break

        print(f"[daily-week] chart={chart_id} natal_moon={natal_moon_sign}")

        # 3. Generate 7-day Python signals (v2 — LLM-backed)
        from antar_engine.daily_prediction_engine import generate_weekly_signals
        signals = await generate_weekly_signals(
            natal_moon_sign=natal_moon_sign,
            chart_id=chart_id,
            supabase_client=supabase,
            language=language,
        )

        # 5. Get WOW event signal for TODAY — v2 with full matrix
        today_data = signals[0] if signals else {}
        today_nakshatra = today_data.get("moon_nakshatra", "Jyeshtha")
        today_moon_sign = today_data.get("moon_sign", "Scorpio")
        today_score = today_data.get("score", 5)
        today_is_friction = today_data.get("is_friction_day", False)
        today_weekday = today_data.get("day", "Monday")
        all_scores = [d.get("score", 5) for d in signals]

        wow_signal = await _get_wow_signal_for_chart_v2(
            chart_id=chart_id,
            chart_data=chart_data,
            today_nakshatra=today_nakshatra,
            today_moon_sign=today_moon_sign,
            today_score=today_score,
            is_friction=today_is_friction,
            all_scores=all_scores,
            weekday=today_weekday,
            language=language,
        )

        # 5. Attach WOW to today only
        for i, day in enumerate(signals):
            day["event_signal"] = wow_signal if i == 0 else None

        if language == "es":
            signals = _translate_daily_signals_es(signals)

        return {
            "chart_id": chart_id,
            "natal_moon_sign": natal_moon_sign,
            "language": language,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "days": signals
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[daily-week] Error for chart {chart_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Daily week generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# GET /api/v1/daily-week/{chart_id}  — 7-Day Daily Signal Engine
# Timezone-aware: pass ?tz_offset=-5 or auto-detected from country
# ═══════════════════════════════════════════════════════════════════


def _translate_daily_signals_es(signals):
    """Translate daily-week signals array to Spanish."""
    if not signals: return signals
    import copy
    result = copy.deepcopy(signals)

    ENERGY = {
        "healing, mysterious": "sanacion y misterio",
        "creative, expressive": "creatividad y expresion",
        "action, courage": "accion y valentia",
        "communication, business": "comunicacion y negocios",
        "expansion, wisdom": "expansion y sabiduria",
        "love, creativity": "amor y creatividad",
        "discipline, karma": "disciplina y karma",
        "leadership, visibility": "liderazgo y visibilidad",
        "intuition, emotions": "intuicion y emociones",
        "transformation": "transformacion profunda",
        "growth, abundance": "crecimiento y abundancia",
        "deep, spiritual": "profundidad espiritual",
        "obstacles, caution": "dia de prueba",
        "fortune, auspicious": "fortuna y energia positiva",
    }
    ACTIONS = {
        "research": "investigacion",
        "solo work": "trabajo en solitario",
        "unconventional approaches": "enfoques innovadores",
        "public-facing work": "trabajo publico",
        "partnerships": "asociaciones",
        "communication": "comunicacion",
        "business meetings": "reuniones de negocios",
        "contracts": "contratos",
        "creative work": "trabajo creativo",
        "leadership": "liderazgo",
        "presentations": "presentaciones",
        "travel": "viajes",
        "learning": "aprendizaje",
        "relationships": "relaciones",
        "physical activity": "actividad fisica",
        "meditation": "meditacion",
        "financial decisions": "decisiones financieras",
        "new beginnings": "nuevos comienzos",
        "deep work": "trabajo profundo",
        "networking": "networking",
        "writing": "escritura",
        "healing": "sanacion",
        "planning": "planificacion",
        "inner work": "trabajo interior",
        "review": "revision",
        "preparation": "preparacion",
        "confrontation": "confrontacion directa",
        "audit": "auditoria",
        # --- Full NAKSHATRA_PROFILES coverage ---
        "starting projects": "iniciar proyectos",
        "health actions": "acciones de salud",
        "speed decisions": "decisiones rapidas",
        "long-term planning": "planificacion a largo plazo",
        "slow negotiations": "negociaciones lentas",
        "difficult conversations": "conversaciones dificiles",
        "ending cycles": "cerrar ciclos",
        "financial moves": "movimientos financieros",
        "light social events": "eventos sociales ligeros",
        "cutting losses": "cortar perdidas",
        "clarity conversations": "conversaciones de claridad",
        "editing work": "trabajo de edicion",
        "diplomacy": "diplomacia",
        "compromise situations": "situaciones de compromiso",
        "relationship building": "construir relaciones",
        "financial planning": "planificacion financiera",
        "endings": "finales",
        "exploration": "exploracion",
        "new contacts": "nuevos contactos",
        "commitment decisions": "decisiones de compromiso",
        "finalizing": "finalizar",
        "problem-solving": "resolucion de problemas",
        "technical work": "trabajo tecnico",
        "breakthrough thinking": "pensamiento disruptivo",
        "public appearances": "apariciones publicas",
        "recovery": "recuperacion",
        "relaunching stalled projects": "relanzar proyectos estancados",
        "intense focus": "enfoque intenso",
        "investments": "inversiones",
        "team building": "construir equipo",
        "risky moves": "movimientos arriesgados",
        "speculation": "especulacion",
        "negotiation": "negociacion",
        "uncovering hidden info": "descubrir informacion oculta",
        "trust-building": "construir confianza",
        "openness": "apertura",
        "leadership actions": "acciones de liderazgo",
        "legacy work": "trabajo de legado",
        "collaboration": "colaboracion",
        "blending in": "pasar desapercibido",
        "client entertainment": "entretenimiento de clientes",
        "creative projects": "proyectos creativos",
        "solo deep work": "trabajo profundo en solitario",
        "financial discipline": "disciplina financiera",
        "long-term agreements": "acuerdos a largo plazo",
        "institutional work": "trabajo institucional",
        "rapid pivots": "cambios rapidos",
        "detailed work": "trabajo detallado",
        "craftsmanship": "artesania",
        "healing actions": "acciones de sanacion",
        "big-picture strategy": "estrategia general",
        "delegation": "delegacion",
        "design": "diseno",
        "brand work": "trabajo de marca",
        "pitches": "presentaciones de pitch",
        "routine work": "trabajo rutinario",
        "slow processes": "procesos lentos",
        "flexibility": "flexibilidad",
        "trading": "comercio",
        "fixed commitments": "compromisos fijos",
        "goal-setting": "fijar metas",
        "competitive moves": "movimientos competitivos",
        "ambition-driven work": "trabajo impulsado por ambicion",
        "rest": "descanso",
        "casual socializing": "socializacion informal",
        "team loyalty": "lealtad de equipo",
        "friendship": "amistad",
        "structured work": "trabajo estructurado",
        "isolation": "aislamiento",
        "self-promotion": "autopromocion",
        "authority decisions": "decisiones de autoridad",
        "crisis management": "gestion de crisis",
        "protection": "proteccion",
        "partnership building": "construir alianzas",
        "softness": "suavidad",
        "root-cause analysis": "analisis de causa raiz",
        "philosophy": "filosofia",
        "stability": "estabilidad",
        "new launches": "nuevos lanzamientos",
        "pitching": "hacer pitch",
        "persuasion": "persuasion",
        "accepting defeat": "aceptar la derrota",
        "slowing down": "desacelerar",
        "finalizing wins": "consolidar victorias",
        "integrity-based decisions": "decisiones basadas en integridad",
        "launches": "lanzamientos",
        "compromise": "compromiso",
        "grey areas": "zonas grises",
        "mentorship": "mentoria",
        "advisory conversations": "conversaciones de asesoria",
        "speaking over others": "hablar por encima de otros",
        "impulsive action": "accion impulsiva",
        "wealth moves": "movimientos de riqueza",
        "group leadership": "liderazgo grupal",
        "bold action": "accion audaz",
        "detail work": "trabajo de detalle",
        "high-stakes decisions": "decisiones de alto riesgo",
        "transitions": "transiciones",
        "patience": "paciencia",
        "slow work": "trabajo lento",
        "teaching": "ensenanza",
        "settling matters": "resolver asuntos",
        "fast pivots": "cambios rapidos",
        "closing cycles": "cerrar ciclos",
        "charitable work": "trabajo caritativo",
        "spiritual clarity": "claridad espiritual",
        "new ventures": "nuevos emprendimientos",
        "competitive pressure": "presion competitiva",
        "exercise": "ejercicio",
        "creativity": "creatividad",
        "emotional conversations": "conversaciones emocionales",
        "signing contracts": "firmar contratos",
        "launching": "lanzar proyectos",
        "negotiating": "negociar",
        "expanding": "expandir",
        "consolidating": "consolidar",
        "reviewing": "revisar",
        "executing": "ejecutar",
        "collaborating": "colaborar",
        "researching": "investigar",
        "presenting": "presentar",
        "selling": "vender",
        "hiring": "contratar",
        "fundraising": "levantar capital",
        "building systems": "construir sistemas",
        "making offers": "hacer ofertas",
        "closing deals": "cerrar tratos",
        "public speaking": "hablar en publico",
        "creating content": "crear contenido",
    }
    DAYS = {
        "Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miercoles",
        "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sabado","Sunday":"Domingo"
    }
    DAY_SHORT = {
        "Monday":"LUN","Tuesday":"MAR","Wednesday":"MIE",
        "Thursday":"JUE","Friday":"Vie","Saturday":"SAB","Sunday":"DOM"
    }
    QUALITY = {
        "Friction": "Friccion",
        "Caution": "Precaucion",
        "Good": "Bueno",
        "Strong": "Fuerte",
        "Excellent": "Excelente",
        "Neutral": "Neutral",
        "Mixed": "Mixto",
    }

    def t_actions(lst):
        return [ACTIONS.get(a, a) for a in (lst or [])]

    def t_signal(text):
        if not text: return text
        # Common patterns in signal text
        replacements = {
            "The energy today is": "La energia hoy es de",
        "The energy today creates": "La energia hoy crea",
        "internal friction": "friccion interna",
        "best used for inner work, review, and preparation rather than launching or confronting": "mejor para trabajo interior y revision que para lanzar o confrontar",
        "compassionate, completing": "compasion y culminacion",
        "completing, compassionate": "culminacion y compasion",
        "auspicious, nourishing": "auspicioso y nutritivo",
        "victorious, completing": "victoria y culminacion",
        "stable, building": "estabilidad y construccion",
        "expansive, optimistic": "expansion y optimismo",
        "sharp, communicative": "agudeza y comunicacion",
        "courageous, initiating": "coraje e iniciativa",
        "pleasurable, creative": "placer y creatividad",
        "disciplined, karmic": "disciplina y karma",
        "spiritual, releasing": "espiritualidad y soltar",
        "transformative, intense": "transformacion intensa",
        "quick, healing": "inicio rapido y sanacion",
        "swift, initiating": "velocidad e iniciativa",
        "swift, initiating —": "velocidad e iniciativa —",
        "sharp, decisive": "claridad y decision",
        "sharp, decisive —": "claridad y decision —",
        "bright, creative": "brillo y creatividad",
        "strong, determined": "fuerza y determinacion",
        "gentle, receptive": "suavidad y receptividad",
        "deep, mystical": "profundidad y misticismo",
        "bold, pioneering": "audacia y pionerismo",
        "graceful, artistic": "gracia y arte",
        "steady, practical": "constancia y practicidad",
        "abundant, growing": "abundancia y crecimiento",
        "The energy today": "La energia hoy",
        "stable, wise": "estabilidad y sabiduria",
        "stable, grounded": "estabilidad y arraigo",
        "focused, determined": "enfoque y determinacion",
        "deep, introspective": "profundidad e introspeccion",
        "social, charming": "energia social y encanto",
        "intense, transformative": "intensidad y transformacion",
        "victorious, unstoppable": "victoria e impulso",
        "curious, searching": "curiosidad y busqueda",
        "nurturing, compassionate": "nutricion y compasion",
        "powerful, authoritative": "poder y autoridad",
        "sharp, analytical": "agudeza y analisis",
        "flowing, adaptable": "fluidez y adaptabilidad",
        "independent, pioneering": "independencia y pionerismo",
        "devoted, faithful": "devocion y lealtad",
        "joyful, creative": "alegria y creatividad",
        "skillful, precise": "habilidad y precision",
        "bright, shining": "brillo y luminosidad",
        "renewing, optimistic": "renovacion y optimismo",
        "nourishing, auspicious": "nutricion y auspicio",
        "perceptive, strategic": "percepcion y estrategia",
        "invincible, purifying": "invencibilidad y pureza",
        "victorious, enduring": "victoria duradera",
        "listening, receptive": "escucha y receptividad",
        "healing, secretive": "sanacion y misterio",
        "intense, passionate": "intensidad y pasion",
        "deep, wise": "profundidad y sabiduria",
        "compassionate, journeying": "compasion y viaje",
        "healing, mysterious": "sanacion y misterio",
        "healing, mysterious —": "sanacion y misterio —",
        "is healing, mysterious": "es de sanacion y misterio",
        "action, courage": "accion y valentia",
        "communication, business": "comunicacion y negocios",
        "expansion, wisdom": "expansion y sabiduria",
        "love, creativity": "amor y creatividad",
        "discipline, karma": "disciplina y karma",
        "leadership, visibility": "liderazgo y visibilidad",
        "intuition, emotions": "intuicion y emociones",
        "growth, abundance": "crecimiento y abundancia",
        "creative, expressive": "creatividad y expresion",
        "amplifies emotional intelligence, intuition": "amplifica la inteligencia emocional y la intuicion",
        "making this a good window for research": "creando una buena ventana para la investigacion",
        "making this a good window for": "creando una buena ventana para",
        ", intuition,": ", intuicion,",
        "emotional intelligence": "inteligencia emocional",
            "lean into it": "aprovechala",
            "amplifies emotional intelligence, intuition": "amplifica la inteligencia emocional y la intuicion",
            "amplifies": "amplifica",
            "making this a good window for": "creando una buena ventana para",
            "making this a": "creando una",
            "good window for": "buena ventana para",
            "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
            "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sabado", "Sunday": "Domingo",
            "creates internal friction": "crea friccion interna",
            "best used for inner work, review, and preparation": "mejor usarla para trabajo interior, revision y preparacion",
            "rather than launching or confronting": "en vez de lanzar o confrontar",
            "overlay favors courage, direct action, confrontation": "favorece el coraje, accion directa y confrontacion",
            "but the": "pero la",
            "Moon energy": "posicion lunar",
            "position slows outer momentum": "frena el impulso externo",
            "creates a stable, grounded": "crea una energia estable y enraizada",
            "good for building": "bueno para construir",
            "favors communication": "favorece la comunicacion",
            "sharp thinking": "pensamiento claro",
        }
        for en, es in replacements.items():
            text = text.replace(en, es)
        return text

    def t_move(text):
        if not text: return text
        replacements = {
            "Take one concrete step today in:": "Da un paso concreto hoy en:",
            "Take one concrete step today": "Da un paso concreto hoy",
            "Avoid:": "Evita:",
            "Use today to audit, review, or strengthen one thing already in motion.": "Usa hoy para revisar o fortalecer algo ya en marcha.",
            "Hold new launches until energy lifts.": "Espera para lanzar algo nuevo.",
            "research": "investigacion",
            "solo work": "trabajo en solitario",
            "unconventional approaches": "enfoques innovadores",
            "public-facing work": "trabajo publico",
            "partnerships": "asociaciones",
            "communication": "comunicacion",
            "creative work": "trabajo creativo",
            "leadership": "liderazgo",
        }
        for en, es in replacements.items():
            text = text.replace(en, es)
        return text

    for day in result:
        if "energy" in day:
            day["energy"] = ENERGY.get(day["energy"], day["energy"])
        if "aligned_for" in day:
            day["aligned_for"] = t_actions(day["aligned_for"])
        if "friction_for" in day:
            day["friction_for"] = t_actions(day["friction_for"])
        if "signal" in day:
            day["signal"] = t_signal(day["signal"])
        if "move" in day:
            day["move"] = t_move(day["move"])
        if "day" in day:
            day["day_es"] = DAYS.get(day["day"], day["day"])
            day["day_short_es"] = DAY_SHORT.get(day["day"], day["day"][:3].upper())
        # Translate score label
        score = day.get("score", 5)
        is_friction = day.get("is_friction_day", False)
        if is_friction:
            day["quality_label"] = "Friccion"
            day["quality_label_es"] = "Friccion"
        elif score >= 8:
            day["quality_label_es"] = "Excelente"
        elif score >= 7:
            day["quality_label_es"] = "Fuerte"
        elif score >= 6:
            day["quality_label_es"] = "Bueno"
        elif score >= 4:
            day["quality_label_es"] = "Mixto"
        else:
            day["quality_label_es"] = "Precaucion"

    return result


@app.get("/api/v1/daily-week/{chart_id}")
async def get_daily_week(chart_id: str, tz_offset: float = None, language: str = "en"):
    """
    Returns 7-day daily signal array starting from TODAY in user's local timezone.

    Args:
        tz_offset: UTC offset in hours (e.g. -5 for Colombia/EST, -3 for Brazil)
                   If not provided, auto-detected from chart's current_country.
        language: Language code (e.g. "en", "es", "hi"). Default "en".

    WOW event signal fires for today when executive summary shows PEAK/ACTIVE instrument.
    """
    try:
        # 1. Fetch chart
        chart_resp = supabase.table("charts").select("*").eq("id", chart_id).single().execute()
        if not chart_resp.data:
            raise HTTPException(status_code=404, detail=f"Chart not found: {chart_id}")
        chart_data = chart_resp.data

        # 2. Extract natal Moon sign
        natal_moon_sign = "Aries"
        planets = None
        raw = chart_data.get("chart_data") or chart_data
        if isinstance(raw, dict):
            planets = raw.get("planets") or raw.get("planet_positions")
        if planets:
            for p in planets:
                if isinstance(p, dict):
                    name = p.get("name", "").lower() or p.get("planet", "").lower()
                    if name == "moon":
                        natal_moon_sign = p.get("sign") or p.get("rashi") or "Aries"
                        break

        # 3. Compute local start date
        current_country = chart_data.get("current_country") or chart_data.get("birth_country") or ""
        start_date = _get_local_start_date(
            tz_offset=int(tz_offset) if tz_offset is not None else None,
            current_country=current_country
        )
        effective_offset = int(tz_offset) if tz_offset is not None else _COUNTRY_TZ_OFFSETS.get(
            current_country.upper(), 0
        )

        print(f"[daily-week] chart={chart_id} natal_moon={natal_moon_sign} country={current_country} tz={effective_offset:+d} start={start_date.date()}")

        # 4. Generate 7-day signals from local start date (v2 — LLM-backed)
        from antar_engine.daily_prediction_engine import generate_weekly_signals
        signals = await generate_weekly_signals(
            natal_moon_sign=natal_moon_sign,
            start_date=start_date,
            chart_id=chart_id,
            supabase_client=supabase,
            language=language,
            tz_offset=effective_offset,
        )

        # 5. Get WOW event signal for TODAY only
        today_nakshatra = signals[0].get("moon_nakshatra", "Unknown") if signals else "Unknown"
        today_weekday = signals[0].get("day", "Monday") if signals else "Monday"
        wow_signal = await _get_wow_signal_for_chart(chart_id, chart_data, today_nakshatra, today_weekday, language=language)

        # 6. Attach WOW to today only
        for i, day in enumerate(signals):
            day["event_signal"] = wow_signal if i == 0 else None

        if language == "es":
            signals = _translate_daily_signals_es(signals)

        # === LIVE TRANSIT HIGHLIGHTS ===
        _transit_highlights = []
        _transit_positions = {}
        _transit_activated_areas = []
        try:
            from antar_engine.transit_engine import get_full_transit_report
            _raw_cd = chart_data.get("chart_data") or chart_data
            if isinstance(_raw_cd, str):
                import json as _tjson
                try: _raw_cd = _tjson.loads(_raw_cd)
                except: _raw_cd = {}
            _transit_rpt = get_full_transit_report(_raw_cd)
            _transit_highlights = _transit_rpt.get("major_transits", [])
            _transit_positions = _transit_rpt.get("transit_positions", {})
            _transit_activated_areas = _transit_rpt.get("activated_areas", [])
        except Exception as _dte:
            print(f"[daily-week] Transit computation failed (non-fatal): {_dte}")
        # === END LIVE TRANSIT HIGHLIGHTS ===

        return {
            "chart_id": chart_id,
            "natal_moon_sign": natal_moon_sign,
            "language": language,
            "timezone_offset": effective_offset,
            "local_date": start_date.strftime("%Y-%m-%d"),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "days": signals,
            "transit_highlights": _transit_highlights,
            "transit_positions": _transit_positions,
            "activated_areas": _transit_activated_areas,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[daily-week] Error for chart {chart_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Daily week generation failed: {str(e)}")



# ══════════════════════════════════════════════════════════════════════════════
# CONNECTIONS — Saved compatibility relationships for Ask Antar context
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/connections/{chart_id}")
async def get_connections(chart_id: str):
    """
    Returns all saved connections for a chart.
    Connections are auto-created after every compatibility reading.
    Used by Ask Antar to inject relationship context into predictions.
    """
    try:
        res = supabase.table("chart_connections").select("*") \
            .eq("chart_id_a", chart_id) \
            .order("updated_at", desc=True) \
            .execute()

        connections = []
        for row in (res.data or []):
            connections.append({
                "id":             row["id"],
                "chart_id_b":     row["chart_id_b"],
                "name_b":         row.get("name_b", ""),
                "compat_type":    row.get("compat_type", ""),
                "overall_score":  row.get("overall_score", 0),
                "pairing_name":   row.get("pairing_name", ""),
                "verdict":        row.get("verdict", ""),
                "analysis_summary": row.get("analysis_summary", ""),
                "score_breakdown":  row.get("score_breakdown", {}),
                "field_mode_layer": row.get("field_mode_layer", {}),
                "updated_at":     row.get("updated_at", ""),
            })

        return {
            "chart_id":    chart_id,
            "connections": connections,
            "total":       len(connections),
        }

    except Exception as e:
        print(f"[connections] GET error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/connections/{chart_id}/{connection_id}")
async def delete_connection(chart_id: str, connection_id: str):
    """Remove a saved connection."""
    try:
        supabase.table("chart_connections").delete() \
            .eq("id", connection_id) \
            .eq("chart_id_a", chart_id) \
            .execute()
        return {"success": True, "deleted": connection_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






# ============================================================================
# ASTROCARTOGRAPHY RECOMMENDATION ENDPOINT
# ============================================================================

class AstroRecommendRequest(BaseModel):
    chart_id: str
    intent:   str  = Field("startup", description="startup|wealth|billionaire|career|relationships|general")
    region:   str  = Field("global",  description="latam|europe|asia|middleeast|africa|north_america|global")
    language: str  = Field("en",      description="en|es")
    top_n:    int  = Field(5,         description="1-10")
    explain:  bool = Field(True,      description="Add DeepSeek narrative")


@app.post("/api/v1/astrocartography/recommend")
async def astrocartography_recommend(
    request: AstroRecommendRequest,
    authorization: Optional[str] = Header(None),
):
    """
    City recommendation engine:
    1. Python computes deterministic scores (line × dasha × yoga × paran)
    2. DeepSeek writes context-aware narrative from the scores
    """
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_record = chart_res.data[0]

    from antar_engine.chart_context_builder_json import _fetch_dashas
    from antar_engine.astrocartography_recommender import recommend_cities

    dashas = _fetch_dashas(request.chart_id, supabase)

    # Extract natal yogas
    chart_data  = chart_record.get("chart_data") or {}
    natal_yogas = chart_data.get("yogas") or []
    if not natal_yogas:
        planets   = chart_data.get("planets", {})
        jup_house = (planets.get("Jupiter") or {}).get("house")
        ven_house = (planets.get("Venus") or {}).get("house")
        if jup_house == 2 and ven_house == 11:
            natal_yogas = [{"name": "Dhana Yoga", "planets": ["Jupiter", "Venus"]}]

    # Python ranking — deterministic
    ranking = recommend_cities(
        chart_record=chart_record,
        dashas=dashas,
        natal_yogas=natal_yogas,
        intent=request.intent,
        region=request.region,
        language=request.language,
        top_n=min(request.top_n, 10),
    )

    if not request.explain or not ranking.get("top_cities"):
        return ranking

    # --- DeepSeek narrative ---
    import json as _json, httpx, os
    from datetime import date

    # Build chart summary for prompt
    lagna_sign   = (chart_data.get("lagna") or {}).get("sign", "")
    atmakaraka   = chart_data.get("atmakaraka", "")
    archetype    = (chart_record.get("character_archetype") or {}).get("name", "")
    career_stage = chart_record.get("career_stage", "")
    current_city = chart_record.get("current_city") or ""
    current_country = chart_record.get("current_country") or ""

    # Age
    age = None
    try:
        bd = chart_record.get("birth_date", "")
        if bd:
            b = date.fromisoformat(str(bd)[:10])
            t = date.today()
            age = t.year - b.year - (1 if (t.month, t.day) < (b.month, b.day) else 0)
    except Exception:
        pass

    dc = ranking["dasha_context"]

    chart_summary = (
        f"Lagna: {lagna_sign}, Atmakaraka: {atmakaraka}, "
        f"Archetype: {archetype}, Age: {age}, Career: {career_stage}"
    )
    dasha_summary = (
        f"Current MD: {dc.get('current_md')} until {dc.get('current_md_end','')[:10]} | "
        f"AD: {dc.get('current_ad')} | "
        f"Next MD: {dc.get('next_md')} from {dc.get('next_md_start','')[:10]} (18-year window)"
    )

    # City rankings compact — only what DeepSeek needs
    city_rankings = []
    for i, c in enumerate(ranking["top_cities"]):
        city_rankings.append({
            "rank":          i + 1,
            "city":          c["city"],
            "score":         c["score"],
            "is_current":    c.get("is_current_location", False),
            "dasha_notes":   c.get("dasha_notes", []),
            "yoga_notes":    c.get("yoga_notes", []),
            "paran_notes":   c.get("paran_notes", []),
            "top_lines":     [{
                "planet": l["planet"],
                "line":   l["line"],
                "strength": l["strength"]
            } for l in c.get("line_details", [])[:3]],
        })

    # DeepSeek prompt — exact spec
    _system = (
        "You are Antar's astrocartography interpreter. "
        "You receive deterministic scores from the Python engine. Do NOT calculate anything. "
        "Your job is to write a warm, specific, actionable narrative from the data provided."
    )

    _user = f"""You are Antar's astrocartography interpreter.
You receive deterministic scores from the Python engine. Do NOT calculate anything.

USER CONTEXT:
- Current location: {current_city or current_country or "unknown"}
- Intent: {request.intent} (startup / billionaire / wealth)
- Chart: {chart_summary}
- Dashas: {dasha_summary}

PYTHON RANKING:
{_json.dumps(city_rankings, indent=2)}

STAY-VS-MOVE RULE RESULT: {ranking["stay_vs_move"]}

MISSING LINES: {", ".join(ranking.get("missing_lines", [])) or "none"}

Your job:
1. If stay_vs_move is "stay": explain why the user should stay put and what to optimize there
2. If "move": recommend the top city and explain why with specific timing
3. Always mention missing lines honestly (e.g., "Rahu MC lines not in dataset — billionaire public track not confirmed")
4. End with a "Your move" sentence — one specific action this week
5. Be warm, specific, and actionable
6. Do NOT use planet names in the final output — use energy language instead
   (e.g., "expansion energy" not "Jupiter", "disruption channel" not "Rahu")

{"Respond in Spanish." if request.language == "es" else "Respond in English."}

Output JSON:
{{
  "plain_summary": "2-3 sentences — where should this person be and why",
  "stay_or_move_explanation": "why stay / why move with timing",
  "top_city_why": "what makes the #1 city right for this person specifically",
  "honest_gaps": "what data is missing — be direct",
  "your_move": "one specific action this week"
}}"""

    _parsed = {}
    try:
        _ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not _ds_key:
            raise ValueError("DEEPSEEK_API_KEY not set")

        _resp = httpx.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {_ds_key}"},
            json={
                "model":       "deepseek-chat",
                "messages":    [
                    {"role": "system", "content": _system},
                    {"role": "user",   "content": _user},
                ],
                "temperature": 0.2,
                "max_tokens":  700,
            },
            timeout=30.0,
        )
        _raw = _resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if "```" in _raw:
            _parts = _raw.split("```")
            for _p in _parts:
                if "{" in _p:
                    _raw = _p.lstrip("json").strip()
                    break

        _parsed = _json.loads(_raw)
        print(f"[astro-deepseek] OK — {len(_raw)} chars")

    except Exception as _e:
        print(f"[astro-deepseek] DeepSeek failed (non-fatal): {_e}")
        _parsed = {
            "plain_summary":             ranking.get("top_cities", [{}])[0].get("city", ""),
            "stay_or_move_explanation":  ranking["stay_vs_move"],
            "top_city_why":              "",
            "honest_gaps":               ", ".join(ranking.get("missing_lines", [])),
            "your_move":                 "",
        }

    return {
        **ranking,
        "narrative":           _parsed,
        "explanation_model":   "deepseek-chat",
    }

# ============================================================================
# END ASTROCARTOGRAPHY RECOMMENDATION ENDPOINT
# ============================================================================


# ============================================================================
# SIGNATURE VERIFICATION — Onboarding WOW screen
# ============================================================================

class SignatureConfirmRequest(BaseModel):
    chart_id: str
    confirmations: dict  # {statement_id: "confirmed"|"declined"|"skipped"}


@app.get("/api/v1/chart/signature/{chart_id}")
async def get_signature_statements(chart_id: str):
    """
    Generate 3 past-event statements for the onboarding WOW screen.
    Uses DashaEventMapper — no LLM involved, instant response.
    Returns human-readable statements with no astrological terms.
    """
    try:
        from antar_engine.dasha_event_mapper import map_all_events

        # Fetch chart data
        chart_res = supabase.table("charts").select(
            "chart_data,birth_date"
        ).eq("id", chart_id).single().execute()

        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")

        chart_data  = chart_res.data.get("chart_data") or {}
        birth_date  = str(chart_res.data.get("birth_date", ""))
        birth_year  = int(birth_date[:4]) if birth_date else 1980
        lagna       = (chart_data.get("lagna") or {}).get("sign", "Capricorn")

        # Fetch ADs from dasha_periods
        ads_res = supabase.table("dasha_periods")             .select("planet_or_sign,start_date,end_date,level,type,metadata")             .eq("chart_id", chart_id)             .eq("system", "vimsottari")             .order("start_date")             .execute()

        ads = [
            r for r in ads_res.data
            if r.get("level") == 2 or
               str(r.get("type","")).lower() in ("antardasha","ad","2")
        ]

        # Compute event windows
        events = map_all_events(birth_year, lagna, ads)

        # Build human-readable statements (NO astrological terms)
        statements = []

        # Statement 1: Foreign move (most verifiable, dramatic)
        fm = events.get("foreign_move")
        if fm and fm["start_year"] < 2020:
            statements.append({
                "id":      "foreign_move",
                "text":    f"Your chart shows a major relocation or foreign move around {fm['start_year']}-{fm['end_year']}.",
                "text_es": f"Tu carta muestra una reubicación importante alrededor de {fm['start_year']}-{fm['end_year']}.",
                "window":  f"{fm['start_year']}-{fm['end_year']}",
            })

        # Statement 2: Relationship transformation (divorce or marriage)
        div = events.get("divorce")
        mar = events.get("marriage")
        if div and div["start_year"] < 2024:
            statements.append({
                "id":      "relationship_change",
                "text":    f"Between {div['start_year']}-{div['end_year']} your chart shows a significant relationship transformation.",
                "text_es": f"Entre {div['start_year']}-{div['end_year']} tu carta muestra una transformación significativa en relaciones.",
                "window":  f"{div['start_year']}-{div['end_year']}",
            })
        elif mar and mar["start_year"] < 2020:
            statements.append({
                "id":      "relationship_change",
                "text":    f"Your chart shows a major commitment or partnership forming around {mar['start_year']}-{mar['end_year']}.",
                "text_es": f"Tu carta muestra un compromiso importante formándose alrededor de {mar['start_year']}-{mar['end_year']}.",
                "window":  f"{mar['start_year']}-{mar['end_year']}",
            })

        # Statement 3: Current period (almost always verifiable — builds immediate trust)
        # Get current MD from dasha_periods
        try:
            cur_md_res = supabase.table("dasha_periods")                 .select("planet_or_sign,start_date,end_date")                 .eq("chart_id", chart_id)                 .eq("system", "vimsottari")                 .lte("start_date", "2026-04-14")                 .gte("end_date", "2026-04-14")                 .execute()

            if cur_md_res.data:
                cur = cur_md_res.data[0]
                cur_start = str(cur.get("start_date",""))[:4]
                cur_end   = str(cur.get("end_date",""))[:4]
                cur_planet = cur.get("planet_or_sign","")

                # Map planet to human description of its energy
                PERIOD_DESCRIPTIONS = {
                    "Mars":    ("career pressure and income friction",
                                "presión profesional y fricción de ingresos"),
                    "Rahu":    ("rapid change and unconventional opportunities",
                                "cambio rápido y oportunidades poco convencionales"),
                    "Saturn":  ("discipline, delays, and structural rebuilding",
                                "disciplina, retrasos y reconstrucción estructural"),
                    "Jupiter": ("expansion, opportunity, and wisdom growth",
                                "expansión, oportunidades y crecimiento de sabiduría"),
                    "Moon":    ("emotional shifts and relationship changes",
                                "cambios emocionales y transformaciones en relaciones"),
                    "Sun":     ("identity clarification and authority building",
                                "clarificación de identidad y construcción de autoridad"),
                    "Venus":   ("creative income and partnership opportunities",
                                "ingresos creativos y oportunidades de asociación"),
                    "Mercury": ("communication, deals, and intellectual growth",
                                "comunicación, acuerdos y crecimiento intelectual"),
                    "Ketu":    ("spiritual seeking and letting go of old patterns",
                                "búsqueda espiritual y soltar patrones antiguos"),
                }

                desc_en, desc_es = PERIOD_DESCRIPTIONS.get(
                    cur_planet,
                    ("significant life changes", "cambios significativos de vida")
                )

                statements.append({
                    "id":      "current_period",
                    "text":    f"Since {cur_start} your chart shows {desc_en}.",
                    "text_es": f"Desde {cur_start} tu carta muestra {desc_es}.",
                    "window":  f"{cur_start}-present",
                })
        except Exception:
            pass

        return {
            "chart_id":   chart_id,
            "statements": statements[:3],  # max 3
            "birth_year": birth_year,
            "lagna":      lagna,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[signature] Error generating statements: {e}")
        return {"chart_id": chart_id, "statements": [], "error": str(e)}


@app.post("/api/v1/chart/signature/confirm")
async def confirm_signature(request: SignatureConfirmRequest):
    """
    Store user's signature confirmations.
    Used by onboarding to calibrate dasha accuracy.
    """
    try:
        # Read existing chart_data
        chart_res = supabase.table("charts")             .select("chart_data")             .eq("id", request.chart_id)             .single().execute()

        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")

        chart_data = chart_res.data.get("chart_data") or {}

        # Add signature confirmations
        chart_data["signature_confirmations"] = {
            **request.confirmations,
            "confirmed_at": "2026-04-14",
            "score": sum(1 for v in request.confirmations.values() if v == "confirmed"),
        }

        # Update chart
        supabase.table("charts").update({
            "chart_data": chart_data
        }).eq("id", request.chart_id).execute()

        score = chart_data["signature_confirmations"]["score"]
        calibration = (
            "fully_locked"  if score == 3 else
            "strong_signal" if score == 2 else
            "calibrating"   if score == 1 else
            "needs_data"
        )

        return {
            "confirmed":    True,
            "score":        score,
            "calibration":  calibration,
            "message":      f"{score}/3 statements confirmed — {calibration.replace('_', ' ').title()}",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[signature] Confirm error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# END SIGNATURE VERIFICATION
# ============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# TRANSIT — Real-time sky positions vs natal chart
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/transit/{chart_id}")
async def get_transit_report_endpoint(chart_id: str):
    """
    Returns current transit positions and how they relate to the natal chart.
    Includes: planet positions, top aspects, house activation, major transits.
    """
    try:
        from antar_engine.transit_engine import get_full_transit_report
        _row = supabase.table("charts").select("chart_data").eq("id", chart_id).single().execute()
        if not _row.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        _cd = _row.data.get("chart_data") or {}
        if isinstance(_cd, str):
            import json as _trjson
            try: _cd = _trjson.loads(_cd)
            except: _cd = {}
        _report = get_full_transit_report(_cd)
        return {"status": "ok", "chart_id": chart_id, **_report}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[transit] Error for chart {chart_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Transit computation failed: {str(e)}")

# ============================================================================
# END TRANSIT ENDPOINT
# ============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK LOOPS — Daily check-in, Prashna follow-up, Accuracy dashboard
# ══════════════════════════════════════════════════════════════════════════════

# ── Daily Check-in ───────────────────────────────────────────────────────────

@app.post("/api/v1/daily-feedback/{chart_id}")
async def submit_daily_feedback(chart_id: str, body: dict):
    """
    User rates how their day went. We compare to what we predicted.
    Body: { "date": "2026-04-16", "user_rating": 3, "user_note": "felt great" }
    user_rating: 1=bad, 2=neutral, 3=good
    """
    try:
        from datetime import datetime as _df_dt
        _date = body.get("date")
        _rating = body.get("user_rating")
        _note = body.get("user_note", "")

        if _rating not in (1, 2, 3):
            raise HTTPException(status_code=400, detail="user_rating must be 1, 2, or 3")
        if not _date:
            raise HTTPException(status_code=400, detail="date is required (YYYY-MM-DD)")

        # Look up predicted signal for that date from daily_wow_cache or generate
        _predicted_score = None
        _predicted_friction = None
        try:
            from antar_engine.daily_prediction_engine import generate_weekly_signals_sync
            _chart_row = supabase.table("charts").select(
                "chart_data, current_country"
            ).eq("id", chart_id).single().execute()
            if _chart_row.data:
                _raw_cd = _chart_row.data.get("chart_data") or {}
                if isinstance(_raw_cd, str):
                    import json as _dfjson
                    try: _raw_cd = _dfjson.loads(_raw_cd)
                    except: _raw_cd = {}
                _natal_moon = "Aries"
                _planets = _raw_cd.get("planets") or _raw_cd.get("planet_positions")
                if _planets:
                    for _p in _planets:
                        if isinstance(_p, dict):
                            _pn = _p.get("name", "").lower() or _p.get("planet", "").lower()
                            if _pn == "moon":
                                _natal_moon = _p.get("sign") or _p.get("rashi") or "Aries"
                                break
                _target_date = _df_dt.fromisoformat(_date)
                _signals = generate_weekly_signals_sync(natal_moon_sign=_natal_moon, start_date=_target_date)
                if _signals:
                    _today_sig = _signals[0]
                    _predicted_score = _today_sig.get("daily_score", 5)
                    _predicted_friction = _today_sig.get("is_friction_day", False)
        except Exception as _pse:
            print(f"[daily-feedback] Predicted signal lookup failed (non-fatal): {_pse}")

        # Save to daily_feedback table
        _row = {
            "chart_id": chart_id,
            "date": _date,
            "predicted_score": _predicted_score,
            "predicted_friction": _predicted_friction,
            "user_rating": _rating,
            "user_note": _note or None,
        }
        supabase.table("daily_feedback").upsert(
            _row, on_conflict="chart_id,date"
        ).execute()

        # Compute match
        _predicted_type = "friction" if _predicted_friction else "flow"
        _rating_label = {1: "bad", 2: "neutral", 3: "good"}[_rating]
        if _predicted_friction:
            _match = _rating == 1
        else:
            _match = _rating == 3
        _partial = _rating == 2

        # Compute accuracy stats
        _all = supabase.table("daily_feedback").select(
            "predicted_friction, user_rating"
        ).eq("chart_id", chart_id).not_.is_(
            "predicted_friction", "null"
        ).execute()
        _total = len(_all.data or [])
        _matched = 0
        for _r in (_all.data or []):
            _pf = _r.get("predicted_friction")
            _ur = _r.get("user_rating")
            if _pf and _ur == 1:
                _matched += 1
            elif not _pf and _ur == 3:
                _matched += 1
            elif _ur == 2:
                _matched += 0.5

        # Compute accuracy streak
        _recent = supabase.table("daily_feedback").select(
            "predicted_friction, user_rating, date"
        ).eq("chart_id", chart_id).not_.is_(
            "predicted_friction", "null"
        ).order("date", desc=True).limit(30).execute()
        _streak = 0
        for _r in (_recent.data or []):
            _pf = _r.get("predicted_friction")
            _ur = _r.get("user_rating")
            _is_match = (_pf and _ur == 1) or (not _pf and _ur == 3) or _ur == 2
            if _is_match:
                _streak += 1
            else:
                break

        return {
            "saved": True,
            "predicted_type": _predicted_type,
            "your_rating": _rating_label,
            "match": _match,
            "partial": _partial,
            "accuracy_streak": _streak,
            "total_rated": _total,
            "total_matched": int(_matched),
            "accuracy_pct": round(_matched / _total * 100) if _total > 0 else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[daily-feedback] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")


@app.get("/api/v1/daily-feedback/{chart_id}/stats")
async def get_daily_feedback_stats(chart_id: str):
    """Returns accuracy stats for daily signal predictions."""
    try:
        _all = supabase.table("daily_feedback").select(
            "date, predicted_friction, predicted_score, user_rating, user_note"
        ).eq("chart_id", chart_id).order("date", desc=True).execute()

        _rows = _all.data or []
        _total = 0
        _matched = 0.0
        _streak = 0
        _streak_counting = True
        _longest_streak = 0
        _current_streak = 0
        _last_7 = []

        for _r in _rows:
            _pf = _r.get("predicted_friction")
            _ur = _r.get("user_rating")
            if _pf is None:
                continue
            _total += 1
            _is_match = (_pf and _ur == 1) or (not _pf and _ur == 3)
            _is_partial = _ur == 2

            if _is_match:
                _matched += 1
                _current_streak += 1
            elif _is_partial:
                _matched += 0.5
                _current_streak += 1  # partial counts for streak
            else:
                _longest_streak = max(_longest_streak, _current_streak)
                _current_streak = 0

            if _streak_counting:
                if _is_match or _is_partial:
                    _streak += 1
                else:
                    _streak_counting = False

            if _total <= 7:
                _last_7.append({
                    "date": _r.get("date"),
                    "predicted": "friction" if _pf else "flow",
                    "actual": {1: "bad", 2: "neutral", 3: "good"}.get(_ur, "?"),
                    "match": _is_match,
                    "partial": _is_partial,
                })

        _longest_streak = max(_longest_streak, _current_streak)

        return {
            "chart_id": chart_id,
            "total_days_rated": _total,
            "total_matched": int(_matched),
            "accuracy_pct": round(_matched / _total * 100) if _total > 0 else 0,
            "current_streak": _streak,
            "longest_streak": _longest_streak,
            "last_7_days": _last_7,
        }

    except Exception as e:
        print(f"[daily-feedback-stats] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Prashna Follow-up ────────────────────────────────────────────────────────

@app.get("/api/v1/prashna-followup/{chart_id}")
async def get_prashna_followups(chart_id: str):
    """Returns prashna questions from 30+ days ago that haven't been followed up."""
    try:
        from datetime import datetime as _pf_dt, timedelta as _pf_td
        _30_ago = (_pf_dt.utcnow() - _pf_td(days=30)).isoformat()

        _pending = supabase.table("prashna_log").select(
            "id, question, verdict, score, label, created_at"
        ).eq("chart_id", chart_id).lt(
            "created_at", _30_ago
        ).is_("follow_up_rating", "null").order(
            "created_at", desc=True
        ).limit(3).execute()

        _followups = []
        for _r in (_pending.data or []):
            _created = _r.get("created_at", "")
            try:
                _days = (_pf_dt.utcnow() - _pf_dt.fromisoformat(
                    _created.replace("Z", "").split("+")[0]
                )).days
            except Exception:
                _days = 30
            _followups.append({
                "prashna_id": _r["id"],
                "question": _r.get("question", ""),
                "asked_date": _created[:10],
                "verdict": _r.get("verdict", ""),
                "score": _r.get("score", 0),
                "label": _r.get("label", ""),
                "days_ago": _days,
            })

        return {"chart_id": chart_id, "pending_followups": _followups}

    except Exception as e:
        print(f"[prashna-followup] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/prashna-followup/{chart_id}/{prashna_id}")
async def submit_prashna_followup(chart_id: str, prashna_id: str, body: dict):
    """
    User reports whether a prashna verdict came true.
    Body: { "outcome": "confirmed", "user_note": "took the job, going great" }
    outcome: "confirmed" | "partially" | "wrong" | "still_unclear"
    """
    try:
        from datetime import datetime as _sf_dt
        _outcome = body.get("outcome", "")
        _note = body.get("user_note", "")

        if _outcome not in ("confirmed", "partially", "wrong", "still_unclear"):
            raise HTTPException(
                status_code=400,
                detail="outcome must be: confirmed, partially, wrong, or still_unclear"
            )

        # Update prashna_log row
        _update = supabase.table("prashna_log").update({
            "follow_up_rating": _outcome,
            "follow_up_note": _note or None,
            "follow_up_at": _sf_dt.utcnow().isoformat(),
        }).eq("id", prashna_id).eq("chart_id", chart_id).execute()

        if not _update.data:
            raise HTTPException(status_code=404, detail="Prashna not found")

        _row = _update.data[0]
        _verdict = (_row.get("verdict") or "").upper()

        # Compute match: PROCEED + confirmed = match, WAIT/AVOID + wrong = match
        _is_match = False
        if _outcome == "confirmed" and _verdict in ("PROCEED", "STRONG PROCEED"):
            _is_match = True
        elif _outcome == "confirmed" and _verdict in ("WAIT", "AVOID", "STRONG AVOID"):
            _is_match = False
        elif _outcome == "wrong" and _verdict in ("WAIT", "AVOID", "STRONG AVOID"):
            _is_match = True
        elif _outcome == "wrong" and _verdict in ("PROCEED", "STRONG PROCEED"):
            _is_match = False
        elif _outcome == "partially":
            _is_match = None  # partial

        # Compute overall prashna accuracy
        _all_followed = supabase.table("prashna_log").select(
            "verdict, follow_up_rating"
        ).eq("chart_id", chart_id).not_.is_(
            "follow_up_rating", "null"
        ).neq("follow_up_rating", "still_unclear").execute()

        _total = len(_all_followed.data or [])
        _correct = 0
        for _r in (_all_followed.data or []):
            _v = (_r.get("verdict") or "").upper()
            _f = _r.get("follow_up_rating", "")
            if _f == "confirmed" and _v in ("PROCEED", "STRONG PROCEED"):
                _correct += 1
            elif _f == "wrong" and _v in ("WAIT", "AVOID", "STRONG AVOID"):
                _correct += 1
            elif _f == "partially":
                _correct += 0.5

        return {
            "saved": True,
            "prashna_id": prashna_id,
            "verdict": _verdict,
            "outcome": _outcome,
            "match": _is_match,
            "total_followed_up": _total,
            "total_correct": int(_correct),
            "accuracy_pct": round(_correct / _total * 100) if _total > 0 else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[prashna-followup] Submit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Accuracy Dashboard ───────────────────────────────────────────────────────

@app.get("/api/v1/accuracy/{chart_id}")
async def get_accuracy_dashboard(chart_id: str):
    """
    Master accuracy endpoint combining daily signal, prashna, and predictions.
    Returns the 'Antar Precision Score' for the user's profile.
    """
    try:
        from datetime import datetime as _ad_dt, timedelta as _ad_td

        # 1. Daily signal accuracy
        _daily = {"total_rated": 0, "accuracy_pct": 0, "current_streak": 0}
        try:
            _df_rows = supabase.table("daily_feedback").select(
                "predicted_friction, user_rating, date"
            ).eq("chart_id", chart_id).not_.is_(
                "predicted_friction", "null"
            ).order("date", desc=True).execute()
            _dt = len(_df_rows.data or [])
            _dm = 0.0
            _ds = 0
            _ds_counting = True
            for _r in (_df_rows.data or []):
                _pf = _r.get("predicted_friction")
                _ur = _r.get("user_rating")
                _is_m = (_pf and _ur == 1) or (not _pf and _ur == 3)
                _is_p = _ur == 2
                if _is_m: _dm += 1
                elif _is_p: _dm += 0.5
                if _ds_counting:
                    if _is_m or _is_p: _ds += 1
                    else: _ds_counting = False
            _daily = {
                "total_rated": _dt,
                "accuracy_pct": round(_dm / _dt * 100) if _dt > 0 else 0,
                "current_streak": _ds,
            }
        except Exception as _de:
            print(f"[accuracy] Daily stats error (non-fatal): {_de}")

        # 2. Prashna accuracy
        _prashna = {"total_asked": 0, "total_followed_up": 0, "accuracy_pct": 0, "pending_followups": 0}
        try:
            _pa = supabase.table("prashna_log").select(
                "verdict, follow_up_rating"
            ).eq("chart_id", chart_id).execute()
            _pa_total = len(_pa.data or [])
            _pa_followed = [r for r in (_pa.data or []) if r.get("follow_up_rating") and r.get("follow_up_rating") != "still_unclear"]
            _pa_pending = _pa_total - len([r for r in (_pa.data or []) if r.get("follow_up_rating")])
            _pa_correct = 0.0
            for _r in _pa_followed:
                _v = (_r.get("verdict") or "").upper()
                _f = _r.get("follow_up_rating", "")
                if _f == "confirmed" and _v in ("PROCEED", "STRONG PROCEED"): _pa_correct += 1
                elif _f == "wrong" and _v in ("WAIT", "AVOID", "STRONG AVOID"): _pa_correct += 1
                elif _f == "partially": _pa_correct += 0.5
            _prashna = {
                "total_asked": _pa_total,
                "total_followed_up": len(_pa_followed),
                "accuracy_pct": round(_pa_correct / len(_pa_followed) * 100) if _pa_followed else 0,
                "pending_followups": _pa_pending,
            }
        except Exception as _pe:
            print(f"[accuracy] Prashna stats error (non-fatal): {_pe}")

        # 3. Predictions accuracy
        _predictions = {"total_predictions": 0, "total_rated": 0, "accuracy_pct": 0, "unrated": 0}
        try:
            _pr = supabase.table("predictions").select(
                "accuracy_rating"
            ).eq("chart_id", chart_id).execute()
            _pr_total = len(_pr.data or [])
            _pr_rated = [r for r in (_pr.data or []) if r.get("accuracy_rating") is not None]
            _pr_accurate = sum(1 for r in _pr_rated if r.get("accuracy_rating") == 1)
            _predictions = {
                "total_predictions": _pr_total,
                "total_rated": len(_pr_rated),
                "accuracy_pct": round(_pr_accurate / len(_pr_rated) * 100) if _pr_rated else 0,
                "unrated": _pr_total - len(_pr_rated),
            }
        except Exception as _pre:
            print(f"[accuracy] Predictions stats error (non-fatal): {_pre}")

        # 4. Overall precision score (weighted average)
        _components = []
        if _daily["total_rated"] >= 5:
            _components.append((_daily["accuracy_pct"], 0.4))
        if _prashna["total_followed_up"] >= 5:
            _components.append((_prashna["accuracy_pct"], 0.3))
        if _predictions["total_rated"] >= 5:
            _components.append((_predictions["accuracy_pct"], 0.3))

        if _components:
            _total_weight = sum(w for _, w in _components)
            _overall = sum(v * w for v, w in _components) / _total_weight
        else:
            _overall = None  # not enough data

        return {
            "chart_id": chart_id,
            "daily_signal": _daily,
            "prashna": _prashna,
            "predictions": _predictions,
            "overall_precision": round(_overall) if _overall is not None else None,
            "precision_status": (
                "insufficient_data" if _overall is None
                else "excellent" if _overall >= 80
                else "good" if _overall >= 65
                else "developing"
            ),
        }

    except Exception as e:
        print(f"[accuracy] Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# END FEEDBACK LOOPS
# ============================================================================
@app.get("/api/v1/debug-context/{chart_id}")
async def debug_context(chart_id: str, question: str = "What is my career direction for 2026?"):
    from antar_engine.chart_context_builder_json import build_chart_context_json
    import asyncio
    chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
    if not chart_res.data:
        return {"error": "Chart not found"}
    chart_record = chart_res.data[0]
    ctx = await build_chart_context_json(
        chart_id=chart_id,
        chart_record=chart_record,
        question=question,
        language="en",
        supabase=supabase
    )
    return ctx

