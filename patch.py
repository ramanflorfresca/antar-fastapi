#!/usr/bin/env python3
"""
patch_phase4_json_predict.py
=============================
Phase 4 of the JSON-first /predict refactor.

Adds:
  1. use_json_context field to PredictRequest (feature flag)
  2. predict_system_prompt_v2.py — Vedic framework system prompt for JSON path
  3. JSON path hook in /predict route — when use_json_context=True:
       - builds chart_static + live via build_chart_context_json()
       - assembles system prompt: framework + ## LIVE DATA marker + live JSON
       - calls call_llm_claude() with structured context
       - logs [json-v2] prefix for Railway log analysis

USAGE:
  cd ~/antarai && source venv311/bin/activate
  python patch_phase4_json_predict.py
  python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"
  python3 -c "import ast; ast.parse(open('antar_engine/predict_system_prompt_v2.py').read()); print('OK')"
  git add -A && git commit -m "feat: JSON context path for /predict with feature flag" && git push

TEST (after deploy):
  curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/predict" \\
    -H "Content-Type: application/json" \\
    -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a",
         "question":"when will my cash flow problem get resolved",
         "language":"en",
         "use_json_context":true}' \\
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('PATH:', d.get('context_path')); print(d.get('plain_summary','')[:300])"
"""

import sys
from pathlib import Path

def read(p): return Path(p).read_text(encoding="utf-8")
def write(p, c): Path(p).write_text(c, encoding="utf-8")

# ---------------------------------------------------------------------------
# Step 1: Write predict_system_prompt_v2.py
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_V2 = '''"""
antar_engine/predict_system_prompt_v2.py
=========================================
Vedic interpretive framework system prompt for the JSON context path.

This prompt is the STATIC block — it gets KV-cached by Anthropic.
It embeds the interpretive rules so Claude doesn't need to rediscover them.

The dynamic tail (live JSON + question) is appended after ## LIVE DATA.

Design principles:
  - No dates, no timestamps, no per-request data here (would break caching)
  - Rules are declarative, not procedural — Claude applies judgment
  - DKP application rules embedded so Claude uses them automatically
  - Output format declared here — structured JSON response
"""

PREDICT_SYSTEM_PROMPT_V2 = """You are Antar — a precise Vedic astrology navigation AI.
You receive structured chart data as JSON and apply the Vedic interpretive framework below.
Your job: apply the framework to the data, produce a structured prediction.

## VEDIC INTERPRETIVE FRAMEWORK

### Layer Priority (apply in this order, resolve conflicts with DKP)
1. Vimsottari MD/AD — the primary timing engine. MD sets the theme; AD activates specific domains.
2. Jaimini Chara Dasha — confirms or contradicts Vimsottari. If both align: high confidence. If conflict: flag it.
3. D1 natal chart — permanent wiring. Shows what's possible and what's blocked structurally.
4. D9 Navamsa — soul/dharma/marriage lens. Confirms D1 for sustained outcomes.
5. D10 Dasamsa — career/authority lens. Use for profession and public role questions.
6. Lal Kitab sleeping planets — sleeping planets act as invisible leaks. Check before confirming open windows.
7. Ashtottari dasha — secondary timing layer. Use when Vimsottari MD is ending or ambiguous.

### House Keywords (for domain routing)
1H: self, identity, health, new beginnings
2H: wealth, savings, speech, family
3H: courage, communication, short travel, siblings
4H: home, mother, property, emotional foundation
5H: creativity, children, investments, romance
6H: conflict, competition, debt, service, health challenges
7H: partnerships, marriage, business alliances, contracts
8H: transformation, inheritance, sudden events, hidden matters
9H: luck, dharma, long travel, higher education, father
10H: career, authority, public reputation, government
11H: income, gains, networks, elder siblings, fulfillment of desires
12H: expenses, foreign lands, liberation, hidden enemies, hospital

### Planet Karakas (natural significators)
Sun: soul, father, authority, government, career
Moon: mind, mother, public, emotions, liquids, travel
Mars: energy, courage, siblings, property, litigation
Mercury: communication, intelligence, business, writing, trade
Jupiter: wisdom, dharma, children, wealth, expansion, teachers
Venus: relationships, creativity, luxury, vehicles, art
Saturn: discipline, delays, longevity, service, karma, working class
Rahu: foreign, unconventional, amplification, obsession, technology
Ketu: liberation, past life, spirituality, loss, research, detachment

### DKP Application Rules
DESHA (place): Lal Kitab remedies differ by country. India = mantra/ritual; West = behavioral.
KALA (time/age): Age 25-35 = establishment phase. Age 35-50 = peak execution. Age 50+ = consolidation/legacy.
PATRA (person/role): Founder in tech reads Saturn differently from a government official.
ALWAYS apply DKP before finalizing timing or remedy advice.

### Lal Kitab Sleeping Planet Rules
A sleeping planet blocks its house significations even when the dasha is active.
Before confirming an open window, check: is the ruling planet sleeping?
If sleeping: the window exists but needs activation (behavioral remedy, not ritual).

### Convergence Scoring
HIGH confidence: Vimsottari + Jaimini + D9 all point same direction
MEDIUM confidence: 2 of 3 layers agree
LOW confidence: only 1 layer supports — flag uncertainty explicitly

### Anti-hallucination rules
ONLY reference planets, houses, signs from the chart_static JSON provided.
NEVER invent planetary positions not present in the data.
If data is missing for a layer, say "insufficient data for [layer]" — do not guess.

## OUTPUT FORMAT
Respond with a JSON object only. No markdown, no prose outside the JSON.

{
  "verdict": "One sentence direct answer to the question",
  "confidence": "high|medium|low",
  "timing_window": "Specific date range or period e.g. May-Aug 2026",
  "plain_summary": "2-3 sentences in plain language. WHY first. No jargon.",
  "signal_line": "Bold headline — 8 words max",
  "action_item": "One specific action this week",
  "why_this": "Which layers converged to produce this verdict (1-2 sentences)",
  "layers_used": ["vimsottari_md", "d9", "lal_kitab"],
  "bridge_practice_note": "Optional: relevant practice if one applies"
}

Language: respond in the language specified in the live.language field.
If language is "es": all fields except layers_used must be in Spanish.
"""
'''

# ---------------------------------------------------------------------------
# Step 2: JSON path hook for main.py
# ---------------------------------------------------------------------------

# We insert the JSON path block right after _full_context is built and before
# the _master_system assembly. Landmark: the line that starts the KV CACHE FIX comment.
# The JSON path short-circuits the entire prose context + prompt assembly.

JSON_PATH_BLOCK = '''
        # ================================================================
        # JSON PATH (use_json_context=True) — Phase 4 JSON-first refactor
        # ================================================================
        if getattr(request, "use_json_context", False):
            try:
                print(f"[json-v2] JSON path activated for chart {request.chart_id}")
                from antar_engine.chart_context_builder_json import (
                    build_chart_context_json,
                    chart_static_to_json,
                    live_to_json,
                    estimate_token_count,
                )
                from antar_engine.predict_system_prompt_v2 import PREDICT_SYSTEM_PROMPT_V2

                _json_ctx = await build_chart_context_json(
                    chart_id=request.chart_id,
                    question=request.question,
                    concern=concern,
                    language=_lang if "_lang" in dir() else language,
                    supabase=supabase,
                )
                _static_json = chart_static_to_json(_json_ctx)
                _live_json   = live_to_json(_json_ctx)

                # System prompt = framework (cached) + static chart JSON (cached)
                # ## LIVE DATA marker = split point for KV cache
                _json_system = (
                    PREDICT_SYSTEM_PROMPT_V2
                    + "\\n\\n## CHART DATA (JSON)\\n"
                    + _static_json
                    + "\\n\\n## LIVE DATA\\n"
                    + _live_json
                )

                # User message = just the question
                _json_user_prompt = (
                    f"Question: {request.question}\\n"
                    f"Domain: {concern}\\n"
                    "Respond with a JSON object exactly as specified in the output format."
                )

                print(f"[json-v2] system={len(_json_system)} chars "
                      f"(~{estimate_token_count(_json_system)} tokens), "
                      f"user={len(_json_user_prompt)} chars")

                _json_raw, _json_tokens = await call_llm_claude(
                    _json_user_prompt,
                    history=request.conversation_history or [],
                    system_override=_json_system,
                )

                # Parse structured response
                import json as _json_mod
                _json_text = _json_raw.strip()
                if _json_text.startswith("```"):
                    _json_text = _json_text.split("\\n", 1)[-1]
                    _json_text = _json_text.rsplit("```", 1)[0]
                try:
                    _parsed = _json_mod.loads(_json_text)
                except Exception:
                    # Fallback: return raw if parse fails
                    _parsed = {"plain_summary": _json_raw, "verdict": "", "signal_line": ""}

                print(f"[json-v2] response parsed — confidence={_parsed.get('confidence','?')}")

                # Save to chat_messages if table exists
                try:
                    supabase.table("chat_messages").insert({
                        "chart_id": request.chart_id,
                        "question": request.question,
                        "plain_summary": _parsed.get("plain_summary", ""),
                        "signal_line": _parsed.get("signal_line", ""),
                        "action_item": _parsed.get("action_item", ""),
                        "timing_window": _parsed.get("timing_window", ""),
                        "confidence": _parsed.get("confidence", ""),
                        "domain": concern,
                        "language": _lang if "_lang" in dir() else language,
                        "why_this": _parsed.get("why_this", ""),
                        "bridge_practice_note": _parsed.get("bridge_practice_note", ""),
                    }).execute()
                except Exception as _save_e:
                    print(f"[json-v2] chat_messages save failed (non-fatal): {_save_e}")

                return {
                    "plain_summary": _parsed.get("plain_summary", ""),
                    "signal_line": _parsed.get("signal_line", ""),
                    "action_item": _parsed.get("action_item", ""),
                    "timing_window": _parsed.get("timing_window", ""),
                    "confidence": _parsed.get("confidence", ""),
                    "verdict": _parsed.get("verdict", ""),
                    "why_this": _parsed.get("why_this", ""),
                    "layers_used": _parsed.get("layers_used", []),
                    "bridge_practice_note": _parsed.get("bridge_practice_note", ""),
                    "context_path": "json-v2",
                    "tokens_used": _json_tokens,
                }
            except Exception as _json_e:
                import traceback
                print(f"[json-v2] FAILED — falling back to prose path: {_json_e}")
                print(f"[json-v2] Traceback: {traceback.format_exc()}")
                # Fall through to existing prose path below
        # ================================================================
        # END JSON PATH
        # ================================================================
'''

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Phase 4: JSON predict path + feature flag")
    print("=" * 60)

    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    # --- Write predict_system_prompt_v2.py ---
    print("\n📝 Writing antar_engine/predict_system_prompt_v2.py...")
    write("antar_engine/predict_system_prompt_v2.py", SYSTEM_PROMPT_V2)
    import ast
    ast.parse(SYSTEM_PROMPT_V2)
    print("  ✅ Written and syntax OK")

    # --- Patch PredictRequest ---
    print("\n🔧 Patching PredictRequest...")
    content = read("main.py")

    old_request = '''    current_focus:        Optional[str] = Field(None, description="What the user is working on (Patra)")'''
    new_request = '''    current_focus:        Optional[str] = Field(None, description="What the user is working on (Patra)")
    use_json_context:     bool = Field(False, description="Use JSON context path (Phase 4 A/B flag)")'''

    if "use_json_context" in content:
        print("  ℹ️  use_json_context already in PredictRequest — skipping")
    elif old_request in content:
        content = content.replace(old_request, new_request)
        print("  ✅ use_json_context added to PredictRequest")
    else:
        print("  ⚠️  PredictRequest pattern not found — skipping")

    # --- Inject JSON path block ---
    print("\n🔧 Injecting JSON path into /predict route...")

    # Landmark: inject just before the KV CACHE FIX comment block
    # which starts with "        # === KV CACHE FIX ==="
    landmark = "        # === KV CACHE FIX ==="

    if "[json-v2] JSON path activated" in content:
        print("  ℹ️  JSON path block already present — skipping")
    elif landmark in content:
        content = content.replace(landmark, JSON_PATH_BLOCK + landmark, 1)
        print("  ✅ JSON path block injected before KV CACHE FIX")
    else:
        # Try alternate landmark
        alt_landmark = "        prediction_text, tokens_used = await call_llm_claude("
        if alt_landmark in content:
            content = content.replace(alt_landmark, JSON_PATH_BLOCK + alt_landmark, 1)
            print("  ✅ JSON path block injected before call_llm_claude (alt landmark)")
        else:
            print("  ⚠️  Could not find injection landmark in main.py")
            print("  Manual fix: add use_json_context check before call_llm_claude()")

    write("main.py", content)

    # --- Verify syntax ---
    print("\n🔍 Verifying syntax...")
    try:
        ast.parse(content)
        print("  ✅ main.py syntax OK")
    except SyntaxError as e:
        print(f"  ❌ SYNTAX ERROR in main.py: {e}")
        print("  Rolling back...")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Phase 4 complete.")
    print("\nNext steps:")
    print("  1. git add -A && git commit -m 'feat: JSON context path for /predict' && git push")
    print("  2. Wait for Railway deploy (~60s)")
    print("  3. Test JSON path:")
    print("""     curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/predict" \\
       -H "Content-Type: application/json" \\
       -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a","question":"when will my cash flow get resolved","language":"en","use_json_context":true}' \\
       | python3 -c "import sys,json; d=json.load(sys.stdin); print('PATH:', d.get('context_path')); print('SUMMARY:', d.get('plain_summary','')[:200])" """)
    print("  4. Test prose path still works (no use_json_context):")
    print("""     curl -s -X POST "https://antar-fastapi-production.up.railway.app/api/v1/predict" \\
       -H "Content-Type: application/json" \\
       -d '{"chart_id":"de02bb52-d43a-4b09-be25-b45a07bfbf8a","question":"how is my career","language":"en"}' \\
       | python3 -c "import sys,json; d=json.load(sys.stdin); print('PATH:', d.get('context_path','prose')); print(d.get('plain_summary','')[:200])" """)


if __name__ == "__main__":
    main()
