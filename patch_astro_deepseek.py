#!/usr/bin/env python3
"""
patch_astro_deepseek.py
========================
Astrocartography endpoint with DeepSeek explanation layer.
Matches the exact architecture from the spec:
  - Python scores (deterministic)
  - DeepSeek narrates (never calculates)
  - Stay-vs-move applied by Python, explained by DeepSeek
"""

import sys, ast
from pathlib import Path

NEW_ENDPOINT = '''
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
        "You are Antar\'s astrocartography interpreter. "
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
'''


def main():
    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    content = Path("main.py").read_text(encoding="utf-8")

    # Remove old endpoint
    start_m = "# ============================================================================\n# ASTROCARTOGRAPHY RECOMMENDATION ENDPOINT"
    end_m   = "# END ASTROCARTOGRAPHY RECOMMENDATION ENDPOINT\n# ============================================================================"
    if start_m in content and end_m in content:
        si = content.find(start_m)
        ei = content.find(end_m) + len(end_m)
        content = content[:si] + content[ei:]
        print("✅ Old endpoint removed")

    # Inject new
    for lm in ['\nif __name__ == "__main__":', '\nuvicorn.run(', '\n# ── Run ──']:
        if lm in content:
            content = content.replace(lm, NEW_ENDPOINT + lm, 1)
            print("✅ New endpoint injected")
            break
    else:
        content += "\n" + NEW_ENDPOINT
        print("✅ Endpoint appended")

    try:
        ast.parse(content)
        print("✅ syntax OK")
    except SyntaxError as e:
        print(f"❌ {e}"); sys.exit(1)

    Path("main.py").write_text(content, encoding="utf-8")
    print("\nCheck DEEPSEEK_API_KEY is in Railway:")
    print("  railway variables | grep DEEPSEEK")
    print("\ngit add -A && git commit -m 'feat: astrocartography v4 — Python scores + DeepSeek narrative' && git push")


if __name__ == "__main__":
    main()
