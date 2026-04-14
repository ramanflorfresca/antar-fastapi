#!/usr/bin/env python3
"""
patch_predict_location_routing.py
===================================
Routes location-related questions in /predict to DeepSeek
instead of Claude, using the astrocartography engine for accuracy.

DETECTION: if the question contains location keywords AND the chart has
astrocartography data, route to DeepSeek with the full context.

USAGE:
  cd ~/antarai && source venv311/bin/activate
  python patch_predict_location_routing.py
  python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"
  git add -A && git commit -m "feat: route location questions to DeepSeek in /predict" && git push

TEST:
  curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/predict" \
    -H "Content-Type: application/json" \
    -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a",
         "question":"which city is best for my startup growth?",
         "language":"en"}' \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('MODEL:', d.get('model_used')); print(d.get('plain_summary','')[:300])"
"""

import sys, ast
from pathlib import Path


# ---------------------------------------------------------------------------
# Location routing block — injected at the START of the predict route,
# before the main context building. If it fires, it returns early.
# ---------------------------------------------------------------------------

LOCATION_ROUTING_BLOCK = '''
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
                if (_loc_planets.get("Jupiter") or {}).get("house") == 2 and \
                   (_loc_planets.get("Venus") or {}).get("house") == 11:
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
'''


def main():
    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    content = Path("main.py").read_text(encoding="utf-8")

    if "LOCATION QUESTION ROUTING" in content:
        print("ℹ️  Location routing already present — skipping")
        return

    # Inject after chart_data and dashas are fetched, before context building
    # Landmark: right after `dashas_response = get_dashas_for_chart(request.chart_id)`
    landmark = "    dashas_response = get_dashas_for_chart(request.chart_id)"

    if landmark not in content:
        print("⚠️  Landmark not found. Trying alternate...")
        landmark = "    # Life events"
        if landmark not in content:
            print("❌ Could not find injection point. Manual fix needed.")
            print("   Add the location routing block after dashas_response = get_dashas_for_chart()")
            sys.exit(1)

    content = content.replace(landmark, landmark + "\n" + LOCATION_ROUTING_BLOCK, 1)
    print("✅ Location routing block injected")

    try:
        ast.parse(content)
        print("✅ syntax OK")
    except SyntaxError as e:
        print(f"❌ {e}"); sys.exit(1)

    Path("main.py").write_text(content, encoding="utf-8")
    print("\ngit add -A && git commit -m 'feat: route location questions to DeepSeek in /predict' && git push")
    print("\nTest:")
    print("""  curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/predict" \\
    -H "Content-Type: application/json" \\
    -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a","question":"which city is best for my startup?","language":"en"}' \\
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('MODEL:', d.get('model_used','claude')); print(d.get('plain_summary','')[:300])" """)


if __name__ == "__main__":
    main()
