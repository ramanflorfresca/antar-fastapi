#!/usr/bin/env python3
"""
patch_json_path_fix.py
=======================
Fixes two bugs in the JSON path (/predict with use_json_context=True):

BUG 1: context_path missing from return dict
  — Response always shows context_path=null
  — Fix: add "context_path": "json" to return dict

BUG 2: _lang variable check is fragile
  — "_lang" in dir() checks module scope, not local scope
  — Fix: use request.language directly

BUG 3: Historical dasha context missing
  — build_chart_context_json only fetches current/upcoming dashas
  — For past event questions, Claude needs full historical MD sequence
  — Fix: inject full vimsottari MD sequence into live block

USAGE:
  cd ~/antarai && source venv311/bin/activate
  python patch_json_path_fix.py
  python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"
  git add -A && git commit -m "fix: JSON path context_path + historical dasha context" && git push
"""

import sys, ast, re
from pathlib import Path


def main():
    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    content = Path("main.py").read_text(encoding="utf-8")

    # ----------------------------------------------------------------
    # FIX 1: Add context_path to JSON path return dict
    # ----------------------------------------------------------------
    old1 = '''                return {
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
                }'''

    new1 = '''                return {
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
                    "context_path":         "json",
                }'''

    if old1 in content:
        content = content.replace(old1, new1, 1)
        print("✅ Fix 1: context_path added to JSON path return dict")
    else:
        print("⚠️  Fix 1: pattern not found — check manually")

    # ----------------------------------------------------------------
    # FIX 2: Fix _lang variable check
    # ----------------------------------------------------------------
    old2 = '"language": _lang if "_lang" in dir() else language,'
    new2 = '"language": request.language if hasattr(request, "language") else "en",'

    if old2 in content:
        # Replace both occurrences (save to chat_messages has same pattern)
        content = content.replace(old2, new2)
        print("✅ Fix 2: _lang variable check fixed")
    else:
        print("⚠️  Fix 2: _lang pattern not found — may already be fixed")

    # ----------------------------------------------------------------
    # FIX 3: Inject historical dasha context for past-event questions
    # Detect past tense questions and add full MD sequence to live block
    # ----------------------------------------------------------------
    old3 = '''                _json_ctx = await build_chart_context_json(
                    chart_id=request.chart_id,
                    question=request.question,
                    concern=concern,
                    language=_lang if "_lang" in dir() else language,
                    supabase=supabase,
                )'''

    new3 = '''                # Detect past-tense questions — need historical dasha context
                _past_keywords = [
                    "when did", "when was", "what year", "which year",
                    "when did i", "when were", "what happened",
                    "cuándo", "cuando", "qué año", "que año",
                    "married", "born", "moved", "divorced", "divorce",
                    "child", "children", "hijo", "hija", "matrimonio",
                ]
                _is_past_question = any(
                    kw in request.question.lower()
                    for kw in _past_keywords
                )

                _json_ctx = await build_chart_context_json(
                    chart_id=request.chart_id,
                    question=request.question,
                    concern=concern,
                    language=request.language if hasattr(request, "language") else "en",
                    supabase=supabase,
                )

                # For past-event questions, inject full historical MD sequence
                if _is_past_question:
                    try:
                        _hist_rows = supabase.table("dasha_periods") \\
                            .select("planet_or_sign,start_date,end_date,level,metadata") \\
                            .eq("chart_id", request.chart_id) \\
                            .eq("system", "vimsottari") \\
                            .order("start_date") \\
                            .execute()

                        _md_rows = [
                            r for r in _hist_rows.data
                            if r.get("level") == 1 or
                               str(r.get("level","")).lower() in ("mahadasha","md","1")
                        ]
                        _ad_rows = [
                            r for r in _hist_rows.data
                            if r.get("level") == 2 or
                               str(r.get("level","")).lower() in ("antardasha","ad","2")
                        ]

                        # Build MD sequence string
                        _md_lines = []
                        for row in _md_rows:
                            planet = row.get("planet_or_sign","")
                            start  = str(row.get("start_date",""))[:10]
                            end    = str(row.get("end_date",""))[:10]
                            _md_lines.append(f"  {planet} MD: {start} → {end}")

                        # Build AD dict grouped by parent MD
                        _ad_by_parent = {}
                        for row in _ad_rows:
                            parent = (row.get("metadata") or {}).get("parent_lord","")
                            if parent not in _ad_by_parent:
                                _ad_by_parent[parent] = []
                            planet = row.get("planet_or_sign","")
                            start  = str(row.get("start_date",""))[:10]
                            end    = str(row.get("end_date",""))[:10]
                            _ad_by_parent[parent].append(f"{planet} AD: {start} → {end}")

                        _hist_block = "\\n\\n## HISTORICAL VIMSOTTARI DASHA SEQUENCE\\n"
                        _hist_block += "Mahadashas (MD):\\n"
                        _hist_block += "\\n".join(_md_lines)
                        _hist_block += "\\n\\nAnterdashas (AD) by MD:\\n"
                        for md_planet, ads in _ad_by_parent.items():
                            _hist_block += f"\\n{md_planet} MD:\\n"
                            for ad in ads:
                                _hist_block += f"  {ad}\\n"

                        _hist_block += """
## PAST EVENT PREDICTION RULES
When asked about PAST events (marriage, children, relocation, divorce):
1. Find the approximate year range using the person's birth year + typical life stage age
2. Look up which MD+AD was active in that year range from the sequence above
3. Confirm the AD planet supports the event via classical house rules:
   - Marriage: 7H lord AD, Venus AD, or Saturn AD (formal commitment)
   - Foreign move: Rahu AD or 12H lord AD
   - First child: 5H lord AD or Jupiter AD
   - Second child: AD after first child, 9H lord AD
   - Divorce: Saturn AD during 7H lord MD
4. State the predicted year as a specific year, not a future window
5. NEVER predict past events as future events
"""
                        # Append historical context to live block
                        if isinstance(_json_ctx, dict):
                            _json_ctx["_historical_dasha"] = _hist_block
                        print(f"[json-v2] Historical dasha injected — {len(_md_lines)} MDs, {len(_ad_rows)} ADs")
                    except Exception as _hist_e:
                        print(f"[json-v2] Historical dasha injection failed (non-fatal): {_hist_e}")'''

    if old3 in content:
        content = content.replace(old3, new3, 1)
        print("✅ Fix 3: Historical dasha context injection added")
    else:
        print("⚠️  Fix 3: build_chart_context_json pattern not found — check manually")

    # ----------------------------------------------------------------
    # FIX 4: Include historical dasha in system prompt when available
    # ----------------------------------------------------------------
    old4 = '''                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\\n\\n## CHART DATA (JSON)\\n"
                    + _static_json
                    + "\\n\\n## LIVE DATA\\n"
                    + _live_json
                )'''

    new4 = '''                _hist_suffix = _json_ctx.get("_historical_dasha", "") if isinstance(_json_ctx, dict) else ""
                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\\n\\n## CHART DATA (JSON)\\n"
                    + _static_json
                    + "\\n\\n## LIVE DATA\\n"
                    + _live_json
                    + (_hist_suffix if _hist_suffix else "")
                )'''

    if old4 in content:
        content = content.replace(old4, new4, 1)
        print("✅ Fix 4: Historical dasha included in system prompt")
    else:
        print("⚠️  Fix 4: _json_system pattern not found — check manually")

    # Validate
    try:
        ast.parse(content)
        print("✅ syntax OK")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        sys.exit(1)

    Path("main.py").write_text(content, encoding="utf-8")
    print("\ngit add -A && git commit -m 'fix: JSON path context_path + historical dasha for past questions' && git push")
    print("\nTest after deploy:")
    print("""  curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/predict" \\
    -H "Content-Type: application/json" \\
    -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a","question":"when did I get married","language":"en","use_json_context":true}' \\
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('PATH:', d.get('context_path')); print('TIMING:', d.get('timing_window')); print(d.get('plain_summary','')[:200])" """)


if __name__ == "__main__":
    main()
