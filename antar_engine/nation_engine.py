# nation_engine.py
import os
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from supabase import create_client, Client
from . import chart, vimsottari, utils
from .country_context import get_nation_chart_params

# Table name in Supabase
NATION_CHARTS_TABLE = "nation_charts"

def get_nation_chart(country_code: str, supabase: Client, force_refresh: bool = False) -> dict:
    """
    Retrieve or compute the nation chart and its dashas.
    Returns a dictionary with 'chart_data' and 'dashas' (Vimsottari).
    Caches in Supabase.
    """
    if not force_refresh:
        # Try to fetch from cache
        result = supabase.table(NATION_CHARTS_TABLE).select("*").eq("country_code", country_code).execute()
        if result.data:
            row = result.data[0]
            # Optional: refresh if older than 7 days
            last_updated = datetime.fromisoformat(row["last_updated"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_updated < timedelta(days=7):
                return {
                    "chart_data": row["chart_data"],
                    "dashas": row["dashas"]
                }

    # Compute nation chart
    params = get_nation_chart_params(country_code)
    if not params:
        raise ValueError(f"No nation chart parameters for country code: {country_code}")

    # Compute chart
    chart_data = chart.calculate_chart(
        params["birth_date"],
        params["birth_time"],
        params["latitude"],
        params["longitude"],
        params["timezone_offset"]
    )

    # Compute birth JD
    dt_local = datetime.strptime(f"{params['birth_date']} {params['birth_time']}", "%Y-%m-%d %H:%M")
    dt_utc = dt_local - timedelta(hours=params["timezone_offset"])
    birth_jd = utils.julian_day(dt_utc)

    # Compute Vimsottari dashas (current and future)
    vim = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)

    # Prepare data for cache
    cache_data = {
        "chart_data": chart_data,
        "dashas": vim  # contains mahadashas and antardashas
    }

    # Upsert into cache
    supabase.table(NATION_CHARTS_TABLE).upsert({
        "country_code": country_code,
        "chart_data": chart_data,
        "dashas": vim,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }).execute()

    return cache_data

def get_current_nation_dashas(country_code: str, supabase: Client) -> dict:
    """
    Return the current Vimsottari mahadasha and antardasha for the nation.
    """
    nation = get_nation_chart(country_code, supabase)
    # Find current dasha based on current date
    now = datetime.now(timezone.utc)
    # The dashas are stored as a list of mahadashas with start/end dates
    mahadashas = nation["dashas"]["mahadashas"]
    current_md = None
    for md in mahadashas:
        start = datetime.fromisoformat(md["start_date"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(md["end_date"].replace("Z", "+00:00"))
        if start <= now < end:
            current_md = md
            break
    # Find current antardasha within that mahadasha
    current_ad = None
    if current_md:
        for ad in nation["dashas"]["antardashas"]:
            if ad.get("parent_lord") == current_md["lord"]:
                ad_start = datetime.fromisoformat(ad["start_date"].replace("Z", "+00:00"))
                ad_end = datetime.fromisoformat(ad["end_date"].replace("Z", "+00:00"))
                if ad_start <= now < ad_end:
                    current_ad = ad
                    break
    return {
        "mahadasha": current_md["lord"] if current_md else "unknown",
        "antardasha": current_ad["lord"] if current_ad else "unknown",
        "mahadasha_start": current_md["start_date"] if current_md else None,
        "mahadasha_end": current_md["end_date"] if current_md else None
    }

def get_nation_insight(country_code: str, supabase: Client, llm_client, language: str = "en") -> str:
    """
    Generate a brief two‑liner about the country's current astrological climate.
    Uses the LLM client to produce the insight.
    """
    nation = get_nation_chart(country_code, supabase)
    current = get_current_nation_dashas(country_code, supabase)

    # Build a simple prompt
    prompt = f"""
You are an expert in mundane astrology. Based on the following data for {country_code}, provide a brief, insightful two‑liner about the nation's current astrological climate and prospects. Keep it positive and constructive, suitable for a general audience.

Current national Vimsottari Mahadasha: {current['mahadasha']}
Current national Vimsottari Antardasha: {current['antardasha']}
(Optional: include any upcoming significant transits if you have them)

Respond in {language}.
"""
    try:
        response = llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a knowledgeable astrologer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM error in nation insight: {e}")
        return f"The nation of {country_code} is currently in its {current['mahadasha']} Mahadasha, indicating a period of focus on matters ruled by {current['mahadasha']}."
