"""
desh_kal_patra.py
Sprint C2 — Desh Kal Patra (Real-World Economic Context Layer)

Fetches live economic indicators per country and combines them with
the existing cultural + nation astrological context into one rich
context block for the /predict system prompt.

Architecture:
- World Bank API (free, no key) for GDP/inflation/unemployment
- DeepSeek for sector intelligence summary (cached weekly)
- Supabase table `country_context_cache` for TTL caching
- Falls back gracefully to static cultural data if anything fails

Cache TTL: 7 days — data doesn't change faster than that.
Zero extra DB queries in the hot path — reads from cache only.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CACHE_TABLE   = "country_context_cache"
CACHE_TTL_DAYS = 7

# World Bank indicator codes
WB_BASE = "https://api.worldbank.org/v2/country/{code}/indicator/{indicator}?format=json&mrv=1"
WB_GDP          = "NY.GDP.MKTP.KD.ZG"   # GDP growth rate %
WB_INFLATION    = "FP.CPI.TOTL.ZG"      # Consumer price inflation %
WB_UNEMPLOYMENT = "SL.UEM.TOTL.ZS"      # Unemployment % of total labour force

# Sector intelligence prompt — kept tight so DeepSeek is fast
SECTOR_PROMPT = """You are an economic analyst. For {country_name} in {year}, list:
1. THREE sectors currently growing (hiring, investment flowing in)
2. TWO sectors currently contracting or struggling
3. ONE sentence on emigration/immigration conditions
4. ONE sentence on currency and financial stability

Be specific to {country_name}. Plain English. No hedging. No bullet symbols.
Format exactly:
GROWING: sector1, sector2, sector3
CONTRACTING: sector1, sector2
EMIGRATION: one sentence
CURRENCY: one sentence"""


# ── Main public function ──────────────────────────────────────────────────────

async def get_dkp_context(
    country_code: str,
    country_name: str,
    supabase,
    deepseek_client,
    force_refresh: bool = False
) -> str:
    """
    Returns a plain English Desh Kal Patra context block for the /predict prompt.
    Reads from cache if fresh. Rebuilds if stale or missing.

    Args:
        country_code:    ISO 2-letter code e.g. "IN", "US", "CO"
        country_name:    Full name e.g. "India"
        supabase:        Supabase client
        deepseek_client: OpenAI-compatible DeepSeek client
        force_refresh:   Bypass cache

    Returns:
        str — formatted context block ready to append to system prompt
    """
    if not country_code:
        return ""

    # ── Try cache first ───────────────────────────────────────────
    if not force_refresh:
        cached = _read_cache(country_code, supabase)
        if cached:
            return cached

    # ── Build fresh ───────────────────────────────────────────────
    try:
        indicators = await _fetch_world_bank(country_code)
    except Exception as e:
        logger.warning(f"[DKP] World Bank fetch failed for {country_code}: {e}")
        indicators = {}

    try:
        sector_text = await _fetch_sector_intelligence(
            country_code, country_name, deepseek_client
        )
    except Exception as e:
        logger.warning(f"[DKP] Sector intelligence failed for {country_code}: {e}")
        sector_text = ""

    period_quality = _assess_period_quality(indicators)
    block          = _format_context_block(
        country_code, country_name, indicators, sector_text, period_quality
    )

    # ── Write to cache ────────────────────────────────────────────
    try:
        _write_cache(country_code, block, indicators, period_quality, supabase)
    except Exception as e:
        logger.warning(f"[DKP] Cache write failed for {country_code}: {e}")

    return block


# ── Cache read/write ──────────────────────────────────────────────────────────

def _read_cache(country_code: str, supabase) -> Optional[str]:
    """Return cached context block if it exists and is < 7 days old."""
    try:
        result = supabase.table(CACHE_TABLE) \
            .select("context_block, fetched_at") \
            .eq("country_code", country_code) \
            .execute()

        if not result.data:
            return None

        row        = result.data[0]
        fetched_at = datetime.fromisoformat(
            row["fetched_at"].replace("Z", "+00:00")
        )
        age = datetime.now(timezone.utc) - fetched_at

        if age < timedelta(days=CACHE_TTL_DAYS):
            logger.info(f"[DKP] Cache hit for {country_code} (age {age.days}d)")
            return row["context_block"]

        logger.info(f"[DKP] Cache stale for {country_code} (age {age.days}d) — rebuilding")
        return None

    except Exception as e:
        logger.warning(f"[DKP] Cache read error for {country_code}: {e}")
        return None


def _write_cache(
    country_code: str,
    context_block: str,
    indicators: dict,
    period_quality: str,
    supabase
) -> None:
    supabase.table(CACHE_TABLE).upsert({
        "country_code":   country_code,
        "context_block":  context_block,
        "gdp_growth":     indicators.get("gdp_growth"),
        "inflation":      indicators.get("inflation"),
        "unemployment":   indicators.get("unemployment"),
        "period_quality": period_quality,
        "fetched_at":     datetime.now(timezone.utc).isoformat(),
    }).execute()


# ── World Bank fetch ──────────────────────────────────────────────────────────

async def _fetch_world_bank(country_code: str) -> dict:
    """Fetch GDP growth, inflation, unemployment from World Bank API."""
    results = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for key, indicator in [
            ("gdp_growth",   WB_GDP),
            ("inflation",    WB_INFLATION),
            ("unemployment", WB_UNEMPLOYMENT),
        ]:
            try:
                url  = WB_BASE.format(code=country_code.lower(), indicator=indicator)
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                # World Bank returns [metadata, [data_points]]
                if (
                    isinstance(data, list)
                    and len(data) > 1
                    and isinstance(data[1], list)
                    and data[1]
                ):
                    value = data[1][0].get("value")
                    if value is not None:
                        results[key] = round(float(value), 1)

            except Exception as e:
                logger.warning(f"[DKP] World Bank {key} failed for {country_code}: {e}")

    return results


# ── Sector intelligence via DeepSeek ─────────────────────────────────────────

async def _fetch_sector_intelligence(
    country_code: str,
    country_name: str,
    deepseek_client
) -> str:
    """Ask DeepSeek for current sector trends. Returns raw text block."""
    year   = datetime.now().year
    prompt = SECTOR_PROMPT.format(
        country_name=country_name,
        year=year
    )

    response = await deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role":    "system",
                "content": "You are a precise economic analyst. Answer factually and concisely."
            },
            {
                "role":    "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


# ── Period quality assessment ─────────────────────────────────────────────────

def _assess_period_quality(indicators: dict) -> str:
    """
    Classify economic climate as expansion / stable / contraction.
    Used to calibrate confidence and risk framing in predictions.
    """
    gdp          = indicators.get("gdp_growth")
    inflation    = indicators.get("inflation")
    unemployment = indicators.get("unemployment")

    if gdp is None:
        return "stable"

    # Simple but effective heuristic
    score = 0

    if gdp >= 5:        score += 2
    elif gdp >= 2:      score += 1
    elif gdp < 0:       score -= 2
    else:               score -= 1

    if inflation is not None:
        if inflation <= 3:    score += 1
        elif inflation >= 8:  score -= 2
        elif inflation >= 5:  score -= 1

    if unemployment is not None:
        if unemployment <= 5:    score += 1
        elif unemployment >= 10: score -= 1

    if score >= 3:    return "expansion"
    elif score <= -1: return "contraction"
    else:             return "stable"


# ── Format the final context block ───────────────────────────────────────────

def _format_context_block(
    country_code:   str,
    country_name:   str,
    indicators:     dict,
    sector_text:    str,
    period_quality: str,
) -> str:
    """
    Build the context block string appended to /predict system prompt.
    Designed to be scannable by the LLM — clear labels, specific numbers.
    """
    now    = datetime.now(timezone.utc)
    month  = now.strftime("%B %Y")

    lines = [f"DESH KAL PATRA — {country_name} ({country_code}) — {month}:"]

    # Economic indicators
    gdp          = indicators.get("gdp_growth")
    inflation    = indicators.get("inflation")
    unemployment = indicators.get("unemployment")

    econ_parts = []
    if gdp          is not None: econ_parts.append(f"GDP growth {gdp:+.1f}%")
    if inflation    is not None: econ_parts.append(f"inflation {inflation:.1f}%")
    if unemployment is not None: econ_parts.append(f"unemployment {unemployment:.1f}%")

    if econ_parts:
        quality_label = {
            "expansion":   "Expansion",
            "stable":      "Stable",
            "contraction": "Contraction"
        }.get(period_quality, "Stable")
        lines.append(f"Economic climate: {quality_label}. {', '.join(econ_parts)}.")
    else:
        lines.append(f"Economic climate: Data unavailable — use cultural context.")

    # Sector intelligence
    if sector_text:
        for line in sector_text.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)

    # Prediction guidance
    guidance = {
        "expansion":   (
            "Risk appetite appropriate. Career moves, business launches, "
            "and investments have economic tailwind."
        ),
        "stable":      (
            "Selective risk. Established careers and conservative investments "
            "outperform speculation."
        ),
        "contraction": (
            "Caution warranted. Stability and debt reduction outperform "
            "new ventures. Foreign options may be stronger than domestic."
        ),
    }.get(period_quality, "")

    if guidance:
        lines.append(f"Prediction guidance: {guidance}")

    return "\n".join(lines)


# ── Synchronous wrapper for non-async contexts ────────────────────────────────

def get_dkp_context_sync(
    country_code: str,
    country_name: str,
    supabase,
) -> Optional[str]:
    """
    Read DKP from cache only — no API calls.
    Safe to call from sync code (e.g. cron jobs reading existing cache).
    Returns None if not cached.
    """
    return _read_cache(country_code, supabase)


# ── Weekly cron refresh ───────────────────────────────────────────────────────

async def refresh_all_country_contexts(supabase, deepseek_client) -> None:
    """
    Refresh DKP context for all countries that have active charts.
    Called weekly by the scheduler alongside ping_cron.
    """
    from .country_context import COUNTRY_CONTEXT

    refreshed = 0
    failed    = 0

    for code, data in COUNTRY_CONTEXT.items():
        name = data.get("name", code)
        try:
            await get_dkp_context(
                country_code=code,
                country_name=name,
                supabase=supabase,
                deepseek_client=deepseek_client,
                force_refresh=True,
            )
            refreshed += 1
            logger.info(f"[DKP cron] Refreshed {code}")
        except Exception as e:
            failed += 1
            logger.warning(f"[DKP cron] Failed {code}: {e}")

    logger.info(f"[DKP cron] Done — {refreshed} refreshed, {failed} failed")
