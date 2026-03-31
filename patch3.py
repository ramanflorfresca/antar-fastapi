#!/usr/bin/env python3
"""
apply_c3_patch.py — Sprint C3 patch for main.py
Run from repo root: python apply_c3_patch.py

Changes:
  1. Add pattern_memory import
  2. Wire memory block into /predict before the LLM call
  3. Wire diagnostic_block into system prompt when triggered
  4. Add POST /api/v1/predictions/{prediction_id}/rate endpoint
  5. Add GET /api/v1/patterns/{chart_id} endpoint (theme summary)
"""

import shutil
import sys
from pathlib import Path

MAIN = Path("main.py")
if not MAIN.exists():
    print("❌  main.py not found — run from repo root")
    sys.exit(1)

shutil.copy(MAIN, "main.py.bak_c3")
print("✅  Backed up to main.py.bak_c3")

src = MAIN.read_text()

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — import
# ─────────────────────────────────────────────────────────────────────────────

IMPORT_ANCHOR = "from antar_engine.desh_kal_patra import get_dkp_context"
IMPORT_NEW = (
    "from antar_engine.desh_kal_patra import get_dkp_context\n"
    "from antar_engine.pattern_memory import build_pattern_memory"
)

if "from antar_engine.pattern_memory import build_pattern_memory" in src:
    print("⚠️   Change 1 already applied — skipping import")
elif IMPORT_ANCHOR not in src:
    print("❌  Change 1 FAILED — desh_kal_patra import not found")
    sys.exit(1)
else:
    src = src.replace(IMPORT_ANCHOR, IMPORT_NEW, 1)
    print("✅  Change 1 applied — pattern_memory import added")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 — wire pattern memory into /predict before the LLM call
# Insert after the DKP block (end of C2) and before the LLM call
# ─────────────────────────────────────────────────────────────────────────────

ANCHOR_C2_END = "    # ── end C2 ───────────────────────────────────────────────────"

MEMORY_BLOCK = """    # ── end C2 ───────────────────────────────────────────────────

    # ── C3: Pattern Memory — Layer 7 ─────────────────────────────
    _memory = {}
    try:
        _memory = build_pattern_memory(
            chart_id=request.chart_id,
            current_concern=concern,
            current_question=request.question,
            supabase=supabase,
        )
        if _memory.get("diagnostic_mode"):
            print(f"[predict] C3 DIAGNOSTIC MODE — unresolved {concern} case detected")
        elif _memory.get("memory_block"):
            print(f"[predict] C3 memory loaded — {len(_memory['past_predictions'])} past predictions")
    except Exception as _mem_err:
        print(f"[predict] C3 pattern memory failed (non-fatal): {_mem_err}")
        _memory = {}
    # ── end C3 ───────────────────────────────────────────────────"""

if "C3: Pattern Memory" in src:
    print("⚠️   Change 2 already applied — skipping memory block")
elif ANCHOR_C2_END not in src:
    print("❌  Change 2 FAILED — C2 end anchor not found")
    sys.exit(1)
else:
    src = src.replace(ANCHOR_C2_END, MEMORY_BLOCK, 1)
    print("✅  Change 2 applied — pattern memory wired into /predict")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3 — inject memory + diagnostic blocks into the prompt
# Find where full_context or prompt is built and append memory
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_ANCHOR = '    _using_master = _full_context and len(_full_context) > 500'
PROMPT_NEW = """    # ── C3: Append memory + diagnostic blocks to prompt ─────────
    _memory_block     = (_memory or {}).get("memory_block", "")
    _diagnostic_block = (_memory or {}).get("diagnostic_block", "")

    if _memory_block and _full_context:
        _full_context += f"\\n\\n{_memory_block}"
    if _diagnostic_block and _full_context:
        _full_context += f"\\n\\n{_diagnostic_block}"
    if _memory_block and not _full_context:
        prompt += f"\\n\\n{_memory_block}"
    if _diagnostic_block and not _full_context:
        prompt += f"\\n\\n{_diagnostic_block}"
    # ── end C3 memory injection ───────────────────────────────────

    _using_master = _full_context and len(_full_context) > 500"""

if "C3: Append memory" in src:
    print("⚠️   Change 3 already applied — skipping prompt injection")
elif PROMPT_ANCHOR not in src:
    print("❌  Change 3 FAILED — _using_master anchor not found")
    sys.exit(1)
else:
    src = src.replace(PROMPT_ANCHOR, PROMPT_NEW, 1)
    print("✅  Change 3 applied — memory blocks injected into prompt")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 4 — new endpoints (rate + patterns)
# ─────────────────────────────────────────────────────────────────────────────

NEW_ENDPOINTS = '''

# ── C3: Rate a prediction ─────────────────────────────────────────────────────
@app.post("/api/v1/predictions/{prediction_id}/rate")
async def rate_prediction(prediction_id: str, body: dict):
    """
    User rates whether a prediction came true.
    Body: { "rating": 1 }  — 1 = accurate, 0 = did not happen
    Sprint C3.
    """
    rating = body.get("rating")
    if rating not in (0, 1):
        raise HTTPException(status_code=400, detail="rating must be 0 or 1")
    try:
        result = supabase.table("predictions") \\
            .update({"accuracy_rating": rating}) \\
            .eq("id", prediction_id) \\
            .execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return {"success": True, "prediction_id": prediction_id, "rating": rating}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[rate] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save rating")


# ── C3: Pattern summary for a chart ──────────────────────────────────────────
@app.get("/api/v1/patterns/{chart_id}")
async def get_pattern_summary(chart_id: str):
    """
    Returns pattern memory analysis for a chart:
    - Recurring themes
    - Unresolved cases
    - Accuracy summary
    - All past predictions with fulfillment status
    Sprint C3.
    """
    from antar_engine.pattern_memory import build_pattern_memory, _fetch_predictions, _infer_fulfillment, _detect_themes, _accuracy_summary

    try:
        past = _fetch_predictions(chart_id, supabase)
        if not past:
            return {
                "chart_id":         chart_id,
                "total_predictions": 0,
                "recurring_themes":  [],
                "unresolved_cases":  [],
                "accuracy_summary":  "",
                "predictions":       [],
            }

        past = _infer_fulfillment(past)

        unresolved = [
            p for p in past
            if p.get("fulfillment_status") == "inferred_unresolved"
        ]
        themes      = _detect_themes(past)
        acc_summary = _accuracy_summary(past)

        return {
            "chart_id":          chart_id,
            "total_predictions": len(past),
            "recurring_themes":  themes,
            "unresolved_cases":  [
                {
                    "id":           p.get("id"),
                    "concern":      p.get("concern"),
                    "signal_line":  p.get("signal_line"),
                    "timing_window":p.get("timing_window"),
                    "created_at":   p.get("created_at"),
                }
                for p in unresolved
            ],
            "accuracy_summary":  acc_summary,
            "predictions":       [
                {
                    "id":               p.get("id"),
                    "created_at":       p.get("created_at"),
                    "concern":          p.get("concern"),
                    "signal_line":      p.get("signal_line"),
                    "timing_window":    p.get("timing_window"),
                    "fulfillment_status": p.get("fulfillment_status"),
                    "accuracy_rating":  p.get("accuracy_rating"),
                }
                for p in past
            ],
        }

    except Exception as e:
        print(f"[patterns] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pattern summary")
'''

if '"/api/v1/predictions/{prediction_id}/rate"' in src:
    print("⚠️   Change 4 already applied — skipping new endpoints")
else:
    src = src.rstrip() + "\n" + NEW_ENDPOINTS + "\n"
    print("✅  Change 4 applied — /rate and /patterns endpoints added")

# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

MAIN.write_text(src)
print(f"\n✅  main.py updated. Backup at main.py.bak_c3")
print("    Next:")
print("    1. cp pattern_memory.py antar_engine/pattern_memory.py")
print("    2. Run c3_migration.sql in Supabase SQL editor")
print("    3. git add antar_engine/pattern_memory.py main.py")
print("    4. git commit -m 'feat(C3): pattern memory + diagnostic mode'")
print("    5. git push")
