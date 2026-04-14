#!/usr/bin/env python3
"""
patch_astrocartography_endpoint.py
=====================================
Adds /api/v1/astrocartography/recommend endpoint to main.py.

USAGE:
  cd ~/antarai && source venv311/bin/activate
  python patch_astrocartography_endpoint.py
  python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"
  git add -A && git commit -m "feat: astrocartography city recommendation endpoint" && git push

TEST after deploy:
  curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/astrocartography/recommend" \
    -H "Content-Type: application/json" \
    -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a","intent":"startup","region":"latam","language":"en"}' \
    | python3 -m json.tool
"""

import sys, ast
from pathlib import Path

ENDPOINT_CODE = '''
# ============================================================================
# ASTROCARTOGRAPHY RECOMMENDATION ENDPOINT
# ============================================================================

class AstroRecommendRequest(BaseModel):
    chart_id:  str
    intent:    str = Field("startup", description="startup|wealth|billionaire|career|relationships|health|spiritual|general")
    region:    str = Field("global",  description="latam|europe|asia|middleeast|africa|north_america|global")
    language:  str = Field("en",      description="en|es")
    top_n:     int = Field(5,         description="Number of cities to return (1-10)")


@app.post("/api/v1/astrocartography/recommend")
async def astrocartography_recommend(
    request: AstroRecommendRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Recommend best cities for a given intent based on astrocartography + dasha alignment.

    Intents: startup, wealth, billionaire, career, relationships, health, spiritual, general
    Regions: latam, europe, asia, middleeast, africa, north_america, global
    """
    # Auth (optional — same pattern as predict)
    user_id = None
    try:
        if authorization:
            token = authorization.replace("Bearer ", "").strip()
            user_resp = supabase.auth.get_user(token)
            user_id = user_resp.user.id if user_resp and user_resp.user else None
    except Exception:
        pass

    # Fetch chart
    chart_res = supabase.table("charts").select("*").eq("id", request.chart_id).execute()
    if not chart_res.data:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_record = chart_res.data[0]

    # Fetch dashas
    from antar_engine.chart_context_builder_json import _fetch_dashas
    dashas = _fetch_dashas(request.chart_id, supabase)

    # Run recommendation engine
    from antar_engine.astrocartography_recommender import recommend_cities
    result = recommend_cities(
        chart_record=chart_record,
        dashas=dashas,
        intent=request.intent,
        region=request.region,
        language=request.language,
        top_n=min(request.top_n, 10),
    )

    return result

# ============================================================================
# END ASTROCARTOGRAPHY RECOMMENDATION ENDPOINT
# ============================================================================
'''

def main():
    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    content = Path("main.py").read_text(encoding="utf-8")

    if "astrocartography_recommend" in content:
        print("ℹ️  Endpoint already present — skipping")
        return

    # Inject before the last app route or at end of file before uvicorn block
    # Landmark: find a reliable insertion point
    landmarks = [
        '\nif __name__ == "__main__":',
        '\nuvicorn.run(',
        '\n# ── Run ──',
    ]

    inserted = False
    for landmark in landmarks:
        if landmark in content:
            content = content.replace(landmark, ENDPOINT_CODE + landmark, 1)
            inserted = True
            print(f"✅ Endpoint injected before: {landmark.strip()[:40]}")
            break

    if not inserted:
        # Append at end
        content = content + "\n" + ENDPOINT_CODE
        print("✅ Endpoint appended at end of file")

    try:
        ast.parse(content)
        print("✅ syntax OK")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}"); sys.exit(1)

    Path("main.py").write_text(content, encoding="utf-8")
    print("\ngit add -A && git commit -m 'feat: astrocartography city recommendation endpoint' && git push")
    print("\nTest after deploy:")
    print("""  curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/astrocartography/recommend" \\
    -H "Content-Type: application/json" \\
    -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a","intent":"startup","region":"latam","language":"en"}' \\
    | python3 -m json.tool""")


if __name__ == "__main__":
    main()
