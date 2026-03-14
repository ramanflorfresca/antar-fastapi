#Antar Backend API
# Updated: full DKP + i18n + predictions integration + conversation memory
# ─────────────────────────────────────────────────────────────────────

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Header
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

# ── Email via Resend ──────────────────────────────────────────────────────────
import httpx as _httpx

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


# ── Clients ──────────────────────────────────────────────────────────────────

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

SYSTEM_PROMPT = (
    "You are Antar, an astrological life coach. "
    "Answer based only on the data provided. "
    "Never invent planetary positions, dashas, transits, or life events. "
    "Never give medical, financial, or legal advice. "
    "Be concise, warm, and practical. "
    "Never use house numbers in your response — translate everything to energy language."
)

async def call_llm(
    prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, Optional[int]]:
    """
    Calls DeepSeek with the system prompt + optional conversation history
    (last 8 turns) + the current prompt as the final user message.

    history format: [{"role": "user"|"assistant", "content": "..."}]
    Only the last 8 items are used to stay within the token budget.
    """
    history = history or []
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history[-8:],
        {"role": "user", "content": prompt},
    ]
    try:
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.5,
            max_tokens=1200,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as e:
        print(f"LLM error: {e}")
        return "I'm sorry, I'm having trouble connecting to my intuition right now. Please try again later.", None

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

    # Guest rate limiting — 3 predictions per month
    if not user_id:
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

    # Guest rate limiting — 3 predictions per month
    if not user_id:
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

    # Country context
    country_code = chart_record.get("country_code")
    country_context = get_country_context(country_code) if country_code else ""

    # Timing
    timing_text = timing_engine.timing_insights(chart_data, dashas_response)

    # Nation insight
    nation_insight = ""
    if country_code:
        try:
            nation_insight = nation_engine.get_nation_insight(
                country_code, supabase, deepseek_client, language
            )
        except Exception as e:
            print(f"Nation insight error: {e}")

    # Concern detection
    concern = _detect_concern(request.question)

    # ── PATRA ──────────────────────────────────────────────────────
    user_profile = {
        "marital_status":   chart_record.get("marital_status", "unknown"),
        "children_status":  chart_record.get("children_status", "no_children_unsure"),
        "career_stage":     chart_record.get("career_stage", "mid_career"),
        "health_status":    chart_record.get("health_status", "excellent"),
        "financial_status": chart_record.get("financial_status", "stable"),
        "birth_country":    chart_record.get("country_code", ""),
        "current_country":  chart_record.get("country_code", ""),
        "countries_lived":  chart_record.get("countries_lived", []),
    }
    patra = build_patra_context(
        birth_date=chart_record["birth_date"],
        user_profile=user_profile,
        primary_concern=concern,
    )
    patra_context = patra_to_context_block(patra)

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

    for extra_block in [rarity_context, windows_context, chakra_context, arc_context,
                        lk_context, enrichment_context, sade_sati_context,
                        life_question_context]:
        if extra_block:
            prompt += f"\n\n{extra_block}"

    # ── LLM CALL — passes conversation history for multi-turn context ──
    prediction_text, tokens_used = await call_llm(
        prompt,
        history=request.conversation_history or [],
    )

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
        }).execute()
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
    gender:         Optional[str]  = None
    language:       Optional[str]  = "en"

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
    try: jai_dashas = _normalise_dashas(
            jaimini.calculate_chara_dasha_from_chart(chart_data, chart_data.get("birth_jd")))
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
        "birth_date":          request.birth_date,
        "birth_time":          request.birth_time,
        "latitude":            lat,
        "longitude":           lng,
        "gender":          getattr(request, "gender", "") or "",
        "current_city":    getattr(request, "current_city", "") or "",
        "current_country": getattr(request, "current_country", "") or "",
        "timezone_offset":     _offset,
        "country_code":        request.birth_country,
        "chart_data":          chart_data,
        "language_preference": request.language or "en",
        "patra_complete":      False,
    }
    try:
        supabase.table("charts").insert(chart_row).execute()
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
            dasha_rows.append({
                "chart_id":       chart_id,
                "system":         system,
                "type":           level_name,
                "planet_or_sign": lord,
                "start_date":     sd,
                "end_date":       ed,
                "duration_years": p.get("duration_years", 0),
                "sequence":       i,
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

    lk_data = None
    if user_id:
        try:
            lk_varshphal = lal_kitab_gen.generate_varshphal(
                user_id=user_id,
                chart_id=chart_id,
                store=True,
            )
            lk_data = {
                "age":                lk_varshphal["age"],
                "table_age":          lk_varshphal["table_age"],
                "placements":         lk_varshphal["placements"],
                "is_special_cycle":   lk_varshphal["is_special_cycle"],
                "cycle_significance": lk_varshphal["cycle_significance"],
                "predictions":        lk_varshphal["predictions"],
                "remedies_summary":   lk_varshphal["remedies"],
            }
        except Exception as e:
            print(f"Lal Kitab varshphal error (non-fatal): {e}")

    planets = chart_data["planets"]
    ak, amk = _ak_amk(planets)

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
        "current_country":  chart_record.get("country_code", ""),
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
        "current_country":  chart_record.get("country_code", ""),
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
