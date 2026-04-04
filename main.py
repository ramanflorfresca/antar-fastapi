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
        build_and_store_jaimini,
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
    timezone_offset: float = Field(..., example=5.5)
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
    timezone_offset: float = Field(..., example=5.5)
    timezone_name:   Optional[str] = Field(None, example="Asia/Kolkata")
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

    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1200,
            temperature=0.35,
            system=system,
            messages=messages,
        )
        text = response.content[0].text.strip()
        tokens = response.usage.output_tokens
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

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Chart ─────────────────────────────────────────────────────────────────────

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
- Frame it as: \"Two lenses, same question \u2014 here's what each one sees.\"

IF your birth chart analysis AGREES with the Oracle verdict:
- Note the convergence: \"Both your birth chart and the Oracle point the same direction.\"
- This increases confidence. Say so.

DO NOT ignore the Oracle reading. DO NOT pretend it doesn't exist.
Acknowledge it explicitly and explain the difference.
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
"""


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

    # Dashas
    dashas_response = get_dashas_for_chart(request.chart_id)

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

        # Nation astrological insight (existing — keep as fallback)
        try:
            nation_insight = nation_engine.get_nation_insight(
                country_code, supabase, deepseek_client, language
            )
        except Exception as e:
            print(f"[predict] Nation insight error (non-fatal): {type(e).__name__}: {e}")
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
        _tr_data = calculate_current_transits(chart_data)
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
        )

        # --- LAYER 2.5: JAIMINI CHARA DASHA ---
        if "id" not in chart_data:
            chart_data["id"] = request.chart_id
        try:
            _jaimini_block = format_jaimini_context_from_stored(chart_data)
            if _jaimini_block:
                _full_context += _jaimini_block
            _concern = getattr(request, 'concern', '') or getattr(request, 'question', '') or ''
            _jaimini_conv = score_jaimini_convergence(chart_data, _concern)
            if _jaimini_conv:
                _full_context += "\n" + _jaimini_conv + "\n"
        except Exception as _je:
            print(f"Jaimini context failed (non-blocking): {_je}")

        # --- LAYER 3.5: JAIMINI → LK BRIDGE ---
        try:
            _bridge_block = format_bridge_from_stored(chart_data)
            if _bridge_block:
                _full_context += _bridge_block
        except Exception as _be:
            print(f"Bridge context failed (non-blocking): {_be}")
        print(f"[predict] Full context: {len(_full_context)} chars")
    except Exception as _ctx_e:
        import traceback
        print(f"[predict] Context build ERROR concern={concern}: {_ctx_e}")
        print(f"[predict] dashas_response type={type(dashas_response)} len={len(dashas_response) if hasattr(dashas_response,'__len__') else 'N/A'}")
        if isinstance(dashas_response, list) and dashas_response:
            print(f"[predict] first dasha row keys: {list(dashas_response[0].keys()) if isinstance(dashas_response[0],dict) else type(dashas_response[0])}")
        print(f"[predict] Traceback: {traceback.format_exc()}")

    if _full_context and len(_full_context) > 500:
        print(f"[predict] Using master context ({len(_full_context)} chars) concern={concern}")
        prompt = _full_context + f"\n\nQUESTION: {request.question}\nCONCERN: {concern}\n\nAnswer the question directly, referencing specific planets, houses, yogas, and dasha periods from the context above. No generic advice."
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
        )

    for _extra_name, _extra_block in [
        ("rarity",       rarity_context),
        ("windows",      windows_context),
        ("chakra",       chakra_context),
        ("arc",          arc_context),
        ("lk",           lk_context),
        ("enrichment",   enrichment_context),
        ("sade_sati",    sade_sati_context),
        ("life_question",life_question_context),
        ("e2_contradiction", _contradiction_block if '_contradiction_block' in dir() else ""),
    ]:
        try:
            if _extra_block:
                prompt += f"\n\n{_extra_block}"
        except Exception as _eb_e:
            print(f"[predict] extra_block {_extra_name} error: {_eb_e}")

    # ── LLM CALL — passes conversation history for multi-turn context ──
    # Use different system prompt for master context vs template
    # ── C3 + C4: Append memory, diagnostic, and common sense to prompt ──
    _memory_block     = (_memory or {}).get("memory_block", "")
    _diagnostic_block = (_memory or {}).get("diagnostic_block", "")

    for _block in [_memory_block, _diagnostic_block, _cs_block]:
        if not _block:
            continue
        prompt += f"\n\n{_block}"
    # ── end C3+C4 injection ───────────────────────────────────────


    # ── Domain Audit Rules (Sprint D) ────────────────────────────
    _domain_rules = DOMAIN_AUDIT_RULES.get(concern, DOMAIN_AUDIT_RULES.get("general", ""))
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

        _master_system = _domain_system if _domain_system else (
            "You are Antar — a precise Vedic astrology AI. "
            "Answer directly and specifically using the data provided. "
            "Reference specific planets, houses, yogas, and timing. "
            "Lead with the actual answer in the first sentence. "
            "Never start responses with template headers like 'YOUR SIGNAL RIGHT NOW'."
        )
        # --- Sprint L: Language injection ---
        from language_utils import build_language_instruction, resolve_language
        _lang = resolve_language({"language": getattr(request, "language", None)}, chart_record)
        _lang_block = build_language_instruction(_lang)
        if _lang_block:
            _master_system = _lang_block + _master_system
            print(f"[predict] Language injection: {_lang}")
        # --- end Sprint L ---
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
                "lagna":   chart_record.get("lagna_sign"),
                "dasha":   chart_record.get("current_dasha"),
                "age":     getattr(patra, "age", None),
                "country": chart_record.get("birth_country"),
                "concern": concern,
            },
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
        plain_summary=_pe.get("plain_summary") if _pe else None,
        action_item=_pe.get("action_item") if _pe else None,
        signal_line=_pe.get("signal_line") if _pe else None,
        timing_window=_pe.get("timing_window") if _pe else None,
        all_domains=_pe.get("all_domains") if _pe else [],
        signal_confidence=_pe.get("confidence") if _pe else None,
        why_this=_pe.get("why_this") if _pe else None,
        bridge_practice_note=_pe.get("bridge_practice_note") if _pe else None,
        contradiction_detected=_contradiction_detected if '_contradiction_detected' in dir() else False,
        oracle_context=_oracle_context if '_oracle_context' in dir() else None,
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
            .eq("user_id", user_id).order("event_date", desc=True).limit(20).execute()
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
                mantra=rem.get("mantra_simple", ""),
                beej_mantra=rem.get("mantra_beej", ""),
                recommended_day=rem.get("fasting_day", ""),
                count=rem.get("count", 108),
                purpose=rem.get("special_instructions", ""),
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

class ChartCreateRequest(BaseModel):
    birth_date:     str
    birth_time:     str
    birth_city:     str
    birth_country:  str
    birth_lat:      Optional[float] = None
    birth_lng:      Optional[float] = None
    birth_timezone: Optional[str]  = None
    user_id:        Optional[str]  = None
    name:           Optional[str]  = None
    first_name:     Optional[str]  = None
    gender:         Optional[str]  = None
    language:       Optional[str]  = "en"
    # Residence — where the person LIVES NOW (not birth location)
    # Used for DKP, foreign signal framing, astrocartography
    current_city:    Optional[str]  = None   # city of current residence
    current_country: Optional[str]  = None   # ISO country code of residence
                                              # defaults to birth_country if not provided

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

@app.post("/api/v1/chart/create", response_model=ChartCreateResponse)
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

    if request.birth_lat and request.birth_lng:
        lat, lng = request.birth_lat, request.birth_lng
        timezone = request.birth_timezone or "UTC"
    else:
        lat, lng, timezone = await _geocode_city(request.birth_city, request.birth_country)

    try:
        chart_data = chart_module.calculate_chart(
            birth_date=request.birth_date,
            birth_time=request.birth_time,
            lat=lat, lng=lng,
            timezone=timezone,
            ayanamsa="lahiri",
        )
    except Exception as e:
        raise HTTPException(500, f"Chart calculation failed: {e}")

    def _normalise_dashas(raw) -> list:
        """
        Dasha modules return {mahadashas:[{lord, start_date, end_date, ...}], antardashas:[...]}
        Normalise to flat list with keys predictions.py / get_dashas_for_chart() expect:
        {lord_or_sign, start, end, duration_years, level, planet_or_sign}
        """
        if isinstance(raw, list):
            return raw   # already flat
        if not isinstance(raw, dict):
            return []
        flat = []
        for p in raw.get("mahadashas", []):
            sd = str(p.get("start_date", "") or "")[:10]
            ed = str(p.get("end_date",   "") or "")[:10]
            flat.append({
                "lord_or_sign":   p.get("lord", ""),
                "planet_or_sign": p.get("lord", ""),
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
            flat.append({
                "lord_or_sign":   p.get("lord", ""),
                "planet_or_sign": p.get("lord", ""),
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
    try:
        import pytz as _pytz
        from datetime import datetime as _dt
        _tz = _pytz.timezone(timezone)
        _offset = _tz.utcoffset(_dt.now()).total_seconds() / 3600
    except Exception:
        _offset = 0.0

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
        "current_country": getattr(request, "current_country", "") or request.birth_country or "",
        "timezone_offset":     _offset,
        "country_code":        request.birth_country,
        "birth_city":      request.birth_city,
        "birth_country":   request.birth_country,
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
        "language_preference": request.language or "en",
        "patra_complete":      False,
    }
    try:
        supabase.table("charts").insert(chart_row).execute()

        # --- Jaimini v2: Compute and store Chara Dasha ---
        try:
            _lagna_idx_j = constants.SIGNS.index(lagna_sign) if isinstance(lagna_sign, str) else int(lagna_sign)
            _planets_for_jaimini = {}
            for pname, pdata in chart_data.get("planets", {}).items():
                if isinstance(pdata, dict):
                    _planets_for_jaimini[pname] = pdata
            _d9_data = chart_data.get("divisional_charts", {}).get("D9", {}).get("planets", {})
            if not _d9_data:
                _d9_data = chart_data.get("d9_planets", {})
            build_and_store_jaimini(
                chart_id=chart_id,
                lagna_sign=_lagna_idx_j,
                planets_dict=_planets_for_jaimini,
                d9_planets_dict=_d9_data if _d9_data else _planets_for_jaimini,
                birth_date_str=str(birth_date)[:10],
                supabase_client=supabase,
            )
        except Exception as _je:
            print(f"Jaimini v2 store failed (non-blocking): {_je}")

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

    return ChartCreateResponse(
        chart_id=chart_id,
        lagna=chart_data["lagna"]["sign"],
        lagna_degree=chart_data["lagna"].get("degree", 0),
        moon_sign=planets.get("Moon",{}).get("sign",""),
        sun_sign=planets.get("Sun",{}).get("sign",""),
        atmakaraka=ak, amatyakaraka=amk,
        current_dasha=_current_dasha_str(dashas_combined),
        dasha_count=len(dasha_rows),
        birth_city=request.birth_city,
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

    top_cities = get_best_cities_for_concern(
        concern=request.concern,
        chart_data=chart_data,
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

    try:
        supabase.table("astrocartography_readings").upsert({
            "chart_id":   request.chart_id,
            "concern":    request.concern,
            "top_cities": top_cities,
            "narrative":  narrative,
            "created_at": "now()",
        }).execute()
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


class CompatibilityContinueRequest(BaseModel):
    session_id:      str
    layer:           int
    startup_context: Optional[dict] = None
    product_context: Optional[str]  = None


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
        # Try internal geocoder, fall back to Nominatim for unknown cities
        try:
            _gc = await _geocode_city(city_b, country_b)
            if isinstance(_gc, (tuple, list)) and len(_gc) >= 2:
                coords_b = {"lat": _gc[0], "lng": _gc[1], "timezone": _gc[2] if len(_gc) > 2 else "UTC"}
            elif isinstance(_gc, dict) and _gc.get("lat"):
                coords_b = _gc
            else:
                coords_b = None
        except Exception:
            coords_b = None
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
                        "timezone": "UTC",
                    }
                    # Get timezone from coords
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
        from antar_engine.chart import calculate_chart
        chart_b   = calculate_chart(
            birth_date=request.birth_date_b,
            birth_time=birth_time_b,
            lat=coords_b["lat"], lng=coords_b["lng"],
            timezone=coords_b.get("timezone","UTC"),
        )
        chart_id_b = str(_uuid.uuid4())
        supabase.table("charts").insert({
            "id": chart_id_b,
            "birth_date": request.birth_date_b,
            "birth_time": birth_time_b,
            "birth_city": city_b,
            "birth_country": country_b,
            "latitude": coords_b["lat"],
            "longitude": coords_b["lng"],
            "timezone": coords_b.get("timezone","UTC"),
            "timezone_offset": 0.0,
            "timezone_offset": 0.0,
            "timezone_offset": 0.0,
            "name": request.name_b,
            "chart_data": chart_b,
            "lagna_sign": chart_b.get("lagna",{}).get("sign",""),
            "lagna_degree": chart_b.get("lagna",{}).get("degree",0),
            "moon_sign": chart_b.get("planets",{}).get("Moon",{}).get("sign",""),
            "moon_nakshatra": chart_b.get("planets",{}).get("Moon",{}).get("nakshatra",""),
            "sun_sign": chart_b.get("planets",{}).get("Sun",{}).get("sign",""),
        }).execute()
        dashas_b = {}

    brief_a = build_person_brief(name_a, chart_a, dashas_a, birth_a, has_time_a)
    brief_b = build_person_brief(request.name_b, chart_b, dashas_b,
                                  birth_b if request.chart_id_b else request.birth_date_b,
                                  has_time_b)

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

    return {
        "session_id":     session_id,
        "layer":          1,
        "chart_id_b":     chart_id_b,
        "analysis":       layer1,
        "has_time_a":     has_time_a,
        "has_time_b":     has_time_b,
        "confidence_pct": 90 if (has_time_a and has_time_b) else 65,
        "next_question":  "Would you like to analyze startup or business alignment?",
        "can_continue":   True,
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
            .select("chart_data, jaimini_data, lal_kitab_data, first_name, current_country, lagna_sign, latitude, longitude") \
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
        current_country = chart_data.get("current_country", "US")

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
        raise HTTPException(500, f"Daily signal error: {e}")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

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

@app.get("/api/v1/dashboard/{chart_id}")
async def get_dashboard(chart_id: str):
    """
    Single endpoint that returns all dashboard data.
    Powers the home page with all 6 sections.
    Parallel fetches for speed.
    """
    try:
        # ── Wire 5: Inject jaimini + lal_kitab into dashboard response ──
        _w5_result = await _get_dashboard_inner(chart_id)
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

async def _get_dashboard_inner(chart_id: str):
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

        result = await generate_welcome_signal_v2(
                chart_data=_chart_row,
                birth_date=_chart_row.get("birth_date"),
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

class _PracticeCompleteReq(_PracticeBaseModel):
    practice_id: str
    user_note: str = None

@app.get("/api/v1/practices/{chart_id}/schedule")
async def get_practice_schedule_endpoint(chart_id: str, refresh: bool = False):
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
                return {"status": "ok", "source": "cache", "schedule": _sched}
        _chart = supabase.table("charts").select("chart_data, jaimini_data, lal_kitab_data, current_country, birth_date").eq("id", chart_id).single().execute()
        if not _chart.data:
            return {"status": "error", "message": "Chart not found"}
        _c = _chart.data
        _streak = await _practice_get_streak(chart_id)
        _sched = generate_practice_schedule(
            chart_data=_safe_jsonb(_c.get("chart_data")),
            jaimini_data=_safe_jsonb(_c.get("jaimini_data")),
            lal_kitab_data=_safe_jsonb(_c.get("lal_kitab_data")),
            current_country=_c.get("current_country", "US"),
            birth_date=_c.get("birth_date"),
            streak_data=_streak,
        )
        try:
            supabase.table("practice_schedule_cache").upsert({"chart_id": chart_id, "week_of": _week_of.isoformat(), "cache_key": _sched.get("cache_key", ""), "schedule_data": _sched}, on_conflict="chart_id,week_of").execute()
        except Exception:
            pass
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
