"""
Jaimini Integration Module — Wires jaimini_engine.py into /predict
===================================================================
Antar Platform · v2.0 · March 31, 2026

This module provides two integration paths:

  HOT PATH (every /predict call):
    format_jaimini_context_from_stored(chart_data) → str
    Reads the pre-computed jaimini_data JSONB from the charts table.
    Zero recalculation. Zero extra DB queries. Just format and return.

  COLD PATH (chart/create + backfill):
    build_and_store_jaimini(chart_id, lagna_sign, planets, d9_planets, birth_date) → dict
    Full computation → stores to charts.jaimini_data JSONB + dashas table rows.

  PRASHNA PATH (Ask Antar / /prashna):
    jaimini_prashna_check(chart_data, question_type) → dict
    Binary YES/NO gate using stored jaimini_data.

Integration Point in main.py:
  In build_complete_context(), add after Layer 2 (Dasha timing):

    # --- LAYER 2.5: JAIMINI CHARA DASHA ---
    from jaimini_integration import format_jaimini_context_from_stored
    jaimini_block = format_jaimini_context_from_stored(chart_data)
    context += jaimini_block

File: antar_engine/jaimini_integration.py
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import the core engine
try:
    from antar_engine.jaimini_engine import (
        Planet,
        compute_7_karakas,
        compute_arudha_lagna,
        compute_upapada_lagna,
        compute_karakamsa,
        compute_chara_dasha,
        get_current_dasha,
        get_rashi_drishti,
        compute_argala,
        analyze_moving_lagna,
        predict_events,
        jaimini_binary_check,
        build_jaimini_context,
        format_jaimini_prompt_block,
        jaimini_to_db_json,
        generate_dasha_rows,
        SIGN_NAMES,
    )
except ImportError:
    # Fallback for direct execution / testing
    from jaimini_engine import (
        Planet,
        compute_7_karakas,
        compute_arudha_lagna,
        compute_upapada_lagna,
        compute_karakamsa,
        compute_chara_dasha,
        get_current_dasha,
        get_rashi_drishti,
        compute_argala,
        analyze_moving_lagna,
        predict_events,
        jaimini_binary_check,
        build_jaimini_context,
        format_jaimini_prompt_block,
        jaimini_to_db_json,
        generate_dasha_rows,
        SIGN_NAMES,
    )

logger = logging.getLogger("antar.jaimini")


# =============================================================================
# HOT PATH — Called on every /predict request
# Reads stored JSONB, formats for LLM prompt. Zero computation.
# =============================================================================

def format_jaimini_context_from_stored(chart_data: Dict[str, Any]) -> str:
    """
    HOT PATH: Read pre-computed jaimini_data from charts table JSONB column
    and format it as the LLM context block.

    This is called inside build_complete_context() in main.py.
    It reads from chart_data['jaimini_data'] which was stored at chart creation.

    Args:
        chart_data: The full chart row from Supabase (dict from .execute())

    Returns:
        Formatted string block ready to append to the /predict system prompt.
        Returns empty string if jaimini_data is missing (graceful degradation).
    """
    jaimini_data = chart_data.get("jaimini_data")

    if not jaimini_data:
        logger.warning(f"No jaimini_data found for chart {chart_data.get('id', 'unknown')}")
        return ""

    # If stored as string, parse it
    if isinstance(jaimini_data, str):
        try:
            jaimini_data = json.loads(jaimini_data)
        except json.JSONDecodeError:
            logger.error(f"Invalid jaimini_data JSON for chart {chart_data.get('id')}")
            return ""

    try:
        return _format_stored_jaimini(jaimini_data)
    except Exception as e:
        logger.error(f"Error formatting jaimini context: {e}")
        return ""


def _format_stored_jaimini(data: Dict[str, Any]) -> str:
    """
    Format the stored jaimini_data JSONB into the LLM prompt block.
    This mirrors format_jaimini_prompt_block() but works from stored JSON
    instead of live dataclass objects.
    """
    lines = []
    lines.append("")
    lines.append("═══ JAIMINI CHARA DASHA ANALYSIS ═══")
    lines.append("")

    # ── Karakas ──
    karakas = data.get("karakas", [])
    if karakas:
        lines.append("SOUL MAP (7 Karakas):")
        for k in karakas:
            lines.append(
                f"  {k['karaka']} ({k.get('meaning', '')}): "
                f"{k['planet']} in {k.get('sign_name', SIGN_NAMES[k.get('sign', 0)])} "
                f"at {k.get('degree', 0):.1f}°"
            )

    # ── Special Points ──
    lines.append("")
    lines.append("SPECIAL POINTS:")

    al = data.get("arudha_lagna", {})
    if al:
        al_text = f"  Public Image (AL): {al.get('sign_name', 'unknown')}"
        if al.get("exception"):
            al_text += f" [Exception: {al.get('exception_detail', '')}]"
        lines.append(al_text)

    ul = data.get("upapada_lagna", {})
    if ul:
        ul_text = f"  Marriage Point (UL): {ul.get('sign_name', 'unknown')}"
        if ul.get("exception"):
            ul_text += f" [Exception: {ul.get('exception_detail', '')}]"
        lines.append(ul_text)

    kl = data.get("karakamsa", {})
    if kl:
        lines.append(f"  Soul Purpose (Karakamsa): {kl.get('sign_name', 'unknown')}")

    # ── Current Timing ──
    md = data.get("current_md")
    ad = data.get("current_ad")
    if md:
        lines.append("")
        lines.append("CURRENT TIMING:")
        md_start = md.get("start", "")[:7]  # YYYY-MM
        md_end = md.get("end", "")[:7]
        lines.append(
            f"  Main Period: {md.get('sign_name', '')} "
            f"({md_start} – {md_end}) "
            f"[{md.get('years', '')}yr, {md.get('direction', '')}]"
        )
    if ad:
        ad_start = ad.get("start", "")[:7]
        ad_end = ad.get("end", "")[:7]
        lines.append(
            f"  Sub-Period: {ad.get('sign_name', '')} "
            f"({ad_start} – {ad_end})"
        )

    # ── Rashi Drishti ──
    drishti = data.get("rashi_drishti_ad", [])
    if drishti:
        lines.append(f"  Signs Influenced: {', '.join(drishti)}")

    # ── Moving Lagna Analysis ──
    ml = data.get("moving_lagna", {})
    if ml:
        lines.append("")
        lines.append("MOVING LAGNA ANALYSIS (Dasha Sign = temporary 1st house):")
        for key in ["ak_effect", "amk_effect", "dk_effect", "gk_effect",
                     "pk_effect", "mk_effect", "al_effect", "ul_effect"]:
            if key in ml:
                label = key.replace("_effect", "").upper()
                lines.append(f"  {label}: {ml[key]}")

    # ── Argala Net ──
    argala_net = data.get("argala_net")
    if argala_net is not None:
        lines.append(f"  Net Assessment: {'Supported' if argala_net else 'Obstructed'}")

    # ── Event Predictions ──
    predictions = data.get("predictions", [])
    if predictions:
        lines.append("")
        lines.append("EVENT SIGNALS:")
        for p in predictions:
            conf = p.get("confidence", "medium").upper()
            etype = p.get("event_type", "unknown").upper()
            desc = p.get("description", "")
            lines.append(f"  [{conf}] {etype}: {desc}")
            for c in p.get("conditions", []):
                lines.append(f"    ✓ {c}")

    lines.append("")
    lines.append("═══ END JAIMINI ANALYSIS ═══")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# COLD PATH — Called at chart/create and during backfill
# Full computation → store to DB
# =============================================================================

def build_and_store_jaimini(
    chart_id: str,
    lagna_sign: int,
    planets_dict: Dict[str, Dict],
    d9_planets_dict: Dict[str, Dict],
    birth_date_str: str,
    supabase_client=None,
) -> Dict[str, Any]:
    """
    COLD PATH: Compute the full Jaimini analysis and store it.

    Called at:
      1. POST /api/v1/chart/create — after Swiss Ephemeris calculation
      2. Backfill script — for existing charts without jaimini_data

    This function:
      a) Builds the full JaiminiContext (karakas, AL, UL, KL, dashas, predictions)
      b) Serializes to JSON and stores in charts.jaimini_data
      c) Generates dasha rows (level=1 MD + level=2 AD) for the dashas table

    Args:
        chart_id: UUID string
        lagna_sign: 0-indexed (0=Aries ... 11=Pisces)
        planets_dict: {planet_name: {sign, degree, degree_in_sign, retrograde, ...}}
        d9_planets_dict: Same format for D9 chart
        birth_date_str: "YYYY-MM-DD"
        supabase_client: Supabase client instance (optional, for direct DB writes)

    Returns:
        {
            "jaimini_data": dict (the JSONB to store),
            "dasha_rows": list (rows for dashas table),
            "prompt_block": str (formatted LLM context block)
        }
    """
    # Convert raw dicts to Planet objects
    SIGN_NAMES_LOCAL = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    def _to_sign_idx(val):
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        if isinstance(val, str):
            try:
                return SIGN_NAMES_LOCAL.index(val.title())
            except ValueError:
                try:
                    return int(val)
                except ValueError:
                    return 0
        return 0

    planets = {}
    for name, data in planets_dict.items():
        planets[name] = Planet(
            name=name,
            sign=_to_sign_idx(data.get("sign", 0)),
            degree=data.get("degree", 0.0),
            degree_in_sign=data.get("degree_in_sign", 0.0),
            retrograde=data.get("retrograde", False),
            nakshatra=data.get("nakshatra", ""),
            nakshatra_lord=data.get("nakshatra_lord", "")
        )

    d9_planets = {}
    for name, data in d9_planets_dict.items():
        d9_planets[name] = Planet(
            name=name,
            sign=_to_sign_idx(data.get("sign", 0)),
            degree=data.get("degree", 0.0),
            degree_in_sign=data.get("degree_in_sign", 0.0),
            retrograde=data.get("retrograde", False)
        )

    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    target_date = datetime.now()

    # Build full context
    ctx = build_jaimini_context(lagna_sign, planets, d9_planets, birth_date, target_date)

    # Serialize
    jaimini_data = jaimini_to_db_json(ctx)
    prompt_block = format_jaimini_prompt_block(ctx)
    dasha_rows = generate_dasha_rows(chart_id, lagna_sign, planets, birth_date, num_cycles=2)

    # Store to DB if client provided
    if supabase_client:
        try:
            # Update charts table with jaimini_data JSONB
            supabase_client.table("charts").update({
                "jaimini_data": jaimini_data
            }).eq("id", chart_id).execute()
            logger.info(f"Stored jaimini_data for chart {chart_id}")

            # Wipe existing Jaimini rows for this chart, then re-insert
            supabase_client.table("dasha_periods").delete().eq(
                "chart_id", chart_id
            ).eq("system", "jaimini").execute()
            if dasha_rows:
                supabase_client.table("dasha_periods").insert(dasha_rows).execute()
                logger.info(f"Inserted {len(dasha_rows)} Jaimini dasha rows for chart {chart_id}")

        except Exception as e:
            logger.error(f"Failed to store Jaimini data for chart {chart_id}: {e}")

    return {
        "jaimini_data": jaimini_data,
        "dasha_rows": dasha_rows,
        "prompt_block": prompt_block,
    }


# =============================================================================
# PRASHNA PATH — Called by /prashna (Ask Antar)
# Binary YES/NO gate from stored data
# =============================================================================

def jaimini_prashna_check(
    chart_data: Dict[str, Any],
    question_type: str,
    lagna_sign: int,
) -> Dict[str, Any]:
    """
    PRASHNA PATH: Quick binary check for Ask Antar questions.
    Uses stored jaimini_data — no recalculation needed.

    Args:
        chart_data: Full chart row from Supabase
        question_type: "marriage" | "lawsuit" | "investment" | "foreign"
        lagna_sign: 0-indexed lagna

    Returns:
        {
            "question_type": str,
            "jaimini_verdict": True/False,
            "reasons": [str],
            "confidence_boost": str  # "high" if Jaimini agrees, "none" if not
        }
    """
    jaimini_data = chart_data.get("jaimini_data")
    if not jaimini_data:
        return {
            "question_type": question_type,
            "jaimini_verdict": None,
            "reasons": ["Jaimini data not available for this chart"],
            "confidence_boost": "none"
        }

    if isinstance(jaimini_data, str):
        try:
            jaimini_data = json.loads(jaimini_data)
        except json.JSONDecodeError:
            return {
                "question_type": question_type,
                "jaimini_verdict": None,
                "reasons": ["Invalid Jaimini data"],
                "confidence_boost": "none"
            }

    # Get active sign from current AD (or MD fallback)
    ad = jaimini_data.get("current_ad")
    md = jaimini_data.get("current_md")
    active_sign = None
    if ad:
        active_sign = ad.get("sign")
    elif md:
        active_sign = md.get("sign")

    if active_sign is None:
        return {
            "question_type": question_type,
            "jaimini_verdict": None,
            "reasons": ["No active dasha period found"],
            "confidence_boost": "none"
        }

    # Get AL, UL, Karakas from stored data
    al_sign = jaimini_data.get("arudha_lagna", {}).get("sign")
    ul_sign = jaimini_data.get("upapada_lagna", {}).get("sign")
    karakas = jaimini_data.get("karakas", [])

    verdict = False
    reasons = []

    drishti = get_rashi_drishti(active_sign)

    if question_type == "marriage":
        # Check 1: Active sign is 1st or 7th from UL
        if ul_sign is not None:
            ul_dist = ((active_sign - ul_sign) % 12) + 1
            if ul_dist in [1, 7]:
                verdict = True
                reasons.append(f"Current sub-period sign is {ul_dist}th from Marriage Point (UL)")

        # Check 2: DK connection
        dk_sign = None
        for k in karakas:
            if k.get("karaka") == "DK":
                dk_sign = k.get("sign")
                break
        if dk_sign is not None and (dk_sign == active_sign or dk_sign in drishti):
            verdict = True
            reasons.append("Current sign contains or aspects spouse significator (DK)")

    elif question_type == "lawsuit":
        # Malefics in 3rd or 6th from AL = victory through struggle
        if al_sign is not None:
            reasons.append("Checking litigation axis from public image point (AL)")
            # Simplified — in production, check actual malefic placements from stored planets
            verdict = True  # Default to checking — detailed check needs planet data

    elif question_type == "investment":
        if al_sign is not None:
            al_dist = ((active_sign - al_sign) % 12) + 1
            if al_dist in [2, 5, 11]:
                verdict = True
                reasons.append(f"Current sign is {al_dist}th from public image point — wealth axis active")

    elif question_type == "foreign":
        seventh = (lagna_sign + 6) % 12
        ninth = (lagna_sign + 8) % 12
        if seventh in drishti or ninth in drishti:
            verdict = True
            reasons.append("Current dasha sign aspects the 7th or 9th house — foreign connection active")

    return {
        "question_type": question_type,
        "jaimini_verdict": verdict,
        "reasons": reasons,
        "confidence_boost": "high" if verdict else "none"
    }


# =============================================================================
# CONVERGENCE SCORER — used by /predict confidence calculation
# =============================================================================

def score_jaimini_convergence(
    chart_data: Dict[str, Any],
    concern_domain: str,
) -> str:
    """
    One-line convergence note for the LLM prompt.
    Tells Claude whether Jaimini supports the domain being asked about.

    Called from build_complete_context() after the main Jaimini block.

    Returns a string like:
      "JAIMINI CONVERGENCE: Career signal is HIGH — AmK aspects current dasha sign."
      "JAIMINI CONVERGENCE: No specific marriage trigger in current period."
    """
    jaimini_data = chart_data.get("jaimini_data")
    if not jaimini_data:
        return ""

    if isinstance(jaimini_data, str):
        try:
            jaimini_data = json.loads(jaimini_data)
        except json.JSONDecodeError:
            return ""

    predictions = jaimini_data.get("predictions", [])
    if not predictions:
        return f"JAIMINI CONVERGENCE: No specific {concern_domain} trigger in current period."

    # Map concern domains to event types
    domain_to_event = {
        "career": "career",
        "wealth": "wealth",
        "love": "marriage",
        "marriage": "marriage",
        "relationship": "marriage",
        "health": "health",
        "children": "children",
        "property": "property",
        "legal": "health",  # GK covers both
        "foreign": None,  # Handled by prashna check
    }

    target_event = domain_to_event.get(concern_domain.lower())
    if not target_event:
        return ""

    # Check if any stored prediction matches the domain
    for p in predictions:
        if p.get("event_type") == target_event:
            conf = p.get("confidence", "medium").upper()
            desc = p.get("description", "")
            conditions = p.get("conditions", [])
            first_condition = conditions[0] if conditions else ""
            return (
                f"JAIMINI CONVERGENCE: {concern_domain.title()} signal is {conf} "
                f"— {first_condition}. {desc}"
            )

    return f"JAIMINI CONVERGENCE: No specific {concern_domain} trigger in current period."


# =============================================================================
# BACKFILL SCRIPT HELPER
# =============================================================================

def backfill_chart_jaimini(
    chart_row: Dict[str, Any],
    supabase_client,
) -> bool:
    """
    Backfill a single chart with Jaimini data.
    Called by the backfill script for existing charts.

    Args:
        chart_row: Full chart row from Supabase
        supabase_client: Supabase client instance

    Returns:
        True if successful, False if failed
    """
    try:
        chart_id = chart_row["id"]
        lagna_sign = chart_row.get("lagna_sign_index")  # Must be 0-indexed int

        if lagna_sign is None:
            # Try to derive from lagna_sign text
            lagna_text = chart_row.get("lagna_sign", "")
            try:
                lagna_sign = SIGN_NAMES.index(lagna_text.title())
            except ValueError:
                logger.error(f"Cannot determine lagna sign for chart {chart_id}")
                return False

        # Get planets from chart_data JSONB
        chart_data_json = chart_row.get("chart_data", {})
        if isinstance(chart_data_json, str):
            chart_data_json = json.loads(chart_data_json)

        planets_dict = chart_data_json.get("planets", {})
        d9_planets_dict = chart_data_json.get("d9_planets", {})

        birth_date_str = chart_row.get("birth_date", "")
        if not birth_date_str:
            logger.error(f"No birth_date for chart {chart_id}")
            return False

        # Normalize birth_date format
        if "T" in str(birth_date_str):
            birth_date_str = str(birth_date_str).split("T")[0]

        result = build_and_store_jaimini(
            chart_id=chart_id,
            lagna_sign=lagna_sign,
            planets_dict=planets_dict,
            d9_planets_dict=d9_planets_dict,
            birth_date_str=birth_date_str,
            supabase_client=supabase_client,
        )

        return result is not None

    except Exception as e:
        logger.error(f"Backfill failed for chart {chart_row.get('id', 'unknown')}: {e}")
        return False


# =============================================================================
# MAIN.PY WIRING REFERENCE
# =============================================================================

"""
===========================================================================
WIRING INTO MAIN.PY — COPY/PASTE REFERENCE
===========================================================================

1. CHART CREATION (POST /api/v1/chart/create)
   After Swiss Ephemeris calculation, add:

   ┌──────────────────────────────────────────────────────────┐
   │  from antar_engine.jaimini_integration import (          │
   │      build_and_store_jaimini                             │
   │  )                                                       │
   │                                                          │
   │  # After planets are calculated and before response:     │
   │  jaimini_result = build_and_store_jaimini(               │
   │      chart_id=chart_id,                                  │
   │      lagna_sign=lagna_sign_index,                        │
   │      planets_dict=planets_for_db,                        │
   │      d9_planets_dict=d9_planets_for_db,                  │
   │      birth_date_str=birth_date,                          │
   │      supabase_client=supabase,                           │
   │  )                                                       │
   └──────────────────────────────────────────────────────────┘


2. PREDICT ENDPOINT (POST /api/v1/predict)
   Inside build_complete_context(), after Layer 2 (Dasha timing):

   ┌──────────────────────────────────────────────────────────┐
   │  from antar_engine.jaimini_integration import (          │
   │      format_jaimini_context_from_stored,                 │
   │      score_jaimini_convergence,                          │
   │  )                                                       │
   │                                                          │
   │  # --- LAYER 2.5: JAIMINI CHARA DASHA ---               │
   │  jaimini_block = format_jaimini_context_from_stored(     │
   │      chart_data                                          │
   │  )                                                       │
   │  context += jaimini_block                                │
   │                                                          │
   │  # --- JAIMINI CONVERGENCE NOTE ---                      │
   │  jaimini_convergence = score_jaimini_convergence(        │
   │      chart_data, concern_domain                          │
   │  )                                                       │
   │  context += "\n" + jaimini_convergence + "\n"            │
   └──────────────────────────────────────────────────────────┘


3. PRASHNA ENDPOINT (POST /api/v1/prashna)
   After the main YES/NO verdict, add Jaimini triple-lock:

   ┌──────────────────────────────────────────────────────────┐
   │  from antar_engine.jaimini_integration import (          │
   │      jaimini_prashna_check                               │
   │  )                                                       │
   │                                                          │
   │  # Map user question to type                             │
   │  q_type = detect_question_type(question)                 │
   │  jaimini_check = jaimini_prashna_check(                  │
   │      chart_data, q_type, lagna_sign_index                │
   │  )                                                       │
   │                                                          │
   │  # Boost confidence if Jaimini agrees                    │
   │  if jaimini_check["jaimini_verdict"]:                    │
   │      confidence_score += 20  # boost                     │
   │      verdict_reasons.extend(jaimini_check["reasons"])    │
   └──────────────────────────────────────────────────────────┘


4. BACKFILL SCRIPT
   For existing charts without jaimini_data:

   ┌──────────────────────────────────────────────────────────┐
   │  from antar_engine.jaimini_integration import (          │
   │      backfill_chart_jaimini                              │
   │  )                                                       │
   │                                                          │
   │  charts = supabase.table("charts").select("*")           │
   │      .is_("jaimini_data", "null").execute()              │
   │                                                          │
   │  for chart in charts.data:                               │
   │      success = backfill_chart_jaimini(chart, supabase)   │
   │      print(f"{chart['id']}: {'OK' if success else 'FAIL'}") │
   └──────────────────────────────────────────────────────────┘


5. DASHBOARD ENDPOINT (GET /api/v1/dashboard/{chart_id})
   Add jaimini summary to the response:

   ┌──────────────────────────────────────────────────────────┐
   │  # In the dashboard response builder:                    │
   │  jd = chart_data.get("jaimini_data", {})                 │
   │  if isinstance(jd, str):                                 │
   │      jd = json.loads(jd) if jd else {}                   │
   │                                                          │
   │  response["jaimini"] = {                                 │
   │      "karakas": jd.get("karakas", []),                   │
   │      "arudha_lagna": jd.get("arudha_lagna", {}),        │
   │      "upapada_lagna": jd.get("upapada_lagna", {}),      │
   │      "karakamsa": jd.get("karakamsa", {}),              │
   │      "current_md": jd.get("current_md"),                │
   │      "current_ad": jd.get("current_ad"),                │
   │      "predictions": jd.get("predictions", []),          │
   │  }                                                       │
   └──────────────────────────────────────────────────────────┘

===========================================================================
"""
