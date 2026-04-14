#!/usr/bin/env python3
"""
patch_signature_endpoint.py
=============================
Adds two endpoints for the onboarding Signature Verification screen:

  GET  /api/v1/chart/signature/{chart_id}
    — Runs DashaEventMapper, returns 3 human-readable statements
    — No astrological terms in output

  POST /api/v1/chart/signature/confirm
    — Stores user confirmations to chart_data.signature_confirmations

USAGE:
  cd ~/antarai && source venv311/bin/activate
  python patch_signature_endpoint.py
  python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"
  git add -A && git commit -m "feat: signature verification endpoint for onboarding WOW" && git push

TEST:
  curl -s "https://antar-fastapi-production.up.railway.app/api/v1/chart/signature/de02bb52-d43a-4b09-be25-b45a07bfbf8a" | python3 -m json.tool
"""

import sys, ast
from pathlib import Path

ENDPOINT_CODE = '''
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
        ads_res = supabase.table("dasha_periods") \
            .select("planet_or_sign,start_date,end_date,level,type,metadata") \
            .eq("chart_id", chart_id) \
            .eq("system", "vimsottari") \
            .order("start_date") \
            .execute()

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
            cur_md_res = supabase.table("dasha_periods") \
                .select("planet_or_sign,start_date,end_date") \
                .eq("chart_id", chart_id) \
                .eq("system", "vimsottari") \
                .lte("start_date", "2026-04-14") \
                .gte("end_date", "2026-04-14") \
                .execute()

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
        chart_res = supabase.table("charts") \
            .select("chart_data") \
            .eq("id", request.chart_id) \
            .single().execute()

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
'''


def main():
    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    content = Path("main.py").read_text(encoding="utf-8")

    if "get_signature_statements" in content:
        print("ℹ️  Signature endpoint already present — skipping")
        return

    # Inject before main app run
    for lm in ['\nif __name__ == "__main__":', '\nuvicorn.run(', '\n# ── Run ──']:
        if lm in content:
            content = content.replace(lm, ENDPOINT_CODE + lm, 1)
            print("✅ Signature endpoint injected")
            break
    else:
        content += "\n" + ENDPOINT_CODE
        print("✅ Signature endpoint appended")

    try:
        ast.parse(content)
        print("✅ syntax OK")
    except SyntaxError as e:
        print(f"❌ {e}"); sys.exit(1)

    Path("main.py").write_text(content, encoding="utf-8")
    print("\ngit add -A && git commit -m 'feat: signature verification endpoint for onboarding WOW' && git push")
    print("\nTest:")
    print('  curl -s "https://antar-fastapi-production.up.railway.app/api/v1/chart/signature/de02bb52-d43a-4b09-be25-b45a07bfbf8a" | python3 -m json.tool')


if __name__ == "__main__":
    main()
